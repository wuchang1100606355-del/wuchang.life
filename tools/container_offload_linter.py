#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT = Path("configs/containers/container_offload_registry.template.json")

REQUIRED_TOP = ["registry_version", "domain", "mode", "containers"]

FORBIDDEN_TASKS_FOR_RISK = [
    "git_commit",
    "router_write",
    "ssh_remote_command",
    "credential_read",
    "formal_db_write"
]

FORBIDDEN_MOUNT_HINTS = [
    ".env",
    "keys",
    ".ssh",
    "private_key",
    "router_inventory_redacted.local.json",
    "postgres_data",
    "raw_member_data"
]

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def lint(obj: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for k in REQUIRED_TOP:
        if k not in obj:
            errors.append(f"missing_top_field:{k}")

    if obj.get("mode") != "plan_only":
        errors.append("mode_must_be_plan_only")

    if obj.get("no_ssh") is not True:
        warnings.append("no_ssh_not_true")

    if obj.get("no_container_move") is not True:
        warnings.append("no_container_move_not_true")

    containers = obj.get("containers", [])
    if not isinstance(containers, list) or not containers:
        errors.append("containers_must_be_nonempty_array")

    for c in containers:
        name = c.get("name", "unknown")
        mode = c.get("execution_mode", "")
        restart = c.get("restart_policy_recommended", "")
        risk = c.get("risk", "")

        for k in ["name", "current_host", "target_host", "class", "execution_mode", "risk"]:
            if not c.get(k):
                errors.append(f"{name}:missing_field:{k}")

        if "one_shot" in mode and restart == "unless-stopped":
            errors.append(f"{name}:one_shot_must_not_use_unless_stopped")

        if risk in ("medium", "high", "critical"):
            forbidden_tasks = set(c.get("forbidden_tasks", []))
            for task in FORBIDDEN_TASKS_FOR_RISK:
                if task not in forbidden_tasks:
                    warnings.append(f"{name}:forbidden_task_missing:{task}")

        forbidden_mounts = " ".join(c.get("forbidden_mounts", []))
        for hint in FORBIDDEN_MOUNT_HINTS:
            if hint not in forbidden_mounts and name == "wuchang_os_indexer":
                warnings.append(f"{name}:forbidden_mount_hint_missing:{hint}")

    return errors, warnings

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(DEFAULT))
    args = ap.parse_args()

    path = Path(args.file)
    obj = load_json(path)
    errors, warnings = lint(obj)
    decision = "safe_plan_only" if not errors else "rejected"

    print(json.dumps({
        "decision": decision,
        "file": str(path),
        "errors": errors,
        "warnings": warnings,
        "container_count": len(obj.get("containers", [])),
        "ssh": False,
        "restart": False,
        "container_move": False
    }, ensure_ascii=False, indent=2))

    return 0 if not errors else 2

if __name__ == "__main__":
    raise SystemExit(main())
