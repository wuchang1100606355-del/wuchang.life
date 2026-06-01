#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DECISION = "safe_xiaoj_converged_governance_plan_only"

REQUIRED_FORBIDDEN_PAYLOAD = {
    "token", "password", "private_key", "credentials",
    "raw_member_pii", "user_cloud_key", "router_secret",
    "formal_db_write_authority"
}

REQUIRED_FORBIDDEN_ACTIONS = {
    "read_api_key", "save_api_key", "infer_identity_from_wifi_only",
    "expose_user_cloud_key_to_group", "send_raw_pii_to_group_lane",
    "access_member_profile_without_session", "access_payment_without_verification",
    "ssh_remote_command", "router_write", "formal_db_write",
    "docker_run", "docker_compose_up", "service_restart",
    "git_add_dot", "git_add_all", "raw_pii_cloud_upload",
    "harm_human_or_community"
}

def get_path(data: dict, path: str):
    cur = data
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    args = parser.parse_args()

    errors: list[str] = []
    try:
        data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    except Exception as exc:
        data = {}
        errors.append(f"invalid_json:{exc}")

    checks = {
        "mode": "plan_only",
        "authority": "local_xiaoj_router",
        "xiaoj_is_not_single_llm": True,
        "architecture_type": "local_first_intent_field",
        "eastern_ai_principle.not_mysticism": True,
        "dual_brain_unified_design.intention_and_engineering_unified": True,
        "dual_brain_unified_design.front_brain_cannot_override_hardwall": True,
        "dual_brain_unified_design.rear_brain_can_block_high_risk_action": True,
        "verification_ethics.unknown_allowed": True,
        "verification_ethics.validation_before_claim": True,
        "verification_ethics.prediction_must_not_claim_verified": True,
        "group_member_compute_switch.wifi_presence_only_is_not_identity": True,
        "guest_network_wake_handshake.identity_verified_by_wifi": False,
        "group_member_compute_switch.raw_pii_allowed_to_group_lane": False,
        "group_member_compute_switch.user_cloud_key_visible_to_group_lane": False,
        "member_pii_governance.external_use_allowed": False,
        "member_pii_governance.data_sale_allowed": False,
        "three_key_usb_custody.founder_alone_raw_pii_access_allowed": False,
        "three_key_usb_custody.secretary_general_decrypt_alone_allowed": False,
        "one_way_privacy_gate.raw_pii_output_allowed": False,
        "lost_device_recovery.identity_proof_required_before_suspend_or_transfer": True
    }

    for path, expected in checks.items():
        actual = get_path(data, path)
        if actual != expected:
            errors.append(f"{path}:expected={expected!r}:actual={actual!r}")

    payload = set(data.get("forbidden_payload", []))
    actions = set(data.get("forbidden_actions", []))
    for item in sorted(REQUIRED_FORBIDDEN_PAYLOAD - payload):
        errors.append(f"forbidden_payload_missing:{item}")
    for item in sorted(REQUIRED_FORBIDDEN_ACTIONS - actions):
        errors.append(f"forbidden_action_missing:{item}")

    result = {
        "decision": DECISION if not errors else "rejected",
        "errors": errors,
        "warnings": [],
        "model_started": False,
        "cloud_call": False,
        "api_key_read": False,
        "raw_pii_read": False,
        "raw_pii_output": False,
        "secret_saved": False,
        "wifi_scanned": False,
        "router_accessed": False,
        "ssh": False,
        "container_start": False
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 2

if __name__ == "__main__":
    raise SystemExit(main())
