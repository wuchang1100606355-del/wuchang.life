"""Universal Organization AV XiaoJ source-only contract helper.

This module is intentionally source-only:
- no Odoo import
- no DB write
- no external API call
- no public controller
- no restart/deploy authority
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List


HARD_BLOCKS = {
    "raw_secret_read",
    "member_plaintext_read",
    "raw_audio_read",
    "raw_audio_save",
    "raw_video_save",
    "db_write",
    "deploy",
    "restart",
    "reboot",
    "router_write",
    "payment_capture",
    "refund",
    "pos_order_create",
    "door_open",
    "gate_open",
    "member_approval",
    "resident_plaintext_read",
}


@dataclass(frozen=True)
class XiaoJRole:
    key: str
    label: str
    allowed: List[str]
    blocked: List[str]


ROLES: Dict[str, XiaoJRole] = {
    "business_counter_xiaoj": XiaoJRole(
        key="business_counter_xiaoj",
        label="商業櫃台小J",
        allowed=[
            "greeting",
            "menu_explain",
            "member_onboarding_guidance",
            "pos_preflight_guidance",
            "queue_support",
            "human_handoff",
        ],
        blocked=[
            "pos_order_create",
            "payment_capture",
            "refund",
            "member_approval",
            "member_plaintext_read",
            "price_write",
        ],
    ),
    "property_counter_xiaoj": XiaoJRole(
        key="property_counter_xiaoj",
        label="物業櫃台小J",
        allowed=[
            "visitor_guidance",
            "bulletin_reading",
            "package_guidance",
            "repair_ticket_guidance",
            "emergency_handoff",
            "property_staff_handoff",
        ],
        blocked=[
            "door_open",
            "gate_open",
            "resident_plaintext_read",
            "visitor_approval",
            "property_record_write",
            "committee_decision_submit",
        ],
    ),
    "community_bulletin_xiaoj": XiaoJRole(
        key="community_bulletin_xiaoj",
        label="社區布告欄小J",
        allowed=[
            "association_intro",
            "public_notice",
            "volunteer_intro",
            "local_service_map",
            "public_safe_evidence",
            "supporter_entry_no_fundraising",
        ],
        blocked=[
            "fundraising_payment",
            "political_mobilization",
            "case_plaintext_disclosure",
            "unreviewed_notice_publish",
            "formal_document_commitment",
        ],
    ),
    "developer_total_field_ui_xiaoj": XiaoJRole(
        key="developer_total_field_ui_xiaoj",
        label="開發者總場 UI 小J",
        allowed=[
            "command_to_8d_packet",
            "pass_hold_block_display",
            "run_id_locator",
            "evidence_locator",
            "dry_run_builder",
            "verify_builder",
            "seal_builder",
            "redteam_drift_guard",
        ],
        blocked=[
            "unconfirmed_restart",
            "unconfirmed_deploy",
            "unconfirmed_db_write",
            "unconfirmed_router_write",
            "unconfirmed_delete_overwrite_move",
            "raw_secret_read",
            "member_plaintext_read",
            "raw_audio_read",
        ],
    ),
}


def list_roles() -> Dict[str, Dict[str, object]]:
    return {key: asdict(role) for key, role in ROLES.items()}


def classify_action(role_key: str, action: str) -> Dict[str, object]:
    role = ROLES.get(role_key)
    if role is None:
        return {
            "state": "HOLD_UNKNOWN_ROLE",
            "role_key": role_key,
            "action": action,
            "allowed": False,
            "reason": "unknown_role",
        }

    if action in HARD_BLOCKS or action in role.blocked:
        return {
            "state": "BLOCK_HARD_RISK",
            "role_key": role_key,
            "role_label": role.label,
            "action": action,
            "allowed": False,
            "reason": "hard_risk_or_role_block",
            "next": "TOTAL_FIELD_REVIEW_REQUIRED",
        }

    if action in role.allowed:
        return {
            "state": "PASS_CANDIDATE_ACTION",
            "role_key": role_key,
            "role_label": role.label,
            "action": action,
            "allowed": True,
            "reason": "role_allowed_candidate_only",
            "next": "TOTAL_FIELD_8D_GATE",
        }

    return {
        "state": "HOLD_UNMAPPED_ACTION",
        "role_key": role_key,
        "role_label": role.label,
        "action": action,
        "allowed": False,
        "reason": "action_not_in_allowlist",
        "next": "MAP_ACTION_OR_HUMAN_REVIEW",
    }


def build_8d_ui_packet(role_key: str, user_text_ref: str, action: str) -> Dict[str, object]:
    decision = classify_action(role_key, action)
    return {
        "STATE": "W7TP_UNIVERSAL_ORG_AV_XIAOJ_8D_UI_PACKET",
        "D1_Intent": action,
        "D2_State": decision["state"],
        "D3_Coordinate": f"coord:{role_key}",
        "D4_Evidence": {
            "user_text_ref": user_text_ref,
            "raw_audio_saved": False,
            "member_plaintext_read": False,
            "secret_read": False,
        },
        "D5_Execution": {
            "mode": "candidate_only",
            "allowed": decision["allowed"],
            "next": decision["next"],
        },
        "D6_GenerativeTransmission": "state_packet_ref_lookup_reconstruct_equivalent_state_total_field_verify",
        "D7_RiskQuarantine": {
            "hard_blocks": sorted(HARD_BLOCKS),
            "decision": decision,
        },
        "D8_Envelope": {
            "short": True,
            "pasteable": True,
            "no_detour": True,
            "no_public_controller_patch": True,
            "no_db_write": True,
            "no_restart": True,
        },
    }


__all__ = [
    "HARD_BLOCKS",
    "ROLES",
    "XiaoJRole",
    "list_roles",
    "classify_action",
    "build_8d_ui_packet",
]
