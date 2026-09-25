from __future__ import annotations

import unittest
from unittest.mock import patch

from tools import w7tp_nl_goal_runner as runner


class NaturalLanguageTotalFieldGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.before = {
            "core/example.py": {"sha256": "b" * 64, "size": 10},
        }
        self.after = {
            "core/example.py": {"sha256": "a" * 64, "size": 12},
        }
        self.changes = {
            "created": [],
            "modified": ["core/example.py"],
            "deleted": [],
        }
        self.validation = {
            "state": "PASS_DETERMINISTIC_VALIDATION",
            "checks": [{"kind": "py_compile", "path": "core/example.py", "rc": 0}],
        }

    def test_verified_source_delta_routes_through_total_field(self) -> None:
        result = runner._total_field_source_delta_gate(
            run_id="0123456789abcdef0123456789abcdef",
            intent_hash="1" * 64,
            before=self.before,
            after=self.after,
            changes=self.changes,
            deterministic_validation=self.validation,
        )
        self.assertEqual(
            result["state"],
            "PASS_TOTAL_FIELD_SOURCE_DELTA_ADJUDICATION",
        )
        self.assertEqual(result["final_decision"], "ALLOW")
        self.assertEqual(result["fixed_point_status"], "REACHED")
        self.assertTrue(result["commit_applied"])
        self.assertFalse(result["raw_source_body_submitted"])

    def test_total_field_hold_blocks_live_land(self) -> None:
        with patch.object(
            runner,
            "llm_push",
            return_value={
                "final_decision": "HOLD",
                "fixed_point_status": "NOT_REACHED",
                "commit_applied": False,
            },
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "HOLD_TOTAL_FIELD_SOURCE_DELTA:HOLD:NOT_REACHED",
            ):
                runner._total_field_source_delta_gate(
                    run_id="0123456789abcdef0123456789abcdef",
                    intent_hash="2" * 64,
                    before=self.before,
                    after=self.after,
                    changes=self.changes,
                    deterministic_validation=self.validation,
                )


if __name__ == "__main__":
    unittest.main()
