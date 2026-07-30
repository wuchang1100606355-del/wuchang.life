from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "Taiji_Odoo/addons/wuchang_google_member_login/services/oauth_config.py"
TOOL_PATH = ROOT / "tools/odoo/configure_google_member_provider.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_callback_builder_and_health_contract() -> None:
    contract = load(CONTRACT_PATH, "google_member_oauth_contract")
    callback = contract.build_callback_uri(
        configured_base_url="https://members.example.test/"
    )
    assert callback == "https://members.example.test/google/member/callback"
    assert contract.public_base_url_state("https://members.example.test") == "PRESENT"
    assert contract.callback_uri_state(callback) == "PRESENT"
    assert contract.login_health_state(True, True, True, True, "https://members.example.test", callback) == "PASS"
    assert contract.build_callback_uri(
        explicit_redirect_uri="https://identity.example.test/google/member/callback"
    ) == "https://identity.example.test/google/member/callback"
    assert contract.callback_uri_state("http://127.0.0.1:8069/google/member/callback") == "INVALID_REF"


def test_google_endpoint_allowlist_never_returns_untrusted_origin() -> None:
    contract = load(CONTRACT_PATH, "google_member_oauth_endpoint_contract")
    assert contract.trusted_google_authorization_url(
        "https://accounts.google.com/o/oauth2/auth"
    ) == "https://accounts.google.com/o/oauth2/auth"
    assert contract.trusted_google_authorization_url(
        "/o/oauth2/auth"
    ) == contract.GOOGLE_AUTHORIZATION_URL
    assert contract.trusted_google_authorization_url(
        "https://example.test/o/oauth2/auth"
    ) == contract.GOOGLE_AUTHORIZATION_URL
    assert contract.trusted_google_userinfo_url(
        "https://example.test/userinfo",
        "https://www.googleapis.com/oauth2/v2/userinfo",
    ) == "https://www.googleapis.com/oauth2/v2/userinfo"
    assert contract.trusted_google_userinfo_url(
        "http://127.0.0.1/userinfo"
    ) == contract.GOOGLE_USERINFO_URL


def test_google_controller_explicitly_allows_only_trusted_external_redirect() -> None:
    source = (
        ROOT
        / "Taiji_Odoo/addons/wuchang_google_member_login/controllers/main.py"
    ).read_text(encoding="utf-8")
    assert "trusted_google_authorization_url(provider.auth_endpoint)" in source
    assert "local=False" in source
    assert "trusted_google_userinfo_url(" in source


def test_provider_tool_uses_odoo_config_and_stdin_without_plaintext_secret() -> None:
    tool = load(TOOL_PATH, "configure_google_member_provider")
    command = tool.docker_command("wuchang_os_odoo_18", "/etc/odoo/odoo.conf", "odoo")
    assert command[:4] == ["docker", "exec", "-i", "wuchang_os_odoo_18"]
    assert command[4:6] == ["/entrypoint.sh", "odoo"]
    assert "-c" in command and "/etc/odoo/odoo.conf" in command
    synthetic_secret = "".join(("synthetic", "-value"))
    program = tool.build_odoo_shell_program(
        "apply",
        {
            "client_id": "synthetic-client-id",
            "client_secret": synthetic_secret,
            "public_base_url": "https://members.example.test",
            "callback_uri": "https://members.example.test/google/member/callback",
        },
    )
    assert synthetic_secret not in program
    assert "psql" not in program
    assert "/tmp" not in program
    assert 'env.ref("auth_oauth.provider_google"' in program
    assert "PRESENT_TRUSTED_GOOGLE_HTTPS" in program
    assert "stat.S_IMODE(file_status.st_mode) != 0o600" in program
    assert "configured_path).read" not in program
    assert "env.cr.commit()" in program
    assert "env.cr.rollback()" in program
    discovery = tool.build_database_discovery_program()
    assert "psycopg2.connect" in discovery
    assert "ir_module_module" in discovery
    assert "psql" not in discovery
    assert "/tmp" not in discovery


def test_provider_check_uses_runtime_secret_file_metadata_and_trusted_origins() -> None:
    tool = load(TOOL_PATH, "configure_google_member_provider_runtime_health")
    program = tool.build_odoo_shell_program("check")
    assert tool.CANONICAL_CALLBACK_URL == (
        "https://member.wuchang.life/google/member/callback"
    )
    assert tool.GOOGLE_CLIENT_SECRET_FILE in program
    assert tool.CANONICAL_CALLBACK_URL in program
    assert "callback_present," in program
    assert "public_base_present," in program
    assert '"accounts.google.com"' in program
    assert '"www.googleapis.com"' in program
    assert 'params.get_param("wuchang_google_member_login.client_secret")' not in program


def test_provider_tool_rejects_non_public_callback_origin() -> None:
    tool = load(TOOL_PATH, "configure_google_member_provider_validation")
    with pytest.raises(ValueError):
        tool.validate_public_base_url("http://127.0.0.1:8069")
    with pytest.raises(ValueError):
        tool.validate_public_base_url("https://localhost")
    assert tool.callback_uri("https://members.example.test") == (
        "https://members.example.test/google/member/callback"
    )
