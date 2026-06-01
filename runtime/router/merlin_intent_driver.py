#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Merlin Intent Driver - Plan Only

This module converts XiaoJ/W7TP intent into a router governance plan.

Safety:
- no SSH login
- no router API call
- no firmware change
- no reboot
- no nvram write
- no firewall change
- no credential storage
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.router.eamtp_7d_translator import build_packet
from runtime.dead_letter.eamtp_policy_gate import check_packet


OUT_DIR = ROOT / "runtime" / "merlin_intent_driver"


CATALOG: Dict[str, Dict[str, Any]] = {
    "observe_status": {
        "risk": "low",
        "summary": "Read-only router status observation plan",
        "steps": [
            "Collect non-sensitive router status from UI or approved read-only channel.",
            "Record LAN/WAN/VPN/guest-network field summary.",
            "Convert network status into EAMTP-7D context packet.",
            "Do not collect password, token, private key, or raw resident data."
        ],
        "allowed_actions": ["draft_plan", "summarize", "answer"]
    },
    "ssh_hardening_plan": {
        "risk": "high",
        "summary": "Plan to reduce router SSH exposure and harden management surface",
        "steps": [
            "Review whether SSH is exposed to WAN.",
            "Prefer LAN/VPN-only SSH administration.",
            "Disable password login if key-based administration is ready.",
            "Disable SSH port forwarding unless there is a documented need.",
            "Record final changes as pending_review before any apply."
        ],
        "allowed_actions": ["draft_plan", "pending_review"]
    },
    "guest_network_design_plan": {
        "risk": "medium",
        "summary": "Plan guest network isolation for members, visitors, merchants, and devices",
        "steps": [
            "Separate trusted LAN, guest WiFi, merchant device field, and IoT field.",
            "Do not treat WiFi connection as identity proof.",
            "Route member-specific services through login or VPN.",
            "Send network class into EAMTP-7D as weak context signal only."
        ],
        "allowed_actions": ["draft_plan", "summarize"]
    },
    "vpn_member_access_plan": {
        "risk": "high",
        "summary": "Plan VPN-based member access without exposing core services to WAN",
        "steps": [
            "Use VPN as controlled entry for remote members or admin.",
            "Do not expose MSI local core services directly to WAN.",
            "Route external requests to taiji01 or VPN gateway first.",
            "Send only redacted EAMTP packets to cloud lanes."
        ],
        "allowed_actions": ["draft_plan", "pending_review"]
    },
    "qos_xiaoj_priority_plan": {
        "risk": "medium",
        "summary": "Plan QoS priority for XiaoJ local service, Odoo, Open WebUI, and VPN",
        "steps": [
            "Identify XiaoJ service ports and host devices.",
            "Prioritize essential service traffic over bulk traffic.",
            "Do not degrade resident emergency or communication traffic.",
            "Record QoS plan for human review before router apply."
        ],
        "allowed_actions": ["draft_plan", "summarize"]
    },
    "emergency_lockdown_plan": {
        "risk": "high",
        "summary": "Plan emergency network lockdown without destroying evidence",
        "steps": [
            "Preserve logs and evidence before any blocking action.",
            "Block only clearly defined suspicious path, not entire system.",
            "Do not wipe logs or erase traces.",
            "Escalate to human review before permanent firewall changes."
        ],
        "allowed_actions": ["draft_plan", "pending_review"]
    },
    "disable_firewall": {
        "risk": "critical",
        "summary": "Hardwall violation: disabling firewall is forbidden",
        "steps": [
            "Reject intent.",
            "Route to dead_letter.",
            "Do not produce executable router command."
        ],
        "allowed_actions": ["dead_letter"]
    },
    "open_unrestricted_wan_ssh": {
        "risk": "critical",
        "summary": "Hardwall violation: unrestricted WAN SSH exposure is forbidden",
        "steps": [
            "Reject intent.",
            "Route to dead_letter.",
            "Suggest VPN/LAN-only management instead."
        ],
        "allowed_actions": ["dead_letter"]
    },
    "export_router_password": {
        "risk": "critical",
        "summary": "Hardwall violation: credential export is forbidden",
        "steps": [
            "Reject credential access.",
            "Route to dead_letter.",
            "Never store router credentials in repo or model memory."
        ],
        "allowed_actions": ["dead_letter"]
    }
}


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def sha256_obj(obj: Dict[str, Any]) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")


