#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DECISION = "safe_local_7d_automation_smoke_gate_plan_only"

REQUIRED_VALUES = {
    "mode": "plan_only",
    "authority": "local_xiaoj_router",
    "local_only": True,
    "push_allowed": False,
    "remote_required": False,
    "cloud_call_allowed": False,
    "runtime_execution_allowed": False,
}

REQUIRED_LISTS = {
    "contracts_to_validate": {
        "M31A_xiaoj_converged_governance_architecture",
        "M32A_tri_party_7d_runtime_dryrun",
        "M32B_nl_to_7d_task_packet",
        "M32C_dual_brain_metrics_capture"
    },
    "linter_paths": {
        "tools/xiaoj_converged_governance_architecture_linter.py",
        "tools/w7tp_tri_party_7d_runtime_dryrun_linter.py",
        "tools/w7tp_nl_to_7d_task_packet_linter.py",
        "tools/xiaoj_dual_brain_metrics_capture_linter.py"
    },
    "template_paths": {
        "configs/dev/xiaoj_converged_governance_architecture.template.json",
        "configs/dev/w7tp_tri_party_7d_runtime_dryrun.template.json",
        "configs/dev/w7tp_nl_to_7d_task_packet.template.json",
        "configs/dev/xiaoj_dual_brain_metrics_capture.template.json"
    },
    "success_decisions": {
        "safe_xiaoj_converged_governance_plan_only",
        "safe_tri_party_7d_runtime_dryrun",
        "safe_nl_to_7d_task_packet_plan_only",
        "safe_dual_brain_metrics_capture_plan_only"
    },
    "forbidden_actions": {
        "git_push",
        "git_add_dot",
        "git_add_all",
        "read_api_key",
        "cloud_api_call",
        "ssh_remote_command",
        "docker_run",
        "service_restart",
        "formal_db_write"
    }
}

FALSE_FLAGS = (
    "git_push",
    "remote_required",
    "cloud_call",
    "api_key_read",
    "raw_pii_read",
    "ssh",
    "container_start",
    "service_restart"
)

def require_members(obj: dict[str, Any], field: str, required: set[str], errors: list[str]) -> None:
    values = obj.get(field, [])
    if not isinstance(values, list):
        errors.append(f"{field}_must_be_array")
        return
    present = {str(v) for v in values}
    for item in sorted(required - present):
        errors.append(f"missing_{field}:{item}")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="configs/dev/w7tp_local_7d_automation_smoke_gate.template.json")
    args = parser.parse_args()

    errors: list[str] = []
    try:
        obj = json.loads(Path(args.file).read_text(encoding="utf-8"))
    except Exception as exc:
        obj = {}
        errors.append(f"invalid_json:{exc}")

    for key, expected in REQUIRED_VALUES.items():
        if obj.get(key) != expected:
            errors.append(f"{key}_must_be_{expected}")

    for field, required in REQUIRED_LISTS.items():
        require_members(obj, field, required, errors)

    flags = obj.get("action_flags", {})
    if not isinstance(flags, dict):
        errors.append("action_flags_must_be_object")
        flags = {}

    for flag in FALSE_FLAGS:
        if flags.get(flag) is not False:
            errors.append(f"action_flags.{flag}_must_be_false")

    result = {
        "decision": DECISION if not errors else "rejected",
        "errors": errors,
        "warnings": [],
        "git_push": False,
        "cloud_call": False,
        "api_key_read": False,
        "raw_pii_read": False,
        "ssh": False,
        "container_start": False
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 2

if __name__ == "__main__":
    raise SystemExit(main())
