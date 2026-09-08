from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


ROOT = Path(__file__).resolve().parents[2]
TOPOLOGY_PATH = ROOT / "configs" / "taiji_topology.json"

router = APIRouter(prefix="/taiji", tags=["taiji-topology"])


class RouteRequest(BaseModel):
    task_class: str
    action: str
    payload_summary: str = ""
    authority_level: int = 1
    human_online: bool = False
    preferred_node: str | None = None


def load_topology() -> dict:
    if not TOPOLOGY_PATH.is_file():
        raise HTTPException(status_code=500, detail="missing_taiji_topology")
    return json.loads(TOPOLOGY_PATH.read_text(encoding="utf-8"))


@router.get("/topology")
def topology() -> dict:
    data = load_topology()
    return {
        "version": data.get("version"),
        "primary_decision_engine": data.get("primary_decision_engine"),
        "network_policy": data.get("network_policy"),
        "common_domain_plane": data.get("common_domain_plane"),
        "total_field_hardware_orchestration": data.get(
            "total_field_hardware_orchestration"
        ),
        "distributed_resource_field": data.get("distributed_resource_field"),
        "odoo_capability_plane": data.get("odoo_capability_plane"),
        "container_common_plane": data.get("container_common_plane"),
        "scenario_fields": data.get("scenario_fields"),
        "observation_views": data.get("observation_views"),
        "nodes": data.get("nodes"),
        "services": data.get("services"),
        "cloud_resources": data.get("cloud_resources"),
        "secret_values_included": False,
        "authority": "OBSERVATION_ONLY_NOT_D8",
    }


@router.get("/topology/summary")
def topology_summary() -> dict:
    data = load_topology()
    return {
        "version": data.get("version"),
        "primary_decision_engine": data.get("primary_decision_engine"),
        "network_policy": data.get("network_policy", {}),
        "domain": (data.get("common_domain_plane") or {}).get("domain"),
        "domain_owner_scene": (data.get("common_domain_plane") or {}).get(
            "owner_scene"
        ),
        "layers": list((data.get("layers") or {}).keys()),
        "nodes": list((data.get("nodes") or {}).keys()),
        "scenarios": list(
            ((data.get("scenario_fields") or {}).get("scenarios") or {}).keys()
        ),
        "shared_drives": list(
            ((data.get("cloud_resources") or {}).get("shared_drives") or {}).keys()
        ),
        "container_common": bool(
            (data.get("container_common_plane") or {}).get(
                "all_registered_nodes_share_capability_namespace"
            )
        ),
        "hardware_orchestration": bool(
            (data.get("total_field_hardware_orchestration") or {}).get(
                "controller"
            )
            == "TOTAL_FIELD"
        ),
        "distributed_resource_aggregation": (
            (data.get("distributed_resource_field") or {}).get(
                "aggregation_mode"
            )
        ),
        "odoo_is_primary_application_capability_plane": (
            (data.get("odoo_capability_plane") or {}).get("role")
            == "PRIMARY_SYSTEM_DESCRIPTION_AND_APPLICATION_CAPABILITY_ARCHITECTURE"
        ),
        "authority": "OBSERVATION_ONLY_NOT_D8",
    }


def _route_for_task(task_class: str) -> str:
    mapping = {
        "local_llm": "msi_gpu_organ",
        "audiovisual_generation": "msi_gpu_organ",
        "chat": "openwebui",
        "ui": "openwebui",
        "property_case": "odoo",
        "pos": "taiji04_sunmi_pos",
        "finance_record": "odoo",
        "vision": "store_lilin_nvr",
        "security_video": "store_lilin_nvr",
        "camera_event": "store_lilin_nvr",
        "hearing": "taiji04_sunmi_pos",
        "speech_input": "taiji04_sunmi_pos",
        "voice_intent": "taiji04_sunmi_pos",
        "speech_output": "homepod_pair",
        "airplay_output": "homepod_pair",
        "heartbeat": "sensor",
        "sensing": "sensor",
        "environment_state": "sensor",
        "cloud_shared_drive": "taiji01",
        "dynamic_context": "taiji01",
        "total_field": "taiji01",
    }
    return mapping.get(task_class, "taiji01")


@router.post("/route/decide")
def route_decide(request: RouteRequest) -> dict:
    topology = load_topology()
    if request.action in (topology.get("hard_denies") or []):
        raise HTTPException(status_code=403, detail="hard_denied_action")
    nodes = topology.get("nodes") or {}
    selected = request.preferred_node or _route_for_task(request.task_class)
    if selected not in nodes:
        raise HTTPException(status_code=404, detail="registered_node_not_found")
    if request.authority_level > int(nodes[selected].get("max_authority_level", 0)):
        raise HTTPException(status_code=403, detail="authority_level_exceeds_node")
    return {
        "state": "8DADI_ROUTE_PROPOSAL_NO_EFFECT",
        "task_class": request.task_class,
        "action": request.action,
        "selected_node": selected,
        "authority_level_requested": request.authority_level,
        "carrier_order": ["LAN", "VPN_ONLY_AFTER_LAN_UNAVAILABLE"],
        "ledger_write": False,
        "execution_authorized": False,
        "requires_total_field_effect_decision": True,
    }
