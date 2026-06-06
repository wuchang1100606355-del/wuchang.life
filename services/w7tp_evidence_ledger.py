from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.w7tp_state_hash import canonical_hash


LEDGER_PATH = Path("runtime/ledger/w7tp_ui_events.jsonl")
DEAD_LETTER_DIR = Path("runtime/dead_letter/w7tp_ui_blocked")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _last_hash(path: Path) -> str:
    if not path.exists():
        return "GENESIS"
    last = ""
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                last = line
    if not last:
        return "GENESIS"
    try:
        data = json.loads(last)
    except json.JSONDecodeError:
        return canonical_hash(last)
    return str(data.get("event_hash") or canonical_hash(data))


def commit_evidence(
    packet: dict[str, Any] | None = None,
    state: str | None = None,
    decision: dict[str, Any] | None = None,
    hash_data: dict[str, Any] | None = None,
    source: str | None = None,
    event_type: str = "w7tp_ui_commit",
) -> dict[str, Any]:
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    decision = decision or {}
    state = state or str(decision.get("state") or "TRANSACTION_COMMITTED")
    prev_hash = _last_hash(LEDGER_PATH)
    event = {
        "ts": _utc_now(),
        "source": source or "w7tp_8d_control_panel",
        "event_type": event_type,
        "packet_ref": canonical_hash(packet or {}),
        "state": state,
        "decision": decision,
        "hash": hash_data or {},
        "prev_hash": prev_hash,
    }
    event["event_hash"] = canonical_hash(event)
    with LEDGER_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")

    dead_letter_path = None
    if decision.get("allowed") is False or state == "HARDWALL_BLOCKED":
        DEAD_LETTER_DIR.mkdir(parents=True, exist_ok=True)
        dead_letter = DEAD_LETTER_DIR / f"{event['event_hash']}.json"
        dead_letter.write_text(
            json.dumps(event, ensure_ascii=False, sort_keys=True, indent=2),
            encoding="utf-8",
        )
        dead_letter_path = str(dead_letter)

    return {
        "ok": True,
        "ledger_path": str(LEDGER_PATH),
        "event_hash": event["event_hash"],
        "dead_letter_path": dead_letter_path,
        "timestamp": event["ts"],
    }
