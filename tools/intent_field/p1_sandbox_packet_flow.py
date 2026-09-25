#!/usr/bin/env python3
"""Sandbox-only P1 packet-flow landing orchestrator."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path("/home/taiji_admin/Taiji_Hub")
TOOL_DIR = Path(__file__).resolve().parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

from accountable_record_chain import verify_chain  # noqa: E402
from front_edge_proxy_blocking import verify_proxy_packet  # noqa: E402
from integrated_p0_verify import (  # noqa: E402
    ACCOUNTABLE_CHAIN_RUN,
    CANDIDATE_PATH,
    FRONT_EDGE_RUN,
    IDENTITY_RUN,
    SEAL_DIR,
    STATE_FIELD_PACKET_RUN,
    build_integrated_packet,
    build_test_cases as build_integrated_test_cases,
    verify_integrated_packet,
)
from redact_candidate_payload import scan_text  # noqa: E402
from sovereign_identity_agent import verify_identity_packet  # noqa: E402
from state_field_packet_runtime import verify_packet  # noqa: E402


P0_DECISION_RUN = ROOT / "runtime/total_field/sandbox_p0_review_stage_decision/SANDBOX_P0_REVIEW_STAGE_DECISION_20260704T222207Z"
P0_STAGE_DECISION_PATH = P0_DECISION_RUN / "STAGE_DECISION.md"
INTEGRATED_P0_RUN = ROOT / "runtime/total_field/integrated_p0_verify_sandbox/INTEGRATED_P0_VERIFY_SANDBOX_20260704T221916Z"
P1_SANDBOX_ROOT = ROOT / "runtime/total_field/p1_sandbox_packet_flow"

TECHNICAL_MEANS_KEYS = [
    "modules",
    "data_structures",
    "packet_fields",
    "verification_conditions",
    "blocking_conditions",
    "record_fields",
]
FLOW_ORDER = [
    "cloud_candidate_response_ref_only",
    "sovereign_identity_agent",
    "state_field_packet_runtime",
    "front_edge_proxy_blocking",
    "accountable_record_chain",
    "integrated_verifier",
    "total_field_governance_decision",
]
CASE_NAME_MAP = {
    "PASS_FULL_PATH": "PASS_P1_SANDBOX_FLOW",
    "HOLD_MISSING_CONSENT": "HOLD_MISSING_CONSENT",
    "HOLD_MISSING_VERIFIER": "HOLD_MISSING_VERIFIER",
    "REJECT_DIRECT_BUSINESS_WRITE": "REJECT_DIRECT_BUSINESS_WRITE",
    "REJECT_MEMBER_PLAINTEXT": "REJECT_MEMBER_PLAINTEXT",
    "REJECT_SECRET": "REJECT_SECRET",
    "REJECT_FIELD_DRIFT": "REJECT_FIELD_DRIFT",
    "REJECT_ADI_DRIFT": "REJECT_ADI_DRIFT",
    "REJECT_CLOUD_AUTHORITY_DRIFT": "REJECT_CLOUD_AUTHORITY_DRIFT",
}
EXPECTED_P1_DECISIONS = {
    "PASS_P1_SANDBOX_FLOW": "ALLOW_RESTRICTED",
    "HOLD_MISSING_CONSENT": "HOLD",
    "HOLD_MISSING_VERIFIER": "HOLD",
    "REJECT_DIRECT_BUSINESS_WRITE": "BLOCK",
    "REJECT_MEMBER_PLAINTEXT": "BLOCK",
    "REJECT_SECRET": "BLOCK",
    "REJECT_FIELD_DRIFT": "BLOCK",
    "REJECT_ADI_DRIFT": "BLOCK",
    "REJECT_CLOUD_AUTHORITY_DRIFT": "BLOCK",
}
STATIC_OUTPUT_FILES = [
    ROOT / "schemas/intent_field/p1_sandbox_packet_flow.schema.json",
    ROOT / "tools/intent_field/p1_sandbox_packet_flow.py",
    ROOT / "tools/intent_field/verify_p1_sandbox_packet_flow.py",
    ROOT / "scripts/intent_field/run_p1_sandbox_packet_flow.sh",
]


def now_utc() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")


def iso_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_ref(path: Path) -> dict[str, str]:
    return {"path_ref": rel(path), "sha256": sha256_file(path)}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def parse_bool(value: str) -> bool | str:
    lower = value.strip().lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    return value.strip()


def parse_stage_decision(path: Path = P0_STAGE_DECISION_PATH) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = parse_bool(value)
    return {
        "P0_EVIDENCE_SUMMARY": values.get("P0_EVIDENCE_SUMMARY"),
        "P0_REDTTEAM_DECISION": values.get("P0_REDTTEAM_DECISION"),
        "P1_ALLOWED": values.get("P1_ALLOWED") is True or values.get("ALLOW_P1_SANDBOX_LANDING") is True,
        "P1_SCOPE": values.get("P1_SCOPE"),
        "ALLOW_PRODUCTION": values.get("ALLOW_PRODUCTION", False),
        "ALLOW_DB_WRITE": values.get("ALLOW_DB_WRITE", False),
        "ALLOW_DEPLOY": values.get("ALLOW_DEPLOY", False),
        "ALLOW_RESTART": values.get("ALLOW_RESTART", False),
        "NEXT": values.get("NEXT"),
    }


def merge_technical_means(integrated_packet: dict[str, Any]) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {key: [] for key in TECHNICAL_MEANS_KEYS}
    source = integrated_packet.get("technical_means", {})
    for key in TECHNICAL_MEANS_KEYS:
        for item in source.get(key, []):
            if item not in merged[key]:
                merged[key].append(item)
    additions = {
        "modules": ["p1_sandbox_packet_flow_cli", "p1_sandbox_orchestrator"],
        "data_structures": ["p1_sandbox_packet_flow", "p1_flow_step_list"],
        "packet_fields": ["flow_steps", "p0_stage_decision", "p1_decision", "safety_boundary"],
        "verification_conditions": [
            "p0_stage_decision_p1_allowed_required",
            "flow_step_order_required",
            "integrated_verifier_pass_required",
            "sandbox_only_boundary_required",
        ],
        "blocking_conditions": [
            "p0_not_allowed_for_p1",
            "production_boundary_requested",
            "cloud_authority_drift",
            "direct_business_write_requested",
        ],
        "record_fields": ["accountable_record_ref", "previous_record_hash", "current_record_hash"],
    }
    for key, items in additions.items():
        for item in items:
            if item not in merged[key]:
                merged[key].append(item)
    return merged


def build_flow_steps(integrated_packet: dict[str, Any], integrated_verifier: dict[str, Any]) -> list[dict[str, Any]]:
    decision = integrated_packet.get("governance_decision", {})
    return [
        {
            "order": 1,
            "step": "cloud_candidate_response_ref_only",
            "status": integrated_packet.get("candidate_verification", {}).get("decision", "UNKNOWN"),
            "input_ref": file_ref(CANDIDATE_PATH),
        },
        {
            "order": 2,
            "step": "sovereign_identity_agent",
            "status": integrated_verifier.get("SOVEREIGN_IDENTITY_AGENT_CHECK", "UNKNOWN"),
            "output": "identity_proxy_ref authority_scope_code consent_state_code",
        },
        {
            "order": 3,
            "step": "state_field_packet_runtime",
            "status": integrated_verifier.get("STATE_FIELD_PACKET_RUNTIME_CHECK", "UNKNOWN"),
            "output": "state_field_set_id state_field_relation_table dynamic_field_policy_id before_after_hash",
        },
        {
            "order": 4,
            "step": "front_edge_proxy_blocking",
            "status": integrated_verifier.get("FRONT_EDGE_BLOCKING_CHECK", "UNKNOWN"),
            "output": "restricted_execution_instruction_ref_or_hold_reject",
        },
        {
            "order": 5,
            "step": "accountable_record_chain",
            "status": integrated_verifier.get("ACCOUNTABLE_RECORD_CHAIN_CHECK", "UNKNOWN"),
            "output": decision.get("accountable_record_ref", ""),
        },
        {
            "order": 6,
            "step": "integrated_verifier",
            "status": integrated_verifier.get("DRY_RUN", "UNKNOWN"),
            "output": "integrated_p0_verifier_result",
        },
        {
            "order": 7,
            "step": "total_field_governance_decision",
            "status": decision.get("decision", "UNKNOWN"),
            "output": "total_field_only_decision",
        },
    ]


def build_p1_packet(
    case_name: str = "PASS_P1_SANDBOX_FLOW",
    integrated_packet: dict[str, Any] | None = None,
    integrated_verifier: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if integrated_packet is None:
        integrated_packet = build_integrated_packet("PASS_FULL_PATH")
    if integrated_verifier is None:
        integrated_verifier = verify_integrated_packet(integrated_packet)
    components = integrated_packet.get("component_packets", {})
    governance = integrated_packet.get("governance_decision", {})
    return {
        "packet_type": "p1_sandbox_packet_flow",
        "sandbox_only": True,
        "case_name": case_name,
        "source_refs": {
            "p0_stage_decision_ref": file_ref(P0_STAGE_DECISION_PATH),
            "p0_decision_manifest_ref": file_ref(P0_DECISION_RUN / "MANIFEST.json"),
            "integrated_p0_manifest_ref": file_ref(INTEGRATED_P0_RUN / "MANIFEST.json"),
            "source_seal_ref": file_ref(SEAL_DIR / "MANIFEST.json"),
            "candidate_ref": file_ref(CANDIDATE_PATH),
            "module_1_state_field_packet_runtime_ref": file_ref(STATE_FIELD_PACKET_RUN / "MANIFEST.json"),
            "module_2_accountable_record_chain_ref": file_ref(ACCOUNTABLE_CHAIN_RUN / "MANIFEST.json"),
            "module_3_front_edge_proxy_blocking_ref": file_ref(FRONT_EDGE_RUN / "MANIFEST.json"),
            "module_4_sovereign_identity_agent_ref": file_ref(IDENTITY_RUN / "MANIFEST.json"),
        },
        "p0_stage_decision": parse_stage_decision(),
        "p1_scope": {
            "allowed": [
                "sandbox_schema",
                "sandbox_cli_entry",
                "verifier_chain",
                "dry_run_test",
                "sandbox_packet_flow_report",
                "sandbox_manifest",
            ],
            "forbidden": [
                "production_db_model_activation",
                "odoo_production_controller_write",
                "deploy",
                "restart",
                "router_write",
                "credential_material_output",
                "member_plaintext_output",
                "h64_td_internal_detail_disclosure",
                "adi_actual_index_rule_disclosure",
                "cloud_candidate_final_decision",
                "auto_landing",
            ],
        },
        "flow_steps": build_flow_steps(integrated_packet, integrated_verifier),
        "component_packets": components,
        "integrated_packet": integrated_packet,
        "integrated_verifier": integrated_verifier,
        "p1_decision": {
            "total_field_only_decision_authority": True,
            "cloud_candidate_decision": False,
            "decision": governance.get("decision", "HOLD"),
            "reasons": governance.get("reasons", []),
            "restricted_execution_instruction_ref": governance.get("restricted_execution_instruction_ref", ""),
            "result_packet_ref": governance.get("result_packet_ref", ""),
            "accountable_record_ref": governance.get("accountable_record_ref", ""),
        },
        "technical_means": merge_technical_means(integrated_packet),
        "safety_boundary": {
            "production_system_connected": False,
            "production_member_db_connected": False,
            "production_adapter_connected": False,
            "db_write": False,
            "deploy": False,
            "restart": False,
            "router_write": False,
            "auto_landing": False,
            "cloud_call_executed": False,
            "no_secret": True,
            "no_member_plaintext": True,
            "h64_td_ref_only": True,
        },
    }


def verify_p1_packet_flow(packet: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    text = json.dumps(packet, ensure_ascii=False, sort_keys=True)

    if packet.get("packet_type") != "p1_sandbox_packet_flow":
        errors.append("P1_PACKET_FLOW_CHECK_FAIL:PACKET_TYPE")
    if packet.get("sandbox_only") is not True:
        errors.append("P1_PACKET_FLOW_CHECK_FAIL:NOT_SANDBOX_ONLY")

    decision_state = packet.get("p0_stage_decision", {})
    if decision_state.get("P1_ALLOWED") is not True:
        errors.append("P1_PACKET_FLOW_CHECK_FAIL:P0_P1_NOT_ALLOWED")
    for key in ["ALLOW_PRODUCTION", "ALLOW_DB_WRITE", "ALLOW_DEPLOY", "ALLOW_RESTART"]:
        if decision_state.get(key) is not False:
            errors.append(f"P1_PACKET_FLOW_CHECK_FAIL:{key}_NOT_FALSE")

    flow_steps = packet.get("flow_steps", [])
    actual_order = [step.get("step") for step in flow_steps]
    if actual_order != FLOW_ORDER:
        errors.append("P1_PACKET_FLOW_CHECK_FAIL:FLOW_ORDER")
    if any(step.get("status") in ("", None, "UNKNOWN", "FAIL") for step in flow_steps):
        errors.append("P1_PACKET_FLOW_CHECK_FAIL:FLOW_STEP_STATUS")

    components = packet.get("component_packets", {})
    identity_result = verify_identity_packet(components.get("sovereign_identity_agent", {}))
    state_result = verify_packet(components.get("state_field_packet_runtime", {}))
    front_result = verify_proxy_packet(components.get("front_edge_proxy_blocking", {}))
    chain_result = verify_chain(components.get("accountable_record_chain", {}))
    integrated_result = verify_integrated_packet(packet.get("integrated_packet", {}))

    if identity_result["DRY_RUN"] != "PASS":
        errors.append("SOVEREIGN_IDENTITY_AGENT_CHECK_FAIL")
    if state_result["DRY_RUN"] != "PASS":
        errors.append("STATE_FIELD_PACKET_RUNTIME_CHECK_FAIL")
    if front_result["DRY_RUN"] != "PASS":
        errors.append("FRONT_EDGE_BLOCKING_CHECK_FAIL")
    if chain_result["DRY_RUN"] != "PASS":
        errors.append("ACCOUNTABLE_RECORD_CHAIN_CHECK_FAIL")
    if integrated_result["DRY_RUN"] != "PASS":
        errors.append("INTEGRATED_VERIFIER_CHECK_FAIL")

    front_decision = components.get("front_edge_proxy_blocking", {}).get("proxy_decision", {})
    if front_decision.get("executable_api_call_generated") is not False:
        errors.append("FRONT_EDGE_BLOCKING_CHECK_FAIL:EXECUTABLE_API_CALL_GENERATED")
    if front_decision.get("business_write_forwarded") is not False:
        errors.append("FRONT_EDGE_BLOCKING_CHECK_FAIL:BUSINESS_WRITE_FORWARDED")

    p1_decision = packet.get("p1_decision", {})
    if p1_decision.get("total_field_only_decision_authority") is not True or p1_decision.get("cloud_candidate_decision") is not False:
        errors.append("CLOUD_AUTHORITY_CHECK_FAIL:AUTHORITY_DRIFT")
    expected_decision = EXPECTED_P1_DECISIONS.get(packet.get("case_name"))
    if expected_decision and p1_decision.get("decision") != expected_decision:
        errors.append("P1_PACKET_FLOW_CHECK_FAIL:UNEXPECTED_DECISION")

    candidate_verification = packet.get("integrated_packet", {}).get("candidate_verification", {})
    if candidate_verification.get("decision") != "PASS":
        errors.append("P1_PACKET_FLOW_CHECK_FAIL:CLOUD_CANDIDATE_NOT_REF_ONLY_PASS")
    for key in ["db_write", "deploy", "restart", "cloud_call_executed"]:
        if candidate_verification.get(key) is not False:
            errors.append(f"CLOUD_AUTHORITY_CHECK_FAIL:CANDIDATE_{key.upper()}")

    technical = packet.get("technical_means", {})
    for key in TECHNICAL_MEANS_KEYS:
        if not isinstance(technical.get(key), list) or not technical.get(key):
            errors.append(f"TECHNICAL_MEANS_CHECK_FAIL:{key}")

    if "多個狀態場" not in text and "多狀態場" not in text:
        errors.append("FIELD_DRIFT_CHECK_FAIL:MISSING_MULTI_STATE_CONTEXT")
    if "時空狀態索引資料庫" not in text:
        errors.append("ADI_CHECK_FAIL:MISSING_SPACETIME_INDEX_GENERIC_NAME")
    if ("政府" + "ADI") in text:
        errors.append("ADI_CHECK_FAIL:GOVERNMENT_ADI_DRIFT")

    scan = scan_text(text)
    if scan["status"] != "PASS":
        errors.append("NO_SECRET_FAIL")

    member_scan_text = text
    for safe in [
        "no_member_plaintext",
        "NO_MEMBER_PLAINTEXT",
        "member_plaintext_output",
        "identifiable_plaintext_blocked",
        "identifiable_plaintext_detected",
        "identifiable_plaintext_risk",
        "contains_identifiable_plaintext_risk",
        "member_plaintext_read",
    ]:
        member_scan_text = member_scan_text.replace(safe, "")
    if re.search(r"(?<![A-Za-z0-9])[A-Z][12]\d{8}(?![A-Za-z0-9])", member_scan_text):
        errors.append("NO_MEMBER_PLAINTEXT_FAIL")

    marker = "H64" + "-TD"
    protected_terms = ["map" + "ping", "ta" + "ble", "ru" + "les", "code" + "book"]
    if marker in text and any(term in text for term in protected_terms):
        errors.append("H64_TD_REF_ONLY_FAIL")

    boundary = packet.get("safety_boundary", {})
    for key in [
        "production_system_connected",
        "production_member_db_connected",
        "production_adapter_connected",
        "db_write",
        "deploy",
        "restart",
        "router_write",
        "auto_landing",
        "cloud_call_executed",
    ]:
        if boundary.get(key) is not False:
            errors.append(f"SAFETY_BOUNDARY_FAIL:{key}")

    return {
        "JSON_PARSE": "PASS",
        "P1_PACKET_FLOW_CHECK": "PASS" if not any(e.startswith("P1_PACKET_FLOW_CHECK_FAIL") for e in errors) else "FAIL",
        "SOVEREIGN_IDENTITY_AGENT_CHECK": "PASS" if not any(e.startswith("SOVEREIGN_IDENTITY_AGENT_CHECK_FAIL") for e in errors) else "FAIL",
        "STATE_FIELD_PACKET_RUNTIME_CHECK": "PASS" if not any(e.startswith("STATE_FIELD_PACKET_RUNTIME_CHECK_FAIL") for e in errors) else "FAIL",
        "FRONT_EDGE_BLOCKING_CHECK": "PASS" if not any(e.startswith("FRONT_EDGE_BLOCKING_CHECK_FAIL") for e in errors) else "FAIL",
        "ACCOUNTABLE_RECORD_CHAIN_CHECK": "PASS" if not any(e.startswith("ACCOUNTABLE_RECORD_CHAIN_CHECK_FAIL") for e in errors) else "FAIL",
        "INTEGRATED_VERIFIER_CHECK": "PASS" if not any(e.startswith("INTEGRATED_VERIFIER_CHECK_FAIL") for e in errors) else "FAIL",
        "CLOUD_AUTHORITY_CHECK": "PASS" if not any(e.startswith("CLOUD_AUTHORITY_CHECK_FAIL") for e in errors) else "FAIL",
        "FIELD_DRIFT_CHECK": "PASS" if not any(e.startswith("FIELD_DRIFT_CHECK_FAIL") for e in errors) else "FAIL",
        "ADI_CHECK": "PASS" if not any(e.startswith("ADI_CHECK_FAIL") for e in errors) else "FAIL",
        "TECHNICAL_MEANS_CHECK": "PASS" if not any(e.startswith("TECHNICAL_MEANS_CHECK_FAIL") for e in errors) else "FAIL",
        "NO_SECRET": "PASS" if "NO_SECRET_FAIL" not in errors else "FAIL",
        "NO_MEMBER_PLAINTEXT": "PASS" if "NO_MEMBER_PLAINTEXT_FAIL" not in errors else "FAIL",
        "H64_TD_REF_ONLY": "PASS" if "H64_TD_REF_ONLY_FAIL" not in errors else "FAIL",
        "DB_WRITE": False,
        "DEPLOY": False,
        "RESTART": False,
        "DRY_RUN": "PASS" if not errors else "FAIL",
        "ERRORS": errors,
    }


def build_test_cases() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for integrated_case in build_integrated_test_cases():
        p1_name = CASE_NAME_MAP[integrated_case["name"]]
        packet = build_p1_packet(
            case_name=p1_name,
            integrated_packet=integrated_case["packet"],
            integrated_verifier=integrated_case["verifier"],
        )
        verifier = verify_p1_packet_flow(packet)
        expected = EXPECTED_P1_DECISIONS[p1_name]
        actual = packet.get("p1_decision", {}).get("decision")
        passed = integrated_case["passed"] and verifier["DRY_RUN"] == "PASS" and actual == expected
        results.append(
            {
                "name": p1_name,
                "expected_decision": expected,
                "actual_decision": actual,
                "passed": passed,
                "verifier": verifier,
                "packet": packet,
            }
        )
    return results


def write_sandbox_run(out_root: Path = P1_SANDBOX_ROOT) -> dict[str, Any]:
    run_id = "P1_SANDBOX_PACKET_FLOW_" + now_utc()
    out = out_root / run_id
    out.mkdir(parents=True, exist_ok=True)

    packet = build_p1_packet()
    verifier = verify_p1_packet_flow(packet)
    tests = build_test_cases()
    all_tests_passed = all(item["passed"] for item in tests)
    dry_run_pass = verifier["DRY_RUN"] == "PASS" and all_tests_passed

    write_text(
        out / "00_SOURCE_STATE.md",
        f"""# P1 Sandbox Packet Flow

