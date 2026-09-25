#!/usr/bin/env python3
"""Focused self-check tests that never execute C1-C9 scenarios."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from tools.total_field import w7tp_xiaoj_dual_llm_c1_c9_runner as runner_module


class C1C9SelfCheckTests(unittest.TestCase):
    def test_self_check_imports_closure_without_executing_scenarios(self) -> None:
        forbidden_runners = tuple(
            lambda: self.fail("self-check executed a canary scenario")
            for _scenario_id in runner_module.SCENARIO_IDS
        )
        with patch.object(runner_module, "SCENARIO_RUNNERS", forbidden_runners):
            result = runner_module.run_self_check()
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(result["scenario_execution_count"], 0)
        self.assertEqual(
            result["local_imported_count"], len(runner_module.LOCAL_IMPORT_CLOSURE)
        )
        self.assertEqual(result["external_call_count"], 0)
        self.assertEqual(result["vertex_call_count"], 0)
        self.assertEqual(result["ollama_call_count"], 0)

    def test_self_check_main_emits_one_json_document(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = runner_module.main(["--self-check"])
        text = stdout.getvalue()
        payload = json.loads(text)
        self.assertEqual(exit_code, 0)
        self.assertEqual(text.count("\n"), 1)
        self.assertEqual(payload["mode"], "SELF_CHECK_ONLY_NO_SCENARIO_EXECUTION")
        self.assertEqual(payload["scenario_execution_count"], 0)
        self.assertEqual(payload["state"], "PASS")


if __name__ == "__main__":
    unittest.main()
