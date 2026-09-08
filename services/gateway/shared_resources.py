from __future__ import annotations

import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel


ROOT = Path(__file__).resolve().parents[2]
TOPOLOGY_PATH = ROOT / "configs" / "taiji_topology.json"
RCLONE_BINARY = os.getenv("TAIJI_RCLONE_BINARY", "/usr/bin/rclone")
MAX_RESULTS = 200
SENSITIVE_NAME = re.compile(
    r"(^\.env$|credential|private[_ -]?key|service[_ -]?account|secret|token)",
    re.IGNORECASE,
)

router = APIRouter(prefix="/v1/taiji/resources", tags=["shared-resources"])


class SharedDriveListRequest(BaseModel):
    source_node: str
    drive_key: str
    path: str = ""


def _topology() -> dict[str, Any]:
    if not TOPOLOGY_PATH.is_file():
        raise HTTPException(status_code=500, detail="missing_taiji_topology")
    return json.loads(TOPOLOGY_PATH.read_text(encoding="utf-8"))


def _client_is_internal(host: str | None) -> bool:
    if not host:
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    tailscale = ipaddress.ip_network("100.64.0.0/10")
    return bool(address.is_private or address.is_loopback or address in tailscale)


def _safe_relative_path(value: str) -> str:
    value = value.strip().replace("\\", "/")
    if not value:
        return ""
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or len(value) > 500:
        raise HTTPException(status_code=422, detail="invalid_shared_drive_path")
    return path.as_posix().strip("/")


def _registered_node(topology: dict[str, Any], source_node: str) -> str:
    aliases = {
        "MSI": "msi_gpu_organ",
        "msi": "msi_gpu_organ",
        "taiji04": "taiji04_sunmi_pos",
        "sunmi": "taiji04_sunmi_pos",
    }
    node = aliases.get(source_node, source_node)
    if node not in (topology.get("nodes") or {}):
        raise HTTPException(status_code=403, detail="source_node_not_registered")
    return node


def _drive_contract(topology: dict[str, Any], drive_key: str) -> tuple[dict, str]:
    cloud = topology.get("cloud_resources") or {}
    drives = cloud.get("shared_drives") or {}
    drive = drives.get(drive_key)
    if not isinstance(drive, dict):
        raise HTTPException(status_code=404, detail="shared_drive_not_registered")
    remote = str((cloud.get("central_broker") or {}).get("runtime_remote") or "")
    if not remote.endswith(":"):
        raise HTTPException(status_code=503, detail="shared_drive_broker_not_configured")
    return drive, remote


def _rclone_lsjson(remote: str, drive_id: str, relative_path: str) -> list[dict]:
    command = [
        RCLONE_BINARY,
        "lsjson",
        remote + relative_path,
        "--drive-team-drive",
        drive_id,
        "--max-depth",
        "1",
        "--no-mimetype",
        "--no-modtime",
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(status_code=503, detail="shared_drive_broker_unavailable") from exc
    if completed.returncode != 0:
        raise HTTPException(status_code=503, detail="shared_drive_read_failed")
    try:
        items = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=503, detail="shared_drive_response_invalid") from exc
    if not isinstance(items, list):
        raise HTTPException(status_code=503, detail="shared_drive_response_invalid")
    return items


def _safe_metadata(items: list[dict]) -> tuple[list[dict], int]:
    visible: list[dict] = []
    omitted = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("Name") or item.get("Path") or "")
        if not name or SENSITIVE_NAME.search(name):
            omitted += 1
            continue
        visible.append(
            {
                "name": name,
                "path": str(item.get("Path") or name),
                "is_dir": bool(item.get("IsDir")),
                "size_bytes": int(item.get("Size") or 0),
                "id": str(item.get("ID") or ""),
            }
        )
        if len(visible) >= MAX_RESULTS:
            break
    return visible, omitted


