from odoo import models, fields

class WuchangPosExpense(models.Model):
    _name = 'wuchang.pos.expense'
    _description = 'Wuchang POS Expense'
    _order = 'date desc, id desc'

    name = fields.Char(string='編號', required=True, default=lambda self: self.env['ir.sequence'].next_by_code('wuchang.pos.expense'))
    reason = fields.Char(string='支出項目', required=True)
    amount = fields.Float(string='金額', required=True)
    user_id = fields.Many2one('res.users', string='登記人', default=lambda self: self.env.user)
    pos_config_id = fields.Many2one('pos.config', string='商店')
    company_id = fields.Many2one('res.company', string='公司', related='pos_config_id.company_id', store=True, readonly=True)
    table_name = fields.Char(string='桌位')
    date = fields.Datetime(string='日期時間', default=fields.Datetime.now)
    note = fields.Text(string='備註')
    is_deducted_from_fund = fields.Boolean(string='已由基金扣除', default=False, help='Sync flag for fund pool deduction')

    def _check_amount_positive(self):
        for rec in self:
            if rec.amount is None or rec.amount <= 0:
                return False
        return True

    def write(self, vals):
        res = super().write(vals)
        if not self._check_amount_positive():
            raise ValueError('金額必須為正數')
        return res

    def create(self, vals_list):
        records = super().create(vals_list)
        if isinstance(records, models.Model):
            recs = records
        else:
            recs = records
        for rec in recs:
            if rec.amount is None or rec.amount <= 0:
                raise ValueError('金額必須為正數')
            
            # Trigger Fund Logic if strictly controlled store
            if rec.pos_config_id.wuchang_store_mode == 'fund':
                fund = self.env['community.fund.account'].search([('account_type', '=', 'general')], limit=1)
                if fund:
                    fund.register_expense(rec.amount, rec.reason or 'Store Expense')
        return records
