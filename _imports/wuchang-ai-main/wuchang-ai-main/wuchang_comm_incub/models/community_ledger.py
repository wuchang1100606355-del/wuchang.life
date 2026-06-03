# -*- coding: utf-8 -*-

from odoo import models, fields, api

class CommunityLedger(models.Model):
    _name = 'community.ledger'
    _description = 'Community Ledger'

    period = fields.Date(string='Period')
    total_income = fields.Float(string='Total Income')
    reward = fields.Float(string='Reward')
    volunteer = fields.Float(string='Volunteer')
    welfare = fields.Float(string='Welfare')
    ops = fields.Float(string='Ops')
    rnd = fields.Float(string='R&D')
    hash = fields.Char(string='Hash')