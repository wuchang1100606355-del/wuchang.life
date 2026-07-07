from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.total_field.wuchang_business_cloud_exchange_bridge import (  # noqa: E402
    ROOKIE_MESSAGE,
    build_business_cloud_candidate,
    classify_business_cloud_task,
    load_business_cloud_exchange_map,
    render_business_cloud_member_response,
)


class WuchangBusinessCloudExchangeBridgeTests(unittest.TestCase):
    def test_policy_is_safe(self):
        data = load_business_cloud_exchange_map()
        self.assertFalse(data["policy"]["formal_exchange"])
        self.assertFalse(data["policy"]["payment_capture"])
        self.assertFalse(data["policy"]["legal_tender_claim"])
        self.assertFalse(data["policy"]["token_mint"])
        self.assertFalse(data["policy"]["db_write"])

    def test_classify_business_cloud_tasks(self):
        self.assertEqual(classify_business_cloud_task("建立商家資料"), "merchant_profile")
        self.assertEqual(classify_business_cloud_task("產生票券候選"), "ticket_candidate")
        self.assertEqual(classify_business_cloud_task("幸福幣交換"), "happiness_coin_exchange")
        self.assertEqual(classify_business_cloud_task("社區商業資訊共享平台"), "business_info_share")

    def test_merchant_profile_pass_candidate(self):
        candidate = build_business_cloud_candidate(intent_text="建立商家資料")
        self.assertEqual(candidate["STATE"], "PASS_CANDIDATE")
        self.assertEqual(candidate["task_type"], "merchant_profile")
        self.assertFalse(candidate["db_write"])
        self.assertIn("eight_d_packet", candidate)

    def test_ticket_requires_exchange_terms(self):
        candidate = build_business_cloud_candidate(intent_text="產生票券候選")
        self.assertEqual(candidate["STATE"], "HOLD")
        self.assertIn("exchange_terms_candidate", candidate["missing_fields"])

    def test_ticket_with_terms_passes_candidate(self):
        candidate = build_business_cloud_candidate(
            intent_text="產生票券候選",
            exchange_terms_candidate={"ticket_kind": "community_discount_candidate"}
        )
        self.assertEqual(candidate["STATE"], "PASS_CANDIDATE")
        self.assertFalse(candidate["issue_real_ticket"])

    def test_happiness_coin_exchange_with_terms_passes_candidate(self):
        candidate = build_business_cloud_candidate(
            intent_text="幸福幣交換",
            exchange_terms_candidate={"from": "happiness_coin_ref", "to": "ticket_candidate_ref"}
        )
        self.assertEqual(candidate["STATE"], "PASS_CANDIDATE")
        self.assertEqual(candidate["task_type"], "happiness_coin_exchange")
        self.assertFalse(candidate["formal_exchange"])
        self.assertFalse(candidate["payment_capture"])
        self.assertFalse(candidate["legal_tender_claim"])

    def test_business_info_share_requires_evidence(self):
        candidate = build_business_cloud_candidate(intent_text="社區商業資訊共享平台")
        self.assertEqual(candidate["STATE"], "HOLD")
        self.assertIn("evidence_refs", candidate["missing_fields"])

    def test_business_info_share_with_evidence_passes_candidate(self):
        candidate = build_business_cloud_candidate(
            intent_text="社區商業資訊共享平台",
            evidence_refs=["evidence_ref:merchant_profile", "evidence_ref:opening_hours"]
        )
        self.assertEqual(candidate["STATE"], "PASS_CANDIDATE")
        self.assertFalse(candidate["publish_now"])

    def test_hard_risk_blocks(self):
        candidate = build_business_cloud_candidate(
            intent_text="幸福幣正式交換",
            exchange_terms_candidate={"from": "coin", "to": "ticket"},
            requested_actions=["payment_capture", "formal_exchange", "token_mint"]
        )
        self.assertEqual(candidate["STATE"], "BLOCK")
        self.assertIn("payment_capture", candidate["blocked_actions"])
        self.assertIn("formal_exchange", candidate["blocked_actions"])
        self.assertIn("token_mint", candidate["blocked_actions"])

    def test_block_response_uses_rookie_message(self):
        candidate = build_business_cloud_candidate(
            intent_text="幸福幣正式交換",
            exchange_terms_candidate={"from": "coin", "to": "ticket"},
            requested_actions=["formal_exchange"]
        )
        response = render_business_cloud_member_response(candidate)
        self.assertEqual(response["member_facing_message"], ROOKIE_MESSAGE)

    def test_8d_packet_has_total_field_authority(self):
        candidate = build_business_cloud_candidate(intent_text="建立商家資料")
        packet = candidate["eight_d_packet"]
        self.assertEqual(packet["d8_envelope"]["decision_authority"], "total_field")
        self.assertTrue(packet["d8_envelope"]["owner_admin_review_required"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
