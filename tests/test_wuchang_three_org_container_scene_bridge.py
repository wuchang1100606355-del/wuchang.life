from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.total_field.wuchang_three_org_container_scene_bridge import (  # noqa: E402
    ROOKIE_MESSAGE,
    build_three_org_scene_candidate,
    classify_scene,
    load_three_org_scene_map,
    render_three_org_scene_response,
    resolve_scene_profile,
)


class WuchangThreeOrgContainerSceneBridgeTests(unittest.TestCase):
    def test_policy_is_safe(self):
        data = load_three_org_scene_map()
        self.assertFalse(data["policy"]["live_container_switch"])
        self.assertFalse(data["policy"]["docker_compose_up"])
        self.assertFalse(data["policy"]["db_write"])
        self.assertFalse(data["policy"]["deploy"])
        self.assertFalse(data["policy"]["restart"])
        self.assertEqual(
            data["odoo_community_core"]["supporting_modules"],
            ["business_organization", "property_organization", "public_welfare_organization"],
        )

    def test_classify_scenes(self):
        self.assertEqual(classify_scene("商業雲票券幸福幣"), "business_scene")
        self.assertEqual(classify_scene("物業雲公道伯法令"), "property_scene")
        self.assertEqual(classify_scene("協會公益志工許願樹"), "association_scene")

    def test_business_scene_shows_property_and_association(self):
        profile = resolve_scene_profile("business_scene")
        self.assertEqual(profile["primary_module"], "business_organization")
        self.assertIn("property_organization", profile["visible_modules"])
        self.assertIn("public_welfare_organization", profile["visible_modules"])
        self.assertFalse(profile["live_container_action"])

    def test_property_scene_uses_property_container_candidate(self):
        profile = resolve_scene_profile("property_scene")
        self.assertEqual(profile["container_profile_candidate"], "container_profile:property_cloud_candidate")
        self.assertEqual(profile["primary_module"], "property_organization")

    def test_association_scene_uses_public_welfare_module(self):
        profile = resolve_scene_profile("association_scene")
        self.assertEqual(profile["primary_module"], "public_welfare_organization")
        self.assertEqual(profile["container_profile_candidate"], "container_profile:association_public_welfare_candidate")

    def test_build_business_landing_candidate(self):
        candidate = build_three_org_scene_candidate(intent_text="商業落地展示物業及協會")
        self.assertEqual(candidate["STATE"], "PASS_CANDIDATE")
        self.assertEqual(candidate["target_scene"], "business_scene")
        self.assertTrue(candidate["business_landing_showcases_property_and_association"])
        self.assertFalse(candidate["live_container_switch"])
        self.assertIn("eight_d_packet", candidate)

    def test_hard_risk_blocks_live_container_switch(self):
        candidate = build_three_org_scene_candidate(
            intent_text="直接換容器啟用商業場景",
            requested_actions=["live_container_switch", "docker_compose_up"]
        )
        self.assertEqual(candidate["STATE"], "BLOCK")
        self.assertIn("live_container_switch", candidate["blocked_actions"])
        self.assertIn("docker_compose_up", candidate["blocked_actions"])
        response = render_three_org_scene_response(candidate)
        self.assertEqual(response["member_facing_message"], ROOKIE_MESSAGE)

    def test_8d_packet_has_total_field_authority(self):
        candidate = build_three_org_scene_candidate(intent_text="物業雲場景")
        packet = candidate["eight_d_packet"]
        self.assertEqual(packet["d8_envelope"]["decision_authority"], "total_field")
        self.assertTrue(packet["d8_envelope"]["owner_admin_review_required"])
        self.assertTrue(packet["d7_risk"]["live_container_switch_blocked"])
        self.assertTrue(packet["d7_risk"]["docker_action_blocked"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
