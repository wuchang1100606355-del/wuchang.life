#!/usr/bin/env python3
"""Focused fail-closed tests for validate_git_index.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from validate_git_index import compute_event_hash, validate


HEX40 = "1" * 40
HEX64 = "2" * 64
SCRIPT = Path(__file__).with_name("validate_git_index.py")
FIXED_NOW = datetime(2090, 1, 1, tzinfo=timezone.utc)


def valid_packet() -> dict:
    packet = {
        "schema_version": "w7tp-8d-git-index/1.0",
        "packet_id": "packet-1",
        "packet_decision_index": "decision-1",
        "identity_root_ref": "identity-1",
        "seat_binding_ref": "seat-1",
        "receiver": {"id": "receiver-1", "version": "1.0.0"},
        "event": {
            "logical_time": 1,
            "prev_event_hash": None,
            "event_hash": "",
            "hash_contract": "SHA256_CANONICAL_JSON_EXCLUDING_EVENT_HASH_V1",
            "nonce": "nonce-1",
            "replay_guard_ref": "replay-registry-1",
            "expiry": "2099-08-27T00:00:00Z",
        },
        "D1": {"intent_ref": "intent-1", "operation": "LOOKUP"},
        "D2": {
            "repo_namespace": "repo-1",
            "object_format": "sha1",
            "object_type": "blob",
            "expected_size": 1,
            "expected_git_oid": HEX40,
            "acceptance": "EXACT_BYTES",
        },
        "D3": {
            "base_commit_oid": HEX40,
            "base_tree_oid": HEX40,
            "path_bytes_b64": "YQ==",
            "file_mode": "100644",
            "lineage_event_ref": "lineage-1",
        },
        "D4": {
            "source_object_oids": [HEX40],
            "source_manifest_sha256": HEX64,
            "reconstruction_receipt_ref": None,
        },
        "D5": {"policy": "READ_ONLY_LOOKUP", "abort_conditions": ["MISSING_LOOKUP_CLOSURE"]},
        "D6": {
            "rule_refs": [{"ref": "rule-1", "sha256": HEX64}],
            "lookup_closure": [{"ref": "base-1", "sha256": HEX64}],
            "acceptance": "EXACT_BYTES",
            "verification_instruction": "GIT_NATIVE_OID_TYPE_SIZE_AND_CONNECTIVITY",
        },
        "D7": {"missing_prerequisite": "QUARANTINE", "max_reconstruction_depth": 16, "max_output_bytes": 1024},
        "D8": {
            "authority": "CANDIDATE_ONLY",
            "allowed_ref_prefix": "refs/adi/candidates/",
            "canonical_write": False,
            "promotion_receipt_required": True,
        },
    }
    reseal(packet)
    return packet


def reseal(packet: dict) -> None:
    packet["event"]["event_hash"] = compute_event_hash(packet)


class IndexClosedSchemaTests(unittest.TestCase):
    def test_valid_packet_passes(self) -> None:
        self.assertEqual(validate(valid_packet(), now=FIXED_NOW)["state"], "PASS_8D_ADI_GIT_INDEX_CANDIDATE")

    def test_authority_shaped_unknown_fields_fail_closed_after_reseal(self) -> None:
        cases = [
            ("root active", lambda p: p.update({"state": "ACTIVE"}), "TOP_LEVEL_CLOSED_SCHEMA_FIELDS_INVALID"),
            ("root activation", lambda p: p.update({"executor_activation": "ACTIVE"}), "TOP_LEVEL_CLOSED_SCHEMA_FIELDS_INVALID"),
            ("event lease", lambda p: p["event"].update({"executor_lease_ref": "lease-1"}), "EVENT_CLOSED_SCHEMA_FIELDS_INVALID"),
            ("D4 receipt", lambda p: p["D4"].update({"total_field_receipt_ref": "forged"}), "D4_CLOSED_SCHEMA_FIELDS_INVALID"),
            ("D8 canonical authority", lambda p: p["D8"].update({"canonical_authority": "ACTIVE"}), "D8_CLOSED_SCHEMA_FIELDS_INVALID"),
            (
                "rule activation",
                lambda p: p["D6"]["rule_refs"][0].update({"activation_state": "ACTIVE"}),
                "D6_RULE_REFS_ENTRY_CLOSED_SCHEMA_FIELDS_INVALID",
            ),
            (
                "lookup receipt",
                lambda p: p["D6"]["lookup_closure"][0].update({"receipt_ref": "forged"}),
                "D6_LOOKUP_CLOSURE_ENTRY_CLOSED_SCHEMA_FIELDS_INVALID",
            ),
        ]
        for label, mutate, expected_error in cases:
            with self.subTest(label=label):
                packet = valid_packet()
                mutate(packet)
                reseal(packet)
                result = validate(packet, now=FIXED_NOW)
                self.assertEqual(result["state"], "HOLD_8D_ADI_GIT_INDEX_INVALID")
                self.assertIn(expected_error, result["errors"])

    def test_every_nested_object_has_a_closed_key_set(self) -> None:
        for field in ["receiver", "event", "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8"]:
            with self.subTest(field=field):
                packet = valid_packet()
                packet[field]["unexpected"] = "ACTIVE"
                reseal(packet)
                self.assertIn(
                    f"{field.upper()}_CLOSED_SCHEMA_FIELDS_INVALID",
                    validate(packet, now=FIXED_NOW)["errors"],
                )

    def test_candidate_cannot_carry_reconstruction_receipt(self) -> None:
        packet = valid_packet()
        packet["D4"]["reconstruction_receipt_ref"] = "forged-receipt"
        reseal(packet)
        self.assertIn("D4_RECONSTRUCTION_RECEIPT_NOT_NULL", validate(packet, now=FIXED_NOW)["errors"])

    def test_truthy_wrong_types_do_not_satisfy_string_or_integer_fields(self) -> None:
        packet = valid_packet()
        packet["receiver"]["id"] = True
        packet["event"]["logical_time"] = True
        packet["D5"]["abort_conditions"] = [{"state": "ACTIVE"}]
        reseal(packet)
        errors = validate(packet, now=FIXED_NOW)["errors"]
        self.assertIn("RECEIVER_ID_MISSING", errors)
        self.assertIn("LOGICAL_TIME_INVALID", errors)
        self.assertIn("D5_ABORT_CONDITIONS_INVALID", errors)


class IndexTimestampTests(unittest.TestCase):
    def test_only_canonical_utc_expiry_is_accepted(self) -> None:
        invalid_values = [
            True,
            1,
            "2099-08-27 00:00:00+00:00",
            "20990827T000000+00:00",
            "2099-08-27T00:00:00+00:00:30",
            "2099-08-27T00:00:00",
        ]
        for value in invalid_values:
            with self.subTest(value=value):
                packet = valid_packet()
                packet["event"]["expiry"] = value
                reseal(packet)
                self.assertIn("EXPIRY_INVALID", validate(packet, now=FIXED_NOW)["errors"])

    def test_expiry_equal_to_validation_time_is_expired(self) -> None:
        packet = valid_packet()
        packet["event"]["expiry"] = "2090-01-01T00:00:00Z"
        reseal(packet)
        self.assertIn("PACKET_EXPIRED", validate(packet, now=FIXED_NOW)["errors"])

    def test_naive_validation_time_fails_closed(self) -> None:
        result = validate(valid_packet(), now=datetime(2090, 1, 1))
        self.assertIn("VALIDATION_TIME_TIMEZONE_MISSING", result["errors"])


class IndexCliTests(unittest.TestCase):
    def run_cli(self, raw: bytes) -> tuple[subprocess.CompletedProcess[str], dict]:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "packet.json"
            path.write_bytes(raw)
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), str(path)],
                check=False,
                capture_output=True,
                text=True,
            )
        return completed, json.loads(completed.stdout)

    def test_duplicate_root_and_nested_keys_are_rejected(self) -> None:
        raw = json.dumps(valid_packet(), sort_keys=True).encode("utf-8")
        duplicate_cases = [
            raw.replace(b'"packet_id": "packet-1"', b'"packet_id": "shadow", "packet_id": "packet-1"', 1),
            raw.replace(b'"nonce": "nonce-1"', b'"nonce": "shadow", "nonce": "nonce-1"', 1),
        ]
        for duplicate_raw in duplicate_cases:
            with self.subTest(raw=duplicate_raw[:80]):
                completed, result = self.run_cli(duplicate_raw)
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(result["errors"], ["INPUT_JSON_INVALID:DUPLICATE_KEY"])
                self.assertEqual(completed.stderr, "")

    def test_non_json_constants_are_rejected(self) -> None:
        raw = json.dumps(valid_packet(), sort_keys=True).encode("utf-8")
        for constant in [b"NaN", b"Infinity", b"-Infinity"]:
            with self.subTest(constant=constant):
                mutated = raw.replace(b'"MISSING_LOOKUP_CLOSURE"', constant, 1)
                completed, result = self.run_cli(mutated)
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(result["errors"], ["INPUT_JSON_INVALID:NON_JSON_CONSTANT"])
                self.assertEqual(completed.stderr, "")

    def test_malformed_and_invalid_utf8_are_stable_json_holds(self) -> None:
        for raw in [b"{", b'{"packet_id":"\xff"}']:
            with self.subTest(raw=raw):
                completed, result = self.run_cli(raw)
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(result["state"], "HOLD_8D_ADI_GIT_INDEX_INVALID")
                self.assertEqual(result["errors"], ["INPUT_JSON_INVALID"])
                self.assertEqual(completed.stderr, "")

    def test_lone_surrogate_hashing_is_a_stable_hold(self) -> None:
        raw = json.dumps(valid_packet(), sort_keys=True).replace('"packet-1"', '"\\ud800"', 1).encode("utf-8")
        completed, result = self.run_cli(raw)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("INPUT_CANONICAL_JSON_INVALID", result["errors"])
        self.assertEqual(completed.stderr, "")

    def test_cli_requires_exact_canonical_bytes(self) -> None:
        packet = valid_packet()
        canonical = json.dumps(
            packet,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8") + b"\n"
        completed, result = self.run_cli(canonical)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(result["state"], "PASS_8D_ADI_GIT_INDEX_CANDIDATE")

        pretty = json.dumps(packet, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
        completed, result = self.run_cli(pretty)
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(result["errors"], ["INPUT_BYTES_NOT_CANONICAL_JSON"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
