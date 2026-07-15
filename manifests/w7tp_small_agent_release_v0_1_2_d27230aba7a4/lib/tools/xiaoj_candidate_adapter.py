#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provider-neutral XiaoJ candidate adapter with no network side effects."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Protocol, cast

from tools.cloud_agent_candidate_provider import (
    CloudCandidateProvider as GCPCloudCandidateProvider,
)
from tools.total_field_candidate_gateway import (
    receive_candidate as total_field_receive_candidate,
)


SOURCE_MODES = frozenset({"TOTAL_FIELD_PULL", "LLM_PUSH"})
PRIVILEGED_RESULT_KEYS = frozenset({"committed", "tfid", "total_field_hash"})


class XiaoJCandidateError(ValueError):
    """Stable XiaoJ candidate validation failure."""

    def __init__(self, reason_code: str):
        """Initialize one stable non-sensitive failure code."""

        super().__init__(reason_code)
        self.reason_code = reason_code


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


def cloud_push(
    prompt: str,
    context: dict,
    *,
    provider: DirectCloudCandidateProvider | None = None,
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
    return total_field_receive_candidate(
        payload,
        previous_state=previous_state,
        observation_domains=observation_domains,
    )
