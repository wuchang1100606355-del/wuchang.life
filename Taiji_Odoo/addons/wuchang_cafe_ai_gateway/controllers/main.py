"""HTTP route shells for XiaoJ cafe auth and transaction flows.

These routes intentionally avoid OAuth secret reads, member plaintext access,
POS order creation, payment capture, and Odoo DB writes. They provide controlled
non-404 entrypoints that can be wired to real services after a separate runtime
release.
"""

from __future__ import annotations

import html
import json

from odoo import http

from ..services.p1_intent_engine import (
    SAFETY_FLAGS,
    SUPPORTED_INTENTS,
    base_payload as _api_payload,
    candidate_action,
    order_payload,
    payment_payload,
    receipt_payload,
    staff_voice_pos_payload,
)


ROUTE_STATE = {
    "line_login": "HOLD_AUTH_PROVIDER_CONFIG_REQUIRED",
    "line_callback": "HOLD_AUTH_PROVIDER_CONFIG_REQUIRED",
    "google_login": "HOLD_AUTH_PROVIDER_CONFIG_REQUIRED",
    "google_welcome": "HOLD_AUTH_PROVIDER_CONFIG_REQUIRED",
    "member_register_start": "HOLD_MEMBER_REGISTRATION_GATE",
    "xiaoj_ordering": "P1_TRANSACTION_CAPABLE_SHELL",
    "xiaoj_order": "HOLD_RUNTIME_POS_ORDER_RELEASE_REQUIRED",
    "xiaoj_payment": "HOLD_RUNTIME_PAYMENT_RELEASE_REQUIRED",
    "xiaoj_receipt": "HOLD_RUNTIME_POS_RECEIPT_REQUIRED",
    "xiaoj_intent_api": "P1_MULTI_INTENT_API_SHELL",
    "xiaoj_order_api": "HOLD_RUNTIME_POS_ORDER_RELEASE_REQUIRED",
    "xiaoj_payment_api": "HOLD_RUNTIME_PAYMENT_RELEASE_REQUIRED",
    "xiaoj_receipt_api": "HOLD_RUNTIME_POS_RECEIPT_REQUIRED",
    "xiaoj_voice_pos_api": "P1_STAFF_VOICE_POS_API_SHELL",
}


SUPPORTED_INTENTS = {
    "menu_lookup",
    "order_candidate",
    "pos_order_create",
    "payment_candidate",
    "receipt_candidate",
    "translate_assist",
    "manager_price_change",
    "return_candidate",
    "category_move",
    "live_notice",
    "cash_advance_ref",
    "member_register",
    "loyalty_return",
}


def _json_payload(intent: str, state: str, extra: dict | None = None) -> str:
    payload = {
        "intent": intent,
        "state": state,
        "runtime_ready": False,
        "requires_human_release": True,
        "safety_flags": SAFETY_FLAGS,
    }
    if extra:
        payload.update(extra)
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _request_params() -> dict:
    params = {}
    request = getattr(http, "request", None)
    if request is not None:
        params.update(getattr(request, "params", {}) or {})
        json_request = getattr(request, "jsonrequest", None)
        if isinstance(json_request, dict):
            params.update(json_request)
    return params


def _page(title: str, state: str, body: str, payload: str) -> str:
    safe_title = html.escape(title)
    safe_state = html.escape(state)
    safe_body = body
    safe_payload = html.escape(payload)
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <style>
    body {{
      margin: 0;
      background: #f7f9fb;
      color: #1f2933;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      max-width: 980px;
      margin: 0 auto;
      padding: 32px 20px;
    }}
    .bar {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
      border-bottom: 1px solid #d9e1e8;
      padding-bottom: 18px;
      margin-bottom: 24px;
    }}
    .state {{
      padding: 8px 12px;
      border: 1px solid #d9e1e8;
      background: #fff7e6;
      color: #8a5a00;
      font-weight: 700;
    }}
    section {{
      background: #fff;
      border: 1px solid #d9e1e8;
      padding: 18px;
      margin-bottom: 16px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      border-bottom: 1px solid #d9e1e8;
      padding: 10px;
      text-align: left;
      vertical-align: top;
    }}
    pre {{
      overflow: auto;
      background: #20252b;
      color: #f7f9fb;
      padding: 14px;
    }}
  </style>
</head>
<body>
  <main>
    <div class="bar">
      <div>
        <p>聊國咖啡館重新總店 · XiaoJ P1</p>
        <h1>{safe_title}</h1>
      </div>
      <span class="state">{safe_state}</span>
    </div>
    {safe_body}
    <section>
      <h2>Route payload</h2>
      <pre>{safe_payload}</pre>
    </section>
  </main>
