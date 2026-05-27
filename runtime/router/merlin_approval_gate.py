#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Merlin Approval Gate - Human Approval Record Only

Safety:
- no router login
- no SSH
- no HTTP router API
- no nvram write
- no reboot
- no firewall change
- no credential storage
- no automatic execution
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


ROOT = Path(__file__).resolve().parents[2]
QUEUE_DIR = ROOT / "runtime" / "merlin_apply_queue"
OUT_DIR = ROOT / "runtime" / "merlin_approval_gate"

APPROVAL_PHRASE = "I APPROVE THIS MERLIN ROUTER CHANGE MANUALLY"


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def sha256_obj(obj: Dict[str, Any]) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")


def iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def find_ticket(ticket_id: str) -> Optional[Dict[str, Any]]:
    for fn in [
        QUEUE_DIR / "merlin_apply_queue.jsonl",
        QUEUE_DIR / "pending_human_review.jsonl",
        QUEUE_DIR / "observe_only.jsonl",
        QUEUE_DIR / "rejected_dead_letter.jsonl",
    ]:
        for obj in iter_jsonl(fn):
            if obj.get("ticket_id") == ticket_id:
                return obj
    return None


def latest_pending_ticket() -> Optional[Dict[str, Any]]:
    latest = None
    for obj in iter_jsonl(QUEUE_DIR / "pending_human_review.jsonl"):
        latest = obj
    return latest


def decide(ticket: Dict[str, Any], phrase: str, expected_hash: str | None) -> Dict[str, Any]:
    status = ticket.get("ticket_status")
    ticket_hash = ticket.get("ticket_hash")
    ticket_id = ticket.get("ticket_id")

    reasons = []

    if expected_hash and expected_hash != ticket_hash:
        reasons.append("ticket_hash_mismatch")

    if phrase != APPROVAL_PHRASE:
        reasons.append("approval_phrase_mismatch")

    if status == "rejected_dead_letter":
        reasons.append("dead_letter_ticket_cannot_be_approved")

    if ticket.get("driver_decision") == "dead_letter":
        reasons.append("driver_dead_letter_cannot_be_approved")

    if status == "observe_only_no_apply_needed":
        reasons.append("observe_only_ticket_does_not_need_apply_approval")

    if reasons:
        decision = "rejected_approval"
        approved = False
    else:
        decision = "approved_record_only"
        approved = True

    record: Dict[str, Any] = {
        "gate": "merlin_approval_gate",
        "mode": "human_approval_record_only",
        "created_at": utc_now(),
        "decision": decision,
        "approved": approved,
        "reasons": reasons if reasons else ["exact_phrase_and_hash_verified"],
        "ticket_id": ticket_id,
        "ticket_hash": ticket_hash,
        "approved_for_manual_apply": approved,
        "auto_execute": False,
        "executable": False,
        "safety": {
            "no_router_login": True,
            "no_ssh": True,
            "no_http_router_api": True,
            "no_nvram_write": True,
            "no_reboot": True,
            "no_firewall_change": True,
            "no_credential_storage": True,
            "record_only": True
        },
        "ticket": ticket
    }
    record["approval_record_hash"] = sha256_obj(record)
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticket-id", default=None)
    parser.add_argument("--ticket-hash", default=None)
    parser.add_argument("--phrase", required=True)
    parser.add_argument("--latest-pending", action="store_true")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.latest_pending:
        ticket = latest_pending_ticket()
    else:
        ticket = find_ticket(args.ticket_id) if args.ticket_id else None

    if not ticket:
        result = {
            "decision": "rejected_approval",
            "approved": False,
            "reasons": ["ticket_not_found"],
            "auto_execute": False,
            "executable": False
        }
        append_jsonl(OUT_DIR / "rejected_approval.jsonl", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    record = decide(ticket, args.phrase, args.ticket_hash)

    append_jsonl(OUT_DIR / "merlin_approval_gate.jsonl", record)
    if record["decision"] == "approved_record_only":
        append_jsonl(OUT_DIR / "approved_record_only.jsonl", record)
    else:
        append_jsonl(OUT_DIR / "rejected_approval.jsonl", record)

    print(json.dumps({
        "decision": record["decision"],
        "approved": record["approved"],
        "reasons": record["reasons"],
        "ticket_id": record["ticket_id"],
        "ticket_hash": record["ticket_hash"],
        "approved_for_manual_apply": record["approved_for_manual_apply"],
        "auto_execute": record["auto_execute"],
        "executable": record["executable"],
        "approval_record_hash": record["approval_record_hash"],
        "store": str(OUT_DIR)
    }, ensure_ascii=False, indent=2))

    return 0 if record["decision"] == "approved_record_only" else 2


if __name__ == "__main__":
    raise SystemExit(main())
