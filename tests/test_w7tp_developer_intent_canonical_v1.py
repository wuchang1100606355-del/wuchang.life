#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / "configs/total_field/w7tp_developer_intent_canonical_v1.json"
LINEAGE = ROOT / "configs/total_field/w7tp_founder_intent_lineage_v1.json"


class DeveloperIntentCanonicalV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.canon = json.loads(CANON.read_text(encoding="utf-8"))
        cls.lineage = json.loads(LINEAGE.read_text(encoding="utf-8"))

    def test_only_active_lineage_enters_active_intents(self) -> None:
        expected = {x["intent_id"] for x in self.lineage["entries"] if x["status"] == "ACTIVE"}
        actual = {x["intent_id"] for x in self.canon["active_intents"]}
        self.assertEqual(actual, expected)

    def test_conflict_and_unresolved_are_preserved_as_gates(self) -> None:
        expected = {
            x["intent_id"] for x in self.lineage["entries"]
            if x["status"] in {"CONFLICT", "UNRESOLVED"}
        }
        actual = {x["intent_id"] for x in self.canon["mandatory_gates"]}
        self.assertEqual(actual, expected)

    def test_retired_intents_never_reenter_active_set(self) -> None:
        active = {x["intent_id"] for x in self.canon["active_intents"]}
        retired = {x["intent_id"] for x in self.canon["retired_intents"]}
        self.assertTrue(active.isdisjoint(retired))

    def test_8d_joint_field_contract(self) -> None:
        d = self.canon["dimension_contract"]
        self.assertEqual(d["mode"], "8_IN_1_SINGLE_STATE_FIELD")
        self.assertEqual(d["D6"], "Generative State Transmission")
        self.assertEqual(d["D7"], "Risk/Quarantine")
        self.assertTrue(d["sequential_pipeline_definition_forbidden"])

    def test_v23_pointer_gap_remains_blocking(self) -> None:
        v = self.canon["version_position"]
        self.assertEqual(v["founder_defined_mainline"], "W7TP/8D ADI V2.3")
        self.assertEqual(v["observed_machine_active_pointer"], "V2.1")
        self.assertFalse(v["pointer_change_allowed"])
        self.assertEqual(v["state"], "BLOCKED_BY_T007_AUTHORITY_LINEAGE_GAP")

    def test_artifact_creates_no_global_authority(self) -> None:
        a = self.canon["authority"]
        self.assertFalse(a["global_w7tp_canonical_mutation"])
        self.assertFalse(a["active_pointer_mutation"])
        self.assertFalse(a["runtime_activation"])
        self.assertFalse(a["d8_authority_created"])

    def test_gst_cannot_fall_back_to_delta(self) -> None:
        g = self.canon["gst_contract"]
        self.assertFalse(g["shared_base_mandatory"])
        self.assertIn("DELTA", g["forbidden_reductions"])
        self.assertIn("RECONSTRUCT_AND_VERIFY_TARGET_STATE", g["required_semantics"])


if __name__ == "__main__":
    unittest.main()
