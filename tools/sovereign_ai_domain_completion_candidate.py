#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic candidate contracts for sovereign multi-domain completion.

This module has no cloud client and grants no authority.  It validates and
detaches attribute candidates produced by caller-supplied Fake/InMemory
providers before the candidates enter the existing Total Field gateway.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "SOVEREIGN_AI_MULTI_DOMAIN_CLOUD_COMPLETION_CANDIDATE_V0_1"
SCHEMA_VERSION = "sovereign-ai-domain-completion-candidate/0.1"
SCHEMA_PATH = (
    ROOT / "schemas/field/sovereign_ai_domain_completion_candidate.schema.json"
)
POLICY_PATH = (
    ROOT
    / "runtime/total_field/candidate/sovereign_ai_domain_completion_policy_v0_1.json"
)

DOMAINS = frozenset({"COMMUNITY", "COMMERCE", "PROPERTY"})
SOURCE_MODES = frozenset(
    {"TOTAL_FIELD_PULL", "LLM_PUSH", "XIAOJ_LOCAL", "RULE_LOOKUP", "HUMAN_INPUT"}
)
SENSITIVITY_CLASSES = frozenset(
    {
        "SAFE_DERIVED",
        "EVIDENCE_REQUIRED",
        "OWNER_CONFIRMATION_REQUIRED",
        "PRIVACY_RESTRICTED",
        "LEGAL_REVIEW_REQUIRED",
        "FINANCIAL_REVIEW_REQUIRED",
        "UNSUPPORTED",
    }
)
AUTHORITY_FORBIDDEN_KEYS = frozenset(
    {"committed", "tfid", "total_field_hash"}
)


JSONValue = (
    None
    | bool
    | int
    | float
    | str
    | list["JSONValue"]
    | dict[str, "JSONValue"]
)


class DomainCompletionError(ValueError):
    """Stable candidate rejection without echoing caller data."""

    def __init__(self, reason_code: str, path: str = "$") -> None:
        self.reason_code = reason_code
        self.path = path
        super().__init__(f"{reason_code}:{path}")


def canonical_json(value: Any) -> str:
    """Return the repository's deterministic JSON representation."""

    try:
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise DomainCompletionError("CANDIDATE_JSON_INVALID") from exc


def deep_copy_json(value: Any) -> JSONValue:
    """Validate and fully detach one JSON value."""

    try:
        copied = json.loads(
            canonical_json(value),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise DomainCompletionError("CANDIDATE_JSON_INVALID") from exc
    return cast(JSONValue, copied)


def canonical_sha256(value: Any) -> str:
    """Hash one canonical JSON value with SHA-256."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _authority_claim_path(value: Any, path: str = "$") -> str | None:
    """Find caller attempts to supply Total Field-owned authority results."""

    if isinstance(value, Mapping):
        for key in sorted(value, key=str):
            nested = value[key]
            normalized = str(key).casefold()
            child = f"{path}.{key}"
            if normalized in AUTHORITY_FORBIDDEN_KEYS:
                return child
            if normalized == "commit_applied" and nested is True:
                return child
            if normalized == "final_decision" and nested == "ALLOW":
                return child
            found = _authority_claim_path(nested, child)
            if found is not None:
                return found
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            found = _authority_claim_path(nested, f"{path}[{index}]")
            if found is not None:
                return found
    return None


def _load_schema(path: Path = SCHEMA_PATH) -> dict[str, Any]:
    """Load and validate the closed candidate schema."""

    try:
        schema = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise DomainCompletionError("CANDIDATE_SCHEMA_READ_FAILED") from exc
    if not isinstance(schema, dict):
        raise DomainCompletionError("CANDIDATE_SCHEMA_INVALID")
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        raise DomainCompletionError("CANDIDATE_SCHEMA_INVALID") from exc
    return schema


def _validation_path(error: ValidationError) -> str:
    path = "$"
    for part in error.absolute_path:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


def calculate_candidate_hash(value: Mapping[str, Any]) -> str:
    """Hash every governance field except the self-referential hash field."""

    if not isinstance(value, Mapping):
        raise DomainCompletionError("CANDIDATE_MAPPING_REQUIRED")
    payload = dict(value)
    payload.pop("candidate_hash", None)
    payload.pop("persona_text", None)
    copied = deep_copy_json(payload)
    if not isinstance(copied, dict):
        raise DomainCompletionError("CANDIDATE_MAPPING_REQUIRED")
    return canonical_sha256(copied)


@dataclass(frozen=True, slots=True)
class GovernanceCandidate:
    """One validated candidate attribute with no commit authority."""

    domain: str
    entity_ref: str
    attribute_name: str
    candidate_value: JSONValue
    source_mode: str
    model_ref: str
    provider_ref: str
    event_ref: str
    observation_domain_ref: str
    rule_ref: str
    evidence_refs: tuple[str, ...]
    confidence: float
    sensitivity: str
    requires_human_confirmation: bool
    candidate_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate_value", deep_copy_json(self.candidate_value))
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))

    @property
    def identity_key(self) -> str:
        """Return the deterministic per-attribute state lookup key."""

        return f"{self.domain}|{self.entity_ref}|{self.attribute_name}"

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a detached schema-valid candidate mapping."""

        value: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "domain": self.domain,
            "entity_ref": self.entity_ref,
            "attribute_name": self.attribute_name,
            "candidate_value": self.candidate_value,
            "source_mode": self.source_mode,
            "model_ref": self.model_ref,
            "provider_ref": self.provider_ref,
            "event_ref": self.event_ref,
            "observation_domain_ref": self.observation_domain_ref,
            "rule_ref": self.rule_ref,
            "evidence_refs": list(self.evidence_refs),
            "confidence": self.confidence,
            "sensitivity": self.sensitivity,
            "requires_human_confirmation": self.requires_human_confirmation,
            "candidate_hash": self.candidate_hash,
        }
        copied = deep_copy_json(value)
        assert isinstance(copied, dict)
        return copied


