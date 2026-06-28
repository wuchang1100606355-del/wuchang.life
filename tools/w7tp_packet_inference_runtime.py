#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W7TP packet-by-packet inference runtime v0.2.

This file is intentionally model-free: tables, rules, and the verifier produce
the packet chain. A model lane may be represented only as an unavailable stub.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


SAFETY_FLAGS = {
    "SECRET_READ": False,
    "MEMBER_PLAINTEXT_READ": False,
    "RAW_AUDIO_SAVED": False,
    "DB_WRITE": False,
    "PAYMENT_CAPTURE": False,
    "SERVICE_RESTART": False,
    "DEPLOY": False,
    "PRODUCTION_RELEASE": False,
    "EXTERNAL_API_CALL": False,
    "MODEL_REQUIRED": False,
    "LLM_AUTHORITY": False,
}

INTENT_ALIAS_TABLE = {
    "recommend_order": ["推薦", "喝什麼", "好喝", "幫我配", "不苦", "清爽", "順口", "有點累", "想喝"],
    "ask_menu": ["菜單", "品項", "價格", "menu"],
    "draft_order": ["幫我點", "我要一杯", "加入訂單", "下單"],
    "member_lookup_masked": ["會員", "點數", "查會員"],
    "member_plaintext_request": ["完整電話", "完整地址", "身份證", "身分證", "會員明文"],
    "payment_request": ["結帳", "付款", "刷卡", "收錢", "付錢"],
}

SLOT_PATTERN_TABLE = {
    "taste_preference": {
        "refreshing": ["清爽", "輕一點", "低酸", "果香"],
        "not_bitter": ["不苦", "不要苦", "順口"],
        "milky": ["拿鐵", "牛奶", "奶"],
    },
    "condition": {
        "tired": ["累", "疲勞", "沒精神"],
        "hot": ["熱", "很熱", "悶"],
    },
    "risk_signal": {
        "allergy": ["過敏", "乳糖", "不能喝奶", "牛奶敏感", "堅果過敏", "敏感"],
        "payment": ["付款", "結帳", "刷卡", "收錢"],
        "member_plaintext": ["完整電話", "完整地址", "身份證", "身分證", "會員明文"],
    },
}

ROUTE_TABLE = {
    "recommend_order": {
        "rule_ref": "rules/cafe_recommend_v2",
        "table_ref": "tables/cafe_pairing_v2",
        "template_ref": "templates/recommend_v2",
        "route": "cafe_recommendation_lane",
    },
    "ask_menu": {
        "rule_ref": "rules/menu_query_v1",
        "table_ref": "tables/menu_v1",
        "template_ref": "templates/menu_v1",
        "route": "menu_query_lane",
    },
    "draft_order": {
        "rule_ref": "rules/draft_order_candidate_v1",
        "table_ref": "tables/order_draft_v1",
        "template_ref": "templates/draft_order_v1",
        "route": "draft_order_candidate_lane",
    },
    "member_lookup_masked": {
        "rule_ref": "rules/member_masked_v1",
        "table_ref": "tables/member_masked_v1",
        "template_ref": "templates/member_masked_v1",
        "route": "member_masked_lane",
    },
    "member_plaintext_request": {
        "rule_ref": "rules/member_plaintext_block_v1",
        "table_ref": "tables/member_no_plaintext_v1",
        "template_ref": "templates/member_plaintext_block_v1",
        "route": "blocked_member_plaintext_lane",
    },
    "payment_request": {
        "rule_ref": "rules/payment_human_review_v1",
        "table_ref": "tables/payment_boundary_v1",
        "template_ref": "templates/payment_hold_v1",
        "route": "payment_hold_lane",
    },
    "unknown": {
        "rule_ref": "rules/unknown_v1",
        "table_ref": "tables/fallback_v1",
        "template_ref": "templates/clarify_v1",
        "route": "clarify_lane",
    },
}

