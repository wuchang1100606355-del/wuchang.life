#!/usr/bin/env python3
"""Focused source verifier for member OAuth pre-activation remediations."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GOOGLE_MODEL = ROOT / "Taiji_Odoo/addons/wuchang_google_member_login/models/res_partner.py"
GOOGLE_CONTROLLER = ROOT / "Taiji_Odoo/addons/wuchang_google_member_login/controllers/main.py"
GOOGLE_SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_google_member_login/services/account_linking.py"
LINE_MODEL = ROOT / "Taiji_Odoo/addons/wuchang_line_login/models/line_user.py"
LINE_CONTROLLER = ROOT / "Taiji_Odoo/addons/wuchang_line_login/controllers/main.py"
LINE_SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_line_login/services/profile_minimization.py"
AUTHORITY = ROOT / "Taiji_Odoo/addons/wuchang_member_registration/models/member_registration.py"
GATEWAY = ROOT / "deploy/packages/taiji01_metric_identity_gateway_v0_1/taiji01_metric_identity_gateway.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"import_failed:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def require(text: str, markers: tuple[str, ...], name: str, failures: list[str]) -> None:
    for marker in markers:
        if marker not in text:
            failures.append(f"{name}:missing:{marker}")


def verify() -> list[str]:
    failures: list[str] = []
    google_model = GOOGLE_MODEL.read_text(encoding="utf-8")
    google_controller = GOOGLE_CONTROLLER.read_text(encoding="utf-8")
    line_model = LINE_MODEL.read_text(encoding="utf-8")
    line_controller = LINE_CONTROLLER.read_text(encoding="utf-8")
    authority = AUTHORITY.read_text(encoding="utf-8")
    gateway_source = GATEWAY.read_text(encoding="utf-8")
    google = load(GOOGLE_SERVICE, "verify_google_linking")
    line = load(LINE_SERVICE, "verify_line_minimization")
    gateway = load(GATEWAY, "verify_member_gateway")

    if 'self.search([("email", "=", email)]' in google_model:
        failures.append("google_same_email_auto_link_present")
    if "self.create(values)" in google_model or "partner.write(values)" in google_model:
        failures.append("google_callback_partner_mutation_present")
    require(
        google_controller,
        (
            'request.session["wuchang_google_oidc_nonce"]',
            "callback_security_decision",
            "resolve_provider_subject",
            "status=202",
            "https://wuchang.life/",
        ),
        "google_callback",
        failures,
    )
    if "groups_id" in google_controller or "has_group" in google_controller:
        failures.append("google_direct_role_grant_present")
    if google.google_link_state(provider_link_found=False) != "LINKING_PENDING":
        failures.append("google_pending_state_missing")

    require(
        authority,
        ("def resolve_provider_subject", '"LINK_DENIED"', '"PROVIDER_LINK_FOUND"'),
        "authority_resolver",
        failures,
    )
    for forbidden in (
        "request.env['wuchang.line.user']",
        "raw_profile",
        "picture_url",
        "display_name",
    ):
        if forbidden in line_controller:
            failures.append(f"line_controller_forbidden:{forbidden}")
    require(
        line_model,
        ("PERSISTENCE_DISABLED_MESSAGE", "raise UserError(PERSISTENCE_DISABLED_MESSAGE)"),
        "line_legacy_persistence",
        failures,
    )
    profile = {
        "userId": "SYNTHETIC-LINE-SUBJECT",
        "displayName": "Synthetic nickname",
        "pictureUrl": "https://example.test/synthetic.png",
    }
    record = line.minimized_link_record(
        profile,
        {"link_state": "LINKING_PENDING", "verifier_result": "HOLD"},
        "2026-07-15T19:01:00Z",
    )
    if set(record) != line.ALLOWED_LINK_FIELDS:
        failures.append("line_allowlist_mismatch")
    if any(value in str(record) for value in profile.values()):
        failures.append("line_raw_profile_leak")

    require(
        gateway_source,
        ("PROVIDER_LINK_DENY_STATES", "def member_api_public_response"),
        "gateway",
        failures,
    )
    if gateway.PROVIDER_LINK_DENY_STATES != line.DENY_LINK_STATES:
        failures.append("provider_link_deny_state_mismatch")

    secret_patterns = (
        re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
        re.compile(r"AIza[0-9A-Za-z_-]{16,}"),
        re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]{16,}"),
    )
    for path in (
        GOOGLE_MODEL,
        GOOGLE_CONTROLLER,
        GOOGLE_SERVICE,
        LINE_MODEL,
        LINE_CONTROLLER,
        LINE_SERVICE,
        AUTHORITY,
        GATEWAY,
    ):
        text = path.read_text(encoding="utf-8")
        if any(pattern.search(text) for pattern in secret_patterns):
            failures.append(f"secret_shape:{path.relative_to(ROOT)}")
    return failures


def main() -> int:
    failures = verify()
    if failures:
        print("STATE=HOLD_MEMBER_OAUTH_PRE_ACTIVATION_REMEDIATION_VERIFY")
        for failure in failures:
            print(f"FAILURE={failure}")
        return 1
    print("STATE=PASS_MEMBER_OAUTH_PRE_ACTIVATION_REMEDIATION_VERIFY")
    print("GOOGLE_LINKING=PASS")
    print("GOOGLE_CALLBACK=PASS")
    print("LINE_MINIMIZATION=PASS")
    print("API_DENY_CASES=PASS")
    print("NO_SECRET=PASS")
    print("NO_MEMBER_PLAINTEXT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
