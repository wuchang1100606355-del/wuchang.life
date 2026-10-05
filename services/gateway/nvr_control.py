from __future__ import annotations

import json
import re
import runpy
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "configs/total_field/w7tp_nvr_read_control_v1.json"
EFFECT_GATE_PATH = PROJECT_ROOT / "capabilities/w7tp-deterministic-effect-gate/scripts/effect_gate.py"
router = APIRouter(prefix="/api/taiji/nvr", tags=["8D ADI NVR Read Control"])

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class NvrReadPlanRequest(BaseModel):
    task_id: str = Field(default="T-024", min_length=1, max_length=128)
    camera_ref: str = Field(default="CAM01", min_length=1, max_length=32)
    operation: str = Field(default="SNAPSHOT", pattern="^(STATUS|SNAPSHOT)$")
    context_ref: str = Field(min_length=1, max_length=512)
    origin_packet_ref: str = Field(min_length=1, max_length=512)


class NvrReceiptRequest(BaseModel):
    task_id: str = Field(default="T-024", min_length=1, max_length=128)
    context_ref: str = Field(min_length=1, max_length=512)
    receipt: dict[str, Any]


def _config() -> dict[str, Any]:
    try:
        value = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail="HOLD_NVR_CONTROL_CONFIG_UNREADABLE") from exc
    if not isinstance(value, dict) or value.get("schema_version") != "W7TP-NVR-READ-CONTROL/1.0":
        raise HTTPException(status_code=503, detail="HOLD_NVR_CONTROL_CONFIG_INVALID")
    return value


def _read_only_effect_gate() -> dict[str, Any]:
    try:
        namespace = runpy.run_path(str(EFFECT_GATE_PATH))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="HOLD_EFFECT_GATE_UNAVAILABLE") from exc
    no_d8 = namespace.get("NO_D8")
    if not isinstance(no_d8, set) or "READ_ONLY" not in no_d8:
        raise HTTPException(status_code=409, detail="HOLD_EFFECT_GATE_READ_ONLY_DRIFT")
    return {
        "state": "ALLOW_READ_ONLY_EXTERNAL_OBSERVATION",
        "effect_class": "READ_ONLY",
        "d8_required": False,
        "effect_authority": False,
        "mutation": False,
        "gate_ref": "capability:w7tp:deterministic-effect-gate",
    }


def build_nvr_read_plan(req: NvrReadPlanRequest) -> dict[str, Any]:
    cfg = _config()
    camera = cfg.get("camera_map", {}).get(req.camera_ref)
    if req.operation == "SNAPSHOT" and not isinstance(camera, dict):
        raise HTTPException(status_code=400, detail="HOLD_NVR_CAMERA_REF_UNKNOWN")

    gate = _read_only_effect_gate()
    if gate.get("mutation") is not False or gate.get("effect_authority") is not False:
        raise HTTPException(status_code=409, detail="HOLD_NVR_READ_GATE_ESCALATION")

    adapter_input: dict[str, Any] = {"command": req.operation.lower()}
    if req.operation == "SNAPSHOT":
        adapter_input["channel_index"] = int(camera["channel_index"])
        adapter_input["camera_ref"] = req.camera_ref

    return {
        "state": "READY_NVR_READ_COMPATIBILITY_TRANSPORT",
        "task_ref": f"task:{req.task_id}",
        "context_ref": req.context_ref,
        "origin_packet_ref": req.origin_packet_ref,
        "joint_state_field": {
            "D1": {
                "intent": "READ_CURRENT_NVR_STATE_OR_FRAME",
                "operation": req.operation,
                "camera_ref": req.camera_ref if req.operation == "SNAPSHOT" else None,
            },
            "D2": {
                "control_state": cfg["state"],
                "native_transport_bound": False,
                "credential_binding_state": "MSI_LOCAL_RUNTIME_OBSERVED_AT_EXECUTION",
            },
            "D3": {
                "authority_node": "taiji01",
                "adapter_node_ref": cfg["adapter_node_ref"],
                "adapter_service_ref": cfg["adapter_service_ref"],
                "device_ref": cfg["device_ref"],
                "camera_mapping_state": camera.get("mapping_state") if isinstance(camera, dict) else None,
            },
            "D4": {
                "acceptance": (
                    "EXACT_RECEIPT_HASH_AND_CAMERA_REF_REQUIRED"
                    if req.operation == "SNAPSHOT"
                    else "EXACT_CURRENT_STATUS_RECEIPT_REQUIRED"
                )
            },
            "D5": {
                "mode": "READ_ONLY",
                "external_effect_gate": gate,
                "transport": "COMPATIBILITY_RDC",
                "adapter_input": adapter_input,
            },
            "D6": {
                "context_ref": req.context_ref,
                "origin_packet_ref": req.origin_packet_ref,
                "raw_frame_is_not_gst_payload": True,
            },
            "D7": {
                "fail_closed": True,
                "credential_plaintext_forbidden_outside_msi": True,
                "mutation_forbidden": True,
                "native_transport_gap_localized": True,
            },
            "D8": {
                "formal_effect_authority": "LOCAL_TOTAL_FIELD",
                "provider_authority": False,
                "read_creates_effect_authority": False,
                "mutation_authority": False,
            },
        },
        "dispatch": {
            "mode": "COMPATIBILITY_RDC",
            "device_ref": cfg["adapter_node_ref"],
            "service_ref": cfg["adapter_service_ref"],
            "source_tool": "start_process",
            "adapter_ref": "tools/msi_nvr_read_adapter.py",
            "input": adapter_input,
            "source_runtime_dependency": True,
        },
    }


