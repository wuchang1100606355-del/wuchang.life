from __future__ import annotations

from dataclasses import replace
import ast
import inspect
import random
import unittest

import tools.total_field.moving_v_route_cleanup_candidate_v2 as candidate_v2

from tools.total_field.moving_v_route_cleanup_candidate_v2 import (
    BudgetPerformanceEvidence,
    BudgetPerformanceGate,
    ClassificationState,
    EnvelopeKnot,
    FileRecord,
    FileStage,
    GenerationJobState,
    MovingVRoutePolicy,
    PlannedAction,
    RequiredNode,
    RouteProof,
    RouteProofType,
    StageTransitionReceipt,
    WatermarkMembershipReceipt,
    WatermarkObservation,
    aligned_safe_watermark,
    classify_record,
    commit_receipt_binding_hash,
    evaluate_action,
    evaluate_budget_adjustment_candidate,
    false_miss_receipt_state,
    make_decision_token,
    materialization_binding,
    plan_branch_invalidation,
    plan_memory_pressure,
    route_proof_binding_hash,
    simulate_commit,
    validate_policy,
    validate_stage_record,
    validate_stage_transition,
)


T = 1_000_000
H_A = "a" * 64
H_B = "b" * 64
H_C = "c" * 64
H_D = "d" * 64
H_E = "e" * 64
H_F = "f" * 64
H_1 = "1" * 64
H_2 = "2" * 64
H_3 = "3" * 64


def policy(**changes: object) -> MovingVRoutePolicy:
    base = MovingVRoutePolicy(
        policy_id="moving-v-route-v2",
        policy_epoch="policy-1",
        prediction_epoch="prediction-1",
        route_epoch="route-1",
        membership_epoch="members-1",
        time_domain_id="tai-ns-1",
        route_graph_root=H_A,
        route_ruleset_root=H_B,
        apex_time_ns=T,
        current_guard_ns=10,
        clock_uncertainty_ns=2,
        past_grace_ns=5,
        future_horizon_ns=100,
        envelope=(
            EnvelopeKnot(0, 1, 10),
            EnvelopeKnot(50, 5, 9),
            EnvelopeKnot(100, 8, 8),
        ),
        shadow_only=True,
    )
    return replace(base, **changes)


def record(
    *,
    materialization_id: str = "mat-1",
    physical_allocation_id: str = "alloc-1",
    record_id: str = "record-1",
    stage: FileStage = FileStage.PREDICTED_NOT_GENERATED,
    need_time_ns: int = T + 20,
    distance: int | None = 1,
    branch_id: str = "branch-1",
    **changes: object,
) -> FileRecord:
    values: dict[str, object] = {
        "namespace": "test",
        "record_id": record_id,
        "record_version": 1,
        "materialization_id": materialization_id,
        "physical_allocation_id": physical_allocation_id,
        "content_hash": H_C,
        "time_domain_id": "tai-ns-1",
        "logical_time": 1,
        "stage": stage,
        "stage_entered_at_ns": T - 3,
        "stage_observed_at_ns": T - 2,
        "stage_sequence": 0,
        "stage_state_hash": H_3,
        "need_time_ns": need_time_ns,
        "event_time_ns": T - 20,
        "ingest_time_ns": T - 1,
        "ingest_seq": 5,
        "classification_snapshot_ingest_seq": 5,
        "late_event_reconciled": True,
        "late_event_reconciliation_receipt_hash": H_1,
        "classification_snapshot_receipt_hash": H_2,
        "adi_delta_f_uint": distance,
        "prediction_epoch": "prediction-1",
        "route_epoch": "route-1",
        "generation_job_id": "",
        "generation_job_state": GenerationJobState.NONE,
        "stage_transition_receipt_hash": "",
        "stage_transition_verified": False,
        "cancellation_receipt_hash": "",
        "cancellation_outcome": "",
        "worker_fence_receipt_hash": "",
        "worker_fence_state": "",
        "completion_receipt_hash": "",
        "storage_tier": "REFERENCE_ONLY",
        "measured_resident_bytes": 0,
        "generation_token": "generation-token-1",
        "lifecycle_snapshot_token": "lifecycle-token-1",
        "live_reference_count": 0,
        "active_lease_count": 0,
        "pin_count": 0,
        "durable_reconstruction_verified": False,
        "reconstruction_reference": "",
        "expected_source_hash": "",
        "observed_source_hash": "",
        "is_canonical_source": False,
        "is_derived_materialization": True,
        "is_speculative_candidate": True,
        "exclusive_to_branch": True,
        "branch_id": branch_id,
        "canonical_parent_retained": True,
        "legal_hold": False,
        "retention_hold": False,
    }
    if stage is FileStage.GENERATION_SCHEDULED_OR_RUNNING:
        values.update(
            generation_job_id="job-1",
            generation_job_state=GenerationJobState.RUNNING,
            stage_transition_receipt_hash=H_D,
            stage_transition_verified=True,
            stage_sequence=1,
            storage_tier="RAM_HEAP",
            measured_resident_bytes=4096,
        )
    elif stage is FileStage.GENERATION_COMPLETED:
        values.update(
            generation_job_id="job-1",
            generation_job_state=GenerationJobState.COMPLETED,
            stage_transition_receipt_hash=H_D,
            stage_transition_verified=True,
            stage_sequence=2,
            completion_receipt_hash=H_E,
            storage_tier="RAM_HEAP",
            measured_resident_bytes=4096,
            durable_reconstruction_verified=True,
            reconstruction_reference="gtp://packet/1",
            expected_source_hash=H_F,
            observed_source_hash=H_F,
            is_speculative_candidate=False,
        )
    values.update(changes)
    return FileRecord(**values)


def proof(
    proof_type: RouteProofType,
    *,
    descendants: tuple[str, ...] = (),
    branch_id: str = "branch-1",
    bindings: tuple[str, ...] | None = None,
    **changes: object,
) -> RouteProof:
    values: dict[str, object] = {
        "proof_id": "proof-1",
        "proof_type": proof_type,
        "prediction_epoch": "prediction-1",
        "route_epoch": "route-1",
        "route_graph_root": H_A,
        "route_ruleset_root": H_B,
        "start_state_root": H_C,
        "target_state_or_predicate_hash": H_D,
        "valid_from_ns": T - 100,
        "valid_until_ns": T + 100,
        "need_time_start_ns": 0,
        "need_time_end_ns": T + 1000,
        "constraint_root": H_E,
        "closed_world_declared": proof_type
        in {
            RouteProofType.ROUTE_EXCLUSION_PROOF,
            RouteProofType.PREDICTION_INVALIDATION_PROOF,
        },
        "verifier_id": "static-verifier",
        "verifier_hash": H_F,
        "proof_payload_hash": H_1,
        "proof_hash": "0" * 64,
        "verification_state": "PASS",
        "covered_materialization_bindings": bindings
        if bindings is not None
        else tuple(f"{item}:{H_C}" for item in (descendants or ("mat-1",))),
        "descendant_closure_root": H_3
        if proof_type is RouteProofType.PREDICTION_INVALIDATION_PROOF
        else "0" * 64,
        "closure_receipt_hash": H_A
        if proof_type is RouteProofType.PREDICTION_INVALIDATION_PROOF
        else "0" * 64,
        "closure_verification_state": "PASS"
        if proof_type is RouteProofType.PREDICTION_INVALIDATION_PROOF
        else "NOT_APPLICABLE",
        "replay_complete": proof_type is RouteProofType.REACHABLE_PATH_PROOF,
        "frontier_complete": proof_type
        in {
            RouteProofType.ROUTE_EXCLUSION_PROOF,
            RouteProofType.PREDICTION_INVALIDATION_PROOF,
        },
        "actual_outcome_ref": "outcome://1"
        if proof_type is RouteProofType.PREDICTION_INVALIDATION_PROOF
        else "",
        "branch_id": branch_id
        if proof_type is RouteProofType.PREDICTION_INVALIDATION_PROOF
        else "",
        "descendant_materialization_ids": descendants
        if proof_type is RouteProofType.PREDICTION_INVALIDATION_PROOF
        else (),
    }
    values.update(changes)
    unsigned = RouteProof(**values)
    return replace(unsigned, proof_hash=route_proof_binding_hash(unsigned))


