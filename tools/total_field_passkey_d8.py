#!/usr/bin/env python3
"""iPhone/WebAuthn signer adapter for an exact Total Field D8 effect."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from fido2.server import Fido2Server
from fido2.utils import websafe_decode, websafe_encode
from fido2.webauthn import (
    AttestedCredentialData,
    AuthenticationResponse,
    PublicKeyCredentialRpEntity,
    UserVerificationRequirement,
)

PASSKEY_APPROVAL_SCHEMA = "W7TP_TOTAL_FIELD_USER_VERIFIED_PASSKEY_D8_APPROVAL_V1"
PASSKEY_APPROVAL_STATE = "PASS_USER_VERIFIED_DEVICE_UNLOCK_D8_APPROVAL"
PASSKEY_POINTER_SCHEMA = "W7TP_TOTAL_FIELD_PASSKEY_APPROVAL_POINTER_V1"
PASSKEY_CREDENTIAL_SCHEMA = "W7TP_TOTAL_FIELD_FOUNDER_PASSKEY_CREDENTIAL_V1"
GIT_PUSH_SCOPE = "AUTHORIZE_GIT_PUSH"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
GIT_OID = re.compile(r"^[0-9a-f]{40,64}$")


class PasskeyD8Rejected(RuntimeError):
    pass


def canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise PasskeyD8Rejected("PASSKEY_TIME_INVALID")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PasskeyD8Rejected("PASSKEY_TIME_INVALID") from exc
    if parsed.tzinfo is None:
        raise PasskeyD8Rejected("PASSKEY_TIME_INVALID")
    return parsed.astimezone(timezone.utc)


def safe_runtime_ref(root: Path, value: Any, *, suffix: str | None = None) -> Path:
    if not isinstance(value, str) or not value:
        raise PasskeyD8Rejected("PASSKEY_REFERENCE_MISSING")
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise PasskeyD8Rejected("PASSKEY_REFERENCE_INVALID")
    if tuple(relative.parts[:2]) != ("runtime", "total_field"):
        raise PasskeyD8Rejected("PASSKEY_REFERENCE_OUTSIDE_TOTAL_FIELD")
    if suffix and not value.endswith(suffix):
        raise PasskeyD8Rejected("PASSKEY_REFERENCE_TYPE_INVALID")
    path = root.joinpath(*relative.parts)
    if not path.is_file() or path.is_symlink():
        raise PasskeyD8Rejected("PASSKEY_REFERENCE_UNAVAILABLE")
    return path


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    handle, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def load_json(path: Path, state: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PasskeyD8Rejected(state) from exc
    if not isinstance(value, dict):
        raise PasskeyD8Rejected(state)
    return value


def build_server(rp_id: str, rp_name: str, expected_origin: str) -> Fido2Server:
    return Fido2Server(
        PublicKeyCredentialRpEntity(id=rp_id, name=rp_name),
        verify_origin=lambda origin: origin == expected_origin,
    )


def load_credential(root: Path, config: Mapping[str, Any]) -> tuple[dict[str, Any], AttestedCredentialData]:
    path = safe_runtime_ref(root, config.get("credential_ref"), suffix="FOUNDER_PASSKEY_CREDENTIAL.json")
    data = load_json(path, "PASSKEY_CREDENTIAL_INVALID")
    if data.get("schema_id") != PASSKEY_CREDENTIAL_SCHEMA or data.get("state") != "ENROLLED_USER_VERIFIED":
        raise PasskeyD8Rejected("PASSKEY_CREDENTIAL_NOT_ENROLLED")
    if data.get("rp_id") != config.get("rp_id") or data.get("expected_origin") != config.get("expected_origin"):
        raise PasskeyD8Rejected("PASSKEY_CREDENTIAL_ORIGIN_DRIFT")
    encoded = data.get("attested_credential_data_b64url")
    if not isinstance(encoded, str):
        raise PasskeyD8Rejected("PASSKEY_CREDENTIAL_INVALID")
    try:
        credential = AttestedCredentialData(websafe_decode(encoded))
    except (ValueError, TypeError) as exc:
        raise PasskeyD8Rejected("PASSKEY_CREDENTIAL_INVALID") from exc
    if websafe_encode(credential.credential_id) != data.get("credential_id_b64url"):
        raise PasskeyD8Rejected("PASSKEY_CREDENTIAL_ID_DRIFT")
    return data, credential


def approval_challenge(claims: Mapping[str, Any], nonce_b64url: str) -> bytes:
    if not isinstance(nonce_b64url, str) or len(nonce_b64url) < 32:
        raise PasskeyD8Rejected("PASSKEY_NONCE_INVALID")
    return hashlib.sha256(canonical_json(claims) + b"\x00" + websafe_decode(nonce_b64url)).digest()


def _consume_once(path: Path, nonce: str, approval_sha256: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS consumed (nonce TEXT PRIMARY KEY, approval_sha256 TEXT NOT NULL, consumed_at TEXT NOT NULL)"
        )
        try:
            connection.execute(
                "INSERT INTO consumed(nonce, approval_sha256, consumed_at) VALUES(?, ?, ?)",
                (nonce, approval_sha256, iso_z(utc_now())),
            )
            connection.commit()
        except sqlite3.IntegrityError as exc:
            raise PasskeyD8Rejected("PASSKEY_APPROVAL_REPLAYED") from exc
    finally:
        connection.close()


def verify_passkey_authority(
    *,
    repo_root: str | Path,
    config: Mapping[str, Any],
    consume: bool,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Cryptographically verify one exact, short-lived WebAuthn approval."""
    root = Path(repo_root).resolve()
    try:
        if config.get("enabled") is not True or config.get("user_verification") != "required":
            raise PasskeyD8Rejected("PASSKEY_VERIFIER_NOT_ACTIVE")
        pointer_path = safe_runtime_ref(root, config.get("active_approval_pointer_ref"), suffix="ACTIVE_APPROVAL.json")
        pointer = load_json(pointer_path, "PASSKEY_APPROVAL_POINTER_INVALID")
        if pointer.get("schema_id") != PASSKEY_POINTER_SCHEMA or pointer.get("state") != "ACTIVE_SINGLE_USE":
            raise PasskeyD8Rejected("PASSKEY_APPROVAL_POINTER_INVALID")
        approval_path = safe_runtime_ref(root, pointer.get("approval_ref"), suffix="GIT_PUSH_PASSKEY_APPROVAL.json")
        approval_bytes = approval_path.read_bytes()
        approval_hash = sha256(approval_bytes)
        if approval_hash != pointer.get("approval_sha256"):
            raise PasskeyD8Rejected("PASSKEY_APPROVAL_HASH_DRIFT")
        approval = load_json(approval_path, "PASSKEY_APPROVAL_INVALID")
        if approval.get("schema_id") != PASSKEY_APPROVAL_SCHEMA or approval.get("state") != PASSKEY_APPROVAL_STATE:
            raise PasskeyD8Rejected("PASSKEY_APPROVAL_INVALID")
        if approval.get("scope") != GIT_PUSH_SCOPE or approval.get("single_use") is not True:
            raise PasskeyD8Rejected("PASSKEY_SCOPE_INVALID")
        issued = parse_time(approval.get("issued_at"))
        expires = parse_time(approval.get("expires_at"))
        observed = now or utc_now()
        max_ttl = int(config.get("maximum_ttl_seconds") or 0)
        if max_ttl <= 0 or (expires - issued).total_seconds() > max_ttl or not (issued <= observed <= expires):
            raise PasskeyD8Rejected("PASSKEY_APPROVAL_EXPIRED")
        claims = approval.get("signed_claims")
        constraints = approval.get("authority_scope_constraints")
        if not isinstance(claims, Mapping) or not isinstance(constraints, Mapping):
            raise PasskeyD8Rejected("PASSKEY_APPROVAL_BINDINGS_MISSING")
        if claims.get("scope") != GIT_PUSH_SCOPE or claims.get("authority_scope_constraints") != constraints:
            raise PasskeyD8Rejected("PASSKEY_APPROVAL_BINDING_DRIFT")
        for field in ("request_packet_sha256", "review_registration_sha256"):
            if not isinstance(claims.get(field), str) or HEX64.fullmatch(str(claims[field])) is None:
                raise PasskeyD8Rejected("PASSKEY_APPROVAL_BINDINGS_INVALID")
        for field in ("base_commit", "target_tree"):
            if GIT_OID.fullmatch(str(constraints.get(field) or "")) is None:
                raise PasskeyD8Rejected("PASSKEY_APPROVAL_BINDINGS_INVALID")
        nonce = approval.get("nonce_b64url")
        expected_challenge = approval_challenge(claims, str(nonce or ""))
        if sha256(expected_challenge) != approval.get("challenge_sha256"):
            raise PasskeyD8Rejected("PASSKEY_CHALLENGE_BINDING_DRIFT")
        assertion_path = safe_runtime_ref(root, approval.get("assertion_ref"), suffix="PASSKEY_ASSERTION.json")
        assertion_bytes = assertion_path.read_bytes()
        if sha256(assertion_bytes) != approval.get("assertion_sha256"):
            raise PasskeyD8Rejected("PASSKEY_ASSERTION_HASH_DRIFT")
        assertion_record = load_json(assertion_path, "PASSKEY_ASSERTION_INVALID")
        if assertion_record.get("state") != "SEALED_WEBAUTHN_ASSERTION":
            raise PasskeyD8Rejected("PASSKEY_ASSERTION_INVALID")
        state = assertion_record.get("webauthn_state")
        response = assertion_record.get("assertion")
        if not isinstance(state, Mapping) or not isinstance(response, Mapping):
            raise PasskeyD8Rejected("PASSKEY_ASSERTION_INVALID")
        if websafe_decode(str(state.get("challenge") or "")) != expected_challenge:
            raise PasskeyD8Rejected("PASSKEY_CHALLENGE_BINDING_DRIFT")
        credential_record, credential = load_credential(root, config)
        credential_path = safe_runtime_ref(root, config.get("credential_ref"), suffix="FOUNDER_PASSKEY_CREDENTIAL.json")
        if sha256(credential_path.read_bytes()) != approval.get("credential_sha256"):
            raise PasskeyD8Rejected("PASSKEY_CREDENTIAL_HASH_DRIFT")
        server = build_server(str(config["rp_id"]), str(config["rp_name"]), str(config["expected_origin"]))
        verified = server.authenticate_complete(state, [credential], response)
        parsed = AuthenticationResponse.from_dict(response)
        if verified.credential_id != credential.credential_id:
            raise PasskeyD8Rejected("PASSKEY_CREDENTIAL_MISMATCH")
        if not parsed.response.authenticator_data.is_user_verified():
            raise PasskeyD8Rejected("PASSKEY_USER_VERIFICATION_MISSING")
        previous_counter = int(credential_record.get("sign_count") or 0)
        counter = int(parsed.response.authenticator_data.counter)
        if previous_counter and counter and counter <= previous_counter:
            raise PasskeyD8Rejected("PASSKEY_SIGNATURE_COUNTER_REPLAY")
        if consume:
            ledger_ref = config.get("consumption_ledger_ref")
            ledger = root.joinpath(*PurePosixPath(str(ledger_ref or "")).parts)
            _consume_once(ledger, str(nonce), approval_hash)
        return {
            "state": "PASS_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVED",
            "authority_verified": True,
            "scope": [GIT_PUSH_SCOPE],
            "authority_scope_constraints": dict(constraints),
            "authority_sha256": approval_hash,
            "signer_type": "LOCAL_WINDOWS_HELLO_USER_VERIFIED",
            "user_verification": True,
            "provider_is_authority": False,
        }
    except (PasskeyD8Rejected, KeyError, ValueError, TypeError) as exc:
        reason = str(exc) if isinstance(exc, PasskeyD8Rejected) else "PASSKEY_CRYPTOGRAPHIC_VERIFICATION_FAILED"
        return {
            "state": "HOLD_DEVICE_PASSKEY_D8_AUTHORITY",
            "authority_verified": False,
            "reason": reason,
            "scope": [],
        }


__all__ = [
    "GIT_PUSH_SCOPE",
    "PASSKEY_APPROVAL_SCHEMA",
    "PASSKEY_APPROVAL_STATE",
    "PASSKEY_CREDENTIAL_SCHEMA",
    "PASSKEY_POINTER_SCHEMA",
    "PasskeyD8Rejected",
    "approval_challenge",
    "atomic_json",
    "build_server",
    "canonical_json",
    "iso_z",
    "load_credential",
    "load_json",
    "parse_time",
    "safe_runtime_ref",
    "sha256",
    "utc_now",
    "verify_passkey_authority",
]
