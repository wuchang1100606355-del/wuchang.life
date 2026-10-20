from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Collection, Mapping, Protocol

ACTIVE_POINTER_REL = Path("runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json")
ARTIFACT_ROOT_REL = Path("runtime/total_field/authority_artifacts")
MAX_JSON_BYTES = 1_000_000
MAX_TTL_SECONDS = 300
RECEIVE_CANDIDATE_SCOPE = "RECEIVE_CANDIDATE"
POINTER_BOOTSTRAP_SCOPE = "BOOTSTRAP_CURRENT_ACTIVE_CANONICAL_POINTER"
PROMOTION_SCOPE = "PROMOTE_ACCEPTED_CANDIDATE"
STATE_CELL_PILOT_SCOPE = "RUN_READ_ONLY_STATE_CELL_PILOT"
GIT_PUSH_SCOPE = "AUTHORIZE_GIT_PUSH"
STATE_CELL_PILOT_ACTION = "RUN_READ_ONLY_STATE_CELL_INDEX_PROJECTION"
STATE_CELL_PILOT_NODE = "MSI"
STATE_CELL_PILOT_MAXIMUM_EFFECT = "IN_MEMORY_READ_ONLY_ONLY"
STATE_CELL_PILOT_FORBIDDEN_EFFECTS = frozenset(
    {
        "ACTIVE_POINTER_WRITE",
        "CANONICAL_POINTER_WRITE",
        "CLOUD_CALL",
        "DB_WRITE",
        "DEPLOY",
        "FILE_DELETE",
        "NETWORK_ROUTE_MUTATION",
        "OLD_VERSION_EXECUTION",
        "RESTART",
    }
)
STATE_CELL_PILOT_CONSTRAINT_FIELDS = frozenset(
    {
        "proposal_sha256",
        "red_team_receipt_sha256",
        "target_field_sha256",
        "carrier_capability_registry_sha256",
        "target_node",
        "object_id",
        "exact_coordinate",
        "authorized_action",
        "authorized_steps_sha256",
        "evidence_refs_sha256",
        "maximum_effect",
        "cell_budget",
        "relation_traversal_budget",
        "observation_budget",
        "forbidden_effects",
        "operation_nonce",
        "single_use_authorization_required",
        "replay_protected",
        "authority_signature_required",
        "db_write",
        "deploy",
        "restart",
        "network_route_mutation",
        "cloud_call",
        "file_delete",
        "canonical_pointer_write",
        "active_pointer_write",
        "old_version_target_import",
    }
)
GIT_PUSH_CONSTRAINT_FIELDS = frozenset(
    {
        "review_registration_ref",
        "review_registration_sha256",
        "base_commit",
        "target_tree",
        "branch",
        "remote_name",
        "remote_url_sha256",
        "allowed_paths_sha256",
        "single_commit_only",
        "formal_submission",
        "git_push",
        "deploy",
        "restart",
        "canonical_pointer_write",
        "active_pointer_write",
        "single_use_authorization_required",
        "replay_protected",
        "authority_signature_required",
    }
)
PROMOTION_SCOPE_CONSTRAINTS = {
    "total_field_decision": "ALLOW_CANDIDATE_ACCEPTED",
    "candidate_sha256": "066e39cd2abad3d4ed713e4f7ecb7f220d4651d9f7624f5b48d13c4781be7890",
    "promotion_mechanism_sha256": "6681cdd0ca6ee7c0133d5fe6eb0b77541a756d4bffad7451656d4b010ea8ebf9",
    "active_pointer_preimage_sha256": "d3ce26e27785400b7eb4eaacb6b522f1484e11c43e4416463f976865fda63b97",
    "current_canonical_sha256": "e960d14254df083ffed711e2c44b76fc2075541716881bc3d1034cb26cffbaba",
    "single_use_authorization_required": True,
    "replay_protected": True,
    "authority_signature_required": True,
    "append_only_promotion_receipt": True,
    "generic_canonical_write": False,
    "arbitrary_pointer_write": False,
    "deploy": False,
    "restart": False,
    "authority_management": False,
    "formal_submission": False,
    "other_candidate_promotion": False,
    "historical_mutation": False,
}
POINTER_BOOTSTRAP_SCOPE_CONSTRAINTS = {
    "target": "runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json",
    "operation": "CREATE_IF_ABSENT",
    "expected_preimage": "ABSENT",
    "bound_canonical_sha256": "e960d14254df083ffed711e2c44b76fc2075541716881bc3d1034cb26cffbaba",
    "fail_if_already_exists": True,
    "overwrite": False,
    "replay_protected": True,
    "single_use_authorization_required": True,
    "authority_signature_required": True,
    "promotion": False,
    "activation": False,
    "generic_canonical_write": False,
    "deploy": False,
    "restart": False,
    "authority_management": False,
}
SCOPE_OWNER_AUTHORIZATIONS = {
    RECEIVE_CANDIDATE_SCOPE: "FOUNDER_APPROVED_RECEIVE_CANDIDATE",
    POINTER_BOOTSTRAP_SCOPE: "FOUNDER_APPROVED_CURRENT_ACTIVE_CANONICAL_POINTER_BOOTSTRAP",
    PROMOTION_SCOPE: "FOUNDER_APPROVED_PROMOTE_ACCEPTED_CANDIDATE",
    STATE_CELL_PILOT_SCOPE: "FOUNDER_APPROVED_RUN_READ_ONLY_STATE_CELL_PILOT",
    GIT_PUSH_SCOPE: "FOUNDER_APPROVED_EXACT_GIT_PUSH",
}
DISALLOWED_PATH_PARTS = {
    "archive",
    "candidate",
    "candidates",
    "candidate_specs",
    "held",
    "optimized_successor_candidate",
    "quarantine",
    "review_archive",
}
NONCE_REF = re.compile(r"^nonce_ref:sha256:[0-9a-f]{64}$")
OPAQUE_REF = re.compile(r"^[A-Za-z0-9_.:-]{8,256}$")


class PersistentNonceLedger(Protocol):
    persistent: bool

    def mark_used_or_replay(
        self,
        nonce: str,
        packet_hash: str,
        now_epoch: float,
        ttl_seconds: int,
    ) -> bool:
        """Return True only for the first accepted use; False means replay."""


