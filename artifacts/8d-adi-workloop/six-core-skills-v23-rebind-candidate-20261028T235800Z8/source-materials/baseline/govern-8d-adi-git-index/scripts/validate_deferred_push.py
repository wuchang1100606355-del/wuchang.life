#!/usr/bin/env python3
"""Validate a durable deferred Git push obligation without mutating Git."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import pwd
import grp
import re
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


HEX_OID = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
STATES = {
    "PUSH_OBLIGATION_OPEN",
    "BLOCKED_REPAIRING",
    "READY_FOR_AUTHORIZATION",
    "READY_TO_PUSH",
    "PUSHED_VERIFIED",
    "CANCELLED_BY_FOUNDER",
    "SUPERSEDED",
}
ROUTES = {"SAFE_PUSH_CANDIDATE", "REVIEW_REQUIRED", "HOLD_PROTECTED_GIT_EFFECT"}
SCHEDULER_STATES = {"ACTIVE_DURABLE_SCHEDULER", "HANDOFF_RESUME_REQUIRED", "TERMINAL"}
TERMINAL_STATES = {"PUSHED_VERIFIED", "CANCELLED_BY_FOUNDER", "SUPERSEDED"}
UNRESOLVED = "UNKNOWN_UNVERIFIED"
CURRENT_SCHEMA = "w7tp-deferred-git-push-obligation/1.2"
LEGACY_SCHEMAS = {
    "w7tp-deferred-git-push-obligation/1.0",
    "w7tp-deferred-git-push-obligation/1.1",
}
EXECUTOR_SKILL_REF = "$complete-deferred-git-push"
EXECUTOR_SKILL_VERSION = "1.0.0"
EXECUTOR_INPUT_CONTRACT = "w7tp-deferred-git-push-request"
EXECUTOR_INPUT_CONTRACT_VERSION = "1.0"
HANDOFF_HASH_CONTRACT = "SHA256_CANONICAL_JSON_EXCLUDING_EXECUTOR_HANDOFF_SHA256_V1"
HANDOFF_RESPONSIBILITIES = [
    "E4_SINGLE_REF_FAST_FORWARD_EXECUTION",
    "TERMINAL_AUTHORITATIVE_RECHECK",
    "REMOTE_EXACT_OID_READBACK_CLOSURE",
]
HANDOFF_STATES = {
    "WAITING_EXACT_TARGET",
    "READY_FOR_E4_VALIDATION",
    "TERMINAL_AUTHORITATIVE_RECHECK_REQUIRED",
    "NO_E4_ACTION_TERMINAL",
}
EXECUTOR_TICKET_ID = re.compile(r"^dgp-[0-9a-f]{64}$")
EXECUTOR_REQUEST_SCHEMA = "w7tp-deferred-git-push-request/1.0"
EXECUTOR_EVENT_SCHEMA = "w7tp-deferred-git-push-event/1.0"
EXECUTOR_RECEIPT_SCHEMA = "w7tp-deferred-git-push-readback-receipt/1.0"
EXECUTOR_HASH_CONTRACT = "SHA256_CANONICAL_JSON_EXCLUDING_OWN_HASH_V1"
EXECUTOR_SCOPE_SCHEMA = "w7tp-deferred-git-push-execution-scope/1.0"
TOTAL_FIELD_RECEIPT_SCHEMA = "w7tp-total-field-e4-git-push-decision-receipt/1.0"
TOTAL_FIELD_RECEIVER = "TOTAL_FIELD_8D_ADI_GIT_INDEX_RECEIVER"
TOTAL_FIELD_DECISION = "ALLOW_E4_SINGLE_REF_FAST_FORWARD_PUSH"
TOTAL_FIELD_ROLLBACK_POLICY = "NO_AUTOMATIC_REMOTE_REWRITE_FOUNDER_GOVERNED_SUCCESSOR_ONLY"
TOTAL_FIELD_STOP_CONDITIONS = [
    "AUTHORIZATION_OR_DECISION_EXPIRED",
    "ENDPOINT_OR_REPOSITORY_DRIFT",
    "REMOTE_OLD_OID_MISMATCH",
    "SOURCE_OR_PROTECTED_STATE_DRIFT",
    "UNREVIEWED_HOOK_LFS_CI_OR_DEPLOY_EFFECT",
]
EXECUTOR_QUEUE_MARKER_NAME = ".w7tp-deferred-push-queue-v1"
EXECUTOR_QUEUE_MARKER_BYTES = b"w7tp-deferred-push-queue/1.0\n"
EXECUTOR_INITIAL_EVENT_NAME = "00000000000000000001.json"
EXECUTOR_TRUST_CONFIG_SCHEMA = "w7tp-e2-executor-queue-trust-config/1.1"
EXECUTOR_TRUST_CONFIG_HASH_CONTRACT = "SHA256_CANONICAL_JSON_EXCLUDING_CONFIG_SHA256_V1"
EXECUTOR_OBLIGATION_ACK_SCHEMA = "w7tp-e2-deferred-push-obligation-queue-ack/1.0"
EXECUTOR_OBLIGATION_ACK_KIND = "E2_DEFERRED_PUSH_OBLIGATION_ENQUEUED"
EXECUTOR_OBLIGATION_ACK_STATE = "ACKNOWLEDGED_IMMUTABLE"
EXECUTOR_OBLIGATION_ACK_DIR = "e2-obligation-acks"
EXECUTOR_ORIGIN_ENVELOPE_SCHEMA = "w7tp-e2-to-e4-origin-envelope/1.0"
EXECUTOR_QUEUE_DIRECTORY_MODES = {0o750}
EXECUTOR_QUEUE_FILE_MODES = {0o440}
PROC_SELF_STATUS = Path("/proc/self/status")
PROC_THREAD_SELF_STATUS = Path("/proc/thread-self/status")
CAPABILITY_NAMES = {
    0: "CAP_CHOWN",
    1: "CAP_DAC_OVERRIDE",
    3: "CAP_FOWNER",
    6: "CAP_SETGID",
    7: "CAP_SETUID",
    21: "CAP_SYS_ADMIN",
}
EXECUTOR_TRUST_CONFIG_KEYS = {
    "schema_version",
    "state_root_parent_realpath",
    "state_root_parent_device",
    "state_root_parent_inode",
    "state_root_parent_mode",
    "state_root_basename",
    "state_root_realpath",
    "state_root_device",
    "state_root_inode",
    "state_root_mode",
    "expected_nonroot_owner_uid",
    "expected_nonroot_owner_username",
    "expected_validator_uid",
    "expected_validator_username",
    "expected_reader_group_gid",
    "expected_reader_group_name",
    "queue_marker",
    "executor_contract",
    "activation",
    "hash_contract",
    "config_sha256",
}
EXECUTOR_TRUST_MARKER_KEYS = {
    "relative_path",
    "bytes_base64",
    "sha256",
}
EXECUTOR_TRUST_CONTRACT_KEYS = {
    "executor_skill_ref",
    "executor_skill_version",
    "request_schema",
    "event_schema",
    "initial_event_kind",
}
EXECUTOR_TRUST_ACTIVATION_KEYS = {
    "activation_ref",
    "valid_from",
    "expires_at",
    "activation_receipt_ref",
    "activation_receipt_sha256",
}
EXECUTOR_OBLIGATION_ACK_KEYS = {
    "schema_version",
    "hash_contract",
    "ack_kind",
    "ack_state",
    "obligation_id",
    "obligation_schema_version",
    "obligation_core_sha256",
    "executor_handoff_payload_sha256",
    "executor_ticket_id",
    "executor_request_ref",
    "executor_request_sha256",
    "executor_initial_event_ref",
    "executor_initial_event_sha256",
    "queue_store_idempotency_key",
    "queue_trust_config_sha256",
    "founder_intent_ref",
    "founder_intent_sha256",
    "repository_root",
    "repository_fingerprint_sha256",
    "identity_root_ref",
    "member_ref",
    "seat_binding_ref",
    "receiver_ref",
    "test_receipt_ref",
    "test_receipt_sha256",
    "authorization_scope_sha256",
    "effect_scope_sha256",
    "change_set_sha256",
    "acknowledged_at",
    "ack_sha256",
}
EXECUTOR_REQUEST_KEYS = {
    "schema_version",
    "origin_intent_sha256",
    "responsible_agent_ref",
    "repository",
    "remote",
    "git",
    "authorization",
    "effects",
    "supersedes_ticket_id",
    "scheduler_state",
    "ticket_id",
    "obligation_id",
    "idempotency_key",
    "executable_envelope_sha256",
    "created_at",
    "hash_contract",
    "request_sha256",
}
EXECUTOR_EVENT_KEYS = {
    "schema_version",
    "hash_contract",
    "ticket_id",
    "sequence",
    "occurred_at",
    "kind",
    "state",
    "next_attempt_at",
    "prev_event_hash",
    "details",
    "event_sha256",
}
EXECUTOR_REPOSITORY_KEYS = {
    "root",
    "git_common_dir",
    "fingerprint_sha256",
    "object_format",
    "local_config_key_count",
    "local_config_keys_sha256",
    "local_config_values_sha256",
}
EXECUTOR_REMOTE_KEYS = {"name", "endpoint_fingerprint_sha256", "file_repository_identity"}
EXECUTOR_GIT_KEYS = {
    "source_state",
    "source_commit_oid",
    "source_tree_oid",
    "source_parent_oids",
    "reachable_object_closure_sha256",
    "reachable_object_count",
    "expected_remote_old_oid",
    "changed_paths",
    "change_manifest",
    "change_scope_sha256",
    "commit_range_oids",
    "commit_range_sha256",
    "causal_groups",
    "causal_group_changed_paths",
    "causal_group_dependency_order",
    "causal_group_combined_sha256",
    "authority_sensitive_paths",
    "target_ref",
    "refspec",
    "bounded_paths",
    "fast_forward_only",
    "force_allowed",
    "non_fast_forward_allowed",
    "exact_server_cas_required",
    "server_cas_expected_old_oid",
    "delete_allowed",
    "tags_allowed",
    "multi_ref_allowed",
}
EXECUTOR_AUTHORIZATION_KEYS = {
    "ref",
    "expires_at",
    "required_scope_sha256",
    "total_field_decision_ref",
    "total_field_decision_expires_at",
    "total_field_scope_sha256",
    "decision_receipt",
    "receiver_activation",
    "single_use",
}
EXECUTOR_EFFECT_KEYS = {"ci_or_deploy", "hook", "lfs", "submodule_recursive_push", "tags"}
EXECUTOR_DECISION_RECEIPT_KEYS = {
    "schema_version",
    "receiver",
    "decision",
    "decision_ref",
    "scope_sha256",
    "identity_root_ref",
    "seat_ref",
    "member_ref",
    "issued_at",
    "not_before",
    "expires_at",
    "single_use_nonce",
    "rollback_policy",
    "stop_conditions",
    "hash_contract",
    "receipt_sha256",
}
EXECUTOR_ACTIVATION_KEYS = {
    "config_path",
    "config_sha256",
    "activation_ref",
    "receiver",
    "protocol",
    "adapter_realpath",
    "adapter_sha256",
    "allowed_executor_uid",
    "allowed_executor_username",
}
EXECUTOR_READBACK_RECEIPT_KEYS = {
    "schema_version",
    "hash_contract",
    "ticket_id",
    "request_sha256",
    "verified_at",
    "verification",
    "remote_endpoint_fingerprint_sha256",
    "target_ref",
    "expected_remote_old_oid",
    "preflight_observed_oid",
    "intended_source_commit_oid",
    "observed_remote_oid",
    "source_tree_oid",
    "reachable_object_closure_sha256",
    "change_scope_sha256",
    "change_manifest",
    "commit_range_sha256",
    "causal_groups",
    "causal_group_combined_sha256",
    "authority_sensitive_paths",
    "total_field_decision_ref",
    "total_field_decision_receipt_sha256",
    "total_field_scope_sha256",
    "total_field_single_use_nonce_sha256",
    "receiver_adapter_sha256",
    "receiver_reservation_ack_sha256",
    "receiver_final_validation_ack_sha256",
    "receiver_consume_ack",
    "delivery_proof_sha256",
    "server_compare_and_swap",
    "changed_paths",
    "push_invoked",
    "uncertain_outcome_reconciled",
    "protected_state_before",
    "protected_state_after",
    "protected_state_comparison",
    "dirty_worktree_unchanged",
    "protected_state_repair_state",
    "remote_exact_oid_match",
    "receipt_sha256",
}

TOP_LEVEL_KEYS = {
    "schema_version",
    "obligation_id",
    "founder_intent_ref",
    "founder_intent_sha256",
    "responsible_agent_ref",
    "workloop_ref",
    "identity_root_ref",
    "member_ref",
    "seat_binding_ref",
    "receiver_ref",
    "state",
    "total_field_route",
    "repository",
    "source_closure",
    "change_scope_state",
    "changes",
    "change_set_sha256",
    "queue_store",
    "blocker",
    "schedule",
    "authorization",
    "safety",
    "executor_handoff",
    "closure",
}
OBJECT_KEYS = {
    "repository": {
        "repo_ref",
        "repository_fingerprint_sha256",
        "remote_name",
        "remote_endpoint_sha256",
        "target_ref",
        "source_oid",
        "expected_remote_old_oid",
        "object_format",
        "refspec",
    },
    "source_closure": {
        "commit_oid",
        "parent_oid",
        "tree_oid",
        "reachable_objects_sha256",
        "reviewed_history_sha256",
        "test_receipt_ref",
        "test_receipt_sha256",
    },
    "queue_store": {
        "store_ref",
        "idempotency_key",
        "append_only_ack_ref",
        "append_only_ack_sha256",
        "outside_target_repo",
    },
    "blocker": {"code", "evidence_ref", "repair_plan", "automation_possible"},
    "schedule": {
        "scheduler_state",
        "scheduler_job_ref",
        "created_at",
        "next_attempt_at",
        "deadline_at",
        "resume_trigger",
        "attempt_count",
        "max_auto_attempts",
        "executor_lease_ref",
        "executor_lease_expires_at",
    },
    "authorization": {
        "required",
        "authorization_ref",
        "authorization_expires_at",
        "decision_ref",
        "decision_receipt_sha256",
        "decision_expires_at",
        "scope_sha256",
    },
    "safety": {
        "fast_forward_only",
        "force_push",
        "delete_ref",
        "push_tags",
        "multiple_refs",
        "recurse_submodules",
        "history_rewrite",
        "include_unrelated_dirty_files",
        "remote_readback_required",
        "push_effects",
        "stop_conditions",
        "rollback",
    },
    "push_effects": {"pre_push_hooks", "git_lfs", "ci_webhook_deploy"},
    "executor_handoff": {
        "executor_skill_ref",
        "executor_skill_version",
        "input_contract",
        "input_contract_version",
        "obligation_id",
        "executor_ticket_id",
        "executor_request_sha256",
        "executor_queue_ack_ref",
        "executor_queue_ack_sha256",
        "handoff_state",
        "activation_state",
        "responsibilities",
        "hash_contract",
        "handoff_sha256",
    },
}


def _string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _parse_canonical_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return parsed


def _timestamp(value: Any) -> bool:
    return _parse_canonical_time(value) is not None


def _safe_path(value: Any) -> bool:
    if (
        not _string(value)
        or "\\" in value
        or "\x00" in value
        or "\n" in value
        or "\r" in value
        or value.endswith("/")
    ):
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and path.as_posix() == value
        and all(part not in {"", ".", ".."} and part.lower() != ".git" for part in path.parts)
    )


def _target_ref(value: Any) -> bool:
    if not isinstance(value, str) or not value.startswith("refs/heads/") or value == "refs/heads/":
        return False
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        return False
    forbidden = ("..", "@{", "\\", " ", "~", "^", ":", "?", "*", "[")
    components = value.split("/")
    return not (
        any(token in value for token in forbidden)
        or value.endswith(("/", "."))
        or any(
            not component or component.startswith(".") or component.endswith(".lock")
            for component in components
        )
    )


def _contains_secret_shape(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in {"password", "token", "private_key", "access_token", "secret_value"}:
                return True
            if _contains_secret_shape(item):
                return True
    elif isinstance(value, list):
        return any(_contains_secret_shape(item) for item in value)
    elif isinstance(value, str) and "-----BEGIN PRIVATE KEY-----" in value:
        return True
    return False


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


class _DuplicateKey(ValueError):
    pass


def _closed_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise _DuplicateKey(key)
        value[key] = item
    return value


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-JSON constant: {value}")


def _decode_json(raw: bytes) -> Any:
    return json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_closed_object_pairs,
        parse_constant=_reject_json_constant,
    )


def _hash_without(value: dict[str, Any], field: str) -> str:
    clone = dict(value)
    clone.pop(field, None)
    return hashlib.sha256(_canonical_json(clone)).hexdigest()


class _ExternalEvidenceError(ValueError):
    """One credential-free reason external executor evidence cannot be trusted."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _safe_int(value: Any, minimum: int = 0) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def _require_external_keys(value: Any, expected: set[str], code: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise _ExternalEvidenceError(code)
    return value