def watermark(**changes: object) -> WatermarkMembershipReceipt:
    values: dict[str, object] = {
        "receipt_id": "watermark-1",
        "membership_epoch": "members-1",
        "required_nodes": (
            RequiredNode("node-a", "boot-a", "clock-1"),
            RequiredNode("node-b", "boot-b", "clock-1"),
        ),
        "observations": (
            WatermarkObservation(
                "node-a", "boot-a", "clock-1", "members-1", T - 20, T - 2, T + 5, 2
            ),
            WatermarkObservation(
                "node-b", "boot-b", "clock-1", "members-1", T - 18, T - 2, T + 5, 2
            ),
        ),
        "partition_state": "HEALTHY",
    }
    values.update(changes)
    return WatermarkMembershipReceipt(**values)


def gate() -> BudgetPerformanceGate:
    return BudgetPerformanceGate(
        min_sample_count=100,
        min_observation_ns=1000,
        min_host_reserve_bytes=1_000_000,
        max_p95_latency_regression_bp=100,
        max_p99_latency_regression_bp=150,
        max_ttft_p95_regression_bp=100,
        max_rehydration_stall_p99_ns=1_000_000,
        max_false_miss_rate_bp=100,
        min_preload_hit_rate_bp=7000,
        max_task_success_regression_bp=50,
        max_tool_success_regression_bp=50,
    )


def evidence(**changes: object) -> BudgetPerformanceEvidence:
    values: dict[str, object] = {
        "sample_count": 1000,
        "observation_ns": 10_000,
        "host_capacity_bytes": 16_000_000_000,
        "host_available_after_adjustment_bytes": 4_000_000_000,
        "protected_working_set_bytes": 1_000_000_000,
        "p95_latency_regression_bp": 10,
        "p99_latency_regression_bp": 10,
        "ttft_p95_regression_bp": 10,
        "rehydration_stall_p99_ns": 1000,
        "false_miss_rate_bp": 10,
        "preload_hit_rate_bp": 9000,
        "task_success_regression_bp": 0,
        "tool_success_regression_bp": 0,
        "oom_event_count": 0,
        "swap_thrashing": False,
        "protected_eviction_violation_count": 0,
        "reconstruction_hash_mismatch_count": 0,
    }
    values.update(changes)
    return BudgetPerformanceEvidence(**values)


def simulate_current(
    token: object,
    item: FileRecord,
    proofs: tuple[RouteProof, ...],
    *,
    actual_released_bytes: int,
    owner_records: tuple[FileRecord, ...] | None = None,
    current_policy: MovingVRoutePolicy | None = None,
    prior_receipt: object | None = None,
):
    return simulate_commit(
        token,
        item,
        now_ns=T,
        actual_released_bytes=actual_released_bytes,
        current_policy=current_policy or policy(),
        current_proofs=proofs,
        current_watermark_receipt=None,
        current_allocation_owner_records=owner_records or (item,),
        prior_receipt=prior_receipt,
    )


class PolicyAndStageTests(unittest.TestCase):
    def test_reference_module_has_no_io_or_process_runtime_imports(self) -> None:
        tree = ast.parse(inspect.getsource(candidate_v2))
        banned = {
            "asyncio",
            "ctypes",
            "httpx",
            "multiprocessing",
            "os",
            "pathlib",
            "requests",
            "shutil",
            "socket",
            "subprocess",
            "urllib",
        }
        imported_roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, {"open", "exec", "eval", "compile"})
        self.assertFalse(imported_roots & banned)

    def test_policy_valid(self) -> None:
        validate_policy(policy())

    def test_policy_rejects_guard_without_future_region(self) -> None:
        with self.assertRaisesRegex(ValueError, "FUTURE_HORIZON"):
            validate_policy(policy(current_guard_ns=100))

    def test_policy_rejects_live_mode(self) -> None:
        with self.assertRaisesRegex(ValueError, "SHADOW_ONLY"):
            validate_policy(policy(shadow_only=False))

    def test_not_generated_cannot_have_job(self) -> None:
        item = record(generation_job_state=GenerationJobState.SCHEDULED)
        self.assertEqual(validate_stage_record(item), "HOLD_NOT_GENERATED_STAGE_HAS_JOB_STATE")

    def test_scheduled_requires_transition_receipt(self) -> None:
        item = record(
            stage=FileStage.GENERATION_SCHEDULED_OR_RUNNING,
            stage_transition_receipt_hash="",
        )
        self.assertEqual(
            validate_stage_record(item),
            "HOLD_SCHEDULED_STAGE_TRANSITION_RECEIPT_REQUIRED",
        )

    def test_completed_requires_completion_receipt(self) -> None:
        item = record(stage=FileStage.GENERATION_COMPLETED, completion_receipt_hash="")
        self.assertEqual(validate_stage_record(item), "HOLD_COMPLETION_RECEIPTS_REQUIRED")

    def test_cancel_confirmed_requires_outcome_and_worker_fence(self) -> None:
        item = record(
            stage=FileStage.GENERATION_SCHEDULED_OR_RUNNING,
            generation_job_state=GenerationJobState.CANCEL_CONFIRMED,
            cancellation_receipt_hash=H_E,
        )
        self.assertEqual(
            validate_stage_record(item),
            "HOLD_CANCELLATION_AND_WORKER_FENCE_RECEIPTS_REQUIRED",
        )

    def test_already_completed_cancellation_must_transition_to_completed_stage(self) -> None:
        item = record(
            stage=FileStage.GENERATION_SCHEDULED_OR_RUNNING,
            generation_job_state=GenerationJobState.CANCEL_CONFIRMED,
            cancellation_receipt_hash=H_E,
            cancellation_outcome="ALREADY_COMPLETED",
            worker_fence_receipt_hash=H_F,
            worker_fence_state="QUIESCED",
        )
        self.assertEqual(
            validate_stage_record(item),
            "HOLD_CANCELLATION_AND_WORKER_FENCE_RECEIPTS_REQUIRED",
        )

    def test_stage_transition_is_time_bound(self) -> None:
        previous = record(stage_entered_at_ns=T - 20)
        current = record(
            stage=FileStage.GENERATION_SCHEDULED_OR_RUNNING,
            stage_entered_at_ns=T - 5,
            logical_time=2,
            stage_state_hash=H_A,
        )
        receipt = StageTransitionReceipt(
            receipt_id="transition-1",
            record_id=previous.record_id,
            materialization_id=previous.materialization_id,
            from_stage=previous.stage,
            to_stage=current.stage,
            transition_time_ns=T - 5,
            observed_time_ns=current.stage_observed_at_ns,
            stage_sequence=1,
            generation_job_id=current.generation_job_id,
            time_domain_id=current.time_domain_id,
            logical_time=2,
            expected_previous_state_hash=previous.stage_state_hash,
            resulting_state_hash=current.stage_state_hash,
            idempotency_key="transition-key-1",
            transition_state="PASS",
            receipt_hash=current.stage_transition_receipt_hash,
        )
        validate_stage_transition(previous, current, receipt)

    def test_illegal_stage_skip_is_rejected(self) -> None:
        previous = record(stage_entered_at_ns=T - 20)
        current = record(
            stage=FileStage.GENERATION_COMPLETED,
            stage_entered_at_ns=T - 5,
            logical_time=2,
            stage_state_hash=H_A,
        )
        receipt = StageTransitionReceipt(
            receipt_id="transition-1",
            record_id=previous.record_id,
            materialization_id=previous.materialization_id,
            from_stage=previous.stage,
            to_stage=current.stage,
            transition_time_ns=T - 5,
            observed_time_ns=current.stage_observed_at_ns,
            stage_sequence=2,
            generation_job_id=current.generation_job_id,
            time_domain_id=current.time_domain_id,
            logical_time=2,
            expected_previous_state_hash=previous.stage_state_hash,
            resulting_state_hash=current.stage_state_hash,
            idempotency_key="transition-key-1",
            transition_state="PASS",
            receipt_hash=current.stage_transition_receipt_hash,
        )
        with self.assertRaisesRegex(ValueError, "ILLEGAL_STAGE_TRANSITION"):
            validate_stage_transition(previous, current, receipt)

    def test_transition_receipt_must_match_record_hash(self) -> None:
        previous = record(stage_entered_at_ns=T - 20)
        current = record(
            stage=FileStage.GENERATION_SCHEDULED_OR_RUNNING,
            stage_entered_at_ns=T - 5,
            logical_time=2,
            stage_state_hash=H_A,
        )
        receipt = StageTransitionReceipt(
            receipt_id="transition-1",
            record_id=previous.record_id,
            materialization_id=previous.materialization_id,
            from_stage=previous.stage,
            to_stage=current.stage,
            transition_time_ns=T - 5,
            observed_time_ns=current.stage_observed_at_ns,
            stage_sequence=1,
            generation_job_id=current.generation_job_id,
            time_domain_id=current.time_domain_id,
            logical_time=2,
            expected_previous_state_hash=previous.stage_state_hash,
            resulting_state_hash=current.stage_state_hash,
            idempotency_key="transition-key-1",
            transition_state="PASS",
            receipt_hash=H_B,
        )
        with self.assertRaisesRegex(ValueError, "INVALID_STAGE_TRANSITION_RECEIPT"):
            validate_stage_transition(previous, current, receipt)