RISK_POLICY_TABLE = {
    "member_plaintext": {"decision": "BLOCK", "reasons": ["member plaintext request blocked"]},
    "payment": {"decision": "HOLD", "reasons": ["payment capture requires human authority"]},
    "allergy": {"decision": "HOLD", "reasons": ["allergy or intolerance signal needs confirmation"]},
    "low_confidence": {"decision": "HOLD", "reasons": ["low intent confidence"]},
    "draft_order": {"decision": "HOLD", "reasons": ["formal order write requires counter confirmation"]},
    "none": {"decision": "CONTINUE", "reasons": ["packet verified"]},
}

CAPABILITY_TABLE = {
    "recommend_order": {
        "allowed_actions": ["show_recommendation", "speak_recommendation", "create_draft_order_candidate"],
        "forbidden_actions": ["formal_pos_order_without_human_review", "payment_capture"],
    },
    "ask_menu": {
        "allowed_actions": ["show_menu", "speak_menu"],
        "forbidden_actions": ["payment_capture"],
    },
    "draft_order": {
        "allowed_actions": ["create_draft_order_candidate", "ask_human_confirmation"],
        "forbidden_actions": ["formal_pos_order_without_human_review", "payment_capture"],
    },
    "member_lookup_masked": {
        "allowed_actions": ["show_masked_member_status"],
        "forbidden_actions": ["show_member_plaintext", "export_member_plaintext"],
    },
    "member_plaintext_request": {
        "allowed_actions": [],
        "forbidden_actions": ["member_plaintext_read", "show_member_plaintext", "export_member_plaintext"],
    },
    "payment_request": {
        "allowed_actions": ["ask_human_confirmation"],
        "forbidden_actions": ["payment_capture", "auto_charge"],
    },
    "unknown": {
        "allowed_actions": ["ask_clarifying_question"],
        "forbidden_actions": ["payment_capture", "member_plaintext_read"],
    },
}

PAIRING_TABLE = {
    ("not_bitter", "tired"): {"item": "拿鐵或低酸手沖", "style": "順口、不太苦", "why": "偵測到不苦偏好與疲勞狀態"},
    ("refreshing", "default"): {"item": "淺焙手沖或冰美式", "style": "清爽", "why": "偵測到清爽偏好"},
    ("milky", "default"): {"item": "拿鐵", "style": "奶香、順口", "why": "偵測到奶類偏好"},
    ("default", "default"): {"item": "拿鐵或今日手沖", "style": "安全泛用", "why": "未取得明確偏好"},
}

TEMPLATE_TABLE = {
    "recommend_allow": "今天可以先考慮{style}的選項，例如{item}。原因是：{why}。",
    "recommend_hold": "我可以先幫你推薦{style}的候選選項，例如{item}。但需要先確認：{reason}。",
    "payment_hold": "付款或結帳必須由櫃台人工確認；此流程只產生候選提示，不會自動扣款。",
    "member_block": "會員明文資料不可由此流程讀取或顯示。",
    "draft_hold": "可以建立候選訂單草稿，但正式寫入 POS 前必須由櫃台確認。",
    "menu_allow": "目前可以查詢菜單與可供應品項；不會觸發下單或付款。",
    "clarify_hold": "目前意圖不明，先進入補問流程。",
}


def sha(value: Any) -> str:
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def now_unix() -> int:
    return int(time.time())


def pick_slots(text: str) -> dict[str, str]:
    lowered = text.lower()
    slots: dict[str, str] = {}
    for slot_name, patterns in SLOT_PATTERN_TABLE.items():
        for slot_value, words in patterns.items():
            if any(word.lower() in lowered for word in words):
                slots[slot_name] = slot_value
                break
    return slots


def parse_intent(text: str) -> tuple[str, dict[str, str], str]:
    lowered = text.lower()
    slots = pick_slots(lowered)
    if slots.get("risk_signal") == "member_plaintext":
        return "member_plaintext_request", slots, "L3"
    if slots.get("risk_signal") == "payment":
        return "payment_request", slots, "L3"

    scores = {intent: sum(1 for word in words if word.lower() in lowered) for intent, words in INTENT_ALIAS_TABLE.items()}
    intent = max(scores, key=scores.get)
    score = scores[intent]
    if score <= 0:
        return "unknown", slots, "L1"
    return intent, slots, "L3" if score > 1 else "L2"


