"""Cafe business onboarding candidate service.

Candidate-only service:
- no DB write
- no deploy
- no restart
- no router write
- no live URL creation
- no container creation
- no payment capture
- no production activation
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping, Sequence


HARD_RISK_ACTIONS = {
    "db_write",
    "database_write",
    "deploy",
    "restart",
    "reboot",
    "router_write",
    "payment_capture",
    "formal_activation",
    "production_activation",
    "create_container",
    "create_live_url",
    "create_live_route",
}

REQUIRED_FIELDS = (
    "responsible_person_ref",
    "organization_ref",
    "business_info",
)


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _fingerprint(value: Any, length: int = 16) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()[:length]


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return bool(value)
    return True


def _actions(values: Sequence[str] | None) -> set[str]:
    return {
        str(value).strip().lower().replace("-", "_")
        for value in (values or [])
        if str(value).strip()
    }


def build_cafe_business_onboarding_candidate(
    *,
    responsible_person_ref: str | None,
    organization_ref: str | None,
    business_info: Mapping[str, Any] | None,
    requested_actions: Sequence[str] | None = None,
    organization_review_state: str = "owner_admin_review_required",
    responsible_person_review_state: str = "owner_admin_review_required",
) -> Dict[str, Any]:
    normalized_actions = _actions(requested_actions)
    business_payload = dict(business_info or {})

    missing_fields = [
        name
        for name, value in {
            "responsible_person_ref": responsible_person_ref,
            "organization_ref": organization_ref,
            "business_info": business_payload,
        }.items()
        if not _present(value)
    ]

    blocked_actions = sorted(normalized_actions & HARD_RISK_ACTIONS)

    base = {
        "responsible_person_ref": responsible_person_ref or "",
        "organization_ref": organization_ref or "",
        "business_info": business_payload,
        "requested_actions": sorted(normalized_actions),
        "organization_review_state": organization_review_state,
        "responsible_person_review_state": responsible_person_review_state,
        "production_activation_ready": False,
        "formal_operation_enabled": False,
        "db_write": False,
        "deploy": False,
        "restart": False,
        "router_write": False,
        "payment_capture": False,
        "live_container_created": False,
        "live_url_created": False,
    }

    candidate_id = _fingerprint(base)

    packet = {
        "packet_type": "merchant_8d_7d_packet",
        "packet_ref": f"merchant_8d_7d_packet:{candidate_id}",
        "authority": "total_field_candidate_only",
        "d1_intent": "cafe_business_onboarding",
        "d2_state": "candidate_waiting_owner_admin_review",
        "d3_coordinate": {
            "responsible_person_ref": base["responsible_person_ref"],
            "organization_ref": base["organization_ref"],
            "merchant_candidate_ref": f"merchant_candidate:{candidate_id}",
        },
        "d4_evidence": {
            "source_refs": [
                "wuchang_member_registration.member_type.organization",
                "wuchang_member_registration.organization_role.responsible_person",
                "wuchang_member_group_registration_packet",
            ],
            "business_info_fingerprint": _fingerprint(business_payload),
        },
        "d5_execution": {
            "mode": "candidate_only",
            "db_write": False,
            "deploy": False,
            "restart": False,
            "router_write": False,
            "payment_capture": False,
        },
        "d6_technical_definition": "8D authority envelope plus 7D functional candidate state",
        "d7_risk": {
            "missing_fields": missing_fields,
            "blocked_actions": blocked_actions,
            "formal_activation_blocked": True,
            "owner_admin_review_required": True,
        },
        "d8_envelope": {
            "seal": f"candidate_seal:{candidate_id}",
            "ttl": "review_required",
            "decision_authority": "total_field",
        },
        "seven_d_functional_state": {
            "tenant_profile_candidate": True,
            "service_profile_candidate": True,
            "container_config_candidate": True,
            "url_routing_candidate": True,
        },
    }

    if blocked_actions:
        decision = "BLOCK"
        reason = "HARD_RISK_ACTION_REQUESTED"
    elif missing_fields:
        decision = "HOLD"
        reason = "MISSING_REQUIRED_ONBOARDING_FIELD"
    else:
        decision = "PASS_CANDIDATE"
        reason = "CANDIDATE_PACKET_READY_FOR_TOTAL_FIELD_OWNER_ADMIN_REVIEW"

    return {
        "candidate_type": "cafe_business_onboarding_final_form",
        "candidate_ref": f"cafe_onboarding_candidate:{candidate_id}",
        **base,
        "merchant_8d_7d_packet": packet,
        "adi_5d_ref": f"adi5d://wuchang/cafe/business-onboarding/{candidate_id}",
        "tenant_profile_candidate": {
            "tenant_ref": f"tenant_candidate:{candidate_id}",
            "tenant_kind": "merchant_cafe",
            "candidate_only": True,
        },
        "service_profile_candidate": {
            "service_ref": f"service_candidate:{candidate_id}",
            "service_kind": "cafe_business_operations",
            "candidate_only": True,
        },
        "container_config_candidate": {
            "container_config_ref": f"container_config_candidate:{candidate_id}",
            "create_container": False,
            "deploy": False,
            "restart": False,
        },
        "url_routing_candidate": {
            "route_ref": f"url_route_candidate:{candidate_id}",
            "create_live_route": False,
            "router_write": False,
        },
        "total_field_candidate_decision": {
            "decision": decision,
            "reason": reason,
            "missing_fields": missing_fields,
            "blocked_actions": blocked_actions,
            "production_activation_ready": False,
            "next": "OWNER_ADMIN_REVIEW_THEN_SEAL_OR_HOLD",
        },
    }


def render_cafe_business_onboarding_response(candidate: Mapping[str, Any]) -> Dict[str, Any]:
    decision = dict(candidate.get("total_field_candidate_decision") or {})
    status = decision.get("decision", "HOLD")

    if status == "PASS_CANDIDATE":
        message = "已建立商家入場候選封包；等待總場與 owner/admin 核准，不會直接啟用正式營運。"
    elif status == "BLOCK":
        message = "命中正式啟用或系統寫入風險；已阻擋，不會執行 DB write、deploy、restart、router write 或金流。"
    else:
        missing = "、".join(decision.get("missing_fields") or [])
        message = f"商家入場候選暫停；缺少必要欄位：{missing}。"

    return {
        "decision": status,
        "member_facing_message": message,
        "production_activation_ready": False,
        "next_action": decision.get("next", "OWNER_ADMIN_REVIEW_THEN_SEAL_OR_HOLD"),
    }


def run_cafe_business_onboarding(
    *,
    responsible_person_ref: str | None,
    organization_ref: str | None,
    business_info: Mapping[str, Any] | None,
    requested_actions: Sequence[str] | None = None,
) -> Dict[str, Any]:
    candidate = build_cafe_business_onboarding_candidate(
        responsible_person_ref=responsible_person_ref,
        organization_ref=organization_ref,
        business_info=business_info,
        requested_actions=requested_actions,
    )
    return {
        "STATE": candidate["total_field_candidate_decision"]["decision"],
        "CANDIDATE": candidate,
        "HUMAN_RESPONSE": render_cafe_business_onboarding_response(candidate),
    }
