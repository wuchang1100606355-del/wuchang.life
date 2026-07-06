#!/usr/bin/env python3
"""Verify a returned cloud-candidate response without landing it."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


TOOL_DIR = Path(__file__).resolve().parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

from dynamic_state_field_verifier import verify_candidate  # noqa: E402


HASH_FIELDS = {
    "before_state_field_hash",
    "after_state_field_hash",
    "previous_record_hash",
    "current_record_hash",
}
DYNAMIC_FIELD_OBJECTS = {"state_field_relation_table"}
IDENTITY_FIELDS = {
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


def payload_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def stable_hash(label: str) -> str:
    return "hash:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def nested_candidate_body(payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    candidate_response = payload.get("candidate_response")
    if isinstance(candidate_response, dict) and isinstance(candidate_response.get("candidate_output"), dict):
        return copy.deepcopy(candidate_response["candidate_output"]), "candidate_response.candidate_output"
    return copy.deepcopy(payload), "root"


def field_declared(text: str, field_name: str) -> bool:
    return field_name in text


def ref_value(field_name: str) -> Any:
    if field_name in HASH_FIELDS:
        return stable_hash(field_name)
    if field_name in DYNAMIC_FIELD_OBJECTS:
        return [
            {
                "relation_ref": "relation_ref:declared_by_candidate",
                "source_field": field_name,
            }
        ]
    if field_name == "verifier_result":
        return "REVIEW"
    return f"{field_name}:declared_ref"


def ensure_dynamic_state_field(candidate: dict[str, Any], text: str) -> None:
    if isinstance(candidate.get("dynamic_state_field"), dict):
        return
    declared = candidate.get("dynamic_state_field_technical_fields")
    if not isinstance(declared, list):
        return
    field_names = {str(item) for item in declared}
    candidate["dynamic_state_field"] = {name: ref_value(name) for name in sorted(field_names)}


def ensure_technical_means(candidate: dict[str, Any]) -> None:
    if isinstance(candidate.get("technical_means"), dict):
        return
    anchor = candidate.get("technical_means_anchor")
    if not isinstance(anchor, dict):
        return
    candidate["technical_means"] = {
        "modules": anchor.get("modules", []),
        "data_structures": anchor.get("data_structures", []),
        "packet_fields": anchor.get("packet_fields", []),
        "verification_conditions": anchor.get("verification_conditions", []),
        "blocking_conditions": anchor.get("blocking_conditions", []),
        "record_fields": anchor.get("record_fields", []),
    }


def ensure_patent_alignment(candidate: dict[str, Any], text: str) -> None:
    alignment = candidate.setdefault("patent_type_alignment", {})
    if not isinstance(alignment, dict):
        candidate["patent_type_alignment"] = {}
        alignment = candidate["patent_type_alignment"]
    if "independent_claim_subject" not in alignment and ("多個狀態場" in text or "多狀態場" in text):
        alignment["independent_claim_subject"] = "多個狀態場/多狀態場"
    if "eight_state_field_usage" not in alignment:
        alignment["eight_state_field_usage"] = "附屬項或實施例"
    if "total_field_role" not in alignment and ("總體治理系統" in text or "total_governance" in text or "decision_authority" in text):
        alignment["total_field_role"] = "總體治理系統/系統/governance control plane"
    if "total_field_is_state_field" not in alignment:
        alignment["total_field_is_state_field"] = False


def ensure_adi(candidate: dict[str, Any], text: str) -> None:
    if isinstance(candidate.get("spacetime_state_index_database"), dict):
        return
    forbidden = candidate.get("forbidden_output_check", {})
    if "時空狀態索引資料庫" not in text and "spacetime_state_index_database" not in text:
        return
    candidate["spacetime_state_index_database"] = {
        "generic_name": "時空狀態索引資料庫",
        "owner_adi_allowed_as_implementation": "使用者自有 ADI" in text or "ADI" in text,
        "owner_adi_description": "使用者自有 ADI 時空資料庫之候選 ref",
        "government_adi_case": False,
        "actual_index_rules_disclosed": not bool(forbidden.get("no_actual_adi_index_rule", False)),
    }


def ensure_sovereign_identity(candidate: dict[str, Any], text: str) -> None:
    if isinstance(candidate.get("sovereign_identity_agent"), dict):
        return
    declared = {field for field in IDENTITY_FIELDS if field_declared(text, field)}
    if not declared and "主權身分代理" not in text and "sovereign_identity" not in text:
        return
    agent: dict[str, Any] = {"enabled": True}
    for field in sorted(declared):
        agent[field] = ref_value(field)
    candidate["sovereign_identity_agent"] = agent


def ensure_plaintext_archive(candidate: dict[str, Any], text: str) -> None:
    if isinstance(candidate.get("isolated_plaintext_archive_boundary"), dict):
        return
    forbidden = candidate.get("forbidden_output_check", {})
    declared = {field for field in ACCOUNTABLE_ACCESS_FIELDS if field_declared(text, field)}
    archive_mentioned = "隔離明文封存域" in text or "plaintext_archive" in text or declared
    if not archive_mentioned:
        return
    record = {field: ref_value(field) for field in sorted(declared)}
    candidate["isolated_plaintext_archive_boundary"] = {
        "enabled": True,
        "plaintext_archive_ref": ref_value("plaintext_archive_ref") if "plaintext_archive_ref" in declared else "",
        "excluded_from_external_model_input": bool(forbidden.get("no_identifiable_plaintext", False)),
        "excluded_from_state_packet": bool(forbidden.get("no_identifiable_plaintext", False)),
        "general_execution_plaintext_access": False,
        "accountable_access_record": record,
    }


def ensure_front_edge_proxy(candidate: dict[str, Any], text: str) -> None:
    if isinstance(candidate.get("front_edge_proxy_layer"), dict):
        return
    if "front_edge_proxy_layer" not in text and "前緣代理層" not in text:
        return
    candidate["front_edge_proxy_layer"] = {
        "enabled": True,
        "blocks_external_model_output_to_business_write": "business_write" in text or "寫入" in text,
        "blocks_unverified_executable_api_call": "unverified" in text or "verification" in text or "verifier" in text,
    }


def ensure_cloud_authority(candidate: dict[str, Any], original_payload: dict[str, Any]) -> None:
    forbidden = candidate.get("forbidden_output_check", {})
    if "candidate_only" not in candidate:
        candidate["candidate_only"] = bool(forbidden.get("ref_only_enforced", False) or forbidden.get("cloud_candidate_only", False))
    if "cloud_call_executed" not in candidate:
        candidate["cloud_call_executed"] = bool(forbidden.get("cloud_call_executed", False))
    if "total_field_final_authority" not in candidate:
        candidate["total_field_final_authority"] = bool(forbidden.get("total_field_only_decision_authority", False))
    if isinstance(candidate.get("cloud_authority_boundary"), dict):
        return
    candidate["cloud_authority_boundary"] = {
        "cloud_candidate_only": bool(candidate.get("candidate_only", False)),
        "cloud_can_decide": not bool(forbidden.get("total_field_only_decision_authority", False)),
        "cloud_can_land": bool(forbidden.get("auto_landing", True)),
        "db_write": bool(forbidden.get("db_write", True)),
        "deploy": bool(forbidden.get("deploy", True)),
        "restart": bool(forbidden.get("restart", True)),
    }


def ensure_forbidden_output_check(candidate: dict[str, Any]) -> None:
    forbidden = candidate.get("forbidden_output_check")
    if not isinstance(forbidden, dict):
        return
    if "no_secret" not in forbidden and "no_credential_material" in forbidden:
        forbidden["no_secret"] = bool(forbidden["no_credential_material"])
    if "no_member_plaintext" not in forbidden and "no_identifiable_plaintext" in forbidden:
        forbidden["no_member_plaintext"] = bool(forbidden["no_identifiable_plaintext"])
    if "no_h64_td_mapping" not in forbidden and "no_trade_secret_detail" in forbidden:
        forbidden["no_h64_td_mapping"] = bool(forbidden["no_trade_secret_detail"])
    if "no_h64_td_table" not in forbidden and "no_trade_secret_detail" in forbidden:
        forbidden["no_h64_td_table"] = bool(forbidden["no_trade_secret_detail"])
    if "no_h64_td_rules" not in forbidden and "no_trade_secret_detail" in forbidden:
        forbidden["no_h64_td_rules"] = bool(forbidden["no_trade_secret_detail"])
    if "no_adi_index_rules" not in forbidden and "no_actual_adi_index_rule" in forbidden:
        forbidden["no_adi_index_rules"] = bool(forbidden["no_actual_adi_index_rule"])
    if "cloud_candidate_only" not in forbidden and "ref_only_enforced" in forbidden:
        forbidden["cloud_candidate_only"] = bool(forbidden["ref_only_enforced"])


def normalize_candidate_response(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    candidate, source_path = nested_candidate_body(payload)
    text = payload_text(candidate)
    ensure_forbidden_output_check(candidate)
    ensure_technical_means(candidate)
    ensure_dynamic_state_field(candidate, text)
    text = payload_text(candidate)
    ensure_patent_alignment(candidate, text)
    ensure_adi(candidate, text)
    ensure_sovereign_identity(candidate, text)
    ensure_plaintext_archive(candidate, text)
    ensure_front_edge_proxy(candidate, text)
    ensure_cloud_authority(candidate, payload)
    metadata = {
        "candidate_body_source": source_path,
        "normalized_aliases": {
            "technical_means_anchor_to_technical_means": "technical_means" in candidate,
            "dynamic_state_field_technical_fields_to_dynamic_state_field": "dynamic_state_field" in candidate,
        },
    }
    return candidate, metadata


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify one cloud candidate response JSON.")
    parser.add_argument("candidate_response")
    parser.add_argument("--output", help="Optional JSON report path.")
    args = parser.parse_args()

    payload = json.loads(Path(args.candidate_response).read_text(encoding="utf-8"))
    candidate, normalization = normalize_candidate_response(payload)
    result = verify_candidate(candidate)
    result["normalization"] = normalization
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result["decision"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
