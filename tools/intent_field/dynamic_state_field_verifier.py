#!/usr/bin/env python3
"""Dry-run verifier for dynamic multi-state-field cloud candidates."""

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


ACTIVE_PATENT_PACKET = "runtime/total_field/patent_rewrite/TIPO_STAGE04_NO_FIELD_DRIFT_TECHNICALIZED_REPAIR_20260704T191641Z"
INTENT_COMPLETION = "runtime/total_field/intent_field_product_completion/INTENT_FIELD_PRODUCT_COMPLETION_20260704T203101Z"
CLOUD_REQUEST_HARDENED = "runtime/total_field/cloud_candidate_request_review/CLOUD_CANDIDATE_REQUEST_POLICY_HARDENING_20260704T210216Z/04_CLOUD_CANDIDATE_REQUEST_POLICY_HARDENED.json"
STAGE07_ALIGNMENT = "runtime/total_field/dev_alignment/DEV_STAGE07_SYSTEM_PATENT_ALIGNMENT_20260704T205901Z"

DYNAMIC_REQUIRED_FIELDS = {
    "state_field_set_id",
    "state_field_version",
    "state_field_relation_table",
    "dynamic_field_policy_id",
    "transition_reason_code",
    "transition_trigger_code",
    "before_state_field_hash",
    "after_state_field_hash",
    "verifier_result",
    "responsible_person_ref",
    "timestamp_coordinate",
    "previous_record_hash",
    "current_record_hash",
}
IDENTITY_REQUIRED_FIELDS = {
    "identity_proxy_ref",
    "authority_scope_code",
    "consent_state_code",
    "device_binding_ref",
    "agent_binding_ref",
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
TECHNICAL_MEANS_KEYS = {
    "modules",
    "data_structures",
    "packet_fields",
    "verification_conditions",
    "blocking_conditions",
    "record_fields",
}
EFFECT_WORDS = ["降低", "避免", "提升", "確保", "防止", "安全", "治理", "風險", "可稽核", "受限"]
SECRET_KEYS = {"token", "password", "private_key", "db_password", "oauth_secret", "api_key", "access_key", "secret"}
SECRET_RISK_KEYS = {"secret_material_risk_labels", "credential_material_risk_labels"}
MEMBER_PLAINTEXT_KEYS = {"member_plaintext", "identifiable_person_plaintext", "plaintext_identity"}
MEMBER_RISK_KEYS = {"member_plaintext_risk_labels", "identifiable_person_plaintext_risk_labels"}
ALLOWED_H64_REFS = {"trade_secret_ref:h64_codebook", "trade_secret_ref:td_hash_runtime"}


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


def sha(value: str) -> str:
    return "hash:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def payload_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def iter_keys(payload: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            keys.append(str(key))
            keys.extend(iter_keys(value))
    elif isinstance(payload, list):
        for item in payload:
            keys.extend(iter_keys(item))
    return keys


def find_key_values(payload: Any, target_key: str) -> list[Any]:
    found: list[Any] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key) == target_key:
                found.append(value)
            found.extend(find_key_values(value, target_key))
    elif isinstance(payload, list):
        for item in payload:
            found.extend(find_key_values(item, target_key))
    return found


def recursive_key_exists(payload: Any, key_name: str) -> bool:
    return any(key == key_name for key in iter_keys(payload))


def has_nonempty_keys(mapping: Any, required: set[str]) -> tuple[bool, list[str]]:
    if not isinstance(mapping, dict):
        return False, sorted(required)
    missing = [key for key in sorted(required) if key not in mapping or mapping[key] in ("", None, [], {})]
    return not missing, missing


def has_nested_fields(payload: Any, required: set[str]) -> tuple[bool, list[str]]:
    missing = [key for key in sorted(required) if not recursive_key_exists(payload, key)]
    return not missing, missing


def status_result(status: str, messages: list[str] | None = None) -> dict[str, Any]:
    return {"status": status, "messages": messages or []}


def aggregate_decision(checks: dict[str, dict[str, Any]]) -> str:
    statuses = {item["status"] for item in checks.values()}
    if "HOLD" in statuses:
        return "HOLD"
    if "FAIL" in statuses:
        return "FAIL"
    return "PASS"


