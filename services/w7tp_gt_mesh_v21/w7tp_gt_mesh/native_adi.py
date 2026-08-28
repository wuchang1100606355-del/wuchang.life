"""Thin adapter for the existing taiji01 Native ADI append-only insert API."""

from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Mapping

from .core import MeshConflict, MeshHold, epoch_seconds, require_core, utc_now, utc_parse, utc_text
from .journal import MeshStorage


NATIVE_ADI_RECORD_SCHEMA = "W7TP_GT_MESH_NATIVE_ADI_RECORD_V21"
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_PAYLOAD_KEYS = {
    "source_node_ref",
    "packet_id",
    "snapshot_sha256",
    "capability_ref",
    "reconstruction_ref",
    "receipt_ref",
    "authority_state",
    "local_logical_time",
}


def _reject_nonfinite(value: str) -> None:
    del value
    raise MeshHold("HOLD_NATIVE_ADI_RESPONSE_NONFINITE")


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise MeshHold("HOLD_NATIVE_ADI_RESPONSE_DUPLICATE_KEY")
        value[key] = item
    return value


def native_adi_insert_url(value: object) -> str:
    if not isinstance(value, str):
        raise MeshHold("HOLD_NATIVE_ADI_URL_INVALID")
    parsed = urllib.parse.urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise MeshHold("HOLD_NATIVE_ADI_URL_INVALID")
    path = parsed.path.rstrip("/")
    if not path.endswith("/v1/adi/insert"):
        path = f"{path}/v1/adi/insert"
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def build_native_adi_record(
    *,
    source_node_ref: str,
    packet_id: str,
    packet_ref: str,
    observed_at: str,
    local_logical_time: int,
    snapshot_ref: str,
    capability_ref: str,
    reconstruction_ref: str,
    receipt_ref: str,
    authority_state: str,
) -> dict[str, object]:
    if isinstance(local_logical_time, bool) or not isinstance(local_logical_time, int) or local_logical_time < 1:
        raise MeshHold("HOLD_NATIVE_ADI_LOCAL_LOGICAL_TIME")
    absolute_time_slot = epoch_seconds(utc_parse(observed_at))
    if not 0 <= absolute_time_slot <= 2**63 - 1:
        raise MeshHold("HOLD_NATIVE_ADI_TIME_SLOT")
    refs = (packet_ref, snapshot_ref, capability_ref, reconstruction_ref, receipt_ref)
    if any(not isinstance(value, str) or ":" not in value for value in refs):
        raise MeshHold("HOLD_NATIVE_ADI_REFERENCE")
    if not isinstance(source_node_ref, str) or not source_node_ref.startswith("node:"):
        raise MeshHold("HOLD_NATIVE_ADI_SOURCE_NODE")
    if not isinstance(packet_id, str) or not packet_id:
        raise MeshHold("HOLD_NATIVE_ADI_PACKET_ID")
    packet_digest = packet_ref.removeprefix("sha256:")
    if len(packet_digest) != 64 or any(character not in "0123456789abcdef" for character in packet_digest):
        raise MeshHold("HOLD_NATIVE_ADI_PACKET_REF")
    node_coordinate = hashlib.sha256(source_node_ref.encode("utf-8")).hexdigest()[:16]
    record_id = f"gtmesh:{node_coordinate}:{packet_digest}"
    if _ID.fullmatch(record_id) is None:
        raise MeshHold("HOLD_NATIVE_ADI_RECORD_ID")
    snapshot_sha256 = snapshot_ref.removeprefix("sha256:")
    if len(snapshot_sha256) != 64 or any(character not in "0123456789abcdef" for character in snapshot_sha256):
        raise MeshHold("HOLD_NATIVE_ADI_SNAPSHOT_REF")
    payload: dict[str, object] = {
        "source_node_ref": source_node_ref,
        "packet_id": packet_id,
        "snapshot_sha256": snapshot_sha256,
        "capability_ref": capability_ref,
        "reconstruction_ref": reconstruction_ref,
        "receipt_ref": receipt_ref,
        "authority_state": authority_state,
        "local_logical_time": local_logical_time,
    }
    if set(payload) != _PAYLOAD_KEYS or len(require_core().canonical_json_bytes(payload)) > 64 * 1024:
        raise MeshHold("HOLD_NATIVE_ADI_PAYLOAD_CONTRACT")
    return {"id": record_id, "time_slot": absolute_time_slot, "payload": payload}


