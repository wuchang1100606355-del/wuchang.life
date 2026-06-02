import hashlib
import base64
import urllib.request
import secrets
from odoo import api, fields, models, _
from odoo.exceptions import UserError



def _fetch_image_b64_from_url(image_url, max_bytes=2_000_000):
    """Fetch LINE/Google profile image into Odoo Image base64 without storing raw URL."""
    if not image_url or not isinstance(image_url, str):
        return False, False
    if not image_url.startswith(("https://", "http://")):
        return False, False

    req = urllib.request.Request(
        image_url,
        headers={"User-Agent": "WuchangMemberRegistration/1.0"}
    )
    with urllib.request.urlopen(req, timeout=8) as res:
        content_type = (res.headers.get("Content-Type") or "").lower()
        if "image" not in content_type:
            return False, False
        raw = res.read(max_bytes + 1)
        if len(raw) > max_bytes:
            return False, False

    digest = hashlib.sha256(raw).hexdigest()
    return base64.b64encode(raw), digest


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
    member_avatar = fields.Image(
        string="會員縮圖",
        max_width=512,
        max_height=512,
        help="會員可手動貼圖/上傳；也可由 LINE 或 Google 頭像預設帶入同一欄位。"
    )
    member_avatar_source = fields.Selection([
        ("manual", "Manual Upload"),
        ("line", "LINE"),
        ("google", "Google"),
        ("odoo", "Odoo"),
    ], default="manual", string="縮圖來源")
    member_avatar_url_hash = fields.Char(readonly=True)
    member_avatar_updated_at = fields.Datetime(readonly=True)

    is_founder_claim = fields.Boolean(
        string="創辦人註冊請求",
        default=False,
        help="僅作為創辦人身份請求；不得由 OAuth 或一般註冊自動通過。"
    )
    founder_claim_status = fields.Selection([
        ("none", "None"),
        ("pending_review", "Pending Founder Review"),
        ("verified", "Founder Verified"),
        ("rejected", "Rejected"),
        ("dead_letter", "Dead Letter"),
    ], default="none", string="創辦人核驗狀態", index=True)
    founder_verification_note = fields.Text(string="創辦人核驗備註")
    founder_verified_at = fields.Datetime(readonly=True)

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

    def set_member_avatar_from_provider(self, provider, image_url):
        if provider not in ("line", "google", "odoo", "manual"):
            provider = "manual"
        image_b64, digest = _fetch_image_b64_from_url(image_url)
        if not image_b64:
            return False
        self.write({
            "member_avatar": image_b64,
            "member_avatar_source": provider,
            "member_avatar_url_hash": digest,
            "member_avatar_updated_at": fields.Datetime.now(),
        })
        return True

    def action_request_founder_review(self):
        for rec in self:
            rec.write({
                "is_founder_claim": True,
                "founder_claim_status": "pending_review",
                "review_status": "pending_review",
                "role_scope": "founder_candidate",
                "founder_verification_note": rec.founder_verification_note or "Founder review requested. OAuth/login alone is not sufficient.",
            })

    def action_approve_founder(self):
        if not self.env.user.has_group("base.group_system"):
            raise UserError(_("Only system administrators may approve founder registration."))
        for rec in self:
            existing = self.env["wuchang.member.identity.code"].search([
                ("founder_authority_status", "=", "founder_verified")
            ], limit=1)
            if existing:
                raise UserError(_("A verified founder identity already exists."))
            rec.write({
                "is_founder_claim": True,
                "founder_claim_status": "verified",
                "founder_verified_at": fields.Datetime.now(),
                "review_status": "pending_review",
                "role_scope": "founder",
            })

    def action_reject_founder(self):
        if not self.env.user.has_group("base.group_system"):
            raise UserError(_("Only system administrators may reject founder registration."))
        for rec in self:
            rec.write({
                "founder_claim_status": "rejected",
                "founder_verification_note": rec.founder_verification_note or "Founder claim rejected.",
            })

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
    member_avatar = fields.Image(
        string="會員縮圖",
        max_width=512,
        max_height=512,
        help="會員可手動貼圖/上傳；也可由 LINE 或 Google 頭像預設帶入同一欄位。"
    )
    member_avatar_source = fields.Selection([
        ("manual", "Manual Upload"),
        ("line", "LINE"),
        ("google", "Google"),
        ("odoo", "Odoo"),
    ], default="manual", string="縮圖來源")
    member_avatar_url_hash = fields.Char(readonly=True)
    member_avatar_updated_at = fields.Datetime(readonly=True)

    is_founder_claim = fields.Boolean(
        string="創辦人註冊請求",
        default=False,
        help="僅作為創辦人身份請求；不得由 OAuth 或一般註冊自動通過。"
    )
    founder_claim_status = fields.Selection([
        ("none", "None"),
        ("pending_review", "Pending Founder Review"),
        ("verified", "Founder Verified"),
        ("rejected", "Rejected"),
        ("dead_letter", "Dead Letter"),
    ], default="none", string="創辦人核驗狀態", index=True)
    founder_verification_note = fields.Text(string="創辦人核驗備註")
    founder_verified_at = fields.Datetime(readonly=True)

    role_scope = fields.Char(default="member")
    service_scope = fields.Char(default="basic_member_service")
    active_status = fields.Selection([
        ("active", "Active"),
        ("suspended", "Suspended"),
        ("recovery_pending", "Recovery Pending"),
        ("closed", "Closed"),
    ], default="active", index=True)
    registration_id = fields.Many2one("wuchang.member.registration", readonly=True)

    def set_identity_avatar_from_provider(self, provider, image_url):
        if provider not in ("line", "google", "odoo", "manual"):
            provider = "manual"
        image_b64, digest = _fetch_image_b64_from_url(image_url)
        if not image_b64:
            return False
        self.write({
            "member_avatar": image_b64,
            "member_avatar_source": provider,
            "member_avatar_url_hash": digest,
            "member_avatar_updated_at": fields.Datetime.now(),
        })
        return True

    @api.constrains("founder_authority_status")
    def _check_single_verified_founder(self):
        for rec in self:
            if rec.founder_authority_status == "founder_verified":
                existing = self.search([
                    ("founder_authority_status", "=", "founder_verified"),
                    ("id", "!=", rec.id),
                ], limit=1)
                if existing:
                    raise UserError(_("Only one verified founder identity is allowed."))

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
            "member_avatar": registration.member_avatar,
            "member_avatar_source": registration.member_avatar_source or "manual",
            "member_avatar_url_hash": registration.member_avatar_url_hash,
            "member_avatar_updated_at": registration.member_avatar_updated_at,
            "founder_authority_status": "founder_verified" if registration.founder_claim_status == "verified" else "none",
            "founder_authority_scope": "system_owner" if registration.founder_claim_status == "verified" else "none",
            "founder_verified_at": registration.founder_verified_at,
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
    provider_picture_url_hash = fields.Char(
        readonly=True,
        help="LINE/Google picture URL or fetched image hash; raw URL should not be exported."
    )
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
