from __future__ import annotations

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..services.sovereign_voucher_checkout import canonical_sha256, phone_last3_hmac
from .capability_seat import CAP_MEMBER_LOOKUP


PHONE_LOOKUP_PEPPER_PARAM = "wuchang.member.phone_last3_lookup_pepper"


class WuchangMemberLowRiskLookup(models.Model):
    _name = "wuchang.member.low.risk.lookup"
    _description = "WuChang Masked Member Low-Risk Lookup Proof"
    _order = "organization_ref, id desc"

    organization_ref = fields.Char(required=True, index=True)
    member_identity_id = fields.Many2one(
        "wuchang.member.identity.code",
        required=True,
        index=True,
        ondelete="cascade",
    )
    masked_display_label = fields.Char(required=True)
    phone_last3_hmac = fields.Char(required=True, index=True, copy=False)
    active = fields.Boolean(default=True, index=True)
    audit_hash = fields.Char(readonly=True, index=True)

    _sql_constraints = [
        (
            "member_lookup_org_unique",
            "unique(organization_ref, member_identity_id)",
            "One low-risk lookup proof per organization/member is allowed.",
        ),
    ]

    @api.model
    def _lookup_pepper(self):
        pepper = self.env["ir.config_parameter"].sudo().get_param(
            PHONE_LOOKUP_PEPPER_PARAM,
            "",
        )
        if not isinstance(pepper, str) or len(pepper) < 32:
            raise UserError(_("HOLD_PHONE_LOOKUP_PEPPER_NOT_CONFIGURED"))
        return pepper

    @api.model
    def configure_lookup(
        self,
        organization_ref,
        member_identity,
        masked_display_label,
        last_three,
    ):
        if not self.env.user.has_group(
            "wuchang_member_registration.group_wuchang_member_admin"
        ):
            raise UserError(_("HOLD_MEMBER_LOOKUP_GOVERNANCE_ADMIN_REQUIRED"))
        if not member_identity or not member_identity.exists():
            raise UserError(_("HOLD_MEMBER_IDENTITY_REQUIRED"))
        digest = phone_last3_hmac(
            organization_ref=organization_ref,
            last_three=last_three,
            pepper=self._lookup_pepper(),
        )
        record = self.search(
            [
                ("organization_ref", "=", organization_ref),
                ("member_identity_id", "=", member_identity.id),
            ],
            limit=1,
        )
        vals = {
            "organization_ref": organization_ref,
            "member_identity_id": member_identity.id,
            "masked_display_label": masked_display_label,
            "phone_last3_hmac": digest,
            "active": True,
        }
        if record:
            record.write(vals)
        else:
            record = self.create(vals)
        record._refresh_audit_hash()
        return record

    def _refresh_audit_hash(self):
        for rec in self:
            rec.audit_hash = canonical_sha256(
                {
                    "organization_ref": rec.organization_ref,
                    "member_ref": rec.member_identity_id.service_code_masked,
                    "masked_display_label": rec.masked_display_label,
                    "phone_lookup_digest": rec.phone_last3_hmac,
                    "active": rec.active,
                }
            )

    @api.model
    def _match_for_staff(self, *, organization_ref, seat, last_three):
        if not self.env.user.has_group(
            "wuchang_member_registration.group_wuchang_member_staff"
        ):
            raise UserError(_("HOLD_MEMBER_STAFF_SEAT_REQUIRED"))
        if (
            not seat
            or not seat.exists()
            or seat.organization_ref != organization_ref
            or not seat.has_capability(CAP_MEMBER_LOOKUP)
        ):
            raise UserError(_("HOLD_MEMBER_LOOKUP_CAPABILITY_SEAT_REQUIRED"))
        digest = phone_last3_hmac(
            organization_ref=organization_ref,
            last_three=last_three,
            pepper=self._lookup_pepper(),
        )
        matches = self.sudo().search(
            [
                ("organization_ref", "=", organization_ref),
                ("phone_last3_hmac", "=", digest),
                ("active", "=", True),
            ],
            limit=2,
        )
        if len(matches) == 0:
            return self.browse(), "NO_MATCH"
        if len(matches) > 1:
            return self.browse(), "AMBIGUOUS"
        return matches, "MATCH"
