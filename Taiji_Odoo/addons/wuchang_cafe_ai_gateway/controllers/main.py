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
    merchant_capability_payload,
    formal_release_status_payload,
    lineworks_notify_payload,
    staff_voice_pos_payload,
)
from ..services.lineworks_connector import (
    build_lineworks_execution_envelope_export,
    build_lineworks_send_preflight,
    execute_lineworks_send_envelope,
)
from ..services.lineworks_activation import build_lineworks_runtime_activation_packet
from ..services.lineworks_handoff import build_lineworks_operator_handoff_pack
from ..services.lineworks_release_refs import build_lineworks_release_refs_draft
from ..services.lineworks_runtime_resolver import build_lineworks_runtime_resolver_contract
from ..services.line_official_account_config import build_line_official_account_config_candidate
from ..services.line_official_account_webhook import build_line_official_account_webhook_candidate
from ..services.eightd_system_assembly import build_eightd_system_assembly_status
from ..services.merchant_productization_readiness import build_merchant_productization_readiness
from ..services.total_product_ref_collection import (
    build_total_product_ref_collection_draft,
    build_total_product_ref_collection_input_template,
)
from ..services.total_product_handoff import build_total_product_operator_handoff
from ..services.total_product_operator_bundle import build_total_product_operator_bundle_payload
from ..services.llm_cost_saving_model_router import build_llm_cost_saving_model_router_candidate
from ..services.productization_console import (
    build_8d_delegate_rotation_draft,
    build_local_personal_data_return_packet,
    build_sovereign_member_llm_release_gate,
    build_sovereign_xiaoj_claim_draft,
    build_xiaoj_total_product_console_status,
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
    "xiaoj_lineworks_notify_api": "HOLD_LINEWORKS_SEND_RELEASE_REQUIRED",
    "xiaoj_lineworks_send_preflight_api": "HOLD_LINEWORKS_SEND_PREFLIGHT",
    "xiaoj_lineworks_release_refs_draft_api": "HOLD_LINEWORKS_RELEASE_REFS_DRAFT",
    "xiaoj_lineworks_execution_envelope_api": "HOLD_LINEWORKS_EXECUTION_ENVELOPE",
    "xiaoj_lineworks_runtime_activation_api": "HOLD_LINEWORKS_RUNTIME_ACTIVATION",
    "xiaoj_lineworks_runtime_dry_run_api": "HOLD_LINEWORKS_RUNTIME_DRY_RUN",
    "xiaoj_lineworks_operator_handoff_api": "HOLD_LINEWORKS_OPERATOR_HANDOFF",
    "xiaoj_lineworks_runtime_resolver_contract_api": "HOLD_LINEWORKS_RUNTIME_RESOLVER_CONTRACT",
    "xiaoj_line_official_account_config_candidate_api": "HOLD_LINE_OFFICIAL_ACCOUNT_CONFIG_CANDIDATE",
    "xiaoj_line_official_account_webhook_candidate_api": "HOLD_LINE_OFFICIAL_ACCOUNT_WEBHOOK_CANDIDATE",
    "xiaoj_8d_system_assembly_status_api": "PASS_XIAOJ_8D_TOTAL_SYSTEM_ASSEMBLY_P1_READY_FOR_HUMAN_REVIEW",
    "xiaoj_merchant_productization_readiness_api": "HOLD_XIAOJ_MERCHANT_PRODUCTIZATION_READINESS",
    "xiaoj_total_product_ref_collection_api": "HOLD_TOTAL_PRODUCT_REF_COLLECTION_DRAFT",
    "xiaoj_total_product_ref_template_api": "TEMPLATE_REQUIRES_HUMAN_FILLED_REFS",
    "xiaoj_total_product_operator_handoff_api": "PASS_XIAOJ_TOTAL_PRODUCT_OPERATOR_HANDOFF_READY",
    "xiaoj_total_product_operator_bundle_api": "PASS_XIAOJ_TOTAL_PRODUCT_OPERATOR_BUNDLE_READY",
    "xiaoj_llm_cost_saving_model_router_api": "HOLD_MODEL_ROUTE_REFS_REQUIRED",
    "xiaoj_total_product_console_status_api": "HOLD_P2_RELEASE_REFS_REQUIRED",
    "xiaoj_member_llm_release_gate_api": "HOLD_MEMBER_LLM_RELEASE_REFS_REQUIRED",
    "xiaoj_local_personal_data_return_packet_api": "HOLD_ENCRYPTED_LOCAL_VAULT_REF_REQUIRED",
    "xiaoj_8d_delegate_rotation_draft_api": "HOLD_8D_DELEGATE_ROTATION_REFS_REQUIRED",
    "xiaoj_sovereign_xiaoj_claim_draft_api": "HOLD_SOVEREIGN_XIAOJ_CLAIM_REFS_REQUIRED",
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
    "staff_voice_pos_operation",
    "sovereign_member_personalization",
    "merchant_social_candidate",
    "property_community_candidate",
    "humanoid_service_candidate",
    "lineworks_notify_candidate",
    "merchant_capability_map",
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


def _request_headers() -> dict:
    request = getattr(http, "request", None)
    if request is None:
        return {}
    httprequest = getattr(request, "httprequest", None)
    headers = getattr(httprequest, "headers", None)
    if headers is None:
        return {}
    return dict(headers)


def _lineworks_refs_from_params(params: dict) -> dict:
    refs = dict(params.get("release_refs")) if isinstance(params.get("release_refs"), dict) else {}
    if isinstance(params.get("lineworks_send"), dict):
        lineworks_send = params.get("lineworks_send")
    elif isinstance(refs.get("lineworks_send"), dict):
        lineworks_send = refs.get("lineworks_send")
    else:
        lineworks_send = {key: value for key, value in refs.items() if key != "connector_refs"}
    result = {"lineworks_send": lineworks_send} if lineworks_send else {}
    if isinstance(params.get("connector_refs"), dict):
        result["connector_refs"] = params.get("connector_refs")
    elif isinstance(refs.get("connector_refs"), dict):
        result["connector_refs"] = refs.get("connector_refs")
    return result


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

    @http.route("/wuchang/xiaoj/api/lineworks-notify", type="json", auth="user", csrf=False)
    def xiaoj_api_lineworks_notify(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        return lineworks_notify_payload(
            params.get("message") or params.get("text") or "",
            params.get("target_ref") or params.get("user_ref") or "",
            params.get("channel") or "member_service",
            params.get("actor_ref") or "",
        )

    @http.route("/wuchang/xiaoj/api/lineworks-send-preflight", type="json", auth="user", csrf=False)
    def xiaoj_api_lineworks_send_preflight(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        candidate = params.get("candidate_payload") if isinstance(params.get("candidate_payload"), dict) else lineworks_notify_payload(
            params.get("message") or params.get("text") or "",
            params.get("target_ref") or params.get("user_ref") or "",
            params.get("channel") or "member_service",
            params.get("actor_ref") or "",
        )
        # Red-team boundary: never trust a caller-supplied release_status_payload.
        # The route always recomputes release state from verified release refs.
        release_status = formal_release_status_payload(params.get("release_refs") if isinstance(params.get("release_refs"), dict) else {})
        connector_refs = params.get("connector_refs") if isinstance(params.get("connector_refs"), dict) else {}
        return build_lineworks_send_preflight(candidate, release_status, connector_refs)

    @http.route("/wuchang/xiaoj/api/lineworks-release-refs-draft", type="json", auth="user", csrf=False)
    def xiaoj_api_lineworks_release_refs_draft(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        release_refs = params.get("lineworks_send") if isinstance(params.get("lineworks_send"), dict) else params.get("release_refs")
        if not isinstance(release_refs, dict):
            release_refs = {}
        connector_refs = params.get("connector_refs") if isinstance(params.get("connector_refs"), dict) else {}
        return build_lineworks_release_refs_draft(
            release_refs=release_refs,
            connector_refs=connector_refs,
            allow_verified=params.get("allow_verified") is True,
        )

    @http.route("/wuchang/xiaoj/api/lineworks-execution-envelope", type="json", auth="user", csrf=False)
    def xiaoj_api_lineworks_execution_envelope(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        candidate = params.get("candidate_payload") if isinstance(params.get("candidate_payload"), dict) else lineworks_notify_payload(
            params.get("message") or params.get("text") or "",
            params.get("target_ref") or params.get("user_ref") or "",
            params.get("channel") or "member_service",
            params.get("actor_ref") or "",
        )
        # Red-team boundary: never trust a caller-supplied release_status_payload.
        # The route always recomputes release state from verified release refs.
        release_status = formal_release_status_payload(params.get("release_refs") if isinstance(params.get("release_refs"), dict) else {})
        connector_refs = params.get("connector_refs") if isinstance(params.get("connector_refs"), dict) else {}
        return build_lineworks_execution_envelope_export(
            candidate,
            release_status,
            connector_refs,
            refs_path="api:/wuchang/xiaoj/api/lineworks-execution-envelope:release_refs",
        )

    @http.route("/wuchang/xiaoj/api/lineworks-runtime-activation-draft", type="json", auth="user", csrf=False)
    def xiaoj_api_lineworks_runtime_activation_draft(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        return build_lineworks_runtime_activation_packet(
            operator_ref=params.get("operator_ref") or "",
            execution_envelope_hash=params.get("execution_envelope_hash") or "",
            candidate_packet_hash=params.get("candidate_packet_hash") or "",
            release_packet_hash=params.get("release_packet_hash") or "",
            reason_ref=params.get("reason_ref") or "REASON_REF_LINEWORKS_RUNTIME_DRY_RUN",
            confirm_human_activation=params.get("confirm_human_activation") is True,
        )

    @http.route("/wuchang/xiaoj/api/lineworks-runtime-dry-run", type="json", auth="user", csrf=False)
    def xiaoj_api_lineworks_runtime_dry_run(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        envelope = params.get("execution_envelope") if isinstance(params.get("execution_envelope"), dict) else {}
        if not envelope:
            candidate = params.get("candidate_payload") if isinstance(params.get("candidate_payload"), dict) else lineworks_notify_payload(
                params.get("message") or params.get("text") or "",
                params.get("target_ref") or params.get("user_ref") or "",
                params.get("channel") or "member_service",
                params.get("actor_ref") or "",
            )
            release_status = formal_release_status_payload(params.get("release_refs") if isinstance(params.get("release_refs"), dict) else {})
            connector_refs = params.get("connector_refs") if isinstance(params.get("connector_refs"), dict) else {}
            envelope = build_lineworks_execution_envelope_export(
                candidate,
                release_status,
                connector_refs,
                refs_path="api:/wuchang/xiaoj/api/lineworks-runtime-dry-run:release_refs",
            )
        runtime_activation = params.get("runtime_activation") if isinstance(params.get("runtime_activation"), dict) else {
            "human_activation": bool(params.get("activation_packet_hash") and params.get("operator_ref")),
            "release_gate": "lineworks_send",
            "activation_packet_hash": params.get("activation_packet_hash") or "",
            "operator_ref": params.get("operator_ref") or "",
        }
        # Red-team boundary: this API never honors client enable_external_call.
        # It performs dry-run readiness only and cannot send LINE WORKS messages.
        return execute_lineworks_send_envelope(
            envelope,
            runtime_activation=runtime_activation,
            enable_external_call=False,
        )

    @http.route("/wuchang/xiaoj/api/lineworks-operator-handoff", type="json", auth="user", csrf=False)
    def xiaoj_api_lineworks_operator_handoff(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        refs = _lineworks_refs_from_params(params)
        # Red-team boundary: the handoff API aggregates operator evidence only.
        # It never honors client enable_external_call and cannot send LINE WORKS messages.
        return build_lineworks_operator_handoff_pack(
            refs=refs,
            refs_path="api:/wuchang/xiaoj/api/lineworks-operator-handoff:release_refs",
            message=params.get("message") or params.get("text") or "",
            target_ref=params.get("target_ref") or params.get("user_ref") or "",
            actor_ref=params.get("actor_ref") or "",
            operator_ref=params.get("operator_ref") or "OPERATOR_REF_HANDOFF_CHECK",
            channel=params.get("channel") or "member_service",
            confirm_human_activation=params.get("confirm_human_activation") is True,
        )

    @http.route("/wuchang/xiaoj/api/lineworks-runtime-resolver-contract", type="json", auth="user", csrf=False)
    def xiaoj_api_lineworks_runtime_resolver_contract(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        refs = _lineworks_refs_from_params(params)
        bindings = (
            params.get("runtime_resolver_bindings")
            if isinstance(params.get("runtime_resolver_bindings"), dict)
            else params.get("resolver_bindings")
        )
        if not isinstance(bindings, dict):
            bindings = {}
        return build_lineworks_runtime_resolver_contract(
            connector_refs=refs.get("connector_refs", {}),
            resolver_bindings=bindings,
            allow_verified=params.get("allow_verified") is True,
        )

    @http.route("/wuchang/xiaoj/api/line-official-account-config-candidate", type="json", auth="user", csrf=False)
    def xiaoj_api_line_official_account_config_candidate(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        refs = params.get("refs") if isinstance(params.get("refs"), dict) else {}
        return build_line_official_account_config_candidate(
            params.get("intent") or params.get("text") or "",
            refs=refs,
            style_ref=params.get("style_ref") or "STYLE_REF_XIAOJ_WARM_PRECISE",
            operator_ref=params.get("operator_ref") or "OPERATOR_REF_LINE_OFFICIAL_ACCOUNT_REVIEW",
        )

    @http.route("/wuchang/xiaoj/api/line-official-account-webhook-candidate", type="json", auth="user", csrf=False)
    def xiaoj_api_line_official_account_webhook_candidate(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        return build_line_official_account_webhook_candidate(
            webhook_payload=params.get("webhook_payload") if isinstance(params.get("webhook_payload"), dict) else params,
            headers=params.get("headers") if isinstance(params.get("headers"), dict) else {},
            verification=params.get("verification") if isinstance(params.get("verification"), dict) else {},
        )

    @http.route("/wuchang/xiaoj/line-official-account/webhook", type="json", auth="public", csrf=False)
    def xiaoj_line_official_account_webhook(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        # P1 webhook shell: never reads channel secret and never replies to LINE.
        # Production signature validation must be supplied as a verified ref by a release-gated runtime.
        return build_line_official_account_webhook_candidate(
            webhook_payload=params,
            headers=_request_headers(),
            verification={},
        )

    @http.route("/wuchang/xiaoj/api/merchant-capabilities", type="json", auth="public", csrf=False)
    def xiaoj_api_merchant_capabilities(self, **_kwargs):
        return merchant_capability_payload()

    @http.route("/wuchang/xiaoj/api/formal-release-status", type="json", auth="user", csrf=False)
    def xiaoj_api_formal_release_status(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        refs = params.get("release_refs") if isinstance(params.get("release_refs"), dict) else params
        return formal_release_status_payload(refs)

    @http.route("/wuchang/xiaoj/api/merchant-productization-readiness", type="json", auth="user", csrf=False)
    def xiaoj_api_merchant_productization_readiness(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        return build_merchant_productization_readiness(
            formal_release_refs=params.get("formal_release_refs") if isinstance(params.get("formal_release_refs"), dict) else {},
            lineworks_refs=params.get("lineworks_refs") if isinstance(params.get("lineworks_refs"), dict) else {},
            line_official_account_refs=(
                params.get("line_official_account_refs")
                if isinstance(params.get("line_official_account_refs"), dict)
                else {}
            ),
            line_official_account_intent=params.get("line_official_account_intent") or "",
            lineworks_probe=params.get("lineworks_probe") if isinstance(params.get("lineworks_probe"), dict) else {},
            input_ref="api:/wuchang/xiaoj/api/merchant-productization-readiness",
        )

    @http.route("/wuchang/xiaoj/api/8d-system-assembly-status", type="json", auth="user", csrf=False)
    def xiaoj_api_8d_system_assembly_status(self, **_kwargs):
        return build_eightd_system_assembly_status()

    @http.route("/wuchang/xiaoj/api/total-product-ref-collection", type="json", auth="user", csrf=False)
    def xiaoj_api_total_product_ref_collection(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        refs = params.get("refs") if isinstance(params.get("refs"), dict) else params
        return build_total_product_ref_collection_draft(
            refs,
            allow_verified=params.get("allow_verified") is True,
        )

    @http.route("/wuchang/xiaoj/api/total-product-ref-template", type="json", auth="user", csrf=False)
    def xiaoj_api_total_product_ref_template(self, **_kwargs):
        return build_total_product_ref_collection_input_template()

    @http.route("/wuchang/xiaoj/api/total-product-operator-handoff", type="json", auth="user", csrf=False)
    def xiaoj_api_total_product_operator_handoff(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        return build_total_product_operator_handoff(
            formal_release_refs=params.get("formal_release_refs") if isinstance(params.get("formal_release_refs"), dict) else {},
            lineworks_refs=params.get("lineworks_refs") if isinstance(params.get("lineworks_refs"), dict) else {},
            line_official_account_refs=(
                params.get("line_official_account_refs")
                if isinstance(params.get("line_official_account_refs"), dict)
                else {}
            ),
            line_official_account_intent=params.get("line_official_account_intent") or "",
            lineworks_probe=params.get("lineworks_probe") if isinstance(params.get("lineworks_probe"), dict) else {},
            input_ref="api:/wuchang/xiaoj/api/total-product-operator-handoff",
        )

    @http.route("/wuchang/xiaoj/api/total-product-operator-bundle", type="json", auth="user", csrf=False)
    def xiaoj_api_total_product_operator_bundle(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        refs = params.get("refs") if isinstance(params.get("refs"), dict) else None
        return build_total_product_operator_bundle_payload(
            refs=refs,
            allow_verified=params.get("allow_verified") is True,
            input_ref="api:/wuchang/xiaoj/api/total-product-operator-bundle:refs",
            bundle_ref="api:/wuchang/xiaoj/api/total-product-operator-bundle",
        )

    @http.route("/wuchang/xiaoj/api/llm-cost-saving-model-router", type="json", auth="user", csrf=False)
    def xiaoj_api_llm_cost_saving_model_router(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        return build_llm_cost_saving_model_router_candidate(
            task_intent=params.get("task_intent") or params.get("intent") or params.get("text") or "",
            task_surface=params.get("task_surface") or params.get("surface") or "",
            refs=params.get("refs") if isinstance(params.get("refs"), dict) else {},
            allow_external_candidate=params.get("allow_external_candidate") is True,
        )

    @http.route("/wuchang/xiaoj/api/total-product-console-status", type="json", auth="user", csrf=False)
    def xiaoj_api_total_product_console_status(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        return build_xiaoj_total_product_console_status(
            refs=params.get("refs") if isinstance(params.get("refs"), dict) else {},
            actor_ref=params.get("actor_ref") or "ACTOR_REF_TOTAL_PRODUCT_CONSOLE",
        )

    @http.route("/wuchang/xiaoj/api/member-llm-release-gate", type="json", auth="user", csrf=False)
    def xiaoj_api_member_llm_release_gate(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        return build_sovereign_member_llm_release_gate(
            refs=params.get("refs") if isinstance(params.get("refs"), dict) else params,
        )

    @http.route("/wuchang/xiaoj/api/local-personal-data-return-packet", type="json", auth="user", csrf=False)
    def xiaoj_api_local_personal_data_return_packet(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        return build_local_personal_data_return_packet(
            refs=params.get("refs") if isinstance(params.get("refs"), dict) else params,
        )

    @http.route("/wuchang/xiaoj/api/8d-delegate-rotation-draft", type="json", auth="user", csrf=False)
    def xiaoj_api_8d_delegate_rotation_draft(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        return build_8d_delegate_rotation_draft(
            refs=params.get("refs") if isinstance(params.get("refs"), dict) else params,
        )

    @http.route("/wuchang/xiaoj/api/sovereign-xiaoj-claim-draft", type="json", auth="user", csrf=False)
    def xiaoj_api_sovereign_xiaoj_claim_draft(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        return build_sovereign_xiaoj_claim_draft(
            refs=params.get("refs") if isinstance(params.get("refs"), dict) else params,
        )
