"""上品聊國咖啡館重新總店 2.3：精準點餐與輕量對話投影。

結構化點餐結果與語氣生成嚴格分離。模型只能潤飾小J的說話方式，
不能修改品項、數量、價格、座位狀態或任何外部效果。
"""

from __future__ import annotations

import json
import hashlib
import re
import urllib.error
import urllib.request
from typing import Any


SHOWCASE_MENU = (
    {"ref": "public-americano", "name": "上品美式咖啡", "price": 90, "aliases": ("上品美式", "美式咖啡", "美式")},
    {"ref": "public-latte", "name": "上品拿鐵咖啡", "price": 90, "aliases": ("上品拿鐵", "拿鐵咖啡", "拿鐵")},
    {"ref": "public-bagel", "name": "烤貝果", "price": 55, "aliases": ("烤貝果", "貝果")},
    {"ref": "public-mandheling", "name": "黃金曼特寧", "price": 150, "aliases": ("黃金曼特寧", "曼特寧")},
    {"ref": "public-mamba", "name": "曼巴混合咖啡", "price": 135, "aliases": ("曼巴混合咖啡", "曼巴咖啡", "曼巴")},
    {"ref": "public-earl-grey", "name": "精選伯爵紅茶", "price": 65, "aliases": ("精選伯爵紅茶", "伯爵紅茶", "紅茶")},
)

