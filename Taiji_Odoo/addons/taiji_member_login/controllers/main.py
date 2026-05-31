import json
from pathlib import Path

from odoo import http
from odoo.http import request


TAIJI_ROOT = Path.home() / "Taiji_Hub"
SESSION_FILE = TAIJI_ROOT / "runtime/state/current_member_session.json"
APPROVED_FILE = TAIJI_ROOT / "data/internal_members/approved_members.jsonl"


def _load_session():
    if SESSION_FILE.exists():
        try:
            return json.loads(SESSION_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _approved_count():
    if not APPROVED_FILE.exists():
        return 0
    count = 0
    for line in APPROVED_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.strip():
            count += 1
    return count


class TaijiMemberLogin(http.Controller):

    @http.route("/taiji/member/status", type="json", auth="public", website=True, csrf=False)
    def member_status(self, **kwargs):
        session = _load_session()
        return {
            "ok": True,
            "session_state": session.get("session_state", "not_logged_in"),
            "member_email": session.get("member_email", ""),
            "member_name": session.get("member_name", ""),
            "member_id": session.get("member_id", ""),
            "status": session.get("status", ""),
            "authority_role": session.get("authority_role", ""),
            "approved_count": _approved_count(),
            "mobile_verified": session.get("mobile_verified", False),
            "mobile_verify_method": session.get("mobile_verify_method", ""),
            "mobile_verify_status": session.get("mobile_verify_status", ""),
            "login_assurance": session.get("login_assurance", ""),
            "secret_policy": "no_password_no_token_no_private_key",
        }

    @http.route("/taiji/member/login", type="http", auth="public", website=True, csrf=False)
    def member_login_redirect(self, **kwargs):
        session = _load_session()
        login = session.get("member_email") or "admin@wuchang.life"
        return request.redirect(f"/web/login?login={login}")

    @http.route("/taiji/member/local-session", type="http", auth="public", website=True, csrf=False)
    def member_local_session(self, **kwargs):
        session = _load_session()
        html = f"""
        <html>
        <head><title>Taiji Member Session</title></head>
        <body style="font-family: sans-serif; padding: 24px;">
          <h2>五常內部會員狀態</h2>
          <pre>{json.dumps(session, ensure_ascii=False, indent=2)}</pre>
          <p><a href="/web/login?login={session.get('member_email','admin@wuchang.life')}">回 Odoo 登入頁</a></p>
        </body>
        </html>
        """
        return request.make_response(html, headers=[("Content-Type", "text/html; charset=utf-8")])
