from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.total_field.error_resolution_redteam_gate import (  # noqa: E402
    assert_no_ignored_errors,
    classify_error,
    classify_error_batch,
)


class ErrorResolutionRedteamGateTests(unittest.TestCase):
    def test_false_pass_after_fatal_goes_redteam(self):
        result = classify_error("fatal: pathspec did not match\nSTATE=PASS_FORWARD_GATE")
        self.assertEqual(result["state"], "REDTEAM_HOLD")
        self.assertEqual(result["code"], "FALSE_PASS_AFTER_FATAL")

    def test_pathspec_can_be_solved_by_later_seal(self):
        result = classify_error({
            "message": "fatal: pathspec did not match any files",
            "later_commit_sealed": True,
        })
        self.assertEqual(result["state"], "SOLVED")
        self.assertEqual(result["code"], "PATHSPEC_MISSING_SOLVED_BY_LATER_SEAL")

    def test_terminal_output_pasted_as_command_is_solved_shell_only(self):
        result = classify_error("[main: command not found\ntaiji_admin@MSI:~/Taiji_Hub$: No such file or directory")
        self.assertEqual(result["state"], "SOLVED")
        self.assertEqual(result["code"], "TERMINAL_OUTPUT_PASTED_AS_COMMAND")

    def test_no_changes_added_after_seal_is_solved_no_op(self):
        result = classify_error({
            "message": "no changes added to commit",
            "already_sealed": True,
        })
        self.assertEqual(result["state"], "SOLVED")
        self.assertEqual(result["code"], "DUPLICATE_RERUN_AFTER_SEAL")

    def test_broken_pipe_goes_redteam(self):
        result = classify_error("client_loop: send disconnect: Broken pipe")
        self.assertEqual(result["state"], "REDTEAM_HOLD")
        self.assertEqual(result["code"], "SSH_BROKEN_PIPE")

    def test_frontend_drift_goes_redteam(self):
        result = classify_error("modified: web/packet_inference_cockpit/app.js")
        self.assertEqual(result["state"], "REDTEAM_HOLD")
        self.assertEqual(result["code"], "FRONTEND_COCKPIT_DRIFT")

    def test_unknown_error_goes_redteam(self):
        result = classify_error("unexpected unclassified failure")
        self.assertEqual(result["state"], "REDTEAM_HOLD")
        self.assertEqual(result["code"], "UNKNOWN_ERROR_ROUTED_TO_REDTEAM")

    def test_batch_never_ignores_errors(self):
        result = classify_error_batch([
            {"message": "no changes added to commit", "already_sealed": True},
            "client_loop: send disconnect: Broken pipe",
            "unexpected unclassified failure",
        ])
        self.assertTrue(result["NO_ERROR_IGNORED"])
        self.assertEqual(result["TOTAL_ERRORS"], 3)
        self.assertEqual(result["SOLVED_COUNT"], 1)
        self.assertEqual(result["REDTEAM_COUNT"], 2)
        self.assertEqual(result["STATE"], "HOLD_REDTEAM_ERRORS_PRESENT")

    def test_assert_no_ignored_errors_returns_accounted_batch(self):
        result = assert_no_ignored_errors([
            "[main: command not found\ntaiji_admin@MSI:~/Taiji_Hub$: No such file or directory",
            "modified: web/packet_inference_cockpit/app.js",
        ])
        self.assertTrue(result["NO_ERROR_IGNORED"])
        self.assertEqual(result["TOTAL_ERRORS"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
