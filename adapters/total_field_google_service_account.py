#!/usr/bin/env python3
"""Reference-only Total Field Google connector identity boundary.

This adapter validates configuration packets and builds candidate requests.  It
does not read credentials, connect to Google, or grant execution authority.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas/w7tp_total_field_service_account_binding.schema.json"
FORBIDDEN_CREDENTIAL_KEYS = {
    "private_key",
    "private_key_id",
    "access_token",
    "refresh_token",
    "client_secret",
    "credential_json",
    "service_account_key_file",
}


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def deterministic_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _forbidden_paths(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key).lower() in FORBIDDEN_CREDENTIAL_KEYS:
                found.append(child_path)
            found.extend(_forbidden_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_forbidden_paths(child, f"{path}[{index}]"))
    return found


def validate_service_account_binding(binding: Mapping[str, Any]) -> dict[str, Any]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    schema_errors = Draft202012Validator(schema).iter_errors(binding)
    errors = [
        f"{'.'.join(str(part) for part in error.path) or '$'}:{error.validator}"
        for error in sorted(schema_errors, key=lambda item: list(item.path))
    ]
    errors.extend(f"FORBIDDEN_CREDENTIAL_FIELD:{path}" for path in _forbidden_paths(binding))
    return {
        "state": "HOLD" if errors else "PASS",
        "errors": errors,
        "binding_id": binding.get("binding_id"),
    }


def build_total_field_candidate_request(
    binding: Mapping[str, Any],
    *,
    run_id: str,
    capability_ref: str,
    candidate_packet_ref: str,
    evidence_refs: list[str],
) -> dict[str, Any]:
    """Build a reference-only cloud candidate request after binding validation."""

    validation = validate_service_account_binding(binding)
    if validation["state"] != "PASS":
        return {
            "state": "HOLD",
            "errors": validation["errors"],
            "execution_authority": False,
            "verification_required": True,
        }
    packet = {
        "schema_version": "W7TP-TOTAL-FIELD-CLOUD-CANDIDATE-REQUEST/1.0",
        "channel": "TOTAL_FIELD",
        "run_id": run_id,
        "binding_ref": binding["binding_id"],
        "principal_ref": binding["principal_ref"],
        "capability_ref": capability_ref,
        "candidate_packet_ref": candidate_packet_ref,
        "evidence_refs": sorted(set(evidence_refs)),
        "execution_authority": False,
        "verification_required": True,
        "owner_xiaoj_identity_used": False,
        "member_identity_used": False,
        "seal_status": "NOT_SEALED",
    }
    packet["sha256"] = deterministic_sha256(packet)
    return packet


def assess_adc_readiness(
    binding: Mapping[str, Any], *, live_probe: bool = False
) -> dict[str, Any]:
    """Report mock readiness without reading ADC or claiming a live connection."""

    validation = validate_service_account_binding(binding)
    if validation["state"] != "PASS":
        return {
            "state": "HOLD_BINDING_INVALID",
            "adc_check": "NOT_RUN",
            "live_probe": "NOT_RUN",
            "errors": validation["errors"],
        }
    if live_probe:
        return {
            "state": "HOLD_CREDENTIAL_NOT_PROVISIONED",
            "adc_check": "HOLD_CREDENTIAL_NOT_PROVISIONED",
            "live_probe": "NOT_RUN",
            "errors": ["CREDENTIAL_INSPECTION_OUTSIDE_ADAPTER_SCOPE"],
        }
    return {
        "state": "PASS_MOCK_CONFIGURATION",
        "adc_check": "NOT_RUN",
        "live_probe": "NOT_RUN",
        "errors": [],
    }


__all__ = [
    "assess_adc_readiness",
    "build_total_field_candidate_request",
    "deterministic_sha256",
    "validate_service_account_binding",
]
