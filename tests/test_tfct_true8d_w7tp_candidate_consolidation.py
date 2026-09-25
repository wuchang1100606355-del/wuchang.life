from __future__ import annotations

import copy
import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.verify.verify_tfct_true8d_w7tp_candidate_consolidation import (  # noqa: E402
    content_errors,
    load_schema,
    schema_errors,
    valid_candidate_vector,
    valid_committed_vector,
)


class TFCTTrue8DW7TPCandidateConsolidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load_schema()

    def test_candidate_vector_is_valid(self):
        self.assertEqual(schema_errors(valid_candidate_vector(), self.schema), [])

    def test_committed_allow_vector_is_valid(self):
        self.assertEqual(schema_errors(valid_committed_vector(), self.schema), [])

    def test_candidate_cannot_commit_or_create_tfs(self):
        value = valid_candidate_vector()
        value["verification"] = {
            "final_decision": "ALLOW",
            "commit_applied": True,
        }
        value["tfs_result"] = {
            "state_ref": "tfs-state:invalid",
            "tfid": "tfid:invalid",
            "total_field_hash": "total-field-hash:invalid",
        }
        self.assertTrue(schema_errors(value, self.schema))

    def test_committed_requires_allow_and_reached_fixed_point(self):
        value = valid_committed_vector()
        value["verification"] = {
            "final_decision": "BLOCK",
            "commit_applied": False,
        }
        value["fixed_point_status"] = "NOT_REACHED"
        self.assertTrue(schema_errors(value, self.schema))

    def test_each_dimension_reference_is_required(self):
        for index in range(1, 9):
            with self.subTest(dimension=index):
                value = valid_candidate_vector()
                del value["dimensions"][f"D{index}_ref"]
                self.assertTrue(schema_errors(value, self.schema))

    def test_unknown_top_level_and_nested_members_are_rejected(self):
        top_level = valid_candidate_vector()
        top_level["unexpected"] = True
        self.assertTrue(schema_errors(top_level, self.schema))

        nested = valid_candidate_vector()
        nested["verification"]["unexpected"] = True
        self.assertTrue(schema_errors(nested, self.schema))

    def test_non_allow_candidate_preserves_no_new_tfs(self):
        for decision in ("HOLD", "BLOCK", "QUARANTINE"):
            with self.subTest(decision=decision):
                value = copy.deepcopy(valid_candidate_vector())
                value["verification"]["final_decision"] = decision
                value["verification"]["commit_applied"] = False
                value["tfs_result"] = None
                self.assertEqual(schema_errors(value, self.schema), [])

    def test_document_and_protected_file_checks_pass(self):
        self.assertEqual(content_errors(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
