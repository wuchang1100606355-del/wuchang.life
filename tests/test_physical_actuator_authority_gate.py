from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tools.physical_actuator_authority_gate import (
    JOINT_8D_FIELDS,
    PACKET_SCHEMA,
    PASS_STATE,
    PhysicalActuatorAuthorityGate,
    canonical_sha256,
)
from tools.total_field_authority_runtime_bindings import (
    build_authority_runtime_bindings,
)


NOW = datetime(2026, 9, 23, 8, 0, 0, tzinfo=timezone.utc)


class SignatureBackend:
    def verify_detached(
        self,
        *,
        verifier_ref: str,
        payload_sha256: str,
        signature: str,
    ) -> bool:
        return (
            verifier_ref == "verifier_ref:synthetic.9002"
            and signature == f"sig:{payload_sha256}"
        )


class ApplicationIdentityVerifier:
    trusted_application_identity_verifier = True

    def __call__(self, **values) -> bool:
        return (
            values["application_identity_ref"]
            == "application_ref:synthetic.cafe.gateway"
            and values["application_identity_proof"]
            == "proof:synthetic:application"
        )


class AuthorityReferenceVerifier:
    trusted_authority_reference_verifier = True

    def __init__(self, allow: bool = True) -> None:
        self.allow = allow

    def __call__(self, **values) -> bool:
        return (
            self.allow
            and values["authority_ref"]
            == "authority_ref:synthetic.total_field.9002"
            and values["effect_scope"] == "PHYSICAL_ACTUATOR_EFFECT"
        )


class RejectingApplicationIdentityVerifier:
    trusted_application_identity_verifier = True

    def __call__(self, **values) -> bool:
        return False


def _joint_state(authority_ref: str) -> dict:
    state = {field: {"state_ref": f"synthetic:{field.lower()}"} for field in JOINT_8D_FIELDS}
    state["D8_ENVELOPE_AUTHORITY"] = {
        "authority_ref": authority_ref,
        "effect_scope": "PHYSICAL_ACTUATOR_EFFECT",
    }
    return state


