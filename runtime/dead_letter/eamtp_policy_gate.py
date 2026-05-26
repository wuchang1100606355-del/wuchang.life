#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EAMTP-7D policy gate
Checks whether a packet must be completed, pending review, or dead-lettered.

Safe boundary:
- This module validates and classifies.
- It does not execute packet actions.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Tuple


REQUIRED_TOP = [
    "eamtp_version",
    "packet_id",
    "field",
    "d1_identity_role",
    "d2_intent",
    "d3_context_topology",
    "d4_privacy_consent",
    "d5_risk_governance",
    "d6_resource_cost",
    "d7_action_state",
    "ledger",
]

CRITICAL_FORBIDDEN = {
    "credential_read",
    "private_key_read",
    "api_key_read",
    "token_export",
    "direct_db_write",
    "delete",
    "payment",
    "ssh",
    "sudo",
    "docker_run",
    "policy_override",
    "raw_pii_to_cloud",
}

HARDWALL_INTENT_TERMS = {
    "api key",
    "apikey",
    "token",
    "private key",
    "password",
    "credential",
    "credentials",
    "secret",
    "正式資料庫",
    "正式庫",
    "direct db write",
    "db write",
    "delete",
    "刪除資料",
    "付款",
    "payment",
    "ssh",
    "sudo",
    "docker run",
    "raw pii",
    "個資上雲",
    "輸出金鑰",
    "讀取金鑰",
}


def check_packet(packet: Dict[str, Any]) -> Tuple[str, List[str]]:
    reasons: List[str] = []

    for k in REQUIRED_TOP:
        if k not in packet:
            reasons.append(f"missing_required:{k}")

    if reasons:
        return "dead_letter", reasons

    if packet.get("eamtp_version") != "EAMTP-7D/0.1":
        reasons.append("unsupported_version")

    if packet.get("field") != "xiaoj_intent_field":
        reasons.append("wrong_field")

    privacy = packet["d4_privacy_consent"].get("privacy_level")
    cloud_allowed = bool(packet["d4_privacy_consent"].get("cloud_allowed"))
    risk = packet["d5_risk_governance"].get("risk_level")
    requires_review = bool(packet["d5_risk_governance"].get("requires_human_review"))
    preferred_lane = packet["d6_resource_cost"].get("preferred_lane")
    allowed_actions = set(packet["d7_action_state"].get("allowed_actions") or [])
    forbidden_actions = set(packet["d5_risk_governance"].get("forbidden_actions") or [])

    if privacy in {"pii", "sensitive"} and cloud_allowed:
        reasons.append("pii_or_sensitive_cloud_not_allowed")

    if preferred_lane == "cloud_redacted" and privacy not in {"public", "redacted"}:
        reasons.append("cloud_lane_requires_public_or_redacted")

    intent_text = " ".join([
        str(packet.get("d2_intent", {}).get("summary", "")),
        str(packet.get("d2_intent", {}).get("user_visible_goal", "")),
        str(packet.get("d2_intent", {}).get("intent_type", "")),
    ]).lower()

    hardwall_hits = sorted(term for term in HARDWALL_INTENT_TERMS if term.lower() in intent_text)
    if hardwall_hits:
        reasons.append("hardwall_intent_detected:" + ",".join(hardwall_hits))

    dangerous_overlap = sorted(allowed_actions & CRITICAL_FORBIDDEN)
    if dangerous_overlap:
        reasons.append("allowed_actions_contains_forbidden:" + ",".join(dangerous_overlap))

    if not forbidden_actions:
        reasons.append("forbidden_actions_empty")

    if risk in {"high", "critical"} and not requires_review:
        reasons.append("high_risk_requires_human_review")

    if any(r.startswith("missing_required") for r in reasons):
        return "dead_letter", reasons

    hard_dead = {
        "unsupported_version",
        "wrong_field",
        "pii_or_sensitive_cloud_not_allowed",
        "cloud_lane_requires_public_or_redacted",
    }
    if any(
        r in hard_dead
        or r.startswith("allowed_actions_contains_forbidden")
        or r.startswith("hardwall_intent_detected")
        for r in reasons
    ):
        return "dead_letter", reasons

    if requires_review or risk in {"medium", "high", "critical"}:
        if reasons:
            return "dead_letter", reasons
        return "pending_review", ["human_review_required"]

    if reasons:
        return "dead_letter", reasons

    return "allow_low_risk", ["low_risk_auto_reply_allowed"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet_json", nargs="?", help="packet json file; stdin if omitted")
    args = parser.parse_args()

    try:
        if args.packet_json:
            with open(args.packet_json, "r", encoding="utf-8") as f:
                packet = json.load(f)
        else:
            packet = json.load(sys.stdin)
    except Exception as e:
        print(json.dumps({"decision": "dead_letter", "reasons": [f"json_load_error:{e}"]}, ensure_ascii=False, indent=2))
        return 2

    decision, reasons = check_packet(packet)
    print(json.dumps({"decision": decision, "reasons": reasons}, ensure_ascii=False, indent=2))
    return 0 if decision != "dead_letter" else 1


if __name__ == "__main__":
    raise SystemExit(main())
