#!/usr/bin/env python3
"""Verify the static XiaoJ P1 operation console prototype.

The verifier only reads repo files. It does not read secrets, call external APIs,
inspect Docker env, write Odoo DB, create POS orders, capture payments, restart
services, deploy, or touch Odoo/LINE addon files.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONSOLE_DIR = ROOT / "runtime/total_field/xiaoj_p1_console"
FILES = {
    "html": CONSOLE_DIR / "index.html",
    "css": CONSOLE_DIR / "styles.css",
    "js": CONSOLE_DIR / "app.js",
    "manifest": CONSOLE_DIR / "manifest.json",
}

REQUIRED_MODULES = [
    "store_header",
    "auth_gate",
    "source_lock",
    "product_table",
    "category_selector",
    "menu_selector",
    "attribute_panel",
    "addon_panel",
    "batch_tools",
    "transaction_order_panel",
    "payment_panel",
    "staff_voice_pos_panel",
    "receipt_panel",
    "xiaoj_candidate_actions",
    "live_message_panel",
    "role_matrix",
    "stickiness_loop",
]

REQUIRED_INTENTS = [
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
]

REQUIRED_TEXT = [
    "LINE / Google",
    "HOLD_AUTH_ROUTE_GATE",
    "HOLD_REAL_MENU_SOURCE_LOCK",
    "HOLD_RUNTIME_PAYMENT_RELEASE_REQUIRED",
    "HOLD_RUNTIME_POS_ORDER_RELEASE_REQUIRED",
    "candidate-only",
    "Tiếng Việt",
    "可交易",
    "可付款",
    "可下單",
    "不寫 Odoo",
    "店員語音 POS",
    "大冰少糖拿鐵",
    "尺寸",
    "溫度",
    "甜度",
    "品項",
    "Staff speech becomes an order candidate",
    "Nhan vien doc dung thu tu",
    "parseStaffVoiceOrder",
]

FORBIDDEN_MENU_ITEMS = ["三明治", "蛋餅"]

SAFETY_FALSE_FLAGS = [
    "SECRET_READ",
    "MEMBER_PLAINTEXT_READ",
    "RAW_AUDIO_SAVED",
    "PRODUCTION_DB_WRITE",
    "ODOO_DB_WRITE",
    "ODOO_MODULE_UPGRADE",
    "POS_ORDER_CREATED",
    "PAYMENT_CAPTURE",
    "SERVICE_RESTART",
    "CONTAINER_MUTATION",
    "DEPLOY",
    "PRODUCTION_RELEASE",
    "EXTERNAL_API_CALL",
    "EMBEDDING_GENERATED",
    "ODOO_FILES_TOUCHED",
    "LINE_LOGIN_FILES_TOUCHED",
]


def fail(message: str) -> None:
    print(f"VERIFY_FAIL={message}")
    raise SystemExit(1)


def read(path: Path) -> str:
    if not path.exists():
        fail(f"missing:{path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def load_manifest() -> dict[str, Any]:
    try:
        return json.loads(read(FILES["manifest"]))
    except json.JSONDecodeError as exc:
        fail(f"manifest_json_invalid:{exc}")


def main() -> int:
    html = read(FILES["html"])
    css = read(FILES["css"])
    js = read(FILES["js"])
    manifest = load_manifest()
    combined = "\n".join([html, css, js, json.dumps(manifest, ensure_ascii=False)])

    for module in REQUIRED_MODULES:
        if module not in html or module not in manifest.get("required_ui_modules", []):
            fail(f"required_module_missing:{module}")

    for intent in REQUIRED_INTENTS:
        if intent not in js or intent not in manifest.get("required_intents", []):
            fail(f"required_intent_missing:{intent}")

    for text in REQUIRED_TEXT:
        if text not in combined:
            fail(f"required_text_missing:{text}")

    for item in FORBIDDEN_MENU_ITEMS:
        if item in combined:
            fail(f"forbidden_invented_item_present:{item}")

    safety = manifest.get("safety_flags", {})
    for flag in SAFETY_FALSE_FLAGS:
        if safety.get(flag) is not False:
            fail(f"safety_flag_not_false:{flag}")
    if safety.get("D8_LOCAL_DB_WRITE") is not True:
        fail("d8_local_db_write_not_true")

    if manifest.get("prototype", {}).get("claims_runtime_ready") is not False:
        fail("prototype_claims_runtime_ready")
    target = manifest.get("transaction_capability_target", {})
    for key in ["must_be_orderable", "must_be_payable", "must_be_tradeable", "runtime_release_required"]:
        if target.get(key) is not True:
            fail(f"transaction_target_not_true:{key}")
    if target.get("prototype_real_transaction") is not False:
        fail("prototype_real_transaction_not_false")

    print("STATE=PASS_XIAOJ_P1_CONSOLE_PROTOTYPE_READY")
    print("ACTION=VERIFY_XIAOJ_P1_CONSOLE_PROTOTYPE")
    print(f"ENTRYPOINT={FILES['html'].relative_to(ROOT)}")
    print("RUNTIME_READY=FALSE")
    print("TRANSACTION_CAPABLE_TARGET=TRUE")
    print("REAL_TRANSACTION_THIS_RUN=FALSE")
    print("AUTH_ROUTE_GATE=HOLD_AUTH_ROUTE_GATE")
    print("REAL_MENU_SOURCE_GATE=HOLD_REAL_MENU_SOURCE_LOCK")
    print("SECRET_READ=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")
    print("ODOO_DB_WRITE=FALSE")
    print("POS_ORDER_CREATED=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    print("SERVICE_RESTART=FALSE")
    print("DEPLOY=FALSE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
