#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest

from tools.total_field.xiaoj_human_need_router import normalize_roles, route_human_need


class XiaoJHumanNeedRouterTest(unittest.TestCase):
    def test_open_source_local_first_has_no_enterprise_dependency(self) -> None:
        result = route_human_need(
            active_role_refs=["odoo_role_ref:resident"],
            intent="我要看社區公告",
        )
        self.assertEqual(result["state"], "PASS_HUMAN_NEED_ROUTE_CANDIDATE")
        self.assertTrue(result["local_only"])
        self.assertFalse(result["cloud_required"])
        self.assertFalse(result["enterprise_sso_required"])
        self.assertFalse(result["paid_service_required"])
        self.assertFalse(result["kubernetes_required"])
        self.assertFalse(result["execution_allowed"])

    def test_same_person_can_route_different_needs_by_active_roles(self) -> None:
        volunteer = route_human_need(
            active_role_refs=["odoo_role_ref:resident", "odoo_role_ref:volunteer"],
            intent="我今天可以接哪個志工外送任務",
        )
        self.assertEqual(volunteer["state"], "PASS_HUMAN_NEED_ROUTE_CANDIDATE")
        self.assertEqual(volunteer["selected"]["role"], "volunteer")
        self.assertEqual(volunteer["selected"]["need"], "volunteer_task")
        self.assertTrue(volunteer["selected"]["human_confirmation_required"])

        resident = route_human_need(
            active_role_refs=["odoo_role_ref:resident", "odoo_role_ref:volunteer"],
            intent="社區停水公告在哪裡",
        )
        self.assertEqual(resident["state"], "PASS_HUMAN_NEED_ROUTE_CANDIDATE")
        self.assertEqual(resident["selected"]["role"], "resident")
        self.assertEqual(resident["selected"]["need"], "notice")

    def test_ambiguous_multi_role_need_requires_human_choice(self) -> None:
        result = route_human_need(
            active_role_refs=["odoo_role_ref:resident", "odoo_role_ref:unit_owner"],
            intent="我要看管理費帳單",
        )
        self.assertEqual(result["state"], "HOLD_ROLE_OR_NEED_CHOICE_REQUIRED")
        self.assertTrue(result["human_choice_required"])
        self.assertGreaterEqual(len(result["candidate_options"]), 2)

    def test_social_worker_is_human_governance_not_ai_authority(self) -> None:
        result = route_human_need(
            active_role_refs=["odoo_role_ref:social_worker"],
            intent="我要整理今天的訪視與轉介案件",
        )
        self.assertEqual(result["state"], "PASS_HUMAN_NEED_ROUTE_CANDIDATE")
        self.assertEqual(result["selected"]["role"], "social_worker")
        self.assertEqual(result["selected"]["need"], "visit_referral")
        self.assertTrue(result["selected"]["human_confirmation_required"])
        self.assertFalse(result["execution_allowed"])

    def test_caregiver_only_gets_minimum_task_lane(self) -> None:
        result = route_human_need(
            active_role_refs=["odoo_role_ref:caregiver"],
            intent="我要看今天長輩陪同任務",
        )
        self.assertEqual(result["state"], "PASS_HUMAN_NEED_ROUTE_CANDIDATE")
        self.assertEqual(result["selected"]["role"], "caregiver")
        self.assertEqual(result["selected"]["need"], "duty_task")
        self.assertTrue(result["selected"]["human_confirmation_required"])

    def test_role_aliases_are_local_and_deterministic(self) -> None:
        self.assertEqual(
            normalize_roles(
                [
                    "odoo_role_ref:responsible_person",
                    "odoo_role_ref:committee_chair",
                    "odoo_role_ref:property_manager",
                ]
            ),
            [
                "organization_responsible",
                "committee_member",
                "property_staff",
            ],
        )

    def test_unknown_need_does_not_guess(self) -> None:
        result = route_human_need(
            active_role_refs=["odoo_role_ref:resident", "odoo_role_ref:consumer"],
            intent="我有一件很難形容的事情",
        )
        self.assertEqual(result["state"], "HOLD_HUMAN_NEED_AMBIGUOUS")
        self.assertTrue(result["human_choice_required"])

    def test_raw_intent_not_returned(self) -> None:
        raw = "我要查管理費，這段原始文字不應被輸出保存"
        result = route_human_need(
            active_role_refs=["odoo_role_ref:resident"],
            intent=raw,
        )
        encoded = json.dumps(result, ensure_ascii=False)
        self.assertNotIn(raw, encoded)
        self.assertIn("intent_sha256", result)
        self.assertFalse(result["raw_intent_persisted"])


if __name__ == "__main__":
    unittest.main()
