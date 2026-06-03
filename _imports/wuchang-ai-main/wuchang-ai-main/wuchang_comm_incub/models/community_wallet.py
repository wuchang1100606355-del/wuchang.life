# -*- coding: utf-8 -*-

from odoo import models, fields, api

class CommunityWallet(models.Model):
    _name = 'community.wallet'
    _description = 'Community Wallet'

    user_id = fields.Many2one('res.users', string='User')
    balance = fields.Float(string='Balance')
    expiry = fields.Date(string='Expiry')
    last_tx_hash = fields.Char(string='Last Transaction Hash')