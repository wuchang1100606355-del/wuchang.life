#!/usr/bin/env python3
"""Check or configure the existing Odoo Google member OAuth Provider safely."""

from __future__ import annotations

import argparse
import base64
import configparser
import ipaddress
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HOST_CONFIG = ROOT / "Taiji_Odoo/config/odoo.conf"
DEFAULT_CONTAINER = "wuchang_os_odoo_18"
DEFAULT_CONTAINER_CONFIG = "/etc/odoo/odoo.conf"
CALLBACK_PATH = "/google/member/callback"
GOOGLE_CLIENT_SECRET_FILE_ENV = "WUCHANG_GOOGLE_CLIENT_SECRET_FILE"
GOOGLE_CLIENT_SECRET_FILE = "/run/secrets/google_member_client_secret"
RESULT_PREFIX = "WUCHANG_GOOGLE_PROVIDER_RESULT="
DATABASE_PREFIX = "WUCHANG_ODOO_DATABASE_RESULT="
APPLY_CONFIRMATION = "APPLY_EXISTING_GOOGLE_PROVIDER"
CANONICAL_BASE_URL = "https://wuchang.life"
CANONICAL_CALLBACK_URL = f"{CANONICAL_BASE_URL}{CALLBACK_PATH}"
SAFE_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
SAFE_CONTAINER_PATH = re.compile(r"^/[A-Za-z0-9_./-]+$")


def database_name_from_config(path: Path) -> str:
    parser = configparser.ConfigParser(interpolation=None)
    if not parser.read(path, encoding="utf-8") or not parser.has_section("options"):
        raise ValueError("odoo_config_missing")
    database = (parser.get("options", "db_name", fallback="") or "").strip()
    if not database or not SAFE_NAME.fullmatch(database):
        raise ValueError("single_database_name_required")
    return database


def validate_public_base_url(value: str) -> str:
    if "<" in (value or "") or ">" in (value or ""):
        raise ValueError("public_base_url_placeholder_detected")
    parsed = urlsplit((value or "").strip().rstrip("/"))
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not hostname or parsed.username or parsed.password:
        raise ValueError("public_https_base_url_required")
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise ValueError("public_base_url_must_be_origin_only")
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise ValueError("loopback_public_base_url_rejected")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address and address.is_loopback:
        raise ValueError("loopback_public_base_url_rejected")
    return f"{parsed.scheme}://{parsed.netloc}"


def callback_uri(public_base_url: str) -> str:
    return f"{validate_public_base_url(public_base_url)}{CALLBACK_PATH}"


def build_database_discovery_program() -> str:
    return f'''import json
import os
import psycopg2

connection_kwargs = {{
    "host": os.environ.get("HOST"),
    "port": os.environ.get("PORT") or "5432",
    "user": os.environ.get("USER"),
    "password": os.environ.get("PASSWORD"),
}}
if not all((connection_kwargs["host"], connection_kwargs["user"], connection_kwargs["password"])):
    raise RuntimeError("container_odoo_connection_environment_missing")
root = psycopg2.connect(dbname="postgres", **connection_kwargs)
root.autocommit = True
with root.cursor() as cursor:
    cursor.execute("SELECT datname FROM pg_database WHERE datallowconn AND NOT datistemplate ORDER BY datname")
    database_names = [row[0] for row in cursor.fetchall()]
root.close()

odoo_databases = []
member_databases = []
for database_name in database_names:
    try:
        connection = psycopg2.connect(dbname=database_name, **connection_kwargs)
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('public.ir_module_module')")
            if cursor.fetchone()[0]:
                odoo_databases.append(database_name)
                cursor.execute(
                    "SELECT 1 FROM ir_module_module WHERE name = %s AND state = %s LIMIT 1",
                    ("wuchang_google_member_login", "installed"),
                )
                if cursor.fetchone():
                    member_databases.append(database_name)
        connection.close()
    except Exception:
        continue

candidates = member_databases or odoo_databases
result = {{
    "database": candidates[0] if len(candidates) == 1 else "",
    "candidate_count": len(candidates),
}}
print({DATABASE_PREFIX!r} + json.dumps(result, sort_keys=True))
'''


def discover_database(container: str) -> str:
    if not SAFE_NAME.fullmatch(container):
        raise ValueError("unsafe_container_name")
    completed = subprocess.run(
        ["docker", "exec", "-i", container, "python3", "-"],
        input=build_database_discovery_program(),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"database_discovery_failed:{completed.returncode}")
    result_line = next(
        (line for line in completed.stdout.splitlines() if line.startswith(DATABASE_PREFIX)),
        None,
    )
    if not result_line:
        raise RuntimeError("database_discovery_result_missing")
    result = json.loads(result_line[len(DATABASE_PREFIX) :])
    database = result.get("database") or ""
    if result.get("candidate_count") != 1 or not SAFE_NAME.fullmatch(database):
        raise RuntimeError("single_odoo_database_not_identified")
    return database


