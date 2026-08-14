from __future__ import annotations

import ast
import copy
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from tools import total_field_genesis_authority_bootstrap_candidate as genesis
from tools.total_field.w7tp_intent_field_suite import (
    founder_identity_evidence_provider as founder_provider,
)


NOW = datetime(2026, 8, 14, 5, 0, 0, tzinfo=timezone.utc)
VERIFIER_REF = "verifier_ref:trusted-runtime-v1"
REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = (
    REPO_ROOT
    / "schemas/field/w7tp_total_field_genesis_authority_bootstrap_candidate_v1.schema.json"
)
MANIFEST_PATH = (
    REPO_ROOT
    / "manifests/total_field/w7tp_total_field_genesis_authority_bootstrap_candidate_v1/SHA256_MANIFEST.json"
)


def _ref(kind: str, label: str) -> str:
    digest = hashlib.sha256(label.encode("utf-8")).hexdigest()
    return f"{kind}:sha256:{digest}"


class _Provider:
    def __init__(self, result: dict[str, Any]) -> None:
        self.result = result
        self.call_count = 0

    def collect_and_verify(self) -> dict[str, Any]:
        self.call_count += 1
        return copy.deepcopy(self.result)


class _Verifier:
    trusted_runtime_verifier = True

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str, str, str, str]] = []

    def verify(
        self,
        *,
        verifier_ref: str,
        expected_signer_identity_root_ref: str,
        expected_role_seat_ref: str,
        verification_method_ref: str,
        payload_sha256: str,
        signature: str,
    ) -> bool:
        self.calls.append(
            (
                verifier_ref,
                expected_signer_identity_root_ref,
                expected_role_seat_ref,
                verification_method_ref,
                payload_sha256,
                signature,
            )
        )
        return signature == f"external-signature:{payload_sha256}"


class _Ledger:
    persistent = True
    global_nonce_uniqueness = True

    def __init__(self) -> None:
        self.seen: set[str] = set()
        self.bindings: dict[str, str] = {}
        self.call_count = 0

    def mark_used_or_replay(
        self,
        nonce: str,
        packet_hash: str,
        now_epoch: float,
        ttl_seconds: int,
    ) -> bool:
        del now_epoch
        assert 0 < ttl_seconds <= genesis.MAX_TTL_SECONDS
        self.call_count += 1
        if nonce in self.seen:
            return False
        self.seen.add(nonce)
        self.bindings[nonce] = packet_hash
        return True


def _provider_result() -> dict[str, Any]:
    return {
        "state": "PASS",
        "reason_code": (
            "PASS_READ_ONLY_FOUNDER_IDENTITY_EVIDENCE_PROVIDER_CANDIDATE"
        ),
        "candidate_only": True,
        "provider_id": founder_provider.PROVIDER_ID,
        "registry_coordinate": founder_provider.REGISTRY_COORDINATE,
        "root_registry_cardinality": 1,
        "founder_role_seat_ref": _ref("founder_role_seat_ref", "seat"),
        "founder_identity_root_ref": _ref(
            "member_identity_root_ref", "root"
        ),
        "founder_identity_binding_receipt_ref": _ref(
            "founder_identity_binding_receipt_ref", "binding-receipt"
        ),
        "8d_adi_binding_evidence_ref": _ref(
            "8d_adi_binding_evidence_ref", "8d-adi"
        ),
        "current_root_registry_cardinality_evidence_ref": _ref(
            "current_root_registry_cardinality_evidence_ref", "cardinality"
        ),
        "p1_verifier_result": {
            "state": "PASS",
            "reason_code": "PASS_P1_CANDIDATE",
        },
        "second_registry_created": False,
        "member_plaintext_read": False,
    }


