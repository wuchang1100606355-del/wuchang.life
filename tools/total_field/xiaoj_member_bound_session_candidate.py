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
from typing import Any, Callable, Protocol

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/xiaoj_member_bound_developer_seat_candidate.schema.json"
POLICY_PATH = ROOT / "manifests/xiaoj_member_bound_developer_seat_candidate_v0_1/policy.json"
FORBIDDEN_CLOUD_KEYS = frozenset({"member_ref", "member_plaintext", "token", "secret", "credential", "password"})
P3_SCHEMA_VERSION = "w7tp.member-session-dual-receipt-9107.v1"
HASH_REF_PATTERN = (
    r"^[a-z][a-z0-9_.-]*_ref:sha256:[0-9a-f]{64}$"
)
P3_AUTHORITY = {
    "member_consent_authority": "member",
    "safety_and_landing_authority": "total_field_verifier",
    "process_authority": "odoo",
    "candidate_authority": "none",
}


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
        "capability_conditions": policy.get("capability_conditions", {}),
        "execution_authority": policy.get("execution_authority", {}),
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


class DurableNonceConsumer(Protocol):
    """Atomic nonce interface supplied by a durable runtime ledger."""

    def consume_once(
        self,
        *,
        nonce_ref: str,
        binding_sha256: str,
        expires_at_epoch: int,
    ) -> Mapping[str, Any]:
        """Return hash-bound durable consumption evidence, never a boolean."""


def _p3_result(state: str, reason_code: str) -> dict[str, Any]:
    return {
        "state": state,
        "reason_code": reason_code,
        "candidate_only": True,
        "generic_gateway_ready": False,
        "runtime_released": False,
        "action_executed": False,
        **P3_AUTHORITY,
    }


def _p3_hold(reason_code: str, *, state: str = "HOLD") -> dict[str, Any]:
    return _p3_result(state, reason_code)


def _member_action_validator() -> Draft202012Validator:
    schema = _load_object(SCHEMA_PATH)
    return Draft202012Validator(
        {
            "$schema": schema["$schema"],
            "$ref": "#/$defs/memberActionRequest",
            "$defs": schema["$defs"],
        }
    )


def _default_p1_verifier(candidate: Mapping[str, Any]) -> Mapping[str, Any]:
    from .w7tp_intent_field_suite.member_sovereign_identity import (
        verify_member_sovereign_identity_candidate,
    )

    return verify_member_sovereign_identity_candidate(candidate)


