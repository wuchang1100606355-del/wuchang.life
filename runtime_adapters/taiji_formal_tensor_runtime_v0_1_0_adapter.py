#!/usr/bin/env python3
"""Taiji formal tensor runtime v0.1.0 fail-closed validator adapter.

This adapter is intentionally standard-library only. It tries to use the
existing repository validator first, then applies fail-closed rules that block
unsafe payment, plaintext, replay, and missing tensor-state conditions.
"""

from __future__ import annotations

import importlib
from typing import Any, Callable


EXISTING_VALIDATOR_MODULE = "services.gateway.policies.formal_tensor_validator"
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
        module = importlib.import_module(EXISTING_VALIDATOR_MODULE)
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


def tensor_root(packet: dict[str, Any]) -> dict[str, Any] | None:
    root = packet.get("TensorPacket")
    return root if isinstance(root, dict) else None


def fail_closed_validate(packet: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    root = tensor_root(packet)
    if root is None:
        errors.append("missing TensorPacket root")
        root = {}

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
    if intent_type in BLOCKED_INTENT_TYPES:
        errors.append(f"blocked intent type: {intent_type}")

    if authority_metric.get("payment_allowed") is True or payload.get("payment_allowed") is True:
        errors.append("payment_allowed=true is blocked")

    if audit_snapshot.get("plaintext_context_stored") is True or payload.get("plaintext_context_stored") is True:
        errors.append("plaintext_context_stored=true is blocked")

    if replay_vector.get("replay_safe") is False:
        warnings.append("replay_safe=false routes to deadbox")

    if audit_snapshot.get("secret_material_printed") is True:
        errors.append("secret_material_printed=true is blocked")

    if audit_snapshot.get("external_api_called") is True:
        errors.append("external_api_called=true is blocked")

    if audit_snapshot.get("live_deploy_executed") is True:
        errors.append("live_deploy_executed=true is blocked")

    if errors or warnings:
        return {
            "allowed": False,
            "risk_level": "L3" if errors else "L2",
            "action": "block" if errors else "warn",
            "route": "deadbox",
            "reason": "fail-closed rule triggered",
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
        "reason": "fail-closed adapter allowed low-risk packet",
        "errors": [],
        "warnings": [],
        "audit_required": True,
        "rollback_required": False,
    }


def validate(packet: dict[str, Any]) -> dict[str, Any]:
    validator = load_existing_validator()
    fallback = fail_closed_validate(packet)

    if validator is None:
        return fallback

    try:
        result = validator(packet)
    except TypeError:
        try:
            result = validator(packet.get("TensorPacket", packet))
        except Exception as exc:
            fallback["allowed"] = False
            fallback["risk_level"] = "L3"
            fallback["action"] = "block"
            fallback["route"] = "deadbox"
            fallback["reason"] = f"existing validator failed closed: {type(exc).__name__}"
            fallback.setdefault("errors", []).append(str(exc))
            return fallback
    except Exception as exc:
        fallback["allowed"] = False
        fallback["risk_level"] = "L3"
        fallback["action"] = "block"
        fallback["route"] = "deadbox"
        fallback["reason"] = f"existing validator failed closed: {type(exc).__name__}"
        fallback.setdefault("errors", []).append(str(exc))
        return fallback

    if not isinstance(result, dict):
        fallback["allowed"] = False
        fallback["risk_level"] = "L3"
        fallback["action"] = "block"
        fallback["route"] = "deadbox"
        fallback["reason"] = "existing validator returned non-object result"
        fallback.setdefault("errors", []).append("validator returned non-object result")
        return fallback

    if not fallback.get("allowed"):
        return fallback

    result.setdefault("allowed", True)
    result.setdefault("risk_level", "L1")
    result.setdefault("action", "allow_with_audit")
    result.setdefault("route", "gateway")
    result.setdefault("audit_required", True)
    result.setdefault("rollback_required", False)
    return result
