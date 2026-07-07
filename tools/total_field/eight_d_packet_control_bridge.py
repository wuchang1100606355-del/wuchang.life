"""8D packet control bridge.

8D packet can control:
- state gate
- member-facing response
- VRM LUT state
- redteam hold
- route candidate
- Total Field decision flow

It never directly performs:
- DB write
- deploy
- restart
- router write
- payment capture
- production activation
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping


DEFAULT_MAP_PATH = Path("configs/total_field/eight_d_packet_control_map.json")

ROOKIE_MESSAGE = "這個我不懂，我只是個菜鳥，我幫你問店長或學長"


def load_control_map(path: str | Path = DEFAULT_MAP_PATH) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    if data.get("mode") != "candidate_only_no_runtime_write":
        raise ValueError("8D control map must remain candidate_only_no_runtime_write")

    policy = data.get("policy") or {}
    for key in [
        "delete",
        "restore",
        "deploy",
        "restart",
        "db_write",
        "router_write",
        "web_cockpit_touch",
        "runtime_bulk_output",
        "production_activation",
        "direct_physical_execution",
    ]:
        if policy.get(key) is not False:
            raise ValueError(f"unsafe policy: {key}")

    if data.get("control_principle", {}).get("eight_d_packet_controls") is not True:
        raise ValueError("8D packet control must be explicit")

    return data


def _as_dict(value: Any) -> Dict[str, Any]:
    return dict(value or {}) if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    if isinstance(value, Mapping):
        return " ".join(f"{k}={v}" for k, v in sorted(value.items()))
    return str(value or "")


def _has_any(text: str, fragments: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(fragment.lower() in lowered for fragment in fragments)


def required_dimension_status(packet: Mapping[str, Any], control_map: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    data = dict(control_map or load_control_map())
    required = list(data.get("required_packet_dimensions") or [])
    missing = [key for key in required if key not in packet]
    return {
        "STATE": "PASS_8D_DIMENSIONS_PRESENT" if not missing else "HOLD_8D_DIMENSIONS_MISSING",
        "missing": missing,
        "required": required,
    }


def decide_control_code(packet: Mapping[str, Any]) -> str:
    d1 = _text(packet.get("d1_intent"))
    d2 = _text(packet.get("d2_state"))
    d5 = _text(packet.get("d5_execution"))
    d7 = _text(packet.get("d7_risk"))
    d8 = _as_dict(packet.get("d8_envelope"))
    decision = str(packet.get("total_field_decision") or packet.get("decision") or "").upper()

    combined = " ".join([d1, d2, d5, d7, decision])

    if _has_any(combined, ("redteam", "critical", "secret", "token", "password", "會員明文", "payment_capture")):
        return "REDTEAM_DEFENSE"

    if _has_any(combined, ("db_write", "deploy", "restart", "router_write", "production_activation", "formal_activation")):
        return "REDTEAM_DEFENSE"

    if _has_any(combined, ("detour", "scope_drift", "paste_burden", "nonessential_validation")):
        return "HOLD_DETOUR_ALERT"

    if decision in {"BLOCK", "REDTEAM_HOLD", "HOLD_REDTEAM"}:
        return "REDTEAM_DEFENSE"

    if decision in {"HOLD_DETOUR_ALERT"}:
        return "HOLD_DETOUR_ALERT"

    if decision in {"HOLD", "UNKNOWN", ""}:
        if d8.get("decision_authority") != "total_field":
            return "TOTAL_FIELD_DECIDES"
        return "ROOKIE_ESCALATE"

    if decision in {"PASS", "PASS_CANDIDATE", "PASS_INTENT", "PASS_RECONSTRUCTED_CANDIDATE"}:
        return "PASS_INTENT"

    return "ROOKIE_ESCALATE"


def build_8d_control_packet(
    packet: Mapping[str, Any],
    *,
    control_map: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    data = dict(control_map or load_control_map())
    dimension_status = required_dimension_status(packet, data)
    control_code = decide_control_code(packet)
    control = dict(data["control_codes"][control_code])

    if dimension_status["STATE"] != "PASS_8D_DIMENSIONS_PRESENT":
        control_code = "TOTAL_FIELD_DECIDES"
        control = dict(data["control_codes"][control_code])

    return {
        "STATE": "PASS_8D_PACKET_CONTROL_RESOLVED",
        "packet_type": "8d_packet_control_packet",
        "control_code": control_code,
        "state_id": control["state_id"],
        "member_facing": control["member_facing"],
        "vrm_expression": control["vrm_expression"],
        "motion": control["motion"],
        "dimension_status": dimension_status,
        "engine": "8d_packet_lookup_control",
        "eight_d_packet_controls": True,
        "runtime_write": False,
        "deploy": False,
        "restart": False,
        "db_write": False,
        "router_write": False,
        "production_activation": False,
    }


def member_facing_from_8d_packet(packet: Mapping[str, Any]) -> str:
    return build_8d_control_packet(packet)["member_facing"]
