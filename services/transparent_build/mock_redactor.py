"""In-memory synthetic redactor for Transparent Build Mode mock packets."""

from __future__ import annotations

import copy
import json
import re
import sys
from typing import Any

from mock_observation_collector import BLOCKED_SENSITIVE_PATHS, collect_mock_observation


ASSIGNMENT_RE = re.compile(
    r"(?i)\b(token|password|private[_ ]key|oauth[_ ]secret|client[_ ]secret|credential)\s*=\s*\S+"
)
BEARER_RE = re.compile(r"(?i)\bBearer\s+\S+")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d -]{7,}\d)(?!\d)")
BLOCKED_VALUE_KEYS = {"raw_profile", "member_profile", "vault_content", "secret_value", "token_value"}


def _redact_string(value: str, categories: set[str]) -> tuple[str, int]:
    count = 0

    value, changed = ASSIGNMENT_RE.subn(r"\1=<REDACTED_SENSITIVE_VALUE>", value)
    if changed:
        categories.add("sensitive_assignment")
        count += changed

    value, changed = BEARER_RE.subn("Bearer <REDACTED_TOKEN>", value)
    if changed:
        categories.add("bearer_token")
        count += changed

    value, changed = EMAIL_RE.subn("<REDACTED_EMAIL>", value)
    if changed:
        categories.add("email")
        count += changed

    value, changed = PHONE_RE.subn("<REDACTED_PHONE>", value)
    if changed:
        categories.add("phone")
        count += changed

    return value, count


def _redact_value(value: Any, categories: set[str]) -> tuple[Any, int]:
    if isinstance(value, str):
        return _redact_string(value, categories)
    if isinstance(value, list):
        output = []
        total = 0
        for item in value:
            cleaned, count = _redact_value(item, categories)
            output.append(cleaned)
            total += count
        return output, total
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        total = 0
        for key, item in value.items():
            if key in BLOCKED_VALUE_KEYS:
                output[key] = "<REDACTED_BLOCKED_FIELD>"
                categories.add("blocked_field")
                total += 1
                continue
            cleaned, count = _redact_value(item, categories)
            output[key] = cleaned
            total += count
        return output, total
    return value, 0


def redact_observation_pack(pack: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Redact a synthetic pack, while preserving the blocked-path policy list."""
    original_paths = list(pack.get("blocked_sensitive_paths", []))
    categories: set[str] = set()
    cleaned, replacement_count = _redact_value(copy.deepcopy(pack), categories)
    cleaned["blocked_sensitive_paths"] = original_paths or list(BLOCKED_SENSITIVE_PATHS)
    summary = {
        "applied": True,
        "replacement_count": replacement_count,
        "categories": sorted(categories),
    }
    return cleaned, summary


def main(argv: list[str]) -> int:
    scenario = argv[0] if argv else "audit_blocked"
    pack, summary = redact_observation_pack(collect_mock_observation(scenario))
    print(json.dumps({"pack": pack, "redaction_summary": summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
