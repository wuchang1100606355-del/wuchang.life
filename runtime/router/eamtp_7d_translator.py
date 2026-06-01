#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EAMTP-7D translator
Internal canonical intent-state packet builder for XiaoJ intent field.

Safe boundary:
- This module builds packets only.
- It does not execute shell commands.
- It does not write Odoo DB.
- It does not call cloud APIs.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import uuid
from typing import Any, Dict, List


VERSION = "EAMTP-7D/0.1"
FIELD = "xiaoj_intent_field"


def _utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _hash_packet(packet: Dict[str, Any]) -> str:
    clone = json.loads(json.dumps(packet, ensure_ascii=False, sort_keys=True))
    clone.setdefault("ledger", {})["hash"] = ""
    raw = json.dumps(clone, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def infer_risk(intent_type: str, text: str) -> str:
    t = (text or "").lower()
    high_terms = [
        "delete", "刪除", "付款", "payment", "pay",
        "token", "api key", "private key", "password", "credential",
        "ssh", "sudo", "docker run", "部署", "正式庫", "db write",
        "法律", "合約", "公開發文", "公告"
    ]
    if any(x in t for x in high_terms):
        return "high"
    if intent_type in {"execute", "memory_update"}:
        return "medium"
    return "low"


def build_packet(
    summary: str,
    intent_type: str = "plan",
    actor_type: str = "admin",
    auth_level: str = "privileged",
    entry: str = "local",
    source_field: str = "local_ops",
    target_field: str = "router",
    privacy_level: str = "redacted",
    consent_state: str = "system",
    cloud_allowed: bool = False,
    preferred_lane: str = "local",
    latency_class: str = "normal",
    cost_policy: str = "balanced",
    allowed_actions: List[str] | None = None,
) -> Dict[str, Any]:
    allowed_actions = allowed_actions or ["answer", "summarize", "draft_plan"]
    risk_level = infer_risk(intent_type, summary)
    requires_review = risk_level in {"medium", "high", "critical"} or intent_type in {"execute", "memory_update"}

    packet: Dict[str, Any] = {
        "eamtp_version": VERSION,
        "packet_id": "eamtp_" + _dt.datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8],
        "field": FIELD,
        "d1_identity_role": {
            "actor_type": actor_type,
            "auth_level": auth_level,
            "sovereignty_proxy": True
        },
        "d2_intent": {
            "intent_type": intent_type,
            "summary": summary,
            "user_visible_goal": summary[:240]
        },
        "d3_context_topology": {
            "entry": entry,
            "source_field": source_field,
            "target_field": target_field
        },
        "d4_privacy_consent": {
            "privacy_level": privacy_level,
            "consent_state": consent_state,
            "cloud_allowed": cloud_allowed
        },
        "d5_risk_governance": {
            "risk_level": risk_level,
            "requires_human_review": requires_review,
            "dead_letter_on_violation": True,
            "forbidden_actions": [
                "credential_read",
                "direct_db_write",
                "delete",
                "payment",
                "ssh",
                "sudo",
                "docker_run",
                "policy_override"
            ]
        },
        "d6_resource_cost": {
            "preferred_lane": preferred_lane,
            "latency_class": latency_class,
            "cost_policy": cost_policy
        },
        "d7_action_state": {
            "state": "received",
            "allowed_actions": allowed_actions,
            "result_capsule": None
        },
        "ledger": {
            "hash": "",
            "created_at": _utc_now(),
            "review_required": requires_review
        }
    }

    packet["ledger"]["hash"] = _hash_packet(packet)
    return packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", required=True)
    parser.add_argument("--intent-type", default="plan")
    parser.add_argument("--entry", default="local")
    parser.add_argument("--source-field", default="local_ops")
    parser.add_argument("--target-field", default="router")
    parser.add_argument("--cloud-allowed", action="store_true")
    args = parser.parse_args()

    pkt = build_packet(
        summary=args.summary,
        intent_type=args.intent_type,
        entry=args.entry,
        source_field=args.source_field,
        target_field=args.target_field,
        cloud_allowed=args.cloud_allowed,
    )
    print(json.dumps(pkt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
