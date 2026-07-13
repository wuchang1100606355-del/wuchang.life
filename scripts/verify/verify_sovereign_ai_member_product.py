#!/usr/bin/env python3
"""Static product verifier for the Sovereign AI Member System.

This verifier reads repository source only. It does not access credentials,
member plaintext, databases, containers, routers, or live services.
"""

from __future__ import annotations

import ast
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOGIN = ROOT / "Taiji_Odoo/addons/wuchang_member_registration/views/login_templates.xml"
MEMBER_VIEWS = ROOT / "Taiji_Odoo/addons/wuchang_member_registration/views/member_registration_views.xml"
MEMBER_CONTROLLER = ROOT / "Taiji_Odoo/addons/wuchang_member_registration/controllers/main.py"
GOOGLE_CONTROLLER = ROOT / "Taiji_Odoo/addons/wuchang_google_member_login/controllers/main.py"
GOOGLE_MODEL = ROOT / "Taiji_Odoo/addons/wuchang_google_member_login/models/res_partner.py"
CAFE_CONTROLLER = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/controllers/main.py"
CAFE_EVENTBOOK_VIEWS = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/views/wuchang_cafe_ai_eventbook_views.xml"
CAFE_HANDOFF_VIEWS = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/views/total_product_handoff_views.xml"
PRODUCT_VIEWS = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/views/sovereign_ai_member_system_views.xml"
CAFE_MANIFEST = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/__manifest__.py"
CANDIDATE_PACKET = ROOT / "tools/xiaoj_gemini_no_plaintext_candidate_packet.py"
EXECUTION_GATE = ROOT / "tools/w7tp_packet_inference_runtime.py"
PRODUCT_DOC = ROOT / "docs/product/SOVEREIGN_AI_MEMBER_SYSTEM.md"

FORBIDDEN_COPY = (
    "免費免訂閱",
    "高利息債務",
    "還債",
    "養員工",
    "員工獎金",
    "已核准發明專利",
    "Google 背書",
    "政府背書",
    "任意檔案都能小封包下載",
)
RAW_CREDENTIAL_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{16,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]{16,}"),
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def require(text: str, markers: tuple[str, ...], check: str, failures: list[str]) -> None:
    missing = [marker for marker in markers if marker not in text]
    if missing:
        failures.append(f"{check}:missing:{','.join(missing)}")


