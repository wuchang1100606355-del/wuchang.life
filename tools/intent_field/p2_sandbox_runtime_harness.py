#!/usr/bin/env python3
"""Sandbox-only P2 runtime harness for repeatable local verification."""

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

from p1_sandbox_packet_flow import (  # noqa: E402
    TECHNICAL_MEANS_KEYS,
    build_p1_packet,
    build_test_cases as build_p1_test_cases,
    verify_p1_packet_flow,
)
from redact_candidate_payload import scan_text  # noqa: E402


P1_STAGE_REVIEW_RUN = ROOT / "runtime/total_field/p1_sandbox_stage_review/P1_SANDBOX_STAGE_REVIEW_20260704T223218Z"
P1_STAGE_DECISION_PATH = P1_STAGE_REVIEW_RUN / "STAGE_DECISION.md"
P1_FLOW_RUN = ROOT / "runtime/total_field/p1_sandbox_packet_flow/P1_SANDBOX_PACKET_FLOW_20260704T222902Z"
CANDIDATE_SEAL_RUN = ROOT / "runtime/total_field/verified_cloud_candidate_seal/VERIFIED_CLOUD_CANDIDATE_SEAL_20260704T215322Z"
VERIFIED_CANDIDATE_PATH = CANDIDATE_SEAL_RUN / "RETURNED_CLOUD_CANDIDATE_RESPONSE.json"
RETURNED_CANDIDATE_PATH = ROOT / "runtime/total_field/owner_authorized_cloud_send/OWNER_AUTHORIZED_CLOUD_SEND_20260704T212136Z/RETURNED_CLOUD_CANDIDATE_RESPONSE.json"
P2_SANDBOX_ROOT = ROOT / "runtime/total_field/p2_sandbox_runtime_harness"

