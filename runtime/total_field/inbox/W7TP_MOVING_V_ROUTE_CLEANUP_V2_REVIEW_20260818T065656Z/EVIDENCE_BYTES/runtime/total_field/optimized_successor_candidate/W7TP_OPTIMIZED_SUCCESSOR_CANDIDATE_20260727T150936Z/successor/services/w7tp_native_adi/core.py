"""Founder-native absolute-time ADI core and 8D reconstruction protocol.

The core maps time directly to absolute integer slots.  Every slot owns one
horizontal time slice containing multiple points; collisions are assigned by
the Founder-native center-out spiral order.  No tree, external space-filling
curve, vector similarity, or general-distance index is used.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import threading
import time
from bisect import bisect_left, bisect_right, insort
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


PROTOCOL_VERSION = "W7TP_8D_GENERATIVE_TRANSMISSION/1.1"
STATE_SCHEMA_VERSION = "W7TP_NATIVE_ADI_STATE/1.1"
PACKET_SCHEMA_VERSION = "W7TP_NATIVE_ADI_PACKET/1.1"
SERVICE_NAME = "W7TP_NATIVE_ADI_AGENT"
MAX_LOGICAL_TIME_UINT64 = (1 << 64) - 1
MAX_RESULTS = 10_000
MAX_PACKET_RECORDS = 250_000
MAX_PAYLOAD_BYTES = 64 * 1024
MAX_SNAPSHOT_ITEM_BYTES = 128 * 1024
MAX_SNAPSHOT_BYTES = 64 * 1024 * 1024
SNAPSHOT_TTL_SECONDS = 60 * 60
MAX_FUTURE_SKEW_SECONDS = 30
MAX_QUERY_OCCUPIED_SLOTS = 10_000
MAX_QUERY_RECORDS = 10_000
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
RECEIPT_REF_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,511}$")
FORBIDDEN_CREDENTIAL_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "client_secret",
        "credential",
        "id_token",
        "password",
        "private_key",
        "raw_credential",
        "raw_secret",
        "raw_token",
        "refresh_token",
        "secret",
        "token",
    }
)


class ADIError(ValueError):
    """Stable fail-closed product error without caller-value disclosure."""

    def __init__(self, reason_code: str, path: str = "$") -> None:
        self.reason_code = reason_code
        self.path = path
        self.dead_lettered = False
        self.dead_letter_receipt: Mapping[str, Any] | None = None
        super().__init__(f"{reason_code}:{path}")


def _normalize_json(value: Any, path: str = "$") -> Any:
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ADIError("NON_FINITE_NUMBER", path)
        return value
    if isinstance(value, list):
        return [_normalize_json(item, f"{path}[{index}]") for index, item in enumerate(value)]
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for raw_key, item in value.items():
            if not isinstance(raw_key, str):
                raise ADIError("JSON_OBJECT_KEY_INVALID", path)
            key = raw_key.strip()
            if not key:
                raise ADIError("JSON_OBJECT_KEY_INVALID", path)
            if key.casefold() in FORBIDDEN_CREDENTIAL_KEYS:
                raise ADIError("RAW_CREDENTIAL_FORBIDDEN", f"{path}.{key}")
            normalized[key] = _normalize_json(item, f"{path}.{key}")
        return normalized
    raise ADIError("NON_JSON_VALUE", path)


def canonical_json(value: Any) -> str:
    """Return the deterministic canonical JSON used by every state root."""

    return json.dumps(
        _normalize_json(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_bytes(value: Any) -> bytes:
    return canonical_json(value).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def spiral_position(index: int) -> tuple[int, int]:
    """Return the deterministic center-out Founder spiral coordinate."""

    if not isinstance(index, int) or isinstance(index, bool) or index < 0:
        raise ADIError("COLLISION_INDEX_INVALID", "$.collision_index")
    if index == 0:
        return 0, 0
    layer = (math.isqrt(index) + 1) // 2
    while (2 * layer + 1) ** 2 <= index:
        layer += 1
    side = 2 * layer
    maximum = (2 * layer + 1) ** 2 - 1
    distance = maximum - index
    if distance < side:
        return layer - distance, -layer
    if distance < 2 * side:
        return -layer, -layer + (distance - side)
    if distance < 3 * side:
        return -layer + (distance - 2 * side), layer
    return layer, layer - (distance - 3 * side)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _require_id(value: Any, path: str = "$.id") -> str:
    if not isinstance(value, str) or ID_PATTERN.fullmatch(value) is None:
        raise ADIError("RECORD_ID_INVALID", path)
    return value


def _require_time_slot(value: Any, path: str = "$.time_slot") -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
        or value > MAX_LOGICAL_TIME_UINT64
    ):
        raise ADIError("ABSOLUTE_TIME_SLOT_INVALID", path)
    return value


def _require_receipt_ref(value: Any, path: str = "$.authority_receipt_ref") -> str:
    if not isinstance(value, str) or RECEIPT_REF_PATTERN.fullmatch(value) is None:
        raise ADIError("AUTHORITY_RECEIPT_REF_INVALID", path)
    return value


def _require_sha256(value: Any, reason_code: str, path: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ADIError(reason_code, path)
    return value


def _require_timestamp(value: Any, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ADIError("TIMESTAMP_INVALID", path)
    return value


def _record_hash_basis(record: Mapping[str, Any]) -> dict[str, Any]:
    basis = dict(record)
    basis.pop("record_sha256", None)
    return _normalize_json(basis)


def _packet_hash_basis(packet: Mapping[str, Any]) -> dict[str, Any]:
    basis = dict(packet)
    basis.pop("packet_root", None)
    return _normalize_json(basis)


def _event_hash_basis(event: Mapping[str, Any]) -> dict[str, Any]:
    basis = dict(event)
    basis.pop("event_sha256", None)
    return _normalize_json(basis)


class SpacetimeADI:
    """Thread-safe absolute-time buckets with native spiral collision order."""

    def __init__(
        self,
        state_dir: str | Path | None = None,
        *,
        authority_receipt_verifier: Callable[[str, str], bool] | None = None,
        dead_letter_writer: Callable[..., Mapping[str, Any]] | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._lock = threading.RLock()
        self._records: dict[str, dict[str, Any]] = {}
        self._slots: dict[int, list[str]] = {}
        self._occupied_slots: list[int] = []
        self._tombstoned_refs: set[str] = set()
        self._slot_next_collision_index: dict[int, int] = {}
        self._consumed_authority_receipts: set[str] = set()
        self._authority_receipt_verifier = authority_receipt_verifier
        self._dead_letter_writer = dead_letter_writer
        self._clock = clock
        self._metrics = {
            "insert_requests": 0,
            "search_requests": 0,
            "packet_requests": 0,
            "reconstruct_requests": 0,
            "rejected_requests": 0,
        }
        self._state_dir = Path(state_dir).expanduser().resolve() if state_dir else None
        self._snapshot_path = self._state_dir / "snapshot.json" if self._state_dir else None
        self._event_path = self._state_dir / "events.jsonl" if self._state_dir else None
        self._event_sequence = 0
        self._last_event_sha256: str | None = None
        if self._state_dir is not None:
            self._state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            self._load_persistent_state()

    def _dead_letter(
        self,
        error: ADIError,
        operation: str,
        *,
        packet_ref: str | None = None,
        authority_receipt_ref: str | None = None,
    ) -> None:
        if error.dead_lettered:
            return
        if self._dead_letter_writer is not None:
            receipt = self._dead_letter_writer(
                reason=error.reason_code,
                source=f"{SERVICE_NAME}:{operation}",
                retry_scope="verify_or_reconstruct_only",
                packet_ref=packet_ref,
                reconstruction_required=operation == "RECONSTRUCT",
                authority_receipt_ref=authority_receipt_ref,
                error_path=error.path,
            )
            error.dead_letter_receipt = _normalize_json(dict(receipt))
        error.dead_lettered = True

    def record_rejection(self, error: ADIError, operation: str) -> None:
        """Route an HTTP-layer rejection through the configured existing writer."""

        with self._lock:
            self._metrics["rejected_requests"] += 1
            self._dead_letter(error, operation)

    @staticmethod
    def _record_sort_key(record: Mapping[str, Any]) -> tuple[int, int, str]:
        return (
            int(record["logical_time_uint64"]),
            int(record["collision_index"]),
            str(record["id"]),
        )

    def _build_record(
        self,
        record_id: Any,
        time_slot: Any,
        payload: Any,
        collision_index: int,
    ) -> dict[str, Any]:
        safe_id = _require_id(record_id)
        safe_slot = _require_time_slot(time_slot)
        safe_payload = _normalize_json(payload, "$.payload")
        if not isinstance(safe_payload, Mapping):
            raise ADIError("PAYLOAD_OBJECT_REQUIRED", "$.payload")
        if len(canonical_bytes(safe_payload)) > MAX_PAYLOAD_BYTES:
            raise ADIError("PAYLOAD_TOO_LARGE", "$.payload")
        x, y = spiral_position(collision_index)
        record: dict[str, Any] = {
            "type_tag": "W7TP_NATIVE_ADI_RECORD",
            "id": safe_id,
            "time_slot": safe_slot,
            "logical_time_uint64": safe_slot,
            "collision_index": collision_index,
            "spiral_position": {"x": x, "y": y},
            "payload": dict(safe_payload),
        }
        record["record_sha256"] = canonical_sha256(record)
        if len(canonical_bytes(record)) > MAX_SNAPSHOT_ITEM_BYTES:
            raise ADIError("SNAPSHOT_ITEM_TOO_LARGE", "$.record")
        return record

    def _validate_supplied_record(self, supplied: Mapping[str, Any]) -> dict[str, Any]:
        expected_keys = {
            "type_tag",
            "id",
            "time_slot",
            "logical_time_uint64",
            "collision_index",
            "spiral_position",
            "payload",
            "record_sha256",
        }
        if not isinstance(supplied, Mapping) or set(supplied) != expected_keys:
            raise ADIError("RECORD_SHAPE_INVALID")
        if supplied.get("type_tag") != "W7TP_NATIVE_ADI_RECORD":
            raise ADIError("RECORD_TYPE_TAG_INVALID", "$.type_tag")
        if supplied.get("logical_time_uint64") != supplied.get("time_slot"):
            raise ADIError("LOGICAL_TIME_MISMATCH", "$.logical_time_uint64")
        collision_index = supplied.get("collision_index")
        if not isinstance(collision_index, int) or isinstance(collision_index, bool):
            raise ADIError("COLLISION_INDEX_INVALID", "$.collision_index")
        rebuilt = self._build_record(
            supplied.get("id"),
            supplied.get("time_slot"),
            supplied.get("payload"),
            collision_index,
        )
        if rebuilt != _normalize_json(dict(supplied)):
            raise ADIError("RECORD_INTEGRITY_MISMATCH")
        return rebuilt

    def _accept_record(self, record: Mapping[str, Any]) -> bool:
        validated = self._validate_supplied_record(record)
        record_id = validated["id"]
        existing = self._records.get(record_id)
        if existing is not None:
            if existing != validated:
                raise ADIError("APPEND_ONLY_RECORD_CONFLICT", "$.id")
            return False
        slot = int(validated["time_slot"])
        bucket = self._slots.get(slot)
        if bucket is None:
            bucket = []
            self._slots[slot] = bucket
            insort(self._occupied_slots, slot)
        if any(
            self._records[item]["collision_index"] == validated["collision_index"]
            for item in bucket
        ):
            raise ADIError("SPIRAL_COLLISION_ORDER_MISMATCH", "$.collision_index")
        bucket.append(record_id)
        bucket.sort(key=lambda item: int(self._records.get(item, validated)["collision_index"]))
        self._records[record_id] = validated
        self._slot_next_collision_index[slot] = max(
            self._slot_next_collision_index.get(slot, 0),
            int(validated["collision_index"]) + 1,
        )
        return True

    def insert(self, record_id: Any, time_slot: Any, payload: Any) -> dict[str, Any]:
        with self._lock:
            self._metrics["insert_requests"] += 1
            try:
                safe_id = _require_id(record_id)
                safe_slot = _require_time_slot(time_slot)
                if safe_id in self._tombstoned_refs:
                    raise ADIError("DELETED_RECORD_REF_REUSE_FORBIDDEN", "$.id")
                existing = self._records.get(safe_id)
                if existing is not None:
                    candidate = self._build_record(
                        safe_id,
                        safe_slot,
                        payload,
                        int(existing["collision_index"]),
                    )
                    if candidate != existing:
                        raise ADIError("APPEND_ONLY_RECORD_CONFLICT", "$.id")
                    return dict(existing)
                record = self._build_record(
                    safe_id,
                    safe_slot,
                    payload,
                    self._slot_next_collision_index.get(safe_slot, 0),
                )
                if self._state_dir is not None:
                    self._append_event("INSERT", {"record": record})
                self._accept_record(record)
                self._persist_snapshot()
                return dict(record)
            except ADIError as exc:
                self._metrics["rejected_requests"] += 1
                self._dead_letter(exc, "INSERT")
                raise

    def search(
        self,
        start_slot: Any,
        end_slot: Any,
        limit: Any = 100,
        query_budget: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        with self._lock:
            self._metrics["search_requests"] += 1
            try:
                start = _require_time_slot(start_slot, "$.start_slot")
                end = _require_time_slot(end_slot, "$.end_slot")
                if end < start:
                    raise ADIError("TIME_RANGE_INVALID")
                if (
                    not isinstance(limit, int)
                    or isinstance(limit, bool)
                    or limit < 1
                    or limit > MAX_RESULTS
                ):
                    raise ADIError("RESULT_LIMIT_INVALID", "$.limit")
                budget = dict(query_budget or {})
                if set(budget) - {"max_occupied_slots", "max_records"}:
                    raise ADIError("QUERY_BUDGET_INVALID", "$.query_budget")
                max_slots = budget.get("max_occupied_slots", MAX_QUERY_OCCUPIED_SLOTS)
                max_records = budget.get("max_records", MAX_QUERY_RECORDS)
                if (
                    not isinstance(max_slots, int)
                    or isinstance(max_slots, bool)
                    or max_slots < 1
                    or max_slots > MAX_QUERY_OCCUPIED_SLOTS
                    or not isinstance(max_records, int)
                    or isinstance(max_records, bool)
                    or max_records < 1
                    or max_records > MAX_QUERY_RECORDS
                    or limit > max_records
                ):
                    raise ADIError("QUERY_BUDGET_INVALID", "$.query_budget")
                left = bisect_left(self._occupied_slots, start)
                right = bisect_right(self._occupied_slots, end)
                occupied = self._occupied_slots[left:right]
                if len(occupied) > max_slots:
                    raise ADIError("QUERY_OCCUPIED_SLOT_BUDGET_EXCEEDED")
                result: list[dict[str, Any]] = []
                scanned_records = 0
                for slot in occupied:
                    for record_id in self._slots[slot]:
                        if record_id in self._tombstoned_refs:
                            continue
                        scanned_records += 1
                        if scanned_records > max_records:
                            raise ADIError("QUERY_RECORD_BUDGET_EXCEEDED")
                        result.append(dict(self._records[record_id]))
                        if len(result) == limit:
                            return result
                return result
            except ADIError as exc:
                self._metrics["rejected_requests"] += 1
                self._dead_letter(exc, "SEARCH")
                raise

    def _selected_records(self, ids: Sequence[str] | None = None) -> list[dict[str, Any]]:
        if ids is None:
            records = [
                record
                for record_id, record in self._records.items()
                if record_id not in self._tombstoned_refs
            ]
        else:
            if isinstance(ids, (str, bytes)) or len(ids) > MAX_PACKET_RECORDS:
                raise ADIError("PACKET_ID_SET_INVALID", "$.ids")
            normalized_ids = [_require_id(item, f"$.ids[{index}]") for index, item in enumerate(ids)]
            if len(set(normalized_ids)) != len(normalized_ids):
                raise ADIError("PACKET_ID_SET_DUPLICATE", "$.ids")
            missing = [
                item
                for item in normalized_ids
                if item not in self._records or item in self._tombstoned_refs
            ]
            if missing:
                raise ADIError("PACKET_RECORD_NOT_FOUND", "$.ids")
            records = [self._records[item] for item in normalized_ids]
        if len(records) > MAX_PACKET_RECORDS:
            raise ADIError("PACKET_RECORD_LIMIT_EXCEEDED")
        return [dict(item) for item in sorted(records, key=self._record_sort_key)]

    @staticmethod
    def _state_document(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        return {
            "type_tag": "W7TP_NATIVE_ADI_STATE",
            "protocol_version": PROTOCOL_VERSION,
            "schema_version": STATE_SCHEMA_VERSION,
            "records": [_normalize_json(dict(item)) for item in records],
        }

    def export_state(self, ids: Sequence[str] | None = None) -> dict[str, Any]:
        with self._lock:
            return self._state_document(self._selected_records(ids))

    def state_sha256(self, ids: Sequence[str] | None = None) -> str:
        return canonical_sha256(self.export_state(ids))

    def record_hashes(self) -> dict[str, str]:
        with self._lock:
            return {
                record_id: str(record["record_sha256"])
                for record_id, record in self._records.items()
                if record_id not in self._tombstoned_refs
            }

    def packet(
        self,
        ids: Sequence[str] | None = None,
        receiver_lookup: Mapping[str, str] | None = None,
        parent_snapshot_ref: str | None = None,
        snapshot_created_at_unix_seconds: int | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            self._metrics["packet_requests"] += 1
            try:
                records = self._selected_records(ids)
                lookup = dict(receiver_lookup or {})
                for record_id, digest in lookup.items():
                    _require_id(record_id, "$.receiver_lookup.id")
                    _require_sha256(
                        digest,
                        "RECEIVER_LOOKUP_HASH_INVALID",
                        f"$.receiver_lookup.{record_id}",
                    )
                if lookup and parent_snapshot_ref is None:
                    raise ADIError("PARENT_SNAPSHOT_REF_REQUIRED", "$.parent_snapshot_ref")
                if parent_snapshot_ref is not None:
                    parent_snapshot_ref = _require_receipt_ref(
                        parent_snapshot_ref, "$.parent_snapshot_ref"
                    )
                source_state = self._state_document(records)
                source_bytes = canonical_bytes(source_state)
                if len(source_bytes) > MAX_SNAPSHOT_BYTES:
                    raise ADIError("SNAPSHOT_BYTE_BUDGET_EXCEEDED", "$.source")
                source_sha256 = hashlib.sha256(source_bytes).hexdigest()
                id_set_sha256 = canonical_sha256(sorted(record["id"] for record in records))
                reference_entries: list[dict[str, str]] = []
                changed_atoms: list[dict[str, Any]] = []
                for record in records:
                    record_id = str(record["id"])
                    delivery = (
                        "REFERENCE"
                        if lookup.get(record_id) == record["record_sha256"]
                        else "STATE_ATOM"
                    )
                    reference_entries.append(
                        {
                            "id": record_id,
                            "record_sha256": str(record["record_sha256"]),
                            "delivery": delivery,
                        }
                    )
                    if delivery == "STATE_ATOM":
                        changed_atoms.append(record)
                reference_lookup = {
                    "mode": "LOCAL_ID_SHA256_LOOKUP",
                    "entries": reference_entries,
                }
                delta = {
                    "mode": "PARENT_SNAPSHOT_DELTA",
                    "parent_snapshot_ref": parent_snapshot_ref,
                    "changed_atom_count": len(changed_atoms),
                    "changed_atoms": changed_atoms,
                    "deleted_refs": sorted(set(lookup) - {str(record["id"]) for record in records}),
                }
                slice_counts = [
                    {"logical_time_uint64": slot, "point_count": len(self._slots[slot])}
                    for slot in sorted({int(record["logical_time_uint64"]) for record in records})
                ]
                conditions = {
                    "logical_time_mapping": "DIRECT_UINT64_SLOT",
                    "collision_resolution": "FOUNDER_NATIVE_CENTER_OUT_SPIRAL",
                    "reference_match": "ID_AND_RECORD_SHA256",
                    "missing_reference": "REQUIRE_STATE_ATOM_FAIL_CLOSED",
                    "target_state_sha256": source_sha256,
                    "target_id_set_sha256": id_set_sha256,
                }
                reference_sha256 = canonical_sha256(reference_lookup)
                delta_sha256 = canonical_sha256(delta)
                verification_root = canonical_sha256(
                    {
                        "source_state_sha256": source_sha256,
                        "source_id_set_sha256": id_set_sha256,
                        "reference_lookup_sha256": reference_sha256,
                        "delta_sha256": delta_sha256,
                        "reconstruction_conditions_sha256": canonical_sha256(conditions),
                    }
                )
                created_at = _require_timestamp(
                    int(self._clock())
                    if snapshot_created_at_unix_seconds is None
                    else snapshot_created_at_unix_seconds,
                    "$.snapshot.created_at_unix_seconds",
                )
                packet: dict[str, Any] = {
                    "type_tag": "W7TP_NATIVE_ADI_PACKET",
                    "protocol_version": PROTOCOL_VERSION,
                    "schema_version": PACKET_SCHEMA_VERSION,
                    "packet_type": "W7TP_NATIVE_ADI_8D_DYNAMIC_CONTEXT",
                    "total_field_decision": "CANDIDATE",
                    "dynamic_context_8d": {
                        "D1": {"intent": "RECONSTRUCT_EQUIVALENT_NATIVE_ADI_STATE"},
                        "D2": {"state_sha256": source_sha256, "record_count": len(records)},
                        "D3": {"coordinate": "LOGICAL_TIME_UINT64_HORIZONTAL_SLICES", "slices": slice_counts},
                        "D4": {"reference_lookup_sha256": reference_sha256, "delta_sha256": delta_sha256},
                        "D5": {"execution": "LOCAL_RECONSTRUCTION_CANDIDATE"},
                        "D6": {"reconstruction_conditions": conditions},
                        "D7": {"hard_risk": False, "redlines": []},
                        "D8": {"verification_root": verification_root, "decision": "CANDIDATE"},
                    },
                    "source": {
                        "state_schema_version": STATE_SCHEMA_VERSION,
                        "record_count": len(records),
                        "source_bytes": len(source_bytes),
                        "state_sha256": source_sha256,
                        "id_set_sha256": id_set_sha256,
                    },
                    "snapshot": {
                        "type_tag": "W7TP_NATIVE_ADI_TRANSFER_SNAPSHOT",
                        "created_at_unix_seconds": created_at,
                        "expires_at_unix_seconds": created_at + SNAPSHOT_TTL_SECONDS,
                        "ttl_seconds": SNAPSHOT_TTL_SECONDS,
                        "byte_budget": MAX_SNAPSHOT_BYTES,
                        "single_item_byte_limit": MAX_SNAPSHOT_ITEM_BYTES,
                    },
                    "reference_lookup": reference_lookup,
                    "delta": delta,
                    "reconstruction_conditions": conditions,
                    "verification": {
                        "source_state_sha256": source_sha256,
                        "source_id_set_sha256": id_set_sha256,
                        "reference_lookup_sha256": reference_sha256,
                        "delta_sha256": delta_sha256,
                        "verification_root": verification_root,
                    },
                    "risk_assessment": {"hard_risk": False, "redlines": []},
                }
                packet["packet_root"] = canonical_sha256(packet)
                if len(canonical_bytes(packet)) > MAX_SNAPSHOT_BYTES:
                    raise ADIError("SNAPSHOT_BYTE_BUDGET_EXCEEDED", "$.packet")
                return packet
            except ADIError as exc:
                self._metrics["rejected_requests"] += 1
                self._dead_letter(exc, "PACKET")
                raise

    def _validate_packet(self, packet: Mapping[str, Any]) -> dict[str, Any]:
        expected_keys = {
            "type_tag",
            "protocol_version",
            "schema_version",
            "packet_type",
            "total_field_decision",
            "dynamic_context_8d",
            "source",
            "snapshot",
            "reference_lookup",
            "delta",
            "reconstruction_conditions",
            "verification",
            "risk_assessment",
            "packet_root",
        }
        if not isinstance(packet, Mapping) or set(packet) != expected_keys:
            raise ADIError("PACKET_SCHEMA_INVALID")
        normalized = _normalize_json(dict(packet))
        if normalized["type_tag"] != "W7TP_NATIVE_ADI_PACKET":
            raise ADIError("PACKET_TYPE_TAG_INVALID")
        if normalized["protocol_version"] != PROTOCOL_VERSION:
            raise ADIError("PACKET_PROTOCOL_VERSION_INVALID")
        if normalized["schema_version"] != PACKET_SCHEMA_VERSION:
            raise ADIError("PACKET_SCHEMA_VERSION_INVALID")
        if normalized["packet_type"] != "W7TP_NATIVE_ADI_8D_DYNAMIC_CONTEXT":
            raise ADIError("PACKET_TYPE_INVALID")
        if normalized["total_field_decision"] != "CANDIDATE":
            raise ADIError("PACKET_CANDIDATE_DECISION_REQUIRED")
        context = normalized["dynamic_context_8d"]
        if not isinstance(context, Mapping) or set(context) != {f"D{index}" for index in range(1, 9)}:
            raise ADIError("PACKET_8D_CONTEXT_INVALID")
        if normalized["packet_root"] != canonical_sha256(_packet_hash_basis(normalized)):
            raise ADIError("PACKET_ROOT_MISMATCH")
        snapshot = normalized["snapshot"]
        if not isinstance(snapshot, Mapping) or set(snapshot) != {
            "type_tag",
            "created_at_unix_seconds",
            "expires_at_unix_seconds",
            "ttl_seconds",
            "byte_budget",
            "single_item_byte_limit",
        }:
            raise ADIError("SNAPSHOT_METADATA_INVALID", "$.snapshot")
        if snapshot.get("type_tag") != "W7TP_NATIVE_ADI_TRANSFER_SNAPSHOT":
            raise ADIError("SNAPSHOT_TYPE_TAG_INVALID", "$.snapshot.type_tag")
        created_at = _require_timestamp(
            snapshot.get("created_at_unix_seconds"),
            "$.snapshot.created_at_unix_seconds",
        )
        expires_at = _require_timestamp(
            snapshot.get("expires_at_unix_seconds"),
            "$.snapshot.expires_at_unix_seconds",
        )
        if (
            snapshot.get("ttl_seconds") != SNAPSHOT_TTL_SECONDS
            or expires_at - created_at != SNAPSHOT_TTL_SECONDS
            or snapshot.get("byte_budget") != MAX_SNAPSHOT_BYTES
            or snapshot.get("single_item_byte_limit") != MAX_SNAPSHOT_ITEM_BYTES
        ):
            raise ADIError("SNAPSHOT_BUDGET_OR_TTL_INVALID", "$.snapshot")
        now = int(self._clock())
        if created_at > now + MAX_FUTURE_SKEW_SECONDS:
            raise ADIError("TIMESTAMP_FUTURE", "$.snapshot.created_at_unix_seconds")
        if expires_at < now:
            raise ADIError("TIMESTAMP_PAST", "$.snapshot.expires_at_unix_seconds")
        if len(canonical_bytes(normalized)) > MAX_SNAPSHOT_BYTES:
            raise ADIError("SNAPSHOT_BYTE_BUDGET_EXCEEDED", "$.packet")
        source = normalized["source"]
        if not isinstance(source, Mapping) or source.get("state_schema_version") != STATE_SCHEMA_VERSION:
            raise ADIError("PACKET_SOURCE_SCHEMA_INVALID")
        lookup = normalized["reference_lookup"]
        if not isinstance(lookup, Mapping) or lookup.get("mode") != "LOCAL_ID_SHA256_LOOKUP":
            raise ADIError("PACKET_REFERENCE_LOOKUP_INVALID")
        entries = lookup.get("entries")
        if not isinstance(entries, list):
            raise ADIError("PACKET_REFERENCE_LOOKUP_REQUIRED")
        if source.get("record_count") != len(entries):
            raise ADIError("PACKET_RECORD_COUNT_MISMATCH")
        seen: set[str] = set()
        for index, entry in enumerate(entries):
            if not isinstance(entry, Mapping) or set(entry) != {"id", "record_sha256", "delivery"}:
                raise ADIError("PACKET_REFERENCE_ENTRY_INVALID", f"$.reference_lookup.entries[{index}]")
            record_id = _require_id(entry.get("id"), f"$.reference_lookup.entries[{index}].id")
            digest = entry.get("record_sha256")
            if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
                raise ADIError("PACKET_REFERENCE_HASH_INVALID", f"$.reference_lookup.entries[{index}]")
            if entry.get("delivery") not in {"REFERENCE", "STATE_ATOM"}:
                raise ADIError("PACKET_DELIVERY_MODE_INVALID", f"$.reference_lookup.entries[{index}]")
            if record_id in seen:
                raise ADIError("PACKET_REFERENCE_DUPLICATE", f"$.reference_lookup.entries[{index}]")
            seen.add(record_id)
        delta = normalized["delta"]
        if not isinstance(delta, Mapping) or set(delta) != {
            "mode",
            "parent_snapshot_ref",
            "changed_atom_count",
            "changed_atoms",
            "deleted_refs",
        } or delta.get("mode") != "PARENT_SNAPSHOT_DELTA":
            raise ADIError("PACKET_DELTA_INVALID")
        parent_snapshot_ref = delta.get("parent_snapshot_ref")
        if parent_snapshot_ref is not None:
            _require_receipt_ref(parent_snapshot_ref, "$.delta.parent_snapshot_ref")
        atoms = delta.get("changed_atoms")
        if not isinstance(atoms, list) or delta.get("changed_atom_count") != len(atoms):
            raise ADIError("PACKET_STATE_ATOMS_INVALID")
        deleted_refs = delta.get("deleted_refs")
        if not isinstance(deleted_refs, list):
            raise ADIError("PACKET_DELETED_REFS_INVALID")
        normalized_deleted = [
            _require_id(item, f"$.delta.deleted_refs[{index}]")
            for index, item in enumerate(deleted_refs)
        ]
        if normalized_deleted != sorted(set(normalized_deleted)):
            raise ADIError("PACKET_DELETED_REFS_INVALID")
        if parent_snapshot_ref is None and (
            any(entry.get("delivery") == "REFERENCE" for entry in entries)
            or normalized_deleted
        ):
            raise ADIError("PARENT_SNAPSHOT_REF_BINDING_INVALID")
        conditions = normalized["reconstruction_conditions"]
        if not isinstance(conditions, Mapping) or not conditions:
            raise ADIError("PACKET_RECONSTRUCTION_CONDITIONS_REQUIRED")
        verification = normalized["verification"]
        if not isinstance(verification, Mapping) or not verification.get("verification_root"):
            raise ADIError("PACKET_VERIFICATION_ROOT_REQUIRED")
        if verification.get("reference_lookup_sha256") != canonical_sha256(lookup):
            raise ADIError("PACKET_REFERENCE_ROOT_MISMATCH")
        if verification.get("delta_sha256") != canonical_sha256(delta):
            raise ADIError("PACKET_DELTA_ROOT_MISMATCH")
        expected_verification_root = canonical_sha256(
            {
                "source_state_sha256": verification.get("source_state_sha256"),
                "source_id_set_sha256": verification.get("source_id_set_sha256"),
                "reference_lookup_sha256": verification.get("reference_lookup_sha256"),
                "delta_sha256": verification.get("delta_sha256"),
                "reconstruction_conditions_sha256": canonical_sha256(conditions),
            }
        )
        if verification.get("verification_root") != expected_verification_root:
            raise ADIError("PACKET_VERIFICATION_ROOT_MISMATCH")
        risk = normalized["risk_assessment"]
        if not isinstance(risk, Mapping) or risk.get("hard_risk") is not False or risk.get("redlines") != []:
            raise ADIError("PACKET_HARD_RISK_BLOCKED")
        return normalized

    def reconstruct(
        self,
        packet: Mapping[str, Any],
        authority_receipt_ref: Any,
    ) -> dict[str, Any]:
        with self._lock:
            self._metrics["reconstruct_requests"] += 1
            packet_ref = packet.get("packet_root") if isinstance(packet, Mapping) else None
            safe_receipt_ref: str | None = None
            try:
                verified_packet = self._validate_packet(packet)
                packet_ref = str(verified_packet["packet_root"])
                safe_receipt_ref = _require_receipt_ref(authority_receipt_ref)
                if safe_receipt_ref in self._consumed_authority_receipts:
                    raise ADIError("AUTHORITY_RECEIPT_REPLAY", "$.authority_receipt_ref")
                if self._authority_receipt_verifier is None:
                    raise ADIError("AUTHORITY_RECEIPT_VERIFIER_UNAVAILABLE")
                if not self._authority_receipt_verifier(safe_receipt_ref, packet_ref):
                    raise ADIError("AUTHORITY_RECEIPT_INVALID", "$.authority_receipt_ref")
                entries = verified_packet["reference_lookup"]["entries"]
                atoms: dict[str, dict[str, Any]] = {}
                for raw_atom in verified_packet["delta"]["changed_atoms"]:
                    atom = self._validate_supplied_record(raw_atom)
                    if atom["id"] in atoms:
                        raise ADIError("PACKET_STATE_ATOM_DUPLICATE")
                    atoms[atom["id"]] = atom
                resolved: list[dict[str, Any]] = []
                used_atoms: set[str] = set()
                for entry in entries:
                    record_id = entry["id"]
                    expected_hash = entry["record_sha256"]
                    if entry["delivery"] == "REFERENCE":
                        record = self._records.get(record_id)
                        if record is None or record["record_sha256"] != expected_hash:
                            raise ADIError("REFERENCE_LOOKUP_MISS", f"$.reference_lookup.{record_id}")
                    else:
                        record = atoms.get(record_id)
                        if record is None or record["record_sha256"] != expected_hash:
                            raise ADIError("REQUIRED_STATE_ATOM_MISSING", f"$.delta.{record_id}")
                        used_atoms.add(record_id)
                    resolved.append(dict(record))
                if used_atoms != set(atoms):
                    raise ADIError("UNREFERENCED_STATE_ATOM_FORBIDDEN")
                deleted_refs = set(verified_packet["delta"]["deleted_refs"])
                if deleted_refs & {entry["id"] for entry in entries}:
                    raise ADIError("DELETED_REF_STILL_PRESENT")
                ordered = sorted(resolved, key=self._record_sort_key)
                reconstructed_state = self._state_document(ordered)
                reconstructed_bytes = canonical_bytes(reconstructed_state)
                reconstructed_sha256 = hashlib.sha256(reconstructed_bytes).hexdigest()
                reconstructed_ids_sha256 = canonical_sha256(sorted(record["id"] for record in ordered))
                source = verified_packet["source"]
                conditions = verified_packet["reconstruction_conditions"]
                checks = {
                    "schema_valid": True,
                    "source_hash_equals_reconstructed_hash": reconstructed_sha256 == source["state_sha256"],
                    "id_set_equivalent": reconstructed_ids_sha256 == source["id_set_sha256"],
                    "byte_equivalent": len(reconstructed_bytes) == source["source_bytes"],
                    "reference_or_lookup_present": bool(entries),
                    "reconstruction_conditions_present": bool(conditions),
                    "protocol_and_schema_present": True,
                    "verification_root_present": bool(verified_packet["verification"]["verification_root"]),
                    "packet_root_integrity_only": bool(verified_packet["packet_root"]),
                    "authority_receipt_bound": True,
                    "hard_risk_clear": True,
                }
                if not all(checks.values()):
                    raise ADIError("TOTAL_FIELD_RECONSTRUCTION_VERIFICATION_FAILED")
                newly_accepted = [record for record in ordered if record["id"] not in self._records]
                if self._state_dir is not None:
                    self._append_event(
                        "RECONSTRUCT_ALLOW",
                        {
                            "source_packet_root": verified_packet["packet_root"],
                            "authority_receipt_ref": safe_receipt_ref,
                            "deleted_refs": sorted(deleted_refs),
                            "records": newly_accepted,
                        },
                    )
                for record in ordered:
                    self._accept_record(record)
                self._tombstoned_refs.update(deleted_refs)
                self._consumed_authority_receipts.add(safe_receipt_ref)
                self._persist_snapshot()
                return {
                    "state": "PASS_RECONSTRUCTED_EQUIVALENT_STATE",
                    "total_field_decision": "ALLOW",
                    "source_sha256": source["state_sha256"],
                    "reconstructed_sha256": reconstructed_sha256,
                    "source_bytes": source["source_bytes"],
                    "reconstructed_bytes": len(reconstructed_bytes),
                    "record_count": len(ordered),
                    "query_result_count": len(ordered),
                    "checks": checks,
                    "authority_receipt_ref": safe_receipt_ref,
                    "packet_root": packet_ref,
                    "packet_root_role": "INTEGRITY_ONLY",
                    "reconstructed_state": reconstructed_state,
                }
            except ADIError as exc:
                self._metrics["rejected_requests"] += 1
                self._dead_letter(
                    exc,
                    "RECONSTRUCT",
                    packet_ref=packet_ref if isinstance(packet_ref, str) else None,
                    authority_receipt_ref=safe_receipt_ref,
                )
                raise

    def metrics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "service": SERVICE_NAME,
                "record_count": len(self._records),
                "time_slice_count": len(self._slots),
                "state_sha256": self.state_sha256(),
                "evidence_root": self.evidence_root(),
                **self._metrics,
            }

    def evidence_root(self) -> str:
        with self._lock:
            return self._last_event_sha256 or self.state_sha256()

    def _append_event(self, event_type: str, payload: Mapping[str, Any]) -> None:
        if self._event_path is None:
            return
        event: dict[str, Any] = {
            "protocol_version": PROTOCOL_VERSION,
            "schema_version": "W7TP_NATIVE_ADI_APPEND_ONLY_EVENT/1.0",
            "sequence": self._event_sequence + 1,
            "observed_at": _utc_now(),
            "event_type": event_type,
            "previous_event_sha256": self._last_event_sha256,
            "payload": _normalize_json(dict(payload)),
        }
        event["event_sha256"] = canonical_sha256(event)
        descriptor = os.open(
            self._event_path,
            os.O_APPEND | os.O_CREAT | os.O_WRONLY,
            0o600,
        )
        try:
            os.write(descriptor, canonical_bytes(event) + b"\n")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        self._event_sequence = int(event["sequence"])
        self._last_event_sha256 = str(event["event_sha256"])

    def _persist_snapshot(self) -> None:
        if self._snapshot_path is None:
            return
        snapshot = {
            "type_tag": "W7TP_NATIVE_ADI_PERSISTENT_SNAPSHOT",
            "protocol_version": PROTOCOL_VERSION,
            "schema_version": STATE_SCHEMA_VERSION,
            "created_at_unix_seconds": int(self._clock()),
            "event_sequence": self._event_sequence,
            "last_event_sha256": self._last_event_sha256,
            "state": self._state_document(self._selected_records()),
            "tombstoned_refs": sorted(self._tombstoned_refs),
            "consumed_authority_receipt_refs": sorted(self._consumed_authority_receipts),
            "slot_next_collision_index": {
                str(slot): value
                for slot, value in sorted(self._slot_next_collision_index.items())
            },
        }
        snapshot["state_sha256"] = canonical_sha256(snapshot["state"])
        encoded = canonical_bytes(snapshot) + b"\n"
        if len(encoded) > MAX_SNAPSHOT_BYTES:
            raise ADIError("SNAPSHOT_BYTE_BUDGET_EXCEEDED", "$.persistent_snapshot")
        temporary = self._snapshot_path.with_suffix(".json.tmp")
        descriptor = os.open(temporary, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
        try:
            os.write(descriptor, encoded)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.replace(temporary, self._snapshot_path)

    def _load_persistent_state(self) -> None:
        snapshot_sequence = 0
        if self._snapshot_path is not None and self._snapshot_path.exists():
            if self._snapshot_path.stat().st_size > MAX_SNAPSHOT_BYTES:
                raise ADIError("SNAPSHOT_BYTE_BUDGET_EXCEEDED", "$.persistent_snapshot")
            try:
                snapshot = json.loads(self._snapshot_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise ADIError("SNAPSHOT_READ_FAILED") from exc
            legacy_empty = (
                snapshot.get("protocol_version") == "W7TP_8D_GENERATIVE_TRANSMISSION/1.0"
                and snapshot.get("schema_version") == "W7TP_NATIVE_ADI_STATE/1.0"
                and snapshot.get("state", {}).get("records") == []
            )
            if not legacy_empty and (
                snapshot.get("protocol_version") != PROTOCOL_VERSION
                or snapshot.get("schema_version") != STATE_SCHEMA_VERSION
                or snapshot.get("type_tag") != "W7TP_NATIVE_ADI_PERSISTENT_SNAPSHOT"
                or snapshot.get("state_sha256") != canonical_sha256(snapshot.get("state"))
            ):
                raise ADIError("SNAPSHOT_INTEGRITY_MISMATCH")
            state = snapshot.get("state")
            if not isinstance(state, Mapping) or not isinstance(state.get("records"), list):
                raise ADIError("SNAPSHOT_STATE_INVALID")
            for record in state["records"]:
                self._accept_record(record)
            if not legacy_empty:
                self._tombstoned_refs = {
                    _require_id(item, "$.snapshot.tombstoned_refs")
                    for item in snapshot.get("tombstoned_refs", [])
                }
                self._consumed_authority_receipts = {
                    _require_receipt_ref(item, "$.snapshot.consumed_authority_receipt_refs")
                    for item in snapshot.get("consumed_authority_receipt_refs", [])
                }
                next_indices = snapshot.get("slot_next_collision_index", {})
                if not isinstance(next_indices, Mapping):
                    raise ADIError("SNAPSHOT_COLLISION_INDEX_INVALID")
                for raw_slot, raw_index in next_indices.items():
                    try:
                        slot = int(raw_slot)
                    except (TypeError, ValueError) as exc:
                        raise ADIError("SNAPSHOT_COLLISION_INDEX_INVALID") from exc
                    safe_slot = _require_time_slot(slot, "$.snapshot.slot_next_collision_index")
                    if not isinstance(raw_index, int) or isinstance(raw_index, bool) or raw_index < 0:
                        raise ADIError("SNAPSHOT_COLLISION_INDEX_INVALID")
                    self._slot_next_collision_index[safe_slot] = max(
                        self._slot_next_collision_index.get(safe_slot, 0), raw_index
                    )
            snapshot_sequence = int(snapshot.get("event_sequence", 0))
        replay_events: list[dict[str, Any]] = []
        previous_sha: str | None = None
        if self._event_path is not None and self._event_path.exists():
            try:
                lines = self._event_path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeError) as exc:
                raise ADIError("EVENT_LOG_READ_FAILED") from exc
            for index, line in enumerate(lines):
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ADIError("EVENT_LOG_JSON_INVALID", f"$.events[{index}]") from exc
                if (
                    event.get("sequence") != index + 1
                    or event.get("previous_event_sha256") != previous_sha
                    or event.get("event_sha256") != canonical_sha256(_event_hash_basis(event))
                ):
                    raise ADIError("EVENT_LOG_CHAIN_INVALID", f"$.events[{index}]")
                previous_sha = event["event_sha256"]
                if event["sequence"] > snapshot_sequence:
                    replay_events.append(event)
            self._event_sequence = len(lines)
            self._last_event_sha256 = previous_sha
        for event in replay_events:
            payload = event.get("payload", {})
            if event.get("event_type") == "INSERT":
                self._accept_record(payload.get("record"))
            elif event.get("event_type") == "RECONSTRUCT_ALLOW":
                for record in payload.get("records", []):
                    self._accept_record(record)
                self._tombstoned_refs.update(payload.get("deleted_refs", []))
                receipt_ref = payload.get("authority_receipt_ref")
                if receipt_ref:
                    self._consumed_authority_receipts.add(
                        _require_receipt_ref(receipt_ref, "$.event.authority_receipt_ref")
                    )
            elif event.get("event_type") != "EMPTY_STATE_CREATED":
                raise ADIError("EVENT_TYPE_INVALID")
        if self._snapshot_path is not None and not self._snapshot_path.exists():
            self._append_event("EMPTY_STATE_CREATED", {"record_count": 0})
        self._persist_snapshot()
