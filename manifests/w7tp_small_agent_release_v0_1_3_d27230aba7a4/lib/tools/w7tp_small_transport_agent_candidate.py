#!/usr/bin/env python3
"""Deterministic candidate core for a small W7TP transport agent.

The module carries references and reconstruction conditions only.  It contains
no model, asset bytes, network implementation, persistence path, or sovereign
decision maker.  A total-field gateway remains the only source of a D8
decision, and :func:`apply_allow_only_commit` treats that response as an input
to a local safety guard rather than creating a decision.
"""

from __future__ import annotations

from abc import abstractmethod
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
import math
from typing import Any, Literal, Mapping, Protocol, TypeAlias, runtime_checkable


JSONValue: TypeAlias = (
    None
    | bool
    | int
    | float
    | str
    | list["JSONValue"]
    | dict[str, "JSONValue"]
)
AgentStatus: TypeAlias = Literal["CANDIDATE", "HOLD", "BLOCK"]
GatewayDecision: TypeAlias = Literal["ALLOW", "HOLD", "BLOCK", "QUARANTINE"]
ReconstructionMode: TypeAlias = Literal["L1", "L2", "L3"]

_SAFE_EXECUTION_PERMISSIONS = frozenset(
    {
        "RESOLVE_REFERENCE",
        "BUILD_RECONSTRUCTION_REQUEST",
        "REQUEST_EQUIVALENCE_VERIFICATION",
        "SUBMIT_CANDIDATE",
        "AUTHORIZED_RAW_CHANNEL",
    }
)
_REQUIRED_EXECUTION_PERMISSIONS = frozenset(
    {
        "RESOLVE_REFERENCE",
        "BUILD_RECONSTRUCTION_REQUEST",
        "REQUEST_EQUIVALENCE_VERIFICATION",
        "SUBMIT_CANDIDATE",
    }
)
_FORBIDDEN_EXECUTION_PERMISSIONS = frozenset(
    {
        "ADJUDICATE_ALLOW",
        "COMMIT",
        "DB_WRITE",
        "DEPLOY",
        "RESTART",
        "ROUTER_WRITE",
    }
)
_GATEWAY_DECISIONS = frozenset({"ALLOW", "HOLD", "BLOCK", "QUARANTINE"})
_GATEWAY_RECEIPT = object()
GENERATIVE_TRANSPORT_SEMANTICS = (
    "STATE_FIELD_PACKET",
    "REFERENCE",
    "LOOKUP",
    "RECONSTRUCTION_CONDITION",
    "EQUIVALENT_STATE_GENERATION",
    "TOTAL_FIELD_VERIFICATION",
)


class SmallTransportAgentError(ValueError):
    """Raised for a stable, non-sensitive candidate-interface failure."""

    def __init__(self, reason_code: str, detail: str) -> None:
        """Initialize the error without including caller payload data."""
        super().__init__(f"{reason_code}: {detail}")
        self.reason_code = reason_code
        self.detail = detail


