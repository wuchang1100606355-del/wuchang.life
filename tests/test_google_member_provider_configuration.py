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
    assert "env.cr.commit()" in program
    assert "env.cr.rollback()" in program
    discovery = tool.build_database_discovery_program()
    assert "psycopg2.connect" in discovery
    assert "ir_module_module" in discovery
    assert "psql" not in discovery
    assert "/tmp" not in discovery


def test_provider_tool_rejects_non_public_callback_origin() -> None:
    tool = load(TOOL_PATH, "configure_google_member_provider_validation")
    with pytest.raises(ValueError):
        tool.validate_public_base_url("http://127.0.0.1:8069")
    with pytest.raises(ValueError):
        tool.validate_public_base_url("https://localhost")
    assert tool.callback_uri("https://members.example.test") == (
        "https://members.example.test/google/member/callback"
    )
