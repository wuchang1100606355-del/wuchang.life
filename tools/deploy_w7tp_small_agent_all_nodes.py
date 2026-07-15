#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic, authority-gated W7TP small-agent deployment orchestrator."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "W7TP_SMALL_AGENT_ALL_NODE_DEPLOYMENT_V0_1_D27230ABA7A4"
ACTIVE_CANONICAL = Path(
    "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_CANONICAL.json"
)
ACTIVE_POINTER = Path(
    "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_POINTER.txt"
)
INSTALL_RELATIVE_ROOT = Path(".local/share/w7tp-small-agent")
USER_SERVICE_RELATIVE_PATH = Path(
    ".config/systemd/user/w7tp-small-agent.service"
)
SERVICE_NAME = "w7tp-small-agent.service"
REQUIRED_FORMAL_FIELDS = (
    "hostname",
    "address",
    "authority",
    "observation_domain",
    "connection_method",
)
FORMAL_NODE_IDS = (
    "taiji01",
    "MSI",
    "penguin",
    "localhost",
    "DESKTOP-OHE05SC",
    "wuchang-us-free-node",
    "V3_MIX_EDLA_GL",
    "RT-BE86U-7428",
)
AUTHORITY_REGISTRY_SCHEMA = "w7tp.small-agent.node-authority-registry/v0.1"
OWNER_AUTHORITY = "OWNER_AUTHORIZED"
OWNER_AUTHORITY_SCOPE = "W7TP_SMALL_AGENT_INSTALL_V0_1_ONLY"
RELEASE_RUNTIME_ENTRYPOINT = Path("bin/w7tp-small-agent")
INSTALLED_RUNTIME_ENTRYPOINT = (
    "~/.local/share/w7tp-small-agent/current/bin/w7tp-small-agent"
)
ENTRYPOINT_READONLY_COMMANDS = frozenset({"version", "health", "self-test"})
MAX_ENTRYPOINT_OUTPUT_BYTES = 65536
HEALTH_REQUIRED_CHECKS = {
    "release_files": "PASS",
    "policy_sha256": "PASS",
    "module_imports": "PASS",
    "capability_manifest": "PASS",
    "eightd_gte_parser": "PASS",
    "total_field_gateway": "PASS",
    "allow_only_commit": "PASS",
    "adi_production_mode": "DISABLED",
}
SELF_TEST_REQUIRED_CHECKS = {
    "d1_projection": "PASS",
    "candidate_replay": "PASS",
    "total_field_pull": "PASS",
    "llm_push": "PASS",
    "common_receive_path": "PASS",
    "allow_only_commit": "PASS",
    "hold_preserves_previous": "PASS",
    "block_preserves_previous": "PASS",
    "quarantine_preserves_previous": "PASS",
    "persona_governance_separation": "PASS",
    "llm_direct_commit": "BLOCKED",
    "raw_secret_scan": "PASS",
}
REGISTRY_NODE_FIELDS = frozenset(
    {
        "node_id",
        "canonical_source",
        "kind",
        "hostname",
        "address",
        "authority",
        "authority_scope",
        "observation_domain",
        "connection_method",
        "deployment_eligibility",
        "evidence_refs",
        "alias_of",
        "reason_code",
    }
)
REGISTRY_OPTIONAL_NODE_FIELDS = frozenset({"ssh_user"})
SUPPORTED_LOCAL_METHODS = frozenset({"LOCAL", "LOCAL_LINUX_USER", "LOCAL_SHELL"})
SUPPORTED_REMOTE_METHODS = frozenset({"SSH"})
ROUTER_KIND_MARKERS = ("router", "asuswrt")
UNSUPPORTED_KINDS = frozenset({"android", "ios", "windows"})
SAFE_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SAFE_REMOTE_ADDRESS = re.compile(r"^[A-Za-z0-9._@:-]+$")
SAFE_SSH_USER = re.compile(r"^[A-Za-z_][A-Za-z0-9._-]{0,63}$")
SAFE_RELEASE_PATH = re.compile(r"^[A-Za-z0-9._/-]+$")


class DeploymentError(Exception):
    """Stable deployment error that never includes sensitive payload content."""

    def __init__(self, reason_code: str):
        """Store one stable reason code."""

        self.reason_code = reason_code
        super().__init__(reason_code)


@dataclass(frozen=True)
class CommandResult:
    """Non-interactive command outcome returned by an executor."""

    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class NodeRecord:
    """One formal node and its immutable deployment decision snapshot."""

    node_id: str
    kind: str
    hostname: str | None = None
    ssh_user: str | None = None
    address: str | None = None
    authority: Any = None
    observation_domain: Any = None
    connection_method: str | None = None
    agent_version: str | None = None
    existing_installation: Any = None
    deployment_eligibility: Any = None
    deployment_result: Any = None
    canonical_source: str | None = None
    authority_scope: str | None = None
    evidence_refs: Any = None
    alias_of: str | None = None
    reason_code: str | None = None


class RemoteExecutor(Protocol):
    """Minimal executor contract suitable for deterministic fake implementations."""

    def run(
        self,
        node: NodeRecord,
        argv: Sequence[str],
        *,
        input_text: str | None = None,
    ) -> CommandResult:
        """Run one non-interactive argv command for an explicitly authorized node."""

        raise DeploymentError("REMOTE_EXECUTOR_PROTOCOL_NOT_IMPLEMENTED")

    def transfer_release(
        self,
        node: NodeRecord,
        release_dir: Path,
        destination: str,
    ) -> CommandResult:
        """Transfer one bounded release tree without overwriting a destination."""

        raise DeploymentError("HOLD_RELEASE_TRANSFER_UNSUPPORTED")


def _is_safe_entrypoint_command(command: Sequence[str]) -> bool:
    """Allow only read-only commands on the dedicated installed entrypoint."""

    if len(command) != 2 or command[1] not in ENTRYPOINT_READONLY_COMMANDS:
        return False
    executable = command[0]
    if executable == INSTALLED_RUNTIME_ENTRYPOINT:
        return True
    path = Path(executable)
    suffix = tuple(INSTALL_RELATIVE_ROOT.parts) + (
        "current",
        "bin",
        "w7tp-small-agent",
    )
    return path.is_absolute() and tuple(path.parts[-len(suffix) :]) == suffix


def _safe_command(argv: Sequence[str]) -> tuple[str, ...]:
    """Validate a command against the narrow user-level installation allowlist."""

    command = tuple(str(item) for item in argv)
    if not command or any("\x00" in item for item in command):
        raise DeploymentError("HOLD_UNSAFE_DEPLOYMENT_COMMAND")
    if _is_safe_entrypoint_command(command):
        return command
    allowed = {
        "cp",
        "install",
        "ln",
        "mv",
        "readlink",
        "sha256sum",
        "systemctl",
        "tee",
        "test",
    }
    if command[0] not in allowed:
        raise DeploymentError("HOLD_UNSAFE_DEPLOYMENT_COMMAND")
    forbidden_tokens = {
        "sudo",
        "su",
        "iptables",
        "nft",
        "firewall-cmd",
        "reboot",
        "shutdown",
        "docker",
        "mysql",
        "psql",
        "sqlite3",
        "nvram",
    }
    if any(item.lower() in forbidden_tokens for item in command):
        raise DeploymentError("HOLD_UNSAFE_DEPLOYMENT_COMMAND")
    if command[0] == "systemctl" and "--user" not in command:
        raise DeploymentError("HOLD_SYSTEM_SERVICE_AUTHORITY_FORBIDDEN")
    return command


class LocalLinuxExecutor:
    """Run allowlisted Linux user commands locally without a command shell."""

    def run(
        self,
        node: NodeRecord,
        argv: Sequence[str],
        *,
        input_text: str | None = None,
    ) -> CommandResult:
        """Execute one safe local argv command and return bounded output."""

        if (node.connection_method or "").upper() not in SUPPORTED_LOCAL_METHODS:
            raise DeploymentError("HOLD_UNSUPPORTED_DEPLOYMENT_TRANSPORT")
        command = _safe_command(argv)
        completed = subprocess.run(
            command,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
            shell=False,
        )
        return CommandResult(
            completed.returncode,
            completed.stdout[:4096],
            completed.stderr[:4096],
        )

    def transfer_release(
        self,
        node: NodeRecord,
        release_dir: Path,
        destination: str,
    ) -> CommandResult:
        """Copy one release tree locally with exclusive destination creation."""

        if (node.connection_method or "").upper() not in SUPPORTED_LOCAL_METHODS:
            raise DeploymentError("HOLD_UNSUPPORTED_DEPLOYMENT_TRANSPORT")
        target = Path(destination).expanduser()
        try:
            shutil.copytree(Path(release_dir), target, copy_function=shutil.copy2)
        except FileExistsError:
            return CommandResult(2, "", "HOLD_EXISTING_RELEASE_VERSION_CONFLICT")
        except OSError:
            return CommandResult(2, "", "HOLD_RELEASE_TRANSFER_FAILED")
        return CommandResult(0, "", "")


