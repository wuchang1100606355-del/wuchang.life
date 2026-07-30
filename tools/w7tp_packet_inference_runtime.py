#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W7TP packet-by-packet inference runtime v0.2.

This file is intentionally model-free: tables, rules, and the verifier produce
the packet chain. A model lane may be represented only as an unavailable stub.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

try:
    from .d3_coordinate_transition_candidate import transition_coordinate
except ImportError:  # pragma: no cover - direct script execution
    try:
        from tools.d3_coordinate_transition_candidate import transition_coordinate
    except ModuleNotFoundError:
        from d3_coordinate_transition_candidate import transition_coordinate


SAFETY_FLAGS = {
    "SECRET_READ": False,
    "MEMBER_PLAINTEXT_READ": False,
    "RAW_AUDIO_SAVED": False,
    "DB_WRITE": False,
    "PAYMENT_CAPTURE": False,
    "SERVICE_RESTART": False,
    "DEPLOY": False,
    "PRODUCTION_RELEASE": False,
    "EXTERNAL_API_CALL": False,
    "MODEL_REQUIRED": False,
    "LLM_AUTHORITY": False,
    "RUNTIME_AUTHORITY": False,
    "CANONICAL_8D_VERIFIER_REQUIRED": True,
}
ACTIVE_XIAOJ_VOICE_OUTPUT_PROJECTION_POINTER = (
    Path(__file__).resolve().parents[1]
    / "runtime/total_field/master_index"
    / "ACTIVE_XIAOJ_VERIFIED_OUTPUT_PROJECTION_POINTER.json"
)

SCENE_ALIAS_TABLE = {
    "STORE_CONTEXT": ["咖啡", "POS", "點餐", "結帳", "菜單", "客人", "店裡", "櫃台", "庫存", "外送", "訂單", "會員點數", "飲料", "拿鐵"],
    "PROPERTY_CONTEXT": ["物業", "管委會", "住戶", "大樓", "社區", "公告", "管理費", "公設", "修繕", "報修", "車位", "門禁", "管理員"],
    "ASSOCIATION_CONTEXT": ["協會", "公益", "會員治理", "志工", "補助", "社區發展", "活動報名", "服務使用", "資格審查"],
    "FOUNDER_CONTEXT": ["總場", "架構", "專利", "發明", "生成式傳輸", "8D", "封包推理", "部署策略", "維護", "commit", "Codex", "技術路線"],
    "CLAIMED_FOUNDER_CONTEXT": ["我是創辦人", "我是發明人", "我是江政隆", "我是隆哥", "我是理事長"],
    "GENERAL_CHAT_CONTEXT": ["你好", "你在嗎", "陪我聊", "心情不好", "我有點累", "你會做什麼", "下一步"],
}

SCENE_SCOPE_TABLE = {
    "STORE_CONTEXT": {
        "allowed_scope": ["recommend_order", "menu_query", "draft_order", "store_status_chat"],
        "forbidden_scope": ["payment_capture", "member_plaintext_read", "formal_pos_write_without_human_review"],
    },
    "PROPERTY_CONTEXT": {
        "allowed_scope": ["property_service_request_candidate", "announcement_draft", "repair_request_candidate", "resident_no_plaintext_context"],
        "forbidden_scope": ["resident_plaintext_read", "building_access_grant_without_verification", "payment_capture"],
    },
    "ASSOCIATION_CONTEXT": {
        "allowed_scope": ["association_service_admission_candidate", "activity_rsvp_candidate", "volunteer_service_candidate", "no_plaintext_member_context"],
        "forbidden_scope": ["member_plaintext_read", "subsidy_approval_without_verification"],
    },
    "FOUNDER_CONTEXT": {
        "allowed_scope": ["architecture_discussion", "codex_task_builder", "patent_non_confidential_draft", "total_field_debug"],
        "forbidden_scope": ["secret_read", "production_deploy_without_explicit_packet", "member_plaintext_read"],
    },
    "CLAIMED_FOUNDER_CONTEXT": {
        "allowed_scope": ["create_claimed_identity_packet", "ask_role_verification"],
        "forbidden_scope": ["grant_role_without_verification", "trust_claimed_identity", "secret_read", "member_plaintext_read"],
    },
    "DEV_DEVICE_CONTEXT": {
        "allowed_scope": ["architecture_discussion", "codex_task_builder", "total_field_debug", "non_confidential_patent_draft"],
        "forbidden_scope": ["secret_read", "member_plaintext_read", "payment_capture", "production_deploy_without_explicit_packet", "grant_identity_role"],
    },
    "VERIFIED_FOUNDER_ROLE": {
        "allowed_scope": ["architecture_discussion", "codex_task_builder", "patent_non_confidential_draft", "total_field_debug"],
        "forbidden_scope": ["secret_read", "member_plaintext_read", "payment_capture", "production_deploy_without_explicit_packet"],
    },
    "GENERAL_CHAT_CONTEXT": {
        "allowed_scope": ["general_chat", "supportive_reply", "capability_intro"],
        "forbidden_scope": ["medical_diagnosis", "legal_advice", "financial_advice", "identity_verification_promise"],
    },
    "UNKNOWN_CONTEXT": {
        "allowed_scope": ["ask_clarifying_question"],
        "forbidden_scope": ["payment_capture", "member_plaintext_read", "secret_read"],
    },
}

DEV_ROLE_REFS = {
    "role_ref:dev:founder_maintainer": {
        "developer_device_trust": True,
        "verified_context_type": "DEV_DEVICE_CONTEXT",
        "developer_scope": ["architecture_discussion", "codex_task_builder", "patent_non_confidential_draft", "total_field_debug"],
    },
    "role_ref:dev:store_operator": {
        "developer_full_context_switch": True,
        "verified_context_type": "STORE_CONTEXT",
        "developer_scope": ["recommend_order", "menu_query", "draft_order", "store_status_chat"],
    },
    "role_ref:dev:property_operator": {
        "developer_full_context_switch": True,
        "verified_context_type": "PROPERTY_CONTEXT",
        "developer_scope": ["property_service_request_candidate", "announcement_draft", "repair_request_candidate"],
    },
    "role_ref:dev:association_operator": {
        "developer_full_context_switch": True,
        "verified_context_type": "ASSOCIATION_CONTEXT",
        "developer_scope": ["association_service_admission_candidate", "activity_rsvp_candidate", "volunteer_service_candidate"],
    },
}

AUTHENTICATED_FOUNDER_REFS = {"role_ref:auth:founder", "role_ref:verified:founder"}