class TrustedSignatureVerifier(Protocol):
    trusted_runtime_verifier: bool

    def verify(
        self,
        *,
        verifier_ref: str,
        payload_sha256: str,
        signature: str,
    ) -> bool:
        """Verify one detached signature without exposing verifier secrets."""


class ResolverError(Exception):
    def __init__(self, state: str, reason: str) -> None:
        super().__init__(reason)
        self.state = state
        self.reason = reason


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _result(
    state: str,
    reason: str,
    *,
    authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    verified = state == "PASS_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVED"
    output: dict[str, Any] = {
        "state": state,
        "reason": reason,
        "authority_verified": verified,
        "candidate_authority": False,
        "execution_authorized": False,
        "formal_decision_authority": False,
        "formal_seal_authority": False,
        "db_write_authorized": False,
        "deploy_authorized": False,
        "restart_authorized": False,
        "formal_send_authorized": False,
    }
    if verified and authority is not None:
        output.update(
            {
                "authority_id": authority["authority_id"],
                "authority_version": authority["authority_version"],
                "founder_person_packet_ref": authority["founder_person_packet_ref"],
                "registered_device_ref": authority["registered_device_ref"],
                "founder_capability_assignment_ref": authority[
                    "founder_capability_assignment_ref"
                ],
                "access_profile_ref": authority["access_profile_ref"],
                "authority_scope": list(authority["authority_scope"]),
                "scope": list(authority["authority_scope"]),
                "authority_scope_constraints": dict(
                    authority.get("authority_scope_constraints") or {}
                ),
                "authority_sha256": authority["_authority_file_sha256"],
                "expires_at": authority["expires_at"],
                "verifier_ref": authority["verifier_ref"],
            }
        )
    return output


def _parse_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ResolverError("HOLD_AUTHORITY_INCOMPLETE", f"{field} is missing")
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ResolverError(
            "HOLD_AUTHORITY_EXPIRED", f"{field} is not valid ISO-8601"
        ) from exc
    if parsed.tzinfo is None:
        raise ResolverError(
            "HOLD_AUTHORITY_EXPIRED", f"{field} must include timezone"
        )
    return parsed.astimezone(timezone.utc)


def _safe_artifact_path(repo_root: Path, relative_ref: Any, field: str) -> Path:
    if not isinstance(relative_ref, str) or not relative_ref.strip():
        raise ResolverError("HOLD_AUTHORITY_INCOMPLETE", f"{field} is missing")
    relative = Path(relative_ref)
    if relative.is_absolute() or ".." in relative.parts:
        raise ResolverError(
            "BLOCK_AUTHORITY_REFERENCE_INVALID", f"{field} is not a safe relative path"
        )
    if any(part in DISALLOWED_PATH_PARTS for part in relative.parts):
        raise ResolverError(
            "BLOCK_AUTHORITY_REFERENCE_INVALID",
            f"{field} points to a non-authoritative tree",
        )

    allowed_root = (repo_root / ARTIFACT_ROOT_REL).resolve()
    candidate = (repo_root / relative).resolve()
    try:
        candidate.relative_to(allowed_root)
    except ValueError as exc:
        raise ResolverError(
            "BLOCK_AUTHORITY_REFERENCE_INVALID",
            f"{field} is outside the authority artifact root",
        ) from exc
    return candidate


def _load_json(path: Path, missing_state: str, field: str) -> dict[str, Any]:
    if not path.is_file():
        raise ResolverError(missing_state, f"{field} does not resolve")
    try:
        if path.stat().st_size > MAX_JSON_BYTES:
            raise ResolverError(
                "BLOCK_AUTHORITY_ARTIFACT_INVALID", f"{field} exceeds size limit"
            )
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ResolverError(missing_state, f"{field} cannot be read") from exc
    except json.JSONDecodeError as exc:
        raise ResolverError(
            "BLOCK_AUTHORITY_ARTIFACT_INVALID", f"{field} is not valid JSON"
        ) from exc
    if not isinstance(value, dict):
        raise ResolverError(
            "BLOCK_AUTHORITY_ARTIFACT_INVALID", f"{field} must be an object"
        )
    return value


def _require_text(mapping: Mapping[str, Any], field: str) -> str:
    value = mapping.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ResolverError("HOLD_AUTHORITY_INCOMPLETE", f"{field} is missing")
    return value.strip()


def _require_opaque_ref(
    mapping: Mapping[str, Any],
    field: str,
    prefix: str,
) -> str:
    value = _require_text(mapping, field)
    if not value.startswith(prefix) or OPAQUE_REF.fullmatch(value) is None:
        raise ResolverError(
            "BLOCK_AUTHORITY_REFERENCE_INVALID",
            f"{field} is not a valid {prefix} reference",
        )
    return value


def _require_hash(mapping: Mapping[str, Any], field: str) -> str:
    value = mapping.get(field)
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ResolverError(
            "BLOCK_AUTHORITY_SCOPE_ESCALATION",
            f"{field} must be a lowercase SHA-256 digest",
        )
    return value


def _require_positive_budget(mapping: Mapping[str, Any], field: str) -> int:
    value = mapping.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ResolverError(
            "BLOCK_AUTHORITY_SCOPE_ESCALATION",
            f"{field} must be an explicit positive integer",
        )
    return value


def _validate_state_cell_pilot_constraints(constraints: Any) -> None:
    if not isinstance(constraints, Mapping):
        raise ResolverError(
            "BLOCK_AUTHORITY_SCOPE_ESCALATION",
            "state-cell pilot scope constraints are required",
        )
    if set(constraints) != STATE_CELL_PILOT_CONSTRAINT_FIELDS:
        raise ResolverError(
            "BLOCK_AUTHORITY_SCOPE_ESCALATION",
            "state-cell pilot scope constraints are missing or expanded",
        )
    for field in (
        "proposal_sha256",
        "red_team_receipt_sha256",
        "target_field_sha256",
        "carrier_capability_registry_sha256",
        "authorized_steps_sha256",
        "evidence_refs_sha256",
    ):
        _require_hash(constraints, field)
    for field in (
        "cell_budget",
        "relation_traversal_budget",
        "observation_budget",
    ):
        _require_positive_budget(constraints, field)
    if constraints.get("target_node") != STATE_CELL_PILOT_NODE:
        raise ResolverError(
            "BLOCK_AUTHORITY_SCOPE_ESCALATION",
            "state-cell pilot target_node must be MSI",
        )
    if constraints.get("authorized_action") != STATE_CELL_PILOT_ACTION:
        raise ResolverError(
            "BLOCK_AUTHORITY_SCOPE_ESCALATION",
            "state-cell pilot authorized_action is invalid",
        )
    if constraints.get("maximum_effect") != STATE_CELL_PILOT_MAXIMUM_EFFECT:
        raise ResolverError(
            "BLOCK_AUTHORITY_SCOPE_ESCALATION",
            "state-cell pilot maximum_effect is invalid",
        )
    for field in ("object_id", "exact_coordinate"):
        if not isinstance(constraints.get(field), str) or not constraints[field].strip():
            raise ResolverError(
                "BLOCK_AUTHORITY_SCOPE_ESCALATION",
                f"state-cell pilot {field} is required",
            )
    forbidden = constraints.get("forbidden_effects")
    if (
        not isinstance(forbidden, list)
        or len(forbidden) != len(set(forbidden))
        or set(forbidden) != STATE_CELL_PILOT_FORBIDDEN_EFFECTS
    ):
        raise ResolverError(
            "BLOCK_AUTHORITY_SCOPE_ESCALATION",
            "state-cell pilot forbidden_effects must match the hard wall",
        )
    operation_nonce = constraints.get("operation_nonce")
    if not isinstance(operation_nonce, str) or NONCE_REF.fullmatch(operation_nonce) is None:
        raise ResolverError(
            "BLOCK_AUTHORITY_REFERENCE_INVALID",
            "operation_nonce is not a valid opaque nonce ref",
        )
    for field in (
        "single_use_authorization_required",
        "replay_protected",
        "authority_signature_required",
    ):
        if constraints.get(field) is not True:
            raise ResolverError(
                "BLOCK_AUTHORITY_SCOPE_ESCALATION",
                f"state-cell pilot {field} must be true",
            )
    for field in (
        "db_write",
        "deploy",
        "restart",
        "network_route_mutation",
        "cloud_call",
        "file_delete",
        "canonical_pointer_write",
        "active_pointer_write",
        "old_version_target_import",
    ):
        if constraints.get(field) is not False:
            raise ResolverError(
                "BLOCK_AUTHORITY_SCOPE_ESCALATION",
                f"state-cell pilot {field} must be false",
            )


def _validate_git_push_constraints(constraints: Any) -> None:
    if not isinstance(constraints, Mapping) or set(constraints) != GIT_PUSH_CONSTRAINT_FIELDS:
        raise ResolverError(
            "BLOCK_AUTHORITY_SCOPE_ESCALATION",
            "git-push scope constraints are missing or expanded",
        )
    for field in ("review_registration_sha256", "remote_url_sha256", "allowed_paths_sha256"):
        _require_hash(constraints, field)
    for field in ("base_commit", "target_tree"):
        value = constraints.get(field)
        if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{40,64}", value) is None:
            raise ResolverError(
                "BLOCK_AUTHORITY_SCOPE_ESCALATION",
                f"git-push {field} must be an exact Git object id",
            )
    review_ref = constraints.get("review_registration_ref")
    if (
        not isinstance(review_ref, str)
        or not review_ref.startswith("runtime/total_field/authority_artifacts/")
        or not review_ref.endswith("/GIT_PUSH_REVIEW_REGISTRATION.json")
        or ".." in Path(review_ref).parts
    ):
        raise ResolverError(
            "BLOCK_AUTHORITY_REFERENCE_INVALID",
            "git-push review_registration_ref is invalid",
        )
    for field in ("branch", "remote_name"):
        value = constraints.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ResolverError(
                "BLOCK_AUTHORITY_SCOPE_ESCALATION",
                f"git-push {field} is required",
            )
    for field in (
        "single_commit_only",
        "formal_submission",
        "git_push",
        "single_use_authorization_required",
        "replay_protected",
        "authority_signature_required",
    ):
        if constraints.get(field) is not True:
            raise ResolverError(
                "BLOCK_AUTHORITY_SCOPE_ESCALATION",
                f"git-push {field} must be true",
            )
    for field in ("deploy", "restart", "canonical_pointer_write", "active_pointer_write"):
        if constraints.get(field) is not False:
            raise ResolverError(
                "BLOCK_AUTHORITY_SCOPE_ESCALATION",
                f"git-push {field} must be false",
            )


def _verify_sha256(path: Path, expected: Any, state: str, field: str) -> None:
    if not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None:
        raise ResolverError("HOLD_AUTHORITY_INCOMPLETE", f"{field} is invalid")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise ResolverError(state, f"{field} mismatch")


def _validate_pointer_shape(pointer: Mapping[str, Any]) -> None:
    required = {
        "schema_id",
        "authority_id",
        "authority_version",
        "state",
        "active",
        "founder_person_packet_ref",
        "registered_device_ref",
        "founder_capability_assignment_ref",
        "access_profile_ref",
        "authority_scope",
        "issued_at",
        "expires_at",
        "nonce",
        "authority_payload_sha256",
        "d8_decision_ref",
        "d8_decision_sha256",
        "owner_seal_ref",
        "owner_seal_sha256",
        "signature_ref",
        "revocation_ref",
        "verifier_ref",
    }
    missing = sorted(
        field for field in required if pointer.get(field) in (None, "", [], {})
    )
    if missing:
        raise ResolverError(
            "HOLD_AUTHORITY_INCOMPLETE",
            "missing pointer fields: " + ",".join(missing),
        )
    if pointer.get("schema_id") != "W7TP_ACTIVE_TOTAL_FIELD_AUTHORITY_V1":
        raise ResolverError("HOLD_AUTHORITY_INCOMPLETE", "pointer schema_id is invalid")
    if pointer.get("state") != "ACTIVE" or pointer.get("active") is not True:
        raise ResolverError("HOLD_AUTHORITY_INCOMPLETE", "pointer is not ACTIVE")

    _require_opaque_ref(pointer, "authority_id", "authority_ref:")
    _require_opaque_ref(pointer, "founder_person_packet_ref", "person_packet_ref:")
    _require_opaque_ref(pointer, "registered_device_ref", "device_ref:")
    _require_opaque_ref(
        pointer,
        "founder_capability_assignment_ref",
        "capability_assignment_ref:",
    )
    _require_opaque_ref(pointer, "access_profile_ref", "access_profile_ref:")
    _require_opaque_ref(pointer, "verifier_ref", "verifier_ref:")

    scope = pointer.get("authority_scope")
    if (
        not isinstance(scope, list)
        or len(scope) != 1
        or scope[0] not in SCOPE_OWNER_AUTHORIZATIONS
    ):
        raise ResolverError(
            "HOLD_AUTHORITY_INCOMPLETE",
            "authority_scope must contain exactly one allowed scope",
        )
    constraints = pointer.get("authority_scope_constraints")
    if scope[0] == POINTER_BOOTSTRAP_SCOPE:
        if constraints != POINTER_BOOTSTRAP_SCOPE_CONSTRAINTS:
            raise ResolverError(
                "BLOCK_AUTHORITY_SCOPE_ESCALATION",
                "pointer-bootstrap scope constraints are missing or expanded",
            )
    elif scope[0] == PROMOTION_SCOPE:
        if constraints != PROMOTION_SCOPE_CONSTRAINTS:
            raise ResolverError(
                "BLOCK_AUTHORITY_SCOPE_ESCALATION",
                "promotion scope constraints are missing, drifted, or expanded",
            )
    elif scope[0] == STATE_CELL_PILOT_SCOPE:
        _validate_state_cell_pilot_constraints(constraints)
    elif scope[0] == GIT_PUSH_SCOPE:
        _validate_git_push_constraints(constraints)
    elif constraints not in (None, {}):
        raise ResolverError(
            "BLOCK_AUTHORITY_SCOPE_ESCALATION",
            "scope constraints are not allowed for RECEIVE_CANDIDATE",
        )

    nonce = pointer.get("nonce")
    if not isinstance(nonce, str) or NONCE_REF.fullmatch(nonce) is None:
        raise ResolverError(
            "BLOCK_AUTHORITY_REFERENCE_INVALID", "nonce is not a valid opaque nonce ref"
        )


def _verify_pointer_hash(pointer: Mapping[str, Any]) -> str:
    supplied = pointer.get("authority_payload_sha256")
    if not isinstance(supplied, str) or re.fullmatch(r"[0-9a-f]{64}", supplied) is None:
        raise ResolverError(
            "HOLD_AUTHORITY_INCOMPLETE", "authority_payload_sha256 is invalid"
        )
    unsigned = dict(pointer)
    unsigned.pop("authority_payload_sha256", None)
    actual = canonical_sha256(unsigned)
    if actual != supplied:
        raise ResolverError(
            "BLOCK_AUTHORITY_BINDING_INVALID", "authority payload hash mismatch"
        )
    return supplied


def _verify_time_window(pointer: Mapping[str, Any], now: datetime) -> int:
    issued_at = _parse_utc(pointer.get("issued_at"), "issued_at")
    expires_at = _parse_utc(pointer.get("expires_at"), "expires_at")
    ttl = int((expires_at - issued_at).total_seconds())
    if ttl <= 0 or ttl > MAX_TTL_SECONDS or issued_at > now or now >= expires_at:
        raise ResolverError(
            "HOLD_AUTHORITY_EXPIRED",
            "authority time window is invalid, expired, or exceeds maximum TTL",
        )
    return ttl


def _verify_d8(
    artifact: Mapping[str, Any],
    *,
    authority_id: str,
    now: datetime,
) -> None:
    if artifact.get("schema_id") != "W7TP_ACTIVE_TOTAL_FIELD_AUTHORITY_D8_DECISION_V1":
        raise ResolverError(
            "HOLD_D8_AUTHORITY_NOT_APPROVED", "D8 artifact schema is invalid"
        )
    if artifact.get("authority_id") != authority_id:
        raise ResolverError(
            "HOLD_D8_AUTHORITY_NOT_APPROVED", "D8 authority_id mismatch"
        )
    if artifact.get("decision") != "PASS":
        raise ResolverError(
            "HOLD_D8_AUTHORITY_NOT_APPROVED", "D8 decision is not PASS"
        )
    reviewed_at = _parse_utc(artifact.get("reviewed_at"), "d8.reviewed_at")
    expires_at = _parse_utc(artifact.get("expires_at"), "d8.expires_at")
    if reviewed_at > now or now >= expires_at:
        raise ResolverError(
            "HOLD_D8_AUTHORITY_NOT_APPROVED", "D8 decision is not currently valid"
        )


def _verify_owner_seal(
    artifact: Mapping[str, Any],
    *,
    authority_id: str,
    authority_scope: list[str],
    now: datetime,
) -> None:
    if artifact.get("schema_id") != "W7TP_ACTIVE_TOTAL_FIELD_AUTHORITY_OWNER_SEAL_V1":
        raise ResolverError("BLOCK_OWNER_SEAL_INVALID", "Owner seal schema is invalid")
    if artifact.get("authority_id") != authority_id:
        raise ResolverError("BLOCK_OWNER_SEAL_INVALID", "Owner seal authority_id mismatch")
    expected_authorization = (
        SCOPE_OWNER_AUTHORIZATIONS.get(authority_scope[0])
        if len(authority_scope) == 1
        else None
    )
    if artifact.get("authorization") != expected_authorization:
        raise ResolverError(
            "BLOCK_OWNER_SEAL_INVALID", "Owner seal authorization is invalid for scope"
        )
    _require_opaque_ref(artifact, "single_use_id", "single_use_ref:")
    issued_at = _parse_utc(artifact.get("issued_at"), "owner_seal.issued_at")
    expires_at = _parse_utc(artifact.get("expires_at"), "owner_seal.expires_at")
    if issued_at > now or now >= expires_at:
        raise ResolverError("BLOCK_OWNER_SEAL_INVALID", "Owner seal is not currently valid")


def _verify_detached_signature(
    artifact: Mapping[str, Any],
    *,
    authority_id: str,
    payload_sha256: str,
    verifier_ref: str,
    verifier: TrustedSignatureVerifier,
) -> None:
    if artifact.get("schema_id") != "W7TP_ACTIVE_TOTAL_FIELD_AUTHORITY_SIGNATURE_V1":
        raise ResolverError(
            "BLOCK_AUTHORITY_SIGNATURE_INVALID", "signature artifact schema is invalid"
        )
    if artifact.get("authority_id") != authority_id:
        raise ResolverError(
            "BLOCK_AUTHORITY_SIGNATURE_INVALID", "signature authority_id mismatch"
        )
    if artifact.get("signed_payload_sha256") != payload_sha256:
        raise ResolverError(
            "BLOCK_AUTHORITY_SIGNATURE_INVALID", "signed payload hash mismatch"
        )
    if artifact.get("verifier_ref") != verifier_ref:
        raise ResolverError(
            "BLOCK_AUTHORITY_SIGNATURE_INVALID", "signature verifier_ref mismatch"
        )
    signature = artifact.get("signature")
    if not isinstance(signature, str) or not signature:
        raise ResolverError(
            "BLOCK_AUTHORITY_SIGNATURE_INVALID", "detached signature is missing"
        )
    if not verifier.verify(
        verifier_ref=verifier_ref,
        payload_sha256=payload_sha256,
        signature=signature,
    ):
        raise ResolverError(
            "BLOCK_AUTHORITY_SIGNATURE_INVALID", "detached signature verification failed"
        )


def _verify_revocation_list(
    artifact: Mapping[str, Any],
    *,
    authority_id: str,
    verifier_ref: str,
    verifier: TrustedSignatureVerifier,
) -> None:
    if artifact.get("schema_id") != "W7TP_ACTIVE_TOTAL_FIELD_AUTHORITY_REVOCATION_LIST_V1":
        raise ResolverError(
            "BLOCK_AUTHORITY_REVOKED", "revocation artifact schema is invalid"
        )
    supplied = artifact.get("revocation_payload_sha256")
    if not isinstance(supplied, str) or re.fullmatch(r"[0-9a-f]{64}", supplied) is None:
        raise ResolverError(
            "BLOCK_AUTHORITY_REVOKED", "revocation payload hash is invalid"
        )
    unsigned = dict(artifact)
    unsigned.pop("revocation_payload_sha256", None)
    signature = unsigned.pop("signature", None)
    actual = canonical_sha256(unsigned)
    if actual != supplied:
        raise ResolverError(
            "BLOCK_AUTHORITY_REVOKED", "revocation payload hash mismatch"
        )
    if artifact.get("verifier_ref") != verifier_ref:
        raise ResolverError(
            "BLOCK_AUTHORITY_REVOKED", "revocation verifier_ref mismatch"
        )
    if not isinstance(signature, str) or not verifier.verify(
        verifier_ref=verifier_ref,
        payload_sha256=supplied,
        signature=signature,
    ):
        raise ResolverError(
            "BLOCK_AUTHORITY_REVOKED", "revocation signature verification failed"
        )
    revoked = artifact.get("revoked_authority_ids")
    if not isinstance(revoked, list):
        raise ResolverError(
            "BLOCK_AUTHORITY_REVOKED", "revoked_authority_ids must be a list"
        )
    if authority_id in revoked:
        raise ResolverError("BLOCK_AUTHORITY_REVOKED", "authority is revoked")


def resolve_active_total_field_authority(
    authority_lookup_ref: Any,
    *,
    repo_root: Path,
    nonce_ledger: PersistentNonceLedger | None,
    signature_verifier: TrustedSignatureVerifier | None,
    trusted_verifier_refs: Collection[str],
) -> dict[str, Any]:
    """
    Resolve the single active runtime pointer and verify independent D8, Owner seal,
    detached signature, revocation, time window, and persistent replay protection.

    The caller may provide only the fixed lookup reference. Caller-supplied Founder,
    provider-account, D8, or authority fields are never accepted.
    """
    try:
        root = Path(repo_root).resolve()
        if authority_lookup_ref != ACTIVE_POINTER_REL.as_posix():
            if isinstance(authority_lookup_ref, Mapping):
                raise ResolverError(
                    "BLOCK_PROVIDER_ACCOUNT_AUTHORITY",
                    "caller-supplied authority mappings are forbidden",
                )
            raise ResolverError(
                "HOLD_AUTHORITY_INCOMPLETE",
                "authority_lookup_ref must name the fixed active runtime pointer",
            )

        if nonce_ledger is None:
            raise ResolverError(
                "HOLD_NONCE_LEDGER_NOT_PERSISTENT", "persistent nonce ledger is required"
            )
        if getattr(nonce_ledger, "persistent", False) is not True:
            raise ResolverError(
                "HOLD_NONCE_LEDGER_NOT_PERSISTENT",
                "process-local nonce storage is insufficient",
            )
        if signature_verifier is None or getattr(
            signature_verifier, "trusted_runtime_verifier", False
        ) is not True:
            raise ResolverError(
                "HOLD_TRUSTED_VERIFIER_UNAVAILABLE",
                "trusted runtime signature verifier is required",
            )

        pointer_path = (root / ACTIVE_POINTER_REL).resolve()
        pointer = _load_json(
            pointer_path,
            "HOLD_AUTHORITY_INCOMPLETE",
            "ACTIVE_TOTAL_FIELD_AUTHORITY",
        )
        _validate_pointer_shape(pointer)

        verifier_ref = str(pointer["verifier_ref"])
        if verifier_ref not in set(trusted_verifier_refs):
            raise ResolverError(
                "BLOCK_AUTHORITY_SIGNATURE_INVALID",
                "verifier_ref is not in the trusted runtime set",
            )

        payload_sha256 = _verify_pointer_hash(pointer)
        now = datetime.now(timezone.utc)
        ttl_seconds = _verify_time_window(pointer, now)
        authority_id = str(pointer["authority_id"])

        d8_path = _safe_artifact_path(root, pointer["d8_decision_ref"], "d8_decision_ref")
        owner_path = _safe_artifact_path(root, pointer["owner_seal_ref"], "owner_seal_ref")
        signature_path = _safe_artifact_path(root, pointer["signature_ref"], "signature_ref")
        revocation_path = _safe_artifact_path(
            root, pointer["revocation_ref"], "revocation_ref"
        )

        d8_artifact = _load_json(
            d8_path,
            "HOLD_D8_AUTHORITY_NOT_APPROVED",
            "d8_decision_ref",
        )
        owner_artifact = _load_json(
            owner_path,
            "BLOCK_OWNER_SEAL_INVALID",
            "owner_seal_ref",
        )
        signature_artifact = _load_json(
            signature_path,
            "BLOCK_AUTHORITY_SIGNATURE_INVALID",
            "signature_ref",
        )
        revocation_artifact = _load_json(
            revocation_path,
            "BLOCK_AUTHORITY_REVOKED",
            "revocation_ref",
        )

        _verify_sha256(
            d8_path,
            pointer["d8_decision_sha256"],
            "BLOCK_AUTHORITY_BINDING_INVALID",
            "d8_decision_sha256",
        )
        _verify_sha256(
            owner_path,
            pointer["owner_seal_sha256"],
            "BLOCK_AUTHORITY_BINDING_INVALID",
            "owner_seal_sha256",
        )
        _verify_d8(d8_artifact, authority_id=authority_id, now=now)
        _verify_owner_seal(
            owner_artifact,
            authority_id=authority_id,
            authority_scope=list(pointer["authority_scope"]),
            now=now,
        )
        _verify_detached_signature(
            signature_artifact,
            authority_id=authority_id,
            payload_sha256=payload_sha256,
            verifier_ref=verifier_ref,
            verifier=signature_verifier,
        )
        _verify_revocation_list(
            revocation_artifact,
            authority_id=authority_id,
            verifier_ref=verifier_ref,
            verifier=signature_verifier,
        )

        nonce = str(pointer["nonce"])
        if not nonce_ledger.mark_used_or_replay(
            nonce,
            payload_sha256,
            now.timestamp(),
            ttl_seconds,
        ):
            raise ResolverError(
                "BLOCK_AUTHORITY_REPLAY", "authority nonce has already been consumed"
            )

        authority_result = dict(pointer)
        authority_result["_authority_file_sha256"] = hashlib.sha256(
            pointer_path.read_bytes()
        ).hexdigest()
        return _result(
            "PASS_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVED",
            "independently issued runtime authority verified for its single bounded scope",
            authority=authority_result,
        )
    except ResolverError as exc:
        return _result(exc.state, exc.reason)


# === FOUNDER_SOVEREIGN_ROOT_D8_TRUST_ANCHOR_POLICY_V1 ===
FOUNDER_SOVEREIGN_ROOT_ROLE_PROMOTION_SCOPE = "AUTHORIZE_G4_V11_D4_FORMAL_EFFECT_SIGNER_ROLE_PROMOTION"
SCOPE_OWNER_AUTHORIZATIONS[FOUNDER_SOVEREIGN_ROOT_ROLE_PROMOTION_SCOPE] = (
    "FOUNDER_APPROVED_G4_V11_D4_FORMAL_EFFECT_SIGNING_AUTHORITY"
)

FOUNDER_SINGLE_IDENTITY_ROOT_POLICY_V1 = {
    "policy_id": "W7TP_FOUNDER_SINGLE_IDENTITY_ROOT_MULTI_ROLE_TRUST_ANCHOR_POLICY_V1",
    "founder_sovereign_authority_w7tp_sha256": "92e67208c60bf7c8a447b22b4444a8cb87973e93e21059055eaae3bba3257990",
    "founder_dual_root_file_ref": "runtime/total_field/founder_identity/ACTIVE_FOUNDER_DUAL_ROOT_V1.json",
    "founder_dual_root_file_sha256": "53959616671df28940b91453d867633a5a5ef8cc974f01736f0422d21060a681",
    "founder_dual_root_content_sha256": "7d50f05169e55e822dbe7dd952a7499cf9442e88cd7334d2f638103c0a76a851",
    "founder_webauthn_cose_public_key_sha256": "7f1760bbec2cc2eb9c2c65d06677cda7faa9a86cc8f0ce0fbe1055e4f2d87e53",
    "founder_webauthn_ecdsa_receipt_sha256": "cfb1ed2037f5497543190e2e10d5ce267409a4e512ccdb532aa4474df0e53935",
    "authorized_sovereign_node_root_key": {
        "key_id": "wuchang-node",
        "authorizer_role": "FOUNDER_SOVEREIGN_NODE_ROOT_AUTHORIZER",
        "verifier_ref": "verifier_ref:founder_sovereign_root_v1",
        "public_key_pem_ref": "runtime/total_field/authority_artifacts/W7TP_TOTAL_FIELD_ROOT_OF_TRUST_BOOTSTRAP_20260821T1557+0800/founder_sovereign_root_public.pem",
        "public_key_pem_sha256": "22846bf4b13addf961b5251ee764398ff59aefaffd5ac4392c4b456447b3defa",
        "ed25519_raw_public_key_fingerprint_sha256": "7e32872072060c90c7954629c68eb31fa6c0532e64d454d189e2c55f1bcb3b0a",
        "openssh_public_key_fingerprint": "SHA256:r2JW3GHzRO6i8+gwCQsuMsx61xm5xuoyR/j3e//qF3E",
        "authorized_to_promote_d8_key_fingerprint": "09adae73f29258eadb9f0eee007a05b2e03ef6bb331ab0ab4c0cf58d57d01570",
        "authorized_effect_domains": [
            "G4_DUAL_ACTIVE_FIELD_RECOVERY_AND_ROUTER_ALIGNMENT",
            "FOUNDER_DUAL_ROOT_ROUTINE_DELEGATION_V11",
            "TOTAL_FIELD_V11_TWO_EFFECT_WHITELIST",
            "D4_SINGLE_USE_FORMAL_BROKER_RECEIPT_ISSUANCE",
        ],
    },
}


def resolve_founder_sovereign_root_role_promotion_authority(
    *,
    repo_root: Path,
    now: datetime | None = None,
) -> dict[str, Any]:
    from cryptography.hazmat.primitives import serialization
    from tools.total_field.w7tp_ed25519_verifier import validate_stage_b_signature
    from tools.total_field_ed25519_backend import Ed25519DetachedSignatureBackend

    root = Path(repo_root).resolve()
    check_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    policy = FOUNDER_SINGLE_IDENTITY_ROOT_POLICY_V1
    anchor = policy["authorized_sovereign_node_root_key"]

    dual_root_path = (root / policy["founder_dual_root_file_ref"]).resolve()
    _verify_sha256(
        dual_root_path,
        policy["founder_dual_root_file_sha256"],
        "BLOCK_FOUNDER_IDENTITY_ROOT_MISMATCH",
        "founder_dual_root_file_sha256",
    )
    dual_root_obj = _load_json(
        dual_root_path,
        "HOLD_FOUNDER_IDENTITY_ROOT_MISSING",
        "ACTIVE_FOUNDER_DUAL_ROOT_V1",
    )
    expected_dev_fp = "sha256:" + policy["founder_webauthn_cose_public_key_sha256"]
    if (
        dual_root_obj.get("enabled") is not True
        or dual_root_obj.get("root_sha256") != policy["founder_dual_root_content_sha256"]
        or dual_root_obj.get("device_principal_fingerprint") != expected_dev_fp
    ):
        raise ResolverError(
            "BLOCK_FOUNDER_IDENTITY_ROOT_MISMATCH",
            "ACTIVE_FOUNDER_DUAL_ROOT_V1 content or passkey fingerprint mismatch",
        )

    fpub_path = (root / anchor["public_key_pem_ref"]).resolve()
    _verify_sha256(
        fpub_path,
        anchor["public_key_pem_sha256"],
        "BLOCK_FOUNDER_SOVEREIGN_KEY_MISMATCH",
        "public_key_pem_sha256",
    )
    f_raw = serialization.load_pem_public_key(fpub_path.read_bytes()).public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    actual_fp = hashlib.sha256(f_raw).hexdigest()
    if actual_fp != anchor["ed25519_raw_public_key_fingerprint_sha256"]:
        raise ResolverError(
            "BLOCK_FOUNDER_SOVEREIGN_KEY_MISMATCH",
            "wuchang-node raw Ed25519 fingerprint mismatch",
        )

    ddir = root / "runtime/total_field/authority_artifacts/W7TP_TOTAL_FIELD_ROOT_OF_TRUST_BOOTSTRAP_20260821T1557+0800"
    grant_path = ddir / "INDEPENDENT_FOUNDER_SOVEREIGN_ROOT_ROLE_PROMOTION_GRANT_20261020.json"
    grant = _load_json(
        grant_path,
        "HOLD_ROLE_PROMOTION_GRANT_MISSING",
        "INDEPENDENT_FOUNDER_SOVEREIGN_ROOT_ROLE_PROMOTION_GRANT_20261020",
    )
    grant_sha256 = hashlib.sha256(grant_path.read_bytes()).hexdigest()

    body = grant.get("stage_b_object_without_signature") or {}
    issued_at = _parse_utc(body.get("issued_at"), "grant.issued_at")
    expires_at = _parse_utc(body.get("expires_at"), "grant.expires_at")
    if issued_at > check_now or check_now >= expires_at:
        raise ResolverError("HOLD_AUTHORITY_EXPIRED", "role promotion grant is not currently valid")

    psa = body.get("promoted_subject_authority") or {}
    ifs = body.get("independent_founder_sovereign_issuer") or {}
    aae = body.get("approved_artifacts_and_effects") or {}
    if (
        body.get("self_authorization") is not False
        or body.get("issuer_is_subject_key") is not False
        or body.get("grant_state") != "PASS_INDEPENDENT_FOUNDER_ROLE_PROMOTION_GRANTED"
        or ifs.get("raw_public_key_fingerprint") != anchor["ed25519_raw_public_key_fingerprint_sha256"]
        or psa.get("final_authority_granted") is not True
        or psa.get("formal_d8_effect_signer_role_granted") is not True
        or psa.get("subject_raw_public_key_fingerprint") != anchor["authorized_to_promote_d8_key_fingerprint"]
        or len(aae) != 16 or any(not isinstance(v, str) or len(v) != 64 for v in aae.values())
    ):
        raise ResolverError(
            "BLOCK_AUTHORITY_SCOPE_ESCALATION",
            "role promotion grant subject or effect domains mismatch",
        )

    stage_b_res = validate_stage_b_signature(
        domain_separator=grant["domain_separator"],
        packet_canonical_id=grant["packet_canonical_id"],
        stage_b_object_without_signature=body,
        public_key_ref=anchor["public_key_pem_ref"],
        public_key_resolver=lambda _ref: f_raw,
        expected_public_key_fingerprint=actual_fp,
        signature_hex=grant["stage_b_signature_hex"],
    )
    if not stage_b_res.valid:
        raise ResolverError("BLOCK_AUTHORITY_SIGNATURE_INVALID", stage_b_res.reason_code)

    f_backend = Ed25519DetachedSignatureBackend(
        fpub_path,
        trusted_verifier_refs=[anchor["verifier_ref"]],
    )
    for label, sig_field in (
        ("detached_signature_artifact", "detached_signature_artifact"),
        ("independent_owner_seal_signature", "independent_owner_seal_signature"),
        ("independent_d8_decision_signature", "independent_d8_decision_signature"),
    ):
        sig_obj = grant.get(sig_field) or {}
        if not f_backend.verify_detached(
            verifier_ref=sig_obj.get("verifier_ref", ""),
            payload_sha256=sig_obj.get("signed_payload_sha256", ""),
            signature=sig_obj.get("signature", ""),
        ):
            raise ResolverError("BLOCK_AUTHORITY_SIGNATURE_INVALID", f"{label} failed verification")

    rpub_path = ddir / "authority_signing_public.pem"
    r_backend = Ed25519DetachedSignatureBackend(
        rpub_path,
        trusted_verifier_refs=["verifier_ref:total_field_runtime_v1"],
    )
    rev_path = ddir / "revocation_list.json"
    rev_obj = _load_json(rev_path, "BLOCK_AUTHORITY_REVOKED", "revocation_list")
    _verify_revocation_list(
        rev_obj,
        authority_id=str(psa.get("authority_id")),
        verifier_ref="verifier_ref:total_field_runtime_v1",
        verifier=r_backend,
    )
    # revocation_list already verified via _verify_revocation_list above

    return {
        "state": "PASS_FOUNDER_SOVEREIGN_ROOT_D8_ROLE_PROMOTION_AUTHORITY_RESOLVED",
        "reason": "wuchang-node admitted under single Founder Identity Root and verified for G4/V11/D4 D8 role promotion",
        "authority_verified": True,
        "policy_id": policy["policy_id"],
        "founder_identity_root_sha256": policy["founder_dual_root_content_sha256"],
        "founder_dual_root_file_sha256": policy["founder_dual_root_file_sha256"],
        "founder_webauthn_ecdsa_receipt_sha256": policy["founder_webauthn_ecdsa_receipt_sha256"],
        "admitted_sovereign_root_key_id": anchor["key_id"],
        "admitted_sovereign_root_role": anchor["authorizer_role"],
        "admitted_sovereign_root_fingerprint": actual_fp,
        "promoted_d8_signer_fingerprint": anchor["authorized_to_promote_d8_key_fingerprint"],
        "promoted_role": psa.get("to_promoted_profile"),
        "authorized_effect_domains": list(anchor["authorized_effect_domains"]),
        "role_promotion_grant_sha256": grant_sha256,
        "revocation_list_sha256": hashlib.sha256(rev_path.read_bytes()).hexdigest(),
        "stage_b_verification": stage_b_res.reason_code,
        "detached_signatures_verified": True,
    }


def verify_canonical_trust_policy_promotion(*, repo_root: Path) -> dict[str, Any]:
    from cryptography.hazmat.primitives import serialization
    from tools.total_field.w7tp_ed25519_verifier import validate_stage_b_signature
    from tools.total_field.w7tp_v2_3_candidate_source import active_canonical_binding
    from tools.total_field_ed25519_backend import Ed25519DetachedSignatureBackend

    root = Path(repo_root).resolve()
    role_res = resolve_founder_sovereign_root_role_promotion_authority(repo_root=root)
    pointer_path = root / "runtime/total_field/master_index/ACTIVE_W7TP_CANONICAL_POINTER.json"
    binding = active_canonical_binding(pointer_path)
    contract_path = root / binding["canonical_path"]
    contract = _load_json(contract_path, "HOLD_CANONICAL_CONTRACT_MISSING", "CONTRACT.json")
    ac = contract.get("activation_contract") or {}

    policy = FOUNDER_SINGLE_IDENTITY_ROOT_POLICY_V1
    anchor = policy["authorized_sovereign_node_root_key"]
    if (
        ac.get("founder_trust_anchor_policy_id") != policy["policy_id"]
        or ac.get("admitted_sovereign_root_key_id") != anchor["key_id"]
        or ac.get("admitted_sovereign_root_fingerprint") != anchor["ed25519_raw_public_key_fingerprint_sha256"]
        or ac.get("trust_anchor_admission_receipt_sha256") != "c3aacf94c8911e0d23d9cc5287d16b6160d96320a70fdef60cfaddd3ef4bb1f3"
        or binding.get("founder_trust_anchor_policy_id") != policy["policy_id"]
    ):
        raise ResolverError("HOLD_CANONICAL_TRUST_POLICY_LINKAGE", "canonical contract or pointer missing trust policy binding")

    prom_ref = binding.get("trust_policy_promotion_receipt_path")
    prom_sha = binding.get("trust_policy_promotion_receipt_sha256")
    prom_path = (root / prom_ref).resolve()
    _verify_sha256(prom_path, prom_sha, "BLOCK_PROMOTION_RECEIPT_HASH_MISMATCH", "trust_policy_promotion_receipt_sha256")
    prom = _load_json(prom_path, "HOLD_PROMOTION_RECEIPT_MISSING", "CANONICAL_TRUST_POLICY_PROMOTION_RECEIPT_20261020.json")

    fpub_path = (root / anchor["public_key_pem_ref"]).resolve()
    f_raw = serialization.load_pem_public_key(fpub_path.read_bytes()).public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    sb_res = validate_stage_b_signature(
        domain_separator=prom["domain_separator"],
        packet_canonical_id=prom["packet_canonical_id"],
        stage_b_object_without_signature=prom["stage_b_object_without_signature"],
        public_key_ref=prom["public_key_ref"],
        public_key_resolver=lambda _ref: f_raw,
        expected_public_key_fingerprint=anchor["ed25519_raw_public_key_fingerprint_sha256"],
        signature_hex=prom["stage_b_signature_hex"],
    )
    if not sb_res.valid:
        raise ResolverError("BLOCK_PROMOTION_RECEIPT_SIGNATURE_INVALID", sb_res.reason_code)

    f_backend = Ed25519DetachedSignatureBackend(fpub_path, trusted_verifier_refs=[anchor["verifier_ref"]])
    dsig = prom.get("detached_signature_artifact") or {}
    if not f_backend.verify_detached(
        verifier_ref=dsig.get("verifier_ref", ""),
        payload_sha256=dsig.get("signed_payload_sha256", ""),
        signature=dsig.get("signature", ""),
    ):
        raise ResolverError("BLOCK_PROMOTION_RECEIPT_DETACHED_INVALID", "detached signature invalid")

    nonce = str((prom.get("stage_b_object_without_signature") or {}).get("nonce") or "")
    marker_name = hashlib.sha256(nonce.encode("utf-8")).hexdigest() + ".consumed"
    marker_rel = f"runtime/total_field/replay/t007_canonical_trust_policy_promotion/{marker_name}"
    marker_path = (root / marker_rel).resolve()
    if not marker_path.is_file() or marker_path.read_text(encoding="utf-8").strip() != prom_sha:
        raise ResolverError("HOLD_REPLAY_MARKER_MISMATCH", "single-use replay marker missing or content mismatch")
    marker_sha256 = hashlib.sha256(marker_path.read_bytes()).hexdigest()

    return {
        "state": "PASS_CANONICAL_TRUST_POLICY_LINKAGE_AND_SINGLE_USE_PROMOTION_VERIFIED",
        "policy_id": policy["policy_id"],
        "canonical_pointer_sha256": binding["pointer_sha256"],
        "canonical_contract_sha256": binding["canonical_sha256"],
        "canonical_contract_preimage_sha256": contract["lineage"]["v23_initial_contract_preimage_sha256"],
        "trust_anchor_admission_receipt_sha256": ac["trust_anchor_admission_receipt_sha256"],
        "trust_policy_promotion_receipt_sha256": prom_sha,
        "single_use_replay_marker_ref": marker_rel,
        "single_use_replay_marker_sha256": marker_sha256,
        "single_use_replay_marker_verified": True,
        "stage_b_verification": sb_res.reason_code,
        "detached_signature_verified": True,
        "role_promotion_state": role_res["state"],
    }
