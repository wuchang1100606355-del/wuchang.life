# -*- coding: utf-8 -*-
"""
路由器證書控制器 - 管理和下載路由器證書
"""
from odoo import http
from odoo.http import request
import json
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class RouterCertificateController(http.Controller):
    
    @http.route('/api/router/certificate/info', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def router_certificate_info(self, **kwargs):
        """獲取路由器證書信息"""
        try:
            router_info = {
                'router_ip': '192.168.50.1',
                'router_model': 'RT-BE86U-7428',
                'admin_url': 'http://192.168.50.1',
                'certificate_endpoints': {
                    'download_url': 'http://www.asusrouter.com/cert_key.tar',
                    'local_url': 'http://192.168.50.1/cert_key.tar',
                    'admin_path': '系統管理 → 系統設定 → 憑證設定'
                },
                'current_config': {
                    'method': 'caddy_auto_https',
                    'status': 'active',
                    'description': '使用 Caddy 自動 HTTPS，通過 Cloudflare 隧道提供外網訪問'
                },
                'certificate_location': {
                    'cert_dir': '/router_certificates',
                    'files': ['server.crt', 'server.key', 'ca.crt']
                },
                'recommendations': [
                    '使用 Caddy 自動 HTTPS（推薦，當前方案）',
                    '如需路由器本地 HTTPS，從管理界面下載證書',
                    '證書文件應保存在 router_certificates/ 目錄'
                ]
            }
            
            return request.make_response(
                json.dumps(router_info, ensure_ascii=False, indent=2),
                headers=[
                    ('Content-Type', 'application/json'),
                    ('Access-Control-Allow-Origin', '*')
                ]
            )
        except Exception as e:
            _logger.error(f"路由器證書信息查詢錯誤: {e}")
            return request.make_response(
                json.dumps({
                    'status': 'error',
                    'message': str(e)
                }, ensure_ascii=False),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
    
    @http.route('/api/router/certificate/status', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def router_certificate_status(self, **kwargs):
        """查詢路由器證書狀態"""
        import os
        
        cert_dir = '/router_certificates'  # 在容器內的路徑
        cert_files = []
        
        # 檢查證書文件（如果在容器內）
        if os.path.exists(cert_dir):
            for file in os.listdir(cert_dir):
                if file.endswith(('.crt', '.key', '.pem', '.cert')):
                    file_path = os.path.join(cert_dir, file)
                    if os.path.isfile(file_path):
                        cert_files.append({
                            'name': file,
                            'size': os.path.getsize(file_path),
                            'path': file_path
                        })
        
        status = {
            'certificate_configured': len(cert_files) > 0,
            'certificate_files': cert_files,
            'current_method': 'caddy_auto_https',
            'router_https_enabled': False,  # 需要實際檢查
            'caddy_https_enabled': True,
            'cloudflare_tunnel': True,
            'recommendation': '繼續使用 Caddy 自動 HTTPS（無需配置路由器證書）'
        }
        
        return request.make_response(
            json.dumps(status, ensure_ascii=False, indent=2),
            headers=[
                ('Content-Type', 'application/json'),
                ('Access-Control-Allow-Origin', '*')
            ]
        )
