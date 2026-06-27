#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import subprocess
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path("/home/taiji_admin/Taiji_Hub")
CONSOLE = ROOT / "tools" / "d8_total_field_console.sh"
REPORT_DIR = ROOT / "runtime" / "total_field" / "dashboard"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def run_console(args: list[str], timeout: int = 30) -> dict:
    proc = subprocess.run(
        [str(CONSOLE)] + args,
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    return {
        "cmd": ["tools/d8_total_field_console.sh"] + args,
        "returncode": proc.returncode,
        "output": proc.stdout[-12000:],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def save_dashboard_report(name: str, payload: dict) -> str:
    path = REPORT_DIR / f"D8_DASHBOARD_{name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path.relative_to(ROOT).as_posix()


def page(title: str, body: str) -> bytes:
    nav = """
    <nav>
      <a href="/">home</a> |
      <a href="/status">status</a> |
      <a href="/doctor">doctor</a> |
      <a href="/alerts">alerts</a> |
      <a href="/redteam">redteam</a> |
      <a href="/evals">evals</a> |
      <a href="/preflight">preflight</a> |
      <a href="/writeback">writeback</a> |
      <a href="/seal">seal</a>
    </nav><hr>
    """
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
:root{{color-scheme:light dark}}
body{{font-family:system-ui,-apple-system,BlinkMacSystemFont,sans-serif;margin:24px;max-width:1180px;line-height:1.45}}
nav a{{margin-right:10px}}
pre{{background:#111;color:#eee;padding:14px;white-space:pre-wrap;border-radius:8px;overflow:auto}}
input,textarea,select{{width:100%;max-width:900px;margin:6px 0 14px;padding:8px;box-sizing:border-box}}
button{{padding:9px 15px;cursor:pointer}}
.badge{{display:inline-block;padding:2px 8px;border:1px solid #999;border-radius:999px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}}
.panel{{border:1px solid #9995;border-radius:8px;padding:12px}}
</style></head><body>{nav}{body}</body></html>""".encode("utf-8")


def render_result(title: str, result: dict) -> str:
    save_dashboard_report(title.lower().replace(" ", "_"), result)
    return (
        f"<h1>{html.escape(title)}</h1>"
        f"<p><span class='badge'>returncode {result['returncode']}</span></p>"
        f"<pre>{html.escape(result['output'])}</pre>"
    )


class Handler(BaseHTTPRequestHandler):
    allow_writeback = False

    def log_message(self, fmt: str, *args) -> None:
        return

    def send_page(self, title: str, body: str, code: int = 200) -> None:
        data = page(title, body)
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            if u.path == "/":
                body = """
                <h1>D8 Total Field Dashboard</h1>
                <p><span class="badge">local only</span> <span class="badge">127.0.0.1</span> <span class="badge">writeback disabled by default</span></p>
                <div class="grid">
                  <div class="panel"><b>Status</b><br>Databaseized D8 overview.</div>
                  <div class="panel"><b>Alerts</b><br>Non-executable redteam-only possible alerts.</div>
                  <div class="panel"><b>Preflight</b><br>Run guard checks before work.</div>
                </div>
                """
                self.send_page("D8 Dashboard", body)
            elif u.path == "/status":
                self.send_page("status", render_result("Status", run_console(["status"])))
            elif u.path == "/doctor":
                self.send_page("doctor", render_result("Doctor", run_console(["doctor"])))
            elif u.path == "/alerts":
                self.send_page("alerts", render_result("Alerts", run_console(["alerts", "--limit", q.get("limit", ["20"])[0]])))
            elif u.path == "/redteam":
                self.send_page("redteam", render_result("Redteam", run_console(["redteam", "--limit", q.get("limit", ["20"])[0]])))
            elif u.path == "/evals":
                self.send_page("evals", render_result("Evals", run_console(["evals", "--limit", q.get("limit", ["20"])[0]])))
            elif u.path == "/seal":
                self.send_page("seal", render_result("Seal", run_console(["seal"])))
            elif u.path == "/preflight":
                if "task_name" not in q:
                    form = """
                    <h1>Preflight</h1>
                    <form method="get" action="/preflight">
                      <label>Task name</label><input name="task_name" value="SAFE_TOTAL_FIELD_STATUS_READ">
                      <label>Mode</label><select name="mode"><option>sandbox</option><option>review</option><option>land</option><option>production</option></select>
                      <label>Scope JSON</label><textarea name="scope_json" rows="6">{"readonly":true,"target":"d8_total_field_current_status"}</textarea>
                      <button>Run preflight</button>
                    </form>
                    """
                    self.send_page("preflight", form)
                else:
                    result = run_console([
                        "preflight",
                        "--task-name", q.get("task_name", [""])[0],
                        "--mode", q.get("mode", ["sandbox"])[0],
                        "--scope-json", q.get("scope_json", ["{}"])[0],
                    ])
                    self.send_page("preflight result", render_result("Preflight", result))
            elif u.path == "/writeback":
                if not self.allow_writeback:
                    self.send_page("writeback disabled", "<h1>Writeback disabled</h1><p>Restart dashboard with <code>--enable-writeback</code> to enable this local-only route.</p>", 403)
                else:
                    self.send_page("writeback", "<h1>Writeback</h1><p>Use CLI writeback for explicit audited evidence payloads.</p>")
            else:
                self.send_page("not found", "<h1>404</h1>", 404)
        except Exception as exc:
            self.send_page("error", f"<h1>Error</h1><pre>{html.escape(str(exc))}</pre>", 500)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--enable-writeback", action="store_true")
    args = ap.parse_args()
    if args.host not in ("127.0.0.1", "localhost"):
        raise SystemExit("Refusing non-local host")
    Handler.allow_writeback = args.enable_writeback
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"STATE=PASS_D8_LOCAL_DASHBOARD_READY URL=http://{args.host}:{args.port}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
