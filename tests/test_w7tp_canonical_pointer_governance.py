import base64
import copy
import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tools.total_field_authority_runtime_bindings import SQLitePersistentNonceLedger
from tools.total_field_ed25519_backend import Ed25519DetachedSignatureBackend
from tools.total_field.w7tp_canonical_pointer_governance import (
    POINTER_REL,
    canonical_bytes,
    create_current_active_canonical_pointer_if_absent,
    resolve_current_active_canonical_pointer,
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class PointerGovernanceTests(unittest.TestCase):
    def fixture(self, *, canonical_sha=None, authority_valid=True):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        canonical_rel = "docs/total_field/W7TP_CANONICAL_V2_1.md"
        canonical_path = root / canonical_rel
        canonical_path.parent.mkdir(parents=True)
        canonical_data = b"CANONICAL_LOCKED\n"
        canonical_path.write_bytes(canonical_data)
        subprocess.run(["git", "-C", str(root), "add", canonical_rel], check=True)
        subprocess.run(
            ["git", "-C", str(root), "-c", "user.name=Fixture", "-c", "user.email=fixture@invalid",
             "commit", "-qm", "fixture canonical"],
            check=True,
        )
        commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
        actual_sha = sha(canonical_data)
        chosen_sha = canonical_sha or actual_sha

        private = Ed25519PrivateKey.generate()
        public_path = root / "public.pem"
        public_path.write_bytes(private.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ))
        verifier_ref = "fixture:pointer-bootstrap"
        verifier = Ed25519DetachedSignatureBackend(public_path, trusted_verifier_refs=[verifier_ref])
        authority_id = "fixture-pointer-authority"
        authority_sha = sha(b"fixture-pointer-authority-object")
        receipt_ref = "runtime/total_field/master_index/receipts/fixture/POINTER_BOOTSTRAP_RECEIPT.json"
        now = datetime.now(timezone.utc)
        auth = {
            "schema_id": "W7TP_CURRENT_POINTER_BOOTSTRAP_AUTHORIZATION_V1",
            "state": "AUTHORIZED_SINGLE_POINTER_BOOTSTRAP",
            "scope": "BOOTSTRAP_CURRENT_ACTIVE_CANONICAL_POINTER",
            "pointer_ref": POINTER_REL,
            "expected_preimage": "ABSENT",
            "canonical_locator": canonical_rel,
            "canonical_commit": commit,
            "canonical_sha256": chosen_sha,
            "receipt_ref": receipt_ref,
            "authority_id": authority_id,
            "authority_sha256": authority_sha,
            "nonce_ref": "nonce_ref:sha256:" + sha(os.urandom(32)),
            "issued_at": (now - timedelta(seconds=1)).isoformat(),
            "expires_at": (now + timedelta(seconds=120)).isoformat(),
            "verifier_ref": verifier_ref,
        }
        payload_sha = sha(canonical_bytes(auth))
        auth["payload_sha256"] = payload_sha
        auth["signature"] = "ed25519:" + base64.urlsafe_b64encode(
            private.sign(payload_sha.encode("ascii"))
        ).decode("ascii").rstrip("=")
        request = {
            "schema_id": "W7TP_CURRENT_POINTER_BOOTSTRAP_REQUEST_V1",
            "state": "REQUEST_POINTER_BOOTSTRAP",
            "pointer_ref": POINTER_REL,
            "expected_preimage": "ABSENT",
            "create_if_absent": True,
            "fail_if_already_exists": True,
            "canonical_locator": canonical_rel,
            "canonical_commit": commit,
            "canonical_sha256": chosen_sha,
            "canonical_identity": "W7TP_V2_1_FIXTURE",
            "logical_time": now.isoformat(),
            "receipt_ref": receipt_ref,
            "authorization_ref": "fixture:founder:pointer-bootstrap",
            "authorization": auth,
        }
        resolver = lambda _: {
            "state": "PASS_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVED" if authority_valid else "HOLD_AUTHORITY_INVALID",
            "authority_verified": authority_valid,
            "authority_id": authority_id,
            "authority_sha256": authority_sha,
            "scope": ["BOOTSTRAP_CURRENT_ACTIVE_CANONICAL_POINTER"],
        }
        ledger = SQLitePersistentNonceLedger(root / "runtime/total_field/runtime_state/nonce.sqlite3")
        return temp, root, request, ledger, verifier, resolver, actual_sha

    def execute(self, fixture, *, dry_run=False):
        temp, root, request, ledger, verifier, resolver, _ = fixture
        result = create_current_active_canonical_pointer_if_absent(
            request,
            repo_root=root,
            nonce_ledger=ledger,
            signature_verifier=verifier,
            authority_resolver=resolver,
            dry_run=dry_run,
        )
        return result

    def close(self, fixture):
        fixture[3].close()
        fixture[0].cleanup()

    def test_a_missing_reported(self):
        f = self.fixture()
        try:
            self.assertEqual("MISSING", resolve_current_active_canonical_pointer(repo_root=f[1])["state"])
        finally:
            self.close(f)

    def test_b_synthetic_create_if_absent_pass(self):
        f = self.fixture()
        try:
            result = self.execute(f)
            self.assertEqual("PASS_POINTER_BOOTSTRAP_CREATED", result["state"])
            resolved = resolve_current_active_canonical_pointer(
                repo_root=f[1], expected_pointer_sha256=result["pointer_sha256"],
                authority_validator=lambda _: True,
            )
            self.assertEqual("FOUND_ACTIVE_AND_CURRENT", resolved["state"])
        finally:
            self.close(f)

    def test_c_second_create_fails_already_exists(self):
        f = self.fixture()
        try:
            self.assertEqual("PASS_POINTER_BOOTSTRAP_CREATED", self.execute(f)["state"])
            self.assertEqual("FAIL_ALREADY_EXISTS", self.execute(f)["state"])
        finally:
            self.close(f)

    def test_d_wrong_canonical_hash_fails(self):
        f = self.fixture(canonical_sha="0" * 64)
        try:
            result = self.execute(f)
            self.assertEqual("HOLD_POINTER_BOOTSTRAP", result["state"])
            self.assertEqual("CANONICAL_HASH_MISMATCH", result["reason"])
            self.assertFalse((f[1] / POINTER_REL).exists())
        finally:
            self.close(f)

    def test_e_invalid_authority_fails(self):
        f = self.fixture(authority_valid=False)
        try:
            result = self.execute(f)
            self.assertEqual("HOLD_POINTER_BOOTSTRAP", result["state"])
            self.assertEqual("AUTHORITY_INVALID", result["reason"])
            self.assertFalse((f[1] / POINTER_REL).exists())
        finally:
            self.close(f)

    def test_f_receipt_is_append_only_and_bound(self):
        f = self.fixture()
        try:
            result = self.execute(f)
            receipt = f[1] / f[2]["receipt_ref"]
            before = receipt.read_bytes()
            self.assertTrue(result["receipt_created"])
            self.assertEqual(result["receipt_sha256"], json.loads(before)["receipt_sha256"])
            self.assertEqual("FAIL_ALREADY_EXISTS", self.execute(f)["state"])
            self.assertEqual(before, receipt.read_bytes())
        finally:
            self.close(f)

    def test_g_dry_run_has_no_pointer_receipt_or_nonce_effect(self):
        f = self.fixture()
        try:
            result = self.execute(f, dry_run=True)
            self.assertEqual("PASS_POINTER_BOOTSTRAP_DRY_RUN", result["state"])
            self.assertFalse((f[1] / POINTER_REL).exists())
            self.assertFalse((f[1] / f[2]["receipt_ref"]).exists())
            self.assertEqual(0, f[3].entry_count())
        finally:
            self.close(f)


if __name__ == "__main__":
    unittest.main()
