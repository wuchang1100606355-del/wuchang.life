from __future__ import annotations

import json
import secrets

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..services.sovereign_voucher_checkout import (
    build_lookup_receipt,
    build_owner_confirmation,
    build_red_tea_redeem_request,
    build_transaction_evidence,
    canonical_sha256,
    hash_ref,
)
from .capability_seat import (
    CAP_MEMBER_LOOKUP,
    CAP_VOUCHER_REQUEST,
    NODE_COMPUTE_CAPABILITY_ID,
)

FEATURE_KEY = "sandbox.liaoguo_red_tea_voucher_redeem"
SANDBOX_MEMBER_PARAM = "wuchang.sandbox.liaoguo_red_tea.member_ref"
SANDBOX_ORG_PARAM = "wuchang.sandbox.liaoguo_red_tea.organization_ref"
SANDBOX_PRODUCT_PARAM = "wuchang.sandbox.liaoguo_red_tea.product_ref"

def _now_string():
    return fields.Datetime.to_string(fields.Datetime.now())


def _product_ref(voucher):
    product = voucher.reward_product_id
    if not product:
        return ""
    return product.default_code or f"product.template:{product.id}"


class WuchangSovereignVoucherCheckout(models.Model):
    _name = "wuchang.sovereign.voucher.checkout"
    _description = "WuChang Sovereign Voucher Checkout"
    _order = "create_date desc, id desc"

    name = fields.Char(default="Sovereign Voucher Checkout", readonly=True)
    authorization_ref = fields.Char(readonly=True, required=True, index=True, copy=False)
    idempotency_key = fields.Char(readonly=True, required=True, index=True, copy=False)
    state = fields.Selection(
        [
            ("lookup_verified", "Lookup Verified"),
            ("pending_owner_confirmation", "Pending Owner Confirmation"),
            ("authorized", "Authorized"),
            ("consumed", "Consumed"),
            ("rejected", "Rejected"),
            ("hold", "Hold"),
        ],
        default="lookup_verified",
        required=True,
        index=True,
        readonly=True,
    )
    organization_ref = fields.Char(required=True, readonly=True, index=True)
    seat_id = fields.Many2one(
        "wuchang.organization.capability.seat",
        required=True,
        readonly=True,
        ondelete="restrict",
    )
    member_identity_id = fields.Many2one(
        "wuchang.member.identity.code",
        required=True,
        readonly=True,
        ondelete="restrict",
        index=True,
    )
    member_ref = fields.Char(required=True, readonly=True, index=True)
    masked_display_label = fields.Char(readonly=True)
    requested_by_id = fields.Many2one("res.users", readonly=True, index=True)
    lookup_receipt_hash = fields.Char(required=True, readonly=True, index=True)
    lookup_receipt_json = fields.Text(readonly=True)
    voucher_count_before = fields.Integer(readonly=True)
    voucher_count_after = fields.Integer(readonly=True)
    voucher_id = fields.Many2one(
        "wuchang.member.voucher",
        readonly=True,
        ondelete="restrict",
    )
    voucher_ref = fields.Char(readonly=True, index=True)
    voucher_hash_before = fields.Char(readonly=True, index=True)
    voucher_hash_after = fields.Char(readonly=True, index=True)
    product_ref = fields.Char(readonly=True, index=True)
    order_ref = fields.Char(readonly=True, index=True)
    request_hash = fields.Char(readonly=True, index=True)
    request_json = fields.Text(readonly=True)
    owner_confirmation_ref = fields.Char(readonly=True, index=True)
    owner_confirmation_hash = fields.Char(readonly=True, index=True)
    owner_confirmation_json = fields.Text(readonly=True)
    transaction_hash = fields.Char(readonly=True, index=True)
    evidence_json = fields.Text(readonly=True)
    node_compute_capability_id = fields.Char(
        default=NODE_COMPUTE_CAPABILITY_ID,
        readonly=True,
    )

    _sql_constraints = [
        ("authorization_ref_unique", "unique(authorization_ref)", "Authorization ref must be unique."),
        ("checkout_idempotency_unique", "unique(idempotency_key)", "Checkout idempotency key must be unique."),
    ]

    @api.model
    def _sandbox_refs(self):
        params = self.env["ir.config_parameter"].sudo()
        refs = {
            "member_ref": params.get_param(SANDBOX_MEMBER_PARAM, ""),
            "organization_ref": params.get_param(SANDBOX_ORG_PARAM, ""),
            "product_ref": params.get_param(SANDBOX_PRODUCT_PARAM, ""),
        }
        if not all(refs.values()):
            raise UserError(_("HOLD_LIAOGUO_RED_TEA_SANDBOX_REFS_NOT_CONFIGURED"))
        return refs

    @api.model
    def _require_feature(self):
        if not self.env["wuchang.community.feature.gate"].is_enabled(FEATURE_KEY, default=False):
            raise UserError(_("HOLD_LIAOGUO_RED_TEA_SANDBOX_DISABLED"))

    @api.model
    def _seat(self, seat_ref, organization_ref):
        seat = self.env["wuchang.organization.capability.seat"].search(
            [("seat_ref", "=", seat_ref)],
            limit=1,
        )
        if (
            not seat
            or seat.organization_ref != organization_ref
            or not seat.has_capability(CAP_MEMBER_LOOKUP)
            or not seat.has_capability(CAP_VOUCHER_REQUEST)
        ):
            raise UserError(_("HOLD_CHECKOUT_CAPABILITY_SEAT_INVALID"))
        return seat

    @api.model
    def _available_vouchers(self, member_identity, product_ref):
        now = fields.Datetime.now()
        vouchers = self.env["wuchang.member.voucher"].sudo().search(
            [
                ("member_identity_id", "=", member_identity.id),
                ("state", "in", ["issued", "reserved"]),
                "|",
                ("expires_at", "=", False),
                ("expires_at", ">=", now),
            ],
            order="expires_at asc, issued_at asc, id asc",
        )
        return vouchers.filtered(lambda voucher: _product_ref(voucher) == product_ref)

    @api.model
    def preview_red_tea_entitlement(self, *, seat_ref, last_three):
        self._require_feature()
        refs = self._sandbox_refs()
        seat = self._seat(seat_ref, refs["organization_ref"])
        lookup, match_state = self.env["wuchang.member.low.risk.lookup"]._match_for_staff(
            organization_ref=refs["organization_ref"],
            seat=seat,
            last_three=last_three,
        )
        now_text = _now_string()
        if match_state != "MATCH":
            receipt = build_lookup_receipt(
                organization_ref=refs["organization_ref"],
                seat_ref=seat.seat_ref,
                issued_at=now_text,
                matched=False,
                ambiguous=match_state == "AMBIGUOUS",
            )
            return {
                "state": "HOLD_MEMBER_LOOKUP_AMBIGUOUS" if match_state == "AMBIGUOUS" else "NO_MATCH",
                "matched": False,
                "member_plaintext": False,
                "entitlement_visible": False,
                "lookup_receipt_hash": receipt["receipt_hash"],
            }

        identity = lookup.member_identity_id
        if identity.service_code_masked != refs["member_ref"]:
            raise UserError(_("HOLD_SANDBOX_MEMBER_SCOPE_MISMATCH"))
        vouchers = self._available_vouchers(identity, refs["product_ref"])
        receipt = build_lookup_receipt(
            organization_ref=refs["organization_ref"],
            seat_ref=seat.seat_ref,
            issued_at=now_text,
            matched=True,
            member_ref=identity.service_code_masked,
            masked_display=lookup.masked_display_label,
            entitlement_count=len(vouchers),
        )
        seed = {
            "member_ref": identity.service_code_masked,
            "seat_ref": seat.seat_ref,
            "lookup_receipt_hash": receipt["receipt_hash"],
            "nonce": secrets.token_hex(16),
        }
        checkout = self.sudo().create(
            {
                "authorization_ref": hash_ref("voucher-authorization", seed),
                "idempotency_key": canonical_sha256(seed),
                "state": "lookup_verified",
                "organization_ref": refs["organization_ref"],
                "seat_id": seat.id,
                "member_identity_id": identity.id,
                "member_ref": identity.service_code_masked,
                "masked_display_label": lookup.masked_display_label,
                "requested_by_id": self.env.user.id,
                "lookup_receipt_hash": receipt["receipt_hash"],
                "lookup_receipt_json": json.dumps(receipt, ensure_ascii=False, sort_keys=True),
                "voucher_count_before": len(vouchers),
                "product_ref": refs["product_ref"],
            }
        )
        return {
            "state": "MATCH",
            "matched": True,
            "member_display": lookup.masked_display_label,
            "red_tea_voucher_count": len(vouchers),
            "checkout_ref": checkout.authorization_ref,
            "lookup_receipt_hash": receipt["receipt_hash"],
            "member_plaintext": False,
            "phone_last3_disclosed": False,
        }

    @api.model
    def request_red_tea_redeem(self, *, checkout_ref, order_ref):
        self._require_feature()
        checkout = self.sudo().search(
            [("authorization_ref", "=", checkout_ref)],
            limit=1,
        )
        if not checkout:
            raise UserError(_("HOLD_CHECKOUT_LOOKUP_NOT_FOUND"))
        if checkout.requested_by_id != self.env.user:
            raise UserError(_("HOLD_CHECKOUT_STAFF_SESSION_MISMATCH"))
        if checkout.state == "pending_owner_confirmation":
            return checkout.build_public_status()
        if checkout.state != "lookup_verified":
            raise UserError(_("HOLD_CHECKOUT_STATE_INVALID"))

        refs = self._sandbox_refs()
        if not checkout.seat_id.has_capability(CAP_VOUCHER_REQUEST):
            raise UserError(_("HOLD_VOUCHER_REQUEST_CAPABILITY_REQUIRED"))
        vouchers = self._available_vouchers(
            checkout.member_identity_id,
            refs["product_ref"],
        )
        if not vouchers:
            raise UserError(_("HOLD_NO_REDEEMABLE_RED_TEA_VOUCHER"))
        if len(vouchers) != checkout.voucher_count_before:
            raise UserError(_("HOLD_VOUCHER_COUNT_PREIMAGE_MISMATCH"))
        if checkout.voucher_count_before != 10:
            raise UserError(_("HOLD_SANDBOX_REQUIRES_EXACT_10_TO_9_PREIMAGE"))
        voucher = vouchers[0]
        lookup_receipt = json.loads(checkout.lookup_receipt_json or "{}")
        request_packet = build_red_tea_redeem_request(
            lookup_receipt=lookup_receipt,
            sandbox_member_ref=refs["member_ref"],
            sandbox_organization_ref=refs["organization_ref"],
            sandbox_product_ref=refs["product_ref"],
            voucher_ref=voucher.voucher_ref,
            voucher_hash=voucher.voucher_hash,
            order_ref=order_ref,
            issued_at=_now_string(),
        )
        idempotency_key = canonical_sha256(
            {
                "member_ref": checkout.member_ref,
                "organization_ref": checkout.organization_ref,
                "seat_ref": checkout.seat_id.seat_ref,
                "order_ref": order_ref,
                "voucher_ref": voucher.voucher_ref,
                "voucher_hash": voucher.voucher_hash,
                "product_ref": refs["product_ref"],
            }
        )
        duplicate = self.sudo().search(
            [
                ("idempotency_key", "=", idempotency_key),
                ("id", "!=", checkout.id),
            ],
            limit=1,
        )
        if duplicate:
            return duplicate.build_public_status()

        checkout.sudo().write(
            {
                "idempotency_key": idempotency_key,
                "state": "pending_owner_confirmation",
                "voucher_id": voucher.id,
                "voucher_ref": voucher.voucher_ref,
                "voucher_hash_before": voucher.voucher_hash,
                "order_ref": order_ref,
                "request_hash": request_packet["request_hash"],
                "request_json": json.dumps(request_packet, ensure_ascii=False, sort_keys=True),
                "voucher_count_before": len(vouchers),
            }
        )
        self.env["wuchang.cafe.ai.eventbook"].sudo().create(
            {
                "name": checkout.authorization_ref,
                "event_type": "ai_action",
                "source": "odoo_capability_seat",
                "session_ref": checkout.authorization_ref,
                "user_role": "clerk_capability_seat",
                "intent": "redeem_one_liaoguo_red_tea_voucher",
                "tool_name": "wuchang.sovereign.voucher.checkout",
                "risk_level": "low",
                "confirmation_required": True,
                "result": "pending",
                "payload_json": json.dumps(
                    {
                        "request_hash": request_packet["request_hash"],
                        "member_ref": checkout.member_ref,
                        "seat_ref": checkout.seat_id.seat_ref,
                        "organization_ref": checkout.organization_ref,
                        "product_ref": checkout.product_ref,
                        "voucher_count_before": checkout.voucher_count_before,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            }
        )
        return checkout.build_public_status()

    @api.model
    def pending_for_current_member(self):
        bindings = self.env["wuchang.member.external.auth"].sudo().search(
            [
                ("member_user_id", "=", self.env.user.id),
                ("binding_status", "=", "bound"),
            ]
        )
        identity_ids = bindings.mapped("member_identity_id").ids
        if not identity_ids:
            return []
        records = self.sudo().search(
            [
                ("member_identity_id", "in", identity_ids),
                ("state", "=", "pending_owner_confirmation"),
            ],
            order="create_date asc, id asc",
        )
        return [
            {
                "checkout_ref": rec.authorization_ref,
                "state": rec.state,
                "organization_ref": rec.organization_ref,
                "product_ref": rec.product_ref,
                "quantity": 1,
                "prompt_intent": "CONFIRM_USE_ONE_LIAOGUO_RED_TEA_VOUCHER",
                "member_plaintext": False,
            }
            for rec in records
        ]

    def _bound_member_channel(self):
        self.ensure_one()
        return self.env["wuchang.member.external.auth"].sudo().search(
            [
                ("member_user_id", "=", self.env.user.id),
                ("member_identity_id", "=", self.member_identity_id.id),
                ("binding_status", "=", "bound"),
            ],
            limit=1,
        )

    def _member_registration(self):
        self.ensure_one()
        return self.env["wuchang.member.registration"].search(
            [
                ("identity_code_id", "=", self.member_identity_id.id),
                ("create_uid", "=", self.env.user.id),
            ],
            limit=1,
        )

    def _member_confirmation(self, decision):
        self.ensure_one()
        binding = self._bound_member_channel()
        if not binding or not binding.verified_channel_binding_ref:
            raise UserError(_("HOLD_VERIFIED_MEMBER_CHANNEL_REQUIRED"))
        registration = self._member_registration()
        if not registration:
            raise UserError(_("HOLD_MEMBER_REGISTRATION_SESSION_REQUIRED"))
        if not self.request_hash:
            raise UserError(_("HOLD_CHECKOUT_REQUEST_HASH_REQUIRED"))

        purpose_ref = hash_ref("purpose_ref", "liaoguo_red_tea_voucher_redeem")
        scope_ref = hash_ref(
            "scope_ref",
            {
                "organization_ref": self.organization_ref,
                "member_ref": self.member_ref,
                "product_ref": self.product_ref,
                "order_ref": self.order_ref,
                "voucher_ref": self.voucher_ref,
            },
        )
        p1_evidence_ref = f"p1_evidence_ref:sha256:{self.lookup_receipt_hash}"
        consent = registration.append_member_consent_candidate(
            action_hash=self.request_hash,
            purpose_ref=purpose_ref,
            scope_refs=[scope_ref],
            effect_class="E3_SANDBOX",
            member_proof_ref=binding.verified_channel_binding_ref,
            p1_evidence_ref=p1_evidence_ref,
            decision=decision,
        )
        return build_owner_confirmation(
            request_packet=json.loads(self.request_json or "{}"),
            confirmer_member_ref=self.member_ref,
            confirmation_ref=consent["event_ref"],
            decision=decision,
            confirmed_at=_now_string(),
        )

    @api.model
    def confirm_for_current_member(self, checkout_ref, approve=True):
        record = self.sudo().search(
            [("authorization_ref", "=", checkout_ref)],
            limit=1,
        )
        if not record:
            raise UserError(_("HOLD_CHECKOUT_NOT_FOUND"))
        record = record.with_user(self.env.user)
        if record.state == "consumed":
            return record.build_public_status()
        if record.state != "pending_owner_confirmation":
            raise UserError(_("HOLD_CHECKOUT_NOT_PENDING_OWNER_CONFIRMATION"))

        decision = "CONSENT" if approve else "DENY"
        confirmation = record._member_confirmation(decision)
        if decision == "DENY":
            record.sudo().write(
                {
                    "state": "rejected",
                    "owner_confirmation_ref": confirmation["confirmation_ref"],
                    "owner_confirmation_hash": confirmation["confirmation_hash"],
                    "owner_confirmation_json": json.dumps(
                        confirmation,
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                }
            )
            return record.build_public_status()

        record.sudo().write(
            {
                "state": "authorized",
                "owner_confirmation_ref": confirmation["confirmation_ref"],
                "owner_confirmation_hash": confirmation["confirmation_hash"],
                "owner_confirmation_json": json.dumps(
                    confirmation,
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            }
        )
        return record._execute_authorized(confirmation)

    def _execute_authorized(self, confirmation):
        self.ensure_one()
        if self.state != "authorized":
            raise UserError(_("HOLD_OWNER_CONFIRMATION_REQUIRED"))
        refs = self._sandbox_refs()
        if (
            self.member_ref != refs["member_ref"]
            or self.organization_ref != refs["organization_ref"]
            or self.product_ref != refs["product_ref"]
        ):
            raise UserError(_("HOLD_SANDBOX_SCOPE_DRIFT"))

        before_vouchers = self._available_vouchers(
            self.member_identity_id,
            self.product_ref,
        )
        before_count = len(before_vouchers)
        if before_count != self.voucher_count_before or before_count != 10:
            raise UserError(_("HOLD_VOUCHER_COUNT_PREIMAGE_MISMATCH"))
        if self.voucher_id not in before_vouchers:
            raise UserError(_("HOLD_SELECTED_VOUCHER_NOT_REDEEMABLE"))

        result = self.voucher_id.sudo()._redeem_from_verified_sovereign_checkout(
            order_ref=self.order_ref,
            expected_voucher_hash=self.voucher_hash_before,
            authorization_ref=self.authorization_ref,
        )
        after_count = len(
            self._available_vouchers(
                self.member_identity_id,
                self.product_ref,
            )
        )
        evidence = build_transaction_evidence(
            request_packet=json.loads(self.request_json or "{}"),
            confirmation=confirmation,
            voucher_count_before=before_count,
            voucher_count_after=after_count,
            voucher_hash_before=result["voucher_hash_before"],
            voucher_hash_after=result["voucher_hash_after"],
            executed_at=_now_string(),
            executor_ref=f"odoo-user:{self.env.user.id}",
        )
        self.sudo().write(
            {
                "state": "consumed",
                "voucher_count_before": before_count,
                "voucher_count_after": after_count,
                "voucher_hash_before": result["voucher_hash_before"],
                "voucher_hash_after": result["voucher_hash_after"],
                "transaction_hash": evidence["transaction_hash"],
                "evidence_json": json.dumps(evidence, ensure_ascii=False, sort_keys=True),
            }
        )
        self.env["wuchang.cafe.ai.eventbook"].sudo().create(
            {
                "name": self.authorization_ref,
                "event_type": "ai_action",
                "source": "member_sovereign_confirmation",
                "session_ref": self.authorization_ref,
                "user_role": "natural_person_member",
                "intent": "redeem_one_liaoguo_red_tea_voucher",
                "tool_name": "wuchang.sovereign.voucher.checkout",
                "risk_level": "low",
                "confirmation_required": True,
                "confirmation_result": "MEMBER_CONSENT",
                "result": "success",
                "payload_json": json.dumps(
                    {
                        "request_hash": self.request_hash,
                        "owner_confirmation_ref": self.owner_confirmation_ref,
                        "transaction_hash": evidence["transaction_hash"],
                        "voucher_count_before": before_count,
                        "voucher_count_after": after_count,
                        "member_ref": self.member_ref,
                        "organization_ref": self.organization_ref,
                        "product_ref": self.product_ref,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            }
        )
        return self.build_public_status()

    def build_public_status(self):
        self.ensure_one()
        return {
            "checkout_ref": self.authorization_ref,
            "state": self.state,
            "organization_ref": self.organization_ref,
            "member_display": self.masked_display_label,
            "product_ref": self.product_ref,
            "quantity": 1,
            "voucher_count_before": self.voucher_count_before,
            "voucher_count_after": (
                self.voucher_count_after if self.state == "consumed" else None
            ),
            "request_hash": self.request_hash or "",
            "owner_confirmation_ref": self.owner_confirmation_ref or "",
            "transaction_hash": self.transaction_hash or "",
            "member_plaintext": False,
            "phone_plaintext": False,
            "happiness_coin_effect": False,
            "ai_direct_effect": False,
            "node_compute_capability_id": self.node_compute_capability_id,
        }
