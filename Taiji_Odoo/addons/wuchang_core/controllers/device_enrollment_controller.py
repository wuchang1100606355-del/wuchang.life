# -*- coding: utf-8 -*-
"""
設備納管控制器 - Chrome OS 設備 (端口 3477)
"""
from odoo import http
from odoo.http import request
import json
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class DeviceEnrollmentController(http.Controller):
    
    @http.route('/api/device/enroll/chrome_os', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def enroll_chrome_os_device(self, **kwargs):
        """Chrome OS 設備納管端點（包括客戶顯示器）"""
        try:
            data = request.jsonrequest or {}
            
            # 獲取設備信息
            device_id = data.get('device_id') or f"CHROME_OS_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            device_name = data.get('device_name') or f"Chrome OS Device ({datetime.now().strftime('%H:%M:%S')})"
            ip_address = data.get('ip_address') or request.httprequest.remote_addr
            mac_address = data.get('mac_address', '')
            port = data.get('port', 3477)
            device_purpose = data.get('device_purpose', '')  # 'customer_display', 'signage', 'other'
            display_url = data.get('display_url', '')  # 如果是客戶顯示器，可指定顯示 URL
            
            # 檢查是否已存在
            existing_device = request.env['wuchang.infrastructure.device'].sudo().search([
                ('device_type', '=', 'chrome_os'),
                ('ip_address', '=', ip_address)
            ], limit=1)
            
            if existing_device:
                # 更新現有設備
                note_parts = [f"重新連接於 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]
                if device_purpose:
                    note_parts.append(f"用途: {device_purpose}")
                if display_url:
                    note_parts.append(f"顯示 URL: {display_url}")
                
                existing_device.write({
                    'name': device_name,  # 更新設備名稱（可能改變）
                    'status': 'online',
                    'last_seen': datetime.now(),
                    'note': "，".join(note_parts)
                })
                device = existing_device
                action = 'updated'
            else:
                # 創建新設備記錄
                note_parts = [f"Chrome OS 設備納管，端口 {port}，納管時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]
                if device_purpose:
                    note_parts.append(f"用途: {device_purpose}")
                if display_url:
                    note_parts.append(f"顯示 URL: {display_url}")
                
                device = request.env['wuchang.infrastructure.device'].sudo().create({
                    'name': device_name,
                    'ip_address': ip_address,
                    'mac_address': mac_address,
                    'device_type': 'chrome_os',
                    'status': 'online',
                    'last_seen': datetime.now(),
                    'note': "，".join(note_parts)
                })
                action = 'enrolled'
            
            # 返回納管結果
            response = {
                'status': 'success',
                'action': action,
                'message': f'Chrome OS 設備{"已更新" if action == "updated" else "已納管"}',
                'device': {
                    'id': device.id,
                    'device_id': device_id,
                    'name': device.name,
                    'ip_address': device.ip_address,
                    'mac_address': device.mac_address,
                    'device_type': device.device_type,
                    'status': device.status,
                    'port': port,
                    'device_purpose': device_purpose,
                    'display_url': display_url,
                    'enrollment_time': datetime.now().isoformat()
                },
                'access': {
                    'command_center': f'/command_center',
                    'design_report': f'/design_report',
                    'handshake': f'/api/handshake',
                    'device_management': f'/web#id={device.id}&model=wuchang.infrastructure.device&view_type=form'
                },
                'capabilities': {
                    'web_access': True,
                    'api_access': True,
                    'remote_control': False,
                    'file_sharing': False,
                    'kiosk_mode': True
                }
            }
            
            _logger.info(f"Chrome OS 設備納管: {device_name} ({ip_address}:{port}) - {action}")
            
            return response
            
        except Exception as e:
            _logger.error(f"Chrome OS 設備納管錯誤: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    @http.route('/api/device/chrome_os/status', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def chrome_os_device_status(self, **kwargs):
        """查詢 Chrome OS 設備狀態"""
        try:
            ip_address = request.httprequest.args.get('ip') or request.httprequest.remote_addr
            
            device = request.env['wuchang.infrastructure.device'].sudo().search([
                ('device_type', '=', 'chrome_os'),
                ('ip_address', '=', ip_address)
            ], limit=1)
            
            if device:
                return request.make_response(
                    json.dumps({
                        'status': 'enrolled',
                        'device': {
                            'id': device.id,
                            'name': device.name,
                            'ip_address': device.ip_address,
                            'device_type': device.device_type,
                            'status': device.status,
                            'last_seen': device.last_seen.isoformat() if device.last_seen else None
                        }
                    }, ensure_ascii=False),
                    headers=[('Content-Type', 'application/json')]
                )
            else:
                return request.make_response(
                    json.dumps({
                        'status': 'not_enrolled',
                        'message': '設備未納管',
                        'enrollment_url': '/api/device/enroll/chrome_os'
                    }, ensure_ascii=False),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )
        except Exception as e:
            return request.make_response(
                json.dumps({
                    'status': 'error',
                    'message': str(e)
                }, ensure_ascii=False),
                headers=[('Content-Type', 'application/json')],
                status=500
            )
    
    @http.route('/api/device/chrome_os/heartbeat', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def chrome_os_heartbeat(self, **kwargs):
        """Chrome OS 設備心跳"""
        try:
            data = request.jsonrequest or {}
            ip_address = data.get('ip_address') or request.httprequest.remote_addr
            
            device = request.env['wuchang.infrastructure.device'].sudo().search([
                ('device_type', '=', 'chrome_os'),
                ('ip_address', '=', ip_address)
            ], limit=1)
            
            if device:
                device.write({
                    'status': 'online',
                    'last_seen': datetime.now()
                })
                return {
                    'status': 'success',
                    'message': '心跳更新成功',
                    'last_seen': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'not_enrolled',
                    'message': '設備未納管，請先進行納管',
                    'enrollment_url': '/api/device/enroll/chrome_os'
                }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    
    @http.route('/api/device/enroll/android', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def enroll_android_device(self, **kwargs):
        """Android POS 設備納管端點"""
        try:
            data = request.jsonrequest or {}
            
            # 獲取設備信息
            device_id = data.get('device_id') or f"ANDROID_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            device_name = data.get('device_name') or f"Android Device ({datetime.now().strftime('%H:%M:%S')})"
            ip_address = data.get('ip_address') or request.httprequest.remote_addr
            mac_address = data.get('mac_address', '')
            os_version = data.get('os_version', 'Unknown')
            device_type = data.get('device_type', 'pos')
            port = data.get('port', None)
            developer_mode = data.get('developer_mode', False)
            demo_mode = data.get('demo_mode', False)
            debug_options = data.get('debug_options', {})
            anydesk_id = data.get('anydesk_id', '')
            anydesk_password = data.get('anydesk_password', '')
            anydesk_configured = data.get('anydesk_configured', False)
            
            # 檢查是否已存在（通過 IP 或設備名稱）
            existing_device = request.env['wuchang.infrastructure.device'].sudo().search([
                ('device_type', '=', 'pos'),
                '|',
                ('ip_address', '=', ip_address),
                ('name', '=', device_name)
            ], limit=1)
            
            # 檢查是否為 v3_mix_edla_gl（主要 POS 設備）
            is_v3_primary = 'v3_mix_edla_gl' in device_name.lower() or data.get('is_primary', False)
            
            # 如果是主要 POS 設備，將其他 POS 設備標記為即將汰換
            if is_v3_primary:
                other_pos_devices = request.env['wuchang.infrastructure.device'].sudo().search([
                    ('device_type', '=', 'pos'),
                    ('is_primary', '=', True),
                    ('id', '!=', existing_device.id if existing_device else 0)
                ])
                for old_pos in other_pos_devices:
                    old_pos.write({
                        'status': 'deprecated',
                        'is_primary': False,
                        'note': f"{old_pos.note or ''}，已被 {device_name} 取代，即將汰換"
                    })
            
            if existing_device:
                # 更新現有設備
                note_parts = [f"Android {os_version} 設備重新連接，IP: {ip_address}{f':{port}' if port else ''}，開發者模式: {'已開啟' if developer_mode else '未開啟'}，Demo Mode: {'已開啟' if demo_mode else '未開啟'}，偵錯選項: USB={debug_options.get('usb', False)}, GPU={debug_options.get('gpu', False)}, WiFi={debug_options.get('wifi', False)}，更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]
                if is_v3_primary:
                    note_parts.append("主要 POS 設備（v3_mix_edla_gl），原 POS 設備即將汰換")
                
                existing_device.write({
                    'name': device_name,
                    'status': 'online',
                    'is_primary': is_v3_primary,
                    'last_seen': datetime.now(),
                    'note': "，".join(note_parts)
                })
                device = existing_device
                action = 'updated'
            else:
                # 創建新設備記錄
                note_parts = [f"Android {os_version} POS 設備納管，IP: {ip_address}{f':{port}' if port else ''}，開發者模式: {'已開啟' if developer_mode else '未開啟'}，Demo Mode: {'已開啟' if demo_mode else '未開啟'}，偵錯選項: USB={debug_options.get('usb', False)}, GPU={debug_options.get('gpu', False)}, WiFi={debug_options.get('wifi', False)}，納管時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]
                if is_v3_primary:
                    note_parts.append("主要 POS 設備（v3_mix_edla_gl），原 POS 設備即將汰換")
                
                create_vals = {
                    'name': device_name,
                    'ip_address': ip_address,
                    'mac_address': mac_address,
                    'device_type': 'pos',
                    'status': 'online',
                    'is_primary': is_v3_primary,
                    'last_seen': datetime.now(),
                    'note': "，".join(note_parts)
                }
                if anydesk_id:
                    create_vals['anydesk_id'] = anydesk_id
                if anydesk_password:
                    create_vals['anydesk_password'] = anydesk_password
                if anydesk_configured is not None:
                    create_vals['anydesk_configured'] = anydesk_configured
                device = request.env['wuchang.infrastructure.device'].sudo().create(create_vals)
                action = 'enrolled'
            
            # 返回納管結果
            response = {
                'status': 'success',
                'action': action,
                'message': f'Android POS 設備{"已更新" if action == "updated" else "已納管"}',
                'device': {
                    'id': device.id,
                    'device_id': device_id,
                    'name': device.name,
                    'ip_address': device.ip_address,
                    'mac_address': device.mac_address,
                    'device_type': device.device_type,
                    'os_version': os_version,
                    'status': device.status,
                    'port': port,
                    'developer_mode': developer_mode,
                    'demo_mode': demo_mode,
                    'debug_options': debug_options,
                    'enrollment_time': datetime.now().isoformat()
                },
                'access': {
                    'command_center': f'/command_center',
                    'sister_control': f'/wuchang/sister/poll',
                    'device_management': f'/web#id={device.id}&model=wuchang.infrastructure.device&view_type=form'
                },
                'capabilities': data.get('capabilities', {
                    'kiosk_mode': True,
                    'remote_management': True,
                    'app_deployment': True,
                    'data_sync': True,
                }),
                'recommendations': {
                    'demo_mode': {
                        'required': False,
                        'reason': 'Demo Mode 主要用於零售展示，POS 設備應使用 Google Workspace MDM 的 Kiosk 模式',
                        'alternative': '使用 Google Workspace MDM 設定 Kiosk 模式鎖定到 Odoo POS 應用'
                    },
                    'developer_mode': {
                        'status': 'enabled' if developer_mode else 'disabled',
                        'note': '開發者模式已開啟，可用於設備管理和調試'
                    }
                }
            }
            
            _logger.info(f"Android POS 設備納管: {device_name} ({ip_address}, Android {os_version}) - {action}")
            
            return response
            
        except Exception as e:
            _logger.error(f"Android POS 設備納管錯誤: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    @http.route('/api/device/enroll/customer_display', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def enroll_customer_display(self, **kwargs):
        """
        客戶顯示器納管端點（相容性端點）
        注意：客戶顯示器就是 Chrome OS 設備，此端點會轉發到 Chrome OS 納管
        """
        try:
            data = request.jsonrequest or {}
            
            # 轉換為 Chrome OS 納管格式
            chrome_os_data = {
                'device_name': data.get('device_name') or f"Customer Display ({datetime.now().strftime('%H:%M:%S')})",
                'ip_address': data.get('ip_address') or request.httprequest.remote_addr,
                'mac_address': data.get('mac_address', ''),
                'port': data.get('port', 3477),
                'device_purpose': 'customer_display',  # 標記為客戶顯示器
                'display_url': data.get('display_url', 'http://localhost:8069/pos/customer_display')
            }
            
            # 調用 Chrome OS 納管方法（使用內部方法調用）
            # 由於是內部調用，我們需要手動處理數據
            ip_address = chrome_os_data['ip_address']
            device_name = chrome_os_data['device_name']
            mac_address = chrome_os_data['mac_address']
            port = chrome_os_data['port']
            device_purpose = chrome_os_data['device_purpose']
            display_url = chrome_os_data['display_url']
            
            # 檢查是否已存在（使用 chrome_os 類型）
            existing_device = request.env['wuchang.infrastructure.device'].sudo().search([
                ('device_type', '=', 'chrome_os'),
                ('ip_address', '=', ip_address)
            ], limit=1)
            
            if existing_device:
                # 更新現有設備
                note_parts = [f"重新連接於 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]
                if device_purpose:
                    note_parts.append(f"用途: {device_purpose}")
                if display_url:
                    note_parts.append(f"顯示 URL: {display_url}")
                
                existing_device.write({
                    'name': device_name,
                    'status': 'online',
                    'last_seen': datetime.now(),
                    'note': "，".join(note_parts)
                })
                device = existing_device
                action = 'updated'
            else:
                # 創建新設備記錄（使用 chrome_os 類型）
                note_parts = [f"Chrome OS 設備納管，端口 {port}，納管時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]
                if device_purpose:
                    note_parts.append(f"用途: {device_purpose}")
                if display_url:
                    note_parts.append(f"顯示 URL: {display_url}")
                
                device = request.env['wuchang.infrastructure.device'].sudo().create({
                    'name': device_name,
                    'ip_address': ip_address,
                    'mac_address': mac_address,
                    'device_type': 'chrome_os',  # 使用 chrome_os 類型
                    'status': 'online',
                    'last_seen': datetime.now(),
                    'note': "，".join(note_parts)
                })
                action = 'enrolled'
            
            # 返回納管結果
            response = {
                'status': 'success',
                'action': action,
                'message': f'客戶顯示器（Chrome OS）{"已更新" if action == "updated" else "已納管"}',
                'device': {
                    'id': device.id,
                    'device_id': f"CHROME_OS_{device_name.replace(' ', '_').upper()}",
                    'name': device.name,
                    'ip_address': device.ip_address,
                    'mac_address': device.mac_address,
                    'device_type': device.device_type,
                    'status': device.status,
                    'port': port,
                    'device_purpose': device_purpose,
                    'display_url': display_url,
                    'enrollment_time': datetime.now().isoformat()
                },
                'access': {
                    'display_url': display_url,
                    'device_management': f'/web#id={device.id}&model=wuchang.infrastructure.device&view_type=form',
                    'sister_control': f'/web#action=&model=wuchang.sister.control&view_type=form'
                },
                'capabilities': {
                    'web_display': True,
                    'remote_control': True,
                    'content_update': True,
                    'kiosk_mode': True
                }
            }
            
            _logger.info(f"客戶顯示器（Chrome OS）納管: {device_name} ({ip_address}:{port}) - {action}")
            
            return response
            
        except Exception as e:
            _logger.error(f"客戶顯示器納管錯誤: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    @http.route('/api/device/android/status', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def android_device_status(self, **kwargs):
        """查詢 Android 設備狀態"""
        try:
            ip_address = request.httprequest.args.get('ip') or request.httprequest.remote_addr
            
            device = request.env['wuchang.infrastructure.device'].sudo().search([
                ('device_type', '=', 'pos'),
                ('ip_address', '=', ip_address)
            ], limit=1)
            
            if device:
                return request.make_response(
                    json.dumps({
                        'status': 'enrolled',
                        'device': {
                            'id': device.id,
                            'name': device.name,
                            'ip_address': device.ip_address,
                            'device_type': device.device_type,
                            'status': device.status,
                            'last_seen': device.last_seen.isoformat() if device.last_seen else None
                        }
                    }, ensure_ascii=False),
                    headers=[('Content-Type', 'application/json')]
                )
            else:
                return request.make_response(
                    json.dumps({
                        'status': 'not_enrolled',
                        'message': '設備未納管',
                        'enrollment_url': '/api/device/enroll/android'
                    }, ensure_ascii=False),
                    headers=[('Content-Type', 'application/json')],
                    status=404
                )
        except Exception as e:
            return request.make_response(
                json.dumps({
                    'status': 'error',
                    'message': str(e)
                }, ensure_ascii=False),
                headers=[('Content-Type', 'application/json')],
                status=500
            )