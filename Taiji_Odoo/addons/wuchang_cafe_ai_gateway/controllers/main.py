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
from ..services.merchant_capability_service import (
    build_group_member_field_application_entry,
    build_group_member_intent_field_questionnaire,
    build_group_member_total_field_product_candidate,
    build_sovereign_ai_multi_account_governance_candidate,
    build_merchant_capability_catalog,
    build_xiaoj_core_supply_contract,
    plan_distributed_device_admission,
    plan_founder_base_template_application,
    plan_group_member_total_field_application,
    plan_local_trade_secret_request,
    plan_merchant_action,
    plan_sovereign_ai_multi_account_binding,
    plan_xiaoj_field_projection,
)
from ..services.storefront_23 import (
    build_storefront_flair,
    build_storefront_response,
    confirm_storefront_preview,
)


ROUTE_STATE = {
    "line_login": "HOLD_AUTH_PROVIDER_CONFIG_REQUIRED",
    "line_callback": "HOLD_AUTH_PROVIDER_CONFIG_REQUIRED",
    "google_login": "HOLD_AUTH_PROVIDER_CONFIG_REQUIRED",
    "google_welcome": "HOLD_AUTH_PROVIDER_CONFIG_REQUIRED",
    "member_register_start": "HOLD_MEMBER_REGISTRATION_GATE",
    "xiaoj_ordering": "商店介面啟用 · 正式下單待菜單對齊",
    "xiaoj_display": "小J 顯示投影啟用 · 不具交易權限",
    "xiaoj_order": "HOLD_RUNTIME_POS_ORDER_RELEASE_REQUIRED",
    "xiaoj_payment": "HOLD_RUNTIME_PAYMENT_RELEASE_REQUIRED",
    "xiaoj_receipt": "HOLD_RUNTIME_POS_RECEIPT_REQUIRED",
    "xiaoj_intent_api": "P1_MULTI_INTENT_API_SHELL",
    "xiaoj_order_api": "HOLD_RUNTIME_POS_ORDER_RELEASE_REQUIRED",
    "xiaoj_payment_api": "HOLD_RUNTIME_PAYMENT_RELEASE_REQUIRED",
    "xiaoj_receipt_api": "HOLD_RUNTIME_POS_RECEIPT_REQUIRED",
    "xiaoj_voice_pos_api": "P1_STAFF_VOICE_POS_API_SHELL",
    "xiaoj_merchant_capabilities_api": "CANDIDATE_FUNCTIONAL_EQUIVALENCE",
    "xiaoj_merchant_action_candidate_api": "CANDIDATE_ACTION_PLANNER",
    "xiaoj_core_capabilities_api": "CANDIDATE_CORE_SUPPLY_CONTRACT",
    "xiaoj_field_projection_candidate_api": "CANDIDATE_FIELD_PROJECTION_PLANNER",
    "xiaoj_local_secret_request_candidate_api": "CANDIDATE_LOCAL_SECRET_REQUEST_PLANNER",
    "xiaoj_device_admission_candidate_api": "CANDIDATE_FOUNDER_GATED_DEVICE_ADMISSION",
    "xiaoj_template_application_candidate_api": "CANDIDATE_FOUNDER_BASE_DEVICE_TEMPLATE_APPLICATION",
    "xiaoj_group_member_field_application_entry_api": "CANDIDATE_XIAOJ_ADDON_VISIBLE_LINK",
    "xiaoj_group_member_field_application_candidate_api": "CANDIDATE_PENDING_FOUNDER_RATIFICATION",
    "xiaoj_group_member_intent_field_questionnaire_api": "CANDIDATE_REAL_WORLD_USABLE_QUESTIONNAIRE",
    "xiaoj_group_member_field_product_page": "CANDIDATE_PRODUCT_LANDING_NO_EFFECT",
    "xiaoj_group_member_field_product_candidate_api": "CANDIDATE_PRODUCT_LANDING_NO_EFFECT",
    "xiaoj_sovereign_ai_account_binding_candidate_api": "CANDIDATE_MULTI_ACCOUNT_MERGE_PENDING_VERIFICATION",
    "xiaoj_sovereign_ai_account_governance_candidate_api": "HOLD_GOVERNANCE_RULE_GAPS",
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


def _page(
    title: str,
    state: str,
    body: str,
    payload: str,
    page_class: str = "",
) -> str:
    safe_title = html.escape(title)
    safe_state = html.escape(state)
    safe_body = body
    safe_payload = html.escape(payload)
    safe_page_class = html.escape(page_class, quote=True)
    payload_section = (
        f'<details class="route-payload"><summary>開發者候選資料</summary><pre>{safe_payload}</pre></details>'
        if page_class == "field-product"
        else f'<section><h2>路由封包（開發者資料）</h2><pre>{safe_payload}</pre></section>'
    )
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
<body class="{safe_page_class}">
  <main>
    <div class="bar">
      <div>
        <p>上品聊國咖啡館重新總店 · 小J 8DADI</p>
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
    <style>
      body.cafe-store { background:#130d09; color:#f8f0e7; }
      body.cafe-store main { max-width:1220px; padding:18px clamp(14px,4vw,46px) 72px; }
      body.cafe-store .bar { border:1px solid rgba(255,237,213,.14); border-radius:18px; padding:13px 16px; background:rgba(38,23,14,.78); backdrop-filter:blur(18px); }
      body.cafe-store .bar p { margin:0; color:#e4b981; font-size:.78rem; letter-spacing:.1em; }
      body.cafe-store .bar h1 { margin:4px 0 0; font-size:clamp(1rem,2vw,1.25rem); }
      body.cafe-store .state { border-color:rgba(111,221,174,.35); border-radius:999px; background:rgba(111,221,174,.1); color:#9df2c9; font-size:.72rem; }
      body.cafe-store main > section:last-child { border:1px solid rgba(255,237,213,.14); border-radius:18px; background:#1b120d; }
      .storefront { --cream:#fff4e6; --muted:#cbb8a5; --coffee:#8e4f2a; --copper:#e38d4f; --mint:#75e0b1; --line:rgba(255,237,213,.15); overflow:hidden; border:1px solid var(--line); border-radius:32px; background:linear-gradient(145deg,#160e0a,#25150d 54%,#120b08); box-shadow:0 38px 110px rgba(0,0,0,.5); }
      .storefront * { box-sizing:border-box; }
      .storefront section { margin:0; padding:clamp(30px,6vw,76px) clamp(20px,6vw,76px); border:0; border-bottom:1px solid var(--line); background:transparent; }
      .store-hero { min-height:620px; display:grid; grid-template-columns:minmax(0,1.12fr) minmax(320px,.88fr); align-items:center; gap:clamp(34px,7vw,86px); background:radial-gradient(circle at 78% 30%,rgba(227,141,79,.18),transparent 31rem),radial-gradient(circle at 8% 5%,rgba(117,224,177,.11),transparent 30rem); }
      .store-kicker { margin:0 0 16px; color:#f1b16e; font-size:.76rem; font-weight:850; letter-spacing:.16em; }
      .store-hero h2 { margin:0; max-width:790px; color:var(--cream); font-size:clamp(3rem,7vw,6.8rem); line-height:.91; letter-spacing:-.065em; text-wrap:balance; }
      .store-hero h2 span { display:block; color:transparent; background:linear-gradient(100deg,#ffd9a8,#ef9658 48%,#79e5b5); background-clip:text; -webkit-background-clip:text; }
      .store-lead { max-width:660px; margin:25px 0 0; color:var(--muted); font-size:clamp(1rem,1.7vw,1.2rem); line-height:1.8; }
      .hero-tags { display:flex; flex-wrap:wrap; gap:9px; margin-top:27px; }
      .hero-tags span { padding:8px 11px; border:1px solid var(--line); border-radius:999px; color:#ead8c5; font-size:.78rem; background:rgba(255,255,255,.025); }
      .warm-state { display:inline-flex; align-items:center; gap:8px; margin-top:14px; padding:8px 11px; border-radius:999px; color:#bff7dc; background:rgba(117,224,177,.09); font-size:.76rem; }
      .warm-state::before { content:""; width:8px; height:8px; border-radius:50%; background:var(--mint); box-shadow:0 0 14px var(--mint); animation:blink 1.2s infinite; }
      .avatar-stage { position:relative; min-height:450px; display:grid; place-items:center; isolation:isolate; }
      .avatar-stage::before { content:""; position:absolute; width:88%; aspect-ratio:1; border-radius:50%; background:radial-gradient(circle,rgba(237,144,79,.22),transparent 62%); filter:blur(18px); }
      .avatar-orbit { position:absolute; width:84%; aspect-ratio:1; border:1px solid rgba(255,196,135,.3); border-radius:50%; transform:rotateX(66deg) rotateZ(12deg); animation:store-orbit 14s linear infinite; }
      .avatar-orbit.second { width:66%; border-color:rgba(117,224,177,.34); transform:rotateY(68deg) rotateZ(28deg); animation-direction:reverse; animation-duration:19s; }
      .avatar { position:relative; width:min(430px,78vw); aspect-ratio:16/10; overflow:hidden; border:1px solid rgba(255,240,222,.3); border-radius:30px; background:#0f0a07; box-shadow:0 0 70px rgba(227,141,79,.3); animation:avatar-float 5.2s ease-in-out infinite; }
      .avatar img { width:100%; height:100%; object-fit:cover; object-position:left center; transform:scale(1.035); transition:filter .25s ease,transform .4s ease; }
      .avatar::after { content:"小J"; position:absolute; left:18px; bottom:16px; padding:6px 12px; border:1px solid rgba(255,255,255,.22); border-radius:999px; color:#fff8ef; background:rgba(19,10,6,.68); backdrop-filter:blur(12px); font-weight:950; letter-spacing:.12em; }
      .avatar-stage.is-speaking .avatar img { filter:brightness(1.08) saturate(1.08); transform:scale(1.055) translateY(-2px); }
      .avatar-stage.is-listening .avatar { box-shadow:0 0 90px rgba(117,224,177,.55); }
      .avatar-stage[data-emotion="welcoming"] .avatar { box-shadow:0 0 92px rgba(237,155,94,.48); }
      .avatar-stage[data-emotion="attentive"] .avatar { box-shadow:0 0 92px rgba(108,188,255,.5); }
      .avatar-stage[data-emotion="cheerful"] .avatar { box-shadow:0 0 104px rgba(255,224,139,.5); }
      .avatar-stage[data-emotion="reassuring"] .avatar { box-shadow:0 0 72px rgba(117,224,177,.34); }
      .avatar-caption { position:absolute; right:0; bottom:6%; max-width:280px; padding:14px 16px; border:1px solid var(--line); border-radius:18px 18px 4px 18px; color:#f5e8dc; background:rgba(32,17,10,.88); backdrop-filter:blur(16px); }
      .display-toolbar { display:flex; flex-wrap:wrap; gap:9px; margin-top:18px; }
      .display-toolbar a,.outfit-pick { min-height:44px; display:inline-grid; place-items:center; padding:9px 13px; border:1px solid var(--line); border-radius:999px; color:#f8eadc; background:rgba(255,255,255,.045); font:inherit; font-size:.8rem; text-decoration:none; cursor:pointer; }
      .outfit-pick.is-active { border-color:rgba(117,224,177,.7); color:#baf6d8; background:rgba(117,224,177,.11); }
      @keyframes store-orbit { to { rotate:1turn; } } @keyframes avatar-float { 50% { transform:translateY(-10px) rotate(.5deg); } } @keyframes blink { 0%,46%,50%,100% { scale:1 1; } 48% { scale:1 .08; } }
      .intent-zone { display:grid; grid-template-columns:.78fr 1.22fr; gap:clamp(25px,5vw,60px); align-items:start; }
      .section-title h3 { margin:5px 0 15px; color:var(--cream); font-size:clamp(2.2rem,4.5vw,4.5rem); letter-spacing:-.045em; line-height:1; }
      .section-title p { margin:0; color:var(--muted); line-height:1.75; }
      .intent-card { padding:20px; border:1px solid var(--line); border-radius:25px; background:rgba(255,250,242,.05); box-shadow:0 24px 60px rgba(0,0,0,.2); }
      .intent-card textarea { width:100%; min-height:132px; resize:vertical; padding:17px; border:1px solid rgba(255,236,211,.2); border-radius:17px; outline:none; color:#fff8ef; background:rgba(7,5,4,.5); font:inherit; font-size:1.05rem; line-height:1.6; }
      .intent-card textarea:focus { border-color:var(--copper); box-shadow:0 0 0 4px rgba(227,141,79,.12); }
      .intent-actions { display:flex; flex-wrap:wrap; gap:10px; margin-top:12px; }
      .send-intent,.voice-intent,.quick-intent,.menu-pick { appearance:none; border:0; cursor:pointer; font:inherit; }
      .send-intent { padding:13px 19px; border-radius:999px; color:#241108; background:linear-gradient(120deg,#ffd09a,#e88749); font-weight:900; }
      .voice-intent { padding:13px 16px; border:1px solid var(--line); border-radius:999px; color:#f9e8d8; background:rgba(255,255,255,.05); }
      .quick-row { display:flex; gap:8px; overflow:auto; margin-top:14px; padding-bottom:3px; }
      .quick-intent { flex:0 0 auto; min-height:44px; padding:9px 12px; border:1px solid var(--line); border-radius:999px; color:#d8c7b8; background:rgba(255,255,255,.03); }
      .xiaoj-result { margin-top:17px; padding:17px; border-left:3px solid var(--mint); border-radius:5px 17px 17px 5px; background:rgba(117,224,177,.08); }
      .xiaoj-result[hidden] { display:none; }
      .result-state { display:inline-flex; margin-bottom:10px; padding:5px 9px; border-radius:999px; color:#a4f2cc; background:rgba(117,224,177,.1); font-size:.75rem; }
      .result-speech { margin:0; font-size:1.06rem; line-height:1.7; }
      .order-preview { margin:13px 0 0; padding:0; list-style:none; }
      .order-preview li { display:flex; justify-content:space-between; gap:12px; padding:8px 0; border-top:1px solid var(--line); color:#e7d7c8; }
      .receipt { margin-top:12px; color:#bcaa99; }
      .receipt pre { max-height:260px; font-size:.74rem; white-space:pre-wrap; }
      .touch-confirm { display:grid; gap:9px; margin-top:15px; padding:14px; border:1px solid rgba(255,209,166,.28); border-radius:18px; background:rgba(227,141,79,.09); }
      .touch-confirm[hidden] { display:none; }
      .touch-confirm button { min-height:68px; border:0; border-radius:16px; color:#241108; background:linear-gradient(120deg,#ffe0ba,#f09a5d); font:inherit; font-size:1.08rem; font-weight:950; cursor:pointer; touch-action:manipulation; }
      .touch-confirm .readback-order { color:#f9e8d8; background:rgba(255,255,255,.07); border:1px solid var(--line); }
      .touch-confirm button:disabled { cursor:not-allowed; filter:saturate(.25); opacity:.65; }
      .touch-confirm small { color:#cbb8a5; line-height:1.55; }
      .menu-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; margin-top:28px; }
      .menu-pick { min-height:150px; padding:19px; border:1px solid var(--line); border-radius:22px; text-align:left; color:#f9ecdf; background:linear-gradient(145deg,rgba(255,255,255,.07),rgba(255,255,255,.02)); transition:.2s ease; }
      .menu-pick:hover { translate:0 -4px; border-color:rgba(227,141,79,.6); }
      .menu-pick small { display:block; color:#e5ad77; }.menu-pick strong { display:block; margin:20px 0 5px; font-size:1.15rem; }.menu-pick span { color:#cfbdad; }
      .source-note { margin:18px 0 0; color:#9f8c7c; font-size:.78rem; line-height:1.65; }
      .initiative { background:radial-gradient(circle at 18% 30%,rgba(117,224,177,.12),transparent 28rem)!important; }
      .initiative-grid { display:grid; grid-template-columns:.86fr 1.14fr; gap:clamp(30px,6vw,78px); align-items:center; }
      .node-field { position:relative; min-height:420px; display:grid; place-items:center; }
      .node-core { z-index:2; width:148px; aspect-ratio:1; display:grid; place-items:center; border-radius:50%; color:#10271d; background:radial-gradient(circle at 33% 25%,#effff7,#75e0b1 48%,#25815d); box-shadow:0 0 60px rgba(117,224,177,.28); font-weight:950; text-align:center; }
      .node-path { position:absolute; width:72%; height:72%; border:1px dashed rgba(117,224,177,.33); border-radius:50%; animation:store-orbit 30s linear infinite reverse; }
      .node { position:absolute; width:132px; padding:12px; border:1px solid var(--line); border-radius:17px; color:#eddfd2; background:rgba(18,11,8,.88); text-align:center; box-shadow:0 18px 40px rgba(0,0,0,.25); }
      .node b { display:block; color:#ffc38d; }.node small { color:#af9c8b; }.node.n1 { top:2%; left:8%; }.node.n2 { top:5%; right:4%; }.node.n3 { bottom:4%; left:3%; }.node.n4 { right:5%; bottom:3%; }
      .principles { display:grid; gap:10px; margin-top:22px; }
      .principles div { padding:13px 15px; border-left:2px solid var(--mint); background:rgba(255,255,255,.035); color:#d8c8ba; }
      .social-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; margin-top:28px; }
      .social-grid article { padding:20px; border:1px solid var(--line); border-radius:22px; background:rgba(255,255,255,.035); }
      .social-grid strong { display:block; margin-bottom:8px; color:#ffd1a6; font-size:1.08rem; }.social-grid p { margin:0; color:#c6b4a4; line-height:1.65; }
      .store-footer { padding:22px!important; text-align:center; color:#a99584; font-size:.8rem; }
      @media(max-width:820px) { .store-hero,.intent-zone,.initiative-grid { grid-template-columns:1fr; }.store-hero { padding-top:48px!important; }.avatar-stage { min-height:390px; }.menu-grid,.social-grid { grid-template-columns:1fr 1fr; } }
      @media(max-width:520px) { .menu-grid,.social-grid { grid-template-columns:1fr; }.node { width:108px; font-size:.78rem; }.node-core { width:120px; }.storefront section { padding-left:17px; padding-right:17px; } }
      @media(prefers-reduced-motion:reduce) { .avatar,.avatar-orbit,.node-path { animation:none!important; } }
    </style>
    <div class="storefront">
      <section class="store-hero">
        <div>
          <p class="store-kicker">數位設備社區團結行動 × 8DADI</p>
          <h2>一杯咖啡，<span>喚醒整個社區的數位能力。</span></h2>
          <p class="store-lead">上品聊國咖啡館重新總店，讓看似普通的舊電腦在瀏覽器裡承載流暢的影音小J。設備不必變昂貴，能力由總場依意圖聚合。</p>
          <div class="hero-tags"><span>外網中斷仍可服務</span><span>區網優先</span><span>D6 重建契約：CANDIDATE／UNKNOWN</span><span>Odoo 商業介面</span></div>
          <div class="warm-state" data-warm-state>固定迎賓動畫與招呼語可用 · 模型器官：CANDIDATE／UNKNOWN</div>
          <div class="display-toolbar">
            <a href="/wuchang/xiaoj/display" target="_blank" rel="noopener" data-open-display>開啟 HDMI 小J 畫面</a>
            <button class="outfit-pick is-active" type="button" data-xiaoj-outfit="white">白色科技制服</button>
            <button class="outfit-pick" type="button" data-xiaoj-outfit="barista">咖啡師圍裙</button>
            <button class="outfit-pick" type="button" data-xiaoj-outfit="event">深色活動接待服</button>
            <button class="outfit-pick" type="button" data-xiaoj-outfit="community">社區日常服</button>
          </div>
        </div>
        <div class="avatar-stage" data-avatar-stage>
          <div class="avatar-orbit"></div><div class="avatar-orbit second"></div>
          <div class="avatar" aria-label="影音AI店員小J"><img src="/wuchang_cafe_ai_gateway/static/src/img/xiaoj_display_23/xiaoj-white-tech.png" alt="小J 白色科技制服" data-xiaoj-hero-image></div>
          <div class="avatar-caption" data-avatar-caption>嗨，我是小J。舊電腦也能有雲端級的出場方式。</div>
        </div>
      </section>

      <section class="intent-zone" id="xiaoj-ordering">
        <div class="section-title"><p class="store-kicker">自然語言店務入口</p><h3>你說人話，<br/>小J負責對準。</h3><p>語音或文字都可以。點餐內容先變成不可被幽默改寫的結構，再由小J用有溫度的方式覆誦。</p></div>
        <div class="intent-card">
          <form data-store-intent-form>
            <label for="store-intent">告訴小J你想做什麼</label>
            <textarea id="store-intent" required="required" placeholder="例如：小J，我 10 分鐘後到，先看看有沒有位子，幫我準備兩杯拿鐵。"></textarea>
            <div class="intent-actions"><button class="send-intent" type="submit">請小J處理</button><button class="voice-intent" type="button" data-voice-intent>開始語音</button></div>
          </form>
          <div class="quick-row"><button class="quick-intent" type="button" data-quick="我 10 分鐘後到，先看看有沒有位子，幫我準備一杯拿鐵。">十分鐘後到</button><button class="quick-intent" type="button" data-quick="兩杯上品美式咖啡和一份烤貝果。">快速點餐</button><button class="quick-intent" type="button" data-quick="分析咖啡館最近的社群印象與可以改善的地方。">社群分析</button></div>
          <div class="xiaoj-result" data-xiaoj-result hidden><span class="result-state" data-result-state></span><p class="result-speech" data-result-speech></p><ul class="order-preview" data-order-preview></ul><div class="touch-confirm" data-touch-confirm hidden><button class="readback-order" type="button" data-readback-order>播放結帳前語音複誦</button><button type="button" data-confirm-order disabled>我確認以上品項與數量</button><small data-confirm-note>語音與模型不能代替這一次觸控。客人親手確認後，系統才可進入正式送單門。</small></div><details class="receipt"><summary>查看 8DADI 回執</summary><pre data-result-receipt></pre></details></div>
        </div>
      </section>

      <section>
        <div class="section-title"><p class="store-kicker">公開菜單展示</p><h3>小J聽得懂，<br/>也算得清楚。</h3><p>點一下品項即可送入自然語言框。正式庫存、價格與 POS 寫單只接受店內 Odoo 的真實來源。</p></div>
        <div class="menu-grid">
          <button class="menu-pick" type="button" data-menu-intent="一杯上品美式咖啡"><small>義式咖啡</small><strong>上品美式咖啡</strong><span>公開索引價 NT$90</span></button>
          <button class="menu-pick" type="button" data-menu-intent="一杯上品拿鐵咖啡"><small>義式咖啡</small><strong>上品拿鐵咖啡</strong><span>公開索引價 NT$90</span></button>
          <button class="menu-pick" type="button" data-menu-intent="一份烤貝果"><small>輕食</small><strong>烤貝果</strong><span>公開索引價 NT$55</span></button>
          <button class="menu-pick" type="button" data-menu-intent="一杯黃金曼特寧"><small>手沖特級品項</small><strong>黃金曼特寧</strong><span>公開索引價 NT$150</span></button>
          <button class="menu-pick" type="button" data-menu-intent="一杯曼巴混合咖啡"><small>手沖咖啡</small><strong>曼巴混合咖啡</strong><span>公開索引價 NT$135</span></button>
          <button class="menu-pick" type="button" data-menu-intent="一杯精選伯爵紅茶"><small>茶飲</small><strong>精選伯爵紅茶</strong><span>公開索引價 NT$65</span></button>
        </div>
        <p class="source-note">資料狀態：2026-09-03 由公開菜單索引觀測，僅作商店展示。未與店內 Odoo 菜單、庫存、座位狀態重新對齊前，不產生正式訂單或付款效果。</p>
      </section>

      <section class="initiative">
        <div class="initiative-grid">
          <div class="section-title"><p class="store-kicker">數位設備社區團結行動</p><h3>不是淘汰舊設備，<br/>是重新分配能力。</h3><p>每台設備只供應伺服器總場依身分封套允許的器官能力：顯示、收音、播音、運算、索引或店務。D6 只有在目標基座、最小必要差異、引用、座標、重建規則與驗證規則齊備並於目標端重驗時成立。</p><div class="principles"><div>設備所有人明確同意後才登錄</div><div>區網可通時只走區網，VPN 只作備援</div><div>伺服器總場決定路徑；模型只是可替換器官</div><div>離線時保留核心點餐與店務能力</div></div></div>
          <div class="node-field" aria-label="社區數位設備能力場示意"><div class="node-path"></div><div class="node-core">伺服器總場<br/>8DADI</div><div class="node n1"><b>咖啡館舊電腦</b><small>瀏覽器與店務介面</small></div><div class="node n2"><b>MSI 顯示卡</b><small>模型與影音生成器官</small></div><div class="node n3"><b>商米 POS</b><small>語音、收銀與現場器官</small></div><div class="node n4"><b>社區閒置設備</b><small>經同意後供應能力</small></div></div>
        </div>
      </section>

      <section>
        <div class="section-title"><p class="store-kicker">動態上下文 × 雲端盲算候選</p><h3>雲端只取得最小投影，<br/>隱私保證仍待驗證。</h3><p>正典、總場秘密與完整身分封套留在伺服器總場；雲端器官只取得當前工作必要的去識別投影並回傳候選結果。沒有可驗證隱私機制前，狀態固定為 CLOUD_BLIND_COMPUTE_CANDIDATE／UNKNOWN。</p></div>
        <div class="social-grid">
          <article><strong>表頭區 · 不可被模型改寫</strong><p>創辦人意圖、8D 不變條件、身分與權限封套留在總場；模型只能閱讀被允許的投影。</p></article>
          <article><strong>動態窗 · 只載入當前意圖</strong><p>點餐時只喚醒菜單、數量、座位與到店時間；社群分析時才載入公開評論及來源時間。</p></article>
          <article><strong>個人化區 · 伺服器總場治理</strong><p>語氣、偏好與可用設備依身分封套由伺服器總場投影。外部 VM 只可作不含行為明文的候選索引器官，接通前維持 UNKNOWN。</p></article>
        </div>
        <div class="principles"><div>伺服器總場＋商米 POS＋可替換模型器官：形成低延遲店務智能</div><div>社區到處可見的舊電腦：經所有人同意後，分別供應顯示、聲音、索引或運算</div><div>想設計新服務時直接說出意圖：8DADI 求受影響閉包、預覽效果、最後人審後才可寫入</div></div>
      </section>

      <section>
        <div class="section-title"><p class="store-kicker">可追溯的社群洞察</p><h3>聽見社群，<br/>不捏造社群。</h3><p>小J把評論、活動互動與會員回饋分開標記來源與時間，再交給商家決定要改善什麼。</p></div>
        <div class="social-grid"><article><strong>被記住的核心</strong><p>手沖咖啡、價格親民、鄰里聊天與長時間陪伴，是公開評論反覆出現的印象。</p></article><article><strong>可以放大的特色</strong><p>瞬間冷卻手沖、舊豆袋再利用與社會企業敘事，適合變成可體驗的店內內容。</p></article><article><strong>不可假裝知道</strong><p>即時座位、庫存、會員個資與 LINE 互動未接上正式來源前，一律顯示未知。</p></article></div>
      </section>
      <section class="store-footer">上品聊國咖啡館重新總店 · 小J影音AI店務系統 · 8DADI 2.3</section>
    </div>
    <script>
      (() => {
        const form = document.querySelector('[data-store-intent-form]');
        if (!form) return;
        const input = form.querySelector('textarea');
        const result = document.querySelector('[data-xiaoj-result]');
        const resultState = document.querySelector('[data-result-state]');
        const resultSpeech = document.querySelector('[data-result-speech]');
        const orderPreview = document.querySelector('[data-order-preview]');
        const receipt = document.querySelector('[data-result-receipt]');
        const touchConfirm = document.querySelector('[data-touch-confirm]');
        const readbackButton = document.querySelector('[data-readback-order]');
        const confirmButton = document.querySelector('[data-confirm-order]');
        const confirmNote = document.querySelector('[data-confirm-note]');
        const avatar = document.querySelector('[data-avatar-stage]');
        const caption = document.querySelector('[data-avatar-caption]');
        const heroImage = document.querySelector('[data-xiaoj-hero-image]');
        const displayStorageKey = 'wuchang-xiaoj-display-v23';
        const displayAssets = {
          white:'/wuchang_cafe_ai_gateway/static/src/img/xiaoj_display_23/xiaoj-white-tech.png',
          barista:'/wuchang_cafe_ai_gateway/static/src/img/xiaoj_display_23/xiaoj-barista.png',
          event:'/wuchang_cafe_ai_gateway/static/src/img/xiaoj_display_23/xiaoj-event-black.png',
          community:'/wuchang_cafe_ai_gateway/static/src/img/xiaoj_display_23/xiaoj-community-gray.png'
        };
        const emotionByState = {
          idle:'warm', warming:'welcoming', listening:'attentive', thinking:'focused',
          speaking:'warm', confirmed:'cheerful', offline:'reassuring'
        };
        const voiceStyles = {
          warm:{rate:1.00,pitch:1.05}, welcoming:{rate:1.02,pitch:1.08},
          attentive:{rate:.97,pitch:1.01}, focused:{rate:.94,pitch:1.00},
          cheerful:{rate:1.06,pitch:1.12}, reassuring:{rate:.90,pitch:.98},
          clear:{rate:.90,pitch:1.00}
        };
        let displayChannel = null;
        let currentOutfit = 'white';
        let currentIntent = '';
        let currentPreviewRef = '';
        let currentPayload = null;
        try { if ('BroadcastChannel' in window) displayChannel = new BroadcastChannel(displayStorageKey); } catch (_error) { displayChannel = null; }
        const publishDisplay = (state, speech, emotion) => {
          const controlledEmotion = voiceStyles[emotion] ? emotion : (emotionByState[state] || 'warm');
          avatar.dataset.emotion = controlledEmotion;
          const packet = {
            schema:'xiaoj_display_projection_2.3',
            state:state || 'idle',
            emotion:controlledEmotion,
            speech:String(speech || caption.textContent || '').slice(0,240),
            outfit:currentOutfit,
            created_at:Date.now()
          };
          try { localStorage.setItem(displayStorageKey, JSON.stringify(packet)); } catch (_error) {}
          if (displayChannel) displayChannel.postMessage(packet);
        };
        const speak = (text, emotion = 'warm') => new Promise((resolve) => {
          caption.textContent = text;
          avatar.classList.add('is-speaking');
          publishDisplay('speaking', text, emotion);
          if ('speechSynthesis' in window) {
            speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            const voiceStyle = voiceStyles[emotion] || voiceStyles.warm;
            utterance.lang = 'zh-TW'; utterance.rate = voiceStyle.rate; utterance.pitch = voiceStyle.pitch;
            let finished = false;
            const finish = (ok) => { if (finished) return; finished = true; avatar.classList.remove('is-speaking'); publishDisplay('idle', text, emotion); resolve(ok); };
            let started = false;
            utterance.onstart = () => { started = true; };
            utterance.onend = () => finish(true);
            utterance.onerror = () => finish(false);
            speechSynthesis.speak(utterance);
            setTimeout(() => { if (!started) { speechSynthesis.cancel(); finish(false); } }, 1600);
            setTimeout(() => finish(false), Math.min(12000, Math.max(4500, text.length * 210)));
          } else { avatar.classList.remove('is-speaking'); publishDisplay('idle', text, emotion); resolve(false); }
        });
        const readBackOrder = (payload) => {
          const lines = payload.frozen_facts?.order_lines || [];
          if (!lines.length) return Promise.resolve(false);
          const items = lines.map(line => `${line.name}${line.quantity}份`).join('、');
          return speak(`結帳前為你複誦：${items}，合計${payload.frozen_facts.total}元。內容正確後，請本人按下確認。`, 'clear');
        };
        const render = (payload) => {
          currentPayload = payload;
          result.hidden = false;
          resultState.textContent = payload.state_zh || '已建立受控回應';
          resultSpeech.textContent = payload.xiaoj_line || '小J已收到。';
          publishDisplay('thinking', resultSpeech.textContent, 'focused');
          orderPreview.innerHTML = '';
          const lines = payload.frozen_facts?.order_lines || [];
          lines.forEach(line => {
            const item = document.createElement('li');
            const left = document.createElement('span'); left.textContent = `${line.name} × ${line.quantity}`;
            const right = document.createElement('strong'); right.textContent = `NT$${line.subtotal}`;
            item.append(left,right); orderPreview.append(item);
          });
          if (lines.length) {
            const total = document.createElement('li');
            const left = document.createElement('span'); left.textContent = '展示預覽合計';
            const right = document.createElement('strong'); right.textContent = `NT$${payload.frozen_facts.total}`;
            total.append(left,right); orderPreview.append(total);
          }
          const confirmation = payload.customer_confirmation || {};
          currentPreviewRef = confirmation.preview_ref || '';
          touchConfirm.hidden = !confirmation.required;
          confirmButton.disabled = true;
          readbackButton.disabled = !confirmation.required;
          readbackButton.textContent = '播放結帳前語音複誦';
          confirmButton.textContent = '我確認以上品項與數量';
          confirmNote.textContent = confirmation.required ? '小J正在進行結帳前語音複誦；完成前不能確認。' : (confirmation.state_zh || '目前沒有可確認品項。');
          receipt.textContent = JSON.stringify(payload.eight_dimensional_receipt || payload,null,2);
          readBackOrder(payload).then((completed) => {
            if (!confirmation.required) return;
            confirmButton.dataset.voiceReadbackCompleted = completed ? 'true' : 'false';
            confirmButton.disabled = !completed;
            readbackButton.textContent = completed ? '重新播放結帳前語音複誦' : '點此播放結帳前語音複誦';
            confirmNote.textContent = completed ? '語音複誦已完成，請真人核對後親手觸控確認。' : '瀏覽器未允許自動語音，請先點上方按鈕播放；結帳確認仍鎖定。';
          });
        };
        const requestAppearance = (text) =>
          fetch('/wuchang/xiaoj/api/store-flair', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',method:'call',params:{text},id:Date.now()})})
            .then(response => response.json()).then(body => {
              const payload = body.result || body;
              if (!payload.flair) return payload;
              caption.textContent = payload.flair;
              if (!('speechSynthesis' in window) || !speechSynthesis.speaking) speak(payload.flair, 'cheerful');
              return payload;
            }).catch(() => null);
        form.addEventListener('submit', async (event) => {
          event.preventDefault();
          const text = input.value.trim(); if (!text) return;
          currentIntent = text; currentPreviewRef = '';
          result.hidden = false; resultState.textContent = '8DADI 正在對準'; resultSpeech.textContent = '小J正在把幽默和訂單分開處理…'; orderPreview.innerHTML = ''; touchConfirm.hidden = true;
          publishDisplay('thinking', '我正在把你的話對準店務狀態。', 'focused');
          try {
            const response = await fetch('/wuchang/xiaoj/api/store-chat', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',method:'call',params:{text},id:Date.now()})});
            const body = await response.json();
            if (body.error) throw new Error(body.error.message || '回應失敗');
            render(body.result || body); requestAppearance(text);
          } catch (error) {
            resultState.textContent = '離線備援'; resultSpeech.textContent = '對話通路正在休息，但商店介面仍可用；正式訂單沒有被送出。'; receipt.textContent = String(error);
            publishDisplay('offline', resultSpeech.textContent, 'reassuring');
          }
        });
        confirmButton.addEventListener('click', async () => {
          if (!currentIntent || !currentPreviewRef) return;
          confirmButton.disabled = true; confirmButton.textContent = '正在核對觸控確認';
          try {
            const response = await fetch('/wuchang/xiaoj/api/store-confirm', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',method:'call',params:{text:currentIntent,preview_ref:currentPreviewRef,acknowledged:true,voice_readback_completed:confirmButton.dataset.voiceReadbackCompleted === 'true'},id:Date.now()})});
            const body = await response.json(); const payload = body.result || body;
            if (body.error || !payload.customer_touch_confirmed) throw new Error(body.error?.message || '確認未成立');
            resultState.textContent = '顧客觸控確認成立';
            confirmButton.textContent = '已確認，不會重複送出';
            confirmNote.textContent = payload.state_zh;
            receipt.textContent = JSON.stringify(payload.eight_dimensional_receipt || payload,null,2);
            publishDisplay('confirmed', '顧客已完成真人觸控確認。', 'cheerful');
            speak('已收到你的親手確認。店內正式菜單尚未接通，所以現在沒有偷送單。', 'cheerful');
          } catch (error) {
            confirmButton.disabled = false; confirmButton.textContent = '重新確認以上品項與數量';
            confirmNote.textContent = '確認未成立，訂單沒有送出。';
          }
        });
        readbackButton.addEventListener('click', async () => {
          if (!currentPayload) return;
          readbackButton.disabled = true; readbackButton.textContent = '小J正在複誦';
          const completed = await readBackOrder(currentPayload);
          confirmButton.dataset.voiceReadbackCompleted = completed ? 'true' : 'false';
          confirmButton.disabled = !completed;
          readbackButton.disabled = false;
          readbackButton.textContent = completed ? '重新播放結帳前語音複誦' : '再次播放結帳前語音複誦';
          confirmNote.textContent = completed ? '語音複誦已完成，請真人核對後親手觸控確認。' : '語音仍未能播放，結帳確認維持鎖定。';
        });
        document.querySelectorAll('[data-quick]').forEach(button => button.addEventListener('click',() => { input.value=button.dataset.quick; input.focus(); }));
        document.querySelectorAll('[data-menu-intent]').forEach(button => button.addEventListener('click',() => { input.value=button.dataset.menuIntent; document.querySelector('#xiaoj-ordering').scrollIntoView({behavior:'smooth'}); input.focus(); }));
        document.querySelectorAll('[data-xiaoj-outfit]').forEach(button => button.addEventListener('click',() => {
          const outfit = button.dataset.xiaojOutfit;
          if (!displayAssets[outfit]) return;
          currentOutfit = outfit;
          heroImage.src = displayAssets[outfit];
          heroImage.alt = '小J ' + button.textContent.trim();
          document.querySelectorAll('[data-xiaoj-outfit]').forEach(item => item.classList.toggle('is-active', item === button));
          publishDisplay('idle', '小J已換上' + button.textContent.trim() + '。', 'warm');
        }));
        const openDisplay = document.querySelector('[data-open-display]');
        openDisplay.addEventListener('click',() => publishDisplay('idle', caption.textContent, 'warm'));
        const voiceButton = document.querySelector('[data-voice-intent]');
        voiceButton.addEventListener('click',() => {
          const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
          if (!Recognition) { input.placeholder='此瀏覽器未提供語音辨識，請直接輸入文字。'; input.focus(); return; }
          const recognition = new Recognition(); recognition.lang='zh-TW'; recognition.interimResults=false;
          recognition.onstart=() => { avatar.classList.add('is-listening'); voiceButton.textContent='小J正在聽'; publishDisplay('listening', '我在聽，請慢慢說。', 'attentive'); };
          recognition.onend=() => { avatar.classList.remove('is-listening'); voiceButton.textContent='開始語音'; publishDisplay('idle', caption.textContent, 'warm'); };
          recognition.onresult=(event) => { input.value=event.results[0][0].transcript; form.requestSubmit(); };
          recognition.start();
        });
        const warmState = document.querySelector('[data-warm-state]');
        const warmup = requestAppearance('新顧客剛走進咖啡館，請準備一句不含交易內容的迎賓幽默。');
        publishDisplay('warming', '歡迎光臨，我正在準備今天的店務狀態。', 'welcoming');
        speak('歡迎光臨上品聊國咖啡館重新總店，我是小J。先看一段迎賓動畫，想喝什麼，等等直接跟我說。', 'welcoming');
        warmup.then(payload => {
          warmState.textContent = payload?.flair ? '本機小模型已暖機 · 8DADI 店務核心隨時可用' : '確定性離線店務已就緒 · 模型外表在背景待命';
        });
      })();
    </script>
    """


def _xiaoj_display_page() -> str:
    return """<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>小J 外接顯示畫面｜上品聊國咖啡館重新總店</title>
  <style>
    :root { color-scheme:dark; --cream:#fff4e7; --muted:#cbb8a5; --mint:#75e0b1; --copper:#ed9b5e; }
    * { box-sizing:border-box; }
    html,body { width:100%; height:100%; margin:0; overflow:hidden; background:#0b0705; font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
    .scene { position:relative; width:100%; height:100%; isolation:isolate; background:#0b0705; }
    .scene-image { position:absolute; inset:-1.5%; width:103%; height:103%; object-fit:cover; object-position:center; animation:display-breathe 8s ease-in-out infinite alternate; transition:opacity .45s ease,filter .35s ease; }
    .scene::after { content:""; position:absolute; inset:0; z-index:1; pointer-events:none; background:linear-gradient(90deg,transparent 28%,rgba(7,5,4,.2) 52%,rgba(7,5,4,.86) 100%),linear-gradient(0deg,rgba(5,3,2,.62),transparent 35%); }
    .brand { position:absolute; z-index:3; left:clamp(22px,4vw,68px); top:clamp(20px,4vw,54px); display:flex; align-items:center; gap:12px; padding:10px 14px; border:1px solid rgba(255,255,255,.16); border-radius:999px; color:var(--cream); background:rgba(12,8,6,.52); backdrop-filter:blur(14px); font-weight:850; letter-spacing:.06em; }
    .brand::before { content:""; width:9px; height:9px; border-radius:50%; background:var(--mint); box-shadow:0 0 18px var(--mint); }
    .panel { position:absolute; z-index:3; right:clamp(24px,5vw,86px); top:50%; width:min(42vw,670px); translate:0 -48%; color:var(--cream); }
    .kicker { margin:0 0 14px; color:var(--copper); font-size:clamp(.72rem,1.1vw,.92rem); font-weight:900; letter-spacing:.17em; }
    h1 { margin:0; font-size:clamp(3.2rem,8vw,8rem); line-height:.86; letter-spacing:-.07em; }
    h1 span { display:block; color:transparent; background:linear-gradient(100deg,#fff2df,#efa36b 55%,#7ce4b5); background-clip:text; -webkit-background-clip:text; }
    .status-line { display:flex; align-items:center; gap:10px; margin-top:26px; color:#bdf5d8; font-weight:850; }
    .status-dot { width:10px; height:10px; border-radius:50%; background:var(--mint); box-shadow:0 0 20px var(--mint); }
    .caption { min-height:4.8em; margin:18px 0 0; color:#efe2d6; font-size:clamp(1.2rem,2.5vw,2.25rem); line-height:1.55; text-wrap:balance; }
    .meta { display:flex; flex-wrap:wrap; gap:9px; margin-top:22px; }
    .meta span { padding:8px 11px; border:1px solid rgba(255,255,255,.15); border-radius:999px; color:var(--muted); background:rgba(255,255,255,.035); font-size:.78rem; }
    .voice-wave { height:32px; display:flex; align-items:center; gap:5px; margin-top:22px; opacity:.32; }
    .voice-wave span { width:4px; height:9px; border-radius:99px; background:var(--mint); }
    body[data-state="speaking"] .voice-wave { opacity:1; }
    body[data-state="speaking"] .voice-wave span { animation:voice-bar .52s ease-in-out infinite alternate; }
    body[data-state="speaking"] .voice-wave span:nth-child(2),body[data-state="speaking"] .voice-wave span:nth-child(5) { animation-delay:.12s; }
    body[data-state="speaking"] .voice-wave span:nth-child(3) { animation-delay:.24s; }
    body[data-state="listening"] .status-dot { background:#6cbcff; box-shadow:0 0 26px #6cbcff; animation:listen-pulse .85s ease-in-out infinite alternate; }
    body[data-state="thinking"] .status-dot,body[data-state="warming"] .status-dot { background:var(--copper); box-shadow:0 0 24px var(--copper); animation:listen-pulse .7s ease-in-out infinite alternate; }
    body[data-state="confirmed"] .status-dot { background:#fff0b2; box-shadow:0 0 28px #fff0b2; }
    body[data-state="offline"] .status-dot { background:#d9a37f; box-shadow:none; }
    body[data-state="speaking"] .scene-image { filter:brightness(1.07) saturate(1.05); }
    body[data-emotion="welcoming"] .scene-image,body[data-emotion="warm"] .scene-image { filter:brightness(1.04) saturate(1.08) sepia(.035); }
    body[data-emotion="attentive"] .scene-image,body[data-emotion="focused"] .scene-image { filter:brightness(1.02) saturate(.96) hue-rotate(3deg); }
    body[data-emotion="cheerful"] .scene-image { filter:brightness(1.1) saturate(1.14); }
    body[data-emotion="reassuring"] .scene-image { filter:brightness(.98) saturate(.9); }
    .boundary { position:absolute; z-index:3; left:clamp(22px,4vw,68px); bottom:clamp(18px,3vw,42px); color:rgba(255,244,231,.68); font-size:clamp(.68rem,1vw,.82rem); }
    .fullscreen { position:absolute; z-index:4; right:20px; top:20px; min-width:44px; min-height:44px; padding:9px 13px; border:1px solid rgba(255,255,255,.17); border-radius:999px; color:#f8eadc; background:rgba(8,5,4,.56); cursor:pointer; font:inherit; }
    @keyframes display-breathe { from { transform:scale(1.01) translate3d(0,0,0); } to { transform:scale(1.035) translate3d(-.25%,-.35%,0); } }
    @keyframes voice-bar { to { height:30px; } }
    @keyframes listen-pulse { to { transform:scale(1.65); opacity:.56; } }
    @media(max-aspect-ratio:4/3) {
      .scene-image { object-position:37% center; }
      .scene::after { background:linear-gradient(0deg,rgba(5,3,2,.92),transparent 73%); }
      .panel { left:7vw; right:7vw; top:auto; bottom:9vh; width:auto; translate:0; }
      h1 { font-size:clamp(3rem,12vw,6.5rem); }
      .caption { min-height:0; }
    }
    @media(prefers-reduced-motion:reduce) { .scene-image,.voice-wave span,.status-dot { animation:none!important; } }
  </style>
</head>
<body data-state="idle" data-emotion="warm">
  <main class="scene">
    <img class="scene-image" src="/wuchang_cafe_ai_gateway/static/src/img/xiaoj_display_23/xiaoj-white-tech.png" alt="小J 白色科技制服" data-display-image>
    <div class="brand">上品聊國咖啡館重新總店</div>
    <section class="panel" aria-live="polite">
      <p class="kicker">數位設備社區團結行動 × 8DADI 2.3</p>
      <h1>我是<span>小J。</span></h1>
      <div class="status-line"><span class="status-dot"></span><span data-display-state>待機中</span></div>
      <p class="caption" data-display-caption>我就在旁邊。想喝什麼，直接跟我說。</p>
      <div class="voice-wave" aria-hidden="true"><span></span><span></span><span></span><span></span><span></span><span></span></div>
      <div class="meta"><span data-display-outfit>白色科技制服</span><span data-display-emotion>情緒：溫暖</span><span>區網內暫態同步</span><span>顯示投影無交易權限</span></div>
    </section>
    <p class="boundary">外接 HDMI 顯示頁｜不寫訂單、不收款、不管理會員資料</p>
    <button class="fullscreen" type="button" data-fullscreen>全螢幕</button>
  </main>
  <script>
    (() => {
      const storageKey = 'wuchang-xiaoj-display-v23';
      const image = document.querySelector('[data-display-image]');
      const caption = document.querySelector('[data-display-caption]');
      const stateLabel = document.querySelector('[data-display-state]');
      const outfitLabel = document.querySelector('[data-display-outfit]');
      const emotionLabel = document.querySelector('[data-display-emotion]');
      const assets = {
        white:['/wuchang_cafe_ai_gateway/static/src/img/xiaoj_display_23/xiaoj-white-tech.png','白色科技制服'],
        barista:['/wuchang_cafe_ai_gateway/static/src/img/xiaoj_display_23/xiaoj-barista.png','咖啡師圍裙'],
        event:['/wuchang_cafe_ai_gateway/static/src/img/xiaoj_display_23/xiaoj-event-black.png','深色活動接待服'],
        community:['/wuchang_cafe_ai_gateway/static/src/img/xiaoj_display_23/xiaoj-community-gray.png','社區日常服']
      };
      const states = {
        idle:'待機中', warming:'正在暖機', listening:'正在聽你說',
        thinking:'8DADI 正在對準', speaking:'小J 正在說話',
        confirmed:'真人確認已成立', offline:'離線備援'
      };
      const emotions = {
        warm:'溫暖', welcoming:'迎賓', attentive:'專注聆聽', focused:'專注對準',
        cheerful:'愉快', reassuring:'安心', clear:'清楚中性'
      };
      const emotionByState = {
        idle:'warm', warming:'welcoming', listening:'attentive', thinking:'focused',
        speaking:'warm', confirmed:'cheerful', offline:'reassuring'
      };
      Object.values(assets).forEach(item => { const preload = new Image(); preload.src = item[0]; });
      const applyPacket = (packet) => {
        if (!packet || packet.schema !== 'xiaoj_display_projection_2.3') return;
        if (!assets[packet.outfit] || !states[packet.state]) return;
        const emotion = emotions[packet.emotion] ? packet.emotion : emotionByState[packet.state];
        document.body.dataset.state = packet.state;
        document.body.dataset.emotion = emotion;
        image.src = assets[packet.outfit][0];
        image.alt = '小J ' + assets[packet.outfit][1];
        outfitLabel.textContent = assets[packet.outfit][1];
        stateLabel.textContent = states[packet.state];
        emotionLabel.textContent = '情緒：' + emotions[emotion];
        if (typeof packet.speech === 'string' && packet.speech.trim()) caption.textContent = packet.speech.slice(0,240);
      };
      try {
        const stored = JSON.parse(localStorage.getItem(storageKey) || 'null');
        applyPacket(stored);
      } catch (_error) {}
      try {
        if ('BroadcastChannel' in window) {
          const channel = new BroadcastChannel(storageKey);
          channel.onmessage = event => applyPacket(event.data);
        }
      } catch (_error) {}
      window.addEventListener('storage', event => {
        if (event.key !== storageKey || !event.newValue) return;
        try { applyPacket(JSON.parse(event.newValue)); } catch (_error) {}
      });
      document.querySelector('[data-fullscreen]').addEventListener('click',() => {
        const target = document.documentElement;
        if (!document.fullscreenElement && target.requestFullscreen) target.requestFullscreen();
        else if (document.exitFullscreen) document.exitFullscreen();
      });
      window.addEventListener('keydown',event => {
        if (event.key.toLowerCase() === 'f') document.querySelector('[data-fullscreen]').click();
      });
    })();
  </script>
</body>
</html>"""


def _group_member_field_product_body() -> str:
    product = build_group_member_total_field_product_candidate()
    type_meta = {
        "merchant": ("店", "商家櫃台", "點餐、菜單、訂單與現場服務"),
        "committee": ("寓", "大廳服務台", "住戶接待、公告、報修與訪客引導"),
        "nonprofit_association": ("會", "非營利協會", "會員服務、活動協作與公共任務"),
        "other": ("新", "其他類型", "由創辦人親訪理解後專案設計"),
    }
    type_cards = "".join(
        f"""
        <button class="ring-card{' is-active' if index == 0 else ''}"
                type="button" data-index="{index}" data-code="{html.escape(item['code'])}"
                style="--item-index:{index}" aria-pressed="{'true' if index == 0 else 'false'}">
          <span class="ring-icon" aria-hidden="true">{type_meta[item['code']][0]}</span>
          <span class="ring-kicker">{html.escape(type_meta[item['code']][1])}</span>
          <strong>{html.escape(item['label'])}</strong>
          <span>{html.escape(type_meta[item['code']][2])}</span>
          <small>{'需現實可用 8D 問卷' if item['questionnaire_required'] else '需創辦人核定與親訪設計'}</small>
        </button>
        """
        for index, item in enumerate(product["type_options"])
    )
    ring_dots = "".join(
        f'<button type="button" data-ring-dot="{index}" aria-label="選擇{html.escape(item["label"])}" '
        f'class="{"is-active" if index == 0 else ""}"></button>'
        for index, item in enumerate(product["type_options"])
    )
    journey_items = "".join(
        f"""
        <li class="journey-step">
          <span>{item['step']:02d}</span>
          <div><small>{html.escape(item['code'].replace('_', ' '))}</small><strong>{html.escape(item['label'])}</strong></div>
        </li>
        """
        for item in product["journey"]
    )
    trust_items = "".join(f"<li>{html.escape(item)}</li>" for item in product["trust_copy"])
    gap_labels = {
        "PERSONAL_IDENTITY_PACKET_RENDERER_BINDING_UNVERIFIED": "身分封包顯示器待綁定",
        "MULTI_ACCOUNT_LOGIN_AND_NATURAL_IDENTITY_RELATION_VERIFIERS_UNBOUND": "多帳號登入與同人關連待驗證",
        "FOUNDER_PERSONAL_ACCOUNT_PACKET_BINDING_VERIFIER_UNBOUND": "創辦人帳號封包驗證待綁定",
        "DOMAIN_PERMISSION_COORDINATION_POLICY_UNRATIFIED": "領域權限協調規則待核定",
        "FOUNDER_EXCLUSIVE_CONSOLE_SEAT_GATE_UNBOUND": "創辦人控制台身分門待綁定",
    }
    gap_items = "".join(
        f'<span>{html.escape(gap_labels.get(item, item))}</span>'
        for item in product["landing_gaps"][:5]
    )
    styles = """
      :root { color-scheme: dark; }
      body.field-product {
        --ink:#edf6ff; --muted:#9fb0c8; --line:rgba(176,205,231,.16);
        --panel:rgba(12,27,47,.72); --cyan:#61e6c6; --blue:#6bb8ff;
        --amber:#ffc277; --danger:#ff8f9e; --deep:#06101c;
        min-height:100vh; color:var(--ink); background:
          radial-gradient(circle at 15% 5%, rgba(42,131,172,.22), transparent 34rem),
          radial-gradient(circle at 85% 20%, rgba(89,77,171,.2), transparent 30rem),
          linear-gradient(150deg,#050c16 0%,#09182a 48%,#07121f 100%);
      }
      body.field-product main { max-width:1240px; padding:24px clamp(16px,4vw,52px) 72px; }
      body.field-product .bar {
        position:relative; z-index:20; border:1px solid var(--line); border-radius:18px;
        padding:12px 16px; margin:0 0 18px; background:rgba(5,14,26,.68);
        backdrop-filter:blur(18px); box-shadow:0 18px 60px rgba(0,0,0,.18);
      }
      body.field-product .bar p { margin:0; color:var(--muted); font-size:.76rem; letter-spacing:.12em; text-transform:uppercase; }
      body.field-product .bar h1 { margin:3px 0 0; font-size:clamp(1rem,2vw,1.25rem); }
      body.field-product .state { border:1px solid rgba(255,194,119,.35); border-radius:999px; background:rgba(255,194,119,.1); color:#ffd9a8; font-size:.7rem; }
      .field-ui { position:relative; isolation:isolate; overflow:hidden; border:1px solid var(--line); border-radius:32px; background:rgba(3,12,23,.7); box-shadow:0 36px 100px rgba(0,0,0,.42); }
      .field-ui::before,.field-ui::after { content:""; position:absolute; z-index:-1; width:32rem; height:32rem; border-radius:50%; filter:blur(70px); opacity:.18; pointer-events:none; }
      .field-ui::before { top:-13rem; right:-10rem; background:var(--cyan); }
      .field-ui::after { left:-16rem; top:40rem; background:#7568ff; }
      .field-ui * { box-sizing:border-box; }
      .field-ui section { margin:0; padding:clamp(32px,7vw,82px) clamp(22px,7vw,86px); border:0; border-bottom:1px solid var(--line); background:transparent; }
      .hero { min-height:620px; display:grid; grid-template-columns:minmax(0,1.15fr) minmax(320px,.85fr); align-items:center; gap:clamp(32px,7vw,86px); }
      .eyebrow { display:inline-flex; align-items:center; gap:9px; margin:0 0 18px; color:var(--cyan); font-size:.74rem; font-weight:800; letter-spacing:.17em; text-transform:uppercase; }
      .eyebrow::before { content:""; width:26px; height:1px; background:currentColor; box-shadow:0 0 16px currentColor; }
      .hero h2 { margin:0; max-width:760px; font-size:clamp(2.7rem,6.4vw,6.1rem); line-height:.98; letter-spacing:-.058em; text-wrap:balance; }
      .hero h2 span { display:block; color:transparent; background:linear-gradient(100deg,var(--cyan),#d9f8ff 52%,var(--blue)); background-clip:text; -webkit-background-clip:text; }
      .hero-copy { margin:24px 0 0; max-width:680px; color:var(--muted); font-size:clamp(1rem,1.7vw,1.2rem); line-height:1.75; }
      .hero-actions { display:flex; flex-wrap:wrap; gap:12px; margin-top:30px; }
      .primary-action,.secondary-action { appearance:none; border:0; border-radius:999px; padding:14px 21px; color:var(--deep); font-weight:850; cursor:pointer; transition:transform .2s ease,box-shadow .2s ease; }
      .primary-action { background:linear-gradient(120deg,var(--cyan),#a4f6e3); box-shadow:0 15px 42px rgba(97,230,198,.24); }
      .secondary-action { color:var(--ink); background:rgba(255,255,255,.06); border:1px solid var(--line); }
      .primary-action:hover,.secondary-action:hover { transform:translateY(-2px); }
      .proof-row { display:flex; flex-wrap:wrap; gap:9px; margin-top:26px; }
      .proof-row span { padding:8px 11px; border:1px solid var(--line); border-radius:999px; color:#bdcbe0; font-size:.74rem; background:rgba(255,255,255,.025); }
      .sovereign-orb { position:relative; aspect-ratio:1; display:grid; place-items:center; transform:translate3d(var(--orb-x,0),var(--orb-y,0),0); transition:transform .25s ease-out; }
      .orb-core { width:48%; aspect-ratio:1; display:grid; place-items:center; border-radius:50%; color:var(--deep); font-size:clamp(2rem,6vw,4.7rem); font-weight:950; background:radial-gradient(circle at 34% 28%,#edfffb,var(--cyan) 42%,#188e83 100%); box-shadow:0 0 70px rgba(97,230,198,.35),inset -18px -20px 50px rgba(1,58,59,.28); }
      .orb-ring { position:absolute; width:76%; aspect-ratio:1; border:1px solid rgba(118,235,220,.32); border-radius:50%; transform:rotateX(68deg) rotateZ(12deg); box-shadow:0 0 35px rgba(97,230,198,.08); animation:orbit 16s linear infinite; }
      .orb-ring:nth-child(2) { width:92%; transform:rotateY(66deg) rotateZ(24deg); animation-direction:reverse; animation-duration:22s; }
      .orb-node { position:absolute; width:10px; height:10px; border-radius:50%; background:var(--amber); box-shadow:0 0 22px var(--amber); }
      .orb-node.n1 { top:15%; left:30%; }.orb-node.n2 { right:8%; top:48%; background:var(--blue); box-shadow:0 0 22px var(--blue); }.orb-node.n3 { bottom:12%; left:24%; }
      @keyframes orbit { to { rotate:1turn; } }
      .section-head { display:flex; align-items:end; justify-content:space-between; gap:20px; margin-bottom:30px; }
      .section-head h3 { margin:5px 0 0; font-size:clamp(2rem,4vw,3.8rem); letter-spacing:-.04em; }
      .section-head p { max-width:520px; margin:0; color:var(--muted); line-height:1.65; }
      .type-selector { min-height:700px; overflow:hidden; }
      .ring-shell { position:relative; min-height:460px; display:grid; place-items:center; perspective:1300px; touch-action:pan-y; }
      .ring-stage { position:relative; width:min(280px,62vw); height:350px; transform-style:preserve-3d; transition:transform .62s cubic-bezier(.2,.78,.2,1); }
      .ring-card { position:absolute; inset:18px 0; display:flex; flex-direction:column; align-items:flex-start; gap:8px; padding:24px; border:1px solid rgba(171,209,235,.2); border-radius:25px; text-align:left; color:var(--ink); background:linear-gradient(145deg,rgba(26,49,76,.92),rgba(8,22,39,.9)); box-shadow:0 24px 65px rgba(0,0,0,.34); backface-visibility:hidden; transform:translateZ(-260px); opacity:.28; cursor:pointer; transition:transform .62s cubic-bezier(.2,.78,.2,1),opacity .35s,border-color .3s,filter .3s; }
      .ring-card.is-active { opacity:1; border-color:rgba(97,230,198,.65); filter:drop-shadow(0 0 24px rgba(97,230,198,.12)); }
      .ring-icon { width:52px; height:52px; display:grid; place-items:center; border-radius:16px; background:rgba(97,230,198,.12); border:1px solid rgba(97,230,198,.28); color:var(--cyan); font-size:1.25rem; font-weight:900; }
      .ring-kicker { margin-top:13px; color:var(--cyan); font-size:.7rem; font-weight:800; letter-spacing:.15em; text-transform:uppercase; }
      .ring-card strong { font-size:1.8rem; letter-spacing:-.04em; }.ring-card>span:not(.ring-icon):not(.ring-kicker) { color:var(--muted); line-height:1.55; }
      .ring-card small { margin-top:auto; padding-top:14px; border-top:1px solid var(--line); width:100%; color:#d6e6f6; }
      .ring-controls { display:flex; align-items:center; justify-content:center; gap:16px; }
      .ring-arrow { width:44px; height:44px; border:1px solid var(--line); border-radius:50%; color:var(--ink); background:rgba(255,255,255,.04); cursor:pointer; font-size:1.15rem; }
      .ring-dots { display:flex; gap:8px; }.ring-dots button { width:7px; height:7px; padding:0; border:0; border-radius:999px; background:#51647d; cursor:pointer; transition:.25s; }.ring-dots button.is-active { width:27px; background:var(--cyan); }
      .selection-live { margin:14px auto 0; text-align:center; color:var(--muted); min-height:1.5em; }
      .identity-command { background:linear-gradient(180deg,rgba(6,16,29,.12),rgba(17,35,57,.28))!important; }
      .bento { display:grid; grid-template-columns:repeat(12,1fr); gap:14px; }
      .bento-card { grid-column:span 4; min-height:210px; padding:24px; border:1px solid var(--line); border-radius:24px; background:linear-gradient(145deg,rgba(255,255,255,.055),rgba(255,255,255,.018)); }
      .bento-card.wide { grid-column:span 8; }.bento-card.accent { background:linear-gradient(135deg,rgba(97,230,198,.13),rgba(107,184,255,.05)); }
      .bento-card .number { color:var(--cyan); font-size:.69rem; font-weight:900; letter-spacing:.15em; }.bento-card h4 { margin:18px 0 9px; font-size:1.35rem; }.bento-card p { margin:0; color:var(--muted); line-height:1.65; }
      .account-flow { display:flex; align-items:center; flex-wrap:wrap; gap:8px; margin-top:22px; }.account-flow span { padding:8px 10px; border-radius:10px; background:rgba(2,12,22,.46); border:1px solid var(--line); font-size:.75rem; }.account-flow b { color:var(--cyan); }
      .journey-layout { display:grid; grid-template-columns:minmax(260px,.72fr) minmax(0,1.28fr); gap:clamp(34px,7vw,84px); align-items:start; }
      .journey-sticky { position:sticky; top:24px; }.journey-sticky h3 { margin:4px 0 18px; font-size:clamp(2rem,4vw,3.7rem); letter-spacing:-.045em; }.journey-sticky p { color:var(--muted); line-height:1.7; }
      .journey { list-style:none; margin:0; padding:0; position:relative; }.journey::before { content:""; position:absolute; left:23px; top:28px; bottom:28px; width:1px; background:linear-gradient(var(--cyan),rgba(107,184,255,.16)); }
      .journey-step { position:relative; display:grid; grid-template-columns:48px 1fr; gap:18px; padding:0 0 26px; }.journey-step>span { position:relative; z-index:1; width:46px; height:46px; display:grid; place-items:center; border-radius:50%; background:#0a1b2e; border:1px solid rgba(97,230,198,.32); color:var(--cyan); font-weight:900; font-size:.72rem; }.journey-step div { padding:11px 18px 18px; border-bottom:1px solid var(--line); }.journey-step small { display:block; margin-bottom:5px; color:#7187a3; font-size:.61rem; letter-spacing:.1em; }.journey-step strong { line-height:1.5; }
      .xiaoj-guide { display:block; }
      .guide-copy { display:grid; grid-template-columns:minmax(260px,.75fr) minmax(0,1.25fr); gap:clamp(24px,6vw,72px); align-items:end; border:1px solid var(--line); border-radius:26px; padding:clamp(24px,4vw,40px); background:rgba(255,255,255,.025); }.guide-copy h3 { margin:5px 0 0; font-size:clamp(2rem,4vw,3.3rem); }.guide-copy>div>p { color:var(--muted); line-height:1.7; }.gap-cloud { display:flex; flex-wrap:wrap; gap:8px; margin-top:20px; }.gap-cloud span { padding:7px 9px; border:1px solid rgba(255,143,158,.22); border-radius:9px; color:#ffc1ca; background:rgba(255,143,158,.055); font-size:.66rem; }
      .space-switcher { display:flex; gap:8px; margin:18px 0 0; padding:6px; border:1px solid var(--line); border-radius:16px; background:rgba(3,13,24,.5); overflow-x:auto; scrollbar-width:none; }.space-switcher::-webkit-scrollbar { display:none; }.space-switcher button { flex:1; min-width:max-content; border:0; border-radius:11px; padding:11px 15px; color:#9eb0c6; background:transparent; cursor:pointer; font-weight:800; }.space-switcher button.is-active { color:var(--deep); background:var(--cyan); }.space-switcher small { margin-left:5px; font-size:.65rem; opacity:.72; }
      .xiaoj-workspace { display:grid; grid-template-columns:minmax(0,1.05fr) minmax(330px,.95fr); gap:18px; margin-top:18px; }
      .guide-chat,.function-orbit { border:1px solid var(--line); border-radius:26px; padding:clamp(24px,4vw,36px); background:rgba(255,255,255,.025); }
      .guide-chat { display:flex; flex-direction:column; min-height:430px; background:linear-gradient(145deg,rgba(21,44,69,.7),rgba(6,18,32,.82)); }.chat-head { display:flex; align-items:center; gap:10px; font-weight:900; }.chat-avatar { width:38px; height:38px; display:grid; place-items:center; border-radius:50%; background:var(--cyan); color:var(--deep); }.chat-status { color:var(--cyan); font-size:.7rem; }.command-launcher { margin-left:auto; border:1px solid var(--line); border-radius:10px; padding:7px 9px; color:#cbd9e8; background:rgba(255,255,255,.045); cursor:pointer; }.command-launcher kbd { color:var(--cyan); }.chat-message { margin:24px 0 14px; padding:17px; border-radius:4px 18px 18px 18px; background:rgba(255,255,255,.07); color:#dce9f7; line-height:1.65; }.workflow-preview { margin-top:auto; padding:18px; border:1px solid var(--line); border-radius:18px; background:rgba(2,12,23,.32); }.workflow-preview small { color:var(--cyan); font-weight:800; letter-spacing:.11em; }.workflow-preview h4 { margin:8px 0 13px; }.workflow-preview ol { margin:0; padding:0; list-style:none; display:grid; gap:8px; counter-reset:flow; }.workflow-preview li { counter-increment:flow; display:flex; gap:9px; color:#acbdd1; font-size:.82rem; }.workflow-preview li::before { content:counter(flow); width:20px; height:20px; display:grid; place-items:center; border-radius:50%; background:rgba(97,230,198,.12); color:var(--cyan); font-size:.65rem; flex:0 0 auto; }
      .function-orbit { position:relative; min-height:430px; overflow:hidden; background:radial-gradient(circle at 50% 50%,rgba(97,230,198,.12),transparent 38%),linear-gradient(145deg,rgba(8,24,42,.88),rgba(5,15,27,.94)); }.function-orbit::before,.function-orbit::after { content:""; position:absolute; left:50%; top:50%; translate:-50% -50%; width:270px; aspect-ratio:1; border:1px solid rgba(97,230,198,.18); border-radius:50%; pointer-events:none; }.function-orbit::after { width:190px; border-color:rgba(107,184,255,.14); }.orbit-core { position:absolute; z-index:2; left:50%; top:50%; translate:-50% -50%; width:88px; height:88px; display:grid; place-items:center; border-radius:50%; background:radial-gradient(circle at 35% 25%,#effffc,var(--cyan) 45%,#218a83); color:var(--deep); font-size:1.55rem; font-weight:950; box-shadow:0 0 45px rgba(97,230,198,.25); }.orbit-action { position:absolute; z-index:3; border:1px solid rgba(174,207,231,.2); border-radius:999px; padding:10px 13px; color:#d6e5f4; background:rgba(13,31,50,.9); box-shadow:0 10px 28px rgba(0,0,0,.25); cursor:pointer; white-space:nowrap; transition:transform .2s,border-color .2s,color .2s; }.orbit-action:hover,.orbit-action.is-active { transform:translateY(-2px); border-color:var(--cyan); color:var(--cyan); }.orbit-action.n1 { left:50%; top:8%; translate:-50% 0; }.orbit-action.n2 { right:4%; top:50%; translate:0 -50%; }.orbit-action.n3 { left:50%; bottom:7%; translate:-50% 0; }.orbit-action.n4 { left:4%; top:50%; translate:0 -50%; }
      .function-orbit[data-space-panel="management"] { background:radial-gradient(circle at 50% 50%,rgba(255,194,119,.1),transparent 38%),linear-gradient(145deg,rgba(31,28,37,.9),rgba(8,17,29,.96)); }.function-orbit[data-space-panel="management"] .orbit-core { background:radial-gradient(circle at 35% 25%,#fff6e9,var(--amber) 50%,#a1662c); }
      .command-palette { width:min(620px,calc(100vw - 28px)); padding:0; border:1px solid rgba(167,205,231,.25); border-radius:24px; color:var(--ink); background:#0a192a; box-shadow:0 35px 100px rgba(0,0,0,.62); }.command-palette::backdrop { background:rgba(1,7,13,.72); backdrop-filter:blur(8px); }.command-shell { padding:20px; }.command-top { display:flex; align-items:center; gap:10px; }.command-search { flex:1; min-width:0; border:1px solid var(--line); border-radius:14px; padding:13px 15px; color:var(--ink); background:rgba(255,255,255,.055); font:inherit; }.command-close { width:42px; height:42px; border:1px solid var(--line); border-radius:50%; color:var(--ink); background:transparent; cursor:pointer; }.command-list { display:grid; gap:8px; margin-top:14px; max-height:min(580px,68vh); overflow:auto; }.command-list button { display:grid; grid-template-columns:42px 1fr; gap:12px; align-items:center; padding:12px; border:1px solid transparent; border-radius:14px; text-align:left; color:var(--ink); background:transparent; cursor:pointer; }.command-list button:hover { border-color:var(--line); background:rgba(255,255,255,.045); }.command-list button span:first-child { width:42px; height:42px; display:grid; place-items:center; border-radius:12px; color:var(--cyan); background:rgba(97,230,198,.1); font-weight:900; }.command-list strong,.command-list small { display:block; }.command-list small { margin-top:3px; color:var(--muted); }
      .trust-panel { display:grid; grid-template-columns:.8fr 1.2fr; gap:34px; align-items:start; }.trust-panel h3 { margin:4px 0 0; font-size:clamp(2rem,3.8vw,3.4rem); }.trust-list { list-style:none; margin:0; padding:0; display:grid; gap:10px; }.trust-list li { position:relative; padding:14px 16px 14px 44px; border:1px solid var(--line); border-radius:16px; color:#c1d0e1; background:rgba(255,255,255,.025); line-height:1.5; }.trust-list li::before { content:"✓"; position:absolute; left:16px; color:var(--cyan); font-weight:950; }
      .candidate-band { display:flex; justify-content:space-between; align-items:center; gap:24px; padding:24px clamp(22px,7vw,86px); background:rgba(255,194,119,.07); border-top:1px solid rgba(255,194,119,.18); }.candidate-band strong { color:#ffd49d; }.candidate-band span { color:var(--muted); font-size:.82rem; }
      body.field-product .route-payload { margin:18px 0 0; padding:15px 18px; border:1px solid var(--line); border-radius:16px; color:var(--muted); background:rgba(3,12,23,.54); }.route-payload summary { cursor:pointer; font-weight:800; }.route-payload pre { border-radius:12px; }
      @media (max-width:860px) { .hero,.journey-layout,.trust-panel,.guide-copy,.xiaoj-workspace { grid-template-columns:1fr; }.hero { padding-top:54px!important; }.sovereign-orb { max-width:500px; width:100%; margin:auto; }.journey-sticky { position:static; }.bento-card,.bento-card.wide { grid-column:span 6; }.section-head { align-items:start; flex-direction:column; } }
      @media (max-width:620px) { body.field-product main { padding:10px 10px 45px; } body.field-product .bar { align-items:flex-start; flex-direction:column; gap:10px; } body.field-product .bar>div { width:100%; min-width:0; } body.field-product .bar p { word-break:keep-all; } body.field-product .bar h1 { font-size:1rem; word-break:keep-all; } body.field-product .state { align-self:flex-start; max-width:100%; white-space:normal; } .field-ui { border-radius:22px; }.type-selector { min-height:auto; }.ring-shell { display:block; min-height:auto; overflow-x:auto; padding-bottom:16px; scroll-snap-type:x mandatory; scrollbar-width:none; }.ring-shell::-webkit-scrollbar { display:none; }.ring-stage { display:grid; grid-template-columns:repeat(4,minmax(230px,1fr)); grid-auto-flow:row; gap:12px; width:100%; max-width:none; height:auto; transform:none!important; }.ring-card { position:relative; inset:auto; width:auto; min-width:0; max-width:100%; min-height:330px; transform:none!important; opacity:1; scroll-snap-align:center; }.ring-controls { display:none; }.space-switcher button { min-width:0; padding:10px 7px; font-size:.74rem; }.space-switcher small { display:block; margin:2px 0 0; font-size:.52rem; }.bento-card,.bento-card.wide { grid-column:1/-1; }.candidate-band { align-items:flex-start; flex-direction:column; }.hero h2 { font-size:clamp(2.55rem,14vw,4.4rem); } }
      @media (prefers-reduced-motion:reduce) { *,*::before,*::after { scroll-behavior:auto!important; animation-duration:.001ms!important; animation-iteration-count:1!important; transition-duration:.001ms!important; }.sovereign-orb { transform:none!important; } }
    """
    script = """
      (() => {
        const root = document.querySelector('.field-ui');
        if (!root) return;
        const stage = root.querySelector('.ring-stage');
        const cards = [...root.querySelectorAll('.ring-card')];
        const dots = [...root.querySelectorAll('[data-ring-dot]')];
        const live = root.querySelector('.selection-live');
        const mobile = () => matchMedia('(max-width:620px)').matches;
        let active = 0, dragStart = null, wheelLocked = false;
        const select = (next) => {
          active = (next + cards.length) % cards.length;
          if (!mobile()) stage.style.transform = 'none';
          cards.forEach((card,index) => {
            const selected = index === active;
            let offset = index - active;
            if (offset > cards.length / 2) offset -= cards.length;
            if (offset < -cards.length / 2) offset += cards.length;
            if (!mobile()) {
              const depth = Math.abs(offset);
              card.style.transform = `translateX(${offset * 188}px) translateZ(${-depth * 155}px) rotateY(${offset * -38}deg) scale(${1 - depth * .07})`;
              card.style.zIndex = String(10 - depth);
              card.style.opacity = selected ? '1' : String(Math.max(.18,.7 - depth * .18));
            } else {
              card.style.removeProperty('transform');
              card.style.removeProperty('z-index');
              card.style.removeProperty('opacity');
            }
            card.classList.toggle('is-active',selected);
            card.setAttribute('aria-pressed',String(selected));
          });
          dots.forEach((dot,index) => dot.classList.toggle('is-active',index === active));
          live.textContent = `目前選擇：${cards[active].querySelector('strong').textContent}`;
        };
        cards.forEach((card,index) => card.addEventListener('click',() => select(index)));
        dots.forEach((dot,index) => dot.addEventListener('click',() => select(index)));
        root.querySelector('[data-ring-prev]').addEventListener('click',() => select(active - 1));
        root.querySelector('[data-ring-next]').addEventListener('click',() => select(active + 1));
        root.querySelector('.ring-shell').addEventListener('keydown',(event) => {
          if (event.key === 'ArrowLeft') { event.preventDefault(); select(active - 1); }
          if (event.key === 'ArrowRight') { event.preventDefault(); select(active + 1); }
        });
        root.querySelector('.ring-shell').addEventListener('pointerdown',(event) => { dragStart = event.clientX; });
        root.querySelector('.ring-shell').addEventListener('pointerup',(event) => {
          if (dragStart === null || mobile()) return;
          const delta = event.clientX - dragStart; dragStart = null;
          if (Math.abs(delta) > 35) select(active + (delta < 0 ? 1 : -1));
        });
        root.querySelector('.ring-shell').addEventListener('wheel',(event) => {
          if (mobile() || wheelLocked || Math.abs(event.deltaY) < 8) return;
          event.preventDefault(); wheelLocked = true; select(active + (event.deltaY > 0 ? 1 : -1));
          setTimeout(() => { wheelLocked = false; },420);
        },{ passive:false });
        root.querySelectorAll('[data-scroll]').forEach(button => button.addEventListener('click',() => {
          root.querySelector(button.dataset.scroll)?.scrollIntoView({behavior:'smooth',block:'start'});
        }));
        const orb = root.querySelector('.sovereign-orb');
        root.querySelector('.hero').addEventListener('pointermove',(event) => {
          if (matchMedia('(prefers-reduced-motion:reduce)').matches) return;
          const rect = event.currentTarget.getBoundingClientRect();
          orb.style.setProperty('--orb-x',`${((event.clientX-rect.left)/rect.width-.5)*16}px`);
          orb.style.setProperty('--orb-y',`${((event.clientY-rect.top)/rect.height-.5)*16}px`);
        });
        const functions = {
          life:{space:'personal',message:'生活輔助把日程、提醒、日常資訊與個人習慣放進同一段對話，讓小J主動整理但不替你做未授權決定。',title:'生活輔助',steps:['整理今天與近期安排','建立提醒與日常清單候選','依個人偏好提供生活資訊']},
          work:{space:'personal',message:'工作協作把任務、文件、會議與團隊交接串成可追蹤流程，先建立候選，再由人確認對外動作。',title:'工作協作',steps:['整理任務與共同目標','協作文件、會議與進度','產生可追蹤的人員交接']},
          entertainment:{space:'personal',message:'個人娛樂提供影音互動、興趣探索與休閒陪伴，內容與推薦依個人領域權限及偏好呈現。',title:'個人娛樂',steps:['選擇影音或互動方式','探索個人興趣與內容','保存可撤回的偏好設定']},
          accounts:{space:'personal',message:'帳號綁定讓多個已驗證帳號進入同一主權 AI 封包；新增與原帳號都要登入驗證，權限仍按領域分開。',title:'帳號綁定',steps:['驗證原帳號與新增帳號','確認同一自然身分關連','開通各帳號領域入口']},
          committee:{space:'field',message:'管委會大樓功能由大廳服務台小J承接住戶服務、訪客公告、報修與公共設施資訊，正式動作依管委會角色放行。',title:'管委會大樓功能',steps:['選擇住戶、訪客或設施情境','建立公告、報修或服務候選','交由核准管理角色確認']},
          merchant:{space:'field',message:'商家會員功能由櫃台小J承接會員服務、點餐訂單、促銷與營運查詢，交易與權限仍由 Odoo 關係驗證。',title:'商家會員功能',steps:['辨識會員與服務需求','建立點餐、優惠或查詢候選','由商家角色確認交易或變更']},
          admin_operations:{space:'management',message:'管理職位工作台只對已驗證的該總場管理角色顯示；營運總覽不會授予創辦人權限或會員身分權威。',title:'管理後台 · 營運總覽',steps:['驗證總場與管理角色綁定','彙整營運指標與待處理事項','僅形成可追蹤管理候選']},
          admin_people:{space:'management',message:'人員與角色管理需逐項核對 role binding、職責範圍與變更核准，不以登入帳號自動推導管理權。',title:'管理後台 · 人員與角色',steps:['查看已核准角色關係','建立人員或權限變更候選','由有權角色複核生效']},
          admin_services:{space:'management',message:'服務配置用於調整該總場小J可見功能、營運流程與人類接手點，不可改動系統核心或創辦人治理模式。',title:'管理後台 · 服務配置',steps:['選擇該總場服務範圍','預覽流程與權限影響','由管理角色核准候選']},
          admin_review:{space:'management',message:'審核與報表集中異常、待放行事項與證據引用；管理角色只能處理被授權的總場範圍。',title:'管理後台 · 審核與報表',steps:['彙整待審與異常項目','檢查證據、風險與權限','留下可驗證的審核結果']}
        };
        const message = root.querySelector('[data-chat-message]');
        const workflowTitle = root.querySelector('[data-workflow-title]');
        const workflowSteps = [...root.querySelectorAll('[data-workflow-step]')];
        const palette = root.querySelector('[data-command-palette]');
        const commandSearch = root.querySelector('[data-command-search]');
        const spaceButtons = [...root.querySelectorAll('[data-space]')];
        const spacePanels = [...root.querySelectorAll('[data-space-panel]')];
        const defaultFunctionBySpace = {personal:'life',field:'committee',management:'admin_operations'};
        const renderSpace = (space) => {
          spaceButtons.forEach(button => {
            const selected = button.dataset.space === space;
            button.classList.toggle('is-active',selected);
            button.setAttribute('aria-selected',String(selected));
          });
          spacePanels.forEach(panel => { panel.hidden = panel.dataset.spacePanel !== space; });
        };
        const openPalette = () => {
          if (!palette.open) palette.showModal ? palette.showModal() : palette.setAttribute('open','');
          commandSearch.focus();
        };
        const activateFunction = (key) => {
          const selected = functions[key];
          if (!selected) return;
          renderSpace(selected.space);
          message.textContent = selected.message;
          workflowTitle.textContent = selected.title;
          workflowSteps.forEach((step,index) => { step.textContent = selected.steps[index]; });
          root.querySelectorAll('[data-function]').forEach(button => button.classList.toggle('is-active',button.dataset.function === key));
          if (palette.open) palette.close();
        };
        root.querySelectorAll('[data-function]').forEach(button => button.addEventListener('click',() => activateFunction(button.dataset.function)));
        spaceButtons.forEach(button => button.addEventListener('click',() => activateFunction(defaultFunctionBySpace[button.dataset.space])));
        root.querySelector('[data-command-launcher]').addEventListener('click',openPalette);
        root.querySelector('[data-command-close]').addEventListener('click',() => palette.close ? palette.close() : palette.removeAttribute('open'));
        commandSearch.addEventListener('input',() => {
          const query = commandSearch.value.trim().toLowerCase();
          root.querySelectorAll('[data-command-item]').forEach(item => { item.hidden = !item.textContent.toLowerCase().includes(query); });
        });
        document.addEventListener('keydown',(event) => {
          const targetTag = event.target?.tagName?.toLowerCase();
          const openShortcut = (event.key.toLowerCase() === 'k' && (event.ctrlKey || event.metaKey)) || (event.key === '/' && !['input','textarea'].includes(targetTag));
          if (!openShortcut) return;
          event.preventDefault();
          openPalette();
        });
        addEventListener('resize',() => select(active),{passive:true});
        select(0);
        activateFunction('life');
      })();
    """
    return f"""
    <style>{styles}</style>
    <div class="field-ui">
      <section class="hero">
        <div>
          <p class="eyebrow">Sovereign AI · XiaoJ Total Field</p>
          <h2>讓每個團體，<span>都有自己的小J總場</span></h2>
          <p class="hero-copy">{html.escape(product['summary'])}</p>
          <div class="hero-actions">
            <button class="primary-action" type="button" data-scroll="#field-types">開始選擇成立類型</button>
            <button class="secondary-action" type="button" data-scroll="#account-governance">了解帳號與權限</button>
          </div>
          <div class="proof-row" aria-label="產品關鍵原則">
            <span>4 種現實組織入口</span><span>多帳號皆可登入</span><span>領域權限明示開通</span><span>拒絕優先不自動升權</span>
          </div>
        </div>
        <div class="sovereign-orb" aria-label="小J主權AI核心示意">
          <div class="orb-ring"></div><div class="orb-ring"></div>
          <span class="orb-node n1"></span><span class="orb-node n2"></span><span class="orb-node n3"></span>
          <div class="orb-core">小J</div>
        </div>
      </section>

      <section id="field-types" class="type-selector">
        <div class="section-head">
          <div><p class="eyebrow">Choose your field</p><h3>選擇你要成立的總場</h3></div>
          <p>拖曳、滾輪或方向鍵切換。每一種外觀不同，底層影音小J能力皆由本系統供應。</p>
        </div>
        <div class="ring-shell" tabindex="0" aria-label="總場類型環狀選擇器">
          <div class="ring-stage">{type_cards}</div>
        </div>
        <div class="ring-controls">
          <button class="ring-arrow" type="button" data-ring-prev aria-label="上一個類型">←</button>
          <div class="ring-dots">{ring_dots}</div>
          <button class="ring-arrow" type="button" data-ring-next aria-label="下一個類型">→</button>
        </div>
        <p class="selection-live" aria-live="polite"></p>
      </section>

      <section id="account-governance" class="identity-command">
        <div class="section-head">
          <div><p class="eyebrow">Identity command center</p><h3>一個自然身分，多個安全入口</h3></div>
          <p>帳號可合併到同一主權 AI 8D 封包，但每個原帳號與新增帳號都必須自行登入、驗證關連並取得明示領域權限。</p>
        </div>
        <div class="bento">
          <article class="bento-card wide accent"><span class="number">01 · NATURAL IDENTITY</span><h4>自然身分是共同根，不是 D1 意圖</h4><p>所有帳號先對準同一自然身分與 D8 envelope，再成為封包入口。帳號持有不等於創辦人已核定個案。</p><div class="account-flow"><span>原帳號登入</span><b>＋</b><span>新增帳號登入</span><b>→</b><span>關連證據閉合</span><b>→</b><span>候選合併</span></div></article>
          <article class="bento-card"><span class="number">02 · LOGIN PROOF</span><h4>全帳號登入驗證</h4><p>新增帳號與原帳號缺一不可；任一登入、同人關連或同意證據缺失，整筆合併維持 HOLD。</p></article>
          <article class="bento-card"><span class="number">03 · DOMAIN RIGHTS</span><h4>權限按領域開通</h4><p>開發、商家、協會或設備管理分開綁定；不因帳號合併就聯集權限。</p></article>
          <article class="bento-card wide"><span class="number">04 · COORDINATION</span><h4>協調權限，不混成超級權限</h4><p>拒絕優先、最小權限、明示委派。權限衝突交由總場政策與人類權威決定，帳號切換不得繞過限制。</p></article>
          <article class="bento-card accent"><span class="number">05 · PRIVACY</span><h4>封包內封存，介面只見引用</h4><p>帳號識別只存在本機受保護 claim；API、Odoo 與投影輸出僅用 opaque ref 或 SHA-256，不放密碼、token 或金鑰。</p></article>
        </div>
      </section>

      <section class="journey-layout">
        <div class="journey-sticky"><p class="eyebrow">Governed journey</p><h3>看得懂，也不會誤按成立</h3><p>每一步都把「已填資料」「候選完成」「權威核准」「實際成立」分開。頁面不會因按鈕或登入自行寫入 Odoo 或啟用總場。</p></div>
        <ol class="journey">{journey_items}</ol>
      </section>

      <section class="xiaoj-guide">
        <div class="guide-copy">
          <div><p class="eyebrow">Human-first review</p><h3>三個空間，一個小J</h3></div>
          <div><p>紅隊已把多帳號接管、舊登入重播、權限合併升權、失聯帳號復原與 Odoo 權威混淆列為產品風險。紫隊方案先拒絕不完整合併，再以明示證據逐項解鎖。</p><div class="gap-cloud">{gap_items}</div></div>
        </div>
        <div class="space-switcher" role="tablist" aria-label="小J工作空間">
          <button class="is-active" type="button" role="tab" aria-selected="true" data-space="personal">個人小J</button>
          <button type="button" role="tab" aria-selected="false" data-space="field">團體服務</button>
          <button type="button" role="tab" aria-selected="false" data-space="management">管理職位 <small>需角色驗證</small></button>
        </div>
        <div class="xiaoj-workspace">
          <aside class="guide-chat" aria-label="小J功能工作流">
            <div class="chat-head"><span class="chat-avatar">J</span><span>小J 對話工作區</span><span class="chat-status">● 候選模式</span><button class="command-launcher" type="button" data-command-launcher aria-label="搜尋小J功能">搜尋 <kbd>⌘K</kbd></button></div>
            <p class="chat-message" data-chat-message>你好，請從功能星圖選擇大項目；我會在對話內展開對應工作流，不會自行送出或寫入。</p>
            <div class="workflow-preview" aria-live="polite"><small>CONTEXTUAL WORKFLOW</small><h4 data-workflow-title>總場成立與分身</h4><ol><li data-workflow-step>選擇現實組織類型</li><li data-workflow-step>準備問卷或親訪設計</li><li data-workflow-step>核對創辦人核定與成立效果</li></ol></div>
          </aside>
          <nav class="function-orbit" data-space-panel="personal" aria-label="個人小J功能類別">
            <span class="orbit-core" aria-hidden="true">小J</span>
            <button class="orbit-action n1 is-active" type="button" data-function="life">生活輔助</button>
            <button class="orbit-action n2" type="button" data-function="work">工作協作</button>
            <button class="orbit-action n3" type="button" data-function="entertainment">個人娛樂</button>
            <button class="orbit-action n4" type="button" data-function="accounts">帳號綁定</button>
          </nav>
          <nav class="function-orbit" data-space-panel="field" aria-label="團體服務功能類別" hidden>
            <span class="orbit-core" aria-hidden="true">場</span>
            <button class="orbit-action n2" type="button" data-function="committee">管委會大樓</button>
            <button class="orbit-action n4" type="button" data-function="merchant">商家會員</button>
          </nav>
          <nav class="function-orbit" data-space-panel="management" aria-label="管理職位後台功能" hidden>
            <span class="orbit-core" aria-hidden="true">管</span>
            <button class="orbit-action n1" type="button" data-function="admin_operations">營運總覽</button>
            <button class="orbit-action n2" type="button" data-function="admin_people">人員角色</button>
            <button class="orbit-action n3" type="button" data-function="admin_services">服務配置</button>
            <button class="orbit-action n4" type="button" data-function="admin_review">審核報表</button>
          </nav>
        </div>
        <dialog class="command-palette" data-command-palette aria-label="搜尋小J功能">
          <div class="command-shell">
            <div class="command-top"><input class="command-search" type="search" data-command-search placeholder="搜尋功能或大項目，例如：帳號、總場、設備"><button class="command-close" type="button" data-command-close aria-label="關閉功能搜尋">×</button></div>
            <div class="command-list">
              <button type="button" data-command-item data-function="life"><span>生</span><span><strong>生活輔助</strong><small>日程、提醒、日常資訊與個人習慣</small></span></button>
              <button type="button" data-command-item data-function="work"><span>工</span><span><strong>工作協作</strong><small>任務、文件、會議與團隊交接</small></span></button>
              <button type="button" data-command-item data-function="entertainment"><span>樂</span><span><strong>個人娛樂</strong><small>影音互動、興趣探索與休閒陪伴</small></span></button>
              <button type="button" data-command-item data-function="accounts"><span>帳</span><span><strong>帳號綁定</strong><small>多帳號登入、自然身分關連與領域入口</small></span></button>
              <button type="button" data-command-item data-function="committee"><span>寓</span><span><strong>管委會大樓功能</strong><small>住戶服務、訪客公告、報修與公共設施</small></span></button>
              <button type="button" data-command-item data-function="merchant"><span>店</span><span><strong>商家會員功能</strong><small>會員服務、點餐訂單、促銷與營運</small></span></button>
              <button type="button" data-command-item data-function="admin_operations"><span>總</span><span><strong>管理職位後台</strong><small>營運總覽、人員角色、服務配置、審核報表</small></span></button>
            </div>
          </div>
        </dialog>
      </section>

      <section class="trust-panel">
        <div><p class="eyebrow">Trust contract</p><h3>你的身分與權利，不被介面偷換</h3></div>
        <ul class="trust-list">{trust_items}</ul>
      </section>
      <div class="candidate-band"><strong>產品級 UI 候選已形成</strong><span>無 Odoo 寫入 · 無封包變更 · 無帳號合併 · 無權限開通 · 無總場成立</span></div>
    </div>
    <script>{script}</script>
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
        return _page("上品聊國咖啡館重新總店", ROUTE_STATE["xiaoj_ordering"], _ordering_body(), payload, page_class="cafe-store")

    @http.route("/wuchang/xiaoj/display", type="http", auth="public", csrf=False)
    def xiaoj_display(self, **_kwargs):
        return _xiaoj_display_page()

    @http.route("/wuchang/xiaoj/api/store-chat", type="json", auth="public", csrf=False)
    def xiaoj_store_chat(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        config = http.request.env["ir.config_parameter"].sudo()
        return build_storefront_response(
            params.get("text") or params.get("transcript") or "",
            model_endpoint=config.get_param(
                "wuchang_cafe_ai_gateway.storefront_model_endpoint",
                "http://wuchang_gpu_brain:11434/api/generate",
            ),
            model=config.get_param(
                "wuchang_cafe_ai_gateway.storefront_model",
                "gemma3:4b",
            ),
            use_model=False,
        )

    @http.route("/wuchang/xiaoj/api/store-flair", type="json", auth="public", csrf=False)
    def xiaoj_store_flair(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        config = http.request.env["ir.config_parameter"].sudo()
        return build_storefront_flair(
            params.get("text") or params.get("transcript") or "",
            model_endpoint=config.get_param(
                "wuchang_cafe_ai_gateway.storefront_model_endpoint",
                "http://wuchang_gpu_brain:11434/api/generate",
            ),
            model=config.get_param(
                "wuchang_cafe_ai_gateway.storefront_model",
                "gemma3:4b",
            ),
        )

    @http.route("/wuchang/xiaoj/api/store-confirm", type="json", auth="public", csrf=False)
    def xiaoj_store_confirm(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        return confirm_storefront_preview(
            params.get("text") or params.get("transcript") or "",
            params.get("preview_ref"),
            params.get("acknowledged"),
            params.get("voice_readback_completed"),
        )

    @http.route("/wuchang/xiaoj/group-member-field-application", type="http", auth="user")
    def xiaoj_group_member_field_application(self, **_kwargs):
        product = build_group_member_total_field_product_candidate()
        payload = json.dumps(product, ensure_ascii=False, indent=2)
        return _page(
            "小J 主權總場申請",
            "產品級候選 · 無執行效果",
            _group_member_field_product_body(),
            payload,
            page_class="field-product",
        )

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

    @http.route("/wuchang/xiaoj/api/merchant-capabilities", type="json", auth="user", csrf=False)
    def xiaoj_api_merchant_capabilities(self, **_kwargs):
        return build_merchant_capability_catalog()

    @http.route("/wuchang/xiaoj/api/merchant-action-candidate", type="json", auth="user", csrf=False)
    def xiaoj_api_merchant_action_candidate(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        return plan_merchant_action(
            capability_code=params.get("capability_code"),
            text=params.get("text") or params.get("transcript"),
            actor_ref=params.get("actor_ref"),
            actor_role=params.get("actor_role") or "service_agent",
            total_field_ref=params.get("total_field_ref"),
            mode_ref=params.get("mode_ref"),
            appearance_profile_ref=params.get("appearance_profile_ref"),
            parameters=params.get("parameters") or {},
        )

    @http.route("/wuchang/xiaoj/api/core-capabilities", type="json", auth="user", csrf=False)
    def xiaoj_api_core_capabilities(self, **_kwargs):
        return build_xiaoj_core_supply_contract()

    @http.route("/wuchang/xiaoj/api/field-projection-candidate", type="json", auth="user", csrf=False)
    def xiaoj_api_field_projection_candidate(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        return plan_xiaoj_field_projection(
            projection_kind=params.get("projection_kind"),
            total_field_ref=params.get("total_field_ref"),
            mode_ref=params.get("mode_ref"),
            appearance_profile_ref=params.get("appearance_profile_ref"),
            odoo_relationship_ref=params.get("odoo_relationship_ref"),
            group_member_application_ref=params.get("group_member_application_ref"),
            personal_identity_packet_ref=params.get("personal_identity_packet_ref"),
            identity_packet_active_evidence_ref=params.get("identity_packet_active_evidence_ref"),
            association_group_member_approval_evidence_ref=params.get(
                "association_group_member_approval_evidence_ref"
            ),
            founder_establishment_approval_evidence_ref=params.get(
                "founder_establishment_approval_evidence_ref"
            ),
            founder_account_packet_binding_evidence_ref=params.get(
                "founder_account_packet_binding_evidence_ref"
            ),
            founder_personal_visit_design_evidence_ref=params.get(
                "founder_personal_visit_design_evidence_ref"
            ),
            intent_field_questionnaire_ref=params.get("intent_field_questionnaire_ref"),
            questionnaire_real_world_usability_evidence_ref=params.get(
                "questionnaire_real_world_usability_evidence_ref"
            ),
        )

    @http.route("/wuchang/xiaoj/api/group-member-intent-field-questionnaire", type="json", auth="user", csrf=False)
    def xiaoj_api_group_member_intent_field_questionnaire(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        return build_group_member_intent_field_questionnaire(
            field_type=params.get("field_type") or params.get("projection_kind")
        )

    @http.route("/wuchang/xiaoj/api/group-member-field-product-candidate", type="json", auth="user", csrf=False)
    def xiaoj_api_group_member_field_product_candidate(self, **_kwargs):
        return build_group_member_total_field_product_candidate()

    @http.route("/wuchang/xiaoj/api/group-member-field-application-entry", type="json", auth="user", csrf=False)
    def xiaoj_api_group_member_field_application_entry(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        return build_group_member_field_application_entry(
            personal_identity_packet_ref=params.get("personal_identity_packet_ref"),
            account_entry_binding_ref=params.get("account_entry_binding_ref"),
            account_domain_permission_ref=params.get("account_domain_permission_ref"),
        )

    @http.route("/wuchang/xiaoj/api/group-member-field-application-candidate", type="json", auth="user", csrf=False)
    def xiaoj_api_group_member_field_application_candidate(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        return plan_group_member_total_field_application(
            projection_kind=params.get("projection_kind"),
            group_member_ref=params.get("group_member_ref"),
            personal_identity_packet_ref=params.get("personal_identity_packet_ref"),
            identity_packet_active_evidence_ref=params.get("identity_packet_active_evidence_ref"),
            account_entry_binding_ref=params.get("account_entry_binding_ref"),
            account_domain_permission_ref=params.get("account_domain_permission_ref"),
            association_group_member_approval_evidence_ref=params.get(
                "association_group_member_approval_evidence_ref"
            ),
            odoo_relationship_ref=params.get("odoo_relationship_ref"),
            requested_total_field_ref=params.get("requested_total_field_ref"),
            intent_field_questionnaire_ref=params.get("intent_field_questionnaire_ref"),
            questionnaire_real_world_usability_evidence_ref=params.get(
                "questionnaire_real_world_usability_evidence_ref"
            ),
        )

    @http.route("/wuchang/xiaoj/api/sovereign-ai-account-binding-candidate", type="json", auth="user", csrf=False)
    def xiaoj_api_sovereign_ai_account_binding_candidate(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        return plan_sovereign_ai_multi_account_binding(
            sovereign_ai_packet_ref=params.get("sovereign_ai_packet_ref"),
            natural_identity_ref=params.get("natural_identity_ref"),
            account_bindings=params.get("account_bindings"),
            permission_coordination_policy_ref=params.get(
                "permission_coordination_policy_ref"
            ),
            physical_identity_root_evidence_ref=params.get(
                "physical_identity_root_evidence_ref"
            ),
            total_field_authority_ref=params.get("total_field_authority_ref"),
        )

    @http.route("/wuchang/xiaoj/api/sovereign-ai-account-governance-candidate", type="json", auth="user", csrf=False)
    def xiaoj_api_sovereign_ai_account_governance_candidate(self, **_kwargs):
        return build_sovereign_ai_multi_account_governance_candidate()

    @http.route("/wuchang/xiaoj/api/local-secret-request-candidate", type="json", auth="user", csrf=False)
    def xiaoj_api_local_secret_request_candidate(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        return plan_local_trade_secret_request(
            approved_device_ref=params.get("approved_device_ref"),
            device_approval_evidence_ref=params.get("device_approval_evidence_ref"),
            total_field_ref=params.get("total_field_ref"),
            request_policy_ref=params.get("request_policy_ref"),
            purpose_scope_ref=params.get("purpose_scope_ref"),
            time_window_ref=params.get("time_window_ref"),
            secret_scope_ref=params.get("secret_scope_ref"),
        )

    @http.route("/wuchang/xiaoj/api/device-admission-candidate", type="json", auth="user", csrf=False)
    def xiaoj_api_device_admission_candidate(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        return plan_distributed_device_admission(
            device_ref=params.get("device_ref"),
            device_capability_manifest_ref=params.get("device_capability_manifest_ref"),
            total_field_ref=params.get("total_field_ref"),
            founder_approval_evidence_ref=params.get("founder_approval_evidence_ref"),
            association_approved_identity_packet_ref=params.get(
                "association_approved_identity_packet_ref"
            ),
        )

    @http.route("/wuchang/xiaoj/api/template-application-candidate", type="json", auth="user", csrf=False)
    def xiaoj_api_template_application_candidate(self, **kwargs):
        params = _request_params()
        params.update(kwargs)
        return plan_founder_base_template_application(
            requesting_device_ref=params.get("requesting_device_ref"),
            founder_base_device_ref=params.get("founder_base_device_ref"),
            founder_base_device_authority_evidence_ref=params.get(
                "founder_base_device_authority_evidence_ref"
            ),
            total_field_ref=params.get("total_field_ref"),
            mode_ref=params.get("mode_ref"),
            template_ref=params.get("template_ref"),
            target_projection_ref=params.get("target_projection_ref"),
            target_identity_packet_ref=params.get("target_identity_packet_ref"),
            target_field_type=params.get("target_field_type"),
            template_origin=params.get("template_origin"),
            founder_personal_visit_design_evidence_ref=params.get(
                "founder_personal_visit_design_evidence_ref"
            ),
        )
