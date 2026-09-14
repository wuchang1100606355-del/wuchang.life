import json
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..services.business_backend_optimization import (
    build_business_backend_av_candidate_quality_packet,
    build_business_backend_daily_signal_packet,
    build_business_backend_management_decision_queue_packet,
    build_business_backend_member_voucher_payment_preflight_packet,
    build_business_backend_operating_review_packet,
    build_business_backend_operator_runbook_packet,
    build_business_backend_optimization_packet,
    build_business_backend_process_walkthrough_packet,
    build_business_backend_product_menu_quality_packet,
    build_business_backend_readiness_scorecard_packet,
    build_business_backend_signal_trend_packet,
)


class WuchangBusinessBackendOptimization(models.Model):
    _name = "wuchang.business.backend.optimization"
    _description = "WuChang Business Backend Optimization"
    _order = "create_date desc, id desc"

    name = fields.Char(default="BUSINESS-BACKEND-OPTIMIZATION", required=True, index=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("review_ready", "Review Ready"),
            ("dead_letter", "Dead Letter"),
        ],
        default="draft",
        readonly=True,
        index=True,
    )
    actor_ref = fields.Char(default="ACTOR_REF_BUSINESS_BACKEND_OPERATOR")
    input_ref = fields.Char(default="odoo:wuchang.business.backend.optimization")
    operator_notes = fields.Text(
        help="Operator notes for backend improvement review. Use refs and summaries only; do not paste secrets or member plaintext."
    )

    review_packet_json = fields.Text(readonly=True)
    operating_review_json = fields.Text(readonly=True)
    operating_review_next_actions = fields.Text(readonly=True)
    process_walkthrough_json = fields.Text(readonly=True)
    process_improvement_next_actions = fields.Text(readonly=True)
    readiness_scorecard_json = fields.Text(readonly=True)
    readiness_scorecard_next_actions = fields.Text(readonly=True)
    readiness_activation_blockers = fields.Text(readonly=True)
    daily_signal_review_json = fields.Text(readonly=True)
    daily_signal_next_actions = fields.Text(readonly=True)
    signal_trend_review_json = fields.Text(readonly=True)
    signal_trend_next_actions = fields.Text(readonly=True)
    management_decision_queue_json = fields.Text(readonly=True)
    management_decision_next_actions = fields.Text(readonly=True)
    operator_runbook_json = fields.Text(readonly=True)
    operator_runbook_next_actions = fields.Text(readonly=True)
    av_candidate_quality_json = fields.Text(readonly=True)
    av_candidate_quality_next_actions = fields.Text(readonly=True)
    product_menu_quality_json = fields.Text(readonly=True)
    product_menu_quality_next_actions = fields.Text(readonly=True)
    member_voucher_payment_preflight_json = fields.Text(readonly=True)
    member_voucher_payment_preflight_next_actions = fields.Text(readonly=True)
    checklist_item_ids = fields.One2many(
        "wuchang.business.backend.optimization.item",
        "optimization_id",
        string="Checklist Items",
    )
    kpi_snapshot_ids = fields.One2many(
        "wuchang.business.backend.kpi.snapshot",
        "optimization_id",
        string="KPI Snapshots",
    )
    improvement_item_ids = fields.One2many(
        "wuchang.business.backend.improvement.item",
        "optimization_id",
        string="Process Improvement Items",
    )
    daily_signal_ids = fields.One2many(
        "wuchang.business.backend.daily.signal",
        "optimization_id",
        string="Daily Operating Signals",
    )
    management_decision_item_ids = fields.One2many(
        "wuchang.business.backend.management.decision.item",
        "optimization_id",
        string="Management Decision Items",
    )
    av_candidate_ids = fields.One2many(
        "wuchang.business.backend.av.candidate",
        "optimization_id",
        string="AV AI Candidates",
    )
    product_quality_ids = fields.One2many(
        "wuchang.business.backend.product.quality",
        "optimization_id",
        string="Product/Menu Quality Items",
    )
    checkout_preflight_ids = fields.One2many(
        "wuchang.business.backend.checkout.preflight",
        "optimization_id",
        string="Member Voucher Payment Preflights",
    )
    recommended_backend_panels_json = fields.Text(readonly=True)
    end_to_end_flow_json = fields.Text(readonly=True)
    ai_technology_features_json = fields.Text(readonly=True)
    quality_gates_json = fields.Text(readonly=True)
    required_refs_json = fields.Text(readonly=True)
    business_context_json = fields.Text(readonly=True)
    first_backoffice_enhancements_json = fields.Text(readonly=True)
    packet_hash = fields.Char(readonly=True, index=True)

    panel_count = fields.Integer(readonly=True)
    flow_step_count = fields.Integer(readonly=True)
    ai_feature_count = fields.Integer(readonly=True)
    required_ref_count = fields.Integer(readonly=True)
    checklist_item_count = fields.Integer(readonly=True)
    kpi_snapshot_count = fields.Integer(readonly=True)
    blocked_checklist_count = fields.Integer(readonly=True)
    needs_action_kpi_count = fields.Integer(readonly=True)
    improvement_item_count = fields.Integer(readonly=True)
    critical_improvement_count = fields.Integer(readonly=True)
    ai_merchant_readiness_score = fields.Float(readonly=True)
    blocked_improvement_count = fields.Integer(readonly=True)
    critical_open_improvement_count = fields.Integer(readonly=True)
    daily_signal_count = fields.Integer(readonly=True)
    daily_signal_needs_action_count = fields.Integer(readonly=True)
    daily_signal_observed_day_count = fields.Integer(readonly=True)
    regressing_signal_count = fields.Integer(readonly=True)
    insufficient_signal_count = fields.Integer(readonly=True)
    management_decision_count = fields.Integer(readonly=True)
    critical_decision_count = fields.Integer(readonly=True)
    high_decision_count = fields.Integer(readonly=True)
    operator_runbook_step_count = fields.Integer(readonly=True)
    operator_runbook_daily_step_count = fields.Integer(readonly=True)
    operator_runbook_weekly_step_count = fields.Integer(readonly=True)
    av_candidate_count = fields.Integer(readonly=True)
    low_confidence_candidate_count = fields.Integer(readonly=True)
    failed_validation_candidate_count = fields.Integer(readonly=True)
    generated_image_hold_count = fields.Integer(readonly=True)
    staff_review_required_candidate_count = fields.Integer(readonly=True)
    product_quality_count = fields.Integer(readonly=True)
    product_quality_ready_count = fields.Integer(readonly=True)
    product_quality_blocked_count = fields.Integer(readonly=True)
    missing_custom_options_count = fields.Integer(readonly=True)
    missing_photo_evidence_count = fields.Integer(readonly=True)
    checkout_preflight_count = fields.Integer(readonly=True)
    checkout_preflight_ready_count = fields.Integer(readonly=True)
    checkout_preflight_blocked_count = fields.Integer(readonly=True)
    production_activation_ready = fields.Boolean(readonly=True)

    external_api_call = fields.Boolean(default=False, readonly=True)
    model_invocation = fields.Boolean(default=False, readonly=True)
    formal_lineworks_send = fields.Boolean(default=False, readonly=True)
    formal_line_message_send = fields.Boolean(default=False, readonly=True)
    formal_member_registration = fields.Boolean(default=False, readonly=True)
    formal_db_write = fields.Boolean(default=False, readonly=True)
    formal_pos_write = fields.Boolean(default=False, readonly=True)
    pos_order_created = fields.Boolean(default=False, readonly=True)
    payment_capture = fields.Boolean(default=False, readonly=True)
    voucher_redemption = fields.Boolean(default=False, readonly=True)
    secret_read = fields.Boolean(default=False, readonly=True)
    member_plaintext_read = fields.Boolean(default=False, readonly=True)
    resident_plaintext_read = fields.Boolean(default=False, readonly=True)
    raw_audio_saved = fields.Boolean(default=False, readonly=True)
    raw_video_saved = fields.Boolean(default=False, readonly=True)
    deploy = fields.Boolean(default=False, readonly=True)
    service_restart = fields.Boolean(default=False, readonly=True)
    odoo_upgrade = fields.Boolean(default=False, readonly=True)

    def _contains_secret_shape(self, value):
        text = str(value or "")
        return bool(
            re.search(r"sk-[A-Za-z0-9_-]{12,}", text)
            or re.search(r"(?i)(access|refresh|id)_token\s*[:=]\s*\S+", text)
            or re.search(r"(?i)api[_ -]?key\s*[:=]\s*\S+", text)
            or re.search(r"(?i)(channel|client|router|odoo|lineworks|line)[_-]?secret\s*[:=]\s*\S+", text)
            or re.search(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}", text)
            or re.search(r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----", text)
            or re.search(r"[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}", text)
            or re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
            or re.search(r"09\d{2}[- ]?\d{3}[- ]?\d{3}", text)
            or re.search(r"\b[A-Z][12]\d{8}\b", text)
        )

    def _assert_no_secret_material(self):
        for rec in self:
            values = [rec.actor_ref, rec.input_ref, rec.operator_notes]
            if any(rec._contains_secret_shape(value) for value in values):
                raise UserError(_("Secret-shaped or plaintext-shaped material is not allowed. Use refs only."))

    @api.constrains("actor_ref", "input_ref", "operator_notes")
    def _check_red_team_boundaries(self):
        self._assert_no_secret_material()

    def _false_side_effect_values(self):
        return {
            "external_api_call": False,
            "model_invocation": False,
            "formal_lineworks_send": False,
            "formal_line_message_send": False,
            "formal_member_registration": False,
            "formal_db_write": False,
            "formal_pos_write": False,
            "pos_order_created": False,
            "payment_capture": False,
            "voucher_redemption": False,
            "secret_read": False,
            "member_plaintext_read": False,
            "resident_plaintext_read": False,
            "raw_audio_saved": False,
            "raw_video_saved": False,
            "deploy": False,
            "service_restart": False,
            "odoo_upgrade": False,
        }

    def action_build_review_packet(self):
        for rec in self:
            rec._assert_no_secret_material()
            packet = build_business_backend_optimization_packet(
                actor_ref=rec.actor_ref or "",
                input_ref=rec.input_ref or f"odoo:wuchang.business.backend.optimization:{rec.id or 'new'}",
            )
            refs = packet.get("required_refs", {})
            required_ref_count = sum(len(values) for values in refs.values() if isinstance(values, list))
            checklist_items = packet.get("backend_checklist_items", [])
            kpi_snapshot_types = packet.get("kpi_snapshot_types", [])
            checklist_commands = [(5, 0, 0)]
            for index, item in enumerate(checklist_items, start=1):
                checklist_commands.append(
                    (
                        0,
                        0,
                        {
                            "sequence": index,
                            "panel": item.get("panel", ""),
                            "item_key": item.get("item_key", ""),
                            "title": item.get("title", ""),
                            "required_ref": item.get("required_ref", ""),
                            "success_metric": item.get("success_metric", ""),
                            "phase": item.get("phase", "P1_REVIEW"),
                            "operator_status": "todo",
                        },
                    )
                )
            kpi_commands = [(5, 0, 0)]
            for index, snapshot_type in enumerate(kpi_snapshot_types, start=1):
                kpi_commands.append(
                    (
                        0,
                        0,
                        {
                            "sequence": index,
                            "snapshot_type": snapshot_type,
                            "state": "draft",
                            "summary": "",
                        },
                    )
                )
            rec.write(
                {
                    "state": "review_ready",
                    "review_packet_json": json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True),
                    "operating_review_json": "",
                    "operating_review_next_actions": "",
                    "process_walkthrough_json": "",
                    "process_improvement_next_actions": "",
                    "readiness_scorecard_json": "",
                    "readiness_scorecard_next_actions": "",
                    "readiness_activation_blockers": "",
                    "daily_signal_review_json": "",
                    "daily_signal_next_actions": "",
                    "signal_trend_review_json": "",
                    "signal_trend_next_actions": "",
                    "management_decision_queue_json": "",
                    "management_decision_next_actions": "",
                    "operator_runbook_json": "",
                    "operator_runbook_next_actions": "",
                    "av_candidate_quality_json": "",
                    "av_candidate_quality_next_actions": "",
                    "product_menu_quality_json": "",
                    "product_menu_quality_next_actions": "",
                    "member_voucher_payment_preflight_json": "",
                    "member_voucher_payment_preflight_next_actions": "",
                    "recommended_backend_panels_json": json.dumps(
                        packet.get("recommended_backend_panels", []), ensure_ascii=False, indent=2
                    ),
                    "end_to_end_flow_json": json.dumps(packet.get("end_to_end_flow", []), ensure_ascii=False, indent=2),
                    "ai_technology_features_json": json.dumps(
                        packet.get("ai_technology_features", []), ensure_ascii=False, indent=2
                    ),
                    "quality_gates_json": json.dumps(packet.get("quality_gates", {}), ensure_ascii=False, indent=2, sort_keys=True),
                    "required_refs_json": json.dumps(refs, ensure_ascii=False, indent=2, sort_keys=True),
                    "business_context_json": json.dumps(
                        packet.get("business_context", {}), ensure_ascii=False, indent=2, sort_keys=True
                    ),
                    "first_backoffice_enhancements_json": json.dumps(
                        packet.get("recommended_first_backoffice_enhancements", []), ensure_ascii=False, indent=2
                    ),
                    "packet_hash": packet.get("packet_hash", ""),
                    "checklist_item_ids": checklist_commands,
                    "kpi_snapshot_ids": kpi_commands,
                    "panel_count": len(packet.get("recommended_backend_panels", [])),
                    "flow_step_count": len(packet.get("end_to_end_flow", [])),
                    "ai_feature_count": len(packet.get("ai_technology_features", [])),
                    "required_ref_count": required_ref_count,
                    "checklist_item_count": len(checklist_items),
                    "kpi_snapshot_count": len(kpi_snapshot_types),
                    "blocked_checklist_count": 0,
                    "needs_action_kpi_count": 0,
                    "improvement_item_count": 0,
                    "critical_improvement_count": 0,
                    "ai_merchant_readiness_score": 0.0,
                    "blocked_improvement_count": 0,
                    "critical_open_improvement_count": 0,
                    "daily_signal_count": 0,
                    "daily_signal_needs_action_count": 0,
                    "daily_signal_observed_day_count": 0,
                    "regressing_signal_count": 0,
                    "insufficient_signal_count": 0,
                    "management_decision_count": 0,
                    "critical_decision_count": 0,
                    "high_decision_count": 0,
                    "operator_runbook_step_count": 0,
                    "operator_runbook_daily_step_count": 0,
                    "operator_runbook_weekly_step_count": 0,
                    "av_candidate_count": 0,
                    "low_confidence_candidate_count": 0,
                    "failed_validation_candidate_count": 0,
                    "generated_image_hold_count": 0,
                    "staff_review_required_candidate_count": 0,
                    "product_quality_count": 0,
                    "product_quality_ready_count": 0,
                    "product_quality_blocked_count": 0,
                    "missing_custom_options_count": 0,
                    "missing_photo_evidence_count": 0,
                    "checkout_preflight_count": 0,
                    "checkout_preflight_ready_count": 0,
                    "checkout_preflight_blocked_count": 0,
                    "production_activation_ready": packet.get("production_activation_ready") is True,
                    **rec._false_side_effect_values(),
                }
            )

    def _checkout_preflight_dicts(self):
        return [
            {
                "candidate_order_ref": item.candidate_order_ref,
                "member_ref": item.member_ref,
                "voucher_dry_run_ref": item.voucher_dry_run_ref,
                "payment_method_ref": item.payment_method_ref,
                "pos_draft_ref": item.pos_draft_ref,
                "consent_ref": item.consent_ref,
                "preflight_state": item.preflight_state,
                "requested_mutation": item.requested_mutation,
            }
            for item in self.checkout_preflight_ids
        ]

    def action_build_member_voucher_payment_preflight(self):
        for rec in self:
            rec._assert_no_secret_material()
            packet = build_business_backend_member_voucher_payment_preflight_packet(
                preflights=rec._checkout_preflight_dicts(),
                actor_ref=rec.actor_ref or "",
                input_ref=rec.input_ref or f"odoo:wuchang.business.backend.optimization:{rec.id or 'new'}:member_voucher_payment_preflight",
            )
            rec.write(
                {
                    "member_voucher_payment_preflight_json": json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True),
                    "member_voucher_payment_preflight_next_actions": "\n".join(packet.get("next_actions", [])),
                    "checkout_preflight_count": packet.get("preflight_count", 0),
                    "checkout_preflight_ready_count": packet.get("ready_preflight_count", 0),
                    "checkout_preflight_blocked_count": packet.get("blocked_preflight_count", 0),
                    "production_activation_ready": packet.get("production_activation_ready") is True,
                    **rec._false_side_effect_values(),
                }
            )

    def _product_quality_dicts(self):
        return [
            {
                "product_ref": item.product_ref,
                "odoo_product_ref": item.odoo_product_ref,
                "menu_category_ref": item.menu_category_ref,
                "price_ref": item.price_ref,
                "custom_options_ref": item.custom_options_ref,
                "photo_evidence_ref": item.photo_evidence_ref,
                "photo_evidence_state": item.photo_evidence_state,
                "availability_state": item.availability_state,
                "ai_candidate_state": item.ai_candidate_state,
            }
            for item in self.product_quality_ids
        ]

    def action_build_product_menu_quality_review(self):
        for rec in self:
            rec._assert_no_secret_material()
            packet = build_business_backend_product_menu_quality_packet(
                products=rec._product_quality_dicts(),
                actor_ref=rec.actor_ref or "",
                input_ref=rec.input_ref or f"odoo:wuchang.business.backend.optimization:{rec.id or 'new'}:product_menu_quality",
            )
            rec.write(
                {
                    "product_menu_quality_json": json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True),
                    "product_menu_quality_next_actions": "\n".join(packet.get("next_actions", [])),
                    "product_quality_count": packet.get("product_count", 0),
                    "product_quality_ready_count": packet.get("ready_product_count", 0),
                    "product_quality_blocked_count": packet.get("blocked_product_count", 0),
                    "missing_custom_options_count": packet.get("missing_custom_options_count", 0),
                    "missing_photo_evidence_count": packet.get("missing_photo_evidence_count", 0),
                    "production_activation_ready": packet.get("production_activation_ready") is True,
                    **rec._false_side_effect_values(),
                }
            )

    def _av_candidate_dicts(self):
        return [
            {
                "candidate_ref": candidate.candidate_ref,
                "modality": candidate.modality,
                "review_state": candidate.review_state,
                "confidence_score": candidate.confidence_score,
                "odoo_validation_state": candidate.odoo_validation_state,
                "product_photo_evidence_state": candidate.product_photo_evidence_state,
                "red_flags": [
                    flag.strip()
                    for flag in (candidate.red_flags or "").splitlines()
                    if flag.strip()
                ],
                "evidence_ref": candidate.evidence_ref,
            }
            for candidate in self.av_candidate_ids
        ]

    def action_build_av_candidate_quality_review(self):
        for rec in self:
            rec._assert_no_secret_material()
            packet = build_business_backend_av_candidate_quality_packet(
                candidates=rec._av_candidate_dicts(),
                actor_ref=rec.actor_ref or "",
                input_ref=rec.input_ref or f"odoo:wuchang.business.backend.optimization:{rec.id or 'new'}:av_candidate_quality",
            )
            rec.write(
                {
                    "av_candidate_quality_json": json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True),
                    "av_candidate_quality_next_actions": "\n".join(packet.get("next_actions", [])),
                    "av_candidate_count": packet.get("candidate_count", 0),
                    "low_confidence_candidate_count": packet.get("low_confidence_count", 0),
                    "failed_validation_candidate_count": packet.get("failed_validation_count", 0),
                    "generated_image_hold_count": packet.get("generated_image_hold_count", 0),
                    "staff_review_required_candidate_count": packet.get("staff_review_required_count", 0),
                    "production_activation_ready": packet.get("production_activation_ready") is True,
                    **rec._false_side_effect_values(),
                }
            )

    def action_build_operator_runbook(self):
        for rec in self:
            rec._assert_no_secret_material()
            packet = build_business_backend_operator_runbook_packet(
                actor_ref=rec.actor_ref or "",
                input_ref=rec.input_ref or f"odoo:wuchang.business.backend.optimization:{rec.id or 'new'}:operator_runbook",
            )
            rec.write(
                {
                    "operator_runbook_json": json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True),
                    "operator_runbook_next_actions": "\n".join(packet.get("next_actions", [])),
                    "operator_runbook_step_count": packet.get("step_count", 0),
                    "operator_runbook_daily_step_count": packet.get("daily_step_count", 0),
                    "operator_runbook_weekly_step_count": packet.get("weekly_step_count", 0),
                    "production_activation_ready": packet.get("production_activation_ready") is True,
                    **rec._false_side_effect_values(),
                }
            )

    def action_build_process_walkthrough(self):
        for rec in self:
            rec._assert_no_secret_material()
            completed_keys = [
                item.improvement_key
                for item in rec.improvement_item_ids
                if item.operator_status == "done" and item.improvement_key
            ]
            packet = build_business_backend_process_walkthrough_packet(
                actor_ref=rec.actor_ref or "",
                input_ref=rec.input_ref or f"odoo:wuchang.business.backend.optimization:{rec.id or 'new'}:process_walkthrough",
                completed_improvement_keys=completed_keys,
            )
            improvement_commands = [(5, 0, 0)]
            for item in packet.get("improvement_items", []):
                improvement_commands.append(
                    (
                        0,
                        0,
                        {
                            "sequence": item.get("sequence", 10),
                            "stage_key": item.get("stage_key", ""),
                            "improvement_key": item.get("improvement_key", ""),
                            "title": item.get("title", ""),
                            "priority": item.get("priority", "medium"),
                            "owner_scope": item.get("owner_scope", ""),
                            "kpi_type": item.get("kpi_type", ""),
                            "operator_status": item.get("operator_status", "todo"),
                            "success_metric": item.get("success_metric", ""),
                        },
                    )
                )
            rec.write(
                {
                    "process_walkthrough_json": json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True),
                    "process_improvement_next_actions": "\n".join(packet.get("next_actions", [])),
                    "improvement_item_ids": improvement_commands,
                    "improvement_item_count": packet.get("improvement_item_count", 0),
                    "critical_improvement_count": packet.get("critical_improvement_count", 0),
                    "production_activation_ready": packet.get("production_activation_ready") is True,
                    **rec._false_side_effect_values(),
                }
            )

    def _daily_signal_dicts(self):
        return [
            {
                "signal_date": str(signal.signal_date or ""),
                "signal_type": signal.signal_type,
                "state": signal.state,
                "numeric_value": signal.numeric_value,
                "unit": signal.unit,
                "evidence_ref": signal.evidence_ref,
                "summary": signal.summary,
            }
            for signal in self.daily_signal_ids
        ]

    def action_build_daily_signal_review(self):
        for rec in self:
            rec._assert_no_secret_material()
            daily_signals = rec._daily_signal_dicts()
            packet = build_business_backend_daily_signal_packet(
                daily_signals=daily_signals,
                actor_ref=rec.actor_ref or "",
                input_ref=rec.input_ref or f"odoo:wuchang.business.backend.optimization:{rec.id or 'new'}:daily_signal",
            )
            rec.write(
                {
                    "daily_signal_review_json": json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True),
                    "daily_signal_next_actions": "\n".join(packet.get("next_actions", [])),
                    "daily_signal_count": len(daily_signals),
                    "daily_signal_needs_action_count": len(packet.get("needs_action_signals", [])),
                    "daily_signal_observed_day_count": packet.get("observed_day_count", 0),
                    "production_activation_ready": packet.get("production_activation_ready") is True,
                    **rec._false_side_effect_values(),
                }
            )

    def action_build_signal_trend_review(self):
        for rec in self:
            rec._assert_no_secret_material()
            packet = build_business_backend_signal_trend_packet(
                daily_signals=rec._daily_signal_dicts(),
                actor_ref=rec.actor_ref or "",
                input_ref=rec.input_ref or f"odoo:wuchang.business.backend.optimization:{rec.id or 'new'}:signal_trend",
            )
            rec.write(
                {
                    "signal_trend_review_json": json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True),
                    "signal_trend_next_actions": "\n".join(packet.get("next_actions", [])),
                    "regressing_signal_count": len(packet.get("regressing_signal_types", [])),
                    "insufficient_signal_count": len(packet.get("insufficient_signal_types", [])),
                    "production_activation_ready": packet.get("production_activation_ready") is True,
                    **rec._false_side_effect_values(),
                }
            )

    def _safe_json_loads(self, value):
        try:
            parsed = json.loads(value or "{}")
        except (TypeError, ValueError):
            parsed = {}
        return parsed if isinstance(parsed, dict) else {}

    def action_build_management_decision_queue(self):
        for rec in self:
            rec._assert_no_secret_material()
            existing_status = {
                item.decision_key: item.operator_status
                for item in rec.management_decision_item_ids
                if item.decision_key
            }
            packet = build_business_backend_management_decision_queue_packet(
                signal_trend_packet=rec._safe_json_loads(rec.signal_trend_review_json),
                readiness_scorecard_packet=rec._safe_json_loads(rec.readiness_scorecard_json),
                operating_review_packet=rec._safe_json_loads(rec.operating_review_json),
                actor_ref=rec.actor_ref or "",
                input_ref=rec.input_ref or f"odoo:wuchang.business.backend.optimization:{rec.id or 'new'}:management_decision_queue",
            )
            counts = packet.get("counts_by_priority", {})
            decision_commands = [(5, 0, 0)]
            for index, item in enumerate(packet.get("decision_items", []), start=1):
                decision_key = item.get("decision_key", "")
                decision_commands.append(
                    (
                        0,
                        0,
                        {
                            "sequence": index,
                            "decision_key": decision_key,
                            "source": item.get("source", ""),
                            "priority": item.get("priority", "medium"),
                            "title": item.get("title", ""),
                            "recommended_action": item.get("recommended_action", ""),
                            "operator_status": existing_status.get(decision_key, "todo"),
                        },
                    )
                )
            rec.write(
                {
                    "management_decision_queue_json": json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True),
                    "management_decision_next_actions": "\n".join(packet.get("next_actions", [])),
                    "management_decision_item_ids": decision_commands,
                    "management_decision_count": packet.get("decision_count", 0),
                    "critical_decision_count": counts.get("critical", 0),
                    "high_decision_count": counts.get("high", 0),
                    "production_activation_ready": packet.get("production_activation_ready") is True,
                    **rec._false_side_effect_values(),
                }
            )

    def action_build_readiness_scorecard(self):
        for rec in self:
            rec._assert_no_secret_material()
            checklist_items = [
                {
                    "panel": item.panel,
                    "item_key": item.item_key,
                    "operator_status": item.operator_status,
                }
                for item in rec.checklist_item_ids
            ]
            kpi_snapshots = [
                {
                    "snapshot_type": snapshot.snapshot_type,
                    "state": snapshot.state,
                }
                for snapshot in rec.kpi_snapshot_ids
            ]
            improvement_items = [
                {
                    "stage_key": item.stage_key,
                    "improvement_key": item.improvement_key,
                    "priority": item.priority,
                    "operator_status": item.operator_status,
                }
                for item in rec.improvement_item_ids
            ]
            packet = build_business_backend_readiness_scorecard_packet(
                checklist_items=checklist_items,
                kpi_snapshots=kpi_snapshots,
                improvement_items=improvement_items,
                actor_ref=rec.actor_ref or "",
                input_ref=rec.input_ref or f"odoo:wuchang.business.backend.optimization:{rec.id or 'new'}:readiness_scorecard",
            )
            rec.write(
                {
                    "readiness_scorecard_json": json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True),
                    "readiness_scorecard_next_actions": "\n".join(packet.get("next_actions", [])),
                    "readiness_activation_blockers": "\n".join(packet.get("activation_blockers", [])),
                    "ai_merchant_readiness_score": packet.get("readiness_score", 0.0),
                    "blocked_checklist_count": packet.get("blocked_checklist_count", 0),
                    "needs_action_kpi_count": packet.get("needs_action_kpi_count", 0),
                    "blocked_improvement_count": packet.get("blocked_improvement_count", 0),
                    "critical_open_improvement_count": packet.get("critical_open_improvement_count", 0),
                    "production_activation_ready": packet.get("production_activation_ready") is True,
                    **rec._false_side_effect_values(),
                }
            )

    def action_build_operating_review(self):
        for rec in self:
            rec._assert_no_secret_material()
            checklist_items = [
                {
                    "panel": item.panel,
                    "item_key": item.item_key,
                    "title": item.title,
                    "required_ref": item.required_ref,
                    "operator_status": item.operator_status,
                }
                for item in rec.checklist_item_ids
            ]
            kpi_snapshots = [
                {
                    "snapshot_type": snapshot.snapshot_type,
                    "state": snapshot.state,
                    "evidence_ref": snapshot.evidence_ref,
                    "summary": snapshot.summary,
                }
                for snapshot in rec.kpi_snapshot_ids
            ]
            packet = build_business_backend_operating_review_packet(
                checklist_items=checklist_items,
                kpi_snapshots=kpi_snapshots,
                actor_ref=rec.actor_ref or "",
                input_ref=rec.input_ref or f"odoo:wuchang.business.backend.optimization:{rec.id or 'new'}:operating_review",
            )
            rec.write(
                {
                    "operating_review_json": json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True),
                    "operating_review_next_actions": "\n".join(packet.get("next_actions", [])),
                    "blocked_checklist_count": len(packet.get("blocked_checklist_items", [])),
                    "needs_action_kpi_count": len(packet.get("needs_action_kpis", [])),
                    "production_activation_ready": packet.get("production_activation_ready") is True,
                    **rec._false_side_effect_values(),
                }
            )

    def action_dead_letter(self):
        for rec in self:
            rec.write(
                {
                    "state": "dead_letter",
                    "production_activation_ready": False,
                    "blocked_checklist_count": 0,
                    "needs_action_kpi_count": 0,
                    "improvement_item_count": 0,
                    "critical_improvement_count": 0,
                    "ai_merchant_readiness_score": 0.0,
                    "blocked_improvement_count": 0,
                    "critical_open_improvement_count": 0,
                    "daily_signal_count": 0,
                    "daily_signal_needs_action_count": 0,
                    "daily_signal_observed_day_count": 0,
                    "regressing_signal_count": 0,
                    "insufficient_signal_count": 0,
                    "management_decision_count": 0,
                    "critical_decision_count": 0,
                    "high_decision_count": 0,
                    "operator_runbook_step_count": 0,
                    "operator_runbook_daily_step_count": 0,
                    "operator_runbook_weekly_step_count": 0,
                    "av_candidate_count": 0,
                    "low_confidence_candidate_count": 0,
                    "failed_validation_candidate_count": 0,
                    "generated_image_hold_count": 0,
                    "staff_review_required_candidate_count": 0,
                    "product_quality_count": 0,
                    "product_quality_ready_count": 0,
                    "product_quality_blocked_count": 0,
                    "missing_custom_options_count": 0,
                    "missing_photo_evidence_count": 0,
                    "checkout_preflight_count": 0,
                    "checkout_preflight_ready_count": 0,
                    "checkout_preflight_blocked_count": 0,
                    **rec._false_side_effect_values(),
                }
            )


