#!/usr/bin/env python3
"""Local gateway for XiaoJ member browser 1B service flow.

The gateway composes the current product contract:

member intent -> 1B action packet -> browser bridge simulation
-> browser bridge return packet -> cloud candidate return packet.

It is intentionally local and pure: no service start, no cloud call, no Odoo,
no POS, no production database, and no runtime SQLite writes.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from jsonschema import validate

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.cloud_proxy.w7tp_openwebui_cloud_proxy import (
    build_cloud_candidate_return_packet,
    dump,
    h,
    validate_cloud_candidate_return_packet,
)
from tools.member_browser.simulate_xiaoj_browser_bridge import simulate, validate_bridge_return
from tools.member_browser.xiaoj_member_browser_1b_controller import (
    build_packet,
    odoo_function_items_for_role,
    ref,
)
from tools.total_field_candidate_gateway import receive_candidate


GATEWAY_SCHEMA = ROOT / "schemas/browser/xiaoj_member_browser_gateway_result_v1.schema.json"
ASSOCIATION_ADMISSION_SCHEMA = ROOT / "schemas/browser/xiaoj_association_usage_admission_packet_v1.schema.json"


def forward_transport_envelope(
    transport_envelope: dict[str, Any],
    *,
    replay_ledger: set[str],
    received_at: dt.datetime | None = None,
) -> dict[str, Any]:
    """Forward one unchanged browser packet through the sole Total Field receiver."""

    return receive_candidate(
        transport_envelope,
        previous_state={},
        observation_domains={},
        browser_replay_ledger=replay_ledger,
        browser_received_at=received_at,
    )


def make_args(args: argparse.Namespace) -> SimpleNamespace:
    return SimpleNamespace(
        intent=args.intent,
        safe_context_ref=args.safe_context_ref,
        member_ref=args.member_ref,
        device_ref=args.device_ref,
        role_ref="member_role_ref",
        site_ref="site_ref:xiaoj_member_browser_gateway",
        key_ref=args.key_ref,
        api_ref=args.api_ref,
        quota_ref=args.quota_ref,
        cost_policy="budget_cap_ref",
        model_tier="small",
        member_preference_ref=args.member_preference_ref,
        service_style_ref=args.service_style_ref,
        behavior_info_ref=args.behavior_info_ref,
        cloud_compute_ref=args.cloud_compute_ref,
        benefit_ref=args.benefit_ref,
        generative_transmission_ref="gt_ref:w7tp_member_browser_gateway_no_plaintext",
        odoo_identity_ref=getattr(args, "odoo_identity_ref", "odoo_identity_ref:member_browser_gateway:demo_identity"),
        odoo_role_ref=getattr(args, "odoo_role_ref", "odoo_role_ref:resident"),
        odoo_function_scope_ref=getattr(args, "odoo_function_scope_ref", "odoo_function_scope_ref:member_daily"),
        odoo_permission_bucket_ref=getattr(args, "odoo_permission_bucket_ref", "odoo_permission_bucket_ref:resident_readonly"),
        payment_tool_ref=getattr(args, "payment_tool_ref", "payment_tool_ref:member_selected_external_tool"),
        management_fee_bill_ref=getattr(args, "management_fee_bill_ref", "management_fee_bill_ref:none"),
        payment_amount_bucket_ref=getattr(args, "payment_amount_bucket_ref", "payment_amount_bucket_ref:not_requested"),
        target_ref="",
        ttl=300,
        counter=1,
    )


def state_from_bridge(bridge_result: dict[str, Any]) -> str:
    if bridge_result.get("reason") == "human_confirm_required_before_write_draft":
        return "HOLD"
    if bridge_result.get("decision") == "BLOCK":
        return "BLOCK"
    if bridge_result.get("browser_bridge_return_packet", {}).get("D5_execution", {}).get("human_confirm_required") is True:
        return "HOLD"
    return "CANDIDATE_READY"


def build_cloud_return(action_packet: dict[str, Any], bridge_result: dict[str, Any], state: str) -> dict[str, Any]:
    job_id = "JOB_" + uuid.uuid4().hex
    cloud_packet = {
        "task_id": "TASK_" + uuid.uuid4().hex,
        "packet_id": "PKT_" + uuid.uuid4().hex,
        "D2_intent": {
            "intent": "member_browser_gateway_candidate",
        },
        "D4_topology": {
            "cloud_lane": "local_gateway_safe_stub",
        },
    }
    candidate = {
        "candidate_id": "CAND_" + uuid.uuid4().hex,
        "risk_flags": [state.lower()],
        "must_not_execute": True,
        "cloud_received_packet_only": True,
        "action_type_ref": action_packet["browser_action"]["action_type"],
        "behavior_info_ref": action_packet["browser_action"]["params"]["behavior_info_ref"],
        "bridge_decision_ref": ref("bridge_decision_ref", bridge_result.get("decision", "UNKNOWN")),
    }
    final_status = "BLOCKED" if state == "BLOCK" else ("HOLD" if state == "HOLD" else "CANDIDATE_READY")
    return_packet = build_cloud_candidate_return_packet(cloud_packet, h(dump(cloud_packet)), job_id, candidate, final_status)
    ok, reason = validate_cloud_candidate_return_packet(return_packet)
    if not ok:
        raise ValueError("cloud_return_packet_invalid:" + reason)
    return return_packet


def admission_decision_from_state(state: str) -> str:
    if state == "BLOCK":
        return "BLOCK"
    if state == "HOLD":
        return "HOLD"
    return "ALLOW"


def build_association_usage_admission_packet(
    action_packet: dict[str, Any],
    bridge_return: dict[str, Any],
    cloud_return: dict[str, Any],
    state: str,
) -> dict[str, Any]:
    params = action_packet["browser_action"]["params"]
    decision = admission_decision_from_state(state)
    odoo_function_item_refs = odoo_function_items_for_role(params["odoo_role_ref"])
    packet = {
        "schema_version": "xiaoj.association_usage_admission_packet.v1",
        "packet_type": "ASSOCIATION_USAGE_ADMISSION_PACKET",
        "admission_packet_id": "ADM_" + uuid.uuid4().hex,
        "candidate_only": True,
        "requires_total_field_verify": True,
        "member_plaintext_transferred": False,
        "secret_transferred": False,
        "raw_browser_page_transferred": False,
        "raw_audio_saved": False,
        "raw_api_key_transferred": False,
        "oauth_token_transferred": False,
        "execution_allowed": False,
        "D1_identity": {
            "association_ref": "association_ref:wuchang_community_governance",
            "member_ref": action_packet["D1_identity"]["actor_ref"],
            "device_ref": action_packet["D1_identity"]["device_ref"],
            "plaintext_identity_forbidden": True,
        },
        "D2_intent": {
            "intent_ref": params["intent_ref"],
            "action_type_ref": ref("action_type_ref", action_packet["browser_action"]["action_type"]),
            "service_scope_ref": params["service_style_ref"],
            "consent_scope_ref": ref("consent_scope_ref", "member_browser_daily_assist_ref_only"),
        },
        "D3_state": {
            "gateway_state": state,
            "quota_bucket_ref": params["quota_bucket_ref"],
            "benefit_ref": params["benefit_ref"],
            "odoo_identity_ref": params["odoo_identity_ref"],
            "odoo_role_ref": params["odoo_role_ref"],
            "odoo_permission_bucket_ref": params["odoo_permission_bucket_ref"],
            "odoo_function_scope_ref": params["odoo_function_scope_ref"],
            "odoo_function_item_set_ref": params["odoo_function_item_set_ref"],
            "payment_tool_ref": params["payment_tool_ref"],
            "management_fee_bill_ref": params["management_fee_bill_ref"],
            "payment_amount_bucket_ref": params["payment_amount_bucket_ref"],
            "payment_intent_ref": params["payment_intent_ref"],
            "cloud_candidate_state": cloud_return["d7_risk"]["final_status_candidate"],
            "ttl_seconds": action_packet["D8_envelope"]["ttl_seconds"],
        },
        "D4_evidence": {
            "gateway_ref": ref(
                "gateway_ref",
                action_packet["D8_envelope"]["content_hash"] + bridge_return["D8_envelope"]["return_packet_hash"],
            ),
            "source_packet_hash": action_packet["D8_envelope"]["content_hash"],
            "browser_return_packet_hash": bridge_return["D8_envelope"]["return_packet_hash"],
            "cloud_return_packet_hash": cloud_return["d8_envelope"]["return_packet_hash"],
            "behavior_info_ref": cloud_return["d4_evidence"]["behavior_info_ref"],
            "action_trace_ref": cloud_return["d4_evidence"]["action_trace_ref"],
            "member_tendency_ref": cloud_return["d4_evidence"]["member_tendency_ref"],
            "odoo_function_item_refs": odoo_function_item_refs,
            "cloud_compute_ref": cloud_return["d3_coordinate"]["cloud_compute_ref"],
            "compute_provider_ref": cloud_return["d3_coordinate"]["compute_provider_ref"],
            "compute_cost_bucket_ref": cloud_return["d3_coordinate"]["compute_cost_bucket_ref"],
        },
        "D5_execution": {
            "admission_decision": decision,
            "execution_allowed": False,
            "allowed_next_actions": [
                "present_candidate_to_member",
                "ask_member_confirm",
                "route_to_total_field_verifier",
            ],
            "forbidden_actions": [
                "member_plaintext_read",
                "secret_read",
                "raw_api_key_read",
                "oauth_token_read",
                "raw_browser_page_read",
                "db_write",
                "odoo_db_write",
                "pos_write",
                "payment_capture",
                "deploy",
                "service_restart",
            ],
            "human_confirm_required": state != "CANDIDATE_READY",
            "odoo_write_authority": False,
            "odoo_member_plaintext_read": False,
            "payment_capture_authority": False,
            "payment_data_transferred": False,
        },
        "D6_generative_transmission": {
            "return_mode": "association_no_plaintext_usage_admission",
            "no_plaintext_context": True,
            "cloud_candidate_only": True,
            "reconstruction_hint_ref": cloud_return["d6_generative_transmission"]["reconstruction_hint_ref"],
            "member_plaintext_transferred": False,
            "secret_transferred": False,
        },
        "D7_risk": {
            "risk_flags": cloud_return["d7_risk"]["risk_flags"],
            "hold_required": state == "HOLD",
            "block_required": state == "BLOCK",
            "legal_review_required": False,
        },
        "D8_envelope": {
            "ttl_seconds": action_packet["D8_envelope"]["ttl_seconds"],
            "nonce": "nonce_ref:" + uuid.uuid4().hex,
            "created_at": action_packet["D8_envelope"]["created_at"],
            "packet_hash": "",
            "total_field_verifier_required": True,
            "replay_protection": True,
        },
    }
    packet["D8_envelope"]["packet_hash"] = ref("admission_packet_hash", dump(packet))
    validate_association_usage_admission_packet(packet)
    return packet


def build_gateway_result(args: argparse.Namespace) -> dict[str, Any]:
    action_packet = build_packet(make_args(args))
    bridge_result = simulate(
        action_packet,
        selected_text=args.selected_text,
        local_draft_text=args.local_draft_text,
        active_field_type=args.active_field_type,
    )
    bridge_return = bridge_result["browser_bridge_return_packet"]
    validate_bridge_return(bridge_return)
    state = state_from_bridge(bridge_result)
    cloud_return = build_cloud_return(action_packet, bridge_result, state)
    association_admission = build_association_usage_admission_packet(
        action_packet,
        bridge_return,
        cloud_return,
        state,
    )
    result = {
        "schema_version": "xiaoj.member_browser_gateway_result.v1",
        "packet_type": "XIAOJ_MEMBER_BROWSER_GATEWAY_RESULT",
        "state": state,
        "candidate_only": True,
        "requires_total_field_verify": True,
        "member_plaintext_transferred": False,
        "secret_transferred": False,
        "raw_audio_saved": False,
        "gateway_ref": ref("gateway_ref", action_packet["D8_envelope"]["content_hash"] + bridge_return["D8_envelope"]["return_packet_hash"]),
        "action_packet": action_packet,
        "browser_bridge_result": {
            k: v for k, v in bridge_result.items() if k != "browser_bridge_return_packet"
        },
        "browser_bridge_return_packet": bridge_return,
        "cloud_candidate_return_packet": cloud_return,
        "association_usage_admission_packet": association_admission,
        "safety_flags": {
            "SECRET_READ": False,
            "MEMBER_PLAINTEXT_READ": False,
            "RAW_AUDIO_SAVED": False,
            "DB_WRITE": False,
            "PAYMENT_CAPTURE": False,
            "SERVICE_RESTART": False,
            "DEPLOY": False,
        },
    }
    validate_gateway_result(result)
    return result


def validate_gateway_result(result: dict[str, Any]) -> None:
    schema = json.loads(GATEWAY_SCHEMA.read_text(encoding="utf-8"))
    validate(result, schema)


def validate_association_usage_admission_packet(packet: dict[str, Any]) -> None:
    schema = json.loads(ASSOCIATION_ADMISSION_SCHEMA.read_text(encoding="utf-8"))
    validate(packet, schema)


def run_smoke() -> int:
    cases = [
        ("summary", "請幫我摘要目前選取的公告文字", "公告測試", "", "textarea", "CANDIDATE_READY"),
        ("open_sidebar", "打開小J側邊欄", "", "", "textarea", "CANDIDATE_READY"),
        ("draft_hold", "請幫我填表草稿", "", "安全草稿", "textarea", "HOLD"),
        ("activity_rsvp_hold", "我要報名社區活動，請先產生候選草稿", "", "活動報名候選", "textarea", "HOLD"),
        ("payment_block", "請幫我直接付款並提交訂單", "", "", "textarea", "BLOCK"),
    ]
    failures: list[str] = []
    for name, intent, selected, draft, field, expected in cases:
        ns = argparse.Namespace(
            intent=intent,
            safe_context_ref="redacted_ref:gateway_smoke",
            selected_text=selected,
            local_draft_text=draft,
            active_field_type=field,
            member_ref="actor_ref:member_browser_gateway:demo_member",
            device_ref="device_ref:member_browser_gateway:demo_device",
            key_ref="key_ref:member_browser_gateway:broker_default",
            api_ref="api_ref:member_browser_gateway:local_1b",
            quota_ref="quota_ref:member_browser_gateway:daily",
            member_preference_ref="preference_ref:member:concise",
            service_style_ref="service_style_ref:community_xiaoj_warm_daily",
            behavior_info_ref="",
            cloud_compute_ref="cloud_compute_ref:local_gateway_safe_stub",
            benefit_ref="benefit_ref:community_ai_member_daily",
            odoo_identity_ref="odoo_identity_ref:gateway_smoke_member",
            odoo_role_ref="odoo_role_ref:resident",
            odoo_function_scope_ref="odoo_function_scope_ref:member_daily",
            odoo_permission_bucket_ref="odoo_permission_bucket_ref:resident_readonly",
            payment_tool_ref="payment_tool_ref:member_selected_external_tool",
            management_fee_bill_ref="management_fee_bill_ref:gateway_smoke",
            payment_amount_bucket_ref="payment_amount_bucket_ref:masked_bucket",
            out="",
        )
        result = build_gateway_result(ns)
        ok = result["state"] == expected
        print(f"CASE_{name}={'PASS' if ok else 'FAIL'} STATE={result['state']}")
        if result["member_plaintext_transferred"] is not False or result["secret_transferred"] is not False:
            ok = False
        if result["cloud_candidate_return_packet"]["d5_execution"]["execution_allowed"] is not False:
            ok = False
        admission = result["association_usage_admission_packet"]
        if admission["execution_allowed"] is not False or admission["member_plaintext_transferred"] is not False:
            ok = False
        if admission["D4_evidence"]["cloud_compute_ref"] == "" or admission["D4_evidence"]["behavior_info_ref"] == "":
            ok = False
        if not admission["D4_evidence"]["odoo_function_item_refs"]:
            ok = False
        if admission["D5_execution"]["odoo_write_authority"] is not False:
            ok = False
        if admission["D5_execution"]["payment_capture_authority"] is not False:
            ok = False
        if not ok:
            failures.append(name)
    print("SECRET_READ=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")
    print("RAW_AUDIO_SAVED=FALSE")
    print("DB_WRITE=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    print("SERVICE_RESTART=FALSE")
    print("DEPLOY=FALSE")
    print("STATE=" + ("PASS_XIAOJ_MEMBER_BROWSER_GATEWAY" if not failures else "FAIL_XIAOJ_MEMBER_BROWSER_GATEWAY"))
    return 0 if not failures else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local XiaoJ member browser gateway.")
    parser.add_argument("--intent", default="")
    parser.add_argument("--safe-context-ref", default="redacted_ref:gateway_default")
    parser.add_argument("--selected-text", default="")
    parser.add_argument("--local-draft-text", default="")
    parser.add_argument("--active-field-type", default="textarea")
    parser.add_argument("--member-ref", default="actor_ref:member_browser_gateway:demo_member")
    parser.add_argument("--device-ref", default="device_ref:member_browser_gateway:demo_device")
    parser.add_argument("--key-ref", default="key_ref:member_browser_gateway:broker_default")
    parser.add_argument("--api-ref", default="api_ref:member_browser_gateway:local_1b")
    parser.add_argument("--quota-ref", default="quota_ref:member_browser_gateway:daily")
    parser.add_argument("--member-preference-ref", default="preference_ref:member:concise")
    parser.add_argument("--service-style-ref", default="service_style_ref:community_xiaoj_warm_daily")
    parser.add_argument("--behavior-info-ref", default="")
    parser.add_argument("--cloud-compute-ref", default="cloud_compute_ref:local_gateway_safe_stub")
    parser.add_argument("--benefit-ref", default="benefit_ref:community_ai_member_daily")
    parser.add_argument("--odoo-identity-ref", default="odoo_identity_ref:member_browser_gateway:demo_identity")
    parser.add_argument("--odoo-role-ref", default="odoo_role_ref:resident")
    parser.add_argument("--odoo-function-scope-ref", default="odoo_function_scope_ref:member_daily")
    parser.add_argument("--odoo-permission-bucket-ref", default="odoo_permission_bucket_ref:resident_readonly")
    parser.add_argument("--payment-tool-ref", default="payment_tool_ref:member_selected_external_tool")
    parser.add_argument("--management-fee-bill-ref", default="management_fee_bill_ref:none")
    parser.add_argument("--payment-amount-bucket-ref", default="payment_amount_bucket_ref:not_requested")
    parser.add_argument("--out", default="")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    if args.smoke:
        return run_smoke()
    if not args.intent:
        parser.error("use --intent or --smoke")
    result = build_gateway_result(args)
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
