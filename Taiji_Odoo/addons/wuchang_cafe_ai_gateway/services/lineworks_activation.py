"""LINE WORKS runtime activation packet helpers.

Activation packets are local evidence for runtime dry-run readiness. They do
not send messages, resolve credentials, read secrets, or call external APIs.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any


SAFE_REF_PATTERN = re.compile(r"[A-Z0-9_:-]{6,160}")
HEX64_PATTERN = re.compile(r"[a-f0-9]{64}")
JWT_SHAPE_PATTERN = re.compile(r"[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}")
LONG_TOKEN_SHAPE_PATTERN = re.compile(r"(?=.*[A-Za-z])(?=.*[0-9])[A-Za-z0-9_~+/=-]{40,}")


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def has_secret_or_plaintext_shape(value: Any) -> bool:
    text = str(value or "")
    return bool(
        re.search(r"sk-[A-Za-z0-9_-]{12,}", text)
        or re.search(r"(?i)(access|refresh|id)_token\s*[:=]\s*\S+", text)
        or re.search(r"(?i)(^|[^A-Z0-9])ACCESS_TOKEN_REF($|[^A-Z0-9])", text)
        or re.search(r"(?i)client_secret\s*[:=]\s*\S+", text)
        or re.search(r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----", text)
        or re.search(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}", text)
        or re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
        or re.search(r"09\d{2}[- ]?\d{3}[- ]?\d{3}", text)
        or re.search(r"\b[A-Z][12]\d{8}\b", text)
        or JWT_SHAPE_PATTERN.search(text)
        or LONG_TOKEN_SHAPE_PATTERN.search(text)
    )


def is_safe_ref_or_hash(value: Any) -> bool:
    text = str(value or "").strip()
    if HEX64_PATTERN.fullmatch(text.lower()):
        return True
    return (
        text == str(value or "")
        and "REF" in text
        and SAFE_REF_PATTERN.fullmatch(text) is not None
        and not has_secret_or_plaintext_shape(text)
    )


def is_safe_hash(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return bool(HEX64_PATTERN.fullmatch(text)) and text != "0" * 64


def build_lineworks_runtime_activation_packet(
    operator_ref: Any = "",
    execution_envelope_hash: Any = "",
    candidate_packet_hash: Any = "",
    release_packet_hash: Any = "",
    reason_ref: Any = "REASON_REF_LINEWORKS_RUNTIME_DRY_RUN",
    confirm_human_activation: bool = False,
) -> dict:
    operator_ref = str(operator_ref or "").strip()
    execution_envelope_hash = str(execution_envelope_hash or "").strip().lower()
    candidate_packet_hash = str(candidate_packet_hash or "").strip().lower()
    release_packet_hash = str(release_packet_hash or "").strip().lower()
    reason_ref = str(reason_ref or "").strip()

    warnings = []
    if not is_safe_ref_or_hash(operator_ref):
        warnings.append("operator_ref_hash_or_opaque_ref_required")
    if not is_safe_hash(execution_envelope_hash):
        warnings.append("execution_envelope_hash_64hex_required")
    if candidate_packet_hash and not is_safe_hash(candidate_packet_hash):
        warnings.append("candidate_packet_hash_64hex_required")
    if release_packet_hash and not is_safe_hash(release_packet_hash):
        warnings.append("release_packet_hash_64hex_required")
    if reason_ref and not is_safe_ref_or_hash(reason_ref):
        warnings.append("reason_ref_hash_or_opaque_ref_required")

    human_activation = bool(confirm_human_activation and not warnings)
    seed = {
        "schema": "W7TP_XIAOJ_LINEWORKS_RUNTIME_ACTIVATION_PACKET_V1",
        "release_gate": "lineworks_send",
        "operator_ref": operator_ref if is_safe_ref_or_hash(operator_ref) else "",
        "execution_envelope_hash": execution_envelope_hash if is_safe_hash(execution_envelope_hash) else "",
        "candidate_packet_hash": candidate_packet_hash if is_safe_hash(candidate_packet_hash) else "",
        "release_packet_hash": release_packet_hash if is_safe_hash(release_packet_hash) else "",
        "reason_ref": reason_ref if is_safe_ref_or_hash(reason_ref) else "",
        "human_activation": human_activation,
    }
    activation_packet_hash = stable_hash(seed)
    state = "RUNTIME_ACTIVATION_PACKET_READY_FOR_DRY_RUN" if human_activation else "HOLD_RUNTIME_ACTIVATION_PACKET"
    return {
        **seed,
        "state": state,
        "activation_packet_hash": activation_packet_hash,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "draft_warnings": warnings,
        "runtime_activation": {
            "human_activation": human_activation,
            "release_gate": "lineworks_send",
            "activation_packet_hash": activation_packet_hash,
            "operator_ref": operator_ref if is_safe_ref_or_hash(operator_ref) else "",
        },
        "side_effects": {
            "external_api_call": False,
            "formal_lineworks_send": False,
            "secret_read": False,
            "member_plaintext_read": False,
            "db_write": False,
            "deploy": False,
            "service_restart": False,
        },
    }
