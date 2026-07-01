#!/usr/bin/env python3
"""Verify XiaoJ total product operator handoff pack."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "packets/product_av_ordering_ai/xiaoj_total_product_operator_handoff_contract.json"
GUIDE = ROOT / "docs/product/XIAOJ_TOTAL_PRODUCT_OPERATOR_HANDOFF_GUIDE.md"
SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/total_product_handoff.py"
TOOL = ROOT / "tools/xiaoj_total_product_handoff_pack.py"
CTRL = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/controllers/main.py"
MODEL = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/models/total_product_handoff.py"
MODEL_INIT = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/models/__init__.py"
VIEW = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/views/total_product_handoff_views.xml"
MANIFEST = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/__manifest__.py"
ACCESS = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/security/ir.model.access.csv"


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
    print("STATE=HOLD_XIAOJ_TOTAL_PRODUCT_OPERATOR_HANDOFF")
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


def main() -> int:
    contract_text = require(CONTRACT, [
        "W7TP_XIAOJ_TOTAL_PRODUCT_OPERATOR_HANDOFF_CONTRACT_V1",
        "P1_TOTAL_PRODUCT_OPERATOR_HANDOFF_READY",
        "tools/xiaoj_total_product_handoff_pack.py",
        "/wuchang/xiaoj/api/total-product-operator-handoff",
        "total_product_ref_collection",
        "merchant_management",
        "association_sovereign_member",
        "resident_property_management",
        "lineworks",
        "line_official_account",
        "resident_property_management",
    ])
    guide_text = require(GUIDE, [
        "STATE=P1_TOTAL_PRODUCT_OPERATOR_HANDOFF_READY",
        "tools/xiaoj_total_product_operator_bundle.py",
        "--input-refs",
        "--allow-verified",
        "Recommended ref collection command before handoff",
        "tools/xiaoj_total_product_ref_collection_builder.py",
        "--emit-template",
        "--worksheet-out",
        "--ref-collection",
        "tools/xiaoj_total_product_handoff_pack.py",
        "/wuchang/xiaoj/api/total-product-ref-template",
        "/wuchang/xiaoj/api/total-product-ref-collection",
        "/wuchang/xiaoj/api/total-product-operator-handoff",
        "WuChang Cafe / Total Product Handoff",
        "Click Load Ref Template",
        "Review Human Fill Checklist",
        "Review Operator Worksheet",
        "merchant management system",
        "association sovereign member system",
        "resident/property management system",
        "production activation remains blocked",
        "resident_plaintext_read=false",
    ])
    service_text = require(SERVICE, [
        "build_total_product_operator_handoff",
        "W7TP_XIAOJ_TOTAL_PRODUCT_OPERATOR_HANDOFF_PACK_V1",
        "PASS_XIAOJ_TOTAL_PRODUCT_OPERATOR_HANDOFF_READY",
        "build_eightd_system_assembly_status",
        "build_merchant_productization_readiness",
        "HUMAN_REF_GROUPS",
        "FORBIDDEN_OPERATOR_INPUTS",
        "ref_template_api",
        "ref_template_cli",
        "ref_collection_api",
        "ref_collection_cli",
        "production_activation_ready",
    ])
    tool_text = require(TOOL, [
        "W7TP_XIAOJ_TOTAL_PRODUCT_OPERATOR_HANDOFF_CLI_REPORT_V1",
        "build_total_product_operator_handoff",
        "--ref-collection",
        "handoff_inputs",
        "runtime/product_av_ordering_ai/total_product_handoff",
    ])
    ctrl_text = require(CTRL, [
        '"/wuchang/xiaoj/api/total-product-ref-template", type="json", auth="user"',
        '"/wuchang/xiaoj/api/total-product-ref-collection", type="json", auth="user"',
        '"/wuchang/xiaoj/api/total-product-operator-handoff", type="json", auth="user"',
        "build_total_product_ref_collection_input_template",
        "build_total_product_ref_collection_draft",
        "build_total_product_operator_handoff",
        "xiaoj_api_total_product_ref_template",
        "xiaoj_api_total_product_ref_collection",
        "xiaoj_api_total_product_operator_handoff",
    ])
    model_text = require(MODEL, [
        '_name = "wuchang.total.product.operator.handoff"',
        "build_total_product_ref_collection_input_template",
        "action_load_ref_template",
        "action_build_ref_collection",
        "action_build_handoff_pack",
        "action_dead_letter",
        "human_fill_checklist_json",
        "operator_fill_worksheet_md",
        "ready_ref_count",
        "needs_human_fill_count",
        "build_total_product_ref_collection_draft",
        "build_total_product_operator_handoff",
        "_assert_no_secret_material",
        "@api.constrains",
        "formal_lineworks_send",
        "formal_line_message_send",
        "formal_member_registration",
        "formal_pos_write",
        "payment_capture",
        "secret_read",
        "member_plaintext_read",
        "resident_plaintext_read",
        "production_activation_ready",
    ])
    view_text = require(VIEW, [
        "Total Product Operator Handoff",
        "action_load_ref_template",
        "Load Ref Template",
        "action_build_ref_collection",
        "Build Ref Collection",
        "action_build_handoff_pack",
        "Build Handoff Pack",
        "Side Effect Boundary",
        "Total Product Refs",
        "Ref Collection",
        "Human Fill Checklist",
        "Operator Worksheet",
        "Handoff Pack",
        "menu_wuchang_total_product_operator_handoff",
    ])
    require(MODEL_INIT, ["total_product_handoff"])
    require(MANIFEST, ["views/total_product_handoff_views.xml"])
    require(ACCESS, [
        "model_wuchang_total_product_operator_handoff",
        "base.group_user,1,1,1,0",
        "base.group_system,1,1,1,1",
    ])
    for label, text in [
        ("contract", contract_text),
        ("guide", guide_text),
        ("service", service_text),
        ("tool", tool_text),
        ("controller", ctrl_text),
        ("model", model_text),
        ("view", view_text),
    ]:
        assert_no_secret_shape(text, label)
    for forbidden in [
        "requests.post",
        "urlopen",
        "http.client",
        "external_api_call = True",
        "formal_lineworks_send = True",
        "formal_line_message_send = True",
        "formal_pos_write = True",
        "payment_capture = True",
        "secret_read = True",
        "member_plaintext_read = True",
        "resident_plaintext_read = True",
    ]:
        if forbidden in model_text:
            fail(f"model_forbidden:{forbidden}")

    contract = json.loads(contract_text)
    if contract.get("api_auth") != "user":
        fail("api_auth_wrong")
    if contract.get("production_activation_ready_by_default") is not False:
        fail("contract_production_ready_not_false")
    if contract.get("handoff_ready_for_operator") is not True:
        fail("contract_handoff_ready_not_true")
    assert_false_map(contract.get("p1_side_effects", {}), "contract_side_effects")

    with tempfile.TemporaryDirectory() as tmp:
        template_path = Path(tmp) / "service_template.json"
        template_code = f"""
