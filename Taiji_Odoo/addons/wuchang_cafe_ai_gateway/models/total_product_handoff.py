import json
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..services.total_product_handoff import build_total_product_operator_handoff
from ..services.total_product_ref_collection import (
    build_total_product_ref_collection_draft,
    build_total_product_ref_collection_input_template,
)


class WuchangTotalProductOperatorHandoff(models.Model):
    _name = "wuchang.total.product.operator.handoff"
    _description = "WuChang Total Product Operator Handoff"
    _order = "create_date desc, id desc"

    name = fields.Char(default="TOTAL-PRODUCT-HANDOFF", required=True, index=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("ref_collection_hold", "Ref Collection Hold"),
            ("refs_ready_for_handoff", "Refs Ready For Handoff"),
            ("handoff_ready", "Handoff Ready"),
            ("dead_letter", "Dead Letter"),
        ],
        default="draft",
        index=True,
        readonly=True,
    )
    allow_verified = fields.Boolean(
        default=False,
        help="Allow verified release refs only after a human owner/admin has checked the refs and packet hashes.",
    )
    refs_json = fields.Text(
        help="Total product refs JSON. Use refs only; do not paste passwords, tokens, raw member data, raw resident data, payment data, audio, or video."
    )
    line_official_account_intent = fields.Text(
        default=(
            "幫我把 LINE 官方帳號設定成咖啡館會員客服模式；新朋友加入先歡迎並詢問是否領用會員小J；"
            "促銷只發給已同意會員；付款、訂單、個資不得由 LLM 自行判定；設定完成後給我核定，不要直接生效。"
        )
    )
    lineworks_probe_json = fields.Text(
        help="Optional LINE WORKS probe JSON for local readiness only. Do not paste raw user IDs, tokens, or member plaintext."
    )
    ref_collection_json = fields.Text(readonly=True)
    human_fill_checklist_json = fields.Text(readonly=True)
    operator_fill_worksheet_md = fields.Text(readonly=True)
    handoff_pack_json = fields.Text(readonly=True)
    failure_reasons = fields.Text(readonly=True)
    draft_hash = fields.Char(readonly=True, index=True)
    handoff_hash = fields.Char(readonly=True, index=True)
    warnings_count = fields.Integer(readonly=True)
    ready_ref_count = fields.Integer(readonly=True)
    needs_human_fill_count = fields.Integer(readonly=True)
    ready_for_handoff_candidate = fields.Boolean(readonly=True)
    handoff_ready_for_operator = fields.Boolean(readonly=True)
    production_activation_ready = fields.Boolean(readonly=True)
    product_ready_for_human_activation = fields.Boolean(readonly=True)

    external_api_call = fields.Boolean(default=False, readonly=True)
    formal_lineworks_send = fields.Boolean(default=False, readonly=True)
    formal_line_message_send = fields.Boolean(default=False, readonly=True)
    official_account_setting_changed = fields.Boolean(default=False, readonly=True)
    formal_member_registration = fields.Boolean(default=False, readonly=True)
    formal_db_write = fields.Boolean(default=False, readonly=True)
    formal_pos_write = fields.Boolean(default=False, readonly=True)
    payment_capture = fields.Boolean(default=False, readonly=True)
    secret_read = fields.Boolean(default=False, readonly=True)
    member_plaintext_read = fields.Boolean(default=False, readonly=True)
    resident_plaintext_read = fields.Boolean(default=False, readonly=True)
    raw_audio_saved = fields.Boolean(default=False, readonly=True)
    raw_video_saved = fields.Boolean(default=False, readonly=True)
    deploy = fields.Boolean(default=False, readonly=True)
    service_restart = fields.Boolean(default=False, readonly=True)

    def _contains_secret_shape(self, value):
        text = str(value or "")
        hash_stripped = re.sub(r"\b[a-fA-F0-9]{64}\b", "[HASH]", text)
        return bool(
            re.search(r"sk-[A-Za-z0-9_-]{12,}", text)
            or re.search(r"(?i)(access|refresh|id)_token\s*[:=]\s*\S+", text)
            or re.search(r"(?i)channel_secret\s*[:=]\s*\S+", text)
            or re.search(r"(?i)client_secret\s*[:=]\s*\S+", text)
            or re.search(r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----", text)
            or re.search(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}", text)
            or re.search(r"[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}", text)
            or re.search(r"(?=.*[A-Za-z])(?=.*[0-9])[A-Za-z0-9_~+/=-]{40,}", hash_stripped)
            or re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
            or re.search(r"09\d{2}[- ]?\d{3}[- ]?\d{3}", text)
            or re.search(r"\b[A-Z][12]\d{8}\b", text)
        )

    def _assert_no_secret_material(self):
        for rec in self:
            values = [
                rec.refs_json,
                rec.line_official_account_intent,
                rec.lineworks_probe_json,
            ]
            if any(rec._contains_secret_shape(value) for value in values):
                raise UserError(
                    _(
                        "Secret-shaped or plaintext-shaped material is not allowed in total product handoff records. Use refs only."
                    )
                )

    @api.constrains("refs_json", "line_official_account_intent", "lineworks_probe_json")
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

    def _false_side_effect_values(self):
        return {
            "external_api_call": False,
            "formal_lineworks_send": False,
            "formal_line_message_send": False,
            "official_account_setting_changed": False,
            "formal_member_registration": False,
            "formal_db_write": False,
            "formal_pos_write": False,
            "payment_capture": False,
            "secret_read": False,
            "member_plaintext_read": False,
            "resident_plaintext_read": False,
            "raw_audio_saved": False,
            "raw_video_saved": False,
            "deploy": False,
            "service_restart": False,
        }

    def _ref_collection_payload(self):
        self.ensure_one()
        collection = self._json_loads_dict(self.ref_collection_json)
        if collection:
            return collection
        return build_total_product_ref_collection_draft(
            self._json_loads_dict(self.refs_json),
            allow_verified=self.allow_verified,
        )

    def _handoff_inputs(self, ref_collection):
        handoff_inputs = ref_collection.get("handoff_inputs") if isinstance(ref_collection.get("handoff_inputs"), dict) else {}
        return {
            "formal_release_refs": (
                handoff_inputs.get("formal_release_refs") if isinstance(handoff_inputs.get("formal_release_refs"), dict) else {}
            ),
            "lineworks_refs": handoff_inputs.get("lineworks_refs") if isinstance(handoff_inputs.get("lineworks_refs"), dict) else {},
            "line_official_account_refs": (
                handoff_inputs.get("line_official_account_refs")
                if isinstance(handoff_inputs.get("line_official_account_refs"), dict)
                else {}
            ),
        }

    def action_build_ref_collection(self):
        for rec in self:
            rec._assert_no_secret_material()
            draft = build_total_product_ref_collection_draft(
                rec._json_loads_dict(rec.refs_json),
                allow_verified=rec.allow_verified,
            )
            warnings = draft.get("draft_warnings", [])
            fill_summary = draft.get("operator_fill_summary", {})
            rec.write(
                {
                    "state": (
                        "refs_ready_for_handoff"
                        if draft.get("ready_for_handoff_candidate") is True
                        else "ref_collection_hold"
                    ),
                    "ref_collection_json": json.dumps(draft, ensure_ascii=False, indent=2, sort_keys=True),
                    "human_fill_checklist_json": json.dumps(
                        draft.get("human_fill_checklist", []),
                        ensure_ascii=False,
                        indent=2,
                        sort_keys=True,
                    ),
                    "operator_fill_worksheet_md": draft.get("operator_fill_worksheet_md", ""),
                    "draft_hash": draft.get("draft_hash") or "",
                    "warnings_count": len(warnings),
                    "ready_ref_count": fill_summary.get("ready_count", 0),
                    "needs_human_fill_count": fill_summary.get("needs_human_fill_count", 0),
                    "ready_for_handoff_candidate": draft.get("ready_for_handoff_candidate") is True,
                    "failure_reasons": "\n".join(warnings),
                    **rec._false_side_effect_values(),
                }
            )

    def action_load_ref_template(self):
        for rec in self:
            template = build_total_product_ref_collection_input_template()
            rec.write(
                {
                    "state": "draft",
                    "refs_json": json.dumps(template, ensure_ascii=False, indent=2, sort_keys=True),
                    "ref_collection_json": "",
                    "human_fill_checklist_json": "",
                    "operator_fill_worksheet_md": "",
                    "handoff_pack_json": "",
                    "failure_reasons": "",
                    "draft_hash": "",
                    "handoff_hash": "",
                    "warnings_count": 0,
                    "ready_ref_count": 0,
                    "needs_human_fill_count": 0,
                    "ready_for_handoff_candidate": False,
                    "handoff_ready_for_operator": False,
                    "production_activation_ready": False,
                    "product_ready_for_human_activation": False,
                    **rec._false_side_effect_values(),
                }
            )

    def action_build_handoff_pack(self):
        for rec in self:
            rec._assert_no_secret_material()
            ref_collection = rec._ref_collection_payload()
            handoff_inputs = rec._handoff_inputs(ref_collection)
            pack = build_total_product_operator_handoff(
                formal_release_refs=handoff_inputs["formal_release_refs"],
                lineworks_refs=handoff_inputs["lineworks_refs"],
                line_official_account_refs=handoff_inputs["line_official_account_refs"],
                line_official_account_intent=rec.line_official_account_intent or "",
                lineworks_probe=rec._json_loads_dict(rec.lineworks_probe_json),
                input_ref=f"odoo:wuchang.total.product.operator.handoff:{rec.id or 'new'}",
            )
            next_actions = pack.get("merchant_productization", {}).get("operator_next_actions", [])
            fill_summary = ref_collection.get("operator_fill_summary", {})
            rec.write(
                {
                    "state": "handoff_ready" if pack.get("state") == "PASS_XIAOJ_TOTAL_PRODUCT_OPERATOR_HANDOFF_READY" else "ref_collection_hold",
                    "ref_collection_json": json.dumps(ref_collection, ensure_ascii=False, indent=2, sort_keys=True),
                    "human_fill_checklist_json": json.dumps(
                        ref_collection.get("human_fill_checklist", []),
                        ensure_ascii=False,
                        indent=2,
                        sort_keys=True,
                    ),
                    "operator_fill_worksheet_md": ref_collection.get("operator_fill_worksheet_md", ""),
                    "handoff_pack_json": json.dumps(pack, ensure_ascii=False, indent=2, sort_keys=True),
                    "draft_hash": ref_collection.get("draft_hash") or rec.draft_hash,
                    "handoff_hash": pack.get("handoff_hash") or "",
                    "warnings_count": len(ref_collection.get("draft_warnings", [])),
                    "ready_ref_count": fill_summary.get("ready_count", 0),
                    "needs_human_fill_count": fill_summary.get("needs_human_fill_count", 0),
                    "ready_for_handoff_candidate": ref_collection.get("ready_for_handoff_candidate") is True,
                    "handoff_ready_for_operator": pack.get("handoff_ready_for_operator") is True,
                    "production_activation_ready": pack.get("production_activation_ready") is True,
                    "product_ready_for_human_activation": (
                        pack.get("merchant_productization", {}).get("product_ready_for_human_activation") is True
                    ),
                    "failure_reasons": "\n".join(next_actions),
                    **rec._false_side_effect_values(),
                }
            )

    def action_dead_letter(self):
        for rec in self:
            rec.write(
                {
                    "state": "dead_letter",
                    "handoff_ready_for_operator": False,
                    "production_activation_ready": False,
                    "product_ready_for_human_activation": False,
                    "ready_ref_count": 0,
                    "needs_human_fill_count": 0,
                    **rec._false_side_effect_values(),
                }
            )
