#!/usr/bin/env python3
"""Fail-closed validator for the bounded RECONSTRUCT_ISOLATED V2 request."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator

try:
    from .w7tp_reconstruct_isolated_contract import (
        AUTHORIZED_STEP_ALLOWLIST,
        CONTRACT_ID,
        DELTA_ITEMS,
        FORBIDDEN_EFFECT_NAMES,
        MAXIMUM_EFFECT,
        MAX_REQUEST_TTL_SECONDS,
        MINIMUM_GENERATIVE_DELTA_SHA256,
        RECONSTRUCTION_CALLABLE,
        REQUEST_HASH_ALGORITHM,
        SCOPE_HASH_ALGORITHM,
        TARGET_BASE_STATE_SHA256,
        TARGET_FIELD_SNAPSHOT_SHA256,
        TARGET_NATIVE_GATEWAY,
        TARGET_NODE,
        TARGET_SUCCESSOR_CANONICAL_SHA256,
        exact_targets_for,
        scope_hash,
        self_hash,
    )
except ImportError:  # pragma: no cover - direct script/import compatibility
    from w7tp_reconstruct_isolated_contract import (
        AUTHORIZED_STEP_ALLOWLIST,
        CONTRACT_ID,
        DELTA_ITEMS,
        FORBIDDEN_EFFECT_NAMES,
        MAXIMUM_EFFECT,
        MAX_REQUEST_TTL_SECONDS,
        MINIMUM_GENERATIVE_DELTA_SHA256,
        RECONSTRUCTION_CALLABLE,
        REQUEST_HASH_ALGORITHM,
        SCOPE_HASH_ALGORITHM,
        TARGET_BASE_STATE_SHA256,
        TARGET_FIELD_SNAPSHOT_SHA256,
        TARGET_NATIVE_GATEWAY,
        TARGET_NODE,
        TARGET_SUCCESSOR_CANONICAL_SHA256,
        exact_targets_for,
        scope_hash,
        self_hash,
    )


RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
WORKSPACE_PREFIX = "runtime/isolated/"
REQUEST_FIELDS = frozenset(
    {
        "contract", "request_id", "request_self_hash_algorithm", "request_self_sha256",
        "scope_hash_algorithm", "scope_sha256", "requested_action", "target", "delta",
        "workspace", "reconstruction_base", "exact_targets", "input_hashes", "authority",
        "authorized_steps", "maximum_effect", "expected_effect", "affected_state",
        "risks", "safeguards", "rollback", "stop_conditions", "existing_services",
        "forbidden_effects", "single_use", "created_at", "expires_at", "replay_root",
        "total_field_review_required", "lineage",
    }
)


class ReconstructIsolatedValidationError(ValueError):
    def __init__(self, code: str, path: str = "$") -> None:
        self.code = code
        self.path = path
        super().__init__(f"DENY:{code}:{path}")


def _deny(condition: bool, code: str, path: str) -> None:
    if condition:
        raise ReconstructIsolatedValidationError(code, path)


def _parse_utc(value: Any, path: str) -> datetime:
    _deny(not isinstance(value, str), "DATETIME_REQUIRED", path)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReconstructIsolatedValidationError("DATETIME_INVALID", path) from exc
    _deny(parsed.tzinfo is None, "DATETIME_TIMEZONE_REQUIRED", path)
    return parsed.astimezone(timezone.utc)


def _schema_path() -> Path:
    return Path(__file__).resolve().parents[2] / "schemas" / "field" / "w7tp_total_field_d8_review_request_v2.schema.json"


def _validate_schema(request: dict[str, Any], schema_path: Path | None) -> None:
    path = schema_path or _schema_path()
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        raise ReconstructIsolatedValidationError("V2_SCHEMA_UNAVAILABLE_OR_INVALID", str(path)) from exc
    errors = sorted(Draft202012Validator(schema).iter_errors(request), key=lambda item: list(item.absolute_path))
    if errors:
        error = errors[0]
        location = "$" + "".join(f"[{part}]" if isinstance(part, int) else f".{part}" for part in error.absolute_path)
        raise ReconstructIsolatedValidationError("V2_SCHEMA_REJECTED", location)


def _pure_relative(raw: Any, path: str) -> PurePosixPath:
    _deny(not isinstance(raw, str) or not raw, "PATH_REQUIRED", path)
    _deny("\\" in raw or "\x00" in raw, "PATH_ENCODING_FORBIDDEN", path)
    pure = PurePosixPath(raw)
    _deny(pure.is_absolute(), "ABSOLUTE_PATH_FORBIDDEN", path)
    _deny(any(part in {"", ".", ".."} for part in pure.parts), "PATH_TRAVERSAL_FORBIDDEN", path)
    return pure


def _validate_no_symlink_escape(repo_root: Path, pure: PurePosixPath, path: str) -> None:
    root = repo_root.resolve()
    current = root
    for part in pure.parts:
        current = current / part
        if current.is_symlink():
            raise ReconstructIsolatedValidationError("SYMLINK_ESCAPE_FORBIDDEN", path)
    resolved = current.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ReconstructIsolatedValidationError("PATH_ESCAPE_FORBIDDEN", path) from exc


def _validate_paths(request: dict[str, Any], repo_root: Path | None) -> None:
    workspace_root = request["workspace"]["root"]
    workspace = _pure_relative(workspace_root, "$.workspace.root")
    _deny(not workspace_root.startswith(WORKSPACE_PREFIX), "WORKSPACE_PREFIX_MISMATCH", "$.workspace.root")
    _deny(len(workspace.parts) != 3, "WORKSPACE_DEPTH_MISMATCH", "$.workspace.root")
    _deny(RUN_ID.fullmatch(workspace.parts[-1]) is None, "RUN_ID_INVALID", "$.workspace.root")
    _deny(not request["request_id"].endswith(workspace.parts[-1]), "REQUEST_RUN_ID_MISMATCH", "$.request_id")

    expected_targets = exact_targets_for(workspace_root)
    _deny(request["exact_targets"] != expected_targets, "EXACT_TARGETS_MISMATCH", "$.exact_targets")
    for index, raw in enumerate(request["exact_targets"]):
        target = _pure_relative(raw, f"$.exact_targets[{index}]")
        _deny(target.parts[:3] != workspace.parts, "TARGET_OUTSIDE_WORKSPACE", f"$.exact_targets[{index}]")
        if repo_root is not None:
            _validate_no_symlink_escape(repo_root, target, f"$.exact_targets[{index}]")

    expected_replay_root = f"{workspace_root}/evidence"
    _deny(request["replay_root"] != expected_replay_root, "REPLAY_ROOT_MISMATCH", "$.replay_root")
    replay = _pure_relative(request["replay_root"], "$.replay_root")
    if repo_root is not None:
        _validate_no_symlink_escape(repo_root, workspace, "$.workspace.root")
        _validate_no_symlink_escape(repo_root, replay, "$.replay_root")


def _validate_exact_bindings(request: dict[str, Any]) -> None:
    target = request["target"]
    expected_target = {
        "node": TARGET_NODE,
        "field_snapshot_sha256": TARGET_FIELD_SNAPSHOT_SHA256,
        "base_state_sha256": TARGET_BASE_STATE_SHA256,
        "canonical_sha256": TARGET_SUCCESSOR_CANONICAL_SHA256,
    }
    _deny(target != expected_target, "TARGET_BINDING_MISMATCH", "$.target")
    _deny(
        request["delta"] != {"sha256": MINIMUM_GENERATIVE_DELTA_SHA256, "items": list(DELTA_ITEMS)},
        "DELTA_BINDING_MISMATCH",
        "$.delta",
    )
    input_hashes = request["input_hashes"]
    _deny(
        set(input_hashes)
        != {
            "target_field_snapshot_sha256",
            "target_base_state_sha256",
            "target_successor_canonical_sha256",
            "minimum_generative_delta_sha256",
        },
        "INPUT_HASH_SHAPE_MISMATCH",
        "$.input_hashes",
    )
    for field, expected in {
        "target_field_snapshot_sha256": TARGET_FIELD_SNAPSHOT_SHA256,
        "target_base_state_sha256": TARGET_BASE_STATE_SHA256,
        "target_successor_canonical_sha256": TARGET_SUCCESSOR_CANONICAL_SHA256,
        "minimum_generative_delta_sha256": MINIMUM_GENERATIVE_DELTA_SHA256,
    }.items():
        _deny(input_hashes.get(field) != expected, "INPUT_HASH_BINDING_MISMATCH", f"$.input_hashes.{field}")
    _deny(
        request["reconstruction_base"]
        != {"callable": RECONSTRUCTION_CALLABLE, "new_adapter_required": False, "gateway": TARGET_NATIVE_GATEWAY},
        "RECONSTRUCTION_BASE_MISMATCH",
        "$.reconstruction_base",
    )
    authority = request["authority"]
    _deny(
        set(authority)
        != {"pointer_ref", "pointer_sha256", "founder_authorization_ref", "founder_authorization_sha256", "authorized_effect"},
        "AUTHORITY_BINDING_SHAPE_MISMATCH",
        "$.authority",
    )
    _deny(authority["authorized_effect"] != "AUTHORIZE_RECONSTRUCT_ISOLATED_REVIEW_ONLY", "AUTHORITY_EFFECT_MISMATCH", "$.authority.authorized_effect")
    for field in ("pointer_sha256", "founder_authorization_sha256"):
        _deny(SHA256.fullmatch(authority[field]) is None, "AUTHORITY_HASH_FORMAT", f"$.authority.{field}")
    for field in ("pointer_ref", "founder_authorization_ref"):
        _pure_relative(authority[field], f"$.authority.{field}")


def _validate_effect_boundary(request: dict[str, Any]) -> None:
    steps = request["authorized_steps"]
    _deny(not steps or len(steps) != len(set(steps)), "AUTHORIZED_STEPS_INVALID", "$.authorized_steps")
    _deny(not set(steps).issubset(AUTHORIZED_STEP_ALLOWLIST), "AUTHORIZED_STEP_NOT_ALLOWED", "$.authorized_steps")
    _deny(request["maximum_effect"] != MAXIMUM_EFFECT, "MAXIMUM_EFFECT_MISMATCH", "$.maximum_effect")
    _deny(request["existing_services"] != "UNCHANGED", "EXISTING_SERVICES_CHANGE_FORBIDDEN", "$.existing_services")
    _deny(request["single_use"] is not True, "SINGLE_USE_REQUIRED", "$.single_use")
    forbidden = request["forbidden_effects"]
    _deny(set(forbidden) != set(FORBIDDEN_EFFECT_NAMES), "FORBIDDEN_EFFECT_MACHINE_INCOMPLETE", "$.forbidden_effects")
    for name in FORBIDDEN_EFFECT_NAMES:
        _deny(forbidden.get(name) is not False, f"FORBIDDEN_EFFECT_{name}", f"$.forbidden_effects.{name}")
    _deny(
        request["workspace"]
        != {
            "root": request["workspace"]["root"],
            "write_scope": "THIS_DIRECTORY_ONLY",
            "repository_mount": "READ_ONLY",
            "network": "NONE",
            "service_autoload": False,
            "live_volume_mount": False,
            "db_access": False,
            "state_store_access": False,
        },
        "WORKSPACE_BOUNDARY_MISMATCH",
        "$.workspace",
    )
    _deny(
        request["rollback"] != {"method": "DELETE_ONLY_THIS_ISOLATED_WORKSPACE", "live_state_restore_required": False},
        "ROLLBACK_BOUNDARY_MISMATCH",
        "$.rollback",
    )
    _deny(
        request["lineage"]
        != {"predecessor": "P2_ISOLATED_CANARY_V1", "relation": "VERSIONED_STRONG_COVER", "v1_preserved": True, "v1_mutated": False},
        "LINEAGE_BINDING_MISMATCH",
        "$.lineage",
    )


def _validate_hashes(request: dict[str, Any]) -> None:
    _deny(request["request_self_hash_algorithm"] != REQUEST_HASH_ALGORITHM, "REQUEST_HASH_ALGORITHM_MISMATCH", "$.request_self_hash_algorithm")
    _deny(request["scope_hash_algorithm"] != SCOPE_HASH_ALGORITHM, "SCOPE_HASH_ALGORITHM_MISMATCH", "$.scope_hash_algorithm")
    _deny(SHA256.fullmatch(request["request_self_sha256"]) is None, "REQUEST_HASH_FORMAT", "$.request_self_sha256")
    _deny(SHA256.fullmatch(request["scope_sha256"]) is None, "SCOPE_HASH_FORMAT", "$.scope_sha256")
    _deny(self_hash(request, "request_self_sha256") != request["request_self_sha256"], "REQUEST_HASH_MISMATCH", "$.request_self_sha256")
    _deny(scope_hash(request) != request["scope_sha256"], "SCOPE_HASH_MISMATCH", "$.scope_sha256")


def _validate_freshness(request: dict[str, Any], now: datetime) -> None:
    created = _parse_utc(request["created_at"], "$.created_at")
    expires = _parse_utc(request["expires_at"], "$.expires_at")
    _deny(expires <= created, "TTL_NON_POSITIVE", "$.expires_at")
    _deny((expires - created).total_seconds() > MAX_REQUEST_TTL_SECONDS, "TTL_EXCEEDS_BOUND", "$.expires_at")
    _deny(now.astimezone(timezone.utc) < created, "REQUEST_NOT_YET_VALID", "$.created_at")
    _deny(now.astimezone(timezone.utc) >= expires, "REQUEST_EXPIRED", "$.expires_at")


def _validate_replay(request: dict[str, Any], replay_root: Path | None) -> None:
    if replay_root is None or not replay_root.exists():
        return
    _deny(replay_root.is_symlink(), "REPLAY_ROOT_SYMLINK_FORBIDDEN", "$.replay_root")
    for path in replay_root.rglob("TOTAL_FIELD_RECONSTRUCT_ISOLATED_RECEIPT.json"):
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise ReconstructIsolatedValidationError("REPLAY_EVIDENCE_UNREADABLE", str(path))
        if receipt.get("request_sha256") == request["request_self_sha256"] and receipt.get("single_use_consumed") is True:
            raise ReconstructIsolatedValidationError("REQUEST_REPLAYED", str(path))


def validate_request(
    request: dict[str, Any],
    *,
    now: datetime,
    repo_root: Path | None = None,
    replay_root: Path | None = None,
    schema_path: Path | None = None,
) -> dict[str, Any]:
    """Validate all V2 bindings; return the same request or raise DENY."""

    _deny(not isinstance(request, dict), "REQUEST_OBJECT_REQUIRED", "$")
    _validate_schema(request, schema_path)
    _deny(set(request) != REQUEST_FIELDS, "REQUEST_SHAPE_MISMATCH", "$")
    _deny(request.get("contract") != CONTRACT_ID, "V2_CONTRACT_REQUIRED", "$.contract")
    _deny(request.get("requested_action") != "RECONSTRUCT_ISOLATED", "V2_ACTION_REQUIRED", "$.requested_action")
    _validate_exact_bindings(request)
    _validate_paths(request, repo_root)
    _validate_effect_boundary(request)
    _validate_hashes(request)
    _validate_freshness(request, now)
    _validate_replay(request, replay_root)
    return request


__all__ = ["ReconstructIsolatedValidationError", "validate_request"]
