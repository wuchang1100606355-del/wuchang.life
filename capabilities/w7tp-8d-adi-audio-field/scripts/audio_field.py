#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
TOPOLOGY_PATH = ROOT / "configs/total_field/w7tp_all_node_audio_topology_v1.json"
SIRI_CONTRACT_PATH = ROOT / "configs/total_field/w7tp_siri_audio_trigger_contract_v1.json"
VOLUME_EVIDENCE_PATH = ROOT / "configs/total_field/w7tp_audio_volume_capability_evidence_v1.json"
NAHIMIC_EVIDENCE_PATH = ROOT / "configs/total_field/w7tp_nahimic_capability_evidence_v1.json"

LEVEL_OPERATIONS = {
    "SET_OUTPUT_VOLUME",
    "SET_INPUT_GAIN",
    "GROUP_SET_VOLUME",
}

OUTPUT_OPERATIONS = {
    "OUTPUT_OPEN",
    "OUTPUT_CLOSE",
    "SET_OUTPUT_VOLUME",
    "MUTE_OUTPUT",
    "UNMUTE_OUTPUT",
    "GROUP_SET_VOLUME",
    "GROUP_OPEN",
    "GROUP_CLOSE",
}

SUPPORTED_OPERATIONS = OUTPUT_OPERATIONS | {"SET_INPUT_GAIN", "STATUS"}

TARGETS = {
    "MSI": {"node": "MSI", "kind": "OUTPUT", "backend": "WINDOWS_CORE_AUDIO"},
    "TAIJI03": {"node": "taiji03", "kind": "OUTPUT", "backend": "WINDOWS_CORE_AUDIO"},
    "OFFICE": {"node": "OFFICE_HOMEPOD", "kind": "OUTPUT", "backend": "PYATV_RAOP"},
    "MSI_MIC": {"node": "MSI", "kind": "INPUT", "backend": "WINDOWS_CORE_AUDIO"},
    "TAIJI03_MIC": {"node": "taiji03", "kind": "INPUT", "backend": "WINDOWS_CORE_AUDIO"},
}

GROUPS = {
    "ALL_OUTPUTS": ["MSI", "TAIJI03", "OFFICE"],
}


