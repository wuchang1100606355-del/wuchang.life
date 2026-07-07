from __future__ import annotations

import importlib.util
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODULE_PATH = os.path.join(
    ROOT,
    "Taiji_Odoo",
    "addons",
    "wuchang_cafe_ai_gateway",
    "services",
    "cafe_business_onboarding.py",
)

spec = importlib.util.spec_from_file_location("cafe_business_onboarding_under_test", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)

build_cafe_business_onboarding_candidate = module.build_cafe_business_onboarding_candidate
run_cafe_business_onboarding = module.run_cafe_business_onboarding


BUSINESS_INFO = {
    "business_name_ref": "business_name_ref:wuchang_cafe_candidate",
    "store_kind": "cafe",
    "service_area_ref": "service_area_ref:wuchang",
}


class CafeBusinessOnboardingFinalFormTests(unittest.TestCase):
    def test_complete_refs_create_pass_candidate_packet(self):
        result = run_cafe_business_onboarding(
            responsible_person_ref="member_ref:owner",
            organization_ref="organization_ref:wuchang_cafe",
            business_info=BUSINESS_INFO,
        )

        self.assertEqual(result["STATE"], "PASS_CANDIDATE")
        candidate = result["CANDIDATE"]
        self.assertFalse(candidate["production_activation_ready"])
        self.assertIn("merchant_8d_7d_packet", candidate)
        self.assertIn("adi_5d_ref", candidate)
        self.assertIn("tenant_profile_candidate", candidate)
        self.assertIn("service_profile_candidate", candidate)
        self.assertIn("container_config_candidate", candidate)
        self.assertIn("url_routing_candidate", candidate)
        self.assertEqual(candidate["merchant_8d_7d_packet"]["d1_intent"], "cafe_business_onboarding")

    def test_missing_responsible_person_holds(self):
        candidate = build_cafe_business_onboarding_candidate(
            responsible_person_ref="",
            organization_ref="organization_ref:wuchang_cafe",
            business_info=BUSINESS_INFO,
        )
        decision = candidate["total_field_candidate_decision"]
        self.assertEqual(decision["decision"], "HOLD")
        self.assertIn("responsible_person_ref", decision["missing_fields"])

    def test_missing_business_info_holds(self):
        candidate = build_cafe_business_onboarding_candidate(
            responsible_person_ref="member_ref:owner",
            organization_ref="organization_ref:wuchang_cafe",
            business_info={},
        )
        decision = candidate["total_field_candidate_decision"]
        self.assertEqual(decision["decision"], "HOLD")
        self.assertIn("business_info", decision["missing_fields"])

    def test_production_activation_request_blocks(self):
        candidate = build_cafe_business_onboarding_candidate(
            responsible_person_ref="member_ref:owner",
            organization_ref="organization_ref:wuchang_cafe",
            business_info=BUSINESS_INFO,
            requested_actions=["production_activation"],
        )
        decision = candidate["total_field_candidate_decision"]
        self.assertEqual(decision["decision"], "BLOCK")
        self.assertIn("production_activation", decision["blocked_actions"])
        self.assertFalse(candidate["production_activation_ready"])

    def test_db_write_deploy_restart_flags_block(self):
        candidate = build_cafe_business_onboarding_candidate(
            responsible_person_ref="member_ref:owner",
            organization_ref="organization_ref:wuchang_cafe",
            business_info=BUSINESS_INFO,
            requested_actions=["db_write", "deploy", "restart"],
        )
        decision = candidate["total_field_candidate_decision"]
        self.assertEqual(decision["decision"], "BLOCK")
        self.assertIn("db_write", decision["blocked_actions"])
        self.assertIn("deploy", decision["blocked_actions"])
        self.assertIn("restart", decision["blocked_actions"])

    def test_human_response_is_member_readable(self):
        result = run_cafe_business_onboarding(
            responsible_person_ref="member_ref:owner",
            organization_ref="organization_ref:wuchang_cafe",
            business_info=BUSINESS_INFO,
        )
        response = result["HUMAN_RESPONSE"]
        self.assertEqual(response["decision"], "PASS_CANDIDATE")
        self.assertIn("商家入場候選封包", response["member_facing_message"])
        self.assertFalse(response["production_activation_ready"])

    def test_packet_never_creates_live_container_or_route(self):
        candidate = build_cafe_business_onboarding_candidate(
            responsible_person_ref="member_ref:owner",
            organization_ref="organization_ref:wuchang_cafe",
            business_info=BUSINESS_INFO,
        )
        self.assertFalse(candidate["container_config_candidate"]["create_container"])
        self.assertFalse(candidate["container_config_candidate"]["restart"])
        self.assertFalse(candidate["container_config_candidate"]["deploy"])
        self.assertFalse(candidate["url_routing_candidate"]["create_live_route"])
        self.assertFalse(candidate["url_routing_candidate"]["router_write"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