def build_merlin_plan(intent: str, note: str = "") -> Dict[str, Any]:
    item = CATALOG.get(intent)
    if not item:
        item = {
            "risk": "medium",
            "summary": f"Unknown Merlin intent requires review: {intent}",
            "steps": [
                "Unknown router intent.",
                "Do not execute.",
                "Send to pending_review for human clarification."
            ],
            "allowed_actions": ["draft_plan", "pending_review"]
        }

    eamtp_summary = f"Merlin router intent: {intent}. {item['summary']}. {note}".strip()

    pkt = build_packet(
        summary=eamtp_summary,
        intent_type="plan" if item["risk"] in {"low", "medium"} else "execute",
        actor_type="admin",
        auth_level="privileged",
        entry="local",
        source_field="local_ops",
        target_field="router",
        privacy_level="redacted",
        consent_state="system",
        cloud_allowed=False,
        preferred_lane="local",
        latency_class="normal",
        cost_policy="balanced",
        allowed_actions=item["allowed_actions"],
    )

    decision, reasons = check_packet(pkt)

    if item["risk"] == "critical":
        decision = "dead_letter"
        reasons = ["merlin_hardwall_intent:" + intent]

    if item["risk"] == "high" and decision == "allow_low_risk":
        decision = "pending_review"
        reasons = ["router_high_risk_requires_human_review"]

    if item["risk"] == "medium" and decision == "allow_low_risk":
        decision = "pending_review"
        reasons = ["router_medium_risk_requires_review_before_apply"]

    plan = {
        "driver": "merlin_intent_driver",
        "mode": "plan_only",
        "created_at": utc_now(),
        "intent": intent,
        "risk": item["risk"],
        "decision": decision,
        "reasons": reasons,
        "summary": item["summary"],
        "steps": item["steps"],
        "eamtp_packet_id": pkt.get("packet_id"),
        "eamtp_packet_hash": sha256_obj(pkt),
        "eamtp_packet": pkt,
        "safety": {
            "no_router_login": True,
            "no_ssh": True,
            "no_nvram_write": True,
            "no_firmware_change": True,
            "no_reboot": True,
            "no_firewall_change": True,
            "no_credential_storage": True
        }
    }
    plan["plan_hash"] = sha256_obj(plan)
    return plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--intent", required=True, choices=sorted(CATALOG.keys()))
    parser.add_argument("--note", default="")
    parser.add_argument("--list-intents", action="store_true")
    args = parser.parse_args()

    plan = build_merlin_plan(args.intent, args.note)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    append_jsonl(OUT_DIR / "merlin_intent_driver_plan_only.jsonl", plan)

    decision = plan["decision"]
    if decision == "allow_low_risk":
        append_jsonl(OUT_DIR / "allow_low_risk_router_plan.jsonl", plan)
    elif decision == "pending_review":
        append_jsonl(OUT_DIR / "pending_review_router_plan.jsonl", plan)
    elif decision == "dead_letter":
        append_jsonl(OUT_DIR / "dead_letter_router_plan.jsonl", plan)
    else:
        append_jsonl(OUT_DIR / "unknown_router_plan.jsonl", plan)

    print(json.dumps({
        "intent": plan["intent"],
        "risk": plan["risk"],
        "decision": plan["decision"],
        "reasons": plan["reasons"],
        "plan_hash": plan["plan_hash"],
        "mode": "plan_only",
        "store": str(OUT_DIR)
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
