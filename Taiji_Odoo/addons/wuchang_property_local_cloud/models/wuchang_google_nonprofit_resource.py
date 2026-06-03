from odoo import models, fields


class WuchangGoogleNonprofitResource(models.Model):
    _name = "wuchang.google.nonprofit.resource"
    _description = "Google 非營利組織優惠與外部算力資源池"
    _rec_name = "name"

    name = fields.Char("資源名稱", required=True)

    holder_company_id = fields.Many2one(
        "res.company",
        string="持有/申請主公司",
        default=lambda self: self.env.company
    )

    holder_partner_id = fields.Many2one(
        "res.partner",
        string="持有/申請組織"
    )

    provider = fields.Selection([
        ("google_for_nonprofits", "Google for Nonprofits"),
        ("google_workspace", "Google Workspace"),
        ("google_ad_grants", "Google Ad Grants"),
        ("google_maps_platform", "Google Maps Platform"),
        ("youtube_nonprofit", "YouTube Nonprofit Program"),
        ("google_cloud", "Google Cloud / Gemini / AI 算力"),
        ("other", "其他"),
    ], string="資源提供方/類型", required=True)

    resource_category = fields.Selection([
        ("identity_workspace", "身份/信箱/協作/雲端硬碟"),
        ("ad_credit", "公益廣告額度"),
        ("map_credit", "地圖/API額度"),
        ("video_outreach", "影音/公益傳播"),
        ("cloud_compute", "雲端算力/AI算力"),
        ("domain_dns", "網域/DNS/管理"),
        ("other", "其他"),
    ], string="資源分類", required=True)

    eligibility_state = fields.Selection([
        ("not_started", "尚未申請"),
        ("to_verify", "待資格驗證"),
        ("verified", "已通過資格驗證"),
        ("activated", "已啟用"),
        ("rejected", "未通過"),
        ("suspended", "暫停"),
        ("not_default_benefit", "非預設權益/另案申請"),
    ], string="資格/啟用狀態", default="not_started", required=True)

    resource_state = fields.Selection([
        ("modeling", "建模中"),
        ("available", "可用"),
        ("pending_approval", "待核准"),
        ("active", "使用中"),
        ("inactive", "未使用"),
        ("ended", "已結束"),
    ], string="資源使用狀態", default="modeling")

    monthly_value_usd = fields.Float("每月名目價值USD")
    annual_value_usd = fields.Float("年度名目價值USD")
    storage_quota_note = fields.Char("儲存/額度說明")
    compute_quota_note = fields.Char("算力/AI額度說明")
    use_case = fields.Text("五常社區雲用途")
    privacy_boundary = fields.Text(
        "隱私/資料邊界",
        default="Google 外部資源不得成為會員權限來源；會員真實身分、5維碼原始資料、完整軌跡與未授權社區資料不得外流。"
    )
    sovereignty_boundary = fields.Text(
        "主權邊界",
        default="Google 非營利優惠屬外部公益資源池；不得取代在地雲端商設備、本地 Odoo、會員權限來源設備或協會/會員治理。"
    )
    notes = fields.Text("備註")
