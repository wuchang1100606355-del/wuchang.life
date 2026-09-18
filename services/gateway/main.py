from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException

from services.gateway.authority_ingress import (
    AUTHORITY_MODE,
    CandidateIngressRuntime,
    build_candidate_ingress_runtime,
)
from services.gateway.openai_compat import _complete_chat
from services.gateway.openai_compat import router as openai_compat_router
from services.gateway.shared_resources import router as shared_resources_router
from services.gateway.topology_router import router as taiji_topology_router
from tools.total_field_dynamic_context import (
    ACTIVE_TOTAL_FIELD_AUTHORITY_LOOKUP_REF,
    build_dynamic_context,
)


PROJECT_ROOT = Path(
    os.getenv("TAIJI_PROJECT_ROOT", "/home/taiji_admin/Taiji_Hub")
).resolve()
CONTEXT_IDENTITY_CLASS = os.getenv(
    "TAIJI_CONTEXT_IDENTITY_CLASS", "unknown"
).strip().lower()
if CONTEXT_IDENTITY_CLASS not in {"founder", "general_member", "unknown"}:
    CONTEXT_IDENTITY_CLASS = "unknown"

app = FastAPI(title="W7TP 8DADI Total Field Organ Gateway", version="2.3.0")
app.state.candidate_ingress_runtime = None
app.state.candidate_ingress_state = "NOT_BOUND"
app.state.candidate_ingress_reason = None


@app.on_event("startup")
def bind_candidate_ingress() -> None:
    try:
        runtime = build_candidate_ingress_runtime(PROJECT_ROOT)
    except Exception as exc:
        app.state.candidate_ingress_runtime = None
        app.state.candidate_ingress_state = "HOLD_CANDIDATE_INGRESS_NOT_BOUND"
        app.state.candidate_ingress_reason = type(exc).__name__
        return
    app.state.candidate_ingress_runtime = runtime
    app.state.candidate_ingress_state = "BOUND_FAIL_CLOSED"
    app.state.candidate_ingress_reason = None


@app.on_event("shutdown")
def close_candidate_ingress() -> None:
    runtime = getattr(app.state, "candidate_ingress_runtime", None)
    if isinstance(runtime, CandidateIngressRuntime):
        runtime.close()
    app.state.candidate_ingress_runtime = None
    app.state.candidate_ingress_state = "CLOSED"


def _intent(payload: dict[str, Any]) -> str:
    return str(
        payload.get("prompt")
        or payload.get("text")
        or payload.get("utterance")
        or ""
    ).strip()


def _context_projection(intent: str) -> dict[str, Any]:
    if not intent:
        raise HTTPException(status_code=422, detail="natural_language_intent_required")
    context = build_dynamic_context(
        root=PROJECT_ROOT,
        query=intent,
        max_items=4,
        identity_class=CONTEXT_IDENTITY_CLASS,
    )
    policy = context.get("policy") or {}
    if (
        context.get("state") != "TOTAL_FIELD_DYNAMIC_CONTEXT_READY"
        or context.get("retrieval_method") != "8DADI_MEMORY_INDEX_ONLY"
        or policy.get("8dadi_index_only") is not True
        or policy.get("workspace_search") is not False
    ):
        raise HTTPException(status_code=503, detail="HOLD_8DADI_CONTEXT_NOT_READY")
    return {
        "state": "8DADI_CONTEXT_RESOLVED_NO_EFFECT",
        "packet_sha256": context.get("packet_sha256"),
        "retrieval_method": context.get("retrieval_method"),
        "identity_class": CONTEXT_IDENTITY_CLASS,
        "founder_intent_projection_present": bool(
            context.get("founder_intent_projection")
        ),
        "context_evidence_count": len(context.get("context_items") or []),
        "model_is_authority": False,
        "execution_authorized": False,
    }


