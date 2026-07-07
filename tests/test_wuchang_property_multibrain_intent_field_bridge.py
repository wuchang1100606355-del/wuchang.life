from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.total_field.wuchang_property_multibrain_intent_field_bridge import (  # noqa: E402
    ROOKIE_MESSAGE,
    build_property_multibrain_candidate,
    classify_property_intent,
    load_property_multibrain_map,
    render_property_multibrain_member_response,
    resolve_household_role,
    select_approvers,
)


class WuchangPropertyMultibrainIntentFieldBridgeTests(unittest.TestCase):
    def test_policy_is_safe(self):
        data = load_property_multibrain_map()
        self.assertFalse(data["policy"]["router_write"])
        self.assertFalse(data["policy"]["live_wifi_change"])
        self.assertFalse(data["policy"]["db_write"])
        self.assertFalse(data["policy"]["deploy"])
        self.assertFalse(data["policy"]["restart"])
        self.assertEqual(data["identity_permission_model"]["household"]["default_household_head"], "unit_owner")

    def test_classify_property_intents(self):
        self.assertEqual(classify_property_intent("路由器訪客網路AI登記"), "guest_wifi_registration")
        self.assertEqual(classify_property_intent("郵件物品收領"), "mail_package_receiving")
        self.assertEqual(classify_property_intent("戶長轉移戶內成員"), "household_head_transfer")
        self.assertEqual(classify_property_intent("影音AI大廳迎賓小J"), "visitor_greeting")

    def test_role_mapping_from_pos(self):
        data = load_property_multibrain_map()
        mapping = data["role_ai_mapping_from_pos"]
        self.assertEqual(mapping["pos_store_manager_ai"], "secretary_general_ai")
        self.assertEqual(mapping["pos_responsible_person_ai"], "chairperson_ai")
        self.assertEqual(mapping["pos_order_pickup"], "mail_package_receiving")

    def test_guest_wifi_approver_household(self):
        approvers = select_approvers(intent_type="guest_wifi_registration", registration_target="household")
        self.assertIn("household_head", approvers)
        self.assertIn("unit_owner", approvers)

    def test_visitor_to_committee_approver(self):
        approvers = select_approvers(intent_type="visitor_greeting", registration_target="committee")
        self.assertIn("chairperson", approvers)
        self.assertIn("secretary_general", approvers)

    def test_household_head_defaults_to_unit_owner(self):
        role = resolve_household_role(person_role="unit_owner", is_unit_owner=True)
        self.assertEqual(role["STATE"], "PASS_HOUSEHOLD_HEAD_DEFAULTED_TO_UNIT_OWNER")
        self.assertEqual(role["household_role"], "household_head")

    def test_household_head_transfer_to_member_candidate(self):
        role = resolve_household_role(
            person_role="household_member",
            is_unit_owner=False,
            transfer_requested=True
        )
        self.assertEqual(role["STATE"], "PASS_HOUSEHOLD_HEAD_TRANSFER_CANDIDATE")
        self.assertEqual(role["transfer_to"], "household_member")
        self.assertIn("total_field_pass", role["requires"])

    def test_guest_wifi_candidate_no_router_write(self):
        candidate = build_property_multibrain_candidate(
            intent_text="路由器訪客網路AI登記",
            registration_target="household"
        )
        self.assertEqual(candidate["STATE"], "PASS_CANDIDATE")
        self.assertEqual(candidate["brain"], "router_guest_ai")
        self.assertFalse(candidate["router_write"])
        self.assertFalse(candidate["live_wifi_change"])
        self.assertIn("eight_d_packet", candidate)

    def test_mail_package_receiving_candidate(self):
        candidate = build_property_multibrain_candidate(
            intent_text="郵件物品收領",
            package_known_recipient=True
        )
        self.assertEqual(candidate["STATE"], "PASS_CANDIDATE")
        self.assertEqual(candidate["brain"], "secretary_general_ai")
        self.assertEqual(candidate["device"], "frontdesk_mail_package_node")
        self.assertIn("recipient", candidate["approvers"])

    def test_household_transfer_candidate_uses_chairperson_ai(self):
        candidate = build_property_multibrain_candidate(
            intent_text="戶長轉移戶內成員",
            person_role="household_member",
            transfer_household_head=True
        )
        self.assertEqual(candidate["STATE"], "PASS_CANDIDATE")
        self.assertEqual(candidate["brain"], "chairperson_ai")
        self.assertIn("chairperson_ai", candidate["approvers"])

    def test_hard_risk_blocks_router_write(self):
        candidate = build_property_multibrain_candidate(
            intent_text="路由器訪客網路AI登記",
            requested_actions=["router_write", "live_wifi_change"]
        )
        self.assertEqual(candidate["STATE"], "BLOCK")
        self.assertIn("router_write", candidate["blocked_actions"])
        self.assertIn("live_wifi_change", candidate["blocked_actions"])
        response = render_property_multibrain_member_response(candidate)
        self.assertEqual(response["member_facing_message"], ROOKIE_MESSAGE)

    def test_8d_packet_has_total_field_authority(self):
        candidate = build_property_multibrain_candidate(intent_text="影音AI大廳迎賓小J")
        packet = candidate["eight_d_packet"]
        self.assertEqual(packet["d8_envelope"]["decision_authority"], "total_field")
        self.assertTrue(packet["d8_envelope"]["owner_admin_review_required"])
        self.assertTrue(packet["d7_risk"]["router_write_blocked"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
