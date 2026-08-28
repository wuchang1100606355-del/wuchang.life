"""Total Field planning facade; artifacts are handed to the existing mesh."""

from __future__ import annotations

from typing import Mapping, Sequence

from w7tp_gt_mesh.core import MeshHold

from .authority import DetachedSigner, build_task_envelope
from .placement import deterministic_place


def plan_task_envelope(
    *,
    snapshots: Sequence[Mapping[str, object]],
    resource_request: Mapping[str, object],
    task_id: str,
    intent: str,
    operation: str,
    parameters: Mapping[str, object],
    logical_time: int,
    issued_at_epoch: int,
    ttl_seconds: int,
    verifier_ref: str,
    signer: DetachedSigner,
    active_authority: Mapping[str, object],
    authority_profile: Mapping[str, object],
    evidence_refs: list[str] | None = None,
    nonce: str | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    """Place then seal; no send or new carrier is implemented here."""

    placement = deterministic_place(snapshots, resource_request)
    normalized_request = placement.get("resource_request")
    if not isinstance(normalized_request, Mapping):
        raise MeshHold("HOLD_RESOURCE_REQUEST_INVALID")
    normalized_request = dict(normalized_request)
    effective_parameters = dict(parameters)
    if operation == "container_run_canary":
        existing_limits = effective_parameters.get("resource_limits")
        if existing_limits is not None and existing_limits != normalized_request:
            raise MeshHold("HOLD_CONTAINER_RESOURCE_LIMIT_BINDING_MISMATCH")
        effective_parameters["resource_limits"] = normalized_request
    envelope = build_task_envelope(
        task_id=task_id,
        intent=intent,
        target_node_id=str(placement["selected_node_id"]),
        selected_snapshot_sha256=str(placement["selected_snapshot_sha256"]),
        operation=operation,
        parameters=effective_parameters,
        resource_request=normalized_request,
        node_manifest=placement["node_manifest"],
        node_resource_state=placement["node_resource_state"],
        execution_lease=placement["execution_lease"],
        logical_time=logical_time,
        issued_at_epoch=issued_at_epoch,
        ttl_seconds=ttl_seconds,
        verifier_ref=verifier_ref,
        signer=signer,
        active_authority=active_authority,
        authority_profile=authority_profile,
        evidence_refs=evidence_refs,
        nonce=nonce,
    )
    return placement, envelope
