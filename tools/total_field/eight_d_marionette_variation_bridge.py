"""8D marionette-master variation bridge.

8D packet is treated as a multi-axis avatar control vector:
- face
- head
- hands
- body
- gaze
- camera
- voice
- tempo

This is not physical puppet pulling.
This is 8D packet -> control vector -> LUT-controlled avatar variation.

No runtime write.
No VRM binary commit.
No video render.
No deploy / restart / DB write.
"""

from __future__ import annotations

import json
from math import prod
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence


DEFAULT_MAP_PATH = Path("configs/total_field/eight_d_marionette_variation_map.json")


def load_marionette_variation_map(path: str | Path = DEFAULT_MAP_PATH) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    if data.get("mode") != "candidate_only_no_runtime_write":
        raise ValueError("marionette variation map must remain candidate_only_no_runtime_write")

    policy = data.get("policy") or {}
    required_false = [
        "delete",
        "restore",
        "deploy",
        "restart",
        "db_write",
        "router_write",
        "web_cockpit_touch",
        "runtime_bulk_output",
        "production_activation",
        "commit_vrm_binary",
        "render_video_now",
        "physical_engine_required",
        "floating_point_ai_inference_required",
    ]
    bad = [key for key in required_false if policy.get(key) is not False]
    if bad:
        raise ValueError("unsafe policy: " + ",".join(bad))

    principle = data.get("principle") or {}
    if principle.get("eight_d_packet_controls_avatar") is not True:
        raise ValueError("8D packet avatar control must be explicit")
    if principle.get("marionette_master_variation") is not True:
        raise ValueError("marionette variation principle must be explicit")

    return data


def variation_capacity(map_data: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    data = dict(map_data or load_marionette_variation_map())
    required = list(data.get("required_packet_dimensions") or [])
    dimensions = dict(data.get("dimensions") or {})

    counts = {}
    for dim in required:
        item = dict(dimensions.get(dim) or {})
        choices = list(item.get("choices") or [])
        counts[dim] = max(1, len(choices))

    capacity = prod(counts.values()) if counts else 0
    baseline = int(data.get("manual_puppet_reference", {}).get("symbolic_baseline_actions", 1024))

    return {
        "STATE": "PASS_8D_VARIATION_CAPACITY_COMPUTED",
        "dimension_counts": counts,
        "variation_capacity": capacity,
        "symbolic_manual_puppet_baseline": baseline,
        "exceeds_symbolic_manual_puppet_baseline": capacity > baseline,
        "runtime_write": False,
    }


def required_dimension_status(packet: Mapping[str, Any], map_data: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    data = dict(map_data or load_marionette_variation_map())
    required = list(data.get("required_packet_dimensions") or [])
    missing = [key for key in required if key not in packet]

    return {
        "STATE": "PASS_8D_DIMENSIONS_PRESENT" if not missing else "HOLD_8D_DIMENSIONS_MISSING",
        "missing": missing,
        "required": required,
    }


def _text(value: Any) -> str:
    if isinstance(value, Mapping):
        return " ".join(f"{key}={val}" for key, val in sorted(value.items()))
    return str(value or "")


def _select_control_state(packet: Mapping[str, Any]) -> str:
    explicit = str(packet.get("control_code") or packet.get("action_code") or "").strip()
    if explicit:
        return explicit

    combined = " ".join(
        [
            _text(packet.get("d1_intent")),
            _text(packet.get("d2_state")),
            _text(packet.get("d3_coordinate")),
            _text(packet.get("d5_execution")),
            _text(packet.get("d7_risk")),
            str(packet.get("decision") or packet.get("total_field_decision") or ""),
        ]
    ).lower()

    if any(x in combined for x in ["redteam", "critical", "secret", "token", "password", "會員明文", "payment_capture"]):
        return "REDTEAM_DEFENSE"

    if any(x in combined for x in ["deploy", "restart", "db_write", "router_write", "production_activation"]):
        return "REDTEAM_DEFENSE"

    if any(x in combined for x in ["total_field_decides", "owner_admin_review", "總場", "verify"]):
        return "TOTAL_FIELD_DECIDES"

    if any(x in combined for x in ["不能", "不懂", "unknown", "菜鳥", "hold"]):
        return "ROOKIE_ESCALATE"

    if any(x in combined for x in ["主播", "anchor", "drink_intro", "飲料介紹", "介紹飲料"]):
        return "ANCHOR_DESK_DRINK_INTRO"

    if any(x in combined for x in ["點單", "點餐", "order", "menu", "推薦"]):
        return "ORDER_GUIDE"

    if any(x in combined for x in ["歡迎", "招呼", "wave", "hello"]):
        return "GREETING_WAVE"

    return "IDLE"


def build_8d_marionette_control_packet(
    packet: Mapping[str, Any],
    *,
    map_data: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    data = dict(map_data or load_marionette_variation_map())
    dim_status = required_dimension_status(packet, data)
    capacity = variation_capacity(data)

    if dim_status["STATE"] != "PASS_8D_DIMENSIONS_PRESENT":
        control_code = "TOTAL_FIELD_DECIDES"
    else:
        control_code = _select_control_state(packet)

    states = dict(data.get("control_states") or {})
    state = dict(states.get(control_code) or states.get("IDLE") or {})
    resolved_code = control_code if control_code in states else "IDLE"

    return {
        "STATE": "PASS_8D_MARIONETTE_CONTROL_RESOLVED",
        "packet_type": "8d_marionette_master_variation_control_packet",
        "control_code": resolved_code,
        "state_id": state.get("state_id", 0),
        "control_vector": {
            "face": state.get("face", "neutral"),
            "head": state.get("head", "center"),
            "hands": state.get("hands", "rest"),
            "body": state.get("body", "standing_idle"),
            "gaze": state.get("gaze", "front"),
            "camera": state.get("camera", "medium"),
            "voice": state.get("voice", "calm"),
            "tempo": state.get("tempo", "slow")
        },
        "member_facing": state.get("member_facing", ""),
        "dimension_status": dim_status,
        "variation_capacity": capacity["variation_capacity"],
        "exceeds_symbolic_manual_puppet_baseline": capacity["exceeds_symbolic_manual_puppet_baseline"],
        "control_method": "8d_packet_to_control_vector_to_lut",
        "marionette_master_variation": True,
        "runtime_write": False,
        "render_video_now": False,
        "physics_engine_required": False,
        "floating_point_ai_inference_required": False,
        "deploy": False,
        "restart": False,
        "db_write": False,
        "commit_vrm_binary": False,
    }


def build_marionette_sequence(
    packets: Sequence[Mapping[str, Any]],
    *,
    map_data: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    data = dict(map_data or load_marionette_variation_map())

    controls = [
        build_8d_marionette_control_packet(packet, map_data=data)
        for packet in packets
    ]

    return {
        "STATE": "PASS_8D_MARIONETTE_SEQUENCE_CANDIDATE" if controls else "HOLD_EMPTY_MARIONETTE_SEQUENCE",
        "packet_type": "8d_marionette_sequence_candidate",
        "control_count": len(controls),
        "controls": controls,
        "movie_possible": len(controls) >= 2,
        "render_video_now": False,
        "runtime_write": False,
        "deploy": False,
        "restart": False,
        "db_write": False,
        "commit_vrm_binary": False,
    }