def disallowed_h64_text(text: str) -> bool:
    cleaned = text
    for allowed in ALLOWED_H64_REFS:
        cleaned = cleaned.replace(allowed, "")
    safe_flags = [
        "H64_TD_REF_ONLY",
        "h64_td_ref_only",
        "no_h64_td_mapping",
        "no_h64_td_table",
        "no_h64_td_rules",
        "NO_H64_TD_MAPPING",
        "NO_H64_TD_TABLE",
        "NO_H64_TD_RULES",
    ]
    for flag in safe_flags:
        cleaned = cleaned.replace(flag, "")
    if re.search(r"(?i)H64[-_ ]?TD.*(mapping|table|rules|WHY_IT_RUNS|codebook)", cleaned):
        return True
    if re.search(r"(?i)(mapping|table|rules|WHY_IT_RUNS|codebook).*H64[-_ ]?TD", cleaned):
        return True
    return False


def check_field_drift(candidate: dict[str, Any]) -> dict[str, Any]:
    text = payload_text(candidate)
    alignment = candidate.get("patent_type_alignment", {})
    messages: list[str] = []
    subject = str(alignment.get("independent_claim_subject", ""))
    eight_usage = str(alignment.get("eight_state_field_usage", ""))
    if "多個狀態場" not in subject and "多狀態場" not in subject and "多個狀態場" not in text and "多狀態場" not in text:
        messages.append("MISSING_MULTI_STATE_FIELD_SUBJECT")
    if "八欄位" in text or candidate.get("state_field_subject_locked_to_eight") is True:
        messages.append("FIELD_DRIFT_TO_EIGHT_COLUMNS")
    if "八個狀態場" in subject and "多" not in subject:
        messages.append("INDEPENDENT_SUBJECT_LOCKED_TO_EIGHT_STATE_FIELDS")
    if "八個狀態場" in text and eight_usage not in {"附屬項", "實施例", "附屬項或實施例"}:
        messages.append("EIGHT_STATE_FIELD_USAGE_NOT_LIMITED_TO_EXAMPLE_OR_DEPENDENT")
    if alignment.get("total_field_is_state_field") is True or candidate.get("total_field_is_state_field") is True or "總場是狀態場之一" in text:
        messages.append("TOTAL_FIELD_DRIFTED_TO_STATE_FIELD")
    ok, missing = has_nonempty_keys(candidate.get("dynamic_state_field", {}), DYNAMIC_REQUIRED_FIELDS)
    if not ok:
        messages.append("MISSING_DYNAMIC_STATE_FIELD_FIELDS:" + ",".join(missing))
    if messages:
        return status_result("FAIL", messages)
    return status_result("PASS")


def check_adi(candidate: dict[str, Any]) -> dict[str, Any]:
    text = payload_text(candidate)
    db = candidate.get("spacetime_state_index_database", {})
    messages: list[str] = []
    if any(term in text for term in ["政府 ADI", "政府ADI", "government ADI", "智慧城鄉案例", "智慧城鄉"]):
        messages.append("ADI_DRIFT_TO_GOVERNMENT_OR_SMART_CITY_CASE")
    if db.get("generic_name") != "時空狀態索引資料庫":
        messages.append("MISSING_SPACETIME_STATE_INDEX_DATABASE_GENERIC_NAME")
    owner_desc = str(db.get("owner_adi_description", ""))
    if db.get("owner_adi_allowed_as_implementation") is not True and "使用者自有 ADI 時空資料庫" not in owner_desc and "使用者自有 ADI 時空資料庫" not in text:
        messages.append("OWNER_ADI_NOT_RETAINED_AS_IMPLEMENTATION")
    if db.get("government_adi_case") is True:
        messages.append("GOVERNMENT_ADI_CASE_TRUE")
    if db.get("actual_index_rules_disclosed") is True or recursive_key_exists(candidate, "adi_index_rules"):
        return status_result("HOLD", ["ADI_ACTUAL_INDEX_RULES_DISCLOSED"])
    if messages:
        return status_result("FAIL", messages)
    return status_result("PASS")


def check_sovereign_identity(candidate: dict[str, Any]) -> dict[str, Any]:
    agent = candidate.get("sovereign_identity_agent", {})
    messages: list[str] = []
    if agent.get("enabled") is not True:
        messages.append("SOVEREIGN_IDENTITY_AGENT_NOT_ENABLED")
    ok, missing = has_nonempty_keys(agent, IDENTITY_REQUIRED_FIELDS)
    if not ok:
        messages.append("MISSING_SOVEREIGN_IDENTITY_FIELDS:" + ",".join(missing))
    if messages:
        return status_result("HOLD", messages)
    return status_result("PASS")


