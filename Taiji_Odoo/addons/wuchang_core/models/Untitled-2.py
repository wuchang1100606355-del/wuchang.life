class VolunteerTask(models.Model):
    _name = 'wuchang.volunteer.task'
    name = fields.Char('任務名稱')
    coins_reward = fields.Integer('獎勵幸福幣')
    is_special_squad = fields.Boolean('專勤隊任務', default=False)
    state = fields.Selection([('open','招募中'),('done','已結束')], default='open')
    volunteer_ids = fields.One2many('wuchang.volunteer.signup', 'task_id')

    def action_close(self):
        self.write({'state': 'done'})
        for signup in self.volunteer_ids:
            signup.partner_id.sudo().write({'whc_wallet_balance': signup.partner_id.whc_wallet_balance + self.coins_reward})

class VolunteerSignup(models.Model):
    _name = 'wuchang.volunteer.signup'
    task_id = fields.Many2one('wuchang.volunteer.task')
    partner_id = fields.Many2one('res.partner')