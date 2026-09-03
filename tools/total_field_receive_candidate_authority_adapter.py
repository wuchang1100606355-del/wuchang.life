from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Collection, Mapping

ACTIVE_POINTER_LOOKUP_REF = "runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json"
RESOLVER_CANDIDATE_REL = "tools/total_field_authority_resolver.py"
RESOLVER_CANDIDATE_SHA256 = (
    "d04043ead2d90d4d0b83f7ae60d7ca36c09332acb12d63e3240957583f7f652e"
)
CURRENT_OWNER_REL = "tools/total_field_dynamic_context.py"
CURRENT_OWNER_SHA256 = (
    "4ef2ad40b75e962582c55a32dff0a4e3a99faf13811c8653c8bcd53eface873d"
)
PASS_AUTHORITY_STATE = "PASS_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVED"
STATE_CELL_PILOT_SCOPE = "RUN_READ_ONLY_STATE_CELL_PILOT"
STATE_CELL_PILOT_ACTION = "RUN_READ_ONLY_STATE_CELL_INDEX_PROJECTION"
STATE_CELL_PILOT_NODE = "MSI"
STATE_CELL_PILOT_MAXIMUM_EFFECT = "IN_MEMORY_READ_ONLY_ONLY"
STATE_CELL_PILOT_FORBIDDEN_EFFECTS = frozenset(
    {
        "ACTIVE_POINTER_WRITE",
        "CANONICAL_POINTER_WRITE",
        "CLOUD_CALL",
        "DB_WRITE",
        "DEPLOY",
        "FILE_DELETE",
        "NETWORK_ROUTE_MUTATION",
        "OLD_VERSION_EXECUTION",
        "RESTART",
    }
)
ALLOWED_CANDIDATE_STATES = {
    "CANDIDATE_ONLY",
    "CANDIDATE_ONLY_WITH_FORBIDDEN_FIELDS_REMOVED",
}
FORBIDDEN_CANDIDATE_AUTHORITY_FIELDS = {
    "authority_ref",
    "authority_lookup_ref",
    "founder_person_packet_ref",
    "registered_device_ref",
    "founder_capability_assignment_ref",
    "access_profile_ref",
    "d8_decision_ref",
    "d8_decision_state",
    "formal_decision_authority",
    "formal_seal_authority",
}


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _safe_result(
    state: str,
    reason: str,
    *,
    candidate_packet: Mapping[str, Any] | None,
    dynamic_context_packet: Mapping[str, Any] | None,
    authority_resolution: Mapping[str, Any] | None = None,
    owner_state: str | None = None,
) -> dict[str, Any]:
    return {
        "state": state,
        "decision": state,
        "reason": reason,
        "decision_authority": "CANDIDATE_INTEGRATION_ONLY_NOT_ACTIVE",
        "authority_resolution_state": (
            authority_resolution.get("state")
            if isinstance(authority_resolution, Mapping)
            else None
        ),
        "authority_resolution_sha256": (
            canonical_sha256(authority_resolution)
            if isinstance(authority_resolution, Mapping)
            else None
        ),
        "owner_receive_candidate_state": owner_state,
        "candidate_authority": False,
        "execution_authorized": False,
        "formal_decision_authority": False,
        "formal_seal_authority": False,
        "candidate_packet_sha256": (
            canonical_sha256(candidate_packet)
            if isinstance(candidate_packet, Mapping)
            else None
        ),
        "dynamic_context_packet_sha256": (
            str(dynamic_context_packet.get("packet_sha256"))
            if isinstance(dynamic_context_packet, Mapping)
            else None
        ),
        "policy": {
            "candidate_only": True,
            "integration_candidate_only": True,
            "active_pointer_write": False,
            "owner_modified": False,
            "model_decision_is_authoritative": False,
            "db_write": False,
            "deploy": False,
            "restart": False,
            "formal_send": False,
        },
    }


def _valid_dynamic_context_evidence(packet: Any) -> bool:
    if not isinstance(packet, Mapping):
        return False
    if packet.get("state") != "TOTAL_FIELD_DYNAMIC_CONTEXT_READY":
        return False
    packet_sha256 = packet.get("packet_sha256")
    if not isinstance(packet_sha256, str) or len(packet_sha256) != 64:
        return False
    try:
        int(packet_sha256, 16)
    except ValueError:
        return False
    unsigned = dict(packet)
    unsigned.pop("packet_sha256", None)
    if canonical_sha256(unsigned) != packet_sha256:
        return False
    if not (packet.get("source_bindings") or packet.get("context_items")):
        return False
    policy = packet.get("policy")
    return isinstance(policy, Mapping) and policy.get("evidence_only") is True