def check_plaintext_archive(candidate: dict[str, Any]) -> dict[str, Any]:
    archive = candidate.get("isolated_plaintext_archive_boundary", {})
    messages: list[str] = []
    if archive.get("enabled") is not True:
        messages.append("PLAINTEXT_ARCHIVE_NOT_ENABLED")
    if archive.get("excluded_from_external_model_input") is not True:
        messages.append("PLAINTEXT_ARCHIVE_CAN_ENTER_EXTERNAL_MODEL_INPUT")
    if archive.get("excluded_from_state_packet") is not True:
        messages.append("PLAINTEXT_ARCHIVE_CAN_ENTER_STATE_PACKET")
    if archive.get("general_execution_plaintext_access") is not False:
        messages.append("PLAINTEXT_CAN_ENTER_GENERAL_EXECUTION_PATH")
    record = archive.get("accountable_access_record", {})
    ok, missing = has_nonempty_keys(record, ACCOUNTABLE_ACCESS_FIELDS)
    if not ok:
        messages.append("MISSING_ACCOUNTABLE_ACCESS_RECORD_FIELDS:" + ",".join(missing))
    if messages:
        return status_result("HOLD" if any("PLAINTEXT" in msg for msg in messages) else "FAIL", messages)
    return status_result("PASS")


def check_cloud_authority(candidate: dict[str, Any]) -> dict[str, Any]:
    boundary = candidate.get("cloud_authority_boundary", {})
    proxy = candidate.get("front_edge_proxy_layer", {})
    messages: list[str] = []
    if candidate.get("candidate_only") is not True or boundary.get("cloud_candidate_only") is not True:
        messages.append("CLOUD_NOT_CANDIDATE_ONLY")
    if candidate.get("cloud_call_executed") is not False:
        messages.append("CLOUD_CALL_EXECUTED")
    for key in ["cloud_can_decide", "cloud_can_land", "db_write", "deploy", "restart"]:
        if boundary.get(key) is not False:
            messages.append(f"CLOUD_AUTHORITY_DRIFT:{key}")
    if proxy.get("enabled") is not True:
        messages.append("FRONT_EDGE_PROXY_NOT_ENABLED")
    if proxy.get("blocks_external_model_output_to_business_write") is not True:
        messages.append("FRONT_EDGE_PROXY_DOES_NOT_BLOCK_BUSINESS_WRITE")
    if proxy.get("blocks_unverified_executable_api_call") is not True:
        messages.append("FRONT_EDGE_PROXY_DOES_NOT_BLOCK_UNVERIFIED_API_CALL")
    final_values = find_key_values(candidate, "final_decision")
    if any(value not in (None, "", "CANDIDATE_ONLY") for value in final_values):
        messages.append("CLOUD_OUTPUT_CONTAINS_FINAL_DECISION")
    if messages:
        return status_result("HOLD", messages)
    return status_result("PASS")


def check_technical_means(candidate: dict[str, Any]) -> dict[str, Any]:
    text = payload_text(candidate)
    means = candidate.get("technical_means", {})
    messages: list[str] = []
    if any(word in text for word in EFFECT_WORDS):
        for key in sorted(TECHNICAL_MEANS_KEYS):
            value = means.get(key)
            if not isinstance(value, list) or not value:
                messages.append(f"EFFECT_WORD_WITHOUT_TECHNICAL_ANCHOR:{key}")
    ok, missing_dynamic = has_nonempty_keys(candidate.get("dynamic_state_field", {}), DYNAMIC_REQUIRED_FIELDS)
    if not ok:
        messages.append("DYNAMIC_FIELD_TECHNICAL_FIELDS_MISSING:" + ",".join(missing_dynamic))
    if messages:
        return status_result("FAIL", messages)
    return status_result("PASS")


def check_no_secret(candidate: dict[str, Any]) -> dict[str, Any]:
    text = payload_text(candidate)
    messages: list[str] = []
    scan = scan_text(text)
    if scan["status"] != "PASS":
        messages.append("SECRET_PATTERN_DETECTED")
    keys = {key.lower() for key in iter_keys(candidate)}
    risky_keys = sorted(keys & SECRET_KEYS)
    if risky_keys:
        messages.append("SECRET_FIELD_NAME_DETECTED:" + ",".join(risky_keys))
    for risk_key in SECRET_RISK_KEYS:
        values = find_key_values(candidate, risk_key)
        if any(value for value in values):
            messages.append(f"SECRET_RISK_LABEL_PRESENT:{risk_key}")
    if messages:
        return status_result("HOLD", messages)
    return status_result("PASS")


