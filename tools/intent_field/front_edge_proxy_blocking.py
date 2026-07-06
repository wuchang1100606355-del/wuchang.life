#!/usr/bin/env python3
"""Sandbox-only front-edge proxy blocking simulator and verifier."""

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
SANDBOX_ROOT = ROOT / "runtime/total_field/front_edge_proxy_blocking_sandbox"

REQUIRED_PROXY_FIELDS = [
    "access_request_id",
    "requester_identity_ref",
    "identity_proxy_ref",
    "authority_scope_code",
    "consent_state_code",
    "target_system_ref",
    "target_operation_code",
    "verifier_result",
    "blocking_condition",
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


def accountable_record_ref(accountable_chain_path: Path = ACCOUNTABLE_CHAIN_PATH) -> str:
    chain = json.loads(accountable_chain_path.read_text(encoding="utf-8"))
    records = chain.get("records", [])
    if not records:
        return "accountable_record_ref:sandbox_missing"
    return "accountable_record_ref:" + str(records[-1].get("current_record_hash", "sandbox_missing"))


def base_proxy_request() -> dict[str, Any]:
    candidate = load_candidate()
    identity = candidate.get("sovereign_identity_agent", {})
    archive = candidate.get("plaintext_archive_accountability", {})
    return {
        "access_request_id": str(archive.get("access_request_id") or "access_request_id:sandbox_ref"),
        "requester_identity_ref": str(archive.get("requester_identity_ref") or "requester_identity_ref:sandbox_ref"),
        "identity_proxy_ref": str(identity.get("identity_proxy_ref") or "identity_proxy_ref:sandbox_ref"),
        "authority_scope_code": str(identity.get("authority_scope_code") or "authority_scope_code:sandbox_ref"),
        "consent_state_code": str(identity.get("consent_state_code") or "consent_state_code:sandbox_ref"),
        "target_system_ref": "target_system_ref:sandbox_business_system",
        "target_operation_code": "target_operation_code:sandbox_restricted_operation",
        "verifier_result": "PASS",
        "blocking_condition": "blocking_condition:no_executable_call_before_pass",
        "cloud_candidate_only": True,
        "cloud_final_decision": False,
        "auto_landing": False,
        "direct_business_write_requested": False,
        "contains_identifiable_plaintext_risk": False,
        "contains_credential_material_risk": False,
    }


def simulate_proxy(request: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(request, ensure_ascii=False, sort_keys=True)
    accountable_ref = str(request.get("accountable_record_ref") or accountable_record_ref())
    reasons: list[str] = []

    scan = scan_text(text)
    member_text = text.replace("contains_identifiable_plaintext_risk", "").replace("contains_member_plaintext_risk", "")
    member_risk = bool(request.get("contains_identifiable_plaintext_risk") or request.get("contains_member_plaintext_risk")) or bool(
        re.search(r"(?<![A-Za-z0-9])[A-Z][12]\d{8}(?![A-Za-z0-9])", member_text)
    )
    credential_risk = bool(request.get("contains_credential_material_risk")) or scan["status"] != "PASS"
    if member_risk:
        reasons.append("identifiable_plaintext_blocked")
    if credential_risk:
        reasons.append("credential_material_blocked")
    if request.get("cloud_final_decision") is True or request.get("auto_landing") is True:
        reasons.append("cloud_authority_drift_blocked")
    if request.get("direct_business_write_requested") is True:
        reasons.append("direct_business_write_blocked")

    verifier_result = request.get("verifier_result")
    if verifier_result in ("", None):
        decision = "HOLD"
        reasons.append("missing_verifier_result")
    elif verifier_result == "FAIL":
        decision = "REJECT"
        reasons.append("verifier_result_fail")
    elif reasons:
        decision = "BLOCK"
    elif verifier_result == "PASS":
        decision = "ALLOW_RESTRICTED"
    else:
        decision = "HOLD"
        reasons.append("unsupported_verifier_result")

    return {
        "decision": decision,
        "reasons": reasons,
        "restricted_execution_instruction_ref": (
            "restricted_execution_instruction_ref:sandbox_only" if decision == "ALLOW_RESTRICTED" else ""
        ),
        "result_packet_ref": "result_packet_ref:sandbox_only",
        "accountable_record_ref": accountable_ref,
        "executable_api_call_generated": False,
        "business_write_forwarded": False,
    }


def build_proxy_packet(request: dict[str, Any] | None = None) -> dict[str, Any]:
    if request is None:
        request = base_proxy_request()
    state_packet = json.loads(STATE_FIELD_PACKET_PATH.read_text(encoding="utf-8"))
    chain = json.loads(ACCOUNTABLE_CHAIN_PATH.read_text(encoding="utf-8"))
    decision = simulate_proxy(request)
    return {
        "packet_type": "front_edge_proxy_blocking_sandbox",
        "sandbox_only": True,
        "source_refs": {
            "seal_ref": file_ref(SEAL_DIR / "MANIFEST.json"),
            "state_field_packet_runtime_ref": file_ref(STATE_FIELD_PACKET_PATH),
            "accountable_record_chain_ref": file_ref(ACCOUNTABLE_CHAIN_PATH),
            "candidate_ref": file_ref(CANDIDATE_PATH),
        },
        "patent_type_alignment": state_packet.get("patent_type_alignment", {}),
        "spacetime_state_index_database": state_packet.get("spacetime_state_index_database", {}),
        "proxy_request": request,
        "proxy_decision": decision,
        "technical_means": {
            "modules": ["front_edge_proxy_layer", "pre_execution_verifier_gate", "restricted_instruction_emitter"],
            "data_structures": ["proxy_request_packet", "restricted_execution_instruction", "result_packet"],
            "packet_fields": REQUIRED_PROXY_FIELDS
            + ["restricted_execution_instruction_ref", "result_packet_ref", "accountable_record_ref"],
            "verification_conditions": [
                "verifier_result_pass_required_before_restricted_instruction",
                "cloud_candidate_only_required",
                "no_direct_business_write",
                "accountable_record_ref_required_for_every_decision",
            ],
            "blocking_conditions": [
                "missing_verifier_result",
                "verifier_result_fail",
                "direct_business_write_requested",
                "identifiable_plaintext_detected",
                "credential_material_detected",
                "cloud_authority_drift",
            ],
            "record_fields": list(chain.get("technical_means", {}).get("record_fields", [])),
        },
        "safety_boundary": {
            "production_system_connected": False,
            "db_write": False,
            "deploy": False,
            "restart": False,
            "auto_landing": False,
            "no_secret": True,
            "no_member_plaintext": True,
            "h64_td_ref_only": True,
        },
    }


def verify_proxy_packet(packet: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    request = packet.get("proxy_request", {})
    decision = packet.get("proxy_decision", {})
    technical = packet.get("technical_means", {})
    index_db = packet.get("spacetime_state_index_database", {})
    text = json.dumps(packet, ensure_ascii=False, sort_keys=True)

    missing = [field for field in REQUIRED_PROXY_FIELDS if field != "verifier_result" and request.get(field) in ("", None, [], {})]
    if missing:
        errors.append("FRONT_EDGE_BLOCKING_CHECK_FAIL:MISSING_PROXY_FIELDS:" + ",".join(missing))

    if decision.get("accountable_record_ref") in ("", None):
        errors.append("ACCOUNTABLE_RECORD_LINK_CHECK_FAIL:MISSING_ACCOUNTABLE_RECORD_REF")
    if decision.get("executable_api_call_generated") is not False:
        errors.append("FRONT_EDGE_BLOCKING_CHECK_FAIL:EXECUTABLE_API_CALL_GENERATED")
    if decision.get("business_write_forwarded") is not False:
        errors.append("FRONT_EDGE_BLOCKING_CHECK_FAIL:BUSINESS_WRITE_FORWARDED")
    if request.get("verifier_result") == "PASS" and decision.get("decision") == "ALLOW_RESTRICTED":
        if decision.get("restricted_execution_instruction_ref") in ("", None):
            errors.append("FRONT_EDGE_BLOCKING_CHECK_FAIL:MISSING_RESTRICTED_INSTRUCTION_REF")
    if request.get("verifier_result") in ("", None) and decision.get("decision") != "HOLD":
        errors.append("FRONT_EDGE_BLOCKING_CHECK_FAIL:MISSING_VERIFIER_NOT_HOLD")
    if request.get("verifier_result") == "FAIL" and decision.get("decision") != "REJECT":
        errors.append("FRONT_EDGE_BLOCKING_CHECK_FAIL:FAIL_VERIFIER_NOT_REJECTED")
    if request.get("direct_business_write_requested") is True and decision.get("decision") not in {"BLOCK", "HOLD", "REJECT"}:
        errors.append("FRONT_EDGE_BLOCKING_CHECK_FAIL:DIRECT_WRITE_NOT_BLOCKED")
    if (request.get("contains_identifiable_plaintext_risk") is True or request.get("contains_member_plaintext_risk") is True) and decision.get("decision") not in {"BLOCK", "HOLD", "REJECT"}:
        errors.append("FRONT_EDGE_BLOCKING_CHECK_FAIL:MEMBER_RISK_NOT_BLOCKED")
    if request.get("contains_credential_material_risk") is True and decision.get("decision") not in {"BLOCK", "HOLD", "REJECT"}:
        errors.append("FRONT_EDGE_BLOCKING_CHECK_FAIL:CREDENTIAL_RISK_NOT_BLOCKED")

    if request.get("cloud_final_decision") is True or request.get("auto_landing") is True:
        if decision.get("decision") not in {"BLOCK", "HOLD", "REJECT"}:
            errors.append("CLOUD_AUTHORITY_CHECK_FAIL:AUTHORITY_DRIFT_NOT_BLOCKED")
    if request.get("cloud_candidate_only") is not True:
        errors.append("CLOUD_AUTHORITY_CHECK_FAIL:NOT_CANDIDATE_ONLY")

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

    safe_member_terms = [
        "no_member_plaintext",
        "NO_MEMBER_PLAINTEXT",
        "contains_member_plaintext_risk",
        "contains_identifiable_plaintext_risk",
        "identifiable_plaintext_blocked",
        "identifiable_plaintext_detected",
    ]
    member_scan_text = text
    for term in safe_member_terms:
        member_scan_text = member_scan_text.replace(term, "")
    if "member_plaintext" in member_scan_text:
        errors.append("NO_MEMBER_PLAINTEXT_FAIL")

    marker = "H64" + "-TD"
    protected_terms = ["map" + "ping", "ta" + "ble", "ru" + "les"]
    if marker in text and any(term in text for term in protected_terms):
        errors.append("H64_TD_REF_ONLY_FAIL")

    boundary = packet.get("safety_boundary", {})
    if boundary.get("production_system_connected") is not False:
        errors.append("PRODUCTION_SYSTEM_CONNECTED_NOT_FALSE")
    if boundary.get("db_write") is not False:
        errors.append("DB_WRITE_NOT_FALSE")
    if boundary.get("deploy") is not False:
        errors.append("DEPLOY_NOT_FALSE")
    if boundary.get("restart") is not False:
        errors.append("RESTART_NOT_FALSE")

    return {
        "JSON_PARSE": "PASS",
        "FRONT_EDGE_BLOCKING_CHECK": "PASS" if not any(e.startswith("FRONT_EDGE_BLOCKING_CHECK_FAIL") for e in errors) else "FAIL",
        "CLOUD_AUTHORITY_CHECK": "PASS" if not any(e.startswith("CLOUD_AUTHORITY_CHECK_FAIL") for e in errors) else "FAIL",
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
    decision = packet.get("proxy_decision", {}).get("decision")
    if name == "PASS_CASE":
        return "PASS" if decision == "ALLOW_RESTRICTED" else "FAIL"
    return "PASS" if decision in {"BLOCK", "HOLD", "REJECT"} else "FAIL"


def build_test_cases() -> list[dict[str, Any]]:
    base = base_proxy_request()
    cases: list[dict[str, Any]] = []

    cases.append({"name": "PASS_CASE", "expected": "PASS", "packet": build_proxy_packet(copy.deepcopy(base))})

    no_verifier = copy.deepcopy(base)
    no_verifier["verifier_result"] = ""
    cases.append({"name": "FAIL_NO_VERIFIER", "expected": "PASS", "packet": build_proxy_packet(no_verifier)})

    deny = copy.deepcopy(base)
    deny["verifier_result"] = "FAIL"
    cases.append({"name": "FAIL_VERIFIER_DENY", "expected": "PASS", "packet": build_proxy_packet(deny)})

    direct_write = copy.deepcopy(base)
    direct_write["direct_business_write_requested"] = True
    cases.append({"name": "FAIL_DIRECT_BUSINESS_WRITE", "expected": "PASS", "packet": build_proxy_packet(direct_write)})

    member = copy.deepcopy(base)
    member["contains_identifiable_plaintext_risk"] = True
    cases.append({"name": "FAIL_MEMBER_PLAINTEXT", "expected": "PASS", "packet": build_proxy_packet(member)})

    secret = copy.deepcopy(base)
    secret["contains_credential_material_risk"] = True
    cases.append({"name": "FAIL_SECRET", "expected": "PASS", "packet": build_proxy_packet(secret)})

    authority = copy.deepcopy(base)
    authority["cloud_final_decision"] = True
    authority["auto_landing"] = True
    cases.append({"name": "FAIL_CLOUD_AUTHORITY_DRIFT", "expected": "PASS", "packet": build_proxy_packet(authority)})
    return cases


def run_test_cases() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in build_test_cases():
        verifier = verify_proxy_packet(case["packet"])
        actual = expected_case_result(case["name"], case["packet"])
        results.append(
            {
                "name": case["name"],
                "expected": case["expected"],
                "actual": actual,
                "proxy_decision": case["packet"].get("proxy_decision", {}).get("decision"),
                "passed": actual == case["expected"] and verifier["DRY_RUN"] == "PASS",
                "verifier": verifier,
            }
        )
    return results


def write_sandbox_run(out_root: Path = SANDBOX_ROOT) -> dict[str, Any]:
    run_id = "FRONT_EDGE_PROXY_BLOCKING_SANDBOX_" + now_utc()
    out = out_root / run_id
    out.mkdir(parents=True, exist_ok=True)

    packet = build_proxy_packet()
    verifier = verify_proxy_packet(packet)
    tests = run_test_cases()
    all_tests_passed = all(item["passed"] for item in tests)
    dry_run_pass = verifier["DRY_RUN"] == "PASS" and all_tests_passed

    write_text(
        out / "00_SOURCE_STATE.md",
        f"""# Front Edge Proxy Blocking Sandbox

STATE=FRONT_EDGE_PROXY_BLOCKING_SANDBOX
RUN_ID={run_id}
SOURCE_SEAL={rel(SEAL_DIR)}
PREVIOUS_MODULE_1={rel(STATE_FIELD_PACKET_RUN)}
PREVIOUS_MODULE_2={rel(ACCOUNTABLE_CHAIN_RUN)}
SOURCE_CANDIDATE={rel(CANDIDATE_PATH)}

## Boundary

- sandbox_only=true
- production_system_connected=false
- db_write=false
- deploy=false
- restart=false
- auto_landing=false
- no_secret=true
- no_member_plaintext=true
- h64_td_ref_only=true
""",
    )
    write_json(out / "01_FRONT_EDGE_PROXY_PACKET.json", packet)
    write_json(out / "02_TEST_CASES.json", tests)
    write_json(out / "03_VERIFIER_RESULTS.json", verifier)
    rows = ["| case | proxy_decision | expected | actual | result |", "|---|---|---|---|---|"]
    for item in tests:
        rows.append(
            f"| {item['name']} | {item['proxy_decision']} | {item['expected']} | {item['actual']} | {'PASS' if item['passed'] else 'FAIL'} |"
        )
    report_lines = [
        "# Front Edge Proxy Blocking Verifier Report",
        "",
        "STATE=FRONT_EDGE_PROXY_BLOCKING_VERIFIER_REPORT",
        f"RUN_ID={run_id}",
        "JSON_PARSE=PASS",
        f"DRY_RUN={'PASS' if dry_run_pass else 'FAIL'}",
        f"FRONT_EDGE_BLOCKING_CHECK={verifier['FRONT_EDGE_BLOCKING_CHECK']}",
        f"CLOUD_AUTHORITY_CHECK={verifier['CLOUD_AUTHORITY_CHECK']}",
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
        "source_candidate": rel(CANDIDATE_PATH),
        "safety_flags": {
            "sandbox_only": True,
            "production_system_connected": False,
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
    parser = argparse.ArgumentParser(description="Build front-edge proxy blocking sandbox output.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify", help="Verify a front-edge proxy packet JSON file.")
    args = parser.parse_args()

    if args.verify:
        packet = json.loads(Path(args.verify).read_text(encoding="utf-8"))
        result = verify_proxy_packet(packet)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["DRY_RUN"] == "PASS" else 2

    if not args.dry_run:
        parser.error("Use --dry-run or --verify")

    summary = write_sandbox_run()
    print("STATE=" + ("PASS_FRONT_EDGE_PROXY_BLOCKING_SANDBOX" if summary["dry_run"] == "PASS" else "HOLD_FRONT_EDGE_PROXY_BLOCKING_SANDBOX"))
    print("RUN_ID=" + summary["run_id"])
    print("OUT=" + summary["out"])
    print("FILES_CREATED=" + str(summary["files_created"]))
    print("DRY_RUN=" + summary["dry_run"])
    return 0 if summary["dry_run"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
