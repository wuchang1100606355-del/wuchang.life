#!/usr/bin/env python3
import json, os, secrets, hashlib, datetime
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, urlencode, parse_qs

ROOT = Path(os.environ.get("TAIJI_ROOT", str(Path.home() / "Taiji_Hub")))
SESSION = ROOT / "runtime/state/current_member_session.json"
STATE_FILE = ROOT / "runtime/state/google_login_oauth_state.json"
LEDGER = ROOT / "runtime/ledger/member_login_events.jsonl"
DEAD = ROOT / "runtime/dead_letter/member_google_login_rejected.jsonl"
BINDINGS = ROOT / "data/internal_members/google_login_bindings.jsonl"

for p in [SESSION.parent, LEDGER.parent, DEAD.parent, BINDINGS.parent]:
    p.mkdir(parents=True, exist_ok=True)

def now():
    return datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()

def append_jsonl(path, obj):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def load_session():
    if SESSION.exists():
        try:
            return json.loads(SESSION.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "session_state": "logged_in",
        "member_email": "admin@wuchang.life",
        "member_name": "江政隆 CHIANG CHENG LUNG",
        "status": "approved_internal_founder",
        "authority_role": "founder_internal_member"
    }

def save_session(s):
    SESSION.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")

class H(BaseHTTPRequestHandler):
    def send_json(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def send_html(self, code, html):
        b = html.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def redirect(self, url):
        self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()

    def do_GET(self):
        u = urlparse(self.path)

        if u.path == "/health":
            self.send_json(200, {
                "service": "taiji-google-login",
                "status": "ok",
                "port": 8104,
                "session": str(SESSION),
                "secret_policy": "no_token_no_password_no_private_key"
            })
            return

        if u.path == "/google/status":
            s = load_session()
            html = f"""
            <html><head><title>Taiji Google Login</title></head>
            <body style="font-family:sans-serif;padding:24px;line-height:1.6">
              <h2>五常智慧雲｜Google 登入橋接</h2>
              <p>會員：{s.get("member_name","")} / {s.get("member_email","")}</p>
              <p>會員狀態：{s.get("status","")}</p>
              <p>手機驗證：{s.get("mobile_verify_status","")}</p>
              <p>LINE 狀態：{s.get("line_login_status","")}</p>
              <p>Google 狀態：{s.get("google_login_status","pending_client_config")}</p>
              <p>規則：不存 Google token、不存密碼、不做 Odoo 免密後門。</p>
              <p><a href="/google/login/start">啟動 Google Login</a></p>
              <p><a href="http://127.0.0.1:8069/web/login?login={s.get("member_email","admin@wuchang.life")}">回 Odoo 登入頁</a></p>
              <h3>Session</h3>
              <pre>{json.dumps(s, ensure_ascii=False, indent=2)}</pre>
            </body></html>
            """
            self.send_html(200, html)
            return

        if u.path == "/google/login/start":
            client_id = os.environ.get("GOOGLE_LOGIN_CLIENT_ID", "").strip()
            redirect_uri = os.environ.get("GOOGLE_LOGIN_REDIRECT_URI", "").strip()
            scope = os.environ.get("GOOGLE_LOGIN_SCOPE", "openid email profile").strip()

            s = load_session()

            if not client_id or not redirect_uri:
                s["google_login_status"] = "pending_client_config"
                s["google_login_note"] = "需填 ~/.secrets/taiji_google_login.env 的 GOOGLE_LOGIN_CLIENT_ID / GOOGLE_LOGIN_REDIRECT_URI"
                save_session(s)
                append_jsonl(LEDGER, {
                    "ts": now(),
                    "event": "google_login_start_blocked_missing_client_config",
                    "member_email": s.get("member_email")
                })
                self.redirect("/google/status")
                return

            state = secrets.token_urlsafe(24)
            STATE_FILE.write_text(json.dumps({
                "ts": now(),
                "state_hash": hashlib.sha256(state.encode()).hexdigest(),
                "member_email": s.get("member_email")
            }, ensure_ascii=False, indent=2), encoding="utf-8")

            auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": scope,
                "state": state,
                "access_type": "offline",
                "prompt": "consent"
            })

            s["google_login_status"] = "oauth_started"
            s["google_login_method"] = "google_oauth"
            save_session(s)

            append_jsonl(LEDGER, {
                "ts": now(),
                "event": "google_login_oauth_started",
                "member_email": s.get("member_email")
            })

            self.redirect(auth_url)
            return

        if u.path == "/google/callback":
            qs = parse_qs(u.query)
            code_present = bool(qs.get("code"))
            error = qs.get("error", [""])[0]

            s = load_session()

            if error:
                s["google_login_status"] = "callback_error"
                s["google_login_error"] = error
                save_session(s)
                append_jsonl(DEAD, {
                    "ts": now(),
                    "event": "google_login_callback_error",
                    "error": error,
                    "member_email": s.get("member_email")
                })
                self.redirect("/google/status")
                return

            s["google_login_status"] = "callback_received_manual_token_exchange_required" if code_present else "callback_received_without_code"
            s["google_login_method"] = "google_oauth"
            s["google_login_note"] = "callback 已收到；下一版再做暫態 token exchange，仍不落地 token。"
            save_session(s)

            append_jsonl(BINDINGS, {
                "ts": now(),
                "member_email": s.get("member_email"),
                "method": "google_oauth",
                "status": "callback_received_no_token_stored",
                "code_present": code_present,
                "store_token": False
            })

            append_jsonl(LEDGER, {
                "ts": now(),
                "event": "google_login_callback_received",
                "member_email": s.get("member_email"),
                "code_present": code_present,
                "store_token": False
            })

            self.redirect("/google/status")
            return

        self.send_json(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        return

HTTPServer(("127.0.0.1", 8104), H).serve_forever()
