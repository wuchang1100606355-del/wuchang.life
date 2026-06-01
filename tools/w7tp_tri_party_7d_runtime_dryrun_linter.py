#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DECISION = "safe_tri_party_7d_runtime_dryrun"

REQUIRED = {
    "tri_party_roles": {
        "local_xiaoj_router",
        "code_agent_lane",
        "cloud_provider_lane"
    },
    "visibility_split": {
        "local_xiaoj_router_view",
        "code_agent_view",
        "cloud_provider_redacted_view"
    },
    "runtime_flow": {
        "receive_7d_packet",
        "validate_schema",
        "split_visibility",
        "route_decision_dryrun",
        "policy_gate_check",
        "dead_letter_check",
        "generate_lane_packet",
        "return_dryrun_report"
    },
    "route_decision": {
        "local_small_llm",
        "code_agent_plan",
        "cloud_provider_redacted",
        "human_review",
        "dead_letter"
    },
    "required_packet_fields": {
        "task_id",
        "intent_summary",
        "allowed_files",
        "forbidden_actions",
        "validation_commands",
        "evidence_chain_required",
        "risk_level",
        "privacy_boundary",
        "audit_hash_required"
    },
    "forbidden_payload": {
        "token",
        "password",
        "private_key",
        "credentials",
        "raw_member_pii",
        "user_cloud_key",
        "router_secret",
        "formal_db_write_authority"
    },
    "forbidden_actions": {
        "read_api_key",
        "save_api_key",
        "cloud_api_call",
        "code_agent_execute",
        "ssh_remote_command",
        "router_write",
        "formal_db_write",
        "docker_run",
        "docker_compose_up",
        "service_restart",
        "git_add_dot",
        "git_add_all",
        "raw_pii_cloud_upload",
        "harm_human_or_community"
    }
}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    args = parser.parse_args()

    errors = []
    try:
        data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    except Exception as exc:
        data = {}
        errors.append(f"invalid_json:{exc}")

    fixed = {
        "mode": "dry_run_only",
        "authority": "local_xiaoj_router",
        "runtime_execution_allowed": False,
        "cloud_call_allowed": False,
        "code_agent_execution_allowed": False,
        "formal_write_allowed": False
    }

    for key, expected in fixed.items():
        if data.get(key) != expected:
            errors.append(f"{key}:expected={expected!r}:actual={data.get(key)!r}")

    for key, required_items in REQUIRED.items():
        actual = set(data.get(key, []))
        for missing in sorted(required_items - actual):
            errors.append(f"{key}_missing:{missing}")

    result = {
        "decision": DECISION if not errors else "rejected",
        "errors": errors,
        "warnings": [],
        "runtime_executed": False,
        "cloud_call": False,
        "code_agent_executed": False,
        "api_key_read": False,
        "raw_pii_read": False,
        "formal_write": False,
        "ssh": False,
        "container_start": False
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 2

if __name__ == "__main__":
    raise SystemExit(main())
