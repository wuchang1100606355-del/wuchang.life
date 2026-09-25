"""Wuchang property multibrain intent-field bridge.

Property design follows POS-style multibrain and intent-field distributed compute:
- lobby audio/video AI XiaoJ
- router guest-network AI registration
- mail/package receiving instead of POS pickup
- store manager AI -> secretary general AI
- responsible person AI -> chairperson AI
- household as smallest group
- household head defaults to unit owner and can transfer to household member

Candidate-only:
- no DB write
- no deploy
- no restart
- no router write
- no live Wi-Fi change
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence


DEFAULT_MAP_PATH = Path("configs/total_field/wuchang_property_multibrain_intent_field_map.json")
ROOKIE_MESSAGE = "這個我不懂，我只是個菜鳥，我幫你問店長或學長"

HARD_RISK_ACTIONS = {
    "db_write",
    "deploy",
    "restart",
    "router_write",
    "live_wifi_change",
    "issue_real_wifi_credential",
    "formal_approval",
    "payment_capture",
    "member_plaintext_exposure",
    "secret_exposure",
    "delete",
    "restore"
}


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _fingerprint(value: Any, length: int = 16) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()[:length]


def _actions(values: Sequence[str] | None) -> set[str]:
    return {
        str(value).strip().lower().replace("-", "_")
        for value in (values or [])
        if str(value).strip()
    }


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return bool(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return bool(value)
    return True


def load_property_multibrain_map(path: str | Path = DEFAULT_MAP_PATH) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    if data.get("mode") != "candidate_only_no_runtime_action":
        raise ValueError("property multibrain map must remain candidate-only")

    policy = data.get("policy") or {}
    required_false = [
        "delete",
        "restore",
        "deploy",
        "restart",
        "db_write",
        "router_write",
        "live_wifi_change",
        "payment_capture",
        "formal_approval",
        "member_plaintext_exposure",
        "secret_exposure",
        "production_activation",
        "web_cockpit_touch",
        "runtime_bulk_output"
    ]
    bad = [key for key in required_false if policy.get(key) is not False]
    if bad:
        raise ValueError("unsafe policy: " + ",".join(bad))

    household = data["identity_permission_model"]["household"]
    if household.get("default_household_head") != "unit_owner":
        raise ValueError("household head must default to unit_owner")
    if household.get("household_head_transferable_to") != "household_member":
        raise ValueError("household head transfer target must be household_member")

    return data


def classify_property_intent(intent_text: str) -> str:
    text = str(intent_text or "").lower()

    if any(x in text for x in ["訪客網路", "guest wifi", "wifi", "路由器", "訪客登記"]):
        return "guest_wifi_registration"

    if any(x in text for x in ["郵件", "包裹", "物品", "收領", "領取", "package", "mail"]):
        return "mail_package_receiving"

    if any(x in text for x in ["戶長", "轉移戶長", "區分所有權", "戶內成員"]):
        return "household_head_transfer"

    if any(x in text for x in ["迎賓", "大廳", "小j", "訪客", "招呼"]):
        return "visitor_greeting"

    if any(x in text for x in ["服務", "導覽", "社區資訊"]):
        return "community_service_guidance"

    return "community_service_guidance"


def select_approvers(
    *,
    intent_type: str,
    registration_target: str = "household",
    package_known_recipient: bool = True,
) -> list[str]:
    data = load_property_multibrain_map()
    rules = data["approver_rules"]
    target = str(registration_target or "").lower()

    if intent_type == "guest_wifi_registration":
        if target in {"household", "home", "resident", "住戶", "家"}:
            return list(rules["guest_wifi_for_household"])
        return list(rules["guest_wifi_for_public_event"])

    if intent_type == "visitor_greeting":
        if target in {"household", "home", "resident", "住戶", "家"}:
            return list(rules["visitor_to_household"])
        if target in {"committee", "chairperson", "管委會", "主委"}:
            return list(rules["visitor_to_committee"])
        if target in {"secretariat", "秘書處", "總幹事"}:
            return list(rules["visitor_to_secretariat"])
        return list(rules["visitor_to_merchant_or_vendor"])

    if intent_type == "mail_package_receiving":
        if package_known_recipient:
            return list(rules["mail_package_to_household"])
        return list(rules["mail_package_unknown_recipient"])

    if intent_type == "household_head_transfer":
        return ["chairperson_ai", "total_field"]

    return []


def resolve_household_role(
    *,
    person_role: str,
    is_unit_owner: bool = False,
    transfer_requested: bool = False,
) -> Dict[str, Any]:
    if is_unit_owner and not transfer_requested:
        return {
            "STATE": "PASS_HOUSEHOLD_HEAD_DEFAULTED_TO_UNIT_OWNER",
            "household_role": "household_head",
            "default_holder": "unit_owner",
            "transfer_required": False
        }

    if transfer_requested and person_role == "household_member":
        return {
            "STATE": "PASS_HOUSEHOLD_HEAD_TRANSFER_CANDIDATE",
            "household_role": "household_head_candidate",
            "default_holder": "unit_owner",
            "transfer_to": "household_member",
            "transfer_required": True,
            "requires": ["chairperson_ai_review_candidate", "total_field_pass"]
        }

    if person_role == "household_member":
        return {
            "STATE": "PASS_HOUSEHOLD_MEMBER",
            "household_role": "household_member",
            "default_holder": "unit_owner",
            "transfer_required": False
        }

    return {
        "STATE": "HOLD_HOUSEHOLD_ROLE_REVIEW_REQUIRED",
        "household_role": "review_required",
        "default_holder": "unit_owner",
        "transfer_required": transfer_requested
    }


def build_property_multibrain_candidate(
    *,
    intent_text: str,
    actor_role_ref: str = "role_ref:property_candidate",
    registration_target: str = "household",
    person_role: str = "household_member",
    is_unit_owner: bool = False,
    transfer_household_head: bool = False,
    package_known_recipient: bool = True,
    evidence_refs: Sequence[str] | None = None,
    requested_actions: Sequence[str] | None = None,
    extra_fields: Mapping[str, Any] | None = None
) -> Dict[str, Any]:
    data = load_property_multibrain_map()
    intent_type = classify_property_intent(intent_text)
    route = data["intent_field_routes"][intent_type]
    actions = _actions(requested_actions)
    blocked_actions = sorted(actions & HARD_RISK_ACTIONS)
    approvers = select_approvers(
        intent_type=intent_type,
        registration_target=registration_target,
        package_known_recipient=package_known_recipient
    )
    household_role = resolve_household_role(
        person_role=person_role,
        is_unit_owner=is_unit_owner,
        transfer_requested=transfer_household_head
    )
    evidence = list(evidence_refs or [])
    extra = dict(extra_fields or {})

    missing_fields = []
    for key, value in {
        "intent_goal": intent_text,
        "actor_role_ref": actor_role_ref,
        "registration_target": registration_target
    }.items():
        if not _present(value):
            missing_fields.append(key)

    if intent_type in {"guest_wifi_registration", "visitor_greeting"} and not approvers:
        missing_fields.append("approvers")

    base = {
        "intent_type": intent_type,
        "intent_text": intent_text,
        "actor_role_ref": actor_role_ref,
        "registration_target": registration_target,
        "route": route,
        "approvers": approvers,
        "household_role": household_role,
        "evidence_refs": evidence,
        "blocked_actions": blocked_actions,
        "missing_fields": missing_fields,
        "extra_fields": extra
    }
    fp = _fingerprint(base)

    if blocked_actions:
        decision = "BLOCK"
        reason = "HARD_RISK_ACTION_REQUESTED"
    elif missing_fields:
        decision = "HOLD"
        reason = "MISSING_REQUIRED_PROPERTY_MULTIBRAIN_FIELD"
    elif household_role["STATE"].startswith("HOLD"):
        decision = "HOLD"
        reason = "HOUSEHOLD_ROLE_REVIEW_REQUIRED"
    else:
        decision = "PASS_CANDIDATE"
        reason = "PROPERTY_MULTIBRAIN_INTENT_FIELD_CANDIDATE_READY_FOR_REVIEW"

    return {
        "STATE": decision,
        "candidate_ref": f"property_multibrain_candidate:{fp}",
        "candidate_type": "wuchang_property_multibrain_intent_field_candidate",
        "intent_goal": intent_text,
        "intent_type": intent_type,
        "actor_role_ref": actor_role_ref,
        "registration_target": registration_target,
        "brain": route["brain"],
        "device": route["device"],
        "approver_selector": route["approver_selector"],
        "approvers": approvers,
        "household_role_resolution": household_role,
        "role_ai_mapping_from_pos": data["role_ai_mapping_from_pos"],
        "formal_approval": False,
        "router_write": False,
        "live_wifi_change": False,
        "db_write": False,
        "deploy": False,
        "restart": False,
        "payment_capture": False,
        "evidence_refs": evidence,
        "missing_fields": missing_fields,
        "blocked_actions": blocked_actions,
        "eight_d_packet": {
            "d1_intent": "property_multibrain_intent_field",
            "d2_state": decision,
            "d3_coordinate": {
                "intent_type": intent_type,
                "brain": route["brain"],
                "device": route["device"],
                "registration_target": registration_target,
                "approvers": approvers
            },
            "d4_evidence": {
                "evidence_refs": evidence,
                "candidate_fingerprint": fp
            },
            "d5_execution": {
                "mode": "candidate_only",
                "router_write": False,
                "live_wifi_change": False,
                "db_write": False,
                "deploy": False,
                "restart": False,
                "formal_approval": False
            },
            "d6_technical_definition": "property scene uses POS-like multibrain intent-field distributed compute and role-routed approval",
            "d7_risk": {
                "blocked_actions": blocked_actions,
                "missing_fields": missing_fields,
                "router_write_blocked": True,
                "live_wifi_change_blocked": True
            },
            "d8_envelope": {
                "decision_authority": "total_field",
                "owner_admin_review_required": True,
                "seal": f"candidate:{fp}"
            }
        },
        "total_field_candidate_decision": {
            "decision": decision,
            "reason": reason,
            "next": "TOTAL_FIELD_OWNER_ADMIN_REVIEW"
        }
    }


def render_property_multibrain_member_response(candidate: Mapping[str, Any]) -> Dict[str, Any]:
    decision = str(candidate.get("STATE") or "HOLD")
    intent_type = str(candidate.get("intent_type") or "")

    if decision == "PASS_CANDIDATE":
        if intent_type == "guest_wifi_registration":
            msg = "我先幫你登記訪客網路候選，會通知對應的人確認，不會直接改路由器。"
        elif intent_type == "mail_package_receiving":
            msg = "我先幫你整理郵件物品收領候選，會通知收件人、戶長或秘書處確認。"
        elif intent_type == "household_head_transfer":
            msg = "我先幫你整理戶長轉移候選，需主委與總場確認。"
        elif intent_type == "visitor_greeting":
            msg = "歡迎光臨，我先幫你做訪客登記候選，通知對應的人確認。"
        else:
            msg = "我先幫你整理社區服務候選，交給總場確認。"
    elif decision == "BLOCK":
        msg = ROOKIE_MESSAGE
    else:
        msg = "資料還不夠，我先幫你列成缺件候選，交給店長或學長確認。"

    return {
        "decision": decision,
        "member_facing_message": msg,
        "router_write": False,
        "live_wifi_change": False,
        "formal_approval": False,
        "next_action": "TOTAL_FIELD_OWNER_ADMIN_REVIEW"
    }
