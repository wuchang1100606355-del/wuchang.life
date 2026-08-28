"""Pinned W7TP V2.1 bindings and fail-closed shared helpers.

This adapter intentionally does not carry a substitute canonicalizer, object
store, or delta implementation.  A deployment must carry the existing
``w7tp_runtime.state_field`` subset.  Missing or incompatible core modules are
therefore a HOLD, never a silent fallback.
"""

from __future__ import annotations

import calendar
import copy
import dataclasses
import datetime as dt
import re
from typing import Any, Callable


CANONICAL_ID = "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1"
CANONICAL_VERSION = "2.1"
CANONICAL_PATH = "docs/total_field/W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1.md"
CANONICAL_SHA256 = "e960d14254df083ffed711e2c44b76fc2075541716881bc3d1034cb26cffbaba"
PARENT_VERSION = "2.0"
PARENT_PATH = "docs/total_field/W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2.md"
PARENT_SHA256 = "a5281f229ced0943072cce373125be16f0d361b9352a71094ad5450a6022d5d0"
MIGRATION_MODE = "APPEND_ONLY_SUCCESSOR"
PACKET_CORE = "UNIFIED_MULTIPURPOSE_INTERACTIVE_COUPLED_8D_STATE_FIELD_PACKET"
STATE_FIELD_KIND = "INTERACTIVE_COUPLED_8D_STATE_FIELD"
TRANSITION_FUNCTION = "S_NEXT=T(S_CURRENT,I,C,E,A,G,R,V)"
DIMENSIONS = (
    "D1_INTENT",
    "D2_STATE",
    "D3_COORDINATE",
    "D4_EVIDENCE",
    "D5_EXECUTION",
    "D6_GENERATIVE_TRANSMISSION",
    "D7_RISK_QUARANTINE",
    "D8_ENVELOPE_VERIFICATION",
)
MESH_PROFILE_SCHEMA = "W7TP_GT_MESH_DOMAIN_PROFILE_V21"
SNAPSHOT_SCHEMA = "W7TP_GT_MESH_NODE_SNAPSHOT_V21"
PACKET_RECEIPT_SCHEMA = "W7TP_GT_MESH_RECEIPT_V21"
CARRIER_SCHEMA = "W7TP_GT_MESH_HTTP_CARRIER_V21"
DRIVE_ENVELOPE_SCHEMA = "W7TP_DRIVE_PROJECTION_ENVELOPE_V21"
TOTAL_FIELD_AUTHORITY_REF = "authority:TOTAL_FIELD"
TOTAL_FIELD_AUTHORITY_NODE_REF = "node:taiji01"
TOTAL_FIELD_CANONICAL_BOUNDARY = "LOCAL_TOTAL_FIELD"
PRIMARY_DECISION_ENGINE = "8D_ADI"
PRIMARY_DECISION_ENGINE_REF = "decision_engine:8D_ADI"
CAPABILITY_INVENTORY_SCHEMA = "W7TP_GT_MESH_SCHEDULER_CAPABILITY_INVENTORY_V21"
CONTROL_PLANE_CONTRACT_SCHEMA = "W7TP_GT_MESH_CONTROL_PLANE_CONTRACT_V21"
CONTROL_TASK_ENVELOPE_SCHEMA = "W7TP_GT_MESH_CONTROL_TASK_ENVELOPE_V21"


