#!/usr/bin/env python3
"""W7TP XiaoJ 8D packet verifier.

Standard-library-only verifier for redacted 8D packets. It checks required
D1-D8 dimensions, plaintext/key leakage markers, key/api reference discipline,
browser action allowlists, and D8 replay envelope shape.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

REQUIRED_DIMENSIONS = [
    "D1_identity",
    "D2_intent",
    "D3_state",
    "D4_topology",
    "D5_resource",
    "D6_governance",
    "D7_verification",
    "D8_envelope",
]

REQUIRED_FIELDS = {
    "D1_identity": ["actor_ref", "actor_type", "device_ref", "role", "plaintext_identity_forbidden"],
    "D2_intent": ["primary_intent", "secondary_intent", "transaction_intent", "risk_level"],
    "D3_state": ["session_state", "task_state", "browser_state", "order_state", "context_mode"],
    "D4_topology": ["channel", "site_ref", "device_topology", "origin_scope"],
    "D5_resource": ["key_policy", "selected_key_ref", "api_refs", "model_tier", "cache_policy", "cost_policy"],
    "D6_governance": ["allowed_actions", "forbidden_actions", "no_plaintext_context", "human_confirm_required", "staff_confirm_required"],
    "D7_verification": ["redaction_check_required", "leak_check_required", "action_allowlist_required", "response_verify_required", "usage_log_required"],
    "D8_envelope": ["packet_ref", "nonce", "counter", "ttl_seconds", "created_at", "schema_version", "content_hash", "hmac_ref", "signature_ref", "replay_protection"],
}

SAFE_BROWSER_ACTIONS = {
    "navigate_ref",
    "click_ref",
    "fill_ref",
    "select_ref",
    "read_text_ref",
    "screenshot_ref",
    "wait_ref",
    "extract_ref",
    "open_sidebar_ref",
    "close_sidebar_ref",
    "render_sidebar_ref",
    "read_context_ref",
    "write_draft_ref",
    "route_to_connector_ref",
    "broker_api_call_ref",
    "cache_lookup_ref",
    "read_menu_ref",
    "create_order_draft_ref",
    "queue_service_ref",
    "notify_staff_ref",
    "ask_human_confirm",
    "handoff_to_human",
}

BLOCKED_ACTION_NAMES = {
    "login_with_plaintext",
    "submit_payment",
    "submit_order_without_human",
    "read_raw_cookie",
    "read_raw_local_storage",
    "write_database",
    "router_change",
    "tailscale_change",
    "dns_change",
    "service_restart",
    "docker_restart",
    "systemctl_restart",
}

FORBIDDEN_VALUE_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    ("openai_raw_key", re.compile(r"sk-[A-Za-z0-9_-]{10,}")),
    ("google_api_raw_key", re.compile(r"AIza[A-Za-z0-9_-]{10,}")),
    ("bearer_token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{10,}")),
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----|BEGIN PRIVATE KEY")),
    ("password_assignment", re.compile(r"(?i)\b(pass(word)?|pwd)\s*[:=]")),
    ("cookie_assignment", re.compile(r"(?i)\bcookie\s*[:=]")),
    ("local_storage_access", re.compile(r"(?i)\blocalStorage\s*(\[|\.|:|=)")),
    ("tw_identity_label", re.compile(r"身分證|身份證")),
    ("phone_label", re.compile(r"電話")),
    ("address_label", re.compile(r"地址")),
    ("birthday_label", re.compile(r"生日")),
    ("email_label", re.compile(r"電子信箱")),
]

DANGEROUS_KEY_NAMES = {
    "password",
    "passwd",
    "pwd",
    "cookie",
    "cookies",
    "localstorage",
    "local_storage",
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "private_key",
    "api_key",
    "raw_api_key",
    "secret_key",
    "client_secret",
    "身分證",
    "身份證",
    "電話",
    "地址",
    "生日",
    "電子信箱",
}

REF_PREFIXES = (
    "actor_ref:",
    "device_ref:",
    "site_ref:",
    "key_ref:",
    "api_ref:",
    "packet_ref:",
    "hmac_ref:",
    "signature_ref:",
    "action_ref:",
    "response_ref:",
    "token_ref:",
    "secret_ref:",
    "redacted_ref:",
)


def load_packet(path: str | Path) -> Dict[str, Any]:
    """Load a JSON packet from disk."""
    with Path(path).open("r", encoding="utf-8") as handle:
        packet = json.load(handle)
    if not isinstance(packet, dict):
        raise ValueError("packet root must be a JSON object")
    return packet


def validate_required_dimensions(packet: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for dimension in REQUIRED_DIMENSIONS:
        value = packet.get(dimension)
        if not isinstance(value, dict):
            errors.append(f"missing_or_invalid_dimension:{dimension}")
            continue
        for field in REQUIRED_FIELDS[dimension]:
            if field not in value:
                errors.append(f"missing_field:{dimension}.{field}")
    if packet.get("D1_identity", {}).get("plaintext_identity_forbidden") is not True:
        errors.append("D1_identity.plaintext_identity_forbidden_must_be_true")
    if packet.get("D6_governance", {}).get("no_plaintext_context") is not True:
        errors.append("D6_governance.no_plaintext_context_must_be_true")
    for field in REQUIRED_FIELDS["D7_verification"]:
        if packet.get("D7_verification", {}).get(field) is not True:
            errors.append(f"D7_verification.{field}_must_be_true")
    return errors


def _walk_values(value: Any, path: str = "$", key: str | None = None) -> Iterable[Tuple[str, str | None, Any]]:
    yield path, key, value
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            yield from _walk_values(child_value, f"{path}.{child_key}", str(child_key))
    elif isinstance(value, list):
        for index, child_value in enumerate(value):
            yield from _walk_values(child_value, f"{path}[{index}]", None)


def _normal_key(key: str) -> str:
    return key.strip().replace("-", "_").lower()


def _is_dangerous_key(key: str) -> bool:
    normalized = _normal_key(key)
    if normalized in DANGEROUS_KEY_NAMES:
        return True
    if normalized.endswith("_password") or normalized.endswith("_private_key"):
        return True
    if normalized in {"secret", "raw_secret"} or normalized.endswith("_client_secret"):
        return True
    return False


def _value_is_empty_or_reference(value: Any) -> bool:
    if value in (None, "", [], {}):
        return True
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"redacted", "masked", "not_stored", "not_present", "none", "false"}:
            return True
        return value.startswith(REF_PREFIXES)
    return False


def scan_for_forbidden_plaintext(packet: Dict[str, Any]) -> List[str]:
    """Scan values and selected sensitive keys for raw keys or plaintext PII."""
    errors: List[str] = []
    for path, key, value in _walk_values(packet):
        if key is not None and _is_dangerous_key(key) and not _value_is_empty_or_reference(value):
            errors.append(f"dangerous_key_has_plain_value:{path}")
        if isinstance(value, str):
            for label, pattern in FORBIDDEN_VALUE_PATTERNS:
                if pattern.search(value):
                    errors.append(f"forbidden_value:{label}:{path}")
    return errors


def validate_key_api_refs(packet: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    resource = packet.get("D5_resource", {})
    selected_key_ref = resource.get("selected_key_ref")
    if not isinstance(selected_key_ref, str) or not selected_key_ref.startswith("key_ref:"):
        errors.append("D5_resource.selected_key_ref_must_start_with_key_ref")
    api_refs = resource.get("api_refs")
    if not isinstance(api_refs, list) or not api_refs:
        errors.append("D5_resource.api_refs_must_be_nonempty_list")
    else:
        for index, api_ref in enumerate(api_refs):
            if not isinstance(api_ref, str) or not api_ref.startswith("api_ref:"):
                errors.append(f"D5_resource.api_refs[{index}]_must_start_with_api_ref")
    key_policy = resource.get("key_policy")
    if key_policy not in {"broker_managed", "hybrid_ref_only", "no_raw_key", "offline_none"}:
        errors.append("D5_resource.key_policy_invalid")
    return errors


def validate_browser_actions(packet: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    governance = packet.get("D6_governance", {})
    allowed_actions = governance.get("allowed_actions", [])
    forbidden_actions = governance.get("forbidden_actions", [])
    if not isinstance(allowed_actions, list):
        return ["D6_governance.allowed_actions_must_be_list"]
    allowed_set = set(allowed_actions)
    unknown = sorted(action for action in allowed_set if action not in SAFE_BROWSER_ACTIONS)
    if unknown:
        errors.append("unknown_allowed_actions:" + ",".join(unknown))
    if isinstance(forbidden_actions, list):
        overlap = sorted(allowed_set.intersection(forbidden_actions))
        if overlap:
            errors.append("allowed_forbidden_action_overlap:" + ",".join(overlap))
    browser_action = packet.get("browser_action")
    if browser_action is not None:
        if not isinstance(browser_action, dict):
            errors.append("browser_action_must_be_object")
        else:
            action_type = browser_action.get("action_type")
            if action_type not in SAFE_BROWSER_ACTIONS:
                errors.append("browser_action.action_type_not_allowlisted")
            if action_type not in allowed_set:
                errors.append("browser_action.action_type_not_declared_in_D6_allowed_actions")
            if browser_action.get("dry_run") is not True:
                errors.append("browser_action.dry_run_must_be_true")
            if browser_action.get("submit_forbidden") is not True:
                errors.append("browser_action.submit_forbidden_must_be_true")
    blocked_declared = sorted(set(forbidden_actions).intersection(BLOCKED_ACTION_NAMES)) if isinstance(forbidden_actions, list) else []
    if not blocked_declared:
        errors.append("D6_governance.forbidden_actions_should_include_at_least_one_known_blocked_action")
    return errors


def validate_envelope(packet: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    envelope = packet.get("D8_envelope", {})
    if not isinstance(envelope, dict):
        return ["D8_envelope_must_be_object"]
    if not isinstance(envelope.get("packet_ref"), str) or not envelope["packet_ref"].startswith("packet_ref:"):
        errors.append("D8_envelope.packet_ref_invalid")
    if not isinstance(envelope.get("nonce"), str) or len(envelope["nonce"]) < 16:
        errors.append("D8_envelope.nonce_too_short")
    if not isinstance(envelope.get("counter"), int) or envelope["counter"] < 0:
        errors.append("D8_envelope.counter_invalid")
    ttl = envelope.get("ttl_seconds")
    if not isinstance(ttl, int) or ttl <= 0 or ttl > 86400:
        errors.append("D8_envelope.ttl_seconds_invalid")
    created_at = envelope.get("created_at")
    if not isinstance(created_at, str):
        errors.append("D8_envelope.created_at_missing")
    else:
        try:
            _dt.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError:
            errors.append("D8_envelope.created_at_not_iso8601")
    if envelope.get("schema_version") != "8d.packet.v1":
        errors.append("D8_envelope.schema_version_invalid")
    content_hash = envelope.get("content_hash")
    if not isinstance(content_hash, str) or not re.fullmatch(r"[a-f0-9]{64}", content_hash):
        errors.append("D8_envelope.content_hash_invalid")
    if not isinstance(envelope.get("hmac_ref"), str) or not envelope["hmac_ref"].startswith("hmac_ref:"):
        errors.append("D8_envelope.hmac_ref_invalid")
    if not isinstance(envelope.get("signature_ref"), str) or not envelope["signature_ref"].startswith("signature_ref:"):
        errors.append("D8_envelope.signature_ref_invalid")
    if envelope.get("replay_protection") is not True:
        errors.append("D8_envelope.replay_protection_must_be_true")
    return errors


def verify_packet_file(path: str | Path) -> Dict[str, Any]:
    packet = load_packet(path)
    checks = {
        "required_dimensions": validate_required_dimensions(packet),
        "forbidden_plaintext": scan_for_forbidden_plaintext(packet),
        "key_api_refs": validate_key_api_refs(packet),
        "browser_actions": validate_browser_actions(packet),
        "envelope": validate_envelope(packet),
    }
    errors = [error for check_errors in checks.values() for error in check_errors]
    return {
        "file": str(path),
        "ok": not errors,
        "errors": errors,
        "checks": checks,
    }


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify W7TP XiaoJ 8D packet JSON files.")
    parser.add_argument("paths", nargs="+", help="Packet JSON file path(s) to verify")
    args = parser.parse_args(argv)
    results = [verify_packet_file(path) for path in args.paths]
    payload: Any = results[0] if len(results) == 1 else results
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if all(result["ok"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
