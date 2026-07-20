#!/usr/bin/env python3
"""
NLP to D1 Intent Adapter for TRUE8D Architecture.

Natural language is treated only as untrusted observation input.
This module may construct a bounded candidate-fill request, but it grants
no execution authority and cannot commit a D1 state transition.
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import secrets
from typing import Any, cast
import unicodedata

from jsonschema import Draft202012Validator

from tools.total_field.xiaoj_member_bound_session_candidate import (
    canonical_sha256 as member_binding_sha256,
)
from tools.total_field_candidate_gateway import (
    receive_candidate as total_field_receive_candidate,
)
from tools.total_field_cloud_fill_packet import (
    RECEIVE_CANDIDATE_PATH,
    build_cloud_fill_request,
    validate_cloud_fill_request,
)
from tools.tfct_true8d_runtime_candidate import PriorityPolicy, load_policy
from tools.w7tp_small_agent_service_runner import project_d1_intent


ROOT = Path(__file__).resolve().parents[1]
MAX_NATURAL_LANGUAGE_LENGTH = 500
DEFAULT_PACKET_TTL_SECONDS = 600
ADAPTER_SCHEMA_VERSION = "W7TP-NLP-D1-INTENT-ADAPTER/1.0"
LOCAL_PROVIDER_REF = "provider_ref:ollama_local"
CLOUD_PROVIDER_REF = "provider_ref:openai_constrained"
D1_PROJECTOR_REF = "tools.w7tp_small_agent_service_runner.project_d1_intent"
ACCESS_PROFILE_PATH = ROOT / "configs/w7tp_member_llm_prefix_policy.example.json"
ROLE_POLICY_PATH = (
    ROOT / "manifests/xiaoj_member_bound_developer_seat_candidate_v0_1/policy.json"
)
LOCAL_ACCESS_PROFILE_KEY = "0_5B_BROWSER_LANGUAGE_PLANE"
SAFE_REF_PATTERN = re.compile(r"^[a-zA-Z0-9_][a-zA-Z0-9_.:-]{0,127}$")
MODEL_REF_PATTERN = re.compile(r"^[a-zA-Z0-9_][a-zA-Z0-9_.:/@-]{0,191}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
PROHIBITED_OUTPUTS = (
    "committed",
    "ALLOW",
    "TFS",
    "TFID",
    "canonical_pointer",
    "formal_hash",
    "credential",
    "member_plaintext",
)
PROTECTED_CONTEXT_KEYS = frozenset(
    {
        "access_token",
        "adi",
        "adc",
        "credential",
        "email",
        "h64_td",
        "member_plaintext",
        "name",
        "password",
        "private_key",
        "raw_token",
        "refresh_token",
        "secret",
        "session",
        "token",
    }
)
SENSITIVE_OBSERVATION_PATTERNS = (
    re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{8,}", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b(?:password|passwd|api[_-]?key|token)\s*[:=]\s*\S+", re.IGNORECASE),
)
CloudAuthorizationVerifier = Callable[[str], Mapping[str, Any]]


class NLPCompressionError(ValueError):
    """Raised when NLP input cannot be safely compressed into an intent."""

    def __init__(self, reason_code: str, path: str = "$") -> None:
        self.reason_code = reason_code
        self.path = path
        super().__init__(f"{reason_code}:{path}")


def _load_object(path: Path, error_code: str) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise NLPCompressionError(error_code) from exc
    if not isinstance(value, dict):
        raise NLPCompressionError(error_code)
    return value


def _deep_copy_json(value: Any, error_code: str) -> Any:
    try:
        return json.loads(
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise NLPCompressionError(error_code) from exc


def _contains_protected_context(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            str(key).strip().casefold().replace("-", "_") in PROTECTED_CONTEXT_KEYS
            or _contains_protected_context(nested)
            for key, nested in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_protected_context(item) for item in value)
    return False


def _normalize_natural_language(value: str) -> str:
    if not isinstance(value, str):
        raise NLPCompressionError("HOLD_NATURAL_LANGUAGE_INPUT_NOT_STRING")

    normalized = unicodedata.normalize("NFKC", value)

    normalized = "".join(
        " " if unicodedata.category(char) in {"Cc", "Cf", "Cn", "Co", "Cs"} else char
        for char in normalized
    )

    normalized = " ".join(normalized.split())

    if not normalized:
        raise NLPCompressionError("HOLD_EMPTY_NATURAL_LANGUAGE_INPUT")

    if len(normalized) > MAX_NATURAL_LANGUAGE_LENGTH:
        raise NLPCompressionError("HOLD_NATURAL_LANGUAGE_INPUT_TOO_LONG")

    if any(pattern.search(normalized) for pattern in SENSITIVE_OBSERVATION_PATTERNS):
        raise NLPCompressionError("HOLD_PROTECTED_OBSERVATION_BOUNDARY")

    return normalized


def _normalize_intent_scope(values: Sequence[str]) -> list[str]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise NLPCompressionError("HOLD_INVALID_ALLOWED_INTENT_SCOPE")

    normalized: list[str] = []

    for value in values:
        if not isinstance(value, str):
            raise NLPCompressionError("HOLD_NON_STRING_ALLOWED_INTENT")

        intent = value.strip()
        if not intent:
            raise NLPCompressionError("HOLD_EMPTY_ALLOWED_INTENT")
        if intent.casefold() in {item.casefold() for item in PROHIBITED_OUTPUTS}:
            raise NLPCompressionError("HOLD_AUTHORITY_INTENT_FORBIDDEN")

        if intent not in normalized:
            normalized.append(intent)

    if not normalized:
        raise NLPCompressionError("HOLD_EMPTY_ALLOWED_INTENT_SCOPE")
    if len(normalized) > 64:
        raise NLPCompressionError("HOLD_ALLOWED_INTENT_SCOPE_TOO_LARGE")

    return normalized


def _normalize_model_refs(values: Sequence[str], error_code: str) -> list[str]:
    normalized = _normalize_intent_scope(values)
    if any(MODEL_REF_PATTERN.fullmatch(item) is None for item in normalized):
        raise NLPCompressionError(error_code)
    return normalized


def _require_safe_reference(value: str, error_code: str) -> str:
    if not isinstance(value, str) or not SAFE_REF_PATTERN.fullmatch(value):
        raise NLPCompressionError(error_code)

    return value


def _require_sha256(value: Any, error_code: str) -> str:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        raise NLPCompressionError(error_code)
    return value


def _validate_context_fragments(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise NLPCompressionError("HOLD_CONTEXT_FRAGMENT_SEQUENCE_REQUIRED")
    if len(values) > 14:
        raise NLPCompressionError("HOLD_CONTEXT_FRAGMENT_LIMIT_EXCEEDED")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, value in enumerate(values):
        if not isinstance(value, Mapping) or set(value) != {"ref", "sha256", "role"}:
            raise NLPCompressionError(
                "HOLD_CONTEXT_FRAGMENT_SCHEMA_INVALID", f"$.context_fragments[{index}]"
            )
        ref = _require_safe_reference(
            cast(str, value.get("ref")), "HOLD_CONTEXT_FRAGMENT_REF_INVALID"
        )
        if ref in seen:
            raise NLPCompressionError("HOLD_CONTEXT_FRAGMENT_DUPLICATE")
        if value.get("role") != "DATA_NOT_GOVERNANCE_INSTRUCTION":
            raise NLPCompressionError("HOLD_CONTEXT_FRAGMENT_ROLE_INVALID")
        normalized.append(
            {
                "ref": ref,
                "sha256": _require_sha256(
                    value.get("sha256"), "HOLD_CONTEXT_FRAGMENT_HASH_INVALID"
                ),
                "role": "DATA_NOT_GOVERNANCE_INSTRUCTION",
            }
        )
        seen.add(ref)
    return normalized


def _load_access_profile() -> dict[str, Any]:
    policy = _load_object(ACCESS_PROFILE_PATH, "HOLD_LLM_ACCESS_PROFILE_UNAVAILABLE")
    persona = policy.get("canonical_persona")
    profiles = policy.get("prefix_profiles")
    if not isinstance(persona, Mapping) or not isinstance(profiles, Mapping):
        raise NLPCompressionError("HOLD_LLM_ACCESS_PROFILE_INVALID")
    profile = profiles.get(LOCAL_ACCESS_PROFILE_KEY)
    if not isinstance(profile, Mapping):
        raise NLPCompressionError("HOLD_LLM_ACCESS_PROFILE_NOT_FOUND")
    allowed = profile.get("allowed")
    denied = profile.get("denied")
    if (
        persona.get("canonical_name") != "XiaoJ"
        or persona.get("authority") != "candidate_only"
        or persona.get("requires_total_field_verify") is not True
        or persona.get("final_decision") is not False
        or not isinstance(allowed, list)
        or "intent_extract" not in allowed
        or not isinstance(denied, list)
        or not {"db_write", "final_decision", "secret_read", "member_plaintext_persist"}
        <= set(denied)
    ):
        raise NLPCompressionError("HOLD_LLM_ACCESS_PROFILE_AUTHORITY_INVALID")
    source_sha256 = hashlib.sha256(ACCESS_PROFILE_PATH.read_bytes()).hexdigest()
    return {
        "profile_ref": f"profile_ref:{LOCAL_ACCESS_PROFILE_KEY}",
        "profile_key": LOCAL_ACCESS_PROFILE_KEY,
        "source_ref": "source_ref:configs:w7tp_member_llm_prefix_policy:p1",
        "source_sha256": source_sha256,
        "authority": "candidate_only",
        "requires_total_field_verify": True,
        "allowed": list(allowed),
        "denied": list(denied),
    }


def _validate_sovereign_ai_binding(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or _contains_protected_context(value):
        raise NLPCompressionError("HOLD_SOVEREIGN_AI_BINDING_INVALID")
    copied = _deep_copy_json(dict(value), "HOLD_SOVEREIGN_AI_BINDING_INVALID")
    if not isinstance(copied, dict):
        raise NLPCompressionError("HOLD_SOVEREIGN_AI_BINDING_INVALID")
    supplied_hash = _require_sha256(
        copied.get("result_sha256"), "HOLD_SOVEREIGN_AI_ASSIGNMENT_HASH_INVALID"
    )
    unsigned = dict(copied)
    unsigned.pop("result_sha256")
    if member_binding_sha256(unsigned) != supplied_hash:
        raise NLPCompressionError("HOLD_SOVEREIGN_AI_ASSIGNMENT_HASH_MISMATCH")
    if (
        copied.get("state") != "PASS_MEMBER_BOUND_CANDIDATE"
        or copied.get("candidate_only") is not True
        or copied.get("role_activated") is not False
        or copied.get("final_authority") is not False
        or copied.get("d7_disposition") != "PASS"
    ):
        raise NLPCompressionError("HOLD_SOVEREIGN_AI_BINDING_NOT_VERIFIED")
    envelope = copied.get("d8_capability_envelope_candidate")
    operation = copied.get("operation_record")
    if not isinstance(envelope, Mapping) or not isinstance(operation, Mapping):
        raise NLPCompressionError("HOLD_SOVEREIGN_AI_BINDING_ENVELOPE_INVALID")
    role_policy = _load_object(ROLE_POLICY_PATH, "HOLD_XIAOJ_ROLE_POLICY_UNAVAILABLE")
    seat = role_policy.get("founder_developer_seat")
    if not isinstance(seat, Mapping):
        raise NLPCompressionError("HOLD_XIAOJ_ROLE_POLICY_INVALID")
    principal_ref = _require_safe_reference(
        cast(str, envelope.get("member_ref")), "HOLD_XIAOJ_PRINCIPAL_REF_INVALID"
    )
    xiaoj_agent_ref = _require_safe_reference(
        cast(str, envelope.get("xiaoj_agent_ref")), "HOLD_XIAOJ_AGENT_REF_INVALID"
    )
    effective_roles = envelope.get("effective_member_roles")
    capability_refs = envelope.get("capability_refs")
    if (
        principal_ref != seat.get("principal_ref")
        or not isinstance(effective_roles, list)
        or seat.get("role_ref") not in effective_roles
        or not isinstance(capability_refs, list)
        or set(capability_refs) != set(seat.get("permissions", []))
        or envelope.get("final_decision") is not None
        or envelope.get("requires_total_field_verify") is not True
        or operation.get("principal") != principal_ref
        or operation.get("actor") != xiaoj_agent_ref
    ):
        raise NLPCompressionError("HOLD_XIAOJ_ROLE_SEAT_BINDING_MISMATCH")
    evidence = operation.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise NLPCompressionError("HOLD_XIAOJ_BINDING_EVIDENCE_REQUIRED")
    evidence_refs = [
        _require_safe_reference(item, "HOLD_XIAOJ_BINDING_EVIDENCE_REF_INVALID")
        for item in evidence
    ]
    return {
        "principal_ref": principal_ref,
        "xiaoj_agent_ref": xiaoj_agent_ref,
        "role_seat_ref": cast(str, seat["role_ref"]),
        "assignment_sha256": supplied_hash,
        "delegation_ref": _require_safe_reference(
            cast(str, envelope.get("delegation_ref")),
            "HOLD_XIAOJ_DELEGATION_REF_INVALID",
        ),
        "verification_evidence_refs": evidence_refs,
        "candidate_only": True,
        "role_activated": False,
        "requires_total_field_verify": True,
    }


def _verify_cloud_authorization(
    evidence_ref: str,
    verifier: CloudAuthorizationVerifier | None,
) -> None:
    evidence_ref = _require_safe_reference(
        evidence_ref, "HOLD_INVALID_CLOUD_AUTHORIZATION_EVIDENCE_REF"
    )
    if verifier is None:
        raise NLPCompressionError("HOLD_CLOUD_AUTHORIZATION_VERIFIER_REQUIRED")
    try:
        result = verifier(evidence_ref)
    except Exception as exc:
        raise NLPCompressionError("HOLD_CLOUD_AUTHORIZATION_VERIFICATION_FAILED") from exc
    if (
        not isinstance(result, Mapping)
        or result.get("decision") != "ALLOW"
        or result.get("evidence_ref") != evidence_ref
        or result.get("scope") != "CLOUD_CANDIDATE_LANE"
        or result.get("candidate_only") is not True
    ):
        raise NLPCompressionError("HOLD_CLOUD_AUTHORIZATION_NOT_ALLOWED")


def _intent_output_schema(allowed_intents: Sequence[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "required": ["decision", "proposed_d1_intent"],
        "properties": {
            "decision": {
                "type": "string",
                "enum": ["PROPOSE_INTENT", "HOLD_UNKNOWN_INTENT"],
            },
            "proposed_d1_intent": {
                "type": ["string", "null"],
                "enum": [*allowed_intents, None],
            },
        },
        "additionalProperties": False,
        "allOf": [
            {
                "if": {
                    "properties": {"decision": {"const": "HOLD_UNKNOWN_INTENT"}},
                    "required": ["decision"],
                },
                "then": {
                    "properties": {"proposed_d1_intent": {"type": "null"}}
                },
            },
            {
                "if": {
                    "properties": {"decision": {"const": "PROPOSE_INTENT"}},
                    "required": ["decision"],
                },
                "then": {
                    "properties": {"proposed_d1_intent": {"type": "string"}}
                },
            },
        ],
    }


def prepare_intent_extraction_packet(
    raw_natural_language: str,
    packet_id: str,
    target_state_coordinate: str,
    allowed_intent_scope: Sequence[str],
    requester_d3_coordinate: str,
    *,
    local_model_refs: Sequence[str],
    sovereign_ai_binding: Mapping[str, Any],
    expected_xiaoj_agent_ref: str,
    expected_assignment_sha256: str,
    context_provenance_ref: str,
    context_logical_time: str,
    member_boundary_ref: str,
    authorized_context_fragments: Sequence[Mapping[str, Any]] = (),
    cloud_fill_authorized: bool = False,
    cloud_model_refs: Sequence[str] = (),
    cloud_authorization_evidence_ref: str | None = None,
    cloud_authorization_verifier: CloudAuthorizationVerifier | None = None,
    ttl_seconds: int = DEFAULT_PACKET_TTL_SECONDS,
    return_coordinate: str = "taiji01:d8_inbox",
    nonce_factory: Callable[[], str] = lambda: secrets.token_hex(32),
    consumed_nonces: Collection[str] = (),
) -> dict[str, Any]:
    """
    Construct a bounded D1 intent-candidate request.

    This function does not call a model, execute an action, confirm an intent,
    or commit a Total Field state transition.
    """

    packet_id = _require_safe_reference(packet_id, "HOLD_INVALID_PACKET_ID")
    target_state_coordinate = _require_safe_reference(
        target_state_coordinate, "HOLD_INVALID_TARGET_STATE_COORDINATE"
    )
    requester_d3_coordinate = _require_safe_reference(
        requester_d3_coordinate, "HOLD_INVALID_REQUESTER_D3_COORDINATE"
    )
    return_coordinate = _require_safe_reference(
        return_coordinate, "HOLD_INVALID_RETURN_COORDINATE"
    )
    context_provenance_ref = _require_safe_reference(
        context_provenance_ref, "HOLD_INVALID_CONTEXT_PROVENANCE_REF"
    )
    context_logical_time = _require_safe_reference(
        context_logical_time, "HOLD_INVALID_CONTEXT_LOGICAL_TIME"
    )
    member_boundary_ref = _require_safe_reference(
        member_boundary_ref, "HOLD_INVALID_MEMBER_BOUNDARY_REF"
    )
    expected_xiaoj_agent_ref = _require_safe_reference(
        expected_xiaoj_agent_ref, "HOLD_INVALID_EXPECTED_XIAOJ_AGENT_REF"
    )
    expected_assignment_sha256 = _require_sha256(
        expected_assignment_sha256, "HOLD_INVALID_EXPECTED_ASSIGNMENT_HASH"
    )

    if not isinstance(ttl_seconds, int) or isinstance(ttl_seconds, bool) or not 1 <= ttl_seconds <= 900:
        raise NLPCompressionError("HOLD_INVALID_PACKET_TTL")

    sanitized_text = _normalize_natural_language(raw_natural_language)
    normalized_scope = _normalize_intent_scope(allowed_intent_scope)
    normalized_local_models = _normalize_model_refs(
        local_model_refs, "HOLD_INVALID_LOCAL_MODEL_REF"
    )
    binding = _validate_sovereign_ai_binding(sovereign_ai_binding)
    if binding["xiaoj_agent_ref"] != expected_xiaoj_agent_ref:
        raise NLPCompressionError("HOLD_XIAOJ_IMPERSONATION")
    if binding["assignment_sha256"] != expected_assignment_sha256:
        raise NLPCompressionError("HOLD_XIAOJ_ASSIGNMENT_HASH_MISMATCH")
    access_profile = _load_access_profile()
    context_fragments = _validate_context_fragments(authorized_context_fragments)

    allowed_provider_refs = [LOCAL_PROVIDER_REF]
    allowed_model_refs = list(normalized_local_models)
    evidence_refs = list(binding["verification_evidence_refs"])

    if cloud_fill_authorized:
        if not cloud_authorization_evidence_ref:
            raise NLPCompressionError("HOLD_MISSING_CLOUD_AUTHORIZATION_EVIDENCE")
        _verify_cloud_authorization(
            cloud_authorization_evidence_ref, cloud_authorization_verifier
        )
        normalized_cloud_models = _normalize_model_refs(
            cloud_model_refs, "HOLD_INVALID_CLOUD_MODEL_REF"
        )
        if set(normalized_local_models).intersection(normalized_cloud_models):
            raise NLPCompressionError("HOLD_PROVIDER_MODEL_LANE_DRIFT")
        allowed_provider_refs.append(CLOUD_PROVIDER_REF)
        allowed_model_refs.extend(normalized_cloud_models)
        evidence_refs.append(cloud_authorization_evidence_ref)
    elif (
        cloud_model_refs
        or cloud_authorization_evidence_ref
        or cloud_authorization_verifier is not None
    ):
        raise NLPCompressionError(
            "HOLD_CLOUD_CONFIGURATION_WITHOUT_EXPLICIT_AUTHORIZATION"
        )

    nonce = nonce_factory()
    if not isinstance(nonce, str) or not 16 <= len(nonce) <= 256:
        raise NLPCompressionError("HOLD_INVALID_PACKET_NONCE")
    if nonce in consumed_nonces:
        raise NLPCompressionError("HOLD_NONCE_REPLAY")

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=ttl_seconds)
    output_schema = _intent_output_schema(normalized_scope)
    product_output_contract = {
        "domain": "INTENT_EXTRACTION",
        "entity_ref": target_state_coordinate,
        "attribute_name": "proposed_d1_intent",
        "event_ref": f"event_ref:{packet_id}",
        "rule_ref": "rule_ref:strict_intent_mapping",
        "observation_domain_ref": "observation_domain:human_interface",
        "requires_human_confirmation": True,
        "candidate_only": True,
        "execution_authority": False,
        "sensitivity": "HIGH",
        "allowed_side_effects": "NONE",
        "prohibited_outputs": list(PROHIBITED_OUTPUTS),
        "output_schema": output_schema,
        "d1_projector_ref": D1_PROJECTOR_REF,
    }
    assignment_fragments = [
        {
            "ref": "state_fragment:sovereign_ai_xiaoj_assignment",
            "sha256": binding["assignment_sha256"],
            "role": "DATA_NOT_GOVERNANCE_INSTRUCTION",
        },
        {
            "ref": "state_fragment:llm_identity_access_profile",
            "sha256": access_profile["source_sha256"],
            "role": "DATA_NOT_GOVERNANCE_INSTRUCTION",
        },
    ]
    dynamic_rule = {
        "applicable_rule_refs": ["rule_ref:strict_intent_mapping"],
        "intent_delta": "MAP_UNTRUSTED_OBSERVATION_TO_ONE_ALLOWED_D1_INTENT",
        "necessary_state_fragments": assignment_fragments,
        "retrieved_context": context_fragments,
        "acceptance_refs": [
            "acceptance_ref:exact_allowed_intent_or_hold_unknown"
        ],
        "instruction": (
            "Classify the observation into exactly one allowed intent. "
            "Do not infer actions, parameters, authorization or execution "
            "authority. Return HOLD_UNKNOWN_INTENT when no exact mapping exists."
        ),
        "allowed_intents": normalized_scope,
        "fallback_action": "HOLD_UNKNOWN_INTENT",
        "output_schema": output_schema,
    }

    relationship_refs = [
        requester_d3_coordinate,
        binding["xiaoj_agent_ref"],
        binding["role_seat_ref"],
        access_profile["profile_ref"],
        member_boundary_ref,
        context_provenance_ref,
        context_logical_time,
    ]
    resource_refs = [
        access_profile["source_ref"],
        "source_ref:manifests:xiaoj_member_bound_developer_seat_policy:v1",
    ]

    transport_product_output_contract = {
        "domain": "COMMUNITY",
        "entity_ref": target_state_coordinate,
        "attribute_name": "proposed_d1_intent",
        "event_ref": f"event_ref:{packet_id}",
        "rule_ref": "rule_ref:strict_intent_mapping",
        "observation_domain_ref": "observation_domain:human_interface",
        "requires_human_confirmation": True,
        "sensitivity": "OWNER_CONFIRMATION_REQUIRED",
    }
    transport_dynamic_rule = {
        "applicable_rule_refs": ["rule_ref:strict_intent_mapping"],
        "intent_delta": "MAP_UNTRUSTED_OBSERVATION_TO_ONE_ALLOWED_D1_INTENT",
        "necessary_state_fragments": assignment_fragments,
        "retrieved_context": context_fragments,
        "acceptance_refs": [
            "acceptance_ref:exact_allowed_intent_or_hold_unknown"
        ],
    }
    cloud_fill_request = cast(
        dict[str, Any],
        build_cloud_fill_request(
            packet_id=packet_id,
            question_type_ref="INTENT_MAPPING_V1",
            sanitized_question=sanitized_text,
            product_output_contract=transport_product_output_contract,
            dynamic_rule_projection=transport_dynamic_rule,
            allowed_information_scope=normalized_scope,
            state_coordinate=target_state_coordinate,
            relationship_refs=relationship_refs,
            resource_refs=resource_refs,
            reconstruction_conditions={
                "condition_refs": [
                    "condition_ref:exact_intent_match",
                    "condition_ref:candidate_only",
                    "condition_ref:execution_forbidden",
                    "condition_ref:human_confirmation_before_commit",
                ],
                "version": "1.0",
            },
            equivalent_candidate_state_rules=[
                "equivalence_ref:exact_schema_match",
                "equivalence_ref:enum_value_match",
                "equivalence_ref:no_additional_properties",
            ],
            verification_conditions={
                "condition_refs": [
                    "condition_ref:d8_consensus_required",
                    "condition_ref:local_schema_validation_required",
                    "condition_ref:human_confirmation_required",
                    "condition_ref:execution_authority_false",
                ],
                "version": "1.0",
            },
            evidence_refs=evidence_refs,
            allowed_provider_refs=allowed_provider_refs,
            allowed_model_refs=allowed_model_refs,
            nonce=nonce,
            expires_at=expires_at.isoformat().replace("+00:00", "Z"),
            return_coordinate=return_coordinate,
        ),
    )
    return {
        "schema_version": ADAPTER_SCHEMA_VERSION,
        "packet_type": "NLP_D1_INTENT_ADAPTER_CANDIDATE_REQUEST",
        "candidate_only": True,
        "execution_authority": False,
        "requires_human_confirmation": True,
        "authoritative_source_preserved": True,
        "product_output_contract": product_output_contract,
        "dynamic_rule_projection": dynamic_rule,
        "sovereign_ai_binding": {
            "xiaoj_agent_ref": binding["xiaoj_agent_ref"],
            "role_seat_ref": binding["role_seat_ref"],
            "assignment_sha256": binding["assignment_sha256"],
            "candidate_only": True,
            "role_activated": False,
        },
        "llm_identity_access_profile": {
            "profile_ref": access_profile["profile_ref"],
            "profile_source_sha256": access_profile["source_sha256"],
            "authority": access_profile["authority"],
            "requires_total_field_verify": True,
        },
        "lane_bindings": {
            "local_candidate_lane": {
                "enabled": True,
                "provider_ref": LOCAL_PROVIDER_REF,
                "model_refs": normalized_local_models,
                "candidate_only": True,
            },
            "cloud_candidate_lane": {
                "enabled": cloud_fill_authorized,
                "provider_ref": CLOUD_PROVIDER_REF,
                "model_refs": (
                    normalized_cloud_models if cloud_fill_authorized else []
                ),
                "authorization_evidence_ref": cloud_authorization_evidence_ref,
                "candidate_only": True,
            },
        },
        "d1_projector_ref": D1_PROJECTOR_REF,
        "receive_candidate_ref": RECEIVE_CANDIDATE_PATH,
        "cloud_fill_request": cloud_fill_request,
    }


def validate_intent_candidate_response(
    packet: Mapping[str, Any],
    response: Mapping[str, Any],
    *,
    lane: str,
    provider_ref: str,
    model_ref: str,
) -> dict[str, Any]:
    """Validate one lane-bound model result locally before candidate intake."""

    if (
        not isinstance(packet, Mapping)
        or packet.get("schema_version") != ADAPTER_SCHEMA_VERSION
        or packet.get("packet_type") != "NLP_D1_INTENT_ADAPTER_CANDIDATE_REQUEST"
        or packet.get("candidate_only") is not True
        or packet.get("execution_authority") is not False
        or packet.get("requires_human_confirmation") is not True
        or packet.get("d1_projector_ref") != D1_PROJECTOR_REF
        or packet.get("receive_candidate_ref") != RECEIVE_CANDIDATE_PATH
    ):
        raise NLPCompressionError("HOLD_INTENT_ADAPTER_PACKET_INVALID")
    cloud_fill_request = packet.get("cloud_fill_request")
    if not isinstance(cloud_fill_request, Mapping):
        raise NLPCompressionError("HOLD_CLOUD_FILL_REQUEST_MISSING")
    validated_packet = validate_cloud_fill_request(cloud_fill_request)
    locked = cast(dict[str, Any], validated_packet["locked"])
    lane = str(lane).upper()
    expected_provider = {
        "LOCAL": LOCAL_PROVIDER_REF,
        "CLOUD": CLOUD_PROVIDER_REF,
    }.get(lane)
    if expected_provider is None:
        raise NLPCompressionError("HOLD_CANDIDATE_LANE_INVALID")
    if provider_ref != expected_provider:
        raise NLPCompressionError("HOLD_PROVIDER_LANE_DRIFT")
    if provider_ref not in locked["allowed_provider_refs"]:
        raise NLPCompressionError("HOLD_PROVIDER_NOT_AUTHORIZED")
    if model_ref not in locked["allowed_model_refs"]:
        raise NLPCompressionError("HOLD_MODEL_NOT_AUTHORIZED")
    if lane == "CLOUD" and CLOUD_PROVIDER_REF not in locked["allowed_provider_refs"]:
        raise NLPCompressionError("HOLD_CLOUD_CANDIDATE_LANE_NOT_AUTHORIZED")
    copied = _deep_copy_json(dict(response), "HOLD_INTENT_CANDIDATE_JSON_INVALID")
    if not isinstance(copied, dict) or _contains_protected_context(copied):
        raise NLPCompressionError("HOLD_INTENT_CANDIDATE_BOUNDARY")
    contract = packet.get("product_output_contract")
    if not isinstance(contract, dict):
        raise NLPCompressionError("HOLD_INTENT_OUTPUT_CONTRACT_MISSING")
    schema = contract.get("output_schema")
    if not isinstance(schema, dict):
        raise NLPCompressionError("HOLD_INTENT_OUTPUT_SCHEMA_MISSING")
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        raise NLPCompressionError("HOLD_INTENT_OUTPUT_SCHEMA_INVALID") from exc
    errors = sorted(
        Draft202012Validator(schema).iter_errors(copied),
        key=lambda item: ([str(part) for part in item.absolute_path], item.message),
    )
    if errors:
        path = "$"
        for part in errors[0].absolute_path:
            path += f"[{part}]" if isinstance(part, int) else f".{part}"
        raise NLPCompressionError("HOLD_INTENT_CANDIDATE_SCHEMA_INVALID", path)
    return copied


def project_intent_candidate_to_d1(
    packet: Mapping[str, Any],
    response: Mapping[str, Any],
    *,
    lane: str,
    provider_ref: str,
    model_ref: str,
    task_ref: str,
    goal_ref: str,
) -> dict[str, Any]:
    """Project one validated proposal with the existing repo-native D1 projector."""

    candidate = validate_intent_candidate_response(
        packet,
        response,
        lane=lane,
        provider_ref=provider_ref,
        model_ref=model_ref,
    )
    if candidate["decision"] == "HOLD_UNKNOWN_INTENT":
        return {
            "state": "HOLD_UNKNOWN_INTENT",
            "candidate_only": True,
            "execution_authority": False,
            "d1_projection": None,
            "receive_candidate_ref": RECEIVE_CANDIDATE_PATH,
        }
    proposed = cast(str, candidate["proposed_d1_intent"])
    projection = project_d1_intent(
        {
            "intent_ref": proposed,
            "task_ref": _require_safe_reference(task_ref, "HOLD_INVALID_TASK_REF"),
            "goal_ref": _require_safe_reference(goal_ref, "HOLD_INVALID_GOAL_REF"),
        }
    )
    return {
        "state": "D1_INTENT_CANDIDATE_PROJECTED",
        "candidate_only": True,
        "execution_authority": False,
        "requires_human_confirmation": True,
        "lane": str(lane).upper(),
        "provider_ref": provider_ref,
        "model_ref": model_ref,
        "d1_projector_ref": D1_PROJECTOR_REF,
        "receive_candidate_ref": RECEIVE_CANDIDATE_PATH,
        "d1_projection": projection,
    }


def _human_confirmation_policy() -> PriorityPolicy:
    policy = load_policy()
    return replace(
        policy,
        sensitive_key_names=tuple(
            sorted(
                frozenset(policy.sensitive_key_names)
                | {"human_confirmation_required"}
            )
        ),
    )


def receive_projected_intent_candidate(
    projected_candidate: Mapping[str, Any],
    gateway_candidate_payload: Mapping[str, Any],
    *,
    previous_state: Mapping[str, Any],
    observation_domains: Mapping[str, Any],
) -> dict[str, Any]:
    """Send one projected candidate only through the existing Total Field receiver."""

    if (
        not isinstance(projected_candidate, Mapping)
        or projected_candidate.get("state") != "D1_INTENT_CANDIDATE_PROJECTED"
        or projected_candidate.get("candidate_only") is not True
        or projected_candidate.get("execution_authority") is not False
        or projected_candidate.get("requires_human_confirmation") is not True
    ):
        raise NLPCompressionError("HOLD_PROJECTED_D1_CANDIDATE_INVALID")
    request = _deep_copy_json(
        dict(gateway_candidate_payload), "HOLD_GATEWAY_CANDIDATE_JSON_INVALID"
    )
    if not isinstance(request, dict) or _contains_protected_context(request):
        raise NLPCompressionError("HOLD_GATEWAY_CANDIDATE_BOUNDARY")
    fields = request.get("resolved_fields")
    if (
        not isinstance(fields, dict)
        or fields.get("D1") != projected_candidate.get("d1_projection")
    ):
        raise NLPCompressionError("HOLD_D1_PROJECTOR_BINDING_MISMATCH")
    context = request.get("context")
    if not isinstance(context, dict):
        raise NLPCompressionError("HOLD_GATEWAY_CONTEXT_INVALID")
    context["human_confirmation_required"] = True
    lane = projected_candidate.get("lane")
    request["source_mode"] = "TOTAL_FIELD_PULL" if lane == "LOCAL" else "LLM_PUSH"
    if lane == "CLOUD":
        request["candidate_only"] = True
    result = total_field_receive_candidate(
        request,
        previous_state=previous_state,
        observation_domains=observation_domains,
        policy=_human_confirmation_policy(),
    )
    if result.get("final_decision") != "HOLD" or result.get("commit_applied") is not False:
        raise NLPCompressionError("BLOCK_HUMAN_CONFIRMATION_GATE_BYPASS")
    return cast(dict[str, Any], result)


__all__ = [
    "CLOUD_PROVIDER_REF",
    "D1_PROJECTOR_REF",
    "DEFAULT_PACKET_TTL_SECONDS",
    "LOCAL_ACCESS_PROFILE_KEY",
    "LOCAL_PROVIDER_REF",
    "MAX_NATURAL_LANGUAGE_LENGTH",
    "NLPCompressionError",
    "PROHIBITED_OUTPUTS",
    "prepare_intent_extraction_packet",
    "project_intent_candidate_to_d1",
    "receive_projected_intent_candidate",
    "validate_intent_candidate_response",
]
