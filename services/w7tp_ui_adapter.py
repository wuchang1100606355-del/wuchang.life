from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

from services.w7tp_d6_linter import lint_w7tp_request
from services.w7tp_evidence_ledger import commit_evidence
from services.w7tp_state_hash import canonical_hash, state_seal
from services.w7tp_ui_models import (
    EvidenceCommitIn,
    EvidenceCommitOut,
    HashSealIn,
    HashSealOut,
    IntentCompileIn,
    IntentCompileOut,
    SecurityLintIn,
    SecurityLintOut,
    StateTransitionIn,
    StateTransitionOut,
)


router = APIRouter(prefix="/api/w7tp", tags=["w7tp-ui"])


def _action(intent: str) -> str:
    text = intent.lower()
    if any(k in text for k in ("delete", "remove", "erase", "del")):
        return "DELETE_DEL"
    if any(k in text for k in ("update", "patch", "modify", "put")):
        return "UPDATE_PUT"
    if any(k in text for k in ("create", "post", "commit", "write")):
        return "CREATE_POST"
    return "READ_GET"


def _route(intent: str) -> str:
    text = intent.lower()
    if "odoo" in text:
        return "ODOO_ADAPTER"
    if "openwebui" in text or "ollama" in text:
        return "LOCAL_AI_ADAPTER"
    if "ledger" in text or "evidence" in text:
        return "EVIDENCE_LEDGER"
    if "hash" in text or "seal" in text:
        return "STATE_HASH"
    return "W7TP_GATEWAY"


def compile_packet(payload: IntentCompileIn) -> dict[str, Any]:
    decision = lint_w7tp_request(payload.intent, context=payload.context)
    action = _action(payload.intent)
    route = _route(payload.intent)
    packet = {
        "D1_Taiji_Root": payload.actor or "local_operator",
        "D2_Liangyi_Lock": "READ_ONLY_SAFE" if action == "READ_GET" and decision["allowed"] else "WRITE_EXECUTE_RISK",
        "D3_Sancai_Topology": payload.node or "MSI-WSL",
        "D4_Sixiang_Action": action,
        "D5_Wuxing_Route": route,
        "D6_Governance_Linter": decision["reason"],
        "D7_Verification_Code": canonical_hash(
            {
                "intent": payload.intent,
                "actor": payload.actor,
                "node": payload.node,
                "context": payload.context,
                "decision": decision,
            }
        ),
        "D8_State_FSM": decision["state"],
        "Heluo_Suggestions": {"tian": 100, "ren": 50, "di": 10},
        "Audit_Trace_Log": "runtime/ledger/w7tp_ui_events.jsonl",
    }
    return packet


@router.post("/intent/compile", response_model=IntentCompileOut)
def intent_compile(payload: IntentCompileIn) -> dict[str, Any]:
    return {"ok": True, "packet": compile_packet(payload), "source": "local_adapter"}


@router.post("/security/lint", response_model=SecurityLintOut)
def security_lint(payload: SecurityLintIn) -> dict[str, Any]:
    return lint_w7tp_request(payload.intent, payload.packet, payload.context)


@router.post("/state/transition", response_model=StateTransitionOut)
def state_transition(payload: StateTransitionIn) -> dict[str, Any]:
    decision = lint_w7tp_request(packet=payload.packet, context={"event": payload.event})
    transition = {
        "from_state": payload.from_state or "UNKNOWN",
        "event": payload.event,
        "next_state": decision["state"],
        "bagua": decision["bagua"],
        "packet_ref": canonical_hash(payload.packet),
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    return {
        "ok": True,
        "state": decision["state"],
        "bagua": decision["bagua"],
        "transition_id": canonical_hash(transition),
    }


@router.post("/hash/seal", response_model=HashSealOut)
def hash_seal(payload: HashSealIn) -> dict[str, Any]:
    return state_seal(payload.packet, payload.state, payload.node, payload.timestamp, payload.coordinate)


@router.post("/evidence/commit", response_model=EvidenceCommitOut)
def evidence_commit(payload: EvidenceCommitIn) -> dict[str, Any]:
    return commit_evidence(payload.packet, payload.state, payload.decision, payload.hash, payload.source)
