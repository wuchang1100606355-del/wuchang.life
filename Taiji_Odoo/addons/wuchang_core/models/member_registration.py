# -*- coding: utf-8 -*-
from odoo import api, fields, models


class WuchangMemberRegistration(models.TransientModel):
    _name = "wuchang.member.registration"
    _description = "Wuchang Member Registration 8D Packet Gate"

    name = fields.Char(string="Registration Ref", default="Wuchang 8D Registration")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("packet_required", "8D Packet Required"),
            ("packet_ready", "8D Packet Ready"),
            ("device_required", "Device Binding Required"),
            ("ai_required", "AI Binding Required"),
            ("ready", "Ready"),
            ("denied", "Denied"),
        ],
        default="packet_required",
        string="State",
    )

    partner_id = fields.Many2one("res.partner", string="Partner")
    user_id = fields.Many2one("res.users", string="User", default=lambda self: self.env.user)
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company)

    # 8D packet authority carrier. QR/code/url are only references.
    packet_ref = fields.Char(string="8D Packet Ref")
    packet_hash_ref = fields.Char(string="8D Packet Hash Ref")
    five_d_ref = fields.Char(string="5D Ref")
    ai_identity_ref = fields.Char(string="AI Identity Ref")
    device_ref = fields.Char(string="Device Ref")
    xiaoj_service_ref = fields.Char(string="Dedicated XiaoJ Service Ref")
    auth_url_ref = fields.Char(string="Authorization URL Ref")
    auth_scope = fields.Char(string="Authorization Scope")

    # Generative transmission fields.
    total_field_feature_code_ref = fields.Char(string="Total Field Feature Code Ref")
    generation_code_ref = fields.Char(string="Receiver Generation Code Ref")
    gt_tx_enabled = fields.Boolean(string="GT TX Enabled", default=False)
    gt_rx_enabled = fields.Boolean(string="GT RX Enabled", default=False)

    # No-plaintext evidence refs only.
    masked_member_ref = fields.Char(string="Masked Member Ref")
    behavior_log_ref = fields.Char(string="No-Plaintext Behavior Log Ref")
    no_plaintext_receipt = fields.Char(string="No-Plaintext Receipt")
    failure_receipt = fields.Char(string="Failure Receipt")
    note = fields.Text(string="Note")

    read_allowed = fields.Boolean(string="Read Allowed", compute="_compute_gate", store=False)
    write_allowed = fields.Boolean(string="Write Allowed", compute="_compute_gate", store=False)
    gate_message = fields.Char(string="Gate Message", compute="_compute_gate", store=False)

    @api.depends("packet_ref", "ai_identity_ref", "device_ref", "xiaoj_service_ref")
    def _compute_gate(self):
        for rec in self:
            member_ready = bool(rec.packet_ref and rec.ai_identity_ref and rec.device_ref and rec.xiaoj_service_ref)
            counter_ai_packet = self.env["ir.config_parameter"].sudo().get_param(
                "wuchang.w7tp.counter_ai_8d_packet_ref"
            )
            if member_ready:
                rec.read_allowed = True
                rec.write_allowed = True
                rec.gate_message = "MEMBER_8D_PACKET_READY"
            elif counter_ai_packet:
                rec.read_allowed = True
                rec.write_allowed = False
                rec.gate_message = "COUNTER_AI_GUEST_PACKET_ONLY"
            else:
                rec.read_allowed = False
                rec.write_allowed = False
                rec.gate_message = "NO_VALID_8D_PACKET"

    def action_generate_8d_packet(self):
        for rec in self:
            if not rec.packet_ref:
                rec.packet_ref = "w7tp://8d-packet/member/registration/%s" % (rec.user_id.id or "guest")
            rec.state = "packet_ready"
        return True

    def action_bind_device(self):
        for rec in self:
            if not rec.device_ref:
                rec.device_ref = "device_ref_pending"
            rec.state = "device_required" if rec.device_ref == "device_ref_pending" else "ready"
        return True

    def action_bind_ai(self):
        for rec in self:
            if not rec.ai_identity_ref:
                rec.ai_identity_ref = "ai_identity_ref_pending"
            rec.state = "ai_required" if rec.ai_identity_ref == "ai_identity_ref_pending" else "ready"
        return True

    def action_confirm(self):
        for rec in self:
            if rec.read_allowed:
                rec.state = "ready"
            else:
                rec.state = "denied"
        return True

    def action_cancel(self):
        self.write({"state": "denied"})
        return True

    def action_clear_session(self):
        self.write({
            "packet_ref": False,
            "packet_hash_ref": False,
            "ai_identity_ref": False,
            "device_ref": False,
            "xiaoj_service_ref": False,
            "auth_url_ref": False,
            "generation_code_ref": False,
            "state": "packet_required",
        })
        return True
