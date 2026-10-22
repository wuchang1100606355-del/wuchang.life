import html
import json

from odoo import fields, http
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.exceptions import UserError
from odoo.http import request


INDIVIDUAL_JURISDICTION_CATEGORIES = {
    "in_community_jurisdiction",
    "outside_community_jurisdiction",
}


class WuchangMemberSignupController(AuthSignupHome):
    def get_auth_signup_qcontext(self):
        qcontext = super().get_auth_signup_qcontext()
        for key in ("member_type", "organization_name", "membership_category"):
            qcontext[key] = request.params.get(key) or ""
        return qcontext

    def do_signup(self, qcontext):
        if not request.env["wuchang.community.feature.gate"].is_landing_enabled(
            "member_registration"
        ):
            raise UserError("會員註冊目前暫停受理。")

        member_type = str(qcontext.get("member_type") or "individual").strip()
        if member_type != "individual":
            raise UserError("團體會員請使用團體申請入口，並等待 Founder 核准。")
        organization_name = str(qcontext.get("organization_name") or "").strip()
        if not organization_name:
            raise UserError("個人會員必須填寫所屬團體。")
        if len(organization_name) > 160:
            raise UserError("所屬團體名稱過長。")
        membership_category = str(
            qcontext.get("membership_category") or ""
        ).strip()
        if membership_category not in INDIVIDUAL_JURISDICTION_CATEGORIES:
            raise UserError("請選擇是否位於五常社區轄區內。")

        values = self._prepare_signup_values(qcontext)
        self._signup_with_values(qcontext.get("token"), values)
        registration = (
            request.env["wuchang.member.registration"]
            .with_user(request.env.user)
            .sudo()
            .create({
            "registration_channel": "odoo",
            "review_status": "draft",
            "consent_version": "individual_member_v1",
            "member_type": "individual",
            "organization_name": organization_name,
            "organization_role": (
                "resident"
                if membership_category == "in_community_jurisdiction"
                else "other"
            ),
            "membership_category": membership_category,
            "role_scope": "member",
            "service_scope": "community_member_service",
            })
        )
        registration.action_submit_review()
        request.env.cr.commit()