def _open_private_directory(
    path: Path,
    code: str,
    *,
    expected_owner: int | None = None,
) -> tuple[int, int]:
    """Open the exact directory inode; return its fd and trusted owner uid."""
    try:
        if not path.is_absolute() or path != path.resolve(strict=True):
            raise _ExternalEvidenceError(code)
        descriptor = os.open(
            path,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
    except _ExternalEvidenceError:
        raise
    except (OSError, RuntimeError) as exc:
        raise _ExternalEvidenceError(code) from exc
    try:
        info = os.fstat(descriptor)
        permitted_owner = info.st_uid in {0, os.geteuid()} if expected_owner is None else info.st_uid == expected_owner
        if (
            not stat.S_ISDIR(info.st_mode)
            or not permitted_owner
            or stat.S_IMODE(info.st_mode) != 0o700
        ):
            raise _ExternalEvidenceError(code)
        return descriptor, info.st_uid
    except BaseException:
        os.close(descriptor)
        raise


def _open_private_directory_at(
    parent_fd: int,
    name: str,
    owner: int,
    reader_gid: int,
    code: str,
    *,
    allowed_modes: set[int] | None = None,
) -> int:
    if not re.fullmatch(r"[A-Za-z0-9._-]+", name):
        raise _ExternalEvidenceError(code)
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
    except OSError as exc:
        raise _ExternalEvidenceError(code) from exc
    try:
        _validate_private_directory_fd(
            descriptor,
            owner,
            reader_gid,
            code,
            allowed_modes=allowed_modes,
        )
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _validate_private_directory_fd(
    descriptor: int,
    owner: int,
    reader_gid: int,
    code: str,
    *,
    allowed_modes: set[int] | None = None,
) -> None:
    try:
        before = os.fstat(descriptor)
        expected_modes = allowed_modes or EXECUTOR_QUEUE_DIRECTORY_MODES
        if (
            not stat.S_ISDIR(before.st_mode)
            or before.st_uid != owner
            or before.st_gid != reader_gid
            or stat.S_IMODE(before.st_mode) not in expected_modes
        ):
            raise _ExternalEvidenceError(code)
        after = os.fstat(descriptor)
    except OSError as exc:
        raise _ExternalEvidenceError(code) from exc
    if (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_uid,
        before.st_gid,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_uid,
        after.st_gid,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        raise _ExternalEvidenceError(code)


def _read_private_file_at(
    parent_fd: int,
    name: str,
    owner: int,
    reader_gid: int,
    *,
    allowed_modes: set[int] | None = None,
    max_bytes: int = 64 * 1024 * 1024,
    code: str,
) -> bytes:
    """Read through one O_NOFOLLOW fd and reject inode drift while reading."""
    if "/" in name or name in {"", ".", ".."}:
        raise _ExternalEvidenceError(code)
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
    except OSError as exc:
        raise _ExternalEvidenceError(code) from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != owner
            or before.st_gid != reader_gid
            or stat.S_IMODE(before.st_mode)
            not in (allowed_modes or EXECUTOR_QUEUE_FILE_MODES)
            or before.st_nlink != 1
            or before.st_size > max_bytes
        ):
            raise _ExternalEvidenceError(code)
        remaining = max_bytes + 1
        chunks: list[bytes] = []
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024 * 1024))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(descriptor)
        before_identity = (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_uid,
            before.st_gid,
            before.st_nlink,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_uid,
            after.st_gid,
            after.st_nlink,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        if before_identity != after_identity or len(raw) != after.st_size or len(raw) > max_bytes:
            raise _ExternalEvidenceError(code)
        return raw
    finally:
        os.close(descriptor)


def _decode_canonical_executor_json(raw: bytes, code: str) -> dict[str, Any]:
    try:
        value = _decode_json(raw)
        canonical = _canonical_json(value) + b"\n"
    except (UnicodeError, json.JSONDecodeError, ValueError, TypeError, RecursionError) as exc:
        raise _ExternalEvidenceError(code) from exc
    if not isinstance(value, dict) or raw != canonical:
        raise _ExternalEvidenceError(code)
    return value


def _opaque_ref(value: Any) -> bool:
    return bool(
        isinstance(value, str)
        and 1 <= len(value) <= 512
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]*", value)
        and "://" not in value
    )


def _paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left.is_relative_to(right) or right.is_relative_to(left)


def _parse_capability_status(raw: bytes) -> tuple[int, int]:
    try:
        lines = raw.decode("ascii", "strict").splitlines()
    except UnicodeDecodeError as exc:
        raise _ExternalEvidenceError("EXECUTOR_QUEUE_VALIDATOR_CAPABILITIES_INVALID") from exc
    matches: dict[str, list[str]] = {"CapEff": [], "CapPrm": []}
    for line in lines:
        for label in matches:
            match = re.fullmatch(rf"{label}:[ \t]+([0-9A-Fa-f]{{16}})", line)
            if match:
                matches[label].append(match.group(1))
                break
            if line.lstrip(" \t").startswith(f"{label}:"):
                raise _ExternalEvidenceError(
                    "EXECUTOR_QUEUE_VALIDATOR_CAPABILITIES_INVALID"
                )
    if any(len(values) != 1 for values in matches.values()):
        raise _ExternalEvidenceError("EXECUTOR_QUEUE_VALIDATOR_CAPABILITIES_INVALID")
    return int(matches["CapEff"][0], 16), int(matches["CapPrm"][0], 16)


def _read_capability_file(path: Path) -> tuple[int, int]:
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        )
    except OSError as exc:
        raise _ExternalEvidenceError("EXECUTOR_QUEUE_VALIDATOR_CAPABILITIES_UNREADABLE") from exc
    try:
        raw = b""
        while len(raw) <= 64 * 1024:
            chunk = os.read(descriptor, 64 * 1024 + 1 - len(raw))
            if not chunk:
                break
            raw += chunk
        if len(raw) > 64 * 1024:
            raise _ExternalEvidenceError("EXECUTOR_QUEUE_VALIDATOR_CAPABILITIES_INVALID")
    finally:
        os.close(descriptor)
    return _parse_capability_status(raw)


def _read_process_capabilities() -> tuple[int, int]:
    """Read and reconcile process-leader/current-thread Linux CapEff and CapPrm."""
    process_sets = _read_capability_file(PROC_SELF_STATUS)
    thread_sets = _read_capability_file(PROC_THREAD_SELF_STATUS)
    if process_sets != thread_sets:
        raise _ExternalEvidenceError("EXECUTOR_QUEUE_VALIDATOR_CAPABILITIES_INVALID")
    return thread_sets


def _validate_live_process_trust_boundary() -> tuple[int, frozenset[int]]:
    """Require an unprivileged validator process separate from the queue owner."""
    euid = os.geteuid()
    if euid == 0:
        raise _ExternalEvidenceError("EXECUTOR_QUEUE_VALIDATOR_ROOT_FORBIDDEN")
    effective, permitted = _read_process_capabilities()
    if effective != 0:
        names = [name for bit, name in CAPABILITY_NAMES.items() if effective & (1 << bit)]
        suffix = "_".join(names) if names else "NONZERO"
        raise _ExternalEvidenceError(f"EXECUTOR_QUEUE_VALIDATOR_EFFECTIVE_CAPABILITIES_FORBIDDEN:{suffix}")
    if permitted != 0:
        names = [name for bit, name in CAPABILITY_NAMES.items() if permitted & (1 << bit)]
        suffix = "_".join(names) if names else "NONZERO"
        raise _ExternalEvidenceError(f"EXECUTOR_QUEUE_VALIDATOR_PERMITTED_CAPABILITIES_FORBIDDEN:{suffix}")
    try:
        group_ids = frozenset({os.getegid(), *os.getgroups()})
    except OSError as exc:
        raise _ExternalEvidenceError(
            "EXECUTOR_QUEUE_VALIDATOR_GROUPS_UNREADABLE"
        ) from exc
    return euid, group_ids


def _parse_mode(value: Any, allowed: set[int]) -> int | None:
    if not isinstance(value, str) or not re.fullmatch(r"0[0-7]{3}", value):
        return None
    parsed = int(value, 8)
    return parsed if parsed in allowed else None


def _trusted_parent_matches(info: os.stat_result, config: dict[str, Any]) -> bool:
    expected_mode = _parse_mode(
        config.get("state_root_parent_mode"),
        {mode for mode in range(0o1000) if mode & 0o022 == 0},
    )
    return bool(
        stat.S_ISDIR(info.st_mode)
        and info.st_uid == 0
        and expected_mode is not None
        and stat.S_IMODE(info.st_mode) == expected_mode
        and info.st_dev == config.get("state_root_parent_device")
        and info.st_ino == config.get("state_root_parent_inode")
    )


def _trusted_state_root_matches(
    info: os.stat_result,
    config: dict[str, Any],
    owner: int,
    reader_gid: int,
) -> bool:
    expected_mode = _parse_mode(
        config.get("state_root_mode"), EXECUTOR_QUEUE_DIRECTORY_MODES
    )
    return bool(
        stat.S_ISDIR(info.st_mode)
        and info.st_uid == owner
        and info.st_gid == reader_gid
        and expected_mode is not None
        and stat.S_IMODE(info.st_mode) == expected_mode
        and info.st_dev == config.get("state_root_device")
        and info.st_ino == config.get("state_root_inode")
    )


def _open_trusted_state_root(
    trust: dict[str, Any],
    code: str,
) -> tuple[int, int]:
    """Open the root-owned anchor then its exact configured queue child."""
    config = trust["config"]
    owner = trust["owner_uid"]
    reader_gid = trust["reader_gid"]
    parent_path = Path(config["state_root_parent_realpath"])
    try:
        if (
            not parent_path.is_absolute()
            or parent_path != parent_path.resolve(strict=True)
        ):
            raise _ExternalEvidenceError(code)
        parent_fd = os.open(
            parent_path,
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0),
        )
    except _ExternalEvidenceError:
        raise
    except (OSError, RuntimeError) as exc:
        raise _ExternalEvidenceError(code) from exc
    root_fd = -1
    try:
        if not _trusted_parent_matches(os.fstat(parent_fd), config):
            raise _ExternalEvidenceError(code)
        root_fd = _open_private_directory_at(
            parent_fd,
            config["state_root_basename"],
            owner,
            reader_gid,
            code,
            allowed_modes=EXECUTOR_QUEUE_DIRECTORY_MODES,
        )
        if not _trusted_state_root_matches(
            os.fstat(root_fd), config, owner, reader_gid
        ):
            raise _ExternalEvidenceError(code)
        return parent_fd, root_fd
    except BaseException:
        if root_fd >= 0:
            os.close(root_fd)
        os.close(parent_fd)
        raise


def _revalidate_trusted_state_root(
    parent_fd: int,
    root_fd: int,
    trust: dict[str, Any],
    code: str,
) -> None:
    """Prove both held inodes and their configured names still identify one tree."""
    config = trust["config"]
    owner = trust["owner_uid"]
    reader_gid = trust["reader_gid"]
    if (
        not _trusted_parent_matches(os.fstat(parent_fd), config)
        or not _trusted_state_root_matches(
            os.fstat(root_fd), config, owner, reader_gid
        )
    ):
        raise _ExternalEvidenceError(code)
    child_again = -1
    parent_again = -1
    named_child_again = -1
    try:
        child_again = _open_private_directory_at(
            parent_fd,
            config["state_root_basename"],
            owner,
            reader_gid,
            code,
            allowed_modes=EXECUTOR_QUEUE_DIRECTORY_MODES,
        )
        if not _trusted_state_root_matches(
            os.fstat(child_again), config, owner, reader_gid
        ):
            raise _ExternalEvidenceError(code)
        parent_path = Path(config["state_root_parent_realpath"])
        if parent_path != parent_path.resolve(strict=True):
            raise _ExternalEvidenceError(code)
        parent_again = os.open(
            parent_path,
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0),
        )
        if not _trusted_parent_matches(os.fstat(parent_again), config):
            raise _ExternalEvidenceError(code)
        named_child_again = _open_private_directory_at(
            parent_again,
            config["state_root_basename"],
            owner,
            reader_gid,
            code,
            allowed_modes=EXECUTOR_QUEUE_DIRECTORY_MODES,
        )
        if not _trusted_state_root_matches(
            os.fstat(named_child_again), config, owner, reader_gid
        ):
            raise _ExternalEvidenceError(code)
    except (OSError, RuntimeError) as exc:
        raise _ExternalEvidenceError(code) from exc
    finally:
        if named_child_again >= 0:
            os.close(named_child_again)
        if parent_again >= 0:
            os.close(parent_again)
        if child_again >= 0:
            os.close(child_again)


