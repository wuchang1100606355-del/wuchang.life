#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Merlin Apply Queue - Human Review Ticket Layer

Safety:
- no router login
- no SSH
- no HTTP router API
- no nvram write
- no reboot
- no firewall change
- no credential storage

It creates review tickets only.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
import uuid
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.router.merlin_intent_driver import build_merlin_plan


OUT_DIR = ROOT / "runtime" / "merlin_apply_queue"


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def sha256_obj(obj: Dict[str, Any]) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")


def make_ticket(intent: str, note: str = "") -> Dict[str, Any]:
    plan = build_merlin_plan(intent=intent, note=note)
    decision = plan.get("decision")
    risk = plan.get("risk")

    if decision == "dead_letter":
        ticket_status = "rejected_dead_letter"
        review_required = True
        executable = False
        reasons = plan.get("reasons", []) + ["dead_letter_cannot_create_apply_ticket"]
    elif decision == "pending_review":
        ticket_status = "awaiting_human_review"
        review_required = True
        executable = False
        reasons = plan.get("reasons", []) + ["human_approval_required_before_apply"]
    elif decision == "allow_low_risk":
        ticket_status = "observe_only_no_apply_needed"
        review_required = False
        executable = False
        reasons = plan.get("reasons", []) + ["low_risk_observation_only"]
    else:
        ticket_status = "unknown_requires_review"
        review_required = True
        executable = False
        reasons = plan.get("reasons", []) + ["unknown_decision_requires_review"]

    ticket: Dict[str, Any] = {
        "queue": "merlin_apply_queue",
        "mode": "human_review_ticket_only",
        "ticket_id": "merlin_apply_" + _dt.datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8],
        "created_at": utc_now(),
        "intent": intent,
        "risk": risk,
        "driver_decision": decision,
        "ticket_status": ticket_status,
        "review_required": review_required,
        "executable": executable,
        "reasons": reasons,
        "plan_hash": plan.get("plan_hash"),
        "plan_summary": plan.get("summary"),
        "manual_review_steps": plan.get("steps", []),
        "forbidden_automatic_actions": [
            "router_login",
            "ssh",
            "http_admin_api_call",
            "nvram_write",
            "firmware_change",
            "router_reboot",
            "firewall_change",
            "wan_exposure_change",
            "credential_read",
            "credential_storage"
        ],
        "human_approval": {
            "approved": False,
            "approved_by": None,
            "approved_at": None,
            "approval_phrase_required": "I APPROVE THIS MERLIN ROUTER CHANGE MANUALLY",
            "notes": ""
        },
        "safety": {
            "no_router_login": True,
            "no_ssh": True,
            "no_http_router_api": True,
            "no_nvram_write": True,
            "no_reboot": True,
            "no_firewall_change": True,
            "no_credential_storage": True
        },
        "source_plan": plan
    }
    ticket["ticket_hash"] = sha256_obj(ticket)
    return ticket


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--intent", required=True)
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ticket = make_ticket(args.intent, args.note)

    append_jsonl(OUT_DIR / "merlin_apply_queue.jsonl", ticket)

    status = ticket["ticket_status"]
    if status == "awaiting_human_review":
        append_jsonl(OUT_DIR / "pending_human_review.jsonl", ticket)
    elif status == "rejected_dead_letter":
        append_jsonl(OUT_DIR / "rejected_dead_letter.jsonl", ticket)
    elif status == "observe_only_no_apply_needed":
        append_jsonl(OUT_DIR / "observe_only.jsonl", ticket)
    else:
        append_jsonl(OUT_DIR / "unknown_review.jsonl", ticket)

    print(json.dumps({
        "ticket_id": ticket["ticket_id"],
        "intent": ticket["intent"],
        "risk": ticket["risk"],
        "driver_decision": ticket["driver_decision"],
        "ticket_status": ticket["ticket_status"],
        "review_required": ticket["review_required"],
        "executable": ticket["executable"],
        "ticket_hash": ticket["ticket_hash"],
        "store": str(OUT_DIR)
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
