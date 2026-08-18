from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Collection, Mapping

ACTIVE_POINTER_LOOKUP_REF = "runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json"
RESOLVER_CANDIDATE_REL = "tools/total_field_authority_resolver.py"
RESOLVER_CANDIDATE_SHA256 = (
    "3d4e1f1f13a40cb131a57a5eb3760ce8a39b3b83a3ec7ad446779fa416032767"
)
CURRENT_OWNER_REL = "tools/total_field_dynamic_context.py"
CURRENT_OWNER_SHA256 = (
    "c7ed3a76348394f6355557743dd09856399768b5a63d0354b07e3d1093393cf9"
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


__all__ = [
    "ACTIVE_POINTER_LOOKUP_REF",
    "CURRENT_OWNER_REL",
    "CURRENT_OWNER_SHA256",
    "RESOLVER_CANDIDATE_REL",
    "RESOLVER_CANDIDATE_SHA256",
    "canonical_sha256",
    "receive_candidate_authority_bound",
]
