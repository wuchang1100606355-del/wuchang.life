"""Cafe business onboarding final-form candidate service.

This module is candidate-only:
- no DB write
- no deploy
- no restart
- no router write
- no live URL creation
- no payment capture
- no production activation
"""

from __future__ import annotations

import hashlib
import importlib
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


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return bool(value)
    return True


def _normalize_actions(actions: Sequence[str] | None) -> set[str]:
    return {
        str(action).strip().lower().replace("-", "_")
        for action in (actions or [])
        if str(action).strip()
    }


def _gate_module_status() -> Dict[str, Any]:
    try:
        module = importlib.import_module("tools.total_field.final_state_gate")
    except Exception as exc:
        return {
            "available": False,
            "module": "tools.total_field.final_state_gate",
            "error": type(exc).__name__,
        }

    public_symbols = [
        name
        for name in dir(module)
        if not name.startswith("_")
    ]

    return {
        "available": True,
        "module": "tools.total_field.final_state_gate",
        "symbols": public_symbols[:20],
        "authority": "referenced_only_total_field_remains_final_decider",
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
    actions = _normalize_actions(requested_actions)
    business_payload = dict(business_info or {})

    missing = [
        field
        for field, value in {
            "responsible_person_ref": responsible_person_ref,
            "organization_ref": organization_ref,
            "business_info": business_payload,
        }.items()
        if not _is_present(value)
    ]

    blocked_actions = sorted(actions & HARD_RISK_ACTIONS)

    base = {
        "candidate_type": "cafe_business_onboarding_final_form",
        "responsible_person_ref": responsible_person_ref or "",
        "organization_ref": organization_ref or "",
        "business_info": business_payload,
        "requested_actions": sorted(actions),
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

    fp = _fingerprint(base)

    candidate = {
        **base,
        "candidate_ref": f"cafe_onboarding_candidate:{fp}",
        "merchant_8d_7d_packet": {
            "packet_type": "merchant_8d_7d_candidate_packet",
            "packet_ref": f"merchant_8d_7d_packet:{fp}",
            "decision_authority": "total_field",
            "d1_intent": "cafe_business_onboarding",
            "d2_state": "candidate_only_waiting_total_field_owner_admin_review",
            "d3_coordinate": {
                "responsible_person_ref": responsible_person_ref or "",
                "organization_ref": organization_ref or "",
                "merchant_candidate_ref": f"merchant_candidate:{fp}",
            },
            "d4_evidence": {
                "source": "member_registration_and_group_packet_capability_refs",
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
                "missing_fields": missing,
                "blocked_actions": blocked_actions,
                "production_activation_blocked": True,
            },
            "d8_envelope": {
                "seal": f"candidate_seal:{fp}",
                "ttl": "owner_admin_review_required",
                "authority": "total_field",
            },
            "seven_d_functional_state": {
                "tenant_profile_candidate": True,
                "service_profile_candidate": True,
                "container_config_candidate": True,
                "url_routing_candidate": True,
            },
        },
        "adi_5d_ref": f"adi5d://wuchang/cafe/business-onboarding/{fp}",
        "tenant_profile_candidate": {
            "tenant_ref": f"tenant_candidate:{fp}",
            "tenant_kind": "merchant_cafe",
            "candidate_only": True,
        },
        "service_profile_candidate": {
            "service_ref": f"service_candidate:{fp}",
            "service_kind": "cafe_business_operations",
            "candidate_only": True,
        },
        "container_config_candidate": {
            "container_config_ref": f"container_config_candidate:{fp}",
            "create_container": False,
            "restart": False,
            "deploy": False,
        },
        "url_routing_candidate": {
            "route_ref": f"url_route_candidate:{fp}",
            "create_live_route": False,
            "router_write": False,
        },
        "final_state_gate_ref": _gate_module_status(),
    }

    if blocked_actions:
        decision = "BLOCK"
        reason = "HARD_RISK_ACTION_REQUESTED"
    elif missing:
        decision = "HOLD"
        reason = "MISSING_REQUIRED_ONBOARDING_FIELD"
    else:
        decision = "PASS_CANDIDATE"
        reason = "CANDIDATE_PACKET_READY_FOR_TOTAL_FIELD_OWNER_ADMIN_REVIEW"

    candidate["total_field_candidate_decision"] = {
        "decision": decision,
        "reason": reason,
        "missing_fields": missing,
        "blocked_actions": blocked_actions,
        "production_activation_ready": False,
        "next": "OWNER_ADMIN_REVIEW_THEN_SEAL_OR_HOLD",
    }

    return candidate


def render_cafe_business_onboarding_response(candidate: Mapping[str, Any]) -> Dict[str, Any]:
    decision = dict(candidate.get("total_field_candidate_decision") or {})
    status = decision.get("decision", "HOLD")

    if status == "PASS_CANDIDATE":
        message = "已建立商家入場候選封包；等待總場與 owner/admin 核准，不會直接啟用正式營運。"
    elif status == "BLOCK":
        message = "命中正式啟用或系統寫入風險；已阻擋，不會執行 DB write、deploy、restart、router write 或金流。"
    else:
        missing = ", ".join(decision.get("missing_fields") or [])
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