class WatermarkAndTimeTests(unittest.TestCase):
    def test_exact_membership_watermark(self) -> None:
        self.assertEqual(
            aligned_safe_watermark(
                watermark(), expected_membership_epoch="members-1", now_ns=T
            ),
            T - 22,
        )

    def test_missing_required_node_holds(self) -> None:
        receipt = watermark(observations=watermark().observations[:1])
        with self.assertRaisesRegex(ValueError, "MEMBERSHIP_NOT_EXACT"):
            aligned_safe_watermark(receipt, expected_membership_epoch="members-1", now_ns=T)

    def test_partition_holds(self) -> None:
        with self.assertRaisesRegex(ValueError, "PARTITION"):
            aligned_safe_watermark(
                watermark(partition_state="PARTITIONED"),
                expected_membership_epoch="members-1",
                now_ns=T,
            )

    def test_past_requires_both_event_and_need_before_cut(self) -> None:
        unsafe = record(need_time_ns=T - 50, event_time_ns=T - 10)
        result = classify_record(policy(), unsafe, (), watermark())
        self.assertEqual(result.state, ClassificationState.PAST_HOLD)

    def test_past_requires_snapshot_and_late_reconciliation(self) -> None:
        unsafe = record(
            need_time_ns=T - 50,
            event_time_ns=T - 50,
            ingest_seq=6,
            classification_snapshot_ingest_seq=5,
        )
        result = classify_record(policy(), unsafe, (), watermark())
        self.assertEqual(result.state, ClassificationState.PAST_HOLD)

    def test_past_eligible_after_aligned_cut(self) -> None:
        safe = record(need_time_ns=T - 50, event_time_ns=T - 50)
        result = classify_record(policy(), safe, (), watermark())
        self.assertEqual(result.state, ClassificationState.PAST_ELIGIBLE)

    def test_past_self_report_without_receipts_holds(self) -> None:
        unsafe = record(
            need_time_ns=T - 50,
            event_time_ns=T - 50,
            late_event_reconciliation_receipt_hash="",
            classification_snapshot_receipt_hash="",
        )
        result = classify_record(policy(), unsafe, (), watermark())
        self.assertEqual(result.state, ClassificationState.PAST_HOLD)

    def test_event_after_ingest_is_unaligned(self) -> None:
        unsafe = record(event_time_ns=T, ingest_time_ns=T - 1)
        result = classify_record(policy(), unsafe, (), watermark())
        self.assertEqual(result.state, ClassificationState.UNALIGNED_HOLD)