def _copy_json(value: Any, *, path: str = "$") -> JSONValue:
    """Validate a JSON-compatible value and return an isolated deep copy."""
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise SmallTransportAgentError(
                "INVALID_JSON_VALUE", f"non-finite number at {path}"
            )
        return value
    if isinstance(value, list):
        return [_copy_json(item, path=f"{path}[{index}]") for index, item in enumerate(value)]
    if isinstance(value, Mapping):
        copied: dict[str, JSONValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise SmallTransportAgentError(
                    "INVALID_JSON_VALUE", f"non-string object key at {path}"
                )
            copied[key] = _copy_json(item, path=f"{path}.{key}")
        return copied
    raise SmallTransportAgentError(
        "INVALID_JSON_VALUE", f"unsupported value type at {path}"
    )


def _require_ref(value: str, field_name: str) -> str:
    """Return a non-empty opaque reference or raise a stable error."""
    if not isinstance(value, str) or not value.strip():
        raise SmallTransportAgentError(
            "INVALID_REFERENCE", f"{field_name} must be a non-empty string"
        )
    return value


def _tuple_of_refs(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    """Normalize a sequence of unique opaque references to an immutable tuple."""
    if isinstance(values, str):
        raise SmallTransportAgentError(
            "INVALID_REFERENCE", f"{field_name} must be a reference sequence"
        )
    normalized = tuple(_require_ref(value, field_name) for value in values)
    if len(set(normalized)) != len(normalized):
        raise SmallTransportAgentError(
            "INVALID_REFERENCE", f"{field_name} must not contain duplicates"
        )
    return normalized


def _mapping_string(value: Mapping[str, JSONValue], field_name: str) -> str:
    """Read a required string without coercing a differently typed value."""
    item = value[field_name]
    if not isinstance(item, str):
        raise SmallTransportAgentError(
            "INVALID_CANDIDATE", f"{field_name} must be a string"
        )
    return _require_ref(item, field_name)


def _mapping_ref_list(
    value: Mapping[str, JSONValue], field_name: str
) -> tuple[str, ...]:
    """Read an optional JSON array consisting only of opaque references."""
    item = value.get(field_name, [])
    if not isinstance(item, list) or any(not isinstance(ref, str) for ref in item):
        raise SmallTransportAgentError(
            "INVALID_CANDIDATE", f"{field_name} must be an array of strings"
        )
    return _tuple_of_refs(tuple(item), field_name)


@dataclass(frozen=True, slots=True)
class AgentVersion:
    """Immutable identity and protocol version tuple for an agent package."""

    agent_ref: str
    version: str
    protocol_version: str

    def __post_init__(self) -> None:
        """Validate the complete version identity."""
        _require_ref(self.agent_ref, "agent_ref")
        _require_ref(self.version, "version")
        _require_ref(self.protocol_version, "protocol_version")


@dataclass(frozen=True, slots=True)
class CapabilityManifest:
    """Declarative allowlist for one candidate agent package."""

    agent_version: AgentVersion
    supported_schema_versions: tuple[str, ...]
    supported_rule_refs: tuple[str, ...]
    supported_reconstructors: tuple[str, ...]
    available_asset_refs: tuple[str, ...]
    observation_domain_ref: str
    privacy_boundary_ref: str
    execution_permissions: tuple[str, ...]

    def __post_init__(self) -> None:
        """Normalize the manifest without retaining caller-owned sequences."""
        if not isinstance(self.agent_version, AgentVersion):
            raise SmallTransportAgentError(
                "INVALID_MANIFEST", "agent_version must be AgentVersion"
            )
        object.__setattr__(
            self,
            "supported_schema_versions",
            _tuple_of_refs(self.supported_schema_versions, "supported_schema_versions"),
        )
        object.__setattr__(
            self,
            "supported_rule_refs",
            _tuple_of_refs(self.supported_rule_refs, "supported_rule_refs"),
        )
        object.__setattr__(
            self,
            "supported_reconstructors",
            _tuple_of_refs(self.supported_reconstructors, "supported_reconstructors"),
        )
        object.__setattr__(
            self,
            "available_asset_refs",
            _tuple_of_refs(self.available_asset_refs, "available_asset_refs"),
        )
        object.__setattr__(
            self,
            "execution_permissions",
            _tuple_of_refs(self.execution_permissions, "execution_permissions"),
        )
        _require_ref(self.observation_domain_ref, "observation_domain_ref")
        _require_ref(self.privacy_boundary_ref, "privacy_boundary_ref")


@dataclass(frozen=True, slots=True)
class TransportCandidate:
    """Reference-only input accepted by the small-agent candidate receiver."""

    candidate_ref: str
    schema_version: str
    protocol_version: str
    required_agent_version: str
    rule_ref: str
    reconstructor_ref: str
    reconstruction_mode: ReconstructionMode
    observation_domain_ref: str
    privacy_boundary_ref: str
    asset_refs: tuple[str, ...] = field(default_factory=tuple)
    lookup_refs: tuple[str, ...] = field(default_factory=tuple)
    reconstruction_condition_refs: tuple[str, ...] = field(default_factory=tuple)
    routing_refs: tuple[str, ...] = field(default_factory=tuple)
    requires_raw_channel: bool = False
    raw_channel_ref: str | None = None

    def __post_init__(self) -> None:
        """Validate references and isolate every caller-provided sequence."""
        for field_name in (
            "candidate_ref",
            "schema_version",
            "protocol_version",
            "required_agent_version",
            "rule_ref",
            "reconstructor_ref",
            "observation_domain_ref",
            "privacy_boundary_ref",
        ):
            _require_ref(getattr(self, field_name), field_name)
        if self.reconstruction_mode not in {"L1", "L2", "L3"}:
            raise SmallTransportAgentError(
                "UNSUPPORTED_RECONSTRUCTOR", "reconstruction_mode must be L1, L2, or L3"
            )
        for field_name in (
            "asset_refs",
            "lookup_refs",
            "reconstruction_condition_refs",
            "routing_refs",
        ):
            object.__setattr__(
                self,
                field_name,
                _tuple_of_refs(getattr(self, field_name), field_name),
            )
        if not isinstance(self.requires_raw_channel, bool):
            raise SmallTransportAgentError(
                "INVALID_CANDIDATE", "requires_raw_channel must be boolean"
            )
        if self.raw_channel_ref is not None:
            _require_ref(self.raw_channel_ref, "raw_channel_ref")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "TransportCandidate":
        """Parse a closed mapping into a candidate without executing content."""
        if not isinstance(value, Mapping):
            raise SmallTransportAgentError(
                "INVALID_CANDIDATE", "candidate must be a mapping"
            )
        allowed = {
            "candidate_ref",
            "schema_version",
            "protocol_version",
            "required_agent_version",
            "rule_ref",
            "reconstructor_ref",
            "reconstruction_mode",
            "observation_domain_ref",
            "privacy_boundary_ref",
            "asset_refs",
            "lookup_refs",
            "reconstruction_condition_refs",
            "routing_refs",
            "requires_raw_channel",
            "raw_channel_ref",
        }
        extra = sorted(set(value) - allowed)
        if extra:
            raise SmallTransportAgentError(
                "BLOCK", "candidate contains fields outside the reference-only contract"
            )
        required = {
            "candidate_ref",
            "schema_version",
            "protocol_version",
            "required_agent_version",
            "rule_ref",
            "reconstructor_ref",
            "reconstruction_mode",
            "observation_domain_ref",
            "privacy_boundary_ref",
        }
        missing = sorted(required - set(value))
        if missing:
            raise SmallTransportAgentError(
                "HOLD", "candidate is missing required reference fields"
            )
        copied = _copy_json(value)
        if not isinstance(copied, dict):
            raise SmallTransportAgentError(
                "INVALID_CANDIDATE", "candidate must be an object"
            )
        mode = _mapping_string(copied, "reconstruction_mode")
        raw_required = copied.get("requires_raw_channel", False)
        if not isinstance(raw_required, bool):
            raise SmallTransportAgentError(
                "INVALID_CANDIDATE", "requires_raw_channel must be boolean"
            )
        raw_ref_value = copied.get("raw_channel_ref")
        if raw_ref_value is not None and not isinstance(raw_ref_value, str):
            raise SmallTransportAgentError(
                "INVALID_CANDIDATE", "raw_channel_ref must be a string or null"
            )
        return cls(
            candidate_ref=_mapping_string(copied, "candidate_ref"),
            schema_version=_mapping_string(copied, "schema_version"),
            protocol_version=_mapping_string(copied, "protocol_version"),
            required_agent_version=_mapping_string(copied, "required_agent_version"),
            rule_ref=_mapping_string(copied, "rule_ref"),
            reconstructor_ref=_mapping_string(copied, "reconstructor_ref"),
            reconstruction_mode=mode,  # type: ignore[arg-type]
            observation_domain_ref=_mapping_string(copied, "observation_domain_ref"),
            privacy_boundary_ref=_mapping_string(copied, "privacy_boundary_ref"),
            asset_refs=_mapping_ref_list(copied, "asset_refs"),
            lookup_refs=_mapping_ref_list(copied, "lookup_refs"),
            reconstruction_condition_refs=_mapping_ref_list(
                copied, "reconstruction_condition_refs"
            ),
            routing_refs=_mapping_ref_list(copied, "routing_refs"),
            requires_raw_channel=raw_required,
            raw_channel_ref=raw_ref_value,
        )


@dataclass(frozen=True, slots=True)
class NegotiatedVersion:
    """Exact version tuple selected without rewriting either peer."""

    agent_version: str
    schema_version: str
    protocol_version: str


@dataclass(frozen=True, slots=True)
class VersionNegotiationResult:
    """Stable result of an exact candidate version negotiation."""

    status: AgentStatus
    reason_code: str
    negotiated: NegotiatedVersion | None


@dataclass(frozen=True, slots=True)
class ReferenceResolution:
    """Stable reference-resolution result containing no resolved asset bytes."""

    status: AgentStatus
    reason_code: str
    reference: str


@dataclass(frozen=True, slots=True)
class ReconstructionRequest:
    """Bounded reconstruction request made entirely of declared references."""

    candidate_ref: str
    rule_ref: str
    reconstructor_ref: str
    reconstruction_mode: ReconstructionMode
    asset_refs: tuple[str, ...]
    lookup_refs: tuple[str, ...]
    reconstruction_condition_refs: tuple[str, ...]
    routing_refs: tuple[str, ...]
    observation_domain_ref: str
    privacy_boundary_ref: str
    raw_channel_ref: str | None
    negotiated_version: NegotiatedVersion

    def __post_init__(self) -> None:
        """Normalize all reference sequences in the public frozen model."""
        for field_name in (
            "candidate_ref",
            "rule_ref",
            "reconstructor_ref",
            "observation_domain_ref",
            "privacy_boundary_ref",
        ):
            _require_ref(getattr(self, field_name), field_name)
        for field_name in (
            "asset_refs",
            "lookup_refs",
            "reconstruction_condition_refs",
            "routing_refs",
        ):
            object.__setattr__(
                self,
                field_name,
                _tuple_of_refs(getattr(self, field_name), field_name),
            )
        if self.raw_channel_ref is not None:
            _require_ref(self.raw_channel_ref, "raw_channel_ref")
        if not isinstance(self.negotiated_version, NegotiatedVersion):
            raise SmallTransportAgentError(
                "INVALID_RECONSTRUCTION_REQUEST",
                "negotiated_version must be NegotiatedVersion",
            )

    def as_dict(self) -> dict[str, JSONValue]:
        """Return an isolated JSON-compatible gateway payload."""
        return {
            "candidate_ref": self.candidate_ref,
            "rule_ref": self.rule_ref,
            "reconstructor_ref": self.reconstructor_ref,
            "reconstruction_mode": self.reconstruction_mode,
            "asset_refs": list(self.asset_refs),
            "lookup_refs": list(self.lookup_refs),
            "reconstruction_condition_refs": list(self.reconstruction_condition_refs),
            "routing_refs": list(self.routing_refs),
            "observation_domain_ref": self.observation_domain_ref,
            "privacy_boundary_ref": self.privacy_boundary_ref,
            "raw_channel_ref": self.raw_channel_ref,
            "negotiated_version": {
                "agent_version": self.negotiated_version.agent_version,
                "schema_version": self.negotiated_version.schema_version,
                "protocol_version": self.negotiated_version.protocol_version,
            },
        }


@dataclass(frozen=True, slots=True)
class EquivalenceVerificationRequest:
    """Request for local verification at the packet-required level."""

    candidate_ref: str
    verification_level: ReconstructionMode
    expected_state_ref: str
    reconstructed_state_ref: str
    verifier_ref: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate and detach every local-equivalence reference."""
        if self.verification_level not in {"L1", "L2", "L3"}:
            raise SmallTransportAgentError(
                "UNSUPPORTED_RECONSTRUCTOR", "verification level is unsupported"
            )
        for field_name in (
            "candidate_ref",
            "expected_state_ref",
            "reconstructed_state_ref",
            "verifier_ref",
        ):
            _require_ref(getattr(self, field_name), field_name)
        object.__setattr__(
            self,
            "evidence_refs",
            _tuple_of_refs(self.evidence_refs, "evidence_refs"),
        )

    def as_dict(self) -> dict[str, JSONValue]:
        """Return a detached representation for the governed gateway."""
        return {
            "candidate_ref": self.candidate_ref,
            "verification_level": self.verification_level,
            "expected_state_ref": self.expected_state_ref,
            "reconstructed_state_ref": self.reconstructed_state_ref,
            "verifier_ref": self.verifier_ref,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class CandidateResponse:
    """Small-agent preparation result; it can never be an ALLOW decision."""

    status: AgentStatus
    reason_code: str
    reconstruction_request: ReconstructionRequest | None = None


@dataclass(frozen=True, slots=True)
class GatewayResponse:
    """Decision evidence received from an injected total-field gateway."""

    final_decision: GatewayDecision
    decision_reason: str
    committed: JSONValue
    commit_applied: bool
    tfid: str | None = None
    total_field_hash: str | None = None
    _receipt_token: InitVar[object | None] = None

    def __post_init__(self, _receipt_token: object | None) -> None:
        """Validate and isolate an externally supplied gateway response."""
        if _receipt_token is not _GATEWAY_RECEIPT:
            raise SmallTransportAgentError(
                "GATEWAY_RESPONSE_PROVENANCE_REQUIRED",
                "response must be returned through submit_to_gateway",
            )
        if self.final_decision not in _GATEWAY_DECISIONS:
            raise SmallTransportAgentError(
                "INVALID_GATEWAY_RESPONSE", "gateway returned an unknown D8 decision"
            )
        _require_ref(self.decision_reason, "decision_reason")
        object.__setattr__(self, "committed", _copy_json(self.committed))
        if not isinstance(self.commit_applied, bool):
            raise SmallTransportAgentError(
                "INVALID_GATEWAY_RESPONSE", "commit_applied must be boolean"
            )
        if self.final_decision != "ALLOW" and self.commit_applied:
            raise SmallTransportAgentError(
                "INVALID_GATEWAY_RESPONSE", "only an ALLOW response may report commit"
            )
        if self.tfid is not None:
            _require_ref(self.tfid, "tfid")
        if self.total_field_hash is not None:
            _require_ref(self.total_field_hash, "total_field_hash")

    @classmethod
    def _from_mapping(cls, value: Mapping[str, Any]) -> "GatewayResponse":
        """Parse a gateway-owned response without manufacturing a decision."""
        if not isinstance(value, Mapping):
            raise SmallTransportAgentError(
                "INVALID_GATEWAY_RESPONSE", "gateway response must be a mapping"
            )
        required = {"final_decision", "decision_reason", "committed", "commit_applied"}
        if required - set(value):
            raise SmallTransportAgentError(
                "INVALID_GATEWAY_RESPONSE", "gateway response is incomplete"
            )
        copied = _copy_json(value)
        if not isinstance(copied, dict):
            raise SmallTransportAgentError(
                "INVALID_GATEWAY_RESPONSE", "gateway response must be an object"
            )
        final_decision = copied["final_decision"]
        decision_reason = copied["decision_reason"]
        commit_applied = copied["commit_applied"]
        if not isinstance(final_decision, str) or not isinstance(decision_reason, str):
            raise SmallTransportAgentError(
                "INVALID_GATEWAY_RESPONSE", "decision fields must be strings"
            )
        if not isinstance(commit_applied, bool):
            raise SmallTransportAgentError(
                "INVALID_GATEWAY_RESPONSE", "commit_applied must be boolean"
            )
        tfid = copied.get("tfid")
        total_field_hash = copied.get("total_field_hash")
        if tfid is not None and not isinstance(tfid, str):
            raise SmallTransportAgentError(
                "INVALID_GATEWAY_RESPONSE", "tfid must be a string or null"
            )
        if total_field_hash is not None and not isinstance(total_field_hash, str):
            raise SmallTransportAgentError(
                "INVALID_GATEWAY_RESPONSE",
                "total_field_hash must be a string or null",
            )
        return cls(
            final_decision=final_decision,  # type: ignore[arg-type]
            decision_reason=decision_reason,
            committed=copied["committed"],
            commit_applied=commit_applied,
            tfid=tfid,
            total_field_hash=total_field_hash,
            _receipt_token=_GATEWAY_RECEIPT,
        )


@dataclass(frozen=True, slots=True)
class CommitGuardResult:
    """Result of applying an injected D8 response to previous/proposed state."""

    committed: JSONValue
    commit_applied: bool
    final_decision: GatewayDecision
    reason_code: str

    def __post_init__(self) -> None:
        """Detach the committed value from caller-owned input."""
        object.__setattr__(self, "committed", _copy_json(self.committed))


@runtime_checkable
class TotalFieldGatewayClient(Protocol):
    """Provider-neutral interface to the single total-field candidate ingress."""

    @abstractmethod
    def receive_candidate(
        self, candidate: Mapping[str, JSONValue], *, source_mode: str
    ) -> GatewayResponse | Mapping[str, Any]:
        """Submit a detached candidate and return gateway-owned decision evidence."""
        raise RuntimeError("PROTOCOL_INTERFACE_ONLY")


class RuleReferenceResolver:
    """Resolve only rule references declared by the capability manifest."""

    @staticmethod
    def resolve(rule_ref: str, manifest: CapabilityManifest) -> ReferenceResolution:
        """Return a candidate resolution or stable unsupported-rule HOLD."""
        _require_ref(rule_ref, "rule_ref")
        if rule_ref not in manifest.supported_rule_refs:
            return ReferenceResolution("HOLD", "UNSUPPORTED_RULE", rule_ref)
        return ReferenceResolution("CANDIDATE", "RULE_REFERENCE_RESOLVED", rule_ref)


class AssetReferenceResolver:
    """Authorize an exact asset reference without loading its material."""

    @staticmethod
    def resolve(asset_ref: str, manifest: CapabilityManifest) -> ReferenceResolution:
        """Return a reference-only resolution or stable missing-asset HOLD."""
        _require_ref(asset_ref, "asset_ref")
        if asset_ref not in manifest.available_asset_refs:
            return ReferenceResolution("HOLD", "MISSING_ASSET", asset_ref)
        return ReferenceResolution("CANDIDATE", "ASSET_REFERENCE_RESOLVED", asset_ref)


class ReconstructorReferenceResolver:
    """Resolve only reconstruction implementations named by the manifest."""

    @staticmethod
    def resolve(
        reconstructor_ref: str, manifest: CapabilityManifest
    ) -> ReferenceResolution:
        """Return a candidate resolution or stable unsupported HOLD."""
        _require_ref(reconstructor_ref, "reconstructor_ref")
        if reconstructor_ref not in manifest.supported_reconstructors:
            return ReferenceResolution(
                "HOLD", "UNSUPPORTED_RECONSTRUCTOR", reconstructor_ref
            )
        return ReferenceResolution(
            "CANDIDATE", "RECONSTRUCTOR_REFERENCE_RESOLVED", reconstructor_ref
        )


class ReconstructionRequestBuilder:
    """Build a bounded reference-only request after all checks succeed."""

    @staticmethod
    def build(
        candidate: TransportCandidate, negotiated: NegotiatedVersion
    ) -> ReconstructionRequest:
        """Build a detached immutable request with no asset material."""
        return ReconstructionRequest(
            candidate_ref=candidate.candidate_ref,
            rule_ref=candidate.rule_ref,
            reconstructor_ref=candidate.reconstructor_ref,
            reconstruction_mode=candidate.reconstruction_mode,
            asset_refs=tuple(candidate.asset_refs),
            lookup_refs=tuple(candidate.lookup_refs),
            reconstruction_condition_refs=tuple(candidate.reconstruction_condition_refs),
            routing_refs=tuple(candidate.routing_refs),
            observation_domain_ref=candidate.observation_domain_ref,
            privacy_boundary_ref=candidate.privacy_boundary_ref,
            raw_channel_ref=candidate.raw_channel_ref,
            negotiated_version=negotiated,
        )


def negotiate_version(
    manifest: CapabilityManifest,
    *,
    schema_version: str,
    protocol_version: str,
    required_agent_version: str,
) -> VersionNegotiationResult:
    """Negotiate an exact compatible tuple without implicit downgrade."""
    _require_ref(schema_version, "schema_version")
    _require_ref(protocol_version, "protocol_version")
    _require_ref(required_agent_version, "required_agent_version")
    compatible = (
        schema_version in manifest.supported_schema_versions
        and protocol_version == manifest.agent_version.protocol_version
        and required_agent_version == manifest.agent_version.version
    )
    if not compatible:
        return VersionNegotiationResult("HOLD", "VERSION_MISMATCH", None)
    return VersionNegotiationResult(
        "CANDIDATE",
        "VERSION_NEGOTIATED",
        NegotiatedVersion(
            agent_version=manifest.agent_version.version,
            schema_version=schema_version,
            protocol_version=protocol_version,
        ),
    )


class CandidateReceiver:
    """Validate and prepare candidate references without adjudicating them."""

    def __init__(self, manifest: CapabilityManifest) -> None:
        """Bind one immutable manifest to the receiver."""
        if not isinstance(manifest, CapabilityManifest):
            raise SmallTransportAgentError(
                "INVALID_MANIFEST", "manifest must be CapabilityManifest"
            )
        self._manifest = manifest

    def receive(
        self, candidate: TransportCandidate | Mapping[str, Any]
    ) -> CandidateResponse:
        """Return CANDIDATE, HOLD, or BLOCK with a stable reason code."""
        try:
            parsed = (
                candidate
                if isinstance(candidate, TransportCandidate)
                else TransportCandidate.from_mapping(candidate)
            )
        except SmallTransportAgentError as error:
            status: AgentStatus = "BLOCK" if error.reason_code == "BLOCK" else "HOLD"
            return CandidateResponse(status, error.reason_code)

        permissions = frozenset(self._manifest.execution_permissions)
        if permissions & _FORBIDDEN_EXECUTION_PERMISSIONS:
            return CandidateResponse("BLOCK", "FORBIDDEN_EXECUTION_PERMISSION")
        if not permissions.issubset(_SAFE_EXECUTION_PERMISSIONS):
            return CandidateResponse("BLOCK", "UNSUPPORTED_EXECUTION_PERMISSION")
        if not _REQUIRED_EXECUTION_PERMISSIONS.issubset(permissions):
            return CandidateResponse("HOLD", "MISSING_EXECUTION_PERMISSION")
        if parsed.observation_domain_ref != self._manifest.observation_domain_ref:
            return CandidateResponse("BLOCK", "OBSERVATION_DOMAIN_MISMATCH")
        if parsed.privacy_boundary_ref != self._manifest.privacy_boundary_ref:
            return CandidateResponse("BLOCK", "PRIVACY_BOUNDARY_MISMATCH")

        negotiation = negotiate_version(
            self._manifest,
            schema_version=parsed.schema_version,
            protocol_version=parsed.protocol_version,
            required_agent_version=parsed.required_agent_version,
        )
        if negotiation.negotiated is None:
            return CandidateResponse(negotiation.status, negotiation.reason_code)

        rule = RuleReferenceResolver.resolve(parsed.rule_ref, self._manifest)
        if rule.status != "CANDIDATE":
            return CandidateResponse(rule.status, rule.reason_code)
        reconstructor = ReconstructorReferenceResolver.resolve(
            parsed.reconstructor_ref, self._manifest
        )
        if reconstructor.status != "CANDIDATE":
            return CandidateResponse(reconstructor.status, reconstructor.reason_code)

        raw_reference_present = parsed.raw_channel_ref is not None
        if parsed.requires_raw_channel and (
            "AUTHORIZED_RAW_CHANNEL" not in permissions or not raw_reference_present
        ):
            return CandidateResponse("HOLD", "RAW_CHANNEL_REQUIRED")
        if not parsed.requires_raw_channel and raw_reference_present:
            return CandidateResponse("BLOCK", "RAW_CHANNEL_NOT_DECLARED")

        for asset_ref in parsed.asset_refs:
            asset = AssetReferenceResolver.resolve(asset_ref, self._manifest)
            if asset.status != "CANDIDATE":
                return CandidateResponse(asset.status, asset.reason_code)

        request = ReconstructionRequestBuilder.build(parsed, negotiation.negotiated)
        return CandidateResponse("CANDIDATE", "CANDIDATE_READY", request)

    def receive_candidate(
        self, candidate: TransportCandidate | Mapping[str, Any]
    ) -> CandidateResponse:
        """Alias that makes the candidate-only responsibility explicit."""
        return self.receive(candidate)


def build_equivalence_verification_request(
    *,
    candidate_ref: str,
    verification_level: ReconstructionMode,
    expected_state_ref: str,
    reconstructed_state_ref: str,
    verifier_ref: str,
    evidence_refs: tuple[str, ...],
) -> EquivalenceVerificationRequest:
    """Build an immutable local-equivalence verification request."""
    if verification_level not in {"L1", "L2", "L3"}:
        raise SmallTransportAgentError(
            "UNSUPPORTED_RECONSTRUCTOR", "verification_level must be L1, L2, or L3"
        )
    for field_name, value in (
        ("candidate_ref", candidate_ref),
        ("expected_state_ref", expected_state_ref),
        ("reconstructed_state_ref", reconstructed_state_ref),
        ("verifier_ref", verifier_ref),
    ):
        _require_ref(value, field_name)
    return EquivalenceVerificationRequest(
        candidate_ref=candidate_ref,
        verification_level=verification_level,
        expected_state_ref=expected_state_ref,
        reconstructed_state_ref=reconstructed_state_ref,
        verifier_ref=verifier_ref,
        evidence_refs=_tuple_of_refs(evidence_refs, "evidence_refs"),
    )


def submit_to_gateway(
    client: TotalFieldGatewayClient,
    reconstruction_request: ReconstructionRequest,
    equivalence_request: EquivalenceVerificationRequest,
    *,
    source_mode: str,
) -> GatewayResponse:
    """Submit candidate evidence and accept, but never invent, a D8 response."""
    if source_mode not in {"TOTAL_FIELD_PULL", "LLM_PUSH"}:
        raise SmallTransportAgentError(
            "INVALID_SOURCE_MODE", "source_mode is outside the gateway contract"
        )
    if reconstruction_request.candidate_ref != equivalence_request.candidate_ref:
        raise SmallTransportAgentError(
            "BLOCK", "reconstruction and equivalence requests reference different candidates"
        )
    outbound: dict[str, JSONValue] = {
        "candidate_ref": reconstruction_request.candidate_ref,
        "reconstruction_request": reconstruction_request.as_dict(),
        "equivalence_verification_request": equivalence_request.as_dict(),
    }
    supplied = client.receive_candidate(deepcopy(outbound), source_mode=source_mode)
    if isinstance(supplied, GatewayResponse):
        return supplied
    return GatewayResponse._from_mapping(supplied)


def apply_allow_only_commit(
    previous: JSONValue,
    proposed: JSONValue,
    gateway_response: GatewayResponse,
) -> CommitGuardResult:
    """Use proposed state only for an ALLOW supplied by the total-field gateway."""
    previous_copy = _copy_json(previous, path="$.previous")
    proposed_copy = _copy_json(proposed, path="$.proposed")
    if not isinstance(gateway_response, GatewayResponse):
        raise SmallTransportAgentError(
            "INVALID_GATEWAY_RESPONSE", "commit guard requires GatewayResponse evidence"
        )
    if gateway_response.final_decision == "ALLOW" and gateway_response.commit_applied:
        return CommitGuardResult(
            committed=proposed_copy,
            commit_applied=True,
            final_decision="ALLOW",
            reason_code="ALLOW_GATEWAY_COMMIT",
        )
    if gateway_response.final_decision == "ALLOW":
        return CommitGuardResult(
            committed=previous_copy,
            commit_applied=False,
            final_decision="ALLOW",
            reason_code="ALLOW_WITHOUT_GATEWAY_COMMIT_PRESERVE_PREVIOUS",
        )
    return CommitGuardResult(
        committed=previous_copy,
        commit_applied=False,
        final_decision=gateway_response.final_decision,
        reason_code=f"{gateway_response.final_decision}_PRESERVE_PREVIOUS",
    )


__all__ = (
    "AgentVersion",
    "AssetReferenceResolver",
    "CandidateReceiver",
    "CandidateResponse",
    "CapabilityManifest",
    "CommitGuardResult",
    "EquivalenceVerificationRequest",
    "GatewayResponse",
    "NegotiatedVersion",
    "ReconstructionRequest",
    "ReconstructionRequestBuilder",
    "ReconstructorReferenceResolver",
    "ReferenceResolution",
    "RuleReferenceResolver",
    "SmallTransportAgentError",
    "TotalFieldGatewayClient",
    "TransportCandidate",
    "VersionNegotiationResult",
    "GENERATIVE_TRANSPORT_SEMANTICS",
    "apply_allow_only_commit",
    "build_equivalence_verification_request",
    "negotiate_version",
    "submit_to_gateway",
)
