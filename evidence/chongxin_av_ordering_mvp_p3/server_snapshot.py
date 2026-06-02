from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs
from pathlib import Path
from html import escape
import json, time

ROOT = Path.home() / "chongxin_av_ordering_mvp"
DATA = ROOT / "data"
ORDERS = DATA / "orders.jsonl"
CONFIRMATIONS = DATA / "confirmations.jsonl"
EVIDENCE = ROOT / "evidence"

MENU = [
    ("americano", "美式咖啡", 80),
    ("latte", "拿鐵", 100),
    ("black_tea", "紅茶", 50),
    ("dessert", "今日甜點", 120),
]

def page(body):
    return f'''<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>聊國咖啡館 客戶互動面板</title>
<style>
body{{font-family:sans-serif;background:#f6efe3;color:#2d1b10;padding:18px;font-size:20px}}
.card{{background:white;border-radius:16px;padding:16px;margin:12px 0}}
button,input,select{{font-size:20px;padding:12px;width:100%;margin-top:8px}}
</style></head><body>{body}</body></html>'''

def read_jsonl(path):
    if not path.exists():
        return []
    rows = []
    for line in path.read_text("utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows

def confirmation_key(event):
    return (event.get("order_ts", ""), event.get("item_name", ""))

class H(BaseHTTPRequestHandler):
    def html(self, body):
        b = page(body).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/orders":
            text = ORDERS.read_text("utf-8") if ORDERS.exists() else "NO_ORDERS_YET\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(text.encode("utf-8"))
            return

        if self.path == "/pos":
            confirmations = {
                confirmation_key(event): event
                for event in read_jsonl(CONFIRMATIONS)
            }
            body = "<h1>聊國咖啡館 POS 店員確認</h1><p>僅供店員人工確認，不處理付款。</p>"
            orders = list(reversed(read_jsonl(ORDERS)))
            if not orders:
                body += "<div class='card'><p>目前沒有待確認訂單。</p></div>"
            for order in orders:
                order_ts = str(order.get("ts", ""))
                item_name = str(order.get("item_name", ""))
                confirmed = confirmations.get((order_ts, item_name))
                status = confirmed.get("decision", "") if confirmed else "waiting_pos_confirm"
                body += f'''
<div class="card">
<h2>{escape(item_name)}</h2>
<p>時間：{escape(order_ts)}</p>
<p>選項：{escape(str(order.get("option", "")))}</p>
<p>備註：{escape(str(order.get("note", "")))}</p>
<p>狀態：<b>{escape(status)}</b></p>'''
                if not confirmed:
                    body += f'''
<form method="POST" action="/confirm">
<input type="hidden" name="order_ts" value="{escape(order_ts, quote=True)}">
<input type="hidden" name="item_name" value="{escape(item_name, quote=True)}">
<input name="staff" value="pos_staff" placeholder="店員代號">
<button name="decision" value="confirmed">確認訂單</button>
<button name="decision" value="rejected">拒絕訂單</button>
</form>'''
                body += "</div>"
            self.html(body)
            return

        body = "<h1>聊國咖啡館 客戶互動面板</h1><p>送出後由 POS 店員確認。</p>"
        for item_id, name, price in MENU:
            body += f'''
<div class="card">
<h2>{name}</h2><b>${price}</b>
<form method="POST" action="/order">
<input type="hidden" name="item_id" value="{item_id}">
<input type="hidden" name="item_name" value="{name}">
<input type="hidden" name="price" value="{price}">
<select name="option"><option>正常</option><option>少冰</option><option>去冰</option><option>熱</option></select>
<input name="note" placeholder="備註">
<button>送出點餐意圖</button>
</form>
</div>'''
        self.html(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        data = parse_qs(self.rfile.read(length).decode("utf-8"))
        if self.path == "/confirm":
            decision = data.get("decision", [""])[0]
            if decision not in ("confirmed", "rejected"):
                self.send_error(400, "decision must be confirmed or rejected")
                return
            event = {
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                "source": "pos_staff_panel",
                "order_ts": data.get("order_ts", [""])[0],
                "item_name": data.get("item_name", [""])[0],
                "decision": decision,
                "staff": data.get("staff", ["pos_staff"])[0],
            }
            DATA.mkdir(parents=True, exist_ok=True)
            EVIDENCE.mkdir(parents=True, exist_ok=True)
            with CONFIRMATIONS.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
            (EVIDENCE / "last_pos_confirm_manifest.md").write_text(
                "# Chongxin POS Confirmation Manifest\n\n"
                + json.dumps(event, ensure_ascii=False, indent=2)
                + "\n",
                encoding="utf-8"
            )
            (EVIDENCE / "p3_pos_confirm_report.md").write_text(
                "# Chongxin AV Ordering MVP P3 POS Confirmation Report\n\n"
                f"- evidence_timestamp: {event['ts']}\n"
                f"- order_timestamp: {event['order_ts']}\n"
                f"- item_name: {event['item_name']}\n"
                f"- decision: {event['decision']}\n"
                f"- staff: {event['staff']}\n"
                "- payment_processing: false\n"
                "- odoo_database_write: false\n"
                "- customer_pii: false\n",
                encoding="utf-8"
            )
            self.html("<h1>POS 確認已記錄</h1><p><a href='/pos'>返回 POS 面板</a></p>")
            return

        order = {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "customer_interaction_panel",
            "target": "pos_staff_confirm",
            "item_id": data.get("item_id", [""])[0],
            "item_name": data.get("item_name", [""])[0],
            "price": data.get("price", [""])[0],
            "option": data.get("option", [""])[0],
            "note": data.get("note", [""])[0],
            "status": "waiting_pos_confirm",
        }
        DATA.mkdir(parents=True, exist_ok=True)
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        with ORDERS.open("a", encoding="utf-8") as f:
            f.write(json.dumps(order, ensure_ascii=False) + "\n")
        (EVIDENCE / "last_order_manifest.md").write_text(
            json.dumps(order, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        self.html("<h1>已送出</h1><p>請等候店員於 POS 確認。</p><p><a href='/'>返回</a></p>")

print("CHONGXIN_CUSTOMER_PANEL_READY http://0.0.0.0:8088")
ThreadingHTTPServer(("0.0.0.0", 8088), H).serve_forever()
