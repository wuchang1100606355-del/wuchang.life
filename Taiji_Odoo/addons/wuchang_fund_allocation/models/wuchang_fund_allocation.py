from odoo import models, fields, api
from odoo.exceptions import ValidationError


class WuchangFundRevenueRuleAllocation(models.Model):
    _inherit = "wuchang.fund.revenue.rule"

    volunteer_team_rate = fields.Float("志工隊統籌財源比例", default=20.0)
    system_cost_rate = fields.Float("系統成本比例", default=20.0)
    wish_tree_rate = fields.Float("社區許願樹公益比例", default=10.0)

    allocation_total_rate = fields.Float(
        "基金收入分配合計比例",
        compute="_compute_allocation_total_rate",
        store=True
    )

    allocation_note = fields.Text(
        "基金分配說明",
        default="以基金收入為基礎：50%圈禁為社區幣/票券保付，20%為志工隊統籌財源，20%為系統成本，10%為社區許願樹公益。"
    )

    @api.depends("reserve_rate", "volunteer_team_rate", "system_cost_rate", "wish_tree_rate")
    def _compute_allocation_total_rate(self):
        for rec in self:
            rec.allocation_total_rate = (
                (rec.reserve_rate or 0.0)
                + (rec.volunteer_team_rate or 0.0)
                + (rec.system_cost_rate or 0.0)
                + (rec.wish_tree_rate or 0.0)
            )

    @api.constrains("reserve_rate", "volunteer_team_rate", "system_cost_rate", "wish_tree_rate")
    def _check_allocation_total(self):
        for rec in self:
            total = (
                (rec.reserve_rate or 0.0)
                + (rec.volunteer_team_rate or 0.0)
                + (rec.system_cost_rate or 0.0)
                + (rec.wish_tree_rate or 0.0)
            )
            if abs(total - 100.0) > 0.0001:
                raise ValidationError("基金收入分配比例必須合計為100%。目前合計為 %.2f%%。" % total)


class WuchangDeliveryOrderFundLedgerAllocation(models.Model):
    _inherit = "wuchang.delivery.order.fund.ledger"

    volunteer_team_rate = fields.Float("志工隊統籌財源比例", related="rule_id.volunteer_team_rate", store=True)
    system_cost_rate = fields.Float("系統成本比例", related="rule_id.system_cost_rate", store=True)
    wish_tree_rate = fields.Float("社區許願樹公益比例", related="rule_id.wish_tree_rate", store=True)

    volunteer_team_amount = fields.Float("志工隊統籌財源", compute="_compute_allocation_amounts", store=True)
    system_cost_amount = fields.Float("系統成本", compute="_compute_allocation_amounts", store=True)
    wish_tree_amount = fields.Float("社區許願樹公益", compute="_compute_allocation_amounts", store=True)

    allocation_total_amount = fields.Float("基金分配合計", compute="_compute_allocation_amounts", store=True)
    allocation_state = fields.Selection([
        ("draft", "草稿"),
        ("allocated", "已分配"),
        ("posted", "已入帳"),
        ("settled", "已結清"),
        ("cancelled", "取消"),
    ], string="分配狀態", default="draft")

    @api.depends(
        "total_fund_amount",
        "reserved_guarantee_amount",
        "rule_id.volunteer_team_rate",
        "rule_id.system_cost_rate",
        "rule_id.wish_tree_rate",
    )
    def _compute_allocation_amounts(self):
        for rec in self:
            total = rec.total_fund_amount or 0.0
            rec.volunteer_team_amount = total * (rec.rule_id.volunteer_team_rate or 0.0) / 100.0
            rec.system_cost_amount = total * (rec.rule_id.system_cost_rate or 0.0) / 100.0
            rec.wish_tree_amount = total * (rec.rule_id.wish_tree_rate or 0.0) / 100.0
            rec.allocation_total_amount = (
                (rec.reserved_guarantee_amount or 0.0)
                + rec.volunteer_team_amount
                + rec.system_cost_amount
                + rec.wish_tree_amount
            )

    def action_allocate_fund(self):
        for rec in self:
            rec.allocation_state = "allocated"

    def action_post_allocation(self):
        for rec in self:
            rec.allocation_state = "posted"

    def action_settle_allocation(self):
        for rec in self:
            rec.allocation_state = "settled"

    def action_cancel_allocation(self):
        for rec in self:
            rec.allocation_state = "cancelled"


class WuchangFundAllocationLedger(models.Model):
    _name = "wuchang.fund.allocation.ledger"
    _description = "五常基金分配台帳"
    _rec_name = "name"

    name = fields.Char("分配台帳名稱", required=True)
    source_ledger_id = fields.Many2one(
        "wuchang.delivery.order.fund.ledger",
        string="來源外送基金台帳",
        required=True
    )

    order_ref = fields.Char(related="source_ledger_id.order_ref", store=True, readonly=True)
    sales_amount = fields.Float(related="source_ledger_id.sales_amount", store=True, readonly=True)
    total_fund_amount = fields.Float(related="source_ledger_id.total_fund_amount", store=True, readonly=True)

    reserved_guarantee_amount = fields.Float(
        related="source_ledger_id.reserved_guarantee_amount",
        store=True,
        readonly=True
    )
    volunteer_team_amount = fields.Float(
        related="source_ledger_id.volunteer_team_amount",
        store=True,
        readonly=True
    )
    system_cost_amount = fields.Float(
        related="source_ledger_id.system_cost_amount",
        store=True,
        readonly=True
    )
    wish_tree_amount = fields.Float(
        related="source_ledger_id.wish_tree_amount",
        store=True,
        readonly=True
    )
    allocation_total_amount = fields.Float(
        related="source_ledger_id.allocation_total_amount",
        store=True,
        readonly=True
    )

    state = fields.Selection([
        ("draft", "草稿"),
        ("allocated", "已分配"),
        ("posted", "已入帳"),
        ("settled", "已結清"),
        ("cancelled", "取消"),
    ], string="狀態", default="draft")

    note = fields.Text("備註")
