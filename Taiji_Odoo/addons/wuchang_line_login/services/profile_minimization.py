"""LINE callback verification and reference-only session minimization."""

from __future__ import annotations

import hashlib
import json


CANONICAL_CALLBACK_URL = "https://member.wuchang.life/line/callback"
PUBLIC_HOME_RETURN = "https://wuchang.life/"
ALLOWED_LINK_FIELDS = {
    "provider_name",
    "provider_subject_reference",
    "local_subject_reference",
    "identity_prefix_ref",
    "link_state",
    "consent_reference",
    "linked_at",
    "last_verified_at",
    "revoked_at",
    "verifier_result",
    "provider_payload_hash",
}
DENY_LINK_STATES = {
    "LINKING_PENDING",
    "REAUTHENTICATION_REQUIRED",
    "EXPLICIT_LINK_CONSENT_REQUIRED",
    "HUMAN_REVIEW_REQUIRED",
    "LINK_DENIED",
}


def canonical_payload_hash(payload: dict) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def provider_subject_reference(subject: str) -> str:
    if not subject:
        raise ValueError("line_provider_subject_required")
    return "provider:line:sha256:" + hashlib.sha256(subject.encode("utf-8")).hexdigest()


def callback_security_decision(
    *,
    expected_state: str | None,
    received_state: str | None,
    expected_nonce: str | None,
    token_claims: dict,
    expected_audience: str,
    profile_subject: str | None,
    callback_url: str,
) -> dict[str, str]:
    if callback_url != CANONICAL_CALLBACK_URL:
        return {"decision": "DENY", "reason": "CALLBACK_HOST_MISMATCH"}
    if not expected_state or received_state != expected_state:
        return {"decision": "DENY", "reason": "STATE_MISMATCH"}
    if not expected_nonce or token_claims.get("nonce") != expected_nonce:
        return {"decision": "DENY", "reason": "NONCE_MISMATCH"}
    if token_claims.get("aud") != expected_audience:
        return {"decision": "DENY", "reason": "AUDIENCE_MISMATCH"}
    if not token_claims.get("sub") or token_claims.get("sub") != profile_subject:
        return {"decision": "DENY", "reason": "PROVIDER_SUBJECT_MISMATCH"}
    return {"decision": "PASS", "reason": "CALLBACK_SECURITY_VERIFIED"}


def strict_channel_callback_security_decision(
    *,
    expected_state: str | None,
    received_state: str | None,
    expected_nonce: str | None,
    token_claims: dict,
    expected_audience: str,
    authenticated_subject: str | None,
    callback_url: str,
    issued_at_epoch: int | None,
    current_epoch: int,
    replay_state: str,
    ttl_seconds: int = 300,
) -> dict[str, str]:
    """Require one fresh, short-lived, authenticated LINE callback."""

    if (
        not isinstance(issued_at_epoch, int)
        or isinstance(issued_at_epoch, bool)
        or not isinstance(current_epoch, int)
        or isinstance(current_epoch, bool)
        or current_epoch < issued_at_epoch
        or current_epoch - issued_at_epoch > ttl_seconds
        or ttl_seconds < 1
        or ttl_seconds > 300
    ):
        return {"decision": "DENY", "reason": "CALLBACK_TTL_EXPIRED"}
    if replay_state != "SESSION_STATE_CONSUMED_ONCE":
        return {"decision": "DENY", "reason": "CALLBACK_REPLAY_EVIDENCE_REQUIRED"}
    return callback_security_decision(
        expected_state=expected_state,
        received_state=received_state,
        expected_nonce=expected_nonce,
        token_claims=token_claims,
        expected_audience=expected_audience,
        profile_subject=authenticated_subject,
        callback_url=callback_url,
    )


def minimized_link_record(
    profile: dict, authority_resolution: dict, verified_at: str
) -> dict:
    record = {
        "provider_name": "LINE",
        "provider_subject_reference": provider_subject_reference(
            str(profile.get("userId") or "")
        ),
        "local_subject_reference": authority_resolution.get("local_subject_reference"),
        "identity_prefix_ref": authority_resolution.get("identity_prefix_ref"),
        "link_state": authority_resolution.get("link_state") or "LINKING_PENDING",
        "consent_reference": authority_resolution.get("consent_reference"),
        "linked_at": authority_resolution.get("linked_at"),
        "last_verified_at": verified_at,
        "revoked_at": authority_resolution.get("revoked_at"),
        "verifier_result": authority_resolution.get("verifier_result") or "HOLD",
        "provider_payload_hash": canonical_payload_hash(profile),
    }
    if set(record) != ALLOWED_LINK_FIELDS:
        raise ValueError("line_link_record_allowlist_violation")
    return record


def authorization_decision(link_state: str) -> str:
    if link_state in DENY_LINK_STATES:
        return "DENY"
    if link_state in {"PROVIDER_LINK_FOUND", "LINK_CONFIRMED"}:
        return "ALLOW"
    return "DENY"
