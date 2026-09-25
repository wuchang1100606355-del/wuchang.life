#!/usr/bin/env python3
"""Verify XiaoJ business backend optimization review packet."""

from __future__ import annotations

import json
import importlib.util
import re
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "packets/product_av_ordering_ai/xiaoj_business_backend_optimization_contract.json"
GUIDE = ROOT / "docs/product/XIAOJ_BUSINESS_BACKEND_OPTIMIZATION_AND_AV_AI_MERCHANT_SYSTEM_PLAN.md"
SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/business_backend_optimization.py"
MODEL = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/models/business_backend_optimization.py"
MODEL_INIT = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/models/__init__.py"
VIEW = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/views/business_backend_optimization_views.xml"
ACCESS = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/security/ir.model.access.csv"
MANIFEST = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/__manifest__.py"

HOLD_STATE = "HOLD_XIAOJ_BUSINESS_BACKEND_OPTIMIZATION"

REQUIRED_PANELS = {
    "business_continuity_cockpit",
    "av_ai_merchant_quality_panel",
    "menu_product_custom_option_control",
    "line_domain_api_control_plane",
    "financial_sustainability_panel",
    "sanchong_demonstration_self_funding_panel",
    "founder_mission_sustainability_panel",
    "release_gate_board",
    "staff_correction_queue",
}

REQUIRED_FLOW = [
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

REQUIRED_AI_FEATURES = {
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
}

REQUIRED_CHECKLIST_KEYS = {
    "manual_order_fallback",
    "daily_revenue_reconciliation",
    "low_confidence_staff_review",
    "staff_correction_feedback_loop",
    "custom_options_json_coverage",
    "cafe_subdomain_gateway",
    "vendor_access_review",
    "debt_reduction_plan",
    "course_cost_allocation",
    "demo_success_metric",
    "operator_burden_reduction",
    "release_gate_board",
}

REQUIRED_KPI_TYPES = {
    "daily_revenue_reconciliation",
    "av_ai_candidate_quality",
    "staff_correction_queue",
    "course_to_member_conversion",
    "sanchong_demo_signal",
    "operator_burden",
    "release_blocker_count",
}

REQUIRED_DAILY_SIGNAL_TYPES = {
    "order_count_signal",
    "revenue_signal",
    "unresolved_candidate_count",
    "line_incident_count",
    "course_income_signal",
    "operator_burden_hours",
    "manual_fallback_status",
}

REQUIRED_AV_CANDIDATE_MODALITIES = {
    "audio_intent",
    "video_product_recognition",
    "menu_text_candidate",
    "product_image_candidate",
    "multimodal_order_candidate",
}

REQUIRED_AV_CANDIDATE_RED_FLAGS = {
    "low_confidence",
    "menu_item_not_found",
    "custom_option_unmapped",
    "price_mismatch",
    "allergy_or_safety_risk",
    "payment_or_voucher_request",
    "member_plaintext_risk",
    "generated_image_not_product_evidence",
    "raw_media_storage_risk",
}

REQUIRED_PRODUCT_MENU_REFS = {
    "odoo_product_ref",
    "price_ref",
    "custom_options_ref",
    "photo_evidence_ref",
}

REQUIRED_PRODUCT_MENU_BLOCKERS = {
    "missing_odoo_product_ref",
    "missing_price_ref",
    "missing_custom_options_ref",
    "missing_photo_evidence_ref",
    "generated_image_only",
    "inactive_or_unavailable",
    "ai_candidate_not_allowed",
}

REQUIRED_PROCESS_STAGE_KEYS = {
    "customer_inquiry_entry",
    "av_ai_candidate_capture",
    "structured_order_candidate",
    "odoo_authority_validation",
    "staff_confirmation",
    "pos_payment_voucher_gate",
    "line_lineworks_notification",
    "daily_close_reconciliation",
    "sanchong_demo_loop",
    "total_field_packet_review",
}

REQUIRED_RUNBOOK_PHASE_KEYS = {
    "opening_check",
    "pre_service_ai_gate_check",
    "service_period_monitoring",
    "staff_correction_review",
    "daily_close_signal_entry",
    "signal_trend_review",
    "decision_queue_review",
    "weekly_sustainability_review",
    "total_field_packet_review",
}

REQUIRED_IMPROVEMENT_KEYS = {
    "unified_entry_intake_board",
    "av_candidate_confidence_and_red_flag_panel",
    "custom_options_json_mapping_queue",
    "authority_validation_failure_reasons",
    "staff_correction_resolution_sla",
    "release_gate_blocker_board",
    "line_subject_scope_dashboard",
    "daily_close_reconciliation_packet",
    "demo_to_self_funding_trigger_tracker",
    "evidence_hash_and_ref_readiness",
}

REQUIRED_REFS = {
    "manual_order_fallback_ref",
    "manual_payment_fallback_ref",
    "existing_pos_continuity_ref",
    "line_manual_customer_service_ref",
    "dns_gateway_rollback_ref",
    "lost_order_prevention_ref",
    "daily_revenue_reconciliation_ref",
    "association_domain_approval_ref",
    "cafe_subdomain_ref",
    "provider_admin_role_review_ref",
    "vendor_access_review_ref",
    "association_gateway_ref",
    "webhook_relay_ref",
    "callback_relay_ref",
    "runtime_secret_rotation_ref",
    "debt_increase_review_ref",
    "association_course_expansion_ref",
    "course_cost_allocation_ref",
    "cafe_cashflow_recovery_ref",
    "debt_reduction_plan_ref",
    "revenue_recovery_ref",
    "sanchong_local_readiness_ref",
    "community_trust_building_ref",
    "demo_success_metric_ref",
    "course_to_member_conversion_ref",
    "cafe_revenue_signal_ref",
    "community_self_funding_trigger_ref",
    "founder_mission_ref",
    "association_governance_handoff_ref",
    "volunteer_role_split_ref",
    "operator_burden_reduction_ref",
    "public_service_continuity_ref",
}

SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9_-]{12,}",
    r"(?i)(access|refresh|id)_token\s*[:=]\s*\S+",
    r"(?i)api[_ -]?key\s*[:=]\s*\S+",
    r"(?i)(channel|client|router|odoo|lineworks|line)[_-]?secret\s*[:=]\s*\S+",
    r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}",
    r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}",
    r"09\d{2}[- ]?\d{3}[- ]?\d{3}",
    r"\b[A-Z][12]\d{8}\b",
]


def fail(message: str) -> None:
    print(f"VERIFY_FAIL={message}")
    print(f"STATE={HOLD_STATE}")
    raise SystemExit(1)


