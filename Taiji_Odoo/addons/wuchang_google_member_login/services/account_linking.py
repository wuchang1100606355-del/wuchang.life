"""Reference-only Google account-linking and callback safety rules."""

from __future__ import annotations

import hashlib


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
