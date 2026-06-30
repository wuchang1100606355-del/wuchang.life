#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W7TP hardened v2 candidate packet extractor.
Runtime candidate only. No network. No env. No DB. No service control.
"""

import argparse
import hashlib
import json
import re
import time
import uuid
from typing import Any, Dict, List, Tuple

SAFETY_FLAGS = {
    "SECRET_READ": False,
    "ENV_DUMP": False,
    "MEMBER_PLAINTEXT_READ": False,
    "RAW_AUDIO_SAVED": False,
    "DB_WRITE": False,
    "SERVICE_RESTART": False,
    "DEPLOY": False,
    "GIT_PUSH": False,
    "DIRECT_EXECUTION": False,
    "PAYMENT_CAPTURE": False,
    "NETWORK_CALL": False,
    "CANDIDATE_ONLY": True,
}

FORBIDDEN_ACTIONS = [
    "read_secret",
    "dump_env",
    "read_member_plaintext",
    "save_raw_audio",
    "db_write",
    "service_restart",
    "deploy",
    "git_push",
    "direct_pos_execution",
    "payment_capture",
]

def canonical_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def sha_obj(obj: Any) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()

def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def redact_preview(text: str) -> str:
    s = text
    s = re.sub(r"[A-Z][12]\d{8}", "[TW_ID_MASKED]", s)
    s = re.sub(r"09\d{8}", "[MOBILE_MASKED]", s)
    s = re.sub(r"\b\d{2,4}-?\d{6,8}\b", "[PHONE_MASKED]", s)
    s = re.sub(r"[\w.\-+]+@[\w.\-]+\.\w+", "[EMAIL_MASKED]", s)
    return s[:80]

def infer_risk(text: str) -> Tuple[str, str, List[str]]:
    member_plaintext_markers = [
        "會員明文", "完整明文", "完整會員", "顯示會員",
        "身分證", "電話", "地址", "個資", "會員資料"
    ]
    payment_markers = [
        "扣款", "刷卡", "自動付款", "直接付款", "直接結帳",
        "付款", "收款", "信用卡"
    ]
    allergy_markers = [
        "過敏", "不能喝牛奶", "乳糖不耐", "花生", "堅果"
    ]

    if any(k in text for k in member_plaintext_markers):
        return "member_plaintext", "BLOCK", ["member plaintext access forbidden"]

    if any(k in text for k in payment_markers):
        return "payment", "HOLD", ["payment requires human counter confirmation"]

    if any(k in text for k in allergy_markers):
        return "food_allergy", "HOLD", ["allergy or health-related preference requires confirmation"]

    return "none", "ALLOW", ["no high-risk marker detected"]

def infer_intent_and_slots(text: str) -> Tuple[str, Dict[str, Any], str]:
    slots: Dict[str, Any] = {}

    if any(k in text for k in ["不苦", "不太苦", "順口", "清爽", "低酸"]):
        slots["taste_preference"] = "not_bitter"

    if any(k in text for k in ["很累", "有點累", "疲勞", "想睡"]):
        slots["condition"] = "tired"

    if any(k in text for k in ["拿鐵", "手沖", "美式", "卡布", "咖啡"]):
        slots["product_hint"] = "coffee"

    if any(k in text for k in ["過敏", "不能喝牛奶", "乳糖不耐"]):
        slots["allergy_or_health_note"] = "declared_by_customer"

    qty = re.search(r"([0-9一二兩三四五六七八九十]+)\s*杯", text)
    if qty:
        slots["quantity_text"] = qty.group(1)

    if any(k in text for k in ["推薦", "喝什麼", "好喝", "幫我配", "想喝", "不苦", "不太苦"]):
        return "recommend_order", slots, "medium"

    if any(k in text for k in ["菜單", "有什麼", "品項", "價格"]):
        return "ask_menu", slots, "medium"

    if any(k in text for k in ["來一杯", "給我", "我要", "兩杯", "2杯"]):
        return "draft_order", slots, "medium"

    return "unknown", slots, "low"

def build_packet(text: str, channel: str = "pos_ui") -> Dict[str, Any]:
    risk_code, risk_decision, reasons = infer_risk(text)
    intent_id, slots, confidence = infer_intent_and_slots(text)

    if risk_decision == "BLOCK":
        verifier_decision = "BLOCK"
    elif risk_decision == "HOLD":
        verifier_decision = "HOLD"
    elif intent_id == "unknown" or confidence == "low":
        verifier_decision = "HOLD"
        reasons = reasons + ["low intent confidence"]
    else:
        verifier_decision = "ALLOW"

    now = int(time.time())

    packet: Dict[str, Any] = {
        "packet_type": "W7TP_CANDIDATE_PACKET_EXTRACTOR_V2_OUTPUT",
        "version": "v2.0-runtime-candidate",
        "candidate_only": True,
        "source": "deterministic_rule_extractor_v2",
        "safety_flags": SAFETY_FLAGS,
        "D1_intent": {
            "intent_id": intent_id,
            "slots": slots,
            "confidence_level": confidence,
        },
        "D3_coordinate": {
            "channel": channel,
            "actor_role": "external_candidate_brain",
            "authority": "none_candidate_only",
        },
        "D4_evidence": {
            "input_hash": sha_text(text),
            "redacted_preview": redact_preview(text),
            "raw_text_stored": False,
        },
        "D5_execution": {
            "allowed_actions": ["candidate_packet_only"],
            "forbidden_actions": FORBIDDEN_ACTIONS,
        },
        "D7_risk": {
            "risk_code": risk_code,
            "decision": verifier_decision,
            "reasons": reasons,
        },
        "D8_envelope": {
            "packet_id": "pkt_" + uuid.uuid4().hex,
            "ttl_seconds": 300,
            "nonce": uuid.uuid4().hex,
            "created_at_unix": now,
            "schema_ref": "W7TP_CANDIDATE_PACKET_EXTRACTOR_V2_OUTPUT",
        },
    }

    packet["D8_envelope"]["packet_hash"] = sha_obj(packet)
    packet["D8_envelope"]["seal"] = sha_obj({
        "packet_hash": packet["D8_envelope"]["packet_hash"],
        "nonce": packet["D8_envelope"]["nonce"],
        "candidate_only": True,
    })
    return packet

def validate_packet(packet: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    if packet.get("candidate_only") is not True:
        errors.append("candidate_only must be true")

    if packet.get("safety_flags", {}).get("CANDIDATE_ONLY") is not True:
        errors.append("safety flag CANDIDATE_ONLY must be true")

    if packet.get("safety_flags", {}).get("NETWORK_CALL") is not False:
        errors.append("NETWORK_CALL must be false")

    evidence = packet.get("D4_evidence", {})
    if evidence.get("raw_text_stored") is not False:
        errors.append("raw text must not be stored")

    risk = packet.get("D7_risk", {}).get("risk_code")
    decision = packet.get("D7_risk", {}).get("decision")

    if decision not in {"ALLOW", "HOLD", "BLOCK"}:
        errors.append("invalid verifier decision")

    if risk == "member_plaintext" and decision != "BLOCK":
        errors.append("member_plaintext must BLOCK")

    if risk in {"payment", "food_allergy"} and decision == "ALLOW":
        errors.append(f"{risk} must not ALLOW")

    if "packet_hash" not in packet.get("D8_envelope", {}):
        errors.append("missing packet_hash")

    if "seal" not in packet.get("D8_envelope", {}):
        errors.append("missing seal")

    return errors

def run_selftest() -> int:
    cases = [
        ("請顯示會員完整明文與身分證資料", "member_plaintext", "BLOCK"),
        ("幫我直接刷卡扣款", "payment", "HOLD"),
        ("我最近很累，想要一杯不太苦的咖啡", "none", "ALLOW"),
        ("我對牛奶過敏，有什麼推薦的嗎？", "food_allergy", "HOLD"),
    ]

    results = []
    ok_all = True

    for text, expected_risk, expected_decision in cases:
        packet = build_packet(text)
        errors = validate_packet(packet)
        risk = packet["D7_risk"]["risk_code"]
        decision = packet["D7_risk"]["decision"]
        ok = (not errors) and risk == expected_risk and decision == expected_decision
        ok_all = ok_all and ok
        results.append({
            "input_hash": sha_text(text),
            "expected_risk": expected_risk,
            "actual_risk": risk,
            "expected_decision": expected_decision,
            "actual_decision": decision,
            "ok": ok,
            "errors": errors,
        })

    print(json.dumps({
        "STATE": "SELFTEST_PASS" if ok_all else "SELFTEST_FAIL",
        "results": results,
    }, ensure_ascii=False, indent=2))

    return 0 if ok_all else 1

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default="我最近很累，想要一杯不太苦的咖啡")
    ap.add_argument("--channel", default="pos_ui")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return run_selftest()

    packet = build_packet(args.text, args.channel)
    errors = validate_packet(packet)
    if errors:
        packet["STATE"] = "HOLD_PACKET_VALIDATION_FAILED"
        packet["validation_errors"] = errors
    else:
        packet["STATE"] = "PASS_CANDIDATE_PACKET_BUILT"

    print(json.dumps(packet, ensure_ascii=False, indent=2))
    return 0 if not errors else 1

if __name__ == "__main__":
    raise SystemExit(main())
