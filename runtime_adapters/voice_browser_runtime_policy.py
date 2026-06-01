#!/usr/bin/env python3
"""Local-only Voice / Browser Runtime policy for Taiji Hub.

The runtime treats voice as an intent input layer and browser operation as a
minimum-privilege action interface. It never turns raw language, audio, or a
browser session into production authority. Unsafe or incomplete packets fail
closed and are routed to deadbox.
"""

from __future__ import annotations

from typing import Any


L3_ACTIONS = {
    "payment_execute",
    "refund",
    "discount_override",
    "manager_override",
    "credential_input",
    "credential_issue",
    "credential_read",
    "secret_read",
    "admin_setting_change",
    "database_direct_write",
    "production_overwrite",
    "browser_submit_production",
    "cloud_plaintext_transfer",
    "raw_audio_cloud_transfer",
    "raw_audio_store",
}

L2_ACTIONS = {
    "pos_order_confirm",
    "service_dispatch_confirm",
    "voice_confirm_draft",
    "browser_submit_local_draft",
    "health_visit_prompt",
    "elder_child_service_prompt",
}

L1_ACTIONS = {
    "voice_transcribe_intent",
    "voice_to_intent_draft",
    "pos_order_create_draft",
    "pos_order_modify_draft",
    "service_request_draft",
    "browser_fill_draft",
    "browser_click_non_destructive",
    "browser_select_option",
    "browser_open_local_dashboard",
    "display_update",
}

L0_ACTIONS = {
    "menu_query",
    "voice_prompt_playback",
    "voice_health_check",
    "browser_read_visible_text",
    "browser_scroll",
    "browser_focus_field",
}

BLOCKED_SENSITIVITY = {
    "customer_personal_data",
    "member_plaintext",
    "payment_sensitive_data",
    "secret_or_token",
    "credential_material",
    "session_cookie",
}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _root(packet: dict[str, Any]) -> dict[str, Any]:
    if isinstance(packet.get("TensorPacket"), dict):
        return packet["TensorPacket"]
    return packet


def _field(root: dict[str, Any], tau: dict[str, Any], name: str, default: Any = None) -> Any:
    intent = _dict(tau.get("I"))
    authority = _dict(tau.get("A"))
    topology = _dict(tau.get("P"))
    payload = _dict(root.get("pi"))
    audit = _dict(root.get("alpha"))
    gamma = _dict(root.get("gamma"))

    sources = (root, payload, intent, authority, topology, audit, gamma)
    for source in sources:
        if name in source:
            return source[name]
    return default


def evaluate_voice_browser_action(packet: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a voice/browser packet without executing any action."""

    if not isinstance(packet, dict):
        return _block("packet_not_object", ["packet_not_object"])

    root = _root(packet)
    tau = _dict(root.get("tau"))
    errors: list[str] = []
    warnings: list[str] = []

    action_type = _text(_field(root, tau, "action_type") or _field(root, tau, "type"))
    modality = _text(_field(root, tau, "modality"))
    target_system = _text(_field(root, tau, "target_system") or _field(root, tau, "target_runtime"))
    node_identity = _text(_field(root, tau, "node_identity") or _field(root, tau, "source_node"))
    data_sensitivity = _text(_field(root, tau, "data_sensitivity", "non_sensitive_metadata"))
    permission_window = _text(_field(root, tau, "permission_window", "runtime"))

    if not action_type:
        errors.append("missing_action_type")
    if modality not in {"voice", "browser", "kiosk_ui", "staff_ui", "system"}:
        errors.append("invalid_or_missing_modality")
    if not target_system:
        errors.append("missing_target_system")
    if not node_identity:
        warnings.append("missing_node_identity")

    if data_sensitivity in BLOCKED_SENSITIVITY:
        errors.append(f"blocked_data_sensitivity:{data_sensitivity}")
    if _field(root, tau, "secret_material_included") is True:
        errors.append("secret_material_included_forbidden")
    if _field(root, tau, "member_plaintext_included") is True:
        errors.append("member_plaintext_included_forbidden")
    if _field(root, tau, "raw_plaintext_context_stored") is True:
        errors.append("raw_plaintext_context_stored_forbidden")
    if _field(root, tau, "admin_session") is True:
        errors.append("admin_browser_session_forbidden")
    if _field(root, tau, "production_mutation") is True:
        errors.append("production_mutation_forbidden")
    if _field(root, tau, "external_api_requested") is True:
        errors.append("external_api_requested_forbidden")
    if _field(root, tau, "payment_allowed") is True:
        errors.append("payment_allowed_forbidden")
    if _field(root, tau, "replay_safe", True) is False:
        return {
            "allowed": False,
            "risk_level": "L3",
            "action": "deadbox",
            "route": "deadbox",
            "requires_human_confirmation": True,
            "audit_required": True,
            "rollback_required": False,
            "reason": "replay unsafe packet routed to deadbox",
            "errors": ["replay_safe_false"],
            "warnings": warnings,
        }

    if action_type in L3_ACTIONS:
        errors.append(f"blocked_action:{action_type}")

    if errors:
        return _block("unsafe voice/browser runtime request", errors, warnings)

    if action_type in L2_ACTIONS:
        return {
            "allowed": False,
            "risk_level": "L2",
            "action": "warn",
            "route": "human_confirmation_queue",
            "requires_human_confirmation": True,
            "audit_required": True,
            "rollback_required": True,
            "reason": "human confirmation required before any controlled execution",
            "errors": [],
            "warnings": warnings,
            "permission_window": permission_window,
        }

    if action_type in L1_ACTIONS:
        return {
            "allowed": True,
            "risk_level": "L1",
            "action": "allow_with_audit",
            "route": "intent_gateway",
            "requires_human_confirmation": action_type.startswith("pos_order_"),
            "audit_required": True,
            "rollback_required": action_type.startswith("pos_order_"),
            "reason": "draft or non-destructive action allowed through gateway",
            "errors": [],
            "warnings": warnings,
            "permission_window": permission_window,
        }

    if action_type in L0_ACTIONS:
        return {
            "allowed": True,
            "risk_level": "L0",
            "action": "allow",
            "route": "local_runtime",
            "requires_human_confirmation": False,
            "audit_required": False,
            "rollback_required": False,
            "reason": "read-only or local prompt action",
            "errors": [],
            "warnings": warnings,
            "permission_window": permission_window,
        }

    return {
        "allowed": False,
        "risk_level": "L2",
        "action": "warn",
        "route": "policy_review_queue",
        "requires_human_confirmation": True,
        "audit_required": True,
        "rollback_required": False,
        "reason": f"uncatalogued action requires policy review: {action_type}",
        "errors": [],
        "warnings": warnings + [f"uncatalogued_action:{action_type}"],
        "permission_window": permission_window,
    }


def _block(reason: str, errors: list[str], warnings: list[str] | None = None) -> dict[str, Any]:
    return {
        "allowed": False,
        "risk_level": "L3",
        "action": "block",
        "route": "deadbox",
        "requires_human_confirmation": True,
        "audit_required": True,
        "rollback_required": False,
        "reason": reason,
        "errors": errors,
        "warnings": warnings or [],
    }


def policy_health() -> dict[str, Any]:
    return {
        "voice_browser_runtime": "ok",
        "mode": "local_policy_only",
        "voice_is_intent_input": True,
        "browser_is_minimum_privilege_interface": True,
        "raw_plaintext_context_allowed": False,
        "payment_execute_allowed": False,
        "admin_browser_session_allowed": False,
        "secret_material_allowed": False,
    }
