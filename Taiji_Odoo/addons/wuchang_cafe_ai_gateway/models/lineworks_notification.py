import hashlib
import json
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..services.lineworks_activation import build_lineworks_runtime_activation_packet
from ..services.lineworks_connector import (
    build_lineworks_execution_envelope_export,
    build_lineworks_send_preflight,
    execute_lineworks_send_envelope,
    is_safe_connector_ref,
)
from ..services.lineworks_handoff import build_lineworks_operator_handoff_pack
from ..services.lineworks_release_refs import build_lineworks_release_refs_draft
from ..services.lineworks_runtime_resolver import build_lineworks_runtime_resolver_contract
from ..services.p1_intent_engine import formal_release_status_payload, lineworks_notify_payload


class WuchangLineworksNotificationCandidate(models.Model):
    _name = "wuchang.lineworks.notification.candidate"
    _description = "WuChang LINE WORKS Notification Candidate"
    _order = "create_date desc, id desc"

    name = fields.Char(default="LINEWORKS-CANDIDATE", required=True, index=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("candidate_ready", "Candidate Ready"),
            ("preflight_hold", "Preflight Hold"),
            ("preflight_ready", "Preflight Ready"),
            ("envelope_hold", "Envelope Hold"),
            ("envelope_ready", "Envelope Ready"),
            ("runtime_dry_run_hold", "Runtime Dry-Run Hold"),
            ("runtime_dry_run_ready", "Runtime Dry-Run Ready"),
            ("dead_letter", "Dead Letter"),
        ],
        default="draft",
        index=True,
        readonly=True,
    )
    channel = fields.Selection(
        [
            ("member_service", "Member Service"),
            ("staff_notice", "Staff Notice"),
            ("community_notice", "Community Notice"),
        ],
        default="member_service",
        required=True,
    )
    message_preview = fields.Text(required=True)
    message_hash = fields.Char(readonly=True, index=True)
    target_ref_hash = fields.Char(
        string="Target Ref Hash",
        help="Hash or masked reference only. Do not store a raw LINE WORKS user id or member plaintext here.",
        required=True,
        index=True,
    )
    actor_ref_hash = fields.Char(
        string="Actor Ref Hash",
        help="Optional staff/operator ref hash. Do not store member plaintext.",
        index=True,
    )
    lineworks_bot_ref = fields.Char(help="Reference only. Do not paste bot secret or token.")
    lineworks_target_user_ref = fields.Char(help="Reference only. Do not paste raw member plaintext.")
    lineworks_access_token_runtime_ref = fields.Char(help="Runtime token provider reference only. Never paste token values.")
    release_refs_json = fields.Text(
        help="Verified release refs JSON for lineworks_send gate. Do not paste tokens, private keys, or secrets."
    )
    runtime_resolver_bindings_json = fields.Text(
        help="Resolver binding metadata only. Do not paste bot IDs, user IDs, tokens, or member plaintext."
    )
    candidate_payload_json = fields.Text(readonly=True)
    preflight_payload_json = fields.Text(readonly=True)
    execution_envelope_json = fields.Text(readonly=True)
    runtime_dry_run_json = fields.Text(readonly=True)
    runtime_activation_packet_json = fields.Text(readonly=True)
    operator_handoff_pack_json = fields.Text(readonly=True)
    runtime_resolver_contract_json = fields.Text(readonly=True)
    release_refs_draft_warnings = fields.Text(readonly=True)
    runtime_resolver_warnings = fields.Text(readonly=True)
    failure_reasons = fields.Text(readonly=True)
    release_refs_draft_hash = fields.Char(readonly=True, index=True)
    candidate_packet_hash = fields.Char(readonly=True, index=True)
    preflight_envelope_hash = fields.Char(readonly=True, index=True)
    execution_envelope_hash = fields.Char(readonly=True, index=True)
    runtime_result_hash = fields.Char(readonly=True, index=True)
    operator_handoff_pack_hash = fields.Char(readonly=True, index=True)
    runtime_resolver_contract_hash = fields.Char(readonly=True, index=True)
    runtime_activation_packet_hash = fields.Char(
        help="64-hex human activation packet hash. Required only for runtime dry-run readiness."
    )
    runtime_operator_ref = fields.Char(help="Operator hash or uppercase opaque ref. Do not store personal plaintext.")

    formal_lineworks_send = fields.Boolean(default=False, readonly=True)
    external_api_call = fields.Boolean(default=False, readonly=True)
    secret_read = fields.Boolean(default=False, readonly=True)
    member_plaintext_read = fields.Boolean(default=False, readonly=True)

    def _stable_hash(self, value):
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _contains_secret_shape(self, value):
        text = str(value or "")
        return bool(
            re.search(r"sk-[A-Za-z0-9_-]{12,}", text)
            or re.search(r"(?i)(access|refresh|id)_token\s*[:=]\s*\S+", text)
            or re.search(r"(?i)client_secret\s*[:=]\s*\S+", text)
            or re.search(r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----", text)
            or re.search(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}", text)
            or re.search(r"[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}", text)
            or re.search(r"(?=.*[A-Za-z])(?=.*[0-9])[A-Za-z0-9_~+/=-]{40,}", text)
        )

    def _safe_identity_ref(self, value, *, required=False):
        text = str(value or "").strip()
        if not text:
            return not required
        return bool(re.fullmatch(r"[a-f0-9]{64}", text) or is_safe_connector_ref(text))

    def _assert_no_secret_material(self):
        for rec in self:
            values = [
                rec.message_preview,
                rec.target_ref_hash,
                rec.actor_ref_hash,
                rec.lineworks_bot_ref,
                rec.lineworks_target_user_ref,
                rec.lineworks_access_token_runtime_ref,
                rec.runtime_activation_packet_hash,
                rec.runtime_operator_ref,
                rec.release_refs_json,
                rec.runtime_resolver_bindings_json,
            ]
            if any(rec._contains_secret_shape(value) for value in values):
                raise UserError(_("Secret-shaped material is not allowed in LINE WORKS candidate records. Use refs only."))
            if not rec._safe_identity_ref(rec.target_ref_hash, required=True):
                raise UserError(_("Target ref must be a 64-hex hash or an uppercase opaque ref containing REF."))
            if rec.actor_ref_hash and not rec._safe_identity_ref(rec.actor_ref_hash):
                raise UserError(_("Actor ref must be a 64-hex hash or an uppercase opaque ref containing REF."))
            activation_hash = str(rec.runtime_activation_packet_hash or "").strip().lower()
            if activation_hash and not re.fullmatch(r"[a-f0-9]{64}", activation_hash):
                raise UserError(_("Runtime activation packet hash must be 64 lowercase hex characters."))
            if rec.runtime_operator_ref and not rec._safe_identity_ref(rec.runtime_operator_ref):
                raise UserError(_("Runtime operator ref must be a 64-hex hash or an uppercase opaque ref containing REF."))
            connector_values = {
                "lineworks_bot_ref": rec.lineworks_bot_ref,
                "lineworks_target_user_ref": rec.lineworks_target_user_ref,
                "lineworks_access_token_runtime_ref": rec.lineworks_access_token_runtime_ref,
            }
            unsafe_connector_keys = [
                key for key, value in connector_values.items() if value and not is_safe_connector_ref(value)
            ]
            if unsafe_connector_keys:
                raise UserError(
                    _("Connector refs must be uppercase opaque refs and must not contain raw ids or tokens: %s")
                    % ", ".join(unsafe_connector_keys)
                )

    @api.constrains(
        "message_preview",
        "target_ref_hash",
        "actor_ref_hash",
        "lineworks_bot_ref",
        "lineworks_target_user_ref",
        "lineworks_access_token_runtime_ref",
        "runtime_activation_packet_hash",
        "runtime_operator_ref",
        "release_refs_json",
        "runtime_resolver_bindings_json",
    )
    def _check_red_team_boundaries(self):
        self._assert_no_secret_material()

    def _json_loads_dict(self, value):
        if not value:
            return {}
        try:
            data = json.loads(value)
        except json.JSONDecodeError as exc:
            raise UserError(_("Invalid JSON: %s") % exc) from exc
        if not isinstance(data, dict):
            raise UserError(_("JSON value must be an object."))
        return data

    def _candidate_payload(self):
        self.ensure_one()
        candidate = self._json_loads_dict(self.candidate_payload_json)
        if candidate:
            return candidate
        return lineworks_notify_payload(
            self.message_preview,
            self.target_ref_hash,
            self.channel,
            self.actor_ref_hash or "",
        )

    def _release_status_payload(self):
        self.ensure_one()
        return formal_release_status_payload(self._json_loads_dict(self.release_refs_json))

    def _connector_refs(self):
        self.ensure_one()
        return {
            "lineworks_bot_ref": self.lineworks_bot_ref,
            "lineworks_target_user_ref": self.lineworks_target_user_ref,
            "lineworks_access_token_runtime_ref": self.lineworks_access_token_runtime_ref,
        }

    def action_build_release_refs_draft(self):
        for rec in self:
            rec._assert_no_secret_material()
            raw_refs = rec._json_loads_dict(rec.release_refs_json)
            release_refs = raw_refs.get("lineworks_send") if isinstance(raw_refs.get("lineworks_send"), dict) else raw_refs
            connector_refs = dict(raw_refs.get("connector_refs") if isinstance(raw_refs.get("connector_refs"), dict) else {})
            for key, value in rec._connector_refs().items():
                if value:
                    connector_refs[key] = value
            draft = build_lineworks_release_refs_draft(
                release_refs=release_refs,
                connector_refs=connector_refs,
                allow_verified=True,
            )
            rec.write(
                {
                    "release_refs_json": json.dumps(
                        {
                            "lineworks_send": draft.get("lineworks_send", {}),
                            "connector_refs": draft.get("connector_refs", {}),
                        },
                        ensure_ascii=False,
                        indent=2,
                        sort_keys=True,
                    ),
                    "release_refs_draft_hash": draft.get("draft_hash") or "",
                    "release_refs_draft_warnings": "\n".join(draft.get("draft_warnings", [])),
                    "failure_reasons": "\n".join(draft.get("draft_warnings", [])),
                    "formal_lineworks_send": False,
                    "external_api_call": False,
                    "secret_read": False,
                    "member_plaintext_read": False,
                }
            )

    def action_build_runtime_resolver_contract(self):
        for rec in self:
            rec._assert_no_secret_material()
            raw_bindings = rec._json_loads_dict(rec.runtime_resolver_bindings_json)
            resolver_bindings = (
                raw_bindings.get("runtime_resolver_bindings")
                if isinstance(raw_bindings.get("runtime_resolver_bindings"), dict)
                else raw_bindings
            )
            contract = build_lineworks_runtime_resolver_contract(
                connector_refs=rec._connector_refs(),
                resolver_bindings=resolver_bindings,
                allow_verified=True,
            )
            rec.write(
                {
                    "runtime_resolver_contract_json": json.dumps(contract, ensure_ascii=False, indent=2, sort_keys=True),
                    "runtime_resolver_contract_hash": contract.get("resolver_contract_hash") or "",
                    "runtime_resolver_warnings": "\n".join(contract.get("draft_warnings", [])),
                    "failure_reasons": "\n".join(contract.get("draft_warnings", [])),
                    "formal_lineworks_send": False,
                    "external_api_call": False,
                    "secret_read": False,
                    "member_plaintext_read": False,
                }
            )

    def action_build_candidate(self):
        for rec in self:
            rec._assert_no_secret_material()
            candidate = lineworks_notify_payload(
                rec.message_preview,
                rec.target_ref_hash,
                rec.channel,
                rec.actor_ref_hash or "",
            )
            lineworks_candidate = candidate.get("lineworks_notify_candidate", {})
            rec.write(
                {
                    "state": "candidate_ready",
                    "message_hash": lineworks_candidate.get("message_hash") or "",
                    "candidate_packet_hash": candidate.get("authority_packet", {}).get("packet_hash") or rec._stable_hash(candidate),
                    "candidate_payload_json": json.dumps(candidate, ensure_ascii=False, indent=2, sort_keys=True),
                    "execution_envelope_json": False,
                    "runtime_dry_run_json": False,
                    "runtime_activation_packet_json": False,
                    "formal_lineworks_send": False,
                    "external_api_call": False,
                    "secret_read": False,
                    "member_plaintext_read": False,
                    "failure_reasons": "\n".join(candidate.get("local_verifier", {}).get("failure_reasons", [])),
                }
            )

    def action_run_preflight(self):
        for rec in self:
            rec._assert_no_secret_material()
            preflight = build_lineworks_send_preflight(
                rec._candidate_payload(),
                rec._release_status_payload(),
                rec._connector_refs(),
            )
            rec.write(
                {
                    "state": "preflight_ready" if preflight.get("send_allowed") else "preflight_hold",
                    "preflight_payload_json": json.dumps(preflight, ensure_ascii=False, indent=2, sort_keys=True),
                    "preflight_envelope_hash": preflight.get("request_envelope_hash") or "",
                    "execution_envelope_json": False,
                    "runtime_dry_run_json": False,
                    "runtime_activation_packet_json": False,
                    "failure_reasons": "\n".join(preflight.get("failure_reasons", [])),
                    "formal_lineworks_send": False,
                    "external_api_call": False,
                    "secret_read": False,
                    "member_plaintext_read": False,
                }
            )

    def action_build_execution_envelope(self):
        for rec in self:
            rec._assert_no_secret_material()
            envelope = build_lineworks_execution_envelope_export(
                rec._candidate_payload(),
                rec._release_status_payload(),
                rec._connector_refs(),
                refs_path="odoo:wuchang.lineworks.notification.candidate.release_refs_json",
            )
            execution = envelope.get("execution_envelope", {})
            rec.write(
                {
                    "state": "envelope_ready" if envelope.get("state") == "PASS_LINEWORKS_EXECUTION_ENVELOPE_READY" else "envelope_hold",
                    "execution_envelope_json": json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True),
                    "execution_envelope_hash": execution.get("request_envelope_hash") or rec._stable_hash(envelope),
                    "runtime_dry_run_json": False,
                    "failure_reasons": "\n".join(execution.get("failure_reasons", [])),
                    "formal_lineworks_send": False,
                    "external_api_call": False,
                    "secret_read": False,
                    "member_plaintext_read": False,
                }
            )

    def action_build_runtime_activation_packet(self):
        for rec in self:
            rec._assert_no_secret_material()
            envelope = rec._json_loads_dict(rec.execution_envelope_json)
            execution_envelope_hash = (
                rec.execution_envelope_hash
                or (envelope.get("execution_envelope", {}) if isinstance(envelope, dict) else {}).get("request_envelope_hash")
                or ""
            )
            activation = build_lineworks_runtime_activation_packet(
                operator_ref=rec.runtime_operator_ref or "",
                execution_envelope_hash=execution_envelope_hash,
                candidate_packet_hash=rec.candidate_packet_hash or "",
                release_packet_hash=(envelope.get("preflight_envelope_hash") if isinstance(envelope, dict) else "") or "",
                confirm_human_activation=True,
            )
            rec.write(
                {
                    "runtime_activation_packet_hash": activation.get("activation_packet_hash") or "",
                    "runtime_activation_packet_json": json.dumps(activation, ensure_ascii=False, indent=2, sort_keys=True),
                    "failure_reasons": "\n".join(activation.get("draft_warnings", [])),
                    "formal_lineworks_send": False,
                    "external_api_call": False,
                    "secret_read": False,
                    "member_plaintext_read": False,
                }
            )

    def action_run_runtime_dry_run(self):
        for rec in self:
            rec._assert_no_secret_material()
            envelope = rec._json_loads_dict(rec.execution_envelope_json)
            if not envelope:
                envelope = build_lineworks_execution_envelope_export(
                    rec._candidate_payload(),
                    rec._release_status_payload(),
                    rec._connector_refs(),
                    refs_path="odoo:wuchang.lineworks.notification.candidate.release_refs_json",
                )
            activation = {
                "human_activation": bool(rec.runtime_activation_packet_hash and rec.runtime_operator_ref),
                "release_gate": "lineworks_send",
                "activation_packet_hash": str(rec.runtime_activation_packet_hash or "").strip().lower(),
                "operator_ref": rec.runtime_operator_ref or "",
            }
            result = execute_lineworks_send_envelope(
                envelope,
                runtime_activation=activation,
                enable_external_call=False,
            )
            rec.write(
                {
                    "state": "runtime_dry_run_ready" if result.get("dry_run_ready") else "runtime_dry_run_hold",
                    "execution_envelope_json": json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True),
                    "runtime_dry_run_json": json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True),
                    "runtime_result_hash": rec._stable_hash(result),
                    "failure_reasons": "\n".join(result.get("failure_reasons", [])),
                    "formal_lineworks_send": False,
                    "external_api_call": False,
                    "secret_read": False,
                    "member_plaintext_read": False,
                }
            )

    def action_build_operator_handoff_pack(self):
        for rec in self:
            rec._assert_no_secret_material()
            raw_refs = rec._json_loads_dict(rec.release_refs_json)
            lineworks_send = (
                raw_refs.get("lineworks_send")
                if isinstance(raw_refs.get("lineworks_send"), dict)
                else {key: value for key, value in raw_refs.items() if key != "connector_refs"}
            )
            connector_refs = dict(raw_refs.get("connector_refs") if isinstance(raw_refs.get("connector_refs"), dict) else {})
            for key, value in rec._connector_refs().items():
                if value:
                    connector_refs[key] = value
            refs = {
                "lineworks_send": lineworks_send,
                "connector_refs": connector_refs,
            }
            pack = build_lineworks_operator_handoff_pack(
                refs=refs,
                refs_path="odoo:wuchang.lineworks.notification.candidate.release_refs_json",
                message=rec.message_preview,
                target_ref=rec.target_ref_hash,
                actor_ref=rec.actor_ref_hash or "",
                operator_ref=rec.runtime_operator_ref or "OPERATOR_REF_HANDOFF_CHECK",
                channel=rec.channel,
                confirm_human_activation=bool(rec.runtime_operator_ref),
            )
            runtime_dry_run = pack.get("runtime_dry_run", {})
            rec.write(
                {
                    "state": (
                        "runtime_dry_run_ready"
                        if pack.get("state") == "PASS_LINEWORKS_OPERATOR_HANDOFF_READY_FOR_HUMAN_REVIEW"
                        else "runtime_dry_run_hold"
                    ),
                    "operator_handoff_pack_json": json.dumps(pack, ensure_ascii=False, indent=2, sort_keys=True),
                    "operator_handoff_pack_hash": rec._stable_hash(pack),
                    "failure_reasons": "\n".join(
                        list(pack.get("readiness", {}).get("blockers", []))
                        + list(runtime_dry_run.get("failure_reasons", []))
                        + list(pack.get("runtime_activation", {}).get("draft_warnings", []))
                    ),
                    "formal_lineworks_send": False,
                    "external_api_call": False,
                    "secret_read": False,
                    "member_plaintext_read": False,
                }
            )

    def action_dead_letter(self):
        for rec in self:
            rec.write(
                {
                    "state": "dead_letter",
                    "formal_lineworks_send": False,
                    "external_api_call": False,
                    "secret_read": False,
                    "member_plaintext_read": False,
                }
            )
