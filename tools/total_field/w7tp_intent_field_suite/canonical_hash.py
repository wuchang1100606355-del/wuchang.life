"""Deterministic, Unicode-normalized content hashing for W7TP packets."""

from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from typing import Any, Mapping

from tools.total_field.w7tp_field_application_runtime import FieldApplicationError


def normalize_content(value: Any, path: str = "$") -> Any:
    """Return the canonical content model.

    Strings and keys use NFC. Keys are sorted by the serializer, integers and
    null are preserved, and floating-point values are rejected so platform
    formatting cannot enter the content identity.
    """

    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise FieldApplicationError("NON_FINITE_NUMBER_BLOCKED", path)
        raise FieldApplicationError("FLOAT_CONTENT_REQUIRES_STRING", path)
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            if not isinstance(raw_key, str):
                raise FieldApplicationError("NON_STRING_KEY_BLOCKED", path)
            key = unicodedata.normalize("NFC", raw_key)
            if key in normalized:
                raise FieldApplicationError("NORMALIZED_KEY_COLLISION", f"{path}.{key}")
            normalized[key] = normalize_content(raw_value, f"{path}.{key}")
        return normalized
    if isinstance(value, (list, tuple)):
        return [normalize_content(item, f"{path}[{index}]") for index, item in enumerate(value)]
    raise FieldApplicationError("UNSUPPORTED_CONTENT_TYPE", path)


def canonical_json(value: Any) -> str:
    return json.dumps(
        normalize_content(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
