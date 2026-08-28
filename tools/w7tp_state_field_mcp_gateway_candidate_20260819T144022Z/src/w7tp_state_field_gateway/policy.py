"""Fail-closed input and bind policy for the local candidate."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from .errors import PolicyDenied

BIND_HOST = "127.0.0.1"
MAX_HTTP_BODY = 65_536
MAX_LOG_LINES = 200
MAX_LOG_AGE_SECONDS = 3_600
MAX_LOG_OUTPUT_BYTES = 32_768
MAX_LOG_READ_BYTES = 65_536
AUTH_TTL_MIN_SECONDS = 60
AUTH_TTL_MAX_SECONDS = 900
MAX_TASK_CANDIDATES = 256

TOOL_NAMES = (
    "list_nodes",
    "get_node_health",
    "get_compute_capability",
    "get_service_status",
    "read_bounded_logs",
    "get_state_field_topology",
    "prepare_task_candidate",
    "prepare_authorization_request",
)

_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,63}$")
_HASH = re.compile(r"^[a-f0-9]{64}$")
_FORBIDDEN_KEY = re.compile(
    r"(?i)(command|cmd|argv|shell|script|powershell|cwd|path|url|host|port|socket|"
    r"sudo|doas|pkexec|run[_-]?as|uid|admin|elevated|credential|password|secret|"
    r"token|auth[_-]?key|private[_-]?key|docker)"
)
_FORBIDDEN_TEXT = re.compile(
    r"(?:\.\.[/\\]|%2e%2e|%252e|\x00|[;&|`]|\$\(|\r|\n|"
    r"(?i:\b(?:sudo|doas|pkexec|powershell|cmd\.exe|bash|sh\s+-c)\b))"
)


def validate_bind_host(host: str) -> None:
    """Reject every bind spelling except the exact IPv4 loopback literal."""

    if host != BIND_HOST:
        raise PolicyDenied("DENY_NON_LOOPBACK_BIND", "Only 127.0.0.1 is permitted.")


def validate_identifier(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise PolicyDenied("DENY_SCHEMA", f"{field} must be an allowlisted identifier.")
    return value


def validate_sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _HASH.fullmatch(value):
        raise PolicyDenied("DENY_SCHEMA", f"{field} must be a lowercase SHA-256 value.")
    return value


def validate_integer(value: Any, field: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PolicyDenied("DENY_SCHEMA", f"{field} must be an integer.")
    if value < minimum or value > maximum:
        raise PolicyDenied("DENY_OUT_OF_BOUNDS", f"{field} is outside the allowed range.")
    return value


def validate_exact_keys(
    arguments: Mapping[str, Any], required: set[str], optional: set[str] | None = None
) -> None:
    allowed = required | (optional or set())
    supplied = set(arguments)
    if not required.issubset(supplied) or not supplied.issubset(allowed):
        raise PolicyDenied("DENY_SCHEMA", "Arguments do not match the closed tool schema.")


def validate_no_prohibited_input(value: Any) -> None:
    """Reject command, path, credential, or privilege-shaped input before dispatch."""

    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key)
            if _FORBIDDEN_KEY.search(key):
                raise PolicyDenied("DENY_PRIVILEGE_ESCALATION", "A prohibited input class was supplied.")
            validate_no_prohibited_input(child)
        return
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        for child in value:
            validate_no_prohibited_input(child)
        return
    if isinstance(value, str) and _FORBIDDEN_TEXT.search(value):
        raise PolicyDenied("DENY_PROTECTED_RESOURCE", "Command or path-shaped text is not accepted.")


def require_enum(value: Any, field: str, allowed: set[str]) -> str:
    candidate = validate_identifier(value, field)
    if candidate not in allowed:
        raise PolicyDenied("DENY_SCHEMA", f"{field} is not allowlisted.")
    return candidate
