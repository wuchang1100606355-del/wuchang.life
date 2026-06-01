#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

DECISION = "safe_local_7d_automation_smoke_runner"

REQUIRED_VALUES = {
    "mode": "local_smoke_only",
    "authority": "local_xiaoj_router",
    "git_push_allowed": False,
    "cloud_call_allowed": False,
    "api_key_read_allowed": False,
    "raw_pii_read_allowed": False,
    "runtime_write_allowed": False
}

REQUIRED_TARGETS = {"M31A", "M32A", "M32B", "M32C", "M33A"}

REQUIRED_FORBIDDEN = {
    "git_push",
    "set_origin",
    "git_add_dot",
    "git_add_all",
    "read_api_key",
    "cloud_api_call",
    "ssh_remote_command",
    "docker_run",
    "service_restart",
    "formal_db_write",
    "runtime_report_commit"
}

FALSE_FLAGS = (
    "git_push",
    "origin_set",
    "cloud_call",
    "api_key_read",
    "raw_pii_read",
    "ssh",
    "container_start",
    "service_restart",
    "runtime_write"
)

def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def run_linter(job: dict[str, Any]) -> dict[str, Any]:
    task_id = str(job.get("task_id", "unknown"))
    linter = Path(str(job.get("linter", "")))
    template = Path(str(job.get("template", "")))
    expected = str(job.get("expected_decision", ""))

    if not linter.is_file():
        return {"task_id": task_id, "ok": False, "error": f"missing_linter:{linter}"}
    if not template.is_file():
        return {"task_id": task_id, "ok": False, "error": f"missing_template:{template}"}

    proc = subprocess.run(
        [sys.executable, str(linter), "--file", str(template)],
        text=True,
        capture_output=True,
        check=False
    )

    if proc.returncode != 0:
        return {
            "task_id": task_id,
            "ok": False,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip()
        }

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return {"task_id": task_id, "ok": False, "error": f"invalid_linter_json:{exc}", "stdout": proc.stdout}

    ok = payload.get("decision") == expected and payload.get("errors") == []
    return {
        "task_id": task_id,
        "ok": ok,
        "decision": payload.get("decision"),
        "errors": payload.get("errors")
    }

def validate_config(obj: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    for key, expected in REQUIRED_VALUES.items():
        if obj.get(key) != expected:
            errors.append(f"{key}_must_be_{expected}")

    targets = set(obj.get("runner_targets", []))
    for item in sorted(REQUIRED_TARGETS - targets):
        errors.append(f"missing_runner_target:{item}")

    forbidden = set(obj.get("forbidden_actions", []))
    for item in sorted(REQUIRED_FORBIDDEN - forbidden):
        errors.append(f"missing_forbidden_action:{item}")

    flags = obj.get("action_flags", {})
    if not isinstance(flags, dict):
        errors.append("action_flags_must_be_object")
        flags = {}

    for flag in FALSE_FLAGS:
        if flags.get(flag) is not False:
            errors.append(f"action_flags.{flag}_must_be_false")

    jobs = obj.get("linter_jobs", [])
    if not isinstance(jobs, list) or len(jobs) < 5:
        errors.append("linter_jobs_must_include_five_targets")

    return errors

def main() -> int:
    parser = argparse.ArgumentParser(description="Run local 7D automation smoke checks.")
    parser.add_argument("--file", default="configs/dev/w7tp_local_7d_automation_smoke_runner.template.json")
    args = parser.parse_args()

    errors: list[str] = []
    try:
        obj = load_json(Path(args.file))
    except Exception as exc:
        result = {
            "decision": "rejected",
            "errors": [f"invalid_config:{exc}"],
            "warnings": [],
            "git_push": False,
            "cloud_call": False,
            "api_key_read": False,
            "raw_pii_read": False,
            "ssh": False,
            "container_start": False
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    errors.extend(validate_config(obj))

    target_results = []
    if not errors:
        for job in obj.get("linter_jobs", []):
            result = run_linter(job)
            target_results.append(result)
            if not result.get("ok"):
                errors.append(f"{result.get('task_id')}_failed")

    output = {
        "decision": DECISION if not errors else "rejected",
        "errors": errors,
        "warnings": [],
        "target_results": target_results,
        "git_push": False,
        "cloud_call": False,
        "api_key_read": False,
        "raw_pii_read": False,
        "ssh": False,
        "container_start": False
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if not errors else 2

if __name__ == "__main__":
    raise SystemExit(main())
