"""Single-use, candidate-only Total Field genesis authority bootstrap.

This module closes the circular bootstrap problem without creating authority.
Stage A binds the existing read-only Founder identity provider to a genesis
proposal without requiring an existing D8 PASS.  Stage B verifies externally
signed Founder, Owner-seal, and revocation evidence and emits a sealed
candidate.  Stage C is only an injected atomic-store protocol; it is never
implemented or invoked here.

No function in this module writes the active authority pointer, calls a
receiver, reads private keys, writes a database, deploys, or restarts a
service.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections.abc import Collection, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from tools.total_field.w7tp_intent_field_suite.founder_identity_evidence_provider import (
    PROVIDER_ID,
    REGISTRY_COORDINATE,
)


SCHEMA_ID = "W7TP_TOTAL_FIELD_GENESIS_AUTHORITY_BOOTSTRAP_CANDIDATE_V1"
EVIDENCE_BUNDLE_SCHEMA_ID = (
    "W7TP_TOTAL_FIELD_GENESIS_AUTHORITY_EVIDENCE_BUNDLE_V1"
)
FOUNDER_SIGNATURE_SCHEMA_ID = (
    "W7TP_TOTAL_FIELD_GENESIS_FOUNDER_SIGNATURE_V1"
)
OWNER_SEAL_SCHEMA_ID = "W7TP_TOTAL_FIELD_GENESIS_OWNER_SEAL_V1"
REVOCATION_SCHEMA_ID = "W7TP_TOTAL_FIELD_GENESIS_REVOCATION_V1"
ACTIVE_AUTHORITY_REL = Path(
    "runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json"
)
AUTHORITY_SCOPE = (
    "E5_FORMAL_READ_ONLY_REVIEW",
    "RECEIVE_CANDIDATE",
)
MAX_TTL_SECONDS = 300

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_HASH_REF = re.compile(r"^[a-z0-9][a-z0-9_.-]*:sha256:[0-9a-f]{64}$")
_NONCE_REF = re.compile(r"^nonce_ref:sha256:[0-9a-f]{64}$")
_VERIFIER_REF = re.compile(r"^verifier_ref:[A-Za-z0-9_.:-]{8,256}$")
_FORBIDDEN_KEYS = frozenset(
    {
        "access_token",
        "address",
        "credential",
        "email",
        "member_name",
        "member_plaintext",
        "mobile",
        "name",
        "password",
        "phone",
        "private_key",
        "provider_profile",
        "raw_credential",
        "raw_key",
        "raw_provider_profile",
        "raw_provider_subject",
        "refresh_token",
        "secret",
        "token",
    }
)

_PROPOSAL_FIELDS = frozenset(
    {
        "schema_id",
        "stage",
        "state",
        "candidate_only",
        "authority_granted",
        "active_authority_created",
        "activation_called",
        "receiver_call_count",
        "second_authority_created",
        "second_receiver_created",
        "database_written",
        "deployment_performed",
        "service_restarted",
        "private_key_read",
        "member_plaintext_included",
        "existing_d8_pass_required",
        "total_field_decision",
        "authority_record_path",
        "authority_id",
        "authority_version",
        "authority_scope",
        "issued_at",
        "expires_at",
        "nonce",
        "verifier_ref",
        "registry_coordinate",
        "founder_person_packet_ref",
        "founder_identity_root_ref",
        "founder_role_seat_ref",
        "registered_device_ref",
        "founder_capability_assignment_ref",
        "access_profile_ref",
        "evidence_bundle_sha256",
        "evidence_refs",
        "proposal_sha256",
        "red_team_pre_definition",
    }
)


class FounderEvidenceProvider(Protocol):
    """Existing candidate-only provider interface."""

    def collect_and_verify(self) -> Mapping[str, Any]: ...


class PersistentNonceLedger(Protocol):
    """Persistent replay barrier; process-local sets are not sufficient."""

    persistent: bool
    global_nonce_uniqueness: bool

    def mark_used_or_replay(
        self,
        nonce: str,
        packet_hash: str,
        now_epoch: float,
        ttl_seconds: int,
    ) -> bool:
        """Consume nonce globally; packet_hash is binding metadata only.

        Return the literal boolean True exactly once for a nonce, and False
        for every later use even when a different packet hash is supplied.
        """


class TrustedExternalSignatureVerifier(Protocol):
    """Injected standard verifier; implementations own all cryptography."""

    trusted_runtime_verifier: bool

    def verify(
        self,
        *,
        verifier_ref: str,
        expected_signer_identity_root_ref: str,
        expected_role_seat_ref: str,
        verification_method_ref: str,
        payload_sha256: str,
        signature: str,
    ) -> bool: ...


class SingleUseAtomicAuthorityStore(Protocol):
    """Stage-C landing capability, intentionally not implemented or invoked.

    A conforming runtime must create the fixed pointer only if absent and make
    the same single-use coordinate permanently unable to run again in one
    durable atomic operation.
    """

    persistent: bool
    atomic_create_if_absent: bool
    permanent_self_stop: bool

    def create_once_and_permanently_stop(
        self,
        *,
        target: Path,
        sealed_candidate: Mapping[str, Any],
        single_use_nonce: str,
    ) -> bool: ...


class GenesisCandidateError(RuntimeError):
    """Internal fail-closed gate result."""

    def __init__(self, state: str, reason_code: str) -> None:
        super().__init__(reason_code)
        self.state = state
        self.reason_code = reason_code


def canonical_sha256(value: Any) -> str:
    """Hash canonical JSON bytes without signing or key access."""

    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def evidence_bundle_sha256(bundle: Mapping[str, Any]) -> str:
    """Hash an evidence bundle with its digest carrier removed."""

    unsigned = copy.deepcopy(dict(bundle))
    unsigned.pop("evidence_sha256", None)
    return canonical_sha256(unsigned)


def _self_hash(document: Mapping[str, Any], field: str) -> str:
    unsigned = copy.deepcopy(dict(document))
    unsigned.pop(field, None)
    return canonical_sha256(unsigned)


def _failure(state: str, reason_code: str) -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "state": state,
        "reason_code": reason_code,
        "candidate_only": True,
        "authority_granted": False,
        "active_authority_created": False,
        "activation_called": False,
        "receiver_call_count": 0,
        "second_authority_created": False,
        "second_receiver_created": False,
        "database_written": False,
        "deployment_performed": False,
        "service_restarted": False,
        "private_key_read": False,
        "member_plaintext_included": False,
        "total_field_decision": "NOT_RUN",
    }


def _require(condition: bool, state: str, reason_code: str) -> None:
    if not condition:
        raise GenesisCandidateError(state, reason_code)


def _walk_forbidden(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            _require(
                isinstance(key, str) and key.casefold() not in _FORBIDDEN_KEYS,
                "HOLD",
                "HOLD_MEMBER_PLAINTEXT_BOUNDARY",
            )
            _walk_forbidden(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _walk_forbidden(nested)


def _parse_utc(value: Any, reason_code: str) -> datetime:
    _require(
        isinstance(value, str) and value.endswith("Z"), "HOLD", reason_code
    )
    assert isinstance(value, str)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise GenesisCandidateError("HOLD", reason_code) from exc
    _require(parsed.tzinfo is not None, "HOLD", reason_code)
    return parsed.astimezone(timezone.utc)


def _hash_ref(value: Any, reason_code: str, *, state: str = "HOLD") -> str:
    _require(
        isinstance(value, str) and _HASH_REF.fullmatch(value) is not None,
        state,
        reason_code,
    )
    return str(value)


def _exact_single(
    bundle: Mapping[str, Any], field: str, reason_code: str
) -> Mapping[str, Any]:
    values = bundle.get(field)
    _require(
        isinstance(values, Sequence)
        and not isinstance(values, (str, bytes))
        and len(values) == 1
        and isinstance(values[0], Mapping),
        "HOLD",
        reason_code,
    )
    return values[0]


def _assert_active_authority_absent(repo_root: Path) -> None:
    target = Path(repo_root) / ACTIVE_AUTHORITY_REL
    _require(
        not target.exists() and not target.is_symlink(),
        "BLOCK",
        "BLOCK_ACTIVE_AUTHORITY_ALREADY_EXISTS_PERMANENT",
    )


def _validate_provider_result(result: Any) -> Mapping[str, Any]:
    _require(isinstance(result, Mapping), "HOLD", "HOLD_PROVIDER_RESULT_INVALID")
    assert isinstance(result, Mapping)
    _walk_forbidden(result)
    _require(
        result.get("state") == "PASS"
        and result.get("candidate_only") is True
        and result.get("provider_id") == PROVIDER_ID
        and result.get("registry_coordinate") == REGISTRY_COORDINATE
        and type(result.get("root_registry_cardinality")) is int
        and result.get("root_registry_cardinality") == 1
        and result.get("second_registry_created") is False
        and result.get("member_plaintext_read") is False,
        "HOLD",
        "HOLD_FOUNDER_PROVIDER_NOT_VERIFIED",
    )
    p1 = result.get("p1_verifier_result")
    _require(
        isinstance(p1, Mapping) and p1.get("state") == "PASS",
        "HOLD",
        "HOLD_FOUNDER_P1_NOT_VERIFIED",
    )
    for field in (
        "founder_role_seat_ref",
        "founder_identity_root_ref",
        "founder_identity_binding_receipt_ref",
        "8d_adi_binding_evidence_ref",
        "current_root_registry_cardinality_evidence_ref",
    ):
        _hash_ref(result.get(field), "HOLD_FOUNDER_PROVIDER_BINDING_INVALID")
    return result


def _validate_evidence_bundle(
    bundle: Any,
    provider_result: Mapping[str, Any],
) -> dict[str, str]:
    _require(isinstance(bundle, Mapping), "HOLD", "HOLD_EVIDENCE_BUNDLE_INVALID")
    assert isinstance(bundle, Mapping)
    _walk_forbidden(bundle)
    required = {
        "schema_id",
        "registry_coordinates",
        "founders",
        "identity_roots",
        "role_seats",
        "registered_devices",
        "founder_capability_assignment_ref",
        "access_profile_ref",
        "evidence_sha256",
    }
    _require(set(bundle) == required, "HOLD", "HOLD_EVIDENCE_BUNDLE_INVALID")
    _require(
        bundle.get("schema_id") == EVIDENCE_BUNDLE_SCHEMA_ID
        and bundle.get("evidence_sha256") == evidence_bundle_sha256(bundle),
        "HOLD",
        "HOLD_EVIDENCE_HASH_MISMATCH",
    )
    coordinates = bundle.get("registry_coordinates")
    _require(
        coordinates == [REGISTRY_COORDINATE],
        "HOLD",
        "HOLD_SECOND_REGISTRY_COORDINATE",
    )

    founder = _exact_single(bundle, "founders", "HOLD_FOUNDER_CARDINALITY")
    root = _exact_single(bundle, "identity_roots", "HOLD_IDENTITY_ROOT_CARDINALITY")
    seat = _exact_single(bundle, "role_seats", "HOLD_ROLE_SEAT_CARDINALITY")
    device = _exact_single(
        bundle, "registered_devices", "HOLD_REGISTERED_DEVICE_CARDINALITY"
    )
    _require(
        set(founder)
        == {
            "founder_person_packet_ref",
            "identity_root_ref",
            "role_seat_ref",
            "registered_device_ref",
        }
        and set(root) == {"identity_root_ref"}
        and set(seat) == {"role_code", "role_seat_ref", "identity_root_ref"}
        and set(device) == {"registered_device_ref", "identity_root_ref"},
        "HOLD",
        "HOLD_IDENTITY_EVIDENCE_SHAPE_INVALID",
    )

    founder_ref = _hash_ref(
        founder.get("founder_person_packet_ref"), "HOLD_FOUNDER_BINDING_INVALID"
    )
    root_ref = _hash_ref(root.get("identity_root_ref"), "HOLD_ROOT_BINDING_INVALID")
    seat_ref = _hash_ref(seat.get("role_seat_ref"), "HOLD_SEAT_BINDING_INVALID")
    device_ref = _hash_ref(
        device.get("registered_device_ref"), "HOLD_DEVICE_BINDING_INVALID"
    )
    capability_ref = _hash_ref(
        bundle.get("founder_capability_assignment_ref"),
        "HOLD_CAPABILITY_BINDING_INVALID",
    )
    access_profile_ref = _hash_ref(
        bundle.get("access_profile_ref"), "HOLD_ACCESS_PROFILE_BINDING_INVALID"
    )
    _require(
        founder.get("identity_root_ref") == root_ref
        and founder.get("role_seat_ref") == seat_ref
        and founder.get("registered_device_ref") == device_ref
        and seat.get("identity_root_ref") == root_ref
        and seat.get("role_code") == "FOUNDER"
        and device.get("identity_root_ref") == root_ref
        and provider_result.get("founder_identity_root_ref") == root_ref
        and provider_result.get("founder_role_seat_ref") == seat_ref,
        "HOLD",
        "HOLD_FOUNDER_ROOT_SEAT_DEVICE_BINDING_MISMATCH",
    )
    return {
        "founder_person_packet_ref": founder_ref,
        "founder_identity_root_ref": root_ref,
        "founder_role_seat_ref": seat_ref,
        "registered_device_ref": device_ref,
        "founder_capability_assignment_ref": capability_ref,
        "access_profile_ref": access_profile_ref,
    }


def _validate_request(request: Any, now: datetime) -> tuple[dict[str, Any], int]:
    _require(isinstance(request, Mapping), "HOLD", "HOLD_REQUEST_INVALID")
    assert isinstance(request, Mapping)
    _walk_forbidden(request)
    _require(
        set(request)
        == {"issued_at", "expires_at", "nonce", "verifier_ref", "authority_scope"},
        "HOLD",
        "HOLD_REQUEST_INVALID",
    )
    issued = _parse_utc(request.get("issued_at"), "HOLD_AUTHORITY_TIME_INVALID")
    expires = _parse_utc(request.get("expires_at"), "HOLD_AUTHORITY_TIME_INVALID")
    _require(now.tzinfo is not None, "HOLD", "HOLD_AUTHORITY_TIME_INVALID")
    current = now.astimezone(timezone.utc)
    ttl_value = (expires - issued).total_seconds()
    _require(
        issued <= current < expires
        and 0 < ttl_value <= MAX_TTL_SECONDS,
        "HOLD",
        "HOLD_AUTHORITY_EXPIRED",
    )
    ttl = math.ceil(ttl_value)
    nonce = request.get("nonce")
    verifier_ref = request.get("verifier_ref")
    _require(
        isinstance(nonce, str) and _NONCE_REF.fullmatch(nonce) is not None,
        "HOLD",
        "HOLD_NONCE_INVALID",
    )
    _require(
        isinstance(verifier_ref, str)
        and _VERIFIER_REF.fullmatch(verifier_ref) is not None,
        "HOLD",
        "HOLD_VERIFIER_REF_INVALID",
    )
    _require(
        request.get("authority_scope") == list(AUTHORITY_SCOPE),
        "HOLD",
        "HOLD_AUTHORITY_SCOPE_INVALID",
    )
    return dict(request), ttl


def _red_team_definition() -> dict[str, str]:
    return {
        "active_authority_preexistence": "PERMANENT_BLOCK",
        "activation_in_this_run": "FORBIDDEN",
        "database_write": "FORBIDDEN",
        "external_signature_verifier": "REQUIRED",
        "persistent_nonce": "REQUIRED",
        "private_key_access": "FORBIDDEN",
        "second_authority": "FORBIDDEN",
        "second_receiver": "FORBIDDEN",
        "second_registry_coordinate": "FORBIDDEN",
    }


def build_genesis_proposal(
    *,
    repo_root: Path,
    founder_evidence_provider: FounderEvidenceProvider,
    evidence_bundle: Mapping[str, Any],
    authority_request: Mapping[str, Any],
    now: datetime,
) -> dict[str, Any]:
    """Build Stage A without an existing D8 decision or any state mutation."""

    try:
        _assert_active_authority_absent(Path(repo_root))
        try:
            raw_provider_result = founder_evidence_provider.collect_and_verify()
        except Exception as exc:
            raise GenesisCandidateError(
                "HOLD", "HOLD_FOUNDER_PROVIDER_CALL_FAILED"
            ) from exc
        provider_result = _validate_provider_result(raw_provider_result)
        bindings = _validate_evidence_bundle(evidence_bundle, provider_result)
        request, _ = _validate_request(authority_request, now)
        _assert_active_authority_absent(Path(repo_root))

        authority_seed = {
            "evidence_bundle_sha256": evidence_bundle["evidence_sha256"],
            "founder_person_packet_ref": bindings["founder_person_packet_ref"],
            "nonce": request["nonce"],
            "registry_coordinate": REGISTRY_COORDINATE,
        }
        authority_id = f"authority_ref:sha256:{canonical_sha256(authority_seed)}"
        proposal: dict[str, Any] = {
            "schema_id": SCHEMA_ID,
            "stage": "A_GENESIS_PROPOSAL",
            "state": "GENESIS_PROPOSAL_CANDIDATE",
            "candidate_only": True,
            "authority_granted": False,
            "active_authority_created": False,
            "activation_called": False,
            "receiver_call_count": 0,
            "second_authority_created": False,
            "second_receiver_created": False,
            "database_written": False,
            "deployment_performed": False,
            "service_restarted": False,
            "private_key_read": False,
            "member_plaintext_included": False,
            "existing_d8_pass_required": False,
            "total_field_decision": "NOT_RUN",
            "authority_record_path": ACTIVE_AUTHORITY_REL.as_posix(),
            "authority_id": authority_id,
            "authority_version": 1,
            "authority_scope": list(AUTHORITY_SCOPE),
            "issued_at": request["issued_at"],
            "expires_at": request["expires_at"],
            "nonce": request["nonce"],
            "verifier_ref": request["verifier_ref"],
            "registry_coordinate": REGISTRY_COORDINATE,
            **bindings,
            "evidence_bundle_sha256": evidence_bundle["evidence_sha256"],
            "evidence_refs": {
                "founder_identity_binding_receipt_ref": provider_result[
                    "founder_identity_binding_receipt_ref"
                ],
                "8d_adi_binding_evidence_ref": provider_result[
                    "8d_adi_binding_evidence_ref"
                ],
                "current_root_registry_cardinality_evidence_ref": provider_result[
                    "current_root_registry_cardinality_evidence_ref"
                ],
            },
            "red_team_pre_definition": _red_team_definition(),
        }
        proposal["proposal_sha256"] = _self_hash(proposal, "proposal_sha256")
        return proposal
    except GenesisCandidateError as exc:
        return _failure(exc.state, exc.reason_code)
    except (TypeError, ValueError, OverflowError):
        return _failure("HOLD", "HOLD_GENESIS_PROPOSAL_INVALID")


def _validate_proposal(
    proposal: Any, now: datetime
) -> tuple[Mapping[str, Any], int]:
    _require(isinstance(proposal, Mapping), "HOLD", "HOLD_PROPOSAL_INVALID")
    assert isinstance(proposal, Mapping)
    _require(set(proposal) == _PROPOSAL_FIELDS, "HOLD", "HOLD_PROPOSAL_INVALID")
    _walk_forbidden(proposal)

    supplied = proposal.get("proposal_sha256")
    _require(
        isinstance(supplied, str)
        and _SHA256.fullmatch(supplied) is not None
        and supplied == _self_hash(proposal, "proposal_sha256"),
        "BLOCK",
        "BLOCK_PROPOSAL_HASH_MISMATCH",
    )

    fixed_false_fields = (
        "authority_granted",
        "active_authority_created",
        "activation_called",
        "second_authority_created",
        "second_receiver_created",
        "database_written",
        "deployment_performed",
        "service_restarted",
        "private_key_read",
        "member_plaintext_included",
        "existing_d8_pass_required",
    )
    _require(
        proposal.get("schema_id") == SCHEMA_ID
        and proposal.get("stage") == "A_GENESIS_PROPOSAL"
        and proposal.get("state") == "GENESIS_PROPOSAL_CANDIDATE"
        and proposal.get("candidate_only") is True
        and all(proposal.get(field) is False for field in fixed_false_fields)
        and type(proposal.get("receiver_call_count")) is int
        and proposal.get("receiver_call_count") == 0
        and proposal.get("total_field_decision") == "NOT_RUN",
        "BLOCK",
        "BLOCK_PROPOSAL_BOUNDARY_INVALID",
    )
    _require(
        proposal.get("authority_record_path") == ACTIVE_AUTHORITY_REL.as_posix()
        and type(proposal.get("authority_version")) is int
        and proposal.get("authority_version") == 1
        and proposal.get("authority_scope") == list(AUTHORITY_SCOPE)
        and proposal.get("registry_coordinate") == REGISTRY_COORDINATE
        and proposal.get("red_team_pre_definition") == _red_team_definition(),
        "BLOCK",
        "BLOCK_PROPOSAL_BOUNDARY_INVALID",
    )

    nonce = proposal.get("nonce")
    verifier_ref = proposal.get("verifier_ref")
    _require(
        isinstance(nonce, str) and _NONCE_REF.fullmatch(nonce) is not None
        and isinstance(verifier_ref, str)
        and _VERIFIER_REF.fullmatch(verifier_ref) is not None,
        "BLOCK",
        "BLOCK_PROPOSAL_BINDING_INVALID",
    )
    for field in (
        "authority_id",
        "founder_person_packet_ref",
        "founder_identity_root_ref",
        "founder_role_seat_ref",
        "registered_device_ref",
        "founder_capability_assignment_ref",
        "access_profile_ref",
    ):
        _hash_ref(
            proposal.get(field),
            "BLOCK_PROPOSAL_BINDING_INVALID",
            state="BLOCK",
        )
    _require(
        isinstance(proposal.get("evidence_bundle_sha256"), str)
        and _SHA256.fullmatch(proposal["evidence_bundle_sha256"]) is not None,
        "BLOCK",
        "BLOCK_PROPOSAL_BINDING_INVALID",
    )
    evidence_refs = proposal.get("evidence_refs")
    expected_evidence_ref_fields = {
        "founder_identity_binding_receipt_ref",
        "8d_adi_binding_evidence_ref",
        "current_root_registry_cardinality_evidence_ref",
    }
    _require(
        isinstance(evidence_refs, Mapping)
        and set(evidence_refs) == expected_evidence_ref_fields,
        "BLOCK",
        "BLOCK_PROPOSAL_BINDING_INVALID",
    )
    assert isinstance(evidence_refs, Mapping)
    for value in evidence_refs.values():
        _hash_ref(value, "BLOCK_PROPOSAL_BINDING_INVALID", state="BLOCK")

    authority_seed = {
        "evidence_bundle_sha256": proposal["evidence_bundle_sha256"],
        "founder_person_packet_ref": proposal["founder_person_packet_ref"],
        "nonce": nonce,
        "registry_coordinate": REGISTRY_COORDINATE,
    }
    _require(
        proposal.get("authority_id")
        == f"authority_ref:sha256:{canonical_sha256(authority_seed)}",
        "BLOCK",
        "BLOCK_PROPOSAL_BINDING_INVALID",
    )

    _require(now.tzinfo is not None, "HOLD", "HOLD_AUTHORITY_TIME_INVALID")
    issued = _parse_utc(proposal.get("issued_at"), "HOLD_AUTHORITY_TIME_INVALID")
    expires = _parse_utc(proposal.get("expires_at"), "HOLD_AUTHORITY_TIME_INVALID")
    current = now.astimezone(timezone.utc)
    ttl_value = (expires - issued).total_seconds()
    _require(
        issued <= current < expires
        and 0 < ttl_value <= MAX_TTL_SECONDS,
        "HOLD",
        "HOLD_AUTHORITY_EXPIRED",
    )
    return proposal, math.ceil(ttl_value)


def _trusted_verifier(
    verifier: Any,
    verifier_ref: Any,
    trusted_verifier_refs: Collection[str],
) -> str:
    try:
        runtime_trusted = getattr(verifier, "trusted_runtime_verifier", False)
        trusted_refs = set(trusted_verifier_refs)
    except Exception as exc:
        raise GenesisCandidateError(
            "HOLD", "HOLD_TRUSTED_VERIFIER_UNAVAILABLE"
        ) from exc
    _require(
        isinstance(verifier_ref, str)
        and verifier_ref in trusted_refs
        and runtime_trusted is True,
        "HOLD",
        "HOLD_TRUSTED_VERIFIER_UNAVAILABLE",
    )
    return verifier_ref


def _verify_signature(
    verifier: TrustedExternalSignatureVerifier,
    *,
    verifier_ref: str,
    expected_signer_identity_root_ref: str,
    expected_role_seat_ref: str,
    verification_method_ref: str,
    payload_sha256: Any,
    signature: Any,
    reason_code: str,
) -> None:
    _require(
        isinstance(payload_sha256, str)
        and _SHA256.fullmatch(payload_sha256) is not None
        and isinstance(signature, str)
        and bool(signature),
        "BLOCK",
        reason_code,
    )
    try:
        verified = verifier.verify(
            verifier_ref=verifier_ref,
            expected_signer_identity_root_ref=(
                expected_signer_identity_root_ref
            ),
            expected_role_seat_ref=expected_role_seat_ref,
            verification_method_ref=verification_method_ref,
            payload_sha256=payload_sha256,
            signature=signature,
        )
    except Exception as exc:
        raise GenesisCandidateError(
            "HOLD", "HOLD_TRUSTED_VERIFIER_CALL_FAILED"
        ) from exc
    _require(
        isinstance(verified, bool),
        "HOLD",
        "HOLD_TRUSTED_VERIFIER_RESULT_INVALID",
    )
    _require(verified, "BLOCK", reason_code)


def _verify_signed_artifact(
    artifact: Any,
    *,
    expected_schema_id: str,
    authority_id: str,
    proposal_verifier_ref: str,
    verifier: TrustedExternalSignatureVerifier,
    trusted_verifier_refs: Collection[str],
    expected_signer_identity_root_ref: str,
    expected_role_seat_ref: str,
    expected_verification_method_ref: str,
    now: datetime,
    extra_fields: set[str],
    reason_code: str,
) -> Mapping[str, Any]:
    _require(isinstance(artifact, Mapping), "HOLD", reason_code)
    assert isinstance(artifact, Mapping)
    required = {
        "schema_id",
        "authority_id",
        "issued_at",
        "expires_at",
        "verifier_ref",
        "signer_identity_root_ref",
        "signer_role_seat_ref",
        "verification_method_ref",
        "payload_sha256",
        "signature",
    } | extra_fields
    _require(set(artifact) == required, "HOLD", reason_code)
    _walk_forbidden(artifact)
    verifier_ref = _trusted_verifier(
        verifier, artifact.get("verifier_ref"), trusted_verifier_refs
    )
    _require(
        artifact.get("schema_id") == expected_schema_id
        and artifact.get("authority_id") == authority_id
        and verifier_ref == proposal_verifier_ref
        and artifact.get("signer_identity_root_ref")
        == expected_signer_identity_root_ref
        and artifact.get("signer_role_seat_ref") == expected_role_seat_ref
        and artifact.get("verification_method_ref")
        == expected_verification_method_ref,
        "BLOCK",
        reason_code,
    )
    issued = _parse_utc(artifact.get("issued_at"), reason_code)
    expires = _parse_utc(artifact.get("expires_at"), reason_code)
    current = now.astimezone(timezone.utc)
    _require(issued <= current < expires, "HOLD", "HOLD_AUTHORITY_EXPIRED")
    unsigned = dict(artifact)
    signature = unsigned.pop("signature")
    supplied = unsigned.pop("payload_sha256")
    _require(
        supplied == canonical_sha256(unsigned),
        "BLOCK",
        "BLOCK_SIGNED_ARTIFACT_HASH_MISMATCH",
    )
    _verify_signature(
        verifier,
        verifier_ref=verifier_ref,
        expected_signer_identity_root_ref=expected_signer_identity_root_ref,
        expected_role_seat_ref=expected_role_seat_ref,
        verification_method_ref=expected_verification_method_ref,
        payload_sha256=supplied,
        signature=signature,
        reason_code=reason_code,
    )
    return artifact


def _activation_capability() -> dict[str, Any]:
    return {
        "capability_id": "W7TP_TOTAL_FIELD_GENESIS_ATOMIC_ACTIVATION_V1",
        "target": ACTIVE_AUTHORITY_REL.as_posix(),
        "single_use": True,
        "atomic_create_if_absent": True,
        "persistent_nonce_required": True,
        "permanent_self_stop_after_success": True,
        "call_forbidden_in_candidate_build": True,
        "implementation": "INJECTED_SINGLE_USE_ATOMIC_AUTHORITY_STORE",
    }


def seal_genesis_candidate(
    *,
    repo_root: Path,
    proposal: Mapping[str, Any],
    founder_signature: Mapping[str, Any],
    owner_seal: Mapping[str, Any],
    revocation_record: Mapping[str, Any],
    signature_verifier: TrustedExternalSignatureVerifier,
    trusted_verifier_refs: Collection[str],
    nonce_ledger: PersistentNonceLedger,
    now: datetime,
) -> dict[str, Any]:
    """Build Stage B and consume its persistent nonce without activation."""

    try:
        _assert_active_authority_absent(Path(repo_root))
        proposal_value, ttl_seconds = _validate_proposal(proposal, now)
        authority_id = str(proposal_value["authority_id"])
        proposal_sha256 = str(proposal_value["proposal_sha256"])
        signer_identity_root_ref = str(
            proposal_value["founder_identity_root_ref"]
        )
        signer_role_seat_ref = str(proposal_value["founder_role_seat_ref"])
        verification_method_ref = str(proposal_value["registered_device_ref"])
        proposal_verifier_ref = _trusted_verifier(
            signature_verifier,
            proposal_value.get("verifier_ref"),
            trusted_verifier_refs,
        )

        _require(
            isinstance(founder_signature, Mapping)
            and set(founder_signature)
            == {
                "schema_id",
                "authority_id",
                "signed_payload_sha256",
                "verifier_ref",
                "signer_identity_root_ref",
                "signer_role_seat_ref",
                "verification_method_ref",
                "signature",
            }
            and founder_signature.get("schema_id") == FOUNDER_SIGNATURE_SCHEMA_ID
            and founder_signature.get("authority_id") == authority_id
            and founder_signature.get("signed_payload_sha256") == proposal_sha256
            and founder_signature.get("verifier_ref") == proposal_verifier_ref,
            "BLOCK",
            "BLOCK_FOUNDER_SIGNATURE_INVALID",
        )
        _require(
            founder_signature.get("signer_identity_root_ref")
            == signer_identity_root_ref
            and founder_signature.get("signer_role_seat_ref")
            == signer_role_seat_ref
            and founder_signature.get("verification_method_ref")
            == verification_method_ref,
            "BLOCK",
            "BLOCK_FOUNDER_SIGNATURE_INVALID",
        )
        _walk_forbidden(founder_signature)
        _verify_signature(
            signature_verifier,
            verifier_ref=proposal_verifier_ref,
            expected_signer_identity_root_ref=signer_identity_root_ref,
            expected_role_seat_ref=signer_role_seat_ref,
            verification_method_ref=verification_method_ref,
            payload_sha256=proposal_sha256,
            signature=founder_signature.get("signature"),
            reason_code="BLOCK_FOUNDER_SIGNATURE_INVALID",
        )

        owner = _verify_signed_artifact(
            owner_seal,
            expected_schema_id=OWNER_SEAL_SCHEMA_ID,
            authority_id=authority_id,
            proposal_verifier_ref=proposal_verifier_ref,
            verifier=signature_verifier,
            trusted_verifier_refs=trusted_verifier_refs,
            expected_signer_identity_root_ref=signer_identity_root_ref,
            expected_role_seat_ref=signer_role_seat_ref,
            expected_verification_method_ref=verification_method_ref,
            now=now,
            extra_fields={"authorization", "single_use_id"},
            reason_code="BLOCK_OWNER_SEAL_INVALID",
        )
        _require(
            owner.get("authorization")
            == "FOUNDER_APPROVED_GENESIS_AUTHORITY_CANDIDATE"
            and owner.get("single_use_id") == proposal_value.get("nonce"),
            "BLOCK",
            "BLOCK_OWNER_SEAL_INVALID",
        )

        revocation = _verify_signed_artifact(
            revocation_record,
            expected_schema_id=REVOCATION_SCHEMA_ID,
            authority_id=authority_id,
            proposal_verifier_ref=proposal_verifier_ref,
            verifier=signature_verifier,
            trusted_verifier_refs=trusted_verifier_refs,
            expected_signer_identity_root_ref=signer_identity_root_ref,
            expected_role_seat_ref=signer_role_seat_ref,
            expected_verification_method_ref=verification_method_ref,
            now=now,
            extra_fields={"revoked_authority_ids", "revoked_signature_sha256s"},
            reason_code="BLOCK_REVOCATION_RECORD_INVALID",
        )
        revoked_authorities = revocation.get("revoked_authority_ids")
        revoked_signatures = revocation.get("revoked_signature_sha256s")
        founder_signature_sha256 = canonical_sha256(founder_signature)
        owner_seal_sha256 = canonical_sha256(owner_seal)
        _require(
            isinstance(revoked_authorities, list)
            and all(
                isinstance(item, str)
                and _HASH_REF.fullmatch(item) is not None
                for item in revoked_authorities
            )
            and isinstance(revoked_signatures, list)
            and all(
                isinstance(item, str) and _SHA256.fullmatch(item) is not None
                for item in revoked_signatures
            ),
            "BLOCK",
            "BLOCK_REVOCATION_RECORD_INVALID",
        )
        _require(
            authority_id not in revoked_authorities
            and founder_signature_sha256 not in revoked_signatures,
            "BLOCK",
            "BLOCK_GENESIS_AUTHORITY_REVOKED",
        )
        _require(
            owner_seal_sha256 not in revoked_signatures,
            "BLOCK",
            "BLOCK_GENESIS_AUTHORITY_REVOKED",
        )

        try:
            persistent_nonce = getattr(nonce_ledger, "persistent", False)
            globally_unique_nonce = getattr(
                nonce_ledger, "global_nonce_uniqueness", False
            )
        except Exception as exc:
            raise GenesisCandidateError(
                "HOLD", "HOLD_NONCE_LEDGER_NOT_PERSISTENT"
            ) from exc
        _require(
            persistent_nonce is True and globally_unique_nonce is True,
            "HOLD",
            "HOLD_NONCE_LEDGER_NOT_PERSISTENT",
        )
        _assert_active_authority_absent(Path(repo_root))
        try:
            nonce_consumed = nonce_ledger.mark_used_or_replay(
                str(proposal_value["nonce"]),
                proposal_sha256,
                now.astimezone(timezone.utc).timestamp(),
                ttl_seconds,
            )
        except Exception as exc:
            raise GenesisCandidateError(
                "HOLD", "HOLD_NONCE_LEDGER_CALL_FAILED"
            ) from exc
        _require(
            isinstance(nonce_consumed, bool),
            "HOLD",
            "HOLD_NONCE_LEDGER_RESULT_INVALID",
        )
        _require(nonce_consumed, "BLOCK", "BLOCK_GENESIS_NONCE_REPLAY")

        sealed = copy.deepcopy(dict(proposal_value))
        sealed.update(
            {
                "stage": "B_SEALED_GENESIS_CANDIDATE",
                "state": "SEALED_GENESIS_AUTHORITY_CANDIDATE",
                "proposal_ref": f"genesis_proposal_ref:sha256:{proposal_sha256}",
                "founder_signature_sha256": founder_signature_sha256,
                "owner_seal_sha256": owner_seal_sha256,
                "revocation_sha256": canonical_sha256(revocation_record),
                "nonce_consumed": True,
                "activation_capability": _activation_capability(),
            }
        )
        sealed["sealed_candidate_sha256"] = _self_hash(
            sealed, "sealed_candidate_sha256"
        )
        return sealed
    except GenesisCandidateError as exc:
        return _failure(exc.state, exc.reason_code)
    except (TypeError, ValueError, OverflowError):
        return _failure("HOLD", "HOLD_GENESIS_SEAL_INVALID")


__all__ = [
    "ACTIVE_AUTHORITY_REL",
    "AUTHORITY_SCOPE",
    "EVIDENCE_BUNDLE_SCHEMA_ID",
    "FOUNDER_SIGNATURE_SCHEMA_ID",
    "OWNER_SEAL_SCHEMA_ID",
    "REVOCATION_SCHEMA_ID",
    "SCHEMA_ID",
    "FounderEvidenceProvider",
    "PersistentNonceLedger",
    "SingleUseAtomicAuthorityStore",
    "TrustedExternalSignatureVerifier",
    "build_genesis_proposal",
    "canonical_sha256",
    "evidence_bundle_sha256",
    "seal_genesis_candidate",
]
