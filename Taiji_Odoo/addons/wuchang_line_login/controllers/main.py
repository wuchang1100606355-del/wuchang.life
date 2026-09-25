import secrets
import time
import requests
from datetime import datetime, timezone
from urllib.parse import urlencode

from odoo import http
from odoo.http import request

from ..services.profile_minimization import (
    CANONICAL_CALLBACK_URL,
    authorization_decision,
    minimized_link_record,
    strict_channel_callback_security_decision,
)


LINE_ID_TOKEN_VERIFY_URL = 'https://api.line.me/oauth2/v2.1/verify'

class WuchangLineLogin(http.Controller):
    def _landing_enabled(self):
        return request.env["wuchang.community.feature.gate"].is_landing_enabled(
            "line_login"
        )

    def _landing_hold(self):
        return self._status_page(
            "LINE 會員入口目前已安全關閉",
            "此入口目前由既有產品控制閘關閉，未授權的請求不會繞過身分與權限。",
            "LANDING_CONTROL_DISABLED:line_login",
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
        return request.make_response(self._html_page(title, message, "LINE_LOGIN_COMPLETE"))

    @http.route('/line/login', type='http', auth='user', website=False, csrf=False)
    def line_login(self, **kw):
        if not self._landing_enabled():
            return self._landing_hold()
        channel_id = request.env['ir.config_parameter'].sudo().get_param('wuchang_line_login.channel_id')
        redirect_uri = request.env['ir.config_parameter'].sudo().get_param('wuchang_line_login.redirect_uri')

        if not channel_id or not redirect_uri:
            return self._status_page(
                "LINE 會員入口尚未完成正式串接",
                "目前 LINE 會員入口尚未完成正式設定。請改用現場協助註冊，或洽店長與系統管理員。",
                "LINE_CONFIG_REQUIRED",
                status=503,
            )
        if redirect_uri != CANONICAL_CALLBACK_URL:
            return self._status_page(
                "LINE 登入安全檢查未通過",
                "LINE callback 尚未鎖定正式會員網域，請洽系統管理員完成確認。",
                "LINE_CALLBACK_HOST_MISMATCH",
                status=503,
            )

        state = secrets.token_urlsafe(24)
        nonce = secrets.token_urlsafe(24)
        request.session['wuchang_line_state'] = state
        request.session['wuchang_line_nonce'] = nonce
        request.session['wuchang_line_issued_at_epoch'] = int(time.time())
        group_packet_ref = kw.get('group_packet_ref')
        if group_packet_ref:
            request.session['wuchang_group_packet_ref'] = group_packet_ref

        params = {
            'response_type': 'code',
            'client_id': channel_id,
            'redirect_uri': redirect_uri,
            'state': state,
            'nonce': nonce,
            'scope': 'profile openid',
        }

        return request.redirect('https://access.line.me/oauth2/v2.1/authorize?' + urlencode(params))

    @http.route('/line/callback', type='http', auth='public', website=False, csrf=False)
    def line_callback(self, **kw):
        if not self._landing_enabled():
            return self._landing_hold()
        if not request.session.uid:
            return self._status_page(
                "LINE 登入安全檢查未通過",
                "必須先由唯一 Odoo 會員入口登入，再進行 LINE channel 綁定。",
                "AUTHENTICATED_MEMBER_SESSION_REQUIRED",
                status=401,
            )
        code = kw.get('code')
        state = kw.get('state')
        saved_state = request.session.pop('wuchang_line_state', None)
        expected_nonce = request.session.pop('wuchang_line_nonce', None)
        issued_at_epoch = request.session.pop(
            'wuchang_line_issued_at_epoch',
            None,
        )

        if not code:
            return self._status_page(
                "LINE 登入尚未完成",
                "LINE 回傳資料不完整，請重新操作，或請店長協助現場註冊。",
                "LINE_CALLBACK_MISSING_CODE",
                status=400,
            )

        if not state or state != saved_state:
            return self._status_page(
                "LINE 登入安全檢查未通過",
                "本次 LINE 登入狀態已失效。請重新從正式入口操作。",
                "LINE_STATE_MISMATCH",
                status=400,
            )

        channel_id = request.env['ir.config_parameter'].sudo().get_param('wuchang_line_login.channel_id')
        channel_secret = request.env['ir.config_parameter'].sudo().get_param('wuchang_line_login.channel_secret')
        redirect_uri = request.env['ir.config_parameter'].sudo().get_param('wuchang_line_login.redirect_uri')
        if not channel_id or not channel_secret or redirect_uri != CANONICAL_CALLBACK_URL:
            return self._status_page(
                "LINE 會員入口尚未完成正式串接",
                "LINE OAuth 或 callback 尚未完成正式設定，請洽系統管理員。",
                "LINE_OAUTH_CONFIGURATION_REQUIRED",
                status=503,
            )

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
            return self._status_page(
                "LINE 登入暫時無法完成",
                "外部 LINE 授權回應未通過。公開頁面不顯示技術細節，請洽系統管理員檢查設定。",
                "LINE_TOKEN_EXCHANGE_FAILED",
                status=502,
            )

        token_data = token_res.json()
        access_token = token_data.get('access_token')
        id_token_value = token_data.get('id_token')
        if not access_token or not id_token_value:
            return self._status_page(
                "LINE 登入安全檢查未通過",
                "LINE 身分驗證資料不完整，請重新從正式入口操作。",
                "LINE_ID_TOKEN_REQUIRED",
                status=400,
            )

        verify_res = requests.post(
            LINE_ID_TOKEN_VERIFY_URL,
            data={
                'id_token': id_token_value,
                'client_id': channel_id,
                'nonce': expected_nonce,
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=20,
        )
        if verify_res.status_code != 200:
            return self._status_page(
                "LINE 登入安全檢查未通過",
                "LINE nonce 或身分聲明未通過驗證，請重新操作。",
                "LINE_ID_TOKEN_VERIFY_FAILED",
                status=400,
            )
        token_claims = verify_res.json()

        profile_res = requests.get(
            'https://api.line.me/v2/profile',
            headers={'Authorization': 'Bearer %s' % access_token},
            timeout=20,
        )

        if profile_res.status_code != 200:
            return self._status_page(
                "LINE 會員資料確認失敗",
                "LINE 會員資料暫時無法確認。請重新操作，或請店長協助現場註冊。",
                "LINE_PROFILE_FAILED",
                status=502,
            )

        profile = profile_res.json()
        line_user_id = profile.get('userId')
        security = strict_channel_callback_security_decision(
            expected_state=saved_state,
            received_state=state,
            expected_nonce=expected_nonce,
            token_claims=token_claims,
            expected_audience=channel_id,
            authenticated_subject=line_user_id,
            callback_url=redirect_uri,
            issued_at_epoch=issued_at_epoch,
            current_epoch=int(time.time()),
            replay_state="SESSION_STATE_CONSUMED_ONCE",
        )
        if security['decision'] != 'PASS':
            return self._status_page(
                "LINE 登入安全檢查未通過",
                "LINE 身分驗證結果不一致，請重新從正式入口操作。",
                security['reason'],
                status=400,
            )

        authority = request.env['wuchang.member.external.auth']
        resolution = authority.resolve_provider_subject_for_session(
            'line',
            line_user_id,
            request.env.user,
        )
        link_context = minimized_link_record(
            profile,
            resolution,
            datetime.now(timezone.utc).isoformat(),
        )
        link_context.update({
            'verified_channel_binding_ref': resolution.get(
                'verified_channel_binding_ref'
            ),
            'member_ref': resolution.get('member_ref'),
        })
        request.session['wuchang_line_link_context'] = link_context
        if authorization_decision(link_context['link_state']) != 'ALLOW':
            return self._status_page(
                "LINE 帳戶需要本地確認",
                "LINE 身分已驗證，但尚未取得本地會員綁定授權。請重新驗證既有帳戶或由授權人員審閱。",
                link_context['link_state'],
                status=202,
            )

        group_packet_ref = request.session.get('wuchang_group_packet_ref')
        if group_packet_ref:
            request.session['wuchang_group_auth_ref'] = {
                'provider': 'line',
                'provider_user_ref': link_context['provider_subject_reference'],
                'display_ref': 'line_member_masked',
                'hash_subject': authority.hash_subject('line', line_user_id),
            }
            return request.redirect('/wuchang/member/register/group/%s' % group_packet_ref)

        return self._success_page(
            "LINE 會員入口已完成",
            "LINE 身分驗證與本地綁定引用已確認，請依現場指示繼續。",
        )
