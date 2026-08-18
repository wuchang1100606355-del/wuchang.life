from __future__ import annotations

import importlib.util
import json
import random
import sys
import unittest
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "total_field" / "moving_v_preload_cleanup_candidate.py"
SPEC = importlib.util.spec_from_file_location("moving_v_candidate", MODULE_PATH)
assert SPEC and SPEC.loader
moving_v = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = moving_v
SPEC.loader.exec_module(moving_v)


def policy_from_candidate_config() -> moving_v.MovingVPolicy:
    path = ROOT / "configs" / "total_field" / "w7tp_moving_v_preload_cleanup_v1.candidate.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    policy = payload["policy"]
    return moving_v.MovingVPolicy(
        policy_id=policy["policy_id"],
        prediction_epoch=policy["prediction_epoch"],
        apex_time_ns=policy["apex_time_ns"],
        safe_watermark_ns=policy["safe_watermark_ns"],
        current_guard_ns=policy["current_guard_ns"],
        clock_uncertainty_ns=policy["clock_uncertainty_ns"],
        past_grace_ns=policy["past_grace_ns"],
        future_horizon_ns=policy["future_horizon_ns"],
        envelope=tuple(moving_v.EnvelopeKnot(**knot) for knot in policy["envelope"]),
    )


def record(
    policy: moving_v.MovingVPolicy,
    *,
    record_id: str = "r1",
    delta_ns: int,
    distance: int | None,
    **overrides,
) -> moving_v.MemoryRecord:
    values = {
        "record_id": record_id,
        "need_time_ns": policy.apex_time_ns + delta_ns,
        "event_time_ns": policy.apex_time_ns,
        "ingest_time_ns": policy.apex_time_ns,
        "adi_absolute_distance_uint": distance,
        "prediction_epoch": policy.prediction_epoch,
        "record_version": 7,
        "storage_tier": "RAM",
        "resident_bytes": 4096,
        "live_reference_count": 0,
        "active_lease": False,
        "pinned": False,
        "durable_source_verified": True,
        "reconstruction_reference": "gtp://packet/r1",
        "expected_source_hash": "a" * 64,
        "observed_source_hash": "a" * 64,
        "is_canonical_source": False,
    }
    values.update(overrides)
    return moving_v.MemoryRecord(**values)


def decision(policy, item, *, version=None, epoch=None):
    return moving_v.evaluate_eviction(
        policy,
        item,
        expected_record_version=item.record_version if version is None else version,
        expected_prediction_epoch=policy.prediction_epoch if epoch is None else epoch,
    )