def blank_8d(packet_type: str, step: str, parent_packet_hash: str | None, context: dict[str, Any]) -> dict[str, Any]:
    packet = {
        "packet_type": packet_type,
        "version": "v0.2",
        "step": step,
        "parent_packet_hash": parent_packet_hash,
        "D1_intent": context.get("D1_intent", {}),
        "D2_state": context.get("D2_state", {}),
        "D3_coordinate": context.get("D3_coordinate", {}),
        "D4_evidence": context.get("D4_evidence", {}),
        "D5_execution": context.get("D5_execution", {}),
        "D6_gt": context.get("D6_gt", {}),
        "D7_risk": context.get("D7_risk", {}),
        "D8_envelope": {
            "packet_id": "pkt_" + uuid.uuid4().hex,
            "created_at_unix": now_unix(),
            "ttl_seconds": context.get("ttl_seconds", 300),
            "nonce": uuid.uuid4().hex,
        },
    }
    packet_hash = sha(packet)
    packet["D8_envelope"]["packet_hash"] = packet_hash
    packet["D8_envelope"]["seal"] = sha(packet_hash + ":" + packet["D8_envelope"]["nonce"])
    return packet


def reseal(packet: dict[str, Any]) -> None:
    packet["D8_envelope"].pop("packet_hash", None)
    packet["D8_envelope"].pop("seal", None)
    packet_hash = sha(packet)
    packet["D8_envelope"]["packet_hash"] = packet_hash
    packet["D8_envelope"]["seal"] = sha(packet_hash + ":" + packet["D8_envelope"]["nonce"])


def verifier(packet: dict[str, Any]) -> dict[str, Any]:
    intent = packet.get("D1_intent", {}).get("intent_id", "unknown")
    slots = packet.get("D1_intent", {}).get("slots", {})
    confidence = packet.get("D1_intent", {}).get("confidence_level", "L1")
    risk_signal = slots.get("risk_signal", "none")

    if risk_signal == "member_plaintext" or intent == "member_plaintext_request":
        policy = RISK_POLICY_TABLE["member_plaintext"]
    elif risk_signal == "payment" or intent == "payment_request":
        policy = RISK_POLICY_TABLE["payment"]
    elif risk_signal == "allergy":
        policy = RISK_POLICY_TABLE["allergy"]
    elif confidence == "L1" or intent == "unknown":
        policy = RISK_POLICY_TABLE["low_confidence"]
    elif intent == "draft_order":
        policy = RISK_POLICY_TABLE["draft_order"]
    else:
        policy = RISK_POLICY_TABLE["none"]

    decision = policy["decision"]
    if decision == "CONTINUE" and packet["step"] in {"S6_OUTPUT_PACKET", "S7_FEEDBACK_CANDIDATE_PACKET"}:
        decision = "ALLOW"
    return {"decision": decision, "reasons": list(policy["reasons"])}


@dataclass(frozen=True)
class PacketStep:
    name: str
    input_packet_type: str
    output_packet_type: str
    verifier: Callable[[dict[str, Any]], dict[str, Any]]
    transition: Callable[[dict[str, Any] | None, dict[str, Any]], dict[str, Any]]


def transition_input_event(_: dict[str, Any] | None, ctx: dict[str, Any]) -> dict[str, Any]:
    text = ctx["text"]
    base = {
        "ttl_seconds": ctx["ttl_seconds"],
        "D1_intent": {"intent_id": "input_event", "slots": {}, "confidence_level": "L0"},
        "D2_state": {"runtime_state": "input_received"},
        "D3_coordinate": {"branch": ctx["branch"], "actor_role": ctx["actor_role"], "channel": ctx["channel"]},
        "D4_evidence": {"input_text_hash": sha(text), "input_length": len(text)},
        "D5_execution": {"candidate_only": True, "side_effects_allowed": False},
        "D6_gt": {"rule_ref": "rules/input_event_v1", "table_ref": "tables/input_event_v1", "template_ref": "templates/input_event_v1"},
        "D7_risk": {"risk_code": "not_evaluated", "decision": "CONTINUE", "reasons": []},
    }
    return blank_8d("input_event_packet", "S0_INPUT_EVENT", None, base)


