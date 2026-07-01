import hashlib
import json
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..services.line_official_account_config import build_line_official_account_config_candidate
from ..services.line_official_account_refs import build_line_official_account_refs_draft


class WuchangLineOfficialAccountConfigCandidate(models.Model):
    _name = "wuchang.line.official.account.config.candidate"
    _description = "WuChang LINE Official Account Config Candidate"
    _order = "create_date desc, id desc"

    name = fields.Char(default="LINE-OA-CONFIG-CANDIDATE", required=True, index=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("candidate_hold", "Candidate Hold"),
            ("ready_for_human_approval", "Ready For Human Approval"),
            ("dead_letter", "Dead Letter"),
        ],
        default="draft",
        index=True,
        readonly=True,
    )
    intent_text = fields.Text(
        required=True,
        help="Natural-language operator intent. Do not paste LINE tokens, channel secrets, raw user IDs, or member plaintext.",
    )
    refs_json = fields.Text(
        help="LINE Official Account refs only. Do not paste channel access tokens, channel secrets, passwords, or member plaintext."
    )
    refs_draft_warnings = fields.Text(readonly=True)
    refs_draft_hash = fields.Char(readonly=True, index=True)
    style_ref = fields.Char(default="STYLE_REF_XIAOJ_WARM_PRECISE", required=True)
    operator_ref = fields.Char(default="OPERATOR_REF_LINE_OFFICIAL_ACCOUNT_REVIEW", required=True)
    config_candidate_json = fields.Text(readonly=True)
    failure_reasons = fields.Text(readonly=True)
    packet_hash = fields.Char(readonly=True, index=True)
    evidence_hash = fields.Char(readonly=True, index=True)

    external_api_call = fields.Boolean(default=False, readonly=True)
    formal_line_message_send = fields.Boolean(default=False, readonly=True)
    official_account_setting_changed = fields.Boolean(default=False, readonly=True)
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
            or re.search(r"(?i)channel_secret\s*[:=]\s*\S+", text)
            or re.search(r"(?i)client_secret\s*[:=]\s*\S+", text)
            or re.search(r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----", text)
            or re.search(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}", text)
            or re.search(r"[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}", text)
            or re.search(r"(?=.*[A-Za-z])(?=.*[0-9])[A-Za-z0-9_~+/=-]{40,}", text)
            or re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
            or re.search(r"09\d{2}[- ]?\d{3}[- ]?\d{3}", text)
            or re.search(r"\b[A-Z][12]\d{8}\b", text)
        )

    def _assert_no_secret_material(self):
        for rec in self:
            values = [rec.intent_text, rec.refs_json, rec.style_ref, rec.operator_ref]
            if any(rec._contains_secret_shape(value) for value in values):
                raise UserError(
                    _(
                        "Secret-shaped or member-plaintext material is not allowed in LINE Official Account config candidates. Use refs only."
                    )
                )

    @api.constrains("intent_text", "refs_json", "style_ref", "operator_ref")
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

    def action_build_config_candidate(self):
        for rec in self:
            rec._assert_no_secret_material()
            candidate = build_line_official_account_config_candidate(
                rec.intent_text,
                refs=rec._json_loads_dict(rec.refs_json),
                style_ref=rec.style_ref,
                operator_ref=rec.operator_ref,
            )
            authority_packet = candidate.get("authority_packet", {})
            rec.write(
                {
                    "state": (
                        "ready_for_human_approval"
                        if candidate.get("state") == "READY_FOR_HUMAN_APPROVAL"
                        else "candidate_hold"
                    ),
                    "config_candidate_json": json.dumps(candidate, ensure_ascii=False, indent=2, sort_keys=True),
                    "packet_hash": authority_packet.get("packet_hash") or rec._stable_hash(candidate),
                    "evidence_hash": authority_packet.get("evidence_hash") or "",
                    "failure_reasons": "\n".join(candidate.get("local_verifier", {}).get("failure_reasons", [])),
                    "external_api_call": False,
                    "formal_line_message_send": False,
                    "official_account_setting_changed": False,
                    "secret_read": False,
                    "member_plaintext_read": False,
                }
            )

    def action_build_refs_draft(self):
        for rec in self:
            rec._assert_no_secret_material()
            draft = build_line_official_account_refs_draft(rec._json_loads_dict(rec.refs_json))
            rec.write(
                {
                    "refs_json": json.dumps(draft.get("refs", {}), ensure_ascii=False, indent=2, sort_keys=True),
                    "refs_draft_hash": draft.get("draft_hash") or "",
                    "refs_draft_warnings": "\n".join(draft.get("draft_warnings", [])),
                    "failure_reasons": "\n".join(draft.get("draft_warnings", [])),
                    "external_api_call": False,
                    "formal_line_message_send": False,
                    "official_account_setting_changed": False,
                    "secret_read": False,
                    "member_plaintext_read": False,
                }
            )

    def action_dead_letter(self):
        for rec in self:
            rec.write(
                {
                    "state": "dead_letter",
                    "external_api_call": False,
                    "formal_line_message_send": False,
                    "official_account_setting_changed": False,
                    "secret_read": False,
                    "member_plaintext_read": False,
                }
            )
