# -*- coding: utf-8 -*-
from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'
    is_supreme_authority = fields.Boolean()
    is_ai_agent = fields.Boolean()
    real_name_verified = fields.Boolean()
    privacy_waived = fields.Boolean()
    bio_face_hash = fields.Char()
    bio_voice_hash = fields.Char()
    id_card_hash = fields.Char()
    citizen_digital_cert_uid = fields.Char()
    legal_jurisdiction = fields.Char(default="臺灣新北地方法院")
    
    legal_responsibility_statement = fields.Text(default="本人奉會員大會決議...願負所有法律責任。")
