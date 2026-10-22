from __future__ import annotations

import html

from odoo import http
from odoo.http import request


_ALLOWED_JURISDICTION = {
    "in_community_jurisdiction",
    "outside_community_jurisdiction",
}


def _page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{html.escape(title)}</title>
  <style>
    body {{ margin:0; background:#f4f7fb; color:#172033; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
    main {{ min-height:100vh; display:grid; place-items:center; padding:28px 18px; background:linear-gradient(135deg,#eef4fb,#f8fafc 58%,#eef7f2); }}
    .card {{ width:min(100%,620px); box-sizing:border-box; padding:30px; background:#fff; border:1px solid #dbe4ef; border-radius:18px; box-shadow:0 24px 70px rgba(15,35,60,.10); }}
    .brand {{ color:#8a5a00; font-size:.9rem; font-weight:800; margin-bottom:10px; }}
    h1 {{ margin:0; color:#102139; font-size:clamp(1.8rem,5vw,2.6rem); letter-spacing:-.02em; }}
    p {{ color:#58687c; line-height:1.75; }}
    label {{ display:block; margin:18px 0 8px; font-weight:750; }}
    input[type=text] {{ width:100%; box-sizing:border-box; min-height:48px; padding:10px 12px; border:1px solid #cfd8e3; border-radius:10px; font-size:1rem; }}
    .choices {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:8px; }}
    .choice {{ display:flex; gap:8px; align-items:center; padding:14px; border:1px solid #d5dee9; border-radius:10px; background:#f8fafc; }}
    .button {{ display:inline-flex; align-items:center; justify-content:center; min-height:48px; padding:0 18px; border:0; border-radius:10px; background:#17466f; color:#fff; font-weight:800; text-decoration:none; cursor:pointer; }}
    .button.secondary {{ background:#f8fafc; color:#172033; border:1px solid #d5dee9; }}
    .actions {{ display:flex; flex-wrap:wrap; gap:10px; margin-top:24px; }}
    .status {{ margin:22px 0; padding:16px; background:#f8fafc; border:1px solid #dbe4ef; border-radius:12px; }}
    .status strong {{ display:block; color:#102139; margin-bottom:6px; }}
    .hint {{ font-size:.92rem; color:#718096; }}
    @media(max-width:560px) {{ .card{{padding:22px 18px}} .choices{{grid-template-columns:1fr}} .actions{{display:grid}} .button{{width:100%;box-sizing:border-box}} }}
  </style>
</head>
<body><main><section class="card">
  <div class="brand">五常社區發展協會 × 聊國咖啡</div>
  {body}
</section></main></body>
</html>"""


class WuchangMemberAccountController(http.Controller):
    def _own_registration(self):
        user = request.env.user
        return request.env["wuchang.member.registration"].sudo().search(
            [
                ("create_uid", "=", user.id),
                ("member_type", "=", "individual"),
                ("review_status", "not in", ["rejected", "dead_letter"]),
            ],
            order="id desc",
            limit=1,
        )

    @http.route(
        "/wuchang/member/account",
        type="http",
        auth="user",
        website=False,
        csrf=False,
    )
    def member_account(self, **kw):
        registration = self._own_registration()
        if not registration:
            return request.redirect("/wuchang/member/finish")

        if registration.review_status == "approved" and registration.identity_code_id:
            status_title = "會員身分已啟用"
            status_text = "系統已確認你的會員身分。登入後會依你的身分與授權顯示可使用的服務。"
            action = '<a class="button" href="/wuchang/home">開始使用</a>'
        elif registration.review_status == "draft":
            status_title = "還差一小步"
            status_text = "補上兩項基本資料後即可完成個人會員申請。"
            action = '<a class="button" href="/wuchang/member/finish">完成申請</a>'
        else:
            status_title = "申請已送出"
            status_text = "目前正在處理你的會員申請；不需要重新註冊。"
            action = '<a class="button secondary" href="/wuchang/home">回首頁</a>'

        providers = request.env["wuchang.member.external.auth"].sudo().search(
            [
                ("member_user_id", "=", request.env.user.id),
                ("binding_status", "=", "bound"),
            ]
        )
        provider_labels = {
            "google": "Google",
            "line": "LINE",
            "odoo": "帳號 / Email",
        }
        linked = "、".join(
            provider_labels.get(item.provider, item.provider)
            for item in providers
        ) or "帳號"
        body = f"""
          <h1>{html.escape(status_title)}</h1>
          <p>{html.escape(status_text)}</p>
          <div class="status">
            <strong>登入方式</strong>
            {html.escape(linked)}
          </div>
          <div class="actions">{action}</div>
        """
        return request.make_response(
            _page("小J會員服務", body),
            headers=[("Content-Type", "text/html; charset=utf-8")],
        )

    @http.route(
        "/wuchang/member/finish",
        type="http",
        auth="user",
        website=False,
        methods=["GET", "POST"],
    )
    def member_finish(self, **kw):
        user = request.env.user
        registration = self._own_registration()
        if registration and registration.review_status == "approved":
            return request.redirect("/wuchang/member/account")

        if not registration:
            registration = (
                request.env["wuchang.member.registration"]
                .with_user(user)
                .sudo()
                .create(
                    {
                        "registration_channel": "odoo",
                        "review_status": "draft",
                        "consent_version": "individual_member_v1",
                        "member_type": "individual",
                        "role_scope": "member",
                        "service_scope": "community_member_service",
                    }
                )
            )

        error = ""
        if request.httprequest.method == "POST":
            organization_name = str(kw.get("organization_name") or "").strip()
            membership_category = str(kw.get("membership_category") or "").strip()
            if not organization_name:
                error = "請填寫目前主要所屬團體；沒有特定團體可填「個人」。"
            elif len(organization_name) > 160:
                error = "所屬團體名稱過長。"
            elif membership_category not in _ALLOWED_JURISDICTION:
                error = "請選擇是否位於五常社區轄區內。"
            else:
                safe_record = registration.with_user(user).sudo()
                safe_record.write(
                    {
                        "organization_name": organization_name,
                        "organization_role": (
                            "resident"
                            if membership_category == "in_community_jurisdiction"
                            else "other"
                        ),
                        "membership_category": membership_category,
                        "role_scope": "member",
                        "service_scope": "community_member_service",
                        "consent_version": registration.consent_version
                        or "individual_member_v1",
                    }
                )
                safe_record.action_submit_review()
                if safe_record.identity_code_id:
                    bindings = request.env[
                        "wuchang.member.external.auth"
                    ].sudo().search([
                        ("registration_ref_id", "=", safe_record.id),
                        ("member_user_id", "=", user.id),
                        ("binding_status", "=", "bound"),
                    ])
                    if bindings:
                        bindings.with_user(user).sudo().write({
                            "member_identity_id": safe_record.identity_code_id.id,
                        })
                request.env.cr.commit()
                return request.redirect("/wuchang/member/account")

        org_value = html.escape(registration.organization_name or "")
        in_checked = (
            " checked"
            if registration.membership_category == "in_community_jurisdiction"
            else ""
        )
        out_checked = (
            " checked"
            if registration.membership_category == "outside_community_jurisdiction"
            else ""
        )
        error_html = (
            f'<div class="status"><strong>請確認</strong>{html.escape(error)}</div>'
            if error
            else ""
        )
        csrf = html.escape(request.csrf_token())
        body = f"""
          <h1>完成會員申請</h1>
          <p>只需要兩項資料。登入方式已驗證，不必再選角色。</p>
          {error_html}
          <form method="post">
            <input type="hidden" name="csrf_token" value="{csrf}"/>
            <label for="organization_name">目前主要所屬團體</label>
            <input id="organization_name" name="organization_name" type="text"
                   maxlength="160" required value="{org_value}"
                   placeholder="例如：五常里、社區組織、公司、學校；沒有可填「個人」"/>
            <label>是否位於五常社區轄區內</label>
            <div class="choices">
              <label class="choice"><input type="radio" name="membership_category"
                value="in_community_jurisdiction" required{in_checked}/> 是，位於轄區內</label>
              <label class="choice"><input type="radio" name="membership_category"
                value="outside_community_jurisdiction" required{out_checked}/> 否，位於轄區外</label>
            </div>
            <div class="actions">
              <button class="button" type="submit">完成申請</button>
              <a class="button secondary" href="/wuchang/member/account">稍後再填</a>
            </div>
          </form>
        """
        return request.make_response(
            _page("完成會員申請", body),
            headers=[("Content-Type", "text/html; charset=utf-8")],
        )