INTENT_ALIAS_TABLE = {
    "recommend_order": ["推薦", "喝什麼", "好喝", "幫我配", "不苦", "清爽", "順口", "有點累", "想喝"],
    "ask_menu": ["菜單", "品項", "價格", "menu"],
    "draft_order": ["幫我點", "我要一杯", "加入訂單", "下單", "點餐"],
    "member_lookup_masked": ["查會員"],
    "member_plaintext_request": ["完整電話", "完整地址", "身份證", "身分證", "會員明文"],
    "identity_context_query": ["你知道我是誰", "你認識我", "我是誰", "認得我", "我的資訊", "你沒有我的資訊", "你有我的資訊"],
    "member_context_query": ["你知道我的會員資料", "我的會員資料", "會員資料", "會員狀態", "我的點數", "點數"],
    "claimed_founder_identity": ["我是創辦人", "我是發明人", "我是理事長", "我是江政隆", "我是隆哥", "創辦人江政隆"],
    "role_context_query": ["我的角色是什麼", "我是什麼角色", "我有什麼權限", "角色是什麼", "我的身份", "我的身分"],
    "property_service_request": ["報修", "公設壞了", "修繕", "住戶說", "管理員"],
    "association_activity_query": ["報名協會活動", "協會活動", "活動報名", "志工", "公益"],
    "architecture_discussion": ["生成式傳輸", "封包推理", "架構", "總場", "技術路線", "下一步怎麼開發"],
    "general_chat": ["你好", "陪我聊", "心情不好", "我有點累"],
    "capability_intro": ["你會做什麼", "你能做什麼", "介紹能力"],
    "payment_request": ["結帳", "付款", "刷卡", "收錢", "付錢"],
}

SLOT_PATTERN_TABLE = {
    "taste_preference": {
        "refreshing": ["清爽", "輕一點", "低酸", "果香"],
        "not_bitter": ["不苦", "不要苦", "順口"],
        "milky": ["拿鐵", "牛奶", "奶"],
    },
    "condition": {
        "tired": ["累", "疲勞", "沒精神"],
        "hot": ["熱", "很熱", "悶"],
    },
    "risk_signal": {
        "allergy": ["過敏", "乳糖", "不能喝奶", "牛奶敏感", "堅果過敏", "敏感"],
        "payment": ["付款", "結帳", "刷卡", "收錢"],
        "member_plaintext": ["完整電話", "完整地址", "身份證", "身分證", "會員明文"],
        "identity_claim": ["我是創辦人", "我是發明人", "我是理事長", "我是江政隆", "我是隆哥", "創辦人江政隆"],
    },
}

ROUTE_TABLE = {
    "recommend_order": {
        "rule_ref": "rules/cafe_recommend_v2",
        "table_ref": "tables/cafe_pairing_v2",
        "template_ref": "templates/recommend_v2",
        "route": "cafe_recommendation_lane",
    },
    "ask_menu": {
        "rule_ref": "rules/menu_query_v1",
        "table_ref": "tables/menu_v1",
        "template_ref": "templates/menu_v1",
        "route": "menu_query_lane",
    },
    "draft_order": {
        "rule_ref": "rules/draft_order_candidate_v1",
        "table_ref": "tables/order_draft_v1",
        "template_ref": "templates/draft_order_v1",
        "route": "draft_order_candidate_lane",
    },
    "member_lookup_masked": {
        "rule_ref": "rules/member_masked_v1",
        "table_ref": "tables/member_masked_v1",
        "template_ref": "templates/member_masked_v1",
        "route": "member_masked_lane",
    },
    "member_plaintext_request": {
        "rule_ref": "rules/member_plaintext_block_v1",
        "table_ref": "tables/member_no_plaintext_v1",
        "template_ref": "templates/member_plaintext_block_v1",
        "route": "blocked_member_plaintext_lane",
    },
    "identity_context_query": {
        "rule_ref": "rules/identity_context_boundary_v1",
        "table_ref": "tables/identity_context_ref_status_v1",
        "template_ref": "templates/identity_context_hold_v1",
        "route": "safe_identity_context_lane",
    },
    "member_context_query": {
        "rule_ref": "rules/profile_ref_status_v1",
        "table_ref": "tables/member_context_ref_status_v1",
        "template_ref": "templates/member_context_hold_v1",
        "route": "safe_member_context_lane",
    },
    "role_context_query": {
        "rule_ref": "rules/role_ref_query_v1",
        "table_ref": "tables/role_ref_status_v1",
        "template_ref": "templates/role_ref_hold_v1",
        "route": "safe_role_ref_lane",
    },
    "claimed_founder_identity": {
        "rule_ref": "rules/claimed_identity_packet_v1",
        "table_ref": "tables/claimed_identity_boundary_v1",
        "template_ref": "templates/claimed_identity_hold_v1",
        "route": "claimed_identity_review_lane",
    },
    "property_service_request": {
        "rule_ref": "rules/property_service_candidate_v1",
        "table_ref": "tables/property_context_v1",
        "template_ref": "templates/property_service_hold_v1",
        "route": "property_service_candidate_lane",
    },
    "association_activity_query": {
        "rule_ref": "rules/association_activity_candidate_v1",
        "table_ref": "tables/association_context_v1",
        "template_ref": "templates/association_activity_hold_v1",
        "route": "association_activity_candidate_lane",
    },
    "architecture_discussion": {
        "rule_ref": "rules/architecture_discussion_v1",
        "table_ref": "tables/founder_context_v1",
        "template_ref": "templates/architecture_discussion_v1",
        "route": "architecture_discussion_lane",
    },
    "general_chat": {
        "rule_ref": "rules/general_chat_v1",
        "table_ref": "tables/general_chat_v1",
        "template_ref": "templates/general_chat_v1",
        "route": "general_chat_lane",
    },
    "capability_intro": {
        "rule_ref": "rules/capability_intro_v1",
        "table_ref": "tables/capability_intro_v1",
        "template_ref": "templates/capability_intro_v1",
        "route": "capability_intro_lane",
    },
    "payment_request": {
        "rule_ref": "rules/payment_human_review_v1",
        "table_ref": "tables/payment_boundary_v1",
        "template_ref": "templates/payment_hold_v1",
        "route": "payment_hold_lane",
    },
    "unknown": {
        "rule_ref": "rules/unknown_v1",
        "table_ref": "tables/fallback_v1",
        "template_ref": "templates/clarify_v1",
        "route": "clarify_lane",
    },
}

