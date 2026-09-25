#!/usr/bin/env python3
"""Build product intent field dry-run packets without side effects."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


TOOL_DIR = Path(__file__).resolve().parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

from product_intent_accountability import build_accountability_record  # noqa: E402
from product_intent_identity_proxy import build_identity_proxy  # noqa: E402
from redact_candidate_payload import scan_text  # noqa: E402


def utc_stamp() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")


def stable_ref(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}:{digest}"


def hash_value(value: str) -> str:
    return "hash:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_request(intent: str, *, force_hold: bool = False) -> dict[str, Any]:
    run_id = "PRODUCT_INTENT_DRY_RUN_" + utc_stamp()
    return {
        "run_id": run_id,
        "intent_request_id": stable_ref("intent_request_id", run_id + intent),
        "intent_text_ref": stable_ref("intent_text_ref", intent),
        "raw_intent_text": intent,
        "dry_run_only": True,
        "candidate_only": True,
        "force_hold": force_hold,
        "db_write": False,
        "deploy": False,
        "restart": False,
        "h64_td_refs": [
            "trade_secret_ref:h64_codebook",
            "trade_secret_ref:td_hash_runtime",
        ],
    }


def build_state_packet(request: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    intent = str(request.get("raw_intent_text", ""))
    force_hold = bool(request.get("force_hold"))
    identity = build_identity_proxy(intent, force_hold=force_hold)
    candidate_action_id = stable_ref("candidate_action_id", request["intent_request_id"] + ":candidate")
    state_packet_id = stable_ref("state_packet_id", candidate_action_id)
    timestamp = "timestamp_coordinate:" + utc_stamp()
    rule_version = "rule_version:product_intent_dry_run_p0"
    content_hash = hash_value(json.dumps(request, ensure_ascii=False, sort_keys=True))
    risk_reasons: list[str] = []

    scan = scan_text(intent)
    if scan["status"] != "PASS":
        risk_reasons.append("protected_material_pattern_hold")
    if identity["contains_member_plaintext"]:
        risk_reasons.append("member_plaintext_hold")
    if force_hold:
        risk_reasons.append("operator_forced_hold")

    verifier_result = "HOLD" if risk_reasons else "PASS"
    risk_code = "risk_code:none" if verifier_result == "PASS" else "risk_code:dry_run_hold"
    hold_reason_code = "hold_reason_code:none" if verifier_result == "PASS" else "hold_reason_code:" + ",".join(risk_reasons)

    packet = {
        "run_id": request["run_id"],
        "intent_request_id": request["intent_request_id"],
        "candidate_action_id": candidate_action_id,
        "state_packet_id": state_packet_id,
        "multi_state_field_codes": [
            "intent_state",
            "authority_state",
            "spacetime_state",
            "evidence_state",
            "execution_state",
            "privacy_state",
            "packet_transport_state",
            "risk_governance_state",
        ],
        "state_field_relation_table": [
            {
                "from_state_field_ref": "intent_state",
                "to_state_field_ref": "risk_governance_state",
                "relation_code": "requires_pre_execution_verification",
            },
            {
                "from_state_field_ref": "authority_state",
                "to_state_field_ref": "execution_state",
                "relation_code": "requires_authority_and_consent",
            },
        ],
        "spacetime_index_ref": stable_ref("spacetime_index_ref", "owner_adi_mock:" + candidate_action_id),
        "identity_proxy_ref": identity["identity_proxy_ref"],
        "authority_scope_code": identity["authority_scope_code"],
        "consent_state_code": identity["consent_state_code"],
        "reference_code": stable_ref("reference_code", candidate_action_id),
        "coordinate_code": stable_ref("coordinate_code", candidate_action_id + ":coordinate"),
        "hash_value": content_hash,
        "mask_code": "mask_code:ref_only",
        "permission_code": "permission_code:dry_run_owner_authorized",
        "state_code": "state_code:verified_dry_run" if verifier_result == "PASS" else "state_code:hold",
        "verifier_result": verifier_result,
        "risk_code": risk_code,
        "hold_reason_code": hold_reason_code,
        "rule_version": rule_version,
        "timestamp_coordinate": timestamp,
        "previous_record_hash": "hash:" + ("0" * 64),
        "current_record_hash": "hash:pending_accountability_record",
        "db_write": False,
        "deploy": False,
        "restart": False,
    }
    record = build_accountability_record(
        candidate_action_id=candidate_action_id,
        state_packet_id=state_packet_id,
        rule_version=rule_version,
        verifier_result=verifier_result,
        timestamp_coordinate=timestamp,
        responsible_person_ref=identity["responsible_person_ref"],
    )
    packet["current_record_hash"] = record["current_record_hash"]
    return packet, record


def build_result(intent: str, *, force_hold: bool = False) -> dict[str, Any]:
    request = build_request(intent, force_hold=force_hold)
    packet, record = build_state_packet(request)
    result = packet["verifier_result"]
    return {
        "state": "PRODUCT_INTENT_FIELD_DRY_RUN_P0",
        "run_id": request["run_id"],
        "dry_run_only": True,
        "request": request,
        "state_packet": packet,
        "verifier_result": {
            "result": result,
            "risk_code": packet["risk_code"],
            "hold_reason_code": packet["hold_reason_code"],
        },
        "dry_run_output": {
            "restricted_execution_instruction_ref": stable_ref("restricted_execution_instruction_ref", packet["state_packet_id"])
            if result == "PASS"
            else "",
            "hold_packet_ref": stable_ref("hold_packet_ref", packet["state_packet_id"]) if result == "HOLD" else "",
            "front_edge_proxy": "dry_run_restricted_preview_only" if result == "PASS" else "dry_run_blocked",
            "db_write": False,
            "deploy": False,
            "restart": False,
        },
        "accountability_record": record,
        "db_write": False,
        "deploy": False,
        "restart": False,
    }