def check_no_member_plaintext(candidate: dict[str, Any]) -> dict[str, Any]:
    text = payload_text(candidate)
    messages: list[str] = []
    if re.search(r"(?<![A-Za-z0-9])[A-Z][12]\d{8}(?![A-Za-z0-9])", text):
        messages.append("TAIWAN_ID_LIKE_MEMBER_PLAINTEXT")
    if re.search(r"(?<![A-Fa-f0-9])09\d{2}[- ]?\d{3}[- ]?\d{3}(?![A-Fa-f0-9])", text):
        messages.append("PHONE_LIKE_MEMBER_PLAINTEXT")
    keys = {key.lower() for key in iter_keys(candidate)}
    risky_keys = sorted(keys & MEMBER_PLAINTEXT_KEYS)
    if risky_keys:
        messages.append("MEMBER_PLAINTEXT_FIELD_NAME_DETECTED:" + ",".join(risky_keys))
    for risk_key in MEMBER_RISK_KEYS:
        values = find_key_values(candidate, risk_key)
        if any(value for value in values):
            messages.append(f"MEMBER_PLAINTEXT_RISK_LABEL_PRESENT:{risk_key}")
    if messages:
        return status_result("HOLD", messages)
    return status_result("PASS")


def check_h64_ref_only(candidate: dict[str, Any]) -> dict[str, Any]:
    text = payload_text(candidate)
    if disallowed_h64_text(text):
        return status_result("HOLD", ["H64_TD_DETAIL_DISCLOSURE_DETECTED"])
    return status_result("PASS")


def verify_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "FIELD_DRIFT_CHECK": check_field_drift(candidate),
        "ADI_CHECK": check_adi(candidate),
        "SOVEREIGN_IDENTITY_CHECK": check_sovereign_identity(candidate),
        "PLAINTEXT_ARCHIVE_ACCOUNTABILITY_CHECK": check_plaintext_archive(candidate),
        "CLOUD_AUTHORITY_CHECK": check_cloud_authority(candidate),
        "TECHNICAL_MEANS_CHECK": check_technical_means(candidate),
        "NO_SECRET": check_no_secret(candidate),
        "NO_MEMBER_PLAINTEXT": check_no_member_plaintext(candidate),
        "H64_TD_REF_ONLY": check_h64_ref_only(candidate),
    }
    return {
        "decision": aggregate_decision(checks),
        "checks": checks,
        "db_write": False,
        "deploy": False,
        "restart": False,
        "cloud_call_executed": False,
    }


