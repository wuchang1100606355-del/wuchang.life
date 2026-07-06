#!/usr/bin/env python3
"""Sandbox-only sovereign identity-agent simulator and verifier."""

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

from redact_candidate_payload import scan_text  # noqa: E402
from verify_cloud_candidate_response import normalize_candidate_response  # noqa: E402


SEAL_DIR = ROOT / "runtime/total_field/verified_cloud_candidate_seal/VERIFIED_CLOUD_CANDIDATE_SEAL_20260704T215322Z"
CANDIDATE_PATH = SEAL_DIR / "RETURNED_CLOUD_CANDIDATE_RESPONSE.json"
STATE_FIELD_PACKET_RUN = ROOT / "runtime/total_field/state_field_packet_runtime_sandbox/STATE_FIELD_PACKET_RUNTIME_SANDBOX_20260704T215805Z"
STATE_FIELD_PACKET_PATH = STATE_FIELD_PACKET_RUN / "01_STATE_FIELD_PACKET_RUNTIME.json"
ACCOUNTABLE_CHAIN_RUN = ROOT / "runtime/total_field/accountable_record_chain_sandbox/ACCOUNTABLE_RECORD_CHAIN_SANDBOX_20260704T220355Z"
ACCOUNTABLE_CHAIN_PATH = ACCOUNTABLE_CHAIN_RUN / "01_ACCOUNTABLE_RECORD_CHAIN.json"
FRONT_EDGE_RUN = ROOT / "runtime/total_field/front_edge_proxy_blocking_sandbox/FRONT_EDGE_PROXY_BLOCKING_SANDBOX_20260704T220953Z"
FRONT_EDGE_PATH = FRONT_EDGE_RUN / "01_FRONT_EDGE_PROXY_PACKET.json"
SANDBOX_ROOT = ROOT / "runtime/total_field/sovereign_identity_agent_sandbox"

IDENTITY_OUTPUT_FIELDS = [
    "identity_proxy_ref",
    "authority_scope_code",
    "consent_state_code",
    "device_binding_ref",
    "agent_binding_ref",
    "responsible_person_ref",
    "accountable_record_ref",
]
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


def load_candidate(candidate_path: Path = CANDIDATE_PATH) -> dict[str, Any]:
    payload = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate, _normalization = normalize_candidate_response(payload)
    return candidate


def latest_accountable_record_ref() -> str:
    chain = json.loads(ACCOUNTABLE_CHAIN_PATH.read_text(encoding="utf-8"))
    records = chain.get("records", [])
    if not records:
        return "accountable_record_ref:sandbox_missing"
    return "accountable_record_ref:" + str(records[-1].get("current_record_hash", "sandbox_missing"))


def base_identity_request() -> dict[str, Any]:
    return {
        "subject_type_code": "subject_type_code:user_member_org_device_ai_agent_ref",
        "candidate_action_id": "candidate_action_id:sandbox_identity_action",
        "required_authority_scope_code": "ref_only:authority_scope",
        "requires_consent_state": True,
        "requires_device_binding": True,
        "requires_agent_binding": True,
        "contains_identifiable_plaintext_risk": False,
        "contains_credential_material_risk": False,
        "cloud_candidate_only": True,
        "cloud_final_decision": False,
    }


def base_identity_output(candidate: dict[str, Any]) -> dict[str, Any]:
    identity = candidate.get("sovereign_identity_agent", {})
    return {
        "identity_proxy_ref": str(identity.get("identity_proxy_ref") or "identity_proxy_ref:sandbox_ref"),
        "authority_scope_code": str(identity.get("authority_scope_code") or "ref_only:authority_scope"),
        "consent_state_code": str(identity.get("consent_state_code") or "ref_only:consent_state"),
        "device_binding_ref": str(identity.get("device_binding_ref") or "device_binding_ref:sandbox_ref"),
        "agent_binding_ref": str(identity.get("agent_binding_ref") or "agent_binding_ref:sandbox_ref"),
        "responsible_person_ref": str(identity.get("responsible_person_ref") or "responsible_person_ref:sandbox_ref"),
        "accountable_record_ref": latest_accountable_record_ref(),
    }


