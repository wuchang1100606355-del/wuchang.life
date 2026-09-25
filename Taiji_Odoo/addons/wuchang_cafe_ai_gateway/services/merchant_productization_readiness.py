"""Unified XiaoJ merchant productization readiness service.

This service aggregates LINE WORKS, LINE Official Account, member
registration, POS order, and payment release gates. It performs no external API
calls, no Odoo DB writes, no LINE/LINE WORKS sends, no POS writes, no payment
captures, no secret reads, and no deploys or restarts.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from .line_official_account_config import build_line_official_account_config_candidate
from .line_official_account_refs import build_line_official_account_refs_draft
from .lineworks_connector import REQUIRED_CONNECTOR_REFS, build_lineworks_send_preflight
from .p1_intent_engine import FORMAL_RELEASE_GATES, formal_release_status_payload, lineworks_notify_payload


DEFAULT_LINE_OFFICIAL_INTENT = (
    "Configure LINE Official Account for cafe member service. New friends are welcomed "
    "and asked whether they want to claim sovereign XiaoJ. Promotions go only to "
    "consented members. Payment, orders, and personal data cannot be decided by an LLM. "
    "Produce a candidate for human approval only."
)

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"(?i)(access|refresh|id)_token\s*[:=]\s*\S+"),
    re.compile(r"(?i)channel_secret\s*[:=]\s*\S+"),
    re.compile(r"(?i)client_secret\s*[:=]\s*\S+"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}"),
]


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def has_secret_shape(value: Any) -> bool:
    text = str(value or "")
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def reject_secret_shapes(value: Any, label: str) -> None:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True) if not isinstance(value, str) else value
    if has_secret_shape(serialized):
        raise ValueError(f"secret-shaped material is not allowed in {label}; use refs only")


def is_placeholder_ref(value: Any) -> bool:
    text = str(value or "")
    return (
        not text
        or text.startswith("REF_")
        or text.endswith("_NO_SECRET")
        or text.endswith("_NO_MEMBER_PLAINTEXT")
        or text.endswith("_NO_TOKEN_VALUE")
        or text.endswith("_TO_FILL")
        or "PLACEHOLDER" in text
        or text == "0" * 64
    )


def p1_side_effects() -> dict:
    return {
        "external_api_call": False,
        "formal_lineworks_send": False,
        "formal_line_message_send": False,
        "official_account_setting_changed": False,
        "formal_member_registration": False,
        "formal_db_write": False,
        "formal_pos_write": False,
        "payment_capture": False,
        "secret_read": False,
        "member_plaintext_read": False,
        "deploy": False,
        "service_restart": False,
    }


def release_ref_readiness(refs: dict, required_refs: list[str]) -> dict:
    gate_refs = refs.get("lineworks_send") if isinstance(refs.get("lineworks_send"), dict) else {}
    missing = [key for key in required_refs if key not in gate_refs]
    unverified = []
    placeholders = []
    for key in required_refs:
        value = gate_refs.get(key) if isinstance(gate_refs, dict) else None
        if not isinstance(value, dict):
            continue
        if value.get("verified") is not True:
            unverified.append(key)
        if is_placeholder_ref(value.get("ref")) or is_placeholder_ref(value.get("packet_hash")):
            placeholders.append(key)
    return {
        "missing_release_refs": missing,
        "unverified_release_refs": unverified,
        "placeholder_release_refs": placeholders,
    }


def connector_ref_readiness(refs: dict, required_connector_refs: list[str]) -> dict:
    connector_refs = refs.get("connector_refs") if isinstance(refs.get("connector_refs"), dict) else {}
    missing = [key for key in required_connector_refs if not connector_refs.get(key)]
    placeholders = [key for key in required_connector_refs if is_placeholder_ref(connector_refs.get(key))]
    return {
        "connector_refs": connector_refs,
        "missing_connector_refs": missing,
        "placeholder_connector_refs": placeholders,
    }


def formal_gate_summary(formal_status: dict) -> dict:
    gates = formal_status.get("formal_release_gates") if isinstance(formal_status.get("formal_release_gates"), dict) else {}
    summary = {}
    for gate_id, gate in gates.items():
        summary[gate_id] = {
            "title": gate.get("title", gate_id),
            "decision": gate.get("decision", ""),
            "release_ready": gate.get("release_ready") is True,
            "missing_refs": gate.get("missing_refs", []),
            "unverified_ref_keys": gate.get("unverified_ref_keys", []),
            "total_field_blocker": gate.get("total_field_blocker", ""),
            "release_packet_hash": gate.get("release_packet_hash", ""),
        }
    return summary


def lineworks_readiness(lineworks_refs: dict, probe: dict | None = None) -> dict:
    probe = probe if isinstance(probe, dict) else {}
    required_release_refs = list(FORMAL_RELEASE_GATES["lineworks_send"]["required_refs"])
    release_readiness = release_ref_readiness(lineworks_refs, required_release_refs)
    connector_readiness = connector_ref_readiness(lineworks_refs, REQUIRED_CONNECTOR_REFS)
    candidate = lineworks_notify_payload(
        probe.get("message") or "XiaoJ merchant productization readiness probe",
        probe.get("target_ref") or "TARGET_REF_READINESS_CHECK",
        probe.get("channel") or "member_service",
        probe.get("actor_ref") or "ACTOR_REF_READINESS_CHECK",
    )
    release_status = formal_release_status_payload({"lineworks_send": lineworks_refs.get("lineworks_send", {})})
    preflight = build_lineworks_send_preflight(
        candidate,
        release_status,
        connector_readiness["connector_refs"],
    )
    blockers = []
    for key in ["missing_release_refs", "unverified_release_refs", "placeholder_release_refs"]:
        if release_readiness[key]:
            blockers.append(key)
    for key in ["missing_connector_refs", "placeholder_connector_refs"]:
        if connector_readiness[key]:
            blockers.append(key)
    if preflight.get("unsafe_connector_ref_keys"):
        blockers.append("unsafe_connector_ref_keys")
    if preflight.get("unsafe_connector_ref_shape_keys"):
        blockers.append("unsafe_connector_ref_shape_keys")
    if preflight.get("send_allowed") is not True:
        blockers.append("lineworks_preflight_not_ready")
    return {
        "state": "PASS_LINEWORKS_RELEASE_READINESS" if not blockers else "HOLD_LINEWORKS_RELEASE_READINESS",
        "ready_for_human_activation": not blockers,
        "blockers": blockers,
        **release_readiness,
        "missing_connector_refs": connector_readiness["missing_connector_refs"],
        "placeholder_connector_refs": connector_readiness["placeholder_connector_refs"],
        "preflight_state": preflight.get("state", ""),
        "preflight_send_allowed": preflight.get("send_allowed") is True,
        "release_gate_decision": release_status.get("formal_release_gates", {}).get("lineworks_send", {}).get("decision", ""),
        "candidate_packet_hash": candidate.get("authority_packet", {}).get("packet_hash", ""),
        "preflight_envelope_hash": preflight.get("request_envelope_hash", ""),
        "side_effects": {
            "external_api_call": False,
            "formal_lineworks_send": False,
            "secret_read": False,
            "member_plaintext_read": False,
            "db_write": False,
            "deploy": False,
            "service_restart": False,
        },
    }


def line_official_account_readiness(refs_payload: dict, intent: str | None = None) -> dict:
    refs_input = refs_payload.get("refs") if isinstance(refs_payload.get("refs"), dict) else refs_payload
    refs_draft = build_line_official_account_refs_draft(refs_input)
    candidate = build_line_official_account_config_candidate(
        intent or DEFAULT_LINE_OFFICIAL_INTENT,
        refs=refs_draft.get("refs", {}),
        style_ref="STYLE_REF_XIAOJ_WARM_PRECISE",
        operator_ref="OPERATOR_REF_LINE_OFFICIAL_ACCOUNT_REVIEW",
    )
    blockers = []
    if refs_draft.get("state") != "LINE_OFFICIAL_ACCOUNT_REFS_READY_FOR_CONFIG_CANDIDATE":
        blockers.append("line_official_account_refs_not_ready")
    if candidate.get("state") != "READY_FOR_HUMAN_APPROVAL":
        blockers.append("line_official_account_config_candidate_not_ready")
    return {
        "state": "PASS_LINE_OFFICIAL_ACCOUNT_READY_FOR_HUMAN_APPROVAL" if not blockers else "HOLD_LINE_OFFICIAL_ACCOUNT_REFS_OR_CONFIG",
        "ready_for_human_approval": not blockers,
        "blockers": blockers,
        "refs_state": refs_draft.get("state", ""),
        "refs_warnings": refs_draft.get("draft_warnings", []),
        "candidate_state": candidate.get("state", ""),
        "candidate_failure_reasons": candidate.get("local_verifier", {}).get("failure_reasons", []),
        "candidate_packet_hash": candidate.get("authority_packet", {}).get("packet_hash", ""),
        "evidence_hash": candidate.get("authority_packet", {}).get("evidence_hash", ""),
        "side_effects": {
            "external_api_call": False,
            "formal_line_message_send": False,
            "official_account_setting_changed": False,
            "secret_read": False,
            "member_plaintext_read": False,
            "db_write": False,
            "deploy": False,
            "service_restart": False,
        },
    }


def operator_next_actions(formal_gates: dict, lineworks: dict, line_official: dict) -> list[str]:
    actions = []
    if not line_official.get("ready_for_human_approval"):
        actions.append("fill_line_official_account_safe_refs_and_rerun_config_candidate")
    if not lineworks.get("ready_for_human_activation"):
        actions.append("fill_verified_lineworks_release_refs_and_runtime_connector_refs")
    gate_labels = {
        "member_registration": "fill_verified_member_registration_release_refs",
        "pos_order": "fill_verified_pos_order_release_refs",
        "payment": "fill_verified_payment_release_refs",
        "lineworks_send": "fill_verified_lineworks_send_release_refs",
    }
    for gate_id, gate in formal_gates.items():
        if gate.get("release_ready") is not True:
            actions.append(gate_labels.get(gate_id, f"fill_verified_{gate_id}_release_refs"))
    if not actions:
        actions.append("human_owner_admin_review_then_create_runtime_activation_packet")
    return sorted(dict.fromkeys(actions))


def build_merchant_productization_readiness(
    *,
    formal_release_refs: dict | None = None,
    lineworks_refs: dict | None = None,
    line_official_account_refs: dict | None = None,
    line_official_account_intent: str | None = None,
    lineworks_probe: dict | None = None,
    input_ref: str = "",
    lineworks_refs_path: str = "",
    line_official_account_refs_path: str = "",
) -> dict:
    formal_release_refs = formal_release_refs if isinstance(formal_release_refs, dict) else {}
    lineworks_refs = lineworks_refs if isinstance(lineworks_refs, dict) else {}
    line_official_account_refs = line_official_account_refs if isinstance(line_official_account_refs, dict) else {}
    reject_secret_shapes(formal_release_refs, "formal release refs")
    reject_secret_shapes(lineworks_refs, "lineworks refs")
    reject_secret_shapes(line_official_account_refs, "line official account refs")
    reject_secret_shapes(line_official_account_intent or "", "line official account intent")

    formal_status_input = dict(formal_release_refs)
    formal_status_input.setdefault("lineworks_send", lineworks_refs.get("lineworks_send", {}))
    formal_status = formal_release_status_payload(formal_status_input)
    formal_gates = formal_gate_summary(formal_status)
    lineworks = lineworks_readiness(lineworks_refs, lineworks_probe)
    line_official = line_official_account_readiness(line_official_account_refs, line_official_account_intent)

    member_ready = formal_gates.get("member_registration", {}).get("release_ready") is True
    pos_ready = formal_gates.get("pos_order", {}).get("release_ready") is True
    payment_ready = formal_gates.get("payment", {}).get("release_ready") is True
    lineworks_ready = lineworks.get("ready_for_human_activation") is True
    line_official_ready = line_official.get("ready_for_human_approval") is True
    product_ready = member_ready and pos_ready and payment_ready and lineworks_ready and line_official_ready
    state = "PASS_XIAOJ_MERCHANT_PRODUCTIZATION_READINESS" if product_ready else "HOLD_XIAOJ_MERCHANT_PRODUCTIZATION_READINESS"
    report_seed = {
        "formal_gates": formal_gates,
        "lineworks_state": lineworks.get("state"),
        "line_official_state": line_official.get("state"),
    }
    return {
        "schema": "W7TP_XIAOJ_MERCHANT_PRODUCTIZATION_READINESS_REPORT_V1",
        "state": state,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "input_ref": input_ref,
        "lineworks_refs_path": lineworks_refs_path,
        "line_official_account_refs_path": line_official_account_refs_path,
        "product_ready_for_human_activation": product_ready,
        "p1_candidate_operations_ready": True,
        "formal_release_ready": {
            "member_registration": member_ready,
            "pos_order": pos_ready,
            "payment": payment_ready,
            "lineworks_send": lineworks_ready,
            "line_official_account_config": line_official_ready,
            "all_required_for_product_activation": product_ready,
        },
        "formal_release_gates": formal_gates,
        "lineworks": lineworks,
        "line_official_account": line_official,
        "operator_next_actions": operator_next_actions(formal_gates, lineworks, line_official),
        "authority_boundary": {
            "total_field_may_prepare_candidates": True,
            "human_owner_admin_root_of_trust": True,
            "llm_direct_execution": False,
            "cloud_model_authority": False,
            "runtime_activation_required": True,
        },
        "side_effects": p1_side_effects(),
        "report_hash": stable_hash(report_seed),
    }
