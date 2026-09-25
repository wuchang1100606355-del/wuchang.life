import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "total_field" / "w7tp_candidate_fine_grain_reviewer.py"
SPEC = importlib.util.spec_from_file_location("w7tp_candidate_fine_grain_reviewer", MODULE_PATH)
reviewer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = reviewer
SPEC.loader.exec_module(reviewer)


class FineGrainReviewerTests(unittest.TestCase):
    def decisions(self, candidate):
        return reviewer.analyze_candidate(candidate)[1]

    def test_one_trade_secret_unit_does_not_quarantine_document(self):
        units = self.decisions({"public": "XDP performs fixed-offset prefiltering.", "private": "WHY_IT_RUNS private rule."})
        quarantined = [unit for unit in units if unit["decision"] == "TRADE_SECRET_QUARANTINE"]
        self.assertEqual(1, len(quarantined))
        self.assertLess(len(quarantined), len(units))
        self.assertEqual("$.candidate.private", quarantined[0]["source_path"])

    def test_mixed_public_and_secret_paragraph_is_split(self):
        units = self.decisions("XDP performs fixed-offset parsing. WHY_IT_RUNS contains the private expansion rule.")
        parts = {unit["exposure_part"] for unit in units}
        self.assertIn("PUBLIC_SAFE_PART", parts)
        self.assertIn("TRADE_SECRET_PART", parts)
        self.assertEqual(1, sum(unit["decision"] == "TRADE_SECRET_QUARANTINE" for unit in units))

    def test_perfect_carrier_requires_correction(self):
        units = self.decisions("QUIC is the perfect carrier for this candidate design.")
        self.assertEqual("ACCEPT_WITH_CORRECTION", units[0]["decision"])
        self.assertTrue(units[0]["correction_text"])

    def test_unsupported_absolute_claim_is_rejected(self):
        units = self.decisions("W7TP is absolutely secure.")
        self.assertEqual("REJECT_OVERCLAIM", units[0]["decision"])

    def test_microsecond_performance_claim_is_held(self):
        units = self.decisions("The measured end-to-end latency is 8 microseconds.")
        self.assertEqual("HOLD_FOR_EVIDENCE", units[0]["decision"])
        self.assertTrue(units[0]["evidence_required"])

    def test_cloud_formal_execution_authority_is_drift(self):
        units = self.decisions("The cloud has formal execution authority for W7TP operations.")
        self.assertEqual("REJECT_TECHNICAL_DRIFT", units[0]["decision"])

    def test_native_json_array_items_are_independent(self):
        parsed, units = reviewer.analyze_candidate(["first public unit", "second public unit"])
        self.assertEqual("native_json_array", parsed.structure_type)
        self.assertEqual(2, len(units))
        self.assertEqual({"$.candidate[0]", "$.candidate[1]"}, {unit["source_path"] for unit in units})

    def test_markdown_fenced_json_is_parsed(self):
        parsed, units = reviewer.analyze_candidate('```json\n{"a": "one", "b": "two"}\n```')
        self.assertEqual("markdown_code_fence_containing_json", parsed.structure_type)
        self.assertEqual(2, len(units))

    def test_long_report_splits_by_heading_and_bullet(self):
        report = "# Architecture\n\nPublic overview.\n\n- XDP parses fixed offsets.\n- Userspace performs local verification.\n\n# Evidence\n\nAppend-only evidence chain."
        parsed, units = reviewer.analyze_candidate(report)
        self.assertEqual("single_long_text_report", parsed.structure_type)
        self.assertGreater(len(units), 1)
        self.assertIn("Architecture", {unit["source_section"] for unit in units})

    def test_truncated_outer_json_does_not_collapse_to_inner_object(self):
        candidate = '{"metadata": {"authority": "candidate"},\n  "public": "XDP fixed-offset parsing",\n  "private": "WHY_IT_RUNS private rule'
        parsed, units = reviewer.analyze_candidate(candidate)
        self.assertEqual("multi_section_mixed_structure", parsed.structure_type)
        self.assertGreater(len(units), 1)
        self.assertEqual(1, sum(unit["decision"] == "TRADE_SECRET_QUARANTINE" for unit in units))


if __name__ == "__main__":
    unittest.main()
