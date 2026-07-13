#!/usr/bin/env python3
"""Verify the Google member login remediation using repository source only."""

from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GOOGLE = ROOT / "Taiji_Odoo/addons/wuchang_google_member_login"
GOOGLE_CONTROLLER = GOOGLE / "controllers/main.py"
GOOGLE_MANIFEST = GOOGLE / "__manifest__.py"
GATEWAY_CONTROLLER = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/controllers/main.py"
MEMBER_CONTROLLER = ROOT / "Taiji_Odoo/addons/wuchang_member_registration/controllers/main.py"
MEMBER_LOGIN_TEMPLATE = ROOT / "Taiji_Odoo/addons/wuchang_member_registration/views/login_templates.xml"


def read(path: Path) -> str:
    if not path.is_file():
        raise AssertionError(f"missing:{path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def verify() -> list[str]:
    failures: list[str] = []
    google = read(GOOGLE_CONTROLLER)
    gateway = read(GATEWAY_CONTROLLER)
    member = read(MEMBER_CONTROLLER)
    login_template = read(MEMBER_LOGIN_TEMPLATE)

    for path, source in ((GOOGLE_CONTROLLER, google), (GATEWAY_CONTROLLER, gateway)):
        try:
            ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            failures.append(f"syntax:{path.relative_to(ROOT)}:{exc}")

    manifest = ast.literal_eval(read(GOOGLE_MANIFEST))
    if "auth_oauth" not in manifest.get("depends", []):
        failures.append("manifest:auth_oauth_dependency_missing")

    combined = google + "\n" + gateway
    for route in ("/google/member/login", "/google/member/callback", "/google/member/welcome"):
        if combined.count(f'@http.route("{route}"') != 1:
            failures.append(f"route:not_unique:{route}")

    required_google = (
        'request.env.ref("auth_oauth.provider_google", raise_if_not_found=False)',
        "provider.enabled",
        "provider.client_id",
        "provider.auth_endpoint",
        "provider.scope",
        "provider.data_endpoint or provider.validation_endpoint",
        'self._param("web.base.url")',
        'self._param("wuchang_google_member_login.client_secret")',
        '"/google/member/callback"',
    )
    for marker in required_google:
        if marker not in google:
            failures.append(f"google_controller:missing:{marker}")

    if 'self._param("wuchang_google_member_login.client_id")' in google:
        failures.append("google_controller:duplicate_client_id_parameter")

    for route in (
        "/wuchang/google/member/recruitment",
        "/wuchang/google/member/recruitment/welcome",
    ):
        if route not in gateway:
            failures.append(f"gateway:preview_route_missing:{route}")

    if "/google/member/login" not in member or 'href="/google/member/login"' not in login_template:
        failures.append("member_flow:google_login_entry_missing")

    forbidden_literals = ("client_secret = \"", "client_secret = '", "access_token = \"", "access_token = '")
    for marker in forbidden_literals:
        if marker in combined:
            failures.append(f"credential_literal:{marker}")

    return failures


def main() -> int:
    failures = verify()
    if failures:
        for failure in failures:
            print(f"VERIFY_FAIL={failure}")
        return 1
    print("STATE=PASS_GOOGLE_MEMBER_LOGIN_EXACT_REMEDIATION")
    print("SOURCE_ONLY=TRUE")
    print("EXISTING_PROVIDER_REUSED=TRUE")
    print("ROUTE_SHADOW_REMOVED=TRUE")
    print("DB_WRITE=FALSE")
    print("SECRET_OUTPUT=FALSE")
    print("SERVICE_RESTART=FALSE")
    print("DEPLOY=FALSE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
