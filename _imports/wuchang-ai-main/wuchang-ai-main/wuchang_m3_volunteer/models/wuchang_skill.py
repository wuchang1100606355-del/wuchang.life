from odoo import fields, models


class WuchangSkill(models.Model):
    _name = 'wuchang.skill'
    _description = 'Wuchang Volunteer Skill'

    name = fields.Char(string='技能名稱', required=True)
