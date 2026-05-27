#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT = Path("configs/cloud/local_xiaoj_cloud_api_broker_dryrun.template.json")
REQUIRED_PROVIDER_LANES = {"openai", "gemini", "google", "custom"}
REQUIRED_ROUTING_POLICY = {
    "local_first",
    "cloud_compute_only",
    "deny_by_default",
}
REQUIRED_FORBIDDEN_PAYLOAD = {
    "token",
    "password",
    "private_key",
    "credentials",
    "raw_member_pii",
}
REQUIRED_FORBIDDEN_ACTIONS = {
    "real_cloud_api_call",
    "api_key_read",
    "credential_export",
    "raw_pii_cloud_upload",
    "router_write",
    "ssh_remote_command",
    "formal_db_write",
}


def lint_broker(broker: dict[str, object]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if broker.get("mode") != "dry_run_only":
        errors.append("mode_must_be_dry_run_only")
    if broker.get("authority") != "local_xiaoj_router":
        errors.append("authority_must_be_local_xiaoj_router")
    if broker.get("cloud_call_allowed") is not False:
        errors.append("cloud_call_allowed_must_be_false")
    if broker.get("api_key_read_allowed") is not False:
        errors.append("api_key_read_allowed_must_be_false")
    if broker.get("secret_saved") is not False:
        errors.append("secret_saved_must_be_false")

    provider_lanes = set(broker.get("provider_lanes", []))
    for lane in sorted(REQUIRED_PROVIDER_LANES - provider_lanes):
        errors.append(f"missing_provider_lane:{lane}")

    routing_policy = set(broker.get("routing_policy", []))
    for policy in sorted(REQUIRED_ROUTING_POLICY - routing_policy):
        errors.append(f"missing_routing_policy:{policy}")

    forbidden_payload = set(broker.get("forbidden_payload", []))
    for item in sorted(REQUIRED_FORBIDDEN_PAYLOAD - forbidden_payload):
        errors.append(f"missing_forbidden_payload:{item}")

    forbidden_actions = set(broker.get("forbidden_actions", []))
    for item in sorted(REQUIRED_FORBIDDEN_ACTIONS - forbidden_actions):
        errors.append(f"missing_forbidden_action:{item}")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the local-only W7TP cloud API broker dry-run contract."
    )
    parser.add_argument("--file", default=str(DEFAULT))
    args = parser.parse_args()

    path = Path(args.file)
    try:
        broker = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(broker, dict):
            errors, warnings = lint_broker(broker)
        else:
            errors = ["broker_must_be_object"]
            warnings: list[str] = []
    except (OSError, json.JSONDecodeError):
        errors = ["broker_unreadable_or_invalid_json"]
        warnings = []

    decision = "safe_dry_run_only" if not errors else "rejected"
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
