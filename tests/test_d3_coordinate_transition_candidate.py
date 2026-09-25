from __future__ import annotations

import copy
import math
import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.d3_coordinate_transition_candidate import (  # noqa: E402
    D3TransitionValidationError,
    legacy_packet_to_transition_inputs,
    transition_coordinate,
    verify_transition_record,
)


def decision_gate(decision: str):
    def gate(_payload):
        return {"decision": decision, "reason_code": f"D8_TEST_{decision}"}

    return gate


class D3CoordinateTransitionCandidateTests(unittest.TestCase):
    def setUp(self):
        self.previous = {
            "node": {"id": "node-a", "position": {"x": 0, "y": 1}},
            "lane": ["candidate"],
        }
        self.context = {
            "coordinate_delta": {"node": {"position": {"x": 2}, "phase": "ready"}},
            "d7_reference": {"rule_ref": "candidate/rules/state-update-v0.3"},
        }
        self.inputs = {
            "previous_coord": self.previous,
            "event_code": "STATE_UPDATE",
            "event_id": "evt-fixed-001",
            "logical_time": "logical:000001",
            "rule_ref": "candidate/rules/state-update-v0.3",
            "context": self.context,
        }

    def build(self, **changes):
        values = {**self.inputs, **changes}
        return transition_coordinate(**values)

    def test_identical_inputs_produce_identical_hash(self):
        self.assertEqual(self.build()["transition_hash"], self.build()["transition_hash"])

    def test_event_id_changes_hash(self):
        self.assertNotEqual(
            self.build()["transition_hash"],
            self.build(event_id="evt-fixed-002")["transition_hash"],
        )

    def test_logical_time_changes_hash(self):
        self.assertNotEqual(
            self.build()["transition_hash"],
            self.build(logical_time="logical:000002")["transition_hash"],
        )

    def test_rule_ref_changes_hash(self):
        self.assertNotEqual(
            self.build()["transition_hash"],
            self.build(rule_ref="candidate/rules/state-update-v0.3-alt")["transition_hash"],
        )

    def test_allow_commits_proposed(self):
        record = self.build(d8_gate=decision_gate("ALLOW"))
        self.assertTrue(record["commit_applied"])
        self.assertEqual(record["committed"], record["proposed"])

    def test_non_allow_decisions_preserve_previous(self):
        for decision in ("HOLD", "BLOCK", "QUARANTINE"):
            with self.subTest(decision=decision):
                record = self.build(d8_gate=decision_gate(decision))
                self.assertEqual(record["final_decision"], decision)
                self.assertFalse(record["commit_applied"])
                self.assertEqual(record["committed"], record["previous"])
                self.assertNotIn("decision", record["proposed"])

    def test_caller_inputs_are_not_mutated(self):
        before = copy.deepcopy(self.inputs)
        self.build()
        self.assertEqual(self.inputs, before)

    def test_context_key_order_does_not_change_hash(self):
        first_context = {
            "coordinate_delta": {"node": {"position": {"x": 2}, "phase": "ready"}},
            "d7_reference": {"rule_ref": "candidate/rules/state-update-v0.3"},
        }
        second_context = {
            "d7_reference": {"rule_ref": "candidate/rules/state-update-v0.3"},
            "coordinate_delta": {"node": {"phase": "ready", "position": {"x": 2}}},
        }
        self.assertEqual(
            self.build(context=first_context)["transition_hash"],
            self.build(context=second_context)["transition_hash"],
        )

    def test_nan_infinity_and_unserializable_values_are_rejected(self):
        invalid_values = (math.nan, math.inf, -math.inf, {"not", "json"})
        for value in invalid_values:
            with self.subTest(value=value):
                context = {"coordinate_delta": {"invalid": value}}
                with self.assertRaises(D3TransitionValidationError):
                    self.build(context=context)

    def test_unknown_event_code_uses_required_message(self):
        with self.assertRaisesRegex(
            D3TransitionValidationError, "未登錄於目前規則表的事件碼"
        ):
            self.build(event_code="UNKNOWN_EVENT")

    def test_required_identifiers_are_rejected_when_missing(self):
        for field, value in (
            ("event_id", ""),
            ("logical_time", None),
            ("rule_ref", ""),
        ):
            with self.subTest(field=field):
                with self.assertRaises(D3TransitionValidationError):
                    self.build(**{field: value})

    def test_nested_delta_deep_merges_without_source_mutation(self):
        previous = copy.deepcopy(self.previous)
        context = copy.deepcopy(self.context)
        previous_before = copy.deepcopy(previous)
        context_before = copy.deepcopy(context)
        record = self.build(previous_coord=previous, context=context)
        self.assertEqual(record["proposed"]["node"]["position"], {"x": 2, "y": 1})
        self.assertEqual(previous, previous_before)
        self.assertEqual(context, context_before)

    def test_verifier_recomputes_transition_hash(self):
        record = self.build()
        verified = verify_transition_record(record)
        self.assertTrue(verified["valid"])
        self.assertEqual(verified["recomputed_hash"], record["transition_hash"])
        tampered = copy.deepcopy(record)
        tampered["event_id"] = "evt-tampered"
        self.assertFalse(verify_transition_record(tampered)["valid"])

    def test_d6_candidate_gate_holds_sensitive_coordinate_key(self):
        record = self.build(context={"coordinate_delta": {"raw_token": "not-a-real-token"}})
        self.assertEqual(record["final_decision"], "HOLD")
        self.assertEqual(record["decision_reason"], "D6_SENSITIVE_KEY_PRESENT")
        self.assertEqual(record["committed"], record["previous"])

    def test_legacy_adapter_maps_only_compatible_fields(self):
        legacy = {
            "D3_coordinate": {"branch": "cafe_main"},
            "D6_gt": {"rule_ref": "rules/input-v1", "table_ref": "tables/input-v1"},
            "D7_risk": {"decision": "BLOCK"},
            "D8_envelope": {"packet_hash": "legacy-hash"},
        }
        adapted = legacy_packet_to_transition_inputs(
            legacy,
            event_code="STATE_UPDATE",
            event_id="evt-adapter-001",
            logical_time="logical:adapter:001",
            rule_ref="candidate/rules/state-update-v0.3",
            context={"coordinate_delta": {"branch": "cafe_next"}},
        )
        self.assertEqual(adapted["previous_coord"], legacy["D3_coordinate"])
        self.assertEqual(adapted["context"]["d7_reference"]["rule_ref"], "rules/input-v1")
        self.assertNotIn("D7_risk", adapted["context"])
        self.assertNotIn("D8_envelope", adapted["context"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
