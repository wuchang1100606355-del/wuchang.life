#!/usr/bin/env python3
from __future__ import annotations

import json
import argparse
from pathlib import Path

DEFAULT = Path("configs/containers/wuchang_indexer_oneshot_job.template.json")

REQUIRED_FALSE = [
    "auto_commit",
    "ssh_allowed",
    "container_start_allowed_by_this_manifest",
]

REQUIRED_FORBIDDEN_PATHS = [
    "/",
    ".env",
    "keys",
    ".ssh",
    "private_key",
    "configs/merlin/router_inventory_redacted.local.json",
    "Taiji_Odoo/postgres_data",
    "raw_member_data",
]

REQUIRED_FORBIDDEN_TASKS = [
    "git_commit",
    "git_push",
    "router_write",
    "ssh_remote_command",
    "credential_read",
    "formal_db_write",
    "raw_member_pii_read",
]

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(DEFAULT))
    args = ap.parse_args()

    path = Path(args.file)
    obj = json.loads(path.read_text(encoding="utf-8"))

    errors = []
    warnings = []

    if obj.get("packet_version") != "W7TP-CONTAINER-JOB/0.1":
        errors.append("invalid_packet_version")

    if obj.get("source_container") != "wuchang_os_indexer":
        errors.append("source_container_must_be_wuchang_os_indexer")

    if obj.get("restart_policy") != "no":
        errors.append("restart_policy_must_be_no")

    if obj.get("execution_mode") != "one_shot_or_scheduled":
        errors.append("execution_mode_must_be_one_shot_or_scheduled")

    for k in REQUIRED_FALSE:
        if obj.get(k) is not False:
            errors.append(f"{k}_must_be_false")

    forbidden_paths = set(obj.get("forbidden_paths", []))
    for item in REQUIRED_FORBIDDEN_PATHS:
        if item not in forbidden_paths:
            errors.append(f"missing_forbidden_path:{item}")

    forbidden_tasks = set(obj.get("forbidden_tasks", []))
    for item in REQUIRED_FORBIDDEN_TASKS:
        if item not in forbidden_tasks:
            errors.append(f"missing_forbidden_task:{item}")

    if obj.get("target_host") in ("msi", "local"):
        warnings.append("target_host_should_prefer_pure_linux_server")

    decision = "safe_plan_only" if not errors else "rejected"

    print(json.dumps({
        "decision": decision,
        "file": str(path),
        "errors": errors,
        "warnings": warnings,
        "ssh": False,
        "restart": False,
        "container_start": False,
        "container_move": False,
    }, ensure_ascii=False, indent=2))

    return 0 if not errors else 2

if __name__ == "__main__":
    raise SystemExit(main())
