# -*- coding: utf-8 -*-
"""
外網握手控制器 - 通過路由器中繼
"""
from odoo import http
from odoo.http import request
import json
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class HandshakeController(http.Controller):
    
    @http.route('/api/handshake', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def handshake(self, **kwargs):
        """外網握手端點 - 用於測試連接和驗證"""
        try:
            # 獲取客戶端信息
            client_ip = request.httprequest.remote_addr
            user_agent = request.httprequest.headers.get('User-Agent', 'Unknown')
            
            # 檢查是否通過路由器
            forwarded_for = request.httprequest.headers.get('X-Forwarded-For', '')
            via = request.httprequest.headers.get('Via', '')
            
            handshake_response = {
                'status': 'success',
                'message': '握手成功',
                'timestamp': datetime.now().isoformat(),
                'server': {
                    'ip': '192.168.50.249',
                    'hostname': 'Home-commput.wuchang.life',
                    'system': 'Wuchang OS V5.1.0',
                    'ai': 'Little J (小j)'
                },
                'client': {
                    'ip': client_ip,
                    'forwarded_for': forwarded_for if forwarded_for else None,
                    'via': via if via else None,
                    'user_agent': user_agent,
                    'relayed': bool(forwarded_for or via)
                },
                'services': {
                    'command_center': '/command_center',
                    'design_report': '/design_report',
                    'api_health': '/health'
                },
                'access': {
                    'command_center_code': 'J2025',
                    'report_url': '/design_report'
                }
            }
            
            _logger.info(f"握手請求來自: {client_ip} (轉發: {forwarded_for}, Via: {via})")
            
            return request.make_response(
                json.dumps(handshake_response, ensure_ascii=False, indent=2),
                headers=[
                    ('Content-Type', 'application/json'),
                    ('Access-Control-Allow-Origin', '*'),
                    ('X-Handshake-Server', 'Wuchang-OS'),
                    ('X-AI-Identity', 'Little-J')
                ]
            )
        except Exception as e:
            _logger.error(f"握手錯誤: {e}")
            return request.make_response(
                json.dumps({
                    'status': 'error',
                    'message': str(e),
                    'timestamp': datetime.now().isoformat()
                }, ensure_ascii=False),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
    
    @http.route('/api/handshake/test', type='json', auth='public', methods=['POST'], csrf=False)
    def handshake_test(self, **kwargs):
        """握手測試（JSON）"""
        try:
            data = request.jsonrequest or {}
            test_type = data.get('type', 'ping')
            
            response = {
                'status': 'success',
                'test_type': test_type,
                'timestamp': datetime.now().isoformat(),
                'server_response': 'Pong from Little J',
                'data_received': data
            }
            
            return response
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
