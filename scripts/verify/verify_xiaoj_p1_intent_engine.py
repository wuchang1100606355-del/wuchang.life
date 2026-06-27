#!/usr/bin/env python3
"""Verify the pure XiaoJ P1 local intent engine.

This imports only the pure service module and exercises multi-intent, order,
payment, and receipt payloads. It does not import Odoo, write DB rows, create
orders, capture payments, save raw audio, call external APIs, or read secrets.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/p1_intent_engine.py"


def fail(message: str) -> None:
    print(f"VERIFY_FAIL={message}")
    raise SystemExit(1)


def load_engine():
    spec = importlib.util.spec_from_file_location("p1_intent_engine", ENGINE)
    if spec is None or spec.loader is None:
        fail("engine_import_spec_missing")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def assert_false_flags(payload: dict) -> None:
    flags = payload.get("safety_flags", {})
    for flag in [
        "SECRET_READ",
        "MEMBER_PLAINTEXT_READ",
        "RAW_AUDIO_SAVED",
        "ODOO_DB_WRITE",
        "POS_ORDER_CREATED",
        "PAYMENT_CAPTURE",
        "EXTERNAL_API_CALL",
    ]:
        if flags.get(flag) is not False:
            fail(f"safety_flag_not_false:{flag}")


def main() -> int:
    engine = load_engine()

    expected = {
        "LINE註冊": "member_register",
        "現金付款": "payment_candidate",
        "我要下單拿鐵": "order_candidate",
        "退這筆": "return_candidate",
        "改價": "manager_price_change",
        "請轉越文": "translate_assist",
        "櫃台提醒後台": "live_notice",
        "廠商費用預支": "cash_advance_ref",
        "客人回訪": "loyalty_return",
        "店員語音POS": "staff_voice_pos_operation",
        "招牌咖啡有什麼": "menu_lookup",
    }
    for text, intent in expected.items():
        got = engine.detect_intent(text)
        if got != intent:
            fail(f"intent_mismatch:{text}:{got}:{intent}")

    for intent in engine.SUPPORTED_INTENTS:
        payload = engine.candidate_action("test", intent)
        if payload["intent"] != intent:
            fail(f"candidate_intent_mismatch:{intent}")
        if payload["runtime_ready"] is not False:
            fail(f"candidate_runtime_ready_not_false:{intent}")
        assert_false_flags(payload)

    order = engine.order_payload([
        {"product_ref": "49180031", "name": "招牌咖啡", "quantity": 2, "price": 120},
        {"product_ref": "49180038", "name": "檸檬汁", "quantity": 1, "price": 90},
    ])
    if order["amount"] != 330:
        fail(f"order_amount_wrong:{order['amount']}")
    if order["pos_order_created"] is not False or order["odoo_db_write"] is not False:
        fail("order_has_side_effect_flag")
    assert_false_flags(order)

    payment = engine.payment_payload(330, "cash")
    if payment["amount"] != 330 or payment["mode"] != "cash":
        fail("payment_payload_wrong")
    if payment["payment_capture"] is not False:
        fail("payment_capture_not_false")
    assert_false_flags(payment)

    receipt = engine.receipt_payload("ORDER-CANDIDATE-1")
    if receipt["receipt_created"] is not False:
        fail("receipt_created_not_false")
    if receipt["waiting_for_odoo_pos_order_id"] is not True:
        fail("receipt_not_waiting_for_order_id")
    assert_false_flags(receipt)

    voice = engine.staff_voice_pos_payload("店員語音POS 我要下單招牌咖啡", "staff_ref_demo", "zh-Hant")
    if voice["intent"] != "staff_voice_pos_operation":
        fail("voice_pos_intent_wrong")
    if voice["raw_audio_saved"] is not False:
        fail("voice_raw_audio_saved_not_false")
    if voice["pos_order_created"] is not False or voice["payment_capture"] is not False:
        fail("voice_has_transaction_side_effect")
    if voice["candidate_action"]["confirm_state"] != "draft":
        fail("voice_candidate_not_draft")
    assert_false_flags(voice)

    grammar = engine.parse_staff_voice_order("大冰少糖拿鐵")
    if grammar["valid"] is not True:
        fail(f"grammar_valid_example_failed:{grammar}")
    slots = grammar["slots"]
    expected_slots = {
        "size": "large",
        "temperature": "ice",
        "sweetness": "less_sugar",
        "item": "拿鐵",
    }
    if slots["size"]["value"] != expected_slots["size"]:
        fail("grammar_size_wrong")
    if slots["temperature"]["value"] != expected_slots["temperature"]:
        fail("grammar_temperature_wrong")
    if slots["sweetness"]["value"] != expected_slots["sweetness"]:
        fail("grammar_sweetness_wrong")
    if slots["item"]["text"] != expected_slots["item"]:
        fail("grammar_item_wrong")

    grammar_payload = engine.staff_voice_pos_payload("大冰少糖拿鐵", "staff_ref_demo", "zh-Hant")
    if grammar_payload["voice_pos_grammar"]["valid"] is not True:
        fail("grammar_payload_not_valid")
    if grammar_payload["candidate_action"]["grammar_valid"] is not True:
        fail("grammar_candidate_not_valid")
    assert_false_flags(grammar_payload)

    invalid = engine.parse_staff_voice_order("拿鐵大冰少糖")
    if invalid["valid"] is not False:
        fail("grammar_invalid_order_passed")
    if "out_of_order_requires_repeat_confirmation" not in invalid["errors"]:
        fail("grammar_invalid_missing_repeat_confirmation_error")
    if invalid["repeat_confirmation_required"] is not True:
        fail("grammar_invalid_repeat_confirmation_not_required")
    if invalid["repeat_confirmation"]["canonical_transcript"] != "大冰少糖拿鐵":
        fail("grammar_invalid_repeat_confirmation_wrong")
    inferred = invalid["inferred_slots"]
    if inferred["size"]["value"] != "large":
        fail("grammar_invalid_inferred_size_wrong")
    if inferred["temperature"]["value"] != "ice":
        fail("grammar_invalid_inferred_temperature_wrong")
    if inferred["sweetness"]["value"] != "less_sugar":
        fail("grammar_invalid_inferred_sweetness_wrong")
    if inferred["item"]["text"] != "拿鐵":
        fail("grammar_invalid_inferred_item_wrong")

    invalid_payload = engine.staff_voice_pos_payload("拿鐵大冰少糖", "staff_ref_demo", "zh-Hant")
    invalid_candidate = invalid_payload["candidate_action"]
    if invalid_candidate["grammar_valid"] is not False:
        fail("invalid_payload_grammar_valid_not_false")
    if invalid_candidate["repeat_confirmation_required"] is not True:
        fail("invalid_payload_repeat_confirmation_not_required")
    if invalid_payload["pos_order_created"] is not False or invalid_payload["payment_capture"] is not False:
        fail("invalid_payload_has_transaction_side_effect")
    assert_false_flags(invalid_payload)

    print("STATE=PASS_XIAOJ_P1_INTENT_ENGINE_READY")
    print("ACTION=VERIFY_XIAOJ_P1_INTENT_ENGINE")
    print(f"ENGINE={ENGINE.relative_to(ROOT)}")
    print("SUPPORTED_INTENTS=" + str(len(engine.SUPPORTED_INTENTS)))
    print("ORDER_AMOUNT_TEST=330")
    print("STAFF_VOICE_POS_OPERATION=TRUE")
    print("VOICE_POS_GRAMMAR=size_temperature_sweetness_item")
    print("VOICE_POS_EXAMPLE=大冰少糖拿鐵")
    print("VOICE_POS_REVERSE_EXAMPLE=拿鐵大冰少糖")
    print("VOICE_POS_REVERSE_REPEAT_CONFIRMATION=TRUE")
    print("RUNTIME_READY=FALSE")
    print("ODOO_DB_WRITE=FALSE")
    print("POS_ORDER_CREATED=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    print("RAW_AUDIO_SAVED=FALSE")
    print("EXTERNAL_API_CALL=FALSE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
