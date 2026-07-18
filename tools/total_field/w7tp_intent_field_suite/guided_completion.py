"""Stateless, one-question-at-a-time completion for shared W7TP intents."""

from __future__ import annotations

import re
from typing import Any, Mapping

from tools.total_field.w7tp_field_application_runtime import (
    AUTHORITY_KEYS,
    SENSITIVE_KEYS,
    FieldApplicationError,
)

from .canonical_hash import canonical_sha256, normalize_content
from .contracts import get_contract
from .drift_monitor import evaluate_drift


EXTRA_SENSITIVE_KEYS = frozenset(
    {
        "access_token",
        "email",
        "family_member_name",
        "member_name",
        "payment_data",
        "phone",
        "raw_audio",
        "raw_image",
        "resident_name",
    }
)
EMAIL_PATTERN = re.compile(r"(?<![\w.-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])")
BEARER_PATTERN = re.compile(r"\bBearer\s+[A-Za-z0-9._~-]{8,}", re.IGNORECASE)
PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")


def validate_safe_content(value: Any, path: str = "$") -> Any:
    """Block sensitive or authority-bearing content before hashing or logging."""

    normalized = normalize_content(value, path)
    if isinstance(normalized, dict):
        for key, item in normalized.items():
            folded = key.strip().casefold()
            child = f"{path}.{key}"
            if folded in SENSITIVE_KEYS or folded in EXTRA_SENSITIVE_KEYS:
                raise FieldApplicationError("SENSITIVE_INTENT_BLOCKED", child)
            if folded in AUTHORITY_KEYS:
                raise FieldApplicationError("AUTHORITY_ESCALATION_BLOCKED", child)
            validate_safe_content(item, child)
    elif isinstance(normalized, list):
        for index, item in enumerate(normalized):
            validate_safe_content(item, f"{path}[{index}]")
    elif isinstance(normalized, str):
        if EMAIL_PATTERN.search(normalized) or BEARER_PATTERN.search(normalized) or PRIVATE_KEY_PATTERN.search(normalized):
            raise FieldApplicationError("SENSITIVE_VALUE_BLOCKED", path)
    return normalized


def missing_fields(profile: str, intent: Mapping[str, Any]) -> list[str]:
    contract = get_contract(profile)
    return [
        question.field
        for question in contract.questions
        if question.field not in intent or intent[question.field] in (None, "", [], {})
    ]


def build_guided_completion_packet(
    profile: str,
    intent: Mapping[str, Any],
    source_snapshot: Mapping[str, str],
) -> dict[str, Any] | None:
    normalized_intent = validate_safe_content(dict(intent))
    contract = get_contract(profile)
    missing = missing_fields(profile, normalized_intent)
    if not missing:
        return None
    question = next(item for item in contract.questions if item.field == missing[0])
    state_basis = {
        "profile": profile,
        "intent": normalized_intent,
        "source_snapshot": dict(source_snapshot),
        "missing_fields": missing,
    }
    packet: dict[str, Any] = {
        "schema_version": "W7TP-GUIDED-COMPLETION/1.1",
        "state": "NEEDS_USER_GUIDED_COMPLETION",
        "packet_type": "GUIDED_COMPLETION_PACKET",
        "profile": profile,
        "state_id": canonical_sha256(state_basis),
        "intent_content_sha256": canonical_sha256(normalized_intent),
        "source_snapshot": dict(source_snapshot),
        "remaining_field_count": len(missing),
        "question": {
            "question_id": question.question_id,
            "field": question.field,
            "prompt": question.prompt,
            "reason": question.reason,
            "options": list(question.options),
            "free_input_allowed": True,
            "sensitive_data_notice": "不得提供密碼、token、credential、姓名、付款資料或原始影音。",
        },
        "candidate_only": True,
        "redteam_drift_monitor": evaluate_drift(normalized_intent),
        "side_effects": {
            "db_write": False,
            "formal_transaction": False,
            "network_call": False,
        },
    }
    packet["content_sha256"] = canonical_sha256(packet)
    return packet


def continue_guided_completion(
    profile: str,
    intent: Mapping[str, Any],
    source_snapshot: Mapping[str, str],
    *,
    state_id: str,
    question_id: str,
    answer: Any,
) -> dict[str, Any]:
    current = build_guided_completion_packet(profile, intent, source_snapshot)
    if current is None:
        raise FieldApplicationError("GUIDED_COMPLETION_NOT_REQUIRED")
    if state_id != current["state_id"]:
        raise FieldApplicationError("GUIDED_STATE_MISMATCH")
    if question_id != current["question"]["question_id"]:
        raise FieldApplicationError("GUIDED_QUESTION_MISMATCH")
    safe_answer = validate_safe_content(answer, "$.answer")
    if safe_answer in (None, "", [], {}):
        raise FieldApplicationError("GUIDED_ANSWER_REQUIRED", "$.answer")
    updated = dict(validate_safe_content(dict(intent)))
    updated[current["question"]["field"]] = safe_answer
    return updated
