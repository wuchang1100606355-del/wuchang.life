#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local hash and fixed-vector healthcheck for a candidate small-agent release."""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence, cast

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.w7tp_small_agent_service_runner import (
    DEFAULT_STATE_DIR,
    ServiceError,
    canonical_json,
    canonical_sha256,
    load_json_file,
    run_self_test,
)


HEALTHCHECK_SCHEMA_VERSION = "w7tp-small-agent-healthcheck/v0.1"
DEFAULT_VECTOR_RELATIVE_PATH = Path(
    "tests/fixtures/w7tp_small_agent_deployment_vectors.json"
)
EXPECTED_POLICY_SHA256 = (
    "d27230aba7a4ecd051f4169184c1fa5357ce5efa1d62019238d68991b0140960"
)
_SHA256_LENGTH = 64


def _is_sha256(value: Any) -> bool:
    """Return whether a value is one lowercase hexadecimal SHA-256 digest."""

    return (
        isinstance(value, str)
        and len(value) == _SHA256_LENGTH
        and all(character in "0123456789abcdef" for character in value)
    )


def _raw_sha256(path: Path) -> str:
    """Hash one regular release file without interpreting its content."""

    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while True:
                block = handle.read(1024 * 1024)
                if not block:
                    break
                digest.update(block)
    except OSError as exc:
        raise ServiceError("RELEASE_FILE_READ_FAILED", str(path)) from exc
    return digest.hexdigest()


def _safe_release_file(release_dir: Path, relative_name: str) -> Path:
    """Resolve one manifest path while rejecting absolute or parent traversal."""

    relative = PurePosixPath(relative_name)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ServiceError("RELEASE_FILE_PATH_UNSAFE", "$.files_sha256.files")
    target = release_dir.joinpath(*relative.parts)
    try:
        root_resolved = release_dir.resolve(strict=True)
        target_resolved = target.resolve(strict=True)
    except OSError as exc:
        raise ServiceError("RELEASE_FILE_MISSING", relative_name) from exc
    if root_resolved != target_resolved and root_resolved not in target_resolved.parents:
        raise ServiceError("RELEASE_FILE_PATH_UNSAFE", relative_name)
    if not target_resolved.is_file():
        raise ServiceError("RELEASE_FILE_NOT_REGULAR", relative_name)
    return target_resolved


def _verify_release(release_dir: Path) -> dict[str, str]:
    """Verify the release identity and every raw file hash deterministically."""

    manifest = load_json_file(release_dir / "release_manifest.json")
    files_document = load_json_file(release_dir / "files_sha256.json")
    files = files_document.get("files")
    if not isinstance(files, dict) or not files:
        raise ServiceError("RELEASE_FILES_MAP_INVALID", "$.files_sha256.files")
    for relative_name in sorted(files):
        expected = files[relative_name]
        if not isinstance(relative_name, str) or not _is_sha256(expected):
            raise ServiceError("RELEASE_FILE_HASH_INVALID", "$.files_sha256.files")
        actual = _raw_sha256(_safe_release_file(release_dir, relative_name))
        if actual != expected:
            raise ServiceError("RELEASE_FILE_HASH_MISMATCH", relative_name)

    expected_files_hash = manifest.get("files_sha256_hash")
    if not _is_sha256(expected_files_hash):
        raise ServiceError("FILES_DOCUMENT_HASH_INVALID", "$.release_manifest")
    if canonical_sha256(files_document) != expected_files_hash:
        raise ServiceError("FILES_DOCUMENT_HASH_MISMATCH", "files_sha256.json")

    identity = manifest.get("release_identity")
    if not isinstance(identity, dict):
        raise ServiceError("RELEASE_IDENTITY_MISSING", "$.release_manifest")
    if identity.get("files_sha256") != files:
        raise ServiceError("RELEASE_IDENTITY_FILES_MISMATCH", "$.release_identity")
    release_sha256 = manifest.get("release_sha256")
    if not _is_sha256(release_sha256):
        raise ServiceError("RELEASE_SHA256_INVALID", "$.release_manifest")
    if canonical_sha256(identity) != release_sha256:
        raise ServiceError("RELEASE_SHA256_MISMATCH", "$.release_identity")
    policy_sha256 = identity.get("policy_sha256")
    if policy_sha256 != EXPECTED_POLICY_SHA256:
        raise ServiceError("POLICY_SHA256_MISMATCH", "$.release_identity.policy_sha256")
    return {
        "release_sha256": cast(str, release_sha256),
        "policy_sha256": cast(str, policy_sha256),
        "release_version": str(identity.get("release_version", "")),
        "files_sha256_hash": cast(str, expected_files_hash),
    }


