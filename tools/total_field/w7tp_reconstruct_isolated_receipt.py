#!/usr/bin/env python3
"""Hash-bound post-execution receipt builder for RECONSTRUCT_ISOLATED V2.

The receipt is derived from three on-disk evidence objects.  Requester-only
claims are insufficient.  This module is a candidate and is not invoked here.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

try:
    from .w7tp_reconstruct_isolated_contract import RECEIPT_CONTRACT_ID, RECEIPT_HASH_ALGORITHM, canonical_json_bytes, self_hash, sha256_bytes
    from .w7tp_reconstruct_isolated_validator import ReconstructIsolatedValidationError, validate_request
except ImportError:  # pragma: no cover
    from w7tp_reconstruct_isolated_contract import RECEIPT_CONTRACT_ID, RECEIPT_HASH_ALGORITHM, canonical_json_bytes, self_hash, sha256_bytes
    from w7tp_reconstruct_isolated_validator import ReconstructIsolatedValidationError, validate_request


def _load_evidence(repo_root: Path, workspace_root: str, relative_name: str) -> tuple[dict[str, Any], str]:
    base = (repo_root.resolve() / PurePosixPath(workspace_root) / "evidence").resolve(strict=False)
    path = base / relative_name
    if path.is_symlink() or base.is_symlink():
        raise ReconstructIsolatedValidationError("EVIDENCE_SYMLINK_FORBIDDEN", str(path))
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise ReconstructIsolatedValidationError("EVIDENCE_PATH_ESCAPE", str(path)) from exc
    raw = resolved.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReconstructIsolatedValidationError("EVIDENCE_JSON_INVALID", str(path)) from exc
    if not isinstance(value, dict):
        raise ReconstructIsolatedValidationError("EVIDENCE_OBJECT_REQUIRED", str(path))
    return value, sha256_bytes(raw)


def _require(value: bool, code: str, path: str) -> None:
    if not value:
        raise ReconstructIsolatedValidationError(code, path)


def build_post_execution_receipt(
    request: dict[str, Any],
    *,
    repo_root: Path,
    now: datetime,
    schema_path: Path | None = None,
) -> dict[str, Any]:
    """Build a receipt only from matching execution, validation, and red-team evidence."""

    validate_request(request, now=now, repo_root=repo_root, schema_path=schema_path)
    workspace = request["workspace"]["root"]
    execution, execution_sha = _load_evidence(repo_root, workspace, "TARGET_NATIVE_RECONSTRUCTION_EVIDENCE.json")
    red_team, red_team_sha = _load_evidence(repo_root, workspace, "RED_TEAM_POST_RECONSTRUCTION.json")
    validation, validation_sha = _load_evidence(repo_root, workspace, "VALIDATION_REPORT.json")

    expected_common = {
        "request_sha256": request["request_self_sha256"],
        "scope_sha256": request["scope_sha256"],
        "target_field_snapshot_sha256": request["target"]["field_snapshot_sha256"],
        "target_base_state_sha256": request["target"]["base_state_sha256"],
        "target_successor_canonical_sha256": request["target"]["canonical_sha256"],
        "minimum_generative_delta_sha256": request["delta"]["sha256"],
    }
    for field, expected in expected_common.items():
        _require(execution.get(field) == expected, "EXECUTION_EVIDENCE_BINDING_MISMATCH", f"$.execution.{field}")
        _require(validation.get(field) == expected, "VALIDATION_EVIDENCE_BINDING_MISMATCH", f"$.validation.{field}")

    _require(execution.get("state") == "PASS", "EXECUTION_EVIDENCE_NOT_PASS", "$.execution.state")
    _require(execution.get("reconstruction_base") == request["reconstruction_base"]["callable"], "EXECUTION_BASE_MISMATCH", "$.execution.reconstruction_base")
    _require(execution.get("exact_targets") == request["exact_targets"], "EXECUTION_TARGETS_MISMATCH", "$.execution.exact_targets")
    _require(validation.get("state") == "PASS", "VALIDATION_REPORT_NOT_PASS", "$.validation.state")
    for field in ("request_sha256_verified", "scope_sha256_verified", "target_hashes_verified", "exact_targets_verified", "existing_services_unchanged", "no_live_effect"):
        _require(validation.get(field) is True, "VALIDATION_FACT_MISSING", f"$.validation.{field}")
    _require(red_team.get("state") == "PASS", "RED_TEAM_NOT_PASS", "$.red_team.state")
    _require(red_team.get("open_high_critical") == 0, "RED_TEAM_HIGH_CRITICAL_OPEN", "$.red_team.open_high_critical")
    _require(red_team.get("execution_evidence_sha256") == execution_sha, "RED_TEAM_EVIDENCE_HASH_MISMATCH", "$.red_team.execution_evidence_sha256")
    _require(red_team.get("validation_report_sha256") == validation_sha, "RED_TEAM_VALIDATION_HASH_MISMATCH", "$.red_team.validation_report_sha256")

    utc = now.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    receipt: dict[str, Any] = {
        "contract": RECEIPT_CONTRACT_ID,
        "receipt_id": f"W7TP_RECONSTRUCT_ISOLATED_RECEIPT_V2_{request['request_id']}",
        "created_at": utc,
        "request_sha256": request["request_self_sha256"],
        "scope_sha256": request["scope_sha256"],
        "target_field_snapshot_sha256": request["target"]["field_snapshot_sha256"],
        "target_base_state_sha256": request["target"]["base_state_sha256"],
        "target_successor_canonical_sha256": request["target"]["canonical_sha256"],
        "minimum_generative_delta_sha256": request["delta"]["sha256"],
        "target_reconstruction_evidence_sha256": execution_sha,
        "red_team_post_reconstruction_sha256": red_team_sha,
        "validation_report_sha256": validation_sha,
        "evidence_verification": {
            "source": "VALIDATION_REPORT_AND_HASH_BOUND_EXECUTION_EVIDENCE",
            "request_sha256_verified": True,
            "scope_sha256_verified": True,
            "target_hashes_verified": True,
            "exact_targets_verified": True,
            "red_team_open_high_critical": 0,
        },
        "candidate_only": True,
        "commit_applied": False,
        "no_action": True,
        "no_live_effect": True,
        "existing_services_unchanged": True,
        "live_rebind_occurred": False,
        "live_9107_mutation_occurred": False,
        "db_write_occurred": False,
        "service_restart_occurred": False,
        "canonical_mutation_occurred": False,
        "pointer_mutation_occurred": False,
        "deployment_occurred": False,
        "promotion_occurred": False,
        "activation_occurred": False,
        "landing_occurred": False,
        "single_use_consumed": True,
        "replay_disposition": "CONSUMED_EXACTLY_ONCE",
        "receipt_self_hash_algorithm": RECEIPT_HASH_ALGORITHM,
        "receipt_self_sha256": "0" * 64,
    }
    receipt["receipt_self_sha256"] = self_hash(receipt, "receipt_self_sha256")
    return receipt


def canonical_receipt_bytes(receipt: dict[str, Any]) -> bytes:
    return canonical_json_bytes(receipt)


__all__ = ["build_post_execution_receipt", "canonical_receipt_bytes"]
