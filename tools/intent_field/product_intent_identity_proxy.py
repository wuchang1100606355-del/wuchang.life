#!/usr/bin/env python3
"""Ref-only sovereign identity proxy mock for product intent dry-runs."""

from __future__ import annotations

import hashlib
import re
from typing import Any


ID_PATTERN = re.compile(r"(?<![A-Za-z0-9])[A-Z][12][0-9]{8}(?![A-Za-z0-9])")


def stable_ref(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}:{digest}"


def contains_member_plaintext(text: str) -> bool:
    return bool(ID_PATTERN.search(text))


def build_identity_proxy(intent_text: str, *, force_hold: bool = False) -> dict[str, Any]:
    """Build ref-only identity and authority fields without member plaintext."""

    base = stable_ref("identity_proxy_ref", intent_text or "empty")
    return {
        "identity_proxy_ref": base,
        "authority_scope_code": "authority_scope_code:owner_authorized_ref",
        "consent_state_code": "consent_state_code:hold_required" if force_hold else "consent_state_code:granted_ref",
        "device_binding_ref": stable_ref("device_binding_ref", "dry-run-device:" + base),
        "agent_binding_ref": stable_ref("agent_binding_ref", "dry-run-agent:" + base),
        "responsible_person_ref": "responsible_person_ref:owner_authorized",
        "contains_member_plaintext": contains_member_plaintext(intent_text),
    }
