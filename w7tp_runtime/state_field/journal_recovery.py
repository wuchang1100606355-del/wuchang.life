"""Effect-journal transition validation and fail-closed recovery decisions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping, Protocol

from .canonical import validate_sha256_hex, validate_sha256_ref
from .models import (
    EffectContract,
    EffectObservation,
    EffectState,
    Hold,
    IdempotencyClass,
    JournalEventType,
    ObservationContext,
    PreparedEffect,
    Quarantine,
)
from .native_ports import (
    ADAPTERS,
    HANDLERS,
    EffectHandler,
    ReceiverAdapter,
)


EFFECT_TRANSITIONS: Mapping[JournalEventType | None, frozenset[JournalEventType]] = {
    None: frozenset({JournalEventType.EFFECT_PREPARED}),
    JournalEventType.EFFECT_PREPARED: frozenset(
        {JournalEventType.EFFECT_STARTED, JournalEventType.EFFECT_FAILED}
    ),
    JournalEventType.EFFECT_STARTED: frozenset(
        {JournalEventType.EFFECT_OBSERVED, JournalEventType.EFFECT_FAILED}
    ),
    JournalEventType.EFFECT_OBSERVED: frozenset(
        {JournalEventType.EFFECT_ACCEPTED, JournalEventType.EFFECT_FAILED}
    ),
    JournalEventType.EFFECT_ACCEPTED: frozenset(
        {JournalEventType.STATE_COMMITTED, JournalEventType.EFFECT_FAILED}
    ),
    JournalEventType.EFFECT_FAILED: frozenset(
        {JournalEventType.EFFECT_PREPARED}
    ),
    JournalEventType.STATE_COMMITTED: frozenset(),
}


def validate_effect_transition(
    previous: JournalEventType | None,
    current: JournalEventType,
    *,
    retry_proven_absent: bool = False,
    retry_idempotent: bool = False,
) -> None:
    """Reject impossible transitions and unsafe retry transitions."""

    allowed = EFFECT_TRANSITIONS.get(previous, frozenset())
    if current not in allowed:
        raise Quarantine("EFFECT_JOURNAL_TRANSITION_CONFLICT")
    if (
        previous is JournalEventType.EFFECT_FAILED
        and current is JournalEventType.EFFECT_PREPARED
        and not (retry_proven_absent and retry_idempotent)
    ):
        raise Quarantine("EFFECT_JOURNAL_UNSAFE_RETRY_CONFLICT")


class RecoveryDecision(StrEnum):
    RESUME_AFTER_OBSERVATION = "RESUME_AFTER_OBSERVATION"
    RETRY_IDEMPOTENT_EXACT_OPERATION = "RETRY_IDEMPOTENT_EXACT_OPERATION"
    HOLD_NON_IDEMPOTENT = "HOLD_NON_IDEMPOTENT"
    QUARANTINE_UNKNOWN_EFFECT = "QUARANTINE_UNKNOWN_EFFECT"
    RESUME_ACCEPTANCE = "RESUME_ACCEPTANCE"
    RESUME_COMMIT = "RESUME_COMMIT"
    RETRY_PRE_EFFECT_WITH_FRESH_AUTHORIZATION = (
        "RETRY_PRE_EFFECT_WITH_FRESH_AUTHORIZATION"
    )
    REPLAY_COMMITTED = "REPLAY_COMMITTED"
    QUARANTINE_POST_EFFECT_CAS_CONFLICT = (
        "QUARANTINE_POST_EFFECT_CAS_CONFLICT"
    )


@dataclass(frozen=True, slots=True)
class StartedEffectRecord:
    operation_id: str
    effect_contract_ref: str
    prepared: PreparedEffect
    started_event_ref: str
    attempt_no: int


@dataclass(frozen=True, slots=True)
class RecoveryResult:
    state: str
    operation_id: str
    decision: RecoveryDecision
    reason: str | None = None
    observation_ref: str | None = None
    retry_allowed: bool = False

    @classmethod
    def resume_after_observation(
        cls,
        operation_id: str,
        observation: EffectObservation,
    ) -> "RecoveryResult":
        return cls(
            state="RESUME",
            operation_id=operation_id,
            decision=RecoveryDecision.RESUME_AFTER_OBSERVATION,
            observation_ref=observation.observation_ref,
        )

    @classmethod
    def retry_idempotent(cls, operation_id: str) -> "RecoveryResult":
        return cls(
            state="RETRY",
            operation_id=operation_id,
            decision=RecoveryDecision.RETRY_IDEMPOTENT_EXACT_OPERATION,
            reason="PROVEN_ABSENT_REAUTHORIZE_AND_RECHECK_BASE",
            retry_allowed=True,
        )

    @classmethod
    def hold_non_idempotent(cls, operation_id: str) -> "RecoveryResult":
        return cls(
            state="HOLD",
            operation_id=operation_id,
            decision=RecoveryDecision.HOLD_NON_IDEMPOTENT,
            reason="HOLD_NON_IDEMPOTENT_RETRY_FORBIDDEN",
        )

    @classmethod
    def quarantine_unknown(
        cls,
        operation_id: str,
        reason: str = "QUARANTINE_EFFECT_STATE_UNKNOWN_OR_PARTIAL",
    ) -> "RecoveryResult":
        return cls(
            state="QUARANTINED",
            operation_id=operation_id,
            decision=RecoveryDecision.QUARANTINE_UNKNOWN_EFFECT,
            reason=reason,
        )


class RecoveryJournal(Protocol):
    def require_started_without_observed(
        self, operation_id: str
    ) -> StartedEffectRecord: ...

    def append_sync(
        self,
        event_type: JournalEventType,
        payload: Mapping[str, object],
    ) -> str | None: ...


class EffectContractLoader(Protocol):
    def load(self, ref: str) -> EffectContract: ...


def _require_evidence(observation: EffectObservation) -> None:
    observation.require_receiver_evidence()
    try:
        validate_sha256_ref(observation.observation_ref)
        validate_sha256_ref(observation.evidence_ref)
        if observation.actual_hash is not None:
            validate_sha256_hex(observation.actual_hash)
    except ValueError as exc:
        raise Quarantine("RECOVERY_RECEIVER_EVIDENCE_CONFLICT") from exc
    if (
        observation.effect_state is EffectState.COMPLETE
        and observation.actual_hash is None
    ):
        raise Quarantine("RECOVERY_COMPLETE_HASH_MISSING")
    if (
        observation.effect_state is EffectState.ABSENT
        and observation.actual_hash is not None
    ):
        raise Quarantine("RECOVERY_ABSENT_HASH_CONFLICT")


class RecoveryEngine:
    """Re-observe first; never infer absence from a crash or exception."""

    def __init__(
        self,
        journal: RecoveryJournal,
        contract_loader: EffectContractLoader,
        adapters: Mapping[str, ReceiverAdapter] | None = None,
        handlers: Mapping[str, EffectHandler] | None = None,
    ) -> None:
        self._journal = journal
        self._contract_loader = contract_loader
        self._adapters = self._freeze_registry(
            ADAPTERS if adapters is None else adapters,
            reference_attribute="adapter_ref",
            method_names=("prepare", "observe"),
        )
        self._handlers = self._freeze_registry(
            HANDLERS if handlers is None else handlers,
            reference_attribute="handler_ref",
            method_names=("apply",),
        )

    @staticmethod
    def _freeze_registry(
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

    def recover_started_without_observed(
        self, operation_id: str
    ) -> RecoveryResult:
        started = self._journal.require_started_without_observed(operation_id)
        if started.operation_id != operation_id:
            raise Quarantine("RECOVERY_OPERATION_COORDINATE_CONFLICT")
        contract = self._contract_loader.load(started.effect_contract_ref)
        if contract.body.operation_id != operation_id:
            raise Quarantine("RECOVERY_CONTRACT_OPERATION_CONFLICT")
        if (
            started.prepared.target_coordinate_ref
            != contract.body.target_coordinate_ref
            or started.prepared.idempotency_key
            != contract.body.idempotency_key
        ):
            raise Quarantine("RECOVERY_PREPARED_EFFECT_CONFLICT")

        adapter = self._resolve_adapter(contract.body.receiver_adapter_ref)
        handler = self._resolve_handler(contract.body.effect_handler_ref)

        # The first receiver action after a STARTED-without-OBSERVED tail is
        # always observation.  An apply call is deliberately unavailable here.
        try:
            observation = adapter.observe(
                ObservationContext(
                    contract=contract,
                    prepared=started.prepared,
                    started_event_ref=started.started_event_ref,
                )
            )
            _require_evidence(observation)
        except BaseException as error:
            self._journal.append_sync(
                JournalEventType.EFFECT_FAILED,
                {
                    "operation_id": operation_id,
                    "attempt_no": started.attempt_no,
                    "phase": "RECOVERY_REOBSERVE",
                    "effect_state": EffectState.UNKNOWN,
                    "retry_disposition": "QUARANTINE_NO_REAPPLY",
                    "error_type": type(error).__name__,
                },
            )
            return RecoveryResult.quarantine_unknown(
                operation_id,
                "QUARANTINE_RECEIVER_REOBSERVATION_FAILED",
            )

        if observation.effect_state is EffectState.COMPLETE:
            self._journal.append_sync(
                JournalEventType.EFFECT_OBSERVED,
                {
                    "operation_id": operation_id,
                    "attempt_no": started.attempt_no,
                    "observation_ref": observation.observation_ref,
                    "evidence_ref": observation.evidence_ref,
                    "actual_hash": observation.actual_hash,
                    "synthetic": True,
                },
            )
            return RecoveryResult.resume_after_observation(
                operation_id, observation
            )

        if observation.effect_state is EffectState.ABSENT:
            both_idempotent = (
                handler.idempotency is IdempotencyClass.IDEMPOTENT
                and contract.body.idempotency is IdempotencyClass.IDEMPOTENT
            )
            if both_idempotent:
                self._journal.append_sync(
                    JournalEventType.EFFECT_FAILED,
                    {
                        "operation_id": operation_id,
                        "attempt_no": started.attempt_no,
                        "phase": "RECOVERY_REOBSERVE",
                        "effect_state": EffectState.PROVEN_ABSENT,
                        "observation_ref": observation.observation_ref,
                        "retry_disposition": (
                            "RETRY_IDEMPOTENT_EXACT_OPERATION"
                        ),
                    },
                )
                return RecoveryResult.retry_idempotent(operation_id)

            self._journal.append_sync(
                JournalEventType.EFFECT_FAILED,
                {
                    "operation_id": operation_id,
                    "attempt_no": started.attempt_no,
                    "phase": "RECOVERY_REOBSERVE",
                    "effect_state": EffectState.PROVEN_ABSENT,
                    "observation_ref": observation.observation_ref,
                    "retry_disposition": "NO_AUTOMATIC_RETRY",
                },
            )
            return RecoveryResult.hold_non_idempotent(operation_id)

        self._journal.append_sync(
            JournalEventType.EFFECT_FAILED,
            {
                "operation_id": operation_id,
                "attempt_no": started.attempt_no,
                "phase": "RECOVERY_REOBSERVE",
                "effect_state": observation.effect_state,
                "observation_ref": observation.observation_ref,
                "retry_disposition": "QUARANTINE_NO_REAPPLY",
            },
        )
        return RecoveryResult.quarantine_unknown(operation_id)


def recovery_decision_for_tail(
    operation_id: str,
    tail: JournalEventType,
) -> RecoveryResult:
    if tail is JournalEventType.EFFECT_PREPARED:
        return RecoveryResult(
            "RETRY",
            operation_id,
            RecoveryDecision.RETRY_PRE_EFFECT_WITH_FRESH_AUTHORIZATION,
            reason="REQUIRE_FRESH_GATE_AND_BASE_RECHECK",
            retry_allowed=True,
        )
    if tail is JournalEventType.EFFECT_OBSERVED:
        return RecoveryResult(
            "RESUME",
            operation_id,
            RecoveryDecision.RESUME_ACCEPTANCE,
        )
    if tail is JournalEventType.EFFECT_ACCEPTED:
        return RecoveryResult(
            "RESUME",
            operation_id,
            RecoveryDecision.RESUME_COMMIT,
        )
    if tail is JournalEventType.STATE_COMMITTED:
        return RecoveryResult(
            "REPLAY",
            operation_id,
            RecoveryDecision.REPLAY_COMMITTED,
        )
    raise Hold("HOLD_RECOVERY_TAIL_REQUIRES_REOBSERVATION")


def post_effect_cas_conflict(
    operation_id: str,
    journal: RecoveryJournal | None = None,
) -> RecoveryResult:
    """External effects cannot be rolled back by SQLite; never reapply."""

    if journal is not None:
        journal.append_sync(
            JournalEventType.EFFECT_FAILED,
            {
                "operation_id": operation_id,
                "phase": "POST_EFFECT_CAS",
                "effect_state": EffectState.PROVEN_COMPLETE,
                "retry_disposition": "QUARANTINE_NO_REAPPLY",
            },
        )
    return RecoveryResult(
        state="QUARANTINED",
        operation_id=operation_id,
        decision=RecoveryDecision.QUARANTINE_POST_EFFECT_CAS_CONFLICT,
        reason="QUARANTINE_POST_EFFECT_CAS_CONFLICT",
        retry_allowed=False,
    )
