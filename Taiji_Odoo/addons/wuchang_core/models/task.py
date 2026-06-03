# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import timedelta


class WuchangTask(models.Model):
    _name = 'wuchang.task'
    _description = 'Wuchang Task Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='標題', required=True, tracking=True)
    description = fields.Text(string='描述', tracking=True)
    state = fields.Selection([
        ('new', '新建'),
        ('in_progress', '進行中'),
        ('waiting', '等待中'),
        ('blocked', '受阻'),
        ('done', '完成'),
        ('cancelled', '已取消'),
    ], string='狀態', default='new', tracking=True)
    progress = fields.Float(string='進度(%)', default=0.0, tracking=True)
    owner_id = fields.Many2one('res.users', string='負責人', tracking=True, default=lambda self: self.env.user)
    partner_id = fields.Many2one('res.partner', string='相關人員', tracking=True)
    deadline = fields.Datetime(string='截止時間', tracking=True)
    priority = fields.Selection([
        ('0', '低'),
        ('1', '普通'),
        ('2', '高'),
        ('3', '緊急'),
    ], string='優先權', default='1', tracking=True)
    parent_id = fields.Many2one('wuchang.task', string='父任務', index=True)
    child_ids = fields.One2many('wuchang.task', 'parent_id', string='子任務')
    category = fields.Selection([
        ('normal', '一般'),
        ('side_quest_review', '支線審查'),
        ('resident_need', '居民需求')
    ], string='類別', default='normal', tracking=True)
    last_conversation_date = fields.Datetime(string='最後對話時間', compute='_compute_last_conversation_date', store=False)
    idle_hours = fields.Float(string='閒置時數', compute='_compute_idle_hours', store=False)
    res_model = fields.Char(string='關聯模型')
    res_id = fields.Integer(string='關聯記錄 ID')
    active = fields.Boolean(string='啟用', default=True)

    def _compute_last_conversation_date(self):
        for rec in self:
            last_date = False
            # 以郵件對話為準（mail.thread 下的 message_ids）
            messages = rec.message_ids.sorted(key=lambda m: m.date or m.create_date or False)
            if messages:
                last_date = messages[-1].date or messages[-1].create_date
            rec.last_conversation_date = last_date

    def _compute_idle_hours(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.last_conversation_date:
                delta = now - rec.last_conversation_date
                rec.idle_hours = delta.total_seconds() / 3600.0
            else:
                rec.idle_hours = 9999.0

    def _needs_intervention(self):
        now = fields.Datetime.now()
        for task in self:
            # 緊急條件：臨近截止 24 小時內尚未完成、或狀態為受阻
            if task.state in ('blocked',) and task.active:
                return True
            if task.deadline and task.active:
                delta = task.deadline - now
                if task.state not in ('done', 'cancelled') and delta <= timedelta(hours=24):
                    return True
        return False

    def action_mark_done(self):
        for task in self:
            task.write({'state': 'done', 'progress': 100.0})

    def _get_idle_threshold_hours(self):
        param = self.env['ir.config_parameter'].sudo().get_param('wuchang.task_idle_hours')
        try:
            return float(param) if param else 48.0
        except Exception:
            return 48.0

    def _has_active_sidequest(self):
        self.ensure_one()
        return any(child.active and child.category == 'side_quest_review' and child.state not in ('done', 'cancelled') for child in self.child_ids)

    def _generate_review_guidance(self):
        # 若可用 AI，則呼叫生成；否則回退為固定指導清單
        try:
            ai = self.env['wuchang.ai.logic']
            # 使用 analyze_operations 作為審查建議生成
            context = f"任務: {self.name}, 狀態: {self.state}, 進度: {self.progress}%"
            guidance = ai.analyze_operations(context)
            if guidance and not guidance.startswith('Error'):
                return guidance
        except Exception:
            pass
        return (
            "高品質審查指導:\n"
            "- 明確化目標與驗收標準\n"
            "- 拆解阻礙並指派可行行動\n"
            "- 對話總結：列出已決議與待決事項\n"
            "- 設定下一步截止與責任人\n"
        )

    def action_generate_sidequest_review(self):
        for task in self:
            if task._has_active_sidequest():
                continue
            guidance = task._generate_review_guidance()
            self.create({
                'name': f"支線任務：高品質審查 — {task.name}",
                'description': guidance,
                'state': 'in_progress',
                'owner_id': task.owner_id.id if task.owner_id else self.env.user.id,
                'priority': task.priority,
                'parent_id': task.id,
                'category': 'side_quest_review',
                'res_model': 'wuchang.task',
                'res_id': task.id,
            })
            task.message_post(body="[自動建立支線] 已建立高品質審查支線任務，請執行審查清單")

    @api.model
    def cron_check_tasks_and_intervene(self):
        # 找出需要介入的任務
        domain = [('active', '=', True), ('state', 'not in', ['done', 'cancelled'])]
        tasks = self.search(domain)
        todo_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        idle_threshold = self._get_idle_threshold_hours()
        for task in tasks:
            if task._needs_intervention():
                summary = '任務臨界提醒或受阻介入'
                note = '系統自動介入：請檢視狀態、解除阻礙或調整時程'
                # 建立待辦活動
                if todo_type:
                    task.activity_schedule(
                        activity_type_id=todo_type.id,
                        summary=summary,
                        user_id=task.owner_id.id if task.owner_id else self.env.user.id,
                        note=note,
                        date_deadline=task.deadline or fields.Datetime.now()
                    )
                # 自動在聊天室留下訊息
                task.message_post(body=f"[自動介入] {summary} — {note}")

            # 對於無進度的對話，派發支線審查
            if task.idle_hours >= idle_threshold and not task._has_active_sidequest():
                task.action_generate_sidequest_review()

    # --- AI Task Manager (Process) Extensions ---
    ai_reminder_date = fields.Datetime(string='AI Reminder Date', help="When the AI should proactively check this task.")
    ai_reminder_note = fields.Text(string='AI Reminder Note', help="What the AI should remind itself about.")
    
    @api.model
    def cron_ai_task_reminder(self):
        """
        Cron job: Active Process Reminder.
        Checks for tasks where the AI set a reminder for itself.
        """
        now = fields.Datetime.now()
        tasks = self.search([
            ('active', '=', True),
            ('ai_reminder_date', '<=', now),
            ('state', 'not in', ['done', 'cancelled'])
        ])

        if not tasks:
            return

        reminder_summary = []
        for task in tasks:
            note = task.ai_reminder_note or "Check progress."
            reminder_summary.append(f"- [Task] {task.name}: {note}")
            
            # Reset reminder (or clear it to avoid loop)
            # In a real agent system, the agent would decide to reschedule.
            # Here, we clear it to indicate 'reminded'.
            task.ai_reminder_date = False 
            
            # Log the reminder
            task.message_post(body=f"🤖 **[AI Self-Reminder]** triggered: {note}")

        if reminder_summary:
            self._notify_ai_process(reminder_summary)

    def _notify_ai_process(self, summary_list):
        """Sends a process notification to the AI."""
        summary_text = "\n".join(summary_list)
        msg_body = f"⏰ **[AI Process Reminder]**\nI have pending tasks to attend to:\n{summary_text}"
        
        # Post to general channel
        channel = self.env['mail.channel'].search([('name', '=', 'general')], limit=1)
        if channel:
            channel.message_post(body=msg_body, message_type='comment', subtype_xmlid='mail.mt_comment')
