from odoo import models, fields, api

class CommunityFundAccount(models.Model):
    _name = 'community.fund.account'
    _description = 'Community Fund Account'

    name = fields.Char(string='Account Name', required=True)
    account_type = fields.Selection([
        ('general', 'General'),
        ('reserve', 'Reserve'),
        ('surplus', 'Surplus'),
        ('welfare', 'Welfare'),
        ('ops', 'Operations')
    ], required=True)

    balance_twd = fields.Float(string='TWD Balance', default=0.0)
    balance_whc = fields.Float(string='WHC Balance', default=0.0)
    merchant_donation_total = fields.Float(string='Merchant Donation Total', default=0.0)
    consumer_donation_total = fields.Float(string='Consumer Donation Total', default=0.0)
    merchant_custody_total = fields.Float(string='Merchant Custody Total', default=0.0)
    deferred_whc_quota = fields.Float(string='Deferred WHC Quota', default=0.0)
    google_maps_credit = fields.Float(string='Google Maps Credit', default=0.0)
    deferred_voucher_quota = fields.Float(string='Deferred Voucher Quota', default=0.0)
    balance = fields.Float(string='Current Balance', compute='_compute_balance', store=True)
    transaction_ids = fields.One2many('community.fund.transaction', 'account_id', string='Transactions')

    @api.depends('transaction_ids.amount')
    def _compute_balance(self):
        for account in self:
            account.balance = sum(account.transaction_ids.mapped('amount'))

class CommunityFundTransaction(models.Model):
    _name = 'community.fund.transaction'
    _description = 'Fund Transaction'

    account_id = fields.Many2one('community.fund.account', string='Account', required=True)
    amount = fields.Float(string='Amount', required=True)
    reference = fields.Char(string='Reference')
    note = fields.Char(string='Note')
    date = fields.Datetime(string='Date', default=fields.Datetime.now)