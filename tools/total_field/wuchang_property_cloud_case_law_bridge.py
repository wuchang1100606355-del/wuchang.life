"""Wuchang Property Cloud case/law/group-member bridge.

Property Cloud scope:
- community mediator
- property case query AI
- subsidy candidate links
- excellent community application candidates
- property law collection candidates
- group member affiliation to business cloud / property cloud / dual cloud

Candidate-only:
- no formal legal advice
- no formal submission
- no public publish
- no DB write
- no deploy / restart
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence


DEFAULT_MAP_PATH = Path("configs/total_field/wuchang_property_cloud_case_law_map.json")
ROOKIE_MESSAGE = "這個我不懂，我只是個菜鳥，我幫你問店長或學長"

HARD_RISK_ACTIONS = {
    "formal_legal_advice",
    "legal_conclusion",
    "formal_submission",
    "public_publish",
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


def load_property_cloud_map(path: str | Path = DEFAULT_MAP_PATH) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    if data.get("mode") != "candidate_only_no_formal_legal_advice_no_submission":
        raise ValueError("property cloud map must remain candidate-only")

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
        "formal_legal_advice",
        "formal_submission",
        "public_publish",
        "member_plaintext_exposure",
        "production_activation"
    ]
    bad = [key for key in required_false if policy.get(key) is not False]
    if bad:
        raise ValueError("unsafe policy: " + ",".join(bad))

    return data


def classify_property_cloud_task(intent_text: str) -> str:
    text = str(intent_text or "").lower()

    if any(x in text for x in ["公道伯", "調解", "協調", "mediator", "mediation"]):
        return "community_mediation"

    if any(x in text for x in ["案例", "判例", "糾紛", "case", "query"]):
        return "property_case_query"

    if any(x in text for x in ["補助", "subsidy", "grant"]):
        return "property_subsidy"

    if any(x in text for x in ["優良社區", "申報", "評鑑", "excellent community"]):
        return "excellent_community_application"

    if any(x in text for x in ["法令", "法規", "物業法", "公寓大廈", "law", "regulation"]):
        return "property_law_collection"

    if any(x in text for x in ["團體會員", "雙雲", "商業雲", "物業雲", "掛接", "affiliation"]):
        return "group_member_cloud_affiliation"

    return "property_case_query"


def classify_group_member_cloud_affiliation(group_member_nature: str) -> Dict[str, Any]:
    data = load_property_cloud_map()
    n = str(group_member_nature or "").lower()
    rules = data["group_member_cloud_affiliation"]

    business_words = ["商家", "店", "票券", "幸福幣", "merchant", "store", "vendor", "commercial"]
    property_words = ["物業", "管委會", "大樓", "社區", "公寓", "管理公司", "property", "committee", "building"]
    dual_words = ["社區商家", "大樓店家", "物業服務商家", "雙雲", "business and property"]

    if any(x in n for x in dual_words) or (any(x in n for x in business_words) and any(x in n for x in property_words)):
        clouds = ["business_cloud", "property_cloud"]
        classification = "dual_cloud"
    elif any(x in n for x in property_words):
        clouds = ["property_cloud"]
        classification = "property_cloud"
    elif any(x in n for x in business_words):
        clouds = ["business_cloud"]
        classification = "business_cloud"
    else:
        clouds = ["property_cloud"]
        classification = "property_cloud_default_review"

    return {
        "classification": classification,
        "cloud_affiliations": clouds,
        "requires_owner_review": True,
        "source_rule": rules["principle"]
    }


def build_property_cloud_candidate(
    *,
    intent_text: str,
    group_member_ref: str = "group_member_ref:candidate",
    group_member_nature: str = "property_cloud_candidate",
    organization_ref: str = "org_ref:wuchang_community_development_association",
    property_cloud_ref: str = "branch_unit_ref:property_cloud",
    requester_role_ref: str = "role_ref:property_cloud_candidate",
    source_refs: Sequence[str] | None = None,
    evidence_refs: Sequence[str] | None = None,
    requested_actions: Sequence[str] | None = None,
    extra_fields: Mapping[str, Any] | None = None
) -> Dict[str, Any]:
    data = load_property_cloud_map()
    task_type = classify_property_cloud_task(intent_text)
    action_set = _actions(requested_actions)
    blocked_actions = sorted(action_set & HARD_RISK_ACTIONS)
    sources = list(source_refs or [])
    evidence = list(evidence_refs or [])
    extra = dict(extra_fields or {})
    affiliation = classify_group_member_cloud_affiliation(group_member_nature)

    missing_fields = []
    required_payload = {
        "intent_goal": intent_text,
        "organization_ref": organization_ref,
        "property_cloud_ref": property_cloud_ref,
        "group_member_ref": group_member_ref,
        "group_member_nature": group_member_nature,
        "requester_role_ref": requester_role_ref
    }
    for key, value in required_payload.items():
        if not _present(value):
            missing_fields.append(key)

    if task_type in {"property_case_query", "property_law_collection"} and not sources:
        missing_fields.append("source_refs")

    if task_type == "excellent_community_application" and not evidence:
        missing_fields.append("evidence_refs")

    base = {
        "task_type": task_type,
        "organization_ref": organization_ref,
        "property_cloud_ref": property_cloud_ref,
        "group_member_ref": group_member_ref,
        "group_member_nature": group_member_nature,
        "cloud_affiliations": affiliation["cloud_affiliations"],
        "requester_role_ref": requester_role_ref,
        "intent_goal": intent_text,
        "source_refs": sources,
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
        reason = "MISSING_REQUIRED_PROPERTY_CLOUD_FIELD"
    else:
        decision = "PASS_CANDIDATE"
        reason = "PROPERTY_CLOUD_CANDIDATE_READY_FOR_REVIEW"

    return {
        "STATE": decision,
        "candidate_ref": f"property_cloud_candidate:{fp}",
        "candidate_type": "wuchang_property_cloud_case_law_candidate",
        "task_type": task_type,
        "organization_ref": organization_ref,
        "property_cloud_ref": property_cloud_ref,
        "group_member_ref": group_member_ref,
        "group_member_nature": group_member_nature,
        "group_member_affiliation": affiliation,
        "requester_role_ref": requester_role_ref,
        "intent_goal": intent_text,
        "source_refs": sources,
        "evidence_refs": evidence,
        "formal_legal_advice": False,
        "formal_submission": False,
        "public_publish": False,
        "db_write": False,
        "deploy": False,
        "restart": False,
        "router_write": False,
        "missing_fields": missing_fields,
        "blocked_actions": blocked_actions,
        "review_chain": data["review_chain"],
        "eight_d_packet": {
            "d1_intent": "property_cloud_case_law_and_group_member_affiliation",
            "d2_state": decision,
            "d3_coordinate": {
                "organization_ref": organization_ref,
                "property_cloud_ref": property_cloud_ref,
                "group_member_ref": group_member_ref,
                "cloud_affiliations": affiliation["cloud_affiliations"]
            },
            "d4_evidence": {
                "source_refs": sources,
                "evidence_refs": evidence,
                "candidate_fingerprint": fp
            },
            "d5_execution": {
                "mode": "candidate_only",
                "formal_legal_advice": False,
                "formal_submission": False,
                "db_write": False,
                "deploy": False,
                "restart": False
            },
            "d6_technical_definition": "AI transforms property cloud intent into case/law/subsidy/application/group-affiliation candidate packet",
            "d7_risk": {
                "missing_fields": missing_fields,
                "blocked_actions": blocked_actions,
                "formal_legal_advice_blocked": True,
                "formal_submission_blocked": True
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
            "next": "PROPERTY_CLOUD_OWNER_ADMIN_TOTAL_FIELD_REVIEW"
        }
    }


def render_property_cloud_member_response(candidate: Mapping[str, Any]) -> Dict[str, Any]:
    decision = str(candidate.get("STATE") or "HOLD")
    task_type = str(candidate.get("task_type") or "")

    if decision == "PASS_CANDIDATE":
        if task_type == "community_mediation":
            msg = "我先幫你整理成社區公道伯協調候選稿，正式處理前會交給物業雲與總場確認。"
        elif task_type == "property_case_query":
            msg = "我先幫你整理物業案例查詢候選結果，正式引用前會交給物業雲與總場確認。"
        elif task_type == "property_law_collection":
            msg = "我先幫你整理物業法令收集候選清單，正式法律判斷前會交給物業雲與總場確認。"
        elif task_type == "excellent_community_application":
            msg = "我先幫你整理優良社區申報候選包，正式申報前會交給物業雲與總場確認。"
        elif task_type == "group_member_cloud_affiliation":
            msg = "我先幫你整理團體會員雲別掛接候選，正式啟用前會交給總場確認。"
        else:
            msg = "我先幫你整理物業雲候選資料，正式處理前會交給物業雲與總場確認。"
    elif decision == "BLOCK":
        msg = ROOKIE_MESSAGE
    else:
        msg = "資料還不夠，我先幫你列成缺件候選，交給店長或學長確認。"

    return {
        "decision": decision,
        "member_facing_message": msg,
        "formal_legal_advice": False,
        "formal_submission": False,
        "next_action": "PROPERTY_CLOUD_OWNER_ADMIN_TOTAL_FIELD_REVIEW"
    }