class SSHExecutor:
    """Non-interactive SSH executor available only for an explicit formal SSH record."""

    def __init__(
        self,
        ssh_binary: str = "ssh",
        scp_binary: str = "scp",
        port: int | None = None,
    ):
        """Configure the executable name and an optional formally supplied port."""

        if ssh_binary not in {"ssh", "/usr/bin/ssh", "/bin/ssh"} or scp_binary not in {
            "scp",
            "/usr/bin/scp",
            "/bin/scp",
        }:
            raise DeploymentError("HOLD_UNSAFE_REMOTE_EXECUTOR_BINARY")
        if port is not None and (port < 1 or port > 65535):
            raise DeploymentError("HOLD_FORMAL_NODE_OR_AUTHORITY_UNRESOLVED")
        self._ssh_binary = ssh_binary
        self._scp_binary = scp_binary
        self._port = port

    def _destination(self, node: NodeRecord) -> str:
        """Return one validated credential-free SSH destination."""

        if (node.connection_method or "").upper() != "SSH":
            raise DeploymentError("HOLD_UNSUPPORTED_DEPLOYMENT_TRANSPORT")
        destination = node.address or node.hostname or ""
        if (
            not destination
            or "@" in destination
            or not SAFE_REMOTE_ADDRESS.fullmatch(destination)
        ):
            raise DeploymentError("HOLD_FORMAL_NODE_OR_AUTHORITY_UNRESOLVED")
        ssh_user = node.ssh_user
        if ssh_user is None:
            return destination
        if not SAFE_SSH_USER.fullmatch(ssh_user):
            raise DeploymentError("HOLD_FORMAL_NODE_OR_AUTHORITY_UNRESOLVED")
        return f"{ssh_user}@{destination}"

    def run(
        self,
        node: NodeRecord,
        argv: Sequence[str],
        *,
        input_text: str | None = None,
    ) -> CommandResult:
        """Execute one safe command through BatchMode SSH without credentials."""

        destination = self._destination(node)
        remote_command = _safe_command(argv)
        command = [
            self._ssh_binary,
            "-o",
            "BatchMode=yes",
            "-o",
            "PasswordAuthentication=no",
            "-o",
            "KbdInteractiveAuthentication=no",
            "-o",
            "StrictHostKeyChecking=yes",
        ]
        if self._port is not None:
            command.extend(("-p", str(self._port)))
        command.extend((destination, *remote_command))
        completed = subprocess.run(
            command,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
            shell=False,
        )
        return CommandResult(completed.returncode, completed.stdout[:4096], "")

    def transfer_release(
        self,
        node: NodeRecord,
        release_dir: Path,
        destination: str,
    ) -> CommandResult:
        """Transfer one explicit release through non-interactive BatchMode SCP."""

        remote = self._destination(node)
        if not destination.startswith("~/.local/share/w7tp-small-agent/releases/"):
            raise DeploymentError("HOLD_UNSAFE_RELEASE_DESTINATION")
        if not SAFE_RELEASE_PATH.fullmatch(destination[2:]):
            raise DeploymentError("HOLD_UNSAFE_RELEASE_DESTINATION")
        command = [
            self._scp_binary,
            "-r",
            "-q",
            "-B",
            "-o",
            "BatchMode=yes",
            "-o",
            "PasswordAuthentication=no",
            "-o",
            "KbdInteractiveAuthentication=no",
            "-o",
            "StrictHostKeyChecking=yes",
        ]
        if self._port is not None:
            command.extend(("-P", str(self._port)))
        command.extend((str(Path(release_dir)), f"{remote}:{destination}"))
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
            shell=False,
        )
        return CommandResult(completed.returncode, "", "")


class ConnectionRoutingExecutor:
    """Route each formal node to its already selected local or SSH executor."""

    def __init__(
        self,
        local_executor: RemoteExecutor | None = None,
        ssh_executor: RemoteExecutor | None = None,
    ):
        """Store executor objects without opening any connection."""

        self._local = local_executor if local_executor is not None else LocalLinuxExecutor()
        self._ssh = ssh_executor if ssh_executor is not None else SSHExecutor()

    def _executor(self, node: NodeRecord) -> RemoteExecutor:
        """Select an executor strictly from the verified registry method."""

        method = (node.connection_method or "").upper()
        if method in SUPPORTED_LOCAL_METHODS:
            return self._local
        if method == "SSH":
            return self._ssh
        raise DeploymentError("HOLD_UNSUPPORTED_DEPLOYMENT_TRANSPORT")

    def run(
        self,
        node: NodeRecord,
        argv: Sequence[str],
        *,
        input_text: str | None = None,
    ) -> CommandResult:
        """Run through the executor selected for this one node."""

        return self._executor(node).run(node, argv, input_text=input_text)

    def transfer_release(
        self,
        node: NodeRecord,
        release_dir: Path,
        destination: str,
    ) -> CommandResult:
        """Transfer through the executor selected for this one node."""

        return self._executor(node).transfer_release(node, release_dir, destination)


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build a JSON object while rejecting duplicate member names."""

    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DeploymentError("HOLD_ACTIVE_CANONICAL_INVALID")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> Any:
    """Reject non-standard non-finite JSON numeric constants."""

    raise DeploymentError("HOLD_ACTIVE_CANONICAL_INVALID")


def _ensure_finite(value: Any) -> None:
    """Reject numeric overflow and nested non-finite values."""

    if isinstance(value, float) and not math.isfinite(value):
        raise DeploymentError("HOLD_ACTIVE_CANONICAL_INVALID")
    if isinstance(value, dict):
        for nested in value.values():
            _ensure_finite(nested)
    elif isinstance(value, list):
        for nested in value:
            _ensure_finite(nested)


def _load_json(path: Path) -> Any:
    """Read strict UTF-8 JSON from one approved path."""

    try:
        text = path.read_text(encoding="utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_nonfinite,
        )
        _ensure_finite(value)
        return value
    except DeploymentError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise DeploymentError("HOLD_ACTIVE_CANONICAL_INVALID") from error


def _canonical_json(value: Any) -> str:
    """Serialize JSON with the deterministic repository contract."""

    try:
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise DeploymentError("HOLD_NONDETERMINISTIC_DEPLOYMENT_VALUE") from error


def _read_pointer(root: Path) -> Path:
    """Resolve the formal active pointer without consulting any other registry."""

    pointer_path = root / ACTIVE_POINTER
    try:
        raw = pointer_path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as error:
        raise DeploymentError("HOLD_ACTIVE_POINTER_INVALID") from error
    if not raw or "\n" in raw or "\r" in raw:
        raise DeploymentError("HOLD_ACTIVE_POINTER_INVALID")
    target = Path(raw)
    if not target.is_absolute():
        target = root / target
    try:
        target.resolve().relative_to(root.resolve())
    except (OSError, ValueError) as error:
        raise DeploymentError("HOLD_ACTIVE_POINTER_OUTSIDE_REPOSITORY") from error
    if not target.is_file():
        raise DeploymentError("HOLD_ACTIVE_POINTER_TARGET_UNAVAILABLE")
    return target


def _is_present(value: Any) -> bool:
    """Return whether a formal field is explicitly populated."""

    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (dict, list, tuple, set)):
        return bool(value)
    return True


def _is_router(kind: str) -> bool:
    """Identify router records solely from their formal kind."""

    normalized = kind.casefold()
    return any(marker in normalized for marker in ROUTER_KIND_MARKERS)


def _registry_json(root: Path, registry_path: Path) -> dict[str, Any]:
    """Load one repository-local authority registry with a stable error boundary."""

    path = Path(registry_path)
    if not path.is_absolute():
        path = root / path
    try:
        path.resolve().relative_to(root.resolve())
    except (OSError, ValueError) as error:
        raise DeploymentError("HOLD_AUTHORITY_REGISTRY_INVALID") from error
    try:
        value = _load_json(path)
    except DeploymentError as error:
        raise DeploymentError("HOLD_AUTHORITY_REGISTRY_INVALID") from error
    if not isinstance(value, dict):
        raise DeploymentError("HOLD_AUTHORITY_REGISTRY_INVALID")
    return value


def _registry_evidence(raw: Mapping[str, Any]) -> tuple[str, ...]:
    """Return closed, nonempty evidence references without interpreting payloads."""

    evidence = raw.get("evidence_refs")
    if (
        not isinstance(evidence, list)
        or not evidence
        or any(not isinstance(item, str) or not item for item in evidence)
    ):
        raise DeploymentError("HOLD_AUTHORITY_REGISTRY_INVALID")
    return tuple(evidence)


def _local_identity_verified(raw: Mapping[str, Any], evidence: Sequence[str]) -> bool:
    """Verify LOCAL_SHELL identity only from an exact hostname command reference."""

    hostname = raw.get("hostname")
    address = raw.get("address")
    node_id = raw.get("node_id")
    if not isinstance(hostname, str) or not hostname:
        return False
    if address not in {hostname, node_id}:
        return False
    accepted = {
        f"local-command:hostname:exact={hostname}",
        f"local-command:hostnamectl-static:exact={hostname}",
    }
    return any(item in accepted for item in evidence)


def _tailscale_address_verified(
    raw: Mapping[str, Any], evidence: Sequence[str]
) -> bool:
    """Accept a Tailscale address only from an exact online node/hostname match."""

    node_id = raw.get("node_id")
    hostname = raw.get("hostname")
    address = raw.get("address")
    if not all(isinstance(item, str) and item for item in (node_id, hostname, address)):
        return False
    exact_segments = {
        f"exact-hostname={node_id}",
        f"exact-hostname={hostname}",
        f"exact-node-id={node_id}",
        f"exact-node-id={hostname}",
    }
    for item in evidence:
        if not item.startswith("local-command:tailscale-status-json:"):
            continue
        segments = set(item.split(":"))
        exact = bool(segments & exact_segments) or (
            "self" in segments and f"hostname={hostname}" in segments
        )
        if exact and f"ipv4={address}" in segments and "online=true" in segments:
            return True
    return False


def _ssh_config_verified(raw: Mapping[str, Any], evidence: Sequence[str]) -> bool:
    """Accept SSH only when ssh -G parsed the exact node id or hostname alias."""

    node_id = raw.get("node_id")
    hostname = raw.get("hostname")
    aliases = {f"alias={node_id}", f"alias={hostname}"}
    for item in evidence:
        if not item.startswith("local-command:ssh-G:"):
            continue
        segments = set(item.split(":"))
        if "parsed=true" in segments and segments & aliases:
            return True
    return False


def _registry_eligibility(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute registry eligibility; never trust its boolean by itself."""

    kind = str(raw.get("kind", ""))
    if _is_router(kind):
        return {"status": "HOLD", "reason_code": "HOLD_ROUTER_WRITE_NOT_AUTHORIZED"}
    alias_of = raw.get("alias_of")
    if isinstance(alias_of, str) and alias_of:
        return {"status": "HOLD", "reason_code": "HOLD_ALIAS_DEDUPLICATED"}
    requested = raw.get("deployment_eligibility")
    if not requested:
        return {"status": "HOLD", "reason_code": str(raw.get("reason_code"))}
    if kind.casefold() != "linux" or kind.casefold() in UNSUPPORTED_KINDS:
        return {"status": "HOLD", "reason_code": "HOLD_UNSUPPORTED_DEPLOYMENT_TRANSPORT"}
    if not _is_present(raw.get("address")):
        return {"status": "HOLD", "reason_code": "HOLD_NODE_ADDRESS_NOT_VERIFIED"}
    if not _is_present(raw.get("hostname")) or not _is_present(raw.get("observation_domain")):
        return {
            "status": "HOLD",
            "reason_code": "HOLD_FORMAL_NODE_OR_AUTHORITY_UNRESOLVED",
        }
    evidence = _registry_evidence(raw)
    method = str(raw.get("connection_method") or "").upper()
    if method in SUPPORTED_LOCAL_METHODS:
        if not _local_identity_verified(raw, evidence):
            return {
                "status": "HOLD",
                "reason_code": "HOLD_CONNECTION_METHOD_NOT_VERIFIED",
            }
    elif method == "SSH":
        ssh_user = raw.get("ssh_user")
        if not isinstance(ssh_user, str) or not SAFE_SSH_USER.fullmatch(ssh_user):
            return {
                "status": "HOLD",
                "reason_code": "HOLD_CONNECTION_METHOD_NOT_VERIFIED",
            }
        if not _tailscale_address_verified(raw, evidence):
            return {"status": "HOLD", "reason_code": "HOLD_NODE_ADDRESS_NOT_VERIFIED"}
        if not _ssh_config_verified(raw, evidence):
            return {
                "status": "HOLD",
                "reason_code": "HOLD_CONNECTION_METHOD_NOT_VERIFIED",
            }
    else:
        return {
            "status": "HOLD",
            "reason_code": "HOLD_CONNECTION_METHOD_NOT_VERIFIED",
        }
    return {"status": "ELIGIBLE", "reason_code": str(raw.get("reason_code"))}