def _breakpoint_disposition(candidate_packet: Mapping[str, Any]) -> str:
    values: list[Any] = [candidate_packet.get("breakpoint_disposition")]
    for key in ("breakpoint", "breakpoint_gate", "governance"):
        nested = candidate_packet.get(key)
        if isinstance(nested, Mapping):
            values.extend(
                nested.get(field)
                for field in ("decision", "disposition", "state")
            )
    normalized = {
        str(value).strip().upper()
        for value in values
        if value not in (None, "")
    }
    if any(
        value in {"DENY", "BLOCK", "BLOCK_BREAKPOINT_OR_POLICY"}
        for value in normalized
    ):
        return "DENY"
    if any(value == "HOLD" or value.startswith("HOLD_") for value in normalized):
        return "HOLD"
    return "ALLOW"


def _preflight(
    candidate_packet: Any,
    dynamic_context_packet: Any,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str | None, str | None]:
    candidate = (
        dict(candidate_packet)
        if isinstance(candidate_packet, Mapping)
        else None
    )
    context = (
        dict(dynamic_context_packet)
        if isinstance(dynamic_context_packet, Mapping)
        else None
    )

    if not _valid_dynamic_context_evidence(context):
        return (
            candidate,
            context,
            "HOLD_EVIDENCE_INCOMPLETE",
            "dynamic_context_packet is missing, unbound, or has no governed evidence",
        )
    if candidate is None:
        return (
            None,
            context,
            "HOLD_EVIDENCE_INCOMPLETE",
            "candidate_packet is missing",
        )

    forbidden = sorted(
        field
        for field in FORBIDDEN_CANDIDATE_AUTHORITY_FIELDS
        if candidate.get(field) not in (None, "", False, [], {})
    )
    if forbidden:
        return (
            candidate,
            context,
            "HOLD_EVIDENCE_INCOMPLETE",
            "candidate attempted to supply authority fields: " + ",".join(forbidden),
        )

    breakpoint = _breakpoint_disposition(candidate)
    if breakpoint == "DENY":
        return (
            candidate,
            context,
            "BLOCK_BREAKPOINT_OR_POLICY",
            "breakpoint or policy denied the candidate before authority resolution",
        )
    if breakpoint == "HOLD":
        return (
            candidate,
            context,
            "HOLD_BREAKPOINT_OR_POLICY",
            "breakpoint or policy held the candidate before authority resolution",
        )

    if candidate.get("state") not in ALLOWED_CANDIDATE_STATES:
        return (
            candidate,
            context,
            "HOLD_EVIDENCE_INCOMPLETE",
            "candidate state is unknown and cannot be normalized",
        )
    if candidate.get("execution_authorized") not in (None, False) or any(
        candidate.get(key) not in (None, "", False)
        for key in ("decision", "total_field_decision", "verdict")
    ):
        return (
            candidate,
            context,
            "HOLD_EVIDENCE_INCOMPLETE",
            "candidate supplied a decision or execution claim that cannot be promoted",
        )
    return candidate, context, None, None


