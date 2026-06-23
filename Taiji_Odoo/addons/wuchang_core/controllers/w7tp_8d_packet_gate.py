# -*- coding: utf-8 -*-
from odoo import fields
from odoo.http import Response

def _get_any_ref(record, names):
    if not record:
        return False
    for name in names:
        if name in record._fields:
            value = record[name]
            if value:
                return value
    return False

def validate_xiaoj_8d_packet_gate(request):
    """
    Official XiaoJ entrance gate.

    Required authority is a valid 8D packet or controlled packet_ref.
    The 8D packet is the carrier for:
    - AI identity
    - device binding
    - Odoo function authority
    - AI function authority
    - dedicated XiaoJ service
    - association-verifiable true identity
    - no-plaintext front-stage behavior refs
    """
    env = request.env
    user = env.user.sudo()
    partner = user.partner_id.sudo() if user and user.partner_id else False
    icp = env["ir.config_parameter"].sudo()

    association_root_packet_ref = icp.get_param("wuchang.w7tp.association_root_8d_packet_ref")
    counter_ai_packet_ref = icp.get_param("wuchang.w7tp.counter_ai_8d_packet_ref")

    if not association_root_packet_ref:
        return {
            "allowed": False,
            "mode": "DENY",
            "reason": "ASSOCIATION_ROOT_8D_PACKET_MISSING",
            "read_allowed": False,
            "write_allowed": False,
        }

    user_packet_ref = _get_any_ref(user, [
        "x_w7tp_8d_packet_ref",
        "x_w7tp_8d_packet",
        "x_w7tp_packet_ref",
    ])

    partner_packet_ref = _get_any_ref(partner, [
        "x_w7tp_8d_packet_ref",
        "x_w7tp_8d_packet",
        "x_w7tp_packet_ref",
    ])

    ai_identity_ref = _get_any_ref(user, [
        "x_w7tp_ai_identity_ref",
        "x_w7tp_ai_binding_ref",
        "x_xiaoj_ai_identity_ref",
    ]) or _get_any_ref(partner, [
        "x_w7tp_ai_identity_ref",
        "x_w7tp_ai_binding_ref",
        "x_xiaoj_ai_identity_ref",
    ])

    device_ref = request.session.get("w7tp_device_ref") or request.session.get("device_ref")

    xiaoj_service_ref = _get_any_ref(user, [
        "x_w7tp_xiaoj_service_ref",
        "x_xiaoj_service_ref",
    ]) or _get_any_ref(partner, [
        "x_w7tp_xiaoj_service_ref",
        "x_xiaoj_service_ref",
    ])

    member_packet_ref = user_packet_ref or partner_packet_ref

    if member_packet_ref and ai_identity_ref and device_ref and xiaoj_service_ref:
        return {
            "allowed": True,
            "mode": "MEMBER_8D_PACKET",
            "packet_ref": str(member_packet_ref),
            "ai_identity_ref": str(ai_identity_ref),
            "device_ref": str(device_ref),
            "xiaoj_service_ref": str(xiaoj_service_ref),
            "read_allowed": True,
            "write_allowed": True,
            "plaintext_allowed": False,
        }

    if counter_ai_packet_ref:
        return {
            "allowed": True,
            "mode": "COUNTER_AI_GUEST_PACKET",
            "packet_ref": str(counter_ai_packet_ref),
            "read_allowed": True,
            "write_allowed": False,
            "guest_only": True,
            "plaintext_allowed": False,
        }

    return {
        "allowed": False,
        "mode": "DENY",
        "reason": "NO_VALID_8D_PACKET_OR_COUNTER_AI_PACKET",
        "read_allowed": False,
        "write_allowed": False,
        "plaintext_allowed": False,
    }

def render_xiaoj_8d_packet_denied_page(gate):
    reason = gate.get("reason", "DENY")
    html = f"""
<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>小J 8維封包閘門</title>
<style>
body{{font-family:system-ui,"Noto Sans TC",sans-serif;background:#111;color:#fff;margin:0;padding:32px}}
.card{{max-width:760px;margin:auto;background:#1b1b1b;border:1px solid #333;border-radius:18px;padding:28px}}
h1{{margin-top:0}}
code{{background:#000;padding:4px 8px;border-radius:8px}}
.bad{{color:#ff9b9b}}
.ok{{color:#9bffcf}}
</style>
</head>
<body>
<div class="card">
<h1>小J 入口尚未通過 8維封包</h1>
<p class="bad">READ_DENY / WRITE_DENY</p>
<p>原因：<code>{reason}</code></p>
<p>本入口需要有效 8維封包或受控 packet_ref。</p>
<p>8維封包必須包含或參照：AI身分、設備綁定、Odoo功能、AI功能、專屬小J服務、真實身分協會可證、非明文前段留存與執行權限。</p>
<p class="ok">訪客點餐需由櫃台AI服務8維封包進入；會員服務需由 Odoo 驗證會員8維封包。</p>
</div>
</body>
</html>
"""
    return Response(html, content_type="text/html; charset=utf-8", status=403)
