# -*- coding: utf-8 -*-
from odoo import models, fields


class WuchangCoinLedger(models.Model):
    _name = 'wuchang.coin.ledger'
    _description = 'WHC Ledger'

    name = fields.Char(string='摘要')
    partner_id = fields.Many2one('res.partner', string='夥伴')
    amount = fields.Float(string='金額 (WHC)', default=0.0)
    ledger_type = fields.Selection([
        ('mint', '鑄造'),
        ('transfer', '轉帳'),
        ('reward', '獎勵'),
        ('burn', '核銷'),
        ('adjust', '調整')
    ], string='類型')
    timestamp = fields.Datetime(string='時間', default=fields.Datetime.now)
    note = fields.Char(string='備註')
