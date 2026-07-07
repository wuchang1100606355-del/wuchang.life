"""Wuchang Business Cloud exchange bridge.

Business Cloud scope:
- merchant profile candidates
- ticket candidates
- happiness coin exchange candidates
- community business information sharing candidates

Candidate-only:
- no payment capture
- no formal exchange
- no legal tender claim
- no token mint
- no on-chain transfer
- no DB write
- no deploy / restart
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence


DEFAULT_MAP_PATH = Path("configs/total_field/wuchang_business_cloud_exchange_map.json")
ROOKIE_MESSAGE = "這個我不懂，我只是個菜鳥，我幫你問店長或學長"

HARD_RISK_ACTIONS = {
    "payment_capture",
    "formal_exchange",
    "real_money_exchange",
    "legal_tender_claim",
    "token_mint",
    "onchain_transfer",
    "redeem_real_value",
    "issue_real_ticket",
    "publish_now",
    "production_activation",
    "db_write",
    "deploy",
    "restart",
    "router_write",
    "member_plaintext_exposure",
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


def load_business_cloud_exchange_map(path: str | Path = DEFAULT_MAP_PATH) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    if data.get("mode") != "candidate_only_no_payment_no_formal_exchange":
        raise ValueError("business cloud exchange map must remain candidate-only")

    policy = data.get("policy") or {}
    required_false = [
        "delete",
        "restore",
        "deploy",
        "restart",
        "db_write",
        "router_write",
        "web_cockpit_touch",
        "runtime_bulk_output",
        "payment_capture",
        "formal_exchange",
        "legal_tender_claim",
        "token_mint",
        "onchain_transfer",
        "member_plaintext_exposure",
        "production_activation"
    ]
    bad = [key for key in required_false if policy.get(key) is not False]
    if bad:
        raise ValueError("unsafe policy: " + ",".join(bad))

    return data


def classify_business_cloud_task(intent_text: str) -> str:
    text = str(intent_text or "").lower()

    if any(x in text for x in ["幸福幣", "幸福币", "交換", "exchange", "coin"]):
        return "happiness_coin_exchange"

    if any(x in text for x in ["票券", "券", "voucher", "ticket", "兌換券"]):
        return "ticket_candidate"

    if any(x in text for x in ["資訊共享", "商業資訊", "平台", "共享", "公告", "publish"]):
        return "business_info_share"

    if any(x in text for x in ["商家", "店家", "商業", "merchant", "business"]):
        return "merchant_profile"

    return "merchant_profile"


def build_business_cloud_candidate(
    *,
    intent_text: str,
    merchant_ref: str = "merchant_ref:candidate",
    organization_ref: str = "org_ref:wuchang_community_development_association",
    business_cloud_ref: str = "branch_unit_ref:business_cloud",
    requester_role_ref: str = "role_ref:business_cloud_candidate",
    evidence_refs: Sequence[str] | None = None,
    exchange_terms_candidate: Mapping[str, Any] | None = None,
    requested_actions: Sequence[str] | None = None,
    extra_fields: Mapping[str, Any] | None = None
) -> Dict[str, Any]:
    data = load_business_cloud_exchange_map()
    task_type = classify_business_cloud_task(intent_text)
    actions = _actions(requested_actions)
    blocked_actions = sorted(actions & HARD_RISK_ACTIONS)
    evidence = list(evidence_refs or [])
    exchange_terms = dict(exchange_terms_candidate or {})
    extra = dict(extra_fields or {})

    missing_fields = []
    required_payload = {
        "intent_goal": intent_text,
        "merchant_ref": merchant_ref,
        "organization_ref": organization_ref,
        "business_cloud_ref": business_cloud_ref,
        "requester_role_ref": requester_role_ref
    }
    for key, value in required_payload.items():
        if not _present(value):
            missing_fields.append(key)

    if task_type in {"ticket_candidate", "happiness_coin_exchange"} and not exchange_terms:
        missing_fields.append("exchange_terms_candidate")

    if task_type == "business_info_share" and not evidence:
        missing_fields.append("evidence_refs")

    base = {
        "task_type": task_type,
        "organization_ref": organization_ref,
        "business_cloud_ref": business_cloud_ref,
        "merchant_ref": merchant_ref,
        "requester_role_ref": requester_role_ref,
        "intent_goal": intent_text,
        "evidence_refs": evidence,
        "exchange_terms_candidate": exchange_terms,
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
        reason = "MISSING_REQUIRED_BUSINESS_CLOUD_FIELD"
    else:
        decision = "PASS_CANDIDATE"
        reason = "BUSINESS_CLOUD_CANDIDATE_READY_FOR_REVIEW"

    return {
        "STATE": decision,
        "candidate_ref": f"business_cloud_candidate:{fp}",
        "candidate_type": "wuchang_business_cloud_exchange_candidate",
        "task_type": task_type,
        "organization_ref": organization_ref,
        "business_cloud_ref": business_cloud_ref,
        "merchant_ref": merchant_ref,
        "requester_role_ref": requester_role_ref,
        "intent_goal": intent_text,
        "evidence_refs": evidence,
        "exchange_terms_candidate": exchange_terms,
        "formal_exchange": False,
        "payment_capture": False,
        "real_money_exchange": False,
        "legal_tender_claim": False,
        "token_mint": False,
        "onchain_transfer": False,
        "redeem_real_value": False,
        "issue_real_ticket": False,
        "publish_now": False,
        "db_write": False,
        "deploy": False,
        "restart": False,
        "router_write": False,
        "missing_fields": missing_fields,
        "blocked_actions": blocked_actions,
        "review_chain": data["review_chain"],
        "eight_d_packet": {
            "d1_intent": "business_cloud_exchange_and_info_platform",
            "d2_state": decision,
            "d3_coordinate": {
                "organization_ref": organization_ref,
                "business_cloud_ref": business_cloud_ref,
                "merchant_ref": merchant_ref,
                "requester_role_ref": requester_role_ref
            },
            "d4_evidence": {
                "evidence_refs": evidence,
                "candidate_fingerprint": fp
            },
            "d5_execution": {
                "mode": "candidate_only",
                "formal_exchange": False,
                "payment_capture": False,
                "db_write": False,
                "deploy": False,
                "restart": False
            },
            "d6_technical_definition": "AI transforms business cloud intent into merchant/ticket/happiness-coin/info-sharing candidate packet",
            "d7_risk": {
                "missing_fields": missing_fields,
                "blocked_actions": blocked_actions,
                "formal_exchange_blocked": True,
                "payment_capture_blocked": True
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
            "next": "BUSINESS_CLOUD_OWNER_ADMIN_TOTAL_FIELD_REVIEW"
        }
    }


def render_business_cloud_member_response(candidate: Mapping[str, Any]) -> Dict[str, Any]:
    decision = str(candidate.get("STATE") or "HOLD")
    task_type = str(candidate.get("task_type") or "")

    if decision == "PASS_CANDIDATE":
        if task_type == "happiness_coin_exchange":
            msg = "我先幫你整理幸福幣交換候選草稿，正式交換前會交給商業雲與總場確認。"
        elif task_type == "ticket_candidate":
            msg = "我先幫你整理票券候選草稿，正式發券或兌換前會交給商業雲與總場確認。"
        elif task_type == "business_info_share":
            msg = "我先幫你整理社區商業資訊共享候選稿，發布前會交給商業雲與總場確認。"
        else:
            msg = "我先幫你整理商家資料候選草稿，啟用前會交給商業雲與總場確認。"
    elif decision == "BLOCK":
        msg = ROOKIE_MESSAGE
    else:
        msg = "資料還不夠，我先幫你列成缺件候選，交給店長或學長確認。"

    return {
        "decision": decision,
        "member_facing_message": msg,
        "formal_exchange": False,
        "payment_capture": False,
        "next_action": "BUSINESS_CLOUD_OWNER_ADMIN_TOTAL_FIELD_REVIEW"
    }
