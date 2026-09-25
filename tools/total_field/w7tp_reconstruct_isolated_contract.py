#!/usr/bin/env python3
"""Pure contract and canonical-hash helpers for RECONSTRUCT_ISOLATED V2.

This module defines a versioned successor contract.  It does not import,
modify, or replace the P2 V1 reviewer and has no runtime side effects.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any


CONTRACT_ID = "W7TP-TOTAL-FIELD-RECONSTRUCT-ISOLATED/2.0"
RECEIPT_CONTRACT_ID = "W7TP-TOTAL-FIELD-RECONSTRUCT-ISOLATED-RECEIPT/2.0"
DECISION_CONTRACT_ID = "W7TP-TOTAL-FIELD-RECONSTRUCT-ISOLATED-DECISION/2.0"
REQUEST_HASH_ALGORITHM = "SHA256_CANONICAL_JSON_EXCLUDING_REQUEST_SELF_SHA256/1.0"
SCOPE_HASH_ALGORITHM = "SHA256_CANONICAL_JSON_RECONSTRUCT_ISOLATED_SCOPE/2.0"
DECISION_HASH_ALGORITHM = "SHA256_CANONICAL_JSON_EXCLUDING_DECISION_SHA256/1.0"
RECEIPT_HASH_ALGORITHM = "SHA256_CANONICAL_JSON_EXCLUDING_RECEIPT_SELF_SHA256/1.0"

TARGET_NODE = "taiji01"
TARGET_FIELD_SNAPSHOT_SHA256 = "4acccea6e5caaa085857fa65c665e25bb9463394860e324de158d5bec35dc323"
TARGET_BASE_STATE_SHA256 = "2253afcc5d72625ed8f3af5a4267669f5dd8e9a9c6cbea044a90c3ba70f2dce2"
TARGET_SUCCESSOR_CANONICAL_SHA256 = "383aba5b7a9f5d0e948d9b43b83e7dd6b6ec9c27f025fb9069e83810f0ae870d"
MINIMUM_GENERATIVE_DELTA_SHA256 = "ab875e3ea504cdcdbedd63416dd89e36ab9e491a4dfa34b28a21da411d269782"
RECONSTRUCTION_CALLABLE = "tools.w7tp_secondary_cloud_packet_ramp.reconstruct_local_state"
TARGET_NATIVE_GATEWAY = "tools/total_field_candidate_gateway.py"
MAX_REQUEST_TTL_SECONDS = 3600
MAXIMUM_EFFECT = "ONE_ISOLATED_TARGET_NATIVE_RECONSTRUCTION_RUN"

DELTA_ITEMS = (
    "SUCCESSOR_EXACT_SHA_SHADOW_CONSUMER_BINDING",
    "9107_OUTPUT_TO_RECONSTRUCT_LOCAL_STATE_BINDING_ONLY",
)
AUTHORIZED_STEP_ALLOWLIST = frozenset(
    {
        "VERIFY_BOUND_TARGET_STATE_AND_AUTHORIZATION",
        "CREATE_ONE_BOUNDED_ISOLATED_WORKSPACE",
        "FORM_SUCCESSOR_SHADOW_BINDING",
        "FORM_9107_RECONSTRUCTION_CALL_EDGE_BINDING",
        "RUN_TARGET_NATIVE_VERIFICATION",
        "EMIT_TARGET_NATIVE_RECONSTRUCTION_EVIDENCE",
        "RUN_RED_TEAM_POST_RECONSTRUCTION",
    }
)
FORBIDDEN_EFFECT_NAMES = (
    "LIVE_REBIND",
    "LIVE_9107_MUTATION",
    "LIVE_STATE_STORE_WRITE",
    "DB_WRITE",
    "SERVICE_RESTART",
    "DEPLOYMENT",
    "CANONICAL_MUTATION",
    "POINTER_MUTATION",
    "PROMOTION",
    "ACTIVATION",
    "LANDING",
    "FINAL_AUTHORITY_BOOTSTRAP",
    "SIGNER_REPAIR",
    "KEY_ROTATION",
    "IMAGE_PULL",
    "NETWORK_BUILD",
    "9110_CREATION",
    "UNDECLARED_ADAPTER_CREATION",
)
SCOPE_FIELDS = (
    "requested_action",
    "target",
    "delta",
    "workspace",
    "reconstruction_base",
    "exact_targets",
    "input_hashes",
    "authority",
    "authorized_steps",
    "maximum_effect",
    "expected_effect",
    "affected_state",
    "risks",
    "safeguards",
    "rollback",
    "stop_conditions",
    "forbidden_effects",
    "existing_services",
    "single_use",
    "created_at",
    "expires_at",
    "replay_root",
    "total_field_review_required",
    "lineage",
)


def canonical_json_bytes(value: Any) -> bytes:
    """Reuse the P2 V1 canonical JSON rule exactly."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def self_hash(value: dict[str, Any], excluded_field: str) -> str:
    material = deepcopy(value)
    material.pop(excluded_field, None)
    return sha256_bytes(canonical_json_bytes(material))


