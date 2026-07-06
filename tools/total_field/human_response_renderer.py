#!/usr/bin/env python3
"""Human-facing renderer for Total Field gate results.

The renderer turns internal gate decisions into natural-language replies. It
does not expose raw D1-D8 fields, verifier internals, ADI rules, H64, or TD.
"""

from __future__ import annotations

import json
from typing import Any


PASS = "PASS"
HOLD = "HOLD"
BLOCK = "BLOCK"

INTERNAL_MARKERS = (
    "D1",
    "D2",
    "D3",
    "D4",
    "D5",
    "D6",
    "D7",
    "D8",
    "H64",
    "TD",
    "proof_D7",
    "env_D8",
    "trajectory_hmac",
    "nonce",
)


def _clean_text(text: Any, limit: int = 500) -> str:
    value = " ".join(str(text or "").split())
    for marker in INTERNAL_MARKERS:
        value = value.replace(marker, "[internal]")
    return value[:limit]


def _hold_text(gate_result: dict[str, Any]) -> str:
    code = str(gate_result.get("gate_code") or "")
    if code == "HOLD_GT_DEFINITION_DRIFT":
        return "這個說法會混淆核心技術定義，我先暫停，只保留為候選內容，需人工確認後才能繼續。"
    if code == "HOLD_HARD_RISK_SIDE_EFFECT":
        return "這個要求涉及寫入、部署、重啟或正式送件等高風險操作，我先暫停，不會執行任何正式動作。"
    if code == "HOLD_ADI_5D_ABSOLUTE_INDEX":
        return "這個候選請求缺少必要索引條件，我先暫停，需補齊後再回覆。"
    return "這個候選需要再確認，我先暫停，不會執行任何正式動作。"


def render_human_response(gate_result: dict[str, Any] | None, channel: str = "web") -> dict[str, Any]:
    result = gate_result if isinstance(gate_result, dict) else {}
    decision = str(result.get("decision") or HOLD)
    risk_level = str(result.get("risk_level") or "MEDIUM")
    channel_name = str(channel or result.get("source_channel") or "web").upper()

    if decision == PASS:
        reply_candidate = result.get("reply_candidate") if isinstance(result.get("reply_candidate"), dict) else {}
        body = _clean_text(reply_candidate.get("text") or "可以，我先提供候選回覆。")
        reply_text = f"{body} 目前沒有執行付款、寫入、部署或重啟。"
        requires_confirmation = False
    elif decision == BLOCK:
        reply_text = "這個請求目前不能繼續，我已停止候選流程，沒有執行任何正式動作。"
        requires_confirmation = True
    else:
        reply_text = _hold_text(result)
        requires_confirmation = risk_level != "LOW"

    response = {
        "state": "HUMAN_RESPONSE_RENDERED",
        "decision": decision,
        "risk_level": risk_level,
        "channel": channel_name,
        "reply_text": _clean_text(reply_text, limit=700),
        "requires_confirmation": requires_confirmation,
        "candidate_reply_only": True,
        "formal_send_executed": False,
        "line_reply_sent": False,
        "db_write": False,
        "odoo_write": False,
        "deploy": False,
        "restart": False,
        "redaction": {
            "raw_d_dimensions_exposed": False,
            "verifier_internals_exposed": False,
            "h64_td_exposed": False,
        },
    }
    return response


def main() -> int:
    sample = {"decision": PASS, "risk_level": "LOW", "reply_candidate": {"text": "可以，我先整理候選回覆。"}}
    print(json.dumps(render_human_response(sample), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