class RouteAndStageActionTests(unittest.TestCase):
    def test_future_time_alone_is_unknown(self) -> None:
        result = classify_record(policy(), record(), (), None)
        self.assertEqual(result.state, ClassificationState.FUTURE_UNKNOWN_HOLD)

    def test_out_of_horizon_is_hold(self) -> None:
        result = classify_record(policy(), record(need_time_ns=T + 101), (), None)
        self.assertEqual(result.state, ClassificationState.OUT_OF_HORIZON_HOLD)

    def test_reachable_inside_v_protects_all_three_stages(self) -> None:
        route = proof(RouteProofType.REACHABLE_PATH_PROOF)
        expected = {
            FileStage.PREDICTED_NOT_GENERATED: PlannedAction.PROTECT_PRELOAD_CANDIDATE,
            FileStage.GENERATION_SCHEDULED_OR_RUNNING: PlannedAction.CONTINUE_PROTECTED_GENERATION,
            FileStage.GENERATION_COMPLETED: PlannedAction.PROTECT_COMPLETED_MATERIALIZATION,
        }
        for stage, action in expected.items():
            with self.subTest(stage=stage):
                decision = evaluate_action(policy(), record(stage=stage), (route,), None)
                self.assertEqual(decision.action, action)
                self.assertEqual(decision.expected_release_upper_bound_bytes, 0)

    def test_reachable_outside_v_keeps_reference(self) -> None:
        route = proof(RouteProofType.REACHABLE_PATH_PROOF)
        item = record(stage=FileStage.GENERATION_COMPLETED, distance=9)
        decision = evaluate_action(policy(), item, (route,), None)
        self.assertEqual(decision.action, PlannedAction.KEEP_REFERENCE_ONLY)

    def test_prediction_miss_not_generated_cancels_candidate_not_file(self) -> None:
        predicted_miss = proof(RouteProofType.ROUTE_PREDICTION_RECEIPT)
        decision = evaluate_action(policy(), record(distance=2), (predicted_miss,), None)
        self.assertEqual(decision.action, PlannedAction.CANCEL_PREDICTED_CANDIDATE)
        self.assertEqual(decision.expected_release_upper_bound_bytes, 0)

    def test_prediction_miss_inside_v_is_conflict_not_cancel(self) -> None:
        predicted_miss = proof(RouteProofType.ROUTE_PREDICTION_RECEIPT)
        decision = evaluate_action(policy(), record(distance=1), (predicted_miss,), None)
        self.assertEqual(decision.classification, ClassificationState.PROOF_CONFLICT_HOLD)
        self.assertEqual(decision.action, PlannedAction.KEEP_HOLD)

    def test_prediction_miss_beyond_managed_envelope_is_unknown(self) -> None:
        predicted_miss = proof(RouteProofType.ROUTE_PREDICTION_RECEIPT)
        decision = evaluate_action(policy(), record(distance=11), (predicted_miss,), None)
        self.assertEqual(decision.classification, ClassificationState.FUTURE_UNKNOWN_HOLD)

    def test_prediction_miss_does_not_cancel_running_job(self) -> None:
        predicted_miss = proof(RouteProofType.ROUTE_PREDICTION_RECEIPT)
        item = record(stage=FileStage.GENERATION_SCHEDULED_OR_RUNNING, distance=2)
        decision = evaluate_action(policy(), item, (predicted_miss,), None)
        self.assertEqual(decision.action, PlannedAction.KEEP_HOLD)

    def test_prediction_miss_completed_is_soft_only(self) -> None:
        predicted_miss = proof(RouteProofType.ROUTE_PREDICTION_RECEIPT)
        item = record(stage=FileStage.GENERATION_COMPLETED, distance=2)
        decision = evaluate_action(policy(), item, (predicted_miss,), None)
        self.assertEqual(decision.action, PlannedAction.SOFT_EVICT_RECONSTRUCTIBLE)

    def test_prediction_miss_shared_completed_keeps_reference(self) -> None:
        predicted_miss = proof(RouteProofType.ROUTE_PREDICTION_RECEIPT)
        item = record(
            stage=FileStage.GENERATION_COMPLETED,
            distance=2,
            exclusive_to_branch=False,
        )
        decision = evaluate_action(policy(), item, (predicted_miss,), None)
        self.assertEqual(decision.action, PlannedAction.KEEP_REFERENCE_ONLY)

    def test_invalidation_not_generated_removes_candidate(self) -> None:
        invalid = proof(
            RouteProofType.PREDICTION_INVALIDATION_PROOF,
            descendants=("mat-1",),
        )
        decision = evaluate_action(policy(), record(distance=2), (invalid,), None)
        self.assertEqual(decision.action, PlannedAction.CANCEL_PREDICTED_CANDIDATE)

    def test_invalidation_running_requests_cancel_first(self) -> None:
        invalid = proof(
            RouteProofType.PREDICTION_INVALIDATION_PROOF,
            descendants=("mat-1",),
        )
        item = record(stage=FileStage.GENERATION_SCHEDULED_OR_RUNNING, distance=2)
        decision = evaluate_action(policy(), item, (invalid,), None)
        self.assertEqual(decision.action, PlannedAction.REQUEST_GENERATION_CANCELLATION)
        self.assertEqual(decision.expected_release_upper_bound_bytes, 0)

    def test_invalidation_cannot_cancel_shared_running_job(self) -> None:
        invalid = proof(
            RouteProofType.PREDICTION_INVALIDATION_PROOF,
            descendants=("mat-1",),
        )
        item = record(
            stage=FileStage.GENERATION_SCHEDULED_OR_RUNNING,
            distance=2,
            exclusive_to_branch=False,
        )
        decision = evaluate_action(policy(), item, (invalid,), None)
        self.assertEqual(decision.action, PlannedAction.KEEP_HOLD)

    def test_cancelled_running_temp_needs_receipt_then_cleans(self) -> None:
        invalid = proof(
            RouteProofType.PREDICTION_INVALIDATION_PROOF,
            descendants=("mat-1",),
        )
        item = record(
            stage=FileStage.GENERATION_SCHEDULED_OR_RUNNING,
            distance=2,
            generation_job_state=GenerationJobState.CANCEL_CONFIRMED,
            cancellation_receipt_hash=H_E,
            cancellation_outcome="CANCELLED_DURING_RUN",
            worker_fence_receipt_hash=H_F,
            worker_fence_state="QUIESCED",
        )
        decision = evaluate_action(policy(), item, (invalid,), None)
        self.assertEqual(decision.action, PlannedAction.CLEAN_CANCELLED_GENERATION_TEMP)

    def test_invalidation_completed_deletes_only_exclusive_noncanonical(self) -> None:
        invalid = proof(
            RouteProofType.PREDICTION_INVALIDATION_PROOF,
            descendants=("mat-1",),
        )
        decision = evaluate_action(
            policy(), record(stage=FileStage.GENERATION_COMPLETED, distance=2), (invalid,), None
        )
        self.assertEqual(
            decision.action,
            PlannedAction.DELETE_NONCANONICAL_DERIVED_MATERIALIZATION,
        )

    def test_invalidation_shared_or_canonical_detaches(self) -> None:
        invalid = proof(
            RouteProofType.PREDICTION_INVALIDATION_PROOF,
            descendants=("mat-1",),
        )
        for changes in (
            {"exclusive_to_branch": False},
            {"is_canonical_source": True},
        ):
            with self.subTest(changes=changes):
                item = record(stage=FileStage.GENERATION_COMPLETED, distance=2, **changes)
                decision = evaluate_action(policy(), item, (invalid,), None)
                self.assertEqual(
                    decision.action,
                    PlannedAction.DETACH_BRANCH_REFERENCE_RETAIN_CANONICAL,
                )

    def test_exclusion_proof_can_delete_completed_derived(self) -> None:
        excluded = proof(RouteProofType.ROUTE_EXCLUSION_PROOF)
        decision = evaluate_action(
            policy(), record(stage=FileStage.GENERATION_COMPLETED, distance=2), (excluded,), None
        )
        self.assertEqual(
            decision.action,
            PlannedAction.DELETE_NONCANONICAL_DERIVED_MATERIALIZATION,
        )

    def test_open_world_exclusion_is_unknown(self) -> None:
        excluded = proof(
            RouteProofType.ROUTE_EXCLUSION_PROOF,
            closed_world_declared=False,
        )
        result = classify_record(policy(), record(), (excluded,), None)
        self.assertEqual(result.state, ClassificationState.FUTURE_UNKNOWN_HOLD)

    def test_reachable_and_excluded_conflict_holds(self) -> None:
        result = classify_record(
            policy(),
            record(),
            (
                proof(RouteProofType.REACHABLE_PATH_PROOF),
                proof(RouteProofType.ROUTE_EXCLUSION_PROOF),
            ),
            None,
        )
        self.assertEqual(result.state, ClassificationState.PROOF_CONFLICT_HOLD)

    def test_stale_route_root_proof_holds(self) -> None:
        stale = proof(RouteProofType.ROUTE_EXCLUSION_PROOF, route_graph_root=H_3)
        result = classify_record(policy(), record(), (stale,), None)
        self.assertEqual(result.state, ClassificationState.FUTURE_UNKNOWN_HOLD)

    def test_record_must_be_in_invalidation_closure(self) -> None:
        invalid = proof(
            RouteProofType.PREDICTION_INVALIDATION_PROOF,
            descendants=("different",),
        )
        result = classify_record(policy(), record(), (invalid,), None)
        self.assertEqual(result.state, ClassificationState.FUTURE_UNKNOWN_HOLD)

    def test_invalidation_proof_branch_must_match_record(self) -> None:
        invalid = proof(
            RouteProofType.PREDICTION_INVALIDATION_PROOF,
            descendants=("mat-1",),
            branch_id="other-branch",
        )
        result = classify_record(policy(), record(distance=2), (invalid,), None)
        self.assertEqual(result.state, ClassificationState.FUTURE_UNKNOWN_HOLD)

    def test_proof_content_binding_must_match_record(self) -> None:
        excluded = proof(
            RouteProofType.ROUTE_EXCLUSION_PROOF,
            bindings=(f"mat-1:{H_D}",),
        )
        result = classify_record(policy(), record(distance=2), (excluded,), None)
        self.assertEqual(result.state, ClassificationState.FUTURE_UNKNOWN_HOLD)

    def test_proof_binding_hash_tamper_holds(self) -> None:
        excluded = replace(
            proof(RouteProofType.ROUTE_EXCLUSION_PROOF),
            proof_hash="0" * 64,
        )
        result = classify_record(policy(), record(distance=2), (excluded,), None)
        self.assertEqual(result.state, ClassificationState.FUTURE_UNKNOWN_HOLD)

    def test_two_distinct_proofs_of_same_type_conflict(self) -> None:
        first = proof(RouteProofType.REACHABLE_PATH_PROOF)
        second = proof(RouteProofType.REACHABLE_PATH_PROOF, proof_id="proof-2")
        result = classify_record(policy(), record(distance=1), (first, second), None)
        self.assertEqual(result.state, ClassificationState.PROOF_CONFLICT_HOLD)