def validate_candidate(
    value: Mapping[str, Any], *, schema_path: Path = SCHEMA_PATH
) -> GovernanceCandidate:
    """Validate, hash-check, and detach one attribute candidate."""

    if not isinstance(value, Mapping):
        raise DomainCompletionError("CANDIDATE_MAPPING_REQUIRED")
    claim_path = _authority_claim_path(value)
    if claim_path is not None:
        raise DomainCompletionError("EXTERNAL_AUTHORITY_CLAIM_BLOCKED", claim_path)
    copied = deep_copy_json(dict(value))
    if not isinstance(copied, dict):
        raise DomainCompletionError("CANDIDATE_MAPPING_REQUIRED")
    validator = Draft202012Validator(_load_schema(schema_path))
    errors = sorted(
        validator.iter_errors(copied),
        key=lambda item: ([str(part) for part in item.absolute_path], item.message),
    )
    if errors:
        raise DomainCompletionError(
            "CANDIDATE_SCHEMA_VALIDATION_FAILED", _validation_path(errors[0])
        )
    expected_hash = calculate_candidate_hash(copied)
    if copied["candidate_hash"] != expected_hash:
        raise DomainCompletionError("CANDIDATE_HASH_MISMATCH", "$.candidate_hash")
    return GovernanceCandidate(
        domain=cast(str, copied["domain"]),
        entity_ref=cast(str, copied["entity_ref"]),
        attribute_name=cast(str, copied["attribute_name"]),
        candidate_value=cast(JSONValue, copied["candidate_value"]),
        source_mode=cast(str, copied["source_mode"]),
        model_ref=cast(str, copied["model_ref"]),
        provider_ref=cast(str, copied["provider_ref"]),
        event_ref=cast(str, copied["event_ref"]),
        observation_domain_ref=cast(str, copied["observation_domain_ref"]),
        rule_ref=cast(str, copied["rule_ref"]),
        evidence_refs=tuple(cast(list[str], copied["evidence_refs"])),
        confidence=float(cast(float, copied["confidence"])),
        sensitivity=cast(str, copied["sensitivity"]),
        requires_human_confirmation=cast(
            bool, copied["requires_human_confirmation"]
        ),
        candidate_hash=cast(str, copied["candidate_hash"]),
    )


def build_candidate(**fields: Any) -> dict[str, JSONValue]:
    """Build and validate one candidate from explicit caller-controlled fields."""

    payload = dict(fields)
    payload.setdefault("schema_version", SCHEMA_VERSION)
    payload.pop("candidate_hash", None)
    payload["candidate_hash"] = calculate_candidate_hash(payload)
    return validate_candidate(payload).to_dict()


def with_source_mode(
    value: Mapping[str, Any], source_mode: str
) -> dict[str, JSONValue]:
    """Return a re-hashed detached candidate for one approved ingress mode."""

    if source_mode not in SOURCE_MODES:
        raise DomainCompletionError("SOURCE_MODE_UNSUPPORTED", "$.source_mode")
    copied = deep_copy_json(dict(value))
    if not isinstance(copied, dict):
        raise DomainCompletionError("CANDIDATE_MAPPING_REQUIRED")
    copied["source_mode"] = source_mode
    copied.pop("candidate_hash", None)
    copied["candidate_hash"] = calculate_candidate_hash(copied)
    return validate_candidate(copied).to_dict()


