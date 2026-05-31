# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class NotificationController(http.Controller):
    
    @http.route('/api/notification/broadcast', type='json', auth='public', methods=['POST'], csrf=False)
    def broadcast_notification(self, **kwargs):
        """接收廣播通知"""
        try:
            data = request.jsonrequest
            _logger.info(f"收到通知: {data.get('title', 'Unknown')}")
            
            # 可以在這裡觸發 Odoo 內部通知
            # 例如：創建通知消息、發送郵件等
            
            return {
                'success': True,
                'message': '通知已接收',
                'timestamp': data.get('timestamp')
            }
        except Exception as e:
            _logger.error(f"通知接收錯誤: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @http.route('/api/notification/design_report', type='http', auth='public', methods=['GET'], csrf=False)
    def get_design_report_notification(self, **kwargs):
        """獲取設計方案報告通知"""
        notification = {
            'title': '小J 指揮通道設計方案報告',
            'message': '專用指揮通道 UI 設計方案已完成，請查看報告。',
            'report_url': '/design_report',
            'command_center_url': '/command_center',
            'access_code': 'J2025',
            'status': 'ready'
        }
        return request.make_response(
            json.dumps(notification, ensure_ascii=False),
            headers=[('Content-Type', 'application/json')]
        )
