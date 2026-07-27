from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

SOURCE_REF = "FOUNDER_NATIVE_ADI_RULE_DECLARATION_V1.md"


@dataclass(frozen=True)
class DimensionBoundaryFacts:
    """Exact Founder-rule predicate results for one 8D dimension."""

    intent_satisfied: bool = False
    evidence_valid: bool = False
    life_safe: bool = False
    other_rights_safe: bool = False
    intent_violated: bool = False
    causal_order_violated: bool = False
    life_harm: bool = False
    other_rights_harm: bool = False
    hard_risk: bool = False


@dataclass(frozen=True)
class StatePacket8D:
    """Integer 8D state plus canonical causal/evidence bindings."""

    dimensions: Tuple[int, int, int, int, int, int, int, int]
    event_time: int
    namespace: str
    state_profile: str
    native_state_ref: str
    state_root: str
    parent_state_root: str
    evidence_root: str
    snapshot_id: str
    canonical_version: str
    rule_version: str
    logical_time: int
    topology_coordinate_ref: str
    event_hash_ref: str
    boundary_facts: Tuple[
        DimensionBoundaryFacts,
        DimensionBoundaryFacts,
        DimensionBoundaryFacts,
        DimensionBoundaryFacts,
        DimensionBoundaryFacts,
        DimensionBoundaryFacts,
        DimensionBoundaryFacts,
        DimensionBoundaryFacts,
    ]
    evidence_digests: Mapping[str, str] = field(default_factory=dict)
    expected_evidence_digests: Mapping[str, str] = field(default_factory=dict)
    satisfied_preconditions: frozenset[str] = field(default_factory=frozenset)
    previous_logical_time: int | None = None
    claimed_metric_signature: Tuple[Any, ...] | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DirectSlotConfig:
    t_min: int
    t_max: int
    slot_count: int
    slot_lookup: Mapping[Tuple[str, str, int, str, str, str], int]


@dataclass(frozen=True)
class MetricSignature:
    logical_time: int
    topology_coordinate_ref: str
    previous_state_root: str
    evidence_root: str
    event_hash_ref: str
    canonical_version: str
    rule_version: str

    def as_tuple(self) -> Tuple[Any, ...]:
        return (
            self.logical_time,
            self.topology_coordinate_ref,
            self.previous_state_root,
            self.evidence_root,
            self.event_hash_ref,
            self.canonical_version,
            self.rule_version,
        )


@dataclass(frozen=True)
class StateCrossSection:
    absolute_time_slot: int
    direct_slot: int
    state_8d: Tuple[int, ...]
    boundary_state: Tuple[int, ...]
    metric_signature: MetricSignature


@dataclass(frozen=True)
class NativeTransitionRule:
    transition_rule_id: str
    from_state_code: str
    to_state_code: str
    preconditions: Tuple[str, ...]
    required_evidence_refs: Tuple[str, ...]
    polarity: int
    direction_code: str
    step_cost_uint: int
    rule_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.step_cost_uint, int) or self.step_cost_uint <= 0:
            raise ValueError("step_cost_uint must be a positive integer")
        if self.polarity not in (-1, 0, 1):
            raise ValueError("polarity must be -1, 0, or 1")


@dataclass(frozen=True)
class CanonicalPath:
    rules: Tuple[NativeTransitionRule, ...]

    @property
    def transition_rule_ids(self) -> Tuple[str, ...]:
        return tuple(rule.transition_rule_id for rule in self.rules)

    @property
    def direction_codes(self) -> Tuple[str, ...]:
        return tuple(rule.direction_code for rule in self.rules)

    @property
    def total_cost(self) -> int:
        return sum(rule.step_cost_uint for rule in self.rules)


@dataclass(frozen=True)
class NativeAdiIndex:
    ordered_fields: Tuple[Tuple[str, Any], ...]
    native_adi_ref: str
    direct_slot: int
    absolute_distance: int
    direction_path: Tuple[str, ...]
    status: str = "NATIVE_ADI_CANDIDATE"
    profile: str = "CURRENT_FOUNDER_CANONICAL_V1"


@dataclass(frozen=True)
class NativeSpiralShell:
    radius: int
    candidates: Tuple[StatePacket8D, ...]
    status: str = "RECONSTRUCTION_CANDIDATE_ONLY"

    @property
    def candidate_state_roots(self) -> Tuple[str, ...]:
        return tuple(packet.state_root for packet in self.candidates)


@dataclass(frozen=True)
class NativeLookupReceipt:
    state: str
    shell: int | None
    candidate_state_root: str | None
    total_field_state_root: str
    evidence: Mapping[str, Any] = field(default_factory=dict)
