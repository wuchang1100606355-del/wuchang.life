import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.safe_git_stage import (
    StageSafetyError,
    is_allowed,
    is_blocked,
    stage_exact_paths,
    validate_exact_path,
)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


class TestSafeGitStage(unittest.TestCase):
    def test_block_runtime_reports(self):
        self.assertTrue(is_blocked("runtime/reports/x.json"))

    def test_block_keys(self):
        self.assertTrue(is_blocked("keys/a.pem"))
        self.assertTrue(is_blocked("config/private_key.pem"))

    def test_allow_tools(self):
        self.assertTrue(is_allowed("tools/x.py", ["tools/"]))

    def test_reject_unknown(self):
        self.assertFalse(is_allowed("random/file.txt", ["tools/"]))

    def test_reject_non_exact_pathspecs(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            for path in (".", "tools/", "../escape", ":(glob)tools/*", "tools/*.py"):
                with self.subTest(path=path), self.assertRaises(StageSafetyError):
                    validate_exact_path(repo, path)


class TestAtomicStage(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.name", "Test")
        git(self.repo, "config", "user.email", "test@example.invalid")
        (self.repo / "tools").mkdir()
        (self.repo / "tools" / "a.txt").write_text("before\n", encoding="utf-8")
        (self.repo / "tools" / "delete.txt").write_text("delete\n", encoding="utf-8")
        git(self.repo, "add", "--", "tools/a.txt", "tools/delete.txt")
        git(self.repo, "commit", "-qm", "base")

    def tearDown(self):
        self.temporary.cleanup()

    def test_stages_exact_content_only(self):
        (self.repo / "tools" / "a.txt").write_text("after\n", encoding="utf-8")
        result = stage_exact_paths(self.repo, ["tools/a.txt"], ["tools/"])
        self.assertEqual(result["state"], "STAGED_EXACT_PATHS")
        self.assertEqual(git(self.repo, "diff", "--cached", "--name-only"), "tools/a.txt")
        self.assertEqual(git(self.repo, "show", ":tools/a.txt"), "after")

    def test_rejects_preexisting_staged_content(self):
        (self.repo / "tools" / "a.txt").write_text("staged first\n", encoding="utf-8")
        git(self.repo, "add", "--", "tools/a.txt")
        (self.repo / "tools" / "new.txt").write_text("new\n", encoding="utf-8")
        with self.assertRaisesRegex(StageSafetyError, "HOLD_PREEXISTING_INDEX_STATE"):
            stage_exact_paths(self.repo, ["tools/new.txt"], ["tools/"])
        self.assertEqual(git(self.repo, "diff", "--cached", "--name-only"), "tools/a.txt")

    def test_deletion_requires_explicit_gate(self):
        (self.repo / "tools" / "delete.txt").unlink()
        with self.assertRaisesRegex(StageSafetyError, "HOLD_DELETE_AUTHORITY_MISSING"):
            stage_exact_paths(self.repo, ["tools/delete.txt"], ["tools/"])
        self.assertEqual(git(self.repo, "diff", "--cached", "--name-only"), "")
        stage_exact_paths(self.repo, ["tools/delete.txt"], ["tools/"], allow_deletion=True)
        self.assertEqual(
            git(self.repo, "diff", "--cached", "--diff-filter=D", "--name-only"),
            "tools/delete.txt",
        )

    def test_failed_scope_does_not_mutate_index(self):
        (self.repo / "tools" / "a.txt").write_text("after\n", encoding="utf-8")
        with self.assertRaises(StageSafetyError):
            stage_exact_paths(self.repo, ["tools/a.txt", "tools/"], ["tools/"])
        self.assertEqual(git(self.repo, "diff", "--cached", "--name-only"), "")


if __name__ == "__main__":
    unittest.main()
