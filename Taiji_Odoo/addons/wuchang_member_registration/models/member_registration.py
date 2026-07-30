import hashlib
import json
import re
import secrets
import time
from pathlib import Path
from odoo import api, fields, models, _
from odoo.exceptions import UserError


_IDENTITY_PREFIX_REF = re.compile(r"^identity_prefix_ref:sha256:[0-9a-f]{64}$")
INDIVIDUAL_JURISDICTION_CATEGORIES = frozenset({
    "in_community_jurisdiction",
    "outside_community_jurisdiction",
})
ORGANIZATION_REVIEW_ROLES = frozenset({
    "responsible_person",
    "representative",
    "position_responsible",
})
LANDING_CONTROL_SURFACES = frozenset({
    "external_api",
    "google_login",
    "line_login",
    "member_ai",
    "member_registration",
    "payment",
    "pos_order",
})
SOVEREIGN_AUTHORITY_MODEL = {
    "member_consent_authority": "member",
    "safety_and_landing_authority": "total_field_verifier",
    "process_authority": "odoo",
    "candidate_authority": "none",
}
SOVEREIGN_EFFECT_CLASSES = frozenset({
    "E0_ANSWER",
    "E1_READ",
    "E2_CANDIDATE",
    "E3_SANDBOX",
    "E4_REVERSIBLE_WRITE",
    "E5_HIGH_IMPACT",
})
SOVEREIGN_HEAD_FIELDS = frozenset({
    "sovereign_identity_root_ref",
    "sovereign_root_packet_ref",
    "sovereign_root_generation",
    "sovereign_rotation_epoch",
    "sovereign_revocation_epoch",
    "sovereign_root_state",
    "sovereign_state_hash",
    "sovereign_recovery_cooldown_until",
    "sovereign_last_completion_ref",
})
PROVIDER_FORBIDDEN_AUTHORITY_FIELDS = frozenset({
    "identity_root_ref",
    "root_packet_ref",
    "root_generation",
    "revocation_epoch",
    "role_ref",
    "seat_ref",
    "action_hash",
    "member_proof_ref",
    "member_consent",
    "consent_ref",
})
FORBIDDEN_LEDGER_VALUE_KEYS = frozenset({
    "raw_provider_profile",
    "raw_provider_subject",
    "raw_key",
    "private_key",
    "access_token",
    "refresh_token",
    "token",
    "password",
    "secret",
    "member_name",
    "email",
    "phone",
    "address",
})
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_HASH_BOUND_REF = re.compile(r"^[a-z][a-z0-9_.-]*:sha256:[0-9a-f]{64}$")
_SCOPE_REF = re.compile(r"^scope_ref:sha256:[0-9a-f]{64}$")
_LEDGER_APPEND_TOKEN = object()
_SOVEREIGN_CAS_TOKEN = object()


def _canonical_sha256(payload):
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _normalize_scope_refs(scope_refs):
    if not isinstance(scope_refs, (list, tuple)):
        raise UserError(_("Scope references must be a list."))
    normalized = sorted(set(scope_refs))
    if not normalized or any(
        not isinstance(value, str) or _SCOPE_REF.fullmatch(value) is None
        for value in normalized
    ):
        raise UserError(_("Scope references must be hash-bound references."))
    return normalized


def _normalize_hash_refs(values, label):
    if values is None:
        return []
    if not isinstance(values, (list, tuple)):
        raise UserError(_("%s must be a list of hash-bound references.") % label)
    normalized = sorted(set(values))
    if any(
        not isinstance(value, str) or _HASH_BOUND_REF.fullmatch(value) is None
        for value in normalized
    ):
        raise UserError(_("%s must contain only hash-bound references.") % label)
    return normalized


def _assert_hash_ref(value, label):
    if not isinstance(value, str) or _HASH_BOUND_REF.fullmatch(value) is None:
        raise UserError(_("%s must be a hash-bound reference.") % label)


def _assert_sha256(value, label):
    if not isinstance(value, str) or _SHA256_HEX.fullmatch(value) is None:
        raise UserError(_("%s must be a SHA-256 value.") % label)


