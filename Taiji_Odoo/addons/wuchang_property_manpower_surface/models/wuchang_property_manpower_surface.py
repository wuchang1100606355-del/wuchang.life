from odoo import models, fields, api
from odoo.exceptions import ValidationError


class WuchangPropertyManpowerSurfacePlan(models.Model):
    _name = "wuchang.property.manpower.surface.plan"
    _description = "五常社區物業人力預算面"
    _rec_name = "name"

    name = fields.Char("預算面名稱", required=True)

    source_point_name = fields.Char(
        "來源點",
        default="聊國咖啡館仁義店人事編制"
    )

    surface_scope = fields.Selection([
        ("single_community", "單一社區面"),
        ("multi_building", "多棟/多管委會面"),
        ("district_grid", "轄區網格面"),
        ("wish_tree_public_service", "許願樹公益服務面"),
        ("safety_care_property", "安全/照護/物業整合面"),
    ], string="覆蓋面類型", default="safety_care_property", required=True)

    stage = fields.Selection([
        ("planning", "規劃中"),
        ("prelaunch", "預上架"),
        ("pilot", "試辦"),
        ("active", "生效中"),
        ("suspended", "暫停"),
    ], string="狀態", default="planning", required=True)

    coverage_area_note = fields.Text("覆蓋範圍說明")
    households_estimate = fields.Integer("預估戶數")
    people_estimate = fields.Integer("預估服務人數")
    service_node_count = fields.Integer("預估服務節點數")

    line_ids = fields.One2many(
        "wuchang.property.manpower.surface.line",
        "plan_id",
        string="人力面配置"
    )

    minimum_monthly_budget = fields.Float(
        "最低月人力預算",
        compute="_compute_budget",
        store=True
    )

    maximum_known_monthly_budget = fields.Float(
        "已知高階資格月預算",
        compute="_compute_budget",
        store=True
    )

    unknown_salary_headcount = fields.Float(
        "薪資待定人數",
        compute="_compute_budget",
        store=True
    )

    governance_note = fields.Text(
        "治理說明",
        default="本預算面用於把單點人事編制擴展為社區物業服務覆蓋能力；不得將單一分館或贊助會員解讀為社區本體控制者。轄區內個人會員與團體會員仍為本體權限來源。"
    )

    safety_note = fields.Text(
        "安全邊界",
        default="安全人力僅能執行陪同、守望、通報、路線指引、現場降溫、急救協助與轉警消；不得私刑、追捕、越權搜索、公開個資或以AI自行裁決。"
    )

    @api.depends("line_ids.minimum_monthly_budget", "line_ids.maximum_known_monthly_budget", "line_ids.headcount", "line_ids.salary_state")
    def _compute_budget(self):
        for rec in self:
            rec.minimum_monthly_budget = sum(rec.line_ids.mapped("minimum_monthly_budget"))
            rec.maximum_known_monthly_budget = sum(rec.line_ids.mapped("maximum_known_monthly_budget"))
            rec.unknown_salary_headcount = sum(
                line.headcount for line in rec.line_ids
                if line.salary_state == "to_be_defined"
            )


class WuchangPropertyManpowerSurfaceLine(models.Model):
    _name = "wuchang.property.manpower.surface.line"
    _description = "五常社區物業人力預算面配置明細"
    _rec_name = "name"

    plan_id = fields.Many2one(
        "wuchang.property.manpower.surface.plan",
        string="預算面",
        required=True,
        ondelete="cascade"
    )

    sequence = fields.Integer("序號", default=10)
    name = fields.Char("職能面名稱", required=True)

    manpower_domain = fields.Selection([
        ("social_work", "社工/社福面"),
        ("care_nursing", "照護/護理面"),
        ("property_management", "物業管理面"),
        ("personal_security", "人身安全守護面"),
        ("volunteer_coordination", "志工協調面"),
        ("system_operation", "系統維運面"),
        ("wish_tree_public_service", "許願樹公益服務面"),
    ], string="職能面", required=True)

    phase = fields.Selection([
        ("phase_1_core", "第一階段核心"),
        ("phase_1_reserved", "第一階段先佔缺"),
        ("phase_2_expansion", "第二階段擴編"),
        ("future", "未來階段"),
    ], string="階段", default="phase_1_core", required=True)

    headcount = fields.Float("人數", default=1.0, required=True)

    base_salary = fields.Float("基準月薪")
    license_extra = fields.Float("證照/資格加給")
    salary_state = fields.Selection([
        ("defined", "已定義"),
        ("to_be_defined", "待定"),
    ], string="薪資狀態", default="defined", required=True)

    minimum_monthly_budget = fields.Float(
        "最低月預算",
        compute="_compute_amounts",
        store=True
    )

    maximum_known_monthly_budget = fields.Float(
        "已知高階資格月預算",
        compute="_compute_amounts",
        store=True
    )

    license_required = fields.Boolean("需證照/資格")
    required_license_name = fields.Char("所需證照/資格")

    coverage_role = fields.Text("覆蓋任務")
    funding_source = fields.Selection([
        ("fund_available_income", "基金可動用收入"),
        ("volunteer_pool", "志工隊統籌財源"),
        ("system_cost_pool", "系統成本池"),
        ("wish_tree_public_pool", "許願樹公益池"),
        ("property_service_fee", "物業服務費"),
        ("sponsor_support", "贊助/公益投入"),
        ("to_be_defined", "待定"),
    ], string="預算來源", default="to_be_defined")

    note = fields.Text("備註")

    @api.depends("headcount", "base_salary", "license_extra", "salary_state")
    def _compute_amounts(self):
        for rec in self:
            if rec.salary_state == "to_be_defined":
                rec.minimum_monthly_budget = 0.0
                rec.maximum_known_monthly_budget = 0.0
            else:
                rec.minimum_monthly_budget = (rec.headcount or 0.0) * (rec.base_salary or 0.0)
                rec.maximum_known_monthly_budget = (rec.headcount or 0.0) * ((rec.base_salary or 0.0) + (rec.license_extra or 0.0))

    @api.constrains("headcount", "base_salary", "license_extra")
    def _check_numbers(self):
        for rec in self:
            if rec.headcount < 0 or rec.base_salary < 0 or rec.license_extra < 0:
                raise ValidationError("人數、薪資與加給不可為負數。")
