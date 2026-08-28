"""Deterministic canonical JSON and SHA-256 identities for candidate state-field data."""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import json
import unicodedata
from enum import Enum
from typing import Any, Mapping


CANONICALIZATION_ID = "W7TP-NFC-STRINGKEY-NOFLOAT-COMPACT-SORTED-UTF8-V0.1"
SHA256_PREFIX = "sha256:"
_MIN_INT64 = -(2**63)
_MAX_INT64 = 2**63 - 1


class CanonicalizationError(ValueError):
    """Raised when a value cannot be represented in the canonical domain."""


def _normalized_string(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def _primitive(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        value = {
            field.name: getattr(value, field.name)
            for field in dataclasses.fields(value)
        }
    elif isinstance(value, Enum):
        value = value.value
    elif isinstance(value, dt.datetime):
        if value.tzinfo is None:
            raise CanonicalizationError("naive datetime is forbidden")
        value = value.astimezone(dt.UTC).isoformat().replace("+00:00", "Z")

    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        if not _MIN_INT64 <= value <= _MAX_INT64:
            raise CanonicalizationError("integer outside signed 64-bit domain")
        return value
    if isinstance(value, float):
        raise CanonicalizationError("floating-point values are forbidden")
    if isinstance(value, str):
        return _normalized_string(value)
    if isinstance(value, (tuple, list)):
        return [_primitive(item) for item in value]
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        originals: dict[str, str] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalizationError("JSON object keys must be strings")
            normalized = _normalized_string(key)
            if normalized in result:
                raise CanonicalizationError(
                    f"NFC key collision: {originals[normalized]!r} and {key!r}"
                )
            result[normalized] = _primitive(item)
            originals[normalized] = key
        return result
    raise CanonicalizationError(f"unsupported canonical type: {type(value)!r}")


def canonical_json_bytes(value: Any) -> bytes:
    """Return compact, sorted, NFC-normalized UTF-8 JSON without floats."""

    return json.dumps(
        _primitive(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8", errors="strict")


def _reject_float(value: str) -> None:
    raise CanonicalizationError(f"floating-point JSON value forbidden: {value}")


def _reject_constant(value: str) -> None:
    raise CanonicalizationError(f"non-finite JSON value forbidden: {value}")


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CanonicalizationError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def canonical_json_loads(raw: bytes, *, require_canonical: bool = True) -> Any:
    """Parse JSON fail-closed and optionally require its exact canonical bytes."""

    try:
        parsed = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_pairs_no_duplicates,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CanonicalizationError("invalid canonical JSON") from exc
    normalized = _primitive(parsed)
    if require_canonical and canonical_json_bytes(normalized) != raw:
        raise CanonicalizationError("JSON bytes are not canonical")
    return normalized


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_ref(data: bytes) -> str:
    return f"{SHA256_PREFIX}{sha256_hex(data)}"


def validate_sha256_hex(value: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise CanonicalizationError("invalid lowercase SHA-256")
    return value


def validate_sha256_ref(value: str) -> str:
    if not isinstance(value, str) or not value.startswith(SHA256_PREFIX):
        raise CanonicalizationError("invalid SHA-256 reference")
    validate_sha256_hex(value[len(SHA256_PREFIX) :])
    return value


def canonical_hash(value: Any) -> str:
    return sha256_hex(canonical_json_bytes(value))
