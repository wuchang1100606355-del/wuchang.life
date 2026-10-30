#!/usr/bin/env python3
"""Behavior tests for the 8D ADI Git index skill helpers."""

from __future__ import annotations

import base64
import grp
import hashlib
import json
import os
import pwd
import stat
import subprocess
import struct
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import validate_deferred_push as deferred_push_module
from validate_deferred_push import (
    _ExternalEvidenceError,
    _executor_execution_scope,
    _open_private_directory_at,
    _open_trusted_state_root,
    _parse_capability_status,
    _read_executor_queue_trust_config,
    _read_private_file_at,
    _read_process_capabilities,
    compute_executor_origin_envelope_sha256,
    compute_executor_handoff_payload_hash,
    compute_executor_handoff_hash,
    compute_obligation_core_hash,
    compute_obligation_effect_scope_hash,
    validate as validate_deferred_push,
)
from git_review_gate import classify
from validate_git_index import compute_event_hash, validate


HEX40 = "1" * 40
HEX64 = "2" * 64
QUEUE_OWNER = pwd.getpwnam("nobody")
QUEUE_OWNER_UID = QUEUE_OWNER.pw_uid
QUEUE_OWNER_USERNAME = QUEUE_OWNER.pw_name
VALIDATOR_ACCOUNT = pwd.getpwnam("daemon")
VALIDATOR_UID = VALIDATOR_ACCOUNT.pw_uid
VALIDATOR_USERNAME = VALIDATOR_ACCOUNT.pw_name
READER_GROUP = grp.getgrgid(VALIDATOR_ACCOUNT.pw_gid)
READER_GID = READER_GROUP.gr_gid
READER_GROUP_NAME = READER_GROUP.gr_name
UNIT_VALIDATOR_UID = VALIDATOR_UID
ARBITRARY_READER_UID = next(
    account.pw_uid
    for account in pwd.getpwall()
    if account.pw_uid not in {0, QUEUE_OWNER_UID, VALIDATOR_UID}
)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def hash_without(value: dict, field: str) -> str:
    clone = dict(value)
    clone.pop(field, None)
    return hashlib.sha256(canonical_bytes(clone)).hexdigest()


def valid_packet() -> dict:
    packet = {
        "schema_version": "w7tp-8d-git-index/1.0",
        "packet_id": "packet-1",
        "packet_decision_index": "decision-1",
        "identity_root_ref": "identity-1",
        "seat_binding_ref": "seat-1",
        "receiver": {"id": "receiver-1", "version": "1.0.0"},
        "event": {
            "logical_time": 1,
            "prev_event_hash": None,
            "event_hash": "",
            "hash_contract": "SHA256_CANONICAL_JSON_EXCLUDING_EVENT_HASH_V1",
            "nonce": "nonce-1",
            "replay_guard_ref": "replay-registry-1",
            "expiry": "2099-08-27T00:00:00Z",
        },
        "D1": {"intent_ref": "intent-1", "operation": "LOOKUP"},
        "D2": {"repo_namespace": "repo-1", "object_format": "sha1", "object_type": "blob", "expected_size": 1, "expected_git_oid": HEX40, "acceptance": "EXACT_BYTES"},
        "D3": {"base_commit_oid": HEX40, "base_tree_oid": HEX40, "path_bytes_b64": "YQ==", "file_mode": "100644", "lineage_event_ref": "lineage-1"},
        "D4": {"source_object_oids": [HEX40], "source_manifest_sha256": HEX64, "reconstruction_receipt_ref": None},
        "D5": {"policy": "READ_ONLY_LOOKUP", "abort_conditions": ["MISSING_LOOKUP_CLOSURE"]},
        "D6": {"rule_refs": [{"ref": "rule-1", "sha256": HEX64}], "lookup_closure": [{"ref": "base-1", "sha256": HEX64}], "acceptance": "EXACT_BYTES", "verification_instruction": "GIT_NATIVE_OID_TYPE_SIZE_AND_CONNECTIVITY"},
        "D7": {"missing_prerequisite": "QUARANTINE", "max_reconstruction_depth": 16, "max_output_bytes": 1024},
        "D8": {"authority": "CANDIDATE_ONLY", "allowed_ref_prefix": "refs/adi/candidates/", "canonical_write": False, "promotion_receipt_required": True},
    }
    packet["event"]["event_hash"] = compute_event_hash(packet)
    return packet


def executor_request_for(document: dict) -> dict:
    repository = document["repository"]
    repo_root = repository["repo_ref"] if str(repository["repo_ref"]).startswith("/") else "/tmp/example-repository"
    git_common_dir = f"{repo_root}/.git"
    source = repository["source_oid"]
    waiting = source == "UNKNOWN_UNVERIFIED"
    change_manifest = [] if waiting else [
        {
            "path": item["path"],
            "status": item["status"],
            "old": None,
            "new": {
                "mode": "100644",
                "object_type": "blob",
                "git_oid": "5" * 40,
                "content_sha256": item["sha256"],
                "size": 1,
            },
        }
        for item in document["changes"]
    ]
    commit_range = [] if waiting else [source]
    causal_groups = [] if waiting else [{
        "sequence": 1,
        "parent_commit_oid": document["source_closure"]["parent_oid"],
        "commit_oid": source,
        "commit_tree_oid": document["source_closure"]["tree_oid"],
        "changed_paths": [item["path"] for item in document["changes"]],
        "change_manifest": change_manifest,
        "change_scope_sha256": hashlib.sha256(canonical_bytes(change_manifest)).hexdigest(),
    }]
    git = {
        "source_state": "WAITING_EXACT_TARGET" if waiting else "EXACT_COMMIT_LOCKED",
        "source_commit_oid": None if waiting else source,
        "source_tree_oid": None if waiting else document["source_closure"]["tree_oid"],
        "source_parent_oids": [] if waiting else [document["source_closure"]["parent_oid"]],
        "reachable_object_closure_sha256": None if waiting else document["source_closure"]["reachable_objects_sha256"],
        "reachable_object_count": None if waiting else 3,
        "expected_remote_old_oid": repository["expected_remote_old_oid"],
        "changed_paths": [] if waiting else [item["path"] for item in document["changes"]],
        "change_manifest": change_manifest,
        "change_scope_sha256": None if waiting else hashlib.sha256(canonical_bytes(change_manifest)).hexdigest(),
        "commit_range_oids": commit_range,
        "commit_range_sha256": None if waiting else hashlib.sha256(canonical_bytes(commit_range)).hexdigest(),
        "causal_groups": causal_groups,
        "causal_group_changed_paths": [] if waiting else sorted(item["path"] for item in document["changes"]),
        "causal_group_dependency_order": [] if waiting else [source],
        "causal_group_combined_sha256": None if waiting else hashlib.sha256(canonical_bytes(causal_groups)).hexdigest(),
        "authority_sensitive_paths": [],
        "target_ref": repository["target_ref"],
        "refspec": None if waiting else repository["refspec"],
        "bounded_paths": [] if waiting else sorted(item["path"] for item in document["changes"]),
        "fast_forward_only": True,
        "force_allowed": False,
        "non_fast_forward_allowed": False,
        "exact_server_cas_required": True,
        "server_cas_expected_old_oid": repository["expected_remote_old_oid"],
        "delete_allowed": False,
        "tags_allowed": False,
        "multi_ref_allowed": False,
    }
    config_keys_sha = "f" * 64
    config_values_sha = "0" * 64
    repository_fingerprint = hashlib.sha256(canonical_bytes({
        "contract": "git-repository-location/v1",
        "repo_root": repo_root,
        "git_common_dir": git_common_dir,
        "object_format": repository["object_format"],
        "local_config_keys_sha256": config_keys_sha,
        "local_config_values_sha256": config_values_sha,
    })).hexdigest()
    request = {
        "schema_version": "w7tp-deferred-git-push-request/1.0",
        "origin_intent_sha256": compute_executor_origin_envelope_sha256(document),
        "responsible_agent_ref": "codex:complete-deferred-git-push",
        "repository": {
            "root": repo_root,
            "git_common_dir": git_common_dir,
            "fingerprint_sha256": repository_fingerprint,
            "object_format": repository["object_format"],
            "local_config_key_count": 0,
            "local_config_keys_sha256": config_keys_sha,
            "local_config_values_sha256": config_values_sha,
        },
        "remote": {
            "name": repository["remote_name"],
            "endpoint_fingerprint_sha256": repository["remote_endpoint_sha256"],
            "file_repository_identity": None,
        },
        "git": git,
        "authorization": {
            "ref": document["authorization"]["authorization_ref"],
            "expires_at": document["authorization"]["authorization_expires_at"],
            "required_scope_sha256": "",
            "total_field_decision_ref": document["authorization"]["decision_ref"],
            "total_field_decision_expires_at": document["authorization"]["decision_expires_at"],
            "total_field_scope_sha256": (
                document["authorization"]["scope_sha256"]
                if document["authorization"]["decision_ref"] is not None
                else None
            ),
            "decision_receipt": None,
            "receiver_activation": None,
            "single_use": True,
        },
        "effects": {
            "ci_or_deploy": {
                "NOT_USED": "NO_CI_OR_DEPLOY_EFFECT",
                "REVIEWED_AUTHORIZED": "AUTHORIZED_CI_OR_DEPLOY_EFFECT",
            }[document["safety"]["push_effects"]["ci_webhook_deploy"]],
            "hook": "REQUIRE_ABSENT",
            "lfs": "REQUIRE_ABSENT",
            "submodule_recursive_push": "DENIED",
            "tags": "DENIED",
        },
        "supersedes_ticket_id": None,
        "scheduler_state": "HANDOFF_RESUME_REQUIRED",
        "ticket_id": "",
        "obligation_id": "",
        "idempotency_key": "",
        "executable_envelope_sha256": "",
        "created_at": "2026-08-27T00:00:00Z",
        "hash_contract": "SHA256_CANONICAL_JSON_EXCLUDING_OWN_HASH_V1",
        "request_sha256": "",
    }
    request["authorization"]["required_scope_sha256"] = _executor_execution_scope(request)
    identity = dict(request)
    for field in (
        "ticket_id", "obligation_id", "idempotency_key", "executable_envelope_sha256",
        "created_at", "hash_contract", "request_sha256",
    ):
        identity.pop(field)
    identity_sha = hashlib.sha256(canonical_bytes(identity)).hexdigest()
    ticket_id = "dgp-" + identity_sha
    request["ticket_id"] = ticket_id
    request["obligation_id"] = ticket_id
    request["idempotency_key"] = identity_sha
    request["executable_envelope_sha256"] = hashlib.sha256(canonical_bytes({
        "contract": "w7tp-deferred-git-executable-envelope/1.0",
        "ticket_id": ticket_id,
        "idempotency_key": identity_sha,
    })).hexdigest()
    request["request_sha256"] = hash_without(request, "request_sha256")
    return request


def initial_executor_event(request: dict) -> dict:
    event = {
        "schema_version": "w7tp-deferred-git-push-event/1.0",
        "hash_contract": "SHA256_CANONICAL_JSON_EXCLUDING_OWN_HASH_V1",
        "ticket_id": request["ticket_id"],
        "sequence": 1,
        "occurred_at": "2026-08-27T00:00:00Z",
        "kind": "ENQUEUED",
        "state": "WAITING_EXACT_TARGET" if request["git"]["source_state"] == "WAITING_EXACT_TARGET" else "WAITING_AUTHORIZATION",
        "next_attempt_at": None,
        "prev_event_hash": None,
        "details": {
            "request_sha256": request["request_sha256"],
            "queue_ack": "DURABLE_EXTERNAL_QUEUE_ACK",
            "background_scheduler_active": False,
        },
        "event_sha256": "",
    }
    event["event_sha256"] = hash_without(event, "event_sha256")
    return event


def bind_executor_handoff(document: dict) -> tuple[dict, dict]:
    request = executor_request_for(document)
    event = initial_executor_event(request)
    ticket = request["ticket_id"]
    document["obligation_id"] = ticket
    document["repository"]["repository_fingerprint_sha256"] = request["repository"]["fingerprint_sha256"]
    document["authorization"]["scope_sha256"] = request["authorization"]["required_scope_sha256"]
    document["queue_store"].update({
        "store_ref": "trusted-executor-queue:" + "0" * 64,
        "idempotency_key": request["idempotency_key"],
        "append_only_ack_ref": f"e2-obligation-acks/{ticket}.json",
        "append_only_ack_sha256": "0" * 64,
        "outside_target_repo": True,
    })
    handoff = document["executor_handoff"]
    handoff.update({
        "obligation_id": ticket,
        "executor_ticket_id": ticket,
        "executor_request_sha256": request["request_sha256"],
        "executor_queue_ack_ref": f"tickets/{ticket}/events/00000000000000000001.json",
        "executor_queue_ack_sha256": event["event_sha256"],
    })
    handoff["handoff_sha256"] = compute_executor_handoff_hash(document)
    return request, event


