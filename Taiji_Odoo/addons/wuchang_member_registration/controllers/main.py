import html
import json

from odoo import fields, http
from odoo.http import request


class WuchangMemberRegistrationController(http.Controller):

    def _request_payload(self, kw):
        params = {}
        params.update(getattr(request, "params", {}) or {})
        json_request = getattr(request, "jsonrequest", None)
        if isinstance(json_request, dict):
            params.update(json_request)
        params.update(kw)
        return params

    def _wuchang_public_homepage_html(self):
        return """<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>五常社區發展協會 | 聊國咖啡館重新總店</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #17202a;
      --muted: #566573;
      --line: #d8dee7;
      --paper: #fffdf7;
      --cream: #f6f1e5;
      --green: #315b48;
      --gold: #b9822b;
      --red: #9b2f2f;
      --blue: #235789;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans TC", sans-serif;
      background: var(--paper);
      color: var(--ink);
      line-height: 1.65;
    }
    a { color: inherit; text-decoration: none; }
    .hero {
      min-height: 74vh;
      display: grid;
      align-items: end;
      background:
        linear-gradient(180deg, rgba(15, 34, 29, .35), rgba(15, 34, 29, .82)),
        radial-gradient(circle at 70% 15%, rgba(255, 225, 160, .28), transparent 34%),
        linear-gradient(135deg, #2d4f43, #1b2d37 58%, #5b3529);
      color: #fff;
      padding: 38px clamp(20px, 5vw, 72px);
    }
    .hero-inner { max-width: 1120px; width: 100%; }
    .kicker {
      display: inline-flex;
      gap: 10px;
      flex-wrap: wrap;
      color: #f8e5b8;
      font-size: 15px;
      letter-spacing: .04em;
      margin-bottom: 18px;
    }
    h1 {
      margin: 0;
      max-width: 900px;
      font-size: clamp(36px, 5vw, 64px);
      line-height: 1.08;
      letter-spacing: 0;
    }
    .lead {
      max-width: 820px;
      margin: 24px 0 30px;
      font-size: clamp(18px, 2.2vw, 24px);
      color: #fff8e8;
    }
    .actions { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 18px; }
    .button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 48px;
      padding: 11px 20px;
      border-radius: 8px;
      font-weight: 700;
      border: 1px solid rgba(255,255,255,.38);
      background: rgba(255,255,255,.12);
    }
    .button.primary {
      background: #fff8e8;
      border-color: #fff8e8;
      color: #22352e;
    }
    .section {
      padding: 56px clamp(20px, 5vw, 72px);
      border-top: 1px solid var(--line);
    }
    .section:nth-child(odd) { background: var(--cream); }
    .wrap { max-width: 1120px; margin: 0 auto; }
    h2 {
      margin: 0 0 20px;
      font-size: clamp(26px, 3.4vw, 40px);
      line-height: 1.2;
      letter-spacing: 0;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
    }
    .panel {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      padding: 22px;
      min-height: 100%;
    }
    .panel strong { display: block; color: var(--green); font-size: 18px; margin-bottom: 8px; }
    .panel p { margin: 0; color: var(--muted); }
    .split {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 28px;
      align-items: start;
    }
    .plain-list {
      display: grid;
      gap: 12px;
      margin: 0;
      padding: 0;
      list-style: none;
    }
    .plain-list li {
      border-left: 4px solid var(--gold);
      background: rgba(255,255,255,.72);
      padding: 12px 14px;
    }
    .notice {
      border: 1px solid #e6ccb2;
      background: #fff7eb;
      border-radius: 8px;
      padding: 18px;
      color: #5b4122;
    }
    .facts {
      width: 100%;
      border-collapse: collapse;
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      display: table;
    }
    .facts th, .facts td {
      text-align: left;
      vertical-align: top;
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
    }
    .facts th {
      width: 210px;
      color: var(--green);
      background: #f8faf8;
    }
    .facts tr:last-child th, .facts tr:last-child td { border-bottom: 0; }
    footer {
      padding: 34px clamp(20px, 5vw, 72px);
      background: #17202a;
      color: #e9edf1;
    }
    footer .wrap { display: flex; gap: 12px; justify-content: space-between; flex-wrap: wrap; }
    @media (max-width: 860px) {
      .grid, .split { grid-template-columns: 1fr; }
      .facts, .facts tbody, .facts tr, .facts th, .facts td { display: block; width: 100%; }
      .facts th { border-bottom: 0; padding-bottom: 4px; }
    }
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div class="hero-inner">
        <div class="kicker">
          <span>新北市三重區五常社區發展協會</span>
          <span>×</span>
          <span>聊國咖啡館重新總店</span>
        </div>
        <h1>先看清主體，再註冊使用。</h1>
        <p class="lead">這個網站服務五常社區的公益治理、會員參與與咖啡館現場營運。協會是社區治理主體；上品食品行與聊國咖啡館重新總店是外部友軍、營運與技術支援窗口。</p>
        <div class="actions">
          <a class="button primary" href="/web/login">店員/店長登入</a>
          <a class="button" href="/web/signup">會員註冊</a>
          <a class="button" href="/line/login">LINE 會員入口</a>
          <a class="button" href="/google/member/login">Google 會員入口</a>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="wrap">
        <h2>誰是主體</h2>
        <div class="grid">
          <article class="panel">
            <strong>公益治理主體</strong>
            <p>新北市三重區五常社區發展協會，負責社區公益、會員治理、志工與公共服務規則。</p>
          </article>
          <article class="panel">
            <strong>營運與技術支援</strong>
            <p>上品食品行／聊國咖啡館重新總店作為外部友軍與開發支援窗口，協助店內營運、Odoo POS 與數位計畫落地。</p>
          </article>
          <article class="panel">
            <strong>分窗原則</strong>
            <p>商業營運、公益基金、會員資料與技術帳號分窗管理，不混帳、不混權限、不把公益敘事當作商業背書。</p>
          </article>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="wrap split">
        <div>
          <h2>為什麼做這個網站</h2>
          <ul class="plain-list">
            <li>讓居民、志工、店員與店長能在同一個清楚入口找到對應服務。</li>
            <li>讓協會的社區互愛互助精神進入可追蹤、可稽核、可交接的數位治理。</li>
            <li>讓咖啡館先恢復現場營運與現金流，再支持協會長期設備與公益服務。</li>
            <li>讓小J與總場 AI 只做輔助、提示與驗證，不取代人類授權與協會治理。</li>
          </ul>
        </div>
        <div class="notice">
          <strong>公開敘事邊界</strong>
          <p>本頁不宣稱 Google、LINE 或任何平台背書本系統；也不宣稱協會已收到特定開發費、加盟費、訓練費，除非日後有正式入帳憑證與公開佐證。</p>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="wrap">
        <h2>現在有什麼</h2>
        <table class="facts" aria-label="目前服務">
          <tr><th>店內營運</th><td>店員與店長可透過 Odoo 入口進入後台與 POS；現金收款是目前優先恢復的營運路徑。</td></tr>
          <tr><th>會員入口</th><td>提供一般註冊入口，LINE 與 Google 會員入口已保留路由，正式 OAuth 值與 callback 測試需完成後才開放正式串接。</td></tr>
          <tr><th>AI 總場</th><td>使用 D8 / W7TP 總場規則保存證據、權限、風險與行動邊界；AI 只能輔助，不能私自下單、付款或讀取會員明文。</td></tr>
          <tr><th>語言輔助</th><td>首頁與操作設計以中文為主，後續可支援英文、越文輔助，方便店長與店員實際使用。</td></tr>
        </table>
      </div>
    </section>

    <section class="section">
      <div class="wrap">
        <h2>未來要做到什麼</h2>
        <div class="grid">
          <article class="panel">
            <strong>社區 AI 主權服務</strong>
            <p>以協會治理為中心，建立居民、志工、商家與管委會的服務入口。</p>
          </article>
          <article class="panel">
            <strong>越文友善店務</strong>
            <p>配合越南籍店長與現場店員，將 POS、點餐與複誦確認流程做成更接近人類工作的介面。</p>
          </article>
          <article class="panel">
            <strong>公益設備升級</strong>
            <p>待營收與正式治理條件成立後，推動協會自有設備、長期 vault 與封存遷移，不把咖啡店機器當永久協會主機。</p>
          </article>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="wrap">
        <h2>贊助、技術與補助獎項</h2>
        <table class="facts" aria-label="贊助與技術">
          <tr><th>友軍支持</th><td>上品食品行／聊國咖啡館重新總店提供店內營運與技術支援，作為協會數位計畫的外部友軍窗口。</td></tr>
          <tr><th>技術基礎</th><td>Odoo POS、W7TP / D8 總場治理、小J AI 輔助、Google Workspace 架構、Google 非營利組織認證相關資格、Google Maps 非營利額度規劃與無明文資料邊界。</td></tr>
          <tr><th>公益承諾</th><td>開發費、加盟費、訓練費等公益支持敘事，須以正式憑證、會計分窗與人審後再公開列示。</td></tr>
          <tr><th>補助、計畫與獎項</th><td>已有人審補充「Google 非營利組織認證」、「社區一家社區營造徵件計畫」、「文化局一般型補助」、「新北市社會局社區營造工作補助」等公益數位化與社區營造脈絡；目前首頁先標示為佐證待補，相關平台資格僅用於公益數位化說明，不作為商品、POS 或商業營收背書，也不宣稱未具文件的補助核定或獎項。待核定文件、核銷資料、獎項證書或公開照片完成佐證後再更新。</td></tr>
        </table>
      </div>
    </section>
  </main>
  <footer>
    <div class="wrap">
      <span>五常社區發展協會公益治理入口</span>
      <span>聊國咖啡館重新總店營運支援</span>
    </div>
  </footer>
</body>
</html>"""

    @http.route(["/", "/wuchang/home"], type="http", auth="public", website=False, csrf=False)
    def wuchang_public_homepage(self, **kw):
        return request.make_response(
            self._wuchang_public_homepage_html(),
            headers=[("Content-Type", "text/html; charset=utf-8")],
        )

    @http.route("/wuchang/member/register/start", type="json", auth="public", csrf=False)
    def start_registration(self, channel="odoo", consent_version="v1", **kw):
        allowed = {"line", "google", "odoo", "pwa", "staff_terminal"}
        if channel not in allowed:
            channel = "odoo"

        reg = request.env["wuchang.member.registration"].sudo().create({
            "registration_channel": channel,
            "consent_version": consent_version or "v1",
            "review_status": "draft",
        })
        return {
            "status": "provisional_created",
            "provisional_member_id": reg.provisional_member_id,
            "review_status": reg.review_status,
            "next": "submit_minimum_review_data",
        }

    @http.route("/wuchang/member/register/status/<string:provisional_member_id>", type="json", auth="public", csrf=False)
    def registration_status(self, provisional_member_id, **kw):
        reg = request.env["wuchang.member.registration"].sudo().search([
            ("provisional_member_id", "=", provisional_member_id)
        ], limit=1)
        if not reg:
            return {"status": "not_found"}
        return {
            "status": "found",
            "provisional_member_id": reg.provisional_member_id,
            "review_status": reg.review_status,
            "member_code_available": bool(reg.identity_code_id),
        }

    def _create_business_onboarding(self, params):
        organization_name = (
            params.get("organization_name")
            or params.get("business_name")
            or "上品聊國咖啡館"
        )
        registration_channel = params.get("registration_channel") or "odoo"
        if registration_channel not in {"line", "google", "odoo", "pwa", "staff_terminal"}:
            registration_channel = "odoo"

        responsible = request.env["wuchang.member.registration"].sudo().create({
            "registration_channel": registration_channel,
            "review_status": "pending_review",
            "consent_version": params.get("consent_version") or "business_onboarding_v1",
            "review_name_hint": params.get("responsible_name_hint") or "",
            "review_contact_hint": params.get("responsible_contact_hint") or "",
            "member_type": "organization",
            "organization_name": organization_name,
            "organization_role": "responsible_person",
            "membership_category": "business_organization",
            "role_scope": "responsible_person",
            "service_scope": "cafe_business_onboarding",
        })

        batch = request.env["wuchang.member.group.registration.batch"].sudo().create({
            "name": organization_name,
            "topology_ref": "merchant/cafe/business_onboarding",
            "registration_scope": "cafe_business_onboarding",
            "expires_at": fields.Datetime.add(fields.Datetime.now(), days=30),
            "business_onboarding_enabled": True,
            "business_onboarding_state": "draft",
            "responsible_registration_id": responsible.id,
            "responsible_person_ref": responsible.provisional_member_id,
            "responsible_role": params.get("responsible_role") or "responsible_person",
            "business_name": params.get("business_name") or organization_name,
            "business_ref": params.get("business_ref") or "business_ref:pending",
            "business_address_ref": params.get("business_address_ref") or "",
            "business_registration_ref": params.get("business_registration_ref") or "",
            "store_name": params.get("store_name") or organization_name,
            "store_ref": params.get("store_ref") or "store_ref:pending",
            "service_area_ref": params.get("service_area_ref") or "service_area_ref:local",
            "service_items_json": (
                params.get("service_items_json")
                or '["cafe_menu", "member_service", "line_ai_response", "odoo_pos_management"]'
            ),
            "line_official_account_ref": params.get("line_official_account_ref") or "",
            "odoo_service_ref": params.get("odoo_service_ref") or "",
            "pos_config_ref": params.get("pos_config_ref") or "",
        })
        if batch.business_ref == "business_ref:pending":
            batch.business_ref = "business_ref:" + batch.group_ref
        if batch.store_ref == "store_ref:pending":
            batch.store_ref = "store_ref:" + batch.group_ref
        batch.action_submit_business_onboarding()
        return responsible, batch

    @http.route("/wuchang/business/onboarding", type="http", auth="public", website=False, csrf=False)
    def business_onboarding_form(self, **kw):
        body = """<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>商家組織註冊</title>
  <style>
    body { margin: 0; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; background: #f7f9fb; color: #17202a; }
    main { max-width: 880px; margin: 0 auto; padding: 32px 20px; }
    form { display: grid; gap: 14px; background: #fff; border: 1px solid #d8dee7; padding: 20px; border-radius: 8px; }
    label { display: grid; gap: 6px; font-weight: 700; }
    input, textarea, select { min-height: 42px; border: 1px solid #cbd5df; border-radius: 6px; padding: 9px 10px; font: inherit; }
    textarea { min-height: 82px; }
    button { min-height: 46px; border: 0; border-radius: 6px; background: #235789; color: #fff; font-weight: 800; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    .note { background: #fff7e6; border: 1px solid #ead19a; padding: 12px; border-radius: 8px; color: #5c4617; margin: 14px 0; }
    @media (max-width: 760px) { .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
<main>
  <h1>商家組織註冊</h1>
  <p>自然人先作為負責人或授權管理者建立商家組織；經總場核准後，才形成營運入口與服務設定。</p>
  <div class="note">送出會建立待審申請，不會直接下單、扣款、部署、重啟或修改 router。</div>
  <form method="post" action="/wuchang/business/onboarding/submit">
    <div class="grid">
      <label>負責人名稱提示<input name="responsible_name_hint" required></label>
      <label>負責人聯絡提示<input name="responsible_contact_hint" required></label>
    </div>
    <label>商家組織名稱<input name="organization_name" value="上品聊國咖啡館" required></label>
    <div class="grid">
      <label>營業名稱<input name="business_name" value="上品聊國咖啡館" required></label>
      <label>營業地址 ref<input name="business_address_ref" placeholder="address_ref:..." required></label>
    </div>
    <div class="grid">
      <label>門市名稱<input name="store_name" value="上品聊國咖啡館" required></label>
      <label>服務區域 ref<input name="service_area_ref" value="service_area_ref:local" required></label>
    </div>
    <label>服務項目 JSON<textarea name="service_items_json">["cafe_menu", "member_service", "line_ai_response", "odoo_pos_management"]</textarea></label>
    <div class="grid">
      <label>LINE 官方帳號 ref<input name="line_official_account_ref" placeholder="line_oa_ref:..." required></label>
      <label>Odoo 服務 ref<input name="odoo_service_ref" placeholder="odoo_service_ref:..." required></label>
    </div>
    <label>POS 設定 ref<input name="pos_config_ref" placeholder="pos_config_ref:..." required></label>
    <button type="submit">建立商家 onboarding 申請</button>
  </form>
</main>
</body>
</html>"""
        return request.make_response(body, headers=[("Content-Type", "text/html; charset=utf-8")])

    @http.route("/wuchang/business/onboarding/submit", type="http", auth="public", methods=["POST"], csrf=False)
    def business_onboarding_submit(self, **kw):
        try:
            _responsible, batch = self._create_business_onboarding(self._request_payload(kw))
        except Exception as exc:
            return request.make_response(
                "Business onboarding failed: %s" % exc,
                status=400,
                headers=[("Content-Type", "text/plain; charset=utf-8")],
            )
        return request.redirect(f"/wuchang/business/onboarding/result/{batch.packet_ref}")

    @http.route("/wuchang/business/onboarding/start", type="json", auth="public", csrf=False)
    def business_onboarding_start(self, **kw):
        try:
            responsible, batch = self._create_business_onboarding(self._request_payload(kw))
        except Exception as exc:
            return {"state": "HOLD_BUSINESS_ONBOARDING_INPUT", "error": str(exc)}
        payload = batch.business_onboarding_status_payload()
        payload.update({
            "state": "BUSINESS_ONBOARDING_CREATED",
            "responsible_provisional_member_id": responsible.provisional_member_id,
            "next": "total_field_review_then_operational_ready",
        })
        return payload

    @http.route("/wuchang/business/onboarding/status/<string:packet_ref>", type="json", auth="public", csrf=False)
    def business_onboarding_status(self, packet_ref, **kw):
        batch = request.env["wuchang.member.group.registration.batch"].sudo().search([
            ("packet_ref", "=", packet_ref),
            ("business_onboarding_enabled", "=", True),
        ], limit=1)
        if not batch:
            return {"status": "not_found"}
        return batch.business_onboarding_status_payload()

    @http.route("/wuchang/business/onboarding/result/<string:packet_ref>", type="http", auth="public", csrf=False)
    def business_onboarding_result(self, packet_ref, **kw):
        payload = self.business_onboarding_status(packet_ref, **kw)
        text = html.escape(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        body = "<html><body><h1>Business onboarding status</h1><pre>%s</pre></body></html>" % text
        return request.make_response(body, headers=[("Content-Type", "text/html; charset=utf-8")])

    @http.route("/wuchang/business/onboarding/<string:packet_ref>/approve", type="json", auth="user", csrf=False)
    def business_onboarding_approve(self, packet_ref, **kw):
        batch = request.env["wuchang.member.group.registration.batch"].sudo().search([
            ("packet_ref", "=", packet_ref),
            ("business_onboarding_enabled", "=", True),
        ], limit=1)
        if not batch:
            return {"state": "not_found"}
        batch.action_total_field_approve_business_onboarding()
        payload = batch.business_onboarding_status_payload()
        payload["state"] = "BUSINESS_ONBOARDING_OPERATIONAL_READY"
        return payload

    def _find_group_batch(self, packet_ref):
        return request.env["wuchang.member.group.registration.batch"].sudo().search([
            ("packet_ref", "=", packet_ref)
        ], limit=1)

    @http.route("/wuchang/member/register/group/<string:packet_ref>", type="http", auth="public", csrf=False)
    def group_registration_entry(self, packet_ref, **kw):
        batch = self._find_group_batch(packet_ref)
        if not batch:
            return request.make_response("Group registration packet not found.", status=404)
        request.session["wuchang_group_packet_ref"] = packet_ref
        body = """
        <html><body>
          <h1>Group member registration</h1>
          <p>Group: %(group)s</p>
          <p>State: %(state)s</p>
          <p>D8 Ref: %(d8)s</p>
          <p><a href="/google/member/login?group_packet_ref=%(packet)s">Continue with Google</a></p>
          <p><a href="/line/login?group_packet_ref=%(packet)s">Continue with LINE</a></p>
          <form method="post" action="/wuchang/member/register/group/%(packet)s/claim">
            <input type="hidden" name="provider" value="manual"/>
            <button type="submit">Create provisional group registration</button>
          </form>
        </body></html>
        """ % {
            "group": batch.name,
            "state": batch.state,
            "d8": batch.d8_ref,
            "packet": packet_ref,
        }
        return request.make_response(body, headers=[("Content-Type", "text/html; charset=utf-8")])

    @http.route("/wuchang/member/register/group/<string:packet_ref>/claim", type="http", auth="public", methods=["POST"], csrf=False)
    def group_registration_claim(self, packet_ref, **kw):
        batch = self._find_group_batch(packet_ref)
        if not batch:
            return request.make_response("Group registration packet not found.", status=404)
        auth_ref = request.session.get("wuchang_group_auth_ref") or {}
        provider = auth_ref.get("provider") or kw.get("provider") or "manual"
        provider_user_ref = auth_ref.get("provider_user_ref") or kw.get("provider_user_ref")
        display_ref = auth_ref.get("display_ref") or "masked"
        packet = request.env["wuchang.member.group.registration.packet"].sudo().create_from_group_claim(
            batch,
            provider=provider,
            provider_user_ref=provider_user_ref,
            display_ref=display_ref,
        )
        request.session["wuchang_group_registration_packet_ref"] = packet.packet_ref
        return request.redirect(f"/wuchang/member/register/group/{packet_ref}/status")

    @http.route("/wuchang/member/register/group/<string:packet_ref>/confirm_dry_run", type="json", auth="public", csrf=False)
    def group_registration_confirm_dry_run(self, packet_ref, **kw):
        batch = self._find_group_batch(packet_ref)
        if not batch:
            return {"state": "not_found"}
        member_packet_ref = kw.get("member_packet_ref") or request.session.get("wuchang_group_registration_packet_ref")
        packet = request.env["wuchang.member.group.registration.packet"].sudo().search([
            ("batch_id", "=", batch.id),
            ("packet_ref", "=", member_packet_ref),
        ], limit=1)
        if not packet:
            return {"state": "packet_not_found"}
        return packet.action_confirm_dry_run()

    @http.route("/wuchang/member/register/group/<string:packet_ref>/status", type="http", auth="public", csrf=False)
    def group_registration_status(self, packet_ref, **kw):
        batch = self._find_group_batch(packet_ref)
        if not batch:
            return request.make_response("Group registration packet not found.", status=404)
        member_packet_ref = kw.get("member_packet_ref") or request.session.get("wuchang_group_registration_packet_ref")
        packet = request.env["wuchang.member.group.registration.packet"].sudo().search([
            ("batch_id", "=", batch.id),
            ("packet_ref", "=", member_packet_ref),
        ], limit=1) if member_packet_ref else request.env["wuchang.member.group.registration.packet"].sudo()
        payload = {
            "status": "found",
            "group_ref": batch.group_ref,
            "batch_state": batch.state,
            "packet_ref": packet.packet_ref if packet else False,
            "packet_state": packet.state if packet else "not_claimed",
            "d8_ref": packet.d8_ref if packet else batch.d8_ref,
            "formal_db_write": False,
            "formal_pos_write": False,
            "payment_capture": False,
            "service_restart": False,
            "deploy": False,
            "production_release": False,
        }
        return request.make_json_response(payload)
