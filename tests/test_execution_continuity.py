#!/usr/bin/env python3
"""Tests for persistent execution continuity and safe resume semantics."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core.execution_continuity import ActionLedger, build_idempotency_key
from core.intent_continuity import apply_conversation_event


class ExecutionContinuityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.action_path = root / "ACTION_LEDGER.json"
        self.work_path = root / "WORK_LEDGER.json"
        self.work_path.write_text(
            json.dumps(
                {
                    "LEDGER_VERSION": "1.0",
                    "MAINLINE": "W7TP / 8D ADI",
                    "UPDATED_AT": "2026-09-25T00:00:00+00:00",
                    "TASKS": [],
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _begin(self, action_id: str = "A-001") -> tuple[ActionLedger, str]:
        ledger = ActionLedger(self.action_path)
        key = build_idempotency_key(
            task_id="T-001",
            target_coordinate="MSI/ChatGPT/RemoteToolSession",
            operation="resume-stream",
            intent_hash="abc",
        )
        ledger.begin_action(
            action_id=action_id,
            task_id="T-001",
            turn_id="TURN-1",
            process_id=43673,
            target_coordinate="MSI/ChatGPT/RemoteToolSession",
            tool="Remote Desktop Commander",
            idempotency_key=key,
        )
        return ledger, key

    def test_begin_action_persists_after_reopen(self) -> None:
        self._begin()
        reopened = ActionLedger(self.action_path)
        self.assertEqual(reopened._action("A-001")["STATE"], "RUNNING")

    def test_duplicate_active_idempotency_key_is_rejected(self) -> None:
        ledger, key = self._begin()
        with self.assertRaises(ValueError):
            ledger.begin_action(
                action_id="A-002",
                task_id="T-001",
                turn_id="TURN-2",
                process_id=999,
                target_coordinate="MSI/ChatGPT/RemoteToolSession",
                tool="Remote Desktop Commander",
                idempotency_key=key,
            )

    def test_interrupted_action_is_resumable(self) -> None:
        ledger, _ = self._begin()
        ledger.mark_interrupted(
            "A-001",
            error="RESUME_STREAM_UNAVAILABLE",
            last_confirmed_effect={"network": "PASS"},
            last_tool_effect={"process": "missing"},
            resume_from="CHECK_ACTUAL_EFFECT_BEFORE_RESUME",
        )
        resumed = ledger.get_resumable_action()
        self.assertIsNotNone(resumed)
        self.assertEqual(resumed["ACTION_ID"], "A-001")
        self.assertEqual(resumed["STATE"], "INTERRUPTED")

    def test_resume_changes_process_without_restarting_identity(self) -> None:
        ledger, _ = self._begin()
        ledger.mark_interrupted(
            "A-001",
            error="stream lost",
            resume_from="VERIFY_EFFECT",
        )
        result = ledger.resume_action(
            "A-001", new_process_id=50000, resume_from="VERIFY_EFFECT"
        )
        self.assertEqual(result["ACTION_ID"], "A-001")
        self.assertEqual(result["PROCESS_ID"], 50000)
        self.assertEqual(result["STATE"], "RESUMED")

    def test_missing_process_never_means_rerun(self) -> None:
        ledger, _ = self._begin()
        result = ledger.recovery_decision(
            "A-001",
            process_exists=False,
            stream_available=False,
            effect_confirmed=False,
        )
        self.assertEqual(result["STATE"], "INTERRUPTED_UNKNOWN_EFFECT")
        self.assertEqual(result["ACTION"], "CHECK_ACTUAL_EFFECT_BEFORE_RESUME")

    def test_confirmed_effect_completes_without_rerun(self) -> None:
        ledger, _ = self._begin()
        result = ledger.recovery_decision(
            "A-001",
            process_exists=False,
            stream_available=False,
            effect_confirmed=True,
        )
        self.assertEqual(result["ACTION"], "VERIFY_AND_COMPLETE")

    def test_completed_action_is_not_resumable(self) -> None:
        ledger, _ = self._begin()
        ledger.complete_action("A-001", confirmed_effect={"result": "PASS"})
        self.assertIsNone(ledger.get_resumable_action())
        self.assertEqual(ledger.list_open_actions(), [])

    def test_conversation_event_action_flow(self) -> None:
        key = build_idempotency_key(
            task_id="T-001",
            target_coordinate="taiji01/service",
            operation="write",
        )
        started = apply_conversation_event(
            {
                "type": "ACTION_STARTED",
                "action": {
                    "action_id": "A-EVENT",
                    "task_id": "T-001",
                    "turn_id": "TURN-X",
                    "process_id": 123,
                    "target_coordinate": "taiji01/service",
                    "tool": "shell",
                    "idempotency_key": key,
                },
            },
            self.work_path,
            self.action_path,
        )
        self.assertEqual(started["STATE"], "RUNNING")

        interrupted = apply_conversation_event(
            {
                "type": "ACTION_INTERRUPTED",
                "ACTION_ID": "A-EVENT",
                "error": "stream lost",
                "last_confirmed_effect": {"phase": "precheck"},
                "resume_from": "VERIFY_EFFECT",
            },
            self.work_path,
            self.action_path,
        )
        self.assertEqual(interrupted["STATE"], "INTERRUPTED")

        resumed = apply_conversation_event(
            {
                "type": "ACTION_RESUMED",
                "ACTION_ID": "A-EVENT",
                "new_process_id": 456,
                "resume_from": "VERIFY_EFFECT",
            },
            self.work_path,
            self.action_path,
        )
        self.assertEqual(resumed["STATE"], "RESUMED")

        done = apply_conversation_event(
            {
                "type": "ACTION_COMPLETED",
                "ACTION_ID": "A-EVENT",
                "confirmed_effect": {"phase": "verified"},
            },
            self.work_path,
            self.action_path,
        )
        self.assertEqual(done["STATE"], "DONE")


if __name__ == "__main__":
    unittest.main()