_CHINESE_QUANTITY = {
    "一": 1,
    "二": 2,
    "兩": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


def _quantity_value(raw: str | None) -> int:
    if not raw:
        return 1
    if raw.isdigit():
        return min(max(int(raw), 1), 20)
    return _CHINESE_QUANTITY.get(raw, 1)


def _quantity_near_alias(text: str, alias: str) -> int:
    quantity = r"([一二兩三四五六七八九十]|\d{1,2})"
    escaped = re.escape(alias)
    before = re.search(quantity + r"\s*(?:杯|份|個)?\s*" + escaped, text)
    if before:
        return _quantity_value(before.group(1))
    after = re.search(escaped + r"\s*" + quantity + r"\s*(?:杯|份|個)?", text)
    if after:
        return _quantity_value(after.group(1))
    return 1


def extract_order_preview(text: Any) -> list[dict]:
    normalized = str(text or "").strip()
    lines = []
    for item in SHOWCASE_MENU:
        matched_alias = next((alias for alias in item["aliases"] if alias in normalized), None)
        if not matched_alias:
            continue
        quantity = _quantity_near_alias(normalized, matched_alias)
        lines.append({
            "product_ref": item["ref"],
            "name": item["name"],
            "quantity": quantity,
            "unit_price": item["price"],
            "subtotal": quantity * item["price"],
        })
    return lines


def _arrival_minutes(text: str) -> int | None:
    match = re.search(r"(\d{1,3})\s*分(?:鐘)?後", text)
    if not match:
        return None
    return min(max(int(match.group(1)), 1), 180)


def _fallback_line(text: str, order_lines: list[dict], seat_requested: bool) -> str:
    if order_lines:
        order_text = "、".join(f"{line['name']} {line['quantity']} 份" for line in order_lines)
        ending = "；座位要等現場狀態接上後才能確認，我不拿空氣替你佔位。" if seat_requested else "。"
        return f"收到，{order_text}{ending}笑話可以加料，訂單一個字都不能亂加。"
    if seat_requested:
        return "我可以幫你問位子，但目前沒有即時座位訊號；我寧可老實站著，也不讓你到店後罰站。"
    if any(word in text for word in ("社群", "評價", "趨勢", "分析")):
        return "社群聲量可以分析，但每一句結論都要帶來源與時間；小J可以風趣，數據不能耍嘴皮。"
    return "想喝什麼直接說，我會先把需求整理清楚；幽默是招待，精準才是本業。"


def _safe_flair(line: Any) -> str | None:
    value = re.sub(r"<think>.*?</think>", "", str(line or ""), flags=re.S).strip()
    forbidden = (
        "預訂", "訂位", "下單", "付款", "結帳", "有位", "座位", "確認", "稍後",
        "已幫", "已經", "杯", "份", "元", "價格", "拿鐵", "美式", "貝果", "曼特寧", "曼巴", "紅茶",
    )
    if not value or len(value) > 48:
        return None
    if any(word in value for word in forbidden):
        return None
    if re.search(r"[0-9A-Za-z$]", value):
        return None
    return value


def _model_flair(text: str, frozen_facts: dict, endpoint: str, model: str) -> tuple[str | None, str]:
    prompt = (
        "你是上品聊國咖啡館重新總店的影音AI店員小J。只生成一句48字內的繁體中文幽默開場。"
        "不得提及或影射品項、杯數、價格、座位、預訂、下單、付款、確認或完成狀態，也不得輸出英文及思考過程。"
        "所有交易事實會由8DADI確定性層另行覆誦，你完全不能碰。\n"
        f"凍結事實：{json.dumps(frozen_facts, ensure_ascii=False, sort_keys=True)}\n"
        f"顧客說：{text}"
    )
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "30m",
        "options": {"temperature": 0.72, "num_predict": 40},
    }, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(endpoint, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
        line = _safe_flair(payload.get("response"))
        return line, "本機模型語氣" if line else "確定性備援"
    except (OSError, ValueError, urllib.error.URLError, TimeoutError):
        return None, "確定性備援"


def build_storefront_response(
    text: Any,
    *,
    model_endpoint: str = "http://wuchang_gpu_brain:11434/api/generate",
    model: str = "gemma3:4b",
    use_model: bool = True,
) -> dict:
    normalized = str(text or "").strip()[:600]
    order_lines = extract_order_preview(normalized)
    seat_requested = any(word in normalized for word in ("位子", "位置", "座位", "有位"))
    arrival_minutes = _arrival_minutes(normalized)
    total = sum(line["subtotal"] for line in order_lines)
    frozen_facts = {
        "order_lines": order_lines,
        "total": total,
        "seat_state": "未觀測" if seat_requested else "未詢問",
        "arrival_minutes": arrival_minutes,
        "order_committed": False,
        "payment_captured": False,
    }
    preview_ref = hashlib.sha256(
        json.dumps(
            {"intent": normalized, "frozen_facts": frozen_facts},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    fallback = _fallback_line(normalized, order_lines, seat_requested)
    flair, language_source = (
        _model_flair(normalized, frozen_facts, model_endpoint, model)
        if use_model
        else (None, "確定性快速路徑")
    )
    speech = f"{flair} {fallback}" if flair else fallback
    return {
        "state": "ACTIVE_STOREFRONT_PREVIEW",
        "state_zh": "商店展示已回應；正式下單尚未放行",
        "xiaoj_line": speech,
        "language_source": f"{language_source}＋確定性點餐" if flair else language_source,
        "frozen_facts": frozen_facts,
        "customer_confirmation": {
            "required": bool(order_lines),
            "state": "AWAITING_CUSTOMER_TOUCH" if order_lines else "NOT_APPLICABLE",
            "state_zh": "等待顧客在店內觸控螢幕確認" if order_lines else "目前沒有可確認的點餐品項",
            "preview_ref": preview_ref,
        },
        "menu_source": {
            "state": "PUBLIC_INDEX_EVIDENCE_ONLY",
            "state_zh": "公開菜單索引僅供展示；正式價格與庫存等待店內 Odoo 對齊",
            "observed_on": "2026-09-03",
        },
        "eight_dimensional_receipt": {
            "D1_意圖": "咖啡館服務與自然語言點餐",
            "D2_狀態": "展示回應；訂單未寫入",
            "D3_座標": "上品聊國咖啡館重新總店／瀏覽器介面",
            "D4_證據": "公開菜單索引與本次結構化解析",
            "D5_效果": "只產生點餐預覽",
            "D6_生成式傳輸": (
                "未啟用（NOT_INVOKED）：本次模型語氣與確定性點餐解析不是生成式傳輸；"
                "跨節點重建必須另附目標基底、最小必要差異、引用、座標、重建規則與驗證規則。"
            ),
            "D7_風險": "即時座位、庫存與正式菜單未對齊時拒絕寫單",
            "D8_權威": "總場未放行交易效果",
        },
    }


def build_storefront_flair(
    text: Any,
    *,
    model_endpoint: str = "http://wuchang_gpu_brain:11434/api/generate",
    model: str = "gemma3:4b",
) -> dict:
    """Generate optional personality without delaying or changing store facts."""
    preview = build_storefront_response(text, use_model=False)
    flair, source = _model_flair(
        str(text or "").strip()[:600],
        preview["frozen_facts"],
        model_endpoint,
        model,
    )
    return {
        "state": "OPTIONAL_APPEARANCE_READY" if flair else "DETERMINISTIC_APPEARANCE_RETAINED",
        "flair": flair,
        "language_source": source,
        "effects": {"order_written": False, "payment_written": False, "facts_changed": False},
    }


def confirm_storefront_preview(
    text: Any,
    preview_ref: Any,
    acknowledged: Any,
    voice_readback_completed: Any,
) -> dict:
    """Record the explicit touch gate without pretending a POS order exists."""
    preview = build_storefront_response(
        text,
        model_endpoint="http://127.0.0.1:1/no-model-needed",
        use_model=False,
    )
    expected_ref = preview["customer_confirmation"]["preview_ref"]
    lines = preview["frozen_facts"]["order_lines"]
    accepted = (
        bool(lines)
        and acknowledged is True
        and voice_readback_completed is True
        and str(preview_ref or "") == expected_ref
    )
    return {
        "state": "CUSTOMER_TOUCH_CONFIRMED_NO_ORDER_EFFECT" if accepted else "CONFIRMATION_REJECTED",
        "state_zh": (
            "顧客已觸控確認點餐預覽；正式送單仍待店內 Odoo 菜單對齊"
            if accepted
            else "觸控確認未成立；訂單沒有送出"
        ),
        "customer_touch_confirmed": accepted,
        "preview_ref": expected_ref if accepted else None,
        "effects": {"order_written": False, "payment_written": False},
        "eight_dimensional_receipt": {
            "D1_意圖": "顧客確認點餐預覽",
            "D2_狀態": "觸控確認成立；正式訂單尚未建立" if accepted else "觸控確認未成立",
            "D3_座標": "店內瀏覽器觸控確認門",
            "D4_證據": "語音複誦完成、真人明示確認、本次預覽指紋一致" if accepted else "語音複誦、預覽指紋或真人明示確認不一致",
            "D5_效果": "只確認顧客意圖，不寫入訂單或付款",
            "D6_生成式傳輸": (
                "未啟用（NOT_INVOKED）：本次只重新計算點餐預覽並核對指紋，"
                "不構成跨節點目標狀態的生成式重建。"
            ),
            "D7_風險": "真實菜單未對齊前拒絕 POS 寫入",
            "D8_權威": "HOLD_REAL_ODOO_MENU_ALIGNMENT",
        },
    }