def trust_config_path(root: Path) -> Path:
    return root.parent / f"{root.name}-queue-trust-config.json"


def _chown_queue_tree(root: Path) -> bool:
    try:
        for path in [root, *root.rglob("*")]:
            os.chown(path, QUEUE_OWNER_UID, READER_GID)
            path.chmod(0o750 if path.is_dir() else 0o440)
    except OSError as exc:
        return False
    return True


def _write_queue_trust_config(root: Path) -> tuple[Path, dict]:
    root_info = root.stat()
    parent = root.parent.resolve(strict=True)
    parent_info = parent.stat()
    config = {
        "schema_version": "w7tp-e2-executor-queue-trust-config/1.1",
        "state_root_parent_realpath": os.fspath(parent),
        "state_root_parent_device": parent_info.st_dev,
        "state_root_parent_inode": parent_info.st_ino,
        "state_root_parent_mode": f"0{stat.S_IMODE(parent_info.st_mode):03o}",
        "state_root_basename": root.name,
        "state_root_realpath": os.fspath(root.resolve(strict=True)),
        "state_root_device": root_info.st_dev,
        "state_root_inode": root_info.st_ino,
        "state_root_mode": f"0{stat.S_IMODE(root_info.st_mode):03o}",
        "expected_nonroot_owner_uid": QUEUE_OWNER_UID,
        "expected_nonroot_owner_username": QUEUE_OWNER_USERNAME,
        "expected_validator_uid": VALIDATOR_UID,
        "expected_validator_username": VALIDATOR_USERNAME,
        "expected_reader_group_gid": READER_GID,
        "expected_reader_group_name": READER_GROUP_NAME,
        "queue_marker": {
            "relative_path": ".w7tp-deferred-push-queue-v1",
            "bytes_base64": base64.b64encode(b"w7tp-deferred-push-queue/1.0\n").decode("ascii"),
            "sha256": hashlib.sha256(b"w7tp-deferred-push-queue/1.0\n").hexdigest(),
        },
        "executor_contract": {
            "executor_skill_ref": "$complete-deferred-git-push",
            "executor_skill_version": "1.0.0",
            "request_schema": "w7tp-deferred-git-push-request/1.0",
            "event_schema": "w7tp-deferred-git-push-event/1.0",
            "initial_event_kind": "ENQUEUED",
        },
        "activation": {
            "activation_ref": "queue-activation-fixture-1",
            "valid_from": "2026-01-01T00:00:00Z",
            "expires_at": "2099-01-01T00:00:00Z",
            "activation_receipt_ref": "queue-activation-receipt-fixture-1",
            "activation_receipt_sha256": "a" * 64,
        },
        "hash_contract": "SHA256_CANONICAL_JSON_EXCLUDING_CONFIG_SHA256_V1",
        "config_sha256": "",
    }
    config["config_sha256"] = hash_without(config, "config_sha256")
    path = trust_config_path(root)
    path.write_bytes(canonical_bytes(config) + b"\n")
    path.chmod(0o444)
    os.chown(path, 0, 0)
    return path, config


def _obligation_ack_for(
    document: dict,
    request: dict,
    event: dict,
    trust_config: dict,
) -> dict:
    ack = {
        "schema_version": "w7tp-e2-deferred-push-obligation-queue-ack/1.0",
        "hash_contract": "SHA256_CANONICAL_JSON_EXCLUDING_OWN_HASH_V1",
        "ack_kind": "E2_DEFERRED_PUSH_OBLIGATION_ENQUEUED",
        "ack_state": "ACKNOWLEDGED_IMMUTABLE",
        "obligation_id": document["obligation_id"],
        "obligation_schema_version": document["schema_version"],
        "obligation_core_sha256": compute_obligation_core_hash(document),
        "executor_handoff_payload_sha256": compute_executor_handoff_payload_hash(document),
        "executor_ticket_id": request["ticket_id"],
        "executor_request_ref": f"tickets/{request['ticket_id']}/request.json",
        "executor_request_sha256": request["request_sha256"],
        "executor_initial_event_ref": (
            f"tickets/{request['ticket_id']}/events/00000000000000000001.json"
        ),
        "executor_initial_event_sha256": event["event_sha256"],
        "queue_store_idempotency_key": request["idempotency_key"],
        "queue_trust_config_sha256": trust_config["config_sha256"],
        "founder_intent_ref": document["founder_intent_ref"],
        "founder_intent_sha256": document["founder_intent_sha256"],
        "repository_root": request["repository"]["root"],
        "repository_fingerprint_sha256": request["repository"]["fingerprint_sha256"],
        "identity_root_ref": document["identity_root_ref"],
        "member_ref": document["member_ref"],
        "seat_binding_ref": document["seat_binding_ref"],
        "receiver_ref": document["receiver_ref"],
        "test_receipt_ref": document["source_closure"]["test_receipt_ref"],
        "test_receipt_sha256": document["source_closure"]["test_receipt_sha256"],
        "authorization_scope_sha256": document["authorization"]["scope_sha256"],
        "effect_scope_sha256": compute_obligation_effect_scope_hash(document),
        "change_set_sha256": document["change_set_sha256"],
        "acknowledged_at": "2026-08-27T00:00:01Z",
        "ack_sha256": "",
    }
    ack["ack_sha256"] = hash_without(ack, "ack_sha256")
    return ack


def _publish_obligation_ack(
    root: Path,
    document: dict,
    request: dict,
    event: dict,
    trust_config: dict,
    queue_owner_uid: int = 0,
    queue_owner_gid: int = 0,
) -> dict:
    document["queue_store"].update({
        "store_ref": f"trusted-executor-queue:{trust_config['config_sha256']}",
        "idempotency_key": request["idempotency_key"],
        "append_only_ack_ref": f"e2-obligation-acks/{request['ticket_id']}.json",
        "append_only_ack_sha256": "0" * 64,
        "outside_target_repo": True,
    })
    ack = _obligation_ack_for(document, request, event, trust_config)
    document["queue_store"]["append_only_ack_sha256"] = ack["ack_sha256"]
    reseal_handoff(document)
    ack_path = root / "e2-obligation-acks" / f"{request['ticket_id']}.json"
    if ack_path.exists():
        rewrite_private_json(ack_path, ack)
    else:
        ack_path.write_bytes(canonical_bytes(ack) + b"\n")
        ack_path.chmod(0o440)
    if ack_path.stat().st_uid != queue_owner_uid or ack_path.stat().st_gid != queue_owner_gid:
        os.chown(ack_path, queue_owner_uid, queue_owner_gid)
    return ack


def write_executor_state(
    root: Path,
    document: dict,
    *,
    materialize_nonroot_owner: bool = False,
) -> tuple[dict, dict]:
    if not str(document["repository"]["repo_ref"]).startswith("/"):
        document["repository"]["repo_ref"] = os.fspath(root.parent / "target-repository")
    repo_root = Path(document["repository"]["repo_ref"])
    repo_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    (repo_root / ".git").mkdir(mode=0o700, exist_ok=True)
    request, event = bind_executor_handoff(document)
    root.mkdir(mode=0o750)
    marker = root / ".w7tp-deferred-push-queue-v1"
    marker.write_bytes(b"w7tp-deferred-push-queue/1.0\n")
    marker.chmod(0o440)
    tickets = root / "tickets"
    tickets.mkdir(mode=0o750)
    ticket = tickets / request["ticket_id"]
    ticket.mkdir(mode=0o750)
    request_path = ticket / "request.json"
    request_path.write_bytes(canonical_bytes(request) + b"\n")
    request_path.chmod(0o440)
    events = ticket / "events"
    events.mkdir(mode=0o750)
    event_path = events / "00000000000000000001.json"
    event_path.write_bytes(canonical_bytes(event) + b"\n")
    event_path.chmod(0o440)
    obligation_acks = root / "e2-obligation-acks"
    obligation_acks.mkdir(mode=0o750)
    queue_owner_uid = 0
    queue_owner_gid = 0
    if materialize_nonroot_owner:
        if not _chown_queue_tree(root):
            raise unittest.SkipTest(
                "NONROOT_QUEUE_POSITIVE_INTEGRATION_NOT_RUN_SANDBOX_UID_MAP"
            )
        queue_owner_uid = QUEUE_OWNER_UID
        queue_owner_gid = READER_GID
    _, trust_config = _write_queue_trust_config(root)
    _publish_obligation_ack(
        root,
        document,
        request,
        event,
        trust_config,
        queue_owner_uid=queue_owner_uid,
        queue_owner_gid=queue_owner_gid,
    )
    return request, event


def materialize_three_party_executor_state(
    root: Path,
    document: dict,
    validator_account: pwd.struct_passwd,
) -> tuple[dict, dict]:
    """Provision a root trust anchor, a distinct queue owner, and a validator group."""
    request, event = write_executor_state(root, document)
    try:
        root.parent.chmod(0o755)
        repository = Path(document["repository"]["repo_ref"])
        repository.chmod(0o755)
        (repository / ".git").chmod(0o755)
        for path in [root, *root.rglob("*")]:
            os.chown(path, QUEUE_OWNER_UID, validator_account.pw_gid)
            path.chmod(0o750 if path.is_dir() else 0o440)

        config_path = trust_config_path(root)
        config = json.loads(config_path.read_text(encoding="utf-8"))
        parent_info = root.parent.stat()
        root_info = root.stat()
        config.update({
            "state_root_parent_realpath": os.fspath(root.parent.resolve(strict=True)),
            "state_root_parent_device": parent_info.st_dev,
            "state_root_parent_inode": parent_info.st_ino,
            "state_root_parent_mode": "0755",
            "state_root_basename": root.name,
            "state_root_realpath": os.fspath(root.resolve(strict=True)),
            "state_root_device": root_info.st_dev,
            "state_root_inode": root_info.st_ino,
            "state_root_mode": "0750",
        })
        rewrite_trust_config(config_path, config, reseal=True, mode=0o444)
        os.chown(config_path, 0, 0)
        ack = _publish_obligation_ack(
            root,
            document,
            request,
            event,
            config,
            queue_owner_uid=QUEUE_OWNER_UID,
            queue_owner_gid=validator_account.pw_gid,
        )
        ack_path = root / "e2-obligation-acks" / f"{request['ticket_id']}.json"
        ack_path.chmod(0o440)
        os.chown(ack_path, QUEUE_OWNER_UID, validator_account.pw_gid)
        if ack["ack_sha256"] != document["queue_store"]["append_only_ack_sha256"]:
            raise OSError("three-party ACK fixture did not close")
    except OSError as exc:
        raise unittest.SkipTest(
            "NONROOT_QUEUE_POSITIVE_INTEGRATION_NOT_RUN_SANDBOX_UID_MAP"
        ) from exc
    return request, event


def validate_with_executor(document: dict, root: Path, now: datetime | None = None) -> dict:
    config_path = trust_config_path(root)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    semantic_trust = {
        "config": config,
        "config_path": os.fspath(config_path),
        "config_sha256": config["config_sha256"],
        "state_root": root,
        "owner_uid": root.stat().st_uid,
        "reader_gid": root.stat().st_gid,
        "activation_valid_from": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "activation_expires_at": datetime(2099, 1, 1, tzinfo=timezone.utc),
    }
    with patch(
        "validate_deferred_push._read_executor_queue_trust_config",
        return_value=semantic_trust,
    ):
        return validate_deferred_push(
            document,
            now=now,
            executor_state_root=root,
            executor_queue_trust_config=config_path,
        )


def live_validate_with_executor(
    document: dict,
    root: Path,
    *,
    config_path: Path | None = None,
    now: datetime | None = None,
) -> dict:
    return validate_deferred_push(
        document,
        now=now,
        executor_state_root=root,
        executor_queue_trust_config=config_path or trust_config_path(root),
    )


def validate_trust_config_fixture(
    document: dict,
    root: Path,
    *,
    config_path: Path | None = None,
) -> dict:
    """Exercise real config/anchor bytes while substituting only process privilege state."""
    with patch(
        "validate_deferred_push._validate_live_process_trust_boundary",
        return_value=(UNIT_VALIDATOR_UID, frozenset({READER_GID})),
    ):
        return live_validate_with_executor(
            document,
            root,
            config_path=config_path,
        )


def rewrite_trust_config(
    path: Path,
    config: dict,
    *,
    reseal: bool = True,
    mode: int = 0o444,
) -> None:
    if reseal:
        config["config_sha256"] = hash_without(config, "config_sha256")
    path.chmod(0o600)
    path.write_bytes(canonical_bytes(config) + b"\n")
    path.chmod(mode)


def rewrite_private_json(path: Path, value: dict) -> None:
    path.chmod(0o600)
    path.write_bytes(canonical_bytes(value) + b"\n")
    path.chmod(0o440)


