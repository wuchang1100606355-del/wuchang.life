#!/usr/bin/env python3
"""Deterministic Total Field rule engine and active-question packet builder."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas/w7tp_total_field_active_question_packet.schema.json"
RULE_VERSION = "W7TP-NON-FLOATING-RULES/1.0"
LOOKUP_VERSION = "W7TP-TOTAL-FIELD-LOOKUP/1.0"
PACKET_PROTOCOL = "W7TP-8D-PACKET-NATIVE/1.0"

QUESTION_RULES = (
    (
        "ACTIVE_QUESTION_RULE_01",
        "missing_state_refs",
        "MISSING_STATE_QUESTION_PACKET",
        "PROVIDE_REQUIRED_STATE_REFS",
        ("state_refs",),
    ),
    (
        "ACTIVE_QUESTION_RULE_02",
        "conflicting_evidence_refs",
        "EVIDENCE_CONFLICT_QUESTION_PACKET",
        "RESOLVE_EVIDENCE_CONFLICT_REFS",
        ("selected_evidence_ref", "conflict_resolution_ref"),
    ),
    (
        "ACTIVE_QUESTION_RULE_03",
        "authority_conflict_refs",
        "AUTHORITY_CLARIFICATION_PACKET",
        "CLARIFY_AUTHORITY_REFS",
        ("authority_ref", "authority_evidence_ref"),
    ),
    (
        "ACTIVE_QUESTION_RULE_04",
        "reconstruction_gap_refs",
        "RECONSTRUCTION_GAP_PACKET",
        "PROVIDE_RECONSTRUCTION_CONDITIONS",
        ("reconstruction_conditions", "verification_method"),
    ),
    (
        "ACTIVE_QUESTION_RULE_05",
        "unresolved_route_refs",
        "UNRESOLVED_ROUTE_PACKET",
        "RESOLVE_ROUTE_REFS",
        ("selected_route_ref", "destination_field_ref"),
    ),
    (
        "ACTIVE_QUESTION_RULE_06",
        "unmatched_condition_refs",
        "NEW_RULE_CANDIDATE_PACKET",
        "REVIEW_NEW_RULE_CANDIDATE",
        ("candidate_rule_ref", "rule_evidence_refs"),
    ),
)


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def deterministic_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def packet_content_sha256(packet: Mapping[str, Any]) -> str:
    content = copy.deepcopy(dict(packet))
    content.pop("sha256", None)
    return deterministic_sha256(content)


def _validate_question(packet: Mapping[str, Any]) -> list[str]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = Draft202012Validator(schema).iter_errors(packet)
    return [
        f"{'.'.join(str(part) for part in error.path) or '$'}:{error.validator}"
        for error in sorted(errors, key=lambda item: list(item.path))
    ]


def generate_active_question_packets(
    run_id: str, state_gap_packet: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Create ordered questions only from explicit non-empty gap-reference sets."""

    evidence_refs = sorted(set(state_gap_packet.get("evidence_refs", [])))
    packets: list[dict[str, Any]] = []
    for rule_id, field, packet_type, question_code, response_fields in QUESTION_RULES:
        trigger_refs = sorted(set(state_gap_packet.get(field, [])))
        if not trigger_refs:
            continue
        seed = {
            "run_id": run_id,
            "rule_version": RULE_VERSION,
            "rule_id": rule_id,
            "trigger_refs": trigger_refs,
        }
        digest = deterministic_sha256(seed)
        packet = {
            "packet_id": f"QUESTION-{digest[:24].upper()}",
            "run_id": run_id,
            "schema_version": "W7TP-TOTAL-FIELD-ACTIVE-QUESTION/1.0",
            "rule_version": RULE_VERSION,
            "state": "HOLD",
            "question_type": packet_type,
            "trigger_rule_id": rule_id,
            "trigger_refs": trigger_refs,
            "question_code": question_code,
            "required_response_fields": list(response_fields),
            "evidence_refs": evidence_refs,
            "execution_authority": False,
            "verification_required": True,
            "seal_status": "NOT_SEALED",
            "d1_intent": {"required_result": "RESOLVE_EXPLICIT_TOTAL_FIELD_GAP"},
            "d2_state": {"question_state": "HOLD", "trigger_refs": trigger_refs},
            "d3_coordinate": {
                "node_ref": "TOTAL_FIELD",
                "engine_ref": "NON_FLOATING_DETERMINISTIC_AI",
                "rule_ref": rule_id,
            },
            "d4_evidence": {"evidence_refs": evidence_refs},
            "d5_execution": {"action": "HOLD_FOR_STRUCTURED_RESPONSE"},
            "d6_generative_transmission": {
                "lookup_ref": "lookup:total-field.active-question.v1",
                "reconstruction_conditions": list(response_fields),
                "verification_method": "EXPLICIT_GAP_REF_RESOLUTION",
                "packet_protocol": PACKET_PROTOCOL,
            },
            "d7_risk": {
                "hard_risk": "MISSING_OR_CONFLICTING_REQUIRED_STATE",
                "authority_boundary_ok": True,
            },
            "d8_envelope": {
                "authority_scope": ["TOTAL_FIELD_GOVERNANCE"],
                "ttl_seconds": 300,
                "nonce": f"question-{digest[24:40]}",
                "protocol": PACKET_PROTOCOL,
                "verifier_ref": "verifier:total-field.non-floating-ai",
            },
        }
        packet["sha256"] = packet_content_sha256(packet)
        errors = _validate_question(packet)
        if errors:
            raise ValueError("INVALID_ACTIVE_QUESTION_PACKET:" + ",".join(errors))
        packets.append(packet)
    return packets