def read(path: Path) -> str:
    if not path.exists():
        fail(f"missing:{path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def assert_no_secret_shape(text: str, label: str) -> None:
    for pattern in SECRET_PATTERNS:
        if re.search(pattern, text):
            fail(f"secret_shape_detected:{label}:{pattern}")


def assert_false_map(values: dict, label: str) -> None:
    if not isinstance(values, dict):
        fail(f"missing_false_map:{label}")
    for key, value in values.items():
        if value is not False:
            fail(f"expected_false:{label}:{key}")


def require_text(path: Path, needles: list[str], label: str) -> str:
    text = read(path)
    assert_no_secret_shape(text, label)
    for needle in needles:
        if needle not in text:
            fail(f"missing_text:{path.relative_to(ROOT)}:{needle}")
    return text


def ensure_package_stub(name: str, path: Path) -> None:
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        module.__path__ = [str(path)]  # type: ignore[attr-defined]
        sys.modules[name] = module
    elif not hasattr(module, "__path__"):
        module.__path__ = [str(path)]  # type: ignore[attr-defined]


def load_service():
    ensure_package_stub("Taiji_Odoo", ROOT / "Taiji_Odoo")
    ensure_package_stub("Taiji_Odoo.addons", ROOT / "Taiji_Odoo/addons")
    ensure_package_stub("Taiji_Odoo.addons.wuchang_cafe_ai_gateway", ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway")
    ensure_package_stub(
        "Taiji_Odoo.addons.wuchang_cafe_ai_gateway.services",
        ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services",
    )
    spec = importlib.util.spec_from_file_location(
        "Taiji_Odoo.addons.wuchang_cafe_ai_gateway.services.business_backend_optimization",
        SERVICE,
    )
    if spec is None or spec.loader is None:
        fail("service_import_spec_missing")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    contract_text = read(CONTRACT)
    guide_text = read(GUIDE)
    assert_no_secret_shape(contract_text, "contract")
    assert_no_secret_shape(guide_text, "guide")

    contract = json.loads(contract_text)
    if contract.get("schema") != "W7TP_XIAOJ_BUSINESS_BACKEND_OPTIMIZATION_CONTRACT_V1":
        fail("schema_wrong")
    if contract.get("state") != "P1_BACKEND_OPTIMIZATION_REVIEW_READY":
        fail("state_wrong")
    if contract.get("guide") != "docs/product/XIAOJ_BUSINESS_BACKEND_OPTIMIZATION_AND_AV_AI_MERCHANT_SYSTEM_PLAN.md":
        fail("guide_path_wrong")
    surface = contract.get("odoo_backend_surface", {})
    if surface.get("model") != "wuchang.business.backend.optimization":
        fail("odoo_surface_model_missing")
    if surface.get("production_activation_ready") is not False:
        fail("odoo_surface_production_activation_not_false")
    if surface.get("operating_review_service") != "wuchang_cafe_ai_gateway.services.business_backend_optimization.build_business_backend_operating_review_packet":
        fail("operating_review_service_missing")
    if surface.get("process_walkthrough_service") != "wuchang_cafe_ai_gateway.services.business_backend_optimization.build_business_backend_process_walkthrough_packet":
        fail("process_walkthrough_service_missing")
    if surface.get("readiness_scorecard_service") != "wuchang_cafe_ai_gateway.services.business_backend_optimization.build_business_backend_readiness_scorecard_packet":
        fail("readiness_scorecard_service_missing")
    if surface.get("daily_signal_service") != "wuchang_cafe_ai_gateway.services.business_backend_optimization.build_business_backend_daily_signal_packet":
        fail("daily_signal_service_missing")
    if surface.get("av_candidate_quality_service") != "wuchang_cafe_ai_gateway.services.business_backend_optimization.build_business_backend_av_candidate_quality_packet":
        fail("av_candidate_quality_service_missing")
    if surface.get("product_menu_quality_service") != "wuchang_cafe_ai_gateway.services.business_backend_optimization.build_business_backend_product_menu_quality_packet":
        fail("product_menu_quality_service_missing")
    if surface.get("signal_trend_service") != "wuchang_cafe_ai_gateway.services.business_backend_optimization.build_business_backend_signal_trend_packet":
        fail("signal_trend_service_missing")
    if surface.get("management_decision_queue_service") != "wuchang_cafe_ai_gateway.services.business_backend_optimization.build_business_backend_management_decision_queue_packet":
        fail("management_decision_queue_service_missing")
    if surface.get("operator_runbook_service") != "wuchang_cafe_ai_gateway.services.business_backend_optimization.build_business_backend_operator_runbook_packet":
        fail("operator_runbook_service_missing")
    if surface.get("daily_signal_model") != "wuchang.business.backend.daily.signal":
        fail("daily_signal_model_missing")
    if surface.get("av_candidate_model") != "wuchang.business.backend.av.candidate":
        fail("av_candidate_model_missing")
    if surface.get("product_quality_model") != "wuchang.business.backend.product.quality":
        fail("product_quality_model_missing")
    if surface.get("management_decision_item_model") != "wuchang.business.backend.management.decision.item":
        fail("management_decision_item_model_missing")
    if surface.get("decision_item_menu") != "WuChang Cafe / Management Decision Items":
        fail("decision_item_menu_missing")
    daily_signal_contract = contract.get("daily_operating_signals", {})
    if daily_signal_contract.get("schema") != "W7TP_XIAOJ_BUSINESS_BACKEND_DAILY_SIGNAL_PACKET_V1":
        fail("daily_signal_schema_contract_missing")
    if set(daily_signal_contract.get("signal_types", [])) != REQUIRED_DAILY_SIGNAL_TYPES:
        fail("daily_signal_types_contract_wrong")
    product_quality_contract = contract.get("product_menu_quality_review", {})
    if product_quality_contract.get("schema") != "W7TP_XIAOJ_BUSINESS_BACKEND_PRODUCT_MENU_QUALITY_PACKET_V1":
        fail("product_menu_quality_schema_contract_missing")
    if product_quality_contract.get("button") != "Build Product Menu Quality":
        fail("product_menu_quality_button_contract_missing")
    if product_quality_contract.get("model") != "wuchang.business.backend.product.quality":
        fail("product_menu_quality_model_contract_missing")
    if set(product_quality_contract.get("required_refs", [])) != REQUIRED_PRODUCT_MENU_REFS:
        fail("product_menu_quality_required_refs_wrong")
    if set(product_quality_contract.get("blocker_types", [])) != REQUIRED_PRODUCT_MENU_BLOCKERS:
        fail("product_menu_quality_blockers_wrong")
    if product_quality_contract.get("production_activation_ready") is not False:
        fail("product_menu_quality_production_activation_not_false")
    av_candidate_contract = contract.get("av_candidate_quality_review", {})
    if av_candidate_contract.get("schema") != "W7TP_XIAOJ_BUSINESS_BACKEND_AV_CANDIDATE_QUALITY_PACKET_V1":
        fail("av_candidate_quality_schema_contract_missing")
    if av_candidate_contract.get("button") != "Build AV Candidate Quality":
        fail("av_candidate_quality_button_contract_missing")
    if av_candidate_contract.get("model") != "wuchang.business.backend.av.candidate":
        fail("av_candidate_quality_model_contract_missing")
    if set(av_candidate_contract.get("candidate_modalities", [])) != REQUIRED_AV_CANDIDATE_MODALITIES:
        fail("av_candidate_modalities_contract_wrong")
    if set(av_candidate_contract.get("red_flag_types", [])) != REQUIRED_AV_CANDIDATE_RED_FLAGS:
        fail("av_candidate_red_flags_contract_wrong")
    if av_candidate_contract.get("confidence_staff_review_threshold") != 0.75:
        fail("av_candidate_confidence_threshold_wrong")
    if av_candidate_contract.get("production_activation_ready") is not False:
        fail("av_candidate_quality_production_activation_not_false")
    trend_contract = contract.get("signal_trend_review", {})
    if trend_contract.get("schema") != "W7TP_XIAOJ_BUSINESS_BACKEND_SIGNAL_TREND_PACKET_V1":
        fail("signal_trend_schema_contract_missing")
    if trend_contract.get("trend_rules", {}).get("line_incident_count") != "lower_is_better":
        fail("signal_trend_rule_missing")
    decision_queue_contract = contract.get("management_decision_queue", {})
    if decision_queue_contract.get("schema") != "W7TP_XIAOJ_BUSINESS_BACKEND_MANAGEMENT_DECISION_QUEUE_PACKET_V1":
        fail("management_decision_queue_schema_contract_missing")
    if "signal_trend" not in decision_queue_contract.get("sources", []):
        fail("management_decision_queue_sources_missing")
    runbook_contract = contract.get("operator_runbook", {})
    if runbook_contract.get("schema") != "W7TP_XIAOJ_BUSINESS_BACKEND_OPERATOR_RUNBOOK_PACKET_V1":
        fail("operator_runbook_schema_contract_missing")
    if runbook_contract.get("button") != "Build Operator Runbook":
        fail("operator_runbook_button_contract_missing")
    if set(runbook_contract.get("phase_keys", [])) != REQUIRED_RUNBOOK_PHASE_KEYS:
        fail("operator_runbook_phase_keys_contract_wrong")
    if runbook_contract.get("production_activation_ready") is not False:
        fail("operator_runbook_production_activation_not_false")
    scorecard_contract = contract.get("readiness_scorecard", {})
    if scorecard_contract.get("schema") != "W7TP_XIAOJ_BUSINESS_BACKEND_READINESS_SCORECARD_PACKET_V1":
        fail("readiness_scorecard_schema_contract_missing")
    if scorecard_contract.get("minimum_score_before_activation_discussion") != 85:
        fail("readiness_scorecard_minimum_wrong")

    panels = set(contract.get("recommended_backend_panels", []))
    missing_panels = sorted(REQUIRED_PANELS - panels)
    if missing_panels:
        fail(f"missing_panels:{','.join(missing_panels)}")

    if contract.get("end_to_end_flow") != REQUIRED_FLOW:
        fail("end_to_end_flow_wrong")

    ai_features = set(contract.get("ai_technology_features", []))
    missing_features = sorted(REQUIRED_AI_FEATURES - ai_features)
    if missing_features:
        fail(f"missing_ai_features:{','.join(missing_features)}")

    checklist_keys = set(contract.get("backend_checklist_item_keys", []))
    missing_checklist = sorted(REQUIRED_CHECKLIST_KEYS - checklist_keys)
    if missing_checklist:
        fail(f"missing_checklist_keys:{','.join(missing_checklist)}")
    kpi_types = set(contract.get("kpi_snapshot_types", []))
    missing_kpis = sorted(REQUIRED_KPI_TYPES - kpi_types)
    if missing_kpis:
        fail(f"missing_kpi_types:{','.join(missing_kpis)}")
    process_stage_keys = set(contract.get("process_walkthrough_stage_keys", []))
    missing_process_stages = sorted(REQUIRED_PROCESS_STAGE_KEYS - process_stage_keys)
    if missing_process_stages:
        fail(f"missing_process_stage_keys:{','.join(missing_process_stages)}")
    improvement_keys = set(contract.get("process_improvement_item_keys", []))
    missing_improvements = sorted(REQUIRED_IMPROVEMENT_KEYS - improvement_keys)
    if missing_improvements:
        fail(f"missing_improvement_keys:{','.join(missing_improvements)}")

    refs = set()
    for key in [
        "business_continuity_refs",
        "line_domain_api_control_refs",
        "financial_sustainability_refs",
        "local_demonstration_refs",
        "founder_mission_refs",
    ]:
        values = contract.get(key, [])
        if not isinstance(values, list):
            fail(f"refs_not_list:{key}")
        refs.update(values)
    missing_refs = sorted(REQUIRED_REFS - refs)
    if missing_refs:
        fail(f"missing_refs:{','.join(missing_refs)}")

    gates = contract.get("quality_gates", {})
    for key in [
        "no_ai_direct_pos_write",
        "no_ai_direct_payment_capture",
        "no_ai_direct_voucher_mutation",
        "no_ai_invented_price",
        "low_confidence_requires_staff_review",
        "generated_image_not_product_evidence",
        "real_or_staff_approved_product_photo_required",
    ]:
        if gates.get(key) is not True:
            fail(f"quality_gate_not_true:{key}")
    for key in ["raw_audio_saved_in_p1", "raw_video_saved_in_p1", "cloud_model_authority"]:
        if gates.get(key) is not False:
            fail(f"quality_gate_not_false:{key}")

    boundaries = contract.get("subject_boundaries", {})
    if boundaries.get("association_line_official_account_is_not_cafe_line_official_account") is not True:
        fail("association_cafe_oa_boundary_missing")
    if boundaries.get("cafe_must_use_association_approved_subdomain") is not True:
        fail("subdomain_boundary_missing")
    if boundaries.get("vendor_controlled_api_can_write_pos_payment_member_or_line_send") is not False:
        fail("vendor_api_write_boundary_missing")

    context = contract.get("business_context", {})
    if context.get("current_cafe_business_status") != "ACTIVE_BUSINESS_CONTINUES_MANUALLY":
        fail("business_continuity_status_missing")
    if context.get("association_depends_on_cafe_operating_cashflow") is not True:
        fail("association_cafe_dependency_missing")
    if context.get("operator_reported_three_year_debt_increase_ntd") != 2000000:
        fail("three_year_debt_burden_missing")
    if context.get("operator_reported_association_added_full_year_courses") != 3:
        fail("course_expansion_missing")
    if context.get("founder_mission") != "FOUNDER_LIFELONG_MISSION_PUBLIC_SERVICE_COMMITMENT":
        fail("founder_mission_missing")
    if context.get("sanchong_local_readiness") != "SANCHONG_COMMUNITY_SELF_FUNDING_NOT_YET_MATURE":
        fail("sanchong_readiness_missing")

    assert_false_map(contract.get("p1_side_effects", {}), "p1_side_effects")

    service_text = require_text(
        SERVICE,
        [
            "build_business_backend_av_candidate_quality_packet",
            "build_business_backend_product_menu_quality_packet",
            "build_business_backend_optimization_packet",
            "build_business_backend_daily_signal_packet",
            "build_business_backend_signal_trend_packet",
            "build_business_backend_management_decision_queue_packet",
            "build_business_backend_operator_runbook_packet",
            "build_business_backend_operating_review_packet",
            "build_business_backend_process_walkthrough_packet",
            "build_business_backend_readiness_scorecard_packet",
            "W7TP_XIAOJ_BUSINESS_BACKEND_OPTIMIZATION_PACKET_V1",
            "W7TP_XIAOJ_BUSINESS_BACKEND_OPERATING_REVIEW_PACKET_V1",
            "W7TP_XIAOJ_BUSINESS_BACKEND_PROCESS_WALKTHROUGH_PACKET_V1",
            "W7TP_XIAOJ_BUSINESS_BACKEND_READINESS_SCORECARD_PACKET_V1",
            "W7TP_XIAOJ_BUSINESS_BACKEND_DAILY_SIGNAL_PACKET_V1",
            "W7TP_XIAOJ_BUSINESS_BACKEND_AV_CANDIDATE_QUALITY_PACKET_V1",
            "W7TP_XIAOJ_BUSINESS_BACKEND_PRODUCT_MENU_QUALITY_PACKET_V1",
            "W7TP_XIAOJ_BUSINESS_BACKEND_SIGNAL_TREND_PACKET_V1",
            "W7TP_XIAOJ_BUSINESS_BACKEND_MANAGEMENT_DECISION_QUEUE_PACKET_V1",
            "W7TP_XIAOJ_BUSINESS_BACKEND_OPERATOR_RUNBOOK_PACKET_V1",
            "DAILY_SIGNAL_TYPES",
            "AV_AI_CANDIDATE_MODALITIES",
            "AV_AI_CANDIDATE_RED_FLAGS",
            "PRODUCT_MENU_REQUIRED_REFS",
            "PRODUCT_MENU_BLOCKER_TYPES",
            "SIGNAL_TREND_DIRECTIONS",
            "PROCESS_WALKTHROUGH_STEPS",
            "OPERATOR_RUNBOOK_STEPS",
            "RECOMMENDED_BACKEND_PANELS",
            "END_TO_END_FLOW",
            "AI_TECHNOLOGY_FEATURES",
            "side_effects_false",
            "\"external_api_call\": False",
            "\"formal_pos_write\": False",
            "\"payment_capture\": False",
            "\"raw_audio_saved\": False",
            "\"raw_video_saved\": False",
        ],
        "service",
    )
    model_text = require_text(
        MODEL,
        [
            "_name = \"wuchang.business.backend.optimization\"",
            "action_build_review_packet",
            "recommended_backend_panels_json",
            "end_to_end_flow_json",
            "ai_technology_features_json",
            "quality_gates_json",
            "required_refs_json",
            "business_context_json",
            "review_packet_json",
            "operating_review_json",
            "operating_review_next_actions",
            "action_build_operating_review",
            "process_walkthrough_json",
            "process_improvement_next_actions",
            "action_build_process_walkthrough",
            "readiness_scorecard_json",
            "readiness_scorecard_next_actions",
            "readiness_activation_blockers",
            "action_build_readiness_scorecard",
            "daily_signal_ids",
            "daily_signal_review_json",
            "daily_signal_next_actions",
            "action_build_daily_signal_review",
            "av_candidate_ids",
            "av_candidate_quality_json",
            "av_candidate_quality_next_actions",
            "action_build_av_candidate_quality_review",
            "av_candidate_count",
            "low_confidence_candidate_count",
            "failed_validation_candidate_count",
            "generated_image_hold_count",
            "staff_review_required_candidate_count",
            "product_quality_ids",
            "product_menu_quality_json",
            "product_menu_quality_next_actions",
            "action_build_product_menu_quality_review",
            "product_quality_count",
            "product_quality_ready_count",
            "product_quality_blocked_count",
            "missing_custom_options_count",
            "missing_photo_evidence_count",
            "signal_trend_review_json",
            "signal_trend_next_actions",
            "action_build_signal_trend_review",
            "management_decision_queue_json",
            "management_decision_next_actions",
            "action_build_management_decision_queue",
            "management_decision_item_ids",
            "management_decision_count",
            "critical_decision_count",
            "high_decision_count",
            "operator_runbook_json",
            "operator_runbook_next_actions",
            "operator_runbook_step_count",
            "operator_runbook_daily_step_count",
            "operator_runbook_weekly_step_count",
            "action_build_operator_runbook",
            "regressing_signal_count",
            "insufficient_signal_count",
            "daily_signal_count",
            "daily_signal_needs_action_count",
            "daily_signal_observed_day_count",
            "ai_merchant_readiness_score",
            "blocked_improvement_count",
            "critical_open_improvement_count",
            "improvement_item_ids",
            "improvement_item_count",
            "critical_improvement_count",
            "blocked_checklist_count",
            "needs_action_kpi_count",
            "checklist_item_ids",
            "checklist_item_count",
            "kpi_snapshot_ids",
            "kpi_snapshot_count",
            "Secret-shaped or plaintext-shaped material is not allowed",
            "_name = \"wuchang.business.backend.optimization.item\"",
            "_name = \"wuchang.business.backend.improvement.item\"",
            "_name = \"wuchang.business.backend.daily.signal\"",
            "_name = \"wuchang.business.backend.av.candidate\"",
            "_name = \"wuchang.business.backend.product.quality\"",
            "_name = \"wuchang.business.backend.management.decision.item\"",
            "_name = \"wuchang.business.backend.kpi.snapshot\"",
            "decision_key",
            "owner_scope",
            "due_date",
            "evidence_ref",
            "operator_status",
            "daily_revenue_reconciliation",
            "av_ai_candidate_quality",
        ],
        "model",
    )
    require_text(MODEL_INIT, ["business_backend_optimization"], "model_init")
    require_text(
        VIEW,
        [
            "wuchang.business.backend.optimization",
            "Business Backend Optimization",
            "Build Review Packet",
            "Build Operating Review",
            "Build Process Walkthrough",
            "Build Readiness Scorecard",
            "Build Daily Signal Review",
            "Build AV Candidate Quality",
            "Build Product Menu Quality",
            "Build Signal Trend Review",
            "Build Decision Queue",
            "Build Operator Runbook",
            "Backend Panels",
            "Checklist Items",
            "KPI Snapshots",
            "Daily Signals",
            "AV AI Candidates",
            "Product Menu Quality",
            "Process Improvements",
            "Process Walkthrough",
            "Readiness Scorecard",
            "Daily Signal Review",
            "AV Candidate Quality Review",
            "Product Menu Quality Review",
            "Signal Trend Review",
            "Decision Queue",
            "Operator Runbook",
            "Management Decision Items",
            "action_wuchang_business_backend_management_decision_item",
            "menu_wuchang_business_backend_management_decision_item",
            "filter_priority_critical",
            "filter_priority_high",
            "filter_status_blocked",
            "filter_ready_for_review",
            "filter_overdue",
            "group_owner",
            "Operating Review",
            "End-To-End Flow",
            "AV AI Features",
            "Quality Gates",
            "Required Refs",
            "Business Context",
            "P1 Side Effect Boundary",
        ],
        "view",
    )
    require_text(
        ACCESS,
        [
            "model_wuchang_business_backend_optimization",
            "model_wuchang_business_backend_optimization_item",
            "model_wuchang_business_backend_kpi_snapshot",
            "model_wuchang_business_backend_improvement_item",
            "model_wuchang_business_backend_daily_signal",
            "model_wuchang_business_backend_av_candidate",
            "model_wuchang_business_backend_product_quality",
            "model_wuchang_business_backend_management_decision_item",
            "access_wuchang_business_backend_optimization_user",
            "access_wuchang_business_backend_optimization_admin",
            "access_wuchang_business_backend_optimization_item_user",
            "access_wuchang_business_backend_kpi_snapshot_user",
            "access_wuchang_business_backend_improvement_item_user",
            "access_wuchang_business_backend_daily_signal_user",
            "access_wuchang_business_backend_av_candidate_user",
            "access_wuchang_business_backend_product_quality_user",
            "access_wuchang_business_backend_management_decision_item_user",
        ],
        "access",
    )
    require_text(MANIFEST, ["business_backend_optimization_views.xml"], "manifest")

    service = load_service()
    packet = service.build_business_backend_optimization_packet(
        actor_ref="ACTOR_REF_VERIFY",
        input_ref="VERIFY_BACKEND_OPTIMIZATION",
    )
    if packet.get("schema") != "W7TP_XIAOJ_BUSINESS_BACKEND_OPTIMIZATION_PACKET_V1":
        fail("service_packet_schema_wrong")
    if packet.get("state") != "P1_BACKEND_OPTIMIZATION_REVIEW_READY":
        fail("service_packet_state_wrong")
    assert_false_map(packet.get("side_effects", {}), "packet_side_effects")
    assert_no_secret_shape(json.dumps(packet, ensure_ascii=False, sort_keys=True), "packet")
    if packet.get("production_activation_ready") is not False:
        fail("packet_production_activation_not_false")
    if set(packet.get("recommended_backend_panels", [])) != REQUIRED_PANELS:
        fail("packet_panels_wrong")
    if packet.get("end_to_end_flow") != REQUIRED_FLOW:
        fail("packet_flow_wrong")
    if set(packet.get("ai_technology_features", [])) != REQUIRED_AI_FEATURES:
        fail("packet_ai_features_wrong")
    packet_checklist_keys = {
        item.get("item_key")
        for item in packet.get("backend_checklist_items", [])
        if isinstance(item, dict)
    }
    if packet_checklist_keys != REQUIRED_CHECKLIST_KEYS:
        fail("packet_checklist_keys_wrong")
    if set(packet.get("kpi_snapshot_types", [])) != REQUIRED_KPI_TYPES:
        fail("packet_kpi_types_wrong")
    packet_process_stage_keys = {
        item.get("stage_key")
        for item in packet.get("process_walkthrough_steps", [])
        if isinstance(item, dict)
    }
    if packet_process_stage_keys != REQUIRED_PROCESS_STAGE_KEYS:
        fail("packet_process_stage_keys_wrong")
    process_walkthrough = service.build_business_backend_process_walkthrough_packet(
        actor_ref="ACTOR_REF_VERIFY",
        input_ref="VERIFY_PROCESS_WALKTHROUGH",
        completed_improvement_keys=["unified_entry_intake_board"],
    )
    if process_walkthrough.get("schema") != "W7TP_XIAOJ_BUSINESS_BACKEND_PROCESS_WALKTHROUGH_PACKET_V1":
        fail("process_walkthrough_schema_wrong")
    if process_walkthrough.get("state") != "P1_PROCESS_WALKTHROUGH_READY":
        fail("process_walkthrough_state_wrong")
    assert_false_map(process_walkthrough.get("side_effects", {}), "process_walkthrough_side_effects")
    if process_walkthrough.get("production_activation_ready") is not False:
        fail("process_walkthrough_production_activation_not_false")
    improvement_keys = {
        item.get("improvement_key")
        for item in process_walkthrough.get("improvement_items", [])
        if isinstance(item, dict)
    }
    if improvement_keys != REQUIRED_IMPROVEMENT_KEYS:
        fail("process_walkthrough_improvement_keys_wrong")
    if process_walkthrough.get("critical_improvement_count") != 2:
        fail("process_walkthrough_critical_count_wrong")
    if not process_walkthrough.get("next_actions"):
        fail("process_walkthrough_next_actions_missing")
    product_menu_quality = service.build_business_backend_product_menu_quality_packet(
        products=[
            {
                "product_ref": "PRODUCT_REF_READY",
                "odoo_product_ref": "ODOO_PRODUCT_REF_READY",
                "menu_category_ref": "MENU_CATEGORY_REF",
                "price_ref": "PRICE_REF_READY",
                "custom_options_ref": "CUSTOM_OPTIONS_REF_READY",
                "photo_evidence_ref": "REAL_PHOTO_REF_READY",
                "photo_evidence_state": "real_photo_ref",
                "availability_state": "available",
                "ai_candidate_state": "allowed_candidate",
            },
            {
                "product_ref": "PRODUCT_REF_BLOCKED",
                "odoo_product_ref": "ODOO_PRODUCT_REF_BLOCKED",
                "menu_category_ref": "MENU_CATEGORY_REF",
                "price_ref": "",
                "custom_options_ref": "",
                "photo_evidence_ref": "",
                "photo_evidence_state": "generated_image_only",
                "availability_state": "inactive",
                "ai_candidate_state": "blocked",
            },
        ],
        actor_ref="ACTOR_REF_VERIFY",
        input_ref="VERIFY_PRODUCT_MENU_QUALITY",
    )
    if product_menu_quality.get("schema") != "W7TP_XIAOJ_BUSINESS_BACKEND_PRODUCT_MENU_QUALITY_PACKET_V1":
        fail("product_menu_quality_schema_wrong")
    if product_menu_quality.get("state") != "P1_PRODUCT_MENU_QUALITY_REVIEW_READY":
        fail("product_menu_quality_state_wrong")
    assert_false_map(product_menu_quality.get("side_effects", {}), "product_menu_quality_side_effects")
    if product_menu_quality.get("production_activation_ready") is not False:
        fail("product_menu_quality_production_activation_not_false")
    if set(product_menu_quality.get("required_refs", [])) != REQUIRED_PRODUCT_MENU_REFS:
        fail("product_menu_quality_required_refs_wrong")
    if set(product_menu_quality.get("blocker_types", [])) != REQUIRED_PRODUCT_MENU_BLOCKERS:
        fail("product_menu_quality_blocker_types_wrong")
    if product_menu_quality.get("ready_product_count") != 1:
        fail("product_menu_quality_ready_count_wrong")
    if product_menu_quality.get("blocked_product_count") != 1:
        fail("product_menu_quality_blocked_count_wrong")
    if product_menu_quality.get("missing_custom_options_count") != 1:
        fail("product_menu_quality_missing_custom_options_wrong")
    if product_menu_quality.get("missing_photo_evidence_count") != 1:
        fail("product_menu_quality_missing_photo_wrong")
    blockers = product_menu_quality.get("blocker_counts", {})
    for blocker in ["missing_price_ref", "missing_custom_options_ref", "generated_image_only", "inactive_or_unavailable"]:
        if blockers.get(blocker, 0) < 1:
            fail(f"product_menu_quality_blocker_missing:{blocker}")
    assert_no_secret_shape(json.dumps(product_menu_quality, ensure_ascii=False, sort_keys=True), "product_menu_quality")
    av_candidate_quality = service.build_business_backend_av_candidate_quality_packet(
        candidates=[
            {
                "candidate_ref": "AV_CANDIDATE_REF_LOW_CONF",
                "modality": "audio_intent",
                "review_state": "needs_staff_review",
                "confidence_score": 0.62,
                "odoo_validation_state": "needs_staff_review",
                "product_photo_evidence_state": "missing",
                "red_flags": ["custom_option_unmapped"],
                "evidence_ref": "AV_SAFE_REF_1",
            },
            {
                "candidate_ref": "AV_CANDIDATE_REF_GENERATED_IMAGE",
                "modality": "product_image_candidate",
                "review_state": "draft",
                "confidence_score": 0.91,
                "odoo_validation_state": "failed",
                "product_photo_evidence_state": "generated_candidate_only",
                "red_flags": [],
                "evidence_ref": "AV_SAFE_REF_2",
            },
        ],
        actor_ref="ACTOR_REF_VERIFY",
        input_ref="VERIFY_AV_CANDIDATE_QUALITY",
    )
    if av_candidate_quality.get("schema") != "W7TP_XIAOJ_BUSINESS_BACKEND_AV_CANDIDATE_QUALITY_PACKET_V1":
        fail("av_candidate_quality_schema_wrong")
    if av_candidate_quality.get("state") != "P1_AV_CANDIDATE_QUALITY_REVIEW_READY":
        fail("av_candidate_quality_state_wrong")
    assert_false_map(av_candidate_quality.get("side_effects", {}), "av_candidate_quality_side_effects")
    if av_candidate_quality.get("production_activation_ready") is not False:
        fail("av_candidate_quality_production_activation_not_false")
    if set(av_candidate_quality.get("candidate_modalities", [])) != REQUIRED_AV_CANDIDATE_MODALITIES:
        fail("av_candidate_quality_modalities_wrong")
    if set(av_candidate_quality.get("red_flag_types", [])) != REQUIRED_AV_CANDIDATE_RED_FLAGS:
        fail("av_candidate_quality_red_flags_wrong")
    if av_candidate_quality.get("low_confidence_count") != 1:
        fail("av_candidate_quality_low_confidence_count_wrong")
    if av_candidate_quality.get("failed_validation_count") != 1:
        fail("av_candidate_quality_failed_validation_count_wrong")
    if av_candidate_quality.get("generated_image_hold_count") != 1:
        fail("av_candidate_quality_generated_image_hold_count_wrong")
    if av_candidate_quality.get("staff_review_required_count") != 2:
        fail("av_candidate_quality_staff_review_count_wrong")
    if not av_candidate_quality.get("next_actions"):
        fail("av_candidate_quality_next_actions_missing")
    assert_no_secret_shape(json.dumps(av_candidate_quality, ensure_ascii=False, sort_keys=True), "av_candidate_quality")
    operator_runbook = service.build_business_backend_operator_runbook_packet(
        actor_ref="ACTOR_REF_VERIFY",
        input_ref="VERIFY_OPERATOR_RUNBOOK",
    )
    if operator_runbook.get("schema") != "W7TP_XIAOJ_BUSINESS_BACKEND_OPERATOR_RUNBOOK_PACKET_V1":
        fail("operator_runbook_schema_wrong")
    if operator_runbook.get("state") != "P1_OPERATOR_RUNBOOK_READY":
        fail("operator_runbook_state_wrong")
    assert_false_map(operator_runbook.get("side_effects", {}), "operator_runbook_side_effects")
    if operator_runbook.get("production_activation_ready") is not False:
        fail("operator_runbook_production_activation_not_false")
    if set(operator_runbook.get("phase_keys", [])) != REQUIRED_RUNBOOK_PHASE_KEYS:
        fail("operator_runbook_phase_keys_wrong")
    if operator_runbook.get("step_count") != len(REQUIRED_RUNBOOK_PHASE_KEYS):
        fail("operator_runbook_step_count_wrong")
    if operator_runbook.get("daily_step_count", 0) < 5:
        fail("operator_runbook_daily_step_count_wrong")
    if operator_runbook.get("weekly_step_count", 0) < 3:
        fail("operator_runbook_weekly_step_count_wrong")
    for phase in ["daily_close_signal_entry", "weekly_sustainability_review", "total_field_packet_review"]:
        if phase not in operator_runbook.get("phase_keys", []):
            fail(f"operator_runbook_phase_missing:{phase}")
    daily_signal = service.build_business_backend_daily_signal_packet(
        daily_signals=[
            {
                "signal_date": "2026-07-02",
                "signal_type": "order_count_signal",
                "state": "observed",
                "numeric_value": 12,
                "unit": "count",
                "evidence_ref": "DAILY_CLOSE_REF",
                "summary": "safe daily order signal",
            },
            {
                "signal_date": "2026-07-02",
                "signal_type": "line_incident_count",
                "state": "needs_action",
                "numeric_value": 1,
                "unit": "count",
                "evidence_ref": "LINE_INCIDENT_REF",
                "summary": "safe incident summary",
            },
        ],
        actor_ref="ACTOR_REF_VERIFY",
        input_ref="VERIFY_DAILY_SIGNAL",
    )
    if daily_signal.get("schema") != "W7TP_XIAOJ_BUSINESS_BACKEND_DAILY_SIGNAL_PACKET_V1":
        fail("daily_signal_schema_wrong")
    if daily_signal.get("state") != "P1_DAILY_SIGNAL_REVIEW_READY":
        fail("daily_signal_state_wrong")
    assert_false_map(daily_signal.get("side_effects", {}), "daily_signal_side_effects")
    if daily_signal.get("production_activation_ready") is not False:
        fail("daily_signal_production_activation_not_false")
    if "revenue_signal" not in daily_signal.get("missing_signal_types", []):
        fail("daily_signal_missing_types_wrong")
    if not daily_signal.get("needs_action_signals"):
        fail("daily_signal_needs_action_missing")
    signal_trend = service.build_business_backend_signal_trend_packet(
        daily_signals=[
            {
                "signal_date": "2026-07-01",
                "signal_type": "revenue_signal",
                "state": "observed",
                "numeric_value": 1000,
                "evidence_ref": "REV_DAY_1",
            },
            {
                "signal_date": "2026-07-02",
                "signal_type": "revenue_signal",
                "state": "observed",
                "numeric_value": 1200,
                "evidence_ref": "REV_DAY_2",
            },
            {
                "signal_date": "2026-07-01",
                "signal_type": "line_incident_count",
                "state": "observed",
                "numeric_value": 0,
                "evidence_ref": "LINE_DAY_1",
            },
            {
                "signal_date": "2026-07-02",
                "signal_type": "line_incident_count",
                "state": "needs_action",
                "numeric_value": 2,
                "evidence_ref": "LINE_DAY_2",
            },
        ],
        actor_ref="ACTOR_REF_VERIFY",
        input_ref="VERIFY_SIGNAL_TREND",
    )
    if signal_trend.get("schema") != "W7TP_XIAOJ_BUSINESS_BACKEND_SIGNAL_TREND_PACKET_V1":
        fail("signal_trend_schema_wrong")
    if signal_trend.get("state") != "P1_SIGNAL_TREND_REVIEW_READY":
        fail("signal_trend_state_wrong")
    assert_false_map(signal_trend.get("side_effects", {}), "signal_trend_side_effects")
    if signal_trend.get("production_activation_ready") is not False:
        fail("signal_trend_production_activation_not_false")
    trend_by_type = {
        item.get("signal_type"): item.get("trend_state")
        for item in signal_trend.get("trend_items", [])
        if isinstance(item, dict)
    }
    if trend_by_type.get("revenue_signal") != "improving":
        fail("signal_trend_revenue_not_improving")
    if trend_by_type.get("line_incident_count") != "regressing":
        fail("signal_trend_line_incident_not_regressing")
    if "order_count_signal" not in signal_trend.get("insufficient_signal_types", []):
        fail("signal_trend_insufficient_missing")
    readiness_scorecard = service.build_business_backend_readiness_scorecard_packet(
        checklist_items=[
            {"item_key": "manual_order_fallback", "operator_status": "done"},
            {"item_key": "release_gate_board", "operator_status": "blocked"},
        ],
        kpi_snapshots=[
            {"snapshot_type": "daily_revenue_reconciliation", "state": "observed"},
            {"snapshot_type": "release_blocker_count", "state": "needs_action"},
        ],
        improvement_items=[
            {"improvement_key": "release_gate_blocker_board", "priority": "critical", "operator_status": "todo"},
            {"improvement_key": "line_subject_scope_dashboard", "priority": "critical", "operator_status": "blocked"},
        ],
        actor_ref="ACTOR_REF_VERIFY",
        input_ref="VERIFY_READINESS_SCORECARD",
    )
    if readiness_scorecard.get("schema") != "W7TP_XIAOJ_BUSINESS_BACKEND_READINESS_SCORECARD_PACKET_V1":
        fail("readiness_scorecard_schema_wrong")
    if readiness_scorecard.get("state") != "P1_IMPROVEMENT_REQUIRED":
        fail("readiness_scorecard_state_wrong")
    assert_false_map(readiness_scorecard.get("side_effects", {}), "readiness_scorecard_side_effects")
    if readiness_scorecard.get("production_activation_ready") is not False:
        fail("readiness_scorecard_production_activation_not_false")
    if readiness_scorecard.get("readiness_score") >= 85:
        fail("readiness_scorecard_score_too_high_for_blocked_fixture")
    blockers = set(readiness_scorecard.get("activation_blockers", []))
    for blocker in [
        "blocked_checklist_items",
        "needs_action_kpis",
        "blocked_process_improvements",
        "critical_process_improvements_open",
        "readiness_score_below_85",
    ]:
        if blocker not in blockers:
            fail(f"readiness_scorecard_blocker_missing:{blocker}")
    operating_review = service.build_business_backend_operating_review_packet(
        checklist_items=[
            {
                "panel": "business_continuity_cockpit",
                "item_key": "manual_order_fallback",
                "required_ref": "manual_order_fallback_ref",
                "operator_status": "blocked",
            }
        ],
        kpi_snapshots=[
            {
                "snapshot_type": "daily_revenue_reconciliation",
                "state": "needs_action",
                "evidence_ref": "DAILY_REVENUE_RECONCILIATION_REF",
                "summary": "safe summary",
            }
        ],
        actor_ref="ACTOR_REF_VERIFY",
        input_ref="VERIFY_OPERATING_REVIEW",
    )
    if operating_review.get("schema") != "W7TP_XIAOJ_BUSINESS_BACKEND_OPERATING_REVIEW_PACKET_V1":
        fail("operating_review_schema_wrong")
    if operating_review.get("state") != "P1_OPERATING_REVIEW_READY":
        fail("operating_review_state_wrong")
    assert_false_map(operating_review.get("side_effects", {}), "operating_review_side_effects")
    if operating_review.get("production_activation_ready") is not False:
        fail("operating_review_production_activation_not_false")
    if not operating_review.get("blocked_checklist_items"):
        fail("operating_review_blocked_items_missing")
    if not operating_review.get("needs_action_kpis"):
        fail("operating_review_needs_action_kpis_missing")
    if "release_blocker_count" not in operating_review.get("missing_kpi_types", []):
        fail("operating_review_missing_kpi_types_wrong")
    decision_queue = service.build_business_backend_management_decision_queue_packet(
        signal_trend_packet=signal_trend,
        readiness_scorecard_packet=readiness_scorecard,
        operating_review_packet=operating_review,
        actor_ref="ACTOR_REF_VERIFY",
        input_ref="VERIFY_DECISION_QUEUE",
    )
    if decision_queue.get("schema") != "W7TP_XIAOJ_BUSINESS_BACKEND_MANAGEMENT_DECISION_QUEUE_PACKET_V1":
        fail("decision_queue_schema_wrong")
    if decision_queue.get("state") != "P1_MANAGEMENT_DECISION_QUEUE_READY":
        fail("decision_queue_state_wrong")
    assert_false_map(decision_queue.get("side_effects", {}), "decision_queue_side_effects")
    if decision_queue.get("production_activation_ready") is not False:
        fail("decision_queue_production_activation_not_false")
    counts = decision_queue.get("counts_by_priority", {})
    if counts.get("critical", 0) < 1 or counts.get("high", 0) < 1:
        fail("decision_queue_priority_counts_wrong")
    first_priority = decision_queue.get("decision_items", [{}])[0].get("priority")
    if first_priority != "critical":
        fail("decision_queue_not_sorted")
    for item in packet.get("backend_checklist_items", []):
        if not item.get("required_ref") or not item.get("success_metric") or item.get("phase") != "P1_REVIEW":
            fail("packet_checklist_item_incomplete")
    if "\"model_invocation\": False" not in service_text or "raw_video_saved" not in model_text:
        fail("service_or_model_side_effect_boundary_missing")

    for needle in [
        "Business Continuity Cockpit",
        "AV AI Merchant Quality Panel",
        "Financial Sustainability Panel",
        "Sanchong Demonstration and Community Self-Funding Panel",
        "Founder Mission Sustainability Panel",
        "Model: wuchang.business.backend.optimization",
        "manual_order_fallback",
        "operator_burden_reduction",
        "daily_revenue_reconciliation",
        "release_blocker_count",
        "W7TP_XIAOJ_BUSINESS_BACKEND_OPERATING_REVIEW_PACKET_V1",
        "W7TP_XIAOJ_BUSINESS_BACKEND_PROCESS_WALKTHROUGH_PACKET_V1",
        "W7TP_XIAOJ_BUSINESS_BACKEND_READINESS_SCORECARD_PACKET_V1",
        "W7TP_XIAOJ_BUSINESS_BACKEND_DAILY_SIGNAL_PACKET_V1",
        "W7TP_XIAOJ_BUSINESS_BACKEND_AV_CANDIDATE_QUALITY_PACKET_V1",
        "W7TP_XIAOJ_BUSINESS_BACKEND_PRODUCT_MENU_QUALITY_PACKET_V1",
        "W7TP_XIAOJ_BUSINESS_BACKEND_SIGNAL_TREND_PACKET_V1",
        "W7TP_XIAOJ_BUSINESS_BACKEND_MANAGEMENT_DECISION_QUEUE_PACKET_V1",
        "W7TP_XIAOJ_BUSINESS_BACKEND_OPERATOR_RUNBOOK_PACKET_V1",
        "Build Operating Review",
        "Build Process Walkthrough",
        "Build Readiness Scorecard",
        "Build Daily Signal Review",
        "Build AV Candidate Quality",
        "Build Product Menu Quality",
        "Build Signal Trend Review",
        "Build Decision Queue",
        "Build Operator Runbook",
        "Process walkthrough output",
        "Readiness scorecard output",
        "Daily signal review output",
        "AV candidate quality review output",
        "Product/menu quality review output",
        "Model: wuchang.business.backend.av.candidate",
        "Model: wuchang.business.backend.product.quality",
        "audio_intent",
        "video_product_recognition",
        "generated_image_not_product_evidence",
        "confidence below 0.75 requires staff review",
        "missing_custom_options_ref",
        "missing_photo_evidence_ref",
        "Product/menu quality is the authority bridge",
        "Signal trend review output",
        "Management decision queue output",
        "Operator runbook output",
        "daily_close_signal_entry",
        "weekly_sustainability_review",
        "total_field_packet_review",
        "Model: wuchang.business.backend.management.decision.item",
        "Menu: WuChang Cafe / Management Decision Items",
        "Statuses: todo, in_progress, blocked, ready_for_review, done",
        "Default filters: Critical, High, Open",
        "order_count_signal",
        "manual_fallback_status",
        "unified_entry_intake_board",
        "line_subject_scope_dashboard",
        "WuChang Cafe / Business Backend Optimization",
        "P1 must not",
        "no raw audio saved in P1",
        "no direct POS write by AI",
    ]:
        if needle not in guide_text:
            fail(f"guide_missing:{needle}")

    print("STATE=PASS_XIAOJ_BUSINESS_BACKEND_OPTIMIZATION")
    print("BACKEND_OPTIMIZATION_REVIEW_READY=TRUE")
    print("AV_AI_MERCHANT_QUALITY_GATES=TRUE")
    print("PRODUCTION_ACTIVATION_READY=FALSE")
    print("EXTERNAL_API_CALL=FALSE")
    print("FORMAL_POS_WRITE=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
