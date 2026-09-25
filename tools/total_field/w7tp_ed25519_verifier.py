#!/usr/bin/env python3
"""Fail-closed Ed25519 verification and Stage B signed-byte binding.

This module verifies signatures only.  It never reads or creates private keys,
does not decide whether a public key is trusted, and does not grant authority.
Trust, revocation, role, and nonce decisions remain external governance gates.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
except ImportError:  # pragma: no cover - exercised only on an unsupported host
    InvalidSignature = Exception  # type: ignore[assignment,misc]
    Ed25519PublicKey = None  # type: ignore[assignment,misc]

from tools.total_field.w7tp_true8d_contract_sandbox import canonical_json


DOMAIN_SEPARATOR = "W7TP_TOTAL_FIELD_V2"
SIGNATURE_ALGORITHM = "ED25519"
SIGNATURE_ENCODING = "RAW_64_BYTES_LOWERCASE_HEX"
SIGNED_BYTES_FORMAT = "INTEGER_ONLY_RFC8785_COMPATIBLE_SUBSET_JCS_ARRAY_UTF8"
VERIFIER_REF = "tools/total_field/w7tp_ed25519_verifier.py#validate_stage_b_signature"

_LOWER_HEX = re.compile(r"^[0-9a-f]+$")
_FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")
_PLACEHOLDER_SIGNATURES = {"0" * 128, "a" * 128}
_PLACEHOLDER_FINGERPRINTS = {"0" * 64, "1" * 64, "a" * 64}
_PLACEHOLDER_PUBLIC_KEYS = {bytes(32), bytes.fromhex("11" * 32), bytes.fromhex("aa" * 32)}


@dataclass(frozen=True)
class VerificationResult:
    """Stable verification result that never contains secret material."""

    valid: bool
    reason_code: str
    public_key_fingerprint: str | None


class SignedBytesBuildError(ValueError):
    """Stable fail-closed error for invalid Stage B signing input."""

    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


def _result(
    valid: bool,
    reason_code: str,
    fingerprint: str | None = None,
) -> VerificationResult:
    return VerificationResult(valid, reason_code, fingerprint)


def _fingerprint(public_key_bytes: bytes) -> str:
    return hashlib.sha256(public_key_bytes).hexdigest()


def build_stage_b_signed_bytes(
    *,
    domain_separator: str,
    packet_canonical_id: str,
    stage_b_object_without_signature: Mapping[str, Any],
) -> bytes:
    """Build the sole governed Stage B Ed25519 input byte sequence."""

    if not isinstance(domain_separator, str) or not domain_separator:
        raise SignedBytesBuildError("HOLD_STAGE_B_DOMAIN_SEPARATOR_INVALID")
    if not isinstance(packet_canonical_id, str) or not packet_canonical_id:
        raise SignedBytesBuildError("HOLD_STAGE_B_PACKET_CANONICAL_ID_INVALID")
    if not isinstance(stage_b_object_without_signature, Mapping):
        raise SignedBytesBuildError("HOLD_STAGE_B_OBJECT_INVALID")
    try:
        if "signature" in stage_b_object_without_signature:
            raise SignedBytesBuildError("HOLD_STAGE_B_SIGNATURE_FIELD_PRESENT")
        signing_array = [
            domain_separator,
            packet_canonical_id,
            dict(stage_b_object_without_signature),
        ]
        return canonical_json(signing_array).encode("utf-8")
    except SignedBytesBuildError:
        raise
    except Exception as exc:
        raise SignedBytesBuildError(
            "HOLD_SIGNED_BYTES_CANONICALIZATION_UNRESOLVED"
        ) from exc


def verify_ed25519_signature(
    *,
    public_key_bytes: bytes,
    signature_hex: str,
    signed_bytes: bytes,
) -> VerificationResult:
    """Verify one raw Ed25519 signature and return a stable fail-closed result."""

    if not isinstance(public_key_bytes, bytes) or len(public_key_bytes) != 32:
        return _result(False, "HOLD_ED25519_PUBLIC_KEY_INVALID")

    fingerprint = _fingerprint(public_key_bytes)
    if public_key_bytes in _PLACEHOLDER_PUBLIC_KEYS:
        return _result(
            False,
            "BLOCK_ED25519_PLACEHOLDER_TRUST_MATERIAL",
            fingerprint,
        )

    if not isinstance(signed_bytes, bytes):
        return _result(False, "HOLD_ED25519_SIGNED_BYTES_INVALID", fingerprint)
    if not isinstance(signature_hex, str) or not signature_hex:
        return _result(
            False,
            "HOLD_ED25519_SIGNATURE_ENCODING_INVALID",
            fingerprint,
        )
    if _LOWER_HEX.fullmatch(signature_hex) is None or len(signature_hex) % 2:
        return _result(
            False,
            "HOLD_ED25519_SIGNATURE_ENCODING_INVALID",
            fingerprint,
        )
    if len(signature_hex) != 128:
        return _result(
            False,
            "HOLD_ED25519_SIGNATURE_LENGTH_INVALID",
            fingerprint,
        )
    if signature_hex in _PLACEHOLDER_SIGNATURES:
        return _result(
            False,
            "BLOCK_ED25519_PLACEHOLDER_TRUST_MATERIAL",
            fingerprint,
        )

    signature = bytes.fromhex(signature_hex)
    if len(signature) != 64:  # Defensive: the exact hex check above already closes this.
        return _result(
            False,
            "HOLD_ED25519_SIGNATURE_LENGTH_INVALID",
            fingerprint,
        )
    if Ed25519PublicKey is None:
        return _result(False, "HOLD_ED25519_LIBRARY_NOT_AVAILABLE", fingerprint)

    try:
        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        public_key.verify(signature, signed_bytes)
    except InvalidSignature:
        return _result(False, "REJECT_ED25519_SIGNATURE_INVALID", fingerprint)
    except (TypeError, ValueError):
        return _result(False, "HOLD_ED25519_PUBLIC_KEY_INVALID", fingerprint)
    except Exception:
        return _result(False, "HOLD_ED25519_VERIFIER_FAILURE", fingerprint)

    return _result(True, "PASS_ED25519_SIGNATURE_VALID", fingerprint)


def validate_stage_b_signature(
    *,
    domain_separator: str,
    packet_canonical_id: str,
    stage_b_object_without_signature: Mapping[str, Any],
    public_key_ref: str,
    public_key_resolver: Callable[[str], bytes | None],
    expected_public_key_fingerprint: str,
    signature_hex: str,
) -> VerificationResult:
    """Stage B entrypoint: build bytes, resolve key, bind fingerprint, verify."""

    try:
        signed_bytes = build_stage_b_signed_bytes(
            domain_separator=domain_separator,
            packet_canonical_id=packet_canonical_id,
            stage_b_object_without_signature=stage_b_object_without_signature,
        )
    except SignedBytesBuildError as exc:
        return _result(False, exc.reason_code)

    if not isinstance(public_key_ref, str) or not public_key_ref:
        return _result(False, "HOLD_ED25519_PUBLIC_KEY_REF_INVALID")
    if not callable(public_key_resolver):
        return _result(False, "HOLD_ED25519_PUBLIC_KEY_RESOLVER_INVALID")

    try:
        public_key_bytes = public_key_resolver(public_key_ref)
    except Exception:
        return _result(False, "HOLD_ED25519_PUBLIC_KEY_UNAVAILABLE")
    if not isinstance(public_key_bytes, bytes) or len(public_key_bytes) != 32:
        return _result(False, "HOLD_ED25519_PUBLIC_KEY_INVALID")

    fingerprint = _fingerprint(public_key_bytes)
    if public_key_bytes in _PLACEHOLDER_PUBLIC_KEYS:
        return _result(
            False,
            "BLOCK_ED25519_PLACEHOLDER_TRUST_MATERIAL",
            fingerprint,
        )
    if (
        not isinstance(expected_public_key_fingerprint, str)
        or _FINGERPRINT.fullmatch(expected_public_key_fingerprint) is None
    ):
        return _result(
            False,
            "HOLD_ED25519_PUBLIC_KEY_FINGERPRINT_INVALID",
            fingerprint,
        )
    if expected_public_key_fingerprint in _PLACEHOLDER_FINGERPRINTS:
        return _result(
            False,
            "BLOCK_ED25519_PLACEHOLDER_TRUST_MATERIAL",
            fingerprint,
        )
    if fingerprint != expected_public_key_fingerprint:
        return _result(
            False,
            "REJECT_ED25519_PUBLIC_KEY_FINGERPRINT_MISMATCH",
            fingerprint,
        )

    return verify_ed25519_signature(
        public_key_bytes=public_key_bytes,
        signature_hex=signature_hex,
        signed_bytes=signed_bytes,
    )

