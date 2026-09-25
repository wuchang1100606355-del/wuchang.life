import json
import os
import re
import secrets
import stat
import time
from pathlib import Path
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from odoo import http
from odoo.http import request

from ..services.account_linking import (
    CANONICAL_CALLBACK_URL,
    IDENTITY_PROJECTION_HEADERS,
    identity_packet_ref_from_link_context,
    strict_channel_callback_security_decision,
    transient_link_context,
)
from ..services.oauth_config import (
    build_callback_uri,
    trusted_google_authorization_url,
    trusted_google_userinfo_url,
)


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_CLIENT_SECRET_FILE_ENV = "WUCHANG_GOOGLE_CLIENT_SECRET_FILE"
GOOGLE_CLIENT_SECRET_FILE = Path("/run/secrets/google_member_client_secret")


class WuchangGoogleMemberLogin(http.Controller):
    def _landing_enabled(self, surface):
        gate = request.env["wuchang.community.feature.gate"]
        if hasattr(gate, "is_landing_enabled"):
            return gate.is_landing_enabled(surface)
        if hasattr(gate, "is_enabled"):
            return gate.is_enabled(f"landing.{surface}", default=True)
        return False

    def _landing_hold(self, surface):
        return self._status_page(
            "會員入口目前已安全關閉",
            "此入口目前由既有產品控制閘關閉，未授權的請求不會繞過身分與權限。",
            f"LANDING_CONTROL_DISABLED:{surface}",
            status=503,
        )

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
      <a class="primary" href="https://wuchang.life/">回到公開首頁</a>
      <a class="secondary" href="https://member.wuchang.life/">回到會員入口</a>
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
        return CANONICAL_CALLBACK_URL

    def _client_secret(self):
        configured_path = Path(os.environ.get(GOOGLE_CLIENT_SECRET_FILE_ENV, ""))
        if configured_path != GOOGLE_CLIENT_SECRET_FILE:
            return None
        try:
            file_status = configured_path.lstat()
            if not stat.S_ISREG(file_status.st_mode):
                return None
            if stat.S_IMODE(file_status.st_mode) != 0o600:
                return None
            secret_value = configured_path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            return None
        return secret_value or None

    @http.route("/google/member/login", type="http", auth="public", csrf=False)
    def google_member_login(self, **kw):
        if not self._landing_enabled("google_login"):
            return self._landing_hold("google_login")
        provider = self._google_provider()
        if not provider or not provider.enabled or not provider.client_id:
            return self._status_page(
                "Google 會員入口尚未完成正式串接",
                "目前 Google 會員登入尚未完成正式設定。請改用現場協助註冊、LINE 入口，或洽店長與系統管理員。",
                "GOOGLE_CONFIG_REQUIRED",
                status=503,
            )

        state = secrets.token_urlsafe(24)
        nonce = secrets.token_urlsafe(24)
        request.session["wuchang_google_oauth_state"] = state
        request.session["wuchang_google_oidc_nonce"] = nonce
        request.session["wuchang_google_oauth_issued_at_epoch"] = int(time.time())
        group_packet_ref = kw.get("group_packet_ref")
        if group_packet_ref:
            request.session["wuchang_group_packet_ref"] = group_packet_ref
        normalized_client_id = re.sub(
            r"^(.+\.apps\.googleusercontent\.com)\1$",
            r"\1",
            (provider.client_id or "").strip(),
        )
        params = {
            "client_id": normalized_client_id,
            "redirect_uri": self._redirect_uri(),
            "response_type": "code",
            "scope": "openid profile email",
            "state": state,
            "nonce": nonce,
            "prompt": "select_account",
        }
        authorization_url = trusted_google_authorization_url(provider.auth_endpoint)
        parsed_authorization = urlsplit(authorization_url)
        if parsed_authorization.query:
            authorization_url = urlunsplit(
                (
                    parsed_authorization.scheme,
                    parsed_authorization.netloc,
                    parsed_authorization.path,
                    "",
                    "",
                )
            )
        return request.redirect(
            f"{authorization_url}?{urlencode(params)}",
            code=302,
            local=False,
        )

    @http.route("/google/member/callback", type="http", auth="public", csrf=False)
    def google_member_callback(self, **kw):
        if not self._landing_enabled("google_login"):
            return self._landing_hold("google_login")
        if not request.session.uid:
            return self._status_page(
                "Google 登入安全檢查未通過",
                "必須先由唯一 Odoo 會員入口登入，再進行 Google channel 綁定。",
                "AUTHENTICATED_MEMBER_SESSION_REQUIRED",
                status=401,
            )
        error = kw.get("error")
        if error:
            return self._status_page(
                "Google 登入未完成",
                "本次 Google 登入未被授權。請重新操作，或改用現場協助註冊。",
                "GOOGLE_LOGIN_DENIED",
                status=400,
            )

        expected_state = request.session.pop("wuchang_google_oauth_state", None)
        expected_nonce = request.session.pop("wuchang_google_oidc_nonce", None)
        issued_at_epoch = request.session.pop(
            "wuchang_google_oauth_issued_at_epoch",
            None,
        )
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
        secret_value = self._client_secret()
        if not provider or not provider.enabled or not provider.client_id or not secret_value:
            return self._status_page(
                "Google 會員入口尚未完成正式串接",
                "目前 Google OAuth 尚未完成正式設定。公開頁面不顯示技術細節，請洽系統管理員。",
                "GOOGLE_OAUTH_CREDENTIALS_REQUIRED",
                status=503,
            )
        callback_url = self._redirect_uri()
        if callback_url != CANONICAL_CALLBACK_URL:
            return self._status_page(
                "Google 登入安全檢查未通過",
                "Google callback 尚未鎖定正式會員網域，請洽系統管理員完成確認。",
                "GOOGLE_CALLBACK_HOST_MISMATCH",
                status=503,
            )

        token_payload = urlencode(
            {
                "code": code,
                "client_id": provider.client_id,
                "client_secret": secret_value,
                "redirect_uri": callback_url,
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
            id_token_value = token_data["id_token"]
            tokeninfo_req = Request(
                f"{GOOGLE_TOKENINFO_URL}?{urlencode({'id_token': id_token_value})}",
                method="GET",
            )
            with urlopen(tokeninfo_req, timeout=10) as response:
                token_claims = json.loads(response.read().decode("utf-8"))
            access_value = token_data["access_token"]
            user_req = Request(
                trusted_google_userinfo_url(
                    provider.data_endpoint,
                    provider.validation_endpoint,
                ),
                headers={"Authorization": f"Bearer {access_value}"},
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

        security = strict_channel_callback_security_decision(
            expected_state=expected_state,
            received_state=kw.get("state"),
            expected_nonce=expected_nonce,
            token_claims=token_claims,
            expected_audience=provider.client_id,
            authenticated_subject=userinfo.get("sub"),
            callback_url=callback_url,
            issued_at_epoch=issued_at_epoch,
            current_epoch=int(time.time()),
            replay_state="SESSION_STATE_CONSUMED_ONCE",
        )
        if security["decision"] != "PASS":
            return self._status_page(
                "Google 登入安全檢查未通過",
                "Google 身分驗證結果不一致，請重新從正式入口操作。",
                security["reason"],
                status=400,
            )

        authority = request.env["wuchang.member.external.auth"]
        resolution = authority.resolve_provider_subject_for_session(
            "google",
            userinfo.get("sub"),
            request.env.user,
        )
        link_context = transient_link_context(userinfo, resolution)
        request.session["wuchang_google_link_context"] = link_context
        # Legacy _wuchang_get_or_create_google_member is intentionally not used:
        # the callback never creates or email-merges a partner.
        if link_context["link_state"] not in {"PROVIDER_LINK_FOUND", "LINK_CONFIRMED"}:
            return self._status_page(
                "Google 帳戶需要本地確認",
                "Google 身分已驗證，但尚未取得本地會員綁定授權。請重新驗證既有帳戶或由授權人員審閱。",
                link_context["link_state"],
                status=202,
            )
        group_packet_ref = request.session.get("wuchang_group_packet_ref")
        if group_packet_ref:
            request.session["wuchang_group_auth_ref"] = {
                "provider": "google",
                "provider_user_ref": link_context["provider_subject_reference"],
                "display_ref": "google_member_masked",
                "hash_subject": authority.hash_subject("google", userinfo.get("sub")),
            }
            return request.redirect(f"/wuchang/member/register/group/{group_packet_ref}")
        return request.redirect("/google/member/welcome")

    @http.route("/google/member/welcome", type="http", auth="user", csrf=False)
    def google_member_welcome(self, **kw):
        if not self._landing_enabled("external_api"):
            return self._landing_hold("external_api")
        google_context = request.session.get("wuchang_google_link_context") or {}
        line_context = request.session.get("wuchang_line_link_context") or {}
        link_context = google_context or line_context
        login_surface = "google_login" if google_context else "line_login"
        if not self._landing_enabled(login_surface):
            return self._landing_hold(login_surface)
        if link_context.get("link_state") not in {"PROVIDER_LINK_FOUND", "LINK_CONFIRMED"}:
            return self._status_page(
                "會員狀態尚未啟用",
                "目前找不到有效的會員登入狀態。請從正式入口重新操作。",
                "MEMBER_SESSION_INACTIVE",
                status=401,
            )
        response = self._success_page(
            "會員入口已完成",
            "會員身分驗證與本地綁定引用已確認，請依現場指示繼續。",
        )
        response.headers[IDENTITY_PROJECTION_HEADERS["identity_ref"]] = (
            identity_packet_ref_from_link_context(link_context)
        )
        return response
