#!/usr/bin/env python3
"""Effect-specific Total Field reviewer candidate for RECONSTRUCT_ISOLATED V2.

It reuses the existing canonical JSON, authority-pointer, founder-authorization,
TTL, replay, and receipt patterns.  It only returns in-memory review artifacts;
it cannot execute reconstruction or write files.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

try:
    from .w7tp_reconstruct_isolated_contract import (
        DECISION_CONTRACT_ID,
        DECISION_HASH_ALGORITHM,
        MAXIMUM_EFFECT,
        MINIMUM_GENERATIVE_DELTA_SHA256,
        TARGET_BASE_STATE_SHA256,
        TARGET_FIELD_SNAPSHOT_SHA256,
        TARGET_SUCCESSOR_CANONICAL_SHA256,
        canonical_json_bytes,
        self_hash,
        sha256_bytes,
    )
    from .w7tp_reconstruct_isolated_validator import ReconstructIsolatedValidationError, validate_request
except ImportError:  # pragma: no cover
    from w7tp_reconstruct_isolated_contract import (
        DECISION_CONTRACT_ID,
        DECISION_HASH_ALGORITHM,
        MAXIMUM_EFFECT,
        MINIMUM_GENERATIVE_DELTA_SHA256,
        TARGET_BASE_STATE_SHA256,
        TARGET_FIELD_SNAPSHOT_SHA256,
        TARGET_SUCCESSOR_CANONICAL_SHA256,
        canonical_json_bytes,
        self_hash,
        sha256_bytes,
    )
    from w7tp_reconstruct_isolated_validator import ReconstructIsolatedValidationError, validate_request


REVIEWER_VERSION = "w7tp-reconstruct-isolated-reviewer/2.0-candidate"
REVIEW_RECEIPT_CONTRACT_ID = "W7TP-TOTAL-FIELD-RECONSTRUCT-ISOLATED-REVIEW-RECEIPT/2.0"
REVIEW_RECEIPT_HASH_ALGORITHM = "SHA256_CANONICAL_JSON_EXCLUDING_RECEIPT_SHA256/1.0"
AUTHORIZED_EFFECT = "AUTHORIZE_RECONSTRUCT_ISOLATED_REVIEW_ONLY"


def _deny(condition: bool, code: str, path: str) -> None:
    if condition:
        raise ReconstructIsolatedValidationError(code, path)


def _parse_utc(value: Any, path: str) -> datetime:
    _deny(not isinstance(value, str), "AUTHORITY_DATETIME_REQUIRED", path)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReconstructIsolatedValidationError("AUTHORITY_DATETIME_INVALID", path) from exc
    _deny(parsed.tzinfo is None, "AUTHORITY_DATETIME_TIMEZONE_REQUIRED", path)
    return parsed.astimezone(timezone.utc)


def _load_hash_bound_json(repo_root: Path, ref: str, expected_sha256: str, path: str) -> dict[str, Any]:
    pure = PurePosixPath(ref)
    _deny(pure.is_absolute() or ".." in pure.parts or "\\" in ref, "AUTHORITY_REF_ESCAPE", path)
    root = repo_root.resolve()
    current = root
    for part in pure.parts:
        current = current / part
        _deny(current.is_symlink(), "AUTHORITY_REF_SYMLINK", path)
    resolved = current.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ReconstructIsolatedValidationError("AUTHORITY_REF_ESCAPE", path) from exc
    raw = resolved.read_bytes()
    _deny(sha256_bytes(raw) != expected_sha256, "AUTHORITY_REF_HASH_MISMATCH", path)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReconstructIsolatedValidationError("AUTHORITY_REF_JSON_INVALID", path) from exc
    _deny(not isinstance(value, dict), "AUTHORITY_REF_OBJECT_REQUIRED", path)
    return value


def _validate_authority(request: dict[str, Any], repo_root: Path, now: datetime) -> dict[str, Any]:
    binding = request["authority"]
    pointer = _load_hash_bound_json(repo_root, binding["pointer_ref"], binding["pointer_sha256"], "$.authority.pointer_ref")
    founder = _load_hash_bound_json(
        repo_root,
        binding["founder_authorization_ref"],
        binding["founder_authorization_sha256"],
        "$.authority.founder_authorization_ref",
    )
    for field, expected in {
        "node_id": "taiji01",
        "state": "ACTIVE_TOTAL_FIELD_AUTHORITY",
        "contract_state": "ACTIVE_FORMAL",
        "formal_decision_authority": True,
    }.items():
        _deny(pointer.get(field) != expected, "TOTAL_FIELD_AUTHORITY_POINTER_MISMATCH", f"$.authority_pointer.{field}")
    allowed = pointer.get("allowed_effects", [])
    _deny(not isinstance(allowed, list) or AUTHORIZED_EFFECT not in allowed, "TOTAL_FIELD_EFFECT_NOT_ALLOWED", "$.authority_pointer.allowed_effects")

    expected_founder = {
        "state": "FOUNDER_AUTHORIZATION_APPROVED",
        "authorized_effect": AUTHORIZED_EFFECT,
        "target_node": "taiji01",
        "target_field_snapshot_sha256": TARGET_FIELD_SNAPSHOT_SHA256,
        "target_base_state_sha256": TARGET_BASE_STATE_SHA256,
        "target_successor_canonical_sha256": TARGET_SUCCESSOR_CANONICAL_SHA256,
        "minimum_generative_delta_sha256": MINIMUM_GENERATIVE_DELTA_SHA256,
        "exact_workspace": request["workspace"]["root"],
        "exact_targets": request["exact_targets"],
        "authorized_steps": request["authorized_steps"],
        "maximum_effect": request["maximum_effect"],
        "single_use": True,
    }
    for field, expected in expected_founder.items():
        _deny(founder.get(field) != expected, "FOUNDER_AUTHORIZATION_SCOPE_MISMATCH", f"$.founder_authorization.{field}")
    created = _parse_utc(founder.get("created_at"), "$.founder_authorization.created_at")
    expires = _parse_utc(founder.get("expires_at"), "$.founder_authorization.expires_at")
    _deny(expires <= created or (expires - created).total_seconds() > 3600, "FOUNDER_AUTHORIZATION_TTL_INVALID", "$.founder_authorization.expires_at")
    _deny(now.astimezone(timezone.utc) < created or now.astimezone(timezone.utc) >= expires, "FOUNDER_AUTHORIZATION_NOT_FRESH", "$.founder_authorization.expires_at")
    return {
        "authority_pointer_sha256": binding["pointer_sha256"],
        "founder_authorization_sha256": binding["founder_authorization_sha256"],
        "authorized_effect": AUTHORIZED_EFFECT,
    }


def review_request(
    request: dict[str, Any],
    *,
    repo_root: Path,
    now: datetime,
    replay_root: Path | None = None,
    schema_path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Return decision, review receipt, and evidence; never execute or write."""

    validate_request(request, now=now, repo_root=repo_root, replay_root=replay_root, schema_path=schema_path)
    authority_evidence = _validate_authority(request, repo_root, now)
    decision: dict[str, Any] = {
        "contract": DECISION_CONTRACT_ID,
        "decision_id": f"D8_ALLOW_{request['request_id']}",
        "decision": "ALLOW",
        "state": "PASS",
        "request_sha256": request["request_self_sha256"],
        "scope_sha256": request["scope_sha256"],
        "target_field_snapshot_sha256": TARGET_FIELD_SNAPSHOT_SHA256,
        "target_base_state_sha256": TARGET_BASE_STATE_SHA256,
        "target_successor_canonical_sha256": TARGET_SUCCESSOR_CANONICAL_SHA256,
        "minimum_generative_delta_sha256": MINIMUM_GENERATIVE_DELTA_SHA256,
        "exact_workspace": request["workspace"]["root"],
        "exact_targets": list(request["exact_targets"]),
        "authorized_steps": list(request["authorized_steps"]),
        "maximum_effect": MAXIMUM_EFFECT,
        "expires_at": request["expires_at"],
        "single_use": True,
        "review_request_single_use_consumed": True,
        "execution_single_use_consumed": False,
        "replay_disposition": "UNCONSUMED_FOR_EXECUTION",
        "decision_hash_algorithm": DECISION_HASH_ALGORITHM,
        "decision_sha256": "0" * 64,
    }
    decision["decision_sha256"] = self_hash(decision, "decision_sha256")
    evidence = {
        "contract": "W7TP-TOTAL-FIELD-RECONSTRUCT-ISOLATED-REVIEW-EVIDENCE/2.0",
        "reviewer_version": REVIEWER_VERSION,
        "request_sha256": request["request_self_sha256"],
        "scope_sha256": request["scope_sha256"],
        "authority": authority_evidence,
        "checks": {
            "typed_request": "PASS",
            "target_hashes": "PASS",
            "workspace_containment": "PASS",
            "forbidden_effects": "PASS",
            "ttl": "PASS",
            "replay": "PASS",
            "authority_pointer": "PASS",
            "founder_authorization": "PASS",
        },
        "side_effects_executed": False,
    }
    receipt: dict[str, Any] = {
        "contract": REVIEW_RECEIPT_CONTRACT_ID,
        "receipt_id": f"REVIEW_RECEIPT_{request['request_id']}",
        "reviewer_version": REVIEWER_VERSION,
        "request_sha256": request["request_self_sha256"],
        "scope_sha256": request["scope_sha256"],
        "decision_sha256": decision["decision_sha256"],
        "review_evidence_sha256": sha256_bytes(canonical_json_bytes(evidence)),
        "final_decision": "ALLOW",
        "state": "PASS",
        "review_request_single_use_consumed": True,
        "execution_single_use_consumed": False,
        "replay_disposition": "UNCONSUMED_FOR_EXECUTION",
        "canary_started": False,
        "receipt_hash_algorithm": REVIEW_RECEIPT_HASH_ALGORITHM,
        "receipt_sha256": "0" * 64,
    }
    receipt["receipt_sha256"] = self_hash(receipt, "receipt_sha256")
    return decision, receipt, evidence


__all__ = ["REVIEWER_VERSION", "review_request"]
