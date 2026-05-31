# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging
import requests
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

class WuchangUIProxy(models.Model):
    """
    UI 代理服務模型
    當 UI 設備離線時，伺服器自動代理 UI 的工作
    """
    _name = 'wuchang.ui.proxy'
    _description = 'UI Proxy Service'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='代理服務名稱', default='UI 代理服務')
    
    # UI 設備資訊
    ui_device_ip = fields.Char(string='UI 設備 IP', required=True, help='控制端 UI 設備的 IP 地址')
    ui_device_name = fields.Char(string='UI 設備名稱', help='UI 設備的識別名稱')
    ui_device_status = fields.Selection([
        ('online', '在線'),
        ('offline', '離線'),
        ('unknown', '未知'),
    ], string='UI 設備狀態', default='unknown', tracking=True)
    
    # 心跳監控
    last_heartbeat = fields.Datetime(string='最後心跳時間', readonly=True)
    heartbeat_interval = fields.Integer(string='心跳間隔（秒）', default=30, help='UI 設備應每 N 秒發送一次心跳')
    heartbeat_timeout = fields.Integer(string='心跳超時（秒）', default=90, help='超過此時間未收到心跳視為離線')
    
    # 代理設定
    proxy_enabled = fields.Boolean(string='啟用代理', default=True, help='當 UI 離線時自動代理其工作')
    proxy_mode = fields.Selection([
        ('auto', '自動（檢測到離線時啟用）'),
        ('manual', '手動（需手動啟用）'),
        ('disabled', '停用'),
    ], string='代理模式', default='auto', required=True)
    
    # 代理狀態
    is_proxying = fields.Boolean(string='正在代理', default=False, readonly=True, help='當前是否正在代理 UI 工作')
    proxy_start_time = fields.Datetime(string='代理開始時間', readonly=True)
    proxy_end_time = fields.Datetime(string='代理結束時間', readonly=True)
    
    # 代理功能清單
    proxy_capabilities = fields.Text(string='代理功能清單', default='{}', help='JSON 格式，定義伺服器可代理的 UI 功能')
    
    # 統計資訊
    total_proxy_count = fields.Integer(string='總代理次數', default=0, readonly=True)
    total_proxy_duration = fields.Float(string='總代理時長（小時）', default=0.0, readonly=True)
    
    @api.model
    def check_ui_status(self):
        """檢查 UI 設備狀態"""
        records = self.search([])
        for record in records:
            record._check_ui_heartbeat()
        return True
    
    def _check_ui_heartbeat(self):
        """檢查 UI 設備心跳"""
        self.ensure_one()
        
        if not self.ui_device_ip:
            self.ui_device_status = 'unknown'
            return
        
        # 檢查最後心跳時間
        now = fields.Datetime.now()
        if self.last_heartbeat:
            time_diff = (now - self.last_heartbeat).total_seconds()
            
            if time_diff > self.heartbeat_timeout:
                # UI 設備已離線
                if self.ui_device_status != 'offline':
                    self.ui_device_status = 'offline'
                    self._on_ui_offline()
            else:
                # UI 設備在線
                if self.ui_device_status != 'online':
                    self.ui_device_status = 'online'
                    self._on_ui_online()
        else:
            # 從未收到心跳，嘗試主動檢測
            self._ping_ui_device()
    
    def _ping_ui_device(self):
        """主動 ping UI 設備"""
        self.ensure_one()
        try:
            # 嘗試連接到 UI 設備的 Odoo 實例
            test_url = f"http://{self.ui_device_ip}:8069/web/health"
            response = requests.get(test_url, timeout=5)
            
            if response.status_code == 200:
                self.ui_device_status = 'online'
                self.last_heartbeat = fields.Datetime.now()
                self._on_ui_online()
            else:
                self.ui_device_status = 'offline'
                self._on_ui_offline()
        except Exception as e:
            _logger.warning(f"無法連接到 UI 設備 {self.ui_device_ip}: {e}")
            self.ui_device_status = 'offline'
            self._on_ui_offline()
    
    def _on_ui_offline(self):
        """UI 設備離線時的處理"""
        self.ensure_one()
        
        if self.proxy_mode == 'disabled':
            return
        
        if not self.is_proxying and self.proxy_enabled:
            # 開始代理 UI 工作
            self._start_proxy()
    
    def _on_ui_online(self):
        """UI 設備上線時的處理"""
        self.ensure_one()
        
        if self.is_proxying:
            # 停止代理，恢復 UI 控制
            self._stop_proxy()
    
    def _start_proxy(self):
        """開始代理 UI 工作"""
        self.ensure_one()
        
        self.is_proxying = True
        self.proxy_start_time = fields.Datetime.now()
        self.total_proxy_count += 1
        
        _logger.info(f"開始代理 UI 設備 {self.ui_device_ip} 的工作")
        self.message_post(
            body=f"[UI 代理] UI 設備 {self.ui_device_ip} 已離線，伺服器開始代理其工作。",
            subject="UI 代理啟動"
        )
        
        # 執行代理功能
        self._execute_proxy_functions()
    
    def _stop_proxy(self):
        """停止代理 UI 工作"""
        self.ensure_one()
        
        if not self.is_proxying:
            return
        
        self.is_proxying = False
        self.proxy_end_time = fields.Datetime.now()
        
        # 計算代理時長
        if self.proxy_start_time:
            duration = (self.proxy_end_time - self.proxy_start_time).total_seconds() / 3600.0
            self.total_proxy_duration += duration
        
        _logger.info(f"停止代理 UI 設備 {self.ui_device_ip} 的工作")
        self.message_post(
            body=f"[UI 代理] UI 設備 {self.ui_device_ip} 已恢復連線，伺服器停止代理。",
            subject="UI 代理停止"
        )
    
    def _execute_proxy_functions(self):
        """執行代理功能"""
        self.ensure_one()
        
        import json
        capabilities = json.loads(self.proxy_capabilities or '{}')
        
        # 預設代理功能
        default_capabilities = {
            'sister_control': True,  # 代理 Sister Control 功能
            'pos_sync': True,        # 代理 POS 同步
            'device_management': True,  # 代理設備管理
            'command_execution': True,  # 代理指令執行
        }
        
        # 合併自訂功能
        final_capabilities = {**default_capabilities, **capabilities}
        
        # 執行各項代理功能
        if final_capabilities.get('sister_control'):
            self._proxy_sister_control()
        
        if final_capabilities.get('pos_sync'):
            self._proxy_pos_sync()
        
        if final_capabilities.get('device_management'):
            self._proxy_device_management()
        
        if final_capabilities.get('command_execution'):
            self._proxy_command_execution()
    
    def _proxy_sister_control(self):
        """代理 Sister Control 功能"""
        self.ensure_one()
        
        # 獲取 Sister Control 記錄
        sister_control = self.env['wuchang.sister.control'].search([], limit=1)
        if sister_control:
            # 伺服器接管控制權
            _logger.info(f"[UI 代理] 伺服器接管 Sister Control")
            # 這裡可以執行原本由 UI 執行的控制指令
    
    def _proxy_pos_sync(self):
        """代理 POS 同步功能"""
        self.ensure_one()
        
        _logger.info(f"[UI 代理] 伺服器執行 POS 同步")
        # 執行 POS 同步邏輯
    
    def _proxy_device_management(self):
        """代理設備管理功能"""
        self.ensure_one()
        
        _logger.info(f"[UI 代理] 伺服器執行設備管理")
        # 執行設備管理邏輯
    
    def _proxy_command_execution(self):
        """代理指令執行功能"""
        self.ensure_one()
        
        _logger.info(f"[UI 代理] 伺服器執行指令")
        # 執行指令邏輯
    
    def action_force_proxy(self):
        """強制啟用代理（手動觸發）"""
        self.ensure_one()
        self._start_proxy()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'UI 代理已啟用',
                'message': f'伺服器已開始代理 UI 設備 {self.ui_device_ip} 的工作',
                'type': 'success',
            }
        }
    
    def action_stop_proxy(self):
        """停止代理"""
        self.ensure_one()
        self._stop_proxy()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'UI 代理已停止',
                'message': f'伺服器已停止代理 UI 設備 {self.ui_device_ip} 的工作',
                'type': 'success',
            }
        }
    
    def receive_heartbeat(self, device_ip=None):
        """接收 UI 設備心跳"""
        device_ip = device_ip or self.ui_device_ip
        record = self.search([('ui_device_ip', '=', device_ip)], limit=1)
        
        if not record:
            # 自動建立記錄
            record = self.create({
                'ui_device_ip': device_ip,
                'ui_device_name': f'UI Device {device_ip}',
            })
        
        record.last_heartbeat = fields.Datetime.now()
        record.ui_device_status = 'online'
        
        if record.is_proxying:
            record._stop_proxy()
        
        return {
            'status': 'success',
            'message': '心跳已接收',
            'is_proxying': record.is_proxying,
        }
