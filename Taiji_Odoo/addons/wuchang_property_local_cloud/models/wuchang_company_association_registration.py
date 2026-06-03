from odoo import models, fields


class ResCompanyAssociationRegistration(models.Model):
    _inherit = "res.company"

    association_registration_no = fields.Char("社區發展協會立案字號")
    association_government_authority = fields.Char("主管機關")
    association_registered_address = fields.Char("協會登記地址")
    association_registered_phone = fields.Char("協會登記電話")
