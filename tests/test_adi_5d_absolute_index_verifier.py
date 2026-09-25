from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path("/home/taiji_admin/Taiji_Hub")
VERIFIER_PATH = ROOT / "tools/intent_field/adi_5d_absolute_index_verifier.py"
spec = importlib.util.spec_from_file_location("adi_5d_absolute_index_verifier", VERIFIER_PATH)
verifier = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(verifier)


class ADI5DAbsoluteIndexVerifierTest(unittest.TestCase):
    def test_adi_5d_absolute_index_pass_packet(self) -> None:
        packet = verifier.base_pass_packet()
        result = verifier.verify_packet(packet)
        self.assertEqual(result["DRY_RUN"], "PASS")
        self.assertEqual(result["CHECKS"]["ADI_5D_DIMENSION_CHECK"], "PASS")
        self.assertEqual(result["CHECKS"]["ARCHITECTURE_CHECK"], "PASS")

    def test_generic_5d_schema_is_rejected(self) -> None:
        packet = verifier.base_pass_packet()
        packet["generic_5d_schema_used"] = True
        result = verifier.verify_packet(packet)
        self.assertEqual(result["DRY_RUN"], "FAIL")
        self.assertIn("GENERIC_5D_SCHEMA_USED", result["ERRORS"])

    def test_adi_rule_disclosure_is_rejected(self) -> None:
        packet = verifier.base_pass_packet()
        packet["adi_absolute_index"]["actual_index_rules_disclosed"] = True
        packet["adi_index_rules"] = {"forbidden": "detail"}
        result = verifier.verify_packet(packet)
        self.assertEqual(result["DRY_RUN"], "FAIL")
        self.assertIn("ADI_ACTUAL_INDEX_RULES_DISCLOSED", result["ERRORS"])
        self.assertIn("ADI_INDEX_RULES_KEY_PRESENT", result["ERRORS"])

    def test_cloud_final_authority_is_rejected(self) -> None:
        packet = verifier.base_pass_packet()
        packet["verifier_contract"]["final_decision_by_cloud"] = True
        result = verifier.verify_packet(packet)
        self.assertEqual(result["DRY_RUN"], "FAIL")
        self.assertIn("CLOUD_FINAL_AUTHORITY_DRIFT", result["ERRORS"])

    def test_architecture_order_must_include_adi_after_8d(self) -> None:
        packet = copy.deepcopy(verifier.base_pass_packet())
        packet["architecture_order"][1], packet["architecture_order"][2] = (
            packet["architecture_order"][2],
            packet["architecture_order"][1],
        )
        result = verifier.verify_packet(packet)
        self.assertEqual(result["DRY_RUN"], "FAIL")
        self.assertIn("ARCHITECTURE_ORDER_INVALID", result["ERRORS"])


if __name__ == "__main__":
    unittest.main()
