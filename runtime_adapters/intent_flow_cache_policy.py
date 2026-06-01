#!/usr/bin/env python3
"""Local-only intent flow cache policy for Taiji TensorPacket runtime.

The cache policy accelerates already-governed intent flow reuse. It never
stores raw speech/text, never executes POS/payment actions, and fails closed
when policy state is missing or unsafe packet fields are present.
"""

from __future__ import annotations

import json
import os
import pathlib
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_POLICY_PATH = ROOT / "Taiji_Governance/system_info/active_intent_flow_cache_policy.manifest.json"

ALLOWED_INTENTS = {
    "menu_query",
    "staff_assist",
    "service_request",
    "display_update",
    "pos_order_create",
    "pos_order_modify",
}

BLOCKED_INTENTS = {
    "payment_execute",
    "payment_prepare",
    "refund",
    "discount_override",
    "manager_override",
    "credential_issue",
    "credential_read",
    "secret_read",
    "production_overwrite",
    "database_direct_write",
    "live_deploy",
}

BLOCKED_SENSITIVITY = {
    "customer_personal_data",
    "payment_sensitive_data",
    "secret_or_token",
    "credential_material",
    "member_plaintext",
}


def _policy_path() -> pathlib.Path:
    return pathlib.Path(os.environ.get("TAIJI_INTENT_CACHE_POLICY_PATH", str(DEFAULT_POLICY_PATH)))


def load_policy() -> dict[str, Any]:
    path = _policy_path()
    if not path.exists():
        return {
            "active": False,
            "status": "missing",
            "path": str(path),
            "reason": "intent flow cache policy manifest missing",
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "active": False,
            "status": "invalid",
            "path": str(path),
            "reason": f"intent flow cache policy unreadable: {type(exc).__name__}",
        }
    active = data.get("status") == "ACTIVE" and data.get("policy_active") is True
    return {
        "active": bool(active),
        "status": "active" if active else "inactive",
        "path": str(path),
        "policy_version": data.get("policy_version", "unknown"),
        "cache_scope": data.get("cache_scope", "unknown"),
    }


def cache_health() -> dict[str, Any]:
    policy = load_policy()
    return {
        "intent_flow_cache": "ok" if policy["active"] else "disabled",
        "policy_status": policy["status"],
        "policy_version": policy.get("policy_version", "unknown"),
        "cache_scope": policy.get("cache_scope", "unknown"),
        "raw_plaintext_cache_allowed": False,
        "payment_cache_allowed": False,
        "member_plaintext_cache_allowed": False,
    }


def _root(packet: dict[str, Any]) -> dict[str, Any] | None:
    value = packet.get("TensorPacket") if isinstance(packet, dict) else None
    return value if isinstance(value, dict) else None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def evaluate_intent_flow_cache(packet: dict[str, Any]) -> dict[str, Any]:
    policy = load_policy()
    errors: list[str] = []
    warnings: list[str] = []
    if not policy["active"]:
        return {
            "cache_allowed": False,
            "risk_level": "L2",
            "action": "cache_disabled",
            "reason": policy["reason"] if "reason" in policy else "intent flow cache policy inactive",
            "errors": [],
            "warnings": ["cache_policy_not_active"],
            "audit_required": True,
        }

    root = _root(packet)
    if root is None:
        return {
            "cache_allowed": False,
            "risk_level": "L3",
            "action": "block",
            "reason": "missing TensorPacket root",
            "errors": ["missing_TensorPacket"],
            "warnings": [],
            "audit_required": True,
        }

    tau = _dict(root.get("tau"))
    intent = _dict(tau.get("I"))
    authority = _dict(tau.get("A"))
    gamma = _dict(root.get("gamma"))
    kappa = _dict(root.get("kappa"))
    sigma = _dict(root.get("sigma"))
    pi = _dict(root.get("pi"))
    alpha = _dict(root.get("alpha"))

    intent_type = str(intent.get("type", "unknown"))
    risk_level = str(gamma.get("risk_level") or "L1")
    sensitivity = str(
        intent.get("data_sensitivity")
        or pi.get("data_sensitivity")
        or authority.get("data_sensitivity")
        or "non_sensitive_metadata"
    )

    if intent_type in BLOCKED_INTENTS:
        errors.append(f"blocked_cache_intent:{intent_type}")
    if intent_type not in ALLOWED_INTENTS:
        warnings.append(f"uncatalogued_cache_intent:{intent_type}")
    if risk_level in {"L2", "L3"}:
        errors.append(f"risk_level_not_cacheable:{risk_level}")
    if sensitivity in BLOCKED_SENSITIVITY:
        errors.append(f"blocked_data_sensitivity:{sensitivity}")
    if pi.get("raw_plaintext_stored") is True or alpha.get("plaintext_context_stored") is True:
        errors.append("raw_plaintext_cache_forbidden")
    if pi.get("raw_text") or pi.get("customer_name") or pi.get("phone") or pi.get("member_id"):
        errors.append("identifying_or_raw_text_cache_forbidden")
    if authority.get("payment_allowed") is True or pi.get("payment_allowed") is True:
        errors.append("payment_cache_forbidden")
    if alpha.get("secret_material_printed") is True:
        errors.append("secret_material_cache_forbidden")

    tensor_hash = sigma.get("tensor_hash") or kappa.get("cache_key")
    pattern = sigma.get("pattern") or kappa.get("pattern")
    if not tensor_hash:
        warnings.append("missing_tensor_hash")
    if not pattern:
        warnings.append("missing_cache_pattern")

    if errors:
        return {
            "cache_allowed": False,
            "risk_level": "L3",
            "action": "block",
            "reason": "unsafe intent flow cache request",
            "errors": errors,
            "warnings": warnings,
            "audit_required": True,
        }

    cache_allowed = intent_type in ALLOWED_INTENTS and bool(tensor_hash and pattern)
    return {
        "cache_allowed": cache_allowed,
        "risk_level": "L1" if cache_allowed else "L2",
        "action": "allow_flow_template_cache" if cache_allowed else "warn_no_cache",
        "reason": "cache reusable governed intent flow only" if cache_allowed else "cache key or pattern incomplete",
        "cache_mode": "flow_template_only",
        "allowed_material": [
            "tensor_hash",
            "semantic_hash",
            "pattern",
            "route_vector",
            "option_vector",
            "redacted_summary",
            "draft_template_hash",
        ],
        "blocked_material": [
            "raw_speech",
            "raw_text",
            "customer_plaintext",
            "payment_sensitive_data",
            "secret_or_token",
            "production_mutation_result",
        ],
        "requires_human_confirmation_before_pos_submit": intent_type.startswith("pos_order_"),
        "errors": [],
        "warnings": warnings,
        "audit_required": True,
    }
