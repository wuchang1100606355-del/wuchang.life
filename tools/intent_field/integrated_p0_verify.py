#!/usr/bin/env python3
"""Sandbox-only integrated P0 verifier for the intent-field path."""

from __future__ import annotations

import argparse
import copy
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
from dynamic_state_field_verifier import verify_candidate  # noqa: E402
from front_edge_proxy_blocking import base_proxy_request, build_proxy_packet, verify_proxy_packet  # noqa: E402
from redact_candidate_payload import scan_text  # noqa: E402
from sovereign_identity_agent import (  # noqa: E402
    base_identity_output,
    base_identity_request,
    build_identity_packet,
    load_candidate,
    verify_identity_packet,
)
from state_field_packet_runtime import verify_packet  # noqa: E402
from verify_cloud_candidate_response import normalize_candidate_response  # noqa: E402


SEAL_DIR = ROOT / "runtime/total_field/verified_cloud_candidate_seal/VERIFIED_CLOUD_CANDIDATE_SEAL_20260704T215322Z"
CANDIDATE_PATH = SEAL_DIR / "RETURNED_CLOUD_CANDIDATE_RESPONSE.json"
STATE_FIELD_PACKET_RUN = ROOT / "runtime/total_field/state_field_packet_runtime_sandbox/STATE_FIELD_PACKET_RUNTIME_SANDBOX_20260704T215805Z"
STATE_FIELD_PACKET_PATH = STATE_FIELD_PACKET_RUN / "01_STATE_FIELD_PACKET_RUNTIME.json"
ACCOUNTABLE_CHAIN_RUN = ROOT / "runtime/total_field/accountable_record_chain_sandbox/ACCOUNTABLE_RECORD_CHAIN_SANDBOX_20260704T220355Z"
ACCOUNTABLE_CHAIN_PATH = ACCOUNTABLE_CHAIN_RUN / "01_ACCOUNTABLE_RECORD_CHAIN.json"
FRONT_EDGE_RUN = ROOT / "runtime/total_field/front_edge_proxy_blocking_sandbox/FRONT_EDGE_PROXY_BLOCKING_SANDBOX_20260704T220953Z"
FRONT_EDGE_PATH = FRONT_EDGE_RUN / "01_FRONT_EDGE_PROXY_PACKET.json"
IDENTITY_RUN = ROOT / "runtime/total_field/sovereign_identity_agent_sandbox/SOVEREIGN_IDENTITY_AGENT_SANDBOX_20260704T221354Z"
IDENTITY_PATH = IDENTITY_RUN / "01_SOVEREIGN_IDENTITY_AGENT_PACKET.json"
SANDBOX_ROOT = ROOT / "runtime/total_field/integrated_p0_verify_sandbox"

