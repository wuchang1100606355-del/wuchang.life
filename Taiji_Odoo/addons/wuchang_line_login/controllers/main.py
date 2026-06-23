import json
import secrets
import requests
from urllib.parse import urlencode

from odoo import http
from odoo.http import request


class WuchangLineLogin(http.Controller):

    @http.route('/line/login', type='http', auth='public', website=False, csrf=False)
    def line_login(self, **kw):
        channel_id = request.env['ir.config_parameter'].sudo().get_param('wuchang_line_login.channel_id')
        redirect_uri = request.env['ir.config_parameter'].sudo().get_param('wuchang_line_login.redirect_uri')

        if not channel_id or not redirect_uri:
            return "LINE config missing: channel_id or redirect_uri"

        state = secrets.token_urlsafe(24)
        request.session['wuchang_line_state'] = state
        group_packet_ref = kw.get('group_packet_ref')
        if group_packet_ref:
            request.session['wuchang_group_packet_ref'] = group_packet_ref

        params = {
            'response_type': 'code',
            'client_id': channel_id,
            'redirect_uri': redirect_uri,
            'state': state,
            'scope': 'profile openid',
        }

        return request.redirect('https://access.line.me/oauth2/v2.1/authorize?' + urlencode(params))

    @http.route('/line/callback', type='http', auth='public', website=False, csrf=False)
    def line_callback(self, **kw):
        code = kw.get('code')
        state = kw.get('state')
        saved_state = request.session.get('wuchang_line_state')

        if not code:
            return "LINE callback missing code"

        if not state or state != saved_state:
            return "LINE state mismatch"

        channel_id = request.env['ir.config_parameter'].sudo().get_param('wuchang_line_login.channel_id')
        channel_secret = request.env['ir.config_parameter'].sudo().get_param('wuchang_line_login.channel_secret')
        redirect_uri = request.env['ir.config_parameter'].sudo().get_param('wuchang_line_login.redirect_uri')

        token_res = requests.post(
            'https://api.line.me/oauth2/v2.1/token',
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': redirect_uri,
                'client_id': channel_id,
                'client_secret': channel_secret,
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=20,
        )

        if token_res.status_code != 200:
            return "LINE token failed: %s" % token_res.text

        access_token = token_res.json().get('access_token')

        profile_res = requests.get(
            'https://api.line.me/v2/profile',
            headers={'Authorization': 'Bearer %s' % access_token},
            timeout=20,
        )

        if profile_res.status_code != 200:
            return "LINE profile failed: %s" % profile_res.text

        profile = profile_res.json()
        line_user_id = profile.get('userId')

        user_model = request.env['wuchang.line.user'].sudo()
        user = user_model.search([('line_user_id', '=', line_user_id)], limit=1)

        vals = {
            'display_name': profile.get('displayName'),
            'line_user_id': line_user_id,
            'picture_url': profile.get('pictureUrl'),
            'status_message': profile.get('statusMessage'),
            'raw_profile': json.dumps(profile, ensure_ascii=False),
        }

        if user:
            user.write(vals)
        else:
            user = user_model.create(vals)

        group_packet_ref = request.session.get('wuchang_group_packet_ref')
        if group_packet_ref:
            subject_hash = request.env['wuchang.member.external.auth'].sudo().hash_subject('line', line_user_id)
            request.session['wuchang_group_auth_ref'] = {
                'provider': 'line',
                'provider_user_ref': subject_hash,
                'display_ref': 'line_member_masked',
            }
            return request.redirect('/wuchang/member/register/group/%s' % group_packet_ref)

        return "LINE LOGIN OK: %s" % (user.display_name or user.line_user_id)
