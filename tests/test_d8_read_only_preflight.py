import argparse
import contextlib
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import d8_codex_mandatory_workflow as mandatory
import d8_codex_preflight_gate as gate
import d8_guard_eval as guard


AUDIT = {
    "query_count": 1,
    "mutation_count": 0,
    "transaction_read_only_confirmed": True,
    "xid_assigned": False,
    "queries": [{"statement_class": "SELECT", "sql_sha256": "0" * 64}],
}


def candidate():
    return guard.prepare_evaluation(
        "RUN_TEST", "TASK_TEST", {"mode": "sandbox", "readonly": True}, [],
        "PASS", "no active possible_alert matched task scope",
    )


class GuardEvaluationTests(unittest.TestCase):
    def test_projection_hash_is_exact_and_persistence_uses_same_projection(self):
        item = candidate()
        expected = guard.evaluation_insert_projection(item)
        expected_hash = hashlib.sha256(guard.canonical_json(expected).encode()).hexdigest()
        self.assertEqual(guard.evaluation_insert_projection_sha256(item), expected_hash)
        with mock.patch.object(guard, "_insert_evaluation") as insert:
            guard.persist_evaluation(item)
        insert.assert_called_once_with(expected)

    def test_evaluation_payload_tamper_fails_validation(self):
        item = candidate()
        item["evaluation_payload"]["decision"] = "HOLD"
        hash_input = json.loads(guard.canonical_json(item))
        hash_input["envelope"]["candidate_sha256"] = ""
        item["envelope"]["candidate_sha256"] = guard.sha256_payload(hash_input)
        report = guard.validate_evaluation(item)
        self.assertEqual(report["state"], "FAIL")
        self.assertFalse(report["checks"]["evaluation_payload"])

    def test_readonly_sql_is_fixed_allowlist(self):
        guard.ensure_readonly_sql(guard._ACTIVE_ALERTS_READONLY_QUERY)
        with self.assertRaises(ValueError):
            guard.ensure_readonly_sql("SELECT pg_advisory_lock(1);")


class EvidenceTests(unittest.TestCase):
    def test_hash_names_match_files_and_atomic_directory(self):
        item = candidate()
        validation = guard.validate_evaluation(item)
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "RUN_TEST"
            with mock.patch.object(gate, "readonly_output_dir", return_value=out):
                result = gate.write_readonly_evidence(
                    "RUN_TEST", item, validation, {"decision": "PASS", "exit_code": 0}, AUDIT
                )
            self.assertEqual(result["output_dir"], out)
            actual = hashlib.sha256((out / "canonical_evaluation_candidate.json").read_bytes()).hexdigest()
            self.assertEqual(actual, (out / "CANDIDATE_FILE_SHA256").read_text().strip())
            projection = out / "canonical_would_insert_projection.json"
            self.assertEqual(
                hashlib.sha256(projection.read_bytes()).hexdigest(),
                (out / "WOULD_INSERT_SHA256").read_text().strip(),
            )
            self.assertFalse((out.parent / ".RUN_TEST.tmp").exists())

    def test_structural_pass_with_warn_decision_is_verifier_hold(self):
        item = candidate()
        validation = guard.validate_evaluation(item)
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "RUN_WARN"
            with mock.patch.object(gate, "readonly_output_dir", return_value=out):
                gate.write_readonly_evidence(
                    "RUN_WARN", item, validation,
                    {"decision": "WARN", "exit_code": 10}, AUDIT,
                )
            verifier = json.loads((out / "verifier_result.json").read_text())
        self.assertEqual(verifier["STRUCTURAL_VALIDATION"], "PASS")
        self.assertEqual(verifier["VERIFIER_RESULT"], "HOLD")

    def test_evidence_write_failure_becomes_hold(self):
        argv = [
            "gate", "--task-name", "TASK", "--scope-json", "{}", "--mode", "sandbox",
            "--run-id", "RUN_FAIL", "--preflight-mode", "READ_ONLY",
        ]
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(gate, "load_alerts", return_value=[]), \
             mock.patch.object(gate, "readonly_sql_audit", return_value=AUDIT), \
             mock.patch.object(gate, "persist_evaluation", side_effect=AssertionError("persist called")), \
             mock.patch.object(gate, "write_readonly_evidence", side_effect=OSError("no space")), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            code = gate.main()
        self.assertEqual(code, 20)
        self.assertIn("STATE=HOLD", output.getvalue())
        self.assertIn("PRODUCTION_PERSISTENCE=NOT_RUN", output.getvalue())

    def test_database_not_confirmed_reports_unknown_mutation_and_xid(self):
        argv = [
            "gate", "--task-name", "TASK", "--scope-json", "{}", "--mode", "sandbox",
            "--run-id", "RUN_DB_FAIL", "--preflight-mode", "READ_ONLY",
        ]
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(gate, "load_alerts", side_effect=RuntimeError("db unavailable")), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            code = gate.main()
        text = output.getvalue()
        self.assertEqual(code, 20)
        self.assertIn("READ_ONLY_CONFIRMED=FALSE", text)
        self.assertIn("SQL_MUTATION_COUNT=UNKNOWN", text)
        self.assertIn("XID_ASSIGNED=UNKNOWN", text)


