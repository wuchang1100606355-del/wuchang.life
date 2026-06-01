"""PM3 LINE OAuth login integration."""

import logging
import os
import secrets
from urllib.parse import urlencode

import requests
from werkzeug.exceptions import BadRequest
from werkzeug.utils import redirect

from odoo import _, http
from odoo.addons.web.controllers.home import ensure_db
from odoo.http import request


_logger = logging.getLogger(__name__)


class PM3LineAuthController(http.Controller):
    @staticmethod
    def _safe_error_response(message, status=200):
        body = (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<title>LINE Login</title></head><body>"
            f"<p>{message}</p>"
            "<p><a href='/web/login?db=postgres'>返回登入頁</a></p>"
            "</body></html>"
        )
        return request.make_response(body, headers=[("Content-Type", "text/html; charset=utf-8")], status=status)

    @staticmethod
    def _get_secret_value(config_param, env_key):
        secret_ref = request.env["ir.config_parameter"].sudo().get_param(config_param)
        if secret_ref:
            secret_value = request.httprequest.environ.get(secret_ref) or os.environ.get(secret_ref)
            if secret_value:
                return secret_value
        return os.environ.get(env_key)


    def _line_oauth_config(self):
        return {
            "client_id": "2008646241",
            "client_secret": "54a74765c5949738528d8adfafe5eadf",
            "redirect_uri": "http://127.0.0.1:8069/auth/line/callback",
        }

    @http.route("/auth/line/login", type="http", auth="none", sitemap=False, csrf=False)
    def line_login(self, **kw):
        cfg = self._line_oauth_config()
        if not cfg:
            return self._safe_error_response(_("LINE Login 尚未設定完成，請聯絡管理員。"))

        oauth_state = secrets.token_urlsafe(24)
        request.session["line_oauth_state"] = oauth_state

        auth_url = "https://access.line.me/oauth2/v2.1/authorize?" + urlencode({
            "response_type": "code",
            "client_id": cfg["client_id"],
            "redirect_uri": cfg["redirect_uri"],
            "state": oauth_state,
            "scope": "profile openid",
        })
        return redirect(auth_url)

    @http.route("/auth/line/callback", type="http", auth="none", sitemap=False, csrf=False)
    def line_callback(self, code=None, state=None, error=None, **kw):
        ensure_db()
        cfg = self._line_oauth_config()
        if not cfg:
            return self._safe_error_response(_("LINE Login 尚未設定完成，請聯絡管理員。"))

        if error:
            _logger.error("LINE login authorization failed: %s", error)
            return self._safe_error_response(_("LINE 授權被拒絕，請重試。"))

        expected_state = request.session.get("line_oauth_state")
        request.session.pop("line_oauth_state", None)
        if not state or not expected_state or state != expected_state:
            return self._safe_error_response(_("LINE 驗證狀態失效，請重新登入。"))
        if not code:
            raise BadRequest("缺少授權碼")

        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": cfg["redirect_uri"],
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
        }

        try:
            token_res = requests.post(
                "https://api.line.me/oauth2/v2.1/token",
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )
            token_res.raise_for_status()
            access_token = token_res.json().get("access_token")

            profile_res = requests.get(
                "https://api.line.me/v2/profile",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            profile_res.raise_for_status()
            line_profile = profile_res.json()

            user = request.env["res.users"].sudo().get_or_create_by_line_id(line_profile)
            if user:
                request.session.uid = user.id
                request.session.login = user.login
                _logger.info("LINE login success: uid=%s", user.id)
                return redirect("/my/home")
            return self._safe_error_response(_("無法建立五維碼身分代理，請洽社區發展協會。"))
        except Exception as exc:
            _logger.error("LINE login exception: %s", exc)
            return self._safe_error_response(_("系統連線異常，無法完成登入。"), status=500)

    @http.route("/auth/line/debug_redirect", type="http", auth="none", sitemap=False, csrf=False)
    def line_debug_redirect(self, **kw):
        return redirect("https://access.line.me/oauth2/v2.1/authorize?response_type=code&client_id=2008646241&redirect_uri=http%3A%2F%2F127.0.0.1%3A8069%2Fauth%2Fline%2Fcallback&state=debug&scope=profile%20openid")
