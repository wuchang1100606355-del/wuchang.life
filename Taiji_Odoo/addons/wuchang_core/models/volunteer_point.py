from odoo import models, fields

class VolunteerPoint(models.Model):
    _name = 'wuchang.volunteer.point'
    _description = '志工點數派發簽核'

    volunteer_id = fields.Many2one('res.partner', string='志工姓名', required=True)
    points = fields.Integer(string='點數', required=True)
    state = fields.Selection([
        ('draft', '人工分配草稿'),
        ('captain', '隊長初核'),
        ('sg', '總幹事批示'),
        ('chairman', '理事長批示'),
        ('committee', '常務理事會追認')
    ], string='簽核狀態', default='draft')

    def action_approve_captain(self): self.state = 'captain'
    def action_approve_sg(self): self.state = 'sg'
    def action_approve_chairman(self): self.state = 'chairman'
    def action_approve_committee(self): self.state = 'committee'