class MovingVGeometryTests(unittest.TestCase):
    def setUp(self):
        self.policy = policy_from_candidate_config()

    def test_candidate_contract_is_explicitly_non_runtime(self):
        path = ROOT / "configs" / "total_field" / "w7tp_moving_v_preload_cleanup_v1.candidate.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "CANDIDATE_ONLY")
        self.assertEqual(payload["mode"], "STATIC_SIMULATION_ONLY")
        self.assertFalse(payload["authority"]["runtime_approved"])
        self.assertFalse(payload["authority"]["hard_delete_enabled"])
        self.assertFalse(payload["authority"]["canonical_source_delete_allowed"])
        self.assertEqual(
            payload["adi_binding"]["distance_input"],
            "FOUNDER_NATIVE_ADI_DELTA_F_UINT_ONLY",
        )
        self.assertEqual(
            payload["optimization_contract"]["founder_intent"],
            "BETTER_EFFECT_AND_BETTER_HUMAN_USER_EXPERIENCE",
        )
        self.assertEqual(
            payload["optimization_contract"]["numeric_parameter_policy"],
            "ALL_NUMERIC_VALUES_ARE_TUNABLE_WITH_EVIDENCE",
        )
        self.assertTrue(payload["memory_budget"]["adjustable"])
        self.assertEqual(payload["memory_budget"]["initial_candidate_bytes"], 2 * 1024**3)
        budget = payload["memory_budget"]
        self.assertLess(budget["low_watermark_bytes"], budget["high_watermark_bytes"])
        self.assertLessEqual(budget["high_watermark_bytes"], budget["max_resident_bytes"])
        self.assertEqual(budget["adjustment_gate_state"], "THRESHOLDS_NOT_CALIBRATED")

    def test_policy_encodes_wider_preload_and_smaller_side_cleanup(self):
        moving_v.validate_policy(self.policy)
        protected = [k.protected_radius_uint for k in self.policy.envelope]
        side = [k.side_cleanup_width_uint for k in self.policy.envelope]
        self.assertEqual(protected, sorted(protected))
        self.assertEqual(side, sorted(side, reverse=True))
        self.assertEqual(side, [64, 48, 32, 16])

    def test_policy_rejects_growing_future_side_cleanup_width(self):
        invalid = replace(
            self.policy,
            envelope=(
                moving_v.EnvelopeKnot(0, 0, 10),
                moving_v.EnvelopeKnot(self.policy.future_horizon_ns, 1, 20),
            ),
        )
        with self.assertRaisesRegex(ValueError, "FUTURE_SIDE_CLEANUP_WIDTH_MUST_NOT_GROW"):
            moving_v.validate_policy(invalid)

    def test_policy_rejects_shrinking_preload_radius(self):
        invalid = replace(
            self.policy,
            envelope=(
                moving_v.EnvelopeKnot(0, 5, 15),
                moving_v.EnvelopeKnot(self.policy.future_horizon_ns, 4, 10),
            ),
        )
        with self.assertRaisesRegex(ValueError, "FUTURE_PROTECTED_RADIUS_MUST_NOT_SHRINK"):
            moving_v.validate_policy(invalid)

    def test_current_guard_must_cover_clock_uncertainty(self):
        invalid = replace(
            self.policy,
            current_guard_ns=self.policy.clock_uncertainty_ns - 1,
        )
        with self.assertRaisesRegex(ValueError, "CURRENT_GUARD_MUST_COVER_CLOCK_UNCERTAINTY"):
            moving_v.validate_policy(invalid)

    def test_apex_is_current_guard(self):
        result = moving_v.classify_record(self.policy, record(self.policy, delta_ns=0, distance=None))
        self.assertEqual(result.state, moving_v.GeometryState.CURRENT_GUARD)

    def test_inside_future_v_is_protected(self):
        item = record(self.policy, delta_ns=30_000_000_000, distance=39)
        self.assertEqual(
            moving_v.classify_record(self.policy, item).state,
            moving_v.GeometryState.FUTURE_PROTECTED,
        )

    def test_v_boundary_is_protected_not_cleaned(self):
        item = record(self.policy, delta_ns=30_000_000_000, distance=40)
        result = decision(self.policy, item)
        self.assertEqual(result.classification, moving_v.GeometryState.FUTURE_PROTECTED)
        self.assertEqual(result.action, moving_v.MemoryAction.PROTECT_PRELOAD)

    def test_v_side_is_predicted_miss(self):
        item = record(self.policy, delta_ns=30_000_000_000, distance=41)
        result = moving_v.classify_record(self.policy, item)
        self.assertEqual(result.state, moving_v.GeometryState.FUTURE_PREDICTED_MISS)

    def test_outside_finite_envelope_fails_closed(self):
        item = record(self.policy, delta_ns=30_000_000_000, distance=73)
        result = moving_v.classify_record(self.policy, item)
        self.assertEqual(result.state, moving_v.GeometryState.OUTSIDE_MANAGED_ENVELOPE_HOLD)

    def test_out_of_horizon_is_not_called_a_miss(self):
        item = record(self.policy, delta_ns=60_000_000_001, distance=None)
        result = decision(self.policy, item)
        self.assertEqual(result.classification, moving_v.GeometryState.OUT_OF_HORIZON)
        self.assertEqual(result.action, moving_v.MemoryAction.NO_PRELOAD_KEEP_REFERENCE)

    def test_missing_adi_distance_fails_closed(self):
        item = record(self.policy, delta_ns=30_000_000_000, distance=None)
        result = moving_v.classify_record(self.policy, item)
        self.assertEqual(result.state, moving_v.GeometryState.UNALIGNED_HOLD)

    def test_prediction_epoch_mismatch_fails_closed(self):
        item = record(
            self.policy,
            delta_ns=30_000_000_000,
            distance=41,
            prediction_epoch="OLD_EPOCH",
        )
        result = decision(self.policy, item)
        self.assertEqual(result.classification, moving_v.GeometryState.UNALIGNED_HOLD)
        self.assertEqual(result.action, moving_v.MemoryAction.KEEP_HOLD)

    def test_invalid_time_and_version_fail_closed(self):
        invalid_time = replace(self.side_record(), need_time_ns=-1)
        self.assertEqual(
            moving_v.classify_record(self.policy, invalid_time).state,
            moving_v.GeometryState.UNALIGNED_HOLD,
        )
        invalid_version = replace(self.side_record(), record_version=True)
        self.assertEqual(
            moving_v.classify_record(self.policy, invalid_version).state,
            moving_v.GeometryState.UNALIGNED_HOLD,
        )

    def test_late_past_event_requires_watermark_reconciliation(self):
        item = record(
            self.policy,
            delta_ns=-10_000_000_000,
            distance=None,
            event_time_ns=self.policy.safe_watermark_ns - 1,
            ingest_time_ns=self.policy.apex_time_ns,
        )
        result = moving_v.classify_record(self.policy, item)
        self.assertEqual(result.state, moving_v.GeometryState.PAST_HOLD)
        self.assertEqual(result.reason, "HOLD_LATE_EVENT_REQUIRES_WATERMARK_RECONCILIATION")

    def test_future_to_current_to_past_transition_as_apex_moves(self):
        future = record(self.policy, delta_ns=30_000_000_000, distance=20)
        self.assertEqual(
            moving_v.classify_record(self.policy, future).state,
            moving_v.GeometryState.FUTURE_PROTECTED,
        )
        at_need_time = replace(
            self.policy,
            apex_time_ns=future.need_time_ns,
            safe_watermark_ns=future.need_time_ns,
        )
        self.assertEqual(
            moving_v.classify_record(at_need_time, future).state,
            moving_v.GeometryState.CURRENT_GUARD,
        )
        after = replace(
            self.policy,
            apex_time_ns=future.need_time_ns + 10_000_000_000,
            safe_watermark_ns=future.need_time_ns + 10_000_000_000,
        )
        self.assertEqual(
            moving_v.classify_record(after, future).state,
            moving_v.GeometryState.PAST_ELIGIBLE,
        )

    def side_record(self):
        return record(self.policy, delta_ns=30_000_000_000, distance=41)


