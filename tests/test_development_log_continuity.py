from __future__ import annotations
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core.intent_continuity import sync_checkpoint_evidence
from tools import w7tp_nl_goal_runner as runner

class DevelopmentLogContinuityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.state = self.root / "state"
        self.state.mkdir()
        self.work = self.state / "WORK_LEDGER.json"
        self.action = self.state / "ACTION_LEDGER.json"
        self.checkpoint = self.state / "CURRENT_CONVERSATION_CHECKPOINT.json"
        task = {
            "TASK_ID":"T-020", "PARENT_INTENT":"test", "TITLE":"log",
            "DESCRIPTION":"log", "STATE":"DOING", "PRIORITY":"P0",
            "D3_COORDINATE":"test", "DEPENDENCIES":[], "BLOCKERS":[],
            "COMPLETION_CRITERIA":"verified", "D4_EVIDENCE":[],
            "LAST_UPDATE":"old", "NEXT_ACTION":"verify"
        }
        self.work.write_text(json.dumps({"TASKS":[task], "UPDATED_AT":"old"}))
        self.action.write_text(json.dumps({"ACTIONS":[], "UPDATED_AT":"old"}))
        self.original_checkpoint = {
            "mainline":"W7TP", "current_goal":"preserve goal",
            "current_state":"existing", "last_decision":"existing receipt",
            "open_tasks":[], "next_action":"stale", "d8":"HOLD",
            "hold_reason":"preserve authority"
        }
        self.checkpoint.write_text(json.dumps(self.original_checkpoint))
        self.root_patch = patch.object(runner, "PROJECT_ROOT", self.root)
        self.root_patch.start()

    def tearDown(self):
        self.root_patch.stop()
        self.tmp.cleanup()

    def test_final_run_updates_ledger_and_checkpoint_without_authority_change(self):
        run = self.root / "runs" / "test"
        runner.write_state(run, {"run_id":"test", "task_id":"T-020", "state":"LANDED_SOURCE_VERIFIED", "finished_at":"today"})
        result = json.loads((run/"state.json").read_text())
        self.assertEqual(result["continuity"]["state"], "RECORDED")
        tasks=json.loads(self.work.read_text())["TASKS"]
        self.assertEqual(tasks[0]["STATE"],"DOING")
        self.assertEqual(len(tasks[0]["D4_EVIDENCE"]),1)
        cp=json.loads(self.checkpoint.read_text())
        for key in ["d8","hold_reason","current_goal","current_state","last_decision"]:
            self.assertEqual(cp[key],self.original_checkpoint[key])
        self.assertEqual(cp["open_tasks"],["T-020"])
        self.assertEqual(cp["next_action"],"verify")

    def test_final_projection_is_idempotent(self):
        payload={"run_id":"same", "task_id":"T-020", "state":"HOLD", "finished_at":"today"}
        runner.write_state(self.root/"runs"/"same",payload)
        runner.write_state(self.root/"runs"/"same",payload)
        self.assertEqual(len(json.loads(self.work.read_text())["TASKS"][0]["D4_EVIDENCE"]),1)

    def test_unknown_task_is_visible_and_does_not_fabricate_task(self):
        with contextlib.redirect_stderr(io.StringIO()) as warnings:
            runner.write_state(self.root/"runs"/"missing",{"task_id":"MISSING","state":"DONE","finished_at":"today"})
        result=json.loads((self.root/"runs"/"missing"/"state.json").read_text())
        self.assertEqual(result["state"],"DONE")
        self.assertEqual(result["continuity"]["reason"],"TASK_NOT_FOUND")
        self.assertIn("CONTINUITY_PENDING",warnings.getvalue())
        self.assertEqual(len(json.loads(self.work.read_text())["TASKS"]),1)

    def test_closed_held_cancelled_tasks_are_preserved(self):
        for state in ["DONE","HOLD","CANCELLED"]:
            data=json.loads(self.work.read_text());data["TASKS"][0]["STATE"]=state
            self.work.write_text(json.dumps(data))
            before=self.work.read_bytes()
            result=runner._append_work_evidence("T-020",{"STATE":"DONE"},next_action="resume")
            self.assertEqual(result["reason"],"TASK_PROTECTED")
            self.assertEqual(self.work.read_bytes(),before)

    def test_broken_checkpoint_retains_run_and_marks_partial_persistence(self):
        self.checkpoint.write_text("invalid")
        with contextlib.redirect_stderr(io.StringIO()):
            runner.write_state(self.root/"runs"/"broken",{"task_id":"T-020","state":"DONE","finished_at":"today"})
        result=json.loads((self.root/"runs"/"broken"/"state.json").read_text())
        self.assertEqual(result["continuity"]["reason"],"PERSISTENCE_ERROR")
        self.assertEqual(len(json.loads(self.work.read_text())["TASKS"][0]["D4_EVIDENCE"]),1)

    def test_running_state_does_not_project_completion(self):
        runner.write_state(self.root/"runs"/"running",{"task_id":"T-020","state":"RUNNING"})
        self.assertEqual(json.loads(self.work.read_text())["TASKS"][0]["D4_EVIDENCE"],[])

    def test_checkpoint_sync_does_not_change_action_ledger(self):
        before=self.action.read_bytes()
        sync_checkpoint_evidence(self.work,self.action,self.checkpoint)
        self.assertEqual(self.action.read_bytes(),before)

if __name__ == "__main__":
    unittest.main()
