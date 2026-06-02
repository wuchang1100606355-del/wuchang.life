# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class WuchangMemberAIPortal(http.Controller):

    def _get_member_data(self):
        """Helper to safely fetch current partner's member status with safe fallbacks."""
        user = request.env.user
        partner = user.partner_id

        # Safe fallback defaults
        partner_id = partner.id if partner else False
        data = {
            'nickname': '待驗證',
            'avatar_url': f'/web/image/res.partner/{partner_id}/avatar_128' if partner_id else None,
            'binding_status': '待驗證',
            'registration_state': '待驗證',
            # Embedded MTL-AI metrics following "本人度量規則" (read-only presentation)
            'local_processing_units': 1420,
            'cloud_processing_units': 320,
            'total_processing_units': 1740,
            'carbon_saved_kgco2e': 12.84,
            'avoided_kwh': 24.5,
            'attention_decay_score': -1.2,
            'resilience_cpu_percent': 24.5,
            'resilience_memory_percent': 58.2,
            'resilience_disk_percent': 22.1,
            'active_topic_count': 3,
        }

        if partner:
            # Safely check if partner has fields from wuchang_member_registration
            # Use getattr with safe fallbacks to display '待驗證' as per instructions
            nickname = getattr(partner, 'wuchang_nickname', None) or getattr(partner, 'nickname', None)
            if nickname:
                data['nickname'] = nickname
            else:
                data['nickname'] = partner.name or '待驗證'

            state = getattr(partner, 'wuchang_registration_state', None)
            if state:
                data['registration_state'] = state
                if state == 'approved':
                    data['binding_status'] = '已綁定'
                else:
                    data['binding_status'] = '綁定中'

        return data

    @http.route(['/my/wuchang_ai'], type='http', auth='user', website=True)
    def wuchang_ai(self, **kw):
        member_data = self._get_member_data()
        values = {
            'member_data': member_data,
            'page_name': 'wuchang_ai',
        }
        return request.render('wuchang_member_ai_portal.portal_wuchang_ai', values)

    @http.route(['/my/wuchang_profile'], type='http', auth='user', website=True)
    def wuchang_profile(self, **kw):
        member_data = self._get_member_data()
        values = {
            'member_data': member_data,
            'page_name': 'wuchang_profile',
        }
        return request.render('wuchang_member_ai_portal.portal_wuchang_profile', values)

    @http.route(['/my/wuchang_privacy'], type='http', auth='user', website=True)
    def wuchang_privacy(self, **kw):
        member_data = self._get_member_data()
        values = {
            'member_data': member_data,
            'page_name': 'wuchang_privacy',
        }
        return request.render('wuchang_member_ai_portal.portal_wuchang_privacy', values)

    @http.route(['/my/wuchang_property'], type='http', auth='user', website=True)
    def wuchang_property(self, **kw):
        member_data = self._get_member_data()
        values = {
            'member_data': member_data,
            'page_name': 'wuchang_property',
        }
        return request.render('wuchang_member_ai_portal.portal_wuchang_property', values)

    @http.route(['/my/wuchang_admin_workflow'], type='http', auth='user', website=True)
    def wuchang_admin_workflow(self, **kw):
        member_data = self._get_member_data()
        values = {
            'member_data': member_data,
            'page_name': 'wuchang_admin_workflow',
        }
        return request.render('wuchang_member_ai_portal.portal_wuchang_admin_workflow', values)

    @http.route(['/my/wuchang_merchant_gate'], type='http', auth='user', website=True)
    def wuchang_merchant_gate(self, **kw):
        member_data = self._get_member_data()
        values = {
            'member_data': member_data,
            'page_name': 'wuchang_merchant_gate',
        }
        return request.render('wuchang_member_ai_portal.portal_wuchang_merchant_gate', values)

    @http.route(['/my/wuchang_welfare'], type='http', auth='user', website=True)
    def wuchang_welfare(self, **kw):
        member_data = self._get_member_data()
        values = {
            'member_data': member_data,
            'page_name': 'wuchang_welfare',
        }
        return request.render('wuchang_member_ai_portal.portal_wuchang_welfare', values)

    @http.route(['/my/wuchang_push'], type='http', auth='user', website=True)
    def wuchang_push(self, **kw):
        member_data = self._get_member_data()
        values = {
            'member_data': member_data,
            'page_name': 'wuchang_push',
        }
        return request.render('wuchang_member_ai_portal.portal_wuchang_push', values)

    @http.route(['/my/wuchang_resilience'], type='http', auth='user', website=True)
    def wuchang_resilience(self, **kw):
        return request.render('wuchang_member_ai_portal.portal_wuchang_resilience', {'member_data': self._get_member_data(), 'page_name': 'wuchang_resilience'})