"""Total Field-only D8 task envelopes using the established Ed25519 verifier."""

from __future__ import annotations

import copy
import hmac
import re
import secrets
from datetime import UTC, datetime
from typing import Mapping, Protocol

from w7tp_gt_mesh.core import (
    CANONICAL_ID,
    CANONICAL_SHA256,
    DIMENSIONS,
    MeshHold,
    require_core,
)

from .human_view import render_task_envelope_zh_tw


TOTAL_FIELD_AUTHORITY = "authority:TOTAL_FIELD"
DESIGN_AUTHORITY = "FOUNDER_ARCHITECTURE"
PRIMARY_DECISION_ENGINE = "8D_ADI"
CONTROL_AUTHORITY_NODE_ID = "taiji01"
TASK_SCHEMA = "W7TP_TOTAL_FIELD_CONTROL_TASK_CANDIDATE_V1"
TASK_NAMESPACE = "w7tp.total_field.control.task.v1"
AUTH_ALGORITHM = "Ed25519"
MAX_TTL_SECONDS = 900
REQUIRED_CONTROL_SCOPES = frozenset(
    {"CROSS_NODE_CONTROL", "HARDWARE_SCHEDULE", "EXECUTE_CANARY"}
)
MANAGE_EXISTING_CONTAINER_SCOPE = "MANAGE_EXISTING_CONTAINER"
_EXISTING_CONTAINER_OPERATIONS = frozenset(
    {
        "container_inspect_existing",
        "container_start_existing",
        "container_stop_existing",
        "container_remove_existing",
    }
)

_NONCE = re.compile(r"^[0-9a-f]{32,128}$")
_VERIFIER_REF = re.compile(r"^verifier_ref:[A-Za-z0-9][A-Za-z0-9_.:/-]{0,191}$")


class DetachedSigner(Protocol):
    def sign_detached(self, *, verifier_ref: str, payload_sha256: str) -> str: ...


class DetachedVerifier(Protocol):
    def verify_detached(self, *, verifier_ref: str, payload_sha256: str, signature: str) -> bool: ...


def _canonical(value: object) -> bytes:
    return require_core().canonical_json_bytes(value)


def _hash(value: object) -> str:
    return require_core().sha256_hex(_canonical(value))


def _signature_projection(envelope: Mapping[str, object]) -> dict[str, object]:
    projected = copy.deepcopy(dict(envelope))
    projected.pop("envelope_sha256", None)
    dimensions = projected.get("dimensions")
    if isinstance(dimensions, dict):
        d8 = dimensions.get("D8_ENVELOPE_VERIFICATION")
        if isinstance(d8, dict):
            d8.pop("payload_sha256", None)
            d8.pop("signature", None)
    return projected


def _parse_utc(value: object, code: str) -> datetime:
    if not isinstance(value, str):
        raise MeshHold(code)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MeshHold(code) from exc
    if parsed.tzinfo is None:
        raise MeshHold(code)
    return parsed.astimezone(UTC)


def authority_artifact_sha256(authority: Mapping[str, object]) -> str:
    return _hash(authority)


def seal_task_envelope(
    envelope: Mapping[str, object],
    *,
    signer: DetachedSigner,
) -> dict[str, object]:
    """Ask the injected Total Field signer to seal a digest; no key is handled here."""

    sealed = copy.deepcopy(dict(envelope))
    dimensions = sealed.get("dimensions")
    if not isinstance(dimensions, dict):
        raise MeshHold("HOLD_TASK_DIMENSIONS_INVALID")
    d8 = dimensions.get("D8_ENVELOPE_VERIFICATION")
    if not isinstance(d8, dict) or not isinstance(d8.get("verifier_ref"), str):
        raise MeshHold("HOLD_TASK_D8_INVALID")
    payload_sha256 = _hash(_signature_projection(sealed))
    signature = signer.sign_detached(
        verifier_ref=str(d8["verifier_ref"]),
        payload_sha256=payload_sha256,
    )
    if not isinstance(signature, str) or not signature:
        raise MeshHold("HOLD_TOTAL_FIELD_SIGNATURE_INVALID")
    d8["payload_sha256"] = payload_sha256
    d8["signature"] = signature
    sealed["envelope_sha256"] = _hash(
        {key: value for key, value in sealed.items() if key != "envelope_sha256"}
    )
    return sealed


