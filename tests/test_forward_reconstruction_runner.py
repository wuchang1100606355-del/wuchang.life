from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.total_field.forward_reconstruction_runner import (  # noqa: E402
    CAFE_PACKET,
    build_source_packet,
    detect_detour,
    reconstruct_cafe_onboarding_candidate,
    total_field_reconstruct,
    verify_reconstructed_candidate,
)


class ForwardReconstructionRunnerTests(unittest.TestCase):
    def test_cafe_onboarding_touching_cockpit_holds_detour(self):
        packet = build_source_packet(
            target_packet=CAFE_PACKET,
            touched_paths=["web/packet_inference_cockpit/app.js"],
            evidence={"STATE": "TASK_WAS_CAFE_ONBOARDING"},
            requested_actions=[],
        )
        decision = detect_detour(packet)
        self.assertEqual(decision["decision"], "HOLD_DETOUR_ALERT")
        self.assertIn("CAFE_ONBOARDING_TOUCHED_COCKPIT_UI", decision["reasons"])
        self.assertIn("TARGET_PACKET_MISMATCH", decision["reasons"])

    def test_paste_burden_holds_when_existing_evidence_can_reconstruct(self):
        packet = build_source_packet(
            target_packet="DETOUR_ALERT_HARD_GATE",
            touched_paths=["tools/total_field/final_state_gate.py"],
            evidence={"TESTS": "PASS", "PY_COMPILE": "PASS", "FILES_CHANGED": "two files"},
            requested_actions=["paste"],
        )
        decision = detect_detour(packet)
        self.assertEqual(decision["decision"], "HOLD_DETOUR_ALERT")
        self.assertIn("PASTE_BURDEN_WHEN_RECONSTRUCTABLE", decision["reasons"])

    def test_restore_without_ownership_holds(self):
        packet = build_source_packet(
            target_packet=CAFE_PACKET,
            touched_paths=["web/packet_inference_cockpit/app.js"],
            evidence={"diff_ownership_confirmed": False},
            requested_actions=["restore"],
        )
        decision = detect_detour(packet)
        self.assertEqual(decision["decision"], "HOLD_DETOUR_ALERT")
        self.assertIn("RESTORE_WITHOUT_DIFF_OWNERSHIP", decision["reasons"])

    def test_delete_action_holds_zero_delete_violation(self):
        packet = build_source_packet(
            target_packet=CAFE_PACKET,
            touched_paths=[],
            evidence={},
            requested_actions=["rm"],
        )
        decision = detect_detour(packet)
        self.assertEqual(decision["decision"], "HOLD_DETOUR_ALERT")
        self.assertIn("ZERO_DELETE_OR_RESTORE_VIOLATION", decision["reasons"])

    def test_self_seeded_cafe_candidate_contains_required_state(self):
        packet = build_source_packet(
            target_packet=CAFE_PACKET,
            touched_paths=[],
            evidence={},
            requested_actions=["generative_reconstruction"],
        )
        candidate = reconstruct_cafe_onboarding_candidate(packet)
        verification = verify_reconstructed_candidate(candidate)

        self.assertEqual(verification["decision"], "PASS_RECONSTRUCTED_CANDIDATE")
        self.assertFalse(candidate["production_activation_ready"])
        self.assertIn("merchant_8d_7d_packet", candidate)
        self.assertIn("adi_5d_ref", candidate)
        self.assertIn("tenant_profile_candidate", candidate)
        self.assertIn("service_profile_candidate", candidate)
        self.assertIn("container_config_candidate", candidate)
        self.assertIn("url_routing_candidate", candidate)
        self.assertFalse(candidate["hard_risk_controls"]["db_write"])
        self.assertFalse(candidate["hard_risk_controls"]["deploy"])
        self.assertFalse(candidate["hard_risk_controls"]["restart"])

    def test_total_field_reconstruct_passes_without_extra_user_data(self):
        packet = build_source_packet(
            target_packet=CAFE_PACKET,
            touched_paths=[],
            evidence={},
            requested_actions=["generative_reconstruction"],
        )
        result = total_field_reconstruct(packet)
        self.assertEqual(result["STATE"], "PASS_RECONSTRUCTED_CANDIDATE")
        self.assertEqual(result["TOTAL_FIELD_DECISION"], "PASS_RECONSTRUCTED_CANDIDATE")
        self.assertIn("RECONSTRUCTED_CANDIDATE", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
