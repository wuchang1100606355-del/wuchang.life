#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "capabilities/w7tp-8d-adi-audio-field/scripts"))

from audio_field import AudioFieldHold, build_candidate, load_contracts  # noqa: E402


def intent(target, operation, level=None, trigger="APP_INTENT"):
    return {
        "request_id": "REQ-TEST-0001",
        "trigger_type": trigger,
        "target_ref": target,
        "operation": operation,
        "level": level,
        "issued_at": "2026-09-26T07:00:00+00:00",
        "nonce": "12345678abcdef",
        "source_device_ref": "iphone-11",
    }


class AudioFieldTest(unittest.TestCase):
    def test_contracts_load(self):
        topology, siri, volume = load_contracts()
        self.assertEqual(siri["trigger_role"], "D1_INTENT_TRIGGER_ONLY")
        self.assertFalse(siri["authority"])
        self.assertTrue(volume["nodes"]["MSI"]["all_discovered_endpoints_volume_interface_pass"])
        self.assertEqual(topology["schema_version"], "W7TP-ALL-NODE-AUDIO-TOPOLOGY/1.0")

    def test_siri_is_not_authority(self):
        result = build_candidate(intent("辦公室", "SET_OUTPUT_VOLUME", 35, "SIRI_SHORTCUT"))
        self.assertFalse(result["execution_allowed"])
        self.assertFalse(result["D8"]["siri_is_authority"])
        self.assertTrue(result["D8"]["total_field_effect_decision_required"])

    def test_office_volume_uses_pyatv(self):
        result = build_candidate(intent("辦公室", "SET_OUTPUT_VOLUME", 35))
        plan = result["D3"]["plans"][0]
        self.assertEqual(plan["backend"], "PYATV_RAOP")
        self.assertEqual(plan["effect"]["normalized_level"], 35)
        self.assertTrue(plan["readback_verification_required"])

    def test_msi_open_is_route_plus_unmute_not_driver_enable(self):
        result = build_candidate(intent("我的電腦", "OUTPUT_OPEN"))
        effect = result["D3"]["plans"][0]["effect"]
        self.assertTrue(effect["route_selectable"])
        self.assertFalse(effect["mute"])
        self.assertFalse(effect["driver_enable_change"])

    def test_msi_close_is_route_remove_plus_mute_not_driver_disable(self):
        result = build_candidate(intent("MSI", "OUTPUT_CLOSE"))
        effect = result["D3"]["plans"][0]["effect"]
        self.assertFalse(effect["route_selectable"])
        self.assertTrue(effect["mute"])
        self.assertFalse(effect["driver_disable"])
        self.assertTrue(effect["preserve_last_nonzero_level"])

    def test_input_gain_is_distinct(self):
        result = build_candidate(intent("MSI麥克風", "SET_INPUT_GAIN", 70))
        plan = result["D3"]["plans"][0]
        self.assertEqual(plan["direction"], "INPUT")
        self.assertEqual(plan["effect"]["control_kind"], "INPUT_GAIN")
        self.assertEqual(plan["effect"]["normalized_level"], 70)

    def test_output_operation_cannot_target_input(self):
        with self.assertRaises(AudioFieldHold) as ctx:
            build_candidate(intent("MSI麥克風", "OUTPUT_CLOSE"))
        self.assertEqual(ctx.exception.code, "HOLD_OUTPUT_OPERATION_TARGETS_INPUT")

    def test_level_is_bounded(self):
        with self.assertRaises(AudioFieldHold) as ctx:
            build_candidate(intent("MSI", "SET_OUTPUT_VOLUME", 101))
        self.assertEqual(ctx.exception.code, "HOLD_AUDIO_LEVEL_OUT_OF_RANGE")

    def test_all_outputs_group_expands_atomically(self):
        result = build_candidate(intent("全部", "GROUP_SET_VOLUME", 42))
        plans = result["D3"]["plans"]
        self.assertEqual([p["target_ref"] for p in plans], ["MSI", "TAIJI03", "OFFICE"])
        self.assertTrue(result["D7"]["hidden_partial_group_success_forbidden"])
        self.assertTrue(all(p["volume_control_gate"] == "PASS" for p in plans))

    def test_taiji01_over_100_is_risk_not_selectable_target(self):
        result = build_candidate(intent("MSI", "STATUS"))
        risks = result["D7"]["risks"]
        self.assertEqual(len(risks), 2)
        self.assertTrue(all(r["risk"] == "BACKEND_GAIN_OVER_NORMALIZED_100" for r in risks))
        self.assertTrue(all(r["selectable"] is False for r in risks))


if __name__ == "__main__":
    unittest.main()
