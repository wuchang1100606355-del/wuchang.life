from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    x_is_volunteer = fields.Boolean(string='Is Volunteer')
    x_volunteer_level = fields.Selection(
        selection=[
            ('l1', '初階'),
            ('l2', '進階'),
            ('l3', '講師'),
        ],
        string='志工等級',
    )
    x_volunteer_skills = fields.Many2many(
        comodel_name='wuchang.skill',
        string='志工技能',
    )
    x_m7_certs = fields.Many2many(
        comodel_name='slide.channel',
        string='M7認證課程',
    )
    x_wallet_id = fields.Many2one(
        comodel_name='community.wallet',
        string='社區幣錢包',
        ondelete='set null',
    )

    _sql_constraints = [
        (
            'unique_wallet_per_volunteer',
            'unique(x_wallet_id)',
            '社區幣錢包只能綁定至單一志工。',
        ),
    ]
