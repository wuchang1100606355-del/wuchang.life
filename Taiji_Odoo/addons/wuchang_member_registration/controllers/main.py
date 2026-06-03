from odoo import http
from odoo.http import request


class WuchangMemberRegistrationController(http.Controller):

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
