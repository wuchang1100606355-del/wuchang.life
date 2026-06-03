#!/usr/bin/env python3
"""Local-only finance/accounting review policy for Wuchang community economy.

This module prepares governance decisions for human/accountant review. It does
not approve payments, mutate Odoo accounting, issue tokens as financial
products, or publish sensitive details.
"""

from __future__ import annotations

from typing import Any


L3_EVENTS = {
    "payment_execute",
    "refund_execute",
    "private_profit_distribution",
    "public_asset_private_conversion",
    "physical_delete_accounting_record",
    "credential_or_secret_access",
    "cloud_plaintext_publish",
    "business_secret_publication",
    "member_plaintext_publication",
    "ai_final_accounting_approval",
}

REVIEW_EVENTS = {
    "resident_purchase_summary",
    "community_revenue_share_draft",
    "happiness_coin_issue_draft",
    "merchant_ticket_credit_draft",
    "fund_pool_retention_draft",
    "labor_compensation_review",
    "intellectual_contribution_review",
    "wrong_entry_correction_review",
    "public_account_summary_publish",
    "zero_eps_esg_allocation_review",
}

PUBLIC_SUMMARY_EVENTS = {
    "public_account_summary_publish",
    "fund_pool_retention_summary",
    "esg_metric_summary",
}

BLOCKED_FLAGS = {
    "payment_execution_requested",
    "odoo_account_mutation_requested",
    "physical_delete_requested",
    "private_gain_distribution_requested",
    "member_plaintext_included",
    "secret_material_included",
    "credential_material_included",
    "individual_transaction_detail_public",
    "business_secret_public",
    "ai_final_accounting_decision_requested",
}


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def evaluate_finance_review_packet(packet: dict[str, Any]) -> dict[str, Any]:
    """Return a governance result for a non-executing finance review packet."""

    if not isinstance(packet, dict):
        return _block(["packet_not_object"], "packet must be a dict")

    errors: list[str] = []
    warnings: list[str] = []

    event_type = _text(packet.get("event_type"))
    node_scope = _text(packet.get("node_scope"))
    visibility = _text(packet.get("visibility"), "permissioned_auditable")
    economy_unit = _text(packet.get("economy_unit"), "twd")
    amount = _num(packet.get("amount"))
    reserve_ratio_after = _num(packet.get("reserve_ratio_after"), default=-1)
    fund_pool_survival_months = _num(packet.get("fund_pool_survival_months"), default=-1)

    if not event_type:
        errors.append("missing_event_type")
    if not node_scope:
        errors.append("missing_node_scope")
    if amount < 0 and event_type != "wrong_entry_correction_review":
        warnings.append("negative_amount_requires_accounting_note")

    for flag in BLOCKED_FLAGS:
        if packet.get(flag) is True:
            errors.append(f"{flag}_forbidden")

    if event_type in L3_EVENTS:
        errors.append(f"blocked_event:{event_type}")

    if visibility == "public_24h":
        if packet.get("detail_visible") is True:
            errors.append("public_detail_visibility_forbidden")
        if packet.get("voucher_visible") is True:
            errors.append("public_voucher_visibility_forbidden")
        if packet.get("summary_visible") is not True or packet.get("subject_visible") is not True:
            warnings.append("public_summary_should_include_subject_and_summary")

    if packet.get("cloud_sync_requested") is True and visibility != "public_24h":
        errors.append("cloud_sync_only_allowed_for_public_24h_summary")

    if economy_unit in {"happiness_coin", "merchant_ticket_credit"}:
        if packet.get("treated_as_legal_tender") is True:
            errors.append("community_unit_must_not_be_legal_tender")
        if packet.get("investment_promise_included") is True:
            errors.append("community_unit_investment_promise_forbidden")
        warnings.append("community_unit_requires_accounting_review")

    if reserve_ratio_after >= 0 and reserve_ratio_after < 0.5:
        warnings.append("reserve_ratio_below_review_threshold")
    if fund_pool_survival_months >= 0 and fund_pool_survival_months < 3:
        warnings.append("fund_pool_survival_below_three_months")

    if errors:
        return _block(errors, "unsafe finance/accounting request", warnings)

    if event_type in PUBLIC_SUMMARY_EVENTS and visibility == "public_24h":
        return {
            "allowed": True,
            "risk_level": "L1",
            "action": "allow_public_summary_with_audit",
            "route": "public_summary_pipeline",
            "accounting_approved": False,
            "payment_allowed": False,
            "odoo_mutation_allowed": False,
            "requires_human_confirmation": False,
            "accountant_review_required": False,
            "audit_required": True,
            "rollback_required": True,
            "reason": "public subject/summary only; details and vouchers remain hidden",
            "errors": [],
            "warnings": warnings,
        }

    if event_type in REVIEW_EVENTS:
        return {
            "allowed": True,
            "risk_level": "L2",
            "action": "prepare_accounting_review_packet",
            "route": "accounting_human_review_queue",
            "accounting_approved": False,
            "payment_allowed": False,
            "odoo_mutation_allowed": False,
            "requires_human_confirmation": True,
            "accountant_review_required": True,
            "audit_required": True,
            "rollback_required": True,
            "reason": "review packet only; formal accounting requires human/accountant window",
            "errors": [],
            "warnings": warnings,
        }

    return {
        "allowed": False,
        "risk_level": "L2",
        "action": "warn",
        "route": "policy_review_queue",
        "accounting_approved": False,
        "payment_allowed": False,
        "odoo_mutation_allowed": False,
        "requires_human_confirmation": True,
        "accountant_review_required": True,
        "audit_required": True,
        "rollback_required": False,
        "reason": f"uncatalogued finance event requires policy review: {event_type}",
        "errors": [],
        "warnings": warnings + [f"uncatalogued_event:{event_type}"],
    }


def _block(errors: list[str], reason: str, warnings: list[str] | None = None) -> dict[str, Any]:
    return {
        "allowed": False,
        "risk_level": "L3",
        "action": "block",
        "route": "deadbox",
        "accounting_approved": False,
        "payment_allowed": False,
        "odoo_mutation_allowed": False,
        "requires_human_confirmation": True,
        "accountant_review_required": True,
        "audit_required": True,
        "rollback_required": False,
        "reason": reason,
        "errors": errors,
        "warnings": warnings or [],
    }


def policy_health() -> dict[str, Any]:
    return {
        "finance_accounting_review": "ok",
        "mode": "review_packet_only",
        "payment_execution_allowed": False,
        "odoo_account_mutation_allowed": False,
        "ai_final_accounting_approval_allowed": False,
        "public_summary_detail_allowed": False,
        "physical_delete_allowed": False,
    }
