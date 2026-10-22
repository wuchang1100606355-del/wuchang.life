"""Odoo-bound, fail-closed routes for the preserved three-style UI suite."""

from __future__ import annotations

import json

from odoo import http
from odoo.addons.wuchang_core.controllers.xiaoj_ordering_app_controller import (
    XiaoJOrderingAppController,
)
from odoo.http import request
from odoo.tools import file_open

from ..services.live_odoo_projection import (
    binding_receipt,
    menu_projection,
    price_projection,
    staff_pos_payload,
)
from ..services.ordering_integration_adapter import build_adapter_plan


SUITES = {"a": "靛藍科技", "b": "暖米咖啡", "c": "墨韻典藏"}
ROLES = {"staff_pos", "online_ordering", "in_store_self_service"}
ROLE_FILES = {
    "online_ordering": "{suite}_online.html",
    "in_store_self_service": "{suite}_kiosk.html",
    "staff_pos": "pos_standalone.html",
}


def _safe_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def _read_original_ui(filename):
    path = f"wuchang_ordering_ui_suite/static/src/original_ui/{filename}"
    with file_open(path, "r") as handle:
        return handle.read()


def _insert_after_script(html, marker, script):
    marker_at = html.find(marker)
    if marker_at < 0:
        raise ValueError("ORIGINAL_UI_DATA_MARKER_MISSING")
    end_at = html.find("</script>", marker_at)
    if end_at < 0:
        raise ValueError("ORIGINAL_UI_DATA_SCRIPT_UNCLOSED")
    end_at += len("</script>")
    return html[:end_at] + script + html[end_at:]


def _render_bound_ui(suite, role, projection):
    filename = ROLE_FILES[role].format(suite=suite)
    html = _read_original_ui(filename)
    # Preserve the generated source files byte-for-byte while preventing their
    # superseded Company 3 labels from being presented by the bound runtime.
    html = html.replace("重新總店 Company 3", "重新總店／上品食品行（POS 待核定）")
    html = html.replace("上品食品行 Company 3", "重新總店／上品食品行（POS 待核定）")
    binding = {
        "state": projection["state"],
        "suite": suite,
        "suite_name": SUITES[suite],
        "role": role,
        "store_ref": projection["store_ref"],
        "product_count": projection["product_count"],
        "projection_receipt_ref": projection["projection_receipt_ref"],
        "observed_at": projection["observed_at"],
        "formal_effect": False,
    }
    status = (
        '<div id="wuchang-odoo-live-binding" role="status" '
        'style="position:fixed;right:12px;bottom:12px;z-index:9999;padding:9px 13px;'
        'border-radius:999px;background:#123;box-shadow:0 5px 20px #0005;color:white;'
        'font:700 12px/1.3 system-ui">Odoo Company 3 / exact POS · 64/64 唯讀接合</div>'
    )
    if role == "staff_pos":
        payload = staff_pos_payload(projection)
        script = (
            "<script>Object.assign(window.LIAOGUO_MENU," + _safe_json(payload) + ");"
            "window.__WUCHANG_ODOO_BINDING__=" + _safe_json(binding) + ";"
            f"try{{localStorage.setItem('liaoguo_suite',JSON.stringify('{suite}'));}}catch(_e){{}}"
            f"window.location.hash='#/pos/{suite}';</script>"
        )
        html = _insert_after_script(html, "window.LIAOGUO_MENU=", script)
    else:
        payload = {
            "menu_id": projection["menu_id"],
            "source_sha256": projection["source_sha256"],
            "categories": projection["categories"],
            "products": projection["products"],
            "groups": projection["groups"],
        }
        script = (
            "<script>Object.assign(window.__MENU__," + _safe_json(payload) + ");"
            "window.__WUCHANG_ODOO_BINDING__=" + _safe_json(binding) + ";</script>"
        )
        html = _insert_after_script(html, "window.__MENU__=", script)
    body_at = html.find("<body")
    body_end = html.find(">", body_at)
    if body_at < 0 or body_end < 0:
        raise ValueError("ORIGINAL_UI_BODY_MISSING")
    return html[: body_end + 1] + status + html[body_end + 1 :]


