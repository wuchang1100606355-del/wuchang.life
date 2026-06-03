# -*- coding: utf-8 -*-

from odoo import models, fields, api

class FundAudit(models.Model):
    _name = 'fund.audit'
    _description = 'Fund Audit'

    ledger_id = fields.Many2one('community.ledger', string='Ledger')
    auditor_id = fields.Many2one('res.users', string='Auditor')
    checksum = fields.Char(string='Checksum')
    verified_date = fields.Date(string='Verified Date')