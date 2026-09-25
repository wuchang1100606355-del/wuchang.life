#!/usr/bin/env python3
"""Local-only task-state reconstruction rule for W7TP minimum packets."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import urllib.request
from pathlib import Path
from typing import Any, Mapping, Sequence


DEFAULT_ROOT = Path("/home/taiji_admin/Taiji_Hub")
NATIVE_ADI_URL = os.getenv("W7TP_NATIVE_ADI_URL", "http://127.0.0.1:9110")
RULE_SCHEMA = "W7TP_LOCAL_TASK_STATE_RECONSTRUCTION_RULE_V1"
ALLOWED_RULE_ID = "WRITE_TASK_STATE_JSON"


class TaskStateRuleError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
def _root() -> Path:
    value = Path(os.getenv("TAIJI_PROJECT_ROOT", str(DEFAULT_ROOT))).resolve()
    if not value.is_dir():
        raise TaskStateRuleError("HOLD_TASK_STATE_ROOT_UNAVAILABLE")
    return value


def _load_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TaskStateRuleError(code) from exc
    if not isinstance(value, dict):
        raise TaskStateRuleError(code)
    return value


def _require_string(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TaskStateRuleError(code)
    return value


def _require_ref_list(value: Any, code: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item.strip() for item in value)
        or len(value) != len(set(value))
    ):
        raise TaskStateRuleError(code)
    return list(value)


def _post_json(path: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        NATIVE_ADI_URL.rstrip("/") + path,
        data=canonical_json_bytes(dict(payload)),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            value = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise TaskStateRuleError("HOLD_TASK_STATE_NATIVE_ADI_UNAVAILABLE") from exc
    if not isinstance(value, dict):
        raise TaskStateRuleError("HOLD_TASK_STATE_NATIVE_ADI_RESPONSE_INVALID")
    return value


def _native_adi_packet(record_ids: Sequence[str]) -> dict[str, Any]:
    value = _post_json("/v1/adi/packet", {"ids": list(record_ids)})
    if (
        value.get("packet_type") != "W7TP_NATIVE_ADI_8D_DYNAMIC_CONTEXT"
        or value.get("schema_version") != "W7TP_NATIVE_ADI_PACKET/1.0"
        or not isinstance(value.get("packet_sha256"), str)
    ):
        raise TaskStateRuleError("HOLD_TASK_STATE_NATIVE_ADI_PACKET_INVALID")
    lookup = value.get("reference_lookup")
    entries = lookup.get("entries") if isinstance(lookup, dict) else None
    if not isinstance(entries, list):
        raise TaskStateRuleError("HOLD_TASK_STATE_NATIVE_ADI_LOOKUP_INVALID")
    observed = [item.get("id") for item in entries if isinstance(item, dict)]
    if len(observed) != len(record_ids) or set(observed) != set(record_ids):
        raise TaskStateRuleError("HOLD_TASK_STATE_NATIVE_ADI_ID_SET_MISMATCH")
    return value
def _git_state(root: Path) -> dict[str, Any]:
    def run(*args: str) -> str:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            text=True,
            capture_output=True,
            timeout=10,
            check=True,
        )
        return proc.stdout.strip()

    status = run("status", "--porcelain=v1")
    return {
        "branch": run("branch", "--show-current"),
        "head": run("rev-parse", "HEAD"),
        "worktree_clean": status == "",
        "worktree_status_sha256": hashlib.sha256(status.encode()).hexdigest(),
    }


def _task_snapshot(
    *,
    task_id: str,
    action_refs: Sequence[str],
    adi_record_ids: Sequence[str],
) -> dict[str, Any]:
    root = _root()
    work_path = root / "state/WORK_LEDGER.json"
    action_path = root / "state/ACTION_LEDGER.json"
    checkpoint_path = root / "state/CURRENT_CONVERSATION_CHECKPOINT.json"

    work = _load_json(work_path, "HOLD_TASK_STATE_WORK_LEDGER_UNREADABLE")
    action = _load_json(action_path, "HOLD_TASK_STATE_ACTION_LEDGER_UNREADABLE")
    checkpoint = _load_json(
        checkpoint_path,
        "HOLD_TASK_STATE_CHECKPOINT_UNREADABLE",
    )

    tasks = work.get("TASKS")
    if not isinstance(tasks, list):
        raise TaskStateRuleError("HOLD_TASK_STATE_TASKS_INVALID")
    task = next(
        (
            item
            for item in tasks
            if isinstance(item, dict) and item.get("TASK_ID") == task_id
        ),
        None,
    )
    if task is None:
        raise TaskStateRuleError("HOLD_TASK_STATE_TASK_NOT_FOUND")

    actions = action.get("ACTIONS")
    if not isinstance(actions, list):
        raise TaskStateRuleError("HOLD_TASK_STATE_ACTIONS_INVALID")
    by_id = {
        str(item.get("ACTION_ID")): item
        for item in actions
        if isinstance(item, dict) and isinstance(item.get("ACTION_ID"), str)
    }
    selected_actions: list[dict[str, Any]] = []
    for ref in action_refs:
        item = by_id.get(ref)
        if item is None:
            raise TaskStateRuleError("HOLD_TASK_STATE_ACTION_REF_NOT_FOUND")
        if item.get("TASK_ID") != task_id:
            raise TaskStateRuleError("HOLD_TASK_STATE_ACTION_TASK_MISMATCH")
        selected_actions.append(item)
    native_adi_packet = _native_adi_packet(adi_record_ids)
    snapshot = {
        "schema_id": "W7TP_TASK_STATE_LOCAL_SNAPSHOT_V1",
        "task": task,
        "selected_actions": selected_actions,
        "checkpoint": checkpoint,
        "native_adi_packet": native_adi_packet,
        "source_hashes": {
            "task_state_sha256": canonical_sha256(task),
            "selected_actions_sha256": canonical_sha256(selected_actions),
            "checkpoint_sha256": canonical_sha256(checkpoint),
            "native_adi_packet_sha256": native_adi_packet["packet_sha256"],
        },
        "git": _git_state(root),
    }
    snapshot["snapshot_sha256"] = canonical_sha256(snapshot)
    return snapshot


def build_task_state_snapshot(
    *,
    task_id: str,
    action_refs: list[str],
    adi_record_ids: list[str],
) -> dict[str, Any]:
    task = _require_string(task_id, "HOLD_TASK_STATE_TASK_ID_INVALID")
    actions = _require_ref_list(
        action_refs,
        "HOLD_TASK_STATE_ACTION_REFS_INVALID",
    )
    adi_ids = _require_ref_list(
        adi_record_ids,
        "HOLD_TASK_STATE_ADI_RECORD_IDS_INVALID",
    )
    return _task_snapshot(
        task_id=task,
        action_refs=actions,
        adi_record_ids=adi_ids,
    )


def build_task_state_recipe(
    *,
    task_id: str,
    action_refs: list[str],
    adi_record_ids: list[str],
) -> dict[str, Any]:
    task = _require_string(task_id, "HOLD_TASK_STATE_TASK_ID_INVALID")
    actions = _require_ref_list(
        action_refs,
        "HOLD_TASK_STATE_ACTION_REFS_INVALID",
    )
    adi_ids = _require_ref_list(
        adi_record_ids,
        "HOLD_TASK_STATE_ADI_RECORD_IDS_INVALID",
    )
    snapshot = build_task_state_snapshot(
        task_id=task,
        action_refs=actions,
        adi_record_ids=adi_ids,
    )
    documents = {
        "task_state.json": {
            "schema_id": snapshot["schema_id"],
            "task": snapshot["task"],
            "source_hashes": snapshot["source_hashes"],
            "git": snapshot["git"],
            "snapshot_sha256": snapshot["snapshot_sha256"],
        },
        "action_state.json": {
            "task_id": task,
            "actions": snapshot["selected_actions"],
        },
        "checkpoint.json": snapshot["checkpoint"],
        "native_adi_packet.json": snapshot["native_adi_packet"],
    }
    rules = [
        {
            "id": f"task-state-{index:02d}",
            "primitive": ALLOWED_RULE_ID,
            "path": path,
            "value": value,
        }
        for index, (path, value) in enumerate(sorted(documents.items()))
    ]
    return {
        "schema_id": RULE_SCHEMA,
        "rules": rules,
        "execution_order": [item["id"] for item in rules],
        "snapshot_sha256": snapshot["snapshot_sha256"],
    }
def execute_task_state_rules(
    output_root: Path,
    rules: list[dict[str, Any]],
    execution_order: list[str],
) -> None:
    if not isinstance(output_root, Path) or not output_root.is_dir():
        raise TaskStateRuleError("HOLD_TASK_STATE_OUTPUT_ROOT_INVALID")
    if (
        not isinstance(rules, list)
        or not isinstance(execution_order, list)
        or len(rules) != len(execution_order)
    ):
        raise TaskStateRuleError("HOLD_TASK_STATE_RULE_SET_INVALID")
    by_id = {
        item.get("id"): item
        for item in rules
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    if set(by_id) != set(execution_order):
        raise TaskStateRuleError("HOLD_TASK_STATE_EXECUTION_ORDER_INVALID")

    for rule_id in execution_order:
        rule = by_id[rule_id]
        if (
            rule.get("primitive") != ALLOWED_RULE_ID
            or set(rule) != {"id", "primitive", "path", "value"}
        ):
            raise TaskStateRuleError("HOLD_TASK_STATE_RULE_INVALID")
        relative = Path(str(rule["path"]))
        if relative.is_absolute() or ".." in relative.parts:
            raise TaskStateRuleError("HOLD_TASK_STATE_RULE_PATH_INVALID")
        target = (output_root / relative).resolve()
        try:
            target.relative_to(output_root.resolve())
        except ValueError as exc:
            raise TaskStateRuleError("HOLD_TASK_STATE_RULE_PATH_ESCAPE") from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(canonical_json_bytes(rule["value"]) + b"\n")
def task_state_manifest(
    output_root: Path,
) -> tuple[list[dict[str, Any]], int, str]:
    rows: list[dict[str, Any]] = []
    total = 0
    for path in sorted(output_root.rglob("*")):
        if not path.is_file():
            continue
        data = path.read_bytes()
        relative = path.relative_to(output_root).as_posix()
        digest = hashlib.sha256(data).hexdigest()
        rows.append(
            {
                "path": relative,
                "size": len(data),
                "sha256": digest,
            }
        )
        total += len(data)
    manifest_sha = canonical_sha256(rows)
    return rows, total, manifest_sha


__all__ = [
    "TaskStateRuleError",
    "build_task_state_recipe",
    "build_task_state_snapshot",
    "execute_task_state_rules",
    "task_state_manifest",
]
