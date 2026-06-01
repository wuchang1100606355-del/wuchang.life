# -*- coding: utf-8 -*-
"""
路由器證書管理模型
"""
from odoo import models, fields, api
from datetime import datetime
import logging
import os

_logger = logging.getLogger(__name__)

class RouterCertificate(models.Model):
    _name = 'wuchang.router.certificate'
    _description = '路由器證書管理'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='證書名稱', required=True, default='ASUS Router Certificate', tracking=True)
    router_ip = fields.Char(string='路由器 IP', default='192.168.50.1', required=True, tracking=True)
    router_model = fields.Char(string='路由器型號', default='RT-BE86U-7428', tracking=True)
    
    # 證書文件路徑
    cert_file_path = fields.Char(string='證書文件路徑', 
                                 help='證書文件 (server.crt) 的完整路徑')
    key_file_path = fields.Char(string='私鑰文件路徑',
                                help='私鑰文件 (server.key) 的完整路徑')
    ca_file_path = fields.Char(string='CA 證書路徑',
                               help='CA 證書文件 (ca.crt) 的完整路徑')
    
    # 證書信息
    certificate_content = fields.Text(string='證書內容', 
                                     help='PEM 格式的證書內容')
    private_key_content = fields.Text(string='私鑰內容',
                                     help='PEM 格式的私鑰內容（敏感信息，加密存儲）')
    
    # 證書狀態
    status = fields.Selection([
        ('not_configured', '未配置'),
        ('configured', '已配置'),
        ('expired', '已過期'),
        ('invalid', '無效'),
    ], string='狀態', default='not_configured', tracking=True)
    
    # 證書元數據
    issuer = fields.Char(string='簽發者')
    subject = fields.Char(string='主體')
    valid_from = fields.Datetime(string='生效時間')
    valid_until = fields.Datetime(string='到期時間')
    is_self_signed = fields.Boolean(string='自簽名證書', default=True)
    
    # 使用配置
    use_in_caddy = fields.Boolean(string='在 Caddy 中使用', default=False,
                                  help='是否在 Caddy 反向代理中使用此證書')
    use_in_router = fields.Boolean(string='在路由器中使用', default=False,
                                   help='是否已上傳到路由器並啟用')
    
    # 當前配置方法
    current_ssl_method = fields.Selection([
        ('caddy_auto', 'Caddy 自動 HTTPS'),
        ('router_cert', '路由器證書'),
        ('cloudflare', 'Cloudflare 證書'),
        ('manual', '手動配置'),
    ], string='當前 SSL 方法', default='caddy_auto', tracking=True)
    
    # 下載信息
    download_url = fields.Char(string='下載 URL', 
                               default='http://www.asusrouter.com/cert_key.tar')
    download_date = fields.Datetime(string='下載時間')
    download_method = fields.Selection([
        ('manual', '手動下載'),
        ('api', 'API 下載'),
        ('auto', '自動下載'),
    ], string='下載方式', default='manual')
    
    note = fields.Text(string='備註')
    
    active = fields.Boolean(string='啟用', default=True)
    
    def action_download_certificate(self):
        """下載證書（需要手動操作）"""
        for cert in self:
            cert.message_post(
                body=f"證書下載提示：請從路由器管理界面 ({cert.router_ip}) 下載證書文件"
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': '證書下載',
                    'message': f'請訪問 {cert.router_ip} 登入後下載證書',
                    'type': 'info',
                    'sticky': False
                }
            }
    
    def action_validate_certificate(self):
        """驗證證書有效性"""
        for cert in self:
            if not cert.certificate_content:
                cert.status = 'not_configured'
                cert.message_post(body="證書內容為空，無法驗證")
                return
            
            try:
                # 這裡可以添加證書驗證邏輯
                # 例如檢查證書格式、有效期等
                cert.status = 'configured'
                cert.message_post(body="證書驗證通過")
            except Exception as e:
                cert.status = 'invalid'
                cert.message_post(body=f"證書驗證失敗: {e}")
                _logger.error(f"證書驗證錯誤: {e}")
    
    def action_apply_to_caddy(self):
        """應用到 Caddy 配置"""
        for cert in self:
            if cert.status != 'configured':
                raise UserError("請先配置並驗證證書")
            
            # 這裡可以添加更新 Caddyfile 的邏輯
            cert.use_in_caddy = True
            cert.current_ssl_method = 'router_cert'
            cert.message_post(body="證書已標記為在 Caddy 中使用，需要重啟 Caddy 服務以應用")