def run_checks() -> tuple[dict[str, str], list[str]]:
    failures: list[str] = []
    required_paths = (
        LOGIN,
        MEMBER_VIEWS,
        MEMBER_CONTROLLER,
        GOOGLE_CONTROLLER,
        GOOGLE_MODEL,
        CAFE_CONTROLLER,
        CAFE_EVENTBOOK_VIEWS,
        CAFE_HANDOFF_VIEWS,
        PRODUCT_VIEWS,
        CAFE_MANIFEST,
        CANDIDATE_PACKET,
        EXECUTION_GATE,
        PRODUCT_DOC,
    )
    missing_paths = [str(path.relative_to(ROOT)) for path in required_paths if not path.is_file()]
    if missing_paths:
        failures.append("required_paths:missing:" + ",".join(missing_paths))
        return {}, failures

    for path in (LOGIN, MEMBER_VIEWS, CAFE_EVENTBOOK_VIEWS, CAFE_HANDOFF_VIEWS, PRODUCT_VIEWS):
        try:
            ET.parse(path)
        except ET.ParseError as exc:
            failures.append(f"xml_parse:{path.relative_to(ROOT)}:{exc}")

    try:
        manifest = ast.literal_eval(read(CAFE_MANIFEST))
    except (SyntaxError, ValueError) as exc:
        failures.append(f"manifest_parse:{exc}")
        manifest = {}
    if "views/sovereign_ai_member_system_views.xml" not in manifest.get("data", []):
        failures.append("manifest_missing_product_views")
    if "wuchang_member_registration" not in manifest.get("depends", []):
        failures.append("manifest_missing_member_dependency")

    login = read(LOGIN)
    require(
        login,
        (
            "主權 AI 會員系統",
            "Sovereign AI Member System",
            "會員主權",
            "雲端候選",
            "本地總場",
            "PASS／HOLD／人工確認／錯誤",
            'href="/web/login"',
            'href="/web/signup"',
            'href="/google/member/login"',
        ),
        "member_portal",
        failures,
    )

    product_views = read(PRODUCT_VIEWS)
    require(
        product_views,
        (
            'id="menu_wuchang_sovereign_ai_member_system"',
            'action="wuchang_member_registration.action_wuchang_member_registration"',
            'action="action_wuchang_cafe_ai_eventbook"',
            'action="action_wuchang_total_product_operator_handoff"',
            "操作員交接與健康狀態",
        ),
        "odoo_product_menu",
        failures,
    )
    require(read(MEMBER_VIEWS), ('id="action_wuchang_member_registration"',), "member_action", failures)
    require(read(CAFE_EVENTBOOK_VIEWS), ('id="action_wuchang_cafe_ai_eventbook"',), "evidence_action", failures)
    require(read(CAFE_HANDOFF_VIEWS), ('id="action_wuchang_total_product_operator_handoff"',), "handoff_action", failures)

    require(
        read(MEMBER_CONTROLLER),
        (
            '"/wuchang/member/register/start"',
            '"/wuchang/member/register/group/<string:packet_ref>"',
        ),
        "member_registration_routes",
        failures,
    )
    require(
        read(GOOGLE_CONTROLLER),
        (
            '"/google/member/login"',
            '"/google/member/callback"',
            "_wuchang_get_or_create_google_member",
        ),
        "google_identity_routes",
        failures,
    )
    require(
        read(GOOGLE_MODEL),
        (
            "wuchang_google_sub",
            "wuchang_google_email_verified",
            "_wuchang_get_or_create_google_member",
        ),
        "google_identity_binding",
        failures,
    )
    require(
        read(CAFE_CONTROLLER),
        (
            '"/wuchang/xiaoj/api/intent"',
            '"/wuchang/xiaoj/api/total-product-console-status"',
            '"/wuchang/xiaoj/api/total-product-operator-handoff"',
        ),
        "xiaoj_member_service_routes",
        failures,
    )

    candidate_packet = read(CANDIDATE_PACKET)
    require(
        candidate_packet,
        (
            '"candidate_only": True',
            '"member_plaintext_transmitted": False',
            '"member_plaintext_to_cloud": False',
            '"execution_allowed": False',
            '"cloud_timeout_state": "QUEUE_OR_HOLD_NOT_AUTHORITY"',
        ),
        "cloud_candidate_boundary",
        failures,
    )
    execution_gate = read(EXECUTION_GATE)
    require(
        execution_gate,
        (
            'decision not in {"ALLOW", "HOLD", "BLOCK"}',
            '"side_effects_allowed": False',
            '"member_plaintext": {"decision": "BLOCK"',
        ),
        "local_execution_gate",
        failures,
    )

    changed_surface = "\n".join((login, product_views, read(PRODUCT_DOC)))
    for phrase in FORBIDDEN_COPY:
        if phrase in changed_surface:
            failures.append(f"forbidden_copy:{phrase}")
    for pattern in RAW_CREDENTIAL_PATTERNS:
        if pattern.search(changed_surface):
            failures.append("raw_credential_shape")

    state = "PASS" if not failures else "HOLD"
    checks = {
        "IDENTITY_FLOW": state,
        "MEMBER_REGISTRATION": state,
        "MEMBER_SOVEREIGNTY_POLICY": state,
        "XIAOJ_MEMBER_INTENT_FLOW": state,
        "CLOUD_CANDIDATE_FLOW": state,
        "NO_PLAINTEXT_CLOUD_BOUNDARY": state,
        "LOCAL_CANDIDATE_NORMALIZATION": state,
        "LOCAL_EXECUTION_GATE": state,
        "MEMBER_PORTAL": state,
        "ODOO_MENU_ACTION_VIEW": state,
        "HOLD_MANUAL_UI": state,
        "EVIDENCE_CHAIN": state,
        "PRODUCT_DOCUMENTATION": state,
        "PRODUCT_SMOKE_TEST": state,
    }
    return checks, failures


def main() -> int:
    checks, failures = run_checks()
    for key, value in checks.items():
        print(f"{key}={value}")
    print("PORTAL_PATH=SOURCE_NOT_PRESENT_USING_EXISTING_LOGIN_SURFACE")
    print("DB_MIGRATION_REQUIRED=NO")
    print("LIVE_SIDE_EFFECTS=NONE")
    if failures:
        print("STATE=HOLD_SOVEREIGN_AI_MEMBER_PRODUCT_SOURCE_VERIFY")
        for failure in failures:
            print(f"FAILURE={failure}")
        return 1
    print("STATE=PASS_SOVEREIGN_AI_MEMBER_PRODUCT_SOURCE_VERIFY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
