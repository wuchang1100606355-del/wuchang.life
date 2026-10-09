from __future__ import annotations

import json
import secrets

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..services.sovereign_voucher_checkout import canonical_sha256, hash_ref


CAP_MEMBER_LOOKUP = "capability:member_low_risk_lookup"
CAP_VOUCHER_REQUEST = "capability:voucher_redeem_request"
NODE_COMPUTE_CAPABILITY_ID = "CAP_INTERNAL_NODE_COMPUTE_V1"


def _safe_json_list(raw):
    try:
        value = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


class WuchangOrganizationCapabilitySeat(models.Model):
    _name = "wuchang.organization.capability.seat"
    _description = "WuChang Organization Capability Seat"
    _order = "organization_ref, name, id"

    name = fields.Char(required=True)
    seat_ref = fields.Char(readonly=True, required=True, index=True, copy=False)
    organization_ref = fields.Char(required=True, index=True)
    role_ref = fields.Char(required=True, index=True)
    capability_refs_json = fields.Text(default="[]", required=True)
    state = fields.Selection(
        [("active", "Active"), ("hold", "Hold"), ("revoked", "Revoked")],
        default="hold",
        required=True,
        index=True,
    )
    masked_data_only = fields.Boolean(default=True, readonly=True)
    member_plaintext_allowed = fields.Boolean(default=False, readonly=True)
    ai_candidate_allowed = fields.Boolean(default=True)
    ai_direct_effect_allowed = fields.Boolean(default=False, readonly=True)
    node_compute_capability_id = fields.Char(
        default=NODE_COMPUTE_CAPABILITY_ID,
        readonly=True,
    )
    compute_dispatch_mode = fields.Selection(
        [("8d_candidate_only", "8D ADI Candidate Only")],
        default="8d_candidate_only",
        readonly=True,
    )
    audit_hash = fields.Char(readonly=True, index=True)

    _sql_constraints = [
        ("seat_ref_unique", "unique(seat_ref)", "Capability seat ref must be unique."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.user.has_group(
            "wuchang_member_registration.group_wuchang_member_manager"
        ):
            raise UserError(_("HOLD_CAPABILITY_SEAT_MANAGER_REQUIRED"))
        for vals in vals_list:
            if vals.get("member_plaintext_allowed"):
                raise UserError(_("HOLD_MEMBER_PLAINTEXT_SEAT_FORBIDDEN"))
            seed = {
                "organization_ref": vals.get("organization_ref"),
                "role_ref": vals.get("role_ref"),
                "nonce": secrets.token_hex(16),
            }
            vals.setdefault("seat_ref", hash_ref("seat_ref", seed))
            vals["masked_data_only"] = True
            vals["member_plaintext_allowed"] = False
            vals["ai_direct_effect_allowed"] = False
            vals["node_compute_capability_id"] = NODE_COMPUTE_CAPABILITY_ID
            vals["compute_dispatch_mode"] = "8d_candidate_only"
        records = super().create(vals_list)
        records._refresh_audit_hash()
        return records

    def write(self, vals):
        if not self.env.user.has_group(
            "wuchang_member_registration.group_wuchang_member_manager"
        ):
            raise UserError(_("HOLD_CAPABILITY_SEAT_MANAGER_REQUIRED"))
        if vals.get("member_plaintext_allowed") or vals.get("ai_direct_effect_allowed"):
            raise UserError(_("HOLD_CAPABILITY_SEAT_AUTHORITY_ESCALATION"))
        vals.pop("node_compute_capability_id", None)
        vals.pop("compute_dispatch_mode", None)
        result = super().write(vals)
        self._refresh_audit_hash()
        return result

    def _refresh_audit_hash(self):
        for rec in self:
            payload = {
                "seat_ref": rec.seat_ref,
                "organization_ref": rec.organization_ref,
                "role_ref": rec.role_ref,
                "capabilities": sorted(_safe_json_list(rec.capability_refs_json)),
                "state": rec.state,
                "masked_data_only": rec.masked_data_only,
                "member_plaintext_allowed": rec.member_plaintext_allowed,
                "ai_candidate_allowed": rec.ai_candidate_allowed,
                "ai_direct_effect_allowed": rec.ai_direct_effect_allowed,
                "node_compute_capability_id": rec.node_compute_capability_id,
                "compute_dispatch_mode": rec.compute_dispatch_mode,
            }
            models.Model.write(rec, {"audit_hash": canonical_sha256(payload)})

    def has_capability(self, capability_ref):
        self.ensure_one()
        return bool(
            self.state == "active"
            and self.masked_data_only
            and capability_ref in set(_safe_json_list(self.capability_refs_json))
        )

    def build_ai_projection(self):
        self.ensure_one()
        return {
            "seat_ref": self.seat_ref,
            "organization_ref": self.organization_ref,
            "role_ref": self.role_ref,
            "capability_refs": sorted(_safe_json_list(self.capability_refs_json)),
            "state": self.state,
            "member_data_visibility": "MASKED_ONLY",
            "member_plaintext_allowed": False,
            "ai_candidate_allowed": self.ai_candidate_allowed,
            "ai_direct_effect_allowed": False,
            "node_compute_capability_id": self.node_compute_capability_id,
            "compute_dispatch_mode": "8D_ADI_CANDIDATE_ONLY",
            "compute_provider_authority": False,
            "audit_hash": self.audit_hash,
        }
