"""Fail-closed candidate executor for one sealed state-field effect.

The executor consumes verified coordinates and native proofs.  It cannot create
authority, dynamically load code, invoke a shell, or continue through a model.
"""

from __future__ import annotations

from dataclasses import asdict, replace
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Callable, Mapping, Protocol, Sequence

from .acceptance import DeterministicAcceptanceEngine
from .canonical import (
    canonical_hash,
    canonical_json_bytes,
    canonical_json_loads,
    sha256_hex,
    sha256_ref,
    validate_sha256_hex,
    validate_sha256_ref,
)
from .journal_recovery import StartedEffectRecord, validate_effect_transition
from .models import (
    BindingSet,
    CurrentPointer,
    DelegationRequest,
    EffectContract,
    EffectGateRequest,
    EffectObservation,
    EffectState,
    EvidenceLifecycleRequest,
    ExecuteCommand,
    ExecutionResult,
    FlowRequest,
    Hold,
    IdempotencyClass,
    IngressRepresentationRequest,
    JournalEventType,
    ObservationContext,
    PrepareContext,
    PreparedEffect,
    Quarantine,
    REQUIRED_NATIVE_CAPABILITIES,
    ResourceReady,
)
from .native_ports import (
    ADAPTERS,
    CAP_DELEGATION,
    CAP_EFFECT_GATE,
    CAP_EVIDENCE_LIFECYCLE,
    CAP_EXTERNAL_GATEWAY,
    CAP_INFORMATION_FLOW,
    HANDLERS,
    EffectHandler,
    NativePorts,
    ReceiverAdapter,
    prepared_effect_descriptor_ref,
    require_exact_effect_permit,
    require_exact_native_proof,
    resolve_static_adapter,
    resolve_static_handler,
)
from .object_packet_store import (
    ObjectPacketStore,
    ObjectStoreConflict,
    ObjectStoreHold,
)
from .store import (
    CASConflict as StoreCASConflict,
    JournalEventWrite,
    JournalHold,
    ReceiptWrite,
    StateCommitWrite,
    StateFieldStore,
    StoreConflict,
    StoreHold,
    TransitionWrite,
)


Clock = Callable[[], datetime]


class BindingResolverPort(Protocol):
    def require_verified_exact_set(
        self,
        binding_refs: Sequence[str],
        required_capabilities: frozenset[str],
    ) -> BindingSet: ...


class NativeRegistryPort(Protocol):
    def bind_all_static(self, bindings: BindingSet) -> NativePorts: ...


class ResourceResolverPort(Protocol):
    def require_resource_ready(self, mrs_ref: str) -> ResourceReady: ...


_EFFECT_EVENT_TYPES = frozenset(
    {
        JournalEventType.EFFECT_PREPARED,
        JournalEventType.EFFECT_STARTED,
        JournalEventType.EFFECT_OBSERVED,
        JournalEventType.EFFECT_FAILED,
        JournalEventType.EFFECT_ACCEPTED,
        JournalEventType.STATE_COMMITTED,
    }
)


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None:
        raise Quarantine("NAIVE_RUNTIME_CLOCK_CONFLICT")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class DurableOperationJournal:
    """Object-backed payloads plus SQLite FULL-synchronous event append."""

    def __init__(
        self,
        store: StateFieldStore,
        objects: ObjectPacketStore,
        command: ExecuteCommand,
        contract: EffectContract,
        clock: Clock,
    ) -> None:
        self._store = store
        self._objects = objects
        self._command = command
        self._contract = contract
        self._clock = clock

    def _events(self):
        return self._store.journal_events(
            self._command.operation_id,
            attempt_no=self._command.attempt_no,
        )

    def _effect_tail(self) -> JournalEventType | None:
        for event in reversed(self._events()):
            try:
                event_type = JournalEventType(event.event_type)
            except ValueError:
                continue
            if event_type in _EFFECT_EVENT_TYPES:
                return event_type
        return None

    def build_event(
        self,
        event_type: JournalEventType,
        payload: Mapping[str, object],
    ) -> JournalEventWrite:
        events = self._events()
        sequence_no = 0 if not events else events[-1].sequence_no + 1
        previous_hash = None if not events else events[-1].event_hash
        if event_type in _EFFECT_EVENT_TYPES:
            validate_effect_transition(self._effect_tail(), event_type)

        payload_body = {
            "operation_id": self._command.operation_id,
            "attempt_no": self._command.attempt_no,
            "effect_contract_ref": self._contract.effect_contract_ref,
            "effect_contract_hash": self._contract.effect_contract_hash,
            "event_type": event_type,
            "payload": dict(payload),
        }
        payload_ref = self._objects.put_bytes(
            canonical_json_bytes(payload_body)
        )
        occurred_at = _utc_text(self._clock())
        event_body = {
            "operation_id": self._command.operation_id,
            "attempt_no": self._command.attempt_no,
            "sequence_no": sequence_no,
            "effect_contract_ref": self._contract.effect_contract_ref,
            "effect_contract_hash": self._contract.effect_contract_hash,
            "event_type": event_type,
            "payload_ref": payload_ref,
            "previous_event_hash": previous_hash,
            "occurred_at": occurred_at,
        }
        return JournalEventWrite(
            operation_id=self._command.operation_id,
            attempt_no=self._command.attempt_no,
            sequence_no=sequence_no,
            effect_contract_ref=self._contract.effect_contract_ref,
            effect_contract_hash=self._contract.effect_contract_hash,
            event_type=event_type.value,
            payload_ref=payload_ref,
            previous_event_hash=previous_hash,
            event_hash=canonical_hash(event_body),
            occurred_at=occurred_at,
        )

    def append_sync(
        self,
        event_type: JournalEventType,
        payload: Mapping[str, object],
    ) -> str:
        try:
            event = self.build_event(event_type, payload)
            self._store.append_journal_event(event)
        except JournalHold as exc:
            raise Quarantine("EFFECT_JOURNAL_CHAIN_CONFLICT") from exc
        return f"sha256:{event.event_hash}"

    def require_started_without_observed(
        self,
        operation_id: str,
    ) -> StartedEffectRecord:
        if operation_id != self._command.operation_id:
            raise Quarantine("RECOVERY_OPERATION_COORDINATE_CONFLICT")
        events = self._events()
        if not events or events[-1].event_type != JournalEventType.EFFECT_STARTED:
            raise Hold("HOLD_STARTED_WITHOUT_OBSERVED_NOT_FOUND")
        started = events[-1]
        raw = self._objects.get_bytes(started.payload_ref)
        payload_packet = canonical_json_loads(raw)
        payload = payload_packet.get("payload", {})
        try:
            prepared = PreparedEffect(**payload["prepared"])
        except (KeyError, TypeError) as exc:
            raise Quarantine("RECOVERY_STARTED_PAYLOAD_CONFLICT") from exc
        return StartedEffectRecord(
            operation_id=operation_id,
            effect_contract_ref=started.effect_contract_ref,
            prepared=prepared,
            started_event_ref=f"sha256:{started.event_hash}",
            attempt_no=started.attempt_no,
        )