def simulate_identity_agent(identity_request: dict[str, Any], identity_output: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps({"identity_request": identity_request, "identity_output": identity_output}, ensure_ascii=False, sort_keys=True)
    scan = scan_text(text)
    reasons: list[str] = []

    member_scan_text = text.replace("contains_identifiable_plaintext_risk", "")
    member_risk = bool(identity_request.get("contains_identifiable_plaintext_risk")) or bool(
        re.search(r"(?<![A-Za-z0-9])[A-Z][12]\d{8}(?![A-Za-z0-9])", member_scan_text)
    )
    credential_risk = bool(identity_request.get("contains_credential_material_risk")) or scan["status"] != "PASS"
    if member_risk:
        reasons.append("identifiable_plaintext_blocked")
    if credential_risk:
        reasons.append("credential_material_blocked")
    if identity_request.get("cloud_final_decision") is True:
        reasons.append("cloud_authority_drift_blocked")

    if identity_request.get("requires_consent_state") is True and not identity_output.get("consent_state_code"):
        reasons.append("missing_consent_state_code")
        decision = "HOLD"
    elif identity_output.get("authority_scope_code") != identity_request.get("required_authority_scope_code"):
        reasons.append("authority_scope_mismatch")
        decision = "REJECT"
    elif identity_request.get("requires_device_binding") is True and not identity_output.get("device_binding_ref"):
        reasons.append("missing_device_binding_ref")
        decision = "HOLD"
    elif identity_request.get("requires_agent_binding") is True and not identity_output.get("agent_binding_ref"):
        reasons.append("missing_agent_binding_ref")
        decision = "HOLD"
    elif not identity_output.get("accountable_record_ref"):
        reasons.append("missing_accountable_record_ref")
        decision = "HOLD"
    elif member_risk or credential_risk or identity_request.get("cloud_final_decision") is True:
        decision = "BLOCK"
    else:
        decision = "ALLOW_REF_ONLY"

    return {
        "decision": decision,
        "reasons": reasons,
        "front_edge_restricted_instruction_allowed": decision == "ALLOW_REF_ONLY",
    }


def build_identity_packet(
    identity_request: dict[str, Any] | None = None,
    identity_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidate = load_candidate()
    state_packet = json.loads(STATE_FIELD_PACKET_PATH.read_text(encoding="utf-8"))
    front_edge = json.loads(FRONT_EDGE_PATH.read_text(encoding="utf-8"))
    if identity_request is None:
        identity_request = base_identity_request()
    if identity_output is None:
        identity_output = base_identity_output(candidate)
    decision = simulate_identity_agent(identity_request, identity_output)
    return {
        "packet_type": "sovereign_identity_agent_sandbox",
        "sandbox_only": True,
        "source_refs": {
            "seal_ref": file_ref(SEAL_DIR / "MANIFEST.json"),
            "state_field_packet_runtime_ref": file_ref(STATE_FIELD_PACKET_PATH),
            "accountable_record_chain_ref": file_ref(ACCOUNTABLE_CHAIN_PATH),
            "front_edge_proxy_blocking_ref": file_ref(FRONT_EDGE_PATH),
            "candidate_ref": file_ref(CANDIDATE_PATH),
        },
        "patent_type_alignment": state_packet.get("patent_type_alignment", {}),
        "spacetime_state_index_database": state_packet.get("spacetime_state_index_database", {}),
        "identity_request": identity_request,
        "identity_proxy_output": identity_output,
        "identity_decision": decision,
        "front_edge_dependency": {
            "restricted_instruction_ref": front_edge.get("proxy_decision", {}).get("restricted_execution_instruction_ref", ""),
            "accountable_record_ref": front_edge.get("proxy_decision", {}).get("accountable_record_ref", ""),
        },
        "technical_means": {
            "modules": ["sovereign_identity_agent", "identity_proxy_ref_mapper", "consent_authority_gate"],
            "data_structures": ["identity_proxy_packet", "authority_consent_binding_record"],
            "packet_fields": IDENTITY_OUTPUT_FIELDS
            + ["subject_type_code", "candidate_action_id", "required_authority_scope_code"],
            "verification_conditions": [
                "consent_state_code_required_before_front_edge_allow",
                "authority_scope_code_matches_candidate_action",
                "device_binding_ref_required_when_device_bound",
                "agent_binding_ref_required_when_agent_bound",
                "accountable_record_ref_required",
            ],
            "blocking_conditions": [
                "missing_consent_state_code",
                "authority_scope_mismatch",
                "missing_device_binding_ref",
                "missing_agent_binding_ref",
                "missing_accountable_record_ref",
                "identifiable_plaintext_detected",
                "credential_material_detected",
            ],
            "record_fields": list(json.loads(ACCOUNTABLE_CHAIN_PATH.read_text(encoding="utf-8")).get("technical_means", {}).get("record_fields", [])),
        },
        "safety_boundary": {
            "production_member_db_connected": False,
            "member_plaintext_read": False,
            "db_write": False,
            "deploy": False,
            "restart": False,
            "auto_landing": False,
            "no_secret": True,
            "no_member_plaintext": True,
            "h64_td_ref_only": True,
        },
    }


def verify_identity_packet(packet: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    request = packet.get("identity_request", {})
    output = packet.get("identity_proxy_output", {})
    decision = packet.get("identity_decision", {})
    technical = packet.get("technical_means", {})
    index_db = packet.get("spacetime_state_index_database", {})
    text = json.dumps(packet, ensure_ascii=False, sort_keys=True)

    missing_output = [field for field in IDENTITY_OUTPUT_FIELDS if output.get(field) in ("", None, [], {})]
    if missing_output and decision.get("decision") == "ALLOW_REF_ONLY":
        errors.append("SOVEREIGN_IDENTITY_AGENT_CHECK_FAIL:MISSING_OUTPUT_FIELDS:" + ",".join(missing_output))
    if output.get("identity_proxy_ref") in ("", None):
        errors.append("SOVEREIGN_IDENTITY_AGENT_CHECK_FAIL:MISSING_IDENTITY_PROXY_REF")

    if request.get("requires_consent_state") is True and output.get("consent_state_code") in ("", None):
        if decision.get("decision") != "HOLD" or decision.get("front_edge_restricted_instruction_allowed") is not False:
            errors.append("CONSENT_STATE_CHECK_FAIL:MISSING_CONSENT_NOT_HELD")
    if output.get("authority_scope_code") != request.get("required_authority_scope_code"):
        if decision.get("decision") != "REJECT" or decision.get("front_edge_restricted_instruction_allowed") is not False:
            errors.append("AUTHORITY_SCOPE_CHECK_FAIL:MISMATCH_NOT_REJECTED")
    if request.get("requires_device_binding") is True and output.get("device_binding_ref") in ("", None):
        if decision.get("decision") != "HOLD" or decision.get("front_edge_restricted_instruction_allowed") is not False:
            errors.append("DEVICE_AGENT_BINDING_CHECK_FAIL:MISSING_DEVICE_NOT_HELD")
    if request.get("requires_agent_binding") is True and output.get("agent_binding_ref") in ("", None):
        if decision.get("decision") != "HOLD" or decision.get("front_edge_restricted_instruction_allowed") is not False:
            errors.append("DEVICE_AGENT_BINDING_CHECK_FAIL:MISSING_AGENT_NOT_HELD")
    if output.get("accountable_record_ref") in ("", None):
        if decision.get("decision") != "HOLD" or decision.get("front_edge_restricted_instruction_allowed") is not False:
            errors.append("ACCOUNTABLE_RECORD_LINK_CHECK_FAIL:MISSING_LINK_NOT_HELD")
    if decision.get("decision") != "ALLOW_REF_ONLY" and decision.get("front_edge_restricted_instruction_allowed") is True:
        errors.append("CONSENT_STATE_CHECK_FAIL:FRONT_EDGE_ALLOWED_WITHOUT_IDENTITY_PASS")

    if "多個狀態場" not in text and "多狀態場" not in text:
        errors.append("FIELD_DRIFT_CHECK_FAIL:MISSING_MULTI_STATE_CONTEXT")
    if index_db.get("generic_name") != "時空狀態索引資料庫":
        errors.append("ADI_CHECK_FAIL:MISSING_SPACETIME_INDEX_GENERIC_NAME")
    if index_db.get("actual_index_rules_disclosed") is True:
        errors.append("ADI_CHECK_FAIL:INDEX_RULE_DISCLOSURE")

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
        "contains_identifiable_plaintext_risk",
        "identifiable_plaintext_blocked",
        "identifiable_plaintext_detected",
        "member_plaintext_read",
    ]:
        member_scan_text = member_scan_text.replace(safe, "")
    if request.get("contains_identifiable_plaintext_risk") is True:
        if decision.get("decision") not in {"BLOCK", "HOLD", "REJECT"}:
            errors.append("SOVEREIGN_IDENTITY_AGENT_CHECK_FAIL:IDENTIFIABLE_RISK_NOT_BLOCKED")
    if "member_plaintext" in member_scan_text or re.search(r"(?<![A-Za-z0-9])[A-Z][12]\d{8}(?![A-Za-z0-9])", member_scan_text):
        errors.append("NO_MEMBER_PLAINTEXT_FAIL")

    marker = "H64" + "-TD"
    protected_terms = ["map" + "ping", "ta" + "ble", "ru" + "les"]
    if marker in text and any(term in text for term in protected_terms):
        errors.append("H64_TD_REF_ONLY_FAIL")

    boundary = packet.get("safety_boundary", {})
    if boundary.get("production_member_db_connected") is not False:
        errors.append("PRODUCTION_MEMBER_DB_CONNECTED_NOT_FALSE")
    if boundary.get("member_plaintext_read") is not False:
        errors.append("MEMBER_PLAINTEXT_READ_NOT_FALSE")
    if boundary.get("db_write") is not False:
        errors.append("DB_WRITE_NOT_FALSE")
    if boundary.get("deploy") is not False:
        errors.append("DEPLOY_NOT_FALSE")
    if boundary.get("restart") is not False:
        errors.append("RESTART_NOT_FALSE")

    return {
        "JSON_PARSE": "PASS",
        "SOVEREIGN_IDENTITY_AGENT_CHECK": "PASS" if not any(e.startswith("SOVEREIGN_IDENTITY_AGENT_CHECK_FAIL") for e in errors) else "FAIL",
        "CONSENT_STATE_CHECK": "PASS" if not any(e.startswith("CONSENT_STATE_CHECK_FAIL") for e in errors) else "FAIL",
        "AUTHORITY_SCOPE_CHECK": "PASS" if not any(e.startswith("AUTHORITY_SCOPE_CHECK_FAIL") for e in errors) else "FAIL",
        "DEVICE_AGENT_BINDING_CHECK": "PASS" if not any(e.startswith("DEVICE_AGENT_BINDING_CHECK_FAIL") for e in errors) else "FAIL",
        "ACCOUNTABLE_RECORD_LINK_CHECK": "PASS" if not any(e.startswith("ACCOUNTABLE_RECORD_LINK_CHECK_FAIL") for e in errors) else "FAIL",
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


def expected_case_result(name: str, packet: dict[str, Any]) -> str:
    decision = packet.get("identity_decision", {}).get("decision")
    if name == "PASS_CASE":
        return "PASS" if decision == "ALLOW_REF_ONLY" else "FAIL"
    return "PASS" if decision in {"HOLD", "REJECT", "BLOCK"} else "FAIL"


def build_test_cases() -> list[dict[str, Any]]:
    request = base_identity_request()
    output = base_identity_output(load_candidate())
    cases: list[dict[str, Any]] = []
    cases.append({"name": "PASS_CASE", "expected": "PASS", "packet": build_identity_packet(copy.deepcopy(request), copy.deepcopy(output))})

    missing_consent = copy.deepcopy(output)
    missing_consent["consent_state_code"] = ""
    cases.append({"name": "FAIL_MISSING_CONSENT", "expected": "PASS", "packet": build_identity_packet(copy.deepcopy(request), missing_consent)})

    authority_bad = copy.deepcopy(output)
    authority_bad["authority_scope_code"] = "authority_scope_code:denied_ref"
    cases.append({"name": "FAIL_AUTHORITY_SCOPE", "expected": "PASS", "packet": build_identity_packet(copy.deepcopy(request), authority_bad)})

    plaintext_request = copy.deepcopy(request)
    plaintext_request["contains_identifiable_plaintext_risk"] = True
    cases.append({"name": "FAIL_DIRECT_IDENTITY_PLAINTEXT", "expected": "PASS", "packet": build_identity_packet(plaintext_request, copy.deepcopy(output))})

    missing_device = copy.deepcopy(output)
    missing_device["device_binding_ref"] = ""
    cases.append({"name": "FAIL_DEVICE_BINDING_MISSING", "expected": "PASS", "packet": build_identity_packet(copy.deepcopy(request), missing_device)})

    missing_agent = copy.deepcopy(output)
    missing_agent["agent_binding_ref"] = ""
    cases.append({"name": "FAIL_AGENT_BINDING_MISSING", "expected": "PASS", "packet": build_identity_packet(copy.deepcopy(request), missing_agent)})

    missing_accountable = copy.deepcopy(output)
    missing_accountable["accountable_record_ref"] = ""
    cases.append({"name": "FAIL_ACCOUNTABLE_RECORD_LINK_MISSING", "expected": "PASS", "packet": build_identity_packet(copy.deepcopy(request), missing_accountable)})
    return cases


def run_test_cases() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in build_test_cases():
        verifier = verify_identity_packet(case["packet"])
        actual = expected_case_result(case["name"], case["packet"])
        results.append(
            {
                "name": case["name"],
                "expected": case["expected"],
                "actual": actual,
                "identity_decision": case["packet"].get("identity_decision", {}).get("decision"),
                "front_edge_allowed": case["packet"].get("identity_decision", {}).get("front_edge_restricted_instruction_allowed"),
                "passed": actual == case["expected"] and verifier["DRY_RUN"] == "PASS",
                "verifier": verifier,
            }
        )
    return results


def write_sandbox_run(out_root: Path = SANDBOX_ROOT) -> dict[str, Any]:
    run_id = "SOVEREIGN_IDENTITY_AGENT_SANDBOX_" + now_utc()
    out = out_root / run_id
    out.mkdir(parents=True, exist_ok=True)

    packet = build_identity_packet()
    verifier = verify_identity_packet(packet)
    tests = run_test_cases()
    all_tests_passed = all(item["passed"] for item in tests)
    dry_run_pass = verifier["DRY_RUN"] == "PASS" and all_tests_passed

    write_text(
        out / "00_SOURCE_STATE.md",
        f"""# Sovereign Identity Agent Sandbox

STATE=SOVEREIGN_IDENTITY_AGENT_SANDBOX
RUN_ID={run_id}
SOURCE_SEAL={rel(SEAL_DIR)}
PREVIOUS_MODULE_1={rel(STATE_FIELD_PACKET_RUN)}
PREVIOUS_MODULE_2={rel(ACCOUNTABLE_CHAIN_RUN)}
PREVIOUS_MODULE_3={rel(FRONT_EDGE_RUN)}
SOURCE_CANDIDATE={rel(CANDIDATE_PATH)}

## Boundary

- sandbox_only=true
- production_member_db_connected=false
- member_plaintext_read=false
- db_write=false
- deploy=false
- restart=false
- auto_landing=false
- no_secret=true
- no_member_plaintext=true
- h64_td_ref_only=true
""",
    )
    write_json(out / "01_SOVEREIGN_IDENTITY_AGENT_PACKET.json", packet)
    write_json(out / "02_TEST_CASES.json", tests)
    write_json(out / "03_VERIFIER_RESULTS.json", verifier)
    rows = ["| case | identity_decision | front_edge_allowed | expected | actual | result |", "|---|---|---|---|---|---|"]
    for item in tests:
        rows.append(
            f"| {item['name']} | {item['identity_decision']} | {str(item['front_edge_allowed']).lower()} | {item['expected']} | {item['actual']} | {'PASS' if item['passed'] else 'FAIL'} |"
        )
    report_lines = [
        "# Sovereign Identity Agent Verifier Report",
        "",
        "STATE=SOVEREIGN_IDENTITY_AGENT_VERIFIER_REPORT",
        f"RUN_ID={run_id}",
        "JSON_PARSE=PASS",
        f"DRY_RUN={'PASS' if dry_run_pass else 'FAIL'}",
        f"SOVEREIGN_IDENTITY_AGENT_CHECK={verifier['SOVEREIGN_IDENTITY_AGENT_CHECK']}",
        f"CONSENT_STATE_CHECK={verifier['CONSENT_STATE_CHECK']}",
        f"AUTHORITY_SCOPE_CHECK={verifier['AUTHORITY_SCOPE_CHECK']}",
        f"DEVICE_AGENT_BINDING_CHECK={verifier['DEVICE_AGENT_BINDING_CHECK']}",
        f"ACCOUNTABLE_RECORD_LINK_CHECK={verifier['ACCOUNTABLE_RECORD_LINK_CHECK']}",
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
        "previous_module_1": rel(STATE_FIELD_PACKET_RUN),
        "previous_module_2": rel(ACCOUNTABLE_CHAIN_RUN),
        "previous_module_3": rel(FRONT_EDGE_RUN),
        "source_candidate": rel(CANDIDATE_PATH),
        "safety_flags": {
            "sandbox_only": True,
            "production_member_db_connected": False,
            "member_plaintext_read": False,
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
    parser = argparse.ArgumentParser(description="Build sovereign identity-agent sandbox output.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify", help="Verify a sovereign identity-agent JSON file.")
    args = parser.parse_args()

    if args.verify:
        packet = json.loads(Path(args.verify).read_text(encoding="utf-8"))
        result = verify_identity_packet(packet)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["DRY_RUN"] == "PASS" else 2

    if not args.dry_run:
        parser.error("Use --dry-run or --verify")

    summary = write_sandbox_run()
    print("STATE=" + ("PASS_SOVEREIGN_IDENTITY_AGENT_SANDBOX" if summary["dry_run"] == "PASS" else "HOLD_SOVEREIGN_IDENTITY_AGENT_SANDBOX"))
    print("RUN_ID=" + summary["run_id"])
    print("OUT=" + summary["out"])
    print("FILES_CREATED=" + str(summary["files_created"]))
    print("DRY_RUN=" + summary["dry_run"])
    return 0 if summary["dry_run"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
