#!/usr/bin/env python3
"""Build and verify the deterministic W7TP small-agent candidate release.

The release is a candidate-deployable, user-level package.  Building it never
changes an Active Canonical, a Pointer, a database, a router, or a service.
Existing release directories are verified and are never overwritten.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any, Mapping, NoReturn


ROOT = Path(__file__).resolve().parents[1]
RELEASE_VERSION = "v0.1-d27230aba7a4"
RELEASE_DIRECTORY_NAME = "w7tp_small_agent_release_v0_1_d27230aba7a4"
PATCH_RELEASE_VERSION = "v0.1.1-d27230aba7a4"
PATCH_RELEASE_DIRECTORY_NAME = "w7tp_small_agent_release_v0_1_1_d27230aba7a4"
SECURITY_PATCH_RELEASE_VERSION = "v0.1.2-d27230aba7a4"
SECURITY_PATCH_RELEASE_DIRECTORY_NAME = (
    "w7tp_small_agent_release_v0_1_2_d27230aba7a4"
)
SECURITY_RUNTIME_PATCH_RELEASE_VERSION = "v0.1.3-d27230aba7a4"
SECURITY_RUNTIME_PATCH_RELEASE_DIRECTORY_NAME = (
    "w7tp_small_agent_release_v0_1_3_d27230aba7a4"
)
POLICY_SHA256 = "d27230aba7a4ecd051f4169184c1fa5357ce5efa1d62019238d68991b0140960"
RELEASE_STATUS = "CANDIDATE_DEPLOYABLE"
SECURITY_CORRECTION = {
    "D6_MERGED_STATE_SCAN": "PASS",
    "RUNTIME_SCHEMA_REQUIRED_FIELDS": "PASS",
    "LOCAL_EQUIVALENCE_STATE_REF": "PASS",
    "ADI_FIXTURE_FORGERY": "BLOCKED",
    "DECISION_PRIORITY": "ALLOW<HOLD<BLOCK<QUARANTINE",
    "D7_NESTED_RAW_PAYLOAD": "PASS",
    "UNSUPPORTED_REF_GATE": "HOLD",
}

ACTIVE_POLICY_PATH = Path(
    "runtime/total_field/active/ACTIVE_TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL.json"
)
ACTIVE_POLICY_POINTER_PATH = Path(
    "runtime/total_field/active/ACTIVE_TFCT_TRUE8D_RUNTIME_POLICY_POINTER.txt"
)

SOURCE_PAYLOAD = (
    Path("tools/w7tp_small_transport_agent_candidate.py"),
    Path("tools/tfct_true8d_runtime_candidate.py"),
    Path("tools/eightd_gte_parser_candidate.py"),
    Path("tools/total_field_candidate_gateway.py"),
    Path("tools/xiaoj_candidate_adapter.py"),
    Path("tools/d3_coordinate_transition_candidate.py"),
    Path("tools/adi_index_strategy_candidate.py"),
    Path("tools/w7tp_small_agent_service_runner.py"),
    Path("tools/w7tp_small_agent_healthcheck.py"),
    Path("tests/fixtures/w7tp_small_agent_deployment_vectors.json"),
)

GENERATED_PAYLOAD = (
    Path("runtime_policy_reference.json"),
    Path("capability_manifest.schema.json"),
    Path("UNINSTALL_ROLLBACK.md"),
)

ROOT_MANIFESTS = (
    Path("release_manifest.json"),
    Path("files_sha256.json"),
    Path("capability_manifest_template.json"),
    Path("install_manifest.json"),
    Path("rollback_manifest.json"),
)

PATCH_LIBRARY_SOURCES = (
    Path("tools/w7tp_small_agent_service_runner.py"),
    Path("tools/w7tp_small_agent_healthcheck.py"),
    Path("tools/w7tp_small_transport_agent_candidate.py"),
    Path("tools/tfct_true8d_runtime_candidate.py"),
    Path("tools/eightd_gte_parser_candidate.py"),
    Path("tools/total_field_candidate_gateway.py"),
    Path("tools/xiaoj_candidate_adapter.py"),
    Path("tools/d3_coordinate_transition_candidate.py"),
    Path("tools/adi_index_strategy_candidate.py"),
)
PATCH_POLICY_SOURCE = Path(
    "runtime/total_field/candidate/tfct_true8d_runtime_policy_v0_1.json"
)
PATCH_D3_RULE_SOURCE = Path(
    "runtime/total_field/candidate/d3_coordinate_transition_rules_v0_3.json"
)
PATCH_D3_RULE_DESTINATION = Path("lib") / PATCH_D3_RULE_SOURCE
PATCH_SCHEMA_SOURCES = (
    Path("schemas/field/8d_governance_tensor_expression_candidate.schema.json"),
    Path("schemas/field/8d_gte_runtime_candidate_profile_v0_1.schema.json"),
)
PATCH_FIXTURE_SOURCE = Path(
    "tests/fixtures/w7tp_small_agent_deployment_vectors.json"
)
PATCH_ENTRYPOINT_SOURCE = Path("tools/w7tp_small_agent_cli.py")
PATCH_ENTRYPOINT = Path("bin/w7tp-small-agent")
PATCH_POLICY_PATHS = (
    Path("policy/tfct_true8d_runtime_policy_v0_1.json"),
    Path("lib/runtime/total_field/candidate/tfct_true8d_runtime_policy_v0_1.json"),
)
PATCH_SERVICE_PATH = Path("service/w7tp-small-agent.service")
PATCH_ROOT_MANIFESTS = frozenset(
    {
        "release_manifest.json",
        "files_sha256.json",
        "capability_manifest_template.json",
        "install_manifest.json",
        "rollback_manifest.json",
    }
)


class ReleaseBuildError(ValueError):
    """Report one stable release build or verification failure."""

    def __init__(self, reason_code: str, path: str = "") -> None:
        """Store a stable reason code and a non-sensitive relative path."""

        self.reason_code = reason_code
        self.path = path
        message = reason_code if not path else f"{reason_code}:{path}"
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class ReleaseBuildResult:
    """Return the deterministic release identity and verified payload map."""

    status: str
    release_sha256: str
    files: Mapping[str, str]


def canonical_json(value: Any) -> str:
    """Serialize JSON data with the repository deterministic JSON contract."""

    try:
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError, RecursionError) as error:
        raise ReleaseBuildError("ERR_NON_CANONICAL_JSON") from error


def canonical_sha256(value: Any) -> str:
    """Hash one canonical JSON value with SHA-256."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _reject_constant(token: str) -> NoReturn:
    """Reject a non-finite JSON number with a stable error."""

    raise ReleaseBuildError("ERR_NON_FINITE_JSON", token)


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Create a JSON object while rejecting duplicate member names."""

    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ReleaseBuildError("ERR_DUPLICATE_JSON_MEMBER", key)
        value[key] = item
    return value


def _read_json(path: Path, display_path: str) -> Any:
    """Read strict UTF-8 JSON from one exact path."""

    try:
        source = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise ReleaseBuildError("ERR_REQUIRED_FILE_MISSING", display_path) from error
    except (OSError, UnicodeError) as error:
        raise ReleaseBuildError("ERR_REQUIRED_FILE_UNREADABLE", display_path) from error
    try:
        return json.loads(
            source,
            object_pairs_hook=_strict_pairs,
            parse_constant=_reject_constant,
        )
    except ReleaseBuildError:
        raise
    except json.JSONDecodeError as error:
        raise ReleaseBuildError("ERR_INVALID_JSON", display_path) from error


def _json_bytes(value: Any) -> bytes:
    """Encode deterministic human-readable JSON with one final newline."""

    try:
        rendered = json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )
    except (TypeError, ValueError, RecursionError) as error:
        raise ReleaseBuildError("ERR_NON_CANONICAL_JSON") from error
    return f"{rendered}\n".encode("utf-8")


def _raw_sha256(content: bytes) -> str:
    """Return the lowercase SHA-256 digest of exact release bytes."""

    return hashlib.sha256(content).hexdigest()


def _is_within(path: Path, parent: Path) -> bool:
    """Report whether a resolved path is contained by a resolved parent."""

    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _resolve_output(root: Path, output_dir: Path | str | None) -> Path:
    """Resolve an output directory and block protected repository locations."""

    resolved_root = root.resolve()
    if output_dir is None:
        output = resolved_root / "manifests" / RELEASE_DIRECTORY_NAME
    else:
        raw_output = Path(output_dir).expanduser()
        output = raw_output if raw_output.is_absolute() else resolved_root / raw_output
        output = output.resolve()
    protected = (
        resolved_root / "runtime" / "total_field" / "active",
        resolved_root / "runtime" / "total_field",
        resolved_root / "tools",
        resolved_root / "tests",
    )
    if _is_within(output, resolved_root):
        manifests_root = resolved_root / "manifests"
        if not _is_within(output, manifests_root):
            raise ReleaseBuildError("HOLD_PROTECTED_RELEASE_TARGET", str(output))
        if output == manifests_root:
            raise ReleaseBuildError("HOLD_PROTECTED_RELEASE_TARGET", str(output))
    if any(output == item for item in protected):
        raise ReleaseBuildError("HOLD_PROTECTED_RELEASE_TARGET", str(output))
    upper_name = output.name.upper()
    if "ACTIVE" in upper_name or "POINTER" in upper_name or "CANONICAL" in upper_name:
        raise ReleaseBuildError("HOLD_PROTECTED_RELEASE_TARGET", str(output))
    return output


def _resolve_patch_output(root: Path, output_dir: Path | str | None) -> Path:
    """Resolve only the new patch-release target without changing old defaults."""

    if output_dir is None:
        output_dir = Path("manifests") / PATCH_RELEASE_DIRECTORY_NAME
    return _resolve_output(root, output_dir)


def _resolve_security_patch_output(
    root: Path, output_dir: Path | str | None
) -> Path:
    """Resolve the separate immutable security-patch output directory."""

    if output_dir is None:
        output_dir = Path("manifests") / SECURITY_PATCH_RELEASE_DIRECTORY_NAME
    return _resolve_output(root, output_dir)


def _resolve_security_runtime_patch_output(
    root: Path, output_dir: Path | str | None
) -> Path:
    """Resolve the dependency-complete security-patch output directory."""

    if output_dir is None:
        output_dir = (
            Path("manifests") / SECURITY_RUNTIME_PATCH_RELEASE_DIRECTORY_NAME
        )
    return _resolve_output(root, output_dir)


def _policy_reference(root: Path) -> dict[str, Any]:
    """Validate and describe the Active policy through read-only references."""

    active_path = root / ACTIVE_POLICY_PATH
    pointer_path = root / ACTIVE_POLICY_POINTER_PATH
    active = _read_json(active_path, ACTIVE_POLICY_PATH.as_posix())
    if not isinstance(active, dict) or not isinstance(active.get("policy"), dict):
        raise ReleaseBuildError("ERR_ACTIVE_POLICY_SHAPE", ACTIVE_POLICY_PATH.as_posix())
    if canonical_sha256(active["policy"]) != POLICY_SHA256:
        raise ReleaseBuildError("ERR_ACTIVE_POLICY_HASH", ACTIVE_POLICY_PATH.as_posix())
    if active.get("source_policy_sha256") != POLICY_SHA256:
        raise ReleaseBuildError("ERR_ACTIVE_POLICY_SOURCE_HASH", ACTIVE_POLICY_PATH.as_posix())
    try:
        pointer_text = pointer_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as error:
        raise ReleaseBuildError(
            "ERR_REQUIRED_FILE_MISSING", ACTIVE_POLICY_POINTER_PATH.as_posix()
        ) from error
    except (OSError, UnicodeError) as error:
        raise ReleaseBuildError(
            "ERR_REQUIRED_FILE_UNREADABLE", ACTIVE_POLICY_POINTER_PATH.as_posix()
        ) from error
    if not pointer_text or "\n" in pointer_text or "\r" in pointer_text:
        raise ReleaseBuildError(
            "ERR_ACTIVE_POINTER_SHAPE", ACTIVE_POLICY_POINTER_PATH.as_posix()
        )
    pointer_target = Path(pointer_text)
    if not pointer_target.is_absolute():
        pointer_target = root / pointer_target
    try:
        resolved_target = pointer_target.resolve(strict=True)
    except (FileNotFoundError, OSError) as error:
        raise ReleaseBuildError(
            "ERR_ACTIVE_POINTER_TARGET", ACTIVE_POLICY_POINTER_PATH.as_posix()
        ) from error
    allowed_runtime_root = (root / "runtime" / "total_field").resolve()
    if not _is_within(resolved_target, allowed_runtime_root):
        raise ReleaseBuildError(
            "ERR_ACTIVE_POINTER_TARGET", ACTIVE_POLICY_POINTER_PATH.as_posix()
        )
    pointed = _read_json(resolved_target, ACTIVE_POLICY_POINTER_PATH.as_posix())
    if pointed != active:
        raise ReleaseBuildError(
            "ERR_ACTIVE_POINTER_MISMATCH", ACTIVE_POLICY_POINTER_PATH.as_posix()
        )
    return {
        "schema_version": "w7tp.small-agent.runtime-policy-reference/v0.1",
        "status": RELEASE_STATUS,
        "reference_mode": "READ_ONLY",
        "active_canonical_ref": ACTIVE_POLICY_PATH.as_posix(),
        "active_pointer_ref": ACTIVE_POLICY_POINTER_PATH.as_posix(),
        "policy_member": "policy",
        "policy_sha256": POLICY_SHA256,
        "canonical_scope": "TFCT_TRUE8D_RUNTIME_POLICY",
        "canonical_write": False,
        "pointer_write": False,
    }


def _capability_schema() -> dict[str, Any]:
    """Return the closed Draft 2020-12 capability manifest schema."""

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:w7tp:small-agent:capability-manifest:v0.1",
        "title": "W7TP Small Agent Candidate Capability Manifest",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema_version",
            "status",
            "agent_ref",
            "agent_version",
            "protocol_version",
            "policy_sha256",
            "supported_schema_versions",
            "supported_rule_refs",
            "supported_reconstructors",
            "available_asset_refs",
            "observation_domain_ref",
            "privacy_boundary_ref",
            "execution_permissions",
            "direct_commit",
        ],
        "properties": {
            "schema_version": {
                "const": "w7tp.small-agent.capability-manifest/v0.1"
            },
            "status": {"const": RELEASE_STATUS},
            "agent_ref": {"type": "string", "minLength": 1},
            "agent_version": {"const": RELEASE_VERSION},
            "protocol_version": {"type": "string", "minLength": 1},
            "policy_sha256": {
                "const": POLICY_SHA256,
                "pattern": "^[0-9a-f]{64}$",
            },
            "supported_schema_versions": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
                "uniqueItems": True,
            },
            "supported_rule_refs": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
                "uniqueItems": True,
            },
            "supported_reconstructors": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
                "uniqueItems": True,
            },
            "available_asset_refs": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
                "uniqueItems": True,
            },
            "observation_domain_ref": {"type": "string", "minLength": 1},
            "privacy_boundary_ref": {"type": "string", "minLength": 1},
            "execution_permissions": {
                "type": "array",
                "items": {
                    "enum": [
                        "RESOLVE_REFERENCE",
                        "BUILD_RECONSTRUCTION_REQUEST",
                        "REQUEST_EQUIVALENCE_VERIFICATION",
                        "SUBMIT_CANDIDATE",
                    ]
                },
                "uniqueItems": True,
            },
            "direct_commit": {"const": False},
        },
    }


def _capability_template() -> dict[str, Any]:
    """Return a reference-only candidate capability manifest template."""

    return {
        "schema_version": "w7tp.small-agent.capability-manifest/v0.1",
        "status": RELEASE_STATUS,
        "agent_ref": "agent/w7tp-small-generative-transport/v0_1",
        "agent_version": RELEASE_VERSION,
        "protocol_version": "w7tp/state-field-packet/v0.1",
        "policy_sha256": POLICY_SHA256,
        "supported_schema_versions": [
            "tfct.true8d.runtime-candidate/0.1",
            "8d-gte-runtime-profile-candidate/0.1",
        ],
        "supported_rule_refs": [
            "rules/tfct/identity_v0_1",
            "rules/tfct/normalize_v0_1",
        ],
        "supported_reconstructors": [
            "reconstructor/w7tp/reference-only/v0_1"
        ],
        "available_asset_refs": [],
        "observation_domain_ref": "observation-domain/configured-at-install/v0_1",
        "privacy_boundary_ref": "privacy/sovereign-node/v0_1",
        "execution_permissions": [
            "RESOLVE_REFERENCE",
            "BUILD_RECONSTRUCTION_REQUEST",
            "REQUEST_EQUIVALENCE_VERIFICATION",
            "SUBMIT_CANDIDATE",
        ],
        "direct_commit": False,
    }


def _install_manifest() -> dict[str, Any]:
    """Return a non-privileged deterministic Linux user-install contract."""

    return {
        "schema_version": "w7tp.small-agent.install-manifest/v0.1",
        "release_version": RELEASE_VERSION,
        "status": RELEASE_STATUS,
        "platform_profile": "LINUX_USER_LEVEL",
        "release_root": "~/.local/share/w7tp-small-agent/releases",
        "release_directory": f"~/.local/share/w7tp-small-agent/releases/{RELEASE_VERSION}",
        "current_path": "~/.local/share/w7tp-small-agent/current",
        "config_directory": "~/.config/w7tp-small-agent",
        "state_directory": "~/.local/state/w7tp-small-agent",
        "current_switch": "ATOMIC_SYMLINK_REPLACE",
        "service_mode": "USER_SYSTEMD_IF_AVAILABLE",
        "service_name": "w7tp-small-agent",
        "restart_policy": "ONLY_IF_RELEASE_CONTENT_CHANGED",
        "existing_equal_policy": "SKIP_ALREADY_PASS",
        "unknown_existing_policy": "HOLD_INSTALL_CONFLICT",
        "requires_root": False,
        "firewall_write": False,
        "router_write": False,
        "database_write": False,
        "external_port_open": False,
        "secret_storage": "NOT_IN_RELEASE_OR_CONFIG",
    }


def _rollback_manifest() -> dict[str, Any]:
    """Return the deterministic no-delete rollback contract."""

    return {
        "schema_version": "w7tp.small-agent.rollback-manifest/v0.1",
        "release_version": RELEASE_VERSION,
        "status": RELEASE_STATUS,
        "current_path": "~/.local/share/w7tp-small-agent/current",
        "previous_target_source": "INSTALL_TIME_LOCAL_STATE",
        "rollback_action": "ATOMIC_RESTORE_PREVIOUS_CURRENT_TARGET",
        "healthcheck_after_rollback": True,
        "delete_previous_release": False,
        "delete_failed_release": False,
        "requires_root": False,
        "service_restart": "ONLY_IF_CURRENT_TARGET_CHANGED",
        "router_write": False,
        "database_write": False,
    }


def _rollback_document() -> bytes:
    """Return deterministic user-level uninstall and rollback instructions."""

    return (
        "# W7TP Small Agent Candidate Uninstall and Rollback\n\n"
        "This package is `CANDIDATE_DEPLOYABLE`; it is not a claim of completed "
        "production deployment.\n\n"
        "Rollback restores the previously recorded user-level `current` target "
        "with an atomic link switch, then runs the packaged healthcheck. The "
        "previous release is retained.\n\n"
        "Uninstall disables only the user-level `w7tp-small-agent` service and "
        "removes its `current` link after operator confirmation. Versioned "
        "release directories, configuration, and state are retained unless a "
        "separate authorized cleanup is performed.\n\n"
        "No step requires root access or changes a firewall, router, database, "
        "Active Canonical, or Pointer. Secrets must not be stored in this "
        "release or its configuration.\n"
    ).encode("utf-8")


def _patch_capability_schema(
    release_version: str = PATCH_RELEASE_VERSION,
    schema_version: str = "v0.1.1",
) -> dict[str, Any]:
    """Return the capability schema with only the patch agent version updated."""

    schema = json.loads(canonical_json(_capability_schema()))
    schema["$id"] = f"urn:w7tp:small-agent:capability-manifest:{schema_version}"
    schema["title"] = "W7TP Small Agent Patch Capability Manifest"
    schema["properties"]["agent_version"]["const"] = release_version
    return schema


def _patch_capability_template(
    release_version: str = PATCH_RELEASE_VERSION,
) -> dict[str, Any]:
    """Return the patch capability template without widening permissions."""

    template = json.loads(canonical_json(_capability_template()))
    template["agent_version"] = release_version
    return template


def _patch_install_manifest(
    release_version: str = PATCH_RELEASE_VERSION,
) -> dict[str, Any]:
    """Return the patch user-level install contract with its executable entrypoint."""

    manifest = json.loads(canonical_json(_install_manifest()))
    manifest["release_version"] = release_version
    manifest["release_directory"] = (
        "~/.local/share/w7tp-small-agent/releases/" + release_version
    )
    manifest["entrypoint"] = PATCH_ENTRYPOINT.as_posix()
    manifest["service_template"] = PATCH_SERVICE_PATH.as_posix()
    manifest["service_exec_start"] = (
        "%h/.local/share/w7tp-small-agent/current/bin/w7tp-small-agent service-run"
    )
    return manifest


def _patch_rollback_manifest(
    release_version: str = PATCH_RELEASE_VERSION,
) -> dict[str, Any]:
    """Return the no-delete rollback contract for the patch version."""

    manifest = json.loads(canonical_json(_rollback_manifest()))
    manifest["release_version"] = release_version
    return manifest


def _patch_service_template() -> bytes:
    """Return the exact non-root user-systemd service template."""

    return (
        "[Unit]\n"
        "Description=W7TP Small Agent\n"
        "After=default.target\n\n"
        "[Service]\n"
        "Type=simple\n"
        "ExecStart=%h/.local/share/w7tp-small-agent/current/bin/"
        "w7tp-small-agent service-run\n"
        "Restart=on-failure\n"
        "NoNewPrivileges=true\n\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    ).encode("utf-8")


def _read_patch_source(root: Path, relative: Path) -> bytes:
    """Read one fixed patch input as UTF-8 and validate JSON inputs strictly."""

    source = root / relative
    try:
        content = source.read_bytes()
    except FileNotFoundError as error:
        raise ReleaseBuildError(
            "ERR_REQUIRED_FILE_MISSING", relative.as_posix()
        ) from error
    except OSError as error:
        raise ReleaseBuildError(
            "ERR_REQUIRED_FILE_UNREADABLE", relative.as_posix()
        ) from error
    try:
        content.decode("utf-8")
    except UnicodeError as error:
        raise ReleaseBuildError(
            "ERR_REQUIRED_FILE_NOT_UTF8", relative.as_posix()
        ) from error
    if relative.suffix == ".json":
        _read_json(source, relative.as_posix())
    return content


def _validate_patch_payload(root: Path, payload: Mapping[str, bytes]) -> None:
    """Reject build paths, credential-shaped bytes, and malformed JSON payloads."""

    forbidden_paths = (
        str(root.resolve()).encode("utf-8"),
        b"/tmp/",
        b"/var/tmp/",
    )
    credential_markers = (
        b"-----BEGIN PRIVATE KEY-----\n",
        b"-----BEGIN OPENSSH PRIVATE KEY-----\n",
        b"AKIAIOSFODNN7EXAMPLE",
        b"ghp_",
        b"sk-proj-",
    )
    for relative, content in sorted(payload.items()):
        if any(marker and marker in content for marker in forbidden_paths):
            raise ReleaseBuildError("HOLD_ABSOLUTE_BUILD_PATH", relative)
        if any(marker in content for marker in credential_markers):
            raise ReleaseBuildError("HOLD_RAW_SECRET_IN_RELEASE", relative)
        if relative.endswith(".json"):
            try:
                json.loads(
                    content.decode("utf-8"),
                    object_pairs_hook=_strict_pairs,
                    parse_constant=_reject_constant,
                )
            except ReleaseBuildError:
                raise
            except (UnicodeError, json.JSONDecodeError) as error:
                raise ReleaseBuildError("ERR_INVALID_JSON", relative) from error


def _patch_source_payload(
    root: Path,
    release_version: str = PATCH_RELEASE_VERSION,
    schema_version: str = "v0.1.1",
    *,
    include_d3_rule_registry: bool = False,
) -> dict[str, bytes]:
    """Map the exact executable patch runtime into its relocatable layout."""

    payload: dict[str, bytes] = {
        PATCH_ENTRYPOINT.as_posix(): _read_patch_source(
            root, PATCH_ENTRYPOINT_SOURCE
        )
    }
    for source in PATCH_LIBRARY_SOURCES:
        destination = Path("lib/tools") / source.name
        payload[destination.as_posix()] = _read_patch_source(root, source)
    if include_d3_rule_registry:
        payload[PATCH_D3_RULE_DESTINATION.as_posix()] = _read_patch_source(
            root, PATCH_D3_RULE_SOURCE
        )
    policy = _read_patch_source(root, PATCH_POLICY_SOURCE)
    for destination in PATCH_POLICY_PATHS:
        payload[destination.as_posix()] = policy
    for source in PATCH_SCHEMA_SOURCES:
        content = _read_patch_source(root, source)
        payload[(Path("schemas/field") / source.name).as_posix()] = content
        payload[(Path("lib/schemas/field") / source.name).as_posix()] = content
    payload[(Path("fixtures") / PATCH_FIXTURE_SOURCE.name).as_posix()] = (
        _read_patch_source(root, PATCH_FIXTURE_SOURCE)
    )
    policy_reference = _policy_reference(root)
    policy_reference["schema_version"] = (
        f"w7tp.small-agent.runtime-policy-reference/{schema_version}"
    )
    policy_reference["packaged_policy_ref"] = PATCH_POLICY_PATHS[0].as_posix()
    policy_reference["packaged_policy_sha256"] = POLICY_SHA256
    payload["policy/runtime_policy_reference.json"] = _json_bytes(
        policy_reference
    )
    payload["schemas/capability_manifest.schema.json"] = _json_bytes(
        _patch_capability_schema(release_version, schema_version)
    )
    payload[PATCH_SERVICE_PATH.as_posix()] = _patch_service_template()
    _validate_patch_payload(root, payload)
    return payload


def _read_source_payload(root: Path) -> dict[str, bytes]:
    """Read the fixed source payload without rewriting its bytes."""

    payload: dict[str, bytes] = {}
    for relative in SOURCE_PAYLOAD:
        source = root / relative
        try:
            content = source.read_bytes()
        except FileNotFoundError as error:
            raise ReleaseBuildError(
                "ERR_REQUIRED_FILE_MISSING", relative.as_posix()
            ) from error
        except OSError as error:
            raise ReleaseBuildError(
                "ERR_REQUIRED_FILE_UNREADABLE", relative.as_posix()
            ) from error
        try:
            content.decode("utf-8")
        except UnicodeError as error:
            raise ReleaseBuildError(
                "ERR_REQUIRED_FILE_NOT_UTF8", relative.as_posix()
            ) from error
        if relative.suffix == ".json":
            _read_json(source, relative.as_posix())
        payload[relative.as_posix()] = content
    return payload


def _expected_release(root: Path) -> tuple[dict[str, bytes], str, dict[str, str]]:
    """Compose every expected release file and its canonical identity."""

    resolved_root = root.resolve()
    payload = _read_source_payload(resolved_root)
    policy_reference = _policy_reference(resolved_root)
    capability_schema = _capability_schema()
    capability_template = _capability_template()
    install_manifest = _install_manifest()
    rollback_manifest = _rollback_manifest()
    payload["runtime_policy_reference.json"] = _json_bytes(policy_reference)
    payload["capability_manifest.schema.json"] = _json_bytes(capability_schema)
    payload["UNINSTALL_ROLLBACK.md"] = _rollback_document()
    files = {
        relative: _raw_sha256(content)
        for relative, content in sorted(payload.items())
    }
    files_document = {
        "schema_version": "w7tp.small-agent.files-sha256/v0.1",
        "release_version": RELEASE_VERSION,
        "files": files,
    }
    release_identity = {
        "schema_version": "w7tp.small-agent.release-identity/v0.1",
        "release_version": RELEASE_VERSION,
        "status": RELEASE_STATUS,
        "policy_sha256": POLICY_SHA256,
        "files_sha256": files,
        "capability_manifest_template_sha256": canonical_sha256(
            capability_template
        ),
        "install_manifest_sha256": canonical_sha256(install_manifest),
        "rollback_manifest_sha256": canonical_sha256(rollback_manifest),
        "runtime_policy_reference_sha256": files[
            "runtime_policy_reference.json"
        ],
    }
    release_sha256 = canonical_sha256(release_identity)
    release_manifest = {
        "schema_version": "w7tp.small-agent.release-manifest/v0.1",
        "release_version": RELEASE_VERSION,
        "status": RELEASE_STATUS,
        "release_sha256": release_sha256,
        "release_identity": release_identity,
        "files_sha256_ref": "files_sha256.json",
        "files_sha256_hash": canonical_sha256(files_document),
        "capability_manifest_schema_ref": "capability_manifest.schema.json",
        "capability_manifest_template_ref": "capability_manifest_template.json",
        "install_manifest_ref": "install_manifest.json",
        "rollback_manifest_ref": "rollback_manifest.json",
        "runtime_policy_reference_ref": "runtime_policy_reference.json",
        "runner_ref": "tools/w7tp_small_agent_service_runner.py",
        "healthcheck_ref": "tools/w7tp_small_agent_healthcheck.py",
        "fixed_vectors_ref": (
            "tests/fixtures/w7tp_small_agent_deployment_vectors.json"
        ),
        "generative_transport_semantics": [
            "STATE_FIELD_PACKET",
            "REFERENCE",
            "LOOKUP",
            "RECONSTRUCTION_CONDITION",
            "EQUIVALENT_STATE_GENERATION",
            "TOTAL_FIELD_VERIFICATION",
        ],
        "direct_tfs_commit": False,
        "allow_only_commit": True,
        "canonical_promotion": False,
        "production_deployment_complete": False,
    }
    complete = dict(payload)
    complete["release_manifest.json"] = _json_bytes(release_manifest)
    complete["files_sha256.json"] = _json_bytes(files_document)
    complete["capability_manifest_template.json"] = _json_bytes(
        capability_template
    )
    complete["install_manifest.json"] = _json_bytes(install_manifest)
    complete["rollback_manifest.json"] = _json_bytes(rollback_manifest)
    expected_names = {
        item.as_posix() for item in SOURCE_PAYLOAD + GENERATED_PAYLOAD + ROOT_MANIFESTS
    }
    if set(complete) != expected_names:
        raise ReleaseBuildError("ERR_RELEASE_INVENTORY_INTERNAL")
    return complete, release_sha256, files


def _expected_patch_release(
    root: Path,
    *,
    release_version: str = PATCH_RELEASE_VERSION,
    schema_version: str = "v0.1.1",
    security_correction: Mapping[str, str] | None = None,
    include_d3_rule_registry: bool = False,
) -> tuple[dict[str, bytes], str, dict[str, str]]:
    """Compose one complete deterministic executable patch release."""

    payload = _patch_source_payload(
        root.resolve(),
        release_version,
        schema_version,
        include_d3_rule_registry=include_d3_rule_registry,
    )
    capability_template = _patch_capability_template(release_version)
    install_manifest = _patch_install_manifest(release_version)
    rollback_manifest = _patch_rollback_manifest(release_version)
    tracked = dict(payload)
    tracked["capability_manifest_template.json"] = _json_bytes(
        capability_template
    )
    tracked["install_manifest.json"] = _json_bytes(install_manifest)
    tracked["rollback_manifest.json"] = _json_bytes(rollback_manifest)
    files = {
        relative: _raw_sha256(content)
        for relative, content in sorted(tracked.items())
    }
    files_document = {
        "schema_version": f"w7tp.small-agent.files-sha256/{schema_version}",
        "release_version": release_version,
        "files": files,
    }
    files_document_bytes = _json_bytes(files_document)
    release_identity = {
        "schema_version": f"w7tp.small-agent.release-identity/{schema_version}",
        "release_version": release_version,
        "status": RELEASE_STATUS,
        "policy_sha256": POLICY_SHA256,
        "files_sha256": files,
        "files_sha256_hash": canonical_sha256(files_document),
        "entrypoint_sha256": files[PATCH_ENTRYPOINT.as_posix()],
        "capability_manifest_template_sha256": files[
            "capability_manifest_template.json"
        ],
        "install_manifest_sha256": files["install_manifest.json"],
        "rollback_manifest_sha256": files["rollback_manifest.json"],
        "packaged_policy_sha256": files[PATCH_POLICY_PATHS[0].as_posix()],
        "service_template_sha256": files[PATCH_SERVICE_PATH.as_posix()],
    }
    if security_correction is not None:
        release_identity["security_correction"] = dict(security_correction)
    release_sha256 = canonical_sha256(release_identity)
    release_manifest = {
        "schema_version": f"w7tp.small-agent.release-manifest/{schema_version}",
        "release_version": release_version,
        "status": RELEASE_STATUS,
        "release_sha256": release_sha256,
        "release_identity": release_identity,
        "files_sha256_ref": "files_sha256.json",
        "files_sha256_hash": canonical_sha256(files_document),
        "capability_manifest_schema_ref": (
            "schemas/capability_manifest.schema.json"
        ),
        "capability_manifest_template_ref": "capability_manifest_template.json",
        "install_manifest_ref": "install_manifest.json",
        "rollback_manifest_ref": "rollback_manifest.json",
        "entrypoint_ref": PATCH_ENTRYPOINT.as_posix(),
        "library_root_ref": "lib",
        "runtime_policy_reference_ref": "policy/runtime_policy_reference.json",
        "packaged_policy_ref": PATCH_POLICY_PATHS[0].as_posix(),
        "runner_ref": "lib/tools/w7tp_small_agent_service_runner.py",
        "healthcheck_ref": "lib/tools/w7tp_small_agent_healthcheck.py",
        "fixed_vectors_ref": (
            "fixtures/w7tp_small_agent_deployment_vectors.json"
        ),
        "service_template_ref": PATCH_SERVICE_PATH.as_posix(),
        "generative_transport_semantics": [
            "STATE_FIELD_PACKET",
            "REFERENCE",
            "LOOKUP",
            "RECONSTRUCTION_CONDITION",
            "EQUIVALENT_STATE_GENERATION",
            "TOTAL_FIELD_VERIFICATION",
        ],
        "direct_tfs_commit": False,
        "allow_only_commit": True,
        "canonical_promotion": False,
        "production_deployment_complete": False,
    }
    if security_correction is not None:
        release_manifest["security_correction"] = dict(security_correction)
    complete = dict(tracked)
    complete["files_sha256.json"] = files_document_bytes
    complete["release_manifest.json"] = _json_bytes(release_manifest)
    root_files = {name for name in complete if "/" not in name}
    if root_files != PATCH_ROOT_MANIFESTS:
        raise ReleaseBuildError("ERR_RELEASE_INVENTORY_INTERNAL")
    required_directories = {"bin", "lib", "policy", "schemas", "fixtures", "service"}
    if {name.split("/", 1)[0] for name in complete if "/" in name} != required_directories:
        raise ReleaseBuildError("ERR_RELEASE_INVENTORY_INTERNAL")
    _validate_patch_payload(root, complete)
    return complete, release_sha256, files


def _release_inventory(release_dir: Path) -> set[str]:
    """List regular release files while rejecting links and special entries."""

    inventory: set[str] = set()
    pending = [release_dir]
    while pending:
        directory = pending.pop()
        try:
            entries = sorted(directory.iterdir(), key=lambda item: item.name)
        except OSError as error:
            raise ReleaseBuildError("HOLD_RELEASE_CONFLICT", str(directory)) from error
        for entry in entries:
            relative = entry.relative_to(release_dir).as_posix()
            if entry.is_symlink():
                raise ReleaseBuildError("HOLD_RELEASE_CONFLICT", relative)
            if entry.is_dir():
                pending.append(entry)
            elif entry.is_file():
                inventory.add(relative)
            else:
                raise ReleaseBuildError("HOLD_RELEASE_CONFLICT", relative)
    return inventory


def _verify_expected(
    release_dir: Path,
    expected: Mapping[str, bytes],
    release_sha256: str,
    files: Mapping[str, str],
    *,
    status: str,
) -> ReleaseBuildResult:
    """Verify an existing release byte-for-byte without changing it."""

    if not release_dir.exists() or not release_dir.is_dir() or release_dir.is_symlink():
        raise ReleaseBuildError("ERR_RELEASE_NOT_FOUND", str(release_dir))
    actual_inventory = _release_inventory(release_dir)
    if actual_inventory != set(expected):
        raise ReleaseBuildError("HOLD_RELEASE_CONFLICT", str(release_dir))
    for relative, expected_content in sorted(expected.items()):
        path = release_dir / relative
        try:
            actual_content = path.read_bytes()
        except OSError as error:
            raise ReleaseBuildError("HOLD_RELEASE_CONFLICT", relative) from error
        if actual_content != expected_content:
            raise ReleaseBuildError("HOLD_RELEASE_CONFLICT", relative)
    return ReleaseBuildResult(
        status=status,
        release_sha256=release_sha256,
        files=dict(files),
    )


def verify_release(
    root: Path | str = ROOT,
    release_dir: Path | str | None = None,
) -> ReleaseBuildResult:
    """Verify the selected release against current fixed source inputs."""

    resolved_root = Path(root).expanduser().resolve()
    target = _resolve_output(resolved_root, release_dir)
    expected, release_sha256, files = _expected_release(resolved_root)
    return _verify_expected(
        target,
        expected,
        release_sha256,
        files,
        status="VERIFIED",
    )


def _write_staging(staging: Path, expected: Mapping[str, bytes]) -> None:
    """Write a complete private staging directory using exclusive files."""

    try:
        staging.mkdir(mode=0o700)
    except FileExistsError as error:
        raise ReleaseBuildError("HOLD_RELEASE_BUILD_IN_PROGRESS", str(staging)) from error
    except OSError as error:
        raise ReleaseBuildError("ERR_RELEASE_CREATE_FAILED", str(staging)) from error
    try:
        for relative, content in sorted(expected.items()):
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
    except (OSError, ReleaseBuildError) as error:
        shutil.rmtree(staging, ignore_errors=True)
        if isinstance(error, ReleaseBuildError):
            raise
        raise ReleaseBuildError("ERR_RELEASE_CREATE_FAILED", str(staging)) from error


def build_release(
    root: Path | str = ROOT,
    output_dir: Path | str | None = None,
) -> ReleaseBuildResult:
    """Build once atomically, or verify an identical existing release."""

    resolved_root = Path(root).expanduser().resolve()
    target = _resolve_output(resolved_root, output_dir)
    expected, release_sha256, files = _expected_release(resolved_root)
    if target.exists():
        return _verify_expected(
            target,
            expected,
            release_sha256,
            files,
            status="ALREADY_BUILT",
        )
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise ReleaseBuildError("ERR_RELEASE_CREATE_FAILED", str(target.parent)) from error
    staging = target.parent / f".{target.name}.building"
    _write_staging(staging, expected)
    if target.exists():
        shutil.rmtree(staging, ignore_errors=True)
        return _verify_expected(
            target,
            expected,
            release_sha256,
            files,
            status="ALREADY_BUILT",
        )
    try:
        os.rename(staging, target)
    except OSError as error:
        shutil.rmtree(staging, ignore_errors=True)
        if target.exists():
            return _verify_expected(
                target,
                expected,
                release_sha256,
                files,
                status="ALREADY_BUILT",
            )
        raise ReleaseBuildError("ERR_RELEASE_CREATE_FAILED", str(target)) from error
    return _verify_expected(
        target,
        expected,
        release_sha256,
        files,
        status="BUILT",
    )


def _verify_patch_expected(
    release_dir: Path,
    expected: Mapping[str, bytes],
    release_sha256: str,
    files: Mapping[str, str],
    *,
    status: str,
) -> ReleaseBuildResult:
    """Verify patch bytes, manifests, entrypoint mode, and read-only policy."""

    result = _verify_expected(
        release_dir,
        expected,
        release_sha256,
        files,
        status=status,
    )
    entrypoint = release_dir / PATCH_ENTRYPOINT
    try:
        mode = entrypoint.stat().st_mode
    except OSError as error:
        raise ReleaseBuildError(
            "HOLD_RELEASE_ENTRYPOINT_MODE", PATCH_ENTRYPOINT.as_posix()
        ) from error
    if not entrypoint.is_file() or entrypoint.is_symlink() or mode & 0o111 == 0:
        raise ReleaseBuildError(
            "HOLD_RELEASE_ENTRYPOINT_MODE", PATCH_ENTRYPOINT.as_posix()
        )
    if not expected[PATCH_ENTRYPOINT.as_posix()].startswith(
        b"#!/usr/bin/env python3\n"
    ):
        raise ReleaseBuildError(
            "HOLD_RELEASE_ENTRYPOINT_SHEBANG", PATCH_ENTRYPOINT.as_posix()
        )
    for relative in PATCH_POLICY_PATHS:
        try:
            policy_mode = (release_dir / relative).stat().st_mode
        except OSError as error:
            raise ReleaseBuildError(
                "HOLD_RELEASE_POLICY_MODE", relative.as_posix()
            ) from error
        if policy_mode & 0o222:
            raise ReleaseBuildError(
                "HOLD_RELEASE_POLICY_MODE", relative.as_posix()
            )
    for name in sorted(PATCH_ROOT_MANIFESTS):
        _read_json(release_dir / name, name)
    return result


def verify_patch_release(
    root: Path | str = ROOT,
    release_dir: Path | str | None = None,
) -> ReleaseBuildResult:
    """Verify the immutable v0.1.1 release against its exact source inputs."""

    resolved_root = Path(root).expanduser().resolve()
    target = _resolve_patch_output(resolved_root, release_dir)
    expected, release_sha256, files = _expected_patch_release(resolved_root)
    return _verify_patch_expected(
        target,
        expected,
        release_sha256,
        files,
        status="VERIFIED",
    )


def verify_security_patch_release(
    root: Path | str = ROOT,
    release_dir: Path | str | None = None,
) -> ReleaseBuildResult:
    """Verify the immutable v0.1.2 security patch against fixed inputs."""

    resolved_root = Path(root).expanduser().resolve()
    target = _resolve_security_patch_output(resolved_root, release_dir)
    expected, release_sha256, files = _expected_patch_release(
        resolved_root,
        release_version=SECURITY_PATCH_RELEASE_VERSION,
        schema_version="v0.1.2",
        security_correction=SECURITY_CORRECTION,
    )
    return _verify_patch_expected(
        target,
        expected,
        release_sha256,
        files,
        status="VERIFIED",
    )


def verify_security_runtime_patch_release(
    root: Path | str = ROOT,
    release_dir: Path | str | None = None,
) -> ReleaseBuildResult:
    """Verify the immutable dependency-complete v0.1.3 security patch."""

    resolved_root = Path(root).expanduser().resolve()
    target = _resolve_security_runtime_patch_output(resolved_root, release_dir)
    expected, release_sha256, files = _expected_patch_release(
        resolved_root,
        release_version=SECURITY_RUNTIME_PATCH_RELEASE_VERSION,
        schema_version="v0.1.3",
        security_correction=SECURITY_CORRECTION,
        include_d3_rule_registry=True,
    )
    return _verify_patch_expected(
        target,
        expected,
        release_sha256,
        files,
        status="VERIFIED",
    )


def _write_patch_staging(staging: Path, expected: Mapping[str, bytes]) -> None:
    """Write a patch staging tree with deterministic executable/read-only modes."""

    try:
        staging.mkdir(mode=0o700)
    except FileExistsError as error:
        raise ReleaseBuildError(
            "HOLD_RELEASE_BUILD_IN_PROGRESS", str(staging)
        ) from error
    except OSError as error:
        raise ReleaseBuildError(
            "ERR_RELEASE_CREATE_FAILED", str(staging)
        ) from error
    try:
        for relative, content in sorted(expected.items()):
            destination = staging / relative
            destination.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
            with destination.open("xb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            if relative == PATCH_ENTRYPOINT.as_posix():
                destination.chmod(0o755)
            elif relative in {item.as_posix() for item in PATCH_POLICY_PATHS}:
                destination.chmod(0o444)
            else:
                destination.chmod(0o644)
        staging.chmod(0o755)
    except OSError as error:
        shutil.rmtree(staging, ignore_errors=True)
        raise ReleaseBuildError(
            "ERR_RELEASE_CREATE_FAILED", str(staging)
        ) from error


def build_patch_release(
    root: Path | str = ROOT,
    output_dir: Path | str | None = None,
) -> ReleaseBuildResult:
    """Build the new patch release atomically without touching the old release."""

    resolved_root = Path(root).expanduser().resolve()
    target = _resolve_patch_output(resolved_root, output_dir)
    expected, release_sha256, files = _expected_patch_release(resolved_root)
    if target.exists():
        return _verify_patch_expected(
            target,
            expected,
            release_sha256,
            files,
            status="ALREADY_BUILT",
        )
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise ReleaseBuildError(
            "ERR_RELEASE_CREATE_FAILED", str(target.parent)
        ) from error
    staging = target.parent / f".{target.name}.building"
    _write_patch_staging(staging, expected)
    if target.exists():
        shutil.rmtree(staging, ignore_errors=True)
        return _verify_patch_expected(
            target,
            expected,
            release_sha256,
            files,
            status="ALREADY_BUILT",
        )
    try:
        os.rename(staging, target)
    except OSError as error:
        shutil.rmtree(staging, ignore_errors=True)
        if target.exists():
            return _verify_patch_expected(
                target,
                expected,
                release_sha256,
                files,
                status="ALREADY_BUILT",
            )
        raise ReleaseBuildError(
            "ERR_RELEASE_CREATE_FAILED", str(target)
        ) from error
    return _verify_patch_expected(
        target,
        expected,
        release_sha256,
        files,
        status="BUILT",
    )


def build_security_patch_release(
    root: Path | str = ROOT,
    output_dir: Path | str | None = None,
) -> ReleaseBuildResult:
    """Build v0.1.2 atomically while leaving every older Release unchanged."""

    resolved_root = Path(root).expanduser().resolve()
    target = _resolve_security_patch_output(resolved_root, output_dir)
    expected, release_sha256, files = _expected_patch_release(
        resolved_root,
        release_version=SECURITY_PATCH_RELEASE_VERSION,
        schema_version="v0.1.2",
        security_correction=SECURITY_CORRECTION,
    )
    if target.exists():
        return _verify_patch_expected(
            target,
            expected,
            release_sha256,
            files,
            status="ALREADY_BUILT",
        )
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise ReleaseBuildError(
            "ERR_RELEASE_CREATE_FAILED", str(target.parent)
        ) from error
    staging = target.parent / f".{target.name}.building"
    _write_patch_staging(staging, expected)
    if target.exists():
        shutil.rmtree(staging, ignore_errors=True)
        return _verify_patch_expected(
            target,
            expected,
            release_sha256,
            files,
            status="ALREADY_BUILT",
        )
    try:
        os.rename(staging, target)
    except OSError as error:
        shutil.rmtree(staging, ignore_errors=True)
        if target.exists():
            return _verify_patch_expected(
                target,
                expected,
                release_sha256,
                files,
                status="ALREADY_BUILT",
            )
        raise ReleaseBuildError(
            "ERR_RELEASE_CREATE_FAILED", str(staging)
        ) from error
    return _verify_patch_expected(
        target,
        expected,
        release_sha256,
        files,
        status="BUILT",
    )


def build_security_runtime_patch_release(
    root: Path | str = ROOT,
    output_dir: Path | str | None = None,
) -> ReleaseBuildResult:
    """Build v0.1.3 atomically without changing any older Release."""

    resolved_root = Path(root).expanduser().resolve()
    target = _resolve_security_runtime_patch_output(resolved_root, output_dir)
    expected, release_sha256, files = _expected_patch_release(
        resolved_root,
        release_version=SECURITY_RUNTIME_PATCH_RELEASE_VERSION,
        schema_version="v0.1.3",
        security_correction=SECURITY_CORRECTION,
        include_d3_rule_registry=True,
    )
    if target.exists():
        return _verify_patch_expected(
            target,
            expected,
            release_sha256,
            files,
            status="ALREADY_BUILT",
        )
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise ReleaseBuildError(
            "ERR_RELEASE_CREATE_FAILED", str(target.parent)
        ) from error
    staging = target.parent / f".{target.name}.building"
    _write_patch_staging(staging, expected)
    if target.exists():
        shutil.rmtree(staging, ignore_errors=True)
        return _verify_patch_expected(
            target,
            expected,
            release_sha256,
            files,
            status="ALREADY_BUILT",
        )
    try:
        os.rename(staging, target)
    except OSError as error:
        shutil.rmtree(staging, ignore_errors=True)
        if target.exists():
            return _verify_patch_expected(
                target,
                expected,
                release_sha256,
                files,
                status="ALREADY_BUILT",
            )
        raise ReleaseBuildError(
            "ERR_RELEASE_CREATE_FAILED", str(staging)
        ) from error
    return _verify_patch_expected(
        target,
        expected,
        release_sha256,
        files,
        status="BUILT",
    )


def _parser() -> argparse.ArgumentParser:
    """Create the stable release-builder command-line parser."""

    parser = argparse.ArgumentParser(
        description="Build or verify the deterministic W7TP small-agent release."
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=(
            "build",
            "verify",
            "canonical-hash",
            "build-patch",
            "verify-patch",
            "patch-canonical-hash",
            "build-security-patch",
            "verify-security-patch",
            "security-patch-canonical-hash",
            "build-security-runtime-patch",
            "verify-security-runtime-patch",
            "security-runtime-patch-canonical-hash",
        ),
        default="build",
    )
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output-dir")
    return parser


def _print_result(result: ReleaseBuildResult) -> None:
    """Print a concise deterministic successful command result."""

    print(f"STATE=PASS_W7TP_SMALL_AGENT_RELEASE_{result.status}")
    print(f"RELEASE_VERSION={RELEASE_VERSION}")
    print(f"RELEASE_SHA256={result.release_sha256}")
    print(f"FILES={len(result.files)}")


def _print_patch_result(result: ReleaseBuildResult) -> None:
    """Print the patch identity without changing the old output contract."""

    print(f"STATE=PASS_W7TP_SMALL_AGENT_PATCH_RELEASE_{result.status}")
    print(f"RELEASE_VERSION={PATCH_RELEASE_VERSION}")
    print(f"RELEASE_SHA256={result.release_sha256}")
    print(f"FILES={len(result.files)}")


def _print_security_patch_result(result: ReleaseBuildResult) -> None:
    """Print the immutable security-patch identity."""

    print(f"STATE=PASS_W7TP_SMALL_AGENT_SECURITY_PATCH_RELEASE_{result.status}")
    print(f"RELEASE_VERSION={SECURITY_PATCH_RELEASE_VERSION}")
    print(f"RELEASE_SHA256={result.release_sha256}")
    print(f"FILES={len(result.files)}")


def _print_security_runtime_patch_result(result: ReleaseBuildResult) -> None:
    """Print the dependency-complete security-patch identity."""

    print(
        "STATE=PASS_W7TP_SMALL_AGENT_SECURITY_RUNTIME_PATCH_RELEASE_"
        f"{result.status}"
    )
    print(f"RELEASE_VERSION={SECURITY_RUNTIME_PATCH_RELEASE_VERSION}")
    print(f"RELEASE_SHA256={result.release_sha256}")
    print(f"FILES={len(result.files)}")


def main(argv: list[str] | None = None) -> int:
    """Run deterministic build, verification, or identity-hash output."""

    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "security-runtime-patch-canonical-hash":
            expected, release_sha256, files = _expected_patch_release(
                Path(arguments.root).expanduser().resolve(),
                release_version=SECURITY_RUNTIME_PATCH_RELEASE_VERSION,
                schema_version="v0.1.3",
                security_correction=SECURITY_CORRECTION,
                include_d3_rule_registry=True,
            )
            if not expected or not files:
                raise ReleaseBuildError("ERR_RELEASE_INVENTORY_INTERNAL")
            print(release_sha256)
            return 0
        if arguments.command == "security-patch-canonical-hash":
            expected, release_sha256, files = _expected_patch_release(
                Path(arguments.root).expanduser().resolve(),
                release_version=SECURITY_PATCH_RELEASE_VERSION,
                schema_version="v0.1.2",
                security_correction=SECURITY_CORRECTION,
            )
            if not expected or not files:
                raise ReleaseBuildError("ERR_RELEASE_INVENTORY_INTERNAL")
            print(release_sha256)
            return 0
        if arguments.command == "patch-canonical-hash":
            expected, release_sha256, files = _expected_patch_release(
                Path(arguments.root).expanduser().resolve()
            )
            if not expected or not files:
                raise ReleaseBuildError("ERR_RELEASE_INVENTORY_INTERNAL")
            print(release_sha256)
            return 0
        if arguments.command == "canonical-hash":
            expected, release_sha256, files = _expected_release(
                Path(arguments.root).expanduser().resolve()
            )
            if not expected or not files:
                raise ReleaseBuildError("ERR_RELEASE_INVENTORY_INTERNAL")
            print(release_sha256)
            return 0
        if arguments.command == "verify-patch":
            result = verify_patch_release(arguments.root, arguments.output_dir)
            _print_patch_result(result)
            return 0
        if arguments.command == "verify-security-patch":
            result = verify_security_patch_release(
                arguments.root, arguments.output_dir
            )
            _print_security_patch_result(result)
            return 0
        if arguments.command == "verify-security-runtime-patch":
            result = verify_security_runtime_patch_release(
                arguments.root, arguments.output_dir
            )
            _print_security_runtime_patch_result(result)
            return 0
        if arguments.command == "build-patch":
            result = build_patch_release(arguments.root, arguments.output_dir)
            _print_patch_result(result)
            return 0
        if arguments.command == "build-security-patch":
            result = build_security_patch_release(
                arguments.root, arguments.output_dir
            )
            _print_security_patch_result(result)
            return 0
        if arguments.command == "build-security-runtime-patch":
            result = build_security_runtime_patch_release(
                arguments.root, arguments.output_dir
            )
            _print_security_runtime_patch_result(result)
            return 0
        if arguments.command == "verify":
            result = verify_release(arguments.root, arguments.output_dir)
        else:
            result = build_release(arguments.root, arguments.output_dir)
        _print_result(result)
        return 0
    except ReleaseBuildError as error:
        print("STATE=HOLD_W7TP_SMALL_AGENT_RELEASE")
        print(f"REASON_CODE={error.reason_code}")
        if error.path:
            print(f"PATH={error.path}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
