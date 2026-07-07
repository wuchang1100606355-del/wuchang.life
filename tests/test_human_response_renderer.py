from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.total_field.human_response_renderer import render_human_response


class HumanResponseRendererTest(unittest.TestCase):
    def test_pass_reply_hides_internal_markers(self) -> None:
        response = render_human_response(
            {
                "decision": "PASS",
                "risk_level": "LOW",
                "reply_candidate": {
                    "text": "D1 D8 proof_D7 env_D8 H64 TD 可以回覆候選資訊",
                },
            },
            channel="web",
        )

        self.assertEqual(response["decision"], "PASS")
        self.assertFalse(response["requires_confirmation"])
        self.assertFalse(response["formal_send_executed"])
        self.assertEqual(response["agent_name"], "小J")
        self.assertEqual(response["authority"], "candidate_only")
        self.assertEqual(response["role"], "service_persona_language_layer")
        self.assertEqual(response["member_facing_message"], response["reply_text"])
        self.assertTrue(response["intent_packet"]["requires_total_field_verify"])
        self.assertEqual(response["required_member_confirmation"], response["requires_confirmation"])
        self.assertEqual(response["intent_packet"]["requires_member_confirmation"], response["requires_confirmation"])
        self.assertEqual(response["persona_projection"], "GENERAL_XIAOJ")
        self.assertEqual(response["service_context"], "general")
        self.assertEqual(response["media_response"]["mode"], "TEXT_WITH_AUDIO")
        self.assertIn("小J", response["aesthetic"].get("brand_voice", ""))
        self.assertEqual(response["aesthetic"]["decision_aura"], "PASS")
        self.assertTrue(response["aesthetic"]["poetic_line"])
        for forbidden in ("D1", "D8", "proof_D7", "env_D8", "H64", "TD"):
            self.assertNotIn(forbidden, response["reply_text"])
        self.assertFalse(response["redaction"]["raw_d_dimensions_exposed"])
        self.assertFalse(response["redaction"]["h64_td_exposed"])
        self.assertEqual(response["response_profiles"]["selected"], "default")
        self.assertEqual(response["response_profiles"]["voice"], "gentle_curator")
        self.assertEqual(response["response_profiles"]["persona"], "web_host_supportive")
        self.assertIn("default", response["response_variants"])
        self.assertIn("concise", response["response_variants"])
        self.assertIn("poetic", response["response_variants"])
        self.assertTrue(len(response["response_variants"]["concise"]) > 0)

    def test_registration_pass_is_literary_and_actionable(self) -> None:
        response = render_human_response(
            {
                "decision": "PASS",
                "risk_level": "LOW",
                "reply_candidate": {
                    "text": "我要註冊會員，請幫我快速完成。",
                },
            },
            channel="web",
        )

        self.assertEqual(response["decision"], "PASS")
        self.assertIn("註冊", response["aesthetic"]["next_action_hint"])
        self.assertTrue(response["aesthetic"]["tone"])
        self.assertTrue(response["aesthetic"]["scene"])
        self.assertIn("候選體驗", response["value_layer"]["mode"])
        self.assertTrue(any("最小欄位" in item for item in response["value_layer"]["highlights"]))
        self.assertIn("門", response["response_variants"]["poetic"])
        self.assertEqual(response["action_pack"]["mode"], "registration_draft")
        self.assertIn("顯示名稱", response["action_pack"]["required_fields"][0])

    def test_order_booking_pass_highlights_candidate_next_step(self) -> None:
        response = render_human_response(
            {
                "decision": "PASS",
                "risk_level": "LOW",
                "reply_candidate": {
                    "text": "幫我預約今晚 7 點的餐點並回覆可行時間",
                },
            },
            channel="line",
        )

        self.assertEqual(response["decision"], "PASS")
        self.assertEqual(response["channel"], "LINE")
        self.assertEqual(response["response_profiles"]["persona"], "line_friend_supportive")
        self.assertIn("可核對", response["response_variants"]["poetic"])
        self.assertIn("可核對項目", response["response_variants"]["poetic"])
        self.assertIn("核對", response["aesthetic"]["next_action_hint"])
        self.assertIn("可核對", response["value_layer"]["highlights"][1])
        self.assertEqual(response["action_pack"]["mode"], "booking_draft")
        self.assertIn("品項或服務", response["action_pack"]["required_fields"])

    def test_support_complaint_pass_shows_stabilizing_tone(self) -> None:
        response = render_human_response(
            {
                "decision": "PASS",
                "risk_level": "LOW",
                "reply_candidate": {
                    "text": "我在下單時遇到問題，系統出錯。",
                },
            },
            channel="odoo",
        )

        self.assertEqual(response["decision"], "PASS")
        self.assertEqual(response["channel"], "ODOO")
        self.assertIn("誠懇", response["aesthetic"]["tone"])
        self.assertIn("補齊發生時間與步驟", response["aesthetic"]["next_action_hint"])
        self.assertIn("候選體驗", response["value_layer"]["mode"])
        self.assertIn("時間", response["response_variants"]["poetic"])
        self.assertEqual(response["action_pack"]["mode"], "complaint_draft")
        self.assertIn("發生時間", response["action_pack"]["required_fields"])

    def test_high_risk_hold_requires_confirmation(self) -> None:
        response = render_human_response(
            {
                "decision": "HOLD",
                "risk_level": "HIGH",
                "gate_code": "HOLD_HARD_RISK_SIDE_EFFECT",
            },
            channel="line",
        )

        self.assertEqual(response["decision"], "HOLD")
        self.assertEqual(response["channel"], "LINE")
        self.assertTrue(response["requires_confirmation"])
        self.assertIn("暫停", response["reply_text"])
        self.assertFalse(response["line_reply_sent"])
        self.assertFalse(response["odoo_write"])
        self.assertFalse(response["formal_send_executed"])
        self.assertFalse(response["db_write"])
        self.assertFalse(response["deploy"])
        self.assertFalse(response["restart"])
        self.assertEqual(response["required_member_confirmation"], response["requires_confirmation"])
        self.assertEqual(response["persona_projection"], "COMMUNITY_SERVICE_STAFF")
        self.assertEqual(response["service_context"], "community")
        self.assertEqual(response["media_response"]["mode"], "TEXT_ONLY")
        self.assertEqual(response["aesthetic"].get("decision_aura"), "HOLD")
        self.assertIn("response_variants", response)
        self.assertIn("default", response["response_variants"])

    def test_missing_adi_hold_has_plain_language(self) -> None:
        response = render_human_response(
            {
                "decision": "HOLD",
                "risk_level": "MEDIUM",
                "gate_code": "HOLD_ADI_5D_ABSOLUTE_INDEX",
            },
            channel="odoo",
        )

        self.assertEqual(response["decision"], "HOLD")
        self.assertEqual(response["channel"], "ODOO")
        self.assertTrue(response["requires_confirmation"])
        self.assertIn("缺少必要索引條件", response["reply_text"])
        self.assertNotIn("D8", response["reply_text"])
        self.assertEqual(response["required_member_confirmation"], response["requires_confirmation"])
        self.assertEqual(response["persona_projection"], "MERCHANT_SERVICE_STAFF")
        self.assertEqual(response["service_context"], "merchant")
        self.assertEqual(response["media_response"]["mode"], "TEXT_ONLY")
        self.assertEqual(response["aesthetic"]["decision_aura"], "HOLD")


if __name__ == "__main__":
    unittest.main()
