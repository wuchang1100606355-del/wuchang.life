from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Collection, Mapping

ACTIVE_POINTER_LOOKUP_REF = "runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json"
RESOLVER_CANDIDATE_REL = "tools/total_field_authority_resolver.py"
RESOLVER_CANDIDATE_SHA256 = (
    "529e23cd07f3399eb0abcb7835533128486dd246bf96fde521847d136e4134cd"
)
CURRENT_OWNER_REL = "tools/total_field_dynamic_context.py"
CURRENT_OWNER_SHA256 = (
    "0f264e36201f89d486276f4d296bc3f45665c54ce96f5db0755d40ef36268ea0"
)
PASS_AUTHORITY_STATE = "PASS_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLVED"
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


def build_total_field_operation_packet(
    proposal: Mapping[str, Any],
    *,
    verified_authority_ref: Mapping[str, Any],
    issued_at: str,
    ttl_seconds: int,
) -> dict[str, Any]:
    """Convert a proposal only when Total Field authority is already verified."""
    if set(proposal) != OPERATION_PROPOSAL_FIELDS:
        raise ValueError("OPERATION_PROPOSAL_SHAPE_MISMATCH")
    if (
        proposal.get("schema_id") != "W7TP_OPERATION_PROPOSAL_V1"
        or proposal.get("candidate_only") is not True
        or proposal.get("operation_authority") is not False
    ):
        raise ValueError("RAW_PROPOSAL_AUTHORITY_FORBIDDEN")
    if (
        verified_authority_ref.get("schema_id")
        != "W7TP_VERIFIED_ACTIVE_TOTAL_FIELD_AUTHORITY_RESOLUTION_V1"
    ):
        raise ValueError("VERIFIED_TOTAL_FIELD_AUTHORITY_REQUIRED")
    if not 1 <= ttl_seconds <= MAX_OPERATION_PACKET_TTL_SECONDS:
        raise ValueError("OPERATION_PACKET_TTL_INVALID")
    issued = _operation_time(issued_at, "issued_at")
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
        "authorized_action": proposal["authorized_action"],
        "authorized_steps": list(proposal["authorized_steps"]),
        "maximum_effect": proposal["maximum_effect"],
        "forbidden_effects": list(proposal["forbidden_effects"]),
        "expected_effect": proposal["expected_effect"],
        "rollback": proposal["rollback"],
        "ttl_seconds": ttl_seconds,
        "issued_at": issued.isoformat().replace("+00:00", "Z"),
        "expires_at": (issued + timedelta(seconds=ttl_seconds))
        .isoformat()
        .replace("+00:00", "Z"),
        "single_use": True,
        "evidence_refs": list(proposal["evidence_refs"]),
        "D8_AUTHORITY": {
            "verified_authority_ref": dict(verified_authority_ref),
            "authority_resolution_sha256": _operation_hash(
                verified_authority_ref.get("authority_resolution_sha256"),
                "verified_authority_ref.authority_resolution_sha256",
            ),
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
) -> dict[str, Any]:
    """Fail closed for absent, forged, expired, replay-unbound, or raw commands."""
    if not isinstance(packet, Mapping):
        return {
            "state": "BLOCK_OPERATION_PACKET_REQUIRED",
            "executor_authorized": False,
        }
    if packet.get("schema_id") != TOTAL_FIELD_OPERATION_PACKET_SCHEMA:
        return {"state": "BLOCK_OPERATION_PACKET_SCHEMA", "executor_authorized": False}
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
        or packet.get("single_use") is not True
        or packet.get("raw_llm_operation_authority") != "FORBIDDEN"
        or packet.get("float_authority_dependency") != "NONE"
    ):
        return {"state": "BLOCK_OPERATION_PACKET_AUTHORITY", "executor_authorized": False}
    return {
        "state": "PASS_TOTAL_FIELD_OPERATION_PACKET",
        "executor_authorized": True,
        "operation_id": packet.get("operation_id"),
        "single_use_requires_runtime_nonce_consumer": True,
        "packet_sha256": supplied_hash,
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
