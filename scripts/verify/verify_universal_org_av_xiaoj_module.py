#!/usr/bin/env python3
from __future__ import annotations

import ast
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONTRACT = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/contracts/universal_org_av_xiaoj_contract.json"
SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/universal_org_av_xiaoj.py"
SPEC = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/docs/total_field/W7TP_UNIVERSAL_ORG_AV_XIAOJ_MODULE_SPEC.md"


def fail(msg: str) -> None:
    print("STATE=HOLD_UNIVERSAL_ORG_AV_XIAOJ_MODULE_VERIFY")
    print(f"ERROR={msg}")
    raise SystemExit(1)


def load_service_module():
    module_name = "universal_org_av_xiaoj_verified"
    spec = importlib.util.spec_from_file_location(module_name, SERVICE)
    if spec is None or spec.loader is None:
        fail("service_import_spec_failed")

    mod = importlib.util.module_from_spec(spec)

    # Python 3.12 dataclasses 需要 module 先存在於 sys.modules。
    sys.modules[module_name] = mod

    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    for path in [CONTRACT, SERVICE, SPEC]:
        if not path.exists():
            fail(f"missing:{path}")

    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if data.get("state") != "W7TP_UNIVERSAL_ORG_AV_XIAOJ_MODULE_CONTRACT":
        fail("bad_contract_state")

    safety = data.get("safety", {})
    required_false = [
        "raw_audio_saved",
        "raw_audio_cloud",
        "raw_video_saved",
        "member_plaintext_read",
        "secret_read",
        "db_write",
        "restart",
        "deploy",
        "router_write",
        "payment_capture",
        "door_open_without_total_field",
    ]
    bad = [k for k in required_false if safety.get(k) is not False]
    if bad:
        fail("safety_not_false:" + ",".join(bad))

    ast.parse(SERVICE.read_text(encoding="utf-8"), filename=str(SERVICE))
    mod = load_service_module()

    roles = mod.list_roles()
    expected_roles = {
        "business_counter_xiaoj",
        "property_counter_xiaoj",
        "community_bulletin_xiaoj",
        "developer_total_field_ui_xiaoj",
    }
    if set(roles) != expected_roles:
        fail("role_set_mismatch")

    blocked_cases = [
        ("business_counter_xiaoj", "payment_capture"),
        ("property_counter_xiaoj", "door_open"),
        ("community_bulletin_xiaoj", "fundraising_payment"),
        ("developer_total_field_ui_xiaoj", "unconfirmed_restart"),
        ("developer_total_field_ui_xiaoj", "raw_secret_read"),
    ]
    for role, action in blocked_cases:
        result = mod.classify_action(role, action)
        if result.get("state") != "BLOCK_HARD_RISK" or result.get("allowed") is not False:
            fail(f"blocked_case_failed:{role}:{action}:{result}")

    pass_cases = [
        ("business_counter_xiaoj", "greeting"),
        ("property_counter_xiaoj", "visitor_guidance"),
        ("community_bulletin_xiaoj", "public_notice"),
        ("developer_total_field_ui_xiaoj", "dry_run_builder"),
    ]
    for role, action in pass_cases:
        result = mod.classify_action(role, action)
        if result.get("state") != "PASS_CANDIDATE_ACTION" or result.get("allowed") is not True:
            fail(f"pass_case_failed:{role}:{action}:{result}")

    packet = mod.build_8d_ui_packet(
        "developer_total_field_ui_xiaoj",
        "ref:test_user_text",
        "verify_builder",
    )
    required_packet_keys = [
        "D1_Intent",
        "D2_State",
        "D3_Coordinate",
        "D4_Evidence",
        "D5_Execution",
        "D6_GenerativeTransmission",
        "D7_RiskQuarantine",
        "D8_Envelope",
    ]
    for key in required_packet_keys:
        if key not in packet:
            fail(f"packet_missing:{key}")

    if packet["D4_Evidence"]["raw_audio_saved"] is not False:
        fail("packet_raw_audio_saved_not_false")

    print("STATE=PASS_UNIVERSAL_ORG_AV_XIAOJ_MODULE_VERIFY")
    print(f"CONTRACT={CONTRACT}")
    print(f"SERVICE={SERVICE}")
    print(f"SPEC={SPEC}")
    print("ROLES=business_counter_xiaoj,property_counter_xiaoj,community_bulletin_xiaoj,developer_total_field_ui_xiaoj")
    print("RAW_AUDIO_SAVED=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")
    print("SECRET_READ=FALSE")
    print("DB_WRITE=FALSE")
    print("RESTART=FALSE")
    print("DEPLOY=FALSE")


if __name__ == "__main__":
    main()
