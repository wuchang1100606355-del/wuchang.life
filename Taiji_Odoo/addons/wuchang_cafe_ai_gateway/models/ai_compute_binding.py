import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class WuchangAIComputeBinding(models.Model):
    _name = "wuchang.ai.compute.binding"
    _description = "Natural Identity Bound Replaceable LLM Compute"
    _order = "priority, provider_kind, id"

    name = fields.Char(string="算力來源名稱", required=True)
    user_id = fields.Many2one(
        "res.users",
        string="登入帳號",
        required=True,
        ondelete="restrict",
        index=True,
    )
    natural_identity_packet_ref = fields.Char(
        string="自然人 8D 身分封包參照",
        required=True,
        index=True,
        help="只保存不含個資的受控參照；同一自然人的多個登入帳號使用相同參照。",
    )
    provider_kind = fields.Selection(
        [
            ("gemini", "Gemini"),
            ("openai", "OpenAI"),
            ("other", "其他 LLM"),
        ],
        string="LLM 供應端",
        required=True,
        index=True,
    )
    account_ref_sha256 = fields.Char(
        string="供應端帳號不可逆指紋",
        required=True,
        size=64,
        index=True,
    )
    credential_vault_ref = fields.Char(
        string="受保護憑證庫參照",
        required=True,
        help="只允許 vault: 參照；不得在 Odoo 保存 API 金鑰或更新權杖明文。",
    )
    state = fields.Selection(
        [("bound", "已綁定"), ("disabled", "已停用")],
        string="狀態",
        required=True,
        default="bound",
        index=True,
    )
    owner_scope = fields.Selection(
        [("founder", "創辦人"), ("member", "會員／商家")],
        string="資源所有域",
        required=True,
        default="member",
        index=True,
    )
    purpose = fields.Selection(
        [("llm_compute_substitution", "LLM 算力替換")],
        string="用途",
        required=True,
        default="llm_compute_substitution",
        readonly=True,
    )
    priority = fields.Integer(string="選路優先序", default=100)
    model_allowlist = fields.Char(
        string="允許模型清單",
        help="只保存模型名稱，不保存憑證。以逗號分隔。",
    )
    daily_budget_units = fields.Integer(
        string="每日用量上限單位",
        default=0,
        help="0 代表由供應端限制；正值供 8DADI 選路使用。",
    )
    last_verified_at = fields.Datetime(string="最後驗證時間", readonly=True)

    _sql_constraints = [
        (
            "user_provider_account_unique",
            "unique(user_id, provider_kind, account_ref_sha256)",
            "同一登入帳號不可重複綁定相同供應端帳號。",
        ),
    ]

    @api.constrains(
        "account_ref_sha256",
        "credential_vault_ref",
        "natural_identity_packet_ref",
        "purpose",
        "daily_budget_units",
    )
    def _check_opaque_references(self):
        secret_markers = ("AIza", "sk-", "Bearer ", "private_key", "refresh_token")
        personal_patterns = (
            r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",
            r"09\d{2}[- ]?\d{3}[- ]?\d{3}",
            r"\b[A-Z][12]\d{8}\b",
        )
        for binding in self:
            digest = (binding.account_ref_sha256 or "").lower()
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValidationError(_("供應端帳號只能保存 SHA-256 不可逆指紋。"))
            vault_ref = binding.credential_vault_ref or ""
            if not vault_ref.startswith("vault:") or any(
                marker in vault_ref for marker in secret_markers
            ):
                raise ValidationError(_("憑證只能保存受保護憑證庫參照，不得保存金鑰明文。"))
            identity_ref = binding.natural_identity_packet_ref or ""
            if any(re.search(pattern, identity_ref) for pattern in personal_patterns):
                raise ValidationError(_("自然人身分封包參照不得包含個資明文。"))
            if binding.purpose != "llm_compute_substitution":
                raise ValidationError(_("外部模型只能作為可替換 LLM 算力來源。"))
            if binding.daily_budget_units < 0:
                raise ValidationError(_("每日用量上限不得為負數。"))

    @api.constrains("user_id", "owner_scope")
    def _check_identity_scope(self):
        for binding in self:
            if binding.owner_scope == "member" and not binding.user_id.share:
                raise ValidationError(_("會員算力只能綁定網站入口帳號。"))
            if binding.owner_scope == "founder" and not binding.user_id.has_group(
                "base.group_system"
            ):
                raise ValidationError(_("創辦人算力只能綁定創辦人後台帳號。"))

    def unlink(self):
        raise AccessError(_("LLM 算力綁定不得刪除；請停用以保留譜系。"))

    def action_disable(self):
        if not self.env.user.has_group("base.group_system"):
            raise AccessError(_("只有創辦人後台可停用 LLM 算力綁定。"))
        self.write({"state": "disabled"})
        return True
