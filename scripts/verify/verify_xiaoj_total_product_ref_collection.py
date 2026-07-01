#!/usr/bin/env python3
"""Verify XiaoJ total product ref collection flow."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "packets/product_av_ordering_ai/xiaoj_total_product_ref_collection_contract.json"
TEMPLATE = ROOT / "packets/product_av_ordering_ai/xiaoj_total_product_ref_collection_template.json"
GUIDE = ROOT / "docs/product/XIAOJ_TOTAL_PRODUCT_REF_COLLECTION_GUIDE.md"
SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/total_product_ref_collection.py"
TOOL = ROOT / "tools/xiaoj_total_product_ref_collection_builder.py"
HANDOFF_TOOL = ROOT / "tools/xiaoj_total_product_handoff_pack.py"
CTRL = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/controllers/main.py"


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
    print("STATE=HOLD_XIAOJ_TOTAL_PRODUCT_REF_COLLECTION")
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


def assert_false_map(values: dict, label: str) -> None:
    if not isinstance(values, dict):
        fail(f"missing_false_map:{label}")
    for key, value in values.items():
        if value is not False:
            fail(f"expected_false:{label}:{key}")


def ready_release_ref(prefix: str, key: str, hash_char: str = "d") -> dict:
    return {
        "ref": f"{prefix}_{key}_READY_REF".upper(),
        "packet_hash": hash_char * 64,
        "verifier": "total_field_release_registry",
        "verified": True,
    }


def make_ready_fixture(tmp: Path) -> Path:
    data = json.loads(read(TEMPLATE))
    for key in data["lineworks"]["lineworks_send"]:
        data["lineworks"]["lineworks_send"][key] = ready_release_ref("lineworks", key, "b")
    data["lineworks"]["connector_refs"] = {
        "lineworks_bot_ref": "LINEWORKS_BOT_RUNTIME_READY_REF",
        "lineworks_target_user_ref": "LINEWORKS_TARGET_RUNTIME_READY_REF",
        "lineworks_access_token_runtime_ref": "LINEWORKS_ACCESS_TOKEN_RUNTIME_PROVIDER_READY_REF",
    }
    data["line_official_account"]["refs"] = {
        key: f"LINEOA_{key}_READY_REF".upper()
        for key in data["line_official_account"]["refs"]
    }
    for gate_id, gate_refs in data["merchant_formal_release"].items():
        for key in gate_refs:
            gate_refs[key] = ready_release_ref(gate_id, key, "c")
    data["association_sovereign_member"] = {
        key: f"ASSOCIATION_{key}_READY_REF".upper()
        for key in data["association_sovereign_member"]
    }
    data["resident_property_management"] = {
        key: f"PROPERTY_{key}_READY_REF".upper()
        for key in data["resident_property_management"]
    }
    path = tmp / "ready_refs.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return path


def run_tool(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> int:
    contract_text = require(CONTRACT, [
        "W7TP_XIAOJ_TOTAL_PRODUCT_REF_COLLECTION_CONTRACT_V1",
        "P1_TOTAL_PRODUCT_REF_COLLECTION_READY_FOR_HUMAN_FILL",
        "tools/xiaoj_total_product_ref_collection_builder.py",
        "/wuchang/xiaoj/api/total-product-ref-collection",
        "/wuchang/xiaoj/api/total-product-ref-template",
        "build_total_product_ref_collection_input_template",
        "--emit-template",
        "--worksheet-out",
        "handoff_inputs_output",
        "human_fill_checklist_output",
        "operator_fill_summary_output",
        "operator_fill_worksheet_md_output",
        "tools/xiaoj_total_product_handoff_pack.py --ref-collection <draft.json>",
    ])
    template_text = require(TEMPLATE, [
        "W7TP_XIAOJ_TOTAL_PRODUCT_REF_COLLECTION_INPUT_V1",
        "lineworks",
        "line_official_account",
        "merchant_formal_release",
        "association_sovereign_member",
        "resident_property_management",
    ])
    guide_text = require(GUIDE, [
        "STATE=P1_TOTAL_PRODUCT_REF_COLLECTION_READY_FOR_HUMAN_FILL",
        "tools/xiaoj_total_product_ref_collection_builder.py",
        "--emit-template",
        "--worksheet-out",
        "/wuchang/xiaoj/api/total-product-ref-collection",
        "/wuchang/xiaoj/api/total-product-ref-template",
        "handoff_inputs",
        "human_fill_checklist",
        "operator_fill_summary",
        "operator_fill_worksheet_md",
        "tools/xiaoj_total_product_handoff_pack.py",
        "resident_plaintext_read=false",
    ])
    service_text = require(SERVICE, [
        "build_total_product_ref_collection_input_template",
        "build_total_product_ref_collection_draft",
        "W7TP_XIAOJ_TOTAL_PRODUCT_REF_COLLECTION_DRAFT_V1",
        "TOTAL_PRODUCT_REFS_READY_FOR_HANDOFF_CANDIDATE",
        "HOLD_TOTAL_PRODUCT_REF_COLLECTION_DRAFT",
        "handoff_inputs",
        "human_fill_checklist",
        "operator_fill_summary",
        "operator_fill_worksheet_md",
        "ASSOCIATION_SOVEREIGN_MEMBER_REFS",
        "RESIDENT_PROPERTY_REFS",
    ])
    tool_text = require(TOOL, [
        "W7TP_XIAOJ_TOTAL_PRODUCT_REF_COLLECTION_TEMPLATE_CLI_REPORT_V1",
        "W7TP_XIAOJ_TOTAL_PRODUCT_REF_COLLECTION_CLI_REPORT_V1",
        "build_total_product_ref_collection_input_template",
        "build_total_product_ref_collection_draft",
        "human_fill_ready_count",
        "human_fill_needs_count",
        "operator_fill_worksheet_present",
        "operator_fill_worksheet_path",
        "--emit-template",
        "--worksheet-out",
        "--allow-verified",
    ])
    handoff_tool_text = require(HANDOFF_TOOL, [
        "--ref-collection",
        "handoff_inputs",
    ])
    ctrl_text = require(CTRL, [
        '"/wuchang/xiaoj/api/total-product-ref-collection", type="json", auth="user"',
        '"/wuchang/xiaoj/api/total-product-ref-template", type="json", auth="user"',
        "build_total_product_ref_collection_input_template",
        "build_total_product_ref_collection_draft",
        "xiaoj_api_total_product_ref_template",
        "xiaoj_api_total_product_ref_collection",
    ])
    for label, text in [
        ("contract", contract_text),
        ("template", template_text),
        ("guide", guide_text),
        ("service", service_text),
        ("tool", tool_text),
        ("handoff_tool", handoff_tool_text),
        ("controller", ctrl_text),
    ]:
        assert_no_secret_shape(text, label)
    contract = json.loads(contract_text)
    if contract.get("api_auth") != "user":
        fail("api_auth_wrong")
    if contract.get("requires_allow_verified_for_verified_refs") is not True:
        fail("allow_verified_requirement_missing")
    if contract.get("worksheet_cli") != "tools/xiaoj_total_product_ref_collection_builder.py --worksheet-out <worksheet.md>":
        fail("worksheet_cli_wrong")
    integration = contract.get("handoff_integration", {})
    if integration.get("human_fill_checklist_output") is not True:
        fail("human_fill_checklist_contract_missing")
    if integration.get("operator_fill_summary_output") is not True:
        fail("operator_fill_summary_contract_missing")
    if integration.get("operator_fill_worksheet_md_output") is not True:
        fail("operator_fill_worksheet_contract_missing")
    assert_false_map(contract.get("p1_side_effects", {}), "contract_side_effects")
    json.loads(template_text)

    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        emitted_template_out = tmp / "emitted_template.json"
        emitted_template = run_tool(["--emit-template", "--out", str(emitted_template_out), "--pretty"])
        if emitted_template.returncode != 0:
            fail(f"emit_template_returncode:{emitted_template.returncode}:{emitted_template.stdout}:{emitted_template.stderr}")
        emitted_template_cli = json.loads(emitted_template.stdout)
        if emitted_template_cli.get("state") != "TEMPLATE_REQUIRES_HUMAN_FILLED_REFS":
            fail("emit_template_state_wrong")
        emitted_template_json = json.loads(emitted_template_out.read_text(encoding="utf-8"))
        if emitted_template_json.get("schema") != "W7TP_XIAOJ_TOTAL_PRODUCT_REF_COLLECTION_INPUT_V1":
            fail("emit_template_schema_wrong")
        for key in [
            "lineworks",
            "line_official_account",
            "merchant_formal_release",
            "association_sovereign_member",
            "resident_property_management",
        ]:
            if key not in emitted_template_json:
                fail(f"emit_template_missing:{key}")
        assert_false_map(emitted_template_cli.get("side_effects", {}), "emit_template_side_effects")
        emitted_hold_out = tmp / "emitted_hold_collection.json"
        emitted_hold = run_tool(["--input", str(emitted_template_out), "--out", str(emitted_hold_out), "--pretty"])
        if emitted_hold.returncode != 2:
            fail(f"emitted_hold_returncode:{emitted_hold.returncode}:{emitted_hold.stdout}:{emitted_hold.stderr}")
        emitted_hold_cli = json.loads(emitted_hold.stdout)
        if emitted_hold_cli.get("state") != "HOLD_TOTAL_PRODUCT_REF_COLLECTION_DRAFT":
            fail("emitted_hold_state_wrong")

        hold_out = tmp / "hold_collection.json"
        hold_worksheet = tmp / "hold_worksheet.md"
        hold = run_tool([
            "--input",
            str(TEMPLATE),
            "--out",
            str(hold_out),
            "--worksheet-out",
            str(hold_worksheet),
            "--pretty",
        ])
        if hold.returncode != 2:
            fail(f"hold_returncode:{hold.returncode}:{hold.stdout}:{hold.stderr}")
        hold_cli = json.loads(hold.stdout)
        if hold_cli.get("state") != "HOLD_TOTAL_PRODUCT_REF_COLLECTION_DRAFT":
            fail("hold_cli_state_wrong")
        if hold_cli.get("human_fill_needs_count", 0) <= 0:
            fail("hold_cli_human_fill_needs_missing")
        if hold_cli.get("operator_fill_worksheet_present") is not True:
            fail("hold_cli_operator_worksheet_missing")
        if not hold_cli.get("operator_fill_worksheet_path"):
            fail("hold_cli_operator_worksheet_path_missing")
        hold_report = json.loads(hold_out.read_text(encoding="utf-8"))
        if hold_report.get("ready_for_handoff_candidate") is not False:
            fail("hold_ready_not_false")
        if not hold_report.get("draft_warnings"):
            fail("hold_warnings_missing")
        if not hold_report.get("human_fill_checklist"):
            fail("hold_human_fill_checklist_missing")
        hold_summary = hold_report.get("operator_fill_summary", {})
        if hold_summary.get("needs_human_fill_count", 0) <= 0:
            fail("hold_operator_fill_summary_wrong")
        if hold_summary.get("all_ready") is not False:
            fail("hold_operator_fill_all_ready_wrong")
        worksheet = hold_report.get("operator_fill_worksheet_md", "")
        if "# XiaoJ Total Product Ref Fill Worksheet" not in worksheet:
            fail("hold_operator_worksheet_title_missing")
        if "NEEDS_HUMAN_FILL_COUNT" not in worksheet:
            fail("hold_operator_worksheet_count_missing")
        for group in ["lineworks_send", "line_official_account", "resident_property_management"]:
            if group not in worksheet:
                fail(f"hold_operator_worksheet_group_missing:{group}")
        hold_worksheet_text = hold_worksheet.read_text(encoding="utf-8")
        if hold_worksheet_text != worksheet:
            fail("hold_operator_worksheet_file_mismatch")
        if "TOTAL_REQUIRED" not in hold_worksheet_text:
            fail("hold_operator_worksheet_file_missing_total")
        assert_false_map(hold_report.get("side_effects", {}), "hold_side_effects")

        ready_input = make_ready_fixture(tmp)
        ready_out = tmp / "ready_collection.json"
        ready_worksheet_out = tmp / "ready_worksheet.md"
        ready = run_tool([
            "--input",
            str(ready_input),
            "--out",
            str(ready_out),
            "--worksheet-out",
            str(ready_worksheet_out),
            "--allow-verified",
            "--pretty",
        ])
        if ready.returncode != 0:
            fail(f"ready_returncode:{ready.returncode}:{ready.stdout}:{ready.stderr}")
        ready_cli = json.loads(ready.stdout)
        if ready_cli.get("state") != "TOTAL_PRODUCT_REFS_READY_FOR_HANDOFF_CANDIDATE":
            fail("ready_cli_state_wrong")
        if ready_cli.get("human_fill_needs_count") != 0:
            fail("ready_cli_human_fill_needs_not_zero")
        if ready_cli.get("operator_fill_worksheet_present") is not True:
            fail("ready_cli_operator_worksheet_missing")
        ready_report = json.loads(ready_out.read_text(encoding="utf-8"))
        if ready_report.get("ready_for_handoff_candidate") is not True:
            fail("ready_report_not_true")
        if ready_report.get("draft_warnings"):
            fail(f"ready_warnings_not_empty:{ready_report.get('draft_warnings')[:5]}")
        ready_summary = ready_report.get("operator_fill_summary", {})
        if ready_summary.get("needs_human_fill_count") != 0:
            fail("ready_operator_fill_needs_not_zero")
        if ready_summary.get("all_ready") is not True:
            fail("ready_operator_fill_all_ready_false")
        if len(ready_report.get("human_fill_checklist", [])) != ready_summary.get("total_required"):
            fail("ready_human_fill_checklist_count_wrong")
        ready_worksheet = ready_report.get("operator_fill_worksheet_md", "")
        if "READY_FOR_HANDOFF_CANDIDATE" not in ready_worksheet:
            fail("ready_operator_worksheet_state_missing")
        if ready_worksheet_out.read_text(encoding="utf-8") != ready_worksheet:
            fail("ready_operator_worksheet_file_mismatch")
        for key in ["formal_release_refs", "lineworks_refs", "line_official_account_refs"]:
            if key not in ready_report.get("handoff_inputs", {}):
                fail(f"handoff_input_missing:{key}")
        assert_false_map(ready_report.get("side_effects", {}), "ready_side_effects")

        handoff_out = tmp / "handoff.json"
        handoff = subprocess.run(
            [sys.executable, str(HANDOFF_TOOL), "--ref-collection", str(ready_out), "--out", str(handoff_out), "--pretty"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if handoff.returncode != 0:
            fail(f"handoff_ref_collection_returncode:{handoff.returncode}:{handoff.stdout}:{handoff.stderr}")
        handoff_report = json.loads(handoff_out.read_text(encoding="utf-8"))
        if handoff_report.get("merchant_productization", {}).get("product_ready_for_human_activation") is not True:
            fail("handoff_merchant_ready_not_true")
        if handoff_report.get("production_activation_ready") is not False:
            fail("handoff_production_ready_not_false")
        assert_false_map(handoff_report.get("side_effects", {}), "handoff_side_effects")

    print("STATE=PASS_XIAOJ_TOTAL_PRODUCT_REF_COLLECTION")
    print("TEMPLATE_HOLD=TRUE")
    print("SYNTHETIC_READY_PASS=TRUE")
    print("HANDOFF_REF_COLLECTION_COMPATIBLE=TRUE")
    print("SECRET_READ=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")
    print("RESIDENT_PLAINTEXT_READ=FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