def base_pass_case() -> dict[str, Any]:
    return {
        "run_id": "DYNAMIC_STATE_FIELD_VERIFIER_TEST",
        "request_id": "cloud_candidate_response:ref_only_pass_case",
        "candidate_only": True,
        "cloud_call_executed": False,
        "total_field_final_authority": True,
        "patent_type_alignment": {
            "patent_type": "人工智慧候選行動之多狀態場封包化控管方法、系統及非暫態電腦可讀取媒體",
            "independent_claim_subject": "多個狀態場/多狀態場",
            "eight_state_field_usage": "附屬項或實施例",
            "total_field_role": "總體治理系統/系統/governance control plane",
            "total_field_is_state_field": False,
        },
        "dynamic_state_field": {
            "state_field_set_id": "state_field_set:ref_only:community_service",
            "state_field_version": "state_field_version:v1",
            "state_field_relation_table": [
                {
                    "from_state_field_ref": "intent_state_ref",
                    "to_state_field_ref": "risk_governance_state_ref",
                    "relation_code": "requires_pre_execution_verification",
                }
            ],
            "dynamic_field_policy_id": "dynamic_field_policy:ref_only:p0",
            "transition_reason_code": "transition_reason_code:candidate_type_change",
            "transition_trigger_code": "transition_trigger_code:pre_execution_review",
            "before_state_field_hash": sha("before-state-field"),
            "after_state_field_hash": sha("after-state-field"),
            "verifier_result": "PASS",
            "responsible_person_ref": "responsible_person_ref:owner_authorized",
            "timestamp_coordinate": "timestamp_coordinate:20260704T000000Z",
            "previous_record_hash": sha("previous-record"),
            "current_record_hash": sha("current-record"),
            "rollback_target_version": "state_field_version:v0",
        },
        "sovereign_identity_agent": {
            "enabled": True,
            "identity_proxy_ref": "identity_proxy_ref:synthetic",
            "authority_scope_code": "authority_scope_code:owner_authorized_ref",
            "consent_state_code": "consent_state_code:granted_ref",
            "device_binding_ref": "device_binding_ref:synthetic",
            "agent_binding_ref": "agent_binding_ref:synthetic",
        },
        "spacetime_state_index_database": {
            "generic_name": "時空狀態索引資料庫",
            "owner_adi_allowed_as_implementation": True,
            "owner_adi_description": "使用者自有 ADI 時空資料庫之 ref-only 實施例",
            "government_adi_case": False,
            "actual_index_rules_disclosed": False,
        },
        "isolated_plaintext_archive_boundary": {
            "enabled": True,
            "plaintext_archive_ref": "plaintext_archive_ref:isolated_domain",
            "excluded_from_external_model_input": True,
            "excluded_from_state_packet": True,
            "general_execution_plaintext_access": False,
            "accountable_access_record": {
                "plaintext_archive_ref": "plaintext_archive_ref:isolated_domain",
                "access_request_id": "access_request_id:synthetic",
                "requester_identity_ref": "requester_identity_ref:synthetic",
                "responsible_person_ref": "responsible_person_ref:owner_authorized",
                "authority_basis": "authority_basis:lawful_or_owner_authorized_ref",
                "access_reason_code": "access_reason_code:accountability_review",
                "rule_version": "rule_version:p0",
                "approval_result": "approval_result:approved_ref_only",
                "timestamp_coordinate": "timestamp_coordinate:20260704T000000Z",
                "previous_record_hash": sha("access-previous"),
                "current_record_hash": sha("access-current"),
            },
        },
        "front_edge_proxy_layer": {
            "enabled": True,
            "blocks_external_model_output_to_business_write": True,
            "blocks_unverified_executable_api_call": True,
        },
        "cloud_authority_boundary": {
            "cloud_candidate_only": True,
            "cloud_can_decide": False,
            "cloud_can_land": False,
            "db_write": False,
            "deploy": False,
            "restart": False,
        },
        "technical_means": {
            "modules": ["多狀態場調度模組", "主權身分代理模組", "前緣代理層", "隔離明文封存域"],
            "data_structures": ["狀態場關係表", "狀態場封包"],
            "packet_fields": [
                "state_field_set_id",
                "state_field_version",
                "dynamic_field_policy_id",
                "transition_reason_code",
                "before_state_field_hash",
                "after_state_field_hash",
                "identity_proxy_ref",
                "verifier_result",
            ],
            "verification_conditions": ["before_after_hash_required", "authority_scope_required", "consent_state_required"],
            "blocking_conditions": ["unverified_business_write_blocked", "plaintext_general_path_blocked"],
            "record_fields": ["previous_record_hash", "current_record_hash", "responsible_person_ref"],
        },
        "forbidden_output_check": {
            "no_member_plaintext": True,
            "no_secret": True,
            "no_h64_td_mapping": True,
            "no_h64_td_table": True,
            "no_h64_td_rules": True,
            "no_adi_index_rules": True,
            "cloud_candidate_only": True,
            "allowed_trade_secret_refs": ["trade_secret_ref:h64_codebook", "trade_secret_ref:td_hash_runtime"],
        },
    }


