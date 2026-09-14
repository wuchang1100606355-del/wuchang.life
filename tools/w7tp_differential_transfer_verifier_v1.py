#!/usr/bin/env python3
"""Repository-only verifier for the Differential Transfer carrier."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from core.stp.delta_engine import build_delta
from tools.w7tp_transfer_rule_common import (
    RuleHold,
    object_sha256,
    reject_floating_point,
    validate_schema,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKET_SCHEMA = REPO_ROOT / "schemas/8d/differential_transfer_packet_v1.schema.json"
RECEIPT_SCHEMA = REPO_ROOT / "schemas/8d/delta_apply_receipt_v1.schema.json"
VERIFIER_ID = "W7TP_DIFFERENTIAL_TRANSFER_VERIFIER_V1"


def _observed_at(value: str | None) -> str:
    return value or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def apply_object_diff(
    base_object: Mapping[str, Any],
    diff_payload: Mapping[str, Any],
    apply_boundary: list[str],
) -> dict[str, Any]:
    """Apply a bounded top-level object diff without mutating the target base."""
    if set(diff_payload) != {"set", "delete"}:
        raise RuleHold("HOLD_DELTA_BOUNDARY_VIOLATION", "DIFF_PAYLOAD_SHAPE")
    set_values = diff_payload["set"]
    delete_values = diff_payload["delete"]
    if not isinstance(set_values, Mapping) or not isinstance(delete_values, list):
        raise RuleHold("HOLD_DELTA_BOUNDARY_VIOLATION", "DIFF_PAYLOAD_TYPES")
    if any(not isinstance(key, str) or not key for key in delete_values):
        raise RuleHold("HOLD_DELTA_BOUNDARY_VIOLATION", "DELETE_KEYS")
    if len(set(delete_values)) != len(delete_values):
        raise RuleHold("HOLD_DELTA_BOUNDARY_VIOLATION", "DUPLICATE_DELETE_KEY")
    if set(set_values).intersection(delete_values):
        raise RuleHold("HOLD_DELTA_BOUNDARY_VIOLATION", "SET_DELETE_OVERLAP")

    allowed = set(apply_boundary)
    requested = set(set_values).union(delete_values)
    if not requested.issubset(allowed):
        raise RuleHold("HOLD_DELTA_BOUNDARY_VIOLATION", "KEY_OUTSIDE_BOUNDARY")

    reconstructed = copy.deepcopy(dict(base_object))
    for key in delete_values:
        reconstructed.pop(key, None)
    for key, value in set_values.items():
        reconstructed[key] = copy.deepcopy(value)

    actual_changed = set(build_delta(dict(base_object), reconstructed))
    if not actual_changed.issubset(allowed):
        raise RuleHold("HOLD_DELTA_BOUNDARY_VIOLATION", "ACTUAL_CHANGE_OUTSIDE_BOUNDARY")
    return reconstructed


def _receipt(
    packet: Mapping[str, Any],
    observed_at: str,
    result: str,
    reconstructed_digest: str | None,
    hold_state: str | None = None,
) -> dict[str, Any]:
    input_digests = {
        "BASE_OBJECT_DIGEST": packet.get("BASE_OBJECT_DIGEST", "UNKNOWN"),
        "DIFF_PAYLOAD_DIGEST": packet.get("DIFF_PAYLOAD_DIGEST", "UNKNOWN"),
        "PACKET_DIGEST": object_sha256(dict(packet)),
    }
    output_digests: dict[str, Any] = {}
    if reconstructed_digest is not None:
        output_digests["RECONSTRUCTED_OBJECT_DIGEST"] = reconstructed_digest
    if hold_state is not None:
        output_digests["HOLD_STATE"] = hold_state
    receipt = {
        "RECEIPT_TYPE": "DELTA_APPLY_RECEIPT",
        "EVIDENCE_SCOPE": "D4_EVIDENCE_ONLY",
        "SOURCE_IDENTITY": str(packet.get("BASE_OBJECT_IDENTITY", "UNKNOWN")),
        "TARGET_IDENTITY": str(packet.get("TARGET_OBJECT_IDENTITY", "UNKNOWN")),
        "OBSERVED_AT": observed_at,
        "INPUT_DIGESTS": input_digests,
        "OUTPUT_DIGESTS": output_digests,
        "LOOKUP_TABLE_REFERENCE": "NOT_APPLICABLE_DIFFERENTIAL_TRANSFER",
        "TRANSITION_RULE_REFERENCE": "JSON_TOP_LEVEL_SET_DELETE_V1",
        "VERIFIER_ID": VERIFIER_ID,
        "RESULT": result,
        "AUTHORITY_SCOPE": "NONE",
        "LINEAGE_REFERENCE": f"sha256:{input_digests['PACKET_DIGEST']}",
        "CARRIER_RESULT": result,
    }
    validate_schema(receipt, RECEIPT_SCHEMA)
    return receipt


def verify_differential_transfer(
    packet: Mapping[str, Any],
    *,
    observed_base_identity: str,
    base_object: Mapping[str, Any],
    diff_payload: Mapping[str, Any],
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Verify and apply a bounded carrier diff; emit D4 evidence only."""
    timestamp = _observed_at(observed_at)
    reconstructed_digest: str | None = None
    try:
        reject_floating_point(packet)
        reject_floating_point(base_object)
        reject_floating_point(diff_payload)
        validate_schema(packet, PACKET_SCHEMA)
        if packet["BASE_OBJECT_IDENTITY"] != observed_base_identity:
            raise RuleHold("HOLD_DELTA_BASE_MISMATCH", "BASE_OBJECT_IDENTITY")
        if packet["BASE_OBJECT_DIGEST"] != object_sha256(dict(base_object)):
            raise RuleHold("HOLD_DELTA_BASE_MISMATCH", "BASE_OBJECT_DIGEST")
        if packet["DIFF_PAYLOAD_DIGEST"] != object_sha256(dict(diff_payload)):
            raise RuleHold("HOLD_DELTA_OUTPUT_MISMATCH", "DIFF_PAYLOAD_DIGEST")

        reconstructed = apply_object_diff(
            base_object,
            diff_payload,
            list(packet["APPLY_BOUNDARY"]),
        )
        reconstructed_digest = object_sha256(reconstructed)
        if reconstructed_digest != packet["EXPECTED_TARGET_DIGEST"]:
            raise RuleHold("HOLD_DELTA_OUTPUT_MISMATCH", "EXPECTED_TARGET_DIGEST")
        receipt = _receipt(packet, timestamp, "SUCCESS", reconstructed_digest)
        return {
            "RECONSTRUCTED_OBJECT_DIGEST": reconstructed_digest,
            "DELTA_APPLY_RECEIPT": receipt,
            "CARRIER_RESULT": "SUCCESS",
        }
    except RuleHold as hold:
        receipt = _receipt(
            packet,
            timestamp,
            "HOLD",
            reconstructed_digest,
            hold.state,
        )
        return {
            "RECONSTRUCTED_OBJECT_DIGEST": reconstructed_digest,
            "DELTA_APPLY_RECEIPT": receipt,
            "CARRIER_RESULT": "HOLD",
        }