RISK_POLICY_TABLE = {
    "member_plaintext": {"decision": "BLOCK", "reasons": ["member plaintext request blocked"]},
    "payment": {"decision": "HOLD", "reasons": ["payment capture requires human authority"]},
    "allergy": {"decision": "HOLD", "reasons": ["allergy or intolerance signal needs confirmation"]},
    "identity_claim": {"decision": "HOLD", "reasons": ["claimed identity requires verification"]},
    "identity_boundary": {"decision": "HOLD", "reasons": ["identity context requires role_ref or authenticated context"]},
    "member_context": {"decision": "HOLD", "reasons": ["member context requires member_ref or authenticated context"]},
    "role_context": {"decision": "HOLD", "reasons": ["role context requires role_ref or authenticated context"]},
    "claimed_founder_context": {"decision": "HOLD", "reasons": ["claimed founder context requires role verification"]},
    "low_confidence": {"decision": "HOLD", "reasons": ["low intent confidence"]},
    "draft_order": {"decision": "HOLD", "reasons": ["formal order write requires counter confirmation"]},
    "none": {"decision": "CONTINUE", "reasons": ["packet verified"]},
}

CAPABILITY_TABLE = {
    "recommend_order": {
        "allowed_actions": ["show_recommendation", "speak_recommendation", "create_draft_order_candidate"],
        "forbidden_actions": ["formal_pos_order_without_human_review", "payment_capture"],
    },
    "ask_menu": {
        "allowed_actions": ["show_menu", "speak_menu"],
        "forbidden_actions": ["payment_capture"],
    },
    "draft_order": {
        "allowed_actions": ["create_draft_order_candidate", "ask_human_confirmation"],
        "forbidden_actions": ["formal_pos_order_without_human_review", "payment_capture"],
    },
    "member_lookup_masked": {
        "allowed_actions": ["show_masked_member_status"],
        "forbidden_actions": ["show_member_plaintext", "export_member_plaintext"],
    },
    "member_plaintext_request": {
        "allowed_actions": [],
        "forbidden_actions": ["member_plaintext_read", "show_member_plaintext", "export_member_plaintext"],
    },
    "identity_context_query": {
        "allowed_actions": ["show_identity_context_boundary", "request_role_ref_or_authenticated_context"],
        "forbidden_actions": ["member_plaintext_read", "db_read", "show_member_plaintext", "export_member_plaintext"],
    },
    "member_context_query": {
        "allowed_actions": ["show_member_ref_status_boundary", "request_member_ref_or_authenticated_context"],
        "forbidden_actions": ["member_plaintext_read", "db_read", "show_member_plaintext", "export_member_plaintext"],
    },
    "role_context_query": {
        "allowed_actions": ["show_role_ref_status_candidate", "ask_identity_verification"],
        "forbidden_actions": ["trust_claimed_identity", "member_plaintext_read", "db_read", "show_member_plaintext"],
    },
    "claimed_founder_identity": {
        "allowed_actions": ["create_claimed_identity_packet", "ask_identity_verification"],
        "forbidden_actions": ["trust_claimed_identity", "grant_role_without_verification", "member_plaintext_read", "db_read", "write_identity_record"],
    },
    "property_service_request": {
        "allowed_actions": ["repair_request_candidate", "resident_no_plaintext_context"],
        "forbidden_actions": ["resident_plaintext_read", "member_plaintext_read", "payment_capture"],
    },
    "association_activity_query": {
        "allowed_actions": ["activity_rsvp_candidate", "association_service_admission_candidate"],
        "forbidden_actions": ["member_plaintext_read", "subsidy_approval_without_verification"],
    },
    "architecture_discussion": {
        "allowed_actions": ["architecture_discussion", "total_field_debug"],
        "forbidden_actions": ["secret_read", "production_deploy_without_explicit_packet", "member_plaintext_read"],
    },
    "general_chat": {
        "allowed_actions": ["general_chat", "supportive_reply"],
        "forbidden_actions": ["medical_diagnosis", "legal_advice", "financial_advice", "identity_verification_promise"],
    },
    "capability_intro": {
        "allowed_actions": ["capability_intro"],
        "forbidden_actions": ["llm_authority", "member_plaintext_read", "payment_capture"],
    },
    "payment_request": {
        "allowed_actions": ["ask_human_confirmation"],
        "forbidden_actions": ["payment_capture", "auto_charge"],
    },
    "unknown": {
        "allowed_actions": ["ask_clarifying_question"],
        "forbidden_actions": ["payment_capture", "member_plaintext_read"],
    },
}

PAIRING_TABLE = {
    ("not_bitter", "tired"): {"item": "拿鐵或低酸手沖", "style": "順口、不太苦", "why": "偵測到不苦偏好與疲勞狀態"},
    ("refreshing", "default"): {"item": "淺焙手沖或冰美式", "style": "清爽", "why": "偵測到清爽偏好"},
    ("milky", "default"): {"item": "拿鐵", "style": "奶香、順口", "why": "偵測到奶類偏好"},
    ("default", "default"): {"item": "拿鐵或今日手沖", "style": "安全泛用", "why": "未取得明確偏好"},
}

TEMPLATE_TABLE = {
    "recommend_allow": "今天可以先考慮{style}的選項，例如{item}。原因是：{why}。",
    "recommend_hold": "我可以先幫你推薦{style}的候選選項，例如{item}。但需要先確認：{reason}。",
    "payment_hold": "付款或結帳必須由櫃台人工確認；此流程只產生候選提示，不會自動扣款。",
    "member_block": "會員明文資料不可由此流程讀取或顯示。",
    "draft_hold": "可以建立候選訂單草稿，但正式寫入 POS 前必須由櫃台確認。",
    "menu_allow": "目前可以查詢菜單與可供應品項；不會觸發下單或付款。",
    "identity_context_hold": "我目前不能只憑一句話確認你的真實身分。若你已登入或提供 8D 身分封包，我可以用 role_ref / member_ref 的去識別化方式判斷你的角色與可用權限；不會顯示會員明文資料。",
    "member_context_hold": "我可以處理會員情境查詢，但目前只使用 member_ref / role_ref 這類去識別化參照；不讀 DB、不顯示會員明文資料，也不會輸出電話、地址或證件資料。",
    "role_context_hold": "我不能只靠這句話判定你的角色或權限。請提供已驗證的 role_ref、登入狀態或 8D 身分封包；通過 verifier 後才會決定可用功能。",
    "claimed_founder_hold": "我收到你的身分聲明，但不會直接把聲明視為已驗證身分。總場會先建立 claimed_identity_packet，並等待 role_ref、登入狀態或 verifier 驗證後，才決定可使用的功能。",
    "property_service_hold": "我可以先建立物業服務候選脈絡，例如報修或公告草稿；但不讀住戶明文，也不授權門禁或付款。",
    "association_activity_hold": "我可以協助建立協會活動或服務使用候選流程；資格、補助或會員治理仍需 verifier 與去識別化參照確認。",
    "architecture_discussion": "這屬於總場工程/架構討論脈絡。我可以用封包、verifier、PR layer 與安全邊界來整理下一步，但不讀 secret、不部署。",
    "general_chat": "我在，可以陪你聊一下。我會保持自然陪伴，但不提供醫療判斷、法律或金融建議，也不承諾身分驗證。",
    "capability_intro": "我能把自然語言轉成 8D packet chain，經 verifier 決定 ALLOW/HOLD/BLOCK，再用 candidate-only PR layer 潤飾回答；不讀會員明文、不付款、不讓模型掌權。",
    "clarify_hold": "目前意圖不明，先進入補問流程。",
}


