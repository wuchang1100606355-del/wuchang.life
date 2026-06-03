from runtime_adapters.finance_accounting_review_policy import (
    evaluate_finance_review_packet,
    policy_health,
)


def packet(event_type="zero_eps_esg_allocation_review", **overrides):
    data = {
        "packet_id": "fin_review_001",
        "event_type": event_type,
        "node_scope": "association",
        "economy_unit": "twd",
        "amount": 1000,
        "visibility": "permissioned_auditable",
        "subject_visible": True,
        "summary_visible": True,
        "detail_visible": False,
        "voucher_visible": False,
        "reserve_ratio_after": 0.75,
        "fund_pool_survival_months": 6,
        "audit_required": True,
        "physical_delete_allowed": False,
        "created_at": "2026-05-13T00:00:00+08:00",
    }
    data.update(overrides)
    return data


def test_policy_health_is_review_only():
    health = policy_health()
    assert health["finance_accounting_review"] == "ok"
    assert health["payment_execution_allowed"] is False
    assert health["odoo_account_mutation_allowed"] is False
    assert health["physical_delete_allowed"] is False


def test_zero_eps_allocation_prepares_review_packet_only():
    result = evaluate_finance_review_packet(packet())
    assert result["allowed"] is True
    assert result["risk_level"] == "L2"
    assert result["action"] == "prepare_accounting_review_packet"
    assert result["accounting_approved"] is False
    assert result["payment_allowed"] is False
    assert result["odoo_mutation_allowed"] is False
    assert result["accountant_review_required"] is True


def test_public_summary_allowed_without_details():
    result = evaluate_finance_review_packet(
        packet(
            event_type="public_account_summary_publish",
            visibility="public_24h",
            cloud_sync_requested=True,
        )
    )
    assert result["allowed"] is True
    assert result["risk_level"] == "L1"
    assert result["action"] == "allow_public_summary_with_audit"


def test_public_summary_blocks_detail_visibility():
    result = evaluate_finance_review_packet(
        packet(
            event_type="public_account_summary_publish",
            visibility="public_24h",
            detail_visible=True,
        )
    )
    assert result["allowed"] is False
    assert "public_detail_visibility_forbidden" in result["errors"]


def test_payment_execute_blocked():
    result = evaluate_finance_review_packet(packet(event_type="payment_execute"))
    assert result["allowed"] is False
    assert result["risk_level"] == "L3"
    assert "blocked_event:payment_execute" in result["errors"]


def test_public_asset_private_conversion_blocked():
    result = evaluate_finance_review_packet(packet(private_gain_distribution_requested=True))
    assert result["allowed"] is False
    assert "private_gain_distribution_requested_forbidden" in result["errors"]


def test_happiness_coin_requires_review_and_not_legal_tender():
    result = evaluate_finance_review_packet(
        packet(
            event_type="happiness_coin_issue_draft",
            economy_unit="happiness_coin",
            treated_as_legal_tender=True,
        )
    )
    assert result["allowed"] is False
    assert "community_unit_must_not_be_legal_tender" in result["errors"]


def test_low_reserve_ratio_warns_but_keeps_review_route():
    result = evaluate_finance_review_packet(packet(reserve_ratio_after=0.25))
    assert result["allowed"] is True
    assert result["risk_level"] == "L2"
    assert "reserve_ratio_below_review_threshold" in result["warnings"]
