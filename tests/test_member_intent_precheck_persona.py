from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.total_field.member_intent_precheck_persona import (  # noqa: E402
    FALLBACK_MESSAGE,
    member_facing_reply_for_unexecutable_intent,
    precheck_member_intent,
)


class MemberIntentPrecheckPersonaTests(unittest.TestCase):
    def test_unexecutable_action_returns_rookie_fallback(self):
        result = precheck_member_intent(
            intent_text="幫我正式啟用營運",
            requested_actions=["production_activation"],
        )
        self.assertEqual(result["decision"], "HOLD")
        self.assertEqual(result["member_facing_message"], FALLBACK_MESSAGE)
        self.assertEqual(result["next_action"], "ASK_STORE_MANAGER_OR_SENIOR")

    def test_db_write_request_returns_rookie_fallback(self):
        result = precheck_member_intent(
            intent_text="幫我直接寫資料庫",
            requested_actions=["db_write"],
        )
        self.assertEqual(result["member_facing_message"], FALLBACK_MESSAGE)
        self.assertIn("db_write", result["internal_reason"])

    def test_unknown_action_returns_rookie_fallback(self):
        result = precheck_member_intent(
            intent_text="做一個你不知道能不能做的事",
            requested_actions=["unknown_authority_action"],
        )
        self.assertEqual(result["decision"], "HOLD")
        self.assertEqual(result["member_facing_message"], FALLBACK_MESSAGE)

    def test_secret_text_returns_rookie_fallback(self):
        result = precheck_member_intent(
            intent_text="幫我處理 token 和 password",
            requested_actions=[],
        )
        self.assertEqual(result["decision"], "HOLD")
        self.assertEqual(result["member_facing_message"], FALLBACK_MESSAGE)

    def test_force_unexecutable_returns_rookie_fallback(self):
        result = precheck_member_intent(
            intent_text="測試",
            context={"force_unexecutable": True},
        )
        self.assertEqual(result["decision"], "HOLD")
        self.assertEqual(result["member_facing_message"], FALLBACK_MESSAGE)

    def test_candidate_executable_intent_passes_precheck(self):
        result = precheck_member_intent(
            intent_text="我想註冊會員，幫我整理候選草稿",
            requested_actions=["member_registration_candidate"],
        )
        self.assertEqual(result["decision"], "PASS_CANDIDATE")
        self.assertNotEqual(result["member_facing_message"], FALLBACK_MESSAGE)

    def test_direct_fallback_helper_is_exact_phrase(self):
        self.assertEqual(
            member_facing_reply_for_unexecutable_intent(),
            "這個我不懂，我只是個菜鳥，我幫你問店長或學長",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