def _inherit_queue_owner(path: Path, root: Path) -> None:
    owner = root.stat()
    current = path.stat()
    if current.st_uid != owner.st_uid or current.st_gid != owner.st_gid:
        os.chown(path, owner.st_uid, owner.st_gid)


def add_terminal_executor_evidence(root: Path, document: dict) -> tuple[dict, dict]:
    request = executor_request_for(document)
    receipt = {
        "schema_version": "w7tp-deferred-git-push-readback-receipt/1.0",
        "hash_contract": "SHA256_CANONICAL_JSON_EXCLUDING_OWN_HASH_V1",
        "ticket_id": request["ticket_id"],
        "request_sha256": request["request_sha256"],
        "verified_at": "2026-08-27T00:00:02Z",
        "verification": "INDEPENDENT_GIT_LS_REMOTE_EXACT_REF_READBACK",
        "remote_endpoint_fingerprint_sha256": request["remote"]["endpoint_fingerprint_sha256"],
        "target_ref": request["git"]["target_ref"],
        "expected_remote_old_oid": request["git"]["expected_remote_old_oid"],
        "preflight_observed_oid": request["git"]["expected_remote_old_oid"],
        "intended_source_commit_oid": request["git"]["source_commit_oid"],
        "observed_remote_oid": request["git"]["source_commit_oid"],
        "source_tree_oid": request["git"]["source_tree_oid"],
        "reachable_object_closure_sha256": request["git"]["reachable_object_closure_sha256"],
        "change_scope_sha256": request["git"]["change_scope_sha256"],
        "change_manifest": request["git"]["change_manifest"],
        "commit_range_sha256": request["git"]["commit_range_sha256"],
        "causal_groups": request["git"]["causal_groups"],
        "causal_group_combined_sha256": request["git"]["causal_group_combined_sha256"],
        "authority_sensitive_paths": request["git"]["authority_sensitive_paths"],
        "total_field_decision_ref": "decision-1",
        "total_field_decision_receipt_sha256": "1" * 64,
        "total_field_scope_sha256": "2" * 64,
        "total_field_single_use_nonce_sha256": "3" * 64,
        "receiver_adapter_sha256": "4" * 64,
        "receiver_reservation_ack_sha256": "5" * 64,
        "receiver_final_validation_ack_sha256": "6" * 64,
        "receiver_consume_ack": {},
        "delivery_proof_sha256": "7" * 64,
        "server_compare_and_swap": {},
        "changed_paths": request["git"]["causal_group_changed_paths"],
        "push_invoked": True,
        "uncertain_outcome_reconciled": False,
        "protected_state_before": {},
        "protected_state_after": {},
        "protected_state_comparison": {},
        "dirty_worktree_unchanged": True,
        "protected_state_repair_state": "NONE",
        "remote_exact_oid_match": True,
        "receipt_sha256": "",
    }
    receipt["receipt_sha256"] = hash_without(receipt, "receipt_sha256")
    relative = f"receipts/readback-{receipt['receipt_sha256']}.json"
    ticket_root = root / "tickets" / request["ticket_id"]
    receipts = ticket_root / "receipts"
    receipts.mkdir(mode=0o750)
    _inherit_queue_owner(receipts, root)
    receipt_path = receipts / f"readback-{receipt['receipt_sha256']}.json"
    receipt_path.write_bytes(canonical_bytes(receipt) + b"\n")
    receipt_path.chmod(0o440)
    _inherit_queue_owner(receipt_path, root)
    first = initial_executor_event(request)
    event = {
        "schema_version": "w7tp-deferred-git-push-event/1.0",
        "hash_contract": "SHA256_CANONICAL_JSON_EXCLUDING_OWN_HASH_V1",
        "ticket_id": request["ticket_id"],
        "sequence": 2,
        "occurred_at": "2026-08-27T00:00:02Z",
        "kind": "REMOTE_EXACT_OID_READBACK_VERIFIED",
        "state": "PUSHED_VERIFIED",
        "next_attempt_at": None,
        "prev_event_hash": first["event_sha256"],
        "details": {
            "remote_oid": request["git"]["source_commit_oid"],
            "receipt_relative_path": relative,
            "receipt_sha256": receipt["receipt_sha256"],
            "push_invoked": True,
            "uncertain_outcome_reconciled": False,
            "protected_state_comparison": {},
            "worktree_state": "UNCHANGED",
            "protected_state_repair_state": "NONE",
        },
        "event_sha256": "",
    }
    event["event_sha256"] = hash_without(event, "event_sha256")
    event_path = ticket_root / "events" / "00000000000000000002.json"
    event_path.write_bytes(canonical_bytes(event) + b"\n")
    event_path.chmod(0o440)
    _inherit_queue_owner(event_path, root)
    document["closure"] = {
        "remote_commit_oid": request["git"]["source_commit_oid"],
        "remote_readback_receipt_ref": f"tickets/{request['ticket_id']}/{relative}",
    }
    trust_config = json.loads(trust_config_path(root).read_text(encoding="utf-8"))
    root_owner = root.stat()
    _publish_obligation_ack(
        root,
        document,
        request,
        first,
        trust_config,
        queue_owner_uid=root_owner.st_uid,
        queue_owner_gid=root_owner.st_gid,
    )
    return receipt, event


def valid_push_obligation() -> dict:
    source_oid = "3" * 40
    target_ref = "refs/heads/agent/safe-candidate"
    document = {
        "schema_version": "w7tp-deferred-git-push-obligation/1.2",
        "obligation_id": "will-be-bound-to-executor-ticket",
        "founder_intent_ref": "founder-intent-1",
        "founder_intent_sha256": "d" * 64,
        "responsible_agent_ref": "opaque-agent-1",
        "workloop_ref": "workloop-1",
        "identity_root_ref": "identity-1",
        "member_ref": "member-1",
        "seat_binding_ref": "seat-1",
        "receiver_ref": "TOTAL_FIELD_8D_ADI_GIT_INDEX_RECEIVER",
        "state": "PUSH_OBLIGATION_OPEN",
        "total_field_route": "REVIEW_REQUIRED",
        "repository": {
            "repo_ref": "repo-1",
            "repository_fingerprint_sha256": "0" * 64,
            "remote_name": "origin",
            "remote_endpoint_sha256": "1" * 64,
            "target_ref": target_ref,
            "source_oid": source_oid,
            "expected_remote_old_oid": "2" * 40,
            "object_format": "sha1",
            "refspec": f"{source_oid}:{target_ref}",
        },
        "source_closure": {
            "commit_oid": source_oid,
            "parent_oid": "2" * 40,
            "tree_oid": "4" * 40,
            "reachable_objects_sha256": "5" * 64,
            "reviewed_history_sha256": hashlib.sha256(canonical_bytes([source_oid])).hexdigest(),
            "test_receipt_ref": "tests-1",
            "test_receipt_sha256": "6" * 64,
        },
        "change_scope_state": "RESOLVED_HASH_BOUND",
        "changes": [{"status": "A", "path": "candidate/evidence/result.md", "sha256": "7" * 64}],
        "change_set_sha256": "",
        "queue_store": {
            "store_ref": "governed-queue-1",
            "idempotency_key": "idempotency-1",
            "append_only_ack_ref": "obligation-queue-ack-1",
            "append_only_ack_sha256": "0" * 64,
            "outside_target_repo": True,
        },
        "blocker": {
            "code": "REVIEW_PENDING",
            "evidence_ref": "review-1",
            "repair_plan": ["完成限定範圍審查", "重新核對遠端 ref"],
            "automation_possible": True,
        },
        "schedule": {
            "scheduler_state": "HANDOFF_RESUME_REQUIRED",
            "scheduler_job_ref": None,
            "created_at": "2026-08-27T00:00:00Z",
            "next_attempt_at": "2026-08-27T01:00:00Z",
            "deadline_at": "2026-09-03T00:00:00Z",
            "resume_trigger": "REVIEW_RECEIPT_AVAILABLE",
            "attempt_count": 0,
            "max_auto_attempts": 3,
            "executor_lease_ref": None,
            "executor_lease_expires_at": None,
        },
        "authorization": {
            "required": True,
            "authorization_ref": None,
            "authorization_expires_at": None,
            "decision_ref": None,
            "decision_receipt_sha256": None,
            "decision_expires_at": None,
            "scope_sha256": "0" * 64,
        },
        "safety": {
            "fast_forward_only": True,
            "force_push": False,
            "delete_ref": False,
            "push_tags": False,
            "multiple_refs": False,
            "recurse_submodules": False,
            "history_rewrite": False,
            "include_unrelated_dirty_files": False,
            "remote_readback_required": True,
            "push_effects": {
                "pre_push_hooks": "DISABLED",
                "git_lfs": "NOT_USED",
                "ci_webhook_deploy": "NOT_USED",
            },
            "stop_conditions": ["REMOTE_OLD_OID_DRIFT", "HASH_OR_TEST_DRIFT"],
            "rollback": "建立新的 revert successor；不得改寫歷史。",
        },
        "executor_handoff": {
            "executor_skill_ref": "$complete-deferred-git-push",
            "executor_skill_version": "1.0.0",
            "input_contract": "w7tp-deferred-git-push-request",
            "input_contract_version": "1.0",
            "obligation_id": "will-be-bound-to-executor-ticket",
            "executor_ticket_id": "dgp-" + "0" * 64,
            "executor_request_sha256": "9" * 64,
            "executor_queue_ack_ref": "tickets/dgp-placeholder/events/00000000000000000001.json",
            "executor_queue_ack_sha256": "a" * 64,
            "handoff_state": "READY_FOR_E4_VALIDATION",
            "activation_state": "NOT_ACTIVATED_BY_E2_ROUTING",
            "responsibilities": [
                "E4_SINGLE_REF_FAST_FORWARD_EXECUTION",
                "TERMINAL_AUTHORITATIVE_RECHECK",
                "REMOTE_EXACT_OID_READBACK_CLOSURE",
            ],
            "hash_contract": "SHA256_CANONICAL_JSON_EXCLUDING_EXECUTOR_HANDOFF_SHA256_V1",
            "handoff_sha256": "",
        },
        "closure": {},
    }
    document["change_set_sha256"] = hashlib.sha256(canonical_bytes(document["changes"])).hexdigest()
    bind_executor_handoff(document)
    return document


def reseal_handoff(document: dict) -> None:
    document["executor_handoff"]["handoff_sha256"] = compute_executor_handoff_hash(document)


def waiting_exact_target_obligation() -> dict:
    document = valid_push_obligation()
    document["repository"].update({
        "source_oid": "UNKNOWN_UNVERIFIED",
        "refspec": "UNKNOWN_UNVERIFIED",
    })
    document["source_closure"].update({
        "commit_oid": "UNKNOWN_UNVERIFIED",
        "parent_oid": "UNKNOWN_UNVERIFIED",
        "tree_oid": "UNKNOWN_UNVERIFIED",
        "reachable_objects_sha256": "UNKNOWN_UNVERIFIED",
        "reviewed_history_sha256": "UNKNOWN_UNVERIFIED",
        "test_receipt_ref": "UNKNOWN_UNVERIFIED",
        "test_receipt_sha256": "UNKNOWN_UNVERIFIED",
    })
    document["change_scope_state"] = "UNRESOLVED_REQUIRES_DISCOVERY"
    document["changes"] = []
    document["change_set_sha256"] = "UNKNOWN_UNVERIFIED"
    document["blocker"].update({
        "code": "WAITING_EXACT_TARGET",
        "evidence_ref": "bounded-worktree-change-1",
        "repair_plan": ["在原工作樹形成並驗證精確 commit", "建立 hash-bound successor ticket"],
    })
    document["schedule"]["resume_trigger"] = "EXACT_TARGET_COMMIT_AVAILABLE"
    document["executor_handoff"]["handoff_state"] = "WAITING_EXACT_TARGET"
    bind_executor_handoff(document)
    return document


