#!/usr/bin/env python3
"""Verify LINE Official Account total-field authorization guide and contract."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "packets/product_av_ordering_ai/line_official_account_total_field_authorization_contract.json"
REFS_TEMPLATE = ROOT / "packets/product_av_ordering_ai/line_official_account_refs_template.json"
GUIDE = ROOT / "docs/product/XIAOJ_LINE_OFFICIAL_ACCOUNT_TOTAL_FIELD_AUTHORIZATION_GUIDE.md"
SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/line_official_account_config.py"
REFS_SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/line_official_account_refs.py"
WEBHOOK_SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/line_official_account_webhook.py"
TOOL = ROOT / "tools/xiaoj_line_official_account_config_candidate.py"
REFS_TOOL = ROOT / "tools/xiaoj_line_official_account_refs_builder.py"
WEBHOOK_TOOL = ROOT / "tools/xiaoj_line_official_account_webhook_candidate.py"
CTRL = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/controllers/main.py"
MODEL = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/models/line_official_account_config.py"
MODEL_INIT = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/models/__init__.py"
VIEW = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/views/line_official_account_config_views.xml"
MANIFEST = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/__manifest__.py"
ACCESS = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/security/ir.model.access.csv"


def fail(message: str) -> None:
    print(f"VERIFY_FAIL={message}")
    print("STATE=HOLD_XIAOJ_LINE_OFFICIAL_ACCOUNT_AUTHORIZATION")
    raise SystemExit(1)


def read(path: Path) -> str:
    if not path.exists():
        fail(f"missing:{path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def require(path: Path, needles: list[str]) -> str:
    text = read(path)
    for needle in needles:
        if needle not in text:
            fail(f"missing_text:{path.relative_to(ROOT)}:{needle}")
    return text


def assert_no_secret_shape(text: str, label: str) -> None:
    patterns = [
        r"sk-[A-Za-z0-9_-]{12,}",
        r"(?i)(access|refresh|id)_token\s*[:=]\s*\S+",
        r"(?i)client_secret\s*[:=]\s*\S+",
        r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}",
        r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----",
        r"[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}",
    ]
    for pattern in patterns:
        if re.search(pattern, text):
            fail(f"secret_shape_detected:{label}:{pattern}")


def main() -> int:
    contract_text = read(CONTRACT)
    guide_text = read(GUIDE)
    assert_no_secret_shape(contract_text, "contract")
    assert_no_secret_shape(guide_text, "guide")
    contract = json.loads(contract_text)
    if contract.get("state") != "P1_AUTHORIZATION_MODEL_READY_FOR_HUMAN_REVIEW":
        fail("contract_state_wrong")
    if contract.get("config_candidate_api") != "/wuchang/xiaoj/api/line-official-account-config-candidate":
        fail("config_candidate_api_wrong")
    if contract.get("config_candidate_api_auth") != "user":
        fail("config_candidate_api_auth_wrong")
    if contract.get("webhook_candidate_api") != "/wuchang/xiaoj/api/line-official-account-webhook-candidate":
        fail("webhook_candidate_api_wrong")
    if contract.get("webhook_shell_route") != "/wuchang/xiaoj/line-official-account/webhook":
        fail("webhook_shell_route_wrong")
    if contract.get("webhook_shell_auth") != "public":
        fail("webhook_shell_auth_wrong")
    if contract.get("refs_template") != "packets/product_av_ordering_ai/line_official_account_refs_template.json":
        fail("refs_template_wrong")
    refs_builder = contract.get("refs_builder", {})
    if refs_builder.get("tool") != "tools/xiaoj_line_official_account_refs_builder.py":
        fail("refs_builder_tool_wrong")
    if refs_builder.get("service") != "wuchang_cafe_ai_gateway.services.line_official_account_refs.build_line_official_account_refs_draft":
        fail("refs_builder_service_wrong")
    if refs_builder.get("odoo_action") != "action_build_refs_draft":
        fail("refs_builder_odoo_action_wrong")
    for key in ["accepts_secret_values", "accepts_member_plaintext", "external_api_call", "official_account_setting_changed", "db_write"]:
        if refs_builder.get(key) is not False:
            fail(f"refs_builder_boundary_not_false:{key}")
    boundary = contract.get("official_account_boundary", {})
    for key in [
        "line_official_account_is_not_lineworks",
        "messaging_api_channel_required",
        "webhook_required_for_inbound_events",
        "human_owner_admin_root_of_trust",
    ]:
        if boundary.get(key) is not True:
            fail(f"boundary_not_true:{key}")
    for key in [
        "total_field_super_admin",
        "total_field_can_accept_admin_invite",
        "total_field_can_hold_plaintext_channel_access_token",
        "total_field_can_change_production_settings_without_release_packet",
    ]:
        if boundary.get(key) is not False:
            fail(f"boundary_not_false:{key}")
    intent_packet = contract.get("natural_language_intent_packet", {})
    if intent_packet.get("tool") != "tools/xiaoj_line_official_account_config_candidate.py":
        fail("intent_packet_tool_missing")
    if intent_packet.get("service") != "wuchang_cafe_ai_gateway.services.line_official_account_config.build_line_official_account_config_candidate":
        fail("intent_packet_service_missing")
    if intent_packet.get("api") != "/wuchang/xiaoj/api/line-official-account-config-candidate":
        fail("intent_packet_api_missing")
    if intent_packet.get("execution_allowed_from_llm") is not False:
        fail("llm_execution_not_false")
    webhook_packet = contract.get("webhook_candidate_packet", {})
    if webhook_packet.get("tool") != "tools/xiaoj_line_official_account_webhook_candidate.py":
        fail("webhook_packet_tool_wrong")
    if webhook_packet.get("service") != "wuchang_cafe_ai_gateway.services.line_official_account_webhook.build_line_official_account_webhook_candidate":
        fail("webhook_packet_service_wrong")
    for key in ["signature_secret_read", "line_reply_sent", "reply_token_echo", "raw_user_id_echo"]:
        if webhook_packet.get(key) is not False:
            fail(f"webhook_packet_boundary_not_false:{key}")
    if webhook_packet.get("requires_signature_verification_ref_for_ready") is not True:
        fail("webhook_signature_ref_requirement_missing")
    for key, value in contract.get("p1_side_effects", {}).items():
        if value is not False:
            fail(f"side_effect_not_false:{key}")
    require(GUIDE, [
        "STATE=P1_AUTHORIZATION_MODEL_READY_FOR_HUMAN_REVIEW",
        "LINE 官方帳號不應把「總場」加入成無限制管理員。",
        "Human owner/admin keeps LINE Official Account authority",
        "Messaging API",
        "channel access token 與 channel secret 放入 vault 或 runtime resolver",
        "CONFIG_CANDIDATE",
        "HOLD_NEEDS_HUMAN_APPROVAL",
        "READY_FOR_HUMAN_APPROVAL",
        "line-official-account-config-candidate",
        "line-official-account-webhook-candidate",
        "/wuchang/xiaoj/line-official-account/webhook",
        "no LINE reply",
        "no replyToken echo",
        "xiaoj_line_official_account_config_candidate.py",
        "xiaoj_line_official_account_webhook_candidate.py",
        "xiaoj_line_official_account_refs_builder.py",
        "HOLD_LINE_OFFICIAL_ACCOUNT_REFS_DRAFT",
        "LINE_OFFICIAL_ACCOUNT_REFS_READY_FOR_CONFIG_CANDIDATE",
        "click Build Refs Draft",
        "LLM 或 Gemini 只能產生候選設定文字",
        "Runtime resolver reads secrets only in memory after release.",
    ])
    refs_template = json.loads(read(REFS_TEMPLATE))
    if refs_template.get("state") != "TEMPLATE_REQUIRES_HUMAN_FILLED_REFS":
        fail("refs_template_state_wrong")
    if refs_template.get("p1_side_effects", {}).get("official_account_setting_changed") is not False:
        fail("refs_template_setting_changed_not_false")
    for key in contract.get("minimum_refs", {}):
        if key not in refs_template.get("refs", {}):
            fail(f"refs_template_missing:{key}")
    service_text = require(SERVICE, [
        "build_line_official_account_config_candidate",
        "W7TP_XIAOJ_LINE_OFFICIAL_ACCOUNT_CONFIG_CANDIDATE_V1",
        "READY_FOR_HUMAN_APPROVAL",
        "HOLD_NEEDS_HUMAN_APPROVAL",
        "official_account_setting_changed",
        "line_official_account_is_not_lineworks",
        "llm_execution_allowed",
    ])
    assert_no_secret_shape(service_text, "service")
    tool_text = require(TOOL, [
        "build_line_official_account_config_candidate",
        "W7TP_XIAOJ_LINE_OFFICIAL_ACCOUNT_CONFIG_CANDIDATE_REPORT_V1",
    ])
    assert_no_secret_shape(tool_text, "tool")
    refs_service_text = require(REFS_SERVICE, [
        "build_line_official_account_refs_draft",
        "W7TP_XIAOJ_LINE_OFFICIAL_ACCOUNT_REFS_DRAFT_V1",
        "HOLD_LINE_OFFICIAL_ACCOUNT_REFS_DRAFT",
        "LINE_OFFICIAL_ACCOUNT_REFS_READY_FOR_CONFIG_CANDIDATE",
    ])
    assert_no_secret_shape(refs_service_text, "refs_service")
    refs_tool_text = require(REFS_TOOL, [
        "build_line_official_account_refs_draft",
        "W7TP_XIAOJ_LINE_OFFICIAL_ACCOUNT_REFS_BUILDER_REPORT_V1",
    ])
    assert_no_secret_shape(refs_tool_text, "refs_tool")
    webhook_service_text = require(WEBHOOK_SERVICE, [
        "build_line_official_account_webhook_candidate",
        "W7TP_XIAOJ_LINE_OFFICIAL_ACCOUNT_WEBHOOK_CANDIDATE_V1",
        "READY_FOR_LOCAL_INTENT_CANDIDATE",
        "HOLD_LINE_OFFICIAL_ACCOUNT_WEBHOOK_CANDIDATE",
        "reply_token_echo",
        "raw_user_id_echo",
        "line_reply_sent",
    ])
    assert_no_secret_shape(webhook_service_text, "webhook_service")
    webhook_tool_text = require(WEBHOOK_TOOL, [
        "build_line_official_account_webhook_candidate",
        "W7TP_XIAOJ_LINE_OFFICIAL_ACCOUNT_WEBHOOK_CANDIDATE_REPORT_V1",
    ])
    assert_no_secret_shape(webhook_tool_text, "webhook_tool")
    require(CTRL, [
        '"/wuchang/xiaoj/api/line-official-account-config-candidate", type="json", auth="user"',
        '"/wuchang/xiaoj/api/line-official-account-webhook-candidate", type="json", auth="user"',
        '"/wuchang/xiaoj/line-official-account/webhook", type="json", auth="public"',
        "build_line_official_account_config_candidate",
        "build_line_official_account_webhook_candidate",
        "xiaoj_line_official_account_config_candidate",
        "xiaoj_line_official_account_webhook",
    ])
    model_text = require(MODEL, [
        '_name = "wuchang.line.official.account.config.candidate"',
        "action_build_refs_draft",
        "action_build_config_candidate",
        "action_dead_letter",
        "build_line_official_account_config_candidate",
        "build_line_official_account_refs_draft",
        "_assert_no_secret_material",
        "@api.constrains",
        "formal_line_message_send",
        "official_account_setting_changed",
        "secret_read",
        "member_plaintext_read",
    ])
    assert_no_secret_shape(model_text, "model")
    for forbidden in ["requests.post", "urlopen", "http.client", "official_account_setting_changed = True", "formal_line_message_send = True"]:
        if forbidden in model_text:
            fail(f"model_forbidden:{forbidden}")
    require(MODEL_INIT, ["line_official_account_config"])
    require(MANIFEST, ["views/line_official_account_config_views.xml"])
    require(ACCESS, [
        "model_wuchang_line_official_account_config_candidate",
        "base.group_user,1,1,1,0",
        "base.group_system,1,1,1,1",
    ])
    view_text = require(VIEW, [
        "LINE Official Account Config Candidate",
        "action_build_refs_draft",
        "Build Refs Draft",
        "action_build_config_candidate",
        "Build Config Candidate",
        "action_dead_letter",
        "LINE Official Account Refs",
        "Candidate Packet",
        "Side Effect Boundary",
        "menu_wuchang_line_official_account_config_candidate",
    ])
    assert_no_secret_shape(view_text, "view")
    if "正式生效" in view_text or "Apply Now" in view_text or "Send Now" in view_text:
        fail("view_has_formal_apply_button")

    intent = (
        "幫我把 LINE 官方帳號設定成咖啡館會員客服模式；"
        "新朋友加入先歡迎並詢問是否領用會員小J；"
        "促銷只發給已同意會員；付款、訂單、個資不得由 LLM 自行判定；"
        "設定完成後給我核定，不要直接生效。 ACCESS_TOKEN_REF_TEST test@example.com"
    )
    with tempfile.TemporaryDirectory() as tmp:
        refs_hold_out = Path(tmp) / "refs_hold.json"
        refs_hold = subprocess.run(
            [sys.executable, str(REFS_TOOL), "--input", str(REFS_TEMPLATE), "--out", str(refs_hold_out), "--pretty"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if refs_hold.returncode != 2:
            fail(f"refs_template_should_hold:{refs_hold.returncode}:{refs_hold.stdout}:{refs_hold.stderr}")
        refs_hold_report = json.loads(refs_hold.stdout)
        if refs_hold_report.get("state") != "HOLD_LINE_OFFICIAL_ACCOUNT_REFS_DRAFT":
            fail("refs_template_hold_state_wrong")

        hold_out = Path(tmp) / "hold.json"
        hold_proc = subprocess.run(
            [sys.executable, str(TOOL), "--intent", intent, "--out", str(hold_out), "--pretty"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if hold_proc.returncode != 2:
            fail(f"hold_cli_returncode_wrong:{hold_proc.returncode}:{hold_proc.stdout}:{hold_proc.stderr}")
        hold_report = json.loads(hold_proc.stdout)
        if hold_report.get("state") != "HOLD_NEEDS_HUMAN_APPROVAL":
            fail("hold_cli_state_wrong")
        hold_packet = json.loads(hold_out.read_text(encoding="utf-8"))
        serialized_hold = json.dumps(hold_packet, ensure_ascii=False)
        for forbidden in ["SHOULD_NOT_SURVIVE", "test@example.com"]:
            if forbidden in serialized_hold:
                fail(f"hold_packet_leaks_redacted_text:{forbidden}")
        if hold_packet.get("side_effects", {}).get("official_account_setting_changed") is not False:
            fail("hold_packet_setting_changed_not_false")

        refs = {
            "line_official_account_ref": "LINE_OFFICIAL_ACCOUNT_REF_CAFE",
            "line_provider_ref": "LINE_PROVIDER_REF_CAFE",
            "messaging_api_channel_ref": "MESSAGING_API_CHANNEL_REF_CAFE",
            "webhook_endpoint_ref": "WEBHOOK_ENDPOINT_REF_CAFE",
            "channel_secret_ref": "CHANNEL_SECRET_REF_VAULT_ONLY",
            "channel_access_token_runtime_ref": "CHANNEL_ACCESS_TOKEN_RUNTIME_REF_VAULT_ONLY",
            "message_policy_ref": "MESSAGE_POLICY_REF_CAFE",
            "audience_policy_ref": "AUDIENCE_POLICY_REF_CONSENTED_MEMBERS",
            "consent_policy_ref": "CONSENT_POLICY_REF_CAFE",
            "human_owner_admin_release_ref": "HUMAN_OWNER_ADMIN_RELEASE_REF_CAFE",
        }
        refs_path = Path(tmp) / "refs.json"
        refs_ready_out = Path(tmp) / "refs_ready.json"
        ready_out = Path(tmp) / "ready.json"
        refs_path.write_text(json.dumps(refs, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        refs_ready = subprocess.run(
            [sys.executable, str(REFS_TOOL), "--input", str(refs_path), "--out", str(refs_ready_out), "--pretty"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if refs_ready.returncode != 0:
            fail(f"refs_ready_should_pass:{refs_ready.returncode}:{refs_ready.stdout}:{refs_ready.stderr}")
        refs_ready_report = json.loads(refs_ready.stdout)
        if refs_ready_report.get("state") != "LINE_OFFICIAL_ACCOUNT_REFS_READY_FOR_CONFIG_CANDIDATE":
            fail("refs_ready_state_wrong")
        ready_proc = subprocess.run(
            [
                sys.executable,
                str(TOOL),
                "--intent",
                "幫我設定 LINE 官方帳號客服，新朋友加入歡迎並詢問會員小J，促銷只發給已同意會員，設定後給我核定不要直接生效。",
                "--refs",
                str(refs_path),
                "--out",
                str(ready_out),
                "--pretty",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if ready_proc.returncode != 0:
            fail(f"ready_cli_returncode_wrong:{ready_proc.returncode}:{ready_proc.stdout}:{ready_proc.stderr}")
        ready_report = json.loads(ready_proc.stdout)
        if ready_report.get("state") != "READY_FOR_HUMAN_APPROVAL":
            fail("ready_cli_state_wrong")
        ready_packet = json.loads(ready_out.read_text(encoding="utf-8"))
        if ready_packet.get("local_verifier", {}).get("llm_execution_allowed") is not False:
            fail("ready_packet_llm_execution_not_false")
        if ready_packet.get("authority_packet", {}).get("official_account_setting_changed") is not False:
            fail("ready_packet_setting_changed_not_false")

        webhook_payload = {
            "destination": "U_SHOULD_NOT_ECHO_DESTINATION",
            "events": [
                {
                    "type": "message",
                    "replyToken": "REPLY_TOKEN_SHOULD_NOT_ECHO",
                    "timestamp": 1710000000000,
                    "source": {
                        "type": "user",
                        "userId": "U_SHOULD_NOT_ECHO_USER_ID",
                    },
                    "message": {
                        "id": "MSG_REF_ONLY",
                        "type": "text",
                        "text": "我想加入會員，email test@example.com，手機 0912-345-678",
                    },
                }
            ],
        }
        headers = {"X-Line-Signature": "SIGNATURE_REF_PRESENT_NOT_REAL_VALUE"}
        verification = {
            "verified": True,
            "signature_verification_ref": "SIGNATURE_VERIFICATION_REF_TEST",
            "channel_secret_ref": "CHANNEL_SECRET_REF_VAULT_ONLY",
        }
        webhook_payload_path = Path(tmp) / "webhook_payload.json"
        webhook_headers_path = Path(tmp) / "webhook_headers.json"
        webhook_verification_path = Path(tmp) / "webhook_verification.json"
        webhook_hold_out = Path(tmp) / "webhook_hold.json"
        webhook_ready_out = Path(tmp) / "webhook_ready.json"
        webhook_payload_path.write_text(json.dumps(webhook_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        webhook_headers_path.write_text(json.dumps(headers, ensure_ascii=False, indent=2), encoding="utf-8")
        webhook_verification_path.write_text(json.dumps(verification, ensure_ascii=False, indent=2), encoding="utf-8")
        webhook_hold = subprocess.run(
            [
                sys.executable,
                str(WEBHOOK_TOOL),
                "--payload",
                str(webhook_payload_path),
                "--headers",
                str(webhook_headers_path),
                "--out",
                str(webhook_hold_out),
                "--pretty",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if webhook_hold.returncode != 2:
            fail(f"webhook_hold_should_hold:{webhook_hold.returncode}:{webhook_hold.stdout}:{webhook_hold.stderr}")
        webhook_hold_report = json.loads(webhook_hold.stdout)
        if webhook_hold_report.get("state") != "HOLD_LINE_OFFICIAL_ACCOUNT_WEBHOOK_CANDIDATE":
            fail("webhook_hold_state_wrong")
        webhook_ready = subprocess.run(
            [
                sys.executable,
                str(WEBHOOK_TOOL),
                "--payload",
                str(webhook_payload_path),
                "--headers",
                str(webhook_headers_path),
                "--verification",
                str(webhook_verification_path),
                "--out",
                str(webhook_ready_out),
                "--pretty",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if webhook_ready.returncode != 0:
            fail(f"webhook_ready_should_pass:{webhook_ready.returncode}:{webhook_ready.stdout}:{webhook_ready.stderr}")
        webhook_ready_report = json.loads(webhook_ready.stdout)
        if webhook_ready_report.get("state") != "READY_FOR_LOCAL_INTENT_CANDIDATE":
            fail("webhook_ready_state_wrong")
        webhook_ready_packet = json.loads(webhook_ready_out.read_text(encoding="utf-8"))
        serialized_webhook = json.dumps(webhook_ready_packet, ensure_ascii=False)
        for forbidden in [
            "U_SHOULD_NOT_ECHO_USER_ID",
            "REPLY_TOKEN_SHOULD_NOT_ECHO",
            "test@example.com",
            "0912-345-678",
        ]:
            if forbidden in serialized_webhook:
                fail(f"webhook_packet_leaks_raw_value:{forbidden}")
        if webhook_ready_packet.get("side_effects", {}).get("line_reply_sent") is not False:
            fail("webhook_ready_line_reply_sent_not_false")
    print("STATE=PASS_XIAOJ_LINE_OFFICIAL_ACCOUNT_AUTHORIZATION_MODEL")
    print("TOTAL_FIELD_SUPER_ADMIN=FALSE")
    print("HUMAN_OWNER_ADMIN_ROOT_OF_TRUST=TRUE")
    print("PLAINTEXT_TOKEN_IN_CONTRACT=FALSE")
    print("LLM_DIRECT_EXECUTION=FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
