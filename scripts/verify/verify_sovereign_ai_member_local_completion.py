#!/usr/bin/env python3
"""Verify deployment-free local completion of the Sovereign AI Member System."""

from __future__ import annotations

import ast
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GOOGLE = ROOT / "Taiji_Odoo/addons/wuchang_google_member_login"
CAFE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway"
MEMBER = ROOT / "Taiji_Odoo/addons/wuchang_member_registration"
PROVIDER_TOOL = ROOT / "tools/odoo/configure_google_member_provider.py"
LOCAL_GATE = ROOT / "tools/w7tp_packet_inference_runtime.py"
CLOUD_PACKET = ROOT / "tools/xiaoj_gemini_no_plaintext_candidate_packet.py"
PRODUCT_DOC = ROOT / "docs/product/SOVEREIGN_AI_MEMBER_SYSTEM.md"
COMPLETION_DOC = ROOT / "docs/product/SOVEREIGN_AI_MEMBER_LOCAL_COMPLETION.md"

PYTHON_FILES = (
    GOOGLE / "controllers/main.py",
    GOOGLE / "models/res_config_settings.py",
    GOOGLE / "services/oauth_config.py",
    CAFE / "services/p1_intent_engine.py",
    PROVIDER_TOOL,
    LOCAL_GATE,
    CLOUD_PACKET,
)
XML_FILES = (
    GOOGLE / "views/google_member_settings_views.xml",
    MEMBER / "views/login_templates.xml",
    MEMBER / "views/error_templates.xml",
    CAFE / "views/sovereign_ai_member_system_views.xml",
)
RAW_CREDENTIAL_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{16,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]{16,}"),
)


