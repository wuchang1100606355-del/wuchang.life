from odoo import models, fields


class WuchangFranchiseRelationship(models.Model):
    _name = "wuchang.franchise.relationship"
    _description = "加盟/合作/公益捐贈型加盟關係"
    _rec_name = "name"

    name = fields.Char("關係名稱", required=True)

    main_company_id = fields.Many2one(
        "res.company",
        string="Odoo主公司",
        default=lambda self: self.env.company
    )

    franchisor_partner_id = fields.Many2one(
        "res.partner",
        string="加盟主/設備提供方/母體承擔方",
        required=True
    )

    subsidiary_partner_id = fields.Many2one(
        "res.partner",
        string="加盟店/未來場域/合作方",
        required=True
    )

    relationship_type = fields.Selection([
        ("franchise_terms_pending", "加盟條款待定義"),
        ("mutual_franchise_framework", "雙方加盟/合作框架"),
        ("public_interest_donation_franchise", "公益捐贈型加盟框架"),
        ("franchise_owner_to_subsidiary", "加盟主對子公司/加盟店"),
        ("mother_site_to_baby_site", "母體場域對孕育中場域"),
        ("fund_engine_relation", "基金經濟引擎關係"),
    ], string="關係類型", default="public_interest_donation_franchise", required=True)

    landing_status = fields.Selection([
        ("concept", "概念中"),
        ("gestating", "孕育中"),
        ("preparing", "籌備中"),
        ("not_landed", "未落地"),
        ("landed", "已落地"),
        ("operating", "已營運"),
        ("suspended", "暫停"),
    ], string="落地狀態", default="not_landed", required=True)

    legal_status = fields.Selection([
        ("internal_planning", "內部規劃"),
        ("pending_registration", "待登記/待文件"),
        ("documented", "已有文件"),
        ("registered", "已完成登記"),
    ], string="法律/文件狀態", default="internal_planning")

    revenue_status = fields.Selection([
        ("not_revenue_subject", "不列為現行收益主體"),
        ("pre_revenue", "預備收益模型"),
        ("revenue_active", "正式收益主體"),
    ], string="收益狀態", default="not_revenue_subject")

    franchise_fee_policy = fields.Selection([
        ("not_defined", "未定義"),
        ("donated_to_association", "加盟金回捐協會"),
        ("waived", "免收"),
        ("commercial_fee", "一般商業加盟金"),
    ], string="加盟金政策", default="donated_to_association")

    equipment_policy = fields.Selection([
        ("not_defined", "未定義"),
        ("provided_by_franchisor_as_donation_like", "設備由加盟主提供，實質公益投入/近似捐贈"),
        ("leased", "租賃"),
        ("sold", "買賣"),
        ("provided_by_franchisee", "加盟店自備"),
    ], string="設備政策", default="provided_by_franchisor_as_donation_like")

    financial_independence_policy = fields.Selection([
        ("not_defined", "未定義"),
        ("independent_no_return_obligation", "財務獨立，無回饋義務"),
        ("royalty_required", "需權利金/抽成"),
        ("profit_share_required", "需利潤分潤"),
    ], string="財務獨立/回饋政策", default="independent_no_return_obligation")

    equipment_cost_bearer = fields.Boolean("承擔設備/研發/算力成本", default=True)
    franchise_fee_donated_to_association = fields.Boolean("加盟金回捐協會", default=True)
    equipment_provided_by_franchisor = fields.Boolean("設備由加盟主提供", default=True)
    no_revenue_return_obligation = fields.Boolean("無營收回饋義務", default=True)
    no_royalty_obligation = fields.Boolean("無權利金/抽成義務", default=True)

    public_interest_terms_summary = fields.Text("公益型加盟條款摘要")
    notes = fields.Text("備註")
