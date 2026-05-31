# -*- coding: utf-8 -*-
"""
API 帳戶分離系統
區分商業用途與非營利用途的 API 配置
"""
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class APIAccountSeparation(models.Model):
    _name = 'wuchang.api.account.separation'
    _description = 'API 帳戶分離配置'
    _order = 'usage_type, name'

    name = fields.Char(string='配置名稱', required=True)
    usage_type = fields.Selection([
        ('commercial', '商業用途'),
        ('nonprofit', '非營利用途'),
    ], string='用途類型', required=True, index=True)
    
    # Google API 配置
    google_api_key = fields.Char(string='Google API Key', help='API 金鑰')
    google_project_id = fields.Char(string='Google Project ID', help='GCP 專案 ID')
    google_location = fields.Char(string='Google Location', default='us-central1', help='GCP 區域')
    
    # 抵免額度配置
    credit_account_type = fields.Selection([
        ('commercial_credits', '商業帳戶抵免額度'),
        ('nonprofit_credits', '非營利補助額度'),
        ('personal_credits', '個人帳戶抵免額度'),
    ], string='抵免額度類型', help='使用的抵免額度來源')
    
    # 適用範圍
    applicable_services = fields.Selection([
        ('voice_conversation', '語音對話服務'),
        ('pos_system', 'POS 系統'),
        ('document_generation', '文件生成'),
        ('all', '所有服務'),
    ], string='適用服務', default='all', help='此配置適用的服務範圍')
    
    # 優先級（數字越小優先級越高）
    priority = fields.Integer(string='優先級', default=10, help='數字越小優先級越高')
    
    # 狀態
    is_active = fields.Boolean(string='啟用', default=True)
    
    # 使用統計
    usage_count = fields.Integer(string='使用次數', default=0, readonly=True)
    last_used_date = fields.Datetime(string='最後使用時間', readonly=True)
    
    note = fields.Text(string='備註')
    
    @api.model
    def get_api_config(self, usage_type='nonprofit', service='voice_conversation'):
        """
        根據用途類型和服務獲取 API 配置
        
        Args:
            usage_type: 'commercial' 或 'nonprofit'
            service: 服務類型（'voice_conversation', 'pos_system', 'document_generation', 'all'）
        
        Returns:
            dict: API 配置字典，包含 google_api_key, google_project_id 等
        """
        # 搜尋符合條件的配置
        domain = [
            ('usage_type', '=', usage_type),
            ('is_active', '=', True),
            '|',
            ('applicable_services', '=', service),
            ('applicable_services', '=', 'all'),
        ]
        
        configs = self.search(domain, order='priority asc', limit=1)
        
        if configs:
            config = configs[0]
            # 更新使用統計
            config.write({
                'usage_count': config.usage_count + 1,
                'last_used_date': fields.Datetime.now(),
            })
            
            return {
                'google_api_key': config.google_api_key or '',
                'google_project_id': config.google_project_id or '',
                'google_location': config.google_location or 'us-central1',
                'credit_account_type': config.credit_account_type or '',
                'config_id': config.id,
            }
        
        # 如果找不到配置，返回預設值（從系統參數讀取）
        params = self.env['ir.config_parameter'].sudo()
        return {
            'google_api_key': params.get_param('wuchang.google_api_key') or '',
            'google_project_id': params.get_param('wuchang.google.project_id') or '',
            'google_location': params.get_param('wuchang.google.location') or 'us-central1',
            'credit_account_type': 'nonprofit_credits' if usage_type == 'nonprofit' else 'commercial_credits',
            'config_id': False,
        }
    
    @api.model
    def ensure_default_configs(self):
        """確保有預設的配置記錄"""
        # 非營利配置（預設）
        nonprofit_config = self.search([
            ('usage_type', '=', 'nonprofit'),
            ('name', '=', '非營利預設配置'),
        ], limit=1)
        
        if not nonprofit_config:
            params = self.env['ir.config_parameter'].sudo()
            self.create({
                'name': '非營利預設配置',
                'usage_type': 'nonprofit',
                'google_api_key': params.get_param('wuchang.google_api_key') or '',
                'google_project_id': params.get_param('wuchang.google.project_id') or '',
                'google_location': params.get_param('wuchang.google.location') or 'us-central1',
                'credit_account_type': 'nonprofit_credits',
                'applicable_services': 'all',
                'priority': 10,
                'is_active': True,
                'note': '非營利用途預設配置（POS、社區服務等）',
            })
        
        # 商業配置（需要手動設定）
        commercial_config = self.search([
            ('usage_type', '=', 'commercial'),
            ('name', '=', '商業預設配置'),
        ], limit=1)
        
        if not commercial_config:
            self.create({
                'name': '商業預設配置',
                'usage_type': 'commercial',
                'google_api_key': '',
                'google_project_id': '',
                'google_location': 'us-central1',
                'credit_account_type': 'commercial_credits',
                'applicable_services': 'all',
                'priority': 5,
                'is_active': False,  # 預設不啟用，需要手動配置
                'note': '商業用途配置（需設定商業帳戶 API 金鑰和抵免額度）',
            })
        
        return True
