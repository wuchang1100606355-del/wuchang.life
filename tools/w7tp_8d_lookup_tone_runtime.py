#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import json
import pathlib
import sys
import hashlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from w7tp_8d_lookup_ai_min import run as lookup_run
from w7tp_packet_tone_renderer import latest_registry, load_registry, render as tone_render

SAFETY_FLAGS = {
    "SECRET_READ": False,
    "MEMBER_PLAINTEXT_READ": False,
    "RAW_AUDIO_SAVED": False,
    "DB_WRITE": False,
    "PAYMENT_CAPTURE": False,
    "SERVICE_RESTART": False,
    "DEPLOY": False,
    "PRODUCTION_RELEASE": False,
    "DIRECT_EXECUTION": False,
    "CANDIDATE_ONLY": True,
}

PAIRING = {
    ("not_bitter", "tired"): ("順口、不太苦", "拿鐵或低酸手沖", "偵測到不苦與疲勞狀態"),
    ("refreshing", "default"): ("清爽", "淺焙手沖或冰美式", "偵測到清爽偏好"),
    ("milky", "default"): ("奶香、順口", "拿鐵", "偵測到奶類偏好"),
    ("default", "default"): ("安全泛用", "拿鐵或今日手沖", "未取得明確偏好"),
}

def sha(obj):
    if not isinstance(obj, str):
        obj = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(obj.encode("utf-8")).hexdigest()

def recommend_slots(packet):
    slots = packet["D1_intent"].get("slots", {})
    taste = slots.get("taste_preference", "default")
    cond = slots.get("condition", "default")
    style, recommendation, reason = (
        PAIRING.get((taste, cond))
        or PAIRING.get((taste, "default"))
        or PAIRING[("default", "default")]
    )
    return {
        "style": style,
        "recommendation": recommendation,
        "reason": reason,
        "risk_items": "牛奶、堅果或咖啡因"
    }

def select_template_and_slots(packet, lookup_decision, channel):
    intent = packet["D1_intent"]["intent_id"]
    risk = packet["D7_risk"]["risk_code"]

    if intent == "recommend_order":
        rs = recommend_slots(packet)
        if lookup_decision == "ALLOW":
            return "recommend_allow_customer_v1", {
                "style": rs["style"],
                "recommendation": rs["recommendation"],
                "reason": rs["reason"],
            }
        if "voice" in channel:
            return "recommend_hold_allergy_voice_v1", {}
        return "recommend_hold_allergy_customer_v1", {
            "style": rs["style"],
            "risk_items": rs["risk_items"],
        }

    if intent == "payment_request":
        return "payment_hold_customer_v1", {}

    if intent == "member_lookup_masked" or risk == "member_plaintext":
        return "member_plaintext_block_v1", {}

    if intent == "member_sovereignty_override" or risk == "member_sovereignty_override":
        return "member_sovereignty_block_v1", {}

    if intent == "draft_order":
        return "draft_order_hold_staff_v1", {}

    return "unknown_intent_clarify_customer_v1", {}

def run_integrated(text, channel, registry_path):
    lookup = lookup_run(text)
    packet = lookup["PACKET"]
    lookup_decision = lookup["VERIFIER"]["decision"]

    template_id, render_slots = select_template_and_slots(packet, lookup_decision, channel)

    reg_path = registry_path or latest_registry()
    registry = load_registry(reg_path)
    if template_id == "member_sovereignty_block_v1":
        rendered = {
            "STATE": "PASS_PACKET_TONE_RENDER",
            "rendered_text": "會員主權不可由總場、協會、管理員、AI 或候選腦取代；安全可處理不等於會員已同意，必須由會員本人明確確認。",
            "template": {
                "template_id": template_id,
                "decision": "BLOCK",
                "tone_policy_id": "staff_direct_hold_v1",
            },
            "forbidden_hits": [],
            "tone_style": {
                "directness": "high",
                "politeness": "medium",
                "urgency": "medium",
                "warmth": "low",
            },
        }
    else:
        rendered = tone_render(registry, template_id, render_slots)

    final_gate = lookup_decision
    final_text = rendered.get("rendered_text", "")

    hard_errors = []
    if rendered.get("STATE", "").startswith("HOLD"):
        hard_errors.append("tone_renderer_hold")
    if rendered.get("forbidden_hits"):
        hard_errors.append("forbidden_hits")

    state = "PASS_W7TP_8D_LOOKUP_TONE_RUNTIME" if not hard_errors else "HOLD_W7TP_8D_LOOKUP_TONE_RUNTIME"

    return {
        "STATE": state,
        "candidate_only": True,
        "production_release": False,
        "db_write": False,
        "direct_execution": False,
        "input_text_hash": sha(text),
        "registry": reg_path,
        "lookup": {
            "intent_id": packet["D1_intent"]["intent_id"],
            "slots": packet["D1_intent"].get("slots", {}),
            "risk_code": packet["D7_risk"]["risk_code"],
            "verifier_decision": lookup_decision,
            "verifier_reasons": lookup["VERIFIER"]["reasons"],
            "packet_hash": packet["D8_envelope"]["packet_hash"]
        },
        "tone_render": {
            "template_id": template_id,
            "template_decision": rendered["template"]["decision"],
            "render_state": rendered["STATE"],
            "forbidden_hits": rendered.get("forbidden_hits", []),
            "tone_style": rendered.get("tone_style", {})
        },
        "final": {
            "gate": final_gate,
            "text": final_text
        },
        "hard_errors": hard_errors,
        "safety_flags": SAFETY_FLAGS
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--channel", default="counter_voice")
    ap.add_argument("--registry", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    result = run_integrated(args.text, args.channel, args.registry)
    s = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    print(s)

    if args.out:
        p = pathlib.Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(s + "\n", encoding="utf-8")

    return 0 if result["STATE"].startswith("PASS") else 1

if __name__ == "__main__":
    raise SystemExit(main())
