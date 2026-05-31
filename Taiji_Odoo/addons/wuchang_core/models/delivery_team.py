from odoo import models, fields

class WuchangDeliveryTeam(models.Model):
    _name = "wuchang.delivery.team"
    _description = "Wuchang Delivery Team"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    note = fields.Text()