class StateFieldExecutor:
    """Execute one benign, sealed operation through all five native ports."""

    def __init__(
        self,
        *,
        store: StateFieldStore,
        objects: ObjectPacketStore,
        binding_resolver: BindingResolverPort,
        native_registry: NativeRegistryPort,
        resource_resolver: ResourceResolverPort,
        acceptance_engine: DeterministicAcceptanceEngine,
        adapters: Mapping[str, ReceiverAdapter] | None = None,
        handlers: Mapping[str, EffectHandler] | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._store = store
        self._objects = objects
        self._binding_resolver = binding_resolver
        self._native_registry = native_registry
        self._resource_resolver = resource_resolver
        self._acceptance = acceptance_engine
        self._adapters = self._freeze_effect_registry(
            ADAPTERS if adapters is None else adapters,
            reference_attribute="adapter_ref",
            method_names=("prepare", "observe"),
        )
        self._handlers = self._freeze_effect_registry(
            HANDLERS if handlers is None else handlers,
            reference_attribute="handler_ref",
            method_names=("apply",),
        )
        self._clock = clock or (lambda: datetime.now(UTC))

    def execute(self, command: ExecuteCommand) -> ExecutionResult:
        try:
            return self._execute(command)
        except Hold as exc:
            return ExecutionResult.hold(
                command.operation_id,
                exc.code,
                no_effect=exc.no_effect,
            )
        except Quarantine as exc:
            return ExecutionResult.quarantine(
                command.operation_id,
                exc.code,
            )
        except ObjectStoreConflict as exc:
            return ExecutionResult.quarantine(
                command.operation_id,
                getattr(exc, "reason_code", "OBJECT_STORE_CONFLICT"),
            )
        except ObjectStoreHold as exc:
            return ExecutionResult.hold(
                command.operation_id,
                getattr(exc, "reason_code", "HOLD_OBJECT_STORE_UNAVAILABLE"),
                no_effect=False,
            )
        except StoreHold as exc:
            return ExecutionResult.hold(
                command.operation_id,
                str(exc),
                no_effect=False,
            )
        except StoreConflict as exc:
            return ExecutionResult.quarantine(
                command.operation_id,
                str(exc),
            )

    def _execute(self, command: ExecuteCommand) -> ExecutionResult:
        if command.attempt_no < 1:
            raise Quarantine("ATTEMPT_NUMBER_CONFLICT")

        contract = EffectContract.load(command.effect_contract_ref, self._objects)
        self._require_command_contract_binding(command, contract)
        history = self._verified_operation_history(command, contract)
        committed = self._store.get_committed_by_idempotency(
            command.idempotency_key
        )
        if committed is not None:
            self._require_exact_replay(command, committed, history)
            return ExecutionResult(
                state="COMPLETED",
                operation_id=committed.operation_id,
                receipt_ref=committed.receipt_ref,
                transition_ref=committed.transition_ref,
                replayed=True,
            )

        adapter = self._resolve_adapter(contract.body.receiver_adapter_ref)
        handler = self._resolve_handler(contract.body.effect_handler_ref)
        if contract.body.idempotency is not handler.idempotency:
            raise Quarantine("IDEMPOTENCY_DECLARATION_CONFLICT")

        recovery_result = self._route_existing_operation(
            command=command,
            contract=contract,
            adapter=adapter,
            handler=handler,
            history=history,
        )
        if recovery_result is not None:
            return recovery_result

        # New execution begins with the closed resource and exact binding set.
        resource = self._resource_resolver.require_resource_ready(
            command.mrs_ref
        )
        if (
            resource.resource_id != command.resource_id
            or resource.mrs_ref != command.mrs_ref
        ):
            raise Quarantine("RESOURCE_COORDINATE_CONFLICT")

        bindings = self._binding_resolver.require_verified_exact_set(
            command.native_binding_refs,
            required_capabilities=REQUIRED_NATIVE_CAPABILITIES,
        )
        ports = self._native_registry.bind_all_static(bindings)

        exact_input = self._load_exact_input(contract.body.effect_input_ref)

        ingress_request = IngressRepresentationRequest(
            resource_ref=resource.resource_ref,
            manifest_ref=resource.manifest_ref,
            effect_contract_ref=contract.effect_contract_ref,
            capability_binding_refs=bindings.binding_refs,
        )
        ingress = require_exact_native_proof(
            ports.external_gateway.verify_ingress(ingress_request),
            ingress_request,
            CAP_EXTERNAL_GATEWAY,
        )

        delegation_request = DelegationRequest(
            ingress_proof_ref=ingress.proof_ref,
            effect_contract_ref=contract.effect_contract_ref,
            delegation_chain_ref=command.delegation_chain_ref,
        )
        delegation = require_exact_native_proof(
            ports.delegation.verify_delegation(delegation_request),
            delegation_request,
            CAP_DELEGATION,
        )

        flow_request = FlowRequest(
            resource_ref=resource.resource_ref,
            ingress_proof_ref=ingress.proof_ref,
            delegation_proof_ref=delegation.proof_ref,
            effect_contract_ref=contract.effect_contract_ref,
            target_coordinate_ref=contract.body.target_coordinate_ref,
        )
        flow = require_exact_native_proof(
            ports.information_flow.verify_flow(flow_request),
            flow_request,
            CAP_INFORMATION_FLOW,
        )

        gate_request = EffectGateRequest(
            effect_contract_ref=contract.effect_contract_ref,
            effect_contract_hash=contract.effect_contract_hash,
            policy_ref=command.policy_ref,
            d8_authorization_ref=command.d8_authorization_ref,
            d8_packet_ref=command.d8_packet_ref,
            authority_ref=command.authority_ref,
            base_version_ref=contract.body.base_version_ref,
            base_generation=contract.body.base_generation,
            target_coordinate_ref=contract.body.target_coordinate_ref,
            acceptance_contract_ref=contract.body.acceptance_contract_ref,
            flow_proof_ref=flow.proof_ref,
        )
        permit = require_exact_effect_permit(
            ports.effect_gate.verify_exact_authorization(gate_request),
            gate_request,
            proof_store=self._objects,
            expected_native_binding_ref=self._binding_ref_for_capability(
                bindings, CAP_EFFECT_GATE
            ),
            now=self._clock(),
        )

        # This load is deliberately after exact D8 verification and bypasses
        # any cache.  Both generation and version are gate-adjacent invariants.
        pointer_row = self._store.load_current_pointer_fresh(
            command.resource_id,
            bypass_cache=True,
        )
        pointer = CurrentPointer(
            resource_id=pointer_row.resource_id,
            version_ref=pointer_row.version_ref,
            generation=pointer_row.generation,
            state_ref=pointer_row.transition_ref,
        )
        journal = DurableOperationJournal(
            self._store, self._objects, command, contract, self._clock
        )
        if (
            pointer.generation != contract.body.base_generation
            or pointer.version_ref != contract.body.base_version_ref
        ):
            journal.append_sync(
                JournalEventType.STATE_DRIFT,
                {
                    "observed_generation": pointer.generation,
                    "observed_version_ref": pointer.version_ref,
                    "required_action": "RECOMPUTE_NEW_OPERATION",
                },
            )
            return ExecutionResult.hold(
                command.operation_id,
                "STATE_DRIFT_RECOMPUTE_NEW_OPERATION",
                no_effect=True,
            )

        self._ensure_effect_claim(
            command,
            contract,
            attempt_no=command.attempt_no,
            allow_existing=False,
        )

        journal.append_sync(
            JournalEventType.EFFECT_PREPARED,
            {
                "ingress_proof_ref": ingress.proof_ref,
                "delegation_proof_ref": delegation.proof_ref,
                "flow_proof_ref": flow.proof_ref,
                "permit_proof_ref": permit.proof_ref,
                "gate_request_hash": permit.bound_request_hash,
                "native_binding_refs": list(bindings.binding_refs),
                "pointer_generation": pointer.generation,
                "pointer_version_ref": pointer.version_ref,
                "receiver_prepare_effect": "NONE",
            },
        )
        try:
            prepared = adapter.prepare(
                PrepareContext(contract=contract, resource=resource, pointer=pointer)
            )
        except BaseException as error:
            disposition = (
                "QUARANTINE_NO_REAPPLY"
                if isinstance(error, Quarantine)
                else "RETRY_PRE_EFFECT_WITH_FRESH_AUTHORIZATION"
            )
            journal.append_sync(
                JournalEventType.EFFECT_FAILED,
                {
                    "phase": "PREPARE",
                    "effect_state": EffectState.NOT_STARTED,
                    "error_type": type(error).__name__,
                    "retry_disposition": disposition,
                },
            )
            if isinstance(error, Quarantine):
                raise error
            if isinstance(error, Hold):
                raise error
            raise Hold("HOLD_RECEIVER_PREPARE_FAILED", no_effect=True) from error

        try:
            self._require_prepared_effect_binding(
                prepared,
                contract,
                adapter,
                handler,
            )
        except BaseException as error:
            journal.append_sync(
                JournalEventType.EFFECT_FAILED,
                {
                    "phase": "PREPARED_BINDING",
                    "effect_state": EffectState.NOT_STARTED,
                    "error_type": type(error).__name__,
                    "retry_disposition": "QUARANTINE_NO_REAPPLY",
                },
            )
            if isinstance(error, Quarantine):
                raise
            raise Quarantine("PREPARED_EFFECT_BINDING_CONFLICT") from error

        try:
            require_exact_effect_permit(
                permit,
                gate_request,
                proof_store=self._objects,
                expected_native_binding_ref=self._binding_ref_for_capability(
                    bindings, CAP_EFFECT_GATE
                ),
                now=self._clock(),
            )
        except (Hold, Quarantine) as error:
            journal.append_sync(
                JournalEventType.EFFECT_FAILED,
                {
                    "phase": "PRE_APPLY_PERMIT_RECHECK",
                    "effect_state": EffectState.NOT_STARTED,
                    "retry_disposition": (
                        "QUARANTINE_NO_REAPPLY"
                        if isinstance(error, Quarantine)
                        else "RETRY_PRE_EFFECT_WITH_FRESH_AUTHORIZATION"
                    ),
                },
            )
            raise

        started_event_ref = journal.append_sync(
            JournalEventType.EFFECT_STARTED,
            {
                "prepared": asdict(prepared),
                "effect_input_ref": contract.body.effect_input_ref,
            },
        )

        try:
            handler.apply(prepared, exact_input)
        except BaseException as error:
            recovered = self._reobserve_after_apply_error(
                command=command,
                contract=contract,
                adapter=adapter,
                handler=handler,
                prepared=prepared,
                journal=journal,
                started_event_ref=started_event_ref,
                apply_error=error,
            )
            if isinstance(recovered, ExecutionResult):
                return recovered
            observation = recovered
        else:
            observation = self._observe_after_started(
                command,
                contract,
                adapter,
                prepared,
                journal,
                started_event_ref,
            )

        acceptance = self._acceptance.evaluate_exact(
            contract.body.acceptance_contract_ref,
            observation,
        )
        self._require_persisted_object(
            acceptance.evidence_ref,
            unavailable="HOLD_ACCEPTANCE_EVIDENCE_UNAVAILABLE",
            conflict="ACCEPTANCE_EVIDENCE_CONFLICT",
        )
        if not acceptance.accepted:
            journal.append_sync(
                JournalEventType.EFFECT_FAILED,
                {
                    "phase": "ACCEPTANCE",
                    "effect_state": observation.effect_state,
                    "acceptance_reason": acceptance.reason,
                    "retry_disposition": "QUARANTINE_NO_REAPPLY",
                },
            )
            return ExecutionResult.quarantine(
                command.operation_id,
                "QUARANTINE_EFFECT_NOT_ACCEPTED",
            )

        journal.append_sync(
            JournalEventType.EFFECT_ACCEPTED,
            {
                "observation_ref": observation.observation_ref,
                "acceptance_evidence_ref": acceptance.evidence_ref,
                "state_committed": False,
                "authority_created": False,
            },
        )

        lifecycle_request = EvidenceLifecycleRequest(
            operation_id=command.operation_id,
            effect_contract_ref=contract.effect_contract_ref,
            ingress_proof_ref=ingress.proof_ref,
            delegation_proof_ref=delegation.proof_ref,
            flow_proof_ref=flow.proof_ref,
            gate_proof_ref=permit.proof_ref,
            observation_ref=observation.observation_ref,
            acceptance_evidence_ref=acceptance.evidence_ref,
        )
        try:
            lifecycle = require_exact_native_proof(
                ports.evidence_lifecycle.verify_and_advance(
                    lifecycle_request
                ),
                lifecycle_request,
                CAP_EVIDENCE_LIFECYCLE,
            )
        except BaseException as error:
            journal.append_sync(
                JournalEventType.EFFECT_FAILED,
                {
                    "phase": "EVIDENCE_LIFECYCLE",
                    "effect_state": EffectState.PROVEN_COMPLETE,
                    "error_type": type(error).__name__,
                    "retry_disposition": "QUARANTINE_NO_REAPPLY",
                },
            )
            return ExecutionResult.quarantine(
                command.operation_id,
                "QUARANTINE_EVIDENCE_LIFECYCLE_FAILED",
            )

        return self._seal_and_commit(
            command=command,
            contract=contract,
            pointer=pointer,
            observation=observation,
            acceptance_evidence_ref=acceptance.evidence_ref,
            lifecycle_proof_ref=lifecycle.proof_ref,
            journal=journal,
        )

    @staticmethod
    def _freeze_effect_registry(
        source: Mapping[str, object],
        *,
        reference_attribute: str,
        method_names: tuple[str, ...],
    ) -> Mapping[str, object]:
        frozen: dict[str, object] = {}
        for reference, implementation in source.items():
            if (
                not isinstance(reference, str)
                or not reference
                or isinstance(implementation, type)
                or getattr(implementation, reference_attribute, None)
                != reference
                or any(
                    not callable(getattr(implementation, name, None))
                    for name in method_names
                )
            ):
                raise Quarantine("STATIC_EFFECT_REGISTRY_CONFLICT")
            frozen[reference] = implementation
        return MappingProxyType(frozen)

    def _resolve_adapter(self, reference: str) -> ReceiverAdapter:
        adapter = self._adapters.get(reference)
        if adapter is None:
            raise Hold("HOLD_RECEIVER_ADAPTER_UNAVAILABLE", no_effect=True)
        return adapter

    def _resolve_handler(self, reference: str) -> EffectHandler:
        handler = self._handlers.get(reference)
        if handler is None:
            raise Hold("HOLD_EFFECT_HANDLER_UNAVAILABLE", no_effect=True)
        return handler

    @staticmethod
    def _binding_ref_for_capability(
        bindings: BindingSet,
        capability_id: str,
    ) -> str:
        matches = tuple(
            binding.binding_ref
            for binding in bindings.bindings
            if binding.capability_id == capability_id
        )
        if len(matches) != 1:
            raise Quarantine("NATIVE_BINDING_CAPABILITY_CONFLICT")
        try:
            validate_sha256_ref(matches[0])
        except ValueError as exc:
            raise Quarantine("NATIVE_BINDING_REF_CONFLICT") from exc
        return matches[0]

    def _verified_operation_history(
        self,
        command: ExecuteCommand,
        contract: EffectContract,
    ) -> tuple[tuple[object, dict[str, object]], ...]:
        events = self._store.journal_events(command.operation_id)
        if not events:
            if command.attempt_no != 1:
                raise Quarantine("ATTEMPT_NUMBER_SEQUENCE_CONFLICT")
            return ()

        verified: list[tuple[object, dict[str, object]]] = []
        current_attempt: int | None = None
        expected_sequence = 0
        previous_hash: str | None = None
        previous_effect: JournalEventType | None = None
        operation_terminal = False
        for event in events:
            if operation_terminal:
                raise Quarantine("TERMINAL_OPERATION_HISTORY_CONFLICT")
            try:
                event_type = JournalEventType(event.event_type)
            except ValueError as exc:
                raise Quarantine("EFFECT_JOURNAL_EVENT_TYPE_CONFLICT") from exc
            if event.attempt_no != current_attempt:
                if current_attempt is None:
                    if event.attempt_no != 1:
                        raise Quarantine("ATTEMPT_NUMBER_SEQUENCE_CONFLICT")
                else:
                    if event.attempt_no != current_attempt + 1:
                        raise Quarantine("ATTEMPT_NUMBER_SEQUENCE_CONFLICT")
                    previous_event, previous_payload = verified[-1]
                    if (
                        JournalEventType(previous_event.event_type)
                        is not JournalEventType.EFFECT_FAILED
                        or not self._safe_retry_payload(
                            previous_payload, contract
                        )
                        or event_type is not JournalEventType.EFFECT_PREPARED
                    ):
                        raise Quarantine("UNSAFE_CROSS_ATTEMPT_HISTORY_CONFLICT")
                current_attempt = event.attempt_no
                expected_sequence = 0
                previous_hash = None
                previous_effect = None
            if (
                event.sequence_no != expected_sequence
                or event.previous_event_hash != previous_hash
                or event.effect_contract_ref != contract.effect_contract_ref
                or event.effect_contract_hash != contract.effect_contract_hash
            ):
                raise Quarantine("EFFECT_JOURNAL_CHAIN_CONFLICT")
            event_body = {
                "operation_id": event.operation_id,
                "attempt_no": event.attempt_no,
                "sequence_no": event.sequence_no,
                "effect_contract_ref": event.effect_contract_ref,
                "effect_contract_hash": event.effect_contract_hash,
                "event_type": event.event_type,
                "payload_ref": event.payload_ref,
                "previous_event_hash": event.previous_event_hash,
                "occurred_at": event.occurred_at,
            }
            if event.event_hash != canonical_hash(event_body):
                raise Quarantine("EFFECT_JOURNAL_EVENT_HASH_CONFLICT")
            if event_type in _EFFECT_EVENT_TYPES:
                validate_effect_transition(previous_effect, event_type)
                previous_effect = event_type
            if event_type is JournalEventType.STATE_DRIFT and (
                event.sequence_no != 0 or previous_effect is not None
            ):
                raise Quarantine("STATE_DRIFT_HISTORY_CONFLICT")
            effect_may_have_started = event_type not in {
                JournalEventType.EFFECT_PREPARED,
                JournalEventType.STATE_DRIFT,
            }
            payload = self._load_verified_journal_payload(
                event,
                contract,
                effect_may_have_started=effect_may_have_started,
            )
            verified.append((event, payload))
            expected_sequence += 1
            previous_hash = event.event_hash
            if event_type in {
                JournalEventType.STATE_DRIFT,
                JournalEventType.STATE_COMMITTED,
            }:
                operation_terminal = True
        return tuple(verified)

    @staticmethod
    def _safe_retry_payload(
        payload: Mapping[str, object],
        contract: EffectContract,
    ) -> bool:
        state = payload.get("effect_state")
        disposition = payload.get("retry_disposition")
        return (
            state == EffectState.NOT_STARTED.value
            and disposition == "RETRY_PRE_EFFECT_WITH_FRESH_AUTHORIZATION"
        ) or (
            state == EffectState.PROVEN_ABSENT.value
            and disposition == "RETRY_IDEMPOTENT_EXACT_OPERATION"
            and contract.body.idempotency is IdempotencyClass.IDEMPOTENT
        )

    def _load_verified_journal_payload(
        self,
        event: object,
        contract: EffectContract,
        *,
        effect_may_have_started: bool,
    ) -> dict[str, object]:
        try:
            validate_sha256_ref(event.payload_ref)
            raw = self._objects.get_bytes(event.payload_ref)
        except ObjectStoreHold as exc:
            if effect_may_have_started:
                raise Quarantine(
                    "JOURNAL_PAYLOAD_UNAVAILABLE_AFTER_EFFECT_BOUNDARY"
                ) from exc
            raise Hold("HOLD_JOURNAL_PAYLOAD_UNAVAILABLE", no_effect=True) from exc
        except (ObjectStoreConflict, ValueError) as exc:
            raise Quarantine("EFFECT_JOURNAL_PAYLOAD_CONFLICT") from exc
        if sha256_ref(raw) != event.payload_ref:
            raise Quarantine("EFFECT_JOURNAL_PAYLOAD_HASH_CONFLICT")
        try:
            packet = canonical_json_loads(raw)
        except ValueError as exc:
            raise Quarantine("EFFECT_JOURNAL_PAYLOAD_CONFLICT") from exc
        if (
            not isinstance(packet, dict)
            or set(packet)
            != {
                "operation_id",
                "attempt_no",
                "effect_contract_ref",
                "effect_contract_hash",
                "event_type",
                "payload",
            }
            or packet["operation_id"] != event.operation_id
            or packet["attempt_no"] != event.attempt_no
            or packet["effect_contract_ref"] != contract.effect_contract_ref
            or packet["effect_contract_hash"] != contract.effect_contract_hash
            or packet["event_type"] != event.event_type
            or not isinstance(packet["payload"], dict)
        ):
            raise Quarantine("EFFECT_JOURNAL_PAYLOAD_BINDING_CONFLICT")
        return dict(packet["payload"])

    def _route_existing_operation(
        self,
        *,
        command: ExecuteCommand,
        contract: EffectContract,
        adapter: ReceiverAdapter,
        handler: EffectHandler,
        history: tuple[tuple[object, dict[str, object]], ...],
    ) -> ExecutionResult | None:
        if not history:
            return None
        tail, payload = history[-1]
        tail_type = JournalEventType(tail.event_type)
        if tail_type is JournalEventType.STATE_DRIFT:
            return ExecutionResult.hold(
                command.operation_id,
                "STATE_DRIFT_RECOMPUTE_NEW_OPERATION",
                no_effect=True,
            )
        if tail_type is JournalEventType.EFFECT_STARTED:
            if command.attempt_no != tail.attempt_no:
                raise Quarantine("ATTEMPT_NUMBER_SEQUENCE_CONFLICT")
            self._ensure_effect_claim(
                command,
                contract,
                attempt_no=tail.attempt_no,
                allow_existing=True,
            )
            return self._recover_started_tail(
                command=command,
                contract=contract,
                adapter=adapter,
                handler=handler,
                tail=tail,
                payload=payload,
                history=history,
            )
        if tail_type is JournalEventType.EFFECT_OBSERVED:
            if command.attempt_no != tail.attempt_no:
                raise Quarantine("ATTEMPT_NUMBER_SEQUENCE_CONFLICT")
            self._ensure_effect_claim(
                command,
                contract,
                attempt_no=tail.attempt_no,
                allow_existing=True,
            )
            journal = DurableOperationJournal(
                self._store,
                self._objects,
                command,
                contract,
                self._clock,
            )
            observation = self._observation_from_history(
                history, tail.attempt_no
            )
            return self._resume_observed_operation(
                command=command,
                contract=contract,
                observation=observation,
                history=history,
                journal=journal,
                already_accepted=False,
            )
        if tail_type is JournalEventType.EFFECT_ACCEPTED:
            if command.attempt_no != tail.attempt_no:
                raise Quarantine("ATTEMPT_NUMBER_SEQUENCE_CONFLICT")
            self._ensure_effect_claim(
                command,
                contract,
                attempt_no=tail.attempt_no,
                allow_existing=True,
            )
            journal = DurableOperationJournal(
                self._store,
                self._objects,
                command,
                contract,
                self._clock,
            )
            observation = self._observation_from_history(
                history, tail.attempt_no
            )
            return self._resume_observed_operation(
                command=command,
                contract=contract,
                observation=observation,
                history=history,
                journal=journal,
                already_accepted=True,
            )
        if tail_type is JournalEventType.STATE_COMMITTED:
            raise Quarantine("COMMITTED_JOURNAL_WITHOUT_RECEIPT_CONFLICT")
        if tail_type is JournalEventType.EFFECT_PREPARED:
            self._require_next_attempt(command, tail.attempt_no)
            prior_command = replace(command, attempt_no=tail.attempt_no)
            self._ensure_effect_claim(
                prior_command,
                contract,
                attempt_no=tail.attempt_no,
                allow_existing=True,
            )
            DurableOperationJournal(
                self._store,
                self._objects,
                prior_command,
                contract,
                self._clock,
            ).append_sync(
                JournalEventType.EFFECT_FAILED,
                {
                    "phase": "RECOVERY_PRE_EFFECT",
                    "effect_state": EffectState.NOT_STARTED,
                    "retry_disposition": (
                        "RETRY_PRE_EFFECT_WITH_FRESH_AUTHORIZATION"
                    ),
                },
            )
            return None
        if tail_type is JournalEventType.EFFECT_FAILED:
            state = payload.get("effect_state")
            disposition = payload.get("retry_disposition")
            if disposition == "QUARANTINE_NO_REAPPLY" or state in {
                EffectState.PARTIAL.value,
                EffectState.UNKNOWN.value,
                EffectState.PROVEN_COMPLETE.value,
            }:
                raise Quarantine("TERMINAL_EFFECT_NO_REAPPLY")
            if self._safe_retry_payload(payload, contract) and (
                state != EffectState.PROVEN_ABSENT.value
                or handler.idempotency is IdempotencyClass.IDEMPOTENT
            ):
                self._require_next_attempt(command, tail.attempt_no)
                prior_command = replace(command, attempt_no=tail.attempt_no)
                self._ensure_effect_claim(
                    prior_command,
                    contract,
                    attempt_no=tail.attempt_no,
                    allow_existing=True,
                )
                return None
            raise Hold("HOLD_OPERATION_RETRY_NOT_PROVEN_SAFE", no_effect=True)
        raise Hold("HOLD_OPERATION_TAIL_UNRESOLVED", no_effect=True)

    @staticmethod
    def _require_next_attempt(command: ExecuteCommand, previous: int) -> None:
        if command.attempt_no != previous + 1:
            raise Quarantine("ATTEMPT_NUMBER_SEQUENCE_CONFLICT")

    def _ensure_effect_claim(
        self,
        command: ExecuteCommand,
        contract: EffectContract,
        *,
        attempt_no: int,
        allow_existing: bool,
    ) -> None:
        operation_claim = self._store.get_effect_operation_claim(
            command.idempotency_key
        )
        attempt_claim = self._store.get_effect_attempt_claim(
            command.operation_id,
            attempt_no,
        )
        if operation_claim is not None and (
            operation_claim.operation_id != command.operation_id
            or operation_claim.effect_contract_ref
            != contract.effect_contract_ref
        ):
            raise Quarantine("IDEMPOTENCY_OPERATION_CLAIM_CONFLICT")
        if attempt_claim is not None and (
            attempt_claim.idempotency_key != command.idempotency_key
            or attempt_claim.effect_contract_ref
            != contract.effect_contract_ref
        ):
            raise Quarantine("EFFECT_ATTEMPT_CLAIM_CONFLICT")
        if attempt_claim is not None:
            if not allow_existing:
                raise Hold(
                    "HOLD_EFFECT_ATTEMPT_ALREADY_CLAIMED_RECOVERY_REQUIRED",
                    no_effect=True,
                )
            return
        result = self._store.claim_effect_operation(
            idempotency_key=command.idempotency_key,
            operation_id=command.operation_id,
            effect_contract_ref=contract.effect_contract_ref,
            attempt_no=attempt_no,
            claimed_at=_utc_text(self._clock()),
        )
        if result != "CLAIMED":
            raise Quarantine("EFFECT_OPERATION_CLAIM_RESULT_CONFLICT")

    def _recover_started_tail(
        self,
        *,
        command: ExecuteCommand,
        contract: EffectContract,
        adapter: ReceiverAdapter,
        handler: EffectHandler,
        tail: object,
        payload: Mapping[str, object],
        history: tuple[tuple[object, dict[str, object]], ...],
    ) -> ExecutionResult:
        try:
            prepared_packet = payload["prepared"]
            if not isinstance(prepared_packet, dict):
                raise TypeError("prepared packet is not an object")
            prepared = PreparedEffect(**prepared_packet)
        except (KeyError, TypeError, ValueError) as exc:
            raise Quarantine("RECOVERY_STARTED_PAYLOAD_CONFLICT") from exc
        self._require_prepared_effect_binding(
            prepared, contract, adapter, handler
        )
        recovery_command = replace(command, attempt_no=tail.attempt_no)
        journal = DurableOperationJournal(
            self._store,
            self._objects,
            recovery_command,
            contract,
            self._clock,
        )
        try:
            observation = adapter.observe(
                ObservationContext(
                    contract=contract,
                    prepared=prepared,
                    started_event_ref=f"sha256:{tail.event_hash}",
                )
            )
            self._require_observation_evidence(observation)
        except BaseException as error:
            journal.append_sync(
                JournalEventType.EFFECT_FAILED,
                {
                    "phase": "RECOVERY_REOBSERVE",
                    "effect_state": EffectState.UNKNOWN,
                    "retry_disposition": "QUARANTINE_NO_REAPPLY",
                    "error_type": type(error).__name__,
                },
            )
            return ExecutionResult.quarantine(
                command.operation_id,
                "QUARANTINE_RECEIVER_REOBSERVATION_FAILED",
            )

        if observation.effect_state is EffectState.COMPLETE:
            journal.append_sync(
                JournalEventType.EFFECT_OBSERVED,
                {
                    "observation_ref": observation.observation_ref,
                    "evidence_ref": observation.evidence_ref,
                    "actual_hash": observation.actual_hash,
                    "effect_state": observation.effect_state,
                    "synthetic": True,
                },
            )
            return self._resume_observed_operation(
                command=recovery_command,
                contract=contract,
                observation=observation,
                history=history,
                journal=journal,
                already_accepted=False,
            )

        if observation.effect_state is EffectState.ABSENT:
            retry_allowed = (
                contract.body.idempotency is IdempotencyClass.IDEMPOTENT
                and handler.idempotency is IdempotencyClass.IDEMPOTENT
            )
            journal.append_sync(
                JournalEventType.EFFECT_FAILED,
                {
                    "phase": "RECOVERY_REOBSERVE",
                    "effect_state": EffectState.PROVEN_ABSENT,
                    "observation_ref": observation.observation_ref,
                    "retry_disposition": (
                        "RETRY_IDEMPOTENT_EXACT_OPERATION"
                        if retry_allowed
                        else "NO_AUTOMATIC_RETRY"
                    ),
                },
            )
            return ExecutionResult.hold(
                command.operation_id,
                (
                    "HOLD_RETRY_IDEMPOTENT_EXACT_OPERATION_REQUIRES_FRESH_GATE"
                    if retry_allowed
                    else "HOLD_NON_IDEMPOTENT_RETRY_FORBIDDEN"
                ),
                no_effect=True,
            )

        journal.append_sync(
            JournalEventType.EFFECT_FAILED,
            {
                "phase": "RECOVERY_REOBSERVE",
                "effect_state": observation.effect_state,
                "observation_ref": observation.observation_ref,
                "retry_disposition": "QUARANTINE_NO_REAPPLY",
            },
        )
        return ExecutionResult.quarantine(
            command.operation_id,
            "QUARANTINE_EFFECT_STATE_UNKNOWN_OR_PARTIAL",
        )

    def _observation_from_history(
        self,
        history: tuple[tuple[object, dict[str, object]], ...],
        attempt_no: int,
    ) -> EffectObservation:
        matches = tuple(
            payload
            for event, payload in history
            if event.attempt_no == attempt_no
            and event.event_type == JournalEventType.EFFECT_OBSERVED.value
        )
        if len(matches) != 1:
            raise Quarantine("RECOVERY_OBSERVATION_HISTORY_CONFLICT")
        payload = matches[0]
        try:
            observation = EffectObservation(
                effect_state=EffectState(payload["effect_state"]),
                observation_ref=payload["observation_ref"],
                evidence_ref=payload["evidence_ref"],
                actual_hash=payload.get("actual_hash"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise Quarantine("RECOVERY_OBSERVATION_HISTORY_CONFLICT") from exc
        self._require_observation_evidence(observation)
        return observation

    def _prepared_recovery_payload(
        self,
        history: tuple[tuple[object, dict[str, object]], ...],
        attempt_no: int,
        command: ExecuteCommand,
    ) -> dict[str, object]:
        matches = tuple(
            payload
            for event, payload in history
            if event.attempt_no == attempt_no
            and event.event_type == JournalEventType.EFFECT_PREPARED.value
        )
        if len(matches) != 1:
            raise Quarantine("RECOVERY_PREPARED_HISTORY_CONFLICT")
        payload = matches[0]
        required_refs = (
            "ingress_proof_ref",
            "delegation_proof_ref",
            "flow_proof_ref",
            "permit_proof_ref",
        )
        try:
            for name in required_refs:
                validate_sha256_ref(payload[name])
            validate_sha256_hex(payload["gate_request_hash"])
            binding_refs = tuple(payload["native_binding_refs"])
            for reference in binding_refs:
                validate_sha256_ref(reference)
        except (KeyError, TypeError, ValueError) as exc:
            raise Quarantine("RECOVERY_PREPARED_HISTORY_CONFLICT") from exc
        if (
            len(binding_refs) != len(set(binding_refs))
            or tuple(sorted(binding_refs))
            != tuple(sorted(command.native_binding_refs))
        ):
            raise Quarantine("RECOVERY_NATIVE_BINDING_HISTORY_CONFLICT")
        self._require_persisted_object(
            payload["permit_proof_ref"],
            unavailable="HOLD_RECOVERY_GATE_PROOF_UNAVAILABLE",
            conflict="RECOVERY_GATE_PROOF_CONFLICT",
        )
        return payload

    def _resume_observed_operation(
        self,
        *,
        command: ExecuteCommand,
        contract: EffectContract,
        observation: EffectObservation,
        history: tuple[tuple[object, dict[str, object]], ...],
        journal: DurableOperationJournal,
        already_accepted: bool,
    ) -> ExecutionResult:
        self._require_observation_evidence(observation)
        prepared_payload = self._prepared_recovery_payload(
            history,
            command.attempt_no,
            command,
        )
        pointer_row = self._store.load_current_pointer_fresh(
            command.resource_id,
            bypass_cache=True,
        )
        pointer = CurrentPointer(
            resource_id=pointer_row.resource_id,
            version_ref=pointer_row.version_ref,
            generation=pointer_row.generation,
            state_ref=pointer_row.transition_ref,
        )
        if (
            pointer.generation != contract.body.base_generation
            or pointer.version_ref != contract.body.base_version_ref
        ):
            journal.append_sync(
                JournalEventType.EFFECT_FAILED,
                {
                    "phase": "RECOVERY_POST_EFFECT_STATE_DRIFT",
                    "effect_state": EffectState.PROVEN_COMPLETE,
                    "retry_disposition": "QUARANTINE_NO_REAPPLY",
                    "observed_generation": pointer.generation,
                    "observed_version_ref": pointer.version_ref,
                },
            )
            return ExecutionResult.quarantine(
                command.operation_id,
                "QUARANTINE_POST_EFFECT_STATE_DRIFT",
            )

        acceptance = self._acceptance.evaluate_exact(
            contract.body.acceptance_contract_ref,
            observation,
        )
        self._require_persisted_object(
            acceptance.evidence_ref,
            unavailable="HOLD_ACCEPTANCE_EVIDENCE_UNAVAILABLE",
            conflict="ACCEPTANCE_EVIDENCE_CONFLICT",
        )
        if not acceptance.accepted:
            journal.append_sync(
                JournalEventType.EFFECT_FAILED,
                {
                    "phase": "RECOVERY_ACCEPTANCE",
                    "effect_state": observation.effect_state,
                    "acceptance_reason": acceptance.reason,
                    "retry_disposition": "QUARANTINE_NO_REAPPLY",
                },
            )
            return ExecutionResult.quarantine(
                command.operation_id,
                "QUARANTINE_EFFECT_NOT_ACCEPTED",
            )

        if already_accepted:
            accepted_tail, accepted_payload = history[-1]
            if (
                accepted_tail.event_type
                != JournalEventType.EFFECT_ACCEPTED.value
                or accepted_tail.attempt_no != command.attempt_no
                or accepted_payload.get("observation_ref")
                != observation.observation_ref
                or accepted_payload.get("acceptance_evidence_ref")
                != acceptance.evidence_ref
                or accepted_payload.get("state_committed") is not False
                or accepted_payload.get("authority_created") is not False
            ):
                raise Quarantine("RECOVERY_ACCEPTED_HISTORY_CONFLICT")
        else:
            journal.append_sync(
                JournalEventType.EFFECT_ACCEPTED,
                {
                    "observation_ref": observation.observation_ref,
                    "acceptance_evidence_ref": acceptance.evidence_ref,
                    "state_committed": False,
                    "authority_created": False,
                },
            )

        bindings = self._binding_resolver.require_verified_exact_set(
            command.native_binding_refs,
            required_capabilities=REQUIRED_NATIVE_CAPABILITIES,
        )
        ports = self._native_registry.bind_all_static(bindings)
        lifecycle_request = EvidenceLifecycleRequest(
            operation_id=command.operation_id,
            effect_contract_ref=contract.effect_contract_ref,
            ingress_proof_ref=prepared_payload["ingress_proof_ref"],
            delegation_proof_ref=prepared_payload["delegation_proof_ref"],
            flow_proof_ref=prepared_payload["flow_proof_ref"],
            gate_proof_ref=prepared_payload["permit_proof_ref"],
            observation_ref=observation.observation_ref,
            acceptance_evidence_ref=acceptance.evidence_ref,
        )
        try:
            lifecycle = require_exact_native_proof(
                ports.evidence_lifecycle.verify_and_advance(
                    lifecycle_request
                ),
                lifecycle_request,
                CAP_EVIDENCE_LIFECYCLE,
            )
        except BaseException as error:
            journal.append_sync(
                JournalEventType.EFFECT_FAILED,
                {
                    "phase": "RECOVERY_EVIDENCE_LIFECYCLE",
                    "effect_state": EffectState.PROVEN_COMPLETE,
                    "error_type": type(error).__name__,
                    "retry_disposition": "QUARANTINE_NO_REAPPLY",
                },
            )
            return ExecutionResult.quarantine(
                command.operation_id,
                "QUARANTINE_EVIDENCE_LIFECYCLE_FAILED",
            )

        return self._seal_and_commit(
            command=command,
            contract=contract,
            pointer=pointer,
            observation=observation,
            acceptance_evidence_ref=acceptance.evidence_ref,
            lifecycle_proof_ref=lifecycle.proof_ref,
            journal=journal,
        )

    @staticmethod
    def _require_prepared_effect_binding(
        prepared: PreparedEffect,
        contract: EffectContract,
        adapter: ReceiverAdapter,
        handler: EffectHandler,
    ) -> None:
        if (
            not isinstance(prepared, PreparedEffect)
            or prepared.effect_contract_ref != contract.effect_contract_ref
            or prepared.receiver_adapter_ref
            != contract.body.receiver_adapter_ref
            or prepared.effect_handler_ref != contract.body.effect_handler_ref
            or prepared.descriptor_ref
            != prepared_effect_descriptor_ref(contract)
            or prepared.target_coordinate_ref
            != contract.body.target_coordinate_ref
            or prepared.idempotency_key != contract.body.idempotency_key
            or getattr(adapter, "adapter_ref", None)
            != contract.body.receiver_adapter_ref
            or getattr(handler, "handler_ref", None)
            != contract.body.effect_handler_ref
        ):
            raise Quarantine("PREPARED_EFFECT_BINDING_CONFLICT")

    def _require_observation_evidence(
        self,
        observation: EffectObservation,
    ) -> None:
        observation.require_receiver_evidence()
        for reference in {
            observation.observation_ref,
            observation.evidence_ref,
        }:
            self._require_persisted_object(
                reference,
                unavailable="HOLD_OBSERVATION_EVIDENCE_UNAVAILABLE",
                conflict="OBSERVATION_EVIDENCE_CONFLICT",
            )
        if observation.actual_hash is not None:
            try:
                validate_sha256_hex(observation.actual_hash)
            except ValueError as exc:
                raise Quarantine("OBSERVATION_ACTUAL_HASH_CONFLICT") from exc
        if (
            observation.effect_state is EffectState.COMPLETE
            and observation.actual_hash is None
        ) or (
            observation.effect_state is EffectState.ABSENT
            and observation.actual_hash is not None
        ):
            raise Quarantine("OBSERVATION_STATE_HASH_CONFLICT")

    def _require_persisted_object(
        self,
        reference: str,
        *,
        unavailable: str,
        conflict: str,
    ) -> bytes:
        try:
            validate_sha256_ref(reference)
            raw = self._objects.get_bytes(reference)
        except ObjectStoreHold as exc:
            raise Hold(unavailable, no_effect=True) from exc
        except (ObjectStoreConflict, ValueError) as exc:
            raise Quarantine(conflict) from exc
        if sha256_ref(raw) != reference:
            raise Quarantine(conflict)
        return raw

    def _observe_after_started(
        self,
        command: ExecuteCommand,
        contract: EffectContract,
        adapter: ReceiverAdapter,
        prepared: PreparedEffect,
        journal: DurableOperationJournal,
        started_event_ref: str,
    ) -> EffectObservation:
        try:
            observation = adapter.observe(
                ObservationContext(
                    contract=contract,
                    prepared=prepared,
                    started_event_ref=started_event_ref,
                )
            )
            self._require_observation_evidence(observation)
        except BaseException as error:
            journal.append_sync(
                JournalEventType.EFFECT_FAILED,
                {
                    "phase": "OBSERVE",
                    "effect_state": EffectState.UNKNOWN,
                    "error_type": type(error).__name__,
                    "retry_disposition": "QUARANTINE_NO_REAPPLY",
                },
            )
            raise Quarantine("QUARANTINE_RECEIVER_OBSERVATION_FAILED") from error
        journal.append_sync(
            JournalEventType.EFFECT_OBSERVED,
            {
                "observation_ref": observation.observation_ref,
                "evidence_ref": observation.evidence_ref,
                "actual_hash": observation.actual_hash,
                "effect_state": observation.effect_state,
                "synthetic": False,
            },
        )
        return observation

    def _reobserve_after_apply_error(
        self,
        *,
        command: ExecuteCommand,
        contract: EffectContract,
        adapter: ReceiverAdapter,
        handler: EffectHandler,
        prepared: PreparedEffect,
        journal: DurableOperationJournal,
        started_event_ref: str,
        apply_error: BaseException,
    ) -> EffectObservation | ExecutionResult:
        # The first receiver action after an uncertain apply is observation.
        try:
            observation = adapter.observe(
                ObservationContext(
                    contract=contract,
                    prepared=prepared,
                    started_event_ref=started_event_ref,
                )
            )
            self._require_observation_evidence(observation)
        except BaseException as observation_error:
            journal.append_sync(
                JournalEventType.EFFECT_FAILED,
                {
                    "phase": "RECOVERY_REOBSERVE",
                    "effect_state": EffectState.UNKNOWN,
                    "apply_error_type": type(apply_error).__name__,
                    "observation_error_type": type(observation_error).__name__,
                    "retry_disposition": "QUARANTINE_NO_REAPPLY",
                },
            )
            return ExecutionResult.quarantine(
                command.operation_id,
                "QUARANTINE_RECEIVER_REOBSERVATION_FAILED",
            )

        if observation.effect_state is EffectState.COMPLETE:
            journal.append_sync(
                JournalEventType.EFFECT_OBSERVED,
                {
                    "observation_ref": observation.observation_ref,
                    "evidence_ref": observation.evidence_ref,
                    "actual_hash": observation.actual_hash,
                    "effect_state": observation.effect_state,
                    "synthetic": True,
                    "apply_error_type": type(apply_error).__name__,
                },
            )
            return observation

        if observation.effect_state is EffectState.ABSENT:
            retry_allowed = (
                contract.body.idempotency is IdempotencyClass.IDEMPOTENT
                and handler.idempotency is IdempotencyClass.IDEMPOTENT
            )
            journal.append_sync(
                JournalEventType.EFFECT_FAILED,
                {
                    "phase": "RECOVERY_REOBSERVE",
                    "effect_state": EffectState.PROVEN_ABSENT,
                    "observation_ref": observation.observation_ref,
                    "retry_disposition": (
                        "RETRY_IDEMPOTENT_EXACT_OPERATION"
                        if retry_allowed
                        else "NO_AUTOMATIC_RETRY"
                    ),
                },
            )
            reason = (
                "HOLD_RETRY_IDEMPOTENT_EXACT_OPERATION_REQUIRES_FRESH_GATE"
                if retry_allowed
                else "HOLD_NON_IDEMPOTENT_RETRY_FORBIDDEN"
            )
            return ExecutionResult.hold(
                command.operation_id,
                reason,
                no_effect=True,
            )

        journal.append_sync(
            JournalEventType.EFFECT_FAILED,
            {
                "phase": "RECOVERY_REOBSERVE",
                "effect_state": observation.effect_state,
                "observation_ref": observation.observation_ref,
                "retry_disposition": "QUARANTINE_NO_REAPPLY",
            },
        )
        return ExecutionResult.quarantine(
            command.operation_id,
            "QUARANTINE_EFFECT_STATE_UNKNOWN_OR_PARTIAL",
        )

    def _seal_and_commit(
        self,
        *,
        command: ExecuteCommand,
        contract: EffectContract,
        pointer: CurrentPointer,
        observation: EffectObservation,
        acceptance_evidence_ref: str,
        lifecycle_proof_ref: str,
        journal: DurableOperationJournal,
    ) -> ExecutionResult:
        if observation.actual_hash is None:
            raise Quarantine("COMPLETED_EFFECT_HASH_MISSING")
        result_version_ref = f"sha256:{observation.actual_hash}"
        created_at = _utc_text(self._clock())
        receipt_body = {
            "schema_id": "W7TP_EXECUTION_RECEIPT_V1",
            "operation_id": command.operation_id,
            "effect_contract_ref": contract.effect_contract_ref,
            "effect_contract_hash": contract.effect_contract_hash,
            "result_version_ref": result_version_ref,
            "observation_ref": observation.observation_ref,
            "acceptance_evidence_ref": acceptance_evidence_ref,
            "lifecycle_proof_ref": lifecycle_proof_ref,
            "created_at": created_at,
        }
        receipt_raw = canonical_json_bytes(receipt_body)
        receipt_ref = self._objects.put_bytes(receipt_raw)
        receipt_hash = sha256_hex(receipt_raw)

        transition_body = {
            "schema_id": "W7TP_STATE_TRANSITION_V1",
            "operation_id": command.operation_id,
            "resource_id": command.resource_id,
            "from_version_ref": pointer.version_ref,
            "to_version_ref": result_version_ref,
            "expected_generation": pointer.generation,
            "receipt_ref": receipt_ref,
            "created_at": created_at,
        }
        transition_hash = canonical_hash(transition_body)
        transition_ref = f"sha256:{transition_hash}"

        transition = TransitionWrite(
            transition_ref=transition_ref,
            transition_hash=transition_hash,
            operation_id=command.operation_id,
            resource_id=command.resource_id,
            from_version_ref=pointer.version_ref,
            to_version_ref=result_version_ref,
            expected_generation=pointer.generation,
            receipt_ref=receipt_ref,
            created_at=created_at,
        )
        receipt = ReceiptWrite(
            receipt_ref=receipt_ref,
            receipt_hash=receipt_hash,
            operation_id=command.operation_id,
            idempotency_key=command.idempotency_key,
            transition_ref=transition_ref,
            effect_contract_ref=contract.effect_contract_ref,
            effect_contract_hash=contract.effect_contract_hash,
            result_version_ref=result_version_ref,
            payload_ref=receipt_ref,
            created_at=created_at,
        )
        commit_event = journal.build_event(
            JournalEventType.STATE_COMMITTED,
            {
                "receipt_ref": receipt_ref,
                "transition_ref": transition_ref,
                "new_version_ref": result_version_ref,
                "new_generation": pointer.generation + 1,
                "authority_created": False,
            },
        )
        try:
            committed = self._store.commit_state(
                StateCommitWrite(
                    transition=transition,
                    receipt=receipt,
                    journal=commit_event,
                    pointer_updated_at=created_at,
                )
            )
        except StoreCASConflict:
            journal.append_sync(
                JournalEventType.EFFECT_FAILED,
                {
                    "phase": "POST_EFFECT_CAS",
                    "effect_state": EffectState.PROVEN_COMPLETE,
                    "retry_disposition": "QUARANTINE_NO_REAPPLY",
                },
            )
            return ExecutionResult.quarantine(
                command.operation_id,
                "QUARANTINE_POST_EFFECT_CAS_CONFLICT",
            )
        except (StoreHold, StoreConflict) as error:
            journal.append_sync(
                JournalEventType.EFFECT_FAILED,
                {
                    "phase": "POST_EFFECT_COMMIT",
                    "effect_state": EffectState.PROVEN_COMPLETE,
                    "error_type": type(error).__name__,
                    "retry_disposition": "QUARANTINE_NO_REAPPLY",
                },
            )
            return ExecutionResult.quarantine(
                command.operation_id,
                "QUARANTINE_POST_EFFECT_COMMIT_CONFLICT",
            )
        return ExecutionResult(
            state="COMPLETED",
            operation_id=command.operation_id,
            receipt_ref=committed.receipt.receipt_ref,
            transition_ref=committed.receipt.transition_ref,
            replayed=committed.replayed,
        )

    def _load_exact_input(self, ref: str) -> bytes:
        try:
            validate_sha256_ref(ref)
            raw = self._objects.get_bytes(ref)
        except ObjectStoreHold as exc:
            raise Hold("HOLD_EFFECT_INPUT_UNAVAILABLE", no_effect=True) from exc
        except (ObjectStoreConflict, ValueError) as exc:
            raise Quarantine("EFFECT_INPUT_REF_HASH_CONFLICT") from exc
        if sha256_ref(raw) != ref:
            raise Quarantine("EFFECT_INPUT_REF_HASH_CONFLICT")
        return raw

    def _require_command_contract_binding(
        self,
        command: ExecuteCommand,
        contract: EffectContract,
    ) -> None:
        if (
            contract.body.operation_id != command.operation_id
            or contract.body.idempotency_key != command.idempotency_key
            or contract.effect_contract_ref != command.effect_contract_ref
        ):
            raise Quarantine("COMMAND_EFFECT_CONTRACT_BINDING_CONFLICT")

    def _require_exact_replay(self, command, committed, history) -> None:
        if (
            committed.operation_id != command.operation_id
            or committed.resource_id != command.resource_id
            or committed.effect_contract_ref != command.effect_contract_ref
            or not history
        ):
            raise Quarantine("IDEMPOTENCY_REPLAY_COORDINATE_CONFLICT")
        tail, tail_payload = history[-1]
        if (
            JournalEventType(tail.event_type)
            is not JournalEventType.STATE_COMMITTED
            or tail.attempt_no != command.attempt_no
        ):
            raise Quarantine("IDEMPOTENCY_REPLAY_JOURNAL_CONFLICT")
        try:
            raw = self._objects.get_bytes(committed.payload_ref)
        except ObjectStoreHold as exc:
            raise Hold("HOLD_REPLAY_RECEIPT_UNAVAILABLE", no_effect=True) from exc
        except (ObjectStoreConflict, ValueError) as exc:
            raise Quarantine("REPLAY_RECEIPT_HASH_CONFLICT") from exc
        if (
            sha256_hex(raw) != committed.receipt_hash
            or committed.receipt_ref != f"sha256:{committed.receipt_hash}"
            or committed.payload_ref != committed.receipt_ref
        ):
            raise Quarantine("REPLAY_RECEIPT_HASH_CONFLICT")
        try:
            receipt_packet = canonical_json_loads(raw)
        except ValueError as exc:
            raise Quarantine("REPLAY_RECEIPT_BODY_CONFLICT") from exc
        required_receipt_fields = {
            "schema_id",
            "operation_id",
            "effect_contract_ref",
            "effect_contract_hash",
            "result_version_ref",
            "observation_ref",
            "acceptance_evidence_ref",
            "lifecycle_proof_ref",
            "created_at",
        }
        if (
            not isinstance(receipt_packet, dict)
            or set(receipt_packet) != required_receipt_fields
            or receipt_packet["schema_id"] != "W7TP_EXECUTION_RECEIPT_V1"
            or receipt_packet["operation_id"] != committed.operation_id
            or receipt_packet["effect_contract_ref"]
            != committed.effect_contract_ref
            or receipt_packet["effect_contract_hash"]
            != committed.effect_contract_hash
            or receipt_packet["result_version_ref"]
            != committed.result_version_ref
            or receipt_packet["created_at"] != committed.created_at
        ):
            raise Quarantine("REPLAY_RECEIPT_BODY_CONFLICT")
        for reference_name in (
            "observation_ref",
            "acceptance_evidence_ref",
            "lifecycle_proof_ref",
        ):
            try:
                validate_sha256_ref(receipt_packet[reference_name])
            except (TypeError, ValueError) as exc:
                raise Quarantine("REPLAY_RECEIPT_BODY_CONFLICT") from exc

        transition_body = {
            "schema_id": "W7TP_STATE_TRANSITION_V1",
            "operation_id": committed.operation_id,
            "resource_id": committed.resource_id,
            "from_version_ref": committed.from_version_ref,
            "to_version_ref": committed.to_version_ref,
            "expected_generation": committed.expected_generation,
            "receipt_ref": committed.transition_receipt_ref,
            "created_at": committed.transition_created_at,
        }
        expected_transition_hash = canonical_hash(transition_body)
        if (
            committed.transition_hash != expected_transition_hash
            or committed.transition_ref
            != f"sha256:{expected_transition_hash}"
            or committed.transition_receipt_ref != committed.receipt_ref
            or committed.to_version_ref != committed.result_version_ref
            or tail_payload.get("receipt_ref") != committed.receipt_ref
            or tail_payload.get("transition_ref") != committed.transition_ref
            or tail_payload.get("new_version_ref")
            != committed.result_version_ref
            or tail_payload.get("new_generation")
            != committed.expected_generation + 1
            or tail_payload.get("authority_created") is not False
        ):
            raise Quarantine("IDEMPOTENCY_REPLAY_TRANSITION_CONFLICT")
        pointer = self._store.load_current_pointer_fresh(
            committed.resource_id,
            bypass_cache=True,
        )
        if (
            pointer.generation != committed.expected_generation + 1
            or pointer.version_ref != committed.result_version_ref
            or pointer.transition_ref != committed.transition_ref
        ):
            raise Quarantine("IDEMPOTENCY_REPLAY_POINTER_CONFLICT")
        operation_claim = self._store.get_effect_operation_claim(
            command.idempotency_key
        )
        attempt_claim = self._store.get_effect_attempt_claim(
            command.operation_id,
            tail.attempt_no,
        )
        if (
            operation_claim is None
            or attempt_claim is None
            or operation_claim.operation_id != command.operation_id
            or operation_claim.effect_contract_ref
            != command.effect_contract_ref
            or attempt_claim.idempotency_key != command.idempotency_key
            or attempt_claim.effect_contract_ref
            != command.effect_contract_ref
        ):
            raise Quarantine("IDEMPOTENCY_REPLAY_CLAIM_CONFLICT")