def _bundle() -> dict[str, Any]:
    provider = _provider_result()
    root_ref = provider["founder_identity_root_ref"]
    seat_ref = provider["founder_role_seat_ref"]
    device_ref = _ref("registered_device_ref", "device")
    bundle = {
        "schema_id": genesis.EVIDENCE_BUNDLE_SCHEMA_ID,
        "registry_coordinates": [founder_provider.REGISTRY_COORDINATE],
        "founders": [
            {
                "founder_person_packet_ref": _ref(
                    "person_packet_ref", "founder"
                ),
                "identity_root_ref": root_ref,
                "role_seat_ref": seat_ref,
                "registered_device_ref": device_ref,
            }
        ],
        "identity_roots": [{"identity_root_ref": root_ref}],
        "role_seats": [
            {
                "role_code": "FOUNDER",
                "role_seat_ref": seat_ref,
                "identity_root_ref": root_ref,
            }
        ],
        "registered_devices": [
            {
                "registered_device_ref": device_ref,
                "identity_root_ref": root_ref,
            }
        ],
        "founder_capability_assignment_ref": _ref(
            "capability_assignment_ref", "founder-capability"
        ),
        "access_profile_ref": _ref("access_profile_ref", "founder-profile"),
    }
    bundle["evidence_sha256"] = genesis.evidence_bundle_sha256(bundle)
    return bundle


def _rehash(bundle: dict[str, Any]) -> None:
    bundle["evidence_sha256"] = genesis.evidence_bundle_sha256(bundle)


def _rehash_proposal(proposal: dict[str, Any]) -> None:
    unsigned = copy.deepcopy(proposal)
    unsigned.pop("proposal_sha256", None)
    proposal["proposal_sha256"] = genesis.canonical_sha256(unsigned)


def _request(
    *,
    verifier_ref: str = VERIFIER_REF,
    issued_at: datetime = NOW - timedelta(seconds=5),
    expires_at: datetime = NOW + timedelta(seconds=250),
) -> dict[str, Any]:
    return {
        "issued_at": issued_at.isoformat().replace("+00:00", "Z"),
        "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        "nonce": _ref("nonce_ref", "single-use-genesis"),
        "verifier_ref": verifier_ref,
        "authority_scope": list(genesis.AUTHORITY_SCOPE),
    }


def _proposal(
    repo_root: Path,
    *,
    bundle: dict[str, Any] | None = None,
    request: dict[str, Any] | None = None,
    provider_result: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], _Provider]:
    provider = _Provider(provider_result or _provider_result())
    proposal = genesis.build_genesis_proposal(
        repo_root=repo_root,
        founder_evidence_provider=provider,
        evidence_bundle=bundle or _bundle(),
        authority_request=request or _request(),
        now=NOW,
    )
    return proposal, provider


def _signed_artifact(
    schema_id: str,
    proposal: dict[str, Any],
    **extra: Any,
) -> dict[str, Any]:
    artifact = {
        "schema_id": schema_id,
        "authority_id": proposal["authority_id"],
        "issued_at": (NOW - timedelta(seconds=2)).isoformat().replace(
            "+00:00", "Z"
        ),
        "expires_at": (NOW + timedelta(seconds=200)).isoformat().replace(
            "+00:00", "Z"
        ),
        "verifier_ref": VERIFIER_REF,
        "signer_identity_root_ref": proposal["founder_identity_root_ref"],
        "signer_role_seat_ref": proposal["founder_role_seat_ref"],
        "verification_method_ref": proposal["registered_device_ref"],
        **extra,
    }
    artifact["payload_sha256"] = genesis.canonical_sha256(artifact)
    artifact["signature"] = (
        f"external-signature:{artifact['payload_sha256']}"
    )
    return artifact


def _resign_artifact(artifact: dict[str, Any]) -> None:
    unsigned = copy.deepcopy(artifact)
    unsigned.pop("signature", None)
    unsigned.pop("payload_sha256", None)
    artifact["payload_sha256"] = genesis.canonical_sha256(unsigned)
    artifact["signature"] = (
        f"external-signature:{artifact['payload_sha256']}"
    )


