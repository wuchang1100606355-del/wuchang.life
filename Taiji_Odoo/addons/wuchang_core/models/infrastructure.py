# -*- coding: utf-8 -*-
from odoo import models, fields, api

class WuchangInfrastructureDevice(models.Model):
    _name = 'wuchang.infrastructure.device'
    _description = 'Wuchang Network Device'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Device Name', required=True, tracking=True)
    ip_address = fields.Char(string='IP Address', tracking=True)
    mac_address = fields.Char(string='MAC Address', tracking=True)
    device_type = fields.Selection([
        ('workstation', 'Workstation'),
        ('mobile', 'Mobile'),
        ('pos', 'POS Terminal'),
        ('printer', 'Printer'),
        ('iot', 'IoT Device'),
        ('router', 'Router/Switch'),
        ('other', 'Other'),
    ], string='Device Type', default='other', tracking=True)
    status = fields.Selection([
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('unknown', 'Unknown')
    ], string='Status', default='unknown', tracking=True)
    last_seen = fields.Datetime(string='Last Seen')
    owner_id = fields.Many2one('res.partner', string='Owner/Assignee')
    note = fields.Text(string='Notes')
