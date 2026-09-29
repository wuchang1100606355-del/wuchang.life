#!/usr/bin/env python3
"""Conversation checkpoint and structured event bridge for the 8D ADI Work Ledger."""

from __future__ import annotations

import hashlib
import json
import os
import re
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
CONVERSATION_EVENT_SCHEMA_VERSION = "W7TP-CONVERSATION-EVENT-CANDIDATE/1.0"
CONVERSATION_EVENT_KINDS = frozenset({
    "INTENT", "TASK", "STATE_CHANGE", "BLOCKER", "HOLD",
    "REVOCATION", "CONFLICT", "EVIDENCE", "NEXT_ACTION",
})
_TASK_ID_RE = re.compile(r"(?<![A-Za-z0-9])(?:T-\d{3}|NLDEV-\d{3})(?![A-Za-z0-9])")
_TASK_HEADER_RE = re.compile(r"^\s*((?:T-\d{3}|NLDEV-\d{3}))(?:\s+(.+?))?\s*$")
_FIELD_RE = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s*=\s*(.*?)\s*$")
_EVIDENCE_FIELDS = frozenset({
    "RESULT", "COMMIT", "SHA", "HEAD", "GIT_HEAD", "PR15_HEAD",
    "LOCAL_HEAD", "UPSTREAM_HEAD", "AHEAD_BEHIND", "WORKTREE",
})


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


def _conversation_candidate(
    kind: str,
    *,
    task_id: str | None,
    payload: dict[str, Any],
    source_coordinate: str,
    source_sha256: str,
    source_line: int,
) -> dict[str, Any]:
    if kind not in CONVERSATION_EVENT_KINDS:
        raise ValueError(f"unsupported candidate kind: {kind}")
    return {
        "kind": kind,
        "task_id": task_id,
        "payload": payload,
        "source_coordinate": source_coordinate,
        "source_sha256": source_sha256,
        "source_line": source_line,
        "candidate_only": True,
        "authority_granted": False,
        "requires_total_field_verify": True,
    }


def _append_candidate(events: list[dict[str, Any]], candidate: dict[str, Any]) -> None:
    marker = json.dumps(candidate, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if not any(
        json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) == marker
        for item in events
    ):
        events.append(candidate)


def extract_conversation_event_candidates(
    text: str,
    *,
    source_coordinate: str = "conversation:current",
) -> dict[str, Any]:
    """Extract explicit conversation events without granting authority or mutating state."""
    if not isinstance(text, str):
        raise TypeError("conversation text must be a string")
    source_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    events: list[dict[str, Any]] = []
    current_task: str | None = None

    for line_no, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        header = _TASK_HEADER_RE.fullmatch(line)
        if header:
            current_task = header.group(1)
            title = (header.group(2) or "").strip()
            if title:
                _append_candidate(events, _conversation_candidate(
                    "TASK", task_id=current_task, payload={"title": title},
                    source_coordinate=source_coordinate, source_sha256=source_sha256,
                    source_line=line_no,
                ))
            continue

        field = _FIELD_RE.fullmatch(line)
        if field:
            key, value = field.group(1), field.group(2).strip()
            if key == "STATE" and current_task and value in {"TODO", "DOING", "BLOCKED", "HOLD", "DONE", "CANCELLED"}:
                _append_candidate(events, _conversation_candidate(
                    "STATE_CHANGE", task_id=current_task, payload={"state": value},
                    source_coordinate=source_coordinate, source_sha256=source_sha256,
                    source_line=line_no,
                ))
            elif key == "NEXT_ACTION" and current_task:
                _append_candidate(events, _conversation_candidate(
                    "NEXT_ACTION", task_id=current_task, payload={"next_action": value},
                    source_coordinate=source_coordinate, source_sha256=source_sha256,
                    source_line=line_no,
                ))
            elif key in {"BLOCKER", "BLOCKERS"} and current_task and value not in {"", "NONE", "[]"}:
                _append_candidate(events, _conversation_candidate(
                    "BLOCKER", task_id=current_task, payload={"blocker": value},
                    source_coordinate=source_coordinate, source_sha256=source_sha256,
                    source_line=line_no,
                ))
            elif key in _EVIDENCE_FIELDS and current_task:
                _append_candidate(events, _conversation_candidate(
                    "EVIDENCE", task_id=current_task, payload={key: value},
                    source_coordinate=source_coordinate, source_sha256=source_sha256,
                    source_line=line_no,
                ))
            elif key in {"REVOKED", "REVOCATION"}:
                _append_candidate(events, _conversation_candidate(
                    "REVOCATION", task_id=current_task, payload={key: value},
                    source_coordinate=source_coordinate, source_sha256=source_sha256,
                    source_line=line_no,
                ))
            elif key == "CONFLICT":
                _append_candidate(events, _conversation_candidate(
                    "CONFLICT", task_id=current_task, payload={"conflict": value},
                    source_coordinate=source_coordinate, source_sha256=source_sha256,
                    source_line=line_no,
                ))
            continue

        if line.startswith(("支線合併原則:", "支線合併原則：")):
            _append_candidate(events, _conversation_candidate(
                "INTENT", task_id=None, payload={"text": line},
                source_coordinate=source_coordinate, source_sha256=source_sha256,
                source_line=line_no,
            ))
        elif line.startswith(("RULE:", "RULE：", "決策:", "決策：")):
            _append_candidate(events, _conversation_candidate(
                "INTENT", task_id=current_task, payload={"text": line},
                source_coordinate=source_coordinate, source_sha256=source_sha256,
                source_line=line_no,
            ))
        elif current_task and "不得" in line and any(token in line for token in ("恢復", "重建", "重新開啟", "修改")):
            _append_candidate(events, _conversation_candidate(
                "HOLD", task_id=current_task, payload={"constraint": line},
                source_coordinate=source_coordinate, source_sha256=source_sha256,
                source_line=line_no,
            ))
        elif line.startswith(("撤銷", "已撤銷", "REVOKED")):
            task_match = _TASK_ID_RE.search(line)
            _append_candidate(events, _conversation_candidate(
                "REVOCATION", task_id=task_match.group(0) if task_match else current_task,
                payload={"text": line}, source_coordinate=source_coordinate,
                source_sha256=source_sha256, source_line=line_no,
            ))
        elif line.startswith(("衝突:", "衝突：", "CONFLICT:")):
            task_match = _TASK_ID_RE.search(line)
            _append_candidate(events, _conversation_candidate(
                "CONFLICT", task_id=task_match.group(0) if task_match else current_task,
                payload={"text": line}, source_coordinate=source_coordinate,
                source_sha256=source_sha256, source_line=line_no,
            ))

    return {
        "schema_version": CONVERSATION_EVENT_SCHEMA_VERSION,
        "candidate_only": True,
        "authority_granted": False,
        "requires_total_field_verify": True,
        "source_coordinate": source_coordinate,
        "source_sha256": source_sha256,
        "events": events,
    }


