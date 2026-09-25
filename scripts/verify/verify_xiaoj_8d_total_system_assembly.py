#!/usr/bin/env python3
"""Verify XiaoJ 8D total system assembly delivery."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "packets/product_av_ordering_ai/xiaoj_8d_total_system_assembly_contract.json"
GUIDE = ROOT / "docs/product/XIAOJ_8D_TOTAL_SYSTEM_ASSEMBLY_GUIDE.md"
SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/eightd_system_assembly.py"
TOOL = ROOT / "tools/xiaoj_8d_system_assembly_report.py"
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
    print("STATE=HOLD_XIAOJ_8D_TOTAL_SYSTEM_ASSEMBLY")
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
        "W7TP_XIAOJ_8D_TOTAL_SYSTEM_ASSEMBLY_CONTRACT_V1",
        "P1_8D_TOTAL_SYSTEM_ASSEMBLY_READY_FOR_HUMAN_REVIEW",
        "8維度意圖場封包自然語言控制系統總成",
        "merchant_management",
        "association_sovereign_member",
        "resident_property_management",
        "D1_identity",
        "D8_envelope",
        "tools/xiaoj_8d_system_assembly_report.py",
        "/wuchang/xiaoj/api/8d-system-assembly-status",
    ])
    guide_text = require(GUIDE, [
        "STATE=P1_8D_TOTAL_SYSTEM_ASSEMBLY_READY_FOR_HUMAN_REVIEW",
        "商家管理系統",
        "協會會員 8 維度主權會員系統",
        "8 維度主權住戶整合式物業管理系統",
        "tools/xiaoj_8d_system_assembly_report.py",
        "/wuchang/xiaoj/api/8d-system-assembly-status",
        "secret_read=false",
        "resident_plaintext_read=false",
        "llm_direct_execution=false",
    ])
    service_text = require(SERVICE, [
        "build_eightd_system_assembly_status",
        "W7TP_XIAOJ_8D_TOTAL_SYSTEM_ASSEMBLY_STATUS_V1",
        "PASS_XIAOJ_8D_TOTAL_SYSTEM_ASSEMBLY_P1_READY_FOR_HUMAN_REVIEW",
        "merchant_management",
        "association_sovereign_member",
        "resident_property_management",
        "D1_identity",
        "D8_envelope",
        "candidate_action",
        "merchant_capability_payload",
    ])
    tool_text = require(TOOL, [
        "W7TP_XIAOJ_8D_TOTAL_SYSTEM_ASSEMBLY_CLI_REPORT_V1",
        "build_eightd_system_assembly_status",
        "runtime/product_av_ordering_ai/8d_system_assembly",
    ])
    ctrl_text = require(CTRL, [
        '"/wuchang/xiaoj/api/8d-system-assembly-status", type="json", auth="user"',
        "build_eightd_system_assembly_status",
        "xiaoj_api_8d_system_assembly_status",
    ])
    for label, text in [
        ("contract", contract_text),
        ("guide", guide_text),
        ("service", service_text),
        ("tool", tool_text),
        ("controller", ctrl_text),
    ]:
        assert_no_secret_shape(text, label)

    contract = json.loads(contract_text)
    if contract.get("api_auth") != "user":
        fail("api_auth_wrong")
    if len(contract.get("eightd_dimensions", [])) != 8:
        fail("contract_dimension_count_wrong")
    for key, value in contract.get("p1_side_effects", {}).items():
        if value is not False:
            fail(f"contract_side_effect_not_false:{key}")

    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "assembly.json"
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
        if cli_report.get("state") != "PASS_XIAOJ_8D_TOTAL_SYSTEM_ASSEMBLY_P1_READY_FOR_HUMAN_REVIEW":
            fail("cli_state_wrong")
        report = json.loads(out_path.read_text(encoding="utf-8"))
        if report.get("state") != "PASS_XIAOJ_8D_TOTAL_SYSTEM_ASSEMBLY_P1_READY_FOR_HUMAN_REVIEW":
            fail("report_state_wrong")
        if len(report.get("eightd_dimensions", [])) != 8:
            fail("report_dimension_count_wrong")
        systems = report.get("systems", {})
        for system_id in ["merchant_management", "association_sovereign_member", "resident_property_management"]:
            system = systems.get(system_id)
            if not isinstance(system, dict):
                fail(f"system_missing:{system_id}")
            if system.get("eightd_packet_required") is not True:
                fail(f"system_8d_required_not_true:{system_id}")
            if system.get("candidate_only_before_local_verifier") is not True:
                fail(f"system_candidate_only_not_true:{system_id}")
            if system.get("probe", {}).get("full_body_transmitted") is not False:
                fail(f"system_full_body_transmitted_not_false:{system_id}")
            if system.get("probe", {}).get("cloud_authority") is not False:
                fail(f"system_cloud_authority_not_false:{system_id}")
            if not system.get("probe", {}).get("packet_hash"):
                fail(f"system_packet_hash_missing:{system_id}")
            boundary = system.get("execution_boundary", {})
            for key in [
                "formal_db_write",
                "formal_pos_write",
                "payment_capture",
                "member_plaintext_read",
                "resident_plaintext_read",
                "external_api_call",
            ]:
                if boundary.get(key) is not False:
                    fail(f"execution_boundary_not_false:{system_id}:{key}")
            if boundary.get("requires_human_release") is not True:
                fail(f"execution_boundary_human_release_not_true:{system_id}")
        if report.get("release_boundary", {}).get("production_activation_ready") is not False:
            fail("production_activation_ready_not_false")
        assert_false_map(report.get("side_effects", {}), "report_side_effects")

    print("STATE=PASS_XIAOJ_8D_TOTAL_SYSTEM_ASSEMBLY")
    print("MERCHANT_MANAGEMENT=READY_P1")
    print("ASSOCIATION_SOVEREIGN_MEMBER=READY_P1_PARTIAL_RELEASE")
    print("RESIDENT_PROPERTY_MANAGEMENT=READY_P1")
    print("DIMENSIONS=8")
    print("PRODUCTION_ACTIVATION_READY=FALSE")
    print("SECRET_READ=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")
    print("RESIDENT_PLAINTEXT_READ=FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
