from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.total_field_prepare_git_push_review_request import (
    ReviewRequestRejected,
    active_review_request_pointer_path,
    build_review_request,
    register_review_request,
)


class PrepareGitPushReviewRequestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        subprocess.run(
            ["git", "init", "-b", "agent/moving-v-v2-taiji8d-local-canary", self.root],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(["git", "-C", self.root, "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", self.root, "config", "user.name", "Review Test"], check=True)
        (self.root / ".gitignore").write_text("runtime/\n", encoding="utf-8")
        config_path = self.root / "configs/total_field/git_push_review_gate_v1.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(
            json.dumps(
                {
                    "state": "ACTIVE_FAIL_CLOSED",
                    "passkey_verifier": {
                        "active_review_request_pointer_ref": "runtime/total_field/runtime_state/passkey_d8/ACTIVE_REVIEW_REQUEST.json",
                        "maximum_ttl_seconds": 300,
                        "admitted_deployments": [
                            {
                                "deployment_id": "msi_wsl_gateway_hourly_v1",
                                "target_node": "MSI_WSL",
                                "repository_root": "/home/taiji_admin/Taiji_Hub",
                                "service": "taiji-gateway.service",
                                "timer": "w7tp-hourly-reviewed-commit.timer",
                                "application": "services.gateway.main:app",
                                "active_port": 8081,
                                "canary_port": 8083,
                                "carrier": "LOCAL_SYSTEMD_USER",
                            }
                        ],
                    },
                }
            ),
            encoding="utf-8",
        )
        subprocess.run(["git", "-C", self.root, "add", "."], check=True)
        subprocess.run(["git", "-C", self.root, "commit", "-m", "base"], check=True, stdout=subprocess.DEVNULL)
        self.base = self.git("rev-parse", "HEAD")
        subprocess.run(
            ["git", "-C", self.root, "update-ref", "refs/remotes/origin/agent/moving-v-v2-taiji8d-local-canary", self.base],
            check=True,
        )
        subprocess.run(
            ["git", "-C", self.root, "remote", "add", "origin", "git@example.invalid:owner/repo.git"],
            check=True,
        )
        (self.root / "change.txt").write_text("review me\n", encoding="utf-8")
        subprocess.run(["git", "-C", self.root, "add", "change.txt"], check=True)
        subprocess.run(["git", "-C", self.root, "commit", "-m", "candidate"], check=True, stdout=subprocess.DEVNULL)
        self.target = self.git("rev-parse", "HEAD")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", self.root, *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def build(self) -> tuple[Path, dict]:
        return build_review_request(
            repo_root=self.root,
            base_commit=self.base,
            target_commit=self.target,
            target_branch="agent/moving-v-v2-taiji8d-local-canary",
            remote_name="origin",
            created_at="2026-09-09T00:00:00Z",
        )

    def test_exact_single_commit_request_is_hash_bound_and_non_authoritative(self) -> None:
        path, packet = self.build()
        self.assertEqual(packet["state"], "REGISTERED_PENDING_TOTAL_FIELD_REVIEW")
        self.assertEqual(packet["D3_COORDINATE"]["base_commit"], self.base)
        self.assertEqual(packet["D3_COORDINATE"]["changed_paths"], ["change.txt"])
        self.assertEqual(packet["D8_ENVELOPE_AUTHORITY"]["requested_scopes"], ["AUTHORIZE_GIT_PUSH"])
        self.assertFalse(packet["D8_ENVELOPE_AUTHORITY"]["execution_authorized"])
        pointer_path = active_review_request_pointer_path(self.root)
        register_review_request(path, packet, active_pointer_path=pointer_path)
        register_review_request(path, packet, active_pointer_path=pointer_path)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["packet_sha256"], packet["packet_sha256"])
        pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
        self.assertEqual(pointer["request_packet_sha256"], packet["packet_sha256"])
        self.assertEqual(pointer["review_request_ref"], path.relative_to(self.root).as_posix())

    def test_dirty_tree_is_blocked(self) -> None:
        (self.root / "late.txt").write_text("not reviewed", encoding="utf-8")
        with self.assertRaisesRegex(ReviewRequestRejected, "DIRTY_WORKTREE_BLOCKED"):
            self.build()

    def test_exact_registered_deployment_is_bound_to_same_request(self) -> None:
        path, packet = build_review_request(
            repo_root=self.root,
            base_commit=self.base,
            target_commit=self.target,
            target_branch="agent/moving-v-v2-taiji8d-local-canary",
            remote_name="origin",
            deployment_id="msi_wsl_gateway_hourly_v1",
            created_at="2026-09-09T00:00:00Z",
        )
        self.assertEqual(
            packet["D8_ENVELOPE_AUTHORITY"]["requested_scopes"],
            ["AUTHORIZE_GIT_PUSH", "AUTHORIZE_EXACT_DEPLOY_RESTART"],
        )
        self.assertEqual(
            packet["D5_EXECUTION_POLICY"]["deployment"]["service"],
            "taiji-gateway.service",
        )
        self.assertIn(packet["packet_sha256"], path.as_posix())

    def test_remote_base_drift_is_blocked(self) -> None:
        subprocess.run(
            ["git", "-C", self.root, "update-ref", "refs/remotes/origin/agent/moving-v-v2-taiji8d-local-canary", self.target],
            check=True,
        )
        with self.assertRaisesRegex(ReviewRequestRejected, "REMOTE_BASE_DRIFT"):
            self.build()


if __name__ == "__main__":
    unittest.main()
