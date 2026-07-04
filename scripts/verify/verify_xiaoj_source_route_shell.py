#!/usr/bin/env python3
"""Verify source-only XiaoJ auth/transaction route shells.

This verifier reads source files only. It does not import Odoo, read secrets,
inspect runtime env, write DB rows, create orders, capture payments, restart
services, or deploy.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ADDON = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway"
CONTROLLER_INIT = ADDON / "controllers/__init__.py"
MAIN = ADDON / "controllers/main.py"
ENGINE = ADDON / "services/p1_intent_engine.py"
ROOT_INIT = ADDON / "__init__.py"

REQUIRED_ROUTES = [
    "/line/login",
    "/line/callback",
    "/google/member/login",
    "/google/member/welcome",
    "/wuchang/internal/guard/google-member-login",
    "/wuchang/member/register/start",
    "/wuchang/xiaoj/ordering",
    "/wuchang/xiaoj/order",
    "/wuchang/xiaoj/payment",
    "/wuchang/xiaoj/receipt",
    "/wuchang/xiaoj/api/intent",
    "/wuchang/xiaoj/api/order",
    "/wuchang/xiaoj/api/payment",
    "/wuchang/xiaoj/api/receipt",
    "/wuchang/xiaoj/api/voice-pos",
]

REQUIRED_STATES = [
    "HOLD_AUTH_PROVIDER_CONFIG_REQUIRED",
    "HOLD_MEMBER_REGISTRATION_GATE",
    "P1_TRANSACTION_CAPABLE_SHELL",
    "HOLD_RUNTIME_POS_ORDER_RELEASE_REQUIRED",
    "HOLD_RUNTIME_PAYMENT_RELEASE_REQUIRED",
    "HOLD_RUNTIME_POS_RECEIPT_REQUIRED",
    "P1_MULTI_INTENT_API_SHELL",
    "P1_STAFF_VOICE_POS_API_SHELL",
    "BEFORE_OWNER_SEAL_COMMAND",
    "REPORT_ONLY",
    "STRICT_ENFORCEMENT",
]

FORBIDDEN_STRINGS = [
    "request.env[",
    ".sudo()",
    "create(",
    "write(",
    "unlink(",
    "requests.",
    "open(",
    ".env",
    "password",
    "token =",
    "os.environ",
    "config_parameter",
    "get_param",
    "payment_capture\": True",
    "pos_order_created\": True",
]


def fail(message: str) -> None:
    print(f"VERIFY_FAIL={message}")
    raise SystemExit(1)


def read(path: Path) -> str:
    if not path.exists():
        fail(f"missing:{path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def function_block(source: str, name: str, next_decorator: str) -> str:
    needle = f"def {name}"
    if needle not in source:
        fail(f"function_missing:{name}")
    start = source.index(needle)
    end = source.find(next_decorator, start)
    if end == -1:
        end = len(source)
    return source[start:end]


def main() -> int:
    root_init = read(ROOT_INIT)
    controller_init = read(CONTROLLER_INIT)
    source = read(MAIN)
    engine_source = read(ENGINE)
    combined_source = source + "\n" + engine_source

    if "from . import controllers" not in root_init:
        fail("root_init_missing_controllers_import")
    if "from . import main" not in controller_init:
        fail("controller_init_missing_main_import")

    try:
        ast.parse(source)
    except SyntaxError as exc:
        fail(f"syntax_error:{exc}")

    for route in REQUIRED_ROUTES:
        if route not in source:
            fail(f"route_missing:{route}")

    for state in REQUIRED_STATES:
        if state not in source:
            fail(f"state_missing:{state}")

    for forbidden in FORBIDDEN_STRINGS:
        if forbidden in combined_source:
            fail(f"forbidden_source_string:{forbidden}")

    if "Route payload" in source:
        fail("public_debug_route_payload_label_present")
    if "Internal guard payload" not in source:
        fail("internal_guard_payload_missing")
    if 'auth="user"' not in source or "/wuchang/internal/guard/google-member-login" not in source:
        fail("internal_guard_route_not_user_scoped")

    google_login_block = function_block(source, "google_member_login", '@http.route("/google/member/welcome"')
    for forbidden in [
        "_json_payload",
        "HOLD_AUTH_PROVIDER_CONFIG_REQUIRED",
        "safety_flags",
        "runtime_ready",
    ]:
        if forbidden in google_login_block:
            fail(f"google_member_login_public_payload_leak:{forbidden}")
    if "會員招募開放" not in google_login_block:
        fail("google_member_login_product_copy_missing:會員招募開放")
    for required in [
        "五常會員招募",
        "Google 登入準備",
        "report-only",
    ]:
        if required not in source:
            fail(f"google_member_login_product_copy_missing:{required}")

    for flag in [
        '"SECRET_READ": False',
        '"MEMBER_PLAINTEXT_READ": False',
        '"ODOO_DB_WRITE": False',
        '"POS_ORDER_CREATED": False',
        '"PAYMENT_CAPTURE": False',
        '"EXTERNAL_API_CALL": False',
        '"RAW_AUDIO_SAVED": False',
    ]:
        if flag not in combined_source:
            fail(f"safety_flag_missing:{flag}")

    for intent in [
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
    ]:
        if intent not in combined_source:
            fail(f"intent_missing:{intent}")

    print("STATE=PASS_XIAOJ_SOURCE_ROUTE_SHELL_READY")
    print("ACTION=VERIFY_XIAOJ_SOURCE_ROUTE_SHELL")
    print(f"ADDON={ADDON.relative_to(ROOT)}")
    print("SOURCE_ONLY=TRUE")
    print("RUNTIME_READY=FALSE")
    print("PRE_SEAL_REPORT_ONLY=TRUE")
    print("GOOGLE_MEMBER_LOGIN_PRODUCT_UX=TRUE")
    print("ODOO_DB_WRITE=FALSE")
    print("POS_ORDER_CREATED=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    print("SERVICE_RESTART=FALSE")
    print("DEPLOY=FALSE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