RUNTIME_CHAIN_ORDER = [
    "returned_cloud_candidate_load",
    "sandbox_fixture_load",
    "sovereign_identity_agent_check",
    "state_field_packet_runtime_check",
    "front_edge_proxy_blocking_check",
    "accountable_record_chain_check",
    "integrated_verifier_check",
    "sandbox_result_packet_emit",
    "runtime_harness_report_emit",
]
P1_TO_P2_CASE_NAME = {
    "PASS_P1_SANDBOX_FLOW": "PASS_P2_RUNTIME_FULL_CHAIN",
    "HOLD_MISSING_CONSENT": "HOLD_MISSING_CONSENT",
    "HOLD_MISSING_VERIFIER": "HOLD_MISSING_VERIFIER",
    "REJECT_DIRECT_BUSINESS_WRITE": "REJECT_DIRECT_BUSINESS_WRITE",
    "REJECT_MEMBER_PLAINTEXT": "REJECT_MEMBER_PLAINTEXT",
    "REJECT_SECRET": "REJECT_SECRET",
    "REJECT_FIELD_DRIFT": "REJECT_FIELD_DRIFT",
    "REJECT_ADI_DRIFT": "REJECT_ADI_DRIFT",
    "REJECT_CLOUD_AUTHORITY_DRIFT": "REJECT_CLOUD_AUTHORITY_DRIFT",
}
EXPECTED_P2_DECISIONS = {
    "PASS_P2_RUNTIME_FULL_CHAIN": "ALLOW_RESTRICTED",
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
    ROOT / "schemas/intent_field/p2_sandbox_runtime_harness.schema.json",
    ROOT / "tools/intent_field/p2_sandbox_runtime_harness.py",
    ROOT / "tools/intent_field/verify_p2_sandbox_runtime_harness.py",
    ROOT / "scripts/intent_field/run_p2_sandbox_runtime_harness.sh",
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


def parse_p1_stage_decision(path: Path = P1_STAGE_DECISION_PATH) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = parse_bool(value)
    return {
        "P1_EVIDENCE_SUMMARY": values.get("P1_EVIDENCE_SUMMARY"),
        "P1_REDTTEAM_DECISION": values.get("P1_REDTTEAM_DECISION"),
        "P2_ALLOWED": values.get("P2_ALLOWED") is True or values.get("ALLOW_P2_SANDBOX_RUNTIME_HARNESS") is True,
        "P2_SCOPE": values.get("P2_SCOPE"),
        "ALLOW_PRODUCTION": values.get("ALLOW_PRODUCTION", False),
        "ALLOW_DB_WRITE": values.get("ALLOW_DB_WRITE", False),
        "ALLOW_DEPLOY": values.get("ALLOW_DEPLOY", False),
        "ALLOW_RESTART": values.get("ALLOW_RESTART", False),
        "ALLOW_ROUTER_WRITE": values.get("ALLOW_ROUTER_WRITE", False),
        "NEXT": values.get("NEXT"),
    }


def build_runtime_fixture() -> dict[str, Any]:
    returned_hash = sha256_file(RETURNED_CANDIDATE_PATH)
    verified_hash = sha256_file(VERIFIED_CANDIDATE_PATH)
    return {
        "fixture_id": "p2_runtime_fixture:ref_only_candidate_local",
        "sandbox_only": True,
        "input_mode": "ref_only_fixture",
        "returned_cloud_candidate_ref": file_ref(RETURNED_CANDIDATE_PATH),
        "verified_candidate_ref": file_ref(VERIFIED_CANDIDATE_PATH),
        "candidate_hash_match": returned_hash == verified_hash,
        "p1_stage_review_ref": file_ref(P1_STAGE_REVIEW_RUN / "MANIFEST.json"),
        "p1_flow_ref": file_ref(P1_FLOW_RUN / "MANIFEST.json"),
        "production_connector": False,
        "db_write": False,
        "deploy": False,
        "restart": False,
        "router_write": False,
        "cloud_call_executed": False,
    }


def extend_technical_means(p1_packet: dict[str, Any]) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {key: [] for key in TECHNICAL_MEANS_KEYS}
    source = p1_packet.get("technical_means", {})
    for key in TECHNICAL_MEANS_KEYS:
        for item in source.get(key, []):
            if item not in merged[key]:
                merged[key].append(item)
    additions = {
        "modules": ["p2_sandbox_runtime_harness", "p2_local_cli_runner", "p2_verifier_chain_runner"],
        "data_structures": ["p2_runtime_fixture", "p2_runtime_result_packet", "p2_verifier_chain"],
        "packet_fields": ["runtime_fixture", "verifier_chain", "result_packet", "p1_stage_decision"],
        "verification_conditions": [
            "p1_stage_decision_p2_allowed_required",
            "candidate_fixture_hash_match_required",
            "p1_packet_flow_pass_required",
            "sandbox_result_packet_required",
            "no_production_connector_required",
        ],
        "blocking_conditions": [
            "p1_stage_not_allowed_for_p2",
            "candidate_fixture_hash_mismatch",
            "production_connector_requested",
            "runtime_result_boundary_drift",
        ],
        "record_fields": ["result_packet_id", "accountable_record_ref", "previous_record_hash", "current_record_hash"],
    }
    for key, items in additions.items():
        for item in items:
            if item not in merged[key]:
                merged[key].append(item)
    return merged


def build_result_packet(case_name: str, p1_packet: dict[str, Any], p1_verifier: dict[str, Any]) -> dict[str, Any]:
    p1_decision = p1_packet.get("p1_decision", {})
    front = p1_packet.get("component_packets", {}).get("front_edge_proxy_blocking", {}).get("proxy_decision", {})
    return {
        "result_packet_id": f"p2_result_packet:{case_name}",
        "sandbox_only": True,
        "case_name": case_name,
        "decision": p1_decision.get("decision", "HOLD"),
        "reasons": p1_decision.get("reasons", []),
        "total_field_only_decision_authority": True,
        "cloud_candidate_decision": False,
        "restricted_execution_instruction_ref": p1_decision.get("restricted_execution_instruction_ref", ""),
        "result_packet_ref": p1_decision.get("result_packet_ref", "result_packet_ref:p2_sandbox_only"),
        "accountable_record_ref": p1_decision.get("accountable_record_ref", ""),
        "p1_verifier_dry_run": p1_verifier.get("DRY_RUN"),
        "executable_api_call_generated": False,
        "business_write_forwarded": False,
        "front_edge_executable_api_call_generated": front.get("executable_api_call_generated", False),
        "front_edge_business_write_forwarded": front.get("business_write_forwarded", False),
        "production_connector": False,
        "db_write": False,
        "deploy": False,
        "restart": False,
        "router_write": False,
        "auto_landing": False,
        "cloud_call_executed": False,
    }


def build_verifier_chain(p1_packet: dict[str, Any], p1_verifier: dict[str, Any], fixture: dict[str, Any]) -> list[dict[str, Any]]:
    result = build_result_packet(str(p1_packet.get("case_name", "P2_CASE")), p1_packet, p1_verifier)
    return [
        {"order": 1, "step": "returned_cloud_candidate_load", "status": "PASS" if fixture.get("candidate_hash_match") else "FAIL"},
        {"order": 2, "step": "sandbox_fixture_load", "status": "PASS" if fixture.get("sandbox_only") is True else "FAIL"},
        {"order": 3, "step": "sovereign_identity_agent_check", "status": p1_verifier.get("SOVEREIGN_IDENTITY_AGENT_CHECK", "UNKNOWN")},
        {"order": 4, "step": "state_field_packet_runtime_check", "status": p1_verifier.get("STATE_FIELD_PACKET_RUNTIME_CHECK", "UNKNOWN")},
        {"order": 5, "step": "front_edge_proxy_blocking_check", "status": p1_verifier.get("FRONT_EDGE_BLOCKING_CHECK", "UNKNOWN")},
        {"order": 6, "step": "accountable_record_chain_check", "status": p1_verifier.get("ACCOUNTABLE_RECORD_CHAIN_CHECK", "UNKNOWN")},
        {"order": 7, "step": "integrated_verifier_check", "status": p1_verifier.get("INTEGRATED_VERIFIER_CHECK", "UNKNOWN")},
        {"order": 8, "step": "sandbox_result_packet_emit", "status": "PASS" if result.get("sandbox_only") is True else "FAIL"},
        {"order": 9, "step": "runtime_harness_report_emit", "status": "PASS"},
    ]


def build_p2_packet(
    case_name: str = "PASS_P2_RUNTIME_FULL_CHAIN",
    p1_packet: dict[str, Any] | None = None,
    p1_verifier: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if p1_packet is None:
        p1_packet = build_p1_packet("PASS_P1_SANDBOX_FLOW")
    if p1_verifier is None:
        p1_verifier = verify_p1_packet_flow(p1_packet)
    fixture = build_runtime_fixture()
    result_packet = build_result_packet(case_name, p1_packet, p1_verifier)
    return {
        "packet_type": "p2_sandbox_runtime_harness",
        "sandbox_only": True,
        "case_name": case_name,
        "source_refs": {
            "p1_stage_review_ref": file_ref(P1_STAGE_REVIEW_RUN / "MANIFEST.json"),
            "p1_stage_decision_ref": file_ref(P1_STAGE_DECISION_PATH),
            "p1_flow_ref": file_ref(P1_FLOW_RUN / "MANIFEST.json"),
            "candidate_seal_ref": file_ref(CANDIDATE_SEAL_RUN / "MANIFEST.json"),
            "returned_candidate_ref": file_ref(RETURNED_CANDIDATE_PATH),
            "verified_candidate_ref": file_ref(VERIFIED_CANDIDATE_PATH),
        },
        "p1_stage_decision": parse_p1_stage_decision(),
        "runtime_fixture": fixture,
        "verifier_chain": build_verifier_chain(p1_packet, p1_verifier, fixture),
        "result_packet": result_packet,
        "p1_packet_flow": p1_packet,
        "p1_verifier": p1_verifier,
        "technical_means": extend_technical_means(p1_packet),
        "safety_boundary": {
            "sandbox_only": True,
            "production_connector": False,
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


def verify_p2_runtime_harness(packet: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    text = json.dumps(packet, ensure_ascii=False, sort_keys=True)

    if packet.get("packet_type") != "p2_sandbox_runtime_harness":
        errors.append("P2_RUNTIME_HARNESS_CHECK_FAIL:PACKET_TYPE")
    if packet.get("sandbox_only") is not True:
        errors.append("P2_RUNTIME_HARNESS_CHECK_FAIL:NOT_SANDBOX_ONLY")

    stage_decision = packet.get("p1_stage_decision", {})
    if stage_decision.get("P2_ALLOWED") is not True:
        errors.append("P2_RUNTIME_HARNESS_CHECK_FAIL:P2_NOT_ALLOWED")
    for key in ["ALLOW_PRODUCTION", "ALLOW_DB_WRITE", "ALLOW_DEPLOY", "ALLOW_RESTART", "ALLOW_ROUTER_WRITE"]:
        if stage_decision.get(key) is not False:
            errors.append(f"P2_RUNTIME_HARNESS_CHECK_FAIL:{key}_NOT_FALSE")

    fixture = packet.get("runtime_fixture", {})
    if fixture.get("sandbox_only") is not True:
        errors.append("P2_RUNTIME_HARNESS_CHECK_FAIL:FIXTURE_NOT_SANDBOX")
    if fixture.get("candidate_hash_match") is not True:
        errors.append("P2_RUNTIME_HARNESS_CHECK_FAIL:CANDIDATE_HASH_MISMATCH")
    if fixture.get("production_connector") is not False:
        errors.append("P2_RUNTIME_HARNESS_CHECK_FAIL:FIXTURE_PRODUCTION_CONNECTOR")

    p1_result = verify_p1_packet_flow(packet.get("p1_packet_flow", {}))
    if p1_result.get("DRY_RUN") != "PASS":
        errors.append("VERIFIER_CHAIN_CHECK_FAIL:P1_PACKET_FLOW")

    chain = packet.get("verifier_chain", [])
    actual_order = [step.get("step") for step in chain]
    if actual_order != RUNTIME_CHAIN_ORDER:
        errors.append("VERIFIER_CHAIN_CHECK_FAIL:ORDER")
    if any(step.get("status") in ("", None, "UNKNOWN", "FAIL") for step in chain):
        errors.append("VERIFIER_CHAIN_CHECK_FAIL:STEP_STATUS")

    p1_verifier = packet.get("p1_verifier", {})
    for key in [
        "SOVEREIGN_IDENTITY_AGENT_CHECK",
        "STATE_FIELD_PACKET_RUNTIME_CHECK",
        "FRONT_EDGE_BLOCKING_CHECK",
        "ACCOUNTABLE_RECORD_CHAIN_CHECK",
        "INTEGRATED_VERIFIER_CHECK",
        "FIELD_DRIFT_CHECK",
        "ADI_CHECK",
        "TECHNICAL_MEANS_CHECK",
        "NO_SECRET",
        "NO_MEMBER_PLAINTEXT",
        "H64_TD_REF_ONLY",
    ]:
        if p1_verifier.get(key) != "PASS":
            errors.append(f"{key}_FAIL")

    result = packet.get("result_packet", {})
    if result.get("sandbox_only") is not True:
        errors.append("P2_RUNTIME_HARNESS_CHECK_FAIL:RESULT_NOT_SANDBOX")
    if result.get("total_field_only_decision_authority") is not True or result.get("cloud_candidate_decision") is not False:
        errors.append("CLOUD_AUTHORITY_CHECK_FAIL:AUTHORITY_DRIFT")
    expected_decision = EXPECTED_P2_DECISIONS.get(packet.get("case_name"))
    if expected_decision and result.get("decision") != expected_decision:
        errors.append("P2_RUNTIME_HARNESS_CHECK_FAIL:UNEXPECTED_DECISION")
    for key in [
        "executable_api_call_generated",
        "business_write_forwarded",
        "front_edge_executable_api_call_generated",
        "front_edge_business_write_forwarded",
        "production_connector",
        "db_write",
        "deploy",
        "restart",
        "router_write",
        "auto_landing",
        "cloud_call_executed",
    ]:
        if result.get(key) is not False:
            errors.append(f"P2_RUNTIME_HARNESS_CHECK_FAIL:RESULT_{key}")

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
        "production_connector",
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
        "P2_RUNTIME_HARNESS_CHECK": "PASS" if not any(e.startswith("P2_RUNTIME_HARNESS_CHECK_FAIL") for e in errors) else "FAIL",
        "VERIFIER_CHAIN_CHECK": "PASS" if not any(e.startswith("VERIFIER_CHAIN_CHECK_FAIL") for e in errors) else "FAIL",
        "SOVEREIGN_IDENTITY_AGENT_CHECK": "PASS" if "SOVEREIGN_IDENTITY_AGENT_CHECK_FAIL" not in errors else "FAIL",
        "STATE_FIELD_PACKET_RUNTIME_CHECK": "PASS" if "STATE_FIELD_PACKET_RUNTIME_CHECK_FAIL" not in errors else "FAIL",
        "FRONT_EDGE_BLOCKING_CHECK": "PASS" if "FRONT_EDGE_BLOCKING_CHECK_FAIL" not in errors else "FAIL",
        "ACCOUNTABLE_RECORD_CHAIN_CHECK": "PASS" if "ACCOUNTABLE_RECORD_CHAIN_CHECK_FAIL" not in errors else "FAIL",
        "INTEGRATED_VERIFIER_CHECK": "PASS" if "INTEGRATED_VERIFIER_CHECK_FAIL" not in errors else "FAIL",
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
    cases: list[dict[str, Any]] = []
    for p1_case in build_p1_test_cases():
        p2_name = P1_TO_P2_CASE_NAME[p1_case["name"]]
        packet = build_p2_packet(p2_name, p1_case["packet"], p1_case["verifier"])
        verifier = verify_p2_runtime_harness(packet)
        expected = EXPECTED_P2_DECISIONS[p2_name]
        actual = packet.get("result_packet", {}).get("decision")
        passed = p1_case["passed"] and verifier["DRY_RUN"] == "PASS" and actual == expected
        cases.append(
            {
                "name": p2_name,
                "expected_decision": expected,
                "actual_decision": actual,
                "passed": passed,
                "verifier": verifier,
                "packet": packet,
            }
        )
    return cases


def write_sandbox_run(out_root: Path = P2_SANDBOX_ROOT) -> dict[str, Any]:
    run_id = "P2_SANDBOX_RUNTIME_HARNESS_" + now_utc()
    out = out_root / run_id
    out.mkdir(parents=True, exist_ok=True)

    packet = build_p2_packet()
    verifier = verify_p2_runtime_harness(packet)
    tests = build_test_cases()
    all_tests_passed = all(item["passed"] for item in tests)
    dry_run_pass = verifier["DRY_RUN"] == "PASS" and all_tests_passed

    write_text(
        out / "00_P2_RUNTIME_HARNESS_DESIGN.md",
        f"""# P2 Sandbox Runtime Harness Design

STATE=P2_SANDBOX_RUNTIME_HARNESS_DESIGN
RUN_ID={run_id}
P1_STAGE_REVIEW={rel(P1_STAGE_REVIEW_RUN)}
P1_FLOW={rel(P1_FLOW_RUN)}
CANDIDATE_SEAL={rel(CANDIDATE_SEAL_RUN)}
RETURNED_CANDIDATE={rel(RETURNED_CANDIDATE_PATH)}

## Boundary

- sandbox_only=true
- production_connector=false
- db_write=false
- deploy=false
- restart=false
- router_write=false
- auto_landing=false
- cloud_call_executed=false

## Runtime Chain

1. load ref-only returned candidate fixture
2. load sandbox fixture
3. run sovereign identity agent check
4. run multi-state packet runtime check
5. run front-edge proxy blocking check
6. run accountable record-chain check
7. run integrated verifier
8. emit sandbox-only result packet
9. emit runtime harness report
""",
    )
    write_json(out / "01_P2_RUNTIME_FIXTURE.json", packet["runtime_fixture"])
    write_json(out / "02_P2_RUNTIME_RESULT_PACKET.json", packet)

    chain_rows = ["| order | step | status |", "|---|---|---|"]
    for step in packet["verifier_chain"]:
        chain_rows.append(f"| {step['order']} | {step['step']} | {step['status']} |")
    write_text(
        out / "03_P2_VERIFIER_CHAIN_REPORT.md",
        "\n".join(
            [
                "# P2 Verifier Chain Report",
                "",
                "STATE=P2_VERIFIER_CHAIN_REPORT",
                f"RUN_ID={run_id}",
                f"VERIFIER_CHAIN_CHECK={verifier['VERIFIER_CHAIN_CHECK']}",
                "",
                "\n".join(chain_rows),
                "",
            ]
        ),
    )

    test_rows = ["| case | expected | actual | result |", "|---|---|---|---|"]
    for item in tests:
        test_rows.append(f"| {item['name']} | {item['expected_decision']} | {item['actual_decision']} | {'PASS' if item['passed'] else 'FAIL'} |")
    write_text(
        out / "04_P2_REDTTEAM_FAILURE_CASES.md",
        "\n".join(
            [
                "# P2 Redteam Failure Cases",
                "",
                "STATE=P2_REDTTEAM_FAILURE_CASES",
                f"RUN_ID={run_id}",
                "",
                "All failure cases use sandbox risk flags and expected blocking outcomes only.",
                "",
                "\n".join(test_rows),
                "",
            ]
        ),
    )
    write_text(
        out / "05_P2_NEXT_STAGE_DECISION_INPUT.md",
        f"""# P2 Next Stage Decision Input

STATE=P2_NEXT_STAGE_DECISION_INPUT
RUN_ID={run_id}
P2_RUNTIME_HARNESS_CHECK={verifier['P2_RUNTIME_HARNESS_CHECK']}
VERIFIER_CHAIN_CHECK={verifier['VERIFIER_CHAIN_CHECK']}
DRY_RUN={'PASS' if dry_run_pass else 'FAIL'}
TEST_CASES_TOTAL={len(tests)}
TEST_CASES_PASS={sum(1 for item in tests if item['passed'])}
DB_WRITE=false
DEPLOY=false
RESTART=false

NEXT={'START_P2_SANDBOX_STAGE_REVIEW' if dry_run_pass else 'REPAIR_P2_SANDBOX_RUNTIME_HARNESS'}
""",
    )

    report_lines = [
        "# P2 Sandbox Runtime Harness Verifier Report",
        "",
        "STATE=P2_SANDBOX_RUNTIME_HARNESS_REPORT",
        f"RUN_ID={run_id}",
        "JSON_PARSE=PASS",
        f"DRY_RUN={'PASS' if dry_run_pass else 'FAIL'}",
        f"P2_RUNTIME_HARNESS_CHECK={verifier['P2_RUNTIME_HARNESS_CHECK']}",
        f"VERIFIER_CHAIN_CHECK={verifier['VERIFIER_CHAIN_CHECK']}",
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
        "\n".join(test_rows),
        "",
    ]
    write_text(out / "VERIFIER_REPORT.md", "\n".join(report_lines))

    manifest = {
        "run_id": run_id,
        "created_at_utc": iso_now(),
        "p1_stage_review": rel(P1_STAGE_REVIEW_RUN),
        "p1_flow": rel(P1_FLOW_RUN),
        "candidate_seal": rel(CANDIDATE_SEAL_RUN),
        "returned_candidate": rel(RETURNED_CANDIDATE_PATH),
        "safety_flags": {
            "sandbox_only": True,
            "production_connector": False,
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
        "evidence": {
            "p2_runtime_harness_check": verifier["P2_RUNTIME_HARNESS_CHECK"],
            "verifier_chain_check": verifier["VERIFIER_CHAIN_CHECK"],
            "dry_run": "PASS" if dry_run_pass else "FAIL",
            "test_cases_total": len(tests),
            "test_cases_pass": sum(1 for item in tests if item["passed"]),
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
    parser = argparse.ArgumentParser(description="Build P2 sandbox runtime harness output.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify", help="Verify a P2 sandbox runtime harness JSON file.")
    args = parser.parse_args()

    if args.verify:
        packet = json.loads(Path(args.verify).read_text(encoding="utf-8"))
        result = verify_p2_runtime_harness(packet)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["DRY_RUN"] == "PASS" else 2

    if not args.dry_run:
        parser.error("Use --dry-run or --verify")

    summary = write_sandbox_run()
    print("STATE=" + ("PASS_P2_SANDBOX_RUNTIME_HARNESS" if summary["dry_run"] == "PASS" else "HOLD_P2_SANDBOX_RUNTIME_HARNESS"))
    print("RUN_ID=" + summary["run_id"])
    print("OUT=" + summary["out"])
    print("FILES_CREATED=" + str(summary["files_created"]))
    print("DRY_RUN=" + summary["dry_run"])
    return 0 if summary["dry_run"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
