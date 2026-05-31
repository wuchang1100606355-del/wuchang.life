# -*- coding: utf-8 -*-
from odoo import models, fields, api


class WuchangJFGateway(models.Model):
    _name = 'wuchang.jf.gateway'
    _description = 'Wuchang JF Gateway'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(default='小JF')
    active = fields.Boolean(default=True)

    @api.model
    def _get_singleton(self):
        recs = self.search([], limit=1)
        if not recs:
            recs = self.create({'name': '小JF'})
        return recs

    def _generate_instructions(self, context_text):
        try:
            logic = self.env['wuchang.ai.logic']
            res = logic.analyze_operations(context_text)
            if res and not str(res).startswith('Error'):
                return res
        except Exception:
            pass
        return '請持續監控進度、解除阻礙並設定下一步行動'

    def post_report_and_request(self, report_text):
        self.message_post(body=report_text)
        instructions = self._generate_instructions(report_text)
        self.message_post(body='[請示指示] ' + instructions)
        return instructions

    @api.model
    def cron_periodic_report(self):
        tasks = self.env['wuchang.task'].search([('active', '=', True), ('state', 'not in', ['done', 'cancelled'])])
        total = len(tasks)
        by_state = {
            'new': len(tasks.filtered(lambda t: t.state == 'new')),
            'in_progress': len(tasks.filtered(lambda t: t.state == 'in_progress')),
            'waiting': len(tasks.filtered(lambda t: t.state == 'waiting')),
            'blocked': len(tasks.filtered(lambda t: t.state == 'blocked')),
        }
        idle_threshold = self.env['wuchang.task']._get_idle_threshold_hours()
        over_idle = tasks.filtered(lambda t: (t.idle_hours or 0.0) >= idle_threshold)
        top_idle = sorted(tasks, key=lambda t: t.idle_hours or 0.0, reverse=True)[:5]
        parts = [
            f"任務總數 {total}",
            f"狀態分布 new:{by_state['new']} in_progress:{by_state['in_progress']} waiting:{by_state['waiting']} blocked:{by_state['blocked']}",
            f"超過閒置閾值 {len(over_idle)}",
        ]
        if top_idle:
            names = ', '.join([f"{t.name}({round(t.idle_hours or 0.0, 1)}h)" for t in top_idle])
            parts.append(f"最久閒置 {names}")
        report = '[回報] ' + '；'.join(parts)
        gateway = self._get_singleton()
        gateway.post_report_and_request(report)
        return True

    @api.model
    def cron_event_watchdog(self):
        try:
            import os, json, time
            candidates = [
                os.path.join(os.getcwd(), 'community_intent.jsonl'),
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'downloads', 'community_intent.jsonl')
            ]
            lines = []
            for p in candidates:
                try:
                    if os.path.exists(p):
                        with open(p, 'r', encoding='utf-8') as f:
                            lines = f.read().splitlines()
                        break
                except Exception:
                    continue
            if not lines:
                return True
            now = int(time.time())
            prefs = {
                'enabled': True,
                'max_create_per_cycle': 10,
                'kind_priority': {'rsvp': 3, 'idea': 2, 'join': 1},
                'deadline_hours': {'rsvp': 24, 'idea': 72, 'join': 48}
            }
            try:
                p = os.path.join(os.getcwd(), 'scheduler_prefs.json')
                if os.path.exists(p):
                    with open(p, 'r', encoding='utf-8') as f:
                        prefs = json.loads(f.read()) or prefs
            except Exception:
                pass
            if not prefs.get('enabled', True):
                return True
            recent = []
            for line in lines[-200:]:
                try:
                    d = json.loads(line)
                    ts = int(d.get('ts', now))
                    if now - ts <= 3600:
                        recent.append(d)
                except Exception:
                    pass
            Task = self.env['wuchang.task'].sudo()
            todo_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
            created = 0
            limit = int(prefs.get('max_create_per_cycle', 10) or 10)
            try:
                from dateutil.relativedelta import relativedelta
            except Exception:
                relativedelta = None
            for ev in recent:
                kind = (ev.get('kind') or '').lower()
                payload = ev.get('payload') or {}
                name = ''
                category = 'event'
                if kind == 'rsvp':
                    name = f"活動 RSVP：{payload.get('event') or '活動'}"
                    category = 'community_event'
                elif kind == 'idea':
                    name = f"點子：{(payload.get('text') or '')[:40]}"
                    category = 'idea'
                elif kind == 'join':
                    name = f"加入關注：{payload.get('topic') or ''}"
                    category = 'interest'
                else:
                    name = f"事件：{kind or '未知'}"
                if not name:
                    continue
                existing = Task.search([('name', '=', name)], limit=1)
                if existing:
                    continue
                pr_map = prefs.get('kind_priority') or {}
                dl_map = prefs.get('deadline_hours') or {}
                pr = int((pr_map.get(kind) or 2))
                vals = {'name': name, 'category': category, 'state': 'new', 'active': True, 'priority': pr, 'owner_id': self.env.user.id}
                if relativedelta:
                    try:
                        hours = int(dl_map.get(kind) or 48)
                        vals['deadline'] = fields.Datetime.now() + relativedelta(hours=hours)
                    except Exception:
                        pass
                task = Task.create(vals)
                created += 1
                if todo_type:
                    task.activity_schedule(
                        activity_type_id=todo_type.id,
                        summary=name,
                        user_id=self.env.user.id,
                        note='自動建立（事件看守）',
                        date_deadline=fields.Datetime.now()
                    )
                if created >= limit:
                    break
            gateway = self._get_singleton()
            gateway.message_post(body=f"[事件看守] 最近 1 小時處理 {created} 則社群意圖")
            return True
        except Exception:
            return True
