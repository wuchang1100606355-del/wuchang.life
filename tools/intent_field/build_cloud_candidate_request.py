#!/usr/bin/env python3
"""Build a ref-only cloud candidate request for intent-field completion."""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from pathlib import Path
from typing import Any


ROOT = Path("/home/taiji_admin/Taiji_Hub")
ACCOUNTABLE_ACCESS_RECORD_FIELDS = [
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
]
ACCOUNTABLE_RECORD_CHAIN_FIELDS = [
    "candidate_action_id",
    "state_packet_id",
    "rule_version",
    "verifier_result",
    "execution_result",
    "timestamp_coordinate",
    "previous_record_hash",
    "current_record_hash",
]
STATE_PACKET_REQUIRED_FIELDS = [
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
]
CANDIDATE_OUTPUT_SECTIONS = [
    "patent_type_alignment",
    "product_completion_plan",
    "claim_support_matrix",
    "forbidden_output_check",
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_ref(path: Path | str, role: str, state: str = "REF_ONLY") -> dict[str, str]:
    p = Path(path)
    full = p if p.is_absolute() else ROOT / p
    if not full.exists() or not full.is_file():
        return {"path": str(path), "sha256": "0" * 64, "role": role, "state": "MISSING"}
    rel = str(full.relative_to(ROOT)) if full.is_relative_to(ROOT) else str(full)
    return {"path": rel, "sha256": sha256_file(full), "role": role, "state": state}


def default_forbidden_data_policy() -> dict[str, Any]:
    return {
        "no_secret": True,
        "no_member_plaintext": True,
        "no_raw_audio": True,
        "no_router_write": True,
        "h64_td_ref_only": True,
        "external_model_candidate_only": True,
        "allowed_trade_secret_refs": [
            "trade_secret_ref:h64_codebook",
            "trade_secret_ref:td_hash_runtime",
        ],
        "forbidden_payload_classes": [
            "credential_material",
            "member_identifiable_plaintext",
            "raw_audio",
            "business_write_command",
            "adi_index_rule_disclosure",
            "trade_secret_detail_disclosure",
        ],
    }


def default_field_lock() -> dict[str, Any]:
    return {
        "total_field_is_state_field": False,
        "preferred_upper_term": "多個狀態場/多狀態場",
        "implementation_example_state_count": "八個狀態場",
        "forbidden_core_terms": ["columnization_lock", "json_key_lock", "db_field_lock"],
        "adi_definition": "使用者自有 ADI 時空資料庫；專利種類詞為時空狀態索引資料庫",
        "government_adi_case": False,
    }


def default_technical_means_lock() -> dict[str, Any]:
    return {
        "effect_requires_means": True,
        "required_means": [
            "module",
            "data_structure",
            "packet_field",
            "verification_condition",
            "blocking_condition",
            "record_field",
            "reconstruction_flow",
        ],
        "effect_words_require_anchor": [
            "降低",
            "避免",
            "提升",
            "確保",
            "防止",
            "安全",
            "治理",
            "風險",
            "可稽核",
            "受限",
        ],
    }


def default_patent_type_conformity_lock() -> dict[str, Any]:
    return {
        "enabled": True,
        "patent_type": "人工智慧候選行動之多狀態場封包化控管方法、系統及非暫態電腦可讀取媒體",
        "independent_claim_subject": "多個狀態場/多狀態場",
        "eight_state_field_usage": "附屬項或實施例",
        "total_field_role": "總體治理系統/系統/governance control plane",
        "forbidden_core_limitations": ["W7TP", "小J", "Odoo", "POS", "一般 AI 產品", "一般 chatbot", "一般 agent gateway"],
        "candidate_output_sections": CANDIDATE_OUTPUT_SECTIONS,
        "cloud_candidate_only": True,
        "total_field_final_authority": True,
        "required_verifier_checks": [
            "field drift check",
            "ADI drift check",
            "technical means check",
            "no-secret check",
            "no-member-plaintext check",
            "h64_td_ref_only_check",
            "product-name limitation check",
        ],
    }


def default_identity_agent() -> dict[str, Any]:
    return {
        "enabled": True,
        "identity_proxy_ref": "identity_proxy_ref:generated_by_sovereign_identity_agent",
        "authority_scope_code": "authority_scope_code:ref_only",
        "consent_state_code": "consent_state_code:ref_only",
        "device_binding_ref": "device_binding_ref:ref_only",
        "agent_binding_ref": "agent_binding_ref:ref_only",
        "responsible_person_ref": "responsible_person_ref:ref_only",
        "access_request_id": "access_request_id:ref_only",
        "input_subject_classes": ["user", "member", "organization", "device", "ai_agent"],
    }


def default_plaintext_archive_boundary() -> dict[str, Any]:
    return {
        "enabled": True,
        "excluded_from_external_model_input": True,
        "excluded_from_state_packet": True,
        "accountable_access_required": True,
        "archive_ref_only": "plaintext_archive_ref:isolated_domain",
    }


def build_request(
    run_id: str,
    active_patent_packet_ref: dict[str, str],
    product_target_refs: list[dict[str, str]],
    current_system_refs: list[dict[str, str]],
    gap_items: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "request_id": f"cloud_candidate_request:{uuid.uuid4().hex[:16]}",
        "active_patent_packet_ref": active_patent_packet_ref,
        "product_target_refs": product_target_refs,
        "current_system_refs": current_system_refs,
        "gap_items": gap_items,
        "candidate_request": {
            "mode": "cloud_candidate_code_completion",
            "task": "補全產品級意圖場建構前置元件；只產生候選方案，不裁決、不落地、不呼叫外部服務。",
            "expected_outputs": CANDIDATE_OUTPUT_SECTIONS,
            "dry_run_only": True,
            "state_packet_required_fields": STATE_PACKET_REQUIRED_FIELDS,
            "accountable_record_chain_fields": ACCOUNTABLE_RECORD_CHAIN_FIELDS,
        },
        "forbidden_data_policy": default_forbidden_data_policy(),
        "redaction_policy": {
            "mode": "redact_or_hold",
            "hard_risk_action": "HOLD",
            "output_contains_only_refs": True,
        },
        "field_lock": default_field_lock(),
        "technical_means_lock": default_technical_means_lock(),
        "patent_type_conformity_lock": default_patent_type_conformity_lock(),
        "sovereign_identity_agent": default_identity_agent(),
        "spacetime_state_index_database": {
            "generic_name": "時空狀態索引資料庫",
            "owner_adi_allowed_as_implementation": True,
            "government_adi_case": False,
            "actual_index_rules_disclosed": False,
        },
        "isolated_plaintext_archive_boundary": default_plaintext_archive_boundary(),
        "accountable_access_record_fields": ACCOUNTABLE_ACCESS_RECORD_FIELDS,
        "verifier_requirements": [
            "json_parse",
            "field_drift_check",
            "adi_check",
            "technical_means_check",
            "no_secret",
            "no_member_plaintext",
            "h64_td_ref_only",
            "cloud_candidate_only",
            "patent_type_conformity",
            "product_name_limitation_check",
        ],
        "cloud_authority_boundary": {
            "cloud_candidate_only": True,
            "total_field_final_authority": True,
            "external_model_can_execute_business_system": False,
            "cloud_call_executed": False,
            "db_write": False,
            "deploy": False,
            "restart": False,
        },
        "candidate_output_template": {
            "A_patent_type_alignment": {
                "符合多狀態場封包化控管方法": "REQUIRED",
                "包含主權身分代理模組": "REQUIRED",
                "包含時空狀態索引資料庫": "REQUIRED",
                "包含隔離明文封存域與可究責紀錄": "REQUIRED",
                "包含前緣代理層阻斷": "REQUIRED",
                "符合技術手段鎖": "REQUIRED",
            },
            "B_product_completion_plan": [
                "需新增模組",
                "需新增 schema",
                "需新增 verifier",
                "需新增 CLI",
                "需新增 dry-run 報告",
                "不可落地項",
                "需人工確認項",
            ],
            "C_claim_support_matrix": [
                "Claim 1 方法項",
                "Claim 13 系統項",
                "Claim 19 非暫態電腦可讀取媒體項",
                "附屬項",
                "尚缺證據",
            ],
            "D_forbidden_output_check": {
                "no_member_plaintext": True,
                "no_secret": True,
                "no_h64_td_detail": True,
                "no_adi_index_rules": True,
                "no_db_write": True,
                "no_deploy": True,
                "no_restart": True,
                "cloud_candidate_only": True,
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build ref-only cloud candidate request.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--active-patent-packet", required=True)
    parser.add_argument("--product-target-ref", action="append", default=[])
    parser.add_argument("--current-system-ref", action="append", default=[])
    parser.add_argument("--gap-items-json", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    gaps = json.loads(Path(args.gap_items_json).read_text(encoding="utf-8"))
    request = build_request(
        run_id=args.run_id,
        active_patent_packet_ref=file_ref(args.active_patent_packet, "active_patent_packet"),
        product_target_refs=[file_ref(p, "product_target") for p in args.product_target_ref],
        current_system_refs=[file_ref(p, "current_system") for p in args.current_system_ref],
        gap_items=gaps,
    )
    Path(args.output).write_text(json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OUTPUT={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
