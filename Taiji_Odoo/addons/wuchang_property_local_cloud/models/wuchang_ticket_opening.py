from odoo import models, fields, api
from odoo.exceptions import ValidationError


class WuchangTicketOpening(models.Model):
    _name = "wuchang.ticket.opening"
    _description = "票券開設：團體會員商品券 / 商家自家票券"
    _rec_name = "name"

    name = fields.Char("票券開設名稱", required=True)

    issuer_mode = fields.Selection([
        ("group_member_universal", "團體會員開設：所有商家商品券"),
        ("merchant_self", "商家自行開設：自家票券"),
    ], string="開設模式", required=True, default="group_member_universal")

    issuer_member_id = fields.Many2one(
        "wuchang.member.identity",
        string="開設團體會員"
    )

    issuer_group_customer_id = fields.Many2one(
        "wuchang.group.customer",
        string="開設所屬團體"
    )

    issuer_merchant_id = fields.Many2one(
        "wuchang.group.customer",
        string="開設商家",
        domain=[("customer_type", "=", "merchant")]
    )

    target_scope = fields.Selection([
        ("all_merchants", "所有商家可用商品券"),
        ("specific_merchant", "指定商家商品券"),
        ("own_merchant", "商家自家票券"),
    ], string="票券適用範圍", required=True, default="all_merchants")

    target_merchant_id = fields.Many2one(
        "wuchang.group.customer",
        string="指定適用商家",
        domain=[("customer_type", "=", "merchant")]
    )

    ticket_type = fields.Selection([
        ("goods_coupon", "商品券"),
        ("service_coupon", "服務券"),
        ("discount_coupon", "折抵券"),
        ("task_reward_coupon", "社區任務獎勵券"),
    ], string="票券類型", default="goods_coupon", required=True)

    unit_value = fields.Float("單張面額", default=100.0, required=True)
    ticket_quantity = fields.Integer("張數", default=1, required=True)
    total_face_value = fields.Float(
        "票券總額度",
        compute="_compute_total_face_value",
        store=True
    )

    member_quota_limit = fields.Float("團體會員票券上限", default=10000.0)
    remaining_member_quota = fields.Float(
        "該團體會員剩餘可開設額度",
        compute="_compute_remaining_member_quota"
    )

    valid_from = fields.Date("有效起日")
    valid_to = fields.Date("有效迄日")

    local_cloud_id = fields.Many2one(
        "wuchang.local.cloud.appliance",
        string="第4件 在地雲端商設備"
    )
    governance_node_id = fields.Many2one(
        "wuchang.trusted.governance.node",
        string="第3件 受託營運/治理設備"
    )

    state = fields.Selection([
        ("draft", "草稿"),
        ("active", "已開設"),
        ("suspended", "暫停"),
        ("closed", "結束"),
        ("cancelled", "取消"),
    ], string="狀態", default="draft")

    notes = fields.Text("備註")

    @api.depends("unit_value", "ticket_quantity")
    def _compute_total_face_value(self):
        for rec in self:
            rec.total_face_value = (rec.unit_value or 0.0) * (rec.ticket_quantity or 0)

    @api.depends("issuer_member_id", "issuer_mode", "unit_value", "ticket_quantity", "state")
    def _compute_remaining_member_quota(self):
        for rec in self:
            if rec.issuer_mode != "group_member_universal" or not rec.issuer_member_id:
                rec.remaining_member_quota = 0.0
                continue

            domain = [
                ("issuer_mode", "=", "group_member_universal"),
                ("issuer_member_id", "=", rec.issuer_member_id.id),
                ("state", "!=", "cancelled"),
            ]
            if isinstance(rec.id, int):
                domain.append(("id", "!=", rec.id))

            used = sum(self.search(domain).mapped("total_face_value"))
            current = rec.total_face_value or ((rec.unit_value or 0.0) * (rec.ticket_quantity or 0))
            rec.remaining_member_quota = max((rec.member_quota_limit or 10000.0) - used - current, 0.0)

    @api.constrains(
        "issuer_mode",
        "issuer_member_id",
        "issuer_merchant_id",
        "target_scope",
        "target_merchant_id",
        "unit_value",
        "ticket_quantity",
        "state",
    )
    def _check_ticket_opening_rules(self):
        for rec in self:
            if rec.unit_value <= 0:
                raise ValidationError("單張面額必須大於 0。")
            if rec.ticket_quantity <= 0:
                raise ValidationError("張數必須大於 0。")

            total = (rec.unit_value or 0.0) * (rec.ticket_quantity or 0)

            if rec.issuer_mode == "group_member_universal":
                if not rec.issuer_member_id:
                    raise ValidationError("團體會員開設商品券時，必須指定開設團體會員。")
                if rec.target_scope not in ("all_merchants", "specific_merchant"):
                    raise ValidationError("團體會員開設票券，只能是所有商家商品券或指定商家商品券。")
                if rec.target_scope == "specific_merchant" and not rec.target_merchant_id:
                    raise ValidationError("指定商家商品券必須指定適用商家。")

                domain = [
                    ("issuer_mode", "=", "group_member_universal"),
                    ("issuer_member_id", "=", rec.issuer_member_id.id),
                    ("state", "!=", "cancelled"),
                ]
                if isinstance(rec.id, int):
                    domain.append(("id", "!=", rec.id))

                used = sum(self.search(domain).mapped("total_face_value"))
                limit = rec.member_quota_limit or 10000.0

                if used + total > limit:
                    raise ValidationError(
                        "團體會員商品券開設額度超過上限：每位團體會員上限為 10,000。"
                    )

            if rec.issuer_mode == "merchant_self":
                if not rec.issuer_merchant_id:
                    raise ValidationError("商家自行開設自家票券時，必須指定開設商家。")
                if rec.target_scope != "own_merchant":
                    raise ValidationError("商家自行開設票券時，適用範圍必須為商家自家票券。")
                if rec.target_merchant_id and rec.target_merchant_id != rec.issuer_merchant_id:
                    raise ValidationError("商家自家票券不得指定其他商家。")

    def action_activate(self):
        for rec in self:
            rec.state = "active"

    def action_suspend(self):
        for rec in self:
            rec.state = "suspended"

    def action_close(self):
        for rec in self:
            rec.state = "closed"

    def action_cancel(self):
        for rec in self:
            rec.state = "cancelled"
