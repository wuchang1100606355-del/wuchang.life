#!/usr/bin/env python3
"""Persistent execution continuity for W7TP / 8D ADI chat-native work.

This module is D2/D4 state persistence only. It does not grant D8 authority and
does not re-execute an interrupted action. Resume decisions must be based on
the last confirmed effect plus an idempotency key.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_ACTION_LEDGER_PATH = (
    Path(__file__).resolve().parents[1] / "state" / "ACTION_LEDGER.json"
)

ACTION_STATES = {
    "RUNNING",
    "WAITING",
    "INTERRUPTED",
    "RESUMED",
    "DONE",
    "FAILED",
    "HOLD",
}

TERMINAL_ACTION_STATES = {"DONE", "FAILED"}
RESUMABLE_ACTION_STATES = {"INTERRUPTED", "HOLD"}

REQUIRED_ACTION_FIELDS = {
    "ACTION_ID",
    "TASK_ID",
    "TURN_ID",
    "PROCESS_ID",
    "STATE",
    "TARGET_COORDINATE",
    "TOOL",
    "IDEMPOTENCY_KEY",
    "STARTED_AT",
    "LAST_UPDATE",
    "LAST_CONFIRMED_EFFECT",
    "LAST_TOOL_EFFECT",
    "RESUME_FROM",
    "ERROR",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_idempotency_key(
    *,
    task_id: str,
    target_coordinate: str,
    operation: str,
    intent_hash: str = "",
) -> str:
    payload = {
        "task_id": task_id,
        "target_coordinate": target_coordinate,
        "operation": operation,
        "intent_hash": intent_hash,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ActionLedger:
    """Atomic JSON-backed ledger for execution/resume state."""

    def __init__(self, path: str | Path = DEFAULT_ACTION_LEDGER_PATH) -> None:
        self.path = Path(path)
        self.data = self._load_or_init()

    def _load_or_init(self) -> dict[str, Any]:
        if not self.path.exists():
            return {
                "LEDGER_VERSION": "1.0",
                "UPDATED_AT": _now(),
                "ACTIONS": [],
            }
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data.get("ACTIONS"), list):
            raise ValueError("ACTION_LEDGER ACTIONS must be a list")
        seen: set[str] = set()
        for action in data["ACTIONS"]:
            self._validate_action(action)
            action_id = action["ACTION_ID"]
            if action_id in seen:
                raise ValueError(f"duplicate ACTION_ID: {action_id}")
            seen.add(action_id)
        return data

    def _validate_action(self, action: dict[str, Any]) -> None:
        missing = REQUIRED_ACTION_FIELDS - set(action)
        if missing:
            raise ValueError(f"action missing fields: {sorted(missing)}")
        if action["STATE"] not in ACTION_STATES:
            raise ValueError(f"invalid action STATE: {action['STATE']}")
        if not action["IDEMPOTENCY_KEY"]:
            raise ValueError("IDEMPOTENCY_KEY required")
        if (
            action["STATE"] in TERMINAL_ACTION_STATES
            and action.get("RESUME_FROM") is not None
        ):
            raise ValueError("terminal action cannot retain RESUME_FROM")

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

    def _action(self, action_id: str) -> dict[str, Any]:
        for action in self.data["ACTIONS"]:
            if action["ACTION_ID"] == action_id:
                return action
        raise KeyError(action_id)

    def begin_action(
        self,
        *,
        action_id: str,
        task_id: str,
        turn_id: str,
        process_id: int | str | None,
        target_coordinate: str,
        tool: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        if any(a["ACTION_ID"] == action_id for a in self.data["ACTIONS"]):
            raise ValueError(f"ACTION_ID already exists: {action_id}")
        for existing in self.data["ACTIONS"]:
            if (
                existing["IDEMPOTENCY_KEY"] == idempotency_key
                and existing["STATE"] not in TERMINAL_ACTION_STATES
            ):
                raise ValueError(
                    f"active action with same IDEMPOTENCY_KEY: {existing['ACTION_ID']}"
                )
        now = _now()
        action = {
            "ACTION_ID": action_id,
            "TASK_ID": task_id,
            "TURN_ID": turn_id,
            "PROCESS_ID": process_id,
            "STATE": "RUNNING",
            "TARGET_COORDINATE": target_coordinate,
            "TOOL": tool,
            "IDEMPOTENCY_KEY": idempotency_key,
            "STARTED_AT": now,
            "LAST_UPDATE": now,
            "LAST_CONFIRMED_EFFECT": None,
            "LAST_TOOL_EFFECT": None,
            "RESUME_FROM": None,
            "ERROR": None,
        }
        self._validate_action(action)
        self.data["ACTIONS"].append(action)
        self._save()
        return copy.deepcopy(action)

    def update_action(self, action_id: str, **changes: Any) -> dict[str, Any]:
        if "ACTION_ID" in changes and changes["ACTION_ID"] != action_id:
            raise ValueError("ACTION_ID is immutable")
        if "STATE" in changes and changes["STATE"] not in ACTION_STATES:
            raise ValueError(f"invalid action STATE: {changes['STATE']}")
        action = self._action(action_id)
        if action["STATE"] in TERMINAL_ACTION_STATES and changes.get("STATE") not in {
            None,
            action["STATE"],
        }:
            raise ValueError("terminal action cannot transition")
        action.update(copy.deepcopy(changes))
        action["LAST_UPDATE"] = _now()
        self._validate_action(action)
        self._save()
        return copy.deepcopy(action)

    def mark_waiting(
        self, action_id: str, *, last_tool_effect: Any = None
    ) -> dict[str, Any]:
        return self.update_action(
            action_id, STATE="WAITING", LAST_TOOL_EFFECT=last_tool_effect
        )

    def mark_interrupted(
        self,
        action_id: str,
        *,
        error: str,
        last_confirmed_effect: Any = None,
        last_tool_effect: Any = None,
        resume_from: str | None = None,
    ) -> dict[str, Any]:
        return self.update_action(
            action_id,
            STATE="INTERRUPTED",
            ERROR=error,
            LAST_CONFIRMED_EFFECT=last_confirmed_effect,
            LAST_TOOL_EFFECT=last_tool_effect,
            RESUME_FROM=resume_from,
        )

    def resume_action(
        self,
        action_id: str,
        *,
        new_process_id: int | str | None,
        resume_from: str,
    ) -> dict[str, Any]:
        action = self._action(action_id)
        if action["STATE"] not in RESUMABLE_ACTION_STATES:
            raise ValueError(f"action not resumable from state {action['STATE']}")
        return self.update_action(
            action_id,
            STATE="RESUMED",
            PROCESS_ID=new_process_id,
            RESUME_FROM=resume_from,
            ERROR=None,
        )

    def complete_action(
        self, action_id: str, *, confirmed_effect: Any
    ) -> dict[str, Any]:
        return self.update_action(
            action_id,
            STATE="DONE",
            LAST_CONFIRMED_EFFECT=confirmed_effect,
            RESUME_FROM=None,
            ERROR=None,
        )

    def fail_action(
        self, action_id: str, *, error: str, last_tool_effect: Any = None
    ) -> dict[str, Any]:
        return self.update_action(
            action_id,
            STATE="FAILED",
            ERROR=error,
            LAST_TOOL_EFFECT=last_tool_effect,
            RESUME_FROM=None,
        )

    def list_open_actions(self) -> list[dict[str, Any]]:
        return [
            copy.deepcopy(a)
            for a in self.data["ACTIONS"]
            if a["STATE"] not in TERMINAL_ACTION_STATES
        ]

    def find_by_idempotency_key(
        self, idempotency_key: str
    ) -> dict[str, Any] | None:
        matches = [
            a for a in self.data["ACTIONS"]
            if a["IDEMPOTENCY_KEY"] == idempotency_key
        ]
        if not matches:
            return None
        matches.sort(
            key=lambda a: (a["LAST_UPDATE"], a["ACTION_ID"]),
            reverse=True,
        )
        return copy.deepcopy(matches[0])

    def get_resumable_action(self) -> dict[str, Any] | None:
        candidates = [
            a
            for a in self.data["ACTIONS"]
            if a["STATE"] in RESUMABLE_ACTION_STATES
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda a: (a["LAST_UPDATE"], a["ACTION_ID"]), reverse=True)
        return copy.deepcopy(candidates[0])

    def recovery_decision(
        self,
        action_id: str,
        *,
        process_exists: bool,
        stream_available: bool,
        effect_confirmed: bool,
    ) -> dict[str, str]:
        """Return a non-authoritative recovery recommendation.

        Crucially, a missing stream/process never means "run again".
        """
        action = self._action(action_id)
        if effect_confirmed:
            return {
                "STATE": "EFFECT_ALREADY_CONFIRMED",
                "ACTION": "VERIFY_AND_COMPLETE",
            }
        if process_exists and stream_available:
            return {"STATE": "RUNNING", "ACTION": "OBSERVE_ONLY"}
        if process_exists and not stream_available:
            return {
                "STATE": "STREAM_DETACHED",
                "ACTION": "OBSERVE_PROCESS_EFFECT",
            }
        return {
            "STATE": "INTERRUPTED_UNKNOWN_EFFECT",
            "ACTION": "CHECK_ACTUAL_EFFECT_BEFORE_RESUME",
        }
