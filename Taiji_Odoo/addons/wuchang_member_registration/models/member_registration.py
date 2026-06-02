import hashlib
import secrets
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
    member_nickname = fields.Char(
        string="會員暱稱",
        help="會員可自行修改的顯示暱稱；不得作為正式身份核驗資料。"
    )
    role_scope = fields.Char(default="member")
    service_scope = fields.Char(default="basic_member_service")

    identity_code_id = fields.Many2one("wuchang.member.identity.code", readonly=True)
    consent_ledger_ids = fields.One2many("wuchang.member.consent.ledger", "registration_id")
    external_auth_ids = fields.One2many("wuchang.member.external.auth", "registration_id")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault("provisional_member_id", self._new_provisional_id())
            vals.setdefault("name", vals["provisional_member_id"])
        return super().create(vals_list)

    @api.model
    def _new_provisional_id(self):
        return "PROV-" + secrets.token_hex(8).upper()

    def action_submit_review(self):
        for rec in self:
            if rec.review_status not in ("draft", "dead_letter"):
                continue
            if not rec.consent_version:
                raise UserError(_("Consent version is required."))
            rec.write({
                "review_status": "pending_review",
                "consent_timestamp": fields.Datetime.now(),
            })

    def action_approve(self):
        for rec in self:
            if rec.review_status != "pending_review":
                raise UserError(_("Only pending registrations can be approved."))
            identity = self.env["wuchang.member.identity.code"].create_from_registration(rec)
            rec.write({
                "review_status": "approved",
                "reviewer_id": self.env.user.id,
                "identity_code_id": identity.id,
            })
            self.env["wuchang.member.consent.ledger"].create({
                "registration_id": rec.id,
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
    member_nickname = fields.Char(
        string="會員暱稱",
        help="會員可自行修改的顯示暱稱；不等於法定姓名或身份核驗資料。"
    )
    nickname_updated_at = fields.Datetime(readonly=True)
    role_scope = fields.Char(default="member")
    service_scope = fields.Char(default="basic_member_service")
    active_status = fields.Selection([
        ("active", "Active"),
        ("suspended", "Suspended"),
        ("recovery_pending", "Recovery Pending"),
        ("closed", "Closed"),
    ], default="active", index=True)
    registration_id = fields.Many2one("wuchang.member.registration", readonly=True)

    @api.model
    def create_from_registration(self, registration):
        seed = f"{registration.provisional_member_id}:{registration.create_date}:{secrets.token_hex(8)}"
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()

    def action_update_nickname(self):
        for rec in self:
            rec.nickname_updated_at = fields.Datetime.now()

        return self.create({
            "member_id": "M-" + digest[:12].upper(),
            "identity_code_7d": "7D-" + digest[12:28].upper(),
            "service_code_masked": "SVC-" + digest[28:44].upper(),
            "role_scope": registration.role_scope or "member",
            "service_scope": registration.service_scope or "basic_member_service",
            "member_nickname": registration.member_nickname,
            "registration_id": registration.id,
        })


class WuchangMemberExternalAuth(models.Model):
    _name = "wuchang.member.external.auth"
    _description = "Wuchang Member External Auth Binding"
    _order = "create_date desc"

    registration_id = fields.Many2one("wuchang.member.registration", ondelete="cascade")
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

    registration_id = fields.Many2one("wuchang.member.registration", ondelete="cascade")
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
