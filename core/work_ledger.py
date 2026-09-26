#!/usr/bin/env python3
"""Persistent D2 Work Ledger for W7TP / 8D ADI."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_LEDGER_PATH = Path(__file__).resolve().parents[1] / "state" / "WORK_LEDGER.json"
ALLOWED_STATES = {"TODO", "DOING", "BLOCKED", "HOLD", "DONE", "CANCELLED"}
OPEN_STATES = {"TODO", "DOING", "BLOCKED", "HOLD"}
REQUIRED_TASK_FIELDS = {
    "TASK_ID", "PARENT_INTENT", "TITLE", "DESCRIPTION", "STATE", "PRIORITY",
    "D3_COORDINATE", "DEPENDENCIES", "BLOCKERS", "COMPLETION_CRITERIA",
    "D4_EVIDENCE", "LAST_UPDATE", "NEXT_ACTION",
}
PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_sha256(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class WorkLedger:
    """Atomic JSON-backed work ledger. It does not make D8 decisions."""

    def __init__(self, path: str | Path = DEFAULT_LEDGER_PATH) -> None:
        self.path = Path(path)
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            raise FileNotFoundError(self.path)
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data.get("TASKS"), list):
            raise ValueError("WORK_LEDGER TASKS must be a list")
        ids: set[str] = set()
        for task in data["TASKS"]:
            self._validate_task(task)
            task_id = task["TASK_ID"]
            if task_id in ids:
                raise ValueError(f"duplicate TASK_ID: {task_id}")
            ids.add(task_id)
        return data

    def _validate_task(self, task: dict[str, Any]) -> None:
        missing = REQUIRED_TASK_FIELDS - set(task)
        if missing:
            raise ValueError(f"task missing fields: {sorted(missing)}")
        if task["STATE"] not in ALLOWED_STATES:
            raise ValueError(f"invalid STATE: {task['STATE']}")
        for field in ("DEPENDENCIES", "BLOCKERS", "D4_EVIDENCE"):
            if not isinstance(task[field], list):
                raise ValueError(f"{field} must be a list")

    def _save(self) -> None:
        self.data["UPDATED_AT"] = _now()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self.data, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, self.path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    def _task(self, task_id: str) -> dict[str, Any]:
        for task in self.data["TASKS"]:
            if task["TASK_ID"] == task_id:
                return task
        raise KeyError(task_id)

    def create_task(self, task: dict[str, Any]) -> dict[str, Any]:
        task = copy.deepcopy(task)
        task.setdefault("LAST_UPDATE", _now())
        self._validate_task(task)
        if any(t["TASK_ID"] == task["TASK_ID"] for t in self.data["TASKS"]):
            raise ValueError(f"TASK_ID already exists: {task['TASK_ID']}")
        self.data["TASKS"].append(task)
        self._save()
        return copy.deepcopy(task)

    def update_task(self, task_id: str, **changes: Any) -> dict[str, Any]:
        if "TASK_ID" in changes and changes["TASK_ID"] != task_id:
            raise ValueError("TASK_ID is immutable")
        if "STATE" in changes and changes["STATE"] not in ALLOWED_STATES:
            raise ValueError(f"invalid STATE: {changes['STATE']}")
        task = self._task(task_id)
        if task["STATE"] == "DONE" or task.get("COMPLETION_SEAL"):
            effective = {
                key: value
                for key, value in changes.items()
                if task.get(key) != value
            }
            if effective:
                raise ValueError("closed task requires explicit reopen_task")
            return copy.deepcopy(task)
        task.update(copy.deepcopy(changes))
        task["LAST_UPDATE"] = _now()
        self._validate_task(task)
        self._save()
        return copy.deepcopy(task)

    def complete_task(
        self,
        task_id: str,
        evidence: dict[str, Any] | None = None,
        *,
        closed_head: str | None = None,
    ) -> dict[str, Any]:
        task = self._task(task_id)
        if task["STATE"] == "DONE" or task.get("COMPLETION_SEAL"):
            raise ValueError("task already closed")
        evidence_items = copy.deepcopy(task["D4_EVIDENCE"])
        if evidence is not None:
            evidence_items.append(copy.deepcopy(evidence))
        closed_at = _now()
        scope_payload = {
            "TASK_ID": task["TASK_ID"],
            "PARENT_INTENT": task["PARENT_INTENT"],
            "TITLE": task["TITLE"],
            "DESCRIPTION": task["DESCRIPTION"],
            "PRIORITY": task["PRIORITY"],
            "D3_COORDINATE": task["D3_COORDINATE"],
            "DEPENDENCIES": task["DEPENDENCIES"],
            "COMPLETION_CRITERIA": task["COMPLETION_CRITERIA"],
        }
        completion_seal = {
            "CLOSED_AT": closed_at,
            "CLOSED_HEAD": closed_head or "UNSPECIFIED",
            "SCOPE_SHA256": _canonical_sha256(scope_payload),
            "EVIDENCE_SHA256": _canonical_sha256(evidence_items),
        }
        return self.update_task(
            task_id,
            STATE="DONE",
            D4_EVIDENCE=evidence_items,
            BLOCKERS=[],
            NEXT_ACTION="NONE",
            CLOSED_AT=closed_at,
            CLOSED_HEAD=closed_head or "UNSPECIFIED",
            COMPLETION_SEAL=completion_seal,
        )

    def reopen_task(
        self,
        task_id: str,
        *,
        reason: str,
        authority_ref: str,
        next_action: str,
    ) -> dict[str, Any]:
        if not reason.strip():
            raise ValueError("reopen reason required")
        if not authority_ref.strip():
            raise ValueError("reopen authority_ref required")
        if not next_action.strip() or next_action == "NONE":
            raise ValueError("explicit reopen next_action required")
        task = self._task(task_id)
        if task["STATE"] != "DONE":
            raise ValueError("only DONE task can be reopened")
        previous_seal = copy.deepcopy(task.get("COMPLETION_SEAL"))
        if previous_seal is None:
            previous_seal = {
                "LEGACY_UNSEALED": True,
                "TASK_STATE_SHA256": _canonical_sha256(task),
            }
        history = copy.deepcopy(task.get("REOPEN_HISTORY", []))
        history.append({
            "REOPENED_AT": _now(),
            "REASON": reason,
            "AUTHORITY_REF": authority_ref,
            "PREVIOUS_COMPLETION_SEAL": previous_seal,
        })
        task["STATE"] = "TODO"
        task["NEXT_ACTION"] = next_action
        task["BLOCKERS"] = []
        task["REOPEN_HISTORY"] = history
        task.pop("COMPLETION_SEAL", None)
        task.pop("CLOSED_AT", None)
        task.pop("CLOSED_HEAD", None)
        task["LAST_UPDATE"] = _now()
        self._validate_task(task)
        self._save()
        return copy.deepcopy(task)

    def block_task(self, task_id: str, blocker: str) -> dict[str, Any]:
        task = self._task(task_id)
        blockers = list(task["BLOCKERS"])
        if blocker not in blockers:
            blockers.append(blocker)
        return self.update_task(task_id, STATE="BLOCKED", BLOCKERS=blockers)

    def list_open_tasks(self) -> list[dict[str, Any]]:
        tasks = [copy.deepcopy(t) for t in self.data["TASKS"] if t["STATE"] in OPEN_STATES]
        return sorted(
            tasks,
            key=lambda t: (
                PRIORITY_RANK.get(t["PRIORITY"], 99),
                0 if t["STATE"] == "DOING" else 1,
                t["TASK_ID"],
            ),
        )

    def _dependencies_done(self, task: dict[str, Any]) -> bool:
        known = {t["TASK_ID"]: t["STATE"] for t in self.data["TASKS"]}
        for dependency in task["DEPENDENCIES"]:
            if dependency in known and known[dependency] != "DONE":
                return False
        return True

    def get_next_action(
        self, verified_active_task_ids: set[str] | None = None
    ) -> dict[str, str] | None:
        verified_active = set(verified_active_task_ids or set())
        candidates = [
            t for t in self.list_open_tasks()
            if t["STATE"] in {"DOING", "TODO"}
            and not t["BLOCKERS"]
            and self._dependencies_done(t)
            and t["NEXT_ACTION"] not in {"", "NONE", None}
        ]
        if not candidates:
            return None
        candidates.sort(
            key=lambda t: (
                0 if t["TASK_ID"] in verified_active else 1,
                PRIORITY_RANK.get(t["PRIORITY"], 99),
                0 if t["STATE"] == "DOING" else 1,
                t["TASK_ID"],
            )
        )
        task = candidates[0]
        return {"TASK_ID": task["TASK_ID"], "NEXT_ACTION": task["NEXT_ACTION"]}

def create_task(task: dict[str, Any], path: str | Path = DEFAULT_LEDGER_PATH) -> dict[str, Any]:
    return WorkLedger(path).create_task(task)


def update_task(
    task_id: str, path: str | Path = DEFAULT_LEDGER_PATH, **changes: Any
) -> dict[str, Any]:
    return WorkLedger(path).update_task(task_id, **changes)


def complete_task(
    task_id: str,
    evidence: dict[str, Any] | None = None,
    path: str | Path = DEFAULT_LEDGER_PATH,
    *,
    closed_head: str | None = None,
) -> dict[str, Any]:
    return WorkLedger(path).complete_task(
        task_id, evidence, closed_head=closed_head
    )


def reopen_task(
    task_id: str,
    *,
    reason: str,
    authority_ref: str,
    next_action: str,
    path: str | Path = DEFAULT_LEDGER_PATH,
) -> dict[str, Any]:
    return WorkLedger(path).reopen_task(
        task_id,
        reason=reason,
        authority_ref=authority_ref,
        next_action=next_action,
    )


def block_task(
    task_id: str, blocker: str, path: str | Path = DEFAULT_LEDGER_PATH
) -> dict[str, Any]:
    return WorkLedger(path).block_task(task_id, blocker)


def list_open_tasks(path: str | Path = DEFAULT_LEDGER_PATH) -> list[dict[str, Any]]:
    return WorkLedger(path).list_open_tasks()


def get_next_action(
    path: str | Path = DEFAULT_LEDGER_PATH,
    verified_active_task_ids: set[str] | None = None,
) -> dict[str, str] | None:
    return WorkLedger(path).get_next_action(verified_active_task_ids)
