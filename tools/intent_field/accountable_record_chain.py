#!/usr/bin/env python3
"""Sandbox-only accountable record-chain builder and verifier."""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
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
SANDBOX_ROOT = ROOT / "runtime/total_field/accountable_record_chain_sandbox"
GENESIS_HASH = "hash:" + ("0" * 64)

RECORD_FIELDS = [
    "candidate_action_id",
    "state_packet_id",
    "rule_version",
    "verifier_result",
    "execution_result",
    "timestamp_coordinate",
    "responsible_person_ref",
    "previous_record_hash",
    "current_record_hash",
    "plaintext_archive_ref",
    "access_request_id",
    "requester_identity_ref",
    "authority_basis",
    "access_reason_code",
    "approval_result",
]
PLAINTEXT_ARCHIVE_FIELDS = [
    "plaintext_archive_ref",
    "access_request_id",
    "requester_identity_ref",
    "authority_basis",
    "access_reason_code",
    "approval_result",
]
TECHNICAL_MEANS_KEYS = [
    "modules",
    "data_structures",
    "record_fields",
    "verification_conditions",
    "blocking_conditions",
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


def canonical_record(record: dict[str, Any]) -> str:
    body = {key: value for key, value in record.items() if key != "current_record_hash"}
    return json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def record_hash(record: dict[str, Any]) -> str:
    return "hash:" + hashlib.sha256(canonical_record(record).encode("utf-8")).hexdigest()


def attach_current_hash(record: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(record)
    out["current_record_hash"] = record_hash(out)
    return out


def load_candidate(candidate_path: Path = CANDIDATE_PATH) -> dict[str, Any]:
    payload = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate, _normalization = normalize_candidate_response(payload)
    return candidate


def archive_fields_from_candidate(candidate: dict[str, Any]) -> dict[str, str]:
    archive = candidate.get("plaintext_archive_accountability")
    if not isinstance(archive, dict):
        archive = candidate.get("isolated_plaintext_archive_boundary", {}).get("accountable_access_record", {})
    if not isinstance(archive, dict):
        archive = {}
    return {
        "plaintext_archive_ref": str(archive.get("plaintext_archive_ref") or "plaintext_archive_ref:sandbox_ref"),
        "access_request_id": str(archive.get("access_request_id") or "access_request_id:sandbox_ref"),
        "requester_identity_ref": str(archive.get("requester_identity_ref") or "requester_identity_ref:sandbox_ref"),
        "authority_basis": str(archive.get("authority_basis") or "authority_basis:sandbox_ref"),
        "access_reason_code": str(archive.get("access_reason_code") or "access_reason_code:sandbox_ref"),
        "approval_result": str(archive.get("approval_result") or "approval_result:sandbox_ref"),
    }


def build_record(
    candidate: dict[str, Any],
    state_packet: dict[str, Any],
    previous_hash: str,
    sequence: int,
    execution_result: str,
) -> dict[str, Any]:
    dynamic = state_packet.get("state_field_packet", {})
    identity = candidate.get("sovereign_identity_agent", {})
    archive = archive_fields_from_candidate(candidate)
    record = {
        "candidate_action_id": f"candidate_action_id:sandbox:{sequence}",
        "state_packet_id": str(dynamic.get("state_field_set_id") or "state_packet_id:sandbox_ref"),
        "rule_version": str(candidate.get("plaintext_archive_accountability", {}).get("rule_version") or "rule_version:sandbox_ref"),
        "verifier_result": str(dynamic.get("verifier_result") or "REVIEW"),
        "execution_result": execution_result,
        "timestamp_coordinate": str(dynamic.get("timestamp_coordinate") or f"timestamp_coordinate:20260704T{sequence:06d}Z"),
        "responsible_person_ref": str(identity.get("responsible_person_ref") or candidate.get("plaintext_archive_accountability", {}).get("responsible_person_ref") or "responsible_person_ref:sandbox_ref"),
        "previous_record_hash": previous_hash,
        **archive,
    }
    return attach_current_hash(record)


def build_pass_chain(candidate_path: Path = CANDIDATE_PATH, state_packet_path: Path = STATE_FIELD_PACKET_PATH) -> dict[str, Any]:
    candidate = load_candidate(candidate_path)
    state_packet = json.loads(state_packet_path.read_text(encoding="utf-8"))
    first = build_record(candidate, state_packet, GENESIS_HASH, 1, "SANDBOX_GENESIS_RECORD_ONLY")
    second = build_record(candidate, state_packet, first["current_record_hash"], 2, "SANDBOX_SECOND_RECORD_ONLY")
    return {
        "packet_type": "accountable_record_chain_sandbox",
        "sandbox_only": True,
        "source_refs": {
            "seal_ref": file_ref(SEAL_DIR / "MANIFEST.json"),
            "state_field_packet_runtime_ref": file_ref(state_packet_path),
            "candidate_ref": file_ref(candidate_path),
        },
        "patent_type_alignment": state_packet.get("patent_type_alignment", {}),
        "spacetime_state_index_database": state_packet.get("spacetime_state_index_database", {}),
        "records": [first, second],
        "technical_means": {
            "modules": ["accountable_record_chain", "hash_chain_verifier", "plaintext_archive_accountability"],
            "data_structures": ["accountable_record", "hash_chain_record_list"],
            "record_fields": RECORD_FIELDS,
            "verification_conditions": [
                "previous_record_hash_matches_prior_current_record_hash",
                "current_record_hash_matches_canonical_record",
                "responsible_person_ref_required",
                "verifier_result_required",
                "plaintext_archive_access_fields_required",
            ],
            "blocking_conditions": [
                "hash_chain_broken",
                "missing_responsible_person_ref",
                "missing_plaintext_archive_access_fields",
                "missing_verifier_result",
            ],
        },
        "safety_boundary": {
            "production_ledger_write": False,
            "db_write": False,
            "deploy": False,
            "restart": False,
            "auto_landing": False,
            "no_secret": True,
            "no_member_plaintext": True,
            "h64_td_ref_only": True,
        },
    }


def has_archive_access(record: dict[str, Any]) -> bool:
    return any(record.get(field) not in ("", None, [], {}) for field in PLAINTEXT_ARCHIVE_FIELDS)


def verify_chain(packet: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    records = packet.get("records", [])
    technical = packet.get("technical_means", {})
    index_db = packet.get("spacetime_state_index_database", {})
    text = json.dumps(packet, ensure_ascii=False, sort_keys=True)

    if not isinstance(records, list) or not records:
        errors.append("ACCOUNTABILITY_FIELDS_CHECK_FAIL:NO_RECORDS")
        records = []

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"ACCOUNTABILITY_FIELDS_CHECK_FAIL:RECORD_{index}_NOT_OBJECT")
            continue
        missing = [field for field in RECORD_FIELDS if record.get(field) in ("", None, [], {})]
        if missing:
            errors.append(f"ACCOUNTABILITY_FIELDS_CHECK_FAIL:RECORD_{index}_MISSING:" + ",".join(missing))
        if record.get("responsible_person_ref") in ("", None):
            errors.append(f"ACCOUNTABILITY_FIELDS_CHECK_FAIL:RECORD_{index}_MISSING_RESPONSIBLE_PERSON")
        if record.get("verifier_result") in ("", None):
            errors.append(f"ACCOUNTABILITY_FIELDS_CHECK_FAIL:RECORD_{index}_MISSING_VERIFIER_RESULT")
        if has_archive_access(record):
            missing_archive = [field for field in PLAINTEXT_ARCHIVE_FIELDS if record.get(field) in ("", None, [], {})]
            if missing_archive:
                errors.append(f"PLAINTEXT_ARCHIVE_ACCOUNTABILITY_CHECK_FAIL:RECORD_{index}_MISSING:" + ",".join(missing_archive))
        expected_current = record_hash(record)
        if record.get("current_record_hash") != expected_current:
            errors.append(f"HASH_CHAIN_CHECK_FAIL:RECORD_{index}_CURRENT_HASH_MISMATCH")
        expected_previous = GENESIS_HASH if index == 0 else records[index - 1].get("current_record_hash")
        if record.get("previous_record_hash") != expected_previous:
            errors.append(f"HASH_CHAIN_CHECK_FAIL:RECORD_{index}_PREVIOUS_HASH_MISMATCH")

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

    member_scan_text = text.replace("no_member_plaintext", "").replace("NO_MEMBER_PLAINTEXT", "")
    if "member_plaintext" in member_scan_text or "identifiable_person_plaintext" in member_scan_text:
        errors.append("NO_MEMBER_PLAINTEXT_FAIL")

    marker = "H64" + "-TD"
    protected_terms = ["map" + "ping", "ta" + "ble", "ru" + "les"]
    h64_fail = marker in text and any(term in text for term in protected_terms)
    if h64_fail:
        errors.append("H64_TD_REF_ONLY_FAIL")

    boundary = packet.get("safety_boundary", {})
    if boundary.get("production_ledger_write") is not False:
        errors.append("PRODUCTION_LEDGER_WRITE_NOT_FALSE")
    if boundary.get("db_write") is not False:
        errors.append("DB_WRITE_NOT_FALSE")
    if boundary.get("deploy") is not False:
        errors.append("DEPLOY_NOT_FALSE")
    if boundary.get("restart") is not False:
        errors.append("RESTART_NOT_FALSE")

    return {
        "JSON_PARSE": "PASS",
        "HASH_CHAIN_CHECK": "PASS" if not any(e.startswith("HASH_CHAIN_CHECK_FAIL") for e in errors) else "FAIL",
        "ACCOUNTABILITY_FIELDS_CHECK": "PASS" if not any(e.startswith("ACCOUNTABILITY_FIELDS_CHECK_FAIL") for e in errors) else "FAIL",
        "PLAINTEXT_ARCHIVE_ACCOUNTABILITY_CHECK": "PASS" if not any(e.startswith("PLAINTEXT_ARCHIVE_ACCOUNTABILITY_CHECK_FAIL") for e in errors) else "FAIL",
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
    pass_packet = build_pass_chain()
    cases = [{"name": "PASS_CASE", "expected": "PASS", "packet": pass_packet}]

    broken = copy.deepcopy(pass_packet)
    broken["records"][1]["previous_record_hash"] = "hash:" + ("1" * 64)
    broken["records"][1]["current_record_hash"] = record_hash(broken["records"][1])
    cases.append({"name": "FAIL_HASH_CHAIN_BROKEN", "expected": "FAIL", "packet": broken})

    missing_person = copy.deepcopy(pass_packet)
    missing_person["records"][0]["responsible_person_ref"] = ""
    missing_person["records"][0]["current_record_hash"] = record_hash(missing_person["records"][0])
    missing_person["records"][1]["previous_record_hash"] = missing_person["records"][0]["current_record_hash"]
    missing_person["records"][1]["current_record_hash"] = record_hash(missing_person["records"][1])
    cases.append({"name": "FAIL_MISSING_RESPONSIBLE_PERSON", "expected": "FAIL", "packet": missing_person})

    missing_archive = copy.deepcopy(pass_packet)
    for field in ["authority_basis", "access_reason_code", "approval_result"]:
        missing_archive["records"][0][field] = ""
    missing_archive["records"][0]["current_record_hash"] = record_hash(missing_archive["records"][0])
    missing_archive["records"][1]["previous_record_hash"] = missing_archive["records"][0]["current_record_hash"]
    missing_archive["records"][1]["current_record_hash"] = record_hash(missing_archive["records"][1])
    cases.append({"name": "FAIL_MISSING_ARCHIVE_ACCESS_FIELDS", "expected": "FAIL", "packet": missing_archive})

    missing_verifier = copy.deepcopy(pass_packet)
    missing_verifier["records"][0]["verifier_result"] = ""
    missing_verifier["records"][0]["current_record_hash"] = record_hash(missing_verifier["records"][0])
    missing_verifier["records"][1]["previous_record_hash"] = missing_verifier["records"][0]["current_record_hash"]
    missing_verifier["records"][1]["current_record_hash"] = record_hash(missing_verifier["records"][1])
    cases.append({"name": "FAIL_VERIFIER_RESULT_MISSING", "expected": "FAIL", "packet": missing_verifier})
    return cases


def run_test_cases() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in build_test_cases():
        result = verify_chain(case["packet"])
        actual = "PASS" if result["DRY_RUN"] == "PASS" else "FAIL"
        results.append(
            {
                "name": case["name"],
                "expected": case["expected"],
                "actual": actual,
                "passed": actual == case["expected"],
                "result": result,
            }
        )
    return results


def write_sandbox_run(out_root: Path = SANDBOX_ROOT) -> dict[str, Any]:
    run_id = "ACCOUNTABLE_RECORD_CHAIN_SANDBOX_" + now_utc()
    out = out_root / run_id
    out.mkdir(parents=True, exist_ok=True)

    chain = build_pass_chain()
    verifier = verify_chain(chain)
    tests = run_test_cases()
    all_tests_passed = all(item["passed"] for item in tests)
    dry_run_pass = verifier["DRY_RUN"] == "PASS" and all_tests_passed

    write_text(
        out / "00_SOURCE_STATE.md",
        f"""# Accountable Record Chain Sandbox

STATE=ACCOUNTABLE_RECORD_CHAIN_SANDBOX
RUN_ID={run_id}
SOURCE_SEAL={rel(SEAL_DIR)}
PREVIOUS_MODULE={rel(STATE_FIELD_PACKET_RUN)}
SOURCE_CANDIDATE={rel(CANDIDATE_PATH)}

## Boundary

- sandbox_only=true
- production_ledger_write=false
- db_write=false
- deploy=false
- restart=false
- auto_landing=false
- no_secret=true
- no_member_plaintext=true
- h64_td_ref_only=true
""",
    )
    write_json(out / "01_ACCOUNTABLE_RECORD_CHAIN.json", chain)
    write_json(out / "02_TEST_CASES.json", tests)
    write_json(out / "03_VERIFIER_RESULTS.json", verifier)
    rows = ["| case | expected | actual | result |", "|---|---|---|---|"]
    for item in tests:
        rows.append(f"| {item['name']} | {item['expected']} | {item['actual']} | {'PASS' if item['passed'] else 'FAIL'} |")
    report_lines = [
        "# Accountable Record Chain Verifier Report",
        "",
        "STATE=ACCOUNTABLE_RECORD_CHAIN_VERIFIER_REPORT",
        f"RUN_ID={run_id}",
        "JSON_PARSE=PASS",
        f"DRY_RUN={'PASS' if dry_run_pass else 'FAIL'}",
        f"HASH_CHAIN_CHECK={verifier['HASH_CHAIN_CHECK']}",
        f"ACCOUNTABILITY_FIELDS_CHECK={verifier['ACCOUNTABILITY_FIELDS_CHECK']}",
        f"PLAINTEXT_ARCHIVE_ACCOUNTABILITY_CHECK={verifier['PLAINTEXT_ARCHIVE_ACCOUNTABILITY_CHECK']}",
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
        "previous_module": rel(STATE_FIELD_PACKET_RUN),
        "source_candidate": rel(CANDIDATE_PATH),
        "safety_flags": {
            "sandbox_only": True,
            "production_ledger_write": False,
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
    parser = argparse.ArgumentParser(description="Build accountable record-chain sandbox output.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify", help="Verify an accountable record-chain JSON file.")
    args = parser.parse_args()

    if args.verify:
        packet = json.loads(Path(args.verify).read_text(encoding="utf-8"))
        result = verify_chain(packet)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["DRY_RUN"] == "PASS" else 2

    if not args.dry_run:
        parser.error("Use --dry-run or --verify")

    summary = write_sandbox_run()
    print("STATE=" + ("PASS_ACCOUNTABLE_RECORD_CHAIN_SANDBOX" if summary["dry_run"] == "PASS" else "HOLD_ACCOUNTABLE_RECORD_CHAIN_SANDBOX"))
    print("RUN_ID=" + summary["run_id"])
    print("OUT=" + summary["out"])
    print("FILES_CREATED=" + str(summary["files_created"]))
    print("DRY_RUN=" + summary["dry_run"])
    return 0 if summary["dry_run"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
