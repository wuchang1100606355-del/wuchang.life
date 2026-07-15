#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Candidate-only deterministic D3 coordinate transition engine.

This module does not modify or promote the Active Canonical.  It keeps D3 as
coordinate data, treats D6 and D8 as gate interfaces, and limits D7 data to
generative-transmission and routing references.
"""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any, Callable, Mapping


SCHEMA_VERSION = "w7tp.d3-coordinate-transition.v0.3-candidate"
DECISIONS = {"ALLOW", "HOLD", "BLOCK", "QUARANTINE"}
D7_REFERENCE_KEYS = {
    "rule_ref",
    "table_ref",
    "template_ref",
    "routing_ref",
    "reconstruction_condition",
}
SENSITIVE_KEYS = {
    "api_key",
    "member_plaintext",
    "password",
    "raw_credentials",
    "raw_key",
    "raw_token",
    "resident_plaintext",
    "token",
}
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULE_REGISTRY = (
    ROOT / "runtime/total_field/candidate/d3_coordinate_transition_rules_v0_3.json"
)

Gate = Callable[[dict[str, Any]], Mapping[str, Any]]


class D3TransitionValidationError(ValueError):
    """Raised when deterministic transition input is invalid."""


def canonical_json(value: Any) -> str:
    """Return the fixed JSON serialization used by transition hashing."""

    try:
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise D3TransitionValidationError(
            "輸入包含 NaN、Infinity 或不可序列化值"
        ) from exc


def _deepcopy_json(value: Any) -> Any:
    try:
        copied = copy.deepcopy(value)
    except Exception as exc:
        raise D3TransitionValidationError("輸入無法深複製") from exc
    canonical_json(copied)
    return copied


def load_candidate_rule_registry(path: Path = DEFAULT_RULE_REGISTRY) -> dict[str, Any]:
    registry = json.loads(path.read_text(encoding="utf-8"))
    if registry.get("status") != "CANDIDATE_NON_CANONICAL":
        raise D3TransitionValidationError("規則表未明確標記為 candidate")
    if not isinstance(registry.get("events"), dict):
        raise D3TransitionValidationError("candidate 規則表缺少 events")
    return _deepcopy_json(registry)


def _deep_merge(base: dict[str, Any], delta: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge dicts; non-dict values and lists are replaced."""

    result = copy.deepcopy(base)
    for key, value in delta.items():
        if isinstance(result.get(key), dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _validate_d7_reference(event_code: str, context: dict[str, Any], rule: dict[str, Any]) -> None:
    d7_reference = context.get("d7_reference")
    if d7_reference is None:
        if rule.get("d7_reference_required"):
            raise D3TransitionValidationError("此事件缺少 D7 生成式傳輸或路由 reference")
        return
    if not isinstance(d7_reference, dict):
        raise D3TransitionValidationError("context.d7_reference 必須是 object")
    unsupported = set(d7_reference) - D7_REFERENCE_KEYS
    if unsupported:
        raise D3TransitionValidationError(
            "D7 僅允許生成式傳輸或路由 reference: " + ",".join(sorted(unsupported))
        )
    if event_code == "GENERATIVE_TRANSMISSION" and not d7_reference:
        raise D3TransitionValidationError("此事件缺少 D7 生成式傳輸或路由 reference")


def _validate_inputs(
    previous_coord: Any,
    event_code: Any,
    event_id: Any,
    logical_time: Any,
    rule_ref: Any,
    context: Any,
    registry: dict[str, Any],
) -> tuple[dict[str, Any], str, str, Any, str, dict[str, Any], dict[str, Any]]:
    if not isinstance(previous_coord, dict):
        raise D3TransitionValidationError("previous_coord 必須是 object")
    if not isinstance(event_code, str) or not event_code:
        raise D3TransitionValidationError("缺少必要輸入: event_code")
    events = registry["events"]
    if event_code not in events:
        raise D3TransitionValidationError("未登錄於目前規則表的事件碼")
    if not isinstance(event_id, str) or not event_id:
        raise D3TransitionValidationError("缺少必要輸入: event_id")
    if logical_time is None or logical_time == "":
        raise D3TransitionValidationError("缺少必要輸入: logical_time")
    if not isinstance(rule_ref, str) or not rule_ref:
        raise D3TransitionValidationError("缺少必要輸入: rule_ref")
    if not isinstance(context, dict):
        raise D3TransitionValidationError("context 必須是 object")

    previous_copy = _deepcopy_json(previous_coord)
    context_copy = _deepcopy_json(context)
    logical_time_copy = _deepcopy_json(logical_time)
    rule = _deepcopy_json(events[event_code])
    delta = context_copy.get("coordinate_delta", {})
    if not isinstance(delta, dict):
        raise D3TransitionValidationError("context.coordinate_delta 必須是 object")
    _validate_d7_reference(event_code, context_copy, rule)
    return (
        previous_copy,
        event_code,
        event_id,
        logical_time_copy,
        rule_ref,
        context_copy,
        rule,
    )


def _propose_coordinate(
    previous: dict[str, Any], context: dict[str, Any], rule: dict[str, Any]
) -> dict[str, Any]:
    base_delta = rule.get("base_delta", {})
    if not isinstance(base_delta, dict):
        raise D3TransitionValidationError("candidate rule base_delta 必須是 object")
    proposed = _deep_merge(previous, base_delta)
    return _deep_merge(proposed, context.get("coordinate_delta", {}))


def candidate_d6_sovereign_privacy_gate(payload: dict[str, Any]) -> dict[str, str]:
    """Candidate D6 stub that holds coordinate/context with sensitive keys."""

    def has_sensitive_key(value: Any) -> bool:
        if isinstance(value, dict):
            return any(
                str(key).lower() in SENSITIVE_KEYS or has_sensitive_key(nested)
                for key, nested in value.items()
            )
        if isinstance(value, list):
            return any(has_sensitive_key(item) for item in value)
        return False

    if has_sensitive_key(payload.get("proposed")) or has_sensitive_key(payload.get("context")):
        return {"decision": "HOLD", "reason_code": "D6_SENSITIVE_KEY_PRESENT"}
    return {"decision": "ALLOW", "reason_code": "D6_CANDIDATE_PRIVACY_ALLOW"}


def candidate_d8_gate(payload: dict[str, Any]) -> dict[str, str]:
    """Candidate D8 stub; it enforces a non-ALLOW D6 result."""

    d6_result = payload["d6_result"]
    if d6_result["decision"] != "ALLOW":
        return {
            "decision": d6_result["decision"],
            "reason_code": d6_result["reason_code"],
        }
    return {"decision": "ALLOW", "reason_code": "D8_CANDIDATE_ALLOW"}


def _validate_gate_result(name: str, value: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise D3TransitionValidationError(f"{name} gate 必須回傳 mapping")
    decision = value.get("decision")
    reason_code = value.get("reason_code")
    if decision not in DECISIONS:
        raise D3TransitionValidationError(f"{name} gate 回傳未知 decision")
    if not isinstance(reason_code, str) or not reason_code:
        raise D3TransitionValidationError(f"{name} gate 缺少穩定 reason_code")
    return {"decision": decision, "reason_code": reason_code}


def _hash_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": record["schema_version"],
        "previous": record["previous"],
        "proposed": record["proposed"],
        "committed": record["committed"],
        "commit_applied": record["commit_applied"],
        "final_decision": record["final_decision"],
        "decision_reason": record["decision_reason"],
        "event_code": record["event_code"],
        "event_id": record["event_id"],
        "logical_time": record["logical_time"],
        "rule_ref": record["rule_ref"],
        "context": record["context"],
    }


def calculate_transition_hash(record: Mapping[str, Any]) -> str:
    serialized = canonical_json(_hash_payload(record))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def transition_coordinate(
    *,
    previous_coord: dict[str, Any],
    event_code: str,
    event_id: str,
    logical_time: Any,
    rule_ref: str,
    context: dict[str, Any],
    d6_gate: Gate = candidate_d6_sovereign_privacy_gate,
    d8_gate: Gate = candidate_d8_gate,
    rule_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one deterministic candidate D3 transition record."""

    inputs = _deepcopy_json(
        {
            "previous_coord": previous_coord,
            "event_code": event_code,
            "event_id": event_id,
            "logical_time": logical_time,
            "rule_ref": rule_ref,
            "context": context,
        }
    )
    registry = _deepcopy_json(rule_registry) if rule_registry is not None else load_candidate_rule_registry()
    (
        previous,
        event_code_copy,
        event_id_copy,
        logical_time_copy,
        rule_ref_copy,
        context_copy,
        rule,
    ) = _validate_inputs(
        inputs["previous_coord"],
        inputs["event_code"],
        inputs["event_id"],
        inputs["logical_time"],
        inputs["rule_ref"],
        inputs["context"],
        registry,
    )
    proposed = _propose_coordinate(previous, context_copy, rule)

    gate_payload = {
        "schema_version": SCHEMA_VERSION,
        "previous": copy.deepcopy(previous),
        "proposed": copy.deepcopy(proposed),
        "event_code": event_code_copy,
        "event_id": event_id_copy,
        "logical_time": copy.deepcopy(logical_time_copy),
        "rule_ref": rule_ref_copy,
        "context": copy.deepcopy(context_copy),
    }
    d6_result = _validate_gate_result("D6", d6_gate(copy.deepcopy(gate_payload)))
    d8_payload = {**copy.deepcopy(gate_payload), "d6_result": copy.deepcopy(d6_result)}
    d8_result = _validate_gate_result("D8", d8_gate(d8_payload))

    if d6_result["decision"] != "ALLOW":
        final_decision = d6_result["decision"]
        decision_reason = d6_result["reason_code"]
    else:
        final_decision = d8_result["decision"]
        decision_reason = d8_result["reason_code"]
    commit_applied = final_decision == "ALLOW"
    committed = copy.deepcopy(proposed if commit_applied else previous)

    record = {
        "schema_version": SCHEMA_VERSION,
        "previous": copy.deepcopy(previous),
        "proposed": copy.deepcopy(proposed),
        "committed": committed,
        "commit_applied": commit_applied,
        "final_decision": final_decision,
        "decision_reason": decision_reason,
        "event_code": event_code_copy,
        "event_id": event_id_copy,
        "logical_time": copy.deepcopy(logical_time_copy),
        "rule_ref": rule_ref_copy,
        "context": copy.deepcopy(context_copy),
    }
    record["transition_hash"] = calculate_transition_hash(record)
    return _deepcopy_json(record)


def verify_transition_record(
    record: Mapping[str, Any], rule_registry: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Recompute the proposal and hash, then verify ALLOW-only commit rules."""

    try:
        candidate = _deepcopy_json(dict(record))
        required = {
            "schema_version",
            "previous",
            "proposed",
            "committed",
            "commit_applied",
            "final_decision",
            "decision_reason",
            "event_code",
            "event_id",
            "logical_time",
            "rule_ref",
            "context",
            "transition_hash",
        }
        if not required.issubset(candidate):
            return {"valid": False, "reason_code": "TRANSITION_RECORD_FIELDS_MISSING"}
        if candidate["schema_version"] != SCHEMA_VERSION:
            return {"valid": False, "reason_code": "SCHEMA_VERSION_MISMATCH"}
        registry = _deepcopy_json(rule_registry) if rule_registry is not None else load_candidate_rule_registry()
        previous, _, _, _, _, context, rule = _validate_inputs(
            candidate["previous"],
            candidate["event_code"],
            candidate["event_id"],
            candidate["logical_time"],
            candidate["rule_ref"],
            candidate["context"],
            registry,
        )
        if candidate["proposed"] != _propose_coordinate(previous, context, rule):
            return {"valid": False, "reason_code": "PROPOSED_COORDINATE_MISMATCH"}
        decision = candidate["final_decision"]
        if decision not in DECISIONS:
            return {"valid": False, "reason_code": "FINAL_DECISION_INVALID"}
        should_commit = decision == "ALLOW"
        if candidate["commit_applied"] is not should_commit:
            return {"valid": False, "reason_code": "COMMIT_APPLIED_MISMATCH"}
        expected_committed = candidate["proposed"] if should_commit else candidate["previous"]
        if candidate["committed"] != expected_committed:
            return {"valid": False, "reason_code": "ALLOW_ONLY_COMMIT_VIOLATION"}
        recomputed = calculate_transition_hash(candidate)
        if not hmac.compare_digest(str(candidate["transition_hash"]), recomputed):
            return {
                "valid": False,
                "reason_code": "TRANSITION_HASH_MISMATCH",
                "recomputed_hash": recomputed,
            }
        return {
            "valid": True,
            "reason_code": "TRANSITION_RECORD_VALID",
            "recomputed_hash": recomputed,
        }
    except (D3TransitionValidationError, TypeError, ValueError) as exc:
        return {"valid": False, "reason_code": "TRANSITION_RECORD_INVALID", "detail": str(exc)}


def legacy_packet_to_transition_inputs(
    packet: Mapping[str, Any],
    *,
    event_code: str,
    event_id: str,
    logical_time: Any,
    rule_ref: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Narrow adapter for the legacy runtime without changing its public API.

    Only ``D3_coordinate`` becomes D3 coordinate state.  Safe refs from legacy
    ``D6_gt`` become candidate D7 refs.  ``D7_risk`` and ``D8_envelope`` are
    deliberately not mapped because their legacy meanings differ from Active
    Canonical D7 and D8 semantics.
    """

    packet_copy = _deepcopy_json(dict(packet))
    previous = packet_copy.get("D3_coordinate")
    if not isinstance(previous, dict):
        raise D3TransitionValidationError("legacy packet 缺少 D3_coordinate")
    context_copy = _deepcopy_json(context or {})
    legacy_gt = packet_copy.get("D6_gt", {})
    if isinstance(legacy_gt, dict) and "d7_reference" not in context_copy:
        safe_refs = {
            key: copy.deepcopy(value)
            for key, value in legacy_gt.items()
            if key in D7_REFERENCE_KEYS
        }
        if safe_refs:
            context_copy["d7_reference"] = safe_refs
    context_copy["legacy_adapter"] = {
        "source_coordinate_field": "D3_coordinate",
        "legacy_gt_ref_source": "D6_gt",
        "unmapped_decision_field": "D7_risk",
        "unmapped_envelope_field": "D8_envelope",
    }
    return {
        "previous_coord": copy.deepcopy(previous),
        "event_code": event_code,
        "event_id": event_id,
        "logical_time": copy.deepcopy(logical_time),
        "rule_ref": rule_ref,
        "context": context_copy,
    }