def _seal_inputs(proposal: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    founder_signature = {
        "schema_id": genesis.FOUNDER_SIGNATURE_SCHEMA_ID,
        "authority_id": proposal["authority_id"],
        "signed_payload_sha256": proposal["proposal_sha256"],
        "verifier_ref": VERIFIER_REF,
        "signer_identity_root_ref": proposal["founder_identity_root_ref"],
        "signer_role_seat_ref": proposal["founder_role_seat_ref"],
        "verification_method_ref": proposal["registered_device_ref"],
        "signature": f"external-signature:{proposal['proposal_sha256']}",
    }
    owner_seal = _signed_artifact(
        genesis.OWNER_SEAL_SCHEMA_ID,
        proposal,
        authorization="FOUNDER_APPROVED_GENESIS_AUTHORITY_CANDIDATE",
        single_use_id=proposal["nonce"],
    )
    revocation = _signed_artifact(
        genesis.REVOCATION_SCHEMA_ID,
        proposal,
        revoked_authority_ids=[],
        revoked_signature_sha256s=[],
    )
    return founder_signature, owner_seal, revocation


def _seal(
    repo_root: Path,
    proposal: dict[str, Any],
    *,
    verifier: _Verifier | None = None,
    ledger: _Ledger | None = None,
    trusted_verifier_refs: set[str] | None = None,
    founder_signature: dict[str, Any] | None = None,
    owner_seal: dict[str, Any] | None = None,
    revocation: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], _Verifier, _Ledger]:
    defaults = _seal_inputs(proposal)
    selected_verifier = verifier or _Verifier()
    selected_ledger = ledger or _Ledger()
    result = genesis.seal_genesis_candidate(
        repo_root=repo_root,
        proposal=proposal,
        founder_signature=founder_signature or defaults[0],
        owner_seal=owner_seal or defaults[1],
        revocation_record=revocation or defaults[2],
        signature_verifier=selected_verifier,
        trusted_verifier_refs=(
            trusted_verifier_refs
            if trusted_verifier_refs is not None
            else {VERIFIER_REF}
        ),
        nonce_ledger=selected_ledger,
        now=NOW,
    )
    return result, selected_verifier, selected_ledger


def _schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _validate_schema(document: dict[str, Any]) -> None:
    schema = _schema()
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(document), key=lambda item: list(item.path))
    assert errors == []


def test_valid_evidence_builds_a_and_b_without_active_authority_or_receiver(
    tmp_path: Path,
) -> None:
    proposal, provider = _proposal(tmp_path)
    assert proposal["stage"] == "A_GENESIS_PROPOSAL"
    assert proposal["state"] == "GENESIS_PROPOSAL_CANDIDATE"
    assert proposal["existing_d8_pass_required"] is False
    assert proposal["total_field_decision"] == "NOT_RUN"
    assert proposal["receiver_call_count"] == 0
    assert provider.call_count == 1
    _validate_schema(proposal)

    sealed, verifier, ledger = _seal(tmp_path, proposal)
    assert sealed["stage"] == "B_SEALED_GENESIS_CANDIDATE"
    assert sealed["state"] == "SEALED_GENESIS_AUTHORITY_CANDIDATE"
    assert sealed["activation_called"] is False
    assert sealed["active_authority_created"] is False
    assert sealed["receiver_call_count"] == 0
    assert sealed["activation_capability"] == {
        "capability_id": "W7TP_TOTAL_FIELD_GENESIS_ATOMIC_ACTIVATION_V1",
        "target": genesis.ACTIVE_AUTHORITY_REL.as_posix(),
        "single_use": True,
        "atomic_create_if_absent": True,
        "persistent_nonce_required": True,
        "permanent_self_stop_after_success": True,
        "call_forbidden_in_candidate_build": True,
        "implementation": "INJECTED_SINGLE_USE_ATOMIC_AUTHORITY_STORE",
    }
    assert len(verifier.calls) == 3
    assert all(
        call[1:4]
        == (
            proposal["founder_identity_root_ref"],
            proposal["founder_role_seat_ref"],
            proposal["registered_device_ref"],
        )
        for call in verifier.calls
    )
    assert ledger.call_count == 1
    assert not (tmp_path / genesis.ACTIVE_AUTHORITY_REL).exists()
    _validate_schema(sealed)


@pytest.mark.parametrize(
    ("field", "reason_code"),
    [
        ("founders", "HOLD_FOUNDER_CARDINALITY"),
        ("identity_roots", "HOLD_IDENTITY_ROOT_CARDINALITY"),
        ("role_seats", "HOLD_ROLE_SEAT_CARDINALITY"),
        ("registered_devices", "HOLD_REGISTERED_DEVICE_CARDINALITY"),
    ],
)
@pytest.mark.parametrize("cardinality", [0, 2])
def test_zero_or_multiple_identity_coordinates_hold(
    tmp_path: Path,
    field: str,
    reason_code: str,
    cardinality: int,
) -> None:
    bundle = _bundle()
    original = copy.deepcopy(bundle[field][0])
    bundle[field] = [] if cardinality == 0 else [original, copy.deepcopy(original)]
    _rehash(bundle)
    result, _ = _proposal(tmp_path, bundle=bundle)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == reason_code
    assert result["receiver_call_count"] == 0


