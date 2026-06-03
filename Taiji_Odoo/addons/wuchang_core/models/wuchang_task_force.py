from odoo import models, fields, api

class WuchangChronosDevice(models.Model):
    _name = "wuchang.chronos.device"
    _description = "時光系 AI 增幅裝置"

    name = fields.Char(string="裝置序號", required=True, default=lambda self: "CHRONOS-" + fields.Datetime.now().strftime("%Y%m%d%H%M%S"))
    owner_name = fields.Char(string="領取人/單位")
    status = fields.Selection([
        ("draft", "庫存中"),
        ("reserved", "預定中"),
        ("distributed", "已發送"),
        ("active", "運作中"),
        ("self_destructed", "已自毀"),
    ], string="狀態", default="draft")
    activation_time = fields.Datetime(string="啟用時間")
    is_helmet_included = fields.Boolean(string="含專利頭盔", default=True)
    note = fields.Text(string="備註", default="主人喝咖啡，AI帶你飛。")

class WuchangLifeCovenant(models.Model):
    _name = "wuchang.life.covenant"
    _description = "五常生活公約"

    name = fields.Char(string="條款名稱", required=True)
    content = fields.Text(string="條款內容", required=True)
    is_active = fields.Boolean(string="生效中", default=True)
    penalty = fields.Char(string="違反罰則", default="敲頭")