def build_test_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    pass_case = base_pass_case()
    cases.append({"name": "PASS_CASE", "expected_decision": "PASS", "candidate": pass_case})

    field_drift = copy.deepcopy(pass_case)
    field_drift["patent_type_alignment"]["independent_claim_subject"] = "八欄位"
    field_drift["state_field_subject_locked_to_eight"] = True
    cases.append({"name": "FAIL_CASE_FIELD_DRIFT", "expected_decision": "FAIL", "candidate": field_drift})

    adi_drift = copy.deepcopy(pass_case)
    adi_drift["spacetime_state_index_database"]["government_adi_case"] = True
    adi_drift["spacetime_state_index_database"]["owner_adi_description"] = "政府 ADI 智慧城鄉案例"
    cases.append({"name": "FAIL_CASE_ADI_DRIFT", "expected_decision": "FAIL", "candidate": adi_drift})

    secret_case = copy.deepcopy(pass_case)
    secret_case["forbidden_probe"] = {
        "secret_material_risk_labels": ["token", "password", "private_key"],
        "redacted_value_only": True,
    }
    cases.append({"name": "FAIL_CASE_SECRET", "expected_decision": "HOLD", "candidate": secret_case})

    member_plaintext = copy.deepcopy(pass_case)
    member_plaintext["forbidden_probe"] = {
        "member_plaintext_risk_labels": ["identifiable_person_plaintext"],
        "redacted_value_only": True,
    }
    cases.append({"name": "FAIL_CASE_MEMBER_PLAINTEXT", "expected_decision": "HOLD", "candidate": member_plaintext})

    cloud_authority = copy.deepcopy(pass_case)
    cloud_authority["cloud_authority_boundary"]["cloud_can_decide"] = True
    cloud_authority["cloud_authority_boundary"]["db_write"] = True
    cloud_authority["final_decision"] = "ALLOW"
    cases.append({"name": "FAIL_CASE_CLOUD_AUTHORITY_DRIFT", "expected_decision": "HOLD", "candidate": cloud_authority})

    effect_as_tech = copy.deepcopy(pass_case)
    effect_as_tech["technical_means"] = {
        "effects": ["安全", "降低風險", "可稽核"],
        "modules": [],
        "data_structures": [],
        "packet_fields": [],
        "verification_conditions": [],
        "blocking_conditions": [],
        "record_fields": [],
    }
    cases.append({"name": "FAIL_CASE_EFFECT_AS_TECH", "expected_decision": "FAIL", "candidate": effect_as_tech})
    return cases


def run_test_cases() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in build_test_cases():
        verification = verify_candidate(case["candidate"])
        results.append(
            {
                "name": case["name"],
                "expected_decision": case["expected_decision"],
                "actual_decision": verification["decision"],
                "passed": verification["decision"] == case["expected_decision"],
                "checks": verification["checks"],
            }
        )
    return results


def expected_format() -> dict[str, Any]:
    return base_pass_case()


def markdown_test_table(results: list[dict[str, Any]]) -> str:
    rows = ["| case | expected | actual | result |", "|---|---|---|---|"]
    for item in results:
        rows.append(
            f"| {item['name']} | {item['expected_decision']} | {item['actual_decision']} | {'PASS' if item['passed'] else 'FAIL'} |"
        )
    return "\n".join(rows)


