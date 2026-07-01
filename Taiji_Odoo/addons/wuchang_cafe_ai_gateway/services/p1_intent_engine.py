"""Pure XiaoJ P1 local intent engine.

This module has no Odoo imports and no external side effects. It turns text,
order lines, payment params, and receipt refs into candidate payloads that the
Odoo controller can expose after module release.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SAFETY_FLAGS = {
    "SECRET_READ": False,
    "MEMBER_PLAINTEXT_READ": False,
    "RAW_AUDIO_SAVED": False,
    "ODOO_DB_WRITE": False,
    "POS_ORDER_CREATED": False,
    "PAYMENT_CAPTURE": False,
    "SERVICE_RESTART": False,
    "DEPLOY": False,
    "EXTERNAL_API_CALL": False,
}


ROOT = Path(__file__).resolve().parents[4]
INTENT_SUBFIELDS_ROOT = ROOT / "runtime" / "intent_subfields"


REALITY_LAYER_POLICY = {
    "schema": "W7TP_TOTAL_FIELD_REALITY_LAYER_POLICY_V1",
    "principle": "LLM imagination is conditionally allowed only as labeled candidate state.",
    "layers": ["REAL_VERIFIED", "IMAGINED_CANDIDATE", "EXECUTABLE_AUTHORIZED"],
    "llm_hallucination_allowed": "conditional",
    "allowed_layer": "IMAGINED_CANDIDATE",
    "required_before_execution": [
        "total_field_subfield_query",
        "authority_packet",
        "local_reconstruction",
        "local_discrete_state_verifier",
        "evidence_seal",
        "human_release_for_merchant_impacting_actions",
    ],
    "forbidden": [
        "llm_candidate_claims_real_world_fact_without_local_evidence",
        "llm_candidate_sets_execution_allowed",
        "imagined_candidate_direct_pos_payment_membership_lineworks_action",
        "cloud_model_overrides_total_field_reality_state",
    ],
}


MENU_SOURCE_LOCK = {
    "state": "HOLD_REAL_MENU_SOURCE_LOCK",
    "current_menu_authority": False,
    "live_quickclick_export_required": True,
    "can_create_pos_order_from_current_menu": False,
}


VOICE_POS_GRAMMAR_ORDER = ["size", "temperature", "sweetness", "item"]
VOICE_SIZE_TOKENS = {
    "大": "large",
    "大杯": "large",
    "中": "medium",
    "中杯": "medium",
    "小": "small",
    "小杯": "small",
}
VOICE_TEMPERATURE_TOKENS = {
    "冰": "ice",
    "冰的": "ice",
    "熱": "hot",
    "熱的": "hot",
    "溫": "warm",
    "溫的": "warm",
}
VOICE_SWEETNESS_TOKENS = {
    "無糖": "no_sugar",
    "微糖": "light_sugar",
    "少糖": "less_sugar",
    "半糖": "half_sugar",
    "正常甜": "regular_sugar",
    "全糖": "full_sugar",
}


SUPPORTED_INTENTS = {
    "menu_lookup",
    "order_candidate",
    "pos_order_create",
    "payment_candidate",
    "receipt_candidate",
    "translate_assist",
    "manager_price_change",
    "return_candidate",
    "category_move",
    "live_notice",
    "cash_advance_ref",
    "member_register",
    "loyalty_return",
    "staff_voice_pos_operation",
    "sovereign_member_personalization",
    "merchant_social_candidate",
    "property_community_candidate",
    "humanoid_service_candidate",
    "lineworks_notify_candidate",
    "merchant_capability_map",
}


MERCHANT_INVENTION_CAPABILITY_MAP = {
    "state": "P1_MERCHANT_INVENTION_CAPABILITY_MAP_READY",
    "core_rule": "AI output is candidate-only; merchant-impacting execution requires local authority.",
    "execution_chain": [
        "merchant_input",
        "ai_candidate",
        "authority_packet",
        "local_reconstruction",
        "local_discrete_authority_verifier",
        "execution_gate",
        "evidence_seal_ui_status",
    ],
    "capabilities": [
        {
            "id": "total_field_subfield_query",
            "surface": ["ordering", "membership", "social", "property", "community", "POS", "humanoid"],
            "cloud_role": "no_generation_before_query",
            "local_authority": "query_runtime_intent_subfields_and_embed_query_hash",
        },
        {
            "id": "candidate_authority_isolation",
            "surface": ["ordering", "membership", "social", "property", "community", "POS"],
            "cloud_role": "candidate_only",
            "local_authority": "required",
        },
        {
            "id": "generative_transmission",
            "surface": ["cloud_humanoid", "cloud_ordering", "member_personalization"],
            "cloud_role": "minimized_candidate_context",
            "local_authority": "reconstruct_from_indexes_deltas_hashes_state_codes_route_keys",
        },
        {
            "id": "llm_reality_layer_governance",
            "surface": ["LLM", "Gemini", "humanoid", "social", "membership", "ordering", "LINE_WORKS"],
            "cloud_role": "imagined_candidate_allowed_when_labeled",
            "local_authority": "distinguish_real_verified_imagined_candidate_executable_authorized",
        },
        {
            "id": "sovereign_ai_membership",
            "surface": ["member_login", "loyalty", "discount", "preference", "coupon"],
            "cloud_role": "suggest_personalization_candidate",
            "local_authority": "member_identity_consent_benefit_discount_verifier",
        },
        {
            "id": "cloud_humanoid_subscription_layer",
            "surface": ["avatar", "voice", "vision", "customer_display", "staff_display"],
            "cloud_role": "interaction_shell",
            "local_authority": "authority_packet_required_for_execution",
        },
        {
            "id": "cafe_av_ordering_waiter",
            "surface": ["audio_ordering", "video_ordering", "table_side_ordering", "customer_display"],
            "cloud_role": "order_intent_candidate",
            "local_authority": "menu_price_option_table_member_pos_verifier",
        },
        {
            "id": "odoo_pos_execution_gate",
            "surface": ["Odoo", "POS", "table_QR", "payment_policy", "order_write"],
            "cloud_role": "draft_order_only",
            "local_authority": "formal_order_payment_discount_refund_inventory_verifier",
        },
        {
            "id": "merchant_social_governance",
            "surface": ["LINE", "LINE_WORKS", "social_post", "campaign", "coupon", "member_message"],
            "cloud_role": "draft_content_or_campaign_candidate",
            "local_authority": "audience_offer_channel_consent_risk_verifier",
        },
        {
            "id": "lineworks_member_service_notification",
            "surface": ["LINE_WORKS", "member_service", "staff_notice", "community_notice"],
            "cloud_role": "draft_notification_candidate",
            "local_authority": "lineworks_bot_config_consent_audience_message_policy_verifier",
        },
        {
            "id": "property_community_governance",
            "surface": ["visitor", "parcel", "facility", "repair", "fee_notice", "announcement"],
            "cloud_role": "service_workflow_candidate",
            "local_authority": "resident_unit_role_time_facility_evidence_verifier",
        },
        {
            "id": "dead_letter_failure_governance",
            "surface": ["ordering", "membership", "POS", "social", "property", "edge"],
            "cloud_role": "no_failure_override",
            "local_authority": "hold_quarantine_queue_dead_letter",
        },
        {
            "id": "evidence_seal_ui_status",
            "surface": ["customer_display", "staff_display", "admin", "audit", "demo"],
            "cloud_role": "status_explanation_candidate",
            "local_authority": "packet_hash_decision_failure_reason_verifier_state_seal",
        },
    ],
    "reality_layer_policy": REALITY_LAYER_POLICY,
    "cloud_humanoid_subscription_boundary": {
        "allowed": [
            "avatar_rendering",
            "speech_to_text",
            "text_to_speech",
            "natural_language_response_candidate",
            "menu_explanation_candidate",
            "order_intent_candidate",
        ],
        "forbidden": [
            "formal_pos_write",
            "payment_capture",
            "member_identity_authority",
            "discount_authority",
            "social_publication_authority",
            "property_access_authority",
            "secret_lookup_authority",
        ],
        "required_labels": {
            "candidate_only": True,
            "cloud_authority": False,
            "local_authority": "discrete_state_core",
        },
    },
}


INTENT_AUTHORITY_SURFACES = {
    "menu_lookup": "menu_read",
    "order_candidate": "cafe_order",
    "pos_order_create": "pos_order_write",
    "payment_candidate": "payment",
    "receipt_candidate": "receipt",
    "translate_assist": "staff_assist",
    "manager_price_change": "price_policy",
    "return_candidate": "refund_or_return",
    "category_move": "catalog_policy",
    "live_notice": "merchant_notice",
    "cash_advance_ref": "cash_policy",
    "member_register": "membership",
    "loyalty_return": "membership",
    "staff_voice_pos_operation": "voice_pos",
    "sovereign_member_personalization": "membership",
    "merchant_social_candidate": "merchant_social",
    "property_community_candidate": "property_community",
    "humanoid_service_candidate": "humanoid_interaction",
    "lineworks_notify_candidate": "lineworks_notification",
    "merchant_capability_map": "capability_read",
}


INTENT_LOCAL_VERIFIERS = {
    "menu_lookup": ["menu_source_lock_verifier"],
    "order_candidate": ["menu_price_option_table_member_pos_verifier"],
    "pos_order_create": ["formal_pos_execution_gate"],
    "payment_candidate": ["payment_policy_gate"],
    "receipt_candidate": ["formal_order_receipt_gate"],
    "translate_assist": ["staff_assist_policy_gate"],
    "manager_price_change": ["manager_price_authority_gate"],
    "return_candidate": ["refund_return_authority_gate"],
    "category_move": ["catalog_policy_gate"],
    "live_notice": ["merchant_notice_publication_gate"],
    "cash_advance_ref": ["cash_policy_evidence_gate"],
    "member_register": ["sovereign_member_registration_gate"],
    "loyalty_return": ["sovereign_member_benefit_gate"],
    "staff_voice_pos_operation": ["voice_pos_grammar_gate", "menu_price_option_table_member_pos_verifier"],
    "sovereign_member_personalization": ["sovereign_member_identity_consent_benefit_verifier"],
    "merchant_social_candidate": ["audience_offer_channel_consent_risk_verifier"],
    "property_community_candidate": ["resident_unit_role_time_facility_evidence_verifier"],
    "humanoid_service_candidate": ["cloud_humanoid_subscription_boundary_gate", "local_authority_packet_gate"],
    "lineworks_notify_candidate": ["lineworks_bot_config_gate", "audience_consent_message_policy_gate"],
    "merchant_capability_map": ["read_only_capability_gate"],
}


MERCHANT_IMPACTING_INTENTS = {
    "order_candidate",
    "pos_order_create",
    "payment_candidate",
    "receipt_candidate",
    "manager_price_change",
    "return_candidate",
    "category_move",
    "live_notice",
    "cash_advance_ref",
    "member_register",
    "loyalty_return",
    "staff_voice_pos_operation",
    "sovereign_member_personalization",
    "merchant_social_candidate",
    "property_community_candidate",
    "humanoid_service_candidate",
    "lineworks_notify_candidate",
}


READ_ONLY_LOCAL_EXECUTE_INTENTS = {
    "menu_lookup",
    "translate_assist",
    "merchant_capability_map",
}


FORMAL_RELEASE_GATES = {
    "member_registration": {
        "title": "正式會員註冊",
        "required_refs": [
            "authenticated_staff_ref",
            "member_release_packet_ref",
            "auth_provider_config_ref",
            "consent_policy_ref",
            "privacy_policy_ref",
            "member_schema_ref",
            "total_field_release_ref",
        ],
        "forbidden_side_effects_in_p1": [
            "member_plaintext_cloud_upload",
            "secret_read",
            "oauth_token_echo",
        ],
    },
    "pos_order": {
        "title": "正式 POS 下單",
        "required_refs": [
            "authenticated_staff_ref",
            "pos_release_packet_ref",
            "validated_packet_hash",
            "menu_authority_ref",
            "odoo_pos_session_ref",
            "odoo_recomputed_total_ref",
            "fresh_human_confirmation_ref",
            "total_field_release_ref",
        ],
        "forbidden_side_effects_in_p1": [
            "cloud_direct_pos_write",
            "unverified_discount",
            "silent_order_creation",
        ],
    },
    "payment": {
        "title": "正式付款",
        "required_refs": [
            "authenticated_staff_ref",
            "payment_release_packet_ref",
            "payment_provider_config_ref",
            "payment_policy_ref",
            "payable_amount_ref",
            "cashier_confirmation_ref",
            "separate_payment_gate_ref",
            "total_field_release_ref",
        ],
        "forbidden_side_effects_in_p1": [
            "cloud_payment_capture",
            "card_data_to_ai",
            "silent_payment_capture",
        ],
    },
    "lineworks_send": {
        "title": "正式 LINE WORKS 通知發送",
        "required_refs": [
            "authenticated_staff_ref",
            "lineworks_release_packet_ref",
            "lineworks_app_config_ref",
            "lineworks_bot_ref",
            "lineworks_target_user_ref",
            "message_policy_ref",
            "consent_policy_ref",
            "total_field_release_ref",
        ],
        "forbidden_side_effects_in_p1": [
            "cloud_direct_lineworks_send",
            "token_echo",
            "member_plaintext_upload",
            "unreviewed_broadcast",
        ],
    },
}

RELEASE_REF_VERIFIER_ALLOWLIST = {
    "total_field_release_registry",
    "total_field_manual_release_packet",
    "d8_release_gate",
}


INTENT_RULES = [
    ("staff_voice_pos_operation", ("語音pos", "voice pos", "店員語音", "nhan vien noi", "pos bang giong noi")),
    ("humanoid_service_candidate", ("人形", "avatar", "humanoid", "服務生", "影音", "voice waiter")),
    ("sovereign_member_personalization", ("主權會員", "會員偏好", "會員優惠", "member preference", "loyalty profile")),
    ("merchant_social_candidate", ("社群", "貼文", "campaign", "coupon", "line message", "social")),
    ("lineworks_notify_candidate", ("line works", "lineworks", "line works通知", "line works 通知", "works 通知", "會員通知", "志工通知")),
    ("property_community_candidate", ("物業", "社區", "住戶", "訪客", "facility", "parcel", "repair")),
    ("member_register", ("line", "google", "註冊", "會員", "login", "dang ky", "thanh vien")),
    ("payment_candidate", ("付款", "pay", "現金", "cash", "thanh toan", "tien mat")),
    ("return_candidate", ("退", "refund", "return", "hoan")),
    ("manager_price_change", ("改價", "price", "gia")),
    ("category_move", ("分類", "category", "移到", "chuyen nhom")),
    ("translate_assist", ("越文", "英文", "translate", "vietnamese", "tieng viet", "english")),
    ("live_notice", ("提醒", "訊息", "notice", "message", "nhac")),
    ("cash_advance_ref", ("預支", "廠商", "advance", "vendor", "tam ung")),
    ("loyalty_return", ("回訪", "集點", "loyalty", "return visit", "khach quay lai")),
    ("order_candidate", ("下單", "order", "交易", "買", "點", "goi mon", "mua")),
]


@dataclass(frozen=True)
class OrderLine:
    product_ref: str
    name: str
    quantity: float
    price: float

    @property
    def subtotal(self) -> float:
        return self.quantity * self.price


def normalize_text(text: Any) -> str:
    return str(text or "").strip().lower()


def compact_voice_text(text: Any) -> str:
    return "".join(str(text or "").strip().split()).lower()


def _consume_token(text: str, tokens: dict[str, str]) -> tuple[str | None, str | None, str]:
    for token in sorted(tokens, key=len, reverse=True):
        if text.startswith(token.lower()):
            return token, tokens[token], text[len(token):]
    return None, None, text


def _extract_token_anywhere(text: str, tokens: dict[str, str]) -> tuple[str | None, str | None, str]:
    best: tuple[int, str, str] | None = None
    for token, value in tokens.items():
        index = text.find(token.lower())
        if index < 0:
            continue
        if best is None or index < best[0] or (index == best[0] and len(token) > len(best[1])):
            best = (index, token, value)
    if best is None:
        return None, None, text
    index, token, value = best
    return token, value, text[:index] + text[index + len(token):]


def _repeat_confirmation_from_inferred(slots: dict) -> dict:
    size = slots.get("size", {}).get("text") or ""
    temperature = slots.get("temperature", {}).get("text") or ""
    sweetness = slots.get("sweetness", {}).get("text") or ""
    item = slots.get("item", {}).get("text") or ""
    canonical = f"{size}{temperature}{sweetness}{item}"
    complete = all([size, temperature, sweetness, item])
    return {
        "required": complete,
        "canonical_transcript": canonical if complete else "",
        "zh": f"我聽到像是「{canonical}」，請店員或店長確認。" if complete else "我聽到順序不完整，請照尺寸、溫度、甜度、品項重念。",
        "vi": f"XiaoJ nghe co the la \"{canonical}\". Vui long xac nhan truoc khi ghi POS." if complete else "Thong tin chua du, vui long doc lai theo thu tu kich co, nhiet do, do ngot, mon.",
        "en": f"I heard this as \"{canonical}\". Please confirm before POS." if complete else "The phrase is incomplete. Please repeat size, temperature, sweetness, item.",
    }


def detect_intent(text: Any, explicit_intent: Any = None) -> str:
    chosen = normalize_text(explicit_intent)
    if chosen in SUPPORTED_INTENTS:
        return chosen
    normalized = normalize_text(text)
    for intent, keywords in INTENT_RULES:
        if any(keyword in normalized for keyword in keywords):
            return intent
    return "menu_lookup"


def role_for_intent(intent: str) -> str:
    if intent in {"manager_price_change", "return_candidate", "category_move", "cash_advance_ref"}:
        return "manager"
    if intent in {
        "member_register",
        "loyalty_return",
        "sovereign_member_personalization",
        "merchant_social_candidate",
        "lineworks_notify_candidate",
    }:
        return "owner_or_manager"
    if intent == "property_community_candidate":
        return "property_admin_or_manager"
    return "cashier"


def parse_staff_voice_order(transcript: Any) -> dict:
    compact = compact_voice_text(transcript)
    size_token, size_value, rest = _consume_token(compact, VOICE_SIZE_TOKENS)
    temperature_token, temperature_value, rest = _consume_token(rest, VOICE_TEMPERATURE_TOKENS)
    sweetness_token, sweetness_value, rest = _consume_token(rest, VOICE_SWEETNESS_TOKENS)
    item = rest.strip()
    errors = []
    if not size_token:
        errors.append("missing_size_first")
    if size_token and not temperature_token:
        errors.append("missing_temperature_second")
    if size_token and temperature_token and not sweetness_token:
        errors.append("missing_sweetness_third")
    if size_token and temperature_token and sweetness_token and not item:
        errors.append("missing_item_fourth")
    valid = not errors
    inferred_rest = compact
    inferred_size_token, inferred_size_value, inferred_rest = _extract_token_anywhere(inferred_rest, VOICE_SIZE_TOKENS)
    inferred_temperature_token, inferred_temperature_value, inferred_rest = _extract_token_anywhere(
        inferred_rest, VOICE_TEMPERATURE_TOKENS
    )
    inferred_sweetness_token, inferred_sweetness_value, inferred_rest = _extract_token_anywhere(
        inferred_rest, VOICE_SWEETNESS_TOKENS
    )
    inferred_item = inferred_rest.strip()
    inferred_slots = {
        "size": {"text": inferred_size_token, "value": inferred_size_value},
        "temperature": {"text": inferred_temperature_token, "value": inferred_temperature_value},
        "sweetness": {"text": inferred_sweetness_token, "value": inferred_sweetness_value},
        "item": {"text": inferred_item or None},
    }
    repeat_confirmation = _repeat_confirmation_from_inferred(inferred_slots)
    if not valid and repeat_confirmation["required"] and "out_of_order_requires_repeat_confirmation" not in errors:
        errors.append("out_of_order_requires_repeat_confirmation")
    return {
        "grammar": "size_temperature_sweetness_item",
        "speak_order": VOICE_POS_GRAMMAR_ORDER,
        "valid": valid,
        "errors": errors,
        "repeat_confirmation_required": bool(not valid and repeat_confirmation["required"]),
        "repeat_confirmation": repeat_confirmation,
        "inferred_slots": inferred_slots,
        "slots": {
            "size": {"text": size_token, "value": size_value},
            "temperature": {"text": temperature_token, "value": temperature_value},
            "sweetness": {"text": sweetness_token, "value": sweetness_value},
            "item": {"text": item or None},
        },
    }


def xiaoj_line(intent: str) -> str:
    lines = {
        "menu_lookup": "我先查真實菜單，不亂變魔術。",
        "order_candidate": "我幫你排好下單候選，最後一下交給人確認。",
        "pos_order_create": "這是可下單資料形狀，還沒寫進 POS。",
        "payment_candidate": "付款候選準備好，錢的事要櫃台點頭。",
        "receipt_candidate": "收據候選等正式訂單號，不偷跑。",
        "translate_assist": "我翻譯，不亂加料。",
        "manager_price_change": "改價要店長確認，我不偷偷動價格。",
        "return_candidate": "退單先列候選，理由和權限要對。",
        "category_move": "分類搬家先預覽，不讓商品迷路。",
        "live_notice": "訊息送到位，證據也跟上。",
        "cash_advance_ref": "現金預支只做 evidence ref，不當付款捕手。",
        "member_register": "會員入口排好了，身份還是走正規 gate。",
        "loyalty_return": "回訪黏著要真誠，優惠也要有憑有據。",
        "staff_voice_pos_operation": "店員說、我整理，POS 真動作等人確認。",
        "sovereign_member_personalization": "會員可以被貼心服務，但身份、優惠和權益要本地驗證。",
        "merchant_social_candidate": "我可以先寫社群候選，真正發布要通過商家權威。",
        "lineworks_notify_candidate": "LINE WORKS 通知先做候選，正式發送要過本地權威與人審。",
        "property_community_candidate": "社區服務先列候選，住戶、權限和時間都要本地核對。",
        "humanoid_service_candidate": "人形服務生可以親切互動，正式動作仍等本地權威。",
        "merchant_capability_map": "這是商家系統目前可承載的發明能力地圖。",
    }
    return lines.get(intent, lines["menu_lookup"])


def _stable_hash(data: Any) -> str:
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _safe_read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def query_total_field_subfield_info(intent: str, surface: str) -> dict:
    subfields = []
    unsafe_subfields = []
    if INTENT_SUBFIELDS_ROOT.exists():
        for subfield_dir in sorted(p for p in INTENT_SUBFIELDS_ROOT.iterdir() if p.is_dir()):
            inbox = subfield_dir / "inbox"
            packets = sorted(inbox.glob("*.total_field_packet.json"), key=lambda p: p.stat().st_mtime, reverse=True) if inbox.exists() else []
            latest = packets[0] if packets else None
            packet = _safe_read_json(latest) if latest else {}
            safety = {
                "db_write": packet.get("db_write") is True,
                "service_restart": packet.get("service_restart") is True,
                "deploy": packet.get("deploy") is True,
                "secret_read": packet.get("secret_read") is True,
                "member_plaintext_read": packet.get("member_plaintext_read") is True,
            }
            if any(safety.values()):
                unsafe_subfields.append(
                    {
                        "subfield": subfield_dir.name,
                        "latest_packet_ref": latest.name if latest else "",
                        "unsafe_flags": sorted(flag for flag, enabled in safety.items() if enabled),
                    }
                )
            subfields.append(
                {
                    "subfield": subfield_dir.name,
                    "inbox_present": inbox.exists(),
                    "packet_count": len(packets),
                    "latest_packet_ref": latest.name if latest else "",
                    "latest_packet_hash": _stable_hash(packet) if packet else "",
                    "latest_state": str(packet.get("state") or ""),
                    "latest_run_id": str(packet.get("run_id") or ""),
                    "mission": str(packet.get("mission") or ""),
                    "safety": safety,
                }
            )
    state = "TOTAL_FIELD_SUBFIELD_QUERY_OK" if subfields else "HOLD_TOTAL_FIELD_SUBFIELD_INFO_MISSING"
    if unsafe_subfields:
        state = "HOLD_TOTAL_FIELD_SUBFIELD_DANGER_FLAGS"
    result = {
        "schema": "W7TP_TOTAL_FIELD_SUBFIELD_QUERY_V1",
        "query_required": True,
        "queried": True,
        "state": state,
        "source_root": "runtime/intent_subfields",
        "intent": intent,
        "surface": surface,
        "subfield_count": len(subfields),
        "subfields": subfields,
        "unsafe_subfield_count": len(unsafe_subfields),
        "unsafe_subfields": unsafe_subfields,
        "danger_flags_present": bool(unsafe_subfields),
        "full_packet_body_exposed": False,
        "secret_read": False,
        "member_plaintext_read": False,
        "db_write": False,
        "deploy": False,
        "service_restart": False,
    }
    result["query_hash"] = _stable_hash(
        {
            "schema": result["schema"],
            "state": result["state"],
            "intent": intent,
            "surface": surface,
            "subfields": subfields,
            "unsafe_subfields": unsafe_subfields,
        }
    )
    return result


def _safe_candidate_projection(intent: str, state: str, payload: dict) -> dict:
    candidate_action = payload.get("candidate_action")
    if not isinstance(candidate_action, dict):
        candidate_action = {}
    total_field_query = payload.get("total_field_subfield_query")
    total_field_query_hash = total_field_query.get("query_hash") if isinstance(total_field_query, dict) else ""
    return {
        "intent": intent,
        "state": state,
        "surface": INTENT_AUTHORITY_SURFACES.get(intent, "general"),
        "candidate_action": candidate_action,
        "total_field_subfield_query_hash": total_field_query_hash,
        "input_text_present": bool(payload.get("input_text_present") or payload.get("transcript_present")),
        "amount_present": "amount" in payload,
        "line_count": len(payload.get("order_lines") or []),
        "member_plaintext_read": False,
        "raw_audio_saved": bool(payload.get("raw_audio_saved", False)),
        "cloud_authority": False,
    }


def _build_authority_packet(intent: str, state: str, payload: dict) -> dict:
    projection = _safe_candidate_projection(intent, state, payload)
    candidate_hash = _stable_hash(projection)
    surface = INTENT_AUTHORITY_SURFACES.get(intent, "general")
    verifiers = INTENT_LOCAL_VERIFIERS.get(intent, ["local_policy_gate"])
    total_field_query = payload.get("total_field_subfield_query") if isinstance(payload.get("total_field_subfield_query"), dict) else {}
    seed = {
        "schema": "W7TP_MERCHANT_AUTHORITY_PACKET_V1",
        "packet_type": "merchant_candidate_authority_packet",
        "intent": intent,
        "surface": surface,
        "state_code": state,
        "candidate_hash": candidate_hash,
        "total_field_subfield_query_required": True,
        "total_field_subfield_query_hash": total_field_query.get("query_hash", ""),
        "total_field_subfield_state": total_field_query.get("state", "HOLD_TOTAL_FIELD_SUBFIELD_INFO_MISSING"),
        "route_key": verifiers[0],
        "candidate_only": True,
        "cloud_authority": False,
        "local_authority": "discrete_state_core",
        "full_body_transmitted": False,
        "reality_layer": "IMAGINED_CANDIDATE",
        "llm_hallucination_allowed": "conditional_candidate_only",
        "reality_state_source": "total_field_local_reconstruction_and_verifier",
    }
    packet_hash = _stable_hash(seed)
    return {
        **seed,
        "packet_hash": packet_hash,
        "ttl": "P1_SESSION_TTL_REQUIRED",
        "nonce": packet_hash[:24],
        "generative_transmission": {
            "full_body_transmitted": False,
            "reconstruction_index": f"{surface}:{intent}:p1",
            "state_delta": f"candidate_to_{state}",
            "route_key": verifiers[0],
            "state_code": state,
            "candidate_hash": candidate_hash,
            "evidence_hash": _stable_hash({"candidate_hash": candidate_hash, "route_key": verifiers[0]}),
            "total_field_subfield_query_hash": total_field_query.get("query_hash", ""),
            "generation_parameters": [
                "intent",
                "surface",
                "state_code",
                "route_key",
                "candidate_hash",
                "total_field_subfield_query_hash",
                "reality_layer",
            ],
            "excluded_bodies": [
                "member_plaintext",
                "raw_audio",
                "raw_video",
                "payment_data",
                "oauth_token",
                "client_secret",
                "odoo_credentials",
                "private_lookup_table",
            ],
        },
        "reality_boundary": {
            "policy_schema": REALITY_LAYER_POLICY["schema"],
            "llm_hallucination_allowed": "conditional",
            "cloud_output_layer": "IMAGINED_CANDIDATE",
            "real_world_fact_layer": "REAL_VERIFIED",
            "execution_layer": "EXECUTABLE_AUTHORIZED",
            "cloud_can_label_real_verified": False,
            "cloud_can_set_executable_authorized": False,
            "total_field_distinguishes_real_or_imagined": True,
            "local_reconstruction_required_for_real": True,
            "local_verifier_required_for_execution": True,
        },
        "authority_protocol_fields": {
            "intent_field": intent,
            "state_field": state,
            "reality_layer_field": "IMAGINED_CANDIDATE",
            "total_field_subfield_query_field": "required_before_generation",
            "evidence_field": "evidence_hash",
            "permission_field": "local_verifier_required",
            "risk_field": "merchant_impacting" if intent in MERCHANT_IMPACTING_INTENTS else "read_or_assist_only",
            "reconstruction_field": "local_reconstruction_required",
            "failure_policy": ["HOLD", "QUARANTINE", "DEAD_LETTER"],
            "execution_gate_condition": "execution_allowed_true_from_local_verifier",
        },
    }


def _local_reconstruction(intent: str, payload: dict, packet: dict) -> dict:
    surface = packet.get("surface") or INTENT_AUTHORITY_SURFACES.get(intent, "general")
    total_field_query = payload.get("total_field_subfield_query") if isinstance(payload.get("total_field_subfield_query"), dict) else {}
    return {
        "schema": "W7TP_LOCAL_RECONSTRUCTION_V1",
        "state": "RECONSTRUCTED_FOR_LOCAL_AUTHORITY",
        "packet_hash": packet["packet_hash"],
        "surface": surface,
        "total_field_subfield_query": {
            "required": True,
            "queried": total_field_query.get("queried") is True,
            "state": total_field_query.get("state", "HOLD_TOTAL_FIELD_SUBFIELD_INFO_MISSING"),
            "query_hash": total_field_query.get("query_hash", ""),
            "subfield_count": int(total_field_query.get("subfield_count") or 0),
            "unsafe_subfield_count": int(total_field_query.get("unsafe_subfield_count") or 0),
            "danger_flags_present": total_field_query.get("danger_flags_present") is True,
        },
        "full_body_received": False,
        "member_plaintext_absent": True,
        "raw_audio_absent": payload.get("raw_audio_saved") is False or not payload.get("raw_audio_saved"),
        "cloud_authority": False,
        "reality_boundary": {
            "input_layer": packet.get("reality_layer", "IMAGINED_CANDIDATE"),
            "total_field_distinguishes_real_or_imagined": True,
            "real_verified_requires_local_sources": True,
            "executable_authorized_requires_local_verifier": True,
            "llm_hallucination_allowed_only_as_candidate": True,
        },
        "local_sources": [
            "authority_packet",
            "total_field_subfield_query",
            "local_menu_source_lock",
            "local_member_policy_ref",
            "local_pos_policy_ref",
            "local_social_policy_ref",
            "local_lineworks_policy_ref",
            "local_property_policy_ref",
        ],
        "reconstructed_refs": {
            "menu_source_lock_state": MENU_SOURCE_LOCK["state"],
            "menu_authority": MENU_SOURCE_LOCK["current_menu_authority"],
            "member_ref_mode": "reference_only",
            "pos_write_mode": "blocked_until_formal_gate",
            "payment_mode": "separate_payment_gate_required",
            "social_publish_mode": "local_approval_required",
            "lineworks_send_mode": "blocked_until_formal_gate",
            "property_action_mode": "local_approval_required",
        },
        "verifier_targets": INTENT_LOCAL_VERIFIERS.get(intent, ["local_policy_gate"]),
    }


def _verification_failure_reasons(intent: str, payload: dict, reconstruction: dict) -> list[str]:
    reasons = []
    total_field_query = reconstruction.get("total_field_subfield_query", {})
    if total_field_query.get("required") is not True or total_field_query.get("queried") is not True:
        reasons.append("total_field_subfield_query_missing")
    elif total_field_query.get("state") != "TOTAL_FIELD_SUBFIELD_QUERY_OK":
        reasons.append("total_field_subfield_query_not_ok")
    elif int(total_field_query.get("subfield_count") or 0) <= 0:
        reasons.append("total_field_subfield_empty")
    if total_field_query.get("danger_flags_present") is True or int(total_field_query.get("unsafe_subfield_count") or 0) > 0:
        reasons.append("total_field_subfield_danger_flags")
    if payload.get("runtime_ready") is not True and intent not in READ_ONLY_LOCAL_EXECUTE_INTENTS:
        reasons.append("runtime_release_required")
    if intent in {"order_candidate", "pos_order_create", "staff_voice_pos_operation", "humanoid_service_candidate"}:
        if reconstruction["reconstructed_refs"]["menu_authority"] is not True:
            reasons.append("menu_authority_false")
    if intent in {"pos_order_create", "staff_voice_pos_operation", "humanoid_service_candidate"}:
        reasons.append("formal_pos_gate_required")
    if intent == "payment_candidate":
        reasons.append("separate_payment_gate_required")
        if float(payload.get("amount") or 0) < 0:
            reasons.append("invalid_negative_amount")
    if intent in {"member_register", "loyalty_return", "sovereign_member_personalization"}:
        reasons.append("sovereign_member_policy_release_required")
    if intent == "merchant_social_candidate":
        reasons.append("publication_approval_required")
    if intent == "lineworks_notify_candidate":
        reasons.append("lineworks_send_release_required")
    if intent == "property_community_candidate":
        reasons.append("resident_unit_role_policy_required")
    if payload.get("safety_flags", {}).get("MEMBER_PLAINTEXT_READ") is not False:
        reasons.append("member_plaintext_boundary_failed")
    if payload.get("safety_flags", {}).get("RAW_AUDIO_SAVED") is not False:
        reasons.append("raw_audio_boundary_failed")
    return reasons


def _local_verifier(intent: str, payload: dict, reconstruction: dict) -> dict:
    reasons = _verification_failure_reasons(intent, payload, reconstruction)
    invalid_reasons = {"invalid_negative_amount", "member_plaintext_boundary_failed", "raw_audio_boundary_failed"}
    if any(reason in invalid_reasons for reason in reasons):
        decision = "DEAD_LETTER"
        execution_allowed = False
    elif reasons:
        decision = "HOLD"
        execution_allowed = False
    else:
        decision = "EXECUTE"
        execution_allowed = intent not in MERCHANT_IMPACTING_INTENTS
        if intent in MERCHANT_IMPACTING_INTENTS:
            decision = "HOLD"
            reasons.append("merchant_impacting_action_requires_human_release")
    return {
        "schema": "W7TP_LOCAL_DISCRETE_AUTHORITY_VERIFIER_V1",
        "verifiers": reconstruction["verifier_targets"],
        "decision": decision,
        "execution_allowed": execution_allowed,
        "failure_reasons": reasons,
        "cloud_candidate_not_authority": True,
        "no_floating_point_authority": True,
        "reality_layer_verification": {
            "llm_hallucination_allowed": "conditional_candidate_only",
            "cloud_output_layer": "IMAGINED_CANDIDATE",
            "real_world_fact_authority": "total_field_local_reconstruction",
            "execution_authority": "local_discrete_state_verifier",
            "cloud_can_upgrade_to_real_or_executable": False,
        },
        "authority_inputs": [
            "integer_state_code",
            "bit_flag",
            "hash_reference",
            "lookup_key",
            "ttl",
            "nonce",
            "evidence_ref",
        ],
    }


def _evidence_seal(packet: dict, reconstruction: dict, verifier: dict) -> dict:
    seed = {
        "packet_hash": packet["packet_hash"],
        "decision": verifier["decision"],
        "failure_reasons": verifier["failure_reasons"],
        "verifiers": verifier["verifiers"],
        "reconstruction_state": reconstruction["state"],
    }
    return {
        "schema": "W7TP_MERCHANT_EVIDENCE_SEAL_V1",
        "packet_hash": packet["packet_hash"],
        "decision": verifier["decision"],
        "failure_reasons": verifier["failure_reasons"],
        "verifier_state": "LOCAL_DISCRETE_AUTHORITY",
        "seal_hash": _stable_hash(seed),
        "raw_audio_saved": False,
        "member_plaintext_read": False,
        "formal_pos_write": False,
        "payment_capture": False,
    }


def _authority_chain(intent: str, state: str, payload: dict) -> dict:
    packet = _build_authority_packet(intent, state, payload)
    reconstruction = _local_reconstruction(intent, payload, packet)
    verifier = _local_verifier(intent, payload, reconstruction)
    seal = _evidence_seal(packet, reconstruction, verifier)
    return {
        "authority_packet": packet,
        "local_reconstruction": reconstruction,
        "local_verifier": verifier,
        "execution_gate": {
            "state": verifier["decision"],
            "execution_allowed": verifier["execution_allowed"],
            "allowed_results": ["EXECUTE", "HOLD", "QUARANTINE", "DEAD_LETTER"],
            "formal_pos_write": False,
            "payment_capture": False,
            "cloud_authority": False,
            "requires_human_release": not verifier["execution_allowed"],
        },
        "data_breathing_flow": [
            "AI_CANDIDATE",
            "AUTHORITY_PACKET",
            "LOCAL_RECONSTRUCTION",
            "LOCAL_VERIFIER",
            verifier["decision"],
            "EVIDENCE_SEAL",
        ],
        "evidence_seal": seal,
    }


def _ref_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return bool(str(value.get("ref") or "").strip()) or bool(str(value.get("packet_hash") or "").strip())
    return True


def _normalize_release_ref(value: Any) -> dict:
    if not isinstance(value, dict):
        return {
            "type": type(value).__name__,
            "ref_present": _ref_present(value),
            "verified": False,
        }
    return {
        "ref": str(value.get("ref") or "").strip(),
        "packet_hash": str(value.get("packet_hash") or "").strip().lower(),
        "verifier": str(value.get("verifier") or "").strip(),
        "verified": value.get("verified") is True,
    }


def _release_ref_hash(value: Any) -> str:
    return _stable_hash(_normalize_release_ref(value))


def _release_ref_verified(value: Any) -> bool:
    ref = _normalize_release_ref(value)
    if ref.get("verified") is not True:
        return False
    if ref.get("verifier") not in RELEASE_REF_VERIFIER_ALLOWLIST:
        return False
    if not re.fullmatch(r"[a-f0-9]{64}", str(ref.get("packet_hash") or "")):
        return False
    return bool(str(ref.get("ref") or "").strip())


def _release_gate_decision(gate_id: str, refs: dict) -> dict:
    gate = FORMAL_RELEASE_GATES[gate_id]
    required = gate["required_refs"]
    refs = refs if isinstance(refs, dict) else {}
    provided_keys = [key for key in required if _ref_present(refs.get(key))]
    provided_ref_hashes = {key: _release_ref_hash(refs.get(key)) for key in provided_keys}
    verified_ref_keys = [key for key in provided_keys if _release_ref_verified(refs.get(key))]
    unverified_ref_keys = [key for key in provided_keys if key not in verified_ref_keys]
    missing = [key for key in required if key not in provided_keys]
    total_field_query = query_total_field_subfield_info(gate_id, f"formal_release:{gate_id}")
    total_field_ready = (
        total_field_query.get("state") == "TOTAL_FIELD_SUBFIELD_QUERY_OK"
        and int(total_field_query.get("unsafe_subfield_count") or 0) == 0
        and total_field_query.get("danger_flags_present") is not True
    )
    if total_field_query.get("state") == "HOLD_TOTAL_FIELD_SUBFIELD_DANGER_FLAGS":
        total_field_blocker = "total_field_subfield_danger_flags"
    elif not total_field_ready:
        total_field_blocker = "total_field_subfield_query_ok"
    else:
        total_field_blocker = ""
    release_ready = not missing and not unverified_ref_keys and total_field_ready
    if release_ready:
        decision = "RELEASE_READY_FOR_HUMAN_ACTIVATION"
    elif missing:
        decision = "HOLD_RELEASE_REQUIREMENTS_INCOMPLETE"
    elif unverified_ref_keys:
        decision = "HOLD_RELEASE_REFS_UNVERIFIED"
    elif total_field_blocker == "total_field_subfield_danger_flags":
        decision = "HOLD_RELEASE_TOTAL_FIELD_DANGER_FLAGS"
    else:
        decision = "HOLD_RELEASE_REQUIREMENTS_INCOMPLETE"
    seed = {
        "gate_id": gate_id,
        "provided_ref_keys": sorted(provided_keys),
        "verified_ref_keys": sorted(verified_ref_keys),
        "unverified_ref_keys": sorted(unverified_ref_keys),
        "missing_refs": missing,
        "total_field_blocker": total_field_blocker,
        "total_field_query_hash": total_field_query.get("query_hash", ""),
    }
    return {
        "gate_id": gate_id,
        "title": gate["title"],
        "decision": decision,
        "release_ready": release_ready,
        "required_refs": required,
        "provided_ref_keys": provided_keys,
        "verified_ref_keys": verified_ref_keys,
        "unverified_ref_keys": unverified_ref_keys,
        "provided_ref_hashes": provided_ref_hashes,
        "missing_refs": missing,
        "total_field_blocker": total_field_blocker,
        "total_field_subfield_query": total_field_query,
        "release_packet_hash": _stable_hash(seed),
        "forbidden_side_effects_in_p1": gate["forbidden_side_effects_in_p1"],
        "p1_side_effects": {
            "member_plaintext_read": False,
            "formal_db_write": False,
            "formal_pos_write": False,
            "payment_capture": False,
            "external_api_call": False,
            "service_restart": False,
            "deploy": False,
        },
    }


def formal_release_status_payload(refs: dict | None = None) -> dict:
    refs = refs or {}
    gates = {gate_id: _release_gate_decision(gate_id, refs.get(gate_id, refs)) for gate_id in FORMAL_RELEASE_GATES}
    all_ready = all(gate["release_ready"] for gate in gates.values())
    return base_payload(
        "merchant_capability_map",
        "FORMAL_RELEASE_GATES_READY_FOR_REVIEW" if all_ready else "HOLD_FORMAL_RELEASE_GATES_INCOMPLETE",
        {
            "formal_release_gates": gates,
            "all_release_gates_ready": all_ready,
            "activation_mode": "human_activation_required",
            "p1_runtime_does_not_execute_formal_writes": True,
            "formal_member_registration_release": gates["member_registration"]["decision"],
            "formal_pos_order_release": gates["pos_order"]["decision"],
            "formal_payment_release": gates["payment"]["decision"],
            "formal_lineworks_send_release": gates["lineworks_send"]["decision"],
            "formal_db_write": False,
            "formal_pos_write": False,
            "payment_capture": False,
            "formal_lineworks_send": False,
            "external_api_call": False,
            "member_plaintext_read": False,
        },
    )


def base_payload(intent: str, state: str, extra: dict | None = None) -> dict:
    payload = {
        "intent": intent,
        "state": state,
        "runtime_ready": False,
        "requires_human_release": True,
        "source": "wuchang_cafe_ai_gateway_p1_intent_engine",
        "menu_source_lock": MENU_SOURCE_LOCK,
        "xiaoj_line": xiaoj_line(intent),
        "safety_flags": SAFETY_FLAGS,
    }
    if extra:
        payload.update(extra)
    payload["total_field_subfield_query"] = query_total_field_subfield_info(
        intent,
        INTENT_AUTHORITY_SURFACES.get(intent, "general"),
    )
    payload.update(_authority_chain(intent, state, payload))
    return payload


def candidate_action(text: Any, explicit_intent: Any = None) -> dict:
    intent = detect_intent(text, explicit_intent)
    return base_payload(
        intent,
        "P1_MULTI_INTENT_API_SHELL",
        {
            "input_text_present": bool(normalize_text(text)),
            "raw_audio_saved": False,
            "candidate_action": {
                "intent": intent,
                "confirm_state": "draft",
                "requires_role": role_for_intent(intent),
            },
        },
    )


def merchant_capability_payload() -> dict:
    return base_payload(
        "merchant_capability_map",
        "P1_MERCHANT_INVENTION_CAPABILITY_MAP_READY",
        {
            "capability_map": MERCHANT_INVENTION_CAPABILITY_MAP,
            "formal_pos_write": False,
            "payment_capture": False,
            "member_plaintext_read": False,
            "cloud_authority": False,
            "local_authority_required": True,
        },
    )


def _lineworks_message_preview(message: Any) -> str:
    text = " ".join(str(message or "").split())
    text = re.sub(r"sk-[A-Za-z0-9_-]{12,}", "[REDACTED_KEY]", text)
    text = re.sub(r"(?i)(access|refresh|id)_token\s*[:=]\s*\S+", "[REDACTED_TOKEN]", text)
    text = re.sub(r"(?i)client_secret\s*[:=]\s*\S+", "[REDACTED_SECRET]", text)
    return text[:280]


def lineworks_notify_payload(message: Any, target_ref: Any = "", channel: Any = "member_service", actor_ref: Any = "") -> dict:
    preview = _lineworks_message_preview(message)
    target_ref_present = bool(str(target_ref or "").strip())
    target_hash = _stable_hash({"target_ref": str(target_ref or ""), "channel": str(channel or "")}) if target_ref_present else ""
    message_hash = _stable_hash({"preview": preview, "channel": str(channel or "")})
    return base_payload(
        "lineworks_notify_candidate",
        "HOLD_LINEWORKS_SEND_RELEASE_REQUIRED",
        {
            "lineworks_notify_candidate": {
                "channel": str(channel or "member_service"),
                "message_preview": preview,
                "message_hash": message_hash,
                "target_ref_present": target_ref_present,
                "target_ref_hash": target_hash,
                "target_ref_mode": "hash_only",
                "actor_ref_present": bool(str(actor_ref or "").strip()),
                "delivery_mode": "candidate_only",
                "official_api_endpoint_template": "POST https://www.worksapis.com/v1.0/bots/{botId}/users/{userId}/messages",
                "required_scope_refs": ["bot", "bot.message"],
            },
            "candidate_action": {
                "intent": "lineworks_notify_candidate",
                "confirm_state": "draft",
                "requires_role": role_for_intent("lineworks_notify_candidate"),
                "message_hash": message_hash,
                "target_ref_hash": target_hash,
            },
            "lineworks_release_gate": "lineworks_send",
            "formal_lineworks_send": False,
            "external_api_call": False,
            "member_plaintext_read": False,
            "token_read": False,
            "secret_read": False,
            "cloud_authority": False,
        },
    )


def staff_voice_pos_payload(transcript: Any, staff_ref: Any = "", language: Any = "zh-Hant") -> dict:
    detected = detect_intent(transcript)
    if detected == "menu_lookup":
        detected = "order_candidate"
    grammar = parse_staff_voice_order(transcript)
    if grammar["valid"]:
        detected = "order_candidate"
    return base_payload(
        "staff_voice_pos_operation",
        "P1_STAFF_VOICE_POS_API_SHELL",
        {
            "transcript_present": bool(normalize_text(transcript)),
            "raw_audio_saved": False,
            "language": str(language or "zh-Hant"),
            "staff_ref": str(staff_ref or ""),
            "voice_pos_grammar": grammar,
            "detected_pos_intent": detected,
            "candidate_action": {
                "intent": detected,
                "confirm_state": "draft",
                "requires_role": role_for_intent(detected),
                "grammar_valid": grammar["valid"],
                "repeat_confirmation_required": grammar["repeat_confirmation_required"],
            },
            "pos_order_created": False,
            "payment_capture": False,
            "odoo_db_write": False,
        },
    )


def parse_order_lines(raw_lines: Any) -> list[OrderLine]:
    if not isinstance(raw_lines, list):
        return []
    lines = []
    for line in raw_lines[:20]:
        if not isinstance(line, dict):
            continue
        lines.append(
            OrderLine(
                product_ref=str(line.get("product_ref") or line.get("id") or ""),
                name=str(line.get("name") or ""),
                quantity=float(line.get("quantity") or 1),
                price=float(line.get("price") or 0),
            )
        )
    return lines


def order_payload(raw_lines: Any) -> dict:
    lines = parse_order_lines(raw_lines)
    return base_payload(
        "pos_order_create",
        "HOLD_RUNTIME_POS_ORDER_RELEASE_REQUIRED",
        {
            "order_lines": [
                {
                    "product_ref": line.product_ref,
                    "name": line.name,
                    "quantity": line.quantity,
                    "price": line.price,
                    "subtotal": line.subtotal,
                }
                for line in lines
            ],
            "amount": sum(line.subtotal for line in lines),
            "pos_order_created": False,
            "odoo_db_write": False,
        },
    )


def payment_payload(amount: Any = 0, mode: Any = "cash") -> dict:
    return base_payload(
        "payment_candidate",
        "HOLD_RUNTIME_PAYMENT_RELEASE_REQUIRED",
        {
            "mode": str(mode or "cash"),
            "amount": float(amount or 0),
            "payment_capture": False,
            "cashier_confirmation_required": True,
        },
    )


def receipt_payload(order_ref: Any = "") -> dict:
    return base_payload(
        "receipt_candidate",
        "HOLD_RUNTIME_POS_RECEIPT_REQUIRED",
        {
            "order_ref": str(order_ref or ""),
            "receipt_created": False,
            "waiting_for_odoo_pos_order_id": True,
        },
    )
