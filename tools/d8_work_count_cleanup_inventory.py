#!/usr/bin/env python3
"""Inventory D8 mandatory-workflow counts and cleanup candidates.

This tool is intentionally read-only by default. It never deletes, moves, or
rewrites workflow artifacts. With --write-report it writes a JSON report only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "runtime/total_field/codex_mandatory_workflow"
REPORT_DIR = ROOT / "runtime/d8_db/reports"


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def parse_dt(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        parsed = dt.datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.UTC)
        return parsed.astimezone(dt.UTC)
    except Exception:
        return None


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "_read_error": str(exc),
            "_path": path.relative_to(ROOT).as_posix(),
        }


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def collect() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    task_dir = WORKFLOW / "tasks"
    result_dir = WORKFLOW / "results"
    seal_dir = WORKFLOW / "seals"

    tasks = []
    for path in sorted(task_dir.glob("D8_MANDATORY_TASK_*.json")):
        data = read_json(path)
        tasks.append({
            "path": rel(path),
            "task_id": data.get("task_id"),
            "task_name": data.get("task_name"),
            "created_at": data.get("created_at"),
            "preflight_decision": data.get("preflight_decision"),
            "mode": data.get("mode"),
            "read_error": data.get("_read_error"),
        })

    results = []
    for path in sorted(result_dir.glob("D8_MANDATORY_RESULT_*.json")):
        data = read_json(path)
        results.append({
            "path": rel(path),
            "task_id": data.get("task_id"),
            "task_name": data.get("task_name"),
            "task_state": data.get("task_state"),
            "created_at": data.get("created_at"),
            "seal": data.get("seal"),
            "writeback_report": data.get("writeback_report"),
            "read_error": data.get("_read_error"),
        })

    seals = []
    for path in sorted(seal_dir.glob("D8_MANDATORY_TASK_RESULT_*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        task_id = None
        task_name = None
        task_state = None
        for line in text.splitlines():
            if line.startswith("TASK_ID="):
                task_id = line.split("=", 1)[1].strip()
            elif line.startswith("TASK_NAME="):
                task_name = line.split("=", 1)[1].strip()
            elif line.startswith("TASK_STATE="):
                task_state = line.split("=", 1)[1].strip()
        seals.append({
            "path": rel(path),
            "task_id": task_id,
            "task_name": task_name,
            "task_state": task_state,
            "mtime_utc": dt.datetime.fromtimestamp(path.stat().st_mtime, dt.UTC).isoformat(),
        })

    return tasks, results, seals


def build_report(retain_latest_per_task_name: int, archive_after_days: int) -> dict[str, Any]:
    now = utc_now()
    tasks, results, seals = collect()

    result_by_task_id = defaultdict(list)
    for result in results:
        if result["task_id"]:
            result_by_task_id[result["task_id"]].append(result)

    task_by_id = {task["task_id"]: task for task in tasks if task["task_id"]}
    by_name = defaultdict(list)
    for task in tasks:
        by_name[task.get("task_name") or "UNKNOWN"].append(task)

    task_decisions = Counter(task.get("preflight_decision") or "UNKNOWN" for task in tasks)
    result_states = Counter(result.get("task_state") or "UNKNOWN" for result in results)
    seal_states = Counter(seal.get("task_state") or "UNKNOWN" for seal in seals)

    orphan_tasks = [
        task for task in tasks
        if task.get("task_id") and not result_by_task_id.get(task["task_id"])
    ]
    orphan_results = [
        result for result in results
        if result.get("task_id") and result["task_id"] not in task_by_id
    ]

    duplicate_groups = []
    archive_candidates = []
    protected_states = {"WARN", "HOLD", "BLOCK", "FAIL", "ERROR"}

    for task_name, group in sorted(by_name.items()):
        ordered = sorted(
            group,
            key=lambda item: parse_dt(item.get("created_at")) or dt.datetime.min.replace(tzinfo=dt.UTC),
            reverse=True,
        )
        if len(ordered) > 1:
            duplicate_groups.append({
                "task_name": task_name,
                "count": len(ordered),
                "latest": ordered[0]["path"],
                "older_count": max(0, len(ordered) - 1),
            })
        for index, task in enumerate(ordered):
            created = parse_dt(task.get("created_at"))
            age_days = (now - created).days if created else None
            related_results = result_by_task_id.get(task.get("task_id"), [])
            result_state_set = {r.get("task_state") for r in related_results if r.get("task_state")}
            is_protected = bool(result_state_set & protected_states)
            is_old_extra = index >= retain_latest_per_task_name
            is_aged = age_days is not None and age_days >= archive_after_days
            if is_old_extra and is_aged and not is_protected:
                archive_candidates.append({
                    "task_id": task.get("task_id"),
                    "task_name": task_name,
                    "task_path": task.get("path"),
                    "age_days": age_days,
                    "reason": "older_than_retention_and_not_protected",
                    "suggested_action": "archive_only_after_separate_total_field_pass",
                })

    return {
        "schema": "D8_WORK_COUNT_CLEANUP_INVENTORY_V1",
        "generated_at": now.isoformat(),
        "mode": "inventory_only_no_delete",
        "workflow_root": rel(WORKFLOW),
        "retention_policy": {
            "retain_latest_per_task_name": retain_latest_per_task_name,
            "archive_after_days": archive_after_days,
            "protected_states": sorted(protected_states),
        },
        "counts": {
            "tasks": len(tasks),
            "results": len(results),
            "seals": len(seals),
            "orphan_tasks_without_result": len(orphan_tasks),
            "orphan_results_without_task": len(orphan_results),
            "duplicate_task_name_groups": len(duplicate_groups),
            "archive_candidates": len(archive_candidates),
        },
        "task_preflight_decisions": dict(sorted(task_decisions.items())),
        "result_states": dict(sorted(result_states.items())),
        "seal_states": dict(sorted(seal_states.items())),
        "orphan_tasks_without_result": orphan_tasks,
        "orphan_results_without_task": orphan_results,
        "duplicate_task_name_groups": duplicate_groups,
        "archive_candidates": archive_candidates,
        "hard_walls": {
            "delete": False,
            "move": False,
            "rewrite": False,
            "secret_read": False,
            "member_plaintext_read": False,
            "odoo_db_write": False,
            "service_restart": False,
            "deploy": False,
        },
        "next_allowed_action": "review_archive_candidates_then_open_separate_total_field_archive_land_task",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory D8 work counts and cleanup candidates.")
    parser.add_argument("--retain-latest-per-task-name", type=int, default=3)
    parser.add_argument("--archive-after-days", type=int, default=14)
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    report = build_report(args.retain_latest_per_task_name, args.archive_after_days)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))

    if args.write_report:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = utc_now().strftime("%Y%m%d_%H%M%S")
        out = REPORT_DIR / f"D8_WORK_COUNT_CLEANUP_INVENTORY_{stamp}.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"REPORT={rel(out)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
