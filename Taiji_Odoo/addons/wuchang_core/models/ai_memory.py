# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)

class WuchangAiMemory(models.Model):
    _name = 'wuchang.ai.memory'
    _description = 'AI Work Log & Memory'
    _order = 'create_date desc'

    name = fields.Char(string='Memory Title', required=True)
    content = fields.Text(string='Memory Content', required=True)
    memory_type = fields.Selection([
        ('daily_log', 'Daily Work Log'),
        ('learning', 'Learning & Reflection'),
        ('event', 'Important Event'),
        ('instruction', 'User Instruction')
    ], string='Memory Type', default='daily_log', required=True)
    
    create_date = fields.Datetime(string='Created On', readonly=True)

    # Spatial Indexing
    spatial_idx_lat = fields.Float('空間緯度 (Latitude)', digits=(10, 7))
    spatial_idx_lng = fields.Float('空間經度 (Longitude)', digits=(10, 7))
    spatial_idx_alt = fields.Float('空間高度 (Altitude)', default=0.0)
    
    # Active Recall / Reminder Fields
    recall_date = fields.Datetime(string='Next Recall Date', help="When should the AI remind itself of this?")
    is_active_recall = fields.Boolean(string='Active Recall Enabled', default=True)
    recall_count = fields.Integer(string='Recall Count', default=0)

    def action_schedule_recall(self, days=1):
        """Schedules a recall for this memory."""
        for rec in self:
            rec.recall_date = fields.Datetime.now() + timedelta(days=days)
            rec.is_active_recall = True

    @api.model
    def cron_ai_memory_recall(self):
        """
        Cron job: Checks for memories that need to be recalled.
        Triggers an internal 'thought' or notifies the system.
        """
        now = fields.Datetime.now()
        memories = self.search([
            ('is_active_recall', '=', True),
            ('recall_date', '<=', now)
        ])

        if not memories:
            return

        # Group memories by type for a consolidated reminder
        recall_summary = []
        for mem in memories:
            recall_summary.append(f"- [{mem.memory_type}] {mem.name}: {mem.content[:50]}...")
            
            # Reschedule (Spaced Repetition Logic - Simple)
            # Increase interval based on recall count
            mem.recall_count += 1
            next_interval = 1 * (2 ** mem.recall_count) # 1, 2, 4, 8 days...
            mem.recall_date = now + timedelta(days=next_interval)
            
            # Post a message to the AI's internal channel or system log
            _logger.info(f"[AI MEMORY RECALL] {mem.name}")

        if recall_summary:
            # Notify the AI (System Channel)
            # We assume a channel or a way to 'speak' exists. 
            # For now, we'll create a system notification / message.
            self._notify_ai_system(recall_summary)

    def _notify_ai_system(self, summary_list):
        """Sends a notification to the AI/Admin about recalled memories."""
        summary_text = "\n".join(summary_list)
        msg_body = f"🧠 **[AI Memory Recall]**\nI remembered these items today:\n{summary_text}"
        
        # Post to a general channel or admin user
        # Finding the 'general' channel or creating a system note
        channel = self.env['mail.channel'].search([('name', '=', 'general')], limit=1)
        if channel:
            channel.message_post(body=msg_body, message_type='comment', subtype_xmlid='mail.mt_comment')
        else:
             # Fallback: Log to a specific system task or admin
             pass

