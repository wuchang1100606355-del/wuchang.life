#!/usr/bin/env python3
"""Fail-closed Total Field decision-to-runner gate for V2.

The gate performs validation only.  It never calls the reconstruction base,
creates a workspace, or consumes an authorization.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
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
        self_hash,
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
        self_hash,
    )
    from w7tp_reconstruct_isolated_validator import ReconstructIsolatedValidationError, validate_request


DECISION_FIELDS = frozenset(
    {
        "contract",
        "decision_id",
        "decision",
        "state",
        "request_sha256",
        "scope_sha256",
        "target_field_snapshot_sha256",
        "target_base_state_sha256",
        "target_successor_canonical_sha256",
        "minimum_generative_delta_sha256",
        "exact_workspace",
        "exact_targets",
        "authorized_steps",
        "maximum_effect",
        "expires_at",
        "single_use",
        "review_request_single_use_consumed",
        "execution_single_use_consumed",
        "replay_disposition",
        "decision_hash_algorithm",
        "decision_sha256",
    }
)
REVIEW_RECEIPT_FIELDS = frozenset(
    {
        "contract",
        "receipt_id",
        "reviewer_version",
        "request_sha256",
        "scope_sha256",
        "decision_sha256",
        "review_evidence_sha256",
        "final_decision",
        "state",
        "review_request_single_use_consumed",
        "execution_single_use_consumed",
        "replay_disposition",
        "canary_started",
        "receipt_hash_algorithm",
        "receipt_sha256",
    }
)


def _deny(condition: bool, code: str, path: str) -> None:
    if condition:
        raise ReconstructIsolatedValidationError(code, path)


def _validate_review_receipt(
    receipt: dict[str, Any], request: dict[str, Any], decision: dict[str, Any]
) -> str:
    _deny(not isinstance(receipt, dict), "TOTAL_FIELD_REVIEW_RECEIPT_REQUIRED", "$.review_receipt")
    _deny(set(receipt) != REVIEW_RECEIPT_FIELDS, "TOTAL_FIELD_REVIEW_RECEIPT_SHAPE_MISMATCH", "$.review_receipt")
    expected = {
        "contract": "W7TP-TOTAL-FIELD-RECONSTRUCT-ISOLATED-REVIEW-RECEIPT/2.0",
        "reviewer_version": "w7tp-reconstruct-isolated-reviewer/2.0-candidate",
        "request_sha256": request["request_self_sha256"],
        "scope_sha256": request["scope_sha256"],
        "final_decision": "ALLOW",
        "state": "PASS",
        "decision_sha256": decision["decision_sha256"],
        "review_request_single_use_consumed": True,
        "execution_single_use_consumed": False,
        "replay_disposition": "UNCONSUMED_FOR_EXECUTION",
        "canary_started": False,
        "receipt_hash_algorithm": "SHA256_CANONICAL_JSON_EXCLUDING_RECEIPT_SHA256/1.0",
    }
    for field, value in expected.items():
        _deny(receipt.get(field) != value, "TOTAL_FIELD_REVIEW_RECEIPT_BINDING_MISMATCH", f"$.review_receipt.{field}")
    for field in ("review_evidence_sha256", "receipt_sha256"):
        value = receipt.get(field)
        _deny(not isinstance(value, str) or len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value), "TOTAL_FIELD_REVIEW_RECEIPT_HASH_INVALID", f"$.review_receipt.{field}")
    _deny(self_hash(receipt, "receipt_sha256") != receipt["receipt_sha256"], "TOTAL_FIELD_REVIEW_RECEIPT_SELF_HASH_MISMATCH", "$.review_receipt.receipt_sha256")
    return receipt["receipt_sha256"]


def validate_runner_gate(
    decision: dict[str, Any],
    request: dict[str, Any],
    review_receipt: dict[str, Any],
    *,
    now: datetime,
    repo_root: Path | None = None,
    replay_root: Path | None = None,
    schema_path: Path | None = None,
) -> dict[str, Any]:
    """Return a bounded gate result only when every binding is exact."""

    validate_request(request, now=now, repo_root=repo_root, replay_root=replay_root, schema_path=schema_path)
    _deny(not isinstance(decision, dict), "DECISION_OBJECT_REQUIRED", "$.decision")
    _deny(set(decision) != DECISION_FIELDS, "DECISION_SHAPE_MISMATCH", "$.decision")
    expected = {
        "contract": DECISION_CONTRACT_ID,
        "decision": "ALLOW",
        "state": "PASS",
        "request_sha256": request["request_self_sha256"],
        "scope_sha256": request["scope_sha256"],
        "target_field_snapshot_sha256": TARGET_FIELD_SNAPSHOT_SHA256,
        "target_base_state_sha256": TARGET_BASE_STATE_SHA256,
        "target_successor_canonical_sha256": TARGET_SUCCESSOR_CANONICAL_SHA256,
        "minimum_generative_delta_sha256": MINIMUM_GENERATIVE_DELTA_SHA256,
        "exact_workspace": request["workspace"]["root"],
        "exact_targets": request["exact_targets"],
        "authorized_steps": request["authorized_steps"],
        "maximum_effect": MAXIMUM_EFFECT,
        "expires_at": request["expires_at"],
        "single_use": True,
        "review_request_single_use_consumed": True,
        "execution_single_use_consumed": False,
        "replay_disposition": "UNCONSUMED_FOR_EXECUTION",
        "decision_hash_algorithm": DECISION_HASH_ALGORITHM,
    }
    for field, value in expected.items():
        _deny(decision.get(field) != value, "DECISION_REQUEST_BINDING_MISMATCH", f"$.decision.{field}")
    _deny(self_hash(decision, "decision_sha256") != decision["decision_sha256"], "DECISION_HASH_MISMATCH", "$.decision.decision_sha256")
    review_receipt_sha256 = _validate_review_receipt(review_receipt, request, decision)
    return {
        "gate": "ALLOW",
        "state": "PASS",
        "request_sha256": request["request_self_sha256"],
        "scope_sha256": request["scope_sha256"],
        "exact_workspace": request["workspace"]["root"],
        "exact_targets": list(request["exact_targets"]),
        "authorized_steps": list(request["authorized_steps"]),
        "maximum_effect": MAXIMUM_EFFECT,
        "execution_single_use_consumed": False,
        "total_field_review_receipt_sha256": review_receipt_sha256,
        "no_execution_performed": True,
    }


__all__ = [
    "validate_runner_gate",
]