@router.get("/shared-drives")
def shared_drive_catalog(request: Request) -> dict[str, Any]:
    if not _client_is_internal(request.client.host if request.client else None):
        raise HTTPException(status_code=403, detail="internal_or_vpn_ingress_required")
    topology = _topology()
    cloud = topology.get("cloud_resources") or {}
    drives = cloud.get("shared_drives") or {}
    return {
        "schema_id": "W7TP_8DADI_SHARED_DRIVE_CATALOG_V2_3",
        "state": "REGISTERED_SHARED_DRIVE_CATALOG",
        "broker_node": (cloud.get("central_broker") or {}).get("host"),
        "drives": [
            {
                "drive_key": key,
                "display_name": value.get("display_name"),
                "role": value.get("role") or [],
            }
            for key, value in drives.items()
            if isinstance(value, dict)
        ],
        "credentials_exposed": False,
        "cloud_is_total_field_authority": False,
        "D6_classification": "CATALOG_METADATA_IS_NOT_D6",
    }


@router.post("/shared-drives/list")
def shared_drive_list(payload: SharedDriveListRequest, request: Request) -> dict[str, Any]:
    if not _client_is_internal(request.client.host if request.client else None):
        raise HTTPException(status_code=403, detail="internal_or_vpn_ingress_required")
    topology = _topology()
    source_node = _registered_node(topology, payload.source_node)
    drive, remote = _drive_contract(topology, payload.drive_key)
    relative_path = _safe_relative_path(payload.path)
    raw_items = _rclone_lsjson(remote, str(drive["drive_id"]), relative_path)
    items, omitted = _safe_metadata(raw_items)
    return {
        "schema_id": "W7TP_8DADI_SHARED_DRIVE_METADATA_V2_3",
        "state": "OBSERVED_SHARED_DRIVE_METADATA",
        "source_node": source_node,
        "broker_node": "taiji01",
        "drive_key": payload.drive_key,
        "drive_name": drive.get("display_name"),
        "path": relative_path,
        "items": items,
        "sensitive_items_omitted": omitted,
        "credentials_exposed": False,
        "content_transferred": False,
        "carrier_order": ["LAN", "VPN_ONLY_AFTER_LAN_UNAVAILABLE"],
        "D6_classification": "METADATA_LOOKUP_IS_NOT_D6",
        "external_effect": False,
        "authority": "READ_ONLY_RESOURCE_EVIDENCE_NOT_TOTAL_FIELD",
    }


@router.get("/state/internal")
def internal_state_view(request: Request) -> dict[str, Any]:
    if not _client_is_internal(request.client.host if request.client else None):
        raise HTTPException(status_code=403, detail="internal_or_vpn_ingress_required")
    topology = _topology()
    return {
        "schema_id": "W7TP_8DADI_INTERNAL_OBSERVATION_VIEW_V2_3",
        "state": "CONFIGURED_INTERNAL_VIEW_REQUIRES_LIVE_RESOURCE_REOBSERVATION",
        "nodes": list((topology.get("nodes") or {}).keys()),
        "scenarios": list(
            ((topology.get("scenario_fields") or {}).get("scenarios") or {}).keys()
        ),
        "container_common_plane": topology.get("container_common_plane"),
        "cloud_broker": (topology.get("cloud_resources") or {}).get(
            "central_broker"
        ),
        "network_policy": topology.get("network_policy"),
        "secret_values_included": False,
        "authority": "OBSERVATION_ONLY_NOT_D8",
    }


@router.get("/state/external")
def external_state_view() -> dict[str, Any]:
    return {
        "schema_id": "W7TP_8DADI_EXTERNAL_OBSERVATION_VIEW_V2_3",
        "state": "BROWSER_INTERFACE_CONTRACT_READY",
        "human_interface": "NATURAL_LANGUAGE_AND_BROWSER",
        "shows": [
            "INTENT_UNDERSTOOD",
            "EXECUTING_NODES",
            "TRANSFER_CLASS",
            "RESULT_LOCATION",
            "RESULT_CONSISTENCY",
            "AUTHORIZATION_REF",
            "RISK_AND_UNKNOWN",
        ],
        "internal_topology_or_secret_values_exposed": False,
        "completion_requires_internal_and_external_alignment": True,
        "authority": "HUMAN_OBSERVABLE_EFFECT_VIEW_NOT_D8",
    }