def build_task_envelope(
    *,
    task_id: str,
    intent: str,
    target_node_id: str,
    selected_snapshot_sha256: str,
    operation: str,
    parameters: Mapping[str, object],
    resource_request: Mapping[str, object],
    node_manifest: Mapping[str, object],
    node_resource_state: Mapping[str, object],
    execution_lease: Mapping[str, object],
    logical_time: int,
    issued_at_epoch: int,
    ttl_seconds: int,
    verifier_ref: str,
    signer: DetachedSigner,
    active_authority: Mapping[str, object],
    authority_profile: Mapping[str, object],
    evidence_refs: list[str] | None = None,
    nonce: str | None = None,
) -> dict[str, object]:
    """Build the candidate 8D task artifact; the existing mesh remains its carrier."""

    if not isinstance(task_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", task_id):
        raise MeshHold("HOLD_TASK_ID_INVALID")
    if not isinstance(intent, str) or not intent or len(intent) > 512:
        raise MeshHold("HOLD_TASK_INTENT_INVALID")
    if not isinstance(target_node_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", target_node_id):
        raise MeshHold("HOLD_TASK_TARGET_INVALID")
    if not isinstance(selected_snapshot_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", selected_snapshot_sha256):
        raise MeshHold("HOLD_TASK_SNAPSHOT_HASH_INVALID")
    if isinstance(logical_time, bool) or not isinstance(logical_time, int) or logical_time < 1:
        raise MeshHold("HOLD_TASK_LOGICAL_TIME_INVALID")
    if isinstance(issued_at_epoch, bool) or not isinstance(issued_at_epoch, int) or issued_at_epoch < 0:
        raise MeshHold("HOLD_TASK_ISSUED_TIME_INVALID")
    if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int) or not 1 <= ttl_seconds <= MAX_TTL_SECONDS:
        raise MeshHold("HOLD_TASK_TTL_INVALID")
    if not isinstance(verifier_ref, str) or not _VERIFIER_REF.fullmatch(verifier_ref):
        raise MeshHold("HOLD_TOTAL_FIELD_VERIFIER_REF_INVALID")
    if (
        not isinstance(node_manifest, Mapping)
        or not isinstance(node_resource_state, Mapping)
        or not isinstance(execution_lease, Mapping)
        or node_manifest.get("node_id") != target_node_id
        or node_resource_state.get("node_id") != target_node_id
        or execution_lease.get("node_id") != target_node_id
        or execution_lease.get("state") != "ISSUED"
        or execution_lease.get("issuer_node_id") != CONTROL_AUTHORITY_NODE_ID
    ):
        raise MeshHold("HOLD_EXECUTION_LEASE_BINDING_INVALID")
    nonce_value = nonce or secrets.token_hex(16)
    if not _NONCE.fullmatch(nonce_value):
        raise MeshHold("HOLD_TASK_NONCE_INVALID")
    evidence = evidence_refs or []
    if not isinstance(evidence, list) or not all(isinstance(item, str) and item for item in evidence):
        raise MeshHold("HOLD_TASK_EVIDENCE_REFS_INVALID")
    authority_ref = active_authority.get("authority_id")
    if not isinstance(authority_ref, str) or not authority_ref:
        raise MeshHold("HOLD_ACTIVE_TOTAL_FIELD_AUTHORITY_ID_INVALID")
    required_scopes = set(REQUIRED_CONTROL_SCOPES)
    if operation in _EXISTING_CONTAINER_OPERATIONS:
        required_scopes.add(MANAGE_EXISTING_CONTAINER_SCOPE)
    envelope: dict[str, object] = {
        "schema_id": TASK_SCHEMA,
        "candidate_state": "CANDIDATE_NOT_CANONICAL_NOT_PROMOTED",
        "canonical_binding": {
            "canonical_id": CANONICAL_ID,
            "canonical_sha256": CANONICAL_SHA256,
            "relationship": "MINIMAL_CONTROL_PROFILE_EXTENSION_NOT_REPLACEMENT",
        },
        "task_id": task_id,
        "namespace": TASK_NAMESPACE,
        "logical_time": logical_time,
        "nonce": nonce_value,
        "issued_at_epoch": issued_at_epoch,
        "expires_at_epoch": issued_at_epoch + ttl_seconds,
        "dimensions": {
            "D1_INTENT": {
                "intent": intent,
                "desired_outcome": "BOUNDED_TOTAL_FIELD_AUTHORIZED_NODE_ACTION",
            },
            "D2_STATE": {
                "resource_request": dict(resource_request),
                "precondition_state": "RESOURCE_RESERVATION_REQUIRED",
                "node_resource_state": dict(node_resource_state),
                "execution_lease": dict(execution_lease),
            },
            "D3_COORDINATE": {
                "target_node_id": target_node_id,
                "selected_snapshot_sha256": selected_snapshot_sha256,
                "node_manifest": dict(node_manifest),
                "control_authority_node_id": CONTROL_AUTHORITY_NODE_ID,
            },
            "D4_EVIDENCE": {
                "evidence_refs": list(evidence),
                "snapshot_sha256": selected_snapshot_sha256,
                "active_authority_sha256": authority_artifact_sha256(active_authority),
                "authority_profile_sha256": authority_artifact_sha256(authority_profile),
                "git_authority_effect": "NONE",
            },
            "D5_EXECUTION": {
                "operation": operation,
                "parameters": dict(parameters),
                "phases": ["RESERVE", "EXECUTE", "VERIFY"],
            },
            "D6_GENERATIVE_TRANSMISSION": {
                "carrier": "EXISTING_W7TP_GT_MESH_V21_ONLY",
                "new_parallel_transport": False,
            },
            "D7_RISK_QUARANTINE": {
                "default_policy": "DEDICATED_W7TP_CANARY_ONLY",
                "existing_production_services_mutable": False,
                "failure_mode": "FAIL_CLOSED",
            },
            "D8_ENVELOPE_VERIFICATION": {
                "authority_ref": TOTAL_FIELD_AUTHORITY,
                "active_authority_id": authority_ref,
                "control_authority_node_id": CONTROL_AUTHORITY_NODE_ID,
                "issuer": "TOTAL_FIELD",
                "design_authority": DESIGN_AUTHORITY,
                "primary_decision_engine": PRIMARY_DECISION_ENGINE,
                "required_scopes": sorted(required_scopes),
                "verifier_ref": verifier_ref,
                "algorithm": AUTH_ALGORITHM,
                "payload_sha256": "",
                "signature": "",
            },
        },
    }
    envelope["human_summary_zh_tw"] = render_task_envelope_zh_tw(envelope)
    return seal_task_envelope(envelope, signer=signer)


def _verify_active_authority(
    envelope: Mapping[str, object],
    *,
    active_authority: Mapping[str, object],
    authority_profile: Mapping[str, object],
    now: datetime,
) -> None:
    dimensions = envelope["dimensions"]
    assert isinstance(dimensions, Mapping)
    d4 = dimensions["D4_EVIDENCE"]
    d8 = dimensions["D8_ENVELOPE_VERIFICATION"]
    assert isinstance(d4, Mapping) and isinstance(d8, Mapping)
    if d4.get("active_authority_sha256") != authority_artifact_sha256(active_authority):
        raise MeshHold("HOLD_ACTIVE_TOTAL_FIELD_AUTHORITY_HASH_MISMATCH")
    if d4.get("authority_profile_sha256") != authority_artifact_sha256(authority_profile):
        raise MeshHold("HOLD_TOTAL_FIELD_AUTHORITY_PROFILE_HASH_MISMATCH")
    if active_authority.get("active") is not True or active_authority.get("state") != "ACTIVE":
        raise MeshHold("HOLD_ACTIVE_TOTAL_FIELD_AUTHORITY_INACTIVE")
    if active_authority.get("authority_id") != d8.get("active_authority_id"):
        raise MeshHold("HOLD_ACTIVE_TOTAL_FIELD_AUTHORITY_ID_MISMATCH")
    required_scopes = d8.get("required_scopes")
    allowed_scope_sets = {
        REQUIRED_CONTROL_SCOPES,
        REQUIRED_CONTROL_SCOPES | {MANAGE_EXISTING_CONTAINER_SCOPE},
    }
    if not isinstance(required_scopes, list) or frozenset(required_scopes) not in allowed_scope_sets:
        raise MeshHold("HOLD_TOTAL_FIELD_CONTROL_SCOPE_BINDING_INVALID")
    scopes = active_authority.get("authority_scope")
    if not isinstance(scopes, list) or frozenset(scopes) != frozenset(required_scopes):
        raise MeshHold("HOLD_TOTAL_FIELD_CONTROL_SCOPE_MISSING_OR_EXPANDED")
    issued = _parse_utc(active_authority.get("issued_at"), "HOLD_ACTIVE_TOTAL_FIELD_AUTHORITY_TIME_INVALID")
    expires = _parse_utc(active_authority.get("expires_at"), "HOLD_ACTIVE_TOTAL_FIELD_AUTHORITY_TIME_INVALID")
    if issued > now or now >= expires:
        raise MeshHold("HOLD_ACTIVE_TOTAL_FIELD_AUTHORITY_EXPIRED_OR_NOT_YET_VALID")
    if authority_profile.get("active") is not True:
        raise MeshHold("HOLD_TOTAL_FIELD_AUTHORITY_PROFILE_INACTIVE")
    boundary = authority_profile.get("authorization_boundary")
    node_binding = authority_profile.get("node_binding")
    signature_verifier = authority_profile.get("signature_verifier")
    if not isinstance(boundary, Mapping) or boundary.get("execution_authority") is not True:
        raise MeshHold("HOLD_TOTAL_FIELD_EXECUTION_AUTHORITY_DISABLED")
    if not isinstance(node_binding, Mapping) or node_binding.get("cross_node_authority_allowed") is not True:
        raise MeshHold("HOLD_TOTAL_FIELD_CROSS_NODE_AUTHORITY_DISABLED")
    if (
        node_binding.get("authority_runtime_owner") != CONTROL_AUTHORITY_NODE_ID
        or node_binding.get("ledger_owner_node") != CONTROL_AUTHORITY_NODE_ID
    ):
        raise MeshHold("HOLD_TOTAL_FIELD_CONTROL_AUTHORITY_NODE_INVALID")
    if (
        not isinstance(signature_verifier, Mapping)
        or signature_verifier.get("algorithm") != AUTH_ALGORITHM
        or signature_verifier.get("implementation") != "tools.total_field_ed25519_backend:Ed25519DetachedSignatureBackend"
    ):
        raise MeshHold("HOLD_TOTAL_FIELD_ED25519_BINDING_INVALID")
    refs = signature_verifier.get("trusted_verifier_refs")
    if not isinstance(refs, list) or d8.get("verifier_ref") not in refs:
        raise MeshHold("HOLD_TOTAL_FIELD_VERIFIER_REF_UNTRUSTED")


def verify_task_envelope(
    envelope: Mapping[str, object],
    *,
    signature_verifier: DetachedVerifier,
    active_authority: Mapping[str, object],
    authority_profile: Mapping[str, object],
    now_epoch: int,
) -> dict[str, object]:
    """Fail closed on current authority, scopes, TTL, hash and Ed25519 proof."""

    if not isinstance(envelope, Mapping) or envelope.get("schema_id") != TASK_SCHEMA:
        raise MeshHold("HOLD_TASK_SCHEMA_INVALID")
    if envelope.get("candidate_state") != "CANDIDATE_NOT_CANONICAL_NOT_PROMOTED":
        raise MeshHold("HOLD_TASK_CANDIDATE_STATE_INVALID")
    dimensions = envelope.get("dimensions")
    if not isinstance(dimensions, Mapping) or tuple(dimensions.keys()) != DIMENSIONS:
        raise MeshHold("HOLD_TASK_DIMENSIONS_INVALID")
    d8 = dimensions.get("D8_ENVELOPE_VERIFICATION")
    if not isinstance(d8, Mapping):
        raise MeshHold("HOLD_TASK_D8_INVALID")
    if d8.get("authority_ref") != TOTAL_FIELD_AUTHORITY or d8.get("issuer") != "TOTAL_FIELD":
        raise MeshHold("HOLD_TOTAL_FIELD_AUTHORITY_REQUIRED")
    if d8.get("control_authority_node_id") != CONTROL_AUTHORITY_NODE_ID:
        raise MeshHold("HOLD_TOTAL_FIELD_CONTROL_AUTHORITY_NODE_INVALID")
    if d8.get("primary_decision_engine") != PRIMARY_DECISION_ENGINE:
        raise MeshHold("HOLD_PRIMARY_DECISION_ENGINE_INVALID")
    if d8.get("design_authority") != DESIGN_AUTHORITY:
        raise MeshHold("HOLD_DESIGN_AUTHORITY_PROVENANCE_INVALID")
    allowed_scope_lists = {
        tuple(sorted(REQUIRED_CONTROL_SCOPES)),
        tuple(sorted(REQUIRED_CONTROL_SCOPES | {MANAGE_EXISTING_CONTAINER_SCOPE})),
    }
    required_scope_value = d8.get("required_scopes")
    if (
        d8.get("algorithm") != AUTH_ALGORITHM
        or not isinstance(required_scope_value, list)
        or tuple(required_scope_value) not in allowed_scope_lists
    ):
        raise MeshHold("HOLD_TOTAL_FIELD_CONTROL_SCOPE_BINDING_INVALID")
    binding = envelope.get("canonical_binding")
    if (
        not isinstance(binding, Mapping)
        or binding.get("canonical_id") != CANONICAL_ID
        or binding.get("canonical_sha256") != CANONICAL_SHA256
        or binding.get("relationship") != "MINIMAL_CONTROL_PROFILE_EXTENSION_NOT_REPLACEMENT"
    ):
        raise MeshHold("HOLD_CANONICAL_BINDING_INVALID")
    issued = envelope.get("issued_at_epoch")
    expires = envelope.get("expires_at_epoch")
    if (
        isinstance(issued, bool)
        or not isinstance(issued, int)
        or isinstance(expires, bool)
        or not isinstance(expires, int)
        or isinstance(now_epoch, bool)
        or not isinstance(now_epoch, int)
    ):
        raise MeshHold("HOLD_TASK_TIME_INVALID")
    if expires <= issued or expires - issued > MAX_TTL_SECONDS:
        raise MeshHold("HOLD_TASK_TTL_INVALID")
    if now_epoch < issued or now_epoch >= expires:
        raise MeshHold("HOLD_TASK_EXPIRED_OR_NOT_YET_VALID")
    nonce = envelope.get("nonce")
    logical_time = envelope.get("logical_time")
    if not isinstance(nonce, str) or not _NONCE.fullmatch(nonce):
        raise MeshHold("HOLD_TASK_NONCE_INVALID")
    if isinstance(logical_time, bool) or not isinstance(logical_time, int) or logical_time < 1:
        raise MeshHold("HOLD_TASK_LOGICAL_TIME_INVALID")
    expected_envelope_hash = envelope.get("envelope_sha256")
    actual_envelope_hash = _hash({key: value for key, value in envelope.items() if key != "envelope_sha256"})
    if not isinstance(expected_envelope_hash, str) or not hmac.compare_digest(expected_envelope_hash, actual_envelope_hash):
        raise MeshHold("HOLD_TASK_ENVELOPE_HASH_MISMATCH")
    payload_sha256 = d8.get("payload_sha256")
    if not isinstance(payload_sha256, str) or not hmac.compare_digest(payload_sha256, _hash(_signature_projection(envelope))):
        raise MeshHold("HOLD_TASK_PAYLOAD_HASH_MISMATCH")
    signature = d8.get("signature")
    verifier_ref = d8.get("verifier_ref")
    if not isinstance(signature, str) or not isinstance(verifier_ref, str):
        raise MeshHold("HOLD_TOTAL_FIELD_SIGNATURE_INVALID")
    now = datetime.fromtimestamp(now_epoch, tz=UTC)
    _verify_active_authority(
        envelope,
        active_authority=active_authority,
        authority_profile=authority_profile,
        now=now,
    )
    if not signature_verifier.verify_detached(
        verifier_ref=verifier_ref,
        payload_sha256=payload_sha256,
        signature=signature,
    ):
        raise MeshHold("HOLD_TOTAL_FIELD_SIGNATURE_INVALID")
    return copy.deepcopy(dict(envelope))
