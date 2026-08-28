"""Node capability agent with RESERVE/EXECUTE/VERIFY append-only receipts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Mapping, Protocol

from w7tp_gt_mesh.core import MeshHold, require_core
from w7tp_gt_mesh.journal import MeshStorage

from .authority import (
    CONTROL_AUTHORITY_NODE_ID,
    MANAGE_EXISTING_CONTAINER_SCOPE,
    TASK_NAMESPACE,
    TOTAL_FIELD_AUTHORITY,
    DetachedVerifier,
    verify_task_envelope,
)
from .placement import ResourceRequest, capability_from_snapshot
from .human_view import render_receipt_zh_tw


_EXISTING_CONTAINER_OPERATIONS = {
    "container_inspect_existing",
    "container_start_existing",
    "container_stop_existing",
    "container_remove_existing",
}


class Dispatcher(Protocol):
    def validate(self, operation: str, parameters: Mapping[str, object]) -> None: ...
    def execute(self, operation: str, parameters: Mapping[str, object]) -> dict[str, object]: ...
    def verify(self, operation: str, parameters: Mapping[str, object]) -> dict[str, object]: ...


def _utc(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, tz=UTC).isoformat().replace("+00:00", "Z")


class TotalFieldNodeAgent:
    """Receives only reconstructed task artifacts from the existing mesh."""

    def __init__(
        self,
        *,
        storage: MeshStorage,
        node_id: str,
        signature_verifier: DetachedVerifier,
        dispatcher: Dispatcher,
    ) -> None:
        if not node_id:
            raise MeshHold("HOLD_CONTROL_NODE_ID_REQUIRED")
        self.storage = storage
        self.node_id = node_id
        self.signature_verifier = signature_verifier
        self.dispatcher = dispatcher

    def _append_receipt(
        self,
        *,
        category: str,
        key: str,
        phase: str,
        state: str,
        task_ref: str,
        task_id: str,
        logical_time: int,
        recorded_at: str,
        detail: Mapping[str, object],
    ) -> dict[str, object]:
        core = require_core()
        receipt: dict[str, object] = {
            "schema_id": "W7TP_TOTAL_FIELD_CONTROL_RECEIPT_CANDIDATE_V1",
            "candidate_state": "CANDIDATE_NOT_CANONICAL_NOT_PROMOTED",
            "authority_ref": TOTAL_FIELD_AUTHORITY,
            "primary_decision_engine": "8D_ADI",
            "node_id": self.node_id,
            "task_id": task_id,
            "task_ref": task_ref,
            "logical_time": logical_time,
            "phase": phase,
            "state": state,
            "recorded_at": recorded_at,
            "detail": dict(detail),
        }
        receipt["human_summary_zh_tw"] = render_receipt_zh_tw(
            phase=phase,
            state=state,
            node_id=self.node_id,
            task_id=task_id,
            detail=detail,
        )
        receipt["receipt_sha256"] = core.sha256_hex(core.canonical_json_bytes(receipt))
        self.storage.journal.append(category, key, receipt)
        return receipt

    def _append_incremental_adi_state(
        self,
        *,
        task_ref: str,
        task_id: str,
        logical_time: int,
        recorded_at: str,
        verification_receipt: Mapping[str, object],
    ) -> dict[str, object]:
        core = require_core()
        prior = list(self.storage.journal.records("total_field_control_adi_state"))
        prior_ref = None
        prior_time = 0
        if prior:
            latest = max(prior, key=lambda item: int(item.get("logical_time", 0)))
            prior_time = int(latest.get("logical_time", 0))
            prior_hash = latest.get("state_sha256")
            if isinstance(prior_hash, str):
                prior_ref = f"sha256:{prior_hash}"
        if logical_time <= prior_time:
            raise MeshHold("HOLD_CONTROL_ADI_LOGICAL_TIME_NOT_MONOTONIC")
        state: dict[str, object] = {
            "schema_id": "W7TP_TOTAL_FIELD_CONTROL_INCREMENTAL_ADI_STATE_CANDIDATE_V1",
            "candidate_state": "CANDIDATE_NOT_CANONICAL_NOT_PROMOTED",
            "authority_ref": TOTAL_FIELD_AUTHORITY,
            "primary_decision_engine": "8D_ADI",
            "namespace": TASK_NAMESPACE,
            "node_id": self.node_id,
            "task_id": task_id,
            "task_ref": task_ref,
            "logical_time": logical_time,
            "prior_state_ref": prior_ref,
            "transition": "ISSUED_TO_ACKNOWLEDGED_TO_RUNNING_TO_RESULT_CANDIDATE_TO_ACCEPTED",
            "verification_receipt_sha256": verification_receipt.get("receipt_sha256"),
            "recorded_at": recorded_at,
        }
        state["state_sha256"] = core.sha256_hex(core.canonical_json_bytes(state))
        self.storage.journal.append(
            "total_field_control_adi_state",
            f"{logical_time:020d}-{task_id}",
            state,
        )
        return state

    def process(
        self,
        envelope: Mapping[str, object],
        *,
        current_snapshot: Mapping[str, object],
        active_authority: Mapping[str, object],
        authority_profile: Mapping[str, object],
        now_epoch: int,
    ) -> dict[str, object]:
        verified = verify_task_envelope(
            envelope,
            signature_verifier=self.signature_verifier,
            active_authority=active_authority,
            authority_profile=authority_profile,
            now_epoch=now_epoch,
        )
        dimensions = verified["dimensions"]
        if not isinstance(dimensions, Mapping):
            raise MeshHold("HOLD_TASK_DIMENSIONS_INVALID")
        d2 = dimensions.get("D2_STATE")
        d3 = dimensions.get("D3_COORDINATE")
        d5 = dimensions.get("D5_EXECUTION")
        d8 = dimensions.get("D8_ENVELOPE_VERIFICATION")
        if (
            not isinstance(d2, Mapping)
            or not isinstance(d3, Mapping)
            or not isinstance(d5, Mapping)
            or not isinstance(d8, Mapping)
        ):
            raise MeshHold("HOLD_TASK_DIMENSION_CONTENT_INVALID")
        if d3.get("target_node_id") != self.node_id:
            raise MeshHold("HOLD_CONTROL_TASK_WRONG_NODE")
        if d3.get("control_authority_node_id") != CONTROL_AUTHORITY_NODE_ID:
            raise MeshHold("HOLD_TOTAL_FIELD_CONTROL_AUTHORITY_NODE_INVALID")
        capability = capability_from_snapshot(current_snapshot)
        if capability.node_id != self.node_id or d3.get("selected_snapshot_sha256") != capability.snapshot_sha256:
            raise MeshHold("HOLD_CONTROL_PLACEMENT_SNAPSHOT_DRIFT")
        request_raw = d2.get("resource_request")
        execution_lease = d2.get("execution_lease")
        if not isinstance(request_raw, Mapping) or not isinstance(execution_lease, Mapping):
            raise MeshHold("HOLD_RESOURCE_REQUEST_INVALID")
        if (
            execution_lease.get("state") != "ISSUED"
            or execution_lease.get("node_id") != self.node_id
            or execution_lease.get("issuer_node_id") != CONTROL_AUTHORITY_NODE_ID
            or execution_lease.get("resource_request") != dict(request_raw)
        ):
            raise MeshHold("HOLD_EXECUTION_LEASE_BINDING_INVALID")
        request = ResourceRequest.from_mapping(request_raw)
        if not capability.satisfies(request):
            raise MeshHold("HOLD_CONTROL_RESOURCES_INSUFFICIENT")
        operation = d5.get("operation")
        parameters = d5.get("parameters")
        if not isinstance(operation, str) or not isinstance(parameters, Mapping):
            raise MeshHold("HOLD_CONTROL_OPERATION_INVALID")
        if operation == "container_run_canary":
            limits = parameters.get("resource_limits")
            if not isinstance(limits, Mapping) or dict(limits) != request.as_dict():
                raise MeshHold("HOLD_CONTAINER_RESOURCE_LIMIT_BINDING_MISMATCH")
        if operation in _EXISTING_CONTAINER_OPERATIONS:
            scopes = d8.get("required_scopes")
            if not isinstance(scopes, list) or MANAGE_EXISTING_CONTAINER_SCOPE not in scopes:
                raise MeshHold("HOLD_MANAGE_EXISTING_CONTAINER_NOT_AUTHORIZED")
        self.dispatcher.validate(operation, parameters)
        target_identity = (
            parameters.get("name")
            or parameters.get("container_id")
            or parameters.get("unit")
            or "尚未綁定"
        )
        if not isinstance(target_identity, str):
            raise MeshHold("HOLD_CONTROL_TARGET_IDENTITY_INVALID")
        core = require_core()
        task_raw = core.canonical_json_bytes(verified)
        task_ref = core.sha256_ref(task_raw)
        task_id = verified.get("task_id")
        logical_time = verified.get("logical_time")
        nonce = verified.get("nonce")
        if (
            not isinstance(task_id, str)
            or isinstance(logical_time, bool)
            or not isinstance(logical_time, int)
            or not isinstance(nonce, str)
        ):
            raise MeshHold("HOLD_CONTROL_TASK_COORDINATE_INVALID")
        tuple_body = {
            "authority_ref": TOTAL_FIELD_AUTHORITY,
            "namespace": TASK_NAMESPACE,
            "nonce": nonce,
            "logical_time": logical_time,
            "task_ref": task_ref,
        }
        tuple_sha256 = core.sha256_hex(core.canonical_json_bytes(tuple_body))
        recorded_at = _utc(now_epoch)
        claimed = self.storage.journal.claim_replay(
            authority_ref=TOTAL_FIELD_AUTHORITY,
            namespace=TASK_NAMESPACE,
            nonce=nonce,
            logical_time=logical_time,
            tuple_sha256=tuple_sha256,
            packet_ref=task_ref,
            claimed_at=recorded_at,
        )
        if not claimed:
            raise MeshHold("HOLD_CONTROL_TASK_REPLAY")
        reservation = self._append_receipt(
            category="total_field_control_reservations",
            key=f"{logical_time:020d}-{task_id}-reserve",
            phase="RESERVE",
            state="PASS_RESERVED",
            task_ref=task_ref,
            task_id=task_id,
            logical_time=logical_time,
            recorded_at=recorded_at,
            detail={
                "operation": operation,
                "target_identity": target_identity,
                "snapshot_sha256": capability.snapshot_sha256,
                "resource_request": request.as_dict(),
                "placement_state": "EXACT_SNAPSHOT_BOUND",
                "execution_lease_id": execution_lease.get("lease_id"),
                "lease_transition": "ISSUED_TO_ACKNOWLEDGED",
            },
        )
        try:
            execution_detail = self.dispatcher.execute(operation, parameters)
        except MeshHold as exc:
            self._append_receipt(
                category="total_field_control_executions",
                key=f"{logical_time:020d}-{task_id}-execute",
                phase="EXECUTE",
                state="HOLD_EXECUTION_FAILED",
                task_ref=task_ref,
                task_id=task_id,
                logical_time=logical_time,
                recorded_at=recorded_at,
                detail={
                    "operation": operation,
                    "target_identity": target_identity,
                    "resource_request": request.as_dict(),
                    "reason_code": exc.code,
                    "reservation_receipt_sha256": reservation["receipt_sha256"],
                },
            )
            raise
        execution = self._append_receipt(
            category="total_field_control_executions",
            key=f"{logical_time:020d}-{task_id}-execute",
            phase="EXECUTE",
            state="PASS_EXECUTED_CANARY_ONLY",
            task_ref=task_ref,
            task_id=task_id,
            logical_time=logical_time,
            recorded_at=recorded_at,
            detail={
                "operation": operation,
                "target_identity": target_identity,
                "resource_request": request.as_dict(),
                "adapter_result": execution_detail,
                "reservation_receipt_sha256": reservation["receipt_sha256"],
                "lease_transition": "ACKNOWLEDGED_TO_RUNNING_TO_RESULT_CANDIDATE",
            },
        )
        try:
            verification_detail = self.dispatcher.verify(operation, parameters)
        except MeshHold as exc:
            self._append_receipt(
                category="total_field_control_verifications",
                key=f"{logical_time:020d}-{task_id}-verify",
                phase="VERIFY",
                state="HOLD_VERIFICATION_FAILED",
                task_ref=task_ref,
                task_id=task_id,
                logical_time=logical_time,
                recorded_at=recorded_at,
                detail={
                    "operation": operation,
                    "target_identity": target_identity,
                    "resource_request": request.as_dict(),
                    "reason_code": exc.code,
                    "execution_receipt_sha256": execution["receipt_sha256"],
                },
            )
            raise
        verification = self._append_receipt(
            category="total_field_control_verifications",
            key=f"{logical_time:020d}-{task_id}-verify",
            phase="VERIFY",
            state="PASS_VERIFIED_CANARY_ONLY",
            task_ref=task_ref,
            task_id=task_id,
            logical_time=logical_time,
            recorded_at=recorded_at,
            detail={
                "operation": operation,
                "target_identity": target_identity,
                "resource_request": request.as_dict(),
                "adapter_verification": verification_detail,
                "execution_receipt_sha256": execution["receipt_sha256"],
                "lease_transition": "RESULT_CANDIDATE_TO_ACCEPTED",
            },
        )
        adi_state = self._append_incremental_adi_state(
            task_ref=task_ref,
            task_id=task_id,
            logical_time=logical_time,
            recorded_at=recorded_at,
            verification_receipt=verification,
        )
        return {
            "state": "PASS_TOTAL_FIELD_CANARY_TASK_VERIFIED",
            "candidate_state": "CANDIDATE_NOT_CANONICAL_NOT_PROMOTED",
            "task_ref": task_ref,
            "reservation_receipt_sha256": reservation["receipt_sha256"],
            "execution_receipt_sha256": execution["receipt_sha256"],
            "verification_receipt_sha256": verification["receipt_sha256"],
            "adi_state_sha256": adi_state["state_sha256"],
            "authority_ref": TOTAL_FIELD_AUTHORITY,
            "primary_decision_engine": "8D_ADI",
            "human_summary_zh_tw": verification["human_summary_zh_tw"],
        }
