#!/usr/bin/env python3
"""Offline simulator for the XiaoJ member browser extension bridge.

The simulator mirrors the MV3 bridge policy in Python so release checks can
prove the browser action boundary without launching Chrome. It never reads
cookies, browser storage, secrets, member plaintext stores, Odoo, POS, or any
external service.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BRIDGE_SCHEMA = ROOT / "schemas/browser/xiaoj_browser_bridge_return_packet_v1.schema.json"

ALLOWED_ACTIONS = {"open_sidebar_ref", "read_text_ref", "write_draft_ref"}
BLOCKED_ACTIONS = {
    "click_ref",
    "fill_ref",
    "select_ref",
    "screenshot_ref",
    "extract_ref",
    "create_order_draft_ref",
    "submit_payment",
    "submit_order_without_human",
    "login_with_plaintext",
    "read_raw_cookie",
    "read_raw_local_storage",
    "write_database",
    "payment_capture",
    "service_restart",
    "deploy",
}
SENSITIVE_DRAFT = re.compile(
    r"(sk-[A-Za-z0-9_-]{10,}|api[_-]?key|password|secret|09\d{2}[- ]?\d{3}[- ]?\d{3})",
    re.I,
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def h(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def ref(prefix: str, value: Any) -> str:
    return f"{prefix}:{h(value)[:16]}"


def allowed(**detail: Any) -> dict[str, Any]:
    return {
        "ok": True,
        "decision": "ALLOW_LOCAL_MINIMUM_PRIVILEGE",
        "execution_allowed": False,
        "candidate_only": True,
        "requires_total_field_verify": True,
        "member_plaintext_transferred": False,
        "secret_transferred": False,
        **detail,
    }


def blocked(reason: str, **detail: Any) -> dict[str, Any]:
    return {
        "ok": False,
        "decision": "BLOCK",
        "reason": reason,
        "execution_allowed": False,
        "candidate_only": True,
        "requires_total_field_verify": True,
        "member_plaintext_transferred": False,
        "secret_transferred": False,
        **detail,
    }


def validate_packet(packet: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(packet, dict):
        return blocked("packet_not_object")
    if packet.get("packet_type") != "xiaoj_8d_action_packet":
        return blocked("packet_type_not_supported")
    action = packet.get("browser_action") or {}
    params = action.get("params") or {}
    if action.get("dry_run") is not True:
        return blocked("dry_run_required")
    if action.get("submit_forbidden") is not True:
        return blocked("submit_forbidden_required")
    if params.get("candidate_only") is not True:
        return blocked("candidate_only_required")
    if params.get("requires_total_field_verify") is not True:
        return blocked("total_field_verify_required")
    governance = packet.get("D6_governance") or {}
    if governance.get("no_plaintext_context") is not True:
        return blocked("no_plaintext_context_required")
    action_type = action.get("action_type")
    if action_type in BLOCKED_ACTIONS:
        return blocked("action_blocked_by_extension_policy", action_type=action_type)
    if action_type not in ALLOWED_ACTIONS:
        return blocked("action_not_allowed_by_extension_policy", action_type=action_type)
    return allowed(action_type=action_type)


def build_bridge_return_packet(packet: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    action = packet.get("browser_action") or {}
    params = action.get("params") or {}
    payload = {
        "schema_version": "xiaoj.browser_bridge_return_packet.v1",
        "packet_type": "BROWSER_BRIDGE_RETURN_PACKET",
        "candidate_only": True,
        "must_not_execute": True,
        "requires_total_field_verify": True,
        "member_plaintext_transferred": False,
        "secret_transferred": False,
        "raw_browser_page_transferred": False,
        "raw_text_returned": False,
        "D1_identity": {
            "actor_ref": (packet.get("D1_identity") or {}).get("actor_ref", "actor_ref:unknown"),
            "device_ref": "device_ref:member_browser_extension:offline_simulator",
            "plaintext_identity_forbidden": True,
        },
        "D2_intent": {
            "intent_ref": params.get("intent_ref", "intent_ref:missing"),
            "action_type_candidate": action.get("action_type", "unknown"),
            "bridge_decision": result.get("decision", "UNKNOWN"),
        },
        "D3_state": {
            "browser_result_ref": result.get("browser_result_ref") or ref("browser_result_ref", result.get("reason", "none")),
            "execution_allowed": False,
            "dry_run": True,
            "submit_forbidden": True,
        },
        "D4_evidence": {
            "behavior_info_ref": params.get("behavior_info_ref", "behavior_ref:missing"),
            "action_trace_ref": ref("action_trace_ref", f"{action.get('action_type', 'unknown')}:{result.get('decision', 'UNKNOWN')}"),
            "selected_text_ref": (result.get("result") or {}).get("selected_text_ref", "selected_text_ref:none"),
            "draft_ref": params.get("draft_ref", "draft_ref:none"),
        },
        "D5_execution": {
            "execution_allowed": False,
            "allowed_next_actions": ["present_candidate", "route_to_total_field_verifier", "ask_member_confirm"],
            "forbidden_actions": sorted(BLOCKED_ACTIONS),
            "human_confirm_required": bool(params.get("human_confirmed") is not True and action.get("action_type") == "write_draft_ref"),
        },
        "D6_generative_transmission": {
            "return_mode": "browser_bridge_packetized_candidate_result",
            "cloud_compute_ref": params.get("cloud_compute_ref", "cloud_compute_ref:missing"),
            "reconstruction_hint_ref": ref("reconstruct_ref", result),
            "cloud_candidate_only": True,
            "member_plaintext_transferred": False,
            "secret_transferred": False,
        },
        "D7_risk": {
            "bridge_ok": bool(result.get("ok")),
            "decision": result.get("decision", "UNKNOWN"),
            "reason_ref": ref("reason_ref", result.get("reason", "none")),
        },
        "D8_envelope": {
            "ttl_seconds": 300,
            "nonce": ref("nonce_ref", now_iso()),
            "created_at": now_iso(),
            "return_packet_hash": "",
            "total_field_verifier_required": True,
            "replay_protection": True,
        },
    }
    payload["D8_envelope"]["return_packet_hash"] = ref("return_packet_hash", payload)
    return payload


def attach_return(packet: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    return {**result, "browser_bridge_return_packet": build_bridge_return_packet(packet, result)}


def simulate(packet: dict[str, Any], selected_text: str = "", local_draft_text: str = "", active_field_type: str = "textarea") -> dict[str, Any]:
    gate = validate_packet(packet)
    if not gate["ok"]:
        return attach_return(packet, gate)
    action_type = packet["browser_action"]["action_type"]
    if action_type == "open_sidebar_ref":
        return attach_return(packet, allowed(action_type=action_type, side_panel_opened=True))
    if action_type == "read_text_ref":
        result = {
            "selected_text_ref": ref("selected_text_ref", selected_text),
            "selected_text_length": len(selected_text),
            "page_title_ref": ref("page_title_ref", "offline simulator page"),
            "raw_text_returned": False,
        }
        return attach_return(packet, allowed(action_type=action_type, browser_result_ref=ref("browser_result_ref", result), result=result))
    if action_type == "write_draft_ref":
        params = packet.get("browser_action", {}).get("params", {})
        if params.get("human_confirmed") is not True:
            return attach_return(packet, blocked("human_confirm_required_before_write_draft"))
        if not local_draft_text or len(local_draft_text) > 500:
            return attach_return(packet, blocked("draft_preview_missing_or_too_long"))
        if SENSITIVE_DRAFT.search(local_draft_text):
            return attach_return(packet, blocked("draft_preview_sensitive_pattern"))
        if active_field_type in {"password", "email", "tel", "number", "payment", "address"}:
            return attach_return(packet, blocked("sensitive_input_type_blocked"))
        result = {"filled": True, "reason": "draft_written_to_editable_field", "raw_draft_returned": False}
        return attach_return(packet, allowed(action_type=action_type, browser_result_ref=ref("browser_result_ref", result), result=result))
    return attach_return(packet, blocked("unreachable_action_policy"))


def validate_bridge_return(packet: dict[str, Any]) -> None:
    from jsonschema import validate

    schema = json.loads(BRIDGE_SCHEMA.read_text(encoding="utf-8"))
    validate(packet, schema)


def demo_packet(action_type: str, human_confirmed: bool = False) -> dict[str, Any]:
    packet = {
        "packet_type": "xiaoj_8d_action_packet",
        "D1_identity": {
            "actor_ref": "actor_ref:member_browser_extension:offline_member",
            "actor_type": "member",
            "device_ref": "device_ref:member_browser_extension:offline_simulator",
            "role": "member_role_ref",
            "plaintext_identity_forbidden": True,
        },
        "D2_intent": {
            "primary_intent": "intent_ref:offline_demo",
            "secondary_intent": "redacted_ref:offline_demo",
            "transaction_intent": "browse",
            "risk_level": "low" if action_type in ALLOWED_ACTIONS else "blocked",
        },
        "D3_state": {
            "session_state": "active",
            "task_state": "dry_run" if action_type in ALLOWED_ACTIONS else "blocked",
            "browser_state": "dry_run" if action_type in ALLOWED_ACTIONS else "blocked",
            "order_state": "none",
            "context_mode": "ref_only",
        },
        "D4_topology": {
            "channel": "browser_action_bus",
            "site_ref": "site_ref:xiaoj_member_browser_extension_offline",
            "device_topology": "member_browser_extension_to_total_field",
            "origin_scope": "member_owned",
        },
        "D5_resource": {
            "key_policy": "hybrid_ref_only",
            "selected_key_ref": "key_ref:member_browser_extension:offline",
            "api_refs": ["api_ref:member_browser_extension:offline_bridge"],
            "model_tier": "small",
            "cache_policy": "ref_cache_only",
            "cost_policy": "budget_cap_ref",
        },
        "D6_governance": {
            "allowed_actions": sorted(ALLOWED_ACTIONS),
            "forbidden_actions": sorted(BLOCKED_ACTIONS),
            "no_plaintext_context": True,
            "human_confirm_required": action_type == "write_draft_ref",
            "staff_confirm_required": False,
        },
        "D7_verification": {
            "redaction_check_required": True,
            "leak_check_required": True,
            "action_allowlist_required": True,
            "response_verify_required": True,
            "usage_log_required": True,
        },
        "D8_envelope": {
            "packet_ref": "packet_ref:offline_demo",
            "nonce": "nonce_ref:offline_demo",
            "counter": 1,
            "ttl_seconds": 300,
            "created_at": now_iso(),
            "schema_version": "8d.packet.v1",
            "content_hash": h(action_type),
            "hmac_ref": "hmac_ref:xiaoj_member_browser_extension:verifier_required",
            "signature_ref": "signature_ref:xiaoj_member_browser_extension:verifier_required",
            "replay_protection": True,
        },
        "browser_action": {
            "action_ref": ref("action_ref", action_type),
            "action_type": action_type,
            "target_ref": ref("target_ref", action_type),
            "params": {
                "controller_ref": "controller_ref:xiaoj_member_browser_1b",
                "intent_ref": "intent_ref:offline_demo",
                "safe_context_ref": "redacted_ref:offline_demo",
                "member_preference_ref": "preference_ref:member:offline",
                "service_style_ref": "service_style_ref:community_xiaoj_warm_daily",
                "behavior_info_ref": ref("behavior_ref", action_type),
                "cloud_compute_ref": "cloud_compute_ref:local_1b_first_extension_bridge",
                "benefit_ref": "benefit_ref:community_ai_member_daily",
                "quota_bucket_ref": "quota_bucket_ref:member_daily_fair_use",
                "generative_transmission_ref": "gt_ref:w7tp_member_browser_extension_no_plaintext",
                "return_packet_schema": "w7tp.cloud_candidate_return_packet.v1",
                "cloud_candidate_only": True,
                "human_confirmed": human_confirmed,
                "draft_ref": ref("draft_ref", "offline_demo"),
                "boundary_hits_ref": "risk_ref:none",
                "candidate_only": True,
                "requires_total_field_verify": True,
            },
            "dry_run": True,
            "submit_forbidden": True,
        },
    }
    return packet


def run_smoke() -> int:
    cases = [
        ("open_sidebar", demo_packet("open_sidebar_ref"), {}, True, "ALLOW_LOCAL_MINIMUM_PRIVILEGE"),
        ("read_selected_text", demo_packet("read_text_ref"), {"selected_text": "公告摘要測試"}, True, "ALLOW_LOCAL_MINIMUM_PRIVILEGE"),
        ("write_draft_unconfirmed", demo_packet("write_draft_ref", human_confirmed=False), {"local_draft_text": "安全草稿"}, False, "BLOCK"),
        ("write_draft_confirmed", demo_packet("write_draft_ref", human_confirmed=True), {"local_draft_text": "安全草稿"}, True, "ALLOW_LOCAL_MINIMUM_PRIVILEGE"),
        ("write_draft_sensitive", demo_packet("write_draft_ref", human_confirmed=True), {"local_draft_text": "password: demo"}, False, "BLOCK"),
        ("write_draft_sensitive_field", demo_packet("write_draft_ref", human_confirmed=True), {"local_draft_text": "安全草稿", "active_field_type": "password"}, False, "BLOCK"),
        ("submit_payment_blocked", demo_packet("submit_payment"), {}, False, "BLOCK"),
        ("cookie_read_blocked", demo_packet("read_raw_cookie"), {}, False, "BLOCK"),
    ]
    failures: list[str] = []
    results: list[dict[str, Any]] = []
    for name, packet, kwargs, expected_ok, expected_decision in cases:
        result = simulate(packet, **kwargs)
        bridge_packet = result["browser_bridge_return_packet"]
        validate_bridge_return(bridge_packet)
        ok = result["ok"] is expected_ok and result["decision"] == expected_decision
        if bridge_packet["member_plaintext_transferred"] is not False or bridge_packet["secret_transferred"] is not False:
            ok = False
        if bridge_packet["D3_state"]["execution_allowed"] is not False:
            ok = False
        results.append({"name": name, "ok": ok, "decision": result["decision"], "bridge_schema": "PASS"})
        print(f"CASE_{name}={'PASS' if ok else 'FAIL'} DECISION={result['decision']}")
        if not ok:
            failures.append(name)
    print("SECRET_READ=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")
    print("RAW_AUDIO_SAVED=FALSE")
    print("DB_WRITE=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    print("SERVICE_RESTART=FALSE")
    print("DEPLOY=FALSE")
    print("STATE=" + ("PASS_XIAOJ_BROWSER_BRIDGE_SIMULATOR" if not failures else "FAIL_XIAOJ_BROWSER_BRIDGE_SIMULATOR"))
    return 0 if not failures else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline simulate XiaoJ browser bridge policy.")
    parser.add_argument("--packet", help="Path to xiaoj_8d_action_packet JSON.")
    parser.add_argument("--selected-text", default="")
    parser.add_argument("--local-draft-text", default="")
    parser.add_argument("--active-field-type", default="textarea")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    if args.smoke:
        return run_smoke()
    if not args.packet:
        parser.error("use --packet or --smoke")
    packet = json.loads(Path(args.packet).read_text(encoding="utf-8"))
    result = simulate(packet, selected_text=args.selected_text, local_draft_text=args.local_draft_text, active_field_type=args.active_field_type)
    validate_bridge_return(result["browser_bridge_return_packet"])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["browser_bridge_return_packet"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