def test_second_registry_coordinate_holds(tmp_path: Path) -> None:
    bundle = _bundle()
    bundle["registry_coordinates"].append("odoo18://second-registry")
    _rehash(bundle)
    result, _ = _proposal(tmp_path, bundle=bundle)
    assert result["reason_code"] == "HOLD_SECOND_REGISTRY_COORDINATE"


def test_evidence_and_proposal_hash_mismatch_fail_closed(tmp_path: Path) -> None:
    bundle = _bundle()
    bundle["founders"][0]["identity_root_ref"] = _ref(
        "member_identity_root_ref", "tampered"
    )
    result, _ = _proposal(tmp_path, bundle=bundle)
    assert result["reason_code"] == "HOLD_EVIDENCE_HASH_MISMATCH"

    proposal, _ = _proposal(tmp_path)
    proposal["authority_version"] = 2
    sealed, _, _ = _seal(tmp_path, proposal)
    assert sealed["reason_code"] == "BLOCK_PROPOSAL_HASH_MISMATCH"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("second_authority_created", True),
        ("second_receiver_created", True),
        ("database_written", True),
        ("deployment_performed", True),
        ("service_restarted", True),
        ("private_key_read", True),
        ("member_plaintext_included", True),
        ("receiver_call_count", False),
        ("authority_record_path", "runtime/total_field/OTHER.json"),
        ("authority_version", True),
        ("authority_version", 2),
        ("registry_coordinate", "odoo18://second-registry"),
    ],
)
def test_rehashed_semantic_proposal_tampering_blocks_before_signatures(
    tmp_path: Path,
    field: str,
    value: Any,
) -> None:
    proposal, _ = _proposal(tmp_path)
    proposal[field] = value
    _rehash_proposal(proposal)
    result, verifier, ledger = _seal(tmp_path, proposal)
    assert result["state"] == "BLOCK"
    assert result["reason_code"] == "BLOCK_PROPOSAL_BOUNDARY_INVALID"
    assert verifier.calls == []
    assert ledger.call_count == 0


def test_founder_signature_is_bound_to_root_seat_and_device(
    tmp_path: Path,
) -> None:
    proposal, _ = _proposal(tmp_path)
    founder_signature, owner_seal, revocation = _seal_inputs(proposal)
    founder_signature["signer_identity_root_ref"] = _ref(
        "member_identity_root_ref", "different-root"
    )
    result, verifier, ledger = _seal(
        tmp_path,
        proposal,
        founder_signature=founder_signature,
        owner_seal=owner_seal,
        revocation=revocation,
    )
    assert result["reason_code"] == "BLOCK_FOUNDER_SIGNATURE_INVALID"
    assert verifier.calls == []
    assert ledger.call_count == 0


def test_validly_signed_owner_seal_with_wrong_identity_is_blocked(
    tmp_path: Path,
) -> None:
    proposal, _ = _proposal(tmp_path)
    founder_signature, owner_seal, revocation = _seal_inputs(proposal)
    owner_seal["signer_identity_root_ref"] = _ref(
        "member_identity_root_ref", "different-owner"
    )
    _resign_artifact(owner_seal)
    result, verifier, ledger = _seal(
        tmp_path,
        proposal,
        founder_signature=founder_signature,
        owner_seal=owner_seal,
        revocation=revocation,
    )
    assert result["reason_code"] == "BLOCK_OWNER_SEAL_INVALID"
    assert len(verifier.calls) == 1
    assert ledger.call_count == 0


def test_expired_request_holds_without_side_effects(tmp_path: Path) -> None:
    request = _request(
        issued_at=NOW - timedelta(minutes=2),
        expires_at=NOW - timedelta(seconds=1),
    )
    result, provider = _proposal(tmp_path, request=request)
    assert result["reason_code"] == "HOLD_AUTHORITY_EXPIRED"
    assert provider.call_count == 1


def test_offset_timestamp_and_fractional_ttl_over_limit_hold(
    tmp_path: Path,
) -> None:
    offset_request = _request()
    offset_request["issued_at"] = (NOW - timedelta(seconds=5)).isoformat()
    offset_request["expires_at"] = (NOW + timedelta(seconds=250)).isoformat()
    result, _ = _proposal(tmp_path, request=offset_request)
    assert result["reason_code"] == "HOLD_AUTHORITY_TIME_INVALID"

    fractional_request = _request(
        issued_at=NOW - timedelta(seconds=0.4),
        expires_at=NOW + timedelta(seconds=299.7),
    )
    result, _ = _proposal(tmp_path, request=fractional_request)
    assert result["reason_code"] == "HOLD_AUTHORITY_EXPIRED"


