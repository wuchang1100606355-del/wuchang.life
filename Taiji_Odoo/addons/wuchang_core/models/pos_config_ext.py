# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import AccessError, ValidationError
import json


class PosConfig(models.Model):
    _inherit = 'pos.config'

    opening_time = fields.Char(
        string='Opening Time', help='HH:MM 24h, e.g., 06:00')
    closing_time = fields.Char(
        string='Closing Time', help='HH:MM 24h, e.g., 14:00')
    overnight = fields.Boolean(
        string='Overnight Hours', help='If closing time is on the next day')

    # --- 營運模式設定 ---
    wuchang_store_mode = fields.Selection([
        ('donor', '總店模式 (Donor Mode)：月結全捐，不即時入帳'),
        ('fund', '仁義店模式 (Community Coin Fund)：本質即五常社區發展基金(社區幣帳戶)，需嚴格控管')
    ], string='五常營運模式', default='donor')

    wuchang_delivery_fund_partner = fields.Boolean(
        string='外送依基金規則結算 (合作商家)', default=False)

    # --- 數位看板 (TV) 設定 ---
    signage_screen_id = fields.Many2one(
        'wuchang.digital.signage', string='綁定廣告電視牆')
    signage_url = fields.Char(string='電視牆播放網址', compute='_compute_signage_url')

    # --- 客顯螢幕 (Customer Display) ---
    enable_little_j_interaction = fields.Boolean(
        string='啟用小J 互動 (客顯)', default=True)
    customer_display_msg = fields.Char(
        string='待機迎賓語', default='歡迎光臨五常社區！您的消費就是做公益。')

    @api.depends('signage_screen_id')
    def _compute_signage_url(self):
        for config in self:
            if config.signage_screen_id:
                base_url = self.env['ir.config_parameter'].sudo(
                ).get_param('web.base.url')
                config.signage_url = f"{base_url}/wuchang/signage/{config.signage_screen_id.id}"
            else:
                config.signage_url = False

    def write(self, vals):
        if 'wuchang_store_mode' in vals and vals['wuchang_store_mode'] == 'fund':
            for config in self:
                if '仁義' not in config.name:
                    raise ValidationError('嚴格控管：只有「聊國咖啡仁義分店」即為基金池本身，才可啟用此模式。')

        if any(k in vals for k in ['wuchang_store_mode']):
            p = self.env['ir.config_parameter'].sudo()
            raw = p.get_param('founder.identity.google_accounts') or '[]'
            try:
                founders = json.loads(raw)
            except Exception:
                founders = []
            d_raw = p.get_param('founder.delegates') or '[]'
            try:
                delegates = json.loads(d_raw)
            except Exception:
                delegates = []
            user = self.env.user
            ok = (user.login in founders) or (user.login == 'o970106@gmail.com') or (user.login in delegates)
            if not ok:
                raise AccessError('forbidden_finance_config')
        return super(PosConfig, self).write(vals)


class WuchangDigitalSignage(models.Model):
    """
    【Mod 48】五常影音聯播網管理
    管理電視牆的播放清單、跑馬燈
    """
    _name = 'wuchang.digital.signage'
    _description = '數位看板播放清單'

    name = fields.Char(string='看板名稱 (e.g., 仁義店大電視)', required=True)

    # --- 內容控制 ---
    marquee_text = fields.Char(string='即時跑馬燈文字', default='今日拿鐵買一送一！五常專勤隊募集中！')
    is_live_interrupt = fields.Boolean(
        string='插播緊急廣播', default=False, help="若勾選，電視將暫停播放清單，強制顯示跑馬燈或緊急畫面")

    playlist_ids = fields.One2many(
        'wuchang.signage.content', 'signage_id', string='播放內容')

    def write(self, vals):
        p = self.env['ir.config_parameter'].sudo()
        raw = p.get_param('founder.identity.google_accounts') or '[]'
        try:
            founders = json.loads(raw)
        except Exception:
            founders = []
        d_raw = p.get_param('founder.delegates') or '[]'
        try:
            delegates = json.loads(d_raw)
        except Exception:
            delegates = []
        user = self.env.user
        ok = (user.login in founders) or (user.login == 'o970106@gmail.com') or (user.login in delegates)
        if not ok:
            raise AccessError('forbidden_design_config')
        return super(WuchangDigitalSignage, self).write(vals)

    def create(self, vals_list):
        p = self.env['ir.config_parameter'].sudo()
        raw = p.get_param('founder.identity.google_accounts') or '[]'
        try:
            founders = json.loads(raw)
        except Exception:
            founders = []
        d_raw = p.get_param('founder.delegates') or '[]'
        try:
            delegates = json.loads(d_raw)
        except Exception:
            delegates = []
        user = self.env.user
        ok = (user.login in founders) or (user.login == 'o970106@gmail.com') or (user.login in delegates)
        if not ok:
            raise AccessError('forbidden_design_config')
        return super(WuchangDigitalSignage, self).create(vals_list)

    def unlink(self):
        p = self.env['ir.config_parameter'].sudo()
        raw = p.get_param('founder.identity.google_accounts') or '[]'
        try:
            founders = json.loads(raw)
        except Exception:
            founders = []
        d_raw = p.get_param('founder.delegates') or '[]'
        try:
            delegates = json.loads(d_raw)
        except Exception:
            delegates = []
        user = self.env.user
        ok = (user.login in founders) or (user.login == 'o970106@gmail.com') or (user.login in delegates)
        if not ok:
            raise AccessError('forbidden_design_config')
        return super(WuchangDigitalSignage, self).unlink()


