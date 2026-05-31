# -*- coding: utf-8 -*-
from odoo import models, fields, api
import json
import logging

_logger = logging.getLogger(__name__)

class WuchangSisterControl(models.Model):
    _name = 'wuchang.sister.control'
    _description = 'Sister Control Center'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='名稱', default='妹妹控制中心')

    # 設備狀態
    pos_status = fields.Selection([
        ('offline', '離線 (Offline)'),
        ('online', '在線 (Online)'),
        ('active', '點餐中 (Active)')
    ], string='POS 狀態', default='offline', tracking=True)

    customer_display_status = fields.Selection([
        ('offline', '離線 (Offline)'),
        ('online', '在線 (Online)'),
        ('active', '顯示中 (Active)')
    ], string='客顯狀態', default='offline', tracking=True)

    # 網址配置
    pos_url = fields.Char(string='POS 網址', default='http://localhost:8069/pos/ui')
    customer_url = fields.Char(string='客顯網址', default='http://localhost:8069/pos/customer_display')

    # 指令隊列 (JSON 格式儲存)
    last_message = fields.Text(string='最後訊息')
    command_queue = fields.Text(string='指令隊列', default='{}')

    def action_sync_pos(self):
        self.ensure_one()
        self._add_command('POS', 'SYNC_UI')
        return True

    def action_sync_customer(self):
        self.ensure_one()
        self._add_command('CUSTOMER', 'SYNC_UI')
        return True

    def action_wake_up(self):
        self.ensure_one()
        self._add_command('POS', 'WAKE_UP')
        self._add_command('CUSTOMER', 'WAKE_UP')
        return True

    def action_sync_all(self):
        self.ensure_one()
        self.action_sync_pos()
        self.action_sync_customer()
        return True

    def action_clear_queue(self):
        self.ensure_one()
        self.command_queue = '{}'
        return True

    def _add_command(self, device_type, cmd_type, params=None):
        queue = json.loads(self.command_queue or '{}')
        if device_type not in queue:
            queue[device_type] = []

        queue[device_type].append({
            'type': cmd_type,
            'params': params or {},
            'timestamp': fields.Datetime.now().isoformat()
        })
        self.command_queue = json.dumps(queue)

