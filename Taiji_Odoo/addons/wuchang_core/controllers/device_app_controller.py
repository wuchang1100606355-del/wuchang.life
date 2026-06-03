# -*- coding: utf-8 -*-
"""
設備專屬 APP 端點控制器
為每個納管的設備提供專屬的訪問端點，類似移動應用程式的深度連結
"""
from odoo import http
from odoo.http import request
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class DeviceAppController(http.Controller):
    """設備專屬 APP 端點控制器"""

    @http.route('/device/<string:device_token>/app', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def device_web_app(self, device_token, **kwargs):
        """設備專屬網頁 APP - 包含定位和地圖功能"""
        try:
            # 查找設備
            device = request.env['wuchang.infrastructure.device'].sudo().search([
                ('device_token', '=', device_token)
            ], limit=1)
            
            if not device:
                return request.render('wuchang_core.device_not_found', {
                    'error': '設備未找到或 Token 無效'
                })
            
            # 更新最後訪問時間
            device.write({
                'last_seen': datetime.now(),
                'status': 'online'
            })
            
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
            
            return request.render('wuchang_core.device_web_app', {
                'device': device,
                'device_name': device.name,
                'device_token': device_token,
                'device_type': device.device_type,
                'base_url': base_url,
                'latitude': device.latitude or 0,
                'longitude': device.longitude or 0,
                'location_address': device.location_address or '',
            })
            
        except Exception as e:
            _logger.error(f"設備網頁 APP 訪問錯誤: {e}")
            return request.render('wuchang_core.device_error', {
                'error': str(e)
            })
    
    @http.route('/device/<string:device_token>/location', type='json', auth='public', methods=['POST'], csrf=False, cors='*')
    def update_device_location(self, device_token, **kwargs):
        """更新設備地理位置"""
        try:
            data = request.jsonrequest or {}
            
            device = request.env['wuchang.infrastructure.device'].sudo().search([
                ('device_token', '=', device_token)
            ], limit=1)
            
            if not device:
                return {
                    'status': 'error',
                    'message': '設備未找到或 Token 無效'
                }
            
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            address = data.get('address', '')
            
            if latitude is None or longitude is None:
                return {
                    'status': 'error',
                    'message': '缺少緯度或經度資訊'
                }
            
            # 更新設備位置
            device.write({
                'latitude': latitude,
                'longitude': longitude,
                'location_address': address,
                'location_updated': datetime.now(),
                'last_seen': datetime.now(),
                'status': 'online'
            })
            
            _logger.info(f"設備 {device.name} 位置已更新: ({latitude}, {longitude})")
            
            return {
                'status': 'success',
                'message': '位置已更新',
                'device': {
                    'name': device.name,
                    'latitude': device.latitude,
                    'longitude': device.longitude,
                    'address': device.location_address,
                    'updated': device.location_updated.isoformat() if device.location_updated else None
                }
            }
            
        except Exception as e:
            _logger.error(f"更新設備位置錯誤: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    @http.route('/elderly/<string:device_token>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def elderly_app_endpoint(self, device_token, **kwargs):
        """長者專用簡化界面 - 類似假 AI 應用"""
        try:
            # 查找設備
            device = request.env['wuchang.infrastructure.device'].sudo().search([
                ('device_token', '=', device_token)
            ], limit=1)
            
            if not device:
                return request.render('wuchang_core.elderly_device_not_found', {
                    'error': '設備未找到'
                })
            
            # 更新最後訪問時間
            device.write({
                'last_seen': datetime.now(),
                'status': 'online'
            })
            
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
            
            return request.render('wuchang_core.elderly_app', {
                'device': device,
                'device_name': device.name,
                'device_token': device_token,
                'base_url': base_url,
            })
            
        except Exception as e:
            _logger.error(f"長者 APP 端點訪問錯誤: {e}")
            return request.render('wuchang_core.elderly_error', {
                'error': str(e)
            })
    
    @http.route('/device/<string:device_token>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def device_app_endpoint(self, device_token, **kwargs):
        """設備專屬端點 - 類似 APP 的深度連結"""
        try:
            # 查找設備
            device = request.env['wuchang.infrastructure.device'].sudo().search([
                ('device_token', '=', device_token)
            ], limit=1)
            
            if not device:
                return request.render('wuchang_core.device_not_found', {
                    'error': '設備未找到或 Token 無效'
                })
            
            # 更新最後訪問時間
            device.write({
                'last_seen': datetime.now(),
                'status': 'online'
            })
            
            # 根據設備類型返回不同的界面
            if device.device_type == 'pos':
                return self._render_pos_app(device, **kwargs)
            elif device.device_type == 'chrome_os':
                return self._render_chrome_os_app(device, **kwargs)
            else:
                return self._render_generic_app(device, **kwargs)
                
        except Exception as e:
            _logger.error(f"設備端點訪問錯誤: {e}")
            return request.render('wuchang_core.device_error', {
                'error': str(e)
            })
    
    def _render_pos_app(self, device, **kwargs):
        """渲染 POS 設備專屬界面"""
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
        
        return request.render('wuchang_core.device_pos_app', {
            'device': device,
            'pos_url': f"{base_url}/pos/ui",
            'device_name': device.name,
            'device_ip': device.ip_address,
            'device_status': device.status,
            'is_primary': device.is_primary,
            'anydesk_id': device.anydesk_id or '',
            'anydesk_configured': device.anydesk_configured,
            'last_seen': device.last_seen.strftime('%Y-%m-%d %H:%M:%S') if device.last_seen else '從未',
        })
    
    def _render_chrome_os_app(self, device, **kwargs):
        """渲染 Chrome OS 設備專屬界面"""
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
        
        # 判斷是否為客戶顯示器
        device_purpose = kwargs.get('purpose', 'unknown')
        is_customer_display = device_purpose == 'customer_display'
        
        if is_customer_display:
            customer_display_url = f"{base_url}/pos/customer_display"
            return request.render('wuchang_core.device_customer_display_app', {
                'device': device,
                'customer_display_url': customer_display_url,
                'device_name': device.name,
                'device_ip': device.ip_address,
            })
        else:
            return self._render_generic_app(device, **kwargs)
    
    def _render_generic_app(self, device, **kwargs):
        """渲染通用設備界面"""
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
        
        return request.render('wuchang_core.device_generic_app', {
            'device': device,
            'device_name': device.name,
            'device_ip': device.ip_address,
            'device_type': device.device_type,
            'device_status': device.status,
            'base_url': base_url,
        })
    
    @http.route('/device/<string:device_token>/status', type='json', auth='public', methods=['GET', 'POST'], csrf=False, cors='*')
    def device_status_api(self, device_token, **kwargs):
        """設備狀態 API - 供設備查詢自身狀態"""
        try:
            device = request.env['wuchang.infrastructure.device'].sudo().search([
                ('device_token', '=', device_token)
            ], limit=1)
            
            if not device:
                return {
                    'status': 'error',
                    'message': '設備未找到或 Token 無效'
                }
            
            # 更新最後訪問時間
            device.write({
                'last_seen': datetime.now(),
                'status': 'online'
            })
            
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
            
            return {
                'status': 'success',
                'device': {
                    'id': device.id,
                    'name': device.name,
                    'ip_address': device.ip_address,
                    'device_type': device.device_type,
                    'status': device.status,
                    'is_primary': device.is_primary,
                    'anydesk_id': device.anydesk_id or '',
                    'anydesk_configured': device.anydesk_configured,
                },
                'endpoints': {
                    'pos_ui': f"{base_url}/pos/ui" if device.device_type == 'pos' else None,
                    'customer_display': f"{base_url}/pos/customer_display" if device.device_type == 'chrome_os' else None,
                    'sister_control': f"{base_url}/wuchang/sister/poll",
                    'device_management': f"{base_url}/web#id={device.id}&model=wuchang.infrastructure.device&view_type=form",
                },
                'last_seen': device.last_seen.isoformat() if device.last_seen else None,
            }
            
        except Exception as e:
            _logger.error(f"設備狀態 API 錯誤: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    @http.route('/device/<string:device_token>/qr', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def device_qr_code(self, device_token, **kwargs):
        """生成設備專屬端點的 QR Code"""
        try:
            device = request.env['wuchang.infrastructure.device'].sudo().search([
                ('device_token', '=', device_token)
            ], limit=1)
            
            if not device:
                return request.not_found()
            
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
            endpoint_url = f"{base_url}/device/{device_token}"
            
            # 生成 QR Code
            try:
                import qrcode
                from io import BytesIO
                
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(endpoint_url)
                qr.make(fit=True)
                
                img = qr.make_image(fill_color="black", back_color="white")
                img_buffer = BytesIO()
                img.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                
                return request.make_response(
                    img_buffer.read(),
                    headers=[
                        ('Content-Type', 'image/png'),
                        ('Content-Disposition', f'inline; filename="device_{device.id}_qr.png"')
                    ]
                )
            except ImportError:
                # 如果沒有 qrcode 庫，返回文字格式的 QR Code 連結
                return request.render('wuchang_core.device_qr_text', {
                    'device': device,
                    'endpoint_url': endpoint_url,
                })
                
        except Exception as e:
            _logger.error(f"QR Code 生成錯誤: {e}")
            return request.not_found()
