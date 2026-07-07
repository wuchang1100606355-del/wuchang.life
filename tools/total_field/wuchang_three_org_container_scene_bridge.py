"""Wuchang three-organization container scene bridge.

商業組織 / 物業組織 / 公益組織三大模組共撐 Odoo 社區。

Local devices can switch scenes by container-profile candidates:
- business scene
- property scene
- association / public welfare scene

Candidate-only:
- no docker action
- no live container switch
- no deploy
- no restart
- no DB write
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence


DEFAULT_MAP_PATH = Path("configs/total_field/wuchang_three_org_container_scene_map.json")
ROOKIE_MESSAGE = "這個我不懂，我只是個菜鳥，我幫你問店長或學長"

HARD_RISK_ACTIONS = {
    "delete",
    "restore",
    "deploy",
    "restart",
    "db_write",
    "router_write",
    "docker_compose_up",
    "docker_restart",
    "live_container_switch",
    "production_activation",
    "payment_capture",
    "formal_public_service_claim",
    "member_plaintext_exposure",
    "secret_exposure"
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


def load_three_org_scene_map(path: str | Path = DEFAULT_MAP_PATH) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    if data.get("mode") != "candidate_only_no_live_container_action":
        raise ValueError("three-org scene map must remain candidate-only")

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
        "docker_compose_up",
        "docker_restart",
        "live_container_switch",
        "production_activation",
        "payment_capture",
        "formal_public_service_claim",
        "member_plaintext_exposure",
        "secret_exposure"
    ]
    bad = [key for key in required_false if policy.get(key) is not False]
    if bad:
        raise ValueError("unsafe policy: " + ",".join(bad))

    modules = data["odoo_community_core"]["supporting_modules"]
    if modules != ["business_organization", "property_organization", "public_welfare_organization"]:
        raise ValueError("Odoo community must be supported by three org modules")

    return data


def classify_scene(intent_text: str) -> str:
    text = str(intent_text or "").lower()

    if any(x in text for x in ["商業", "商家", "票券", "幸福幣", "商業雲", "business", "merchant"]):
        return "business_scene"

    if any(x in text for x in ["物業", "公道伯", "管委會", "法令", "優良社區", "property"]):
        return "property_scene"

    if any(x in text for x in ["協會", "公益", "志工", "社工", "照服", "許願樹", "基金", "association", "welfare"]):
        return "association_scene"

    return "business_scene"


def resolve_scene_profile(scene: str, *, map_data: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    data = dict(map_data or load_three_org_scene_map())
    profiles = data["local_device_scene_profiles"]
    resolved = str(scene or "business_scene")
    profile = dict(profiles.get(resolved) or profiles["business_scene"])

    return {
        "scene": resolved if resolved in profiles else "business_scene",
        "zh": profile["zh"],
        "container_profile_candidate": profile["container_profile"],
        "primary_module": profile["primary_module"],
        "visible_modules": list(profile["visible_modules"]),
        "landing_message": profile["landing_message"],
        "live_container_action": False
    }


def build_three_org_scene_candidate(
    *,
    intent_text: str,
    local_device_ref: str = "local_device_ref:node_c_or_lobby_xiaoj",
    requested_scene: str | None = None,
    requested_actions: Sequence[str] | None = None,
    evidence_refs: Sequence[str] | None = None,
    extra_fields: Mapping[str, Any] | None = None
) -> Dict[str, Any]:
    data = load_three_org_scene_map()
    actions = _actions(requested_actions)
    blocked_actions = sorted(actions & HARD_RISK_ACTIONS)
    scene = requested_scene or classify_scene(intent_text)
    profile = resolve_scene_profile(scene, map_data=data)
    evidence = list(evidence_refs or [])
    extra = dict(extra_fields or {})

    missing_fields = []
    for key, value in {
        "intent_goal": intent_text,
        "target_scene": profile["scene"],
        "primary_module": profile["primary_module"],
        "visible_modules": profile["visible_modules"],
        "local_device_ref": local_device_ref,
        "container_profile_candidate": profile["container_profile_candidate"]
    }.items():
        if not value:
            missing_fields.append(key)

    base = {
        "intent_text": intent_text,
        "local_device_ref": local_device_ref,
        "scene_profile": profile,
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
        reason = "MISSING_REQUIRED_THREE_ORG_SCENE_FIELD"
    else:
        decision = "PASS_CANDIDATE"
        reason = "THREE_ORG_CONTAINER_SCENE_CANDIDATE_READY_FOR_TOTAL_FIELD_REVIEW"

    return {
        "STATE": decision,
        "candidate_ref": f"three_org_scene_candidate:{fp}",
        "candidate_type": "wuchang_three_org_container_scene_candidate",
        "intent_goal": intent_text,
        "odoo_community_core": data["odoo_community_core"],
        "three_org_modules": data["three_org_modules"],
        "target_scene": profile["scene"],
        "primary_module": profile["primary_module"],
        "visible_modules": profile["visible_modules"],
        "local_device_ref": local_device_ref,
        "container_profile_candidate": profile["container_profile_candidate"],
        "landing_message": profile["landing_message"],
        "business_landing_showcases_property_and_association": profile["scene"] == "business_scene",
        "live_container_switch": False,
        "docker_compose_up": False,
        "docker_restart": False,
        "db_write": False,
        "deploy": False,
        "restart": False,
        "payment_capture": False,
        "production_activation": False,
        "evidence_refs": evidence,
        "missing_fields": missing_fields,
        "blocked_actions": blocked_actions,
        "review_chain": data["scene_switch_rules"]["same_review_chain"],
        "eight_d_packet": {
            "d1_intent": "three_org_modules_support_odoo_community_container_scene_switch",
            "d2_state": decision,
            "d3_coordinate": {
                "target_scene": profile["scene"],
                "primary_module": profile["primary_module"],
                "visible_modules": profile["visible_modules"],
                "local_device_ref": local_device_ref
            },
            "d4_evidence": {
                "evidence_refs": evidence,
                "candidate_fingerprint": fp
            },
            "d5_execution": {
                "mode": "candidate_only",
                "container_profile_candidate": profile["container_profile_candidate"],
                "live_container_switch": False,
                "docker_compose_up": False,
                "db_write": False,
                "deploy": False,
                "restart": False
            },
            "d6_technical_definition": "business_property_public_welfare_modules share Odoo community and local devices switch scene by container profile candidate",
            "d7_risk": {
                "blocked_actions": blocked_actions,
                "missing_fields": missing_fields,
                "live_container_switch_blocked": True,
                "docker_action_blocked": True
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


def render_three_org_scene_response(candidate: Mapping[str, Any]) -> Dict[str, Any]:
    decision = str(candidate.get("STATE") or "HOLD")

    if decision == "PASS_CANDIDATE":
        msg = str(candidate.get("landing_message") or "我先幫你整理三大模組 Odoo 社區候選場景，交給總場確認。")
    elif decision == "BLOCK":
        msg = ROOKIE_MESSAGE
    else:
        msg = "資料還不夠，我先幫你列成缺件候選，交給店長或學長確認。"

    return {
        "decision": decision,
        "member_facing_message": msg,
        "live_container_switch": False,
        "docker_compose_up": False,
        "db_write": False,
        "deploy": False,
        "restart": False,
        "next_action": "TOTAL_FIELD_OWNER_ADMIN_REVIEW"
    }
