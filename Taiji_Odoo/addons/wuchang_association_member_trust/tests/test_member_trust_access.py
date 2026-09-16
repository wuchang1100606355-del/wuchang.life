from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user


class TestMemberTrustCompanyIsolation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env["res.company"].create({"name": "Trust Company A"})
        cls.company_b = cls.env["res.company"].create({"name": "Trust Company B"})
        cls.user_a = new_test_user(
            cls.env,
            login="trust-company-a-user",
            groups="base.group_user",
            company_id=cls.company_a.id,
            company_ids=[(6, 0, [cls.company_a.id])],
        )
        tenant_model = cls.env["wuchang.association.merchant.tenant"]
        cls.tenant_a = tenant_model.create(
            {"name": "Tenant A", "company_id": cls.company_a.id}
        )
        cls.tenant_b = tenant_model.create(
            {"name": "Tenant B", "company_id": cls.company_b.id}
        )
        cls.tenant_unassigned = tenant_model.create({"name": "Unassigned Tenant"})

    def test_internal_user_reads_only_active_company(self):
        visible = self.env["wuchang.association.merchant.tenant"].with_user(
            self.user_a
        ).search([])
        self.assertEqual(visible, self.tenant_a)

    def test_internal_user_cannot_open_other_or_unassigned_tenant(self):
        with self.assertRaises(AccessError):
            self.tenant_b.with_user(self.user_a).check_access("read")
        with self.assertRaises(AccessError):
            self.tenant_unassigned.with_user(self.user_a).check_access("read")

    def test_manager_rule_explicitly_allows_cross_company_records(self):
        manager = new_test_user(
            self.env,
            login="trust-association-manager",
            groups="wuchang_association_member_trust.group_wuchang_association_manager",
            company_id=self.company_a.id,
            company_ids=[(6, 0, [self.company_a.id])],
        )
        visible = self.env["wuchang.association.merchant.tenant"].with_user(manager).search([])
        expected = self.tenant_a | self.tenant_b | self.tenant_unassigned
        self.assertTrue(expected <= visible)
