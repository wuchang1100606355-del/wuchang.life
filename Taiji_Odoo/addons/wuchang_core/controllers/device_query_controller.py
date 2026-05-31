# -*- coding: utf-8 -*-
"""
設備查詢控制器 - 查詢設備納管狀態和方案
"""
from odoo import http
from odoo.http import request
import json
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class DeviceQueryController(http.Controller):
    
    @http.route('/api/device/query/<string:ip_address>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def query_device_status(self, ip_address, **kwargs):
        """查詢設備納管狀態和適用的控制方案"""
        try:
            # 1. 查詢設備
            devices = request.env['wuchang.infrastructure.device'].sudo().search([
                ('ip_address', '=', ip_address)
            ])
            
            device_data = None
            if devices:
                device = devices[0]
                device_data = {
                    'id': device.id,
                    'name': device.name,
                    'ip_address': device.ip_address,
                    'mac_address': device.mac_address,
                    'device_type': device.device_type,
                    'status': device.status,
                    'last_seen': device.last_seen.isoformat() if device.last_seen else None,
                    'enrolled': True
                }
            else:
                device_data = {
                    'ip_address': ip_address,
                    'enrolled': False
                }
            
            # 2. 查詢適用的控制方案
            device_type = device_data.get('device_type') if device_data and device_data.get('enrolled') else None
            
            suitable_plans = request.env['wuchang.device.control.plan'].sudo().search([
                ('status', '=', 'active'),
                '|',
                ('device_type', '=', device_type) if device_type else ('id', '=', False),
                ('device_type', '=', 'all')
            ])
            
            plans_data = []
            for plan in suitable_plans:
                plans_data.append({
                    'id': plan.id,
                    'name': plan.name,
                    'plan_type': plan.plan_type,
                    'device_type': plan.device_type,
                    'priority': plan.priority,
                    'control_strategy': plan.control_strategy,
                    'enrollment_method': plan.enrollment_method,
                    'monitor_enabled': plan.monitor_enabled,
                    'device_count': plan.device_count,
                    'device_included': device_data['id'] in plan.device_ids.ids if device_data and device_data.get('enrolled') else False
                })
            
            # 3. 構建響應
            response = {
                'status': 'success',
                'timestamp': datetime.now().isoformat(),
                'ip_address': ip_address,
                'device': device_data,
                'suitable_plans': plans_data,
                'recommendations': []
            }
            
            # 生成建議
            if not device_data or not device_data.get('enrolled'):
                response['recommendations'].append({
                    'action': 'enroll',
                    'message': f'設備 {ip_address} 尚未納管，建議執行納管操作',
                    'endpoint': '/api/device/enroll/chrome_os' if device_type == 'chrome_os' else '創建設備記錄'
                })
            
            if plans_data:
                response['recommendations'].append({
                    'action': 'apply_plan',
                    'message': f'找到 {len(plans_data)} 個適用的控制方案',
                    'plans': [{'id': p['id'], 'name': p['name']} for p in plans_data]
                })
            
            return request.make_response(
                json.dumps(response, ensure_ascii=False, indent=2),
                headers=[
                    ('Content-Type', 'application/json'),
                    ('Access-Control-Allow-Origin', '*')
                ]
            )
            
        except Exception as e:
            _logger.error(f"設備查詢錯誤: {e}")
            return request.make_response(
                json.dumps({
                    'status': 'error',
                    'message': str(e),
                    'timestamp': datetime.now().isoformat()
                }, ensure_ascii=False),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
