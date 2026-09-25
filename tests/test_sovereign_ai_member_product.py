from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFY_PATH = ROOT / "scripts/verify/verify_sovereign_ai_member_product.py"
LOGIN_PATH = ROOT / "Taiji_Odoo/addons/wuchang_member_registration/views/login_templates.xml"


def load_verifier():
    spec = importlib.util.spec_from_file_location("verify_sovereign_ai_member_product", VERIFY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sovereign_ai_member_product_source_contract() -> None:
    checks, failures = load_verifier().run_checks()
    assert failures == []
    assert checks
    assert set(checks.values()) == {"PASS"}


def test_public_member_entry_keeps_external_channels_behind_local_login() -> None:
    login = LOGIN_PATH.read_text(encoding="utf-8")
    assert 'href="/web/login"' in login
    assert 'href="/web/signup"' in login
    assert 'href="/wuchang/business/onboarding"' in login
    assert 'href="/forum"' in login
    assert "Google／LINE 僅供登入後的 verified channel 綁定" in login
    assert 'href="/google/member/login"' not in login
    assert 'href="/line/login"' not in login
