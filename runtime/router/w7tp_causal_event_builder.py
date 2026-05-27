#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W7TP Causal Event Builder

Plan-only causal event packet builder for XiaoJ / W7TP.

Safety:
- no blockchain execution
- no financial settlement
- no Odoo/Postgres write
- no cloud upload
- no credential access
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import uuid
from typing import Any, Dict, List


VERSION = "W7TP-CAUSAL-EVENT/0.1"


HARDWALL_TERMS = {
    "double spend": "double_spend_causal_conflict",
    "雙重支付": "double_spend_causal_conflict",
    "lww balance": "unsafe_lww_balance_merge",
    "最後寫入者勝出": "unsafe_lww_merge",
    "forged vector clock": "forged_vector_clock",
    "偽造向量時鐘": "forged_vector_clock",
    "parent set mutation": "parent_set_mutation",
    "父節點竄改": "parent_set_mutation",
    "raw pii to cloud": "raw_pii_to_cloud",
    "個資上雲": "raw_pii_to_cloud",
    "unsigned financial delta": "unsigned_financial_delta",
    "未簽章金融": "unsigned_financial_delta",
    "spv-only security decision": "spv_only_high_risk_decision"
}

HIGH_RISK_TERMS = {
    "crdt": "crdt_merge_requires_review",
    "vector clock": "clock_logic_requires_review",
    "compressed clock": "compressed_clock_requires_review",
    "coprime": "coprime_clock_requires_review",
    "因果": "causal_event_requires_review",
    "odoo": "odoo_event_requires_review",
    "pos": "pos_event_requires_review",
    "member": "member_event_requires_review",
    "merlin": "merlin_event_requires_review",
    "ledger": "ledger_event_requires_review"
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_obj(obj: Dict[str, Any]) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def classify(summary: str, privacy_level: str, event_type: str) -> Dict[str, Any]:
    text = (summary or "").lower()
    reasons: List[str] = []

    for term, reason in HARDWALL_TERMS.items():
        if term.lower() in text:
            reasons.append(reason)

    if privacy_level in {"pii", "sensitive"}:
        reasons.append("pii_or_sensitive_requires_review")

    if reasons:
        return {
            "level": "critical" if any("raw_pii" in r or "double_spend" in r or "forged" in r for r in reasons) else "high",
            "decision": "dead_letter",
            "reasons": reasons,
            "human_review_required": True
        }

    for term, reason in HIGH_RISK_TERMS.items():
        if term.lower() in text:
            reasons.append(reason)

    if event_type in {"odoo_event", "pos_event", "member_consent", "merlin_ticket", "execution_result", "ha_mesh_job"}:
        reasons.append(f"{event_type}_requires_review")

    if reasons:
        return {
            "level": "high",
            "decision": "pending_review",
            "reasons": sorted(set(reasons)),
            "human_review_required": True
        }

    return {
        "level": "low",
        "decision": "allow_low_risk",
        "reasons": ["low_risk_causal_metadata_only"],
        "human_review_required": False
    }


def build_packet(
    event_type: str,
    source_field: str,
    summary: str,
    parent_event_hashes: List[str] | None = None,
    privacy_level: str = "redacted",
    cloud_allowed: bool = False,
    clock_mode: str = "none",
    crdt_mode: str = "none"
) -> Dict[str, Any]:
    parent_event_hashes = parent_event_hashes or []
    c = classify(summary, privacy_level, event_type)

    pkt: Dict[str, Any] = {
        "packet_version": VERSION,
        "event_id": "causal_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8],
        "event_type": event_type,
        "source_field": source_field,
        "causal": {
            "parent_event_hashes": parent_event_hashes,
            "clock_mode": clock_mode,
            "clock_payload_redacted": True,
            "dag_append_only": True,
            "crdt_mode": crdt_mode,
            "summary_redacted": summary[:500]
        },
        "privacy": {
            "level": privacy_level,
            "cloud_allowed": cloud_allowed
        },
        "risk": {
            "level": c["level"],
            "reasons": c["reasons"]
        },
        "policy": {
            "decision": c["decision"],
            "human_review_required": c["human_review_required"],
            "dead_letter_on_violation": True
        },
        "ledger": {
            "created_at": utc_now(),
            "event_hash": "",
            "append_only": True
        }
    }

    if pkt["privacy"]["level"] in {"pii", "sensitive"} and pkt["privacy"]["cloud_allowed"]:
        pkt["risk"]["level"] = "critical"
        pkt["risk"]["reasons"].append("pii_cloud_not_allowed")
        pkt["policy"]["decision"] = "dead_letter"
        pkt["policy"]["human_review_required"] = True

    pkt["ledger"]["event_hash"] = sha256_obj(pkt)
    return pkt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-type", default="causal_audit")
    parser.add_argument("--source-field", default="xiaoj_intent_field")
    parser.add_argument("--summary", required=True)
    parser.add_argument("--parent", action="append", default=[])
    parser.add_argument("--privacy-level", default="redacted")
    parser.add_argument("--cloud-allowed", action="store_true")
    parser.add_argument("--clock-mode", default="none")
    parser.add_argument("--crdt-mode", default="none")
    args = parser.parse_args()

    pkt = build_packet(
        event_type=args.event_type,
        source_field=args.source_field,
        summary=args.summary,
        parent_event_hashes=args.parent,
        privacy_level=args.privacy_level,
        cloud_allowed=args.cloud_allowed,
        clock_mode=args.clock_mode,
        crdt_mode=args.crdt_mode,
    )

    print(json.dumps(pkt, ensure_ascii=False, indent=2))
    return 0 if pkt["policy"]["decision"] != "dead_letter" else 2


if __name__ == "__main__":
    raise SystemExit(main())