def sha(value: Any) -> str:
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def now_unix() -> int:
    return int(time.time())


def pick_slots(text: str) -> dict[str, str]:
    lowered = text.lower()
    slots: dict[str, str] = {}
    for slot_name, patterns in SLOT_PATTERN_TABLE.items():
        for slot_value, words in patterns.items():
            if any(word.lower() in lowered for word in words):
                slots[slot_name] = slot_value
                break
    if any(word.lower() in lowered for word in INTENT_ALIAS_TABLE["claimed_founder_identity"]):
        slots["claimed_identity_packet"] = "CLAIMED_IDENTITY_PACKET"
    return slots


def detect_scene_context(
    text: str,
    dev_role_ref: str = "",
    dev_identity_switch: bool = False,
    authenticated_role_ref: str = "",
    signed_identity_packet_ref: str = "",
) -> dict[str, Any]:
    lowered = text.lower()
    scores = {
        context_type: sum(1 for word in aliases if word.lower() in lowered)
        for context_type, aliases in SCENE_ALIAS_TABLE.items()
    }
    if scores["CLAIMED_FOUNDER_CONTEXT"] > 0:
        context_type = "CLAIMED_FOUNDER_CONTEXT"
    else:
        context_type = max(scores, key=scores.get)
    score = scores.get(context_type, 0)
    if score <= 0:
        context_type = "UNKNOWN_CONTEXT"
        confidence = "L1"
    elif score == 1:
        confidence = "L2"
    else:
        confidence = "L3"

    dev_role = DEV_ROLE_REFS.get(dev_role_ref) if dev_identity_switch else None
    signed_founder_packet = signed_identity_packet_ref.startswith("signed_identity_packet:founder")
    founder_role_verified = authenticated_role_ref in AUTHENTICATED_FOUNDER_REFS or signed_founder_packet
    if founder_role_verified:
        context_type = "VERIFIED_FOUNDER_ROLE"
        confidence = "L3"
    elif dev_role:
        context_type = "DEV_DEVICE_CONTEXT"
        confidence = "L3"

    scope = SCENE_SCOPE_TABLE[context_type]
    scene_context = {
        "context_type": context_type,
        "confidence_level": confidence,
        "accepted_as_truth": bool(founder_role_verified),
        "device_trust": bool(dev_role),
        "identity_verified": bool(founder_role_verified),
        "accepted_as_person_identity": bool(founder_role_verified),
        "requires_role_verification": False if founder_role_verified else context_type in {"FOUNDER_CONTEXT", "CLAIMED_FOUNDER_CONTEXT", "DEV_DEVICE_CONTEXT"},
        "allowed_scope": list(scope["allowed_scope"]),
        "forbidden_scope": list(scope["forbidden_scope"]),
    }
    if dev_role:
        scene_context["dev_identity_override"] = {
            "enabled": True,
            "role_ref": dev_role_ref,
            "verification_source": "explicit_dev_device_role_ref",
            "device_trust": True,
            "identity_verified": False,
            "accepted_as_person_identity": False,
            "production_authority": False,
            "plaintext_access": False,
            "db_read": False,
        }
        scene_context["allowed_scope"] = list(dict.fromkeys(scene_context["allowed_scope"] + dev_role["developer_scope"]))
    if founder_role_verified:
        scene_context["verified_founder_role"] = {
            "enabled": True,
            "authenticated_role_ref": authenticated_role_ref or None,
            "signed_identity_packet_ref": signed_identity_packet_ref or None,
            "verification_source": "authenticated_role_ref_or_signed_identity_packet",
        }
    return scene_context


def parse_intent(text: str) -> tuple[str, dict[str, str], str]:
    lowered = text.lower()
    slots = pick_slots(lowered)
    if slots.get("risk_signal") == "member_plaintext":
        return "member_plaintext_request", slots, "L3"
    if slots.get("risk_signal") == "payment":
        return "payment_request", slots, "L3"
    if slots.get("risk_signal") == "identity_claim":
        return "claimed_founder_identity", slots, "L3"

    scores = {intent: sum(1 for word in words if word.lower() in lowered) for intent, words in INTENT_ALIAS_TABLE.items()}
    intent = max(scores, key=scores.get)
    score = scores[intent]
    if score <= 0:
        return "unknown", slots, "L1"
    return intent, slots, "L3" if score > 1 else "L2"


def blank_8d(packet_type: str, step: str, parent_packet_hash: str | None, context: dict[str, Any]) -> dict[str, Any]:
    packet = {
        "packet_type": packet_type,
        "version": "v0.2",
        "step": step,
        "parent_packet_hash": parent_packet_hash,
        "D1_intent": context.get("D1_intent", {}),
        "D2_state": context.get("D2_state", {}),
        "D3_coordinate": context.get("D3_coordinate", {}),
        "D4_evidence": context.get("D4_evidence", {}),
        "D5_execution": context.get("D5_execution", {}),
        "D6_gt": context.get("D6_gt", {}),
        "D7_risk": context.get("D7_risk", {}),
        "D8_envelope": {
            "packet_id": "pkt_" + uuid.uuid4().hex,
            "created_at_unix": now_unix(),
            "ttl_seconds": context.get("ttl_seconds", 300),
            "nonce": uuid.uuid4().hex,
        },
    }
    if "D3_transition_metadata" in context:
        packet["D3_transition_metadata"] = dict(context["D3_transition_metadata"])
    packet_hash = sha(packet)
    packet["D8_envelope"]["packet_hash"] = packet_hash
    packet["D8_envelope"]["seal"] = sha(packet_hash + ":" + packet["D8_envelope"]["nonce"])
    return packet


def reseal(packet: dict[str, Any]) -> None:
    packet["D8_envelope"].pop("packet_hash", None)
    packet["D8_envelope"].pop("seal", None)
    packet_hash = sha(packet)
    packet["D8_envelope"]["packet_hash"] = packet_hash
    packet["D8_envelope"]["seal"] = sha(packet_hash + ":" + packet["D8_envelope"]["nonce"])


