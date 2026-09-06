from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.total_field_git_push_gate import _paths_sha256, verify_push


class Ledger:
    persistent = True


class Verifier:
    trusted_runtime_verifier = True


class TotalFieldGitPushGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.name", "Test"], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.email", "test@example.invalid"], check=True)
        (self.root / "configs/total_field").mkdir(parents=True)
        (self.root / "configs/total_field/git_push_review_gate_v1.json").write_text(
            json.dumps({"state": "ACTIVE_FAIL_CLOSED"}), encoding="utf-8"
        )
        (self.root / "a.txt").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.root), "add", "a.txt"], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-qm", "base"], check=True)
        self.base = self.git("rev-parse", "HEAD")
        (self.root / "a.txt").write_text("target\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.root), "add", "a.txt"], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-qm", "target"], check=True)
        self.tip = self.git("rev-parse", "HEAD")
        self.tree = self.git("rev-parse", "HEAD^{tree}")
        self.remote_url = "git@example.invalid:wuchang.life.git"
        self.paths_hash = _paths_sha256(["a.txt"])
        self.review_ref = "runtime/total_field/authority_artifacts/review/GIT_PUSH_REVIEW_REGISTRATION.json"
        review = {
            "schema_id": "W7TP_TOTAL_FIELD_GIT_PUSH_REVIEW_REGISTRATION_V1",
            "state": "PASS_TOTAL_FIELD_REVIEW_REGISTERED",
            "review_registered": True,
            "total_field_decision": "ALLOW_FORMAL_GIT_PUSH",
            "base_commit": self.base,
            "target_tree": self.tree,
            "branch": "main",
            "remote_name": "origin",
            "remote_url_sha256": hashlib.sha256(self.remote_url.encode()).hexdigest(),
            "allowed_paths_sha256": self.paths_hash,
        }
        path = self.root / self.review_ref
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(review, sort_keys=True) + "\n", encoding="utf-8")
        self.constraints = {
            **{key: review[key] for key in ("base_commit", "target_tree", "branch", "remote_name", "remote_url_sha256", "allowed_paths_sha256")},
            "review_registration_ref": self.review_ref,
            "review_registration_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "single_commit_only": True,
            "formal_submission": True,
            "git_push": True,
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def git(self, *args: str) -> str:
        return subprocess.check_output(["git", "-C", str(self.root), *args], text=True).strip()

    def resolve(self, *_args, **_kwargs):
        return {
            "state": "PASS_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVED",
            "authority_verified": True,
            "scope": ["AUTHORIZE_GIT_PUSH"],
            "authority_scope_constraints": self.constraints,
            "authority_sha256": "a" * 64,
        }

    def call(self, resolver=None):
        return verify_push(
            repo_root=self.root,
            remote_name="origin",
            remote_url=self.remote_url,
            updates=[("refs/heads/main", self.tip, "refs/heads/main", self.base)],
            authority_resolver=resolver or self.resolve,
            nonce_ledger=Ledger(),
            signature_verifier=Verifier(),
            trusted_verifier_refs=("verifier_ref:total_field_runtime_v1",),
        )

    def test_exact_registered_review_passes(self) -> None:
        result = self.call()
        self.assertEqual(result["state"], "PASS_TOTAL_FIELD_GIT_PUSH_GATE")
        self.assertTrue(result["push_authorized"])

    def test_expired_or_unverified_authority_holds(self) -> None:
        result = self.call(lambda *_args, **_kwargs: {"state": "HOLD_AUTHORITY_EXPIRED"})
        self.assertEqual(result["state"], "HOLD_TOTAL_FIELD_GIT_PUSH_GATE")
        self.assertFalse(result["push_authorized"])

    def test_tree_drift_holds(self) -> None:
        self.constraints["target_tree"] = "f" * 40
        result = self.call()
        self.assertEqual(result["reason"], "REVIEW_AUTHORITY_BINDING_MISMATCH")
        self.assertFalse(result["push_authorized"])

    def test_expired_legacy_authority_uses_and_consumes_exact_passkey(self) -> None:
        calls = []

        def passkey(**kwargs):
            calls.append(kwargs["consume"])
            return {
                "state": "PASS_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVED",
                "authority_verified": True,
                "scope": ["AUTHORIZE_GIT_PUSH"],
                "authority_scope_constraints": self.constraints,
                "authority_sha256": "b" * 64,
            }

        result = verify_push(
            repo_root=self.root,
            remote_name="origin",
            remote_url=self.remote_url,
            updates=[("refs/heads/main", self.tip, "refs/heads/main", self.base)],
            authority_resolver=lambda *_args, **_kwargs: {"state": "HOLD_AUTHORITY_EXPIRED"},
            nonce_ledger=Ledger(),
            signature_verifier=Verifier(),
            trusted_verifier_refs=("verifier_ref:total_field_runtime_v1",),
            passkey_authority_resolver=passkey,
        )
        self.assertTrue(result["push_authorized"])
        self.assertEqual(result["authority_source"], "USER_VERIFIED_DEVICE_PASSKEY")
        self.assertEqual(calls, [False, True])

    def test_invalid_push_does_not_consume_passkey(self) -> None:
        calls = []

        def passkey(**kwargs):
            calls.append(kwargs["consume"])
            return {
                "state": "PASS_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVED",
                "authority_verified": True,
                "scope": ["AUTHORIZE_GIT_PUSH"],
                "authority_scope_constraints": self.constraints,
                "authority_sha256": "b" * 64,
            }

        result = verify_push(
            repo_root=self.root,
            remote_name="wrong",
            remote_url=self.remote_url,
            updates=[("refs/heads/main", self.tip, "refs/heads/main", self.base)],
            authority_resolver=lambda *_args, **_kwargs: {"state": "HOLD_AUTHORITY_EXPIRED"},
            nonce_ledger=Ledger(),
            signature_verifier=Verifier(),
            trusted_verifier_refs=("verifier_ref:total_field_runtime_v1",),
            passkey_authority_resolver=passkey,
        )
        self.assertFalse(result["push_authorized"])
        self.assertEqual(result["reason"], "REMOTE_BINDING_MISMATCH")
        self.assertEqual(calls, [False])


if __name__ == "__main__":
    unittest.main()