class PlanningAndCommitTests(unittest.TestCase):
    def test_branch_invalidation_accounts_all_three_stages(self) -> None:
        records = (
            record(materialization_id="m-p", physical_allocation_id="a-p", distance=2),
            record(
                materialization_id="m-r",
                physical_allocation_id="a-r",
                record_id="record-r",
                stage=FileStage.GENERATION_SCHEDULED_OR_RUNNING,
                distance=2,
            ),
            record(
                materialization_id="m-c",
                physical_allocation_id="a-c",
                record_id="record-c",
                stage=FileStage.GENERATION_COMPLETED,
                distance=2,
            ),
            record(
                materialization_id="m-shared",
                physical_allocation_id="a-shared",
                record_id="record-shared",
                stage=FileStage.GENERATION_COMPLETED,
                distance=2,
                exclusive_to_branch=False,
            ),
        )
        invalid = proof(
            RouteProofType.PREDICTION_INVALIDATION_PROOF,
            descendants=tuple(item.materialization_id for item in records),
        )
        plan = plan_branch_invalidation(policy(), records, invalid)
        self.assertEqual(plan.state, "PENDING_CANCELLATION_RECEIPTS_SHADOW_PLAN")
        self.assertEqual(plan.planned_release_upper_bound_bytes, 4096)
        self.assertTrue(plan.graph_closure_complete)
        self.assertFalse(plan.action_plan_terminal)
        self.assertFalse(plan.cleanup_commit_complete)
        self.assertEqual(
            {decision.action for decision in plan.decisions},
            {
                PlannedAction.CANCEL_PREDICTED_CANDIDATE,
                PlannedAction.REQUEST_GENERATION_CANCELLATION,
                PlannedAction.DELETE_NONCANONICAL_DERIVED_MATERIALIZATION,
                PlannedAction.DETACH_BRANCH_REFERENCE_RETAIN_CANONICAL,
            },
        )

    def test_branch_closure_must_be_exact(self) -> None:
        invalid = proof(
            RouteProofType.PREDICTION_INVALIDATION_PROOF,
            descendants=("mat-1", "missing"),
        )
        plan = plan_branch_invalidation(policy(), (record(),), invalid)
        self.assertEqual(plan.state, "HOLD_DESCENDANT_CLOSURE_INCOMPLETE")
        self.assertFalse(plan.graph_closure_complete)
        self.assertFalse(plan.action_plan_terminal)
        self.assertFalse(plan.cleanup_commit_complete)

    def test_empty_branch_closure_never_passes(self) -> None:
        invalid = proof(
            RouteProofType.PREDICTION_INVALIDATION_PROOF,
            descendants=(),
            bindings=(),
        )
        plan = plan_branch_invalidation(policy(), (), invalid)
        self.assertEqual(
            plan.state,
            "HOLD_NONEMPTY_GRAPH_DERIVED_DESCENDANT_CLOSURE_REQUIRED",
        )
        self.assertFalse(plan.graph_closure_complete)
        self.assertFalse(plan.action_plan_terminal)
        self.assertFalse(plan.cleanup_commit_complete)

    def test_branch_gate_rejects_ineligible_action(self) -> None:
        item = record(stage=FileStage.GENERATION_COMPLETED, distance=2, active_lease_count=1)
        invalid = proof(
            RouteProofType.PREDICTION_INVALIDATION_PROOF,
            descendants=(item.materialization_id,),
        )
        plan = plan_branch_invalidation(policy(), (item,), invalid)
        self.assertEqual(plan.state, "HOLD_BRANCH_ACTION_NOT_ELIGIBLE")
        self.assertEqual(plan.planned_release_upper_bound_bytes, 0)
        self.assertTrue(plan.graph_closure_complete)
        self.assertFalse(plan.action_plan_terminal)
        self.assertFalse(plan.cleanup_commit_complete)

    def test_current_guard_cannot_pass_branch_invalidation_plan(self) -> None:
        item = record(need_time_ns=T + 5, distance=1)
        invalid = proof(
            RouteProofType.PREDICTION_INVALIDATION_PROOF,
            descendants=(item.materialization_id,),
        )
        plan = plan_branch_invalidation(policy(), (item,), invalid)
        self.assertEqual(plan.state, "HOLD_BRANCH_ACTION_NOT_ELIGIBLE")
        self.assertEqual(plan.decisions[0].action, PlannedAction.PROTECT_CURRENT)
        self.assertEqual(plan.planned_release_upper_bound_bytes, 0)
        self.assertTrue(plan.graph_closure_complete)
        self.assertFalse(plan.action_plan_terminal)
        self.assertFalse(plan.cleanup_commit_complete)

    def test_terminal_shadow_branch_plan_is_not_cleanup_commit(self) -> None:
        item = record(stage=FileStage.GENERATION_COMPLETED, distance=2)
        invalid = proof(
            RouteProofType.PREDICTION_INVALIDATION_PROOF,
            descendants=(item.materialization_id,),
        )
        plan = plan_branch_invalidation(policy(), (item,), invalid)
        self.assertEqual(plan.state, "PASS_SHADOW_BRANCH_INVALIDATION_PLAN")
        self.assertTrue(plan.graph_closure_complete)
        self.assertTrue(plan.action_plan_terminal)
        self.assertFalse(plan.cleanup_commit_complete)

    def test_duplicate_materialization_id_holds(self) -> None:
        first = record(stage=FileStage.GENERATION_COMPLETED)
        second = record(
            stage=FileStage.GENERATION_COMPLETED,
            distance=2,
            physical_allocation_id="alloc-2",
            record_id="record-2",
        )
        plan = plan_memory_pressure(
            policy(), (first, second), {}, target_release_bytes=1
        )
        self.assertIn("DUPLICATE_MATERIALIZATION_ID", plan.state)

    def test_logical_identity_content_conflict_holds(self) -> None:
        first = record(materialization_id="m1")
        second = record(materialization_id="m2", content_hash=H_D)
        plan = plan_memory_pressure(
            policy(), (first, second), {}, target_release_bytes=1
        )
        self.assertIn("IDENTITY_CONFLICT", plan.state)

    def test_shared_allocation_counted_once(self) -> None:
        first = record(
            materialization_id="m1",
            physical_allocation_id="shared",
            record_id="r1",
            stage=FileStage.GENERATION_COMPLETED,
            distance=2,
        )
        second = record(
            materialization_id="m2",
            physical_allocation_id="shared",
            record_id="r2",
            stage=FileStage.GENERATION_COMPLETED,
            distance=2,
        )
        invalid = proof(
            RouteProofType.PREDICTION_INVALIDATION_PROOF,
            descendants=("m1", "m2"),
        )
        plan = plan_memory_pressure(
            policy(),
            (first, second),
            {"m1": (invalid,), "m2": (invalid,)},
            target_release_bytes=8192,
        )
        self.assertEqual(plan.planned_release_upper_bound_bytes, 4096)
        self.assertEqual(plan.selected_physical_allocation_ids, ("shared",))

    def test_retained_coowner_makes_shared_allocation_nonreclaimable(self) -> None:
        derived = record(
            materialization_id="m-derived",
            physical_allocation_id="shared",
            record_id="r-derived",
            stage=FileStage.GENERATION_COMPLETED,
            distance=2,
        )
        canonical = record(
            materialization_id="m-canonical",
            physical_allocation_id="shared",
            record_id="r-canonical",
            stage=FileStage.GENERATION_COMPLETED,
            distance=2,
            is_canonical_source=True,
            exclusive_to_branch=False,
        )
        invalid = proof(
            RouteProofType.PREDICTION_INVALIDATION_PROOF,
            descendants=("m-derived", "m-canonical"),
        )
        proof_map = {"m-derived": (invalid,), "m-canonical": (invalid,)}
        for ordered in ((derived, canonical), (canonical, derived)):
            with self.subTest(order=ordered[0].materialization_id):
                plan = plan_memory_pressure(
                    policy(), ordered, proof_map, target_release_bytes=1
                )
                self.assertEqual(plan.planned_release_upper_bound_bytes, 0)
                self.assertEqual(plan.selected_physical_allocation_ids, ())

    def test_quarantine_move_does_not_claim_release(self) -> None:
        past = record(
            stage=FileStage.GENERATION_COMPLETED,
            need_time_ns=T - 50,
            event_time_ns=T - 50,
        )
        decision = evaluate_action(policy(), past, (), watermark())
        self.assertEqual(
            decision.action,
            PlannedAction.MOVE_PAST_MATERIALIZATION_TO_QUARANTINE,
        )
        self.assertEqual(decision.expected_release_upper_bound_bytes, 0)

    def test_commit_rechecks_generation_and_lifecycle_tokens(self) -> None:
        item = record(stage=FileStage.GENERATION_COMPLETED, distance=2)
        predicted = proof(RouteProofType.ROUTE_PREDICTION_RECEIPT)
        decision = evaluate_action(policy(), item, (predicted,), None)
        token = make_decision_token(
            policy(), item, decision, decision_id="d1", idempotency_key="i1", allocation_owner_records=(item,), expires_at_ns=T + 100
        )
        changed = replace(item, lifecycle_snapshot_token="changed")
        receipt = simulate_current(
            token,
            changed,
            (predicted,),
            actual_released_bytes=4096,
            owner_records=(changed,),
        )
        self.assertEqual(receipt.cas_result, "HOLD_CAS_MISMATCH")
        self.assertEqual(receipt.actual_released_bytes, 0)
        self.assertEqual(receipt.failure_code, "LIFECYCLE_SNAPSHOT_TOKEN_MISMATCH")

    def test_commit_rechecks_canonical_references_and_leases(self) -> None:
        item = record(stage=FileStage.GENERATION_COMPLETED, distance=2)
        predicted = proof(RouteProofType.ROUTE_PREDICTION_RECEIPT)
        decision = evaluate_action(policy(), item, (predicted,), None)
        token = make_decision_token(
            policy(), item, decision, decision_id="d1", idempotency_key="i1", allocation_owner_records=(item,), expires_at_ns=T + 100
        )
        unsafe = replace(
            item,
            is_canonical_source=True,
            live_reference_count=9,
            active_lease_count=2,
        )
        receipt = simulate_current(
            token,
            unsafe,
            (predicted,),
            actual_released_bytes=4096,
            owner_records=(unsafe,),
        )
        self.assertEqual(receipt.cas_result, "HOLD_CAS_MISMATCH")
        self.assertEqual(receipt.actual_released_bytes, 0)
        self.assertEqual(receipt.failure_code, "HOLD_CANONICAL_SOURCE_NEVER_DELETED")

    def test_commit_rejects_actual_release_above_upper_bound(self) -> None:
        item = record(stage=FileStage.GENERATION_COMPLETED, distance=2)
        predicted = proof(RouteProofType.ROUTE_PREDICTION_RECEIPT)
        decision = evaluate_action(policy(), item, (predicted,), None)
        token = make_decision_token(
            policy(), item, decision, decision_id="d1", idempotency_key="i1", allocation_owner_records=(item,), expires_at_ns=T + 100
        )
        receipt = simulate_current(
            token,
            item,
            (predicted,),
            actual_released_bytes=4097,
        )
        self.assertEqual(receipt.cas_result, "HOLD_CAS_MISMATCH")
        self.assertEqual(receipt.actual_released_bytes, 0)
        self.assertEqual(receipt.failure_code, "ACTUAL_RELEASE_EXCEEDS_UPPER_BOUND")

    def test_commit_rejects_stale_proof_or_policy(self) -> None:
        item = record(stage=FileStage.GENERATION_COMPLETED, distance=2)
        predicted = proof(RouteProofType.ROUTE_PREDICTION_RECEIPT)
        decision = evaluate_action(policy(), item, (predicted,), None)
        token = make_decision_token(
            policy(), item, decision, decision_id="d1", idempotency_key="i1", allocation_owner_records=(item,), expires_at_ns=T + 100
        )
        stale_proof = replace(predicted, proof_hash=H_B)
        receipt = simulate_current(
            token,
            item,
            (stale_proof,),
            actual_released_bytes=4096,
            current_policy=policy(policy_epoch="policy-2"),
        )
        self.assertEqual(receipt.cas_result, "HOLD_CAS_MISMATCH")

    def test_forged_action_is_recomputed_and_rejected(self) -> None:
        item = record(stage=FileStage.GENERATION_COMPLETED, distance=2)
        predicted = proof(RouteProofType.ROUTE_PREDICTION_RECEIPT)
        legitimate = evaluate_action(policy(), item, (predicted,), None)
        forged = replace(
            legitimate,
            action=PlannedAction.DELETE_NONCANONICAL_DERIVED_MATERIALIZATION,
            classification=ClassificationState.FUTURE_ROUTE_EXCLUDED,
        )
        token = make_decision_token(
            policy(), item, forged, decision_id="forged", idempotency_key="forged-key", allocation_owner_records=(item,), expires_at_ns=T + 100
        )
        receipt = simulate_current(
            token, item, (predicted,), actual_released_bytes=4096
        )
        self.assertEqual(receipt.cas_result, "HOLD_CAS_MISMATCH")
        self.assertEqual(receipt.failure_code, "DECISION_REVALIDATION_MISMATCH")

    def test_shared_allocation_cannot_make_single_record_reclaim_token(self) -> None:
        first = record(stage=FileStage.GENERATION_COMPLETED, distance=2)
        second = record(
            materialization_id="mat-2",
            physical_allocation_id=first.physical_allocation_id,
            record_id="record-2",
            stage=FileStage.GENERATION_COMPLETED,
            distance=2,
        )
        predicted = proof(RouteProofType.ROUTE_PREDICTION_RECEIPT)
        decision = evaluate_action(policy(), first, (predicted,), None)
        with self.assertRaisesRegex(ValueError, "ATOMIC_GROUP_COMMIT_TOKEN"):
            make_decision_token(
                policy(), first, decision, decision_id="d1", idempotency_key="i1", allocation_owner_records=(first, second), expires_at_ns=T + 100
            )

    def test_new_allocation_coowner_invalidates_commit_token(self) -> None:
        item = record(stage=FileStage.GENERATION_COMPLETED, distance=2)
        predicted = proof(RouteProofType.ROUTE_PREDICTION_RECEIPT)
        decision = evaluate_action(policy(), item, (predicted,), None)
        token = make_decision_token(
            policy(), item, decision, decision_id="d1", idempotency_key="i1", allocation_owner_records=(item,), expires_at_ns=T + 100
        )
        coowner = record(
            materialization_id="mat-2",
            physical_allocation_id=item.physical_allocation_id,
            record_id="record-2",
            stage=FileStage.GENERATION_COMPLETED,
            distance=2,
        )
        receipt = simulate_current(
            token,
            item,
            (predicted,),
            actual_released_bytes=4096,
            owner_records=(item, coowner),
        )
        self.assertEqual(receipt.cas_result, "HOLD_CAS_MISMATCH")
        self.assertEqual(receipt.failure_code, "ALLOCATION_OWNER_SET_CHANGED")

    def test_idempotency_returns_original_receipt(self) -> None:
        item = record(stage=FileStage.GENERATION_COMPLETED, distance=2)
        predicted = proof(RouteProofType.ROUTE_PREDICTION_RECEIPT)
        decision = evaluate_action(policy(), item, (predicted,), None)
        token = make_decision_token(
            policy(), item, decision, decision_id="d1", idempotency_key="i1", allocation_owner_records=(item,), expires_at_ns=T + 100
        )
        first = simulate_current(
            token, item, (predicted,), actual_released_bytes=4096
        )
        second = simulate_current(
            token,
            item,
            (predicted,),
            actual_released_bytes=9999,
            prior_receipt=first,
        )
        self.assertIs(first, second)
        self.assertEqual(second.actual_released_bytes, 4096)

    def test_expired_decision_token_holds(self) -> None:
        item = record(stage=FileStage.GENERATION_COMPLETED, distance=2)
        predicted = proof(RouteProofType.ROUTE_PREDICTION_RECEIPT)
        decision = evaluate_action(policy(), item, (predicted,), None)
        token = make_decision_token(
            policy(), item, decision, decision_id="d1", idempotency_key="i1", allocation_owner_records=(item,), expires_at_ns=T - 1
        )
        receipt = simulate_current(
            token, item, (predicted,), actual_released_bytes=4096
        )
        self.assertEqual(receipt.failure_code, "DECISION_TOKEN_EXPIRED")

    def test_prior_receipt_must_bind_same_decision_token(self) -> None:
        item = record(stage=FileStage.GENERATION_COMPLETED, distance=2)
        predicted = proof(RouteProofType.ROUTE_PREDICTION_RECEIPT)
        decision = evaluate_action(policy(), item, (predicted,), None)
        first_token = make_decision_token(
            policy(), item, decision, decision_id="d1", idempotency_key="same-key", allocation_owner_records=(item,), expires_at_ns=T + 100
        )
        first_receipt = simulate_current(
            first_token, item, (predicted,), actual_released_bytes=4096
        )
        second_token = make_decision_token(
            policy(), item, decision, decision_id="d2", idempotency_key="same-key", allocation_owner_records=(item,), expires_at_ns=T + 100
        )
        with self.assertRaisesRegex(ValueError, "PRIOR_RECEIPT_DECISION_BINDING_MISMATCH"):
            simulate_current(
                second_token,
                item,
                (predicted,),
                actual_released_bytes=4096,
                prior_receipt=first_receipt,
            )

    def test_forged_live_prior_receipt_cannot_bypass_simulation_authority(self) -> None:
        item = record(stage=FileStage.GENERATION_COMPLETED, distance=2)
        predicted = proof(RouteProofType.ROUTE_PREDICTION_RECEIPT)
        decision = evaluate_action(policy(), item, (predicted,), None)
        token = make_decision_token(
            policy(), item, decision, decision_id="d1", idempotency_key="i1", allocation_owner_records=(item,), expires_at_ns=T + 100
        )
        valid = simulate_current(
            token, item, (predicted,), actual_released_bytes=4096
        )
        unsigned_forgery = replace(
            valid,
            receipt_id="",
            cas_result="COMMITTED",
            actual_released_bytes=999_999_999,
            simulation_only=False,
            failure_code=None,
            receipt_hash="0" * 64,
        )
        forged_hash = commit_receipt_binding_hash(unsigned_forgery)
        forged = replace(
            unsigned_forgery,
            receipt_id="sim-" + forged_hash[:24],
            receipt_hash=forged_hash,
        )
        with self.assertRaisesRegex(ValueError, "LIVE_AUTHORITY_UNVERIFIED"):
            simulate_current(
                token,
                item,
                (predicted,),
                actual_released_bytes=0,
                prior_receipt=forged,
            )
        self.assertEqual(
            false_miss_receipt_state(
                forged,
                decision_token=token,
                actual_hit=True,
                demand_event_id="demand-forged",
                demand_materialization_id=item.materialization_id,
                demand_prediction_epoch="prediction-1",
                demand_route_epoch="route-1",
                reconstructed_content_hash=item.content_hash,
            ),
            "HOLD_PRIOR_RECEIPT_LIVE_AUTHORITY_UNVERIFIED",
        )

    def test_false_miss_requires_committed_soft_evict(self) -> None:
        item = record(stage=FileStage.GENERATION_COMPLETED, distance=2)
        predicted = proof(RouteProofType.ROUTE_PREDICTION_RECEIPT)
        decision = evaluate_action(policy(), item, (predicted,), None)
        token = make_decision_token(
            policy(), item, decision, decision_id="d1", idempotency_key="i1", allocation_owner_records=(item,), expires_at_ns=T + 100
        )
        receipt = simulate_current(
            token, item, (predicted,), actual_released_bytes=4096
        )
        self.assertEqual(
            false_miss_receipt_state(
                receipt,
                decision_token=token,
                actual_hit=True,
                demand_event_id="demand-1",
                demand_materialization_id=item.materialization_id,
                demand_prediction_epoch="prediction-1",
                demand_route_epoch="route-1",
                reconstructed_content_hash=item.content_hash,
            ),
            "SIMULATED_FALSE_MISS_BYTE_EXACT",
        )

    def test_false_miss_uses_commit_bound_content_not_caller_hash(self) -> None:
        item = record(stage=FileStage.GENERATION_COMPLETED, distance=2)
        predicted = proof(RouteProofType.ROUTE_PREDICTION_RECEIPT)
        decision = evaluate_action(policy(), item, (predicted,), None)
        token = make_decision_token(
            policy(), item, decision, decision_id="d1", idempotency_key="i1", allocation_owner_records=(item,), expires_at_ns=T + 100
        )
        receipt = simulate_current(
            token,
            item,
            (predicted,),
            actual_released_bytes=4096,
        )
        self.assertEqual(
            false_miss_receipt_state(
                receipt,
                decision_token=token,
                actual_hit=True,
                demand_event_id="demand-1",
                demand_materialization_id=item.materialization_id,
                demand_prediction_epoch="prediction-1",
                demand_route_epoch="route-1",
                reconstructed_content_hash=H_A,
            ),
            "REHYDRATION_FAILURE_HOLD",
        )

    def test_false_miss_epoch_change_is_regeneration(self) -> None:
        item = record(stage=FileStage.GENERATION_COMPLETED, distance=2)
        predicted = proof(RouteProofType.ROUTE_PREDICTION_RECEIPT)
        decision = evaluate_action(policy(), item, (predicted,), None)
        token = make_decision_token(
            policy(), item, decision, decision_id="d1", idempotency_key="i1", allocation_owner_records=(item,), expires_at_ns=T + 100
        )
        receipt = simulate_current(
            token,
            item,
            (predicted,),
            actual_released_bytes=4096,
        )
        self.assertEqual(
            false_miss_receipt_state(
                receipt,
                decision_token=token,
                actual_hit=True,
                demand_event_id="demand-1",
                demand_materialization_id=item.materialization_id,
                demand_prediction_epoch="prediction-2",
                demand_route_epoch="route-2",
                reconstructed_content_hash=item.content_hash,
            ),
            "ROUTE_CHANGE_REGENERATION",
        )

    def test_keep_hold_cannot_create_false_miss(self) -> None:
        item = record(stage=FileStage.GENERATION_SCHEDULED_OR_RUNNING, distance=2)
        predicted = proof(RouteProofType.ROUTE_PREDICTION_RECEIPT)
        decision = evaluate_action(policy(), item, (predicted,), None)
        token = make_decision_token(
            policy(), item, decision, decision_id="d1", idempotency_key="i1", allocation_owner_records=(item,), expires_at_ns=T + 100
        )
        receipt = simulate_current(
            token, item, (predicted,), actual_released_bytes=0
        )
        self.assertEqual(
            false_miss_receipt_state(
                receipt,
                decision_token=token,
                actual_hit=True,
                demand_event_id="demand-1",
                demand_materialization_id=item.materialization_id,
                demand_prediction_epoch="prediction-1",
                demand_route_epoch="route-1",
                reconstructed_content_hash=item.content_hash,
            ),
            "NOT_A_FALSE_MISS",
        )


