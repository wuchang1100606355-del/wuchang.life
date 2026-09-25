from __future__ import annotations

import unittest
from unittest.mock import patch

from services.gateway import natural_language_control as nl_control
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

    def test_plan_requires_pointer_first_context_delivery(self) -> None:
        resource_decision = {
            "RESOURCE_COORDINATES": [],
            "QUALIFIED_SET": ["MSI_OLLAMA_LOCAL"],
            "PREFERRED_SET": ["MSI_OLLAMA_LOCAL"],
        }
        with (
            patch.object(
                nl_control,
                "arbitrate_resources",
                return_value=resource_decision,
            ),
            patch.object(
                nl_control,
                "build_static_state_cell_envelope",
                return_value={"state": "STATIC_TEST_CELL"},
            ),
            patch.object(nl_control, "_git", return_value="fixture"),
        ):
            plan = nl_control.build_plan(
                nl_control.NaturalLanguageRequest(
                    intent="test pointer first context delivery",
                    task_id="NLDEV-005",
                    dry_run=True,
                )
            )
        execution = plan["D5_EXECUTION"]
        risk = plan["D7_RISK"]
        self.assertEqual(
            execution["context_delivery_mode"],
            "TOTAL_FIELD_POINTER_FIRST_DYNAMIC_CONTEXT_PULL",
        )
        self.assertEqual(
            execution["context_bootstrap"],
            "POINTER_AND_REFERENCES_ONLY",
        )
        self.assertEqual(
            execution["dynamic_context_materialization"],
            "LOCAL_VOLATILE_ON_PULL",
        )
        self.assertEqual(
            execution["context_persistence"],
            "EPHEMERAL_BODY_REFERENCES_ONLY",
        )
        self.assertFalse(
            risk["full_dynamic_context_in_initial_model_bootstrap"]
        )
        self.assertFalse(risk["local_rule_ref_cloud_visible"])

    def test_bound_gemini_is_reasoning_organ_not_source_writer(self) -> None:
        resource_decision = {
            "RESOURCE_COORDINATES": [
                {
                    "RESOURCE_ID": "GEMINI_CODE_ASSIST",
                    "CONTEXT_BINDING_STATE": (
                        "POINTER_FIRST_TOTAL_FIELD_BOUND"
                    ),
                }
            ],
            "QUALIFIED_SET": [
                "GEMINI_CODE_ASSIST",
                "MSI_OLLAMA_LOCAL",
            ],
            "PREFERRED_SET": ["GEMINI_CODE_ASSIST"],
        }
        with (
            patch.object(
                nl_control,
                "arbitrate_resources",
                return_value=resource_decision,
            ),
            patch.object(
                nl_control,
                "build_static_state_cell_envelope",
                return_value={"state": "STATIC_TEST_CELL"},
            ),
            patch.object(nl_control, "_git", return_value="fixture"),
        ):
            plan = nl_control.build_plan(
                nl_control.NaturalLanguageRequest(
                    intent="test bound gemini reasoning organ",
                    task_id="NLDEV-005",
                    dry_run=True,
                )
            )
        execution = plan["D5_EXECUTION"]
        self.assertEqual(
            execution["selected_candidate_builder"],
            "MSI_OLLAMA_LOCAL",
        )
        self.assertEqual(
            execution["bound_reasoning_organs"],
            ["GEMINI_CODE_ASSIST"],
        )
        self.assertEqual(
            execution["gemini_a2a_binding"],
            "POINTER_FIRST_TOTAL_FIELD_BOUND",
        )
        self.assertFalse(execution["gemini_direct_source_write"])
        self.assertEqual(
            execution["resource_binding_state"],
            "EXECUTABLE_LOCAL_SOURCE_BUILDER_WITH_BOUND_GEMINI_REASONING_ORGAN",
        )


if __name__ == "__main__":
    unittest.main()
