import json
import re

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class WuchangCafeMerchantAccount(models.Model):
    _name = "wuchang.cafe.merchant.account"
    _description = "WuChang Cafe Merchant Account"
    _order = "company_id, name, id"

    name = fields.Char(string="商家帳號名稱", required=True, index=True)
    user_id = fields.Many2one(
        "res.users",
        string="Odoo 使用者",
        required=True,
        ondelete="restrict",
        index=True,
        domain=[("share", "=", True)],
    )
    company_id = fields.Many2one(
        "res.company",
        string="所屬公司",
        required=True,
        default=lambda self: self.env.company,
        ondelete="restrict",
        index=True,
    )
    pos_config_ids = fields.Many2many(
        "pos.config",
        "wuchang_cafe_merchant_pos_config_rel",
        "merchant_account_id",
        "pos_config_id",
        string="可管理的店面／點餐入口",
        domain="[('company_id', '=', company_id)]",
    )
    role_profile = fields.Selection(
        [
            ("viewer", "檢視者"),
            ("operator", "店務操作員"),
            ("manager", "店務管理員"),
        ],
        string="店務權限",
        required=True,
        default="viewer",
        index=True,
    )
    access_state = fields.Selection(
        [
            ("draft", "尚未套用"),
            ("active", "已啟用"),
            ("disabled", "已停用"),
        ],
        string="權限狀態",
        required=True,
        default="draft",
        index=True,
        copy=False,
    )
    identity_realm = fields.Selection(
        [("cafe_operations", "咖啡館店務域")],
        string="身分領域",
        required=True,
        default="cafe_operations",
        readonly=True,
        copy=False,
    )
    member_personal_data_access = fields.Selection(
        [("denied", "禁止存取協會會員個資")],
        string="協會會員個資",
        required=True,
        default="denied",
        readonly=True,
        copy=False,
    )
    ai_resource_policy = fields.Selection(
        [
            (
                "adaptive_total_field",
                "瀏覽器本機／自帶算力／總場共享池自適應選路",
            )
        ],
        string="AI 資源規則",
        required=True,
        default="adaptive_total_field",
        readonly=True,
        copy=False,
    )
    founder_compute_access = fields.Selection(
        [("quota_governed", "只可經總場配額治理取用")],
        string="創辦人算力",
        required=True,
        default="quota_governed",
        readonly=True,
        copy=False,
    )
    ai_compute_binding_ids = fields.Many2many(
        "wuchang.ai.compute.binding",
        string="可替換 LLM 算力來源",
        compute="_compute_ai_compute_bindings",
        readonly=True,
    )
    line_official_account_ref = fields.Char(
        string="LINE 官方帳號座標",
        default="@831ttauc",
        help="只保存公開官方帳號 ID；不保存會員、好友或聊天個資。",
    )
    google_login_bound = fields.Boolean(
        string="Google 登入已綁定",
        compute="_compute_google_login_state",
    )
    google_login_provider = fields.Char(
        string="Google 登入提供者",
        compute="_compute_google_login_state",
    )
    last_access_applied_at = fields.Datetime(
        string="最後套用時間",
        readonly=True,
        copy=False,
    )
    last_access_applied_by = fields.Many2one(
        "res.users",
        string="最後套用者",
        readonly=True,
        copy=False,
    )

    _sql_constraints = [
        (
            "merchant_user_company_unique",
            "unique(user_id, company_id)",
            "同一個 Odoo 使用者在同一家公司只能有一個商家帳號。",
        ),
    ]

    @api.depends("user_id.oauth_provider_id")
    def _compute_google_login_state(self):
        for account in self:
            provider = account.user_id.oauth_provider_id
            account.google_login_bound = bool(provider)
            account.google_login_provider = provider.display_name if provider else False

    @api.depends("user_id")
    def _compute_ai_compute_bindings(self):
        binding_model = self.env["wuchang.ai.compute.binding"]
        for account in self:
            account.ai_compute_binding_ids = binding_model.search(
                [("user_id", "=", account.user_id.id)]
            ) if account.user_id else binding_model.browse()

    @api.constrains("pos_config_ids", "company_id")
    def _check_pos_company(self):
        for account in self:
            foreign_configs = account.pos_config_ids.filtered(
                lambda config: config.company_id != account.company_id
            )
            if foreign_configs:
                raise ValidationError(_("點餐入口必須與商家帳號屬於同一家公司。"))

    @api.constrains("line_official_account_ref")
    def _check_line_official_account_ref(self):
        for account in self:
            value = (account.line_official_account_ref or "").strip()
            if value and not re.fullmatch(r"@[A-Za-z0-9]+", value):
                raise ValidationError(_("LINE 官方帳號座標格式不正確。"))

    @api.constrains("user_id")
    def _check_portal_only_user(self):
        for account in self:
            if account.user_id and (
                not account.user_id.share
                or not account.user_id.has_group("base.group_portal")
                or account.user_id.has_group("base.group_user")
            ):
                raise ValidationError(_("商家與會員只能綁定入口使用者，不得綁定 Odoo 後台使用者。"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._reject_member_personal_data_access(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._reject_member_personal_data_access(vals)
        return super().write(vals)

    def unlink(self):
        raise AccessError(_("商家帳號不得刪除；請使用「停用權限」保留稽核軌跡。"))

    @api.model
    def _reject_member_personal_data_access(self, vals):
        if vals.get("member_personal_data_access") not in (None, False, "denied"):
            raise AccessError(_("咖啡館商家帳號不得取得協會會員個資權限。"))
        if vals.get("identity_realm") not in (None, False, "cafe_operations"):
            raise AccessError(_("商家帳號只能存在於咖啡館店務域。"))
        if vals.get("ai_resource_policy") not in (None, False, "adaptive_total_field"):
            raise AccessError(_("商家與會員 AI 算力必須由總場依固定選路規則調度。"))
        if vals.get("founder_compute_access") not in (None, False, "quota_governed"):
            raise AccessError(_("創辦人算力只能由總場依配額與負載治理取用。"))

    def _require_access_administrator(self):
        if not self.env.user.has_group("base.group_system"):
            raise AccessError(_("只有系統管理員可套用或停用商家帳號權限。"))

    def _merchant_group_commands(self):
        self.ensure_one()
        viewer = self.env.ref("wuchang_cafe_ai_gateway.group_wuchang_cafe_merchant_viewer")
        operator = self.env.ref("wuchang_cafe_ai_gateway.group_wuchang_cafe_merchant_operator")
        manager = self.env.ref("wuchang_cafe_ai_gateway.group_wuchang_cafe_merchant_manager")
        selected = {
            "viewer": viewer.id,
            "operator": operator.id,
            "manager": manager.id,
        }[self.role_profile]
        commands = [
            Command.unlink(viewer.id),
            Command.unlink(operator.id),
            Command.unlink(manager.id),
            Command.link(selected),
        ]
        return commands

    def _write_access_event(self, result):
        self.ensure_one()
        self.env["wuchang.cafe.ai.eventbook"].sudo().create(
            {
                "name": "商家帳號權限變更",
                "event_type": "merchant_access_change",
                "source": "odoo_browser",
                "user_role": "system_administrator",
                "intent": "apply_merchant_access",
                "risk_level": "medium",
                "target_model": self._name,
                "target_record_id": str(self.id),
                "result": result,
                "payload_json": json.dumps(
                    {
                        "merchant_account_id": self.id,
                        "role_profile": self.role_profile,
                        "access_state": self.access_state,
                        "identity_realm": self.identity_realm,
                        "member_personal_data_access": self.member_personal_data_access,
                        "ai_resource_policy": self.ai_resource_policy,
                        "founder_compute_access": self.founder_compute_access,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            }
        )

    def action_apply_access(self):
        self._require_access_administrator()
        for account in self:
            account._check_portal_only_user()
            account.user_id.write(
                {
                    "groups_id": account._merchant_group_commands(),
                    "company_ids": [Command.link(account.company_id.id)],
                }
            )
            account.write(
                {
                    "access_state": "active",
                    "last_access_applied_at": fields.Datetime.now(),
                    "last_access_applied_by": self.env.user.id,
                }
            )
            account._write_access_event("success")
        return True

    def action_disable_access(self):
        self._require_access_administrator()
        viewer = self.env.ref("wuchang_cafe_ai_gateway.group_wuchang_cafe_merchant_viewer")
        operator = self.env.ref("wuchang_cafe_ai_gateway.group_wuchang_cafe_merchant_operator")
        manager = self.env.ref("wuchang_cafe_ai_gateway.group_wuchang_cafe_merchant_manager")
        for account in self:
            account.user_id.write(
                {
                    "groups_id": [
                        Command.unlink(viewer.id),
                        Command.unlink(operator.id),
                        Command.unlink(manager.id),
                    ]
                }
            )
            account.write(
                {
                    "access_state": "disabled",
                    "last_access_applied_at": fields.Datetime.now(),
                    "last_access_applied_by": self.env.user.id,
                }
            )
            account._write_access_event("success")
        return True

    def action_open_self_ordering(self):
        self.ensure_one()
        if self.access_state != "active":
            raise AccessError(_("商家帳號尚未啟用。"))
        if not self.env.user.has_group("base.group_system") and self.user_id != self.env.user:
            raise AccessError(_("只能開啟自己獲授權的點餐入口。"))
        config = self.sudo().pos_config_ids.filtered(
            lambda item: item.self_ordering_mode != "nothing"
        )[:1]
        if not config:
            raise ValidationError(_("尚未指派已啟用的 POS 自助點餐入口。"))
        url = config.self_ordering_url
        if not url:
            raise ValidationError(_("POS 自助點餐網址尚未由 Odoo 產生。"))
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "self",
        }