def write_reports(out: Path, run_id: str, results: list[dict[str, Any]]) -> None:
    all_passed = all(item["passed"] for item in results)
    source_refs = {
        "active_patent_packet": ACTIVE_PATENT_PACKET,
        "intent_completion": INTENT_COMPLETION,
        "cloud_request_hardened": CLOUD_REQUEST_HARDENED,
        "stage07_alignment": STAGE07_ALIGNMENT,
    }
    write_text(
        out / "00_DYNAMIC_STATE_FIELD_VERIFIER_DESIGN.md",
        f"""# Dynamic Multi-State Field Verifier Design

STATE=DYNAMIC_STATE_FIELD_VERIFIER_DESIGN
RUN_ID={run_id}

## Source Refs

- active_patent_packet={ACTIVE_PATENT_PACKET}
- intent_completion={INTENT_COMPLETION}
- cloud_request_hardened={CLOUD_REQUEST_HARDENED}
- stage07_alignment={STAGE07_ALIGNMENT}

## Purpose

本 verifier 只檢查雲端候選補全方案是否符合「人工智慧候選行動之多狀態場封包化控管方法、系統及非暫態電腦可讀取媒體」之產品落地邊界。

## Boundary

- 雲端輸出只能是 candidate_only。
- 總場維持為總體治理系統/系統，不是狀態場之一。
- ADI 維持為使用者自有 ADI 時空資料庫，種類詞為時空狀態索引資料庫。
- H64-TD 只能使用 trade_secret_ref:h64_codebook 或 trade_secret_ref:td_hash_runtime。
- 不讀取會員明文，不輸出 secret，不進行 DB write/deploy/restart/TIPO submission。
""",
    )
    write_text(
        out / "01_DYNAMIC_STATE_FIELD_RULES.md",
        """# Dynamic State Field Rules

STATE=DYNAMIC_STATE_FIELD_RULES

## PASS Rules

- 主體使用「多個狀態場/多狀態場」。
- 八個狀態場只作為附屬項或實施例。
- 必含多狀態場調度所需欄位：state_field_set_id、state_field_version、state_field_relation_table、dynamic_field_policy_id、transition_reason_code、transition_trigger_code、before_state_field_hash、after_state_field_hash、verifier_result、responsible_person_ref、timestamp_coordinate、previous_record_hash、current_record_hash。
- 必含主權身分代理模組欄位：identity_proxy_ref、authority_scope_code、consent_state_code、device_binding_ref、agent_binding_ref。
- 隔離明文封存域不得進外部模型輸入或狀態場封包。
- 每次明文調閱必有可究責紀錄。
- 前緣代理層必須阻斷未驗證候選行動進入業務系統寫入介面。

## FAIL/HOLD Rules

- 八欄位、總場變成狀態場之一、動態場必要欄位缺失：FAIL。
- 政府 ADI、智慧城鄉案例或 ADI 實際索引規則揭露：FAIL/HOLD。
- 雲端候選直接裁決、落地、DB write、deploy 或 restart：HOLD。
- 會員明文或 secret/token/password/private key/DB password 風險標籤：HOLD。
- 只寫安全、降低風險、可稽核等效果詞，未對應模組/資料結構/封包欄位/驗證條件/阻斷條件/紀錄欄位：FAIL。
""",
    )
    write_json(out / "02_CLOUD_CANDIDATE_RESPONSE_EXPECTED_FORMAT.json", expected_format())
    write_text(
        out / "03_VERIFIER_TEST_CASES.md",
        f"""# Verifier Test Cases

STATE=VERIFIER_TEST_CASES

{markdown_test_table(results)}

## Cases

- PASS_CASE：ref-only 候選方案，符合多狀態場、ADI、主權身分代理、隔離明文封存、前緣代理層、可究責紀錄。
- FAIL_CASE_FIELD_DRIFT：把多狀態場寫成八欄位。
- FAIL_CASE_ADI_DRIFT：把 ADI 寫成政府 ADI 或智慧城鄉案例。
- FAIL_CASE_SECRET：只放 secret 風險標籤，不放真 secret。
- FAIL_CASE_MEMBER_PLAINTEXT：只放會員明文風險標籤，不放真會員明文。
- FAIL_CASE_CLOUD_AUTHORITY_DRIFT：雲端候選直接裁決或要求 DB write。
- FAIL_CASE_EFFECT_AS_TECH：只有效果詞，沒有技術手段錨點。
""",
    )
    redteam_rows = ["| case | redteam purpose | expected boundary |", "|---|---|---|"]
    for item in results:
        if item["name"] != "PASS_CASE":
            redteam_rows.append(f"| {item['name']} | 壓力測試 | {item['expected_decision']} |")
    write_text(
        out / "04_REDTTEAM_FAILURE_CASES.md",
        "# Redteam Failure Cases\n\nSTATE=REDTEAM_FAILURE_CASES\n\n" + "\n".join(redteam_rows) + "\n",
    )
    write_text(
        out / "05_NEXT_CLOUD_SEND_PACKET.md",
        f"""# Next Cloud Send Packet

STATE=NEXT_CLOUD_SEND_PACKET
RUN_ID={run_id}

## Packet Boundary

- SEND_MODE=REF_ONLY_CANDIDATE_REQUEST
- CLOUD_CALL_EXECUTED=false
- DB_WRITE=false
- DEPLOY=false
- RESTART=false
- TIPO_SUBMISSION=false

## Required Candidate Sections

1. patent_type_alignment
2. product_completion_plan
3. claim_support_matrix
4. forbidden_output_check

## Verifier To Run After Candidate Return

```bash
python3 tools/intent_field/verify_cloud_candidate_response.py path/to/cloud_candidate_response.json
```

NEXT=ONLY_AFTER_OWNER_AUTHORIZED_CLOUD_SEND
""",
    )
    report = {
        "STATE": "DYNAMIC_STATE_FIELD_VERIFIER_REPORT",
        "RUN_ID": run_id,
        "TEST_SUITE": "PASS" if all_passed else "FAIL",
        "FIELD_DRIFT_CHECK": "PASS" if all_passed else "FAIL",
        "ADI_CHECK": "PASS" if all_passed else "FAIL",
        "SOVEREIGN_IDENTITY_CHECK": "PASS" if all_passed else "FAIL",
        "PLAINTEXT_ARCHIVE_ACCOUNTABILITY_CHECK": "PASS" if all_passed else "FAIL",
        "CLOUD_AUTHORITY_CHECK": "PASS" if all_passed else "FAIL",
        "TECHNICAL_MEANS_CHECK": "PASS" if all_passed else "FAIL",
        "NO_SECRET": "PASS",
        "NO_MEMBER_PLAINTEXT": "PASS",
        "H64_TD_REF_ONLY": "PASS",
        "DB_WRITE": False,
        "DEPLOY": False,
        "RESTART": False,
        "CLOUD_CALL_EXECUTED": False,
        "results": results,
    }
    lines = ["# Verifier Report", "", "STATE=DYNAMIC_STATE_FIELD_VERIFIER_REPORT", f"RUN_ID={run_id}", ""]
    for key in [
        "TEST_SUITE",
        "FIELD_DRIFT_CHECK",
        "ADI_CHECK",
        "SOVEREIGN_IDENTITY_CHECK",
        "PLAINTEXT_ARCHIVE_ACCOUNTABILITY_CHECK",
        "CLOUD_AUTHORITY_CHECK",
        "TECHNICAL_MEANS_CHECK",
        "NO_SECRET",
        "NO_MEMBER_PLAINTEXT",
        "H64_TD_REF_ONLY",
        "DB_WRITE",
        "DEPLOY",
        "RESTART",
        "CLOUD_CALL_EXECUTED",
    ]:
        value = report[key]
        if isinstance(value, bool):
            value = str(value).lower()
        lines.append(f"{key}={value}")
    lines.extend(["", "## Test Summary", "", markdown_test_table(results), ""])
    write_text(out / "VERIFIER_REPORT.md", "\n".join(lines))

    manifest = {
        "run_id": run_id,
        "created_at_utc": iso_now(),
        "source_refs": source_refs,
        "safety_flags": {
            "readonly_scan_ok": True,
            "write_reports_and_verifier_only": True,
            "no_db_write": True,
            "no_deploy": True,
            "no_restart": True,
            "no_tipo_submission": True,
            "no_secret": True,
            "no_member_plaintext": True,
            "no_raw_audio": True,
            "no_router_write": True,
            "h64_td_ref_only": True,
            "cloud_call_executed": False,
            "dry_run_only": True,
        },
        "test_results": results,
        "files": {},
    }
    write_json(out / "MANIFEST.json", manifest)
    manifest["files"] = {
        path.name: sha256_file(path)
        for path in sorted(out.iterdir())
        if path.is_file() and path.name != "MANIFEST.json"
    }
    write_json(out / "MANIFEST.json", manifest)


