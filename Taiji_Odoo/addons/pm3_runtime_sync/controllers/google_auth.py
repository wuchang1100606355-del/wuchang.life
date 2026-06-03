"""PM3 Google OAuth Integration."""

import logging
import os
import secrets
from urllib.parse import urlencode

import requests
from werkzeug.exceptions import BadRequest
from werkzeug.utils import redirect

from odoo import http, _, fields
from odoo.exceptions import AccessDenied
from odoo.http import request
from odoo.addons.web.controllers.home import ensure_db

_logger = logging.getLogger(__name__)


class PM3GoogleAuthController(http.Controller):
    @staticmethod
    def _safe_error_response(message, status=200):
        body = (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<title>Google Auth</title></head><body>"
            f"<p>{message}</p>"
            "<p><a href='/web/login?db=postgres'>返回登入頁</a></p>"
            "</body></html>"
        )
        return request.make_response(body, headers=[("Content-Type", "text/html; charset=utf-8")], status=status)

    @staticmethod
    def _truthy(value):
        return str(value or '').strip().lower() in {'1', 'true', 'yes', 'on'}

    def _superadmin_registration_config(self):
        params = request.env['ir.config_parameter'].sudo()
        enabled = self._truthy(
            params.get_param('xiaoj.superadmin.registration.enabled')
            or os.environ.get('XIAOJ_SUPERADMIN_REGISTRATION_ENABLED')
        )
        allowed_email = (
            params.get_param('xiaoj.superadmin.registration.allowed_email')
            or os.environ.get('XIAOJ_SUPERADMIN_ALLOWED_EMAIL')
            or 'admin@wuchang.life'
        ).strip().lower()
        allowed_domain = (
            params.get_param('xiaoj.superadmin.registration.allowed_domain')
            or os.environ.get('XIAOJ_SUPERADMIN_ALLOWED_DOMAIN')
            or 'wuchang.life'
        ).strip().lower()
        transfer_allowed = self._truthy(
            params.get_param('xiaoj.superadmin.registration.transfer_allowed')
            or os.environ.get('XIAOJ_SUPERADMIN_TRANSFER_ALLOWED')
        )
        return {
            'enabled': enabled,
            'allowed_email': allowed_email,
            'allowed_domain': allowed_domain,
            'transfer_allowed': transfer_allowed,
        }

    def _proxy_policy_context(self):
        params = request.env['ir.config_parameter'].sudo()
        admin_emails = {
            e.strip().lower()
            for e in (params.get_param('xiaoj.google.proxy.admin_emails', '') or '').split(',')
            if e.strip()
        }
        staff_domains = {
            d.strip().lower()
            for d in (params.get_param('xiaoj.google.proxy.staff_domains', '') or '').split(',')
            if d.strip()
        }
        default_scope = params.get_param(
            'xiaoj.google.proxy.default_scope',
            'drive.readonly,calendar.readonly'
        )
        return {
            'admin_emails': admin_emails,
            'staff_domains': staff_domains,
            'default_scope': default_scope,
        }

    def _assign_google_proxy_role(self, user, google_profile):
        policy = self._proxy_policy_context()
        email = (google_profile.get('email') or '').strip().lower()
        domain = email.split('@', 1)[1] if '@' in email else ''

        role = 'member'
        if email in policy['admin_emails']:
            role = 'admin_delegate'
        elif domain and domain in policy['staff_domains']:
            role = 'staff'

        user.sudo().write({
            'google_proxy_enabled': True,
            'google_proxy_role': role,
            'google_proxy_scope': policy['default_scope'],
            'google_proxy_last_auth': fields.Datetime.now(),
        })
        return role

    @staticmethod
    def _get_secret_value(config_param, env_key):
        secret_ref = request.env['ir.config_parameter'].sudo().get_param(config_param)
        if secret_ref:
            secret_value = request.httprequest.environ.get(secret_ref) or os.environ.get(secret_ref)
            if secret_value:
                return secret_value
        return os.environ.get(env_key)

    def _google_oauth_config(self):
        client_id = self._get_secret_value('google.oauth.client_id.ref', 'GOOGLE_OAUTH_CLIENT_ID')
        client_secret = self._get_secret_value('google.oauth.client_secret.ref', 'GOOGLE_OAUTH_CLIENT_SECRET')
        redirect_uri = request.env['ir.config_parameter'].sudo().get_param(
            'google.oauth.redirect_uri',
            'http://127.0.0.1:8069/auth/google/callback'
        )
        if not client_id or not client_secret:
            return None
        return {
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
        }

    def _google_service_account_status(self):
        credential_path = (
            request.env['ir.config_parameter'].sudo().get_param('xiaoj.google.service_account.path')
            or os.environ.get('XIAOJ_INTENT_FIELD_GOOGLE_CREDENTIALS')
            or os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        )
        if not credential_path:
            return {
                'enabled': False,
                'reason': 'credential_path_not_set',
                'token_acquired': False,
                'private_key_returned': False,
            }
        try:
            import hashlib
            import json
            from pathlib import Path

            from google.auth.transport.requests import Request
            from google.oauth2 import service_account

            path = Path(credential_path)
            info = json.loads(path.read_text(encoding='utf-8'))
            scopes = [
                s.strip()
                for s in (
                    request.env['ir.config_parameter'].sudo().get_param(
                        'xiaoj.google.service_account.scopes',
                        'https://www.googleapis.com/auth/cloud-platform.read-only',
                    )
                ).split(',')
                if s.strip()
            ]
            creds = service_account.Credentials.from_service_account_file(str(path), scopes=scopes)
            creds.refresh(Request())
            return {
                'enabled': True,
                'service_account_email': info.get('client_email', ''),
                'project_id': info.get('project_id', ''),
                'token_acquired': bool(creds.token),
                'token_expiry': str(creds.expiry) if creds.expiry else '',
                'private_key_present': bool(info.get('private_key')),
                'private_key_returned': False,
                'file_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'scope_count': len(scopes),
            }
        except Exception as exc:
            _logger.error("Google service account status check failed: %s", exc)
            return {
                'enabled': False,
                'reason': exc.__class__.__name__,
                'token_acquired': False,
                'private_key_returned': False,
            }

    @http.route('/auth/google/login', type='http', auth='none', sitemap=False, csrf=False)
    def google_login(self, **kw):
        ensure_db()
        cfg = self._google_oauth_config()
        if not cfg:
            return self._safe_error_response(_("Google OAuth 尚未設定完成，請聯絡管理員。"))

        oauth_state = secrets.token_urlsafe(24)
        request.session['google_oauth_state'] = oauth_state
        request.session['google_oauth_superadmin'] = bool(kw.get('superadmin'))
        request.session['google_oauth_superadmin_transfer'] = bool(kw.get('transfer'))
        auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
            "response_type": "code",
            "client_id": cfg["client_id"],
            "redirect_uri": cfg["redirect_uri"],
            "state": oauth_state,
            "scope": "openid email profile",
        })
        return redirect(auth_url)

    @http.route('/auth/superadmin/register', type='http', auth='none', sitemap=False, csrf=False)
    def superadmin_register(self, transfer=None, **kw):
        ensure_db()
        cfg = self._superadmin_registration_config()
        if not cfg['enabled']:
            return self._safe_error_response(_("超級管理員註冊通道尚未開啟。"))
        return self.google_login(superadmin=1, transfer=1 if transfer else None)

    @http.route('/auth/google/callback', type='http', auth='none', sitemap=False, csrf=False)
    def google_callback(self, code=None, state=None, error=None, **kw):
        ensure_db()
        cfg = self._google_oauth_config()
        if not cfg:
            return self._safe_error_response(_("Google OAuth 尚未設定完成，請聯絡管理員。"))

        if error:
            _logger.error(f"Google 授權失敗: {error}")
            return self._safe_error_response(_("Google 授權被拒絕，請重試。"))

        expected_state = request.session.get('google_oauth_state')
        request.session.pop('google_oauth_state', None)
        if not state or not expected_state or state != expected_state:
            return self._safe_error_response(_("Google 驗證狀態失效，請重新登入。"))
        if not code:
            raise BadRequest("缺少授權碼")

        token_url = "https://oauth2.googleapis.com/token"
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': cfg['redirect_uri'],
            'client_id': cfg['client_id'],
            'client_secret': cfg['client_secret']
        }

        try:
            token_res = requests.post(token_url, data=data, timeout=10)
            token_res.raise_for_status()
            token_info = token_res.json()
            access_token = token_info.get('access_token')

            profile_res = requests.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10
            )
            profile_res.raise_for_status()
            google_profile = profile_res.json()
            superadmin_mode = bool(request.session.get('google_oauth_superadmin'))
            transfer_mode = bool(request.session.get('google_oauth_superadmin_transfer'))
            request.session.pop('google_oauth_superadmin', None)
            request.session.pop('google_oauth_superadmin_transfer', None)

            if superadmin_mode:
                self._assert_superadmin_google_profile(google_profile, transfer_mode)

            user = request.env['res.users'].sudo().get_or_create_by_google_id(google_profile)
            if user:
                role = self._assign_google_proxy_role(user, google_profile)
                if superadmin_mode:
                    user = request.env['res.users'].sudo().activate_single_seat_superadmin(
                        user,
                        transfer=transfer_mode,
                        note='Google verified super-admin single-seat registration',
                    )
                    role = 'admin_delegate'
                request.session.uid = user.id
                request.session.login = user.login
                _logger.info("Google proxy delegated login success: uid=%s role=%s", user.id, role)
                return redirect('/my/home')
            return self._safe_error_response(_("無法建立五維碼身分代理，請聯絡管理員。"))
        except Exception as e:
            _logger.error(f"Google 登入例外: {str(e)}")
            return self._safe_error_response(_("系統連線異常，無法完成登入。"), status=500)

    def _assert_superadmin_google_profile(self, google_profile, transfer_mode=False):
        cfg = self._superadmin_registration_config()
        if not cfg['enabled']:
            raise AccessDenied("super-admin registration channel is disabled")

        email = (google_profile.get('email') or '').strip().lower()
        domain = email.split('@', 1)[1] if '@' in email else ''
        email_verified = google_profile.get('email_verified')
        if email_verified is False:
            raise AccessDenied("Google email is not verified")
        if email != cfg['allowed_email']:
            raise AccessDenied("super-admin registration email is not allowed")
        if domain != cfg['allowed_domain']:
            raise AccessDenied("super-admin registration domain is not allowed")
        if transfer_mode and not cfg['transfer_allowed']:
            raise AccessDenied("super-admin transfer is not enabled")

    @http.route('/api/pm3/google/proxy/check', type='json', auth='user', csrf=False)
    def google_proxy_check(self, action=None, risk_level='low', **kwargs):
        """
        小J Google 權限代理檢查 API（不執行實際 Google 操作）。
        """
        user = request.env.user
        allowed, decision, reason = user.sudo().evaluate_google_proxy_permission(action, risk_level)
        return {
            'allowed': allowed,
            'decision': decision,
            'reason': reason,
            'uid': user.id,
            'proxy_role': user.google_proxy_role,
            'proxy_enabled': user.google_proxy_enabled,
        }

    @http.route('/api/pm3/google/auth/status', type='json', auth='user', csrf=False)
    def google_auth_status(self, **kwargs):
        oauth_cfg = self._google_oauth_config()
        service_account = self._google_service_account_status()
        return {
            'google_oauth_web_login_ready': bool(oauth_cfg),
            'google_oauth_redirect_uri': oauth_cfg['redirect_uri'] if oauth_cfg else '',
            'google_oauth_client_secret_returned': False,
            'service_account_backend_ready': service_account.get('enabled') and service_account.get('token_acquired'),
            'service_account': service_account,
            'boundary': {
                'service_account_replaces_user_login': False,
                'user_login_requires_oauth_web_client': True,
                'private_key_returned': False,
                'credential_storage_in_repo': False,
            },
        }