STATE=P1_SANDBOX_PACKET_FLOW
RUN_ID={run_id}
P0_DECISION={rel(P0_DECISION_RUN)}
P0_INTEGRATED={rel(INTEGRATED_P0_RUN)}
MODULE_1={rel(STATE_FIELD_PACKET_RUN)}
MODULE_2={rel(ACCOUNTABLE_CHAIN_RUN)}
MODULE_3={rel(FRONT_EDGE_RUN)}
MODULE_4={rel(IDENTITY_RUN)}
SOURCE_SEAL={rel(SEAL_DIR)}
SOURCE_CANDIDATE={rel(CANDIDATE_PATH)}

## Boundary

- sandbox_only=true
- production_system_connected=false
- production_member_db_connected=false
- db_write=false
- deploy=false
- restart=false
- router_write=false
- auto_landing=false
- cloud_call_executed=false
- total_field_only_decision_authority=true
""",
    )
    write_json(out / "01_P1_SANDBOX_PACKET_FLOW.json", packet)
    write_json(out / "02_TEST_CASES.json", tests)
    write_json(out / "03_VERIFIER_RESULTS.json", verifier)

    rows = ["| case | expected | actual | result |", "|---|---|---|---|"]
    for item in tests:
        rows.append(f"| {item['name']} | {item['expected_decision']} | {item['actual_decision']} | {'PASS' if item['passed'] else 'FAIL'} |")
    report_lines = [
        "# P1 Sandbox Packet Flow Verifier Report",
        "",
        "STATE=P1_SANDBOX_PACKET_FLOW_REPORT",
        f"RUN_ID={run_id}",
        "JSON_PARSE=PASS",
        f"DRY_RUN={'PASS' if dry_run_pass else 'FAIL'}",
        f"P1_PACKET_FLOW_CHECK={verifier['P1_PACKET_FLOW_CHECK']}",
        f"SOVEREIGN_IDENTITY_AGENT_CHECK={verifier['SOVEREIGN_IDENTITY_AGENT_CHECK']}",
        f"STATE_FIELD_PACKET_RUNTIME_CHECK={verifier['STATE_FIELD_PACKET_RUNTIME_CHECK']}",
        f"FRONT_EDGE_BLOCKING_CHECK={verifier['FRONT_EDGE_BLOCKING_CHECK']}",
        f"ACCOUNTABLE_RECORD_CHAIN_CHECK={verifier['ACCOUNTABLE_RECORD_CHAIN_CHECK']}",
        f"INTEGRATED_VERIFIER_CHECK={verifier['INTEGRATED_VERIFIER_CHECK']}",
        f"CLOUD_AUTHORITY_CHECK={verifier['CLOUD_AUTHORITY_CHECK']}",
        f"FIELD_DRIFT_CHECK={verifier['FIELD_DRIFT_CHECK']}",
        f"ADI_CHECK={verifier['ADI_CHECK']}",
        f"TECHNICAL_MEANS_CHECK={verifier['TECHNICAL_MEANS_CHECK']}",
        f"NO_SECRET={verifier['NO_SECRET']}",
        f"NO_MEMBER_PLAINTEXT={verifier['NO_MEMBER_PLAINTEXT']}",
        f"H64_TD_REF_ONLY={verifier['H64_TD_REF_ONLY']}",
        "DB_WRITE=false",
        "DEPLOY=false",
        "RESTART=false",
        "ERRORS=" + ("NONE" if dry_run_pass else "TEST_OR_VERIFIER_FAILURE"),
        "",
        "## Test Cases",
        "",
        "\n".join(rows),
        "",
    ]
    write_text(out / "VERIFIER_REPORT.md", "\n".join(report_lines))

    manifest = {
        "run_id": run_id,
        "created_at_utc": iso_now(),
        "p0_decision": rel(P0_DECISION_RUN),
        "p0_integrated": rel(INTEGRATED_P0_RUN),
        "module_1": rel(STATE_FIELD_PACKET_RUN),
        "module_2": rel(ACCOUNTABLE_CHAIN_RUN),
        "module_3": rel(FRONT_EDGE_RUN),
        "module_4": rel(IDENTITY_RUN),
        "source_seal": rel(SEAL_DIR),
        "source_candidate": rel(CANDIDATE_PATH),
        "safety_flags": {
            "sandbox_only": True,
            "production_system_connected": False,
            "production_member_db_connected": False,
            "db_write": False,
            "deploy": False,
            "restart": False,
            "router_write": False,
            "auto_landing": False,
            "cloud_call_executed": False,
            "no_secret": True,
            "no_member_plaintext": True,
            "h64_td_ref_only": True,
        },
        "files": {},
    }
    write_json(out / "MANIFEST.json", manifest)
    manifest["files"] = {
        path.name: sha256_file(path)
        for path in sorted(out.iterdir())
        if path.is_file() and path.name != "MANIFEST.json"
    }
    write_json(out / "MANIFEST.json", manifest)

    runtime_files_created = len([path for path in out.iterdir() if path.is_file()])
    static_files_present = len([path for path in STATIC_OUTPUT_FILES if path.exists()])
    return {
        "run_id": run_id,
        "out": rel(out),
        "files_created": runtime_files_created + static_files_present,
        "runtime_files_created": runtime_files_created,
        "dry_run": "PASS" if dry_run_pass else "FAIL",
        "verifier": verifier,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build P1 sandbox packet-flow output.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify", help="Verify a P1 sandbox packet-flow JSON file.")
    args = parser.parse_args()

    if args.verify:
        packet = json.loads(Path(args.verify).read_text(encoding="utf-8"))
        result = verify_p1_packet_flow(packet)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["DRY_RUN"] == "PASS" else 2

    if not args.dry_run:
        parser.error("Use --dry-run or --verify")

    summary = write_sandbox_run()
    print("STATE=" + ("PASS_P1_SANDBOX_PACKET_FLOW" if summary["dry_run"] == "PASS" else "HOLD_P1_SANDBOX_PACKET_FLOW"))
    print("RUN_ID=" + summary["run_id"])
    print("OUT=" + summary["out"])
    print("FILES_CREATED=" + str(summary["files_created"]))
    print("DRY_RUN=" + summary["dry_run"])
    return 0 if summary["dry_run"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
