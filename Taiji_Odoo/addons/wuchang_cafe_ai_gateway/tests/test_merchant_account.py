from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestWuchangCafeMerchantAccount(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.merchant_user = cls.env["res.users"].create(
            {
                "name": "商家權限測試使用者",
                "login": "merchant-access-contract-test@example.invalid",
                "company_id": cls.company.id,
                "company_ids": [Command.set([cls.company.id])],
                "groups_id": [Command.set([cls.env.ref("base.group_portal").id])],
            }
        )
        cls.account = cls.env["wuchang.cafe.merchant.account"].create(
            {
                "name": "咖啡館店務測試帳號",
                "user_id": cls.merchant_user.id,
                "company_id": cls.company.id,
                "role_profile": "manager",
            }
        )

    def test_apply_access_stays_inside_cafe_realm(self):
        self.account.action_apply_access()

        self.assertEqual(self.account.access_state, "active")
        self.assertTrue(
            self.merchant_user.has_group(
                "wuchang_cafe_ai_gateway.group_wuchang_cafe_merchant_viewer"
            )
        )
        self.assertTrue(
            self.merchant_user.has_group(
                "wuchang_cafe_ai_gateway.group_wuchang_cafe_merchant_operator"
            )
        )
        self.assertTrue(
            self.merchant_user.has_group(
                "wuchang_cafe_ai_gateway.group_wuchang_cafe_merchant_manager"
            )
        )
        self.assertFalse(
            self.merchant_user.has_group("point_of_sale.group_pos_user")
        )
        self.assertFalse(
            self.merchant_user.has_group("point_of_sale.group_pos_manager")
        )
        self.assertTrue(self.merchant_user.share)
        self.assertTrue(self.merchant_user.has_group("base.group_portal"))
        self.assertFalse(self.merchant_user.has_group("base.group_user"))
        self.assertEqual(self.account.member_personal_data_access, "denied")
        self.assertEqual(self.account.ai_resource_policy, "adaptive_total_field")
        self.assertEqual(self.account.founder_compute_access, "quota_governed")

    def test_google_signup_template_is_portal_only(self):
        template_id = int(
            self.env["ir.config_parameter"].sudo().get_param(
                "base.template_portal_user_id"
            )
        )
        template = self.env["res.users"].sudo().browse(template_id)
        self.assertEqual(
            template,
            self.env.ref("wuchang_cafe_ai_gateway.user_wuchang_portal_template"),
        )
        self.assertTrue(template.share)
        self.assertTrue(template.has_group("base.group_portal"))
        self.assertFalse(template.has_group("base.group_user"))
        self.assertFalse(template.has_group("base.group_system"))

        oauth_user = template.with_context(no_reset_password=True).copy(
            {
                "name": "Google 入口使用者測試",
                "login": "google-portal-contract-test@example.invalid",
                "active": True,
            }
        )
        self.assertTrue(oauth_user.share)
        self.assertTrue(oauth_user.has_group("base.group_portal"))
        self.assertFalse(oauth_user.has_group("base.group_user"))
        self.assertFalse(oauth_user.has_group("base.group_system"))

    def test_merchant_cannot_promote_own_access(self):
        self.account.action_apply_access()
        with self.assertRaises(AccessError):
            self.account.with_user(self.merchant_user).action_apply_access()

    def test_merchant_cannot_enter_backend_models(self):
        self.account.action_apply_access()
        with self.assertRaises(AccessError):
            self.env["wuchang.cafe.gateway"].with_user(self.merchant_user).create(
                {"name": "越權閘道", "store_node_ref": "store:forbidden"}
            )
        with self.assertRaises(AccessError):
            self.env["wuchang.cafe.ai.eventbook"].with_user(self.merchant_user).search([])
        with self.assertRaises(AccessError):
            self.env["wuchang.ai.compute.binding"].with_user(
                self.merchant_user
            ).create(
                {
                    "name": "越權算力",
                    "user_id": self.merchant_user.id,
                    "natural_identity_packet_ref": "8d:forbidden",
                    "provider_kind": "gemini",
                    "account_ref_sha256": "f" * 64,
                    "credential_vault_ref": "vault:forbidden",
                }
            )

    def test_internal_non_admin_cannot_use_member_ai_handshake(self):
        internal_user = self.env["res.users"].create(
            {
                "name": "非創辦人內部使用者",
                "login": "internal-handshake-test@example.invalid",
                "company_id": self.company.id,
                "company_ids": [Command.set([self.company.id])],
                "groups_id": [Command.set([self.env.ref("base.group_user").id])],
            }
        )
        with self.assertRaises(AccessError):
            self.env[
                "wuchang.cafe.merchant.ai.handshake.service"
            ].with_user(internal_user).execute_v23(text="我要一杯拿鐵")

    def test_member_personal_data_access_cannot_be_enabled(self):
        with self.assertRaises(AccessError):
            self.account.write({"member_personal_data_access": "allowed"})

    def test_account_is_disabled_instead_of_deleted(self):
        with self.assertRaises(AccessError):
            self.account.unlink()

    def test_ai_proposal_never_creates_pos_order_or_payment(self):
        gateway = self.env["wuchang.cafe.gateway"].create(
            {
                "name": "點餐提案測試閘道",
                "store_node_ref": "store:test",
            }
        )
        proposal = self.env["wuchang.cafe.order.proposal"].create(
            {
                "name": "測試提案",
                "gateway_id": gateway.id,
                "proposal_text": "一杯熱美式，不加糖",
                "total_amount_preview": 80,
            }
        )
        pos_order_count = self.env["pos.order"].search_count([])

        proposal.action_staff_confirm()

        self.assertEqual(proposal.state, "staff_confirmed")
        self.assertTrue(proposal.evidence_hash)
        self.assertTrue(proposal.formal_payment_forbidden)
        self.assertTrue(proposal.formal_redemption_forbidden)
        self.assertTrue(proposal.auto_order_forbidden)
        self.assertEqual(self.env["pos.order"].search_count([]), pos_order_count)

    def test_ai_proposal_rejects_member_plaintext(self):
        gateway = self.env["wuchang.cafe.gateway"].create(
            {
                "name": "個資邊界測試閘道",
                "store_node_ref": "store:privacy-test",
            }
        )
        with self.assertRaises(ValidationError):
            self.env["wuchang.cafe.order.proposal"].create(
                {
                    "name": "不合法提案",
                    "gateway_id": gateway.id,
                    "member_packet_ref": "person@example.invalid",
                }
            )

    def test_8dadi_merchant_ai_handshake_is_byo_and_no_effect(self):
        self.account.action_apply_access()
        identity_ref = "8d:natural-person:test-owner"
        self.env["wuchang.ai.compute.binding"].create(
            {
                "name": "會員 Gemini 算力",
                "user_id": self.merchant_user.id,
                "natural_identity_packet_ref": identity_ref,
                "provider_kind": "gemini",
                "account_ref_sha256": "a" * 64,
                "credential_vault_ref": "vault:test/gemini/primary",
            }
        )
        second_login = self.env["res.users"].create(
            {
                "name": "同一自然人第二登入帳號",
                "login": "same-natural-person-second@example.invalid",
                "company_id": self.company.id,
                "company_ids": [Command.set([self.company.id])],
                "groups_id": [Command.set([self.env.ref("base.group_portal").id])],
            }
        )
        self.env["wuchang.ai.compute.binding"].create(
            {
                "name": "會員 OpenAI 備援算力",
                "user_id": second_login.id,
                "natural_identity_packet_ref": identity_ref,
                "provider_kind": "openai",
                "account_ref_sha256": "b" * 64,
                "credential_vault_ref": "vault:test/openai/secondary",
                "priority": 200,
            }
        )
        pos_config = self.env["pos.config"].search([], limit=1)
        gateway = self.env["wuchang.cafe.gateway"].create(
            {
                "name": "聊國咖啡館握手測試",
                "store_node_ref": "liaoguo_main_store",
                "pos_config_id": pos_config.id,
                "seat_capacity_verified": False,
            }
        )
        pos_order_count = self.env["pos.order"].search_count([])
        response = self.env[
            "wuchang.cafe.merchant.ai.handshake.service"
        ].with_user(self.merchant_user).execute_v23(
            text="小J我要去聊國咖啡先幫我看看有沒有位子點一杯拿鐵我10分後到",
            store_ref=gateway.store_node_ref,
        )

        self.assertEqual(response["d2_state"]["party_size"], 1)
        self.assertEqual(response["d2_state"]["eta_minutes"], 10)
        self.assertEqual(
            response["d2_state"]["seat"]["state"],
            "HOLD_SEAT_SOURCE_ALIGNMENT_REQUIRED",
        )
        self.assertFalse(response["d5_execution"]["pos_order_created"])
        self.assertFalse(response["d5_execution"]["payment_captured"])
        self.assertFalse(response["d7_risk"]["founder_gpu_access"])
        self.assertFalse(response["d7_risk"]["founder_api_quota_access"])
        self.assertEqual(response["bindings"]["llm_compute_source_count"], 2)
        self.assertEqual(response["bindings"]["provider_counts"]["gemini"], 1)
        self.assertEqual(response["bindings"]["provider_counts"]["openai"], 1)
        self.assertTrue(response["bindings"]["same_natural_identity_multi_account"])
        self.assertEqual(self.env["pos.order"].search_count([]), pos_order_count)
        self.assertNotIn("小J我要去聊國咖啡", str(response))

    def test_handshake_rejects_bad_numbers_by_bounding_to_safe_values(self):
        parsed = self.env[
            "wuchang.cafe.merchant.ai.handshake.service"
        ]._parse_request(
            "我要一杯拿鐵",
            party_size="不是數字",
            eta_minutes={"不合法": True},
        )
        self.assertEqual(parsed["party_size"], 1)
        self.assertIsNone(parsed["eta_minutes"])
