"""P1-safe business backend optimization packet builder.

The builder emits an operator review packet for backend management
enhancements. It does not call external APIs, write POS orders, capture
payments, send LINE messages, read secrets, or store raw audio/video.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


RECOMMENDED_BACKEND_PANELS = [
    "business_continuity_cockpit",
    "av_ai_merchant_quality_panel",
    "menu_product_custom_option_control",
    "line_domain_api_control_plane",
    "financial_sustainability_panel",
    "sanchong_demonstration_self_funding_panel",
    "founder_mission_sustainability_panel",
    "release_gate_board",
    "staff_correction_queue",
]

END_TO_END_FLOW = [
    "inquiry_or_order_intent_received",
    "av_ai_candidate_capture",
    "structured_order_candidate",
    "odoo_authority_validation",
    "operator_review_or_staff_correction",
    "manual_or_released_pos_confirmation",
    "payment_voucher_member_gate",
    "line_lineworks_candidate_or_released_notification",
    "daily_revenue_and_incident_reconciliation",
    "total_field_evaluation_packet",
]

AI_TECHNOLOGY_FEATURES = [
    "audio_intent_candidate",
    "video_or_product_recognition_candidate",
    "anti_hallucination_gate",
    "odoo_authority_node",
    "custom_options_json",
    "staff_correction_feedback_loop",
    "local_discrete_verifier",
    "candidate_only_cloud_model",
    "risk_flag_extraction",
    "evidence_hash_packet",
]

AV_AI_CANDIDATE_MODALITIES = [
    "audio_intent",
    "video_product_recognition",
    "menu_text_candidate",
    "product_image_candidate",
    "multimodal_order_candidate",
]

AV_AI_CANDIDATE_REVIEW_STATES = [
    "draft",
    "needs_staff_review",
    "ready_for_odoo_validation",
    "odoo_validation_failed",
    "staff_rejected",
    "staff_approved_candidate",
]

AV_AI_CANDIDATE_RED_FLAGS = [
    "low_confidence",
    "menu_item_not_found",
    "custom_option_unmapped",
    "price_mismatch",
    "allergy_or_safety_risk",
    "payment_or_voucher_request",
    "member_plaintext_risk",
    "generated_image_not_product_evidence",
    "raw_media_storage_risk",
]

PRODUCT_MENU_QUALITY_FIELDS = [
    "product_ref",
    "odoo_product_ref",
    "menu_category_ref",
    "price_ref",
    "custom_options_ref",
    "photo_evidence_ref",
    "availability_state",
    "ai_candidate_state",
]

PRODUCT_MENU_REQUIRED_REFS = [
    "odoo_product_ref",
    "price_ref",
    "custom_options_ref",
    "photo_evidence_ref",
]

PRODUCT_MENU_BLOCKER_TYPES = [
    "missing_odoo_product_ref",
    "missing_price_ref",
    "missing_custom_options_ref",
    "missing_photo_evidence_ref",
    "generated_image_only",
    "inactive_or_unavailable",
    "ai_candidate_not_allowed",
]

MEMBER_VOUCHER_PAYMENT_PREFLIGHT_FIELDS = [
    "candidate_order_ref",
    "member_ref",
    "voucher_dry_run_ref",
    "payment_method_ref",
    "pos_draft_ref",
    "consent_ref",
    "preflight_state",
]

MEMBER_VOUCHER_PAYMENT_BLOCKER_TYPES = [
    "missing_candidate_order_ref",
    "missing_member_ref",
    "missing_consent_ref",
    "missing_voucher_dry_run_ref",
    "missing_payment_method_ref",
    "missing_pos_draft_ref",
    "voucher_conflict",
    "payment_precondition_failed",
    "member_plaintext_risk",
    "production_mutation_requested",
]

BACKEND_CHECKLIST_ITEMS = [
    {
        "panel": "business_continuity_cockpit",
        "item_key": "manual_order_fallback",
        "title": "Manual order fallback is documented and visible",
        "required_ref": "manual_order_fallback_ref",
        "success_metric": "Staff can continue taking orders when AI/LINE/API automation is held.",
        "phase": "P1_REVIEW",
    },
    {
        "panel": "business_continuity_cockpit",
        "item_key": "daily_revenue_reconciliation",
        "title": "Daily revenue reconciliation is tracked",
        "required_ref": "daily_revenue_reconciliation_ref",
        "success_metric": "Manual orders, POS records, LINE incidents, and course income can be reconciled daily.",
        "phase": "P1_REVIEW",
    },
    {
        "panel": "av_ai_merchant_quality_panel",
        "item_key": "low_confidence_staff_review",
        "title": "Low-confidence AV AI candidates go to staff review",
        "required_ref": "demo_success_metric_ref",
        "success_metric": "Low-confidence voice/video/menu candidates never become POS writes without staff confirmation.",
        "phase": "P1_REVIEW",
    },
    {
        "panel": "av_ai_merchant_quality_panel",
        "item_key": "staff_correction_feedback_loop",
        "title": "Staff corrections become safe improvement evidence",
        "required_ref": "lost_order_prevention_ref",
        "success_metric": "AI mistakes are captured as non-plaintext correction evidence for future tuning.",
        "phase": "P1_REVIEW",
    },
    {
        "panel": "menu_product_custom_option_control",
        "item_key": "custom_options_json_coverage",
        "title": "Custom Options JSON coverage is visible",
        "required_ref": "existing_pos_continuity_ref",
        "success_metric": "Sweetness, ice, temperature, size, toppings, and service notes map to structured options.",
        "phase": "P1_REVIEW",
    },
    {
        "panel": "line_domain_api_control_plane",
        "item_key": "cafe_subdomain_gateway",
        "title": "Cafe endpoint uses association-approved subdomain and gateway",
        "required_ref": "cafe_subdomain_ref",
        "success_metric": "Webhook/callback/landing endpoints do not use unapproved independent domains.",
        "phase": "P1_REVIEW",
    },
    {
        "panel": "line_domain_api_control_plane",
        "item_key": "vendor_access_review",
        "title": "Vendor/API control risk has review refs",
        "required_ref": "vendor_access_review_ref",
        "success_metric": "Vendor-controlled API cannot write POS, payment, member, or LINE send surfaces.",
        "phase": "P1_REVIEW",
    },
    {
        "panel": "financial_sustainability_panel",
        "item_key": "debt_reduction_plan",
        "title": "Debt reduction plan is tracked",
        "required_ref": "debt_reduction_plan_ref",
        "success_metric": "New automation or vendor costs are not approved without debt and revenue recovery review.",
        "phase": "P1_REVIEW",
    },
    {
        "panel": "financial_sustainability_panel",
        "item_key": "course_cost_allocation",
        "title": "Course cost allocation is visible",
        "required_ref": "course_cost_allocation_ref",
        "success_metric": "Association course expansion cost is not silently absorbed by cafe cashflow.",
        "phase": "P1_REVIEW",
    },
    {
        "panel": "sanchong_demonstration_self_funding_panel",
        "item_key": "demo_success_metric",
        "title": "Sanchong demo success metric is defined",
        "required_ref": "demo_success_metric_ref",
        "success_metric": "Small visible wins are measured before expecting full community self-funding.",
        "phase": "P1_REVIEW",
    },
    {
        "panel": "founder_mission_sustainability_panel",
        "item_key": "operator_burden_reduction",
        "title": "Operator burden reduction is tracked",
        "required_ref": "operator_burden_reduction_ref",
        "success_metric": "Mission continuity does not depend on one person absorbing unbounded debt/labor/risk.",
        "phase": "P1_REVIEW",
    },
    {
        "panel": "release_gate_board",
        "item_key": "release_gate_board",
        "title": "Release gate board separates P1 review from activation",
        "required_ref": "public_service_continuity_ref",
        "success_metric": "Candidate, human refs pending, ready for review, and activation packet states are visible.",
        "phase": "P1_REVIEW",
    },
]

KPI_SNAPSHOT_TYPES = [
    "daily_revenue_reconciliation",
    "av_ai_candidate_quality",
    "staff_correction_queue",
    "course_to_member_conversion",
    "sanchong_demo_signal",
    "operator_burden",
    "release_blocker_count",
]

DAILY_SIGNAL_TYPES = [
    "order_count_signal",
    "revenue_signal",
    "unresolved_candidate_count",
    "line_incident_count",
    "course_income_signal",
    "operator_burden_hours",
    "manual_fallback_status",
]

SIGNAL_TREND_DIRECTIONS = {
    "order_count_signal": "higher_is_better",
    "revenue_signal": "higher_is_better",
    "unresolved_candidate_count": "lower_is_better",
    "line_incident_count": "lower_is_better",
    "course_income_signal": "higher_is_better",
    "operator_burden_hours": "lower_is_better",
    "manual_fallback_status": "higher_is_better",
}

PROCESS_WALKTHROUGH_STEPS = [
    {
        "sequence": 10,
        "stage_key": "customer_inquiry_entry",
        "stage_title": "Customer inquiry and order entry",
        "expected_control": "Separate in-store, LINE, manual, and future AV AI entry channels while keeping manual service available.",
        "improvement_key": "unified_entry_intake_board",
        "improvement_title": "Create a unified intake board for manual, LINE, and AV AI candidate entries",
        "priority": "high",
        "owner_scope": "cafe_operations",
        "kpi_type": "daily_revenue_reconciliation",
    },
    {
        "sequence": 20,
        "stage_key": "av_ai_candidate_capture",
        "stage_title": "AV AI candidate capture",
        "expected_control": "Capture voice/video intent as candidate metadata only, without raw audio/video storage in P1.",
        "improvement_key": "av_candidate_confidence_and_red_flag_panel",
        "improvement_title": "Expose confidence, missing menu match, allergy, price, and payment red flags before staff review",
        "priority": "high",
        "owner_scope": "ai_quality",
        "kpi_type": "av_ai_candidate_quality",
    },
    {
        "sequence": 30,
        "stage_key": "structured_order_candidate",
        "stage_title": "Structured order candidate",
        "expected_control": "Normalize item, quantity, custom options, notes, and risk flags before Odoo authority validation.",
        "improvement_key": "custom_options_json_mapping_queue",
        "improvement_title": "Track unmapped sweetness, ice, temperature, size, topping, and service-note options",
        "priority": "medium",
        "owner_scope": "product_menu",
        "kpi_type": "staff_correction_queue",
    },
    {
        "sequence": 40,
        "stage_key": "odoo_authority_validation",
        "stage_title": "Odoo authority validation",
        "expected_control": "Odoo validates menu, price, availability, member, voucher, and payment preconditions.",
        "improvement_key": "authority_validation_failure_reasons",
        "improvement_title": "Record safe validation failure reasons so repeated AI/menu mismatches can be corrected",
        "priority": "high",
        "owner_scope": "odoo_authority",
        "kpi_type": "staff_correction_queue",
    },
    {
        "sequence": 50,
        "stage_key": "staff_confirmation",
        "stage_title": "Staff confirmation and correction",
        "expected_control": "Human staff confirms, edits, or rejects candidates before any formal POS or payment action.",
        "improvement_key": "staff_correction_resolution_sla",
        "improvement_title": "Add staff correction status and aging so candidate queues do not become lost orders",
        "priority": "high",
        "owner_scope": "cafe_operations",
        "kpi_type": "staff_correction_queue",
    },
    {
        "sequence": 60,
        "stage_key": "pos_payment_voucher_gate",
        "stage_title": "POS, payment, voucher, and member gate",
        "expected_control": "Keep POS write, payment capture, voucher redemption, and member mutation manual or separately released.",
        "improvement_key": "release_gate_blocker_board",
        "improvement_title": "Show release blockers by POS, payment, voucher, member, LINE send, and gateway domains",
        "priority": "critical",
        "owner_scope": "release_governance",
        "kpi_type": "release_blocker_count",
    },
    {
        "sequence": 70,
        "stage_key": "line_lineworks_notification",
        "stage_title": "LINE / LINE WORKS candidate notification",
        "expected_control": "Separate association and cafe LINE scopes; keep formal sends blocked until refs and activation packet pass.",
        "improvement_key": "line_subject_scope_dashboard",
        "improvement_title": "Display association OA, cafe OA, subdomain, webhook, callback, and relay refs in one scope dashboard",
        "priority": "critical",
        "owner_scope": "line_domain_api_control",
        "kpi_type": "release_blocker_count",
    },
    {
        "sequence": 80,
        "stage_key": "daily_close_reconciliation",
        "stage_title": "Daily close reconciliation",
        "expected_control": "Reconcile manual orders, POS records, LINE incidents, course income, expenses, and operator burden daily.",
        "improvement_key": "daily_close_reconciliation_packet",
        "improvement_title": "Create a daily close packet with revenue signal, incidents, course income, and unresolved blockers",
        "priority": "high",
        "owner_scope": "financial_sustainability",
        "kpi_type": "daily_revenue_reconciliation",
    },
    {
        "sequence": 90,
        "stage_key": "sanchong_demo_loop",
        "stage_title": "Sanchong demonstration loop",
        "expected_control": "Turn small visible results into trust, course conversion, cafe revenue signal, and self-funding trigger evidence.",
        "improvement_key": "demo_to_self_funding_trigger_tracker",
        "improvement_title": "Track demo wins, course-to-member conversion, cafe revenue signals, and community self-funding triggers",
        "priority": "medium",
        "owner_scope": "local_demonstration",
        "kpi_type": "sanchong_demo_signal",
    },
    {
        "sequence": 100,
        "stage_key": "total_field_packet_review",
        "stage_title": "Total-field packet review",
        "expected_control": "Send evidence hashes and refs for evaluation without secrets, plaintext member data, raw audio, or raw video.",
        "improvement_key": "evidence_hash_and_ref_readiness",
        "improvement_title": "Keep total-field evidence hashes, required refs, and missing review items visible for decision",
        "priority": "medium",
        "owner_scope": "total_field_evaluation",
        "kpi_type": "release_blocker_count",
    },
]

OPERATOR_RUNBOOK_STEPS = [
    {
        "sequence": 10,
        "phase": "opening_check",
        "title": "Opening business continuity check",
        "required_action": "Confirm manual ordering, manual payment, existing POS, LINE manual service, and rollback refs before service starts.",
        "expected_output_ref": "manual_order_fallback_ref",
        "cadence": "daily_open",
        "owner_scope": "cafe_operations",
    },
    {
        "sequence": 20,
        "phase": "pre_service_ai_gate_check",
        "title": "Pre-service AV AI gate check",
        "required_action": "Confirm AI remains candidate-only, low-confidence items require staff review, and raw audio/video are not saved in P1.",
        "expected_output_ref": "demo_success_metric_ref",
        "cadence": "daily_open",
        "owner_scope": "ai_quality",
    },
    {
        "sequence": 30,
        "phase": "service_period_monitoring",
        "title": "Service period revenue and incident monitoring",
        "required_action": "Watch order count, revenue signal, unresolved candidates, LINE incidents, and manual fallback status without changing production flows.",
        "expected_output_ref": "daily_revenue_reconciliation_ref",
        "cadence": "service_period",
        "owner_scope": "cafe_operations",
    },
    {
        "sequence": 40,
        "phase": "staff_correction_review",
        "title": "Staff correction review",
        "required_action": "Capture safe correction refs for AI/menu/payment/member mismatch cases so candidate mistakes become improvement work.",
        "expected_output_ref": "lost_order_prevention_ref",
        "cadence": "service_period",
        "owner_scope": "staff_correction_queue",
    },
    {
        "sequence": 50,
        "phase": "daily_close_signal_entry",
        "title": "Daily close signal entry",
        "required_action": "Enter aggregate order, revenue, course income, LINE incident, unresolved candidate, burden, and fallback signals after close.",
        "expected_output_ref": "daily_revenue_reconciliation_ref",
        "cadence": "daily_close",
        "owner_scope": "financial_sustainability",
    },
    {
        "sequence": 60,
        "phase": "signal_trend_review",
        "title": "Signal trend review",
        "required_action": "Compare at least two observed days and flag regressing or insufficient data before expanding automation scope.",
        "expected_output_ref": "cafe_revenue_signal_ref",
        "cadence": "weekly",
        "owner_scope": "financial_sustainability",
    },
    {
        "sequence": 70,
        "phase": "decision_queue_review",
        "title": "Management decision queue review",
        "required_action": "Assign critical/high decision items to owner scope, due date, and safe evidence ref before activation discussion.",
        "expected_output_ref": "association_governance_handoff_ref",
        "cadence": "weekly",
        "owner_scope": "management_review",
    },
    {
        "sequence": 80,
        "phase": "weekly_sustainability_review",
        "title": "Weekly sustainability and debt-risk review",
        "required_action": "Review debt pressure, course cost allocation, cafe cashflow recovery, operator burden, and next Sanchong demonstration milestone.",
        "expected_output_ref": "debt_reduction_plan_ref",
        "cadence": "weekly",
        "owner_scope": "founder_mission_sustainability",
    },
    {
        "sequence": 90,
        "phase": "total_field_packet_review",
        "title": "Total-field packet review",
        "required_action": "Send only safe refs, hashes, scorecards, and runbook status to total field; keep secrets, plaintext, raw audio, and raw video out.",
        "expected_output_ref": "public_service_continuity_ref",
        "cadence": "weekly_or_before_review",
        "owner_scope": "total_field_evaluation",
    },
]

REQUIRED_REFS = {
    "business_continuity_refs": [
        "manual_order_fallback_ref",
        "manual_payment_fallback_ref",
        "existing_pos_continuity_ref",
        "line_manual_customer_service_ref",
        "dns_gateway_rollback_ref",
        "lost_order_prevention_ref",
        "daily_revenue_reconciliation_ref",
    ],
    "line_domain_api_control_refs": [
        "association_domain_approval_ref",
        "cafe_subdomain_ref",
        "provider_admin_role_review_ref",
        "vendor_access_review_ref",
        "association_gateway_ref",
        "webhook_relay_ref",
        "callback_relay_ref",
        "runtime_secret_rotation_ref",
    ],
    "financial_sustainability_refs": [
        "debt_increase_review_ref",
        "association_course_expansion_ref",
        "course_cost_allocation_ref",
        "cafe_cashflow_recovery_ref",
        "debt_reduction_plan_ref",
        "revenue_recovery_ref",
    ],
    "local_demonstration_refs": [
        "sanchong_local_readiness_ref",
        "community_trust_building_ref",
        "demo_success_metric_ref",
        "course_to_member_conversion_ref",
        "cafe_revenue_signal_ref",
        "community_self_funding_trigger_ref",
    ],
    "founder_mission_refs": [
        "founder_mission_ref",
        "association_governance_handoff_ref",
        "volunteer_role_split_ref",
        "operator_burden_reduction_ref",
        "public_service_continuity_ref",
    ],
}


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def side_effects_false() -> dict:
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


def quality_gates() -> dict:
    return {
        "no_ai_direct_pos_write": True,
        "no_ai_direct_payment_capture": True,
        "no_ai_direct_voucher_mutation": True,
        "no_ai_invented_price": True,
        "low_confidence_requires_staff_review": True,
        "generated_image_not_product_evidence": True,
        "real_or_staff_approved_product_photo_required": True,
        "raw_audio_saved_in_p1": False,
        "raw_video_saved_in_p1": False,
        "cloud_model_authority": False,
    }


def business_context() -> dict:
    return {
        "current_cafe_business_status": "ACTIVE_BUSINESS_CONTINUES_MANUALLY",
        "production_hold_does_not_mean_business_shutdown": True,
        "association_depends_on_cafe_operating_cashflow": True,
        "operator_reported_three_year_debt_increase_ntd": 2000000,
        "operator_reported_association_added_full_year_courses": 3,
        "founder_mission": "FOUNDER_LIFELONG_MISSION_PUBLIC_SERVICE_COMMITMENT",
        "sanchong_local_readiness": "SANCHONG_COMMUNITY_SELF_FUNDING_NOT_YET_MATURE",
        "strategy": "DEMONSTRATE_RESULTS_FIRST_THEN_TRIGGER_COMMUNITY_SELF_FUNDING",
    }


def build_business_backend_optimization_packet(*, actor_ref: str = "", input_ref: str = "") -> dict:
    packet_seed = {
        "actor_ref": actor_ref,
        "input_ref": input_ref,
        "panels": RECOMMENDED_BACKEND_PANELS,
        "flow": END_TO_END_FLOW,
        "features": AI_TECHNOLOGY_FEATURES,
    }
    return {
        "schema": "W7TP_XIAOJ_BUSINESS_BACKEND_OPTIMIZATION_PACKET_V1",
        "state": "P1_BACKEND_OPTIMIZATION_REVIEW_READY",
        "generated_at_utc": now_utc(),
        "actor_ref": actor_ref,
        "input_ref": input_ref,
        "recommended_backend_panels": RECOMMENDED_BACKEND_PANELS,
        "end_to_end_flow": END_TO_END_FLOW,
        "ai_technology_features": AI_TECHNOLOGY_FEATURES,
        "backend_checklist_items": BACKEND_CHECKLIST_ITEMS,
        "kpi_snapshot_types": KPI_SNAPSHOT_TYPES,
        "process_walkthrough_steps": PROCESS_WALKTHROUGH_STEPS,
        "operator_runbook_steps": OPERATOR_RUNBOOK_STEPS,
        "quality_gates": quality_gates(),
        "required_refs": REQUIRED_REFS,
        "business_context": business_context(),
        "recommended_first_backoffice_enhancements": [
            "business_continuity_refs_and_daily_reconciliation_tab",
            "av_ai_quality_gates_and_staff_correction_queue_tab",
            "line_domain_api_control_plane_tab",
            "financial_sustainability_and_course_cost_allocation_tab",
            "sanchong_demonstration_metrics_tab",
            "founder_mission_handoff_and_operator_burden_tab",
            "release_gate_board_tab",
        ],
        "production_activation_ready": False,
        "side_effects": side_effects_false(),
        "packet_hash": stable_hash(packet_seed),
    }


def build_business_backend_operator_runbook_packet(*, actor_ref: str = "", input_ref: str = "") -> dict:
    daily_cadences = {"daily_open", "service_period", "daily_close"}
    weekly_cadences = {"weekly", "weekly_or_before_review"}
    daily_steps = [step for step in OPERATOR_RUNBOOK_STEPS if step.get("cadence") in daily_cadences]
    weekly_steps = [step for step in OPERATOR_RUNBOOK_STEPS if step.get("cadence") in weekly_cadences]
    phase_keys = [step.get("phase", "") for step in OPERATOR_RUNBOOK_STEPS]
    next_actions = [
        "Run opening_check before service without changing current manual cafe operation.",
        "Complete daily_close_signal_entry after each business day so revenue, incidents, course income, and burden are visible.",
        "Review weekly_sustainability_review before adding vendor, cloud, gateway, course, or automation cost.",
        "Use total_field_packet_review to submit safe refs and hashes only; keep production activation behind a separate gate.",
    ]
    packet_seed = {
        "actor_ref": actor_ref,
        "input_ref": input_ref,
        "phase_keys": phase_keys,
        "daily_step_count": len(daily_steps),
        "weekly_step_count": len(weekly_steps),
    }
    return {
        "schema": "W7TP_XIAOJ_BUSINESS_BACKEND_OPERATOR_RUNBOOK_PACKET_V1",
        "state": "P1_OPERATOR_RUNBOOK_READY",
        "generated_at_utc": now_utc(),
        "actor_ref": actor_ref,
        "input_ref": input_ref,
        "operator_runbook_steps": OPERATOR_RUNBOOK_STEPS,
        "phase_keys": phase_keys,
        "step_count": len(OPERATOR_RUNBOOK_STEPS),
        "daily_step_count": len(daily_steps),
        "weekly_step_count": len(weekly_steps),
        "business_context": business_context(),
        "next_actions": next_actions,
        "production_activation_ready": False,
        "side_effects": side_effects_false(),
        "packet_hash": stable_hash(packet_seed),
    }


def build_business_backend_av_candidate_quality_packet(
    *,
    candidates: list[dict] | None = None,
    actor_ref: str = "",
    input_ref: str = "",
) -> dict:
    candidates = candidates if isinstance(candidates, list) else []
    reviewed_candidates = []
    low_confidence_candidates = []
    failed_validation_candidates = []
    generated_image_hold_candidates = []
    staff_review_required_candidates = []
    modality_counts: dict[str, int] = {}
    state_counts: dict[str, int] = {}

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        candidate_ref = str(candidate.get("candidate_ref") or "candidate_ref_missing")
        modality = str(candidate.get("modality") or "unknown")
        review_state = str(candidate.get("review_state") or "draft")
        try:
            confidence_score = float(candidate.get("confidence_score") or 0.0)
        except (TypeError, ValueError):
            confidence_score = 0.0
        odoo_validation_state = str(candidate.get("odoo_validation_state") or "not_checked")
        product_photo_evidence_state = str(candidate.get("product_photo_evidence_state") or "missing")
        red_flags = candidate.get("red_flags", [])
        red_flags = red_flags if isinstance(red_flags, list) else []

        if confidence_score < 0.75 and "low_confidence" not in red_flags:
            red_flags = [*red_flags, "low_confidence"]
        if product_photo_evidence_state == "generated_candidate_only" and "generated_image_not_product_evidence" not in red_flags:
            red_flags = [*red_flags, "generated_image_not_product_evidence"]
        if odoo_validation_state == "failed" and "menu_item_not_found" not in red_flags:
            red_flags = [*red_flags, "menu_item_not_found"]

        requires_staff_review = bool(red_flags) or confidence_score < 0.75 or odoo_validation_state in {"failed", "needs_staff_review"}
        recommended_action = "Staff review required before any POS, payment, voucher, member, or LINE send action."
        if product_photo_evidence_state == "generated_candidate_only":
            recommended_action = "Replace generated image candidate with real or staff-approved product photo evidence before product evidence use."
        elif odoo_validation_state == "failed":
            recommended_action = "Correct menu/options/price mapping and rebuild candidate before staff approval."
        elif not requires_staff_review:
            recommended_action = "Keep as staff-approved candidate only; production activation still requires separate release gate."

        item = {
            "candidate_ref": candidate_ref,
            "modality": modality,
            "review_state": review_state,
            "confidence_score": round(confidence_score, 4),
            "odoo_validation_state": odoo_validation_state,
            "product_photo_evidence_state": product_photo_evidence_state,
            "red_flags": sorted(set(str(flag) for flag in red_flags if flag)),
            "requires_staff_review": requires_staff_review,
            "evidence_ref": candidate.get("evidence_ref", ""),
            "recommended_action": recommended_action,
        }
        reviewed_candidates.append(item)
        modality_counts[modality] = modality_counts.get(modality, 0) + 1
        state_counts[review_state] = state_counts.get(review_state, 0) + 1
        if confidence_score < 0.75:
            low_confidence_candidates.append(item)
        if odoo_validation_state == "failed":
            failed_validation_candidates.append(item)
        if product_photo_evidence_state == "generated_candidate_only":
            generated_image_hold_candidates.append(item)
        if requires_staff_review:
            staff_review_required_candidates.append(item)

    next_actions = []
    if not candidates:
        next_actions.append("Start AV AI candidate quality capture with safe refs, confidence scores, red flags, and Odoo validation states.")
    if low_confidence_candidates:
        next_actions.append("Route low-confidence AV AI candidates to staff review before customer-facing or POS use.")
    if failed_validation_candidates:
        next_actions.append("Fix Odoo menu, price, custom option, or availability validation failures before candidate approval.")
    if generated_image_hold_candidates:
        next_actions.append("Do not use generated images as product evidence; attach real or staff-approved product photo refs.")
    if not next_actions:
        next_actions.append("Continue candidate quality review and keep production activation behind separate human release gates.")

    packet_seed = {
        "actor_ref": actor_ref,
        "input_ref": input_ref,
        "candidate_count": len(reviewed_candidates),
        "low_confidence_count": len(low_confidence_candidates),
        "failed_validation_count": len(failed_validation_candidates),
        "generated_image_hold_count": len(generated_image_hold_candidates),
        "modality_counts": modality_counts,
        "state_counts": state_counts,
    }
    return {
        "schema": "W7TP_XIAOJ_BUSINESS_BACKEND_AV_CANDIDATE_QUALITY_PACKET_V1",
        "state": "P1_AV_CANDIDATE_QUALITY_REVIEW_READY",
        "generated_at_utc": now_utc(),
        "actor_ref": actor_ref,
        "input_ref": input_ref,
        "candidate_modalities": AV_AI_CANDIDATE_MODALITIES,
        "review_states": AV_AI_CANDIDATE_REVIEW_STATES,
        "red_flag_types": AV_AI_CANDIDATE_RED_FLAGS,
        "reviewed_candidates": reviewed_candidates,
        "modality_counts": modality_counts,
        "review_state_counts": state_counts,
        "candidate_count": len(reviewed_candidates),
        "low_confidence_count": len(low_confidence_candidates),
        "failed_validation_count": len(failed_validation_candidates),
        "generated_image_hold_count": len(generated_image_hold_candidates),
        "staff_review_required_count": len(staff_review_required_candidates),
        "next_actions": next_actions,
        "quality_gates": quality_gates(),
        "production_activation_ready": False,
        "side_effects": side_effects_false(),
        "packet_hash": stable_hash(packet_seed),
    }


def build_business_backend_product_menu_quality_packet(
    *,
    products: list[dict] | None = None,
    actor_ref: str = "",
    input_ref: str = "",
) -> dict:
    products = products if isinstance(products, list) else []
    reviewed_products = []
    blocker_counts: dict[str, int] = {}
    ready_product_refs = []
    blocked_products = []
    missing_custom_options = []
    missing_photo_evidence = []

    for product in products:
        if not isinstance(product, dict):
            continue
        product_ref = str(product.get("product_ref") or "product_ref_missing")
        odoo_product_ref = str(product.get("odoo_product_ref") or "")
        price_ref = str(product.get("price_ref") or "")
        custom_options_ref = str(product.get("custom_options_ref") or "")
        photo_evidence_ref = str(product.get("photo_evidence_ref") or "")
        photo_evidence_state = str(product.get("photo_evidence_state") or "missing")
        availability_state = str(product.get("availability_state") or "unknown")
        ai_candidate_state = str(product.get("ai_candidate_state") or "blocked")
        blockers = []

        if not odoo_product_ref:
            blockers.append("missing_odoo_product_ref")
        if not price_ref:
            blockers.append("missing_price_ref")
        if not custom_options_ref:
            blockers.append("missing_custom_options_ref")
            missing_custom_options.append(product_ref)
        if not photo_evidence_ref:
            blockers.append("missing_photo_evidence_ref")
            missing_photo_evidence.append(product_ref)
        if photo_evidence_state == "generated_image_only":
            blockers.append("generated_image_only")
        if availability_state not in {"available", "limited"}:
            blockers.append("inactive_or_unavailable")
        if ai_candidate_state not in {"allowed_candidate", "staff_review_required"}:
            blockers.append("ai_candidate_not_allowed")

        for blocker in blockers:
            blocker_counts[blocker] = blocker_counts.get(blocker, 0) + 1
        ready_for_ai_candidate = not blockers or (set(blockers) == {"ai_candidate_not_allowed"} and ai_candidate_state == "staff_review_required")
        if blockers:
            blocked_products.append(product_ref)
        if ready_for_ai_candidate and not blockers:
            ready_product_refs.append(product_ref)

        reviewed_products.append(
            {
                "product_ref": product_ref,
                "odoo_product_ref": odoo_product_ref,
                "menu_category_ref": product.get("menu_category_ref", ""),
                "price_ref": price_ref,
                "custom_options_ref": custom_options_ref,
                "photo_evidence_ref": photo_evidence_ref,
                "photo_evidence_state": photo_evidence_state,
                "availability_state": availability_state,
                "ai_candidate_state": ai_candidate_state,
                "blockers": blockers,
                "ready_for_ai_candidate": not blockers,
                "recommended_action": (
                    "Ready for AI candidate use only; production still requires separate release gate."
                    if not blockers
                    else "Resolve product/menu blockers before AI candidate or product evidence use."
                ),
            }
        )

    next_actions = []
    if not products:
        next_actions.append("Start product/menu quality capture with Odoo product, price, custom option, and photo evidence refs.")
    if missing_custom_options:
        next_actions.append("Attach Custom Options JSON refs for products with unmapped sweetness, ice, size, topping, or service notes.")
    if missing_photo_evidence:
        next_actions.append("Attach real or staff-approved product photo evidence refs before official product evidence use.")
    if blocker_counts.get("generated_image_only", 0):
        next_actions.append("Replace generated-image-only product visuals with real or staff-approved photo refs.")
    if blocker_counts.get("missing_price_ref", 0):
        next_actions.append("Attach Odoo authority price refs so AI cannot invent or quote unverified prices.")
    if not next_actions:
        next_actions.append("Continue product/menu quality review and keep AI use candidate-only until release gates pass.")

    packet_seed = {
        "actor_ref": actor_ref,
        "input_ref": input_ref,
        "product_count": len(reviewed_products),
        "ready_count": len(ready_product_refs),
        "blocker_counts": blocker_counts,
    }
    return {
        "schema": "W7TP_XIAOJ_BUSINESS_BACKEND_PRODUCT_MENU_QUALITY_PACKET_V1",
        "state": "P1_PRODUCT_MENU_QUALITY_REVIEW_READY",
        "generated_at_utc": now_utc(),
        "actor_ref": actor_ref,
        "input_ref": input_ref,
        "quality_fields": PRODUCT_MENU_QUALITY_FIELDS,
        "required_refs": PRODUCT_MENU_REQUIRED_REFS,
        "blocker_types": PRODUCT_MENU_BLOCKER_TYPES,
        "reviewed_products": reviewed_products,
        "product_count": len(reviewed_products),
        "ready_product_count": len(ready_product_refs),
        "blocked_product_count": len(blocked_products),
        "blocker_counts": blocker_counts,
        "missing_custom_options_count": len(missing_custom_options),
        "missing_photo_evidence_count": len(missing_photo_evidence),
        "next_actions": next_actions,
        "quality_gates": quality_gates(),
        "production_activation_ready": False,
        "side_effects": side_effects_false(),
        "packet_hash": stable_hash(packet_seed),
    }


def build_business_backend_member_voucher_payment_preflight_packet(
    *,
    preflights: list[dict] | None = None,
    actor_ref: str = "",
    input_ref: str = "",
) -> dict:
    preflights = preflights if isinstance(preflights, list) else []
    reviewed_preflights = []
    blocker_counts: dict[str, int] = {}
    ready_preflight_refs = []
    blocked_preflight_refs = []

    for preflight in preflights:
        if not isinstance(preflight, dict):
            continue
        candidate_order_ref = str(preflight.get("candidate_order_ref") or "")
        member_ref = str(preflight.get("member_ref") or "")
        voucher_dry_run_ref = str(preflight.get("voucher_dry_run_ref") or "")
        payment_method_ref = str(preflight.get("payment_method_ref") or "")
        pos_draft_ref = str(preflight.get("pos_draft_ref") or "")
        consent_ref = str(preflight.get("consent_ref") or "")
        preflight_state = str(preflight.get("preflight_state") or "draft")
        requested_mutation = bool(preflight.get("requested_mutation"))
        blockers = []

        if not candidate_order_ref:
            blockers.append("missing_candidate_order_ref")
        if not member_ref:
            blockers.append("missing_member_ref")
        if not consent_ref:
            blockers.append("missing_consent_ref")
        if not voucher_dry_run_ref:
            blockers.append("missing_voucher_dry_run_ref")
        if not payment_method_ref:
            blockers.append("missing_payment_method_ref")
        if not pos_draft_ref:
            blockers.append("missing_pos_draft_ref")
        if preflight_state == "voucher_conflict":
            blockers.append("voucher_conflict")
        if preflight_state == "payment_failed":
            blockers.append("payment_precondition_failed")
        if preflight_state == "member_plaintext_risk":
            blockers.append("member_plaintext_risk")
        if requested_mutation:
            blockers.append("production_mutation_requested")

        for blocker in blockers:
            blocker_counts[blocker] = blocker_counts.get(blocker, 0) + 1

        preflight_ref = candidate_order_ref or "candidate_order_ref_missing"
        if blockers:
            blocked_preflight_refs.append(preflight_ref)
        else:
            ready_preflight_refs.append(preflight_ref)

        reviewed_preflights.append(
            {
                "candidate_order_ref": preflight_ref,
                "member_ref": member_ref,
                "voucher_dry_run_ref": voucher_dry_run_ref,
                "payment_method_ref": payment_method_ref,
                "pos_draft_ref": pos_draft_ref,
                "consent_ref": consent_ref,
                "preflight_state": preflight_state,
                "requested_mutation": requested_mutation,
                "blockers": blockers,
                "ready_for_human_checkout_review": not blockers,
                "recommended_action": (
                    "Ready for human checkout review only; payment capture, voucher redemption, member mutation, and POS write remain blocked."
                    if not blockers
                    else "Resolve member/voucher/payment preflight blockers before checkout or activation discussion."
                ),
            }
        )

    next_actions = []
    if not preflights:
        next_actions.append("Start member/voucher/payment preflight capture with candidate order, member, consent, voucher dry-run, payment method, and POS draft refs.")
    if blocker_counts.get("missing_voucher_dry_run_ref", 0):
        next_actions.append("Attach voucher dry-run refs before any voucher redemption discussion.")
    if blocker_counts.get("missing_payment_method_ref", 0):
        next_actions.append("Attach payment method refs and keep payment capture disabled.")
    if blocker_counts.get("production_mutation_requested", 0):
        next_actions.append("Remove production mutation requests; P1 preflight cannot write POS, capture payment, redeem voucher, or mutate members.")
    if blocker_counts.get("member_plaintext_risk", 0):
        next_actions.append("Replace member plaintext with opaque member refs before review.")
    if not next_actions:
        next_actions.append("Continue preflight review and keep checkout actions behind separate human release gates.")

    packet_seed = {
        "actor_ref": actor_ref,
        "input_ref": input_ref,
        "preflight_count": len(reviewed_preflights),
        "ready_count": len(ready_preflight_refs),
        "blocker_counts": blocker_counts,
    }
    return {
        "schema": "W7TP_XIAOJ_BUSINESS_BACKEND_MEMBER_VOUCHER_PAYMENT_PREFLIGHT_PACKET_V1",
        "state": "P1_MEMBER_VOUCHER_PAYMENT_PREFLIGHT_READY",
        "generated_at_utc": now_utc(),
        "actor_ref": actor_ref,
        "input_ref": input_ref,
        "preflight_fields": MEMBER_VOUCHER_PAYMENT_PREFLIGHT_FIELDS,
        "blocker_types": MEMBER_VOUCHER_PAYMENT_BLOCKER_TYPES,
        "reviewed_preflights": reviewed_preflights,
        "preflight_count": len(reviewed_preflights),
        "ready_preflight_count": len(ready_preflight_refs),
        "blocked_preflight_count": len(blocked_preflight_refs),
        "blocker_counts": blocker_counts,
        "next_actions": next_actions,
        "quality_gates": quality_gates(),
        "production_activation_ready": False,
        "side_effects": side_effects_false(),
        "packet_hash": stable_hash(packet_seed),
    }


def build_business_backend_process_walkthrough_packet(
    *,
    actor_ref: str = "",
    input_ref: str = "",
    completed_improvement_keys: list[str] | None = None,
) -> dict:
    completed_keys = set(completed_improvement_keys if isinstance(completed_improvement_keys, list) else [])
    improvement_items = []
    critical_count = 0
    for step in PROCESS_WALKTHROUGH_STEPS:
        priority = step.get("priority", "medium")
        if priority == "critical":
            critical_count += 1
        improvement_items.append(
            {
                "sequence": step.get("sequence", 10),
                "stage_key": step.get("stage_key", ""),
                "improvement_key": step.get("improvement_key", ""),
                "title": step.get("improvement_title", ""),
                "priority": priority,
                "owner_scope": step.get("owner_scope", ""),
                "kpi_type": step.get("kpi_type", ""),
                "operator_status": "done" if step.get("improvement_key") in completed_keys else "todo",
                "success_metric": step.get("expected_control", ""),
            }
        )

    next_actions = [
        "Review critical improvement items before any production activation packet.",
        "Attach safe evidence refs for daily close, LINE scope, release blockers, and AV AI correction queues.",
        "Use staff correction and daily reconciliation data to choose the next backend model split.",
    ]
    packet_seed = {
        "actor_ref": actor_ref,
        "input_ref": input_ref,
        "walkthrough_stage_count": len(PROCESS_WALKTHROUGH_STEPS),
        "improvement_count": len(improvement_items),
        "critical_count": critical_count,
        "completed_keys": sorted(completed_keys),
    }
    return {
        "schema": "W7TP_XIAOJ_BUSINESS_BACKEND_PROCESS_WALKTHROUGH_PACKET_V1",
        "state": "P1_PROCESS_WALKTHROUGH_READY",
        "generated_at_utc": now_utc(),
        "actor_ref": actor_ref,
        "input_ref": input_ref,
        "process_walkthrough_steps": PROCESS_WALKTHROUGH_STEPS,
        "improvement_items": improvement_items,
        "walkthrough_stage_count": len(PROCESS_WALKTHROUGH_STEPS),
        "improvement_item_count": len(improvement_items),
        "critical_improvement_count": critical_count,
        "next_actions": next_actions,
        "production_activation_ready": False,
        "side_effects": side_effects_false(),
        "packet_hash": stable_hash(packet_seed),
    }


def _status_count(items: list[dict], field_name: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        status = str(item.get(field_name) or "todo")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _completion_ratio(counts: dict[str, int], total: int, positive_statuses: set[str]) -> float:
    if total <= 0:
        return 0.0
    positive = sum(counts.get(status, 0) for status in positive_statuses)
    return round(positive / total, 4)


def build_business_backend_readiness_scorecard_packet(
    *,
    checklist_items: list[dict] | None = None,
    kpi_snapshots: list[dict] | None = None,
    improvement_items: list[dict] | None = None,
    actor_ref: str = "",
    input_ref: str = "",
) -> dict:
    checklist_items = checklist_items if isinstance(checklist_items, list) else []
    kpi_snapshots = kpi_snapshots if isinstance(kpi_snapshots, list) else []
    improvement_items = improvement_items if isinstance(improvement_items, list) else []

    checklist_counts = _status_count(checklist_items, "operator_status")
    kpi_counts = _status_count(kpi_snapshots, "state")
    improvement_counts = _status_count(improvement_items, "operator_status")

    checklist_ratio = _completion_ratio(checklist_counts, len(checklist_items), {"done", "ready_for_review"})
    kpi_ratio = _completion_ratio(kpi_counts, len(kpi_snapshots), {"observed", "ready_for_review"})
    improvement_ratio = _completion_ratio(improvement_counts, len(improvement_items), {"done", "ready_for_review"})

    weighted_score = round((checklist_ratio * 40) + (kpi_ratio * 30) + (improvement_ratio * 30), 2)
    blocked_checklist = [item for item in checklist_items if item.get("operator_status") == "blocked"]
    needs_action_kpis = [item for item in kpi_snapshots if item.get("state") == "needs_action"]
    blocked_improvements = [item for item in improvement_items if item.get("operator_status") == "blocked"]
    critical_open_improvements = [
        item
        for item in improvement_items
        if item.get("priority") == "critical" and item.get("operator_status") not in {"done", "ready_for_review"}
    ]

    activation_blockers = []
    if blocked_checklist:
        activation_blockers.append("blocked_checklist_items")
    if needs_action_kpis:
        activation_blockers.append("needs_action_kpis")
    if blocked_improvements:
        activation_blockers.append("blocked_process_improvements")
    if critical_open_improvements:
        activation_blockers.append("critical_process_improvements_open")
    if weighted_score < 85:
        activation_blockers.append("readiness_score_below_85")

    if activation_blockers:
        maturity_state = "P1_IMPROVEMENT_REQUIRED"
    elif weighted_score >= 95:
        maturity_state = "P1_REVIEW_STRONG_READY_FOR_HUMAN_ACTIVATION_REVIEW"
    else:
        maturity_state = "P1_REVIEW_NEEDS_MORE_EVIDENCE"

    next_actions = []
    if blocked_checklist:
        next_actions.append("Clear blocked checklist items and attach safe refs.")
    if needs_action_kpis:
        next_actions.append("Resolve needs_action KPI snapshots before activation review.")
    if critical_open_improvements:
        next_actions.append("Complete or ready-for-review all critical process improvements.")
    if weighted_score < 85:
        next_actions.append("Raise readiness score to at least 85 before any activation packet discussion.")
    if not next_actions:
        next_actions.append("Keep collecting evidence and prepare a separate human activation packet only if refs are complete.")

    packet_seed = {
        "actor_ref": actor_ref,
        "input_ref": input_ref,
        "checklist_counts": checklist_counts,
        "kpi_counts": kpi_counts,
        "improvement_counts": improvement_counts,
        "weighted_score": weighted_score,
        "activation_blockers": activation_blockers,
    }
    return {
        "schema": "W7TP_XIAOJ_BUSINESS_BACKEND_READINESS_SCORECARD_PACKET_V1",
        "state": maturity_state,
        "generated_at_utc": now_utc(),
        "actor_ref": actor_ref,
        "input_ref": input_ref,
        "readiness_score": weighted_score,
        "score_components": {
            "checklist_completion_ratio": checklist_ratio,
            "kpi_observed_or_review_ready_ratio": kpi_ratio,
            "improvement_completion_ratio": improvement_ratio,
            "checklist_weight": 40,
            "kpi_weight": 30,
            "improvement_weight": 30,
        },
        "status_counts": {
            "checklist": checklist_counts,
            "kpi": kpi_counts,
            "improvement": improvement_counts,
        },
        "activation_blockers": activation_blockers,
        "blocked_checklist_count": len(blocked_checklist),
        "needs_action_kpi_count": len(needs_action_kpis),
        "blocked_improvement_count": len(blocked_improvements),
        "critical_open_improvement_count": len(critical_open_improvements),
        "next_actions": next_actions,
        "production_activation_ready": False,
        "side_effects": side_effects_false(),
        "packet_hash": stable_hash(packet_seed),
    }


def build_business_backend_daily_signal_packet(
    *,
    daily_signals: list[dict] | None = None,
    actor_ref: str = "",
    input_ref: str = "",
) -> dict:
    daily_signals = daily_signals if isinstance(daily_signals, list) else []
    signal_type_counts: dict[str, int] = {}
    total_numeric_by_type: dict[str, float] = {}
    needs_action_signals: list[dict] = []
    observed_dates = set()
    for signal in daily_signals:
        if not isinstance(signal, dict):
            continue
        signal_type = str(signal.get("signal_type") or "unknown")
        state = str(signal.get("state") or "draft")
        signal_type_counts[signal_type] = signal_type_counts.get(signal_type, 0) + 1
        observed_dates.add(str(signal.get("signal_date") or "unknown"))
        try:
            numeric_value = float(signal.get("numeric_value") or 0)
        except (TypeError, ValueError):
            numeric_value = 0.0
        total_numeric_by_type[signal_type] = round(total_numeric_by_type.get(signal_type, 0.0) + numeric_value, 4)
        if state == "needs_action":
            needs_action_signals.append(
                {
                    "signal_date": signal.get("signal_date", ""),
                    "signal_type": signal_type,
                    "evidence_ref": signal.get("evidence_ref", ""),
                    "summary": signal.get("summary", ""),
                }
            )

    missing_signal_types = sorted(set(DAILY_SIGNAL_TYPES) - set(signal_type_counts))
    next_actions = []
    if missing_signal_types:
        next_actions.append("Add missing daily operating signal types before relying on scorecard trends.")
    if needs_action_signals:
        next_actions.append("Resolve daily signals marked needs_action and attach safe evidence refs.")
    if not daily_signals:
        next_actions.append("Start daily operating signal capture for cafe revenue, order, LINE, course, and burden indicators.")
    if not next_actions:
        next_actions.append("Continue daily signal capture and compare weekly trend direction before activation discussion.")

    packet_seed = {
        "actor_ref": actor_ref,
        "input_ref": input_ref,
        "signal_type_counts": signal_type_counts,
        "total_numeric_by_type": total_numeric_by_type,
        "needs_action_count": len(needs_action_signals),
        "observed_day_count": len(observed_dates - {"unknown"}),
    }
    return {
        "schema": "W7TP_XIAOJ_BUSINESS_BACKEND_DAILY_SIGNAL_PACKET_V1",
        "state": "P1_DAILY_SIGNAL_REVIEW_READY",
        "generated_at_utc": now_utc(),
        "actor_ref": actor_ref,
        "input_ref": input_ref,
        "daily_signal_types": DAILY_SIGNAL_TYPES,
        "signal_type_counts": signal_type_counts,
        "total_numeric_by_type": total_numeric_by_type,
        "observed_day_count": len(observed_dates - {"unknown"}),
        "missing_signal_types": missing_signal_types,
        "needs_action_signals": needs_action_signals,
        "next_actions": next_actions,
        "production_activation_ready": False,
        "side_effects": side_effects_false(),
        "packet_hash": stable_hash(packet_seed),
    }


def build_business_backend_signal_trend_packet(
    *,
    daily_signals: list[dict] | None = None,
    actor_ref: str = "",
    input_ref: str = "",
) -> dict:
    daily_signals = daily_signals if isinstance(daily_signals, list) else []
    by_type: dict[str, dict[str, float]] = {}
    needs_action_signals = []
    for signal in daily_signals:
        if not isinstance(signal, dict):
            continue
        signal_type = str(signal.get("signal_type") or "unknown")
        signal_date = str(signal.get("signal_date") or "unknown")
        if signal_date == "unknown":
            continue
        try:
            numeric_value = float(signal.get("numeric_value") or 0)
        except (TypeError, ValueError):
            numeric_value = 0.0
        by_type.setdefault(signal_type, {})
        by_type[signal_type][signal_date] = round(by_type[signal_type].get(signal_date, 0.0) + numeric_value, 4)
        if str(signal.get("state") or "draft") == "needs_action":
            needs_action_signals.append(
                {
                    "signal_date": signal_date,
                    "signal_type": signal_type,
                    "evidence_ref": signal.get("evidence_ref", ""),
                }
            )

    trend_items = []
    regressing_types = []
    insufficient_types = []
    for signal_type in DAILY_SIGNAL_TYPES:
        values_by_date = by_type.get(signal_type, {})
        dates = sorted(values_by_date)
        if len(dates) < 2:
            trend_state = "insufficient_data"
            delta = 0.0
            first_value = values_by_date.get(dates[0], 0.0) if dates else 0.0
            last_value = first_value
            insufficient_types.append(signal_type)
        else:
            first_value = values_by_date[dates[0]]
            last_value = values_by_date[dates[-1]]
            delta = round(last_value - first_value, 4)
            direction = SIGNAL_TREND_DIRECTIONS.get(signal_type, "higher_is_better")
            if delta == 0:
                trend_state = "flat"
            elif (direction == "higher_is_better" and delta > 0) or (direction == "lower_is_better" and delta < 0):
                trend_state = "improving"
            else:
                trend_state = "regressing"
                regressing_types.append(signal_type)
        trend_items.append(
            {
                "signal_type": signal_type,
                "direction_rule": SIGNAL_TREND_DIRECTIONS.get(signal_type, "higher_is_better"),
                "observed_day_count": len(dates),
                "first_value": first_value,
                "last_value": last_value,
                "delta": delta,
                "trend_state": trend_state,
            }
        )

    next_actions = []
    if insufficient_types:
        next_actions.append("Collect at least two observed days for each insufficient daily signal type.")
    if regressing_types:
        next_actions.append("Review regressing daily signals before expanding automation scope.")
    if needs_action_signals:
        next_actions.append("Resolve needs_action daily signals and attach safe evidence refs.")
    if not next_actions:
        next_actions.append("Continue weekly trend review and keep production activation held until separate refs pass.")

    packet_seed = {
        "actor_ref": actor_ref,
        "input_ref": input_ref,
        "trend_items": trend_items,
        "regressing_types": regressing_types,
        "insufficient_types": insufficient_types,
        "needs_action_count": len(needs_action_signals),
    }
    return {
        "schema": "W7TP_XIAOJ_BUSINESS_BACKEND_SIGNAL_TREND_PACKET_V1",
        "state": "P1_SIGNAL_TREND_REVIEW_READY",
        "generated_at_utc": now_utc(),
        "actor_ref": actor_ref,
        "input_ref": input_ref,
        "trend_items": trend_items,
        "regressing_signal_types": regressing_types,
        "insufficient_signal_types": insufficient_types,
        "needs_action_signals": needs_action_signals,
        "next_actions": next_actions,
        "production_activation_ready": False,
        "side_effects": side_effects_false(),
        "packet_hash": stable_hash(packet_seed),
    }


def build_business_backend_management_decision_queue_packet(
    *,
    signal_trend_packet: dict | None = None,
    readiness_scorecard_packet: dict | None = None,
    operating_review_packet: dict | None = None,
    actor_ref: str = "",
    input_ref: str = "",
) -> dict:
    signal_trend_packet = signal_trend_packet if isinstance(signal_trend_packet, dict) else {}
    readiness_scorecard_packet = readiness_scorecard_packet if isinstance(readiness_scorecard_packet, dict) else {}
    operating_review_packet = operating_review_packet if isinstance(operating_review_packet, dict) else {}
    decision_items = []

    for signal_type in signal_trend_packet.get("regressing_signal_types", []):
        decision_items.append(
            {
                "decision_key": f"review_regressing_signal:{signal_type}",
                "source": "signal_trend",
                "priority": "high",
                "title": f"Review regressing daily signal: {signal_type}",
                "recommended_action": "Inspect safe evidence refs, identify cause, and create an improvement item before automation expansion.",
            }
        )
    for signal_type in signal_trend_packet.get("insufficient_signal_types", []):
        decision_items.append(
            {
                "decision_key": f"collect_insufficient_signal:{signal_type}",
                "source": "signal_trend",
                "priority": "medium",
                "title": f"Collect more daily signal data: {signal_type}",
                "recommended_action": "Capture at least two observed days before treating the trend as reliable.",
            }
        )
    for blocker in readiness_scorecard_packet.get("activation_blockers", []):
        decision_items.append(
            {
                "decision_key": f"clear_activation_blocker:{blocker}",
                "source": "readiness_scorecard",
                "priority": "critical",
                "title": f"Clear activation blocker: {blocker}",
                "recommended_action": "Keep production activation held and clear this blocker with safe refs and human review.",
            }
        )
    for item in operating_review_packet.get("blocked_checklist_items", []):
        item_key = item.get("item_key", "unknown")
        decision_items.append(
            {
                "decision_key": f"resolve_blocked_checklist:{item_key}",
                "source": "operating_review",
                "priority": "critical",
                "title": f"Resolve blocked checklist item: {item_key}",
                "recommended_action": "Attach required refs, update operator status, and rebuild operating review.",
            }
        )
    for item in operating_review_packet.get("needs_action_kpis", []):
        snapshot_type = item.get("snapshot_type", "unknown")
        decision_items.append(
            {
                "decision_key": f"resolve_needs_action_kpi:{snapshot_type}",
                "source": "operating_review",
                "priority": "high",
                "title": f"Resolve KPI marked needs_action: {snapshot_type}",
                "recommended_action": "Review safe KPI evidence, update summary, and decide whether an improvement item is needed.",
            }
        )

    priority_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    decision_items = sorted(decision_items, key=lambda item: (priority_rank.get(item.get("priority", "medium"), 2), item.get("decision_key", "")))
    counts_by_priority: dict[str, int] = {}
    for item in decision_items:
        priority = item.get("priority", "medium")
        counts_by_priority[priority] = counts_by_priority.get(priority, 0) + 1

    next_actions = []
    if counts_by_priority.get("critical", 0):
        next_actions.append("Handle critical decision items before any activation discussion.")
    if counts_by_priority.get("high", 0):
        next_actions.append("Assign high-priority decision items to an owner scope and evidence ref.")
    if not decision_items:
        next_actions.append("No management decision items were generated; continue daily signal and scorecard review.")

    packet_seed = {
        "actor_ref": actor_ref,
        "input_ref": input_ref,
        "decision_count": len(decision_items),
        "counts_by_priority": counts_by_priority,
    }
    return {
        "schema": "W7TP_XIAOJ_BUSINESS_BACKEND_MANAGEMENT_DECISION_QUEUE_PACKET_V1",
        "state": "P1_MANAGEMENT_DECISION_QUEUE_READY",
        "generated_at_utc": now_utc(),
        "actor_ref": actor_ref,
        "input_ref": input_ref,
        "decision_items": decision_items,
        "decision_count": len(decision_items),
        "counts_by_priority": counts_by_priority,
        "next_actions": next_actions,
        "production_activation_ready": False,
        "side_effects": side_effects_false(),
        "packet_hash": stable_hash(packet_seed),
    }


def build_business_backend_operating_review_packet(
    *,
    checklist_items: list[dict] | None = None,
    kpi_snapshots: list[dict] | None = None,
    actor_ref: str = "",
    input_ref: str = "",
) -> dict:
    checklist_items = checklist_items if isinstance(checklist_items, list) else []
    kpi_snapshots = kpi_snapshots if isinstance(kpi_snapshots, list) else []
    status_counts: dict[str, int] = {}
    panel_counts: dict[str, int] = {}
    blocker_items: list[dict] = []
    for item in checklist_items:
        if not isinstance(item, dict):
            continue
        status = str(item.get("operator_status") or "todo")
        panel = str(item.get("panel") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        panel_counts[panel] = panel_counts.get(panel, 0) + 1
        if status == "blocked":
            blocker_items.append(
                {
                    "panel": panel,
                    "item_key": item.get("item_key", ""),
                    "required_ref": item.get("required_ref", ""),
                    "title": item.get("title", ""),
                }
            )

    kpi_type_counts: dict[str, int] = {}
    needs_action_kpis: list[dict] = []
    for snapshot in kpi_snapshots:
        if not isinstance(snapshot, dict):
            continue
        snapshot_type = str(snapshot.get("snapshot_type") or "unknown")
        state = str(snapshot.get("state") or "draft")
        kpi_type_counts[snapshot_type] = kpi_type_counts.get(snapshot_type, 0) + 1
        if state == "needs_action":
            needs_action_kpis.append(
                {
                    "snapshot_type": snapshot_type,
                    "evidence_ref": snapshot.get("evidence_ref", ""),
                    "summary": snapshot.get("summary", ""),
                }
            )

    missing_kpi_types = sorted(set(KPI_SNAPSHOT_TYPES) - set(kpi_type_counts))
    next_actions = []
    if status_counts.get("blocked", 0):
        next_actions.append("Resolve blocked checklist items before expanding automation scope.")
    if missing_kpi_types:
        next_actions.append("Create KPI snapshots for missing operating review types.")
    if needs_action_kpis:
        next_actions.append("Review KPI snapshots marked needs_action and attach safe evidence refs.")
    if not next_actions:
        next_actions.append("Continue P1 review, keep production activation held, and collect more operating evidence.")

    packet_seed = {
        "actor_ref": actor_ref,
        "input_ref": input_ref,
        "status_counts": status_counts,
        "kpi_type_counts": kpi_type_counts,
        "blocker_count": len(blocker_items),
        "needs_action_kpi_count": len(needs_action_kpis),
    }
    return {
        "schema": "W7TP_XIAOJ_BUSINESS_BACKEND_OPERATING_REVIEW_PACKET_V1",
        "state": "P1_OPERATING_REVIEW_READY",
        "generated_at_utc": now_utc(),
        "actor_ref": actor_ref,
        "input_ref": input_ref,
        "checklist_status_counts": status_counts,
        "checklist_panel_counts": panel_counts,
        "blocked_checklist_items": blocker_items,
        "kpi_type_counts": kpi_type_counts,
        "missing_kpi_types": missing_kpi_types,
        "needs_action_kpis": needs_action_kpis,
        "next_actions": next_actions,
        "production_activation_ready": False,
        "side_effects": side_effects_false(),
        "packet_hash": stable_hash(packet_seed),
    }
