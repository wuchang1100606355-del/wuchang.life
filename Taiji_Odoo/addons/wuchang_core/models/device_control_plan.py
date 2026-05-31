# -*- coding: utf-8 -*-
"""
長期設備控制方案模型
"""
from odoo import models, fields, api
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class DeviceControlPlan(models.Model):
    _name = 'wuchang.device.control.plan'
    _description = '長期設備控制方案'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, create_date desc'

    name = fields.Char(string='方案名稱', required=True, tracking=True)
    plan_type = fields.Selection([
        ('enrollment', '設備納管'),
        ('monitoring', '監控管理'),
        ('remote_control', '遠程控制'),
        ('automation', '自動化控制'),
        ('maintenance', '維護管理'),
        ('security', '安全管理'),
    ], string='方案類型', required=True, default='enrollment', tracking=True)
    
    device_type = fields.Selection([
        ('workstation', '工作站'),
        ('mobile', '移動設備'),
        ('pos', 'POS 終端'),
        ('printer', '打印機'),
        ('iot', 'IoT 設備'),
        ('router', '路由器/交換機'),
        ('chrome_os', 'Chrome OS'),
        ('chromebook', 'Chromebook'),
        ('all', '所有設備'),
    ], string='目標設備類型', default='all', tracking=True)
    
    priority = fields.Selection([
        ('critical', '關鍵'),
        ('high', '高'),
        ('medium', '中'),
        ('low', '低'),
    ], string='優先級', default='medium', tracking=True)
    
    status = fields.Selection([
        ('draft', '草稿'),
        ('active', '啟用'),
        ('paused', '暫停'),
        ('completed', '已完成'),
        ('archived', '已歸檔'),
    ], string='狀態', default='draft', tracking=True)
    
    description = fields.Text(string='方案描述', tracking=True)
    
    # 控制策略
    control_strategy = fields.Selection([
        ('full_control', '完全控制'),
        ('monitoring_only', '僅監控'),
        ('conditional', '條件控制'),
        ('manual', '手動控制'),
    ], string='控制策略', default='monitoring_only', tracking=True)
    
    enrollment_method = fields.Selection([
        ('auto', '自動納管'),
        ('manual', '手動納管'),
        ('approval', '需要審批'),
    ], string='納管方式', default='auto')
    
    # 時間設置
    start_date = fields.Datetime(string='開始時間', default=fields.Datetime.now)
    end_date = fields.Datetime(string='結束時間')
    duration_days = fields.Integer(string='持續天數', default=365)
    
    # 監控設置
    monitor_enabled = fields.Boolean(string='啟用監控', default=True)
    monitor_interval = fields.Integer(string='監控間隔（分鐘）', default=5)
    heartbeat_timeout = fields.Integer(string='心跳超時（分鐘）', default=15)
    alert_on_offline = fields.Boolean(string='離線告警', default=True)
    
    # 訪問控制
    allowed_ips = fields.Text(string='允許的 IP 範圍', 
                             help='每行一個 IP 或 CIDR 範圍，如: 192.168.50.0/24')
    allowed_ports = fields.Text(string='允許的端口', 
                               help='每行一個端口，如: 3477, 8069')
    access_hours = fields.Char(string='訪問時間', 
                              default='00:00-23:59',
                              help='格式: HH:MM-HH:MM，如: 08:00-18:00')
    
    # 自動化規則
    automation_rules = fields.Text(string='自動化規則',
                                  help='JSON 格式的自動化規則配置')
    
    # 關聯設備
    device_ids = fields.Many2many(
        'wuchang.infrastructure.device',
        'device_control_plan_device_rel',
        'plan_id', 'device_id',
        string='目標設備'
    )
    
    device_count = fields.Integer(string='設備數量', compute='_compute_device_count', store=True)
    
    # 執行記錄
    execution_log_ids = fields.One2many(
        'wuchang.device.control.execution.log',
        'plan_id',
        string='執行記錄'
    )
    
    last_execution = fields.Datetime(string='最後執行時間')
    execution_count = fields.Integer(string='執行次數', default=0)
    success_count = fields.Integer(string='成功次數', default=0)
    failure_count = fields.Integer(string='失敗次數', default=0)
    
    # 審批流程
    require_approval = fields.Boolean(string='需要審批', default=False)
    approver_ids = fields.Many2many('res.users', string='審批人')
    approved_by = fields.Many2one('res.users', string='審批人')
    approved_date = fields.Datetime(string='審批時間')
    
    active = fields.Boolean(string='啟用', default=True)
    
    @api.depends('device_ids')
    def _compute_device_count(self):
        for plan in self:
            plan.device_count = len(plan.device_ids)
    
    def action_activate(self):
        """啟用方案"""
        for plan in self:
            if plan.require_approval and not plan.approved_by:
                raise UserError("此方案需要審批後才能啟用")
            plan.status = 'active'
            plan.message_post(body="長期控制方案已啟用")
            _logger.info(f"長期控制方案已啟用: {plan.name}")
    
    def action_pause(self):
        """暫停方案"""
        self.status = 'paused'
        self.message_post(body="長期控制方案已暫停")
    
    def action_execute(self):
        """執行方案"""
        for plan in self:
            if plan.status != 'active':
                raise UserError("只有啟用狀態的方案才能執行")
            
            # 記錄執行
            log = self.env['wuchang.device.control.execution.log'].create({
                'plan_id': plan.id,
                'execution_time': fields.Datetime.now(),
                'status': 'running'
            })
            
            try:
                # 執行控制邏輯
                result = plan._execute_control_logic()
                
                log.write({
                    'status': 'success' if result.get('success') else 'failed',
                    'result': str(result),
                    'execution_time': fields.Datetime.now()
                })
                
                plan.last_execution = fields.Datetime.now()
                plan.execution_count += 1
                if result.get('success'):
                    plan.success_count += 1
                else:
                    plan.failure_count += 1
                    
                plan.message_post(body=f"方案執行完成: {result.get('message', '')}")
                
            except Exception as e:
                log.write({
                    'status': 'failed',
                    'result': str(e),
                    'execution_time': fields.Datetime.now()
                })
                plan.failure_count += 1
                _logger.error(f"方案執行失敗: {plan.name} - {e}")
    
    def _execute_control_logic(self):
        """執行控制邏輯（子類可重寫）"""
        devices = self.device_ids or self.env['wuchang.infrastructure.device'].search([
            ('device_type', '=', self.device_type) if self.device_type != 'all' else []
        ])
        
        results = {
            'success': True,
            'message': f'已處理 {len(devices)} 個設備',
            'devices_processed': len(devices),
            'details': []
        }
        
        for device in devices:
            try:
                # 檢查設備狀態
                if self.monitor_enabled:
                    device.action_check_status()
                
                # 根據控制策略執行操作
                if self.control_strategy == 'full_control':
                    # 完全控制邏輯
                    pass
                elif self.control_strategy == 'monitoring_only':
                    # 僅監控
                    pass
                
                results['details'].append({
                    'device': device.name,
                    'status': 'success'
                })
            except Exception as e:
                results['success'] = False
                results['details'].append({
                    'device': device.name,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return results
    
    def action_schedule_automation(self):
        """設置自動執行計劃"""
        # 使用 Odoo 的定時任務或外部 cron
        pass


class DeviceControlExecutionLog(models.Model):
    _name = 'wuchang.device.control.execution.log'
    _description = '設備控制方案執行記錄'
    _order = 'execution_time desc'

    plan_id = fields.Many2one('wuchang.device.control.plan', string='控制方案', required=True, ondelete='cascade')
    execution_time = fields.Datetime(string='執行時間', required=True, default=fields.Datetime.now)
    status = fields.Selection([
        ('running', '執行中'),
        ('success', '成功'),
        ('failed', '失敗'),
        ('cancelled', '已取消'),
    ], string='狀態', default='running')
    result = fields.Text(string='執行結果')
    duration = fields.Float(string='執行時長（秒）')
    devices_affected = fields.Integer(string='受影響設備數')