class IndexContractTests(unittest.TestCase):
    def test_valid_exact_packet_passes(self) -> None:
        self.assertEqual(validate(valid_packet())["state"], "PASS_8D_ADI_GIT_INDEX_CANDIDATE")

    def test_equivalent_state_cannot_reuse_oid(self) -> None:
        packet = valid_packet()
        packet["D2"]["acceptance"] = "EQUIVALENT_STATE"
        packet["D6"]["acceptance"] = "EQUIVALENT_STATE"
        self.assertIn("EQUIVALENT_STATE_CANNOT_REUSE_EXPECTED_OID", validate(packet)["errors"])

    def test_missing_seat_is_rejected(self) -> None:
        packet = valid_packet()
        packet["seat_binding_ref"] = ""
        self.assertIn("SEAT_BINDING_REF_MISSING", validate(packet)["errors"])

    def test_canonical_write_is_rejected(self) -> None:
        packet = valid_packet()
        packet["D8"]["canonical_write"] = True
        self.assertIn("D8_CANONICAL_WRITE_NOT_DENIED", validate(packet)["errors"])

    def test_unpinned_rule_is_rejected(self) -> None:
        packet = valid_packet()
        packet["D6"]["rule_refs"][0]["sha256"] = "bad"
        self.assertIn("D6_RULE_REFS_UNPINNED", validate(packet)["errors"])

    def test_malformed_receiver_fails_closed(self) -> None:
        packet = valid_packet()
        packet["receiver"] = "wrong-type"
        self.assertIn("RECEIVER_OBJECT_INVALID", validate(packet)["errors"])

    def test_missing_git_coordinate_is_rejected(self) -> None:
        packet = valid_packet()
        packet["D3"].pop("base_tree_oid")
        packet["D3"].pop("path_bytes_b64")
        errors = validate(packet)["errors"]
        self.assertIn("D3_BASE_TREE_OID_INVALID", errors)
        self.assertIn("D3_PATH_BYTES_INVALID", errors)

    def test_expired_packet_is_rejected(self) -> None:
        packet = valid_packet()
        packet["event"]["expiry"] = "2000-01-01T00:00:00Z"
        packet["event"]["event_hash"] = compute_event_hash(packet)
        self.assertIn("PACKET_EXPIRED", validate(packet)["errors"])

    def test_event_hash_mismatch_is_rejected(self) -> None:
        packet = valid_packet()
        packet["D1"]["intent_ref"] = "changed-after-hash"
        self.assertIn("EVENT_HASH_MISMATCH", validate(packet)["errors"])


