#!/usr/bin/env python3
"""Tests for D2 persistent Work Ledger and conversation checkpoint."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core.intent_continuity import (
    apply_conversation_event,
    extract_conversation_event_candidates,
    load_checkpoint,
    project_verified_conversation_candidate,
    refresh_checkpoint_from_ledger,
)
from core.work_ledger import WorkLedger


def make_task(task_id: str, *, state: str = "TODO", priority: str = "P1") -> dict:
    return {
        "TASK_ID": task_id,
        "PARENT_INTENT": "test intent",
        "TITLE": f"Task {task_id}",
        "DESCRIPTION": "test",
        "STATE": state,
        "PRIORITY": priority,
        "D3_COORDINATE": "test/node",
        "DEPENDENCIES": [],
        "BLOCKERS": [],
        "COMPLETION_CRITERIA": "verified",
        "D4_EVIDENCE": [],
        "LAST_UPDATE": "2026-09-25T00:00:00+00:00",
        "NEXT_ACTION": f"next {task_id}",
    }


class WorkLedgerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.ledger_path = root / "WORK_LEDGER.json"
        self.checkpoint_path = root / "CHECKPOINT.json"
        payload = {
            "LEDGER_VERSION": "1.0",
            "MAINLINE": "W7TP / 8D ADI",
            "UPDATED_AT": "2026-09-25T00:00:00+00:00",
            "TASKS": [make_task("T-001", state="DOING", priority="P0")],
        }
        self.ledger_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_create_task_persists_after_reopen(self) -> None:
        ledger = WorkLedger(self.ledger_path)
        ledger.create_task(make_task("T-002"))
        reopened = WorkLedger(self.ledger_path)
        self.assertEqual(
            {task["TASK_ID"] for task in reopened.data["TASKS"]},
            {"T-001", "T-002"},
        )

    def test_update_task(self) -> None:
        ledger = WorkLedger(self.ledger_path)
        changed = ledger.update_task("T-001", DESCRIPTION="changed")
        self.assertEqual(changed["DESCRIPTION"], "changed")
        self.assertEqual(WorkLedger(self.ledger_path)._task("T-001")["DESCRIPTION"], "changed")

    def test_complete_task_records_evidence(self) -> None:
        ledger = WorkLedger(self.ledger_path)
        result = ledger.complete_task("T-001", {"RESULT": "PASS"})
        self.assertEqual(result["STATE"], "DONE")
        self.assertEqual(result["D4_EVIDENCE"], [{"RESULT": "PASS"}])
        self.assertEqual(result["NEXT_ACTION"], "NONE")

    def test_block_task(self) -> None:
        ledger = WorkLedger(self.ledger_path)
        result = ledger.block_task("T-001", "WAIT_FOR_EVIDENCE")
        self.assertEqual(result["STATE"], "BLOCKED")
        self.assertIn("WAIT_FOR_EVIDENCE", result["BLOCKERS"])
    def test_list_open_tasks_excludes_done_and_cancelled(self) -> None:
        ledger = WorkLedger(self.ledger_path)
        ledger.create_task(make_task("T-002"))
        ledger.create_task(make_task("T-003"))
        ledger.update_task("T-002", STATE="DONE")
        ledger.update_task("T-003", STATE="CANCELLED")
        ids = {task["TASK_ID"] for task in ledger.list_open_tasks()}
        self.assertEqual(ids, {"T-001"})

    def test_get_next_action_is_unique(self) -> None:
        ledger = WorkLedger(self.ledger_path)
        ledger.create_task(make_task("T-002", priority="P0"))
        ledger.create_task(make_task("T-003", priority="P1"))
        result = ledger.get_next_action()
        self.assertEqual(result, {"TASK_ID": "T-001", "NEXT_ACTION": "next T-001"})

    def test_closed_task_is_sealed_and_generic_update_cannot_reopen(self) -> None:
        ledger = WorkLedger(self.ledger_path)
        closed = ledger.complete_task(
            "T-001",
            {"RESULT": "PASS"},
            closed_head="abc123",
        )
        self.assertEqual(closed["STATE"], "DONE")
        self.assertEqual(closed["NEXT_ACTION"], "NONE")
        self.assertEqual(closed["CLOSED_HEAD"], "abc123")
        self.assertIn("COMPLETION_SEAL", closed)
        with self.assertRaisesRegex(ValueError, "closed task requires explicit reopen_task"):
            ledger.update_task("T-001", STATE="DOING", NEXT_ACTION="scope drift")

    def test_explicit_reopen_requires_reason_authority_and_next_action(self) -> None:
        ledger = WorkLedger(self.ledger_path)
        ledger.complete_task("T-001", closed_head="abc123")
        with self.assertRaises(ValueError):
            ledger.reopen_task(
                "T-001",
                reason="",
                authority_ref="founder:test",
                next_action="continue",
            )
        reopened = ledger.reopen_task(
            "T-001",
            reason="new founder-scoped requirement",
            authority_ref="founder:test",
            next_action="continue explicit reopened scope",
        )
        self.assertEqual(reopened["STATE"], "TODO")
        self.assertEqual(reopened["NEXT_ACTION"], "continue explicit reopened scope")
        self.assertNotIn("COMPLETION_SEAL", reopened)
        self.assertEqual(len(reopened["REOPEN_HISTORY"]), 1)

    def test_legacy_done_task_can_only_reopen_explicitly(self) -> None:
        ledger = WorkLedger(self.ledger_path)
        legacy = ledger._task("T-001")
        legacy["STATE"] = "DONE"
        legacy["NEXT_ACTION"] = "NONE"
        ledger._save()
        reopened = ledger.reopen_task(
            "T-001",
            reason="explicit legacy correction",
            authority_ref="founder:test",
            next_action="review legacy task",
        )
        self.assertEqual(reopened["STATE"], "TODO")
        self.assertTrue(
            reopened["REOPEN_HISTORY"][0]["PREVIOUS_COMPLETION_SEAL"]["LEGACY_UNSEALED"]
        )

    def test_p0_todo_preempts_unverified_p1_doing(self) -> None:
        ledger = WorkLedger(self.ledger_path)
        ledger.update_task("T-001", PRIORITY="P1")
        ledger.create_task(make_task("T-000", state="TODO", priority="P0"))
        result = ledger.get_next_action()
        self.assertEqual(result, {"TASK_ID": "T-000", "NEXT_ACTION": "next T-000"})

    def test_verified_active_task_may_continue_before_higher_priority_todo(self) -> None:
        ledger = WorkLedger(self.ledger_path)
        ledger.update_task("T-001", PRIORITY="P1")
        ledger.create_task(make_task("T-000", state="TODO", priority="P0"))
        result = ledger.get_next_action({"T-001"})
        self.assertEqual(result, {"TASK_ID": "T-001", "NEXT_ACTION": "next T-001"})

    def test_checkpoint_round_trip(self) -> None:
        payload = refresh_checkpoint_from_ledger(
            self.ledger_path,
            self.checkpoint_path,
            current_goal="persist work",
            current_state="TESTING",
            last_decision="verify",
            d8="HOLD",
            hold_reason="TEST_ONLY",
        )
        loaded = load_checkpoint(self.checkpoint_path)
        self.assertEqual(loaded["open_tasks"], ["T-001"])
        self.assertEqual(loaded["next_action"], "next T-001")
        self.assertEqual(payload["d8"], "HOLD")
    def test_structured_event_updates_ledger(self) -> None:
        result = apply_conversation_event(
            {
                "type": "TASK_UPDATED",
                "TASK_ID": "T-001",
                "changes": {"NEXT_ACTION": "new next"},
            },
            self.ledger_path,
        )
        self.assertEqual(result["NEXT_ACTION"], "new next")
        self.assertEqual(
            WorkLedger(self.ledger_path)._task("T-001")["NEXT_ACTION"],
            "new next",
        )

    def test_extract_conversation_candidates_is_candidate_only(self) -> None:
        envelope = extract_conversation_event_candidates(
            "T-001 Example task\nSTATE=DOING\nNEXT_ACTION=continue\nRESULT=PASS_PARTIAL",
            source_coordinate="chat:test",
        )
        self.assertTrue(envelope["candidate_only"])
        self.assertFalse(envelope["authority_granted"])
        self.assertTrue(envelope["requires_total_field_verify"])
        kinds = [event["kind"] for event in envelope["events"]]
        self.assertEqual(kinds, ["TASK", "STATE_CHANGE", "NEXT_ACTION", "EVIDENCE"])
        self.assertTrue(all(event["task_id"] == "T-001" for event in envelope["events"]))
        self.assertTrue(all(event["authority_granted"] is False for event in envelope["events"]))

    def test_extract_hold_and_blocker_constraints(self) -> None:
        envelope = extract_conversation_event_candidates(
            "T-001 Example task\nSTATE=HOLD\nBLOCKER=PAUSED_BY_FOUNDER\n不得自行恢復或重建候選",
        )
        kinds = [event["kind"] for event in envelope["events"]]
        self.assertIn("STATE_CHANGE", kinds)
        self.assertIn("BLOCKER", kinds)
        self.assertIn("HOLD", kinds)

    def test_non_conflict_phrase_does_not_create_conflict_event(self) -> None:
        envelope = extract_conversation_event_candidates(
            "T-001 Example task\n支線合併原則：\nGit clean merge（無衝突合併）不等於允許合併。",
        )
        conflicts = [event for event in envelope["events"] if event["kind"] == "CONFLICT"]
        self.assertEqual(conflicts, [])
        intent = next(event for event in envelope["events"] if event["kind"] == "INTENT")
        self.assertIsNone(intent["task_id"])

    def test_unverified_candidate_cannot_project_to_ledger_event(self) -> None:
        envelope = extract_conversation_event_candidates(
            "T-001 Example task\nNEXT_ACTION=verified next",
        )
        candidate = next(event for event in envelope["events"] if event["kind"] == "NEXT_ACTION")
        with self.assertRaisesRegex(ValueError, "not verified by Total Field"):
            project_verified_conversation_candidate(
                candidate,
                {"final_decision": "HOLD", "fixed_point_status": "REACHED"},
                self.ledger_path,
            )

    def test_verified_candidate_projects_updates_ledger_and_checkpoint(self) -> None:
        envelope = extract_conversation_event_candidates(
            "T-001 Example task\nNEXT_ACTION=verified next",
            source_coordinate="chat:test",
        )
        candidate = next(event for event in envelope["events"] if event["kind"] == "NEXT_ACTION")
        event = project_verified_conversation_candidate(
            candidate,
            {"final_decision": "ALLOW", "fixed_point_status": "REACHED"},
            self.ledger_path,
        )
        self.assertIsNotNone(event)
        result = apply_conversation_event(event, self.ledger_path)
        self.assertEqual(result["NEXT_ACTION"], "verified next")
        checkpoint = refresh_checkpoint_from_ledger(
            self.ledger_path,
            self.checkpoint_path,
            current_goal="event extraction",
            current_state="VERIFIED",
            last_decision="apply verified candidate",
            d8="PASS",
        )
        self.assertEqual(checkpoint["next_action"], "verified next")


if __name__ == "__main__":
    unittest.main()
