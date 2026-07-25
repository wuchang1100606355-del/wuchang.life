#!/usr/bin/env python3
"""Deterministic container entrypoint for hash-bound Total Field D8 review.

This module is a thin container adapter around the repository's existing
fine-grained reviewer rules.  It never calls an LLM, starts a canary, deploys,
writes a database, or grants production execution authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.total_field.w7tp_candidate_fine_grain_reviewer import (
    DECISIONS as FINE_GRAIN_DECISIONS,
    analyze_candidate,
)


REVIEWER_VERSION = "w7tp-true8d-d8-reviewer-entrypoint/1.1"
REQUEST_SCHEMA_VERSION = "W7TP-D8-REVIEW-REQUEST/1.0"
SKILL_LIFECYCLE_SCOPE_VERSION = "W7TP-D8-SKILL-LIFECYCLE-CANDIDATE/1.0"
AGGREGATE_ALGORITHM_VERSION = "W7TP-LANDING-PAYLOAD-AGGREGATE/1.0"
AGGREGATE_ORDERING = "COMPLETE_LANDING_MANIFEST_FILES_ARRAY_ORDER"
REQUEST_SELF_HASH_ALGORITHM = "SHA256_CANONICAL_JSON_EXCLUDING_REQUEST_SELF_SHA256/1.0"
DECISION_ALLOW = "ALLOW_P2_ISOLATED_CANARY_EXECUTION_ONLY"
DECISION_ALLOW_OFFLINE_BUILD = "ALLOW_NO_NETWORK_OFFLINE_CANARY_IMAGE_BUILD_ONLY"
DECISION_HOLD = "HOLD"
DECISION_BLOCK = "BLOCK"
SUPPORTED_REQUESTED_DECISIONS = {
    "ALLOW_P2_ISOLATED_CANARY_EXECUTION_ONLY": DECISION_ALLOW,
    "ALLOW_NO_NETWORK_OFFLINE_CANARY_IMAGE_BUILD_ONLY": DECISION_ALLOW_OFFLINE_BUILD,
}
ALLOW_DECISIONS = frozenset(SUPPORTED_REQUESTED_DECISIONS.values())
OFFLINE_BUILD_FALSE_FIELDS = (
    "network_download",
    "pull",
    "c1_c9_execution",
    "production_deploy",
    "existing_service_restart",
    "db_write",
    "canonical_change",
    "pointer_change",
)
RULE_REFS = [
    "tools/total_field/w7tp_candidate_fine_grain_reviewer.py",
    "tools/total_field_candidate_gateway.py#external-authority-claim-guard",
    "containers/total_field/true8d-contract-formal/compose.formal.yaml#d8",
    "schemas/field/w7tp_total_field_d8_review_request_v1.schema.json",
]
BLOCK_FINE_GRAIN_DECISIONS = {
    "REJECT_TECHNICAL_DRIFT",
    "REJECT_OVERCLAIM",
    "TRADE_SECRET_QUARANTINE",
}
HEX64 = set("0123456789abcdef")


class D8ReviewError(ValueError):
    """Stable review failure with a deterministic disposition."""

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
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_SCHEMA_DATETIME_REQUIRED", path)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_SCHEMA_DATETIME_INVALID", path) from exc
    if parsed.tzinfo is None:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_SCHEMA_DATETIME_TIMEZONE_REQUIRED", path)
    return parsed.astimezone(timezone.utc)


def load_object(path: Path, reason_prefix: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise D8ReviewError(DECISION_BLOCK, f"BLOCK_{reason_prefix}_JSON_INVALID", str(path)) from exc
    if not isinstance(value, dict):
        raise D8ReviewError(DECISION_BLOCK, f"BLOCK_{reason_prefix}_OBJECT_REQUIRED", str(path))
    return value


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in HEX64 for char in value)


def validate_offline_build_scope(request: dict[str, Any]) -> None:
    if request["requested_decision"] != DECISION_ALLOW_OFFLINE_BUILD:
        return
    scope = request.get("offline_build_scope")
    if not isinstance(scope, dict):
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_OFFLINE_BUILD_SCOPE_REQUIRED", "$.offline_build_scope")
    required_types: dict[str, type] = {
        "base_image_reference": str,
        "base_image_digest": str,
        "wheelhouse_path": str,
        "wheelhouse_sha256": str,
        "wheelhouse_file_count": int,
        "containerfile_path": str,
        "containerfile_sha256": str,
        "network": str,
        "pip_no_index": bool,
        "single_use_build": bool,
        "image_qualification": bool,
        "qualification_network": str,
    }
    expected_fields = set(required_types) | set(OFFLINE_BUILD_FALSE_FIELDS)
    if set(scope) != expected_fields:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_OFFLINE_BUILD_SCOPE_FIELD", "$.offline_build_scope")
    for key, expected_type in required_types.items():
        if key not in scope or not isinstance(scope[key], expected_type) or (
            expected_type is int and isinstance(scope[key], bool)
        ):
            raise D8ReviewError(DECISION_BLOCK, "BLOCK_OFFLINE_BUILD_SCOPE_FIELD", f"$.offline_build_scope.{key}")
    for key in OFFLINE_BUILD_FALSE_FIELDS:
        if scope.get(key) is not False:
            raise D8ReviewError(DECISION_BLOCK, "BLOCK_OFFLINE_BUILD_FORBIDDEN_CAPABILITY", f"$.offline_build_scope.{key}")
    digest = scope["base_image_digest"]
    if not digest.startswith("sha256:") or not is_sha256(digest.removeprefix("sha256:")):
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_OFFLINE_BUILD_BASE_DIGEST", "$.offline_build_scope.base_image_digest")
    if not scope["base_image_reference"].endswith(f"@{digest}"):
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_OFFLINE_BUILD_BASE_BINDING", "$.offline_build_scope.base_image_reference")
    for key in ("wheelhouse_sha256", "containerfile_sha256"):
        if not is_sha256(scope[key]):
            raise D8ReviewError(DECISION_BLOCK, "BLOCK_OFFLINE_BUILD_SHA256", f"$.offline_build_scope.{key}")
    if scope["wheelhouse_file_count"] < 1:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_OFFLINE_BUILD_WHEELHOUSE_EMPTY", "$.offline_build_scope.wheelhouse_file_count")
    if scope["network"] != "none" or scope["qualification_network"] != "none":
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_OFFLINE_BUILD_NETWORK", "$.offline_build_scope.network")
    if scope["pip_no_index"] is not True:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_OFFLINE_BUILD_PIP_INDEX", "$.offline_build_scope.pip_no_index")
    if scope["single_use_build"] is not True or scope["image_qualification"] is not True:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_OFFLINE_BUILD_SINGLE_USE", "$.offline_build_scope.single_use_build")


def wheelhouse_aggregate_sha256(wheelhouse: Path, repo_root: Path) -> tuple[str, int]:
    entries = sorted(wheelhouse.iterdir(), key=lambda path: path.name)
    if not entries or any(not path.is_file() or path.is_symlink() for path in entries):
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_OFFLINE_BUILD_WHEELHOUSE_LAYOUT", str(wheelhouse))
    lines = "".join(
        f"{sha256_file(path)}  {path.resolve().relative_to(repo_root.resolve()).as_posix()}\n"
        for path in entries
    )
    return sha256_bytes(lines.encode("utf-8")), len(entries)


def verify_offline_build_bindings(request: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    if request["requested_decision"] != DECISION_ALLOW_OFFLINE_BUILD:
        return {}
    scope = request["offline_build_scope"]
    wheelhouse = safe_repo_path(repo_root, scope["wheelhouse_path"], "$.offline_build_scope.wheelhouse_path")
    if not wheelhouse.is_dir():
        raise D8ReviewError(DECISION_HOLD, "HOLD_OFFLINE_BUILD_WHEELHOUSE_MISSING", scope["wheelhouse_path"])
    aggregate_sha256, file_count = wheelhouse_aggregate_sha256(wheelhouse, repo_root)
    if aggregate_sha256 != scope["wheelhouse_sha256"] or file_count != scope["wheelhouse_file_count"]:
        raise D8ReviewError(DECISION_HOLD, "HOLD_OFFLINE_BUILD_WHEELHOUSE_MISMATCH", scope["wheelhouse_path"])
    containerfile = safe_repo_path(repo_root, scope["containerfile_path"], "$.offline_build_scope.containerfile_path")
    if not containerfile.is_file() or sha256_file(containerfile) != scope["containerfile_sha256"]:
        raise D8ReviewError(DECISION_HOLD, "HOLD_OFFLINE_BUILD_CONTAINERFILE_MISMATCH", scope["containerfile_path"])
    lines = [line.strip() for line in containerfile.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines or lines[0] != f"FROM {scope['base_image_reference']}":
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_OFFLINE_BUILD_CONTAINERFILE_FROM", scope["containerfile_path"])
    containerfile_text = "\n".join(lines)
    required_pip_flags = ("pip install", "--no-index", "--find-links", "--require-hashes", "--no-deps")
    if not all(flag in containerfile_text for flag in required_pip_flags):
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_OFFLINE_BUILD_CONTAINERFILE_PIP", scope["containerfile_path"])
    return {
        "base_image_digest": scope["base_image_digest"],
        "wheelhouse_sha256": aggregate_sha256,
        "wheelhouse_file_count": file_count,
        "containerfile_sha256": scope["containerfile_sha256"],
        "pull": False,
        "network": "none",
        "pip_no_index": True,
        "single_use_build": True,
        "image_qualification": True,
    }


def safe_repo_path(repo_root: Path, raw_path: Any, path: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_SCHEMA_PATH_REQUIRED", path)
    candidate = Path(raw_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_UNSAFE_MANIFEST_PATH", path)
    resolved_root = repo_root.resolve()
    resolved = (resolved_root / candidate).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_UNSAFE_MANIFEST_PATH", path) from exc
    return resolved


def recursive_authority_injection(value: Any, path: str = "$") -> str | None:
    if isinstance(value, dict):
        for key in sorted(value):
            nested = value[key]
            normalized = key.casefold()
            child = f"{path}.{key}"
            if normalized == "final_decision":
                return child
            if normalized in {"execution_authority", "production_deploy_authorized"}:
                return child
            if normalized in {
                "canonical_write",
                "pointer_change",
                "db_write",
                "deploy",
                "restart",
                "router_write",
                "commit_applied",
            } and nested is True:
                return child
            found = recursive_authority_injection(nested, child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found = recursive_authority_injection(nested, f"{path}[{index}]")
            if found is not None:
                return found
    return None


def review_skill_lifecycle_candidate_scope(candidate: dict[str, Any]) -> dict[str, Any]:
    """Review the closed five-skill candidate scope without granting authority."""

    required_types: dict[str, type] = {
        "schema_version": str,
        "packet_type": str,
        "run_id": str,
        "state": str,
        "parent_packet_sha256": str,
        "mapping_set_sha256": str,
        "skills": list,
        "non_execution_assertions": dict,
        "founder_seal_present": bool,
    }
    if set(candidate) != set(required_types):
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_SKILL_SCOPE_FIELD_SET", "$")
    for key, expected_type in required_types.items():
        if not isinstance(candidate[key], expected_type):
            raise D8ReviewError(DECISION_BLOCK, "BLOCK_SKILL_SCOPE_REQUIRED_FIELD", f"$.{key}")
    if candidate["schema_version"] != SKILL_LIFECYCLE_SCOPE_VERSION:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_SKILL_SCOPE_VERSION", "$.schema_version")
    if candidate["packet_type"] != "D8_SKILL_LIFECYCLE_CANDIDATE_REVIEW":
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_SKILL_SCOPE_PACKET_TYPE", "$.packet_type")
    if candidate["state"] != "PENDING_FOUNDER_G8_SEAL":
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_SKILL_SCOPE_STATE", "$.state")
    for key in ("parent_packet_sha256", "mapping_set_sha256"):
        if not is_sha256(candidate[key]):
            raise D8ReviewError(DECISION_BLOCK, "BLOCK_SKILL_SCOPE_SHA256", f"$.{key}")
    if candidate["founder_seal_present"] is not False:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_PREMATURE_FOUNDER_SEAL", "$.founder_seal_present")
    injection_path = recursive_authority_injection(candidate)
    if injection_path is not None:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_FORBIDDEN_AUTHORITY_INJECTION", injection_path)

    expected_assertions = {
        "canonical_write",
        "pointer_change",
        "registry_write",
        "db_write",
        "deploy",
        "restart",
        "router_write",
        "publication",
        "c1_c9_execution",
    }
    assertions = candidate["non_execution_assertions"]
    if set(assertions) != expected_assertions or any(value is not False for value in assertions.values()):
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_SKILL_SCOPE_FORBIDDEN_EFFECT", "$.non_execution_assertions")

    expected_skill_fields = {
        "package_id",
        "target_skill_id",
        "source_manifest_sha256",
        "contract_payload_sha256",
        "manifest_sha256",
        "lifecycle_state",
    }
    skills = candidate["skills"]
    if len(skills) != 5:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_SKILL_SCOPE_COUNT", "$.skills")
    package_ids: set[str] = set()
    for index, skill in enumerate(skills):
        path = f"$.skills[{index}]"
        if not isinstance(skill, dict) or set(skill) != expected_skill_fields:
            raise D8ReviewError(DECISION_BLOCK, "BLOCK_SKILL_SCOPE_SKILL_FIELDS", path)
        target_skill_id = skill.get("target_skill_id")
        package_id = skill.get("package_id")
        if not isinstance(target_skill_id, str) or package_id != f"vcp:{target_skill_id}":
            raise D8ReviewError(DECISION_BLOCK, "BLOCK_SKILL_SCOPE_IDENTITY_BINDING", path)
        if package_id in package_ids:
            raise D8ReviewError(DECISION_BLOCK, "BLOCK_SKILL_SCOPE_DUPLICATE_PACKAGE", f"{path}.package_id")
        package_ids.add(package_id)
        if skill.get("lifecycle_state") != "CANDIDATE":
            raise D8ReviewError(DECISION_BLOCK, "BLOCK_SKILL_SCOPE_LIFECYCLE_EXPANSION", f"{path}.lifecycle_state")
        for key in ("source_manifest_sha256", "contract_payload_sha256", "manifest_sha256"):
            if not is_sha256(skill.get(key)):
                raise D8ReviewError(DECISION_BLOCK, "BLOCK_SKILL_SCOPE_SHA256", f"{path}.{key}")

    return {
        "state": "PASS_D8_SKILL_LIFECYCLE_CANDIDATE_SCOPE_REVIEW",
        "reviewer_version": REVIEWER_VERSION,
        "review_scope": "SKILL_REVIEW_LIFECYCLE_CANDIDATE_ONLY",
        "final_decision": DECISION_HOLD,
        "reason_codes": [
            "PASS_FIVE_SKILL_HASH_BOUND_CANDIDATE_SCOPE",
            "HOLD_G8_FOUNDER_SEAL_REQUIRED",
        ],
        "skills_reviewed": 5,
        "lifecycle_state": "CANDIDATE",
        "founder_seal_required": True,
        "authority_granted": False,
        "c1_c9_execution_authorized": False,
        "db_write": False,
        "deploy": False,
        "restart": False,
        "registry_write": False,
    }


def validate_request_schema(request: dict[str, Any]) -> None:
    required_types: dict[str, type] = {
        "schema_version": str,
        "packet_type": str,
        "run_id": str,
        "created_at": str,
        "expires_at": str,
        "state": str,
        "requested_decision": str,
        "only_request": str,
        "canary_started": bool,
        "d8_decision": str,
        "single_use": bool,
        "request_self_hash_algorithm": str,
        "request_self_sha256": str,
        "bindings": dict,
        "atomic_gate": dict,
        "non_execution_assertions": dict,
    }
    for key, expected_type in required_types.items():
        if key not in request or not isinstance(request[key], expected_type):
            raise D8ReviewError(DECISION_BLOCK, "BLOCK_SCHEMA_REQUIRED_FIELD", f"$.{key}")
    if request["schema_version"] != REQUEST_SCHEMA_VERSION:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_SCHEMA_VERSION_UNSUPPORTED", "$.schema_version")
    if request["packet_type"] != "D8_REVIEW_REQUEST":
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_SCHEMA_PACKET_TYPE", "$.packet_type")
    if request["state"] != "PENDING_TOTAL_FIELD_D8_DECISION":
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_SCHEMA_REQUEST_STATE", "$.state")
    requested = request["requested_decision"]
    if requested not in SUPPORTED_REQUESTED_DECISIONS or request["only_request"] != requested:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_SCHEMA_DECISION_SCOPE", "$.requested_decision")
    validate_offline_build_scope(request)
    if request["canary_started"] is not False or request["d8_decision"] != "PENDING":
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_REQUEST_NOT_PENDING", "$.d8_decision")
    if request["single_use"] is not True:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_SCHEMA_SINGLE_USE_REQUIRED", "$.single_use")
    bindings = request["bindings"]
    if not is_sha256(bindings.get("new_archive_manifest_sha256")):
        raise D8ReviewError(
            DECISION_BLOCK,
            "BLOCK_SCHEMA_SOURCE_MANIFEST_SHA256",
            "$.bindings.new_archive_manifest_sha256",
        )
    injection_path = recursive_authority_injection(request)
    if injection_path is not None:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_FORBIDDEN_AUTHORITY_INJECTION", injection_path)
    if request["request_self_hash_algorithm"] != REQUEST_SELF_HASH_ALGORITHM:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_REQUEST_SELF_HASH_ALGORITHM", "$.request_self_hash_algorithm")
    if not is_sha256(request["request_self_sha256"]):
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_REQUEST_SELF_SHA256", "$.request_self_sha256")
    self_hash_input = dict(request)
    expected_self_hash = self_hash_input.pop("request_self_sha256")
    if sha256_bytes(canonical_json_bytes(self_hash_input)) != expected_self_hash:
        raise D8ReviewError(DECISION_HOLD, "HOLD_REQUEST_SELF_HASH_MISMATCH", "$.request_self_sha256")


def relative_request_path(request_path: Path, repo_root: Path) -> str:
    try:
        return request_path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_REQUEST_OUTSIDE_REPOSITORY", str(request_path)) from exc


def verify_manifest(
    manifest_path: Path,
    expected_manifest_sha256: str,
    request_path: Path,
    repo_root: Path,
) -> dict[str, Any]:
    actual_manifest_sha256 = sha256_file(manifest_path)
    if actual_manifest_sha256 != expected_manifest_sha256:
        raise D8ReviewError(DECISION_HOLD, "HOLD_MANIFEST_SHA256_MISMATCH", str(manifest_path))
    manifest = load_object(manifest_path, "MANIFEST")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_MANIFEST_FILES_SCHEMA", "$.files")
    request_rel = relative_request_path(request_path, repo_root)
    seen: set[str] = set()
    verified: list[dict[str, Any]] = []
    for index, entry in enumerate(files):
        if not isinstance(entry, dict):
            raise D8ReviewError(DECISION_BLOCK, "BLOCK_MANIFEST_ENTRY_SCHEMA", f"$.files[{index}]")
        raw_path = entry.get("path")
        if raw_path in seen:
            raise D8ReviewError(DECISION_BLOCK, "BLOCK_MANIFEST_DUPLICATE_PATH", f"$.files[{index}].path")
        source = safe_repo_path(repo_root, raw_path, f"$.files[{index}].path")
        expected_hash = entry.get("sha256")
        expected_size = entry.get("size_bytes", entry.get("size"))
        if not is_sha256(expected_hash) or not isinstance(expected_size, int) or expected_size < 0:
            raise D8ReviewError(DECISION_BLOCK, "BLOCK_MANIFEST_ENTRY_SCHEMA", f"$.files[{index}]")
        if not source.is_file():
            raise D8ReviewError(DECISION_HOLD, "HOLD_MANIFEST_FILE_MISSING", str(raw_path))
        actual_hash = sha256_file(source)
        actual_size = source.stat().st_size
        if actual_hash != expected_hash or actual_size != expected_size:
            raise D8ReviewError(DECISION_HOLD, "HOLD_MANIFEST_FILE_HASH_OR_SIZE_MISMATCH", str(raw_path))
        seen.add(str(raw_path))
        verified.append({"path": raw_path, "sha256": actual_hash, "size_bytes": actual_size})
    if request_rel not in seen:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_REQUEST_NOT_BOUND_BY_MANIFEST", request_rel)
    return {
        "actual_sha256": actual_manifest_sha256,
        "files_verified": len(verified),
        "verified_files": verified,
    }


def payload_aggregate_sha256(files: list[dict[str, Any]]) -> str:
    lines = "".join(f"{entry['sha256']}  {entry['path']}\n" for entry in files)
    return sha256_bytes(lines.encode("utf-8"))


def verify_archive_entries(archive_root: Path, files: Any, expected_count: int | None = None) -> list[dict[str, Any]]:
    if not isinstance(files, list) or not files:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_SOURCE_FILES_SCHEMA", "$.files")
    if expected_count is not None and len(files) != expected_count:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_SOURCE_FILE_COUNT", "$.files")
    seen: set[str] = set()
    verified: list[dict[str, Any]] = []
    for index, entry in enumerate(files):
        if not isinstance(entry, dict):
            raise D8ReviewError(DECISION_BLOCK, "BLOCK_SOURCE_FILE_ENTRY_SCHEMA", f"$.files[{index}]")
        raw_path = entry.get("path")
        if raw_path in seen:
            raise D8ReviewError(DECISION_BLOCK, "BLOCK_SOURCE_DUPLICATE_PATH", f"$.files[{index}].path")
        source = safe_repo_path(archive_root, raw_path, f"$.files[{index}].path")
        expected_hash = entry.get("sha256")
        expected_size = entry.get("size_bytes", entry.get("size"))
        if not is_sha256(expected_hash) or not isinstance(expected_size, int) or expected_size < 0:
            raise D8ReviewError(DECISION_BLOCK, "BLOCK_SOURCE_FILE_ENTRY_SCHEMA", f"$.files[{index}]")
        if not source.is_file():
            raise D8ReviewError(DECISION_HOLD, "HOLD_SOURCE_FILE_MISSING", str(raw_path))
        actual_hash = sha256_file(source)
        actual_size = source.stat().st_size
        if actual_hash != expected_hash or actual_size != expected_size:
            raise D8ReviewError(DECISION_HOLD, "HOLD_SOURCE_FILE_HASH_OR_SIZE_MISMATCH", str(raw_path))
        seen.add(str(raw_path))
        verified.append({"path": raw_path, "sha256": actual_hash, "size_bytes": actual_size})
    return verified


def verify_source_archive_binding(
    request: dict[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    bindings = request["bindings"]
    required_binding_fields = {
        "new_archive_path": str,
        "complete_handoff_receipt_path": str,
        "complete_handoff_receipt_sha256": str,
        "complete_landing_manifest_path": str,
        "complete_landing_manifest_sha256": str,
        "new_archive_manifest_path": str,
        "new_archive_manifest_sha256": str,
        "landing_payload_count": int,
        "landing_payload_aggregate_sha256": str,
        "aggregate_algorithm_version": str,
        "aggregate_ordering": str,
        "landing_payload_input_paths": list,
    }
    for key, expected_type in required_binding_fields.items():
        if not isinstance(bindings.get(key), expected_type):
            raise D8ReviewError(DECISION_BLOCK, "BLOCK_SOURCE_BINDING_SCHEMA", f"$.bindings.{key}")
    for key in (
        "complete_handoff_receipt_sha256",
        "complete_landing_manifest_sha256",
        "new_archive_manifest_sha256",
        "landing_payload_aggregate_sha256",
    ):
        if not is_sha256(bindings[key]):
            raise D8ReviewError(DECISION_BLOCK, "BLOCK_SOURCE_BINDING_SHA256", f"$.bindings.{key}")

    archive_root = safe_repo_path(repo_root, bindings["new_archive_path"], "$.bindings.new_archive_path")
    if not archive_root.is_dir():
        raise D8ReviewError(DECISION_HOLD, "HOLD_SOURCE_ARCHIVE_MISSING", bindings["new_archive_path"])
    receipt_path = safe_repo_path(repo_root, bindings["complete_handoff_receipt_path"], "$.bindings.complete_handoff_receipt_path")
    landing_path = safe_repo_path(repo_root, bindings["complete_landing_manifest_path"], "$.bindings.complete_landing_manifest_path")
    archive_manifest_path = safe_repo_path(repo_root, bindings["new_archive_manifest_path"], "$.bindings.new_archive_manifest_path")
    for path, expected_hash, reason in (
        (receipt_path, bindings["complete_handoff_receipt_sha256"], "HANDOFF_RECEIPT"),
        (landing_path, bindings["complete_landing_manifest_sha256"], "LANDING_MANIFEST"),
        (archive_manifest_path, bindings["new_archive_manifest_sha256"], "ARCHIVE_MANIFEST"),
    ):
        if not path.is_file():
            raise D8ReviewError(DECISION_HOLD, f"HOLD_{reason}_MISSING", str(path))
        if sha256_file(path) != expected_hash:
            raise D8ReviewError(DECISION_HOLD, f"HOLD_{reason}_SHA256_MISMATCH", str(path))

    receipt = load_object(receipt_path, "HANDOFF_RECEIPT")
    landing = load_object(landing_path, "LANDING_MANIFEST")
    archive_manifest = load_object(archive_manifest_path, "ARCHIVE_MANIFEST")
    if receipt.get("source_bytes") != "PASS_10_OF_10" or receipt.get("counts", {}).get("total_files") != 10:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_SOURCE_10_OF_10_NOT_DECLARED", str(receipt_path))
    receipt_verified = verify_archive_entries(archive_root, receipt.get("files"), expected_count=10)
    landing_verified = verify_archive_entries(archive_root, landing.get("files"), expected_count=10)
    receipt_set = {(item["path"], item["sha256"], item["size_bytes"]) for item in receipt_verified}
    landing_set = {(item["path"], item["sha256"], item["size_bytes"]) for item in landing_verified}
    if receipt_set != landing_set:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_SOURCE_RECEIPT_LANDING_SET_MISMATCH")
    archive_verified = verify_archive_entries(archive_root, archive_manifest.get("files"))
    if archive_manifest.get("manifest_self_hash_excluded") is not True:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_ARCHIVE_MANIFEST_SELF_HASH_RULE")
    if bindings["landing_payload_count"] != 10:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_LANDING_PAYLOAD_COUNT", "$.bindings.landing_payload_count")
    if bindings["aggregate_algorithm_version"] != AGGREGATE_ALGORITHM_VERSION:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_LANDING_AGGREGATE_ALGORITHM_VERSION")
    if bindings["aggregate_ordering"] != AGGREGATE_ORDERING:
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_LANDING_AGGREGATE_ORDERING")
    landing_paths = [item["path"] for item in landing_verified]
    if bindings["landing_payload_input_paths"] != landing_paths:
        raise D8ReviewError(DECISION_HOLD, "HOLD_LANDING_PAYLOAD_INPUT_PATHS_MISMATCH")
    aggregate_actual = payload_aggregate_sha256(landing_verified)
    if aggregate_actual != bindings["landing_payload_aggregate_sha256"]:
        raise D8ReviewError(DECISION_HOLD, "HOLD_LANDING_PAYLOAD_AGGREGATE_MISMATCH")

    candidate_binding = landing.get("candidate_binding")
    if not isinstance(candidate_binding, dict) or candidate_binding.get("status") != "PASS":
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_CANDIDATE_BINDING_STATUS")
    receipt_hashes = {item["sha256"]: item["path"] for item in receipt_verified}
    for key in (
        "submitted_manifest_self_sha256",
        "total_field_review_receipt_sha256",
        "total_field_review_manifest_sha256",
    ):
        if candidate_binding.get(key) not in receipt_hashes:
            raise D8ReviewError(DECISION_HOLD, "HOLD_CANDIDATE_BINDING_HASH_NOT_IN_10_OF_10", f"$.candidate_binding.{key}")
    submitted_manifest_rel = receipt_hashes[candidate_binding["submitted_manifest_self_sha256"]]
    submitted_manifest = load_object(safe_repo_path(archive_root, submitted_manifest_rel, "$.candidate_binding.submitted_manifest"), "SUBMITTED_MANIFEST")
    if submitted_manifest.get("scope_aggregate_sha256") != candidate_binding.get("submitted_scope_sha256"):
        raise D8ReviewError(DECISION_HOLD, "HOLD_CANDIDATE_SCOPE_BINDING_MISMATCH")
    expiry = landing.get("expiry")
    if not isinstance(expiry, dict) or expiry.get("status") != "PASS":
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_SOURCE_EXPIRY_BINDING")
    landing_reference_expires_at = parse_utc(expiry.get("reference_expires_at"), "$.expiry.reference_expires_at")
    return {
        "archive_path": bindings["new_archive_path"],
        "source_files_verified": len(receipt_verified),
        "archive_manifest_files_verified": len(archive_verified),
        "archive_manifest_sha256": bindings["new_archive_manifest_sha256"],
        "landing_payload_count": len(landing_verified),
        "landing_payload_aggregate_sha256": aggregate_actual,
        "aggregate_algorithm_version": AGGREGATE_ALGORITHM_VERSION,
        "aggregate_ordering": AGGREGATE_ORDERING,
        "landing_payload_input_paths": landing_paths,
        "candidate_binding": "PASS",
        "landing_reference_expires_at": landing_reference_expires_at,
    }


def find_replay(replay_root: Path | None, source_manifest_sha256: str, output_dir: Path) -> str | None:
    if replay_root is None or not replay_root.is_dir():
        return None
    for decision_path in sorted(replay_root.rglob("TOTAL_FIELD_D8_DECISION.json")):
        try:
            decision_path.resolve().relative_to(output_dir.resolve())
            continue
        except ValueError:
            pass
        try:
            existing = json.loads(decision_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if isinstance(existing, dict) and existing.get("source_manifest_sha256") == source_manifest_sha256:
            return decision_path.as_posix()
    return None


def fine_grain_check(request: dict[str, Any]) -> dict[str, Any]:
    _parsed, units = analyze_candidate(request, "$.review_request")
    counts = {decision: sum(unit["decision"] == decision for unit in units) for decision in FINE_GRAIN_DECISIONS}
    blocked = sorted(decision for decision in BLOCK_FINE_GRAIN_DECISIONS if counts.get(decision, 0))
    held = counts.get("HOLD_FOR_EVIDENCE", 0) > 0
    return {"review_unit_count": len(units), "counts": counts, "blocked_decisions": blocked, "held": held}


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def decision_state(final_decision: str) -> str:
    if final_decision == DECISION_ALLOW:
        return "PASS_HASH_BOUND_ISOLATED_CANARY_ONLY"
    if final_decision == DECISION_ALLOW_OFFLINE_BUILD:
        return "PASS_HASH_BOUND_OFFLINE_BUILD_ONLY"
    if final_decision == DECISION_BLOCK:
        return "BLOCK_TOTAL_FIELD_D8_REVIEW"
    return "HOLD_TOTAL_FIELD_D8_REVIEW"


def existing_result(
    output_dir: Path,
    expected_manifest_sha256: str,
    request_sha256: str | None,
) -> dict[str, Any] | None:
    required = {
        "TOTAL_FIELD_D8_DECISION.json",
        "REVIEW_EVIDENCE.json",
        "TOTAL_FIELD_D8_REVIEW_RECEIPT.json",
        "SHA256_MANIFEST.json",
    }
    if not output_dir.is_dir() or {path.name for path in output_dir.iterdir() if path.is_file()} != required:
        return None
    output_manifest_path = output_dir / "SHA256_MANIFEST.json"
    output_manifest = load_object(output_manifest_path, "OUTPUT_MANIFEST")
    files = output_manifest.get("files")
    if not isinstance(files, list) or len(files) != 3:
        return None
    for entry in files:
        if not isinstance(entry, dict) or Path(str(entry.get("path"))).name != entry.get("path"):
            return None
        path = output_dir / entry["path"]
        if not path.is_file() or sha256_file(path) != entry.get("sha256") or path.stat().st_size != entry.get("size_bytes"):
            return None
    decision = load_object(output_dir / "TOTAL_FIELD_D8_DECISION.json", "EXISTING_DECISION")
    if decision.get("source_manifest_sha256") != expected_manifest_sha256:
        return None
    if decision.get("source_request_sha256") != request_sha256:
        return None
    result = {
        "state": decision.get("state"),
        "final_decision": decision.get("final_decision"),
        "reason_codes": decision.get("reason_codes", []),
        "output_dir": output_dir.as_posix(),
        "decision_sha256": sha256_file(output_dir / "TOTAL_FIELD_D8_DECISION.json"),
        "evidence_sha256": sha256_file(output_dir / "REVIEW_EVIDENCE.json"),
        "receipt_sha256": sha256_file(output_dir / "TOTAL_FIELD_D8_REVIEW_RECEIPT.json"),
        "manifest_sha256": sha256_file(output_manifest_path),
        "canary_started": False,
        "reused_existing_result": True,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return result


def correction_zh_tw(reason_codes: list[str]) -> str:
    if "HOLD_REQUEST_EXPIRED" in reason_codes or "HOLD_EXPLICIT_EXPIRY_REQUIRED" in reason_codes:
        return "送審封套已逾期或缺少有效期限；請由 Founder 重新簽發綁定相同來源雜湊、明確 TTL 與 single-use 的 D8_REVIEW_REQUEST。"
    if any("MANIFEST" in code or "HASH" in code or "BINDING" in code for code in reason_codes):
        return "雜湊或綁定驗證未通過；請重新產生不可變送審封套並提供可重算的來源 manifest，不得改寫既有證據。"
    if any("SCHEMA" in code for code in reason_codes):
        return "送審封包不符合既有 D8 Schema；請只修正缺少或不合法欄位後重新送審，不得加入裁決或執行權。"
    if any("AUTHORITY" in code for code in reason_codes):
        return "送審封包含權威注入；請移除 final_decision、execution authority 或其他自行擴權欄位後重新送審。"
    if "HOLD_REQUEST_REPLAY" in reason_codes:
        return "此 single-use 送審封套已處理；請使用既有 hash-bound 裁決，不得重放。"
    return "請依 reason_codes 修正唯一失敗項目後，以新的 hash-bound single-use 封套重新送審。"


def review_once(
    *,
    request_path: Path,
    manifest_path: Path,
    expected_manifest_sha256: str,
    output_dir: Path,
    repo_root: Path,
    replay_root: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not is_sha256(expected_manifest_sha256):
        raise D8ReviewError(DECISION_BLOCK, "BLOCK_EXPECTED_MANIFEST_SHA256_INVALID", "--manifest-sha256")
    reviewed_at = (now or utc_now()).astimezone(timezone.utc)
    request_sha256 = sha256_file(request_path) if request_path.is_file() else None
    reused = existing_result(output_dir, expected_manifest_sha256, request_sha256)
    if reused is not None:
        return reused
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty output directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    reason_codes: list[str] = []
    checks: dict[str, Any] = {
        "reviewer_module": "PASS",
        "llm_call": "NO",
        "canary_started": "NO",
        "deploy": "NO",
        "db_write": "NO",
    }
    request: dict[str, Any] = {}
    manifest_result: dict[str, Any] = {}
    source_binding_result: dict[str, Any] = {}
    fine_grain_result: dict[str, Any] = {}
    offline_build_result: dict[str, Any] = {}
    final_decision = DECISION_ALLOW
    error_path: str | None = None
    try:
        if not request_path.is_file():
            raise D8ReviewError(DECISION_HOLD, "HOLD_REQUEST_FILE_MISSING", str(request_path))
        request = load_object(request_path, "REQUEST")
        validate_request_schema(request)
        final_decision = SUPPORTED_REQUESTED_DECISIONS[request["requested_decision"]]
        checks["request_schema"] = "PASS"
        offline_build_result = verify_offline_build_bindings(request, repo_root)
        checks["offline_build_scope"] = "PASS" if offline_build_result else "NOT_APPLICABLE"
        manifest_result = verify_manifest(
            manifest_path,
            expected_manifest_sha256,
            request_path,
            repo_root,
        )
        checks["manifest_sha256"] = "PASS"
        checks["manifest_files"] = f"PASS_{manifest_result['files_verified']}_OF_{manifest_result['files_verified']}"
        source_binding_result = verify_source_archive_binding(request, repo_root)
        checks["source_10_of_10"] = "PASS_10_OF_10"
        checks["source_archive_manifest"] = "PASS"
        checks["candidate_binding"] = "PASS"
        checks["single_use"] = "PASS_REVIEWER_ENFORCED"
        created_at = parse_utc(request["created_at"], "$.created_at")
        expiry = parse_utc(request["expires_at"], "$.expires_at")
        if expiry <= created_at:
            raise D8ReviewError(DECISION_BLOCK, "BLOCK_REQUEST_TTL_INVALID", "$.expires_at")
        if reviewed_at >= expiry:
            raise D8ReviewError(DECISION_HOLD, "HOLD_REQUEST_EXPIRED", "$.expires_at")
        checks["expiry"] = "PASS"
        replay_path = find_replay(replay_root, expected_manifest_sha256, output_dir)
        if replay_path is not None:
            raise D8ReviewError(DECISION_HOLD, "HOLD_REQUEST_REPLAY", replay_path)
        checks["replay"] = "PASS"
        fine_grain_result = fine_grain_check(request)
        checks["fine_grain_reviewer"] = "PASS"
        if fine_grain_result["blocked_decisions"]:
            raise D8ReviewError(
                DECISION_BLOCK,
                "BLOCK_FINE_GRAIN_REVIEW",
                ",".join(fine_grain_result["blocked_decisions"]),
            )
        if fine_grain_result["held"]:
            raise D8ReviewError(DECISION_HOLD, "HOLD_FINE_GRAIN_EVIDENCE_REQUIRED")
        reason_codes.append("PASS_DETERMINISTIC_RULES_AND_HASH_BINDING")
    except D8ReviewError as exc:
        final_decision = exc.disposition
        reason_codes.append(exc.reason_code)
        error_path = exc.path
        checks.setdefault("request_schema", "BLOCK" if "SCHEMA" in exc.reason_code else "NOT_REACHED")
        checks.setdefault(
            "offline_build_scope",
            "HOLD" if "OFFLINE_BUILD" in exc.reason_code and exc.disposition == DECISION_HOLD else (
                "BLOCK" if "OFFLINE_BUILD" in exc.reason_code else "NOT_REACHED"
            ),
        )
        checks.setdefault("manifest_sha256", "HOLD" if "MANIFEST" in exc.reason_code else "NOT_REACHED")
        checks.setdefault("source_10_of_10", "HOLD" if "SOURCE" in exc.reason_code else "NOT_REACHED")
        checks.setdefault("candidate_binding", "HOLD" if "BINDING" in exc.reason_code else "NOT_REACHED")
        checks.setdefault("single_use", "NOT_REACHED")
        checks.setdefault("expiry", "HOLD" if "EXPIR" in exc.reason_code else "NOT_REACHED")
        checks.setdefault("replay", "HOLD" if "REPLAY" in exc.reason_code else "NOT_REACHED")
        checks.setdefault("fine_grain_reviewer", "NOT_REACHED")

    request_run_id = request.get("run_id") if isinstance(request.get("run_id"), str) else "UNBOUND_INVALID_REQUEST"
    output_run_id = f"{request_run_id}_TOTAL_FIELD_D8_DECISION"
    decision = {
        "schema_version": "W7TP-TOTAL-FIELD-D8-DECISION/1.0",
        "packet_type": "TOTAL_FIELD_D8_DECISION",
        "run_id": output_run_id,
        "decided_at": utc_text(reviewed_at),
        "authority": "TOTAL_FIELD_DETERMINISTIC_RULE_REVIEWER",
        "reviewer_version": REVIEWER_VERSION,
        "state": decision_state(final_decision),
        "final_decision": final_decision,
        "decision_scope": final_decision if final_decision in ALLOW_DECISIONS else None,
        "reason_codes": reason_codes,
        "correction_zh_tw": None if final_decision in ALLOW_DECISIONS else correction_zh_tw(reason_codes),
        "rule_refs": RULE_REFS,
        "error_path": error_path,
        "source_request_path": relative_request_path(request_path, repo_root) if request_path.is_file() else str(request_path),
        "source_request_sha256": request_sha256,
        "source_manifest_sha256": expected_manifest_sha256,
        "source_archive_manifest_sha256": source_binding_result.get("archive_manifest_sha256"),
        "source_files_verified": source_binding_result.get("source_files_verified", 0),
        "input_final_decision_field": "absent",
        "single_use": True,
        "production_execution_authority": False,
        "deployment_authorized": False,
        "offline_image_build_authorized": final_decision == DECISION_ALLOW_OFFLINE_BUILD,
        "image_qualification_authorized": final_decision == DECISION_ALLOW_OFFLINE_BUILD,
        "image_pull_authorized": False,
        "build_network_authorized": False,
        "c1_c9_execution_authorized": final_decision == DECISION_ALLOW,
        "canonical_or_pointer_write_authorized": False,
        "canary_started": False,
        "side_effects_executed": False,
    }
    evidence = {
        "schema_version": "W7TP-TOTAL-FIELD-D8-REVIEW-EVIDENCE/1.0",
        "packet_type": "REVIEW_EVIDENCE",
        "run_id": output_run_id,
        "reviewed_at": utc_text(reviewed_at),
        "reviewer_version": REVIEWER_VERSION,
        "source_request_sha256": request_sha256,
        "source_manifest_sha256_expected": expected_manifest_sha256,
        "source_manifest_sha256_actual": sha256_file(manifest_path) if manifest_path.is_file() else None,
        "checks": checks,
        "manifest_files_verified": manifest_result.get("files_verified", 0),
        "source_binding": {
            key: utc_text(value) if isinstance(value, datetime) else value
            for key, value in source_binding_result.items()
        },
        "offline_build_binding": offline_build_result,
        "fine_grain_review": fine_grain_result,
        "reason_codes": reason_codes,
        "rule_refs": RULE_REFS,
        "forbidden_actions": {
            "llm_call": False,
            "canary_start": False,
            "deploy": False,
            "restart": False,
            "db_write": False,
            "canonical_write": False,
            "pointer_write": False,
            "production_execution": False,
        },
    }
    decision_path = output_dir / "TOTAL_FIELD_D8_DECISION.json"
    evidence_path = output_dir / "REVIEW_EVIDENCE.json"
    write_json(decision_path, decision)
    write_json(evidence_path, evidence)
    receipt = {
        "schema_version": "W7TP-TOTAL-FIELD-D8-REVIEW-RECEIPT/1.0",
        "packet_type": "TOTAL_FIELD_D8_REVIEW_RECEIPT",
        "run_id": output_run_id,
        "received_and_decided_at": utc_text(reviewed_at),
        "reviewer_version": REVIEWER_VERSION,
        "source_request_sha256": request_sha256,
        "source_manifest_sha256": expected_manifest_sha256,
        "final_decision": final_decision,
        "reason_codes": reason_codes,
        "decision_sha256": sha256_file(decision_path),
        "review_evidence_sha256": sha256_file(evidence_path),
        "single_use_consumed": True,
        "replay_disposition": "RETURN_IDENTICAL_EXISTING_RESULT",
        "canary_started": False,
    }
    receipt_path = output_dir / "TOTAL_FIELD_D8_REVIEW_RECEIPT.json"
    write_json(receipt_path, receipt)
    output_manifest = {
        "schema_version": "W7TP-TOTAL-FIELD-D8-DECISION-MANIFEST/1.0",
        "algorithm": "SHA-256",
        "run_id": output_run_id,
        "created_at": utc_text(reviewed_at),
        "manifest_self_hash_excluded": True,
        "source_manifest_sha256": expected_manifest_sha256,
        "reviewer_version": REVIEWER_VERSION,
        "files": [
            {
                "path": decision_path.name,
                "sha256": sha256_file(decision_path),
                "size_bytes": decision_path.stat().st_size,
            },
            {
                "path": evidence_path.name,
                "sha256": sha256_file(evidence_path),
                "size_bytes": evidence_path.stat().st_size,
            },
            {
                "path": receipt_path.name,
                "sha256": sha256_file(receipt_path),
                "size_bytes": receipt_path.stat().st_size,
            },
        ],
    }
    manifest_output_path = output_dir / "SHA256_MANIFEST.json"
    write_json(manifest_output_path, output_manifest)
    result = {
        "state": decision["state"],
        "final_decision": final_decision,
        "reason_codes": reason_codes,
        "output_dir": output_dir.as_posix(),
        "decision_sha256": sha256_file(decision_path),
        "evidence_sha256": sha256_file(evidence_path),
        "receipt_sha256": sha256_file(receipt_path),
        "manifest_sha256": sha256_file(manifest_output_path),
        "canary_started": False,
        "reused_existing_result": False,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return result


def intake_envelopes(intake_dir: Path) -> Iterable[Path]:
    if not intake_dir.is_dir():
        return []
    return sorted(intake_dir.glob("*/D8_INTAKE_ENVELOPE.json"))


def status_payload(intake_dir: Path, output_root: Path, healthcheck: bool) -> dict[str, Any]:
    module_path = Path(__file__)
    checks = {
        "reviewer_executable_exists": module_path.is_file() and os.access(module_path, os.X_OK),
        "reviewer_module_imported": REVIEWER_VERSION.startswith("w7tp-true8d-d8-reviewer-entrypoint/"),
        "intake_readable": intake_dir.is_dir() and os.access(intake_dir, os.R_OK),
        "evidence_output_writable": output_root.is_dir() and os.access(output_root, os.W_OK),
        "status_command": True,
    }
    pending = sum(1 for _ in intake_envelopes(intake_dir))
    state = "PASS_D8_REVIEWER_FUNCTIONAL_HEALTH" if all(checks.values()) else "HOLD_D8_REVIEWER_FUNCTIONAL_HEALTH"
    return {
        "state": state,
        "reviewer_version": REVIEWER_VERSION,
        "intake_dir": intake_dir.as_posix(),
        "output_root": output_root.as_posix(),
        "pending_count": pending,
        "checks": checks,
        "healthcheck": healthcheck,
        "read_only_status": True,
    }


def run_serve(args: argparse.Namespace) -> int:
    intake_dir = args.intake_dir
    output_root = args.output_root
    while True:
        for envelope_path in intake_envelopes(intake_dir):
            envelope = load_object(envelope_path, "INTAKE_ENVELOPE")
            request_rel = envelope.get("request_path")
            manifest_rel = envelope.get("manifest_path")
            manifest_sha256 = envelope.get("manifest_sha256")
            request_path = safe_repo_path(args.repo_root, request_rel, "$.request_path")
            manifest_path = safe_repo_path(args.repo_root, manifest_rel, "$.manifest_path")
            envelope_id = sha256_bytes(canonical_json_bytes(envelope))[:20]
            target = output_root / envelope_id
            if target.exists() and any(target.iterdir()):
                continue
            review_once(
                request_path=request_path,
                manifest_path=manifest_path,
                expected_manifest_sha256=manifest_sha256,
                output_dir=target,
                repo_root=args.repo_root,
                replay_root=output_root,
            )
        if args.once:
            return 0
        time.sleep(args.poll_seconds)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="poll hash-bound intake envelopes")
    serve.add_argument("--intake-dir", type=Path, required=True)
    serve.add_argument("--output-root", type=Path, required=True)
    serve.add_argument("--repo-root", type=Path, default=Path("/formal"))
    serve.add_argument("--poll-seconds", type=float, default=2.0)
    serve.add_argument("--once", action="store_true")

    once = subparsers.add_parser("review-once", help="review one request and exact manifest hash")
    once.add_argument("--request-path", type=Path, required=True)
    once.add_argument("--manifest-path", type=Path, required=True)
    once.add_argument("--manifest-sha256", required=True)
    once.add_argument("--output-dir", type=Path, required=True)
    once.add_argument("--repo-root", type=Path, default=Path("/formal"))
    once.add_argument("--replay-root", type=Path)

    status = subparsers.add_parser("status", help="read-only reviewer and intake status")
    status.add_argument("--intake-dir", type=Path, required=True)
    status.add_argument("--output-root", type=Path, required=True)
    status.add_argument("--healthcheck", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "serve":
            return run_serve(args)
        if args.command == "review-once":
            result = review_once(
                request_path=args.request_path,
                manifest_path=args.manifest_path,
                expected_manifest_sha256=args.manifest_sha256,
                output_dir=args.output_dir,
                repo_root=args.repo_root,
                replay_root=args.replay_root,
            )
            return 0 if result["final_decision"] in ALLOW_DECISIONS else 2
        payload = status_payload(args.intake_dir, args.output_root, args.healthcheck)
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 0 if payload["state"].startswith("PASS") else 2
    except (D8ReviewError, FileExistsError, OSError) as exc:
        print(json.dumps({"state": "BLOCK_D8_REVIEWER_ENTRYPOINT", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