import importlib.util
import json
import sys
import types
from pathlib import Path

root = Path({str(ROOT)!r})

def pkg(name, rel_path):
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        sys.modules[name] = module
    module.__path__ = [str(root / rel_path)]

pkg("Taiji_Odoo", "Taiji_Odoo")
pkg("Taiji_Odoo.addons", "Taiji_Odoo/addons")
pkg("Taiji_Odoo.addons.wuchang_cafe_ai_gateway", "Taiji_Odoo/addons/wuchang_cafe_ai_gateway")
pkg("Taiji_Odoo.addons.wuchang_cafe_ai_gateway.services", "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services")
spec = importlib.util.spec_from_file_location(
    "Taiji_Odoo.addons.wuchang_cafe_ai_gateway.services.total_product_ref_collection",
    str(root / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/total_product_ref_collection.py"),
)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
print(json.dumps(module.build_total_product_ref_collection_input_template(), ensure_ascii=False, sort_keys=True))
"""
        template_proc = subprocess.run(
            [
                sys.executable,
                "-c",
                template_code,
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if template_proc.returncode != 0:
            fail(f"template_service_returncode:{template_proc.returncode}:{template_proc.stdout}:{template_proc.stderr}")
        template = json.loads(template_proc.stdout)
        if template.get("state") != "TEMPLATE_REQUIRES_HUMAN_FILLED_REFS":
            fail("template_service_state_wrong")
        for key in ["lineworks", "line_official_account", "merchant_formal_release", "association_sovereign_member", "resident_property_management"]:
            if key not in template:
                fail(f"template_service_missing:{key}")
        template_path.write_text(json.dumps(template, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        template_hold = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools/xiaoj_total_product_ref_collection_builder.py"),
                "--input",
                str(template_path),
                "--pretty",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if template_hold.returncode != 2:
            fail(f"template_hold_returncode:{template_hold.returncode}:{template_hold.stdout}:{template_hold.stderr}")
        template_cli = json.loads(template_hold.stdout)
        if template_cli.get("state") != "HOLD_TOTAL_PRODUCT_REF_COLLECTION_DRAFT":
            fail("template_hold_state_wrong")

        out_path = Path(tmp) / "handoff.json"
        proc = subprocess.run(
            [sys.executable, str(TOOL), "--out", str(out_path), "--pretty"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            fail(f"tool_returncode:{proc.returncode}:{proc.stdout}:{proc.stderr}")
        cli_report = json.loads(proc.stdout)
        if cli_report.get("state") != "PASS_XIAOJ_TOTAL_PRODUCT_OPERATOR_HANDOFF_READY":
            fail("cli_state_wrong")
        if cli_report.get("production_activation_ready") is not False:
            fail("cli_production_ready_not_false")
        report = json.loads(out_path.read_text(encoding="utf-8"))
        if report.get("state") != "PASS_XIAOJ_TOTAL_PRODUCT_OPERATOR_HANDOFF_READY":
            fail("report_state_wrong")
        if report.get("handoff_ready_for_operator") is not True:
            fail("report_handoff_ready_not_true")
        if report.get("production_activation_ready") is not False:
            fail("report_production_ready_not_false")
        for system_id in ["merchant_management", "association_sovereign_member", "resident_property_management"]:
            if system_id not in report.get("systems", {}):
                fail(f"report_system_missing:{system_id}")
        for group in [
            "lineworks",
            "line_official_account",
            "merchant_formal_release",
            "association_sovereign_member",
            "resident_property_management",
        ]:
            if group not in report.get("human_ref_groups", {}):
                fail(f"human_ref_group_missing:{group}")
        for forbidden in ["Google Gemini raw API key", "member plaintext", "resident plaintext", "payment card data"]:
            if forbidden not in report.get("forbidden_operator_inputs", []):
                fail(f"forbidden_input_missing:{forbidden}")
        if len(report.get("operator_checklist", [])) < 5:
            fail("operator_checklist_too_short")
        if report.get("authority_boundary", {}).get("llm_direct_execution") is not False:
            fail("llm_direct_execution_not_false")
        if report.get("authority_boundary", {}).get("human_owner_admin_root_of_trust") is not True:
            fail("human_root_not_true")
        delivered = report.get("delivered_interfaces", {})
        if delivered.get("ref_template_api") != "/wuchang/xiaoj/api/total-product-ref-template":
            fail("ref_template_api_missing")
        if delivered.get("ref_template_cli") != "tools/xiaoj_total_product_ref_collection_builder.py --emit-template":
            fail("ref_template_cli_missing")
        if delivered.get("ref_collection_api") != "/wuchang/xiaoj/api/total-product-ref-collection":
            fail("ref_collection_api_missing")
        if delivered.get("ref_collection_cli") != "tools/xiaoj_total_product_ref_collection_builder.py":
            fail("ref_collection_cli_missing")
        if delivered.get("total_handoff_cli") != "tools/xiaoj_total_product_handoff_pack.py":
            fail("total_handoff_cli_missing")
        assert_false_map(report.get("side_effects", {}), "report_side_effects")

    print("STATE=PASS_XIAOJ_TOTAL_PRODUCT_OPERATOR_HANDOFF")
    print("HANDOFF_READY_FOR_OPERATOR=TRUE")
    print("PRODUCTION_ACTIVATION_READY=FALSE")
    print("TOTAL_PRODUCT_API=/wuchang/xiaoj/api/total-product-operator-handoff")
    print("SECRET_READ=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")
    print("RESIDENT_PLAINTEXT_READ=FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
