# -*- coding: utf-8 -*-
from odoo import models, fields, api

# ==========================================
# 1. 志工與專勤隊模組
# ==========================================
class VolunteerTask(models.Model):
    _name = 'wuchang.volunteer.task'
    _description = '五常社區志工任務'

    name = fields.Char('任務名稱', required=True)
    description = fields.Text('任務描述')
    coins_reward = fields.Integer('獎勵幸福幣', default=0)
    is_special_squad = fields.Boolean('專勤隊任務', default=False)
    is_voice_collection = fields.Boolean('語音採集任務', default=False)
    
    language = fields.Selection([
        ('mandarin', '國語'),
        ('taiwanese', '閩南語'),
        ('hakka', '客家語'),
        ('english', '英語')
    ], string='主要語言', default='mandarin')

    state = fields.Selection([('open', '招募中'), ('done', '已結束')], string='狀態', default='open')
    volunteer_ids = fields.One2many('wuchang.volunteer.signup', 'task_id', string='報名志工')
    voice_sample_ids = fields.One2many('wuchang.voice.sample', 'task_id', string='採集樣本')

    def action_close(self):
        self.write({'state': 'done'})
        for signup in self.volunteer_ids:
            if signup.partner_id:
                current = signup.partner_id.whc_wallet_balance or 0
                signup.partner_id.sudo().write({'whc_wallet_balance': current + self.coins_reward})

class VolunteerSignup(models.Model):
    _name = 'wuchang.volunteer.signup'
    _description = '志工報名紀錄'
    task_id = fields.Many2one('wuchang.volunteer.task', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', required=True)
    state = fields.Selection([('confirmed', '已確認'), ('attended', '已出席')], default='confirmed')

class WuchangVoiceSample(models.Model):
    _name = 'wuchang.voice.sample'
    _description = '語音採集樣本'
    task_id = fields.Many2one('wuchang.volunteer.task', required=True)
    partner_id = fields.Many2one('res.partner', required=True)
    audio_file = fields.Binary('錄音檔', required=True, attachment=True)
    state = fields.Selection([('pending', '待審核'), ('approved', '已通過')], default='pending')

    def action_approve(self):
        self.write({'state': 'approved'})
        if self.task_id.coins_reward > 0:
            self.partner_id.sudo().write({'whc_wallet_balance': self.partner_id.whc_wallet_balance + self.task_id.coins_reward})

class WuchangVolunteerMeeting(models.Model):
    _name = 'wuchang.volunteer.meeting'
    _description = '專勤隊會議'
    name = fields.Char('會議主題', required=True)
    date = fields.Datetime('會議時間', default=fields.Datetime.now)
    team_id = fields.Many2one('wuchang.delivery.team', required=True)
    attendee_ids = fields.Many2many('res.partner')
    content = fields.Html('會議內容')
    ai_summary = fields.Text('小J 摘要')

class WuchangVolunteerAnnouncement(models.Model):
    _name = 'wuchang.volunteer.announcement'
    _description = '專勤隊公告'
    name = fields.Char('標題')
    content = fields.Html('內容')
    team_id = fields.Many2one('wuchang.delivery.team')
    
class WuchangAiSupervisorLog(models.Model):
    _name = 'wuchang.ai.supervisor.log'
    name = fields.Char('督導事項')
    target_volunteer_id = fields.Many2one('res.partner')
    type = fields.Selection([('praise', '表揚'), ('reminder', '提醒'), ('warning', '警告')])
    content = fields.Text()
