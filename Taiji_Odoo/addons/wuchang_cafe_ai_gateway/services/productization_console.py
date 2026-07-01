"""P1/P2-safe XiaoJ total productization console services.

These builders create review packets only. They do not write Odoo records,
invoke models, read credentials, send LINE WORKS messages, create POS orders,
capture payments, or move member/resident plaintext into prompts.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from .lineworks_handoff import build_lineworks_operator_handoff_pack
from .llm_cost_saving_model_router import build_llm_cost_saving_model_router_candidate
from .p1_intent_engine import formal_release_status_payload


SECRET_OR_PII_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"(?i)(access|refresh|id)_token\s*[:=]\s*\S+"),
    re.compile(r"(?i)api[_ -]?key\s*[:=]\s*\S+"),
    re.compile(r"(?i)(channel|client|router|odoo|lineworks|line)[_-]?secret\s*[:=]\s*\S+"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}"),
    re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
    re.compile(r"09\d{2}[- ]?\d{3}[- ]?\d{3}"),
    re.compile(r"\b[A-Z][12]\d{8}\b"),
]

PRODUCT_LINES = [
    "merchant_branch_xiaoj",
    "association_total_field_member_service_xiaoj",
    "eightd_sovereign_member_system",
    "eightd_sovereign_resident_property_management",
]

MEMBER_LLM_REQUIRED_REFS = [
    "member_ref",
    "model_ref",
    "quota_ref",
    "consent_ref",
    "truth_boundary_ref",
    "gemini_key_ref",
    "release_packet_hash",
]

LOCAL_PII_RETURN_REQUIRED_REFS = [
    "member_ref",
    "consent_ref",
    "local_vault_ref",
    "encrypted_payload_hash",
]

DELEGATE_ROTATION_REQUIRED_REFS = [
    "old_packet_ref",
    "new_packet_ref",
    "revocation_ref",
    "owner_admin_or_quorum_ref",
    "evidence_chain_hash",
]

SOVEREIGN_XIAOJ_CLAIM_REQUIRED_REFS = [
    "member_ref",
    "xiaoj_instance_ref",
    "device_ref",
    "claim_packet_hash",
    "revocation_ref",
    "transfer_policy_ref",
]


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def side_effects_false() -> dict:
    return {
        "external_api_call": False,
        "model_invocation": False,
        "formal_lineworks_send": False,
        "formal_line_message_send": False,
        "formal_member_registration": False,
        "formal_db_write": False,
        "db_write": False,
        "formal_pos_write": False,
        "pos_order_created": False,
        "payment_capture": False,
        "secret_read": False,
        "raw_api_key_read": False,
        "raw_api_key_saved": False,
        "member_plaintext_read": False,
        "resident_plaintext_read": False,
        "member_plaintext_to_prompt": False,
        "resident_plaintext_to_prompt": False,
        "raw_audio_saved": False,
        "raw_video_saved": False,
        "runtime_model_changed": False,
        "deploy": False,
        "service_restart": False,
    }


def _contains_secret_or_pii(value: Any) -> bool:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value or "")
    return any(pattern.search(text) for pattern in SECRET_OR_PII_PATTERNS)


def reject_secret_or_plaintext(value: Any, label: str) -> None:
    if _contains_secret_or_pii(value):
        raise ValueError(f"secret-shaped or plaintext-shaped material is not allowed in {label}")


def _refs(refs: dict | None) -> dict:
    refs = refs if isinstance(refs, dict) else {}
    reject_secret_or_plaintext(refs, "productization refs")
    return refs


def _missing(refs: dict, required: list[str]) -> list[str]:
    return [key for key in required if not str(refs.get(key) or "").strip()]


def _state_for(required_missing: list[str], ready_state: str, hold_state: str) -> str:
    return ready_state if not required_missing else hold_state


def _release_gate_summary(formal_status: dict) -> dict:
    gates = formal_status.get("formal_release_gates", {}) if isinstance(formal_status, dict) else {}
    return {
        "formal_member_registration": gates.get("member_registration", {}).get("decision", "HOLD"),
        "formal_pos_order": gates.get("pos_order", {}).get("decision", "HOLD"),
        "formal_payment": gates.get("payment", {}).get("decision", "HOLD"),
        "lineworks_send": gates.get("lineworks_send", {}).get("decision", "HOLD"),
        "sovereign_xiaoj_claim": "HOLD_P2_SOVEREIGN_XIAOJ_CLAIM_REQUIRED",
        "local_personal_data_return": "HOLD_P2_LOCAL_VAULT_RETURN_REQUIRED",
        "member_llm_release": "HOLD_P2_MEMBER_LLM_RELEASE_REQUIRED",
        "eightd_delegate_rotation": "HOLD_P2_DELEGATE_ROTATION_REQUIRED",
    }


def build_sovereign_member_llm_release_gate(*, refs: dict | None = None) -> dict:
    refs = _refs(refs)
    missing = _missing(refs, MEMBER_LLM_REQUIRED_REFS)
    packet_seed = {"refs": refs, "missing": missing, "gate": "member_llm_release"}
    return {
        "schema": "W7TP_MEMBER_LLM_RELEASE_GATE_V1",
        "state": _state_for(missing, "READY_FOR_HUMAN_REVIEW", "HOLD_MEMBER_LLM_RELEASE_REFS_REQUIRED"),
        "generated_at_utc": now_utc(),
        "required_refs": MEMBER_LLM_REQUIRED_REFS,
        "missing_refs": missing,
        "cloud_model_authority": False,
        "raw_api_key_allowed": False,
        "raw_api_key_storage_allowed": False,
        "candidate_only": True,
        "local_verifier_required": True,
        "human_owner_admin_release_required": True,
        "recommended_runtime_candidate_model": "gemini-2.5-flash-lite",
        "packet_hash": stable_hash(packet_seed),
        "side_effects": side_effects_false(),
    }


def build_local_personal_data_return_packet(*, refs: dict | None = None) -> dict:
    refs = _refs(refs)
    missing = _missing(refs, LOCAL_PII_RETURN_REQUIRED_REFS)
    packet_seed = {"refs": refs, "missing": missing, "gate": "local_personal_data_return"}
    return {
        "schema": "W7TP_LOCAL_PERSONAL_DATA_RETURN_PACKET_V1",
        "state": _state_for(missing, "READY_FOR_HUMAN_REVIEW", "HOLD_ENCRYPTED_LOCAL_VAULT_REF_REQUIRED"),
        "generated_at_utc": now_utc(),
        "required_refs": LOCAL_PII_RETURN_REQUIRED_REFS,
        "missing_refs": missing,
        "cloud_llm_receives_personal_data": False,
        "prompt_contains_personal_data": False,
        "personal_data_to_cloud_llm": False,
        "requires_consent_ref": True,
        "requires_local_vault_ref": True,
        "packet_hash": stable_hash(packet_seed),
        "side_effects": side_effects_false(),
    }


def build_8d_delegate_rotation_draft(*, refs: dict | None = None) -> dict:
    refs = _refs(refs)
    missing = _missing(refs, DELEGATE_ROTATION_REQUIRED_REFS)
    packet_seed = {"refs": refs, "missing": missing, "gate": "8d_delegate_rotation"}
    return {
        "schema": "W7TP_8D_DELEGATE_ROTATION_DRAFT_V1",
        "state": _state_for(missing, "READY_FOR_HUMAN_REVIEW", "HOLD_8D_DELEGATE_ROTATION_REFS_REQUIRED"),
        "generated_at_utc": now_utc(),
        "required_refs": DELEGATE_ROTATION_REQUIRED_REFS,
        "missing_refs": missing,
        "old_delegate_revoked_by_default": False,
        "new_delegate_activated_by_default": False,
        "requires_owner_admin_or_quorum_ref": True,
        "requires_evidence_chain_hash": True,
        "packet_hash": stable_hash(packet_seed),
        "side_effects": side_effects_false(),
    }


def build_sovereign_xiaoj_claim_draft(*, refs: dict | None = None) -> dict:
    refs = _refs(refs)
    missing = _missing(refs, SOVEREIGN_XIAOJ_CLAIM_REQUIRED_REFS)
    packet_seed = {"refs": refs, "missing": missing, "gate": "sovereign_xiaoj_claim"}
    return {
        "schema": "W7TP_SOVEREIGN_XIAOJ_CLAIM_DRAFT_V1",
        "state": _state_for(missing, "READY_FOR_HUMAN_REVIEW", "HOLD_SOVEREIGN_XIAOJ_CLAIM_REFS_REQUIRED"),
        "generated_at_utc": now_utc(),
        "required_refs": SOVEREIGN_XIAOJ_CLAIM_REQUIRED_REFS,
        "missing_refs": missing,
        "claim_activated_by_default": False,
        "device_bound_by_default": False,
        "transfer_allowed_by_default": False,
        "requires_revocation_ref": True,
        "requires_human_owner_admin_release": True,
        "packet_hash": stable_hash(packet_seed),
        "side_effects": side_effects_false(),
    }


def build_xiaoj_total_product_console_status(*, refs: dict | None = None, actor_ref: Any = "") -> dict:
    refs = _refs(refs)
    reject_secret_or_plaintext(actor_ref, "actor_ref")
    formal_refs = refs.get("formal_release_refs") if isinstance(refs.get("formal_release_refs"), dict) else {}
    lineworks_refs = refs.get("lineworks_refs") if isinstance(refs.get("lineworks_refs"), dict) else {}
    model_refs = refs.get("model_refs") if isinstance(refs.get("model_refs"), dict) else {}
    member_llm_refs = refs.get("member_llm_refs") if isinstance(refs.get("member_llm_refs"), dict) else {}
    local_pii_refs = refs.get("local_personal_data_return_refs") if isinstance(refs.get("local_personal_data_return_refs"), dict) else {}
    delegate_refs = refs.get("delegate_rotation_refs") if isinstance(refs.get("delegate_rotation_refs"), dict) else {}
    claim_refs = refs.get("sovereign_xiaoj_claim_refs") if isinstance(refs.get("sovereign_xiaoj_claim_refs"), dict) else {}

    formal_status = formal_release_status_payload(formal_refs)
    lineworks_handoff = build_lineworks_operator_handoff_pack(
        refs=lineworks_refs,
        refs_path="api:/wuchang/xiaoj/api/total-product-console-status:lineworks_refs",
        actor_ref=str(actor_ref or "ACTOR_REF_TOTAL_PRODUCT_CONSOLE"),
        confirm_human_activation=False,
    )
    model_route = build_llm_cost_saving_model_router_candidate(
        task_intent="total product console status candidate",
        task_surface="routine_member_service",
        refs=model_refs,
        allow_external_candidate=False,
    )
    member_llm = build_sovereign_member_llm_release_gate(refs=member_llm_refs)
    local_pii = build_local_personal_data_return_packet(refs=local_pii_refs)
    delegate_rotation = build_8d_delegate_rotation_draft(refs=delegate_refs)
    sovereign_claim = build_sovereign_xiaoj_claim_draft(refs=claim_refs)

    release_gates = _release_gate_summary(formal_status)
    release_gates["member_llm_release"] = member_llm["state"]
    release_gates["local_personal_data_return"] = local_pii["state"]
    release_gates["eightd_delegate_rotation"] = delegate_rotation["state"]
    release_gates["sovereign_xiaoj_claim"] = sovereign_claim["state"]
    p2_blockers = [
        key for key, state in release_gates.items()
        if str(state or "").startswith("HOLD") or str(state or "").startswith("HOLD_")
    ]
    packet_seed = {
        "formal": formal_status.get("state"),
        "lineworks": lineworks_handoff.get("state"),
        "model": model_route.get("state"),
        "release_gates": release_gates,
        "p2_blockers": sorted(p2_blockers),
    }
    return {
        "schema": "W7TP_XIAOJ_TOTAL_PRODUCT_CONSOLE_STATUS_V1",
        "state": "READY_FOR_HUMAN_REVIEW" if not p2_blockers else "HOLD_P2_RELEASE_REFS_REQUIRED",
        "generated_at_utc": now_utc(),
        "actor_ref": str(actor_ref or ""),
        "product_lines": PRODUCT_LINES,
        "human_world_refs": {
            "owner_admin_ref_required": True,
            "merchant_manager_ref_required": True,
            "association_ref_required": True,
            "sponsor_org_ref_required": True,
            "plaintext_email_in_public_contract": False,
        },
        "lineworks": {
            "handoff_state": lineworks_handoff.get("state"),
            "preflight_ready": lineworks_handoff.get("readiness", {}).get("preflight_send_allowed") is True,
            "formal_send": False,
            "runtime_dry_run_external_api_call": False,
        },
        "low_cost_model_governance": {
            "route_state": model_route.get("state"),
            "recommended_code_model": "gpt-5.4-mini",
            "recommended_runtime_candidate_model": "gemini-2.5-flash-lite",
            "nano_architecture_decision_allowed": False,
            "cloud_model_candidate_only": True,
        },
        "release_gates": release_gates,
        "p2_blockers": p2_blockers,
        "formal_release_status": {
            "state": formal_status.get("state"),
            "formal_member_registration_release": formal_status.get("formal_member_registration_release"),
            "formal_pos_order_release": formal_status.get("formal_pos_order_release"),
            "formal_payment_release": formal_status.get("formal_payment_release"),
            "formal_lineworks_send_release": formal_status.get("formal_lineworks_send_release"),
        },
        "draft_packets": {
            "member_llm_release_gate": member_llm,
            "local_personal_data_return_packet": local_pii,
            "delegate_rotation": delegate_rotation,
            "sovereign_xiaoj_claim": sovereign_claim,
        },
        "login_test_mode": "candidate_dry_run_preflight_only",
        "production_activation_ready": False,
        "packet_hash": stable_hash(packet_seed),
        "side_effects": side_effects_false(),
    }
