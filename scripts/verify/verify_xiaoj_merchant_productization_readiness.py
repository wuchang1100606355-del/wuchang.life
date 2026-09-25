#!/usr/bin/env python3
"""Verify XiaoJ merchant productization readiness gate."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools/xiaoj_merchant_productization_readiness.py"
SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/merchant_productization_readiness.py"
CTRL = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/controllers/main.py"
TEMPLATE = ROOT / "packets/product_av_ordering_ai/xiaoj_merchant_productization_readiness_template.json"
LINEWORKS_TEMPLATE = ROOT / "packets/product_av_ordering_ai/lineworks_release_refs_template.json"
LINE_OFFICIAL_TEMPLATE = ROOT / "packets/product_av_ordering_ai/line_official_account_refs_template.json"
GUIDE = ROOT / "docs/product/XIAOJ_MERCHANT_PRODUCTIZATION_READINESS_GUIDE.md"


SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9_-]{12,}",
    r"(?i)(access|refresh|id)_token\s*[:=]\s*\S+",
    r"(?i)channel_secret\s*[:=]\s*\S+",
    r"(?i)client_secret\s*[:=]\s*\S+",
    r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}",
    r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}",
]


def fail(message: str) -> None:
    print(f"VERIFY_FAIL={message}")
    print("STATE=HOLD_XIAOJ_MERCHANT_PRODUCTIZATION_READINESS_VERIFIER")
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
    for pattern in SECRET_PATTERNS:
        if re.search(pattern, text):
            fail(f"secret_shape_detected:{label}:{pattern}")


def assert_side_effects_false(report: dict, label: str) -> None:
    side_effects = report.get("side_effects")
    if not isinstance(side_effects, dict):
        fail(f"missing_side_effects:{label}")
    for key, value in side_effects.items():
        if value is not False:
            fail(f"side_effect_not_false:{label}:{key}")


def ready_ref(prefix: str, key: str, hash_char: str = "c") -> dict:
    return {
        "ref": f"{prefix}_{key}_READY_REF".upper(),
        "packet_hash": hash_char * 64,
        "verifier": "total_field_release_registry",
        "verified": True,
    }


def build_ready_fixture(tmp: Path) -> Path:
    config = json.loads(read(TEMPLATE))
    lineworks = json.loads(read(LINEWORKS_TEMPLATE))
    line_official = json.loads(read(LINE_OFFICIAL_TEMPLATE))

    for gate_id, refs in config["formal_release_refs"].items():
        for key in refs:
            refs[key] = ready_ref(gate_id, key)

    for key in list(lineworks["lineworks_send"]):
        lineworks["lineworks_send"][key] = ready_ref("lineworks", key, "b")
    lineworks["connector_refs"] = {
        "lineworks_bot_ref": "LINEWORKS_BOT_REF_READY",
        "lineworks_target_user_ref": "LINEWORKS_TARGET_REF_READY",
        "lineworks_access_token_runtime_ref": "LINEWORKS_TOKEN_RUNTIME_REF_READY",
    }

    line_official["refs"] = {key: f"LINEOA_{key}_READY_REF".upper() for key in line_official["refs"]}

    lineworks_path = tmp / "lineworks_ready.json"
    line_official_path = tmp / "line_official_ready.json"
    config_path = tmp / "merchant_ready.json"
    lineworks_path.write_text(json.dumps(lineworks, ensure_ascii=False, indent=2), encoding="utf-8")
    line_official_path.write_text(json.dumps(line_official, ensure_ascii=False, indent=2), encoding="utf-8")
    config["lineworks_refs_path"] = str(lineworks_path)
    config["line_official_account_refs_path"] = str(line_official_path)
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return config_path


def run_tool(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> int:
    tool_text = require(TOOL, [
        "MERCHANT_READINESS_SERVICE_PATH",
        "build_merchant_productization_readiness",
        "XIAOJ_MERCHANT_PRODUCTIZATION_READINESS_CLI_REPORT_V1",
    ])
    service_text = require(SERVICE, [
        "build_merchant_productization_readiness",
        "W7TP_XIAOJ_MERCHANT_PRODUCTIZATION_READINESS_REPORT_V1",
        "HOLD_XIAOJ_MERCHANT_PRODUCTIZATION_READINESS",
        "PASS_XIAOJ_MERCHANT_PRODUCTIZATION_READINESS",
        "formal_member_registration",
        "formal_pos_write",
        "payment_capture",
        "lineworks_readiness",
        "line_official_account_readiness",
        "operator_next_actions",
        "reject_secret_shapes",
    ])
    template_text = require(TEMPLATE, [
        "W7TP_XIAOJ_MERCHANT_PRODUCTIZATION_READINESS_INPUT_V1",
        "lineworks_refs_path",
        "line_official_account_refs_path",
        "formal_release_refs",
        "member_registration",
        "pos_order",
        "payment",
        "external_api_call",
        "payment_capture",
    ])
    guide_text = require(GUIDE, [
        "STATE=MERCHANT_PRODUCTIZATION_READINESS_GATE_READY",
        "tools/xiaoj_merchant_productization_readiness.py",
        "HOLD_XIAOJ_MERCHANT_PRODUCTIZATION_READINESS",
        "PASS_XIAOJ_MERCHANT_PRODUCTIZATION_READINESS",
        "LINE WORKS notification send",
        "LINE Official Account configuration",
        "/wuchang/xiaoj/api/merchant-productization-readiness",
        "wuchang_cafe_ai_gateway.services.merchant_productization_readiness.build_merchant_productization_readiness",
        "formal member registration",
        "formal POS order creation",
        "formal payment",
        "runtime activation required=true",
    ])
    ctrl_text = require(CTRL, [
        '"/wuchang/xiaoj/api/merchant-productization-readiness", type="json", auth="user"',
        "build_merchant_productization_readiness",
        "xiaoj_api_merchant_productization_readiness",
        "api:/wuchang/xiaoj/api/merchant-productization-readiness",
    ])
    assert_no_secret_shape(tool_text, "tool")
    assert_no_secret_shape(service_text, "service")
    assert_no_secret_shape(template_text, "template")
    assert_no_secret_shape(guide_text, "guide")
    assert_no_secret_shape(ctrl_text, "controller")
    json.loads(template_text)

    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        hold_out = tmp / "hold_report.json"
        hold = run_tool(["--config", str(TEMPLATE), "--out", str(hold_out), "--pretty"])
        if hold.returncode != 2:
            fail(f"hold_template_returncode:{hold.returncode}:{hold.stdout}:{hold.stderr}")
        hold_cli = json.loads(hold.stdout)
        if hold_cli.get("state") != "HOLD_XIAOJ_MERCHANT_PRODUCTIZATION_READINESS":
            fail("hold_cli_state_wrong")
        hold_report = json.loads(hold_out.read_text(encoding="utf-8"))
        if hold_report.get("state") != "HOLD_XIAOJ_MERCHANT_PRODUCTIZATION_READINESS":
            fail("hold_report_state_wrong")
        if hold_report.get("product_ready_for_human_activation") is not False:
            fail("hold_report_ready_not_false")
        assert_side_effects_false(hold_report, "hold_report")
        for action in [
            "fill_line_official_account_safe_refs_and_rerun_config_candidate",
            "fill_verified_lineworks_release_refs_and_runtime_connector_refs",
            "fill_verified_member_registration_release_refs",
            "fill_verified_pos_order_release_refs",
            "fill_verified_payment_release_refs",
        ]:
            if action not in hold_report.get("operator_next_actions", []):
                fail(f"hold_missing_operator_action:{action}")

        ready_config = build_ready_fixture(tmp)
        ready_out = tmp / "ready_report.json"
        ready = run_tool(["--config", str(ready_config), "--out", str(ready_out), "--pretty"])
        if ready.returncode != 0:
            fail(f"ready_fixture_returncode:{ready.returncode}:{ready.stdout}:{ready.stderr}")
        ready_cli = json.loads(ready.stdout)
        if ready_cli.get("state") != "PASS_XIAOJ_MERCHANT_PRODUCTIZATION_READINESS":
            fail("ready_cli_state_wrong")
        ready_report = json.loads(ready_out.read_text(encoding="utf-8"))
        if ready_report.get("state") != "PASS_XIAOJ_MERCHANT_PRODUCTIZATION_READINESS":
            fail("ready_report_state_wrong")
        if ready_report.get("product_ready_for_human_activation") is not True:
            fail("ready_report_ready_not_true")
        assert_side_effects_false(ready_report, "ready_report")
        for key in [
            "member_registration",
            "pos_order",
            "payment",
            "lineworks_send",
            "line_official_account_config",
            "all_required_for_product_activation",
        ]:
            if ready_report.get("formal_release_ready", {}).get(key) is not True:
                fail(f"ready_gate_not_true:{key}")
        if ready_report.get("lineworks", {}).get("preflight_send_allowed") is not True:
            fail("ready_lineworks_preflight_not_true")
        if ready_report.get("line_official_account", {}).get("ready_for_human_approval") is not True:
            fail("ready_line_official_not_true")
        if ready_report.get("authority_boundary", {}).get("llm_direct_execution") is not False:
            fail("ready_llm_direct_execution_not_false")
        if ready_report.get("authority_boundary", {}).get("human_owner_admin_root_of_trust") is not True:
            fail("ready_human_root_not_true")

    print("STATE=PASS_XIAOJ_MERCHANT_PRODUCTIZATION_READINESS_VERIFIER")
    print("TEMPLATE_HOLD=TRUE")
    print("SYNTHETIC_READY_PASS=TRUE")
    print("EXTERNAL_API_CALL=FALSE")
    print("FORMAL_POS_WRITE=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    print("SECRET_READ=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
