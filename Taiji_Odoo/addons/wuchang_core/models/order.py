# -*- coding: utf-8 -*-
from odoo import models, fields, api


class WuchangOrder(models.Model):
    _name = 'wuchang.order'
    _description = 'Wuchang Online Order'

    name = fields.Char(string='Order Ref', required=True, default=lambda self: self.env['ir.sequence'].next_by_code('wuchang.order'))
    customer_name = fields.Char(string='客戶姓名')
    phone = fields.Char(string='電話')
    sale_mode = fields.Selection([
        ('dine_in', '內用'),
        ('takeout', '外帶'),
        ('delivery_commercial', '商業平台外送'),
        ('delivery_nonprofit', '公益平台外送'),
    ], string='銷售模式', default='takeout')
    table_no = fields.Char(string='桌號')
    delivery_address = fields.Char(string='外送地址')
    delivery_time = fields.Char(string='期望送達時間')
    delivery_note = fields.Text(string='外送備註')
    delivery_platform = fields.Char(string='外送平台')
    nonprofit_program = fields.Char(string='公益專案')
    merchant_id = fields.Many2one('res.partner', string='商業店家')
    property_community_id = fields.Many2one('wuchang.property.community', string='物業社區')
    property_unit_id = fields.Many2one('wuchang.property.unit', string='戶號')
    delivery_team_id = fields.Many2one('wuchang.delivery.team', string='商業志工隊')
    caregiver_staff_id = fields.Many2one('res.partner', string='照服員員工')
    social_worker_partner_id = fields.Many2one('res.partner', string='社工治理責任人')
    service_relation_type = fields.Selection([
        ('commercial_delivery', '商業外送'),
        ('nonprofit_delivery', '公益外送'),
        ('property_care_delivery', '物業照護外送'),
        ('social_worker_referral', '社工轉介服務'),
    ], string='物業商業服務關聯', default='commercial_delivery')
    care_context = fields.Selection([
        ('general', '一般'),
        ('senior_care', '銀髮照護'),
        ('social_work', '社工審核'),
        ('caregiver_escort', '照服員陪同'),
    ], string='照護場景', default='general')
    social_worker_governance_required = fields.Boolean('需社工治理', default=False)
    caregiver_employee_required = fields.Boolean('需照服員員工執行/陪同', default=False)
    requires_caregiver_escort = fields.Boolean('需照服員核定陪同', default=False)
    requires_social_worker_review = fields.Boolean('需社工審核/轉介', default=False)
    member_plaintext_included = fields.Boolean('含會員/住戶明文', default=False, readonly=True)
    payment_execution_allowed = fields.Boolean('允許付款執行', default=False, readonly=True)
    total_field_relation_ref = fields.Char('總場關聯證據 Ref', default='W7TP-007')
    eight_dimensional_code_ref = fields.Char('8維碼主權 AI Ref', default='8D_SOVEREIGN_AI_COMMUNITY_XIAOJ')
    sovereign_ai_persona = fields.Selection([
        ('community_xiaoj', '8維碼主權 AI 社區小J'),
    ], string='主權 AI 人格', default='community_xiaoj')
    property_commerce_relation_summary = fields.Char(
        '物業商業關聯摘要',
        compute='_compute_property_commerce_relation_summary',
        store=True,
    )
    delivery_fee = fields.Float(string='外送費')
    tip_amount = fields.Float(string='小費')
    location_lat = fields.Float(string='座標緯度')
    location_lng = fields.Float(string='座標經度')
    total_amount = fields.Float(string='金額')
    social_impact_score = fields.Float(string='社會貢獻值', default=0.0)
    social_impact_note = fields.Char(string='社會貢獻說明')
    state = fields.Selection([
        ('new', '新訂單'),
        ('paid', '已付款'),
        ('cancelled', '已取消'),
    ], string='狀態', default='new')
    items_json = fields.Text(string='品項（JSON）')
    note = fields.Text(string='備註')

    @api.onchange('property_unit_id')
    def _onchange_property_unit_id(self):
        for rec in self:
            if rec.property_unit_id and rec.property_unit_id.community_id:
                rec.property_community_id = rec.property_unit_id.community_id

    @api.depends(
        'property_community_id',
        'property_unit_id',
        'merchant_id',
        'delivery_team_id',
        'service_relation_type',
        'care_context',
    )
    def _compute_property_commerce_relation_summary(self):
        for rec in self:
            parts = [
                rec.property_community_id.name or '未指定物業',
                rec.property_unit_id.name or '區域級/無戶號',
                rec.merchant_id.name or '未指定店家',
                rec.delivery_team_id.name or '未指定志工隊',
                dict(rec._fields['service_relation_type'].selection).get(rec.service_relation_type, ''),
                dict(rec._fields['care_context'].selection).get(rec.care_context, ''),
            ]
            rec.property_commerce_relation_summary = ' / '.join([part for part in parts if part])
