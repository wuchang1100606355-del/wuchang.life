import unittest
from tools.safe_git_stage import is_blocked, is_allowed

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

if __name__ == "__main__":
    unittest.main()
