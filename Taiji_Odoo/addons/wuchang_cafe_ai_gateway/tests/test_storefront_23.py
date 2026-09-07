from odoo.tests.common import TransactionCase

from ..controllers.main import _ordering_body, _xiaoj_display_page
from ..services.storefront_23 import (
    _safe_flair,
    build_storefront_flair,
    build_storefront_response,
    confirm_storefront_preview,
    extract_order_preview,
)
from ..services.merchant_capability_service import (
    build_group_member_intent_field_questionnaire,
)


class TestStorefront23(TransactionCase):
    def test_drallion_and_hdmi_are_separate_projection_surfaces(self):
        ordering = _ordering_body()
        display = _xiaoj_display_page()
        self.assertIn("/wuchang/xiaoj/display", ordering)
        self.assertIn("wuchang-xiaoj-display-v23", ordering)
        self.assertIn("wuchang-xiaoj-display-v23", display)
        self.assertIn("顯示投影無交易權限", display)
        self.assertIn("data-display-emotion", display)
        self.assertIn("emotionByState", ordering)
        self.assertIn("clear:{rate:.90,pitch:1.00}", ordering)
        self.assertNotIn("/wuchang/xiaoj/api/store-confirm", display)
        self.assertNotIn("/wuchang/xiaoj/api/store-chat", display)

    def test_display_outfits_do_not_define_system_state(self):
        display = _xiaoj_display_page()
        for asset in (
            "xiaoj-white-tech.png",
            "xiaoj-barista.png",
            "xiaoj-event-black.png",
            "xiaoj-community-gray.png",
        ):
            self.assertIn(asset, display)
        self.assertNotIn("GT Canonical SHA-256", display)
        self.assertNotIn("taiji01", display)

    def test_order_facts_are_deterministic(self):
        lines = extract_order_preview("兩杯拿鐵和一份烤貝果")
        self.assertEqual([(line["name"], line["quantity"], line["subtotal"]) for line in lines], [
            ("上品拿鐵咖啡", 2, 180),
            ("烤貝果", 1, 55),
        ])

    def test_model_failure_keeps_safe_fallback_and_no_effect(self):
        payload = build_storefront_response(
            "我10分鐘後到，看看有沒有位子，幫我準備一杯美式",
            model_endpoint="http://127.0.0.1:1/unavailable",
        )
        self.assertEqual(payload["language_source"], "確定性備援")
        self.assertEqual(payload["frozen_facts"]["total"], 90)
        self.assertEqual(payload["frozen_facts"]["seat_state"], "未觀測")
        self.assertFalse(payload["frozen_facts"]["order_committed"])
        self.assertFalse(payload["frozen_facts"]["payment_captured"])
        self.assertTrue(payload["customer_confirmation"]["required"])
        self.assertEqual(payload["customer_confirmation"]["state"], "AWAITING_CUSTOMER_TOUCH")
        d6 = payload["eight_dimensional_receipt"]["D6_生成式傳輸"]
        self.assertIn("未啟用（NOT_INVOKED）", d6)
        self.assertIn("目標基底", d6)
        self.assertNotIn("模型只潤飾語氣", d6)

    def test_model_language_cannot_claim_store_effect(self):
        self.assertFalse(_safe_flair("我們已幫您預訂，稍後確認座位。"))
        self.assertFalse(_safe_flair("Your seat is ready"))
        self.assertEqual(_safe_flair("煩惱先打烊，香氣準備上班。"), "煩惱先打烊，香氣準備上班。")

    def test_touch_confirmation_is_explicit_and_still_has_no_order_effect(self):
        text = "兩杯拿鐵和一份烤貝果"
        preview = build_storefront_response(text, model_endpoint="http://127.0.0.1:1/unavailable")
        refused = confirm_storefront_preview(text, preview["customer_confirmation"]["preview_ref"], False, True)
        self.assertFalse(refused["customer_touch_confirmed"])
        voice_missing = confirm_storefront_preview(text, preview["customer_confirmation"]["preview_ref"], True, False)
        self.assertFalse(voice_missing["customer_touch_confirmed"])
        confirmed = confirm_storefront_preview(text, preview["customer_confirmation"]["preview_ref"], True, True)
        self.assertTrue(confirmed["customer_touch_confirmed"])
        self.assertFalse(confirmed["effects"]["order_written"])
        self.assertFalse(confirmed["effects"]["payment_written"])
        self.assertIn(
            "未啟用（NOT_INVOKED）",
            confirmed["eight_dimensional_receipt"]["D6_生成式傳輸"],
        )

    def test_questionnaire_keeps_audiovisual_role_in_d5_and_true_d6_contract(self):
        payload = build_group_member_intent_field_questionnaire(field_type="merchant")
        sections = {item["code"]: item for item in payload["sections"]}
        self.assertIn("xiaoj_projection_role_ref", sections["d5_execution_policy"]["fields"])
        self.assertNotIn("xiaoj_projection_role_ref", sections["d6_generative_transmission"]["fields"])
        self.assertEqual(
            sections["d6_generative_transmission"]["fields"],
            [
                "target_base_state_ref",
                "minimum_required_delta_ref",
                "reference_refs",
                "coordinate_refs",
                "reconstruction_rule_refs",
                "verification_rule_refs",
            ],
        )

    def test_optional_model_appearance_cannot_change_facts(self):
        payload = build_storefront_flair(
            "兩杯拿鐵",
            model_endpoint="http://127.0.0.1:1/unavailable",
        )
        self.assertEqual(payload["state"], "DETERMINISTIC_APPEARANCE_RETAINED")
        self.assertFalse(payload["effects"]["facts_changed"])
