#!/usr/bin/env python3
"""Taiji formal tensor runtime v0.1.1 fail-closed adapter.

This adapter is conservative: existing validator failures and negative
validator decisions always route to deadbox.
"""

from __future__ import annotations

import importlib
from typing import Any, Callable


BLOCKED_INTENT_TYPES = {
    "payment_execute",
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


def load_existing_validator() -> Callable[[dict[str, Any]], dict[str, Any]] | None:
    try:
        module = importlib.import_module("services.gateway.policies.formal_tensor_validator")
    except Exception:
        return None
    for name in (
        "validate_formal_tensor_packet",
        "validate_tensor_packet",
        "evaluate_tensor_packet",
        "validate_packet",
        "evaluate",
    ):
        candidate = getattr(module, name, None)
        if callable(candidate):
            return candidate
    return None


def _deadbox(reason: str, errors: list[str] | None = None, warnings: list[str] | None = None) -> dict[str, Any]:
    return {
        "allowed": False,
        "risk_level": "L3" if errors else "L2",
        "action": "block" if errors else "warn",
        "route": "deadbox",
        "reason": reason,
        "errors": errors or [],
        "warnings": warnings or [],
        "audit_required": True,
        "rollback_required": True,
    }


def fail_closed_validate(packet: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    root = packet.get("TensorPacket")
    if not isinstance(root, dict):
        return _deadbox("missing TensorPacket root", ["missing TensorPacket root"])

    tau = root.get("tau")
    if not isinstance(tau, dict):
        errors.append("missing tau")
        tau = {}

    intent = tau.get("I", {}) if isinstance(tau.get("I", {}), dict) else {}
    authority = tau.get("A", {}) if isinstance(tau.get("A", {}), dict) else {}
    replay = root.get("rho", {}) if isinstance(root.get("rho", {}), dict) else {}
    alpha = root.get("alpha", {}) if isinstance(root.get("alpha", {}), dict) else {}
    payload = root.get("pi", {}) if isinstance(root.get("pi", {}), dict) else {}

    intent_type = str(intent.get("type", "unknown"))
    if intent_type in BLOCKED_INTENT_TYPES:
        errors.append(f"blocked intent type: {intent_type}")
    if authority.get("payment_allowed") is True or payload.get("payment_allowed") is True:
        errors.append("payment_allowed=true is blocked")
    if alpha.get("plaintext_context_stored") is True or payload.get("plaintext_context_stored") is True:
        errors.append("plaintext_context_stored=true is blocked")
    if replay.get("replay_safe") is False:
        warnings.append("replay_safe=false routes to deadbox")
    if alpha.get("secret_material_printed") is True:
        errors.append("secret_material_printed=true is blocked")
    if alpha.get("external_api_called") is True:
        errors.append("external_api_called=true is blocked")
    if alpha.get("live_deploy_executed") is True:
        errors.append("live_deploy_executed=true is blocked")

    if errors or warnings:
        return _deadbox("fail-closed rule triggered", errors, warnings)
    return {
        "allowed": True,
        "risk_level": "L1",
        "action": "allow_with_audit",
        "route": "gateway",
        "reason": "fail-closed adapter allowed low-risk packet",
        "errors": [],
        "warnings": [],
        "audit_required": True,
        "rollback_required": False,
    }


def validate(packet: dict[str, Any]) -> dict[str, Any]:
    fallback = fail_closed_validate(packet)
    validator = load_existing_validator()
    if validator is None:
        return fallback
    try:
        result = validator(packet)
    except TypeError:
        try:
            result = validator(packet.get("TensorPacket", packet))
        except Exception as exc:
            return _deadbox(f"existing validator failed closed: {type(exc).__name__}", [str(exc)])
    except Exception as exc:
        return _deadbox(f"existing validator failed closed: {type(exc).__name__}", [str(exc)])

    if not isinstance(result, dict):
        return _deadbox("existing validator returned non-object result", ["validator returned non-object result"])
    if not fallback.get("allowed"):
        return fallback
    if result.get("allowed") is False:
        errors = result.get("errors") if isinstance(result.get("errors"), list) else ["existing validator denied packet"]
        warnings = result.get("warnings") if isinstance(result.get("warnings"), list) else []
        return _deadbox("existing validator denied packet", errors, warnings)

    result.setdefault("allowed", True)
    result.setdefault("risk_level", "L1")
    result.setdefault("action", "allow_with_audit")
    result.setdefault("route", "gateway")
    result.setdefault("audit_required", True)
    result.setdefault("rollback_required", False)
    return result
