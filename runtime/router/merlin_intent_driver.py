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
    "lan_dns_direct_plan": {
        "risk": "high",
        "summary": "Plan direct router LAN and router-DNS service for taiji02, taiji03, and taiji04 without a transit node",
        "steps": [
            "Verify each node has its own router DHCP reservation and uses the router as its DNS server.",
            "Reject exit-node, subnet-router, policy-route, or gateway settings that make one client transit through another client.",
            "Preserve ordinary direct LAN paths while remote VPN remains a separate router-hosted entry.",
            "Reobserve node-to-router, node-to-node, DNS, default route, and throughput after any separately authorized change."
        ],
        "allowed_actions": ["draft_plan", "pending_review"]
    },
    "wireguard_dual_stack_plan": {
        "risk": "high",
        "summary": "Plan RT-BE86U WireGuard server on fixed public IPv4 with IPv4 and IPv6 client transport, router DNS, and LAN access",
        "steps": [
            "Capture a redacted preimage of current WireGuard, WAN IPv4, native IPv6, DNS, LAN-access, and listener state.",
            "Keep private keys and preshared keys on the router or in owner-only client profiles; never print them.",
            "Prepare UDP 51820, router DNS, LAN access, native IPv6/NAT6, and one peer without exposing the router admin surface to WAN.",
            "Apply only after a short-lived single-use D8 scope binds the exact target, preimage, mutation, rollback, and verification rules.",
            "Verify external IPv4, IPv6, DNS, LAN access, listener, and rollback before any VPN cutover."
        ],
        "allowed_actions": ["draft_plan", "pending_review"]
    },
    "wireguard_peer_plan": {
        "risk": "high",
        "summary": "Plan one individually named WireGuard peer without sharing private key material",
        "steps": [
            "Select one unused router peer slot and one non-conflicting tunnel address.",
            "Generate peer key material in a protected execution boundary and never store it in the repository or model output.",
            "Bind exactly one device profile, allowed addresses, router DNS, LAN access, and keepalive policy.",
            "Reobserve that peer only; do not bulk-edit other peers."
        ],
        "allowed_actions": ["draft_plan", "pending_review"]
    },
    "wireguard_cutover_plan": {
        "risk": "high",
        "summary": "Plan cutover from Tailscale fallback only after router WireGuard dual-stack verification",
        "steps": [
            "Require PASS evidence for external IPv4, IPv6, router DNS, LAN access, and recovery access through WireGuard.",
            "Record current Tailscale state as rollback evidence.",
            "Disable only the exact approved Tailscale target; do not uninstall or erase node identity.",
            "Reobserve every registered node and immediately roll back if management reachability fails."
        ],
        "allowed_actions": ["draft_plan", "pending_review"]
    },
    "wireguard_disable_plan": {
        "risk": "high",
        "summary": "Plan disabling router WireGuard while preserving recovery access and evidence",
        "steps": [
            "Verify an independent recovery path before disabling the WireGuard server.",
            "Capture a redacted preimage and peer-slot inventory without secret material.",
            "Disable only the WireGuard server service; do not erase keys, peers, logs, or unrelated VPN state unless separately authorized.",
            "Reobserve LAN, WAN, DNS, IPv6, and management access."
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
