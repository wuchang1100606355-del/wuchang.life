#!/usr/bin/env python3
"""XiaoJ member browser 1B controller.

This tool creates dry-run 8D browser action packets for a member-owned
browser cockpit. It does not control a browser directly, does not read browser
secrets, and does not submit forms. A local 1B-class model may be used upstream
to phrase the intent, but this controller keeps the execution surface symbolic
and verifier-gated.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple


SAFE_BROWSER_ACTIONS = {
    "navigate_ref",
    "click_ref",
    "fill_ref",
    "select_ref",
    "read_text_ref",
    "screenshot_ref",
    "wait_ref",
    "extract_ref",
    "open_sidebar_ref",
    "close_sidebar_ref",
    "render_sidebar_ref",
    "read_context_ref",
    "write_draft_ref",
    "route_to_connector_ref",
    "broker_api_call_ref",
    "cache_lookup_ref",
    "read_menu_ref",
    "create_order_draft_ref",
    "queue_service_ref",
    "notify_staff_ref",
    "ask_human_confirm",
    "handoff_to_human",
}

FORBIDDEN_ACTIONS = [
    "login_with_plaintext",
    "submit_payment",
    "submit_order_without_human",
    "read_raw_cookie",
    "read_raw_local_storage",
    "write_database",
    "router_change",
    "tailscale_change",
    "dns_change",
    "service_restart",
    "docker_restart",
    "systemctl_restart",
]

SENSITIVE_PATTERNS = {
    "raw_secret": re.compile(r"(sk-[A-Za-z0-9_-]{10,}|api[_-]?key\s*[:=]\s*\S+|password\s*[:=]\s*\S+|secret\s*[:=]\s*\S+)", re.I),
    "phone_like": re.compile(r"(?:\+?886[- ]?)?09\d{2}[- ]?\d{3}[- ]?\d{3}"),
    "email_like": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "raw_storage": re.compile(r"(cookie|localStorage|sessionStorage|bearer\s+)", re.I),
}

ODOO_ROLE_FUNCTION_ITEMS = {
    "resident": [
        "odoo_function_ref:resident.notice_read",
        "odoo_function_ref:resident.activity_query",
        "odoo_function_ref:resident.activity_rsvp_candidate",
        "odoo_function_ref:resident.benefit_masked_read",
        "odoo_function_ref:resident.management_fee_masked_read",
        "odoo_function_ref:resident.management_fee_payment_intent_candidate",
        "odoo_function_ref:resident.service_request_draft",
        "odoo_function_ref:resident.personal_status_masked",
    ],
    "owner": [
        "odoo_function_ref:owner.notice_read",
        "odoo_function_ref:owner.activity_query",
        "odoo_function_ref:owner.activity_rsvp_candidate",
        "odoo_function_ref:owner.hoa_issue_summary",
        "odoo_function_ref:owner.management_fee_masked_read",
        "odoo_function_ref:owner.management_fee_payment_intent_candidate",
        "odoo_function_ref:owner.property_document_summary",
        "odoo_function_ref:owner.benefit_masked_read",
        "odoo_function_ref:owner.service_request_draft",
    ],
    "consumer": [
        "odoo_function_ref:consumer.menu_read",
        "odoo_function_ref:consumer.benefit_masked_read",
        "odoo_function_ref:consumer.points_bucket_read",
        "odoo_function_ref:consumer.activity_query",
        "odoo_function_ref:consumer.activity_rsvp_candidate",
        "odoo_function_ref:consumer.order_draft_candidate",
    ],
    "merchant_staff": [
        "odoo_function_ref:merchant_staff.menu_ops_summary",
        "odoo_function_ref:merchant_staff.order_candidate_review",
        "odoo_function_ref:merchant_staff.customer_service_draft",
        "odoo_function_ref:merchant_staff.campaign_summary",
        "odoo_function_ref:merchant_staff.inventory_notice_summary",
    ],
    "committee": [
        "odoo_function_ref:committee.announcement_draft",
        "odoo_function_ref:committee.activity_notice_draft",
        "odoo_function_ref:committee.issue_summary",
        "odoo_function_ref:committee.vote_summary",
        "odoo_function_ref:committee.maintenance_ticket_summary",
        "odoo_function_ref:committee.finance_public_summary",
    ],
    "property_staff": [
        "odoo_function_ref:property_staff.work_order_summary",
        "odoo_function_ref:property_staff.facility_booking_summary",
        "odoo_function_ref:property_staff.activity_notice_route",
        "odoo_function_ref:property_staff.announcement_draft",
        "odoo_function_ref:property_staff.emergency_notice_route",
        "odoo_function_ref:property_staff.service_request_triage",
    ],
    "operator": [
        "odoo_function_ref:operator.gateway_health_summary",
        "odoo_function_ref:operator.audit_dashboard_summary",
        "odoo_function_ref:operator.role_function_catalog_review",
        "odoo_function_ref:operator.redaction_review",
        "odoo_function_ref:operator.release_readiness_summary",
    ],
}


def canonical_json(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ref(prefix: str, value: str) -> str:
    return f"{prefix}:{sha256_hex(value)[:16]}"


def normalize_ref(prefix: str, value: str) -> str:
    value = (value or "").strip()
    if re.match(r"^[A-Za-z0-9_]+_ref:[A-Za-z0-9_./:-]+$", value):
        return value
    return ref(prefix, value or "none")


def normalize_quota_bucket_ref(value: str) -> str:
    normalized = normalize_ref("quota_bucket_ref", value)
    if normalized.startswith("quota_ref:"):
        return "quota_bucket_ref:" + normalized.split(":", 1)[1]
    return normalized


def normalize_odoo_role_ref(value: str) -> str:
    value = (value or "").strip()
    if value.startswith("odoo_role_ref:"):
        role = value.split(":", 1)[1]
    else:
        role = value
    role = re.sub(r"[^A-Za-z0-9_./:-]+", "_", role or "resident")
    if role not in ODOO_ROLE_FUNCTION_ITEMS:
        role = "resident"
    return "odoo_role_ref:" + role


def odoo_role_key(odoo_role_ref: str) -> str:
    return odoo_role_ref.split(":", 1)[1] if ":" in odoo_role_ref else "resident"


def odoo_function_items_for_role(odoo_role_ref: str) -> List[str]:
    return ODOO_ROLE_FUNCTION_ITEMS.get(odoo_role_key(odoo_role_ref), ODOO_ROLE_FUNCTION_ITEMS["resident"])


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def detect_boundary_hits(text: str) -> List[str]:
    hits = [name for name, pattern in SENSITIVE_PATTERNS.items() if pattern.search(text)]
    member_plaintext_terms = ["會員明文", "身分證", "身份證", "完整姓名", "完整地址"]
    if any(term in text for term in member_plaintext_terms):
        hits.append("member_plaintext_term")
    payment_terms = ["直接付款", "提交付款", "自動扣款", "刷卡號", "payment capture", "capture payment"]
    if any(term.lower() in text.lower() for term in payment_terms):
        hits.append("payment_term")
    return sorted(set(hits))


def choose_action(intent: str, boundary_hits: List[str]) -> Tuple[str, str, str, str]:
    text = intent.lower()
    if boundary_hits:
        return "handoff_to_human", "governance_review", "blocked", "blocked"
    if any(token in intent for token in ["側邊欄", "小J", "打開"]):
        return "open_sidebar_ref", "browse", "low", "dry_run"
    if any(token in intent for token in ["翻譯", "translate"]):
        return "read_text_ref", "browse", "low", "dry_run"
    if any(token in intent for token in ["摘要", "summarize", "解釋", "explain"]):
        return "read_text_ref", "browse", "low", "dry_run"
    if any(token in intent for token in ["管理費", "繳費", "繳管理費", "支付管理費", "maintenance fee"]):
        return "route_to_connector_ref", "payment_intent_requires_human", "medium", "pending_verify"
    wants_activity_rsvp = (
        any(token in intent for token in ["活動報名", "報名活動", "參加活動", "志工報名", "熱舞社報名", "RSVP", "rsvp"])
        or (any(token in intent for token in ["活動", "志工", "熱舞社", "運動社團"]) and any(token in intent for token in ["報名", "參加", "RSVP", "rsvp"]))
    )
    if wants_activity_rsvp:
        return "write_draft_ref", "activity_rsvp_candidate", "medium", "dry_run"
    if any(token in intent for token in ["填表", "表單", "草稿", "draft", "填寫"]):
        return "write_draft_ref", "service_request", "medium", "dry_run"
    if any(token in intent for token in ["菜單", "menu", "活動", "公告", "福利"]):
        return "cache_lookup_ref", "browse", "low", "dry_run"
    if any(token in intent for token in ["點", "下單", "訂單", "order"]):
        return "create_order_draft_ref", "order_draft", "medium", "dry_run"
    if any(token in text for token in ["notify", "remind", "提醒"]):
        return "notify_staff_ref", "service_request", "medium", "dry_run"
    return "read_context_ref", "browse", "low", "dry_run"


def build_packet(args: argparse.Namespace) -> Dict[str, Any]:
    boundary_hits = detect_boundary_hits(args.intent + "\n" + args.safe_context_ref)
    action_type, transaction_intent, risk_level, task_state = choose_action(args.intent, boundary_hits)
    human_confirm_required = risk_level in {"medium", "high", "blocked"} or action_type in {"create_order_draft_ref", "handoff_to_human"}
    browser_state = "blocked" if risk_level == "blocked" else "dry_run"
    order_state = "draft" if action_type == "create_order_draft_ref" else "none"
    if risk_level == "blocked":
        order_state = "blocked"

    safe_context_ref = normalize_ref("redacted_ref", args.safe_context_ref)
    member_preference_ref = normalize_ref("preference_ref", args.member_preference_ref)
    service_style_ref = normalize_ref("service_style_ref", args.service_style_ref)
    behavior_info_ref = normalize_ref("behavior_ref", args.behavior_info_ref or args.intent + action_type)
    cloud_compute_ref = normalize_ref("cloud_compute_ref", args.cloud_compute_ref)
    benefit_ref = normalize_ref("benefit_ref", args.benefit_ref)
    quota_bucket_ref = normalize_quota_bucket_ref(args.quota_ref)
    generative_transmission_ref = normalize_ref("gt_ref", args.generative_transmission_ref)
    odoo_identity_ref = normalize_ref("odoo_identity_ref", args.odoo_identity_ref)
    odoo_role_ref = normalize_odoo_role_ref(args.odoo_role_ref)
    odoo_function_items = odoo_function_items_for_role(odoo_role_ref)
    odoo_function_item_set_ref = ref("odoo_function_item_set_ref", "|".join(odoo_function_items))
    odoo_permission_bucket_ref = normalize_ref("odoo_permission_bucket_ref", args.odoo_permission_bucket_ref or odoo_role_ref)
    odoo_function_scope_ref = normalize_ref("odoo_function_scope_ref", args.odoo_function_scope_ref or odoo_role_ref)
    payment_tool_ref = normalize_ref("payment_tool_ref", args.payment_tool_ref)
    management_fee_bill_ref = normalize_ref("management_fee_bill_ref", args.management_fee_bill_ref)
    payment_amount_bucket_ref = normalize_ref("payment_amount_bucket_ref", args.payment_amount_bucket_ref)
    payment_intent_ref = ref(
        "payment_intent_ref",
        f"{args.member_ref}:{management_fee_bill_ref}:{payment_amount_bucket_ref}:{payment_tool_ref}",
    )
    target_ref = args.target_ref or ref("target_ref", args.intent + safe_context_ref)
    packet = {
        "packet_type": "xiaoj_8d_action_packet",
        "D1_identity": {
            "actor_ref": args.member_ref,
            "actor_type": "member",
            "device_ref": args.device_ref,
            "role": args.role_ref,
            "plaintext_identity_forbidden": True,
        },
        "D2_intent": {
            "primary_intent": ref("intent_ref", args.intent),
            "secondary_intent": safe_context_ref,
            "transaction_intent": transaction_intent,
            "risk_level": risk_level,
        },
        "D3_state": {
            "session_state": "active",
            "task_state": task_state,
            "browser_state": browser_state,
            "order_state": order_state,
            "context_mode": "ref_only",
        },
        "D4_topology": {
            "channel": "browser_action_bus",
            "site_ref": args.site_ref,
            "device_topology": "member_browser_to_total_field",
            "origin_scope": "member_owned",
        },
        "D5_resource": {
            "key_policy": "hybrid_ref_only",
            "selected_key_ref": args.key_ref,
            "api_refs": [args.api_ref],
            "model_tier": args.model_tier,
            "cache_policy": "ref_cache_only",
            "cost_policy": args.cost_policy,
        },
        "D6_governance": {
            "allowed_actions": sorted(SAFE_BROWSER_ACTIONS),
            "forbidden_actions": FORBIDDEN_ACTIONS,
            "no_plaintext_context": True,
            "human_confirm_required": human_confirm_required,
            "staff_confirm_required": action_type in {"create_order_draft_ref", "notify_staff_ref"},
        },
        "D7_verification": {
            "redaction_check_required": True,
            "leak_check_required": True,
            "action_allowlist_required": True,
            "response_verify_required": True,
            "usage_log_required": True,
        },
        "D8_envelope": {
            "packet_ref": "packet_ref:xiaoj_member_browser_1b:" + uuid.uuid4().hex[:16],
            "nonce": "nonce_ref:" + uuid.uuid4().hex,
            "counter": args.counter,
            "ttl_seconds": args.ttl,
            "created_at": now_iso(),
            "schema_version": "8d.packet.v1",
            "content_hash": "",
            "hmac_ref": "hmac_ref:xiaoj_member_browser_1b:verifier_required",
            "signature_ref": "signature_ref:xiaoj_member_browser_1b:verifier_required",
            "replay_protection": True,
        },
        "browser_action": {
            "action_ref": "action_ref:xiaoj_member_browser_1b:" + uuid.uuid4().hex[:16],
            "action_type": action_type,
            "target_ref": target_ref,
            "params": {
                "controller_ref": "controller_ref:xiaoj_member_browser_1b",
                "intent_ref": ref("intent_ref", args.intent),
                "safe_context_ref": safe_context_ref,
                "member_preference_ref": member_preference_ref,
                "service_style_ref": service_style_ref,
                "behavior_info_ref": behavior_info_ref,
                "cloud_compute_ref": cloud_compute_ref,
                "benefit_ref": benefit_ref,
                "quota_bucket_ref": quota_bucket_ref,
                "public_activity_cache_ref": "public_activity_cache_ref:web/community_activities.json"
                if any(token in args.intent for token in ["活動", "志工", "熱舞社", "運動社團"])
                else "public_activity_cache_ref:none",
                "odoo_identity_ref": odoo_identity_ref,
                "odoo_role_ref": odoo_role_ref,
                "odoo_function_scope_ref": odoo_function_scope_ref,
                "odoo_function_item_set_ref": odoo_function_item_set_ref,
                "odoo_function_item_refs_csv": ",".join(odoo_function_items),
                "odoo_permission_bucket_ref": odoo_permission_bucket_ref,
                "odoo_connector_mode": "ref_only_no_db",
                "odoo_write_authority": False,
                "odoo_member_plaintext_read": False,
                "payment_tool_ref": payment_tool_ref,
                "management_fee_bill_ref": management_fee_bill_ref,
                "payment_amount_bucket_ref": payment_amount_bucket_ref,
                "payment_intent_ref": payment_intent_ref,
                "payment_capture_authority": False,
                "payment_data_transferred": False,
                "generative_transmission_ref": generative_transmission_ref,
                "return_packet_schema": "w7tp.cloud_candidate_return_packet.v1",
                "cloud_candidate_only": True,
                "boundary_hits_ref": ref("risk_ref", ",".join(boundary_hits) or "none"),
                "candidate_only": True,
                "requires_total_field_verify": True,
            },
            "dry_run": True,
            "submit_forbidden": True,
        },
    }
    packet_for_hash = json.loads(canonical_json(packet))
    packet_for_hash["D8_envelope"]["content_hash"] = ""
    packet["D8_envelope"]["content_hash"] = sha256_hex(canonical_json(packet_for_hash))
    return packet


def main() -> int:
    parser = argparse.ArgumentParser(description="Build XiaoJ member browser 1B dry-run 8D action packet.")
    parser.add_argument("--intent", required=True, help="Member request text. It is hashed/ref-coded into the packet, not stored as raw action authority.")
    parser.add_argument("--safe-context-ref", default="", help="Optional redacted context ref, not raw page text.")
    parser.add_argument("--member-ref", default="actor_ref:member_browser_1b:demo_member")
    parser.add_argument("--device-ref", default="device_ref:member_browser_1b:demo_device")
    parser.add_argument("--role-ref", default="member_role_ref")
    parser.add_argument("--site-ref", default="site_ref:member_browser_1b:demo_site")
    parser.add_argument("--key-ref", default="key_ref:member_browser_1b:broker_managed_default")
    parser.add_argument("--api-ref", default="api_ref:member_browser_1b:local_1b_controller")
    parser.add_argument("--quota-ref", default="quota_ref:member_browser_1b:free_member")
    parser.add_argument("--cost-policy", choices=["blocked", "metered", "budget_cap_ref", "human_approved"], default="budget_cap_ref")
    parser.add_argument("--model-tier", choices=["none", "small", "standard", "high_reasoning", "local_only"], default="small")
    parser.add_argument("--member-preference-ref", default="preference_ref:member_browser_1b:member_tendency_default")
    parser.add_argument("--service-style-ref", default="service_style_ref:community_xiaoj_warm_daily")
    parser.add_argument("--behavior-info-ref", default="")
    parser.add_argument("--cloud-compute-ref", default="cloud_compute_ref:local_1b_first_cloud_candidate_if_needed")
    parser.add_argument("--benefit-ref", default="benefit_ref:member_browser_1b:community_ai_benefit")
    parser.add_argument("--generative-transmission-ref", default="gt_ref:w7tp_member_browser_1b_no_plaintext")
    parser.add_argument("--odoo-identity-ref", default="odoo_identity_ref:member_browser_1b:demo_identity")
    parser.add_argument("--odoo-role-ref", default="odoo_role_ref:resident")
    parser.add_argument("--odoo-function-scope-ref", default="")
    parser.add_argument("--odoo-permission-bucket-ref", default="")
    parser.add_argument("--payment-tool-ref", default="payment_tool_ref:member_selected_external_tool")
    parser.add_argument("--management-fee-bill-ref", default="management_fee_bill_ref:none")
    parser.add_argument("--payment-amount-bucket-ref", default="payment_amount_bucket_ref:not_requested")
    parser.add_argument("--target-ref", default="")
    parser.add_argument("--ttl", type=int, default=300)
    parser.add_argument("--counter", type=int, default=1)
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    packet = build_packet(args)
    text = json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