def verifier(packet: dict[str, Any]) -> dict[str, Any]:
    intent = packet.get("D1_intent", {}).get("intent_id", "unknown")
    slots = packet.get("D1_intent", {}).get("slots", {})
    confidence = packet.get("D1_intent", {}).get("confidence_level", "L1")
    risk_signal = slots.get("risk_signal", "none")
    scene_context = packet.get("D2_state", {}).get("scene_context", {})
    scene_type = scene_context.get("context_type")

    if risk_signal == "member_plaintext" or intent == "member_plaintext_request":
        policy = RISK_POLICY_TABLE["member_plaintext"]
    elif risk_signal == "payment" or intent == "payment_request":
        policy = RISK_POLICY_TABLE["payment"]
    elif risk_signal == "allergy":
        policy = RISK_POLICY_TABLE["allergy"]
    elif risk_signal == "identity_claim" or intent == "claimed_founder_identity":
        policy = RISK_POLICY_TABLE["identity_claim"]
    elif intent == "identity_context_query":
        policy = RISK_POLICY_TABLE["identity_boundary"]
    elif intent == "member_context_query":
        policy = RISK_POLICY_TABLE["member_context"]
    elif intent == "role_context_query":
        policy = RISK_POLICY_TABLE["role_context"]
    elif scene_type == "CLAIMED_FOUNDER_CONTEXT":
        policy = RISK_POLICY_TABLE["claimed_founder_context"]
    elif confidence == "L1" or intent == "unknown":
        policy = RISK_POLICY_TABLE["low_confidence"]
    elif intent == "draft_order":
        policy = RISK_POLICY_TABLE["draft_order"]
    else:
        policy = RISK_POLICY_TABLE["none"]

    decision = policy["decision"]
    if decision == "CONTINUE" and packet["step"] in {"S6_OUTPUT_PACKET", "S7_FEEDBACK_CANDIDATE_PACKET"}:
        decision = "ALLOW"
    return {"decision": decision, "reasons": list(policy["reasons"])}


@dataclass(frozen=True)
class PacketStep:
    name: str
    input_packet_type: str
    output_packet_type: str
    verifier: Callable[[dict[str, Any]], dict[str, Any]]
    transition: Callable[[dict[str, Any] | None, dict[str, Any]], dict[str, Any]]


def transition_input_event(_: dict[str, Any] | None, ctx: dict[str, Any]) -> dict[str, Any]:
    text = ctx["text"]
    initial_coordinate = {
        "branch": ctx["branch"],
        "actor_role": ctx["actor_role"],
        "channel": ctx["channel"],
    }
    d7_reference = {
        "rule_ref": "rules/input_event_v1",
        "table_ref": "tables/input_event_v1",
        "template_ref": "templates/input_event_v1",
    }
    transition = transition_coordinate(
        previous_coord={},
        event_code="STATE_UPDATE",
        event_id=ctx["d3_event_id"],
        logical_time=ctx["d3_logical_time"],
        rule_ref=d7_reference["rule_ref"],
        context={
            "coordinate_delta": initial_coordinate,
            "d7_reference": d7_reference,
        },
    )
    coordinate = (
        transition["committed"]
        if transition["final_decision"] == "ALLOW"
        else transition["previous"]
    )
    base = {
        "ttl_seconds": ctx["ttl_seconds"],
        "D1_intent": {"intent_id": "input_event", "slots": {}, "confidence_level": "L0"},
        "D2_state": {"runtime_state": "input_received", "scene_context": ctx["scene_context"]},
        "D3_coordinate": coordinate,
        "D3_transition_metadata": {
            "transition_hash": transition["transition_hash"],
            "event_id": transition["event_id"],
            "logical_time": transition["logical_time"],
            "committed": transition["committed"],
            "commit_applied": transition["commit_applied"],
            "final_decision": transition["final_decision"],
        },
        "D4_evidence": {"input_text_hash": sha(text), "input_length": len(text)},
        "D5_execution": {"candidate_only": True, "side_effects_allowed": False},
        "D6_gt": d7_reference,
        "D7_risk": {"risk_code": "not_evaluated", "decision": "CONTINUE", "reasons": []},
    }
    return blank_8d("input_event_packet", "S0_INPUT_EVENT", None, base)


def transition_intent(prev: dict[str, Any] | None, ctx: dict[str, Any]) -> dict[str, Any]:
    intent, slots, confidence = parse_intent(ctx["text"])
    base = dict(prev or {})
    identity_claim = {}
    if slots.get("claimed_identity_packet") == "CLAIMED_IDENTITY_PACKET":
        identity_claim = {
            "packet_type": "CLAIMED_IDENTITY_PACKET",
            "claim_hash": sha(ctx["text"]),
            "claim_source": "user_self_asserted_text",
            "accepted_as_truth": False,
            "verification_required": True,
        }
    context = {
        "ttl_seconds": ctx["ttl_seconds"],
        "D1_intent": {"intent_id": intent, "slots": slots, "confidence_level": confidence},
        "D2_state": {"runtime_state": "intent_parsed", "scene_context": ctx["scene_context"]},
        "D3_coordinate": (prev or {})["D3_coordinate"],
        "D4_evidence": {
            "input_text_hash": sha(ctx["text"]),
            "parser": "model_free_alias_slot_parser_v1",
            **({"claimed_identity_packet": identity_claim} if identity_claim else {}),
        },
        "D5_execution": {"candidate_only": True, "side_effects_allowed": False},
        "D6_gt": {"rule_ref": "rules/intent_alias_v1", "table_ref": "intent_alias_table", "template_ref": "none"},
        "D7_risk": base.get("D7_risk", {}),
    }
    return blank_8d("intent_packet", "S1_INTENT_PACKET", prev["D8_envelope"]["packet_hash"], context)


def transition_route(prev: dict[str, Any] | None, ctx: dict[str, Any]) -> dict[str, Any]:
    intent = prev["D1_intent"]["intent_id"]
    route = ROUTE_TABLE.get(intent, ROUTE_TABLE["unknown"])
    context = {
        "ttl_seconds": ctx["ttl_seconds"],
        "D1_intent": prev["D1_intent"],
        "D2_state": {"runtime_state": "route_selected", "route": route["route"], "scene_context": ctx["scene_context"]},
        "D3_coordinate": prev["D3_coordinate"],
        "D4_evidence": {**prev["D4_evidence"], "route_table_hash": sha(ROUTE_TABLE)},
        "D5_execution": prev["D5_execution"],
        "D6_gt": {"rule_ref": route["rule_ref"], "table_ref": route["table_ref"], "template_ref": route["template_ref"]},
        "D7_risk": prev["D7_risk"],
    }
    return blank_8d("route_packet", "S2_ROUTE_PACKET", prev["D8_envelope"]["packet_hash"], context)


