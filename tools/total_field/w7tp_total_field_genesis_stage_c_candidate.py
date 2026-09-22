"""Candidate-only Stage C design for the first Total Field authority.

The public preparation function validates an immutable Stage B document and
produces an activation *plan*.  It never writes the live authority pointer.
The simulation function is deliberately limited to an explicit sandbox and
uses a receipt-first transaction capsule followed by create-if-absent linking.

Nothing in this module grants authority, consumes a real nonce, deploys,
restarts a service, or writes ``runtime/total_field`` in the repository.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol


SCHEMA_ID = "W7TP_TOTAL_FIELD_GENESIS_STAGE_C_CANDIDATE_V1"
RECEIPT_SCHEMA_ID = "W7TP_GENESIS_ACTIVATION_RECEIPT_CANDIDATE_V1"
STAGE_B_SCHEMA_ID = "W7TP_TOTAL_FIELD_GENESIS_AUTHORITY_BOOTSTRAP_CANDIDATE_V1"
FORMAL_AUTHORIZATION_SCHEMA_ID = (
    "W7TP_FOUNDER_GENESIS_AUTHORITY_FORMAL_ACTIVATION_AUTHORIZATION_V1"
)
REVOCATION_STATUS_SCHEMA_ID = "W7TP_GENESIS_AUTHORITY_REVOCATION_STATUS_V1"
TARGET_NODE = "taiji01"
TARGET_HEAD = "7803c64508d2cc402a3cbb999c3f748c28b0c203"
ACTIVE_AUTHORITY_REL = Path("runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json")
FORMAL_ACTIVATION_EFFECT = "AUTHORIZE_FORMAL_GENESIS_AUTHORITY_ACTIVATION"
BUILD_ONLY_EFFECT = "AUTHORIZE_BUILD_VALIDATE_GENESIS_STAGE_C_CANDIDATE_ONLY"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_HASH_REF = re.compile(r"^[a-z0-9][a-z0-9_.-]*:sha256:[0-9a-f]{64}$")
_NONCE_REF = re.compile(r"^nonce_ref:sha256:[0-9a-f]{64}$")
_VERIFIER_REF = re.compile(r"^verifier_ref:[A-Za-z0-9_.:-]{8,256}$")
_AUTHORITY_SCOPE = ["E5_FORMAL_READ_ONLY_REVIEW", "RECEIVE_CANDIDATE"]
_REGISTRY_COORDINATE = (
    "odoo18://wuchang_member_registration/wuchang.member.registration/"
    "sovereign-authority-ledger-candidate-v1"
)
_STAGE_B_FIELDS = {
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
    "proposal_ref",
    "founder_signature_sha256",
    "owner_seal_sha256",
    "revocation_sha256",
    "nonce_consumed",
    "sealed_candidate_sha256",
    "activation_capability",
    "red_team_pre_definition",
}


class StageCError(RuntimeError):
    """Fail-closed Stage C gate result."""

    def __init__(self, state: str, reason_code: str) -> None:
        super().__init__(reason_code)
        self.state = state
        self.reason_code = reason_code


class SimulatedCrash(RuntimeError):
    """Deterministic fault injection used only by sandbox tests."""


class TrustedStageCGovernanceVerifier(Protocol):
    """Injected verifier boundary; Stage C never owns Founder private keys."""

    trusted_runtime_verifier: bool

    def verify_formal_authorization(
        self, authorization: Mapping[str, Any]
    ) -> bool: ...

    def verify_revocation_status(self, status: Mapping[str, Any]) -> bool: ...


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _self_hash(document: Mapping[str, Any], field: str) -> str:
    unsigned = copy.deepcopy(dict(document))
    unsigned.pop(field, None)
    return canonical_sha256(unsigned)


def _parse_utc(value: Any, reason: str) -> datetime:
    _require(isinstance(value, str) and value.endswith("Z"), "HOLD", reason)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise StageCError("HOLD", reason) from exc
    _require(parsed.tzinfo is not None, "HOLD", reason)
    return parsed.astimezone(timezone.utc)


def _require(condition: bool, state: str, reason: str) -> None:
    if not condition:
        raise StageCError(state, reason)


def _failure(state: str, reason: str) -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "state": state,
        "reason_code": reason,
        "candidate_only": True,
        "authority_granted": False,
        "active_authority_created": False,
        "formal_activation_performed": False,
        "live_pointer_written": False,
        "real_nonce_consumed": False,
        "total_field_decision": "NOT_RUN",
    }


def _validate_stage_b(
    stage_b: Any,
    expected_document_sha256: str,
    now: datetime,
) -> Mapping[str, Any]:
    _require(isinstance(stage_b, Mapping), "HOLD", "HOLD_GENESIS_STAGE_B_MISSING")
    assert isinstance(stage_b, Mapping)
    _require(
        _SHA256.fullmatch(expected_document_sha256) is not None
        and canonical_sha256(stage_b) == expected_document_sha256,
        "REJECT",
        "REJECT_GENESIS_STAGE_B_DOCUMENT_HASH_MISMATCH",
    )
    _require(
        set(stage_b) == _STAGE_B_FIELDS,
        "REJECT",
        "REJECT_GENESIS_STAGE_B_SHAPE_INVALID",
    )
    _require(
        stage_b.get("schema_id") == STAGE_B_SCHEMA_ID
        and stage_b.get("stage") == "B_SEALED_GENESIS_CANDIDATE"
        and stage_b.get("state") == "SEALED_GENESIS_AUTHORITY_CANDIDATE"
        and stage_b.get("candidate_only") is True
        and stage_b.get("authority_granted") is False
        and stage_b.get("active_authority_created") is False
        and stage_b.get("activation_called") is False
        and stage_b.get("nonce_consumed") is True
        and stage_b.get("total_field_decision") == "NOT_RUN",
        "REJECT",
        "REJECT_GENESIS_STAGE_B_BOUNDARY_INVALID",
    )
    false_fields = (
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
        all(stage_b.get(field) is False for field in false_fields)
        and type(stage_b.get("receiver_call_count")) is int
        and stage_b.get("receiver_call_count") == 0
        and type(stage_b.get("authority_version")) is int
        and stage_b.get("authority_version") == 1
        and stage_b.get("authority_scope") == _AUTHORITY_SCOPE
        and stage_b.get("registry_coordinate") == _REGISTRY_COORDINATE,
        "REJECT",
        "REJECT_GENESIS_STAGE_B_BOUNDARY_INVALID",
    )
    supplied_self_hash = stage_b.get("sealed_candidate_sha256")
    _require(
        isinstance(supplied_self_hash, str)
        and _SHA256.fullmatch(supplied_self_hash) is not None
        and supplied_self_hash == _self_hash(stage_b, "sealed_candidate_sha256"),
        "REJECT",
        "REJECT_GENESIS_STAGE_B_SELF_HASH_MISMATCH",
    )
    _require(
        stage_b.get("authority_record_path") == ACTIVE_AUTHORITY_REL.as_posix()
        and isinstance(stage_b.get("authority_id"), str)
        and _HASH_REF.fullmatch(str(stage_b["authority_id"])) is not None,
        "REJECT",
        "REJECT_GENESIS_STAGE_B_POINTER_BINDING_INVALID",
    )
    for field in (
        "proposal_sha256",
        "founder_signature_sha256",
        "owner_seal_sha256",
        "revocation_sha256",
    ):
        _require(
            isinstance(stage_b.get(field), str)
            and _SHA256.fullmatch(str(stage_b[field])) is not None,
            "REJECT",
            "REJECT_GENESIS_STAGE_B_SEAL_BINDING_INVALID",
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
        _require(
            isinstance(stage_b.get(field), str)
            and _HASH_REF.fullmatch(str(stage_b[field])) is not None,
            "REJECT",
            "REJECT_GENESIS_STAGE_B_IDENTITY_BINDING_INVALID",
        )
    _require(
        isinstance(stage_b.get("evidence_bundle_sha256"), str)
        and _SHA256.fullmatch(str(stage_b["evidence_bundle_sha256"])) is not None
        and isinstance(stage_b.get("proposal_ref"), str)
        and stage_b.get("proposal_ref")
        == f"genesis_proposal_ref:sha256:{stage_b['proposal_sha256']}"
        and isinstance(stage_b.get("nonce"), str)
        and _NONCE_REF.fullmatch(str(stage_b["nonce"])) is not None
        and isinstance(stage_b.get("verifier_ref"), str)
        and _VERIFIER_REF.fullmatch(str(stage_b["verifier_ref"])) is not None,
        "REJECT",
        "REJECT_GENESIS_STAGE_B_EVIDENCE_BINDING_INVALID",
    )
    evidence_refs = stage_b.get("evidence_refs")
    _require(
        isinstance(evidence_refs, Mapping)
        and set(evidence_refs)
        == {
            "founder_identity_binding_receipt_ref",
            "8d_adi_binding_evidence_ref",
            "current_root_registry_cardinality_evidence_ref",
        }
        and all(
            isinstance(value, str) and _HASH_REF.fullmatch(value) is not None
            for value in evidence_refs.values()
        ),
        "REJECT",
        "REJECT_GENESIS_STAGE_B_EVIDENCE_BINDING_INVALID",
    )
    capability = stage_b.get("activation_capability")
    _require(
        isinstance(capability, Mapping)
        and capability.get("capability_id")
        == "W7TP_TOTAL_FIELD_GENESIS_ATOMIC_ACTIVATION_V1"
        and capability.get("target") == ACTIVE_AUTHORITY_REL.as_posix()
        and capability.get("single_use") is True
        and capability.get("atomic_create_if_absent") is True
        and capability.get("persistent_nonce_required") is True
        and capability.get("permanent_self_stop_after_success") is True
        and capability.get("call_forbidden_in_candidate_build") is True
        and capability.get("implementation")
        == "INJECTED_SINGLE_USE_ATOMIC_AUTHORITY_STORE",
        "REJECT",
        "REJECT_GENESIS_STAGE_B_CAPABILITY_INVALID",
    )
    current = now.astimezone(timezone.utc)
    issued = _parse_utc(stage_b.get("issued_at"), "HOLD_GENESIS_STAGE_B_TIME_INVALID")
    expires = _parse_utc(stage_b.get("expires_at"), "HOLD_GENESIS_STAGE_B_TIME_INVALID")
    _require(issued <= current < expires, "HOLD", "HOLD_GENESIS_STAGE_B_EXPIRED")
    return stage_b


def _validate_revocation_status(
    status: Any,
    *,
    stage_b: Mapping[str, Any],
    stage_b_document_sha256: str,
    now: datetime,
    governance_verifier: TrustedStageCGovernanceVerifier,
) -> None:
    _require(
        isinstance(status, Mapping),
        "HOLD",
        "HOLD_GENESIS_REVOCATION_STATUS_MISSING",
    )
    assert isinstance(status, Mapping)
    _require(
        status.get("schema_id") == REVOCATION_STATUS_SCHEMA_ID
        and status.get("authority_id") == stage_b.get("authority_id")
        and status.get("stage_b_document_sha256") == stage_b_document_sha256
        and status.get("verified") is True,
        "HOLD",
        "HOLD_GENESIS_REVOCATION_STATUS_UNVERIFIED",
    )
    _require(
        isinstance(status.get("verifier_ref"), str)
        and _VERIFIER_REF.fullmatch(str(status["verifier_ref"])) is not None
        and isinstance(status.get("evidence_sha256"), str)
        and _SHA256.fullmatch(str(status["evidence_sha256"])) is not None
        and isinstance(status.get("verification_receipt_ref"), str)
        and _HASH_REF.fullmatch(str(status["verification_receipt_ref"])) is not None,
        "HOLD",
        "HOLD_GENESIS_REVOCATION_STATUS_UNVERIFIED",
    )
    try:
        verifier_trusted = governance_verifier.trusted_runtime_verifier
        verified = governance_verifier.verify_revocation_status(status)
    except Exception as exc:
        raise StageCError(
            "HOLD", "HOLD_STAGE_C_GOVERNANCE_VERIFIER_FAILED"
        ) from exc
    _require(
        verifier_trusted is True and isinstance(verified, bool) and verified,
        "HOLD",
        "HOLD_GENESIS_REVOCATION_STATUS_UNVERIFIED",
    )
    _require(
        status.get("state") != "REVOKED",
        "BLOCK",
        "BLOCK_GENESIS_STAGE_B_REVOKED",
    )
    _require(
        status.get("state") == "NOT_REVOKED",
        "HOLD",
        "HOLD_GENESIS_REVOCATION_STATUS_UNKNOWN",
    )
    checked_at = _parse_utc(
        status.get("checked_at"), "HOLD_GENESIS_REVOCATION_STATUS_TIME_INVALID"
    )
    expires_at = _parse_utc(
        status.get("expires_at"), "HOLD_GENESIS_REVOCATION_STATUS_TIME_INVALID"
    )
    current = now.astimezone(timezone.utc)
    _require(
        checked_at <= current < expires_at,
        "HOLD",
        "HOLD_GENESIS_REVOCATION_STATUS_EXPIRED",
    )


def _validate_formal_authorization(
    authorization: Any,
    *,
    stage_b: Mapping[str, Any],
    stage_b_document_sha256: str,
    node_id: str,
    head: str,
    now: datetime,
    governance_verifier: TrustedStageCGovernanceVerifier,
) -> Mapping[str, Any]:
    _require(
        isinstance(authorization, Mapping),
        "HOLD",
        "HOLD_FOUNDER_FORMAL_ACTIVATION_AUTHORIZATION_ABSENT",
    )
    assert isinstance(authorization, Mapping)
    supplied_hash = authorization.get("authorization_sha256")
    _require(
        authorization.get("schema_id") == FORMAL_AUTHORIZATION_SCHEMA_ID
        and authorization.get("authorized_effect") == FORMAL_ACTIVATION_EFFECT
        and authorization.get("target_node") == node_id
        and authorization.get("target_head") == head
        and authorization.get("authority_id") == stage_b.get("authority_id")
        and authorization.get("stage_b_document_sha256")
        == stage_b_document_sha256
        and authorization.get("authority_pointer") == ACTIVE_AUTHORITY_REL.as_posix()
        and authorization.get("single_use") is True
        and isinstance(supplied_hash, str)
        and supplied_hash == _self_hash(authorization, "authorization_sha256"),
        "REJECT",
        "REJECT_FOUNDER_FORMAL_ACTIVATION_AUTHORIZATION_INVALID",
    )
    _require(
        isinstance(authorization.get("verifier_ref"), str)
        and _VERIFIER_REF.fullmatch(str(authorization["verifier_ref"])) is not None
        and isinstance(authorization.get("signer_identity_root_ref"), str)
        and _HASH_REF.fullmatch(str(authorization["signer_identity_root_ref"]))
        is not None
        and isinstance(authorization.get("signer_role_seat_ref"), str)
        and _HASH_REF.fullmatch(str(authorization["signer_role_seat_ref"])) is not None
        and isinstance(authorization.get("signature_sha256"), str)
        and _SHA256.fullmatch(str(authorization["signature_sha256"])) is not None,
        "REJECT",
        "REJECT_FOUNDER_FORMAL_ACTIVATION_AUTHORIZATION_INVALID",
    )
    try:
        verifier_trusted = governance_verifier.trusted_runtime_verifier
        verified = governance_verifier.verify_formal_authorization(authorization)
    except Exception as exc:
        raise StageCError(
            "HOLD", "HOLD_STAGE_C_GOVERNANCE_VERIFIER_FAILED"
        ) from exc
    _require(
        verifier_trusted is True and isinstance(verified, bool) and verified,
        "REJECT",
        "REJECT_FOUNDER_FORMAL_ACTIVATION_AUTHORIZATION_INVALID",
    )
    issued = _parse_utc(
        authorization.get("issued_at"),
        "HOLD_FOUNDER_FORMAL_ACTIVATION_AUTHORIZATION_TIME_INVALID",
    )
    expires = _parse_utc(
        authorization.get("expires_at"),
        "HOLD_FOUNDER_FORMAL_ACTIVATION_AUTHORIZATION_TIME_INVALID",
    )
    current = now.astimezone(timezone.utc)
    _require(
        issued <= current < expires,
        "HOLD",
        "HOLD_FOUNDER_FORMAL_ACTIVATION_AUTHORIZATION_EXPIRED",
    )
    return authorization


def prepare_stage_c_candidate(
    *,
    stage_b: Mapping[str, Any] | None,
    stage_b_document_sha256: str,
    revocation_status: Mapping[str, Any] | None,
    founder_activation_authorization: Mapping[str, Any] | None,
    governance_verifier: TrustedStageCGovernanceVerifier,
    current_build_effect: str,
    node_id: str,
    head: str,
    active_pointer_exists: bool,
    now: datetime,
) -> dict[str, Any]:
    """Return a validated candidate plan; do not mutate any state."""

    try:
        _require(node_id == TARGET_NODE, "BLOCK", "BLOCK_TARGET_NODE_NOT_TAIJI01")
        _require(head == TARGET_HEAD, "HOLD", "HOLD_TAIJI01_HEAD_MISMATCH")
        _require(
            not active_pointer_exists,
            "BLOCK",
            "BLOCK_ACTIVE_TOTAL_FIELD_AUTHORITY_ALREADY_EXISTS",
        )
        _require(
            current_build_effect == BUILD_ONLY_EFFECT,
            "BLOCK",
            "BLOCK_STAGE_C_BUILD_AUTHORIZATION_INVALID",
        )
        stage_b_value = _validate_stage_b(stage_b, stage_b_document_sha256, now)
        _validate_revocation_status(
            revocation_status,
            stage_b=stage_b_value,
            stage_b_document_sha256=stage_b_document_sha256,
            now=now,
            governance_verifier=governance_verifier,
        )
        formal = _validate_formal_authorization(
            founder_activation_authorization,
            stage_b=stage_b_value,
            stage_b_document_sha256=stage_b_document_sha256,
            node_id=node_id,
            head=head,
            now=now,
            governance_verifier=governance_verifier,
        )
        plan: dict[str, Any] = {
            "schema_id": SCHEMA_ID,
            "stage": "C_GENESIS_ACTIVATION_READY",
            "state": "C_GENESIS_ACTIVATION_READY",
            "contract_state": "CANDIDATE_ONLY",
            "candidate_only": True,
            "authority_granted": False,
            "active_authority_created": False,
            "formal_activation_performed": False,
            "live_pointer_written": False,
            "real_nonce_consumed": False,
            "total_field_decision": "NOT_RUN",
            "target_node": node_id,
            "target_head": head,
            "authority_pointer": ACTIVE_AUTHORITY_REL.as_posix(),
            "authority_id": stage_b_value["authority_id"],
            "stage_b_document_sha256": stage_b_document_sha256,
            "stage_b_self_sha256": stage_b_value["sealed_candidate_sha256"],
            "formal_authorization_sha256": formal["authorization_sha256"],
            "formal_activation_effect": FORMAL_ACTIVATION_EFFECT,
            "transaction_model": "RECEIPT_FIRST_CAPSULE_THEN_CREATE_IF_ABSENT_LINK",
            "replay_policy": "EXISTING_POINTER_OR_USED_SINGLE_USE_ID_BLOCKS",
            "crash_policy": "NO_POINTER_BEFORE_DURABLE_RECEIPT_CAPSULE",
            "recovery_policy": "VERIFY_OR_QUARANTINE_TRANSACTION_CAPSULE",
        }
        plan["plan_sha256"] = _self_hash(plan, "plan_sha256")
        return plan
    except StageCError as exc:
        return _failure(exc.state, exc.reason_code)
    except (TypeError, ValueError, OverflowError):
        return _failure("HOLD", "HOLD_GENESIS_STAGE_C_INPUT_INVALID")


def _write_json_fsync(path: Path, value: Mapping[str, Any]) -> None:
    encoded = (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, encoded)
        os.fsync(fd)
    finally:
        os.close(fd)


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def simulate_atomic_activation(
    *,
    plan: Mapping[str, Any],
    simulation_root: Path,
    explicit_simulation: bool,
    fault: str | None = None,
) -> dict[str, Any]:
    """Exercise atomic ordering only inside an explicit disposable sandbox."""

    try:
        root = Path(simulation_root).resolve()
        live_root = Path(__file__).resolve().parents[2]
        _require(explicit_simulation is True, "BLOCK", "BLOCK_SIMULATION_GUARD_ABSENT")
        _require(root != live_root, "BLOCK", "BLOCK_LIVE_REPOSITORY_SIMULATION")
        _require(
            plan.get("state") == "C_GENESIS_ACTIVATION_READY"
            and plan.get("candidate_only") is True
            and plan.get("formal_activation_performed") is False,
            "HOLD",
            "HOLD_STAGE_C_PLAN_NOT_READY",
        )
        _require(
            plan.get("plan_sha256") == _self_hash(plan, "plan_sha256"),
            "REJECT",
            "REJECT_STAGE_C_PLAN_HASH_MISMATCH",
        )
        target = root / ACTIVE_AUTHORITY_REL
        _require(
            not target.exists() and not target.is_symlink(),
            "BLOCK",
            "BLOCK_ACTIVE_TOTAL_FIELD_AUTHORITY_ALREADY_EXISTS",
        )
        transaction_id = canonical_sha256(
            {
                "plan_sha256": plan["plan_sha256"],
                "authorization_sha256": plan["formal_authorization_sha256"],
            }
        )
        tx_root = root / "stage_c_transactions"
        staging = tx_root / f".precommit-{transaction_id}"
        committed = tx_root / transaction_id
        quarantine = tx_root / f"quarantine-{transaction_id}"
        tx_root.mkdir(parents=True, exist_ok=True)
        _require(
            not staging.exists() and not committed.exists() and not quarantine.exists(),
            "BLOCK",
            "BLOCK_GENESIS_ACTIVATION_REPLAY",
        )
        staging.mkdir()
        authority = {
            "schema_id": "W7TP_ACTIVE_TOTAL_FIELD_AUTHORITY_CANDIDATE_V1",
            "state": "SIMULATED_ACTIVE_TOTAL_FIELD_AUTHORITY_CANDIDATE",
            "contract_state": "CANDIDATE_ONLY",
            "candidate_only": True,
            "authority_granted": False,
            "formal_decision_authority": False,
            "formal_seal_authority": False,
            "live_runtime_authority": False,
            "simulation_only": True,
            "target_node": plan["target_node"],
            "target_head": plan["target_head"],
            "authority_id": plan["authority_id"],
            "stage_b_document_sha256": plan["stage_b_document_sha256"],
            "formal_authorization_sha256": plan["formal_authorization_sha256"],
            "intended_post_activation_state": "ACTIVE_TOTAL_FIELD_AUTHORITY",
            "intended_formal_decision_authority": True,
            "intended_formal_seal_authority": True,
        }
        authority["candidate_sha256"] = _self_hash(authority, "candidate_sha256")
        receipt = {
            "schema_id": RECEIPT_SCHEMA_ID,
            "state": "SIMULATED_ATOMIC_ACTIVATION",
            "candidate_only": True,
            "formal_activation_performed": False,
            "live_pointer_written": False,
            "real_nonce_consumed": False,
            "total_field_decision": "NOT_RUN",
            "transaction_id": transaction_id,
            "plan_sha256": plan["plan_sha256"],
            "candidate_sha256": authority["candidate_sha256"],
            "pointer": ACTIVE_AUTHORITY_REL.as_posix(),
            "atomic_order": [
                "WRITE_CANDIDATE",
                "WRITE_RECEIPT",
                "FSYNC_CAPSULE",
                "COMMIT_CAPSULE",
                "CREATE_POINTER_IF_ABSENT",
            ],
        }
        receipt["receipt_sha256"] = _self_hash(receipt, "receipt_sha256")
        try:
            _write_json_fsync(staging / "AUTHORITY_CANDIDATE.json", authority)
            if fault == "receipt_failure":
                raise OSError("injected receipt failure")
            _write_json_fsync(staging / "ACTIVATION_RECEIPT_CANDIDATE.json", receipt)
            _fsync_dir(staging)
            if fault == "before_commit":
                raise SimulatedCrash("injected crash before transaction commit")
            os.replace(staging, committed)
            _fsync_dir(tx_root)
            if fault == "mid_commit":
                raise SimulatedCrash("injected crash after capsule commit, before pointer")
            target.parent.mkdir(parents=True, exist_ok=True)
            os.link(committed / "AUTHORITY_CANDIDATE.json", target)
            _fsync_dir(target.parent)
        except OSError as exc:
            if staging.exists() and not quarantine.exists():
                os.replace(staging, quarantine)
                _fsync_dir(tx_root)
            elif committed.exists() and not quarantine.exists():
                os.replace(committed, quarantine)
                _fsync_dir(tx_root)
            raise StageCError(
                "QUARANTINE", "QUARANTINE_GENESIS_ACTIVATION_RECEIPT_OR_COMMIT_FAILURE"
            ) from exc
        return receipt
    except StageCError as exc:
        return _failure(exc.state, exc.reason_code)


__all__ = [
    "ACTIVE_AUTHORITY_REL",
    "BUILD_ONLY_EFFECT",
    "FORMAL_ACTIVATION_EFFECT",
    "FORMAL_AUTHORIZATION_SCHEMA_ID",
    "RECEIPT_SCHEMA_ID",
    "REVOCATION_STATUS_SCHEMA_ID",
    "SCHEMA_ID",
    "SimulatedCrash",
    "TARGET_HEAD",
    "TARGET_NODE",
    "TrustedStageCGovernanceVerifier",
    "canonical_sha256",
    "prepare_stage_c_candidate",
    "simulate_atomic_activation",
]
