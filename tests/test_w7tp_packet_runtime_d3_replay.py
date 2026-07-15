from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools import w7tp_packet_inference_runtime as runtime  # noqa: E402
from tools.d3_coordinate_transition_candidate import (  # noqa: E402
    transition_coordinate as candidate_transition_coordinate,
)


FIXED_RUNTIME_INPUT = {
    "text": "固定 D3 runtime replay input",
    "branch": "cafe_main",
    "actor_role": "counter_ai",
    "channel": "counter_voice",
    "event_id": "evt-runtime-replay-001",
    "logical_time": "logical:runtime-replay:001",
}
EXPECTED_COORDINATE = {
    "branch": "cafe_main",
    "actor_role": "counter_ai",
    "channel": "counter_voice",
}
LEGACY_PACKET_KEYS = {
    "packet_type",
    "version",
    "step",
    "parent_packet_hash",
    "D1_intent",
    "D2_state",
    "D3_coordinate",
    "D4_evidence",
    "D5_execution",
    "D6_gt",
    "D7_risk",
    "D8_envelope",
}
TRANSITION_METADATA_KEYS = {
    "transition_hash",
    "event_id",
    "logical_time",
    "committed",
    "commit_applied",
    "final_decision",
}


def decision_gate(decision: str):
    def gate(_payload):
        return {"decision": decision, "reason_code": f"D8_RUNTIME_REPLAY_{decision}"}

    return gate


class W7TPPacketRuntimeD3ReplayTests(unittest.TestCase):
    def test_fixed_runtime_input_replays_identically(self):
        first = runtime.run(**FIXED_RUNTIME_INPUT)
        second = runtime.run(**FIXED_RUNTIME_INPUT)
        first_packet = first["PACKET_CHAIN"][0]
        second_packet = second["PACKET_CHAIN"][0]
        first_metadata = first["D3_TRANSITION_METADATA"]
        second_metadata = second["D3_TRANSITION_METADATA"]

        self.assertEqual(first_packet["D3_coordinate"], second_packet["D3_coordinate"])
        self.assertEqual(first_metadata["committed"], second_metadata["committed"])
        self.assertEqual(first_metadata["final_decision"], second_metadata["final_decision"])
        self.assertEqual(first_metadata["transition_hash"], second_metadata["transition_hash"])

    def test_runtime_uses_allow_only_commit(self):
        for decision in ("ALLOW", "HOLD", "BLOCK", "QUARANTINE"):
            with self.subTest(decision=decision):
                def transition_with_decision(**kwargs):
                    return candidate_transition_coordinate(
                        **kwargs,
                        d8_gate=decision_gate(decision),
                    )

                with patch.object(
                    runtime,
                    "transition_coordinate",
                    side_effect=transition_with_decision,
                ):
                    result = runtime.run(**FIXED_RUNTIME_INPUT)

                packet = result["PACKET_CHAIN"][0]
                metadata = result["D3_TRANSITION_METADATA"]
                self.assertEqual(metadata["final_decision"], decision)
                if decision == "ALLOW":
                    self.assertTrue(metadata["commit_applied"])
                    self.assertEqual(metadata["committed"], EXPECTED_COORDINATE)
                    self.assertEqual(packet["D3_coordinate"], metadata["committed"])
                else:
                    self.assertFalse(metadata["commit_applied"])
                    self.assertEqual(metadata["committed"], {})
                    self.assertEqual(packet["D3_coordinate"], {})

    def test_transition_metadata_stays_outside_d3_body(self):
        result = runtime.run(**FIXED_RUNTIME_INPUT)
        packet = result["PACKET_CHAIN"][0]
        metadata = packet["D3_transition_metadata"]
        self.assertEqual(set(metadata), TRANSITION_METADATA_KEYS)
        self.assertTrue(TRANSITION_METADATA_KEYS.isdisjoint(packet["D3_coordinate"]))
        self.assertNotIn("D3_transition_metadata", packet["D3_coordinate"])

    def test_legacy_packet_schema_and_coordinate_shape_remain_compatible(self):
        result = runtime.run(**FIXED_RUNTIME_INPUT)
        packet = result["PACKET_CHAIN"][0]
        self.assertTrue(LEGACY_PACKET_KEYS.issubset(packet))
        self.assertEqual(packet["D3_coordinate"], EXPECTED_COORDINATE)
        self.assertEqual(set(packet["D3_coordinate"]), set(EXPECTED_COORDINATE))
        self.assertEqual(result["D3_TRANSITION_METADATA"], packet["D3_transition_metadata"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