def _authority_registry_nodes(
    root: Path,
    registry_path: Path,
    active_nodes: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    """Validate one exact registry overlay against the eight active formal nodes."""

    registry = _registry_json(root, registry_path)
    if (
        registry.get("schema_version") != AUTHORITY_REGISTRY_SCHEMA
        or registry.get("run_id") != RUN_ID
        or registry.get("owner_confirmation") != "YES"
        or registry.get("owner_authority_scope") != OWNER_AUTHORITY_SCOPE
        or registry.get("canonical_source") != ACTIVE_CANONICAL.as_posix()
    ):
        raise DeploymentError("HOLD_AUTHORITY_REGISTRY_INVALID")
    active_ids = tuple(str(item.get("node_id", "")) for item in active_nodes)
    formal_ids = registry.get("formal_node_ids")
    nodes = registry.get("nodes")
    if (
        active_ids != FORMAL_NODE_IDS
        or not isinstance(formal_ids, list)
        or tuple(formal_ids) != FORMAL_NODE_IDS
        or not isinstance(nodes, list)
    ):
        raise DeploymentError("HOLD_AUTHORITY_REGISTRY_NODE_SET_MISMATCH")
    by_id: dict[str, Mapping[str, Any]] = {}
    active_by_id = {str(item["node_id"]): item for item in active_nodes}
    for raw in nodes:
        if (
            not isinstance(raw, dict)
            or not REGISTRY_NODE_FIELDS <= raw.keys()
            or not raw.keys() <= REGISTRY_NODE_FIELDS | REGISTRY_OPTIONAL_NODE_FIELDS
        ):
            raise DeploymentError("HOLD_AUTHORITY_REGISTRY_INVALID")
        node_id = raw.get("node_id")
        if not isinstance(node_id, str) or not node_id or node_id in by_id:
            raise DeploymentError("HOLD_AUTHORITY_REGISTRY_NODE_SET_MISMATCH")
        by_id[node_id] = raw
    if set(by_id) != set(FORMAL_NODE_IDS):
        raise DeploymentError("HOLD_AUTHORITY_REGISTRY_NODE_SET_MISMATCH")
    for node_id in FORMAL_NODE_IDS:
        raw = by_id[node_id]
        active = active_by_id[node_id]
        expected_source = f"{ACTIVE_CANONICAL.as_posix()}#node={node_id}"
        if raw.get("canonical_source") != expected_source or raw.get("kind") != active.get("kind"):
            raise DeploymentError("HOLD_AUTHORITY_REGISTRY_CANONICAL_MISMATCH")
        if not isinstance(raw.get("deployment_eligibility"), bool):
            raise DeploymentError("HOLD_AUTHORITY_REGISTRY_INVALID")
        if not isinstance(raw.get("reason_code"), str) or not raw.get("reason_code"):
            raise DeploymentError("HOLD_AUTHORITY_REGISTRY_INVALID")
        ssh_user = raw.get("ssh_user")
        if ssh_user is not None and (
            not isinstance(ssh_user, str) or not SAFE_SSH_USER.fullmatch(ssh_user)
        ):
            raise DeploymentError("HOLD_AUTHORITY_REGISTRY_INVALID")
        alias_of = raw.get("alias_of")
        if alias_of is not None and (not isinstance(alias_of, str) or not alias_of):
            raise DeploymentError("HOLD_ALIAS_TARGET_INVALID")
        _registry_evidence(raw)
        if not _is_router(str(raw.get("kind", ""))) and (
            raw.get("authority") != OWNER_AUTHORITY
            or raw.get("authority_scope") != OWNER_AUTHORITY_SCOPE
        ):
            raise DeploymentError("HOLD_OWNER_AUTHORITY_SCOPE_INVALID")
    for node_id, raw in by_id.items():
        alias_of = raw.get("alias_of")
        if alias_of is None:
            continue
        if (
            alias_of == node_id
            or alias_of not in by_id
            or by_id[alias_of].get("alias_of") is not None
            or _is_router(str(by_id[alias_of].get("kind", "")))
        ):
            raise DeploymentError("HOLD_ALIAS_TARGET_INVALID")
    return by_id


def _eligibility(node: Mapping[str, Any]) -> dict[str, Any]:
    """Derive one stable eligibility decision without filling missing metadata."""

    kind = str(node.get("kind", ""))
    if _is_router(kind):
        return {"status": "HOLD", "reason_code": "HOLD_ROUTER_WRITE_NOT_AUTHORIZED"}
    missing = [name for name in REQUIRED_FORMAL_FIELDS if not _is_present(node.get(name))]
    if missing:
        return {
            "status": "HOLD",
            "reason_code": "HOLD_FORMAL_NODE_OR_AUTHORITY_UNRESOLVED",
            "missing_fields": missing,
        }
    normalized_kind = kind.casefold()
    method = str(node.get("connection_method", "")).upper()
    if normalized_kind != "linux" or normalized_kind in UNSUPPORTED_KINDS:
        return {
            "status": "HOLD",
            "reason_code": "HOLD_UNSUPPORTED_DEPLOYMENT_TRANSPORT",
        }
    if method not in SUPPORTED_LOCAL_METHODS | SUPPORTED_REMOTE_METHODS:
        return {
            "status": "HOLD",
            "reason_code": "HOLD_UNSUPPORTED_DEPLOYMENT_TRANSPORT",
        }
    authority = node.get("authority")
    if authority is False or (
        isinstance(authority, str)
        and authority.upper() in {"DENIED", "NOT_AUTHORIZED", "READ_ONLY"}
    ):
        return {"status": "HOLD", "reason_code": "HOLD_DEPLOYMENT_NOT_AUTHORIZED"}
    if isinstance(authority, dict) and (
        authority.get("authorized") is False
        or authority.get("deployment_authorized") is False
    ):
        return {"status": "HOLD", "reason_code": "HOLD_DEPLOYMENT_NOT_AUTHORIZED"}
    return {"status": "ELIGIBLE", "reason_code": "FORMAL_NODE_AUTHORITY_RESOLVED"}


def resolve_formal_nodes(
    root: Path = ROOT,
    authority_registry: Path | None = None,
) -> tuple[NodeRecord, ...]:
    """Resolve active nodes, optionally applying one strict authority registry."""

    root = Path(root)
    active = _load_json(root / ACTIVE_CANONICAL)
    pointed = _load_json(_read_pointer(root))
    if _canonical_json(active) != _canonical_json(pointed):
        raise DeploymentError("HOLD_ACTIVE_CANONICAL_POINTER_MISMATCH")
    if not isinstance(active, dict) or not isinstance(active.get("nodes"), list):
        raise DeploymentError("HOLD_ACTIVE_CANONICAL_INVALID")
    active_nodes = active["nodes"]
    if any(not isinstance(raw, dict) for raw in active_nodes):
        raise DeploymentError("HOLD_ACTIVE_CANONICAL_INVALID")
    registry_nodes = (
        _authority_registry_nodes(root, authority_registry, active_nodes)
        if authority_registry is not None
        else None
    )
    records: list[NodeRecord] = []
    seen: set[str] = set()
    for raw in active_nodes:
        node_id = raw.get("node_id")
        kind = raw.get("kind")
        if not isinstance(node_id, str) or not node_id or not isinstance(kind, str) or not kind:
            raise DeploymentError("HOLD_FORMAL_NODE_OR_AUTHORITY_UNRESOLVED")
        if node_id in seen:
            raise DeploymentError("HOLD_DUPLICATE_FORMAL_NODE_ID")
        seen.add(node_id)
        overlay = registry_nodes[node_id] if registry_nodes is not None else raw
        eligibility = (
            _registry_eligibility(overlay)
            if registry_nodes is not None
            else _eligibility(raw)
        )
        records.append(
            NodeRecord(
                node_id=node_id,
                kind=kind,
                hostname=copy.deepcopy(overlay.get("hostname")),
                ssh_user=copy.deepcopy(overlay.get("ssh_user")),
                address=copy.deepcopy(overlay.get("address")),
                authority=copy.deepcopy(overlay.get("authority")),
                observation_domain=copy.deepcopy(overlay.get("observation_domain")),
                connection_method=copy.deepcopy(overlay.get("connection_method")),
                agent_version=copy.deepcopy(overlay.get("agent_version")),
                existing_installation=copy.deepcopy(overlay.get("existing_installation")),
                deployment_eligibility=eligibility,
                deployment_result={
                    "status": eligibility["status"],
                    "reason_code": eligibility["reason_code"],
                },
                canonical_source=copy.deepcopy(overlay.get("canonical_source")),
                authority_scope=copy.deepcopy(overlay.get("authority_scope")),
                evidence_refs=copy.deepcopy(overlay.get("evidence_refs")),
                alias_of=copy.deepcopy(overlay.get("alias_of")),
                reason_code=copy.deepcopy(overlay.get("reason_code")),
            )
        )
    return tuple(records)


def _release_manifest(release_dir: Path) -> tuple[dict[str, Any], Path]:
    """Load one explicit versioned release manifest from a candidate directory."""

    candidates = (
        release_dir / "release_manifest.json",
        release_dir / "agent_manifest.json",
        release_dir / "manifest.json",
    )
    existing = [path for path in candidates if path.is_file()]
    if len(existing) != 1:
        raise DeploymentError("HOLD_RELEASE_MANIFEST_INVALID")
    try:
        value = _load_json(existing[0])
    except DeploymentError as error:
        raise DeploymentError("HOLD_RELEASE_MANIFEST_INVALID") from error
    if not isinstance(value, dict):
        raise DeploymentError("HOLD_RELEASE_MANIFEST_INVALID")
    release_version = value.get("release_version")
    agent_version = value.get("agent_version")
    if release_version is not None and agent_version is not None and release_version != agent_version:
        raise DeploymentError("HOLD_RELEASE_VERSION_INVALID")
    version = release_version if release_version is not None else agent_version
    if not isinstance(version, str) or not SAFE_VERSION.fullmatch(version):
        raise DeploymentError("HOLD_RELEASE_VERSION_INVALID")
    value = copy.deepcopy(value)
    value["agent_version"] = version
    return value, existing[0]


def _release_sha256(release_dir: Path, *, exclude_install_marker: bool = False) -> str:
    """Hash an explicit release tree deterministically by relative path and bytes."""

    digest = hashlib.sha256()
    files = sorted(
        (
            path
            for path in release_dir.rglob("*")
            if path.is_file()
            and not (
                exclude_install_marker
                and path.relative_to(release_dir).as_posix() == ".release_sha256"
            )
        ),
        key=lambda path: path.relative_to(release_dir).as_posix(),
    )
    if not files:
        raise DeploymentError("HOLD_RELEASE_EMPTY")
    for path in files:
        relative = path.relative_to(release_dir).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        content = path.read_bytes()
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _release_file_hashes(release_dir: Path) -> tuple[tuple[str, str], ...]:
    """Return safe relative paths and content hashes for remote verification."""

    entries: list[tuple[str, str]] = []
    for path in sorted(
        (item for item in release_dir.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(release_dir).as_posix(),
    ):
        relative = path.relative_to(release_dir).as_posix()
        if not SAFE_RELEASE_PATH.fullmatch(relative) or ".." in Path(relative).parts:
            raise DeploymentError("HOLD_RELEASE_PATH_INVALID")
        entries.append((relative, hashlib.sha256(path.read_bytes()).hexdigest()))
    if not entries:
        raise DeploymentError("HOLD_RELEASE_EMPTY")
    return tuple(entries)


def _service_content() -> str:
    """Return the locked user-level systemd service definition."""

    return (
        "[Unit]\n"
        "Description=W7TP Small Agent\n"
        "After=default.target\n\n"
        "[Service]\n"
        "Type=simple\n"
        "ExecStart=%h/.local/share/w7tp-small-agent/current/bin/w7tp-small-agent service-run\n"
        "Restart=on-failure\n"
        "NoNewPrivileges=true\n\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )


def _manifest_runtime_identity(manifest: Mapping[str, Any]) -> dict[str, str]:
    """Extract the immutable version and hashes required from runtime output."""

    identity = manifest.get("release_identity")
    release_version = manifest.get("release_version") or manifest.get("agent_version")
    release_sha256 = manifest.get("release_sha256")
    policy_sha256 = manifest.get("policy_sha256")
    if policy_sha256 is None and isinstance(identity, Mapping):
        policy_sha256 = identity.get("policy_sha256")
    if (
        not isinstance(release_version, str)
        or not SAFE_VERSION.fullmatch(release_version)
        or not isinstance(release_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", release_sha256) is None
        or not isinstance(policy_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", policy_sha256) is None
    ):
        raise DeploymentError("HOLD_RELEASE_MANIFEST_INVALID")
    return {
        "release_version": release_version,
        "release_sha256": release_sha256,
        "policy_sha256": policy_sha256,
    }


def _sanitized_entrypoint_environment() -> dict[str, str]:
    """Return a closed environment without inherited credentials or PYTHONPATH."""

    return {
        "HOME": "/nonexistent",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": "/usr/bin:/bin",
        "PYTHONHASHSEED": "0",
        "PYTHONIOENCODING": "utf-8",
    }


def _run_local_entrypoint(entrypoint: Path, command: str, reason: str) -> str:
    """Run one bounded read-only command from an unrelated working directory."""

    if command not in ENTRYPOINT_READONLY_COMMANDS:
        raise DeploymentError("HOLD_UNSAFE_DEPLOYMENT_COMMAND")
    try:
        completed = subprocess.run(
            (str(entrypoint.resolve()), command),
            cwd="/",
            env=_sanitized_entrypoint_environment(),
            text=True,
            capture_output=True,
            check=False,
            shell=False,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired, UnicodeError) as error:
        raise DeploymentError(reason) from error
    if (
        completed.returncode != 0
        or completed.stderr
        or len(completed.stdout.encode("utf-8")) > MAX_ENTRYPOINT_OUTPUT_BYTES
    ):
        raise DeploymentError(reason)
    return completed.stdout


def _validate_version_output(output: str, expected: Mapping[str, str]) -> None:
    """Validate the exact five-line immutable version response."""

    values: dict[str, str] = {}
    lines = output.splitlines()
    for line in lines:
        if "=" not in line:
            raise DeploymentError("HOLD_RELEASE_RUNTIME_VERSION_FAILED")
        key, value = line.split("=", 1)
        if not key or not value or key in values:
            raise DeploymentError("HOLD_RELEASE_RUNTIME_VERSION_FAILED")
        values[key] = value
    required_order = (
        "agent_name",
        "agent_version",
        "release_sha256",
        "policy_sha256",
        "schema_version",
    )
    if (
        len(lines) != 5
        or tuple(values) != required_order
        or values["agent_version"] != expected["release_version"]
        or values["release_sha256"] != expected["release_sha256"]
        or values["policy_sha256"] != expected["policy_sha256"]
    ):
        raise DeploymentError("HOLD_RELEASE_RUNTIME_VERSION_FAILED")


def _strict_output_json(text: str, reason: str) -> dict[str, Any]:
    """Parse one canonical evidence line without duplicate or non-finite values."""

    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_nonfinite,
        )
        _ensure_finite(value)
    except (DeploymentError, json.JSONDecodeError, ValueError, TypeError) as error:
        raise DeploymentError(reason) from error
    if not isinstance(value, dict) or _canonical_json(value) != text:
        raise DeploymentError(reason)
    return value


def _validate_state_evidence_output(
    output: str,
    expected_state: str,
    expected_identity: Mapping[str, str],
    expected_checks: Mapping[str, str],
    reason: str,
) -> None:
    """Validate one two-line PASS state and its closed canonical evidence."""

    lines = output.splitlines()
    if len(lines) != 2 or lines[0] != f"STATE={expected_state}":
        raise DeploymentError(reason)
    evidence = _strict_output_json(lines[1], reason)
    expected_keys = {
        "release_version",
        "release_sha256",
        "policy_sha256",
        "status",
        "checks",
    }
    if expected_state == "PASS_W7TP_SMALL_AGENT_SELF_TEST":
        expected_keys |= {
            "candidate_hash",
            "d1_projection_hash",
            "common_receive_path_marker",
            "gateway_fixture_mode",
        }
    if (
        set(evidence) != expected_keys
        or evidence.get("release_version") != expected_identity["release_version"]
        or evidence.get("release_sha256") != expected_identity["release_sha256"]
        or evidence.get("policy_sha256") != expected_identity["policy_sha256"]
        or evidence.get("status") != "PASS"
        or evidence.get("checks") != dict(expected_checks)
    ):
        raise DeploymentError(reason)
    if expected_state == "PASS_W7TP_SMALL_AGENT_SELF_TEST" and (
        not isinstance(evidence.get("candidate_hash"), str)
        or re.fullmatch(r"[0-9a-f]{64}", evidence["candidate_hash"]) is None
        or not isinstance(evidence.get("d1_projection_hash"), str)
        or re.fullmatch(r"[0-9a-f]{64}", evidence["d1_projection_hash"]) is None
        or evidence.get("common_receive_path_marker")
        != "AgentService._receive_through_gateway/v0.1"
        or evidence.get("gateway_fixture_mode") != "TEST_ONLY"
    ):
        raise DeploymentError(reason)


def preflight_release_runtime_entrypoint(release_dir: Path) -> dict[str, str]:
    """Execute version, health, and self-test before any node operation."""

    release_dir = Path(release_dir)
    entrypoint = release_dir / RELEASE_RUNTIME_ENTRYPOINT
    try:
        mode = entrypoint.lstat().st_mode
    except OSError as error:
        raise DeploymentError("HOLD_RELEASE_RUNTIME_ENTRYPOINT_MISSING") from error
    if not stat.S_ISREG(mode):
        raise DeploymentError("HOLD_RELEASE_RUNTIME_ENTRYPOINT_MISSING")
    if mode & 0o111 == 0 or not os.access(entrypoint, os.X_OK):
        raise DeploymentError("HOLD_RELEASE_RUNTIME_ENTRYPOINT_NOT_EXECUTABLE")
    manifest, _manifest_path = _release_manifest(release_dir)
    expected = _manifest_runtime_identity(manifest)
    version_output = _run_local_entrypoint(
        entrypoint, "version", "HOLD_RELEASE_RUNTIME_VERSION_FAILED"
    )
    _validate_version_output(version_output, expected)
    health_output = _run_local_entrypoint(
        entrypoint, "health", "HOLD_RELEASE_RUNTIME_HEALTHCHECK_FAILED"
    )
    _validate_state_evidence_output(
        health_output,
        "PASS_W7TP_SMALL_AGENT_HEALTH",
        expected,
        HEALTH_REQUIRED_CHECKS,
        "HOLD_RELEASE_RUNTIME_HEALTHCHECK_FAILED",
    )
    self_test_output = _run_local_entrypoint(
        entrypoint, "self-test", "HOLD_RELEASE_RUNTIME_SELF_TEST_FAILED"
    )
    _validate_state_evidence_output(
        self_test_output,
        "PASS_W7TP_SMALL_AGENT_SELF_TEST",
        expected,
        SELF_TEST_REQUIRED_CHECKS,
        "HOLD_RELEASE_RUNTIME_SELF_TEST_FAILED",
    )
    return {
        "status": "PASS",
        "reason_code": "RELEASE_RUNTIME_ENTRYPOINT_VALID",
        "entrypoint": RELEASE_RUNTIME_ENTRYPOINT.as_posix(),
        **expected,
    }


def _write_new_text(path: Path, text: str) -> None:
    """Create one UTF-8 file exclusively and never overwrite existing content."""

    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as error:
        raise DeploymentError("HOLD_EXISTING_INSTALLATION_CONFLICT") from error


def _atomic_symlink(target: Path, link: Path) -> None:
    """Replace one dedicated current symlink through a deterministic temporary link."""

    temporary = link.with_name(link.name + ".next")
    if temporary.exists() or temporary.is_symlink():
        raise DeploymentError("HOLD_STALE_ATOMIC_LINK")
    temporary.symlink_to(target)
    try:
        os.replace(temporary, link)
    except OSError as error:
        if temporary.is_symlink():
            temporary.unlink()
        raise DeploymentError("HOLD_ATOMIC_CURRENT_UPDATE_FAILED") from error


def install_linux_release(
    home: Path,
    release_dir: Path,
    service_changed: bool = True,
) -> dict[str, Any]:
    """Install one immutable Linux user release and atomically switch current."""

    home = Path(home)
    release_dir = Path(release_dir)
    preflight_release_runtime_entrypoint(release_dir)
    manifest, _manifest_path = _release_manifest(release_dir)
    version = manifest["agent_version"]
    release_hash = _release_sha256(release_dir)
    install_root = home / INSTALL_RELATIVE_ROOT
    releases = install_root / "releases"
    rollbacks = install_root / "rollback"
    target = releases / version
    current = install_root / "current"
    service = home / USER_SERVICE_RELATIVE_PATH
    releases.mkdir(parents=True, exist_ok=True)
    rollbacks.mkdir(parents=True, exist_ok=True)
    service.parent.mkdir(parents=True, exist_ok=True)
    expected_service = _service_content()
    service_created = False
    if service.exists():
        try:
            if service.read_text(encoding="utf-8") != expected_service:
                raise DeploymentError("HOLD_EXISTING_USER_SERVICE_CONFLICT")
        except UnicodeError as error:
            raise DeploymentError("HOLD_EXISTING_USER_SERVICE_CONFLICT") from error
    else:
        _write_new_text(service, expected_service)
        service_created = True
    previous_target: str | None = None
    if current.is_symlink():
        previous_target = os.readlink(current)
    elif current.exists():
        raise DeploymentError("HOLD_EXISTING_INSTALLATION_CONFLICT")
    if target.exists():
        if _release_sha256(target) != release_hash:
            raise DeploymentError("HOLD_EXISTING_RELEASE_VERSION_CONFLICT")
        resolved_current = str((current.parent / previous_target).resolve()) if previous_target else ""
        current_matches = resolved_current == str(target.resolve())
        if current_matches and not service_created:
            return {
                "status": "ALREADY_PASS",
                "reason_code": "RELEASE_ALREADY_INSTALLED_AND_HEALTHY",
                "agent_version": version,
                "release_sha256": release_hash,
                "current": str(target),
                "restart_required": False,
                "restart_performed": False,
                "health": "PASS",
            }
        if not current_matches:
            _atomic_symlink(target, current)
        return {
            "status": "PASS",
            "reason_code": "EXISTING_RELEASE_ACTIVATED",
            "agent_version": version,
            "release_sha256": release_hash,
            "current": str(target),
            "restart_required": bool(service_changed or service_created),
            "restart_performed": False,
            "health": "PASS",
        }
    stage = releases / f".{version}.stage"
    rollback_path = rollbacks / f"{version}.json"
    if stage.exists():
        raise DeploymentError("HOLD_STALE_RELEASE_STAGE")
    if rollback_path.exists():
        raise DeploymentError("HOLD_EXISTING_INSTALLATION_CONFLICT")
    try:
        shutil.copytree(release_dir, stage, copy_function=shutil.copy2)
        if _release_sha256(stage) != release_hash:
            raise DeploymentError("HOLD_RELEASE_HASH_MISMATCH")
        os.replace(stage, target)
        rollback = {
            "schema_version": "w7tp.small-agent.rollback/v0.1",
            "agent_version": version,
            "previous_current": previous_target,
            "promoted_release": str(target),
            "rollback_requires_owner_confirmation": True,
        }
        _write_new_text(rollback_path, _canonical_json(rollback) + "\n")
        _atomic_symlink(target, current)
        if not current.is_symlink() or current.resolve() != target.resolve():
            raise DeploymentError("HOLD_LOCAL_HEALTHCHECK_FAILED")
    except Exception as error:
        if stage.exists():
            shutil.rmtree(stage)
        if previous_target is not None and target.exists():
            try:
                _atomic_symlink(Path(previous_target), current)
            except DeploymentError:
                raise DeploymentError("HOLD_DEPLOYMENT_FAILED_ROLLBACK_FAILED") from error
        if isinstance(error, DeploymentError):
            raise error
        raise DeploymentError("HOLD_DEPLOYMENT_FAILED") from error
    return {
        "status": "PASS",
        "reason_code": "W7TP_SMALL_AGENT_INSTALLED",
        "agent_version": version,
        "release_sha256": release_hash,
        "current": str(target),
        "restart_required": bool(service_changed or service_created),
        "restart_performed": False,
        "health": "PASS",
    }


def _result(record: NodeRecord, status: str, reason: str, **fields: Any) -> NodeRecord:
    """Return a record with one deep-copied stable deployment result."""

    payload: dict[str, Any] = {"status": status, "reason_code": reason}
    payload.update(copy.deepcopy(fields))
    payload["result_hash"] = hashlib.sha256(
        _canonical_json(payload).encode("utf-8")
    ).hexdigest()
    return replace(record, deployment_result=payload)


def _bounded_command_stdout(outcome: CommandResult, reason: str) -> str:
    """Accept only a successful bounded UTF-8 command response without stderr."""

    if not isinstance(outcome.stdout, str) or not isinstance(outcome.stderr, str):
        raise DeploymentError(reason)
    try:
        output_size = len(outcome.stdout.encode("utf-8"))
    except UnicodeError as error:
        raise DeploymentError(reason) from error
    if (
        outcome.returncode != 0
        or outcome.stderr
        or output_size > MAX_ENTRYPOINT_OUTPUT_BYTES
    ):
        raise DeploymentError(reason)
    return outcome.stdout


def _post_install_runtime_checks(
    node: NodeRecord,
    release_dir: Path,
    executor: RemoteExecutor,
    entrypoint: str,
) -> dict[str, str]:
    """Verify the service and immutable runtime commands on one installed node."""

    manifest, _manifest_path = _release_manifest(Path(release_dir))
    expected = _manifest_runtime_identity(manifest)
    service = executor.run(
        node, ("systemctl", "--user", "is-active", "--quiet", SERVICE_NAME)
    )
    if service.returncode != 0:
        raise DeploymentError("HOLD_USER_SERVICE_HEALTHCHECK_FAILED")
    version = _bounded_command_stdout(
        executor.run(node, (entrypoint, "version")),
        "HOLD_RELEASE_RUNTIME_VERSION_FAILED",
    )
    _validate_version_output(version, expected)
    health = _bounded_command_stdout(
        executor.run(node, (entrypoint, "health")),
        "HOLD_RELEASE_RUNTIME_HEALTHCHECK_FAILED",
    )
    _validate_state_evidence_output(
        health,
        "PASS_W7TP_SMALL_AGENT_HEALTH",
        expected,
        HEALTH_REQUIRED_CHECKS,
        "HOLD_RELEASE_RUNTIME_HEALTHCHECK_FAILED",
    )
    self_test = _bounded_command_stdout(
        executor.run(node, (entrypoint, "self-test")),
        "HOLD_RELEASE_RUNTIME_SELF_TEST_FAILED",
    )
    _validate_state_evidence_output(
        self_test,
        "PASS_W7TP_SMALL_AGENT_SELF_TEST",
        expected,
        SELF_TEST_REQUIRED_CHECKS,
        "HOLD_RELEASE_RUNTIME_SELF_TEST_FAILED",
    )
    return {
        "service_health": "PASS",
        "version": "PASS",
        "health": "PASS",
        "self_test": "PASS",
        **expected,
    }


def _remote_deploy(
    node: NodeRecord,
    release_dir: Path,
    executor: RemoteExecutor,
    service_changed: bool,
) -> NodeRecord:
    """Perform one bounded remote user-level installation attempt."""

    preflight_release_runtime_entrypoint(release_dir)
    manifest, _manifest_path = _release_manifest(release_dir)
    version = manifest["agent_version"]
    if node.agent_version and node.agent_version != version:
        return _result(node, "HOLD", "HOLD_RELEASE_VERSION_MISMATCH")
    base = "~/.local/share/w7tp-small-agent"
    target = f"{base}/releases/{version}"
    stage = f"{base}/releases/.{version}.stage"
    current = f"{base}/current"
    next_link = f"{base}/current.next"
    service_path = "~/.config/systemd/user/w7tp-small-agent.service"
    existing = executor.run(node, ("test", "-e", target))
    if existing.returncode == 0:
        try:
            checks = _post_install_runtime_checks(
                node,
                release_dir,
                executor,
                INSTALLED_RUNTIME_ENTRYPOINT,
            )
        except DeploymentError as error:
            return _result(node, "HOLD", error.reason_code)
        return _result(
            node,
            "ALREADY_PASS",
            "RELEASE_ALREADY_INSTALLED_AND_HEALTHY",
            **checks,
        )
    previous = executor.run(node, ("readlink", current))
    previous_target = previous.stdout.strip() if previous.returncode == 0 else ""
    commands = (
        ("test", "!", "-e", stage),
        ("install", "-d", f"{base}/releases", f"{base}/rollback"),
        ("install", "-d", "~/.config/systemd/user"),
    )
    for command in commands:
        outcome = executor.run(node, command)
        if outcome.returncode != 0:
            return _result(node, "HOLD", "HOLD_DEPLOYMENT_COMMAND_FAILED")
    transfer_method = getattr(executor, "transfer_release", None)
    if not callable(transfer_method):
        return _result(node, "HOLD", "HOLD_RELEASE_TRANSFER_UNSUPPORTED")
    transferred = transfer_method(node, release_dir, stage)
    if not isinstance(transferred, CommandResult) or transferred.returncode != 0:
        return _result(node, "HOLD", "HOLD_RELEASE_TRANSFER_FAILED")
    for relative, expected_hash in _release_file_hashes(release_dir):
        verified = executor.run(node, ("sha256sum", f"{stage}/{relative}"))
        if (
            verified.returncode != 0
            or verified.stdout.split(maxsplit=1)[0] != expected_hash
        ):
            return _result(node, "HOLD", "HOLD_RELEASE_HASH_MISMATCH")
    if executor.run(node, ("mv", "-T", stage, target)).returncode != 0:
        return _result(node, "HOLD", "HOLD_ATOMIC_RELEASE_PROMOTION_FAILED")
    service_exists = executor.run(node, ("test", "-e", service_path))
    if service_exists.returncode == 0:
        expected_service_hash = hashlib.sha256(
            _service_content().encode("utf-8")
        ).hexdigest()
        actual_service_hash = executor.run(node, ("sha256sum", service_path))
        if (
            actual_service_hash.returncode != 0
            or actual_service_hash.stdout.split(maxsplit=1)[0] != expected_service_hash
        ):
            return _result(node, "HOLD", "HOLD_EXISTING_USER_SERVICE_CONFLICT")
    else:
        outcome = executor.run(
            node,
            ("tee", service_path),
            input_text=_service_content(),
        )
        if outcome.returncode != 0:
            return _result(node, "HOLD", "HOLD_USER_SERVICE_WRITE_FAILED")
    rollback = _canonical_json(
        {
            "schema_version": "w7tp.small-agent.rollback/v0.1",
            "agent_version": version,
            "previous_current": previous_target or None,
            "promoted_release": target,
            "rollback_requires_owner_confirmation": True,
        }
    ) + "\n"
    if executor.run(
        node,
        ("tee", f"{base}/rollback/{version}.json"),
        input_text=rollback,
    ).returncode != 0:
        return _result(node, "HOLD", "HOLD_ROLLBACK_MANIFEST_WRITE_FAILED")
    switch_commands = (("ln", "-s", target, next_link), ("mv", "-Tf", next_link, current))
    for command in switch_commands:
        if executor.run(node, command).returncode != 0:
            return _result(node, "HOLD", "HOLD_ATOMIC_CURRENT_UPDATE_FAILED")
    if service_changed:
        if executor.run(
            node, ("systemctl", "--user", "daemon-reload")
        ).returncode != 0 or executor.run(
            node, ("systemctl", "--user", "restart", SERVICE_NAME)
        ).returncode != 0:
            return _remote_rollback(node, executor, previous_target, current, next_link)
    health = executor.run(
        node, ("systemctl", "--user", "is-active", "--quiet", SERVICE_NAME)
    )
    if health.returncode != 0:
        return _remote_rollback(node, executor, previous_target, current, next_link)
    try:
        checks = _post_install_runtime_checks(
            node,
            release_dir,
            executor,
            INSTALLED_RUNTIME_ENTRYPOINT,
        )
    except DeploymentError as error:
        return _remote_rollback(
            node,
            executor,
            previous_target,
            current,
            next_link,
            failure_reason=error.reason_code,
        )
    return _result(
        node,
        "PASS",
        "W7TP_SMALL_AGENT_INSTALLED",
        agent_version=version,
        restart_performed=bool(service_changed),
        **checks,
    )


def _remote_rollback(
    node: NodeRecord,
    executor: RemoteExecutor,
    previous_target: str,
    current: str,
    next_link: str,
    failure_reason: str = "HOLD_DEPLOYMENT_FAILED_ROLLED_BACK",
) -> NodeRecord:
    """Attempt one current-link rollback and verify user-service health."""

    if not previous_target:
        if failure_reason != "HOLD_DEPLOYMENT_FAILED_ROLLED_BACK":
            return _result(
                node,
                "HOLD",
                failure_reason,
                rollback_status="NOT_AVAILABLE_NO_PREVIOUS_RELEASE",
            )
        return _result(node, "HOLD", "HOLD_DEPLOYMENT_FAILED_NO_ROLLBACK_TARGET")
    for command in (
        ("ln", "-s", previous_target, next_link),
        ("mv", "-Tf", next_link, current),
        ("systemctl", "--user", "restart", SERVICE_NAME),
        ("systemctl", "--user", "is-active", "--quiet", SERVICE_NAME),
    ):
        if executor.run(node, command).returncode != 0:
            return _result(node, "HOLD", "HOLD_DEPLOYMENT_FAILED_ROLLBACK_FAILED")
    return _result(
        node,
        "HOLD",
        failure_reason,
        rollback_status="PASS",
        service_health="PASS",
    )


def _local_rollback(
    node: NodeRecord,
    executor: RemoteExecutor,
    install_home: Path,
    version: str,
    failure_reason: str = "HOLD_DEPLOYMENT_FAILED_ROLLED_BACK",
) -> NodeRecord:
    """Restore the previous local current link and verify the user service."""

    rollback_path = (
        Path(install_home)
        / INSTALL_RELATIVE_ROOT
        / "rollback"
        / f"{version}.json"
    )
    try:
        rollback = _load_json(rollback_path)
    except DeploymentError:
        return _result(node, "HOLD", "HOLD_DEPLOYMENT_FAILED_NO_ROLLBACK_TARGET")
    previous = rollback.get("previous_current") if isinstance(rollback, dict) else None
    if not isinstance(previous, str) or not previous:
        if failure_reason != "HOLD_DEPLOYMENT_FAILED_ROLLED_BACK":
            return _result(
                node,
                "HOLD",
                failure_reason,
                rollback_status="NOT_AVAILABLE_NO_PREVIOUS_RELEASE",
            )
        return _result(node, "HOLD", "HOLD_DEPLOYMENT_FAILED_NO_ROLLBACK_TARGET")
    current = Path(install_home) / INSTALL_RELATIVE_ROOT / "current"
    try:
        _atomic_symlink(Path(previous), current)
    except DeploymentError:
        return _result(node, "HOLD", "HOLD_DEPLOYMENT_FAILED_ROLLBACK_FAILED")
    for command in (
        ("systemctl", "--user", "restart", SERVICE_NAME),
        ("systemctl", "--user", "is-active", "--quiet", SERVICE_NAME),
    ):
        if executor.run(node, command).returncode != 0:
            return _result(node, "HOLD", "HOLD_DEPLOYMENT_FAILED_ROLLBACK_FAILED")
    return _result(
        node,
        "HOLD",
        failure_reason,
        rollback_status="PASS",
        service_health="PASS",
    )


def deploy_nodes(
    nodes: Sequence[NodeRecord],
    release_dir: Path,
    executor: RemoteExecutor,
    *,
    install_home: Path | None = None,
    service_changed: bool = True,
) -> tuple[NodeRecord, ...]:
    """Attempt every eligible node once, continuing after stable per-node failures."""

    release_dir = Path(release_dir)
    preflight_reason: str | None = None
    if any(
        isinstance(node.deployment_eligibility, Mapping)
        and node.deployment_eligibility.get("status") == "ELIGIBLE"
        for node in nodes
    ):
        try:
            preflight_release_runtime_entrypoint(release_dir)
        except DeploymentError as error:
            preflight_reason = error.reason_code
    attempted: set[str] = set()
    results: list[NodeRecord] = []
    for node in nodes:
        if node.node_id in attempted:
            results.append(_result(node, "HOLD", "HOLD_DUPLICATE_FORMAL_NODE_ID"))
            continue
        attempted.add(node.node_id)
        if node.alias_of:
            results.append(_result(node, "HOLD", "HOLD_ALIAS_DEDUPLICATED"))
            continue
        eligibility = node.deployment_eligibility
        eligible = isinstance(eligibility, Mapping) and eligibility.get("status") == "ELIGIBLE"
        if not eligible:
            reason = (
                eligibility.get("reason_code")
                if isinstance(eligibility, Mapping)
                else "HOLD_FORMAL_NODE_OR_AUTHORITY_UNRESOLVED"
            )
            results.append(_result(node, "HOLD", str(reason)))
            continue
        if preflight_reason is not None:
            results.append(_result(node, "HOLD", preflight_reason))
            continue
        method = (node.connection_method or "").upper()
        try:
            if method in SUPPORTED_LOCAL_METHODS:
                if install_home is None:
                    results.append(_result(node, "HOLD", "HOLD_LOCAL_INSTALL_HOME_REQUIRED"))
                    continue
                installed = install_linux_release(
                    install_home,
                    release_dir,
                    service_changed=service_changed,
                )
                if installed.get("restart_required"):
                    restart = executor.run(
                        node, ("systemctl", "--user", "daemon-reload")
                    )
                    if restart.returncode == 0:
                        restart = executor.run(
                            node, ("systemctl", "--user", "restart", SERVICE_NAME)
                        )
                    if restart.returncode != 0:
                        results.append(
                            _local_rollback(
                                node,
                                executor,
                                install_home,
                                str(installed.get("agent_version", "")),
                            )
                        )
                        continue
                    health = executor.run(
                        node,
                        ("systemctl", "--user", "is-active", "--quiet", SERVICE_NAME),
                    )
                    if health.returncode != 0:
                        results.append(
                            _local_rollback(
                                node,
                                executor,
                                install_home,
                                str(installed.get("agent_version", "")),
                            )
                        )
                        continue
                    installed["restart_performed"] = True
                installed_entrypoint = str(
                    Path(install_home)
                    / INSTALL_RELATIVE_ROOT
                    / "current"
                    / RELEASE_RUNTIME_ENTRYPOINT
                )
                try:
                    checks = _post_install_runtime_checks(
                        node,
                        release_dir,
                        executor,
                        installed_entrypoint,
                    )
                except DeploymentError as error:
                    if installed.get("status") == "ALREADY_PASS":
                        results.append(_result(node, "HOLD", error.reason_code))
                    else:
                        results.append(
                            _local_rollback(
                                node,
                                executor,
                                install_home,
                                str(installed.get("agent_version", "")),
                                failure_reason=error.reason_code,
                            )
                        )
                    continue
                installed.update(checks)
                results.append(replace(node, deployment_result=copy.deepcopy(installed)))
            elif method == "SSH":
                results.append(_remote_deploy(node, release_dir, executor, service_changed))
            else:
                results.append(_result(node, "HOLD", "HOLD_UNSUPPORTED_DEPLOYMENT_TRANSPORT"))
        except DeploymentError as error:
            results.append(_result(node, "HOLD", error.reason_code))
        except (OSError, ValueError, TypeError):
            results.append(_result(node, "HOLD", "HOLD_DEPLOYMENT_FAILED"))
    return tuple(results)


def _normalized_results(records: Sequence[NodeRecord]) -> list[dict[str, Any]]:
    """Render results without authority, address, or observation-domain payloads."""

    return sorted(
        (
            {
                "node_id": record.node_id,
                "kind": record.kind,
                "agent_version": record.agent_version,
                "deployment_eligibility": copy.deepcopy(record.deployment_eligibility),
                "deployment_result": copy.deepcopy(record.deployment_result),
            }
            for record in records
        ),
        key=lambda item: item["node_id"],
    )


def _difference_paths(left: Any, right: Any, prefix: str = "$") -> list[str]:
    """Return stable JSON-style paths for two deterministic result values."""

    if type(left) is not type(right):
        return [prefix]
    if isinstance(left, dict):
        differences: list[str] = []
        for key in sorted(set(left) | set(right)):
            path = f"{prefix}.{key}"
            if key not in left or key not in right:
                differences.append(path)
            else:
                differences.extend(_difference_paths(left[key], right[key], path))
        return differences
    if isinstance(left, list):
        differences = []
        if len(left) != len(right):
            differences.append(f"{prefix}.length")
        for index, values in enumerate(zip(left, right)):
            differences.extend(_difference_paths(values[0], values[1], f"{prefix}[{index}]"))
        return differences
    return [] if left == right else [prefix]


def compare_node_results(
    results: Sequence[NodeRecord],
    other: Sequence[NodeRecord] | None = None,
) -> dict[str, Any]:
    """Compare deterministic node results, or validate one replay snapshot against itself."""

    left = _normalized_results(results)
    right = _normalized_results(results if other is None else other)
    differences = _difference_paths(left, right)
    return {
        "status": "MATCH" if not differences else "MISMATCH",
        "difference_paths": differences,
        "result_hash": hashlib.sha256(_canonical_json(left).encode("utf-8")).hexdigest(),
    }


def _record_for_output(record: NodeRecord) -> dict[str, Any]:
    """Render a node without hostname, address, authority, or domain payloads."""

    return {
        "node_id": record.node_id,
        "kind": record.kind,
        "connection_method": record.connection_method,
        "agent_version": record.agent_version,
        "deployment_eligibility": copy.deepcopy(record.deployment_eligibility),
        "deployment_result": copy.deepcopy(record.deployment_result),
    }


def _print_records(state: str, records: Sequence[NodeRecord]) -> None:
    """Print one deterministic CLI response without sensitive formal metadata."""

    print(f"STATE={state}")
    print(f"RUN_ID={RUN_ID}")
    print(f"NODE_COUNT={len(records)}")
    print(f"ELIGIBLE_COUNT={sum(1 for item in records if isinstance(item.deployment_eligibility, Mapping) and item.deployment_eligibility.get('status') == 'ELIGIBLE')}")
    print(f"RESULTS={_canonical_json([_record_for_output(item) for item in records])}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run resolve, deploy, or deterministic equivalence from the command line."""

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    resolve_parser = subparsers.add_parser(
        "resolve", help="Resolve formal nodes without deployment"
    )
    resolve_parser.add_argument("--authority-registry", type=Path)
    deploy_parser = subparsers.add_parser("deploy", help="Deploy only formally eligible nodes")
    deploy_parser.add_argument("--release-dir", type=Path, required=True)
    deploy_parser.add_argument("--authority-registry", type=Path)
    deploy_parser.add_argument("--owner-confirmation", default="")
    deploy_parser.add_argument("--remote-node-write", default="")
    deploy_parser.add_argument("--service-change", default="")
    deploy_parser.add_argument("--node-id", choices=FORMAL_NODE_IDS)
    equivalence_parser = subparsers.add_parser(
        "equivalence", help="Replay formal resolution and compare deterministic results"
    )
    equivalence_parser.add_argument("--release-dir", type=Path, required=False)
    equivalence_parser.add_argument("--authority-registry", type=Path)
    args = parser.parse_args(argv)
    try:
        nodes = resolve_formal_nodes(ROOT, args.authority_registry)
        if args.command == "resolve":
            _print_records("PASS_FORMAL_NODE_RESOLUTION", nodes)
            return 0
        if args.command == "deploy":
            if args.node_id is not None:
                nodes = tuple(node for node in nodes if node.node_id == args.node_id)
            eligible = [
                node
                for node in nodes
                if isinstance(node.deployment_eligibility, Mapping)
                and node.deployment_eligibility.get("status") == "ELIGIBLE"
            ]
            if not eligible:
                _print_records("HOLD_FORMAL_NODE_OR_AUTHORITY_UNRESOLVED", nodes)
                return 2
            authorization_gates = (
                (args.owner_confirmation, "HOLD_OWNER_CONFIRMATION_REQUIRED"),
                (args.remote_node_write, "HOLD_REMOTE_NODE_WRITE_NOT_AUTHORIZED"),
                (args.service_change, "HOLD_SERVICE_CHANGE_NOT_AUTHORIZED"),
            )
            for value, reason_code in authorization_gates:
                if value != "YES":
                    _print_records(reason_code, nodes)
                    return 2
            methods = {(node.connection_method or "").upper() for node in eligible}
            if methods <= SUPPORTED_LOCAL_METHODS:
                executor: RemoteExecutor = LocalLinuxExecutor()
            elif methods == {"SSH"}:
                executor = SSHExecutor()
            elif methods <= SUPPORTED_LOCAL_METHODS | SUPPORTED_REMOTE_METHODS:
                executor = ConnectionRoutingExecutor()
            else:
                _print_records("HOLD_UNSUPPORTED_DEPLOYMENT_TRANSPORT", nodes)
                return 2
            install_home = (
                Path.home() if methods & SUPPORTED_LOCAL_METHODS else None
            )
            deployed = deploy_nodes(
                nodes,
                args.release_dir,
                executor,
                install_home=install_home,
            )
            eligible_ids = {item.node_id for item in eligible}
            eligible_results = [
                item.deployment_result
                for item in deployed
                if item.node_id in eligible_ids
            ]
            state = (
                "PASS_W7TP_SMALL_AGENT_DEPLOYMENT"
                if eligible_results
                and all(
                    isinstance(item, Mapping)
                    and item.get("status") in {"PASS", "ALREADY_PASS"}
                    for item in eligible_results
                )
                else "HOLD_W7TP_SMALL_AGENT_DEPLOYMENT"
            )
            _print_records(state, deployed)
            return 0 if state.startswith("PASS") else 2
        comparison = compare_node_results(
            nodes,
            resolve_formal_nodes(ROOT, args.authority_registry),
        )
        print(
            "STATE="
            + (
                "PASS_W7TP_SMALL_AGENT_NODE_EQUIVALENCE"
                if comparison["status"] == "MATCH"
                else "HOLD_W7TP_SMALL_AGENT_NODE_EQUIVALENCE"
            )
        )
        print(f"RUN_ID={RUN_ID}")
        print(f"EQUIVALENCE={comparison['status']}")
        print(f"RESULT_HASH={comparison['result_hash']}")
        return 0 if comparison["status"] == "MATCH" else 2
    except DeploymentError as error:
        print(f"STATE={error.reason_code}")
        print(f"RUN_ID={RUN_ID}")
        print(f"REASON_CODE={error.reason_code}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
