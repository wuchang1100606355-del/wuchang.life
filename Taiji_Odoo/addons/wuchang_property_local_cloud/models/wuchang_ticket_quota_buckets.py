from odoo import models, fields, api
from odoo.exceptions import ValidationError


class WuchangGroupCustomerTicketQuotaTotals(models.Model):
    _inherit = "wuchang.group.customer"

    community_coin_ticket_subtotal = fields.Float(
        "社區幣對應折價/商品券小計",
        compute="_compute_ticket_quota_totals"
    )
    self_issued_ticket_subtotal = fields.Float(
        "自發行折價/商品券小計",
        compute="_compute_ticket_quota_totals"
    )
    ticket_quota_grand_total = fields.Float(
        "票券額度合併總計",
        compute="_compute_ticket_quota_totals"
    )

    def _compute_ticket_quota_totals(self):
        Ticket = self.env["wuchang.ticket.opening"]
        for rec in self:
            community_domain = [
                ("quota_account_type", "=", "community_coin_backed"),
                ("state", "!=", "cancelled"),
                "|", "|",
                ("issuer_group_customer_id", "=", rec.id),
                ("issuer_member_id.group_customer_id", "=", rec.id),
                ("target_merchant_id", "=", rec.id),
            ]
            self_issued_domain = [
                ("quota_account_type", "=", "self_issued"),
                ("state", "!=", "cancelled"),
                ("issuer_merchant_id", "=", rec.id),
            ]

            community_total = sum(Ticket.search(community_domain).mapped("total_face_value"))
            self_issued_total = sum(Ticket.search(self_issued_domain).mapped("total_face_value"))

            rec.community_coin_ticket_subtotal = community_total
            rec.self_issued_ticket_subtotal = self_issued_total
            rec.ticket_quota_grand_total = community_total + self_issued_total


class WuchangTicketOpeningQuotaBuckets(models.Model):
    _inherit = "wuchang.ticket.opening"

    quota_account_type = fields.Selection([
        ("community_coin_backed", "社區幣對應折價/商品券"),
        ("self_issued", "自發行折價/商品券"),
    ], string="票券額度類型", required=True, default="community_coin_backed")

    is_quota_limited = fields.Boolean(
        "是否受團體會員一萬元額度限制",
        compute="_compute_quota_bucket_flags"
    )

    quota_bucket_note = fields.Char(
        "額度桶說明",
        compute="_compute_quota_bucket_flags"
    )

    @api.depends("quota_account_type", "issuer_mode")
    def _compute_quota_bucket_flags(self):
        for rec in self:
            rec.is_quota_limited = rec.quota_account_type == "community_coin_backed"
            if rec.quota_account_type == "community_coin_backed":
                rec.quota_bucket_note = "社區幣對應折價/商品券：團體會員每人上限 10,000。"
            elif rec.quota_account_type == "self_issued":
                rec.quota_bucket_note = "自發行折價/商品券：商家自行開設自家票券，不受團體會員 10,000 額度限制。"
            else:
                rec.quota_bucket_note = ""

    @api.onchange("issuer_mode")
    def _onchange_issuer_mode_set_quota_type(self):
        for rec in self:
            if rec.issuer_mode == "merchant_self":
                rec.quota_account_type = "self_issued"
                rec.target_scope = "own_merchant"
            elif rec.issuer_mode == "group_member_universal":
                rec.quota_account_type = "community_coin_backed"
                if rec.target_scope == "own_merchant":
                    rec.target_scope = "all_merchants"

    @api.constrains("issuer_mode", "quota_account_type", "target_scope")
    def _check_quota_bucket_rules(self):
        for rec in self:
            if rec.issuer_mode == "group_member_universal" and rec.quota_account_type != "community_coin_backed":
                raise ValidationError("團體會員開設的票券，必須歸入「社區幣對應折價/商品券」額度桶。")

            if rec.issuer_mode == "merchant_self" and rec.quota_account_type != "self_issued":
                raise ValidationError("商家自行開設的票券，必須歸入「自發行折價/商品券」額度桶。")

            if rec.quota_account_type == "self_issued" and rec.target_scope != "own_merchant":
                raise ValidationError("自發行折價/商品券只能作為商家自家票券。")

            if rec.quota_account_type == "community_coin_backed" and rec.issuer_mode == "merchant_self":
                raise ValidationError("商家自家票券不可歸入社區幣對應額度桶。")