def transition_state(prev: dict[str, Any] | None, ctx: dict[str, Any]) -> dict[str, Any]:
    intent = prev["D1_intent"]["intent_id"]
    profile_state = {
        "profile_ref": "profile_ref:masked_or_none",
        "role_ref": "role_ref:verified_context_required",
        "identity_ref": "identity_ref:not_asserted_as_truth",
        "plaintext_available": False,
        "db_read_performed": False,
    }
    context = {
        "ttl_seconds": ctx["ttl_seconds"],
        "D1_intent": prev["D1_intent"],
        "D2_state": {
            **prev["D2_state"],
            "scene_context": ctx["scene_context"],
            "state_refs": {
                "menu_ref": "branch.menu.current",
                "member_ref": "masked_or_none",
                "inventory_ref": "branch.inventory.summary",
                **({"identity_context_ref": "identity.context.masked_ref_only"} if intent in {"identity_context_query", "member_context_query", "role_context_query", "claimed_founder_identity"} else {}),
            },
            **({"profile_state": profile_state} if intent in {"identity_context_query", "member_context_query", "role_context_query", "claimed_founder_identity"} else {}),
        },
        "D3_coordinate": prev["D3_coordinate"],
        "D4_evidence": {**prev["D4_evidence"], "state_ref_mode": "refs_only_no_plaintext"},
        "D5_execution": prev["D5_execution"],
        "D6_gt": prev["D6_gt"],
        "D7_risk": prev["D7_risk"],
    }
    return blank_8d("state_packet", "S3_STATE_PACKET", prev["D8_envelope"]["packet_hash"], context)


def transition_risk(prev: dict[str, Any] | None, ctx: dict[str, Any]) -> dict[str, Any]:
    interim = verifier(prev)
    risk_code = prev["D1_intent"].get("slots", {}).get("risk_signal", "none")
    if prev["D1_intent"]["intent_id"] == "unknown":
        risk_code = "low_confidence"
    if prev["D1_intent"]["intent_id"] == "identity_context_query":
        risk_code = "identity_boundary"
    if prev["D1_intent"]["intent_id"] == "member_context_query":
        risk_code = "member_context"
    if prev["D1_intent"]["intent_id"] == "role_context_query":
        risk_code = "role_context"
    if ctx["scene_context"]["context_type"] == "CLAIMED_FOUNDER_CONTEXT":
        risk_code = "claimed_founder_context"
    context = {
        "ttl_seconds": ctx["ttl_seconds"],
        "D1_intent": prev["D1_intent"],
        "D2_state": {**prev["D2_state"], "scene_context": ctx["scene_context"]},
        "D3_coordinate": prev["D3_coordinate"],
        "D4_evidence": {**prev["D4_evidence"], "risk_policy_table_hash": sha(RISK_POLICY_TABLE)},
        "D5_execution": prev["D5_execution"],
        "D6_gt": prev["D6_gt"],
        "D7_risk": {"risk_code": risk_code, "decision": interim["decision"], "reasons": interim["reasons"]},
    }
    return blank_8d("risk_packet", "S4_RISK_PACKET", prev["D8_envelope"]["packet_hash"], context)


def transition_capability(prev: dict[str, Any] | None, ctx: dict[str, Any]) -> dict[str, Any]:
    intent = prev["D1_intent"]["intent_id"]
    caps = CAPABILITY_TABLE.get(intent, CAPABILITY_TABLE["unknown"])
    scene_forbidden = ctx["scene_context"].get("forbidden_scope", [])
    forbidden_actions = list(dict.fromkeys(caps["forbidden_actions"] + scene_forbidden))
    allowed_actions = list(dict.fromkeys(caps["allowed_actions"] + ctx["scene_context"].get("allowed_scope", [])))
    context = {
        "ttl_seconds": ctx["ttl_seconds"],
        "D1_intent": prev["D1_intent"],
        "D2_state": {**prev["D2_state"], "scene_context": ctx["scene_context"]},
        "D3_coordinate": prev["D3_coordinate"],
        "D4_evidence": {**prev["D4_evidence"], "capability_table_hash": sha(CAPABILITY_TABLE)},
        "D5_execution": {
            "allowed_actions": allowed_actions,
            "forbidden_actions": forbidden_actions,
            "candidate_only": True,
            "side_effects_allowed": False,
        },
        "D6_gt": prev["D6_gt"],
        "D7_risk": prev["D7_risk"],
    }
    return blank_8d("capability_packet", "S5_CAPABILITY_PACKET", prev["D8_envelope"]["packet_hash"], context)


def build_semantic_ir(packet: dict[str, Any]) -> dict[str, Any]:
    slots = packet["D1_intent"].get("slots", {})
    taste = slots.get("taste_preference", "default")
    condition = slots.get("condition", "default")
    pairing = PAIRING_TABLE.get((taste, condition)) or PAIRING_TABLE.get((taste, "default")) or PAIRING_TABLE[("default", "default")]
    semantic_ir = {
        "intent_id": packet["D1_intent"]["intent_id"],
        "slots": slots,
        "decision": packet["D7_risk"].get("decision", "CONTINUE"),
        "recommendation": pairing,
        "route": packet["D2_state"].get("route", "unknown"),
        "scene_context": packet["D2_state"].get("scene_context", {}),
    }
    if semantic_ir["intent_id"] in {"identity_context_query", "member_context_query", "role_context_query", "claimed_founder_identity"}:
        semantic_ir["identity_profile"] = {
            "profile_ref_mode": "masked_refs_only",
            "claimed_identity_packet": packet["D4_evidence"].get("claimed_identity_packet"),
            "accepted_as_truth": False,
            "member_plaintext_read": False,
            "db_read_performed": False,
            "requires_verified_context": True,
        }
    return semantic_ir