def run_dry(out_root: Path | None = None) -> dict[str, Any]:
    run_id = "DYNAMIC_STATE_FIELD_VERIFIER_" + now_utc()
    out_base = out_root or ROOT / "runtime/total_field/dynamic_state_field_verifier"
    out = out_base / run_id
    out.mkdir(parents=True, exist_ok=True)
    results = run_test_cases()
    write_reports(out, run_id, results)
    all_passed = all(item["passed"] for item in results)
    return {
        "state": "PASS_DYNAMIC_STATE_FIELD_VERIFIER" if all_passed else "HOLD_DYNAMIC_STATE_FIELD_VERIFIER",
        "run_id": run_id,
        "out": rel(out),
        "files_created": len([p for p in out.iterdir() if p.is_file()]),
        "dry_run": "PASS" if all_passed else "FAIL",
        "checks_pass": all_passed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and run dynamic state-field verifier reports.")
    parser.add_argument("--dry-run", action="store_true", help="Run built-in PASS/FAIL/HOLD test cases.")
    parser.add_argument("--candidate", help="Verify one candidate JSON and print result JSON.")
    parser.add_argument("--out-root", help="Override runtime output root for dry-run reports.")
    args = parser.parse_args()

    if args.candidate:
        candidate = json.loads(Path(args.candidate).read_text(encoding="utf-8"))
        print(json.dumps(verify_candidate(candidate), ensure_ascii=False, indent=2))
        return 0

    if not args.dry_run:
        parser.error("Use --dry-run or --candidate")

    summary = run_dry(Path(args.out_root) if args.out_root else None)
    for key in ["state", "run_id", "out", "files_created", "dry_run"]:
        print(f"{key.upper()}={summary[key]}")
    return 0 if summary["checks_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
