#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify W7TP packet-as-inference runtime locally."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.w7tp_packet_inference_runtime import SAFETY_FLAGS, run


def fail(message: str) -> None:
    print(f"FAIL={message}")
    print("STATE=HOLD_VERIFY_W7TP_PACKET_INFERENCE_RUNTIME")
    raise SystemExit(1)


def check(condition: bool, name: str) -> None:
    print(f"{name}={'PASS' if condition else 'FAIL'}")
    if not condition:
        fail(name)


def packet_intent(result: dict) -> str:
    return result["PACKET_CHAIN"][1]["D1_intent"]["intent_id"]


def forbidden_actions(result: dict) -> list[str]:
    return result["PACKET_CHAIN"][5]["D5_execution"]["forbidden_actions"]


def verify_case(name: str, text: str, expected_intent: set[str], expected_decision: set[str]) -> dict:
    result = run(text)
    final = result["FINAL_VERIFIER"]["decision"]
    intent = packet_intent(result)
    check(result["STATE"] == "PASS_W7TP_PACKET_INFERENCE_RUNTIME", f"{name}_STATE")
    check(result["RUN_MODE"] == "MODEL_FREE_PACKET_BY_PACKET_INFERENCE", f"{name}_RUN_MODE")
    check(all(value is False for value in result["SAFETY_FLAGS"].values()), f"{name}_SAFETY_FLAGS_FALSE")
    check(len(result["PACKET_CHAIN"]) == 8, f"{name}_EIGHT_PACKET_CHAIN")
    check(intent in expected_intent, f"{name}_INTENT")
    check(final in expected_decision, f"{name}_FINAL_DECISION")
    check(result["PACKET_CHAIN"][0]["parent_packet_hash"] is None, f"{name}_ROOT_PARENT_NULL")
    for index, packet in enumerate(result["PACKET_CHAIN"][1:], start=1):
        expected_parent = result["PACKET_CHAIN"][index - 1]["D8_envelope"]["packet_hash"]
        check(packet["parent_packet_hash"] == expected_parent, f"{name}_PARENT_HASH_{index}")
    return result


def main() -> int:
    cases = [
        ("RECOMMEND", "我今天有點累，想喝不太苦的，幫我推薦", {"recommend_order"}, {"ALLOW", "HOLD"}),
        ("PAYMENT", "幫我直接結帳付款", {"payment_request"}, {"HOLD"}),
        ("MEMBER", "我要查會員完整電話和地址", {"member_lookup_masked", "member_plaintext_request"}, {"BLOCK"}),
        ("ALLERGY", "我對牛奶有點敏感，想喝順口的", {"recommend_order"}, {"HOLD"}),
        ("UNKNOWN", "xqz-??-000", {"unknown"}, {"HOLD"}),
        ("PROFILE", "你沒有我的資訊嗎", {"profile_existence_query"}, {"ALLOW", "HOLD"}),
        ("CLAIMED_IDENTITY", "我是創辦人江政隆你認識我嗎", {"claimed_identity_query"}, {"HOLD"}),
        ("ROLE", "我的角色是什麼", {"role_query"}, {"HOLD"}),
    ]
    results = [verify_case(*case) for case in cases]

    payment_result = results[1]
    check("payment_capture" in forbidden_actions(payment_result), "PAYMENT_CAPTURE_FORBIDDEN")
    check(payment_result["SAFETY_FLAGS"]["PAYMENT_CAPTURE"] is False, "PAYMENT_CAPTURE_FALSE")
    check(results[2]["SAFETY_FLAGS"]["MEMBER_PLAINTEXT_READ"] is False, "MEMBER_PLAINTEXT_READ_FALSE")
    check(results[3]["PACKET_CHAIN"][4]["D7_risk"]["risk_code"] == "allergy", "ALLERGY_RISK_CODE")
    check(results[5]["SAFETY_FLAGS"]["MEMBER_PLAINTEXT_READ"] is False, "PROFILE_MEMBER_PLAINTEXT_READ_FALSE")
    check(results[6]["PACKET_CHAIN"][1]["D4_evidence"]["claimed_identity_packet"]["packet_type"] == "CLAIMED_IDENTITY_PACKET", "CLAIMED_IDENTITY_PACKET_PRESENT")
    check(results[6]["PACKET_CHAIN"][1]["D4_evidence"]["claimed_identity_packet"]["accepted_as_truth"] is False, "CLAIMED_IDENTITY_NOT_TRUSTED")
    check("member_plaintext_read" in results[7]["PACKET_CHAIN"][5]["D5_execution"]["forbidden_actions"], "ROLE_MEMBER_PLAINTEXT_FORBIDDEN")
    check(SAFETY_FLAGS["EXTERNAL_API_CALL"] is False, "EXTERNAL_API_CALL_FALSE")
    check(SAFETY_FLAGS["MODEL_REQUIRED"] is False, "MODEL_REQUIRED_FALSE")
    check(SAFETY_FLAGS["LLM_AUTHORITY"] is False, "LLM_AUTHORITY_FALSE")

    run_id = time.strftime("%Y%m%d_%H%M%S")
    report_dir = ROOT / "runtime" / "total_field" / "packet_inference" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "STATE": "PASS_VERIFY_W7TP_PACKET_INFERENCE_RUNTIME",
        "RUN_ID": run_id,
        "cases": [
            {
                "input_hash": result["INPUT_TEXT_HASH"],
                "intent": packet_intent(result),
                "decision": result["FINAL_VERIFIER"]["decision"],
                "packet_count": len(result["PACKET_CHAIN"]),
            }
            for result in results
        ],
        "safety_flags": SAFETY_FLAGS,
    }
    (report_dir / "VERIFY_REPORT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"VERIFY_REPORT={report_dir / 'VERIFY_REPORT.json'}")
    print("STATE=PASS_VERIFY_W7TP_PACKET_INFERENCE_RUNTIME")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
