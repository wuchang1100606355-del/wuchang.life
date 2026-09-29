from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from services.gateway import natural_language_control as nl_control
from tools import w7tp_local_model_agent as local_agent
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
            "TOTAL_FIELD_POINTER_FIRST_STATE_CELL_PULL",
        )
        self.assertEqual(execution["context_target_scope"], "ALL_CONTEXT_REQUIRING_LLM")
        self.assertEqual(execution["unbound_context_requiring_llm"], "HOLD")
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

    def test_local_model_prompt_excludes_static_state_cell(self) -> None:
        plan = {
            "TASK_ID": "NLDEV-005",
            "STATIC_STATE_CELL": {"legacy": "must-not-reach-model"},
            "RESOURCE_DECISION": {"legacy": "must-not-reach-model"},
            "D3_COORDINATE": {"affected_closure": ["core"]},
            "D5_EXECUTION": {"context_delivery_mode": "TOTAL_FIELD_POINTER_FIRST_STATE_CELL_PULL"},
            "D7_RISK": {"unbound_context_requiring_llm": "HOLD"},
        }
        prompt = runner.build_prompt("intent", runner.PROJECT_ROOT, plan)
        self.assertNotIn("STATIC_STATE_CELL", prompt)
        self.assertNotIn("must-not-reach-model", prompt)
        self.assertNotIn("RESOURCE_DECISION", prompt)
        self.assertIn("TOTAL_FIELD_POINTER_FIRST_STATE_CELL_PULL", prompt)

    def test_local_model_dynamic_context_pull_is_task_bound(self) -> None:
        bootstrap = {
            "pull_coordinate": "pull:test:local-model",
            "bootstrap_sha256": "a" * 64,
        }
        pulled = {
            "model_visible_context": {
                "context_ref": "context:test:local-model",
            },
            "transmission_semantics": {
                "semantic_class": "NON_DIFFERENTIAL_POINTER_FIRST_STATE_RECONSTRUCTION",
            },
        }
        broker = Mock()
        broker.register.return_value = bootstrap
        broker.pull.return_value = pulled
        with (
            patch.object(
                runner,
                "select_task_state_support_refs",
                return_value={"action_refs": ["A-1"], "adi_record_ids": ["ADI-1"]},
            ),
            patch.object(
                runner,
                "issue_task_state_minimum_packet",
                return_value={
                    "task_state_record_id": "ADI-TASK",
                    "packet": {
                        "packet_ref": "packet:test",
                        "packet_sha256": "b" * 64,
                    },
                },
            ),
            patch.object(
                runner,
                "TotalFieldDynamicContextPullBroker",
                return_value=broker,
            ),
        ):
            result = runner.pull_task_dynamic_context_for_model(
                task_id="NLDEV-005",
                action_id="A-1",
                provider_ref="provider:MSI_OLLAMA_LOCAL",
                model_ref="model:xiaoj:8b",
            )
        self.assertEqual(result["state"], "PASS_MODEL_DYNAMIC_CONTEXT_PULL")
        self.assertEqual(result["context_ref"], "context:test:local-model")
        self.assertNotIn("model_visible_context", result)
        self.assertNotIn(
            "reconstructed_projection",
            result["state_cell_transmission"],
        )
        self.assertEqual(
            result["state_cell_transmission"]["context_ref"],
            "context:test:local-model",
        )
        broker.pull.assert_called_once_with(
            "pull:test:local-model",
            task_ref="task:NLDEV-005",
            provider_ref="provider:MSI_OLLAMA_LOCAL",
            model_ref="model:xiaoj:8b",
        )

    def test_effectful_intent_scoped_read_only_markers_do_not_mask_effect(self) -> None:
        self.assertFalse(runner.effectful_intent("分析目前狀態"))
        marker_a = "禁止" + "修改"
        marker_b = "不得" + "寫入"
        self.assertTrue(
            runner.effectful_intent(
                f"新增工作並完成驗證，{marker_a}其他檔案"
            )
        )
        self.assertTrue(
            runner.effectful_intent(
                f"修改 X 的判定邏輯，{marker_b}外部系統"
            )
        )

    def test_stage_path_remains_available_after_observation_budget(self) -> None:
        streak = local_agent.MAX_CONSECUTIVE_OBSERVATION_CALLS + 1
        blocked, observed = local_agent._tool_budget("stage_path", streak)
        self.assertFalse(blocked)
        self.assertEqual(observed, streak)
        blocked, observed = local_agent._tool_budget("read_file", streak)
        self.assertTrue(blocked)
        self.assertGreater(observed, streak)

    def test_changed_python_tests_fall_back_to_unittest(self) -> None:
        with patch.object(runner.importlib.util, "find_spec", return_value=None):
            cmd, kind = runner._python_test_command(
                ["tests/test_w7tp_nl_goal_total_field_gate.py"]
            )
        self.assertEqual(kind, "unittest_changed")
        self.assertEqual(
            cmd,
            [
                "python3",
                "-m",
                "unittest",
                "-v",
                "tests.test_w7tp_nl_goal_total_field_gate",
            ],
        )

    def test_source_evidence_cache_is_bounded_and_retains_recent_content(self) -> None:
        cache: list[str] = []
        for index in range(5):
            entry = local_agent._source_evidence_text(
                "read_file",
                {"path": f"tools/example_{index}.py"},
                {
                    "state": "PASS",
                    "path": f"tools/example_{index}.py",
                    "start": 1,
                    "end": 2,
                    "content": f"line-{index}",
                },
            )
            cache = local_agent._append_source_evidence(cache, entry)
        self.assertEqual(
            len(cache),
            local_agent.MAX_SOURCE_EVIDENCE_ENTRIES,
        )
        joined = "\n".join(cache)
        self.assertNotIn("example_0.py", joined)
        self.assertIn("example_4.py", joined)
        self.assertIn("line-4", joined)
        self.assertLessEqual(
            sum(len(item) for item in cache),
            local_agent.MAX_SOURCE_EVIDENCE_TOTAL_CHARS,
        )

    def test_observation_budget_switches_to_progress_only_tools(self) -> None:
        full = {
            item["function"]["name"]
            for item in local_agent._active_tool_defs(0)
        }
        self.assertIn("read_file", full)
        progress = {
            item["function"]["name"]
            for item in local_agent._active_tool_defs(
                local_agent.MAX_CONSECUTIVE_OBSERVATION_CALLS
            )
        }
        self.assertEqual(
            progress,
            {"stage_path", "replace_text", "write_file"},
        )
        self.assertNotIn("read_file", progress)
        self.assertNotIn("search_text", progress)
        self.assertNotIn("run_check", progress)

    def test_local_agent_step_budget_is_adaptive(self) -> None:
        self.assertEqual(
            runner.local_agent_step_budget(
                {
                    "RESOURCE_DECISION": {
                        "TASK_PROFILE": {"complex_code": True}
                    }
                }
            ),
            64,
        )
        self.assertEqual(
            runner.local_agent_step_budget(
                {
                    "RESOURCE_DECISION": {
                        "TASK_PROFILE": {"complex_code": False}
                    }
                }
            ),
            32,
        )
        self.assertEqual(runner.local_agent_step_budget({}), 32)

    def test_local_agent_failure_codes_and_complex_step_budget(self) -> None:
        plan = {
            "RESOURCE_DECISION": {
                "TASK_PROFILE": {"complex_code": True}
            },
            "D3_COORDINATE": {
                "affected_closure": ["core"],
            },
        }
        cases = [
            (
                "Traceback\nRuntimeError: LOCAL_MODEL_STEP_LIMIT\n",
                "HOLD_LOCAL_MODEL_STEP_LIMIT",
            ),
            (
                "Traceback\nRuntimeError: LOCAL_MODEL_CALL_FAILED\n",
                "HOLD_LOCAL_MODEL_CALL_FAILED",
            ),
            (
                "Traceback\nRuntimeError: OTHER_FAILURE\n",
                "HOLD_LOCAL_MODEL_AGENT_FAILED",
            ),
        ]
        for stderr, expected in cases:
            mocked = Mock(
                returncode=1,
                stdout="",
                stderr=stderr,
            )
            with patch.object(
                runner.subprocess,
                "run",
                return_value=mocked,
            ) as run_mock:
                with self.assertRaisesRegex(
                    RuntimeError,
                    expected + r":stderr_sha256:[0-9a-f]{64}",
                ):
                    runner.run_local_agent(
                        "bounded prompt",
                        runner.PROJECT_ROOT,
                        plan,
                        120,
                    )
            cmd = run_mock.call_args.args[0]
            self.assertIn("--max-steps", cmd)
            self.assertEqual(
                cmd[cmd.index("--max-steps") + 1],
                "64",
            )

    def test_runner_real_task_gemini_reasoning_helper(self) -> None:
        plan = {
            "TASK_ID": "NLDEV-005",
            "D5_EXECUTION": {
                "gemini_a2a_binding": "POINTER_FIRST_TOTAL_FIELD_BOUND",
                "bound_reasoning_organs": ["GEMINI_CODE_ASSIST"],
            },
        }
        packet = {
            "packet_ref": "packet:test:real-task",
            "packet_sha256": "a" * 64,
        }
        with (
            patch.object(
                runner,
                "select_task_state_support_refs",
                return_value={
                    "action_refs": ["action:test:1"],
                    "adi_record_ids": ["capability:test:1"],
                },
            ) as selector,
            patch.object(
                runner,
                "issue_task_state_minimum_packet",
                return_value={
                    "task_state_record_id": "task-state:test:1",
                    "packet": packet,
                },
            ) as issuer,
            patch.object(
                runner,
                "TotalFieldDynamicContextPullBroker",
            ) as broker_type,
            patch.object(
                runner,
                "run_gemini_pointer_first_candidate",
                return_value={
                    "state": "PASS_GEMINI_A2A_POINTER_FIRST_CANDIDATE",
                    "context_ref": "context:test:real-task",
                    "candidate_sha256": "b" * 64,
                    "candidate": {
                        "state": "CANDIDATE_ONLY",
                        "candidate": {
                            "engineering_hypothesis": "bounded",
                        },
                    },
                    "total_field": {
                        "final_decision": "ALLOW",
                        "state_ref": "tfs-state:test",
                        "total_field_hash": "c" * 64,
                    },
                    "provider_reported_model": "gemini-test",
                    "provider_internal_context_controlled": False,
                },
            ) as gemini,
        ):
            broker_type.return_value.register.return_value = {
                "bootstrap_sha256": "d" * 64,
            }
            with patch.object(
                runner,
                "LIVE_CLOUD_REASONING_ENABLED",
                True,
            ):
                result = runner.gemini_task_state_reasoning_hint(
                    intent="implement bounded change",
                    plan=plan,
                    action_id="A-CURRENT",
                    timeout_seconds=120,
                )
        self.assertEqual(
            result["state"],
            "PASS_REAL_TASK_GEMINI_REASONING",
        )
        self.assertEqual(
            result["task_state_record_id"],
            "task-state:test:1",
        )
        self.assertEqual(result["packet_sha256"], "a" * 64)
        self.assertEqual(result["candidate_sha256"], "b" * 64)
        self.assertEqual(result["total_field_decision"], "ALLOW")
        selector.assert_called_once_with(
            task_id="NLDEV-005",
            current_action_id="A-CURRENT",
            max_actions=8,
            max_adi_refs=16,
        )
        issuer.assert_called_once_with(
            task_id="NLDEV-005",
            action_refs=["action:test:1"],
            support_adi_record_ids=["capability:test:1"],
        )
        self.assertEqual(gemini.call_count, 1)

    def test_pointer_first_plan_blocks_legacy_google_fallback(self) -> None:
        self.assertFalse(
            runner.legacy_google_fallback_allowed(
                {
                    "D5_EXECUTION": {
                        "context_delivery_mode": (
                            "TOTAL_FIELD_POINTER_FIRST_STATE_CELL_PULL"
                        )
                    }
                }
            )
        )
        self.assertFalse(
            runner.legacy_google_fallback_allowed(
                {"D5_EXECUTION": {"context_delivery_mode": "LEGACY"}}
            )
        )
        with patch.object(runner, "LIVE_CLOUD_REASONING_ENABLED", True):
            self.assertTrue(
                runner.legacy_google_fallback_allowed(
                    {"D5_EXECUTION": {"context_delivery_mode": "LEGACY"}}
                )
            )

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
            patch.object(nl_control, "LIVE_CLOUD_REASONING_ENABLED", True),
            patch.object(nl_control, "GOOGLE_FALLBACK", True),
        ):
            plan = nl_control.build_plan(
                nl_control.NaturalLanguageRequest(
                    intent="test bound gemini reasoning organ",
                    task_id="NLDEV-005",
                    dry_run=True,
                    google_fallback=True,
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
        self.assertTrue(execution["real_task_state_packet_auto_issue"])
        self.assertFalse(
            execution["legacy_vertex_direct_context_allowed"]
        )
        self.assertEqual(
            execution["real_task_state_sources"],
            [
                "WORK_LEDGER",
                "ACTION_LEDGER",
                "CURRENT_CONVERSATION_CHECKPOINT",
                "NATIVE_ADI_SELECTED_RECORDS",
            ],
        )
        self.assertIn(
            "REAL_TASK_STATE_MINIMUM_PACKET",
            execution["complex_code_reasoning_pipeline"],
        )
        self.assertIn(
            "GEMINI_A2A_POINTER_FIRST_CANDIDATE",
            execution["complex_code_reasoning_pipeline"],
        )
        self.assertTrue(
            plan["D7_RISK"]["gemini_reasoning_failure_local_fallback"]
        )
        self.assertTrue(
            plan["D7_RISK"]["gemini_candidate_never_becomes_source_truth"]
        )
        self.assertEqual(
            execution["resource_binding_state"],
            "EXECUTABLE_LOCAL_SOURCE_BUILDER_WITH_BOUND_GEMINI_REASONING_ORGAN",
        )


if __name__ == "__main__":
    unittest.main()
