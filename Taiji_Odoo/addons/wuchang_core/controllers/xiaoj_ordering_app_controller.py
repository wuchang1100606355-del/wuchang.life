# -*- coding: utf-8 -*-
import html
import re

from odoo import http
from odoo.http import request

from .w7tp_8d_packet_gate import validate_xiaoj_8d_packet_gate, render_xiaoj_8d_packet_denied_page


TABLE_REF_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,16}$")


def _safe_table_ref(value):
    table_ref = str(value or "").strip()
    return table_ref if TABLE_REF_PATTERN.fullmatch(table_ref) else ""


class XiaoJOrderingAppController(http.Controller):
    @http.route("/wuchang/xiaoj/ordering", type="http", auth="public", website=True, csrf=False)
    def xiaoj_ordering_app(self, **kw):
        gate = validate_xiaoj_8d_packet_gate(request)
        if not gate.get("allowed"):
            return render_xiaoj_8d_packet_denied_page(gate)
        request.session["w7tp_xiaoj_gate_mode"] = gate.get("mode")
        request.session["w7tp_xiaoj_packet_ref"] = gate.get("packet_ref")
        store_ref = request.env["ir.config_parameter"].sudo().get_param("wuchang.store.ref", "wuchang_cafe_main_store")
        mode = (kw.get("mode") or "staff_pos").strip()
        table_ref = _safe_table_ref(kw.get("table_ref"))
        html_body = """<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>聊國咖啡館｜小J 主權式影音點餐 AI</title>
  <link rel="manifest" href="/wuchang_core/static/src/xiaoj_ordering/xiaoj_ordering.webmanifest"/>
  <link rel="stylesheet" href="/wuchang_core/static/src/xiaoj_ordering/xiaoj_ordering_app.css"/>
</head>
<body data-start-mode="%s" data-table-ref="%s" data-store-ref="%s" data-route="/wuchang/xiaoj/ordering">
  <main id="xiaoj-ordering-app" class="app-shell">
    <noscript>此介面需要啟用 JavaScript。</noscript>
  </main>
  <script src="/wuchang_core/static/src/xiaoj_ordering/xiaoj_ordering_app.js"></script>
</body>
</html>""" % (html.escape(mode), html.escape(table_ref), html.escape(store_ref))
        return request.make_response(html_body, headers=[("Content-Type", "text/html; charset=utf-8")])

    @http.route("/wuchang/xiaoj/ordering/manifest", type="json", auth="user", csrf=False)
    def xiaoj_ordering_manifest(self, **kw):
        return {
            "state": "XIAOJ_ORDERING_BROWSER_APP_READY",
            "route": "/wuchang/xiaoj/ordering",
            "pages": [
                "staff_pos",
                "counter_service_touch",
                "customer_service",
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
