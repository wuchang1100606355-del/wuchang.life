"""HTTP carrier sender and durable append-only retry outbox."""

from __future__ import annotations

import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Mapping

from .core import CoreBindings, MeshHold, require_core, utc_now, utc_text
from .journal import MeshStorage


def validate_peer_url(value: object) -> str:
    if not isinstance(value, str):
        raise MeshHold("HOLD_PEER_URL_INVALID")
    parsed = urllib.parse.urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise MeshHold("HOLD_PEER_URL_INVALID")
    path = parsed.path.rstrip("/")
    if not path.endswith("/v2.1/packets"):
        path = f"{path}/v2.1/packets"
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


class MeshTransport:
    def __init__(self, storage: MeshStorage) -> None:
        self.storage = storage

    def _queue(self, *, carrier_ref: str, peer_url: str, reason_code: str, attempt: int) -> dict[str, object]:
        core = require_core()
        queued_at = utc_text(utc_now())
        record = {
            "schema_id": "W7TP_GT_MESH_OUTBOX_EVENT_V21",
            "state": "QUEUED_FOR_RETRY",
            "carrier_ref": carrier_ref,
            "peer_url": peer_url,
            "attempt": attempt,
            "reason_code": reason_code,
            "queued_at": queued_at,
            "carrier_authority": "NONE",
        }
        key = f"{time.time_ns():020d}-{core.sha256_hex(core.canonical_json_bytes(record))}"
        self.storage.journal.append("outbox_queue", key, record)
        return record

    def _terminal_conflict(
        self,
        *,
        carrier_ref: str,
        peer_url: str,
        reason_code: str,
        attempt: int,
    ) -> dict[str, object]:
        core = require_core()
        terminated_at = utc_text(utc_now())
        record = {
            "schema_id": "W7TP_GT_MESH_OUTBOX_TERMINAL_V21",
            "state": "HOLD_TERMINAL_CONFLICT_NOT_RETRYABLE",
            "carrier_ref": carrier_ref,
            "peer_url": peer_url,
            "attempt": attempt,
            "reason_code": reason_code,
            "terminated_at": terminated_at,
            "carrier_authority": "NONE",
        }
        key = f"{time.time_ns():020d}-{core.sha256_hex(core.canonical_json_bytes(record))}"
        self.storage.journal.append("outbox_terminal", key, record)
        return record

    @staticmethod
    def _safe_terminal_conflict_reason(raw: bytes, core: CoreBindings) -> str | None:
        if len(raw) > 64 * 1024:
            return None
        try:
            parsed = core.canonical_json_loads(raw, require_canonical=False)
        except Exception:
            return None
        if not isinstance(parsed, dict):
            return None
        reason_code = parsed.get("reason_code")
        if (
            not isinstance(reason_code, str)
            or not reason_code.startswith("CONFLICT_")
            or len(reason_code) <= len("CONFLICT_")
            or len(reason_code) > 128
            or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for character in reason_code)
        ):
            return None
        return reason_code

    def send(
        self,
        carrier: Mapping[str, object],
        *,
        carrier_ref: str,
        peer_url: str,
        timeout_seconds: int = 10,
        queue_on_failure: bool = True,
        attempt: int = 1,
    ) -> dict[str, object]:
        core = require_core()
        url = validate_peer_url(peer_url)
        raw = core.canonical_json_bytes(carrier)
        if carrier_ref != core.sha256_ref(raw):
            raise MeshHold("HOLD_CARRIER_REF_MISMATCH")
        request = urllib.request.Request(
            url,
            data=raw,
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        started_ns = time.perf_counter_ns()
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                response_raw = response.read(1024 * 1024 + 1)
                if len(response_raw) > 1024 * 1024:
                    raise MeshHold("HOLD_RECEIPT_TOO_LARGE")
        except urllib.error.HTTPError as exc:
            if exc.code == 409:
                try:
                    conflict_raw = exc.read(64 * 1024 + 1)
                except (OSError, ValueError):
                    conflict_raw = b""
                conflict_reason = self._safe_terminal_conflict_reason(conflict_raw, core)
                if conflict_reason is not None:
                    self._terminal_conflict(
                        carrier_ref=carrier_ref,
                        peer_url=url,
                        reason_code=conflict_reason,
                        attempt=attempt,
                    )
                    return {
                        "state": "HOLD_TERMINAL_CONFLICT_NOT_RETRYABLE",
                        "reason_code": conflict_reason,
                        "carrier_ref": carrier_ref,
                    }
            reason = f"HTTP_{exc.code}"
            if queue_on_failure:
                self._queue(carrier_ref=carrier_ref, peer_url=url, reason_code=reason, attempt=attempt)
            return {"state": "HOLD_QUEUED_FOR_RETRY", "reason_code": reason, "carrier_ref": carrier_ref}
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            del exc
            reason = "CARRIER_UNAVAILABLE"
            if queue_on_failure:
                self._queue(carrier_ref=carrier_ref, peer_url=url, reason_code=reason, attempt=attempt)
            return {"state": "HOLD_QUEUED_FOR_RETRY", "reason_code": reason, "carrier_ref": carrier_ref}
        receipt = core.canonical_json_loads(response_raw, require_canonical=True)
        if not isinstance(receipt, dict):
            raise MeshHold("HOLD_RECEIPT_INVALID")
        round_trip_ns = time.perf_counter_ns() - started_ns
        transport_receipt = {
            **receipt,
            "carrier_bytes": len(raw),
            "receipt_bytes": len(response_raw),
            "round_trip_ns": round_trip_ns,
            "peer_url": url,
            "packet_ref": receipt.get("packet_ref") or carrier.get("packet_ref"),
            "target_snapshot_ref": receipt.get("target_snapshot_ref"),
            "performance_evidence_state": "OBSERVED_DIRECT_HTTP_ROUND_TRIP",
            "economic_gate_scope": "OBJECT_PACKET_COST_NOT_COMPLETE_HTTP_BENCHMARK",
            "w7g3_fixed_vector_relation": "CODEC_COMPATIBILITY_ONLY_NOT_MESH_END_TO_END_BENCHMARK",
            "synthetic_throughput_claim": False,
        }
        event = {
            "schema_id": "W7TP_GT_MESH_REMOTE_RECEIPT_EVENT_V21",
            "carrier_ref": carrier_ref,
            "peer_url": url,
            "received_at": utc_text(utc_now()),
            "packet_ref": transport_receipt.get("packet_ref"),
            "target_snapshot_ref": transport_receipt.get("target_snapshot_ref"),
            "carrier_bytes": len(raw),
            "receipt_bytes": len(response_raw),
            "round_trip_ns": round_trip_ns,
            "receipt": transport_receipt,
            "carrier_authority": "NONE",
        }
        key = f"{time.time_ns():020d}-{carrier_ref.removeprefix('sha256:')}"
        self.storage.journal.append("remote_receipts", key, event)
        return transport_receipt

    def retry_pending(self, *, timeout_seconds: int = 10) -> list[dict[str, object]]:
        completed = {
            (item.get("carrier_ref"), item.get("peer_url"))
            for item in self.storage.journal.records("outbox_done")
        }
        terminated = {
            (item.get("carrier_ref"), item.get("peer_url"))
            for item in self.storage.journal.records("outbox_terminal")
        }
        latest: dict[tuple[object, object], dict[str, object]] = {}
        for item in self.storage.journal.records("outbox_queue"):
            latest[(item.get("carrier_ref"), item.get("peer_url"))] = item
        results: list[dict[str, object]] = []
        for (carrier_ref, peer_url), item in latest.items():
            if (
                (carrier_ref, peer_url) in completed
                or (carrier_ref, peer_url) in terminated
                or not isinstance(carrier_ref, str)
                or not isinstance(peer_url, str)
            ):
                continue
            carrier = self.storage.get_artifact(carrier_ref)
            attempt = int(item.get("attempt", 0)) + 1
            result = self.send(
                carrier,
                carrier_ref=carrier_ref,
                peer_url=peer_url,
                timeout_seconds=timeout_seconds,
                queue_on_failure=False,
                attempt=attempt,
            )
            results.append(result)
            if str(result.get("delivery_state", "")).startswith("PASS"):
                done = {
                    "schema_id": "W7TP_GT_MESH_OUTBOX_DONE_V21",
                    "carrier_ref": carrier_ref,
                    "peer_url": peer_url,
                    "attempt": attempt,
                    "completed_at": utc_text(utc_now()),
                    "receipt_ref": result.get("receipt_ref"),
                }
                key = f"{time.time_ns():020d}-{carrier_ref.removeprefix('sha256:')}"
                self.storage.journal.append("outbox_done", key, done)
            elif result.get("state") == "HOLD_TERMINAL_CONFLICT_NOT_RETRYABLE":
                continue
            else:
                self._queue(
                    carrier_ref=carrier_ref,
                    peer_url=peer_url,
                    reason_code=str(result.get("reason_code", "RETRY_HOLD")),
                    attempt=attempt,
                )
        return results
