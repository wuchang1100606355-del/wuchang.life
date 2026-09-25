#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Single candidate ingress for TOTAL_FIELD_PULL and LLM_PUSH.

Candidate Source is never authority: both wrappers set only ``source_mode`` and
then call :func:`receive_candidate`.  The gateway validates 8D-GTE data,
resolves a caller-supplied Observation Domain, runs the existing TRUE8D
candidate core, and emits authority-owned result metadata without side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, cast

from jsonschema import Draft202012Validator, RefResolver
from jsonschema.exceptions import ValidationError

from tools.eightd_gte_parser_candidate import (
    EightDGTEParserCandidate,
    GTECandidateParseError,
)
from tools.tfct_true8d_runtime_candidate import (
    DEFAULT_POLICY_PATH,
    EightFieldState,
    Event,
    JSONValue,
    ObservationDomain,
    PriorityPolicy,
    RuntimeCandidateError,
    deep_copy_json,
    load_policy,
    run_convergence,
)


ROOT = Path(__file__).resolve().parents[1]
PROFILE_SCHEMA_VERSION = "8d-gte-runtime-candidate-profile/0.1"
PROFILE_SCHEMA_PATH = (
    ROOT / "schemas/field/8d_gte_runtime_candidate_profile_v0_1.schema.json"
)
BASE_GTE_SCHEMA_PATH = (
    ROOT / "schemas/field/8d_governance_tensor_expression_candidate.schema.json"
)
SOURCE_MODES = frozenset({"TOTAL_FIELD_PULL", "LLM_PUSH"})
AUTHORITY_RESULT_KEYS = frozenset({"committed", "tfid", "total_field_hash"})
CLOUD_AUTHORITY_RESULT_KEYS = frozenset(
    {"committed", "commit_applied", "tfid", "total_field_hash"}
)
RESERVED_CONTEXT_KEYS = frozenset(
    {
        "adi_fixture",
        "adi_result",
        "gateway_projection_reason_code",
        "gateway_projection_status",
        "test_fixture",
        "test_only",
    }
)


class TotalFieldGatewayError(ValueError):
    """One stable gateway rejection without caller payload disclosure."""

    def __init__(self, reason_code: str, path: str = "$") -> None:
        """Initialize one stable code and structural path only."""

        self.reason_code = reason_code
        self.path = path
        super().__init__(f"{reason_code}:{path}")


def _copy_mapping(value: Mapping[str, Any], path: str) -> dict[str, JSONValue]:
    """Return a validated detached JSON object."""

    if not isinstance(value, Mapping):
        raise TotalFieldGatewayError("GATEWAY_MAPPING_REQUIRED", path)
    copied = deep_copy_json(dict(value))
    if not isinstance(copied, dict):
        raise TotalFieldGatewayError("GATEWAY_MAPPING_REQUIRED", path)
    return copied


def _load_schema(path: Path) -> dict[str, Any]:
    """Load one checked JSON schema through the deterministic parser decoder."""

    try:
        import json

        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (OSError, UnicodeError, ValueError) as exc:
        raise TotalFieldGatewayError("GATEWAY_SCHEMA_READ_FAILED", str(path)) from exc
    if not isinstance(value, dict):
        raise TotalFieldGatewayError("GATEWAY_SCHEMA_NOT_OBJECT", str(path))
    try:
        Draft202012Validator.check_schema(value)
    except Exception as exc:
        raise TotalFieldGatewayError("GATEWAY_SCHEMA_INVALID", str(path)) from exc
    return value


def _absolutize_local_refs(value: Any, base_id: str) -> Any:
    """Rewrite local refs for the repository's legacy jsonschema resolver."""

    if isinstance(value, dict):
        rewritten: dict[str, Any] = {}
        for key, nested in value.items():
            if key == "$ref" and isinstance(nested, str) and nested.startswith("#/"):
                rewritten[key] = base_id + nested
            else:
                rewritten[key] = _absolutize_local_refs(nested, base_id)
        return rewritten
    if isinstance(value, list):
        return [_absolutize_local_refs(item, base_id) for item in value]
    return value