class WuchangMemberRegistrationController(http.Controller):
    def _founder_review_authorized(self):
        raw = request.env["ir.config_parameter"].sudo().get_param(
            "founder.identity.google_accounts"
        ) or "[]"
        try:
            founder_accounts = {
                str(account).strip().lower()
                for account in json.loads(raw)
                if isinstance(account, str) and account.strip()
            }
        except (TypeError, ValueError):
            return False
        login = str(request.env.user.login or "").strip().lower()
        return bool(
            login
            and login in founder_accounts
            and request.env.user.has_group(
                "wuchang_member_registration.group_wuchang_member_admin"
            )
        )

    def _registration_enabled(self):
        return request.env["wuchang.community.feature.gate"].is_landing_enabled(
            "member_registration"
        )

    def _registration_hold(self):
        return {
            "state": "HOLD_LANDING_CONTROL_DISABLED",
            "feature_key": "landing.member_registration",
            "member_plaintext": False,
        }

    def _registration_hold_page(self):
        return request.make_response(
            "會員服務目前暫停受理，既有會員權益不受影響；請稍後再試或洽服務人員。",
            status=503,
            headers=[("Content-Type", "text/plain; charset=utf-8")],
        )

    @http.route(
        "/wuchang/control/member-registration",
        type="http",
        auth="public",
        csrf=False,
    )
    def member_registration_control(self, **kw):
        gate = request.env["wuchang.community.feature.gate"].sudo().search([
            ("feature_key", "=", "landing.member_registration"),
        ], limit=1)
        if not gate or not gate.is_landing_enabled("member_registration"):
            return request.make_response("", status=503)
        status = gate.build_status()
        return request.make_response(
            "",
            status=204,
            headers=[
                ("X-W7TP-Control-State", status["gate_state"]),
                ("X-W7TP-Control-Receipt", status["receipt_ref"]),
            ],
        )

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
  <title>新北市三重區五常社區發展協會｜以 AI 科技抵禦 AI 時代的衝擊，以科技服務社區</title>
  <style>
    :root {
      --bg-deep: #0b0f14;
      --bg-card: rgba(20, 27, 36, 0.88);
      --gold: #e5a93c;
      --gold-soft: #f5d08a;
      --emerald: #2dd4bf;
      --text-main: #f3f6fa;
      --text-muted: #a6b4c6;
      --line: rgba(229, 169, 60, 0.28);
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      font-family: "Noto Serif TC", "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif;
      color: var(--text-main);
      background: radial-gradient(circle at 18% 10%, rgba(229,169,60,0.16), transparent 38%),
                  radial-gradient(circle at 82% 26%, rgba(45,212,191,0.10), transparent 42%),
                  linear-gradient(180deg, #090d12 0%, #111822 50%, #0b0f14 100%);
      line-height: 1.78;
    }
    a { color: inherit; text-decoration: none; }
    .topbar {
      position: sticky; top: 0; z-index: 99;
      backdrop-filter: blur(18px);
      background: rgba(9, 13, 18, 0.88);
      border-bottom: 1px solid var(--line);
      padding: 14px clamp(20px, 5vw, 64px);
      display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 14px;
    }
    .brand { display: flex; align-items: center; gap: 12px; font-weight: 800; }
    .brand-badge {
      padding: 4px 12px; border-radius: 999px;
      background: linear-gradient(135deg, var(--gold), #b87b14);
      color: #090d12; font-size: 0.8rem; font-weight: 900;
    }
    .nav-links { display: flex; gap: 18px; flex-wrap: wrap; font-size: 0.93rem; color: var(--text-muted); }
    .nav-links a:hover { color: var(--gold-soft); }
    .hero {
      padding: clamp(50px, 7vw, 96px) clamp(20px, 5vw, 64px);
      border-bottom: 1px solid var(--line);
      background:
        linear-gradient(120deg, rgba(9,13,18,0.94) 28%, rgba(17,24,34,0.80) 68%, rgba(229,169,60,0.15) 100%),
        url("/wuchang_member_registration/static/src/img/liaoguo_exterior.jpg") center/cover no-repeat;
    }
    .hero-inner, .wrap { max-width: 1180px; margin: 0 auto; }
    .kicker {
      display: inline-flex; gap: 10px; align-items: center; flex-wrap: wrap;
      padding: 6px 16px; border-radius: 999px;
      border: 1px solid var(--line); background: rgba(229,169,60,0.12);
      color: var(--gold-soft); font-size: 0.9rem; margin-bottom: 18px;
    }
    h1 {
      font-size: clamp(1.9rem, 3.6vw, 3.15rem);
      line-height: 1.26; margin: 0 0 20px;
      background: linear-gradient(95deg, #ffffff 0%, #f5d08a 62%, #e5a93c 100%);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .hero-quote {
      font-size: clamp(1.02rem, 1.45vw, 1.15rem);
      color: #e2e8f0; max-width: 1060px;
      border-left: 4px solid var(--gold); margin: 0 0 22px;
      background: rgba(15, 23, 34, 0.68); padding: 20px 24px; border-radius: 0 14px 14px 0;
    }
    .pledge-banner {
      background: linear-gradient(135deg, rgba(229,169,60,0.22) 0%, rgba(20,184,166,0.18) 100%);
      border: 2px solid var(--gold); border-radius: 16px;
      padding: 18px 24px; margin-bottom: 26px; max-width: 1060px;
      box-shadow: 0 12px 32px rgba(229,169,60,0.2);
    }
    .pledge-banner strong { color: var(--gold-soft); font-size: 1.16rem; display: block; margin-bottom: 6px; }
    .mission-tags { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 26px; }
    .tag {
      padding: 6px 14px; border-radius: 8px; font-size: 0.87rem;
      background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.14);
    }
    .actions { display: flex; flex-wrap: wrap; gap: 14px; }
    .btn {
      display: inline-flex; align-items: center; gap: 8px;
      padding: 13px 22px; border-radius: 12px; font-weight: 700; font-size: 0.96rem;
      border: 1px solid rgba(255,255,255,0.22); background: rgba(255,255,255,0.06);
      color: #fff; transition: all 0.2s ease; cursor: pointer;
    }
    .btn:hover { transform: translateY(-2px); border-color: var(--gold); background: rgba(229,169,60,0.16); }
    .btn.primary {
      background: linear-gradient(135deg, #e5a93c 0%, #c48216 100%);
      color: #090d12; border: none; box-shadow: 0 10px 28px rgba(229,169,60,0.3);
    }
    .btn.emerald {
      background: linear-gradient(135deg, #14b8a6 0%, #0f766e 100%);
      color: #fff; border: none;
    }
    .section { padding: clamp(50px, 7vw, 84px) clamp(20px, 5vw, 64px); border-bottom: 1px solid rgba(255,255,255,0.07); }
    .sec-head { margin-bottom: 32px; }
    .sec-label { color: var(--gold); font-size: 0.86rem; font-weight: 800; letter-spacing: 1.5px; }
    .sec-title { font-size: clamp(1.7rem, 2.8vw, 2.4rem); margin: 8px 0 12px; color: #fff; }
    .sec-desc { color: var(--text-muted); max-width: 980px; margin: 0; font-size: 1.03rem; }
    .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; }
    .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 22px; }
    .grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; }
    .card {
      background: var(--bg-card); border: 1px solid rgba(255,255,255,0.1);
      border-radius: 18px; padding: 24px;
      box-shadow: 0 18px 40px rgba(0,0,0,0.42);
      display: flex; flex-direction: column; justify-content: space-between;
    }
    .card.gold-border { border-color: var(--line); }
    .card h3 { margin: 0 0 10px; font-size: 1.24rem; color: var(--gold-soft); }
    .card p { margin: 0 0 14px; color: #d5deeb; font-size: 0.95rem; }
    .photo-card {
      border-radius: 18px; overflow: hidden; border: 1px solid var(--line);
      background: #121923; display: flex; flex-direction: column;
    }
    .photo-box {
      height: 210px; position: relative;
      background: linear-gradient(135deg, #1e293b 0%, #0f172a 55%, #3b2a14 100%);
      background-size: cover; background-position: center;
    }
    .photo-badge {
      position: absolute; top: 12px; left: 12px;
      padding: 4px 12px; border-radius: 999px; font-size: 0.76rem; font-weight: 700;
      background: rgba(9,13,18,0.84); color: var(--gold-soft); border: 1px solid var(--line);
    }
    .photo-body { padding: 18px; }
    .photo-body h4 { margin: 0 0 8px; color: #fff; font-size: 1.1rem; }
    .photo-body p { margin: 0; color: var(--text-muted); font-size: 0.9rem; }
    .stat-box {
      padding: 18px; border-radius: 14px; background: rgba(0,0,0,0.36);
      border: 1px solid rgba(229,169,60,0.28); text-align: center;
    }
    .stat-num { font-size: 1.58rem; font-weight: 900; color: var(--gold-soft); }
    .pool-diagram {
      background: linear-gradient(135deg, rgba(22,30,41,0.96), rgba(12,18,26,0.96));
      border: 1px solid var(--line); border-radius: 22px; padding: 30px;
      margin-top: 26px; display: grid; grid-template-columns: 1fr 210px 1.2fr; gap: 22px; align-items: center;
    }
    .pool-center {
      width: 185px; height: 185px; margin: 0 auto; border-radius: 50%;
      background: radial-gradient(circle, #f5b942 0%, #c98212 100%);
      color: #090d12; display: flex; flex-direction: column; align-items: center; justify-content: center;
      text-align: center; font-weight: 900; box-shadow: 0 0 46px rgba(229,169,60,0.42);
    }
    .pool-center .dollar { font-size: 3rem; line-height: 1; }
    .xiaoj-stage {
      background: linear-gradient(125deg, rgba(30,41,59,0.92) 0%, rgba(15,23,42,0.96) 60%, rgba(229,169,60,0.18) 100%);
      border: 1px solid var(--gold); border-radius: 24px; padding: clamp(24px, 4vw, 42px);
    }
    footer {
      padding: 38px clamp(20px, 5vw, 64px); background: #070a0e;
      border-top: 1px solid var(--line); color: var(--text-muted); font-size: 0.9rem;
    }
    @media (max-width: 960px) {
      .grid-4, .grid-3, .grid-2, .pool-diagram { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header class="topbar">
    <div class="brand">
      <span class="brand-badge">五常社區發展協會</span>
      <span>新北市三重區五常社區發展協會（理事長 江政隆）× 上品聊國咖啡烘焙館</span>
    </div>
    <nav class="nav-links">
      <a href="#section-location">1. 地理位置與田野調查</a>
      <a href="#section-features">2. 共生共榮與AI價值重分配</a>
      <a href="#section-xiaoj">3. 社區聊天機器人小J</a>
      <a href="#section-tech">4. Gemini優化與區域算力群</a>
      <a href="#section-services">5. 即將開啟的 AI 服務</a>
    </nav>
  </header>

  <main>
    <!-- 主視覺：聊天機器人讓社區服務 × Gemini 負責提高優化能力 × 讓 Google 賺但與公益共享收益 -->
    <section class="hero">
      <div class="hero-inner">
        <div class="kicker">
          <span>🌾 共生共榮才是王道・社區服務第一線 × Gemini 幕後優化 × 與公益共享收益</span>
          <span>•</span>
          <span>以 AI 科技抵禦 AI 時代的衝擊，以科技服務社區</span>
        </div>
        <h1>聊天機器人讓社區來服務，Gemini 負責幫我們提高優化能力；<br>讓 Google 合法賺錢但與公益共享收益——立志讓社區長輩都有早餐吃。</h1>
        <blockquote class="hero-quote">
          「我從街頭勞權抗爭者、<strong>秋鬥籌劃人</strong>，歷經<strong>關廠工人、國道收費員、華航罷工</strong>，當過<strong>政府公務員</strong>、親手創立<strong>『新北市政府環境保護局工會』</strong>，一路走到現在深耕社區。待在街頭的那些年，我深知<strong>台灣社會的問題來自家庭</strong>；而步入 AI 時代，<strong>我的洞見是：AI 對世界所產生的衝擊，本質上是『分配問題』！</strong><br><br>
          我在孕育我長大的三重五常社區居住 40 年，親自做過田野調查、走過每一寸土地——看著家鄉從一片田園抓青蛙，變成高樓林立與老巷弄臭水溝抓老鼠；忘不了兒時<strong>大樹下的米苔目</strong>、<strong>巷子口賣麵的大胖伯伯</strong>，還有當年<strong>買魚的伯母跟她老公，今年都已經九十多歲了</strong>。<br><br>
          我帶著鮭魚返鄉建設故鄉的心願創建這套系統，就是要<strong>拋磚引玉，重建 AI 價值的分配邏輯</strong>。我並不是要打擊雲端大廠，反而是為他們開條合法路線——在我的字典裡，<strong>共生共榮才是王道</strong>！<strong>以後第一線的聊天機器人（小J）讓社區自己來服務，幕後由 Google Gemini 負責幫我們提高與優化能力；我們讓 Google 合法合規賺取雲端與優化收益，同時將商業成果與社區公益共享收益</strong>，透過『聊國咖啡館』與社區基金池，<strong>我立志讓社區每一位長輩每天都有熱騰騰的早餐吃！</strong>」<br>
          <strong style="color:var(--gold-soft); display:inline-block; margin-top:10px;">—— 新北市三重區五常社區發展協會 理事長 江政隆</strong>
        </blockquote>

        <div class="pledge-banner">
          <strong>🎁 五常社區專屬公益承諾：只要五常社區的物業或在地商業，自出設備、我免費搭建！快速匯集「區域算力群」與雲端大廠共生共榮！</strong>
          <span>為什麼堅持在社區大樓現場搭建？因為<strong>社區物業擁有極為充裕的社區網路（肥頻寬）</strong>！凡五常社區轄區（五常里、五順里、仁忠里及仁義重劃區）之大樓管委會或在地商業，只要自備硬體設備，理事長本人免費為您搭建整套「3D 影音小J ＋ 協會主控電子看板 ＋ 專利物業系統」：<strong>由社區區域算力群直接提供第一線聊天機器人服務，由 Gemini 在幕後強化優化能力，讓大廠與社區公益共享收益！</strong></span>
        </div>

        <div class="mission-tags">
          <span class="tag">✅ 公益治理主體：新北市三重區五常社區發展協會（理事長 江政隆）</span>
          <span class="tag">✅ 黃金分工：第一線聊天機器人由社區服務 × 幕後由 Gemini 提高優化能力</span>
          <span class="tag">✅ 王道分配：為雲端大廠開條合法路線・讓 Google 賺但與公益共享收益</span>
          <span class="tag">✅ 算力戰略：善用社區物業肥頻寬・自出設備免費搭建・快速匯集區域算力群</span>
        </div>
        <div class="actions">
          <a class="btn primary" href="/web/login">🔐 主權會員單一登入（免選角色・依座位自動配屬權限）</a>
          <a class="btn emerald" href="/wuchang/business/onboarding">🏢 五常物業／在地商家：申請「自出設備・免費搭建」加入區域算力群</a>
          <a class="btn" href="/web/signup">🌱 自然人會員／家庭與長輩早餐註冊</a>
          <a class="btn" href="/forum">💬 五常社區會員討論版</a>
        </div>
      </div>
    </section>

    <!-- 第一篇：協會地理位置與理事長親身田野調查實錄 -->
    <section id="section-location" class="section">
      <div class="wrap">
        <div class="sec-head">
          <div class="sec-label">CHAPTER 01 • FIELD SURVEY & REGIONAL COMPUTE GEOGRAPHY</div>
          <h2 class="sec-title">一、協會地理位置與田野調查：走過 62.9 公頃每一寸土地，串聯仁義重劃區高樓物業與「銀新未來城」</h2>
          <p class="sec-desc">
            因為深知「台灣社會的問題來自家庭」，江政隆理事長親自走訪五常社區（涵蓋五常里、五順里、仁忠里共 3 里，總面積 62.9 公頃、5,783 戶家庭、13,922 人）每一條街巷完成田野調查：這裡有面積達 22.28 公頃（占 35.38%）、高樓林立且具備完善社區光纖網路的「五常仁義重劃區」，緊鄰新北市智慧長照園區「銀新未來城」預定地，並以重安街口 204 號「聊國咖啡烘焙館（重新總店）」作為第一號慈善商業與算力示範母基地！
          </p>
        </div>

        <div class="grid-4" style="margin-bottom:24px;">
          <div class="stat-box">
            <div class="stat-num">62.9 公頃實地踏查</div>
            <strong>五常・五順・仁忠里</strong>
            <p style="margin:6px 0 0; font-size:0.85rem; color:var(--text-muted);">理事長走過每一寸土地・守護 5,783 個家庭</p>
          </div>
          <div class="stat-box">
            <div class="stat-num">22.28 公頃高樓群</div>
            <strong>社區物業肥頻寬基地</strong>
            <p style="margin:6px 0 0; font-size:0.85rem; color:var(--text-muted);">在社區物業搭建・快速匯集區域算力群</p>
          </div>
          <div class="stat-box">
            <div class="stat-num">老化指數 138.3%</div>
            <strong>分擔家庭主要照顧壓力</strong>
            <p style="margin:6px 0 0; font-size:0.85rem; color:var(--text-muted);">實現「生在這、長在這、老在這」與每日早餐</p>
          </div>
          <div class="stat-box">
            <div class="stat-num">緊鄰銀新未來城</div>
            <strong>仁義街 × 重安街雙核心</strong>
            <p style="margin:6px 0 0; font-size:0.85rem; color:var(--text-muted);">協會治理核心 × 聊國咖啡館重新總店</p>
          </div>
        </div>

        <div class="grid-4">
          <article class="photo-card">
            <div class="photo-box" style="background-image: linear-gradient(180deg,transparent 30%,rgba(9,13,18,0.92)), url('/wuchang_member_registration/static/src/img/wuchang_dance_club.jpg');">
              <span class="photo-badge">實景 (1) 五常公園天幕舞台</span>
            </div>
            <div class="photo-body">
              <h4>五常社區舞蹈社活動實況</h4>
              <p>本會成立舞蹈社、家政社、新住民文化推廣社與柔力球社，長輩在五常公園彩繪舞台前舞出健康活力，減輕家庭照護負擔。</p>
            </div>
          </article>

          <article class="photo-card">
            <div class="photo-box" style="background-image: linear-gradient(180deg,transparent 30%,rgba(9,13,18,0.92)), url('/wuchang_member_registration/static/src/img/renyi_rezone_1.jpg');">
              <span class="photo-badge">實景 (2) 仁義街 × 元信二街</span>
            </div>
            <div class="photo-body">
              <h4>五常仁義重劃區：匯集區域算力群</h4>
              <p>昔日抓青蛙的田園已成現代高樓群，各棟社區物業擁有充裕社區網路頻寬，自出設備由理事長免費搭建，快速匯集區域算力群！</p>
            </div>
          </article>

          <article class="photo-card">
            <div class="photo-box" style="background-image: linear-gradient(180deg,transparent 30%,rgba(9,13,18,0.92)), url('/wuchang_member_registration/static/src/img/yinxin_future_city.jpg');">
              <span class="photo-badge">實景 (3) 仁義街口樞紐</span>
            </div>
            <div class="photo-body">
              <h4>緊鄰「銀新未來城」預定地</h4>
              <p>面對社區內缺乏長照機構之痛點，本會超前部署社區家庭照護網與長輩愛心早餐，與銀新未來城無縫接軌。</p>
            </div>
          </article>

          <article class="photo-card">
            <div class="photo-box" style="background-image: linear-gradient(180deg,transparent 30%,rgba(9,13,18,0.92)), url('/wuchang_member_registration/static/src/img/wuchang_home_econ.jpg');">
              <span class="photo-badge">實景 (4) 社區溫暖教室</span>
            </div>
            <div class="photo-body">
              <h4>五常社區家政社教學實況</h4>
              <p>長輩們手把手編織毛線、學習手作，並結合獲「社區一家」與文化局肯定之「社區專勤隊」發揮銀髮互助價值。</p>
            </div>
          </article>
        </div>
      </div>
    </section>

    <!-- 第二篇：特色介紹（讓 Google 賺但與公益共享收益 × 聊國咖啡館慈善商業 × 社區基金池） -->
    <section id="section-features" class="section">
      <div class="wrap">
        <div class="sec-head">
          <div class="sec-label">CHAPTER 02 • SYMBIOTIC CO-PROSPERITY & SHARED REVENUE WITH PHILANTHROPY</div>
          <h2 class="sec-title">二、特色介紹：讓 Google 合法賺錢但與公益共享收益——不募款、婉謝捐款，以聊國咖啡館與 AI 養公益</h2>
          <p class="sec-desc">
            我們重建 AI 價值的分配邏輯，是開創「社區服務第一線 × Gemini 幕後優化 × 大廠與公益共享收益」的共生共榮新典範！五常社區發展協會堅持「不對外募款、婉謝捐款、以商以智養公益」，由長期挹注社區的慈善商業「上品食品行／聊國咖啡烘焙館（重新總店）」無償為社區提供資金、提供技術；而在全台推廣的商業與物業服務中，我們讓 Google 與合作大廠合法賺取技術與雲端收益，同時將共創收益與社區公益共享，匯入「社區發展基金－社區照護專戶」，讓九十歲長輩每天都有熱騰騰的早餐吃！
          </p>
        </div>

        <div class="grid-2">
          <article class="photo-card">
            <div class="photo-box" style="height:240px; background-image: linear-gradient(180deg,transparent 25%,rgba(9,13,18,0.92)), url('/wuchang_member_registration/static/src/img/liaoguo_night.jpg');">
              <span class="photo-badge">慈善商業示範基地（重安街口 204 號）</span>
            </div>
            <div class="photo-body">
              <h4>聊國咖啡烘焙館（重新總店）—— 價值重分配的資金與技術母引擎</h4>
              <p>座落於三重重安街口的聊國咖啡烘焙館，長期無私為協會提供資金與頂尖 AI 技術，將營業盈餘與科技紅利注入社區基金池，撐起社區長輩每天早上的營養早餐與家庭支持服務。</p>
            </div>
          </article>

          <article class="photo-card">
            <div class="photo-box" style="height:240px; background-image: linear-gradient(180deg,transparent 25%,rgba(9,13,18,0.92)), url('/wuchang_member_registration/static/src/img/liaoguo_arcade.jpg');">
              <span class="photo-badge">溫暖騎樓 × 區域算力與社區專勤隊基地</span>
            </div>
            <div class="photo-body">
              <h4>社區第一線服務 × Gemini 幕後優化 × 社區專勤隊</h4>
              <p>第一線聊天機器人由社區區域算力群與長輩專勤隊親切服務；幕後由 Gemini 持續幫系統提高優化能力，讓雲端大廠合法獲利並與社區照護專戶共享收益。</p>
            </div>
          </article>
        </div>

        <div class="pool-diagram">
          <div class="card gold-border">
            <h3>☕ 價值輸入端：慈善商業 × 大廠與公益共享收益</h3>
            <p><strong>聊國咖啡館（重新總店）</strong>、社區區域算力節點與雲端大廠合法商用合作，讓 Google 賺取優化服務收益，並將<strong>商業盈餘與共享分潤</strong>注入社區基金池。</p>
            <p style="margin:0; color:var(--gold-soft); font-weight:700;">🔄 共生共榮・每季公開透明・社區共好</p>
          </div>
          <div class="pool-center">
            <div class="dollar">$</div>
            <div>社區發展基金</div>
            <small style="font-weight:800;">商善共享分配中樞</small>
          </div>
          <div class="grid-2" style="gap:12px;">
            <div class="card" style="padding:16px;">
              <h3 style="font-size:1.05rem;">🤖 社區第一線聊天機器人</h3>
              <p style="margin:0; font-size:0.88rem;">由社區與區域算力群直接服務里民長輩，溫暖零延遲。</p>
            </div>
            <div class="card" style="padding:16px;">
              <h3 style="font-size:1.05rem;">🧠 Gemini 幕後提高優化</h3>
              <p style="margin:0; font-size:0.88rem;">零明文遮罩保護下，由 Gemini 強化語意與系統能力。</p>
            </div>
            <div class="card" style="padding:16px;">
              <h3 style="font-size:1.05rem;">🤝 讓大廠賺並與公益共享</h3>
              <p style="margin:0; font-size:0.88rem;">開創合法合規商用路線，大廠獲利同時回流社區公益！</p>
            </div>
            <div class="card" style="padding:16px;">
              <h3 style="font-size:1.05rem;">🥣 長輩每日愛心早餐</h3>
              <p style="margin:0; font-size:0.88rem;">將共創紅利化為長輩每天早上的熱早餐，減輕家庭重擔！</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 第三篇：數位孿生 AI 家人「小J」—— 社區自己服務的聊天機器人・每日短片擬人化 AI 明星 -->
    <section id="section-xiaoj" class="section">
      <div class="wrap">
        <div class="xiaoj-stage">
          <div class="sec-head" style="margin-bottom:24px;">
            <div class="sec-label">CHAPTER 03 • COMMUNITY-SERVED AI FAMILY & GEMINI-OPTIMIZED STAR</div>
            <h2 class="sec-title">三、認識「小J」：由社區直接服務的第一線聊天機器人 × 江政隆理事長設計的數位孿生「AI 家人」</h2>
            <p class="sec-desc" style="color:#e2e8f0;">
              第一線的聊天機器人，最懂街坊人情味的永遠是社區自己！江政隆理事長親自設計了<strong>「數位孿生（Digital Twin）—— 小J」</strong>，由五常社區區域算力群在第一線直接服務長輩與家庭，並由 <strong>Google Gemini 在幕後持續幫我們提高與優化能力</strong>——讓小J 成為五常社區發展協會的<strong>官方代言人、未來行銷大使與每日短片擬人化 AI 明星</strong>！
            </p>
          </div>

          <div class="grid-4">
            <article class="card gold-border">
              <h3>🎬 每日短片 ①：長輩早安早餐篇</h3>
              <p>頂著招牌銀黃色復古波浪短髮（Finger Wave Pixie），AI 家人小J 每天清晨以溫暖短片問候九十多歲的買魚伯母夫妻與社區長輩，提醒享用今日熱騰騰的營養早餐，讓子女安心上班。</p>
              <a class="btn" href="/web/login">進入長輩早餐關懷 →</a>
            </article>
            <article class="card gold-border">
              <h3>🎬 每日短片 ②：社團與家庭共好篇</h3>
              <p>每日播報五常公園舞蹈社、家政社、柔力球社與「社區專勤隊」實況，讓 22.28 公頃仁義重劃區的新興小家庭與老街坊緊密相連。</p>
              <a class="btn" href="/forum">前往社區討論版 →</a>
            </article>
            <article class="card gold-border">
              <h3>🎬 每日短片 ③：聊國咖啡職人篇</h3>
              <p>帶大家走進重安街口「聊國咖啡烘焙館（重新總店）」，分享手沖精品咖啡與大樹下米苔目、賣麵大胖伯伯等五常里 40 年溫暖記憶。</p>
              <a class="btn" href="#section-features">了解慈善商業基地 →</a>
            </article>
            <article class="card gold-border">
              <h3>🎬 每日短片 ④：雲端商會行銷篇</h3>
              <p>擔任在地商家雲端商會與大樓管委會的首席 AI 行銷大使！經 Gemini 幕後優化行銷劇本，透過駐店圖形化電子看板為店家帶來穩定客流。</p>
              <a class="btn" href="/wuchang/business/onboarding">預約小J行銷代言 →</a>
            </article>
          </div>
        </div>
      </div>
    </section>

    <!-- 第四篇：發展方向與現有技術（社區服務第一線 × Gemini 幕後優化 × 區域算力群 × 專利 M663678 號） -->
    <section id="section-tech" class="section">
      <div class="wrap">
        <div class="sec-head">
          <div class="sec-label">CHAPTER 04 • COMMUNITY FRONTLINE, GEMINI OPTIMIZATION & PATENT M663678</div>
          <h2 class="sec-title">四、發展方向與現有技術：社區區域算力服務第一線 × Gemini 幕後提高優化能力 × 專利 M663678 號</h2>
          <p class="sec-desc">
            在江政隆理事長的「共生共榮」架構下，社區與雲端大廠有著最明確的黃金分工：本會以國家新型專利「整合式物業管理系統（M663678 號）」結合「原胞狀態生成式傳輸（Origin-Cell GST V2.1）」，善用五常各社區物業肥美的社區網路免費搭建節點、快速匯集「區域算力群」來承擔第一線聊天機器人與 3D 影音服務；而 Google Gemini 則在主權個資遮罩（零明文）的安全邊界後，負責幫系統持續提高與優化能力——讓 Google 合法賺取雲端優化收益，並與社區公益共享收益！
          </p>
        </div>

        <div class="grid-3" style="margin-bottom:22px;">
          <div class="stat-box">
            <div class="stat-num">社區服務 × Gemini 優化</div>
            <strong>讓 Google 賺但與公益共享收益</strong>
            <p style="margin:6px 0 0; font-size:0.85rem; color:var(--text-muted);">社區區域算力扛第一線服務，Gemini 幕後強化優化能力</p>
          </div>
          <div class="stat-box">
            <div class="stat-num">25.17 MB → 99 Bytes</div>
            <strong>Tier 2 巨型 4K 影像＋動作封包</strong>
            <p style="margin:6px 0 0; font-size:0.85rem; color:var(--text-muted);">15.1 毫秒本地重構，結合社區物業肥頻寬發揮極致效能</p>
          </div>
          <div class="stat-box">
            <div class="stat-num">5.00 GiB → 46 Bytes</div>
            <strong>Tier 3 跨洲 64-bit 串流分塊引擎</strong>
            <p style="margin:6px 0 0; font-size:0.85rem; color:var(--text-muted);">台灣 ➔ 美國 1GB RAM 節點零 OOM 實機落盤驗證</p>
          </div>
        </div>

        <div class="grid-3">
          <article class="card">
            <h3>1. 社區區域算力群（第一線服務）</h3>
            <p>善用各社區物業大樓既有的高速社區網路（肥頻寬）與原胞狀態傳輸（79B / 99B / 46B），讓聊天機器人小J 與 3D 數位看板由社區自己就近服務，迅速、親切且零頻寬瓶頸！</p>
          </article>
          <article class="card">
            <h3>2. Gemini 幕後優化（合法零明文）</h3>
            <p>Odoo 總場僅留存「個人遮罩識別」；<strong>開啟規則握在自然人手上（權限在個人），加密封存由總場主權根守護（責任在總場）</strong>。Gemini 在不觸碰明文個資下幫系統提高優化能力，100% 合法合規！</p>
          </article>
          <article class="card">
            <h3>3. 駐店／駐樓高速 VM・核心物理隔絕</h3>
            <p>部署於各社區物業與合作店家的交界伺服器，整合運用區網全部可用通訊埠就近服務；底層核心物理隔絕、對外「可用不可修」，唯江政隆理事長本人主權身分根經指定管道可修。</p>
          </article>
        </div>
      </div>
    </section>

    <!-- 第五篇：即將開啟的 AI 服務介紹頁 -->
    <section id="section-services" class="section">
      <div class="wrap">
        <div class="sec-head">
          <div class="sec-label">CHAPTER 05 • UPCOMING SOVEREIGN AI SERVICES</div>
          <h2 class="sec-title">五、即將開啟的 AI 服務介紹：個人端「會員小J」× 組織端「3D 影音小J 與協會主控電子看板」</h2>
          <p class="sec-desc">
            單一會員入口登入，免選角色！系統根據自然人所在的家庭、組織與座位（相對位置規則），自動配屬對應權限與 AI 技能。
          </p>
        </div>

        <div class="grid-2">
          <article class="card gold-border">
            <div>
              <span class="brand-badge" style="display:inline-block; margin-bottom:12px;">自然人與家庭受服務主權單位</span>
              <h3>📱 個人服務「會員小J」—— 社區親自服務每個家庭與長輩的 AI 家人</h3>
              <p>• <strong>服務對象</strong>：五常社區 3 里（五常里、五順里、仁忠里）5,783 戶家庭、長輩、社區專勤隊隊員與全體自然人會員。</p>
              <p>• <strong>核心功能</strong>：由社區第一線提供每日長輩愛心早餐一鍵核銷、家庭健康與平安語音關懷、雲端商會跨店消費回饋、社安通報專線與個人主權身分封包自主管理，並由 Gemini 幕後持續優化體驗。</p>
            </div>
            <div class="actions" style="margin-top:18px;">
              <a class="btn primary" href="/web/login">立即登入個人會員小J</a>
              <a class="btn" href="/web/signup">免費註冊自然人會員</a>
            </div>
          </article>

          <article class="card gold-border">
            <div>
              <span class="brand-badge" style="display:inline-block; margin-bottom:12px; background:linear-gradient(135deg,#2dd4bf,#0d9488);">五常社區物業／在地商業「自出設備・免費搭建」</span>
              <h3>🖥️ 組織窗口「3D 影音小J」＋ 協會主控圖形化廣告機／電子看板（區域算力節點）</h3>
              <p>• <strong>善用社區網路肥頻寬・免費搭建</strong>：只要是五常社區的大樓管委會（物業）或在地商業，<strong>自出設備並接上社區網路，江政隆理事長免費為您搭建整套系統</strong>，直接成為五常區域算力群的一員！</p>
              <p>• <strong>三機鐵三角地端服務</strong>：由駐樓／駐店伺服器（原生圖形介面源頭）＋ 背容器電腦控制機 ＋ 8GB GPU 算力機協同，提供 3D 迎賓點餐、管委會門禁接待與家庭包裹通知。</p>
              <p>• <strong>協會主控廣告機 ＆ 與公益共享收益</strong>：組織負責人（店長／管委會主委）可隨時刊登店內電子布告欄或大樓公告，並透過 Gemini 優化之跨社區廣告聯播，讓大廠、店家與社區公益共享收益！</p>
            </div>
            <div class="actions" style="margin-top:18px;">
              <a class="btn emerald" href="/wuchang/business/onboarding">五常物業／商家：申請自出設備免費搭建</a>
              <a class="btn" href="/forum">前往社區討論版交流</a>
            </div>
          </article>
        </div>
      </div>
    </section>
  </main>

  <footer>
    <div class="wrap" style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:16px;">
      <div>
        <strong style="color:#fff;">新北市三重區五常社區發展協會（理事長 江政隆｜會址：新北市三重區仁義街161號）× 上品聊國咖啡烘焙館（重新總店）</strong><br>
        <span>宗旨：以 AI 科技抵禦 AI 時代的衝擊，以科技服務社區｜共生共榮：聊天機器人讓社區服務，Gemini 負責提高優化能力，讓 Google 賺但與公益共享收益</span>
      </div>
      <div>
        <a href="/web/login" style="color:var(--gold-soft); margin-right:16px;">主權會員登入</a>
        <a href="/web/signup" style="color:var(--gold-soft); margin-right:16px;">個人註冊</a>
        <a href="/wuchang/business/onboarding" style="color:var(--gold-soft); margin-right:16px;">團體入駐／免費搭建申請</a>
        <a href="/forum" style="color:var(--gold-soft);">社區討論版</a>
      </div>
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
        if not self._registration_enabled():
            return self._registration_hold()
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
            "member_type": "individual",
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
        if not self._registration_enabled():
            return self._registration_hold_page()
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
  <p>自然人先作為負責人或授權管理者建立團體；由 Founder 核准團體資格，總場只核對安全、權限與證據邊界。</p>
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
      <label>是否位於五常社區轄區
        <select name="service_area_ref" required>
          <option value="in_community_jurisdiction">轄區內（五常里、五順里、仁忠里）</option>
          <option value="outside_community_jurisdiction">轄區外</option>
        </select>
      </label>
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
        if not self._registration_enabled():
            return self._registration_hold_page()
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
        if not self._registration_enabled():
            return self._registration_hold()
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
        if not self._founder_review_authorized():
            return {
                "state": "HOLD_FOUNDER_APPROVAL_REQUIRED",
                "member_plaintext": False,
            }
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
        if not self._registration_enabled():
            return self._registration_hold_page()
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
          <p>Google／LINE channel 綁定須在既有會員 session 內完成；本頁不提供外部登入旁路。</p>
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
        if not self._registration_enabled():
            return self._registration_hold_page()
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
