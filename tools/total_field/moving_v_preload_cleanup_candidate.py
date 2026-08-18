"""Pure, candidate-only logic for the moving-V preload protection model.

The module classifies records and proposes non-destructive memory actions.  It
does not read clocks, mutate caches, delete data, call a model, or grant runtime
authority.  ``adi_absolute_distance_uint`` must already have been produced by
the Founder-canonical ADI ``delta_F`` path; this module never substitutes a
geometric or similarity distance.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping, Sequence


MANAGED_STORAGE_TIERS = frozenset(
    {
        "VRAM",
        "RAM",
        "STATIC_PACKET",
        "ADI_INDEX_ONLY",
        "QUARANTINE",
        "EVICTED_REFERENCE",
    }
)


class GeometryState(str, Enum):
    PAST_HOLD = "PAST_HOLD"
    PAST_ELIGIBLE = "PAST_ELIGIBLE"
    CURRENT_GUARD = "CURRENT_GUARD"
    FUTURE_PROTECTED = "FUTURE_PROTECTED"
    FUTURE_PREDICTED_MISS = "FUTURE_PREDICTED_MISS"
    OUT_OF_HORIZON = "OUT_OF_HORIZON"
    OUTSIDE_MANAGED_ENVELOPE_HOLD = "OUTSIDE_MANAGED_ENVELOPE_HOLD"
    UNALIGNED_HOLD = "UNALIGNED_HOLD"


class MemoryAction(str, Enum):
    PROTECT_CURRENT = "PROTECT_CURRENT"
    PROTECT_PRELOAD = "PROTECT_PRELOAD"
    KEEP_HOLD = "KEEP_HOLD"
    NO_PRELOAD_KEEP_REFERENCE = "NO_PRELOAD_KEEP_REFERENCE"
    SOFT_EVICT_RECONSTRUCTIBLE = "SOFT_EVICT_RECONSTRUCTIBLE"
    MOVE_TO_QUARANTINE = "MOVE_TO_QUARANTINE"
    NOOP_REFERENCE_ONLY = "NOOP_REFERENCE_ONLY"


@dataclass(frozen=True)
class EnvelopeKnot:
    future_offset_ns: int
    protected_radius_uint: int
    candidate_radius_uint: int

    @property
    def side_cleanup_width_uint(self) -> int:
        return self.candidate_radius_uint - self.protected_radius_uint


@dataclass(frozen=True)
class MovingVPolicy:
    policy_id: str
    prediction_epoch: str
    apex_time_ns: int
    safe_watermark_ns: int
    current_guard_ns: int
    clock_uncertainty_ns: int
    past_grace_ns: int
    future_horizon_ns: int
    envelope: tuple[EnvelopeKnot, ...]


@dataclass(frozen=True)
class MemoryRecord:
    record_id: str
    need_time_ns: int
    event_time_ns: int
    ingest_time_ns: int
    adi_absolute_distance_uint: int | None
    prediction_epoch: str
    record_version: int
    storage_tier: str = "RAM"
    resident_bytes: int = 0
    live_reference_count: int = 0
    active_lease: bool = False
    pinned: bool = False
    durable_source_verified: bool = False
    reconstruction_reference: str = ""
    expected_source_hash: str = ""
    observed_source_hash: str = ""
    is_canonical_source: bool = False


@dataclass(frozen=True)
class Classification:
    state: GeometryState
    reason: str
    delta_time_ns: int
    protected_radius_uint: int | None = None
    candidate_radius_uint: int | None = None


@dataclass(frozen=True)
class EvictionDecision:
    record_id: str
    classification: GeometryState
    action: MemoryAction
    reason: str
    destructive: bool
    canonical_delete_allowed: bool
    cas_prediction_epoch: str
    cas_record_version: int


@dataclass(frozen=True)
class PressurePlan:
    state: str
    target_release_bytes: int
    planned_release_bytes: int
    selected_record_ids: tuple[str, ...]
    decisions: tuple[EvictionDecision, ...]
    protected_eviction_violation: bool = False


@dataclass(frozen=True)
class BudgetPerformanceGate:
    min_sample_count_uint: int
    min_observation_ns_uint: int
    min_host_reserve_bytes_uint: int
    max_p95_latency_regression_bp_uint: int
    max_false_miss_rate_bp_uint: int
    min_preload_hit_rate_bp_uint: int


@dataclass(frozen=True)
class BudgetPerformanceEvidence:
    sample_count_uint: int
    observation_ns_uint: int
    host_available_after_adjustment_bytes_uint: int
    protected_working_set_bytes_uint: int
    p95_latency_regression_bp_uint: int
    false_miss_rate_bp_uint: int
    preload_hit_rate_bp_uint: int
    oom_event_count_uint: int = 0
    swap_thrashing: bool = False
    protected_eviction_violation_count_uint: int = 0
    reconstruction_hash_mismatch_count_uint: int = 0


@dataclass(frozen=True)
class BudgetAdjustmentDecision:
    state: str
    current_limit_bytes: int
    proposed_limit_bytes: int
    reason: str
    applies_change: bool = False


def _require_uint(name: str, value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name}_MUST_BE_UINT")


def _is_uint(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def validate_policy(policy: MovingVPolicy) -> None:
    if not policy.policy_id or not policy.prediction_epoch:
        raise ValueError("POLICY_ID_AND_EPOCH_REQUIRED")
    for name in (
        "apex_time_ns",
        "safe_watermark_ns",
        "current_guard_ns",
        "clock_uncertainty_ns",
        "past_grace_ns",
        "future_horizon_ns",
    ):
        _require_uint(name, getattr(policy, name))
    if policy.safe_watermark_ns > policy.apex_time_ns:
        raise ValueError("SAFE_WATERMARK_CANNOT_EXCEED_APEX")
    if policy.current_guard_ns < policy.clock_uncertainty_ns:
        raise ValueError("CURRENT_GUARD_MUST_COVER_CLOCK_UNCERTAINTY")
    if not policy.envelope:
        raise ValueError("ENVELOPE_REQUIRED")
    if policy.envelope[0].future_offset_ns != 0:
        raise ValueError("ENVELOPE_MUST_START_AT_ZERO")
    if policy.envelope[-1].future_offset_ns != policy.future_horizon_ns:
        raise ValueError("ENVELOPE_MUST_END_AT_HORIZON")

    previous_offset = -1
    previous_protected = -1
    previous_side_width: int | None = None
    for knot in policy.envelope:
        _require_uint("future_offset_ns", knot.future_offset_ns)
        _require_uint("protected_radius_uint", knot.protected_radius_uint)
        _require_uint("candidate_radius_uint", knot.candidate_radius_uint)
        if knot.future_offset_ns <= previous_offset:
            raise ValueError("ENVELOPE_OFFSETS_MUST_STRICTLY_INCREASE")
        if knot.protected_radius_uint > knot.candidate_radius_uint:
            raise ValueError("PROTECTED_RADIUS_EXCEEDS_CANDIDATE_RADIUS")
        if knot.protected_radius_uint < previous_protected:
            raise ValueError("FUTURE_PROTECTED_RADIUS_MUST_NOT_SHRINK")
        side_width = knot.side_cleanup_width_uint
        if previous_side_width is not None and side_width > previous_side_width:
            raise ValueError("FUTURE_SIDE_CLEANUP_WIDTH_MUST_NOT_GROW")
        previous_offset = knot.future_offset_ns
        previous_protected = knot.protected_radius_uint
        previous_side_width = side_width


def validate_apex_advance(previous: MovingVPolicy, current: MovingVPolicy) -> None:
    validate_policy(previous)
    validate_policy(current)
    if current.apex_time_ns < previous.apex_time_ns:
        raise ValueError("APEX_TIME_MUST_BE_MONOTONIC")
    if current.safe_watermark_ns < previous.safe_watermark_ns:
        raise ValueError("SAFE_WATERMARK_MUST_BE_MONOTONIC")


def aligned_safe_watermark(node_watermarks_ns: Iterable[int]) -> int:
    values = tuple(node_watermarks_ns)
    if not values:
        raise ValueError("ACTIVE_NODE_WATERMARK_REQUIRED")
    for value in values:
        _require_uint("node_watermark_ns", value)
    return min(values)


def envelope_at(policy: MovingVPolicy, delta_time_ns: int) -> EnvelopeKnot:
    validate_policy(policy)
    _require_uint("delta_time_ns", delta_time_ns)
    if delta_time_ns > policy.future_horizon_ns:
        raise ValueError("DELTA_TIME_OUT_OF_HORIZON")
    selected = policy.envelope[0]
    for knot in policy.envelope:
        if knot.future_offset_ns > delta_time_ns:
            break
        selected = knot
    return selected


def classify_record(policy: MovingVPolicy, record: MemoryRecord) -> Classification:
    validate_policy(policy)
    if not all(
        _is_uint(value)
        for value in (record.need_time_ns, record.event_time_ns, record.ingest_time_ns)
    ):
        return Classification(
            GeometryState.UNALIGNED_HOLD,
            "HOLD_INVALID_EVENT_INGEST_OR_NEED_TIME",
            0,
        )
    if (
        not isinstance(record.record_id, str)
        or not record.record_id
        or not _is_uint(record.record_version)
        or not isinstance(record.prediction_epoch, str)
        or not record.prediction_epoch
    ):
        return Classification(
            GeometryState.UNALIGNED_HOLD,
            "HOLD_INVALID_RECORD_BINDING",
            record.need_time_ns - policy.apex_time_ns,
        )
    delta_time_ns = record.need_time_ns - policy.apex_time_ns
    if record.ingest_time_ns > policy.apex_time_ns + policy.clock_uncertainty_ns:
        return Classification(
            GeometryState.UNALIGNED_HOLD,
            "HOLD_RECORD_ARRIVED_AFTER_CLASSIFICATION_APEX",
            delta_time_ns,
        )
    if record.prediction_epoch != policy.prediction_epoch:
        return Classification(
            GeometryState.UNALIGNED_HOLD,
            "HOLD_PREDICTION_EPOCH_MISMATCH",
            delta_time_ns,
        )
    if -policy.current_guard_ns <= delta_time_ns <= policy.current_guard_ns:
        return Classification(
            GeometryState.CURRENT_GUARD,
            "PROTECT_APEX_CURRENT_GUARD",
            delta_time_ns,
        )
    if delta_time_ns < -policy.current_guard_ns:
        if (
            record.event_time_ns <= policy.safe_watermark_ns
            and record.ingest_time_ns > policy.safe_watermark_ns
        ):
            return Classification(
                GeometryState.PAST_HOLD,
                "HOLD_LATE_EVENT_REQUIRES_WATERMARK_RECONCILIATION",
                delta_time_ns,
            )
        eligible_before = policy.safe_watermark_ns - policy.past_grace_ns
        if eligible_before < 0 or record.need_time_ns > eligible_before:
            return Classification(
                GeometryState.PAST_HOLD,
                "HOLD_PAST_NOT_BEYOND_SAFE_WATERMARK_AND_GRACE",
                delta_time_ns,
            )
        return Classification(
            GeometryState.PAST_ELIGIBLE,
            "PAST_BEYOND_SAFE_WATERMARK_AND_GRACE",
            delta_time_ns,
        )
    if delta_time_ns > policy.future_horizon_ns:
        return Classification(
            GeometryState.OUT_OF_HORIZON,
            "FUTURE_NOT_YET_EVALUATED_IS_NOT_A_MISS",
            delta_time_ns,
        )
    if (
        record.adi_absolute_distance_uint is None
        or not isinstance(record.adi_absolute_distance_uint, int)
        or isinstance(record.adi_absolute_distance_uint, bool)
        or record.adi_absolute_distance_uint < 0
    ):
        return Classification(
            GeometryState.UNALIGNED_HOLD,
            "HOLD_CANONICAL_ADI_DISTANCE_MISSING",
            delta_time_ns,
        )

    knot = envelope_at(policy, delta_time_ns)
    distance = record.adi_absolute_distance_uint
    if distance <= knot.protected_radius_uint:
        return Classification(
            GeometryState.FUTURE_PROTECTED,
            "PROTECT_INSIDE_MOVING_V_INCLUDING_BOUNDARY",
            delta_time_ns,
            knot.protected_radius_uint,
            knot.candidate_radius_uint,
        )
    if distance <= knot.candidate_radius_uint:
        return Classification(
            GeometryState.FUTURE_PREDICTED_MISS,
            "PREDICTED_MISS_ON_MANAGED_V_SIDE",
            delta_time_ns,
            knot.protected_radius_uint,
            knot.candidate_radius_uint,
        )
    return Classification(
        GeometryState.OUTSIDE_MANAGED_ENVELOPE_HOLD,
        "HOLD_OUTSIDE_FINITE_MANAGED_ENVELOPE",
        delta_time_ns,
        knot.protected_radius_uint,
        knot.candidate_radius_uint,
    )


def _reconstruction_gate_reason(record: MemoryRecord) -> str | None:
    if record.storage_tier not in MANAGED_STORAGE_TIERS:
        return "HOLD_UNKNOWN_STORAGE_TIER"
    if record.is_canonical_source:
        return "HOLD_CANONICAL_SOURCE_NEVER_CLEANED_BY_CANDIDATE"
    if not _is_uint(record.live_reference_count):
        return "HOLD_INVALID_LIVE_REFERENCE_COUNT"
    if record.live_reference_count != 0:
        return "HOLD_LIVE_REFERENCE"
    if record.active_lease:
        return "HOLD_ACTIVE_LEASE"
    if record.pinned:
        return "HOLD_PINNED_RECORD"
    if not record.durable_source_verified:
        return "HOLD_DURABLE_SOURCE_NOT_VERIFIED"
    if not record.reconstruction_reference:
        return "HOLD_GTP_OR_ADI_RECONSTRUCTION_REFERENCE_MISSING"
    if not _is_sha256(record.expected_source_hash) or not _is_sha256(
        record.observed_source_hash
    ):
        return "HOLD_SOURCE_HASH_MISSING"
    if record.expected_source_hash != record.observed_source_hash:
        return "HOLD_SOURCE_HASH_MISMATCH"
    return None


def evaluate_eviction(
    policy: MovingVPolicy,
    record: MemoryRecord,
    *,
    expected_record_version: int,
    expected_prediction_epoch: str,
) -> EvictionDecision:
    classification = classify_record(policy, record)
    base = {
        "record_id": record.record_id,
        "classification": classification.state,
        "destructive": False,
        "canonical_delete_allowed": False,
        "cas_prediction_epoch": expected_prediction_epoch,
        "cas_record_version": expected_record_version,
    }
    if expected_prediction_epoch != policy.prediction_epoch:
        return EvictionDecision(
            action=MemoryAction.KEEP_HOLD,
            reason="HOLD_CAS_PREDICTION_EPOCH_MISMATCH",
            **base,
        )
    if expected_record_version != record.record_version:
        return EvictionDecision(
            action=MemoryAction.KEEP_HOLD,
            reason="HOLD_CAS_RECORD_VERSION_MISMATCH",
            **base,
        )
    if classification.state is GeometryState.CURRENT_GUARD:
        return EvictionDecision(
            action=MemoryAction.PROTECT_CURRENT,
            reason=classification.reason,
            **base,
        )
    if classification.state is GeometryState.FUTURE_PROTECTED:
        return EvictionDecision(
            action=MemoryAction.PROTECT_PRELOAD,
            reason=classification.reason,
            **base,
        )
    if classification.state is GeometryState.OUT_OF_HORIZON:
        return EvictionDecision(
            action=MemoryAction.NO_PRELOAD_KEEP_REFERENCE,
            reason=classification.reason,
            **base,
        )
    if classification.state not in {
        GeometryState.PAST_ELIGIBLE,
        GeometryState.FUTURE_PREDICTED_MISS,
    }:
        return EvictionDecision(
            action=MemoryAction.KEEP_HOLD,
            reason=classification.reason,
            **base,
        )

    gate_reason = _reconstruction_gate_reason(record)
    if gate_reason:
        return EvictionDecision(
            action=MemoryAction.KEEP_HOLD,
            reason=gate_reason,
            **base,
        )
    if record.storage_tier in {
        "STATIC_PACKET",
        "ADI_INDEX_ONLY",
        "QUARANTINE",
        "EVICTED_REFERENCE",
    }:
        return EvictionDecision(
            action=MemoryAction.NOOP_REFERENCE_ONLY,
            reason="ALREADY_OUTSIDE_RAM_VRAM_WORKING_SET",
            **base,
        )
    if classification.state is GeometryState.PAST_ELIGIBLE:
        return EvictionDecision(
            action=MemoryAction.MOVE_TO_QUARANTINE,
            reason="PAST_SOFT_CLEAN_REQUIRES_QUARANTINE_COMMIT",
            **base,
        )
    return EvictionDecision(
        action=MemoryAction.SOFT_EVICT_RECONSTRUCTIBLE,
        reason="FUTURE_PREDICTED_MISS_SOFT_EVICTION_ONLY",
        **base,
    )


def plan_memory_pressure(
    policy: MovingVPolicy,
    records: Sequence[MemoryRecord],
    *,
    target_release_bytes: int,
    expected_versions: Mapping[str, int] | None = None,
) -> PressurePlan:
    _require_uint("target_release_bytes", target_release_bytes)
    expected_versions = expected_versions or {}
    candidates: list[tuple[int, int, MemoryRecord, EvictionDecision]] = []
    all_decisions: list[EvictionDecision] = []
    for record in records:
        decision = evaluate_eviction(
            policy,
            record,
            expected_record_version=expected_versions.get(record.record_id, record.record_version),
            expected_prediction_epoch=policy.prediction_epoch,
        )
        all_decisions.append(decision)
        if decision.action not in {
            MemoryAction.SOFT_EVICT_RECONSTRUCTIBLE,
            MemoryAction.MOVE_TO_QUARANTINE,
        }:
            continue
        _require_uint("resident_bytes", record.resident_bytes)
        priority = 0 if decision.classification is GeometryState.FUTURE_PREDICTED_MISS else 1
        distance_rank = -(record.adi_absolute_distance_uint or 0)
        candidates.append((priority, distance_rank, record, decision))

    candidates.sort(key=lambda item: (item[0], item[1], item[2].record_id.encode("utf-8")))
    selected: list[str] = []
    released = 0
    for _, _, record, _ in candidates:
        if released >= target_release_bytes:
            break
        selected.append(record.record_id)
        released += record.resident_bytes

    selected_set = set(selected)
    protected_violation = any(
        decision.record_id in selected_set
        and decision.classification in {GeometryState.CURRENT_GUARD, GeometryState.FUTURE_PROTECTED}
        for decision in all_decisions
    )
    state = "PASS_PRESSURE_PLAN" if released >= target_release_bytes else "BACKPRESSURE_REQUIRED"
    return PressurePlan(
        state=state,
        target_release_bytes=target_release_bytes,
        planned_release_bytes=released,
        selected_record_ids=tuple(selected),
        decisions=tuple(all_decisions),
        protected_eviction_violation=protected_violation,
    )


def false_miss_receipt(
    decision: EvictionDecision,
    *,
    actual_hit: bool,
    reconstructed_hash_matches: bool,
) -> str:
    if decision.classification is not GeometryState.FUTURE_PREDICTED_MISS or not actual_hit:
        return "NOT_A_FALSE_MISS"
    if not reconstructed_hash_matches:
        return "HOLD_RECONSTRUCTION_HASH_MISMATCH"
    return "FALSE_MISS_REHYDRATED_AND_RECORDED"


def evaluate_budget_adjustment_candidate(
    *,
    current_limit_bytes: int,
    proposed_limit_bytes: int,
    gate: BudgetPerformanceGate,
    evidence: BudgetPerformanceEvidence,
) -> BudgetAdjustmentDecision:
    """Evaluate evidence only; never apply or authorize a memory limit change."""
    _require_uint("current_limit_bytes", current_limit_bytes)
    _require_uint("proposed_limit_bytes", proposed_limit_bytes)
    for name, value in vars(gate).items():
        _require_uint(name, value)
    for name, value in vars(evidence).items():
        if name == "swap_thrashing":
            if not isinstance(value, bool):
                return BudgetAdjustmentDecision(
                    "HOLD_BUDGET_ADJUSTMENT",
                    current_limit_bytes,
                    proposed_limit_bytes,
                    "HOLD_INVALID_SWAP_THRASHING_FLAG",
                )
            continue
        _require_uint(name, value)
    if proposed_limit_bytes == 0:
        reason = "HOLD_PROPOSED_LIMIT_MUST_BE_POSITIVE"
    elif evidence.sample_count_uint < gate.min_sample_count_uint:
        reason = "HOLD_INSUFFICIENT_PERFORMANCE_SAMPLES"
    elif evidence.observation_ns_uint < gate.min_observation_ns_uint:
        reason = "HOLD_INSUFFICIENT_OBSERVATION_DURATION"
    elif proposed_limit_bytes < evidence.protected_working_set_bytes_uint:
        reason = "HOLD_PROPOSED_LIMIT_BELOW_PROTECTED_WORKING_SET"
    elif (
        evidence.host_available_after_adjustment_bytes_uint
        < gate.min_host_reserve_bytes_uint
    ):
        reason = "HOLD_HOST_RESERVE_TOO_LOW"
    elif evidence.oom_event_count_uint != 0:
        reason = "HOLD_OOM_EVENT_OBSERVED"
    elif evidence.swap_thrashing:
        reason = "HOLD_SWAP_THRASHING_OBSERVED"
    elif evidence.protected_eviction_violation_count_uint != 0:
        reason = "HOLD_PROTECTED_EVICTION_VIOLATION"
    elif evidence.reconstruction_hash_mismatch_count_uint != 0:
        reason = "HOLD_RECONSTRUCTION_HASH_MISMATCH"
    elif (
        evidence.p95_latency_regression_bp_uint
        > gate.max_p95_latency_regression_bp_uint
    ):
        reason = "HOLD_P95_LATENCY_REGRESSION"
    elif evidence.false_miss_rate_bp_uint > gate.max_false_miss_rate_bp_uint:
        reason = "HOLD_FALSE_MISS_RATE_TOO_HIGH"
    elif evidence.preload_hit_rate_bp_uint < gate.min_preload_hit_rate_bp_uint:
        reason = "HOLD_PRELOAD_HIT_RATE_TOO_LOW"
    else:
        return BudgetAdjustmentDecision(
            "PASS_BUDGET_ADJUSTMENT_CANDIDATE_ONLY",
            current_limit_bytes,
            proposed_limit_bytes,
            "PERFORMANCE_GATES_PASS_REQUIRES_SEPARATE_TOTAL_FIELD_AUTHORIZATION",
            False,
        )
    return BudgetAdjustmentDecision(
        "HOLD_BUDGET_ADJUSTMENT",
        current_limit_bytes,
        proposed_limit_bytes,
        reason,
        False,
    )


__all__ = [
    "Classification",
    "BudgetAdjustmentDecision",
    "BudgetPerformanceEvidence",
    "BudgetPerformanceGate",
    "EnvelopeKnot",
    "EvictionDecision",
    "GeometryState",
    "MemoryAction",
    "MemoryRecord",
    "MovingVPolicy",
    "PressurePlan",
    "aligned_safe_watermark",
    "classify_record",
    "envelope_at",
    "evaluate_budget_adjustment_candidate",
    "evaluate_eviction",
    "false_miss_receipt",
    "plan_memory_pressure",
    "validate_apex_advance",
    "validate_policy",
]
