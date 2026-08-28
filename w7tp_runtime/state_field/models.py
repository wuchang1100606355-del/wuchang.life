"""Closed candidate-domain models for the W7TP state-field runtime.

These types carry coordinates and evidence.  They do not create authority and
they deliberately contain no dynamic loading or model-continuation hooks.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Literal, Protocol, runtime_checkable

from .canonical import (
    canonical_hash,
    canonical_json_bytes,
    canonical_json_loads,
    sha256_hex,
    sha256_ref,
    validate_sha256_hex,
    validate_sha256_ref,
)


ABSENCE_SCOPE = "MSI_CURRENT_WORKTREE_ONLY"

CANONICAL_MAKER = "FOUNDER"
TOTAL_FIELD_CAN_DEFINE_CANONICAL = False
TOTAL_FIELD_CAN_OVERRIDE_FOUNDER = False
CLOUD_MODEL_AUTHORITY = "NONE"
EXECUTOR_CANNOT_CREATE_AUTHORITY = True

POLICY_ALLOW_IS_NOT_D8_AUTHORIZATION = True
RUNTIME_EFFECT_REQUIRES_EXACT_D8_AUTHORIZATION = True

UNKNOWN_TO_HOLD = True
CONFLICT_TO_QUARANTINE = True
MODEL_CONTINUATION_ALLOWED = False
DYNAMIC_ADAPTER_LOADING_ALLOWED = False
MOCK_ONLY_REAL_E2E_PASS_ALLOWED = False

REQUIRED_NATIVE_CAPABILITIES = frozenset(
    {
        "w7tp-external-capability-gateway",
        "w7tp-deterministic-effect-gate",
        "w7tp-bounded-delegation-chain",
        "w7tp-stateful-information-flow",
        "w7tp-execution-evidence-lifecycle",
    }
)

REQUIRED_BINDING_FIELDS = (
    "node_id",
    "workspace_id",
    "artifact_ref",
    "manifest_ref",
    "artifact_hash",
    "capability_id",
    "version",
    "adapter_ref",
)


class StateFieldError(RuntimeError):
    """Base fail-closed error carrying a stable machine reason."""

    def __init__(self, code: str, *, no_effect: bool = False) -> None:
        if not code:
            raise ValueError("state-field error code must not be empty")
        self.code = code
        self.no_effect = no_effect
        super().__init__(code)


class Hold(StateFieldError):
    """Insufficient verified state; no authority may be inferred."""


class Quarantine(StateFieldError):
    """Conflicting evidence or an unsafe post-effect state."""


class CASConflict(StateFieldError):
    """A state pointer no longer matches its sealed base coordinate."""


class EntryKind(StrEnum):
    FILE = "FILE"
    DIRECTORY = "DIRECTORY"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class BindingState(StrEnum):
    OBSERVED = "OBSERVED"
    CANDIDATE = "CANDIDATE"
    VERIFIED = "VERIFIED"
    HOLD = "HOLD"
    CONFLICT = "CONFLICT"


class IdempotencyClass(StrEnum):
    IDEMPOTENT = "IDEMPOTENT"
    NON_IDEMPOTENT = "NON_IDEMPOTENT"


class EffectState(StrEnum):
    COMPLETE = "COMPLETE"
    ABSENT = "ABSENT"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"
    NOT_STARTED = "NOT_STARTED"
    PROVEN_COMPLETE = "PROVEN_COMPLETE"
    PROVEN_ABSENT = "PROVEN_ABSENT"


class JournalEventType(StrEnum):
    EFFECT_PREPARED = "EFFECT_PREPARED"
    EFFECT_STARTED = "EFFECT_STARTED"
    EFFECT_OBSERVED = "EFFECT_OBSERVED"
    EFFECT_FAILED = "EFFECT_FAILED"
    EFFECT_ACCEPTED = "EFFECT_ACCEPTED"
    STATE_COMMITTED = "STATE_COMMITTED"
    STATE_DRIFT = "STATE_DRIFT"
    RECOVERY_DECISION = "RECOVERY_DECISION"


@dataclass(frozen=True, slots=True)
class ManifestChunk:
    object_id: str
    chunk_ordinal: int
    byte_offset: int
    byte_length: int


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    entry_ordinal: int
    logical_path: str
    entry_kind: EntryKind
    mode: int
    size_bytes: int
    file_sha256: str | None
    chunks: tuple[ManifestChunk, ...] = ()


@dataclass(frozen=True, slots=True)
class WorkspaceObservation:
    workspace_id: str
    logical_path: str
    exists: bool
    entry_kind: EntryKind
    mode: int | None
    size_bytes: int | None
    observed_version_ref: str | None


@dataclass(frozen=True, slots=True)
class ArtifactBinding:
    binding_ref: str
    binding_hash: str
    node_id: str
    workspace_id: str
    artifact_ref: str
    manifest_ref: str
    artifact_hash: str
    capability_id: str
    version: str
    adapter_ref: str
    binding_state: BindingState
    evidence_ref: str
    observed_at: str

    def __post_init__(self) -> None:
        validate_sha256_ref(self.binding_ref)
        validate_sha256_hex(self.binding_hash)
        validate_sha256_hex(self.artifact_hash)
        if not isinstance(self.binding_state, BindingState):
            raise Quarantine("NATIVE_BINDING_STATE_CONFLICT")
        for name in (*REQUIRED_BINDING_FIELDS, "evidence_ref", "observed_at"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise Quarantine(f"NATIVE_BINDING_EMPTY_{name.upper()}")

    def coordinate_body(self) -> dict[str, str]:
        return {
            name: str(getattr(self, name))
            for name in REQUIRED_BINDING_FIELDS
        }

    def sealed_body(self) -> dict[str, str]:
        """Bind verification state and evidence as well as coordinates."""

        return {
            "schema_id": "W7TP_ARTIFACT_BINDING_V1",
            **self.coordinate_body(),
            "binding_state": self.binding_state.value,
            "evidence_ref": self.evidence_ref,
            "observed_at": self.observed_at,
        }


@dataclass(frozen=True, slots=True)
class BindingSet:
    bindings: tuple[ArtifactBinding, ...]

    @property
    def capability_ids(self) -> tuple[str, ...]:
        return tuple(binding.capability_id for binding in self.bindings)

    @property
    def binding_refs(self) -> tuple[str, ...]:
        return tuple(binding.binding_ref for binding in self.bindings)


@dataclass(frozen=True, slots=True)
class CurrentPointer:
    resource_id: str
    version_ref: str | None
    generation: int
    state_ref: str | None = None


@dataclass(frozen=True, slots=True)
class ResourceReady:
    resource_id: str
    resource_ref: str
    manifest_ref: str
    mrs_ref: str


@runtime_checkable
class ObjectStoreLike(Protocol):
    def put_bytes(self, data: bytes) -> str: ...

    def get_bytes(self, ref: str) -> bytes: ...


@dataclass(frozen=True, slots=True)
class EffectContractBody:
    schema_id: Literal["W7TP_EFFECT_CONTRACT_V1"]
    operation_id: str
    target_coordinate_ref: str
    base_version_ref: str | None
    base_generation: int
    receiver_adapter_ref: str
    effect_handler_ref: str
    effect_input_ref: str
    acceptance_contract_ref: str
    idempotency_key: str
    idempotency: IdempotencyClass

    def __post_init__(self) -> None:
        if self.schema_id != "W7TP_EFFECT_CONTRACT_V1":
            raise Quarantine("EFFECT_CONTRACT_SCHEMA_CONFLICT")
        if (
            isinstance(self.base_generation, bool)
            or not isinstance(self.base_generation, int)
            or self.base_generation < 0
        ):
            raise Quarantine("EFFECT_CONTRACT_GENERATION_CONFLICT")
        if not isinstance(self.idempotency, IdempotencyClass):
            raise Quarantine("EFFECT_CONTRACT_IDEMPOTENCY_CONFLICT")
        if self.base_version_ref is not None and (
            not isinstance(self.base_version_ref, str)
            or not self.base_version_ref
        ):
            raise Quarantine("EFFECT_CONTRACT_BASE_VERSION_CONFLICT")
        for name in (
            "operation_id",
            "target_coordinate_ref",
            "receiver_adapter_ref",
            "effect_handler_ref",
            "effect_input_ref",
            "acceptance_contract_ref",
            "idempotency_key",
        ):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise Quarantine(f"EFFECT_CONTRACT_EMPTY_{name.upper()}")


@dataclass(frozen=True, slots=True)
class EffectContract:
    body: EffectContractBody
    effect_contract_hash: str
    effect_contract_ref: str

    def __post_init__(self) -> None:
        validate_sha256_hex(self.effect_contract_hash)
        validate_sha256_ref(self.effect_contract_ref)
        expected_hash = canonical_hash(self.body)
        if (
            self.effect_contract_hash != expected_hash
            or self.effect_contract_ref != f"sha256:{expected_hash}"
        ):
            raise Quarantine("EFFECT_CONTRACT_BODY_HASH_CONFLICT")

    @classmethod
    def seal(
        cls,
        body: EffectContractBody,
        objects: ObjectStoreLike,
    ) -> "EffectContract":
        raw = canonical_json_bytes(asdict(body))
        digest = sha256_hex(raw)
        ref = sha256_ref(raw)
        stored_ref = objects.put_bytes(raw)
        if stored_ref != ref:
            raise Quarantine("EFFECT_CONTRACT_OBJECT_REF_CONFLICT")
        return cls(body=body, effect_contract_hash=digest, effect_contract_ref=ref)

    @classmethod
    def load(
        cls,
        ref: str,
        objects: ObjectStoreLike,
    ) -> "EffectContract":
        try:
            validate_sha256_ref(ref)
        except ValueError as exc:
            raise Quarantine("EFFECT_CONTRACT_REF_INVALID") from exc
        try:
            raw = objects.get_bytes(ref)
        except (KeyError, OSError) as exc:
            raise Hold("HOLD_EFFECT_CONTRACT_UNAVAILABLE", no_effect=True) from exc
        except ValueError as exc:
            reason = getattr(exc, "reason_code", "")
            if isinstance(reason, str) and reason.startswith("HOLD_"):
                raise Hold(
                    "HOLD_EFFECT_CONTRACT_UNAVAILABLE", no_effect=True
                ) from exc
            raise Quarantine("EFFECT_CONTRACT_OBJECT_CONFLICT") from exc
        digest = sha256_hex(raw)
        if ref != f"sha256:{digest}":
            raise Quarantine("EFFECT_CONTRACT_REF_HASH_CONFLICT")
        try:
            payload = canonical_json_loads(raw)
            payload["idempotency"] = IdempotencyClass(payload["idempotency"])
            body = EffectContractBody(**payload)
        except (KeyError, TypeError, ValueError) as exc:
            raise Quarantine("EFFECT_CONTRACT_BODY_CONFLICT") from exc
        return cls(body=body, effect_contract_hash=digest, effect_contract_ref=ref)


@dataclass(frozen=True, slots=True)
class IngressRepresentationRequest:
    resource_ref: str
    manifest_ref: str
    effect_contract_ref: str
    capability_binding_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DelegationRequest:
    ingress_proof_ref: str
    effect_contract_ref: str
    delegation_chain_ref: str


@dataclass(frozen=True, slots=True)
class FlowRequest:
    resource_ref: str
    ingress_proof_ref: str
    delegation_proof_ref: str
    effect_contract_ref: str
    target_coordinate_ref: str


@dataclass(frozen=True, slots=True)
class EffectGateRequest:
    effect_contract_ref: str
    effect_contract_hash: str
    policy_ref: str
    d8_authorization_ref: str
    d8_packet_ref: str
    authority_ref: str
    base_version_ref: str | None
    base_generation: int
    target_coordinate_ref: str
    acceptance_contract_ref: str
    flow_proof_ref: str

    def __post_init__(self) -> None:
        validate_sha256_ref(self.effect_contract_ref)
        validate_sha256_hex(self.effect_contract_hash)
        if self.effect_contract_ref != f"sha256:{self.effect_contract_hash}":
            raise Quarantine("EFFECT_GATE_SUBJECT_HASH_CONFLICT")
        if (
            isinstance(self.base_generation, bool)
            or not isinstance(self.base_generation, int)
            or self.base_generation < 0
        ):
            raise Quarantine("EFFECT_GATE_GENERATION_CONFLICT")


@dataclass(frozen=True, slots=True)
class EvidenceLifecycleRequest:
    operation_id: str
    effect_contract_ref: str
    ingress_proof_ref: str
    delegation_proof_ref: str
    flow_proof_ref: str
    gate_proof_ref: str
    observation_ref: str
    acceptance_evidence_ref: str


@dataclass(frozen=True, slots=True)
class NativeProof:
    capability_id: str
    input_hash: str
    proof_ref: str
    proof_hash: str
    verifier_ref: str

    def __post_init__(self) -> None:
        validate_sha256_hex(self.input_hash)
        validate_sha256_hex(self.proof_hash)


@dataclass(frozen=True, slots=True)
class VerifiedEffectPermit:
    policy_allowed: bool
    exact_d8_authorized: bool
    bound_request_hash: str
    native_binding_ref: str
    proof_ref: str
    proof_hash: str
    valid_until: datetime

    def __post_init__(self) -> None:
        validate_sha256_hex(self.bound_request_hash)
        validate_sha256_ref(self.native_binding_ref)
        validate_sha256_hex(self.proof_hash)
        if self.valid_until.tzinfo is None:
            raise Quarantine("EFFECT_PERMIT_NAIVE_EXPIRY_CONFLICT")


@dataclass(frozen=True, slots=True)
class PreparedEffect:
    effect_contract_ref: str
    receiver_adapter_ref: str
    effect_handler_ref: str
    descriptor_ref: str
    target_coordinate_ref: str
    idempotency_key: str

    def __post_init__(self) -> None:
        validate_sha256_ref(self.effect_contract_ref)
        validate_sha256_ref(self.descriptor_ref)
        for value in (
            self.receiver_adapter_ref,
            self.effect_handler_ref,
            self.target_coordinate_ref,
            self.idempotency_key,
        ):
            if not isinstance(value, str) or not value:
                raise Quarantine("PREPARED_EFFECT_COORDINATE_CONFLICT")


@dataclass(frozen=True, slots=True)
class EffectObservation:
    effect_state: EffectState
    observation_ref: str
    evidence_ref: str
    actual_hash: str | None = None

    def require_receiver_evidence(self) -> None:
        if not self.observation_ref or not self.evidence_ref:
            raise Quarantine("RECEIVER_EVIDENCE_MISSING")
        if self.effect_state not in {
            EffectState.COMPLETE,
            EffectState.ABSENT,
            EffectState.PARTIAL,
            EffectState.UNKNOWN,
        }:
            raise Quarantine("RECEIVER_EFFECT_STATE_CONFLICT")


@dataclass(frozen=True, slots=True)
class AcceptanceResult:
    accepted: bool
    evidence_ref: str
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ApplyOutcome:
    result_ref: str | None = None


@dataclass(frozen=True, slots=True)
class PrepareContext:
    contract: EffectContract
    resource: ResourceReady
    pointer: CurrentPointer


@dataclass(frozen=True, slots=True)
class ObservationContext:
    contract: EffectContract
    prepared: PreparedEffect
    started_event_ref: str | None = None


@dataclass(frozen=True, slots=True)
class ExecuteCommand:
    operation_id: str
    resource_id: str
    mrs_ref: str
    effect_contract_ref: str
    native_binding_refs: tuple[str, ...]
    policy_ref: str
    d8_authorization_ref: str
    d8_packet_ref: str
    authority_ref: str
    delegation_chain_ref: str
    idempotency_key: str
    attempt_no: int = 1


@dataclass(frozen=True, slots=True)
class Receipt:
    receipt_ref: str
    operation_id: str
    effect_contract_ref: str
    result_version_ref: str
    observation_ref: str
    acceptance_evidence_ref: str
    lifecycle_proof_ref: str


@dataclass(frozen=True, slots=True)
class Transition:
    transition_ref: str
    operation_id: str
    from_version_ref: str | None
    to_version_ref: str
    from_generation: int
    to_generation: int
    receipt_ref: str


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    state: Literal["COMPLETED", "HOLD", "QUARANTINED"]
    operation_id: str
    reason: str | None = None
    no_effect: bool = False
    receipt_ref: str | None = None
    transition_ref: str | None = None
    replayed: bool = False

    @classmethod
    def hold(
        cls,
        operation_id: str,
        reason: str,
        *,
        no_effect: bool,
    ) -> "ExecutionResult":
        return cls("HOLD", operation_id, reason=reason, no_effect=no_effect)

    @classmethod
    def quarantine(
        cls,
        operation_id: str,
        reason: str,
    ) -> "ExecutionResult":
        return cls("QUARANTINED", operation_id, reason=reason)

    @classmethod
    def completed(
        cls,
        receipt: Receipt,
        transition: Transition,
        *,
        replayed: bool = False,
    ) -> "ExecutionResult":
        return cls(
            "COMPLETED",
            receipt.operation_id,
            receipt_ref=receipt.receipt_ref,
            transition_ref=transition.transition_ref,
            replayed=replayed,
        )


def request_hash(request: object) -> str:
    """Hash a closed request dataclass using the candidate canonical domain."""

    return canonical_hash(request)


def receipt_body_hash(receipt: Receipt) -> str:
    return canonical_hash(receipt)


def transition_body_hash(transition: Transition) -> str:
    return canonical_hash(transition)
