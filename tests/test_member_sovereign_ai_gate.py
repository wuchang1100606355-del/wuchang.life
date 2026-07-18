from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATEWAY_PATH = (
    ROOT
    / "deploy/packages/taiji01_metric_identity_gateway_v0_1/taiji01_metric_identity_gateway.py"
)


def load_gateway():
    spec = importlib.util.spec_from_file_location("member_sovereign_gateway", GATEWAY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gateway = load_gateway()


def authority(**overrides):
    value = {
        "local_source_ref": "odoo:wuchang.member.identity.code:SYNTHETIC-0001",
        "issuer": "taiji01:odoo-member-authority",
        "purpose": "association_member_service",
        "service_scope": "association",
        "target_system": "association_system",
        "identity_state": "registered",
        "subject_types": ["association_member", "volunteer"],
        "role_refs": ["role:association_member"],
        "qualification_states": {"association_member": True, "volunteer": True},
        "consent_state": "granted",
        "authorization_scopes": [
            "membership_status_reference",
            "volunteer_status_reference",
        ],
        "qualification_source_refs": ["odoo:wuchang.member.identity.code:SYNTHETIC-0001"],
        "consent_record_ref": "odoo:wuchang.member.consent.ledger:SYNTHETIC-0001",
        "local_state_check_ref": "taiji01:member-authority-state-check:v1",
        "verified_at": "2026-07-15T18:00:00Z",
        "issued_at": "2026-07-15T18:00:00Z",
        "expires_at": "2026-07-15T18:15:00Z",
        "nonce": "synthetic-nonce-0001",
    }
    value.update(overrides)
    return value


def request_state(**overrides):
    value = {
        "purpose": "association_member_service",
        "target_system": "association_system",
        "requested_scopes": ["membership_status_reference"],
        "current_authority_state": {
            "identity_state": "registered",
            "consent_state": "granted",
            "consent_record_ref": "odoo:wuchang.member.consent.ledger:SYNTHETIC-0001",
            "checked_at": "2026-07-15T18:01:00Z",
        },
    }
    value.update(overrides)
    return value


def test_registered_member_gets_only_minimum_disclosure() -> None:
    packet = gateway.issue_member_sovereign_packet(authority())
    result = gateway.evaluate_member_authorization(
        packet, request_state(), "2026-07-15T18:02:00Z"
    )
    assert result["decision"] == "allow"
    assert result["member_plaintext_included"] is False
    assert set(result["minimum_disclosure"]) == {
        "subject_ref",
        "role_refs",
        "qualification_states",
        "authorization_scopes",
        "valid_until",
        "source_refs",
        "verifier_result",
    }
    assert not gateway._forbidden_member_paths(result)


def test_anonymous_packet_allows_only_scope_free_public_entry() -> None:
    anonymous = authority(
        local_source_ref="anonymous:SYNTHETIC-SESSION-0001",
        purpose="anonymous_public_service",
        service_scope="public_counter_ai",
        target_system="community_system",
        identity_state="anonymous",
        subject_types=["visitor"],
        role_refs=[],
        qualification_states={},
        consent_state="not_requested",
        authorization_scopes=[],
        qualification_source_refs=[],
        consent_record_ref=None,
    )
    packet = gateway.issue_member_sovereign_packet(anonymous)
    allowed = gateway.evaluate_member_authorization(
        packet,
        {
            "purpose": "anonymous_public_service",
            "target_system": "community_system",
            "requested_scopes": [],
        },
        "2026-07-15T18:02:00Z",
    )
    denied = gateway.evaluate_member_authorization(
        packet,
        {
            "purpose": "anonymous_public_service",
            "target_system": "community_system",
            "requested_scopes": ["membership_status_reference"],
        },
        "2026-07-15T18:02:00Z",
    )
    assert allowed["decision"] == "allow"
    assert denied["decision"] == "deny"
    assert denied["reason"] == "anonymous_privilege_forbidden"


def test_scope_mismatch_and_missing_current_state_do_not_authorize() -> None:
    packet = gateway.issue_member_sovereign_packet(authority())
    mismatch = gateway.evaluate_member_authorization(
        packet,
        request_state(requested_scopes=["merchant_role_reference"]),
        "2026-07-15T18:02:00Z",
    )
    missing_state = request_state()
    missing_state.pop("current_authority_state")
    held = gateway.evaluate_member_authorization(
        packet, missing_state, "2026-07-15T18:02:00Z"
    )
    assert mismatch["decision"] == "deny"
    assert mismatch["reason"] == "scope_mismatch"
    assert held["decision"] == "hold"
    assert held["reason"] == "current_authority_state_check_required"


def test_withdrawal_immediately_denies_a_new_request() -> None:
    packet = gateway.issue_member_sovereign_packet(authority())
    withdrawn = request_state()
    withdrawn["current_authority_state"]["consent_state"] = "withdrawn"
    result = gateway.evaluate_member_authorization(
        packet, withdrawn, "2026-07-15T18:02:00Z"
    )
    assert result["decision"] == "deny"
    assert result["reason"] == "consent_withdrawn"


def test_expired_packet_is_denied() -> None:
    packet = gateway.issue_member_sovereign_packet(authority())
    result = gateway.evaluate_member_authorization(
        packet, request_state(), "2026-07-15T18:16:00Z"
    )
    assert result["decision"] == "deny"
    assert result["reason"] == "packet_expired"


def test_packet_tampering_is_detected() -> None:
    packet = gateway.issue_member_sovereign_packet(authority())
    packet["D2_STATE"]["authorization_scopes"].append("merchant_role_reference")
    result = gateway.evaluate_member_authorization(
        packet, request_state(), "2026-07-15T18:02:00Z"
    )
    assert result["decision"] == "deny"
    assert result["reason"] == "packet_tampering_detected"


def test_member_plaintext_shaped_field_is_rejected() -> None:
    unsafe = authority()
    unsafe["full_name"] = "SYNTHETIC PERSON"
    try:
        gateway.issue_member_sovereign_packet(unsafe)
    except ValueError as exc:
        assert "member_plaintext_forbidden" in str(exc)
    else:
        raise AssertionError("plaintext-shaped field was accepted")


def test_three_data_exports_have_distinct_governance() -> None:
    subject_ref = "subject:sha256:" + ("a" * 64)
    assert gateway.classify_data_export(
        {
            "request_type": "MEMBER_ACCESS_REQUEST",
            "requester_subject_ref": subject_ref,
            "subject_ref": subject_ref,
        }
    ) == ("allow", "member_controlled_access")
    assert gateway.classify_data_export(
        {"request_type": "AUTHORITY_REQUEST", "legal_case_ref": "case:SYNTHETIC"}
    )[0] == "require_human_review"
    assert gateway.classify_data_export(
        {
            "request_type": "DEIDENTIFIED_RESEARCH",
            "deidentified": True,
            "research_permission_ref": "research:SYNTHETIC",
        }
    ) == ("allow", "deidentified_research_only")


def test_governance_hash_chain_detects_event_modification() -> None:
    genesis = "sha256:" + ("0" * 64)
    first = gateway.governance_event(
        "subject:synthetic",
        "consent_grant",
        "explicit_test_consent",
        "membership_status_reference",
        "consent:SYNTHETIC-0001",
        genesis,
        "2026-07-15T18:00:00Z",
        "PASS",
    )
    second = gateway.governance_event(
        "subject:synthetic",
        "authorization_decision",
        "minimum_disclosure_authorized",
        "membership_status_reference",
        "authorization:SYNTHETIC-0001",
        first["resulting_state_hash"],
        "2026-07-15T18:01:00Z",
        "PASS",
    )
    assert gateway.verify_governance_chain([first, second]) == []
    tampered = [first, copy.deepcopy(second)]
    tampered[1]["reason"] = "modified"
    assert "event_tampering_detected:1" in gateway.verify_governance_chain(tampered)
