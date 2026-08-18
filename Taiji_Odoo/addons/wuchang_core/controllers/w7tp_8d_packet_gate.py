# -*- coding: utf-8 -*-
from __future__ import annotations

from odoo import fields
from odoo.http import Response


HOLD_NO_VERIFIER_REASON = "HOLD_NATIVE_8D_VERIFIER_NOT_BOUND"
GUEST_MODE = "GUEST_SERVICE_SESSION"
MEMBER_MODE = "VERIFIED_8D_MEMBER"


def _get_any_ref(record, names):
    if not record:
        return False
    for name in names:
        if name in record._fields:
            value = record[name]
            if value:
                return value
    return False


def _resolve_existing_canonical_8d_verifier():
    """Thin adapter hook for an existing canonical verifier.

    No bound verifier exists in the currently permitted workspace scope, so
    the adapter deliberately returns None instead of inventing a second
    authority system.
    """

    return None


def validate_xiaoj_8d_packet_gate(request):
    """
    Official XiaoJ entrance gate.

    Member identity authority is only the 8D ADI identity packet.
    Odoo user/partner refs, device refs, table refs, and service refs are only
    coordinates or evidence. They do not authorize identity by themselves.
    """

    env = request.env
    user = env.user.sudo()
    partner = getattr(user, "partner_id", False)
    if partner:
        partner = partner.sudo()
    icp = env["ir.config_parameter"].sudo()

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
    member_packet_ref = user_packet_ref or partner_packet_ref

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

    verifier = _resolve_existing_canonical_8d_verifier()

    if member_packet_ref:
        if verifier is None:
            return {
                "allowed": False,
                "mode": "DENY",
                "identity_verified": False,
                "identity_authority": "NONE",
                "read_allowed": True,
                "write_allowed": False,
                "plaintext_allowed": False,
                "reason": HOLD_NO_VERIFIER_REASON,
                "packet_ref": str(member_packet_ref),
                "member_packet_ref": str(member_packet_ref),
                "ai_identity_ref": str(ai_identity_ref or ""),
                "device_ref": str(device_ref or ""),
                "xiaoj_service_ref": str(xiaoj_service_ref or ""),
                "execution_authorized": False,
            }

        verification = verifier.verify(
            request=request,
            packet_ref=str(member_packet_ref),
            ai_identity_ref=str(ai_identity_ref or ""),
            device_ref=str(device_ref or ""),
            xiaoj_service_ref=str(xiaoj_service_ref or ""),
        )
        if not verification.get("verified"):
            return {
                "allowed": False,
                "mode": "DENY",
                "identity_verified": False,
                "identity_authority": "NONE",
                "read_allowed": True,
                "write_allowed": False,
                "plaintext_allowed": False,
                "reason": verification.get("reason") or "VERIFIER_DENIED",
                "packet_ref": str(member_packet_ref),
                "execution_authorized": False,
            }
        return {
            "allowed": True,
            "mode": MEMBER_MODE,
            "packet_ref": str(member_packet_ref),
            "identity_verified": True,
            "identity_authority": "8D_ADI_IDENTITY_PACKET",
            "read_allowed": True,
            "write_allowed": bool(verification.get("execution_authorized", False)),
            "plaintext_allowed": False,
            "verification_receipt_ref": str(verification.get("verification_receipt_ref") or ""),
            "execution_authorized": bool(verification.get("execution_authorized", False)),
        }

    counter_ai_packet_ref = icp.get_param("wuchang.w7tp.counter_ai_8d_packet_ref")
    if counter_ai_packet_ref:
        return {
            "allowed": True,
            "mode": GUEST_MODE,
            "packet_ref": str(counter_ai_packet_ref),
            "identity_verified": False,
            "identity_authority": "NONE",
            "read_allowed": True,
            "write_allowed": False,
            "guest_only": True,
            "plaintext_allowed": False,
            "execution_authorized": False,
        }

    return {
        "allowed": False,
        "mode": "DENY",
        "identity_verified": False,
        "identity_authority": "NONE",
        "read_allowed": False,
        "write_allowed": False,
        "plaintext_allowed": False,
        "reason": "NO_GUEST_CAPABILITY_PACKET_BOUND",
        "execution_authorized": False,
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
<h1>小J 入口暫時無法進入</h1>
<p class="bad">READ_DENY / WRITE_DENY</p>
<p>原因：<code>{reason}</code></p>
<p>會員身份只能由 8D ADI identity packet 驗證；若沒有正式 verifier，會員權限會維持關閉。</p>
<p class="ok">Guest service session 仍可在具備 counter AI capability 時以唯讀方式進入。</p>
</div>
</body>
</html>
"""
    return Response(html, content_type="text/html; charset=utf-8", status=403)
