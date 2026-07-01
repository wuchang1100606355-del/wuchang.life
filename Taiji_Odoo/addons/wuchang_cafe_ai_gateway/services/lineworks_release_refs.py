"""LINE WORKS release refs draft helpers.

This module builds human-fillable release refs packets. It never reads
credentials, never writes databases, and never calls external APIs.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any


REQUIRED_RELEASE_REFS = [
    "authenticated_staff_ref",
    "lineworks_release_packet_ref",
    "lineworks_app_config_ref",
    "lineworks_bot_ref",
    "lineworks_target_user_ref",
    "message_policy_ref",
    "consent_policy_ref",
    "total_field_release_ref",
]
REQUIRED_CONNECTOR_REFS = [
    "lineworks_bot_ref",
    "lineworks_target_user_ref",
    "lineworks_access_token_runtime_ref",
]

RELEASE_REF_VERIFIER_ALLOWLIST = {
    "total_field_release_registry",
    "total_field_manual_release_packet",
    "d8_release_gate",
}

SAFE_RELEASE_REF_PATTERN = re.compile(r"[A-Z0-9_:-]{6,160}")
SAFE_CONNECTOR_REF_PATTERN = re.compile(r"[A-Z0-9_:-]{6,128}")
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
        or re.search(r"(?i)client_secret\s*[:=]\s*\S+", text)
        or re.search(r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----", text)
        or re.search(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}", text)
        or re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
        or re.search(r"09\d{2}[- ]?\d{3}[- ]?\d{3}", text)
        or re.search(r"\b[A-Z][12]\d{8}\b", text)
        or JWT_SHAPE_PATTERN.search(text)
        or LONG_TOKEN_SHAPE_PATTERN.search(text)
    )


def is_safe_release_ref(value: Any) -> bool:
    text = str(value or "").strip()
    return (
        text == str(value or "")
        and "REF" in text
        and SAFE_RELEASE_REF_PATTERN.fullmatch(text) is not None
        and not has_secret_or_plaintext_shape(text)
    )


def is_safe_connector_ref(value: Any) -> bool:
    text = str(value or "").strip()
    return (
        text == str(value or "")
        and "REF" in text
        and SAFE_CONNECTOR_REF_PATTERN.fullmatch(text) is not None
        and not has_secret_or_plaintext_shape(text)
    )


def is_safe_packet_hash(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return bool(HEX64_PATTERN.fullmatch(text)) and text != "0" * 64


def _provided_ref(raw_refs: dict, key: str) -> dict:
    raw_value = raw_refs.get(key) if isinstance(raw_refs, dict) else None
    if isinstance(raw_value, dict):
        return {
            "ref": str(raw_value.get("ref") or "").strip(),
            "packet_hash": str(raw_value.get("packet_hash") or "").strip().lower(),
            "verifier": str(raw_value.get("verifier") or "total_field_manual_release_packet").strip(),
            "verified": raw_value.get("verified") is True,
        }
    if raw_value:
        return {
            "ref": str(raw_value).strip(),
            "packet_hash": "",
            "verifier": "total_field_manual_release_packet",
            "verified": False,
        }
    return {
        "ref": f"REF_{key.upper()}",
        "packet_hash": "0" * 64,
        "verifier": "total_field_manual_release_packet",
        "verified": False,
    }


def _normalize_release_ref(raw_refs: dict, key: str, allow_verified: bool) -> tuple[dict, list[str]]:
    ref = _provided_ref(raw_refs, key)
    warnings = []
    if not is_safe_release_ref(ref["ref"]):
        warnings.append(f"unsafe_or_placeholder_release_ref:{key}")
        ref["verified"] = False
    if not is_safe_packet_hash(ref["packet_hash"]):
        warnings.append(f"missing_or_placeholder_packet_hash:{key}")
        ref["verified"] = False
    if ref["verifier"] not in RELEASE_REF_VERIFIER_ALLOWLIST:
        warnings.append(f"verifier_not_allowlisted:{key}")
        ref["verified"] = False
    if not allow_verified:
        ref["verified"] = False
    return ref, warnings


def _normalize_connector_refs(raw_connector_refs: dict) -> tuple[dict, list[str]]:
    connector_refs = {}
    warnings = []
    for key in REQUIRED_CONNECTOR_REFS:
        value = str((raw_connector_refs or {}).get(key) or "").strip()
        if not value:
            value = {
                "lineworks_bot_ref": "BOT_REF_ONLY_NO_SECRET",
                "lineworks_target_user_ref": "TARGET_REF_ONLY_NO_MEMBER_PLAINTEXT",
                "lineworks_access_token_runtime_ref": "RUNTIME_TOKEN_PROVIDER_REF_ONLY_NO_TOKEN_VALUE",
            }[key]
        connector_refs[key] = value
        if not is_safe_connector_ref(value):
            warnings.append(f"unsafe_or_placeholder_connector_ref:{key}")
    return connector_refs, warnings


def build_lineworks_release_refs_draft(
    release_refs: dict | None = None,
    connector_refs: dict | None = None,
    allow_verified: bool = False,
) -> dict:
    release_refs = release_refs if isinstance(release_refs, dict) else {}
    if isinstance(release_refs.get("lineworks_send"), dict):
        release_refs = release_refs["lineworks_send"]
    connector_refs = connector_refs if isinstance(connector_refs, dict) else {}
    if not connector_refs and isinstance(release_refs.get("connector_refs"), dict):
        connector_refs = release_refs["connector_refs"]

    normalized_release_refs = {}
    warnings = []
    for key in REQUIRED_RELEASE_REFS:
        normalized, ref_warnings = _normalize_release_ref(release_refs, key, allow_verified)
        normalized_release_refs[key] = normalized
        warnings.extend(ref_warnings)

    normalized_connector_refs, connector_warnings = _normalize_connector_refs(connector_refs)
    warnings.extend(connector_warnings)

    all_release_refs_verified = all(ref.get("verified") is True for ref in normalized_release_refs.values())
    connector_refs_ready = not connector_warnings
    state = (
        "RELEASE_REFS_DRAFT_READY_FOR_READINESS_CHECK"
        if all_release_refs_verified and connector_refs_ready
        else "DRAFT_REQUIRES_HUMAN_VERIFICATION"
    )
    draft = {
        "schema": "W7TP_XIAOJ_LINE_WORKS_RELEASE_REFS_TEMPLATE_V1",
        "state": state,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "usage": "Refs only. Do not paste access tokens, private keys, client secrets, raw LINE WORKS user IDs, or member plaintext.",
        "lineworks_send": normalized_release_refs,
        "connector_refs": normalized_connector_refs,
        "draft_warnings": warnings,
        "allow_verified_input": allow_verified,
        "draft_hash": stable_hash(
            {
                "lineworks_send": normalized_release_refs,
                "connector_refs": normalized_connector_refs,
                "warnings": warnings,
            }
        ),
        "p1_side_effects": {
            "external_api_call": False,
            "formal_lineworks_send": False,
            "secret_read": False,
            "member_plaintext_read": False,
            "deploy": False,
            "service_restart": False,
            "db_write": False,
        },
    }
    return draft
