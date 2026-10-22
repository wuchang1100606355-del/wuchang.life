from __future__ import annotations

import copy
import unittest
from pathlib import Path

from products.eight_dimensional_generative_memory import (
    w7tp_endpoint_rule_handshake_v1 as handshake,
)


ROOT = Path(__file__).resolve().parents[1]
TASK_RULE = "local-rule:w7tp-task-state-ledger-reconstruction/v1"
FIXTURE_RULE = "local-rule:w7tp-origin-cell-fixture-recipe/v2"


class EndpointRuleHandshakeTests(unittest.TestCase):
    def test_observe_current_root_distinguishes_present_from_ready(self) -> None:
        result = handshake.observe_endpoint_rule_capability(
            root=ROOT,
            node_ref="taiji01-test",
            state_root=None,
        )
        self.assertEqual(result["state"], "PASS_ENDPOINT_RULE_BASE_PRESENT")
        self.assertIn(TASK_RULE, result["rule_base"]["present_rule_refs"])
        self.assertIn(FIXTURE_RULE, result["rule_base"]["present_rule_refs"])
        self.assertIn(FIXTURE_RULE, result["rule_base"]["ready_rule_refs"])
        self.assertNotIn(TASK_RULE, result["rule_base"]["ready_rule_refs"])
        self.assertTrue(result["semantics"]["file_presence_is_not_readiness"])
        self.assertFalse(result["authority"]["canonical"])
        self.assertFalse(result["authority"]["execution_authorized"])

    def test_shared_rule_exact_match_does_not_invent_readiness(self) -> None:
        source = handshake.observe_endpoint_rule_capability(
            root=ROOT,
            node_ref="source",
            state_root=None,
        )
        receiver = copy.deepcopy(source)
        receiver["node_ref"] = "receiver"
        result = handshake.shared_rule_match(
            source,
            receiver,
            rule_ref=TASK_RULE,
        )
        self.assertEqual(result["state"], "PASS_SHARED_RULE_EXACT_MATCH")
        self.assertFalse(result["source_ready"])
        self.assertFalse(result["receiver_ready"])

    def test_shared_rule_hash_drift_fails_closed(self) -> None:
        source = handshake.observe_endpoint_rule_capability(
            root=ROOT,
            node_ref="source",
            state_root=None,
        )
        receiver = copy.deepcopy(source)
        for item in receiver["rule_base"]["rules"]:
            if item["rule_ref"] == TASK_RULE:
                item["implementation_sha256"] = "0" * 64
        with self.assertRaisesRegex(
            handshake.EndpointRuleHandshakeHold,
            "HOLD_SHARED_RULE_HASH_MISMATCH",
        ):
            handshake.shared_rule_match(
                source,
                receiver,
                rule_ref=TASK_RULE,
            )

    def test_cost_vector_keeps_unknown_distinct_from_zero(self) -> None:
        vector = handshake.build_cost_vector(total_wire_bytes=120)
        self.assertEqual(vector["transport"]["bootstrap_bytes"], "UNKNOWN")
        self.assertEqual(vector["transport"]["first_use_transport_bytes"], "UNKNOWN")
        self.assertEqual(vector["transport"]["steady_state_transport_bytes"], 120)
        self.assertIn("reconstruction_time_ms", vector["unknown_material_dimensions"])
        self.assertFalse(vector["total_effect_complete"])
        self.assertTrue(vector["accounting_semantics"]["unknown_never_zero"])

    def test_cost_vector_separates_first_use_from_steady_state(self) -> None:
        vector = handshake.build_cost_vector(
            total_wire_bytes=120,
            bootstrap_bytes=880,
            state_acquisition_bytes=10,
            state_acquisition_time_ms=1.0,
            reconstruction_time_ms=2.0,
            verification_time_ms=1.0,
            verification_bytes=20,
            authority_time_ms=0.0,
            human_review_required=False,
            cpu_time_ms=2.0,
            gpu_time_ms=0.0,
            memory_peak_bytes=1024,
            energy_joules=0.5,
            failure_probability=0.0,
            failure_fallback_bytes=0,
            persistent_storage_bytes=0,
            temporary_storage_peak_bytes=2048,
            amortization_runs=10,
        )
        self.assertEqual(vector["transport"]["first_use_transport_bytes"], 1000)
        self.assertEqual(vector["transport"]["steady_state_transport_bytes"], 120)
        self.assertEqual(vector["transport"]["amortized_transport_bytes"], 208.0)
        self.assertTrue(vector["total_effect_complete"])

    def test_selector_reports_wire_scope_not_total_effect_optimum(self) -> None:
        exact_ready = {
            "state": "PASS_SHARED_RULE_EXACT_MATCH",
            "receiver_ready": True,
        }
        result = handshake.select_transport(
            full_transfer_wire_bytes=1000,
            shared_rule_origin_cell_wire_bytes=120,
            shared_rule_match_state=exact_ready,
        )
        self.assertEqual(result["selected_mode"], "SHARED_RULE_ORIGIN_CELL")
        self.assertEqual(result["cost_model"]["decision_scope"], "TRANSPORT_WIRE_COST_ONLY")
        self.assertFalse(result["cost_model"]["total_effect_cost_complete"])
        self.assertTrue(result["cost_model"]["unknown_never_zero"])
        self.assertFalse(result["cost_model"]["cross_unit_scalarization"])

    def test_selector_can_fail_closed_on_incomplete_total_effect_cost(self) -> None:
        exact_ready = {
            "state": "PASS_SHARED_RULE_EXACT_MATCH",
            "receiver_ready": True,
        }
        with self.assertRaisesRegex(
            handshake.EndpointRuleHandshakeHold,
            "HOLD_TOTAL_EFFECT_COST_INCOMPLETE",
        ):
            handshake.select_transport(
                full_transfer_wire_bytes=1000,
                shared_rule_origin_cell_wire_bytes=120,
                shared_rule_match_state=exact_ready,
                require_total_effect_complete=True,
            )

    def test_cost_vector_rejects_invalid_failure_probability(self) -> None:
        with self.assertRaisesRegex(
            handshake.EndpointRuleHandshakeHold,
            "HOLD_COST_FAILURE_PROBABILITY_INVALID",
        ):
            handshake.build_cost_vector(
                total_wire_bytes=100,
                failure_probability=1.1,
            )

    def test_selector_reports_transport_break_even_when_inputs_are_known(self) -> None:
        exact_ready = {
            "state": "PASS_SHARED_RULE_EXACT_MATCH",
            "receiver_ready": True,
        }
        common = dict(
            state_acquisition_bytes=0,
            state_acquisition_time_ms=0.0,
            reconstruction_time_ms=1.0,
            verification_time_ms=1.0,
            verification_bytes=0,
            authority_time_ms=0.0,
            human_review_required=False,
            cpu_time_ms=1.0,
            gpu_time_ms=0.0,
            memory_peak_bytes=1024,
            energy_joules=0.1,
            failure_probability=0.0,
            failure_fallback_bytes=0,
            persistent_storage_bytes=0,
            temporary_storage_peak_bytes=1024,
        )
        full = handshake.build_cost_vector(
            total_wire_bytes=1000,
            bootstrap_bytes=0,
            **common,
        )
        shared = handshake.build_cost_vector(
            total_wire_bytes=100,
            bootstrap_bytes=1800,
            **common,
        )
        result = handshake.select_transport(
            full_transfer_wire_bytes=1000,
            shared_rule_origin_cell_wire_bytes=100,
            shared_rule_match_state=exact_ready,
            cost_vectors={
                "FULL_TRANSFER": full,
                "SHARED_RULE_ORIGIN_CELL": shared,
            },
            require_total_effect_complete=True,
        )
        row = next(
            x for x in result["candidates"]
            if x["mode"] == "SHARED_RULE_ORIGIN_CELL"
        )
        self.assertEqual(row["break_even_runs_vs_full"], 2)
        self.assertTrue(result["cost_model"]["total_effect_cost_complete"])

    def test_selector_uses_complete_wire_cost_and_full_transfer_can_win(self) -> None:
        exact_ready = {
            "state": "PASS_SHARED_RULE_EXACT_MATCH",
            "receiver_ready": True,
        }
        result = handshake.select_transport(
            full_transfer_wire_bytes=1000,
            shared_rule_origin_cell_wire_bytes=1200,
            shared_rule_match_state=exact_ready,
            generative_origin_cell_wire_bytes=1500,
        )
        self.assertEqual(result["selected_mode"], "FULL_TRANSFER")
        self.assertEqual(result["selected_wire_bytes"], 1000)
        self.assertIn("COMPLETE_SERIALIZED_WIRE_BYTES", result["metric_rule"])

    def test_selector_prefers_shared_rule_only_when_exact_ready_and_cheaper(self) -> None:
        exact_ready = {
            "state": "PASS_SHARED_RULE_EXACT_MATCH",
            "receiver_ready": True,
        }
        result = handshake.select_transport(
            full_transfer_wire_bytes=1000,
            shared_rule_origin_cell_wire_bytes=120,
            shared_rule_match_state=exact_ready,
            generative_origin_cell_wire_bytes=700,
        )
        self.assertEqual(result["selected_mode"], "SHARED_RULE_ORIGIN_CELL")
        self.assertEqual(result["selected_wire_bytes"], 120)

    def test_selector_rejects_shared_rule_when_receiver_not_ready(self) -> None:
        exact_not_ready = {
            "state": "PASS_SHARED_RULE_EXACT_MATCH",
            "receiver_ready": False,
        }
        result = handshake.select_transport(
            full_transfer_wire_bytes=1000,
            shared_rule_origin_cell_wire_bytes=120,
            shared_rule_match_state=exact_not_ready,
            generative_origin_cell_wire_bytes=700,
        )
        self.assertEqual(result["selected_mode"], "GENERATIVE_RULE_ORIGIN_CELL")

    def test_universal_executor_is_ready_without_task_state_material(self) -> None:
        result = handshake.observe_endpoint_rule_capability(
            root=ROOT,
            node_ref="universal-source",
            state_root=None,
        )
        universal = result["rule_base"]["universal_executor"]
        self.assertTrue(universal["ready"])
        self.assertFalse(universal["canonical"])
        self.assertFalse(universal["runtime_activated"])

    def test_universal_executor_exact_match_is_selector_eligible(self) -> None:
        source = handshake.observe_endpoint_rule_capability(
            root=ROOT,
            node_ref="source",
            state_root=None,
        )
        receiver = copy.deepcopy(source)
        receiver["node_ref"] = "receiver"
        match = handshake.universal_executor_match(source, receiver)
        self.assertEqual(
            match["state"],
            "PASS_SHARED_UNIVERSAL_EXECUTOR_MATCH",
        )
        self.assertTrue(match["receiver_ready"])
        selected = handshake.select_transport(
            full_transfer_wire_bytes=1000,
            shared_rule_origin_cell_wire_bytes=300,
            shared_rule_match_state=match,
        )
        self.assertEqual(selected["selected_mode"], "SHARED_RULE_ORIGIN_CELL")


if __name__ == "__main__":
    unittest.main()
