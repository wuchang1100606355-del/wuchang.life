from odoo import models, fields, api

class Partner(models.Model):
    _inherit = 'res.partner'

    property_management_role = fields.Selection([
        ('association', '社區發展協會'),
        ('committee', '公寓大廈管委會'),
        ('government', '里辦公處/政府機關'),
        ('vendor', '合作廠商'),
        ('resident', '一般住戶')
    ], string='物業管理角色', default='resident')

    spatial_idx_lat = fields.Float('緯度', digits=(10, 7))
    spatial_idx_lng = fields.Float('經度', digits=(10, 7))
    spatial_idx_alt = fields.Float('高度', digits=(10, 2))
    spatial_ref_uuid = fields.Char('時空參考 UUID')
