#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, hashlib, time, uuid, argparse
from pathlib import Path

SAFETY = dict(
    SECRET_READ=False,
    MEMBER_PLAINTEXT_READ=False,
    RAW_AUDIO_SAVED=False,
    DB_WRITE=False,
    PAYMENT_CAPTURE=False,
    SERVICE_RESTART=False,
    DEPLOY=False,
    PRODUCTION_RELEASE=False,
    MODEL_REQUIRED=False,
    LLM_AUTHORITY=False,
)

ALIASES = {
    "recommend_order": ["推薦","喝什麼","好喝","幫我配","不苦","清爽","順口","有點累","想喝"],
    "ask_menu": ["菜單","品項","價格","menu"],
    "draft_order": ["幫我點","我要一杯","加入訂單","下單"],
    "member_lookup_masked": ["會員","點數","查會員"],
    "payment_request": ["結帳","付款","刷卡","收錢","付錢"],
}

SLOTS = {
    "taste_preference": {
        "refreshing": ["清爽","輕一點","低酸","果香"],
        "not_bitter": ["不苦","不要苦","順口"],
        "milky": ["拿鐵","牛奶","奶"],
    },
    "condition": {
        "tired": ["累","疲勞","沒精神"],
        "hot": ["熱","很熱","悶"],
    },
    "risk_signal": {
        "allergy": ["過敏","乳糖","不能喝奶","牛奶敏感","堅果過敏"],
        "payment": ["付款","結帳","刷卡","收錢"],
        "member_plaintext": ["完整電話","完整地址","身份證","身分證","會員明文"],
    },
}

ROUTES = {
    "recommend_order": ("rules/cafe_recommend_v1","tables/cafe_pairing_v1","templates/recommend_v1",
        ["show_recommendation","speak_recommendation","create_draft_order"],
        ["formal_pos_order_without_human_review","payment_capture"]),
    "ask_menu": ("rules/menu_query_v1","tables/menu_v1","templates/menu_v1",
        ["show_menu","speak_menu"],["payment_capture"]),
    "draft_order": ("rules/draft_order_v1","tables/order_draft_v1","templates/draft_order_v1",
        ["create_draft_order","ask_human_confirmation"],
        ["formal_pos_order_without_human_review","payment_capture"]),
    "member_lookup_masked": ("rules/member_masked_v1","tables/member_masked_v1","templates/member_masked_v1",
        ["show_masked_member_status"],["show_member_plaintext","export_member_plaintext"]),
    "payment_request": ("rules/payment_human_review_v1","tables/payment_boundary_v1","templates/payment_hold_v1",
        ["ask_human_confirmation"],["payment_capture","auto_charge"]),
    "unknown": ("rules/unknown_v1","tables/fallback_v1","templates/clarify_v1",
        ["ask_clarifying_question"],["payment_capture","member_plaintext_read"]),
}

PAIRING = {
    ("not_bitter","tired"): ("拿鐵或低酸手沖","順口、不太苦","偵測到不苦與疲勞狀態"),
    ("refreshing","default"): ("淺焙手沖或冰美式","清爽","偵測到清爽偏好"),
    ("milky","default"): ("拿鐵","奶香、順口","偵測到奶類偏好"),
    ("default","default"): ("拿鐵或今日手沖","安全泛用","未取得明確偏好"),
}

def sha(x):
    if not isinstance(x, str):
        x = json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",",":"))
    return hashlib.sha256(x.encode()).hexdigest()

def pick_slots(text):
    out = {}
    q = text.lower()
    for k, mp in SLOTS.items():
        for v, words in mp.items():
            if any(w.lower() in q for w in words):
                out[k] = v
                break
    return out

def parse(text):
    q = text.lower()
    slots = pick_slots(q)
    if slots.get("risk_signal") == "payment":
        return "payment_request", slots, "L3"
    if slots.get("risk_signal") == "member_plaintext":
        return "member_lookup_masked", slots, "L3"
    scores = {k: sum(1 for w in ws if w.lower() in q) for k, ws in ALIASES.items()}
    intent = max(scores, key=scores.get)
    score = scores[intent]
    if score <= 0:
        return "unknown", slots, "L1"
    return intent, slots, "L3" if score > 1 else "L2"

