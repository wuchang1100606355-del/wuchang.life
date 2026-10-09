from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "wuchang_menu_batch")
class TestMenuBatch(TransactionCase):
    """Real ORM checks on a disposable, empty Odoo database only."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param("wuchang_member_registration.total_field_evidence_root", "/tmp/menu-batch-test-evidence")
        cls.user = cls.env.ref("base.user_admin")
        cls.user.groups_id |= cls.env.ref("wuchang_member_registration.group_wuchang_member_admin")
        cls.products = cls.env["product.template"].create([
            {"name": "招牌咖啡", "list_price": 85, "available_in_pos": True, "company_id": cls.env.company.id},
            {"name": "特調咖啡", "list_price": 75, "available_in_pos": True, "company_id": cls.env.company.id},
        ])
        cls.batch = cls.env["wuchang.member.group.registration.batch"].with_user(cls.user).create({
            "name": "隔離菜單驗收", "expires_at": fields.Datetime.now() + timedelta(hours=1),
            "business_onboarding_enabled": True, "business_onboarding_state": "operational_ready",
            "menu_company_id": cls.env.company.id, "responsible_menu_reviewer_user_id": cls.user.id,
            "responsible_person_ref": "person:isolated-reviewer", "store_ref": "store:isolated-cafe",
        })
        cls.user.groups_id |= cls.env.ref("wuchang_cafe_menu_options.group_wuchang_cafe_menu_responsible")

    def wizard(self, **overrides):
        values = {"product_ids": [(6, 0, self.products.ids)], "operation": "set_price", "price": 90}
        values.update(overrides)
        return self.env["wuchang.cafe.menu.batch.wizard"].with_user(self.user).create(values)

    def requests(self, wizard):
        action = wizard.action_submit()
        return self.env[action["res_model"]].with_user(self.user).search(action["domain"])

    def test_preview_submit_approval_and_reversal(self):
        wizard = self.wizard()
        wizard.action_preview()
        self.assertIn("招牌咖啡", wizard.preview_html)
        self.assertEqual(self.products.mapped("list_price"), [85, 75])
        requests = self.requests(wizard)
        self.assertEqual(len(requests), 2)
        self.assertEqual(self.products.mapped("list_price"), [85, 75])
        requests.action_responsible_approve()
        self.assertEqual(self.products.mapped("list_price"), [85, 75])
        requests.action_responsible_apply()
        self.products.invalidate_recordset()
        self.assertEqual(self.products.mapped("list_price"), [90, 90])
        for request in requests:
            action = request.action_prepare_reversal()
            reverse = self.env[request._name].with_user(self.user).browse(action["res_id"])
            reverse.action_responsible_approve()
            reverse.action_responsible_apply()
            self.assertEqual(request.state, "applied")
        self.products.invalidate_recordset()
        self.assertEqual(self.products.mapped("list_price"), [85, 75])

    def test_stale_preview_and_modified_input(self):
        wizard = self.wizard()
        wizard.action_preview()
        self.products[:1].with_user(self.user).write({"list_price": 86})
        with self.assertRaises(UserError), self.cr.savepoint():
            wizard.action_submit()
        wizard.write({"price": 91})
        self.assertFalse(wizard.preview_sha256)
        with self.assertRaises(UserError), self.cr.savepoint():
            wizard.action_submit()

    def test_client_context_cannot_forge_preview_or_candidate_evidence(self):
        wizard = self.wizard()
        with self.assertRaises(UserError), self.cr.savepoint():
            wizard.with_context(wuchang_batch_preview_write=True).write({"preview_sha256": "a" * 64})
        wizard.action_preview()
        requests = self.requests(wizard)
        with self.assertRaises(UserError), self.cr.savepoint():
            requests.with_context(wuchang_menu_request_internal_write=True).write({"state": "approved"})

    def test_zero_price_repeated_submission_and_apply(self):
        wizard = self.wizard(price=0)
        wizard.action_preview()
        requests = self.requests(wizard)
        with self.assertRaises(UserError), self.cr.savepoint():
            wizard.action_submit()
        requests.action_responsible_approve()
        requests.action_responsible_apply()
        self.products.invalidate_recordset()
        self.assertEqual(self.products.mapped("list_price"), [0, 0])
        with self.assertRaises(UserError), self.cr.savepoint():
            requests.action_responsible_apply()

    def test_reversal_refuses_newer_product_and_keeps_evidence(self):
        wizard = self.wizard()
        wizard.action_preview()
        requests = self.requests(wizard)
        requests.action_responsible_approve()
        requests.action_responsible_apply()
        self.products[:1].with_user(self.user).write({"list_price": 100})
        with self.assertRaises(UserError), self.cr.savepoint():
            requests.filtered(lambda r: r.product_template_id == self.products[:1]).action_prepare_reversal()
        self.assertTrue(all(r.state == "applied" for r in requests))

    def test_cross_company_product_is_blocked(self):
        other = self.env["res.company"].create({"name": "隔離其他公司"})
        # Fixture construction only; no production account or company is created.
        self.products[:1].sudo().with_context(wuchang_menu_internal_write=True).write({"company_id": other.id})
        wizard = self.wizard()
        with self.assertRaises(UserError), self.cr.savepoint():
            wizard.action_preview()

    def test_pause_archive_reversal_preserves_paused_state(self):
        self.products.with_user(self.user).write({"available_in_pos": False})
        wizard = self.wizard(operation="archive")
        wizard.action_preview()
        requests = self.requests(wizard)
        requests.action_responsible_approve()
        requests.action_responsible_apply()
        for request in requests:
            action = request.action_prepare_reversal()
            reverse = self.env[request._name].with_user(self.user).browse(action["res_id"])
            reverse.action_responsible_approve()
            reverse.action_responsible_apply()
        self.products.invalidate_recordset()
        self.assertTrue(all(self.products.mapped("active")))
        self.assertFalse(any(self.products.mapped("available_in_pos")))

    def test_noop_and_stale_approved_candidate(self):
        wizard = self.wizard(product_ids=[(6, 0, self.products[:1].ids)], price=85)
        wizard.action_preview()
        self.assertEqual(wizard.changed_count, 0)
        with self.assertRaises(UserError), self.cr.savepoint():
            wizard.action_submit()
        wizard = self.wizard()
        wizard.action_preview()
        requests = self.requests(wizard)
        requests.action_responsible_approve()
        self.products[:1].with_user(self.user).write({"list_price": 86})
        with self.assertRaises(UserError), self.cr.savepoint():
            requests.action_responsible_apply()
        self.products.invalidate_recordset()
        self.assertEqual(self.products.mapped("list_price"), [86, 75])

    def test_single_item_archive_only_creates_review_candidate(self):
        action = self.products[:1].with_user(self.user).action_wuchang_menu_archive()
        request = self.env[action["res_model"]].with_user(self.user).browse(action["res_id"])
        self.assertEqual(request.state, "pending_responsible_review")
        self.products.invalidate_recordset()
        self.assertTrue(all(self.products.mapped("active")))

    def test_context_defaults_cannot_preset_review_state(self):
        wizard = self.env["wuchang.cafe.menu.batch.wizard"].with_user(self.user).with_context(
            default_submitted=True, default_preview_sha256="a" * 64).create({
                "product_ids": [(6, 0, self.products.ids)], "operation": "pause"})
        self.assertFalse(wizard.submitted)
        self.assertFalse(wizard.preview_sha256)
        request = self.env["wuchang.cafe.menu.change.request"].with_user(self.user).with_context(
            default_state="approved", default_candidate_sha256="a" * 64).create({
                "origin": "merchant_manager", "group_batch_id": self.batch.id,
                "product_template_id": self.products[:1].id, "change_price": True, "proposed_list_price": 90})
        self.assertEqual(request.state, "draft")
        self.assertFalse(request.candidate_sha256)
