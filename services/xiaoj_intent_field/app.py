import os
from datetime import datetime, timezone
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from w7tp_gt_mesh import core
from w7tp_gt_mesh.core import MeshError, TOTAL_FIELD_AUTHORITY_REF
from w7tp_gt_mesh.journal import MeshStorage
from w7tp_gt_mesh.packet import build_transfer
from w7tp_gt_mesh.transport import MeshTransport, validate_peer_url

DEFAULT_BROWSER_ORIGINS = (
    "http://127.0.0.1:8069",
    "http://localhost:8069",
)
BROWSER_ORIGINS = tuple(
    origin.strip()
    for origin in os.environ.get(
        "XIAOJ_BROWSER_ORIGINS",
        ",".join(DEFAULT_BROWSER_ORIGINS),
    ).split(",")
    if origin.strip()
)
if not BROWSER_ORIGINS or "*" in BROWSER_ORIGINS:
    raise RuntimeError("XIAOJ_BROWSER_ORIGINS must contain exact origins and cannot use '*'")

app = FastAPI(title="XiaoJ Intent Field")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(BROWSER_ORIGINS),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
    max_age=600,
)

RUNTIME_ROOT = os.environ.get("XIAOJ_W7TP_RUNTIME_ROOT", "/app/runtime/w7tp")
TOTAL_FIELD_LAN_URL = os.environ.get(
    "XIAOJ_TOTAL_FIELD_LAN_URL",
    "http://192.168.50.249:9238/v2.1/packets",
)
TOTAL_FIELD_VPN_URL = os.environ.get(
    "XIAOJ_TOTAL_FIELD_VPN_URL",
    "http://100.71.224.18:9238/v2.1/packets",
)
FOUNDER_REF = "founder:CHIANG_CHENG_LUNG"
ROUTE_ID = "CANDIDATE_FOUNDER_INTENT_TO_W7TP_V1"
SOURCE_NODE_REF = "node:msi:xiaoj-intent-field:route-v1"


def _receiver_health_url(peer_url: str) -> str:
    parsed = urllib.parse.urlsplit(validate_peer_url(peer_url))
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "/healthz", "", ""))


