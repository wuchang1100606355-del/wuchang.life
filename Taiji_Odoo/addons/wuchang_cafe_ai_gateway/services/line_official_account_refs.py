"""LINE Official Account refs draft helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .line_official_account_config import REQUIRED_LINE_OFFICIAL_REFS, has_secret_or_plaintext_shape, is_safe_ref, stable_hash


DEFAULT_REFS = {
    "line_official_account_ref": "REF_LINE_OFFICIAL_ACCOUNT_TO_FILL",
    "line_provider_ref": "REF_LINE_PROVIDER_TO_FILL",
    "messaging_api_channel_ref": "REF_MESSAGING_API_CHANNEL_TO_FILL",
    "webhook_endpoint_ref": "REF_WEBHOOK_ENDPOINT_TO_FILL",
    "channel_secret_ref": "REF_CHANNEL_SECRET_VAULT_BINDING_TO_FILL",
    "channel_access_token_runtime_ref": "REF_CHANNEL_ACCESS_TOKEN_RUNTIME_BINDING_TO_FILL",
    "message_policy_ref": "REF_MESSAGE_POLICY_TO_FILL",
    "audience_policy_ref": "REF_AUDIENCE_POLICY_TO_FILL",
    "consent_policy_ref": "REF_CONSENT_POLICY_TO_FILL",
    "human_owner_admin_release_ref": "REF_HUMAN_OWNER_ADMIN_RELEASE_TO_FILL",
}


def _is_placeholder(value: Any) -> bool:
    text = str(value or "")
    return not text or text.startswith("REF_") or text.endswith("_TO_FILL") or "PLACEHOLDER" in text


def build_line_official_account_refs_draft(refs: dict | None = None) -> dict:
    refs = refs if isinstance(refs, dict) else {}
    normalized = {}
    warnings = []
    for key in REQUIRED_LINE_OFFICIAL_REFS:
        value = str(refs.get(key) or DEFAULT_REFS[key]).strip()
        normalized[key] = value
        if _is_placeholder(value):
            warnings.append(f"placeholder_ref:{key}")
        if not is_safe_ref(value):
            warnings.append(f"unsafe_ref:{key}")
        if has_secret_or_plaintext_shape(value):
            warnings.append(f"secret_or_plaintext_shape:{key}")
    state = "LINE_OFFICIAL_ACCOUNT_REFS_READY_FOR_CONFIG_CANDIDATE" if not warnings else "HOLD_LINE_OFFICIAL_ACCOUNT_REFS_DRAFT"
    return {
        "schema": "W7TP_XIAOJ_LINE_OFFICIAL_ACCOUNT_REFS_DRAFT_V1",
        "state": state,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "usage": "Refs only. Do not paste LINE passwords, channel secrets, channel access tokens, raw LINE user IDs, or member plaintext.",
        "refs": normalized,
        "draft_warnings": warnings,
        "draft_hash": stable_hash({"refs": normalized, "warnings": warnings}),
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
