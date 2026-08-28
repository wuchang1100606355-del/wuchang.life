"""Output masking. This module never discovers or opens protected resources."""

from __future__ import annotations

import ipaddress
import re
from collections.abc import Mapping, Sequence
from typing import Any

MAX_MODEL_TEXT_CHARS = 16_384

_EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_IPV4 = re.compile(r"(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])")
_TAILSCALE_V6 = re.compile(r"(?i)\bfd7a:115c:a1e0(?::[0-9a-f]{0,4}){1,5}\b")
_PEM = re.compile(
    r"-----BEGIN [^-\r\n]+-----.*?-----END [^-\r\n]+-----",
    re.DOTALL,
)
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_BASIC = re.compile(r"(?i)\bBasic\s+[A-Za-z0-9+/=]+")
_AUTHORIZATION = re.compile(
    r"(?i)(?P<prefix>[\"']?authorization[\"']?\s*[:=]\s*[\"']?(?:basic|bearer)\s+)"
    r"[A-Za-z0-9._~+/=-]+"
)
_TAILSCALE_KEY = re.compile(r"(?i)\btskey-[A-Za-z0-9_-]{8,}")
_COMMON_TOKEN = re.compile(r"\b(?:sk|ghp|github_pat|cfpat)[-_][A-Za-z0-9_-]{8,}\b")
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\b")
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)(?P<prefix>[\"']?(?:token|password|passwd|secret|auth[_-]?key|api[_-]?key|"
    r"private[_-]?key|credential)[\"']?\s*[:=]\s*[\"']?)[^\"'\s,;}]+"
)
_PROTECTED_PATH = re.compile(
    r"(?i)(?:/var/run/docker\.sock|(?:^|[/\\])\.env(?:\.[^/\\\s]+)?|"
    r"(?:^|[/\\])id_(?:rsa|ed25519)|\.ssh[/\\][^\s]+|cloudflare[^\s]*token)"
)
_SENSITIVE_KEYS = re.compile(
    r"(?i)(token|password|passwd|secret|auth[_-]?key|api[_-]?key|private[_-]?key|"
    r"email|login|tailscale[_-]?ip|credential|member[_-]?plaintext)"
)


def _mask_tailscale_ipv4(match: re.Match[str]) -> str:
    value = match.group(0)
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return value
    network = ipaddress.ip_network("100.64.0.0/10")
    return "<redacted:tailscale-ipv4>" if address in network else value


def redact_text(value: str, max_chars: int = MAX_MODEL_TEXT_CHARS) -> str:
    """Mask known credential/identity patterns and bound the final text."""

    masked = _PEM.sub("<redacted:key-material>", value)
    masked = _EMAIL.sub("<redacted:login-email>", masked)
    masked = _TAILSCALE_V6.sub("<redacted:tailscale-ipv6>", masked)
    masked = _IPV4.sub(_mask_tailscale_ipv4, masked)
    masked = _AUTHORIZATION.sub(lambda match: f"{match.group('prefix')}<redacted>", masked)
    masked = _BEARER.sub("Bearer <redacted>", masked)
    masked = _BASIC.sub("Basic <redacted>", masked)
    masked = _TAILSCALE_KEY.sub("<redacted:tailscale-key>", masked)
    masked = _COMMON_TOKEN.sub("<redacted:credential>", masked)
    masked = _JWT.sub("<redacted:jwt>", masked)
    masked = _SECRET_ASSIGNMENT.sub(
        lambda match: f"{match.group('prefix')}<redacted>", masked
    )
    masked = _PROTECTED_PATH.sub("<redacted:protected-resource>", masked)
    if len(masked) > max_chars:
        return masked[: max_chars - 22] + "<truncated:policy>"
    return masked


def redact_object(value: Any) -> Any:
    """Recursively create a model-safe value without mutating the source."""

    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        output: dict[str, Any] = {}
        for raw_key, child in value.items():
            key = str(raw_key)
            if _SENSITIVE_KEYS.search(key):
                output[key] = child if child is False or child is None else "<redacted:protected-field>"
            else:
                output[key] = redact_object(child)
        return output
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return [redact_object(child) for child in value]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return redact_text(str(value))


def contains_sensitive_canary(value: Any) -> bool:
    """Return True when serialized model output still resembles protected data."""

    text = re.sub(r"<redacted(?::[^>]+)?>", "", str(value))
    patterns = (
        _EMAIL,
        _TAILSCALE_V6,
        _PEM,
        _AUTHORIZATION,
        _BEARER,
        _BASIC,
        _TAILSCALE_KEY,
        _COMMON_TOKEN,
        _JWT,
        _SECRET_ASSIGNMENT,
        _PROTECTED_PATH,
    )
    if any(pattern.search(text) for pattern in patterns):
        return True
    return any(_mask_tailscale_ipv4(match) != match.group(0) for match in _IPV4.finditer(text))
