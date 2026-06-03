from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ordering_enabled = fields.Boolean(string='啟用線上點餐')
    announcement = fields.Char(string='公告')
    allow_delivery = fields.Boolean(string='允許外送')
    min_amount = fields.Float(string='最低消費')

    kb_enabled = fields.Boolean(string='啟用史料館')
    kb_plaque_text = fields.Char(string='史料館匾額文字')

    webauthn_enabled = fields.Boolean(string='啟用WebAuthn登入')
    webauthn_rp_id = fields.Char(string='WebAuthn RP ID')
    webauthn_rp_name = fields.Char(string='WebAuthn RP 名稱')

    security_require_2fa = fields.Boolean(string='後台強制2FA')

    smtp_name = fields.Char(string='郵件伺服器名稱')
    smtp_host = fields.Char(string='SMTP 主機')
    smtp_port = fields.Integer(string='SMTP 連接埠', default=587)
    smtp_encryption = fields.Selection(
        [('none', '無'), ('starttls', 'STARTTLS'), ('ssl', 'SSL/TLS')], string='加密方式', default='starttls')
    smtp_user = fields.Char(string='SMTP 使用者')
    smtp_pass = fields.Char(string='SMTP 密碼')
    email_from = fields.Char(string='預設寄件地址')

    agent_enabled = fields.Boolean(string='啟用代理人（小j）')
    agent_name = fields.Char(string='代理人顯示名稱')
    agent_email = fields.Char(string='代理人電子郵件')

    ai_mode = fields.Selection([
        ('cloud_builtin', '雲端內建'),
        ('external_key', '外部金鑰'),
        ('local_ollama', '本地 Ollama'),
        ('master_logic', '主控邏輯')
    ], string='AI 模式', default='local_ollama')
    gen_model = fields.Char(string='雲端模型')
    ollama_model = fields.Char(string='Ollama 模型')
    google_api_key = fields.Char(string='Google API Key')
    body_enabled = fields.Boolean(string='啟用身體')
    body_name = fields.Char(string='身體名稱')
    body_location = fields.Char(string='身體位置')
    voice_enabled = fields.Boolean(string='啟用語音')
    asr_host = fields.Char(string='ASR 主機')
    tts_host = fields.Char(string='TTS 主機')
    llm_host = fields.Char(string='LLM 主機')

    ws_privacy_enabled = fields.Boolean(string='啟用工作站隱私')
    ws_privacy_anonymize_logs = fields.Boolean(string='匿名化工作站日誌')
    ws_privacy_retention_days = fields.Integer(string='瀏覽資料保留天數', default=7)
    ws_privacy_disable_analytics = fields.Boolean(string='停用工作站分析追蹤')

    # 組織身份與資金來源聲明
    branding_organization_info = fields.Text(string='組織身份', help='組織法律名稱與立案資訊')
    branding_funding_source = fields.Text(string='資金來源', help='資金來源與合作夥伴信息')
    branding_coffee_org_link = fields.Char(
        string='咖啡館Google商家資訊', help='Google Maps 或官方網站連結')
    branding_decision_maker = fields.Char(
        string='核心決策人', help='決策人及其身份證號、出生日期')
    branding_nonprofit_declaration = fields.Text(
        string='無資本利得宣告', help='無資本利得宣告文本')

    def get_values(self):
        res = super().get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(
            ordering_enabled=(params.get_param(
                'wuchang.ordering_enabled') == 'True'),
            announcement=params.get_param('wuchang.announcement') or '',
            allow_delivery=(params.get_param(
                'wuchang.allow_delivery') == 'True'),
            min_amount=float(params.get_param('wuchang.min_amount') or 0),
            kb_enabled=(params.get_param('wuchang.kb.enabled') == 'True'),
            kb_plaque_text=params.get_param('wuchang.kb.plaque') or '五常史料馆',
            webauthn_enabled=(params.get_param(
                'wuchang.webauthn.enabled') == 'True'),
            webauthn_rp_id=params.get_param('wuchang.webauthn.rp_id') or '',
            webauthn_rp_name=params.get_param(
                'wuchang.webauthn.rp_name') or '',
            security_require_2fa=(params.get_param(
                'security.require_2fa') or '').lower() in ('1', 'true', 'yes'),
        )
        res.update(
            agent_enabled=(params.get_param('wuchang.agent.enabled')
                           or '').lower() in ('1', 'true', 'yes'),
            agent_name=params.get_param('wuchang.agent.name') or '小j',
            agent_email=params.get_param('wuchang.agent.email') or (
                params.get_param('web.company_email') or 'admin@wuchang.life'),
        )
        res.update(
            ai_mode=params.get_param('wuchang.ai_mode') or 'local_ollama',
            gen_model=params.get_param('wuchang.gen_model') or '',
            ollama_model=params.get_param('wuchang.ollama_model') or '',
            google_api_key=params.get_param('wuchang.google_api_key') or '',
            body_enabled=(params.get_param('wuchang.body.enabled')
                          or '').lower() in ('1', 'true', 'yes'),
            body_name=params.get_param('wuchang.body.name') or '洛地',
            body_location=params.get_param('wuchang.body.location') or '',
            voice_enabled=(params.get_param('wuchang.voice.enabled')
                           or '').lower() in ('1', 'true', 'yes'),
            asr_host=params.get_param(
                'wuchang.asr.host') or 'asr.wuchang.life',
            tts_host=params.get_param(
                'wuchang.tts.host') or 'tts.wuchang.life',
            llm_host=params.get_param(
                'wuchang.llm.host') or 'llm.wuchang.life',
        )
        res.update(
            ws_privacy_enabled=(params.get_param(
                'wuchang.ws_privacy.enabled') or '').lower() in ('1', 'true', 'yes'),
            ws_privacy_anonymize_logs=(params.get_param(
                'wuchang.ws_privacy.anonymize_logs') or '').lower() in ('1', 'true', 'yes'),
            ws_privacy_retention_days=int(params.get_param(
                'wuchang.ws_privacy.retention_days') or '7'),
            ws_privacy_disable_analytics=(params.get_param(
                'wuchang.ws_privacy.disable_analytics') or '').lower() in ('1', 'true', 'yes'),
            branding_organization_info=params.get_param(
                'branding.organization_info') or '新北市五常社區發展協會（立案字號：新北市社區補自第1100606355號）',
            branding_funding_source=params.get_param(
                'branding.funding_source') or '系統開發：上品聊國咖啡館全額捐助',
            branding_coffee_org_link=params.get_param(
                'branding.coffee_org_link') or 'https://www.google.com/maps/search/上品聊國咖啡館',
            branding_decision_maker=params.get_param(
                'branding.decision_maker') or '江政隆（F124771717，1979-12-25）',
            branding_nonprofit_declaration=params.get_param(
                'branding.nonprofit_declaration') or '',
        )
        try:
            server = self.env['ir.mail_server'].sudo().search([], limit=1)
            if server:
                res.update(
                    smtp_name=server.name or '',
                    smtp_host=server.smtp_host or '',
                    smtp_port=server.smtp_port or 0,
                    smtp_encryption=server.smtp_encryption or 'starttls',
                    smtp_user=server.smtp_user or '',
                    smtp_pass='',
                    email_from=server.from_filter or '',
                )
        except Exception:
            pass
        return res

    def set_values(self):
        super().set_values()
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('wuchang.ordering_enabled',
                         'True' if self.ordering_enabled else 'False')
        params.set_param('wuchang.announcement', self.announcement or '')
        params.set_param('wuchang.allow_delivery',
                         'True' if self.allow_delivery else 'False')
        params.set_param('wuchang.min_amount', str(self.min_amount or 0))
        params.set_param('wuchang.kb.enabled',
                         'True' if self.kb_enabled else 'False')
        params.set_param('wuchang.kb.plaque', self.kb_plaque_text or '五常史料馆')
        params.set_param('wuchang.webauthn.enabled',
                         'True' if self.webauthn_enabled else 'False')
        params.set_param('wuchang.webauthn.rp_id', self.webauthn_rp_id or '')
        params.set_param('wuchang.webauthn.rp_name',
                         self.webauthn_rp_name or '')
        params.set_param('security.require_2fa',
                         'True' if self.security_require_2fa else 'False')
        params.set_param('wuchang.agent.enabled',
                         'True' if self.agent_enabled else 'False')
        params.set_param('wuchang.agent.name', self.agent_name or '小j')
        params.set_param('wuchang.agent.email', self.agent_email or '')
        params.set_param('wuchang.ai_mode', self.ai_mode or 'local_ollama')
        params.set_param('wuchang.gen_model', self.gen_model or '')
        params.set_param('wuchang.ollama_model', self.ollama_model or '')
        if self.google_api_key:
            params.set_param('wuchang.google_api_key', self.google_api_key)
        params.set_param('wuchang.body.enabled',
                         'True' if self.body_enabled else 'False')
        params.set_param('wuchang.body.name', self.body_name or '洛地')
        params.set_param('wuchang.body.location', self.body_location or '')
        params.set_param('wuchang.voice.enabled',
                         'True' if self.voice_enabled else 'False')
        params.set_param('wuchang.asr.host',
                         self.asr_host or 'asr.wuchang.life')
        params.set_param('wuchang.tts.host',
                         self.tts_host or 'tts.wuchang.life')
        params.set_param('wuchang.llm.host',
                         self.llm_host or 'llm.wuchang.life')
        params.set_param('wuchang.ws_privacy.enabled',
                         'True' if self.ws_privacy_enabled else 'False')
        params.set_param('wuchang.ws_privacy.anonymize_logs',
                         'True' if self.ws_privacy_anonymize_logs else 'False')
        params.set_param('wuchang.ws_privacy.retention_days', str(
            int(self.ws_privacy_retention_days or 0) or 7))
        params.set_param('wuchang.ws_privacy.disable_analytics',
                         'True' if self.ws_privacy_disable_analytics else 'False')

        # 儲存組織身份與資金來源聲明
        params.set_param('branding.organization_info',
                         self.branding_organization_info or '')
        params.set_param('branding.funding_source',
                         self.branding_funding_source or '')
        params.set_param('branding.coffee_org_link',
                         self.branding_coffee_org_link or 'https://www.google.com/maps/search/上品聊國咖啡館')
        params.set_param('branding.decision_maker',
                         self.branding_decision_maker or '')
        params.set_param('branding.nonprofit_declaration',
                         self.branding_nonprofit_declaration or '')

        try:
            if self.agent_enabled and self.agent_email:
                Partner = self.env['res.partner'].sudo()
                p = Partner.search([('email', '=', self.agent_email)], limit=1)
                vals = {'name': self.agent_name or '小j',
                        'email': self.agent_email}
                if p:
                    p.write(vals)
                else:
                    Partner.create(vals)
        except Exception:
            pass
        try:
            vals = {
                'name': self.smtp_name or 'Mail Server',
                'smtp_host': self.smtp_host or '',
                'smtp_port': int(self.smtp_port or 0) or 587,
                'smtp_encryption': self.smtp_encryption or 'starttls',
                'smtp_user': self.smtp_user or '',
                'from_filter': self.email_from or '',
                'smtp_debug': False,
            }
            if self.smtp_pass:
                vals['smtp_pass'] = self.smtp_pass
            MailServer = self.env['ir.mail_server'].sudo()
            existing = None
            if self.smtp_host:
                existing = MailServer.search(
                    [('smtp_host', '=', self.smtp_host)], limit=1)
            if existing:
                existing.write(vals)
            else:
                MailServer.create(vals)
        except Exception:
            pass
