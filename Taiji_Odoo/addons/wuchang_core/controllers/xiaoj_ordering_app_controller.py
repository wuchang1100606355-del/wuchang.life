# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from .w7tp_8d_packet_gate import validate_xiaoj_8d_packet_gate, render_xiaoj_8d_packet_denied_page


class XiaoJOrderingAppController(http.Controller):
    @http.route("/wuchang/xiaoj/ordering", type="http", auth="user", website=True, csrf=False)
    def xiaoj_ordering_app(self, **kw):
        gate = validate_xiaoj_8d_packet_gate(request)
        if not gate.get("allowed"):
            return render_xiaoj_8d_packet_denied_page(gate)
        request.session["w7tp_xiaoj_gate_mode"] = gate.get("mode")
        request.session["w7tp_xiaoj_packet_ref"] = gate.get("packet_ref")
        mode = (kw.get("mode") or "staff_pos").strip()
        html = """<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>聊國咖啡館｜小J 主權式影音點餐 AI</title>
  <link rel="manifest" href="/wuchang_core/static/src/xiaoj_ordering/xiaoj_ordering.webmanifest"/>
  <link rel="stylesheet" href="/wuchang_core/static/src/xiaoj_ordering/xiaoj_ordering_app.css"/>
</head>
<body data-start-mode="%s">
  <main id="xiaoj-ordering-app" class="app-shell">
    <noscript>此介面需要啟用 JavaScript。</noscript>
  </main>
  <script src="/wuchang_core/static/src/xiaoj_ordering/xiaoj_ordering_app.js"></script>
</body>
</html>""" % mode
        return request.make_response(html, headers=[("Content-Type", "text/html; charset=utf-8")])

    @http.route("/wuchang/xiaoj/ordering/manifest", type="json", auth="user", csrf=False)
    def xiaoj_ordering_manifest(self, **kw):
        return {
            "state": "XIAOJ_ORDERING_BROWSER_APP_READY",
            "route": "/wuchang/xiaoj/ordering",
            "pages": [
                "staff_pos",
                "counter_service_touch",
                "av_ai_menu_display",
                "business_management",
                "hardware_menu_business_settings",
            ],
            "formal_db_write": False,
            "formal_pos_write": False,
            "payment_capture": False,
            "service_restart": False,
            "deploy": False,
            "production_release": False,
            "secret_read": False,
            "member_plaintext_read": False,
        }
