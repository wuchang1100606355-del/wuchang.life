#!/usr/bin/env python3
from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/"configs/total_field/w7tp_v23_authority_lineage_gap_v1.json"
POINTER=ROOT/"runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json"
FIELD=ROOT/"runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_CANONICAL.json"
DEV=ROOT/"configs/total_field/w7tp_developer_intent_canonical_v1.json"
AUTH=ROOT/"runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json"
PRE=ROOT/"runtime/total_field/adaptive_network/W7TP_ADAPTIVE_NETWORK_RUNTIME_ACTIVATION_20260924/AUTHORITY_POINTER_PREIMAGE.json"
D8=ROOT/"evidence/total_field/gst_v23_runtime_consumer_binding_candidate/GST_V23_D8_FORMAL_CLOSURE_20260924/D8_FORMAL_CLOSURE_DECISION.json"

class V23AuthorityLineageGapV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=json.loads(REPORT.read_text(encoding="utf-8"))

    def test_report_is_hold_not_promotion(self):
        self.assertEqual(self.r["state"],"PASS_PRECISE_HOLD_GAPS_IDENTIFIED")
        self.assertFalse(self.r["authority"]["canonical_pointer_mutated"])
        self.assertFalse(self.r["safe_conclusion"]["pointer_change_allowed_now"])

    def test_pointer_is_still_v21(self):
        p=json.loads(POINTER.read_text(encoding="utf-8"))
        self.assertEqual(p["version"],"2.1")

    def test_current_field_semantics_conflict_with_developer_canonical(self):
        f=json.loads(FIELD.read_text(encoding="utf-8"))
        d=json.loads(DEV.read_text(encoding="utf-8"))
        dims={x["id"]:x["field_en"] for x in f["dimensions"]}
        self.assertNotEqual(dims["D6"],d["dimension_contract"]["D6"])
        self.assertNotEqual(dims["D7"],d["dimension_contract"]["D7"])

    def test_current_total_field_preserves_gst_effect_as_additive_superset(self):
        cur=json.loads(AUTH.read_text(encoding="utf-8"))
        pre=json.loads(PRE.read_text(encoding="utf-8"))
        d8=json.loads(D8.read_text(encoding="utf-8"))
        self.assertTrue(set(pre["allowed_effects"]).issubset(set(cur["allowed_effects"])))
        self.assertIn(d8["required_effect"],cur["allowed_effects"])

    def test_exact_d8_closure_did_not_promote_global_pointer(self):
        d8=json.loads(D8.read_text(encoding="utf-8"))
        self.assertTrue(d8["runtime_activated"])
        self.assertFalse(d8["canonical_pointer_changed"])
        self.assertEqual(d8["scope_boundary"],"DOES_NOT_PROMOTE_GLOBAL_CANONICAL_OR_SECOND_TOTAL_FIELD")

    def test_four_precise_gaps_are_explicit(self):
        self.assertEqual({x["gap_id"] for x in self.r["gaps"]},{"G1","G2","G3","G4"})

if __name__=="__main__":
    unittest.main()
