# -*- coding: utf-8 -*-
from odoo import models, fields


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
