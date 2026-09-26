#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINEAGE = ROOT / "configs/total_field/w7tp_founder_intent_lineage_v1.json"
POINTER = ROOT / "runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json"
ALLOWED = {"ACTIVE", "SUPERSEDED", "REVOKED", "CONFLICT", "UNRESOLVED"}


class FounderIntentLineageV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(LINEAGE.read_text(encoding="utf-8"))
        cls.entries = {row["intent_id"]: row for row in cls.data["entries"]}

    def test_classification_vocabulary_and_unique_ids(self) -> None:
        ids = [row["intent_id"] for row in self.data["entries"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(ids)
        for row in self.data["entries"]:
            self.assertIn(row["status"], ALLOWED)
            self.assertTrue(row["assertion"].strip())

    def test_lineage_artifact_cannot_create_authority(self) -> None:
        authority = self.data["authority"]
        self.assertFalse(authority["canonical_mutation"])
        self.assertFalse(authority["runtime_effect"])
        self.assertFalse(authority["active_pointer_mutation"])
        self.assertFalse(authority["d8_authority_created"])
        self.assertEqual(authority["formal_effect_authority"], "TAIJI01_TOTAL_FIELD_ONLY")

    def test_v21_machine_pointer_vs_v23_founder_intent_is_explicit(self) -> None:
        pointer = json.loads(POINTER.read_text(encoding="utf-8"))
        self.assertEqual(pointer["version"], "2.1")
        self.assertEqual(self.entries["FI-013"]["status"], "ACTIVE")
        self.assertEqual(self.entries["FI-014"]["status"], "CONFLICT")
        self.assertEqual(self.entries["FI-015"]["status"], "UNRESOLVED")

    def test_latest_gst_semantics_retire_delta_fallback(self) -> None:
        self.assertEqual(self.entries["FI-006"]["status"], "ACTIVE")
        self.assertEqual(self.entries["FI-018"]["status"], "REVOKED")
        self.assertEqual(self.entries["FI-019"]["status"], "SUPERSEDED")
        self.assertIn("求同存異", self.entries["FI-006"]["assertion"])
        self.assertIn("差分傳輸", self.entries["FI-018"]["assertion"])
        self.assertIn("明確撤回", self.entries["FI-018"]["assertion"])

    def test_8d_is_joint_field_not_eight_step_pipeline(self) -> None:
        self.assertEqual(self.entries["FI-001"]["status"], "ACTIVE")
        self.assertEqual(self.entries["FI-016"]["status"], "SUPERSEDED")
        self.assertIn("8_IN_1_SINGLE_STATE_FIELD", self.entries["FI-001"]["assertion"])

    def test_branch_mergeability_never_grants_authority(self) -> None:
        self.assertIn("Git clean merge", self.data["current_true_intent_coordinate"]["branch_merge_rule"])
        self.assertTrue(self.data["branch_supply_demand"])
        self.assertTrue(all(row["merge_now"] is False for row in self.data["branch_supply_demand"]))


if __name__ == "__main__":
    unittest.main()