def _packet(parameters: dict, *, nonce_digit: str = "a") -> dict:
    authority_ref = "authority_ref:synthetic.total_field.9002"
    joint_state = _joint_state(authority_ref)
    signed = {
        "schema_id": PACKET_SCHEMA,
        "request_id": "request:synthetic:9002:1",
        "application_identity_ref": "application_ref:synthetic.cafe.gateway",
        "application_identity_proof": "proof:synthetic:application",
        "issued_at": (NOW - timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
        "expires_at": (NOW + timedelta(seconds=29)).isoformat().replace("+00:00", "Z"),
        "ttl_seconds": 30,
        "nonce": "nonce_ref:sha256:" + nonce_digit * 64,
        "actuator_id": "9002:lobster_code_writer",
        "action": "lobster_code_writer",
        "parameters_sha256": canonical_sha256(parameters),
        "joint_8d_state": joint_state,
        "joint_8d_state_sha256": canonical_sha256(joint_state),
        "authority_ref": authority_ref,
        "verifier_ref": "verifier_ref:synthetic.9002",
    }
    request_sha256 = canonical_sha256(signed)
    return {
        **signed,
        "request_sha256": request_sha256,
        "signature": f"sig:{request_sha256}",
    }


@pytest.fixture
def gate(tmp_path):
    bindings = build_authority_runtime_bindings(
        ledger_path=tmp_path / "nonce.sqlite3",
        signature_backend=SignatureBackend(),
        trusted_verifier_refs=["verifier_ref:synthetic.9002"],
    )
    authority_gate = PhysicalActuatorAuthorityGate(
        nonce_ledger=bindings.nonce_ledger,
        signature_verifier=bindings.signature_verifier,
        application_identity_verifier=ApplicationIdentityVerifier(),
        authority_reference_verifier=AuthorityReferenceVerifier(),
    )
    yield authority_gate
    bindings.close()


def _validate(gate, packet, parameters):
    return gate.validate_and_consume(
        packet,
        actuator_id="9002:lobster_code_writer",
        action="lobster_code_writer",
        parameters=parameters,
        now=NOW,
    )


def test_exact_request_passes_once_and_replay_fails_closed(gate) -> None:
    parameters = {"file_path": "synthetic.txt", "code_content": "candidate"}
    packet = _packet(parameters)

    first = _validate(gate, packet, parameters)
    replay = _validate(gate, packet, parameters)

    assert first["state"] == PASS_STATE
    assert first["actuator_authorized"] is True
    assert first["application_identity_verified"] is True
    assert first["request_integrity_verified"] is True
    assert first["freshness_verified"] is True
    assert first["anti_replay_consumed"] is True
    assert first["joint_8d_state_verified"] is True
    assert first["authority_reference_verified"] is True
    assert first["final_authority"] is False
    assert first["total_field_decision"] == "NOT_RUN"
    assert replay["state"] == "BLOCK_9002_REQUEST_REPLAY"
    assert replay["actuator_authorized"] is False


def test_parameter_tampering_is_blocked_before_nonce_consumption(gate) -> None:
    original = {"file_path": "synthetic.txt", "code_content": "candidate"}
    packet = _packet(original, nonce_digit="b")
    tampered = {**original, "file_path": "different.txt"}

    result = _validate(gate, packet, tampered)
    assert result["state"] == "BLOCK_9002_REQUEST_PARAMETERS_MISMATCH"
    assert gate.nonce_ledger.entry_count() == 0


def test_stale_request_is_blocked(gate) -> None:
    parameters = {"file_path": "synthetic.txt", "code_content": "candidate"}
    packet = _packet(parameters, nonce_digit="c")
    result = gate.validate_and_consume(
        packet,
        actuator_id="9002:lobster_code_writer",
        action="lobster_code_writer",
        parameters=parameters,
        now=NOW + timedelta(seconds=30),
    )
    assert result["state"] == "BLOCK_9002_FRESHNESS_EXPIRED"
    assert gate.nonce_ledger.entry_count() == 0


@pytest.mark.parametrize("missing_dimension", JOINT_8D_FIELDS)
def test_joint_8d_representation_requires_all_fixed_dimensions(
    gate,
    missing_dimension: str,
) -> None:
    parameters = {"file_path": "synthetic.txt", "code_content": "candidate"}
    packet = _packet(parameters, nonce_digit="d")
    packet["joint_8d_state"].pop(missing_dimension)
    result = _validate(gate, packet, parameters)
    assert result["state"] in {
        "BLOCK_9002_REQUEST_INTEGRITY",
        "BLOCK_9002_JOINT_8D_STATE_INVALID",
    }
    assert result["actuator_authorized"] is False


def test_d1_to_d8_presence_does_not_grant_authority(tmp_path) -> None:
    parameters = {"file_path": "synthetic.txt", "code_content": "candidate"}
    packet = _packet(parameters, nonce_digit="e")
    bindings = build_authority_runtime_bindings(
        ledger_path=tmp_path / "nonce.sqlite3",
        signature_backend=SignatureBackend(),
        trusted_verifier_refs=["verifier_ref:synthetic.9002"],
    )
    gate = PhysicalActuatorAuthorityGate(
        nonce_ledger=bindings.nonce_ledger,
        signature_verifier=bindings.signature_verifier,
        application_identity_verifier=ApplicationIdentityVerifier(),
        authority_reference_verifier=AuthorityReferenceVerifier(allow=False),
    )
    try:
        result = _validate(gate, packet, parameters)
    finally:
        bindings.close()
    assert result["state"] == "BLOCK_9002_AUTHORITY_REFERENCE_UNVERIFIED"
    assert result["actuator_authorized"] is False


def test_application_identity_must_be_verified_by_trusted_binding(tmp_path) -> None:
    parameters = {"file_path": "synthetic.txt", "code_content": "candidate"}
    packet = _packet(parameters, nonce_digit="f")
    bindings = build_authority_runtime_bindings(
        ledger_path=tmp_path / "nonce.sqlite3",
        signature_backend=SignatureBackend(),
        trusted_verifier_refs=["verifier_ref:synthetic.9002"],
    )
    gate = PhysicalActuatorAuthorityGate(
        nonce_ledger=bindings.nonce_ledger,
        signature_verifier=bindings.signature_verifier,
        application_identity_verifier=RejectingApplicationIdentityVerifier(),
        authority_reference_verifier=AuthorityReferenceVerifier(),
    )
    try:
        result = _validate(gate, packet, parameters)
    finally:
        bindings.close()
    assert result["state"] == "BLOCK_9002_APPLICATION_IDENTITY"
    assert result["actuator_authorized"] is False


def test_untrusted_true_callbacks_do_not_grant_authority(tmp_path) -> None:
    parameters = {"file_path": "synthetic.txt", "code_content": "candidate"}
    packet = _packet(parameters, nonce_digit="1")
    bindings = build_authority_runtime_bindings(
        ledger_path=tmp_path / "nonce.sqlite3",
        signature_backend=SignatureBackend(),
        trusted_verifier_refs=["verifier_ref:synthetic.9002"],
    )
    gate = PhysicalActuatorAuthorityGate(
        nonce_ledger=bindings.nonce_ledger,
        signature_verifier=bindings.signature_verifier,
        application_identity_verifier=lambda **values: True,
        authority_reference_verifier=lambda **values: True,
    )
    try:
        result = _validate(gate, packet, parameters)
    finally:
        bindings.close()
    assert result["state"] == "BLOCK_9002_APPLICATION_IDENTITY_BINDING_REQUIRED"
    assert result["actuator_authorized"] is False


def test_gateway_candidate_is_not_runtime_bound() -> None:
    source = Path("legacy_core/taiji_unified_gateway_edge.py").read_text(encoding="utf-8")
    assert "wuchang_gateway = WuchangUniversalGateway()" in source
    assert "BLOCK_9002_PHYSICAL_ACTUATOR_GATE_NOT_BOUND" in source
    assert source.index("scan_operation(", source.index("async def _execute_tool")) < source.index(
        "gate.validate_and_consume(", source.index("async def _execute_tool")
    )
    assert source.index("gate.validate_and_consume(") < source.index(
        "self.open_claw.lobster_code_writer"
    )
