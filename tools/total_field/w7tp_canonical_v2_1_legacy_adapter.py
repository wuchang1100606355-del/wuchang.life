"""Read-only Canonical V2 projection and V2.1 machine-contract helpers."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
V2_SCHEMA_PATH = ROOT / "schemas/w7tp_8d_multipurpose_packet_canonical_v2.schema.json"
V2_1_SCHEMA_PATH = (
    ROOT / "schemas/w7tp_8d_multipurpose_packet_canonical_v2_1.schema.json"
)
ADAPTER_SCHEMA_PATH = (
    ROOT / "schemas/field/w7tp_canonical_v2_to_v2_1_legacy_adapter_v1.schema.json"
)

V2_CANONICAL_ID = "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2"
V2_1_CANONICAL_ID = (
    "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1"
)
V2_1_CANONICAL_PATH = (
    "docs/total_field/"
    "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1.md"
)
V2_1_CANONICAL_SHA256 = (
    "e960d14254df083ffed711e2c44b76fc2075541716881bc3d1034cb26cffbaba"
)

_PROTECTED_MARKERS = (
    "h64-td",
    "h64_td",
    "h64 codebook",
    "h64_codebook",
    "codebook material",
    "mapping table material",
    "mapping_table_material",
    "recovery material",
    "recovery_material",
)
_PROTECTED_KEY_MARKERS = (
    "h64_material",
    "codebook_payload",
    "mapping_table_payload",
    "recovery_material_payload",
)
_APPROVED_PROTECTED_REF_PREFIXES = (
    "trade_secret_ref:",
    "protected_ref:",
)


class ContractViolation(ValueError):
    """Raised when a packet violates a V2.1 machine-contract boundary."""


def canonical_json_bytes(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON bytes."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def replay_tuple_sha256(value: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def _load_schema(path: Path) -> dict[str, Any]:
    schema = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(schema, dict):
        raise ContractViolation(f"schema is not an object: {path}")
    Draft202012Validator.check_schema(schema)
    return schema


def protected_material_violations(
    value: Any,
    path: tuple[str, ...] = (),
) -> list[str]:
    """Return JSON pointers that expose protected material instead of references."""

    violations: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = key.casefold().replace("-", "_")
            child_path = (*path, key)
            if any(marker in normalized_key for marker in _PROTECTED_KEY_MARKERS):
                violations.append(_json_pointer(child_path))
            violations.extend(protected_material_violations(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            violations.extend(
                protected_material_violations(child, (*path, str(index)))
            )
    elif isinstance(value, str):
        normalized = value.casefold()
        has_marker = any(marker in normalized for marker in _PROTECTED_MARKERS)
        approved_reference = normalized.startswith(
            _APPROVED_PROTECTED_REF_PREFIXES
        )
        protected_kind = (
            len(path) >= 3
            and path[-1] == "kind"
            and "protected_refs" in path
            and value in {"H64_TD", "CODEBOOK", "MAPPING_TABLE", "RECOVERY_MATERIAL"}
        )
        if has_marker and not approved_reference and not protected_kind:
            violations.append(_json_pointer(path))
    return sorted(set(violations))


def _json_pointer(path: tuple[str, ...]) -> str:
    if not path:
        return ""
    escaped = [part.replace("~", "~0").replace("/", "~1") for part in path]
    return "/" + "/".join(escaped)


def _validate_protected_refs(value: Any) -> None:
    violations = protected_material_violations(value)
    if violations:
        raise ContractViolation(
            "protected material must be reference-only at: " + ",".join(violations)
        )


def load_and_validate_v2_packet(raw_bytes: bytes) -> dict[str, Any]:
    """Validate historical V2 bytes without changing or normalizing the input."""

    if not isinstance(raw_bytes, bytes) or not raw_bytes:
        raise ContractViolation("legacy packet input must be non-empty bytes")
    try:
        packet = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractViolation("legacy packet must be UTF-8 JSON") from exc
    if not isinstance(packet, dict):
        raise ContractViolation("legacy packet must be a JSON object")
    schema = _load_schema(V2_SCHEMA_PATH)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(packet),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        pointer = _json_pointer(tuple(str(part) for part in errors[0].absolute_path))
        raise ContractViolation(f"legacy V2 schema mismatch at {pointer or '/'}")
    _validate_protected_refs(packet)
    return packet


def project_v2_packet(
    raw_bytes: bytes,
    *,
    source_ref: str,
    authority_ref: str,
    namespace: str,
    logical_time: int,
    nonce: str,
) -> dict[str, Any]:
    """Project V2 bytes into a V2.1 legacy receipt without embedding source data."""

    packet = load_and_validate_v2_packet(raw_bytes)
    source_raw_sha256 = sha256_bytes(raw_bytes)
    projection_id = f"W7TP-V2-LEGACY-PROJECTION-{source_raw_sha256[:16]}"
    replay_tuple = {
        "authority_ref": authority_ref,
        "namespace": namespace,
        "packet_id": projection_id,
        "nonce": nonce,
        "logical_time": logical_time,
    }
    legacy_dimension_paths = {
        "D1_INTENT": "D1_INTENT",
        "D2_STATE": "D2_STATE",
        "D3_COORDINATE": "D3_COORDINATE",
        "D4_EVIDENCE": "D4_EVIDENCE",
        "D5_EXECUTION": "D5_EXECUTION",
        "D6_GENERATIVE_TRANSMISSION": "D6_GENERATIVE_TRANSMISSION",
        "D7_RISK_QUARANTINE": "D7_RISK",
        "D8_ENVELOPE_VERIFICATION": "D8_ENVELOPE",
    }
    projection = {
        "adapter_id": "W7TP_CANONICAL_V2_TO_V2_1_LEGACY_ADAPTER_V1",
        "version": "1.0.0",
        "mode": "LEGACY_V2_READ_TO_V2_1_PROJECTION",
        "source": {
            "source_ref": source_ref,
            "canonical_id": packet["canonical_id"],
            "version": packet["version"],
            "raw_sha256": source_raw_sha256,
            "canonical_json_sha256": sha256_bytes(canonical_json_bytes(packet)),
            "byte_length": len(raw_bytes),
            "schema_validated": True,
            "bytes_mutated": False,
        },
        "target": {
            "canonical_id": V2_1_CANONICAL_ID,
            "version": "2.1",
            "canonical_path": V2_1_CANONICAL_PATH,
            "canonical_sha256": V2_1_CANONICAL_SHA256,
            "projection_only": True,
        },
        "lineage": {
            "append_only": True,
            "parent_ref": source_ref,
            "parent_raw_sha256": source_raw_sha256,
            "logical_time": logical_time,
        },
        "replay_protection": {
            "tuple": replay_tuple,
            "tuple_sha256": replay_tuple_sha256(replay_tuple),
        },
        "projection": {
            "projection_id": projection_id,
            "legacy_profile": "CANONICAL_V2_DIMENSIONS_READ_ONLY",
            "legacy_dimensions_sha256": sha256_bytes(
                canonical_json_bytes(packet["dimensions"])
            ),
            "dimension_refs": {
                target: f"legacy-json-pointer:/dimensions/{source}"
                for target, source in legacy_dimension_paths.items()
            },
            "verification_mode": "L3_CANDIDATE",
            "local_decision_required": True,
            "source_content_embedded": False,
        },
    }
    validate_legacy_projection(projection)
    return projection


def validate_legacy_projection(projection: dict[str, Any]) -> None:
    schema = _load_schema(ADAPTER_SCHEMA_PATH)
    Draft202012Validator(schema).validate(projection)
    expected_tuple_sha256 = replay_tuple_sha256(
        projection["replay_protection"]["tuple"]
    )
    if projection["replay_protection"]["tuple_sha256"] != expected_tuple_sha256:
        raise ContractViolation("legacy projection replay tuple hash mismatch")
    if (
        projection["source"]["raw_sha256"]
        != projection["lineage"]["parent_raw_sha256"]
    ):
        raise ContractViolation("legacy projection parent digest mismatch")
    _validate_protected_refs(projection)


def validate_v2_1_packet(packet: dict[str, Any]) -> None:
    """Validate schema plus cross-field namespace, lineage and replay invariants."""

    schema = _load_schema(V2_1_SCHEMA_PATH)
    Draft202012Validator(schema).validate(packet)
    _validate_protected_refs(packet)

    packet_layer = packet["adi"]["packet_layer"]
    system_layer = packet["adi"]["system_layer"]
    replay = packet["adi"]["replay_protection"]
    replay_tuple = replay["tuple"]
    lineage = packet["lineage"]
    envelope = packet["envelope"]

    if len(
        {
            packet_layer["namespace"],
            system_layer["namespace"],
            replay_tuple["namespace"],
        }
    ) != 1:
        raise ContractViolation("ADI namespace mismatch")
    if len(
        {
            packet_layer["authority_ref"],
            system_layer["owner_authority_ref"],
            replay_tuple["authority_ref"],
            envelope["authority_ref"],
        }
    ) != 1:
        raise ContractViolation("authority reference mismatch")
    if replay_tuple["packet_id"] != envelope["packet_id"]:
        raise ContractViolation("replay packet_id mismatch")
    if len(
        {
            packet_layer["nonce"],
            replay_tuple["nonce"],
            envelope["nonce"],
        }
    ) != 1:
        raise ContractViolation("nonce mismatch")
    if len(
        {
            system_layer["logical_time"],
            replay_tuple["logical_time"],
            lineage["logical_time"],
        }
    ) != 1:
        raise ContractViolation("logical time mismatch")
    if replay["tuple_sha256"] != replay_tuple_sha256(replay_tuple):
        raise ContractViolation("replay tuple hash mismatch")


class InMemoryReplayGuard:
    """Side-effect-free replay and logical-time guard for focused validation."""

    def __init__(self) -> None:
        self._seen: set[tuple[str, str, str, str]] = set()
        self._latest_logical_time: dict[tuple[str, str], int] = {}

    def accept(self, packet: dict[str, Any]) -> None:
        snapshot = deepcopy(packet)
        validate_v2_1_packet(snapshot)
        replay_tuple = snapshot["adi"]["replay_protection"]["tuple"]
        replay_key = (
            replay_tuple["authority_ref"],
            replay_tuple["namespace"],
            replay_tuple["packet_id"],
            replay_tuple["nonce"],
        )
        authority_namespace = (
            replay_tuple["authority_ref"],
            replay_tuple["namespace"],
        )
        logical_time = replay_tuple["logical_time"]
        if replay_key in self._seen:
            raise ContractViolation("replay tuple already observed")
        previous = self._latest_logical_time.get(authority_namespace)
        if previous is not None and logical_time <= previous:
            raise ContractViolation("logical time is not monotonic")
        self._seen.add(replay_key)
        self._latest_logical_time[authority_namespace] = logical_time
