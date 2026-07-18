"""Shared D1-D8 packet builder over the one authoritative runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from tools.total_field.w7tp_field_application_runtime import (
    CAPABILITY_REGISTRY_PATH,
    SCENARIO_ROUTE_TABLE_PATH,
    FieldApplicationError,
    build_field_application_packet,
    load_authoritative_route_and_capability,
)
from tools.total_field.w7tp_core_encoding import build_packet_field_encoding

from .canonical_hash import canonical_sha256, normalize_content
from .contracts import get_contract
from .drift_monitor import evaluate_drift
from .guided_completion import (
    build_guided_completion_packet,
    continue_guided_completion,
    validate_safe_content,
)


def _source_snapshot(route_table: Mapping[str, Any], registry: Mapping[str, Any]) -> dict[str, str]:
    return {
        "scenario_route_table_sha256": canonical_sha256(route_table),
        "capability_registry_sha256": canonical_sha256(registry),
    }


def _drift_hold_packet(
    profile: str,
    intent: Mapping[str, Any],
    snapshot: Mapping[str, str],
    monitor: Mapping[str, Any],
    execution_metadata: Mapping[str, Any] | None,
) -> dict[str, Any]:
    packet = {
        "schema_version": "W7TP-SHARED-REDTEAM-DRIFT-HOLD/1.0",
        "state": "HOLD_DETOUR_ALERT",
        "packet_type": "REDTEAM_DRIFT_ALERT_PACKET",
        "profile": profile,
        "candidate_only": True,
        "intent_content_sha256": canonical_sha256(intent),
        "source_snapshot": dict(snapshot),
        "redteam_drift_monitor": dict(monitor),
        "D7": {
            "risk_status": "DRIFT_ALERT",
            "drift_alert_count": monitor["alert_count"],
            "drift_alert_codes": [item["code"] for item in monitor["alerts"]],
        },
        "D8": {
            "authority": "LOCAL_TOTAL_FIELD_ONLY",
            "decision": "HOLD_DETOUR_ALERT",
            "candidate_only": True,
            "formal_execution": False,
        },
        "side_effects": {
            "db_write": False,
            "formal_transaction": False,
            "network_call": False,
        },
    }
    content = normalize_content(packet)
    content["content_sha256"] = canonical_sha256(content)
    content["execution_metadata"] = normalize_content(dict(execution_metadata or {}))
    return content


def process_intent(
    profile: str,
    intent: Mapping[str, Any],
    *,
    state_id: str | None = None,
    question_id: str | None = None,
    answer: Any = None,
    execution_metadata: Mapping[str, Any] | None = None,
    route_table_path: Path = SCENARIO_ROUTE_TABLE_PATH,
    capability_registry_path: Path = CAPABILITY_REGISTRY_PATH,
) -> dict[str, Any]:
    """Return one guided packet or one deterministic L3 candidate packet."""

    if not isinstance(profile, str):
        raise FieldApplicationError("SCENARIO_TOKEN_INVALID")
    profile = profile.strip().upper()
    contract = get_contract(profile)
    route, _capability, route_table, registry = load_authoritative_route_and_capability(
        profile,
        route_table_path=route_table_path,
        capability_registry_path=capability_registry_path,
    )
    if route.get("packet_type") != contract.packet_type:
        raise FieldApplicationError("PROFILE_ROUTE_PACKET_TYPE_MISMATCH")
    snapshot = _source_snapshot(route_table, registry)
    safe_intent = validate_safe_content(dict(intent))

    continuation_values = (state_id, question_id)
    if any(value is not None for value in continuation_values):
        if not all(value is not None for value in continuation_values) or answer is None:
            raise FieldApplicationError("GUIDED_CONTINUATION_INCOMPLETE")
        safe_intent = continue_guided_completion(
            profile,
            safe_intent,
            snapshot,
            state_id=str(state_id),
            question_id=str(question_id),
            answer=answer,
        )

    redteam_monitor = evaluate_drift(safe_intent)
    if redteam_monitor["status"] == "DRIFT_ALERT":
        return _drift_hold_packet(
            profile,
            safe_intent,
            snapshot,
            redteam_monitor,
            execution_metadata,
        )

    guided = build_guided_completion_packet(profile, safe_intent, snapshot)
    if guided is not None:
        return guided

    base = build_field_application_packet(
        profile,
        safe_intent,
        route_table_path=route_table_path,
        capability_registry_path=capability_registry_path,
    )
    compatibility_sha256 = base.pop("packet_sha256")
    base["schema_version"] = "W7TP-SHARED-8D-INTENT-FIELD/1.0"
    base["profile"] = profile
    base["D2"]["intent_state_id"] = canonical_sha256(
        {"profile": profile, "intent": safe_intent, "source_snapshot": snapshot}
    )
    base["D4"]["source_snapshot"] = snapshot
    base["D5"]["shared_runtime"] = "tools/total_field/w7tp_field_application_runtime.py"
    base["D6"]["effect_equivalence_conditions"] = {
        "task_state_control_effect_match": True,
        "byte_identity_required": False,
        "local_state_machine_judgment_required": True,
    }
    base["D7"]["redteam_status"] = redteam_monitor["status"]
    base["D7"]["drift_alert_count"] = redteam_monitor["alert_count"]
    base["D7"]["drift_alert_codes"] = [item["code"] for item in redteam_monitor["alerts"]]
    base["D8"]["founder_adoption"] = "REQUIRES_EXISTING_LOCAL_FOUNDER_ROOT_VERIFICATION"
    base["redteam_drift_monitor"] = redteam_monitor
    base["compatibility_packet_sha256"] = compatibility_sha256
    base["field_encoding"] = build_packet_field_encoding(
        base,
        profile,
        base["D2"]["intent_state_id"],
    )
    content = normalize_content(base)
    content["content_sha256"] = canonical_sha256(content)
    content["execution_metadata"] = normalize_content(dict(execution_metadata or {}))
    return content
