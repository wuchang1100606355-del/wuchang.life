#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DECISION = "safe_nl_to_7d_task_packet_plan_only"

FALSE_FLAGS = (
    "model_started",
    "cloud_call",
    "api_key_read",
    "raw_pii_read",
    "secret_saved",
    "ssh",
    "container_start",
)

REQUIRED_VALUES = {
    "mode": "plan_only",
    "authority": "local_xiaoj_router",
    "model_call_allowed": False,
    "cloud_call_allowed": False,
    "prediction_policy.prediction_first_allowed": True,
    "prediction_policy.prediction_must_not_claim_verified": True,
    "prediction_policy.validation_required_before_commit": True,
}

REQUIRED_LISTS = {
    "generator_input": {"natural_language_request", "user_context_redacted", "task_domain", "risk_hint"},
    "generator_output": {"task_id", "intent_summary", "allowed_files", "forbidden_actions", "validation_commands", "commit_message", "focused_git_status", "evidence_chain_required", "risk_level", "privacy_boundary", "human_review_required"},
    "packet_state": {"predicted", "pending_validation", "verified", "rejected", "human_review"},
    "forbidden_payload": {"token", "password", "private_key", "credentials", "raw_member_pii", "user_cloud_key", "router_secret"},
    "forbidden_actions": {"read_api_key", "save_api_key", "cloud_api_call", "ssh_remote_command", "router_write", "formal_db_write", "docker_run", "docker_compose_up", "service_restart", "git_add_dot", "git_add_all", "raw_pii_cloud_upload"},
}

def get_path(obj: dict[str, Any], dotted_path: str) -> Any:
    value: Any = obj
    for part in dotted_path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value

def require_members(obj: dict[str, Any], field: str, required: set[str], errors: list[str]) -> None:
    values = obj.get(field, [])
    if not isinstance(values, list):
        errors.append(f"{field}_must_be_array")
        return
    present = {str(value) for value in values}
    for item in sorted(required - present):
        errors.append(f"missing_{field}:{item}")

def base_result(decision: str, errors: list[str], warnings: list[str]) -> dict[str, object]:
    result: dict[str, object] = {"decision": decision, "errors": errors, "warnings": warnings}
    for flag in FALSE_FLAGS:
        result[flag] = False
    return result

def validate(path: Path) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return base_result("rejected", [f"invalid_json:{exc}"], warnings)

    if not isinstance(obj, dict):
        return base_result("rejected", ["root_must_be_object"], warnings)

    for field, expected in REQUIRED_VALUES.items():
        if get_path(obj, field) != expected:
            errors.append(f"{field}_must_be_{expected}")

    action_flags = obj.get("action_flags", {})
    if not isinstance(action_flags, dict):
        errors.append("action_flags_must_be_object")
        action_flags = {}
    for flag in FALSE_FLAGS:
        if action_flags.get(flag) is not False:
            errors.append(f"action_flags.{flag}_must_be_false")

    for field, required in REQUIRED_LISTS.items():
        require_members(obj, field, required, errors)

    return base_result(DECISION if not errors else "rejected", errors, warnings)

def main() -> int:
    parser = argparse.ArgumentParser(description="Validate W7TP natural language to 7D task packet generator contract.")
    parser.add_argument("--file", default="configs/dev/w7tp_nl_to_7d_task_packet.template.json")
    args = parser.parse_args()
    result = validate(Path(args.file))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["decision"] == DECISION else 2

if __name__ == "__main__":
    raise SystemExit(main())