def verify(intent, slots, confidence):
    risk = slots.get("risk_signal", "none")
    if risk == "member_plaintext":
        return risk, "BLOCK", ["member plaintext blocked"]
    if risk == "payment" or intent == "payment_request":
        return "payment", "HOLD", ["payment requires human confirmation"]
    if risk == "allergy":
        return risk, "HOLD", ["allergy or intolerance needs confirmation"]
    if intent == "draft_order":
        return "none", "HOLD", ["draft order requires counter confirmation"]
    if confidence == "L1":
        return "none", "HOLD", ["low intent confidence"]
    return "none", "ALLOW", ["verified"]

def language(intent, slots, decision, reasons):
    taste = slots.get("taste_preference","default")
    cond = slots.get("condition","default")
    rec, style, why = PAIRING.get((taste,cond)) or PAIRING.get((taste,"default")) or PAIRING[("default","default")]
    reason = "、".join(reasons)
    if intent == "recommend_order":
        if decision == "ALLOW":
            return f"今天可以先考慮{style}的選項，例如{rec}。原因是：{why}。"
        return f"我可以先幫你推薦{style}的選項，例如{rec}。但需要先確認：{reason}。"
    if intent == "payment_request":
        return "付款或結帳必須由櫃台人工確認；系統只產生候選提示，不會自動扣款。"
    if intent == "member_lookup_masked":
        return "會員明文資料不可由此流程讀取或顯示。"
    if intent == "draft_order":
        return "可以建立候選訂單草稿，但正式寫入 POS 前必須由櫃台確認。"
    if intent == "ask_menu":
        return "目前可以查詢菜單與可供應品項；不會觸發下單或付款。"
    return "目前意圖不明，先進入補問流程。"

def run(text, branch="cafe_main", actor="counter_ai", channel="counter_voice"):
    intent, slots, confidence = parse(text)
    risk, decision, reasons = verify(intent, slots, confidence)
    rule_ref, table_ref, template_ref, allowed, forbidden = ROUTES.get(intent, ROUTES["unknown"])
    now = int(time.time())
    packet = {
        "packet_type": "W7TP_8D_LOOKUP_AI_PACKET",
        "version": "v0.1",
        "D1_intent": {"intent_id": intent, "slots": slots, "confidence_level": confidence},
        "D2_state": {"state_refs": {"menu_ref":"branch.menu.current","member_ref":"masked_or_none"}},
        "D3_coordinate": {"branch": branch, "actor_role": actor, "channel": channel},
        "D4_evidence": {"input_hash": sha(text)},
        "D5_execution": {"allowed_actions": allowed, "forbidden_actions": forbidden},
        "D6_gt": {"rule_ref": rule_ref, "table_ref": table_ref, "template_ref": template_ref},
        "D7_risk": {"risk_code": risk, "decision": decision, "reasons": reasons},
        "D8_envelope": {"packet_id": "pkt_"+uuid.uuid4().hex, "ttl_seconds":300, "nonce":uuid.uuid4().hex, "created_at":now},
    }
    packet["D8_envelope"]["packet_hash"] = sha(packet)
    packet["D8_envelope"]["seal"] = sha(packet["D8_envelope"]["packet_hash"] + ":" + packet["D8_envelope"]["nonce"])
    return {
        "STATE": "PASS_W7TP_8D_LOOKUP_AI_MIN",
        "RUN_MODE": "MODEL_FREE_LOOKUP_PACKET_RECONSTRUCT",
        "SAFETY_FLAGS": SAFETY,
        "INPUT_TEXT_HASH": sha(text),
        "PACKET": packet,
        "VERIFIER": {"decision": decision, "reasons": reasons},
        "LANGUAGE_RECONSTRUCTION": {"zh_TW": language(intent, slots, decision, reasons)}
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    data = run(args.text)
    s = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
    print(s)
    if args.out:
        p = Path(args.out); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(s+"\n", encoding="utf-8")

if __name__ == "__main__":
    main()