def scope_material(request: dict[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(request[field]) for field in SCOPE_FIELDS}


def scope_hash(request: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(scope_material(request)))


def exact_targets_for(workspace_root: str) -> list[str]:
    return [
        f"{workspace_root}/TARGET_SUCCESSOR_SHADOW_BINDING_CANDIDATE.json",
        f"{workspace_root}/W7TP_9107_RECONSTRUCTION_CALL_EDGE_BINDING_CANDIDATE.json",
    ]


def make_request(run_id: str, created_at: str, expires_at: str) -> dict[str, Any]:
    """Build a deterministic typed request for static validation only."""

    workspace_root = f"runtime/isolated/{run_id}"
    request: dict[str, Any] = {
        "contract": CONTRACT_ID,
        "request_id": f"W7TP_RECONSTRUCT_ISOLATED_V2_{run_id}",
        "request_self_hash_algorithm": REQUEST_HASH_ALGORITHM,
        "request_self_sha256": "0" * 64,
        "scope_hash_algorithm": SCOPE_HASH_ALGORITHM,
        "scope_sha256": "0" * 64,
        "requested_action": "RECONSTRUCT_ISOLATED",
        "target": {
            "node": TARGET_NODE,
            "field_snapshot_sha256": TARGET_FIELD_SNAPSHOT_SHA256,
            "base_state_sha256": TARGET_BASE_STATE_SHA256,
            "canonical_sha256": TARGET_SUCCESSOR_CANONICAL_SHA256,
        },
        "delta": {"sha256": MINIMUM_GENERATIVE_DELTA_SHA256, "items": list(DELTA_ITEMS)},
        "workspace": {
            "root": workspace_root,
            "write_scope": "THIS_DIRECTORY_ONLY",
            "repository_mount": "READ_ONLY",
            "network": "NONE",
            "service_autoload": False,
            "live_volume_mount": False,
            "db_access": False,
            "state_store_access": False,
        },
        "reconstruction_base": {
            "callable": RECONSTRUCTION_CALLABLE,
            "new_adapter_required": False,
            "gateway": TARGET_NATIVE_GATEWAY,
        },
        "exact_targets": exact_targets_for(workspace_root),
        "input_hashes": {
            "target_field_snapshot_sha256": TARGET_FIELD_SNAPSHOT_SHA256,
            "target_base_state_sha256": TARGET_BASE_STATE_SHA256,
            "target_successor_canonical_sha256": TARGET_SUCCESSOR_CANONICAL_SHA256,
            "minimum_generative_delta_sha256": MINIMUM_GENERATIVE_DELTA_SHA256,
        },
        "authority": {
            "pointer_ref": "runtime/total_field/authority/ACTIVE_TOTAL_FIELD_AUTHORITY.json",
            "pointer_sha256": "a" * 64,
            "founder_authorization_ref": "runtime/total_field/authorization/RECONSTRUCT_ISOLATED_AUTHORIZATION.json",
            "founder_authorization_sha256": "b" * 64,
            "authorized_effect": "AUTHORIZE_RECONSTRUCT_ISOLATED_REVIEW_ONLY",
        },
        "authorized_steps": sorted(AUTHORIZED_STEP_ALLOWLIST),
        "maximum_effect": MAXIMUM_EFFECT,
        "expected_effect": "FORM_TWO_ISOLATED_BINDING_CANDIDATES_VERIFY_AND_EMIT_EVIDENCE",
        "affected_state": [
            "ISOLATED_SUCCESSOR_SHADOW_CONSUMER_BINDING_CANDIDATE",
            "ISOLATED_9107_RECONSTRUCTION_CALL_EDGE_BINDING_CANDIDATE",
        ],
        "risks": ["PATH_ESCAPE", "REPLAY", "LIVE_SCOPE_OVERLAP", "FALSE_EVIDENCE"],
        "safeguards": [
            "FAIL_CLOSED_V2_VALIDATOR",
            "DECISION_RUNNER_HASH_REBIND",
            "READ_ONLY_REPOSITORY_MOUNT",
            "NETWORK_NONE",
            "POST_RECONSTRUCTION_RED_TEAM_REQUIRED",
        ],
        "rollback": {
            "method": "DELETE_ONLY_THIS_ISOLATED_WORKSPACE",
            "live_state_restore_required": False,
        },
        "stop_conditions": [
            "ANY_HASH_OR_COORDINATE_MISMATCH",
            "ANY_SCOPE_OR_DECISION_MISMATCH",
            "AUTHORIZATION_EXPIRED_OR_REPLAYED",
            "WORKSPACE_CONTAINMENT_UNPROVEN",
            "ANY_FORBIDDEN_EFFECT_REQUESTED",
            "ANY_EXISTING_SERVICE_STATE_CHANGE",
            "UNEXPECTED_NEW_ADAPTER_REQUIREMENT",
            "ANY_9110_REQUIREMENT",
            "ANY_RED_TEAM_HIGH_OR_CRITICAL",
        ],
        "existing_services": "UNCHANGED",
        "forbidden_effects": {name: False for name in FORBIDDEN_EFFECT_NAMES},
        "single_use": True,
        "created_at": created_at,
        "expires_at": expires_at,
        "replay_root": f"{workspace_root}/evidence",
        "total_field_review_required": True,
        "lineage": {
            "predecessor": "P2_ISOLATED_CANARY_V1",
            "relation": "VERSIONED_STRONG_COVER",
            "v1_preserved": True,
            "v1_mutated": False,
        },
    }
    request["scope_sha256"] = scope_hash(request)
    request["request_self_sha256"] = self_hash(request, "request_self_sha256")
    return request


__all__ = [
    "AUTHORIZED_STEP_ALLOWLIST",
    "CONTRACT_ID",
    "DECISION_CONTRACT_ID",
    "DECISION_HASH_ALGORITHM",
    "DELTA_ITEMS",
    "FORBIDDEN_EFFECT_NAMES",
    "MAXIMUM_EFFECT",
    "MAX_REQUEST_TTL_SECONDS",
    "MINIMUM_GENERATIVE_DELTA_SHA256",
    "RECEIPT_CONTRACT_ID",
    "RECEIPT_HASH_ALGORITHM",
    "RECONSTRUCTION_CALLABLE",
    "REQUEST_HASH_ALGORITHM",
    "SCOPE_HASH_ALGORITHM",
    "TARGET_BASE_STATE_SHA256",
    "TARGET_FIELD_SNAPSHOT_SHA256",
    "TARGET_NATIVE_GATEWAY",
    "TARGET_NODE",
    "TARGET_SUCCESSOR_CANONICAL_SHA256",
    "canonical_json_bytes",
    "exact_targets_for",
    "make_request",
    "scope_hash",
    "scope_material",
    "self_hash",
    "sha256_bytes",
]
