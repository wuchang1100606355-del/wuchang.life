import json
import secrets
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from odoo import http
from odoo.http import request


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class WuchangGoogleMemberLogin(http.Controller):
    def _param(self, key):
        return request.env["ir.config_parameter"].sudo().get_param(key)

    def _base_url(self):
        configured = self._param("wuchang_google_member_login.base_url")
        return (configured or request.httprequest.host_url.rstrip("/")).rstrip("/")

    def _redirect_uri(self):
        configured = self._param("wuchang_google_member_login.redirect_uri")
        return configured or f"{self._base_url()}/google/member/callback"

    @http.route("/google/member/login", type="http", auth="public", csrf=False)
    def google_member_login(self, **kw):
        client_id = self._param("wuchang_google_member_login.client_id")
        if not client_id:
            return request.make_response(
                "Google member login is not configured: missing client_id.",
                status=503,
            )

        state = secrets.token_urlsafe(24)
        request.session["wuchang_google_oauth_state"] = state
        params = {
            "client_id": client_id,
            "redirect_uri": self._redirect_uri(),
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "select_account",
        }
        return request.redirect(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")

    @http.route("/google/member/callback", type="http", auth="public", csrf=False)
    def google_member_callback(self, **kw):
        error = kw.get("error")
        if error:
            return request.make_response(f"Google login denied: {error}", status=400)

        expected_state = request.session.pop("wuchang_google_oauth_state", None)
        if not expected_state or kw.get("state") != expected_state:
            return request.make_response("Invalid Google login state.", status=400)

        code = kw.get("code")
        if not code:
            return request.make_response("Missing Google authorization code.", status=400)

        client_id = self._param("wuchang_google_member_login.client_id")
        client_secret = self._param("wuchang_google_member_login.client_secret")
        if not client_id or not client_secret:
            return request.make_response(
                "Google member login is not configured: missing OAuth credentials.",
                status=503,
            )

        token_payload = urlencode(
            {
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": self._redirect_uri(),
                "grant_type": "authorization_code",
            }
        ).encode("utf-8")
        token_req = Request(
            GOOGLE_TOKEN_URL,
            data=token_payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urlopen(token_req, timeout=10) as response:
                token_data = json.loads(response.read().decode("utf-8"))
            access_token = token_data["access_token"]
            user_req = Request(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            with urlopen(user_req, timeout=10) as response:
                userinfo = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            return request.make_response(f"Google login exchange failed: {exc}", status=502)

        partner = request.env["res.partner"].sudo()._wuchang_get_or_create_google_member(userinfo)
        request.session["wuchang_google_member_partner_id"] = partner.id
        return request.redirect("/google/member/welcome")

    @http.route("/google/member/welcome", type="http", auth="public", csrf=False)
    def google_member_welcome(self, **kw):
        partner_id = request.session.get("wuchang_google_member_partner_id")
        partner = partner_id and request.env["res.partner"].sudo().browse(partner_id)
        if not partner or not partner.exists():
            return request.make_response("Google member session is not active.", status=401)
        name = partner.display_name or "Google member"
        return request.make_response(f"Google member joined: {name}")
