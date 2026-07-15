#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic TFCT/TRUE8D candidate runtime core.

The module implements a candidate-only, local deterministic evaluation path.
It does not promote or alter an Active Canonical, implement distributed
consensus, or create a second D3 engine.  D3 projection is delegated directly
to the accepted candidate transition engine and its governance metadata remains
outside the D3 coordinate body.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, TypeAlias, cast

from tools.d3_coordinate_transition_candidate import (
    D3TransitionValidationError,
    transition_coordinate,
    verify_transition_record,
)


JSONScalar: TypeAlias = None | bool | int | float | str
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY_PATH = (
    ROOT
    / "runtime"
    / "total_field"
    / "candidate"
    / "tfct_true8d_runtime_policy_v0_1.json"
)
RUNTIME_SCHEMA_VERSION = "tfct.true8d.runtime-candidate/0.1"
TFID_PREFIX = "tfid:candidate:v0.1:"
STATE_REF_PREFIX = "tfs-state:candidate:v0.1:"
FIELD_NAMES = ("D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8")
DECISIONS = frozenset({"ALLOW", "HOLD", "BLOCK", "QUARANTINE"})
CONSTRAINT_OUTCOMES = frozenset({"PASS", "HOLD", "BLOCK", "QUARANTINE"})
FIXED_POINT_STATUSES = frozenset(
    {"REACHED", "NOT_REACHED", "CYCLE_DETECTED", "MAX_ITERATIONS_REACHED"}
)
D3_ENGINE_D7_KEYS = frozenset(
    {
        "reconstruction_condition",
        "routing_ref",
        "rule_ref",
        "table_ref",
        "template_ref",
    }
)


class RuntimeCandidateError(ValueError):
    """Raised for a deterministic candidate-runtime validation failure."""

    def __init__(self, reason_code: str, detail: str = "") -> None:
        """Initialize the error with one stable code and non-sensitive detail."""

        self.reason_code = reason_code
        self.detail = detail
        message = reason_code if not detail else f"{reason_code}: {detail}"
        super().__init__(message)