def _receiver_ready(peer_url: str) -> bool:
    request = urllib.request.Request(
        _receiver_health_url(peer_url),
        method="GET",
        headers={"Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            raw = response.read(64 * 1024 + 1)
            if response.status != 200 or len(raw) > 64 * 1024:
                return False
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False
    try:
        payload = core.require_core().canonical_json_loads(raw, require_canonical=False)
    except (ValueError, TypeError, core.MeshError):
        return False
    return bool(
        isinstance(payload, dict)
        and payload.get("state") == "LIVE_SERVICE_PRESENCE_ONLY"
        and payload.get("authority_node_ref") == "node:taiji01"
        and payload.get("authority_ref") == TOTAL_FIELD_AUTHORITY_REF
        and payload.get("canonical_id") == core.CANONICAL_ID
        and payload.get("final_authority_granted") is False
    )


def _select_receiver_url(probe=None) -> tuple[str, str]:
    check = probe or _receiver_ready
    if check(TOTAL_FIELD_LAN_URL):
        return TOTAL_FIELD_LAN_URL, "LAN_PRIMARY"
    if TOTAL_FIELD_VPN_URL and TOTAL_FIELD_VPN_URL != TOTAL_FIELD_LAN_URL and check(TOTAL_FIELD_VPN_URL):
        return TOTAL_FIELD_VPN_URL, "VPN_FALLBACK_AFTER_LAN_UNAVAILABLE"
    raise HTTPException(status_code=503, detail="HOLD_TOTAL_FIELD_RECEIVER_UNAVAILABLE")


class FounderIntentPacket(BaseModel):
    intent: str = Field(min_length=1, max_length=8192)
    state_ref: str = Field(min_length=3, max_length=256)
    coordinate_ref: str = Field(min_length=3, max_length=256)
    evidence_refs: list[str] = Field(default_factory=list, max_length=32)
    execution_policy: str = Field(default="INTERNAL_EVIDENCE_ONLY", max_length=128)
    generative_target: str = Field(min_length=3, max_length=512)
    risk_state: str = Field(default="FAIL_CLOSED_NO_EXTERNAL_EFFECT", max_length=128)
    founder_ref: str = Field(default=FOUNDER_REF, max_length=128)


def _build_snapshot(request: FounderIntentPacket, logical_time: int) -> dict[str, Any]:
    if request.founder_ref != FOUNDER_REF:
        raise HTTPException(status_code=403, detail="HOLD_FOUNDER_REF_INVALID")
    if request.execution_policy != "INTERNAL_EVIDENCE_ONLY":
        raise HTTPException(status_code=409, detail="HOLD_EFFECT_SCOPE_NOT_AUTHORIZED")
    return {
        "schema_id": core.SNAPSHOT_SCHEMA,
        "intent_schema_id": "W7TP_FOUNDER_INTENT_STATE_PACKET_CANDIDATE_V1",
        "canonical_id": core.CANONICAL_ID,
        "version": core.CANONICAL_VERSION,
        "canonical_binding": core.canonical_binding(),
        "source_node_ref": SOURCE_NODE_REF,
        "logical_time": logical_time,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "route_id": ROUTE_ID,
        "D1_INTENT": {"founder_ref": request.founder_ref, "intent": request.intent},
        "D2_STATE": {"state_ref": request.state_ref},
        "D3_COORDINATE": {"coordinate_ref": request.coordinate_ref},
        "D4_EVIDENCE": {"refs": request.evidence_refs},
        "D5_EXECUTION": {"policy": request.execution_policy, "external_effect": False},
        "D6_GENERATIVE_TRANSMISSION": {
            "target": request.generative_target,
            "receiver_local_reconstruction_required": True,
        },
        "D7_RISK_QUARANTINE": {"state": request.risk_state, "fail_closed": True},
        "D8_ENVELOPE_VERIFICATION": {
            "authority_ref": TOTAL_FIELD_AUTHORITY_REF,
            "founder_ref": request.founder_ref,
            "authority_state": "FOUNDER_AUTHORIZED_CANDIDATE_ROUTE",
            "final_authority_granted": False,
        },
    }

@app.get("/healthz")
def healthz():
    return {"ok": True, "service": "xiaoj-intent-field"}

@app.get("/state")
def state():
    return {
        "intent_field_loaded": True,
        "memory_field_loaded": True,
        "topology_field_loaded": True,
        "policy_gate_active": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/intent-field/status")
def status():
    return {
        "service_name": "xiaoj-intent-field",
        "mode": "containerized_intent_field",
        "governance": "local_first_human_reviewed",
        "hardwalls_enabled": True,
        "cloud_allowed": False,
        "pii_allowed": False,
        "secrets_allowed": False,
        "founder_intent_route": ROUTE_ID,
        "founder_intent_route_state": "CANDIDATE_WIRED_INTERNAL_EVIDENCE_ONLY",
        "receiver_route_policy": "LAN_PRIMARY_VPN_FALLBACK",
        "queue_on_failure": False,
    }


@app.post("/v1/founder-intents")
def submit_founder_intent(request: FounderIntentPacket):
    try:
        peer_url, route_used = _select_receiver_url()
        with MeshStorage(RUNTIME_ROOT) as storage:
            logical_time = storage.journal.next_logical_time(SOURCE_NODE_REF)
            snapshot = _build_snapshot(request, logical_time)
            transfer = build_transfer(
                storage,
                snapshot,
                authority_ref=TOTAL_FIELD_AUTHORITY_REF,
                namespace="w7tp.founder_intent.candidate.v1",
                ttl_seconds=300,
            )
            receipt = MeshTransport(storage).send(
                transfer.carrier,
                carrier_ref=transfer.carrier_ref,
                peer_url=peer_url,
                queue_on_failure=False,
            )
            if receipt.get("delivery_state") != "PASS_RECEIVED":
                reason = str(receipt.get("reason_code") or receipt.get("state") or "HOLD_RECEIVER_REJECTED")
                raise HTTPException(status_code=409, detail=reason)
    except MeshError as exc:
        raise HTTPException(status_code=409, detail=exc.code) from exc
    return {
        "state": "PASS_FOUNDER_INTENT_RECEIVED_CANDIDATE_ONLY",
        "route_id": ROUTE_ID,
        "intent_packet_ref": transfer.packet_ref,
        "target_snapshot_ref": transfer.target_snapshot_ref,
        "transfer_mode": transfer.transfer_mode,
        "route_used": route_used,
        "receipt": receipt,
        "canonical_promoted": False,
        "final_authority_granted": False,
    }
