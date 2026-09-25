"""Total XiaoJ product operator handoff service.

The handoff pack combines the 8D system assembly and merchant productization
readiness into one operator-facing delivery artifact. It is safe for P1 review:
no DB writes, no external API calls, no message sends, no POS writes, no payment
captures, no secret reads, and no member or resident plaintext reads.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from .eightd_system_assembly import build_eightd_system_assembly_status
from .merchant_productization_readiness import build_merchant_productization_readiness, reject_secret_shapes


HUMAN_REF_GROUPS = {
    "lineworks": [
        "authenticated_staff_ref",
        "lineworks_release_packet_ref",
        "lineworks_app_config_ref",
        "lineworks_bot_ref",
        "lineworks_target_user_ref",
        "message_policy_ref",
        "consent_policy_ref",
        "total_field_release_ref",
        "lineworks_access_token_runtime_ref",
    ],
    "line_official_account": [
        "line_official_account_ref",
        "line_provider_ref",
        "messaging_api_channel_ref",
        "webhook_endpoint_ref",
        "channel_secret_ref",
        "channel_access_token_runtime_ref",
        "message_policy_ref",
        "audience_policy_ref",
        "consent_policy_ref",
        "human_owner_admin_release_ref",
    ],
    "merchant_formal_release": [
        "member_registration release refs",
        "pos_order release refs",
        "payment release refs",
    ],
    "association_sovereign_member": [
        "member_identity_ref",
        "member_consent_ref",
        "sovereign_xiaoj_claim_ref",
        "delegate_rotation_ref",
        "gemini_key_ref_vault_binding",
        "member_llm_release_ref",
    ],
    "resident_property_management": [
        "resident_ref",
        "unit_ref",
        "role_ref",
        "facility_ref",
        "repair_or_service_case_ref",
        "resident_unit_role_policy_ref",
        "property_action_approval_ref",
        "resident_plaintext_redaction_verifier_ref",
    ],
}

FORBIDDEN_OPERATOR_INPUTS = [
    "LINE password",
    "LINE WORKS password",
    "channel access token value",
    "channel secret value",
    "Google Gemini raw API key",
    "Odoo password",
    "router password",
    "member plaintext",
    "resident plaintext",
    "payment card data",
    "raw audio",
    "raw video",
]


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def side_effects_false() -> dict:
    return {
        "external_api_call": False,
        "formal_lineworks_send": False,
        "formal_line_message_send": False,
        "official_account_setting_changed": False,
        "formal_member_registration": False,
        "formal_db_write": False,
        "formal_pos_write": False,
        "payment_capture": False,
        "secret_read": False,
        "member_plaintext_read": False,
        "resident_plaintext_read": False,
        "raw_audio_saved": False,
        "raw_video_saved": False,
        "deploy": False,
        "service_restart": False,
    }


def _production_ready(assembly: dict, merchant: dict) -> bool:
    return (
        assembly.get("release_boundary", {}).get("production_activation_ready") is True
        and merchant.get("product_ready_for_human_activation") is True
    )


def _system_summary(assembly: dict, merchant: dict) -> dict:
    systems = assembly.get("systems", {}) if isinstance(assembly.get("systems"), dict) else {}
    merchant_gates = merchant.get("formal_release_ready", {}) if isinstance(merchant.get("formal_release_ready"), dict) else {}
    return {
        "merchant_management": {
            "p1_status": systems.get("merchant_management", {}).get("status", ""),
            "readiness_state": merchant.get("state", ""),
            "formal_release_ready": merchant_gates,
            "operator_next_actions": merchant.get("operator_next_actions", []),
        },
        "association_sovereign_member": {
            "p1_status": systems.get("association_sovereign_member", {}).get("status", ""),
            "release_status": "PARTIAL_LANDING_NOT_FULL_PRODUCT_RELEASE",
            "required_before_activation": [
                "local_personal_data_return_packet",
                "8d_delegate_rotation_and_revocation",
                "sovereign_xiaoj_claim_activation",
                "gemini_key_ref_vault_connector",
                "member_llm_release_gate",
            ],
        },
        "resident_property_management": {
            "p1_status": systems.get("resident_property_management", {}).get("status", ""),
            "release_status": "P1_CANDIDATE_RELEASE_GATE_REQUIRED",
            "required_before_activation": [
                "resident_unit_role_policy_ref",
                "property_action_approval_ref",
                "resident_plaintext_redaction_verifier_ref",
                "property_case_evidence_ref",
            ],
        },
    }


def _operator_checklist(merchant: dict) -> list[dict]:
    next_actions = merchant.get("operator_next_actions", []) if isinstance(merchant.get("operator_next_actions"), list) else []
    return [
        {
            "step": "review_8d_system_assembly_status",
            "action": "Run tools/xiaoj_8d_system_assembly_report.py or call /wuchang/xiaoj/api/8d-system-assembly-status.",
            "done_when": "PASS_XIAOJ_8D_TOTAL_SYSTEM_ASSEMBLY_P1_READY_FOR_HUMAN_REVIEW is present.",
        },
        {
            "step": "fill_refs_only",
            "action": "Fill only opaque refs and verified packet hashes for LINE WORKS, LINE Official Account, member, POS, payment, sovereign member, and resident property gates.",
            "done_when": "No raw token, secret, member plaintext, resident plaintext, or payment data is present.",
        },
        {
            "step": "rerun_merchant_readiness",
            "action": "Run tools/xiaoj_merchant_productization_readiness.py or call /wuchang/xiaoj/api/merchant-productization-readiness.",
            "done_when": "PASS_XIAOJ_MERCHANT_PRODUCTIZATION_READINESS appears, or the remaining operator_next_actions are accepted as blockers.",
            "current_next_actions": next_actions,
        },
        {
            "step": "prepare_runtime_activation_packets",
            "action": "Create separate human owner/admin activation packets only after all target refs pass.",
            "done_when": "Activation packet hash is available and bound to the target subsystem release gate.",
        },
        {
            "step": "keep_p1_boundaries",
            "action": "Do not send LINE/LINE WORKS, write POS/Odoo, capture payment, deploy, restart, or read plaintext during handoff.",
            "done_when": "All side_effects remain false.",
        },
    ]


def build_total_product_operator_handoff(
    *,
    formal_release_refs: dict | None = None,
    lineworks_refs: dict | None = None,
    line_official_account_refs: dict | None = None,
    line_official_account_intent: str | None = None,
    lineworks_probe: dict | None = None,
    input_ref: str = "",
) -> dict:
    formal_release_refs = formal_release_refs if isinstance(formal_release_refs, dict) else {}
    lineworks_refs = lineworks_refs if isinstance(lineworks_refs, dict) else {}
    line_official_account_refs = line_official_account_refs if isinstance(line_official_account_refs, dict) else {}
    reject_secret_shapes(formal_release_refs, "formal release refs")
    reject_secret_shapes(lineworks_refs, "lineworks refs")
    reject_secret_shapes(line_official_account_refs, "line official account refs")
    reject_secret_shapes(line_official_account_intent or "", "line official account intent")

    assembly = build_eightd_system_assembly_status()
    merchant = build_merchant_productization_readiness(
        formal_release_refs=formal_release_refs,
        lineworks_refs=lineworks_refs,
        line_official_account_refs=line_official_account_refs,
        line_official_account_intent=line_official_account_intent,
        lineworks_probe=lineworks_probe,
        input_ref=input_ref or "total_product_operator_handoff",
    )
    production_ready = _production_ready(assembly, merchant)
    report_seed = {
        "assembly_hash": assembly.get("report_hash", ""),
        "merchant_hash": merchant.get("report_hash", ""),
        "production_ready": production_ready,
    }
    return {
        "schema": "W7TP_XIAOJ_TOTAL_PRODUCT_OPERATOR_HANDOFF_PACK_V1",
        "state": "PASS_XIAOJ_TOTAL_PRODUCT_OPERATOR_HANDOFF_READY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "input_ref": input_ref,
        "production_activation_ready": production_ready,
        "handoff_ready_for_operator": True,
        "systems": _system_summary(assembly, merchant),
        "eightd_assembly": {
            "state": assembly.get("state", ""),
            "report_hash": assembly.get("report_hash", ""),
            "dimensions": [dimension.get("id", "") for dimension in assembly.get("eightd_dimensions", [])],
            "production_activation_ready": assembly.get("release_boundary", {}).get("production_activation_ready") is True,
        },
        "merchant_productization": {
            "state": merchant.get("state", ""),
            "report_hash": merchant.get("report_hash", ""),
            "product_ready_for_human_activation": merchant.get("product_ready_for_human_activation") is True,
            "operator_next_actions": merchant.get("operator_next_actions", []),
        },
        "human_ref_groups": HUMAN_REF_GROUPS,
        "forbidden_operator_inputs": FORBIDDEN_OPERATOR_INPUTS,
        "operator_checklist": _operator_checklist(merchant),
        "delivered_interfaces": {
            "ref_template_api": "/wuchang/xiaoj/api/total-product-ref-template",
            "ref_template_cli": "tools/xiaoj_total_product_ref_collection_builder.py --emit-template",
            "ref_collection_api": "/wuchang/xiaoj/api/total-product-ref-collection",
            "ref_collection_cli": "tools/xiaoj_total_product_ref_collection_builder.py",
            "8d_status_api": "/wuchang/xiaoj/api/8d-system-assembly-status",
            "merchant_readiness_api": "/wuchang/xiaoj/api/merchant-productization-readiness",
            "total_handoff_api": "/wuchang/xiaoj/api/total-product-operator-handoff",
            "8d_status_cli": "tools/xiaoj_8d_system_assembly_report.py",
            "merchant_readiness_cli": "tools/xiaoj_merchant_productization_readiness.py",
            "total_handoff_cli": "tools/xiaoj_total_product_handoff_pack.py",
        },
        "authority_boundary": {
            "total_field_may_prepare_candidates": True,
            "human_owner_admin_root_of_trust": True,
            "llm_direct_execution": False,
            "cloud_model_authority": False,
            "runtime_activation_required": True,
            "verified_release_refs_required": True,
        },
        "side_effects": side_effects_false(),
        "handoff_hash": stable_hash(report_seed),
    }
