"""8D packet cinematic transition bridge.

8D packet -> control state -> LUT transition -> cinematic timeline candidate.

This source layer supports:
- packet-to-packet smooth transition
- multi-packet cinematic sequence
- avatar expression / gesture / pose / motion / camera / tempo blending
- movie-like timeline candidate

No video render.
No VRM binary commit.
No runtime write.
No deploy.
No restart.
No DB write.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


DEFAULT_MAP_PATH = Path("configs/total_field/eight_d_packet_cinematic_transition_map.json")


def load_cinematic_transition_map(path: str | Path = DEFAULT_MAP_PATH) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    if data.get("mode") != "candidate_only_no_runtime_write":
        raise ValueError("cinematic transition map must remain candidate_only_no_runtime_write")

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
    if principle.get("packet_to_packet_transition") is not True:
        raise ValueError("packet-to-packet transition must be explicit")
    if principle.get("cinematic_timeline_candidate") is not True:
        raise ValueError("cinematic timeline candidate must be explicit")

    return data


def smoothstep(t: float) -> float:
    value = max(0.0, min(1.0, float(t)))
    return value * value * (3.0 - 2.0 * value)


def required_dimension_status(
    packet: Mapping[str, Any],
    *,
    map_data: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    data = dict(map_data or load_cinematic_transition_map())
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


def _select_control_code(packet: Mapping[str, Any]) -> str:
    explicit = str(packet.get("control_code") or packet.get("action_code") or "").strip()
    if explicit:
        return explicit

    combined = " ".join(
        [
            _text(packet.get("d1_intent")),
            _text(packet.get("d2_state")),
            _text(packet.get("d5_execution")),
            _text(packet.get("d7_risk")),
            str(packet.get("decision") or packet.get("total_field_decision") or ""),
        ]
    ).lower()

    if any(fragment in combined for fragment in ["redteam", "risk", "風險", "secret", "token", "password", "deploy", "restart", "db_write"]):
        return "REDTEAM_DEFENSE"
    if any(fragment in combined for fragment in ["anchor", "主播", "飲料介紹", "drink_intro"]):
        return "ANCHOR_DESK_DRINK_INTRO"
    if any(fragment in combined for fragment in ["order", "點單", "菜單", "recommend", "推薦"]):
        return "ORDER_GUIDE"
    if any(fragment in combined for fragment in ["welcome", "hello", "招呼", "揮手", "歡迎"]):
        return "GREETING_WAVE"
    if any(fragment in combined for fragment in ["hold", "不能", "unknown", "菜鳥"]):
        return "ROOKIE_ESCALATE"

    return "IDLE"


def resolve_control_state(
    packet: Mapping[str, Any],
    *,
    map_data: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    data = dict(map_data or load_cinematic_transition_map())
    controls = dict(data.get("default_control_states") or {})
    code = _select_control_code(packet)
    state = dict(controls.get(code) or controls.get("IDLE") or {})

    return {
        "control_code": code if code in controls else "IDLE",
        "state_id": int(state.get("state_id", 0)),
        "expression": state.get("expression", "neutral"),
        "gesture": state.get("gesture", "standby"),
        "pose": state.get("pose", "standing_idle"),
        "motion": state.get("motion", "breathing_idle"),
        "camera": state.get("camera", "medium"),
        "tempo": state.get("tempo", "slow"),
        "voice_hint": state.get("voice_hint", "calm"),
        "member_facing": state.get("member_facing", ""),
    }


def _mix_label(a: str, b: str, eased: float) -> str:
    if eased <= 0.0:
        return a
    if eased >= 1.0:
        return b
    return f"{a}->{b}@{eased:.2f}"


def build_packet_transition(
    from_packet: Mapping[str, Any],
    to_packet: Mapping[str, Any],
    *,
    frames: int | None = None,
    duration_ms: int = 1000,
    map_data: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    data = dict(map_data or load_cinematic_transition_map())

    from_dim = required_dimension_status(from_packet, map_data=data)
    to_dim = required_dimension_status(to_packet, map_data=data)

    if from_dim["STATE"] != "PASS_8D_DIMENSIONS_PRESENT" or to_dim["STATE"] != "PASS_8D_DIMENSIONS_PRESENT":
        return {
            "STATE": "HOLD_8D_CINEMATIC_TRANSITION_DIMENSION_MISSING",
            "from_dimension_status": from_dim,
            "to_dimension_status": to_dim,
            "runtime_write": False,
            "render_video_now": False,
        }

    controls = dict(data.get("transition_controls") or {})
    default_frames = int(controls.get("default_frames", 16))
    max_frames = int(controls.get("max_candidate_frames", 48))

    frame_count = int(frames or default_frames)
    frame_count = max(2, min(frame_count, max_frames))

    from_state = resolve_control_state(from_packet, map_data=data)
    to_state = resolve_control_state(to_packet, map_data=data)

    generated_frames: List[Dict[str, Any]] = []

    for index in range(frame_count):
        raw_t = index / (frame_count - 1)
        eased = smoothstep(raw_t)
        state_id = round(from_state["state_id"] * (1.0 - eased) + to_state["state_id"] * eased)

        generated_frames.append(
            {
                "frame": index,
                "t": round(raw_t, 4),
                "eased": round(eased, 4),
                "from_weight": round(1.0 - eased, 4),
                "to_weight": round(eased, 4),
                "state_id": state_id,
                "expression": _mix_label(from_state["expression"], to_state["expression"], eased),
                "gesture": _mix_label(from_state["gesture"], to_state["gesture"], eased),
                "pose": _mix_label(from_state["pose"], to_state["pose"], eased),
                "motion": _mix_label(from_state["motion"], to_state["motion"], eased),
                "camera": _mix_label(from_state["camera"], to_state["camera"], eased),
                "tempo": _mix_label(from_state["tempo"], to_state["tempo"], eased),
                "voice_hint": _mix_label(from_state["voice_hint"], to_state["voice_hint"], eased),
            }
        )

    return {
        "STATE": "PASS_8D_PACKET_CINEMATIC_TRANSITION",
        "packet_type": "8d_packet_to_packet_cinematic_transition",
        "from_control_code": from_state["control_code"],
        "to_control_code": to_state["control_code"],
        "duration_ms": int(duration_ms),
        "frame_count": frame_count,
        "easing": "smoothstep",
        "frames": generated_frames,
        "member_facing_from": from_state["member_facing"],
        "member_facing_to": to_state["member_facing"],
        "runtime_write": False,
        "render_video_now": False,
        "deploy": False,
        "restart": False,
        "db_write": False,
        "commit_vrm_binary": False,
    }


def build_cinematic_sequence(
    packets: Sequence[Mapping[str, Any]],
    *,
    frames_per_transition: int = 16,
    duration_ms_per_transition: int = 1000,
    map_data: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    data = dict(map_data or load_cinematic_transition_map())

    if len(packets) < 2:
        return {
            "STATE": "HOLD_CINEMATIC_SEQUENCE_NEEDS_AT_LEAST_TWO_PACKETS",
            "segment_count": 0,
            "runtime_write": False,
            "render_video_now": False,
        }

    segments = []
    for index in range(len(packets) - 1):
        segment = build_packet_transition(
            packets[index],
            packets[index + 1],
            frames=frames_per_transition,
            duration_ms=duration_ms_per_transition,
            map_data=data,
        )
        if segment["STATE"] != "PASS_8D_PACKET_CINEMATIC_TRANSITION":
            return {
                "STATE": "HOLD_CINEMATIC_SEQUENCE_SEGMENT_NOT_READY",
                "failed_segment": index,
                "segment": segment,
                "runtime_write": False,
                "render_video_now": False,
            }
        segments.append(segment)

    return {
        "STATE": "PASS_8D_CINEMATIC_SEQUENCE_CANDIDATE",
        "packet_type": "8d_cinematic_sequence_candidate",
        "segment_count": len(segments),
        "segments": segments,
        "movie_possible": True,
        "render_video_now": False,
        "runtime_write": False,
        "deploy": False,
        "restart": False,
        "db_write": False,
        "commit_vrm_binary": False,
    }
