"""Pure XiaoJ P1 local intent engine.

This module has no Odoo imports and no external side effects. It turns text,
order lines, payment params, and receipt refs into candidate payloads that the
Odoo controller can expose after module release.
"""

from __future__ import annotations

from dataclasses import dataclass
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
}


INTENT_RULES = [
    ("staff_voice_pos_operation", ("語音pos", "voice pos", "店員語音", "nhan vien noi", "pos bang giong noi")),
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
    if intent in {"member_register", "loyalty_return"}:
        return "owner_or_manager"
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
    }
    return lines.get(intent, lines["menu_lookup"])


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
