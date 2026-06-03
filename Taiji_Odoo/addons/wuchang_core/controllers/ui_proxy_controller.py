# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class UIProxyController(http.Controller):
    """UI 代理控制器 - 處理 UI 設備心跳和代理請求"""
    
    @http.route('/wuchang/ui/heartbeat', type='json', auth='none', methods=['POST'], csrf=False)
    def ui_heartbeat(self, device_ip=None, device_name=None, **kwargs):
        """接收 UI 設備心跳"""
        try:
            ui_proxy = request.env['wuchang.ui.proxy'].sudo()
            result = ui_proxy.receive_heartbeat(device_ip=device_ip)
            
            _logger.info(f"收到 UI 設備心跳: {device_ip} - {device_name}")
            
            from odoo import fields
            return {
                'status': 'success',
                'message': '心跳已接收',
                'is_proxying': result.get('is_proxying', False),
                'timestamp': fields.Datetime.now().isoformat(),
            }
        except Exception as e:
            _logger.error(f"處理 UI 心跳失敗: {e}")
            return {
                'status': 'error',
                'message': str(e),
            }
    
    @http.route('/wuchang/ui/proxy/status', type='json', auth='user', methods=['GET'])
    def proxy_status(self, **kwargs):
        """查詢代理狀態"""
        try:
            ui_proxy = request.env['wuchang.ui.proxy'].sudo().search([], limit=1)
            if not ui_proxy:
                return {
                    'status': 'not_configured',
                    'message': '未配置 UI 代理服務',
                }
            
            return {
                'status': 'success',
                'is_proxying': ui_proxy.is_proxying,
                'ui_device_status': ui_proxy.ui_device_status,
                'ui_device_ip': ui_proxy.ui_device_ip,
                'last_heartbeat': ui_proxy.last_heartbeat.isoformat() if ui_proxy.last_heartbeat else None,
                'proxy_start_time': ui_proxy.proxy_start_time.isoformat() if ui_proxy.proxy_start_time else None,
            }
        except Exception as e:
            _logger.error(f"查詢代理狀態失敗: {e}")
            return {
                'status': 'error',
                'message': str(e),
            }
