import base64
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tools.total_field_authority_runtime_bindings import SQLitePersistentNonceLedger
from tools.total_field_ed25519_backend import Ed25519DetachedSignatureBackend
from tools.total_field.w7tp_governed_promotion import canonical_bytes, promote_accepted_candidate


def sha(data):
    return hashlib.sha256(data).hexdigest()


class GovernedPromotionTests(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)

        def put(rel, data):
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return sha(data)

        candidate_sha = put("runtime/total_field/candidate_specs/bridge/candidate.json", b'{"candidate_only":true,"activation":false}\n')
        canonical_sha = put("docs/total_field/current.md", b"CANONICAL_LOCKED\n")
        target_sha = put("runtime/total_field/candidate_specs/bridge/target.md", b"W7TP 3.0 CANDIDATE\n")
        decision = {
            "schema_id": "W7TP_TOTAL_FIELD_FORMAL_CANDIDATE_DECISION_EVIDENCE_V1",
            "state": "TOTAL_FIELD_DECISION_OBTAINED",
            "candidate_sha256": candidate_sha,
            "total_field_result": {
                "decision": "ALLOW_CANDIDATE_ACCEPTED",
                "owner_receive_candidate_state": "ALLOW_CANDIDATE_ACCEPTED",
                "state": "ALLOW_CANDIDATE_ACCEPTED",
            },
        }
        decision_sha = put("runtime/total_field/decisions/bridge/decision.json", canonical_bytes(decision) + b"\n")
        pointer = {
            "schema_id": "ACTIVE_W7TP_CANONICAL_POINTER_V1",
            "active_canonical_sha256": canonical_sha,
            "activation": True,
        }
        pointer_sha = put("runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json", canonical_bytes(pointer) + b"\n")

        private = Ed25519PrivateKey.generate()
        public_path = root / "public.pem"
        public_path.write_bytes(private.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ))
        verifier_ref = "fixture:promotion-ed25519"
        verifier = Ed25519DetachedSignatureBackend(public_path, trusted_verifier_refs=[verifier_ref])
        now = datetime.now(timezone.utc)
        auth = {
            "schema_id": "W7TP_SINGLE_USE_PROMOTION_AUTHORIZATION_V1",
            "state": "AUTHORIZED_SINGLE_PROMOTION",
            "scope": "PROMOTE_ACCEPTED_CANDIDATE",
            "authority_id": "fixture-active-authority",
            "candidate_sha256": candidate_sha,
            "decision_evidence_sha256": decision_sha,
            "current_canonical_sha256": canonical_sha,
            "target_canonical_sha256": target_sha,
            "active_pointer_preimage_sha256": pointer_sha,
            "nonce_ref": "nonce_ref:sha256:" + sha(b"single-use-fixture"),
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
            "schema_id": "W7TP_GOVERNED_PROMOTION_REQUEST_V1",
            "state": "REQUEST_SINGLE_PROMOTION",
            "candidate_artifact_ref": "runtime/total_field/candidate_specs/bridge/candidate.json",
            "candidate_sha256": candidate_sha,
            "decision_evidence_ref": "runtime/total_field/decisions/bridge/decision.json",
            "decision_evidence_sha256": decision_sha,
            "total_field_decision": "ALLOW_CANDIDATE_ACCEPTED",
            "current_canonical_ref": "docs/total_field/current.md",
            "current_canonical_sha256": canonical_sha,
            "target_canonical_ref": "runtime/total_field/candidate_specs/bridge/target.md",
            "target_canonical_sha256": target_sha,
            "active_pointer_ref": "runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json",
            "active_pointer_sha256": pointer_sha,
            "promotion_output_ref": "runtime/total_field/promotions/fixture-promotion",
            "historical_receipt_reconstruction": False,
            "promotion_authorization": auth,
        }
        resolver = lambda _: {
            "state": "PASS_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVED",
            "authority_verified": True,
            "authority_id": "fixture-active-authority",
            "scope": ["PROMOTE_ACCEPTED_CANDIDATE"],
        }
        ledger = SQLitePersistentNonceLedger(root / "runtime/total_field/runtime_state/nonce.sqlite3")
        return temp, root, request, ledger, verifier, resolver

    def test_dry_run_has_no_promotion_effect(self):
        temp, root, request, ledger, verifier, resolver = self.fixture()
        try:
            before = (root / request["active_pointer_ref"]).read_bytes()
            result = promote_accepted_candidate(
                request, repo_root=root, nonce_ledger=ledger,
                signature_verifier=verifier, authority_resolver=resolver, dry_run=True,
            )
            self.assertEqual("PASS_GOVERNED_PROMOTION_DRY_RUN", result["state"])
            self.assertFalse(result["promotion"])
            self.assertFalse(result["activation"])
            self.assertEqual(before, (root / request["active_pointer_ref"]).read_bytes())
            self.assertFalse((root / request["promotion_output_ref"]).exists())
        finally:
            ledger.close()
            temp.cleanup()

    def test_formal_total_field_decision_contract_is_accepted(self):
        temp, root, request, ledger, verifier, resolver = self.fixture()
        try:
            result = promote_accepted_candidate(
                request, repo_root=root, nonce_ledger=ledger,
                signature_verifier=verifier, authority_resolver=resolver, dry_run=True,
            )
            self.assertEqual("PASS_GOVERNED_PROMOTION_DRY_RUN", result["state"])
        finally:
            ledger.close()
            temp.cleanup()

    def test_fixture_commit_is_append_only_and_pending_activation(self):
        temp, root, request, ledger, verifier, resolver = self.fixture()
        try:
            canonical_before = (root / request["current_canonical_ref"]).read_bytes()
            result = promote_accepted_candidate(
                request, repo_root=root, nonce_ledger=ledger,
                signature_verifier=verifier, authority_resolver=resolver,
            )
            self.assertEqual("PASS_GOVERNED_PROMOTION", result["state"])
            self.assertTrue(result["promotion"])
            self.assertFalse(result["activation"])
            self.assertEqual(canonical_before, (root / request["current_canonical_ref"]).read_bytes())
            receipt = json.loads((root / result["promotion_receipt"]).read_text())
            self.assertEqual("PROMOTED_PENDING_ACTIVATION", receipt["state"])
            self.assertFalse(receipt["final_authority_granted"])
            pointer = json.loads((root / request["active_pointer_ref"]).read_text())
            self.assertEqual("PROMOTED_PENDING_ACTIVATION", pointer["promotion_state"])
            self.assertFalse(pointer["pending_promotion"]["activation"])
        finally:
            ledger.close()
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
