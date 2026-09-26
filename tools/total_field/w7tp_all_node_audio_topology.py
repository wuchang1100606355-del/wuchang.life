#!/usr/bin/env python3
"""Role-aware all-node audio topology for W7TP / 8D ADI.

This overlay does not create audio authority. It prevents capability/node
availability from being mistaken for permission to render or capture audio.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TOPOLOGY_PATH = (
    ROOT / "configs/total_field/w7tp_all_node_audio_topology_v1.json"
)
EXPECTED_NODES = {
    "taiji01",
    "MSI",
    "taiji03",
    "taiji04",
    "drallion",
    "penguin",
    "wuchang-us-free-node",
}
WINDOWS_AUDIO_ROLES = {"CONSOLE", "MULTIMEDIA", "COMMUNICATIONS"}
DEPRECATED_MSI_WSL_TAILSCALE_IP = "100.84.204.114"


class AudioTopologyHold(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise AudioTopologyHold(code)


def load_audio_topology(path: Path = TOPOLOGY_PATH) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise AudioTopologyHold("HOLD_AUDIO_TOPOLOGY_READ_FAILED") from exc
    _require(isinstance(value, dict), "HOLD_AUDIO_TOPOLOGY_SHAPE_INVALID")
    validate_audio_topology(value)
    return copy.deepcopy(value)


def validate_audio_topology(value: dict[str, Any]) -> None:
    _require(
        value.get("schema_version") == "W7TP-ALL-NODE-AUDIO-TOPOLOGY/1.0",
        "HOLD_AUDIO_TOPOLOGY_SCHEMA_VERSION",
    )
    _require(value.get("canonical") is False, "HOLD_AUDIO_TOPOLOGY_CANONICAL_FORBIDDEN")
    boundary = value.get("authority_boundary") or {}
    _require(
        boundary.get("formal_effect_boundary") == "TAIJI01_TOTAL_FIELD"
        and boundary.get("device_or_provider_authority") is False
        and boundary.get("vpn_authority") is False
        and boundary.get("application_authority") is False
        and boundary.get("held_coordinate_selectable") is False,
        "HOLD_AUDIO_TOPOLOGY_AUTHORITY_DRIFT",
    )

    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    _require(
        DEPRECATED_MSI_WSL_TAILSCALE_IP not in encoded,
        "HOLD_DEPRECATED_MSI_WSL_AUDIO_ROUTE_PRESENT",
    )

    nodes = value.get("nodes")
    _require(isinstance(nodes, list), "HOLD_AUDIO_NODES_REQUIRED")
    by_id = {}
    for item in nodes:
        _require(isinstance(item, dict), "HOLD_AUDIO_NODE_INVALID")
        node_ref = item.get("node_ref")
        _require(isinstance(node_ref, str) and node_ref, "HOLD_AUDIO_NODE_REF_INVALID")
        _require(node_ref not in by_id, "HOLD_AUDIO_NODE_DUPLICATE")
        by_id[node_ref] = item
    _require(set(by_id) == EXPECTED_NODES, "HOLD_AUDIO_NODE_COVERAGE_INVALID")

    for node_ref in ("MSI", "taiji03"):
        item = by_id[node_ref]
        _require(item.get("state") == "PASS", "HOLD_WINDOWS_AUDIO_NODE_NOT_PASS")
        _require(item.get("user_audio_endpoint") is True, "HOLD_WINDOWS_AUDIO_ROLE_INVALID")
        _require(item.get("local_audio_authoritative") is True, "HOLD_WINDOWS_LOCAL_AUDIO_INVALID")
        for field in ("render", "capture"):
            endpoint = item.get(field) or {}
            _require(
                set(endpoint.get("roles") or []) == WINDOWS_AUDIO_ROLES,
                "HOLD_WINDOWS_AUDIO_ROLE_SPLIT",
            )
            _require(
                isinstance(endpoint.get("endpoint_id"), str)
                and endpoint["endpoint_id"].startswith("{0.0."),
                "HOLD_WINDOWS_AUDIO_ENDPOINT_INVALID",
            )

    msi_policy = by_id["MSI"].get("application_audio_policy") or {}
    _require(
        msi_policy.get("apple_music_local_computer") is True
        and msi_policy.get("apple_music_office_airplay_direct") is False
        and msi_policy.get("office_network_playback_via_taiji01_only") is True,
        "HOLD_MSI_APPLICATION_AUDIO_POLICY_DRIFT",
    )

    for node_ref in ("taiji04", "drallion"):
        item = by_id[node_ref]
        _require(str(item.get("state", "")).startswith("HOLD_"), "HOLD_ANDROID_AUDIO_GATE_MISSING")
        _require(item.get("selectable") is False, "HOLD_ANDROID_AUDIO_SELECTABLE_FORBIDDEN")
        _require(item.get("runtime_enabled") is False, "HOLD_ANDROID_AUDIO_RUNTIME_FORBIDDEN")

    for node_ref in ("penguin", "wuchang-us-free-node"):
        item = by_id[node_ref]
        _require(item.get("role") == "NO_USER_AUDIO_ROLE", "HOLD_COMPUTE_AUDIO_ROLE_DRIFT")
        _require(item.get("selectable") is False, "HOLD_COMPUTE_AUDIO_SELECTABLE_FORBIDDEN")

    speakers = value.get("network_speakers")
    _require(isinstance(speakers, list) and len(speakers) == 1, "HOLD_NETWORK_SPEAKER_COUNT")
    speaker = speakers[0]
    _require(
        speaker.get("device_ref") == "HOME_POD_LAN_AUDIO_NODE_OFFICE_01"
        and speaker.get("bridge_node_ref") == "taiji01"
        and speaker.get("host") == "192.168.50.101"
        and speaker.get("port") == 7000
        and speaker.get("transport") == "RAOP_AIRPLAY_AUDIO",
        "HOLD_OFFICE_HOMEPOD_ROUTE_DRIFT",
    )


def resolve_audio_target(target: str, path: Path = TOPOLOGY_PATH) -> dict[str, Any]:
    topology = load_audio_topology(path)
    by_id = {item["node_ref"]: item for item in topology["nodes"]}
    normalized = str(target).strip().upper()

    if normalized in {"OFFICE", "OFFICE_HOMEPOD", "HOMEPOD"}:
        speaker = copy.deepcopy(topology["network_speakers"][0])
        return {
            "state": "PASS_AUDIO_TARGET",
            "target_class": "NETWORK_SPEAKER",
            "bridge_node_ref": "taiji01",
            "target": speaker,
            "requires_total_field_allow": True,
        }

    node_key = {
        "MSI": "MSI",
        "TAIJI03": "taiji03",
        "TAIJI04": "taiji04",
        "DRALLION": "drallion",
        "PENGUIN": "penguin",
        "US_VM": "wuchang-us-free-node",
        "WUCHANG-US-FREE-NODE": "wuchang-us-free-node",
    }.get(normalized)
    if node_key is None:
        raise AudioTopologyHold("HOLD_AUDIO_TARGET_UNKNOWN")

    node = copy.deepcopy(by_id[node_key])
    if str(node.get("state", "")).startswith("HOLD_"):
        return {
            "state": node["state"],
            "target_class": "HELD_NODE",
            "node": node,
            "selectable": False,
        }
    if node.get("role") == "NO_USER_AUDIO_ROLE":
        return {
            "state": "BLOCK_NO_USER_AUDIO_ROLE",
            "target_class": "NON_AUDIO_NODE",
            "node": node,
            "selectable": False,
        }
    return {
        "state": "PASS_AUDIO_TARGET",
        "target_class": "LOCAL_AUDIO_NODE",
        "node": node,
        "requires_total_field_allow": False,
    }


__all__ = [
    "AudioTopologyHold",
    "load_audio_topology",
    "resolve_audio_target",
    "validate_audio_topology",
]