def _profile_validator(
    profile_schema_path: Path = PROFILE_SCHEMA_PATH,
    base_gte_schema_path: Path = BASE_GTE_SCHEMA_PATH,
) -> Draft202012Validator:
    """Build a fresh validator with the base 8D-GTE schema registered by ID."""

    profile = _load_schema(profile_schema_path)
    base = _load_schema(base_gte_schema_path)
    base_id = base.get("$id")
    if not isinstance(base_id, str) or not base_id:
        raise TotalFieldGatewayError("GATEWAY_BASE_SCHEMA_ID_MISSING")
    resolvable_base = _absolutize_local_refs(base, base_id)
    resolver = RefResolver.from_schema(profile, store={base_id: resolvable_base})
    return Draft202012Validator(profile, resolver=resolver)


def _error_path(error: ValidationError) -> str:
    """Render a stable dotted path for a profile validation error."""

    path = "$"
    for part in error.absolute_path:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


def _validate_profile(
    payload: Mapping[str, Any],
    *,
    validator: Draft202012Validator,
    expected_type: str,
) -> None:
    """Validate one closed runtime profile and report only its first error."""

    if payload.get("profile_type") != expected_type:
        raise TotalFieldGatewayError("GATEWAY_PROFILE_TYPE_MISMATCH", "$.profile_type")
    errors = sorted(
        validator.iter_errors(dict(payload)),
        key=lambda item: ([str(part) for part in item.absolute_path], item.message),
    )
    if errors:
        raise TotalFieldGatewayError("GATEWAY_PROFILE_INVALID", _error_path(errors[0]))