class WuchangSignageContent(models.Model):
    _name = 'wuchang.signage.content'
    _description = '看板內容項目'
    _order = 'sequence'

    sequence = fields.Integer(string='排序', default=10)
    signage_id = fields.Many2one('wuchang.digital.signage', string='所屬看板')

    content_type = fields.Selection([
        ('image', '圖片'),
        ('video', '影片 (URL)'),
        ('dashboard', '戰情室 (Iframe)')
    ], default='image')

    url = fields.Char(string='資源網址 (URL)', help="圖片連結、YouTube 連結或戰情室網址")
    duration = fields.Integer(string='播放秒數', default=10)

    def write(self, vals):
        p = self.env['ir.config_parameter'].sudo()
        raw = p.get_param('founder.identity.google_accounts') or '[]'
        try:
            founders = json.loads(raw)
        except Exception:
            founders = []
        d_raw = p.get_param('founder.delegates') or '[]'
        try:
            delegates = json.loads(d_raw)
        except Exception:
            delegates = []
        user = self.env.user
        ok = (user.login in founders) or (user.login == 'o970106@gmail.com') or (user.login in delegates)
        if not ok:
            raise AccessError('forbidden_design_config')
        return super(WuchangSignageContent, self).write(vals)

    def create(self, vals_list):
        p = self.env['ir.config_parameter'].sudo()
        raw = p.get_param('founder.identity.google_accounts') or '[]'
        try:
            founders = json.loads(raw)
        except Exception:
            founders = []
        d_raw = p.get_param('founder.delegates') or '[]'
        try:
            delegates = json.loads(d_raw)
        except Exception:
            delegates = []
        user = self.env.user
        ok = (user.login in founders) or (user.login == 'o970106@gmail.com') or (user.login in delegates)
        if not ok:
            raise AccessError('forbidden_design_config')
        return super(WuchangSignageContent, self).create(vals_list)

    def unlink(self):
        p = self.env['ir.config_parameter'].sudo()
        raw = p.get_param('founder.identity.google_accounts') or '[]'
        try:
            founders = json.loads(raw)
        except Exception:
            founders = []
        d_raw = p.get_param('founder.delegates') or '[]'
        try:
            delegates = json.loads(d_raw)
        except Exception:
            delegates = []
        user = self.env.user
        ok = (user.login in founders) or (user.login == 'o970106@gmail.com') or (user.login in delegates)
        if not ok:
            raise AccessError('forbidden_design_config')
        return super(WuchangSignageContent, self).unlink()


class WuchangPosOrder(models.Model):
    """
    訂單邏輯擴充：處理基金注入
    """
    _inherit = 'pos.order'

    wuchang_sale_mode = fields.Selection([
        ('dine_in', '內用'),
        ('takeout', '外帶'),
        ('delivery', '外送'),
    ], string='銷售模式', default='dine_in')

    social_impact_score = fields.Float(string='社會貢獻值', default=0.0)
    social_impact_note = fields.Char(string='社會貢獻說明')

    def _process_saved_orders(self, draft, orders, user_id):
        """
        覆寫訂單處理邏輯，攔截並注入基金 (如果是仁義店模式)
        """
        res = super(WuchangPosOrder, self)._process_saved_orders(
            draft, orders, user_id)

        for order_id in res:
            order = self.browse(order_id)
            sale_mode = order.wuchang_sale_mode or 'dine_in'
            if sale_mode != 'delivery':
                continue
            cfg = order.config_id
            if cfg.wuchang_store_mode == 'fund' or cfg.wuchang_delivery_fund_partner:
                self._inject_to_fund(order)
        return res

    def _inject_to_fund(self, order):
        fund = self.env['community.fund.account'].search(
            [('account_type', '=', 'general')], limit=1)
        if not fund:
            return

        amount_total = float(order.amount_total or 0.0)
        if amount_total <= 0:
            return

        donation_total = amount_total * (30.0 / 110.0)
        merchant_donation = donation_total * (2.0 / 3.0)
        consumer_donation = donation_total - merchant_donation
        merchant_custody = amount_total - donation_total

        order.write({
            'social_impact_score': donation_total,
            'social_impact_note': '消費者捐款%.2f, 商家捐款%.2f, 商家代收%.2f' % (
                consumer_donation,
                merchant_donation,
                merchant_custody,
            ),
        })

        fund.inject_pos_breakdown(
            consumer_donation,
            merchant_donation,
            merchant_custody,
            'POS Order %s' % (order.name or ''),
        )

        self.env['wuchang.coin.transaction'].create({
            'source_partner_id': order.partner_id.id if order.partner_id else False,
            'dest_partner_id': order.company_id.partner_id.id,
            'amount': donation_total * 0.5,
            'transaction_type': 'mint',
        })


