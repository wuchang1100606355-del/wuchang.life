#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT = Path("configs/packets/tri_party_7d_packet.template.json")

REQUIRED_PARTIES = {
    "local_xiaoj_router",
    "code_agent",
    "cloud_provider_lane",
}

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
}


def lint_packet(packet: dict[str, object]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if packet.get("mode") != "plan_only":
        errors.append("mode_must_be_plan_only")

    if packet.get("authority") != "local_xiaoj_router":
        errors.append("authority_must_be_local_xiaoj_router")

    parties = set(packet.get("parties", []))
    for party in sorted(REQUIRED_PARTIES - parties):
        errors.append(f"missing_party:{party}")

    if packet.get("cloud_allowed") is not False:
        errors.append("cloud_allowed_must_default_false")

    risk_policy = packet.get("d5_risk_policy", {})
    if not isinstance(risk_policy, dict):
        errors.append("d5_risk_policy_must_be_object")
    elif (
        risk_policy.get("risk_level") == "high"
        and (
            risk_policy.get("human_review_required") is not True
            or packet.get("human_review_required") is not True
        )
    ):
        errors.append("high_risk_requires_human_review")

    forbidden_payload = set(packet.get("forbidden_payload", []))
    for item in sorted(REQUIRED_FORBIDDEN_PAYLOAD - forbidden_payload):
        errors.append(f"missing_forbidden_payload:{item}")

    forbidden_actions = set(packet.get("forbidden_actions", []))
    for item in sorted(REQUIRED_FORBIDDEN_ACTIONS - forbidden_actions):
        errors.append(f"missing_forbidden_action:{item}")

    if packet.get("audit_hash_required") is not True:
        errors.append("audit_hash_required_must_be_true")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the plan-only W7TP tri-party 7D packet template."
    )
    parser.add_argument("--file", default=str(DEFAULT))
    args = parser.parse_args()

    path = Path(args.file)
    try:
        packet = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(packet, dict):
            errors = ["packet_must_be_object"]
            warnings: list[str] = []
        else:
            errors, warnings = lint_packet(packet)
    except (OSError, json.JSONDecodeError):
        errors = ["packet_unreadable_or_invalid_json"]
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
                "container_start": False
            },
            ensure_ascii=False,
            indent=2
        )
    )
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
