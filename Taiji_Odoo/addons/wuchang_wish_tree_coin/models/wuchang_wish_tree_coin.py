from odoo import models, fields, api
from odoo.exceptions import ValidationError


class WuchangWishTreeCoinPolicy(models.Model):
    _name = "wuchang.wish.tree.coin.policy"
    _description = "社區許願樹公益幣撥發政策"
    _rec_name = "name"

    name = fields.Char("政策名稱", required=True)
    grant_frequency = fields.Selection([
        ("quarterly", "每三個月一次"),
        ("manual", "手動"),
    ], string="撥發頻率", default="quarterly", required=True)

    grant_amount = fields.Float("每次撥發公益幣額度", default=0.0)
    state = fields.Selection([
        ("draft", "草稿"),
        ("active", "啟用"),
        ("suspended", "暫停"),
        ("retired", "停用"),
    ], string="狀態", default="active")

    allowed_usage = fields.Text(
        "用途限制",
        default="公益幣僅可捐給審核通過之公益單位或願望牌；不可提領現金、不可購物折抵、不可轉給私人、不可流入未審核項目。"
    )


class WuchangWishTreeTarget(models.Model):
    _name = "wuchang.wish.tree.target"
    _description = "社區許願樹捐贈目標：單位/願望牌"
    _rec_name = "name"

    name = fields.Char("名稱", required=True)
    target_type = fields.Selection([
        ("approved_unit", "審核通過單位"),
        ("wish_card", "審核通過願望牌"),
    ], string="目標類型", required=True)

    related_group_customer_id = fields.Many2one(
        "wuchang.group.customer",
        string="關聯團體會員/單位"
    )

    approval_state = fields.Selection([
        ("draft", "草稿"),
        ("review", "審核中"),
        ("approved", "審核通過"),
        ("rejected", "退回"),
        ("closed", "結案"),
    ], string="審核狀態", default="draft", required=True)

    public_description = fields.Text("公開說明")
    needed_amount = fields.Float("需求公益幣")
    received_amount = fields.Float("已收到公益幣", compute="_compute_received_amount", store=False)
    progress_rate = fields.Float("完成率", compute="_compute_received_amount", store=False)

    privacy_note = fields.Text(
        "隱私說明",
        default="願望牌公開前必須去識別化；不得公開提案人真名、電話、住址、精確位置、緊急事件敏感資料或未授權影像。"
    )

    @api.depends("needed_amount")
    def _compute_received_amount(self):
        Ledger = self.env["wuchang.wish.tree.coin.ledger"]
        for rec in self:
            total = sum(Ledger.search([
                ("target_id", "=", rec.id),
                ("ledger_type", "=", "donation"),
                ("state", "in", ["confirmed", "posted"]),
            ]).mapped("amount"))
            rec.received_amount = total
            rec.progress_rate = (total / rec.needed_amount * 100.0) if rec.needed_amount else 0.0


class WuchangWishTreeCoinCycle(models.Model):
    _name = "wuchang.wish.tree.coin.cycle"
    _description = "公益幣季度撥發週期"
    _rec_name = "name"

    name = fields.Char("週期名稱", required=True)
    policy_id = fields.Many2one("wuchang.wish.tree.coin.policy", string="撥發政策", required=True)
    date_start = fields.Date("週期開始")
    date_end = fields.Date("週期結束")
    grant_date = fields.Date("撥發日期")
    grant_amount = fields.Float("每位消費者公益幣額度", related="policy_id.grant_amount", store=True)

    state = fields.Selection([
        ("draft", "草稿"),
        ("granted", "已撥發"),
        ("closed", "已關帳"),
        ("cancelled", "取消"),
    ], string="狀態", default="draft")

    note = fields.Text("備註")

    def action_grant_to_consumers(self):
        Member = self.env["wuchang.member.identity"].sudo()
        Ledger = self.env["wuchang.wish.tree.coin.ledger"].sudo()

        for cycle in self:
            if cycle.policy_id.state != "active":
                raise ValidationError("撥發政策尚未啟用。")
            if cycle.grant_amount <= 0:
                raise ValidationError("每次撥發公益幣額度必須大於 0。")

            members = Member.search([
                ("member_role", "in", ["consumer", "resident", "owner"]),
                ("status", "=", "active"),
            ])

            for member in members:
                exists = Ledger.search([
                    ("cycle_id", "=", cycle.id),
                    ("member_id", "=", member.id),
                    ("ledger_type", "=", "grant"),
                ], limit=1)
                if not exists:
                    Ledger.create({
                        "name": f"{cycle.name} / {member.display_name} 公益幣撥發",
                        "cycle_id": cycle.id,
                        "member_id": member.id,
                        "ledger_type": "grant",
                        "amount": cycle.grant_amount,
                        "state": "posted",
                        "note": "季度公益幣撥發；僅可捐給審核通過單位或願望牌。",
                    })

            cycle.state = "granted"


class WuchangWishTreeCoinLedger(models.Model):
    _name = "wuchang.wish.tree.coin.ledger"
    _description = "社區許願樹公益幣台帳"
    _rec_name = "name"

    name = fields.Char("台帳名稱", required=True)
    cycle_id = fields.Many2one("wuchang.wish.tree.coin.cycle", string="撥發週期")
    member_id = fields.Many2one("wuchang.member.identity", string="消費者/會員")

    ledger_type = fields.Selection([
        ("grant", "季度撥發"),
        ("donation", "捐出"),
        ("reversal", "沖正"),
    ], string="台帳類型", required=True)

    target_id = fields.Many2one("wuchang.wish.tree.target", string="捐贈目標")
    amount = fields.Float("公益幣數量", required=True)

    state = fields.Selection([
        ("draft", "草稿"),
        ("confirmed", "已確認"),
        ("posted", "已入帳"),
        ("cancelled", "取消"),
    ], string="狀態", default="draft")

    restriction_note = fields.Text(
        "用途限制",
        default="公益幣僅可捐給審核通過之公益單位或願望牌；不可提領現金、不可購物折抵、不可轉給私人。"
    )
    note = fields.Text("備註")

    @api.constrains("ledger_type", "target_id", "amount")
    def _check_donation_target(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError("公益幣數量必須大於 0。")
            if rec.ledger_type == "donation":
                if not rec.target_id:
                    raise ValidationError("捐出公益幣必須指定捐贈目標。")
                if rec.target_id.approval_state != "approved":
                    raise ValidationError("公益幣只能捐給審核通過的單位或願望牌。")

    def action_confirm(self):
        for rec in self:
            rec.state = "confirmed"

    def action_post(self):
        for rec in self:
            rec.state = "posted"

    def action_cancel(self):
        for rec in self:
            rec.state = "cancelled"