def validate_nvr_receipt(req: NvrReceiptRequest) -> dict[str, Any]:
    cfg = _config()
    receipt = dict(req.receipt)
    state = receipt.get("state")
    if receipt.get("device_ref") != cfg["device_ref"]:
        raise HTTPException(status_code=409, detail="HOLD_NVR_RECEIPT_DEVICE_MISMATCH")
    if receipt.get("service_ref") != cfg["adapter_service_ref"]:
        raise HTTPException(status_code=409, detail="HOLD_NVR_RECEIPT_SERVICE_MISMATCH")
    if receipt.get("node_ref") != cfg["adapter_node_ref"]:
        raise HTTPException(status_code=409, detail="HOLD_NVR_RECEIPT_NODE_MISMATCH")
    if receipt.get("credentials_output") is not False:
        raise HTTPException(status_code=409, detail="HOLD_NVR_RECEIPT_CREDENTIAL_POLICY")
    if receipt.get("mutation_performed") is not False:
        raise HTTPException(status_code=409, detail="HOLD_NVR_RECEIPT_MUTATION_FORBIDDEN")

    if state == "PASS_NVR_SNAPSHOT_ACQUIRED":
        camera_ref = receipt.get("camera_ref")
        camera = cfg.get("camera_map", {}).get(camera_ref)
        if not isinstance(camera, dict):
            raise HTTPException(status_code=409, detail="HOLD_NVR_RECEIPT_CAMERA_UNKNOWN")
        if receipt.get("channel_index") != camera.get("channel_index"):
            raise HTTPException(status_code=409, detail="HOLD_NVR_RECEIPT_CAMERA_COORDINATE_MISMATCH")
        if not SHA256_RE.fullmatch(str(receipt.get("sha256", ""))):
            raise HTTPException(status_code=409, detail="HOLD_NVR_RECEIPT_HASH_INVALID")
        if not isinstance(receipt.get("bytes"), int) or receipt["bytes"] <= 0:
            raise HTTPException(status_code=409, detail="HOLD_NVR_RECEIPT_SIZE_INVALID")
        acceptance = "PASS_REAL_JPEG_RECEIPT_ACCEPTED"
    elif state == "PASS_NVR_READ_ADAPTER_REACHABLE":
        rtsp = receipt.get("rtsp")
        if not isinstance(rtsp, dict) or rtsp.get("reachable") is not True:
            raise HTTPException(status_code=409, detail="HOLD_NVR_RECEIPT_STATUS_INVALID")
        acceptance = "PASS_CURRENT_NVR_REACHABILITY_RECEIPT_ACCEPTED"
    else:
        raise HTTPException(status_code=409, detail="HOLD_NVR_RECEIPT_STATE_NOT_ACCEPTABLE")

    return {
        "state": acceptance,
        "task_ref": f"task:{req.task_id}",
        "context_ref": req.context_ref,
        "device_ref": cfg["device_ref"],
        "service_ref": cfg["adapter_service_ref"],
        "receipt_state": state,
        "effect_authority_created": False,
        "mutation_accepted": False,
    }


@router.get("/status")
def status():
    cfg = _config()
    return {
        "state": cfg["state"],
        "device_ref": cfg["device_ref"],
        "adapter_service_ref": cfg["adapter_service_ref"],
        "adapter_node_ref": cfg["adapter_node_ref"],
        "transport": cfg["transport"],
        "credential_policy": {
            "location": cfg["credential_policy"]["location"],
            "credential_body_to_model": False,
            "credential_body_to_total_field": False,
        },
    }


@router.post("/plan")
def plan(req: NvrReadPlanRequest):
    return build_nvr_read_plan(req)


@router.post("/verify-receipt")
def verify_receipt(req: NvrReceiptRequest):
    return validate_nvr_receipt(req)
