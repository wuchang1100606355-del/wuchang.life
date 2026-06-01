# -*- coding: utf-8 -*-

from odoo import models, fields, api

class CareAlert(models.Model):
    _name = 'care.alert'
    _description = 'Care Alert'

    resident_id = fields.Many2one('res.partner', string='Resident')
    alert_type = fields.Selection([
        ('fall', 'Fall'),
        ('medical', 'Medical'),
        ('other', 'Other')
    ], string='Alert Type')
    timestamp = fields.Datetime(string='Timestamp')
    resolved_by = fields.Many2one('res.users', string='Resolved By')