class MandatoryTests(unittest.TestCase):
    TASK_ID = "D8_MANDATORY_TASK_20260101_000000_TASK"

    def args(self, **updates):
        values = dict(
            task_name="TASK", mode="sandbox", preflight_mode="READ_ONLY", scope_json="{}",
            allowed_paths_json="[]", forbidden_paths_json="[]", expected_output="result",
            explicit_human_release=False, capsule=None, task_state="HOLD", result_summary="held",
        )
        values.update(updates)
        return argparse.Namespace(**values)

    def make_valid_capsule(self, root: Path, *, decision="PASS", preflight_mode="READ_ONLY"):
        if preflight_mode == "READ_ONLY":
            report = root / "runtime/d8/preflight" / self.TASK_ID / "validation_report.json"
        else:
            report = root / "runtime/d8_db/reports/D8_CODEX_PREFLIGHT_20260101_000000.json"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text("{}\n")
        tasks = root / "runtime/total_field/codex_mandatory_workflow/tasks"
        tasks.mkdir(parents=True, exist_ok=True)
        capsule = {
            "task_id": self.TASK_ID,
            "task_name": "TASK",
            "mode": "sandbox",
            "preflight_mode": preflight_mode,
            "allowed_paths": ["tools/safe.py"],
            "forbidden_paths": ["AGENTS.md"],
            "preflight_decision": decision,
            "permission": mandatory.permission(decision),
            "mandatory_preflight": True,
            "preflight_report": report.relative_to(root).as_posix(),
            "preflight_report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
            "safety_flags": mandatory.safety_flags(
                d8_local_db_write=preflight_mode == "PERSIST"
            ),
            "capsule_sha256": "",
        }
        capsule["capsule_sha256"] = mandatory.capsule_sha256(capsule)
        path = tasks / f"{self.TASK_ID}.json"
        path.write_text(json.dumps(capsule))
        return path, capsule, report

    def test_start_runs_preflight_once_and_carries_mode(self):
        output_root = f"runtime/d8/preflight/{self.TASK_ID}"
        proc = subprocess.CompletedProcess(
            [], 0, f"STATE=PASS\nDECISION=PASS\nOUTPUT_ROOT={output_root}\n", ""
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = root / output_root / "validation_report.json"
            report.parent.mkdir(parents=True)
            report.write_text("{}\n")
            with mock.patch.object(mandatory, "ROOT", root), \
                 mock.patch.object(mandatory, "stamp", return_value="20260101_000000"), \
                 mock.patch.object(mandatory, "run", return_value=proc) as runner:
                code = mandatory.cmd_start(self.args())
                capsules = list(root.glob("runtime/total_field/codex_mandatory_workflow/tasks/*.json"))
                saved = json.loads(capsules[0].read_text())
        self.assertEqual(code, 0)
        self.assertEqual(runner.call_count, 1)
        self.assertEqual(saved["preflight_mode"], "READ_ONLY")
        self.assertFalse(saved["safety_flags"]["D8_LOCAL_DB_WRITE"])
        self.assertEqual(saved["preflight_report_sha256"], hashlib.sha256(b"{}\n").hexdigest())
        self.assertEqual(saved["capsule_sha256"], mandatory.capsule_sha256(saved))

    def test_start_without_readonly_evidence_does_not_write_capsule(self):
        proc = subprocess.CompletedProcess([], 20, "STATE=HOLD\nDECISION=HOLD\nOUTPUT_ROOT=false\n", "")
        with tempfile.TemporaryDirectory() as temp, \
             mock.patch.object(mandatory, "ROOT", Path(temp)), \
             mock.patch.object(mandatory, "run", return_value=proc):
            code = mandatory.cmd_start(self.args())
            capsules = list(Path(temp).glob("runtime/total_field/codex_mandatory_workflow/tasks/*.json"))
        self.assertEqual(code, 20)
        self.assertEqual(capsules, [])

    def test_readonly_finalize_never_calls_writeback(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with mock.patch.object(mandatory, "ROOT", root):
                capsule, _, _ = self.make_valid_capsule(root)
            with mock.patch.object(mandatory, "ROOT", root), \
                 mock.patch.object(mandatory, "run", side_effect=AssertionError("writeback called")):
                code = mandatory.cmd_finalize(self.args(capsule=str(capsule)))
            result = json.loads(next(root.glob("runtime/total_field/codex_mandatory_workflow/results/*.json")).read_text())
        self.assertEqual(code, 20)
        self.assertIsNone(result["writeback_report"])
        self.assertFalse(result["safety_flags"]["D8_LOCAL_DB_WRITE"])
        self.assertEqual(result["production_persistence"], "NOT_RUN")

    def test_missing_mode_finalize_holds_before_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            tasks = root / "runtime/total_field/codex_mandatory_workflow/tasks"
            tasks.mkdir(parents=True)
            capsule = tasks / f"{self.TASK_ID}.json"
            capsule.write_text(json.dumps({"task_id": self.TASK_ID, "task_name": "TASK"}))
            with mock.patch.object(mandatory, "ROOT", root):
                code = mandatory.cmd_finalize(self.args(capsule=str(capsule)))
            artifacts = list(root.glob("runtime/total_field/codex_mandatory_workflow/seals/*"))
        self.assertEqual(code, 20)
        self.assertEqual(artifacts, [])

    def test_tampered_report_holds_before_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with mock.patch.object(mandatory, "ROOT", root):
                capsule, _, report = self.make_valid_capsule(root)
            report.write_text("tampered")
            with mock.patch.object(mandatory, "ROOT", root):
                code = mandatory.cmd_finalize(self.args(capsule=str(capsule)))
            artifacts = list(root.glob("runtime/total_field/codex_mandatory_workflow/seals/*"))
        self.assertEqual(code, 20)
        self.assertEqual(artifacts, [])

    def test_pass_task_state_rejected_after_warn_preflight(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with mock.patch.object(mandatory, "ROOT", root):
                capsule, _, _ = self.make_valid_capsule(root, decision="WARN")
                code = mandatory.cmd_finalize(
                    self.args(capsule=str(capsule), task_state="PASS")
                )
            artifacts = list(root.glob("runtime/total_field/codex_mandatory_workflow/seals/*"))
        self.assertEqual(code, 20)
        self.assertEqual(artifacts, [])

    def test_hold_preflight_cannot_downgrade_to_info_or_warn(self):
        for task_state in ("INFO", "WARN"):
            with self.subTest(task_state=task_state), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                with mock.patch.object(mandatory, "ROOT", root):
                    capsule, _, _ = self.make_valid_capsule(
                        root, decision="HOLD", preflight_mode="PERSIST"
                    )
                with mock.patch.object(mandatory, "ROOT", root), \
                     mock.patch.object(mandatory, "run") as runner:
                    code = mandatory.cmd_finalize(self.args(
                        capsule=str(capsule), preflight_mode="PERSIST", task_state=task_state
                    ))
                seals = list(root.glob("runtime/total_field/codex_mandatory_workflow/seals/*"))
                results = list(root.glob("runtime/total_field/codex_mandatory_workflow/results/*"))
                self.assertEqual(code, 20)
                self.assertEqual(seals, [])
                self.assertEqual(results, [])
                runner.assert_not_called()

    def test_readonly_validate_holds_without_database_access(self):
        with tempfile.TemporaryDirectory() as temp, \
             mock.patch.object(mandatory, "ROOT", Path(temp)), \
             mock.patch.object(mandatory, "count", side_effect=AssertionError("database accessed")):
            code = mandatory.cmd_validate(self.args())
        self.assertEqual(code, 20)


if __name__ == "__main__":
    unittest.main()