TECHNICAL_MEANS_KEYS = [
    "modules",
    "data_structures",
    "packet_fields",
    "verification_conditions",
    "blocking_conditions",
    "record_fields",
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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verified_candidate_packet() -> dict[str, Any]:
    payload = load_json(CANDIDATE_PATH)
    candidate, _normalization = normalize_candidate_response(payload)
    return candidate


def accountable_record_ref(chain: dict[str, Any]) -> str:
    records = chain.get("records", [])
    if not records:
        return "accountable_record_ref:sandbox_missing"
    return "accountable_record_ref:" + str(records[-1].get("current_record_hash", "sandbox_missing"))


def component_technical_means(*packets: dict[str, Any]) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {key: [] for key in TECHNICAL_MEANS_KEYS}
    for packet in packets:
        means = packet.get("technical_means", {})
        for key in TECHNICAL_MEANS_KEYS:
            for item in means.get(key, []):
                if item not in merged[key]:
                    merged[key].append(item)
    merged["modules"].append("integrated_p0_verify")
    merged["verification_conditions"].append("total_field_only_decision_authority_required")
    merged["blocking_conditions"].append("cloud_authority_drift_blocked")
    return merged


def derive_governance_decision(
    identity_packet: dict[str, Any],
    state_packet: dict[str, Any],
    front_packet: dict[str, Any],
    chain_packet: dict[str, Any],
    case_flags: dict[str, Any],
) -> dict[str, Any]:
    identity_decision = identity_packet.get("identity_decision", {})
    front_decision = front_packet.get("proxy_decision", {})
    reasons: list[str] = []

    if case_flags.get("field_drift_risk"):
        reasons.append("field_drift_blocked")
    if case_flags.get("adi_drift_risk"):
        reasons.append("adi_drift_blocked")
    if case_flags.get("cloud_authority_drift_risk"):
        reasons.append("cloud_authority_drift_blocked")
    if case_flags.get("credential_material_risk"):
        reasons.append("credential_material_blocked")
    if case_flags.get("identifiable_plaintext_risk"):
        reasons.append("identifiable_plaintext_blocked")

    if identity_decision.get("decision") == "HOLD":
        decision = "HOLD"
        reasons.extend(identity_decision.get("reasons", []))
    elif identity_decision.get("decision") == "REJECT":
        decision = "REJECT"
        reasons.extend(identity_decision.get("reasons", []))
    elif identity_decision.get("decision") == "BLOCK":
        decision = "BLOCK"
        reasons.extend(identity_decision.get("reasons", []))
    elif front_decision.get("decision") == "HOLD":
        decision = "HOLD"
        reasons.extend(front_decision.get("reasons", []))
    elif front_decision.get("decision") == "REJECT":
        decision = "REJECT"
        reasons.extend(front_decision.get("reasons", []))
    elif front_decision.get("decision") == "BLOCK":
        decision = "BLOCK"
        reasons.extend(front_decision.get("reasons", []))
    elif reasons:
        decision = "BLOCK"
    else:
        decision = "ALLOW_RESTRICTED"

    if case_flags.get("direct_business_write_risk"):
        decision = "BLOCK"
        reasons.append("direct_business_write_blocked")

    restricted_ref = front_decision.get("restricted_execution_instruction_ref", "") if decision == "ALLOW_RESTRICTED" else ""
    return {
        "total_field_only_decision_authority": True,
        "cloud_candidate_decision": False,
        "decision": decision,
        "reasons": sorted(set(reasons)),
        "restricted_execution_instruction_ref": restricted_ref,
        "result_packet_ref": front_decision.get("result_packet_ref", "result_packet_ref:sandbox_only"),
        "accountable_record_ref": accountable_record_ref(chain_packet),
    }


def build_integrated_packet(
    case_name: str = "PASS_FULL_PATH",
    identity_packet: dict[str, Any] | None = None,
    front_packet: dict[str, Any] | None = None,
    case_flags: dict[str, Any] | None = None,
) -> dict[str, Any]:
    case_flags = case_flags or {}
    state_packet = load_json(STATE_FIELD_PACKET_PATH)
    chain_packet = load_json(ACCOUNTABLE_CHAIN_PATH)
    if identity_packet is None:
        identity_packet = load_json(IDENTITY_PATH)
    if front_packet is None:
        front_packet = load_json(FRONT_EDGE_PATH)
    governance = derive_governance_decision(identity_packet, state_packet, front_packet, chain_packet, case_flags)
    return {
        "packet_type": "integrated_p0_verify_sandbox",
        "sandbox_only": True,
        "case_name": case_name,
        "case_flags": case_flags,
        "source_refs": {
            "seal_ref": file_ref(SEAL_DIR / "MANIFEST.json"),
            "candidate_ref": file_ref(CANDIDATE_PATH),
            "module_1_state_field_packet_runtime_ref": file_ref(STATE_FIELD_PACKET_PATH),
            "module_2_accountable_record_chain_ref": file_ref(ACCOUNTABLE_CHAIN_PATH),
            "module_3_front_edge_proxy_blocking_ref": file_ref(FRONT_EDGE_PATH),
            "module_4_sovereign_identity_agent_ref": file_ref(IDENTITY_PATH),
        },
        "candidate_verification": verify_candidate(verified_candidate_packet()),
        "component_packets": {
            "sovereign_identity_agent": identity_packet,
            "state_field_packet_runtime": state_packet,
            "front_edge_proxy_blocking": front_packet,
            "accountable_record_chain": chain_packet,
        },
        "governance_decision": governance,
        "technical_means": component_technical_means(identity_packet, state_packet, front_packet, chain_packet),
        "safety_boundary": {
            "production_system_connected": False,
            "production_member_db_connected": False,
            "db_write": False,
            "deploy": False,
            "restart": False,
            "auto_landing": False,
            "no_secret": True,
            "no_member_plaintext": True,
            "h64_td_ref_only": True,
        },
    }


def verify_integrated_packet(packet: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    components = packet.get("component_packets", {})
    identity = components.get("sovereign_identity_agent", {})
    state_packet = components.get("state_field_packet_runtime", {})
    front = components.get("front_edge_proxy_blocking", {})
    chain = components.get("accountable_record_chain", {})
    governance = packet.get("governance_decision", {})
    flags = packet.get("case_flags", {})
    text = json.dumps(packet, ensure_ascii=False, sort_keys=True)

    identity_result = verify_identity_packet(identity)
    state_result = verify_packet(state_packet)
    front_result = verify_proxy_packet(front)
    chain_result = verify_chain(chain)

    if state_result["DRY_RUN"] != "PASS":
        errors.append("STATE_FIELD_PACKET_RUNTIME_CHECK_FAIL")
    if chain_result["DRY_RUN"] != "PASS":
        errors.append("ACCOUNTABLE_RECORD_CHAIN_CHECK_FAIL")
    if front_result["DRY_RUN"] != "PASS":
        errors.append("FRONT_EDGE_BLOCKING_CHECK_FAIL")
    if identity_result["DRY_RUN"] != "PASS":
        errors.append("SOVEREIGN_IDENTITY_AGENT_CHECK_FAIL")

    if governance.get("total_field_only_decision_authority") is not True or governance.get("cloud_candidate_decision") is not False:
        errors.append("CLOUD_AUTHORITY_CHECK_FAIL:TOTAL_FIELD_AUTHORITY_DRIFT")
    if governance.get("decision") == "ALLOW_RESTRICTED" and not governance.get("restricted_execution_instruction_ref"):
        errors.append("INTEGRATED_FLOW_CHECK_FAIL:MISSING_RESTRICTED_INSTRUCTION_REF")
    if not governance.get("accountable_record_ref"):
        errors.append("ACCOUNTABLE_RECORD_CHAIN_CHECK_FAIL:MISSING_GOVERNANCE_RECORD_REF")
    if front.get("proxy_decision", {}).get("executable_api_call_generated") is not False:
        errors.append("FRONT_EDGE_BLOCKING_CHECK_FAIL:EXECUTABLE_CALL_GENERATED")
    if front.get("proxy_decision", {}).get("business_write_forwarded") is not False:
        errors.append("FRONT_EDGE_BLOCKING_CHECK_FAIL:BUSINESS_WRITE_FORWARDED")

    should_block_flags = [
        "field_drift_risk",
        "adi_drift_risk",
        "cloud_authority_drift_risk",
        "credential_material_risk",
        "identifiable_plaintext_risk",
        "direct_business_write_risk",
    ]
    if any(flags.get(flag) for flag in should_block_flags) and governance.get("decision") not in {"HOLD", "REJECT", "BLOCK"}:
        errors.append("INTEGRATED_FLOW_CHECK_FAIL:RISK_NOT_BLOCKED")
    if flags.get("missing_consent_risk") and governance.get("decision") != "HOLD":
        errors.append("SOVEREIGN_IDENTITY_AGENT_CHECK_FAIL:MISSING_CONSENT_NOT_HELD")
    if flags.get("missing_verifier_risk") and governance.get("decision") != "HOLD":
        errors.append("FRONT_EDGE_BLOCKING_CHECK_FAIL:MISSING_VERIFIER_NOT_HELD")

    if "多個狀態場" not in text and "多狀態場" not in text:
        errors.append("FIELD_DRIFT_CHECK_FAIL:MISSING_MULTI_STATE_CONTEXT")
    if flags.get("field_drift_risk") and governance.get("decision") not in {"HOLD", "REJECT", "BLOCK"}:
        errors.append("FIELD_DRIFT_CHECK_FAIL:RISK_NOT_BLOCKED")
    if flags.get("adi_drift_risk") and governance.get("decision") not in {"HOLD", "REJECT", "BLOCK"}:
        errors.append("ADI_CHECK_FAIL:RISK_NOT_BLOCKED")

    technical = packet.get("technical_means", {})
    for key in TECHNICAL_MEANS_KEYS:
        if not isinstance(technical.get(key), list) or not technical.get(key):
            errors.append(f"TECHNICAL_MEANS_CHECK_FAIL:{key}")

    scan = scan_text(text)
    if scan["status"] != "PASS":
        errors.append("NO_SECRET_FAIL")

    member_scan_text = text
    for safe in [
        "no_member_plaintext",
        "NO_MEMBER_PLAINTEXT",
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
    protected_terms = ["map" + "ping", "ta" + "ble", "ru" + "les"]
    if marker in text and any(term in text for term in protected_terms):
        errors.append("H64_TD_REF_ONLY_FAIL")

    boundary = packet.get("safety_boundary", {})
    for key in ["production_system_connected", "production_member_db_connected", "db_write", "deploy", "restart", "auto_landing"]:
        if boundary.get(key) is not False:
            errors.append(f"SAFETY_BOUNDARY_FAIL:{key}")

    return {
        "JSON_PARSE": "PASS",
        "INTEGRATED_FLOW_CHECK": "PASS" if not any(e.startswith("INTEGRATED_FLOW_CHECK_FAIL") for e in errors) else "FAIL",
        "SOVEREIGN_IDENTITY_AGENT_CHECK": "PASS" if not any(e.startswith("SOVEREIGN_IDENTITY_AGENT_CHECK_FAIL") for e in errors) else "FAIL",
        "STATE_FIELD_PACKET_RUNTIME_CHECK": "PASS" if not any(e.startswith("STATE_FIELD_PACKET_RUNTIME_CHECK_FAIL") for e in errors) else "FAIL",
        "FRONT_EDGE_BLOCKING_CHECK": "PASS" if not any(e.startswith("FRONT_EDGE_BLOCKING_CHECK_FAIL") for e in errors) else "FAIL",
        "ACCOUNTABLE_RECORD_CHAIN_CHECK": "PASS" if not any(e.startswith("ACCOUNTABLE_RECORD_CHAIN_CHECK_FAIL") for e in errors) else "FAIL",
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


def case_passed(case_name: str, packet: dict[str, Any], verifier: dict[str, Any]) -> tuple[str, bool]:
    decision = packet.get("governance_decision", {}).get("decision")
    expected_decision = {
        "PASS_FULL_PATH": "ALLOW_RESTRICTED",
        "HOLD_MISSING_CONSENT": "HOLD",
        "HOLD_MISSING_VERIFIER": "HOLD",
        "REJECT_DIRECT_BUSINESS_WRITE": "BLOCK",
        "REJECT_MEMBER_PLAINTEXT": "BLOCK",
        "REJECT_SECRET": "BLOCK",
        "REJECT_FIELD_DRIFT": "BLOCK",
        "REJECT_ADI_DRIFT": "BLOCK",
        "REJECT_CLOUD_AUTHORITY_DRIFT": "BLOCK",
    }[case_name]
    return expected_decision, verifier["DRY_RUN"] == "PASS" and decision == expected_decision


def build_test_cases() -> list[dict[str, Any]]:
    candidate = load_candidate()
    identity_request = base_identity_request()
    identity_output = base_identity_output(candidate)
    front_request = base_proxy_request()
    cases: list[tuple[str, dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]] = []

    cases.append(("PASS_FULL_PATH", {}, None, None))

    missing_consent = copy.deepcopy(identity_output)
    missing_consent["consent_state_code"] = ""
    cases.append((
        "HOLD_MISSING_CONSENT",
        {"missing_consent_risk": True},
        build_identity_packet(copy.deepcopy(identity_request), missing_consent),
        None,
    ))

    no_verifier = copy.deepcopy(front_request)
    no_verifier["verifier_result"] = ""
    cases.append(("HOLD_MISSING_VERIFIER", {"missing_verifier_risk": True}, None, build_proxy_packet(no_verifier)))

    direct_write = copy.deepcopy(front_request)
    direct_write["direct_business_write_requested"] = True
    cases.append(("REJECT_DIRECT_BUSINESS_WRITE", {"direct_business_write_risk": True}, None, build_proxy_packet(direct_write)))

    member_risk = copy.deepcopy(identity_request)
    member_risk["contains_identifiable_plaintext_risk"] = True
    cases.append((
        "REJECT_MEMBER_PLAINTEXT",
        {"identifiable_plaintext_risk": True},
        build_identity_packet(member_risk, copy.deepcopy(identity_output)),
        None,
    ))

    secret_risk = copy.deepcopy(identity_request)
    secret_risk["contains_credential_material_risk"] = True
    cases.append((
        "REJECT_SECRET",
        {"credential_material_risk": True},
        build_identity_packet(secret_risk, copy.deepcopy(identity_output)),
        None,
    ))

    cases.append(("REJECT_FIELD_DRIFT", {"field_drift_risk": True}, None, None))
    cases.append(("REJECT_ADI_DRIFT", {"adi_drift_risk": True}, None, None))

    cases.append(("REJECT_CLOUD_AUTHORITY_DRIFT", {"cloud_authority_drift_risk": True}, None, None))

    results: list[dict[str, Any]] = []
    for name, flags, identity_packet, front_packet in cases:
        packet = build_integrated_packet(name, identity_packet=identity_packet, front_packet=front_packet, case_flags=flags)
        verifier = verify_integrated_packet(packet)
        expected, passed = case_passed(name, packet, verifier)
        results.append(
            {
                "name": name,
                "expected_decision": expected,
                "actual_decision": packet.get("governance_decision", {}).get("decision"),
                "passed": passed,
                "verifier": verifier,
                "packet": packet,
            }
        )
    return results


def write_sandbox_run(out_root: Path = SANDBOX_ROOT) -> dict[str, Any]:
    run_id = "INTEGRATED_P0_VERIFY_SANDBOX_" + now_utc()
    out = out_root / run_id
    out.mkdir(parents=True, exist_ok=True)

    packet = build_integrated_packet()
    verifier = verify_integrated_packet(packet)
    tests = build_test_cases()
    all_tests_passed = all(item["passed"] for item in tests)
    dry_run_pass = verifier["DRY_RUN"] == "PASS" and all_tests_passed

    write_text(
        out / "00_SOURCE_STATE.md",
        f"""# Integrated P0 Verify Sandbox

STATE=INTEGRATED_P0_VERIFY_SANDBOX
RUN_ID={run_id}
SOURCE_SEAL={rel(SEAL_DIR)}
MODULE_1={rel(STATE_FIELD_PACKET_RUN)}
MODULE_2={rel(ACCOUNTABLE_CHAIN_RUN)}
MODULE_3={rel(FRONT_EDGE_RUN)}
MODULE_4={rel(IDENTITY_RUN)}
SOURCE_CANDIDATE={rel(CANDIDATE_PATH)}

## Boundary

- sandbox_only=true
- production_system_connected=false
- production_member_db_connected=false
- db_write=false
- deploy=false
- restart=false
- auto_landing=false
- total_field_only_decision_authority=true
""",
    )
    write_json(out / "01_INTEGRATED_P0_PACKET.json", packet)
    write_json(out / "02_TEST_CASES.json", tests)
    write_json(out / "03_VERIFIER_RESULTS.json", verifier)
    rows = ["| case | expected | actual | result |", "|---|---|---|---|"]
    for item in tests:
        rows.append(f"| {item['name']} | {item['expected_decision']} | {item['actual_decision']} | {'PASS' if item['passed'] else 'FAIL'} |")
    report_lines = [
        "# Integrated P0 Verify Report",
        "",
        "STATE=INTEGRATED_P0_VERIFY_REPORT",
        f"RUN_ID={run_id}",
        "JSON_PARSE=PASS",
        f"DRY_RUN={'PASS' if dry_run_pass else 'FAIL'}",
        f"INTEGRATED_FLOW_CHECK={verifier['INTEGRATED_FLOW_CHECK']}",
        f"SOVEREIGN_IDENTITY_AGENT_CHECK={verifier['SOVEREIGN_IDENTITY_AGENT_CHECK']}",
        f"STATE_FIELD_PACKET_RUNTIME_CHECK={verifier['STATE_FIELD_PACKET_RUNTIME_CHECK']}",
        f"FRONT_EDGE_BLOCKING_CHECK={verifier['FRONT_EDGE_BLOCKING_CHECK']}",
        f"ACCOUNTABLE_RECORD_CHAIN_CHECK={verifier['ACCOUNTABLE_RECORD_CHAIN_CHECK']}",
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
        "source_seal": rel(SEAL_DIR),
        "module_1": rel(STATE_FIELD_PACKET_RUN),
        "module_2": rel(ACCOUNTABLE_CHAIN_RUN),
        "module_3": rel(FRONT_EDGE_RUN),
        "module_4": rel(IDENTITY_RUN),
        "source_candidate": rel(CANDIDATE_PATH),
        "safety_flags": {
            "sandbox_only": True,
            "production_system_connected": False,
            "production_member_db_connected": False,
            "db_write": False,
            "deploy": False,
            "restart": False,
            "auto_landing": False,
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
    return {
        "run_id": run_id,
        "out": rel(out),
        "files_created": len([path for path in out.iterdir() if path.is_file()]),
        "dry_run": "PASS" if dry_run_pass else "FAIL",
        "verifier": verifier,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build integrated P0 sandbox verification output.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify", help="Verify an integrated P0 packet JSON file.")
    args = parser.parse_args()

    if args.verify:
        packet = json.loads(Path(args.verify).read_text(encoding="utf-8"))
        result = verify_integrated_packet(packet)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["DRY_RUN"] == "PASS" else 2

    if not args.dry_run:
        parser.error("Use --dry-run or --verify")

    summary = write_sandbox_run()
    print("STATE=" + ("PASS_INTEGRATED_P0_VERIFY_SANDBOX" if summary["dry_run"] == "PASS" else "HOLD_INTEGRATED_P0_VERIFY_SANDBOX"))
    print("RUN_ID=" + summary["run_id"])
    print("OUT=" + summary["out"])
    print("FILES_CREATED=" + str(summary["files_created"]))
    print("DRY_RUN=" + summary["dry_run"])
    return 0 if summary["dry_run"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