class MeshError(RuntimeError):
    """Base error with a stable, non-sensitive reason code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class MeshHold(MeshError):
    """Evidence or prerequisite is insufficient for safe progression."""


class MeshConflict(MeshError):
    """Immutable identity or append-only state conflicts."""


@dataclasses.dataclass(frozen=True, slots=True)
class CoreBindings:
    canonical_json_bytes: Callable[[Any], bytes]
    canonical_json_loads: Callable[..., Any]
    sha256_hex: Callable[[bytes], str]
    sha256_ref: Callable[[bytes], str]
    object_store_type: type
    build_delta: Callable[[bytes, bytes], dict[str, object]]
    apply_delta: Callable[[bytes, dict[str, object]], bytes]


_CORE: CoreBindings | None = None


def require_core() -> CoreBindings:
    """Load the established W7TP subset or fail with one explicit HOLD."""

    global _CORE
    if _CORE is not None:
        return _CORE
    try:
        from w7tp_runtime.state_field.canonical import (
            canonical_json_bytes,
            canonical_json_loads,
            sha256_hex,
            sha256_ref,
        )
        from w7tp_runtime.state_field.object_packet_store import ObjectPacketStore
        from w7tp_runtime.state_field.controlled_experiment_v1.bridge import (
            apply_delta,
            build_delta,
        )
    except (ImportError, AttributeError) as exc:
        raise MeshHold("HOLD_W7TP_CORE_SUBSET_UNAVAILABLE") from exc
    _CORE = CoreBindings(
        canonical_json_bytes=canonical_json_bytes,
        canonical_json_loads=canonical_json_loads,
        sha256_hex=sha256_hex,
        sha256_ref=sha256_ref,
        object_store_type=ObjectPacketStore,
        build_delta=build_delta,
        apply_delta=apply_delta,
    )
    return _CORE


def canonical_binding() -> dict[str, str]:
    return {
        "canonical_path": CANONICAL_PATH,
        "canonical_sha256": CANONICAL_SHA256,
        "parent_version": PARENT_VERSION,
        "parent_path": PARENT_PATH,
        "parent_sha256": PARENT_SHA256,
        "migration_mode": MIGRATION_MODE,
    }


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def utc_text(value: dt.datetime) -> str:
    if value.tzinfo is None:
        raise MeshHold("HOLD_TIMEZONE_REQUIRED")
    return value.astimezone(dt.UTC).isoformat().replace("+00:00", "Z")


def utc_parse(value: object) -> dt.datetime:
    if not isinstance(value, str):
        raise MeshHold("HOLD_TIME_REQUIRED")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MeshHold("HOLD_TIME_INVALID") from exc
    if parsed.tzinfo is None:
        raise MeshHold("HOLD_TIMEZONE_REQUIRED")
    return parsed.astimezone(dt.UTC)


def epoch_seconds(value: dt.datetime) -> int:
    """Integer-only UTC epoch coordinate (no persisted floating point)."""

    if value.tzinfo is None:
        raise MeshHold("HOLD_TIMEZONE_REQUIRED")
    normalized = value.astimezone(dt.UTC)
    return calendar.timegm(normalized.utctimetuple())


def sha256_hex_of(value: Any) -> str:
    core = require_core()
    return core.sha256_hex(core.canonical_json_bytes(value))


def sha256_ref_of(value: Any) -> str:
    core = require_core()
    return core.sha256_ref(core.canonical_json_bytes(value))


def self_hash_excluding(
    value: dict[str, object],
    *,
    container_key: str,
    hash_key: str,
) -> str:
    """Hash canonical JSON after removing the designated self-hash field."""

    core = require_core()
    projection = copy.deepcopy(value)
    container = projection.get(container_key)
    if not isinstance(container, dict):
        raise MeshHold("HOLD_SELF_HASH_CONTAINER_INVALID")
    container.pop(hash_key, None)
    return core.sha256_hex(core.canonical_json_bytes(projection))


_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def safe_component(value: object, *, code: str = "HOLD_PATH_COMPONENT_INVALID") -> str:
    if not isinstance(value, str) or not _SAFE_COMPONENT.fullmatch(value):
        raise MeshHold(code)
    return value


def object_typed_ref(object_ref: str, fragment: str) -> str:
    if not object_ref.startswith("sha256:") or len(object_ref) != 71:
        raise MeshHold("HOLD_OBJECT_REFERENCE_INVALID")
    safe_component(fragment)
    return f"object:{object_ref}#{fragment}"


def canonical_round_trip(value: Any) -> Any:
    """Normalize and prove a value belongs to the existing no-float domain."""

    core = require_core()
    raw = core.canonical_json_bytes(value)
    return core.canonical_json_loads(raw, require_canonical=True)
