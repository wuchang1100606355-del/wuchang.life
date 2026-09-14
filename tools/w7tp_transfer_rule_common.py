#!/usr/bin/env python3
"""Shared deterministic primitives for repository-only W7TP transfer rules."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator


CANONICAL_IDENTITY = "W7TP / 8D ADI V2.3"
ZERO_AUTHORITY = "NONE"


class RuleHold(ValueError):
    """A fail-closed repository rule result with a fixed HOLD state."""

    def __init__(self, state: str, detail: str = "") -> None:
        super().__init__(detail or state)
        self.state = state
        self.detail = detail or state


def canonical_json(value: Any) -> bytes:
    text = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return unicodedata.normalize("NFC", text).encode("utf-8")


def object_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
    )


def validate_schema(instance: Mapping[str, Any], schema_path: Path) -> None:
    schema = load_json(schema_path)
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(dict(instance)),
        key=lambda item: ([str(part) for part in item.absolute_path], item.message),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise RuleHold("HOLD_PACKET_SCHEMA_INVALID", f"{location}:{first.message}")


def require_integer(value: Any, field: str) -> int:
    if type(value) is not int:  # bool is deliberately excluded.
        raise RuleHold("HOLD_INTEGER_INDEX_DOMAIN_INVALID", field)
    return value


def reject_floating_point(value: Any, path: str = "$") -> None:
    if isinstance(value, float):
        raise RuleHold("HOLD_INTEGER_INDEX_DOMAIN_INVALID", path)
    if isinstance(value, Mapping):
        for key, child in value.items():
            reject_floating_point(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_floating_point(child, f"{path}[{index}]")


def append_only_json(path: Path, value: Mapping[str, Any]) -> None:
    """Write one receipt without permitting an existing coordinate overwrite."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(
            dict(value),
            handle,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        handle.write("\n")
