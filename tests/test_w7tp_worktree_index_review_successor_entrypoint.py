import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from tools.total_field.w7tp_worktree_index_review_successor_entrypoint import (
    BindingError,
    REQUEST_SCHEMA,
    RECEIPT_SCHEMA,
    envelope_hash,
    index_entries,
    manifest_hash,
    safe_ref,
    self_hash,
    validate_schemas,
)


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class WorktreeIndexReviewSuccessorTests(unittest.TestCase):
    def test_successor_schemas_are_valid_and_receipt_binds_native_decision(self):
        self.assertEqual(validate_schemas()["state"], "CANDIDATE_SCHEMAS_VALID")
        receipt_schema = json.loads(RECEIPT_SCHEMA.read_text())
        self.assertIn("native_d8_decision_reference", receipt_schema["required"])
        self.assertIn("native_d8_decision_sha256", receipt_schema["required"])

    def test_index_entries_are_derived_from_index_blob_not_worktree(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            source = repo / "candidate.txt"
            source.write_bytes(b"staged bytes\n")
            subprocess.run(["git", "-C", str(repo), "add", "candidate.txt"], check=True)
            source.write_bytes(b"working tree drift\n")
            entries = index_entries(repo)
            self.assertEqual(entries, [{
                "path": "candidate.txt", "mode": "100644", "stage": 0,
                "blob_oid": entries[0]["blob_oid"],
                "staged_bytes_sha256": sha(b"staged bytes\n"),
            }])

    def test_manifest_request_and_envelope_self_hashes_are_non_cyclic(self):
        schema = json.loads(REQUEST_SCHEMA.read_text())
        digest = "a" * 64
        manifest = {
            "schema_version": "W7TP-GIT-INDEX-MANIFEST/1.0", "staged_count": 1,
            "entries": [{"path": "candidate.txt", "mode": "100644", "stage": 0, "blob_oid": "b" * 40, "staged_bytes_sha256": digest}],
            "excluded_files": ["core/adi_native/index.py"],
            "manifest_self_hash_algorithm": "SHA256_CANONICAL_JSON_EXCLUDING_MANIFEST_SELF_SHA256/1.0",
            "manifest_self_sha256": "0" * 64,
        }
        manifest["manifest_self_sha256"] = manifest_hash(manifest)
        authority = {name: {"reference": f"authority/{name}.json", "sha256": digest} for name in (
            "canonical", "active_root", "founder_authorization", "d8_authority",
            "identity", "seat", "assignment", "access_profile"
        )}
        request = {
            "schema_version": "W7TP-TOTAL-FIELD-WORKTREE-INDEX-REVIEW-REQUEST/1.0",
            "packet_type": "TOTAL_FIELD_WORKTREE_INDEX_REVIEW_REQUEST_CANDIDATE",
            "state": "CANDIDATE_PENDING_OWNER_SEAL_AND_FORMAL_SUBMISSION",
            "run_id": "RUN", "authorization_request_id": "AUTH",
            "acceptance_mode": "EXACT_STATE_ONLY", "float_data_index": "NOT_APPLICABLE",
            "repository": {"identity_reference": "authority/repo.json", "identity_sha256": digest, "path": "/repo", "object_format": "sha1", "branch": "main", "base_head": "c" * 40, "upstream_sha": "d" * 40},
            "queue_binding": {"queue_path": "queue.json", "queue_entry_sha256": digest, "candidate_content_sha256": digest},
            "index_manifest": manifest, "authority_binding": authority,
            "logical_time": {"namespace": "native", "reference": "authority/time.json", "reference_sha256": digest},
            "single_use": {"enabled": True, "nonce_reference": "authority/nonce.json", "nonce_sha256": digest, "expires_at": "2099-01-01T00:00:00Z", "replay_protection": "REJECT_EXISTING_NONCE_OR_EXACT_BINDING"},
            "non_execution_assertions": {key: False for key in ("formal_submission", "reviewer_call", "receipt_creation", "owner_seal_activation", "git_write", "deploy", "restart", "db_write", "pointer_write", "canonical_write")},
            "request_self_hash_algorithm": "SHA256_CANONICAL_JSON_EXCLUDING_REQUEST_SELF_SHA256/1.0", "request_self_sha256": "0" * 64,
            "envelope_self_hash_algorithm": "SHA256_CANONICAL_JSON_EXCLUDING_BOTH_SELF_HASHES/1.0", "envelope_self_sha256": "0" * 64,
        }
        request["envelope_self_sha256"] = envelope_hash(request)
        request["request_self_sha256"] = self_hash(request, "request_self_sha256")
        self.assertEqual(list(Draft202012Validator(schema).iter_errors(request)), [])
        self.assertEqual(envelope_hash(request), request["envelope_self_sha256"])

    def test_reference_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(BindingError, "HOLD_REFERENCE_PATH_INVALID"):
                safe_ref(Path(raw), "../secret", "0" * 64, "$.authority")


if __name__ == "__main__":
    unittest.main()
