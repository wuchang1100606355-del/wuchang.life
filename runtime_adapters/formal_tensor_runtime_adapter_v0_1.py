#!/usr/bin/env python3
"""Fail-closed adapter for the Taiji formal tensor validator.

This module intentionally uses only the Python standard library. It attempts to
delegate to the repository validator when available. If import or invocation
fails, it enforces a conservative fail-closed policy.
"""

from __future__ import annotations

import importlib
from typing import Any, Callable


BLOCKED_INTENTS = {
    "payment_execute",
    "refund",
    "discount_override",
    "manager_override",
    "credential_issue",
    "production_overwrite",
    "database_direct_write",
    "live_deploy",
}


def _load_existing_validator() -> Callable[[dict[str, Any]], dict[str, Any]] | None:
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


def _root(packet: dict[str, Any]) -> dict[str, Any] | None:
    root = packet.get("TensorPacket")
    return root if isinstance(root, dict) else None


def fail_closed_validate(packet: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    root = _root(packet)
    if root is None:
        return {
            "allowed": False,
            "risk_level": "L3",
            "action": "block",
            "route": "deadbox",
            "reason": "missing TensorPacket root",
            "errors": ["missing TensorPacket root"],
            "warnings": [],
            "audit_required": True,
            "rollback_required": True,
        }

    tau = root.get("tau")
    if not isinstance(tau, dict):
        errors.append("missing tau")
        tau = {}

    intent_metric = tau.get("I", {}) if isinstance(tau.get("I", {}), dict) else {}
    authority_metric = tau.get("A", {}) if isinstance(tau.get("A", {}), dict) else {}
    replay_vector = root.get("rho", {}) if isinstance(root.get("rho", {}), dict) else {}
    audit_snapshot = root.get("alpha", {}) if isinstance(root.get("alpha", {}), dict) else {}
    payload = root.get("pi", {}) if isinstance(root.get("pi", {}), dict) else {}

    intent_type = str(intent_metric.get("type", "unknown"))
    if intent_type in BLOCKED_INTENTS:
        errors.append(f"{intent_type} is blocked")

    if authority_metric.get("payment_allowed") is True:
        errors.append("payment_allowed=true is blocked")

    if payload.get("payment_allowed") is True:
        errors.append("payload payment_allowed=true is blocked")

    if audit_snapshot.get("plaintext_context_stored") is True:
        errors.append("plaintext_context_stored=true is blocked")

    if payload.get("plaintext_context_stored") is True:
        errors.append("payload plaintext_context_stored=true is blocked")

    if replay_vector.get("replay_safe") is False:
        warnings.append("replay_safe=false routes to deadbox")

    if audit_snapshot.get("secret_material_printed") is True:
        errors.append("secret_material_printed=true is blocked")

    if audit_snapshot.get("external_api_called") is True:
        errors.append("external_api_called=true is blocked in local runtime")

    if audit_snapshot.get("live_deploy_executed") is True:
        errors.append("live_deploy_executed=true is blocked in local runtime")

    if errors or warnings:
        return {
            "allowed": False,
            "risk_level": "L3" if errors else "L2",
            "action": "block" if errors else "warn",
            "route": "deadbox",
            "reason": "fail-closed governance rule triggered",
            "errors": errors,
            "warnings": warnings,
            "audit_required": True,
            "rollback_required": True,
        }

    return {
        "allowed": True,
        "risk_level": "L1",
        "action": "allow_with_audit",
        "route": "gateway",
        "reason": "fail-closed validation passed",
        "errors": [],
        "warnings": [],
        "audit_required": True,
        "rollback_required": False,
    }


def validate(packet: dict[str, Any]) -> dict[str, Any]:
    validator = _load_existing_validator()
    if validator is None:
        return fail_closed_validate(packet)

    try:
        result = validator(packet)
    except TypeError:
        result = validator(packet.get("TensorPacket", packet))
    except Exception as exc:
        closed = fail_closed_validate(packet)
        closed["allowed"] = False
        closed["risk_level"] = "L3"
        closed["action"] = "block"
        closed["route"] = "deadbox"
        closed["reason"] = f"existing validator failed closed: {type(exc).__name__}"
        closed.setdefault("errors", []).append(str(exc))
        return closed

    if not isinstance(result, dict):
        closed = fail_closed_validate(packet)
        closed["allowed"] = False
        closed["risk_level"] = "L3"
        closed["action"] = "block"
        closed["route"] = "deadbox"
        closed["reason"] = "existing validator returned non-object result"
        closed.setdefault("errors", []).append("validator returned non-object result")
        return closed

    fallback = fail_closed_validate(packet)
    if not fallback.get("allowed"):
        return fallback

    result.setdefault("allowed", True)
    result.setdefault("risk_level", "L1")
    result.setdefault("action", "allow_with_audit")
    result.setdefault("route", "gateway")
    result.setdefault("audit_required", True)
    result.setdefault("rollback_required", False)
    return result
