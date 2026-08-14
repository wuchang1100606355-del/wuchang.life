#!/usr/bin/env python3
"""Build a Founder device-approval candidate without creating authority.

The executable reads one JSON object from stdin and writes one JSON result to
stdout.  It performs no database, identity-root, session, runtime, deploy,
restart, role, Canonical, or Total Field decision write.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.total_field.w7tp_intent_field_suite.canonical_hash import (
    canonical_sha256,
)


SESSION_SCHEMA_PATH = (
    ROOT / "schemas/xiaoj_member_bound_developer_seat_candidate.schema.json"
)
REQUEST_FIELDS = frozenset(
    {
        "founder_identity_evidence_ref",
        "device_ref",
        "device_evidence_sha256",
        "explicit_human_approval",
        "approval_command_ref",
        "current_epoch",
        "expires_at_epoch",
    }
)
DEVICE_REF = re.compile(r"^device_ref:[A-Za-z0-9._:-]+$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
CANDIDATE_STATE = "CANDIDATE_DEVICE_APPROVAL_PENDING_TOTAL_FIELD_VERIFY"


def _base_result(state: str) -> dict[str, Any]:
    return {
        "state": state,
        "candidate_only": True,
        "formal_authority_created": False,
        "device_or_channel_binding": None,
        "approval_receipt_candidate": None,
        "requires_total_field_verify": True,
    }


def _block(state: str) -> dict[str, Any]:
    return _base_result(state)


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_epoch(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _binding_matches_existing_schema(binding: Mapping[str, Any]) -> bool:
    try:
        schema = json.loads(SESSION_SCHEMA_PATH.read_text(encoding="utf-8"))
        binding_schema = dict(schema["properties"]["device_or_channel_binding"])
        binding_schema["$defs"] = schema["$defs"]
        return not list(Draft202012Validator(binding_schema).iter_errors(binding))
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError):
        return False


def evaluate_founder_device_approval(
    request: Mapping[str, Any],
) -> dict[str, Any]:
    """Return one deterministic, fail-closed device-approval candidate."""

    if not isinstance(request, Mapping) or set(request) != REQUEST_FIELDS:
        return _block("BLOCK_DEVICE_APPROVAL_REQUEST_FIELDS_INVALID")
    if request["explicit_human_approval"] is not True:
        return _block("BLOCK_EXPLICIT_HUMAN_APPROVAL_REQUIRED")
    if not _is_nonempty_string(request["founder_identity_evidence_ref"]):
        return _block("BLOCK_FOUNDER_IDENTITY_EVIDENCE_REF_REQUIRED")
    if (
        not isinstance(request["device_ref"], str)
        or DEVICE_REF.fullmatch(request["device_ref"]) is None
    ):
        return _block("BLOCK_DEVICE_REF_INVALID")
    if (
        not isinstance(request["device_evidence_sha256"], str)
        or SHA256.fullmatch(request["device_evidence_sha256"]) is None
    ):
        return _block("BLOCK_DEVICE_EVIDENCE_SHA256_INVALID")
    if not _is_nonempty_string(request["approval_command_ref"]):
        return _block("BLOCK_APPROVAL_COMMAND_REF_REQUIRED")
    if not _is_epoch(request["current_epoch"]) or not _is_epoch(
        request["expires_at_epoch"]
    ):
        return _block("BLOCK_DEVICE_APPROVAL_EPOCH_INVALID")
    if request["expires_at_epoch"] <= request["current_epoch"]:
        return _block("BLOCK_DEVICE_APPROVAL_EXPIRED")

    approval_material = {field: request[field] for field in sorted(REQUEST_FIELDS)}
    binding_hash = canonical_sha256(approval_material)
    binding = {
        "binding_type": "DEVICE",
        "binding_ref": request["device_ref"],
        "binding_hash": binding_hash,
    }
    if not _binding_matches_existing_schema(binding):
        return _block("BLOCK_DEVICE_OR_CHANNEL_BINDING_SCHEMA_INVALID")

    receipt_material = {
        "state": "CANDIDATE_ONLY",
        "founder_identity_evidence_ref": request[
            "founder_identity_evidence_ref"
        ],
        "device_or_channel_binding": binding,
        "device_evidence_sha256": request["device_evidence_sha256"],
        "explicit_human_approval": True,
        "approval_command_ref": request["approval_command_ref"],
        "current_epoch": request["current_epoch"],
        "expires_at_epoch": request["expires_at_epoch"],
        "formal_authority_created": False,
        "requires_total_field_verify": True,
    }
    receipt = dict(receipt_material)
    receipt["receipt_ref"] = (
        "device_approval_receipt_candidate_ref:sha256:"
        f"{canonical_sha256(receipt_material)}"
    )

    result = _base_result(CANDIDATE_STATE)
    result["device_or_channel_binding"] = binding
    result["approval_receipt_candidate"] = receipt
    return result


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def main() -> int:
    try:
        request = json.loads(sys.stdin.read(), object_pairs_hook=_unique_object)
    except (UnicodeError, ValueError, json.JSONDecodeError):
        result = _block("BLOCK_DEVICE_APPROVAL_JSON_INVALID")
    else:
        result = evaluate_founder_device_approval(request)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["state"] == CANDIDATE_STATE else 2


if __name__ == "__main__":
    raise SystemExit(main())
