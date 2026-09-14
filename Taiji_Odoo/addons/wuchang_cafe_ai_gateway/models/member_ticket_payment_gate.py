import hashlib
import json
import re
from datetime import datetime, timezone

from odoo import api, fields, models, _
from odoo.exceptions import UserError


PACKET_SCHEMA = "W7TP_XIAOJ_BUSINESS_BACKEND_MEMBER_TICKET_PAYMENT_GATE_PACKET_V1"


def _now_utc():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _stable_hash(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _false_boundary_flags():
    return {
        "secret_read": False,
        "member_plaintext_read": False,
        "raw_audio_saved": False,
        "db_write": False,
        "pos_write": False,
        "payment_capture": False,
        "ticket_redeem": False,
        "external_api_call": False,
        "service_restart": False,
        "deploy": False,
    }


class WuchangBusinessBackendMemberTicketPaymentGate(models.Model):
    _name = "wuchang.business.backend.member.ticket.payment.gate"
    _description = "WuChang Business Backend Member Ticket Payment Gate"
    _order = "create_date desc, id desc"

    name = fields.Char(default="MEMBER-TICKET-PAYMENT-GATE", required=True, index=True)
    member_identity_ref = fields.Char(help="Ref only. Do not paste member plaintext.")
    member_authority_state = fields.Selection(
        [
            ("unknown", "Unknown"),
            ("guest_ref_only", "Guest Ref Only"),
            ("member_ref_only", "Member Ref Only"),
            ("verified_ref", "Verified Ref"),
            ("hold", "Hold"),
        ],
        default="unknown",
        index=True,
    )
    ticket_ref = fields.Char(help="Ticket ref only.")
    ticket_state = fields.Selection(
        [
            ("not_required", "Not Required"),
            ("missing", "Missing"),
            ("ref_present", "Ref Present"),
            ("expired", "Expired"),
            ("mismatch", "Mismatch"),
            ("hold", "Hold"),
            ("pass", "Pass"),
        ],
        default="not_required",
        index=True,
    )
    entitlement_ref = fields.Char(help="Entitlement ref only.")
    entitlement_state = fields.Selection(
        [
            ("not_required", "Not Required"),
            ("missing", "Missing"),
            ("ref_present", "Ref Present"),
            ("expired", "Expired"),
            ("mismatch", "Mismatch"),
            ("hold", "Hold"),
            ("pass", "Pass"),
        ],
        default="not_required",
        index=True,
    )
    voucher_ref = fields.Char(help="Voucher dry-run ref only.")
    voucher_state = fields.Selection(
        [
            ("not_required", "Not Required"),
            ("missing", "Missing"),
            ("ref_present", "Ref Present"),
            ("expired", "Expired"),
            ("mismatch", "Mismatch"),
            ("hold", "Hold"),
            ("pass", "Pass"),
        ],
        default="not_required",
        index=True,
    )
    happiness_coin_ref = fields.Char(help="Happiness coin dry-run ref only.")
    happiness_coin_state = fields.Selection(
        [
            ("not_required", "Not Required"),
            ("missing", "Missing"),
            ("ref_present", "Ref Present"),
            ("expired", "Expired"),
            ("mismatch", "Mismatch"),
            ("hold", "Hold"),
            ("pass", "Pass"),
        ],
        default="not_required",
        index=True,
    )
    cart_ref = fields.Char(help="Cart/candidate order ref only.")
    product_menu_quality_ref = fields.Char(help="Product/menu quality packet or row ref.")
    product_menu_quality_state = fields.Selection(
        [
            ("unknown", "Unknown"),
            ("pass", "Pass"),
            ("approved", "Approved"),
            ("ready", "Ready"),
            ("hold", "Hold"),
            ("reject", "Reject"),
        ],
        default="unknown",
        index=True,
    )
    odoo_product_ref = fields.Char(help="Odoo product authority ref.")
    price_ref = fields.Char(help="Price authority ref.")
    custom_options_ref = fields.Char(help="Custom Options JSON ref.")
    photo_evidence_ref = fields.Char(help="Real or staff-approved photo evidence ref.")
    photo_evidence_state = fields.Selection(
        [
            ("unknown", "Unknown"),
            ("real_photo_ref", "Real Photo Ref"),
            ("staff_approved_photo_ref", "Staff Approved Photo Ref"),
            ("generated_image_only", "Generated Image Only"),
        ],
        default="unknown",
        index=True,
    )
    consent_ref = fields.Char(help="Consent ref only.")
    consent_state = fields.Selection(
        [
            ("unknown", "Unknown"),
            ("missing", "Missing"),
            ("ref_present", "Ref Present"),
            ("pass", "Pass"),
            ("hold", "Hold"),
        ],
        default="unknown",
        index=True,
    )
    pre_payment_gate_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("ready_for_dryrun", "Ready For Dry-run"),
            ("hold", "Hold"),
            ("rejected", "Rejected"),
            ("approved_dryrun_only", "Approved Dry-run Only"),
        ],
        default="draft",
        index=True,
    )
    ai_candidate_state = fields.Selection(
        [
            ("unknown", "Unknown"),
            ("candidate_only", "Candidate Only"),
            ("staff_review_required", "Staff Review Required"),
            ("blocked", "Blocked"),
        ],
        default="unknown",
        index=True,
    )
    payment_action_requested = fields.Boolean(default=False, help="Must remain false in P1 dry-run.")
    blocker_generated_image_only = fields.Boolean(readonly=True)
    blocker_missing_member_authority = fields.Boolean(readonly=True)
    blocker_missing_ticket_or_entitlement = fields.Boolean(readonly=True)
    blocker_missing_price = fields.Boolean(readonly=True)
    blocker_missing_custom_options = fields.Boolean(readonly=True)
    blocker_missing_photo_evidence = fields.Boolean(readonly=True)
    blocker_missing_consent = fields.Boolean(readonly=True)
    blocker_product_menu_quality_not_pass = fields.Boolean(readonly=True)
    blocker_payment_action_requested = fields.Boolean(readonly=True)
    final_gate_decision = fields.Selection(
        [
            ("ALLOW_DRYRUN", "ALLOW_DRYRUN"),
            ("HOLD", "HOLD"),
            ("REJECT", "REJECT"),
        ],
        default="HOLD",
        readonly=True,
        index=True,
    )
    packet_json = fields.Text(readonly=True)
    packet_hash = fields.Char(readonly=True, index=True)
    notes = fields.Text(help="Safe notes only. Use refs, states, hashes, and placeholders.")

    def _contains_plaintext_or_secret_shape(self, value):
        text = str(value or "")
        return bool(
            re.search(r"sk-[A-Za-z0-9_-]{12,}", text)
            or re.search(r"(?i)(access|refresh|id)_token\s*[:=]\s*\S+", text)
            or re.search(r"(?i)api[_ -]?key\s*[:=]\s*\S+", text)
            or re.search(r"(?i)(secret|password)\s*[:=]\s*\S+", text)
            or re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
            or re.search(r"09\d{2}[- ]?\d{3}[- ]?\d{3}", text)
            or re.search(r"\b[A-Z][12]\d{8}\b", text)
        )

    @api.constrains(
        "member_identity_ref",
        "ticket_ref",
        "entitlement_ref",
        "voucher_ref",
        "happiness_coin_ref",
        "cart_ref",
        "product_menu_quality_ref",
        "odoo_product_ref",
        "price_ref",
        "custom_options_ref",
        "photo_evidence_ref",
        "consent_ref",
        "notes",
    )
    def _check_ref_only_boundaries(self):
        for rec in self:
            values = [
                rec.member_identity_ref,
                rec.ticket_ref,
                rec.entitlement_ref,
                rec.voucher_ref,
                rec.happiness_coin_ref,
                rec.cart_ref,
                rec.product_menu_quality_ref,
                rec.odoo_product_ref,
                rec.price_ref,
                rec.custom_options_ref,
                rec.photo_evidence_ref,
                rec.consent_ref,
                rec.notes,
            ]
            if any(rec._contains_plaintext_or_secret_shape(value) for value in values):
                raise UserError(_("Only refs, states, hashes, and placeholders are allowed in this P1 gate."))

    def _ticket_or_entitlement_missing(self):
        states = [
            self.ticket_state,
            self.entitlement_state,
            self.voucher_state,
            self.happiness_coin_state,
        ]
        useful_states = {"ref_present", "pass", "not_required"}
        return not any(state in useful_states for state in states)

    def _build_packet(self, blockers, final_decision):
        body = {
            "name": self.name,
            "member_identity_ref": self.member_identity_ref or "",
            "member_authority_state": self.member_authority_state,
            "ticket_ref": self.ticket_ref or "",
            "ticket_state": self.ticket_state,
            "entitlement_ref": self.entitlement_ref or "",
            "entitlement_state": self.entitlement_state,
            "voucher_ref": self.voucher_ref or "",
            "voucher_state": self.voucher_state,
            "happiness_coin_ref": self.happiness_coin_ref or "",
            "happiness_coin_state": self.happiness_coin_state,
            "cart_ref": self.cart_ref or "",
            "product_menu_quality_ref": self.product_menu_quality_ref or "",
            "product_menu_quality_state": self.product_menu_quality_state,
            "odoo_product_ref": self.odoo_product_ref or "",
            "price_ref": self.price_ref or "",
            "custom_options_ref": self.custom_options_ref or "",
            "photo_evidence_ref": self.photo_evidence_ref or "",
            "photo_evidence_state": self.photo_evidence_state,
            "consent_ref": self.consent_ref or "",
            "consent_state": self.consent_state,
            "pre_payment_gate_state": self.pre_payment_gate_state,
            "ai_candidate_state": self.ai_candidate_state,
            "blockers": blockers,
            "final_gate_decision": final_decision,
            "allowed_decisions": ["ALLOW_DRYRUN", "HOLD", "REJECT"],
            "side_effects": _false_boundary_flags(),
        }
        packet = {
            "packet_type": PACKET_SCHEMA,
            "run_id": f"odoo:wuchang.business.backend.member.ticket.payment.gate:{self.id or 'new'}",
            "created_at": _now_utc(),
            "body": body,
        }
        packet["packet_hash"] = _stable_hash(packet)
        return packet

    def action_build_member_ticket_payment_gate(self):
        for rec in self:
            rec._check_ref_only_boundaries()
            blocker_values = {
                "blocker_generated_image_only": rec.photo_evidence_state == "generated_image_only",
                "blocker_missing_member_authority": rec.member_authority_state not in {"guest_ref_only", "member_ref_only", "verified_ref"}
                or not rec.member_identity_ref,
                "blocker_missing_ticket_or_entitlement": rec._ticket_or_entitlement_missing(),
                "blocker_missing_price": not rec.price_ref,
                "blocker_missing_custom_options": not rec.custom_options_ref,
                "blocker_missing_photo_evidence": not rec.photo_evidence_ref,
                "blocker_missing_consent": rec.consent_state not in {"ref_present", "pass"} or not rec.consent_ref,
                "blocker_product_menu_quality_not_pass": rec.product_menu_quality_state not in {"pass", "approved", "ready"},
                "blocker_payment_action_requested": rec.payment_action_requested,
            }
            blockers = [key for key, value in blocker_values.items() if value]
            if blocker_values["blocker_payment_action_requested"]:
                decision = "REJECT"
                gate_state = "rejected"
            elif blockers:
                decision = "HOLD"
                gate_state = "hold"
            else:
                decision = "ALLOW_DRYRUN"
                gate_state = "approved_dryrun_only"
            packet = rec._build_packet(blockers, decision)
            rec.write(
                {
                    **blocker_values,
                    "final_gate_decision": decision,
                    "pre_payment_gate_state": gate_state,
                    "packet_json": json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True),
                    "packet_hash": packet["packet_hash"],
                }
            )
