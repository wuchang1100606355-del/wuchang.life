"""LLM cost-saving model router candidate service.

The router decides which model lane should be proposed for a XiaoJ task without
calling any model, reading API keys, saving configuration, or granting execution
authority. It is a P1 candidate generator for human review and release.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any


SAFE_REF_PATTERN = re.compile(r"[A-Z0-9_:-]{6,180}")
HEX64_PATTERN = re.compile(r"[a-f0-9]{64}")

REQUIRED_REFS = [
    "local_model_ref",
    "external_candidate_model_ref",
    "gemini_key_ref_vault_binding",
    "member_llm_release_ref",
    "quota_policy_ref",
    "consent_policy_ref",
]

MODEL_ROLE_POLICY = {
    "total_field_planning_review": {
        "recommended_model": "gpt-5.5",
        "allowed_use": [
            "total-field planning",
            "patent core review",
            "red-team review",
            "final release judgment",
        ],
        "execution_authority": False,
    },
    "codex_engineering_cost_saving": {
        "recommended_model": "gpt-5.4-mini",
        "allowed_use": [
            "code implementation",
            "documentation fill",
            "focused verifier repair",
            "Odoo/LINE module modification",
        ],
        "execution_authority": False,
    },
    "merchant_runtime_candidate": {
        "recommended_model": "gemini-2.5-flash-lite",
        "allowed_use": [
            "customer-service draft",
            "menu copy candidate",
            "social post candidate",
            "natural-language intent candidate",
        ],
        "execution_authority": False,
    },
    "nano_utility_only": {
        "recommended_model": "gpt-5.4-nano",
        "allowed_use": [
            "classification",
            "format conversion",
            "field backfill",
            "verification report summary",
        ],
        "execution_authority": False,
        "architecture_decision_allowed": False,
    },
}

PRICE_SNAPSHOT = {
    "snapshot_date": "2026-07-01",
    "must_recheck_before_procurement": True,
    "sources": [
        "https://platform.openai.com/docs/pricing",
        "https://ai.google.dev/gemini-api/docs/pricing",
    ],
    "models": {
        "gpt-5.4-mini": {"input_per_1m_usd": 0.75, "output_per_1m_usd": 4.50},
        "gpt-5.4-nano": {"input_per_1m_usd": 0.20, "output_per_1m_usd": 1.25},
        "gemini-2.5-flash-lite": {"input_per_1m_usd": 0.10, "output_per_1m_usd": 0.40},
    },
}

RELEASE_SEQUENCE = [
    "complete_llm_cost_saving_model_router_doc_contract_verifier",
    "migrate_gemini_raw_key_to_gemini_key_ref_vault_binding",
    "add_member_llm_release_gate",
    "add_local_personal_data_return_packet",
    "add_8d_delegate_rotation_and_revocation",
    "add_sovereign_xiaoj_claim_activation",
    "only_then_enable_formal_pos_member_payment_release_gates",
]

LOCAL_FIRST_SURFACES = {
    "routine_member_service",
    "merchant_social_management",
    "pos_language_assist",
    "property_lobby_service",
    "property_case_triage",
    "association_member_service",
}

EXTERNAL_CANDIDATE_SURFACES = {
    "av_humanoid_service",
    "high_quality_dialogue",
    "long_context_summary",
    "vision_audio_understanding",
    "technical_reasoning_candidate",
}

AUTHORITY_ONLY_SURFACES = {
    "payment_execution",
    "pos_order_execution",
    "member_identity_authority",
    "property_access_authority",
}


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def side_effects_false() -> dict:
    return {
        "external_api_call": False,
        "model_invocation": False,
        "raw_api_key_read": False,
        "raw_api_key_saved": False,
        "member_plaintext_read": False,
        "resident_plaintext_read": False,
        "formal_db_write": False,
        "runtime_model_changed": False,
        "llm_execution_authority": False,
        "deploy": False,
        "service_restart": False,
    }


def has_secret_or_plaintext_shape(value: Any) -> bool:
    text = str(value or "")
    return bool(
        re.search(r"sk-[A-Za-z0-9_-]{12,}", text)
        or re.search(r"(?i)(access|refresh|id)_token\s*[:=]\s*\S+", text)
        or re.search(r"(?i)api[_ -]?key\s*[:=]\s*\S+", text)
        or re.search(r"(?i)client_secret\s*[:=]\s*\S+", text)
        or re.search(r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----", text)
        or re.search(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}", text)
        or re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
        or re.search(r"09\d{2}[- ]?\d{3}[- ]?\d{3}", text)
        or re.search(r"\b[A-Z][12]\d{8}\b", text)
    )


def is_safe_ref(value: Any) -> bool:
    text = str(value or "").strip()
    return (
        (HEX64_PATTERN.fullmatch(text.lower()) is not None or ("REF" in text and SAFE_REF_PATTERN.fullmatch(text) is not None))
        and text == str(value or "")
        and not has_secret_or_plaintext_shape(text)
    )


def _normalize_refs(refs: dict | None) -> tuple[dict, list[str]]:
    refs = refs if isinstance(refs, dict) else {}
    normalized = {}
    warnings = []
    for key in REQUIRED_REFS:
        value = str(refs.get(key) or f"REF_{key.upper()}_TO_FILL").strip()
        normalized[key] = value
        if value.endswith("_TO_FILL") or value.startswith("REF_"):
            warnings.append(f"placeholder_ref:{key}")
        if not is_safe_ref(value):
            warnings.append(f"unsafe_ref:{key}")
        if has_secret_or_plaintext_shape(value):
            warnings.append(f"secret_or_plaintext_shape:{key}")
    return normalized, warnings


def _surface_from_intent(task_intent: Any, task_surface: Any) -> str:
    surface = str(task_surface or "").strip()
    if surface:
        return surface
    text = str(task_intent or "").lower()
    zh = str(task_intent or "")
    if any(word in zh for word in ["付款", "正式下單", "會員身分", "門禁", "授權"]):
        return "authority_only"
    if any(word in zh for word in ["影音", "人形", "高品質", "長文", "視覺", "語音"]):
        return "high_quality_dialogue"
    if any(word in zh for word in ["物業", "大廳", "住戶"]):
        return "property_lobby_service"
    if any(word in zh for word in ["社群", "會員", "促銷", "客服", "點餐"]) or "member" in text:
        return "routine_member_service"
    return "routine_member_service"


def _lane(surface: str, allow_external_candidate: bool, refs_ready: bool) -> tuple[str, bool]:
    if surface in AUTHORITY_ONLY_SURFACES or surface == "authority_only":
        return "LOCAL_AUTHORITY_ONLY", False
    if surface in EXTERNAL_CANDIDATE_SURFACES:
        if allow_external_candidate and refs_ready:
            return "CLOUD_CANDIDATE_WITH_LOCAL_AUTHORITY", True
        return "LOCAL_FALLBACK_HOLD_EXTERNAL_REFS", False
    if surface in LOCAL_FIRST_SURFACES:
        return "LOCAL_FIRST", False
    if allow_external_candidate and refs_ready:
        return "LOCAL_FIRST_OPTIONAL_CLOUD_CANDIDATE", True
    return "LOCAL_FIRST", False


def build_llm_cost_saving_model_router_candidate(
    *,
    task_intent: Any = "",
    task_surface: Any = "",
    refs: dict | None = None,
    allow_external_candidate: bool = False,
) -> dict:
    if has_secret_or_plaintext_shape(task_intent) or has_secret_or_plaintext_shape(task_surface):
        raise ValueError("secret-shaped or plaintext-shaped material is not allowed in LLM model router intent")
    normalized_refs, warnings = _normalize_refs(refs)
    surface = _surface_from_intent(task_intent, task_surface)
    refs_ready = not warnings
    selected_lane, cloud_candidate_allowed = _lane(surface, allow_external_candidate, refs_ready)
    selected_model_ref = (
        normalized_refs["external_candidate_model_ref"]
        if cloud_candidate_allowed
        else normalized_refs["local_model_ref"]
    )
    if selected_lane == "LOCAL_AUTHORITY_ONLY":
        selected_model_ref = "LOCAL_DISCRETE_AUTHORITY_CORE_REF"
    state = "READY_FOR_HUMAN_MODEL_ROUTE_REVIEW" if not warnings else "HOLD_MODEL_ROUTE_REFS_REQUIRED"
    packet_seed = {
        "task_intent": str(task_intent or ""),
        "surface": surface,
        "refs": normalized_refs,
        "allow_external_candidate": allow_external_candidate,
        "selected_lane": selected_lane,
        "selected_model_ref": selected_model_ref,
        "warnings": warnings,
    }
    return {
        "schema": "W7TP_XIAOJ_LLM_COST_SAVING_MODEL_ROUTER_CANDIDATE_V1",
        "state": state,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "task_surface": surface,
        "selected_lane": selected_lane,
        "selected_model_ref": selected_model_ref,
        "cloud_candidate_allowed": cloud_candidate_allowed,
        "runtime_model_changed": False,
        "refs": normalized_refs,
        "local_verifier": {
            "decision": "READY_FOR_HUMAN_REVIEW" if not warnings else "HOLD",
            "failure_reasons": warnings,
            "llm_direct_execution": False,
            "cloud_model_authority": False,
            "human_release_required": True,
        },
        "cost_controls": {
            "local_first_default": True,
            "external_model_only_for_high_value_candidate": True,
            "daily_quota_ref_required": True,
            "member_consent_ref_required": True,
            "gemini_key_ref_required_instead_of_raw_key": True,
            "fallback_to_local_when_cloud_slow_or_unavailable": True,
        },
        "model_role_policy": MODEL_ROLE_POLICY,
        "price_snapshot": PRICE_SNAPSHOT,
        "release_sequence": RELEASE_SEQUENCE,
        "authority_boundary": {
            "llm_is_candidate_worker": True,
            "local_discrete_verifier_is_authority": True,
            "payment_pos_member_property_execution_by_llm": False,
            "raw_member_plaintext_to_model": False,
            "raw_resident_plaintext_to_model": False,
            "raw_api_key_to_model_router": False,
        },
        "side_effects": side_effects_false(),
        "packet_hash": stable_hash(packet_seed),
    }