class BudgetAndPropertyTests(unittest.TestCase):
    def test_basis_points_above_10000_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "10000"):
            evaluate_budget_adjustment_candidate(
                current_limit_bytes=2_000_000_000,
                proposed_limit_bytes=3_000_000_000,
                gate=gate(),
                evidence=evidence(false_miss_rate_bp=10_001),
            )

    def test_proposed_limit_cannot_exceed_capacity(self) -> None:
        decision = evaluate_budget_adjustment_candidate(
            current_limit_bytes=2_000_000_000,
            proposed_limit_bytes=20_000_000_000,
            gate=gate(),
            evidence=evidence(),
        )
        self.assertEqual(decision.reason, "HOLD_PROPOSED_LIMIT_EXCEEDS_HOST_CAPACITY")

    def test_capacity_evidence_must_be_arithmetically_consistent(self) -> None:
        decision = evaluate_budget_adjustment_candidate(
            current_limit_bytes=2_000_000_000,
            proposed_limit_bytes=15_000_000_000,
            gate=gate(),
            evidence=evidence(host_available_after_adjustment_bytes=4_000_000_000),
        )
        self.assertEqual(decision.reason, "HOLD_HOST_CAPACITY_EVIDENCE_INCONSISTENT")

    def test_two_gib_is_adjustable_when_ux_gates_pass(self) -> None:
        decision = evaluate_budget_adjustment_candidate(
            current_limit_bytes=2 * 1024**3,
            proposed_limit_bytes=3 * 1024**3,
            gate=gate(),
            evidence=evidence(),
        )
        self.assertEqual(decision.state, "PASS_MEASUREMENT_CANDIDATE_ONLY")
        self.assertFalse(decision.applies_change)

    def test_task_success_regression_holds_even_if_memory_fits(self) -> None:
        decision = evaluate_budget_adjustment_candidate(
            current_limit_bytes=2 * 1024**3,
            proposed_limit_bytes=3 * 1024**3,
            gate=gate(),
            evidence=evidence(task_success_regression_bp=51),
        )
        self.assertEqual(decision.reason, "HOLD_TASK_SUCCESS_REGRESSION")

    def test_random_reachable_inside_v_never_reclaims(self) -> None:
        rng = random.Random(70818)
        stages = tuple(FileStage)
        for index in range(500):
            offset = rng.randint(11, 100)
            knot_radius = 1 if offset < 50 else (5 if offset < 100 else 8)
            stage = rng.choice(stages)
            item = record(
                materialization_id=f"m-{index}",
                physical_allocation_id=f"a-{index}",
                record_id=f"r-{index}",
                stage=stage,
                need_time_ns=T + offset,
                distance=rng.randint(0, knot_radius),
            )
            route = proof(
                RouteProofType.REACHABLE_PATH_PROOF,
                bindings=(materialization_binding(item),),
            )
            decision = evaluate_action(policy(), item, (route,), None)
            self.assertIn(
                decision.action,
                {
                    PlannedAction.PROTECT_PRELOAD_CANDIDATE,
                    PlannedAction.CONTINUE_PROTECTED_GENERATION,
                    PlannedAction.PROTECT_COMPLETED_MATERIALIZATION,
                },
            )
            self.assertEqual(decision.expected_release_upper_bound_bytes, 0)


if __name__ == "__main__":
    unittest.main()