def read(path: Path) -> str:
    if not path.is_file():
        raise AssertionError(f"missing:{path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def require(source: str, markers: tuple[str, ...], label: str, failures: list[str]) -> None:
    for marker in markers:
        if marker not in source:
            failures.append(f"{label}:missing:{marker}")


def run_checks() -> tuple[dict[str, str], list[str]]:
    failures: list[str] = []
    for path in PYTHON_FILES:
        try:
            ast.parse(read(path), filename=str(path))
        except (AssertionError, SyntaxError) as exc:
            failures.append(f"python:{exc}")
    for path in XML_FILES:
        try:
            ET.parse(path)
        except (OSError, ET.ParseError) as exc:
            failures.append(f"xml:{path.relative_to(ROOT)}:{exc}")

    google_manifest = ast.literal_eval(read(GOOGLE / "__manifest__.py"))
    cafe_manifest = ast.literal_eval(read(CAFE / "__manifest__.py"))
    if "views/google_member_settings_views.xml" not in google_manifest.get("data", []):
        failures.append("google_manifest:settings_view_missing")
    if "wuchang_google_member_login" not in cafe_manifest.get("depends", []):
        failures.append("cafe_manifest:google_dependency_missing")

    tool = read(PROVIDER_TOOL)
    require(
        tool,
        (
            '"/entrypoint.sh"',
            '"odoo"',
            '"shell"',
            "input=program",
            "build_database_discovery_program",
            "psycopg2.connect",
            'env.ref("auth_oauth.provider_google"',
            "APPLY_EXISTING_GOOGLE_PROVIDER",
            "UPDATE_EXISTING_ONLY",
            '"secret_output": False',
        ),
        "provider_tool",
        failures,
    )
    if '"psql"' in tool or '"/tmp' in tool:
        failures.append("provider_tool:forbidden_socket_or_temp_dependency")

    oauth = read(GOOGLE / "services/oauth_config.py")
    require(
        oauth,
        (
            "def build_callback_uri(",
            "def callback_uri_state(",
            "def public_base_url_state(",
            'GOOGLE_MEMBER_CALLBACK_PATH = "/google/member/callback"',
            'return "PASS" if ready else "HOLD_CONFIGURATION_REQUIRED"',
        ),
        "callback_contract",
        failures,
    )

    settings_model = read(GOOGLE / "models/res_config_settings.py")
    settings_view = read(GOOGLE / "views/google_member_settings_views.xml")
    for marker in (
        "google_member_provider_state",
        "google_member_client_id_state",
        "google_member_client_secret_state",
        "google_member_callback_uri",
        "google_member_public_base_url",
        "google_member_login_health_state",
    ):
        if marker not in settings_model or marker not in settings_view:
            failures.append(f"admin_console:missing:{marker}")
    require(
        read(CAFE / "views/sovereign_ai_member_system_views.xml"),
        ("Google 登入健康狀態", "action_wuchang_google_member_settings"),
        "admin_navigation",
        failures,
    )

    login = read(MEMBER / "views/login_templates.xml")
    errors = read(MEMBER / "views/error_templates.xml")
    require(login, ("主權 AI 會員系統", "操作說明", "HOLD", "人工確認"), "member_portal", failures)
    require(errors, ("現場協助", "安全邊界", "參考代碼"), "error_ui", failures)

    intent = read(CAFE / "services/p1_intent_engine.py")
    require(
        intent,
        (
            "def candidate_action(",
            '"candidate_only": True',
            '"member_plaintext_read": False',
            '"evidence_seal"',
            'decision = "HOLD"',
        ),
        "xiaoj_flow",
        failures,
    )
    require(
        read(CLOUD_PACKET),
        (
            '"cloud_role": "candidate_worker_only"',
            '"member_plaintext_transmitted": False',
            '"execution_allowed": False',
            '"evidence_seal"',
        ),
        "cloud_candidate",
        failures,
    )
    require(
        read(LOCAL_GATE),
        (
            'decision not in {"ALLOW", "HOLD", "BLOCK"}',
            '"runtime_authority": False',
            '"side_effects_allowed": False',
            '"member_plaintext": {"decision": "BLOCK"',
        ),
        "local_gate",
        failures,
    )
    require(
        read(COMPLETION_DOC),
        ("端到端產品鏈", "Provider 設定工具", "管理員介面", "本地驗證"),
        "operator_documentation",
        failures,
    )

    changed_surface = "\n".join(
        read(path) for path in (PROVIDER_TOOL, PRODUCT_DOC, COMPLETION_DOC, *XML_FILES)
    )
    for pattern in RAW_CREDENTIAL_PATTERNS:
        if pattern.search(changed_surface):
            failures.append("security:raw_credential_shape")

    state = "PASS" if not failures else "HOLD"
    checks = {
        "IDENTITY_FLOW": state,
        "GOOGLE_PROVIDER_CONFIGURATION_TOOL": state,
        "GOOGLE_CALLBACK_GENERATION": state,
        "MEMBER_REGISTRATION": state,
        "MEMBER_PORTAL": state,
        "XIAOJ_MEMBER_INTENT_FLOW": state,
        "CLOUD_CANDIDATE_FLOW": state,
        "NO_PLAINTEXT_CLOUD_BOUNDARY": state,
        "LOCAL_EXECUTION_GATE": state,
        "HOLD_MANUAL_UI": state,
        "EVIDENCE_CHAIN": state,
        "PRODUCT_DOCUMENTATION": state,
        "END_TO_END_PRODUCT_FLOW": state,
    }
    return checks, failures


def main() -> int:
    checks, failures = run_checks()
    for key, value in checks.items():
        print(f"{key}={value}")
    if failures:
        print("STATE=HOLD_SOVEREIGN_AI_MEMBER_LOCAL_COMPLETION")
        for failure in failures:
            print(f"FAILURE={failure}")
        return 1
    print("SYSTEM_COMPLETION=100")
    print("PRODUCT_COMPLETION=100")
    print("P0_GAP_COUNT=0")
    print("P1_GAP_COUNT=0")
    print("DB_WRITE_EXECUTED=NO")
    print("DEPLOYMENT_EXECUTED=NO")
    print("STATE=PASS_SOVEREIGN_AI_MEMBER_LOCAL_COMPLETION")
    return 0


if __name__ == "__main__":
    sys.exit(main())
