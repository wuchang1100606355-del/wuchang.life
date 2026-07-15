#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local hash and fixed-vector healthcheck for a candidate small-agent release."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence, cast

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.w7tp_small_agent_service_runner import (
    DEFAULT_STATE_DIR,
    ServiceError,
    canonical_json,
    canonical_sha256,
    load_json_file,
)


HEALTHCHECK_SCHEMA_VERSION = "w7tp-small-agent-healthcheck/v0.1"
DEFAULT_VECTOR_RELATIVE_PATH = Path(
    "fixtures/w7tp_small_agent_deployment_vectors.json"
)
EXPECTED_POLICY_SHA256 = (
    "d27230aba7a4ecd051f4169184c1fa5357ce5efa1d62019238d68991b0140960"
)
_SHA256_LENGTH = 64


def _health_strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Decode health evidence while rejecting duplicate members."""

    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ServiceError("RUNTIME_HEALTH_EVIDENCE_INVALID", f"$.{key}")
        result[key] = value
    return result


def _health_reject_constant(token: str) -> None:
    """Reject non-finite numbers in installed health evidence."""

    raise ServiceError("RUNTIME_HEALTH_EVIDENCE_INVALID", f"$.{token}")


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


def _release_inventory(release_dir: Path) -> set[str]:
    """List the bounded release tree while rejecting links and special files."""

    inventory: set[str] = set()
    pending = [release_dir]
    while pending:
        directory = pending.pop()
        try:
            entries = sorted(directory.iterdir(), key=lambda item: item.name)
        except OSError as exc:
            raise ServiceError("RELEASE_INVENTORY_READ_FAILED", str(directory)) from exc
        for entry in entries:
            relative = entry.relative_to(release_dir).as_posix()
            if entry.is_symlink():
                raise ServiceError("RELEASE_INVENTORY_LINK_BLOCKED", relative)
            if entry.is_dir():
                pending.append(entry)
            elif entry.is_file():
                inventory.add(relative)
            else:
                raise ServiceError("RELEASE_INVENTORY_SPECIAL_FILE_BLOCKED", relative)
    return inventory


def _verify_release(release_dir: Path) -> dict[str, str]:
    """Verify the release identity and every raw file hash deterministically."""

    manifest = load_json_file(release_dir / "release_manifest.json")
    files_document = load_json_file(release_dir / "files_sha256.json")
    files = files_document.get("files")
    if not isinstance(files, dict) or not files:
        raise ServiceError("RELEASE_FILES_MAP_INVALID", "$.files_sha256.files")
    expected_inventory = set(files) | {"release_manifest.json", "files_sha256.json"}
    if _release_inventory(release_dir) != expected_inventory:
        raise ServiceError("RELEASE_INVENTORY_MISMATCH", "$")
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


def _policy_reference_path(release_root: Path) -> Path:
    """Select the patch-release policy reference with a legacy fallback."""

    installed = release_root / "policy" / "runtime_policy_reference.json"
    if installed.is_file():
        return installed
    return release_root / "runtime_policy_reference.json"


def _vector_file(release_root: Path, vector_path: Path | str | None) -> Path:
    """Select the explicit or packaged fixed vector without directory scanning."""

    if vector_path is not None:
        return Path(vector_path).expanduser()
    installed = release_root / DEFAULT_VECTOR_RELATIVE_PATH
    if installed.is_file():
        return installed
    return release_root / "tests" / "fixtures" / "w7tp_small_agent_deployment_vectors.json"


def run_embedded_healthcheck(
    release_dir: Path | str,
    vector_path: Path | str | None = None,
) -> dict[str, Any]:
    """Run health primitives for the installed CLI without CLI recursion."""

    release_root = Path(release_dir).expanduser()
    try:
        release = _verify_release(release_root)
        policy_reference = load_json_file(_policy_reference_path(release_root))
        if policy_reference.get("policy_sha256") != release["policy_sha256"]:
            raise ServiceError("POLICY_REFERENCE_SHA256_MISMATCH", "$.policy_sha256")
        vector = load_json_file(_vector_file(release_root, vector_path))
        if vector.get("policy_sha256") != release["policy_sha256"]:
            raise ServiceError("VECTOR_POLICY_SHA256_MISMATCH", "$.policy_sha256")
        capability = load_json_file(release_root / "capability_manifest_template.json")
        from tools.adi_index_strategy_candidate import (
            ADIInputContract,
            DisabledADIIndexStrategy,
        )
        from tools.eightd_gte_parser_candidate import EightDGTEParserCandidate
        from tools.total_field_candidate_gateway import llm_push, total_field_pull
        from tools.w7tp_small_agent_service_runner import build_capability_manifest
        from tools.w7tp_small_transport_agent_candidate import apply_allow_only_commit

        build_capability_manifest(
            {
                "agent_ref": capability.get("agent_ref"),
                "version": capability.get("agent_version"),
                "protocol_version": capability.get("protocol_version"),
                "supported_schema_versions": capability.get("supported_schema_versions"),
                "supported_rule_refs": capability.get("supported_rule_refs"),
                "supported_reconstructors": capability.get("supported_reconstructors"),
                "available_asset_refs": capability.get("available_asset_refs"),
                "observation_domain_ref": capability.get("observation_domain_ref"),
                "privacy_boundary_ref": capability.get("privacy_boundary_ref"),
                "execution_permissions": capability.get("execution_permissions"),
            }
        )
        EightDGTEParserCandidate()
        if not callable(total_field_pull) or not callable(llm_push):
            raise ServiceError("TOTAL_FIELD_GATEWAY_NOT_CALLABLE")
        if not callable(apply_allow_only_commit):
            raise ServiceError("ALLOW_ONLY_COMMIT_GUARD_NOT_CALLABLE")
        adi = DisabledADIIndexStrategy().evaluate(ADIInputContract(requested=False))
        if adi.status != "NOT_REQUESTED" or adi.TEST_ONLY:
            raise ServiceError("ADI_PRODUCTION_MODE_NOT_DISABLED")
        checks = {
            "release_files": "PASS",
            "policy_sha256": "PASS",
            "module_imports": "PASS",
            "capability_manifest": "PASS",
            "eightd_gte_parser": "PASS",
            "total_field_gateway": "PASS",
            "allow_only_commit": "PASS",
            "adi_production_mode": "DISABLED",
        }
        return {
            "release_version": release["release_version"],
            "release_sha256": release["release_sha256"],
            "policy_sha256": release["policy_sha256"],
            "status": "PASS",
            "checks": checks,
        }
    except Exception as exc:
        reason_code = getattr(exc, "reason_code", "EMBEDDED_HEALTHCHECK_FAILED")
        return {
            "release_version": None,
            "release_sha256": None,
            "policy_sha256": None,
            "status": "HOLD",
            "reason_code": reason_code,
            "checks": {},
        }


def _installed_binary(release_root: Path) -> Path:
    """Resolve and validate the installed executable health entrypoint."""

    root = release_root.resolve(strict=True)
    binary = (root / "bin" / "w7tp-small-agent").resolve(strict=True)
    if root not in binary.parents or not binary.is_file():
        raise ServiceError("RUNTIME_ENTRYPOINT_INVALID", "bin/w7tp-small-agent")
    if not os.access(binary, os.X_OK):
        raise ServiceError("RUNTIME_ENTRYPOINT_NOT_EXECUTABLE", "bin/w7tp-small-agent")
    return binary


def _subprocess_environment() -> dict[str, str]:
    """Return a minimal deterministic environment without inherited PYTHONPATH."""

    return {
        "HOME": str(Path.home()),
        "LANG": "C.UTF-8",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
    }


def run_healthcheck(
    release_dir: Path | str,
    state_dir: Path | str | None = None,
    vector_path: Path | str | None = None,
) -> dict[str, Any]:
    """Execute the installed binary health command and validate its evidence."""

    del vector_path
    release_root = Path(release_dir).expanduser()
    output_dir = Path(state_dir).expanduser() if state_dir is not None else DEFAULT_STATE_DIR
    try:
        binary = _installed_binary(release_root)
        completed = subprocess.run(
            [str(binary), "health"],
            cwd="/",
            env=_subprocess_environment(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            check=False,
        )
        lines = completed.stdout.splitlines()
        if len(completed.stdout.encode("utf-8")) > 65536:
            raise ServiceError("RUNTIME_HEALTH_OUTPUT_TOO_LARGE")
        if completed.returncode != 0 or len(lines) != 2:
            raise ServiceError("RUNTIME_HEALTH_COMMAND_FAILED")
        if lines[0] != "STATE=PASS_W7TP_SMALL_AGENT_HEALTH":
            raise ServiceError("RUNTIME_HEALTH_STATE_INVALID")
        try:
            evidence = json.loads(
                lines[1],
                object_pairs_hook=_health_strict_pairs,
                parse_constant=_health_reject_constant,
            )
        except (json.JSONDecodeError, ServiceError) as exc:
            raise ServiceError("RUNTIME_HEALTH_EVIDENCE_INVALID") from exc
        if not isinstance(evidence, dict) or evidence.get("status") != "PASS":
            raise ServiceError("RUNTIME_HEALTH_EVIDENCE_INVALID")
        _write_health_state(output_dir, evidence)
        return evidence
    except (OSError, subprocess.SubprocessError, ServiceError) as exc:
        reason_code = getattr(exc, "reason_code", "RUNTIME_HEALTH_COMMAND_FAILED")
        result = {
            "release_version": None,
            "release_sha256": None,
            "policy_sha256": None,
            "status": "HOLD",
            "reason_code": reason_code,
            "checks": {},
        }
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
    "run_embedded_healthcheck",
    "run_healthcheck",
)
