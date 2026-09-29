"""Non-active formal Total Field review-entry candidate.

This adapter validates a binding-candidate review packet and creates an
in-memory review receipt candidate. It cannot authorize effects, activate a
capability pack, or mutate runtime state.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from tools.total_field.w7tp_governed_promotion import canonical_bytes, sha256

INPUT_SCHEMA = "W7TP_V23_FORMAL_TOTAL_FIELD_REVIEW_INPUT_CANDIDATE_V1"
RECEIPT_SCHEMA = "W7TP_V23_FORMAL_TOTAL_FIELD_REVIEW_RECEIPT_CANDIDATE_V1"

ACCEPT = "ACCEPT_BINDING_CANDIDATE"
HOLD = "HOLD_BINDING_CANDIDATE"
REJECT = "REJECT_BINDING_CANDIDATE"
OUTPUT_STATES = frozenset({ACCEPT, HOLD, REJECT})

EFFECT_SCOPE = "ACTIVE_CAPABILITY_PACK_BINDING_CANDIDATE"
RISK_RESULTS = frozenset({"PASS", "HOLD", "BLOCK", "UNKNOWN"})
SOURCE_C_LINEAGE = {
    "COMMON_PARENT": "d32ebc73ea7e413daa61c58cc831964743dba99d",
    "SOURCE_A": "680f646bd383077695b5a44e1d40657f7b6a358d",
    "SOURCE_B": "dbf06fca1fcee33d6a695c7be657146c543298ca",
    "SOURCE_C_SHA256": "0ba43b83fd9da27fa60751aeed22d2de1e8859a024775b78a99c6a5862b2577c",
    "LINEAGE_RECEIPT": (
        "runtime/total_field/candidates/w7tp_v23_founder_semantic_successor_c/"
        "LINEAGE_RECEIPT.json"
    ),
}
REQUIRED_FIELDS = (
    "FOUNDER_INTENT_REFERENCE",
    "SOURCE_LINEAGE",
    "CURRENT_8D_FIELD_REFERENCE",
    "CANDIDATE_STATE",
    "D4_EVIDENCE",
    "RISK_RESULT",
    "EFFECT_SCOPE",
)
REQUIRED_CANDIDATE_FIELDS = (
    "SOURCE_C_SHA",
    "SEMANTIC_GUARD_RESULT",
    "CAPABILITY_PACK_HASH",
    "CAPABILITY_PACK_SEMANTIC_RESULT",
    "FOUNDER_DYNAMIC_CONTEXT_RESULT",
    "CLOUD_CANDIDATE_ONLY",
    "D4_D8_SEPARATION",
)
REQUIRED_LINEAGE_FIELDS = (
    "COMMON_PARENT",
    "SOURCE_A",
    "SOURCE_B",
    "SOURCE_C_SHA256",
    "LINEAGE_RECEIPT",
)
FORBIDDEN_OUTPUT_VALUES = frozenset(
    {"ALLOW_EFFECT", "D8_ALLOW", "CANONICAL", "CURRENT", "ACTIVE", "DEPLOY"}
)


def _digest(value: Any) -> str:
    return sha256(canonical_bytes(value))


def _issued_at(value: str | None) -> str:
    if value is not None:
        return value
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _reference_status(value: Mapping[str, Any] | None) -> str:
    if value is None:
        return "INVALID"
    status = value.get("status")
    return str(status).strip().upper() if isinstance(status, str) else "INVALID"


def _reference_value(value: Mapping[str, Any] | None) -> str | None:
    if value is None:
        return None
    reference = value.get("reference")
    return reference if isinstance(reference, str) and reference.strip() else None


def _lineage_valid(value: Mapping[str, Any] | None) -> bool:
    if value is None or any(not value.get(field) for field in REQUIRED_LINEAGE_FIELDS):
        return False
    return (
        all(value.get(field) == expected for field, expected in SOURCE_C_LINEAGE.items())
        and value.get("authority") == "D4_EVIDENCE_ONLY"
    )


def _candidate_state_valid(value: Mapping[str, Any] | None) -> bool:
    if value is None or any(field not in value for field in REQUIRED_CANDIDATE_FIELDS):
        return False
    if any(value.get(field) is True for field in ("ACTIVE", "CANONICAL", "D8")):
        return False
    return (
        value.get("SOURCE_C_SHA") == SOURCE_C_LINEAGE["SOURCE_C_SHA256"]
        and value.get("SEMANTIC_GUARD_RESULT") == "PASS_14_OF_14"
        and isinstance(value.get("CAPABILITY_PACK_HASH"), str)
        and len(value["CAPABILITY_PACK_HASH"]) == 64
        and value.get("CAPABILITY_PACK_SEMANTIC_RESULT") == "PASS"
        and value.get("FOUNDER_DYNAMIC_CONTEXT_RESULT")
        == "TOTAL_FIELD_DYNAMIC_CONTEXT_READY_CANDIDATE_ONLY"
        and value.get("CLOUD_CANDIDATE_ONLY") is True
        and value.get("D4_D8_SEPARATION") is True
    )


def _d4_evidence_valid(value: Mapping[str, Any] | None) -> bool:
    if not value:
        return False
    return (
        value.get("source_c_sha_match") is True
        and value.get("semantic_guard") == "PASS_14_OF_14"
        and value.get("manifest_source_hash_match") is True
        and isinstance(value.get("lineage_receipt_sha256"), str)
        and len(value["lineage_receipt_sha256"]) == 64
        and value.get("authority") == "D4_EVIDENCE_ONLY"
        and value.get("d4_evidence_is_authority") is not True
    )


def _contains_forbidden_output(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_forbidden_output(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_forbidden_output(item) for item in value)
    return isinstance(value, str) and value in FORBIDDEN_OUTPUT_VALUES


def _review_disposition(packet: Mapping[str, Any]) -> tuple[str, list[str]]:
    missing = [field for field in REQUIRED_FIELDS if field not in packet]
    if missing:
        return HOLD, [f"MISSING_{field}" for field in missing]

    founder = _mapping(packet.get("FOUNDER_INTENT_REFERENCE"))
    lineage = _mapping(packet.get("SOURCE_LINEAGE"))
    current_field = _mapping(packet.get("CURRENT_8D_FIELD_REFERENCE"))
    candidate = _mapping(packet.get("CANDIDATE_STATE"))
    evidence = _mapping(packet.get("D4_EVIDENCE"))
    risk = packet.get("RISK_RESULT")
    effect_scope = packet.get("EFFECT_SCOPE")

    if effect_scope != EFFECT_SCOPE:
        return REJECT, ["EFFECT_SCOPE_MISMATCH"]
    if risk == "BLOCK":
        return REJECT, ["RISK_RESULT_BLOCK"]

    reasons: list[str] = []
    if _reference_value(founder) is None:
        reasons.append("FOUNDER_INTENT_REFERENCE_INVALID")
    elif _reference_status(founder) != "BOUND":
        reasons.append("FOUNDER_INTENT_REFERENCE_NOT_BOUND")
    if not _lineage_valid(lineage):
        reasons.append("SOURCE_LINEAGE_INVALID_OR_UNBOUND")
    if _reference_value(current_field) is None or _reference_status(current_field) != "BOUND":
        reasons.append("CURRENT_8D_FIELD_REFERENCE_NOT_BOUND")
    if not _candidate_state_valid(candidate):
        reasons.append("CANDIDATE_STATE_INVALID_OR_UNBOUND")
    elif candidate.get("CLOUD_CANDIDATE_DIRECT_ACCEPT") is True:
        reasons.append("CLOUD_CANDIDATE_DIRECT_ACCEPT_FORBIDDEN")
    if not _d4_evidence_valid(evidence):
        reasons.append("D4_EVIDENCE_INVALID_OR_AUTHORITY_CLAIMED")
    if risk not in RISK_RESULTS:
        reasons.append("RISK_RESULT_INVALID")
    elif risk in {"UNKNOWN", "HOLD"}:
        reasons.append(f"RISK_RESULT_{risk}")

    return (HOLD, reasons) if reasons else (ACCEPT, [])


def evaluate_formal_review_entry_candidate(
    packet: Mapping[str, Any], *, issued_at: str | None = None
) -> dict[str, Any]:
    """Validate one packet without writing files or granting authority."""
    timestamp = _issued_at(issued_at)
    if not isinstance(packet, Mapping) or packet.get("schema_id") != INPUT_SCHEMA:
        review_result, reasons = HOLD, ["INPUT_SCHEMA_INVALID"]
        normalized: Mapping[str, Any] = packet if isinstance(packet, Mapping) else {}
    else:
        normalized = packet
        review_result, reasons = _review_disposition(normalized)

    founder = _mapping(normalized.get("FOUNDER_INTENT_REFERENCE"))
    current_field = _mapping(normalized.get("CURRENT_8D_FIELD_REFERENCE"))
    lineage = normalized.get("SOURCE_LINEAGE")
    candidate = normalized.get("CANDIDATE_STATE")
    evidence = normalized.get("D4_EVIDENCE")
    receipt_body = {
        "schema_id": RECEIPT_SCHEMA,
        "receipt_type": "REVIEW_RECEIPT_CANDIDATE_NOT_D8_RECEIPT",
        "founder_intent_reference": _reference_value(founder),
        "source_lineage_digest": _digest(lineage),
        "current_8d_field_reference": _reference_value(current_field),
        "candidate_state_digest": _digest(candidate),
        "d4_evidence_digest": _digest(evidence),
        "risk_result": normalized.get("RISK_RESULT"),
        "effect_scope": normalized.get("EFFECT_SCOPE"),
        "review_result": review_result,
        "reason_codes": reasons,
        "issued_at": timestamp,
        "authority_granted": False,
        "d8_receipt": False,
        "runtime_effect": "NONE",
    }
    receipt_body["review_id"] = "review_candidate:sha256:" + _digest(receipt_body)
    receipt_hash = _digest(receipt_body)
    receipt = dict(receipt_body, receipt_hash=receipt_hash)
    result = {
        "state": "FORMAL_TOTAL_FIELD_REVIEW_ENTRY_CANDIDATE",
        "review_result": review_result,
        "reason_codes": reasons,
        "review_receipt_candidate": receipt,
        "total_field_effect_decision": "NOT_RUN",
        "d8_decision": "NOT_RUN",
        "authority_granted": False,
        "runtime_effect": "NONE",
    }
    if review_result not in OUTPUT_STATES:
        raise AssertionError("review result escaped the candidate-only contract")
    if _contains_forbidden_output(result):
        raise AssertionError("forbidden effect decision escaped the review adapter")
    return result


__all__ = [
    "ACCEPT",
    "EFFECT_SCOPE",
    "HOLD",
    "INPUT_SCHEMA",
    "RECEIPT_SCHEMA",
    "REJECT",
    "evaluate_formal_review_entry_candidate",
]
