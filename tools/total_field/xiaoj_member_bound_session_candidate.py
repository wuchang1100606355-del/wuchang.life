#!/usr/bin/env python3
"""Member-only XiaoJ session and exclusive Founder developer-seat candidate.

The module consumes deidentified references and an already verified role-table
snapshot supplied by the caller. It performs no database, network, deploy,
restart, router, Canonical, role-activation, or plaintext operation.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/xiaoj_member_bound_developer_seat_candidate.schema.json"
POLICY_PATH = ROOT / "manifests/xiaoj_member_bound_developer_seat_candidate_v0_1/policy.json"
FORBIDDEN_CLOUD_KEYS = frozenset({"member_ref", "member_plaintext", "token", "secret", "credential", "password"})


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    if not isinstance(value, dict):
        raise ValueError("POLICY_OR_SCHEMA_OBJECT_REQUIRED")
    return value


def canonical_sha256(value: Any) -> str:
    """Hash one deterministic reference-only object."""

    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _base(state: str, d7: str) -> dict[str, Any]:
    return {
        "state": state,
        "d7_disposition": d7,
        "candidate_only": True,
        "role_activated": False,
        "final_authority": False,
        "db_write": False,
        "deploy": False,
        "restart": False,
        "router_write": False,
        "canonical_change": False,
        "member_plaintext_count": 0,
        "server_llm": "BLOCK",
    }


def _block(code: str) -> dict[str, Any]:
    result = _base(code, "BLOCK")
    result["d8_capability_envelope_candidate"] = None
    return result


def evaluate_session(
    request: Mapping[str, Any],
    role_table: Mapping[str, Sequence[str]],
    *,
    current_epoch: int,
    active_developer_seats: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Derive one member-bound candidate session without activating a role."""

    schema = _load_object(SCHEMA_PATH)
    errors = list(Draft202012Validator(schema).iter_errors(dict(request)))
    if errors:
        return _block("BLOCK_MEMBER_BINDING_SCHEMA_INVALID")
    policy = _load_object(POLICY_PATH)
    member_ref = str(request["member_ref"])
    agent_ref = str(request["xiaoj_agent_ref"])
    delegation = request["delegation_envelope"]
    assert isinstance(delegation, Mapping)
    if request["principal_verified"] is not True:
        return _block("BLOCK_NON_MEMBER")
    if request["membership_state"] != "ACTIVE":
        return _block("BLOCK_INACTIVE_MEMBER")
    if member_ref not in role_table:
        return _block("BLOCK_NON_MEMBER")
    if delegation["issuer_member_ref"] != member_ref or delegation["subject_member_ref"] != member_ref:
        return _block("BLOCK_IDENTITY_MISMATCH")
    if delegation["bound_xiaoj_agent_ref"] != agent_ref:
        return _block("BLOCK_XIAOJ_NOT_BOUND")
    if delegation["revoked"] is True or request["revocation_state"] == "REVOKED":
        return _block("BLOCK_DELEGATION_REVOKED")
    if current_epoch >= delegation["expires_at_epoch"] or current_epoch - delegation["issued_at_epoch"] > request["ttl_seconds"]:
        return _block("BLOCK_DELEGATION_EXPIRED")
    if delegation["subdelegation"] is not False:
        return _block("BLOCK_SUBDELEGATION_FORBIDDEN")
    existing_roles = set(role_table[member_ref])
    asserted_roles = set(request["member_role_refs"])
    delegated_roles = set(delegation["allowed_role_refs"])
    effective_roles = sorted(existing_roles & asserted_roles & delegated_roles)
    if asserted_roles - existing_roles:
        return _block("BLOCK_SELF_DECLARED_ROLE")
    seat = policy["founder_developer_seat"]
    founder_seat_requested = seat["role_ref"] in effective_roles
    if founder_seat_requested:
        if member_ref != seat["principal_ref"]:
            return _block("BLOCK_FOUNDER_DEVELOPER_SEAT_PRINCIPAL_MISMATCH")
        occupied = [item for item in active_developer_seats if item.get("state") == "ACTIVE" and item.get("member_ref") != member_ref]
        if len(occupied) >= seat["max_seats"]:
            return _block("BLOCK_FOUNDER_DEVELOPER_SEAT_EXCLUSIVE")
    permissions = seat["permissions"] if founder_seat_requested else []
    envelope = {
        "member_ref": member_ref,
        "xiaoj_agent_ref": agent_ref,
        "effective_member_roles": effective_roles,
        "capability_refs": permissions,
        "organization_context_hash": canonical_sha256(request["organization_context"]),
        "device_or_channel_binding_hash": canonical_sha256(request["device_or_channel_binding"]),
        "delegation_ref": delegation["delegation_ref"],
        "ttl_seconds": request["ttl_seconds"],
        "nonce": request["nonce"],
        "revocation_state": request["revocation_state"],
        "final_decision": None,
        "requires_total_field_verify": True,
    }
    operation_record = {
        "principal": member_ref,
        "actor": agent_ref,
        "role": effective_roles,
        "command": request["command_ref"],
        "evidence": list(request["verification_refs"]),
    }
    result = _base("PASS_MEMBER_BOUND_CANDIDATE", "PASS")
    result.update({
        "permission_derivation": policy["permission_derivation"],
        "d8_capability_envelope_candidate": envelope,
        "operation_record": operation_record,
        "founder_developer_seat": {
            "requested": founder_seat_requested,
            "max_seats": seat["max_seats"],
            "exclusive": seat["exclusive"],
            "transferable": seat["transferable"],
            "subdelegation": seat["subdelegation"],
        },
    })
    result["result_sha256"] = canonical_sha256(result)
    return result


def receive_cloud_fragment(fragment: Mapping[str, Any], verified_session: Mapping[str, Any], *, founder_authorized: bool) -> dict[str, Any]:
    """Gate a deidentified cloud fragment through a verified member XiaoJ."""

    if founder_authorized is not True:
        return _block("BLOCK_CLOUD_CANDIDATE_NOT_AUTHORIZED")
    if verified_session.get("state") != "PASS_MEMBER_BOUND_CANDIDATE":
        return _block("BLOCK_CLOUD_DIRECT_CONNECTION")
    if fragment.get("fragment_type") not in {"CANDIDATE", "EVIDENCE_FRAGMENT"}:
        return _block("BLOCK_CLOUD_FRAGMENT_TYPE")
    if any(str(key).casefold() in FORBIDDEN_CLOUD_KEYS for key in fragment):
        return _block("BLOCK_CLOUD_MEMBER_REF_OR_PLAINTEXT")
    result = _base("PASS_RECEIVE_CANDIDATE_REQUIRED", "PASS")
    result.update({
        "fragment_sha256": canonical_sha256(fragment),
        "intake": "receive_candidate",
        "requires_total_field_verify": True,
        "cloud_direct_connection": False,
    })
    return result


__all__ = ["evaluate_session", "receive_cloud_fragment"]
