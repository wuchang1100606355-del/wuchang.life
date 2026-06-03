from odoo import models, fields

class WuchangLineUser(models.Model):
    _name = "wuchang.line.user"
    _description = "Wuchang LINE User"
    _rec_name = "display_name"

    display_name = fields.Char(string="Display Name")
    line_user_id = fields.Char(string="LINE User ID", required=True, index=True)
    picture_url = fields.Char(string="Picture URL")
    status_message = fields.Char(string="Status Message")
    raw_profile = fields.Text(string="Raw Profile")
