#!/usr/bin/env python3
"""Independent, local-only entrypoint for hash-bound Total Field static review.

The entrypoint can accept only a static implementation candidate.  It never
grants runtime, image, deployment, database, Canonical, Pointer, or git write
authority, and it refuses to review its own implementation sources.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ENTRYPOINT_VERSION = "w7tp-total-field-static-review-entrypoint/1.0"
REQUEST_SCHEMA_VERSION = "W7TP-TOTAL-FIELD-STATIC-REVIEW-REQUEST/1.0"
SOURCE_MANIFEST_SCHEMA_VERSION = "W7TP-TOTAL-FIELD-STATIC-SOURCE-MANIFEST/1.0"
OWNER_SEAL_SCHEMA_VERSION = "W7TP-TOTAL-FIELD-STATIC-REVIEW-OWNER-SEAL/1.0"
REQUEST_SELF_HASH_ALGORITHM = "SHA256_CANONICAL_JSON_EXCLUDING_REQUEST_SELF_SHA256/1.0"
OWNER_SEAL_SELF_HASH_ALGORITHM = "SHA256_CANONICAL_JSON_EXCLUDING_OWNER_SEAL_SELF_SHA256/1.0"
FOUNDER_AUTHORITY_REF = "founder:jiang-zhenglong"
OWNER_AUTHORIZATION = "AUTHORIZE_SINGLE_USE_TOTAL_FIELD_STATIC_REVIEW_ONLY"

DECISION_ACCEPT = "ACCEPT_STATIC_IMPLEMENTATION_CANDIDATE_ONLY"
DECISION_HOLD = "HOLD_STATIC_REVIEW"
DECISION_BLOCK = "BLOCK_STATIC_REVIEW"
REQUESTED_DECISIONS = frozenset(
    {
        DECISION_ACCEPT,
        "ACCEPT_STATIC_D8_REVIEWER_ENTRYPOINT_REPAIR_CANDIDATE_ONLY",
        "ACCEPT_GOOGLE_EXTERNAL_CANDIDATE_DUAL_CHANNEL_AS_STATIC_IMPLEMENTATION_AND_ISOLATED_TEST_BASELINE",
    }
)
SELF_REVIEW_PATHS = frozenset(
    {
        "tools/total_field/w7tp_static_review_entrypoint.py",
        "schemas/field/w7tp_total_field_static_review_request_v1.schema.json",
        "tests/test_w7tp_static_review_entrypoint.py",
    }
)
NON_EXECUTION_FIELDS = frozenset(
    {
        "runtime_activation",
        "image_build",
        "image_pull",
        "image_tag",
        "container_start",
        "deploy",
        "restart",
        "db_write",
        "canonical_change",
        "pointer_change",
        "git_commit",
        "git_push",
    }
)
REQUEST_FIELDS = frozenset(
    {
        "schema_version",
        "packet_type",
        "run_id",
        "packet_id",
        "event_id",
        "created_at",
        "expires_at",
        "state",
        "requested_decision",
        "only_request",
        "purpose",
        "single_use",
        "single_use_id",
        "request_self_hash_algorithm",
        "request_self_sha256",
        "source_manifest_path",
        "source_manifest_sha256",
        "owner_seal_path",
        "non_execution_assertions",
    }
)
OWNER_SEAL_FIELDS = frozenset(
    {
        "schema_version",
        "packet_type",
        "seal_id",
        "run_id",
        "purpose",
        "complete_manifest_sha256",
        "review_request_sha256",
        "single_use",
        "single_use_id",
        "issued_at",
        "expires_at",
        "founder_authority_ref",
        "authorization",
        "owner_seal_self_hash_algorithm",
        "owner_seal_self_sha256",
        "non_execution_assertions",
    }
)
HEX64 = re.compile(r"^[0-9a-f]{64}$")
PURPOSE = re.compile(r"^[A-Z0-9_:-]+$")


class StaticReviewError(ValueError):
    """Stable review failure carrying a fixed Total Field disposition."""

    def __init__(self, disposition: str, reason_code: str, path: str = "$") -> None:
        self.disposition = disposition
        self.reason_code = reason_code
        self.path = path
        super().__init__(f"{disposition}:{reason_code}:{path}")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc(value: Any, path: str) -> datetime:
    if not isinstance(value, str):
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_SCHEMA_DATETIME_REQUIRED", path)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_SCHEMA_DATETIME_INVALID", path) from exc
    if parsed.tzinfo is None:
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_SCHEMA_DATETIME_TIMEZONE_REQUIRED", path)
    return parsed.astimezone(timezone.utc)


def load_object(path: Path, reason: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise StaticReviewError(DECISION_BLOCK, f"BLOCK_STATIC_{reason}_JSON_INVALID", str(path)) from exc
    if not isinstance(value, dict):
        raise StaticReviewError(DECISION_BLOCK, f"BLOCK_STATIC_{reason}_OBJECT_REQUIRED", str(path))
    return value


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and HEX64.fullmatch(value) is not None


def safe_repo_path(repo_root: Path, raw_path: Any, path: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path:
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_PATH_REQUIRED", path)
    candidate = Path(raw_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_PATH_ESCAPE", path)
    current = repo_root.resolve()
    for part in candidate.parts:
        current = current / part
        if current.is_symlink():
            raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_SYMBOLIC_LINK", path)
    resolved = (repo_root / candidate).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_PATH_ESCAPE", path) from exc
    return resolved


def bound_input_path(input_path: Path, repo_root: Path, path: str) -> tuple[Path, str]:
    try:
        candidate = input_path.relative_to(repo_root) if input_path.is_absolute() else input_path
        relative = candidate.as_posix()
    except ValueError as exc:
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_PATH_ESCAPE", path) from exc
    return safe_repo_path(repo_root, relative, path), relative


def validate_non_execution(value: Any, path: str) -> None:
    if not isinstance(value, dict) or set(value) != NON_EXECUTION_FIELDS:
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_NON_EXECUTION_SCHEMA", path)
    for key in NON_EXECUTION_FIELDS:
        if value.get(key) is not False:
            raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_FORBIDDEN_AUTHORITY_INJECTION", f"{path}.{key}")


def validate_self_hash(value: dict[str, Any], field: str, algorithm_field: str, algorithm: str, path: str) -> None:
    if value.get(algorithm_field) != algorithm or not is_sha256(value.get(field)):
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_SELF_HASH_SCHEMA", path)
    candidate = dict(value)
    expected = candidate.pop(field)
    if sha256_bytes(canonical_json_bytes(candidate)) != expected:
        raise StaticReviewError(DECISION_HOLD, "HOLD_STATIC_SELF_HASH_MISMATCH", path)


def validate_request(request: dict[str, Any]) -> None:
    if set(request) != REQUEST_FIELDS:
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_REQUEST_FIELD_INJECTION", "$")
    string_fields = (
        "run_id",
        "packet_id",
        "event_id",
        "created_at",
        "expires_at",
        "requested_decision",
        "only_request",
        "purpose",
        "single_use_id",
        "source_manifest_path",
        "source_manifest_sha256",
        "owner_seal_path",
    )
    if any(not isinstance(request.get(key), str) or not request[key] for key in string_fields):
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_REQUEST_FIELD_SCHEMA", "$")
    if request.get("schema_version") != REQUEST_SCHEMA_VERSION:
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_REQUEST_SCHEMA_VERSION", "$.schema_version")
    if request.get("packet_type") != "TOTAL_FIELD_STATIC_REVIEW_REQUEST":
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_REQUEST_PACKET_TYPE", "$.packet_type")
    if request.get("state") != "PENDING_TOTAL_FIELD_STATIC_REVIEW":
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_REQUEST_STATE", "$.state")
    requested = request["requested_decision"]
    if requested not in REQUESTED_DECISIONS or request["only_request"] != requested:
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_DECISION_VOCABULARY", "$.requested_decision")
    if request.get("single_use") is not True:
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_SINGLE_USE_REQUIRED", "$.single_use")
    if PURPOSE.fullmatch(request["purpose"]) is None:
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_PURPOSE_SCHEMA", "$.purpose")
    if not is_sha256(request["source_manifest_sha256"]):
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_MANIFEST_SHA256_SCHEMA", "$.source_manifest_sha256")
    validate_non_execution(request["non_execution_assertions"], "$.non_execution_assertions")
    validate_self_hash(
        request,
        "request_self_sha256",
        "request_self_hash_algorithm",
        REQUEST_SELF_HASH_ALGORITHM,
        "$.request_self_sha256",
    )


def validate_manifest(
    manifest: dict[str, Any],
    request: dict[str, Any],
    repo_root: Path,
) -> list[dict[str, Any]]:
    required = {
        "schema_version",
        "packet_type",
        "run_id",
        "purpose",
        "manifest_self_hash_excluded",
        "files",
        "file_count",
    }
    if set(manifest) != required:
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_MANIFEST_FIELD_INJECTION", "$.manifest")
    if manifest.get("schema_version") != SOURCE_MANIFEST_SCHEMA_VERSION:
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_MANIFEST_SCHEMA_VERSION", "$.manifest.schema_version")
    if manifest.get("packet_type") != "TOTAL_FIELD_STATIC_SOURCE_MANIFEST":
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_MANIFEST_PACKET_TYPE", "$.manifest.packet_type")
    if manifest.get("run_id") != request["run_id"] or manifest.get("purpose") != request["purpose"]:
        raise StaticReviewError(DECISION_HOLD, "HOLD_STATIC_RUN_OR_PURPOSE_MISMATCH", "$.manifest")
    if manifest.get("manifest_self_hash_excluded") is not True:
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_MANIFEST_SELF_RULE", "$.manifest")
    files = manifest.get("files")
    if not isinstance(files, list) or not files or manifest.get("file_count") != len(files):
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_MANIFEST_FILES_SCHEMA", "$.manifest.files")
    seen: set[str] = set()
    verified: list[dict[str, Any]] = []
    for index, entry in enumerate(files):
        entry_path = f"$.manifest.files[{index}]"
        if not isinstance(entry, dict) or not {"path", "sha256", "size_bytes"} <= set(entry) <= {
            "path",
            "sha256",
            "size_bytes",
            "role",
        }:
            raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_MANIFEST_ENTRY_SCHEMA", entry_path)
        raw_path = entry.get("path")
        if raw_path in seen:
            raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_MANIFEST_DUPLICATE_PATH", f"{entry_path}.path")
        source = safe_repo_path(repo_root, raw_path, f"{entry_path}.path")
        normalized_path = source.relative_to(repo_root.resolve()).as_posix()
        if normalized_path in SELF_REVIEW_PATHS:
            raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_SELF_REVIEW", f"{entry_path}.path")
        expected_hash = entry.get("sha256")
        expected_size = entry.get("size_bytes")
        if not is_sha256(expected_hash) or not isinstance(expected_size, int) or isinstance(expected_size, bool) or expected_size < 0:
            raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_MANIFEST_ENTRY_SCHEMA", entry_path)
        if not source.is_file():
            raise StaticReviewError(DECISION_HOLD, "HOLD_STATIC_SOURCE_FILE_MISSING", str(raw_path))
        actual_hash = sha256_file(source)
        actual_size = source.stat().st_size
        if actual_hash != expected_hash or actual_size != expected_size:
            raise StaticReviewError(DECISION_HOLD, "HOLD_STATIC_SOURCE_HASH_OR_SIZE_MISMATCH", str(raw_path))
        seen.add(str(raw_path))
        verified.append({"path": raw_path, "sha256": actual_hash, "size_bytes": actual_size})
    return verified


def validate_owner_seal(
    seal: dict[str, Any],
    request: dict[str, Any],
    request_sha256: str,
    reviewed_at: datetime,
) -> dict[str, Any]:
    if set(seal) != OWNER_SEAL_FIELDS:
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_OWNER_SEAL_FIELD_INJECTION", "$.owner_seal")
    if seal.get("schema_version") != OWNER_SEAL_SCHEMA_VERSION or seal.get("packet_type") != "TOTAL_FIELD_STATIC_REVIEW_OWNER_SEAL":
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_OWNER_SEAL_SCHEMA", "$.owner_seal")
    if seal.get("founder_authority_ref") != FOUNDER_AUTHORITY_REF or seal.get("authorization") != OWNER_AUTHORIZATION:
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_OWNER_SEAL_AUTHORITY", "$.owner_seal.authorization")
    if seal.get("single_use") is not True:
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_OWNER_SEAL_SINGLE_USE", "$.owner_seal.single_use")
    if not isinstance(seal.get("seal_id"), str) or not seal["seal_id"]:
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_OWNER_SEAL_ID", "$.owner_seal.seal_id")
    validate_non_execution(seal.get("non_execution_assertions"), "$.owner_seal.non_execution_assertions")
    validate_self_hash(
        seal,
        "owner_seal_self_sha256",
        "owner_seal_self_hash_algorithm",
        OWNER_SEAL_SELF_HASH_ALGORITHM,
        "$.owner_seal.owner_seal_self_sha256",
    )
    bindings = {
        "run_id": request["run_id"],
        "purpose": request["purpose"],
        "complete_manifest_sha256": request["source_manifest_sha256"],
        "review_request_sha256": request_sha256,
        "single_use_id": request["single_use_id"],
    }
    for key, expected in bindings.items():
        if seal.get(key) != expected:
            raise StaticReviewError(DECISION_HOLD, "HOLD_STATIC_OWNER_SEAL_BINDING_MISMATCH", f"$.owner_seal.{key}")
    issued_at = parse_utc(seal.get("issued_at"), "$.owner_seal.issued_at")
    expires_at = parse_utc(seal.get("expires_at"), "$.owner_seal.expires_at")
    request_created_at = parse_utc(request["created_at"], "$.created_at")
    request_expires_at = parse_utc(request["expires_at"], "$.expires_at")
    if issued_at < request_created_at or expires_at <= issued_at or expires_at > request_expires_at:
        raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_OWNER_SEAL_TTL", "$.owner_seal.expires_at")
    if reviewed_at >= expires_at:
        raise StaticReviewError(DECISION_HOLD, "HOLD_STATIC_OWNER_SEAL_EXPIRED", "$.owner_seal.expires_at")
    return {
        "seal_id": seal["seal_id"],
        "single_use_id": seal["single_use_id"],
        "expires_at": utc_text(expires_at),
    }


def find_replay(replay_root: Path | None, single_use_id: str, seal_id: str, output_dir: Path) -> str | None:
    if replay_root is None or not replay_root.is_dir():
        return None
    for result_path in sorted(replay_root.rglob("TOTAL_FIELD_STATIC_REVIEW_RESULT.json")):
        try:
            result_path.resolve().relative_to(output_dir.resolve())
            continue
        except ValueError:
            pass
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if result.get("single_use_id") == single_use_id or result.get("owner_seal_id") == seal_id:
            return result_path.as_posix()
    return None


def decision_state(decision: str) -> str:
    if decision == DECISION_ACCEPT:
        return "PASS_STATIC_IMPLEMENTATION_CANDIDATE_ACCEPTED"
    if decision == DECISION_BLOCK:
        return "BLOCK_TOTAL_FIELD_STATIC_REVIEW"
    return "HOLD_TOTAL_FIELD_STATIC_REVIEW"


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def review_once(
    *,
    request_path: Path,
    manifest_path: Path,
    owner_seal_path: Path,
    output_dir: Path,
    repo_root: Path,
    replay_root: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Review one exact static packet and emit only the fixed three-file result."""

    output_dir, _output_relative = bound_input_path(output_dir, repo_root, "--output-dir")
    if replay_root is not None:
        replay_root, _replay_relative = bound_input_path(replay_root, repo_root, "--replay-root")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    reviewed_at = (now or utc_now()).astimezone(timezone.utc)
    decision = DECISION_ACCEPT
    reason_codes: list[str] = []
    error_path: str | None = None
    request: dict[str, Any] = {}
    seal: dict[str, Any] = {}
    request_sha256: str | None = None
    manifest_sha256: str | None = None
    owner_seal_sha256: str | None = None
    verified_sources: list[dict[str, Any]] = []
    owner_binding: dict[str, Any] = {}
    checks: dict[str, Any] = {
        "entrypoint_independent": "PASS",
        "self_review": "NOT_REACHED",
        "runtime_activation": "NO",
        "image_build": "NO",
        "deploy": "NO",
        "db_write": "NO",
        "canonical_or_pointer_write": "NO",
    }
    try:
        bound_request, request_relative = bound_input_path(request_path, repo_root, "--request-path")
        if not bound_request.is_file():
            raise StaticReviewError(DECISION_HOLD, "HOLD_STATIC_REQUEST_MISSING", request_relative)
        request_sha256 = sha256_file(bound_request)
        request = load_object(bound_request, "REQUEST")
        validate_request(request)
        safe_repo_path(repo_root, request["source_manifest_path"], "$.source_manifest_path")
        safe_repo_path(repo_root, request["owner_seal_path"], "$.owner_seal_path")
        checks["request_schema_and_self_hash"] = "PASS"
        request_created_at = parse_utc(request["created_at"], "$.created_at")
        request_expires_at = parse_utc(request["expires_at"], "$.expires_at")
        if request_expires_at <= request_created_at:
            raise StaticReviewError(DECISION_BLOCK, "BLOCK_STATIC_REQUEST_TTL", "$.expires_at")
        if reviewed_at >= request_expires_at:
            raise StaticReviewError(DECISION_HOLD, "HOLD_STATIC_REQUEST_EXPIRED", "$.expires_at")
        checks["request_ttl"] = "PASS"

        bound_manifest, manifest_relative = bound_input_path(manifest_path, repo_root, "--manifest-path")
        if manifest_relative != request["source_manifest_path"]:
            raise StaticReviewError(DECISION_HOLD, "HOLD_STATIC_MANIFEST_PATH_BINDING", "$.source_manifest_path")
        if not bound_manifest.is_file():
            raise StaticReviewError(DECISION_HOLD, "HOLD_STATIC_MANIFEST_MISSING", manifest_relative)
        manifest_sha256 = sha256_file(bound_manifest)
        if manifest_sha256 != request["source_manifest_sha256"]:
            raise StaticReviewError(DECISION_HOLD, "HOLD_STATIC_MANIFEST_SHA256_MISMATCH", manifest_relative)
        manifest = load_object(bound_manifest, "MANIFEST")
        verified_sources = validate_manifest(manifest, request, repo_root)
        checks["manifest_and_source_files"] = f"PASS_{len(verified_sources)}_OF_{len(verified_sources)}"
        checks["self_review"] = "PASS_NOT_SELF_REVIEW"

        bound_seal, seal_relative = bound_input_path(owner_seal_path, repo_root, "--owner-seal-path")
        if seal_relative != request["owner_seal_path"]:
            raise StaticReviewError(DECISION_HOLD, "HOLD_STATIC_OWNER_SEAL_PATH_BINDING", "$.owner_seal_path")
        if not bound_seal.is_file():
            raise StaticReviewError(DECISION_HOLD, "HOLD_STATIC_OWNER_SEAL_MISSING", seal_relative)
        owner_seal_sha256 = sha256_file(bound_seal)
        seal = load_object(bound_seal, "OWNER_SEAL")
        owner_binding = validate_owner_seal(seal, request, request_sha256, reviewed_at)
        checks["owner_seal"] = "PASS"

        replay_path = find_replay(replay_root, request["single_use_id"], seal["seal_id"], output_dir)
        if replay_path is not None:
            raise StaticReviewError(DECISION_HOLD, "HOLD_STATIC_REPLAY", replay_path)
        checks["replay"] = "PASS"
        reason_codes.append("PASS_EXACT_HASH_BOUND_STATIC_IMPLEMENTATION_CANDIDATE_ONLY")
    except StaticReviewError as exc:
        decision = exc.disposition
        reason_codes.append(exc.reason_code)
        error_path = exc.path
        checks.setdefault("request_schema_and_self_hash", "NOT_REACHED")
        checks.setdefault("request_ttl", "NOT_REACHED")
        checks.setdefault("manifest_and_source_files", "NOT_REACHED")
        checks.setdefault("owner_seal", "NOT_REACHED")
        checks.setdefault("replay", "NOT_REACHED")

    run_id = request.get("run_id") if isinstance(request.get("run_id"), str) else "UNBOUND_STATIC_REVIEW"
    output_run_id = f"{run_id}_TOTAL_FIELD_STATIC_REVIEW"
    result = {
        "schema_version": "W7TP-TOTAL-FIELD-STATIC-REVIEW-RESULT/1.0",
        "packet_type": "TOTAL_FIELD_STATIC_REVIEW_RESULT",
        "run_id": output_run_id,
        "reviewed_at": utc_text(reviewed_at),
        "authority": "TOTAL_FIELD_STATIC_REVIEW_ENTRYPOINT",
        "entrypoint_version": ENTRYPOINT_VERSION,
        "state": decision_state(decision),
        "final_decision": decision,
        "accepted_request": request.get("requested_decision") if decision == DECISION_ACCEPT else None,
        "decision_scope": "EXACT_HASH_BOUND_STATIC_IMPLEMENTATION_CANDIDATE_ONLY" if decision == DECISION_ACCEPT else None,
        "reason_codes": reason_codes,
        "error_path": error_path,
        "source_request_sha256": request_sha256,
        "source_manifest_sha256": manifest_sha256,
        "owner_seal_sha256": owner_seal_sha256,
        "owner_seal_id": seal.get("seal_id") if isinstance(seal.get("seal_id"), str) else None,
        "single_use_id": request.get("single_use_id") if isinstance(request.get("single_use_id"), str) else None,
        "single_use_consumed": bool(seal) and decision in {DECISION_ACCEPT, DECISION_HOLD, DECISION_BLOCK},
        "source_files_verified": len(verified_sources),
        "runtime_update_authorized": False,
        "image_build_authorized": False,
        "image_pull_authorized": False,
        "image_tag_authorized": False,
        "container_start_authorized": False,
        "deployment_authorized": False,
        "restart_authorized": False,
        "db_write_authorized": False,
        "canonical_write_authorized": False,
        "pointer_write_authorized": False,
        "git_commit_authorized": False,
        "git_push_authorized": False,
        "side_effects_executed": False,
    }
    evidence = {
        "schema_version": "W7TP-TOTAL-FIELD-STATIC-REVIEW-EVIDENCE/1.0",
        "packet_type": "REVIEW_EVIDENCE",
        "run_id": output_run_id,
        "reviewed_at": utc_text(reviewed_at),
        "entrypoint_version": ENTRYPOINT_VERSION,
        "checks": checks,
        "reason_codes": reason_codes,
        "request": {
            "sha256": request_sha256,
            "run_id": request.get("run_id"),
            "purpose": request.get("purpose"),
            "requested_decision": request.get("requested_decision"),
        },
        "manifest": {
            "sha256": manifest_sha256,
            "files_verified": len(verified_sources),
            "verified_sources": verified_sources,
        },
        "owner_seal": {
            "sha256": owner_seal_sha256,
            **owner_binding,
        },
        "fixed_authority_boundary": {
            "runtime_activation": False,
            "image_build": False,
            "image_pull": False,
            "image_tag": False,
            "container_start": False,
            "deploy": False,
            "restart": False,
            "db_write": False,
            "canonical_change": False,
            "pointer_change": False,
            "git_commit": False,
            "git_push": False,
        },
    }
    result_path = output_dir / "TOTAL_FIELD_STATIC_REVIEW_RESULT.json"
    evidence_path = output_dir / "REVIEW_EVIDENCE.json"
    write_json(result_path, result)
    write_json(evidence_path, evidence)
    manifest_output = {
        "schema_version": "W7TP-TOTAL-FIELD-STATIC-REVIEW-DECISION-MANIFEST/1.0",
        "packet_type": "TOTAL_FIELD_STATIC_REVIEW_DECISION_MANIFEST",
        "run_id": output_run_id,
        "created_at": utc_text(reviewed_at),
        "manifest_self_hash_excluded": True,
        "files": [
            {
                "path": result_path.name,
                "size_bytes": result_path.stat().st_size,
                "sha256": sha256_file(result_path),
            },
            {
                "path": evidence_path.name,
                "size_bytes": evidence_path.stat().st_size,
                "sha256": sha256_file(evidence_path),
            },
        ],
        "file_count": 2,
        "source_manifest_sha256": manifest_sha256,
        "owner_seal_sha256": owner_seal_sha256,
        "final_decision": decision,
    }
    output_manifest_path = output_dir / "SHA256_MANIFEST.json"
    write_json(output_manifest_path, manifest_output)
    response = {
        "state": result["state"],
        "final_decision": decision,
        "reason_codes": reason_codes,
        "output_dir": output_dir.as_posix(),
        "result_sha256": sha256_file(result_path),
        "evidence_sha256": sha256_file(evidence_path),
        "manifest_sha256": sha256_file(output_manifest_path),
        "runtime_update_authorized": False,
        "side_effects_executed": False,
    }
    print(json.dumps(response, ensure_ascii=False, sort_keys=True))
    return response


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request-path", type=Path, required=True)
    parser.add_argument("--manifest-path", type=Path, required=True)
    parser.add_argument("--owner-seal-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--replay-root", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        response = review_once(
            request_path=args.request_path,
            manifest_path=args.manifest_path,
            owner_seal_path=args.owner_seal_path,
            output_dir=args.output_dir,
            repo_root=args.repo_root,
            replay_root=args.replay_root,
        )
    except (FileExistsError, OSError) as exc:
        print(json.dumps({"state": "BLOCK_STATIC_REVIEW_ENTRYPOINT", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0 if response["final_decision"] == DECISION_ACCEPT else 2


if __name__ == "__main__":
    raise SystemExit(main())
