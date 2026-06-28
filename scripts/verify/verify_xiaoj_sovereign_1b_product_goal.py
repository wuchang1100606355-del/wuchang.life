#!/usr/bin/env python3
"""Verify the full XiaoJ sovereign 1B product goal.

This is an aggregate local verifier for the thread objective. It runs the
website, cockpit, and release verifiers, then directly checks representative
8D packets for user tendency refs, warm service style refs, cloud compute refs,
behavior refs, no-plaintext association admission, public activity RSVP, and
management-fee payment-intent boundaries.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.member_browser.xiaoj_member_browser_1b_controller import build_packet
from tools.member_browser.xiaoj_member_browser_gateway import build_gateway_result


def fail(message: str) -> None:
    print(f"FAIL={message}")
    print("SECRET_READ=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")
    print("RAW_API_KEY_OUTPUT=FALSE")
    print("RAW_AUDIO_SAVED=FALSE")
    print("DB_WRITE=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    print("SERVICE_RESTART=FALSE")
    print("DEPLOY=FALSE")
    print("STATE=HOLD_XIAOJ_SOVEREIGN_1B_PRODUCT_GOAL")
    raise SystemExit(1)


def check(condition: bool, name: str) -> None:
    print(f"{name}={'PASS' if condition else 'FAIL'}")
    if not condition:
        fail(name)


def run_state(script: str, expected: str) -> None:
    proc = subprocess.run([sys.executable, script], cwd=ROOT, text=True, capture_output=True, check=False)
    if proc.returncode != 0 or expected not in proc.stdout:
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        fail(f"{script} did not produce {expected}")
    print(f"{Path(script).name}={expected}")


def controller_args(intent: str, safe_context_ref: str = "redacted_ref:goal_verify") -> argparse.Namespace:
    return argparse.Namespace(
        intent=intent,
        safe_context_ref=safe_context_ref,
        member_ref="actor_ref:sovereign_1b_goal:demo_member",
        device_ref="device_ref:sovereign_1b_goal:demo_device",
        role_ref="member_role_ref",
        site_ref="site_ref:sovereign_1b_goal",
        key_ref="key_ref:sovereign_1b_goal:broker_default",
        api_ref="api_ref:sovereign_1b_goal:local_1b",
        quota_ref="quota_ref:sovereign_1b_goal:daily",
        cost_policy="budget_cap_ref",
        model_tier="small",
        member_preference_ref="preference_ref:member:concise_accessible_daily",
        service_style_ref="service_style_ref:community_xiaoj_warm_daily",
        behavior_info_ref="",
        cloud_compute_ref="cloud_compute_ref:local_1b_first_cloud_candidate_if_needed",
        benefit_ref="benefit_ref:community_ai_member_daily",
        generative_transmission_ref="gt_ref:w7tp_sovereign_1b_no_plaintext",
        odoo_identity_ref="odoo_identity_ref:goal_demo_member",
        odoo_role_ref="odoo_role_ref:resident",
        odoo_function_scope_ref="odoo_function_scope_ref:member_daily",
        odoo_permission_bucket_ref="odoo_permission_bucket_ref:resident_readonly",
        payment_tool_ref="payment_tool_ref:member_selected_external_tool",
        management_fee_bill_ref="management_fee_bill_ref:masked_current_cycle",
        payment_amount_bucket_ref="payment_amount_bucket_ref:masked_bucket",
        target_ref="",
        ttl=300,
        counter=1,
        out="",
    )


def gateway_args(intent: str, selected_text: str = "", draft: str = "") -> argparse.Namespace:
    return argparse.Namespace(
        intent=intent,
        safe_context_ref="redacted_ref:goal_gateway",
        selected_text=selected_text,
        local_draft_text=draft,
        active_field_type="textarea",
        member_ref="actor_ref:sovereign_1b_gateway:demo_member",
        device_ref="device_ref:sovereign_1b_gateway:demo_device",
        key_ref="key_ref:sovereign_1b_gateway:broker_default",
        api_ref="api_ref:sovereign_1b_gateway:local_1b",
        quota_ref="quota_ref:sovereign_1b_gateway:daily",
        member_preference_ref="preference_ref:member:concise_accessible_daily",
        service_style_ref="service_style_ref:community_xiaoj_warm_daily",
        behavior_info_ref="",
        cloud_compute_ref="cloud_compute_ref:local_gateway_safe_stub",
        benefit_ref="benefit_ref:community_ai_member_daily",
        odoo_identity_ref="odoo_identity_ref:goal_gateway_member",
        odoo_role_ref="odoo_role_ref:resident",
        odoo_function_scope_ref="odoo_function_scope_ref:member_daily",
        odoo_permission_bucket_ref="odoo_permission_bucket_ref:resident_readonly",
        payment_tool_ref="payment_tool_ref:member_selected_external_tool",
        management_fee_bill_ref="management_fee_bill_ref:masked_current_cycle",
        payment_amount_bucket_ref="payment_amount_bucket_ref:masked_bucket",
        out="",
    )


def assert_packet_common(packet: dict, label: str) -> None:
    params = packet["browser_action"]["params"]
    check(packet["packet_type"] == "xiaoj_8d_action_packet", f"{label}_PACKET_TYPE")
    check(packet["D4_topology"]["channel"] == "browser_action_bus", f"{label}_BROWSER_ACTION_BUS")
    check(packet["D5_resource"]["model_tier"] == "small", f"{label}_MODEL_TIER_SMALL")
    check(packet["browser_action"]["dry_run"] is True, f"{label}_DRY_RUN")
    check(packet["browser_action"]["submit_forbidden"] is True, f"{label}_SUBMIT_FORBIDDEN")
    check(params["candidate_only"] is True, f"{label}_CANDIDATE_ONLY")
    check(params["requires_total_field_verify"] is True, f"{label}_TOTAL_FIELD_VERIFY")
    check(params["member_preference_ref"].startswith("preference_ref:"), f"{label}_MEMBER_PREFERENCE_REF")
    check(params["service_style_ref"] == "service_style_ref:community_xiaoj_warm_daily", f"{label}_WARM_SERVICE_STYLE")
    check(params["behavior_info_ref"].startswith("behavior_ref:"), f"{label}_BEHAVIOR_REF")
    check(params["cloud_compute_ref"].startswith("cloud_compute_ref:"), f"{label}_CLOUD_COMPUTE_REF")
    check(params["generative_transmission_ref"].startswith("gt_ref:"), f"{label}_GENERATIVE_TRANSMISSION_REF")
    check(params["odoo_identity_ref"].startswith("odoo_identity_ref:"), f"{label}_ODOO_IDENTITY_REF")
    check(params["odoo_role_ref"].startswith("odoo_role_ref:"), f"{label}_ODOO_ROLE_REF")
    check(params["odoo_write_authority"] is False, f"{label}_ODOO_WRITE_FALSE")
    check(params["odoo_member_plaintext_read"] is False, f"{label}_ODOO_MEMBER_PLAINTEXT_FALSE")
    check(params["payment_capture_authority"] is False, f"{label}_PAYMENT_CAPTURE_FALSE")
    check(params["payment_data_transferred"] is False, f"{label}_PAYMENT_DATA_FALSE")


def verify_controller_packets() -> None:
    summary = build_packet(controller_args("請依照我的偏好，用溫暖簡潔方式摘要目前公告"))
    assert_packet_common(summary, "SUMMARY")
    check(summary["browser_action"]["action_type"] == "read_text_ref", "SUMMARY_READ_TEXT_ACTION")

    activity = build_packet(controller_args("我要參加五常公園熱舞社運動社團", "redacted_ref:hot_dance_public_activity"))
    assert_packet_common(activity, "ACTIVITY")
    check(activity["D2_intent"]["transaction_intent"] == "activity_rsvp_candidate", "ACTIVITY_RSVP_INTENT")
    check(activity["browser_action"]["action_type"] == "write_draft_ref", "ACTIVITY_WRITE_DRAFT_ACTION")
    check(activity["D6_governance"]["human_confirm_required"] is True, "ACTIVITY_HUMAN_CONFIRM")
    check(activity["browser_action"]["params"]["public_activity_cache_ref"] == "public_activity_cache_ref:web/community_activities.json", "ACTIVITY_PUBLIC_CACHE_REF")

    payment = build_packet(controller_args("我要用支付工具繳管理費"))
    assert_packet_common(payment, "PAYMENT")
    check(payment["D2_intent"]["transaction_intent"] == "payment_intent_requires_human", "PAYMENT_INTENT_REQUIRES_HUMAN")
    check(payment["browser_action"]["action_type"] == "route_to_connector_ref", "PAYMENT_ROUTE_TO_CONNECTOR")
    check("odoo_function_ref:resident.management_fee_payment_intent_candidate" in payment["browser_action"]["params"]["odoo_function_item_refs_csv"], "PAYMENT_ODOO_FUNCTION_REF")


def verify_gateway_admission() -> None:
    result = build_gateway_result(gateway_args("請幫我摘要目前選取的公告文字", selected_text="公告測試"))
    check(result["state"] == "CANDIDATE_READY", "GATEWAY_SUMMARY_READY")
    check(result["candidate_only"] is True, "GATEWAY_CANDIDATE_ONLY")
    check(result["member_plaintext_transferred"] is False, "GATEWAY_MEMBER_PLAINTEXT_FALSE")
    check(result["secret_transferred"] is False, "GATEWAY_SECRET_FALSE")
    check(result["raw_audio_saved"] is False, "GATEWAY_RAW_AUDIO_FALSE")

    bridge = result["browser_bridge_return_packet"]
    cloud = result["cloud_candidate_return_packet"]
    admission = result["association_usage_admission_packet"]

    check(bridge["D6_generative_transmission"]["cloud_compute_ref"].startswith("cloud_compute_ref:"), "BRIDGE_CLOUD_COMPUTE_REF")
    check(bridge["D4_evidence"]["behavior_info_ref"].startswith("behavior_ref:"), "BRIDGE_BEHAVIOR_REF")
    check(cloud["candidate_only"] is True, "CLOUD_CANDIDATE_ONLY")
    check(cloud["d5_execution"]["execution_allowed"] is False, "CLOUD_EXECUTION_FALSE")
    check(cloud["d3_coordinate"]["cloud_compute_ref"].startswith("CLOUD_COMPUTE_REF:"), "CLOUD_COMPUTE_REF")
    check(cloud["d4_evidence"]["behavior_info_ref"].startswith("BEHAVIOR_INFO_REF:"), "CLOUD_BEHAVIOR_REF")
    check(cloud["d4_evidence"]["member_tendency_ref"].startswith("MEMBER_TENDENCY_REF:"), "CLOUD_MEMBER_TENDENCY_REF")

    check(admission["packet_type"] == "ASSOCIATION_USAGE_ADMISSION_PACKET", "ADMISSION_PACKET_TYPE")
    check(admission["candidate_only"] is True, "ADMISSION_CANDIDATE_ONLY")
    check(admission["execution_allowed"] is False, "ADMISSION_EXECUTION_FALSE")
    check(admission["member_plaintext_transferred"] is False, "ADMISSION_MEMBER_PLAINTEXT_FALSE")
    check(admission["secret_transferred"] is False, "ADMISSION_SECRET_FALSE")
    check(admission["raw_api_key_transferred"] is False, "ADMISSION_RAW_API_KEY_FALSE")
    check(admission["oauth_token_transferred"] is False, "ADMISSION_OAUTH_TOKEN_FALSE")
    check(admission["D4_evidence"]["cloud_compute_ref"].startswith("CLOUD_COMPUTE_REF:"), "ADMISSION_CLOUD_COMPUTE_REF")
    check(admission["D4_evidence"]["behavior_info_ref"].startswith("BEHAVIOR_INFO_REF:"), "ADMISSION_BEHAVIOR_REF")
    check(admission["D4_evidence"]["member_tendency_ref"].startswith("MEMBER_TENDENCY_REF:"), "ADMISSION_MEMBER_TENDENCY_REF")
    check(admission["D6_generative_transmission"]["no_plaintext_context"] is True, "ADMISSION_NO_PLAINTEXT_CONTEXT")
    check(admission["D6_generative_transmission"]["cloud_candidate_only"] is True, "ADMISSION_CLOUD_CANDIDATE_ONLY")
    check(admission["D5_execution"]["odoo_write_authority"] is False, "ADMISSION_ODOO_WRITE_FALSE")
    check(admission["D5_execution"]["payment_capture_authority"] is False, "ADMISSION_PAYMENT_CAPTURE_FALSE")

    activity_result = build_gateway_result(gateway_args("我要報名五常公園熱舞社運動社團", draft="活動報名候選"))
    check(activity_result["state"] == "HOLD", "GATEWAY_ACTIVITY_RSVP_HOLD")
    check(activity_result["association_usage_admission_packet"]["D5_execution"]["human_confirm_required"] is True, "GATEWAY_ACTIVITY_HUMAN_CONFIRM")


def verify_static_product_sources() -> None:
    modelfile = (ROOT / "tools/member_browser/Modelfile.xiaoj-member-browser-1b").read_text(encoding="utf-8")
    spec = (ROOT / "docs/total_field/XIAOJ_MEMBER_BROWSER_1B_CONTROL_SPEC.md").read_text(encoding="utf-8")
    activity = json.loads((ROOT / "web/community_activities.json").read_text(encoding="utf-8"))
    active = json.loads((ROOT / "runtime/member_browser/ACTIVE_XIAOJ_MEMBER_BROWSER_RELEASE.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / active["manifest"]).read_text(encoding="utf-8"))
    source_paths = {row["path"] for row in manifest["included_sources"]}

    for snippet in ["服務熱誠", "CANDIDATE_ONLY=TRUE", "cloud_compute_ref", "behavior_info_ref"]:
        check(snippet in modelfile, f"MODELFILE_SNIPPET_{snippet}")
    for snippet in ["warm community", "member_preference_ref", "ASSOCIATION_USAGE_ADMISSION_PACKET", "CLOUD_CANDIDATE_RETURN_PACKET"]:
        check(snippet in spec, f"SPEC_SNIPPET_{snippet}")
    check(activity["activities"][0]["activity_ref"] == "activity_ref:wuchang_park_hot_dance_weekday_2000", "PUBLIC_ACTIVITY_SEED")
    check("scripts/verify/verify_xiaoj_sovereign_1b_product_goal.py" in source_paths, "RELEASE_INCLUDES_GOAL_VERIFIER")
    check("docs/total_field/XIAOJ_SOVEREIGN_1B_PRODUCT_GOAL_ACCEPTANCE.md" in source_paths, "RELEASE_INCLUDES_GOAL_ACCEPTANCE_DOC")


def main() -> int:
    run_state("scripts/verify/verify_wuchang_website_quality.py", "STATE=PASS_WUCHANG_WEBSITE_QUALITY")
    run_state("scripts/verify/verify_xiaoj_member_browser_cockpit.py", "STATE=PASS_XIAOJ_MEMBER_BROWSER_COCKPIT")
    run_state("scripts/verify/verify_xiaoj_member_browser_release.py", "STATE=PASS_XIAOJ_MEMBER_BROWSER_RELEASE")
    verify_controller_packets()
    verify_gateway_admission()
    verify_static_product_sources()

    print("STATE=PASS_XIAOJ_SOVEREIGN_1B_PRODUCT_GOAL")
    print("PRODUCT_GRADE_MVP=TRUE")
    print("CANDIDATE_ONLY=TRUE")
    print("REQUIRES_TOTAL_FIELD_VERIFY=TRUE")
    print("SECRET_READ=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")
    print("RAW_API_KEY_OUTPUT=FALSE")
    print("RAW_AUDIO_SAVED=FALSE")
    print("DB_WRITE=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    print("SERVICE_RESTART=FALSE")
    print("DEPLOY=FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
