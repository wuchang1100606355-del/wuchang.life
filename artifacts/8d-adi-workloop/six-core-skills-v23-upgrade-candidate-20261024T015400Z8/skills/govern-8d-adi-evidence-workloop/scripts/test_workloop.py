#!/usr/bin/env python3
"""Regression and adversarial tests for the 8D ADI workloop validator."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
INIT = SCRIPT_DIR / "init_workloop.py"
VALIDATE = SCRIPT_DIR / "validate_workloop.py"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_json(command: list[str]) -> tuple[int, dict[str, object]]:
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    return completed.returncode, json.loads(completed.stdout)


class WorkloopValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name)
        command = [
            sys.executable,
            str(INIT),
            "--project-root",
            str(self.project),
            "--run-id",
            "test-run-001",
            "--title",
            "Deterministic candidate",
            "--intent",
            "Produce one evidence-bound candidate result.",
        ]
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.run_dir = self.project / "artifacts" / "8d-adi-workloop" / "test-run-001"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def validate(self) -> tuple[int, dict[str, object]]:
        return run_json([sys.executable, str(VALIDATE), str(self.run_dir)])

    def promote_to_done_candidate(self) -> None:
        evidence_dir = self.run_dir / "evidence"
        (evidence_dir / "ac-1.txt").write_text(
            "Observable product result verified.\n", encoding="utf-8"
        )
        (evidence_dir / "independent.txt").write_text(
            "Fresh independent fixture verified the product output.\n", encoding="utf-8"
        )

        envelope_path = self.run_dir / "intent-envelope.json"
        envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
        envelope["lifecycle_state"] = "CANDIDATE_FOR_TOTAL_FIELD_REVIEW"
        envelope["red_team"] = {
            "RED_TEAM_PRE_DEFINITION": "PASS_TEST_FIXTURE",
            "RED_TEAM_PRE_ACTIVATION": "PASS_TEST_FIXTURE",
            "RED_TEAM_POST_OPERATION": "PASS_TEST_FIXTURE",
        }
        envelope_path.write_text(
            json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        order_path = self.run_dir / "order.md"
        order_text = order_path.read_text(encoding="utf-8")
        order_text = order_text.replace("Lifecycle: DRAFT_LOCAL", "Lifecycle: CANDIDATE_FOR_TOTAL_FIELD_REVIEW")
        order_text = order_text.replace("Frozen: NOT_FROZEN", "Frozen: TEST_LOGICAL_TIME")
        order_path.write_text(order_text, encoding="utf-8")
        order_hash = sha256_file(order_path)

        frozen_event = {
            "event_id": "evt-0002",
            "logical_time": "2026-08-23T01:00:00+08:00",
            "event_type": "ORDER_FROZEN",
            "status": "CLOSED",
            "evidence_label": "CANDIDATE",
            "observation_status": "DECLARED_ONLY",
            "source_ref": "artifacts/8d-adi-workloop/test-run-001/order.md",
            "source_sha256": order_hash,
            "summary": "Test fixture froze the order.",
            "authority_state": "CANDIDATE_FOR_TOTAL_FIELD_REVIEW",
            "supersedes": [],
        }
        with (self.run_dir / "decisions.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(frozen_event, ensure_ascii=False) + "\n")

        closeout = """# 8D ADI Closeout: Deterministic candidate

Status: DONE
Run-ID: test-run-001

## Acceptance
- [PASS] AC-1: observable result exists | evidence: evidence/ac-1.txt

## Independent functional verification
- Independent functional verification: fresh fixture outside mutable output | evidence: evidence/independent.txt

## Protected unchanged state
- ADI, canonical pointers, live services, databases, identity, Seat, and member data were not changed.

## Total Field
- Decision: NOT_REVIEWED
"""
        (self.run_dir / "closeout.md").write_text(closeout, encoding="utf-8")

    def test_scaffold_is_valid_draft_not_done(self) -> None:
        code, report = self.validate()
        self.assertEqual(code, 0, report)
        self.assertEqual(report["result"], "PASS_WORKLOOP_DRAFT_VALID")
        self.assertFalse(report["canonical_mutation"])

    def test_complete_candidate_done_passes(self) -> None:
        self.promote_to_done_candidate()
        code, report = self.validate()
        self.assertEqual(code, 0, report)
        self.assertEqual(report["result"], "PASS_WORKLOOP_VALID")
        self.assertEqual(report["total_field_decision"], "NOT_REVIEWED")

    def test_missing_acceptance_evidence_rejects_done(self) -> None:
        self.promote_to_done_candidate()
        (self.run_dir / "evidence" / "ac-1.txt").unlink()
        code, report = self.validate()
        self.assertEqual(code, 2)
        self.assertEqual(report["result"], "HOLD_WORKLOOP_INVALID")
        self.assertTrue(
            any(str(item).startswith("DONE_ACCEPTANCE_EVIDENCE_NOT_FOUND") for item in report["errors"])
        )

    def test_self_asserted_total_field_receipt_is_rejected(self) -> None:
        envelope_path = self.run_dir / "intent-envelope.json"
        envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
        envelope["d1_d8"]["D8"]["value"]["total_field_decision"] = "PASS"
        envelope_path.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
        code, report = self.validate()
        self.assertEqual(code, 2)
        self.assertIn("TOTAL_FIELD_RECEIPT_CANNOT_BE_SELF_ASSERTED", report["errors"])

    def test_w7tp_claim_without_protocol_proof_is_rejected(self) -> None:
        envelope_path = self.run_dir / "intent-envelope.json"
        envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
        envelope["d1_d8"]["D6"]["value"]["claimed"] = True
        envelope_path.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
        code, report = self.validate()
        self.assertEqual(code, 2)
        self.assertIn("D6_W7TP_CLAIM_REQUIRES_SEPARATE_PROTOCOL_PROOF", report["errors"])


if __name__ == "__main__":
    unittest.main()
