"""LINE WORKS connector contract helpers.

P1 helpers perform no HTTP requests and read no secrets. The P2 runtime helper
defaults to dry-run and can perform an HTTP request only when an explicit
activation packet, runtime resolver, and enable flag are supplied.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any


LINEWORKS_SEND_ENDPOINT_TEMPLATE = "https://www.worksapis.com/v1.0/bots/{botId}/users/{userId}/messages"
LINEWORKS_REQUIRED_SCOPES = ["bot", "bot.message"]
REQUIRED_CONNECTOR_REFS = [
    "lineworks_bot_ref",
    "lineworks_target_user_ref",
    "lineworks_access_token_runtime_ref",
]
RUNTIME_RESOLVER_KEYS = [
    "lineworks_bot_ref",
    "lineworks_target_user_ref",
    "lineworks_access_token_runtime_ref",
]
SAFE_CONNECTOR_REF_PATTERN = re.compile(r"[A-Z0-9_:-]{6,128}")
JWT_SHAPE_PATTERN = re.compile(r"[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}")
LONG_TOKEN_SHAPE_PATTERN = re.compile(r"(?=.*[A-Za-z])(?=.*[0-9])[A-Za-z0-9_~+/=-]{40,}")


def _stable_hash(data: Any) -> str:
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _hex64(value: Any) -> bool:
    return bool(re.fullmatch(r"[a-f0-9]{64}", str(value or "").strip().lower()))


def _has_secret_shape(value: Any) -> bool:
    text = str(value or "")
    return bool(
        re.search(r"sk-[A-Za-z0-9_-]{12,}", text)
        or re.search(r"(?i)(access|refresh|id)_token\s*[:=]\s*\S+", text)
        or re.search(r"(?i)(^|[^A-Z0-9])ACCESS_TOKEN_REF($|[^A-Z0-9])", text)
        or re.search(r"(?i)client_secret\s*[:=]\s*\S+", text)
        or re.search(r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----", text)
        or re.search(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}", text)
        or JWT_SHAPE_PATTERN.search(text)
        or LONG_TOKEN_SHAPE_PATTERN.search(text)
    )


def is_safe_connector_ref(value: Any) -> bool:
    """Return True only for uppercase opaque refs, never raw ids or tokens."""

    text = str(value or "").strip()
    return (
        text == str(value or "")
        and "REF" in text
        and SAFE_CONNECTOR_REF_PATTERN.fullmatch(text) is not None
        and not _has_secret_shape(text)
    )


def _is_safe_operator_ref(value: Any) -> bool:
    return _hex64(value) or is_safe_connector_ref(value)


def _safe_text(value: Any, limit: int = 280) -> str:
    text = " ".join(str(value or "").split())
    text = re.sub(r"sk-[A-Za-z0-9_-]{12,}", "[REDACTED_KEY]", text)
    text = re.sub(r"(?i)(access|refresh|id)_token\s*[:=]\s*\S+", "[REDACTED_TOKEN]", text)
    text = re.sub(r"(?i)client_secret\s*[:=]\s*\S+", "[REDACTED_SECRET]", text)
    text = re.sub(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}", "[REDACTED_BEARER]", text)
    text = JWT_SHAPE_PATTERN.sub("[REDACTED_JWT]", text)
    text = LONG_TOKEN_SHAPE_PATTERN.sub("[REDACTED_TOKEN_REF]", text)
    return text[:limit]


def _release_gate_ready(release_status_payload: dict) -> bool:
    gates = release_status_payload.get("formal_release_gates") if isinstance(release_status_payload, dict) else {}
    lineworks_gate = gates.get("lineworks_send") if isinstance(gates, dict) else {}
    return lineworks_gate.get("decision") == "RELEASE_READY_FOR_HUMAN_ACTIVATION" and lineworks_gate.get("release_ready") is True


def _lineworks_candidate(candidate_payload: dict) -> dict:
    candidate = candidate_payload.get("lineworks_notify_candidate") if isinstance(candidate_payload, dict) else {}
    return candidate if isinstance(candidate, dict) else {}


def _activation_failure_reasons(runtime_activation: dict | None) -> list[str]:
    activation = runtime_activation if isinstance(runtime_activation, dict) else {}
    reasons = []
    if activation.get("human_activation") is not True:
        reasons.append("human_activation_required")
    if activation.get("release_gate") not in {"lineworks_send", None, ""}:
        reasons.append("lineworks_release_gate_required")
    if not _hex64(activation.get("activation_packet_hash")):
        reasons.append("activation_packet_hash_64hex_required")
    if not _is_safe_operator_ref(activation.get("operator_ref")):
        reasons.append("operator_ref_hash_or_opaque_ref_required")
    return reasons


def _validate_runtime_values(values: dict) -> list[str]:
    reasons = []
    bot_id = str(values.get("lineworks_bot_ref") or "").strip()
    user_id = str(values.get("lineworks_target_user_ref") or "").strip()
    lineworks_token_ref = str(values.get("lineworks_access_token_runtime_ref") or "").strip()
    if not bot_id or not re.fullmatch(r"\d{1,19}", bot_id):
        reasons.append("runtime_bot_id_required")
    if not user_id or len(user_id) > 256 or _has_secret_shape(user_id):
        reasons.append("runtime_target_user_id_required")
    if not lineworks_token_ref:
        reasons.append("runtime_access_token_required")
    return reasons


def _resolve_runtime_values(runtime_resolver) -> tuple[dict, list[str]]:
    if not callable(runtime_resolver):
        return {}, ["runtime_resolver_required"]
    values = {}
    missing = []
    for key in RUNTIME_RESOLVER_KEYS:
        value = runtime_resolver(key)
        if not value:
            missing.append(key)
        values[key] = value
    reasons = [f"runtime_value_missing:{key}" for key in missing]
    reasons.extend(_validate_runtime_values(values))
    return values, reasons


def _default_http_post(url: str, headers: dict, body: dict, timeout: int) -> dict:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_body = response.read()
            return {
                "status_code": int(response.status),
                "response_body_hash": hashlib.sha256(response_body).hexdigest(),
            }
    except urllib.error.HTTPError as exc:
        response_body = exc.read()
        return {
            "status_code": int(exc.code),
            "response_body_hash": hashlib.sha256(response_body).hexdigest(),
        }


def _runtime_base_failure_reasons(envelope_export: dict, envelope: dict) -> list[str]:
    reasons = []
    if envelope_export.get("schema") != "W7TP_XIAOJ_LINEWORKS_EXECUTION_ENVELOPE_EXPORT_V1":
        reasons.append("execution_envelope_export_schema_required")
    if envelope_export.get("state") != "PASS_LINEWORKS_EXECUTION_ENVELOPE_READY":
        reasons.append("execution_envelope_not_ready")
    if envelope_export.get("preflight_send_allowed") is not True:
        reasons.append("preflight_send_allowed_required")
    if envelope.get("method") != "POST":
        reasons.append("post_method_required")
    if envelope.get("endpoint_template") != LINEWORKS_SEND_ENDPOINT_TEMPLATE:
        reasons.append("lineworks_endpoint_template_required")
    if envelope.get("body_hash") != _stable_hash(envelope.get("body_preview") or {}):
        reasons.append("body_hash_mismatch")
    if envelope_export.get("handoff_policy", {}).get("client_supplied_release_status_trusted") is not False:
        reasons.append("client_supplied_release_status_must_not_be_trusted")
    return reasons


def build_lineworks_send_preflight(
    candidate_payload: dict,
    release_status_payload: dict,
    connector_refs: dict | None = None,
) -> dict:
    """Return a redacted, non-executing LINE WORKS request envelope."""

    connector_refs = connector_refs if isinstance(connector_refs, dict) else {}
    candidate = _lineworks_candidate(candidate_payload)
    message_preview = _safe_text(candidate.get("message_preview") or "")
    target_ref_hash = str(candidate.get("target_ref_hash") or "")
    missing_refs = [ref for ref in REQUIRED_CONNECTOR_REFS if not connector_refs.get(ref)]
    unsafe_ref_keys = [key for key, value in connector_refs.items() if _has_secret_shape(value)]
    unsafe_shape_ref_keys = [
        key
        for key, value in connector_refs.items()
        if key in REQUIRED_CONNECTOR_REFS and value and not is_safe_connector_ref(value)
    ]
    release_ready = _release_gate_ready(release_status_payload)
    reasons = []
    if candidate_payload.get("intent") != "lineworks_notify_candidate":
        reasons.append("lineworks_candidate_payload_required")
    if not message_preview:
        reasons.append("message_preview_required")
    if not target_ref_hash:
        reasons.append("target_ref_hash_required")
    if missing_refs:
        reasons.append("connector_refs_missing")
    if unsafe_ref_keys:
        reasons.append("connector_refs_must_not_contain_secret_material")
    if unsafe_shape_ref_keys:
        reasons.append("connector_refs_must_be_opaque_uppercase_refs")
    if not release_ready:
        reasons.append("lineworks_send_release_gate_not_ready")

    body = {
        "content": {
            "type": "text",
            "text": message_preview,
        }
    }
    seed = {
        "endpoint_template": LINEWORKS_SEND_ENDPOINT_TEMPLATE,
        "required_scopes": LINEWORKS_REQUIRED_SCOPES,
        "body": body,
        "target_ref_hash": target_ref_hash,
        "connector_ref_keys": sorted(connector_refs),
    }
    state = "LINEWORKS_SEND_PREFLIGHT_READY" if not reasons else "HOLD_LINEWORKS_SEND_PREFLIGHT"
    return {
        "schema": "W7TP_LINE_WORKS_SEND_PREFLIGHT_V1",
        "state": state,
        "send_allowed": not reasons,
        "external_api_call": False,
        "formal_lineworks_send": False,
        "release_gate_ready": release_ready,
        "failure_reasons": reasons,
        "missing_connector_refs": missing_refs,
        "unsafe_connector_ref_keys": unsafe_ref_keys,
        "unsafe_connector_ref_shape_keys": unsafe_shape_ref_keys,
        "method": "POST",
        "endpoint_template": LINEWORKS_SEND_ENDPOINT_TEMPLATE,
        "headers": {
            "Authorization": "BEARER_REF_TEST",
            "Content-Type": "application/json",
        },
        "body_preview": body,
        "body_hash": _stable_hash(body),
        "target_ref_hash": target_ref_hash,
        "connector_ref_keys": sorted(connector_refs),
        "required_scopes": LINEWORKS_REQUIRED_SCOPES,
        "request_envelope_hash": _stable_hash(seed),
        "redaction": {
            "bot_id_echo": False,
            "target_user_id_echo": False,
            "access_token_echo": False,
            "client_secret_echo": False,
            "private_key_echo": False,
            "member_plaintext_echo": False,
        },
    }


def build_lineworks_execution_envelope_export(
    candidate_payload: dict,
    release_status_payload: dict,
    connector_refs: dict | None = None,
    refs_path: str = "",
) -> dict:
    """Return the redacted runtime handoff envelope for a verified preflight."""

    preflight = build_lineworks_send_preflight(candidate_payload, release_status_payload, connector_refs)
    gates = release_status_payload.get("formal_release_gates") if isinstance(release_status_payload, dict) else {}
    lineworks_gate = gates.get("lineworks_send") if isinstance(gates, dict) else {}
    send_allowed = preflight.get("send_allowed") is True
    state = "PASS_LINEWORKS_EXECUTION_ENVELOPE_READY" if send_allowed else "HOLD_LINEWORKS_EXECUTION_ENVELOPE"
    return {
        "schema": "W7TP_XIAOJ_LINEWORKS_EXECUTION_ENVELOPE_EXPORT_V1",
        "state": state,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "refs_path": str(refs_path or ""),
        "intent": "lineworks_notify_candidate",
        "release_gate": "lineworks_send",
        "release_gate_decision": lineworks_gate.get("decision", ""),
        "release_ready": lineworks_gate.get("release_ready") is True,
        "preflight_state": preflight.get("state", ""),
        "preflight_send_allowed": send_allowed,
        "runtime_send_enabled": False,
        "side_effects": {
            "external_api_call": False,
            "formal_lineworks_send": False,
            "secret_read": False,
            "member_plaintext_read": False,
            "db_write": False,
            "deploy": False,
            "service_restart": False,
        },
        "candidate_packet_hash": candidate_payload.get("authority_packet", {}).get("packet_hash", ""),
        "preflight_envelope_hash": preflight.get("request_envelope_hash", ""),
        "execution_envelope": {
            "method": preflight.get("method", ""),
            "endpoint_template": preflight.get("endpoint_template", ""),
            "headers": preflight.get("headers", {}),
            "body_preview": preflight.get("body_preview", {}),
            "body_hash": preflight.get("body_hash", ""),
            "target_ref_hash": preflight.get("target_ref_hash", ""),
            "connector_ref_keys": preflight.get("connector_ref_keys", []),
            "required_scopes": preflight.get("required_scopes", []),
            "request_envelope_hash": preflight.get("request_envelope_hash", ""),
            "failure_reasons": preflight.get("failure_reasons", []),
        },
        "redaction": preflight.get("redaction", {}),
        "handoff_policy": {
            "cloud_authority": False,
            "local_authority_required": True,
            "client_supplied_release_status_trusted": False,
            "credential_values_in_export": False,
            "raw_member_identity_in_export": False,
            "operator_action": (
                "HAND_TO_P2_RUNTIME_CONNECTOR_AFTER_HUMAN_ACTIVATION"
                if send_allowed
                else "COMPLETE_VERIFIED_RELEASE_REFS_AND_CONNECTOR_REFS"
            ),
        },
    }


def execute_lineworks_send_envelope(
    envelope_export: dict,
    runtime_activation: dict | None = None,
    runtime_resolver=None,
    http_post=None,
    enable_external_call: bool = False,
    timeout: int = 10,
) -> dict:
    """Execute a ready envelope only when explicitly activated.

    The default path is a dry run. It does not call LINE WORKS and does not
    resolve runtime credential values. A production caller must pass
    enable_external_call=True, a verified activation packet, and a resolver that
    returns bot ID, target user ID, and access token in memory.
    """

    envelope_export = envelope_export if isinstance(envelope_export, dict) else {}
    envelope = envelope_export.get("execution_envelope") if isinstance(envelope_export.get("execution_envelope"), dict) else {}
    base_reasons = _runtime_base_failure_reasons(envelope_export, envelope)
    activation_reasons = _activation_failure_reasons(runtime_activation)
    dry_run_ready = not base_reasons and not activation_reasons
    if not enable_external_call:
        return {
            "schema": "W7TP_LINE_WORKS_RUNTIME_SEND_RESULT_V1",
            "state": "LINEWORKS_RUNTIME_DRY_RUN_READY" if dry_run_ready else "HOLD_LINEWORKS_RUNTIME_SEND",
            "dry_run_ready": dry_run_ready,
            "send_executed": False,
            "external_api_call": False,
            "formal_lineworks_send": False,
            "secret_read": False,
            "member_plaintext_read": False,
            "failure_reasons": base_reasons + activation_reasons + ["runtime_external_call_disabled"],
            "endpoint_template": envelope.get("endpoint_template", ""),
            "request_envelope_hash": envelope.get("request_envelope_hash", ""),
            "body_hash": envelope.get("body_hash", ""),
            "redaction": {
                "bot_id_echo": False,
                "target_user_id_echo": False,
                "access_token_echo": False,
                "response_body_echo": False,
            },
        }

    values, runtime_reasons = _resolve_runtime_values(runtime_resolver)
    reasons = base_reasons + activation_reasons + runtime_reasons
    if reasons:
        return {
            "schema": "W7TP_LINE_WORKS_RUNTIME_SEND_RESULT_V1",
            "state": "HOLD_LINEWORKS_RUNTIME_SEND",
            "dry_run_ready": False,
            "send_executed": False,
            "external_api_call": False,
            "formal_lineworks_send": False,
            "secret_read": bool(runtime_reasons),
            "member_plaintext_read": False,
            "failure_reasons": reasons,
            "endpoint_template": envelope.get("endpoint_template", ""),
            "request_envelope_hash": envelope.get("request_envelope_hash", ""),
            "body_hash": envelope.get("body_hash", ""),
            "redaction": {
                "bot_id_echo": False,
                "target_user_id_echo": False,
                "access_token_echo": False,
                "response_body_echo": False,
            },
        }

    bot_id = str(values["lineworks_bot_ref"]).strip()
    user_id = str(values["lineworks_target_user_ref"]).strip()
    lineworks_token_ref = str(values["lineworks_access_token_runtime_ref"]).strip()
    url = LINEWORKS_SEND_ENDPOINT_TEMPLATE.replace("{botId}", bot_id).replace("{userId}", user_id)
    headers = {
        "Authorization": f"Bearer {lineworks_token_ref}",
        "Content-Type": "application/json",
    }
    body = envelope.get("body_preview") or {}
    post = http_post or _default_http_post
    response = post(url, headers, body, int(timeout or 10))
    status_code = int(response.get("status_code") or 0)
    accepted = 200 <= status_code < 300
    return {
        "schema": "W7TP_LINE_WORKS_RUNTIME_SEND_RESULT_V1",
        "state": "PASS_LINEWORKS_RUNTIME_SEND_ACCEPTED" if accepted else "HOLD_LINEWORKS_RUNTIME_SEND_REJECTED",
        "dry_run_ready": True,
        "send_executed": accepted,
        "external_api_call": True,
        "formal_lineworks_send": accepted,
        "secret_read": True,
        "member_plaintext_read": False,
        "failure_reasons": [] if accepted else ["lineworks_api_non_2xx_response"],
        "status_code": status_code,
        "response_body_hash": response.get("response_body_hash", ""),
        "endpoint_template": envelope.get("endpoint_template", ""),
        "request_envelope_hash": envelope.get("request_envelope_hash", ""),
        "body_hash": envelope.get("body_hash", ""),
        "runtime_value_hashes": {
            "bot_id_hash": _stable_hash({"bot_id": bot_id}),
            "target_user_id_hash": _stable_hash({"target_user_id": user_id}),
            "access_token_hash": _stable_hash({"lineworks_token_ref": lineworks_token_ref}),
        },
        "redaction": {
            "bot_id_echo": False,
            "target_user_id_echo": False,
            "access_token_echo": False,
            "response_body_echo": False,
        },
    }