def _read_executor_queue_trust_config(
    config_path: Path,
    state_root: Path,
    current_time: datetime,
) -> dict[str, Any]:
    """Load one root-issued queue activation and bind it to the exact queue inode."""
    validator_euid, validator_group_ids = _validate_live_process_trust_boundary()
    try:
        if not config_path.is_absolute() or config_path != config_path.resolve(strict=True):
            raise _ExternalEvidenceError("EXECUTOR_QUEUE_TRUST_CONFIG_PATH_INVALID")
        descriptor = os.open(
            config_path,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        )
    except _ExternalEvidenceError:
        raise
    except (OSError, RuntimeError) as exc:
        raise _ExternalEvidenceError("EXECUTOR_QUEUE_TRUST_CONFIG_UNREADABLE") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != 0
            or stat.S_IMODE(before.st_mode) != 0o444
            or before.st_nlink != 1
            or before.st_size > 64 * 1024
        ):
            raise _ExternalEvidenceError("EXECUTOR_QUEUE_TRUST_CONFIG_FILE_UNSAFE")
        raw = b""
        while len(raw) <= 64 * 1024:
            chunk = os.read(descriptor, min(1024 * 1024, 64 * 1024 + 1 - len(raw)))
            if not chunk:
                break
            raw += chunk
        after = os.fstat(descriptor)
        before_identity = (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_uid,
            before.st_gid,
            before.st_nlink,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_uid,
            after.st_gid,
            after.st_nlink,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        if before_identity != after_identity or len(raw) != after.st_size or len(raw) > 64 * 1024:
            raise _ExternalEvidenceError("EXECUTOR_QUEUE_TRUST_CONFIG_READ_RACE")
    finally:
        os.close(descriptor)

    config = _decode_canonical_executor_json(raw, "EXECUTOR_QUEUE_TRUST_CONFIG_INVALID")
    _require_external_keys(
        config,
        EXECUTOR_TRUST_CONFIG_KEYS,
        "EXECUTOR_QUEUE_TRUST_CONFIG_SCHEMA_INVALID",
    )
    marker = _require_external_keys(
        config.get("queue_marker"),
        EXECUTOR_TRUST_MARKER_KEYS,
        "EXECUTOR_QUEUE_TRUST_CONFIG_MARKER_SCHEMA_INVALID",
    )
    contract = _require_external_keys(
        config.get("executor_contract"),
        EXECUTOR_TRUST_CONTRACT_KEYS,
        "EXECUTOR_QUEUE_TRUST_CONFIG_CONTRACT_SCHEMA_INVALID",
    )
    activation = _require_external_keys(
        config.get("activation"),
        EXECUTOR_TRUST_ACTIVATION_KEYS,
        "EXECUTOR_QUEUE_TRUST_CONFIG_ACTIVATION_SCHEMA_INVALID",
    )
    valid_from = _parse_canonical_time(activation.get("valid_from"))
    expires_at = _parse_canonical_time(activation.get("expires_at"))
    expected_uid = config.get("expected_nonroot_owner_uid")
    expected_username = config.get("expected_nonroot_owner_username")
    expected_validator_uid = config.get("expected_validator_uid")
    expected_validator_username = config.get("expected_validator_username")
    expected_reader_gid = config.get("expected_reader_group_gid")
    expected_reader_group_name = config.get("expected_reader_group_name")
    try:
        account_name = pwd.getpwuid(expected_uid).pw_name if _safe_int(expected_uid, 1) else None
    except (KeyError, OSError):
        account_name = None
    try:
        validator_account_name = (
            pwd.getpwuid(expected_validator_uid).pw_name
            if _safe_int(expected_validator_uid, 1)
            else None
        )
    except (KeyError, OSError):
        validator_account_name = None
    try:
        reader_group_name = (
            grp.getgrgid(expected_reader_gid).gr_name
            if _safe_int(expected_reader_gid, 1)
            else None
        )
    except (KeyError, OSError):
        reader_group_name = None
    try:
        marker_bytes = base64.b64decode(str(marker.get("bytes_base64", "")), validate=True)
    except (ValueError, TypeError):
        marker_bytes = b""
    parent_raw = config.get("state_root_parent_realpath")
    basename = config.get("state_root_basename")
    parent_path = Path(parent_raw) if isinstance(parent_raw, str) else Path()
    expected_state_path = (
        parent_path / basename if isinstance(basename, str) else Path()
    )
    if (
        config.get("schema_version") != EXECUTOR_TRUST_CONFIG_SCHEMA
        or config.get("hash_contract") != EXECUTOR_TRUST_CONFIG_HASH_CONTRACT
        or config.get("config_sha256") != _hash_without(config, "config_sha256")
        or not isinstance(parent_raw, str)
        or not parent_path.is_absolute()
        or str(parent_path) != parent_raw
        or not _safe_int(config.get("state_root_parent_device"))
        or not _safe_int(config.get("state_root_parent_inode"), 1)
        or _parse_mode(
            config.get("state_root_parent_mode"),
            {mode for mode in range(0o1000) if mode & 0o022 == 0},
        )
        is None
        or not isinstance(basename, str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", basename)
        or basename in {".", ".."}
        or not isinstance(config.get("state_root_realpath"), str)
        or not Path(config["state_root_realpath"]).is_absolute()
        or str(expected_state_path) != config.get("state_root_realpath")
        or str(state_root) != config.get("state_root_realpath")
        or not state_root.is_absolute()
        or not _safe_int(config.get("state_root_device"))
        or not _safe_int(config.get("state_root_inode"), 1)
        or _parse_mode(config.get("state_root_mode"), EXECUTOR_QUEUE_DIRECTORY_MODES)
        is None
        or not _safe_int(expected_uid, 1)
        or expected_uid == 0
        or expected_uid == validator_euid
        or not _string(expected_username)
        or account_name != expected_username
        or not _safe_int(expected_validator_uid, 1)
        or expected_validator_uid != validator_euid
        or expected_validator_uid in {0, expected_uid}
        or not _string(expected_validator_username)
        or validator_account_name != expected_validator_username
        or not _safe_int(expected_reader_gid, 1)
        or not _string(expected_reader_group_name)
        or reader_group_name != expected_reader_group_name
        or expected_reader_gid not in validator_group_ids
        or marker.get("relative_path") != EXECUTOR_QUEUE_MARKER_NAME
        or marker_bytes != EXECUTOR_QUEUE_MARKER_BYTES
        or marker.get("sha256") != hashlib.sha256(marker_bytes).hexdigest()
        or contract
        != {
            "executor_skill_ref": EXECUTOR_SKILL_REF,
            "executor_skill_version": EXECUTOR_SKILL_VERSION,
            "request_schema": EXECUTOR_REQUEST_SCHEMA,
            "event_schema": EXECUTOR_EVENT_SCHEMA,
            "initial_event_kind": "ENQUEUED",
        }
        or not _opaque_ref(activation.get("activation_ref"))
        or valid_from is None
        or expires_at is None
        or not (valid_from <= current_time < expires_at)
        or not _opaque_ref(activation.get("activation_receipt_ref"))
        or not HEX64.fullmatch(str(activation.get("activation_receipt_sha256", "")))
    ):
        raise _ExternalEvidenceError("EXECUTOR_QUEUE_TRUST_CONFIG_SEMANTICS_INVALID")

    trust = {
        "config": config,
        "config_path": str(config_path),
        "config_sha256": config["config_sha256"],
        "state_root": state_root,
        "owner_uid": expected_uid,
        "reader_gid": expected_reader_gid,
        "validator_euid": validator_euid,
        "activation_valid_from": valid_from,
        "activation_expires_at": expires_at,
    }
    parent_fd, root_fd = _open_trusted_state_root(
        trust, "EXECUTOR_QUEUE_TRUST_STATE_ROOT_UNSAFE"
    )
    try:
        observed_marker = _read_private_file_at(
            root_fd,
            marker["relative_path"],
            expected_uid,
            expected_reader_gid,
            max_bytes=1024,
            code="EXECUTOR_QUEUE_TRUST_MARKER_INVALID",
        )
        if observed_marker != marker_bytes or hashlib.sha256(observed_marker).hexdigest() != marker["sha256"]:
            raise _ExternalEvidenceError("EXECUTOR_QUEUE_TRUST_MARKER_INVALID")
        _revalidate_trusted_state_root(
            parent_fd,
            root_fd,
            trust,
            "EXECUTOR_QUEUE_TRUST_STATE_ROOT_IDENTITY_DRIFT",
        )
    finally:
        os.close(root_fd)
        os.close(parent_fd)
    return trust


def _executor_request_identity(request: dict[str, Any]) -> str:
    identity = dict(request)
    for field in (
        "ticket_id",
        "obligation_id",
        "idempotency_key",
        "executable_envelope_sha256",
        "created_at",
        "hash_contract",
        "request_sha256",
    ):
        identity.pop(field, None)
    return hashlib.sha256(_canonical_json(identity)).hexdigest()


def compute_executor_origin_envelope_sha256(document: dict[str, Any]) -> str:
    """Bind E2 subject and test identity into the existing DGP origin hash field."""
    source_closure = document["source_closure"]
    envelope = {
        "schema_version": EXECUTOR_ORIGIN_ENVELOPE_SCHEMA,
        "founder_intent_ref": document["founder_intent_ref"],
        "founder_intent_sha256": document["founder_intent_sha256"],
        "identity_root_ref": document["identity_root_ref"],
        "member_ref": document["member_ref"],
        "seat_binding_ref": document["seat_binding_ref"],
        "receiver_ref": document["receiver_ref"],
        "test_receipt_ref": source_closure["test_receipt_ref"],
        "test_receipt_sha256": source_closure["test_receipt_sha256"],
    }
    return hashlib.sha256(_canonical_json(envelope)).hexdigest()


def _path_is_bounded(path: str, bounds: list[str]) -> bool:
    return any(path == bound or path.startswith(bound.rstrip("/") + "/") for bound in bounds)


def _authority_sensitive_path(path: str) -> bool:
    return bool(
        re.search(r"^runtime/total_field/", path, re.IGNORECASE)
        or re.search(
            r"(?:^|/)(?:authority|identity|seat|canonical|ratification|receipt|pointer)(?:[._/-]|$)",
            path,
            re.IGNORECASE,
        )
    )


def _executor_execution_scope(request: dict[str, Any]) -> str:
    git = request["git"]
    effects = request["effects"]
    scope = {
        "schema_version": EXECUTOR_SCOPE_SCHEMA,
        "origin_intent_sha256": request["origin_intent_sha256"],
        "repository_fingerprint_sha256": request["repository"]["fingerprint_sha256"],
        "remote_endpoint_fingerprint_sha256": request["remote"]["endpoint_fingerprint_sha256"],
        "remote_name": request["remote"]["name"],
        "target_ref": git["target_ref"],
        "expected_remote_old_oid": git["expected_remote_old_oid"],
        "source_state": git["source_state"],
        "source_commit_oid": git["source_commit_oid"],
        "source_tree_oid": git["source_tree_oid"],
        "commit_range_sha256": git["commit_range_sha256"],
        "causal_group_combined_sha256": git["causal_group_combined_sha256"],
        "causal_group_changed_paths": git["causal_group_changed_paths"],
        "causal_group_dependency_order": git["causal_group_dependency_order"],
        "authority_sensitive_paths": git["authority_sensitive_paths"],
        "change_scope_sha256": git["change_scope_sha256"],
        "reachable_object_closure_sha256": git["reachable_object_closure_sha256"],
        "bounded_paths": git["bounded_paths"],
        "effects": {
            "ci_or_deploy": effects["ci_or_deploy"],
            "hook": "REQUIRE_ABSENT",
            "lfs": "REQUIRE_ABSENT",
            "submodule_recursive_push": "DENIED",
            "tags": "DENIED",
        },
        "effect_class": "E4",
        "push_policy": "ONE_PROVEN_FAST_FORWARD_WITH_EXACT_SERVER_CAS",
    }
    return hashlib.sha256(_canonical_json(scope)).hexdigest()


def _validate_external_authority(request: dict[str, Any]) -> None:
    authorization = request["authorization"]
    if (
        authorization["single_use"] is not True
        or (authorization["ref"] is None) != (authorization["expires_at"] is None)
    ):
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_AUTHORIZATION_INVALID")
    if authorization["ref"] is not None and (
        not _string(authorization["ref"])
        or _parse_canonical_time(authorization["expires_at"]) is None
    ):
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_AUTHORIZATION_INVALID")
    legacy = (
        authorization["total_field_decision_ref"],
        authorization["total_field_decision_expires_at"],
        authorization["total_field_scope_sha256"],
    )
    if any(value is not None for value in legacy) and not all(value is not None for value in legacy):
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_AUTHORIZATION_INVALID")
    if all(value is not None for value in legacy) and (
        not _string(legacy[0])
        or _parse_canonical_time(legacy[1]) is None
        or not HEX64.fullmatch(str(legacy[2]))
    ):
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_AUTHORIZATION_INVALID")
    required_scope = _executor_execution_scope(request)
    if authorization["required_scope_sha256"] != required_scope:
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_REQUIRED_SCOPE_INVALID")
    receipt = authorization["decision_receipt"]
    if receipt is not None:
        receipt = _require_external_keys(
            receipt,
            EXECUTOR_DECISION_RECEIPT_KEYS,
            "EXTERNAL_EXECUTOR_DECISION_RECEIPT_SCHEMA_INVALID",
        )
        issued = _parse_canonical_time(receipt.get("issued_at"))
        not_before = _parse_canonical_time(receipt.get("not_before"))
        expires = _parse_canonical_time(receipt.get("expires_at"))
        if (
            receipt.get("schema_version") != TOTAL_FIELD_RECEIPT_SCHEMA
            or receipt.get("receiver") != TOTAL_FIELD_RECEIVER
            or receipt.get("decision") != TOTAL_FIELD_DECISION
            or receipt.get("hash_contract") != EXECUTOR_HASH_CONTRACT
            or receipt.get("scope_sha256") != required_scope
            or receipt.get("rollback_policy") != TOTAL_FIELD_ROLLBACK_POLICY
            or receipt.get("stop_conditions") != TOTAL_FIELD_STOP_CONDITIONS
            or not all(_string(receipt.get(field)) for field in (
                "decision_ref",
                "identity_root_ref",
                "seat_ref",
                "member_ref",
                "single_use_nonce",
            ))
            or len(receipt.get("single_use_nonce", "")) < 16
            or issued is None
            or not_before is None
            or expires is None
            or not (issued <= not_before < expires)
            or receipt.get("receipt_sha256") != _hash_without(receipt, "receipt_sha256")
            or legacy != (
                receipt.get("decision_ref"),
                receipt.get("expires_at"),
                receipt.get("scope_sha256"),
            )
        ):
            raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_DECISION_RECEIPT_INVALID")
    activation = authorization["receiver_activation"]
    if activation is not None:
        activation = _require_external_keys(
            activation,
            EXECUTOR_ACTIVATION_KEYS,
            "EXTERNAL_EXECUTOR_ACTIVATION_SCHEMA_INVALID",
        )
        if (
            activation.get("receiver") != TOTAL_FIELD_RECEIVER
            or activation.get("protocol") != "w7tp-total-field-receiver-adapter/1.0"
            or not all(HEX64.fullmatch(str(activation.get(field, ""))) for field in (
                "config_sha256",
                "adapter_sha256",
            ))
            or not all(_string(activation.get(field)) for field in (
                "config_path",
                "activation_ref",
                "adapter_realpath",
                "allowed_executor_username",
            ))
            or not Path(activation["config_path"]).is_absolute()
            or not Path(activation["adapter_realpath"]).is_absolute()
            or not _safe_int(activation.get("allowed_executor_uid"), 1)
        ):
            raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_ACTIVATION_INVALID")


def _validate_external_manifest(
    manifest: Any,
    bounds: list[str],
    oid_length: int,
    label: str,
) -> list[str]:
    if not isinstance(manifest, list):
        raise _ExternalEvidenceError(f"EXTERNAL_EXECUTOR_{label}_INVALID")
    paths: list[str] = []
    previous: tuple[str, str] | None = None
    for raw_entry in manifest:
        entry = _require_external_keys(
            raw_entry,
            {"path", "status", "old", "new"},
            f"EXTERNAL_EXECUTOR_{label}_SCHEMA_INVALID",
        )
        path = entry.get("path")
        status = entry.get("status")
        if (
            not _safe_path(path)
            or not _path_is_bounded(path, bounds)
            or status not in {"A", "M", "D", "T"}
        ):
            raise _ExternalEvidenceError(f"EXTERNAL_EXECUTOR_{label}_INVALID")
        for side in ("old", "new"):
            blob = entry.get(side)
            if blob is None:
                continue
            blob = _require_external_keys(
                blob,
                {"mode", "object_type", "git_oid", "content_sha256", "size"},
                f"EXTERNAL_EXECUTOR_{label}_BLOB_SCHEMA_INVALID",
            )
            if (
                blob.get("mode") not in {"100644", "100755"}
                or blob.get("object_type") != "blob"
                or not isinstance(blob.get("git_oid"), str)
                or len(blob["git_oid"]) != oid_length
                or not HEX_OID.fullmatch(blob["git_oid"])
                or not HEX64.fullmatch(str(blob.get("content_sha256", "")))
                or not _safe_int(blob.get("size"))
            ):
                raise _ExternalEvidenceError(f"EXTERNAL_EXECUTOR_{label}_BLOB_INVALID")
        if (
            (status == "A" and (entry["old"] is not None or entry["new"] is None))
            or (status == "D" and (entry["old"] is None or entry["new"] is not None))
            or (status in {"M", "T"} and (entry["old"] is None or entry["new"] is None))
        ):
            raise _ExternalEvidenceError(f"EXTERNAL_EXECUTOR_{label}_PAIRING_INVALID")
        coordinate = (path, status)
        if previous is not None and coordinate <= previous:
            raise _ExternalEvidenceError(f"EXTERNAL_EXECUTOR_{label}_ORDER_INVALID")
        previous = coordinate
        paths.append(path)
    return paths


def _validate_external_request(request: dict[str, Any], ticket_id: str) -> None:
    _require_external_keys(request, EXECUTOR_REQUEST_KEYS, "EXTERNAL_EXECUTOR_REQUEST_SCHEMA_INVALID")
    if (
        request.get("schema_version") != EXECUTOR_REQUEST_SCHEMA
        or request.get("hash_contract") != EXECUTOR_HASH_CONTRACT
        or request.get("responsible_agent_ref") != "codex:complete-deferred-git-push"
        or request.get("scheduler_state") != "HANDOFF_RESUME_REQUIRED"
        or not HEX64.fullmatch(str(request.get("origin_intent_sha256", "")))
        or _parse_canonical_time(request.get("created_at")) is None
    ):
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_REQUEST_SEMANTICS_INVALID")
    for key, expected in (
        ("repository", EXECUTOR_REPOSITORY_KEYS),
        ("remote", EXECUTOR_REMOTE_KEYS),
        ("git", EXECUTOR_GIT_KEYS),
        ("authorization", EXECUTOR_AUTHORIZATION_KEYS),
        ("effects", EXECUTOR_EFFECT_KEYS),
    ):
        _require_external_keys(request.get(key), expected, f"EXTERNAL_EXECUTOR_{key.upper()}_SCHEMA_INVALID")
    repository = request["repository"]
    remote = request["remote"]
    git = request["git"]
    authorization = request["authorization"]
    effects = request["effects"]
    if repository.get("object_format") not in {"sha1", "sha256"}:
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_REQUEST_SEMANTICS_INVALID")
    oid_length = 40 if repository["object_format"] == "sha1" else 64
    if (
        not all(
            _string(repository.get(field))
            and Path(repository[field]).is_absolute()
            and str(Path(repository[field])) == repository[field]
            and ".." not in Path(repository[field]).parts
            and Path(repository[field]).is_dir()
            and Path(repository[field]).resolve(strict=True) == Path(repository[field])
            for field in ("root", "git_common_dir")
        )
        or not all(HEX64.fullmatch(str(repository.get(field, ""))) for field in (
            "fingerprint_sha256",
            "local_config_keys_sha256",
            "local_config_values_sha256",
        ))
        or not _safe_int(repository.get("local_config_key_count"))
        or not isinstance(remote.get("name"), str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", remote["name"])
        or not HEX64.fullmatch(str(remote.get("endpoint_fingerprint_sha256", "")))
    ):
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_REQUEST_SEMANTICS_INVALID")
    expected_repository_fingerprint = hashlib.sha256(
        _canonical_json(
            {
                "contract": "git-repository-location/v1",
                "repo_root": repository["root"],
                "git_common_dir": repository["git_common_dir"],
                "object_format": repository["object_format"],
                "local_config_keys_sha256": repository["local_config_keys_sha256"],
                "local_config_values_sha256": repository["local_config_values_sha256"],
            }
        )
    ).hexdigest()
    if repository["fingerprint_sha256"] != expected_repository_fingerprint:
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_REPOSITORY_FINGERPRINT_INVALID")
    if remote.get("file_repository_identity") is not None:
        file_identity = _require_external_keys(
            remote["file_repository_identity"],
            {"canonical_bare_repository", "device", "inode"},
            "EXTERNAL_EXECUTOR_FILE_REMOTE_IDENTITY_INVALID",
        )
        if not _string(file_identity.get("canonical_bare_repository")) or not all(
            _safe_int(file_identity.get(field)) for field in ("device", "inode")
        ):
            raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_FILE_REMOTE_IDENTITY_INVALID")
    expected_safety = {
        "fast_forward_only": True,
        "force_allowed": False,
        "non_fast_forward_allowed": False,
        "exact_server_cas_required": True,
        "delete_allowed": False,
        "tags_allowed": False,
        "multi_ref_allowed": False,
    }
    if any(git.get(key) is not value for key, value in expected_safety.items()):
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_GIT_SAFETY_INVALID")
    if git.get("target_ref") is not None and not _target_ref(git.get("target_ref")):
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_TARGET_REF_INVALID")
    source_state = git.get("source_state")
    source = git.get("source_commit_oid")
    old = git.get("expected_remote_old_oid")
    if source_state == "EXACT_COMMIT_LOCKED":
        if not (
            isinstance(source, str)
            and len(source) == oid_length
            and HEX_OID.fullmatch(source)
            and isinstance(old, str)
            and len(old) == oid_length
            and HEX_OID.fullmatch(old)
            and git.get("server_cas_expected_old_oid") == old
            and git.get("refspec") == f"{source}:{git.get('target_ref')}"
            and isinstance(git.get("source_tree_oid"), str)
            and len(git["source_tree_oid"]) == oid_length
            and HEX_OID.fullmatch(git["source_tree_oid"])
            and _safe_int(git.get("reachable_object_count"), 1)
            and HEX64.fullmatch(str(git.get("reachable_object_closure_sha256", "")))
        ):
            raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_EXACT_SOURCE_INVALID")
    elif source_state == "WAITING_EXACT_TARGET":
        waiting_values = {
            "source_commit_oid": None,
            "source_tree_oid": None,
            "source_parent_oids": [],
            "reachable_object_closure_sha256": None,
            "reachable_object_count": None,
            "changed_paths": [],
            "change_manifest": [],
            "change_scope_sha256": None,
            "commit_range_oids": [],
            "commit_range_sha256": None,
            "causal_groups": [],
            "causal_group_changed_paths": [],
            "causal_group_dependency_order": [],
            "causal_group_combined_sha256": None,
            "authority_sensitive_paths": [],
            "refspec": None,
        }
        if (
            any(git.get(field) != value for field, value in waiting_values.items())
            or not _target_ref(git.get("target_ref"))
            or not isinstance(old, str)
            or len(old) != oid_length
            or not HEX_OID.fullmatch(old)
            or git.get("server_cas_expected_old_oid") != old
        ):
            raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_WAITING_SOURCE_INVALID")
    else:
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_SOURCE_STATE_INVALID")
    list_fields = (
        "source_parent_oids",
        "changed_paths",
        "change_manifest",
        "commit_range_oids",
        "causal_groups",
        "causal_group_changed_paths",
        "causal_group_dependency_order",
        "authority_sensitive_paths",
        "bounded_paths",
    )
    if any(not isinstance(git.get(field), list) for field in list_fields):
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_GIT_SCHEMA_INVALID")
    bounds = git["bounded_paths"]
    if (
        not all(isinstance(path, str) and _safe_path(path) for path in bounds)
        or bounds != sorted(set(bounds))
        or not all(isinstance(path, str) and _safe_path(path) for path in git["changed_paths"])
        or git["changed_paths"] != sorted(set(git["changed_paths"]))
        or not all(_path_is_bounded(path, bounds) for path in git["changed_paths"])
    ):
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_GIT_CANONICAL_ORDER_INVALID")
    manifest_paths = _validate_external_manifest(
        git["change_manifest"], bounds, oid_length, "CHANGE_MANIFEST"
    )
    if manifest_paths != git["changed_paths"]:
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_CHANGE_MANIFEST_PATHS_INVALID")
    if source_state == "EXACT_COMMIT_LOCKED":
        if not bounds:
            raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_BOUNDED_PATHS_REQUIRED")
        if (
            len(git["source_parent_oids"]) > 1
            or not all(
                isinstance(oid, str) and len(oid) == oid_length and HEX_OID.fullmatch(oid)
                for oid in git["source_parent_oids"]
            )
            or not 1 <= len(git["commit_range_oids"]) <= 256
            or git["commit_range_oids"][-1] != source
            or not all(
                isinstance(oid, str) and len(oid) == oid_length and HEX_OID.fullmatch(oid)
                for oid in git["commit_range_oids"]
            )
            or git["change_scope_sha256"]
            != hashlib.sha256(_canonical_json(git["change_manifest"])).hexdigest()
            or git["commit_range_sha256"]
            != hashlib.sha256(_canonical_json(git["commit_range_oids"])).hexdigest()
            or len(git["causal_groups"]) != len(git["commit_range_oids"])
        ):
            raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_EXACT_SOURCE_CLOSURE_INVALID")
        causal_union: set[str] = set()
        causal_parent = old
        for index, raw_group in enumerate(git["causal_groups"], start=1):
            group = _require_external_keys(
                raw_group,
                {
                    "sequence",
                    "parent_commit_oid",
                    "commit_oid",
                    "commit_tree_oid",
                    "changed_paths",
                    "change_manifest",
                    "change_scope_sha256",
                },
                "EXTERNAL_EXECUTOR_CAUSAL_GROUP_SCHEMA_INVALID",
            )
            group_paths = _validate_external_manifest(
                group["change_manifest"], bounds, oid_length, f"CAUSAL_GROUP_{index}_MANIFEST"
            )
            commit_oid = git["commit_range_oids"][index - 1]
            tree_oid = group.get("commit_tree_oid")
            if (
                group.get("sequence") != index
                or group.get("parent_commit_oid") != causal_parent
                or group.get("commit_oid") != commit_oid
                or not isinstance(tree_oid, str)
                or len(tree_oid) != oid_length
                or not HEX_OID.fullmatch(tree_oid)
                or group.get("changed_paths") != group_paths
                or group_paths != sorted(set(group_paths))
                or group.get("change_scope_sha256")
                != hashlib.sha256(_canonical_json(group["change_manifest"])).hexdigest()
            ):
                raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_CAUSAL_GROUP_INVALID")
            causal_union.update(group_paths)
            causal_parent = commit_oid
        expected_union = sorted(causal_union)
        if (
            git["causal_group_changed_paths"] != expected_union
            or git["causal_group_dependency_order"] != git["commit_range_oids"]
            or git["causal_group_combined_sha256"]
            != hashlib.sha256(_canonical_json(git["causal_groups"])).hexdigest()
            or git["authority_sensitive_paths"]
            != [path for path in expected_union if _authority_sensitive_path(path)]
        ):
            raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_CAUSAL_SCOPE_INVALID")
    if effects != {
        "ci_or_deploy": effects.get("ci_or_deploy"),
        "hook": "REQUIRE_ABSENT",
        "lfs": "REQUIRE_ABSENT",
        "submodule_recursive_push": "DENIED",
        "tags": "DENIED",
    } or effects.get("ci_or_deploy") not in {
        "UNKNOWN_UNVERIFIED",
        "NO_CI_OR_DEPLOY_EFFECT",
        "AUTHORIZED_CI_OR_DEPLOY_EFFECT",
    }:
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_EFFECTS_INVALID")
    _validate_external_authority(request)
    identity = _executor_request_identity(request)
    envelope = hashlib.sha256(
        _canonical_json(
            {
                "contract": "w7tp-deferred-git-executable-envelope/1.0",
                "ticket_id": ticket_id,
                "idempotency_key": identity,
            }
        )
    ).hexdigest()
    if (
        request.get("ticket_id") != ticket_id
        or request.get("obligation_id") != ticket_id
        or request.get("idempotency_key") != identity
        or ticket_id != "dgp-" + identity
        or request.get("executable_envelope_sha256") != envelope
        or request.get("request_sha256") != _hash_without(request, "request_sha256")
        or (
            request.get("supersedes_ticket_id") is not None
            and not EXECUTOR_TICKET_ID.fullmatch(str(request["supersedes_ticket_id"]))
        )
    ):
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_REQUEST_IDENTITY_INVALID")


def _validate_initial_executor_event(request: dict[str, Any], event: dict[str, Any]) -> None:
    _require_external_keys(event, EXECUTOR_EVENT_KEYS, "EXTERNAL_EXECUTOR_EVENT_SCHEMA_INVALID")
    expected_state = (
        "WAITING_EXACT_TARGET"
        if request["git"]["source_state"] == "WAITING_EXACT_TARGET"
        else "WAITING_AUTHORIZATION"
    )
    details = _require_external_keys(
        event.get("details"),
        {"request_sha256", "queue_ack", "background_scheduler_active"},
        "EXTERNAL_EXECUTOR_INITIAL_ACK_SCHEMA_INVALID",
    )
    if (
        event.get("schema_version") != EXECUTOR_EVENT_SCHEMA
        or event.get("hash_contract") != EXECUTOR_HASH_CONTRACT
        or event.get("ticket_id") != request["ticket_id"]
        or event.get("sequence") != 1
        or _parse_canonical_time(event.get("occurred_at")) is None
        or event.get("kind") != "ENQUEUED"
        or event.get("state") != expected_state
        or event.get("next_attempt_at") is not None
        or event.get("prev_event_hash") is not None
        or details
        != {
            "request_sha256": request["request_sha256"],
            "queue_ack": "DURABLE_EXTERNAL_QUEUE_ACK",
            "background_scheduler_active": False,
        }
        or event.get("event_sha256") != _hash_without(event, "event_sha256")
    ):
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_INITIAL_ACK_INVALID")


def _cross_bind_executor_request(document: dict[str, Any], request: dict[str, Any]) -> None:
    repository = document["repository"]
    source_closure = document["source_closure"]
    authorization = document["authorization"]
    safety = document["safety"]
    git = request["git"]
    request_authorization = request["authorization"]
    request_receipt = request_authorization["decision_receipt"]
    external_source = git["source_commit_oid"] if git["source_commit_oid"] is not None else UNRESOLVED
    external_target = git["target_ref"] if git["target_ref"] is not None else UNRESOLVED
    external_old = git["expected_remote_old_oid"] if git["expected_remote_old_oid"] is not None else UNRESOLVED
    external_refspec = git["refspec"] if git["refspec"] is not None else UNRESOLVED
    expected = {
        "repo_ref": request["repository"]["root"],
        "repository_fingerprint_sha256": request["repository"]["fingerprint_sha256"],
        "remote_name": request["remote"]["name"],
        "remote_endpoint_sha256": request["remote"]["endpoint_fingerprint_sha256"],
        "target_ref": external_target,
        "source_oid": external_source,
        "expected_remote_old_oid": external_old,
        "object_format": request["repository"]["object_format"],
        "refspec": external_refspec,
    }
    decision_receipt_sha = None if request_receipt is None else request_receipt.get("receipt_sha256")
    expected_authorization = {
        "required": True,
        "authorization_ref": request_authorization["ref"],
        "authorization_expires_at": request_authorization["expires_at"],
        "decision_ref": request_authorization["total_field_decision_ref"],
        "decision_receipt_sha256": decision_receipt_sha,
        "decision_expires_at": request_authorization["total_field_decision_expires_at"],
        "scope_sha256": request_authorization["required_scope_sha256"],
    }
    expected_ci = {
        "NOT_USED": "NO_CI_OR_DEPLOY_EFFECT",
        "REVIEWED_AUTHORIZED": "AUTHORIZED_CI_OR_DEPLOY_EFFECT",
    }.get(safety["push_effects"]["ci_webhook_deploy"])
    if (
        any(repository.get(key) != value for key, value in expected.items())
        or request.get("origin_intent_sha256")
        != compute_executor_origin_envelope_sha256(document)
        or authorization != expected_authorization
        or safety["push_effects"].get("pre_push_hooks") != "DISABLED"
        or safety["push_effects"].get("git_lfs") != "NOT_USED"
        or expected_ci is None
        or request["effects"]
        != {
            "ci_or_deploy": expected_ci,
            "hook": "REQUIRE_ABSENT",
            "lfs": "REQUIRE_ABSENT",
            "submodule_recursive_push": "DENIED",
            "tags": "DENIED",
        }
    ):
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_REQUEST_OBLIGATION_MISMATCH")
    if request_receipt is not None and (
        request_receipt.get("identity_root_ref") != document.get("identity_root_ref")
        or request_receipt.get("member_ref") != document.get("member_ref")
        or request_receipt.get("seat_ref") != document.get("seat_binding_ref")
        or request_receipt.get("receiver") != document.get("receiver_ref")
        or request_receipt.get("scope_sha256") != authorization.get("scope_sha256")
    ):
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_AUTHORITY_SUBJECT_MISMATCH")
    if external_source != UNRESOLVED:
        if (
            source_closure.get("commit_oid") != external_source
            or source_closure.get("tree_oid") != git.get("source_tree_oid")
            or source_closure.get("reachable_objects_sha256")
            != git.get("reachable_object_closure_sha256")
            or git.get("source_parent_oids") != [source_closure.get("parent_oid")]
            or source_closure.get("reviewed_history_sha256") != git.get("commit_range_sha256")
        ):
            raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_SOURCE_CLOSURE_MISMATCH")
        projected_changes: list[dict[str, Any]] = []
        for entry in git["change_manifest"]:
            status = entry["status"]
            blob = entry["old"] if status == "D" else entry["new"]
            if blob is None:
                raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_CHANGE_SCOPE_MISMATCH")
            projected_changes.append(
                {
                    "status": status,
                    "path": entry["path"],
                    "sha256": blob["content_sha256"],
                }
            )
        projected_changes.sort(key=lambda item: (item["path"], item["status"], item["sha256"]))
        if (
            document.get("changes") != projected_changes
            or document.get("change_set_sha256")
            != hashlib.sha256(_canonical_json(projected_changes)).hexdigest()
            or git.get("causal_group_changed_paths")
            != [item["path"] for item in projected_changes]
        ):
            raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_CHANGE_SCOPE_MISMATCH")


def _validate_executor_event_chain(
    events_fd: int,
    owner: int,
    reader_gid: int,
    request: dict[str, Any],
) -> list[dict[str, Any]]:
    try:
        before = os.fstat(events_fd)
        names = os.listdir(events_fd)
    except OSError as exc:
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_EVENT_CHAIN_INVALID") from exc
    if not names or any(not re.fullmatch(r"[0-9]{20}\.json", name) for name in names):
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_EVENT_CHAIN_INVALID")
    ordered = sorted(names)
    if ordered != [f"{index:020d}.json" for index in range(1, len(ordered) + 1)]:
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_EVENT_CHAIN_INVALID")
    events: list[dict[str, Any]] = []
    previous: str | None = None
    previous_time = _parse_canonical_time(request["created_at"])
    for index, name in enumerate(ordered, start=1):
        event = _decode_canonical_executor_json(
            _read_private_file_at(
                events_fd,
                name,
                owner,
                reader_gid,
                code="EXTERNAL_EXECUTOR_EVENT_CHAIN_INVALID",
            ),
            "EXTERNAL_EXECUTOR_EVENT_CHAIN_INVALID",
        )
        _require_external_keys(event, EXECUTOR_EVENT_KEYS, "EXTERNAL_EXECUTOR_EVENT_SCHEMA_INVALID")
        occurred = _parse_canonical_time(event.get("occurred_at"))
        next_attempt = (
            None
            if event.get("next_attempt_at") is None
            else _parse_canonical_time(event.get("next_attempt_at"))
        )
        if (
            event.get("schema_version") != EXECUTOR_EVENT_SCHEMA
            or event.get("hash_contract") != EXECUTOR_HASH_CONTRACT
            or event.get("ticket_id") != request["ticket_id"]
            or event.get("sequence") != index
            or event.get("prev_event_hash") != previous
            or event.get("event_sha256") != _hash_without(event, "event_sha256")
            or occurred is None
            or previous_time is None
            or occurred < previous_time
            or (event.get("next_attempt_at") is not None and next_attempt is None)
            or (next_attempt is not None and next_attempt < occurred)
        ):
            raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_EVENT_CHAIN_INVALID")
        previous_time = occurred
        previous = event["event_sha256"]
        events.append(event)
    after = os.fstat(events_fd)
    if (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_uid,
        before.st_gid,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_uid,
        after.st_gid,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_EVENT_CHAIN_INVALID")
    _validate_initial_executor_event(request, events[0])
    return events


def compute_obligation_core_hash(document: dict[str, Any]) -> str:
    """Hash the obligation fields that an independent queue ACK can bind without a cycle."""
    clone = json.loads(json.dumps(document, ensure_ascii=False, allow_nan=False))
    queue_store = clone.get("queue_store")
    if isinstance(queue_store, dict):
        queue_store.pop("append_only_ack_sha256", None)
    handoff = clone.get("executor_handoff")
    if isinstance(handoff, dict):
        handoff.pop("handoff_sha256", None)
    return hashlib.sha256(_canonical_json(clone)).hexdigest()


def compute_executor_handoff_payload_hash(document: dict[str, Any]) -> str:
    handoff = dict(document["executor_handoff"])
    handoff.pop("handoff_sha256", None)
    return hashlib.sha256(_canonical_json(handoff)).hexdigest()


def compute_obligation_effect_scope_hash(document: dict[str, Any]) -> str:
    scope = {
        "contract": "w7tp-e2-deferred-push-effect-scope/1.0",
        "total_field_route": document["total_field_route"],
        "safety": document["safety"],
    }
    return hashlib.sha256(_canonical_json(scope)).hexdigest()


def _validate_external_obligation_ack(
    ack: dict[str, Any],
    document: dict[str, Any],
    request: dict[str, Any],
    initial_event: dict[str, Any],
    trust: dict[str, Any],
) -> None:
    _require_external_keys(
        ack,
        EXECUTOR_OBLIGATION_ACK_KEYS,
        "EXTERNAL_OBLIGATION_ACK_SCHEMA_INVALID",
    )
    queue_store = document["queue_store"]
    handoff = document["executor_handoff"]
    ticket_id = request["ticket_id"]
    request_ref = f"tickets/{ticket_id}/request.json"
    event_ref = f"tickets/{ticket_id}/events/{EXECUTOR_INITIAL_EVENT_NAME}"
    ack_ref = f"{EXECUTOR_OBLIGATION_ACK_DIR}/{ticket_id}.json"
    acknowledged_at = _parse_canonical_time(ack.get("acknowledged_at"))
    event_time = _parse_canonical_time(initial_event.get("occurred_at"))
    if (
        ack.get("schema_version") != EXECUTOR_OBLIGATION_ACK_SCHEMA
        or ack.get("hash_contract") != EXECUTOR_HASH_CONTRACT
        or ack.get("ack_kind") != EXECUTOR_OBLIGATION_ACK_KIND
        or ack.get("ack_state") != EXECUTOR_OBLIGATION_ACK_STATE
        or ack.get("obligation_id") != document["obligation_id"]
        or ack.get("obligation_schema_version") != CURRENT_SCHEMA
        or ack.get("obligation_core_sha256") != compute_obligation_core_hash(document)
        or ack.get("executor_handoff_payload_sha256")
        != compute_executor_handoff_payload_hash(document)
        or ack.get("executor_ticket_id") != ticket_id
        or ack.get("executor_request_ref") != request_ref
        or ack.get("executor_request_sha256") != request["request_sha256"]
        or ack.get("executor_initial_event_ref") != event_ref
        or ack.get("executor_initial_event_sha256") != initial_event["event_sha256"]
        or ack.get("queue_store_idempotency_key") != request["idempotency_key"]
        or ack.get("queue_trust_config_sha256") != trust["config_sha256"]
        or ack.get("founder_intent_ref") != document["founder_intent_ref"]
        or ack.get("founder_intent_sha256") != document["founder_intent_sha256"]
        or ack.get("repository_root") != request["repository"]["root"]
        or ack.get("repository_fingerprint_sha256")
        != request["repository"]["fingerprint_sha256"]
        or ack.get("identity_root_ref") != document["identity_root_ref"]
        or ack.get("member_ref") != document["member_ref"]
        or ack.get("seat_binding_ref") != document["seat_binding_ref"]
        or ack.get("receiver_ref") != document["receiver_ref"]
        or ack.get("test_receipt_ref") != document["source_closure"]["test_receipt_ref"]
        or ack.get("test_receipt_sha256")
        != document["source_closure"]["test_receipt_sha256"]
        or ack.get("authorization_scope_sha256") != document["authorization"]["scope_sha256"]
        or ack.get("effect_scope_sha256") != compute_obligation_effect_scope_hash(document)
        or ack.get("change_set_sha256") != document["change_set_sha256"]
        or acknowledged_at is None
        or event_time is None
        or not (event_time <= acknowledged_at < trust["activation_expires_at"])
        or acknowledged_at < trust["activation_valid_from"]
        or ack.get("ack_sha256") != _hash_without(ack, "ack_sha256")
        or queue_store
        != {
            "store_ref": f"trusted-executor-queue:{trust['config_sha256']}",
            "idempotency_key": request["idempotency_key"],
            "append_only_ack_ref": ack_ref,
            "append_only_ack_sha256": ack.get("ack_sha256"),
            "outside_target_repo": True,
        }
        or handoff.get("executor_queue_ack_ref") != event_ref
        or handoff.get("executor_queue_ack_sha256") != initial_event["event_sha256"]
    ):
        raise _ExternalEvidenceError("EXTERNAL_OBLIGATION_ACK_INVALID")


def _load_external_executor_evidence(
    state_root: Path,
    document: dict[str, Any],
    trust: dict[str, Any],
) -> dict[str, Any]:
    handoff = document["executor_handoff"]
    ticket_id = handoff["executor_ticket_id"]
    owner = trust["owner_uid"]
    reader_gid = trust["reader_gid"]
    parent_fd, root_fd = _open_trusted_state_root(
        trust, "EXTERNAL_EXECUTOR_STATE_ROOT_UNSAFE"
    )
    tickets_fd = ticket_fd = events_fd = obligation_acks_fd = -1
    try:
        config = trust["config"]
        if _read_private_file_at(
            root_fd,
            EXECUTOR_QUEUE_MARKER_NAME,
            owner,
            reader_gid,
            max_bytes=1024,
            code="EXTERNAL_EXECUTOR_QUEUE_MARKER_INVALID",
        ) != EXECUTOR_QUEUE_MARKER_BYTES:
            raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_QUEUE_MARKER_INVALID")
        tickets_fd = _open_private_directory_at(
            root_fd, "tickets", owner, reader_gid, "EXTERNAL_EXECUTOR_TICKETS_UNSAFE"
        )
        ticket_fd = _open_private_directory_at(
            tickets_fd,
            ticket_id,
            owner,
            reader_gid,
            "EXTERNAL_EXECUTOR_TICKET_UNSAFE",
        )
        request = _decode_canonical_executor_json(
            _read_private_file_at(
                ticket_fd,
                "request.json",
                owner,
                reader_gid,
                code="EXTERNAL_EXECUTOR_REQUEST_INVALID",
            ),
            "EXTERNAL_EXECUTOR_REQUEST_INVALID",
        )
        _validate_external_request(request, ticket_id)
        state_path = Path(config["state_root_realpath"])
        for protected in (
            Path(request["repository"]["root"]),
            Path(request["repository"]["git_common_dir"]),
        ):
            if _paths_overlap(state_path, protected):
                raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_STATE_ROOT_OVERLAPS_REPOSITORY")
        _cross_bind_executor_request(document, request)
        events_fd = _open_private_directory_at(
            ticket_fd,
            "events",
            owner,
            reader_gid,
            "EXTERNAL_EXECUTOR_EVENTS_UNSAFE",
        )
        events = _validate_executor_event_chain(events_fd, owner, reader_gid, request)
        if (
            handoff.get("obligation_id") != ticket_id
            or document.get("obligation_id") != ticket_id
            or handoff.get("executor_request_sha256") != request["request_sha256"]
            or handoff.get("executor_queue_ack_ref")
            != f"tickets/{ticket_id}/events/{EXECUTOR_INITIAL_EVENT_NAME}"
            or handoff.get("executor_queue_ack_sha256") != events[0]["event_sha256"]
        ):
            raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_HANDOFF_BACKREFERENCE_INVALID")
        obligation_acks_fd = _open_private_directory_at(
            root_fd,
            EXECUTOR_OBLIGATION_ACK_DIR,
            owner,
            reader_gid,
            "EXTERNAL_OBLIGATION_ACK_DIRECTORY_UNSAFE",
        )
        obligation_ack = _decode_canonical_executor_json(
            _read_private_file_at(
                obligation_acks_fd,
                f"{ticket_id}.json",
                owner,
                reader_gid,
                code="EXTERNAL_OBLIGATION_ACK_UNREADABLE",
            ),
            "EXTERNAL_OBLIGATION_ACK_INVALID",
        )
        _validate_external_obligation_ack(obligation_ack, document, request, events[0], trust)
        _validate_private_directory_fd(
            obligation_acks_fd,
            owner,
            reader_gid,
            "EXTERNAL_OBLIGATION_ACK_DIRECTORY_UNSAFE",
        )
        _validate_private_directory_fd(
            events_fd,
            owner,
            reader_gid,
            "EXTERNAL_EXECUTOR_EVENTS_UNSAFE",
        )
        _validate_private_directory_fd(
            ticket_fd,
            owner,
            reader_gid,
            "EXTERNAL_EXECUTOR_TICKET_UNSAFE",
        )
        _validate_private_directory_fd(
            tickets_fd,
            owner,
            reader_gid,
            "EXTERNAL_EXECUTOR_TICKETS_UNSAFE",
        )
        _revalidate_trusted_state_root(
            parent_fd,
            root_fd,
            trust,
            "EXTERNAL_EXECUTOR_STATE_ROOT_IDENTITY_DRIFT",
        )
        return {
            "request": request,
            "events": events,
            "obligation_ack": obligation_ack,
            "owner": owner,
        }
    finally:
        if obligation_acks_fd >= 0:
            os.close(obligation_acks_fd)
        if events_fd >= 0:
            os.close(events_fd)
        if ticket_fd >= 0:
            os.close(ticket_fd)
        if tickets_fd >= 0:
            os.close(tickets_fd)
        os.close(root_fd)
        os.close(parent_fd)


def _validate_external_terminal_receipt(
    state_root: Path,
    document: dict[str, Any],
    evidence: dict[str, Any],
    trust: dict[str, Any],
) -> None:
    request = evidence["request"]
    events = evidence["events"]
    terminal = events[-1]
    details = _require_external_keys(
        terminal.get("details"),
        {
            "remote_oid",
            "receipt_relative_path",
            "receipt_sha256",
            "push_invoked",
            "uncertain_outcome_reconciled",
            "protected_state_comparison",
            "worktree_state",
            "protected_state_repair_state",
        },
        "EXTERNAL_EXECUTOR_TERMINAL_EVENT_INVALID",
    )
    if (
        terminal.get("kind") != "REMOTE_EXACT_OID_READBACK_VERIFIED"
        or terminal.get("state") not in {
            "PUSHED_VERIFIED",
            "PUSHED_VERIFIED_PROTECTED_STATE_DRIFT",
        }
        or terminal.get("next_attempt_at") is not None
        or details.get("remote_oid") != request["git"]["source_commit_oid"]
        or not HEX64.fullmatch(str(details.get("receipt_sha256", "")))
        or type(details.get("push_invoked")) is not bool
        or type(details.get("uncertain_outcome_reconciled")) is not bool
    ):
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_TERMINAL_EVENT_INVALID")
    expected_relative = f"receipts/readback-{details['receipt_sha256']}.json"
    if details.get("receipt_relative_path") != expected_relative:
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_TERMINAL_RECEIPT_REF_INVALID")
    closure = document.get("closure", {})
    if (
        closure.get("remote_readback_receipt_ref")
        != f"tickets/{request['ticket_id']}/{expected_relative}"
        or closure.get("remote_commit_oid") != request["git"]["source_commit_oid"]
    ):
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_TERMINAL_CLOSURE_MISMATCH")

    owner = trust["owner_uid"]
    reader_gid = trust["reader_gid"]
    parent_fd, root_fd = _open_trusted_state_root(
        trust, "EXTERNAL_EXECUTOR_STATE_ROOT_UNSAFE"
    )
    tickets_fd = ticket_fd = receipts_fd = -1
    try:
        tickets_fd = _open_private_directory_at(
            root_fd, "tickets", owner, reader_gid, "EXTERNAL_EXECUTOR_TICKETS_UNSAFE"
        )
        ticket_fd = _open_private_directory_at(
            tickets_fd,
            request["ticket_id"],
            owner,
            reader_gid,
            "EXTERNAL_EXECUTOR_TICKET_UNSAFE",
        )
        receipts_fd = _open_private_directory_at(
            ticket_fd,
            "receipts",
            owner,
            reader_gid,
            "EXTERNAL_EXECUTOR_RECEIPTS_UNSAFE",
        )
        receipt = _decode_canonical_executor_json(
            _read_private_file_at(
                receipts_fd,
                f"readback-{details['receipt_sha256']}.json",
                owner,
                reader_gid,
                code="EXTERNAL_EXECUTOR_TERMINAL_RECEIPT_INVALID",
            ),
            "EXTERNAL_EXECUTOR_TERMINAL_RECEIPT_INVALID",
        )
        _validate_private_directory_fd(
            receipts_fd,
            owner,
            reader_gid,
            "EXTERNAL_EXECUTOR_RECEIPTS_UNSAFE",
        )
        _validate_private_directory_fd(
            ticket_fd,
            owner,
            reader_gid,
            "EXTERNAL_EXECUTOR_TICKET_UNSAFE",
        )
        _validate_private_directory_fd(
            tickets_fd,
            owner,
            reader_gid,
            "EXTERNAL_EXECUTOR_TICKETS_UNSAFE",
        )
        _revalidate_trusted_state_root(
            parent_fd,
            root_fd,
            trust,
            "EXTERNAL_EXECUTOR_STATE_ROOT_IDENTITY_DRIFT",
        )
    finally:
        if receipts_fd >= 0:
            os.close(receipts_fd)
        if ticket_fd >= 0:
            os.close(ticket_fd)
        if tickets_fd >= 0:
            os.close(tickets_fd)
        os.close(root_fd)
        os.close(parent_fd)
    _require_external_keys(
        receipt,
        EXECUTOR_READBACK_RECEIPT_KEYS,
        "EXTERNAL_EXECUTOR_TERMINAL_RECEIPT_SCHEMA_INVALID",
    )
    if (
        receipt.get("schema_version") != EXECUTOR_RECEIPT_SCHEMA
        or receipt.get("hash_contract") != EXECUTOR_HASH_CONTRACT
        or receipt.get("ticket_id") != request["ticket_id"]
        or receipt.get("request_sha256") != request["request_sha256"]
        or _parse_canonical_time(receipt.get("verified_at")) is None
        or receipt.get("verification") != "INDEPENDENT_GIT_LS_REMOTE_EXACT_REF_READBACK"
        or receipt.get("remote_endpoint_fingerprint_sha256")
        != request["remote"]["endpoint_fingerprint_sha256"]
        or receipt.get("target_ref") != request["git"]["target_ref"]
        or receipt.get("expected_remote_old_oid") != request["git"]["expected_remote_old_oid"]
        or receipt.get("intended_source_commit_oid") != request["git"]["source_commit_oid"]
        or receipt.get("observed_remote_oid") != request["git"]["source_commit_oid"]
        or receipt.get("source_tree_oid") != request["git"]["source_tree_oid"]
        or receipt.get("reachable_object_closure_sha256")
        != request["git"]["reachable_object_closure_sha256"]
        or receipt.get("change_scope_sha256") != request["git"]["change_scope_sha256"]
        or receipt.get("remote_exact_oid_match") is not True
        or receipt.get("receipt_sha256") != _hash_without(receipt, "receipt_sha256")
        or receipt.get("receipt_sha256") != details["receipt_sha256"]
    ):
        raise _ExternalEvidenceError("EXTERNAL_EXECUTOR_TERMINAL_RECEIPT_INVALID")


def compute_executor_handoff_hash(document: dict[str, Any]) -> str:
    """Hash the complete closed obligation except the handoff hash itself."""
    clone = json.loads(json.dumps(document, ensure_ascii=False, allow_nan=False))
    handoff = clone.get("executor_handoff")
    if isinstance(handoff, dict):
        handoff.pop("handoff_sha256", None)
    return hashlib.sha256(_canonical_json(clone)).hexdigest()


def _require_exact_keys(value: Any, expected: set[str], label: str, errors: list[str]) -> None:
    if isinstance(value, dict) and set(value) != expected:
        errors.append(f"{label}_CLOSED_SCHEMA_FIELDS_INVALID")


def _validate_executor_handoff(document: dict[str, Any], errors: list[str]) -> None:
    handoff = document.get("executor_handoff")
    if not isinstance(handoff, dict):
        errors.append("EXECUTOR_HANDOFF_MISSING")
        return

    _require_exact_keys(handoff, OBJECT_KEYS["executor_handoff"], "EXECUTOR_HANDOFF", errors)
    if handoff.get("executor_skill_ref") != EXECUTOR_SKILL_REF:
        errors.append("EXECUTOR_HANDOFF_SKILL_REF_INVALID")
    if handoff.get("executor_skill_version") != EXECUTOR_SKILL_VERSION:
        errors.append("EXECUTOR_HANDOFF_SKILL_VERSION_INVALID")
    if handoff.get("input_contract") != EXECUTOR_INPUT_CONTRACT:
        errors.append("EXECUTOR_HANDOFF_INPUT_CONTRACT_INVALID")
    if handoff.get("input_contract_version") != EXECUTOR_INPUT_CONTRACT_VERSION:
        errors.append("EXECUTOR_HANDOFF_INPUT_CONTRACT_VERSION_INVALID")
    if handoff.get("obligation_id") != document.get("obligation_id"):
        errors.append("EXECUTOR_HANDOFF_OBLIGATION_ID_MISMATCH")
    if not EXECUTOR_TICKET_ID.fullmatch(str(handoff.get("executor_ticket_id", ""))):
        errors.append("EXECUTOR_HANDOFF_TICKET_ID_INVALID")
    elif document.get("obligation_id") != handoff.get("executor_ticket_id"):
        errors.append("EXECUTOR_HANDOFF_OBLIGATION_BACKREF_INVALID")
    if not HEX64.fullmatch(str(handoff.get("executor_request_sha256", ""))):
        errors.append("EXECUTOR_HANDOFF_REQUEST_SHA256_INVALID")
    if not _string(handoff.get("executor_queue_ack_ref")):
        errors.append("EXECUTOR_HANDOFF_QUEUE_ACK_REF_MISSING")
    queue_store = document.get("queue_store") if isinstance(document.get("queue_store"), dict) else {}
    expected_ack_ref = (
        f"tickets/{handoff.get('executor_ticket_id')}/events/{EXECUTOR_INITIAL_EVENT_NAME}"
    )
    if handoff.get("executor_queue_ack_ref") != expected_ack_ref:
        errors.append("EXECUTOR_HANDOFF_QUEUE_ACK_REF_INVALID")
    if handoff.get("executor_queue_ack_ref") == queue_store.get("append_only_ack_ref"):
        errors.append("OBLIGATION_AND_EXECUTOR_QUEUE_ACK_MUST_BE_DISTINCT")
    if not HEX64.fullmatch(str(handoff.get("executor_queue_ack_sha256", ""))):
        errors.append("EXECUTOR_HANDOFF_QUEUE_ACK_SHA256_INVALID")
    if handoff.get("activation_state") != "NOT_ACTIVATED_BY_E2_ROUTING":
        errors.append("EXECUTOR_HANDOFF_CANNOT_GRANT_ACTIVATION")
    if handoff.get("responsibilities") != HANDOFF_RESPONSIBILITIES:
        errors.append("EXECUTOR_HANDOFF_RESPONSIBILITIES_INVALID")
    if handoff.get("hash_contract") != HANDOFF_HASH_CONTRACT:
        errors.append("EXECUTOR_HANDOFF_HASH_CONTRACT_INVALID")
    if not HEX64.fullmatch(str(handoff.get("handoff_sha256", ""))):
        errors.append("EXECUTOR_HANDOFF_SHA256_INVALID")
    else:
        try:
            expected_handoff_hash = compute_executor_handoff_hash(document)
        except (TypeError, ValueError, UnicodeError, RecursionError):
            errors.append("EXECUTOR_HANDOFF_CANONICAL_JSON_INVALID")
        else:
            if handoff["handoff_sha256"] != expected_handoff_hash:
                errors.append("EXECUTOR_HANDOFF_SHA256_MISMATCH")

    handoff_state = handoff.get("handoff_state")
    if handoff_state not in HANDOFF_STATES:
        errors.append("EXECUTOR_HANDOFF_STATE_INVALID")
        return

    obligation_state = document.get("state")
    repository = document.get("repository") if isinstance(document.get("repository"), dict) else {}
    source_oid = repository.get("source_oid")
    if obligation_state == "PUSHED_VERIFIED":
        if handoff_state != "TERMINAL_AUTHORITATIVE_RECHECK_REQUIRED":
            errors.append("PUSHED_TERMINAL_RECHECK_HANDOFF_REQUIRED")
        if source_oid == UNRESOLVED:
            errors.append("PUSHED_TERMINAL_SOURCE_CANNOT_BE_UNRESOLVED")
    elif obligation_state in {"CANCELLED_BY_FOUNDER", "SUPERSEDED"}:
        if handoff_state != "NO_E4_ACTION_TERMINAL":
            errors.append("NON_PUSH_TERMINAL_HANDOFF_STATE_INVALID")
    elif source_oid == UNRESOLVED:
        if handoff_state != "WAITING_EXACT_TARGET":
            errors.append("UNRESOLVED_SOURCE_REQUIRES_WAITING_EXACT_TARGET")
        if obligation_state in {"READY_TO_PUSH", "PUSHED_VERIFIED"}:
            errors.append("WAITING_EXACT_TARGET_CANNOT_BE_EXECUTABLE")
        source_closure = document.get("source_closure") if isinstance(document.get("source_closure"), dict) else {}
        unresolved_execution_fields = [
            repository.get("refspec"),
            source_closure.get("commit_oid"),
            source_closure.get("parent_oid"),
            source_closure.get("tree_oid"),
            source_closure.get("reachable_objects_sha256"),
            source_closure.get("reviewed_history_sha256"),
            source_closure.get("test_receipt_ref"),
            source_closure.get("test_receipt_sha256"),
        ]
        if any(value != UNRESOLVED for value in unresolved_execution_fields):
            errors.append("WAITING_EXACT_TARGET_HAS_EXECUTABLE_SOURCE_EVIDENCE")
        schedule = document.get("schedule") if isinstance(document.get("schedule"), dict) else {}
        if schedule.get("executor_lease_ref") is not None or schedule.get("executor_lease_expires_at") is not None:
            errors.append("WAITING_EXACT_TARGET_HAS_EXECUTOR_LEASE")
        blocker = document.get("blocker") if isinstance(document.get("blocker"), dict) else {}
        if blocker.get("code") != "WAITING_EXACT_TARGET":
            errors.append("WAITING_EXACT_TARGET_BLOCKER_INVALID")
        if schedule.get("resume_trigger") != "EXACT_TARGET_COMMIT_AVAILABLE":
            errors.append("WAITING_EXACT_TARGET_RESUME_TRIGGER_INVALID")
    elif handoff_state != "READY_FOR_E4_VALIDATION":
        errors.append("EXACT_SOURCE_REQUIRES_E4_VALIDATION_HANDOFF")


def validate(
    document: Any,
    now: datetime | None = None,
    executor_state_root: Path | None = None,
    executor_queue_trust_config: Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    else:
        current_time = current_time.astimezone(timezone.utc)
    if not isinstance(document, dict):
        return {"state": "HOLD_INVALID_PUSH_OBLIGATION", "errors": ["TOP_LEVEL_OBJECT_REQUIRED"]}

    schema_version = document.get("schema_version")
    legacy_read_only = schema_version in LEGACY_SCHEMAS
    current_schema = schema_version == CURRENT_SCHEMA
    if not current_schema and not legacy_read_only:
        errors.append("SCHEMA_VERSION_INVALID")
    if current_schema:
        _require_exact_keys(document, TOP_LEVEL_KEYS, "TOP_LEVEL", errors)

    for key in (
        "obligation_id",
        "founder_intent_ref",
        "responsible_agent_ref",
        "workloop_ref",
        "identity_root_ref",
        "member_ref",
        "seat_binding_ref",
        "receiver_ref",
    ):
        if not _string(document.get(key)):
            errors.append(f"{key.upper()}_MISSING")
    if not HEX64.fullmatch(str(document.get("founder_intent_sha256", ""))):
        errors.append("FOUNDER_INTENT_SHA256_INVALID")
    if document.get("receiver_ref") != TOTAL_FIELD_RECEIVER:
        errors.append("RECEIVER_REF_INVALID")

    state = document.get("state")
    if state not in STATES:
        errors.append("STATE_INVALID")
    route = document.get("total_field_route")
    if route not in ROUTES:
        errors.append("TOTAL_FIELD_ROUTE_INVALID")

    repository = document.get("repository")
    if not isinstance(repository, dict):
        errors.append("REPOSITORY_OBJECT_REQUIRED")
        repository = {}
    elif current_schema:
        _require_exact_keys(repository, OBJECT_KEYS["repository"], "REPOSITORY", errors)
    if not _string(repository.get("repo_ref")):
        errors.append("REPOSITORY_REF_MISSING")
    if not HEX64.fullmatch(str(repository.get("repository_fingerprint_sha256", ""))):
        errors.append("REPOSITORY_FINGERPRINT_SHA256_INVALID")
    if not isinstance(repository.get("remote_name"), str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", repository["remote_name"]
    ):
        errors.append("REMOTE_NAME_MISSING")
    if not HEX64.fullmatch(str(repository.get("remote_endpoint_sha256", ""))):
        errors.append("REMOTE_ENDPOINT_SHA256_INVALID")
    target_ref = repository.get("target_ref")
    if target_ref != UNRESOLVED and not _target_ref(target_ref):
        errors.append("TARGET_REF_INVALID")
    source_oid = repository.get("source_oid")
    if source_oid != UNRESOLVED and not HEX_OID.fullmatch(str(source_oid or "")):
        errors.append("SOURCE_OID_INVALID")
    expected_remote_old_oid = repository.get("expected_remote_old_oid")
    if expected_remote_old_oid != UNRESOLVED and not HEX_OID.fullmatch(str(expected_remote_old_oid or "")):
        errors.append("EXPECTED_REMOTE_OLD_OID_INVALID")
    if repository.get("object_format") not in {"sha1", "sha256"}:
        errors.append("OBJECT_FORMAT_INVALID")
    expected_oid_length = 40 if repository.get("object_format") == "sha1" else 64
    for field in ("source_oid", "expected_remote_old_oid"):
        if _string(repository.get(field)) and repository[field] != UNRESOLVED and len(repository[field]) != expected_oid_length:
            errors.append(f"{field.upper()}_FORMAT_MISMATCH")
    expected_refspec = (
        f"{source_oid}:{target_ref}"
        if source_oid != UNRESOLVED and target_ref != UNRESOLVED and _string(source_oid) and _string(target_ref)
        else UNRESOLVED
    )
    if repository.get("refspec") != expected_refspec:
        errors.append("REFSPEC_INVALID")

    source_closure = document.get("source_closure")
    if not isinstance(source_closure, dict):
        errors.append("SOURCE_CLOSURE_OBJECT_REQUIRED")
        source_closure = {}
    elif current_schema:
        _require_exact_keys(source_closure, OBJECT_KEYS["source_closure"], "SOURCE_CLOSURE", errors)
    if source_closure.get("commit_oid") != source_oid:
        errors.append("SOURCE_COMMIT_OID_MISMATCH")
    for field in ("parent_oid", "tree_oid"):
        if source_closure.get(field) != UNRESOLVED and not HEX_OID.fullmatch(str(source_closure.get(field, ""))):
            errors.append(f"SOURCE_{field.upper()}_INVALID")
    for field in ("reachable_objects_sha256", "reviewed_history_sha256"):
        if source_closure.get(field) != UNRESOLVED and not HEX64.fullmatch(str(source_closure.get(field, ""))):
            errors.append(f"SOURCE_{field.upper()}_INVALID")
    if not _string(source_closure.get("test_receipt_ref")):
        errors.append("SOURCE_TEST_RECEIPT_REF_MISSING")
    test_receipt_sha256 = source_closure.get("test_receipt_sha256")
    if test_receipt_sha256 != UNRESOLVED and not HEX64.fullmatch(str(test_receipt_sha256 or "")):
        errors.append("SOURCE_TEST_RECEIPT_SHA256_INVALID")

    scope_state = document.get("change_scope_state")
    if scope_state not in {"UNRESOLVED_REQUIRES_DISCOVERY", "RESOLVED_HASH_BOUND"}:
        errors.append("CHANGE_SCOPE_STATE_INVALID")
    changes = document.get("changes")
    if not isinstance(changes, list):
        errors.append("CHANGES_ARRAY_REQUIRED")
        changes = []
    seen_paths: set[str] = set()
    for item in changes:
        if not isinstance(item, dict):
            errors.append("CHANGE_OBJECT_INVALID")
            continue
        if current_schema:
            _require_exact_keys(item, {"status", "path", "sha256"}, "CHANGE", errors)
        path = item.get("path")
        if not _safe_path(path):
            errors.append("CHANGE_PATH_INVALID")
        elif path in seen_paths:
            errors.append("CHANGE_PATH_DUPLICATE")
        else:
            seen_paths.add(path)
        if item.get("status") not in {"A", "M", "D", "T"}:
            errors.append("CHANGE_STATUS_INVALID")
        if not HEX64.fullmatch(str(item.get("sha256", ""))):
            errors.append("CHANGE_SHA256_INVALID")
    if changes and changes != sorted(
        changes,
        key=lambda item: (
            str(item.get("path", "")) if isinstance(item, dict) else "",
            str(item.get("status", "")) if isinstance(item, dict) else "",
            str(item.get("sha256", "")) if isinstance(item, dict) else "",
        ),
    ):
        errors.append("CHANGES_CANONICAL_ORDER_INVALID")
    if scope_state == "RESOLVED_HASH_BOUND":
        if not changes:
            errors.append("RESOLVED_SCOPE_REQUIRES_CHANGES")
        if not HEX64.fullmatch(str(document.get("change_set_sha256", ""))):
            errors.append("CHANGE_SET_SHA256_INVALID")
        else:
            try:
                expected_change_set = hashlib.sha256(_canonical_json(changes)).hexdigest()
            except (TypeError, ValueError, UnicodeError, RecursionError):
                errors.append("CHANGE_SET_CANONICAL_JSON_INVALID")
            else:
                if document.get("change_set_sha256") != expected_change_set:
                    errors.append("CHANGE_SET_SHA256_MISMATCH")
    elif document.get("change_set_sha256") != UNRESOLVED:
        errors.append("UNRESOLVED_SCOPE_CHANGE_SET_MUST_BE_UNRESOLVED")

    queue_store = document.get("queue_store")
    if not isinstance(queue_store, dict):
        errors.append("QUEUE_STORE_OBJECT_REQUIRED")
        queue_store = {}
    elif current_schema:
        _require_exact_keys(queue_store, OBJECT_KEYS["queue_store"], "QUEUE_STORE", errors)
    for field in ("store_ref", "idempotency_key", "append_only_ack_ref"):
        if not _string(queue_store.get(field)):
            errors.append(f"QUEUE_{field.upper()}_MISSING")
    if not HEX64.fullmatch(str(queue_store.get("append_only_ack_sha256", ""))):
        errors.append("QUEUE_APPEND_ONLY_ACK_SHA256_INVALID")
    if queue_store.get("outside_target_repo") is not True:
        errors.append("QUEUE_STORE_MUST_SURVIVE_UNPUSHED_REPO")

    blocker = document.get("blocker")
    if not isinstance(blocker, dict):
        errors.append("BLOCKER_OBJECT_REQUIRED")
        blocker = {}
    elif current_schema:
        _require_exact_keys(blocker, OBJECT_KEYS["blocker"], "BLOCKER", errors)
    if not _string(blocker.get("code")) or not _string(blocker.get("evidence_ref")):
        errors.append("BLOCKER_EVIDENCE_INCOMPLETE")
    repair_plan = blocker.get("repair_plan")
    if not isinstance(repair_plan, list) or not repair_plan or not all(_string(x) for x in repair_plan):
        errors.append("REPAIR_PLAN_REQUIRED")
    if not isinstance(blocker.get("automation_possible"), bool):
        errors.append("AUTOMATION_BOUNDARY_REQUIRED")

    schedule = document.get("schedule")
    if not isinstance(schedule, dict):
        errors.append("SCHEDULE_OBJECT_REQUIRED")
        schedule = {}
    elif current_schema:
        _require_exact_keys(schedule, OBJECT_KEYS["schedule"], "SCHEDULE", errors)
    scheduler_state = schedule.get("scheduler_state")
    if scheduler_state not in SCHEDULER_STATES:
        errors.append("SCHEDULER_STATE_INVALID")
    if not _timestamp(schedule.get("created_at")):
        errors.append("CREATED_AT_INVALID")
    if state not in TERMINAL_STATES and not _timestamp(schedule.get("next_attempt_at")):
        errors.append("NEXT_ATTEMPT_AT_REQUIRED")
    if not _timestamp(schedule.get("deadline_at")):
        errors.append("DEADLINE_AT_INVALID")
    if not _string(schedule.get("resume_trigger")):
        errors.append("RESUME_TRIGGER_REQUIRED")
    if not _safe_int(schedule.get("attempt_count")):
        errors.append("ATTEMPT_COUNT_INVALID")
    retries = schedule.get("max_auto_attempts")
    if not _safe_int(retries, 1) or not retries <= 10:
        errors.append("MAX_AUTO_ATTEMPTS_INVALID")
    if scheduler_state == "ACTIVE_DURABLE_SCHEDULER" and not _string(schedule.get("scheduler_job_ref")):
        errors.append("ACTIVE_SCHEDULER_JOB_REF_REQUIRED")
    if state in TERMINAL_STATES and scheduler_state != "TERMINAL":
        errors.append("TERMINAL_STATE_REQUIRES_TERMINAL_SCHEDULER")
    if state not in TERMINAL_STATES and scheduler_state == "TERMINAL":
        errors.append("OPEN_STATE_CANNOT_HAVE_TERMINAL_SCHEDULER")
    created_at = _parse_canonical_time(schedule.get("created_at"))
    next_attempt_at = _parse_canonical_time(schedule.get("next_attempt_at"))
    deadline_at = _parse_canonical_time(schedule.get("deadline_at"))
    if created_at is not None and deadline_at is not None and created_at > deadline_at:
        errors.append("SCHEDULE_TIME_ORDER_INVALID")
    if (
        next_attempt_at is not None
        and created_at is not None
        and deadline_at is not None
        and not (created_at <= next_attempt_at <= deadline_at)
    ):
        errors.append("SCHEDULE_TIME_ORDER_INVALID")
    lease_ref = schedule.get("executor_lease_ref")
    lease_expires_raw = schedule.get("executor_lease_expires_at")
    lease_expires = _parse_canonical_time(lease_expires_raw)
    if (lease_ref is None) != (lease_expires_raw is None):
        errors.append("EXECUTOR_LEASE_PAIR_INVALID")
    if lease_ref is not None:
        if not _string(lease_ref) or lease_expires is None:
            errors.append("EXECUTOR_LEASE_INVALID")
        elif state == "READY_TO_PUSH" and lease_expires <= current_time:
            errors.append("EXECUTOR_LEASE_EXPIRED")

    authorization = document.get("authorization")
    if not isinstance(authorization, dict):
        errors.append("AUTHORIZATION_OBJECT_REQUIRED")
        authorization = {}
    elif current_schema:
        _require_exact_keys(authorization, OBJECT_KEYS["authorization"], "AUTHORIZATION", errors)
    if not isinstance(authorization.get("required"), bool):
        errors.append("AUTHORIZATION_REQUIRED_FLAG_INVALID")
    authorization_receipt = authorization.get("authorization_ref")
    authorization_expiry_raw = authorization.get("authorization_expires_at")
    authorization_expiry = _parse_canonical_time(authorization_expiry_raw)
    if (authorization_receipt is None) != (authorization_expiry_raw is None):
        errors.append("AUTHORIZATION_RECEIPT_EXPIRY_PAIR_INVALID")
    if authorization_receipt is not None:
        if not _string(authorization_receipt) or authorization_expiry is None:
            errors.append("AUTHORIZATION_RECEIPT_WINDOW_INVALID")
        elif state == "READY_TO_PUSH" and authorization_expiry <= current_time:
            errors.append("AUTHORIZATION_RECEIPT_EXPIRED")
    decision_tuple = (
        authorization.get("decision_ref"),
        authorization.get("decision_receipt_sha256"),
        authorization.get("decision_expires_at"),
    )
    if any(value is not None for value in decision_tuple) and not all(value is not None for value in decision_tuple):
        errors.append("DECISION_RECEIPT_TUPLE_INVALID")
    decision_expiry = _parse_canonical_time(authorization.get("decision_expires_at"))
    if all(value is not None for value in decision_tuple) and (
        not _string(decision_tuple[0])
        or not HEX64.fullmatch(str(decision_tuple[1]))
        or decision_expiry is None
    ):
        errors.append("DECISION_RECEIPT_INVALID")
    if not HEX64.fullmatch(str(authorization.get("scope_sha256", ""))):
        errors.append("AUTHORIZATION_SCOPE_SHA256_INVALID")
    if state == "READY_TO_PUSH":
        if authorization.get("required") is not True:
            errors.append("READY_TO_PUSH_AUTHORIZATION_REQUIRED_MUST_BE_TRUE")
        if not _string(authorization_receipt) or authorization_expiry is None:
            errors.append("READY_TO_PUSH_AUTHORIZATION_RECEIPT_MISSING")
        if not all(value is not None for value in decision_tuple) or decision_expiry is None:
            errors.append("READY_TO_PUSH_DECISION_RECEIPT_MISSING")
        elif decision_expiry <= current_time:
            errors.append("READY_TO_PUSH_DECISION_RECEIPT_EXPIRED")
        unresolved_refs = [
            document.get("identity_root_ref"),
            document.get("seat_binding_ref"),
            document.get("receiver_ref"),
            target_ref,
            source_oid,
            expected_remote_old_oid,
            source_closure.get("parent_oid"),
            source_closure.get("tree_oid"),
            source_closure.get("reachable_objects_sha256"),
            source_closure.get("reviewed_history_sha256"),
        ]
        if scope_state != "RESOLVED_HASH_BOUND" or UNRESOLVED in unresolved_refs:
            errors.append("READY_TO_PUSH_HAS_UNRESOLVED_PREREQUISITE")
        if scheduler_state != "ACTIVE_DURABLE_SCHEDULER":
            errors.append("READY_TO_PUSH_REQUIRES_ACTIVE_SCHEDULER")
        if not _string(lease_ref) or lease_expires is None:
            errors.append("READY_TO_PUSH_EXECUTOR_LEASE_MISSING")

    safety = document.get("safety")
    expected_safety = {
        "fast_forward_only": True,
        "force_push": False,
        "delete_ref": False,
        "push_tags": False,
        "multiple_refs": False,
        "recurse_submodules": False,
        "history_rewrite": False,
        "include_unrelated_dirty_files": False,
        "remote_readback_required": True,
    }
    if not isinstance(safety, dict):
        errors.append("SAFETY_OBJECT_REQUIRED")
    else:
        if current_schema:
            _require_exact_keys(safety, OBJECT_KEYS["safety"], "SAFETY", errors)
        for key, expected in expected_safety.items():
            if safety.get(key) is not expected:
                errors.append(f"SAFETY_{key.upper()}_INVALID")
        if not isinstance(safety.get("stop_conditions"), list) or not safety.get("stop_conditions"):
            errors.append("STOP_CONDITIONS_REQUIRED")
        if not _string(safety.get("rollback")):
            errors.append("ROLLBACK_REQUIRED")
        effects = safety.get("push_effects")
        if not isinstance(effects, dict):
            errors.append("PUSH_EFFECTS_OBJECT_REQUIRED")
        else:
            if current_schema:
                _require_exact_keys(effects, OBJECT_KEYS["push_effects"], "PUSH_EFFECTS", errors)
            allowed_effect_states = {"DISABLED", "NOT_USED", "REVIEWED_AUTHORIZED"}
            for field in ("pre_push_hooks", "git_lfs", "ci_webhook_deploy"):
                if effects.get(field) not in allowed_effect_states:
                    errors.append(f"PUSH_EFFECT_{field.upper()}_UNRESOLVED")

    closure = document.get("closure")
    if not isinstance(closure, dict):
        errors.append("CLOSURE_OBJECT_REQUIRED")
        closure = {}
    elif current_schema:
        expected_closure_keys: set[str] = set()
        if state == "PUSHED_VERIFIED":
            expected_closure_keys = {"remote_commit_oid", "remote_readback_receipt_ref"}
        elif state == "CANCELLED_BY_FOUNDER":
            expected_closure_keys = {"founder_cancel_receipt_ref"}
        elif state == "SUPERSEDED":
            expected_closure_keys = {"superseding_obligation_ref"}
        _require_exact_keys(closure, expected_closure_keys, "CLOSURE", errors)
    if state == "PUSHED_VERIFIED":
        if not HEX_OID.fullmatch(str(closure.get("remote_commit_oid", ""))):
            errors.append("PUSHED_REMOTE_COMMIT_OID_INVALID")
        if not _string(closure.get("remote_readback_receipt_ref")):
            errors.append("PUSHED_REMOTE_READBACK_RECEIPT_MISSING")
        if closure.get("remote_commit_oid") != source_oid:
            errors.append("PUSHED_REMOTE_OID_NOT_SOURCE_OID")
    elif state == "CANCELLED_BY_FOUNDER":
        if not _string(closure.get("founder_cancel_receipt_ref")):
            errors.append("FOUNDER_CANCEL_RECEIPT_MISSING")
    elif state == "SUPERSEDED":
        if not _string(closure.get("superseding_obligation_ref")):
            errors.append("SUPERSEDING_OBLIGATION_REF_MISSING")

    if current_schema:
        _validate_executor_handoff(document, errors)

    if _contains_secret_shape(document):
        errors.append("SECRET_SHAPED_FIELD_FORBIDDEN")

    if legacy_read_only:
        errors.extend(["EXECUTOR_HANDOFF_MIGRATION_REQUIRED", "LEGACY_SCHEMA_READ_ONLY"])
        return {
            "state": "HOLD_LEGACY_PUSH_OBLIGATION_MIGRATION_REQUIRED",
            "obligation_state": state,
            "legacy_validation": "PASS_LEGACY_READ_ONLY" if len(errors) == 2 else "HOLD_INVALID_LEGACY_OBLIGATION",
            "migration_target_schema": CURRENT_SCHEMA,
            "execution_routed": False,
            "errors": sorted(set(errors)),
        }

    if errors:
        return {
            "state": "HOLD_INVALID_PUSH_OBLIGATION",
            "obligation_state": state,
            "execution_routed": False,
            "errors": sorted(set(errors)),
        }

    if executor_state_root is None or executor_queue_trust_config is None:
        return {
            "state": "HOLD_TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE",
            "obligation_state": state,
            "execution_routed": state == "PUSHED_VERIFIED",
            "executor_queue_ack_verified": False,
            "obligation_queue_ack_verified": False,
            "terminal_readback_verified": False if state == "PUSHED_VERIFIED" else None,
            "errors": ["TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE"],
        }

    try:
        trust = _read_executor_queue_trust_config(
            executor_queue_trust_config,
            executor_state_root,
            current_time,
        )
    except _ExternalEvidenceError as exc:
        return {
            "state": "HOLD_TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE",
            "obligation_state": state,
            "execution_routed": state == "PUSHED_VERIFIED",
            "executor_queue_ack_verified": False,
            "obligation_queue_ack_verified": False,
            "terminal_readback_verified": False if state == "PUSHED_VERIFIED" else None,
            "errors": [exc.code, "TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE"],
        }

    try:
        evidence = _load_external_executor_evidence(executor_state_root, document, trust)
    except _ExternalEvidenceError as exc:
        if state == "PUSHED_VERIFIED":
            return {
                "state": "HOLD_EXTERNAL_EXECUTOR_TERMINAL_UNVERIFIED",
                "obligation_state": state,
                "execution_routed": True,
                "executor_queue_ack_verified": False,
                "obligation_queue_ack_verified": False,
                "terminal_readback_verified": False,
                "errors": [exc.code, "TERMINAL_AUTHORITATIVE_RECHECK_REQUIRED"],
            }
        return {
            "state": "HOLD_EXTERNAL_EXECUTOR_ACK_INVALID",
            "obligation_state": state,
            "execution_routed": False,
            "executor_queue_ack_verified": False,
            "obligation_queue_ack_verified": False,
            "errors": [exc.code],
        }

    if state == "PUSHED_VERIFIED":
        try:
            _validate_external_terminal_receipt(executor_state_root, document, evidence, trust)
        except _ExternalEvidenceError as exc:
            return {
                "state": "HOLD_EXTERNAL_EXECUTOR_TERMINAL_UNVERIFIED",
                "obligation_state": state,
                "execution_routed": True,
                "executor_queue_ack_verified": True,
                "obligation_queue_ack_verified": True,
                "terminal_readback_verified": False,
                "errors": [exc.code, "TERMINAL_AUTHORITATIVE_RECHECK_REQUIRED"],
            }
        # The E2 verifier deliberately does not reproduce the executor's full
        # authority lease, reservation/final-validation/consume ACK continuity,
        # server CAS, protected-state, and live remote state machine.  These
        # static bytes establish integrity coordinates only, never a verified
        # historical delivery or current closure.
        return {
            "state": "HOLD_EXTERNAL_EXECUTOR_TERMINAL_UNVERIFIED",
            "obligation_state": state,
            "execution_routed": True,
            "executor_queue_ack_verified": True,
            "obligation_queue_ack_verified": True,
            "terminal_receipt_integrity_loaded": True,
            "terminal_readback_verified": False,
            "errors": [
                "EXTERNAL_EXECUTOR_TERMINAL_SEMANTICS_UNVERIFIED",
                "TERMINAL_AUTHORITATIVE_RECHECK_REQUIRED",
            ],
        }

    if state == "READY_TO_PUSH":
        return {
            "state": "HOLD_EXTERNAL_EXECUTOR_STATE_UNVERIFIED",
            "obligation_state": state,
            "execution_routed": True,
            "executor_queue_ack_verified": True,
            "obligation_queue_ack_verified": True,
            "errors": ["CURRENT_EXECUTOR_AUTHORITY_AND_LEASE_RECHECK_REQUIRED"],
        }
    if state in {"CANCELLED_BY_FOUNDER", "SUPERSEDED"}:
        return {
            "state": "HOLD_EXTERNAL_EXECUTOR_TERMINAL_UNVERIFIED",
            "obligation_state": state,
            "execution_routed": False,
            "executor_queue_ack_verified": True,
            "obligation_queue_ack_verified": True,
            "errors": ["EXTERNAL_EXECUTOR_TERMINAL_EVIDENCE_REQUIRED"],
        }

    return {
        "state": "PASS_DEFERRED_PUSH_OBLIGATION",
        "obligation_state": state,
        "execution_routed": True,
        "execution_authorized": False,
        "executor_queue_ack_verified": True,
        "obligation_queue_ack_verified": True,
        "handoff_state": document["executor_handoff"]["handoff_state"],
        "errors": [],
    }


def _read_cli_obligation(path: Path) -> dict[str, Any]:
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as exc:
        raise _ExternalEvidenceError("INPUT_READ_FAILED") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid not in {0, os.geteuid()}
            or before.st_nlink != 1
            or stat.S_IMODE(before.st_mode) & 0o022
            or before.st_size > 16 * 1024 * 1024
        ):
            raise _ExternalEvidenceError("INPUT_FILE_UNSAFE")
        raw = b""
        while len(raw) <= 16 * 1024 * 1024:
            chunk = os.read(descriptor, min(1024 * 1024, 16 * 1024 * 1024 + 1 - len(raw)))
            if not chunk:
                break
            raw += chunk
        after = os.fstat(descriptor)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ) or len(raw) != after.st_size or len(raw) > 16 * 1024 * 1024:
            raise _ExternalEvidenceError("INPUT_FILE_CHANGED_OR_TOO_LARGE")
    finally:
        os.close(descriptor)
    try:
        document = _decode_json(raw)
    except (UnicodeError, json.JSONDecodeError, ValueError, TypeError, RecursionError) as exc:
        raise _ExternalEvidenceError("INPUT_JSON_INVALID_OR_DUPLICATE_KEY") from exc
    if not isinstance(document, dict):
        raise _ExternalEvidenceError("TOP_LEVEL_OBJECT_REQUIRED")
    try:
        canonical = _canonical_json(document) + b"\n"
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise _ExternalEvidenceError("INPUT_CANONICAL_JSON_INVALID") from exc
    if raw != canonical:
        raise _ExternalEvidenceError("INPUT_BYTES_NOT_CANONICAL_JSON")
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("obligation", type=Path)
    parser.add_argument(
        "--executor-state-root",
        type=Path,
        help="Exact complete-deferred-git-push queue root selected by the root-issued trust config.",
    )
    parser.add_argument(
        "--executor-queue-trust-config",
        type=Path,
        help="Canonical root-owned config that activates one exact nonroot executor queue inode.",
    )
    args = parser.parse_args()
    try:
        document = _read_cli_obligation(args.obligation)
    except _ExternalEvidenceError as exc:
        print(
            json.dumps(
                {"state": "HOLD_INVALID_PUSH_OBLIGATION", "errors": [exc.code]},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 1
    result = validate(
        document,
        executor_state_root=args.executor_state_root,
        executor_queue_trust_config=args.executor_queue_trust_config,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["state"] == "PASS_DEFERRED_PUSH_OBLIGATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