def test_boolean_provider_cardinality_does_not_count_as_one(
    tmp_path: Path,
) -> None:
    provider_result = _provider_result()
    provider_result["root_registry_cardinality"] = True
    result, _ = _proposal(tmp_path, provider_result=provider_result)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_FOUNDER_PROVIDER_NOT_VERIFIED"


def test_revoked_authority_blocks(tmp_path: Path) -> None:
    proposal, _ = _proposal(tmp_path)
    founder_signature, owner_seal, revocation = _seal_inputs(proposal)
    revocation = _signed_artifact(
        genesis.REVOCATION_SCHEMA_ID,
        proposal,
        revoked_authority_ids=[proposal["authority_id"]],
        revoked_signature_sha256s=[],
    )
    result, _, ledger = _seal(
        tmp_path,
        proposal,
        founder_signature=founder_signature,
        owner_seal=owner_seal,
        revocation=revocation,
    )
    assert result["reason_code"] == "BLOCK_GENESIS_AUTHORITY_REVOKED"
    assert ledger.call_count == 0


def test_revoked_owner_seal_blocks(tmp_path: Path) -> None:
    proposal, _ = _proposal(tmp_path)
    founder_signature, owner_seal, _ = _seal_inputs(proposal)
    revocation = _signed_artifact(
        genesis.REVOCATION_SCHEMA_ID,
        proposal,
        revoked_authority_ids=[],
        revoked_signature_sha256s=[genesis.canonical_sha256(owner_seal)],
    )
    result, _, ledger = _seal(
        tmp_path,
        proposal,
        founder_signature=founder_signature,
        owner_seal=owner_seal,
        revocation=revocation,
    )
    assert result["reason_code"] == "BLOCK_GENESIS_AUTHORITY_REVOKED"
    assert ledger.call_count == 0


def test_replay_is_blocked_by_persistent_nonce(tmp_path: Path) -> None:
    proposal, _ = _proposal(tmp_path)
    ledger = _Ledger()
    first, _, _ = _seal(tmp_path, proposal, ledger=ledger)
    second, _, _ = _seal(tmp_path, proposal, ledger=ledger)
    assert first["stage"] == "B_SEALED_GENESIS_CANDIDATE"
    assert second["reason_code"] == "BLOCK_GENESIS_NONCE_REPLAY"
    assert ledger.call_count == 2


def test_same_nonce_cannot_be_reused_for_a_different_valid_proposal(
    tmp_path: Path,
) -> None:
    first_proposal, _ = _proposal(tmp_path)
    second_bundle = _bundle()
    second_bundle["founders"][0]["founder_person_packet_ref"] = _ref(
        "person_packet_ref", "different-founder-packet-version"
    )
    _rehash(second_bundle)
    second_proposal, _ = _proposal(tmp_path, bundle=second_bundle)
    assert first_proposal["nonce"] == second_proposal["nonce"]
    assert first_proposal["proposal_sha256"] != second_proposal["proposal_sha256"]

    ledger = _Ledger()
    first, _, _ = _seal(tmp_path, first_proposal, ledger=ledger)
    second, _, _ = _seal(tmp_path, second_proposal, ledger=ledger)
    assert first["state"] == "SEALED_GENESIS_AUTHORITY_CANDIDATE"
    assert second["reason_code"] == "BLOCK_GENESIS_NONCE_REPLAY"
    assert ledger.call_count == 2


def test_unknown_verifier_holds_without_signature_or_nonce_use(tmp_path: Path) -> None:
    unknown = "verifier_ref:unknown-runtime-v1"
    proposal, _ = _proposal(tmp_path, request=_request(verifier_ref=unknown))
    verifier = _Verifier()
    ledger = _Ledger()
    result, _, _ = _seal(
        tmp_path,
        proposal,
        verifier=verifier,
        ledger=ledger,
        trusted_verifier_refs={VERIFIER_REF},
    )
    assert result["reason_code"] == "HOLD_TRUSTED_VERIFIER_UNAVAILABLE"
    assert verifier.calls == []
    assert ledger.call_count == 0


