"""LINE Official Account configuration candidate helper.

The helper turns a natural-language operator intent into a local, evidence
sealed configuration candidate. It performs no LINE API calls, reads no
secrets, and never changes official account settings.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any


REQUIRED_LINE_OFFICIAL_REFS = [
    "line_official_account_ref",
    "line_provider_ref",
    "messaging_api_channel_ref",
    "webhook_endpoint_ref",
    "channel_secret_ref",
    "channel_access_token_runtime_ref",
    "message_policy_ref",
    "audience_policy_ref",
    "consent_policy_ref",
    "human_owner_admin_release_ref",
]

SAFE_REF_PATTERN = re.compile(r"[A-Z0-9_:-]{6,180}")
HEX64_PATTERN = re.compile(r"[a-f0-9]{64}")
JWT_SHAPE_PATTERN = re.compile(r"[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}")
LONG_TOKEN_SHAPE_PATTERN = re.compile(r"(?=.*[A-Za-z])(?=.*[0-9])[A-Za-z0-9_~+/=-]{40,}")


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def has_secret_or_plaintext_shape(value: Any) -> bool:
    text = str(value or "")
    return bool(
        re.search(r"sk-[A-Za-z0-9_-]{12,}", text)
        or re.search(r"(?i)(access|refresh|id)_token\s*[:=]\s*\S+", text)
        or re.search(r"(?i)channel_secret\s*[:=]\s*\S+", text)
        or re.search(r"(?i)client_secret\s*[:=]\s*\S+", text)
        or re.search(r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----", text)
        or re.search(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}", text)
        or re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
        or re.search(r"09\d{2}[- ]?\d{3}[- ]?\d{3}", text)
        or re.search(r"\b[A-Z][12]\d{8}\b", text)
        or JWT_SHAPE_PATTERN.search(text)
        or LONG_TOKEN_SHAPE_PATTERN.search(text)
    )


def redact_text(text: Any, limit: int = 420) -> tuple[str, list[str]]:
    redacted = " ".join(str(text or "").split())
    flags: list[str] = []
    replacements = [
        (r"sk-[A-Za-z0-9_-]{12,}", "[SECRET_REF]", "secret_shape_redacted"),
        (r"(?i)(access|refresh|id)_token\s*[:=]\s*\S+", "[TOKEN_REF]", "token_shape_redacted"),
        (r"(?i)channel_secret\s*[:=]\s*\S+", "[CHANNEL_SECRET_REF]", "secret_shape_redacted"),
        (r"(?i)client_secret\s*[:=]\s*\S+", "[CLIENT_SECRET_REF]", "secret_shape_redacted"),
        (r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}", "[BEARER_REF]", "token_shape_redacted"),
        (r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[MEMBER_REF]", "member_plaintext_shape_redacted"),
        (r"09\d{2}[- ]?\d{3}[- ]?\d{3}", "[MEMBER_REF]", "member_plaintext_shape_redacted"),
        (r"\b[A-Z][12]\d{8}\b", "[MEMBER_REF]", "member_plaintext_shape_redacted"),
        (JWT_SHAPE_PATTERN.pattern, "[JWT_REF]", "token_shape_redacted"),
        (LONG_TOKEN_SHAPE_PATTERN.pattern, "[TOKEN_VALUE_REF]", "token_shape_redacted"),
    ]
    for pattern, replacement, flag in replacements:
        if re.search(pattern, redacted):
            flags.append(flag)
            redacted = re.sub(pattern, replacement, redacted)
    return redacted[:limit], sorted(set(flags))


def is_safe_ref(value: Any) -> bool:
    text = str(value or "").strip()
    return (
        (HEX64_PATTERN.fullmatch(text.lower()) is not None or ("REF" in text and SAFE_REF_PATTERN.fullmatch(text) is not None))
        and text == str(value or "")
        and not has_secret_or_plaintext_shape(text)
    )


def _normalized_refs(refs: dict | None) -> tuple[dict, list[str]]:
    refs = refs if isinstance(refs, dict) else {}
    normalized = {key: str(refs.get(key) or "").strip() for key in REQUIRED_LINE_OFFICIAL_REFS}
    warnings = []
    for key, value in normalized.items():
        if not value:
            warnings.append(f"missing_ref:{key}")
        elif not is_safe_ref(value):
            warnings.append(f"unsafe_ref:{key}")
    return normalized, warnings


def _intent_features(redacted_intent: str) -> dict:
    text = redacted_intent.lower()
    zh = redacted_intent
    return {
        "member_onboarding_requested": any(word in zh for word in ["會員", "領用", "小J", "新朋友", "加入"]),
        "promotion_requested": any(word in zh for word in ["促銷", "優惠", "活動", "推播", "廣播"]),
        "customer_service_requested": any(word in zh for word in ["客服", "詢問", "回覆", "服務"]),
        "webhook_required": "webhook" in text or "事件" in zh or "加入" in zh or "訊息" in zh,
        "payment_or_order_boundary_requested": any(word in zh for word in ["付款", "訂單", "下單", "個資", "不能由 llm", "不得由 LLM"]),
        "human_approval_requested": any(word in zh for word in ["核定", "審核", "不要直接", "不直接", "供我"]),
    }


def build_line_official_account_config_candidate(
    intent_text: Any,
    refs: dict | None = None,
    style_ref: Any = "STYLE_REF_XIAOJ_WARM_PRECISE",
    operator_ref: Any = "OPERATOR_REF_LINE_OFFICIAL_ACCOUNT_REVIEW",
) -> dict:
    redacted_intent, redaction_flags = redact_text(intent_text)
    normalized_refs, ref_warnings = _normalized_refs(refs)
    style_ref = str(style_ref or "").strip()
    operator_ref = str(operator_ref or "").strip()
    features = _intent_features(redacted_intent)
    warnings = list(ref_warnings)
    if not redacted_intent:
        warnings.append("intent_text_required")
    if not is_safe_ref(style_ref):
        warnings.append("style_ref_unsafe")
    if not is_safe_ref(operator_ref):
        warnings.append("operator_ref_unsafe")
    if redaction_flags:
        warnings.append("intent_text_redacted_requires_review")

    proposed_config = {
        "line_official_account_ref": normalized_refs["line_official_account_ref"],
        "messaging_api_channel_ref": normalized_refs["messaging_api_channel_ref"],
        "webhook_endpoint_ref": normalized_refs["webhook_endpoint_ref"],
        "messaging_api_required": True,
        "webhook_required": True,
        "welcome_flow": {
            "enabled_candidate": features["member_onboarding_requested"] or features["customer_service_requested"],
            "message_style_ref": style_ref,
            "ask_sovereign_xiaoj_claim": features["member_onboarding_requested"],
            "execution_allowed": False,
        },
        "promotion_policy": {
            "enabled_candidate": features["promotion_requested"],
            "requires_consent_policy_ref": normalized_refs["consent_policy_ref"],
            "requires_audience_policy_ref": normalized_refs["audience_policy_ref"],
            "broadcast_without_release": False,
        },
        "authority_boundaries": {
            "llm_direct_setting_change": False,
            "llm_payment_authority": False,
            "llm_order_authority": False,
            "llm_member_identity_authority": False,
            "human_owner_admin_release_required": True,
            "runtime_resolver_secret_read_only_after_release": True,
        },
    }
    verifier_checks = [
        "no_plaintext_token_or_secret",
        "line_official_account_not_lineworks",
        "messaging_api_channel_ref_present",
        "webhook_endpoint_ref_present",
        "message_policy_ref_present",
        "audience_policy_ref_present",
        "consent_policy_ref_present",
        "human_owner_admin_release_ref_present",
        "llm_execution_forbidden",
    ]
    ready = not warnings
    state = "READY_FOR_HUMAN_APPROVAL" if ready else "HOLD_NEEDS_HUMAN_APPROVAL"
    packet_seed = {
        "intent": redacted_intent,
        "refs": normalized_refs,
        "style_ref": style_ref,
        "operator_ref": operator_ref,
        "proposed_config": proposed_config,
        "warnings": warnings,
    }
    packet_hash = stable_hash(packet_seed)
    return {
        "schema": "W7TP_XIAOJ_LINE_OFFICIAL_ACCOUNT_CONFIG_CANDIDATE_V1",
        "state": state,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "surface": "LINE_OFFICIAL_ACCOUNT_MESSAGING_API",
        "intent": "line_official_account_config_candidate",
        "line_official_account_is_not_lineworks": True,
        "natural_language_intent": redacted_intent,
        "intent_features": features,
        "redaction_flags": redaction_flags,
        "required_refs": list(REQUIRED_LINE_OFFICIAL_REFS),
        "refs": normalized_refs,
        "proposed_config": proposed_config,
        "local_verifier": {
            "decision": "READY_FOR_HUMAN_APPROVAL" if ready else "HOLD",
            "checks": verifier_checks,
            "failure_reasons": warnings,
            "llm_execution_allowed": False,
            "human_owner_admin_release_required": True,
        },
        "authority_packet": {
            "packet_hash": packet_hash,
            "evidence_hash": stable_hash({"packet_hash": packet_hash, "state": state}),
            "release_required": True,
            "human_approval_required": True,
            "official_account_setting_changed": False,
        },
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
        "redaction": {
            "channel_access_token_echo": False,
            "channel_secret_echo": False,
            "line_password_echo": False,
            "member_plaintext_echo": False,
            "raw_user_id_echo": False,
        },
    }