def _sorted_refs(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    normalized = sorted(set(value))
    return normalized if normalized == value else None


def _sealed_ref(
    value: Mapping[str, Any],
    *,
    ref_field: str,
    prefix: str,
    excluded_fields: Sequence[str] = (),
) -> bool:
    material = {
        key: nested
        for key, nested in value.items()
        if key != ref_field and key not in excluded_fields
    }
    return value.get(ref_field) == f"{prefix}:sha256:{canonical_sha256(material)}"


def _p1_join_material(candidate: Mapping[str, Any]) -> dict[str, Any] | None:
    try:
        root_chain = candidate["root_chain_evidence"]["payload"]
        derived = candidate["derived_packets_evidence"]["payload"]
        dual_receipt = candidate["dual_receipt_evidence"]["payload"]
        roots = root_chain["roots"]
        current_root = roots[-1]
        return {
            "root": current_root,
            "session": derived["session"]["payload"],
            "scene": derived["scene"]["payload"],
            "role_seat": derived["role_seat"]["payload"],
            "action": dual_receipt["action_binding"],
        }
    except (KeyError, IndexError, TypeError):
        return None


def _p3_chain_reason(request: Mapping[str, Any]) -> str | None:
    session = request["session"]
    scene = request["scene"]
    action = request["action"]
    member_receipt = request["member_consent_receipt"]
    total_field_receipt = request["total_field_receipt"]
    root_fields = (
        "identity_root_ref",
        "root_generation",
        "revocation_epoch",
    )
    if any(session[field] != request[field] for field in root_fields):
        return "HOLD_CROSS_ROOT_SESSION"
    if any(scene[field] != request[field] for field in root_fields):
        return "HOLD_CROSS_ROOT_SCENE"
    if scene["session_ref"] != session["session_ref"]:
        return "HOLD_CROSS_SESSION_SCENE"
    scopes = _sorted_refs(action["scope_refs"])
    if (
        scopes is None
        or _sorted_refs(session["scope_refs"]) != scopes
        or _sorted_refs(scene["scope_refs"]) != scopes
        or _sorted_refs(member_receipt["scope_refs"]) != scopes
        or _sorted_refs(total_field_receipt["scope_refs"]) != scopes
    ):
        return "HOLD_SCOPE_EXPANSION"
    if any(
        value != action["effect_class"]
        for value in (
            session["effect_class"],
            scene["effect_class"],
            member_receipt["effect_class"],
            total_field_receipt["effect_class"],
        )
    ):
        return "HOLD_EFFECT_CLASS_EXPANSION"
    receipt_basis = (
        "action_hash",
        "root_generation",
        "session_ref",
        "scene_ref",
        "effect_class",
    )
    expected = {
        "action_hash": action["action_hash"],
        "root_generation": request["root_generation"],
        "session_ref": session["session_ref"],
        "scene_ref": scene["scene_ref"],
        "effect_class": action["effect_class"],
    }
    for receipt in (member_receipt, total_field_receipt):
        if any(receipt[field] != expected[field] for field in receipt_basis):
            return "HOLD_DUAL_RECEIPT_BASIS_MISMATCH"
    if member_receipt["receipt_state"] != "CONSENT":
        return "HOLD_MEMBER_CONSENT_RECEIPT_REQUIRED"
    if total_field_receipt["receipt_state"] != "PASS":
        return "HOLD_TOTAL_FIELD_RECEIPT_REQUIRED"
    if not _sealed_ref(
        session,
        ref_field="session_ref",
        prefix="session_ref",
        excluded_fields=("nonce_binding_sha256",),
    ):
        return "HOLD_SESSION_HASH_BINDING_MISMATCH"
    if not _sealed_ref(scene, ref_field="scene_ref", prefix="scene_ref"):
        return "HOLD_SCENE_HASH_BINDING_MISMATCH"
    if not _sealed_ref(
        member_receipt,
        ref_field="receipt_ref",
        prefix="member_consent_receipt_ref",
    ):
        return "HOLD_MEMBER_RECEIPT_HASH_BINDING_MISMATCH"
    if not _sealed_ref(
        total_field_receipt,
        ref_field="receipt_ref",
        prefix="total_field_receipt_ref",
    ):
        return "HOLD_TOTAL_FIELD_RECEIPT_HASH_BINDING_MISMATCH"
    return None


def _p1_binding_reason(
    request: Mapping[str, Any],
    p1_material: Mapping[str, Any],
) -> str | None:
    root = p1_material["root"]
    session = p1_material["session"]
    scene = p1_material["scene"]
    action = p1_material["action"]
    role_seat = p1_material["role_seat"]
    for field in (
        "identity_root_ref",
        "root_packet_ref",
        "root_generation",
        "revocation_epoch",
    ):
        if root.get(field) != request.get(field):
            return "HOLD_P1_ROOT_BINDING_MISMATCH"
    if session.get("session_ref") != request["session"]["session_ref"]:
        return "HOLD_P1_SESSION_BINDING_MISMATCH"
    if scene.get("scene_ref") != request["scene"]["scene_ref"]:
        return "HOLD_P1_SCENE_BINDING_MISMATCH"
    for field in ("action_hash", "purpose_ref", "scope_refs", "effect_class"):
        if action.get(field) != request["action"][field]:
            return "HOLD_P1_ACTION_BINDING_MISMATCH"
    leases = request["session"]["role_seat_snapshot"]["seat_leases"]
    if leases:
        p1_role_ref = role_seat.get("role_ref")
        p1_seat_ref = role_seat.get("seat_ref")
        if not any(
            lease["role_ref"] == p1_role_ref and lease["seat_ref"] == p1_seat_ref
            for lease in leases
        ):
            return "HOLD_P1_ROLE_SEAT_BINDING_MISMATCH"
    return None


def _role_seat_reason(
    request: Mapping[str, Any],
    *,
    current_epoch: int,
    active_seat_leases: Sequence[Mapping[str, Any]],
) -> str | None:
    snapshot = request["session"]["role_seat_snapshot"]
    snapshot_material = {
        "role_refs": snapshot["role_refs"],
        "seat_leases": snapshot["seat_leases"],
    }
    snapshot_sha256 = canonical_sha256(snapshot_material)
    if (
        snapshot["snapshot_sha256"] != snapshot_sha256
        or snapshot["snapshot_ref"]
        != f"role_seat_snapshot_ref:sha256:{snapshot_sha256}"
    ):
        return "HOLD_ROLE_SEAT_SNAPSHOT_HASH_MISMATCH"
    if _sorted_refs(snapshot["role_refs"]) is None:
        return "HOLD_ROLE_SEAT_SNAPSHOT_NOT_CANONICAL"
    leases = [*snapshot["seat_leases"], *active_seat_leases]
    seen_seats: dict[str, str] = {}
    founder_leases: set[str] = set()
    for lease in leases:
        if not isinstance(lease, Mapping):
            return "HOLD_ROLE_SEAT_SNAPSHOT_NOT_EVIDENCED"
        if (
            lease.get("identity_root_ref") != request["identity_root_ref"]
            or lease.get("root_generation") != request["root_generation"]
            or lease.get("revocation_epoch") != request["revocation_epoch"]
        ):
            return "HOLD_ROLE_SEAT_CROSS_ROOT"
        if not (
            isinstance(lease.get("issued_at_epoch"), int)
            and isinstance(lease.get("expires_at_epoch"), int)
            and lease["issued_at_epoch"] <= current_epoch < lease["expires_at_epoch"]
        ):
            return "HOLD_ROLE_SEAT_LEASE_EXPIRED"
        seat_ref = str(lease.get("seat_ref"))
        lease_ref = str(lease.get("lease_ref"))
        if seat_ref in seen_seats and seen_seats[seat_ref] != lease_ref:
            return "HOLD_DOUBLE_ACTIVE_SEAT"
        seen_seats[seat_ref] = lease_ref
        if lease.get("seat_class") == "FOUNDER_DEVELOPER":
            founder_leases.add(lease_ref)
    if len(founder_leases) > 1:
        return "HOLD_DOUBLE_ACTIVE_SEAT"
    return None


def evaluate_member_action_session(
    request: Mapping[str, Any],
    *,
    current_epoch: int,
    nonce_consumer: DurableNonceConsumer | None,
    p1_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    active_seat_leases: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Gate root -> session -> scene -> dual receipt before generic ingress."""

    if not isinstance(request, Mapping):
        return _p3_hold("HOLD_MEMBER_ACTION_REQUEST_REQUIRED")
    if list(_member_action_validator().iter_errors(dict(request))):
        return _p3_hold("HOLD_MEMBER_ACTION_SCHEMA_INVALID")
    verifier = p1_verifier or _default_p1_verifier
    try:
        p1_result = verifier(request["p1_identity_candidate"])
    except Exception:
        return _p3_hold("HOLD_P1_VERIFIER_UNAVAILABLE")
    if not isinstance(p1_result, Mapping) or p1_result.get("state") != "PASS":
        state = "BLOCK" if p1_result.get("state") == "BLOCK" else "HOLD"
        reason = str(p1_result.get("reason_code") or "HOLD_P1_VERIFIER_REQUIRED")
        return _p3_hold(reason, state=state)
    p1_material = _p1_join_material(request["p1_identity_candidate"])
    if p1_material is None:
        return _p3_hold("HOLD_P1_VERIFIED_MATERIAL_REQUIRED")
    p1_reason = _p1_binding_reason(request, p1_material)
    if p1_reason is not None:
        return _p3_hold(p1_reason)
    chain_reason = _p3_chain_reason(request)
    if chain_reason is not None:
        return _p3_hold(chain_reason)
    session = request["session"]
    if not (
        session["issued_at_epoch"] <= current_epoch < session["expires_at_epoch"]
        and session["expires_at_epoch"] - session["issued_at_epoch"]
        <= session["ttl_seconds"]
    ):
        return _p3_hold("HOLD_SESSION_TTL_INVALID")
    if session["revocation_epoch"] != request["revocation_epoch"]:
        return _p3_hold("HOLD_STALE_REVOCATION_EPOCH")
    seat_reason = _role_seat_reason(
        request,
        current_epoch=current_epoch,
        active_seat_leases=active_seat_leases,
    )
    if seat_reason is not None:
        return _p3_hold(seat_reason)
    nonce_material = {
        "nonce_ref": session["nonce_ref"],
        "identity_root_ref": request["identity_root_ref"],
        "root_generation": request["root_generation"],
        "revocation_epoch": request["revocation_epoch"],
        "session_ref": session["session_ref"],
        "scene_ref": request["scene"]["scene_ref"],
        "action_hash": request["action"]["action_hash"],
        "scope_refs": request["action"]["scope_refs"],
        "effect_class": request["action"]["effect_class"],
        "device_ref": session["device_ref"],
        "channel_ref": session["channel_ref"],
        "expires_at_epoch": session["expires_at_epoch"],
    }
    binding_sha256 = canonical_sha256(nonce_material)
    if session["nonce_binding_sha256"] != binding_sha256:
        return _p3_hold("HOLD_NONCE_BINDING_MISMATCH")
    if nonce_consumer is None or not callable(
        getattr(nonce_consumer, "consume_once", None)
    ):
        return _p3_hold("HOLD_DURABLE_NONCE_INTERFACE_REQUIRED")
    try:
        nonce_evidence = nonce_consumer.consume_once(
            nonce_ref=session["nonce_ref"],
            binding_sha256=binding_sha256,
            expires_at_epoch=session["expires_at_epoch"],
        )
    except Exception:
        return _p3_hold("HOLD_DURABLE_NONCE_CONSUME_FAILED")
    if not isinstance(nonce_evidence, Mapping):
        return _p3_hold("HOLD_DURABLE_NONCE_EVIDENCE_REQUIRED")
    if nonce_evidence.get("state") == "REPLAY":
        return _p3_hold("HOLD_NONCE_REPLAY")
    evidence_material = {
        "state": "CONSUMED",
        "nonce_ref": session["nonce_ref"],
        "binding_sha256": binding_sha256,
        "expires_at_epoch": session["expires_at_epoch"],
        "durable": True,
        "atomic": True,
    }
    evidence_sha256 = canonical_sha256(evidence_material)
    if (
        nonce_evidence.get("state") != "CONSUMED"
        or nonce_evidence.get("nonce_ref") != session["nonce_ref"]
        or nonce_evidence.get("binding_sha256") != binding_sha256
        or nonce_evidence.get("expires_at_epoch") != session["expires_at_epoch"]
        or nonce_evidence.get("durable") is not True
        or nonce_evidence.get("atomic") is not True
        or nonce_evidence.get("evidence_ref")
        != f"nonce_consumption_evidence_ref:sha256:{evidence_sha256}"
    ):
        return _p3_hold("HOLD_DURABLE_NONCE_EVIDENCE_INVALID")
    gate_material = {
        "schema_version": P3_SCHEMA_VERSION,
        "identity_root_ref": request["identity_root_ref"],
        "root_generation": request["root_generation"],
        "revocation_epoch": request["revocation_epoch"],
        "session_ref": session["session_ref"],
        "scene_ref": request["scene"]["scene_ref"],
        "action_hash": request["action"]["action_hash"],
        "scope_refs": request["action"]["scope_refs"],
        "effect_class": request["action"]["effect_class"],
        "member_consent_receipt_ref": request["member_consent_receipt"][
            "receipt_ref"
        ],
        "total_field_receipt_ref": request["total_field_receipt"]["receipt_ref"],
        "nonce_consumption_evidence_ref": nonce_evidence["evidence_ref"],
        **P3_AUTHORITY,
    }
    result = _p3_result(
        "PASS",
        "PASS_P3_SESSION_DUAL_RECEIPT_9107_GATE_CANDIDATE",
    )
    result.update(
        {
            "generic_gateway_ready": True,
            "gate_ref": (
                "member_action_gate_ref:sha256:"
                + canonical_sha256(gate_material)
            ),
            "gate_material": gate_material,
            "p1_verifier_state": "PASS",
        }
    )
    return result


__all__ = [
    "DurableNonceConsumer",
    "evaluate_member_action_session",
    "evaluate_session",
    "receive_cloud_fragment",
]
