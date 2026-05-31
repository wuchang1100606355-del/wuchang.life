# -*- coding: utf-8 -*-
"""
路由器中繼控制器 - 處理通過路由器的外網握手
"""
from odoo import http
from odoo.http import request
import json
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class RouterRelayController(http.Controller):
    
    @http.route('/api/relay/handshake', type='http', auth='public', methods=['GET', 'POST', 'OPTIONS'], csrf=False, cors='*')
    def router_relay_handshake(self, **kwargs):
        """通過路由器中繼的外網握手端點"""
        try:
            # 獲取請求信息
            client_ip = request.httprequest.remote_addr
            forwarded_for = request.httprequest.headers.get('X-Forwarded-For', '')
            via = request.httprequest.headers.get('Via', '')
            user_agent = request.httprequest.headers.get('User-Agent', 'Unknown')
            
            # 檢查是否通過路由器中繼
            is_relayed = bool(forwarded_for or via or '192.168.50.1' in forwarded_for)
            
            # 獲取本地 IP
            local_ip = request.httprequest.environ.get('SERVER_NAME', '192.168.50.249')
            
            handshake_response = {
                'status': 'success',
                'message': '通過路由器中繼握手成功',
                'timestamp': datetime.now().isoformat(),
                'relay': {
                    'enabled': True,
                    'router_ip': '192.168.50.1',
                    'relayed': is_relayed,
                    'via_router': '192.168.50.1' in forwarded_for or '192.168.50.1' in str(via)
                },
                'server': {
                    'ip': local_ip,
                    'hostname': 'Home-commput.wuchang.life',
                    'system': 'Wuchang OS V5.1.0',
                    'ai': 'Little J (小j)'
                },
                'client': {
                    'ip': client_ip,
                    'forwarded_for': forwarded_for if forwarded_for else None,
                    'via': via if via else None,
                    'user_agent': user_agent,
                    'method': request.httprequest.method
                },
                'endpoints': {
                    'command_center': '/command_center',
                    'design_report': '/design_report',
                    'handshake': '/api/handshake',
                    'relay_handshake': '/api/relay/handshake'
                },
                'access': {
                    'command_center_url': f'http://{local_ip}/command_center',
                    'report_url': f'http://{local_ip}/design_report',
                    'access_code': 'J2025'
                },
                'network': {
                    'local_network': '192.168.50.0/24',
                    'router_gateway': '192.168.50.1',
                    'external_access': 'via Cloudflare Tunnel or Router Port Forward'
                }
            }
            
            _logger.info(f"路由器中繼握手: {client_ip} -> {local_ip} (轉發: {forwarded_for})")
            
            headers = [
                ('Content-Type', 'application/json'),
                ('Access-Control-Allow-Origin', '*'),
                ('Access-Control-Allow-Methods', 'GET, POST, OPTIONS'),
                ('Access-Control-Allow-Headers', 'Content-Type, Authorization'),
                ('X-Handshake-Server', 'Wuchang-OS'),
                ('X-AI-Identity', 'Little-J'),
                ('X-Relay-Enabled', 'true'),
                ('X-Router-IP', '192.168.50.1')
            ]
            
            # 處理 OPTIONS 預檢請求
            if request.httprequest.method == 'OPTIONS':
                return request.make_response('', headers=headers)
            
            return request.make_response(
                json.dumps(handshake_response, ensure_ascii=False, indent=2),
                headers=headers
            )
        except Exception as e:
            _logger.error(f"路由器中繼握手錯誤: {e}")
            return request.make_response(
                json.dumps({
                    'status': 'error',
                    'message': str(e),
                    'timestamp': datetime.now().isoformat()
                }, ensure_ascii=False),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
    
    @http.route('/router/relay/status', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def router_relay_status(self, **kwargs):
        """路由器中繼狀態查詢"""
        return request.make_response(
            json.dumps({
                'status': 'active',
                'router_ip': '192.168.50.1',
                'local_ip': '192.168.50.249',
                'services': {
                    'odoo': {'port': 8069, 'accessible': True},
                    'caddy': {'port': 80, 'accessible': True},
                    'command_center': {'path': '/command_center', 'accessible': True}
                },
                'timestamp': datetime.now().isoformat()
            }, ensure_ascii=False),
            headers=[
                ('Content-Type', 'application/json'),
                ('Access-Control-Allow-Origin', '*')
            ]
        )
