#!/usr/bin/env python3
"""Append-only V2.3 review-candidate to Canonical V2.1 adapter.

The V2 adapter remains the validating legacy boundary. This successor consumes
its PASS evidence, never mutates the V2 input, and emits a new V2.1 candidate
whose lineage, verification mode, ADI references, and deterministic hash are
explicit. It performs no receiver, network, filesystem-write, database,
deployment, restart, or canonical-promotion action.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from tools.total_field.w7tp_canonical_v2_1_legacy_adapter import (
    validate_v2_1_packet,
)
from tools.total_field.w7tp_intent_field_suite.canonical_hash import (
    canonical_sha256,
)
from tools.total_field.w7tp_review_candidate_v2_3_adapter import (
    AdapterError,
    adapt_review_candidate_v2_3 as legacy_adapt_review_candidate_v2_3,
    request_self_sha256 as legacy_request_self_sha256,
    strict_json_bytes,
)


ROOT = Path(__file__).resolve().parents[2]
REQUEST_SCHEMA_PATH = (
    ROOT
    / "schemas/field/w7tp_review_candidate_v2_3_adapter_request_v2_1.schema.json"
)
CANONICAL_REF = (
    "docs/total_field/"
    "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1_FOUNDER_LOCKED_SUCCESSOR_20260728.md"
)
CANONICAL_PATH = ROOT / CANONICAL_REF
CANONICAL_SHA256 = "383aba5b7a9f5d0e948d9b43b83e7dd6b6ec9c27f025fb9069e83810f0ae870d"
PARENT_CANONICAL_REF = (
    "docs/total_field/"
    "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2.md"
)
PARENT_CANONICAL_PATH = ROOT / PARENT_CANONICAL_REF
PARENT_CANONICAL_SHA256 = (
    "a5281f229ced0943072cce373125be16f0d361b9352a71094ad5450a6022d5d0"
)
CANONICAL_ID = (
    "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1"
)
CANONICAL_VERSION = "2.1"
ADAPTER_CONTRACT_VERSION = "W7TP-REVIEW-CANDIDATE-2.3-TO-CANONICAL-V2.1/1.0"
REQUEST_SELF_HASH_ALGORITHM = (
    "SHA256_CANONICAL_JSON_EXCLUDING_REQUEST_SELF_SHA256/1.0"
)
PACKET_HASH_ALGORITHM = (
    "SHA256_CANONICAL_JSON_EXCLUDING_ENVELOPE_DIGESTS/2.1"
)
CORE_DIMENSIONS = (
    "D1_INTENT",
    "D2_STATE",
    "D3_COORDINATE",
    "D4_EVIDENCE",
    "D5_EXECUTION",
    "D6_GENERATIVE_TRANSMISSION",
    "D7_RISK_QUARANTINE",
    "D8_ENVELOPE_VERIFICATION",
)
NO_SIDE_EFFECTS = {
    "canonical_write": False,
    "database_write": False,
    "deploy": False,
    "file_write": False,
    "network": False,
    "registry_write": False,
    "restart": False,
    "router_write": False,
    "runtime_receiver_call": False,
}


def _sha256_file(path: Path, reason_code: str) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise AdapterError(reason_code, str(path)) from exc


def _copy_without_floats(value: Any, path: str = "$") -> Any:
    if isinstance(value, float):
        raise AdapterError("HOLD_FLOAT_VALUE_FORBIDDEN", path)
    if isinstance(value, Mapping):
        return {
            str(key): _copy_without_floats(item, f"{path}.{key}")
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _copy_without_floats(item, f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, tuple):
        return [
            _copy_without_floats(item, f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    return deepcopy(value)


def _json_path(parts: Collection[Any]) -> str:
    path = "$"
    for part in parts:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


def _load_request_schema() -> dict[str, Any]:
    try:
        schema = strict_json_bytes(
            REQUEST_SCHEMA_PATH.read_bytes(),
            "HOLD_V2_1_REQUEST_SCHEMA_UNAVAILABLE",
        )
        Draft202012Validator.check_schema(schema)
        return schema
    except AdapterError:
        raise
    except Exception as exc:
        raise AdapterError(
            "HOLD_V2_1_REQUEST_SCHEMA_INVALID",
            str(REQUEST_SCHEMA_PATH),
        ) from exc


def _validate_request(request: Mapping[str, Any]) -> dict[str, Any]:
    value = _copy_without_floats(request)
    errors = sorted(
        Draft202012Validator(_load_request_schema()).iter_errors(value),
        key=lambda error: [str(item) for item in error.absolute_path],
    )
    if errors:
        raise AdapterError(
            "HOLD_V2_1_REQUEST_SCHEMA_INVALID",
            _json_path(errors[0].absolute_path),
        )
    return value


def successor_request_self_sha256(request: Mapping[str, Any]) -> str:
    candidate = _copy_without_floats(request)
    candidate.pop("request_self_sha256", None)
    return canonical_sha256(candidate)


def with_successor_request_self_hash(
    request: Mapping[str, Any],
) -> dict[str, Any]:
    candidate = _copy_without_floats(request)
    candidate["request_self_sha256"] = successor_request_self_sha256(candidate)
    return candidate


def _v2_1_payload_sha256(packet: Mapping[str, Any]) -> str:
    candidate = _copy_without_floats(packet)
    candidate.pop("envelope", None)
    return canonical_sha256(candidate)


def v2_1_packet_sha256(packet: Mapping[str, Any]) -> str:
    candidate = _copy_without_floats(packet)
    envelope = candidate.get("envelope")
    if not isinstance(envelope, dict):
        raise AdapterError("HOLD_V2_1_PACKET_ENVELOPE_MISSING", "$.envelope")
    envelope.pop("payload_sha256", None)
    envelope.pop("canonical_json_sha256", None)
    return canonical_sha256(candidate)


def verify_v2_1_packet_hash(packet: Mapping[str, Any]) -> bool:
    try:
        candidate = _copy_without_floats(packet)
        validate_v2_1_packet(candidate)
        envelope = candidate["envelope"]
        return (
            envelope["payload_sha256"] == _v2_1_payload_sha256(candidate)
            and envelope["canonical_json_sha256"]
            == v2_1_packet_sha256(candidate)
        )
    except Exception:
        return False


def _parse_utc(value: str, path: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise AdapterError("HOLD_LOGICAL_TIME_INVALID", path)
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise AdapterError("HOLD_LOGICAL_TIME_INVALID", path) from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise AdapterError("HOLD_LOGICAL_TIME_INVALID", path)
    return parsed


def _source_profile_ref(source: Mapping[str, Any], field: str) -> str:
    return f"sha256:w7tp-v2.3:{field}:{canonical_sha256(source[field])}"


def _verification_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    mode = value["mode"]
    if mode == "L1_EXACT_BYTES":
        return {
            "mode": "L1_EXACT_BYTE",
            "method_ref": "method:sha256",
            "contract_ref": value["hash_scope_ref"],
            "decision": "HOLD",
            "raw_sha256": value["raw_sha256"],
            "byte_length": value["byte_length"],
            "hash_scope": "TARGET_RAW_BYTES",
        }
    if mode == "L2_EFFECT_EQUIVALENT":
        return {
            "mode": mode,
            "method_ref": "method:effect-equivalence",
            "contract_ref": value["effect_contract_ref"],
            "decision": "HOLD",
            "effect_contract_ref": value["effect_contract_ref"],
            "comparison_fields": sorted(value["comparison_fields"]),
            "evidence_refs": sorted(value["evidence_refs"]),
            "local_verifier_ref": "verifier:local-total-field",
        }
    if mode == "L3_CANDIDATE":
        return {
            "mode": mode,
            "method_ref": "method:local-candidate-adjudication",
            "contract_ref": value["local_decision_machine_ref"],
            "decision": "HOLD",
            "candidate_refs": ["ref:review-candidate:v2-3"],
            "local_decision_authority_ref": value[
                "local_decision_machine_ref"
            ],
            "final_authority_granted": False,
        }
    raise AdapterError("HOLD_VERIFICATION_MODE_INVALID", "$.output_contract.verification")


def _assert_canonical_pins() -> None:
    if _sha256_file(CANONICAL_PATH, "HOLD_V2_1_CANONICAL_UNAVAILABLE") != CANONICAL_SHA256:
        raise AdapterError("HOLD_V2_1_CANONICAL_HASH_MISMATCH", str(CANONICAL_PATH))
    if (
        _sha256_file(PARENT_CANONICAL_PATH, "HOLD_PARENT_CANONICAL_UNAVAILABLE")
        != PARENT_CANONICAL_SHA256
    ):
        raise AdapterError(
            "HOLD_PARENT_CANONICAL_HASH_MISMATCH",
            str(PARENT_CANONICAL_PATH),
        )


def _cross_validate_inputs(
    source_packet_bytes: bytes,
    source_packet: Mapping[str, Any],
    legacy_request: Mapping[str, Any],
    request: Mapping[str, Any],
) -> None:
    raw_sha256 = hashlib.sha256(source_packet_bytes).hexdigest()
    source_canonical_sha256 = canonical_sha256(source_packet)
    checks = (
        (
            raw_sha256,
            request["source_packet_raw_sha256"],
            "HOLD_SOURCE_RAW_SHA256_MISMATCH",
            "$.source_packet_raw_sha256",
        ),
        (
            raw_sha256,
            legacy_request.get("source_packet_raw_sha256"),
            "HOLD_LEGACY_SOURCE_RAW_SHA256_MISMATCH",
            "$.legacy_request.source_packet_raw_sha256",
        ),
        (
            source_canonical_sha256,
            request["source_packet_canonical_sha256"],
            "HOLD_SOURCE_CANONICAL_SHA256_MISMATCH",
            "$.source_packet_canonical_sha256",
        ),
        (
            source_canonical_sha256,
            legacy_request.get("source_packet_canonical_sha256"),
            "HOLD_LEGACY_SOURCE_CANONICAL_SHA256_MISMATCH",
            "$.legacy_request.source_packet_canonical_sha256",
        ),
        (
            legacy_request_self_sha256(legacy_request),
            request["legacy_request_self_sha256"],
            "HOLD_LEGACY_REQUEST_SHA256_MISMATCH",
            "$.legacy_request_self_sha256",
        ),
        (
            request["legacy_request_self_sha256"],
            legacy_request.get("request_self_sha256"),
            "HOLD_LEGACY_REQUEST_SHA256_MISMATCH",
            "$.legacy_request.request_self_sha256",
        ),
        (
            successor_request_self_sha256(request),
            request["request_self_sha256"],
            "HOLD_V2_1_REQUEST_SHA256_MISMATCH",
            "$.request_self_sha256",
        ),
    )
    for actual, expected, reason, path in checks:
        if actual != expected:
            raise AdapterError(reason, path)
    if canonical_sha256(legacy_request.get("source_packet")) != source_canonical_sha256:
        raise AdapterError(
            "HOLD_LEGACY_SOURCE_PACKET_BINDING_MISMATCH",
            "$.legacy_request.source_packet",
        )


def _build_v2_1_packet(
    source: Mapping[str, Any],
    request: Mapping[str, Any],
    legacy_result: Mapping[str, Any],
) -> dict[str, Any]:
    output = request["output_contract"]
    logical_time_value = _parse_utc(
        output["logical_time"],
        "$.output_contract.logical_time",
    )
    if logical_time_value.microsecond:
        raise AdapterError(
            "HOLD_LOGICAL_TIME_SUBSECOND_UNSUPPORTED",
            "$.output_contract.logical_time",
        )
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    logical_time_delta = logical_time_value - epoch
    logical_time = (
        logical_time_delta.days * 86400 + logical_time_delta.seconds
    )
    evidence_refs = sorted(
        set(
            output["evidence_refs"]
            + [
                "sha256:source-packet:" + request["source_packet_canonical_sha256"],
                "sha256:legacy-request:" + request["legacy_request_self_sha256"],
                "sha256:legacy-v2-projection:"
                + str(legacy_result["canonical_packet_sha256"]),
            ]
        )
    )
    source_packet_ref = f"packet:{source['packet_id']}"
    source_state_ref = (
        "state:review-candidate:"
        + request["source_packet_canonical_sha256"][:16]
    )
    target_state_ref = f"state:v2-1-candidate:{output['packet_id']}"
    coordinate_ref = _source_profile_ref(source, "d3_coordinate")
    generation_ref = f"generation:{output['packet_id']}"
    risk_ref = f"risk-quarantine:{output['packet_id']}"
    verification_ref = f"verification:{output['packet_id']}"
    envelope_ref = f"envelope:{output['packet_id']}"
    seal_policy_ref = "seal-policy:local-total-field-candidate"
    replay_tuple = {
        "authority_ref": output["authority_ref"],
        "namespace": output["namespace"],
        "packet_id": output["packet_id"],
        "nonce": output["nonce"],
        "logical_time": logical_time,
    }
    lineage = {
        "append_only": True,
        "parent_ref": source_packet_ref,
        "parent_sha256": request["source_packet_canonical_sha256"],
        "previous_seal_ref": output["previous_seal_ref"],
        "logical_time": logical_time,
        "changed_dimensions": list(CORE_DIMENSIONS),
        "transition_evidence_refs": evidence_refs,
    }
    verification = _verification_contract(output["verification"])
    if verification["mode"] == "L3_CANDIDATE":
        verification["candidate_refs"] = [
            source_packet_ref,
            "sha256:legacy-v2-projection:"
            + str(legacy_result["canonical_packet_sha256"]),
        ]

    protected_materials = []
    for protected_ref in output["protected_refs"]:
        reference = protected_ref["reference"]
        if not reference.startswith(("trade_secret_ref:", "protected_ref:")):
            reference = (
                "protected_ref:request-"
                + canonical_sha256(
                    {
                        "kind": protected_ref["protected_type"],
                        "reference": reference,
                    }
                )
            )
        protected_materials.append(
            {
                "kind": protected_ref["protected_type"],
                "reference": reference,
                "disclosure": "REFERENCE_ONLY",
            }
        )

    dimensions = {
        "D1_INTENT": {
            "profile_ref": _source_profile_ref(source, "d1_intent"),
        },
        "D2_STATE": {
            "profile_ref": _source_profile_ref(source, "d2_state"),
        },
        "D3_COORDINATE": {
            "profile_ref": coordinate_ref,
        },
        "D4_EVIDENCE": {
            "profile_ref": _source_profile_ref(source, "d4_evidence"),
            "evidence_refs": evidence_refs,
        },
        "D5_EXECUTION": {
            "profile_ref": _source_profile_ref(source, "d5_execution"),
        },
        "D6_GENERATIVE_TRANSMISSION": {
            "protocol_ref": "protocol:w7tp-v2.1",
            "routing_ref": "routing:local-total-field",
            "lookup_refs": [coordinate_ref],
            "reference_refs": evidence_refs,
            "generation_rule_refs": ["rule:review-candidate-projection"],
            "reconstruction_condition_refs": [
                "condition:legacy-v2-validated"
            ],
            "equivalent_state_rule_refs": [
                "equivalence:governed-candidate-state"
            ],
            "total_field_verifier_ref": output[
                "total_field_verifier_ref"
            ],
        },
        "D7_RISK_QUARANTINE": {
            "hard_risks": [
                "AUTHORITY_INJECTION",
                "CANONICAL_WRITE",
                "DATABASE_WRITE",
                "DEPLOY",
                "REPLAY",
                "ROUTER_WRITE",
            ],
            "quarantine_refs": [
                "risk-quarantine:candidate-only-no-authority"
            ],
            "decision": "HOLD",
        },
        "D8_ENVELOPE_VERIFICATION": {
            "envelope_ref": envelope_ref,
            "verifier_ref": output["total_field_verifier_ref"],
            "seal_policy_ref": seal_policy_ref,
        },
    }
    packet = {
        "canonical_id": CANONICAL_ID,
        "version": CANONICAL_VERSION,
        "canonical_binding": {
            "canonical_path": CANONICAL_REF,
            "canonical_sha256": CANONICAL_SHA256,
            "parent_version": "2.0",
            "parent_path": PARENT_CANONICAL_REF,
            "parent_sha256": PARENT_CANONICAL_SHA256,
            "migration_mode": "APPEND_ONLY_SUCCESSOR",
        },
        "packet_core": (
            "UNIFIED_MULTIPURPOSE_INTERACTIVE_COUPLED_8D_STATE_FIELD_PACKET"
        ),
        "communication_contract": {
            "primary": "INTENT_COMMUNICATION",
            "secondary": "STATE_FIELD_PACKET_COMMUNICATION",
            "semantic_communication": False,
            "semantic_model_role": "CANDIDATE_EVIDENCE_ONLY",
            "floating_point_required": False,
        },
        "authority_boundary": {
            "cloud_authority": ["CANDIDATE", "EVIDENCE"],
            "llm_authority": ["CANDIDATE", "EVIDENCE"],
            "final_decision_authority": "LOCAL_TOTAL_FIELD",
            "final_seal_authority": "LOCAL_TOTAL_FIELD",
        },
        "state_field": {
            "kind": "INTERACTIVE_COUPLED_8D_STATE_FIELD",
            "dimensions": dimensions,
            "coupling": {
                "transition_function": "S_NEXT=T(S_CURRENT,I,C,E,A,G,R,V)",
                "current_state_ref": source_state_ref,
                "intent_ref": _source_profile_ref(source, "d1_intent"),
                "coordinate_ref": coordinate_ref,
                "evidence_refs": evidence_refs,
                "execution_ref": _source_profile_ref(source, "d5_execution"),
                "generation_ref": generation_ref,
                "risk_ref": risk_ref,
                "verification_ref": verification_ref,
                "target_state_ref": target_state_ref,
                "non_float_execution": True,
            },
        },
        "adi": {
            "packet_layer": {
                "index_kind": "OPAQUE_IRREVERSIBLE_PACKET_DECISION_INDEX",
                "namespace": output["namespace"],
                "decision_index": canonical_sha256(
                    {
                        "authority_ref": output["authority_ref"],
                        "evidence_refs": evidence_refs,
                        "key_version_ref": output["key_version_ref"],
                        "namespace": output["namespace"],
                        "nonce": output["nonce"],
                    }
                ),
                "nonce": output["nonce"],
                "key_version_ref": output["key_version_ref"],
                "authority_ref": output["authority_ref"],
                "evidence_refs": evidence_refs,
                "derivation_ref": "derivation:local-packet-adjudication",
                "verifier_ref": output["total_field_verifier_ref"],
                "irreversible": True,
                "reversible_identity": False,
                "database_primary_key": False,
                "floating_embedding": False,
            },
            "system_layer": {
                "index_kind": (
                    "USER_OWNED_SPATIOTEMPORAL_STATE_INDEX_NETWORK"
                ),
                "owner_authority_ref": output["authority_ref"],
                "namespace": output["namespace"],
                "logical_time": logical_time,
                "packet_lineage_refs": [source_packet_ref],
                "state_transition_ref": output["state_transition_ref"],
                "evidence_refs": evidence_refs,
            },
            "replay_protection": {
                "tuple": replay_tuple,
                "tuple_sha256": canonical_sha256(replay_tuple),
                "logical_time_monotonic": True,
            },
        },
        "lineage": lineage,
        "generation": {
            "protocol_native": True,
            "state_ref": source_state_ref,
            "coordinate_ref": coordinate_ref,
            "lookup_refs": [coordinate_ref],
            "generation_rule_refs": ["rule:review-candidate-projection"],
            "reconstruction_condition_refs": [
                "condition:legacy-v2-validated"
            ],
            "target_state_ref": target_state_ref,
            "file_movement": False,
        },
        "reconstruction": {
            "local_state_field_ref": "state-field:local-total-field",
            "lookup_refs": [coordinate_ref],
            "condition_refs": ["condition:legacy-v2-validated"],
            "equivalent_state_rule_refs": [
                "equivalence:governed-candidate-state"
            ],
            "target_state_ref": target_state_ref,
            "total_field_verifier_ref": output[
                "total_field_verifier_ref"
            ],
            "deterministic_operations": [
                "INTEGER",
                "BOOLEAN",
                "SYMBOLIC",
                "LOOKUP",
                "REFERENCE_RESOLUTION",
                "STATE_TRANSITION",
            ],
            "model_output_role": "CANDIDATE_EVIDENCE_ONLY",
        },
        "verification": verification,
        "protected_refs": {
            "materials": protected_materials,
        },
        "envelope": {
            "packet_id": output["packet_id"],
            "authority_ref": output["authority_ref"],
            "version": CANONICAL_VERSION,
            "ttl_seconds": 300,
            "nonce": output["nonce"],
            "payload_sha256": "0" * 64,
            "canonical_json_sha256": "0" * 64,
            "verifier_ref": output["total_field_verifier_ref"],
            "seal_policy_ref": seal_policy_ref,
            "seal_state": "UNSEALED_CANDIDATE",
            "final_seal_authority": "LOCAL_TOTAL_FIELD",
        },
    }
    packet["envelope"]["payload_sha256"] = _v2_1_payload_sha256(packet)
    packet["envelope"]["canonical_json_sha256"] = v2_1_packet_sha256(
        packet
    )
    validate_v2_1_packet(packet)
    return packet


def _hold_receipt(reason_code: str, path: str) -> dict[str, Any]:
    return {
        "state": "HOLD_V2_1_ADAPTER_CONTRACT",
        "decision": "HOLD",
        "reason_code": reason_code,
        "path": path,
        "target_canonical_version": CANONICAL_VERSION,
        "canonical_packet": None,
        "canonical_packet_sha256": None,
        "candidate_only": True,
        "authority_granted": False,
        "side_effects": dict(NO_SIDE_EFFECTS),
    }


def adapt_review_candidate_v2_3_to_v2_1(
    source_packet_bytes: bytes,
    legacy_adapter_request: Mapping[str, Any],
    successor_request: Mapping[str, Any],
    *,
    workspace_root: Path = ROOT,
    identity_map: Mapping[str, Any] | None = None,
    now: datetime | None = None,
    seen_nonces: Collection[str] = (),
) -> dict[str, Any]:
    """Validate the V2 legacy projection and emit a distinct V2.1 candidate."""

    try:
        _assert_canonical_pins()
        request = _validate_request(successor_request)
        source = strict_json_bytes(
            source_packet_bytes,
            "HOLD_SOURCE_PACKET_INVALID",
        )
        legacy_request = _copy_without_floats(legacy_adapter_request)
        _cross_validate_inputs(
            source_packet_bytes,
            source,
            legacy_request,
            request,
        )
        legacy_result = legacy_adapt_review_candidate_v2_3(
            source_packet_bytes,
            legacy_request,
            workspace_root=workspace_root,
            identity_map=identity_map,
            now=now,
            seen_nonces=seen_nonces,
        )
        if not str(legacy_result.get("state", "")).startswith("PASS_"):
            return _hold_receipt(
                str(legacy_result.get("reason_code") or "HOLD_LEGACY_V2_VALIDATION"),
                str(legacy_result.get("path") or "$.legacy_adapter_request"),
            )

        output = request["output_contract"]
        source_issued_at = _parse_utc(
            source["d7_risk"]["issued_at"],
            "$.source_packet.d7_risk.issued_at",
        )
        logical_time = _parse_utc(
            output["logical_time"],
            "$.output_contract.logical_time",
        )
        if logical_time <= source_issued_at:
            raise AdapterError(
                "HOLD_LOGICAL_TIME_NOT_APPEND_ONLY",
                "$.output_contract.logical_time",
            )
        nonce = output["nonce"]
        if nonce == source["d7_risk"]["nonce"]:
            raise AdapterError("HOLD_NONCE_REUSE", "$.output_contract.nonce")
        replay_tuple = f"{output['authority_ref']}|{output['namespace']}|{nonce}"
        if nonce in seen_nonces or replay_tuple in seen_nonces:
            raise AdapterError("HOLD_REPLAY_DETECTED", "$.output_contract.nonce")

        packet = _build_v2_1_packet(source, request, legacy_result)
        packet_hash = packet["envelope"]["canonical_json_sha256"]
        if not verify_v2_1_packet_hash(packet):
            raise AdapterError(
                "HOLD_V2_1_PACKET_HASH_MISMATCH",
                "$.envelope.packet_sha256",
            )
        return {
            "state": "PASS_V2_1_ADAPTER_CONTRACT_RECONSTRUCTED_CANDIDATE",
            "decision": "HOLD",
            "reason_code": "HOLD_AWAITING_LOCAL_TOTAL_FIELD_DECISION_AND_SEAL",
            "source_schema_version": source["schema_version"],
            "target_canonical_version": CANONICAL_VERSION,
            "source_packet_raw_sha256": request["source_packet_raw_sha256"],
            "source_packet_canonical_sha256": request[
                "source_packet_canonical_sha256"
            ],
            "legacy_request_self_sha256": request["legacy_request_self_sha256"],
            "successor_request_self_sha256": request["request_self_sha256"],
            "legacy_v2_projection_sha256": legacy_result[
                "canonical_packet_sha256"
            ],
            "canonical_packet_sha256": packet_hash,
            "canonical_packet": packet,
            "candidate_only": True,
            "authority_granted": False,
            "side_effects": dict(NO_SIDE_EFFECTS),
        }
    except AdapterError as exc:
        return _hold_receipt(exc.reason_code, exc.path)
    except Exception:
        return _hold_receipt("HOLD_UNEXPECTED_ADAPTER_FAILURE", "$")


__all__ = [
    "ADAPTER_CONTRACT_VERSION",
    "CANONICAL_ID",
    "CANONICAL_REF",
    "CANONICAL_SHA256",
    "CANONICAL_VERSION",
    "PARENT_CANONICAL_REF",
    "PARENT_CANONICAL_SHA256",
    "REQUEST_SCHEMA_PATH",
    "adapt_review_candidate_v2_3_to_v2_1",
    "successor_request_self_sha256",
    "v2_1_packet_sha256",
    "verify_v2_1_packet_hash",
    "with_successor_request_self_hash",
]
