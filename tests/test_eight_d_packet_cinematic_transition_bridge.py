from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.total_field.eight_d_packet_cinematic_transition_bridge import (  # noqa: E402
    build_cinematic_sequence,
    build_packet_transition,
    load_cinematic_transition_map,
    required_dimension_status,
    resolve_control_state,
    smoothstep,
)


def packet(intent: str, control_code: str):
    return {
        "d1_intent": intent,
        "d2_state": "candidate",
        "d3_coordinate": {"avatar_ref": "asset_ref:J.vrm"},
        "d4_evidence": {"source": "test"},
        "d5_execution": {"mode": "candidate_only"},
        "d6_technical_definition": "8D packet controls cinematic avatar state",
        "d7_risk": {"risk": "low"},
        "d8_envelope": {"decision_authority": "total_field"},
        "control_code": control_code,
    }


class EightDPacketCinematicTransitionBridgeTests(unittest.TestCase):
    def test_map_policy_is_safe(self):
        data = load_cinematic_transition_map()
        self.assertTrue(data["principle"]["packet_to_packet_transition"])
        self.assertTrue(data["principle"]["cinematic_timeline_candidate"])
        self.assertFalse(data["policy"]["deploy"])
        self.assertFalse(data["policy"]["restart"])
        self.assertFalse(data["policy"]["db_write"])
        self.assertFalse(data["policy"]["render_video_now"])
        self.assertFalse(data["policy"]["commit_vrm_binary"])

    def test_smoothstep_endpoints(self):
        self.assertEqual(smoothstep(0), 0)
        self.assertEqual(smoothstep(1), 1)
        self.assertGreater(smoothstep(0.5), 0.0)
        self.assertLess(smoothstep(0.5), 1.0)

    def test_required_dimensions(self):
        ok = required_dimension_status(packet("welcome", "GREETING_WAVE"))
        bad = required_dimension_status({"d1_intent": "partial"})
        self.assertEqual(ok["STATE"], "PASS_8D_DIMENSIONS_PRESENT")
        self.assertEqual(bad["STATE"], "HOLD_8D_DIMENSIONS_MISSING")

    def test_resolve_control_state(self):
        state = resolve_control_state(packet("drink intro", "ANCHOR_DESK_DRINK_INTRO"))
        self.assertEqual(state["control_code"], "ANCHOR_DESK_DRINK_INTRO")
        self.assertEqual(state["pose"], "seated_anchor_desk")

    def test_packet_transition_generates_smooth_frames(self):
        result = build_packet_transition(
            packet("welcome", "GREETING_WAVE"),
            packet("drink intro", "ANCHOR_DESK_DRINK_INTRO"),
            frames=5,
        )
        self.assertEqual(result["STATE"], "PASS_8D_PACKET_CINEMATIC_TRANSITION")
        self.assertEqual(result["frame_count"], 5)
        self.assertEqual(result["frames"][0]["from_weight"], 1.0)
        self.assertEqual(result["frames"][-1]["to_weight"], 1.0)
        self.assertFalse(result["render_video_now"])
        self.assertFalse(result["runtime_write"])

    def test_transition_clamps_max_candidate_frames(self):
        result = build_packet_transition(
            packet("a", "GREETING_WAVE"),
            packet("b", "ORDER_GUIDE"),
            frames=999,
        )
        self.assertEqual(result["frame_count"], 48)

    def test_missing_dimension_holds(self):
        result = build_packet_transition(
            {"d1_intent": "partial"},
            packet("b", "ORDER_GUIDE"),
        )
        self.assertEqual(result["STATE"], "HOLD_8D_CINEMATIC_TRANSITION_DIMENSION_MISSING")

    def test_cinematic_sequence_multiple_packets(self):
        result = build_cinematic_sequence(
            [
                packet("welcome", "GREETING_WAVE"),
                packet("order", "ORDER_GUIDE"),
                packet("drink intro", "ANCHOR_DESK_DRINK_INTRO"),
            ],
            frames_per_transition=4,
        )
        self.assertEqual(result["STATE"], "PASS_8D_CINEMATIC_SEQUENCE_CANDIDATE")
        self.assertEqual(result["segment_count"], 2)
        self.assertTrue(result["movie_possible"])
        self.assertFalse(result["render_video_now"])
        self.assertFalse(result["commit_vrm_binary"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
