"""Trusted, reference-only Odoo identity projection for the shared 9107 runtime."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from tools.total_field.w7tp_field_application_runtime import FieldApplicationError

from .canonical_hash import canonical_sha256, normalize_content
from .identity_prefix import (
    SCHEMA_VERSION as IDENTITY_PREFIX_VERSION,
    verify_natural_person_identity_prefix,
)


PROJECTION_SCHEMA_VERSION = "W7TP-ODOO-IDENTITY-PROJECTION/1.0"
CANONICAL_IDENTITY_REF = "canonical_ref:W7TP_8D_IDENTITY_PACKET"
TRUSTED_ISSUER_REF = "issuer_ref:taiji01:odoo-member-authority"
TRUSTED_BOUNDARY_VALUE = "caddy:wuchang.life:odoo-forward-auth:v1"
BOUNDARY_HEADER = "X-W7TP-Projection-Boundary"
MAX_PROJECTION_TTL_SECONDS = 300
PROJECTION_FIELDS = (
    "schema_version",
    "identity_ref",
    "canonical_ref",
    "prefix_ref",
    "prefix_version",
    "issuer_ref",
    "projection_ref",
    "projection_sha256",
    "issued_at",
    "expires_at",
    "nonce",
)
HEADER_BY_FIELD = {
    "schema_version": "X-W7TP-Identity-Schema",
    "identity_ref": "X-W7TP-Identity-Ref",
    "canonical_ref": "X-W7TP-Canonical-Ref",
    "prefix_ref": "X-W7TP-Prefix-Ref",
    "prefix_version": "X-W7TP-Prefix-Version",
    "issuer_ref": "X-W7TP-Issuer-Ref",
    "projection_ref": "X-W7TP-Projection-Ref",
    "projection_sha256": "X-W7TP-Projection-SHA256",
    "issued_at": "X-W7TP-Issued-At",
    "expires_at": "X-W7TP-Expires-At",
    "nonce": "X-W7TP-Nonce",
}
PROJECTION_HEADER_NAMES = tuple(HEADER_BY_FIELD.values())
IDENTITY_REF = re.compile(r"^identity_packet_ref:sha256:[0-9a-f]{64}$")
PREFIX_REF = re.compile(r"^identity_prefix_ref:sha256:[0-9a-f]{64}$")
PROJECTION_REF = re.compile(r"^identity_projection_ref:sha256:[0-9a-f]{64}$")
NONCE_REF = re.compile(r"^nonce_ref:sha256:[0-9a-f]{64}$")
SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")

IdentityPrefixResolver = Callable[[str], Mapping[str, Any] | None]


def _projection_hash_basis(projection: Mapping[str, Any]) -> dict[str, Any]:
    basis = normalize_content(dict(projection))
    basis.pop("projection_sha256", None)
    return basis


def _projection_ref_basis(projection: Mapping[str, Any]) -> dict[str, Any]:
    basis = _projection_hash_basis(projection)
    basis.pop("projection_ref", None)
    return basis


def projection_ref_for(projection: Mapping[str, Any]) -> str:
    """Return the deterministic projection reference without trusting its hash."""

    return "identity_projection_ref:sha256:" + canonical_sha256(
        _projection_ref_basis(projection)
    )


def projection_sha256_for(projection: Mapping[str, Any]) -> str:
    """Return the canonical integrity hash with its own field removed."""

    return canonical_sha256(_projection_hash_basis(projection))


def prefix_ref_for(packet: Mapping[str, Any]) -> str:
    """Return the stable reference of an already-issued immutable prefix."""

    d8 = packet.get("D8")
    prefix_sha256 = d8.get("prefix_sha256") if isinstance(d8, Mapping) else None
    if not isinstance(prefix_sha256, str) or SHA256_HEX.fullmatch(prefix_sha256) is None:
        raise FieldApplicationError("IDENTITY_PREFIX_SHA256_INVALID", "$.D8.prefix_sha256")
    return f"identity_prefix_ref:sha256:{prefix_sha256}"


def _parse_utc(value: Any, path: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise FieldApplicationError("IDENTITY_PROJECTION_TIME_INVALID", path)
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise FieldApplicationError("IDENTITY_PROJECTION_TIME_INVALID", path) from exc
    if parsed.tzinfo != timezone.utc:
        raise FieldApplicationError("IDENTITY_PROJECTION_TIME_INVALID", path)
    return parsed


def _projection_from_headers(headers: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(headers, Mapping):
        raise FieldApplicationError("IDENTITY_PROJECTION_HEADERS_REQUIRED")
    normalized = {str(key).casefold(): value for key, value in headers.items()}
    projection: dict[str, str] = {}
    for field, header in HEADER_BY_FIELD.items():
        value = normalized.get(header.casefold())
        if not isinstance(value, str) or not value.strip():
            raise FieldApplicationError(
                "IDENTITY_PROJECTION_HEADER_REQUIRED",
                f"$.headers.{header}",
            )
        projection[field] = value.strip()
    return projection


def projection_headers_present(headers: Mapping[str, Any]) -> bool:
    """Return whether an HTTP request carries any reserved projection header."""

    normalized = {str(key).casefold() for key in headers}
    return BOUNDARY_HEADER.casefold() in normalized or any(
        header.casefold() in normalized for header in PROJECTION_HEADER_NAMES
    )


def trusted_caddy_boundary(headers: Mapping[str, Any], peer_ip: str) -> bool:
    """Trust only the loopback proxy plus its post-sanitization marker."""

    if str(peer_ip) not in {"127.0.0.1", "::1"}:
        return False
    normalized = {str(key).casefold(): value for key, value in headers.items()}
    return normalized.get(BOUNDARY_HEADER.casefold()) == TRUSTED_BOUNDARY_VALUE


def _validate_projection_shape(projection: Mapping[str, Any]) -> None:
    if set(projection) != set(PROJECTION_FIELDS):
        raise FieldApplicationError("IDENTITY_PROJECTION_SHAPE_INVALID")
    exact = {
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "canonical_ref": CANONICAL_IDENTITY_REF,
        "prefix_version": IDENTITY_PREFIX_VERSION,
        "issuer_ref": TRUSTED_ISSUER_REF,
    }
    for field, expected in exact.items():
        if projection.get(field) != expected:
            raise FieldApplicationError(
                "IDENTITY_PROJECTION_FIELD_INVALID", f"$.{field}"
            )
    patterns = {
        "identity_ref": IDENTITY_REF,
        "prefix_ref": PREFIX_REF,
        "projection_ref": PROJECTION_REF,
        "projection_sha256": SHA256_HEX,
        "nonce": NONCE_REF,
    }
    for field, pattern in patterns.items():
        value = projection.get(field)
        if not isinstance(value, str) or pattern.fullmatch(value) is None:
            raise FieldApplicationError(
                "IDENTITY_PROJECTION_FIELD_INVALID", f"$.{field}"
            )


def verify_trusted_identity_projection(
    headers: Mapping[str, Any],
    *,
    trusted_boundary: bool,
    identity_prefix_resolver: IdentityPrefixResolver | None,
    identity_registry_snapshot: Mapping[str, Any] | None,
    now: str | None = None,
) -> dict[str, Any]:
    """Verify the Caddy-authenticated projection and resolve an existing prefix.

    Header values alone never establish trust.  The 9107 transport middleware
    supplies ``trusted_boundary`` only after the loopback Caddy boundary and its
    server-injected marker both match.  The resolver is read-only and must return
    an already-issued prefix; this function never creates an identity or prefix.
    """

    if trusted_boundary is not True:
        raise FieldApplicationError("IDENTITY_PROJECTION_UNTRUSTED_SOURCE")
    projection = _projection_from_headers(headers)
    _validate_projection_shape(projection)
    if projection["projection_ref"] != projection_ref_for(projection):
        raise FieldApplicationError("IDENTITY_PROJECTION_REF_MISMATCH")
    if projection["projection_sha256"] != projection_sha256_for(projection):
        raise FieldApplicationError("IDENTITY_PROJECTION_SHA256_MISMATCH")

    issued_at = _parse_utc(projection["issued_at"], "$.issued_at")
    expires_at = _parse_utc(projection["expires_at"], "$.expires_at")
    observed_at = (
        _parse_utc(now, "$.now") if now is not None else datetime.now(timezone.utc)
    )
    ttl_seconds = (expires_at - issued_at).total_seconds()
    if ttl_seconds <= 0 or ttl_seconds > MAX_PROJECTION_TTL_SECONDS:
        raise FieldApplicationError("IDENTITY_PROJECTION_TTL_INVALID")
    if observed_at < issued_at:
        raise FieldApplicationError("IDENTITY_PROJECTION_NOT_YET_VALID")
    if observed_at >= expires_at:
        raise FieldApplicationError("IDENTITY_PROJECTION_EXPIRED")
    if identity_prefix_resolver is None:
        raise FieldApplicationError("IDENTITY_PREFIX_RESOLVER_REQUIRED")
    prefix = identity_prefix_resolver(projection["prefix_ref"])
    if not isinstance(prefix, Mapping):
        raise FieldApplicationError("IDENTITY_PREFIX_NOT_FOUND")
    if prefix_ref_for(prefix) != projection["prefix_ref"]:
        raise FieldApplicationError("IDENTITY_PREFIX_REF_MISMATCH")
    d1 = prefix.get("D1")
    if not isinstance(d1, Mapping) or d1.get("identity_packet_ref") != projection[
        "identity_ref"
    ]:
        raise FieldApplicationError("IDENTITY_PROJECTION_IDENTITY_MISMATCH")

    verification = verify_natural_person_identity_prefix(
        prefix,
        identity_registry_snapshot=identity_registry_snapshot,
    )
    if verification["state"] != "PASS_IDENTITY_PREFIX_VERIFIED":
        raise FieldApplicationError(verification["state"])
    entries = (
        identity_registry_snapshot.get("entries")
        if isinstance(identity_registry_snapshot, Mapping)
        else None
    )
    if not isinstance(entries, list):
        raise FieldApplicationError("IDENTITY_PREFIX_REGISTRY_EVIDENCE_REQUIRED")
    registry_entry_fields = {
        "protected_plaintext_binding_ref",
        "identity_packet_ref",
        "identity_prefix_ref",
    }
    for index, item in enumerate(entries):
        if not isinstance(item, Mapping) or set(item) != registry_entry_fields:
            raise FieldApplicationError(
                "IDENTITY_PREFIX_REGISTRY_REF_ONLY_REQUIRED",
                f"$.identity_registry_snapshot.entries[{index}]",
            )
        if (
            not isinstance(item.get("protected_plaintext_binding_ref"), str)
            or not isinstance(item.get("identity_packet_ref"), str)
            or IDENTITY_REF.fullmatch(item["identity_packet_ref"]) is None
            or not isinstance(item.get("identity_prefix_ref"), str)
            or PREFIX_REF.fullmatch(item["identity_prefix_ref"]) is None
        ):
            raise FieldApplicationError(
                "IDENTITY_PREFIX_REGISTRY_REF_ONLY_REQUIRED",
                f"$.identity_registry_snapshot.entries[{index}]",
            )
    registered_prefix_refs = {
        item.get("identity_prefix_ref")
        for item in entries
        if isinstance(item, Mapping)
        and item.get("identity_packet_ref") == projection["identity_ref"]
    }
    if not registered_prefix_refs:
        raise FieldApplicationError("IDENTITY_PREFIX_REGISTRY_EVIDENCE_REQUIRED")
    if registered_prefix_refs != {projection["prefix_ref"]}:
        raise FieldApplicationError("HOLD_IDENTITY_PREFIX_CONFLICT")
    return {
        "projection": normalize_content(projection),
        "identity_prefix": normalize_content(dict(prefix)),
        "identity_registry_snapshot": normalize_content(
            dict(identity_registry_snapshot)
        ),
        "state": "PASS_TRUSTED_IDENTITY_PROJECTION",
        "member_plaintext_included": False,
        "secret_included": False,
    }


__all__ = [
    "BOUNDARY_HEADER",
    "CANONICAL_IDENTITY_REF",
    "HEADER_BY_FIELD",
    "IDENTITY_PREFIX_VERSION",
    "MAX_PROJECTION_TTL_SECONDS",
    "PROJECTION_FIELDS",
    "PROJECTION_HEADER_NAMES",
    "PROJECTION_SCHEMA_VERSION",
    "TRUSTED_BOUNDARY_VALUE",
    "TRUSTED_ISSUER_REF",
    "prefix_ref_for",
    "projection_headers_present",
    "projection_ref_for",
    "projection_sha256_for",
    "trusted_caddy_boundary",
    "verify_trusted_identity_projection",
]