def test_injected_provider_failure_holds(tmp_path: Path) -> None:
    class RaisingProvider:
        def collect_and_verify(self) -> dict[str, Any]:
            raise RuntimeError("provider unavailable")

    result = genesis.build_genesis_proposal(
        repo_root=tmp_path,
        founder_evidence_provider=RaisingProvider(),
        evidence_bundle=_bundle(),
        authority_request=_request(),
        now=NOW,
    )
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_FOUNDER_PROVIDER_CALL_FAILED"
    assert result["receiver_call_count"] == 0


@pytest.mark.parametrize("verifier_result", ["truthy", 1, object()])
def test_non_boolean_verifier_result_fails_closed(
    tmp_path: Path,
    verifier_result: Any,
) -> None:
    class NonBooleanVerifier(_Verifier):
        def verify(self, **kwargs: Any) -> Any:
            super().verify(**kwargs)
            return verifier_result

    proposal, _ = _proposal(tmp_path)
    verifier = NonBooleanVerifier()
    ledger = _Ledger()
    result, _, _ = _seal(
        tmp_path, proposal, verifier=verifier, ledger=ledger
    )
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_TRUSTED_VERIFIER_RESULT_INVALID"
    assert ledger.call_count == 0


def test_verifier_exception_holds_without_nonce_use(tmp_path: Path) -> None:
    class RaisingVerifier(_Verifier):
        def verify(self, **kwargs: Any) -> bool:
            del kwargs
            raise RuntimeError("trusted verifier unavailable")

    proposal, _ = _proposal(tmp_path)
    ledger = _Ledger()
    result, _, _ = _seal(
        tmp_path, proposal, verifier=RaisingVerifier(), ledger=ledger
    )
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_TRUSTED_VERIFIER_CALL_FAILED"
    assert ledger.call_count == 0


@pytest.mark.parametrize("ledger_result", ["truthy", 1, object()])
def test_non_boolean_nonce_result_fails_closed(
    tmp_path: Path,
    ledger_result: Any,
) -> None:
    class NonBooleanLedger(_Ledger):
        def mark_used_or_replay(self, *args: Any, **kwargs: Any) -> Any:
            del args, kwargs
            self.call_count += 1
            return ledger_result

    proposal, _ = _proposal(tmp_path)
    result, _, ledger = _seal(tmp_path, proposal, ledger=NonBooleanLedger())
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_NONCE_LEDGER_RESULT_INVALID"
    assert ledger.call_count == 1


def test_nonce_ledger_exception_holds(tmp_path: Path) -> None:
    class RaisingLedger(_Ledger):
        def mark_used_or_replay(self, *args: Any, **kwargs: Any) -> bool:
            del args, kwargs
            self.call_count += 1
            raise RuntimeError("persistent ledger unavailable")

    proposal, _ = _proposal(tmp_path)
    result, _, ledger = _seal(tmp_path, proposal, ledger=RaisingLedger())
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_NONCE_LEDGER_CALL_FAILED"
    assert ledger.call_count == 1


def test_invalid_founder_signature_and_owner_seal_block(tmp_path: Path) -> None:
    proposal, _ = _proposal(tmp_path)
    founder_signature, owner_seal, revocation = _seal_inputs(proposal)
    founder_signature["signature"] = "invalid"
    result, _, ledger = _seal(
        tmp_path,
        proposal,
        founder_signature=founder_signature,
        owner_seal=owner_seal,
        revocation=revocation,
    )
    assert result["reason_code"] == "BLOCK_FOUNDER_SIGNATURE_INVALID"
    assert ledger.call_count == 0

    founder_signature, owner_seal, revocation = _seal_inputs(proposal)
    owner_seal["authorization"] = "UNBOUND"
    result, _, ledger = _seal(
        tmp_path,
        proposal,
        founder_signature=founder_signature,
        owner_seal=owner_seal,
        revocation=revocation,
    )
    assert result["reason_code"] == "BLOCK_SIGNED_ARTIFACT_HASH_MISMATCH"
    assert ledger.call_count == 0


def test_member_plaintext_key_holds(tmp_path: Path) -> None:
    bundle = _bundle()
    bundle["email"] = "founder@example.invalid"
    _rehash(bundle)
    result, _ = _proposal(tmp_path, bundle=bundle)
    assert result["reason_code"] == "HOLD_MEMBER_PLAINTEXT_BOUNDARY"
    assert result["member_plaintext_included"] is False


