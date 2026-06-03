"""Deterministic W7IP Lite parser for design-time, plan-only demonstrations.

This module performs no network calls, service operations, shell execution,
database access, or secret access. It converts a test sentence into a mock
seven-dimensional intent packet.
"""

from __future__ import annotations

import hashlib
import json
import sys
from typing import Any


SCHEMA_ID = "w7ip_lite.intent_packet.v0.1"

TARGET_RULES = (
    ("line_webhook", ("line webhook", "line webhook", "webhook")),
    ("gateway", ("gateway", "閘道")),
    ("ollama", ("ollama",)),
    ("odoo", ("odoo",)),
)

OBSERVE_TERMS = ("檢查", "查詢", "是否在線", "在線", "狀態", "status", "health")
MUTATION_TERMS = ("啟動", "重啟", "寫入", "修改", "建立", "刪除", "部署", "同步", "執行")


def _intent_id(input_text: str) -> str:
    digest = hashlib.sha256(input_text.encode("utf-8")).hexdigest()[:12]
    return f"w7ip_lite_{digest}"


def _detect_targets(input_text: str) -> list[str]:
    normalized = input_text.casefold()
    targets: list[str] = []
    for target, terms in TARGET_RULES:
        if any(term.casefold() in normalized for term in terms):
            targets.append(target)
    return targets or ["unknown"]


def parse_intent(input_text: str) -> dict[str, Any]:
    """Convert mock text into a W7IP Lite packet without any side effects."""
    text = input_text.strip()
    if not text:
        raise ValueError("input_text must not be empty")

    normalized = text.casefold()
    has_mutation = any(term.casefold() in normalized for term in MUTATION_TERMS)
    has_observation = any(term.casefold() in normalized for term in OBSERVE_TERMS)
    targets = _detect_targets(text)

    if has_mutation:
        actor_level = "A1_design"
        bagua_direction = "HU"
        risk_level = "L2"
        heaven = "governance_human_review_required"
        vector_y = "proposed_change"
        vector_z = "blocked_mutation"
        reason = "Mutation-like intent detected; block execution and produce a human-review plan only."
    elif "unknown" in targets or not has_observation:
        actor_level = "A0_readonly"
        bagua_direction = "TIAN"
        risk_level = "L1"
        heaven = "governance_human_review_required"
        vector_y = "unclassified_target"
        vector_z = "review_required"
        reason = "Target or observation intent is not fully classified; produce a review plan only."
    else:
        actor_level = "A0_readonly"
        bagua_direction = "NIAO"
        risk_level = "L0"
        heaven = "governance_observe_only"
        vector_y = "service_health"
        vector_z = "observe"
        reason = "Read-only service status intent detected; generate observation plan only."

    return {
        "schema": SCHEMA_ID,
        "intent_id": _intent_id(text),
        "input_text": text,
        "actor_level": actor_level,
        "yin_yang_axis": {
            "heaven": heaven,
            "earth": "mock_local_no_state_write",
        },
        "bagua_direction": bagua_direction,
        "five_d_vector": {
            "x": "local_runtime",
            "y": vector_y,
            "z": vector_z,
            "time": "request_now",
            "scale": "w7tp_lite_mvp",
        },
        "target_system": targets,
        "risk_level": risk_level,
        "allowed_mode": "plan_only",
        "plan_only": True,
        "reason": reason,
    }


def main(argv: list[str]) -> int:
    text = " ".join(argv).strip() or "檢查目前 Gateway、Ollama、Odoo 是否在線"
    print(json.dumps(parse_intent(text), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
