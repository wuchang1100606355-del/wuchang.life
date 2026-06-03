# -*- coding: utf-8 -*-
from odoo import models, fields, api

# ==========================================
# 4. 外送與票券模組
# ==========================================
class WuchangDeliveryTeam(models.Model):
    _name = 'wuchang.delivery.team'
    name = fields.Char(required=True)
    code = fields.Char()
    leader_id = fields.Many2one('res.partner', string='隊長(兼店長)')
    supervisor_id = fields.Many2one('res.partner', string='督導(兼會計)')

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # 外送員裝備檢查
    has_helmet = fields.Boolean('符合規格之安全帽')
    has_thermal_bag = fields.Boolean('保溫袋 (需清潔)')
    has_vest = fields.Boolean('識別背心 / 證件')
    delivery_equipment_verified = fields.Boolean('外送裝備已驗證')

class WuchangDeliveryOrder(models.Model):
    _name = 'wuchang.delivery.order'
    _inherit = ['mail.thread']
    
    name = fields.Char(default='New')
    partner_id = fields.Many2one('res.partner')
    merchant_id = fields.Many2one('res.partner')
    order_type = fields.Selection([('dine_in', '內用'), ('takeout', '外帶'), ('delivery', '外送')], default='delivery')
    delivery_team_id = fields.Many2one('wuchang.delivery.team')
    delivery_partner_id = fields.Many2one('res.partner')
    amount_total = fields.Float()
    fund_contribution_amount = fields.Float(compute='_compute_contribution', store=True)
    state = fields.Selection([('confirmed', '已接單'), ('delivering', '配送中'), ('done', '完成')], default='confirmed')
    
    # GIS
    current_lat = fields.Float()
    current_lng = fields.Float()

    @api.depends('merchant_id', 'amount_total', 'order_type')
    def _compute_contribution(self):
        for r in self:
            if r.merchant_id.is_fund_pool_store:
                r.fund_contribution_amount = r.amount_total
            elif r.order_type == 'delivery':
                r.fund_contribution_amount = r.amount_total * 0.2
            else:
                r.fund_contribution_amount = 0

    def action_reconcile_bank(self, fee):
        # 1.5元 許願額度
        self.env['wuchang.community.coin'].create({
            'partner_id': self.partner_id.id, 'type': 'wish_credit', 'amount': 1.5, 'state': 'active'
        })
        self.partner_id.sudo().write({'wish_credit_balance': self.partner_id.wish_credit_balance + 1.5})

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
    _name = 'wuchang.pos.expense'
    amount = fields.Float()
    vendor_name = fields.Char()
    reason = fields.Char()
    pos_config_id = fields.Many2one('pos.config')

class WuchangSocialConfig(models.Model):
    _name = 'wuchang.social.config'
    pos_config_id = fields.Many2one('pos.config')
    platform = fields.Selection([('facebook', 'FB'), ('line', 'LINE'), ('google', 'Google')])
