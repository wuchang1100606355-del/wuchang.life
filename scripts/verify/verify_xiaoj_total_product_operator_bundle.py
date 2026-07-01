#!/usr/bin/env python3
"""Verify XiaoJ total product operator bundle generation."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "packets/product_av_ordering_ai/xiaoj_total_product_operator_bundle_contract.json"
GUIDE = ROOT / "docs/product/XIAOJ_TOTAL_PRODUCT_OPERATOR_BUNDLE_GUIDE.md"
TOOL = ROOT / "tools/xiaoj_total_product_operator_bundle.py"
SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/total_product_operator_bundle.py"
CONTROLLER = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/controllers/main.py"

REQUIRED_FILES = [
    "README.md",
    "MANIFEST.json",
    "ref_template.json",
    "ref_collection.json",
    "ref_worksheet.md",
    "handoff.json",
]

SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9_-]{12,}",
    r"(?i)(access|refresh|id)_token\s*[:=]\s*\S+",
    r"(?i)channel_secret\s*[:=]\s*\S+",
    r"(?i)client_secret\s*[:=]\s*\S+",
    r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}",
    r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}",
    r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",
    r"09\d{2}[- ]?\d{3}[- ]?\d{3}",
    r"\b[A-Z][12]\d{8}\b",
]


def fail(message: str) -> None:
    print(f"VERIFY_FAIL={message}")
    print("STATE=HOLD_XIAOJ_TOTAL_PRODUCT_OPERATOR_BUNDLE")
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ready_release_ref(prefix: str, key: str, hash_char: str = "d") -> dict:
    return {
        "ref": f"{prefix}_{key}_READY_REF".upper(),
        "packet_hash": hash_char * 64,
        "verifier": "total_field_release_registry",
        "verified": True,
    }


def make_ready_refs(template_path: Path, output_path: Path) -> None:
    data = json.loads(template_path.read_text(encoding="utf-8"))
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
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def main() -> int:
    contract_text = require(
        CONTRACT,
        [
            "W7TP_XIAOJ_TOTAL_PRODUCT_OPERATOR_BUNDLE_CONTRACT_V1",
            "P1_TOTAL_PRODUCT_OPERATOR_BUNDLE_READY",
            "tools/xiaoj_total_product_operator_bundle.py",
            "wuchang_cafe_ai_gateway.services.total_product_operator_bundle.build_total_product_operator_bundle_payload",
            "/wuchang/xiaoj/api/total-product-operator-bundle",
            "tool_refresh_with_filled_refs",
            "ref_worksheet.md",
            "handoff.json",
            "production_activation_ready_by_default",
        ],
    )
    guide_text = require(
        GUIDE,
        [
            "STATE=P1_TOTAL_PRODUCT_OPERATOR_BUNDLE_READY",
            "tools/xiaoj_total_product_operator_bundle.py",
            "POST /wuchang/xiaoj/api/total-product-operator-bundle",
            "W7TP_XIAOJ_TOTAL_PRODUCT_OPERATOR_BUNDLE_PAYLOAD_V1",
            "The API does not accept server file paths",
            "--input-refs",
            "--allow-verified",
            "runtime/product_av_ordering_ai/total_product_operator_bundle/",
            "ref_template.json",
            "ref_collection.json",
            "ref_worksheet.md",
            "handoff.json",
            "secret_read=false",
            "resident_plaintext_read=false",
        ],
    )
    service_text = require(
        SERVICE,
        [
            "build_total_product_operator_bundle_payload",
            "W7TP_XIAOJ_TOTAL_PRODUCT_OPERATOR_BUNDLE_PAYLOAD_V1",
            "build_total_product_operator_bundle_readme",
            "build_total_product_ref_collection_draft",
            "build_total_product_operator_handoff",
            "\"formal_db_write\": False",
            "\"secret_read\": False",
            "\"resident_plaintext_read\": False",
        ],
    )
    tool_text = require(
        TOOL,
        [
            "BUNDLE_SERVICE",
            "build_total_product_operator_bundle_payload",
            "W7TP_XIAOJ_TOTAL_PRODUCT_OPERATOR_BUNDLE_MANIFEST_V1",
            "PASS_XIAOJ_TOTAL_PRODUCT_OPERATOR_BUNDLE_READY",
            "W7TP_XIAOJ_TOTAL_PRODUCT_OPERATOR_BUNDLE_CLI_REPORT_V1",
            "--input-refs",
            "--allow-verified",
            "ref_template.json",
            "ref_collection.json",
            "ref_worksheet.md",
            "handoff.json",
        ],
    )
    controller_text = require(
        CONTROLLER,
        [
            "build_total_product_operator_bundle_payload",
            "\"xiaoj_total_product_operator_bundle_api\": \"PASS_XIAOJ_TOTAL_PRODUCT_OPERATOR_BUNDLE_READY\"",
            "@http.route(\"/wuchang/xiaoj/api/total-product-operator-bundle\", type=\"json\", auth=\"user\", csrf=False)",
            "input_ref=\"api:/wuchang/xiaoj/api/total-product-operator-bundle:refs\"",
            "bundle_ref=\"api:/wuchang/xiaoj/api/total-product-operator-bundle\"",
        ],
    )
    for label, text in [
        ("contract", contract_text),
        ("guide", guide_text),
        ("service", service_text),
        ("tool", tool_text),
        ("controller", controller_text),
    ]:
        assert_no_secret_shape(text, label)

    contract = json.loads(contract_text)
    if contract.get("production_activation_ready_by_default") is not False:
        fail("contract_production_ready_not_false")
    if contract.get("api_writes_files") is not False:
        fail("contract_api_writes_files_not_false")
    if contract.get("api_auth") != "user":
        fail("contract_api_auth_wrong")
    if contract.get("api") != "/wuchang/xiaoj/api/total-product-operator-bundle":
        fail("contract_api_wrong")
    if "--input-refs <filled_refs.json> --allow-verified" not in contract.get("tool_refresh_with_filled_refs", ""):
        fail("contract_refresh_command_missing")
    assert_false_map(contract.get("p1_side_effects", {}), "contract_side_effects")
    for name in REQUIRED_FILES:
        if name not in contract.get("bundle_files", []):
            fail(f"contract_file_missing:{name}")

    with tempfile.TemporaryDirectory() as tmp_name:
        bundle_dir = Path(tmp_name) / "bundle"
        proc = subprocess.run(
            [sys.executable, str(TOOL), "--out-dir", str(bundle_dir), "--pretty"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            fail(f"tool_returncode:{proc.returncode}:{proc.stdout}:{proc.stderr}")
        cli_report = json.loads(proc.stdout)
        if cli_report.get("state") != "PASS_XIAOJ_TOTAL_PRODUCT_OPERATOR_BUNDLE_READY":
            fail("cli_state_wrong")
        if cli_report.get("production_activation_ready") is not False:
            fail("cli_production_ready_not_false")
        assert_false_map(cli_report.get("side_effects", {}), "cli_side_effects")

        for name in REQUIRED_FILES:
            if not (bundle_dir / name).exists():
                fail(f"bundle_file_missing:{name}")
            assert_no_secret_shape((bundle_dir / name).read_text(encoding="utf-8"), f"bundle:{name}")

        manifest = json.loads((bundle_dir / "MANIFEST.json").read_text(encoding="utf-8"))
        if manifest.get("schema") != "W7TP_XIAOJ_TOTAL_PRODUCT_OPERATOR_BUNDLE_MANIFEST_V1":
            fail("manifest_schema_wrong")
        if manifest.get("state") != "PASS_XIAOJ_TOTAL_PRODUCT_OPERATOR_BUNDLE_READY":
            fail("manifest_state_wrong")
        if manifest.get("production_activation_ready") is not False:
            fail("manifest_production_ready_not_false")
        if manifest.get("handoff_ready_for_operator") is not True:
            fail("manifest_handoff_ready_not_true")
        if manifest.get("operator_fill_summary", {}).get("needs_human_fill_count", 0) <= 0:
            fail("manifest_needs_human_fill_missing")
        assert_false_map(manifest.get("side_effects", {}), "manifest_side_effects")
        for name in ["README.md", "ref_template.json", "ref_collection.json", "ref_worksheet.md", "handoff.json"]:
            entry = manifest.get("files", {}).get(name)
            if not entry:
                fail(f"manifest_file_entry_missing:{name}")
            if entry.get("sha256") != sha256(bundle_dir / name):
                fail(f"manifest_sha_wrong:{name}")

        ref_collection = json.loads((bundle_dir / "ref_collection.json").read_text(encoding="utf-8"))
        if ref_collection.get("state") != "HOLD_TOTAL_PRODUCT_REF_COLLECTION_DRAFT":
            fail("ref_collection_state_wrong")
        if not ref_collection.get("operator_fill_worksheet_md"):
            fail("ref_collection_worksheet_missing")
        worksheet = (bundle_dir / "ref_worksheet.md").read_text(encoding="utf-8")
        if "# XiaoJ Total Product Ref Fill Worksheet" not in worksheet:
            fail("worksheet_title_missing")
        if "NEEDS_HUMAN_FILL_COUNT" not in worksheet:
            fail("worksheet_needs_count_missing")
        if worksheet != ref_collection.get("operator_fill_worksheet_md"):
            fail("worksheet_mismatch")

        handoff = json.loads((bundle_dir / "handoff.json").read_text(encoding="utf-8"))
        if handoff.get("state") != "PASS_XIAOJ_TOTAL_PRODUCT_OPERATOR_HANDOFF_READY":
            fail("handoff_state_wrong")
        if handoff.get("production_activation_ready") is not False:
            fail("handoff_production_ready_not_false")
        assert_false_map(handoff.get("side_effects", {}), "handoff_side_effects")

        ready_refs = Path(tmp_name) / "ready_refs.json"
        ready_bundle_dir = Path(tmp_name) / "ready_bundle"
        make_ready_refs(bundle_dir / "ref_template.json", ready_refs)
        ready_proc = subprocess.run(
            [
                sys.executable,
                str(TOOL),
                "--input-refs",
                str(ready_refs),
                "--allow-verified",
                "--out-dir",
                str(ready_bundle_dir),
                "--pretty",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if ready_proc.returncode != 0:
            fail(f"ready_tool_returncode:{ready_proc.returncode}:{ready_proc.stdout}:{ready_proc.stderr}")
        ready_cli = json.loads(ready_proc.stdout)
        if ready_cli.get("needs_human_fill_count") != 0:
            fail("ready_cli_needs_human_fill_not_zero")
        if ready_cli.get("allow_verified") is not True:
            fail("ready_cli_allow_verified_not_true")
        ready_manifest = json.loads((ready_bundle_dir / "MANIFEST.json").read_text(encoding="utf-8"))
        if ready_manifest.get("operator_fill_summary", {}).get("needs_human_fill_count") != 0:
            fail("ready_manifest_needs_human_fill_not_zero")
        if ready_manifest.get("production_activation_ready") is not False:
            fail("ready_manifest_production_ready_not_false")
        ready_ref_collection = json.loads((ready_bundle_dir / "ref_collection.json").read_text(encoding="utf-8"))
        if ready_ref_collection.get("state") != "TOTAL_PRODUCT_REFS_READY_FOR_HANDOFF_CANDIDATE":
            fail("ready_ref_collection_state_wrong")
        ready_worksheet = (ready_bundle_dir / "ref_worksheet.md").read_text(encoding="utf-8")
        if "READY_FOR_HANDOFF_CANDIDATE" not in ready_worksheet:
            fail("ready_worksheet_state_missing")
        ready_handoff = json.loads((ready_bundle_dir / "handoff.json").read_text(encoding="utf-8"))
        if ready_handoff.get("merchant_productization", {}).get("product_ready_for_human_activation") is not True:
            fail("ready_handoff_merchant_not_ready")
        if ready_handoff.get("production_activation_ready") is not False:
            fail("ready_handoff_production_ready_not_false")
        assert_false_map(ready_manifest.get("side_effects", {}), "ready_manifest_side_effects")

    print("STATE=PASS_XIAOJ_TOTAL_PRODUCT_OPERATOR_BUNDLE")
    print("BUNDLE_READY=TRUE")
    print("PRODUCTION_ACTIVATION_READY=FALSE")
    print("SECRET_READ=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")
    print("RESIDENT_PLAINTEXT_READ=FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