def render_language(semantic_ir: dict[str, Any], final_decision: str, reasons: list[str]) -> str:
    intent = semantic_ir["intent_id"]
    scene_type = (semantic_ir.get("scene_context") or {}).get("context_type")
    rec = semantic_ir["recommendation"]
    reason = "、".join(reasons)
    if intent == "recommend_order":
        key = "recommend_allow" if final_decision == "ALLOW" else "recommend_hold"
        return TEMPLATE_TABLE[key].format(**rec, reason=reason)
    if intent == "payment_request":
        return TEMPLATE_TABLE["payment_hold"]
    if intent in {"member_lookup_masked", "member_plaintext_request"}:
        return TEMPLATE_TABLE["member_block"]
    if intent == "identity_context_query":
        return TEMPLATE_TABLE["identity_context_hold"]
    if intent == "member_context_query":
        return TEMPLATE_TABLE["member_context_hold"]
    if intent == "role_context_query":
        return TEMPLATE_TABLE["role_context_hold"]
    if intent == "claimed_founder_identity":
        return TEMPLATE_TABLE["claimed_founder_hold"]
    if intent == "property_service_request":
        return TEMPLATE_TABLE["property_service_hold"]
    if intent == "association_activity_query":
        return TEMPLATE_TABLE["association_activity_hold"]
    if intent == "architecture_discussion":
        return TEMPLATE_TABLE["architecture_discussion"]
    if intent == "general_chat":
        return TEMPLATE_TABLE["general_chat"]
    if intent == "capability_intro":
        return TEMPLATE_TABLE["capability_intro"]
    if scene_type == "CLAIMED_FOUNDER_CONTEXT":
        return TEMPLATE_TABLE["claimed_founder_hold"]
    if intent == "draft_order":
        return TEMPLATE_TABLE["draft_hold"]
    if intent == "ask_menu":
        return TEMPLATE_TABLE["menu_allow"]
    return TEMPLATE_TABLE["clarify_hold"]


def transition_output(prev: dict[str, Any] | None, ctx: dict[str, Any]) -> dict[str, Any]:
    semantic_ir = build_semantic_ir(prev)
    context = {
        "ttl_seconds": ctx["ttl_seconds"],
        "D1_intent": prev["D1_intent"],
        "D2_state": {**prev["D2_state"], "scene_context": ctx["scene_context"], "semantic_ir": semantic_ir},
        "D3_coordinate": prev["D3_coordinate"],
        "D4_evidence": {**prev["D4_evidence"], "template_table_hash": sha(TEMPLATE_TABLE)},
        "D5_execution": prev["D5_execution"],
        "D6_gt": prev["D6_gt"],
        "D7_risk": prev["D7_risk"],
    }
    return blank_8d("output_packet", "S6_OUTPUT_PACKET", prev["D8_envelope"]["packet_hash"], context)


def transition_feedback(prev: dict[str, Any] | None, ctx: dict[str, Any]) -> dict[str, Any]:
    model_lane = {"model_lane_available": False, "candidate_packet": None, "authority": "verifier_only"}
    context = {
        "ttl_seconds": ctx["ttl_seconds"],
        "D1_intent": prev["D1_intent"],
        "D2_state": {
            **prev["D2_state"],
            "scene_context": ctx["scene_context"],
            "feedback_candidate": {
                "capture_mode": "hash_and_refs_only",
                "may_update_tables_after_review": True,
                "model_lane_stub": model_lane,
            },
        },
        "D3_coordinate": prev["D3_coordinate"],
        "D4_evidence": {**prev["D4_evidence"], "feedback_ref": "runtime.feedback_candidate.local"},
        "D5_execution": prev["D5_execution"],
        "D6_gt": prev["D6_gt"],
        "D7_risk": prev["D7_risk"],
    }
    return blank_8d("feedback_candidate_packet", "S7_FEEDBACK_CANDIDATE_PACKET", prev["D8_envelope"]["packet_hash"], context)


STEPS = [
    PacketStep("S0_INPUT_EVENT", "none", "input_event_packet", verifier, transition_input_event),
    PacketStep("S1_INTENT_PACKET", "input_event_packet", "intent_packet", verifier, transition_intent),
    PacketStep("S2_ROUTE_PACKET", "intent_packet", "route_packet", verifier, transition_route),
    PacketStep("S3_STATE_PACKET", "route_packet", "state_packet", verifier, transition_state),
    PacketStep("S4_RISK_PACKET", "state_packet", "risk_packet", verifier, transition_risk),
    PacketStep("S5_CAPABILITY_PACKET", "risk_packet", "capability_packet", verifier, transition_capability),
    PacketStep("S6_OUTPUT_PACKET", "capability_packet", "output_packet", verifier, transition_output),
    PacketStep("S7_FEEDBACK_CANDIDATE_PACKET", "output_packet", "feedback_candidate_packet", verifier, transition_feedback),
]


def normalize_canonical_verifier_result(canonical_verifier_result: dict[str, Any] | None) -> dict[str, Any]:
    if not canonical_verifier_result:
        return {
            "decision": "HOLD",
            "reasons": ["canonical 8D verifier result required"],
            "authority": "canonical_8d_verifier",
            "runtime_authority": False,
        }
    decision = canonical_verifier_result.get("decision") or canonical_verifier_result.get("collapse_result")
    if decision not in {"ALLOW", "HOLD", "BLOCK"}:
        return {
            "decision": "HOLD",
            "reasons": ["canonical 8D verifier result invalid or missing ALLOW/HOLD/BLOCK"],
            "authority": "canonical_8d_verifier",
            "runtime_authority": False,
            "canonical_verifier_result": canonical_verifier_result,
        }
    reasons = canonical_verifier_result.get("reasons")
    if not isinstance(reasons, list) or not reasons:
        reasons = [f"canonical 8D verifier decision: {decision}"]
    return {
        "decision": decision,
        "reasons": reasons,
        "authority": "canonical_8d_verifier",
        "runtime_authority": False,
        "canonical_verifier_result": canonical_verifier_result,
    }