def recovery_transition_hold_code(
    current_generation,
    current_epoch,
    expected_generation,
    expected_epoch,
    completion_seen=False,
    cooldown_active=False,
):
    if completion_seen:
        return "HOLD_RECOVERY_ALREADY_COMPLETED"
    if cooldown_active:
        return "HOLD_RECOVERY_COOLDOWN_ACTIVE"
    if expected_generation != current_generation or expected_epoch != current_epoch:
        return "HOLD_RECOVERY_STALE_CAS"
    return None


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
    sovereign_identity_root_ref = fields.Char(readonly=True, index=True, copy=False)
    sovereign_root_packet_ref = fields.Char(readonly=True, index=True, copy=False)
    sovereign_root_generation = fields.Integer(default=0, readonly=True, index=True)
    sovereign_rotation_epoch = fields.Integer(default=0, readonly=True)
    sovereign_revocation_epoch = fields.Integer(default=0, readonly=True, index=True)
    sovereign_root_state = fields.Selection([
        ("unissued", "Unissued"),
        ("active_candidate", "Active Candidate"),
        ("recovery_pending_candidate", "Recovery Pending Candidate"),
        ("revoked_candidate", "Revoked Candidate"),
    ], default="unissued", readonly=True, index=True)
    sovereign_state_hash = fields.Char(readonly=True, index=True, copy=False)
    sovereign_recovery_cooldown_until = fields.Datetime(readonly=True, index=True)
    sovereign_last_completion_ref = fields.Char(readonly=True, index=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if SOVEREIGN_HEAD_FIELDS & set(vals):
                raise UserError(_("Sovereign authority head fields are CAS-managed."))
            vals.setdefault("provisional_member_id", self._new_provisional_id())
            vals.setdefault("name", vals["provisional_member_id"])
        return super().create(vals_list)

    def write(self, vals):
        if (
            SOVEREIGN_HEAD_FIELDS & set(vals)
            and self.env.context.get("_wuchang_sovereign_cas_token")
            is not _SOVEREIGN_CAS_TOKEN
        ):
            raise UserError(_("Sovereign authority head fields are CAS-managed."))
        return super().write(vals)

    @api.model
    def _new_provisional_id(self):
        return "PROV-" + secrets.token_hex(8).upper()

    def _compute_review_level_value(self):
        self.ensure_one()
        if (
            self.member_type == "organization"
            or self.organization_role in ORGANIZATION_REVIEW_ROLES
            or self.role_scope in ORGANIZATION_REVIEW_ROLES
        ):
            return "owner_required"
        return "manager_allowed"

    def _is_individual_self_service_registration(self):
        self.ensure_one()
        return (
            self.member_type == "individual"
            and self.organization_role not in ORGANIZATION_REVIEW_ROLES
            and self.role_scope not in ORGANIZATION_REVIEW_ROLES
        )

    def _validate_individual_self_service_registration(self):
        self.ensure_one()
        if not (self.organization_name or "").strip():
            raise UserError(_("Individual members must state their affiliated group."))
        if self.membership_category not in INDIVIDUAL_JURISDICTION_CATEGORIES:
            raise UserError(
                _("Individual members must state whether they are inside the community jurisdiction.")
            )

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

    def _activate_registration(self, reviewer_id=None):
        self.ensure_one()
        identity = self.env["wuchang.member.identity.code"].create_from_registration(self)
        values = {
            "review_status": "approved",
            "reviewed_at": fields.Datetime.now(),
            "identity_code_id": identity.id,
        }
        if reviewer_id:
            values["reviewer_id"] = reviewer_id
        self.write(values)
        # Activation is an Odoo process receipt. Member consent is accepted
        # only with the complete P0/P1 basis below.
        decision_authority = "odoo"
        consent_payload = {
            "registration_ref": self.provisional_member_id,
            "member_identity_ref": identity.service_code_masked,
            "consent_type": "registration_process_receipt",
            "purpose": "membership_service",
            "consent_version": self.consent_version,
            "decision": "HOLD",
            "decision_authority": decision_authority,
            **SOVEREIGN_AUTHORITY_MODEL,
        }
        event_ref = (
            "member_consent_event_ref:sha256:"
            + _canonical_sha256(consent_payload)
        )
        self.env["wuchang.member.consent.ledger"].with_context(
            _wuchang_ledger_append_token=_LEDGER_APPEND_TOKEN
        ).create({
            "event_ref": event_ref,
            "registration_id": self.id,
            "registration_ref_id": self.id,
            "provisional_member_ref": self.provisional_member_id,
            "member_user_id": self.create_uid.id,
            "member_identity_id": identity.id,
            "consent_type": consent_payload["consent_type"],
            "purpose": "membership_service",
            "consent_version": self.consent_version,
            "decision": consent_payload["decision"],
            "decision_authority": decision_authority,
            "audit_hash": _canonical_sha256(
                {**consent_payload, "event_ref": event_ref}
            ),
        })

    def action_submit_review(self):
        for rec in self:
            if rec.review_status not in ("draft", "dead_letter"):
                continue
            if not rec.consent_version:
                raise UserError(_("Consent version is required."))
            review_level = rec._compute_review_level_value()
            rec.write({
                "review_status": "pending_review",
                "review_level": review_level,
                "consent_timestamp": fields.Datetime.now(),
            })
            if rec._is_individual_self_service_registration():
                rec._validate_individual_self_service_registration()
                rec._activate_registration()

    def action_approve(self):
        for rec in self:
            if rec.review_status != "pending_review":
                raise UserError(_("Only pending registrations can be approved."))
            if rec._is_individual_self_service_registration():
                raise UserError(_("Individual registrations do not require manual approval."))
            rec._check_approval_governance()
            rec._activate_registration(reviewer_id=self.env.user.id)

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

    def _assert_member_subject_authority(self):
        self.ensure_one()
        if self.env.su:
            raise UserError(_("HOLD_SUDO_MEMBER_AUTHORITY_BYPASS"))
        if not self.create_uid or self.create_uid != self.env.user:
            raise UserError(_("HOLD_CROSS_MEMBER_AUTHORITY"))

    def _sovereign_head_payload(
        self,
        *,
        identity_root_ref,
        root_packet_ref,
        root_generation,
        rotation_epoch,
        revocation_epoch,
        root_state,
        recovery_cooldown_until=False,
        completion_ref=False,
    ):
        return {
            "registration_ref": self.provisional_member_id,
            "identity_root_ref": identity_root_ref,
            "root_packet_ref": root_packet_ref,
            "root_generation": root_generation,
            "rotation_epoch": rotation_epoch,
            "revocation_epoch": revocation_epoch,
            "root_state": root_state,
            "recovery_cooldown_until": (
                fields.Datetime.to_string(recovery_cooldown_until)
                if recovery_cooldown_until else None
            ),
            "completion_ref": completion_ref or None,
            **SOVEREIGN_AUTHORITY_MODEL,
        }

    def _cas_update_sovereign_head(
        self,
        *,
        expected_generation,
        expected_epoch,
        expected_state,
        values,
    ):
        self.ensure_one()
        required = {
            "sovereign_identity_root_ref",
            "sovereign_root_packet_ref",
            "sovereign_root_generation",
            "sovereign_rotation_epoch",
            "sovereign_revocation_epoch",
            "sovereign_root_state",
            "sovereign_state_hash",
            "sovereign_recovery_cooldown_until",
            "sovereign_last_completion_ref",
        }
        if set(values) != required:
            raise UserError(_("HOLD_SOVEREIGN_HEAD_CAS_SHAPE"))
        self.env.cr.execute(
            """
                UPDATE wuchang_member_registration
                   SET sovereign_identity_root_ref = %s,
                       sovereign_root_packet_ref = %s,
                       sovereign_root_generation = %s,
                       sovereign_rotation_epoch = %s,
                       sovereign_revocation_epoch = %s,
                       sovereign_root_state = %s,
                       sovereign_state_hash = %s,
                       sovereign_recovery_cooldown_until = %s,
                       sovereign_last_completion_ref = %s,
                       write_uid = %s,
                       write_date = NOW()
                 WHERE id = %s
                   AND COALESCE(sovereign_root_generation, 0) = %s
                   AND COALESCE(sovereign_revocation_epoch, 0) = %s
                   AND sovereign_root_state = %s
            """,
            (
                values["sovereign_identity_root_ref"],
                values["sovereign_root_packet_ref"],
                values["sovereign_root_generation"],
                values["sovereign_rotation_epoch"],
                values["sovereign_revocation_epoch"],
                values["sovereign_root_state"],
                values["sovereign_state_hash"],
                values["sovereign_recovery_cooldown_until"] or None,
                values["sovereign_last_completion_ref"] or None,
                self.env.user.id,
                self.id,
                expected_generation,
                expected_epoch,
                expected_state,
            ),
        )
        if self.env.cr.rowcount != 1:
            raise UserError(_("HOLD_RECOVERY_STALE_CAS"))
        self.invalidate_recordset(list(required))

    def append_initial_sovereign_root_candidate(self, root_candidate):
        self.ensure_one()
        self._assert_member_subject_authority()
        if self.sovereign_root_generation != 0:
            raise UserError(_("HOLD_DOUBLE_ACTIVE_ROOT"))
        if not isinstance(root_candidate, dict):
            raise UserError(_("HOLD_ROOT_NOT_EVIDENCED"))
        forbidden = FORBIDDEN_LEDGER_VALUE_KEYS & set(root_candidate)
        if forbidden:
            raise UserError(_("HOLD_PRIVATE_VALUE_FORBIDDEN"))
        for field_name in (
            "identity_root_ref",
            "root_packet_ref",
            "member_proof_ref",
            "p1_evidence_ref",
        ):
            _assert_hash_ref(root_candidate.get(field_name), field_name)
        for field_name in ("member_display_hash", "payload_sha256"):
            _assert_sha256(root_candidate.get(field_name), field_name)
        if not root_candidate.get("terms_version"):
            raise UserError(_("HOLD_TERMS_VERSION_REQUIRED"))

        issued_at = fields.Datetime.now()
        root_payload = {
            "registration_ref": self.provisional_member_id,
            "member_user_ref": (
                "member_subject_ref:sha256:"
                + _canonical_sha256({
                    "registration_ref": self.provisional_member_id,
                    "odoo_user_id": self.env.user.id,
                })
            ),
            "identity_root_ref": root_candidate["identity_root_ref"],
            "root_packet_ref": root_candidate["root_packet_ref"],
            "previous_root_packet_ref": None,
            "root_generation": 1,
            "rotation_epoch": 0,
            "revocation_epoch": 0,
            "member_display_hash": root_candidate["member_display_hash"],
            "terms_version": root_candidate["terms_version"],
            "member_proof_ref": root_candidate["member_proof_ref"],
            "p1_evidence_ref": root_candidate["p1_evidence_ref"],
            "source_payload_sha256": root_candidate["payload_sha256"],
            "issued_at": fields.Datetime.to_string(issued_at),
            **SOVEREIGN_AUTHORITY_MODEL,
        }
        root_payload["ledger_hash"] = _canonical_sha256(root_payload)
        self.env["wuchang.member.sovereign.root.ledger"].with_context(
            _wuchang_ledger_append_token=_LEDGER_APPEND_TOKEN
        ).create({
            "event_ref": (
                "root_ledger_event_ref:sha256:"
                + _canonical_sha256(root_payload)
            ),
            "registration_id": self.id,
            "member_user_id": self.env.user.id,
            **root_payload,
        })
        head_payload = self._sovereign_head_payload(
            identity_root_ref=root_candidate["identity_root_ref"],
            root_packet_ref=root_candidate["root_packet_ref"],
            root_generation=1,
            rotation_epoch=0,
            revocation_epoch=0,
            root_state="active_candidate",
        )
        self._cas_update_sovereign_head(
            expected_generation=0,
            expected_epoch=0,
            expected_state="unissued",
            values={
                "sovereign_identity_root_ref": root_candidate["identity_root_ref"],
                "sovereign_root_packet_ref": root_candidate["root_packet_ref"],
                "sovereign_root_generation": 1,
                "sovereign_rotation_epoch": 0,
                "sovereign_revocation_epoch": 0,
                "sovereign_root_state": "active_candidate",
                "sovereign_state_hash": _canonical_sha256(head_payload),
                "sovereign_recovery_cooldown_until": False,
                "sovereign_last_completion_ref": False,
            },
        )
        return {
            "state": "PASS_ROOT_LEDGER_SOURCE_CANDIDATE",
            "candidate_only": True,
            "root_generation": 1,
            "revocation_epoch": 0,
            "runtime_propagated": False,
        }

    def append_member_consent_candidate(
        self,
        *,
        action_hash,
        purpose_ref,
        scope_refs,
        effect_class,
        member_proof_ref,
        p1_evidence_ref,
        decision="CONSENT",
        supersedes_consent_ref=None,
        amount_currency_hash=None,
    ):
        self.ensure_one()
        self._assert_member_subject_authority()
        if self.sovereign_root_generation < 1:
            raise UserError(_("HOLD_ROOT_NOT_EVIDENCED"))
        _assert_sha256(action_hash, "action_hash")
        _assert_hash_ref(purpose_ref, "purpose_ref")
        _assert_hash_ref(member_proof_ref, "member_proof_ref")
        _assert_hash_ref(p1_evidence_ref, "p1_evidence_ref")
        normalized_scopes = _normalize_scope_refs(scope_refs)
        if effect_class not in SOVEREIGN_EFFECT_CLASSES:
            raise UserError(_("HOLD_EFFECT_CLASS_INVALID"))
        if decision not in {"CONSENT", "DENY", "WITHDRAW", "HOLD"}:
            raise UserError(_("HOLD_CONSENT_DECISION_INVALID"))
        if decision == "WITHDRAW" and not supersedes_consent_ref:
            raise UserError(_("HOLD_CONSENT_SUPERSESSION_REQUIRED"))
        if supersedes_consent_ref:
            _assert_hash_ref(supersedes_consent_ref, "supersedes_consent_ref")
        if amount_currency_hash is not None:
            _assert_sha256(amount_currency_hash, "amount_currency_hash")

        issued_at = fields.Datetime.now()
        payload = {
            "registration_ref": self.provisional_member_id,
            "identity_root_ref": self.sovereign_identity_root_ref,
            "root_packet_ref": self.sovereign_root_packet_ref,
            "root_generation": self.sovereign_root_generation,
            "revocation_epoch": self.sovereign_revocation_epoch,
            "action_hash": action_hash,
            "purpose_ref": purpose_ref,
            "scope_refs": normalized_scopes,
            "effect_class": effect_class,
            "decision": decision,
            "member_proof_ref": member_proof_ref,
            "p1_evidence_ref": p1_evidence_ref,
            "supersedes_consent_ref": supersedes_consent_ref,
            "amount_currency_hash": amount_currency_hash,
            "issued_at": fields.Datetime.to_string(issued_at),
            **SOVEREIGN_AUTHORITY_MODEL,
        }
        event_ref = "member_consent_event_ref:sha256:" + _canonical_sha256(payload)
        payload_hash = _canonical_sha256({**payload, "event_ref": event_ref})
        self.env["wuchang.member.consent.ledger"].with_context(
            _wuchang_ledger_append_token=_LEDGER_APPEND_TOKEN
        ).create({
            "event_ref": event_ref,
            "registration_id": self.id,
            "registration_ref_id": self.id,
            "provisional_member_ref": self.provisional_member_id,
            "member_user_id": self.env.user.id,
            "member_identity_id": self.identity_code_id.id,
            "consent_type": "sovereign_action",
            "purpose": purpose_ref,
            "consent_version": self.consent_version,
            "decision": decision,
            "decision_authority": "member",
            "identity_root_ref": self.sovereign_identity_root_ref,
            "root_packet_ref": self.sovereign_root_packet_ref,
            "root_generation": self.sovereign_root_generation,
            "revocation_epoch": self.sovereign_revocation_epoch,
            "action_hash": action_hash,
            "purpose_ref": purpose_ref,
            "scope_refs_json": json.dumps(normalized_scopes),
            "effect_class": effect_class,
            "amount_currency_hash": amount_currency_hash,
            "member_proof_ref": member_proof_ref,
            "p1_evidence_ref": p1_evidence_ref,
            "supersedes_consent_ref": supersedes_consent_ref,
            "audit_hash": payload_hash,
        })
        return {
            "state": "PASS_CONSENT_LEDGER_SOURCE_CANDIDATE",
            "candidate_only": True,
            "event_ref": event_ref,
            "action_hash": action_hash,
            "runtime_propagated": False,
        }

    def _append_invalidation_candidates(
        self,
        *,
        targets,
        reason_code,
        p1_evidence_ref,
        root_generation,
        revocation_epoch,
    ):
        self.ensure_one()
        _assert_hash_ref(p1_evidence_ref, "p1_evidence_ref")
        values_list = []
        for target_type, target_ref in targets:
            if target_type not in {
                "ROOT",
                "SESSION",
                "SCENE",
                "CONSENT_LEASE",
            }:
                raise UserError(_("HOLD_INVALIDATION_TARGET_TYPE"))
            _assert_hash_ref(target_ref, "invalidation_target_ref")
            payload = {
                "registration_ref": self.provisional_member_id,
                "target_type": target_type,
                "target_ref": target_ref,
                "reason_code": reason_code,
                "root_generation": root_generation,
                "revocation_epoch": revocation_epoch,
                "p1_evidence_ref": p1_evidence_ref,
                "runtime_propagated": False,
                **SOVEREIGN_AUTHORITY_MODEL,
            }
            event_ref = (
                "invalidation_candidate_ref:sha256:"
                + _canonical_sha256(payload)
            )
            values_list.append({
                "event_ref": event_ref,
                "registration_id": self.id,
                "member_user_id": self.env.user.id,
                "target_type": target_type,
                "target_ref": target_ref,
                "reason_code": reason_code,
                "root_generation": root_generation,
                "revocation_epoch": revocation_epoch,
                "p1_evidence_ref": p1_evidence_ref,
                "payload_sha256": _canonical_sha256(
                    {**payload, "event_ref": event_ref}
                ),
                "runtime_propagated": False,
                **SOVEREIGN_AUTHORITY_MODEL,
            })
        if values_list:
            self.env[
                "wuchang.member.sovereign.invalidation.candidate"
            ].with_context(
                _wuchang_ledger_append_token=_LEDGER_APPEND_TOKEN
            ).create(values_list)
        return [values["event_ref"] for values in values_list]

    def append_revocation_candidate(
        self,
        *,
        target_type,
        target_ref,
        expected_epoch,
        reason_code,
        member_proof_ref,
        p1_evidence_ref,
    ):
        self.ensure_one()
        self._assert_member_subject_authority()
        if self.sovereign_root_generation < 1:
            raise UserError(_("HOLD_ROOT_NOT_EVIDENCED"))
        if expected_epoch != self.sovereign_revocation_epoch:
            raise UserError(_("HOLD_REVOCATION_EPOCH_STALE"))
        _assert_hash_ref(target_ref, "target_ref")
        _assert_hash_ref(member_proof_ref, "member_proof_ref")
        _assert_hash_ref(p1_evidence_ref, "p1_evidence_ref")
        new_epoch = expected_epoch + 1
        issued_at = fields.Datetime.now()
        payload = {
            "registration_ref": self.provisional_member_id,
            "identity_root_ref": self.sovereign_identity_root_ref,
            "root_packet_ref": self.sovereign_root_packet_ref,
            "root_generation": self.sovereign_root_generation,
            "previous_revocation_epoch": expected_epoch,
            "new_revocation_epoch": new_epoch,
            "target_type": target_type,
            "target_ref": target_ref,
            "reason_code": reason_code,
            "member_proof_ref": member_proof_ref,
            "p1_evidence_ref": p1_evidence_ref,
            "issued_at": fields.Datetime.to_string(issued_at),
            **SOVEREIGN_AUTHORITY_MODEL,
        }
        event_ref = "revocation_event_ref:sha256:" + _canonical_sha256(payload)
        self.env["wuchang.member.sovereign.revocation.ledger"].with_context(
            _wuchang_ledger_append_token=_LEDGER_APPEND_TOKEN
        ).create({
            "event_ref": event_ref,
            "registration_id": self.id,
            "member_user_id": self.env.user.id,
            "identity_root_ref": self.sovereign_identity_root_ref,
            "root_packet_ref": self.sovereign_root_packet_ref,
            "root_generation": self.sovereign_root_generation,
            "previous_revocation_epoch": expected_epoch,
            "new_revocation_epoch": new_epoch,
            "target_type": target_type,
            "target_ref": target_ref,
            "reason_code": reason_code,
            "member_proof_ref": member_proof_ref,
            "p1_evidence_ref": p1_evidence_ref,
            "payload_sha256": _canonical_sha256(
                {**payload, "event_ref": event_ref}
            ),
            **SOVEREIGN_AUTHORITY_MODEL,
        })
        invalidation_refs = self._append_invalidation_candidates(
            targets=[(target_type, target_ref)],
            reason_code=reason_code,
            p1_evidence_ref=p1_evidence_ref,
            root_generation=self.sovereign_root_generation,
            revocation_epoch=new_epoch,
        )
        new_state = (
            "revoked_candidate"
            if target_type == "ROOT"
            else self.sovereign_root_state
        )
        head_payload = self._sovereign_head_payload(
            identity_root_ref=self.sovereign_identity_root_ref,
            root_packet_ref=self.sovereign_root_packet_ref,
            root_generation=self.sovereign_root_generation,
            rotation_epoch=self.sovereign_rotation_epoch,
            revocation_epoch=new_epoch,
            root_state=new_state,
            recovery_cooldown_until=self.sovereign_recovery_cooldown_until,
            completion_ref=self.sovereign_last_completion_ref,
        )
        self._cas_update_sovereign_head(
            expected_generation=self.sovereign_root_generation,
            expected_epoch=expected_epoch,
            expected_state=self.sovereign_root_state,
            values={
                "sovereign_identity_root_ref": self.sovereign_identity_root_ref,
                "sovereign_root_packet_ref": self.sovereign_root_packet_ref,
                "sovereign_root_generation": self.sovereign_root_generation,
                "sovereign_rotation_epoch": self.sovereign_rotation_epoch,
                "sovereign_revocation_epoch": new_epoch,
                "sovereign_root_state": new_state,
                "sovereign_state_hash": _canonical_sha256(head_payload),
                "sovereign_recovery_cooldown_until": (
                    self.sovereign_recovery_cooldown_until or False
                ),
                "sovereign_last_completion_ref": (
                    self.sovereign_last_completion_ref or False
                ),
            },
        )
        return {
            "state": "PASS_REVOCATION_LEDGER_SOURCE_CANDIDATE",
            "candidate_only": True,
            "event_ref": event_ref,
            "revocation_epoch": new_epoch,
            "invalidation_candidate_refs": invalidation_refs,
            "runtime_propagated": False,
        }

    def request_sovereign_recovery_candidate(
        self,
        *,
        expected_generation,
        expected_epoch,
        new_identity_root_ref,
        new_root_packet_ref,
        new_member_display_hash,
        new_root_payload_sha256,
        recovery_cas_ref,
        completion_ref,
        member_proof_ref,
        p1_evidence_ref,
        session_refs=None,
        scene_refs=None,
        consent_lease_refs=None,
    ):
        self.ensure_one()
        self._assert_member_subject_authority()
        now = fields.Datetime.now()
        cooldown_active = bool(
            self.sovereign_recovery_cooldown_until
            and now < self.sovereign_recovery_cooldown_until
        )
        completion_seen = bool(
            self.env["wuchang.member.sovereign.recovery.ledger"].search_count([
                ("completion_guard_key", "=", completion_ref),
            ])
        )
        hold_code = recovery_transition_hold_code(
            self.sovereign_root_generation,
            self.sovereign_revocation_epoch,
            expected_generation,
            expected_epoch,
            completion_seen=completion_seen,
            cooldown_active=cooldown_active,
        )
        if hold_code:
            raise UserError(_(hold_code))
        for value, label in (
            (new_identity_root_ref, "new_identity_root_ref"),
            (new_root_packet_ref, "new_root_packet_ref"),
            (recovery_cas_ref, "recovery_cas_ref"),
            (completion_ref, "completion_ref"),
            (member_proof_ref, "member_proof_ref"),
            (p1_evidence_ref, "p1_evidence_ref"),
        ):
            _assert_hash_ref(value, label)
        for value, label in (
            (new_member_display_hash, "new_member_display_hash"),
            (new_root_payload_sha256, "new_root_payload_sha256"),
        ):
            _assert_sha256(value, label)
        normalized_sessions = _normalize_hash_refs(session_refs, "session_refs")
        normalized_scenes = _normalize_hash_refs(scene_refs, "scene_refs")
        normalized_consents = _normalize_hash_refs(
            consent_lease_refs, "consent_lease_refs"
        )
        cooldown_until = fields.Datetime.add(now, minutes=5)
        payload = {
            "registration_ref": self.provisional_member_id,
            "identity_root_ref": self.sovereign_identity_root_ref,
            "root_packet_ref": self.sovereign_root_packet_ref,
            "expected_generation": expected_generation,
            "expected_epoch": expected_epoch,
            "new_identity_root_ref": new_identity_root_ref,
            "new_root_packet_ref": new_root_packet_ref,
            "new_member_display_hash": new_member_display_hash,
            "new_root_payload_sha256": new_root_payload_sha256,
            "recovery_cas_ref": recovery_cas_ref,
            "completion_ref": completion_ref,
            "member_proof_ref": member_proof_ref,
            "p1_evidence_ref": p1_evidence_ref,
            "session_refs": normalized_sessions,
            "scene_refs": normalized_scenes,
            "consent_lease_refs": normalized_consents,
            "cooldown_until": fields.Datetime.to_string(cooldown_until),
            **SOVEREIGN_AUTHORITY_MODEL,
        }
        event_ref = "recovery_event_ref:sha256:" + _canonical_sha256(payload)
        self.env["wuchang.member.sovereign.recovery.ledger"].with_context(
            _wuchang_ledger_append_token=_LEDGER_APPEND_TOKEN
        ).create({
            "event_ref": event_ref,
            "event_type": "REQUESTED_CANDIDATE",
            "registration_id": self.id,
            "member_user_id": self.env.user.id,
            "identity_root_ref": self.sovereign_identity_root_ref,
            "root_packet_ref": self.sovereign_root_packet_ref,
            "expected_generation": expected_generation,
            "expected_epoch": expected_epoch,
            "new_identity_root_ref": new_identity_root_ref,
            "new_root_packet_ref": new_root_packet_ref,
            "new_member_display_hash": new_member_display_hash,
            "new_root_payload_sha256": new_root_payload_sha256,
            "recovery_cas_ref": recovery_cas_ref,
            "requested_completion_ref": completion_ref,
            "member_proof_ref": member_proof_ref,
            "p1_evidence_ref": p1_evidence_ref,
            "session_refs_json": json.dumps(normalized_sessions),
            "scene_refs_json": json.dumps(normalized_scenes),
            "consent_lease_refs_json": json.dumps(normalized_consents),
            "cooldown_until": cooldown_until,
            "payload_sha256": _canonical_sha256(
                {**payload, "event_ref": event_ref}
            ),
            **SOVEREIGN_AUTHORITY_MODEL,
        })
        head_payload = self._sovereign_head_payload(
            identity_root_ref=self.sovereign_identity_root_ref,
            root_packet_ref=self.sovereign_root_packet_ref,
            root_generation=expected_generation,
            rotation_epoch=self.sovereign_rotation_epoch,
            revocation_epoch=expected_epoch,
            root_state="recovery_pending_candidate",
            recovery_cooldown_until=cooldown_until,
            completion_ref=self.sovereign_last_completion_ref,
        )
        self._cas_update_sovereign_head(
            expected_generation=expected_generation,
            expected_epoch=expected_epoch,
            expected_state="active_candidate",
            values={
                "sovereign_identity_root_ref": self.sovereign_identity_root_ref,
                "sovereign_root_packet_ref": self.sovereign_root_packet_ref,
                "sovereign_root_generation": expected_generation,
                "sovereign_rotation_epoch": self.sovereign_rotation_epoch,
                "sovereign_revocation_epoch": expected_epoch,
                "sovereign_root_state": "recovery_pending_candidate",
                "sovereign_state_hash": _canonical_sha256(head_payload),
                "sovereign_recovery_cooldown_until": cooldown_until,
                "sovereign_last_completion_ref": (
                    self.sovereign_last_completion_ref or False
                ),
            },
        )
        return {
            "state": "PASS_RECOVERY_REQUEST_SOURCE_CANDIDATE",
            "candidate_only": True,
            "event_ref": event_ref,
            "cooldown_until": fields.Datetime.to_string(cooldown_until),
            "runtime_propagated": False,
        }

    def complete_sovereign_recovery_candidate(
        self,
        *,
        recovery_event_ref,
        completion_ref,
        expected_generation,
        expected_epoch,
    ):
        self.ensure_one()
        self._assert_member_subject_authority()
        for value, label in (
            (recovery_event_ref, "recovery_event_ref"),
            (completion_ref, "completion_ref"),
        ):
            _assert_hash_ref(value, label)
        recovery_ledger = self.env[
            "wuchang.member.sovereign.recovery.ledger"
        ]
        completion_seen = bool(recovery_ledger.search_count([
            ("completion_guard_key", "=", completion_ref),
        ]))
        hold_code = recovery_transition_hold_code(
            self.sovereign_root_generation,
            self.sovereign_revocation_epoch,
            expected_generation,
            expected_epoch,
            completion_seen=completion_seen,
            cooldown_active=False,
        )
        if hold_code:
            raise UserError(_(hold_code))
        request_event = recovery_ledger.search([
            ("event_ref", "=", recovery_event_ref),
            ("event_type", "=", "REQUESTED_CANDIDATE"),
            ("registration_id", "=", self.id),
            ("member_user_id", "=", self.env.user.id),
        ], limit=1)
        if not request_event:
            raise UserError(_("HOLD_RECOVERY_NOT_EVIDENCED"))
        if (
            request_event.requested_completion_ref != completion_ref
            or request_event.expected_generation != expected_generation
            or request_event.expected_epoch != expected_epoch
        ):
            raise UserError(_("HOLD_RECOVERY_STALE_CAS"))
        if (
            request_event.cooldown_until
            and fields.Datetime.now() < request_event.cooldown_until
        ):
            raise UserError(_("HOLD_RECOVERY_COOLDOWN_ACTIVE"))

        new_generation = expected_generation + 1
        new_epoch = expected_epoch + 1
        root_payload = {
            "registration_ref": self.provisional_member_id,
            "member_user_ref": (
                "member_subject_ref:sha256:"
                + _canonical_sha256({
                    "registration_ref": self.provisional_member_id,
                    "odoo_user_id": self.env.user.id,
                })
            ),
            "identity_root_ref": request_event.new_identity_root_ref,
            "root_packet_ref": request_event.new_root_packet_ref,
            "previous_root_packet_ref": self.sovereign_root_packet_ref,
            "root_generation": new_generation,
            "rotation_epoch": self.sovereign_rotation_epoch + 1,
            "revocation_epoch": new_epoch,
            "member_display_hash": request_event.new_member_display_hash,
            "terms_version": self.consent_version,
            "member_proof_ref": request_event.member_proof_ref,
            "p1_evidence_ref": request_event.p1_evidence_ref,
            "source_payload_sha256": request_event.new_root_payload_sha256,
            "issued_at": fields.Datetime.to_string(fields.Datetime.now()),
            **SOVEREIGN_AUTHORITY_MODEL,
        }
        root_payload["ledger_hash"] = _canonical_sha256(root_payload)
        self.env["wuchang.member.sovereign.root.ledger"].with_context(
            _wuchang_ledger_append_token=_LEDGER_APPEND_TOKEN
        ).create({
            "event_ref": (
                "root_ledger_event_ref:sha256:"
                + _canonical_sha256(root_payload)
            ),
            "registration_id": self.id,
            "member_user_id": self.env.user.id,
            **root_payload,
        })

        targets = [("ROOT", self.sovereign_root_packet_ref)]
        targets.extend(
            ("SESSION", value)
            for value in json.loads(request_event.session_refs_json or "[]")
        )
        targets.extend(
            ("SCENE", value)
            for value in json.loads(request_event.scene_refs_json or "[]")
        )
        targets.extend(
            ("CONSENT_LEASE", value)
            for value in json.loads(request_event.consent_lease_refs_json or "[]")
        )
        invalidation_refs = self._append_invalidation_candidates(
            targets=targets,
            reason_code="RECOVERY_ROOT_ROTATION",
            p1_evidence_ref=request_event.p1_evidence_ref,
            root_generation=new_generation,
            revocation_epoch=new_epoch,
        )
        completion_payload = {
            "request_event_ref": recovery_event_ref,
            "completion_ref": completion_ref,
            "registration_ref": self.provisional_member_id,
            "previous_root_packet_ref": self.sovereign_root_packet_ref,
            "new_root_packet_ref": request_event.new_root_packet_ref,
            "new_generation": new_generation,
            "new_revocation_epoch": new_epoch,
            "invalidation_candidate_refs": invalidation_refs,
            "runtime_propagated": False,
            **SOVEREIGN_AUTHORITY_MODEL,
        }
        completion_event_ref = (
            "recovery_completion_event_ref:sha256:"
            + _canonical_sha256(completion_payload)
        )
        recovery_ledger.with_context(
            _wuchang_ledger_append_token=_LEDGER_APPEND_TOKEN
        ).create({
            "event_ref": completion_event_ref,
            "event_type": "COMPLETED_CANDIDATE",
            "registration_id": self.id,
            "member_user_id": self.env.user.id,
            "identity_root_ref": request_event.new_identity_root_ref,
            "root_packet_ref": request_event.new_root_packet_ref,
            "expected_generation": expected_generation,
            "expected_epoch": expected_epoch,
            "new_identity_root_ref": request_event.new_identity_root_ref,
            "new_root_packet_ref": request_event.new_root_packet_ref,
            "new_member_display_hash": request_event.new_member_display_hash,
            "new_root_payload_sha256": request_event.new_root_payload_sha256,
            "recovery_cas_ref": request_event.recovery_cas_ref,
            "requested_completion_ref": completion_ref,
            "completion_guard_key": completion_ref,
            "previous_event_ref": recovery_event_ref,
            "member_proof_ref": request_event.member_proof_ref,
            "p1_evidence_ref": request_event.p1_evidence_ref,
            "session_refs_json": request_event.session_refs_json,
            "scene_refs_json": request_event.scene_refs_json,
            "consent_lease_refs_json": request_event.consent_lease_refs_json,
            "cooldown_until": request_event.cooldown_until,
            "payload_sha256": _canonical_sha256(
                {**completion_payload, "event_ref": completion_event_ref}
            ),
            **SOVEREIGN_AUTHORITY_MODEL,
        })
        head_payload = self._sovereign_head_payload(
            identity_root_ref=request_event.new_identity_root_ref,
            root_packet_ref=request_event.new_root_packet_ref,
            root_generation=new_generation,
            rotation_epoch=self.sovereign_rotation_epoch + 1,
            revocation_epoch=new_epoch,
            root_state="active_candidate",
            recovery_cooldown_until=request_event.cooldown_until,
            completion_ref=completion_ref,
        )
        self._cas_update_sovereign_head(
            expected_generation=expected_generation,
            expected_epoch=expected_epoch,
            expected_state="recovery_pending_candidate",
            values={
                "sovereign_identity_root_ref": request_event.new_identity_root_ref,
                "sovereign_root_packet_ref": request_event.new_root_packet_ref,
                "sovereign_root_generation": new_generation,
                "sovereign_rotation_epoch": self.sovereign_rotation_epoch + 1,
                "sovereign_revocation_epoch": new_epoch,
                "sovereign_root_state": "active_candidate",
                "sovereign_state_hash": _canonical_sha256(head_payload),
                "sovereign_recovery_cooldown_until": request_event.cooldown_until,
                "sovereign_last_completion_ref": completion_ref,
            },
        )
        return {
            "state": "PASS_RECOVERY_COMPLETION_SOURCE_CANDIDATE",
            "candidate_only": True,
            "completion_event_ref": completion_event_ref,
            "root_generation": new_generation,
            "revocation_epoch": new_epoch,
            "invalidation_candidate_refs": invalidation_refs,
            "runtime_propagated": False,
        }


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
    member_identity_id = fields.Many2one(
        "wuchang.member.identity.code", readonly=True, ondelete="restrict"
    )
    member_user_id = fields.Many2one(
        "res.users", required=True, readonly=True, index=True, ondelete="restrict"
    )
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
    verified_channel_binding_ref = fields.Char(readonly=True, index=True, copy=False)
    consent_ref = fields.Char(readonly=True)
    last_login_at = fields.Datetime()

    _sql_constraints = [
        (
            "provider_subject_hash_unique",
            "unique(provider, provider_subject_hash)",
            "This external auth subject is already bound.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            forbidden = (
                PROVIDER_FORBIDDEN_AUTHORITY_FIELDS & set(vals)
            ) | (FORBIDDEN_LEDGER_VALUE_KEYS & set(vals))
            if forbidden:
                raise UserError(_("HOLD_PROVIDER_AUTHORITY_ESCALATION"))
            _assert_sha256(
                vals.get("provider_subject_hash"),
                "provider_subject_hash",
            )
            binding_ref = vals.get("verified_channel_binding_ref")
            if binding_ref:
                _assert_hash_ref(binding_ref, "verified_channel_binding_ref")
            if vals.get("binding_status") == "bound" and not binding_ref:
                raise UserError(_("HOLD_VERIFIED_CHANNEL_NOT_EVIDENCED"))
            registration_id = vals.get("registration_ref_id")
            if registration_id:
                registration = self.env[
                    "wuchang.member.registration"
                ].browse(registration_id).exists()
                if registration:
                    vals["member_user_id"] = registration.create_uid.id
        return super().create(vals_list)

    def write(self, vals):
        allowed = {
            "binding_status",
            "member_identity_id",
            "verified_channel_binding_ref",
            "last_login_at",
        }
        if set(vals) - allowed:
            raise UserError(_("HOLD_PROVIDER_BINDING_IMMUTABLE"))
        forbidden = (
            PROVIDER_FORBIDDEN_AUTHORITY_FIELDS & set(vals)
        ) | (FORBIDDEN_LEDGER_VALUE_KEYS & set(vals))
        if forbidden:
            raise UserError(_("HOLD_PROVIDER_AUTHORITY_ESCALATION"))
        binding_ref = vals.get("verified_channel_binding_ref")
        if binding_ref:
            _assert_hash_ref(binding_ref, "verified_channel_binding_ref")
        target_status = vals.get("binding_status")
        if target_status == "revoked":
            raise UserError(_("HOLD_CHANNEL_REVOKE_CANDIDATE_REQUIRED"))
        for record in self:
            final_status = target_status or record.binding_status
            final_ref = binding_ref or record.verified_channel_binding_ref
            if final_status == "bound" and not final_ref:
                raise UserError(_("HOLD_VERIFIED_CHANNEL_NOT_EVIDENCED"))
        return super().write(vals)

    @api.model
    def hash_subject(self, provider, subject):
        if not provider or not subject:
            raise UserError(_("Provider and subject are required."))
        return hashlib.sha256(f"{provider}:{subject}".encode("utf-8")).hexdigest()

    @api.model
    def resolve_provider_subject(self, provider, subject):
        """Resolve an existing local link without creating or changing one."""
        subject_hash = self.hash_subject(provider, subject)
        provider_ref = f"provider:{provider}:sha256:{subject_hash}"
        binding = self.sudo().search([
            ("provider", "=", provider),
            ("provider_subject_hash", "=", subject_hash),
        ], limit=1)
        if not binding:
            return {
                "provider_subject_reference": provider_ref,
                "local_subject_reference": None,
                "link_state": "LINKING_PENDING",
                "consent_reference": None,
                "verifier_result": "HOLD",
            }
        if binding.binding_status == "revoked":
            return {
                "provider_subject_reference": provider_ref,
                "local_subject_reference": None,
                "link_state": "LINK_DENIED",
                "consent_reference": binding.consent_ref or None,
                "revoked_at": fields.Datetime.to_string(binding.write_date),
                "verifier_result": "BLOCK",
            }
        if binding.binding_status != "bound":
            return {
                "provider_subject_reference": provider_ref,
                "local_subject_reference": None,
                "link_state": "EXPLICIT_LINK_CONSENT_REQUIRED",
                "consent_reference": binding.consent_ref or None,
                "verifier_result": "HOLD",
            }
        identity = binding.member_identity_id
        if not identity or identity.active_status != "active":
            return {
                "provider_subject_reference": provider_ref,
                "local_subject_reference": None,
                "link_state": "HUMAN_REVIEW_REQUIRED",
                "consent_reference": binding.consent_ref or None,
                "verifier_result": "HOLD",
            }
        local_seed = f"member:{identity.id}:{identity.service_code_masked or ''}"
        local_ref = "subject:sha256:" + hashlib.sha256(local_seed.encode("utf-8")).hexdigest()
        prefix_ref = self.env["ir.config_parameter"].sudo().get_param(
            f"wuchang.identity_prefix_ref.{provider}.{subject_hash}",
            "",
        )
        if _IDENTITY_PREFIX_REF.fullmatch(prefix_ref or "") is None:
            prefix_ref = None
        return {
            "provider_subject_reference": provider_ref,
            "local_subject_reference": local_ref,
            "identity_prefix_ref": prefix_ref,
            "link_state": "PROVIDER_LINK_FOUND",
            "consent_reference": binding.consent_ref or None,
            "linked_at": fields.Datetime.to_string(binding.create_date),
            "last_verified_at": fields.Datetime.to_string(binding.last_login_at),
            "verified_channel_binding_ref": (
                binding.verified_channel_binding_ref or None
            ),
            "verifier_result": "PASS",
        }

    @api.model
    def resolve_provider_subject_for_session(
        self,
        provider,
        authenticated_subject,
        session_user,
    ):
        """Resolve one provider subject only for the current authenticated user."""

        if (
            self.env.su
            or not session_user
            or session_user != self.env.user
        ):
            return {
                "link_state": "AUTHENTICATED_MEMBER_SESSION_REQUIRED",
                "verifier_result": "HOLD",
            }
        subject_hash = self.hash_subject(provider, authenticated_subject)
        binding = self.search([
            ("provider", "=", provider),
            ("provider_subject_hash", "=", subject_hash),
        ], limit=1)
        if not binding or binding.member_user_id != session_user:
            return {
                "provider_subject_reference": (
                    f"provider:{provider}:sha256:{subject_hash}"
                ),
                "local_subject_reference": None,
                "verified_channel_binding_ref": None,
                "link_state": "CROSS_MEMBER_OR_UNBOUND_CHANNEL",
                "verifier_result": "HOLD",
            }
        resolution = self.resolve_provider_subject(
            provider,
            authenticated_subject,
        )
        if (
            resolution.get("verifier_result") != "PASS"
            or not binding.verified_channel_binding_ref
        ):
            resolution["verified_channel_binding_ref"] = None
            resolution["link_state"] = "VERIFIED_CHANNEL_BINDING_REQUIRED"
            resolution["verifier_result"] = "HOLD"
            return resolution
        resolution["verified_channel_binding_ref"] = (
            binding.verified_channel_binding_ref
        )
        resolution["member_ref"] = (
            "member_ref:sha256:"
            + hashlib.sha256(
                f"member-user:{session_user.id}".encode("utf-8")
            ).hexdigest()
        )
        return resolution

    def build_channel_revoke_candidate(
        self,
        *,
        identity_root_ref,
        root_generation,
        revocation_epoch,
        session_ref,
    ):
        """Build a no-write unlink/revoke candidate bound to the member head."""

        self.ensure_one()
        registration = self.env["wuchang.member.registration"].browse(
            self.registration_ref_id
        ).exists()
        if (
            self.env.su
            or not registration
            or self.member_user_id != self.env.user
            or registration.create_uid != self.env.user
        ):
            raise UserError(_("HOLD_CROSS_MEMBER_AUTHORITY"))
        if (
            registration.sovereign_identity_root_ref != identity_root_ref
            or registration.sovereign_root_generation != root_generation
            or registration.sovereign_revocation_epoch != revocation_epoch
        ):
            raise UserError(_("HOLD_CHANNEL_REVOKE_ROOT_HEAD_MISMATCH"))
        for field_name, value in (
            ("identity_root_ref", identity_root_ref),
            ("session_ref", session_ref),
            (
                "verified_channel_binding_ref",
                self.verified_channel_binding_ref,
            ),
        ):
            _assert_hash_ref(value, field_name)
        material = {
            "provider": self.provider,
            "provider_subject_hash": self.provider_subject_hash,
            "verified_channel_binding_ref": (
                self.verified_channel_binding_ref
            ),
            "identity_root_ref": identity_root_ref,
            "root_generation": root_generation,
            "revocation_epoch": revocation_epoch,
            "session_ref": session_ref,
            "member_user_ref": (
                "member_user_ref:sha256:"
                + hashlib.sha256(
                    f"member-user:{self.env.user.id}".encode("utf-8")
                ).hexdigest()
            ),
            "candidate_only": True,
            "revoke_applied": False,
            "unlink_applied": False,
        }
        return {
            "state": "PASS_CHANNEL_REVOKE_CANDIDATE",
            **material,
            "candidate_ref": (
                "channel_revoke_candidate_ref:sha256:"
                + _canonical_sha256(material)
            ),
        }

    def unlink(self):
        raise UserError(_("HOLD_CHANNEL_BINDING_UNLINK_FORBIDDEN"))


class WuchangMemberConsentLedger(models.Model):
    _name = "wuchang.member.consent.ledger"
    _description = "Wuchang Append-Only Member Consent Authority Ledger"
    _order = "create_date desc"

    event_ref = fields.Char(readonly=True, required=True, index=True, copy=False)
    registration_id = fields.Many2one(
        "wuchang.member.registration",
        readonly=True,
        index=True,
        ondelete="restrict",
    )
    registration_ref_id = fields.Integer(index=True)
    provisional_member_ref = fields.Char(index=True)
    member_identity_id = fields.Many2one(
        "wuchang.member.identity.code", readonly=True, ondelete="restrict"
    )
    member_user_id = fields.Many2one(
        "res.users", required=True, readonly=True, index=True, ondelete="restrict"
    )
    consent_type = fields.Char(required=True)
    purpose = fields.Char(required=True)
    consent_version = fields.Char(required=True, default="v1")
    decision = fields.Selection([
        ("CONSENT", "Consent"),
        ("DENY", "Deny"),
        ("WITHDRAW", "Withdraw"),
        ("HOLD", "Hold"),
    ], required=True, default="HOLD", readonly=True, index=True)
    decision_authority = fields.Selection([
        ("member", "Member"),
        ("odoo", "Odoo Process"),
    ], required=True, default="member", readonly=True, index=True)
    member_consent_authority = fields.Char(
        default="member", required=True, readonly=True
    )
    safety_and_landing_authority = fields.Char(
        default="total_field_verifier", required=True, readonly=True
    )
    process_authority = fields.Char(
        default="odoo", required=True, readonly=True
    )
    candidate_authority = fields.Char(
        default="none", required=True, readonly=True
    )
    identity_root_ref = fields.Char(readonly=True, index=True)
    root_packet_ref = fields.Char(readonly=True, index=True)
    root_generation = fields.Integer(readonly=True, index=True)
    revocation_epoch = fields.Integer(readonly=True, index=True)
    action_hash = fields.Char(readonly=True, index=True)
    purpose_ref = fields.Char(readonly=True)
    scope_refs_json = fields.Text(readonly=True, default="[]")
    effect_class = fields.Selection([
        (value, value) for value in sorted(SOVEREIGN_EFFECT_CLASSES)
    ], readonly=True)
    amount_currency_hash = fields.Char(readonly=True)
    member_proof_ref = fields.Char(readonly=True)
    p1_evidence_ref = fields.Char(readonly=True)
    supersedes_consent_ref = fields.Char(readonly=True, index=True)
    allowed_until = fields.Datetime()
    revoked_at = fields.Datetime(readonly=True)
    audit_hash = fields.Char(required=True, readonly=True, index=True)

    _sql_constraints = [
        (
            "event_ref_unique",
            "unique(event_ref)",
            "Consent ledger event references must be unique.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        if (
            self.env.context.get("_wuchang_ledger_append_token")
            is not _LEDGER_APPEND_TOKEN
        ):
            raise UserError(_("HOLD_APPEND_ONLY_LEDGER_CREATE_FORBIDDEN"))
        for vals in vals_list:
            if FORBIDDEN_LEDGER_VALUE_KEYS & set(vals):
                raise UserError(_("HOLD_PRIVATE_VALUE_FORBIDDEN"))
            for field_name, expected in SOVEREIGN_AUTHORITY_MODEL.items():
                vals.setdefault(field_name, expected)
                if vals[field_name] != expected:
                    raise UserError(_("HOLD_AUTHORITY_MODEL_MISMATCH"))
            _assert_hash_ref(vals.get("event_ref"), "event_ref")
            _assert_sha256(vals.get("audit_hash"), "audit_hash")
            registration = self.env["wuchang.member.registration"].browse(
                vals.get("registration_id") or vals.get("registration_ref_id")
            ).exists()
            if not registration:
                raise UserError(_("HOLD_NOT_EVIDENCED"))
            vals["registration_id"] = registration.id
            vals["registration_ref_id"] = registration.id
            vals["member_user_id"] = registration.create_uid.id
            if vals.get("decision_authority") == "member":
                if self.env.su or registration.create_uid != self.env.user:
                    raise UserError(_("HOLD_FORGED_MEMBER_CONSENT"))
                for field_name in (
                    "identity_root_ref",
                    "root_packet_ref",
                    "purpose_ref",
                    "member_proof_ref",
                    "p1_evidence_ref",
                ):
                    _assert_hash_ref(vals.get(field_name), field_name)
                _assert_sha256(vals.get("action_hash"), "action_hash")
                if vals.get("effect_class") not in SOVEREIGN_EFFECT_CLASSES:
                    raise UserError(_("HOLD_EFFECT_CLASS_INVALID"))
                try:
                    scope_refs = json.loads(vals.get("scope_refs_json") or "")
                except (TypeError, ValueError):
                    raise UserError(_("HOLD_SCOPE_REFS_NOT_CANONICAL"))
                if _normalize_scope_refs(scope_refs) != scope_refs:
                    raise UserError(_("HOLD_SCOPE_REFS_NOT_CANONICAL"))
        return super().create(vals_list)

    def write(self, vals):
        raise UserError(_("HOLD_APPEND_ONLY_LEDGER_OVERWRITE"))

    def unlink(self):
        raise UserError(_("HOLD_APPEND_ONLY_LEDGER_DELETE"))

    @api.model
    def make_audit_hash(self, member_ref, consent_version, purpose):
        seed = f"{member_ref}:{consent_version}:{purpose}:{fields.Datetime.now()}"
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()

    def action_revoke(self):
        for rec in self:
            if rec.decision_authority != "member":
                raise UserError(_("HOLD_FORGED_MEMBER_CONSENT"))
            registration = rec.registration_id
            registration._assert_member_subject_authority()
            registration.append_member_consent_candidate(
                action_hash=rec.action_hash,
                purpose_ref=rec.purpose_ref,
                scope_refs=json.loads(rec.scope_refs_json or "[]"),
                effect_class=rec.effect_class,
                member_proof_ref=rec.member_proof_ref,
                p1_evidence_ref=rec.p1_evidence_ref,
                decision="WITHDRAW",
                supersedes_consent_ref=rec.event_ref,
                amount_currency_hash=rec.amount_currency_hash or None,
            )
            registration.append_revocation_candidate(
                target_type="CONSENT_LEASE",
                target_ref=rec.event_ref,
                expected_epoch=registration.sovereign_revocation_epoch,
                reason_code="MEMBER_CONSENT_WITHDRAWAL",
                member_proof_ref=rec.member_proof_ref,
                p1_evidence_ref=rec.p1_evidence_ref,
            )
        return True


class WuchangMemberSovereignRootLedger(models.Model):
    _name = "wuchang.member.sovereign.root.ledger"
    _description = "Wuchang Append-Only Sovereign Root Lineage Ledger"
    _order = "root_generation desc, id desc"

    event_ref = fields.Char(required=True, readonly=True, index=True, copy=False)
    registration_id = fields.Many2one(
        "wuchang.member.registration",
        required=True,
        readonly=True,
        index=True,
        ondelete="restrict",
    )
    member_user_id = fields.Many2one(
        "res.users", required=True, readonly=True, index=True, ondelete="restrict"
    )
    registration_ref = fields.Char(required=True, readonly=True, index=True)
    member_user_ref = fields.Char(required=True, readonly=True)
    identity_root_ref = fields.Char(required=True, readonly=True, index=True)
    root_packet_ref = fields.Char(required=True, readonly=True, index=True)
    previous_root_packet_ref = fields.Char(readonly=True, index=True)
    root_generation = fields.Integer(required=True, readonly=True, index=True)
    rotation_epoch = fields.Integer(required=True, readonly=True)
    revocation_epoch = fields.Integer(required=True, readonly=True, index=True)
    member_display_hash = fields.Char(required=True, readonly=True)
    terms_version = fields.Char(required=True, readonly=True)
    member_proof_ref = fields.Char(required=True, readonly=True)
    p1_evidence_ref = fields.Char(required=True, readonly=True)
    source_payload_sha256 = fields.Char(required=True, readonly=True)
    issued_at = fields.Datetime(required=True, readonly=True)
    member_consent_authority = fields.Char(
        default="member", required=True, readonly=True
    )
    safety_and_landing_authority = fields.Char(
        default="total_field_verifier", required=True, readonly=True
    )
    process_authority = fields.Char(
        default="odoo", required=True, readonly=True
    )
    candidate_authority = fields.Char(
        default="none", required=True, readonly=True
    )
    ledger_hash = fields.Char(required=True, readonly=True, index=True)

    _sql_constraints = [
        (
            "event_ref_unique",
            "unique(event_ref)",
            "Root ledger event references must be unique.",
        ),
        (
            "root_packet_ref_unique",
            "unique(root_packet_ref)",
            "Root packet references must be unique.",
        ),
        (
            "member_root_generation_unique",
            "unique(registration_id, root_generation)",
            "A member can have only one root record per generation.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        if (
            self.env.context.get("_wuchang_ledger_append_token")
            is not _LEDGER_APPEND_TOKEN
        ):
            raise UserError(_("HOLD_APPEND_ONLY_LEDGER_CREATE_FORBIDDEN"))
        for vals in vals_list:
            if FORBIDDEN_LEDGER_VALUE_KEYS & set(vals):
                raise UserError(_("HOLD_PRIVATE_VALUE_FORBIDDEN"))
            registration = self.env["wuchang.member.registration"].browse(
                vals.get("registration_id")
            ).exists()
            if (
                not registration
                or self.env.su
                or registration.create_uid != self.env.user
            ):
                raise UserError(_("HOLD_CROSS_MEMBER_AUTHORITY"))
            vals["member_user_id"] = registration.create_uid.id
            for field_name, expected in SOVEREIGN_AUTHORITY_MODEL.items():
                if vals.get(field_name) != expected:
                    raise UserError(_("HOLD_AUTHORITY_MODEL_MISMATCH"))
            if vals.get("root_generation") != (
                registration.sovereign_root_generation + 1
            ):
                raise UserError(_("HOLD_ROOT_GENERATION_STALE"))
            if (
                registration.sovereign_root_generation
                and vals.get("previous_root_packet_ref")
                != registration.sovereign_root_packet_ref
            ):
                raise UserError(_("HOLD_ROOT_LINEAGE_MISMATCH"))
            for field_name in (
                "event_ref",
                "member_user_ref",
                "identity_root_ref",
                "root_packet_ref",
                "member_proof_ref",
                "p1_evidence_ref",
            ):
                _assert_hash_ref(vals.get(field_name), field_name)
            if vals.get("previous_root_packet_ref"):
                _assert_hash_ref(
                    vals["previous_root_packet_ref"],
                    "previous_root_packet_ref",
                )
            for field_name in (
                "member_display_hash",
                "source_payload_sha256",
                "ledger_hash",
            ):
                _assert_sha256(vals.get(field_name), field_name)
        return super().create(vals_list)

    def write(self, vals):
        raise UserError(_("HOLD_APPEND_ONLY_LEDGER_OVERWRITE"))

    def unlink(self):
        raise UserError(_("HOLD_APPEND_ONLY_LEDGER_DELETE"))


class WuchangMemberSovereignRevocationLedger(models.Model):
    _name = "wuchang.member.sovereign.revocation.ledger"
    _description = "Wuchang Append-Only Sovereign Revocation Ledger"
    _order = "new_revocation_epoch desc, id desc"

    event_ref = fields.Char(required=True, readonly=True, index=True, copy=False)
    registration_id = fields.Many2one(
        "wuchang.member.registration",
        required=True,
        readonly=True,
        index=True,
        ondelete="restrict",
    )
    member_user_id = fields.Many2one(
        "res.users", required=True, readonly=True, index=True, ondelete="restrict"
    )
    identity_root_ref = fields.Char(required=True, readonly=True, index=True)
    root_packet_ref = fields.Char(required=True, readonly=True, index=True)
    root_generation = fields.Integer(required=True, readonly=True)
    previous_revocation_epoch = fields.Integer(required=True, readonly=True)
    new_revocation_epoch = fields.Integer(required=True, readonly=True, index=True)
    target_type = fields.Selection([
        ("ROOT", "Root"),
        ("SESSION", "Session"),
        ("SCENE", "Scene"),
        ("CONSENT_LEASE", "Consent Lease"),
    ], required=True, readonly=True)
    target_ref = fields.Char(required=True, readonly=True, index=True)
    reason_code = fields.Char(required=True, readonly=True)
    member_proof_ref = fields.Char(required=True, readonly=True)
    p1_evidence_ref = fields.Char(required=True, readonly=True)
    member_consent_authority = fields.Char(
        default="member", required=True, readonly=True
    )
    safety_and_landing_authority = fields.Char(
        default="total_field_verifier", required=True, readonly=True
    )
    process_authority = fields.Char(
        default="odoo", required=True, readonly=True
    )
    candidate_authority = fields.Char(
        default="none", required=True, readonly=True
    )
    payload_sha256 = fields.Char(required=True, readonly=True, index=True)

    _sql_constraints = [
        (
            "event_ref_unique",
            "unique(event_ref)",
            "Revocation event references must be unique.",
        ),
        (
            "member_revocation_epoch_unique",
            "unique(registration_id, new_revocation_epoch)",
            "A member can have only one revocation event per epoch.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        if (
            self.env.context.get("_wuchang_ledger_append_token")
            is not _LEDGER_APPEND_TOKEN
        ):
            raise UserError(_("HOLD_APPEND_ONLY_LEDGER_CREATE_FORBIDDEN"))
        for vals in vals_list:
            if FORBIDDEN_LEDGER_VALUE_KEYS & set(vals):
                raise UserError(_("HOLD_PRIVATE_VALUE_FORBIDDEN"))
            registration = self.env["wuchang.member.registration"].browse(
                vals.get("registration_id")
            ).exists()
            if (
                not registration
                or self.env.su
                or registration.create_uid != self.env.user
            ):
                raise UserError(_("HOLD_CROSS_MEMBER_AUTHORITY"))
            vals["member_user_id"] = registration.create_uid.id
            for field_name, expected in SOVEREIGN_AUTHORITY_MODEL.items():
                if vals.get(field_name) != expected:
                    raise UserError(_("HOLD_AUTHORITY_MODEL_MISMATCH"))
            if vals.get("new_revocation_epoch") != (
                vals.get("previous_revocation_epoch", -1) + 1
            ):
                raise UserError(_("HOLD_REVOCATION_EPOCH_STALE"))
            if (
                vals.get("previous_revocation_epoch")
                != registration.sovereign_revocation_epoch
            ):
                raise UserError(_("HOLD_REVOCATION_EPOCH_STALE"))
            for field_name in (
                "event_ref",
                "identity_root_ref",
                "root_packet_ref",
                "target_ref",
                "member_proof_ref",
                "p1_evidence_ref",
            ):
                _assert_hash_ref(vals.get(field_name), field_name)
            _assert_sha256(vals.get("payload_sha256"), "payload_sha256")
        return super().create(vals_list)

    def write(self, vals):
        raise UserError(_("HOLD_APPEND_ONLY_LEDGER_OVERWRITE"))

    def unlink(self):
        raise UserError(_("HOLD_APPEND_ONLY_LEDGER_DELETE"))


class WuchangMemberSovereignRecoveryLedger(models.Model):
    _name = "wuchang.member.sovereign.recovery.ledger"
    _description = "Wuchang Append-Only Sovereign Recovery Ledger"
    _order = "create_date desc, id desc"

    event_ref = fields.Char(required=True, readonly=True, index=True, copy=False)
    event_type = fields.Selection([
        ("REQUESTED_CANDIDATE", "Requested Candidate"),
        ("COMPLETED_CANDIDATE", "Completed Candidate"),
    ], required=True, readonly=True, index=True)
    registration_id = fields.Many2one(
        "wuchang.member.registration",
        required=True,
        readonly=True,
        index=True,
        ondelete="restrict",
    )
    member_user_id = fields.Many2one(
        "res.users", required=True, readonly=True, index=True, ondelete="restrict"
    )
    identity_root_ref = fields.Char(required=True, readonly=True)
    root_packet_ref = fields.Char(required=True, readonly=True)
    expected_generation = fields.Integer(required=True, readonly=True)
    expected_epoch = fields.Integer(required=True, readonly=True)
    new_identity_root_ref = fields.Char(required=True, readonly=True)
    new_root_packet_ref = fields.Char(required=True, readonly=True)
    new_member_display_hash = fields.Char(required=True, readonly=True)
    new_root_payload_sha256 = fields.Char(required=True, readonly=True)
    recovery_cas_ref = fields.Char(required=True, readonly=True, index=True)
    requested_completion_ref = fields.Char(required=True, readonly=True, index=True)
    completion_guard_key = fields.Char(readonly=True, index=True, copy=False)
    previous_event_ref = fields.Char(readonly=True)
    member_proof_ref = fields.Char(required=True, readonly=True)
    p1_evidence_ref = fields.Char(required=True, readonly=True)
    session_refs_json = fields.Text(readonly=True, default="[]")
    scene_refs_json = fields.Text(readonly=True, default="[]")
    consent_lease_refs_json = fields.Text(readonly=True, default="[]")
    cooldown_until = fields.Datetime(required=True, readonly=True, index=True)
    member_consent_authority = fields.Char(
        default="member", required=True, readonly=True
    )
    safety_and_landing_authority = fields.Char(
        default="total_field_verifier", required=True, readonly=True
    )
    process_authority = fields.Char(
        default="odoo", required=True, readonly=True
    )
    candidate_authority = fields.Char(
        default="none", required=True, readonly=True
    )
    payload_sha256 = fields.Char(required=True, readonly=True, index=True)

    _sql_constraints = [
        (
            "event_ref_unique",
            "unique(event_ref)",
            "Recovery event references must be unique.",
        ),
        (
            "recovery_cas_event_unique",
            "unique(recovery_cas_ref, event_type)",
            "A recovery CAS reference can be used once per event type.",
        ),
        (
            "completion_guard_unique",
            "unique(completion_guard_key)",
            "A recovery completion can succeed only once.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        if (
            self.env.context.get("_wuchang_ledger_append_token")
            is not _LEDGER_APPEND_TOKEN
        ):
            raise UserError(_("HOLD_APPEND_ONLY_LEDGER_CREATE_FORBIDDEN"))
        for vals in vals_list:
            if FORBIDDEN_LEDGER_VALUE_KEYS & set(vals):
                raise UserError(_("HOLD_PRIVATE_VALUE_FORBIDDEN"))
            registration = self.env["wuchang.member.registration"].browse(
                vals.get("registration_id")
            ).exists()
            if (
                not registration
                or self.env.su
                or registration.create_uid != self.env.user
            ):
                raise UserError(_("HOLD_CROSS_MEMBER_AUTHORITY"))
            vals["member_user_id"] = registration.create_uid.id
            for field_name, expected in SOVEREIGN_AUTHORITY_MODEL.items():
                if vals.get(field_name) != expected:
                    raise UserError(_("HOLD_AUTHORITY_MODEL_MISMATCH"))
            if (
                vals.get("expected_generation")
                != registration.sovereign_root_generation
                or vals.get("expected_epoch")
                != registration.sovereign_revocation_epoch
            ):
                raise UserError(_("HOLD_RECOVERY_STALE_CAS"))
            for field_name in (
                "event_ref",
                "identity_root_ref",
                "root_packet_ref",
                "new_identity_root_ref",
                "new_root_packet_ref",
                "recovery_cas_ref",
                "requested_completion_ref",
                "member_proof_ref",
                "p1_evidence_ref",
            ):
                _assert_hash_ref(vals.get(field_name), field_name)
            if vals.get("previous_event_ref"):
                _assert_hash_ref(vals["previous_event_ref"], "previous_event_ref")
            if vals.get("completion_guard_key"):
                _assert_hash_ref(
                    vals["completion_guard_key"], "completion_guard_key"
                )
            for field_name in (
                "new_member_display_hash",
                "new_root_payload_sha256",
                "payload_sha256",
            ):
                _assert_sha256(vals.get(field_name), field_name)
            if (
                vals.get("event_type") == "COMPLETED_CANDIDATE"
                and vals.get("completion_guard_key")
                != vals.get("requested_completion_ref")
            ):
                raise UserError(_("HOLD_RECOVERY_COMPLETION_GUARD_MISMATCH"))
        return super().create(vals_list)

    def write(self, vals):
        raise UserError(_("HOLD_APPEND_ONLY_LEDGER_OVERWRITE"))

    def unlink(self):
        raise UserError(_("HOLD_APPEND_ONLY_LEDGER_DELETE"))


class WuchangMemberSovereignInvalidationCandidate(models.Model):
    _name = "wuchang.member.sovereign.invalidation.candidate"
    _description = "Wuchang Append-Only Sovereign Invalidation Candidate"
    _order = "create_date desc, id desc"

    event_ref = fields.Char(required=True, readonly=True, index=True, copy=False)
    registration_id = fields.Many2one(
        "wuchang.member.registration",
        required=True,
        readonly=True,
        index=True,
        ondelete="restrict",
    )
    member_user_id = fields.Many2one(
        "res.users", required=True, readonly=True, index=True, ondelete="restrict"
    )
    target_type = fields.Selection([
        ("ROOT", "Root"),
        ("SESSION", "Session"),
        ("SCENE", "Scene"),
        ("CONSENT_LEASE", "Consent Lease"),
    ], required=True, readonly=True)
    target_ref = fields.Char(required=True, readonly=True, index=True)
    reason_code = fields.Char(required=True, readonly=True)
    root_generation = fields.Integer(required=True, readonly=True)
    revocation_epoch = fields.Integer(required=True, readonly=True)
    p1_evidence_ref = fields.Char(required=True, readonly=True)
    member_consent_authority = fields.Char(
        default="member", required=True, readonly=True
    )
    safety_and_landing_authority = fields.Char(
        default="total_field_verifier", required=True, readonly=True
    )
    process_authority = fields.Char(
        default="odoo", required=True, readonly=True
    )
    candidate_authority = fields.Char(
        default="none", required=True, readonly=True
    )
    payload_sha256 = fields.Char(required=True, readonly=True, index=True)
    runtime_propagated = fields.Boolean(default=False, required=True, readonly=True)

    _sql_constraints = [
        (
            "event_ref_unique",
            "unique(event_ref)",
            "Invalidation candidate references must be unique.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        if (
            self.env.context.get("_wuchang_ledger_append_token")
            is not _LEDGER_APPEND_TOKEN
        ):
            raise UserError(_("HOLD_APPEND_ONLY_LEDGER_CREATE_FORBIDDEN"))
        for vals in vals_list:
            if FORBIDDEN_LEDGER_VALUE_KEYS & set(vals):
                raise UserError(_("HOLD_PRIVATE_VALUE_FORBIDDEN"))
            registration = self.env["wuchang.member.registration"].browse(
                vals.get("registration_id")
            ).exists()
            if (
                not registration
                or self.env.su
                or registration.create_uid != self.env.user
            ):
                raise UserError(_("HOLD_CROSS_MEMBER_AUTHORITY"))
            if vals.get("runtime_propagated") is not False:
                raise UserError(_("HOLD_RUNTIME_PROPAGATION_FORBIDDEN"))
            vals["member_user_id"] = registration.create_uid.id
            for field_name, expected in SOVEREIGN_AUTHORITY_MODEL.items():
                if vals.get(field_name) != expected:
                    raise UserError(_("HOLD_AUTHORITY_MODEL_MISMATCH"))
            for field_name in ("event_ref", "target_ref", "p1_evidence_ref"):
                _assert_hash_ref(vals.get(field_name), field_name)
            _assert_sha256(vals.get("payload_sha256"), "payload_sha256")
        return super().create(vals_list)

    def write(self, vals):
        raise UserError(_("HOLD_APPEND_ONLY_LEDGER_OVERWRITE"))

    def unlink(self):
        raise UserError(_("HOLD_APPEND_ONLY_LEDGER_DELETE"))


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
    def is_landing_enabled(self, surface):
        if surface not in LANDING_CONTROL_SURFACES:
            return False
        return self.is_enabled(f"landing.{surface}", default=False)

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
            "receipt_ref": (
                f"feature_gate_receipt:sha256:{self.audit_hash}"
                if self.audit_hash else ""
            ),
            "decided_by_ref": (
                f"odoo_user_ref:{self.decided_by_id.id}"
                if self.decided_by_id else ""
            ),
            "decided_at": (
                fields.Datetime.to_string(self.decided_at)
                if self.decided_at else ""
            ),
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

    business_onboarding_enabled = fields.Boolean(default=False, index=True)
    business_onboarding_state = fields.Selection([
        ("not_business", "Not Business Onboarding"),
        ("draft", "Draft"),
        ("pending_total_field", "Pending Total Field Review"),
        ("operational_ready", "Operational Entry Ready"),
        ("hold", "Hold"),
        ("rejected", "Rejected"),
    ], default="not_business", index=True)
    responsible_registration_id = fields.Many2one("wuchang.member.registration", ondelete="set null")
    responsible_person_ref = fields.Char(index=True)
    responsible_role = fields.Selection([
        ("responsible_person", "Responsible Person"),
        ("authorized_manager", "Authorized Manager"),
    ], default="responsible_person")
    business_name = fields.Char()
    business_ref = fields.Char(index=True)
    business_address_ref = fields.Char()
    business_registration_ref = fields.Char(
        help="Reference only; this does not claim legal business registration is complete."
    )
    store_name = fields.Char()
    store_ref = fields.Char(index=True)
    service_area_ref = fields.Char()
    service_items_json = fields.Text(default='["cafe_menu", "member_service", "line_ai_response", "odoo_pos_management"]')
    line_official_account_ref = fields.Char()
    odoo_service_ref = fields.Char()
    pos_config_ref = fields.Char()
    total_field_review_ref = fields.Char(readonly=True, index=True)
    merchant_state_packet_json = fields.Text(readonly=True)
    tenant_ref = fields.Char(readonly=True, index=True)
    service_profile_ref = fields.Char(readonly=True, index=True)
    container_config_ref = fields.Char(readonly=True, index=True)
    url_routing_ref = fields.Char(readonly=True, index=True)
    public_page_path = fields.Char(readonly=True)
    member_entry_path = fields.Char(readonly=True)
    line_ai_entry_ref = fields.Char(readonly=True)
    odoo_pos_management_entry_ref = fields.Char(readonly=True)
    ordering_or_service_entry_path = fields.Char(readonly=True)

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

    def _business_required_errors(self):
        self.ensure_one()
        errors = []
        for name, value in [
            ("responsible_person_ref", self.responsible_person_ref),
            ("business_name", self.business_name),
            ("business_ref", self.business_ref),
            ("business_address_ref", self.business_address_ref),
            ("store_name", self.store_name),
            ("store_ref", self.store_ref),
            ("service_area_ref", self.service_area_ref),
            ("line_official_account_ref", self.line_official_account_ref),
            ("odoo_service_ref", self.odoo_service_ref),
            ("pos_config_ref", self.pos_config_ref),
        ]:
            if not value:
                errors.append(name)
        self._business_service_items()
        return errors

    def _business_service_items(self):
        self.ensure_one()
        try:
            items = json.loads(self.service_items_json or "[]")
        except json.JSONDecodeError as exc:
            raise UserError(_("Service items JSON is invalid: %s") % exc) from exc
        if not isinstance(items, list) or not items:
            raise UserError(_("At least one business service item is required."))
        return items

    def _business_hash_ref(self, payload):
        return "hash:" + self._packet_hash(payload)

    def _business_slug(self):
        self.ensure_one()
        seed = self.business_name or self.name or self.group_ref
        slug = "".join(ch if ch.isascii() and ch.isalnum() else "-" for ch in seed.lower()).strip("-")
        return slug[:48] or ("merchant-" + self._packet_hash(self.group_ref)[:12])

    def _build_business_8d_7d_packet(self):
        self.ensure_one()
        service_items = self._business_service_items()
        return {
            "packet_type": "CAFE_BUSINESS_8D_7D_MERCHANT_STATE_PACKET",
            "state_subject": "MERCHANT_ORGANIZATION",
            "natural_person_role": self.responsible_role,
            "natural_person_ref": self.responsible_person_ref,
            "group_ref": self.group_ref,
            "organization_name": self.name,
            "business_info_ref": self._business_hash_ref({
                "business_name": self.business_name,
                "business_ref": self.business_ref,
                "business_address_ref": self.business_address_ref,
                "business_registration_ref": self.business_registration_ref or "",
            }),
            "store_info_ref": self._business_hash_ref({
                "store_name": self.store_name,
                "store_ref": self.store_ref,
                "service_area_ref": self.service_area_ref,
            }),
            "service_items_ref": self._business_hash_ref(service_items),
            "functional_state_7d": {
                "layer": "7D_FUNCTIONAL_STATE_LAYER",
                "functional_state_type": "CAFE_BUSINESS_ONBOARDING",
                "state_generation_mode": "MERCHANT_SERVICE_PROFILE_GENERATION",
            },
            "adi_5d_positioning": {
                "positioning_type": "ADI_5D_ABSOLUTE_INDEX",
                "absolute_index_ref": "adi_absolute_index_ref:" + self._packet_hash(self.group_ref)[:24],
                "actual_index_rules_disclosed": False,
                "h64_td_ref_only": True,
            },
            "authority_envelope_8d": {
                "authority": "LOCAL_TOTAL_FIELD",
                "review_ref": self.total_field_review_ref,
                "final_authority": True,
            },
            "legal_boundary": {
                "legal_business_registration_completed": False,
                "food_license_completed": False,
                "tax_registration_completed": False,
                "payment_contract_completed": False,
            },
        }

    def _build_business_service_config(self):
        self.ensure_one()
        slug = self._business_slug()
        tenant_ref = "tenant:" + self._packet_hash(self.group_ref)[:24]
        return {
            "tenant_ref": tenant_ref,
            "service_profile_ref": "service_profile:" + self._packet_hash(self.business_ref)[:24],
            "container_config_ref": "container_config:" + self._packet_hash(f"{self.group_ref}:{self.pos_config_ref}")[:24],
            "url_routing_ref": "url_routing:" + self._packet_hash(f"{self.group_ref}:{slug}")[:24],
            "public_page_path": f"/merchant/{slug}",
            "member_entry_path": f"/merchant/{slug}/member",
            "line_ai_entry_ref": self.line_official_account_ref,
            "odoo_pos_management_entry_ref": self.odoo_service_ref,
            "ordering_or_service_entry_path": f"/merchant/{slug}/service",
            "natural_person_container": False,
            "container_is_business_qualification": False,
        }

    def action_submit_business_onboarding(self):
        for rec in self:
            if not rec.business_onboarding_enabled:
                raise UserError(_("This batch is not a business onboarding record."))
            errors = rec._business_required_errors()
            if errors:
                raise UserError(_("Business onboarding is incomplete: %s") % ", ".join(errors))
            review_ref = rec.total_field_review_ref or rec._new_ref("TFREVIEW")
            rec.write({
                "state": "pending_review",
                "business_onboarding_state": "pending_total_field",
                "total_field_review_ref": review_ref,
            })

    def action_total_field_approve_business_onboarding(self):
        for rec in self:
            if rec.business_onboarding_state != "pending_total_field":
                raise UserError(_("Only pending Total Field business onboarding can be approved."))
            packet = rec._build_business_8d_7d_packet()
            config = rec._build_business_service_config()
            rec.write({
                "state": "approved",
                "business_onboarding_state": "operational_ready",
                "merchant_state_packet_json": json.dumps(packet, ensure_ascii=False, sort_keys=True, indent=2),
                "tenant_ref": config["tenant_ref"],
                "service_profile_ref": config["service_profile_ref"],
                "container_config_ref": config["container_config_ref"],
                "url_routing_ref": config["url_routing_ref"],
                "public_page_path": config["public_page_path"],
                "member_entry_path": config["member_entry_path"],
                "line_ai_entry_ref": config["line_ai_entry_ref"],
                "odoo_pos_management_entry_ref": config["odoo_pos_management_entry_ref"],
                "ordering_or_service_entry_path": config["ordering_or_service_entry_path"],
            })

    def business_onboarding_status_payload(self):
        self.ensure_one()
        return {
            "status": "found",
            "packet_ref": self.packet_ref,
            "group_ref": self.group_ref,
            "state": self.business_onboarding_state,
            "responsible_person_ref": self.responsible_person_ref,
            "organization_name": self.name,
            "tenant_ref": self.tenant_ref or "",
            "service_profile_ref": self.service_profile_ref or "",
            "container_config_ref": self.container_config_ref or "",
            "url_routing_ref": self.url_routing_ref or "",
            "public_page_path": self.public_page_path or "",
            "member_entry_path": self.member_entry_path or "",
            "line_ai_entry_ref": self.line_ai_entry_ref or "",
            "odoo_pos_management_entry_ref": self.odoo_pos_management_entry_ref or "",
            "ordering_or_service_entry_path": self.ordering_or_service_entry_path or "",
            "natural_person_container": False,
            "container_is_business_qualification": False,
            "legal_business_registration_completed": False,
            "food_license_completed": False,
            "tax_registration_completed": False,
            "payment_contract_completed": False,
            "payment_capture": False,
            "formal_order": False,
            "deploy": False,
            "restart": False,
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

        auth_provider = provider if provider in ("google", "line") else "odoo"
        external_auth = self.env["wuchang.member.external.auth"].sudo()
        existing_binding = external_auth.search([
            ("provider", "=", auth_provider),
            ("provider_subject_hash", "=", provider_hash),
        ], limit=1)
        if existing_binding and existing_binding.binding_status == "revoked":
            raise UserError(_(
                "Existing login binding is revoked. Use account recovery; "
                "the system will not create a duplicate record."
            ))
        if existing_binding:
            registration = (
                self.env["wuchang.member.registration"]
                .sudo()
                .browse(existing_binding.registration_ref_id)
                .exists()
            )
            if not registration:
                raise UserError(_(
                    "Existing login binding was found, but its member reference "
                    "requires account recovery. The system will not create a "
                    "duplicate record."
                ))
        else:
            registration = self.env["wuchang.member.registration"].sudo().create({
                "registration_channel": auth_provider,
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
        if not existing_binding:
            external_auth.create({
                "registration_ref_id": registration.id,
                "provisional_member_ref": registration.provisional_member_id,
                "provider": auth_provider,
                "provider_subject_hash": provider_hash,
                "binding_status": "pending",
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
