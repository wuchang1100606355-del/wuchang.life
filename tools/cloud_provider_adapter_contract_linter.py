#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT = Path("configs/cloud/cloud_provider_adapter_contract.template.json")

REQUIRED_PROVIDERS = {"openai", "gemini", "google", "custom"}
REQUIRED_FORBIDDEN_PAYLOAD = {
    "token",
    "password",
    "private_key",
    "credentials",
    "raw_member_pii",
}
REQUIRED_FORBIDDEN_ACTIONS = {
    "router_write",
    "ssh_remote_command",
    "formal_db_write",
    "credential_export",
    "raw_pii_cloud_upload",
}


def lint_contract(contract: dict[str, object]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if contract.get("mode") != "plan_only":
        errors.append("mode_must_be_plan_only")

    if contract.get("authority") != "local_xiaoj_router":
        errors.append("authority_must_be_local_xiaoj_router")

    if contract.get("cloud_is_compute_only") is not True:
        errors.append("cloud_is_compute_only_must_be_true")

    if contract.get("direct_action_allowed") is not False:
        errors.append("direct_action_allowed_must_be_false")

    if contract.get("api_key_read_allowed") is not False:
        errors.append("api_key_read_allowed_must_be_false")

    if contract.get("cloud_call_performed_by_this_contract") is not False:
        errors.append("cloud_call_performed_by_this_contract_must_be_false")

    providers = set(contract.get("providers", []))
    for provider in sorted(REQUIRED_PROVIDERS - providers):
        errors.append(f"missing_provider:{provider}")

    forbidden_payload = set(contract.get("forbidden_payload", []))
    for item in sorted(REQUIRED_FORBIDDEN_PAYLOAD - forbidden_payload):
        errors.append(f"missing_forbidden_payload:{item}")

    forbidden_actions = set(contract.get("forbidden_actions", []))
    for item in sorted(REQUIRED_FORBIDDEN_ACTIONS - forbidden_actions):
        errors.append(f"missing_forbidden_action:{item}")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the plan-only W7TP cloud provider adapter contract."
    )
    parser.add_argument("--file", default=str(DEFAULT))
    args = parser.parse_args()

    path = Path(args.file)
    try:
        contract = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(contract, dict):
            errors, warnings = lint_contract(contract)
        else:
            errors = ["contract_must_be_object"]
            warnings: list[str] = []
    except (OSError, json.JSONDecodeError):
        errors = ["contract_unreadable_or_invalid_json"]
        warnings = []

    decision = "safe_plan_only" if not errors else "rejected"
    print(
        json.dumps(
            {
                "decision": decision,
                "file": str(path),
                "errors": errors,
                "warnings": warnings,
                "cloud_call": False,
                "api_key_read": False,
                "secret_saved": False,
                "ssh": False,
                "container_start": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
