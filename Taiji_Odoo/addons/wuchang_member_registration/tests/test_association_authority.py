from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAssociationMemberAuthority(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.registration_model = cls.env["wuchang.member.registration"]
        cls.cafe_only_user = cls.env["res.users"].create(
            {
                "name": "咖啡館單域測試使用者",
                "login": "cafe-only-member-boundary@example.invalid",
                "company_id": cls.env.company.id,
                "company_ids": [Command.set([cls.env.company.id])],
                "groups_id": [
                    Command.set([cls.env.ref("base.group_user").id])
                ],
            }
        )

    def test_association_is_fixed_personal_data_controller(self):
        registration = self.registration_model.create({})

        self.assertEqual(registration.identity_realm, "association_membership")
        self.assertEqual(
            registration.personal_data_controller,
            "wuchang_association",
        )

        with self.assertRaises(ValidationError):
            registration.write({"personal_data_controller": "cafe"})

    def test_cafe_only_internal_user_has_no_member_management_access(self):
        with self.assertRaises(AccessError):
            self.registration_model.with_user(self.cafe_only_user).create({})
