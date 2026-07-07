from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.total_field.wuchang_property_cloud_case_law_bridge import (  # noqa: E402
    ROOKIE_MESSAGE,
    build_property_cloud_candidate,
    classify_group_member_cloud_affiliation,
    classify_property_cloud_task,
    load_property_cloud_map,
    render_property_cloud_member_response,
)


class WuchangPropertyCloudCaseLawBridgeTests(unittest.TestCase):
    def test_policy_is_safe(self):
        data = load_property_cloud_map()
        self.assertFalse(data["policy"]["formal_legal_advice"])
        self.assertFalse(data["policy"]["formal_submission"])
        self.assertFalse(data["policy"]["db_write"])
        self.assertFalse(data["policy"]["deploy"])
        self.assertFalse(data["policy"]["restart"])

    def test_classify_property_cloud_tasks(self):
        self.assertEqual(classify_property_cloud_task("社區公道伯調解"), "community_mediation")
        self.assertEqual(classify_property_cloud_task("物業案例查詢"), "property_case_query")
        self.assertEqual(classify_property_cloud_task("物業補助"), "property_subsidy")
        self.assertEqual(classify_property_cloud_task("優良社區申報"), "excellent_community_application")
        self.assertEqual(classify_property_cloud_task("公寓大廈法令收集"), "property_law_collection")

    def test_group_member_business_cloud(self):
        result = classify_group_member_cloud_affiliation("商家票券合作店")
        self.assertEqual(result["cloud_affiliations"], ["business_cloud"])

    def test_group_member_property_cloud(self):
        result = classify_group_member_cloud_affiliation("管委會物業管理公司")
        self.assertEqual(result["cloud_affiliations"], ["property_cloud"])

    def test_group_member_dual_cloud(self):
        result = classify_group_member_cloud_affiliation("社區商家兼物業服務商家")
        self.assertEqual(result["cloud_affiliations"], ["business_cloud", "property_cloud"])

    def test_case_query_requires_source_refs(self):
        candidate = build_property_cloud_candidate(intent_text="物業案例查詢")
        self.assertEqual(candidate["STATE"], "HOLD")
        self.assertIn("source_refs", candidate["missing_fields"])

    def test_case_query_with_sources_passes_candidate(self):
        candidate = build_property_cloud_candidate(
            intent_text="物業案例查詢",
            source_refs=["law_ref:apartment_building_act", "case_ref:community_dispute"]
        )
        self.assertEqual(candidate["STATE"], "PASS_CANDIDATE")
        self.assertFalse(candidate["formal_legal_advice"])
        self.assertIn("eight_d_packet", candidate)

    def test_excellent_community_application_requires_evidence(self):
        candidate = build_property_cloud_candidate(intent_text="優良社區申報")
        self.assertEqual(candidate["STATE"], "HOLD")
        self.assertIn("evidence_refs", candidate["missing_fields"])

    def test_hard_risk_blocks(self):
        candidate = build_property_cloud_candidate(
            intent_text="正式提出法律意見並申報",
            source_refs=["law_ref:x"],
            requested_actions=["formal_legal_advice", "formal_submission"]
        )
        self.assertEqual(candidate["STATE"], "BLOCK")
        self.assertIn("formal_legal_advice", candidate["blocked_actions"])
        self.assertIn("formal_submission", candidate["blocked_actions"])

    def test_block_response_uses_rookie_message(self):
        candidate = build_property_cloud_candidate(
            intent_text="正式法律意見",
            source_refs=["law_ref:x"],
            requested_actions=["formal_legal_advice"]
        )
        response = render_property_cloud_member_response(candidate)
        self.assertEqual(response["member_facing_message"], ROOKIE_MESSAGE)

    def test_8d_packet_has_dual_cloud_affiliation(self):
        candidate = build_property_cloud_candidate(
            intent_text="團體會員雙雲掛接",
            group_member_nature="社區商家兼物業服務商家"
        )
        packet = candidate["eight_d_packet"]
        self.assertEqual(packet["d8_envelope"]["decision_authority"], "total_field")
        self.assertEqual(packet["d3_coordinate"]["cloud_affiliations"], ["business_cloud", "property_cloud"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