def _authority_claim_path(value: JSONValue, path: str = "$") -> str | None:
    """Find an external attempt to supply a Total Field-owned result."""

    if isinstance(value, dict):
        for key in sorted(value):
            nested = value[key]
            normalized = key.casefold()
            child = f"{path}.{key}"
            if normalized in AUTHORITY_RESULT_KEYS:
                return child
            if normalized == "commit_applied" and nested is True:
                return child
            if normalized == "final_decision" and nested == "ALLOW":
                return child
            found = _authority_claim_path(nested, child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found = _authority_claim_path(nested, f"{path}[{index}]")
            if found is not None:
                return found
    return None


def _cloud_authority_claim_path(value: JSONValue, path: str = "$") -> str | None:
    """Find any LLM_PUSH field reserved to Total Field authority."""

    if isinstance(value, dict):
        for key in sorted(value):
            child = f"{path}.{key}"
            if key.casefold() in CLOUD_AUTHORITY_RESULT_KEYS:
                schema_declaration = (
                    child == "$.gte.verification.commit_applied"
                    and value[key] is False
                )
                if not schema_declaration:
                    return child
            found = _cloud_authority_claim_path(value[key], child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found = _cloud_authority_claim_path(nested, f"{path}[{index}]")
            if found is not None:
                return found
    return None


def _trusted_context_claim_path(
    value: JSONValue, path: str = "$.context"
) -> str | None:
    """Find recursive attempts to forge gateway- or policy-owned context."""

    if isinstance(value, dict):
        for key in sorted(value):
            child = f"{path}.{key}"
            if key.casefold() in RESERVED_CONTEXT_KEYS:
                return child
            found = _trusted_context_claim_path(value[key], child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found = _trusted_context_claim_path(nested, f"{path}[{index}]")
            if found is not None:
                return found
    return None


def _resolve_observation_domain(
    observation_domain_ref: str,
    observation_domains: Mapping[str, Any],
) -> ObservationDomain:
    """Resolve one opaque ref or return an executable unconfigured domain."""

    registry = _copy_mapping(observation_domains, "$.observation_domains")
    resolved = registry.get(observation_domain_ref)
    if resolved is None:
        return ObservationDomain(
            observation_domain_ref=observation_domain_ref,
            configured=False,
            observations={},
        )
    if not isinstance(resolved, dict):
        raise TotalFieldGatewayError(
            "GATEWAY_OBSERVATION_DOMAIN_INVALID",
            f"$.observation_domains.{observation_domain_ref}",
        )
    if frozenset(resolved) != frozenset({"configured", "observations"}):
        raise TotalFieldGatewayError(
            "GATEWAY_OBSERVATION_DOMAIN_INVALID",
            f"$.observation_domains.{observation_domain_ref}",
        )
    configured = resolved["configured"]
    observations = resolved["observations"]
    if not isinstance(configured, bool) or not isinstance(observations, dict):
        raise TotalFieldGatewayError(
            "GATEWAY_OBSERVATION_DOMAIN_INVALID",
            f"$.observation_domains.{observation_domain_ref}",
        )
    return ObservationDomain(
        observation_domain_ref=observation_domain_ref,
        configured=configured,
        observations=observations,
    )


def _projection_validation(
    gte: Mapping[str, Any], policy: PriorityPolicy
) -> tuple[str, str | None]:
    """Match every GTE projection/runtime ref to the candidate registry."""

    dimensions = gte.get("dimensions")
    if not isinstance(dimensions, dict) or dimensions != dict(policy.dimension_refs):
        return "HOLD", "HOLD_DIMENSION_PROJECTION_NOT_CONFIGURED"
    if gte.get("constraint_hypergraph_ref") != policy.constraint_hypergraph_ref:
        return "HOLD", "HOLD_CONSTRAINT_HYPERGRAPH_NOT_CONFIGURED"
    if gte.get("convergence_operator_ref") != policy.convergence_operator_ref:
        return "HOLD", "HOLD_CONVERGENCE_OPERATOR_NOT_CONFIGURED"
    return "MATCH", None


def _result_gte(
    source_gte: Mapping[str, Any],
    *,
    commit_applied: bool,
    fixed_point_status: str,
    final_decision: str,
    state_ref: str,
    tfid: str,
    total_field_hash: str,
) -> dict[str, JSONValue]:
    """Derive a base-schema-valid GTE result without mutating the request."""

    gte = _copy_mapping(source_gte, "$.gte")
    if commit_applied:
        gte["lifecycle"] = "COMMITTED"
        gte["fixed_point_status"] = "REACHED"
        gte["verification"] = {
            "final_decision": "ALLOW",
            "commit_applied": True,
        }
        gte["tfs_result"] = {
            "state_ref": state_ref,
            "tfid": tfid,
            "total_field_hash": total_field_hash,
        }
        return gte
    gte["lifecycle"] = "CANDIDATE"
    gte["fixed_point_status"] = (
        fixed_point_status
        if fixed_point_status in {"REACHED", "NOT_REACHED"}
        else "NOT_REACHED"
    )
    gte["verification"] = {
        "final_decision": final_decision,
        "commit_applied": False,
    }
    gte["tfs_result"] = None
    return gte


def receive_candidate(
    candidate_payload: Mapping[str, Any],
    *,
    previous_state: Mapping[str, Any],
    observation_domains: Mapping[str, Any],
    policy: PriorityPolicy | None = None,
    policy_path: Path | str = DEFAULT_POLICY_PATH,
    parser: EightDGTEParserCandidate | None = None,
    profile_schema_path: Path = PROFILE_SCHEMA_PATH,
    base_gte_schema_path: Path = BASE_GTE_SCHEMA_PATH,
) -> dict[str, JSONValue]:
    """Validate, converge, adjudicate, and return one authority-owned result."""

    request = _copy_mapping(candidate_payload, "$")
    declared_source_mode = request.get("source_mode")
    if declared_source_mode == "LLM_PUSH":
        candidate_only = request.pop("candidate_only", None)
        if candidate_only is not True:
            raise TotalFieldGatewayError(
                "BLOCK_UNAUTHORIZED_CLOUD_COMMIT", "$.candidate_only"
            )
        cloud_claim_path = _cloud_authority_claim_path(request)
        if cloud_claim_path is not None:
            raise TotalFieldGatewayError(
                "BLOCK_UNAUTHORIZED_CLOUD_COMMIT", cloud_claim_path
            )
    claim_path = _authority_claim_path(request)
    if claim_path is not None:
        raise TotalFieldGatewayError("EXTERNAL_AUTHORITY_CLAIM_BLOCKED", claim_path)
    validator = _profile_validator(profile_schema_path, base_gte_schema_path)
    _validate_profile(request, validator=validator, expected_type="RUNTIME_REQUEST")
    source_mode = request["source_mode"]
    if source_mode not in SOURCE_MODES:
        raise TotalFieldGatewayError("GATEWAY_SOURCE_MODE_UNSUPPORTED", "$.source_mode")
    gte_value = request["gte"]
    if not isinstance(gte_value, dict):
        raise TotalFieldGatewayError("GATEWAY_GTE_OBJECT_REQUIRED", "$.gte")
    try:
        parsed_gte = (parser or EightDGTEParserCandidate()).parse_dict(gte_value)
    except GTECandidateParseError as exc:
        raise TotalFieldGatewayError(exc.reason_code, f"$.gte{exc.path[1:]}") from exc
    if parsed_gte.lifecycle != "CANDIDATE":
        raise TotalFieldGatewayError("GATEWAY_CANDIDATE_LIFECYCLE_REQUIRED", "$.gte.lifecycle")
    gte = parsed_gte.payload
    event_value = request["event"]
    fields_value = request["resolved_fields"]
    context_value = request["context"]
    if not isinstance(event_value, dict) or not isinstance(fields_value, dict):
        raise TotalFieldGatewayError("GATEWAY_PROFILE_INVALID")
    if not isinstance(context_value, dict):
        raise TotalFieldGatewayError("GATEWAY_PROFILE_INVALID", "$.context")
    if event_value["event_ref"] != gte["event_ref"]:
        raise TotalFieldGatewayError("GATEWAY_EVENT_REF_MISMATCH", "$.event.event_ref")
    priority_policy_ref = gte["priority_policy_ref"]
    observation_domain_ref = gte["observation_domain_ref"]
    if not isinstance(priority_policy_ref, str) or not isinstance(
        observation_domain_ref, str
    ):
        raise TotalFieldGatewayError("GATEWAY_GTE_REFERENCE_INVALID", "$.gte")
    selected_policy = policy if policy is not None else load_policy(policy_path)
    projection_status, projection_reason = _projection_validation(
        gte, selected_policy
    )
    event = Event(
        event_ref=cast(str, event_value["event_ref"]),
        event_code=cast(str, event_value["event_code"]),
        event_id=cast(str, event_value["event_id"]),
        logical_time=event_value["logical_time"],
        rule_set_ref=cast(str, request["rule_set_ref"]),
        priority_policy_ref=priority_policy_ref,
        observation_domain_ref=observation_domain_ref,
    )
    previous = EightFieldState.from_mapping(previous_state)
    candidate = EightFieldState.from_mapping(fields_value)
    observation_domain = _resolve_observation_domain(
        observation_domain_ref,
        observation_domains,
    )
    context = _copy_mapping(context_value, "$.context")
    reserved_path = _trusted_context_claim_path(context)
    if reserved_path is not None:
        raise TotalFieldGatewayError(
            "GATEWAY_TRUSTED_CONTEXT_FIELD_FORBIDDEN",
            reserved_path,
        )
    context["source_mode"] = cast(str, source_mode)
    context["adi_requested"] = cast(bool, request["adi_requested"])
    context["gateway_projection_status"] = projection_status
    if projection_reason is not None:
        context["gateway_projection_reason_code"] = projection_reason
    try:
        convergence = run_convergence(
            previous=previous,
            candidate=candidate,
            event=event,
            observation_domain=observation_domain,
            context=context,
            policy=selected_policy,
        )
    except RuntimeCandidateError:
        raise
    result = convergence.to_dict()
    result_gte = _result_gte(
        gte,
        commit_applied=convergence.commit_applied,
        fixed_point_status=convergence.fixed_point_status,
        final_decision=convergence.final_decision,
        state_ref=convergence.state_ref,
        tfid=convergence.tfid,
        total_field_hash=convergence.total_field_hash,
    )
    result["profile_schema_version"] = PROFILE_SCHEMA_VERSION
    result["profile_type"] = "RUNTIME_RESULT"
    result["gte"] = result_gte
    _validate_profile(result, validator=validator, expected_type="RUNTIME_RESULT")
    return cast(dict[str, JSONValue], deep_copy_json(result))


def _with_source_mode(
    candidate_payload: Mapping[str, Any], source_mode: str
) -> dict[str, JSONValue]:
    """Set the wrapper-owned source mode on a detached request."""

    request = _copy_mapping(candidate_payload, "$")
    request["source_mode"] = source_mode
    if source_mode == "LLM_PUSH":
        request["candidate_only"] = True
    return request


def total_field_pull(
    candidate_payload: Mapping[str, Any],
    *,
    previous_state: Mapping[str, Any],
    observation_domains: Mapping[str, Any],
    policy: PriorityPolicy | None = None,
) -> dict[str, JSONValue]:
    """Route a Total Field pull through the sole candidate receiver."""

    return receive_candidate(
        _with_source_mode(candidate_payload, "TOTAL_FIELD_PULL"),
        previous_state=previous_state,
        observation_domains=observation_domains,
        policy=policy,
    )


def llm_push(
    candidate_payload: Mapping[str, Any],
    *,
    previous_state: Mapping[str, Any],
    observation_domains: Mapping[str, Any],
    policy: PriorityPolicy | None = None,
) -> dict[str, JSONValue]:
    """Route an LLM push through the sole candidate receiver."""

    return receive_candidate(
        _with_source_mode(candidate_payload, "LLM_PUSH"),
        previous_state=previous_state,
        observation_domains=observation_domains,
        policy=policy,
    )


@dataclass(frozen=True, slots=True)
class TotalFieldCandidateGateway:
    """Provider-neutral bound gateway with caller-supplied domain registry."""

    observation_domains: Mapping[str, Any]
    policy_path: Path | str = DEFAULT_POLICY_PATH

    def __post_init__(self) -> None:
        """Detach the caller-supplied Observation Domain registry."""

        object.__setattr__(
            self,
            "observation_domains",
            _copy_mapping(self.observation_domains, "$.observation_domains"),
        )

    def receive_candidate(
        self,
        candidate_payload: Mapping[str, Any],
        *,
        previous_state: Mapping[str, Any],
        source_mode: str | None = None,
    ) -> dict[str, JSONValue]:
        """Receive one candidate through the common bound entrypoint."""

        request = _copy_mapping(candidate_payload, "$")
        if source_mode is not None:
            if source_mode not in SOURCE_MODES:
                raise TotalFieldGatewayError("GATEWAY_SOURCE_MODE_UNSUPPORTED")
            request["source_mode"] = source_mode
            if source_mode == "LLM_PUSH":
                request["candidate_only"] = True
        return receive_candidate(
            request,
            previous_state=previous_state,
            observation_domains=self.observation_domains,
            policy_path=self.policy_path,
        )

    def total_field_pull(
        self,
        candidate_payload: Mapping[str, Any],
        *,
        previous_state: Mapping[str, Any],
    ) -> dict[str, JSONValue]:
        """Route a bound pull request through ``receive_candidate``."""

        return self.receive_candidate(
            candidate_payload,
            previous_state=previous_state,
            source_mode="TOTAL_FIELD_PULL",
        )

    def llm_push(
        self,
        candidate_payload: Mapping[str, Any],
        *,
        previous_state: Mapping[str, Any],
    ) -> dict[str, JSONValue]:
        """Route a bound push request through ``receive_candidate``."""

        return self.receive_candidate(
            candidate_payload,
            previous_state=previous_state,
            source_mode="LLM_PUSH",
        )


__all__ = [
    "BASE_GTE_SCHEMA_PATH",
    "PROFILE_SCHEMA_PATH",
    "PROFILE_SCHEMA_VERSION",
    "TotalFieldCandidateGateway",
    "TotalFieldGatewayError",
    "llm_push",
    "receive_candidate",
    "total_field_pull",
]