def build_odoo_shell_program(mode: str, payload: dict[str, str] | None = None) -> str:
    if mode not in {"check", "apply"}:
        raise ValueError("unsupported_mode")
    encoded_payload = base64.urlsafe_b64encode(
        json.dumps(payload or {}, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    return f'''import base64
import json
import os
import stat
from pathlib import Path
from urllib.parse import urlsplit


def google_endpoint_state(value, endpoint_kind):
    try:
        parsed = urlsplit((value or "").strip())
    except ValueError:
        return "INVALID_REF" if value else "MISSING"
    allowed_paths = {{
        "authorization": {{"/o/oauth2/auth", "/o/oauth2/v2/auth"}},
        "userinfo": {{"/oauth2/v1/userinfo", "/oauth2/v2/userinfo", "/oauth2/v3/userinfo"}},
    }}
    allowed_host = "accounts.google.com" if endpoint_kind == "authorization" else "www.googleapis.com"
    if (
        parsed.scheme == "https"
        and parsed.hostname == allowed_host
        and not parsed.username
        and not parsed.password
        and parsed.path in allowed_paths[endpoint_kind]
        and not parsed.query
        and not parsed.fragment
    ):
        return "PRESENT_TRUSTED_GOOGLE_HTTPS"
    return "INVALID_REF" if value else "MISSING"


def secret_file_state():
    configured_path = os.environ.get({GOOGLE_CLIENT_SECRET_FILE_ENV!r}, "")
    if configured_path != {GOOGLE_CLIENT_SECRET_FILE!r}:
        return "INVALID_REF" if configured_path else "MISSING"
    try:
        file_status = Path(configured_path).lstat()
    except OSError:
        return "MISSING"
    if not stat.S_ISREG(file_status.st_mode):
        return "INVALID_TYPE"
    if stat.S_IMODE(file_status.st_mode) != 0o600:
        return "INVALID_MODE"
    return "PRESENT" if file_status.st_size > 0 else "EMPTY"

payload = json.loads(base64.urlsafe_b64decode({encoded_payload!r}).decode("utf-8"))
provider = env.ref("auth_oauth.provider_google", raise_if_not_found=False)
params = env["ir.config_parameter"].sudo()

if {mode!r} == "apply":
    if not provider:
        raise RuntimeError("existing_google_provider_missing")
    provider.sudo().write({{
        "enabled": True,
        "client_id": payload["client_id"],
        "auth_endpoint": "https://accounts.google.com/o/oauth2/auth",
        "validation_endpoint": "https://www.googleapis.com/oauth2/v3/userinfo",
        "data_endpoint": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scope": "openid profile email",
        "body": "Google",
    }})
    params.set_param("wuchang_google_member_login.client_secret", payload["client_secret"])
    params.set_param("wuchang_google_member_login.base_url", payload["public_base_url"])
    params.set_param("wuchang_google_member_login.redirect_uri", payload["callback_uri"])

provider = env.ref("auth_oauth.provider_google", raise_if_not_found=False)
public_base_url = params.get_param("wuchang_google_member_login.base_url") or ""
redirect_uri = params.get_param("wuchang_google_member_login.redirect_uri") or ""
provider_exists = bool(provider)
provider_active = bool(provider and provider.enabled)
client_id_present = bool(provider and provider.client_id)
callback_present = redirect_uri == {CANONICAL_CALLBACK_URL!r}
public_base_present = public_base_url == "https://wuchang.life"
auth_endpoint_state = google_endpoint_state(
    provider.auth_endpoint if provider else "", "authorization"
)
userinfo_endpoint = ""
if provider:
    userinfo_endpoint = provider.data_endpoint or provider.validation_endpoint or ""
userinfo_endpoint_state = google_endpoint_state(userinfo_endpoint, "userinfo")
runtime_secret_file_state = secret_file_state()
canonical_callback_state = "PRESENT" if {CANONICAL_CALLBACK_URL!r} else "INVALID_REF"
runtime_login_ready = all((
    provider_exists,
    provider_active,
    client_id_present,
    callback_present,
    public_base_present,
    runtime_secret_file_state == "PRESENT",
    auth_endpoint_state == "PRESENT_TRUSTED_GOOGLE_HTTPS",
    userinfo_endpoint_state == "PRESENT_TRUSTED_GOOGLE_HTTPS",
    canonical_callback_state == "PRESENT",
))
result = {{
    "provider_exists": "PRESENT" if provider_exists else "MISSING",
    "provider_active": "PRESENT" if provider_active else "INACTIVE",
    "client_id_state": "PRESENT" if client_id_present else "MISSING",
    "client_secret_state": runtime_secret_file_state,
    "auth_endpoint_state": auth_endpoint_state,
    "validation_endpoint_state": "PRESENT" if provider and provider.validation_endpoint else "MISSING",
    "data_endpoint_state": "PRESENT" if provider and provider.data_endpoint else "MISSING",
    "userinfo_endpoint_state": userinfo_endpoint_state,
    "scope_state": "PRESENT" if provider and provider.scope else "MISSING",
    "body_state": "PRESENT" if provider and provider.body else "MISSING",
    "public_base_url_state": "PRESENT" if public_base_present else "INVALID_REF" if public_base_url else "MISSING",
    "callback_uri_state": "PRESENT" if callback_present and public_base_present else "INVALID_REF" if redirect_uri else "MISSING",
    "canonical_callback_state": canonical_callback_state,
    "login_health": "PASS" if runtime_login_ready else "HOLD_CONFIGURATION_REQUIRED",
    "db_write_executed": False,
    "secret_output": False,
}}
if {mode!r} == "apply":
    if result["login_health"] != "PASS":
        env.cr.rollback()
        result["apply_state"] = "ROLLED_BACK_CONFIGURATION_INCOMPLETE"
    else:
        env.cr.commit()
        result["db_write_executed"] = True
        result["apply_state"] = "APPLIED"
print({RESULT_PREFIX!r} + json.dumps(result, sort_keys=True))
'''


def docker_command(container: str, container_config: str, database: str) -> list[str]:
    if not SAFE_NAME.fullmatch(container) or not SAFE_NAME.fullmatch(database):
        raise ValueError("unsafe_container_or_database_name")
    if not SAFE_CONTAINER_PATH.fullmatch(container_config):
        raise ValueError("unsafe_container_config_path")
    return [
        "docker",
        "exec",
        "-i",
        container,
        "/entrypoint.sh",
        "odoo",
        "shell",
        "-c",
        container_config,
        "-d",
        database,
        "--no-http",
    ]


def run_odoo_shell(command: list[str], program: str) -> dict[str, object]:
    if not shutil.which("docker"):
        raise RuntimeError("docker_command_missing")
    completed = subprocess.run(
        command,
        input=program,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"odoo_shell_failed:{completed.returncode}")
    result_line = next(
        (line for line in completed.stdout.splitlines() if line.startswith(RESULT_PREFIX)),
        None,
    )
    if not result_line:
        raise RuntimeError("odoo_shell_result_missing")
    return json.loads(result_line[len(RESULT_PREFIX) :])


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    mode = result.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="read and report status only")
    mode.add_argument("--apply", action="store_true", help="update the existing Provider")
    mode.add_argument("--plan", action="store_true", help="print a no-DB-write operation plan")
    result.add_argument("--container", default=DEFAULT_CONTAINER)
    result.add_argument("--host-odoo-config", type=Path)
    result.add_argument("--container-odoo-config", default=DEFAULT_CONTAINER_CONFIG)
    result.add_argument("--database")
    result.add_argument("--public-base-url")
    result.add_argument("--confirm", default="")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    database = args.database
    if not database and args.host_odoo_config:
        database = database_name_from_config(args.host_odoo_config)
    if not database and not args.plan:
        database = discover_database(args.container)
    database = database or "database-discovered-at-check-or-apply"
    command = docker_command(args.container, args.container_odoo_config, database)
    if args.plan:
        print(json.dumps({
            "mode": "PLAN_ONLY",
            "provider": "auth_oauth.provider_google",
            "operation": "UPDATE_EXISTING_ONLY",
            "database_source": "CONTAINER_ODOO_CONNECTION_OR_EXPLICIT_CONFIG",
            "transport": "ODOO_SHELL_STDIN",
            "local_postgresql_socket": False,
            "temporary_file": False,
            "db_write_executed": False,
            "secret_output": False,
        }, sort_keys=True))
        return 0

    mode = "apply" if args.apply else "check"
    payload = None
    if mode == "apply":
        if args.confirm != APPLY_CONFIRMATION:
            raise SystemExit("HOLD=explicit_apply_confirmation_required")
        client_id = os.environ.get("WUCHANG_GOOGLE_CLIENT_ID", "")
        secret_value = os.environ.get("WUCHANG_GOOGLE_CLIENT_SECRET", "")
        if not client_id or not secret_value:
            raise SystemExit("HOLD=credential_environment_refs_required")
        if not args.public_base_url:
            raise SystemExit("HOLD=public_base_url_required")
        public_base_url = validate_public_base_url(args.public_base_url)
        payload = {
            "client_id": client_id,
            "client_secret": secret_value,
            "public_base_url": public_base_url,
            "callback_uri": callback_uri(public_base_url),
        }
    result = run_odoo_shell(command, build_odoo_shell_program(mode, payload))
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("login_health") == "PASS" or mode == "check" else 1


if __name__ == "__main__":
    sys.exit(main())