class MovingVSafetyGateTests(unittest.TestCase):
    def setUp(self):
        self.policy = policy_from_candidate_config()
        self.side = record(self.policy, delta_ns=30_000_000_000, distance=41)
        self.past = record(self.policy, delta_ns=-10_000_000_000, distance=None)

    def test_future_predicted_miss_only_soft_evicts(self):
        result = decision(self.policy, self.side)
        self.assertEqual(result.action, moving_v.MemoryAction.SOFT_EVICT_RECONSTRUCTIBLE)
        self.assertFalse(result.destructive)
        self.assertFalse(result.canonical_delete_allowed)

    def test_safe_past_moves_to_quarantine_not_hard_delete(self):
        result = decision(self.policy, self.past)
        self.assertEqual(result.classification, moving_v.GeometryState.PAST_ELIGIBLE)
        self.assertEqual(result.action, moving_v.MemoryAction.MOVE_TO_QUARANTINE)
        self.assertFalse(result.destructive)
        self.assertFalse(result.canonical_delete_allowed)

    def test_live_reference_cancels_cleanup(self):
        result = decision(self.policy, replace(self.side, live_reference_count=1))
        self.assertEqual(result.action, moving_v.MemoryAction.KEEP_HOLD)
        self.assertEqual(result.reason, "HOLD_LIVE_REFERENCE")

    def test_lease_and_pin_cancel_cleanup(self):
        self.assertEqual(
            decision(self.policy, replace(self.side, active_lease=True)).reason,
            "HOLD_ACTIVE_LEASE",
        )
        self.assertEqual(
            decision(self.policy, replace(self.side, pinned=True)).reason,
            "HOLD_PINNED_RECORD",
        )

    def test_record_version_cas_mismatch_cancels_cleanup(self):
        result = decision(self.policy, self.side, version=self.side.record_version + 1)
        self.assertEqual(result.action, moving_v.MemoryAction.KEEP_HOLD)
        self.assertEqual(result.reason, "HOLD_CAS_RECORD_VERSION_MISMATCH")

    def test_prediction_epoch_cas_mismatch_cancels_cleanup(self):
        result = decision(self.policy, self.side, epoch="STALE_EPOCH")
        self.assertEqual(result.action, moving_v.MemoryAction.KEEP_HOLD)
        self.assertEqual(result.reason, "HOLD_CAS_PREDICTION_EPOCH_MISMATCH")

    def test_unverified_or_mismatched_source_cancels_cleanup(self):
        self.assertEqual(
            decision(self.policy, replace(self.side, durable_source_verified=False)).reason,
            "HOLD_DURABLE_SOURCE_NOT_VERIFIED",
        )
        self.assertEqual(
            decision(self.policy, replace(self.side, observed_source_hash="b" * 64)).reason,
            "HOLD_SOURCE_HASH_MISMATCH",
        )
        self.assertEqual(
            decision(self.policy, replace(self.side, expected_source_hash="not-a-hash")).reason,
            "HOLD_SOURCE_HASH_MISSING",
        )

    def test_unknown_storage_tier_fails_closed(self):
        result = decision(self.policy, replace(self.side, storage_tier="UNKNOWN"))
        self.assertEqual(result.action, moving_v.MemoryAction.KEEP_HOLD)
        self.assertEqual(result.reason, "HOLD_UNKNOWN_STORAGE_TIER")

    def test_canonical_source_is_never_cleaned(self):
        result = decision(self.policy, replace(self.past, is_canonical_source=True))
        self.assertEqual(result.action, moving_v.MemoryAction.KEEP_HOLD)
        self.assertEqual(result.reason, "HOLD_CANONICAL_SOURCE_NEVER_CLEANED_BY_CANDIDATE")

    def test_already_reference_only_is_noop(self):
        result = decision(self.policy, replace(self.side, storage_tier="ADI_INDEX_ONLY"))
        self.assertEqual(result.action, moving_v.MemoryAction.NOOP_REFERENCE_ONLY)
        quarantined = decision(self.policy, replace(self.past, storage_tier="QUARANTINE"))
        self.assertEqual(quarantined.action, moving_v.MemoryAction.NOOP_REFERENCE_ONLY)

    def test_false_miss_rehydrates_only_after_hash_verification(self):
        result = decision(self.policy, self.side)
        self.assertEqual(
            moving_v.false_miss_receipt(
                result,
                actual_hit=True,
                reconstructed_hash_matches=True,
            ),
            "FALSE_MISS_REHYDRATED_AND_RECORDED",
        )
        self.assertEqual(
            moving_v.false_miss_receipt(
                result,
                actual_hit=True,
                reconstructed_hash_matches=False,
            ),
            "HOLD_RECONSTRUCTION_HASH_MISMATCH",
        )


