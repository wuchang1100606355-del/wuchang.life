import hashlib
import json
import secrets
import time
from pathlib import Path
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WuchangMemberRegistration(models.Model):
    _name = "wuchang.member.registration"
    _description = "Wuchang Member Registration"
    _order = "create_date desc"

    name = fields.Char(default="New", readonly=True)
    provisional_member_id = fields.Char(readonly=True, index=True)
    registration_channel = fields.Selection([
        ("line", "LINE"),
        ("google", "Google"),
        ("odoo", "Odoo"),
        ("pwa", "PWA"),
        ("staff_terminal", "Staff Assisted"),
    ], required=True, default="odoo")
    review_status = fields.Selection([
        ("draft", "Draft"),
        ("pending_review", "Pending Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("dead_letter", "Dead Letter"),
    ], default="draft", index=True)
    consent_version = fields.Char(required=True, default="v1")
    consent_timestamp = fields.Datetime()
    reviewer_id = fields.Many2one("res.users", readonly=True)
    dead_letter_reason = fields.Text(readonly=True)

    # Minimal review fields. These should not be used as daily runtime identity.
    review_name_hint = fields.Char("Review Name Hint")
    review_contact_hint = fields.Char("Review Contact Hint")
    membership_category = fields.Char()
    role_scope = fields.Char(default="member")
    service_scope = fields.Char(default="basic_member_service")

    member_type = fields.Selection([
        ("individual", "Individual Member"),
        ("organization", "Organization Member"),
    ], default="individual", required=True, index=True)

    organization_name = fields.Char("Organization / Affiliation")
    organization_role = fields.Selection([
        ("none", "None"),
        ("responsible_person", "Responsible Person"),
        ("representative", "Representative"),
        ("position_responsible", "Position Responsible"),
        ("staff", "Staff"),
        ("volunteer", "Volunteer"),
        ("resident", "Resident"),
        ("other", "Other"),
    ], default="none", index=True)

    review_level = fields.Selection([
        ("manager_allowed", "Manager Allowed"),
        ("owner_required", "Owner Required"),
        ("org_responsible_required", "Organization Responsible Required"),
    ], default="manager_allowed", readonly=True, index=True)

    reviewed_at = fields.Datetime(readonly=True)
    review_reason = fields.Text("Review Reason")

    identity_code_id = fields.Many2one("wuchang.member.identity.code", readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault("provisional_member_id", self._new_provisional_id())
            vals.setdefault("name", vals["provisional_member_id"])
        return super().create(vals_list)

    @api.model
    def _new_provisional_id(self):
        return "PROV-" + secrets.token_hex(8).upper()

    def _compute_review_level_value(self):
        self.ensure_one()
        owner_roles = {"responsible_person", "representative", "position_responsible"}
        if self.member_type == "organization" or self.organization_role in owner_roles or self.role_scope in owner_roles:
            return "owner_required"
        if self.organization_name:
            return "org_responsible_required"
        return "manager_allowed"

    def _is_owner_reviewer(self):
        return self.env.user.has_group("wuchang_member_registration.group_wuchang_member_admin")

    def _check_approval_governance(self):
        self.ensure_one()
        if self.create_uid and self.create_uid == self.env.user:
            raise UserError(_("Reviewer cannot approve their own registration."))

        level = self.review_level or self._compute_review_level_value()

        if level == "owner_required" and not self._is_owner_reviewer():
            raise UserError(_("Organization members and responsible persons require owner/admin review."))

        if level == "org_responsible_required" and not self._is_owner_reviewer():
            raise UserError(_("Organization-affiliated members require approved organization responsible-person review. Responsible-person binding is not enabled yet."))

    def action_submit_review(self):
        for rec in self:
            if rec.review_status not in ("draft", "dead_letter"):
                continue
            if not rec.consent_version:
                raise UserError(_("Consent version is required."))
            rec.write({
                "review_status": "pending_review",
                "review_level": rec._compute_review_level_value(),
                "consent_timestamp": fields.Datetime.now(),
            })

    def action_approve(self):
        for rec in self:
            if rec.review_status != "pending_review":
                raise UserError(_("Only pending registrations can be approved."))
            rec._check_approval_governance()
            identity = self.env["wuchang.member.identity.code"].create_from_registration(rec)
            rec.write({
                "review_status": "approved",
                "reviewer_id": self.env.user.id,
                "reviewed_at": fields.Datetime.now(),
                "identity_code_id": identity.id,
            })
            self.env["wuchang.member.consent.ledger"].create({
                "registration_ref_id": rec.id,
                "provisional_member_ref": rec.provisional_member_id,
                "member_identity_id": identity.id,
                "consent_type": "registration",
                "purpose": "membership_service",
                "consent_version": rec.consent_version,
                "audit_hash": self.env["wuchang.member.consent.ledger"].make_audit_hash(
                    rec.provisional_member_id,
                    rec.consent_version,
                    "membership_service",
                ),
            })

    def action_reject(self):
        for rec in self:
            rec.write({
                "review_status": "rejected",
                "reviewer_id": self.env.user.id,
            })

    def action_dead_letter(self):
        for rec in self:
            rec.write({
                "review_status": "dead_letter",
                "reviewer_id": self.env.user.id,
                "dead_letter_reason": rec.dead_letter_reason or "Manual dead-letter review required.",
            })


class WuchangMemberIdentityCode(models.Model):
    _name = "wuchang.member.identity.code"
    _description = "Wuchang Member 7D Identity Code"
    _order = "create_date desc"

    member_id = fields.Char(readonly=True, index=True)
    identity_code_7d = fields.Char(readonly=True, index=True)
    service_code_masked = fields.Char(readonly=True, index=True)
    role_scope = fields.Char(default="member")
    service_scope = fields.Char(default="basic_member_service")
    active_status = fields.Selection([
        ("active", "Active"),
        ("suspended", "Suspended"),
        ("recovery_pending", "Recovery Pending"),
        ("closed", "Closed"),
    ], default="active", index=True)
    registration_ref_id = fields.Integer(readonly=True, index=True)
    provisional_member_ref = fields.Char(readonly=True, index=True)

    @api.model
    def create_from_registration(self, registration):
        seed = f"{registration.provisional_member_id}:{registration.create_date}:{secrets.token_hex(8)}"
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        return self.create({
            "member_id": "M-" + digest[:12].upper(),
            "identity_code_7d": "7D-" + digest[12:28].upper(),
            "service_code_masked": "SVC-" + digest[28:44].upper(),
            "role_scope": registration.role_scope or "member",
            "service_scope": registration.service_scope or "basic_member_service",
            "registration_ref_id": registration.id,
            "provisional_member_ref": registration.provisional_member_id,
        })


class WuchangMemberExternalAuth(models.Model):
    _name = "wuchang.member.external.auth"
    _description = "Wuchang Member External Auth Binding"
    _order = "create_date desc"

    registration_ref_id = fields.Integer(index=True)
    provisional_member_ref = fields.Char(index=True)
    member_identity_id = fields.Many2one("wuchang.member.identity.code", ondelete="cascade")
    provider = fields.Selection([
        ("line", "LINE"),
        ("google", "Google"),
        ("odoo", "Odoo"),
    ], required=True, index=True)
    provider_subject_hash = fields.Char(required=True, index=True)
    binding_status = fields.Selection([
        ("pending", "Pending"),
        ("bound", "Bound"),
        ("revoked", "Revoked"),
    ], default="pending", index=True)
    consent_ref = fields.Char()
    last_login_at = fields.Datetime()

    _sql_constraints = [
        (
            "provider_subject_hash_unique",
            "unique(provider, provider_subject_hash)",
            "This external auth subject is already bound.",
        ),
    ]

    @api.model
    def hash_subject(self, provider, subject):
        if not provider or not subject:
            raise UserError(_("Provider and subject are required."))
        return hashlib.sha256(f"{provider}:{subject}".encode("utf-8")).hexdigest()


class WuchangMemberConsentLedger(models.Model):
    _name = "wuchang.member.consent.ledger"
    _description = "Wuchang Member Consent Ledger"
    _order = "create_date desc"

    registration_ref_id = fields.Integer(index=True)
    provisional_member_ref = fields.Char(index=True)
    member_identity_id = fields.Many2one("wuchang.member.identity.code", ondelete="cascade")
    consent_type = fields.Char(required=True)
    purpose = fields.Char(required=True)
    consent_version = fields.Char(required=True, default="v1")
    allowed_until = fields.Datetime()
    revoked_at = fields.Datetime()
    audit_hash = fields.Char(required=True, readonly=True, index=True)

    @api.model
    def make_audit_hash(self, member_ref, consent_version, purpose):
        seed = f"{member_ref}:{consent_version}:{purpose}:{fields.Datetime.now()}"
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()

    def action_revoke(self):
        for rec in self:
            rec.revoked_at = fields.Datetime.now()


class WuchangMemberPreferenceVault(models.Model):
    _name = "wuchang.member.preference.vault"
    _description = "Wuchang Sovereign Member Preference Vault"
    _order = "write_date desc, id desc"

    name = fields.Char(default="Sovereign Preference", readonly=True)
    preference_ref = fields.Char(readonly=True, index=True, copy=False)
    member_identity_id = fields.Many2one(
        "wuchang.member.identity.code",
        required=True,
        ondelete="cascade",
        index=True,
    )
    active = fields.Boolean(default=True)

    ai_memory_enabled = fields.Boolean(default=False)
    pos_personalization_enabled = fields.Boolean(default=False)
    recommendation_enabled = fields.Boolean(default=False)
    cloud_context_allowed = fields.Boolean(default=False)

    usual_product_id = fields.Many2one("product.template", string="Usual Product")
    preferred_pos_category_id = fields.Many2one("pos.category", string="Preferred POS Category")
    preferred_size = fields.Selection([
        ("small", "Small"),
        ("medium", "Medium"),
        ("large", "Large"),
    ])
    preferred_temperature = fields.Selection([
        ("ice", "Ice"),
        ("less_ice", "Less Ice"),
        ("no_ice", "No Ice"),
        ("warm", "Warm"),
        ("hot", "Hot"),
    ])
    preferred_sweetness = fields.Selection([
        ("regular_sugar", "Regular Sugar"),
        ("less_sugar", "Less Sugar"),
        ("half_sugar", "Half Sugar"),
        ("light_sugar", "Light Sugar"),
        ("no_sugar", "No Sugar"),
    ])
    caffeine_policy = fields.Selection([
        ("unknown", "Unknown"),
        ("ok", "Caffeine OK"),
        ("prefer_low", "Prefer Low Caffeine"),
        ("avoid", "Avoid Caffeine"),
    ], default="unknown")
    language_preference = fields.Selection([
        ("zh-Hant", "Traditional Chinese"),
        ("vi", "Vietnamese"),
        ("en", "English"),
    ], default="zh-Hant")

    local_summary = fields.Text(
        help="Local operator note. Never send this field to cloud candidate APIs."
    )
    preference_hash = fields.Char(readonly=True, index=True)
    consent_version = fields.Char(default="sovereign_member_preference_v1")
    last_candidate_at = fields.Datetime(readonly=True)

    _sql_constraints = [
        (
            "member_identity_unique",
            "unique(member_identity_id)",
            "Each member identity can have one active sovereign preference vault.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault("preference_ref", self._new_preference_ref())
        records = super().create(vals_list)
        records._refresh_preference_hash()
        return records

    def write(self, vals):
        result = super().write(vals)
        if vals.keys() & {
            "ai_memory_enabled",
            "pos_personalization_enabled",
            "recommendation_enabled",
            "cloud_context_allowed",
            "usual_product_id",
            "preferred_pos_category_id",
            "preferred_size",
            "preferred_temperature",
            "preferred_sweetness",
            "caffeine_policy",
            "language_preference",
        }:
            self._refresh_preference_hash()
        return result

    @api.model
    def _new_preference_ref(self):
        return "PREF-" + secrets.token_hex(10).upper()

    def _refresh_preference_hash(self):
        for rec in self:
            payload = {
                "preference_ref": rec.preference_ref,
                "member_ref": rec.member_identity_id.member_id,
                "ai_memory_enabled": rec.ai_memory_enabled,
                "pos_personalization_enabled": rec.pos_personalization_enabled,
                "recommendation_enabled": rec.recommendation_enabled,
                "usual_product_id": rec.usual_product_id.id or 0,
                "preferred_pos_category_id": rec.preferred_pos_category_id.id or 0,
                "preferred_size": rec.preferred_size or "",
                "preferred_temperature": rec.preferred_temperature or "",
                "preferred_sweetness": rec.preferred_sweetness or "",
                "caffeine_policy": rec.caffeine_policy or "",
                "language_preference": rec.language_preference or "",
            }
            rec.preference_hash = hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            ).hexdigest()

    @api.model
    def find_by_member_ref(self, member_ref):
        member_ref = (member_ref or "").strip()
        if not member_ref:
            return self.browse()
        identity = self.env["wuchang.member.identity.code"].sudo().search([
            "|", "|",
            ("member_id", "=", member_ref),
            ("identity_code_7d", "=", member_ref),
            ("service_code_masked", "=", member_ref),
        ], limit=1)
        if not identity:
            return self.browse()
        return self.sudo().search([("member_identity_id", "=", identity.id)], limit=1)

    def build_pos_candidate_context(self, utterance_text=""):
        self.ensure_one()
        self.last_candidate_at = fields.Datetime.now()
        allowed = bool(self.ai_memory_enabled and self.pos_personalization_enabled)
        slots = {}
        if allowed:
            for field_name, key in [
                ("preferred_size", "size"),
                ("preferred_temperature", "temperature"),
                ("preferred_sweetness", "sweetness"),
            ]:
                value = getattr(self, field_name)
                if value:
                    slots[key] = value
        usual_product = {}
        if allowed and self.usual_product_id:
            usual_product = {
                "product_ref": self.usual_product_id.default_code or f"product.template:{self.usual_product_id.id}",
                "display_name": self.usual_product_id.name,
                "pos_category": self.preferred_pos_category_id.name if self.preferred_pos_category_id else "",
            }
        return {
            "schema": "WUCHANG_SOVEREIGN_MEMBER_POS_CONTEXT_V1",
            "state": "PASS_LOCAL_MEMBER_AUTHORITY" if allowed else "HOLD_MEMBER_AI_MEMORY_DISABLED",
            "candidate_only": True,
            "member_plaintext": False,
            "cloud_context_allowed": bool(allowed and self.cloud_context_allowed),
            "preference_ref": self.preference_ref,
            "preference_hash": self.preference_hash,
            "member_ref": self.member_identity_id.service_code_masked,
            "utterance_hash": hashlib.sha256((utterance_text or "").encode("utf-8")).hexdigest() if utterance_text else "",
            "suggested_slots": slots,
            "usual_product_candidate": usual_product,
            "caffeine_policy": self.caffeine_policy if allowed else "withheld",
            "language_preference": self.language_preference if allowed else "withheld",
            "requires_staff_confirmation": True,
            "write_to_pos": False,
            "payment_capture": False,
        }


class WuchangMemberVoucherProgram(models.Model):
    _name = "wuchang.member.voucher.program"
    _description = "Wuchang Sovereign Member Buy-Gift Voucher Program"
    _order = "active desc, sequence, id desc"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    program_ref = fields.Char(readonly=True, index=True, copy=False)
    buy_quantity = fields.Integer(default=10, required=True)
    gift_quantity = fields.Integer(default=1, required=True)
    applies_pos_category_id = fields.Many2one("pos.category", string="Applies POS Category")
    applies_product_id = fields.Many2one("product.template", string="Applies Product")
    reward_product_id = fields.Many2one("product.template", string="Reward Product")
    validity_days = fields.Integer(default=90)
    local_policy_note = fields.Text()
    audit_hash = fields.Char(readonly=True, index=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault("program_ref", "VPG-" + secrets.token_hex(8).upper())
        records = super().create(vals_list)
        records._refresh_audit_hash()
        return records

    def write(self, vals):
        result = super().write(vals)
        if vals.keys() & {
            "active",
            "buy_quantity",
            "gift_quantity",
            "applies_pos_category_id",
            "applies_product_id",
            "reward_product_id",
            "validity_days",
        }:
            self._refresh_audit_hash()
        return result

    def _refresh_audit_hash(self):
        for rec in self:
            payload = {
                "program_ref": rec.program_ref,
                "active": rec.active,
                "buy_quantity": rec.buy_quantity,
                "gift_quantity": rec.gift_quantity,
                "applies_pos_category_id": rec.applies_pos_category_id.id or 0,
                "applies_product_id": rec.applies_product_id.id or 0,
                "reward_product_id": rec.reward_product_id.id or 0,
                "validity_days": rec.validity_days,
            }
            rec.audit_hash = hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            ).hexdigest()


class WuchangMemberVoucher(models.Model):
    _name = "wuchang.member.voucher"
    _description = "Wuchang Sovereign Member Voucher"
    _order = "create_date desc"

    name = fields.Char(default="Voucher", readonly=True)
    voucher_ref = fields.Char(readonly=True, index=True, copy=False)
    voucher_hash = fields.Char(readonly=True, index=True)
    program_id = fields.Many2one("wuchang.member.voucher.program", required=True, ondelete="restrict")
    member_identity_id = fields.Many2one("wuchang.member.identity.code", required=True, ondelete="cascade", index=True)
    state = fields.Selection([
        ("issued", "Issued"),
        ("reserved", "Reserved"),
        ("redeemed", "Redeemed"),
        ("expired", "Expired"),
        ("void", "Void"),
    ], default="issued", index=True)
    source_order_ref = fields.Char(index=True)
    source_evidence_ref = fields.Char()
    reward_product_id = fields.Many2one("product.template", string="Reward Product")
    issued_at = fields.Datetime(default=fields.Datetime.now)
    expires_at = fields.Datetime(index=True)
    reserved_at = fields.Datetime()
    redeemed_at = fields.Datetime()
    redeemed_order_ref = fields.Char(index=True)
    redeemed_by_id = fields.Many2one("res.users", readonly=True)
    audit_hash = fields.Char(readonly=True, index=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault("voucher_ref", "VCH-" + secrets.token_hex(10).upper())
            program = self.env["wuchang.member.voucher.program"].browse(vals.get("program_id"))
            if program and program.exists() and not vals.get("expires_at") and program.validity_days:
                vals["expires_at"] = fields.Datetime.add(fields.Datetime.now(), days=program.validity_days)
            if program and program.exists() and not vals.get("reward_product_id") and program.reward_product_id:
                vals["reward_product_id"] = program.reward_product_id.id
        records = super().create(vals_list)
        records._refresh_voucher_hash()
        return records

    def write(self, vals):
        result = super().write(vals)
        if vals.keys() & {"state", "expires_at", "redeemed_order_ref", "reward_product_id"}:
            self._refresh_voucher_hash()
        return result

    def _refresh_voucher_hash(self):
        for rec in self:
            payload = {
                "voucher_ref": rec.voucher_ref,
                "program_ref": rec.program_id.program_ref,
                "member_ref": rec.member_identity_id.service_code_masked,
                "state": rec.state,
                "reward_product_id": rec.reward_product_id.id or 0,
                "expires_at": fields.Datetime.to_string(rec.expires_at) if rec.expires_at else "",
            }
            digest = hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            ).hexdigest()
            rec.voucher_hash = digest
            rec.audit_hash = digest

    @api.model
    def issue_from_authority(self, member_identity, program, source_order_ref="", source_evidence_ref=""):
        if not program.active:
            raise UserError(_("Voucher program is not active."))
        return self.sudo().create({
            "program_id": program.id,
            "member_identity_id": member_identity.id,
            "source_order_ref": source_order_ref,
            "source_evidence_ref": source_evidence_ref,
            "reward_product_id": program.reward_product_id.id if program.reward_product_id else False,
        })

    @api.model
    def find_by_ref(self, voucher_ref):
        return self.sudo().search([("voucher_ref", "=", (voucher_ref or "").strip())], limit=1)

    def build_redeem_candidate(self, order_ref=""):
        self.ensure_one()
        now = fields.Datetime.now()
        allowed = self.state in ("issued", "reserved") and (not self.expires_at or self.expires_at >= now)
        reason = "PASS_LOCAL_VOUCHER_AUTHORITY" if allowed else "HOLD_VOUCHER_NOT_REDEEMABLE"
        if self.expires_at and self.expires_at < now:
            reason = "HOLD_VOUCHER_EXPIRED"
        if self.state == "redeemed":
            reason = "HOLD_VOUCHER_ALREADY_REDEEMED"
        if self.state in ("void", "expired"):
            reason = "HOLD_VOUCHER_CLOSED"
        return {
            "schema": "WUCHANG_SOVEREIGN_MEMBER_VOUCHER_REDEEM_CANDIDATE_V1",
            "state": reason,
            "candidate_only": True,
            "voucher_ref": self.voucher_ref,
            "voucher_hash": self.voucher_hash,
            "program_ref": self.program_id.program_ref,
            "member_ref": self.member_identity_id.service_code_masked,
            "reward_product_ref": (
                self.reward_product_id.default_code
                or (f"product.template:{self.reward_product_id.id}" if self.reward_product_id else "")
            ),
            "reward_display_name": self.reward_product_id.name if self.reward_product_id else "",
            "order_ref": order_ref or "",
            "requires_staff_confirmation": True,
            "write_to_pos": False,
            "payment_capture": False,
            "member_plaintext": False,
        }

    def action_redeem_with_authority(self, order_ref):
        for rec in self:
            candidate = rec.build_redeem_candidate(order_ref)
            if not candidate["state"].startswith("PASS_"):
                raise UserError(_(candidate["state"]))
            rec.write({
                "state": "redeemed",
                "redeemed_at": fields.Datetime.now(),
                "redeemed_order_ref": order_ref,
                "redeemed_by_id": self.env.user.id,
            })


class WuchangCommunityFeatureGate(models.Model):
    _name = "wuchang.community.feature.gate"
    _description = "Wuchang Community Central Feature Gate"
    _order = "feature_key"

    name = fields.Char(required=True)
    feature_key = fields.Char(required=True, index=True)
    enabled = fields.Boolean(default=False)
    gate_state = fields.Selection([
        ("enabled", "Enabled"),
        ("disabled", "Disabled"),
        ("hold_review", "Hold Review"),
    ], default="disabled", index=True)
    decision_scope = fields.Selection([
        ("community_central", "Community Central Control"),
        ("shop_manager", "Shop Manager"),
        ("owner_admin", "Owner Admin"),
    ], default="community_central")
    decided_by_id = fields.Many2one("res.users", readonly=True)
    decided_at = fields.Datetime(readonly=True)
    reason_ref = fields.Char()
    audit_hash = fields.Char(readonly=True, index=True)

    _sql_constraints = [
        ("feature_key_unique", "unique(feature_key)", "Feature key must be unique."),
    ]

    @api.model
    def is_enabled(self, feature_key, default=False):
        gate = self.sudo().search([("feature_key", "=", feature_key)], limit=1)
        if not gate:
            return bool(default)
        return bool(gate.enabled and gate.gate_state == "enabled")

    @api.model
    def set_gate(self, feature_key, enabled, reason_ref="", name=None):
        if not feature_key:
            raise UserError(_("Feature key is required."))
        gate = self.sudo().search([("feature_key", "=", feature_key)], limit=1)
        vals = {
            "name": name or feature_key,
            "feature_key": feature_key,
            "enabled": bool(enabled),
            "gate_state": "enabled" if enabled else "disabled",
            "reason_ref": reason_ref or "",
            "decided_by_id": self.env.user.id,
            "decided_at": fields.Datetime.now(),
        }
        if gate:
            gate.write(vals)
        else:
            gate = self.sudo().create(vals)
        gate._refresh_audit_hash()
        return gate

    def _refresh_audit_hash(self):
        for rec in self:
            payload = {
                "feature_key": rec.feature_key,
                "enabled": rec.enabled,
                "gate_state": rec.gate_state,
                "decision_scope": rec.decision_scope,
                "reason_ref": rec.reason_ref or "",
                "decided_at": fields.Datetime.to_string(rec.decided_at) if rec.decided_at else "",
            }
            rec.audit_hash = hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            ).hexdigest()

    def build_status(self):
        self.ensure_one()
        return {
            "schema": "WUCHANG_COMMUNITY_FEATURE_GATE_V1",
            "feature_key": self.feature_key,
            "enabled": bool(self.enabled and self.gate_state == "enabled"),
            "gate_state": self.gate_state,
            "decision_scope": self.decision_scope,
            "reason_ref": self.reason_ref or "",
            "audit_hash": self.audit_hash,
            "member_plaintext": False,
            "secret_read": False,
        }


class WuchangMemberRecoveryCase(models.Model):
    _name = "wuchang.member.recovery.case"
    _description = "Wuchang Member Recovery Case"
    _order = "create_date desc"

    name = fields.Char(default="New", readonly=True)
    member_identity_id = fields.Many2one("wuchang.member.identity.code", required=True)
    applicant_type = fields.Selection([
        ("self", "Self"),
        ("delegated_family", "Delegated Family"),
        ("staff_initiated", "Staff Initiated"),
    ], required=True)
    review_status = fields.Selection([
        ("draft", "Draft"),
        ("pending_review", "Pending Review"),
        ("key_custody_required", "Key Custody Required"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("sealed_again", "Sealed Again"),
    ], default="draft", index=True)
    key_custody_required = fields.Boolean(default=True)
    approval_count = fields.Integer(default=0)
    audit_hash = fields.Char(readonly=True, index=True)
    sealed_again_at = fields.Datetime()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault("name", "REC-" + secrets.token_hex(6).upper())
            seed = f"{vals.get('member_identity_id')}:{vals.get('applicant_type')}:{secrets.token_hex(8)}"
            vals.setdefault("audit_hash", hashlib.sha256(seed.encode("utf-8")).hexdigest())
        return super().create(vals_list)

    def action_mark_key_custody_required(self):
        for rec in self:
            rec.write({
                "review_status": "key_custody_required",
                "key_custody_required": True,
            })

    def action_seal_again(self):
        for rec in self:
            rec.write({
                "review_status": "sealed_again",
                "sealed_again_at": fields.Datetime.now(),
            })


class WuchangMemberGroupRegistrationBatch(models.Model):
    _name = "wuchang.member.group.registration.batch"
    _description = "W7TP Group Member 8D Registration Batch"
    _order = "create_date desc"

    name = fields.Char(string="Group Name", required=True)
    packet_ref = fields.Char(readonly=True, index=True, copy=False)
    group_ref = fields.Char(readonly=True, index=True, copy=False)
    issuer_user_id = fields.Many2one("res.users", default=lambda self: self.env.user, readonly=True)
    topology_ref = fields.Char(default="association/branch/shop/group")
    registration_scope = fields.Char(default="group_member_registration")
    expires_at = fields.Datetime(required=True)
    state = fields.Selection([
        ("provisional", "Provisional"),
        ("pending_review", "Pending Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("expired", "Expired"),
    ], default="provisional", index=True)
    packet_hash = fields.Char(readonly=True, index=True, copy=False)
    d8_ref = fields.Char(readonly=True, index=True, copy=False)
    qr_payload = fields.Text(readonly=True)
    evidence_ref = fields.Char(readonly=True)
    packet_ids = fields.One2many("wuchang.member.group.registration.packet", "batch_id")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._ensure_group_8d_code()
        return records

    @api.model
    def _new_ref(self, prefix):
        return f"{prefix}-{secrets.token_hex(10).upper()}"

    @api.model
    def _packet_hash(self, payload):
        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _short_qr_payload(self, packet_ref, group_ref, expires_at, d8_ref):
        return {
            "type": "W7TP_GROUP_MEMBER_REG",
            "version": "1",
            "packet_ref": packet_ref,
            "group_ref": group_ref,
            "nonce": secrets.token_urlsafe(16),
            "expires_at": fields.Datetime.to_string(expires_at),
            "d8_ref": d8_ref,
            "verify_url": f"/wuchang/member/register/group/{packet_ref}",
        }

    def _ensure_group_8d_code(self):
        for rec in self:
            packet_ref = rec.packet_ref or self._new_ref("G8D")
            group_ref = rec.group_ref or self._new_ref("GROUP")
            d8_seed = f"{packet_ref}:{group_ref}:{fields.Datetime.now()}:{secrets.token_hex(8)}"
            d8_ref = rec.d8_ref or "D8-" + hashlib.sha256(d8_seed.encode("utf-8")).hexdigest()[:20].upper()
            payload = rec._short_qr_payload(packet_ref, group_ref, rec.expires_at, d8_ref)
            packet_hash = rec._packet_hash(payload)
            rec.write({
                "packet_ref": packet_ref,
                "group_ref": group_ref,
                "d8_ref": d8_ref,
                "packet_hash": packet_hash,
                "qr_payload": json.dumps(payload, ensure_ascii=False, sort_keys=True),
                "evidence_ref": rec._write_group_8d_evidence(payload, packet_hash, d8_ref),
            })

    def _write_group_8d_evidence(self, payload, packet_hash, d8_ref):
        root = Path(
            self.env["ir.config_parameter"].sudo().get_param(
                "wuchang_member_registration.total_field_evidence_root",
                "runtime/total_field/evidence",
            )
        )
        run_id = f"TOTAL_FIELD_GROUP_MEMBER_8D_REGISTRATION_{int(time.time())}"
        out_dir = root / run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        seal = {
            "schema": "W7TP_GROUP_MEMBER_8D_CODE_SEAL_V1",
            "state": "GROUP_MEMBER_8D_CODE_SEALED",
            "run_id": run_id,
            "group_ref": payload["group_ref"],
            "packet_ref": payload["packet_ref"],
            "packet_hash": packet_hash,
            "d8_ref": d8_ref,
            "verify_url": payload["verify_url"],
            "safety": self._safety_flags(),
        }
        seal_path = out_dir / "GROUP_MEMBER_8D_CODE_SEAL.json"
        readme_path = out_dir / "README_GROUP_MEMBER_8D_REGISTRATION.md"
        seal_path.write_text(json.dumps(seal, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        readme_path.write_text(
            "# Group Member 8D Registration Evidence\n\n"
            "STATE=GROUP_MEMBER_8D_CODE_SEALED\n"
            f"RUN_ID={run_id}\n"
            "FORMAL_DB_WRITE=FALSE\n"
            "FORMAL_POS_WRITE=FALSE\n"
            "PAYMENT_CAPTURE=FALSE\n"
            "SERVICE_RESTART=FALSE\n"
            "DEPLOY=FALSE\n"
            "PRODUCTION_RELEASE=FALSE\n"
            "SECRET_READ=FALSE\n"
            "MEMBER_PLAINTEXT_READ=FALSE\n",
            encoding="utf-8",
        )
        manifest = []
        for path in [seal_path, readme_path]:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest.append(f"{digest}  {path.name}")
        (out_dir / "sha256_manifest.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")
        return str(seal_path)

    @api.model
    def _safety_flags(self):
        return {
            "formal_db_write": False,
            "formal_pos_write": False,
            "payment_capture": False,
            "service_restart": False,
            "deploy": False,
            "production_release": False,
            "secret_read": False,
            "member_plaintext_read": False,
        }


class WuchangMemberGroupRegistrationPacket(models.Model):
    _name = "wuchang.member.group.registration.packet"
    _description = "W7TP Group Member 8D Registration Packet"
    _order = "create_date desc"

    name = fields.Char(default="New", readonly=True)
    batch_id = fields.Many2one("wuchang.member.group.registration.batch", required=True, ondelete="cascade")
    packet_ref = fields.Char(readonly=True, index=True, copy=False)
    group_ref = fields.Char(readonly=True, index=True, copy=False)
    provider = fields.Selection([
        ("google", "Google"),
        ("line", "LINE"),
        ("manual", "Manual"),
    ], required=True, default="manual", index=True)
    provider_user_ref = fields.Char(readonly=True, index=True)
    registration_ref_id = fields.Integer(readonly=True, index=True)
    provisional_member_ref = fields.Char(readonly=True, index=True)
    state = fields.Selection([
        ("provisional", "Provisional"),
        ("pending_review", "Pending Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ], default="provisional", index=True)
    packet_json = fields.Text(readonly=True)
    packet_hash = fields.Char(readonly=True, index=True)
    d8_ref = fields.Char(readonly=True, index=True)
    evidence_ref = fields.Char(readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault("name", vals.get("packet_ref") or self.env["wuchang.member.group.registration.batch"]._new_ref("GM8D"))
        return super().create(vals_list)

    @api.model
    def hash_provider_ref(self, provider, provider_user_ref):
        if not provider_user_ref:
            provider_user_ref = secrets.token_urlsafe(24)
        return hashlib.sha256(f"{provider}:{provider_user_ref}".encode("utf-8")).hexdigest()

    @api.model
    def create_from_group_claim(self, batch, provider="manual", provider_user_ref=None, display_ref=None):
        if batch.state not in ("provisional", "pending_review"):
            raise UserError(_("This group registration batch is not open."))
        if batch.expires_at and fields.Datetime.now() > batch.expires_at:
            batch.state = "expired"
            raise UserError(_("This group registration batch has expired."))

        provider_hash = self.hash_provider_ref(provider, provider_user_ref)
        duplicate = self.search([
            ("batch_id", "=", batch.id),
            ("provider", "=", provider),
            ("provider_user_ref", "=", provider_hash),
        ], limit=1)
        if duplicate:
            return duplicate

        registration = self.env["wuchang.member.registration"].sudo().create({
            "registration_channel": provider if provider in ("google", "line") else "odoo",
            "review_status": "pending_review",
            "consent_version": "group_member_v1",
            "membership_category": "group_member",
            "role_scope": "group_member",
            "service_scope": batch.registration_scope or "group_member_registration",
        })
        packet_ref = self.env["wuchang.member.group.registration.batch"]._new_ref("GM8D")
        d8_seed = f"{packet_ref}:{batch.group_ref}:{provider_hash}:{secrets.token_hex(8)}"
        d8_ref = "D8-" + hashlib.sha256(d8_seed.encode("utf-8")).hexdigest()[:20].upper()
        envelope = self._build_8d_envelope(batch, registration, packet_ref, provider, provider_hash, display_ref, d8_ref)
        packet_hash = batch._packet_hash(envelope)
        envelope["D8_ENVELOPE"]["packet_hash"] = packet_hash
        envelope["D8_ENVELOPE"]["seal_ref"] = batch.evidence_ref or ""
        record = self.create({
            "batch_id": batch.id,
            "packet_ref": packet_ref,
            "group_ref": batch.group_ref,
            "provider": provider,
            "provider_user_ref": provider_hash,
            "registration_ref_id": registration.id,
            "provisional_member_ref": registration.provisional_member_id,
            "state": "pending_review",
            "packet_json": json.dumps(envelope, ensure_ascii=False, sort_keys=True),
            "packet_hash": packet_hash,
            "d8_ref": d8_ref,
            "evidence_ref": batch.evidence_ref,
        })
        self.env["wuchang.member.external.auth"].sudo().create({
            "registration_ref_id": registration.id,
            "provisional_member_ref": registration.provisional_member_id,
            "provider": provider if provider in ("google", "line") else "odoo",
            "provider_subject_hash": provider_hash,
            "binding_status": "pending",
            "consent_ref": record.packet_ref,
            "last_login_at": fields.Datetime.now(),
        })
        return record

    def _build_8d_envelope(self, batch, registration, packet_ref, provider, provider_hash, display_ref, d8_ref):
        return {
            "D1_IDENTITY": {
                "provider": provider,
                "provider_user_ref": provider_hash,
                "display_ref": display_ref or "masked",
                "member_ref": registration.provisional_member_id,
            },
            "D2_INTENT": "group_member_registration",
            "D3_STATE": "pending_review",
            "D4_TOPOLOGY": {
                "association": "wuchang",
                "branch": batch.topology_ref or "branch_ref",
                "shop": "shop_ref",
                "group": batch.group_ref,
                "source_channel": provider,
            },
            "D5_RESOURCE": {
                "registration_scope": batch.registration_scope,
                "available_permissions": ["view_only"],
                "default": "view_only",
            },
            "D6_GOVERNANCE": {
                "privacy_boundary": "no_member_plaintext_in_payload",
                "member_plaintext_policy": "hash_or_ref_only",
                "operator_gate": "human_confirm_required",
            },
            "D7_VERIFICATION": {
                "nonce": secrets.token_urlsafe(16),
                "expires_at": fields.Datetime.to_string(batch.expires_at),
                "signature_check": "hmac_ref_required",
                "duplicate_check": "provider_user_ref_batch_unique",
            },
            "D8_ENVELOPE": {
                "packet_hash": "",
                "hmac_ref": "ir.config_parameter:wuchang_member_registration.hmac_key_ref",
                "ttl": fields.Datetime.to_string(batch.expires_at),
                "seal_ref": "",
                "version": "1",
                "d8_ref": d8_ref,
            },
            "packet_ref": packet_ref,
        }

    def action_confirm_dry_run(self):
        return {
            "state": "CONFIRM_DRY_RUN",
            "packet_ref": self.packet_ref,
            "group_ref": self.group_ref,
            "formal_db_write": False,
            "formal_pos_write": False,
            "payment_capture": False,
            "service_restart": False,
            "deploy": False,
            "production_release": False,
        }
