#!/usr/bin/env python3
"""Verify XiaoJ P1 local voice-order rehearsal.

This verifier executes only the local rehearsal command. It does not read
secrets, write Odoo DB, create POS orders, capture payments, save raw audio,
restart services, deploy, generate embeddings, or call external APIs.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "tools/xiaoj_p1_local_rehearsal.py"


def fail(message: str) -> None:
    print(f"VERIFY_FAIL={message}")
    raise SystemExit(1)


def run_harness(transcript: str) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, str(HARNESS), "--transcript", transcript, "--staff-ref", "staff_ref_demo"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        fail(f"harness_failed:{proc.stderr.strip()}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        fail(f"harness_json_invalid:{exc}")


def assert_false(value: Any, label: str) -> None:
    if value is not False:
        fail(f"expected_false:{label}")


def assert_safety(packet: dict[str, Any]) -> None:
    flags = packet.get("safety_flags", {})
    for flag in [
        "SECRET_READ",
        "MEMBER_PLAINTEXT_READ",
        "RAW_AUDIO_SAVED",
        "PRODUCTION_DB_WRITE",
        "ODOO_DB_WRITE",
        "ODOO_MODULE_UPGRADE",
        "POS_ORDER_CREATED",
        "PAYMENT_CAPTURE",
        "SERVICE_RESTART",
        "DEPLOY",
        "PRODUCTION_RELEASE",
        "EXTERNAL_API_CALL",
        "EMBEDDING_GENERATED",
    ]:
        assert_false(flags.get(flag), flag)


def main() -> int:
    if not HARNESS.exists():
        fail("harness_missing")

    packet = run_harness("大冰少糖拿鐵")
    if packet.get("state") != "P1_LOCAL_VOICE_ORDER_REHEARSAL_READY_RUNTIME_HOLD":
        fail("state_wrong")
    if packet.get("training_decision") != "HOLD_LIVE_ORDER_UNTIL_MENU_SOURCE_AND_RUNTIME_RELEASE":
        fail("training_decision_wrong")

    voice = packet["voice_payload"]
    grammar = voice["voice_pos_grammar"]
    if grammar["valid"] is not True:
        fail("voice_grammar_not_valid")
    slots = grammar["slots"]
    expected_slots = {
        "size": "large",
        "temperature": "ice",
        "sweetness": "less_sugar",
        "item": "拿鐵",
    }
    if slots["size"]["value"] != expected_slots["size"]:
        fail("size_parse_wrong")
    if slots["temperature"]["value"] != expected_slots["temperature"]:
        fail("temperature_parse_wrong")
    if slots["sweetness"]["value"] != expected_slots["sweetness"]:
        fail("sweetness_parse_wrong")
    if slots["item"]["text"] != expected_slots["item"]:
        fail("item_parse_wrong")

    menu_resolution = packet["menu_resolution"]
    if menu_resolution["menu_source_state"] != "HOLD_REAL_MENU_SOURCE_LOCK":
        fail("menu_source_gate_wrong")
    assert_false(menu_resolution["price_authority"], "price_authority")
    assert_false(menu_resolution["live_orderable"], "live_orderable")
    assert_false(menu_resolution["current_menu_authority"], "current_menu_authority")

    order = packet["order_candidate"]
    payment = packet["payment_candidate"]
    receipt = packet["receipt_candidate"]
    if order["state"] != "HOLD_RUNTIME_POS_ORDER_RELEASE_REQUIRED":
        fail("order_gate_wrong")
    if payment["state"] != "HOLD_RUNTIME_PAYMENT_RELEASE_REQUIRED":
        fail("payment_gate_wrong")
    if receipt["state"] != "HOLD_RUNTIME_POS_RECEIPT_REQUIRED":
        fail("receipt_gate_wrong")
    assert_false(order["pos_order_created"], "order.pos_order_created")
    assert_false(order["odoo_db_write"], "order.odoo_db_write")
    assert_false(payment["payment_capture"], "payment.payment_capture")
    assert_false(receipt["receipt_created"], "receipt.receipt_created")

    invalid = run_harness("拿鐵大冰少糖")
    invalid_grammar = invalid["voice_payload"]["voice_pos_grammar"]
    if invalid_grammar["valid"] is not False:
        fail("invalid_grammar_passed")
    if "out_of_order_requires_repeat_confirmation" not in invalid_grammar["errors"]:
        fail("invalid_grammar_missing_expected_error")
    if invalid_grammar["repeat_confirmation_required"] is not True:
        fail("invalid_grammar_repeat_confirmation_not_required")
    if invalid_grammar["repeat_confirmation"]["canonical_transcript"] != "大冰少糖拿鐵":
        fail("invalid_grammar_repeat_confirmation_wrong")
    invalid_menu = invalid["menu_resolution"]
    assert_false(invalid_menu["live_orderable"], "invalid_menu.live_orderable")
    assert_false(invalid["voice_payload"]["pos_order_created"], "invalid_voice.pos_order_created")
    assert_false(invalid["voice_payload"]["payment_capture"], "invalid_voice.payment_capture")

    assert_safety(packet)
    assert_safety(invalid)

    print("STATE=PASS_XIAOJ_P1_LOCAL_VOICE_ORDER_REHEARSAL_READY")
    print("ACTION=VERIFY_XIAOJ_P1_LOCAL_REHEARSAL")
    print(f"HARNESS={HARNESS.relative_to(ROOT)}")
    print("VOICE_POS_EXAMPLE=大冰少糖拿鐵")
    print("VOICE_PARSE=size:large,temperature:ice,sweetness:less_sugar,item:拿鐵")
    print("VOICE_POS_REVERSE_EXAMPLE=拿鐵大冰少糖")
    print("VOICE_POS_REVERSE_REPEAT_CONFIRMATION=TRUE")
    print("MENU_SOURCE_GATE=HOLD_REAL_MENU_SOURCE_LOCK")
    print("ORDER_GATE=HOLD_RUNTIME_POS_ORDER_RELEASE_REQUIRED")
    print("PAYMENT_GATE=HOLD_RUNTIME_PAYMENT_RELEASE_REQUIRED")
    print("RECEIPT_GATE=HOLD_RUNTIME_POS_RECEIPT_REQUIRED")
    print("REAL_POS_ORDER_CREATED=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    print("ODOO_DB_WRITE=FALSE")
    print("RAW_AUDIO_SAVED=FALSE")
    print("EXTERNAL_API_CALL=FALSE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
