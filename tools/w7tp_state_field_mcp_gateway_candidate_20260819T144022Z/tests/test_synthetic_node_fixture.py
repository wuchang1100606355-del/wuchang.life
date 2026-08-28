from __future__ import annotations

import json
import unittest

from tests.support import CANDIDATE_ROOT
from w7tp_state_field_gateway.inventory import validate_and_summarize_nodes


class SyntheticNodeFixtureTests(unittest.TestCase):
    def test_synthetic_nodes_exercise_fault_domain_and_mobile_invariants(self) -> None:
        fixture = json.loads(
            (CANDIDATE_ROOT / "fixtures" / "synthetic_nodes.json").read_text(
                encoding="utf-8"
            )
        )
        summary = validate_and_summarize_nodes(fixture["nodes"])
        expected = fixture["expected"]
        self.assertEqual(summary["logical_node_count"], expected["logical_node_count"])
        self.assertEqual(
            len(summary["evidenced_physical_fault_domains"]),
            expected["evidenced_physical_fault_domains"],
        )
        shared = summary["evidenced_physical_fault_domains"][0]
        self.assertEqual(
            len(shared["logical_node_ids"]), expected["logical_planes_in_shared_domain"]
        )
        self.assertEqual(summary["mobile_shell_assumed"], expected["mobile_shell_assumed"])

    def test_synthetic_mobile_shell_claim_fails_closed(self) -> None:
        unsafe = [
            {
                "id": "synthetic-mobile",
                "node_class": "mobile_sensing_light_compute_node",
                "physical_fault_domain_id": None,
                "shell_capable": True,
                "execution_enabled": False,
            }
        ]
        with self.assertRaises(RuntimeError):
            validate_and_summarize_nodes(unsafe)


if __name__ == "__main__":
    unittest.main()