class MovingVConcurrencyAndPressureTests(unittest.TestCase):
    def setUp(self):
        self.policy = policy_from_candidate_config()

    def test_safe_watermark_is_minimum_of_nodes(self):
        self.assertEqual(moving_v.aligned_safe_watermark([100, 80, 90]), 80)
        with self.assertRaisesRegex(ValueError, "ACTIVE_NODE_WATERMARK_REQUIRED"):
            moving_v.aligned_safe_watermark([])

    def test_apex_and_watermark_cannot_move_backward(self):
        current = replace(
            self.policy,
            apex_time_ns=self.policy.apex_time_ns - 1,
            safe_watermark_ns=self.policy.safe_watermark_ns,
        )
        with self.assertRaisesRegex(ValueError, "APEX_TIME_MUST_BE_MONOTONIC"):
            moving_v.validate_apex_advance(self.policy, current)
        current = replace(
            self.policy,
            apex_time_ns=self.policy.apex_time_ns + 1,
            safe_watermark_ns=self.policy.safe_watermark_ns - 1,
        )
        with self.assertRaisesRegex(ValueError, "SAFE_WATERMARK_MUST_BE_MONOTONIC"):
            moving_v.validate_apex_advance(self.policy, current)

    def test_pressure_plan_prefers_v_side_then_safe_past(self):
        protected = record(
            self.policy,
            record_id="protected",
            delta_ns=30_000_000_000,
            distance=20,
            resident_bytes=4096,
        )
        side = record(
            self.policy,
            record_id="side",
            delta_ns=30_000_000_000,
            distance=50,
            resident_bytes=4096,
        )
        past = record(
            self.policy,
            record_id="past",
            delta_ns=-10_000_000_000,
            distance=None,
            resident_bytes=4096,
        )
        plan = moving_v.plan_memory_pressure(
            self.policy,
            [past, protected, side],
            target_release_bytes=8192,
        )
        self.assertEqual(plan.state, "PASS_PRESSURE_PLAN")
        self.assertEqual(plan.selected_record_ids, ("side", "past"))
        self.assertFalse(plan.protected_eviction_violation)

    def test_insufficient_safe_candidates_requires_backpressure(self):
        protected = record(
            self.policy,
            record_id="protected",
            delta_ns=30_000_000_000,
            distance=20,
            resident_bytes=8192,
        )
        plan = moving_v.plan_memory_pressure(
            self.policy,
            [protected],
            target_release_bytes=4096,
        )
        self.assertEqual(plan.state, "BACKPRESSURE_REQUIRED")
        self.assertEqual(plan.selected_record_ids, ())
        self.assertFalse(plan.protected_eviction_violation)

    def test_property_no_protected_or_current_record_is_selected(self):
        rng = random.Random(20260818)
        records = []
        for i in range(1000):
            delta_ns = rng.choice([0, 10_000_000_000, 30_000_000_000, 60_000_000_000])
            distance = rng.randint(0, 80)
            records.append(
                record(
                    self.policy,
                    record_id=f"r{i:04d}",
                    delta_ns=delta_ns,
                    distance=distance,
                    resident_bytes=1,
                )
            )
        plan = moving_v.plan_memory_pressure(
            self.policy,
            records,
            target_release_bytes=10_000,
        )
        selected = set(plan.selected_record_ids)
        for item, item_decision in zip(records, plan.decisions):
            if item.record_id in selected:
                self.assertIn(
                    item_decision.classification,
                    {
                        moving_v.GeometryState.FUTURE_PREDICTED_MISS,
                        moving_v.GeometryState.PAST_ELIGIBLE,
                    },
                )
                self.assertFalse(item_decision.destructive)
                self.assertFalse(item_decision.canonical_delete_allowed)
        self.assertFalse(plan.protected_eviction_violation)


