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


def test_public_member_entry_is_simple_and_role_neutral() -> None:
    login = LOGIN_PATH.read_text(encoding="utf-8")
    assert "小J會員服務" in login
    assert "不用先選會員、店員、店長或管理員身分" in login
    assert "登入後不需要再選角色" in login
    assert 'href="/web/signup"' in login
    assert 'href="/wuchang/business/onboarding"' in login
    assert "店員 / 店長登入" not in login
    assert "進入店務系統" not in login
    assert "Google／LINE 僅供登入後的 verified channel 綁定" not in login
    assert 'href="/forum"' not in login
    assert 'href="/google/member/login"' not in login
    assert 'href="/line/login"' not in login
