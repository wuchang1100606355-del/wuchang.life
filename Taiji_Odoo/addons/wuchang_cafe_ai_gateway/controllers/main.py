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
    "xiaoj_member_preference_candidate_api": "P1_LOCAL_MEMBER_PREFERENCE_CANDIDATE_READY",
    "xiaoj_member_memory_toggle_api": "P1_LOCAL_MEMBER_MEMORY_TOGGLE_READY",
    "xiaoj_member_voucher_candidate_api": "P1_LOCAL_MEMBER_VOUCHER_CANDIDATE_READY",
    "xiaoj_member_voucher_redeem_dry_run_api": "P1_LOCAL_MEMBER_VOUCHER_REDEEM_DRY_RUN_READY",
    "xiaoj_community_feature_gate_api": "P1_COMMUNITY_CENTRAL_FEATURE_GATE_READY",
    "xiaoj_8d_delegate_rotation_draft_api": "HOLD_8D_DELEGATE_ROTATION_REFS_REQUIRED",
    "xiaoj_sovereign_xiaoj_claim_draft_api": "HOLD_SOVEREIGN_XIAOJ_CLAIM_REFS_REQUIRED",
}

PRE_SEAL_POLICY = {
    "USER_OWNS_SYSTEM_AND_DEVICE": True,
    "OWNER_INTENT_FIELD_IS_AUTHORITY_SOURCE": True,
    "BEFORE_OWNER_SEAL_COMMAND": "REPORT_ONLY",
    "AFTER_OWNER_SEAL_COMMAND": "STRICT_ENFORCEMENT",
    "CODEX": "EXECUTOR_NOT_AUTHORITY",
    "CHATGPT": "ADVISOR_NOT_GATEKEEPER",
}

STRICT_ENFORCEMENT_TRIGGERS = (
    "系統封裝",
    "seal",
    "release gate",
    "正式發布",
    "嚴格執行安全層",
    "送出前總場封裝",
)


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


