"""Pure V2 candidate for time-staged moving-V route cleanup.

This module is deliberately non-live.  It performs deterministic validation,
classification, planning, and receipt simulation only.  It never reads a
clock, mutates memory, cancels a job, deletes a file, or grants authority.

The founder clarification implemented here is that time anchors a three-stage
file lifecycle:

1. PREDICTED_NOT_GENERATED
2. GENERATION_SCHEDULED_OR_RUNNING
3. GENERATION_COMPLETED

Route evidence and moving-V geometry select a safe action *within* a stage.
Future time by itself is neither a deletion proof nor a protection proof.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import Enum
import hashlib
import json
from typing import Iterable, Mapping, Sequence


SHA256_ZERO = "0" * 64
VOLATILE_TIERS = frozenset({"RAM_HEAP", "RAM_PINNED", "VRAM_KV_PAGE"})


class FileStage(str, Enum):
    PREDICTED_NOT_GENERATED = "PREDICTED_NOT_GENERATED"
    GENERATION_SCHEDULED_OR_RUNNING = "GENERATION_SCHEDULED_OR_RUNNING"
    GENERATION_COMPLETED = "GENERATION_COMPLETED"


class GenerationJobState(str, Enum):
    NONE = "NONE"
    SCHEDULED = "SCHEDULED"
    RUNNING = "RUNNING"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCEL_CONFIRMED = "CANCEL_CONFIRMED"
    COMPLETED = "COMPLETED"


class RouteProofType(str, Enum):
    REACHABLE_PATH_PROOF = "REACHABLE_PATH_PROOF"
    ROUTE_PREDICTION_RECEIPT = "ROUTE_PREDICTION_RECEIPT"
    ROUTE_EXCLUSION_PROOF = "ROUTE_EXCLUSION_PROOF"
    PREDICTION_INVALIDATION_PROOF = "PREDICTION_INVALIDATION_PROOF"


class ClassificationState(str, Enum):
    CURRENT_GUARD = "CURRENT_GUARD"
    PAST_ELIGIBLE = "PAST_ELIGIBLE"
    PAST_HOLD = "PAST_HOLD"
    FUTURE_REACHABLE_V_PROTECTED = "FUTURE_REACHABLE_V_PROTECTED"
    FUTURE_REACHABLE_REFERENCE_ONLY = "FUTURE_REACHABLE_REFERENCE_ONLY"
    FUTURE_ROUTE_PREDICTED_MISS = "FUTURE_ROUTE_PREDICTED_MISS"
    FUTURE_ROUTE_EXCLUDED = "FUTURE_ROUTE_EXCLUDED"
    FUTURE_PREDICTION_INVALIDATED = "FUTURE_PREDICTION_INVALIDATED"
    FUTURE_UNKNOWN_HOLD = "FUTURE_UNKNOWN_HOLD"
    OUT_OF_HORIZON_HOLD = "OUT_OF_HORIZON_HOLD"
    PROOF_CONFLICT_HOLD = "PROOF_CONFLICT_HOLD"
    UNALIGNED_HOLD = "UNALIGNED_HOLD"


class PlannedAction(str, Enum):
    PROTECT_CURRENT = "PROTECT_CURRENT"
    PROTECT_PRELOAD_CANDIDATE = "PROTECT_PRELOAD_CANDIDATE"
    CONTINUE_PROTECTED_GENERATION = "CONTINUE_PROTECTED_GENERATION"
    PROTECT_COMPLETED_MATERIALIZATION = "PROTECT_COMPLETED_MATERIALIZATION"
    KEEP_REFERENCE_ONLY = "KEEP_REFERENCE_ONLY"
    KEEP_HOLD = "KEEP_HOLD"
    CANCEL_PREDICTED_CANDIDATE = "CANCEL_PREDICTED_CANDIDATE"
    REQUEST_GENERATION_CANCELLATION = "REQUEST_GENERATION_CANCELLATION"
    CLEAN_CANCELLED_GENERATION_TEMP = "CLEAN_CANCELLED_GENERATION_TEMP"
    SOFT_EVICT_RECONSTRUCTIBLE = "SOFT_EVICT_RECONSTRUCTIBLE"
    DELETE_NONCANONICAL_DERIVED_MATERIALIZATION = (
        "DELETE_NONCANONICAL_DERIVED_MATERIALIZATION"
    )
    DETACH_BRANCH_REFERENCE_RETAIN_CANONICAL = (
        "DETACH_BRANCH_REFERENCE_RETAIN_CANONICAL"
    )
    MOVE_PAST_MATERIALIZATION_TO_QUARANTINE = (
        "MOVE_PAST_MATERIALIZATION_TO_QUARANTINE"
    )


PHYSICAL_RECLAIM_ACTIONS = frozenset(
    {
        PlannedAction.CLEAN_CANCELLED_GENERATION_TEMP,
        PlannedAction.SOFT_EVICT_RECONSTRUCTIBLE,
        PlannedAction.DELETE_NONCANONICAL_DERIVED_MATERIALIZATION,
    }
)

BRANCH_INVALIDATION_ELIGIBLE_ACTIONS = frozenset(
    {
        PlannedAction.CANCEL_PREDICTED_CANDIDATE,
        PlannedAction.REQUEST_GENERATION_CANCELLATION,
        PlannedAction.CLEAN_CANCELLED_GENERATION_TEMP,
        PlannedAction.DELETE_NONCANONICAL_DERIVED_MATERIALIZATION,
        PlannedAction.DETACH_BRANCH_REFERENCE_RETAIN_CANONICAL,
    }
)


@dataclass(frozen=True)
class EnvelopeKnot:
    future_offset_ns: int
    protected_radius_uint: int
    candidate_radius_uint: int

    @property
    def side_width_uint(self) -> int:
        return self.candidate_radius_uint - self.protected_radius_uint


@dataclass(frozen=True)
class RequiredNode:
    node_id: str
    boot_id: str
    clock_id: str


@dataclass(frozen=True)
class WatermarkObservation:
    node_id: str
    boot_id: str
    clock_id: str
    membership_epoch: str
    event_watermark_ns: int
    observed_at_ns: int
    valid_until_ns: int
    clock_uncertainty_ns: int
    attested: bool = True


@dataclass(frozen=True)
class WatermarkMembershipReceipt:
    receipt_id: str
    membership_epoch: str
    required_nodes: tuple[RequiredNode, ...]
    observations: tuple[WatermarkObservation, ...]
    partition_state: str = "HEALTHY"


@dataclass(frozen=True)
class MovingVRoutePolicy:
    policy_id: str
    policy_epoch: str
    prediction_epoch: str
    route_epoch: str
    membership_epoch: str
    time_domain_id: str
    route_graph_root: str
    route_ruleset_root: str
    apex_time_ns: int
    current_guard_ns: int
    clock_uncertainty_ns: int
    past_grace_ns: int
    future_horizon_ns: int
    envelope: tuple[EnvelopeKnot, ...]
    shadow_only: bool = True


@dataclass(frozen=True)
class RouteProof:
    proof_id: str
    proof_type: RouteProofType
    prediction_epoch: str
    route_epoch: str
    route_graph_root: str
    route_ruleset_root: str
    start_state_root: str
    target_state_or_predicate_hash: str
    valid_from_ns: int
    valid_until_ns: int
    need_time_start_ns: int
    need_time_end_ns: int
    constraint_root: str
    closed_world_declared: bool
    verifier_id: str
    verifier_hash: str
    proof_payload_hash: str
    proof_hash: str
    verification_state: str
    covered_materialization_bindings: tuple[str, ...]
    descendant_closure_root: str
    closure_receipt_hash: str
    closure_verification_state: str
    replay_complete: bool = False
    frontier_complete: bool = False
    actual_outcome_ref: str = ""
    branch_id: str = ""
    descendant_materialization_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class FileRecord:
    namespace: str
    record_id: str
    record_version: int
    materialization_id: str
    physical_allocation_id: str
    content_hash: str
    time_domain_id: str
    logical_time: int
    stage: FileStage
    stage_entered_at_ns: int
    stage_observed_at_ns: int
    stage_sequence: int
    stage_state_hash: str
    need_time_ns: int
    event_time_ns: int
    ingest_time_ns: int
    ingest_seq: int
    classification_snapshot_ingest_seq: int
    late_event_reconciled: bool
    late_event_reconciliation_receipt_hash: str
    classification_snapshot_receipt_hash: str
    adi_delta_f_uint: int | None
    prediction_epoch: str
    route_epoch: str
    generation_job_id: str = ""
    generation_job_state: GenerationJobState = GenerationJobState.NONE
    stage_transition_receipt_hash: str = ""
    stage_transition_verified: bool = False
    cancellation_receipt_hash: str = ""
    cancellation_outcome: str = ""
    worker_fence_receipt_hash: str = ""
    worker_fence_state: str = ""
    completion_receipt_hash: str = ""
    storage_tier: str = "REFERENCE_ONLY"
    measured_resident_bytes: int = 0
    generation_token: str = ""
    lifecycle_snapshot_token: str = ""
    live_reference_count: int = 0
    active_lease_count: int = 0
    pin_count: int = 0
    durable_reconstruction_verified: bool = False
    reconstruction_reference: str = ""
    expected_source_hash: str = ""
    observed_source_hash: str = ""
    is_canonical_source: bool = False
    is_derived_materialization: bool = True
    is_speculative_candidate: bool = False
    exclusive_to_branch: bool = True
    branch_id: str = ""
    canonical_parent_retained: bool = True
    legal_hold: bool = False
    retention_hold: bool = False

    @property
    def logical_record_key(self) -> str:
        return f"{self.namespace}:{self.record_id}:{self.record_version}"


@dataclass(frozen=True)
class StageTransitionReceipt:
    receipt_id: str
    record_id: str
    materialization_id: str
    from_stage: FileStage
    to_stage: FileStage
    transition_time_ns: int
    observed_time_ns: int
    stage_sequence: int
    generation_job_id: str
    time_domain_id: str
    logical_time: int
    expected_previous_state_hash: str
    resulting_state_hash: str
    idempotency_key: str
    transition_state: str
    receipt_hash: str


@dataclass(frozen=True)
class Classification:
    state: ClassificationState
    reason: str
    stage: FileStage
    delta_time_ns: int
    safe_watermark_ns: int | None = None
    protected_radius_uint: int | None = None
    candidate_radius_uint: int | None = None
    governing_proof_hash: str = ""


@dataclass(frozen=True)
class ActionDecision:
    record_id: str
    materialization_id: str
    physical_allocation_id: str
    stage: FileStage
    classification: ClassificationState
    action: PlannedAction
    reason: str
    proof_hash: str
    expected_release_upper_bound_bytes: int
    canonical_action: str = "RETAIN"
    applies_live_change: bool = False


@dataclass(frozen=True)
class BranchInvalidationPlan:
    state: str
    branch_id: str
    proof_hash: str
    decisions: tuple[ActionDecision, ...]
    planned_release_upper_bound_bytes: int
    graph_closure_complete: bool
    action_plan_terminal: bool = False
    cleanup_commit_complete: bool = False
    atomic_commit_required: bool = True
    applies_live_change: bool = False


@dataclass(frozen=True)
class PressurePlan:
    state: str
    target_release_bytes: int
    planned_release_upper_bound_bytes: int
    selected_materialization_ids: tuple[str, ...]
    selected_physical_allocation_ids: tuple[str, ...]
    decisions: tuple[ActionDecision, ...]
    applies_live_change: bool = False


@dataclass(frozen=True)
class DecisionToken:
    decision_id: str
    idempotency_key: str
    materialization_id: str
    physical_allocation_id: str
    action: PlannedAction
    classification: ClassificationState
    record_version: int
    stage: FileStage
    generation_job_state: GenerationJobState
    generation_token: str
    lifecycle_snapshot_token: str
    policy_epoch: str
    prediction_epoch: str
    route_epoch: str
    route_graph_root: str
    proof_hash: str
    expected_content_hash: str
    safety_state_hash: str
    allocation_owner_set_hash: str
    expected_release_upper_bound_bytes: int
    expires_at_ns: int
    token_hash: str


@dataclass(frozen=True)
class CommitReceipt:
    receipt_id: str
    idempotency_key: str
    decision_id: str
    token_hash: str
    materialization_id: str
    expected_content_hash: str
    prediction_epoch: str
    route_epoch: str
    committed_action: PlannedAction
    classification: ClassificationState
    cas_result: str
    actual_released_bytes: int
    commit_time_ns: int
    simulation_only: bool
    failure_code: str | None
    receipt_hash: str


@dataclass(frozen=True)
class BudgetPerformanceGate:
    min_sample_count: int
    min_observation_ns: int
    min_host_reserve_bytes: int
    max_p95_latency_regression_bp: int
    max_p99_latency_regression_bp: int
    max_ttft_p95_regression_bp: int
    max_rehydration_stall_p99_ns: int
    max_false_miss_rate_bp: int
    min_preload_hit_rate_bp: int
    max_task_success_regression_bp: int
    max_tool_success_regression_bp: int


@dataclass(frozen=True)
class BudgetPerformanceEvidence:
    sample_count: int
    observation_ns: int
    host_capacity_bytes: int
    host_available_after_adjustment_bytes: int
    protected_working_set_bytes: int
    p95_latency_regression_bp: int
    p99_latency_regression_bp: int
    ttft_p95_regression_bp: int
    rehydration_stall_p99_ns: int
    false_miss_rate_bp: int
    preload_hit_rate_bp: int
    task_success_regression_bp: int
    tool_success_regression_bp: int
    oom_event_count: int = 0
    swap_thrashing: bool = False
    protected_eviction_violation_count: int = 0
    reconstruction_hash_mismatch_count: int = 0


@dataclass(frozen=True)
class BudgetAdjustmentDecision:
    state: str
    current_limit_bytes: int
    proposed_limit_bytes: int
    reason: str
    applies_change: bool = False


def _is_uint(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _require_uint(name: str, value: int) -> None:
    if not _is_uint(value):
        raise ValueError(f"{name}_MUST_BE_UINT")


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _hash_object(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def materialization_binding(record: FileRecord) -> str:
    return f"{record.materialization_id}:{record.content_hash}"


def route_proof_binding_hash(proof: RouteProof) -> str:
    """Hash every static proof binding except the hash field itself.

    This is an integrity check, not a replacement for the external verifier
    attestation required by a live adapter.
    """
    body = {
        "proof_id": proof.proof_id,
        "proof_type": proof.proof_type.value,
        "prediction_epoch": proof.prediction_epoch,
        "route_epoch": proof.route_epoch,
        "route_graph_root": proof.route_graph_root,
        "route_ruleset_root": proof.route_ruleset_root,
        "start_state_root": proof.start_state_root,
        "target_state_or_predicate_hash": proof.target_state_or_predicate_hash,
        "valid_from_ns": proof.valid_from_ns,
        "valid_until_ns": proof.valid_until_ns,
        "need_time_start_ns": proof.need_time_start_ns,
        "need_time_end_ns": proof.need_time_end_ns,
        "constraint_root": proof.constraint_root,
        "closed_world_declared": proof.closed_world_declared,
        "verifier_id": proof.verifier_id,
        "verifier_hash": proof.verifier_hash,
        "proof_payload_hash": proof.proof_payload_hash,
        "verification_state": proof.verification_state,
        "covered_materialization_bindings": sorted(
            proof.covered_materialization_bindings
        ),
        "descendant_closure_root": proof.descendant_closure_root,
        "closure_receipt_hash": proof.closure_receipt_hash,
        "closure_verification_state": proof.closure_verification_state,
        "replay_complete": proof.replay_complete,
        "frontier_complete": proof.frontier_complete,
        "actual_outcome_ref": proof.actual_outcome_ref,
        "branch_id": proof.branch_id,
        "descendant_materialization_ids": sorted(
            proof.descendant_materialization_ids
        ),
    }
    return _hash_object(body)


def validate_policy(policy: MovingVRoutePolicy) -> None:
    if not all(
        isinstance(value, str) and value
        for value in (
            policy.policy_id,
            policy.policy_epoch,
            policy.prediction_epoch,
            policy.route_epoch,
            policy.membership_epoch,
            policy.time_domain_id,
        )
    ):
        raise ValueError("POLICY_BINDINGS_REQUIRED")
    if not _is_sha256(policy.route_graph_root) or not _is_sha256(
        policy.route_ruleset_root
    ):
        raise ValueError("ROUTE_ROOTS_MUST_BE_SHA256")
    for name in (
        "apex_time_ns",
        "current_guard_ns",
        "clock_uncertainty_ns",
        "past_grace_ns",
        "future_horizon_ns",
    ):
        _require_uint(name, getattr(policy, name))
    if policy.shadow_only is not True:
        raise ValueError("CANDIDATE_MUST_REMAIN_SHADOW_ONLY")
    if policy.current_guard_ns < policy.clock_uncertainty_ns:
        raise ValueError("CURRENT_GUARD_MUST_COVER_CLOCK_UNCERTAINTY")
    if policy.current_guard_ns >= policy.future_horizon_ns:
        raise ValueError("FUTURE_HORIZON_MUST_EXCEED_CURRENT_GUARD")
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
        for name in (
            "future_offset_ns",
            "protected_radius_uint",
            "candidate_radius_uint",
        ):
            _require_uint(name, getattr(knot, name))
        if knot.future_offset_ns <= previous_offset:
            raise ValueError("ENVELOPE_OFFSETS_MUST_STRICTLY_INCREASE")
        if knot.protected_radius_uint > knot.candidate_radius_uint:
            raise ValueError("PROTECTED_RADIUS_EXCEEDS_CANDIDATE_RADIUS")
        if knot.protected_radius_uint < previous_protected:
            raise ValueError("FUTURE_PROTECTED_RADIUS_MUST_NOT_SHRINK")
        if previous_side_width is not None and knot.side_width_uint > previous_side_width:
            raise ValueError("FUTURE_SIDE_WIDTH_MUST_NOT_GROW")
        previous_offset = knot.future_offset_ns
        previous_protected = knot.protected_radius_uint
        previous_side_width = knot.side_width_uint


def validate_apex_advance(
    previous: MovingVRoutePolicy, current: MovingVRoutePolicy
) -> None:
    validate_policy(previous)
    validate_policy(current)
    if (
        current.time_domain_id == previous.time_domain_id
        and current.apex_time_ns < previous.apex_time_ns
    ):
        raise ValueError("APEX_TIME_MUST_BE_MONOTONIC")
    if current.policy_epoch == previous.policy_epoch and (
        current.time_domain_id != previous.time_domain_id
        or current.membership_epoch != previous.membership_epoch
        or current.route_epoch != previous.route_epoch
        or current.prediction_epoch != previous.prediction_epoch
        or current.route_graph_root != previous.route_graph_root
        or current.route_ruleset_root != previous.route_ruleset_root
    ):
        raise ValueError("ROOT_OR_EPOCH_CHANGE_REQUIRES_NEW_POLICY_EPOCH")


def envelope_at(policy: MovingVRoutePolicy, delta_time_ns: int) -> EnvelopeKnot:
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


def aligned_safe_watermark(
    receipt: WatermarkMembershipReceipt,
    *,
    expected_membership_epoch: str,
    now_ns: int,
) -> int:
    _require_uint("now_ns", now_ns)
    if receipt.membership_epoch != expected_membership_epoch:
        raise ValueError("MEMBERSHIP_EPOCH_MISMATCH")
    if receipt.partition_state != "HEALTHY":
        raise ValueError("PARTITION_STATE_HOLD")
    if not receipt.required_nodes:
        raise ValueError("REQUIRED_NODE_SET_EMPTY")
    required: dict[str, RequiredNode] = {}
    for node in receipt.required_nodes:
        if not node.node_id or node.node_id in required:
            raise ValueError("DUPLICATE_OR_EMPTY_REQUIRED_NODE")
        required[node.node_id] = node
    observed: dict[str, WatermarkObservation] = {}
    for item in receipt.observations:
        if not item.node_id or item.node_id in observed:
            raise ValueError("DUPLICATE_OR_EMPTY_WATERMARK_OBSERVATION")
        observed[item.node_id] = item
    if set(observed) != set(required):
        raise ValueError("REQUIRED_NODE_MEMBERSHIP_NOT_EXACT")
    safe_values: list[int] = []
    for node_id, required_node in required.items():
        item = observed[node_id]
        if (
            item.boot_id != required_node.boot_id
            or item.clock_id != required_node.clock_id
            or item.membership_epoch != expected_membership_epoch
        ):
            raise ValueError("NODE_BOOT_CLOCK_OR_MEMBERSHIP_MISMATCH")
        if item.attested is not True:
            raise ValueError("UNATTESTED_WATERMARK")
        for name in (
            "event_watermark_ns",
            "observed_at_ns",
            "valid_until_ns",
            "clock_uncertainty_ns",
        ):
            _require_uint(name, getattr(item, name))
        if item.observed_at_ns > now_ns or item.valid_until_ns < now_ns:
            raise ValueError("STALE_OR_FUTURE_WATERMARK_OBSERVATION")
        if item.clock_uncertainty_ns > item.event_watermark_ns:
            raise ValueError("WATERMARK_UNCERTAINTY_UNDERFLOW")
        safe_values.append(item.event_watermark_ns - item.clock_uncertainty_ns)
    return min(safe_values)


def validate_stage_record(record: FileRecord) -> str | None:
    if not isinstance(record.stage, FileStage) or not isinstance(
        record.generation_job_state, GenerationJobState
    ):
        return "HOLD_STAGE_OR_JOB_STATE_ENUM_INVALID"
    for flag_name in (
        "late_event_reconciled",
        "stage_transition_verified",
        "durable_reconstruction_verified",
        "is_canonical_source",
        "is_derived_materialization",
        "is_speculative_candidate",
        "exclusive_to_branch",
        "canonical_parent_retained",
        "legal_hold",
        "retention_hold",
    ):
        if not isinstance(getattr(record, flag_name), bool):
            return f"HOLD_{flag_name.upper()}_FLAG_INVALID"
    if not all(
        isinstance(value, str) and value
        for value in (
            record.namespace,
            record.record_id,
            record.materialization_id,
            record.physical_allocation_id,
            record.time_domain_id,
        )
    ):
        return "HOLD_RECORD_IDENTIFIERS_REQUIRED"
    if not _is_sha256(record.content_hash):
        return "HOLD_CONTENT_HASH_INVALID"
    for name in (
        "record_version",
        "logical_time",
        "stage_entered_at_ns",
        "stage_observed_at_ns",
        "stage_sequence",
        "need_time_ns",
        "event_time_ns",
        "ingest_time_ns",
        "ingest_seq",
        "classification_snapshot_ingest_seq",
        "measured_resident_bytes",
        "live_reference_count",
        "active_lease_count",
        "pin_count",
    ):
        if not _is_uint(getattr(record, name)):
            return f"HOLD_{name.upper()}_INVALID"
    if record.event_time_ns > record.ingest_time_ns:
        return "HOLD_EVENT_TIME_AFTER_INGEST_TIME"
    if not (
        record.stage_entered_at_ns
        <= record.stage_observed_at_ns
        <= record.ingest_time_ns
    ):
        return "HOLD_STAGE_EFFECTIVE_OBSERVED_OR_INGEST_TIME_ORDER"
    if not _is_sha256(record.stage_state_hash):
        return "HOLD_STAGE_STATE_HASH_INVALID"
    if not isinstance(record.stage_transition_verified, bool):
        return "HOLD_STAGE_TRANSITION_VERIFICATION_FLAG_INVALID"
    if record.stage is FileStage.PREDICTED_NOT_GENERATED:
        if record.generation_job_state is not GenerationJobState.NONE:
            return "HOLD_NOT_GENERATED_STAGE_HAS_JOB_STATE"
        if record.generation_job_id or record.completion_receipt_hash:
            return "HOLD_NOT_GENERATED_STAGE_HAS_JOB_OR_COMPLETION"
        if record.stage_sequence != 0 or record.stage_transition_verified:
            return "HOLD_NOT_GENERATED_STAGE_SEQUENCE_OR_TRANSITION_INVALID"
    elif record.stage is FileStage.GENERATION_SCHEDULED_OR_RUNNING:
        if not record.generation_job_id:
            return "HOLD_SCHEDULED_STAGE_JOB_ID_REQUIRED"
        if record.generation_job_state not in {
            GenerationJobState.SCHEDULED,
            GenerationJobState.RUNNING,
            GenerationJobState.CANCEL_REQUESTED,
            GenerationJobState.CANCEL_CONFIRMED,
        }:
            return "HOLD_SCHEDULED_STAGE_JOB_STATE_INVALID"
        if not _is_sha256(record.stage_transition_receipt_hash):
            return "HOLD_SCHEDULED_STAGE_TRANSITION_RECEIPT_REQUIRED"
        if not record.stage_transition_verified or record.stage_sequence < 1:
            return "HOLD_SCHEDULED_STAGE_TRANSITION_NOT_VERIFIED"
        if (
            record.generation_job_state is GenerationJobState.CANCEL_CONFIRMED
            and (
                not _is_sha256(record.cancellation_receipt_hash)
                or not _is_sha256(record.worker_fence_receipt_hash)
                or record.cancellation_outcome
                not in {"CANCELLED_BEFORE_START", "CANCELLED_DURING_RUN"}
                or record.worker_fence_state != "QUIESCED"
            )
        ):
            return "HOLD_CANCELLATION_AND_WORKER_FENCE_RECEIPTS_REQUIRED"
    elif record.stage is FileStage.GENERATION_COMPLETED:
        if record.generation_job_state is not GenerationJobState.COMPLETED:
            return "HOLD_COMPLETED_STAGE_JOB_STATE_INVALID"
        if not record.generation_job_id:
            return "HOLD_COMPLETED_STAGE_JOB_ID_REQUIRED"
        if not _is_sha256(record.stage_transition_receipt_hash) or not _is_sha256(
            record.completion_receipt_hash
        ):
            return "HOLD_COMPLETION_RECEIPTS_REQUIRED"
        if not record.stage_transition_verified or record.stage_sequence < 2:
            return "HOLD_COMPLETED_STAGE_TRANSITION_NOT_VERIFIED"
    return None


def validate_stage_transition(
    previous: FileRecord,
    current: FileRecord,
    receipt: StageTransitionReceipt,
) -> None:
    previous_reason = validate_stage_record(previous)
    current_reason = validate_stage_record(current)
    if previous_reason or current_reason:
        raise ValueError("STAGE_TRANSITION_RECORD_INVALID")
    if previous.record_id != current.record_id or previous.materialization_id != current.materialization_id:
        raise ValueError("STAGE_TRANSITION_RECORD_MISMATCH")
    if receipt.record_id != current.record_id or receipt.materialization_id != current.materialization_id:
        raise ValueError("STAGE_TRANSITION_RECEIPT_RECORD_MISMATCH")
    if receipt.from_stage is not previous.stage or receipt.to_stage is not current.stage:
        raise ValueError("STAGE_TRANSITION_RECEIPT_STAGE_MISMATCH")
    allowed = {
        (
            FileStage.PREDICTED_NOT_GENERATED,
            FileStage.GENERATION_SCHEDULED_OR_RUNNING,
        ),
        (
            FileStage.GENERATION_SCHEDULED_OR_RUNNING,
            FileStage.GENERATION_COMPLETED,
        ),
    }
    if (previous.stage, current.stage) not in allowed:
        raise ValueError("ILLEGAL_STAGE_TRANSITION")
    if (
        receipt.transition_state != "PASS"
        or not _is_sha256(receipt.receipt_hash)
        or receipt.transition_time_ns != current.stage_entered_at_ns
        or receipt.observed_time_ns != current.stage_observed_at_ns
        or receipt.observed_time_ns < receipt.transition_time_ns
        or receipt.transition_time_ns < previous.stage_entered_at_ns
        or receipt.stage_sequence != previous.stage_sequence + 1
        or receipt.stage_sequence != current.stage_sequence
        or receipt.generation_job_id != current.generation_job_id
        or receipt.time_domain_id != current.time_domain_id
        or not _is_uint(receipt.logical_time)
        or receipt.logical_time != current.logical_time
        or receipt.logical_time <= previous.logical_time
        or receipt.expected_previous_state_hash != previous.stage_state_hash
        or receipt.resulting_state_hash != current.stage_state_hash
        or not receipt.idempotency_key
        or receipt.receipt_hash != current.stage_transition_receipt_hash
    ):
        raise ValueError("INVALID_STAGE_TRANSITION_RECEIPT")


def _proof_validity_reason(
    policy: MovingVRoutePolicy, record: FileRecord, proof: RouteProof
) -> str | None:
    if not isinstance(proof.proof_type, RouteProofType):
        return "PROOF_TYPE_INVALID"
    if proof.verification_state != "PASS":
        return "PROOF_VERIFICATION_NOT_PASS"
    if proof.prediction_epoch != policy.prediction_epoch or proof.prediction_epoch != record.prediction_epoch:
        return "PROOF_PREDICTION_EPOCH_MISMATCH"
    if proof.route_epoch != policy.route_epoch or proof.route_epoch != record.route_epoch:
        return "PROOF_ROUTE_EPOCH_MISMATCH"
    if (
        proof.route_graph_root != policy.route_graph_root
        or proof.route_ruleset_root != policy.route_ruleset_root
    ):
        return "PROOF_ROUTE_ROOT_MISMATCH"
    required_hashes = (
        proof.route_graph_root,
        proof.route_ruleset_root,
        proof.start_state_root,
        proof.target_state_or_predicate_hash,
        proof.constraint_root,
        proof.verifier_hash,
        proof.proof_payload_hash,
        proof.proof_hash,
    )
    if not proof.proof_id or not proof.verifier_id or not all(
        _is_sha256(value) for value in required_hashes
    ):
        return "PROOF_BINDING_OR_HASH_INVALID"
    if proof.proof_hash != route_proof_binding_hash(proof):
        return "PROOF_BINDING_HASH_MISMATCH"
    bindings = proof.covered_materialization_bindings
    if (
        not bindings
        or len(set(bindings)) != len(bindings)
        or materialization_binding(record) not in bindings
    ):
        return "PROOF_TARGET_MATERIALIZATION_OR_CONTENT_NOT_COVERED"
    parsed_bindings: dict[str, str] = {}
    for binding in bindings:
        if ":" not in binding:
            return "PROOF_MATERIALIZATION_BINDING_INVALID"
        materialization_id, content_hash = binding.rsplit(":", 1)
        if not materialization_id or not _is_sha256(content_hash):
            return "PROOF_MATERIALIZATION_BINDING_INVALID"
        if materialization_id in parsed_bindings:
            return "PROOF_DUPLICATE_MATERIALIZATION_BINDING"
        parsed_bindings[materialization_id] = content_hash
    for name in (
        "valid_from_ns",
        "valid_until_ns",
        "need_time_start_ns",
        "need_time_end_ns",
    ):
        if not _is_uint(getattr(proof, name)):
            return "PROOF_TIME_INVALID"
    if not (proof.valid_from_ns <= policy.apex_time_ns <= proof.valid_until_ns):
        return "PROOF_EXPIRED_OR_NOT_YET_VALID"
    if not (proof.need_time_start_ns <= record.need_time_ns <= proof.need_time_end_ns):
        return "PROOF_DOES_NOT_COVER_NEED_TIME"
    if (
        proof.proof_type is RouteProofType.REACHABLE_PATH_PROOF
        and proof.replay_complete is not True
    ):
        return "REACHABLE_PATH_NOT_REPLAY_COMPLETE"
    if proof.proof_type in {
        RouteProofType.ROUTE_EXCLUSION_PROOF,
        RouteProofType.PREDICTION_INVALIDATION_PROOF,
    } and (
        proof.closed_world_declared is not True
        or proof.frontier_complete is not True
    ):
        return "DESTRUCTIVE_PROOF_NOT_CLOSED_WORLD_COMPLETE"
    if proof.proof_type is RouteProofType.PREDICTION_INVALIDATION_PROOF:
        if (
            not proof.actual_outcome_ref
            or not proof.branch_id
            or proof.branch_id != record.branch_id
            or not proof.descendant_materialization_ids
            or len(set(proof.descendant_materialization_ids))
            != len(proof.descendant_materialization_ids)
            or not _is_sha256(proof.descendant_closure_root)
            or not _is_sha256(proof.closure_receipt_hash)
            or proof.closure_verification_state != "PASS"
        ):
            return "INVALIDATION_PROOF_CLOSURE_OR_OUTCOME_MISSING"
        if set(proof.descendant_materialization_ids) != set(parsed_bindings):
            return "INVALIDATION_DESCENDANTS_AND_CONTENT_BINDINGS_DIFFER"
    return None


def classify_record(
    policy: MovingVRoutePolicy,
    record: FileRecord,
    proofs: Sequence[RouteProof],
    watermark_receipt: WatermarkMembershipReceipt | None,
) -> Classification:
    validate_policy(policy)
    stage_reason = validate_stage_record(record)
    if stage_reason:
        return Classification(
            ClassificationState.UNALIGNED_HOLD,
            stage_reason,
            record.stage,
            record.need_time_ns - policy.apex_time_ns,
        )
    delta = record.need_time_ns - policy.apex_time_ns
    if record.ingest_time_ns > policy.apex_time_ns + policy.clock_uncertainty_ns:
        return Classification(
            ClassificationState.UNALIGNED_HOLD,
            "HOLD_RECORD_ARRIVED_AFTER_CLASSIFICATION_APEX",
            record.stage,
            delta,
        )
    if record.prediction_epoch != policy.prediction_epoch or record.route_epoch != policy.route_epoch:
        return Classification(
            ClassificationState.UNALIGNED_HOLD,
            "HOLD_PREDICTION_OR_ROUTE_EPOCH_MISMATCH",
            record.stage,
            delta,
        )
    if record.time_domain_id != policy.time_domain_id:
        return Classification(
            ClassificationState.UNALIGNED_HOLD,
            "HOLD_TIME_DOMAIN_MISMATCH",
            record.stage,
            delta,
        )
    if -policy.current_guard_ns <= delta <= policy.current_guard_ns:
        return Classification(
            ClassificationState.CURRENT_GUARD,
            "PROTECT_CURRENT_TIME_GUARD",
            record.stage,
            delta,
        )
    if delta < -policy.current_guard_ns:
        if watermark_receipt is None:
            return Classification(
                ClassificationState.PAST_HOLD,
                "HOLD_WATERMARK_RECEIPT_REQUIRED",
                record.stage,
                delta,
            )
        try:
            safe = aligned_safe_watermark(
                watermark_receipt,
                expected_membership_epoch=policy.membership_epoch,
                now_ns=policy.apex_time_ns,
            )
        except ValueError as error:
            return Classification(
                ClassificationState.PAST_HOLD,
                f"HOLD_WATERMARK_{error}",
                record.stage,
                delta,
            )
        if safe < policy.past_grace_ns:
            return Classification(
                ClassificationState.PAST_HOLD,
                "HOLD_PAST_CUT_UNDERFLOW",
                record.stage,
                delta,
                safe_watermark_ns=safe,
            )
        past_cut = safe - policy.past_grace_ns
        if not (
            record.need_time_ns <= past_cut
            and record.event_time_ns <= past_cut
            and record.ingest_seq <= record.classification_snapshot_ingest_seq
            and record.late_event_reconciled
            and _is_sha256(record.late_event_reconciliation_receipt_hash)
            and _is_sha256(record.classification_snapshot_receipt_hash)
        ):
            return Classification(
                ClassificationState.PAST_HOLD,
                "HOLD_PAST_EVENT_NEED_SNAPSHOT_OR_LATE_RECONCILIATION",
                record.stage,
                delta,
                safe_watermark_ns=safe,
            )
        return Classification(
            ClassificationState.PAST_ELIGIBLE,
            "PAST_EVENT_AND_NEED_BEYOND_ALIGNED_SAFE_CUT",
            record.stage,
            delta,
            safe_watermark_ns=safe,
        )
    if delta > policy.future_horizon_ns:
        return Classification(
            ClassificationState.OUT_OF_HORIZON_HOLD,
            "HOLD_FUTURE_OUTSIDE_FINITE_EVALUATION_HORIZON",
            record.stage,
            delta,
        )
    if not _is_uint(record.adi_delta_f_uint):
        return Classification(
            ClassificationState.UNALIGNED_HOLD,
            "HOLD_ADI_DELTA_F_PROOF_VALUE_REQUIRED",
            record.stage,
            delta,
        )
    knot = envelope_at(policy, delta)
    inside_v = record.adi_delta_f_uint <= knot.protected_radius_uint
    valid = [proof for proof in proofs if _proof_validity_reason(policy, record, proof) is None]
    kinds = {proof.proof_type for proof in valid}
    for proof_type in RouteProofType:
        hashes = {
            item.proof_hash for item in valid if item.proof_type is proof_type
        }
        if len(hashes) > 1:
            return Classification(
                ClassificationState.PROOF_CONFLICT_HOLD,
                "HOLD_MULTIPLE_GOVERNING_PROOFS_OF_SAME_TYPE",
                record.stage,
                delta,
            )
    reachable = RouteProofType.REACHABLE_PATH_PROOF in kinds
    excluded = RouteProofType.ROUTE_EXCLUSION_PROOF in kinds
    invalidated = RouteProofType.PREDICTION_INVALIDATION_PROOF in kinds
    predicted_miss = RouteProofType.ROUTE_PREDICTION_RECEIPT in kinds
    if (
        (reachable and (excluded or invalidated))
        or (excluded and invalidated)
        or (inside_v and (excluded or invalidated or predicted_miss))
    ):
        return Classification(
            ClassificationState.PROOF_CONFLICT_HOLD,
            "HOLD_MOVING_V_OR_ROUTE_PROOF_CONFLICT",
            record.stage,
            delta,
        )
    governing: RouteProof | None = None
    if invalidated:
        governing = next(
            proof
            for proof in valid
            if proof.proof_type is RouteProofType.PREDICTION_INVALIDATION_PROOF
        )
        if record.materialization_id not in governing.descendant_materialization_ids:
            return Classification(
                ClassificationState.FUTURE_UNKNOWN_HOLD,
                "HOLD_RECORD_NOT_IN_INVALIDATED_DESCENDANT_CLOSURE",
                record.stage,
                delta,
            )
        return Classification(
            ClassificationState.FUTURE_PREDICTION_INVALIDATED,
            "CONFIRMED_WRONG_PREDICTION_BRANCH",
            record.stage,
            delta,
            governing_proof_hash=governing.proof_hash,
        )
    if excluded:
        governing = next(
            proof
            for proof in valid
            if proof.proof_type is RouteProofType.ROUTE_EXCLUSION_PROOF
        )
        return Classification(
            ClassificationState.FUTURE_ROUTE_EXCLUDED,
            "CLOSED_WORLD_ROUTE_EXCLUSION_PROVEN",
            record.stage,
            delta,
            governing_proof_hash=governing.proof_hash,
        )
    if reachable:
        governing = next(
            proof
            for proof in valid
            if proof.proof_type is RouteProofType.REACHABLE_PATH_PROOF
        )
        if record.adi_delta_f_uint <= knot.protected_radius_uint:
            return Classification(
                ClassificationState.FUTURE_REACHABLE_V_PROTECTED,
                "REACHABLE_AND_INSIDE_MOVING_V",
                record.stage,
                delta,
                protected_radius_uint=knot.protected_radius_uint,
                candidate_radius_uint=knot.candidate_radius_uint,
                governing_proof_hash=governing.proof_hash,
            )
        return Classification(
            ClassificationState.FUTURE_REACHABLE_REFERENCE_ONLY,
            "REACHABLE_BUT_OUTSIDE_ACTIVE_PRELOAD_RADIUS",
            record.stage,
            delta,
            protected_radius_uint=knot.protected_radius_uint,
            candidate_radius_uint=knot.candidate_radius_uint,
            governing_proof_hash=governing.proof_hash,
        )
    predicted = [
        proof
        for proof in valid
        if proof.proof_type is RouteProofType.ROUTE_PREDICTION_RECEIPT
    ]
    if predicted:
        if record.adi_delta_f_uint > knot.candidate_radius_uint:
            return Classification(
                ClassificationState.FUTURE_UNKNOWN_HOLD,
                "HOLD_PREDICTED_MISS_OUTSIDE_FINITE_MANAGED_ENVELOPE",
                record.stage,
                delta,
                protected_radius_uint=knot.protected_radius_uint,
                candidate_radius_uint=knot.candidate_radius_uint,
            )
        return Classification(
            ClassificationState.FUTURE_ROUTE_PREDICTED_MISS,
            "PREDICTED_MISS_IS_NOT_AN_IMPOSSIBILITY_PROOF",
            record.stage,
            delta,
            governing_proof_hash=predicted[0].proof_hash,
        )
    invalid_reasons = sorted(
        {
            reason
            for proof in proofs
            if (reason := _proof_validity_reason(policy, record, proof)) is not None
        }
    )
    reason = "HOLD_ROUTE_EVIDENCE_UNKNOWN"
    if invalid_reasons:
        reason += ":" + ",".join(invalid_reasons)
    return Classification(
        ClassificationState.FUTURE_UNKNOWN_HOLD,
        reason,
        record.stage,
        delta,
    )


def _lifecycle_delete_gate(record: FileRecord) -> str | None:
    if record.is_canonical_source:
        return "HOLD_CANONICAL_SOURCE_NEVER_DELETED"
    if not record.is_derived_materialization:
        return "HOLD_TARGET_NOT_DERIVED_MATERIALIZATION"
    if not record.exclusive_to_branch:
        return "HOLD_SHARED_MATERIALIZATION_NOT_PHYSICALLY_RECLAIMABLE"
    if record.live_reference_count != 0:
        return "HOLD_LIVE_REFERENCE"
    if record.active_lease_count != 0:
        return "HOLD_ACTIVE_LEASE"
    if record.pin_count != 0:
        return "HOLD_PINNED"
    if record.legal_hold or record.retention_hold:
        return "HOLD_LEGAL_OR_RETENTION"
    if not record.canonical_parent_retained:
        return "HOLD_CANONICAL_PARENT_NOT_RETAINED"
    if not record.generation_token or not record.lifecycle_snapshot_token:
        return "HOLD_ATOMIC_GENERATION_AND_LIFECYCLE_TOKENS_REQUIRED"
    return None


def _rehydration_gate(record: FileRecord) -> str | None:
    gate = _lifecycle_delete_gate(record)
    if gate:
        return gate
    if not record.durable_reconstruction_verified or not record.reconstruction_reference:
        return "HOLD_DURABLE_RECONSTRUCTION_NOT_VERIFIED"
    if not _is_sha256(record.expected_source_hash) or not _is_sha256(
        record.observed_source_hash
    ):
        return "HOLD_RECONSTRUCTION_HASHES_INVALID"
    if record.expected_source_hash != record.observed_source_hash:
        return "HOLD_RECONSTRUCTION_HASH_MISMATCH"
    return None


def _decision(
    record: FileRecord,
    classification: Classification,
    action: PlannedAction,
    reason: str,
    release_upper_bound: int = 0,
) -> ActionDecision:
    return ActionDecision(
        record.record_id,
        record.materialization_id,
        record.physical_allocation_id,
        record.stage,
        classification.state,
        action,
        reason,
        classification.governing_proof_hash,
        release_upper_bound,
    )


def evaluate_action(
    policy: MovingVRoutePolicy,
    record: FileRecord,
    proofs: Sequence[RouteProof],
    watermark_receipt: WatermarkMembershipReceipt | None,
) -> ActionDecision:
    classification = classify_record(policy, record, proofs, watermark_receipt)
    state = classification.state
    if state is ClassificationState.CURRENT_GUARD:
        return _decision(record, classification, PlannedAction.PROTECT_CURRENT, classification.reason)
    if state is ClassificationState.FUTURE_REACHABLE_V_PROTECTED:
        actions = {
            FileStage.PREDICTED_NOT_GENERATED: PlannedAction.PROTECT_PRELOAD_CANDIDATE,
            FileStage.GENERATION_SCHEDULED_OR_RUNNING: PlannedAction.CONTINUE_PROTECTED_GENERATION,
            FileStage.GENERATION_COMPLETED: PlannedAction.PROTECT_COMPLETED_MATERIALIZATION,
        }
        return _decision(record, classification, actions[record.stage], classification.reason)
    if state is ClassificationState.FUTURE_REACHABLE_REFERENCE_ONLY:
        return _decision(
            record,
            classification,
            PlannedAction.KEEP_REFERENCE_ONLY,
            "REACHABLE_OUTSIDE_PRELOAD_RADIUS_RETAIN_REFERENCE",
        )
    if state in {
        ClassificationState.FUTURE_UNKNOWN_HOLD,
        ClassificationState.OUT_OF_HORIZON_HOLD,
        ClassificationState.PROOF_CONFLICT_HOLD,
        ClassificationState.UNALIGNED_HOLD,
        ClassificationState.PAST_HOLD,
    }:
        return _decision(record, classification, PlannedAction.KEEP_HOLD, classification.reason)

    destructive_proof = state in {
        ClassificationState.FUTURE_ROUTE_EXCLUDED,
        ClassificationState.FUTURE_PREDICTION_INVALIDATED,
    }

    if record.stage is FileStage.PREDICTED_NOT_GENERATED:
        if destructive_proof or state in {
            ClassificationState.FUTURE_ROUTE_PREDICTED_MISS,
            ClassificationState.PAST_ELIGIBLE,
        }:
            if record.is_canonical_source:
                return _decision(
                    record,
                    classification,
                    PlannedAction.KEEP_HOLD,
                    "HOLD_CANONICAL_FUTURE_GENERATION_INTENT",
                )
            return _decision(
                record,
                classification,
                PlannedAction.CANCEL_PREDICTED_CANDIDATE,
                "REMOVE_PREDICTION_CANDIDATE_NO_FILE_BYTES_EXIST",
            )

    if record.stage is FileStage.GENERATION_SCHEDULED_OR_RUNNING:
        if state is ClassificationState.FUTURE_ROUTE_PREDICTED_MISS:
            return _decision(
                record,
                classification,
                PlannedAction.KEEP_HOLD,
                "PREDICTED_MISS_ALONE_CANNOT_CANCEL_IN_FLIGHT_GENERATION",
            )
        if destructive_proof or state is ClassificationState.PAST_ELIGIBLE:
            if record.is_canonical_source or not record.exclusive_to_branch:
                return _decision(
                    record,
                    classification,
                    PlannedAction.KEEP_HOLD,
                    "HOLD_SHARED_OR_CANONICAL_GENERATION_JOB_NOT_CANCELLABLE",
                )
            if record.generation_job_state is not GenerationJobState.CANCEL_CONFIRMED:
                return _decision(
                    record,
                    classification,
                    PlannedAction.REQUEST_GENERATION_CANCELLATION,
                    "REQUEST_CANCEL_AND_WAIT_FOR_SCHEDULER_RECEIPT",
                )
            gate = _lifecycle_delete_gate(record)
            if gate:
                return _decision(record, classification, PlannedAction.KEEP_HOLD, gate)
            return _decision(
                record,
                classification,
                PlannedAction.CLEAN_CANCELLED_GENERATION_TEMP,
                "CANCELLATION_CONFIRMED_CLEAN_EXCLUSIVE_NONCANONICAL_TEMP",
                record.measured_resident_bytes,
            )

    if record.stage is FileStage.GENERATION_COMPLETED:
        if record.is_canonical_source or not record.exclusive_to_branch:
            if destructive_proof:
                if (
                    record.legal_hold
                    or record.retention_hold
                    or record.active_lease_count
                    or record.pin_count
                ):
                    return _decision(
                        record,
                        classification,
                        PlannedAction.KEEP_HOLD,
                        "HOLD_SHARED_OR_CANONICAL_DETACH_SAFETY_STATE",
                    )
                return _decision(
                    record,
                    classification,
                    PlannedAction.DETACH_BRANCH_REFERENCE_RETAIN_CANONICAL,
                    "PROVEN_BRANCH_INVALID_SHARED_OR_CANONICAL_BYTES_RETAINED",
                )
            return _decision(
                record,
                classification,
                PlannedAction.KEEP_REFERENCE_ONLY,
                "NO_DESTRUCTIVE_BRANCH_PROOF_SHARED_OR_CANONICAL_RETAINED",
            )
        if state is ClassificationState.FUTURE_ROUTE_PREDICTED_MISS:
            gate = _rehydration_gate(record)
            if gate:
                return _decision(record, classification, PlannedAction.KEEP_HOLD, gate)
            return _decision(
                record,
                classification,
                PlannedAction.SOFT_EVICT_RECONSTRUCTIBLE,
                "PREDICTED_MISS_ONLY_SOFT_EVICTS_COMPLETED_MATERIALIZATION",
                record.measured_resident_bytes,
            )
        if destructive_proof:
            gate = _lifecycle_delete_gate(record)
            if gate:
                return _decision(record, classification, PlannedAction.KEEP_HOLD, gate)
            return _decision(
                record,
                classification,
                PlannedAction.DELETE_NONCANONICAL_DERIVED_MATERIALIZATION,
                "PROVEN_WRONG_OR_EXCLUDED_EXCLUSIVE_COMPLETED_DERIVATION",
                record.measured_resident_bytes,
            )
        if state is ClassificationState.PAST_ELIGIBLE:
            gate = _rehydration_gate(record)
            if gate:
                return _decision(record, classification, PlannedAction.KEEP_HOLD, gate)
            return _decision(
                record,
                classification,
                PlannedAction.MOVE_PAST_MATERIALIZATION_TO_QUARANTINE,
                "PAST_ITEM_REQUIRES_QUARANTINE_COMMIT_RECEIPT",
                0,
            )
    return _decision(
        record,
        classification,
        PlannedAction.KEEP_HOLD,
        "HOLD_NO_SAFE_STAGE_ACTION",
    )


def _identity_conflict(records: Sequence[FileRecord]) -> str | None:
    logical: dict[str, str] = {}
    materializations: set[str] = set()
    allocation_bytes: dict[str, int] = {}
    allocation_content: dict[str, str] = {}
    for record in records:
        previous_hash = logical.setdefault(record.logical_record_key, record.content_hash)
        if previous_hash != record.content_hash:
            return "IDENTITY_CONFLICT_SAME_LOGICAL_KEY_DIFFERENT_CONTENT"
        if record.materialization_id in materializations:
            return "DUPLICATE_MATERIALIZATION_ID"
        materializations.add(record.materialization_id)
        previous_bytes = allocation_bytes.setdefault(
            record.physical_allocation_id, record.measured_resident_bytes
        )
        if previous_bytes != record.measured_resident_bytes:
            return "SHARED_ALLOCATION_BYTE_MEASUREMENT_CONFLICT"
        previous_content = allocation_content.setdefault(
            record.physical_allocation_id, record.content_hash
        )
        if previous_content != record.content_hash:
            return "SHARED_ALLOCATION_CONTENT_CONFLICT"
    return None


def plan_branch_invalidation(
    policy: MovingVRoutePolicy,
    records: Sequence[FileRecord],
    proof: RouteProof,
    watermark_receipt: WatermarkMembershipReceipt | None = None,
) -> BranchInvalidationPlan:
    if not records or not proof.descendant_materialization_ids:
        return BranchInvalidationPlan(
            "HOLD_NONEMPTY_GRAPH_DERIVED_DESCENDANT_CLOSURE_REQUIRED",
            proof.branch_id,
            proof.proof_hash,
            (),
            0,
            False,
        )
    conflict = _identity_conflict(records)
    if conflict:
        return BranchInvalidationPlan("HOLD_IDENTITY_CONFLICT:" + conflict, proof.branch_id, proof.proof_hash, (), 0, False)
    if proof.proof_type is not RouteProofType.PREDICTION_INVALIDATION_PROOF:
        return BranchInvalidationPlan("HOLD_INVALIDATION_PROOF_REQUIRED", proof.branch_id, proof.proof_hash, (), 0, False)
    supplied = {record.materialization_id for record in records}
    declared = set(proof.descendant_materialization_ids)
    if supplied != declared:
        return BranchInvalidationPlan("HOLD_DESCENDANT_CLOSURE_INCOMPLETE", proof.branch_id, proof.proof_hash, (), 0, False)
    if any(record.branch_id != proof.branch_id for record in records):
        return BranchInvalidationPlan("HOLD_BRANCH_ID_MISMATCH", proof.branch_id, proof.proof_hash, (), 0, False)
    decisions = tuple(
        evaluate_action(policy, record, (proof,), watermark_receipt) for record in records
    )
    if any(
        decision.action not in BRANCH_INVALIDATION_ELIGIBLE_ACTIONS
        for decision in decisions
    ):
        return BranchInvalidationPlan(
            state="HOLD_BRANCH_ACTION_NOT_ELIGIBLE",
            branch_id=proof.branch_id,
            proof_hash=proof.proof_hash,
            decisions=decisions,
            planned_release_upper_bound_bytes=0,
            graph_closure_complete=True,
            action_plan_terminal=False,
            cleanup_commit_complete=False,
        )
    groups: dict[str, list[ActionDecision]] = {}
    for decision in decisions:
        groups.setdefault(decision.physical_allocation_id, []).append(decision)
    release = sum(
        max(item.expected_release_upper_bound_bytes for item in group)
        for group in groups.values()
        if group
        and all(item.action in PHYSICAL_RECLAIM_ACTIONS for item in group)
    )
    cancellation_pending = any(
        decision.action is PlannedAction.REQUEST_GENERATION_CANCELLATION
        for decision in decisions
    )
    state = (
        "PENDING_CANCELLATION_RECEIPTS_SHADOW_PLAN"
        if cancellation_pending
        else "PASS_SHADOW_BRANCH_INVALIDATION_PLAN"
    )
    return BranchInvalidationPlan(
        state=state,
        branch_id=proof.branch_id,
        proof_hash=proof.proof_hash,
        decisions=decisions,
        planned_release_upper_bound_bytes=release,
        graph_closure_complete=True,
        action_plan_terminal=not cancellation_pending,
        cleanup_commit_complete=False,
    )


def plan_memory_pressure(
    policy: MovingVRoutePolicy,
    records: Sequence[FileRecord],
    proof_map: Mapping[str, Sequence[RouteProof]],
    *,
    target_release_bytes: int,
    watermark_receipt: WatermarkMembershipReceipt | None = None,
) -> PressurePlan:
    _require_uint("target_release_bytes", target_release_bytes)
    conflict = _identity_conflict(records)
    if conflict:
        return PressurePlan("HOLD_IDENTITY_CONFLICT:" + conflict, target_release_bytes, 0, (), (), ())
    decisions = tuple(
        evaluate_action(policy, record, proof_map.get(record.materialization_id, ()), watermark_receipt)
        for record in records
    )
    groups: dict[str, list[ActionDecision]] = {}
    for decision in decisions:
        groups.setdefault(decision.physical_allocation_id, []).append(decision)
    ranked = sorted(
        (
            (
                allocation_id,
                group,
                max(item.expected_release_upper_bound_bytes for item in group),
            )
            for allocation_id, group in groups.items()
            if group
            and all(item.action in PHYSICAL_RECLAIM_ACTIONS for item in group)
            and max(item.expected_release_upper_bound_bytes for item in group) > 0
        ),
        key=lambda item: (
            0
            if any(
                decision.classification
                is ClassificationState.FUTURE_PREDICTION_INVALIDATED
                for decision in item[1]
            )
            else 1,
            -item[2],
            item[0].encode("utf-8"),
        ),
    )
    selected_materializations: list[str] = []
    selected_allocations: list[str] = []
    release = 0
    for allocation_id, group, allocation_release in ranked:
        if release >= target_release_bytes:
            break
        selected_materializations.extend(
            sorted(item.materialization_id for item in group)
        )
        selected_allocations.append(allocation_id)
        release += allocation_release
    state = "PASS_SHADOW_PRESSURE_PLAN" if release >= target_release_bytes else "BACKPRESSURE_REQUIRED"
    return PressurePlan(
        state,
        target_release_bytes,
        release,
        tuple(selected_materializations),
        tuple(selected_allocations),
        decisions,
    )


def _record_safety_state_hash(record: FileRecord) -> str:
    return _hash_object(
        {
            "logical_record_key": record.logical_record_key,
            "materialization_id": record.materialization_id,
            "physical_allocation_id": record.physical_allocation_id,
            "content_hash": record.content_hash,
            "record_version": record.record_version,
            "time_domain_id": record.time_domain_id,
            "logical_time": record.logical_time,
            "stage": record.stage.value,
            "stage_entered_at_ns": record.stage_entered_at_ns,
            "stage_observed_at_ns": record.stage_observed_at_ns,
            "stage_sequence": record.stage_sequence,
            "stage_state_hash": record.stage_state_hash,
            "need_time_ns": record.need_time_ns,
            "event_time_ns": record.event_time_ns,
            "ingest_time_ns": record.ingest_time_ns,
            "ingest_seq": record.ingest_seq,
            "classification_snapshot_ingest_seq": record.classification_snapshot_ingest_seq,
            "late_event_reconciled": record.late_event_reconciled,
            "late_event_reconciliation_receipt_hash": record.late_event_reconciliation_receipt_hash,
            "classification_snapshot_receipt_hash": record.classification_snapshot_receipt_hash,
            "adi_delta_f_uint": record.adi_delta_f_uint,
            "generation_job_id": record.generation_job_id,
            "generation_job_state": record.generation_job_state.value,
            "stage_transition_receipt_hash": record.stage_transition_receipt_hash,
            "stage_transition_verified": record.stage_transition_verified,
            "cancellation_receipt_hash": record.cancellation_receipt_hash,
            "cancellation_outcome": record.cancellation_outcome,
            "worker_fence_receipt_hash": record.worker_fence_receipt_hash,
            "worker_fence_state": record.worker_fence_state,
            "completion_receipt_hash": record.completion_receipt_hash,
            "generation_token": record.generation_token,
            "lifecycle_snapshot_token": record.lifecycle_snapshot_token,
            "live_reference_count": record.live_reference_count,
            "active_lease_count": record.active_lease_count,
            "pin_count": record.pin_count,
            "is_canonical_source": record.is_canonical_source,
            "is_derived_materialization": record.is_derived_materialization,
            "is_speculative_candidate": record.is_speculative_candidate,
            "exclusive_to_branch": record.exclusive_to_branch,
            "branch_id": record.branch_id,
            "canonical_parent_retained": record.canonical_parent_retained,
            "legal_hold": record.legal_hold,
            "retention_hold": record.retention_hold,
            "durable_reconstruction_verified": record.durable_reconstruction_verified,
            "reconstruction_reference": record.reconstruction_reference,
            "expected_source_hash": record.expected_source_hash,
            "observed_source_hash": record.observed_source_hash,
            "storage_tier": record.storage_tier,
            "measured_resident_bytes": record.measured_resident_bytes,
            "prediction_epoch": record.prediction_epoch,
            "route_epoch": record.route_epoch,
        }
    )


def allocation_owner_set_hash(records: Sequence[FileRecord]) -> str:
    if not records:
        raise ValueError("ALLOCATION_OWNER_SET_REQUIRED")
    conflict = _identity_conflict(records)
    if conflict:
        raise ValueError("ALLOCATION_OWNER_SET_" + conflict)
    allocation_ids = {record.physical_allocation_id for record in records}
    if len(allocation_ids) != 1:
        raise ValueError("ALLOCATION_OWNER_SET_MUST_SHARE_ONE_PHYSICAL_ALLOCATION")
    body = sorted(
        (
            record.materialization_id,
            record.content_hash,
            _record_safety_state_hash(record),
        )
        for record in records
    )
    return _hash_object(body)


def _decision_token_hash(token: DecisionToken) -> str:
    return _hash_object(
        {
            "decision_id": token.decision_id,
            "idempotency_key": token.idempotency_key,
            "materialization_id": token.materialization_id,
            "physical_allocation_id": token.physical_allocation_id,
            "action": token.action.value,
            "classification": token.classification.value,
            "record_version": token.record_version,
            "stage": token.stage.value,
            "generation_job_state": token.generation_job_state.value,
            "generation_token": token.generation_token,
            "lifecycle_snapshot_token": token.lifecycle_snapshot_token,
            "policy_epoch": token.policy_epoch,
            "prediction_epoch": token.prediction_epoch,
            "route_epoch": token.route_epoch,
            "route_graph_root": token.route_graph_root,
            "proof_hash": token.proof_hash,
            "expected_content_hash": token.expected_content_hash,
            "safety_state_hash": token.safety_state_hash,
            "allocation_owner_set_hash": token.allocation_owner_set_hash,
            "expected_release_upper_bound_bytes": token.expected_release_upper_bound_bytes,
            "expires_at_ns": token.expires_at_ns,
        }
    )


def commit_receipt_binding_hash(receipt: CommitReceipt) -> str:
    return _hash_object(
        {
            "idempotency_key": receipt.idempotency_key,
            "decision_id": receipt.decision_id,
            "token_hash": receipt.token_hash,
            "materialization_id": receipt.materialization_id,
            "expected_content_hash": receipt.expected_content_hash,
            "prediction_epoch": receipt.prediction_epoch,
            "route_epoch": receipt.route_epoch,
            "action": receipt.committed_action.value,
            "classification": receipt.classification.value,
            "cas_result": receipt.cas_result,
            "actual_released_bytes": receipt.actual_released_bytes,
            "commit_time_ns": receipt.commit_time_ns,
            "simulation_only": receipt.simulation_only,
            "failure_code": receipt.failure_code,
        }
    )


def _prior_receipt_validation_reason(
    token: DecisionToken, receipt: CommitReceipt
) -> str | None:
    if not isinstance(receipt.committed_action, PlannedAction) or not isinstance(
        receipt.classification, ClassificationState
    ):
        return "PRIOR_RECEIPT_ENUM_INVALID"
    if (
        receipt.receipt_hash != commit_receipt_binding_hash(receipt)
        or receipt.receipt_id != "sim-" + receipt.receipt_hash[:24]
    ):
        return "PRIOR_RECEIPT_INTEGRITY_HASH_MISMATCH"
    if (
        receipt.idempotency_key != token.idempotency_key
        or receipt.decision_id != token.decision_id
        or receipt.token_hash != token.token_hash
        or receipt.committed_action is not token.action
        or receipt.classification is not token.classification
        or receipt.materialization_id != token.materialization_id
        or receipt.expected_content_hash != token.expected_content_hash
        or receipt.prediction_epoch != token.prediction_epoch
        or receipt.route_epoch != token.route_epoch
    ):
        return "PRIOR_RECEIPT_DECISION_BINDING_MISMATCH"
    if receipt.simulation_only is not True:
        return "PRIOR_RECEIPT_LIVE_AUTHORITY_UNVERIFIED"
    if not _is_uint(receipt.actual_released_bytes) or not _is_uint(
        receipt.commit_time_ns
    ):
        return "PRIOR_RECEIPT_UINT_INVALID"
    if receipt.actual_released_bytes > token.expected_release_upper_bound_bytes:
        return "PRIOR_RECEIPT_RELEASE_EXCEEDS_UPPER_BOUND"
    if (
        token.action not in PHYSICAL_RECLAIM_ACTIONS
        and receipt.actual_released_bytes != 0
    ):
        return "PRIOR_RECEIPT_NON_RECLAIM_RELEASE"
    if receipt.cas_result == "SIMULATED_COMMIT":
        if receipt.failure_code is not None:
            return "PRIOR_RECEIPT_COMMIT_WITH_FAILURE_CODE"
        if receipt.commit_time_ns > token.expires_at_ns:
            return "PRIOR_RECEIPT_COMMITTED_AFTER_TOKEN_EXPIRY"
    elif receipt.cas_result == "HOLD_CAS_MISMATCH":
        if receipt.actual_released_bytes != 0 or not receipt.failure_code:
            return "PRIOR_RECEIPT_HOLD_STATE_INCONSISTENT"
    else:
        return "PRIOR_RECEIPT_CAS_RESULT_UNSUPPORTED"
    return None


def make_decision_token(
    policy: MovingVRoutePolicy,
    record: FileRecord,
    decision: ActionDecision,
    *,
    decision_id: str,
    idempotency_key: str,
    allocation_owner_records: Sequence[FileRecord],
    expires_at_ns: int,
) -> DecisionToken:
    _require_uint("expires_at_ns", expires_at_ns)
    if not decision_id or not idempotency_key:
        raise ValueError("DECISION_AND_IDEMPOTENCY_IDS_REQUIRED")
    owner_hash = allocation_owner_set_hash(allocation_owner_records)
    if record.materialization_id not in {
        owner.materialization_id for owner in allocation_owner_records
    }:
        raise ValueError("DECISION_RECORD_NOT_IN_ALLOCATION_OWNER_SET")
    if decision.action in PHYSICAL_RECLAIM_ACTIONS and len(allocation_owner_records) != 1:
        raise ValueError("SHARED_ALLOCATION_REQUIRES_ATOMIC_GROUP_COMMIT_TOKEN")
    if (
        decision.record_id != record.record_id
        or decision.materialization_id != record.materialization_id
        or decision.physical_allocation_id != record.physical_allocation_id
        or decision.stage is not record.stage
    ):
        raise ValueError("DECISION_RECORD_BINDING_MISMATCH")
    if (
        decision.action not in PHYSICAL_RECLAIM_ACTIONS
        and decision.expected_release_upper_bound_bytes != 0
    ):
        raise ValueError("NON_RECLAIM_ACTION_CANNOT_EXPECT_RELEASE")
    unsigned = DecisionToken(
        decision_id=decision_id,
        idempotency_key=idempotency_key,
        materialization_id=record.materialization_id,
        physical_allocation_id=record.physical_allocation_id,
        action=decision.action,
        classification=decision.classification,
        record_version=record.record_version,
        stage=record.stage,
        generation_job_state=record.generation_job_state,
        generation_token=record.generation_token,
        lifecycle_snapshot_token=record.lifecycle_snapshot_token,
        policy_epoch=policy.policy_epoch,
        prediction_epoch=policy.prediction_epoch,
        route_epoch=policy.route_epoch,
        route_graph_root=policy.route_graph_root,
        proof_hash=decision.proof_hash,
        expected_content_hash=record.content_hash,
        safety_state_hash=_record_safety_state_hash(record),
        allocation_owner_set_hash=owner_hash,
        expected_release_upper_bound_bytes=decision.expected_release_upper_bound_bytes,
        expires_at_ns=expires_at_ns,
        token_hash=SHA256_ZERO,
    )
    return replace(unsigned, token_hash=_decision_token_hash(unsigned))


def simulate_commit(
    token: DecisionToken,
    current_record: FileRecord,
    *,
    now_ns: int,
    actual_released_bytes: int,
    current_policy: MovingVRoutePolicy,
    current_proofs: Sequence[RouteProof],
    current_watermark_receipt: WatermarkMembershipReceipt | None,
    current_allocation_owner_records: Sequence[FileRecord],
    prior_receipt: CommitReceipt | None = None,
) -> CommitReceipt:
    """Simulate commit validation without applying an action."""
    _require_uint("now_ns", now_ns)
    _require_uint("actual_released_bytes", actual_released_bytes)
    if prior_receipt is not None:
        prior_reason = _prior_receipt_validation_reason(token, prior_receipt)
        if prior_reason:
            raise ValueError(prior_reason)
        return prior_receipt
    stage_reason = validate_stage_record(current_record)
    action_gate_reason: str | None = None
    if token.action is PlannedAction.SOFT_EVICT_RECONSTRUCTIBLE:
        if current_record.stage is not FileStage.GENERATION_COMPLETED:
            action_gate_reason = "SOFT_EVICT_REQUIRES_COMPLETED_STAGE"
        else:
            action_gate_reason = _rehydration_gate(current_record)
    elif token.action is PlannedAction.DELETE_NONCANONICAL_DERIVED_MATERIALIZATION:
        if current_record.stage is not FileStage.GENERATION_COMPLETED:
            action_gate_reason = "DELETE_REQUIRES_COMPLETED_STAGE"
        else:
            action_gate_reason = _lifecycle_delete_gate(current_record)
    elif token.action is PlannedAction.CLEAN_CANCELLED_GENERATION_TEMP:
        if (
            current_record.stage is not FileStage.GENERATION_SCHEDULED_OR_RUNNING
            or current_record.generation_job_state
            is not GenerationJobState.CANCEL_CONFIRMED
        ):
            action_gate_reason = "TEMP_CLEAN_REQUIRES_CONFIRMED_CANCELLATION"
        else:
            action_gate_reason = _lifecycle_delete_gate(current_record)
    try:
        current_owner_hash = allocation_owner_set_hash(
            current_allocation_owner_records
        )
        owner_set_hash_valid = True
    except ValueError:
        current_owner_hash = ""
        owner_set_hash_valid = False
    try:
        current_decision = evaluate_action(
            current_policy,
            current_record,
            current_proofs,
            current_watermark_receipt,
        )
        decision_revalidated = (
            current_decision.action is token.action
            and current_decision.classification is token.classification
            and current_decision.proof_hash == token.proof_hash
            and current_decision.expected_release_upper_bound_bytes
            == token.expected_release_upper_bound_bytes
        )
    except (TypeError, ValueError):
        decision_revalidated = False
    checks = (
        (token.token_hash == _decision_token_hash(token), "TOKEN_HASH_MISMATCH"),
        (now_ns <= token.expires_at_ns, "DECISION_TOKEN_EXPIRED"),
        (stage_reason is None, stage_reason or "STAGE_RECORD_INVALID"),
        (action_gate_reason is None, action_gate_reason or "ACTION_GATE_HOLD"),
        (owner_set_hash_valid, "ALLOCATION_OWNER_SET_HASH_INVALID"),
        (
            current_record.materialization_id == token.materialization_id,
            "MATERIALIZATION_ID_MISMATCH",
        ),
        (
            current_record.physical_allocation_id == token.physical_allocation_id,
            "PHYSICAL_ALLOCATION_ID_MISMATCH",
        ),
        (current_record.content_hash == token.expected_content_hash, "CONTENT_HASH_MISMATCH"),
        (current_record.record_version == token.record_version, "RECORD_VERSION_MISMATCH"),
        (current_record.stage is token.stage, "STAGE_CAS_MISMATCH"),
        (
            current_record.generation_job_state is token.generation_job_state,
            "GENERATION_JOB_STATE_MISMATCH",
        ),
        (current_record.generation_token == token.generation_token, "GENERATION_TOKEN_MISMATCH"),
        (
            current_record.lifecycle_snapshot_token == token.lifecycle_snapshot_token,
            "LIFECYCLE_SNAPSHOT_TOKEN_MISMATCH",
        ),
        (
            _record_safety_state_hash(current_record) == token.safety_state_hash,
            "SAFETY_STATE_HASH_MISMATCH",
        ),
        (
            current_owner_hash == token.allocation_owner_set_hash,
            "ALLOCATION_OWNER_SET_CHANGED",
        ),
        (current_policy.policy_epoch == token.policy_epoch, "POLICY_EPOCH_MISMATCH"),
        (
            current_policy.route_graph_root == token.route_graph_root,
            "ROUTE_GRAPH_ROOT_MISMATCH",
        ),
        (decision_revalidated, "DECISION_REVALIDATION_MISMATCH"),
        (
            actual_released_bytes <= token.expected_release_upper_bound_bytes,
            "ACTUAL_RELEASE_EXCEEDS_UPPER_BOUND",
        ),
        (
            token.action in PHYSICAL_RECLAIM_ACTIONS
            or actual_released_bytes == 0,
            "NON_RECLAIM_ACTION_REPORTED_RELEASE",
        ),
    )
    failure_code = next((code for passed, code in checks if not passed), None)
    matches = failure_code is None
    cas_result = "SIMULATED_COMMIT" if matches else "HOLD_CAS_MISMATCH"
    released = actual_released_bytes if matches else 0
    unsigned_receipt = CommitReceipt(
        receipt_id="",
        idempotency_key=token.idempotency_key,
        decision_id=token.decision_id,
        token_hash=token.token_hash,
        materialization_id=token.materialization_id,
        expected_content_hash=token.expected_content_hash,
        prediction_epoch=token.prediction_epoch,
        route_epoch=token.route_epoch,
        committed_action=token.action,
        classification=token.classification,
        cas_result=cas_result,
        actual_released_bytes=released,
        commit_time_ns=now_ns,
        simulation_only=True,
        failure_code=failure_code,
        receipt_hash=SHA256_ZERO,
    )
    receipt_hash = commit_receipt_binding_hash(unsigned_receipt)
    return replace(
        unsigned_receipt,
        receipt_id="sim-" + receipt_hash[:24],
        receipt_hash=receipt_hash,
    )


def false_miss_receipt_state(
    commit_receipt: CommitReceipt,
    *,
    decision_token: DecisionToken,
    actual_hit: bool,
    demand_event_id: str,
    demand_materialization_id: str,
    demand_prediction_epoch: str,
    demand_route_epoch: str,
    reconstructed_content_hash: str,
) -> str:
    receipt_reason = _prior_receipt_validation_reason(
        decision_token, commit_receipt
    )
    if receipt_reason:
        return "HOLD_" + receipt_reason
    if (
        commit_receipt.committed_action is not PlannedAction.SOFT_EVICT_RECONSTRUCTIBLE
        or commit_receipt.cas_result != "SIMULATED_COMMIT"
        or commit_receipt.failure_code is not None
        or not _is_uint(commit_receipt.actual_released_bytes)
        or commit_receipt.actual_released_bytes == 0
        or not actual_hit
    ):
        return "NOT_A_FALSE_MISS"
    if not demand_event_id or demand_materialization_id != commit_receipt.materialization_id:
        return "HOLD_DEMAND_RECEIPT_BINDING_MISMATCH"
    if (
        demand_prediction_epoch != commit_receipt.prediction_epoch
        or demand_route_epoch != commit_receipt.route_epoch
    ):
        return "ROUTE_CHANGE_REGENERATION"
    if (
        not _is_sha256(commit_receipt.expected_content_hash)
        or not _is_sha256(reconstructed_content_hash)
        or commit_receipt.expected_content_hash != reconstructed_content_hash
    ):
        return "REHYDRATION_FAILURE_HOLD"
    if commit_receipt.simulation_only:
        return "SIMULATED_FALSE_MISS_BYTE_EXACT"
    return "FALSE_MISS_REHYDRATED_BYTE_EXACT"


def evaluate_budget_adjustment_candidate(
    *,
    current_limit_bytes: int,
    proposed_limit_bytes: int,
    gate: BudgetPerformanceGate,
    evidence: BudgetPerformanceEvidence,
) -> BudgetAdjustmentDecision:
    """Evaluate a RAM candidate; 2 GiB is an initial ceiling, not a constant."""
    _require_uint("current_limit_bytes", current_limit_bytes)
    _require_uint("proposed_limit_bytes", proposed_limit_bytes)
    for name, value in asdict(gate).items():
        _require_uint(name, value)
        if name.endswith("_bp") and value > 10_000:
            raise ValueError(f"{name}_MUST_NOT_EXCEED_10000")
    for name, value in asdict(evidence).items():
        if name == "swap_thrashing":
            if not isinstance(value, bool):
                raise ValueError("swap_thrashing_MUST_BE_BOOL")
            continue
        _require_uint(name, value)
        if name.endswith("_bp") and value > 10_000:
            raise ValueError(f"{name}_MUST_NOT_EXCEED_10000")
    reason = ""
    if proposed_limit_bytes == 0:
        reason = "HOLD_PROPOSED_LIMIT_MUST_BE_POSITIVE"
    elif current_limit_bytes > evidence.host_capacity_bytes:
        reason = "HOLD_CURRENT_LIMIT_EXCEEDS_HOST_CAPACITY"
    elif proposed_limit_bytes > evidence.host_capacity_bytes:
        reason = "HOLD_PROPOSED_LIMIT_EXCEEDS_HOST_CAPACITY"
    elif evidence.host_available_after_adjustment_bytes > (
        evidence.host_capacity_bytes - proposed_limit_bytes
    ):
        reason = "HOLD_HOST_CAPACITY_EVIDENCE_INCONSISTENT"
    elif evidence.sample_count < gate.min_sample_count:
        reason = "HOLD_INSUFFICIENT_SAMPLES"
    elif evidence.observation_ns < gate.min_observation_ns:
        reason = "HOLD_INSUFFICIENT_OBSERVATION"
    elif proposed_limit_bytes < evidence.protected_working_set_bytes:
        reason = "HOLD_LIMIT_BELOW_PROTECTED_WORKING_SET"
    elif evidence.host_available_after_adjustment_bytes < gate.min_host_reserve_bytes:
        reason = "HOLD_HOST_RESERVE_TOO_LOW"
    elif evidence.oom_event_count:
        reason = "HOLD_OOM_OBSERVED"
    elif evidence.swap_thrashing:
        reason = "HOLD_SWAP_THRASHING"
    elif evidence.protected_eviction_violation_count:
        reason = "HOLD_PROTECTED_EVICTION"
    elif evidence.reconstruction_hash_mismatch_count:
        reason = "HOLD_RECONSTRUCTION_HASH_MISMATCH"
    elif evidence.p95_latency_regression_bp > gate.max_p95_latency_regression_bp:
        reason = "HOLD_P95_LATENCY_REGRESSION"
    elif evidence.p99_latency_regression_bp > gate.max_p99_latency_regression_bp:
        reason = "HOLD_P99_LATENCY_REGRESSION"
    elif evidence.ttft_p95_regression_bp > gate.max_ttft_p95_regression_bp:
        reason = "HOLD_TTFT_REGRESSION"
    elif evidence.rehydration_stall_p99_ns > gate.max_rehydration_stall_p99_ns:
        reason = "HOLD_REHYDRATION_STALL"
    elif evidence.false_miss_rate_bp > gate.max_false_miss_rate_bp:
        reason = "HOLD_FALSE_MISS_RATE"
    elif evidence.preload_hit_rate_bp < gate.min_preload_hit_rate_bp:
        reason = "HOLD_PRELOAD_HIT_RATE"
    elif evidence.task_success_regression_bp > gate.max_task_success_regression_bp:
        reason = "HOLD_TASK_SUCCESS_REGRESSION"
    elif evidence.tool_success_regression_bp > gate.max_tool_success_regression_bp:
        reason = "HOLD_TOOL_SUCCESS_REGRESSION"
    else:
        return BudgetAdjustmentDecision(
            "PASS_MEASUREMENT_CANDIDATE_ONLY",
            current_limit_bytes,
            proposed_limit_bytes,
            "UX_AND_CAPACITY_GATES_PASS_SEPARATE_AUTHORITY_REQUIRED",
        )
    return BudgetAdjustmentDecision(
        "HOLD_BUDGET_ADJUSTMENT",
        current_limit_bytes,
        proposed_limit_bytes,
        reason,
    )


__all__ = [
    "ActionDecision",
    "BranchInvalidationPlan",
    "BudgetAdjustmentDecision",
    "BudgetPerformanceEvidence",
    "BudgetPerformanceGate",
    "Classification",
    "ClassificationState",
    "CommitReceipt",
    "DecisionToken",
    "EnvelopeKnot",
    "FileRecord",
    "FileStage",
    "GenerationJobState",
    "MovingVRoutePolicy",
    "PlannedAction",
    "PressurePlan",
    "RequiredNode",
    "RouteProof",
    "RouteProofType",
    "StageTransitionReceipt",
    "WatermarkMembershipReceipt",
    "WatermarkObservation",
    "aligned_safe_watermark",
    "allocation_owner_set_hash",
    "classify_record",
    "commit_receipt_binding_hash",
    "envelope_at",
    "evaluate_action",
    "evaluate_budget_adjustment_candidate",
    "false_miss_receipt_state",
    "make_decision_token",
    "materialization_binding",
    "plan_branch_invalidation",
    "plan_memory_pressure",
    "route_proof_binding_hash",
    "simulate_commit",
    "validate_apex_advance",
    "validate_policy",
    "validate_stage_record",
    "validate_stage_transition",
]
