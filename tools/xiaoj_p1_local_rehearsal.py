#!/usr/bin/env python3
"""Run a local XiaoJ P1 voice-order rehearsal.

This command is source-only. It imports the pure local intent engine, reads the
menu source-lock manifest, and emits a candidate packet. It does not import
Odoo, write DB rows, create POS orders, capture payments, save raw audio, call
external APIs, restart services, deploy, or read secrets.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/p1_intent_engine.py"
MENU_LOCK = ROOT / "runtime/total_field/xiaoj_p1_console/menu_source_lock.json"


def load_engine():
    spec = importlib.util.spec_from_file_location("p1_intent_engine", ENGINE)
    if spec is None or spec.loader is None:
        raise RuntimeError("p1_intent_engine import spec missing")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_menu_lock() -> dict[str, Any]:
    if not MENU_LOCK.exists():
        return {
            "state": "HOLD_REAL_MENU_SOURCE_LOCK",
            "authority": {
                "current_menu_authority": False,
                "can_create_pos_order_from_this_manifest": False,
                "can_capture_payment_from_this_manifest": False,
            },
            "candidate_rows": [],
        }
    return json.loads(MENU_LOCK.read_text(encoding="utf-8"))


def resolve_item(menu_lock: dict[str, Any], item_text: str) -> dict[str, Any]:
    candidates = menu_lock.get("candidate_rows", [])
    match = next((row for row in candidates if row.get("name_zh") == item_text), None)
    authority = menu_lock.get("authority", {})
    return {
        "item_text": item_text,
        "matched_candidate": match,
        "matched_candidate_found": match is not None,
        "menu_source_state": menu_lock.get("state", "HOLD_REAL_MENU_SOURCE_LOCK"),
        "current_menu_authority": authority.get("current_menu_authority") is True,
        "price_authority": False,
        "live_orderable": False,
        "can_create_pos_order_from_this_manifest": authority.get("can_create_pos_order_from_this_manifest") is True,
        "can_capture_payment_from_this_manifest": authority.get("can_capture_payment_from_this_manifest") is True,
    }


def rehearsal_packet(transcript: str, staff_ref: str, language: str, payment_mode: str) -> dict[str, Any]:
    engine = load_engine()
    menu_lock = load_menu_lock()
    voice = engine.staff_voice_pos_payload(transcript, staff_ref, language)
    grammar = voice["voice_pos_grammar"]
    item_text = grammar.get("slots", {}).get("item", {}).get("text") or ""
    menu_resolution = resolve_item(menu_lock, item_text)

    line_name = item_text or "UNRESOLVED_VOICE_ITEM"
    product_ref = "UNRESOLVED_MENU_ITEM"
    if menu_resolution["matched_candidate_found"]:
        product_ref = str(menu_resolution["matched_candidate"].get("id") or product_ref)

    order = engine.order_payload([
        {
            "product_ref": product_ref,
            "name": line_name,
            "quantity": 1,
            "price": 0,
        }
    ])
    payment = engine.payment_payload(order["amount"], payment_mode)
    receipt = engine.receipt_payload("LOCAL-REHEARSAL-NO-ODOO-ORDER")

    safety_flags = dict(engine.SAFETY_FLAGS)
    safety_flags.update(
        {
            "D8_LOCAL_DB_WRITE": False,
            "PRODUCTION_DB_WRITE": False,
            "ODOO_MODULE_UPGRADE": False,
            "PRODUCTION_RELEASE": False,
            "EMBEDDING_GENERATED": False,
        }
    )
    return {
        "state": "P1_LOCAL_VOICE_ORDER_REHEARSAL_READY_RUNTIME_HOLD",
        "action": "XIAOJ_P1_LOCAL_VOICE_ORDER_REHEARSAL",
        "root": str(ROOT),
        "transcript": transcript,
        "staff_ref": staff_ref,
        "language": language,
        "voice_payload": voice,
        "menu_resolution": menu_resolution,
        "order_candidate": order,
        "payment_candidate": payment,
        "receipt_candidate": receipt,
        "training_decision": "HOLD_LIVE_ORDER_UNTIL_MENU_SOURCE_AND_RUNTIME_RELEASE",
        "xiaoj_lines": [
            voice["xiaoj_line"],
            "我可以把店員語音整理成候選單，但真實 POS 要等菜單 source 與 runtime release。",
            "Neu chua khoa nguon menu, XiaoJ chi tao phieu nhap thu, khong ghi POS.",
            "If the menu source is not locked, this stays a rehearsal packet.",
        ],
        "runtime_holds": {
            "auth_route_gate": "HOLD_AUTH_ROUTE_GATE",
            "real_menu_source_gate": "HOLD_REAL_MENU_SOURCE_LOCK",
            "pos_order_gate": "HOLD_RUNTIME_POS_ORDER_RELEASE_REQUIRED",
            "payment_gate": "HOLD_RUNTIME_PAYMENT_RELEASE_REQUIRED",
        },
        "safety_flags": safety_flags,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a local XiaoJ P1 voice-order rehearsal.")
    parser.add_argument("--transcript", default="大冰少糖拿鐵")
    parser.add_argument("--staff-ref", default="staff_ref_demo")
    parser.add_argument("--language", default="zh-Hant")
    parser.add_argument("--payment-mode", default="cash")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    packet = rehearsal_packet(args.transcript, args.staff_ref, args.language, args.payment_mode)
    print(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