def receive_candidate_authority_bound(
    candidate_packet: Mapping[str, Any],
    dynamic_context_packet: Mapping[str, Any] | None,
    *,
    repo_root: Path,
    nonce_ledger: Any,
    signature_verifier: Any,
    trusted_verifier_refs: Collection[str],
    authority_resolver: Callable[..., Mapping[str, Any]],
    owner_receive_candidate: Callable[
        [Mapping[str, Any], Mapping[str, Any] | None, Any],
        Mapping[str, Any],
    ],
) -> dict[str, Any]:
    """
    Candidate-only adapter. It preflights candidate evidence, resolves the fixed
    independently issued runtime authority, and only then invokes the existing
    receive_candidate owner. It cannot create or modify the active pointer.
    """
    candidate, context, preflight_state, preflight_reason = _preflight(
        candidate_packet,
        dynamic_context_packet,
    )
    if preflight_state is not None:
        return _safe_result(
            preflight_state,
            str(preflight_reason),
            candidate_packet=candidate,
            dynamic_context_packet=context,
        )

    try:
        authority_resolution = authority_resolver(
            ACTIVE_POINTER_LOOKUP_REF,
            repo_root=Path(repo_root),
            nonce_ledger=nonce_ledger,
            signature_verifier=signature_verifier,
            trusted_verifier_refs=trusted_verifier_refs,
        )
    except Exception as exc:
        return _safe_result(
            "HOLD_AUTHORITY_RESOLVER_FAILED",
            f"authority resolver raised {type(exc).__name__}",
            candidate_packet=candidate,
            dynamic_context_packet=context,
        )

    if not isinstance(authority_resolution, Mapping):
        return _safe_result(
            "BLOCK_AUTHORITY_RESOLVER_INVALID",
            "authority resolver returned a non-mapping result",
            candidate_packet=candidate,
            dynamic_context_packet=context,
        )

    authority_state = authority_resolution.get("state")
    if (
        authority_state != PASS_AUTHORITY_STATE
        or authority_resolution.get("authority_verified") is not True
    ):
        state = (
            str(authority_state)
            if isinstance(authority_state, str) and authority_state
            else "HOLD_AUTHORITY_INCOMPLETE"
        )
        return _safe_result(
            state,
            str(
                authority_resolution.get(
                    "reason",
                    "active authority did not resolve",
                )
            ),
            candidate_packet=candidate,
            dynamic_context_packet=context,
            authority_resolution=authority_resolution,
        )

    required_resolution_fields = (
        "authority_id",
        "authority_version",
        "founder_person_packet_ref",
        "registered_device_ref",
        "founder_capability_assignment_ref",
        "access_profile_ref",
        "authority_scope",
        "expires_at",
        "verifier_ref",
    )
    missing = [
        field
        for field in required_resolution_fields
        if authority_resolution.get(field) in (None, "", [], {})
    ]
    if missing:
        return _safe_result(
            "BLOCK_AUTHORITY_RESOLVER_INVALID",
            "verified authority result omitted fields: " + ",".join(sorted(missing)),
            candidate_packet=candidate,
            dynamic_context_packet=context,
            authority_resolution=authority_resolution,
        )

    raw_scope_constraints = authority_resolution.get("authority_scope_constraints")
    if not isinstance(raw_scope_constraints, Mapping):
        return _safe_result(
            "BLOCK_AUTHORITY_RESOLVER_INVALID",
            "verified authority result has invalid authority_scope_constraints",
            candidate_packet=candidate,
            dynamic_context_packet=context,
            authority_resolution=authority_resolution,
        )
    if (
        authority_resolution.get("authority_scope") == [STATE_CELL_PILOT_SCOPE]
        and not raw_scope_constraints
    ):
        return _safe_result(
            "BLOCK_AUTHORITY_RESOLVER_INVALID",
            "state-cell pilot authority omitted authority_scope_constraints",
            candidate_packet=candidate,
            dynamic_context_packet=context,
            authority_resolution=authority_resolution,
        )

    verified_authority_ref = {
        "schema_id": "W7TP_VERIFIED_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLUTION_V1",
        "authority_id": authority_resolution["authority_id"],
        "authority_version": authority_resolution["authority_version"],
        "founder_person_packet_ref": authority_resolution[
            "founder_person_packet_ref"
        ],
        "registered_device_ref": authority_resolution["registered_device_ref"],
        "founder_capability_assignment_ref": authority_resolution[
            "founder_capability_assignment_ref"
        ],
        "access_profile_ref": authority_resolution["access_profile_ref"],
        "authority_scope": list(authority_resolution["authority_scope"]),
        "authority_scope_constraints": dict(raw_scope_constraints),
        "expires_at": authority_resolution["expires_at"],
        "verifier_ref": authority_resolution["verifier_ref"],
        "authority_resolution_sha256": canonical_sha256(authority_resolution),
    }

    try:
        owner_result = owner_receive_candidate(
            candidate,
            context,
            verified_authority_ref,
        )
    except Exception as exc:
        return _safe_result(
            "HOLD_OWNER_RECEIVER_FAILED",
            f"owner receive_candidate raised {type(exc).__name__}",
            candidate_packet=candidate,
            dynamic_context_packet=context,
            authority_resolution=authority_resolution,
        )

    if not isinstance(owner_result, Mapping):
        return _safe_result(
            "BLOCK_OWNER_RECEIVER_INVALID",
            "owner receive_candidate returned a non-mapping result",
            candidate_packet=candidate,
            dynamic_context_packet=context,
            authority_resolution=authority_resolution,
        )

    owner_state = owner_result.get("state")
    if (
        owner_result.get("candidate_authority") is not False
        or owner_result.get("execution_authorized") is not False
    ):
        return _safe_result(
            "BLOCK_OWNER_BOUNDARY_VIOLATION",
            "owner result attempted to grant candidate or execution authority",
            candidate_packet=candidate,
            dynamic_context_packet=context,
            authority_resolution=authority_resolution,
            owner_state=str(owner_state) if owner_state is not None else None,
        )

    state = (
        str(owner_state)
        if isinstance(owner_state, str) and owner_state
        else "BLOCK_OWNER_RECEIVER_INVALID"
    )
    reason = str(
        owner_result.get(
            "reason",
            "owner receive_candidate completed without a reason",
        )
    )
    return _safe_result(
        state,
        reason,
        candidate_packet=candidate,
        dynamic_context_packet=context,
        authority_resolution=authority_resolution,
        owner_state=state,
    )


