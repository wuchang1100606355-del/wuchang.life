"""Local-only validator for Taiji formal TensorPacket dictionaries.

This module performs structural and governance checks only. It does not call
external APIs, does not mutate Odoo/POS/browser runtimes, and does not execute
deployment commands.
"""

from __future__ import annotations

from typing import Any


BLOCKED_INTENT_TYPES = {
    "payment_execute",
}

BLOCKED_TARGET_RUNTIMES = {
    "production_overwrite",
    "credential_issuance",
}


def validate_formal_tensor_packet(packet: dict[str, Any]) -> dict[str, Any]:
    """Return a governance validation result for a formal TensorPacket."""

    errors: list[str] = []
    warnings: list[str] = []

    root = packet.get("TensorPacket")
    if not isinstance(root, dict):
        return _result(False, "L3", "block", ["missing_TensorPacket"], warnings)

    required = {"packet_id", "schema", "tau", "pi", "sigma", "lambda", "gamma", "rho", "kappa", "epsilon", "zeta", "alpha"}
    missing = sorted(required - set(root))
    if missing:
        errors.append("missing_fields:" + ",".join(missing))

    if root.get("schema") != "taiji.formal_tensor_packet.v1":
        errors.append("invalid_schema")

    tau = root.get("tau", {})
    if not isinstance(tau, dict):
        errors.append("tau_not_object")
        tau = {}

    for metric in ("I", "R", "T", "A", "P"):
        if metric not in tau:
            errors.append(f"missing_tau_{metric}")

    pi = root.get("pi", {})
    if isinstance(pi, dict) and pi.get("raw_plaintext_stored") is not False:
        errors.append("raw_plaintext_runtime_memory_forbidden")

    intent_type = _nested(tau, "I", "type")
    target_runtime = _nested(tau, "P", "target_runtime")
    governance_level = _nested(tau, "A", "governance_level")
    payment_boundary = _nested(tau, "A", "payment_boundary")
    credential_boundary = _nested(tau, "A", "credential_boundary")
    production_boundary = _nested(tau, "A", "production_overwrite_boundary")

    if intent_type in BLOCKED_INTENT_TYPES:
        errors.append("blocked_intent:" + str(intent_type))

    if target_runtime in BLOCKED_TARGET_RUNTIMES:
        errors.append("blocked_target_runtime:" + str(target_runtime))

    if payment_boundary == "blocked" and intent_type == "payment_execute":
        errors.append("payment_execute_blocked")

    if credential_boundary != "no_credential_access":
        errors.append("credential_boundary_must_be_no_access")

    if production_boundary == "blocked" and target_runtime == "production":
        errors.append("production_runtime_blocked")

    gamma = root.get("gamma", {})
    if isinstance(gamma, dict):
        risk_level = gamma.get("risk_level")
        human_decision = gamma.get("human_decision")
        audit_required = gamma.get("audit_required")
        rollback_required = gamma.get("rollback_required")
        if risk_level in {"L2", "L3"} and human_decision != "required":
            errors.append("human_decision_required_for_L2_L3")
        if risk_level in {"L1", "L2", "L3"} and audit_required is not True:
            errors.append("audit_required_for_L1_plus")
        if risk_level in {"L2", "L3"} and rollback_required is not True:
            errors.append("rollback_required_for_L2_L3")

    alpha = root.get("alpha", {})
    if isinstance(alpha, dict):
        if alpha.get("secret_material_printed") is not False:
            errors.append("secret_material_printed_forbidden")
        if alpha.get("external_api_called") is not False:
            errors.append("external_api_called_forbidden_in_local_validator")
        if alpha.get("live_deploy_executed") is not False:
            errors.append("live_deploy_forbidden")

    zeta = root.get("zeta", {})
    if isinstance(zeta, dict) and zeta.get("deadbox_state") == "deadbox":
        warnings.append("packet_already_deadboxed")

    if errors:
        risk = "L3" if any("blocked" in e or "forbidden" in e for e in errors) else "L2"
        return _result(False, risk, "block", errors, warnings)

    if governance_level == "L2_confirm":
        return _result(True, "L2", "warn", errors, warnings)

    if governance_level == "L1_audit":
        return _result(True, "L1", "allow_with_audit", errors, warnings)

    return _result(True, "L0", "allow", errors, warnings)


def _nested(data: dict[str, Any], *path: str) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _result(allowed: bool, risk_level: str, action: str, errors: list[str], warnings: list[str]) -> dict[str, Any]:
    return {
        "allowed": allowed,
        "risk_level": risk_level,
        "action": action,
        "errors": errors,
        "warnings": warnings,
        "external_api_called": False,
        "live_deploy_executed": False,
        "secret_material_printed": False,
    }
