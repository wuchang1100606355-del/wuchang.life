#!/usr/bin/env python3
"""Fail-closed repository verifier for D6 discrete integer reconstruction."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, AbstractSet

from tools.w7tp_transfer_rule_common import (
    CANONICAL_IDENTITY,
    RuleHold,
    object_sha256,
    reject_floating_point,
    require_integer,
    validate_schema,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKET_SCHEMA = REPO_ROOT / "schemas/8d/d6_generative_transmission_packet_v2_3.schema.json"
EVIDENCE_SCHEMA = REPO_ROOT / "schemas/8d/d6_integer_reconstruction_evidence_v2_3.schema.json"
DELTA_RECEIPT_SCHEMA = REPO_ROOT / "schemas/8d/delta_apply_receipt_v1.schema.json"
VERIFIER_ID = "W7TP_D6_GENERATIVE_TRANSMISSION_VERIFIER_V2_3"


def _observed_at(value: str | None) -> str:
    return value or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _step(steps: list[dict[str, Any]], number: int, name: str, result: str) -> None:
    steps.append({"ORDER": number, "CHECK": name, "RESULT": result})


def _build_evidence(
    packet: Mapping[str, Any],
    observed_at: str,
    result: str,
    reconstructed_index: int | None,
    hold_state: str | None,
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    if reconstructed_index is not None:
        output["TARGET_STATE_INTEGER_INDEX"] = reconstructed_index
    if hold_state is not None:
        output["HOLD_STATE"] = hold_state
    evidence = {
        "RECEIPT_TYPE": "D6_INTEGER_RECONSTRUCTION_EVIDENCE",
        "EVIDENCE_SCOPE": "REPOSITORY_RULE_ONLY",
        "SOURCE_IDENTITY": str(packet.get("SOURCE_IDENTITY", "UNKNOWN")),
        "TARGET_IDENTITY": str(packet.get("TARGET_IDENTITY", "UNKNOWN")),
        "OBSERVED_AT": observed_at,
        "INPUT_DIGESTS": {"PACKET_DIGEST": object_sha256(dict(packet))},
        "OUTPUT_DIGESTS": output,
        "LOOKUP_TABLE_REFERENCE": (
            f"{packet.get('LOOKUP_TABLE_ID', 'UNKNOWN')}@"
            f"{packet.get('LOOKUP_TABLE_VERSION', 'UNKNOWN')}#"
            f"{packet.get('LOOKUP_TABLE_DIGEST', 'UNKNOWN')}"
        ),
        "TRANSITION_RULE_REFERENCE": (
            f"{packet.get('DISCRETE_TRANSITION_RULE_ID', 'UNKNOWN')}#"
            f"{packet.get('DISCRETE_TRANSITION_RULE_DIGEST', 'UNKNOWN')}"
        ),
        "VERIFIER_ID": VERIFIER_ID,
        "RESULT": result,
        "AUTHORITY_SCOPE": "NONE",
        "LINEAGE_REFERENCE": f"sha256:{object_sha256(dict(packet))}",
    }
    validate_schema(evidence, EVIDENCE_SCHEMA)
    return evidence


def _carrier_ok(packet: Mapping[str, Any], carrier_result: Mapping[str, Any] | None) -> None:
    carrier = packet["CARRIER"]
    if carrier == "REFERENCE_ONLY":
        if carrier_result is not None:
            raise RuleHold("HOLD_DELTA_BOUNDARY_VIOLATION", "UNEXPECTED_CARRIER_RESULT")
        return
    if carrier_result is None:
        raise RuleHold("HOLD_DELTA_OUTPUT_MISMATCH", "CARRIER_RESULT_REQUIRED")
    if carrier_result.get("CARRIER_RESULT") != "SUCCESS":
        raise RuleHold("HOLD_DELTA_OUTPUT_MISMATCH", "CARRIER_RESULT")
    if carrier == "DIFFERENTIAL_TRANSFER":
        receipt = carrier_result.get("DELTA_APPLY_RECEIPT")
        if not isinstance(receipt, Mapping):
            raise RuleHold("HOLD_DELTA_OUTPUT_MISMATCH", "DELTA_APPLY_RECEIPT")
        validate_schema(receipt, DELTA_RECEIPT_SCHEMA)
        if receipt["AUTHORITY_SCOPE"] != "NONE":
            raise RuleHold("HOLD_DELTA_BOUNDARY_VIOLATION", "DELTA_AUTHORITY")
        if receipt["SOURCE_IDENTITY"] != packet["SOURCE_IDENTITY"]:
            raise RuleHold("HOLD_DELTA_BASE_MISMATCH", "CARRIER_SOURCE_IDENTITY")
        if receipt["TARGET_IDENTITY"] != packet["TARGET_IDENTITY"]:
            raise RuleHold("HOLD_DELTA_OUTPUT_MISMATCH", "CARRIER_TARGET_IDENTITY")
    elif carrier == "BOUNDED_FULL_BOOTSTRAP":
        if carrier_result.get("EVIDENCE_SCOPE") != "D4_EVIDENCE_ONLY":
            raise RuleHold("HOLD_DELTA_BOUNDARY_VIOLATION", "BOOTSTRAP_EVIDENCE_SCOPE")


def _joint_d1_d8_verified(receipt: Mapping[str, Any] | None) -> bool:
    if not isinstance(receipt, Mapping):
        return False
    if receipt.get("RECEIPT_TYPE") != "D1_D8_JOINT_VERIFICATION_RECEIPT":
        return False
    dimensions = receipt.get("DIMENSIONS")
    return (
        isinstance(dimensions, Mapping)
        and set(dimensions) == {f"D{number}" for number in range(1, 9)}
        and all(value == "VERIFIED" for value in dimensions.values())
        and receipt.get("JOINTLY_CLOSED") is True
        and receipt.get("RESULT") == "VERIFIED"
    )


def verify_d6_generative_transmission(
    packet: Mapping[str, Any],
    *,
    target_field_snapshot: Mapping[str, Any],
    lookup_table: Mapping[str, Any] | None,
    transition_rule: Mapping[str, Any] | None,
    carrier_result: Mapping[str, Any] | None = None,
    seen_nonces: AbstractSet[str] = frozenset(),
    current_logical_time: int | None = None,
    d1_d8_receipt: Mapping[str, Any] | None = None,
    total_field_decision: Mapping[str, Any] | None = None,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Execute the fixed 15-step rule without granting runtime authority."""
    timestamp = _observed_at(observed_at)
    steps: list[dict[str, Any]] = []
    reconstructed_index: int | None = None
    hold_state: str | None = None
    snapshot_copy = copy.deepcopy(dict(target_field_snapshot))

    try:
        reject_floating_point(packet)
        reject_floating_point(target_field_snapshot)
        for integer_field in (
            "SOURCE_STATE_INTEGER_INDEX",
            "TARGET_BASE_INTEGER_INDEX",
            "EXPECTED_TARGET_STATE_INTEGER_INDEX",
            "MINIMUM_REQUIRED_INDEX_DELTA",
            "LOGICAL_TIME",
            "TTL",
        ):
            if integer_field in packet:
                require_integer(packet[integer_field], integer_field)
        validate_schema(packet, PACKET_SCHEMA)

        logical_time = require_integer(packet["LOGICAL_TIME"], "LOGICAL_TIME")
        ttl = require_integer(packet["TTL"], "TTL")
        if current_logical_time is not None:
            now = require_integer(current_logical_time, "CURRENT_LOGICAL_TIME")
            if now > logical_time + ttl:
                raise RuleHold("HOLD_PACKET_EXPIRED")
        if packet["NONCE"] in seen_nonces:
            raise RuleHold("HOLD_REPLAY_DETECTED")

        if (
            packet["TARGET_IDENTITY"] != packet["RECEIVER_IDENTITY"]
            or packet["TARGET_IDENTITY"] != target_field_snapshot.get("TARGET_IDENTITY")
        ):
            raise RuleHold("HOLD_COORDINATE_DRIFT", "TARGET_NODE_IDENTITY")
        _step(steps, 1, "TARGET_NODE_IDENTITY", "VERIFIED")

        if (
            packet["TARGET_FIELD_SNAPSHOT_REFERENCE"]
            != target_field_snapshot.get("SNAPSHOT_REFERENCE")
            or packet["RECONSTRUCTION_COORDINATE"]
            != target_field_snapshot.get("RECONSTRUCTION_COORDINATE")
        ):
            raise RuleHold("HOLD_COORDINATE_DRIFT", "TARGET_FIELD_SNAPSHOT")
        _step(steps, 2, "CURRENT_TARGET_FIELD_SNAPSHOT", "VERIFIED")

        if packet["CANONICAL_IDENTITY"] != CANONICAL_IDENTITY:
            raise RuleHold("HOLD_CANONICAL_VERSION_MISMATCH")
        _step(steps, 3, "CANONICAL_IDENTITY", "VERIFIED")

        if lookup_table is None:
            raise RuleHold("HOLD_LOOKUP_TABLE_NOT_FOUND")
        if (
            lookup_table.get("LOOKUP_TABLE_ID") != packet["LOOKUP_TABLE_ID"]
            or lookup_table.get("LOOKUP_TABLE_VERSION") != packet["LOOKUP_TABLE_VERSION"]
        ):
            raise RuleHold("HOLD_LOOKUP_TABLE_NOT_FOUND", "ID_OR_VERSION")
        if object_sha256(dict(lookup_table)) != packet["LOOKUP_TABLE_DIGEST"]:
            raise RuleHold("HOLD_LOOKUP_TABLE_DIGEST_MISMATCH")
        _step(steps, 4, "LOOKUP_TABLE_ID_VERSION_DIGEST", "VERIFIED")

        source_index = require_integer(
            packet["SOURCE_STATE_INTEGER_INDEX"], "SOURCE_STATE_INTEGER_INDEX"
        )
        target_base_index = require_integer(
            packet["TARGET_BASE_INTEGER_INDEX"], "TARGET_BASE_INTEGER_INDEX"
        )
        expected_target_index = require_integer(
            packet["EXPECTED_TARGET_STATE_INTEGER_INDEX"],
            "EXPECTED_TARGET_STATE_INTEGER_INDEX",
        )
        declared_delta = require_integer(
            packet["MINIMUM_REQUIRED_INDEX_DELTA"], "MINIMUM_REQUIRED_INDEX_DELTA"
        )
        if target_base_index != target_field_snapshot.get("TARGET_BASE_INTEGER_INDEX"):
            raise RuleHold("HOLD_TARGET_BASE_INDEX_MISMATCH")
        _step(steps, 5, "INTEGER_INDEX_DOMAIN", "VERIFIED")

        entries = lookup_table.get("ENTRIES")
        lookup_key = f"{source_index}:{target_base_index}"
        if not isinstance(entries, Mapping) or lookup_key not in entries:
            raise RuleHold("HOLD_LOOKUP_TABLE_NOT_FOUND", "INTEGER_LOOKUP_KEY")
        lookup_result = require_integer(entries[lookup_key], "LOOKUP_RESULT")
        _step(steps, 6, "DISCRETE_INTEGER_LOOKUP", "VERIFIED")

        computed_delta = lookup_result - target_base_index
        if computed_delta != declared_delta:
            raise RuleHold("HOLD_DISCRETE_RULE_MISMATCH", "MINIMUM_REQUIRED_INDEX_DELTA")
        _step(steps, 7, "MINIMUM_REQUIRED_INDEX_DELTA", "VERIFIED")

        _carrier_ok(packet, carrier_result)
        _step(steps, 8, "CARRIER_INPUT", "VERIFIED")
        _step(
            steps,
            9,
            "DIFFERENTIAL_TRANSFER_APPLY_IF_REQUIRED",
            "VERIFIED" if packet["CARRIER"] == "DIFFERENTIAL_TRANSFER" else "NOT_REQUIRED",
        )
        _step(steps, 10, "CARRIER_OUTPUT_DIGEST", "VERIFIED")

        if transition_rule is None:
            raise RuleHold("HOLD_DISCRETE_RULE_MISMATCH", "RULE_NOT_FOUND")
        if (
            transition_rule.get("DISCRETE_TRANSITION_RULE_ID")
            != packet["DISCRETE_TRANSITION_RULE_ID"]
            or object_sha256(dict(transition_rule))
            != packet["DISCRETE_TRANSITION_RULE_DIGEST"]
            or transition_rule.get("OPERATION") != "TARGET_BASE_PLUS_MINIMUM_REQUIRED_INDEX_DELTA"
            or transition_rule.get("NUMERIC_DOMAIN") != "INTEGER"
        ):
            raise RuleHold("HOLD_DISCRETE_RULE_MISMATCH")
        reconstructed_index = target_base_index + computed_delta
        _step(steps, 11, "DISCRETE_TARGET_NATIVE_RECONSTRUCTION", "VERIFIED")

        if reconstructed_index != lookup_result or reconstructed_index != expected_target_index:
            raise RuleHold("HOLD_TARGET_STATE_INDEX_MISMATCH")
        _step(steps, 12, "EXPECTED_TARGET_STATE_INTEGER_INDEX", "VERIFIED")

        _step(steps, 13, "TARGET_NATIVE_EVIDENCE", "GENERATED_REPOSITORY_ONLY")

        if not _joint_d1_d8_verified(d1_d8_receipt):
            raise RuleHold("HOLD_D1_D8_JOINT_VERIFICATION_REQUIRED")
        _step(steps, 14, "D1_D8_JOINT_VERIFICATION", "VERIFIED_EXTERNAL_RECEIPT")

        if not isinstance(total_field_decision, Mapping) or not (
            total_field_decision.get("RECEIPT_TYPE") == "TOTAL_FIELD_DECISION"
            and total_field_decision.get("RESULT") in {"APPROVED", "REJECTED", "HOLD"}
            and total_field_decision.get("AUTHORITY_VERIFIED") is True
        ):
            raise RuleHold("HOLD_TOTAL_FIELD_AUTHORITY_REQUIRED")
        _step(steps, 15, "TOTAL_FIELD_ADJUDICATION", "EXTERNAL_RECEIPT_OBSERVED")

        state = "CANDIDATE_D6_RULE_CHAIN_VERIFIED_NO_LIVE_EFFECT"
    except RuleHold as hold:
        hold_state = hold.state
        state = hold.state

    if dict(target_field_snapshot) != snapshot_copy:
        hold_state = "HOLD_TARGET_BASE_MUTATION_DETECTED"
        state = hold_state

    evidence_result = (
        "CANDIDATE_RECONSTRUCTION_VERIFIED"
        if reconstructed_index is not None and hold_state in {
            "HOLD_D1_D8_JOINT_VERIFICATION_REQUIRED",
            "HOLD_TOTAL_FIELD_AUTHORITY_REQUIRED",
            None,
        }
        else "HOLD"
    )
    evidence = _build_evidence(
        packet,
        timestamp,
        evidence_result,
        reconstructed_index,
        hold_state,
    )
    return {
        "STATE": state,
        "HOLD_STATE": hold_state,
        "TARGET_STATE_INTEGER_INDEX": reconstructed_index,
        "D6_INTEGER_RECONSTRUCTION_EVIDENCE": evidence,
        "D1_D8_VERIFICATION": (
            "VERIFIED_EXTERNAL_RECEIPT" if _joint_d1_d8_verified(d1_d8_receipt) else "REQUIRED"
        ),
        "TOTAL_FIELD_DECISION": (
            "EXTERNAL_RECEIPT_OBSERVED" if total_field_decision is not None else "NOT_PERFORMED"
        ),
        "D6_PASS": False,
        "TARGET_PASS": False,
        "CROSS_NODE_PASS": False,
        "END_TO_END_PASS": False,
        "RUNTIME_EFFECT": "NONE",
        "VERIFICATION_STEPS": steps,
    }