def final_verifier(
    verifier_results: list[dict[str, Any]],
    canonical_verifier_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reasons: list[str] = []
    decisions = [result["decision"] for result in verifier_results]
    for result in verifier_results:
        for reason in result["reasons"]:
            if reason not in reasons:
                reasons.append(reason)
    canonical = normalize_canonical_verifier_result(canonical_verifier_result)
    return {
        **canonical,
        "runtime_authority": False,
        "runtime_advisory": {
            "decisions": decisions,
            "reasons": reasons or ["runtime advisory verified"],
        },
    }


def _load_active_voice_output_hook() -> Any:
    pointer = json.loads(
        ACTIVE_XIAOJ_VOICE_OUTPUT_PROJECTION_POINTER.read_text(
            encoding="utf-8"
        )
    )
    pointer_without_hash = {
        key: value for key, value in pointer.items() if key != "pointer_sha256"
    }
    hook = pointer.get("formal_output_hook")
    if (
        pointer.get("active") is not True
        or sha(pointer_without_hash) != pointer.get("pointer_sha256")
        or not isinstance(hook, dict)
    ):
        raise RuntimeError("HOLD_ACTIVE_VOICE_OUTPUT_POINTER_INVALID")
    hook_path = Path(str(hook.get("path") or ""))
    if (
        not hook_path.is_file()
        or hashlib.sha256(hook_path.read_bytes()).hexdigest()
        != hook.get("sha256")
    ):
        raise RuntimeError("HOLD_ACTIVE_VOICE_OUTPUT_HOOK_HASH_MISMATCH")
    spec = importlib.util.spec_from_file_location(
        "xiaoj_active_verified_voice_output_hook",
        hook_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("HOLD_ACTIVE_VOICE_OUTPUT_HOOK_LOAD_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def voice_output_hook_health() -> dict[str, Any]:
    """Read the active pointer on demand so version switches need no restart."""

    try:
        hook = _load_active_voice_output_hook()
        return hook.health(require_active=True)
    except Exception as exc:
        return {
            "state": "HOLD_FORMAL_VOICE_OUTPUT_HEALTH",
            "failure_class": type(exc).__name__,
            "active": False,
            "restart_required": False,
        }


def dispatch_verified_final_answer_voice(
    *,
    answer_text: str,
    final_verifier: dict[str, Any],
    output_mode: str,
    disclosure_class: str,
    logical_time: str,
) -> dict[str, Any]:
    """Keep voice effects optional and never block the verified text result."""

    if output_mode != "VOICE":
        return {
            "state": "VOICE_OUTPUT_NOT_REQUESTED",
            "output_mode": output_mode,
            "playback_started": False,
            "text_response_blocked": False,
        }
    try:
        hook = _load_active_voice_output_hook()
        return hook.dispatch_verified_voice_output(
            answer_text=answer_text,
            final_verifier=final_verifier,
            output_mode=output_mode,
            disclosure_class=disclosure_class,
            logical_time=logical_time,
        )
    except Exception as exc:
        return {
            "state": "HOLD_FORMAL_VOICE_OUTPUT_NON_BLOCKING_FAILURE",
            "failure_class": type(exc).__name__,
            "playback_started": False,
            "playback_finished": False,
            "automatic_retry": False,
            "text_response_blocked": False,
        }


def run(
    text: str,
    branch: str = "cafe_main",
    actor_role: str = "counter_ai",
    channel: str = "counter_voice",
    dev_role_ref: str = "",
    dev_identity_switch: bool = False,
    authenticated_role_ref: str = "",
    signed_identity_packet_ref: str = "",
    canonical_verifier_result: dict[str, Any] | None = None,
    event_id: str = "",
    logical_time: Any = None,
    output_mode: str = "TEXT",
    disclosure_class: str = "PUBLIC",
) -> dict[str, Any]:
    event_basis = {
        "text": text,
        "branch": branch,
        "actor_role": actor_role,
        "channel": channel,
    }
    resolved_event_id = event_id or "evt_" + sha(event_basis)[:32]
    resolved_logical_time = (
        logical_time
        if logical_time is not None and logical_time != ""
        else "logical:" + sha({"event_id": resolved_event_id, "step": "S0_INPUT_EVENT"})[:32]
    )
    ctx = {
        "text": text,
        "branch": branch,
        "actor_role": actor_role,
        "channel": channel,
        "ttl_seconds": 300,
        "dev_role_ref": dev_role_ref,
        "dev_identity_switch": dev_identity_switch,
        "authenticated_role_ref": authenticated_role_ref,
        "signed_identity_packet_ref": signed_identity_packet_ref,
        "d3_event_id": resolved_event_id,
        "d3_logical_time": resolved_logical_time,
        "scene_context": detect_scene_context(
            text,
            dev_role_ref=dev_role_ref,
            dev_identity_switch=dev_identity_switch,
            authenticated_role_ref=authenticated_role_ref,
            signed_identity_packet_ref=signed_identity_packet_ref,
        ),
    }
    packet_chain = []
    verifier_results = []
    previous = None
    for step in STEPS:
        packet = step.transition(previous, ctx)
        result = step.verifier(packet)
        packet["D7_risk"] = {
            **packet.get("D7_risk", {}),
            "decision": result["decision"],
            "reasons": result["reasons"],
        }
        reseal(packet)
        packet_chain.append(packet)
        verifier_results.append({"step": step.name, **result})
        previous = packet

    final = final_verifier(verifier_results, canonical_verifier_result=canonical_verifier_result)
    semantic_ir = packet_chain[-2]["D2_state"]["semantic_ir"]
    zh_tw = render_language(semantic_ir, final["decision"], final["reasons"])
    result = {
        "STATE": "PASS_W7TP_PACKET_INFERENCE_RUNTIME",
        "RUN_MODE": "MODEL_FREE_PACKET_BY_PACKET_INFERENCE",
        "SAFETY_FLAGS": SAFETY_FLAGS,
        "INPUT_TEXT_HASH": sha(text),
        "D3_TRANSITION_METADATA": packet_chain[0]["D3_transition_metadata"],
        "PACKET_CHAIN": packet_chain,
        "STEP_VERIFIERS": verifier_results,
        "FINAL_VERIFIER": final,
        "LANGUAGE_RECONSTRUCTION": {
            "semantic_ir": semantic_ir,
            "zh_TW": zh_tw,
        },
    }
    result["VOICE_OUTPUT"] = dispatch_verified_final_answer_voice(
        answer_text=zh_tw,
        final_verifier=final,
        output_mode=output_mode,
        disclosure_class=disclosure_class,
        logical_time=str(resolved_logical_time),
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    parser.add_argument("--out", default="")
    parser.add_argument("--branch", default="cafe_main")
    parser.add_argument("--actor-role", default="counter_ai")
    parser.add_argument("--channel", default="counter_voice")
    parser.add_argument("--dev-role-ref", default="")
    parser.add_argument("--dev-identity-switch", action="store_true")
    parser.add_argument("--authenticated-role-ref", default="")
    parser.add_argument("--signed-identity-packet-ref", default="")
    parser.add_argument("--canonical-verifier-result-json", default="")
    parser.add_argument("--output-mode", choices=("TEXT", "VOICE"), default="TEXT")
    parser.add_argument(
        "--disclosure-class",
        choices=("PUBLIC", "INTERNAL_AUTHORIZED", "FOUNDER_AUTHORIZED"),
        default="PUBLIC",
    )
    args = parser.parse_args()

    canonical_verifier_result = None
    if args.canonical_verifier_result_json:
        canonical_verifier_result = json.loads(Path(args.canonical_verifier_result_json).read_text(encoding="utf-8"))

    data = run(
        args.text,
        branch=args.branch,
        actor_role=args.actor_role,
        channel=args.channel,
        dev_role_ref=args.dev_role_ref,
        dev_identity_switch=args.dev_identity_switch,
        authenticated_role_ref=args.authenticated_role_ref,
        signed_identity_packet_ref=args.signed_identity_packet_ref,
        canonical_verifier_result=canonical_verifier_result,
        output_mode=args.output_mode,
        disclosure_class=args.disclosure_class,
    )
    rendered = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
    print(rendered)
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
