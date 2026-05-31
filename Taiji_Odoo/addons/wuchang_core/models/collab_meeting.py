from odoo import models, fields


class WuchangCollabSpace(models.Model):
    _name = 'wuchang.collab.space'
    _description = 'Wuchang Collaboration Space'

    name = fields.Char(required=True)
    space_type = fields.Char()
    owner_id = fields.Many2one('res.partner')
    active = fields.Boolean(default=True)


class WuchangAiMeeting(models.Model):
    _name = 'wuchang.ai.meeting'
    _description = 'Wuchang AI Meeting'

    name = fields.Char(required=True)
    space_id = fields.Many2one('wuchang.collab.space')
    human_ids = fields.Many2many('res.partner')
    ai_agent_ids = fields.Many2many('wuchang.ai.agent')
    state = fields.Selection([
        ('planned', 'Planned'),
        ('ongoing', 'Ongoing'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], default='planned')
    final_decision_holder_id = fields.Many2one('res.partner')
    start_date = fields.Datetime()
    end_date = fields.Datetime()
    agenda = fields.Text()
    minutes = fields.Text()

    def action_start(self):
        for rec in self:
            rec.write({'state': 'ongoing', 'start_date': fields.Datetime.now()})

    def action_finish(self):
        for rec in self:
            rec.write({'state': 'done', 'end_date': fields.Datetime.now()})

    def add_minutes(self, text):
        for rec in self:
            m = (rec.minutes or '')
            rec.write({'minutes': (m + (('\n' if m else '') + (text or '')))})
