# -*- coding: utf-8 -*-

from odoo import models, fields, api

class VolunteerTask(models.Model):
    _name = 'volunteer.task'
    _description = 'Volunteer Task'

    name = fields.Char(string='Name')
    type = fields.Selection([
        ('clean', 'Clean'),
        ('delivery', 'Delivery'),
        ('care', 'Care'),
        ('fix', 'Fix')
    ], string='Type')
    sla_hours = fields.Float(string='SLA Hours')
    assigned_id = fields.Many2one('res.partner', string='Assigned To')
    status = fields.Selection([
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='Status')