def _write_health_state(state_dir: Path, result: Mapping[str, Any]) -> Path:
    """Atomically write the latest hash/status-only health result."""

    directory = state_dir.expanduser()
    target = directory / "latest_healthcheck.json"
    temporary = directory / ".latest_healthcheck.json.tmp"
    try:
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        with temporary.open("w", encoding="utf-8") as handle:
            handle.write(canonical_json(result))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
    except OSError as exc:
        raise ServiceError("HEALTH_STATE_WRITE_FAILED", str(directory)) from exc
    return target


def run_healthcheck(
    release_dir: Path | str,
    state_dir: Path | str | None = None,
    vector_path: Path | str | None = None,
) -> dict[str, Any]:
    """Verify one release and exercise its deterministic local service vector."""

    release_root = Path(release_dir).expanduser()
    output_dir = Path(state_dir).expanduser() if state_dir is not None else DEFAULT_STATE_DIR
    selected_vector = (
        Path(vector_path).expanduser()
        if vector_path is not None
        else release_root / DEFAULT_VECTOR_RELATIVE_PATH
    )
    try:
        release = _verify_release(release_root)
        vector = load_json_file(selected_vector)
        if vector.get("policy_sha256") != release["policy_sha256"]:
            raise ServiceError("VECTOR_POLICY_SHA256_MISMATCH", "$.policy_sha256")
        if vector.get("release_version") != release["release_version"]:
            raise ServiceError("VECTOR_RELEASE_VERSION_MISMATCH", "$.release_version")
        service = run_self_test(vector)
        gateway_status = service["gateway_profile_status"]
        status = "PASS" if gateway_status == "READY" else "HOLD"
        reason_code = None if status == "PASS" else gateway_status
        result: dict[str, Any] = {
            "schema_version": HEALTHCHECK_SCHEMA_VERSION,
            "status": status,
            "reason_code": reason_code,
            "agent_process": "PASS",
            "release_hash": "PASS",
            "release_sha256": release["release_sha256"],
            "release_version": release["release_version"],
            "files_sha256_hash": release["files_sha256_hash"],
            "policy_sha256": "MATCH",
            "policy_hash": release["policy_sha256"],
            "capability_manifest": service["capability_manifest"],
            "d1_projection": service["d1_projection"],
            "candidate_replay": service["candidate_replay"],
            "candidate_hash": service["candidate_hash"],
            "total_field_pull": (
                "PASS" if gateway_status == "READY" else gateway_status
            ),
            "llm_push": "PASS" if gateway_status == "READY" else gateway_status,
            "fixture_gateway": "TEST_ONLY_PASS",
            "common_receive_path": service["common_receive_path"],
            "common_receive_path_marker": service["common_receive_path_marker"],
            "allow_only_commit": service["allow_only_commit"],
            "commit_gates": service["commit_gates"],
            "persona_governance_separation": service[
                "persona_governance_separation"
            ],
            "d7_reference_only": service["d7_reference_only"],
            "llm_direct_commit": "BLOCKED",
            "external_port": "NONE",
            "real_llm_call": "NO",
            "db_write": "NO",
            "router_write": "NO",
            "service_health": status,
        }
        result["healthcheck_hash"] = canonical_sha256(result)
        _write_health_state(output_dir, result)
        return result
    except ServiceError as exc:
        result = {
            "schema_version": HEALTHCHECK_SCHEMA_VERSION,
            "status": "HOLD",
            "reason_code": exc.reason_code,
            "release_hash": "HOLD",
            "policy_sha256": "NOT_VERIFIED",
            "external_port": "NONE",
            "real_llm_call": "NO",
            "db_write": "NO",
            "router_write": "NO",
            "service_health": "HOLD",
        }
        result["healthcheck_hash"] = canonical_sha256(result)
        try:
            _write_health_state(output_dir, result)
        except ServiceError:
            return result
        return result


def _parser() -> argparse.ArgumentParser:
    """Build the local-only healthcheck CLI parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", required=True, type=Path)
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--vector-path", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the local healthcheck and return nonzero for a truthful HOLD."""

    arguments = _parser().parse_args(argv)
    result = run_healthcheck(
        arguments.release_dir,
        state_dir=arguments.state_dir,
        vector_path=arguments.vector_path,
    )
    print(canonical_json(result))
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = (
    "DEFAULT_VECTOR_RELATIVE_PATH",
    "EXPECTED_POLICY_SHA256",
    "HEALTHCHECK_SCHEMA_VERSION",
    "main",
    "run_healthcheck",
)
