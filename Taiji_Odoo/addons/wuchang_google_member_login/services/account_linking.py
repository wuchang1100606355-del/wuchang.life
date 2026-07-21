"""Reference-only Google account-linking and callback safety rules."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone


CANONICAL_CALLBACK_URL = "https://wuchang.life/google/member/callback"
PUBLIC_HOME_RETURN = "https://wuchang.life/"
LINK_STATES = {
    "PROVIDER_LINK_FOUND",
    "LINKING_PENDING",
    "REAUTHENTICATION_REQUIRED",
    "EXPLICIT_LINK_CONSENT_REQUIRED",
    "HUMAN_REVIEW_REQUIRED",
    "LINK_DENIED",
    "LINK_CONFIRMED",
}
IDENTITY_PROJECTION_SCHEMA_VERSION = "W7TP-ODOO-IDENTITY-PROJECTION/1.0"
IDENTITY_PACKET_CANONICAL_REF = "canonical_ref:W7TP_8D_IDENTITY_PACKET"
IDENTITY_PREFIX_VERSION = "W7TP-NATURAL-PERSON-IDENTITY-PREFIX/1.0"
IDENTITY_PROJECTION_ISSUER_REF = "issuer_ref:taiji01:odoo-member-authority"
IDENTITY_PROJECTION_HEADERS = {
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
_LOCAL_SUBJECT_REF = re.compile(r"^subject:sha256:[0-9a-f]{64}$")
_PREFIX_REF = re.compile(r"^identity_prefix_ref:sha256:[0-9a-f]{64}$")
_NONCE_REF = re.compile(r"^nonce_ref:sha256:[0-9a-f]{64}$")


def sha256_ref(namespace: str, value: str) -> str:
    if not value:
        raise ValueError(f"{namespace}_required")
    return f"{namespace}:sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def google_link_state(
    *,
    provider_link_found: bool,
    linking_started: bool = False,
    reauthenticated: bool = False,
    explicit_link_consent: bool = False,
    human_review_required: bool = False,
    human_review_approved: bool = False,
    denied: bool = False,
) -> str:
    if denied:
        return "LINK_DENIED"
    if provider_link_found:
        return "PROVIDER_LINK_FOUND"
    if not linking_started:
        return "LINKING_PENDING"
    if not reauthenticated:
        return "REAUTHENTICATION_REQUIRED"
    if not explicit_link_consent:
        return "EXPLICIT_LINK_CONSENT_REQUIRED"
    if human_review_required and not human_review_approved:
        return "HUMAN_REVIEW_REQUIRED"
    return "LINK_CONFIRMED"


def callback_security_decision(
    *,
    expected_state: str | None,
    received_state: str | None,
    expected_nonce: str | None,
    token_claims: dict,
    expected_audience: str,
    userinfo_subject: str | None,
    callback_url: str,
) -> dict[str, str]:
    if callback_url != CANONICAL_CALLBACK_URL:
        return {"decision": "DENY", "reason": "CALLBACK_HOST_MISMATCH"}
    if not expected_state or received_state != expected_state:
        return {"decision": "DENY", "reason": "STATE_MISMATCH"}
    if not expected_nonce or token_claims.get("nonce") != expected_nonce:
        return {"decision": "DENY", "reason": "NONCE_MISMATCH"}
    audience = token_claims.get("aud")
    audiences = set(audience if isinstance(audience, list) else [audience])
    if expected_audience not in audiences:
        return {"decision": "DENY", "reason": "AUDIENCE_MISMATCH"}
    token_subject = token_claims.get("sub")
    if not token_subject or token_subject != userinfo_subject:
        return {"decision": "DENY", "reason": "PROVIDER_SUBJECT_MISMATCH"}
    return {"decision": "PASS", "reason": "CALLBACK_SECURITY_VERIFIED"}


def transient_link_context(userinfo: dict, authority_resolution: dict) -> dict:
    subject = str(userinfo.get("sub") or "")
    email = str(userinfo.get("email") or "").strip().lower()
    return {
        "provider_name": "GOOGLE",
        "provider_subject_reference": sha256_ref("provider:google", subject),
        "local_subject_reference": authority_resolution.get("local_subject_reference"),
        "link_state": authority_resolution.get("link_state") or "LINKING_PENDING",
        "consent_reference": authority_resolution.get("consent_reference"),
        "email_candidate_signal": sha256_ref("candidate:email", email) if email else None,
        "verifier_result": authority_resolution.get("verifier_result") or "HOLD",
        "public_home_return": PUBLIC_HOME_RETURN,
    }


def _canonical_sha256(value: dict) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("identity_projection_time_invalid")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("identity_projection_time_invalid") from exc
    if parsed.tzinfo != timezone.utc:
        raise ValueError("identity_projection_time_invalid")
    return parsed


def identity_packet_ref_from_link_context(link_context: dict) -> str:
    """Derive one stable packet ref from the existing opaque local subject ref."""

    if link_context.get("link_state") not in {"PROVIDER_LINK_FOUND", "LINK_CONFIRMED"}:
        raise ValueError("identity_projection_link_not_verified")
    if link_context.get("verifier_result") != "PASS":
        raise ValueError("identity_projection_verifier_not_pass")
    local_ref = link_context.get("local_subject_reference")
    if not isinstance(local_ref, str) or _LOCAL_SUBJECT_REF.fullmatch(local_ref) is None:
        raise ValueError("identity_projection_local_subject_ref_invalid")
    return "identity_packet_ref:sha256:" + hashlib.sha256(
        local_ref.encode("utf-8")
    ).hexdigest()


def build_verified_identity_projection(
    link_context: dict,
    *,
    prefix_ref: str,
    issued_at: str,
    expires_at: str,
    nonce: str,
) -> dict[str, str]:
    """Build a short-lived ref-only projection after local Odoo verification."""

    identity_ref = identity_packet_ref_from_link_context(link_context)
    if not isinstance(prefix_ref, str) or _PREFIX_REF.fullmatch(prefix_ref) is None:
        raise ValueError("identity_projection_prefix_ref_invalid")
    if not isinstance(nonce, str) or _NONCE_REF.fullmatch(nonce) is None:
        raise ValueError("identity_projection_nonce_ref_invalid")
    issued = _utc(issued_at)
    expires = _utc(expires_at)
    ttl = (expires - issued).total_seconds()
    if ttl <= 0 or ttl > 300:
        raise ValueError("identity_projection_ttl_invalid")
    projection = {
        "schema_version": IDENTITY_PROJECTION_SCHEMA_VERSION,
        "identity_ref": identity_ref,
        "canonical_ref": IDENTITY_PACKET_CANONICAL_REF,
        "prefix_ref": prefix_ref,
        "prefix_version": IDENTITY_PREFIX_VERSION,
        "issuer_ref": IDENTITY_PROJECTION_ISSUER_REF,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "nonce": nonce,
    }
    projection["projection_ref"] = "identity_projection_ref:sha256:" + _canonical_sha256(
        projection
    )
    projection["projection_sha256"] = _canonical_sha256(projection)
    return projection


def identity_projection_response_headers(
    projection: dict[str, str],
) -> dict[str, str]:
    """Return the exact Odoo response-header allowlist consumed by Caddy."""

    if set(projection) != set(IDENTITY_PROJECTION_HEADERS):
        raise ValueError("identity_projection_shape_invalid")
    return {
        header: projection[field]
        for field, header in IDENTITY_PROJECTION_HEADERS.items()
    }