def evaluate_total_field_state(
    run_id: str, state_gap_packet: Mapping[str, Any]
) -> dict[str, Any]:
    """Apply fixed schema/lookup/engineering checks before any seal decision."""

    errors: list[str] = []
    if state_gap_packet.get("rule_version") != RULE_VERSION:
        errors.append("RULE_VERSION_UNSUPPORTED")
    if state_gap_packet.get("lookup_version") != LOOKUP_VERSION:
        errors.append("LOOKUP_VERSION_UNSUPPORTED")
    if state_gap_packet.get("input_valid") is not True:
        errors.append("INPUT_INVALID")
    if state_gap_packet.get("bug_evidence_refs"):
        errors.append("ENGINEERING_BUG_EVIDENCE_PRESENT")

    questions = generate_active_question_packets(run_id, state_gap_packet)
    if questions:
        errors.append("ACTIVE_QUESTIONS_PRESENT")
    decision_seed = {
        "run_id": run_id,
        "rule_version": RULE_VERSION,
        "lookup_version": LOOKUP_VERSION,
        "errors": errors,
        "question_hashes": [packet["sha256"] for packet in questions],
    }
    return {
        "state": "HOLD" if errors else "PASS",
        "decision": "HOLD_FOR_EVIDENCE" if errors else "PASS_RULE_EVALUATION",
        "errors": errors,
        "questions": questions,
        "deterministic_core": True,
        "llm_required": False,
        "engineering_error_audit_required": True,
        "sha256": deterministic_sha256(decision_seed),
    }


def can_seal_candidate(candidate: Mapping[str, Any], evaluation: Mapping[str, Any]) -> bool:
    """Keep seal authority outside unverified candidates and active questions."""

    return bool(
        evaluation.get("state") == "PASS"
        and not evaluation.get("questions")
        and candidate.get("verification_result") == "VERIFIED"
        and candidate.get("candidate_only") is False
    )


__all__ = [
    "LOOKUP_VERSION",
    "QUESTION_RULES",
    "RULE_VERSION",
    "can_seal_candidate",
    "deterministic_sha256",
    "evaluate_total_field_state",
    "generate_active_question_packets",
    "packet_content_sha256",
]
