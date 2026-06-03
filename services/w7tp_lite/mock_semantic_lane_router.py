"""Deterministic semantic-lane router for W7TP Lite design experiments.

Routing is performed by code rules before any model or executor could be
considered. This module has no network, shell, database, or service access.
"""

from __future__ import annotations

import hashlib
import json
import sys
from typing import Any

from mock_intent_parser import parse_intent


SCHEMA_ID = "w7tp.semantic_router_decision.v0.1"
DOCUMENT_TERMS = ("文件", "規格", "schema", "spec", "review", "差異")
WRITE_TERMS = ("寫入", "建立", "修改", "刪除", "部署", "同步", "正式資料")


def _decision_id(intent_id: str, intent_class: str) -> str:
    digest = hashlib.sha256(f"{intent_id}:{intent_class}".encode("utf-8")).hexdigest()[:12]
    return f"router_decision_{digest}"


def route_packet(packet: dict[str, Any]) -> dict[str, Any]:
    """Route an existing plan-only W7IP Lite packet into deterministic lanes."""
    if packet.get("plan_only") is not True or packet.get("allowed_mode") != "plan_only":
        raise ValueError("semantic router only accepts W7IP Lite plan-only packets")

    text = str(packet.get("input_text", "")).casefold()
    targets = set(packet.get("target_system", []))
    has_write = any(term.casefold() in text for term in WRITE_TERMS)
    has_document = any(term.casefold() in text for term in DOCUMENT_TERMS)

    if has_write or ("odoo" in targets and packet.get("risk_level") in {"L2", "L3"}):
        intent_class = "blocked_write"
        lanes = ["blocked"]
        risk_level = "L3"
        interrupt_required = True
        route_to_dlq = True
        reason = "Write or formal-data intent is blocked before allocation and routed to Router DLQ."
    elif has_document:
        intent_class = "document_spec_review"
        lanes = ["google_lane", "open_lane"]
        risk_level = "L1"
        interrupt_required = False
        route_to_dlq = False
        reason = "Document/spec intent is routed to review-only collaboration lanes."
    elif targets & {"gateway", "ollama", "odoo", "line_webhook"}:
        intent_class = "health_check"
        lanes = ["local_lane", "open_lane"]
        risk_level = packet.get("risk_level", "L0")
        interrupt_required = False
        route_to_dlq = False
        reason = "Read-only system observation intent is routed to local and open review lanes."
    else:
        intent_class = "manual_review"
        lanes = ["open_lane"]
        risk_level = "L1"
        interrupt_required = True
        route_to_dlq = False
        reason = "Unclassified intent stays in review-only lane pending human interpretation."

    return {
        "schema": SCHEMA_ID,
        "decision_id": _decision_id(packet["intent_id"], intent_class),
        "intent_id": packet["intent_id"],
        "intent_class": intent_class,
        "selected_lanes": lanes,
        "risk_level": risk_level,
        "plan_only": True,
        "interrupt_required": interrupt_required,
        "route_to_dlq": route_to_dlq,
        "durable_state_hint": "manifest_only_no_runtime_write",
        "reason": reason,
    }


def route_text(input_text: str) -> dict[str, Any]:
    """Convenience wrapper for mock testing only."""
    return route_packet(parse_intent(input_text))


def main(argv: list[str]) -> int:
    text = " ".join(argv).strip() or "檢查目前 Gateway、Ollama、Odoo 是否在線"
    print(json.dumps(route_text(text), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