def _no_effect(operation, payload):
    binding = binding_receipt(request.env)
    if binding.get("state") != "PASS_EXACT_CHONGXIN_BINDING":
        return {**binding, "formal_effect": False}
    pos_config_id = binding["binding"]["pos_config_id"]
    return build_adapter_plan(
        operation,
        company_id=3,
        pos_config_id=pos_config_id,
        expected_pos_config_id=pos_config_id,
        role="staff_pos" if operation in {"cancel", "member_lookup"} else "online_ordering",
        payload=payload,
    )


class WuchangOrderingAdapterController(http.Controller):
    @http.route(
        "/wuchang/ordering/xiaoj-hdmi",
        type="http",
        auth="user",
        website=True,
        sitemap=False,
        csrf=False,
    )
    def xiaoj_hdmi(self, **_kwargs):
        """Dedicated alias to the existing wuchang_core VRM app and its 8D gate."""
        return XiaoJOrderingAppController().xiaoj_ordering_app(mode="av_ai_menu_display")

    @http.route(
        "/wuchang/ordering/menu",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def menu(self, **payload):
        del payload
        return menu_projection(request.env)

    @http.route(
        "/wuchang/ordering/price",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def price(self, **payload):
        forbidden = {
            "amount_total", "grand_total", "price", "price_unit", "total",
            "member_id", "phone", "voucher_ref", "payment_token",
        }
        hits = sorted(forbidden.intersection(payload))
        if hits:
            return {
                "state": "HOLD_CLIENT_AUTHORITY_OR_SENSITIVE_FIELD_FORBIDDEN",
                "forbidden_keys": hits,
                "formal_effect": False,
            }
        return price_projection(request.env, payload)

    @http.route(
        "/wuchang/ordering/ui/<string:suite>/<string:role>",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def ordering_ui(self, suite, role, **_kwargs):
        if suite not in SUITES or role not in ROLES:
            return request.not_found()
        projection = menu_projection(request.env)
        if projection.get("state") != "PASS_ODOO_MENU_PROJECTION":
            body = (
                "<!doctype html><meta charset='utf-8'><title>Odoo 接合暫停</title>"
                "<main style='max-width:760px;margin:10vh auto;font:16px/1.7 system-ui'>"
                "<h1>Odoo 接合暫停</h1><p>未取得精確 64/64 QuickClick 映射，介面已失敗閉鎖。</p>"
                f"<pre>{_safe_json(projection)}</pre></main>"
            )
            return request.make_response(body, status=503, headers=[("Content-Type", "text/html; charset=utf-8")])
        body = _render_bound_ui(suite, role, projection)
        return request.make_response(
            body,
            headers=[
                ("Content-Type", "text/html; charset=utf-8"),
                ("X-Wuchang-Odoo-Binding", "company-3-pos-unresolved-readonly"),
                ("X-Wuchang-Projection-Receipt", projection["projection_receipt_ref"]),
            ],
        )

    @http.route("/wuchang/ordering/draft", type="json", auth="public", methods=["POST"], csrf=False)
    def draft(self, **payload):
        return _no_effect("draft", payload)

    @http.route("/wuchang/ordering/cancel", type="json", auth="user", methods=["POST"], csrf=False)
    def cancel(self, **payload):
        return _no_effect("cancel", payload)

    @http.route("/wuchang/ordering/member/lookup", type="json", auth="user", methods=["POST"], csrf=False)
    def member_lookup(self, **payload):
        return _no_effect("member_lookup", payload)

    @http.route("/wuchang/ordering/voucher/confirm", type="json", auth="user", methods=["POST"], csrf=False)
    def voucher_confirm(self, **payload):
        return _no_effect("voucher_confirm", payload)
