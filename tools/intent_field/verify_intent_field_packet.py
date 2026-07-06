#!/usr/bin/env python3
"""Verify intent-field product completion dry-run outputs."""

from __future__ import annotations

import argparse
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


REQUIRED_JSON = [
    "03_INTENT_FIELD_COMPLETION_PACKET.json",
    "04_CLOUD_CANDIDATE_REQUEST.json",
    "cloud_candidate_request.json",
    "intent_field_construction_packet.json",
]
REQUIRED_FILES = [
    "00_SYSTEM_SEARCH_INDEX.md",
    "01_PATENT_TARGET_EXTRACTION.md",
    "02_CURRENT_SYSTEM_CAPABILITY_MATRIX.md",
    "03_INTENT_FIELD_COMPLETION_PACKET.json",
    "04_CLOUD_CANDIDATE_REQUEST.json",
    "05_REDTEAM_FINDINGS.md",
    "06_OPTIMIZATION_PLAN.md",
    "07_ONE_CLICK_LAUNCH_PREFLIGHT.md",
    "08_VERIFIER_REPORT.md",
    "MANIFEST.json",
]
STATE_PACKET_REQUIRED_FIELDS = {
    "state_packet_id",
    "candidate_action_id",
    "identity_proxy_ref",
    "authority_scope_code",
    "consent_state_code",
    "reference_code",
    "coordinate_code",
    "hash_value",
    "mask_code",
    "permission_code",
    "state_code",
    "verifier_result",
    "risk_code",
    "rule_version",
    "timestamp_coordinate",
}
ACCOUNTABLE_ACCESS_FIELDS = {
    "plaintext_archive_ref",
    "access_request_id",
    "requester_identity_ref",
    "responsible_person_ref",
    "authority_basis",
    "access_reason_code",
    "rule_version",
    "approval_result",
    "timestamp_coordinate",
    "previous_record_hash",
    "current_record_hash",
}
IDENTITY_AGENT_FIELDS = {
    "identity_proxy_ref",
    "authority_scope_code",
    "consent_state_code",
    "device_binding_ref",
    "agent_binding_ref",
    "responsible_person_ref",
    "access_request_id",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def generated_text(out: Path) -> str:
    parts = []
    for path in sorted(out.iterdir()):
        if path.is_file() and path.suffix in {".json", ".md", ".txt"}:
            parts.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(parts)


def disallowed_h64_text(text: str) -> bool:
    allowed = text
    allowed = allowed.replace("trade_secret_ref:h64_codebook", "")
    allowed = allowed.replace("trade_secret_ref:td_hash_runtime", "")
    allowed = allowed.replace("H64_TD_REF_ONLY", "")
    allowed = allowed.replace("h64_td_ref_only", "")
    if re.search(r"(?i)H64[-_ ]?TD.*(mapping|table|rules|codebook|WHY_IT_RUNS)", allowed):
        return True
    if re.search(r"(?i)(mapping|table|rules|WHY_IT_RUNS).*H64[-_ ]?TD", allowed):
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify intent-field preflight output directory.")
    parser.add_argument("run_dir")
    args = parser.parse_args()
    out = Path(args.run_dir)
    if not out.is_absolute():
        out = ROOT / out

    errors: list[str] = []
    for name in REQUIRED_FILES:
        if not (out / name).is_file():
            errors.append(f"MISSING_FILE:{name}")

    json_objects: dict[str, Any] = {}
    for name in REQUIRED_JSON:
        try:
            json_objects[name] = load_json(out / name)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"JSON_PARSE_FAIL:{name}:{exc.__class__.__name__}")

    full = json_objects.get("cloud_candidate_request.json", {})
    completion = json_objects.get("03_INTENT_FIELD_COMPLETION_PACKET.json", {})
    minimal = json_objects.get("04_CLOUD_CANDIDATE_REQUEST.json", {})
    all_text = generated_text(out)

    field_lock = full.get("field_lock", {})
    field_drift_ok = (
        field_lock.get("total_field_is_state_field") is False
        and "多個狀態場/多狀態場" in json.dumps(full, ensure_ascii=False)
        and "八欄位" not in all_text
    )
    if not field_drift_ok:
        errors.append("FIELD_DRIFT_CHECK_FAIL")

    adi_ok = (
        "時空狀態索引資料庫" in all_text
        and "政府 ADI" not in all_text
        and "智慧城鄉" not in all_text
        and full.get("spacetime_state_index_database", {}).get("generic_name") == "時空狀態索引資料庫"
    )
    if not adi_ok:
        errors.append("ADI_CHECK_FAIL")

    patent_lock = full.get("patent_type_conformity_lock", {})
    patent_type_ok = (
        patent_lock.get("enabled") is True
        and patent_lock.get("patent_type") == "人工智慧候選行動之多狀態場封包化控管方法、系統及非暫態電腦可讀取媒體"
        and set(patent_lock.get("candidate_output_sections", [])) >= {
            "patent_type_alignment",
            "product_completion_plan",
            "claim_support_matrix",
            "forbidden_output_check",
        }
    )
    if not patent_type_ok:
        errors.append("PATENT_TYPE_CONFORMITY_CHECK_FAIL")

    tech = full.get("technical_means_lock", {})
    technical_ok = set(tech.get("required_means", [])) >= {
        "module",
        "data_structure",
        "packet_field",
        "verification_condition",
        "blocking_condition",
        "record_field",
        "reconstruction_flow",
    }
    if not technical_ok:
        errors.append("TECHNICAL_MEANS_CHECK_FAIL")

    identity = full.get("sovereign_identity_agent", {})
    privacy_ok = (
        IDENTITY_AGENT_FIELDS <= set(identity)
        and ACCOUNTABLE_ACCESS_FIELDS <= set(full.get("accountable_access_record_fields", []))
        and full.get("isolated_plaintext_archive_boundary", {}).get("excluded_from_external_model_input") is True
        and full.get("isolated_plaintext_archive_boundary", {}).get("excluded_from_state_packet") is True
    )
    if not privacy_ok:
        errors.append("PRIVACY_ACCOUNTABILITY_CHECK_FAIL")

    cloud = full.get("cloud_authority_boundary", {})
    cloud_ok = (
        cloud.get("cloud_candidate_only") is True
        and cloud.get("total_field_final_authority") is True
        and cloud.get("external_model_can_execute_business_system") is False
        and cloud.get("cloud_call_executed") is False
        and cloud.get("db_write") is False
        and cloud.get("deploy") is False
        and cloud.get("restart") is False
        and minimal.get("status_code") == "DRY_RUN_CLOUD_CANDIDATE_ONLY"
    )
    if not cloud_ok:
        errors.append("CLOUD_AUTHORITY_CHECK_FAIL")

    packet_fields = set(full.get("candidate_request", {}).get("state_packet_required_fields", []))
    if not STATE_PACKET_REQUIRED_FIELDS <= packet_fields:
        errors.append("STATE_PACKET_REQUIRED_FIELDS_FAIL")

    scan = scan_text(all_text)
    no_secret = scan["status"] == "PASS"
    if not no_secret:
        errors.append("NO_SECRET_FAIL")

    member_assignment = re.search(
        r"(?i)(member_plaintext_value|identifiable_person_plaintext|plaintext_identity)\s*[:=]\s*[^,\n}\]]+",
        all_text,
    )
    taiwan_id_like = re.search(r"(?<![A-Za-z0-9])[A-Z][12]\d{8}(?![A-Za-z0-9])", all_text)
    phone_like = re.search(r"(?<![A-Fa-f0-9])09\d{2}[- ]?\d{3}[- ]?\d{3}(?![A-Fa-f0-9])", all_text)
    member_plaintext_ok = not (member_assignment or taiwan_id_like or phone_like)
    if not member_plaintext_ok:
        errors.append("NO_MEMBER_PLAINTEXT_FAIL")

    h64_ok = not disallowed_h64_text(all_text)
    if not h64_ok:
        errors.append("H64_TD_REF_ONLY_FAIL")

    json_parse_ok = not any(item.startswith("JSON_PARSE_FAIL") for item in errors)
    final_decision = "PASS" if not errors else "HOLD"
    checks = {
        "json_parse": "PASS" if json_parse_ok else "FAIL",
        "field_drift_check": "PASS" if field_drift_ok else "FAIL",
        "adi_check": "PASS" if adi_ok else "FAIL",
        "technical_means_check": "PASS" if technical_ok else "FAIL",
        "no_secret": "PASS" if no_secret else "FAIL",
        "no_member_plaintext": "PASS" if member_plaintext_ok else "FAIL",
        "h64_td_ref_only": "PASS" if h64_ok else "FAIL",
        "cloud_candidate_only": "PASS" if cloud_ok else "FAIL",
        "patent_type_conformity": "PASS" if patent_type_ok else "FAIL",
    }
    verification = {
        "run_id": completion.get("run_id") or full.get("run_id") or out.name,
        "state": "TOTAL_FIELD_CANDIDATE_VERIFICATION",
        "checks": checks,
        "errors": errors,
        "final_decision": final_decision,
        "cloud_call_executed": False,
        "db_write": False,
        "deploy": False,
        "restart": False,
    }
    (out / "total_field_candidate_verification.json").write_text(
        json.dumps(verification, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report = f"""# Verifier Report

STATE=TOTAL_FIELD_CANDIDATE_VERIFICATION
FIELD_DRIFT_CHECK={checks['field_drift_check']}
ADI_CHECK={checks['adi_check']}
PATENT_TYPE_CONFORMITY_CHECK={checks['patent_type_conformity']}
TECHNICAL_MEANS_CHECK={checks['technical_means_check']}
PRIVACY_ACCOUNTABILITY_CHECK={'PASS' if privacy_ok else 'FAIL'}
CLOUD_AUTHORITY_CHECK={checks['cloud_candidate_only']}
NO_SECRET={checks['no_secret']}
NO_MEMBER_PLAINTEXT={checks['no_member_plaintext']}
H64_TD_REF_ONLY={checks['h64_td_ref_only']}
NO_DB_WRITE=true
NO_DEPLOY=true
NO_RESTART=true
FINAL_DECISION={final_decision}
ERRORS={','.join(errors) if errors else 'NONE'}
"""
    (out / "08_VERIFIER_REPORT.md").write_text(report, encoding="utf-8")

    manifest_path = out / "MANIFEST.json"
    manifest = load_json(manifest_path) if manifest_path.exists() else {}
    output_files = {}
    for path in sorted(out.iterdir()):
        if path.is_file() and path.name != "MANIFEST.json":
            output_files[path.name] = __import__("hashlib").sha256(path.read_bytes()).hexdigest()
    manifest["output_files"] = output_files
    manifest["redteam_status"] = "PASS_PREFLIGHT_WITH_REVIEW_ITEMS" if final_decision == "PASS" else "HOLD"
    manifest["final_decision"] = final_decision
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    final_paste = f"""STATE={'PASS_INTENT_FIELD_PRODUCT_COMPLETION_WITH_REPO_SEARCH_AND_REDTEAM' if final_decision == 'PASS' else 'HOLD_INTENT_FIELD_PRODUCT_COMPLETION_WITH_REPO_SEARCH_AND_REDTEAM'}
RUN_ID={verification['run_id']}
OUT={out.relative_to(ROOT)}
FILES_CREATED={len(output_files) + 1}
SYSTEM_SEARCH={'PASS' if (out / '00_SYSTEM_SEARCH_INDEX.md').exists() else 'FAIL'}
PATENT_TARGET_EXTRACTION={'PASS' if (out / '01_PATENT_TARGET_EXTRACTION.md').exists() else 'FAIL'}
CAPABILITY_MATRIX={'PASS' if (out / '02_CURRENT_SYSTEM_CAPABILITY_MATRIX.md').exists() else 'FAIL'}
REDTEAM={'PASS_WITH_REVIEW_ITEMS' if final_decision == 'PASS' else 'HOLD'}
OPTIMIZATION_PLAN={'PASS' if (out / '06_OPTIMIZATION_PLAN.md').exists() else 'FAIL'}
FIELD_DRIFT_CHECK={checks['field_drift_check']}
ADI_CHECK={checks['adi_check']}
PATENT_TYPE_CONFORMITY_CHECK={checks['patent_type_conformity']}
TECHNICAL_MEANS_CHECK={checks['technical_means_check']}
PRIVACY_ACCOUNTABILITY_CHECK={'PASS' if privacy_ok else 'FAIL'}
CLOUD_AUTHORITY_CHECK={checks['cloud_candidate_only']}
NO_SECRET={checks['no_secret']}
NO_MEMBER_PLAINTEXT={checks['no_member_plaintext']}
H64_TD_REF_ONLY={checks['h64_td_ref_only']}
DB_WRITE=false
DEPLOY=false
RESTART=false
NEXT=人工確認 04_CLOUD_CANDIDATE_REQUEST.json 後，可用 ref-only 方式發射雲端候選補全；不得自動落地。
"""
    (out / "FINAL_PASTE_BACK.txt").write_text(final_paste, encoding="utf-8")

    try:
        rel_out = out.relative_to(ROOT / "runtime/total_field/intent_field_product_completion")
        construction_out = ROOT / "runtime/total_field/intent_field_construction" / rel_out
    except ValueError:
        construction_out = None
    if construction_out and construction_out.exists():
        for name in ["total_field_candidate_verification.json", "08_VERIFIER_REPORT.md", "FINAL_PASTE_BACK.txt"]:
            src = out / name
            if src.exists():
                (construction_out / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        construction_manifest = manifest.copy()
        construction_outputs = {}
        for path in sorted(construction_out.iterdir()):
            if path.is_file() and path.name != "MANIFEST.json":
                construction_outputs[path.name] = __import__("hashlib").sha256(path.read_bytes()).hexdigest()
        construction_manifest["output_files"] = construction_outputs
        (construction_out / "MANIFEST.json").write_text(
            json.dumps(construction_manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(final_paste, end="")
    return 0 if final_decision == "PASS" else 4


if __name__ == "__main__":
    raise SystemExit(main())
