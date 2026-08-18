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
    if not isinstance(scope, list) or "RECEIVE_CANDIDATE" not in scope:
        raise ResolverError(
            "HOLD_AUTHORITY_INCOMPLETE",
            "authority_scope lacks RECEIVE_CANDIDATE",
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
    now: datetime,
) -> None:
    if artifact.get("schema_id") != "W7TP_ACTIVE_TOTAL_FIELD_AUTHORITY_OWNER_SEAL_V1":
        raise ResolverError("BLOCK_OWNER_SEAL_INVALID", "Owner seal schema is invalid")
    if artifact.get("authority_id") != authority_id:
        raise ResolverError("BLOCK_OWNER_SEAL_INVALID", "Owner seal authority_id mismatch")
    if artifact.get("authorization") != "FOUNDER_APPROVED_RECEIVE_CANDIDATE":
        raise ResolverError(
            "BLOCK_OWNER_SEAL_INVALID", "Owner seal authorization is invalid"
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
        _verify_owner_seal(owner_artifact, authority_id=authority_id, now=now)
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

        return _result(
            "PASS_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVED",
            "independently issued runtime authority verified for candidate intake only",
            authority=pointer,
        )
    except ResolverError as exc:
        return _result(exc.state, exc.reason)


__all__ = [
    "ACTIVE_POINTER_REL",
    "ARTIFACT_ROOT_REL",
    "PersistentNonceLedger",
    "TrustedSignatureVerifier",
    "canonical_sha256",
    "resolve_active_total_field_authority",
]
