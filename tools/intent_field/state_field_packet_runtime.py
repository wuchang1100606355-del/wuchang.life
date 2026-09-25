#!/usr/bin/env python3
"""Sandbox-only state-field packet runtime builder."""

from __future__ import annotations

import argparse
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


DEFAULT_SEAL_DIR = ROOT / "runtime/total_field/verified_cloud_candidate_seal/VERIFIED_CLOUD_CANDIDATE_SEAL_20260704T215322Z"
DEFAULT_CANDIDATE = DEFAULT_SEAL_DIR / "RETURNED_CLOUD_CANDIDATE_RESPONSE.json"
SANDBOX_ROOT = ROOT / "runtime/total_field/state_field_packet_runtime_sandbox"
REQUIRED_PACKET_FIELDS = [
    "state_field_set_id",
    "state_field_version",
    "state_field_relation_table",
    "transition_trigger_code",
    "transition_reason_code",
    "before_state_field_hash",
    "after_state_field_hash",
    "dynamic_field_policy_id",
    "timestamp_coordinate",
    "verifier_result",
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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def read_candidate(path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    candidate, normalization = normalize_candidate_response(payload)
    return payload, candidate, normalization


def build_state_field_packet(candidate_path: Path = DEFAULT_CANDIDATE) -> dict[str, Any]:
    _payload, candidate, normalization = read_candidate(candidate_path)
    dynamic = candidate.get("dynamic_state_field", {})
    technical = candidate.get("technical_means", {})
    alignment = candidate.get("patent_type_alignment", {})
    index_db = candidate.get("spacetime_state_index_database", {})

    state_packet = {field: dynamic.get(field) for field in REQUIRED_PACKET_FIELDS}
    return {
        "packet_type": "state_field_packet_runtime_sandbox",
        "sandbox_only": True,
        "source_candidate_ref": {
            "path_ref": rel(candidate_path),
            "sha256": sha256_file(candidate_path),
        },
        "normalization": normalization,
        "patent_type_alignment": {
            "subject": alignment.get("independent_claim_subject", ""),
            "total_field_role": alignment.get("total_field_role", ""),
            "total_field_is_state_field": bool(alignment.get("total_field_is_state_field", False)),
        },
        "spacetime_state_index_database": {
            "generic_name": index_db.get("generic_name", ""),
            "owner_adi_allowed_as_implementation": bool(index_db.get("owner_adi_allowed_as_implementation", False)),
            "actual_index_rules_disclosed": bool(index_db.get("actual_index_rules_disclosed", False)),
        },
        "state_field_packet": state_packet,
        "technical_means": {key: technical.get(key, []) for key in TECHNICAL_MEANS_KEYS},
        "safety_boundary": {
            "db_write": False,
            "deploy": False,
            "restart": False,
            "auto_landing": False,
            "no_secret": True,
            "no_member_plaintext": True,
            "h64_td_ref_only": True,
        },
    }


def verify_packet(packet: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    state_packet = packet.get("state_field_packet", {})
    technical = packet.get("technical_means", {})
    alignment = packet.get("patent_type_alignment", {})
    index_db = packet.get("spacetime_state_index_database", {})
    text = json.dumps(packet, ensure_ascii=False, sort_keys=True)

    missing = [field for field in REQUIRED_PACKET_FIELDS if state_packet.get(field) in ("", None, [], {})]
    if missing:
        errors.append("MISSING_STATE_FIELD_PACKET_FIELDS:" + ",".join(missing))

    if "多個狀態場" not in text and "多狀態場" not in text:
        errors.append("FIELD_DRIFT_CHECK_FAIL:MISSING_MULTI_STATE_SUBJECT")
    if alignment.get("total_field_is_state_field") is True:
        errors.append("FIELD_DRIFT_CHECK_FAIL:TOTAL_FIELD_ROLE_DRIFT")

    if index_db.get("generic_name") != "時空狀態索引資料庫":
        errors.append("ADI_CHECK_FAIL:MISSING_GENERIC_INDEX_NAME")
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

    cleaned = text.replace("trade_secret_ref:h64_codebook", "").replace("trade_secret_ref:td_hash_runtime", "")
    cleaned = cleaned.replace("h64_td_ref_only", "")
    trade_secret_marker = "H64" + "-TD"
    protected_detail_terms = ["map" + "ping", "ta" + "ble", "ru" + "les"]
    if trade_secret_marker in cleaned and any(term in cleaned for term in protected_detail_terms):
        errors.append("H64_TD_REF_ONLY_FAIL")

    boundary = packet.get("safety_boundary", {})
    if boundary.get("db_write") is not False:
        errors.append("DB_WRITE_NOT_FALSE")
    if boundary.get("deploy") is not False:
        errors.append("DEPLOY_NOT_FALSE")
    if boundary.get("restart") is not False:
        errors.append("RESTART_NOT_FALSE")

    return {
        "JSON_PARSE": "PASS",
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


def write_sandbox_run(candidate_path: Path = DEFAULT_CANDIDATE, out_root: Path = SANDBOX_ROOT) -> dict[str, Any]:
    run_id = "STATE_FIELD_PACKET_RUNTIME_SANDBOX_" + now_utc()
    out = out_root / run_id
    out.mkdir(parents=True, exist_ok=True)

    packet = build_state_field_packet(candidate_path)
    result = verify_packet(packet)

    write_text(
        out / "00_SOURCE_STATE.md",
        f"""# State Field Packet Runtime Sandbox

STATE=STATE_FIELD_PACKET_RUNTIME_SANDBOX
RUN_ID={run_id}
SOURCE_SEAL={rel(DEFAULT_SEAL_DIR)}
SOURCE_CANDIDATE={rel(candidate_path)}

## Boundary

- sandbox_only=true
- db_write=false
- deploy=false
- restart=false
- auto_landing=false
- no_secret=true
- no_member_plaintext=true
- h64_td_ref_only=true
""",
    )
    write_json(out / "01_STATE_FIELD_PACKET_RUNTIME.json", packet)
    write_json(out / "02_VERIFIER_RESULTS.json", result)
    report_lines = [
        "# State Field Packet Runtime Verifier Report",
        "",
        "STATE=STATE_FIELD_PACKET_RUNTIME_VERIFIER_REPORT",
        f"RUN_ID={run_id}",
        f"JSON_PARSE={result['JSON_PARSE']}",
        f"DRY_RUN={result['DRY_RUN']}",
        f"FIELD_DRIFT_CHECK={result['FIELD_DRIFT_CHECK']}",
        f"ADI_CHECK={result['ADI_CHECK']}",
        f"TECHNICAL_MEANS_CHECK={result['TECHNICAL_MEANS_CHECK']}",
        f"NO_SECRET={result['NO_SECRET']}",
        f"NO_MEMBER_PLAINTEXT={result['NO_MEMBER_PLAINTEXT']}",
        f"H64_TD_REF_ONLY={result['H64_TD_REF_ONLY']}",
        "DB_WRITE=false",
        "DEPLOY=false",
        "RESTART=false",
        "ERRORS=" + ("NONE" if not result["ERRORS"] else ",".join(result["ERRORS"])),
        "",
    ]
    write_text(out / "VERIFIER_REPORT.md", "\n".join(report_lines))

    manifest = {
        "run_id": run_id,
        "created_at_utc": iso_now(),
        "source_seal": rel(DEFAULT_SEAL_DIR),
        "source_candidate": rel(candidate_path),
        "safety_flags": {
            "sandbox_only": True,
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
        "result": result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build state-field packet runtime sandbox output.")
    parser.add_argument("--candidate", default=str(DEFAULT_CANDIDATE))
    parser.add_argument("--out-root", default=str(SANDBOX_ROOT))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--packet-only", action="store_true")
    args = parser.parse_args()

    candidate_path = Path(args.candidate)
    if not candidate_path.is_absolute():
        candidate_path = ROOT / candidate_path

    if args.packet_only:
        print(json.dumps(build_state_field_packet(candidate_path), ensure_ascii=False, indent=2))
        return 0

    if not args.dry_run:
        parser.error("Use --dry-run or --packet-only")

    summary = write_sandbox_run(candidate_path, Path(args.out_root))
    result = summary["result"]
    print("STATE=" + ("PASS_STATE_FIELD_PACKET_RUNTIME_SANDBOX" if result["DRY_RUN"] == "PASS" else "HOLD_STATE_FIELD_PACKET_RUNTIME_SANDBOX"))
    print("RUN_ID=" + summary["run_id"])
    print("OUT=" + summary["out"])
    print("FILES_CREATED=" + str(summary["files_created"]))
    print("DRY_RUN=" + result["DRY_RUN"])
    return 0 if result["DRY_RUN"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