TOTAL_FIELD_FLOAT_AUTHORITY_DEPENDENCY = "NONE"
TOTAL_FIELD_OPERATION_PACKET_SCHEMA = "W7TP_TOTAL_FIELD_OPERATION_PACKET_V1"
MAX_OPERATION_PACKET_TTL_SECONDS = 3600
OPERATION_PROPOSAL_FIELDS = frozenset(
    {
        "schema_id",
        "operation_id",
        "intent_ref",
        "target_node",
        "object_id",
        "exact_coordinate",
        "current_state_hash",
        "input_hashes",
        "authorized_action",
        "authorized_steps",
        "maximum_effect",
        "forbidden_effects",
        "expected_effect",
        "rollback",
        "evidence_refs",
        "candidate_only",
        "operation_authority",
    }
)
STATE_CELL_PILOT_PROPOSAL_FIELDS = OPERATION_PROPOSAL_FIELDS | frozenset(
    {
        "proposal_sha256",
        "red_team_receipt_sha256",
        "target_field_sha256",
        "carrier_capability_registry_sha256",
        "cell_budget",
        "relation_traversal_budget",
        "observation_budget",
    }
)
STATE_CELL_PILOT_CONSTRAINT_FIELDS = frozenset(
    {
        "proposal_sha256",
        "red_team_receipt_sha256",
        "target_field_sha256",
        "carrier_capability_registry_sha256",
        "target_node",
        "object_id",
        "exact_coordinate",
        "authorized_action",
        "authorized_steps_sha256",
        "evidence_refs_sha256",
        "maximum_effect",
        "cell_budget",
        "relation_traversal_budget",
        "observation_budget",
        "forbidden_effects",
        "operation_nonce",
        "single_use_authorization_required",
        "replay_protected",
        "authority_signature_required",
        "db_write",
        "deploy",
        "restart",
        "network_route_mutation",
        "cloud_call",
        "file_delete",
        "canonical_pointer_write",
        "active_pointer_write",
        "old_version_target_import",
    }
)
STATE_CELL_PILOT_PACKET_FIELDS = frozenset(
    {
        "schema_id",
        "operation_id",
        "intent_ref",
        "target_node",
        "object_id",
        "exact_coordinate",
        "current_state_hash",
        "input_hashes",
        "proposal_sha256",
        "red_team_receipt_sha256",
        "target_field_sha256",
        "carrier_capability_registry_sha256",
        "authorized_action",
        "authorized_steps",
        "maximum_effect",
        "forbidden_effects",
        "expected_effect",
        "rollback",
        "cell_budget",
        "relation_traversal_budget",
        "observation_budget",
        "operation_nonce",
        "ttl_seconds",
        "issued_at",
        "expires_at",
        "single_use",
        "evidence_refs",
        "D8_AUTHORITY",
        "raw_llm_operation_authority",
        "float_authority_dependency",
        "packet_sha256",
    }
)


def _operation_time(value: Any, path: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"DATETIME_REQUIRED:{path}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"DATETIME_INVALID:{path}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"DATETIME_TIMEZONE_REQUIRED:{path}")
    return parsed.astimezone(timezone.utc)


