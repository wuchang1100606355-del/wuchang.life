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

    identity_code_id = fields.Many2one("wuchang.member.identity.code", readonly=True)
    consent_ledger_ids = fields.One2many("wuchang.member.consent.ledger", "registration_id")
    external_auth_ids = fields.One2many("wuchang.member.external.auth", "registration_id")
    group_registration_packet_ids = fields.One2many(
        "wuchang.member.group.registration.packet",
        "provisional_member_id",
        string="Group Registration Packets",
    )

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
        return self.create({
            "member_id": "M-" + digest[:12].upper(),
            "identity_code_7d": "7D-" + digest[12:28].upper(),
            "service_code_masked": "SVC-" + digest[28:44].upper(),
            "role_scope": registration.role_scope or "member",
            "service_scope": registration.service_scope or "basic_member_service",
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
    provisional_member_id = fields.Many2one("wuchang.member.registration", readonly=True, ondelete="set null")
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
            "provisional_member_id": registration.id,
            "state": "pending_review",
            "packet_json": json.dumps(envelope, ensure_ascii=False, sort_keys=True),
            "packet_hash": packet_hash,
            "d8_ref": d8_ref,
            "evidence_ref": batch.evidence_ref,
        })
        self.env["wuchang.member.external.auth"].sudo().create({
            "registration_id": registration.id,
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