class NativeADIAdapter:
    def __init__(self, storage: MeshStorage, *, base_url: str, timeout_seconds: int = 10) -> None:
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int) or not 1 <= timeout_seconds <= 120:
            raise MeshHold("HOLD_NATIVE_ADI_TIMEOUT")
        self.storage = storage
        self.url = native_adi_insert_url(base_url)
        self.timeout_seconds = timeout_seconds

    def insert(self, record: Mapping[str, object]) -> dict[str, object]:
        if set(record) != {"id", "time_slot", "payload"}:
            raise MeshHold("HOLD_NATIVE_ADI_RECORD_SHAPE")
        raw = require_core().canonical_json_bytes(record)
        request = urllib.request.Request(
            self.url,
            data=raw,
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                response_raw = response.read(256 * 1024 + 1)
                if len(response_raw) > 256 * 1024:
                    raise MeshHold("HOLD_NATIVE_ADI_RESPONSE_TOO_LARGE")
        except urllib.error.HTTPError as exc:
            if exc.code == 422:
                raise MeshConflict("CONFLICT_NATIVE_ADI_APPEND_ONLY_RECORD") from exc
            raise MeshHold("HOLD_NATIVE_ADI_HTTP_UNAVAILABLE") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise MeshHold("HOLD_NATIVE_ADI_UNAVAILABLE") from exc
        try:
            parsed = json.loads(
                response_raw.decode("utf-8"),
                parse_constant=_reject_nonfinite,
                object_pairs_hook=_unique_pairs,
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MeshHold("HOLD_NATIVE_ADI_RESPONSE_JSON") from exc
        if not isinstance(parsed, Mapping) or set(parsed) != {"state", "record"} or parsed.get("state") != "PASS":
            raise MeshHold("HOLD_NATIVE_ADI_RESPONSE_SHAPE")
        returned = parsed.get("record")
        expected_keys = {"id", "time_slot", "collision_index", "spiral_position", "payload", "record_sha256"}
        if not isinstance(returned, Mapping) or set(returned) != expected_keys:
            raise MeshHold("HOLD_NATIVE_ADI_RESPONSE_RECORD_SHAPE")
        if (
            returned.get("id") != record.get("id")
            or returned.get("time_slot") != record.get("time_slot")
            or returned.get("payload") != record.get("payload")
        ):
            raise MeshConflict("CONFLICT_NATIVE_ADI_RESPONSE_BINDING")
        collision_index = returned.get("collision_index")
        record_sha256 = returned.get("record_sha256")
        if (
            isinstance(collision_index, bool)
            or not isinstance(collision_index, int)
            or collision_index < 0
            or not isinstance(record_sha256, str)
            or len(record_sha256) != 64
            or any(character not in "0123456789abcdef" for character in record_sha256)
        ):
            raise MeshHold("HOLD_NATIVE_ADI_RESPONSE_CONTRACT")
        receipt = {
            "schema_id": "W7TP_GT_MESH_NATIVE_ADI_RECEIPT_V21",
            "record_id": record["id"],
            "time_slot": record["time_slot"],
            "collision_index": collision_index,
            "record_sha256": record_sha256,
            "native_adi_url": self.url,
            "authority_state": "TOTAL_FIELD_AUTHORITY_ENDPOINT_RECEIPT",
        }
        receipt_ref = self.storage.put_artifact(receipt)
        self.storage.journal.append("native_adi_receipts", record_sha256, {**receipt, "receipt_ref": receipt_ref})
        return {**receipt, "receipt_ref": receipt_ref, "state": "PASS_NATIVE_ADI_INSERT"}

    def _queue(self, record: Mapping[str, object], *, reason_code: str, attempt: int) -> dict[str, object]:
        record_ref = self.storage.put_artifact(dict(record))
        queued = {
            "schema_id": "W7TP_GT_MESH_NATIVE_ADI_OUTBOX_EVENT_V21",
            "state": "QUEUED_FOR_RETRY",
            "record_ref": record_ref,
            "native_adi_url": self.url,
            "attempt": attempt,
            "reason_code": reason_code,
            "queued_at": utc_text(utc_now()),
        }
        key = f"{time.time_ns():020d}-{record_ref.removeprefix('sha256:')}"
        self.storage.journal.append("native_adi_outbox", key, queued)
        return queued

    def insert_or_queue(self, record: Mapping[str, object], *, attempt: int = 1) -> dict[str, object]:
        try:
            return self.insert(record)
        except MeshConflict:
            raise
        except MeshHold as exc:
            return self._queue(record, reason_code=exc.code, attempt=attempt)

    def retry_pending(self) -> list[dict[str, object]]:
        completed = {item.get("record_ref") for item in self.storage.journal.records("native_adi_outbox_done")}
        latest: dict[str, dict[str, object]] = {}
        for item in self.storage.journal.records("native_adi_outbox"):
            record_ref = item.get("record_ref")
            if isinstance(record_ref, str):
                latest[record_ref] = item
        results: list[dict[str, object]] = []
        for record_ref, item in latest.items():
            if record_ref in completed:
                continue
            record = self.storage.get_artifact(record_ref)
            result = self.insert_or_queue(record, attempt=int(item.get("attempt", 0)) + 1)
            results.append(result)
            if result.get("state") == "PASS_NATIVE_ADI_INSERT":
                done = {
                    "schema_id": "W7TP_GT_MESH_NATIVE_ADI_OUTBOX_DONE_V21",
                    "record_ref": record_ref,
                    "completed_at": utc_text(utc_now()),
                    "receipt_ref": result.get("receipt_ref"),
                }
                key = f"{time.time_ns():020d}-{record_ref.removeprefix('sha256:')}"
                self.storage.journal.append("native_adi_outbox_done", key, done)
        return results
