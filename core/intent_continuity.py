#!/usr/bin/env python3
"""Conversation checkpoint and structured event bridge for the 8D ADI Work Ledger."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.work_ledger import DEFAULT_LEDGER_PATH, WorkLedger
from core.execution_continuity import DEFAULT_ACTION_LEDGER_PATH, ActionLedger

DEFAULT_CHECKPOINT_PATH = (
    Path(__file__).resolve().parents[1] / "state" / "CURRENT_CONVERSATION_CHECKPOINT.json"
)
REQUIRED_CHECKPOINT_FIELDS = {
    "mainline", "current_goal", "current_state", "last_decision",
    "open_tasks", "next_action", "d8", "hold_reason",
}
D8_VALUES = {"PASS", "HOLD", "BLOCK"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_checkpoint(path: str | Path = DEFAULT_CHECKPOINT_PATH) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_checkpoint(data)
    return data

def validate_checkpoint(data: dict[str, Any]) -> None:
    missing = REQUIRED_CHECKPOINT_FIELDS - set(data)
    if missing:
        raise ValueError(f"checkpoint missing fields: {sorted(missing)}")
    if data["d8"] not in D8_VALUES:
        raise ValueError(f"invalid d8: {data['d8']}")
    if not isinstance(data["open_tasks"], list):
        raise ValueError("open_tasks must be a list")


def checkpoint_conversation(
    data: dict[str, Any], path: str | Path = DEFAULT_CHECKPOINT_PATH
) -> dict[str, Any]:
    payload = dict(data)
    payload["updated_at"] = _now()
    validate_checkpoint(payload)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, target)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
    return payload

def refresh_checkpoint_from_ledger(
    ledger_path: str | Path = DEFAULT_LEDGER_PATH,
    checkpoint_path: str | Path = DEFAULT_CHECKPOINT_PATH,
    *,
    current_goal: str,
    current_state: str,
    last_decision: str,
    d8: str,
    hold_reason: str = "",
) -> dict[str, Any]:
    ledger = WorkLedger(ledger_path)
    open_tasks = ledger.list_open_tasks()
    next_item = ledger.get_next_action()
    payload = {
        "mainline": ledger.data.get("MAINLINE", "W7TP / 8D ADI"),
        "current_goal": current_goal,
        "current_state": current_state,
        "last_decision": last_decision,
        "open_tasks": [task["TASK_ID"] for task in open_tasks],
        "next_action": next_item["NEXT_ACTION"] if next_item else "NONE",
        "d8": d8,
        "hold_reason": hold_reason,
    }
    return checkpoint_conversation(payload, checkpoint_path)


def apply_conversation_event(
    event: dict[str, Any],
    ledger_path: str | Path = DEFAULT_LEDGER_PATH,
    action_ledger_path: str | Path = DEFAULT_ACTION_LEDGER_PATH,
) -> dict[str, Any]:
    """Apply a structured task/action event; this stores state only."""
    ledger = WorkLedger(ledger_path)
    kind = event.get("type")

    if kind == "TASK_CREATED":
        return ledger.create_task(event["task"])
    if kind == "TASK_UPDATED":
        return ledger.update_task(event["TASK_ID"], **event.get("changes", {}))
    if kind == "TASK_COMPLETED":
        return ledger.complete_task(event["TASK_ID"], event.get("evidence"))
    if kind == "TASK_BLOCKED":
        return ledger.block_task(event["TASK_ID"], event["blocker"])

    actions = ActionLedger(action_ledger_path)
    if kind == "ACTION_STARTED":
        return actions.begin_action(**event["action"])
    if kind == "ACTION_WAITING":
        return actions.mark_waiting(
            event["ACTION_ID"], last_tool_effect=event.get("last_tool_effect")
        )
    if kind == "ACTION_INTERRUPTED":
        return actions.mark_interrupted(
            event["ACTION_ID"],
            error=event["error"],
            last_confirmed_effect=event.get("last_confirmed_effect"),
            last_tool_effect=event.get("last_tool_effect"),
            resume_from=event.get("resume_from"),
        )
    if kind == "ACTION_RESUMED":
        return actions.resume_action(
            event["ACTION_ID"],
            new_process_id=event.get("new_process_id"),
            resume_from=event["resume_from"],
        )
    if kind == "ACTION_COMPLETED":
        return actions.complete_action(
            event["ACTION_ID"], confirmed_effect=event.get("confirmed_effect")
        )
    if kind == "ACTION_FAILED":
        return actions.fail_action(
            event["ACTION_ID"],
            error=event["error"],
            last_tool_effect=event.get("last_tool_effect"),
        )
    raise ValueError(f"unsupported conversation event type: {kind}")