class MovingVBudgetAdjustmentTests(unittest.TestCase):
    def setUp(self):
        self.gate = moving_v.BudgetPerformanceGate(
            min_sample_count_uint=1000,
            min_observation_ns_uint=60_000_000_000,
            min_host_reserve_bytes_uint=1024**3,
            max_p95_latency_regression_bp_uint=500,
            max_false_miss_rate_bp_uint=200,
            min_preload_hit_rate_bp_uint=8000,
        )
        self.evidence = moving_v.BudgetPerformanceEvidence(
            sample_count_uint=2000,
            observation_ns_uint=120_000_000_000,
            host_available_after_adjustment_bytes_uint=4 * 1024**3,
            protected_working_set_bytes_uint=1024**3,
            p95_latency_regression_bp_uint=200,
            false_miss_rate_bp_uint=100,
            preload_hit_rate_bp_uint=9000,
        )

    def evaluate(self, proposed, evidence=None):
        return moving_v.evaluate_budget_adjustment_candidate(
            current_limit_bytes=2 * 1024**3,
            proposed_limit_bytes=proposed,
            gate=self.gate,
            evidence=evidence or self.evidence,
        )

    def test_budget_can_move_up_or_down_when_synthetic_gates_pass(self):
        for proposed in (1536 * 1024**2, 3 * 1024**3):
            with self.subTest(proposed=proposed):
                result = self.evaluate(proposed)
                self.assertEqual(result.state, "PASS_BUDGET_ADJUSTMENT_CANDIDATE_ONLY")
                self.assertFalse(result.applies_change)

    def test_budget_cannot_drop_below_protected_working_set(self):
        result = self.evaluate(512 * 1024**2)
        self.assertEqual(result.state, "HOLD_BUDGET_ADJUSTMENT")
        self.assertEqual(result.reason, "HOLD_PROPOSED_LIMIT_BELOW_PROTECTED_WORKING_SET")

    def test_low_host_reserve_or_bad_user_experience_metrics_hold(self):
        cases = (
            (
                replace(self.evidence, host_available_after_adjustment_bytes_uint=1),
                "HOLD_HOST_RESERVE_TOO_LOW",
            ),
            (
                replace(self.evidence, p95_latency_regression_bp_uint=501),
                "HOLD_P95_LATENCY_REGRESSION",
            ),
            (
                replace(self.evidence, false_miss_rate_bp_uint=201),
                "HOLD_FALSE_MISS_RATE_TOO_HIGH",
            ),
            (
                replace(self.evidence, preload_hit_rate_bp_uint=7999),
                "HOLD_PRELOAD_HIT_RATE_TOO_LOW",
            ),
        )
        for evidence, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(self.evaluate(3 * 1024**3, evidence).reason, expected)

    def test_oom_swap_or_integrity_violation_holds(self):
        cases = (
            (replace(self.evidence, oom_event_count_uint=1), "HOLD_OOM_EVENT_OBSERVED"),
            (replace(self.evidence, swap_thrashing=True), "HOLD_SWAP_THRASHING_OBSERVED"),
            (
                replace(self.evidence, protected_eviction_violation_count_uint=1),
                "HOLD_PROTECTED_EVICTION_VIOLATION",
            ),
            (
                replace(self.evidence, reconstruction_hash_mismatch_count_uint=1),
                "HOLD_RECONSTRUCTION_HASH_MISMATCH",
            ),
        )
        for evidence, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(self.evaluate(3 * 1024**3, evidence).reason, expected)

if __name__ == "__main__":
    unittest.main()
