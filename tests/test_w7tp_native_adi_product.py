from __future__ import annotations

import copy
import hashlib
import random
import sys
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.w7tp_native_adi.core import (
    ADIError,
    PACKET_SCHEMA_VERSION,
    PROTOCOL_VERSION,
    SpacetimeADI,
    canonical_bytes,
    spiral_position,
)
from services.w7tp_native_adi.service import health_payload


RECORD_COUNT = 100_000
FIXED_SEED = 20260722


class W7TPNativeADIProductTest(unittest.TestCase):
    def test_01_native_spiral_and_thread_safe_insert_search(self) -> None:
        self.assertEqual(
            [spiral_position(index) for index in range(9)],
            [(0, 0), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)],
        )
        engine = SpacetimeADI()
        barrier = threading.Barrier(8)

        def insert_partition(worker: int) -> None:
            barrier.wait()
            for index in range(worker, 2_000, 8):
                engine.insert(f"thread-{index:05d}", 7, {"ordinal": index})

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(insert_partition, range(8)))
        results = engine.search(7, 7, 2_000)
        self.assertEqual(len(results), 2_000)
        self.assertEqual(
            [record["collision_index"] for record in results], list(range(2_000))
        )

    def test_02_fixed_seed_100000_product_demo(self) -> None:
        randomizer = random.Random(FIXED_SEED)
        source = SpacetimeADI()
        receiver = SpacetimeADI(
            authority_receipt_verifier=lambda ref, _root: (
                ref == "total-field:receipt:test-product"
            )
        )
        baseline_count = 75_000
        source_records = []
        for index in range(RECORD_COUNT):
            slot = 1_800_000_000 + randomizer.randrange(4_096)
            payload = {
                "scene": "ASSOCIATION",
                "ordinal": index,
                "context_ref": "ctx:sha256:"
                + hashlib.sha256(f"{FIXED_SEED}:{index}".encode("utf-8")).hexdigest(),
            }
            record = source.insert(f"adi-{index:06d}", slot, payload)
            source_records.append(record)
            if index < baseline_count:
                receiver.insert(record["id"], record["time_slot"], record["payload"])

        packet = source.packet(
            receiver_lookup=receiver.record_hashes(),
            parent_snapshot_ref="snapshot:test-product-baseline",
        )
        reconstructed = receiver.reconstruct(
            packet, "total-field:receipt:test-product"
        )
        source_state = source.export_state()
        source_bytes = canonical_bytes(source_state)
        reconstructed_bytes = canonical_bytes(reconstructed["reconstructed_state"])
        source_ids = {record["id"] for record in source_state["records"]}
        reconstructed_ids = {
            record["id"] for record in reconstructed["reconstructed_state"]["records"]
        }

        self.assertEqual(packet["protocol_version"], PROTOCOL_VERSION)
        self.assertEqual(packet["schema_version"], PACKET_SCHEMA_VERSION)
        self.assertEqual(packet["total_field_decision"], "CANDIDATE")
        self.assertEqual(reconstructed["total_field_decision"], "ALLOW")
        self.assertEqual(source_ids, reconstructed_ids)
        self.assertEqual(source_bytes, reconstructed_bytes)
        self.assertEqual(reconstructed["source_sha256"], reconstructed["reconstructed_sha256"])
        self.assertTrue(packet["reference_lookup"]["entries"])
        self.assertTrue(packet["reconstruction_conditions"])
        self.assertTrue(packet["verification"]["verification_root"])
        self.assertEqual(packet["delta"]["changed_atom_count"], RECORD_COUNT - baseline_count)

        print(f"RECORD_COUNT={RECORD_COUNT}")
        print(f"QUERY_RESULT_COUNT={len(reconstructed_ids)}")
        print(f"SOURCE_SHA256={reconstructed['source_sha256']}")
        print(f"RECONSTRUCTED_SHA256={reconstructed['reconstructed_sha256']}")
        print(f"PACKET_BYTES={len(canonical_bytes(packet))}")
        print(f"SOURCE_BYTES={len(source_bytes)}")
        print("ID_EQUIVALENT=PASS")
        print("BYTE_EQUIVALENT=PASS")
        print("PACKET_EVIDENCE_REFERENCE_OR_LOOKUP=PASS")
        print("PACKET_EVIDENCE_RECONSTRUCTION_CONDITIONS=PASS")
        print("PACKET_EVIDENCE_PROTOCOL=PASS")
        print("PACKET_EVIDENCE_VERIFICATION=PASS")
        print("PACKET_EVIDENCE_TOTAL_FIELD_DECISION=PASS")

    def test_03_fail_closed_and_health_contract(self) -> None:
        engine = SpacetimeADI()
        with self.assertRaises(ADIError) as secret:
            engine.insert("blocked", 1, {"token": "fixture"})
        self.assertEqual(secret.exception.reason_code, "RAW_CREDENTIAL_FORBIDDEN")
        engine.insert("safe", 1, {"value": "candidate"})
        packet = engine.packet()
        tampered = copy.deepcopy(packet)
        tampered["total_field_decision"] = "ALLOW"
        with self.assertRaises(ADIError) as authority:
            SpacetimeADI().reconstruct(tampered, "receipt:test-tampered")
        self.assertEqual(
            authority.exception.reason_code, "PACKET_CANDIDATE_DECISION_REQUIRED"
        )
        health = health_payload()
        self.assertEqual(health["state"], "PASS")
        self.assertEqual(health["service"], "W7TP_NATIVE_ADI_AGENT")
        self.assertTrue(health["production"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
