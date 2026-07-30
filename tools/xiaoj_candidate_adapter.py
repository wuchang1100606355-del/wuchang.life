#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provider-neutral XiaoJ candidate adapter with no network side effects."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Mapping, Protocol, Sequence, cast

from tools.cloud_agent_candidate_provider import (
    CloudCandidateProvider as GCPCloudCandidateProvider,
)
from tools.total_field.xiaoj_member_bound_session_candidate import (
    evaluate_member_action_session,
)
from tools.total_field_candidate_gateway import (
    receive_candidate as total_field_receive_candidate,
)


SOURCE_MODES = frozenset({"TOTAL_FIELD_PULL", "LLM_PUSH"})
PRIVILEGED_RESULT_KEYS = frozenset({"committed", "tfid", "total_field_hash"})
P3_PRIVILEGED_RESULT_KEYS = frozenset(
    {
        "allow",
        "commit",
        "committed",
        "commit_applied",
        "tfid",
        "total_field_hash",
        "canonical_pointer",
        "canonical_ref",
        "formal_execution_authority",
    }
)
DUAL_NLIO_RUN_ID = "W7TP_XIAOJ_DUAL_LLM_GOVERNED_NLIO_P1_POLICY_V1"
DEGRADATION_POLICY_VERSION = "w7tp-xiaoj-single-provider-degradation-policy/1.0"
DEGRADABLE_FAILURE_CLASSES = frozenset(
    {
        "PROVIDER_TIMEOUT",
        "PROVIDER_UNAVAILABLE",
        "TRANSPORT_UNREACHABLE",
        "RATE_LIMIT_NO_CANDIDATE_RETURNED",
    }
)
NON_DEGRADABLE_FAILURE_CLASSES = frozenset(
    {
        "DOMAIN_CANDIDATE_CONFLICT",
        "INVALID_SCHEMA",
        "FORBIDDEN_AUTHORITY",
        "SECRET_OR_MEMBER_PLAINTEXT_BOUNDARY",
        "IDENTITY_OR_PERMISSION_MISMATCH",
        "HASH_OR_ENVELOPE_MISMATCH",
        "PROVIDER_RETURNED_INVALID_CANDIDATE",
    }
)
DUAL_NLIO_REQUEST_MODES = frozenset(
    {"CHAT_ONLY", "CODE_DRAFT_ONLY", "ACTION_REQUEST"}
)
DEGRADATION_FORBIDDEN_EFFECTS = frozenset(
    {
        "tool_execution",
        "process_execution",
        "file_write",
        "db_write",
        "network_write",
        "router_write",
        "service_change",
        "credential_access",
        "secret_access",
        "member_plaintext_access",
        "canonical_change",
        "pointer_change",
        "permission_change",
        "identity_change",
    }
)
DEGRADATION_BOUNDARY_KEYS = frozenset(
    {
        "password",
        "token",
        "raw_token",
        "api_key",
        "raw_key",
        "private_key",
        "credential",
        "real_person_identity",
        "member_plaintext",
        "member_data",
        "contact_data",
        "address",
        "bank_data",
        "biometric_data",
        "medical_or_mental_health_data",
        "permission",
        "access_control_result",
    }
)


class XiaoJCandidateError(ValueError):
    """Stable XiaoJ candidate validation failure."""

    def __init__(self, reason_code: str):
        """Initialize one stable non-sensitive failure code."""

        super().__init__(reason_code)
        self.reason_code = reason_code


class CandidateProviderFailure(RuntimeError):
    """Typed provider failure carrying only one approved non-sensitive class."""

    def __init__(self, failure_class: str):
        allowed = DEGRADABLE_FAILURE_CLASSES | NON_DEGRADABLE_FAILURE_CLASSES
        if failure_class not in allowed:
            raise XiaoJCandidateError("PROVIDER_FAILURE_CLASS_UNSUPPORTED")
        super().__init__(failure_class)
        self.failure_class = failure_class


def _canonical_json(value: Any) -> str:
    """Return the fixed canonical JSON representation of a strict JSON value."""

    copied = _copy_json(value)
    try:
        return json.dumps(
            copied,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise XiaoJCandidateError("XIAOJ_CANDIDATE_NOT_JSON_COMPATIBLE") from exc


def _copy_json(value: Any) -> Any:
    """Strictly validate and recursively detach one JSON-compatible value."""

    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise XiaoJCandidateError("XIAOJ_CANDIDATE_NOT_JSON_COMPATIBLE")
        return value
    if isinstance(value, list):
        return [_copy_json(item) for item in value]
    if isinstance(value, dict):
        copied: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise XiaoJCandidateError("XIAOJ_CANDIDATE_NOT_JSON_COMPATIBLE")
            copied[key] = _copy_json(item)
        return copied
    raise XiaoJCandidateError("XIAOJ_CANDIDATE_NOT_JSON_COMPATIBLE")


def _freeze_json(value: Any) -> Any:
    """Convert detached JSON containers into recursively immutable containers."""

    copied = _copy_json(value)
    if isinstance(copied, dict):
        return MappingProxyType(
            {key: _freeze_json(nested) for key, nested in copied.items()}
        )
    if isinstance(copied, list):
        return tuple(_freeze_json(item) for item in copied)
    return copied


def _thaw_json(value: Any) -> Any:
    """Return a detached JSON representation of internal immutable data."""

    if isinstance(value, Mapping):
        thawed: dict[str, Any] = {}
        for key, nested in value.items():
            if not isinstance(key, str):
                raise XiaoJCandidateError("XIAOJ_CANDIDATE_NOT_JSON_COMPATIBLE")
            thawed[key] = _thaw_json(nested)
        return thawed
    if isinstance(value, (tuple, list)):
        return [_thaw_json(item) for item in value]
    return _copy_json(value)


def _contains_forbidden_authority(value: Any) -> bool:
    """Detect any candidate attempt to provide Total Field authority results."""

    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).lower()
            if normalized in PRIVILEGED_RESULT_KEYS:
                return True
            if normalized == "commit_applied" and nested is True:
                return True
            if normalized in {"final_decision", "decision"} and nested == "ALLOW":
                return True
            if _contains_forbidden_authority(nested):
                return True
    elif isinstance(value, list):
        return any(_contains_forbidden_authority(item) for item in value)
    return False