def transition_intent(prev: dict[str, Any] | None, ctx: dict[str, Any]) -> dict[str, Any]:
    intent, slots, confidence = parse_intent(ctx["text"])
    base = dict(prev or {})
    context = {
        "ttl_seconds": ctx["ttl_seconds"],
        "D1_intent": {"intent_id": intent, "slots": slots, "confidence_level": confidence},
        "D2_state": {"runtime_state": "intent_parsed"},
        "D3_coordinate": (prev or {})["D3_coordinate"],
        "D4_evidence": {"input_text_hash": sha(ctx["text"]), "parser": "model_free_alias_slot_parser_v1"},
        "D5_execution": {"candidate_only": True, "side_effects_allowed": False},
        "D6_gt": {"rule_ref": "rules/intent_alias_v1", "table_ref": "intent_alias_table", "template_ref": "none"},
        "D7_risk": base.get("D7_risk", {}),
    }
    return blank_8d("intent_packet", "S1_INTENT_PACKET", prev["D8_envelope"]["packet_hash"], context)


def transition_route(prev: dict[str, Any] | None, ctx: dict[str, Any]) -> dict[str, Any]:
    intent = prev["D1_intent"]["intent_id"]
    route = ROUTE_TABLE.get(intent, ROUTE_TABLE["unknown"])
    context = {
        "ttl_seconds": ctx["ttl_seconds"],
        "D1_intent": prev["D1_intent"],
        "D2_state": {"runtime_state": "route_selected", "route": route["route"]},
        "D3_coordinate": prev["D3_coordinate"],
        "D4_evidence": {**prev["D4_evidence"], "route_table_hash": sha(ROUTE_TABLE)},
        "D5_execution": prev["D5_execution"],
        "D6_gt": {"rule_ref": route["rule_ref"], "table_ref": route["table_ref"], "template_ref": route["template_ref"]},
        "D7_risk": prev["D7_risk"],
    }
    return blank_8d("route_packet", "S2_ROUTE_PACKET", prev["D8_envelope"]["packet_hash"], context)


def transition_state(prev: dict[str, Any] | None, ctx: dict[str, Any]) -> dict[str, Any]:
    context = {
        "ttl_seconds": ctx["ttl_seconds"],
        "D1_intent": prev["D1_intent"],
        "D2_state": {
            **prev["D2_state"],
            "state_refs": {
                "menu_ref": "branch.menu.current",
                "member_ref": "masked_or_none",
                "inventory_ref": "branch.inventory.summary",
            },
        },
        "D3_coordinate": prev["D3_coordinate"],
        "D4_evidence": {**prev["D4_evidence"], "state_ref_mode": "refs_only_no_plaintext"},
        "D5_execution": prev["D5_execution"],
        "D6_gt": prev["D6_gt"],
        "D7_risk": prev["D7_risk"],
    }
    return blank_8d("state_packet", "S3_STATE_PACKET", prev["D8_envelope"]["packet_hash"], context)


def transition_risk(prev: dict[str, Any] | None, ctx: dict[str, Any]) -> dict[str, Any]:
    interim = verifier(prev)
    risk_code = prev["D1_intent"].get("slots", {}).get("risk_signal", "none")
    if prev["D1_intent"]["intent_id"] == "unknown":
        risk_code = "low_confidence"
    context = {
        "ttl_seconds": ctx["ttl_seconds"],
        "D1_intent": prev["D1_intent"],
        "D2_state": prev["D2_state"],
        "D3_coordinate": prev["D3_coordinate"],
        "D4_evidence": {**prev["D4_evidence"], "risk_policy_table_hash": sha(RISK_POLICY_TABLE)},
        "D5_execution": prev["D5_execution"],
        "D6_gt": prev["D6_gt"],
        "D7_risk": {"risk_code": risk_code, "decision": interim["decision"], "reasons": interim["reasons"]},
    }
    return blank_8d("risk_packet", "S4_RISK_PACKET", prev["D8_envelope"]["packet_hash"], context)


