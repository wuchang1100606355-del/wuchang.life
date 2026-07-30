"""LINE Official Account webhook candidate helper.

This helper turns LINE Messaging API webhook payloads into local candidate
packets. It performs no signature secret reads, no DB writes, no external API
calls, and no LINE replies.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SAFE_REF_PATTERN = re.compile(r"[A-Z0-9_:-]{6,180}")
HEX64_PATTERN = re.compile(r"[a-f0-9]{64}")
JWT_SHAPE_PATTERN = re.compile(r"[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}")
LONG_TOKEN_SHAPE_PATTERN = re.compile(r"(?=.*[A-Za-z])(?=.*[0-9])[A-Za-z0-9_~+/=-]{40,}")


def _ensure_repo_root_on_path() -> None:
    root = Path(__file__).resolve().parents[4]
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def has_secret_or_plaintext_shape(value: Any) -> bool:
    text = str(value or "")
    return bool(
        re.search(r"sk-[A-Za-z0-9_-]{12,}", text)
        or re.search(r"(?i)(access|refresh|id)_token\s*[:=]\s*\S+", text)
        or re.search(r"(?i)\bACCESS_TOKEN_REF[A-Z0-9_:-]*\b", text)
        or re.search(r"(?i)channel_secret\s*[:=]\s*\S+", text)
        or re.search(r"(?i)client_secret\s*[:=]\s*\S+", text)
        or re.search(r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----", text)
        or re.search(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}", text)
        or re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
        or re.search(r"09\d{2}[- ]?\d{3}[- ]?\d{3}", text)
        or re.search(r"\b[A-Z][12]\d{8}\b", text)
        or re.search(r"(?i)\bMEMBER_(EMAIL|PHONE|ID)_REF[A-Z0-9_:-]*\b", text)
        or JWT_SHAPE_PATTERN.search(text)
        or LONG_TOKEN_SHAPE_PATTERN.search(text)
    )


def redact_text(text: Any, limit: int = 360) -> tuple[str, list[str]]:
    redacted = " ".join(str(text or "").split())
    flags: list[str] = []
    replacements = [
        (r"sk-[A-Za-z0-9_-]{12,}", "[SECRET_REF]", "secret_shape_redacted"),
        (r"(?i)(access|refresh|id)_token\s*[:=]\s*\S+", "[TOKEN_REF]", "token_shape_redacted"),
        (r"(?i)\bACCESS_TOKEN_REF[A-Z0-9_:-]*\b", "[TOKEN_REF]", "token_shape_redacted"),
        (r"(?i)channel_secret\s*[:=]\s*\S+", "[CHANNEL_SECRET_REF]", "secret_shape_redacted"),
        (r"(?i)client_secret\s*[:=]\s*\S+", "[CLIENT_SECRET_REF]", "secret_shape_redacted"),
        (r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}", "[BEARER_REF]", "token_shape_redacted"),
        (r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[MEMBER_REF]", "member_plaintext_shape_redacted"),
        (r"09\d{2}[- ]?\d{3}[- ]?\d{3}", "[MEMBER_REF]", "member_plaintext_shape_redacted"),
        (r"\b[A-Z][12]\d{8}\b", "[MEMBER_REF]", "member_plaintext_shape_redacted"),
        (r"(?i)\bMEMBER_(EMAIL|PHONE|ID)_REF[A-Z0-9_:-]*\b", "[MEMBER_REF]", "member_plaintext_shape_redacted"),
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


def _signature_verified(verification: dict | None) -> bool:
    verification = verification if isinstance(verification, dict) else {}
    return (
        verification.get("verified") is True
        and is_safe_ref(verification.get("signature_verification_ref"))
        and is_safe_ref(verification.get("channel_secret_ref"))
    )


def _event_candidate(event: dict) -> dict:
    event = event if isinstance(event, dict) else {}
    source = event.get("source") if isinstance(event.get("source"), dict) else {}
    message = event.get("message") if isinstance(event.get("message"), dict) else {}
    message_text, redaction_flags = redact_text(message.get("text") if message.get("type") == "text" else "")
    source_seed = {
        "type": source.get("type", ""),
        "userId": source.get("userId", ""),
        "groupId": source.get("groupId", ""),
        "roomId": source.get("roomId", ""),
    }
    reply_token = str(event.get("replyToken") or "")
    event_ref_input = {
        "timestamp": event.get("timestamp", ""),
        "source": source_seed,
        "event_type": str(event.get("type") or ""),
    }
    event_ref_hash = stable_hash(event_ref_input)
    reply_token_hash = stable_hash({"replyToken": reply_token}) if reply_token else ""
    return {
        "event_ref_hash": event_ref_hash,
        "event_type": str(event.get("type") or ""),
        "timestamp_hash": stable_hash({"timestamp": event.get("timestamp", "")}),
        "source_type": str(source.get("type") or ""),
        "source_ref_hash": stable_hash(source_seed),
        "reply_token_hash": reply_token_hash,
        "reply_token_echo": False,
        "message_type": str(message.get("type") or ""),
        "message_text_candidate": message_text,
        "message_text_redaction_flags": redaction_flags,
        "raw_user_id_echo": False,
        "member_plaintext_echo": False,
    }


def _render_total_field_line_response(candidate: dict) -> tuple[dict, dict]:
    try:
        _ensure_repo_root_on_path()
        from tools.total_field.final_state_gate import run_line_candidate_gate
        from tools.total_field.human_response_renderer import render_human_response
    except Exception as exc:  # pragma: no cover - defensive Odoo runtime fallback
        gate = {
            "state": "TOTAL_FIELD_FINAL_STATE_GATE_RESULT",
            "decision": "HOLD",
            "gate_code": "HOLD_TOTAL_FIELD_GATE_IMPORT",
            "risk_level": "MEDIUM",
            "errors": [f"TOTAL_FIELD_GATE_IMPORT_FAILED:{type(exc).__name__}"],
            "side_effects": {
                "db_write": False,
                "odoo_write": False,
                "deploy": False,
                "restart": False,
                "external_api_call": False,
                "line_reply_sent": False,
            },
        }
        response = {
            "state": "HUMAN_RESPONSE_RENDERED",
            "decision": "HOLD",
            "risk_level": "MEDIUM",
            "channel": "LINE",
            "reply_text": "這個候選需要再確認，我先暫停，不會執行任何正式動作。",
            "requires_confirmation": True,
            "candidate_reply_only": True,
            "formal_send_executed": False,
            "line_reply_sent": False,
        }
        return gate, response

    gate = run_line_candidate_gate(candidate)
    return gate, render_human_response(gate, channel="line")


def build_line_official_account_webhook_candidate(
    webhook_payload: dict | None = None,
    headers: dict | None = None,
    verification: dict | None = None,
) -> dict:
    payload = webhook_payload if isinstance(webhook_payload, dict) else {}
    headers = headers if isinstance(headers, dict) else {}
    events = payload.get("events") if isinstance(payload.get("events"), list) else []
    signature_present = bool(
        headers.get("x-line-signature")
        or headers.get("X-Line-Signature")
        or headers.get("HTTP_X_LINE_SIGNATURE")
    )
    verified = _signature_verified(verification)
    event_candidates = [_event_candidate(event) for event in events[:20]]
    failure_reasons = []
    if not signature_present:
        failure_reasons.append("line_signature_header_required")
    if not verified:
        failure_reasons.append("signature_verification_ref_required")
    if not event_candidates:
        failure_reasons.append("line_webhook_events_required")
    state = "READY_FOR_LOCAL_INTENT_CANDIDATE" if not failure_reasons else "HOLD_LINE_OFFICIAL_ACCOUNT_WEBHOOK_CANDIDATE"
    packet_seed = {
        "destination_hash": stable_hash({"destination": payload.get("destination", "")}),
        "event_candidates": event_candidates,
        "signature_present": signature_present,
        "verified": verified,
        "failure_reasons": failure_reasons,
    }
    packet_hash = stable_hash(packet_seed)
    candidate = {
        "schema": "W7TP_XIAOJ_LINE_OFFICIAL_ACCOUNT_WEBHOOK_CANDIDATE_V1",
        "state": state,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "surface": "LINE_OFFICIAL_ACCOUNT_MESSAGING_API",
        "intent": "line_official_account_webhook_candidate",
        "line_official_account_is_not_lineworks": True,
        "destination_hash": packet_seed["destination_hash"],
        "signature_header_present": signature_present,
        "signature_verified_by_ref": verified,
        "event_count": len(event_candidates),
        "event_candidates": event_candidates,
        "local_verifier": {
            "decision": "READY_FOR_LOCAL_INTENT_CANDIDATE" if state.startswith("READY_") else "HOLD",
            "failure_reasons": failure_reasons,
            "checks": [
                "signature_header_present",
                "signature_verification_ref_present",
                "events_present",
                "no_reply_token_echo",
                "no_raw_user_id_echo",
                "no_member_plaintext_echo",
                "no_line_reply_from_webhook_candidate",
            ],
            "line_reply_allowed": False,
            "human_release_required_for_reply": True,
        },
        "authority_packet": {
            "packet_hash": packet_hash,
            "evidence_hash": stable_hash({"packet_hash": packet_hash, "state": state}),
            "release_required_for_reply": True,
            "line_reply_sent": False,
        },
        "side_effects": {
            "external_api_call": False,
            "formal_line_message_send": False,
            "line_reply_sent": False,
            "official_account_setting_changed": False,
            "secret_read": False,
            "member_plaintext_read": False,
            "db_write": False,
            "deploy": False,
            "service_restart": False,
        },
        "redaction": {
            "reply_token_echo": False,
            "raw_user_id_echo": False,
            "channel_secret_echo": False,
            "channel_access_token_echo": False,
            "member_plaintext_echo": False,
        },
        "verified_channel_binding": {
            "state": "HOLD_NOT_AUTHENTICATED_MEMBER_SESSION",
            "provider": "line",
            "provider_subject_hashes": [
                event["source_ref_hash"] for event in event_candidates
            ],
            "raw_provider_profile": False,
            "root_issued": False,
            "consent_issued": False,
            "role_issued": False,
            "seat_issued": False,
            "permission_issued": False,
            "candidate_only": True,
        },
    }
    gate, response = _render_total_field_line_response(candidate)
    candidate["total_field_gate"] = gate
    candidate["human_response"] = response
    candidate["local_verifier"]["line_reply_allowed"] = False
    candidate["local_verifier"]["human_release_required_for_reply"] = True
    candidate["side_effects"]["formal_line_message_send"] = False
    candidate["side_effects"]["line_reply_sent"] = False
    return candidate
