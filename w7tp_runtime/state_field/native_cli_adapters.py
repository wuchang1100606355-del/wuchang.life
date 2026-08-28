"""Pinned CLI-to-native-port adapters for the real-E2E binding candidate.

The taiji01 implementations are deterministic command-line programs, not
direct implementations of the State Field Protocols.  This module provides a
thin, fail-closed boundary around a *bounded* runner.  It never imports source
artifacts dynamically, constructs authority, runs a shell, or treats policy as
D8 authorization.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Literal, Mapping, Protocol

from .canonical import (
    canonical_hash,
    canonical_json_bytes,
    canonical_json_loads,
    sha256_hex,
    sha256_ref,
    validate_sha256_hex,
    validate_sha256_ref,
)
from .models import (
    DelegationRequest,
    EffectGateRequest,
    EvidenceLifecycleRequest,
    FlowRequest,
    Hold,
    IngressRepresentationRequest,
    NativeProof,
    Quarantine,
    VerifiedEffectPermit,
    request_hash,
)
from .native_ports import (
    CAP_DELEGATION,
    CAP_EFFECT_GATE,
    CAP_EVIDENCE_LIFECYCLE,
    CAP_EXTERNAL_GATEWAY,
    CAP_INFORMATION_FLOW,
    build_native_proof,
    seal_effect_permit_proof,
)
from .object_packet_store import (
    ObjectPacketStore,
    ObjectStoreConflict,
    ObjectStoreHold,
)


SOURCE_NODE = "taiji01"
SOURCE_REPOSITORY = "https://github.com/wuchang1100606355-del/wuchang.life.git"
SOURCE_BRANCH = "design/wish-tree-adi-thaw-launch-20260703-185047"
SOURCE_COMMIT = "d80c71cbae80b2405d6ce75e0b43dcbbaf676263"
SOURCE_TREE = "5fba5ddce199e29e40c32c50850928720eeeb26e"
CANDIDATE_VERSION = "0.1.0-candidate"
CANDIDATE_VERSION_SOURCE = "NEW_BINDING_CANDIDATE"

Compatibility = Literal[
    "MATCH", "EXTENDABLE", "STALE_OR_INCOMPATIBLE", "UNKNOWN"
]
VerificationState = Literal["VERIFIED", "HOLD", "UNKNOWN", "CONFLICT"]
RunnerState = Literal["COMPLETED", "TIMEOUT", "FAILED"]


@dataclass(frozen=True, slots=True)
class ArtifactPin:
    capability_id: str
    implementation_ref: str
    implementation_sha256: str
    adapter_ref: str
    adapter_class_name: str
    protocol_id: str
    input_schema: str
    output_schema: str
    compatibility: Compatibility = "EXTENDABLE"

    def __post_init__(self) -> None:
        validate_sha256_hex(self.implementation_sha256)
        if self.compatibility != "EXTENDABLE":
            raise Quarantine("NATIVE_CLI_COMPATIBILITY_CONFLICT")
        for value in (
            self.capability_id,
            self.implementation_ref,
            self.adapter_ref,
            self.adapter_class_name,
            self.protocol_id,
            self.input_schema,
            self.output_schema,
        ):
            if not isinstance(value, str) or not value:
                raise Quarantine("NATIVE_CLI_ARTIFACT_PIN_CONFLICT")

    @property
    def artifact_coordinate(self) -> str:
        return (
            f"git+{SOURCE_REPOSITORY}@{SOURCE_COMMIT}"
            f"#{self.implementation_ref}"
        )

    @property
    def raw_implementation_ref(self) -> str:
        return (
            "https://raw.githubusercontent.com/"
            "wuchang1100606355-del/wuchang.life/"
            f"{SOURCE_COMMIT}/{self.implementation_ref}"
        )


ARTIFACT_PINS: Mapping[str, ArtifactPin] = MappingProxyType(
    {
        CAP_EXTERNAL_GATEWAY: ArtifactPin(
            CAP_EXTERNAL_GATEWAY,
            "capabilities/w7tp-external-capability-gateway/scripts/"
            "build_gateway_contract.py",
            "a6c1cc1e0cc5ab82fbc8d2f79f185329d6e3c9c5ee33235c5d63b61b49011e24",
            "w7tp.state-field.external-gateway.cli-adapter.v1",
            "ExternalGatewayCliAdapter",
            "W7TP_EXTERNAL_CAPABILITY_GATEWAY_PORT_V1",
            "IngressRepresentationRequest",
            "NativeProof",
        ),
        CAP_EFFECT_GATE: ArtifactPin(
            CAP_EFFECT_GATE,
            "capabilities/w7tp-deterministic-effect-gate/scripts/effect_gate.py",
            "1f2f190ab2f7bbd796c4d04f663f1f095afc6c341d8d99fa16d913dc2b884fd8",
            "w7tp.state-field.effect-gate.cli-adapter.v1",
            "DeterministicEffectGateCliAdapter",
            "W7TP_DETERMINISTIC_EFFECT_GATE_PORT_V1",
            "EffectGateRequest+ExactEffectDecisionEvidence",
            "VerifiedEffectPermit",
        ),
        CAP_DELEGATION: ArtifactPin(
            CAP_DELEGATION,
            "capabilities/w7tp-bounded-delegation-chain/scripts/"
            "validate_delegation_chain.py",
            "4cd4adf43dfea76420a3d78306fa71b0fe606a1d3a2949bcde9432f428d2f446",
            "w7tp.state-field.delegation.cli-adapter.v1",
            "BoundedDelegationCliAdapter",
            "W7TP_BOUNDED_DELEGATION_CHAIN_PORT_V1",
            "DelegationRequest+ExactDelegationEvidence",
            "NativeProof",
        ),
        CAP_INFORMATION_FLOW: ArtifactPin(
            CAP_INFORMATION_FLOW,
            "capabilities/w7tp-stateful-information-flow/scripts/"
            "apply_information_flow.py",
            "ca7bfd7c8c716dbcd8d6aeb3acf62f31c8a8628bc00aee0ddb146cf3403c7225",
            "w7tp.state-field.information-flow.cli-adapter.v1",
            "StatefulInformationFlowCliAdapter",
            "W7TP_STATEFUL_INFORMATION_FLOW_PORT_V1",
            "FlowRequest+ExactFlowPolicyEvidence",
            "NativeProof",
        ),
        CAP_EVIDENCE_LIFECYCLE: ArtifactPin(
            CAP_EVIDENCE_LIFECYCLE,
            "capabilities/w7tp-execution-evidence-lifecycle/scripts/"
            "build_execution_receipt.py",
            "caa740d9e5a6d2888739e1da13085b71bbfebf6b50e6ff39d5c47a2cd45928f0",
            "w7tp.state-field.evidence-lifecycle.cli-adapter.v1",
            "ExecutionEvidenceLifecycleCliAdapter",
            "W7TP_EXECUTION_EVIDENCE_LIFECYCLE_PORT_V1",
            "EvidenceLifecycleRequest+ExactLifecycleEvidence",
            "NativeProof",
        ),
    }
)


@dataclass(frozen=True, slots=True)
class BoundedCliInvocation:
    schema_id: Literal["W7TP_BOUNDED_NATIVE_CLI_INVOCATION_V1"]
    capability_id: str
    artifact_coordinate: str
    expected_artifact_sha256: str
    input_ref: str
    input_bytes: bytes
    output_file_required: bool
    timeout_ms: int
    external_effect_allowed: Literal[False] = False


@dataclass(frozen=True, slots=True)
class BoundedCliResult:
    state: RunnerState
    exit_code: int | None
    stdout_lines: tuple[str, ...]
    output_bytes: bytes | None
    observed_artifact_sha256: str
    evidence_ref: str
    runner_ref: str
    external_effect_observed: bool = False


class BoundedNativeCliRunnerPort(Protocol):
    """Run one pinned artifact without shell text or caller-controlled argv."""

    def invoke(self, invocation: BoundedCliInvocation) -> BoundedCliResult: ...


@dataclass(frozen=True, slots=True)
class ExactEffectDecisionEvidence:
    request_hash: str
    effect_class: str
    exact_effect_ref: str
    target_coordinate_ref: str
    policy_ref: str
    d8_authorization_ref: str
    d8_packet_ref: str
    authority_ref: str
    authorization_ref: str
    policy_allowed: bool
    exact_d8_authorized: bool
    valid_until: datetime
    evidence_ref: str
    verification_state: VerificationState


@dataclass(frozen=True, slots=True)
class ExactDelegationEvidence:
    request_hash: str
    delegation_chain_ref: str
    authenticity_proven: bool
    evidence_ref: str
    verification_state: VerificationState


@dataclass(frozen=True, slots=True)
class ExactFlowPolicyEvidence:
    request_hash: str
    policy_ref: str
    label_rank: Mapping[str, int]
    current_labels: tuple[str, ...]
    incoming_labels: tuple[str, ...]
    destination_max_label: str
    declassification_authorized: bool
    declassified_output_labels: tuple[str, ...]
    redaction_available: bool
    redaction_output_labels: tuple[str, ...]
    evidence_ref: str
    verification_state: VerificationState


@dataclass(frozen=True, slots=True)
class ExactLifecycleEvidence:
    request_hash: str
    target_coordinate_ref: str
    started_at: str
    ended_at: str
    authority_ref: str
    previous_receipt_hash: str
    artifact_hashes: tuple[str, ...]
    evidence_ref: str
    verification_state: VerificationState


class ExactNativeAdapterEvidencePort(Protocol):
    """Supply already verified auxiliary packets; it cannot create authority."""

    def effect_decision(
        self, request: EffectGateRequest
    ) -> ExactEffectDecisionEvidence: ...

    def delegation(
        self, request: DelegationRequest
    ) -> ExactDelegationEvidence: ...

    def flow(self, request: FlowRequest) -> ExactFlowPolicyEvidence: ...

    def lifecycle(
        self, request: EvidenceLifecycleRequest
    ) -> ExactLifecycleEvidence: ...


class AdapterHold(Hold):
    """A deterministic no-effect HOLD with a sealed evidence coordinate."""

    def __init__(self, code: str, evidence_ref: str) -> None:
        self.evidence_ref = evidence_ref
        super().__init__(code, no_effect=True)


def _require_request_type(request: object, expected: type[object]) -> None:
    if not isinstance(request, expected):
        raise Hold("HOLD_NATIVE_ADAPTER_REQUEST_TYPE", no_effect=True)


def _strict_stdout(
    lines: tuple[str, ...],
    *,
    required: frozenset[str],
    allowed: frozenset[str],
    evidence_ref: str,
    allow_empty: frozenset[str] = frozenset(),
) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in lines:
        if not isinstance(line, str) or not line or "=" not in line:
            raise AdapterHold("HOLD_NATIVE_ADAPTER_MALFORMED_OUTPUT", evidence_ref)
        key, value = line.split("=", 1)
        if (
            not key
            or (not value and key not in allow_empty)
            or key in values
            or key not in allowed
        ):
            raise AdapterHold("HOLD_NATIVE_ADAPTER_MALFORMED_OUTPUT", evidence_ref)
        values[key] = value
    if not required.issubset(values):
        raise AdapterHold("HOLD_NATIVE_ADAPTER_MALFORMED_OUTPUT", evidence_ref)
    return values


class _PinnedCliAdapter:
    timeout_ms = 5_000

    def __init__(
        self,
        *,
        pin: ArtifactPin,
        runner: BoundedNativeCliRunnerPort,
        objects: ObjectPacketStore,
        binding_ref: str,
        manifest_ref: str,
    ) -> None:
        validate_sha256_ref(binding_ref)
        validate_sha256_ref(manifest_ref)
        self.pin = pin
        self._runner = runner
        self._objects = objects
        self.binding_ref = binding_ref
        self.manifest_ref = manifest_ref

    def _seal_local_failure(
        self, stage: str, error_type: str, input_ref: str
    ) -> str:
        raw = canonical_json_bytes(
            {
                "schema_id": "W7TP_NATIVE_ADAPTER_FAILURE_EVIDENCE_V1",
                "adapter_ref": self.pin.adapter_ref,
                "artifact_sha256": self.pin.implementation_sha256,
                "capability_id": self.pin.capability_id,
                "error_type": error_type,
                "input_ref": input_ref,
                "stage": stage,
            }
        )
        ref = sha256_ref(raw)
        try:
            self._objects.put_exact(ref, raw)
            if self._objects.get_exact(ref) != raw:
                raise Quarantine("NATIVE_ADAPTER_FAILURE_EVIDENCE_CONFLICT")
        except ObjectStoreHold as error:
            raise Hold(
                "HOLD_NATIVE_ADAPTER_FAILURE_EVIDENCE_UNAVAILABLE",
                no_effect=True,
            ) from error
        except ObjectStoreConflict as error:
            raise Quarantine("NATIVE_ADAPTER_FAILURE_EVIDENCE_CONFLICT") from error
        return ref

    def _require_stored_evidence(self, evidence_ref: str) -> None:
        try:
            validate_sha256_ref(evidence_ref)
            raw = self._objects.get_exact(evidence_ref)
        except (ValueError, ObjectStoreHold) as error:
            raise Hold(
                "HOLD_NATIVE_ADAPTER_EVIDENCE_UNAVAILABLE", no_effect=True
            ) from error
        except ObjectStoreConflict as error:
            raise Quarantine("NATIVE_ADAPTER_EVIDENCE_CONFLICT") from error
        if sha256_ref(raw) != evidence_ref:
            raise Quarantine("NATIVE_ADAPTER_EVIDENCE_CONFLICT")

    def _require_verified_state(
        self, state: VerificationState, evidence_ref: str
    ) -> None:
        self._require_stored_evidence(evidence_ref)
        if state in ("UNKNOWN", "HOLD"):
            raise AdapterHold("HOLD_NATIVE_ADAPTER_EVIDENCE_UNVERIFIED", evidence_ref)
        if state == "CONFLICT":
            raise Quarantine("NATIVE_ADAPTER_EVIDENCE_CONFLICT")
        if state != "VERIFIED":
            raise AdapterHold("HOLD_NATIVE_ADAPTER_EVIDENCE_UNVERIFIED", evidence_ref)

    def _invoke(
        self, input_payload: Mapping[str, object], *, output_required: bool
    ) -> BoundedCliResult:
        raw = canonical_json_bytes(input_payload)
        input_ref = sha256_ref(raw)
        invocation = BoundedCliInvocation(
            schema_id="W7TP_BOUNDED_NATIVE_CLI_INVOCATION_V1",
            capability_id=self.pin.capability_id,
            artifact_coordinate=self.pin.artifact_coordinate,
            expected_artifact_sha256=self.pin.implementation_sha256,
            input_ref=input_ref,
            input_bytes=raw,
            output_file_required=output_required,
            timeout_ms=self.timeout_ms,
        )
        try:
            result = self._runner.invoke(invocation)
        except Exception as error:
            evidence_ref = self._seal_local_failure(
                "RUNNER_EXCEPTION", type(error).__name__, input_ref
            )
            raise AdapterHold("HOLD_NATIVE_ADAPTER_RUNNER_FAILURE", evidence_ref) from error
        if not isinstance(result, BoundedCliResult):
            evidence_ref = self._seal_local_failure(
                "RUNNER_RESULT", type(result).__name__, input_ref
            )
            raise AdapterHold("HOLD_NATIVE_ADAPTER_RUNNER_RESULT", evidence_ref)
        self._require_stored_evidence(result.evidence_ref)
        if result.observed_artifact_sha256 != self.pin.implementation_sha256:
            raise Quarantine("NATIVE_ADAPTER_ARTIFACT_HASH_CONFLICT")
        if result.external_effect_observed:
            raise Quarantine("NATIVE_ADAPTER_EXTERNAL_EFFECT_CONFLICT")
        if result.state == "TIMEOUT":
            raise AdapterHold("HOLD_NATIVE_ADAPTER_TIMEOUT", result.evidence_ref)
        if result.state == "FAILED":
            raise AdapterHold("HOLD_NATIVE_ADAPTER_IMPLEMENTATION_FAILURE", result.evidence_ref)
        if result.state != "COMPLETED" or result.exit_code != 0:
            raise AdapterHold("HOLD_NATIVE_ADAPTER_UNKNOWN_RESULT", result.evidence_ref)
        if output_required != (result.output_bytes is not None):
            raise AdapterHold("HOLD_NATIVE_ADAPTER_MALFORMED_OUTPUT", result.evidence_ref)
        return result


class ExternalGatewayCliAdapter(_PinnedCliAdapter):
    def verify_ingress(
        self, request: IngressRepresentationRequest
    ) -> NativeProof:
        _require_request_type(request, IngressRepresentationRequest)
        payload: dict[str, object] = {
            "capability_id": self.pin.capability_id,
            "source_ref": request.resource_ref,
            "target_coordinate": request.effect_contract_ref,
            "protocols": [self.pin.protocol_id],
            "input_contract": {
                "manifest_ref": request.manifest_ref,
                "request_hash": request_hash(request),
            },
            "output_contract": {"schema_id": self.pin.output_schema},
            "state_transition": "NONE_VERIFY_ONLY",
            "side_effects": [],
            "failure_modes": ["HOLD", "QUARANTINE"],
            "evidence_requirements": [
                self.binding_ref,
                self.manifest_ref,
                f"sha256:{self.pin.implementation_sha256}",
            ],
        }
        result = self._invoke(payload, output_required=True)
        values = _strict_stdout(
            result.stdout_lines,
            required=frozenset({"STATE", "OUTPUT", "CONTRACT_SHA256"}),
            allowed=frozenset({"STATE", "OUTPUT", "CONTRACT_SHA256"}),
            evidence_ref=result.evidence_ref,
        )
        if values["STATE"] != "PASS_GATEWAY_CONTRACT_BUILT":
            raise AdapterHold("HOLD_NATIVE_ADAPTER_MALFORMED_OUTPUT", result.evidence_ref)
        try:
            output = canonical_json_loads(
                result.output_bytes or b"", require_canonical=False
            )
        except ValueError as error:
            raise AdapterHold(
                "HOLD_NATIVE_ADAPTER_MALFORMED_OUTPUT", result.evidence_ref
            ) from error
        if not isinstance(output, dict):
            raise AdapterHold("HOLD_NATIVE_ADAPTER_MALFORMED_OUTPUT", result.evidence_ref)
        expected = dict(payload)
        expected.update(
            {
                "source_runtime_required": False,
                "source_authority_inherited": False,
                "w7tp_d8_authority_created": False,
                "contract_state": "W7TP_NATIVE_GATEWAY_CANDIDATE",
            }
        )
        expected_hash = canonical_hash(expected)
        expected["contract_sha256"] = expected_hash
        if output != expected or values["CONTRACT_SHA256"] != expected_hash:
            raise AdapterHold("HOLD_NATIVE_ADAPTER_MALFORMED_OUTPUT", result.evidence_ref)
        return build_native_proof(
            self.pin.capability_id, request, self.binding_ref
        )


class DeterministicEffectGateCliAdapter(_PinnedCliAdapter):
    def __init__(
        self, *, evidence: ExactNativeAdapterEvidencePort, **kwargs: object
    ) -> None:
        super().__init__(**kwargs)
        self._evidence = evidence

    def verify_exact_authorization(
        self, request: EffectGateRequest
    ) -> VerifiedEffectPermit:
        _require_request_type(request, EffectGateRequest)
        evidence = self._evidence.effect_decision(request)
        self._require_verified_state(
            evidence.verification_state, evidence.evidence_ref
        )
        exact_coordinates = (
            evidence.request_hash == request_hash(request)
            and evidence.exact_effect_ref == request.effect_contract_ref
            and evidence.target_coordinate_ref == request.target_coordinate_ref
            and evidence.policy_ref == request.policy_ref
            and evidence.d8_authorization_ref == request.d8_authorization_ref
            and evidence.d8_packet_ref == request.d8_packet_ref
            and evidence.authority_ref == request.authority_ref
            and evidence.authorization_ref == request.d8_authorization_ref
        )
        if not exact_coordinates:
            raise Quarantine("NATIVE_EFFECT_EVIDENCE_COORDINATE_CONFLICT")
        if not evidence.policy_allowed:
            raise AdapterHold("HOLD_POLICY_DENIED", evidence.evidence_ref)
        if not evidence.exact_d8_authorized:
            raise AdapterHold(
                "HOLD_EXACT_D8_AUTHORIZATION_MISSING", evidence.evidence_ref
            )
        if evidence.valid_until.tzinfo is None:
            raise Quarantine("NATIVE_EFFECT_EVIDENCE_EXPIRY_CONFLICT")
        if evidence.valid_until <= datetime.now(UTC):
            raise AdapterHold(
                "HOLD_EXACT_D8_AUTHORIZATION_EXPIRED", evidence.evidence_ref
            )
        if evidence.effect_class.upper() in {
            "READ_ONLY",
            "ISOLATED_CANDIDATE",
            "STATIC_ANALYSIS",
        }:
            raise Quarantine("NATIVE_EFFECT_CLASS_D8_BYPASS_CONFLICT")
        payload = {
            "request_id": evidence.request_hash,
            "effect_class": evidence.effect_class,
            "target": evidence.target_coordinate_ref,
            "exact_effect": request.effect_contract_ref,
            "d8_authorization": {
                "status": "VALID",
                "target": evidence.target_coordinate_ref,
                "exact_effect": request.effect_contract_ref,
                "authorization_ref": evidence.authorization_ref,
            },
        }
        result = self._invoke(payload, output_required=False)
        values = _strict_stdout(
            result.stdout_lines,
            required=frozenset(
                {"DECISION", "D8_REQUIRED", "AUTHORIZATION_REF"}
            ),
            allowed=frozenset(
                {"DECISION", "D8_REQUIRED", "AUTHORIZATION_REF"}
            ),
            evidence_ref=result.evidence_ref,
        )
        if (
            values["DECISION"] != "ALLOW_EXECUTE"
            or values["D8_REQUIRED"] != "true"
            or values["AUTHORIZATION_REF"] != evidence.authorization_ref
        ):
            raise AdapterHold("HOLD_NATIVE_ADAPTER_MALFORMED_OUTPUT", result.evidence_ref)
        empty_hash = "0" * 64
        permit = VerifiedEffectPermit(
            policy_allowed=True,
            exact_d8_authorized=True,
            bound_request_hash=request_hash(request),
            native_binding_ref=self.binding_ref,
            proof_ref=f"sha256:{empty_hash}",
            proof_hash=empty_hash,
            valid_until=evidence.valid_until,
        )
        return seal_effect_permit_proof(permit, self._objects)


class BoundedDelegationCliAdapter(_PinnedCliAdapter):
    def __init__(
        self, *, evidence: ExactNativeAdapterEvidencePort, **kwargs: object
    ) -> None:
        super().__init__(**kwargs)
        self._evidence = evidence

    def verify_delegation(self, request: DelegationRequest) -> NativeProof:
        _require_request_type(request, DelegationRequest)
        evidence = self._evidence.delegation(request)
        self._require_verified_state(
            evidence.verification_state, evidence.evidence_ref
        )
        if (
            evidence.request_hash != request_hash(request)
            or evidence.delegation_chain_ref != request.delegation_chain_ref
        ):
            raise Quarantine("NATIVE_DELEGATION_EVIDENCE_COORDINATE_CONFLICT")
        if not evidence.authenticity_proven:
            raise AdapterHold(
                "HOLD_DELEGATION_AUTHENTICITY_UNVERIFIED", evidence.evidence_ref
            )
        try:
            chain_raw = self._objects.get_exact(request.delegation_chain_ref)
            chain = canonical_json_loads(chain_raw)
        except (ObjectStoreHold, ValueError) as error:
            raise AdapterHold(
                "HOLD_DELEGATION_CHAIN_UNAVAILABLE", evidence.evidence_ref
            ) from error
        except ObjectStoreConflict as error:
            raise Quarantine("NATIVE_DELEGATION_CHAIN_CONFLICT") from error
        if not isinstance(chain, dict) or not isinstance(chain.get("grants"), list):
            raise AdapterHold(
                "HOLD_NATIVE_ADAPTER_MALFORMED_REQUEST", evidence.evidence_ref
            )
        result = self._invoke(chain, output_required=False)
        values = _strict_stdout(
            result.stdout_lines,
            required=frozenset({"STATE", "GRANT_COUNT", "AUTHENTICITY_PROVEN"}),
            allowed=frozenset({"STATE", "GRANT_COUNT", "AUTHENTICITY_PROVEN"}),
            evidence_ref=result.evidence_ref,
        )
        if (
            values["STATE"] != "PASS_BOUNDED_DELEGATION_CHAIN"
            or values["GRANT_COUNT"] != str(len(chain["grants"]))
            or values["AUTHENTICITY_PROVEN"] != "false"
        ):
            raise AdapterHold("HOLD_NATIVE_ADAPTER_MALFORMED_OUTPUT", result.evidence_ref)
        return build_native_proof(
            self.pin.capability_id, request, self.binding_ref
        )


class StatefulInformationFlowCliAdapter(_PinnedCliAdapter):
    def __init__(
        self, *, evidence: ExactNativeAdapterEvidencePort, **kwargs: object
    ) -> None:
        super().__init__(**kwargs)
        self._evidence = evidence

    def verify_flow(self, request: FlowRequest) -> NativeProof:
        _require_request_type(request, FlowRequest)
        evidence = self._evidence.flow(request)
        self._require_verified_state(
            evidence.verification_state, evidence.evidence_ref
        )
        if evidence.request_hash != request_hash(request):
            raise Quarantine("NATIVE_FLOW_EVIDENCE_COORDINATE_CONFLICT")
        if not evidence.policy_ref:
            raise AdapterHold("HOLD_FLOW_POLICY_UNAVAILABLE", evidence.evidence_ref)
        rank = dict(evidence.label_rank)
        if not rank or any(
            not isinstance(label, str)
            or not label
            or isinstance(value, bool)
            or not isinstance(value, int)
            for label, value in rank.items()
        ):
            raise AdapterHold("HOLD_FLOW_POLICY_MALFORMED", evidence.evidence_ref)
        combined_labels = tuple(
            sorted(set(evidence.current_labels) | set(evidence.incoming_labels))
        )
        if any(label not in rank for label in combined_labels):
            raise AdapterHold("HOLD_FLOW_POLICY_LABEL_UNKNOWN", evidence.evidence_ref)
        if evidence.destination_max_label not in rank:
            raise AdapterHold("HOLD_FLOW_DESTINATION_LABEL_UNKNOWN", evidence.evidence_ref)
        maximum_rank = max((rank[label] for label in combined_labels), default=0)
        destination_rank = rank[evidence.destination_max_label]
        if maximum_rank <= destination_rank:
            expected_decision = "ALLOW"
            expected_next_labels = combined_labels
        elif evidence.declassification_authorized:
            expected_decision = "ALLOW_WITH_DECLARED_DECLASSIFICATION"
            expected_next_labels = tuple(evidence.declassified_output_labels)
        elif evidence.redaction_available:
            expected_decision = "ALLOW_WITH_REDACTION"
            expected_next_labels = tuple(evidence.redaction_output_labels)
        else:
            raise AdapterHold("HOLD_INFORMATION_FLOW_DENIED", evidence.evidence_ref)
        if (
            len(expected_next_labels) != len(set(expected_next_labels))
            or any(label not in rank for label in expected_next_labels)
            or max((rank[label] for label in expected_next_labels), default=0)
            > destination_rank
        ):
            raise AdapterHold("HOLD_FLOW_POLICY_OUTPUT_INVALID", evidence.evidence_ref)
        canonical_next_labels = ",".join(expected_next_labels)
        payload: dict[str, object] = {
            "request_hash": evidence.request_hash,
            "policy_ref": evidence.policy_ref,
            "label_rank": dict(evidence.label_rank),
            "current_labels": list(evidence.current_labels),
            "incoming_labels": list(evidence.incoming_labels),
            "destination_max_label": evidence.destination_max_label,
            "declassification_authorized": evidence.declassification_authorized,
            "declassified_output_labels": list(
                evidence.declassified_output_labels
            ),
            "redaction_available": evidence.redaction_available,
            "redaction_output_labels": list(evidence.redaction_output_labels),
        }
        result = self._invoke(payload, output_required=False)
        values = _strict_stdout(
            result.stdout_lines,
            required=frozenset({"DECISION", "NEXT_LABELS", "D8_AUTHORITY_CREATED"}),
            allowed=frozenset({"DECISION", "NEXT_LABELS", "D8_AUTHORITY_CREATED"}),
            evidence_ref=result.evidence_ref,
            allow_empty=frozenset({"NEXT_LABELS"}),
        )
        if (
            values["DECISION"] != expected_decision
            or values["NEXT_LABELS"] != canonical_next_labels
        ):
            raise Quarantine("NATIVE_FLOW_OUTPUT_POLICY_CONFLICT")
        if values["D8_AUTHORITY_CREATED"] != "false":
            raise Quarantine("NATIVE_FLOW_AUTHORITY_CREATION_CONFLICT")
        return build_native_proof(
            self.pin.capability_id, request, self.binding_ref
        )


class ExecutionEvidenceLifecycleCliAdapter(_PinnedCliAdapter):
    def __init__(
        self, *, evidence: ExactNativeAdapterEvidencePort, **kwargs: object
    ) -> None:
        super().__init__(**kwargs)
        self._evidence = evidence

    def verify_and_advance(
        self, request: EvidenceLifecycleRequest
    ) -> NativeProof:
        _require_request_type(request, EvidenceLifecycleRequest)
        evidence = self._evidence.lifecycle(request)
        self._require_verified_state(
            evidence.verification_state, evidence.evidence_ref
        )
        if evidence.request_hash != request_hash(request):
            raise Quarantine("NATIVE_LIFECYCLE_EVIDENCE_COORDINATE_CONFLICT")
        for digest in evidence.artifact_hashes:
            validate_sha256_hex(digest)
        validate_sha256_hex(evidence.previous_receipt_hash)
        payload: dict[str, object] = {
            "execution_id": request.operation_id,
            "request_ref": request.effect_contract_ref,
            "target": evidence.target_coordinate_ref,
            "exact_effect": request.effect_contract_ref,
            "started_at": evidence.started_at,
            "ended_at": evidence.ended_at,
            "outcome": "ACCEPTED_CANDIDATE_EVIDENCE",
            "evidence_refs": [
                request.ingress_proof_ref,
                request.delegation_proof_ref,
                request.flow_proof_ref,
                request.gate_proof_ref,
                request.observation_ref,
                request.acceptance_evidence_ref,
            ],
            "artifact_hashes": list(evidence.artifact_hashes),
            "authority_ref": evidence.authority_ref,
            "previous_receipt_hash": evidence.previous_receipt_hash,
            "canonical_changed": False,
        }
        result = self._invoke(payload, output_required=True)
        values = _strict_stdout(
            result.stdout_lines,
            required=frozenset({"STATE", "RECEIPT_SHA256", "OUTPUT"}),
            allowed=frozenset({"STATE", "RECEIPT_SHA256", "OUTPUT"}),
            evidence_ref=result.evidence_ref,
        )
        try:
            output = canonical_json_loads(
                result.output_bytes or b"", require_canonical=False
            )
        except ValueError as error:
            raise AdapterHold(
                "HOLD_NATIVE_ADAPTER_MALFORMED_OUTPUT", result.evidence_ref
            ) from error
        expected = dict(payload)
        expected.update(
            {
                "receipt_state": "W7TP_EXECUTION_EVIDENCE",
                "authority_created": False,
            }
        )
        expected_hash = canonical_hash(expected)
        expected["receipt_sha256"] = expected_hash
        if (
            values["STATE"] != "PASS_EXECUTION_RECEIPT_BUILT"
            or values["RECEIPT_SHA256"] != expected_hash
            or output != expected
        ):
            raise AdapterHold("HOLD_NATIVE_ADAPTER_MALFORMED_OUTPUT", result.evidence_ref)
        return build_native_proof(
            self.pin.capability_id, request, self.binding_ref
        )


ADAPTER_CLASSES: Mapping[str, type[_PinnedCliAdapter]] = MappingProxyType(
    {
        CAP_EXTERNAL_GATEWAY: ExternalGatewayCliAdapter,
        CAP_EFFECT_GATE: DeterministicEffectGateCliAdapter,
        CAP_DELEGATION: BoundedDelegationCliAdapter,
        CAP_INFORMATION_FLOW: StatefulInformationFlowCliAdapter,
        CAP_EVIDENCE_LIFECYCLE: ExecutionEvidenceLifecycleCliAdapter,
    }
)


def build_static_candidate_ports(
    *,
    runner: BoundedNativeCliRunnerPort,
    objects: ObjectPacketStore,
    evidence: ExactNativeAdapterEvidencePort,
    binding_refs: Mapping[str, str],
    manifest_refs: Mapping[str, str],
) -> Mapping[str, _PinnedCliAdapter]:
    """Construct exactly five statically named adapters; no loader is used."""

    if set(binding_refs) != set(ARTIFACT_PINS) or set(manifest_refs) != set(
        ARTIFACT_PINS
    ):
        raise Quarantine("NATIVE_CANDIDATE_STATIC_SET_CONFLICT")
    result: dict[str, _PinnedCliAdapter] = {}
    for capability_id, pin in ARTIFACT_PINS.items():
        common: dict[str, object] = {
            "pin": pin,
            "runner": runner,
            "objects": objects,
            "binding_ref": binding_refs[capability_id],
            "manifest_ref": manifest_refs[capability_id],
        }
        adapter_class = ADAPTER_CLASSES[capability_id]
        if capability_id == CAP_EXTERNAL_GATEWAY:
            adapter = adapter_class(**common)
        else:
            adapter = adapter_class(evidence=evidence, **common)
        result[binding_refs[capability_id]] = adapter
    return MappingProxyType(result)
