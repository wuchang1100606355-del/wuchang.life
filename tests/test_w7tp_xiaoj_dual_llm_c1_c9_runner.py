#!/usr/bin/env python3
"""Focused checks for the repo-mounted XiaoJ C1-C9 canary runner."""

from __future__ import annotations

import ast
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tools.total_field.w7tp_xiaoj_dual_llm_c1_c9_runner import (
    RUN_ID,
    SCENARIO_IDS,
    main,
    run_c1_c9,
)


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "tools/total_field/w7tp_xiaoj_dual_llm_c1_c9_runner.py"
COMPOSE_PATH = (
    ROOT
    / "containers/total_field/true8d-contract-sandbox/"
    "compose.xiaoj-dual-llm-c1-c9.runner.yaml"
)


class C1C9RunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = run_c1_c9()

    def test_all_nine_scenarios_pass(self) -> None:
        self.assertEqual(self.result["run_id"], RUN_ID)
        self.assertEqual(self.result["scenario_ids"], list(SCENARIO_IDS))
        self.assertEqual(self.result["scenarios_pass"], 9)
        self.assertEqual(self.result["scenarios_total"], 9)
        self.assertEqual(self.result["state"], "PASS")

    def test_governance_and_human_response_contracts(self) -> None:
        self.assertEqual(self.result["total_field_authority_check"], "PASS")
        self.assertEqual(self.result["conflict_hold_check"], "PASS")
        self.assertEqual(self.result["single_provider_degradation_check"], "PASS")
        self.assertEqual(self.result["traditional_chinese_reply_check"], "PASS")
        self.assertEqual(self.result["persona_tfs_hash_exclusion"], "PASS")

    def test_forbidden_integrations_and_writes_are_zero(self) -> None:
        self.assertEqual(self.result["provider_mode"], "SYNTHETIC_INJECTED_ONLY")
        for key in (
            "external_call_count",
            "workspace_call_count",
            "vertex_call_count",
            "ollama_call_count",
            "secret_read_count",
            "member_plaintext_read_count",
            "db_write_count",
            "repo_write_count",
            "formal_state_write_count",
        ):
            self.assertEqual(self.result[key], 0)

    def test_main_emits_one_json_document(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main()
        text = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertEqual(text.count("\n"), 1)
        self.assertEqual(json.loads(text)["scenarios_pass"], 9)

    def test_runner_has_no_external_io_imports(self) -> None:
        tree = ast.parse(RUNNER_PATH.read_text(encoding="utf-8"))
        imported = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertTrue(
            imported.isdisjoint(
                {
                    "google",
                    "ollama",
                    "psycopg",
                    "requests",
                    "socket",
                    "sqlite3",
                    "subprocess",
                    "urllib",
                    "vertexai",
                }
            )
        )

    def test_compose_is_immutable_read_only_and_non_networked(self) -> None:
        text = COMPOSE_PATH.read_text(encoding="utf-8")
        required = (
            "w7tp-true8d-contract-sandbox@sha256:066cf56812708adef0fdbfd1677fb6bf3401c86e0c1c309ab4472920abde7ae5",
            "pull_policy: never",
            "network_mode: none",
            "read_only: true",
            "source: /home/taiji_admin/Taiji_Hub",
            "target: /workspace",
            "no-new-privileges:true",
            "cap_drop: [\"ALL\"]",
            "pids_limit: 32",
            "pids: 32",
            "/workspace/tools/total_field/w7tp_xiaoj_dual_llm_c1_c9_runner.py",
        )
        for value in required:
            self.assertIn(value, text)
        self.assertNotIn("ports:", text)
        self.assertNotIn("build:", text)


if __name__ == "__main__":
    unittest.main()