class WuchangBusinessBackendOptimizationItem(models.Model):
    _name = "wuchang.business.backend.optimization.item"
    _description = "WuChang Business Backend Optimization Checklist Item"
    _order = "optimization_id desc, sequence, id"

    optimization_id = fields.Many2one(
        "wuchang.business.backend.optimization",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    panel = fields.Char(readonly=True, index=True)
    item_key = fields.Char(readonly=True, index=True)
    title = fields.Char(readonly=True)
    required_ref = fields.Char(readonly=True)
    success_metric = fields.Text(readonly=True)
    phase = fields.Char(readonly=True, default="P1_REVIEW")
    operator_status = fields.Selection(
        [
            ("todo", "To Do"),
            ("in_progress", "In Progress"),
            ("blocked", "Blocked"),
            ("ready_for_review", "Ready For Review"),
            ("done", "Done"),
        ],
        default="todo",
        index=True,
    )
    operator_note = fields.Text(help="Safe operator note. Use refs and summaries only.")

    @api.constrains("operator_note")
    def _check_operator_note_boundaries(self):
        checker = self.env["wuchang.business.backend.optimization"]
        for rec in self:
            if checker._contains_secret_shape(rec.operator_note):
                raise UserError(_("Secret-shaped or plaintext-shaped material is not allowed. Use refs only."))


class WuchangBusinessBackendImprovementItem(models.Model):
    _name = "wuchang.business.backend.improvement.item"
    _description = "WuChang Business Backend Process Improvement Item"
    _order = "optimization_id desc, sequence, id"

    optimization_id = fields.Many2one(
        "wuchang.business.backend.optimization",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    stage_key = fields.Char(readonly=True, index=True)
    improvement_key = fields.Char(readonly=True, index=True)
    title = fields.Char(readonly=True)
    priority = fields.Selection(
        [
            ("critical", "Critical"),
            ("high", "High"),
            ("medium", "Medium"),
            ("low", "Low"),
        ],
        default="medium",
        readonly=True,
        index=True,
    )
    owner_scope = fields.Char(readonly=True, index=True)
    kpi_type = fields.Char(readonly=True)
    success_metric = fields.Text(readonly=True)
    operator_status = fields.Selection(
        [
            ("todo", "To Do"),
            ("in_progress", "In Progress"),
            ("blocked", "Blocked"),
            ("ready_for_review", "Ready For Review"),
            ("done", "Done"),
        ],
        default="todo",
        index=True,
    )
    operator_note = fields.Text(help="Safe improvement note. Use refs and summaries only.")

    @api.constrains("operator_note")
    def _check_operator_note_boundaries(self):
        checker = self.env["wuchang.business.backend.optimization"]
        for rec in self:
            if checker._contains_secret_shape(rec.operator_note):
                raise UserError(_("Secret-shaped or plaintext-shaped material is not allowed. Use refs only."))


class WuchangBusinessBackendDailySignal(models.Model):
    _name = "wuchang.business.backend.daily.signal"
    _description = "WuChang Business Backend Daily Operating Signal"
    _order = "optimization_id desc, signal_date desc, sequence, id"

    optimization_id = fields.Many2one(
        "wuchang.business.backend.optimization",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    signal_date = fields.Date(default=fields.Date.context_today, index=True)
    signal_type = fields.Selection(
        [
            ("order_count_signal", "Order Count Signal"),
            ("revenue_signal", "Revenue Signal"),
            ("unresolved_candidate_count", "Unresolved Candidate Count"),
            ("line_incident_count", "LINE Incident Count"),
            ("course_income_signal", "Course Income Signal"),
            ("operator_burden_hours", "Operator Burden Hours"),
            ("manual_fallback_status", "Manual Fallback Status"),
        ],
        required=True,
        index=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("observed", "Observed"),
            ("needs_action", "Needs Action"),
            ("ready_for_review", "Ready For Review"),
        ],
        default="draft",
        index=True,
    )
    numeric_value = fields.Float(help="Safe aggregate number only. Do not enter payment card, member, secret, or raw media data.")
    unit = fields.Char(help="Examples: count, NTD, hours, yes_no.")
    summary = fields.Text(help="Safe daily summary only. No member plaintext, payment card data, tokens, raw audio, or raw video.")
    evidence_ref = fields.Char(help="Opaque evidence ref, daily close ref, or packet hash only.")

    external_api_call = fields.Boolean(default=False, readonly=True)
    formal_pos_write = fields.Boolean(default=False, readonly=True)
    payment_capture = fields.Boolean(default=False, readonly=True)
    secret_read = fields.Boolean(default=False, readonly=True)
    member_plaintext_read = fields.Boolean(default=False, readonly=True)
    raw_audio_saved = fields.Boolean(default=False, readonly=True)
    raw_video_saved = fields.Boolean(default=False, readonly=True)

    @api.constrains("summary", "evidence_ref", "unit")
    def _check_daily_signal_boundaries(self):
        checker = self.env["wuchang.business.backend.optimization"]
        for rec in self:
            if any(checker._contains_secret_shape(value) for value in [rec.summary, rec.evidence_ref, rec.unit]):
                raise UserError(_("Secret-shaped or plaintext-shaped material is not allowed in daily signals. Use refs only."))


class WuchangBusinessBackendAvCandidate(models.Model):
    _name = "wuchang.business.backend.av.candidate"
    _description = "WuChang Business Backend AV AI Candidate"
    _order = "optimization_id desc, sequence, id"

    optimization_id = fields.Many2one(
        "wuchang.business.backend.optimization",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    candidate_ref = fields.Char(required=True, index=True, help="Opaque candidate ref only. Do not paste transcript or raw media.")
    modality = fields.Selection(
        [
            ("audio_intent", "Audio Intent"),
            ("video_product_recognition", "Video Product Recognition"),
            ("menu_text_candidate", "Menu Text Candidate"),
            ("product_image_candidate", "Product Image Candidate"),
            ("multimodal_order_candidate", "Multimodal Order Candidate"),
        ],
        default="multimodal_order_candidate",
        required=True,
        index=True,
    )
    review_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("needs_staff_review", "Needs Staff Review"),
            ("ready_for_odoo_validation", "Ready For Odoo Validation"),
            ("odoo_validation_failed", "Odoo Validation Failed"),
            ("staff_rejected", "Staff Rejected"),
            ("staff_approved_candidate", "Staff Approved Candidate"),
        ],
        default="draft",
        index=True,
    )
    confidence_score = fields.Float(help="0.0 to 1.0 candidate confidence. Below 0.75 requires staff review.")
    odoo_validation_state = fields.Selection(
        [
            ("not_checked", "Not Checked"),
            ("passed", "Passed"),
            ("failed", "Failed"),
            ("needs_staff_review", "Needs Staff Review"),
        ],
        default="not_checked",
        index=True,
    )
    product_photo_evidence_state = fields.Selection(
        [
            ("missing", "Missing"),
            ("real_photo_ref", "Real Photo Ref"),
            ("staff_approved_photo_ref", "Staff Approved Photo Ref"),
            ("generated_candidate_only", "Generated Candidate Only"),
        ],
        default="missing",
        index=True,
    )
    red_flags = fields.Text(
        help="One safe red flag per line, for example low_confidence or price_mismatch. No transcript, member plaintext, tokens, raw audio, or raw video."
    )
    evidence_ref = fields.Char(help="Opaque evidence ref or packet hash only.")
    operator_note = fields.Text(help="Safe candidate note. Use refs and summaries only.")

    external_api_call = fields.Boolean(default=False, readonly=True)
    model_invocation = fields.Boolean(default=False, readonly=True)
    formal_pos_write = fields.Boolean(default=False, readonly=True)
    payment_capture = fields.Boolean(default=False, readonly=True)
    formal_line_message_send = fields.Boolean(default=False, readonly=True)
    secret_read = fields.Boolean(default=False, readonly=True)
    member_plaintext_read = fields.Boolean(default=False, readonly=True)
    raw_audio_saved = fields.Boolean(default=False, readonly=True)
    raw_video_saved = fields.Boolean(default=False, readonly=True)

    @api.constrains("candidate_ref", "red_flags", "evidence_ref", "operator_note")
    def _check_av_candidate_boundaries(self):
        checker = self.env["wuchang.business.backend.optimization"]
        for rec in self:
            if any(checker._contains_secret_shape(value) for value in [rec.candidate_ref, rec.red_flags, rec.evidence_ref, rec.operator_note]):
                raise UserError(_("Secret-shaped or plaintext-shaped material is not allowed in AV AI candidates. Use refs only."))


class WuchangBusinessBackendProductQuality(models.Model):
    _name = "wuchang.business.backend.product.quality"
    _description = "WuChang Business Backend Product/Menu Quality Item"
    _order = "optimization_id desc, sequence, id"

    optimization_id = fields.Many2one(
        "wuchang.business.backend.optimization",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    product_ref = fields.Char(required=True, index=True, help="Opaque product ref only. Do not paste customer data or vendor secrets.")
    odoo_product_ref = fields.Char(help="Opaque Odoo product authority ref.")
    menu_category_ref = fields.Char(help="Opaque menu/category ref.")
    price_ref = fields.Char(help="Opaque price/version authority ref.")
    custom_options_ref = fields.Char(help="Opaque Custom Options JSON ref.")
    photo_evidence_ref = fields.Char(help="Real or staff-approved product photo evidence ref.")
    photo_evidence_state = fields.Selection(
        [
            ("missing", "Missing"),
            ("real_photo_ref", "Real Photo Ref"),
            ("staff_approved_photo_ref", "Staff Approved Photo Ref"),
            ("generated_image_only", "Generated Image Only"),
        ],
        default="missing",
        index=True,
    )
    availability_state = fields.Selection(
        [
            ("available", "Available"),
            ("limited", "Limited"),
            ("inactive", "Inactive"),
            ("unknown", "Unknown"),
        ],
        default="unknown",
        index=True,
    )
    ai_candidate_state = fields.Selection(
        [
            ("allowed_candidate", "Allowed Candidate"),
            ("staff_review_required", "Staff Review Required"),
            ("blocked", "Blocked"),
        ],
        default="blocked",
        index=True,
    )
    operator_note = fields.Text(help="Safe product/menu note. Use refs and summaries only.")

    external_api_call = fields.Boolean(default=False, readonly=True)
    formal_pos_write = fields.Boolean(default=False, readonly=True)
    payment_capture = fields.Boolean(default=False, readonly=True)
    secret_read = fields.Boolean(default=False, readonly=True)
    member_plaintext_read = fields.Boolean(default=False, readonly=True)
    raw_audio_saved = fields.Boolean(default=False, readonly=True)
    raw_video_saved = fields.Boolean(default=False, readonly=True)

    @api.constrains(
        "product_ref",
        "odoo_product_ref",
        "menu_category_ref",
        "price_ref",
        "custom_options_ref",
        "photo_evidence_ref",
        "operator_note",
    )
    def _check_product_quality_boundaries(self):
        checker = self.env["wuchang.business.backend.optimization"]
        for rec in self:
            values = [
                rec.product_ref,
                rec.odoo_product_ref,
                rec.menu_category_ref,
                rec.price_ref,
                rec.custom_options_ref,
                rec.photo_evidence_ref,
                rec.operator_note,
            ]
            if any(checker._contains_secret_shape(value) for value in values):
                raise UserError(_("Secret-shaped or plaintext-shaped material is not allowed in product quality items. Use refs only."))


class WuchangBusinessBackendCheckoutPreflight(models.Model):
    _name = "wuchang.business.backend.checkout.preflight"
    _description = "WuChang Business Backend Member Voucher Payment Preflight"
    _order = "optimization_id desc, sequence, id"

    optimization_id = fields.Many2one(
        "wuchang.business.backend.optimization",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    candidate_order_ref = fields.Char(required=True, index=True, help="Opaque candidate order ref only.")
    member_ref = fields.Char(help="Opaque member ref only. Do not paste name, phone, email, or identity number.")
    consent_ref = fields.Char(help="Opaque consent or member policy ref.")
    voucher_dry_run_ref = fields.Char(help="Opaque voucher dry-run ref; no real redemption in P1.")
    payment_method_ref = fields.Char(help="Opaque payment method/precondition ref; no payment capture in P1.")
    pos_draft_ref = fields.Char(help="Opaque POS draft/candidate ref; no POS write in P1.")
    preflight_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("ready_for_human_checkout_review", "Ready For Human Checkout Review"),
            ("voucher_conflict", "Voucher Conflict"),
            ("payment_failed", "Payment Precondition Failed"),
            ("member_plaintext_risk", "Member Plaintext Risk"),
            ("blocked", "Blocked"),
        ],
        default="draft",
        index=True,
    )
    requested_mutation = fields.Boolean(
        default=False,
        help="Must remain false in P1. True means someone requested POS/payment/voucher/member mutation.",
    )
    operator_note = fields.Text(help="Safe checkout preflight note. Use refs and summaries only.")

    external_api_call = fields.Boolean(default=False, readonly=True)
    formal_pos_write = fields.Boolean(default=False, readonly=True)
    payment_capture = fields.Boolean(default=False, readonly=True)
    voucher_redemption = fields.Boolean(default=False, readonly=True)
    formal_member_registration = fields.Boolean(default=False, readonly=True)
    secret_read = fields.Boolean(default=False, readonly=True)
    member_plaintext_read = fields.Boolean(default=False, readonly=True)
    raw_audio_saved = fields.Boolean(default=False, readonly=True)
    raw_video_saved = fields.Boolean(default=False, readonly=True)

    @api.constrains(
        "candidate_order_ref",
        "member_ref",
        "consent_ref",
        "voucher_dry_run_ref",
        "payment_method_ref",
        "pos_draft_ref",
        "operator_note",
    )
    def _check_checkout_preflight_boundaries(self):
        checker = self.env["wuchang.business.backend.optimization"]
        for rec in self:
            values = [
                rec.candidate_order_ref,
                rec.member_ref,
                rec.consent_ref,
                rec.voucher_dry_run_ref,
                rec.payment_method_ref,
                rec.pos_draft_ref,
                rec.operator_note,
            ]
            if any(checker._contains_secret_shape(value) for value in values):
                raise UserError(_("Secret-shaped or plaintext-shaped material is not allowed in checkout preflights. Use refs only."))


class WuchangBusinessBackendManagementDecisionItem(models.Model):
    _name = "wuchang.business.backend.management.decision.item"
    _description = "WuChang Business Backend Management Decision Item"
    _order = "optimization_id desc, sequence, id"

    optimization_id = fields.Many2one(
        "wuchang.business.backend.optimization",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    decision_key = fields.Char(readonly=True, index=True)
    source = fields.Char(readonly=True, index=True)
    priority = fields.Selection(
        [
            ("critical", "Critical"),
            ("high", "High"),
            ("medium", "Medium"),
            ("low", "Low"),
        ],
        default="medium",
        readonly=True,
        index=True,
    )
    title = fields.Char(readonly=True)
    recommended_action = fields.Text(readonly=True)
    operator_status = fields.Selection(
        [
            ("todo", "To Do"),
            ("in_progress", "In Progress"),
            ("blocked", "Blocked"),
            ("ready_for_review", "Ready For Review"),
            ("done", "Done"),
        ],
        default="todo",
        index=True,
    )
    owner_scope = fields.Char(help="Safe owner scope only, for example cafe_operations or line_domain_api_control.")
    due_date = fields.Date(index=True)
    evidence_ref = fields.Char(help="Opaque evidence ref or packet hash only.")
    operator_note = fields.Text(help="Safe decision note. Use refs and summaries only.")

    @api.constrains("owner_scope", "evidence_ref", "operator_note")
    def _check_decision_boundaries(self):
        checker = self.env["wuchang.business.backend.optimization"]
        for rec in self:
            if any(checker._contains_secret_shape(value) for value in [rec.owner_scope, rec.evidence_ref, rec.operator_note]):
                raise UserError(_("Secret-shaped or plaintext-shaped material is not allowed in decision items. Use refs only."))


class WuchangBusinessBackendKpiSnapshot(models.Model):
    _name = "wuchang.business.backend.kpi.snapshot"
    _description = "WuChang Business Backend KPI Snapshot"
    _order = "optimization_id desc, snapshot_date desc, sequence, id"

    optimization_id = fields.Many2one(
        "wuchang.business.backend.optimization",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    snapshot_date = fields.Date(default=fields.Date.context_today, index=True)
    snapshot_type = fields.Selection(
        [
            ("daily_revenue_reconciliation", "Daily Revenue Reconciliation"),
            ("av_ai_candidate_quality", "AV AI Candidate Quality"),
            ("staff_correction_queue", "Staff Correction Queue"),
            ("course_to_member_conversion", "Course To Member Conversion"),
            ("sanchong_demo_signal", "Sanchong Demo Signal"),
            ("operator_burden", "Operator Burden"),
            ("release_blocker_count", "Release Blocker Count"),
        ],
        required=True,
        index=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("observed", "Observed"),
            ("needs_action", "Needs Action"),
            ("ready_for_review", "Ready For Review"),
        ],
        default="draft",
        index=True,
    )
    numeric_value = fields.Float(help="Safe numeric KPI value. Do not enter member, payment, or secret data.")
    target_value = fields.Float(help="Safe target value for comparison.")
    unit = fields.Char(help="Examples: NTD, count, percent, hours.")
    summary = fields.Text(help="Safe summary only. No member plaintext, payment card data, tokens, raw audio, or raw video.")
    evidence_ref = fields.Char(help="Opaque evidence ref or packet hash only.")

    external_api_call = fields.Boolean(default=False, readonly=True)
    formal_pos_write = fields.Boolean(default=False, readonly=True)
    payment_capture = fields.Boolean(default=False, readonly=True)
    secret_read = fields.Boolean(default=False, readonly=True)
    member_plaintext_read = fields.Boolean(default=False, readonly=True)
    raw_audio_saved = fields.Boolean(default=False, readonly=True)
    raw_video_saved = fields.Boolean(default=False, readonly=True)

    @api.constrains("summary", "evidence_ref", "unit")
    def _check_kpi_boundaries(self):
        checker = self.env["wuchang.business.backend.optimization"]
        for rec in self:
            if any(checker._contains_secret_shape(value) for value in [rec.summary, rec.evidence_ref, rec.unit]):
                raise UserError(_("Secret-shaped or plaintext-shaped material is not allowed in KPI snapshots. Use refs only."))
