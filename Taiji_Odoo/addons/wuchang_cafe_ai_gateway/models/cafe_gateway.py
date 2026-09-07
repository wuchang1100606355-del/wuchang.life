import hashlib
import json
import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class WuchangCafeGateway(models.Model):
    _name = "wuchang.cafe.gateway"
    _description = "WuChang Cafe AI Gateway"
    _order = "name, id"

    name = fields.Char(string="名稱", required=True, index=True)
    active = fields.Boolean(string="啟用", default=True)
    store_node_ref = fields.Char(string="店面節點參照", required=True, index=True)
    pos_config_id = fields.Many2one(
        "pos.config",
        string="實際 POS 店面",
        ondelete="restrict",
        index=True,
    )
    seat_capacity_verified = fields.Boolean(
        string="座位資料已由創辦人確認",
        default=False,
        help="未確認時，商家 AI 必須回覆座位狀態未知，不得使用示範餐桌推測。",
    )
    line_official_url = fields.Char(
        string="咖啡館 LINE 官方帳號網址",
        help="只保存咖啡館官方公開網址；不得填入協會群組或會員個資。",
    )
    community_payment_enabled = fields.Boolean(
        string="社區支付可用",
        default=False,
    )
    self_issued_ticket_enabled = fields.Boolean(
        string="自發票券可用",
        default=False,
    )
    online_order_mode = fields.Selection(
        [
            ("proposal_only", "只形成待確認提案"),
            ("disabled", "停用"),
        ],
        string="AI 線上點餐模式",
        required=True,
        default="proposal_only",
        index=True,
    )
    backend_visibility_policy = fields.Selection(
        [("login_required", "必須登入")],
        string="後台可見規則",
        required=True,
        default="login_required",
    )
    public_route_policy = fields.Selection(
        [("forbidden", "禁止公開直接寫入")],
        string="公開路徑規則",
        required=True,
        default="forbidden",
    )
    cross_db_identity_policy = fields.Char(
        string="跨資料庫身分規則",
        required=True,
        default="separate_identity_realms",
    )
    member_plaintext_policy = fields.Selection(
        [("forbidden", "禁止會員明文")],
        string="會員明文規則",
        required=True,
        default="forbidden",
    )
    customer_ai_resource_policy = fields.Selection(
        [
            (
                "adaptive_total_field",
                "瀏覽器本機／自帶算力／總場共享池自適應選路",
            )
        ],
        string="使用者 AI 資源規則",
        required=True,
        default="adaptive_total_field",
        readonly=True,
    )
    founder_compute_access = fields.Selection(
        [("quota_governed", "只可經總場配額治理取用")],
        string="創辦人算力規則",
        required=True,
        default="quota_governed",
        readonly=True,
    )
    note = fields.Text(string="說明")

    @api.constrains(
        "backend_visibility_policy",
        "public_route_policy",
        "member_plaintext_policy",
        "cross_db_identity_policy",
        "customer_ai_resource_policy",
        "founder_compute_access",
    )
    def _check_fixed_boundaries(self):
        for gateway in self:
            if gateway.backend_visibility_policy != "login_required":
                raise ValidationError(_("咖啡館後台必須登入。"))
            if gateway.public_route_policy != "forbidden":
                raise ValidationError(_("公開路徑不得直接寫入店務系統。"))
            if gateway.member_plaintext_policy != "forbidden":
                raise ValidationError(_("咖啡館閘道不得保存協會會員明文。"))
            if gateway.cross_db_identity_policy != "separate_identity_realms":
                raise ValidationError(_("協會會員域與咖啡館商家域必須分離。"))
            if gateway.customer_ai_resource_policy != "adaptive_total_field":
                raise ValidationError(_("顧客與會員 AI 算力必須由總場依固定選路規則調度。"))
            if gateway.founder_compute_access != "quota_governed":
                raise ValidationError(_("創辦人算力只能由總場依配額與負載治理取用。"))

    def unlink(self):
        raise AccessError(_("咖啡館閘道不得刪除；請停用並保留稽核軌跡。"))


