#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EAMTP Router Guard Dry-Run

Shadow router guard for XiaoJ / W7TP intent field.

Safety boundary:
- No service restart.
- No live traffic interception.
- No shell execution.
- No DB write.
- No cloud API call.
- No production memory mutation.
- Writes only shadow JSONL records under runtime/router_guard_dryrun/.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.router.eamtp_7d_translator import build_packet
from runtime.dead_letter.eamtp_policy_gate import check_packet


OUT_DIR = ROOT / "runtime" / "router_guard_dryrun"


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def sha256_obj(obj: Dict[str, Any]) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")


def load_packet(path: str | None) -> Dict[str, Any] | None:
    if not path:
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def state_for_decision(decision: str) -> str:
    if decision == "allow_low_risk":
        return "routed"
    if decision == "pending_review":
        return "pending_review"
    if decision == "dead_letter":
        return "dead_letter"
    return "received"


def run_guard(args: argparse.Namespace) -> Dict[str, Any]:
    packet = load_packet(args.packet_json)

    if packet is None:
        packet = build_packet(
            summary=args.summary,
            intent_type=args.intent_type,
            actor_type=args.actor_type,
            auth_level=args.auth_level,
            entry=args.entry,
            source_field=args.source_field,
            target_field=args.target_field,
            privacy_level=args.privacy_level,
            consent_state=args.consent_state,
            cloud_allowed=args.cloud_allowed,
            preferred_lane=args.preferred_lane,
            latency_class=args.latency_class,
            cost_policy=args.cost_policy,
        )

    decision, reasons = check_packet(packet)

    packet.setdefault("d7_action_state", {})["state"] = state_for_decision(decision)

    record: Dict[str, Any] = {
        "guard": "eamtp_router_guard_dryrun",
        "mode": "shadow_dry_run",
        "created_at": utc_now(),
        "decision": decision,
        "reasons": reasons,
        "packet_id": packet.get("packet_id"),
        "packet_hash": sha256_obj(packet),
        "packet": packet,
        "safety": {
            "no_execution": True,
            "no_service_restart": True,
            "no_live_interception": True,
            "no_db_write": True,
            "no_cloud_call": True,
            "shadow_store_only": True
        }
    }

    append_jsonl(OUT_DIR / "eamtp_router_guard_dryrun.jsonl", record)

    if decision == "allow_low_risk":
        append_jsonl(OUT_DIR / "allow_low_risk_shadow.jsonl", record)
    elif decision == "pending_review":
        append_jsonl(OUT_DIR / "pending_review_shadow.jsonl", record)
    elif decision == "dead_letter":
        append_jsonl(OUT_DIR / "dead_letter_shadow.jsonl", record)
    else:
        append_jsonl(OUT_DIR / "unknown_decision_shadow.jsonl", record)

    return {
        "decision": decision,
        "reasons": reasons,
        "packet_id": packet.get("packet_id"),
        "packet_hash": record["packet_hash"],
        "shadow_store": str(OUT_DIR),
        "mode": "shadow_dry_run"
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet-json", default=None)
    parser.add_argument("--summary", default="EAMTP router guard dry-run packet")
    parser.add_argument("--intent-type", default="ask")
    parser.add_argument("--actor-type", default="admin")
    parser.add_argument("--auth-level", default="privileged")
    parser.add_argument("--entry", default="local")
    parser.add_argument("--source-field", default="local_ops")
    parser.add_argument("--target-field", default="router")
    parser.add_argument("--privacy-level", default="redacted")
    parser.add_argument("--consent-state", default="system")
    parser.add_argument("--cloud-allowed", action="store_true")
    parser.add_argument("--preferred-lane", default="local")
    parser.add_argument("--latency-class", default="normal")
    parser.add_argument("--cost-policy", default="balanced")
    args = parser.parse_args()

    result = run_guard(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
