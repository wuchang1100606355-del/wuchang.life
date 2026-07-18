from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


google = load(
    ROOT
    / "Taiji_Odoo/addons/wuchang_google_member_login/services/account_linking.py",
    "focused_google_account_linking",
)
line = load(
    ROOT / "Taiji_Odoo/addons/wuchang_line_login/services/profile_minimization.py",
    "focused_line_profile_minimization",
)
gateway = load(
    ROOT
    / "deploy/packages/taiji01_metric_identity_gateway_v0_1/taiji01_metric_identity_gateway.py",
    "focused_member_sovereign_gateway",
)


def authority(**overrides):
    value = {
        "local_source_ref": "odoo:wuchang.member.identity.code:SYNTHETIC-REMEDIATION",
        "issuer": "taiji01:odoo-member-authority",
        "purpose": "association_member_service",
        "service_scope": "association",
        "target_system": "association_system",
        "identity_state": "registered",
        "subject_types": ["association_member"],
        "role_refs": ["role:association_member"],
        "qualification_states": {"association_member": True},
        "consent_state": "granted",
        "authorization_scopes": ["membership_status_reference"],
        "qualification_source_refs": ["qualification:SYNTHETIC"],
        "consent_record_ref": "consent:SYNTHETIC-REMEDIATION",
        "local_state_check_ref": "taiji01:member-authority-state-check:v1",
        "verified_at": "2026-07-15T19:00:00Z",
        "issued_at": "2026-07-15T19:00:00Z",
        "expires_at": "2026-07-15T19:15:00Z",
        "nonce": "synthetic-remediation-nonce",
    }
    value.update(overrides)
    return value


def request_state(**overrides):
    value = {
        "purpose": "association_member_service",
        "target_system": "association_system",
        "requested_scopes": ["membership_status_reference"],
        "provider_link_state": "PROVIDER_LINK_FOUND",
        "current_authority_state": {
            "identity_state": "registered",
            "consent_state": "granted",
            "consent_record_ref": "consent:SYNTHETIC-REMEDIATION",
        },
    }
    value.update(overrides)
    return value


def test_google_same_email_without_provider_link_stays_pending() -> None:
    state = google.google_link_state(provider_link_found=False)
    context = google.transient_link_context(
        {
            "sub": "SYNTHETIC-GOOGLE-SUBJECT",
            "email": "same-address@example.test",
        },
        {"link_state": state, "verifier_result": "HOLD"},
    )
    source = (
        ROOT / "Taiji_Odoo/addons/wuchang_google_member_login/models/res_partner.py"
    ).read_text(encoding="utf-8")
    assert state == "LINKING_PENDING"
    assert context["email_candidate_signal"].startswith("candidate:email:sha256:")
    assert "email" not in context
    assert 'self.search([("email", "=", email)]' not in source
    assert "self.create(values)" not in source
    assert "partner.write(values)" not in source


def test_google_existing_link_and_confirmation_states() -> None:
    assert google.google_link_state(provider_link_found=True) == "PROVIDER_LINK_FOUND"
    assert google.google_link_state(
        provider_link_found=False, linking_started=True
    ) == "REAUTHENTICATION_REQUIRED"
    assert google.google_link_state(
        provider_link_found=False, linking_started=True, reauthenticated=True
    ) == "EXPLICIT_LINK_CONSENT_REQUIRED"
    assert google.google_link_state(
        provider_link_found=False,
        linking_started=True,
        reauthenticated=True,
        explicit_link_consent=True,
        human_review_required=True,
    ) == "HUMAN_REVIEW_REQUIRED"
    assert google.google_link_state(
        provider_link_found=False,
        linking_started=True,
        reauthenticated=True,
        explicit_link_consent=True,
    ) == "LINK_CONFIRMED"


def test_google_callback_state_nonce_host_and_subject_are_strict() -> None:
    valid = {
        "expected_state": "state-1",
        "received_state": "state-1",
        "expected_nonce": "nonce-1",
        "token_claims": {"nonce": "nonce-1", "aud": "client-1", "sub": "subject-1"},
        "expected_audience": "client-1",
        "userinfo_subject": "subject-1",
        "callback_url": google.CANONICAL_CALLBACK_URL,
    }
    assert google.callback_security_decision(**valid)["decision"] == "PASS"
    for key, value in (
        ("received_state", "wrong"),
        ("expected_nonce", "wrong"),
        ("callback_url", "https://example.test/google/member/callback"),
        ("userinfo_subject", "wrong"),
    ):
        candidate = dict(valid)
        candidate[key] = value
        assert google.callback_security_decision(**candidate)["decision"] == "DENY"