@app.get("/health")
@app.get("/healthz")
def health() -> dict[str, Any]:
    runtime = getattr(app.state, "candidate_ingress_runtime", None)
    verifier_state = (
        runtime.compatibility_signature_verifier_state
        if isinstance(runtime, CandidateIngressRuntime)
        else "NOT_BOUND"
    )
    return {
        "state": "PASS_GATEWAY_PROCESS",
        "service": "w7tp-8dadi-total-field-organ-gateway",
        "version": "2.3.0",
        "role": "PASSIVE_MODEL_RESOURCE_AND_PERCEPTION_ORGAN",
        "primary_decision_engine": "8D_ADI",
        "total_field_is_final_effect_authority": True,
        "lan_precedes_vpn": True,
        "context_identity_class": CONTEXT_IDENTITY_CLASS,
        "candidate_ingress_state": getattr(
            app.state, "candidate_ingress_state", "NOT_BOUND"
        ),
        "candidate_ingress_authority_mode": AUTHORITY_MODE,
        "candidate_ingress_compatibility_verifier_state": verifier_state,
        "candidate_ingress_execution_authorized": False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/taiji/plan")
def plan_get() -> dict[str, Any]:
    return {
        "state": "READY_FOR_NATURAL_LANGUAGE_INTENT",
        "method": "POST",
        "effect": "NONE",
    }


@app.post("/api/taiji/plan")
def plan(payload: dict[str, Any]) -> dict[str, Any]:
    return _context_projection(_intent(payload))


@app.post("/api/taiji/candidate")
def receive_candidate(payload: dict[str, Any]) -> dict[str, Any]:
    forbidden_top_level = {
        "authority_ref",
        "authority_lookup_ref",
        "verified_authority_ref",
        "d8_decision_ref",
    }
    if forbidden_top_level.intersection(payload):
        raise HTTPException(status_code=422, detail="caller_authority_fields_forbidden")

    candidate = payload.get("candidate_packet")
    context = payload.get("dynamic_context_packet")
    if not isinstance(candidate, dict):
        raise HTTPException(status_code=422, detail="candidate_packet_required")
    if not isinstance(context, dict):
        raise HTTPException(status_code=422, detail="dynamic_context_packet_required")

    runtime = getattr(app.state, "candidate_ingress_runtime", None)
    if not isinstance(runtime, CandidateIngressRuntime):
        raise HTTPException(
            status_code=503,
            detail=getattr(
                app.state,
                "candidate_ingress_state",
                "HOLD_CANDIDATE_INGRESS_NOT_BOUND",
            ),
        )

    result = runtime.receiver(
        candidate,
        context,
        ACTIVE_TOTAL_FIELD_AUTHORITY_LOOKUP_REF,
    )
    result["gateway_ingress"] = {
        "state": "BOUND_FAIL_CLOSED",
        "authority_mode": runtime.authority_mode,
        "caller_authority_injection": False,
        "execution_authorized": False,
        "total_field_is_final_effect_authority": True,
    }
    return result


@app.post("/api/taiji/execute")
def execute(payload: dict[str, Any]) -> dict[str, Any]:
    intent = _intent(payload)
    if not intent:
        raise HTTPException(status_code=422, detail="natural_language_intent_required")
    body = dict(payload)
    body.setdefault("model", os.getenv("TAIJI_MODEL", "xiaoj:latest"))
    body.setdefault("messages", [{"role": "user", "content": intent}])
    body["stream"] = False
    result = _complete_chat(body)
    result["taiji"]["requested_route"] = "MODEL_CANDIDATE_ONLY"
    result["taiji"]["external_effect_executed"] = False
    return result


@app.post("/api/taiji/voice")
def voice(payload: dict[str, Any]) -> dict[str, Any]:
    body = dict(payload)
    body["prompt"] = _intent(payload)
    body["source"] = "voice_transcript"
    return execute(body)


app.include_router(taiji_topology_router)
app.include_router(shared_resources_router)
app.include_router(openai_compat_router)