def transition_capability(prev: dict[str, Any] | None, ctx: dict[str, Any]) -> dict[str, Any]:
    intent = prev["D1_intent"]["intent_id"]
    caps = CAPABILITY_TABLE.get(intent, CAPABILITY_TABLE["unknown"])
    context = {
        "ttl_seconds": ctx["ttl_seconds"],
        "D1_intent": prev["D1_intent"],
        "D2_state": prev["D2_state"],
        "D3_coordinate": prev["D3_coordinate"],
        "D4_evidence": {**prev["D4_evidence"], "capability_table_hash": sha(CAPABILITY_TABLE)},
        "D5_execution": {
            "allowed_actions": caps["allowed_actions"],
            "forbidden_actions": caps["forbidden_actions"],
            "candidate_only": True,
            "side_effects_allowed": False,
        },
        "D6_gt": prev["D6_gt"],
        "D7_risk": prev["D7_risk"],
    }
    return blank_8d("capability_packet", "S5_CAPABILITY_PACKET", prev["D8_envelope"]["packet_hash"], context)


def build_semantic_ir(packet: dict[str, Any]) -> dict[str, Any]:
    slots = packet["D1_intent"].get("slots", {})
    taste = slots.get("taste_preference", "default")
    condition = slots.get("condition", "default")
    pairing = PAIRING_TABLE.get((taste, condition)) or PAIRING_TABLE.get((taste, "default")) or PAIRING_TABLE[("default", "default")]
    return {
        "intent_id": packet["D1_intent"]["intent_id"],
        "slots": slots,
        "decision": packet["D7_risk"].get("decision", "CONTINUE"),
        "recommendation": pairing,
        "route": packet["D2_state"].get("route", "unknown"),
    }


def render_language(semantic_ir: dict[str, Any], final_decision: str, reasons: list[str]) -> str:
    intent = semantic_ir["intent_id"]
    rec = semantic_ir["recommendation"]
    reason = "、".join(reasons)
    if intent == "recommend_order":
        key = "recommend_allow" if final_decision == "ALLOW" else "recommend_hold"
        return TEMPLATE_TABLE[key].format(**rec, reason=reason)
    if intent == "payment_request":
        return TEMPLATE_TABLE["payment_hold"]
    if intent in {"member_lookup_masked", "member_plaintext_request"}:
        return TEMPLATE_TABLE["member_block"]
    if intent == "draft_order":
        return TEMPLATE_TABLE["draft_hold"]
    if intent == "ask_menu":
        return TEMPLATE_TABLE["menu_allow"]
    return TEMPLATE_TABLE["clarify_hold"]


def transition_output(prev: dict[str, Any] | None, ctx: dict[str, Any]) -> dict[str, Any]:
    semantic_ir = build_semantic_ir(prev)
    context = {
        "ttl_seconds": ctx["ttl_seconds"],
        "D1_intent": prev["D1_intent"],
        "D2_state": {**prev["D2_state"], "semantic_ir": semantic_ir},
        "D3_coordinate": prev["D3_coordinate"],
        "D4_evidence": {**prev["D4_evidence"], "template_table_hash": sha(TEMPLATE_TABLE)},
        "D5_execution": prev["D5_execution"],
        "D6_gt": prev["D6_gt"],
        "D7_risk": prev["D7_risk"],
    }
    return blank_8d("output_packet", "S6_OUTPUT_PACKET", prev["D8_envelope"]["packet_hash"], context)