def project_verified_conversation_candidate(
    candidate: dict[str, Any],
    verification_receipt: dict[str, Any],
    ledger_path: str | Path = DEFAULT_LEDGER_PATH,
) -> dict[str, Any] | None:
    """Project an externally verified candidate into the existing ledger event contract."""
    if (
        candidate.get("candidate_only") is not True
        or candidate.get("authority_granted") is not False
        or candidate.get("requires_total_field_verify") is not True
    ):
        raise ValueError("conversation candidate authority boundary invalid")
    if (
        verification_receipt.get("final_decision") != "ALLOW"
        or verification_receipt.get("fixed_point_status") != "REACHED"
    ):
        raise ValueError("conversation candidate not verified by Total Field")

    kind = candidate.get("kind")
    task_id = candidate.get("task_id")
    payload = candidate.get("payload")
    if kind not in CONVERSATION_EVENT_KINDS or not isinstance(payload, dict):
        raise ValueError("conversation candidate structure invalid")
    if task_id is None:
        return None
    if not isinstance(task_id, str) or _TASK_ID_RE.fullmatch(task_id) is None:
        raise ValueError("conversation candidate task_id invalid")

    ledger = WorkLedger(ledger_path)
    task = ledger._task(task_id)
    if kind == "STATE_CHANGE":
        state = payload.get("state")
        if state == "DONE":
            return {
                "type": "TASK_COMPLETED",
                "TASK_ID": task_id,
                "evidence": {
                    "EVIDENCE_TYPE": "VERIFIED_CONVERSATION_EVENT",
                    "SOURCE_COORDINATE": candidate.get("source_coordinate"),
                    "SOURCE_SHA256": candidate.get("source_sha256"),
                },
            }
        if state not in {"TODO", "DOING", "BLOCKED", "HOLD", "CANCELLED"}:
            raise ValueError("conversation candidate state invalid")
        return {"type": "TASK_UPDATED", "TASK_ID": task_id, "changes": {"STATE": state}}
    if kind == "NEXT_ACTION":
        return {
            "type": "TASK_UPDATED", "TASK_ID": task_id,
            "changes": {"NEXT_ACTION": str(payload.get("next_action", ""))},
        }
    if kind == "BLOCKER":
        return {"type": "TASK_BLOCKED", "TASK_ID": task_id, "blocker": str(payload["blocker"])}
    if kind == "HOLD":
        blockers = list(task["BLOCKERS"])
        constraint = str(payload.get("constraint", "CONVERSATION_HOLD"))
        if constraint not in blockers:
            blockers.append(constraint)
        return {
            "type": "TASK_UPDATED", "TASK_ID": task_id,
            "changes": {"STATE": "HOLD", "BLOCKERS": blockers},
        }
    if kind == "EVIDENCE":
        evidence = list(task["D4_EVIDENCE"])
        evidence.append({
            "EVIDENCE_TYPE": "VERIFIED_CONVERSATION_EVENT",
            "SOURCE_COORDINATE": candidate.get("source_coordinate"),
            "SOURCE_SHA256": candidate.get("source_sha256"),
            **payload,
        })
        return {
            "type": "TASK_UPDATED", "TASK_ID": task_id,
            "changes": {"D4_EVIDENCE": evidence},
        }
    return None


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
