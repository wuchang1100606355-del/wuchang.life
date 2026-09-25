from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.total_field.eight_d_packet_control_bridge import (  # noqa: E402
    ROOKIE_MESSAGE,
    build_8d_control_packet,
    load_control_map,
    member_facing_from_8d_packet,
    required_dimension_status,
)


BASE_PACKET = {
    "d1_intent": "member_registration_candidate",
    "d2_state": "candidate_ready",
    "d3_coordinate": {"member_ref": "member_ref:candidate"},
    "d4_evidence": {"source": "test"},
    "d5_execution": {"mode": "candidate_only"},
    "d6_technical_definition": "8D packet controls candidate state",
    "d7_risk": {"risk": "low"},
    "d8_envelope": {"decision_authority": "total_field"},
}


class EightDPacketControlBridgeTests(unittest.TestCase):
    def test_control_map_policy_is_safe(self):
        data = load_control_map()
        self.assertTrue(data["control_principle"]["eight_d_packet_controls"])
        self.assertFalse(data["policy"]["deploy"])
        self.assertFalse(data["policy"]["restart"])
        self.assertFalse(data["policy"]["db_write"])
        self.assertFalse(data["policy"]["runtime_bulk_output"])

    def test_pass_packet_controls_pass_intent_state(self):
        packet = dict(BASE_PACKET, total_field_decision="PASS_CANDIDATE")
        control = build_8d_control_packet(packet)
        self.assertEqual(control["control_code"], "PASS_INTENT")
        self.assertEqual(control["state_id"], 1)
        self.assertFalse(control["runtime_write"])

    def test_unexecutable_hold_controls_rookie_escalation(self):
        packet = dict(BASE_PACKET, total_field_decision="HOLD")
        control = build_8d_control_packet(packet)
        self.assertEqual(control["control_code"], "ROOKIE_ESCALATE")
        self.assertEqual(control["member_facing"], ROOKIE_MESSAGE)

    def test_detour_controls_hold_detour_alert(self):
        packet = dict(BASE_PACKET, total_field_decision="HOLD_DETOUR_ALERT")
        control = build_8d_control_packet(packet)
        self.assertEqual(control["control_code"], "HOLD_DETOUR_ALERT")
        self.assertEqual(control["state_id"], 8)

    def test_runtime_risk_controls_redteam_defense(self):
        packet = dict(BASE_PACKET)
        packet["d5_execution"] = {"deploy": True, "restart": True}
        packet["total_field_decision"] = "BLOCK"
        control = build_8d_control_packet(packet)
        self.assertEqual(control["control_code"], "REDTEAM_DEFENSE")
        self.assertEqual(control["state_id"], 99)
        self.assertFalse(control["deploy"])
        self.assertFalse(control["restart"])
        self.assertFalse(control["db_write"])

    def test_missing_dimension_controls_total_field_decides(self):
        packet = {"d1_intent": "partial"}
        status = required_dimension_status(packet)
        control = build_8d_control_packet(packet)
        self.assertEqual(status["STATE"], "HOLD_8D_DIMENSIONS_MISSING")
        self.assertEqual(control["control_code"], "TOTAL_FIELD_DECIDES")
        self.assertEqual(control["state_id"], 64)

    def test_member_facing_from_8d_packet(self):
        packet = dict(BASE_PACKET, total_field_decision="HOLD")
        self.assertEqual(member_facing_from_8d_packet(packet), ROOKIE_MESSAGE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
