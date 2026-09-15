#!/usr/bin/env python3
"""Tests for the fail-closed Founder device-approval candidate entrypoint."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from tools.total_field.w7tp_founder_device_approval_candidate import (
    CANDIDATE_STATE,
    evaluate_founder_device_approval,
)
from tools.total_field.w7tp_intent_field_suite.canonical_hash import (
    canonical_sha256,
)


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "tools/total_field/w7tp_founder_device_approval_candidate.py"
SESSION_SCHEMA = (
    ROOT / "schemas/xiaoj_member_bound_developer_seat_candidate.schema.json"
)


class FounderDeviceApprovalCandidateTest(unittest.TestCase):
    def request(self) -> dict:
        return {
            "founder_identity_evidence_ref": "evidence_ref:founder-identity",
            "device_ref": "device_ref:founder-msi",
            "device_evidence_sha256": "a" * 64,
            "explicit_human_approval": True,
            "approval_command_ref": "command_ref:approve-founder-device",
            "current_epoch": 100,
            "expires_at_epoch": 200,
        }

    def test_candidate_is_deterministic_and_creates_no_formal_authority(self) -> None:
        request = self.request()
        first = evaluate_founder_device_approval(request)
        second = evaluate_founder_device_approval(dict(reversed(list(request.items()))))

        self.assertEqual(first, second)
        self.assertEqual(first["state"], CANDIDATE_STATE)
        self.assertTrue(first["candidate_only"])
        self.assertFalse(first["formal_authority_created"])
        self.assertTrue(first["requires_total_field_verify"])
        self.assertEqual(
            first["device_or_channel_binding"]["binding_hash"],
            canonical_sha256(request),
        )
        receipt = first["approval_receipt_candidate"]
        self.assertEqual(receipt["state"], "CANDIDATE_ONLY")
        self.assertFalse(receipt["formal_authority_created"])
        self.assertTrue(receipt["requires_total_field_verify"])

    def test_human_approval_false_fails_closed(self) -> None:
        request = self.request()
        request["explicit_human_approval"] = False

        result = evaluate_founder_device_approval(request)

        self.assertEqual(result["state"], "BLOCK_EXPLICIT_HUMAN_APPROVAL_REQUIRED")
        self.assertIsNone(result["device_or_channel_binding"])
        self.assertIsNone(result["approval_receipt_candidate"])
        self.assertFalse(result["formal_authority_created"])

    def test_expired_approval_fails_closed(self) -> None:
        for expires_at_epoch in (99, 100):
            with self.subTest(expires_at_epoch=expires_at_epoch):
                request = self.request()
                request["expires_at_epoch"] = expires_at_epoch
                result = evaluate_founder_device_approval(request)
                self.assertEqual(result["state"], "BLOCK_DEVICE_APPROVAL_EXPIRED")
                self.assertIsNone(result["device_or_channel_binding"])

    def test_all_required_input_guards_fail_closed(self) -> None:
        cases = {
            "missing founder evidence ref": (
                "founder_identity_evidence_ref",
                "",
                "BLOCK_FOUNDER_IDENTITY_EVIDENCE_REF_REQUIRED",
            ),
            "invalid device ref": (
                "device_ref",
                "founder-msi",
                "BLOCK_DEVICE_REF_INVALID",
            ),
            "invalid device evidence sha256": (
                "device_evidence_sha256",
                "a" * 63,
                "BLOCK_DEVICE_EVIDENCE_SHA256_INVALID",
            ),
            "missing approval command ref": (
                "approval_command_ref",
                "",
                "BLOCK_APPROVAL_COMMAND_REF_REQUIRED",
            ),
        }
        for name, (field, value, state) in cases.items():
            with self.subTest(name=name):
                request = self.request()
                request[field] = value
                result = evaluate_founder_device_approval(request)
                self.assertEqual(result["state"], state)
                self.assertTrue(result["candidate_only"])
                self.assertFalse(result["formal_authority_created"])

    def test_request_rejects_missing_or_extra_fields(self) -> None:
        missing = self.request()
        missing.pop("approval_command_ref")
        extra = self.request()
        extra["session_activation"] = True

        for request in (missing, extra):
            with self.subTest(fields=sorted(request)):
                result = evaluate_founder_device_approval(request)
                self.assertEqual(
                    result["state"],
                    "BLOCK_DEVICE_APPROVAL_REQUEST_FIELDS_INVALID",
                )
                self.assertFalse(result["formal_authority_created"])

    def test_device_binding_validates_against_existing_session_schema(self) -> None:
        schema = json.loads(SESSION_SCHEMA.read_text(encoding="utf-8"))
        binding_schema = dict(schema["properties"]["device_or_channel_binding"])
        binding_schema["$defs"] = schema["$defs"]
        result = evaluate_founder_device_approval(self.request())
        binding = result["device_or_channel_binding"]

        Draft202012Validator(binding_schema).validate(binding)
        self.assertEqual(binding["binding_type"], "DEVICE")
        self.assertEqual(binding["binding_ref"], self.request()["device_ref"])

    def test_stdin_entrypoint_emits_candidate_only_json(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ENTRYPOINT)],
            cwd=ROOT,
            input=json.dumps(self.request()),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["state"], CANDIDATE_STATE)
        self.assertTrue(result["candidate_only"])
        self.assertFalse(result["formal_authority_created"])


if __name__ == "__main__":
    unittest.main()
