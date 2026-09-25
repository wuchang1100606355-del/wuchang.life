# -*- coding: utf-8 -*-
from odoo import models, fields, api

class WuchangDeliveryTeam(models.Model):
    _inherit = 'wuchang.delivery.team'

    code = fields.Char()
    leader_id = fields.Many2one('res.partner', string='隊長(兼店長)')
    supervisor_id = fields.Many2one('res.partner', string='督導(兼會計)')
    property_community_id = fields.Many2one(
        'wuchang.property.community',
        string='服務物業社區',
        help='志工隊可服務的物業/管委會社區關聯，不代表取得住戶明文。',
    )
    commercial_partner_id = fields.Many2one(
        'res.partner',
        string='商業承載店家',
        domain="[('property_management_role', 'in', ('vendor', 'association'))]",
    )
    caregiver_staff_id = fields.Many2one(
        'res.partner',
        string='照服員員工',
        help='照服員是照護執行員工，負責高齡/弱勢服務陪同、觀察與回報留痕。',
    )
    social_worker_partner_id = fields.Many2one(
        'res.partner',
        string='社工治理責任人',
        help='社工是意圖場與社區知能中樞的人類治理責任人，負責照護判斷、權限分窗與服務閉環。',
    )
    relation_scope = fields.Selection([
        ('commercial_delivery', '商業外送'),
        ('nonprofit_delivery', '公益外送'),
        ('property_care_delivery', '物業照護外送'),
        ('social_worker_referral', '社工轉介服務'),
    ], string='物業商業關聯範圍', default='property_care_delivery')
    senior_care_enabled = fields.Boolean('銀髮照護任務', default=True)
    social_worker_governance_required = fields.Boolean('需社工治理', default=True)
    caregiver_employee_required = fields.Boolean('需照服員員工執行/陪同', default=True)
    requires_caregiver_escort = fields.Boolean('需照服員核定陪同', default=True)
    requires_social_worker_review = fields.Boolean('需社工審核/轉介', default=False)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # 外送員裝備檢查
    has_helmet = fields.Boolean('符合規格之安全帽')
    has_thermal_bag = fields.Boolean('保溫袋 (需清潔)')
    has_vest = fields.Boolean('識別背心 / 證件')
    delivery_equipment_verified = fields.Boolean('外送裝備已驗證')
    is_fund_pool_store = fields.Boolean('公益基金池合作店')
    whc_wallet_balance = fields.Float('幸福幣餘額', default=0.0)
    wish_credit_balance = fields.Float('許願額度餘額', default=0.0)

class WuchangDeliveryOrder(models.Model):
    _name = 'wuchang.delivery.order'
    _description = '五常物業商業志工外送單'
    _inherit = ['mail.thread']
    
    name = fields.Char(default='New')
    partner_id = fields.Many2one('res.partner', string='需求者/住戶')
    merchant_id = fields.Many2one('res.partner', string='商業店家')
    property_community_id = fields.Many2one('wuchang.property.community', string='物業社區')
    property_unit_id = fields.Many2one('wuchang.property.unit', string='戶號')
    order_type = fields.Selection([('dine_in', '內用'), ('takeout', '外帶'), ('delivery', '外送')], default='delivery')
    service_relation_type = fields.Selection([
        ('commercial_delivery', '商業外送'),
        ('nonprofit_delivery', '公益外送'),
        ('property_care_delivery', '物業照護外送'),
        ('social_worker_referral', '社工轉介服務'),
    ], string='物業商業服務關聯', default='property_care_delivery')
    care_context = fields.Selection([
        ('general', '一般'),
        ('senior_care', '銀髮照護'),
        ('social_work', '社工審核'),
        ('caregiver_escort', '照服員陪同'),
    ], string='照護場景', default='senior_care')
    delivery_team_id = fields.Many2one('wuchang.delivery.team', string='商業志工隊')
    delivery_partner_id = fields.Many2one('res.partner', string='接單志工')
    caregiver_staff_id = fields.Many2one('res.partner', string='照服員員工')
    social_worker_partner_id = fields.Many2one('res.partner', string='社工治理責任人')
    amount_total = fields.Float()
    fund_contribution_amount = fields.Float(compute='_compute_contribution', store=True)
    social_worker_governance_required = fields.Boolean('需社工治理', default=True)
    caregiver_employee_required = fields.Boolean('需照服員員工執行/陪同', default=True)
    requires_caregiver_escort = fields.Boolean('需照服員核定陪同', default=True)
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
    state = fields.Selection([
        ('confirmed', '已接單'),
        ('care_review', '照護審核'),
        ('delivering', '配送中'),
        ('done', '完成'),
        ('blocked', '已封鎖'),
    ], default='care_review')
    
    # GIS
    current_lat = fields.Float()
    current_lng = fields.Float()

    @api.onchange('property_unit_id')
    def _onchange_property_unit_id(self):
        for r in self:
            if r.property_unit_id and r.property_unit_id.community_id:
                r.property_community_id = r.property_unit_id.community_id

    @api.depends('merchant_id', 'amount_total', 'order_type')
    def _compute_contribution(self):
        for r in self:
            if r.merchant_id and r.merchant_id.is_fund_pool_store:
                r.fund_contribution_amount = r.amount_total
            elif r.order_type == 'delivery':
                r.fund_contribution_amount = r.amount_total * 0.2
            else:
                r.fund_contribution_amount = 0

    @api.depends(
        'property_community_id',
        'property_unit_id',
        'merchant_id',
        'delivery_team_id',
        'care_context',
        'service_relation_type',
    )
    def _compute_property_commerce_relation_summary(self):
        for r in self:
            parts = [
                r.property_community_id.name or '未指定物業',
                r.property_unit_id.name or '區域級/無戶號',
                r.merchant_id.name or '未指定店家',
                r.delivery_team_id.name or '未指定志工隊',
                dict(r._fields['service_relation_type'].selection).get(r.service_relation_type, ''),
                dict(r._fields['care_context'].selection).get(r.care_context, ''),
            ]
            r.property_commerce_relation_summary = ' / '.join([p for p in parts if p])

    def action_reconcile_bank(self, fee):
        # 1.5元 許願額度
        if not self.partner_id:
            return False
        self.env['wuchang.community.coin'].create({
            'partner_id': self.partner_id.id, 'type': 'wish_credit', 'amount': 1.5, 'state': 'active'
        })
        self.partner_id.sudo().write({'wish_credit_balance': self.partner_id.wish_credit_balance + 1.5})
        return True

class WuchangVoucherProduct(models.Model):
    _name = 'wuchang.voucher.product'
    name = fields.Char()
    voucher_type = fields.Selection([('discount_70', '7折'), ('discount_60', '6折'), ('free', '免費')])
    merchant_id = fields.Many2one('res.partner')
    stock_qty = fields.Integer()

class WuchangCommunityCoin(models.Model):
    _name = 'wuchang.community.coin'
    partner_id = fields.Many2one('res.partner')
    type = fields.Selection([('coin', '幣'), ('voucher', '券'), ('wish_credit', '許願')])
    amount = fields.Float()
    state = fields.Selection([('deferred', '遞延'), ('active', '有效')])

class WuchangPosExpense(models.Model):
    _inherit = 'wuchang.pos.expense'

    vendor_name = fields.Char()

class WuchangSocialConfig(models.Model):
    _name = 'wuchang.social.config'
    pos_config_id = fields.Many2one('pos.config')
    platform = fields.Selection([('facebook', 'FB'), ('line', 'LINE'), ('google', 'Google')])