</body>
</html>"""


def _auth_body(provider: str) -> str:
    return f"""
    <section>
      <h2>{html.escape(provider)} 註冊登入入口</h2>
      <table>
        <tr><th>目前狀態</th><td>受控 route shell 已建立；正式 OAuth redirect 仍需 provider 設定與人審 runtime release。</td></tr>
        <tr><th>安全邊界</th><td>不讀 token、不讀 secret、不讀會員明文、不呼叫外部 API。</td></tr>
        <tr><th>下一步</th><td>接入 provider config ref，通過 D8 guard 後才啟用正式登入。</td></tr>
      </table>
    </section>
    """


def _ordering_body() -> str:
    return """
    <section>
      <h2>可交易 / 可付款 / 可下單流程</h2>
      <table>
        <tr><th>點餐</th><td>使用真實菜單 source lock 後建立訂單草稿。</td></tr>
        <tr><th>付款</th><td>支援現金櫃台確認；外部金流需另行授權。</td></tr>
        <tr><th>下單</th><td>需要 POS session 與人審 release 後才可寫入 Odoo POS。</td></tr>
        <tr><th>收據</th><td>等待 Odoo POS 正式 order id 後產生。</td></tr>
      </table>
    </section>
    """


class WuchangCafeAiGatewayController(http.Controller):
    @http.route("/line/login", type="http", auth="public", csrf=False)
    def line_login(self, **_kwargs):
        payload = _json_payload("line_login", ROUTE_STATE["line_login"])
        return _page("LINE 註冊登入", ROUTE_STATE["line_login"], _auth_body("LINE"), payload)

    @http.route("/line/callback", type="http", auth="public", csrf=False)
    def line_callback(self, **_kwargs):
        payload = _json_payload("line_callback", ROUTE_STATE["line_callback"])
        return _page("LINE Callback", ROUTE_STATE["line_callback"], _auth_body("LINE Callback"), payload)

    @http.route("/google/member/login", type="http", auth="public", csrf=False)
    def google_member_login(self, **_kwargs):
        payload = _json_payload("google_member_login", ROUTE_STATE["google_login"])
        return _page("Google 會員登入", ROUTE_STATE["google_login"], _auth_body("Google"), payload)

    @http.route("/google/member/welcome", type="http", auth="public", csrf=False)
    def google_member_welcome(self, **_kwargs):
        payload = _json_payload("google_member_welcome", ROUTE_STATE["google_welcome"])
        return _page("Google 會員歡迎頁", ROUTE_STATE["google_welcome"], _auth_body("Google Welcome"), payload)

    @http.route("/wuchang/member/register/start", type="http", auth="public", csrf=False)
    def member_register_start(self, **_kwargs):
        payload = _json_payload(
            "member_register_start",
            ROUTE_STATE["member_register_start"],
            {"member_plaintext_required": False},
        )
        body = """
        <section>
          <h2>會員註冊起點</h2>
          <table>
            <tr><th>識別</th><td>使用 member_ref / packet_ref，不讀會員明文。</td></tr>
            <tr><th>渠道</th><td>LINE / Google / 店內 QR 均需通過 8D packet gate。</td></tr>
            <tr><th>狀態</th><td>等待正式 auth provider 與 association governance release。</td></tr>
          </table>
        </section>
        """
        return _page("會員註冊起點", ROUTE_STATE["member_register_start"], body, payload)

    @http.route("/wuchang/xiaoj/ordering", type="http", auth="public", csrf=False)
    def xiaoj_ordering(self, **_kwargs):
        payload = _json_payload("xiaoj_ordering", ROUTE_STATE["xiaoj_ordering"])
        return _page("小J影音點餐", ROUTE_STATE["xiaoj_ordering"], _ordering_body(), payload)

    @http.route("/wuchang/xiaoj/order", type="http", auth="public", csrf=False)
    def xiaoj_order(self, **_kwargs):
        payload = _json_payload("pos_order_create", ROUTE_STATE["xiaoj_order"])
        return _page("小J下單", ROUTE_STATE["xiaoj_order"], _ordering_body(), payload)

    @http.route("/wuchang/xiaoj/payment", type="http", auth="public", csrf=False)
    def xiaoj_payment(self, **_kwargs):
        payload = _json_payload("payment_candidate", ROUTE_STATE["xiaoj_payment"])
        return _page("小J付款", ROUTE_STATE["xiaoj_payment"], _ordering_body(), payload)

    @http.route("/wuchang/xiaoj/receipt", type="http", auth="public", csrf=False)
    def xiaoj_receipt(self, **_kwargs):
        payload = _json_payload("receipt_candidate", ROUTE_STATE["xiaoj_receipt"])
        return _page("小J收據", ROUTE_STATE["xiaoj_receipt"], _ordering_body(), payload)

    @http.route("/wuchang/xiaoj/api/intent", type="json", auth="public", csrf=False)
    def xiaoj_api_intent(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        text = str(params.get("text") or params.get("transcript") or "")
        return candidate_action(text, params.get("intent"))

    @http.route("/wuchang/xiaoj/api/order", type="json", auth="public", csrf=False)
    def xiaoj_api_order(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        return order_payload(params.get("order_lines") or params.get("lines") or [])

    @http.route("/wuchang/xiaoj/api/payment", type="json", auth="public", csrf=False)
    def xiaoj_api_payment(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        return payment_payload(params.get("amount") or 0, params.get("mode") or "cash")

    @http.route("/wuchang/xiaoj/api/receipt", type="json", auth="public", csrf=False)
    def xiaoj_api_receipt(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        return receipt_payload(params.get("order_ref") or "")

    @http.route("/wuchang/xiaoj/api/voice-pos", type="json", auth="public", csrf=False)
    def xiaoj_api_voice_pos(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        return staff_voice_pos_payload(
            params.get("transcript") or params.get("text") or "",
            params.get("staff_ref") or "",
            params.get("language") or "zh-Hant",
        )