class DeferredPushObligationTests(unittest.TestCase):
    def test_document_only_cannot_self_assert_executor_ack(self) -> None:
        result = validate_deferred_push(valid_push_obligation())
        self.assertEqual(result["state"], "HOLD_TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE")
        self.assertFalse(result["executor_queue_ack_verified"])

    def test_open_obligation_with_verified_external_ack_passes(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            write_executor_state(root, document)
            result = validate_with_executor(document, root)
        self.assertEqual(result["state"], "PASS_DEFERRED_PUSH_OBLIGATION")
        self.assertTrue(result["executor_queue_ack_verified"])
        self.assertTrue(result["obligation_queue_ack_verified"])
        self.assertFalse(result["execution_authorized"])

    def test_live_reader_rejects_root_validator_before_queue_evidence(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            write_executor_state(root, document)
            result = live_validate_with_executor(document, root)
        self.assertEqual(result["state"], "HOLD_TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE")
        self.assertIn("EXECUTOR_QUEUE_VALIDATOR_ROOT_FORBIDDEN", result["errors"])
        self.assertFalse(result["executor_queue_ack_verified"])

    def test_live_reader_rejects_every_dangerous_effective_or_permitted_capability(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            write_executor_state(root, document)
            for set_name, tuple_index in (("EFFECTIVE", 0), ("PERMITTED", 1)):
                for bit in (0, 1, 3, 6, 7, 21):
                    sets = [0, 0]
                    sets[tuple_index] = 1 << bit
                    with self.subTest(set_name=set_name, capability_bit=bit), patch(
                        "validate_deferred_push.os.geteuid",
                        return_value=UNIT_VALIDATOR_UID,
                    ), patch(
                        "validate_deferred_push._read_process_capabilities",
                        return_value=tuple(sets),
                    ):
                        result = live_validate_with_executor(document, root)
                    self.assertEqual(
                        result["state"], "HOLD_TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE"
                    )
                    self.assertTrue(
                        any(
                            error.startswith(
                                f"EXECUTOR_QUEUE_VALIDATOR_{set_name}_CAPABILITIES_FORBIDDEN:"
                            )
                            for error in result["errors"]
                        )
                    )

    def test_live_reader_holds_when_capability_status_is_unreadable_or_invalid(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            write_executor_state(root, document)
            for code in (
                "EXECUTOR_QUEUE_VALIDATOR_CAPABILITIES_UNREADABLE",
                "EXECUTOR_QUEUE_VALIDATOR_CAPABILITIES_INVALID",
            ):
                with self.subTest(code=code), patch(
                    "validate_deferred_push.os.geteuid",
                    return_value=UNIT_VALIDATOR_UID,
                ), patch(
                    "validate_deferred_push._read_process_capabilities",
                    side_effect=_ExternalEvidenceError(code),
                ):
                    result = live_validate_with_executor(document, root)
                self.assertEqual(
                    result["state"], "HOLD_TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE"
                )
                self.assertIn(code, result["errors"])

    def test_live_reader_holds_when_process_groups_are_unreadable(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            write_executor_state(root, document)
            with patch(
                "validate_deferred_push.os.geteuid",
                return_value=VALIDATOR_UID,
            ), patch(
                "validate_deferred_push._read_process_capabilities",
                return_value=(0, 0),
            ), patch(
                "validate_deferred_push.os.getgroups",
                side_effect=OSError("group database unavailable"),
            ):
                result = live_validate_with_executor(document, root)
        self.assertEqual(result["state"], "HOLD_TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE")
        self.assertIn(
            "EXECUTOR_QUEUE_VALIDATOR_GROUPS_UNREADABLE", result["errors"]
        )

    def test_proc_capability_parser_reads_current_process_status(self) -> None:
        effective, permitted = _read_process_capabilities()
        self.assertIsInstance(effective, int)
        self.assertIsInstance(permitted, int)

    def test_proc_capability_parser_is_exact_and_fail_closed(self) -> None:
        self.assertEqual(
            _parse_capability_status(
                b"Name:\tfixture\nCapPrm:\t0000000000000000\n"
                b"CapEff:\t0000000000000000\n"
            ),
            (0, 0),
        )
        self.assertEqual(
            _parse_capability_status(
                b"CapPrm:  0000000000000002\nCapEff:  0000000000200001\n"
            ),
            (0x200001, 0x2),
        )
        invalid = (
            b"Name:\tmissing\n",
            b"CapPrm:\t0000000000000000\n",
            b"CapEff:\t0000000000000000\n",
            b"CapEff:\n0000000000000000\nCapPrm:\t0000000000000000\n",
            b"CapEff:\t0000000000000000\nCapEff:\t0000000000000000\nCapPrm:\t0000000000000000\n",
            b"CapEff:\t0000000000000000\n CapEff:\t0000000000000000\nCapPrm:\t0000000000000000\n",
            b"CapEff:\t0000000000000000\nCapPrm:\t0000000000000000\nCapPrm:\t0000000000000000\n",
            b"CapEff:\t00000000000000000\nCapPrm:\t0000000000000000\n",
            b"CapEff:\t000000000000000\nCapPrm:\t0000000000000000\n",
            b"CapEff:\t000000000000000g\nCapPrm:\t0000000000000000\n",
            b"CapEff:\t0000000000000000\nCapPrm:\t000000000000000g\n",
        )
        for raw in invalid:
            with self.subTest(raw=raw), self.assertRaises(_ExternalEvidenceError) as raised:
                _parse_capability_status(raw)
            self.assertEqual(
                raised.exception.code,
                "EXECUTOR_QUEUE_VALIDATOR_CAPABILITIES_INVALID",
            )

    def test_live_reader_rejects_configured_queue_owner_equal_to_process_euid(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            write_executor_state(root, document)
            with patch(
                "validate_deferred_push.os.geteuid",
                return_value=QUEUE_OWNER_UID,
            ), patch(
                "validate_deferred_push._read_process_capabilities",
                return_value=(0, 0),
            ):
                result = live_validate_with_executor(document, root)
        self.assertEqual(result["state"], "HOLD_TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE")
        self.assertIn("EXECUTOR_QUEUE_TRUST_CONFIG_SEMANTICS_INVALID", result["errors"])
        self.assertFalse(result["executor_queue_ack_verified"])

    def test_live_nonroot_queue_positive_integration_when_kernel_uid_map_allows_it(self) -> None:
        document = valid_push_obligation()
        try:
            validator_account = pwd.getpwnam("daemon")
        except KeyError as exc:
            raise unittest.SkipTest(
                "NONROOT_QUEUE_POSITIVE_INTEGRATION_NOT_RUN_SANDBOX_UID_MAP"
            ) from exc
        if (
            os.geteuid() != 0
            or validator_account.pw_uid in {0, QUEUE_OWNER_UID}
        ):
            self.skipTest(
                "NONROOT_QUEUE_POSITIVE_INTEGRATION_NOT_RUN_SANDBOX_UID_MAP"
            )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            materialize_three_party_executor_state(root, document, validator_account)
            obligation_path = Path(temp) / "obligation.json"
            obligation_path.write_bytes(canonical_bytes(document) + b"\n")
            obligation_path.chmod(0o444)
            validator_copy = Path(temp) / "validate_deferred_push.py"
            validator_copy.write_bytes(
                (Path(__file__).parent / "validate_deferred_push.py").read_bytes()
            )
            validator_copy.chmod(0o555)

            def drop_to_validator() -> None:
                os.setgroups([])
                os.setgid(validator_account.pw_gid)
                os.setuid(validator_account.pw_uid)

            try:
                completed = subprocess.run(
                    [
                        sys.executable,
                        os.fspath(validator_copy),
                        os.fspath(obligation_path),
                        "--executor-state-root",
                        os.fspath(root),
                        "--executor-queue-trust-config",
                        os.fspath(trust_config_path(root)),
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                    env={
                        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                        "PYTHONIOENCODING": "utf-8",
                    },
                    preexec_fn=drop_to_validator,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                raise unittest.SkipTest(
                    "NONROOT_QUEUE_POSITIVE_INTEGRATION_NOT_RUN_SANDBOX_UID_MAP"
                ) from exc
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            result = json.loads(completed.stdout)
        self.assertEqual(result["state"], "PASS_DEFERRED_PUSH_OBLIGATION")
        self.assertTrue(result["executor_queue_ack_verified"])
        self.assertTrue(result["obligation_queue_ack_verified"])

    def test_live_reader_rejects_missing_trust_config(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            write_executor_state(root, document)
            missing = Path(temp) / "missing-trust-config.json"
            result = validate_trust_config_fixture(
                document, root, config_path=missing
            )
        self.assertEqual(result["state"], "HOLD_TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE")
        self.assertIn("EXECUTOR_QUEUE_TRUST_CONFIG_UNREADABLE", result["errors"])

    def test_trust_config_same_fd_read_reaches_state_root_gate(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            write_executor_state(root, document)
            with patch(
                "validate_deferred_push._validate_live_process_trust_boundary",
                return_value=(VALIDATOR_UID, frozenset({READER_GID})),
            ), self.assertRaises(_ExternalEvidenceError) as raised:
                _read_executor_queue_trust_config(
                    trust_config_path(root),
                    root,
                    datetime(2026, 8, 27, tzinfo=timezone.utc),
                )
        self.assertEqual(
            raised.exception.code,
            "EXECUTOR_QUEUE_TRUST_STATE_ROOT_UNSAFE",
        )

    def test_live_reader_rejects_unsafe_trust_config_mode(self) -> None:
        for mode in (0o400, 0o600):
            with self.subTest(mode=oct(mode)), tempfile.TemporaryDirectory() as temp:
                document = valid_push_obligation()
                root = Path(temp) / "executor-state"
                write_executor_state(root, document)
                config_path = trust_config_path(root)
                config_path.chmod(mode)
                result = validate_trust_config_fixture(document, root)
            self.assertEqual(
                result["state"], "HOLD_TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE"
            )
            self.assertIn(
                "EXECUTOR_QUEUE_TRUST_CONFIG_FILE_UNSAFE", result["errors"]
            )

    def test_live_reader_rejects_trust_config_path_symlink(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            write_executor_state(root, document)
            link = Path(temp) / "trust-config-link.json"
            link.symlink_to(trust_config_path(root))
            result = validate_trust_config_fixture(
                document, root, config_path=link
            )
        self.assertEqual(result["state"], "HOLD_TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE")
        self.assertIn("EXECUTOR_QUEUE_TRUST_CONFIG_PATH_INVALID", result["errors"])

    def test_live_reader_rejects_trust_config_hash_and_activation_drift(self) -> None:
        mutations = {
            "hash": lambda config: config.update({"config_sha256": "f" * 64}),
            "schema": lambda config: config.update({
                "schema_version": "w7tp-e2-executor-queue-trust-config/1.0",
            }),
            "parent-path": lambda config: config.update({
                "state_root_parent_realpath": "/tmp/other-parent",
            }),
            "parent-device": lambda config: config.update({
                "state_root_parent_device": config["state_root_parent_device"] + 1,
            }),
            "parent-inode": lambda config: config.update({
                "state_root_parent_inode": config["state_root_parent_inode"] + 1,
            }),
            "parent-mode": lambda config: config.update({
                "state_root_parent_mode": "0777",
            }),
            "basename": lambda config: config.update({
                "state_root_basename": "other-state-root",
            }),
            "state-root-path": lambda config: config.update({"state_root_realpath": "/tmp/other-root"}),
            "device": lambda config: config.update({"state_root_device": config["state_root_device"] + 1}),
            "inode": lambda config: config.update({"state_root_inode": config["state_root_inode"] + 1}),
            "state-root-mode": lambda config: config.update({"state_root_mode": "0777"}),
            "uid": lambda config: config.update({
                "expected_nonroot_owner_uid": 1,
                "expected_nonroot_owner_username": pwd.getpwuid(1).pw_name,
            }),
            "username": lambda config: config.update({"expected_nonroot_owner_username": "wrong-user"}),
            "validator-uid": lambda config: config.update({
                "expected_validator_uid": QUEUE_OWNER_UID,
                "expected_validator_username": QUEUE_OWNER_USERNAME,
            }),
            "validator-username": lambda config: config.update({
                "expected_validator_username": "wrong-validator",
            }),
            "reader-group-gid": lambda config: config.update({
                "expected_reader_group_gid": QUEUE_OWNER.pw_gid,
                "expected_reader_group_name": grp.getgrgid(QUEUE_OWNER.pw_gid).gr_name,
            }),
            "reader-group-name": lambda config: config.update({
                "expected_reader_group_name": "wrong-reader-group",
            }),
            "expiry": lambda config: config["activation"].update({"expires_at": "2000-01-01T00:00:00Z"}),
            "activation-receipt-ref": lambda config: config["activation"].update({"activation_receipt_ref": ""}),
            "activation-receipt-hash": lambda config: config["activation"].update({"activation_receipt_sha256": "bad"}),
            "marker-bytes": lambda config: config["queue_marker"].update({
                "bytes_base64": base64.b64encode(b"caller-marker\n").decode("ascii"),
            }),
            "marker-hash": lambda config: config["queue_marker"].update({"sha256": "e" * 64}),
            "executor-contract": lambda config: config["executor_contract"].update({
                "executor_skill_version": "caller-version",
            }),
            "unknown-field": lambda config: config.update({"executor_activation": "ACTIVE"}),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp:
                document = valid_push_obligation()
                root = Path(temp) / "executor-state"
                write_executor_state(root, document)
                config_path = trust_config_path(root)
                config = json.loads(config_path.read_text(encoding="utf-8"))
                mutate(config)
                rewrite_trust_config(config_path, config, reseal=label != "hash")
                result = validate_trust_config_fixture(document, root)
                self.assertEqual(result["state"], "HOLD_TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE")
                self.assertIn("TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE", result["errors"])

    def test_live_reader_requires_configured_reader_group_membership(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            write_executor_state(root, document)
            with patch(
                "validate_deferred_push._validate_live_process_trust_boundary",
                return_value=(VALIDATOR_UID, frozenset()),
            ):
                result = live_validate_with_executor(document, root)
        self.assertEqual(result["state"], "HOLD_TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE")
        self.assertIn(
            "EXECUTOR_QUEUE_TRUST_CONFIG_SEMANTICS_INVALID", result["errors"]
        )

    def test_account_or_group_lookup_failure_is_a_hold_not_a_crash(self) -> None:
        lookups = (
            "validate_deferred_push.pwd.getpwuid",
            "validate_deferred_push.grp.getgrgid",
        )
        for lookup in lookups:
            with self.subTest(lookup=lookup), tempfile.TemporaryDirectory() as temp:
                document = valid_push_obligation()
                root = Path(temp) / "executor-state"
                write_executor_state(root, document)
                with patch(lookup, side_effect=OSError("identity lookup unavailable")):
                    result = validate_trust_config_fixture(document, root)
            self.assertEqual(
                result["state"], "HOLD_TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE"
            )
            self.assertIn(
                "EXECUTOR_QUEUE_TRUST_CONFIG_SEMANTICS_INVALID", result["errors"]
            )

    def test_arbitrary_reader_group_member_cannot_replace_configured_validator(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            write_executor_state(root, document)
            with patch(
                "validate_deferred_push._validate_live_process_trust_boundary",
                return_value=(ARBITRARY_READER_UID, frozenset({READER_GID})),
            ):
                result = live_validate_with_executor(document, root)
        self.assertEqual(result["state"], "HOLD_TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE")
        self.assertIn(
            "EXECUTOR_QUEUE_TRUST_CONFIG_SEMANTICS_INVALID", result["errors"]
        )

    def test_resealed_config_and_ack_cannot_change_validator_or_reader_group(self) -> None:
        mutations = (
            {
                "expected_validator_uid": QUEUE_OWNER_UID,
                "expected_validator_username": QUEUE_OWNER_USERNAME,
            },
            {
                "expected_reader_group_gid": QUEUE_OWNER.pw_gid,
                "expected_reader_group_name": grp.getgrgid(QUEUE_OWNER.pw_gid).gr_name,
            },
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                document = valid_push_obligation()
                root = Path(temp) / "executor-state"
                request, event = write_executor_state(root, document)
                config_path = trust_config_path(root)
                config = json.loads(config_path.read_text(encoding="utf-8"))
                config.update(mutation)
                rewrite_trust_config(config_path, config, reseal=True)
                _publish_obligation_ack(root, document, request, event, config)
                result = validate_trust_config_fixture(document, root)
            self.assertEqual(
                result["state"], "HOLD_TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE"
            )
            self.assertIn(
                "EXECUTOR_QUEUE_TRUST_CONFIG_SEMANTICS_INVALID", result["errors"]
            )

    def test_state_root_and_every_fd_entry_require_exact_reader_gid(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            write_executor_state(root, document)
            config = json.loads(
                trust_config_path(root).read_text(encoding="utf-8")
            )
            wrong_group_trust = {
                "config": config,
                "owner_uid": root.stat().st_uid,
                "reader_gid": READER_GID,
            }
            with self.assertRaises(_ExternalEvidenceError):
                _open_trusted_state_root(
                    wrong_group_trust,
                    "EXPECTED_STATE_ROOT_GID_HOLD",
                )

            root_fd = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                with self.assertRaises(_ExternalEvidenceError) as marker_hold:
                    _read_private_file_at(
                        root_fd,
                        ".w7tp-deferred-push-queue-v1",
                        root.stat().st_uid,
                        READER_GID,
                        code="EXPECTED_FILE_GID_HOLD",
                    )
                self.assertEqual(marker_hold.exception.code, "EXPECTED_FILE_GID_HOLD")
                with self.assertRaises(_ExternalEvidenceError) as directory_hold:
                    _open_private_directory_at(
                        root_fd,
                        "tickets",
                        root.stat().st_uid,
                        READER_GID,
                        "EXPECTED_DIRECTORY_GID_HOLD",
                    )
                self.assertEqual(
                    directory_hold.exception.code, "EXPECTED_DIRECTORY_GID_HOLD"
                )
            finally:
                os.close(root_fd)

    def test_queue_private_only_modes_cannot_claim_distinct_reader_access(self) -> None:
        mutations = (
            ("state-root", lambda root: root.chmod(0o700)),
            (
                "directory",
                lambda root: (root / "tickets").chmod(0o700),
            ),
            (
                "evidence-file",
                lambda root: (
                    root / ".w7tp-deferred-push-queue-v1"
                ).chmod(0o400),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp:
                document = valid_push_obligation()
                root = Path(temp) / "executor-state"
                write_executor_state(root, document)
                mutate(root)
                result = validate_with_executor(document, root)
            self.assertEqual(result["state"], "HOLD_EXTERNAL_EXECUTOR_ACK_INVALID")
            self.assertFalse(result["executor_queue_ack_verified"])

    def test_actual_parent_mode_drift_is_held_through_parent_fd_anchor(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            root = parent / "executor-state"
            write_executor_state(root, document)
            parent.chmod(0o777)
            result = validate_trust_config_fixture(document, root)
        self.assertEqual(result["state"], "HOLD_TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE")
        self.assertIn("EXECUTOR_QUEUE_TRUST_STATE_ROOT_UNSAFE", result["errors"])

    def test_wrong_parent_owner_requires_materializable_nonroot_uid(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            root = parent / "executor-state"
            write_executor_state(root, document)
            try:
                os.chown(parent, QUEUE_OWNER_UID, QUEUE_OWNER.pw_gid)
            except OSError:
                self.skipTest(
                    "NONROOT_PARENT_OWNER_NEGATIVE_NOT_RUN_SANDBOX_UID_MAP"
                )
            result = validate_trust_config_fixture(document, root)
        self.assertEqual(result["state"], "HOLD_TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE")
        self.assertIn("EXECUTOR_QUEUE_TRUST_STATE_ROOT_UNSAFE", result["errors"])

    def test_wrong_config_owner_negative_requires_materializable_nonroot_uid(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            write_executor_state(root, document)
            config_path = trust_config_path(root)
            try:
                os.chown(config_path, QUEUE_OWNER_UID, QUEUE_OWNER.pw_gid)
            except OSError as exc:
                self.skipTest("NONROOT_CONFIG_OWNER_NEGATIVE_NOT_RUN_SANDBOX_UID_MAP")
            result = validate_trust_config_fixture(document, root)
        self.assertEqual(result["state"], "HOLD_TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE")
        self.assertIn("EXECUTOR_QUEUE_TRUST_CONFIG_FILE_UNSAFE", result["errors"])

    def test_missing_or_tampered_independent_obligation_ack_is_held(self) -> None:
        for mutation in ("missing", "tampered"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                document = valid_push_obligation()
                root = Path(temp) / "executor-state"
                request, _ = write_executor_state(root, document)
                ack_path = root / "e2-obligation-acks" / f"{request['ticket_id']}.json"
                if mutation == "missing":
                    ack_path.unlink()
                else:
                    ack = json.loads(ack_path.read_text(encoding="utf-8"))
                    ack["identity_root_ref"] = "other-identity"
                    ack["ack_sha256"] = hash_without(ack, "ack_sha256")
                    rewrite_private_json(ack_path, ack)
                result = validate_with_executor(document, root)
                self.assertEqual(result["state"], "HOLD_EXTERNAL_EXECUTOR_ACK_INVALID")
                self.assertFalse(result["obligation_queue_ack_verified"])

    def test_arbitrary_queue_store_strings_cannot_self_assert_ack(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            write_executor_state(root, document)
            document["queue_store"].update({
                "store_ref": "caller-queue",
                "idempotency_key": "caller-idempotency",
                "append_only_ack_ref": "caller-ack",
                "append_only_ack_sha256": "f" * 64,
                "outside_target_repo": True,
            })
            reseal_handoff(document)
            result = validate_with_executor(document, root)
        self.assertEqual(result["state"], "HOLD_EXTERNAL_EXECUTOR_ACK_INVALID")
        self.assertIn("EXTERNAL_OBLIGATION_ACK_INVALID", result["errors"])

    def test_executor_ticket_id_requires_exact_dgp_hash_shape(self) -> None:
        document = valid_push_obligation()
        document["executor_handoff"]["executor_ticket_id"] = "dgp-not-a-hash"
        reseal_handoff(document)
        self.assertIn("EXECUTOR_HANDOFF_TICKET_ID_INVALID", validate_deferred_push(document)["errors"])

    def test_obligation_and_executor_ack_references_are_distinct(self) -> None:
        document = valid_push_obligation()
        document["queue_store"]["append_only_ack_ref"] = document["executor_handoff"]["executor_queue_ack_ref"]
        reseal_handoff(document)
        self.assertIn(
            "OBLIGATION_AND_EXECUTOR_QUEUE_ACK_MUST_BE_DISTINCT",
            validate_deferred_push(document)["errors"],
        )

    def test_external_initial_ack_semantics_cannot_be_resealed_by_caller(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            request, event = write_executor_state(root, document)
            event["details"]["queue_ack"] = "CALLER_ASSERTED_ACK"
            event["event_sha256"] = hash_without(event, "event_sha256")
            document["executor_handoff"]["executor_queue_ack_sha256"] = event["event_sha256"]
            reseal_handoff(document)
            rewrite_private_json(
                root / "tickets" / request["ticket_id"] / "events" / "00000000000000000001.json",
                event,
            )
            result = validate_with_executor(document, root)
        self.assertEqual(result["state"], "HOLD_EXTERNAL_EXECUTOR_ACK_INVALID")
        self.assertIn("EXTERNAL_EXECUTOR_INITIAL_ACK_INVALID", result["errors"])

    def test_initial_executor_ack_cannot_claim_a_scheduler_attempt(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            request, event = write_executor_state(root, document)
            event["next_attempt_at"] = "2026-08-27T00:00:01Z"
            event["event_sha256"] = hash_without(event, "event_sha256")
            document["executor_handoff"]["executor_queue_ack_sha256"] = event["event_sha256"]
            reseal_handoff(document)
            rewrite_private_json(
                root / "tickets" / request["ticket_id"] / "events" / "00000000000000000001.json",
                event,
            )
            result = validate_with_executor(document, root)
        self.assertIn("EXTERNAL_EXECUTOR_INITIAL_ACK_INVALID", result["errors"])

    def test_unknown_external_request_field_is_rejected_even_with_new_hash(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            request, _ = write_executor_state(root, document)
            request["git"]["executor_activation"] = "ACTIVE"
            request["request_sha256"] = hash_without(request, "request_sha256")
            rewrite_private_json(root / "tickets" / request["ticket_id"] / "request.json", request)
            result = validate_with_executor(document, root)
        self.assertEqual(result["state"], "HOLD_EXTERNAL_EXECUTOR_ACK_INVALID")
        self.assertIn("EXTERNAL_EXECUTOR_GIT_SCHEMA_INVALID", result["errors"])

    def test_e2_change_status_and_content_hash_are_bound_to_external_manifest(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            write_executor_state(root, document)
            document["changes"][0].update({"status": "M", "sha256": "8" * 64})
            document["change_set_sha256"] = hashlib.sha256(canonical_bytes(document["changes"])).hexdigest()
            reseal_handoff(document)
            result = validate_with_executor(document, root)
        self.assertEqual(result["state"], "HOLD_EXTERNAL_EXECUTOR_ACK_INVALID")
        self.assertIn("EXTERNAL_EXECUTOR_CHANGE_SCOPE_MISMATCH", result["errors"])

    def test_obligation_executor_subject_and_effect_mixing_is_held(self) -> None:
        mutations = {
            "repository-root": (
                lambda document, root: document["repository"].update({
                    "repo_ref": os.fspath(root.parent / "different-repository"),
                }),
                "EXTERNAL_EXECUTOR_REQUEST_OBLIGATION_MISMATCH",
            ),
            "repository-fingerprint": (
                lambda document, root: document["repository"].update({
                    "repository_fingerprint_sha256": "e" * 64,
                }),
                "EXTERNAL_EXECUTOR_REQUEST_OBLIGATION_MISMATCH",
            ),
            "founder-intent": (
                lambda document, root: document.update({"founder_intent_sha256": "e" * 64}),
                "EXTERNAL_EXECUTOR_REQUEST_OBLIGATION_MISMATCH",
            ),
            "identity": (
                lambda document, root: document.update({"identity_root_ref": "other-identity"}),
                "EXTERNAL_EXECUTOR_REQUEST_OBLIGATION_MISMATCH",
            ),
            "member": (
                lambda document, root: document.update({"member_ref": "other-member"}),
                "EXTERNAL_EXECUTOR_REQUEST_OBLIGATION_MISMATCH",
            ),
            "seat": (
                lambda document, root: document.update({"seat_binding_ref": "other-seat"}),
                "EXTERNAL_EXECUTOR_REQUEST_OBLIGATION_MISMATCH",
            ),
            "receiver": (
                lambda document, root: document.update({"receiver_ref": "other-receiver"}),
                "RECEIVER_REF_INVALID",
            ),
            "authorization-scope": (
                lambda document, root: document["authorization"].update({"scope_sha256": "e" * 64}),
                "EXTERNAL_EXECUTOR_REQUEST_OBLIGATION_MISMATCH",
            ),
            "authorization-receipt": (
                lambda document, root: document["authorization"].update({
                    "authorization_ref": "other-authorization",
                    "authorization_expires_at": "2099-01-01T00:00:00Z",
                }),
                "EXTERNAL_EXECUTOR_REQUEST_OBLIGATION_MISMATCH",
            ),
            "decision-receipt": (
                lambda document, root: document["authorization"].update({
                    "decision_ref": "other-decision",
                    "decision_receipt_sha256": "e" * 64,
                    "decision_expires_at": "2099-01-01T00:00:00Z",
                }),
                "EXTERNAL_EXECUTOR_REQUEST_OBLIGATION_MISMATCH",
            ),
            "test-receipt-ref": (
                lambda document, root: document["source_closure"].update({
                    "test_receipt_ref": "other-test-receipt",
                }),
                "EXTERNAL_EXECUTOR_REQUEST_OBLIGATION_MISMATCH",
            ),
            "test-receipt-hash": (
                lambda document, root: document["source_closure"].update({
                    "test_receipt_sha256": "e" * 64,
                }),
                "EXTERNAL_EXECUTOR_REQUEST_OBLIGATION_MISMATCH",
            ),
            "effect-scope": (
                lambda document, root: document["safety"]["push_effects"].update({
                    "ci_webhook_deploy": "REVIEWED_AUTHORIZED",
                }),
                "EXTERNAL_EXECUTOR_REQUEST_OBLIGATION_MISMATCH",
            ),
        }
        for label, (mutate, expected_error) in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp:
                document = valid_push_obligation()
                root = Path(temp) / "executor-state"
                write_executor_state(root, document)
                mutate(document, root)
                reseal_handoff(document)
                result = validate_with_executor(document, root)
                self.assertNotEqual(result["state"], "PASS_DEFERRED_PUSH_OBLIGATION")
                self.assertIn(expected_error, result["errors"])

    def test_subject_and_test_receipt_change_executor_ticket_identity(self) -> None:
        baseline = valid_push_obligation()
        baseline_request = executor_request_for(baseline)
        mutations = {
            "identity": lambda document: document.update({"identity_root_ref": "other-identity"}),
            "member": lambda document: document.update({"member_ref": "other-member"}),
            "seat": lambda document: document.update({"seat_binding_ref": "other-seat"}),
            "receiver": lambda document: document.update({
                "receiver_ref": "TOTAL_FIELD_8D_ADI_GIT_INDEX_RECEIVER-v2",
            }),
            "test-ref": lambda document: document["source_closure"].update({
                "test_receipt_ref": "other-test-receipt",
            }),
            "test-sha": lambda document: document["source_closure"].update({
                "test_receipt_sha256": "e" * 64,
            }),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                document = json.loads(json.dumps(baseline))
                mutate(document)
                changed_request = executor_request_for(document)
                self.assertNotEqual(changed_request["origin_intent_sha256"], baseline_request["origin_intent_sha256"])
                self.assertNotEqual(changed_request["ticket_id"], baseline_request["ticket_id"])
                self.assertNotEqual(changed_request["request_sha256"], baseline_request["request_sha256"])

    def test_regenerated_ack_cannot_alias_changed_subject_to_original_ticket(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            request, event = write_executor_state(root, document)
            document["identity_root_ref"] = "other-identity"
            trust_config = json.loads(
                trust_config_path(root).read_text(encoding="utf-8")
            )
            _publish_obligation_ack(root, document, request, event, trust_config)
            result = validate_with_executor(document, root)
            changed_request = executor_request_for(document)
        self.assertNotEqual(changed_request["ticket_id"], request["ticket_id"])
        self.assertEqual(result["state"], "HOLD_EXTERNAL_EXECUTOR_ACK_INVALID")
        self.assertIn("EXTERNAL_EXECUTOR_REQUEST_OBLIGATION_MISMATCH", result["errors"])

    def test_executor_state_root_cannot_overlap_target_repository(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            repo_root = Path(temp) / "target-repository"
            repo_root.mkdir()
            document["repository"]["repo_ref"] = os.fspath(repo_root)
            bind_executor_handoff(document)
            state_root = repo_root / "executor-state"
            write_executor_state(state_root, document)
            result = validate_with_executor(document, state_root)
        self.assertIn("EXTERNAL_EXECUTOR_STATE_ROOT_OVERLAPS_REPOSITORY", result["errors"])

    def test_queue_inode_rename_after_request_read_is_held_at_final_anchor_check(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            write_executor_state(root, document)
            repository = Path(document["repository"]["repo_ref"])
            original_validate = deferred_push_module._validate_external_request
            moved = repository / "moved-executor-state"

            def validate_then_replace(request: dict, ticket_id: str) -> None:
                original_validate(request, ticket_id)
                root.rename(moved)
                root.mkdir(mode=0o750)

            with patch(
                "validate_deferred_push._validate_external_request",
                side_effect=validate_then_replace,
            ):
                result = validate_with_executor(document, root)
        self.assertEqual(result["state"], "HOLD_EXTERNAL_EXECUTOR_ACK_INVALID")
        self.assertIn(
            "EXTERNAL_EXECUTOR_STATE_ROOT_IDENTITY_DRIFT", result["errors"]
        )

    def test_queue_inode_rename_after_ack_read_defeats_resealed_replacement(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            write_executor_state(root, document)
            repository = Path(document["repository"]["repo_ref"])
            original_validate = deferred_push_module._validate_external_obligation_ack
            moved = repository / "moved-executor-state"

            def validate_then_replace(
                ack: dict,
                obligation: dict,
                request: dict,
                event: dict,
                trust: dict,
            ) -> None:
                original_validate(ack, obligation, request, event, trust)
                root.rename(moved)
                root.mkdir(mode=0o750)
                replacement_config = json.loads(
                    trust_config_path(root).read_text(encoding="utf-8")
                )
                replacement_info = root.stat()
                replacement_config["state_root_device"] = replacement_info.st_dev
                replacement_config["state_root_inode"] = replacement_info.st_ino
                replacement_config["state_root_mode"] = "0750"
                rewrite_trust_config(
                    trust_config_path(root), replacement_config, reseal=True
                )

            with patch(
                "validate_deferred_push._validate_external_obligation_ack",
                side_effect=validate_then_replace,
            ):
                result = validate_with_executor(document, root)
        self.assertEqual(result["state"], "HOLD_EXTERNAL_EXECUTOR_ACK_INVALID")
        self.assertIn(
            "EXTERNAL_EXECUTOR_STATE_ROOT_IDENTITY_DRIFT", result["errors"]
        )

    def test_queue_parent_path_replacement_is_held_at_final_anchor_check(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            anchor = base / "trusted-queue-anchor"
            anchor.mkdir(mode=0o755)
            root = anchor / "executor-state"
            repository = base / "target-repository"
            document["repository"]["repo_ref"] = os.fspath(repository)
            write_executor_state(root, document)
            original_validate = deferred_push_module._validate_external_obligation_ack
            moved_anchor = repository / "moved-trusted-queue-anchor"

            def validate_then_replace_parent(
                ack: dict,
                obligation: dict,
                request: dict,
                event: dict,
                trust: dict,
            ) -> None:
                original_validate(ack, obligation, request, event, trust)
                anchor.rename(moved_anchor)
                anchor.mkdir(mode=0o755)
                (anchor / root.name).mkdir(mode=0o750)

            with patch(
                "validate_deferred_push._validate_external_obligation_ack",
                side_effect=validate_then_replace_parent,
            ):
                result = validate_with_executor(document, root)
        self.assertEqual(result["state"], "HOLD_EXTERNAL_EXECUTOR_ACK_INVALID")
        self.assertIn(
            "EXTERNAL_EXECUTOR_STATE_ROOT_IDENTITY_DRIFT", result["errors"]
        )

    def test_waiting_external_request_cannot_hide_executable_source_evidence(self) -> None:
        document = waiting_exact_target_obligation()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            request, _ = write_executor_state(root, document)
            request["git"]["changed_paths"] = ["candidate/hidden.py"]
            request["request_sha256"] = hash_without(request, "request_sha256")
            rewrite_private_json(root / "tickets" / request["ticket_id"] / "request.json", request)
            result = validate_with_executor(document, root)
        self.assertIn("EXTERNAL_EXECUTOR_WAITING_SOURCE_INVALID", result["errors"])

    def test_external_bounded_path_parent_escape_is_rejected(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            request, _ = write_executor_state(root, document)
            request["git"]["bounded_paths"] = ["../../outside"]
            request["authorization"]["required_scope_sha256"] = _executor_execution_scope(request)
            request["request_sha256"] = hash_without(request, "request_sha256")
            rewrite_private_json(root / "tickets" / request["ticket_id"] / "request.json", request)
            result = validate_with_executor(document, root)
        self.assertIn("EXTERNAL_EXECUTOR_GIT_CANONICAL_ORDER_INVALID", result["errors"])

    def test_external_partial_legacy_authority_tuple_is_rejected(self) -> None:
        document = valid_push_obligation()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            request, _ = write_executor_state(root, document)
            request["authorization"]["total_field_scope_sha256"] = "9" * 64
            request["request_sha256"] = hash_without(request, "request_sha256")
            rewrite_private_json(root / "tickets" / request["ticket_id"] / "request.json", request)
            result = validate_with_executor(document, root)
        self.assertIn("EXTERNAL_EXECUTOR_AUTHORIZATION_INVALID", result["errors"])

    def test_change_set_hash_is_derived_from_canonical_changes(self) -> None:
        document = valid_push_obligation()
        document["change_set_sha256"] = "8" * 64
        reseal_handoff(document)
        self.assertIn("CHANGE_SET_SHA256_MISMATCH", validate_deferred_push(document)["errors"])

    def test_ready_authorization_cannot_be_false(self) -> None:
        document = valid_push_obligation()
        document["state"] = "READY_TO_PUSH"
        document["authorization"].update({
            "required": False,
            "authorization_ref": "authority-1",
            "authorization_expires_at": "2099-08-27T00:00:00Z",
            "decision_ref": "decision-1",
            "decision_receipt_sha256": "b" * 64,
            "decision_expires_at": "2099-08-27T00:00:00Z",
        })
        document["schedule"].update({
            "scheduler_state": "ACTIVE_DURABLE_SCHEDULER",
            "scheduler_job_ref": "job-1",
            "executor_lease_ref": "lease-1",
            "executor_lease_expires_at": "2099-08-27T00:00:00Z",
        })
        reseal_handoff(document)
        self.assertIn(
            "READY_TO_PUSH_AUTHORIZATION_REQUIRED_MUST_BE_TRUE",
            validate_deferred_push(document)["errors"],
        )

    def test_ready_requires_canonical_current_authority_and_lease_windows(self) -> None:
        document = valid_push_obligation()
        document["state"] = "READY_TO_PUSH"
        document["authorization"].update({
            "required": True,
            "authorization_ref": "authority-1",
            "authorization_expires_at": "2026-08-27T08:00:00+08:00",
            "decision_ref": "decision-1",
            "decision_receipt_sha256": "b" * 64,
            "decision_expires_at": "2099-08-27T00:00:00Z",
        })
        document["schedule"].update({
            "scheduler_state": "ACTIVE_DURABLE_SCHEDULER",
            "scheduler_job_ref": "job-1",
            "executor_lease_ref": "lease-1",
            "executor_lease_expires_at": "2000-01-01T00:00:00Z",
        })
        reseal_handoff(document)
        errors = validate_deferred_push(document)["errors"]
        self.assertIn("AUTHORIZATION_RECEIPT_WINDOW_INVALID", errors)
        self.assertIn("EXECUTOR_LEASE_EXPIRED", errors)

    def test_schedule_time_order_is_canonical(self) -> None:
        document = valid_push_obligation()
        document["schedule"]["next_attempt_at"] = "2026-09-04T00:00:00Z"
        reseal_handoff(document)
        self.assertIn("SCHEDULE_TIME_ORDER_INVALID", validate_deferred_push(document)["errors"])

    def test_empty_consume_and_cas_terminal_fixture_is_never_verified(self) -> None:
        document = valid_push_obligation()
        document["state"] = "PUSHED_VERIFIED"
        document["schedule"]["scheduler_state"] = "TERMINAL"
        document["schedule"]["next_attempt_at"] = None
        document["executor_handoff"]["handoff_state"] = "TERMINAL_AUTHORITATIVE_RECHECK_REQUIRED"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            write_executor_state(root, document)
            add_terminal_executor_evidence(root, document)
            result = validate_with_executor(document, root)
        self.assertEqual(result["state"], "HOLD_EXTERNAL_EXECUTOR_TERMINAL_UNVERIFIED")
        self.assertFalse(result["terminal_readback_verified"])
        self.assertTrue(result["terminal_receipt_integrity_loaded"])
        self.assertIn("EXTERNAL_EXECUTOR_TERMINAL_SEMANTICS_UNVERIFIED", result["errors"])
        self.assertIn("TERMINAL_AUTHORITATIVE_RECHECK_REQUIRED", result["errors"])

    def test_cli_rejects_duplicate_keys_and_noncanonical_bytes(self) -> None:
        script = Path(__file__).with_name("validate_deferred_push.py")
        with tempfile.TemporaryDirectory() as temp:
            duplicate = Path(temp) / "duplicate.json"
            duplicate.write_text('{"schema_version":"x","schema_version":"y"}\n', encoding="utf-8")
            duplicate_result = subprocess.run(
                [sys.executable, os.fspath(script), os.fspath(duplicate)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(duplicate_result.returncode, 0)
            self.assertIn("INPUT_JSON_INVALID_OR_DUPLICATE_KEY", duplicate_result.stdout)

            document = valid_push_obligation()
            noncanonical = Path(temp) / "pretty.json"
            noncanonical.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
            noncanonical_result = subprocess.run(
                [sys.executable, os.fspath(script), os.fspath(noncanonical)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(noncanonical_result.returncode, 0)
            self.assertIn("INPUT_BYTES_NOT_CANONICAL_JSON", noncanonical_result.stdout)

    def test_missing_executor_handoff_is_rejected(self) -> None:
        document = valid_push_obligation()
        document.pop("executor_handoff")
        errors = validate_deferred_push(document)["errors"]
        self.assertIn("EXECUTOR_HANDOFF_MISSING", errors)
        self.assertIn("TOP_LEVEL_CLOSED_SCHEMA_FIELDS_INVALID", errors)

    def test_malformed_executor_handoff_fails_closed(self) -> None:
        document = valid_push_obligation()
        document["executor_handoff"] = []
        self.assertIn("EXECUTOR_HANDOFF_MISSING", validate_deferred_push(document)["errors"])

    def test_wrong_executor_is_rejected_even_with_recomputed_hash(self) -> None:
        document = valid_push_obligation()
        document["executor_handoff"]["executor_skill_ref"] = "$some-other-push-executor"
        reseal_handoff(document)
        self.assertIn(
            "EXECUTOR_HANDOFF_SKILL_REF_INVALID",
            validate_deferred_push(document)["errors"],
        )

    def test_handoff_input_contract_is_exact(self) -> None:
        document = valid_push_obligation()
        document["executor_handoff"]["input_contract_version"] = "2.0"
        reseal_handoff(document)
        self.assertIn(
            "EXECUTOR_HANDOFF_INPUT_CONTRACT_VERSION_INVALID",
            validate_deferred_push(document)["errors"],
        )

    def test_handoff_hash_covers_obligation_and_executor_ack(self) -> None:
        document = valid_push_obligation()
        document["executor_handoff"]["executor_queue_ack_sha256"] = "b" * 64
        self.assertIn("EXECUTOR_HANDOFF_SHA256_MISMATCH", validate_deferred_push(document)["errors"])

    def test_handoff_cross_bindings_are_required_after_rehash(self) -> None:
        document = valid_push_obligation()
        document["executor_handoff"]["obligation_id"] = "different-obligation"
        document["executor_handoff"]["executor_queue_ack_ref"] = "different-ack"
        reseal_handoff(document)
        errors = validate_deferred_push(document)["errors"]
        self.assertIn("EXECUTOR_HANDOFF_OBLIGATION_ID_MISMATCH", errors)
        self.assertIn("EXECUTOR_HANDOFF_QUEUE_ACK_REF_INVALID", errors)

    def test_route_never_grants_activation(self) -> None:
        document = valid_push_obligation()
        document["executor_handoff"]["activation_state"] = "ACTIVE"
        reseal_handoff(document)
        self.assertIn(
            "EXECUTOR_HANDOFF_CANNOT_GRANT_ACTIVATION",
            validate_deferred_push(document)["errors"],
        )

    def test_legacy_v1_schemas_are_read_only_migration_holds(self) -> None:
        for version in ("1.0", "1.1"):
            with self.subTest(version=version):
                document = valid_push_obligation()
                document["schema_version"] = f"w7tp-deferred-git-push-obligation/{version}"
                document.pop("executor_handoff")
                result = validate_deferred_push(document)
                self.assertEqual(
                    result["state"],
                    "HOLD_LEGACY_PUSH_OBLIGATION_MIGRATION_REQUIRED",
                )
                self.assertEqual(result["legacy_validation"], "PASS_LEGACY_READ_ONLY")
                self.assertEqual(
                    result["migration_target_schema"],
                    "w7tp-deferred-git-push-obligation/1.2",
                )
                self.assertFalse(result["execution_routed"])
                self.assertIn("EXECUTOR_HANDOFF_MIGRATION_REQUIRED", result["errors"])

    def test_queue_ack_is_mandatory(self) -> None:
        document = valid_push_obligation()
        document["queue_store"]["append_only_ack_ref"] = None
        self.assertIn("QUEUE_APPEND_ONLY_ACK_REF_MISSING", validate_deferred_push(document)["errors"])

    def test_queue_ack_sha256_is_mandatory(self) -> None:
        document = valid_push_obligation()
        document["queue_store"]["append_only_ack_sha256"] = "bad"
        self.assertIn(
            "QUEUE_APPEND_ONLY_ACK_SHA256_INVALID",
            validate_deferred_push(document)["errors"],
        )

    def test_queue_only_inside_target_repo_is_rejected(self) -> None:
        document = valid_push_obligation()
        document["queue_store"]["outside_target_repo"] = False
        self.assertIn("QUEUE_STORE_MUST_SURVIVE_UNPUSHED_REPO", validate_deferred_push(document)["errors"])

    def test_force_push_is_rejected(self) -> None:
        document = valid_push_obligation()
        document["safety"]["force_push"] = True
        self.assertIn("SAFETY_FORCE_PUSH_INVALID", validate_deferred_push(document)["errors"])

    def test_refspec_must_bind_one_source_and_target(self) -> None:
        document = valid_push_obligation()
        document["repository"]["refspec"] = "HEAD:refs/heads/other"
        self.assertIn("REFSPEC_INVALID", validate_deferred_push(document)["errors"])

    def test_ready_requires_authorization_scheduler_and_lease(self) -> None:
        document = valid_push_obligation()
        document["state"] = "READY_TO_PUSH"
        errors = validate_deferred_push(document)["errors"]
        self.assertIn("READY_TO_PUSH_AUTHORIZATION_RECEIPT_MISSING", errors)
        self.assertIn("READY_TO_PUSH_REQUIRES_ACTIVE_SCHEDULER", errors)
        self.assertIn("READY_TO_PUSH_EXECUTOR_LEASE_MISSING", errors)

    def test_waiting_exact_target_is_queued_but_non_executable(self) -> None:
        document = waiting_exact_target_obligation()
        self.assertEqual(
            validate_deferred_push(document)["state"],
            "HOLD_TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE",
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "executor-state"
            write_executor_state(root, document)
            result = validate_with_executor(document, root)
        self.assertEqual(result["state"], "PASS_DEFERRED_PUSH_OBLIGATION")
        self.assertEqual(result["handoff_state"], "WAITING_EXACT_TARGET")
        self.assertFalse(result["execution_authorized"])
        document["state"] = "READY_TO_PUSH"
        reseal_handoff(document)
        errors = validate_deferred_push(document)["errors"]
        self.assertIn("READY_TO_PUSH_HAS_UNRESOLVED_PREREQUISITE", errors)
        self.assertIn("WAITING_EXACT_TARGET_CANNOT_BE_EXECUTABLE", errors)

    def test_waiting_exact_target_cannot_carry_source_evidence(self) -> None:
        document = waiting_exact_target_obligation()
        document["source_closure"]["tree_oid"] = "4" * 40
        reseal_handoff(document)
        self.assertIn(
            "WAITING_EXACT_TARGET_HAS_EXECUTABLE_SOURCE_EVIDENCE",
            validate_deferred_push(document)["errors"],
        )

    def test_waiting_exact_target_cannot_carry_executor_lease(self) -> None:
        document = waiting_exact_target_obligation()
        document["schedule"]["executor_lease_ref"] = "lease-1"
        document["schedule"]["executor_lease_expires_at"] = "2099-08-27T00:00:00Z"
        reseal_handoff(document)
        self.assertIn(
            "WAITING_EXACT_TARGET_HAS_EXECUTOR_LEASE",
            validate_deferred_push(document)["errors"],
        )

    def test_waiting_exact_target_requires_exact_resume_semantics(self) -> None:
        document = waiting_exact_target_obligation()
        document["blocker"]["code"] = "REVIEW_PENDING"
        document["schedule"]["resume_trigger"] = "REVIEW_RECEIPT_AVAILABLE"
        reseal_handoff(document)
        errors = validate_deferred_push(document)["errors"]
        self.assertIn("WAITING_EXACT_TARGET_BLOCKER_INVALID", errors)
        self.assertIn("WAITING_EXACT_TARGET_RESUME_TRIGGER_INVALID", errors)

    def test_unknown_handoff_field_is_rejected_after_rehash(self) -> None:
        document = valid_push_obligation()
        document["executor_handoff"]["executable"] = True
        reseal_handoff(document)
        self.assertIn(
            "EXECUTOR_HANDOFF_CLOSED_SCHEMA_FIELDS_INVALID",
            validate_deferred_push(document)["errors"],
        )

    def test_unreviewed_push_effect_is_rejected(self) -> None:
        document = valid_push_obligation()
        document["safety"]["push_effects"]["ci_webhook_deploy"] = "UNKNOWN"
        self.assertIn("PUSH_EFFECT_CI_WEBHOOK_DEPLOY_UNRESOLVED", validate_deferred_push(document)["errors"])

    def test_pushed_state_requires_remote_readback(self) -> None:
        document = valid_push_obligation()
        document["state"] = "PUSHED_VERIFIED"
        document["schedule"]["scheduler_state"] = "TERMINAL"
        document["schedule"]["next_attempt_at"] = None
        self.assertIn("PUSHED_REMOTE_READBACK_RECEIPT_MISSING", validate_deferred_push(document)["errors"])

    def test_pushed_remote_oid_must_equal_source(self) -> None:
        document = valid_push_obligation()
        document["state"] = "PUSHED_VERIFIED"
        document["schedule"]["scheduler_state"] = "TERMINAL"
        document["schedule"]["next_attempt_at"] = None
        document["closure"] = {
            "remote_commit_oid": "9" * 40,
            "remote_readback_receipt_ref": "remote-receipt-1",
        }
        self.assertIn("PUSHED_REMOTE_OID_NOT_SOURCE_OID", validate_deferred_push(document)["errors"])

    def test_pushed_terminal_routes_authoritative_recheck(self) -> None:
        document = valid_push_obligation()
        document["state"] = "PUSHED_VERIFIED"
        document["schedule"]["scheduler_state"] = "TERMINAL"
        document["schedule"]["next_attempt_at"] = None
        document["closure"] = {
            "remote_commit_oid": document["repository"]["source_oid"],
            "remote_readback_receipt_ref": "remote-receipt-1",
        }
        document["executor_handoff"]["handoff_state"] = "TERMINAL_AUTHORITATIVE_RECHECK_REQUIRED"
        reseal_handoff(document)
        result = validate_deferred_push(document)
        self.assertEqual(result["state"], "HOLD_TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE")
        self.assertFalse(result["executor_queue_ack_verified"])
        self.assertTrue(result["execution_routed"])

    def test_pushed_record_keeps_terminal_route_when_external_queue_is_unreadable(self) -> None:
        document = valid_push_obligation()
        document["state"] = "PUSHED_VERIFIED"
        document["schedule"]["scheduler_state"] = "TERMINAL"
        document["schedule"]["next_attempt_at"] = None
        document["closure"] = {
            "remote_commit_oid": document["repository"]["source_oid"],
            "remote_readback_receipt_ref": "tickets/unverified/receipts/unverified.json",
        }
        document["executor_handoff"]["handoff_state"] = "TERMINAL_AUTHORITATIVE_RECHECK_REQUIRED"
        reseal_handoff(document)
        with tempfile.TemporaryDirectory() as temp:
            result = validate_deferred_push(
                document,
                executor_state_root=Path(temp) / "missing-executor-state",
            )
        self.assertEqual(result["state"], "HOLD_TRUSTED_EXECUTOR_QUEUE_UNAVAILABLE")
        self.assertTrue(result["execution_routed"])
        self.assertFalse(result["terminal_readback_verified"])

    def test_pushed_terminal_without_recheck_route_is_rejected(self) -> None:
        document = valid_push_obligation()
        document["state"] = "PUSHED_VERIFIED"
        document["schedule"]["scheduler_state"] = "TERMINAL"
        document["schedule"]["next_attempt_at"] = None
        document["closure"] = {
            "remote_commit_oid": document["repository"]["source_oid"],
            "remote_readback_receipt_ref": "remote-receipt-1",
        }
        reseal_handoff(document)
        self.assertIn(
            "PUSHED_TERMINAL_RECHECK_HANDOFF_REQUIRED",
            validate_deferred_push(document)["errors"],
        )

    def test_founder_cancellation_requires_receipt(self) -> None:
        document = valid_push_obligation()
        document["state"] = "CANCELLED_BY_FOUNDER"
        document["schedule"]["scheduler_state"] = "TERMINAL"
        document["schedule"]["next_attempt_at"] = None
        self.assertIn("FOUNDER_CANCEL_RECEIPT_MISSING", validate_deferred_push(document)["errors"])

    def test_secret_shaped_fields_are_rejected(self) -> None:
        document = valid_push_obligation()
        document["token"] = "must-not-be-stored"
        self.assertIn("SECRET_SHAPED_FIELD_FORBIDDEN", validate_deferred_push(document)["errors"])


class ReviewGateTests(unittest.TestCase):
    def make_change(self, root: Path, text: str = "safe evidence\n") -> tuple[dict, Path]:
        git_dir = root / ".git"
        git_dir.mkdir()
        index_content = b"DIRC" + struct.pack(">II", 2, 0)
        (git_dir / "index").write_bytes(index_content + hashlib.sha1(index_content).digest())
        skill_root = root / "new-skill"
        skill_root.mkdir()
        evidence_root = skill_root / "evidence"
        evidence_root.mkdir()
        target = evidence_root / "evidence.md"
        target.write_text(text, encoding="utf-8")
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        document = {
            "schema_version": "w7tp-git-change-review/1.0",
            "candidate_root": "new-skill",
            "operations": ["ADD_REVIEW_EVIDENCE"],
            "changes": [{"status": "A", "path": "new-skill/evidence/evidence.md", "sha256": digest}],
        }
        return document, target

    def test_add_only_candidate_is_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            document, _ = self.make_change(root)
            result = classify(document, root)
            self.assertEqual(result["decision"], "SAFE_PUSH_CANDIDATE")
            self.assertFalse(result["direct_push_allowed"])
            self.assertEqual(result["executor_route"], "$complete-deferred-git-push")
            self.assertTrue(result["executor_handoff_required_for_remote_delivery"])

    def test_modification_requires_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            document, _ = self.make_change(root)
            document["changes"][0]["status"] = "M"
            self.assertEqual(classify(document, root)["decision"], "REVIEW_REQUIRED")

    def test_force_push_operation_is_held(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            document, _ = self.make_change(root)
            document["operations"] = ["FORCE_PUSH"]
            self.assertEqual(classify(document, root)["decision"], "HOLD_PROTECTED_GIT_EFFECT")

    def test_live_object_operation_is_held(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            document, _ = self.make_change(root)
            document["operations"] = ["LIVE_OBJECT_DB_WRITE"]
            self.assertEqual(classify(document, root)["decision"], "HOLD_PROTECTED_GIT_EFFECT")

    def test_hash_mismatch_is_held(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            document, _ = self.make_change(root)
            document["changes"][0]["sha256"] = "0" * 64
            self.assertEqual(classify(document, root)["decision"], "HOLD_PROTECTED_GIT_EFFECT")

    def test_symlink_is_held(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            git_dir = root / ".git"
            git_dir.mkdir()
            index_content = b"DIRC" + struct.pack(">II", 2, 0)
            (git_dir / "index").write_bytes(index_content + hashlib.sha1(index_content).digest())
            skill_root = root / "new-skill"
            skill_root.mkdir()
            real = root / "real-evidence.md"
            real.write_text("safe evidence\n", encoding="utf-8")
            target = skill_root / "evidence.md"
            target.symlink_to(real)
            document = {
                "schema_version": "w7tp-git-change-review/1.0",
                "candidate_root": "new-skill",
                "operations": ["ADD_REVIEW_EVIDENCE"],
                "changes": [{"status": "A", "path": "new-skill/evidence.md", "sha256": hashlib.sha256(real.read_bytes()).hexdigest()}],
            }
            self.assertEqual(classify(document, root)["decision"], "HOLD_PROTECTED_GIT_EFFECT")

    def test_tracked_path_cannot_claim_addition(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            document, _ = self.make_change(root)
            with patch("git_review_gate.git_index_membership", return_value="TRACKED"):
                self.assertEqual(classify(document, root)["decision"], "HOLD_PROTECTED_GIT_EFFECT")

    def test_non_object_document_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(classify([], Path(temp))["decision"], "HOLD_PROTECTED_GIT_EFFECT")

    def test_non_string_operation_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            document, _ = self.make_change(root)
            document["operations"] = [{"operation": "ADD_REVIEW_EVIDENCE"}]
            self.assertEqual(classify(document, root)["decision"], "HOLD_PROTECTED_GIT_EFFECT")

    def test_malformed_lifecycle_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            document, _ = self.make_change(root)
            manifest = root / "new-skill" / "total-field-skill-manifest.json"
            manifest.write_text(json.dumps({"manifest_state": "CANDIDATE_FOR_TOTAL_FIELD_REVIEW", "lifecycle": []}), encoding="utf-8")
            document["changes"] = [{
                "status": "A",
                "path": "new-skill/total-field-skill-manifest.json",
                "sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
            }]
            self.assertEqual(classify(document, root)["decision"], "HOLD_PROTECTED_GIT_EFFECT")

    def test_repository_root_is_not_candidate_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            document, _ = self.make_change(root)
            document["candidate_root"] = "."
            self.assertEqual(classify(document, root)["decision"], "HOLD_PROTECTED_GIT_EFFECT")

    def test_benign_python_requires_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            document, _ = self.make_change(root)
            source = root / "new-skill" / "validator.py"
            source.write_text("value = 1\n", encoding="utf-8")
            document["changes"] = [{
                "status": "A",
                "path": "new-skill/validator.py",
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            }]
            self.assertEqual(classify(document, root)["decision"], "REVIEW_REQUIRED")

    def test_process_capability_is_held(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            document, _ = self.make_change(root)
            source = root / "new-skill" / "danger.py"
            source.write_text('import os\nos.system("git push --force")\n', encoding="utf-8")
            document["changes"] = [{
                "status": "A",
                "path": "new-skill/danger.py",
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            }]
            self.assertEqual(classify(document, root)["decision"], "HOLD_PROTECTED_GIT_EFFECT")

    def test_ci_autoload_path_is_held(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            git_dir = root / ".git"
            git_dir.mkdir()
            index_content = b"DIRC" + struct.pack(">II", 2, 0)
            (git_dir / "index").write_bytes(index_content + hashlib.sha1(index_content).digest())
            workflow = root / "candidate" / ".github" / "workflows" / "run.yml"
            workflow.parent.mkdir(parents=True)
            workflow.write_text("on: [push]\n", encoding="utf-8")
            document = {
                "schema_version": "w7tp-git-change-review/1.0",
                "candidate_root": "candidate",
                "operations": ["ADD_REVIEW_EVIDENCE"],
                "changes": [{
                    "status": "A",
                    "path": "candidate/.github/workflows/run.yml",
                    "sha256": hashlib.sha256(workflow.read_bytes()).hexdigest(),
                }],
            }
            self.assertEqual(classify(document, root)["decision"], "HOLD_PROTECTED_GIT_EFFECT")

    def test_skill_instruction_file_requires_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            document, _ = self.make_change(root)
            instruction = root / "new-skill" / "SKILL.md"
            instruction.write_text("Run a destructive command.\n", encoding="utf-8")
            document["operations"] = ["ADD_CANDIDATE_SKILL_INSTRUCTIONS"]
            document["changes"] = [{
                "status": "A",
                "path": "new-skill/SKILL.md",
                "sha256": hashlib.sha256(instruction.read_bytes()).hexdigest(),
            }]
            self.assertEqual(classify(document, root)["decision"], "REVIEW_REQUIRED")

    def test_agents_instruction_file_requires_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            document, _ = self.make_change(root)
            instruction = root / "new-skill" / "AGENTS.md"
            instruction.write_text("Run a destructive command.\n", encoding="utf-8")
            document["operations"] = ["ADD_REVIEW_EVIDENCE"]
            document["changes"] = [{
                "status": "A",
                "path": "new-skill/AGENTS.md",
                "sha256": hashlib.sha256(instruction.read_bytes()).hexdigest(),
            }]
            self.assertEqual(classify(document, root)["decision"], "REVIEW_REQUIRED")

    def test_agent_control_directory_requires_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            document, _ = self.make_change(root)
            rule = root / "new-skill" / ".cursor" / "rules.md"
            rule.parent.mkdir()
            rule.write_text("Run a destructive command.\n", encoding="utf-8")
            document["operations"] = ["ADD_REVIEW_EVIDENCE"]
            document["changes"] = [{
                "status": "A",
                "path": "new-skill/.cursor/rules.md",
                "sha256": hashlib.sha256(rule.read_bytes()).hexdigest(),
            }]
            self.assertEqual(classify(document, root)["decision"], "REVIEW_REQUIRED")

    def test_root_declarative_file_requires_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            document, _ = self.make_change(root)
            note = root / "new-skill" / "notes.md"
            note.write_text("ordinary note\n", encoding="utf-8")
            document["operations"] = ["ADD_REVIEW_EVIDENCE"]
            document["changes"] = [{
                "status": "A",
                "path": "new-skill/notes.md",
                "sha256": hashlib.sha256(note.read_bytes()).hexdigest(),
            }]
            self.assertEqual(classify(document, root)["decision"], "REVIEW_REQUIRED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