@dataclass(frozen=True, slots=True)
class DomainAdapter:
    """Narrow adapter that prevents cross-domain candidate substitution."""

    domain: str

    def adapt(self, value: Mapping[str, Any]) -> GovernanceCandidate:
        candidate = validate_candidate(value)
        if candidate.domain != self.domain:
            raise DomainCompletionError("DOMAIN_ADAPTER_MISMATCH", "$.domain")
        return candidate


class CommunityDomainAdapter(DomainAdapter):
    def __init__(self) -> None:
        super().__init__("COMMUNITY")


class CommerceDomainAdapter(DomainAdapter):
    def __init__(self) -> None:
        super().__init__("COMMERCE")


class PropertyDomainAdapter(DomainAdapter):
    def __init__(self) -> None:
        super().__init__("PROPERTY")


def adapter_for(domain: str) -> DomainAdapter:
    """Resolve exactly one of the three candidate domain adapters."""

    adapters: dict[str, DomainAdapter] = {
        "COMMUNITY": CommunityDomainAdapter(),
        "COMMERCE": CommerceDomainAdapter(),
        "PROPERTY": PropertyDomainAdapter(),
    }
    try:
        return adapters[domain]
    except KeyError as exc:
        raise DomainCompletionError("DOMAIN_UNSUPPORTED", "$.domain") from exc


class CompletionProvider(Protocol):
    """Provider-neutral interface; implementations return candidates only."""

    def candidates_for(
        self, request_ref: str, source_mode: str
    ) -> tuple[dict[str, JSONValue], ...]: ...


class InMemoryCompletionProvider:
    """Deterministic test provider with no network or external model calls."""

    def __init__(self, responses: Mapping[str, Sequence[Mapping[str, Any]]]) -> None:
        copied = deep_copy_json(
            {key: [dict(item) for item in items] for key, items in responses.items()}
        )
        if not isinstance(copied, dict):
            raise DomainCompletionError("PROVIDER_RESPONSES_INVALID")
        self._responses = copied
        self.call_count = 0

    def candidates_for(
        self, request_ref: str, source_mode: str
    ) -> tuple[dict[str, JSONValue], ...]:
        if not isinstance(request_ref, str) or not request_ref:
            raise DomainCompletionError("PROVIDER_REQUEST_REF_REQUIRED")
        if source_mode not in SOURCE_MODES:
            raise DomainCompletionError("SOURCE_MODE_UNSUPPORTED")
        if request_ref not in self._responses:
            raise DomainCompletionError("PROVIDER_REQUEST_NOT_FOUND")
        raw_items = self._responses[request_ref]
        if not isinstance(raw_items, list):
            raise DomainCompletionError("PROVIDER_RESPONSES_INVALID")
        self.call_count += 1
        results: list[dict[str, JSONValue]] = []
        for raw in raw_items:
            if not isinstance(raw, dict):
                raise DomainCompletionError("PROVIDER_CANDIDATE_INVALID")
            results.append(with_source_mode(raw, source_mode))
        return tuple(results)


@dataclass(frozen=True, slots=True)
class XiaoJCandidateEnvelope:
    """Keep persona text outside the governance payload and its hash."""

    persona_text: str
    governance_candidate: GovernanceCandidate

    def governance_payload(self) -> dict[str, JSONValue]:
        return self.governance_candidate.to_dict()


def build_xiaoj_envelope(
    persona_text: str, candidate: Mapping[str, Any]
) -> XiaoJCandidateEnvelope:
    """Build a separated XiaoJ envelope without hashing persona text."""

    if not isinstance(persona_text, str):
        raise DomainCompletionError("XIAOJ_PERSONA_TEXT_INVALID")
    normalized = with_source_mode(candidate, "XIAOJ_LOCAL")
    return XiaoJCandidateEnvelope(
        persona_text=persona_text,
        governance_candidate=validate_candidate(normalized),
    )


__all__ = [
    "CommerceDomainAdapter",
    "CommunityDomainAdapter",
    "CompletionProvider",
    "DOMAINS",
    "DomainAdapter",
    "DomainCompletionError",
    "GovernanceCandidate",
    "InMemoryCompletionProvider",
    "POLICY_PATH",
    "PropertyDomainAdapter",
    "RUN_ID",
    "SCHEMA_PATH",
    "SCHEMA_VERSION",
    "SENSITIVITY_CLASSES",
    "SOURCE_MODES",
    "XiaoJCandidateEnvelope",
    "adapter_for",
    "build_candidate",
    "build_xiaoj_envelope",
    "calculate_candidate_hash",
    "canonical_json",
    "canonical_sha256",
    "deep_copy_json",
    "validate_candidate",
    "with_source_mode",
]