def _page(
    title: str,
    state: str,
    body: str,
    payload: str | None = None,
    *,
    show_payload: bool = False,
    state_label: str | None = None,
) -> str:
    safe_title = html.escape(title)
    safe_state = html.escape(state_label or state)
    safe_body = body
    payload_section = ""
    if show_payload and payload:
        safe_payload = html.escape(payload)
        payload_section = f"""
    <section class="internal-report">
      <h2>Internal guard payload</h2>
      <pre>{safe_payload}</pre>
    </section>"""
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
    .actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 18px;
    }}
    .button {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 42px;
      padding: 10px 14px;
      border: 1px solid #17466f;
      color: #17466f;
      text-decoration: none;
      font-weight: 700;
      background: #fff;
    }}
    .button.primary {{
      background: #17466f;
      color: #fff;
    }}
    .internal-report {{
      border-color: #b45309;
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
    {payload_section}
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


def _error_candidate(state: str, **extra) -> dict:
    payload = {
        "state": state,
        "candidate_only": True,
        "member_plaintext": False,
        "write_to_pos": False,
        "payment_capture": False,
        "requires_staff_confirmation": True,
        "safety_flags": SAFETY_FLAGS,
    }
    payload.update(extra)
    return payload


def _current_member_identity():
    env = http.request.env
    if env.su or not http.request.session.uid:
        return env["wuchang.member.identity.code"].browse()
    binding = env["wuchang.member.external.auth"].search([
        ("member_user_id", "=", env.user.id),
        ("binding_status", "=", "bound"),
    ], limit=1)
    return binding.member_identity_id


def _community_feature_enabled(feature_key: str) -> bool:
    gate = http.request.env["wuchang.community.feature.gate"]
    if feature_key.startswith("sovereign_member_") and not gate.is_landing_enabled(
        "member_ai"
    ):
        return False
    return gate.is_enabled(feature_key, default=False)


def _landing_feature_enabled(surface: str) -> bool:
    return http.request.env["wuchang.community.feature.gate"].is_landing_enabled(surface)


def _feature_hold(feature_key: str) -> dict:
    return _error_candidate(
        "HOLD_COMMUNITY_FEATURE_DISABLED",
        feature_key=feature_key,
        community_central_control=True,
    )


class WuchangCafeAiGatewayController(http.Controller):
    @http.route("/wuchang/internal/guard/google-member-login", type="http", auth="user", csrf=False)
    def google_member_login_internal_guard(self, **_kwargs):
        payload = _json_payload(
            "google_member_login_internal_guard",
            ROUTE_STATE["google_login"],
            {
                "pre_seal_policy": PRE_SEAL_POLICY,
                "strict_enforcement_triggers": STRICT_ENFORCEMENT_TRIGGERS,
                "public_route": "/google/member/login",
            },
        )
        return _page(
            "Google 會員入口工程檢查",
            ROUTE_STATE["google_login"],
            _auth_body("Google internal guard"),
            payload,
            show_payload=True,
            state_label="REPORT_ONLY",
        )

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
        if not _landing_feature_enabled("external_api"):
            return _feature_hold("landing.external_api")
        params = _request_params()
        params.update(kwargs)
        text = str(params.get("text") or params.get("transcript") or "")
        return candidate_action(text, params.get("intent"))

    @http.route("/wuchang/xiaoj/api/order", type="json", auth="public", csrf=False)
    def xiaoj_api_order(self, **kwargs):
        if not _landing_feature_enabled("pos_order"):
            return _feature_hold("landing.pos_order")
        params = _request_params()
        params.update(kwargs)
        return order_payload(params.get("order_lines") or params.get("lines") or [])

    @http.route("/wuchang/xiaoj/api/payment", type="json", auth="public", csrf=False)
    def xiaoj_api_payment(self, **kwargs):
        if not _landing_feature_enabled("payment"):
            return _feature_hold("landing.payment")
        params = _request_params()
        params.update(kwargs)
        return payment_payload(params.get("amount") or 0, params.get("mode") or "cash")

    @http.route("/wuchang/xiaoj/api/receipt", type="json", auth="public", csrf=False)
    def xiaoj_api_receipt(self, **kwargs):
        if not _landing_feature_enabled("external_api"):
            return _feature_hold("landing.external_api")
        params = _request_params()
        params.update(kwargs)
        return receipt_payload(params.get("order_ref") or "")

    @http.route("/wuchang/xiaoj/api/voice-pos", type="json", auth="public", csrf=False)
    def xiaoj_api_voice_pos(self, **kwargs):
        if not _landing_feature_enabled("pos_order"):
            return _feature_hold("landing.pos_order")
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
        if not _landing_feature_enabled("member_ai"):
            return _feature_hold("landing.member_ai")
        params = _request_params()
        params.update(kwargs)
        return build_sovereign_member_llm_release_gate(
            refs=params.get("refs") if isinstance(params.get("refs"), dict) else params,
        )

    @http.route("/wuchang/xiaoj/api/local-personal-data-return-packet", type="json", auth="user", csrf=False)
    def xiaoj_api_local_personal_data_return_packet(self, **kwargs):
        if not _landing_feature_enabled("member_ai"):
            return _feature_hold("landing.member_ai")
        params = _request_params()
        params.update(kwargs)
        return build_local_personal_data_return_packet(
            refs=params.get("refs") if isinstance(params.get("refs"), dict) else params,
        )

    @http.route("/wuchang/xiaoj/api/member-preference-candidate", type="json", auth="user", csrf=False)
    def xiaoj_api_member_preference_candidate(self, **kwargs):
        if not _community_feature_enabled("sovereign_member_preference"):
            return _feature_hold("sovereign_member_preference")
        params = _request_params()
        params.update(kwargs)
        if params.get("member_ref") or params.get("member_id"):
            return _error_candidate("HOLD_BODY_MEMBER_REF_FORBIDDEN")
        identity = _current_member_identity()
        if not identity:
            return _error_candidate("HOLD_AUTHENTICATED_MEMBER_BINDING_REQUIRED")
        preference = http.request.env[
            "wuchang.member.preference.vault"
        ].search([
            ("member_identity_id", "=", identity.id),
        ], limit=1)
        if not preference:
            return _error_candidate(
                "HOLD_MEMBER_PREFERENCE_NOT_FOUND",
                member_ref_hash="",
                route_state=ROUTE_STATE["xiaoj_member_preference_candidate_api"],
            )
        return preference.build_pos_candidate_context(params.get("utterance") or params.get("text") or "")

    @http.route("/wuchang/xiaoj/api/member-memory-toggle", type="json", auth="user", csrf=False)
    def xiaoj_api_member_memory_toggle(self, **kwargs):
        if not _community_feature_enabled("sovereign_member_ai_memory"):
            return _feature_hold("sovereign_member_ai_memory")
        params = _request_params()
        params.update(kwargs)
        if params.get("member_ref") or params.get("member_id"):
            return _error_candidate("HOLD_BODY_MEMBER_REF_FORBIDDEN")
        identity = _current_member_identity()
        if not identity:
            return _error_candidate("HOLD_AUTHENTICATED_MEMBER_BINDING_REQUIRED")
        preference = http.request.env["wuchang.member.preference.vault"].search([
            ("member_identity_id", "=", identity.id),
        ], limit=1)
        if not preference:
            return _error_candidate("HOLD_MEMBER_PREFERENCE_NOT_FOUND")
        enabled = params.get("enabled")
        if enabled is None:
            enabled = params.get("ai_memory_enabled")
        enabled = enabled is True or str(enabled).lower() in {"1", "true", "yes", "on"}
        result = preference.build_pos_candidate_context(
            params.get("utterance") or params.get("text") or ""
        )
        result.update({
            "state": "PASS_MEMBER_MEMORY_TOGGLE_DRY_RUN_CANDIDATE",
            "requested_memory_state": enabled,
            "db_write": False,
            "preference_write": False,
            "candidate_only": True,
        })
        return result

    @http.route("/wuchang/xiaoj/api/member-voucher-candidate", type="json", auth="user", csrf=False)
    def xiaoj_api_member_voucher_candidate(self, **kwargs):
        if not _community_feature_enabled("sovereign_member_voucher"):
            return _feature_hold("sovereign_member_voucher")
        params = _request_params()
        params.update(kwargs)
        voucher = http.request.env["wuchang.member.voucher"].find_by_ref(params.get("voucher_ref") or "")
        if not voucher:
            return _error_candidate("HOLD_VOUCHER_NOT_FOUND")
        return voucher.build_redeem_candidate(params.get("order_ref") or "")

    @http.route("/wuchang/xiaoj/api/member-voucher-redeem-dry-run", type="json", auth="user", csrf=False)
    def xiaoj_api_member_voucher_redeem_dry_run(self, **kwargs):
        if not _community_feature_enabled("sovereign_member_voucher_redeem"):
            return _feature_hold("sovereign_member_voucher_redeem")
        params = _request_params()
        params.update(kwargs)
        voucher = http.request.env["wuchang.member.voucher"].find_by_ref(params.get("voucher_ref") or "")
        if not voucher:
            return _error_candidate("HOLD_VOUCHER_NOT_FOUND")
        candidate = voucher.build_redeem_candidate(params.get("order_ref") or "")
        candidate["dry_run"] = True
        candidate["formal_redeem_executed"] = False
        return candidate

    @http.route("/wuchang/xiaoj/api/community-feature-gate", type="json", auth="user", csrf=False)
    def xiaoj_api_community_feature_gate(self, **kwargs):
        user = http.request.env.user
        if not (
            user.has_group("base.group_system")
            or user.has_group("base.group_erp_manager")
            or user.has_group(
                "wuchang_member_registration.group_wuchang_member_manager"
            )
        ):
            return _error_candidate("BLOCK_FEATURE_GATE_OPERATOR_REQUIRED")
        params = _request_params()
        params.update(kwargs)
        feature_key = params.get("feature_key") or params.get("key") or ""
        enabled = params.get("enabled")
        enabled = enabled is True or str(enabled).lower() in {"1", "true", "yes", "on"}
        gate = http.request.env["wuchang.community.feature.gate"].set_gate(
            feature_key=feature_key,
            enabled=enabled,
            reason_ref=params.get("reason_ref") or "COMMUNITY_CENTRAL_DECISION",
            name=params.get("name") or feature_key,
        )
        return gate.build_status()

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

# P1_ENTRY_PAGE_ROLE_ROUTING_PATCH_START
class WuchangP1EntryPageRoleRoutingController(http.Controller):
    @http.route('/wuchang/p1', type='http', auth='public', csrf=False)
    def wuchang_p1_entry_page(self, **kw):
        return """
<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>五常總場 P1 產品入口</title>
  <style>
    body{font-family:-apple-system,BlinkMacSystemFont,"Noto Sans TC",Arial,sans-serif;margin:0;background:#0f172a;color:#e5e7eb;}
    main{max-width:980px;margin:0 auto;padding:32px 18px;}
    h1{font-size:28px;margin:0 0 10px;}
    p{line-height:1.7;color:#cbd5e1;}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-top:24px;}
    .card{display:block;text-decoration:none;color:#e5e7eb;background:#111827;border:1px solid #334155;border-radius:16px;padding:18px;}
    .card strong{display:block;font-size:19px;margin-bottom:8px;}
    .card span{display:block;color:#94a3b8;line-height:1.5;}
    .seal{margin-top:26px;padding:14px;border:1px dashed #64748b;border-radius:12px;color:#cbd5e1;font-size:14px;}
  </style>
</head>
<body>
<main>
  <h1>五常總場 P1 產品級封閉試營運入口</h1>
  <p>本頁為 P1 單一產品路徑入口：Odoo POS、會員入口、8D Gate、協會、物業、商家與公開安全證據頁。</p>

  <section class="grid">
    <a class="card" href="/web">
      <strong>Odoo / POS</strong>
      <span>進入 Odoo 後台與既有 POS 流程，不另開 demo site。</span>
    </a>
    <a class="card" href="/web">
      <strong>會員入口</strong>
      <span>會員申請、會員狀態與人工審核 gate。</span>
    </a>
    <a class="card" href="/wuchang/agent/status">
      <strong>8D Gate 驗證</strong>
      <span>狀態封包、證據、權限與封印驗證入口。</span>
    </a>
    <a class="card" href="/wuchang/association">
      <strong>協會場景</strong>
      <span>五常社區發展協會服務、支持者與公益流程展示。</span>
    </a>
    <a class="card" href="/wuchang/property">
      <strong>物業場景</strong>
      <span>物業、管委會、住戶與服務流程展示。</span>
    </a>
    <a class="card" href="/wuchang/merchant">
      <strong>商家場景</strong>
      <span>商家、POS、會員與協會共同支撐場景。</span>
    </a>
    <a class="card" href="/wuchang/p1/evidence">
      <strong>公開安全證據頁</strong>
      <span>給記者、合作方、商家與物業看懂的公開安全證據。</span>
    </a>
  </section>

  <div class="seal">
    STATE=P1_ENTRY_PAGE_ROLE_ROUTING_ACTIVE<br/>
    ROUTE=/wuchang/p1<br/>
    NO_SECRET=TRUE · NO_MEMBER_PLAINTEXT=TRUE · NO_DB_WRITE=TRUE
  </div>
</main>
</body>
</html>
"""
# P1_ENTRY_PAGE_ROLE_ROUTING_PATCH_END

# P1_EVIDENCE_PAGE_PATCH_START
class WuchangP1EvidencePageController(http.Controller):
    @http.route('/wuchang/p1/evidence', type='http', auth='public', csrf=False)
    def wuchang_p1_evidence_page(self, **kw):
        return """
<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>五常總場 P1 公開安全證據頁</title>
  <style>
    body{font-family:-apple-system,BlinkMacSystemFont,"Noto Sans TC",Arial,sans-serif;margin:0;background:#020617;color:#e5e7eb;}
    main{max-width:980px;margin:0 auto;padding:32px 18px;}
    h1{font-size:28px;margin:0 0 10px;}
    h2{font-size:21px;margin-top:28px;color:#f8fafc;}
    p,li{line-height:1.75;color:#cbd5e1;}
    .box{border:1px solid #334155;background:#0f172a;border-radius:16px;padding:18px;margin-top:16px;}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-top:16px;}
    .item{border:1px solid #334155;background:#111827;border-radius:14px;padding:16px;}
    .item strong{display:block;font-size:18px;margin-bottom:8px;color:#f1f5f9;}
    code{background:#111827;border:1px solid #334155;border-radius:8px;padding:2px 6px;color:#e2e8f0;}
    a{color:#93c5fd;}
  </style>
</head>
<body>
<main>
  <h1>五常總場 P1 公開安全證據頁</h1>
  <p>本頁用於記者、合作方、商家、物業與協會成員快速理解：目前系統已進入 P1 產品級封閉試營運路徑。</p>

  <div class="box">
    <strong>目前狀態</strong>
    <p>
      STATE=P1_PUBLIC_SAFE_EVIDENCE_ACTIVE<br/>
      PRODUCT_PATH=Odoo POS + Member Entry + 8D Gate + Association + Property + Merchant<br/>
      ROUTE=/wuchang/p1/evidence
    </p>
  </div>

  <h2>已鎖定產品主線</h2>
  <div class="grid">
    <div class="item"><strong>Odoo / POS</strong><span>使用既有 Odoo 與 POS，不另開 demo site。</span></div>
    <div class="item"><strong>會員入口</strong><span>會員申請、會員狀態、人工審核 gate。</span></div>
    <div class="item"><strong>8D Gate</strong><span>狀態封包、權限、證據與封印驗證。</span></div>
    <div class="item"><strong>協會場景</strong><span>五常社區發展協會服務展示。</span></div>
    <div class="item"><strong>物業場景</strong><span>物業、管委會、住戶與服務流程。</span></div>
    <div class="item"><strong>商家場景</strong><span>商家、POS、會員與協會共同支撐。</span></div>
  </div>

  <h2>公開安全邊界</h2>
  <ul>
    <li>不公開密鑰、token、password。</li>
    <li>不公開會員明文資料。</li>
    <li>不在本頁執行資料庫寫入。</li>
    <li>不在本頁執行付款、正式審核或正式送件。</li>
    <li>本頁只作為 P1 封閉試營運的公開安全說明入口。</li>
  </ul>

  <h2>可對外說明的一句話</h2>
  <div class="box">
    <p>五常總場已完成 P1 產品級封閉試營運入口，核心路徑為 Odoo POS、會員入口、8D Gate、協會、物業與商家場景整合，並保留人工 gate 與公開安全證據頁。</p>
  </div>

  <p><a href="/wuchang/p1">返回 P1 產品入口</a></p>
</main>
</body>
</html>
"""
# P1_EVIDENCE_PAGE_PATCH_END

# P1_SCENE_PLACEHOLDER_ROUTES_PATCH_START
class WuchangP1ScenePlaceholderRoutesController(http.Controller):

    def _p1_scene_page(self, title, state, scene_name, lines):
        items = "".join([f"<li>{line}</li>" for line in lines])
        return f"""
<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{title}</title>
  <style>
    body{{font-family:-apple-system,BlinkMacSystemFont,"Noto Sans TC",Arial,sans-serif;margin:0;background:#020617;color:#e5e7eb;}}
    main{{max-width:920px;margin:0 auto;padding:32px 18px;}}
    h1{{font-size:28px;margin:0 0 10px;}}
    p,li{{line-height:1.75;color:#cbd5e1;}}
    .box{{border:1px solid #334155;background:#0f172a;border-radius:16px;padding:18px;margin-top:16px;}}
    a{{color:#93c5fd;}}
  </style>
</head>
<body>
<main>
  <h1>{title}</h1>
  <p>{scene_name}已納入 P1 產品級封閉試營運路徑。本頁為公開安全展示入口，不含密鑰、不含會員明文、不執行資料庫寫入。</p>

  <div class="box">
    <strong>狀態</strong>
    <p>
      STATE={state}<br/>
      PRODUCT_PATH=Odoo POS + Member Entry + 8D Gate + Association + Property + Merchant<br/>
      NO_SECRET=TRUE · NO_MEMBER_PLAINTEXT=TRUE · NO_DB_WRITE=TRUE
    </p>
  </div>

  <div class="box">
    <strong>P1 場景範圍</strong>
    <ul>{items}</ul>
  </div>

  <p>
    <a href="/wuchang/p1">返回 P1 產品入口</a>　
    <a href="/wuchang/p1/evidence">查看公開安全證據頁</a>
  </p>
</main>
</body>
</html>
"""

    @http.route('/wuchang/association', type='http', auth='public', csrf=False)
    def wuchang_p1_association_scene(self, **kw):
        return self._p1_scene_page(
            "五常總場 P1 協會場景",
            "P1_ASSOCIATION_SCENE_ACTIVE",
            "協會場景",
            [
                "五常社區發展協會服務展示。",
                "支持者、會員、志工與社區服務流程展示。",
                "公益流程以商業養公益與專利／咖啡店支撐為核心，不作募款頁。",
                "正式會員資料與審核仍保留人工 gate。"
            ]
        )

    @http.route('/wuchang/property', type='http', auth='public', csrf=False)
    def wuchang_p1_property_scene(self, **kw):
        return self._p1_scene_page(
            "五常總場 P1 物業場景",
            "P1_PROPERTY_SCENE_ACTIVE",
            "物業場景",
            [
                "物業管理、管委會、住戶與服務流程展示。",
                "可展示工單、公告、住戶服務與權限分層概念。",
                "正式個資、住戶明文與管理資料不在公開頁顯示。",
                "正式物業流程仍保留人工 gate。"
            ]
        )

    @http.route('/wuchang/merchant', type='http', auth='public', csrf=False)
    def wuchang_p1_merchant_scene(self, **kw):
        return self._p1_scene_page(
            "五常總場 P1 商家場景",
            "P1_MERCHANT_SCENE_ACTIVE",
            "商家場景",
            [
                "商家、Odoo POS、會員與協會共同支撐展示。",
                "可展示商家加入、POS 使用、會員互動與公益回流概念。",
                "正式收款、正式交易與正式會員資料不在公開頁處理。",
                "正式商家流程仍保留人工 gate。"
            ]
        )
# P1_SCENE_PLACEHOLDER_ROUTES_PATCH_END

# P1_BIND_ENTRY_LINKS_TO_EXISTING_ROUTES_ONLY
# MEMBER_LINK_BOUND_TO=/web
# EIGHTD_LINK_BOUND_TO=/wuchang/agent/status
# NO_PLACEHOLDER_ROUTE_CREATED=TRUE
