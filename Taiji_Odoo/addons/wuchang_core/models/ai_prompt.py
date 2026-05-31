# -*- coding: utf-8 -*-
from odoo import models, fields

class WuchangAIPrompt(models.Model):
    _name = 'wuchang.ai.prompt'
    _description = 'AI Prompt Template'

    name = fields.Char(string='Key', required=True, index=True, help="Unique key to identify the prompt in code (e.g., 'fortune_telling').")
    template = fields.Text(string='Prompt Template', required=True, help="The prompt text. Use {variable} for dynamic placeholders.")
    description = fields.Char(string='Description', help="What this prompt is used for.")
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Prompt key must be unique!')
    ]
