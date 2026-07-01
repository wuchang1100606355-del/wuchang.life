"""LINE WORKS runtime resolver contract helpers.

This module validates resolver binding metadata only. It never reads runtime
credential values, never calls LINE WORKS, and never writes databases.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from .lineworks_connector import REQUIRED_CONNECTOR_REFS, is_safe_connector_ref


REQUIRED_RESOLVER_BINDINGS = {
    "lineworks_bot_ref": "lineworks_bot_id",
    "lineworks_target_user_ref": "lineworks_target_user_id",
    "lineworks_access_token_runtime_ref": "lineworks_access_token",
}

RUNTIME_RESOLVER_VERIFIER_ALLOWLIST = {
    "total_field_runtime_resolver_registry",
    "total_field_manual_runtime_binding",
    "lineworks_secret_vault_binding",
}

SAFE_BINDING_REF_PATTERN = re.compile(r"[A-Z0-9_:-]{6,160}")
HEX64_PATTERN = re.compile(r"[a-f0-9]{64}")
JWT_SHAPE_PATTERN = re.compile(r"[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}")
LONG_TOKEN_SHAPE_PATTERN = re.compile(r"(?=.*[A-Za-z])(?=.*[0-9])[A-Za-z0-9_~+/=-]{40,}")


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def has_secret_or_plaintext_shape(value: Any) -> bool:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value or "")
    return bool(
        re.search(r"sk-[A-Za-z0-9_-]{12,}", text)
        or re.search(r"(?i)(access|refresh|id)_token\s*[:=]\s*\S+", text)
        or re.search(r"(?i)client_secret\s*[:=]\s*\S+", text)
        or re.search(r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----", text)
        or re.search(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}", text)
        or re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
        or re.search(r"09\d{2}[- ]?\d{3}[- ]?\d{3}", text)
        or re.search(r"\b[A-Z][12]\d{8}\b", text)
        or JWT_SHAPE_PATTERN.search(text)
        or LONG_TOKEN_SHAPE_PATTERN.search(text)
    )


def is_safe_binding_ref(value: Any) -> bool:
    text = str(value or "").strip()
    return (
        text == str(value or "")
        and "REF" in text
        and SAFE_BINDING_REF_PATTERN.fullmatch(text) is not None
        and not has_secret_or_plaintext_shape(text)
    )


def is_safe_value_hash(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return bool(HEX64_PATTERN.fullmatch(text)) and text != "0" * 64


def _provided_binding(bindings: dict, key: str) -> dict:
    raw_value = bindings.get(key) if isinstance(bindings, dict) else None
    expected_class = REQUIRED_RESOLVER_BINDINGS[key]
    if isinstance(raw_value, dict):
        return {
            "connector_ref": str(raw_value.get("connector_ref") or "").strip(),
            "binding_ref": str(raw_value.get("binding_ref") or "").strip(),
            "value_class": str(raw_value.get("value_class") or expected_class).strip(),
            "value_hash": str(raw_value.get("value_hash") or "").strip().lower(),
            "verifier": str(raw_value.get("verifier") or "total_field_manual_runtime_binding").strip(),
            "verified": raw_value.get("verified") is True,
        }
    return {
        "connector_ref": "",
        "binding_ref": f"REF_{key.upper()}_RUNTIME_BINDING",
        "value_class": expected_class,
        "value_hash": "0" * 64,
        "verifier": "total_field_manual_runtime_binding",
        "verified": False,
    }


def _normalize_binding(
    key: str,
    connector_refs: dict,
    resolver_bindings: dict,
    allow_verified: bool,
) -> tuple[dict, list[str]]:
    binding = _provided_binding(resolver_bindings, key)
    warnings = []
    connector_ref = str((connector_refs or {}).get(key) or "").strip()
    if not binding["connector_ref"]:
        binding["connector_ref"] = connector_ref
    if binding["connector_ref"] != connector_ref:
        warnings.append(f"runtime_binding_connector_ref_mismatch:{key}")
        binding["verified"] = False
    if not is_safe_connector_ref(binding["connector_ref"]):
        warnings.append(f"runtime_binding_connector_ref_unsafe:{key}")
        binding["verified"] = False
    if not is_safe_binding_ref(binding["binding_ref"]):
        warnings.append(f"runtime_binding_ref_unsafe:{key}")
        binding["verified"] = False
    if binding["value_class"] != REQUIRED_RESOLVER_BINDINGS[key]:
        warnings.append(f"runtime_binding_value_class_wrong:{key}")
        binding["verified"] = False
    if not is_safe_value_hash(binding["value_hash"]):
        warnings.append(f"runtime_binding_value_hash_missing:{key}")
        binding["verified"] = False
    if binding["verifier"] not in RUNTIME_RESOLVER_VERIFIER_ALLOWLIST:
        warnings.append(f"runtime_binding_verifier_not_allowlisted:{key}")
        binding["verified"] = False
    if any(
        has_secret_or_plaintext_shape(binding.get(field))
        for field in ["connector_ref", "binding_ref", "verifier"]
    ):
        warnings.append(f"runtime_binding_contains_secret_or_plaintext_shape:{key}")
        binding["verified"] = False
    if not allow_verified:
        binding["verified"] = False
    return binding, warnings


def build_lineworks_runtime_resolver_contract(
    connector_refs: dict | None = None,
    resolver_bindings: dict | None = None,
    allow_verified: bool = False,
) -> dict:
    connector_refs = connector_refs if isinstance(connector_refs, dict) else {}
    resolver_bindings = resolver_bindings if isinstance(resolver_bindings, dict) else {}
    missing_connector_refs = [key for key in REQUIRED_CONNECTOR_REFS if not connector_refs.get(key)]
    unsafe_connector_refs = [
        key for key in REQUIRED_CONNECTOR_REFS if connector_refs.get(key) and not is_safe_connector_ref(connector_refs.get(key))
    ]
    normalized_bindings = {}
    warnings = []
    for key in REQUIRED_CONNECTOR_REFS:
        binding, binding_warnings = _normalize_binding(key, connector_refs, resolver_bindings, allow_verified)
        normalized_bindings[key] = binding
        warnings.extend(binding_warnings)
    warnings.extend(f"runtime_connector_ref_missing:{key}" for key in missing_connector_refs)
    warnings.extend(f"runtime_connector_ref_unsafe:{key}" for key in unsafe_connector_refs)
    resolver_ready = (
        not missing_connector_refs
        and not unsafe_connector_refs
        and all(binding.get("verified") is True for binding in normalized_bindings.values())
    )
    state = (
        "PASS_LINEWORKS_RUNTIME_RESOLVER_CONTRACT_READY"
        if resolver_ready
        else "HOLD_LINEWORKS_RUNTIME_RESOLVER_CONTRACT"
    )
    return {
        "schema": "W7TP_XIAOJ_LINEWORKS_RUNTIME_RESOLVER_CONTRACT_V1",
        "state": state,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "resolver_ready": resolver_ready,
        "resolver_role": "resolve_runtime_values_in_memory_only",
        "connector_ref_keys": list(REQUIRED_CONNECTOR_REFS),
        "runtime_value_classes": dict(REQUIRED_RESOLVER_BINDINGS),
        "runtime_resolver_bindings": normalized_bindings,
        "draft_warnings": warnings,
        "allow_verified_input": allow_verified,
        "resolver_contract_hash": stable_hash(
            {
                "connector_refs": {key: connector_refs.get(key, "") for key in REQUIRED_CONNECTOR_REFS},
                "runtime_resolver_bindings": normalized_bindings,
                "warnings": warnings,
            }
        ),
        "redaction": {
            "raw_runtime_values_in_contract": False,
            "bot_id_echo": False,
            "target_user_id_echo": False,
            "access_token_echo": False,
            "secret_value_echo": False,
            "member_plaintext_echo": False,
        },
        "p1_side_effects": {
            "external_api_call": False,
            "formal_lineworks_send": False,
            "secret_read": False,
            "member_plaintext_read": False,
            "deploy": False,
            "service_restart": False,
            "db_write": False,
        },
    }
