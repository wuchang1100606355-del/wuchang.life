#!/usr/bin/env python3
"""Chrome/Edge native messaging host for XiaoJ member browser gateway.

This host speaks the native messaging length-prefixed JSON protocol. It routes
member-owned browser requests into the local XiaoJ gateway and returns
candidate-only, no-plaintext 8D packets.

It does not call cloud services, does not read secrets, does not read member
plaintext stores, does not touch Odoo/POS/production DB, and does not start any
service.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.member_browser.xiaoj_member_browser_gateway import forward_transport_envelope
from tools.tfct_true8d_runtime_candidate import RuntimeCandidateError
from tools.total_field_candidate_gateway import TotalFieldGatewayError


BROWSER_REPLAY_LEDGER: set[str] = set()


def read_message() -> dict | None:
    header = sys.stdin.buffer.read(4)
    if not header:
        return None
    if len(header) != 4:
        raise ValueError("native_header_incomplete")
    length = struct.unpack("<I", header)[0]
    if length <= 0 or length > 1024 * 1024:
        raise ValueError("native_message_length_invalid")
    raw = sys.stdin.buffer.read(length)
    if len(raw) != length:
        raise ValueError("native_message_body_incomplete")
    return json.loads(raw.decode("utf-8"))


def write_message(message: dict) -> None:
    raw = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(raw)))
    sys.stdout.buffer.write(raw)
    sys.stdout.buffer.flush()


def build_args(payload: dict) -> argparse.Namespace:
    return argparse.Namespace(
        intent=str(payload.get("intent") or "會員日常協力"),
        safe_context_ref=str(payload.get("safe_context_ref") or "redacted_ref:native_host_default"),
        selected_text=str(payload.get("selected_text") or ""),
        local_draft_text=str(payload.get("local_draft_text") or ""),
        active_field_type=str(payload.get("active_field_type") or "textarea"),
        member_ref=str(payload.get("member_ref") or "actor_ref:member_browser_native_host:demo_member"),
        device_ref=str(payload.get("device_ref") or "device_ref:member_browser_native_host:chrome_mv3"),
        key_ref=str(payload.get("key_ref") or "key_ref:member_browser_native_host:broker_default"),
        api_ref=str(payload.get("api_ref") or "api_ref:member_browser_native_host:local_1b"),
        quota_ref=str(payload.get("quota_ref") or "quota_ref:member_browser_native_host:daily"),
        member_preference_ref=str(payload.get("member_preference_ref") or "preference_ref:member:sidepanel_default"),
        service_style_ref=str(payload.get("service_style_ref") or "service_style_ref:community_xiaoj_warm_daily"),
        behavior_info_ref=str(payload.get("behavior_info_ref") or ""),
        cloud_compute_ref=str(payload.get("cloud_compute_ref") or "cloud_compute_ref:native_host_local_gateway"),
        benefit_ref=str(payload.get("benefit_ref") or "benefit_ref:community_ai_member_daily"),
        odoo_identity_ref=str(payload.get("odoo_identity_ref") or "odoo_identity_ref:native_host_demo_member"),
        odoo_role_ref=str(payload.get("odoo_role_ref") or "odoo_role_ref:resident"),
        odoo_function_scope_ref=str(payload.get("odoo_function_scope_ref") or "odoo_function_scope_ref:member_daily"),
        odoo_permission_bucket_ref=str(payload.get("odoo_permission_bucket_ref") or "odoo_permission_bucket_ref:resident_readonly"),
        payment_tool_ref=str(payload.get("payment_tool_ref") or "payment_tool_ref:member_selected_external_tool"),
        management_fee_bill_ref=str(payload.get("management_fee_bill_ref") or "management_fee_bill_ref:none"),
        payment_amount_bucket_ref=str(payload.get("payment_amount_bucket_ref") or "payment_amount_bucket_ref:not_requested"),
        out="",
    )


def handle(payload: dict) -> dict:
    if payload.get("type") != "XIAOJ_NATIVE_GATEWAY_REQUEST":
        return {
            "ok": False,
            "decision": "BLOCK",
            "reason": "unsupported_native_message_type",
            "candidate_only": True,
            "requires_total_field_verify": True,
            "member_plaintext_transferred": False,
            "secret_transferred": False,
        }
    transport_envelope = payload.get("transport_envelope")
    if not isinstance(transport_envelope, dict):
        return {
            "ok": False,
            "decision": "HOLD",
            "reason": "browser_transport_envelope_required",
            "candidate_only": True,
            "authority_granted": False,
            "requires_total_field_verify": True,
            "member_plaintext_transferred": False,
            "secret_transferred": False,
        }
    try:
        result = forward_transport_envelope(
            transport_envelope,
            replay_ledger=BROWSER_REPLAY_LEDGER,
        )
    except TotalFieldGatewayError as exc:
        return {
            "ok": False,
            "decision": "HOLD",
            "reason": exc.reason_code,
            "path": exc.path,
            "candidate_only": True,
            "authority_granted": False,
            "requires_total_field_verify": True,
            "member_plaintext_transferred": False,
            "secret_transferred": False,
        }
    except (OSError, RuntimeCandidateError):
        return {
            "ok": False,
            "decision": "HOLD",
            "reason": "total_field_receiver_unavailable",
            "candidate_only": True,
            "authority_granted": False,
            "requires_total_field_verify": True,
            "member_plaintext_transferred": False,
            "secret_transferred": False,
        }
    receipt = result["total_field_receipt"]
    return {
        "ok": result["state"] == "ALLOW",
        "decision": result["state"],
        "candidate_only": True,
        "authority_granted": False,
        "requires_total_field_verify": True,
        "member_plaintext_transferred": False,
        "secret_transferred": False,
        "packet_id": result["packet_id"],
        "trace_id": result["trace_id"],
        "content_sha256": result["content_sha256"],
        "total_field_receipt": receipt,
        "gateway_result": result,
    }


def run_loop() -> int:
    while True:
        payload = read_message()
        if payload is None:
            return 0
        try:
            write_message(handle(payload))
        except Exception as exc:
            write_message({
                "ok": False,
                "decision": "BLOCK",
                "reason": "native_host_exception",
                "error_ref": "error_ref:" + str(abs(hash(str(exc))))[:16],
                "candidate_only": True,
                "requires_total_field_verify": True,
                "member_plaintext_transferred": False,
                "secret_transferred": False,
            })


def run_once(payload: dict) -> dict:
    return handle(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="XiaoJ member browser native messaging host.")
    parser.add_argument("--once-json", help="Run once with a JSON payload string for verification.")
    args = parser.parse_args()
    if args.once_json:
        print(json.dumps(run_once(json.loads(args.once_json)), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    return run_loop()


if __name__ == "__main__":
    raise SystemExit(main())
