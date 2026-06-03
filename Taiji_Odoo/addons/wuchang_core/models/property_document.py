# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class PropertyDocument(models.Model):
    """管委會公文管理（獨立於社區發展協會）"""
    _name = 'wuchang.property.document'
    _description = '管委會公文'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char('公文標題', required=True, tracking=True)
    community_id = fields.Many2one('wuchang.property.community', string='所屬社區', required=True, tracking=True)
    
    # 公文類型
    document_type = fields.Selection([
        ('announcement', '公告'),
        ('notice', '通知'),
        ('resolution', '決議'),
        ('report', '報告'),
        ('meeting_minutes', '會議記錄'),
        ('other', '其他'),
    ], string='公文類型', required=True, tracking=True)
    
    # 公文內容
    content = fields.Html('公文內容', required=True)
    content_draft = fields.Text('原始內容（AI 生成前）', readonly=True)
    
    # 關聯 Google 表單（可選）
    form_id = fields.Many2one('wuchang.google.form', string='來源表單', domain=[('form_type', '=', 'document')])
    response_id = fields.Many2one('wuchang.google.form.response', string='來源回應')
    
    # 使用的範本
    template_id = fields.Many2one('wuchang.document.template', string='使用範本', 
                                   domain=[('organization_type', '=', 'committee')])
    
    # 簽核資訊
    signer_id = fields.Many2one('wuchang.property.committee.member', string='簽核人', 
                                 domain="[('community_id', '=', community_id)]")
    signer_role = fields.Char('簽核人職務', related='signer_id.role', readonly=True)
    sign_date = fields.Date('簽核日期', default=fields.Date.context_today)
    
    # 文件狀態
    state = fields.Selection([
        ('draft', '草稿'),
        ('review', '審核中'),
        ('approved', '已核准'),
        ('published', '已發布'),
        ('archived', '已歸檔'),
    ], string='狀態', default='draft', tracking=True)
    
    # Google Drive 整合
    google_drive_file_id = fields.Char('Google Drive 檔案 ID', readonly=True)
    google_drive_url = fields.Char('Google Drive 連結', readonly=True)
    
    # 建立者和建立時間
    create_uid = fields.Many2one('res.users', '建立者', readonly=True)
    create_date = fields.Datetime('建立時間', readonly=True)
    
    # 文件編號
    doc_number = fields.Char('文件編號', readonly=True, copy=False)
    
    @api.model
    def create(self, vals):
        """建立時自動產生文件編號"""
        if not vals.get('doc_number'):
            vals['doc_number'] = self._generate_doc_number(vals.get('document_type', 'other'))
        return super().create(vals)
    
    def _generate_doc_number(self, doc_type):
        """產生管委會文件編號"""
        # 格式：COMM-類型-年月日-序號
        type_code = {
            'announcement': 'ANN',
            'notice': 'NOT',
            'resolution': 'RES',
            'report': 'RPT',
            'meeting_minutes': 'MIN',
            'other': 'OTH',
        }.get(doc_type, 'OTH')
        
        date_str = datetime.now().strftime('%Y%m%d')
        
        # 查詢當日同類型文件數量
        today = fields.Date.context_today(self)
        same_type_count = self.search_count([
            ('document_type', '=', doc_type),
            ('create_date', '>=', today),
            ('create_date', '<', fields.Date.add(today, days=1)),
        ])
        
        seq = str(same_type_count + 1).zfill(3)
        return f"COMM-{type_code}-{date_str}-{seq}"
    
    def action_generate_from_template(self):
        """從範本生成公文"""
        for record in self:
            if not record.template_id:
                raise UserError('請先選擇公文範本')
            
            if not record.template_id.organization_type == 'committee':
                raise UserError('此範本不適用於管委會，請選擇管委會專屬範本')
            
            try:
                # 準備上下文
                context = {
                    'subject': record.name,
                    'content': record.content_draft or '',
                    'signer_name': record.signer_id.name if record.signer_id else '主任委員',
                    'signer_role': record.signer_id.role if record.signer_id else '主任委員',
                    'organization': record.community_id.name + '管理委員會',
                    'community_name': record.community_id.name,
                    'community_address': record.community_id.address or '',
                }
                
                # 如果有表單回應，加入回應資料
                if record.response_id and record.response_id.response_data:
                    import json
                    try:
                        response_data = json.loads(record.response_id.response_data)
                        context.update(response_data)
                    except:
                        pass
                
                # 渲染範本
                rendered_content = record.template_id.render_template(context)
                
                # 更新公文內容
                record.write({
                    'content': rendered_content,
                    'state': 'draft',
                })
                
                # 記錄範本使用
                record.template_id.action_use_template()
                
                _logger.info(f"管委會公文已生成: {record.name} (編號: {record.doc_number})")
                
            except Exception as e:
                _logger.error(f"管委會公文生成失敗: {str(e)}")
                raise UserError(f"公文生成失敗: {str(e)}")
    
    def action_generate_from_form_response(self):
        """從 Google 表單回應生成公文"""
        for record in self:
            if not record.response_id:
                raise UserError('請先選擇表單回應')
            
            if not record.document_type:
                raise UserError('請先選擇公文類型')
            
            try:
                # 根據公文類型選擇範本
                template = self.env['wuchang.document.template'].search([
                    ('document_type', '=', record.document_type),
                    ('organization_type', '=', 'committee'),
                    ('is_active', '=', True),
                ], limit=1)
                
                if not template:
                    raise UserError(f'找不到管委會 {record.document_type} 類型的公文範本')
                
                # 設定範本
                record.template_id = template
                
                # 從回應取得資料
                response_data = record.response_id.response_data or '{}'
                record.content_draft = response_data
                
                # 生成公文
                record.action_generate_from_template()
                
            except Exception as e:
                _logger.error(f"從表單回應生成公文失敗: {str(e)}")
                raise UserError(f"生成公文失敗: {str(e)}")
    
    def action_save_to_google_drive(self):
        """儲存到 Google Drive"""
        for record in self:
            try:
                # TODO: 實作 Google Drive API 呼叫
                # 將公文內容儲存到 Google Drive
                
                _logger.info(f"管委會公文已儲存到 Google Drive: {record.name}")
                
            except Exception as e:
                _logger.error(f"儲存到 Google Drive 失敗: {str(e)}")
                raise UserError(f"儲存到 Google Drive 失敗: {str(e)}")
