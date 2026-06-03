# -*- coding: utf-8 -*-
from odoo import models, fields

class WuchangAiAgent(models.Model):
    _name = 'wuchang.ai.agent'
    _description = 'Wuchang AI Agent'

    name = fields.Char(string="Agent Name", required=True)
    agent_type = fields.Char(string="Agent Type")
    role_type = fields.Selection([
        ('sentinel', 'The Sentinel (Security)'),
        ('steward', 'The Steward (Operations)'),
        ('connector', 'The Connector (Care)')
    ], string="Role Type", required=True)
    description = fields.Text(string="Description")
    responsibilities = fields.Text(string="Key Responsibilities")
    color_code = fields.Char(string="Color Code")
    capabilities = fields.Text(string="Capabilities")
