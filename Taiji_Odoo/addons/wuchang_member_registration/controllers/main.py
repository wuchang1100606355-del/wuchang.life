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
