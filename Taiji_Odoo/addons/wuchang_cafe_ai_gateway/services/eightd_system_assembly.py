"""8D natural-language control system assembly status service.

The assembly connects merchant management, association sovereign membership,
and resident/property management through reference-only 8D intent-field
packets. It is a P1 status and candidate-authority report, not a production
activation path.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from .p1_intent_engine import SAFETY_FLAGS, candidate_action, merchant_capability_payload


EIGHTD_DIMENSIONS = [
    {
        "id": "D1_INTENT",
        "zh": "意圖",
        "purpose": "the current human or organization intent without treating model output as authority",
    },
    {
        "id": "D2_STATE",
        "zh": "狀態",
        "purpose": "the current effective task, service, member, order, voucher, and runtime state",
    },
    {
        "id": "D3_COORDINATE",
        "zh": "座標",
        "purpose": "natural person, organization, seat, node, scene, time, and service coordinates",
    },
    {
        "id": "D4_EVIDENCE",
        "zh": "證據",
        "purpose": "receipts, hashes, preimages, postimages, observations, and audit references",
    },
    {
        "id": "D5_EXECUTION_POLICY",
        "zh": "執行／政策",
        "purpose": "allowed effects, policy gates, capability seats, and execution boundaries",
    },
    {
        "id": "D6_GENERATIVE_STATE_TRANSMISSION",
        "zh": "生成式狀態傳輸",
        "purpose": "non-differential pointer-first minimum-state transmission and local reconstruction",
    },
    {
        "id": "D7_RISK_ISOLATION",
        "zh": "風險／隔離",
        "purpose": "masked-data boundaries, cross-member and cross-organization isolation, fail-closed risk controls",
    },
    {
        "id": "D8_ENVELOPE_AUTHORITY",
        "zh": "封套／權威",
        "purpose": "authority envelope, owner consent, organization scope, replay protection, seal and authorization refs",
    },
]
EIGHTD_COUPLING_RULE = "ONE_COUPLED_DYNAMIC_STATE_FIELD_NOT_PIPELINE"

SYSTEMS = {
    "merchant_management": {
        "title_zh": "商家管理系統",
        "intent": "merchant_capability_map",
        "natural_language_probe": "咖啡館店員要查菜單、桌邊點餐、會員服務、LINE WORKS 通知與付款 gate 狀態",
        "required_surfaces": ["Odoo", "POS", "LINE_WORKS", "LINE_OFFICIAL_ACCOUNT", "table_side_ordering"],
        "release_gates": ["member_registration", "pos_order", "payment", "lineworks_send"],
    },
    "association_sovereign_member": {
        "title_zh": "協會會員 8 維度主權會員系統",
        "intent": "sovereign_member_personalization",
        "natural_language_probe": "會員要領用主權小J並使用自己的 Gemini key ref 取得候選服務",
        "required_surfaces": ["member_browser", "8D_claim", "Gemini_candidate_worker", "consent_ledger"],
        "release_gates": ["member_registration", "member_llm_release_gate", "delegate_rotation"],
    },
    "resident_property_management": {
        "title_zh": "8 維度主權住戶整合式物業管理系統",
        "intent": "property_community_candidate",
        "natural_language_probe": "住戶回報公設損壞、包裹、訪客、管理費或社區公告候選流程",
        "required_surfaces": ["resident", "unit", "facility", "parcel", "repair", "announcement"],
        "release_gates": ["resident_unit_role_policy", "property_action_approval", "resident_plaintext_redaction"],
    },
}


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _safe_probe(system_id: str, spec: dict) -> dict:
    if system_id == "merchant_management":
        payload = merchant_capability_payload()
    else:
        payload = candidate_action(spec["natural_language_probe"], explicit_intent=spec["intent"])
    authority_packet = payload.get("authority_packet", {}) if isinstance(payload.get("authority_packet"), dict) else {}
    local_verifier = payload.get("local_verifier", {}) if isinstance(payload.get("local_verifier"), dict) else {}
    execution_gate = payload.get("execution_gate", {}) if isinstance(payload.get("execution_gate"), dict) else {}
    return {
        "intent": payload.get("intent", ""),
        "state": payload.get("state", ""),
        "packet_hash": authority_packet.get("packet_hash", ""),
        "evidence_hash": payload.get("evidence_seal", {}).get("evidence_hash", ""),
        "local_verifier_decision": local_verifier.get("decision", ""),
        "execution_allowed": execution_gate.get("execution_allowed") is True,
        "failure_reasons": local_verifier.get("failure_reasons", []),
        "total_field_subfield_state": payload.get("total_field_subfield_query", {}).get("state", ""),
        "total_field_subfield_query_hash": payload.get("total_field_subfield_query", {}).get("query_hash", ""),
        "full_body_transmitted": authority_packet.get("generative_transmission", {}).get("full_body_transmitted") is True,
        "candidate_only": authority_packet.get("candidate_only") is True,
        "cloud_authority": authority_packet.get("cloud_authority") is True,
    }


def build_eightd_system_assembly_status() -> dict:
    probes = {system_id: _safe_probe(system_id, spec) for system_id, spec in SYSTEMS.items()}
    systems = {}
    for system_id, spec in SYSTEMS.items():
        probe = probes[system_id]
        systems[system_id] = {
            "title_zh": spec["title_zh"],
            "status": "P1_CANDIDATE_AUTHORITY_CHAIN_READY",
            "natural_language_control": True,
            "eightd_packet_required": True,
            "candidate_only_before_local_verifier": True,
            "required_surfaces": spec["required_surfaces"],
            "release_gates": spec["release_gates"],
            "probe": probe,
            "execution_boundary": {
                "formal_db_write": False,
                "formal_pos_write": False,
                "payment_capture": False,
                "member_plaintext_read": False,
                "resident_plaintext_read": False,
                "external_api_call": False,
                "requires_human_release": True,
            },
        }
    report_seed = {
        "dimensions": [dimension["id"] for dimension in EIGHTD_DIMENSIONS],
        "systems": {system_id: system["probe"].get("packet_hash", "") for system_id, system in systems.items()},
    }
    return {
        "schema": "W7TP_XIAOJ_8D_TOTAL_SYSTEM_ASSEMBLY_STATUS_V1",
        "state": "PASS_XIAOJ_8D_TOTAL_SYSTEM_ASSEMBLY_P1_READY_FOR_HUMAN_REVIEW",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title_zh": "8維度意圖場封包自然語言控制系統總成",
        "title_en": "8D Intent-Field Packet Natural-Language Control System Assembly",
        "eightd_dimensions": EIGHTD_DIMENSIONS,
        "eightd_coupling_rule": EIGHTD_COUPLING_RULE,
        "core_chain": [
            "natural_language_input",
            "total_field_subfield_query",
            "8d_intent_field_packet",
            "authority_packet",
            "local_reconstruction",
            "local_discrete_state_verifier",
            "hold_or_human_release_or_dead_letter",
            "evidence_seal_and_ui_status",
        ],
        "systems": systems,
        "patent_alignment": {
            "merchant_management": "AI candidate outputs are converted into 8D authority packets before merchant execution.",
            "association_sovereign_member": "Member identity, consent, LLM key refs, and XiaoJ claim refs remain member-sovereign.",
            "resident_property_management": "Resident/unit/facility actions require local role-time-evidence verification before action.",
            "new_patent_subject_zh": "8維度主權住戶整合式物業管理系統",
        },
        "release_boundary": {
            "p1_ready": True,
            "production_activation_ready": False,
            "human_owner_admin_root_of_trust": True,
            "runtime_activation_packet_required": True,
            "verified_release_refs_required": True,
        },
        "side_effects": {
            **SAFETY_FLAGS,
            "FORMAL_DB_WRITE": False,
            "FORMAL_POS_WRITE": False,
            "FORMAL_LINEWORKS_SEND": False,
            "FORMAL_LINE_MESSAGE_SEND": False,
            "RESIDENT_PLAINTEXT_READ": False,
        },
        "report_hash": stable_hash(report_seed),
    }