def test_google_callback_has_no_direct_role_grant() -> None:
    source = (
        ROOT / "Taiji_Odoo/addons/wuchang_google_member_login/controllers/main.py"
    ).read_text(encoding="utf-8")
    assert "resolve_provider_subject" in source
    assert 'link_context["link_state"]' in source
    assert "status=202" in source
    assert "groups_id" not in source
    assert "has_group" not in source
    assert "wuchang_google_member_partner_id" not in source


def test_line_profile_is_minimized_to_exact_allowlist_and_hash() -> None:
    profile = {
        "userId": "SYNTHETIC-LINE-SUBJECT",
        "displayName": "Synthetic nickname",
        "pictureUrl": "https://example.test/synthetic.png",
        "statusMessage": "Synthetic status",
    }
    resolution = {
        "local_subject_reference": "subject:sha256:" + ("a" * 64),
        "link_state": "PROVIDER_LINK_FOUND",
        "consent_reference": "consent:SYNTHETIC",
        "verifier_result": "PASS",
    }
    record = line.minimized_link_record(profile, resolution, "2026-07-15T19:01:00Z")
    assert set(record) == line.ALLOWED_LINK_FIELDS
    assert record["provider_payload_hash"] == line.canonical_payload_hash(profile)
    serialized = str(record)
    assert "Synthetic nickname" not in serialized
    assert "synthetic.png" not in serialized
    assert "Synthetic status" not in serialized
    assert "access_token" not in serialized
    assert "refresh_token" not in serialized
    assert "id_token" not in serialized


def test_line_controller_does_not_persist_raw_profile() -> None:
    controller = (
        ROOT / "Taiji_Odoo/addons/wuchang_line_login/controllers/main.py"
    ).read_text(encoding="utf-8")
    model = (
        ROOT / "Taiji_Odoo/addons/wuchang_line_login/models/line_user.py"
    ).read_text(encoding="utf-8")
    assert "request.env['wuchang.line.user']" not in controller
    assert "raw_profile" not in controller
    assert "picture_url" not in controller
    assert "display_name" not in controller
    assert "PERSISTENCE_DISABLED_MESSAGE" in model
    assert "raise UserError(PERSISTENCE_DISABLED_MESSAGE)" in model


def test_line_revoked_or_pending_link_cannot_authorize() -> None:
    for state in (
        "LINK_DENIED",
        "LINKING_PENDING",
        "REAUTHENTICATION_REQUIRED",
        "HUMAN_REVIEW_REQUIRED",
    ):
        assert line.authorization_decision(state) == "DENY"


def test_gateway_denies_provider_link_holds() -> None:
    packet = gateway.issue_member_sovereign_packet(authority())
    for state in (
        "LINKING_PENDING",
        "REAUTHENTICATION_REQUIRED",
        "HUMAN_REVIEW_REQUIRED",
    ):
        result = gateway.evaluate_member_authorization(
            packet,
            request_state(provider_link_state=state),
            "2026-07-15T19:02:00Z",
        )
        assert result["decision"] == "deny"


def test_gateway_preserves_withdrawal_expiry_scope_and_tamper_denials() -> None:
    packet = gateway.issue_member_sovereign_packet(authority())
    withdrawn = request_state()
    withdrawn["current_authority_state"] = dict(withdrawn["current_authority_state"])
    withdrawn["current_authority_state"]["consent_state"] = "withdrawn"
    assert gateway.evaluate_member_authorization(
        packet, withdrawn, "2026-07-15T19:02:00Z"
    )["decision"] == "deny"
    assert gateway.evaluate_member_authorization(
        packet, request_state(), "2026-07-15T19:16:00Z"
    )["reason"] == "packet_expired"
    assert gateway.evaluate_member_authorization(
        packet,
        request_state(requested_scopes=["merchant_role_reference"]),
        "2026-07-15T19:02:00Z",
    )["reason"] == "scope_mismatch"
    tampered = copy.deepcopy(packet)
    tampered["D2_STATE"]["identity_state"] = "revoked"
    assert gateway.evaluate_member_authorization(
        tampered, request_state(), "2026-07-15T19:02:00Z"
    )["reason"] == "packet_tampering_detected"


def test_public_member_api_response_uses_only_allowlisted_fields() -> None:
    packet = gateway.issue_member_sovereign_packet(authority())
    internal = gateway.evaluate_member_authorization(
        packet, request_state(), "2026-07-15T19:02:00Z"
    )
    response = gateway.member_api_public_response(
        internal, packet, "PROVIDER_LINK_FOUND"
    )
    assert set(response) == {
        "subject_reference",
        "provider_link_state",
        "identity_state",
        "necessary_role",
        "qualification_status",
        "granted_scope",
        "decision",
        "issued_at",
        "expires_at",
        "verifier_result",
    }
    assert response["decision"] == "ALLOW"
    denied = gateway.member_api_public_response(
        internal, packet, "HUMAN_REVIEW_REQUIRED"
    )
    assert denied["decision"] == "DENY"
