#!/usr/bin/env python3
"""Candidate-only LAN/VPN intake for the existing Total Field gateway.

This adapter accepts one closed ``LLM_PUSH`` request, delegates to the existing
sovereign-domain adapter and Total Field candidate core, and returns only a
non-executable adjudication summary.  It performs no network, database, deploy,
restart, router, canonical, pointer, or persistent-state action.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from tools.domain_completion_total_field_gateway import (
    DomainCompletionTotalFieldGateway,
)
from tools.sovereign_ai_domain_completion_candidate import (
    DomainCompletionError,
    canonical_sha256,
    deep_copy_json,
    validate_candidate,
)


ROOT = Path(__file__).resolve().parents[1]
INTAKE_PATH = "/w7tp/member-sovereign/total-field-candidate"
REQUEST_SCHEMA_PATH = (
    ROOT / "schemas/sovereign_ai_candidate_intake_request.schema.json"
)
REQUEST_SCHEMA_VERSION = "w7tp-sovereign-ai-candidate-intake-request/0.1"
RESULT_SCHEMA_VERSION = "w7tp-sovereign-ai-candidate-intake-result/0.1"
MAX_REQUEST_BYTES = 256 * 1024
FORBIDDEN_INPUT_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "canonical_write",
        "commit_applied",
        "committed",
        "credential",
        "credential_json",
        "db_write",
        "deploy",
        "final_decision",
        "member_plaintext",
        "password",
        "permission_escalation",
        "physical_control",
        "pointer_write",
        "private_key",
        "raw_credential",
        "raw_key",
        "raw_token",
        "refresh_token",
        "restart",
        "router_write",
        "seal_applied",
        "secret",
        "tfid",
        "token",
        "total_field_hash",
    }
)


def _load_request_schema() -> dict[str, Any]:
    try:
        value = json.loads(
            REQUEST_SCHEMA_PATH.read_text(encoding="utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError("CANDIDATE_INTAKE_SCHEMA_READ_FAILED") from exc
    if not isinstance(value, dict):
        raise RuntimeError("CANDIDATE_INTAKE_SCHEMA_INVALID")
    Draft202012Validator.check_schema(value)
    return value


def _error_path(error: ValidationError) -> str:
    path = "$"
    for part in error.absolute_path:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


def _forbidden_path(value: Any, path: str = "$") -> str | None:
    if isinstance(value, Mapping):
        for key in sorted(value, key=str):
            child = f"{path}.{key}"
            if str(key).strip().casefold() in FORBIDDEN_INPUT_KEYS:
                return child
            found = _forbidden_path(value[key], child)
            if found is not None:
                return found
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            found = _forbidden_path(item, f"{path}[{index}]")
            if found is not None:
                return found
    return None


def _base_result(
    *,
    state: str,
    request_id: str | None,
    request_sha256: str | None,
    errors: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "state": state,
        "request_id": request_id,
        "request_sha256": request_sha256,
        "source_mode": "LLM_PUSH",
        "candidate_only": True,
        "requires_total_field_verify": True,
        "execution_authority": False,
        "production_commit_applied": False,
        "seal_applied": False,
        "db_write": False,
        "deploy": False,
        "restart": False,
        "router_write": False,
        "external_network_called": False,
        "errors": errors,
    }


def _rejection(
    state: str,
    error: str,
    *,
    request_id: str | None = None,
    request_sha256: str | None = None,
) -> dict[str, Any]:
    return _base_result(
        state=state,
        request_id=request_id,
        request_sha256=request_sha256,
        errors=[error],
    )


def run_sovereign_ai_candidate_intake(request: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and adjudicate one laptop LLM candidate without side effects."""

    if not isinstance(request, Mapping):
        return _rejection("HOLD_REQUEST_REJECTED", "REQUEST_OBJECT_REQUIRED")
    try:
        copied = deep_copy_json(dict(request))
    except DomainCompletionError as exc:
        return _rejection("HOLD_REQUEST_REJECTED", exc.reason_code)
    if not isinstance(copied, dict):
        return _rejection("HOLD_REQUEST_REJECTED", "REQUEST_OBJECT_REQUIRED")
    request_id_value = copied.get("request_id")
    request_id = request_id_value if isinstance(request_id_value, str) else None
    request_sha256 = canonical_sha256(copied)
    forbidden = _forbidden_path(copied)
    if forbidden is not None:
        return _rejection(
            "BLOCK_REQUEST_FORBIDDEN_FIELD",
            f"FORBIDDEN_INPUT_FIELD:{forbidden}",
            request_id=request_id,
            request_sha256=request_sha256,
        )
    validator = Draft202012Validator(_load_request_schema())
    errors = sorted(
        validator.iter_errors(copied),
        key=lambda item: ([str(part) for part in item.absolute_path], item.message),
    )
    if errors:
        return _rejection(
            "HOLD_REQUEST_REJECTED",
            f"REQUEST_SCHEMA_INVALID:{_error_path(errors[0])}",
            request_id=request_id,
            request_sha256=request_sha256,
        )
    candidate_payload = copied["candidate"]
    assert isinstance(candidate_payload, dict)
    if candidate_payload.get("source_mode") != "LLM_PUSH":
        return _rejection(
            "BLOCK_SOURCE_MODE_FORBIDDEN",
            "LLM_PUSH_REQUIRED",
            request_id=request_id,
            request_sha256=request_sha256,
        )
    try:
        candidate = validate_candidate(candidate_payload)
        observation_domains = copied["observation_domains"]
        assert isinstance(observation_domains, dict)
        if set(observation_domains) != {candidate.observation_domain_ref}:
            return _rejection(
                "HOLD_OBSERVATION_DOMAIN_REF_MISMATCH",
                "OBSERVATION_DOMAIN_REF_MISMATCH",
                request_id=request_id,
                request_sha256=request_sha256,
            )
        gateway = DomainCompletionTotalFieldGateway(
            observation_domains=observation_domains
        )
        core_result = gateway.receive_candidate(
            candidate.to_dict(), previous_value=copied["previous_value"]
        )
    except DomainCompletionError as exc:
        blocked = exc.reason_code in {
            "EXTERNAL_AUTHORITY_CLAIM_BLOCKED",
            "BLOCK_UNAUTHORIZED_CLOUD_COMMIT",
        }
        return _rejection(
            "BLOCK_CANDIDATE_REJECTED" if blocked else "HOLD_CANDIDATE_REJECTED",
            exc.reason_code,
            request_id=request_id,
            request_sha256=request_sha256,
        )
    decision = str(core_result["final_decision"])
    state_by_decision = {
        "ALLOW": "PASS_CANDIDATE_ACCEPTED",
        "HOLD": "HOLD_CANDIDATE",
        "BLOCK": "BLOCK_CANDIDATE",
        "QUARANTINE": "QUARANTINE_CANDIDATE",
    }
    result = _base_result(
        state=state_by_decision.get(decision, "HOLD_CANDIDATE_RESULT_INVALID"),
        request_id=request_id,
        request_sha256=request_sha256,
        errors=[],
    )
    result.update(
        {
            "candidate_hash": candidate.candidate_hash,
            "candidate_core_decision": decision,
            "decision_reason_codes": list(core_result["decision_reason_codes"]),
            "fixed_point_status": core_result["fixed_point_status"],
            "candidate_core_result_sha256": canonical_sha256(core_result),
        }
    )
    return result


__all__ = [
    "INTAKE_PATH",
    "MAX_REQUEST_BYTES",
    "REQUEST_SCHEMA_VERSION",
    "RESULT_SCHEMA_VERSION",
    "run_sovereign_ai_candidate_intake",
]