def test_existing_active_authority_permanently_blocks_before_provider(
    tmp_path: Path,
) -> None:
    target = tmp_path / genesis.ACTIVE_AUTHORITY_REL
    target.parent.mkdir(parents=True)
    target.write_text("{}\n", encoding="utf-8")
    result, provider = _proposal(tmp_path)
    assert result["state"] == "BLOCK"
    assert result["reason_code"] == (
        "BLOCK_ACTIVE_AUTHORITY_ALREADY_EXISTS_PERMANENT"
    )
    assert provider.call_count == 0
    assert target.read_text(encoding="utf-8") == "{}\n"


def test_active_authority_appearing_before_stage_b_permanently_blocks(
    tmp_path: Path,
) -> None:
    proposal, _ = _proposal(tmp_path)
    target = tmp_path / genesis.ACTIVE_AUTHORITY_REL
    target.parent.mkdir(parents=True)
    target.write_text("{}\n", encoding="utf-8")
    result, verifier, ledger = _seal(tmp_path, proposal)
    assert result["state"] == "BLOCK"
    assert result["reason_code"] == (
        "BLOCK_ACTIVE_AUTHORITY_ALREADY_EXISTS_PERMANENT"
    )
    assert verifier.calls == []
    assert ledger.call_count == 0
    assert target.read_text(encoding="utf-8") == "{}\n"


def test_nonpersistent_nonce_ledger_holds(tmp_path: Path) -> None:
    proposal, _ = _proposal(tmp_path)
    ledger = _Ledger()
    ledger.persistent = False
    result, _, _ = _seal(tmp_path, proposal, ledger=ledger)
    assert result["reason_code"] == "HOLD_NONCE_LEDGER_NOT_PERSISTENT"
    assert ledger.call_count == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("proposal_ref", _ref("genesis_proposal_ref", "proposal")),
        ("founder_signature_sha256", "0" * 64),
        ("owner_seal_sha256", "0" * 64),
        ("revocation_sha256", "0" * 64),
        ("nonce_consumed", True),
        ("sealed_candidate_sha256", "0" * 64),
        ("activation_capability", {}),
    ],
)
def test_schema_rejects_stage_b_fields_on_stage_a(
    tmp_path: Path,
    field: str,
    value: Any,
) -> None:
    proposal, _ = _proposal(tmp_path)
    proposal[field] = value
    validator = Draft202012Validator(
        _schema(), format_checker=FormatChecker()
    )
    assert list(validator.iter_errors(proposal))


def test_manifest_excludes_itself_and_hashes_exact_three_inputs() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "W7TP_SHA256_MANIFEST_V1"
    assert manifest["candidate_id"] == genesis.SCHEMA_ID
    assert manifest["manifest_path"] == MANIFEST_PATH.relative_to(
        REPO_ROOT
    ).as_posix()
    assert manifest["manifest_excludes_itself"] is True
    assert manifest["active_authority_created"] is False
    assert manifest["receiver_call_count"] == 0
    expected = {
        "tools/total_field_genesis_authority_bootstrap_candidate.py",
        "schemas/field/w7tp_total_field_genesis_authority_bootstrap_candidate_v1.schema.json",
        "tests/test_total_field_genesis_authority_bootstrap_candidate.py",
    }
    paths = [entry["path"] for entry in manifest["files"]]
    assert len(paths) == len(set(paths)) == 3
    assert set(paths) == expected
    assert manifest["manifest_path"] not in expected
    for entry in manifest["files"]:
        raw = (REPO_ROOT / entry["path"]).read_bytes()
        assert entry["bytes"] == len(raw)
        assert entry["sha256"] == hashlib.sha256(raw).hexdigest()


def test_red_team_static_boundary_has_no_receiver_crypto_or_write_path() -> None:
    source_path = REPO_ROOT / "tools/total_field_genesis_authority_bootstrap_candidate.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    called_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called_names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called_names.add(node.func.attr)
    assert imported_roots.isdisjoint(
        {"cryptography", "nacl", "OpenSSL", "sqlite3", "subprocess"}
    )
    assert called_names.isdisjoint(
        {
            "receive_candidate",
            "open",
            "write_text",
            "write_bytes",
            "mkdir",
            "rename",
            "unlink",
        }
    )
    assert genesis.SingleUseAtomicAuthorityStore.__module__ == genesis.__name__
