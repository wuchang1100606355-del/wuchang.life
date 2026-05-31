from odoo import models, fields


class ResCompanyGoogleWorkspace(models.Model):
    _inherit = "res.company"

    google_workspace_domain = fields.Char("Google Workspace 網域")
    google_workspace_super_admin = fields.Char("Google Workspace 超級管理員帳號")
    google_workspace_owner_scope = fields.Selection([
        ("association_main_company", "協會主公司"),
        ("personal", "自然人"),
        ("merchant", "商家/分館"),
        ("other", "其他"),
    ], string="Google Workspace 歸屬", default="association_main_company")
    google_workspace_status = fields.Selection([
        ("not_set", "未設定"),
        ("active", "生效中"),
        ("suspended", "暫停"),
        ("pending", "待確認"),
    ], string="Google Workspace 狀態", default="active")
    google_workspace_note = fields.Text("Google Workspace 說明")
