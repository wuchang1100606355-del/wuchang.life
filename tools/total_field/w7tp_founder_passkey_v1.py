#!/usr/bin/env python3
"""Verify Founder WebAuthn assertions for Total Field authorization.

This module verifies only possession/user-verification evidence. It does not grant
Total Field authority, mutate runtime state, or promote a canonical pointer.
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec


FOUNDER_USER_HANDLE = b"w7tp-total-field-founder"


class PasskeyVerificationError(ValueError):
    def __init__(self, code: str, path: str = "$") -> None:
        self.code = code
        self.path = path
        super().__init__(f"{code}:{path}")


@dataclass(frozen=True)
class VerifiedPasskey:
    credential_path: Path
    assertion_path: Path
    sign_count: int
    challenge: str


def _b64url_decode(value: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise PasskeyVerificationError("PASSKEY_B64URL_INVALID")
    pad = "=" * ((4 - len(value) % 4) % 4)
    try:
        return base64.urlsafe_b64decode(value + pad)
    except Exception as exc:
        raise PasskeyVerificationError("PASSKEY_B64URL_INVALID") from exc


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def scope_challenge(scope: dict[str, Any]) -> str:
    return _b64url_encode(hashlib.sha256(_canonical_json(scope)).digest())


def _safe_repo_path(repo_root: Path, ref: str, path: str) -> Path:
    rel = Path(ref)
    if rel.is_absolute() or ".." in rel.parts:
        raise PasskeyVerificationError("PASSKEY_UNSAFE_REF", path)
    root = repo_root.resolve()
    resolved = (root / rel).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise PasskeyVerificationError("PASSKEY_REF_ESCAPE", path) from exc
    if resolved.is_symlink():
        raise PasskeyVerificationError("PASSKEY_SYMLINK_REF", path)
    return resolved


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PasskeyVerificationError(f"PASSKEY_{label}_INVALID") from exc
    if not isinstance(value, dict):
        raise PasskeyVerificationError(f"PASSKEY_{label}_INVALID")
    return value


def _read_cbor_uint(data: bytes, offset: int) -> tuple[int, int, int]:
    if offset >= len(data):
        raise PasskeyVerificationError("PASSKEY_COSE_KEY_TRUNCATED")
    first = data[offset]
    major = first >> 5
    add = first & 0x1F
    offset += 1
    if add < 24:
        return major, add, offset
    if add == 24:
        if offset + 1 > len(data):
            raise PasskeyVerificationError("PASSKEY_COSE_KEY_TRUNCATED")
        return major, data[offset], offset + 1
    if add == 25:
        if offset + 2 > len(data):
            raise PasskeyVerificationError("PASSKEY_COSE_KEY_TRUNCATED")
        return major, int.from_bytes(data[offset:offset + 2], "big"), offset + 2
    raise PasskeyVerificationError("PASSKEY_COSE_KEY_UNSUPPORTED_CBOR")


def _read_cbor_item(data: bytes, offset: int) -> tuple[Any, int]:
    major, value, offset = _read_cbor_uint(data, offset)
    if major == 0:
        return value, offset
    if major == 1:
        return -1 - value, offset
    if major == 2:
        end = offset + value
        if end > len(data):
            raise PasskeyVerificationError("PASSKEY_COSE_KEY_TRUNCATED")
        return data[offset:end], end
    if major == 5:
        result: dict[Any, Any] = {}
        for _ in range(value):
            key, offset = _read_cbor_item(data, offset)
            item, offset = _read_cbor_item(data, offset)
            result[key] = item
        return result, offset
    raise PasskeyVerificationError("PASSKEY_COSE_KEY_UNSUPPORTED_CBOR")


def _credential_public_key(credential: dict[str, Any]) -> tuple[ec.EllipticCurvePublicKey, bytes]:
    raw = _b64url_decode(credential.get("attested_credential_data_b64url"))
    if len(raw) < 18:
        raise PasskeyVerificationError("PASSKEY_ATTESTED_CREDENTIAL_DATA_INVALID")
    credential_len = int.from_bytes(raw[16:18], "big")
    end = 18 + credential_len
    if end > len(raw):
        raise PasskeyVerificationError("PASSKEY_ATTESTED_CREDENTIAL_DATA_INVALID")
    credential_id = raw[18:end]
    cose, cose_end = _read_cbor_item(raw, end)
    if cose_end != len(raw) or not isinstance(cose, dict):
        raise PasskeyVerificationError("PASSKEY_COSE_KEY_INVALID")
    if cose.get(1) != 2 or cose.get(3) != -7 or cose.get(-1) != 1:
        raise PasskeyVerificationError("PASSKEY_COSE_KEY_NOT_ES256_P256")
    x = cose.get(-2)
    y = cose.get(-3)
    if not isinstance(x, bytes) or not isinstance(y, bytes) or len(x) != 32 or len(y) != 32:
        raise PasskeyVerificationError("PASSKEY_COSE_KEY_COORDINATE_INVALID")
    numbers = ec.EllipticCurvePublicNumbers(
        int.from_bytes(x, "big"),
        int.from_bytes(y, "big"),
        ec.SECP256R1(),
    )
    return numbers.public_key(), credential_id


def verify_assertion(
    credential: dict[str, Any],
    assertion_wrapper: dict[str, Any],
    *,
    expected_challenge: str,
) -> int:
    if credential.get("state") != "ENROLLED_USER_VERIFIED" or credential.get("user_verification") is not True:
        raise PasskeyVerificationError("PASSKEY_CREDENTIAL_NOT_USER_VERIFIED")
    rp_id = credential.get("rp_id")
    expected_origin = credential.get("expected_origin")
    if not isinstance(rp_id, str) or not isinstance(expected_origin, str):
        raise PasskeyVerificationError("PASSKEY_CREDENTIAL_SCOPE_INVALID")
    public_key, credential_id = _credential_public_key(credential)
    if _b64url_decode(credential.get("credential_id_b64url")) != credential_id:
        raise PasskeyVerificationError("PASSKEY_CREDENTIAL_ID_BINDING_INVALID")

    if assertion_wrapper.get("state") != "SEALED_WEBAUTHN_ASSERTION":
        raise PasskeyVerificationError("PASSKEY_ASSERTION_STATE_INVALID")
    if assertion_wrapper.get("webauthn_state", {}).get("challenge") != expected_challenge:
        raise PasskeyVerificationError("PASSKEY_ASSERTION_CHALLENGE_WRAPPER_MISMATCH")
    if assertion_wrapper.get("webauthn_state", {}).get("user_verification") != "required":
        raise PasskeyVerificationError("PASSKEY_ASSERTION_UV_REQUIREMENT_MISSING")

    assertion = assertion_wrapper.get("assertion")
    if not isinstance(assertion, dict) or assertion.get("type") != "public-key":
        raise PasskeyVerificationError("PASSKEY_ASSERTION_FORMAT_INVALID")
    if assertion.get("authenticatorAttachment") != "platform":
        raise PasskeyVerificationError("PASSKEY_ASSERTION_NOT_PLATFORM")
    if assertion.get("id") != credential.get("credential_id_b64url") or assertion.get("rawId") != assertion.get("id"):
        raise PasskeyVerificationError("PASSKEY_ASSERTION_CREDENTIAL_ID_MISMATCH")

    response = assertion.get("response")
    if not isinstance(response, dict):
        raise PasskeyVerificationError("PASSKEY_ASSERTION_RESPONSE_INVALID")
    client_data_raw = _b64url_decode(response.get("clientDataJSON"))
    try:
        client = json.loads(client_data_raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PasskeyVerificationError("PASSKEY_CLIENT_DATA_INVALID") from exc
    if client.get("type") != "webauthn.get":
        raise PasskeyVerificationError("PASSKEY_CLIENT_DATA_TYPE_INVALID")
    if client.get("challenge") != expected_challenge:
        raise PasskeyVerificationError("PASSKEY_CHALLENGE_MISMATCH")
    if client.get("origin") != expected_origin or client.get("crossOrigin") is not False:
        raise PasskeyVerificationError("PASSKEY_ORIGIN_MISMATCH")

    auth_data = _b64url_decode(response.get("authenticatorData"))
    if len(auth_data) < 37:
        raise PasskeyVerificationError("PASSKEY_AUTHENTICATOR_DATA_INVALID")
    if auth_data[:32] != hashlib.sha256(rp_id.encode("utf-8")).digest():
        raise PasskeyVerificationError("PASSKEY_RP_ID_HASH_MISMATCH")
    flags = auth_data[32]
    if flags & 0x01 == 0:
        raise PasskeyVerificationError("PASSKEY_USER_PRESENCE_MISSING")
    if flags & 0x04 == 0:
        raise PasskeyVerificationError("PASSKEY_USER_VERIFICATION_MISSING")
    sign_count = int.from_bytes(auth_data[33:37], "big")
    enrolled_count = int(credential.get("sign_count", 0))
    if enrolled_count and sign_count and sign_count <= enrolled_count:
        raise PasskeyVerificationError("PASSKEY_SIGN_COUNT_NOT_ADVANCED")

    user_handle = response.get("userHandle")
    if user_handle is not None and _b64url_decode(user_handle) != FOUNDER_USER_HANDLE:
        raise PasskeyVerificationError("PASSKEY_USER_HANDLE_MISMATCH")
    signature = _b64url_decode(response.get("signature"))
    signed = auth_data + hashlib.sha256(client_data_raw).digest()
    try:
        public_key.verify(signature, signed, ec.ECDSA(hashes.SHA256()))
    except InvalidSignature as exc:
        raise PasskeyVerificationError("PASSKEY_SIGNATURE_INVALID") from exc
    return sign_count


def verify_authorization_passkey(
    repo_root: Path,
    authorization: dict[str, Any],
    *,
    scope: dict[str, Any],
) -> VerifiedPasskey:
    webauthn = authorization.get("webauthn")
    if not isinstance(webauthn, dict):
        raise PasskeyVerificationError("PASSKEY_AUTHORIZATION_BINDING_MISSING", "$.webauthn")
    expected = scope_challenge(scope)
    if webauthn.get("scope_challenge") != expected:
        raise PasskeyVerificationError("PASSKEY_SCOPE_CHALLENGE_MISMATCH", "$.webauthn.scope_challenge")
    credential_path = _safe_repo_path(repo_root, webauthn.get("credential_ref"), "$.webauthn.credential_ref")
    assertion_path = _safe_repo_path(repo_root, webauthn.get("assertion_ref"), "$.webauthn.assertion_ref")
    for path, expected_sha, field in (
        (credential_path, webauthn.get("credential_sha256"), "$.webauthn.credential_sha256"),
        (assertion_path, webauthn.get("assertion_sha256"), "$.webauthn.assertion_sha256"),
    ):
        if not path.is_file() or path.is_symlink() or _sha256_file(path) != expected_sha:
            raise PasskeyVerificationError("PASSKEY_BOUND_FILE_HASH_MISMATCH", field)
    credential = _read_json(credential_path, "CREDENTIAL")
    assertion = _read_json(assertion_path, "ASSERTION")
    sign_count = verify_assertion(credential, assertion, expected_challenge=expected)
    return VerifiedPasskey(
        credential_path=credential_path,
        assertion_path=assertion_path,
        sign_count=sign_count,
        challenge=expected,
    )