def _clone_json(
    value: Any,
    *,
    path: str,
    active_container_ids: frozenset[int],
) -> JSONValue:
    """Validate and recursively clone one JSON-compatible value."""

    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise RuntimeCandidateError("ERR_NON_FINITE_NUMBER", path)
        return value
    if isinstance(value, list):
        container_id = id(value)
        if container_id in active_container_ids:
            raise RuntimeCandidateError("ERR_CYCLIC_JSON_VALUE", path)
        next_ids = active_container_ids | frozenset({container_id})
        return [
            _clone_json(item, path=f"{path}[{index}]", active_container_ids=next_ids)
            for index, item in enumerate(value)
        ]
    if isinstance(value, dict):
        container_id = id(value)
        if container_id in active_container_ids:
            raise RuntimeCandidateError("ERR_CYCLIC_JSON_VALUE", path)
        next_ids = active_container_ids | frozenset({container_id})
        cloned: dict[str, JSONValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise RuntimeCandidateError("ERR_JSON_OBJECT_KEY_TYPE", path)
            cloned[key] = _clone_json(
                item,
                path=f"{path}.{key}",
                active_container_ids=next_ids,
            )
        return cloned
    raise RuntimeCandidateError("ERR_NON_JSON_VALUE", path)


def deep_copy_json(value: Any) -> JSONValue:
    """Return a validated deep copy without retaining caller-owned containers."""

    cloned = _clone_json(value, path="$", active_container_ids=frozenset())
    try:
        json.dumps(
            cloned,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeCandidateError("ERR_JSON_SERIALIZATION") from exc
    return cloned


def canonical_json(value: Any) -> str:
    """Serialize a JSON-compatible value with the candidate canonical form."""

    cloned = deep_copy_json(value)
    try:
        return json.dumps(
            cloned,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeCandidateError("ERR_JSON_SERIALIZATION") from exc


def canonical_sha256(value: Any) -> str:
    """Return SHA-256 over the UTF-8 candidate canonical serialization."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _is_sha256_hex(value: str) -> bool:
    """Recognize one lowercase hexadecimal SHA-256 digest."""

    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _require_non_empty_text(value: Any, field_name: str) -> str:
    """Return a non-empty string or raise one stable validation error."""

    if not isinstance(value, str) or not value:
        raise RuntimeCandidateError("ERR_REQUIRED_REFERENCE", field_name)
    return value


def _closed_mapping(
    value: Any,
    *,
    required: frozenset[str],
    location: str,
) -> dict[str, JSONValue]:
    """Clone a mapping and enforce an exact closed set of keys."""

    if not isinstance(value, Mapping):
        raise RuntimeCandidateError("ERR_MAPPING_REQUIRED", location)
    raw = dict(value)
    cloned = deep_copy_json(raw)
    if not isinstance(cloned, dict):
        raise RuntimeCandidateError("ERR_MAPPING_REQUIRED", location)
    keys = frozenset(cloned)
    missing = sorted(required - keys)
    if missing:
        raise RuntimeCandidateError(
            "ERR_REQUIRED_MEMBER_MISSING", f"{location}:{','.join(missing)}"
        )
    extras = sorted(keys - required)
    if extras:
        raise RuntimeCandidateError(
            "ERR_UNKNOWN_MEMBER", f"{location}:{','.join(extras)}"
        )
    return cloned


def _string_tuple(value: Any, field_name: str) -> tuple[str, ...]:
    """Validate a JSON array of unique, non-empty strings."""

    if not isinstance(value, list):
        raise RuntimeCandidateError("ERR_POLICY_FIELD_TYPE", field_name)
    result: list[str] = []
    for item in value:
        result.append(_require_non_empty_text(item, field_name))
    if len(result) != len(frozenset(result)):
        raise RuntimeCandidateError("ERR_POLICY_DUPLICATE_VALUE", field_name)
    return tuple(result)


def _strict_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build a JSON object while rejecting duplicate member names."""

    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeCandidateError("ERR_DUPLICATE_MEMBER", key)
        result[key] = value
    return result


def _reject_json_constant(token: str) -> None:
    """Reject non-finite constants accepted by the default decoder."""

    raise RuntimeCandidateError("ERR_NON_FINITE_NUMBER", token)


@dataclass(frozen=True, slots=True)
class Event:
    """Caller-supplied deterministic event identity and rule references."""

    event_ref: str
    event_code: str
    event_id: str
    logical_time: JSONValue
    rule_set_ref: str
    priority_policy_ref: str
    observation_domain_ref: str

    def __post_init__(self) -> None:
        """Validate and detach all event values from caller-owned input."""

        for field_name in (
            "event_ref",
            "event_code",
            "event_id",
            "rule_set_ref",
            "priority_policy_ref",
            "observation_domain_ref",
        ):
            _require_non_empty_text(getattr(self, field_name), field_name)
        object.__setattr__(self, "logical_time", deep_copy_json(self.logical_time))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Event":
        """Create an event from one closed mapping."""

        data = _closed_mapping(
            value,
            required=frozenset(
                {
                    "event_ref",
                    "event_code",
                    "event_id",
                    "logical_time",
                    "rule_set_ref",
                    "priority_policy_ref",
                    "observation_domain_ref",
                }
            ),
            location="event",
        )
        return cls(
            event_ref=cast(str, data["event_ref"]),
            event_code=cast(str, data["event_code"]),
            event_id=cast(str, data["event_id"]),
            logical_time=data["logical_time"],
            rule_set_ref=cast(str, data["rule_set_ref"]),
            priority_policy_ref=cast(str, data["priority_policy_ref"]),
            observation_domain_ref=cast(str, data["observation_domain_ref"]),
        )

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a detached JSON event representation."""

        return cast(
            dict[str, JSONValue],
            deep_copy_json(
                {
                    "event_ref": self.event_ref,
                    "event_code": self.event_code,
                    "event_id": self.event_id,
                    "logical_time": self.logical_time,
                    "rule_set_ref": self.rule_set_ref,
                    "priority_policy_ref": self.priority_policy_ref,
                    "observation_domain_ref": self.observation_domain_ref,
                }
            ),
        )


@dataclass(frozen=True, slots=True)
class ObservationDomain:
    """Opaque Observation Domain reference with locally supplied observations."""

    observation_domain_ref: str
    configured: bool
    observations: Mapping[str, JSONValue]

    def __post_init__(self) -> None:
        """Validate the reference and detach observation data."""

        _require_non_empty_text(
            self.observation_domain_ref, "observation_domain_ref"
        )
        if not isinstance(self.configured, bool):
            raise RuntimeCandidateError(
                "ERR_OBSERVATION_DOMAIN_CONFIGURED_TYPE",
                "configured",
            )
        cloned = deep_copy_json(dict(self.observations))
        if not isinstance(cloned, dict):
            raise RuntimeCandidateError("ERR_MAPPING_REQUIRED", "observations")
        object.__setattr__(self, "observations", cloned)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ObservationDomain":
        """Create an Observation Domain from one closed mapping."""

        data = _closed_mapping(
            value,
            required=frozenset(
                {"observation_domain_ref", "configured", "observations"}
            ),
            location="observation_domain",
        )
        observations = data["observations"]
        if not isinstance(observations, dict):
            raise RuntimeCandidateError("ERR_MAPPING_REQUIRED", "observations")
        return cls(
            observation_domain_ref=cast(str, data["observation_domain_ref"]),
            configured=cast(bool, data["configured"]),
            observations=observations,
        )

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a detached JSON Observation Domain representation."""

        return cast(
            dict[str, JSONValue],
            deep_copy_json(
                {
                    "observation_domain_ref": self.observation_domain_ref,
                    "configured": self.configured,
                    "observations": dict(self.observations),
                }
            ),
        )


@dataclass(frozen=True, slots=True)
class EightFieldState:
    """Closed TRUE8D state whose D3 body remains coordinate data only."""

    D1: JSONValue
    D2: JSONValue
    D3: JSONValue
    D4: JSONValue
    D5: JSONValue
    D6: JSONValue
    D7: JSONValue
    D8: JSONValue

    def __post_init__(self) -> None:
        """Validate and detach every dimension value."""

        for field_name in FIELD_NAMES:
            object.__setattr__(
                self,
                field_name,
                deep_copy_json(getattr(self, field_name)),
            )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "EightFieldState":
        """Create a state from an exact D1-through-D8 mapping."""

        data = _closed_mapping(
            value,
            required=frozenset(FIELD_NAMES),
            location="eight_field_state",
        )
        return cls(**{name: data[name] for name in FIELD_NAMES})

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a detached exact D1-through-D8 mapping."""

        return cast(
            dict[str, JSONValue],
            deep_copy_json({name: getattr(self, name) for name in FIELD_NAMES}),
        )


@dataclass(frozen=True, slots=True)
class ConstraintResult:
    """One deterministic Constraint Hypergraph edge evaluation result."""

    constraint_ref: str
    outcome: str
    reason_code: str
    affected_fields: tuple[str, ...]
    evidence: Mapping[str, JSONValue]

    def __post_init__(self) -> None:
        """Validate stable constraint output and detach evidence."""

        _require_non_empty_text(self.constraint_ref, "constraint_ref")
        if self.outcome not in CONSTRAINT_OUTCOMES:
            raise RuntimeCandidateError("ERR_CONSTRAINT_OUTCOME", self.outcome)
        _require_non_empty_text(self.reason_code, "reason_code")
        if any(field_name not in FIELD_NAMES for field_name in self.affected_fields):
            raise RuntimeCandidateError("ERR_CONSTRAINT_FIELD")
        cloned = deep_copy_json(dict(self.evidence))
        if not isinstance(cloned, dict):
            raise RuntimeCandidateError("ERR_MAPPING_REQUIRED", "evidence")
        object.__setattr__(self, "evidence", cloned)

    def to_dict(self) -> dict[str, JSONValue]:
        """Return detached constraint evidence."""

        return cast(
            dict[str, JSONValue],
            deep_copy_json(
                {
                    "constraint_ref": self.constraint_ref,
                    "outcome": self.outcome,
                    "reason_code": self.reason_code,
                    "affected_fields": list(self.affected_fields),
                    "evidence": dict(self.evidence),
                }
            ),
        )


@dataclass(frozen=True, slots=True)
class HyperedgeConstraint:
    """Versioned candidate constraint definition in stable execution order."""

    constraint_ref: str
    status: str
    order: int
    evaluator: str
    affected_fields: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate one executable constraint registry entry."""

        _require_non_empty_text(self.constraint_ref, "constraint_ref")
        if self.status != "CANDIDATE":
            raise RuntimeCandidateError("ERR_POLICY_NOT_CANDIDATE", self.constraint_ref)
        if not isinstance(self.order, int) or isinstance(self.order, bool) or self.order < 0:
            raise RuntimeCandidateError("ERR_CONSTRAINT_ORDER", self.constraint_ref)
        _require_non_empty_text(self.evaluator, "evaluator")
        if not self.affected_fields:
            raise RuntimeCandidateError("ERR_CONSTRAINT_FIELD", self.constraint_ref)
        if any(field_name not in FIELD_NAMES for field_name in self.affected_fields):
            raise RuntimeCandidateError("ERR_CONSTRAINT_FIELD", self.constraint_ref)


@dataclass(frozen=True, slots=True)
class RuleReference:
    """One explicit deterministic rule operation from the candidate registry."""

    name: str
    ref: str
    status: str
    operation: str
    test_only: bool

    def __post_init__(self) -> None:
        """Validate one candidate rule reference."""

        _require_non_empty_text(self.name, "rule_name")
        _require_non_empty_text(self.ref, "rule_ref")
        if self.status != "CANDIDATE":
            raise RuntimeCandidateError("ERR_POLICY_NOT_CANDIDATE", self.ref)
        _require_non_empty_text(self.operation, "operation")
        if not isinstance(self.test_only, bool):
            raise RuntimeCandidateError("ERR_POLICY_FIELD_TYPE", self.ref)


@dataclass(frozen=True, slots=True)
class PriorityPolicy:
    """Validated immutable view of the candidate priority policy registry."""

    schema_version: str
    policy_version: str
    status: str
    max_iterations: int
    allowed_source_modes: tuple[str, ...]
    stable_decisions: tuple[str, ...]
    decision_priority: tuple[str, ...]
    hard_risk_codes: tuple[str, ...]
    sensitive_key_names: tuple[str, ...]
    candidate_only_sources: tuple[str, ...]
    commit_rule: Mapping[str, JSONValue]
    cycle_policy: Mapping[str, JSONValue]
    timeout_policy: Mapping[str, JSONValue]
    consensus_mode: str
    distributed_consensus_status: str
    adi_mode: str
    rule_refs: tuple[RuleReference, ...]
    priority_policy_ref: str
    constraint_hypergraph_ref: str
    convergence_operator_ref: str
    dimension_refs: Mapping[str, JSONValue]
    constraint_refs: tuple[HyperedgeConstraint, ...]
    d7_allowed_reference_keys: tuple[str, ...]
    d7_raw_channel_keys: tuple[str, ...]
    authority_forbidden_keys: tuple[str, ...]
    open_problem_gates: tuple[Mapping[str, JSONValue], ...]

    def __post_init__(self) -> None:
        """Validate policy invariants and detach nested policy objects."""

        if self.status != "CANDIDATE":
            raise RuntimeCandidateError("ERR_POLICY_NOT_CANDIDATE")
        if (
            not isinstance(self.max_iterations, int)
            or isinstance(self.max_iterations, bool)
            or self.max_iterations < 1
        ):
            raise RuntimeCandidateError("ERR_MAX_ITERATIONS")
        if self.allowed_source_modes != ("TOTAL_FIELD_PULL", "LLM_PUSH"):
            raise RuntimeCandidateError("ERR_ALLOWED_SOURCE_MODES")
        if frozenset(self.stable_decisions) != DECISIONS:
            raise RuntimeCandidateError("ERR_STABLE_DECISIONS")
        if self.decision_priority != ("QUARANTINE", "BLOCK", "HOLD", "ALLOW"):
            raise RuntimeCandidateError("ERR_DECISION_PRIORITY")
        if self.consensus_mode != "LOCAL_EQUIVALENCE_ONLY":
            raise RuntimeCandidateError("ERR_CONSENSUS_MODE")
        if self.distributed_consensus_status != "OPEN_PROBLEM":
            raise RuntimeCandidateError("ERR_DISTRIBUTED_CONSENSUS_STATUS")
        if not all(
            isinstance(value, Mapping)
            for value in (self.commit_rule, self.cycle_policy, self.timeout_policy)
        ):
            raise RuntimeCandidateError("ERR_POLICY_FIELD_TYPE")
        if dict(self.commit_rule) != {
            "status": "CANDIDATE",
            "fixed_point_status": "REACHED",
            "final_decision": "ALLOW",
            "action": "COMMIT_PROPOSED_ONLY",
        }:
            raise RuntimeCandidateError("ERR_COMMIT_RULE")
        if dict(self.cycle_policy) != {
            "status": "CANDIDATE",
            "fixed_point_status": "CYCLE_DETECTED",
            "decision": "HOLD",
            "reason_code": "CONVERGENCE_CYCLE_DETECTED",
        }:
            raise RuntimeCandidateError("ERR_CYCLE_POLICY")
        if dict(self.timeout_policy) != {
            "status": "CANDIDATE",
            "fixed_point_status": "MAX_ITERATIONS_REACHED",
            "decision": "HOLD",
            "reason_code": "CONVERGENCE_TIMEOUT",
        }:
            raise RuntimeCandidateError("ERR_TIMEOUT_POLICY")
        expected_rules = (
            ("identity", "rules/tfct/identity_v0_1", "IDENTITY", False),
            ("normalize", "rules/tfct/normalize_v0_1", "NORMALIZE_JSON", False),
            (
                "test_cycle",
                "rules/tfct/test_cycle_v0_1",
                "TEST_CYCLE_D5_MARKER",
                True,
            ),
            (
                "test_timeout",
                "rules/tfct/test_timeout_v0_1",
                "TEST_TIMEOUT_D5_COUNTER",
                True,
            ),
        )
        actual_rules = tuple(
            (rule.name, rule.ref, rule.operation, rule.test_only)
            for rule in self.rule_refs
        )
        if actual_rules != expected_rules:
            raise RuntimeCandidateError("ERR_POLICY_RULE_SET")
        _require_non_empty_text(self.priority_policy_ref, "priority_policy_ref")
        _require_non_empty_text(
            self.constraint_hypergraph_ref, "constraint_hypergraph_ref"
        )
        _require_non_empty_text(
            self.convergence_operator_ref, "convergence_operator_ref"
        )
        dimension_refs = cast(
            dict[str, JSONValue], deep_copy_json(dict(self.dimension_refs))
        )
        expected_dimension_keys = frozenset(f"D{index}_ref" for index in range(1, 9))
        if frozenset(dimension_refs) != expected_dimension_keys:
            raise RuntimeCandidateError("ERR_POLICY_DIMENSION_REFS")
        for key, value in dimension_refs.items():
            _require_non_empty_text(value, key)
        object.__setattr__(self, "dimension_refs", dimension_refs)
        expected_constraint_order = tuple(
            sorted(self.constraint_refs, key=lambda constraint: constraint.order)
        )
        if expected_constraint_order != self.constraint_refs:
            raise RuntimeCandidateError("ERR_CONSTRAINT_ORDER")
        if len({constraint.order for constraint in self.constraint_refs}) != len(
            self.constraint_refs
        ):
            raise RuntimeCandidateError("ERR_CONSTRAINT_ORDER")
        object.__setattr__(
            self,
            "commit_rule",
            cast(dict[str, JSONValue], deep_copy_json(dict(self.commit_rule))),
        )
        object.__setattr__(
            self,
            "cycle_policy",
            cast(dict[str, JSONValue], deep_copy_json(dict(self.cycle_policy))),
        )
        object.__setattr__(
            self,
            "timeout_policy",
            cast(dict[str, JSONValue], deep_copy_json(dict(self.timeout_policy))),
        )
        object.__setattr__(
            self,
            "open_problem_gates",
            tuple(
                cast(dict[str, JSONValue], deep_copy_json(dict(item)))
                for item in self.open_problem_gates
            ),
        )

    def rule_by_ref(self, rule_ref: str) -> RuleReference | None:
        """Return the rule definition for an exact versioned reference."""

        for rule in self.rule_refs:
            if rule.ref == rule_ref:
                return rule
        return None

    def decision_rank(self, decision: str) -> int:
        """Return a lower numeric rank for a more restrictive decision."""

        if decision not in self.decision_priority:
            raise RuntimeCandidateError("ERR_DECISION_UNKNOWN", decision)
        return self.decision_priority.index(decision)


@dataclass(frozen=True, slots=True)
class TFS:
    """Deterministic local Total Field State candidate identity."""

    state: EightFieldState
    state_ref: str
    tfid: str
    total_field_hash: str

    def __post_init__(self) -> None:
        """Validate candidate TFS identifiers."""

        if not self.state_ref.startswith(STATE_REF_PREFIX) or not _is_sha256_hex(
            self.state_ref[len(STATE_REF_PREFIX) :]
        ):
            raise RuntimeCandidateError("ERR_STATE_REF_FORMAT")
        if not self.tfid.startswith(TFID_PREFIX) or not _is_sha256_hex(
            self.tfid[len(TFID_PREFIX) :]
        ):
            raise RuntimeCandidateError("ERR_TFID_FORMAT")
        if not _is_sha256_hex(self.total_field_hash):
            raise RuntimeCandidateError("ERR_TOTAL_FIELD_HASH_FORMAT")

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a detached canonical TFS comparison object."""

        return cast(
            dict[str, JSONValue],
            deep_copy_json(
                {
                    "state": self.state.to_dict(),
                    "state_ref": self.state_ref,
                    "tfid": self.tfid,
                    "total_field_hash": self.total_field_hash,
                }
            ),
        )


TotalFieldStateCandidate = TFS


@dataclass(frozen=True, slots=True)
class ConvergenceResult:
    """Complete deterministic outcome of one finite candidate evaluation."""

    schema_version: str
    event_ref: str
    observation_domain_ref: str
    rule_set_ref: str
    priority_policy_ref: str
    previous: EightFieldState
    proposed: EightFieldState
    committed: EightFieldState
    fixed_point_status: str
    final_decision: str
    decision_reason_codes: tuple[str, ...]
    commit_applied: bool
    iterations: int
    state_fingerprints: tuple[str, ...]
    constraint_results: tuple[ConstraintResult, ...]
    d3_transition: Mapping[str, JSONValue]
    tfs: TFS
    consensus_mode: str

    def __post_init__(self) -> None:
        """Validate result invariants and detach D3 transition evidence."""

        if self.schema_version != RUNTIME_SCHEMA_VERSION:
            raise RuntimeCandidateError("ERR_RUNTIME_SCHEMA_VERSION")
        if self.fixed_point_status not in FIXED_POINT_STATUSES:
            raise RuntimeCandidateError("ERR_FIXED_POINT_STATUS")
        if self.final_decision not in DECISIONS:
            raise RuntimeCandidateError("ERR_DECISION_UNKNOWN", self.final_decision)
        expected_commit = (
            self.fixed_point_status == "REACHED"
            and self.final_decision == "ALLOW"
        )
        if self.commit_applied is not expected_commit:
            raise RuntimeCandidateError("ERR_ALLOW_ONLY_COMMIT")
        expected_state = self.proposed if expected_commit else self.previous
        if self.committed.to_dict() != expected_state.to_dict():
            raise RuntimeCandidateError("ERR_COMMITTED_STATE_MISMATCH")
        if self.tfs.state.to_dict() != self.committed.to_dict():
            raise RuntimeCandidateError("ERR_TFS_STATE_MISMATCH")
        if self.iterations < 1:
            raise RuntimeCandidateError("ERR_ITERATION_COUNT")
        cloned = deep_copy_json(dict(self.d3_transition))
        if not isinstance(cloned, dict):
            raise RuntimeCandidateError("ERR_MAPPING_REQUIRED", "d3_transition")
        object.__setattr__(self, "d3_transition", cloned)

    @property
    def state_ref(self) -> str:
        """Return the deterministic committed-state reference."""

        return self.tfs.state_ref

    @property
    def tfid(self) -> str:
        """Return the TFID bound to the committed state."""

        return self.tfs.tfid

    @property
    def total_field_hash(self) -> str:
        """Return the deterministic hash of the full transition contract."""

        return self.tfs.total_field_hash

    def to_dict(self) -> dict[str, JSONValue]:
        """Return the closed runtime-result payload used by gateway profiles."""

        return cast(
            dict[str, JSONValue],
            deep_copy_json(
                {
                    "schema_version": self.schema_version,
                    "event_ref": self.event_ref,
                    "observation_domain_ref": self.observation_domain_ref,
                    "rule_set_ref": self.rule_set_ref,
                    "priority_policy_ref": self.priority_policy_ref,
                    "previous": self.previous.to_dict(),
                    "proposed": self.proposed.to_dict(),
                    "committed": self.committed.to_dict(),
                    "fixed_point_status": self.fixed_point_status,
                    "final_decision": self.final_decision,
                    "decision_reason_codes": list(self.decision_reason_codes),
                    "commit_applied": self.commit_applied,
                    "iterations": self.iterations,
                    "state_fingerprints": list(self.state_fingerprints),
                    "constraint_results": [
                        result.to_dict() for result in self.constraint_results
                    ],
                    "d3_transition": dict(self.d3_transition),
                    "state_ref": self.state_ref,
                    "tfid": self.tfid,
                    "total_field_hash": self.total_field_hash,
                    "consensus_mode": self.consensus_mode,
                }
            ),
        )


@dataclass(frozen=True, slots=True)
class EquivalenceResult:
    """Local deterministic equivalence comparison without consensus claims."""

    status: str
    canonical_state_match: bool
    state_ref_match: bool
    tfid_match: bool
    total_field_hash_match: bool
    difference_paths: tuple[str, ...]
    consensus_mode: str = "LOCAL_EQUIVALENCE_ONLY"
    distributed_consensus: str = "OPEN_PROBLEM"

    def __post_init__(self) -> None:
        """Validate local-equivalence result invariants."""

        if self.status not in {"MATCH", "MISMATCH"}:
            raise RuntimeCandidateError("ERR_EQUIVALENCE_STATUS")
        expected = (
            self.canonical_state_match
            and self.state_ref_match
            and self.tfid_match
            and self.total_field_hash_match
        )
        if (self.status == "MATCH") is not expected:
            raise RuntimeCandidateError("ERR_EQUIVALENCE_INVARIANT")
        if self.consensus_mode != "LOCAL_EQUIVALENCE_ONLY":
            raise RuntimeCandidateError("ERR_CONSENSUS_MODE")
        if self.distributed_consensus != "OPEN_PROBLEM":
            raise RuntimeCandidateError("ERR_DISTRIBUTED_CONSENSUS_STATUS")

    def to_dict(self) -> dict[str, JSONValue]:
        """Return detached local equivalence evidence."""

        return cast(
            dict[str, JSONValue],
            deep_copy_json(
                {
                    "status": self.status,
                    "canonical_state_match": self.canonical_state_match,
                    "state_ref_match": self.state_ref_match,
                    "tfid_match": self.tfid_match,
                    "total_field_hash_match": self.total_field_hash_match,
                    "difference_paths": list(self.difference_paths),
                    "consensus_mode": self.consensus_mode,
                    "distributed_consensus": self.distributed_consensus,
                }
            ),
        )


Equivalence = EquivalenceResult


def _policy_rule_object(value: Any, name: str) -> RuleReference:
    """Parse one closed rule definition from the policy registry."""

    data = _closed_mapping(
        value,
        required=frozenset({"ref", "status", "operation", "test_only"}),
        location=f"rule_refs.{name}",
    )
    return RuleReference(
        name=name,
        ref=cast(str, data["ref"]),
        status=cast(str, data["status"]),
        operation=cast(str, data["operation"]),
        test_only=cast(bool, data["test_only"]),
    )


def _policy_constraint(value: Any, index: int) -> HyperedgeConstraint:
    """Parse one closed executable Hyperedge Constraint definition."""

    data = _closed_mapping(
        value,
        required=frozenset(
            {"ref", "status", "order", "evaluator", "affected_fields"}
        ),
        location=f"constraint_refs[{index}]",
    )
    return HyperedgeConstraint(
        constraint_ref=cast(str, data["ref"]),
        status=cast(str, data["status"]),
        order=cast(int, data["order"]),
        evaluator=cast(str, data["evaluator"]),
        affected_fields=_string_tuple(
            data["affected_fields"], f"constraint_refs[{index}].affected_fields"
        ),
    )


def _candidate_rule_mapping(value: Any, field_name: str) -> dict[str, JSONValue]:
    """Validate a candidate policy sub-rule and return a detached mapping."""

    if not isinstance(value, dict):
        raise RuntimeCandidateError("ERR_POLICY_FIELD_TYPE", field_name)
    cloned = cast(dict[str, JSONValue], deep_copy_json(value))
    if cloned.get("status") != "CANDIDATE":
        raise RuntimeCandidateError("ERR_POLICY_NOT_CANDIDATE", field_name)
    return cloned


def _priority_policy_from_mapping(value: Mapping[str, Any]) -> PriorityPolicy:
    """Build a validated PriorityPolicy from a closed JSON mapping."""

    required = frozenset(
        {
            "schema_version",
            "policy_version",
            "status",
            "max_iterations",
            "allowed_source_modes",
            "stable_decisions",
            "decision_priority",
            "hard_risk_codes",
            "sensitive_key_names",
            "candidate_only_sources",
            "commit_rule",
            "cycle_policy",
            "timeout_policy",
            "consensus_mode",
            "distributed_consensus_status",
            "adi_mode",
            "rule_refs",
            "priority_policy_ref",
            "constraint_hypergraph_ref",
            "convergence_operator_ref",
            "dimension_refs",
            "constraint_refs",
            "d7_allowed_reference_keys",
            "d7_raw_channel_keys",
            "authority_forbidden_keys",
            "open_problem_gates",
        }
    )
    data = _closed_mapping(value, required=required, location="policy")
    raw_rules = data["rule_refs"]
    if not isinstance(raw_rules, dict):
        raise RuntimeCandidateError("ERR_POLICY_FIELD_TYPE", "rule_refs")
    expected_rule_names = frozenset(
        {"identity", "normalize", "test_cycle", "test_timeout"}
    )
    if frozenset(raw_rules) != expected_rule_names:
        raise RuntimeCandidateError("ERR_POLICY_RULE_SET")
    rules = tuple(
        _policy_rule_object(raw_rules[name], name)
        for name in ("identity", "normalize", "test_cycle", "test_timeout")
    )
    raw_constraints = data["constraint_refs"]
    if not isinstance(raw_constraints, list):
        raise RuntimeCandidateError("ERR_POLICY_FIELD_TYPE", "constraint_refs")
    constraints = tuple(
        _policy_constraint(item, index)
        for index, item in enumerate(raw_constraints)
    )
    evaluator_order = tuple(item.evaluator for item in constraints)
    expected_evaluator_order = (
        "REQUIRED_FIELDS",
        "AUTHORITY_GUARD",
        "D6_SOVEREIGN_PRIVACY",
        "D7_REFERENCE_ONLY",
        "OPEN_PROBLEM_GATE",
    )
    if evaluator_order != expected_evaluator_order:
        raise RuntimeCandidateError("ERR_CONSTRAINT_ORDER")
    gates = data["open_problem_gates"]
    if not isinstance(gates, list) or not gates:
        raise RuntimeCandidateError("ERR_POLICY_FIELD_TYPE", "open_problem_gates")
    parsed_gates = tuple(
        _candidate_rule_mapping(item, f"open_problem_gates[{index}]")
        for index, item in enumerate(gates)
    )
    max_iterations = data["max_iterations"]
    if not isinstance(max_iterations, int) or isinstance(max_iterations, bool):
        raise RuntimeCandidateError("ERR_MAX_ITERATIONS")
    dimension_refs = data["dimension_refs"]
    if not isinstance(dimension_refs, dict):
        raise RuntimeCandidateError("ERR_POLICY_FIELD_TYPE", "dimension_refs")
    return PriorityPolicy(
        schema_version=cast(str, data["schema_version"]),
        policy_version=cast(str, data["policy_version"]),
        status=cast(str, data["status"]),
        max_iterations=max_iterations,
        allowed_source_modes=_string_tuple(
            data["allowed_source_modes"], "allowed_source_modes"
        ),
        stable_decisions=_string_tuple(data["stable_decisions"], "stable_decisions"),
        decision_priority=_string_tuple(
            data["decision_priority"], "decision_priority"
        ),
        hard_risk_codes=_string_tuple(data["hard_risk_codes"], "hard_risk_codes"),
        sensitive_key_names=_string_tuple(
            data["sensitive_key_names"], "sensitive_key_names"
        ),
        candidate_only_sources=_string_tuple(
            data["candidate_only_sources"], "candidate_only_sources"
        ),
        commit_rule=_candidate_rule_mapping(data["commit_rule"], "commit_rule"),
        cycle_policy=_candidate_rule_mapping(data["cycle_policy"], "cycle_policy"),
        timeout_policy=_candidate_rule_mapping(data["timeout_policy"], "timeout_policy"),
        consensus_mode=cast(str, data["consensus_mode"]),
        distributed_consensus_status=cast(str, data["distributed_consensus_status"]),
        adi_mode=cast(str, data["adi_mode"]),
        rule_refs=rules,
        priority_policy_ref=cast(str, data["priority_policy_ref"]),
        constraint_hypergraph_ref=cast(str, data["constraint_hypergraph_ref"]),
        convergence_operator_ref=cast(str, data["convergence_operator_ref"]),
        dimension_refs=dimension_refs,
        constraint_refs=constraints,
        d7_allowed_reference_keys=_string_tuple(
            data["d7_allowed_reference_keys"], "d7_allowed_reference_keys"
        ),
        d7_raw_channel_keys=_string_tuple(
            data["d7_raw_channel_keys"], "d7_raw_channel_keys"
        ),
        authority_forbidden_keys=_string_tuple(
            data["authority_forbidden_keys"], "authority_forbidden_keys"
        ),
        open_problem_gates=parsed_gates,
    )


def load_policy(path: Path | str = DEFAULT_POLICY_PATH) -> PriorityPolicy:
    """Load and validate the versioned candidate runtime policy without caching."""

    policy_path = Path(path)
    try:
        text = policy_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise RuntimeCandidateError("ERR_POLICY_READ", str(policy_path)) from exc
    try:
        raw = json.loads(
            text,
            object_pairs_hook=_strict_object_pairs,
            parse_constant=_reject_json_constant,
        )
    except RuntimeCandidateError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise RuntimeCandidateError("ERR_POLICY_JSON", str(policy_path)) from exc
    if not isinstance(raw, dict):
        raise RuntimeCandidateError("ERR_POLICY_ROOT")
    return _priority_policy_from_mapping(raw)


def calculate_tfid(committed: EightFieldState | Mapping[str, Any]) -> str:
    """Return the versioned TFID bound only to canonical committed TFS state."""

    state = _coerce_state(committed)
    return TFID_PREFIX + canonical_sha256(state.to_dict())


def calculate_state_ref(committed: EightFieldState | Mapping[str, Any]) -> str:
    """Return the deterministic candidate state reference."""

    state = _coerce_state(committed)
    return STATE_REF_PREFIX + canonical_sha256(state.to_dict())


def calculate_total_field_hash(payload: Mapping[str, Any]) -> str:
    """Hash the exact closed Total Field transition contract."""

    required = frozenset(
        {
            "schema_version",
            "event_ref",
            "observation_domain_ref",
            "rule_set_ref",
            "priority_policy_ref",
            "previous",
            "proposed",
            "committed",
            "fixed_point_status",
            "final_decision",
            "decision_reason_codes",
            "commit_applied",
            "tfid",
        }
    )
    closed = _closed_mapping(
        payload,
        required=required,
        location="total_field_hash_payload",
    )
    return canonical_sha256(closed)


def _coerce_state(value: EightFieldState | Mapping[str, Any]) -> EightFieldState:
    """Return a detached EightFieldState from a model or mapping."""

    if isinstance(value, EightFieldState):
        return EightFieldState.from_mapping(value.to_dict())
    return EightFieldState.from_mapping(value)


def _coerce_event(value: Event | Mapping[str, Any]) -> Event:
    """Return a detached Event from a model or mapping."""

    if isinstance(value, Event):
        return Event.from_mapping(value.to_dict())
    return Event.from_mapping(value)


def _coerce_observation_domain(
    value: ObservationDomain | Mapping[str, Any],
) -> ObservationDomain:
    """Return a detached ObservationDomain from a model or mapping."""

    if isinstance(value, ObservationDomain):
        return ObservationDomain.from_mapping(value.to_dict())
    return ObservationDomain.from_mapping(value)


def _replace_state(state: EightFieldState, **updates: JSONValue) -> EightFieldState:
    """Return a new state with a validated subset of dimensions replaced."""

    unknown = frozenset(updates) - frozenset(FIELD_NAMES)
    if unknown:
        raise RuntimeCandidateError("ERR_UNKNOWN_DIMENSION", ",".join(sorted(unknown)))
    payload = state.to_dict()
    for key, value in updates.items():
        payload[key] = deep_copy_json(value)
    return EightFieldState.from_mapping(payload)


def _runtime_d3_projection(
    *,
    previous: EightFieldState,
    candidate: EightFieldState,
    event: Event,
    context: Mapping[str, JSONValue],
) -> tuple[EightFieldState, dict[str, JSONValue]]:
    """Delegate D3 proposal to the accepted engine and place evidence in D4."""

    if not isinstance(previous.D3, dict) or not isinstance(candidate.D3, dict):
        raise RuntimeCandidateError("ERR_D3_COORDINATE_OBJECT_REQUIRED")
    if not isinstance(candidate.D4, dict):
        raise RuntimeCandidateError("ERR_D4_EVIDENCE_OBJECT_REQUIRED")
    supplied_d3_context = context.get("d3_context", {})
    if not isinstance(supplied_d3_context, dict):
        raise RuntimeCandidateError("ERR_D3_CONTEXT_OBJECT_REQUIRED")
    d3_context = cast(dict[str, JSONValue], deep_copy_json(supplied_d3_context))
    d3_context["coordinate_delta"] = cast(
        dict[str, JSONValue], deep_copy_json(candidate.D3)
    )
    if isinstance(candidate.D7, dict):
        d7_reference = {
            key: deep_copy_json(value)
            for key, value in candidate.D7.items()
            if key in D3_ENGINE_D7_KEYS
        }
        if d7_reference:
            d3_context["d7_reference"] = d7_reference
    try:
        record = transition_coordinate(
            previous_coord=cast(dict[str, Any], deep_copy_json(previous.D3)),
            event_code=event.event_code,
            event_id=event.event_id,
            logical_time=deep_copy_json(event.logical_time),
            rule_ref=event.rule_set_ref,
            context=cast(dict[str, Any], d3_context),
        )
        verification = verify_transition_record(record)
    except D3TransitionValidationError as exc:
        raise RuntimeCandidateError("ERR_D3_TRANSITION_REJECTED") from exc
    if verification.get("valid") is not True:
        raise RuntimeCandidateError(
            "ERR_D3_TRANSITION_VERIFY",
            str(verification.get("reason_code", "UNKNOWN")),
        )
    metadata = cast(
        dict[str, JSONValue],
        deep_copy_json(
            {
                "transition_hash": record["transition_hash"],
                "event_id": record["event_id"],
                "logical_time": record["logical_time"],
                "commit_applied": record["commit_applied"],
                "final_decision": record["final_decision"],
                "decision_reason": record["decision_reason"],
                "rule_ref": record["rule_ref"],
                "verification_reason_code": verification["reason_code"],
            }
        ),
    )
    evidence = cast(dict[str, JSONValue], deep_copy_json(candidate.D4))
    evidence["d3_transition"] = deep_copy_json(metadata)
    projected = _replace_state(
        candidate,
        D3=cast(JSONValue, deep_copy_json(record["proposed"])),
        D4=evidence,
    )
    return projected, metadata


def _contains_key(value: JSONValue, names: frozenset[str]) -> tuple[str, ...]:
    """Return sorted JSON paths whose object keys match a protected set."""

    found: list[str] = []

    def visit(item: JSONValue, path: str) -> None:
        """Walk JSON containers while retaining stable member paths."""

        if isinstance(item, dict):
            for key, nested in item.items():
                child_path = f"{path}.{key}"
                if key.casefold() in names:
                    found.append(child_path)
                visit(nested, child_path)
        elif isinstance(item, list):
            for index, nested in enumerate(item):
                visit(nested, f"{path}[{index}]")

    visit(value, "$")
    return tuple(sorted(found))


def _contains_allow_claim(value: JSONValue) -> tuple[str, ...]:
    """Return paths containing an externally supplied final ALLOW claim."""

    found: list[str] = []

    def visit(item: JSONValue, path: str) -> None:
        """Walk JSON containers and record final ALLOW claims."""

        if isinstance(item, dict):
            for key, nested in item.items():
                child_path = f"{path}.{key}"
                if key == "final_decision" and nested == "ALLOW":
                    found.append(child_path)
                visit(nested, child_path)
        elif isinstance(item, list):
            for index, nested in enumerate(item):
                visit(nested, f"{path}[{index}]")

    visit(value, "$")
    return tuple(sorted(found))


def _collect_hard_risk_codes(value: JSONValue) -> tuple[str, ...]:
    """Collect explicitly labeled hard-risk codes from candidate input."""

    collected: list[str] = []

    def visit(item: JSONValue) -> None:
        """Walk JSON containers and collect explicit risk-code arrays."""

        if isinstance(item, dict):
            for key, nested in item.items():
                if key == "hard_risk_codes" and isinstance(nested, list):
                    collected.extend(code for code in nested if isinstance(code, str))
                visit(nested)
        elif isinstance(item, list):
            for nested in item:
                visit(nested)

    visit(value)
    return tuple(sorted(frozenset(collected)))


@dataclass(frozen=True, slots=True)
class _ConstraintContext:
    """Internal immutable context shared by deterministic constraint evaluators."""

    submitted_candidate: EightFieldState
    current_state: EightFieldState
    event: Event
    observation_domain: ObservationDomain
    caller_context: Mapping[str, JSONValue]
    policy: PriorityPolicy


def _result(
    constraint: HyperedgeConstraint,
    outcome: str,
    reason_code: str,
    evidence: Mapping[str, JSONValue] | None = None,
) -> ConstraintResult:
    """Build one constraint result using its declared affected fields."""

    return ConstraintResult(
        constraint_ref=constraint.constraint_ref,
        outcome=outcome,
        reason_code=reason_code,
        affected_fields=constraint.affected_fields,
        evidence=evidence or {},
    )


def _evaluate_required_fields(
    constraint: HyperedgeConstraint,
    runtime: _ConstraintContext,
) -> ConstraintResult:
    """Require all eight fields to be resolved JSON values."""

    unresolved = tuple(
        field_name
        for field_name, value in runtime.current_state.to_dict().items()
        if value is None
    )
    if unresolved:
        return _result(
            constraint,
            "HOLD",
            "REQUIRED_FIELD_UNRESOLVED",
            {"fields": list(unresolved)},
        )
    return _result(constraint, "PASS", "REQUIRED_FIELDS_PASS")


def _evaluate_authority_guard(
    constraint: HyperedgeConstraint,
    runtime: _ConstraintContext,
) -> ConstraintResult:
    """Block direct authority claims supplied by a candidate source."""

    submitted = runtime.submitted_candidate.to_dict()
    context = cast(dict[str, JSONValue], deep_copy_json(dict(runtime.caller_context)))
    joined: JSONValue = {"candidate": submitted, "context": context}
    forbidden_names = frozenset(
        key.casefold() for key in runtime.policy.authority_forbidden_keys
    )
    forbidden_paths = _contains_key(joined, forbidden_names)
    allow_paths = _contains_allow_claim(joined)
    if forbidden_paths or allow_paths:
        return _result(
            constraint,
            "BLOCK",
            "EXTERNAL_AUTHORITY_CLAIM_BLOCKED",
            {"claim_paths": list(sorted(forbidden_paths + allow_paths))},
        )
    source_mode = context.get("source_mode")
    if source_mode is not None and source_mode not in runtime.policy.allowed_source_modes:
        return _result(
            constraint,
            "BLOCK",
            "SOURCE_MODE_NOT_ALLOWED",
            {"source_mode": source_mode},
        )
    return _result(constraint, "PASS", "AUTHORITY_GUARD_PASS")


def _evaluate_d6_privacy(
    constraint: HyperedgeConstraint,
    runtime: _ConstraintContext,
) -> ConstraintResult:
    """Apply sovereign-privacy key and explicit hard-risk gates."""

    submitted = runtime.current_state.to_dict()
    context = cast(dict[str, JSONValue], deep_copy_json(dict(runtime.caller_context)))
    joined: JSONValue = {"candidate": submitted, "context": context}
    sensitive_names = frozenset(
        key.casefold() for key in runtime.policy.sensitive_key_names
    )
    sensitive_paths = _contains_key(joined, sensitive_names)
    declared_codes = frozenset(_collect_hard_risk_codes(joined))
    matched_codes = tuple(
        sorted(declared_codes & frozenset(runtime.policy.hard_risk_codes))
    )
    if matched_codes:
        return _result(
            constraint,
            "QUARANTINE",
            "D6_HARD_RISK_QUARANTINED",
            {"hard_risk_codes": list(matched_codes)},
        )
    if sensitive_paths:
        return _result(
            constraint,
            "HOLD",
            "D6_SENSITIVE_KEY_PRESENT",
            {"key_paths": list(sensitive_paths)},
        )
    return _result(constraint, "PASS", "D6_SOVEREIGN_PRIVACY_PASS")


def _evaluate_d7_reference_only(
    constraint: HyperedgeConstraint,
    runtime: _ConstraintContext,
) -> ConstraintResult:
    """Require D7 to contain references or reconstruction conditions only."""

    d7 = runtime.submitted_candidate.D7
    if not isinstance(d7, dict):
        return _result(constraint, "HOLD", "D7_REFERENCE_OBJECT_REQUIRED")
    keys = frozenset(d7)
    raw_paths = _contains_key(
        d7,
        frozenset(key.casefold() for key in runtime.policy.d7_raw_channel_keys),
    )
    if raw_paths:
        return _result(
            constraint,
            "HOLD",
            "RAW_CHANNEL_REQUIRED",
            {"raw_paths": list(raw_paths)},
        )
    unsupported = tuple(
        sorted(keys - frozenset(runtime.policy.d7_allowed_reference_keys))
    )
    if unsupported:
        return _result(
            constraint,
            "HOLD",
            "D7_REFERENCE_ONLY_REQUIRED",
            {"unsupported_keys": list(unsupported)},
        )
    invalid_refs = tuple(
        sorted(
            key
            for key, value in d7.items()
            if key.endswith("_ref") and (not isinstance(value, str) or not value)
        )
    )
    if invalid_refs:
        return _result(
            constraint,
            "HOLD",
            "D7_REFERENCE_INVALID",
            {"invalid_refs": list(invalid_refs)},
        )
    return _result(constraint, "PASS", "D7_REFERENCE_ONLY_PASS")


def _evaluate_open_problem_gate(
    constraint: HyperedgeConstraint,
    runtime: _ConstraintContext,
) -> ConstraintResult:
    """Return executable HOLD outcomes for unresolved candidate definitions."""

    if not runtime.observation_domain.configured:
        return _result(
            constraint,
            "HOLD",
            "HOLD_OBSERVATION_DOMAIN_NOT_CONFIGURED",
        )
    if (
        runtime.observation_domain.observation_domain_ref
        != runtime.event.observation_domain_ref
    ):
        return _result(
            constraint,
            "HOLD",
            "HOLD_OBSERVATION_DOMAIN_REF_MISMATCH",
        )
    if runtime.event.priority_policy_ref != runtime.policy.priority_policy_ref:
        return _result(
            constraint,
            "HOLD",
            "HOLD_PRIORITY_POLICY_NOT_CONFIGURED",
        )
    rule = runtime.policy.rule_by_ref(runtime.event.rule_set_ref)
    if rule is None:
        return _result(
            constraint,
            "HOLD",
            "HOLD_RULE_SET_NOT_CONFIGURED",
        )
    test_fixture = runtime.caller_context.get("test_fixture") is True
    if rule.test_only and not test_fixture:
        return _result(
            constraint,
            "HOLD",
            "HOLD_TEST_ONLY_RULE_OUTSIDE_FIXTURE",
        )
    projection_status = runtime.caller_context.get("gateway_projection_status")
    if projection_status == "HOLD":
        reason_code = runtime.caller_context.get("gateway_projection_reason_code")
        allowed_projection_reasons = {
            "HOLD_DIMENSION_PROJECTION_NOT_CONFIGURED",
            "HOLD_CONSTRAINT_HYPERGRAPH_NOT_CONFIGURED",
            "HOLD_CONVERGENCE_OPERATOR_NOT_CONFIGURED",
        }
        if reason_code not in allowed_projection_reasons:
            reason_code = "HOLD_DIMENSION_PROJECTION_NOT_CONFIGURED"
        return _result(constraint, "HOLD", cast(str, reason_code))
    if projection_status not in {None, "MATCH"}:
        return _result(
            constraint,
            "HOLD",
            "HOLD_DIMENSION_PROJECTION_NOT_CONFIGURED",
        )
    if runtime.caller_context.get("distributed_consensus_requested") is True:
        return _result(
            constraint,
            "HOLD",
            "HOLD_DISTRIBUTED_CONSENSUS_OPEN_PROBLEM",
        )
    if runtime.caller_context.get("adi_requested") is True:
        return _result(
            constraint,
            "HOLD",
            "HOLD_ADI_NOT_CONFIGURED",
        )
    return _result(constraint, "PASS", "OPEN_PROBLEM_GATES_PASS")


def _evaluate_constraint(
    constraint: HyperedgeConstraint,
    runtime: _ConstraintContext,
) -> ConstraintResult:
    """Dispatch one registry-declared constraint without dynamic execution."""

    if constraint.evaluator == "REQUIRED_FIELDS":
        return _evaluate_required_fields(constraint, runtime)
    if constraint.evaluator == "AUTHORITY_GUARD":
        return _evaluate_authority_guard(constraint, runtime)
    if constraint.evaluator == "D6_SOVEREIGN_PRIVACY":
        return _evaluate_d6_privacy(constraint, runtime)
    if constraint.evaluator == "D7_REFERENCE_ONLY":
        return _evaluate_d7_reference_only(constraint, runtime)
    if constraint.evaluator == "OPEN_PROBLEM_GATE":
        return _evaluate_open_problem_gate(constraint, runtime)
    raise RuntimeCandidateError("ERR_CONSTRAINT_EVALUATOR", constraint.evaluator)


def _evaluate_hypergraph(runtime: _ConstraintContext) -> tuple[ConstraintResult, ...]:
    """Execute every candidate hyperedge in stable declared priority order."""

    return tuple(
        _evaluate_constraint(constraint, runtime)
        for constraint in runtime.policy.constraint_refs
    )


def _adjudicate(
    results: tuple[ConstraintResult, ...],
    policy: PriorityPolicy,
) -> str:
    """Apply QUARANTINE, BLOCK, HOLD, ALLOW priority deterministically."""

    decisions = tuple(
        result.outcome for result in results if result.outcome != "PASS"
    )
    if not decisions:
        return "ALLOW"
    return min(decisions, key=policy.decision_rank)


def _combine_decision(left: str, right: str, policy: PriorityPolicy) -> str:
    """Return the more restrictive of two stable D8 decisions."""

    return left if policy.decision_rank(left) <= policy.decision_rank(right) else right


def _non_pass_reasons(results: tuple[ConstraintResult, ...]) -> tuple[str, ...]:
    """Return stable reason codes for every non-PASS constraint."""

    return tuple(result.reason_code for result in results if result.outcome != "PASS")


def _apply_rule(
    state: EightFieldState,
    rule: RuleReference | None,
) -> EightFieldState:
    """Apply one explicit candidate registry operation to a detached state."""

    if rule is None or rule.operation == "IDENTITY":
        return EightFieldState.from_mapping(state.to_dict())
    if rule.operation == "NORMALIZE_JSON":
        normalized = json.loads(canonical_json(state.to_dict()))
        if not isinstance(normalized, dict):
            raise RuntimeCandidateError("ERR_NORMALIZED_STATE")
        return EightFieldState.from_mapping(normalized)
    if rule.operation == "TEST_CYCLE_D5_MARKER":
        if not isinstance(state.D5, dict):
            raise RuntimeCandidateError("ERR_D5_EXECUTION_OBJECT_REQUIRED")
        d5 = cast(dict[str, JSONValue], deep_copy_json(state.D5))
        current = d5.get("candidate_test_cycle_phase")
        d5["candidate_test_cycle_phase"] = 1 if current == 0 else 0
        return _replace_state(state, D5=d5)
    if rule.operation == "TEST_TIMEOUT_D5_COUNTER":
        if not isinstance(state.D5, dict):
            raise RuntimeCandidateError("ERR_D5_EXECUTION_OBJECT_REQUIRED")
        d5 = cast(dict[str, JSONValue], deep_copy_json(state.D5))
        current = d5.get("candidate_test_timeout_counter", 0)
        if not isinstance(current, int) or isinstance(current, bool) or current < 0:
            raise RuntimeCandidateError("ERR_TEST_TIMEOUT_COUNTER")
        d5["candidate_test_timeout_counter"] = current + 1
        return _replace_state(state, D5=d5)
    raise RuntimeCandidateError("ERR_RULE_OPERATION", rule.operation)


def _finalize_result(
    *,
    event: Event,
    observation_domain: ObservationDomain,
    previous: EightFieldState,
    proposed: EightFieldState,
    fixed_point_status: str,
    final_decision: str,
    reason_codes: tuple[str, ...],
    iterations: int,
    fingerprints: tuple[str, ...],
    constraint_results: tuple[ConstraintResult, ...],
    d3_transition: Mapping[str, JSONValue],
    policy: PriorityPolicy,
) -> ConvergenceResult:
    """Enforce ALLOW-only commit and construct deterministic TFS identities."""

    commit_applied = fixed_point_status == "REACHED" and final_decision == "ALLOW"
    committed = proposed if commit_applied else previous
    committed = EightFieldState.from_mapping(committed.to_dict())
    tfid = calculate_tfid(committed)
    hash_payload: dict[str, Any] = {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "event_ref": event.event_ref,
        "observation_domain_ref": observation_domain.observation_domain_ref,
        "rule_set_ref": event.rule_set_ref,
        "priority_policy_ref": event.priority_policy_ref,
        "previous": previous.to_dict(),
        "proposed": proposed.to_dict(),
        "committed": committed.to_dict(),
        "fixed_point_status": fixed_point_status,
        "final_decision": final_decision,
        "decision_reason_codes": list(reason_codes),
        "commit_applied": commit_applied,
        "tfid": tfid,
    }
    total_field_hash = calculate_total_field_hash(hash_payload)
    tfs = TFS(
        state=committed,
        state_ref=calculate_state_ref(committed),
        tfid=tfid,
        total_field_hash=total_field_hash,
    )
    return ConvergenceResult(
        schema_version=RUNTIME_SCHEMA_VERSION,
        event_ref=event.event_ref,
        observation_domain_ref=observation_domain.observation_domain_ref,
        rule_set_ref=event.rule_set_ref,
        priority_policy_ref=event.priority_policy_ref,
        previous=EightFieldState.from_mapping(previous.to_dict()),
        proposed=EightFieldState.from_mapping(proposed.to_dict()),
        committed=committed,
        fixed_point_status=fixed_point_status,
        final_decision=final_decision,
        decision_reason_codes=reason_codes,
        commit_applied=commit_applied,
        iterations=iterations,
        state_fingerprints=fingerprints,
        constraint_results=constraint_results,
        d3_transition=d3_transition,
        tfs=tfs,
        consensus_mode=policy.consensus_mode,
    )


def run_convergence(
    *,
    previous: EightFieldState | Mapping[str, Any],
    candidate: EightFieldState | Mapping[str, Any],
    event: Event | Mapping[str, Any],
    observation_domain: ObservationDomain | Mapping[str, Any],
    context: Mapping[str, Any] | None = None,
    policy: PriorityPolicy | None = None,
    policy_path: Path | str = DEFAULT_POLICY_PATH,
) -> ConvergenceResult:
    """Run bounded deterministic convergence and D8 candidate adjudication.

    The caller supplies event identity, logical ordering, every versioned rule
    reference, and the Observation Domain reference.  The function never
    mutates those inputs.  A proposal is committed only after an ALLOW result at
    an observed fixed point; every other outcome preserves ``previous``.
    """

    previous_state = _coerce_state(previous)
    submitted_candidate = _coerce_state(candidate)
    event_model = _coerce_event(event)
    domain_model = _coerce_observation_domain(observation_domain)
    raw_context = {} if context is None else dict(context)
    context_copy = deep_copy_json(raw_context)
    if not isinstance(context_copy, dict):
        raise RuntimeCandidateError("ERR_MAPPING_REQUIRED", "context")
    selected_policy = policy if policy is not None else load_policy(policy_path)
    proposed, d3_metadata = _runtime_d3_projection(
        previous=previous_state,
        candidate=submitted_candidate,
        event=event_model,
        context=context_copy,
    )
    rule = selected_policy.rule_by_ref(event_model.rule_set_ref)
    current = EightFieldState.from_mapping(proposed.to_dict())
    initial_fingerprint = canonical_sha256(current.to_dict())
    fingerprints: list[str] = [initial_fingerprint]
    seen: dict[str, int] = {initial_fingerprint: 0}
    previous_fingerprint = initial_fingerprint
    latest_results: tuple[ConstraintResult, ...] = ()
    latest_decision = "ALLOW"

    for iteration in range(1, selected_policy.max_iterations + 1):
        next_state = _apply_rule(current, rule)
        fingerprint = canonical_sha256(next_state.to_dict())
        fingerprints.append(fingerprint)
        runtime_context = _ConstraintContext(
            submitted_candidate=submitted_candidate,
            current_state=next_state,
            event=event_model,
            observation_domain=domain_model,
            caller_context=context_copy,
            policy=selected_policy,
        )
        latest_results = _evaluate_hypergraph(runtime_context)
        latest_decision = _adjudicate(latest_results, selected_policy)

        if fingerprint == previous_fingerprint:
            if latest_decision == "ALLOW":
                fixed_status = "REACHED"
                reasons = ("FIXED_POINT_REACHED",)
            else:
                fixed_status = "NOT_REACHED"
                reasons = _non_pass_reasons(latest_results)
            return _finalize_result(
                event=event_model,
                observation_domain=domain_model,
                previous=previous_state,
                proposed=next_state,
                fixed_point_status=fixed_status,
                final_decision=latest_decision,
                reason_codes=reasons,
                iterations=iteration,
                fingerprints=tuple(fingerprints),
                constraint_results=latest_results,
                d3_transition=d3_metadata,
                policy=selected_policy,
            )

        if fingerprint in seen:
            cycle_decision = _combine_decision(
                latest_decision,
                cast(str, selected_policy.cycle_policy["decision"]),
                selected_policy,
            )
            reasons = _non_pass_reasons(latest_results) + (
                cast(str, selected_policy.cycle_policy["reason_code"]),
            )
            return _finalize_result(
                event=event_model,
                observation_domain=domain_model,
                previous=previous_state,
                proposed=next_state,
                fixed_point_status=cast(
                    str, selected_policy.cycle_policy["fixed_point_status"]
                ),
                final_decision=cycle_decision,
                reason_codes=reasons,
                iterations=iteration,
                fingerprints=tuple(fingerprints),
                constraint_results=latest_results,
                d3_transition=d3_metadata,
                policy=selected_policy,
            )

        seen[fingerprint] = iteration
        previous_fingerprint = fingerprint
        current = next_state

    timeout_decision = _combine_decision(
        latest_decision,
        cast(str, selected_policy.timeout_policy["decision"]),
        selected_policy,
    )
    timeout_reasons = _non_pass_reasons(latest_results) + (
        cast(str, selected_policy.timeout_policy["reason_code"]),
    )
    return _finalize_result(
        event=event_model,
        observation_domain=domain_model,
        previous=previous_state,
        proposed=current,
        fixed_point_status=cast(
            str, selected_policy.timeout_policy["fixed_point_status"]
        ),
        final_decision=timeout_decision,
        reason_codes=timeout_reasons,
        iterations=selected_policy.max_iterations,
        fingerprints=tuple(fingerprints),
        constraint_results=latest_results,
        d3_transition=d3_metadata,
        policy=selected_policy,
    )


def evaluate_candidate(
    *,
    previous: EightFieldState | Mapping[str, Any],
    candidate: EightFieldState | Mapping[str, Any],
    event_ref: str,
    event_code: str,
    event_id: str,
    logical_time: JSONValue,
    rule_set_ref: str,
    priority_policy_ref: str,
    observation_domain_ref: str,
    observations: Mapping[str, Any],
    observation_domain_configured: bool,
    context: Mapping[str, Any] | None = None,
    policy: PriorityPolicy | None = None,
    policy_path: Path | str = DEFAULT_POLICY_PATH,
) -> ConvergenceResult:
    """Convenience wrapper accepting every deterministic caller input directly."""

    event = Event(
        event_ref=event_ref,
        event_code=event_code,
        event_id=event_id,
        logical_time=logical_time,
        rule_set_ref=rule_set_ref,
        priority_policy_ref=priority_policy_ref,
        observation_domain_ref=observation_domain_ref,
    )
    observations_copy = deep_copy_json(dict(observations))
    if not isinstance(observations_copy, dict):
        raise RuntimeCandidateError("ERR_MAPPING_REQUIRED", "observations")
    domain = ObservationDomain(
        observation_domain_ref=observation_domain_ref,
        configured=observation_domain_configured,
        observations=observations_copy,
    )
    return run_convergence(
        previous=previous,
        candidate=candidate,
        event=event,
        observation_domain=domain,
        context=context,
        policy=policy,
        policy_path=policy_path,
    )


def _coerce_tfs(value: TFS | ConvergenceResult | Mapping[str, Any]) -> TFS:
    """Create a detached TFS comparison model from supported result shapes."""

    if isinstance(value, ConvergenceResult):
        value = value.tfs
    if isinstance(value, TFS):
        return TFS(
            state=EightFieldState.from_mapping(value.state.to_dict()),
            state_ref=value.state_ref,
            tfid=value.tfid,
            total_field_hash=value.total_field_hash,
        )
    data = dict(value)
    state_value = data.get("state", data.get("committed"))
    if not isinstance(state_value, Mapping):
        raise RuntimeCandidateError("ERR_TFS_STATE_REQUIRED")
    return TFS(
        state=EightFieldState.from_mapping(state_value),
        state_ref=_require_non_empty_text(data.get("state_ref"), "state_ref"),
        tfid=_require_non_empty_text(data.get("tfid"), "tfid"),
        total_field_hash=_require_non_empty_text(
            data.get("total_field_hash"), "total_field_hash"
        ),
    )


def _difference_paths(left: JSONValue, right: JSONValue, path: str = "$") -> tuple[str, ...]:
    """Return stable JSON paths that differ between two canonical values."""

    differences: list[str] = []
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(frozenset(left) | frozenset(right)):
            child = f"{path}.{key}"
            if key not in left or key not in right:
                differences.append(child)
            else:
                differences.extend(_difference_paths(left[key], right[key], child))
        return tuple(differences)
    if isinstance(left, list) and isinstance(right, list):
        common = min(len(left), len(right))
        for index in range(common):
            differences.extend(
                _difference_paths(left[index], right[index], f"{path}[{index}]")
            )
        for index in range(common, max(len(left), len(right))):
            differences.append(f"{path}[{index}]")
        return tuple(differences)
    if left != right or type(left) is not type(right):
        differences.append(path)
    return tuple(differences)


def compare_tfs_equivalence(
    node_a: TFS | ConvergenceResult | Mapping[str, Any],
    node_b: TFS | ConvergenceResult | Mapping[str, Any],
) -> EquivalenceResult:
    """Compare local canonical TFS state and identities across two nodes."""

    left = _coerce_tfs(node_a)
    right = _coerce_tfs(node_b)
    canonical_state_match = canonical_json(left.state.to_dict()) == canonical_json(
        right.state.to_dict()
    )
    state_ref_match = left.state_ref == right.state_ref
    tfid_match = left.tfid == right.tfid
    total_field_hash_match = left.total_field_hash == right.total_field_hash
    paths = list(_difference_paths(left.state.to_dict(), right.state.to_dict(), "$.state"))
    if not state_ref_match:
        paths.append("$.state_ref")
    if left.tfid != right.tfid:
        paths.append("$.tfid")
    if left.total_field_hash != right.total_field_hash:
        paths.append("$.total_field_hash")
    status = (
        "MATCH"
        if canonical_state_match
        and state_ref_match
        and tfid_match
        and total_field_hash_match
        else "MISMATCH"
    )
    return EquivalenceResult(
        status=status,
        canonical_state_match=canonical_state_match,
        state_ref_match=state_ref_match,
        tfid_match=tfid_match,
        total_field_hash_match=total_field_hash_match,
        difference_paths=tuple(sorted(frozenset(paths))),
    )


__all__ = [
    "ConstraintResult",
    "ConvergenceResult",
    "DEFAULT_POLICY_PATH",
    "Equivalence",
    "EquivalenceResult",
    "EightFieldState",
    "Event",
    "HyperedgeConstraint",
    "JSONValue",
    "ObservationDomain",
    "PriorityPolicy",
    "RUNTIME_SCHEMA_VERSION",
    "RuleReference",
    "RuntimeCandidateError",
    "TFS",
    "TotalFieldStateCandidate",
    "calculate_state_ref",
    "calculate_tfid",
    "calculate_total_field_hash",
    "canonical_json",
    "canonical_sha256",
    "compare_tfs_equivalence",
    "deep_copy_json",
    "evaluate_candidate",
    "load_policy",
    "run_convergence",
]
