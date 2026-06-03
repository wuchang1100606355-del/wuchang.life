from odoo import models, fields


class WuchangGroupCustomerPOSPolicy(models.Model):
    _inherit = "wuchang.group.customer"

    pos_accepts_community_coin = fields.Boolean(
        "POS啟用社區幣",
        default=False
    )
    pos_accepts_community_coin_ticket = fields.Boolean(
        "POS啟用社區幣對應折價/商品券",
        default=False
    )
    pos_accepts_self_issued_ticket = fields.Boolean(
        "POS啟用自發行折價/商品券",
        default=True
    )
    pos_policy_mode = fields.Selection([
        ("self_ticket_only", "僅自發行獨立票券"),
        ("community_coin_only", "僅社區幣"),
        ("community_coin_and_ticket", "社區幣與票券皆啟用"),
        ("no_coin_no_ticket", "社區幣與票券皆停用"),
    ], string="POS核銷模式", default="self_ticket_only")

    pos_policy_note = fields.Text("POS政策說明")


class WuchangFieldVerificationDevicePOSPolicy(models.Model):
    _inherit = "wuchang.field.verification.device"

    pos_accepts_community_coin = fields.Boolean(
        "設備啟用社區幣",
        default=False
    )
    pos_accepts_community_coin_ticket = fields.Boolean(
        "設備啟用社區幣對應折價/商品券",
        default=False
    )
    pos_accepts_self_issued_ticket = fields.Boolean(
        "設備啟用自發行折價/商品券",
        default=True
    )
    pos_policy_mode = fields.Selection([
        ("self_ticket_only", "僅自發行獨立票券"),
        ("community_coin_only", "僅社區幣"),
        ("community_coin_and_ticket", "社區幣與票券皆啟用"),
        ("no_coin_no_ticket", "社區幣與票券皆停用"),
    ], string="設備核銷模式", default="self_ticket_only")

    pos_policy_note = fields.Text("設備POS政策說明")