class WuchangCafeOrderProposal(models.Model):
    _name = "wuchang.cafe.order.proposal"
    _description = "WuChang Cafe Order Proposal"
    _order = "create_date desc, id desc"

    name = fields.Char(string="提案名稱", required=True, index=True)
    gateway_id = fields.Many2one(
        "wuchang.cafe.gateway",
        string="咖啡館閘道",
        required=True,
        ondelete="restrict",
        index=True,
    )
    state = fields.Selection(
        [
            ("draft", "待店員確認"),
            ("staff_confirmed", "店員已確認"),
            ("cancelled", "已取消"),
        ],
        string="狀態",
        required=True,
        default="draft",
        index=True,
        copy=False,
    )
    member_packet_ref = fields.Char(
        string="8D 身分封包參照",
        help="只允許不可逆參照，不得填入協會會員明文。",
    )
    kiosk_pair_id = fields.Char(string="點餐機配對參照", index=True)
    intent_type = fields.Selection(
        [
            ("online_order", "線上點餐"),
            ("voucher_status", "票券狀態"),
            ("stored_cup_status", "寄杯狀態"),
        ],
        string="意圖類型",
        required=True,
        default="online_order",
        index=True,
    )
    proposal_text = fields.Text(string="點餐提案")
    total_amount_preview = fields.Monetary(string="金額預覽")
    currency_id = fields.Many2one(
        "res.currency",
        string="幣別",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    ticket_policy = fields.Selection(
        [
            ("self_issued_ticket_only", "只允許自發票券"),
            ("none", "無票券"),
        ],
        string="票券規則",
        required=True,
        default="none",
    )
    community_payment_enabled = fields.Boolean(
        string="社區支付可用",
        related="gateway_id.community_payment_enabled",
        readonly=True,
        store=True,
    )
    formal_payment_forbidden = fields.Boolean(
        string="禁止正式付款",
        default=True,
        readonly=True,
    )
    formal_redemption_forbidden = fields.Boolean(
        string="禁止正式兌換",
        default=True,
        readonly=True,
    )
    auto_order_forbidden = fields.Boolean(
        string="禁止自動下單",
        default=True,
        readonly=True,
    )
    staff_user_id = fields.Many2one(
        "res.users",
        string="確認店員",
        readonly=True,
        copy=False,
    )
    staff_confirmed_at = fields.Datetime(
        string="店員確認時間",
        readonly=True,
        copy=False,
    )
    evidence_hash = fields.Char(
        string="證據雜湊",
        readonly=True,
        copy=False,
        index=True,
    )
    governance_note = fields.Text(string="治理說明")

    @api.constrains("member_packet_ref", "proposal_text", "governance_note")
    def _check_no_member_plaintext(self):
        forbidden_patterns = (
            r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",
            r"09\d{2}[- ]?\d{3}[- ]?\d{3}",
            r"\b[A-Z][12]\d{8}\b",
        )
        for proposal in self:
            combined = "\n".join(
                filter(
                    None,
                    [
                        proposal.member_packet_ref,
                        proposal.proposal_text,
                        proposal.governance_note,
                    ],
                )
            )
            if any(re.search(pattern, combined) for pattern in forbidden_patterns):
                raise ValidationError(_("點餐提案不得保存協會會員個資明文。"))

    @api.constrains(
        "formal_payment_forbidden",
        "formal_redemption_forbidden",
        "auto_order_forbidden",
    )
    def _check_hard_walls(self):
        for proposal in self:
            if not (
                proposal.formal_payment_forbidden
                and proposal.formal_redemption_forbidden
                and proposal.auto_order_forbidden
            ):
                raise ValidationError(_("AI 點餐提案不得直接付款、兌換或建立正式訂單。"))

    def _make_evidence_hash(self):
        self.ensure_one()
        evidence = {
            "proposal_id": self.id,
            "gateway_id": self.gateway_id.id,
            "intent_type": self.intent_type,
            "ticket_policy": self.ticket_policy,
            "total_amount_preview": self.total_amount_preview,
            "state": "staff_confirmed",
            "staff_user_id": self.env.user.id,
        }
        encoded = json.dumps(evidence, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def action_staff_confirm(self):
        for proposal in self:
            if proposal.state != "draft":
                raise ValidationError(_("只有待確認提案可以由店員確認。"))
            proposal.write(
                {
                    "state": "staff_confirmed",
                    "staff_user_id": self.env.user.id,
                    "staff_confirmed_at": fields.Datetime.now(),
                    "evidence_hash": proposal._make_evidence_hash(),
                }
            )
        return True

    def action_cancel(self):
        for proposal in self:
            if proposal.state == "cancelled":
                continue
            proposal.write({"state": "cancelled"})
        return True

    def unlink(self):
        raise AccessError(_("點餐提案不得刪除；請取消並保留稽核軌跡。"))
