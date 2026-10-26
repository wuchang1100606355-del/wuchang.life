#!/usr/bin/env python3
"""Founder-enrolled platform-passkey adapter for an exact Total Field D8 effect."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import tempfile
import sys
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
DEPLOY_RESTART_SCOPE = "AUTHORIZE_EXACT_DEPLOY_RESTART"
RECEIVE_CANDIDATE_SCOPE = "RECEIVE_CANDIDATE"
EXACT_REPAIR_SCOPE = "EXACT_MINIMAL_REPAIR_ONLY"
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


def normalized_scopes(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        scopes = (value,)
    elif isinstance(value, list) and all(isinstance(item, str) for item in value):
        scopes = tuple(value)
    else:
        raise PasskeyD8Rejected("PASSKEY_SCOPE_INVALID")
    if not scopes or len(set(scopes)) != len(scopes):
        raise PasskeyD8Rejected("PASSKEY_SCOPE_INVALID")
    admitted = {GIT_PUSH_SCOPE, DEPLOY_RESTART_SCOPE, RECEIVE_CANDIDATE_SCOPE, EXACT_REPAIR_SCOPE}
    if any(scope not in admitted for scope in scopes):
        raise PasskeyD8Rejected("PASSKEY_SCOPE_INVALID")
    return scopes


def require_platform_authenticator(response: Mapping[str, Any]) -> str:
    """Accept only the enrolled platform authenticator, never an external security key."""
    attachment = response.get("authenticatorAttachment")
    if attachment != "platform":
        raise PasskeyD8Rejected("PASSKEY_PLATFORM_AUTHENTICATOR_REQUIRED")
    return str(attachment)


def require_admitted_authenticator(
    response: Mapping[str, Any],
    credential_record: Mapping[str, Any] | None = None,
    *,
    allow_hybrid_mobile: bool = True,
) -> str:
    """Accept a device-bound authenticator or an enrolled phone reached by the hybrid transport."""
    attachment = response.get("authenticatorAttachment")
    response_body = response.get("response")
    response_transports = (
        (response_body.get("transports") or []) if isinstance(response_body, Mapping) else []
    )
    enrolled_transports = (
        (credential_record.get("transports") or []) if isinstance(credential_record, Mapping) else []
    )
    transports = {str(value) for value in [*response_transports, *enrolled_transports]}
    if attachment == "platform":
        return "platform"
    if attachment == "cross-platform" and allow_hybrid_mobile and "hybrid" in transports:
        return "cross-platform"
    raise PasskeyD8Rejected("PASSKEY_ADMITTED_AUTHENTICATOR_REQUIRED")


def _consume_once(path: Path, nonce: str, scope: str, approval_sha256: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS consumed_scopes (nonce TEXT NOT NULL, scope TEXT NOT NULL, approval_sha256 TEXT NOT NULL, consumed_at TEXT NOT NULL, PRIMARY KEY(nonce, scope))"
        )
        if scope == GIT_PUSH_SCOPE:
            legacy = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='consumed'"
            ).fetchone()
            if legacy and connection.execute(
                "SELECT 1 FROM consumed WHERE nonce=?", (nonce,)
            ).fetchone():
                raise PasskeyD8Rejected("PASSKEY_APPROVAL_REPLAYED")
        try:
            connection.execute(
                "INSERT INTO consumed_scopes(nonce, scope, approval_sha256, consumed_at) VALUES(?, ?, ?, ?)",
                (nonce, scope, approval_sha256, iso_z(utc_now())),
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
    required_scope: str = GIT_PUSH_SCOPE,
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
        approval_path = safe_runtime_ref(root, pointer.get("approval_ref"), suffix="PASSKEY_APPROVAL.json")
        approval_bytes = approval_path.read_bytes()
        approval_hash = sha256(approval_bytes)
        if approval_hash != pointer.get("approval_sha256"):
            raise PasskeyD8Rejected("PASSKEY_APPROVAL_HASH_DRIFT")
        approval = load_json(approval_path, "PASSKEY_APPROVAL_INVALID")
        if approval.get("schema_id") != PASSKEY_APPROVAL_SCHEMA or approval.get("state") != PASSKEY_APPROVAL_STATE:
            raise PasskeyD8Rejected("PASSKEY_APPROVAL_INVALID")
        scopes = normalized_scopes(approval.get("scopes", approval.get("scope")))
        if required_scope not in scopes or approval.get("single_use") is not True:
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
        claim_scopes = normalized_scopes(claims.get("scopes", claims.get("scope")))
        if claim_scopes != scopes or claims.get("authority_scope_constraints") != constraints:
            raise PasskeyD8Rejected("PASSKEY_APPROVAL_BINDING_DRIFT")
        for field in ("request_packet_sha256", "review_registration_sha256"):
            if not isinstance(claims.get(field), str) or HEX64.fullmatch(str(claims[field])) is None:
                raise PasskeyD8Rejected("PASSKEY_APPROVAL_BINDINGS_INVALID")
        if required_scope == GIT_PUSH_SCOPE:
            for field in ("base_commit", "target_tree"):
                if GIT_OID.fullmatch(str(constraints.get(field) or "")) is None:
                    raise PasskeyD8Rejected("PASSKEY_APPROVAL_BINDINGS_INVALID")
        elif required_scope == DEPLOY_RESTART_SCOPE:
            deployment = constraints.get("deployment")
            admitted_deployments = config.get("admitted_deployments")
            if (
                constraints.get("deploy") is not True
                or constraints.get("restart") is not True
                or not isinstance(admitted_deployments, list)
                or deployment not in admitted_deployments
            ):
                raise PasskeyD8Rejected("PASSKEY_APPROVAL_BINDINGS_INVALID")
        elif required_scope == RECEIVE_CANDIDATE_SCOPE:
            if constraints.get("candidate_id") != "w7tp_8d_adi_origin_cell_fusion":
                raise PasskeyD8Rejected("PASSKEY_APPROVAL_BINDINGS_INVALID")
            for field in (
                "candidate_packet_sha256",
                "skill_index_sha256",
                "skill_source_manifest_sha256",
                "dynamic_context_sha256",
            ):
                if HEX64.fullmatch(str(constraints.get(field) or "")) is None:
                    raise PasskeyD8Rejected("PASSKEY_APPROVAL_BINDINGS_INVALID")
        elif required_scope == EXACT_REPAIR_SCOPE:
            expected = {
                "repo_root": "/home/taiji_admin/Taiji_Hub",
                "branch": "agent/moving-v-v2-taiji8d-local-canary",
                "head": "dd9b24c15e97564e19dc0a069d4cc96b735773f0",
                "file": "tools/total_field_dynamic_context.py",
                "function": "build_dynamic_context",
                "intent": "閉合第一動態上下文污染入口，使 8D/ADI 譜系資格先於語義排序",
                "allowed_effect": EXACT_REPAIR_SCOPE,
                "prohibited_effects": [
                    "DEPLOY", "SERVICE_RESTART", "POINTER_CHANGE", "CANONICAL_CHANGE",
                    "RECEIVER_VERSION_CHANGE", "CROSS_LINEAGE_SUCCESSOR",
                    "V2_3_TO_V2_1_PROJECTION", "HISTORICAL_FILE_DELETE",
                    "GENERAL_REFACTOR", "GIT_PUSH",
                ],
            }
            if any(constraints.get(key) != value for key, value in expected.items()):
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
        credential_record, credential = load_credential(root, config)
        authenticator_attachment = require_admitted_authenticator(
            response,
            credential_record,
            allow_hybrid_mobile=config.get("hybrid_mobile_passkey_allowed") is True,
        )
        if approval.get("authenticator_attachment") != authenticator_attachment:
            raise PasskeyD8Rejected("PASSKEY_AUTHENTICATOR_BINDING_DRIFT")
        if websafe_decode(str(state.get("challenge") or "")) != expected_challenge:
            raise PasskeyD8Rejected("PASSKEY_CHALLENGE_BINDING_DRIFT")
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
            _consume_once(ledger, str(nonce), required_scope, approval_hash)
        return {
            "state": "PASS_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVED",
            "authority_verified": True,
            "scope": list(scopes),
            "verified_scope": required_scope,
            "authority_scope_constraints": dict(constraints),
            "authority_sha256": approval_hash,
            "issued_at": iso_z(issued),
            "expires_at": iso_z(expires),
            "signer_type": "FOUNDER_ENROLLED_USER_VERIFIED_PASSKEY",
            "authenticator_attachment": authenticator_attachment,
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument(
        "--gate-config",
        default="configs/total_field/git_push_review_gate_v1.json",
    )
    parser.add_argument("--required-scope", required=True)
    parser.add_argument("--consume", action="store_true")
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    config_path = (root / args.gate_config).resolve()
    try:
        config_path.relative_to(root / "configs" / "total_field")
        gate = load_json(config_path, "PASSKEY_CONFIG_INVALID")
        result = verify_passkey_authority(
            repo_root=root,
            config=gate.get("passkey_verifier") or {},
            consume=args.consume,
            required_scope=args.required_scope,
        )
    except (PasskeyD8Rejected, ValueError, OSError) as exc:
        result = {
            "state": "HOLD_DEVICE_PASSKEY_D8_AUTHORITY",
            "authority_verified": False,
            "reason": str(exc),
            "scope": [],
        }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("authority_verified") is True else 1


__all__ = [
    "GIT_PUSH_SCOPE",
    "DEPLOY_RESTART_SCOPE",
    "EXACT_REPAIR_SCOPE",
    "RECEIVE_CANDIDATE_SCOPE",
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
    "normalized_scopes",
    "parse_time",
    "require_admitted_authenticator",
    "require_platform_authenticator",
    "safe_runtime_ref",
    "sha256",
    "utc_now",
    "verify_passkey_authority",
]


if __name__ == "__main__":
    sys.exit(main())