class AudioFieldHold(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AudioFieldHold("HOLD_AUDIO_FIELD_SOURCE_READ_FAILED") from exc
    if not isinstance(value, dict):
        raise AudioFieldHold("HOLD_AUDIO_FIELD_SOURCE_SHAPE_INVALID")
    return value


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise AudioFieldHold(code)


def load_contracts() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    topology = _load(TOPOLOGY_PATH)
    siri = _load(SIRI_CONTRACT_PATH)
    volume = _load(VOLUME_EVIDENCE_PATH)
    _require(
        siri.get("schema_version") == "W7TP-SIRI-AUDIO-TRIGGER/1.0",
        "HOLD_SIRI_CONTRACT_VERSION",
    )
    _require(
        volume.get("schema_version") == "W7TP-AUDIO-VOLUME-CAPABILITY-EVIDENCE/1.0",
        "HOLD_VOLUME_EVIDENCE_VERSION",
    )
    return topology, siri, volume


def resolve_alias(target_ref: str, siri: dict[str, Any]) -> str:
    raw = str(target_ref).strip()
    if raw in TARGETS or raw in GROUPS:
        return raw
    aliases = siri.get("target_aliases") or {}
    resolved = aliases.get(raw)
    if resolved in TARGETS or resolved in GROUPS:
        return resolved
    raise AudioFieldHold("HOLD_AUDIO_TARGET_UNKNOWN")


def _control_evidence(target_ref: str, volume: dict[str, Any]) -> dict[str, Any]:
    nodes = volume.get("nodes") or {}
    if target_ref == "OFFICE":
        return copy.deepcopy(nodes.get("OFFICE_HOMEPOD") or {})
    target = TARGETS[target_ref]
    node = nodes.get(target["node"]) or {}
    key = "default_output" if target["kind"] == "OUTPUT" else "default_input"
    return copy.deepcopy(node.get(key) or {})


def _volume_gate(target_ref: str, volume: dict[str, Any]) -> dict[str, Any]:
    evidence = _control_evidence(target_ref, volume)
    _require(bool(evidence), "HOLD_VOLUME_CONTROL_EVIDENCE_MISSING")
    _require(evidence.get("read_control") is True, "HOLD_VOLUME_READ_UNPROVEN")
    _require(evidence.get("write_api_present") is True, "HOLD_VOLUME_WRITE_UNPROVEN")
    _require(evidence.get("readback_api_present") is True, "HOLD_VOLUME_READBACK_UNPROVEN")
    return evidence


def validate_intent(intent: dict[str, Any], siri: dict[str, Any]) -> dict[str, Any]:
    required = {"request_id", "trigger_type", "target_ref", "operation", "issued_at", "nonce"}
    _require(required <= set(intent), "HOLD_AUDIO_INTENT_REQUIRED_FIELD_MISSING")
    op = str(intent["operation"])
    _require(op in SUPPORTED_OPERATIONS, "HOLD_AUDIO_OPERATION_UNSUPPORTED")
    _require(
        intent["trigger_type"] in {"SIRI_SHORTCUT", "APP_INTENT", "LOCAL_UI", "TOTAL_FIELD_INTERNAL"},
        "HOLD_AUDIO_TRIGGER_TYPE_INVALID",
    )
    nonce = str(intent["nonce"])
    _require(8 <= len(nonce) <= 128, "HOLD_AUDIO_NONCE_INVALID")
    target = resolve_alias(str(intent["target_ref"]), siri)
    level = intent.get("level")
    if op in LEVEL_OPERATIONS:
        _require(isinstance(level, int) and not isinstance(level, bool), "HOLD_AUDIO_LEVEL_REQUIRED")
        _require(0 <= level <= 100, "HOLD_AUDIO_LEVEL_OUT_OF_RANGE")
    elif level is not None:
        _require(isinstance(level, int) and not isinstance(level, bool), "HOLD_AUDIO_LEVEL_INVALID")
        _require(0 <= level <= 100, "HOLD_AUDIO_LEVEL_OUT_OF_RANGE")

    if op == "SET_INPUT_GAIN":
        _require(target in {"MSI_MIC", "TAIJI03_MIC"}, "HOLD_INPUT_GAIN_TARGET_INVALID")
    if op in OUTPUT_OPERATIONS and target in {"MSI_MIC", "TAIJI03_MIC"}:
        raise AudioFieldHold("HOLD_OUTPUT_OPERATION_TARGETS_INPUT")
    return {"target": target, "operation": op, "level": level}


def _effect_for_target(target_ref: str, operation: str, level: int | None, evidence: dict[str, Any]) -> dict[str, Any]:
    target = TARGETS[target_ref]
    common = {
        "target_ref": target_ref,
        "node_ref": target["node"],
        "direction": target["kind"],
        "backend": target["backend"],
        "requires_total_field_allow": True,
        "volume_control_gate": "PASS",
        "rollback_preimage_required": True,
        "readback_verification_required": True,
    }
    if operation == "OUTPUT_CLOSE":
        common["effect"] = {
            "route_selectable": False,
            "mute": True,
            "preserve_last_nonzero_level": True,
            "driver_disable": False,
        }
    elif operation == "OUTPUT_OPEN":
        common["effect"] = {
            "route_selectable": True,
            "mute": False,
            "restore_last_valid_level": True,
            "driver_enable_change": False,
        }
    elif operation in {"MUTE_OUTPUT", "UNMUTE_OUTPUT"}:
        common["effect"] = {"mute": operation == "MUTE_OUTPUT"}
    elif operation in {"SET_OUTPUT_VOLUME", "SET_INPUT_GAIN"}:
        common["effect"] = {
            "normalized_level": level,
            "normalized_range": [0, 100],
            "control_kind": "OUTPUT_VOLUME" if operation == "SET_OUTPUT_VOLUME" else "INPUT_GAIN",
        }
    elif operation == "STATUS":
        common["effect"] = {"read_only": True}
        common["requires_total_field_allow"] = False
    else:
        raise AudioFieldHold("HOLD_AUDIO_EFFECT_MAPPING_MISSING")
    common["control_evidence"] = evidence
    return common


def build_candidate(intent: dict[str, Any]) -> dict[str, Any]:
    topology, siri, volume = load_contracts()
    validated = validate_intent(intent, siri)
    target = validated["target"]
    op = validated["operation"]
    level = validated["level"]

    if target in GROUPS:
        members = GROUPS[target]
        if op == "GROUP_SET_VOLUME":
            member_op = "SET_OUTPUT_VOLUME"
        elif op == "GROUP_OPEN":
            member_op = "OUTPUT_OPEN"
        elif op == "GROUP_CLOSE":
            member_op = "OUTPUT_CLOSE"
        elif op == "STATUS":
            member_op = "STATUS"
        elif op in {"MUTE_OUTPUT", "UNMUTE_OUTPUT"}:
            member_op = op
        else:
            raise AudioFieldHold("HOLD_GROUP_OPERATION_INVALID")
        plans = []
        for member in members:
            evidence = _volume_gate(member, volume)
            plans.append(_effect_for_target(member, member_op, level, evidence))
    else:
        evidence = _volume_gate(target, volume)
        plans = [_effect_for_target(target, op, level, evidence)]

    risks = []
    for node_name, node in (volume.get("nodes") or {}).items():
        for key in ("local_output", "local_input"):
            endpoint = (node or {}).get(key) or {}
            if endpoint.get("risk") == "BACKEND_GAIN_OVER_NORMALIZED_100":
                risks.append({
                    "node_ref": node_name,
                    "endpoint_ref": endpoint.get("endpoint_id"),
                    "risk": "BACKEND_GAIN_OVER_NORMALIZED_100",
                    "selectable": endpoint.get("selectable", False),
                })

    return {
        "state": "PASS_AUDIO_EFFECT_CANDIDATE",
        "execution_allowed": False,
        "candidate_only": True,
        "D1": {
            "intent": op,
            "target_ref": target,
            "requested_level": level,
            "trigger_type": intent["trigger_type"],
        },
        "D2": {
            "state": "CANDIDATE_PLAN_ONLY",
            "endpoint_count": len(plans),
        },
        "D3": {
            "plans": plans,
        },
        "D4": {
            "volume_capability_evidence_ref": str(VOLUME_EVIDENCE_PATH.relative_to(ROOT)),
            "nahimic_capability_evidence_ref": str(NAHIMIC_EVIDENCE_PATH.relative_to(ROOT)),
            "audio_topology_ref": str(TOPOLOGY_PATH.relative_to(ROOT)),
            "siri_contract_ref": str(SIRI_CONTRACT_PATH.relative_to(ROOT)),
        },
        "D5": {
            "normalized_level_range": [0, 100],
            "all_selectable_ingress_egress_require_volume_gain_control": True,
            "output_close_semantics": "ROUTE_REMOVE_PLUS_MUTE_PRESERVE_LEVEL",
            "output_open_semantics": "ROUTE_ENABLE_PLUS_UNMUTE_RESTORE_LEVEL",
        },
        "D6": {
            "raw_audio_transfer_implied": False,
            "state_control_reference_only": True,
        },
        "D7": {
            "risks": risks,
            "hidden_partial_group_success_forbidden": True,
        },
        "D8": {
            "siri_is_authority": False,
            "provider_is_authority": False,
            "total_field_effect_decision_required": any(
                plan["requires_total_field_allow"] for plan in plans
            ),
        },
    }


__all__ = [
    "AudioFieldHold",
    "build_candidate",
    "load_contracts",
    "resolve_alias",
    "validate_intent",
]
