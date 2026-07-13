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
    def _html_page(self, title, message, reference):
        return """<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{title}</title>
  <style>
    body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:#102139; color:#172033; }}
    main {{ min-height:100vh; display:flex; align-items:center; justify-content:center; padding:32px; background:linear-gradient(135deg,#102139,#24443c); }}
    section {{ width:min(680px,100%); background:#fff; border-radius:8px; padding:34px; box-shadow:0 24px 80px rgba(2,8,23,.32); }}
    .kicker {{ color:#9a6a08; font-weight:700; margin:0 0 12px; }}
    h1 {{ margin:0; font-size:clamp(28px,5vw,44px); line-height:1.15; }}
    p {{ color:#334155; line-height:1.75; font-size:17px; }}
    .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin:24px 0; }}
    .grid div {{ background:#f8fafc; border:1px solid #dbe7f4; padding:16px; border-radius:6px; }}
    strong {{ display:block; margin-bottom:8px; color:#172033; }}
    a {{ display:inline-flex; min-height:44px; align-items:center; justify-content:center; padding:10px 16px; border-radius:6px; text-decoration:none; font-weight:700; }}
    .primary {{ background:#17466f; color:#fff; }}
    .secondary {{ background:#f8fafc; color:#172033; border:1px solid #d8dee8; margin-left:8px; }}
    .ref {{ margin-top:20px; color:#64748b; font-size:14px; }}
    @media (max-width:640px) {{ .grid {{ grid-template-columns:1fr; }} .secondary {{ margin-left:0; margin-top:8px; }} a {{ width:100%; }} }}
  </style>
</head>
<body>
  <main>
    <section>
      <p class="kicker">五常社區發展協會 × 聊國咖啡館重新總店</p>
      <h1>{title}</h1>
      <p>{message}</p>
      <div class="grid">
        <div><strong>現場協助</strong><span>請由店長或櫃台協助完成會員服務流程。</span></div>
        <div><strong>安全邊界</strong><span>公開頁面不顯示技術密鑰、會員明文或外部服務錯誤細節。</span></div>
      </div>
      <a class="primary" href="/web/login">回到登入入口</a>
      <a class="secondary" href="/web/signup">前往會員註冊</a>
      <div class="ref">參考代碼：{reference}</div>
    </section>
  </main>
</body>
</html>""".format(title=title, message=message, reference=reference)

    def _status_page(self, title, message, reference, status=200):
        return request.make_response(self._html_page(title, message, reference), status=status)

    def _success_page(self, title, message):
        return request.make_response(self._html_page(title, message, "GOOGLE_LOGIN_COMPLETE"))

    def _param(self, key):
        return request.env["ir.config_parameter"].sudo().get_param(key)

    def _google_provider(self):
        provider = request.env.ref("auth_oauth.provider_google", raise_if_not_found=False)
        return provider.sudo() if provider else provider

    def _base_url(self):
        configured = self._param("wuchang_google_member_login.base_url")
        web_base_url = self._param("web.base.url")
        return (configured or web_base_url or request.httprequest.host_url).rstrip("/")

    def _redirect_uri(self):
        configured = self._param("wuchang_google_member_login.redirect_uri")
        return configured or f"{self._base_url()}/google/member/callback"

    @http.route("/google/member/login", type="http", auth="public", csrf=False)
    def google_member_login(self, **kw):
        provider = self._google_provider()
        if not provider or not provider.enabled or not provider.client_id:
            return self._status_page(
                "Google 會員入口尚未完成正式串接",
                "目前 Google 會員登入尚未完成正式設定。請改用現場協助註冊、LINE 入口，或洽店長與系統管理員。",
                "GOOGLE_CONFIG_REQUIRED",
                status=503,
            )

        state = secrets.token_urlsafe(24)
        request.session["wuchang_google_oauth_state"] = state
        group_packet_ref = kw.get("group_packet_ref")
        if group_packet_ref:
            request.session["wuchang_group_packet_ref"] = group_packet_ref
        params = {
            "client_id": provider.client_id,
            "redirect_uri": self._redirect_uri(),
            "response_type": "code",
            "scope": provider.scope or "openid profile email",
            "state": state,
            "access_type": "offline",
            "prompt": "select_account",
        }
        return request.redirect(f"{provider.auth_endpoint or GOOGLE_AUTH_URL}?{urlencode(params)}")

    @http.route("/google/member/callback", type="http", auth="public", csrf=False)
    def google_member_callback(self, **kw):
        error = kw.get("error")
        if error:
            return self._status_page(
                "Google 登入未完成",
                "本次 Google 登入未被授權。請重新操作，或改用現場協助註冊。",
                "GOOGLE_LOGIN_DENIED",
                status=400,
            )

        expected_state = request.session.pop("wuchang_google_oauth_state", None)
        if not expected_state or kw.get("state") != expected_state:
            return self._status_page(
                "Google 登入安全檢查未通過",
                "本次 Google 登入狀態已失效。請重新從正式入口操作。",
                "GOOGLE_STATE_MISMATCH",
                status=400,
            )

        code = kw.get("code")
        if not code:
            return self._status_page(
                "Google 登入尚未完成",
                "Google 回傳資料不完整，請重新操作，或請店長協助現場註冊。",
                "GOOGLE_CALLBACK_MISSING_CODE",
                status=400,
            )

        provider = self._google_provider()
        client_secret = self._param("wuchang_google_member_login.client_secret")
        if not provider or not provider.enabled or not provider.client_id or not client_secret:
            return self._status_page(
                "Google 會員入口尚未完成正式串接",
                "目前 Google OAuth 尚未完成正式設定。公開頁面不顯示技術細節，請洽系統管理員。",
                "GOOGLE_OAUTH_CREDENTIALS_REQUIRED",
                status=503,
            )

        token_payload = urlencode(
            {
                "code": code,
                "client_id": provider.client_id,
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
                provider.data_endpoint or provider.validation_endpoint or GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            with urlopen(user_req, timeout=10) as response:
                userinfo = json.loads(response.read().decode("utf-8"))
        except Exception:
            return self._status_page(
                "Google 登入暫時無法完成",
                "外部 Google 授權回應未通過。公開頁面不顯示技術細節，請洽系統管理員檢查設定。",
                "GOOGLE_TOKEN_EXCHANGE_FAILED",
                status=502,
            )

        partner = request.env["res.partner"].sudo()._wuchang_get_or_create_google_member(userinfo)
        request.session["wuchang_google_member_partner_id"] = partner.id
        group_packet_ref = request.session.get("wuchang_group_packet_ref")
        if group_packet_ref:
            subject_hash = request.env["wuchang.member.external.auth"].sudo().hash_subject("google", userinfo.get("sub"))
            request.session["wuchang_group_auth_ref"] = {
                "provider": "google",
                "provider_user_ref": subject_hash,
                "display_ref": "google_member_masked",
            }
            return request.redirect(f"/wuchang/member/register/group/{group_packet_ref}")
        return request.redirect("/google/member/welcome")

    @http.route("/google/member/welcome", type="http", auth="public", csrf=False)
    def google_member_welcome(self, **kw):
        partner_id = request.session.get("wuchang_google_member_partner_id")
        partner = partner_id and request.env["res.partner"].sudo().browse(partner_id)
        if not partner or not partner.exists():
            return self._status_page(
                "Google 會員狀態尚未啟用",
                "目前找不到有效的 Google 會員登入狀態。請從正式入口重新操作。",
                "GOOGLE_SESSION_INACTIVE",
                status=401,
            )
        name = partner.display_name or "Google member"
        return self._success_page(
            "Google 會員入口已完成",
            "%s，會員登入已完成，請依現場指示繼續。" % name,
        )
