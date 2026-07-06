from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "Taiji_Odoo/addons/wuchang_member_registration/models/member_registration.py"
CONTROLLER = ROOT / "Taiji_Odoo/addons/wuchang_member_registration/controllers/main.py"
VIEW = ROOT / "Taiji_Odoo/addons/wuchang_member_registration/views/group_member_registration_views.xml"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class CafeBusinessOnboardingFinalFormStaticTest(unittest.TestCase):
    def test_model_generates_required_final_form_outputs(self):
        text = read(MODEL)
        for required in [
            "business_onboarding_enabled",
            "responsible_registration_id",
            "responsible_person_ref",
            "business_name",
            "business_address_ref",
            "service_items_json",
            "line_official_account_ref",
            "odoo_service_ref",
            "pos_config_ref",
            "merchant_state_packet_json",
            "tenant_ref",
            "service_profile_ref",
            "container_config_ref",
            "url_routing_ref",
            "public_page_path",
            "member_entry_path",
            "line_ai_entry_ref",
            "odoo_pos_management_entry_ref",
            "ordering_or_service_entry_path",
            "action_submit_business_onboarding",
            "action_total_field_approve_business_onboarding",
            "CAFE_BUSINESS_8D_7D_MERCHANT_STATE_PACKET",
            "ADI_5D_ABSOLUTE_INDEX",
            "7D_FUNCTIONAL_STATE_LAYER",
            "LOCAL_TOTAL_FIELD",
        ]:
            self.assertIn(required, text)

    def test_controller_has_public_registration_and_auth_approval(self):
        text = read(CONTROLLER)
        for required in [
            '/wuchang/business/onboarding"',
            "/wuchang/business/onboarding/submit",
            "/wuchang/business/onboarding/start",
            "/wuchang/business/onboarding/status/<string:packet_ref>",
            "/wuchang/business/onboarding/<string:packet_ref>/approve",
            'auth="public"',
            'auth="user"',
            "business_onboarding_status_payload",
            "total_field_review_then_operational_ready",
        ]:
            self.assertIn(required, text)

    def test_view_exposes_backend_review_and_service_settings(self):
        text = read(VIEW)
        for required in [
            "Submit Business Onboarding",
            "Approve Business Onboarding",
            "Cafe Business Onboarding",
            "Operational Entry Settings",
            "Merchant 8D+7D State Packet",
            "tenant_ref",
            "service_profile_ref",
            "container_config_ref",
            "url_routing_ref",
        ]:
            self.assertIn(required, text)

    def test_forbidden_drift_is_locked_false(self):
        text = read(MODEL)
        forbidden_false = [
            '"natural_person_container": False',
            '"container_is_business_qualification": False',
            '"legal_business_registration_completed": False',
            '"food_license_completed": False',
            '"tax_registration_completed": False',
            '"payment_contract_completed": False',
            '"payment_capture": False',
            '"formal_order": False',
            '"deploy": False',
            '"restart": False',
        ]
        for required in forbidden_false:
            self.assertIn(required, text)
        self.assertNotIn('"natural_person_container": True', text)
        self.assertNotIn('"container_is_business_qualification": True', text)


if __name__ == "__main__":
    unittest.main()
