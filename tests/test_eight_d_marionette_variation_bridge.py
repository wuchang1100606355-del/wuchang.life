from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.total_field.eight_d_marionette_variation_bridge import (  # noqa: E402
    build_8d_marionette_control_packet,
    build_marionette_sequence,
    load_marionette_variation_map,
    required_dimension_status,
    variation_capacity,
)


def packet(intent: str, control_code: str | None = None):
    data = {
        "d1_intent": intent,
        "d2_state": "candidate",
        "d3_coordinate": {"avatar_ref": "asset_ref:J.vrm"},
        "d4_evidence": {"source": "test"},
        "d5_execution": {"mode": "candidate_only"},
        "d6_technical_definition": "8D packet controls avatar control vector",
        "d7_risk": {"risk": "low"},
        "d8_envelope": {"decision_authority": "total_field"},
    }
    if control_code:
        data["control_code"] = control_code
    return data


class EightDMarionetteVariationBridgeTests(unittest.TestCase):
    def test_map_policy_is_safe(self):
        data = load_marionette_variation_map()
        self.assertTrue(data["principle"]["eight_d_packet_controls_avatar"])
        self.assertTrue(data["principle"]["marionette_master_variation"])
        self.assertFalse(data["policy"]["deploy"])
        self.assertFalse(data["policy"]["restart"])
        self.assertFalse(data["policy"]["db_write"])
        self.assertFalse(data["policy"]["render_video_now"])
        self.assertFalse(data["policy"]["commit_vrm_binary"])

    def test_variation_capacity_exceeds_symbolic_manual_puppet_baseline(self):
        result = variation_capacity()
        self.assertEqual(result["STATE"], "PASS_8D_VARIATION_CAPACITY_COMPUTED")
        self.assertGreater(result["variation_capacity"], result["symbolic_manual_puppet_baseline"])
        self.assertTrue(result["exceeds_symbolic_manual_puppet_baseline"])
        self.assertFalse(result["runtime_write"])

    def test_required_dimensions(self):
        ok = required_dimension_status(packet("歡迎招呼"))
        bad = required_dimension_status({"d1_intent": "partial"})
        self.assertEqual(ok["STATE"], "PASS_8D_DIMENSIONS_PRESENT")
        self.assertEqual(bad["STATE"], "HOLD_8D_DIMENSIONS_MISSING")

    def test_greeting_wave_control_vector(self):
        result = build_8d_marionette_control_packet(packet("歡迎客人招呼"))
        self.assertEqual(result["control_code"], "GREETING_WAVE")
        self.assertEqual(result["control_vector"]["hands"], "right_hand_wave")
        self.assertFalse(result["runtime_write"])

    def test_anchor_drink_intro_control_vector(self):
        result = build_8d_marionette_control_packet(packet("坐主播台介紹飲料"))
        self.assertEqual(result["control_code"], "ANCHOR_DESK_DRINK_INTRO")
        self.assertEqual(result["control_vector"]["body"], "seated_anchor_desk")
        self.assertEqual(result["control_vector"]["camera"], "anchor_desk")

    def test_runtime_risk_becomes_redteam_defense(self):
        risky = packet("deploy restart db_write")
        risky["d5_execution"] = {"deploy": True, "restart": True, "db_write": True}
        result = build_8d_marionette_control_packet(risky)
        self.assertEqual(result["control_code"], "REDTEAM_DEFENSE")
        self.assertFalse(result["deploy"])
        self.assertFalse(result["restart"])
        self.assertFalse(result["db_write"])

    def test_missing_dimensions_total_field_decides(self):
        result = build_8d_marionette_control_packet({"d1_intent": "partial"})
        self.assertEqual(result["control_code"], "TOTAL_FIELD_DECIDES")
        self.assertEqual(result["dimension_status"]["STATE"], "HOLD_8D_DIMENSIONS_MISSING")

    def test_sequence_movie_possible(self):
        seq = build_marionette_sequence([
            packet("歡迎招呼"),
            packet("點單推薦"),
            packet("坐主播台介紹飲料")
        ])
        self.assertEqual(seq["STATE"], "PASS_8D_MARIONETTE_SEQUENCE_CANDIDATE")
        self.assertEqual(seq["control_count"], 3)
        self.assertTrue(seq["movie_possible"])
        self.assertFalse(seq["render_video_now"])
        self.assertFalse(seq["commit_vrm_binary"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
