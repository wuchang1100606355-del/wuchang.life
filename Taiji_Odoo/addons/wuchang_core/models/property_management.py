# -*- coding: utf-8 -*-
from odoo import models, fields, api

class PropertyCommunity(models.Model):
    _name = 'wuchang.property.community'
    _description = '公寓大廈/社區'

    name = fields.Char('社區名稱', required=True)
    address = fields.Char('社區地址')
    committee_partner_id = fields.Many2one('res.partner', string='管委會(團體客戶)', domain="[('property_management_role', '=', 'committee')]")
    total_households = fields.Integer('總戶數')
    building_ids = fields.One2many('wuchang.property.building', 'community_id', string='棟別')
    committee_member_ids = fields.One2many('wuchang.property.committee.member', 'community_id', string='管委會成員')

class PropertyBuilding(models.Model):
    _name = 'wuchang.property.building'
    _description = '棟別/樓層'

    name = fields.Char('棟別名稱', required=True)
    community_id = fields.Many2one('wuchang.property.community', string='所屬社區', required=True)
    unit_ids = fields.One2many('wuchang.property.unit', 'building_id', string='戶號')

class PropertyUnit(models.Model):
    _name = 'wuchang.property.unit'
    _description = '區分所有權專有部分 (戶號)'

    name = fields.Char('戶號', required=True)
    building_id = fields.Many2one('wuchang.property.building', string='所屬棟別', required=True)
    community_id = fields.Many2one('wuchang.property.community', related='building_id.community_id', string='所屬社區', store=True)
    floor = fields.Integer('樓層')
    area = fields.Float('坪數')
    owner_id = fields.Many2one('res.partner', string='區分所有權人')
    resident_count = fields.Integer('居住人數')
    management_fee_base = fields.Float('管理費計算基準(元/坪)')

    def calculate_fee(self):
        for rec in self:
            return rec.area * rec.management_fee_base

class PropertyCommitteeMember(models.Model):
    _name = 'wuchang.property.committee.member'
    _description = '管委會成員'

    name = fields.Char('姓名', required=True)
    community_id = fields.Many2one('wuchang.property.community', string='所屬社區', required=True)
    role = fields.Selection([
        ('chair', '主任委員'),
        ('vice_chair', '副主任委員'),
        ('finance', '財務委員'),
        ('monitor', '監察委員'),
        ('equipment', '機電委員'),
        ('general', '一般委員')
    ], string='職務', required=True)
    term_start = fields.Date('任期開始')
    term_end = fields.Date('任期結束')
    phone = fields.Char('聯絡電話')

class PropertyComplaint(models.Model):
    _name = 'wuchang.property.complaint'
    _description = '住戶反映/報修'

    name = fields.Char('主旨', required=True)
    community_id = fields.Many2one('wuchang.property.community', string='社區')
    unit_id = fields.Many2one('wuchang.property.unit', string='戶號')
    type = fields.Selection([
        ('repair', '公共設施報修'),
        ('noise', '噪音反映'),
        ('suggestion', '一般建議'),
        ('other', '其他')
    ], string='類型', default='repair')
    description = fields.Text('詳細內容')
    state = fields.Selection([
        ('draft', '草稿'),
        ('reported', '已通報'),
        ('processing', '處理中'),
        ('done', '已完成')
    ], string='狀態', default='draft')
    
    response = fields.Text('管委會/物業回覆')

class PropertyFinancialReport(models.Model):
    _name = 'wuchang.property.financial.report'
    _description = '財務報表'

    name = fields.Char('報表名稱', required=True) # e.g. 2026年1月財務報表
    community_id = fields.Many2one('wuchang.property.community', string='社區')
    date = fields.Date('報表日期')
    file = fields.Binary('報表檔案')
    summary = fields.Text('財務摘要')

class CommunityBulletin(models.Model):
    _name = 'community.bulletin'
    _description = '社區公告'

    name = fields.Char('標題', required=True)
    content = fields.Text('內容')
    date_published = fields.Date('發佈日期', default=lambda self: fields.Date.context_today(self))
    active = fields.Boolean(default=True)


class CommunityPackage(models.Model):
    _name = 'community.package'
    _description = '社區包裹'

    name = fields.Char('包裹編號/摘要', required=True)
    resident_id = fields.Many2one('res.partner', string='住戶')
    status = fields.Selection([
        ('arrived', '已到貨'),
        ('picked_up', '已領取'),
    ], string='狀態', default='arrived', required=True)
    arrival_date = fields.Date('到貨日期', default=lambda self: fields.Date.context_today(self))
    pickup_date = fields.Date('領取日期')

    def action_confirm_pickup(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.write({'status': 'picked_up', 'pickup_date': today})
        return True