def _contains_p3_forbidden_authority(value: Any) -> bool:
    """Reject authority-shaped output specifically on P3 ACTION_REQUEST paths."""

    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = str(key).strip().casefold().replace("-", "_")
            if normalized in P3_PRIVILEGED_RESULT_KEYS:
                return True
            if normalized in {"final_decision", "decision"} and nested == "ALLOW":
                return True
            if _contains_p3_forbidden_authority(nested):
                return True
    elif isinstance(value, (tuple, list)):
        return any(_contains_p3_forbidden_authority(item) for item in value)
    return False


class CloudCandidateProvider(Protocol):
    """Contract for a cloud-layer candidate source."""

    def generate_candidate(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        """Return candidate content or raise a stable provider failure."""
        raise XiaoJCandidateError("CLOUD_PROVIDER_METHOD_NOT_BOUND")


class LocalCandidateProvider(Protocol):
    """Contract for a local sovereign candidate source."""

    def generate_candidate(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        """Return candidate content or raise a stable provider failure."""
        raise XiaoJCandidateError("LOCAL_PROVIDER_METHOD_NOT_BOUND")


class DirectCloudCandidateProvider(Protocol):
    """Candidate-only cloud interface used by the direct XiaoJ integration."""

    def generate_candidate(self, prompt: str, context: dict) -> dict:
        """Return a cloud candidate envelope without commit authority."""
        raise XiaoJCandidateError("DIRECT_CLOUD_PROVIDER_METHOD_NOT_BOUND")


class TotalFieldGatewayProtocol(Protocol):
    """Minimal interface used by XiaoJ to reach the sole candidate gateway."""

    def total_field_pull(
        self,
        candidate_payload: Mapping[str, Any],
        *,
        previous_state: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Submit a Total Field pull candidate through the unified receiver."""
        raise XiaoJCandidateError("TOTAL_FIELD_PULL_METHOD_NOT_BOUND")

    def llm_push(
        self,
        candidate_payload: Mapping[str, Any],
        *,
        previous_state: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Submit an LLM push candidate through the unified receiver."""
        raise XiaoJCandidateError("LLM_PUSH_METHOD_NOT_BOUND")


class DomainCompletionProviderProtocol(Protocol):
    """Candidate-only source contract shared by LOCAL and CLOUD providers."""

    def candidates_for(
        self, request_ref: str, source_mode: str
    ) -> tuple[dict[str, Any], ...]:
        """Return candidate envelopes without Total Field authority."""
        raise XiaoJCandidateError("DOMAIN_COMPLETION_PROVIDER_METHOD_NOT_BOUND")


class DomainCompletionBatchGatewayProtocol(Protocol):
    """Existing domain-completion batch receiver contract."""

    def receive_batch(
        self,
        candidates: tuple[Mapping[str, Any], ...],
        *,
        previous_values: Mapping[str, Any],
        forced_hold_reason: str | None = None,
    ) -> tuple[dict[str, Any], ...]:
        """Submit candidates through the existing Total Field receiver."""
        raise XiaoJCandidateError("DOMAIN_COMPLETION_GATEWAY_METHOD_NOT_BOUND")


@dataclass(frozen=True)
class InMemoryCandidateProvider:
    """Deterministic provider used only with caller-supplied test candidates."""

    provider_ref: str
    model_ref: str
    governance_candidate: Mapping[str, Any]
    persona_text: str = ""

    def __post_init__(self) -> None:
        """Validate references and retain only recursively immutable input data."""

        if any(
            not isinstance(value, str) or not value
            for value in (self.provider_ref, self.model_ref)
        ):
            raise XiaoJCandidateError("XIAOJ_REQUIRED_REFERENCE_MISSING")
        if not isinstance(self.persona_text, str):
            raise XiaoJCandidateError("XIAOJ_PERSONA_TEXT_INVALID")
        if not isinstance(self.governance_candidate, Mapping):
            raise XiaoJCandidateError("XIAOJ_GOVERNANCE_CANDIDATE_MISSING")
        governance = _copy_json(dict(self.governance_candidate))
        if _contains_forbidden_authority(governance):
            raise XiaoJCandidateError("XIAOJ_DIRECT_AUTHORITY_BLOCKED")
        object.__setattr__(self, "governance_candidate", _freeze_json(governance))

    def generate_candidate(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        """Return a fresh provider-neutral candidate from fixed in-memory data."""

        request_copy = _copy_json(dict(request))
        return {
            "provider_ref": self.provider_ref,
            "model_ref": self.model_ref,
            "persona_text": self.persona_text,
            "governance_candidate": _thaw_json(self.governance_candidate),
            "request_ref": request_copy.get("request_ref"),
        }


@dataclass(frozen=True)
class CandidateEnvelope:
    """Candidate envelope keeping persona and governance content separate."""

    source_mode: str
    model_ref: str
    provider_ref: str
    event_ref: str
    observation_domain_ref: str
    rule_ref: str
    logical_time: Any
    persona_text: str
    governance_candidate: Mapping[str, Any]
    candidate_hash: str

    def __post_init__(self) -> None:
        """Validate hash integrity and freeze every caller-owned container."""

        if self.source_mode not in SOURCE_MODES:
            raise XiaoJCandidateError("XIAOJ_SOURCE_MODE_UNSUPPORTED")
        required_refs = (
            self.model_ref,
            self.provider_ref,
            self.event_ref,
            self.observation_domain_ref,
            self.rule_ref,
        )
        if any(not isinstance(value, str) or not value for value in required_refs):
            raise XiaoJCandidateError("XIAOJ_REQUIRED_REFERENCE_MISSING")
        if not isinstance(self.persona_text, str):
            raise XiaoJCandidateError("XIAOJ_PERSONA_TEXT_INVALID")
        if not isinstance(self.governance_candidate, Mapping):
            raise XiaoJCandidateError("XIAOJ_GOVERNANCE_CANDIDATE_MISSING")
        logical_time = _copy_json(self.logical_time)
        governance = _copy_json(dict(self.governance_candidate))
        if not isinstance(governance, dict):
            raise XiaoJCandidateError("XIAOJ_GOVERNANCE_CANDIDATE_MISSING")
        if _contains_forbidden_authority(governance):
            raise XiaoJCandidateError("XIAOJ_DIRECT_AUTHORITY_BLOCKED")
        material = {
            "source_mode": self.source_mode,
            "model_ref": self.model_ref,
            "provider_ref": self.provider_ref,
            "event_ref": self.event_ref,
            "observation_domain_ref": self.observation_domain_ref,
            "rule_ref": self.rule_ref,
            "logical_time": logical_time,
            "governance_candidate": governance,
        }
        expected = hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()
        if self.candidate_hash != expected:
            raise XiaoJCandidateError("XIAOJ_CANDIDATE_HASH_MISMATCH")
        object.__setattr__(self, "logical_time", _freeze_json(logical_time))
        object.__setattr__(self, "governance_candidate", _freeze_json(governance))

    def governance_payload(self) -> dict[str, Any]:
        """Return only data permitted to enter governance processing."""

        payload = _thaw_json(self.governance_candidate)
        if not isinstance(payload, dict):
            raise XiaoJCandidateError("XIAOJ_GOVERNANCE_CANDIDATE_MISSING")
        if _contains_forbidden_authority(payload):
            raise XiaoJCandidateError("XIAOJ_DIRECT_AUTHORITY_BLOCKED")
        return payload

    def to_dict(self) -> dict[str, Any]:
        """Return a detached representation for display and tests."""
        return {
            "source_mode": self.source_mode,
            "model_ref": self.model_ref,
            "provider_ref": self.provider_ref,
            "event_ref": self.event_ref,
            "observation_domain_ref": self.observation_domain_ref,
            "rule_ref": self.rule_ref,
            "logical_time": _thaw_json(self.logical_time),
            "persona_text": self.persona_text,
            "governance_candidate": self.governance_payload(),
            "candidate_hash": self.candidate_hash,
        }


def build_candidate_envelope(
    *,
    source_mode: str,
    model_ref: str,
    provider_ref: str,
    event_ref: str,
    observation_domain_ref: str,
    rule_ref: str,
    logical_time: Any,
    persona_text: str,
    governance_candidate: Mapping[str, Any],
) -> CandidateEnvelope:
    """Build a deterministic candidate envelope without granting authority."""

    if source_mode not in SOURCE_MODES:
        raise XiaoJCandidateError("XIAOJ_SOURCE_MODE_UNSUPPORTED")
    required_refs = (model_ref, provider_ref, event_ref, observation_domain_ref, rule_ref)
    if any(not isinstance(value, str) or not value for value in required_refs):
        raise XiaoJCandidateError("XIAOJ_REQUIRED_REFERENCE_MISSING")
    if not isinstance(governance_candidate, Mapping):
        raise XiaoJCandidateError("XIAOJ_GOVERNANCE_CANDIDATE_MISSING")
    if not isinstance(persona_text, str):
        raise XiaoJCandidateError("XIAOJ_PERSONA_TEXT_INVALID")
    governance_copy = _copy_json(dict(governance_candidate))
    logical_time_copy = _copy_json(logical_time)
    if _contains_forbidden_authority(governance_copy):
        raise XiaoJCandidateError("XIAOJ_DIRECT_AUTHORITY_BLOCKED")
    hash_payload = {
        "source_mode": source_mode,
        "model_ref": model_ref,
        "provider_ref": provider_ref,
        "event_ref": event_ref,
        "observation_domain_ref": observation_domain_ref,
        "rule_ref": rule_ref,
        "logical_time": logical_time_copy,
        "governance_candidate": governance_copy,
    }
    candidate_hash = hashlib.sha256(_canonical_json(hash_payload).encode("utf-8")).hexdigest()
    return CandidateEnvelope(
        source_mode=source_mode,
        model_ref=model_ref,
        provider_ref=provider_ref,
        event_ref=event_ref,
        observation_domain_ref=observation_domain_ref,
        rule_ref=rule_ref,
        logical_time=logical_time_copy,
        persona_text=persona_text,
        governance_candidate=governance_copy,
        candidate_hash=candidate_hash,
    )


@dataclass(frozen=True)
class XiaoJCandidateAdapter:
    """Routes cloud/local candidates through one Total Field gateway only."""

    cloud_provider: CloudCandidateProvider
    local_provider: LocalCandidateProvider
    gateway: TotalFieldGatewayProtocol

    def _provider(self, provider_layer: str) -> CloudCandidateProvider | LocalCandidateProvider:
        """Select one explicitly injected provider layer."""

        if provider_layer == "CLOUD":
            return self.cloud_provider
        if provider_layer == "LOCAL":
            return self.local_provider
        raise XiaoJCandidateError("XIAOJ_PROVIDER_LAYER_UNSUPPORTED")

    def produce_envelope(
        self,
        *,
        source_mode: str,
        provider_layer: str,
        request: Mapping[str, Any],
        event_ref: str,
        observation_domain_ref: str,
        rule_ref: str,
        logical_time: Any,
    ) -> CandidateEnvelope:
        """Generate and validate one provider-neutral candidate envelope."""

        candidate = _copy_json(dict(self._provider(provider_layer).generate_candidate(request)))
        governance_candidate = candidate.get("governance_candidate")
        if not isinstance(governance_candidate, dict):
            raise XiaoJCandidateError("XIAOJ_GOVERNANCE_CANDIDATE_MISSING")
        return build_candidate_envelope(
            source_mode=source_mode,
            model_ref=cast(str, candidate.get("model_ref")),
            provider_ref=cast(str, candidate.get("provider_ref")),
            event_ref=event_ref,
            observation_domain_ref=observation_domain_ref,
            rule_ref=rule_ref,
            logical_time=logical_time,
            persona_text=cast(str, candidate.get("persona_text", "")),
            governance_candidate=governance_candidate,
        )

    def total_field_pull(
        self,
        envelope: CandidateEnvelope,
        *,
        previous_state: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Route a pull candidate without exposing persona text to governance."""

        if envelope.source_mode != "TOTAL_FIELD_PULL":
            raise XiaoJCandidateError("XIAOJ_PULL_SOURCE_MODE_MISMATCH")
        return self.gateway.total_field_pull(
            envelope.governance_payload(),
            previous_state=_copy_json(dict(previous_state)),
        )

    def llm_push(
        self,
        envelope: CandidateEnvelope,
        *,
        previous_state: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Route an LLM push candidate without granting commit authority."""

        if envelope.source_mode != "LLM_PUSH":
            raise XiaoJCandidateError("XIAOJ_PUSH_SOURCE_MODE_MISMATCH")
        return self.gateway.llm_push(
            envelope.governance_payload(),
            previous_state=_copy_json(dict(previous_state)),
        )

    @staticmethod
    def explain_decision(persona_text: str, gateway_result: Mapping[str, Any]) -> dict[str, Any]:
        """Keep human-facing explanation separate from the governance result."""

        result_copy = _copy_json(dict(gateway_result))
        return {
            "persona_text": str(persona_text),
            "governance_result": result_copy,
            "authority": "TOTAL_FIELD_GATEWAY",
        }


def dual_nlio_request_ref(request_text: str) -> str:
    """Derive an opaque local coordinate without disclosing natural-language input."""

    if not isinstance(request_text, str) or not request_text.strip():
        raise XiaoJCandidateError("DUAL_NLIO_REQUEST_TEXT_REQUIRED")
    digest = hashlib.sha256(request_text.strip().encode("utf-8")).hexdigest()
    return f"nlio:sha256:{digest}"


def _provider_failure_class(exc: Exception) -> str:
    """Map one provider or envelope failure to the closed policy vocabulary."""

    if isinstance(exc, CandidateProviderFailure):
        return exc.failure_class
    if isinstance(exc, TimeoutError):
        return "PROVIDER_TIMEOUT"
    if isinstance(exc, ConnectionError):
        return "TRANSPORT_UNREACHABLE"
    reason_code = str(getattr(exc, "reason_code", ""))
    if reason_code == "EXTERNAL_AUTHORITY_CLAIM_BLOCKED":
        return "FORBIDDEN_AUTHORITY"
    if "HASH" in reason_code or "ENVELOPE" in reason_code:
        return "HASH_OR_ENVELOPE_MISMATCH"
    if "IDENTITY" in reason_code or "PERMISSION" in reason_code:
        return "IDENTITY_OR_PERMISSION_MISMATCH"
    if "SCHEMA" in reason_code:
        return "INVALID_SCHEMA"
    return "PROVIDER_RETURNED_INVALID_CANDIDATE"


def _contains_degradation_boundary(value: Any) -> bool:
    """Detect prohibited identity, permission, secret, or member-data keys."""

    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = str(key).strip().casefold().replace("-", "_")
            if normalized in DEGRADATION_BOUNDARY_KEYS:
                return True
            if _contains_degradation_boundary(nested):
                return True
    elif isinstance(value, (tuple, list)):
        return any(_contains_degradation_boundary(item) for item in value)
    return False


@dataclass(frozen=True)
class DualLLMGovernedNLIOCoordinator:
    """Sequence two candidate sources through the existing governed receiver."""

    local_provider: DomainCompletionProviderProtocol
    cloud_provider: DomainCompletionProviderProtocol
    domain_gateway: DomainCompletionBatchGatewayProtocol

    @staticmethod
    def _render(
        decision: str,
        *,
        member_text: str,
        channel: str,
        gate_code: str | None = None,
    ) -> dict[str, Any]:
        from tools.total_field.human_response_renderer import render_human_response

        renderer_decision = {
            "ALLOW": "PASS",
            "HOLD": "HOLD",
            "BLOCK": "BLOCK",
            "QUARANTINE": "BLOCK",
        }.get(decision, "HOLD")
        gate_result: dict[str, Any] = {
            "decision": renderer_decision,
            "risk_level": "LOW" if renderer_decision == "PASS" else "MEDIUM",
        }
        if renderer_decision == "PASS":
            gate_result["reply_candidate"] = {
                "text": member_text or "候選已由總場完成驗證。"
            }
        if gate_code is not None:
            gate_result["gate_code"] = gate_code
        return render_human_response(gate_result, channel=channel)

    @staticmethod
    def _provider_candidates(
        provider: DomainCompletionProviderProtocol,
        *,
        request_ref: str,
        persona_text: str,
        layer: str,
        provider_call_order: list[str],
    ) -> tuple[tuple[dict[str, Any], ...], str | None]:
        from tools.sovereign_ai_domain_completion_candidate import (
            build_xiaoj_envelope,
            with_source_mode,
        )

        provider_call_order.append(layer)
        source_mode = "XIAOJ_LOCAL" if layer == "LOCAL" else "LLM_PUSH"
        try:
            raw_candidates = provider.candidates_for(request_ref, source_mode)
            if not isinstance(raw_candidates, tuple) or not raw_candidates:
                raise CandidateProviderFailure("PROVIDER_RETURNED_INVALID_CANDIDATE")
            if layer == "LOCAL":
                candidates = tuple(
                    build_xiaoj_envelope(persona_text, item).governance_payload()
                    for item in raw_candidates
                )
            else:
                candidates = tuple(
                    with_source_mode(item, "LLM_PUSH") for item in raw_candidates
                )
            return tuple(cast(dict[str, Any], item) for item in candidates), None
        except Exception as exc:
            return (), _provider_failure_class(exc)

    def _hold_result(
        self,
        *,
        state: str,
        request_ref: str,
        channel: str,
        provider_call_order: list[str],
        available_provider: str | None,
        missing_provider: str | list[str] | None,
        failure_class: str | dict[str, str],
        request_mode: str,
        gate_code: str | None = None,
    ) -> dict[str, Any]:
        rendered = self._render(
            "HOLD",
            member_text="",
            channel=channel,
            gate_code=gate_code,
        )
        return {
            "STATE": state,
            "RUN_ID": DUAL_NLIO_RUN_ID,
            "policy_version": DEGRADATION_POLICY_VERSION,
            "request_ref": request_ref,
            "provider_call_order": provider_call_order,
            "local_candidate_hashes": [],
            "cloud_candidate_hashes": [],
            "candidate_results": [],
            "total_field_final_decision": None,
            "renderer_decision": "HOLD",
            "reply_text": rendered["reply_text"],
            "both_received": False,
            "degraded_mode": False,
            "dual_convergence": False,
            "available_provider": available_provider,
            "missing_provider": missing_provider,
            "failure_class": failure_class,
            "request_mode": request_mode,
            "candidate_sources_are_authority": False,
            "total_field_authority": True,
            "persona_tfs_hash_exclusion": "PASS",
            "side_effects_performed": False,
            "internal_error_exposed": False,
        }

    @staticmethod
    def _degraded_evidence(
        results: tuple[dict[str, Any], ...]
    ) -> list[dict[str, Any]]:
        """Expose decision evidence without formal state identifiers or hashes."""

        permitted = {
            "schema_version",
            "run_id",
            "candidate_hash",
            "domain",
            "entity_ref",
            "attribute_name",
            "source_mode",
            "sensitivity",
            "fixed_point_status",
            "runtime_final_decision",
            "final_decision",
            "decision_reason_codes",
            "candidate_source_is_authority",
            "cloud_llm_is_committer",
            "xiaoj_is_final_authority",
            "persona_governance_separation",
            "total_field_gateway",
        }
        return [
            {key: _copy_json(value) for key, value in item.items() if key in permitted}
            for item in results
        ]

    def process(
        self,
        request_text: str,
        *,
        previous_values: Mapping[str, Any],
        persona_text: str = "",
        channel: str = "web",
        request_mode: str = "CHAT_ONLY",
        requested_effects: Mapping[str, bool] | None = None,
        member_action_candidate: Mapping[str, Any] | None = None,
        member_nonce_consumer: Any | None = None,
        member_p1_verifier: (
            Callable[[Mapping[str, Any]], Mapping[str, Any]] | None
        ) = None,
        member_current_epoch: int | None = None,
        active_seat_leases: Sequence[Mapping[str, Any]] = (),
    ) -> dict[str, Any]:
        """Return governed final state plus a natural-language presentation."""

        from tools.sovereign_ai_domain_completion_candidate import (
            validate_candidate,
        )

        request_ref = dual_nlio_request_ref(request_text)
        if request_mode not in DUAL_NLIO_REQUEST_MODES:
            raise XiaoJCandidateError("DUAL_NLIO_REQUEST_MODE_UNSUPPORTED")
        provider_call_order: list[str] = []
        member_gate: Mapping[str, Any] | None = None
        missing_member_gate_reason: str | None = None
        if request_mode == "ACTION_REQUEST":
            if not isinstance(member_action_candidate, Mapping):
                missing_member_gate_reason = "HOLD_MEMBER_DUAL_RECEIPT_REQUIRED"
            elif not isinstance(member_current_epoch, int):
                missing_member_gate_reason = "HOLD_MEMBER_SESSION_CLOCK_REQUIRED"
            else:
                member_gate = evaluate_member_action_session(
                    member_action_candidate,
                    current_epoch=member_current_epoch,
                    nonce_consumer=member_nonce_consumer,
                    p1_verifier=member_p1_verifier,
                    active_seat_leases=active_seat_leases,
                )
                if member_gate.get("state") != "PASS":
                    reason_code = str(
                        member_gate.get("reason_code")
                        or "HOLD_MEMBER_ACTION_GATE"
                    )
                    return self._hold_result(
                        state=reason_code,
                        request_ref=request_ref,
                        channel=channel,
                        provider_call_order=provider_call_order,
                        available_provider=None,
                        missing_provider=None,
                        failure_class="IDENTITY_OR_PERMISSION_MISMATCH",
                        request_mode=request_mode,
                        gate_code=reason_code,
                    )
        local_candidates, local_failure = self._provider_candidates(
            self.local_provider,
            request_ref=request_ref,
            persona_text=persona_text,
            layer="LOCAL",
            provider_call_order=provider_call_order,
        )
        cloud_candidates, cloud_failure = self._provider_candidates(
            self.cloud_provider,
            request_ref=request_ref,
            persona_text=persona_text,
            layer="CLOUD",
            provider_call_order=provider_call_order,
        )
        if request_mode == "ACTION_REQUEST" and any(
            _contains_p3_forbidden_authority(item)
            for item in (*local_candidates, *cloud_candidates)
        ):
            return self._hold_result(
                state="BLOCK_PROVIDER_AUTHORITY_INJECTION",
                request_ref=request_ref,
                channel=channel,
                provider_call_order=provider_call_order,
                available_provider=None,
                missing_provider=None,
                failure_class="FORBIDDEN_AUTHORITY",
                request_mode=request_mode,
                gate_code="BLOCK_PROVIDER_AUTHORITY_INJECTION",
            )
        available = {
            layer: candidates
            for layer, candidates in (
                ("LOCAL", local_candidates),
                ("CLOUD", cloud_candidates),
            )
            if candidates
        }
        failures = {
            layer: failure
            for layer, failure in (
                ("LOCAL", local_failure),
                ("CLOUD", cloud_failure),
            )
            if failure is not None
        }

        if not available:
            return self._hold_result(
                state="HOLD_BOTH_PROVIDERS_UNAVAILABLE",
                request_ref=request_ref,
                channel=channel,
                provider_call_order=provider_call_order,
                available_provider=None,
                missing_provider=["LOCAL", "CLOUD"],
                failure_class=failures,
                request_mode=request_mode,
            )

        if len(available) == 1:
            available_provider, single_candidates = next(iter(available.items()))
            missing_provider = "CLOUD" if available_provider == "LOCAL" else "LOCAL"
            failure_class = failures[missing_provider]
            if failure_class not in DEGRADABLE_FAILURE_CLASSES:
                return self._hold_result(
                    state="HOLD_NON_DEGRADABLE_PROVIDER_FAILURE",
                    request_ref=request_ref,
                    channel=channel,
                    provider_call_order=provider_call_order,
                    available_provider=available_provider,
                    missing_provider=missing_provider,
                    failure_class=failure_class,
                    request_mode=request_mode,
                )
            validated = tuple(validate_candidate(item) for item in single_candidates)
            if any(
                item.attribute_name.strip().casefold().replace("-", "_")
                in DEGRADATION_BOUNDARY_KEYS
                or _contains_degradation_boundary(item.candidate_value)
                for item in validated
            ):
                return self._hold_result(
                    state="HOLD_NON_DEGRADABLE_PROVIDER_FAILURE",
                    request_ref=request_ref,
                    channel=channel,
                    provider_call_order=provider_call_order,
                    available_provider=available_provider,
                    missing_provider=missing_provider,
                    failure_class="SECRET_OR_MEMBER_PLAINTEXT_BOUNDARY",
                    request_mode=request_mode,
                )
            effects = {} if requested_effects is None else dict(requested_effects)
            invalid_effects = {
                key for key, enabled in effects.items()
                if key not in DEGRADATION_FORBIDDEN_EFFECTS
                or not isinstance(enabled, bool)
            }
            if invalid_effects:
                return self._hold_result(
                    state="HOLD_NON_DEGRADABLE_PROVIDER_FAILURE",
                    request_ref=request_ref,
                    channel=channel,
                    provider_call_order=provider_call_order,
                    available_provider=available_provider,
                    missing_provider=missing_provider,
                    failure_class="IDENTITY_OR_PERMISSION_MISMATCH",
                    request_mode=request_mode,
                )
            action_requested = request_mode == "ACTION_REQUEST" or any(effects.values())
            forced_hold_reason = (
                "HOLD_SINGLE_PROVIDER_ACTION_NOT_AUTHORIZED"
                if action_requested else None
            )
            results = self.domain_gateway.receive_batch(
                single_candidates,
                previous_values=_copy_json(dict(previous_values)),
                forced_hold_reason=forced_hold_reason,
            )
            final_decisions = {str(item.get("final_decision")) for item in results}
            if len(results) != len(single_candidates) or len(final_decisions) != 1:
                return self._hold_result(
                    state="HOLD_NON_DEGRADABLE_PROVIDER_FAILURE",
                    request_ref=request_ref,
                    channel=channel,
                    provider_call_order=provider_call_order,
                    available_provider=available_provider,
                    missing_provider=missing_provider,
                    failure_class="PROVIDER_RETURNED_INVALID_CANDIDATE",
                    request_mode=request_mode,
                )
            final_decision = final_decisions.pop()
            if action_requested:
                member_text = ""
                state = "HOLD_SINGLE_PROVIDER_ACTION_NOT_AUTHORIZED"
                gate_code = state
            elif request_mode == "CODE_DRAFT_ONLY":
                member_text = "目前使用備援模式完成程式碼候選草稿，未寫檔或執行。"
                state = "PASS"
                gate_code = None
            else:
                member_text = (
                    "目前使用備援模式完成回覆。 "
                    + (persona_text or "候選已由總場完成驗證。")
                )
                state = "PASS"
                gate_code = None
            rendered = self._render(
                final_decision,
                member_text=member_text,
                channel=channel,
                gate_code=gate_code,
            )
            result: dict[str, Any] = {
                "STATE": state,
                "RUN_ID": DUAL_NLIO_RUN_ID,
                "policy_version": DEGRADATION_POLICY_VERSION,
                "request_ref": request_ref,
                "provider_call_order": provider_call_order,
                "local_candidate_hashes": [
                    item.candidate_hash for item in validated
                ] if available_provider == "LOCAL" else [],
                "cloud_candidate_hashes": [
                    item.candidate_hash for item in validated
                ] if available_provider == "CLOUD" else [],
                "candidate_results": self._degraded_evidence(results),
                "total_field_final_decision": final_decision,
                "renderer_decision": rendered["decision"],
                "reply_text": rendered["reply_text"],
                "both_received": False,
                "degraded_mode": True,
                "dual_convergence": False,
                "available_provider": available_provider,
                "missing_provider": missing_provider,
                "failure_class": failure_class,
                "request_mode": request_mode,
                "candidate_sources_are_authority": False,
                "total_field_authority": True,
                "persona_tfs_hash_exclusion": "PASS",
                "side_effects_performed": False,
                "formal_state_material_exposed": False,
                "internal_error_exposed": False,
            }
            if member_gate is not None:
                result["member_action_gate_ref"] = member_gate["gate_ref"]
            if request_mode == "CODE_DRAFT_ONLY" and not action_requested:
                draft_values = [item.candidate_value for item in validated]
                draft_text = "\n\n".join(
                    value if isinstance(value, str) else _canonical_json(value)
                    for value in draft_values
                )
                result["code_draft_candidate"] = {
                    "status": "CANDIDATE_ONLY",
                    "text": draft_text,
                    "file_write": False,
                    "execution": False,
                    "commit": False,
                    "deploy": False,
                }
            return result

        if missing_member_gate_reason is not None:
            return self._hold_result(
                state=missing_member_gate_reason,
                request_ref=request_ref,
                channel=channel,
                provider_call_order=provider_call_order,
                available_provider=["LOCAL", "CLOUD"],
                missing_provider=None,
                failure_class="IDENTITY_OR_PERMISSION_MISMATCH",
                request_mode=request_mode,
                gate_code=missing_member_gate_reason,
            )
        combined: tuple[Mapping[str, Any], ...] = (
            *local_candidates,
            *cloud_candidates,
        )
        results = self.domain_gateway.receive_batch(
            combined,
            previous_values=_copy_json(dict(previous_values)),
        )
        final_decisions = {str(item.get("final_decision")) for item in results}
        if len(results) != len(combined) or len(final_decisions) != 1:
            return self._hold_result(
                state="HOLD_NON_UNIFORM_TOTAL_FIELD_RESULTS",
                request_ref=request_ref,
                channel=channel,
                provider_call_order=provider_call_order,
                available_provider=None,
                missing_provider=None,
                failure_class="PROVIDER_RETURNED_INVALID_CANDIDATE",
                request_mode=request_mode,
            )
        final_decision = final_decisions.pop()
        conflict = any(
            "HOLD_CANDIDATE_CONFLICT_DETECTED"
            in cast(list[str], item.get("decision_reason_codes", []))
            for item in results
        )
        rendered = self._render(
            final_decision,
            member_text=persona_text,
            channel=channel,
        )
        local_hashes = [
            validate_candidate(item).candidate_hash for item in local_candidates
        ]
        cloud_hashes = [
            validate_candidate(item).candidate_hash for item in cloud_candidates
        ]
        result = {
            "STATE": "PASS",
            "RUN_ID": DUAL_NLIO_RUN_ID,
            "policy_version": DEGRADATION_POLICY_VERSION,
            "request_ref": request_ref,
            "provider_call_order": provider_call_order,
            "local_candidate_hashes": local_hashes,
            "cloud_candidate_hashes": cloud_hashes,
            "candidate_results": _copy_json(list(results)),
            "total_field_final_decision": final_decision,
            "renderer_decision": rendered["decision"],
            "reply_text": rendered["reply_text"],
            "both_received": True,
            "degraded_mode": False,
            "dual_convergence": not conflict,
            "available_provider": ["LOCAL", "CLOUD"],
            "missing_provider": None,
            "failure_class": "DOMAIN_CANDIDATE_CONFLICT" if conflict else None,
            "request_mode": request_mode,
            "candidate_sources_are_authority": False,
            "total_field_authority": True,
            "persona_tfs_hash_exclusion": "PASS",
            "side_effects_performed": False,
            "internal_error_exposed": False,
        }
        if member_gate is not None:
            result["member_action_gate_ref"] = member_gate["gate_ref"]
        return result


def cloud_push(
    prompt: str,
    context: dict,
    *,
    provider: DirectCloudCandidateProvider | None = None,
    member_action_candidate: Mapping[str, Any] | None = None,
    member_nonce_consumer: Any | None = None,
    member_p1_verifier: (
        Callable[[Mapping[str, Any]], Mapping[str, Any]] | None
    ) = None,
    member_current_epoch: int | None = None,
    active_seat_leases: Sequence[Mapping[str, Any]] = (),
) -> Mapping[str, Any]:
    """Route Cloud -> XiaoJ -> the sole Total Field candidate receiver.

    ``previous_state`` and ``observation_domains`` are trusted local inputs in
    ``context`` and are never copied into the provider's ``cloud_context``.
    Persona text remains envelope-only and is excluded from governance input.
    """

    if not isinstance(prompt, str) or not prompt.strip():
        raise XiaoJCandidateError("CLOUD_PUSH_PROMPT_REQUIRED")
    if not isinstance(context, dict):
        raise XiaoJCandidateError("CLOUD_PUSH_CONTEXT_REQUIRED")
    context_copy = _copy_json(context)
    if not isinstance(context_copy, dict):
        raise XiaoJCandidateError("CLOUD_PUSH_CONTEXT_REQUIRED")
    previous_state = context_copy.get("previous_state")
    observation_domains = context_copy.get("observation_domains")
    if not isinstance(previous_state, dict):
        raise XiaoJCandidateError("CLOUD_PUSH_PREVIOUS_STATE_REQUIRED")
    if not isinstance(observation_domains, dict):
        raise XiaoJCandidateError("CLOUD_PUSH_OBSERVATION_DOMAINS_REQUIRED")
    selected_provider = provider or GCPCloudCandidateProvider()
    generated = _copy_json(selected_provider.generate_candidate(prompt, context_copy))
    if not isinstance(generated, dict):
        raise XiaoJCandidateError("CLOUD_PUSH_PROVIDER_RESULT_INVALID")
    if generated.get("source_mode") != "LLM_PUSH":
        raise XiaoJCandidateError("CLOUD_PUSH_SOURCE_MODE_INVALID")
    if generated.get("candidate_only") is not True:
        raise XiaoJCandidateError("CLOUD_PUSH_CANDIDATE_ONLY_REQUIRED")
    governance_candidate = generated.get("candidate")
    if not isinstance(governance_candidate, dict):
        raise XiaoJCandidateError("XIAOJ_GOVERNANCE_CANDIDATE_MISSING")
    if _contains_forbidden_authority(governance_candidate):
        raise XiaoJCandidateError("XIAOJ_DIRECT_AUTHORITY_BLOCKED")
    if (
        member_action_candidate is not None
        and _contains_p3_forbidden_authority(governance_candidate)
    ):
        raise XiaoJCandidateError("XIAOJ_P3_PROVIDER_AUTHORITY_BLOCKED")
    governance_candidate = _copy_json(governance_candidate)
    governance_candidate["source_mode"] = "LLM_PUSH"
    governance_candidate.pop("candidate_only", None)
    event_ref = generated.get("event_ref")
    observation_domain_ref = generated.get("observation_domain_ref")
    rule_ref = generated.get("rule_ref")
    logical_time = context_copy.get("logical_time")
    if logical_time is None:
        event = governance_candidate.get("event")
        if isinstance(event, dict):
            logical_time = event.get("logical_time")
    envelope = build_candidate_envelope(
        source_mode="LLM_PUSH",
        model_ref=cast(str, generated.get("model_ref")),
        provider_ref=cast(str, generated.get("provider_ref")),
        event_ref=cast(str, event_ref),
        observation_domain_ref=cast(str, observation_domain_ref),
        rule_ref=cast(str, rule_ref),
        logical_time=logical_time,
        persona_text=cast(str, context_copy.get("persona_text", "")),
        governance_candidate=governance_candidate,
    )
    payload = envelope.governance_payload()
    payload["source_mode"] = "LLM_PUSH"
    payload["candidate_only"] = True
    if member_action_candidate is not None:
        payload["member_action_candidate"] = _copy_json(
            dict(member_action_candidate)
        )
        payload_context = payload.get("context")
        if not isinstance(payload_context, dict):
            payload_context = {}
        payload_context["request_mode"] = "ACTION_REQUEST"
        payload["context"] = payload_context
    return total_field_receive_candidate(
        payload,
        previous_state=previous_state,
        observation_domains=observation_domains,
        member_nonce_consumer=member_nonce_consumer,
        member_p1_verifier=member_p1_verifier,
        member_current_epoch=member_current_epoch,
        active_seat_leases=active_seat_leases,
    )