def transition_feedback(prev: dict[str, Any] | None, ctx: dict[str, Any]) -> dict[str, Any]:
    model_lane = {"model_lane_available": False, "candidate_packet": None, "authority": "verifier_only"}
    context = {
        "ttl_seconds": ctx["ttl_seconds"],
        "D1_intent": prev["D1_intent"],
        "D2_state": {
            **prev["D2_state"],
            "feedback_candidate": {
                "capture_mode": "hash_and_refs_only",
                "may_update_tables_after_review": True,
                "model_lane_stub": model_lane,
            },
        },
        "D3_coordinate": prev["D3_coordinate"],
        "D4_evidence": {**prev["D4_evidence"], "feedback_ref": "runtime.feedback_candidate.local"},
        "D5_execution": prev["D5_execution"],
        "D6_gt": prev["D6_gt"],
        "D7_risk": prev["D7_risk"],
    }
    return blank_8d("feedback_candidate_packet", "S7_FEEDBACK_CANDIDATE_PACKET", prev["D8_envelope"]["packet_hash"], context)


STEPS = [
    PacketStep("S0_INPUT_EVENT", "none", "input_event_packet", verifier, transition_input_event),
    PacketStep("S1_INTENT_PACKET", "input_event_packet", "intent_packet", verifier, transition_intent),
    PacketStep("S2_ROUTE_PACKET", "intent_packet", "route_packet", verifier, transition_route),
    PacketStep("S3_STATE_PACKET", "route_packet", "state_packet", verifier, transition_state),
    PacketStep("S4_RISK_PACKET", "state_packet", "risk_packet", verifier, transition_risk),
    PacketStep("S5_CAPABILITY_PACKET", "risk_packet", "capability_packet", verifier, transition_capability),
    PacketStep("S6_OUTPUT_PACKET", "capability_packet", "output_packet", verifier, transition_output),
    PacketStep("S7_FEEDBACK_CANDIDATE_PACKET", "output_packet", "feedback_candidate_packet", verifier, transition_feedback),
]


def final_verifier(verifier_results: list[dict[str, Any]]) -> dict[str, Any]:
    reasons: list[str] = []
    decisions = [result["decision"] for result in verifier_results]
    for result in verifier_results:
        for reason in result["reasons"]:
            if reason not in reasons:
                reasons.append(reason)
    if "BLOCK" in decisions:
        decision = "BLOCK"
    elif "HOLD" in decisions:
        decision = "HOLD"
    else:
        decision = "ALLOW"
    return {"decision": decision, "reasons": reasons or ["verified"]}


def run(text: str, branch: str = "cafe_main", actor_role: str = "counter_ai", channel: str = "counter_voice") -> dict[str, Any]:
    ctx = {
        "text": text,
        "branch": branch,
        "actor_role": actor_role,
        "channel": channel,
        "ttl_seconds": 300,
    }
    packet_chain = []
    verifier_results = []
    previous = None
    for step in STEPS:
        packet = step.transition(previous, ctx)
        result = step.verifier(packet)
        packet["D7_risk"] = {
            **packet.get("D7_risk", {}),
            "decision": result["decision"],
            "reasons": result["reasons"],
        }
        reseal(packet)
        packet_chain.append(packet)
        verifier_results.append({"step": step.name, **result})
        previous = packet

    final = final_verifier(verifier_results)
    semantic_ir = packet_chain[-2]["D2_state"]["semantic_ir"]
    zh_tw = render_language(semantic_ir, final["decision"], final["reasons"])
    return {
        "STATE": "PASS_W7TP_PACKET_INFERENCE_RUNTIME",
        "RUN_MODE": "MODEL_FREE_PACKET_BY_PACKET_INFERENCE",
        "SAFETY_FLAGS": SAFETY_FLAGS,
        "INPUT_TEXT_HASH": sha(text),
        "PACKET_CHAIN": packet_chain,
        "STEP_VERIFIERS": verifier_results,
        "FINAL_VERIFIER": final,
        "LANGUAGE_RECONSTRUCTION": {
            "semantic_ir": semantic_ir,
            "zh_TW": zh_tw,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    parser.add_argument("--out", default="")
    parser.add_argument("--branch", default="cafe_main")
    parser.add_argument("--actor-role", default="counter_ai")
    parser.add_argument("--channel", default="counter_voice")
    args = parser.parse_args()

    data = run(args.text, branch=args.branch, actor_role=args.actor_role, channel=args.channel)
    rendered = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
    print(rendered)
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