def _operation_hash(value: Any, path: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(f"HASH_INVALID:{path}")
    return value


def _operation_budget(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"POSITIVE_INTEGER_REQUIRED:{path}")
    return value


def _state_cell_pilot_constraints(
    verified_authority_ref: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        verified_authority_ref.get("schema_id")
        != "W7TP_VERIFIED_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLUTION_V1"
    ):
        raise ValueError("VERIFIED_TOTAL_FIELD_AUTHORITY_REQUIRED")
    if verified_authority_ref.get("authority_scope") != [STATE_CELL_PILOT_SCOPE]:
        raise ValueError("TOTAL_FIELD_OPERATION_SCOPE_FORBIDDEN")
    raw = verified_authority_ref.get("authority_scope_constraints")
    if not isinstance(raw, Mapping) or set(raw) != STATE_CELL_PILOT_CONSTRAINT_FIELDS:
        raise ValueError("STATE_CELL_PILOT_SCOPE_CONSTRAINTS_INVALID")
    constraints = dict(raw)
    for field in (
        "proposal_sha256",
        "red_team_receipt_sha256",
        "target_field_sha256",
        "carrier_capability_registry_sha256",
        "authorized_steps_sha256",
        "evidence_refs_sha256",
    ):
        _operation_hash(constraints.get(field), f"authority_scope_constraints.{field}")
    for field in (
        "cell_budget",
        "relation_traversal_budget",
        "observation_budget",
    ):
        _operation_budget(constraints.get(field), f"authority_scope_constraints.{field}")
    if constraints.get("target_node") != STATE_CELL_PILOT_NODE:
        raise ValueError("STATE_CELL_PILOT_NODE_INVALID")
    if constraints.get("authorized_action") != STATE_CELL_PILOT_ACTION:
        raise ValueError("STATE_CELL_PILOT_ACTION_INVALID")
    if constraints.get("maximum_effect") != STATE_CELL_PILOT_MAXIMUM_EFFECT:
        raise ValueError("STATE_CELL_PILOT_MAXIMUM_EFFECT_INVALID")
    if set(constraints.get("forbidden_effects") or []) != STATE_CELL_PILOT_FORBIDDEN_EFFECTS:
        raise ValueError("STATE_CELL_PILOT_FORBIDDEN_EFFECTS_INVALID")
    if len(constraints["forbidden_effects"]) != len(STATE_CELL_PILOT_FORBIDDEN_EFFECTS):
        raise ValueError("STATE_CELL_PILOT_FORBIDDEN_EFFECTS_DUPLICATED")
    for field in (
        "single_use_authorization_required",
        "replay_protected",
        "authority_signature_required",
    ):
        if constraints.get(field) is not True:
            raise ValueError(f"STATE_CELL_PILOT_TRUE_REQUIRED:{field}")
    for field in (
        "db_write",
        "deploy",
        "restart",
        "network_route_mutation",
        "cloud_call",
        "file_delete",
        "canonical_pointer_write",
        "active_pointer_write",
        "old_version_target_import",
    ):
        if constraints.get(field) is not False:
            raise ValueError(f"STATE_CELL_PILOT_FALSE_REQUIRED:{field}")
    nonce = constraints.get("operation_nonce")
    if not isinstance(nonce, str) or not nonce.startswith("nonce_ref:sha256:"):
        raise ValueError("STATE_CELL_PILOT_OPERATION_NONCE_INVALID")
    _operation_hash(nonce.removeprefix("nonce_ref:sha256:"), "operation_nonce")
    for field in ("object_id", "exact_coordinate"):
        if not isinstance(constraints.get(field), str) or not constraints[field].strip():
            raise ValueError(f"STATE_CELL_PILOT_TEXT_REQUIRED:{field}")
    return constraints


def _require_state_cell_proposal_matches_scope(
    proposal: Mapping[str, Any],
    constraints: Mapping[str, Any],
) -> None:
    if set(proposal) != STATE_CELL_PILOT_PROPOSAL_FIELDS:
        raise ValueError("STATE_CELL_PILOT_PROPOSAL_SHAPE_MISMATCH")
    if (
        proposal.get("schema_id") != "W7TP_OPERATION_PROPOSAL_V1"
        or proposal.get("candidate_only") is not True
        or proposal.get("operation_authority") is not False
    ):
        raise ValueError("RAW_PROPOSAL_AUTHORITY_FORBIDDEN")
    for field in (
        "proposal_sha256",
        "red_team_receipt_sha256",
        "target_field_sha256",
        "carrier_capability_registry_sha256",
    ):
        value = _operation_hash(proposal.get(field), field)
        if value != constraints[field]:
            raise ValueError(f"STATE_CELL_PILOT_SCOPE_MISMATCH:{field}")
    for field in (
        "target_node",
        "object_id",
        "exact_coordinate",
        "authorized_action",
        "maximum_effect",
    ):
        if proposal.get(field) != constraints[field]:
            raise ValueError(f"STATE_CELL_PILOT_SCOPE_MISMATCH:{field}")
    for field in (
        "cell_budget",
        "relation_traversal_budget",
        "observation_budget",
    ):
        value = _operation_budget(proposal.get(field), field)
        if value != constraints[field]:
            raise ValueError(f"STATE_CELL_PILOT_SCOPE_MISMATCH:{field}")
    steps = proposal.get("authorized_steps")
    evidence_refs = proposal.get("evidence_refs")
    forbidden = proposal.get("forbidden_effects")
    if not isinstance(steps, list) or not steps:
        raise ValueError("STATE_CELL_PILOT_AUTHORIZED_STEPS_REQUIRED")
    if not isinstance(evidence_refs, list) or not evidence_refs:
        raise ValueError("STATE_CELL_PILOT_EVIDENCE_REFS_REQUIRED")
    if (
        not isinstance(forbidden, list)
        or len(forbidden) != len(set(forbidden))
        or set(forbidden) != STATE_CELL_PILOT_FORBIDDEN_EFFECTS
    ):
        raise ValueError("STATE_CELL_PILOT_FORBIDDEN_EFFECTS_INVALID")
    if canonical_sha256(steps) != constraints["authorized_steps_sha256"]:
        raise ValueError("STATE_CELL_PILOT_SCOPE_MISMATCH:authorized_steps")
    if canonical_sha256(evidence_refs) != constraints["evidence_refs_sha256"]:
        raise ValueError("STATE_CELL_PILOT_SCOPE_MISMATCH:evidence_refs")
    input_hashes = proposal.get("input_hashes")
    if not isinstance(input_hashes, Mapping) or set(input_hashes) != {
        "proposal",
        "red_team_receipt",
        "target_field",
    }:
        raise ValueError("STATE_CELL_PILOT_INPUT_HASHES_INVALID")
    expected_hashes = {
        "proposal": proposal["proposal_sha256"],
        "red_team_receipt": proposal["red_team_receipt_sha256"],
        "target_field": proposal["target_field_sha256"],
    }
    for name, expected in expected_hashes.items():
        if _operation_hash(input_hashes.get(name), f"input_hashes.{name}") != expected:
            raise ValueError(f"STATE_CELL_PILOT_SCOPE_MISMATCH:input_hashes.{name}")


def build_total_field_operation_packet(
    proposal: Mapping[str, Any],
    *,
    verified_authority_ref: Mapping[str, Any],
    issued_at: str,
    ttl_seconds: int,
) -> dict[str, Any]:
    """Build only the exact, scope-bound, read-only state-cell pilot packet."""
    constraints = _state_cell_pilot_constraints(verified_authority_ref)
    _require_state_cell_proposal_matches_scope(proposal, constraints)
    if not 1 <= ttl_seconds <= MAX_OPERATION_PACKET_TTL_SECONDS:
        raise ValueError("OPERATION_PACKET_TTL_INVALID")
    issued = _operation_time(issued_at, "issued_at")
    expires = issued + timedelta(seconds=ttl_seconds)
    authority_expires = _operation_time(
        verified_authority_ref.get("expires_at"),
        "verified_authority_ref.expires_at",
    )
    if expires > authority_expires:
        raise ValueError("OPERATION_PACKET_EXCEEDS_AUTHORITY_WINDOW")
    for field in ("current_state_hash",):
        _operation_hash(proposal.get(field), field)
    input_hashes = proposal.get("input_hashes")
    if not isinstance(input_hashes, Mapping) or not input_hashes:
        raise ValueError("OPERATION_INPUT_HASHES_REQUIRED")
    for name, digest in input_hashes.items():
        _operation_hash(digest, f"input_hashes.{name}")
    packet = {
        "schema_id": TOTAL_FIELD_OPERATION_PACKET_SCHEMA,
        "operation_id": proposal["operation_id"],
        "intent_ref": proposal["intent_ref"],
        "target_node": proposal["target_node"],
        "object_id": proposal["object_id"],
        "exact_coordinate": proposal["exact_coordinate"],
        "current_state_hash": proposal["current_state_hash"],
        "input_hashes": dict(input_hashes),
        "proposal_sha256": proposal["proposal_sha256"],
        "red_team_receipt_sha256": proposal["red_team_receipt_sha256"],
        "target_field_sha256": proposal["target_field_sha256"],
        "carrier_capability_registry_sha256": proposal[
            "carrier_capability_registry_sha256"
        ],
        "authorized_action": proposal["authorized_action"],
        "authorized_steps": list(proposal["authorized_steps"]),
        "maximum_effect": proposal["maximum_effect"],
        "forbidden_effects": list(proposal["forbidden_effects"]),
        "expected_effect": proposal["expected_effect"],
        "rollback": proposal["rollback"],
        "cell_budget": proposal["cell_budget"],
        "relation_traversal_budget": proposal["relation_traversal_budget"],
        "observation_budget": proposal["observation_budget"],
        "operation_nonce": constraints["operation_nonce"],
        "ttl_seconds": ttl_seconds,
        "issued_at": issued.isoformat().replace("+00:00", "Z"),
        "expires_at": expires.isoformat().replace("+00:00", "Z"),
        "single_use": True,
        "evidence_refs": list(proposal["evidence_refs"]),
        "D8_AUTHORITY": {
            "verified_authority_ref": dict(verified_authority_ref),
            "authority_resolution_sha256": _operation_hash(
                verified_authority_ref.get("authority_resolution_sha256"),
                "verified_authority_ref.authority_resolution_sha256",
            ),
            "authority_scope": [STATE_CELL_PILOT_SCOPE],
            "authority_scope_constraints_sha256": canonical_sha256(constraints),
            "issuer": "TOTAL_FIELD_ONLY",
        },
        "raw_llm_operation_authority": "FORBIDDEN",
        "float_authority_dependency": TOTAL_FIELD_FLOAT_AUTHORITY_DEPENDENCY,
    }
    packet["packet_sha256"] = canonical_sha256(packet)
    return packet


def validate_total_field_operation_packet(
    packet: Mapping[str, Any] | None,
    *,
    now: datetime,
    nonce_ledger: Any | None = None,
    trusted_authority_resolution: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate and consume one exact read-only pilot operation at executor entry."""
    if not isinstance(packet, Mapping):
        return {
            "state": "BLOCK_OPERATION_PACKET_REQUIRED",
            "executor_authorized": False,
        }
    if packet.get("schema_id") != TOTAL_FIELD_OPERATION_PACKET_SCHEMA:
        return {"state": "BLOCK_OPERATION_PACKET_SCHEMA", "executor_authorized": False}
    if set(packet) != STATE_CELL_PILOT_PACKET_FIELDS:
        return {"state": "BLOCK_OPERATION_PACKET_SHAPE", "executor_authorized": False}
    supplied_hash = packet.get("packet_sha256")
    unsigned = dict(packet)
    unsigned.pop("packet_sha256", None)
    if supplied_hash != canonical_sha256(unsigned):
        return {"state": "BLOCK_OPERATION_PACKET_HASH", "executor_authorized": False}
    try:
        issued = _operation_time(packet.get("issued_at"), "issued_at")
        expires = _operation_time(packet.get("expires_at"), "expires_at")
    except ValueError:
        return {"state": "BLOCK_OPERATION_PACKET_TIME", "executor_authorized": False}
    ttl = packet.get("ttl_seconds")
    if (
        isinstance(ttl, bool)
        or not isinstance(ttl, int)
        or not 1 <= ttl <= MAX_OPERATION_PACKET_TTL_SECONDS
        or expires - issued != timedelta(seconds=ttl)
        or now.astimezone(timezone.utc) < issued
        or now.astimezone(timezone.utc) >= expires
    ):
        return {"state": "BLOCK_OPERATION_PACKET_TTL", "executor_authorized": False}
    d8 = packet.get("D8_AUTHORITY")
    if (
        not isinstance(d8, Mapping)
        or d8.get("issuer") != "TOTAL_FIELD_ONLY"
        or not isinstance(d8.get("verified_authority_ref"), Mapping)
        or d8["verified_authority_ref"].get("schema_id")
        != "W7TP_VERIFIED_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLUTION_V1"
        or d8.get("authority_scope") != [STATE_CELL_PILOT_SCOPE]
        or packet.get("single_use") is not True
        or packet.get("raw_llm_operation_authority") != "FORBIDDEN"
        or packet.get("float_authority_dependency") != "NONE"
    ):
        return {"state": "BLOCK_OPERATION_PACKET_AUTHORITY", "executor_authorized": False}
    verified = d8["verified_authority_ref"]
    if (
        not isinstance(trusted_authority_resolution, Mapping)
        or trusted_authority_resolution.get("state") != PASS_AUTHORITY_STATE
        or trusted_authority_resolution.get("authority_verified") is not True
        or canonical_sha256(trusted_authority_resolution)
        != verified.get("authority_resolution_sha256")
        or trusted_authority_resolution.get("authority_scope")
        != verified.get("authority_scope")
        or trusted_authority_resolution.get("authority_scope_constraints")
        != verified.get("authority_scope_constraints")
        or trusted_authority_resolution.get("registered_device_ref")
        != verified.get("registered_device_ref")
        or trusted_authority_resolution.get("expires_at")
        != verified.get("expires_at")
    ):
        return {
            "state": "BLOCK_TRUSTED_AUTHORITY_RESOLUTION_REQUIRED",
            "executor_authorized": False,
        }
    try:
        constraints = _state_cell_pilot_constraints(verified)
        if d8.get("authority_scope_constraints_sha256") != canonical_sha256(constraints):
            raise ValueError("STATE_CELL_PILOT_CONSTRAINT_HASH_MISMATCH")
        proposal_view = {
            "schema_id": "W7TP_OPERATION_PROPOSAL_V1",
            "operation_id": packet.get("operation_id"),
            "intent_ref": packet.get("intent_ref"),
            "target_node": packet.get("target_node"),
            "object_id": packet.get("object_id"),
            "exact_coordinate": packet.get("exact_coordinate"),
            "current_state_hash": packet.get("current_state_hash"),
            "input_hashes": packet.get("input_hashes"),
            "proposal_sha256": packet.get("proposal_sha256"),
            "red_team_receipt_sha256": packet.get("red_team_receipt_sha256"),
            "target_field_sha256": packet.get("target_field_sha256"),
            "carrier_capability_registry_sha256": packet.get(
                "carrier_capability_registry_sha256"
            ),
            "authorized_action": packet.get("authorized_action"),
            "authorized_steps": packet.get("authorized_steps"),
            "maximum_effect": packet.get("maximum_effect"),
            "forbidden_effects": packet.get("forbidden_effects"),
            "expected_effect": packet.get("expected_effect"),
            "rollback": packet.get("rollback"),
            "evidence_refs": packet.get("evidence_refs"),
            "cell_budget": packet.get("cell_budget"),
            "relation_traversal_budget": packet.get("relation_traversal_budget"),
            "observation_budget": packet.get("observation_budget"),
            "candidate_only": True,
            "operation_authority": False,
        }
        _require_state_cell_proposal_matches_scope(proposal_view, constraints)
        if packet.get("operation_nonce") != constraints["operation_nonce"]:
            raise ValueError("STATE_CELL_PILOT_OPERATION_NONCE_MISMATCH")
        authority_expires = _operation_time(
            verified.get("expires_at"),
            "verified_authority_ref.expires_at",
        )
        if expires > authority_expires:
            raise ValueError("OPERATION_PACKET_EXCEEDS_AUTHORITY_WINDOW")
    except ValueError:
        return {"state": "BLOCK_OPERATION_PACKET_SCOPE", "executor_authorized": False}
    if (
        nonce_ledger is None
        or getattr(nonce_ledger, "persistent", False) is not True
        or not callable(getattr(nonce_ledger, "mark_used_or_replay", None))
    ):
        return {
            "state": "BLOCK_OPERATION_NONCE_LEDGER_REQUIRED",
            "executor_authorized": False,
        }
    if not nonce_ledger.mark_used_or_replay(
        str(packet["operation_nonce"]),
        str(supplied_hash),
        now.astimezone(timezone.utc).timestamp(),
        int(ttl),
    ):
        return {"state": "BLOCK_OPERATION_REPLAY", "executor_authorized": False}
    return {
        "state": "PASS_TOTAL_FIELD_OPERATION_PACKET",
        "executor_authorized": True,
        "operation_id": packet.get("operation_id"),
        "single_use_nonce_consumed": True,
        "packet_sha256": supplied_hash,
        "validation_class": "D4_EXECUTOR_PREFLIGHT_ONLY",
        "8dadi_reobservation_required": True,
        "final_authority": False,
    }


__all__ = [
    "ACTIVE_POINTER_LOOKUP_REF",
    "CURRENT_OWNER_REL",
    "CURRENT_OWNER_SHA256",
    "RESOLVER_CANDIDATE_REL",
    "RESOLVER_CANDIDATE_SHA256",
    "canonical_sha256",
    "build_total_field_operation_packet",
    "receive_candidate_authority_bound",
    "validate_total_field_operation_packet",
]
