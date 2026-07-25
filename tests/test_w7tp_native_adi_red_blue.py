from __future__ import annotations

import copy
import json
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.dead_letter import dead_letter_24h_hash_writer
from services.w7tp_native_adi.core import (
    ADIError,
    MAX_LOGICAL_TIME_UINT64,
    SpacetimeADI,
    _packet_hash_basis,
    canonical_bytes,
    canonical_sha256,
)
from services.w7tp_native_adi.service import (
    DEFAULT_PORT,
    NativeADIHTTPServer,
)


class CaptureDeadLetter:
    def __init__(self) -> None:
        self.items: list[dict[str, object]] = []

    def __call__(self, **kwargs: object) -> dict[str, object]:
        self.items.append(dict(kwargs))
        return {
            "state": "DEAD_LETTER_HASH_ONLY_24H_WRITTEN",
            "dead_letter_id": f"test-{len(self.items)}",
            "plaintext_stored": False,
        }


class W7TPNativeADIRedBlueTest(unittest.TestCase):
    def _source_packet(self, now: int = 1_000) -> dict[str, object]:
        source = SpacetimeADI(clock=lambda: now)
        source.insert("atom-a", 7, {"value": 1})
        return source.packet(snapshot_created_at_unix_seconds=now)

    def test_forged_allow_is_rejected_and_dead_lettered(self) -> None:
        dead_letter = CaptureDeadLetter()
        packet = self._source_packet()
        packet["total_field_decision"] = "ALLOW"
        packet["packet_root"] = canonical_sha256(_packet_hash_basis(packet))
        receiver = SpacetimeADI(
            authority_receipt_verifier=lambda _ref, _root: True,
            dead_letter_writer=dead_letter,
            clock=lambda: 1_000,
        )
        with self.assertRaises(ADIError) as caught:
            receiver.reconstruct(packet, "receipt:forged")
        self.assertEqual(caught.exception.reason_code, "PACKET_CANDIDATE_DECISION_REQUIRED")
        self.assertEqual(dead_letter.items[0]["reason"], "PACKET_CANDIDATE_DECISION_REQUIRED")

    def test_valid_authority_receipt_is_bound_and_replay_dead_lettered(self) -> None:
        dead_letter = CaptureDeadLetter()
        packet = self._source_packet()
        expected_root = packet["packet_root"]
        receiver = SpacetimeADI(
            authority_receipt_verifier=lambda ref, root: (
                ref == "total-field:receipt:valid" and root == expected_root
            ),
            dead_letter_writer=dead_letter,
            clock=lambda: 1_000,
        )
        result = receiver.reconstruct(packet, "total-field:receipt:valid")
        self.assertEqual(result["total_field_decision"], "ALLOW")
        self.assertEqual(result["authority_receipt_ref"], "total-field:receipt:valid")
        self.assertEqual(result["packet_root_role"], "INTEGRITY_ONLY")
        with self.assertRaises(ADIError) as replay:
            receiver.reconstruct(packet, "total-field:receipt:valid")
        self.assertEqual(replay.exception.reason_code, "AUTHORITY_RECEIPT_REPLAY")
        self.assertEqual(dead_letter.items[-1]["reason"], "AUTHORITY_RECEIPT_REPLAY")

    def test_canonical_type_distinction_and_strict_json(self) -> None:
        self.assertNotEqual(canonical_bytes(1), canonical_bytes("1"))
        self.assertNotEqual(canonical_bytes(True), canonical_bytes(1))
        with self.assertRaises(ADIError) as caught:
            canonical_bytes((1, 2))
        self.assertEqual(caught.exception.reason_code, "NON_JSON_VALUE")
        record = SpacetimeADI().insert("typed", 1, {"value": 1})
        self.assertEqual(record["type_tag"], "W7TP_NATIVE_ADI_RECORD")

    def test_uint64_time_determinism_and_timestamp_classes(self) -> None:
        left = SpacetimeADI(clock=lambda: 1_000)
        right = SpacetimeADI(clock=lambda: 1_000)
        self.assertEqual(
            left.insert("max", MAX_LOGICAL_TIME_UINT64, {"value": "same"}),
            right.insert("max", MAX_LOGICAL_TIME_UINT64, {"value": "same"}),
        )
        packet = left.packet(snapshot_created_at_unix_seconds=1_000)
        receiver = SpacetimeADI(
            authority_receipt_verifier=lambda _ref, _root: True,
            clock=lambda: 1_000,
        )
        invalid = copy.deepcopy(packet)
        invalid["snapshot"]["created_at_unix_seconds"] = "bad"
        invalid["packet_root"] = canonical_sha256(_packet_hash_basis(invalid))
        with self.assertRaises(ADIError) as invalid_error:
            receiver.reconstruct(invalid, "receipt:invalid-time")
        self.assertEqual(invalid_error.exception.reason_code, "TIMESTAMP_INVALID")
        future = left.packet(snapshot_created_at_unix_seconds=1_031)
        with self.assertRaises(ADIError) as future_error:
            receiver.reconstruct(future, "receipt:future")
        self.assertEqual(future_error.exception.reason_code, "TIMESTAMP_FUTURE")
        past = left.packet(snapshot_created_at_unix_seconds=0)
        receiver_past = SpacetimeADI(
            authority_receipt_verifier=lambda _ref, _root: True,
            clock=lambda: 4_601,
        )
        with self.assertRaises(ADIError) as past_error:
            receiver_past.reconstruct(past, "receipt:past")
        self.assertEqual(past_error.exception.reason_code, "TIMESTAMP_PAST")

    def test_hotspot_scaling_and_empty_sparse_query_budget(self) -> None:
        timings: list[float] = []
        for count in (2_000, 4_000):
            engine = SpacetimeADI()
            started = time.perf_counter()
            for index in range(count):
                engine.insert(f"hot-{count}-{index}", 99, {"ordinal": index})
            timings.append(time.perf_counter() - started)
        self.assertLess(timings[1], timings[0] * 3.5)

        sparse = SpacetimeADI()
        sparse.insert("low", 1, {"value": "low"})
        sparse.insert("high", MAX_LOGICAL_TIME_UINT64, {"value": "high"})
        self.assertEqual(sparse.search(2, MAX_LOGICAL_TIME_UINT64 - 1), [])
        self.assertEqual(
            [item["id"] for item in sparse.search(0, MAX_LOGICAL_TIME_UINT64)],
            ["low", "high"],
        )
        with self.assertRaises(ADIError) as budget:
            sparse.search(
                0,
                MAX_LOGICAL_TIME_UINT64,
                limit=2,
                query_budget={"max_occupied_slots": 1, "max_records": 10},
            )
        self.assertEqual(
            budget.exception.reason_code, "QUERY_OCCUPIED_SLOT_BUDGET_EXCEEDED"
        )

    def test_parent_delta_changed_atoms_and_deleted_refs_reconstruct(self) -> None:
        source = SpacetimeADI(clock=lambda: 1_000)
        source.insert("keep", 10, {"value": "same"})
        source.insert("add", 20, {"value": "new"})
        receiver = SpacetimeADI(
            authority_receipt_verifier=lambda _ref, _root: True,
            clock=lambda: 1_000,
        )
        receiver.insert("keep", 10, {"value": "same"})
        receiver.insert("delete", 30, {"value": "old"})
        packet = source.packet(
            receiver_lookup=receiver.record_hashes(),
            parent_snapshot_ref="snapshot:receiver-before",
            snapshot_created_at_unix_seconds=1_000,
        )
        self.assertEqual(packet["delta"]["parent_snapshot_ref"], "snapshot:receiver-before")
        self.assertEqual(packet["delta"]["changed_atom_count"], 1)
        self.assertEqual(packet["delta"]["deleted_refs"], ["delete"])
        result = receiver.reconstruct(packet, "receipt:delta")
        self.assertEqual(
            canonical_bytes(result["reconstructed_state"]),
            canonical_bytes(source.export_state()),
        )
        self.assertNotIn("delete", receiver.record_hashes())

    def test_http_default_9110_path_routes_reject_to_existing_writer(self) -> None:
        self.assertEqual(DEFAULT_PORT, 9110)
        with tempfile.TemporaryDirectory() as directory:
            original_queue = dead_letter_24h_hash_writer.QUEUE
            dead_letter_24h_hash_writer.QUEUE = Path(directory) / "dead_letter_hash_queue.jsonl"
            engine = SpacetimeADI(
                dead_letter_writer=dead_letter_24h_hash_writer.append_24h_hash_dead_letter
            )
            server = NativeADIHTTPServer(("127.0.0.1", 0), engine)
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                request = urllib.request.Request(
                    f"http://127.0.0.1:{server.server_port}/v1/adi/reconstruct",
                    data=json.dumps({"packet": {}}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as response:
                    urllib.request.urlopen(request, timeout=3)
                self.assertEqual(response.exception.code, 422)
                lines = dead_letter_24h_hash_writer.QUEUE.read_text(encoding="utf-8").splitlines()
                self.assertEqual(len(lines), 1)
                record = json.loads(lines[0])
                self.assertEqual(record["reason"], "RECONSTRUCT_REQUEST_SHAPE_INVALID")
                self.assertFalse(record["plaintext_stored"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)
                dead_letter_24h_hash_writer.QUEUE = original_queue


if __name__ == "__main__":
    unittest.main(verbosity=2)
