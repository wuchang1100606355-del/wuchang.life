from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from .policy_engine import evaluate_policy


D8_TWO_PHASE_GATES = (
    "SOURCE_BOUND",
    "SOURCE_ZONE_BOUND",
    "INTERFACE_BOUND",
    "ROUTE_BOUND",
    "TARGET_BOUND",
    "TARGET_ZONE_BOUND",
    "SERVICE_PASS",
    "APPLICATION_PASS",
    "RESPONSE_VERIFIED",
)

_LEGACY_GATE_NAMES = {
    "SOURCE_BOUND": "source",
    "INTERFACE_BOUND": "interface",
    "ROUTE_BOUND": "route",
    "TARGET_BOUND": "target",
    "SERVICE_PASS": "service",
    "APPLICATION_PASS": "application",
    "RESPONSE_VERIFIED": "response",
}


def select_route(
    intent: dict[str, Any],
    paths: list[dict[str, Any]],
    verification: dict[str, Any] | None = None,
    *,
    observed_at: str | None = None,
    ttl_seconds: int = 300,
    policy_version: str = "PER_INTENT_MULTIPATH_V1",
    now: str | datetime | None = None,
) -> dict[str, Any]:
    """Resolve one intent and apply D8's verification phase fail-closed."""

    policy = evaluate_policy(intent, paths, now=now)
    selected_id = policy.get("selected_path")
    selected_verification = _verification_for_path(verification or {}, selected_id)
    gates = _normalize_gates(intent, selected_verification)
    candidate_selected = policy.get("candidate_decision") == "CANDIDATE_PATH_SELECTED"
    authorized = bool(candidate_selected and all(gates.values()))

    timestamp = observed_at or _format_time(_coerce_time(now) or datetime.now(timezone.utc))
    observed_time = _coerce_time(timestamp)
    if observed_time is None:
        raise ValueError("invalid_observed_at")
    decision_expiry = observed_time + timedelta(seconds=max(1, ttl_seconds))
    selected_expiry = _selected_path_expiry(paths, selected_id)
    if selected_expiry and selected_expiry < decision_expiry:
        decision_expiry = selected_expiry
    expires_at = _format_time(decision_expiry)
    active_paths: list[str] = []
    if authorized and selected_id:
        active_paths.append(selected_id)
    for path_id in policy.get("concurrent_paths", []):
        if path_id == selected_id:
            continue
        concurrent_gates = _normalize_gates(intent, _verification_for_path(verification or {}, path_id))
        if all(concurrent_gates.values()):
            active_paths.append(path_id)

    decision = "D8_ALLOW_FOR_THIS_INTENT" if authorized else "HOLD"
    decision_state = "VERIFIED_CANDIDATE" if authorized else (
        "CANDIDATE_PATH_SELECTED_AWAITING_D8_CLOSURE" if candidate_selected else policy["candidate_decision"]
    )
    decision_id = _decision_id(intent, policy, gates, policy_version)

    return {
        **policy,
        "decision": decision,
        "authorized": authorized,
        "candidate_selection_state": policy["candidate_decision"],
        "d8_two_phase_gates": gates,
        "d8_two_phase_decision": "PASS" if authorized else "HOLD",
        "intent_id": intent.get("intent_id", "LOCALIZED_UNKNOWN"),
        "source_node": intent.get("source_node", "LOCALIZED_UNKNOWN"),
        "source_zone": intent.get("source_zone", "LOCALIZED_UNKNOWN"),
        "target_node": intent.get("target_node", "LOCALIZED_UNKNOWN"),
        "target_zone": intent.get("target_zone", "LOCALIZED_UNKNOWN"),
        "service_identity": intent.get("service_identity", "LOCALIZED_UNKNOWN"),
        "service_class": intent.get("service_class", "LOCALIZED_UNKNOWN"),
        "published_gateway_bound": bool(intent.get("published_gateway_bound", False)),
        "intent": dict(intent),
        "active_path_set": sorted(set(active_paths)),
        "end_to_end_chain": gates,
        "end_to_end_verified": authorized,
        "decision_state": decision_state,
        "binding_state": "HEALTHY" if authorized else "HOLD",
        "decision_id": decision_id,
        "observed_at": timestamp,
        "expires_at": expires_at,
        "ttl_seconds": max(1, ttl_seconds),
        "policy_version": policy_version,
        "authority_scope": "CANDIDATE_D8_DECISION_ONLY",
        "total_field_decision": "NOT_RUN",
        "canonical": False,
    }


def _normalize_gates(intent: dict[str, Any], verification: dict[str, Any]) -> dict[str, bool]:
    result: dict[str, bool] = {}
    for gate in D8_TWO_PHASE_GATES:
        snake = gate.lower()
        legacy = _LEGACY_GATE_NAMES.get(gate)
        if gate in verification:
            value = verification[gate]
        elif snake in verification:
            value = verification[snake]
        elif legacy and legacy in verification:
            value = verification[legacy]
        else:
            value = False
        result[gate] = bool(value)
    return result


def _verification_for_path(verification: dict[str, Any], path_id: str | None) -> dict[str, Any]:
    if path_id and isinstance(verification.get(path_id), dict):
        return verification[path_id]
    return verification


def _decision_id(
    intent: dict[str, Any],
    policy: dict[str, Any],
    gates: dict[str, bool],
    policy_version: str,
) -> str:
    payload = {
        "intent": {
            key: intent.get(key)
            for key in (
                "intent_id",
                "source_node",
                "source_zone",
                "target_node",
                "target_zone",
                "service_identity",
                "service_class",
                "published_gateway_bound",
            )
        },
        "selected_path": policy.get("selected_path"),
        "alternate_paths": policy.get("alternate_paths", []),
        "concurrent_paths": policy.get("concurrent_paths", []),
        "gates": gates,
        "policy_version": policy_version,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _selected_path_expiry(paths: list[dict[str, Any]], selected_id: str | None) -> datetime | None:
    if not selected_id:
        return None
    for path in paths:
        path_type = str(path.get("path_type", "UNKNOWN"))
        target = path.get("target") or path.get("interface")
        identifiers = {str(path.get("path_id") or path_type), path_type}
        if target:
            identifiers.add(f"{path_type}@{target}")
        if selected_id in identifiers:
            return _coerce_time(path.get("expires_at"))
    return None


def _coerce_time(value: str | datetime | None) -> datetime | None:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str):
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
