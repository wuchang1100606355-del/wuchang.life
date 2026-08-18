#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Single candidate ingress for TOTAL_FIELD_PULL and LLM_PUSH.

Candidate Source is never authority: both wrappers set only ``source_mode`` and
then call :func:`receive_candidate`.  The gateway validates 8D-GTE data,
resolves a caller-supplied Observation Domain, runs the existing TRUE8D
candidate core, and emits authority-owned result metadata without side effects.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, MutableSet, Sequence, cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource

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
from tools.total_field.w7tp_intent_field_suite.canonical_hash import canonical_sha256
from tools.total_field.xiaoj_member_bound_session_candidate import (
    evaluate_member_action_session,
)
from tools.w7tp_secondary_cloud_packet_ramp import (
    packet_content_sha256,
    reconstruct_local_state,
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
BROWSER_TRANSPORT_PROFILE = "BROWSER_8D_TRANSPORT_ENVELOPE"
BROWSER_TRANSPORT_SCHEMA_VERSION = "w7tp.browser-8d-transport-envelope.v1"
BROWSER_RECEIPT_SCHEMA_VERSION = "w7tp.browser-total-field-receipt.v1"
BROWSER_SENDER_REF = "web.xiaoj_member_browser_extension.background"
BROWSER_RECEIVER_REF = "tools.total_field_candidate_gateway.receive_candidate"
BROWSER_RETURN_COORDINATE = "chrome.runtime.sendMessage"
BROWSER_TRANSPORT_KEYS = frozenset(
    {
        "schema_version",
        "profile_type",
        "sender_ref",
        "receiver_ref",
        "return_coordinate",
        "packet_id",
        "trace_id",
        "content_sha256",
        "reconstruction_level",
        "authority_granted",
        "browser_packet",
    }
)
BROWSER_PACKET_ID = re.compile(r"^PKT_BROWSER_[a-f0-9]{32}$")
BROWSER_TRACE_ID = re.compile(r"^TRACE_BROWSER_[a-f0-9]{32}$")
SHA256_HEX = re.compile(r"^[a-f0-9]{64}$")
OPAQUE_REF = re.compile(r"^[A-Za-z0-9_.:/-]{3,180}$")
BROWSER_ALLOWED_ACTIONS = frozenset(
    {"open_sidebar_ref", "read_text_ref", "write_draft_ref"}
)
MEMBER_ACTION_CANDIDATE_KEY = "member_action_candidate"
MEMBER_ACTION_REQUEST_MODE = "ACTION_REQUEST"


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
    registry = Registry().with_resource(
        base_id, Resource.from_contents(resolvable_base)
    )
    return Draft202012Validator(profile, registry=registry)


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


def _browser_created_at(value: Any) -> dt.datetime:
    """Parse one timezone-aware browser packet timestamp."""

    if not isinstance(value, str) or not value:
        raise TotalFieldGatewayError(
            "BROWSER_CREATED_AT_REQUIRED", "$.browser_packet.D8_envelope.created_at"
        )
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TotalFieldGatewayError(
            "BROWSER_CREATED_AT_INVALID", "$.browser_packet.D8_envelope.created_at"
        ) from exc
    if parsed.tzinfo is None:
        raise TotalFieldGatewayError(
            "BROWSER_CREATED_AT_TIMEZONE_REQUIRED",
            "$.browser_packet.D8_envelope.created_at",
        )
    return parsed.astimezone(dt.timezone.utc)


def _browser_packet_sha256(packet: Mapping[str, Any]) -> str:
    """Hash the original browser packet with only its digest carriers blanked."""

    content = _copy_mapping(packet, "$.browser_packet")
    envelope = content.get("D8_envelope")
    if not isinstance(envelope, dict):
        raise TotalFieldGatewayError(
            "BROWSER_D8_ENVELOPE_REQUIRED", "$.browser_packet.D8_envelope"
        )
    envelope["content_hash"] = ""
    envelope["content_sha256"] = ""
    try:
        return canonical_sha256(content)
    except ValueError as exc:
        raise TotalFieldGatewayError(
            "BROWSER_CONTENT_CANONICALIZATION_FAILED", "$.browser_packet"
        ) from exc


def _browser_runtime_request(
    packet: Mapping[str, Any],
    *,
    packet_id: str,
    trace_id: str,
    content_sha256: str,
    intent_ref: str,
    reconstruction: Mapping[str, Any],
    created_at: str,
) -> dict[str, JSONValue]:
    """Project reference-only browser evidence into the existing runtime profile."""

    identity = cast(Mapping[str, Any], packet["D1_identity"])
    action = cast(Mapping[str, Any], packet["browser_action"])
    params = cast(Mapping[str, Any], action["params"])
    actor_ref = cast(str, identity["actor_ref"])
    action_type = cast(str, action["action_type"])
    reconstruction_sha256 = cast(str, reconstruction["sha256"])
    resolved_fields: dict[str, JSONValue] = {
        "D1": {"intent_ref": intent_ref, "identity_ref": actor_ref},
        "D2": {
            "state_ref": f"state_ref:browser-packet:{content_sha256}",
            "candidate_hash": content_sha256,
        },
        "D3": {
            "node_ref": "node:taiji01:member-browser-receiver",
            "routing_ref": "routing:member-browser:total-field",
            "scene_ref": "scene:member-browser-candidate",
        },
        "D4": {
            "evidence_ref": f"sha256:{content_sha256}",
            "candidate_ref": f"candidate_ref:sha256:{content_sha256}",
            "reconstruction_ref": f"sha256:{reconstruction_sha256}",
        },
        "D5": {
            "execution_ref": "execution:browser-candidate-only",
            "return_coordinate": BROWSER_RETURN_COORDINATE,
        },
        "D6": {"privacy_boundary_ref": "privacy:reference-only"},
        "D7": {
            "rule_ref": "rule:member-browser-candidate-only",
            "routing_ref": "routing:member-browser:total-field",
            "reconstruction_condition": "L3_CANDIDATE_LOCAL_STATE_MACHINE",
        },
        "D8": {"adjudication_policy_ref": "priority/tfct/candidate/v0_1"},
    }
    return {
        "profile_schema_version": PROFILE_SCHEMA_VERSION,
        "profile_type": "RUNTIME_REQUEST",
        "gte": {
            "schema_version": "8d-gte-candidate/0.1",
            "lifecycle": "CANDIDATE",
            "event_ref": trace_id,
            "observation_domain_ref": "observation-domain:member-browser:ref-only",
            "dimensions": {
                f"D{index}_ref": f"field/tfct/D{index}/v0_1"
                for index in range(1, 9)
            },
            "constraint_hypergraph_ref": "constraints/tfct/runtime-hypergraph/v0_1",
            "convergence_operator_ref": "convergence/tfct/finite-fixed-point/v0_1",
            "priority_policy_ref": "priority/tfct/candidate/v0_1",
            "fixed_point_status": "PENDING",
            "verification": {
                "final_decision": "PENDING",
                "commit_applied": False,
            },
            "tfs_result": None,
        },
        "source_mode": "TOTAL_FIELD_PULL",
        "event": {
            "event_id": trace_id,
            "event_ref": trace_id,
            "event_code": "STATE_UPDATE",
            "logical_time": created_at,
        },
        "rule_set_ref": "rules/tfct/identity_v0_1",
        "resolved_fields": resolved_fields,
        "context": {
            "request_ref": trace_id,
            "packet_id": packet_id,
            "trace_id": trace_id,
            "intent_ref": intent_ref,
            "action_type_ref": action_type,
            "behavior_info_ref": cast(str, params["behavior_info_ref"]),
            "candidate_hash": content_sha256,
            "reconstruction_level": "L3_CANDIDATE",
            "reconstruction_packet_sha256": reconstruction_sha256,
            "return_coordinate": BROWSER_RETURN_COORDINATE,
            "authority_granted": False,
        },
        "adi_requested": False,
    }


def _browser_reconstruction_packets(
    packet: Mapping[str, Any],
    *,
    packet_id: str,
    trace_id: str,
    content_sha256: str,
    intent_ref: str,
    nonce: str,
    ttl_seconds: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build reference-only inputs for the existing mode-selecting reconstructor."""

    identity = cast(Mapping[str, Any], packet["D1_identity"])
    action = cast(Mapping[str, Any], packet["browser_action"])
    params = cast(Mapping[str, Any], action["params"])
    actor_ref = cast(str, identity["actor_ref"])
    role_ref = cast(str, identity["role"])
    action_type = cast(str, action["action_type"])
    scenario = {
        "packet_id": packet_id,
        "schema_version": "W7TP-SCENARIO-TRANSLATION/1.0",
        "selected_container": "GENERIC",
        "packet_type": "GENERIC_INTENT_PACKET",
        "capability_ref": "CAP_GENERIC_INTENT_V1",
        "destination_field": "MEMBER_BROWSER_CANDIDATE_FIELD",
        "d1_intent": {"service_result_ref": intent_ref},
        "d2_state": {
            "identity_ref": actor_ref,
            "role_refs": [role_ref],
            "consent_state": "REFERENCE_ONLY",
            "workflow_state_ref": "workflow:member-browser:candidate",
        },
        "d3_coordinate": {
            "node_ref": "taiji01",
            "container": "GENERIC",
            "service_field": "MEMBER_BROWSER_CANDIDATE_FIELD",
            "module_ref": "module:xiaoj-member-browser",
            "task_ref": trace_id,
        },
        "d4_evidence": {
            "evidence_refs": [
                cast(str, params["behavior_info_ref"]),
                f"browser-packet:{packet_id}",
            ],
            "evidence_hashes": [content_sha256],
        },
        "d5_execution": {
            "service_contract_ref": "contract:member-browser:candidate-only",
            "local_action_ref": f"action:{action_type}",
        },
        "d6_generative_transmission": {
            "packet_protocol": "W7TP-8D-PACKET-NATIVE/1.0",
            "lookup_refs": [
                cast(str, params["controller_ref"]),
                "CAP_GENERIC_INTENT_V1",
            ],
            "reconstruction_conditions": [
                "original_packet_hash_matches",
                "candidate_only_local_state_machine",
            ],
            "verification_method": "TOTAL_FIELD_CANDIDATE_RECEIVER",
        },
        "d7_risk": {"hard_risks": [], "authority_boundary_ok": True},
        "d8_envelope": {
            "identity_ref": actor_ref,
            "authority_scope": ["candidate_only"],
            "ttl_seconds": ttl_seconds,
            "nonce": nonce,
            "sha256": "",
            "protocol": "W7TP-8D-PACKET-NATIVE/1.0",
            "verifier_ref": BROWSER_RECEIVER_REF,
        },
    }
    scenario["d8_envelope"]["sha256"] = packet_content_sha256(scenario)
    capability = {
        "capability_ref": "CAP_GENERIC_INTENT_V1",
        "packet_type": "PROFESSIONAL_RULE_PACKET",
        "schema_version": "W7TP-CAPABILITY/1.0",
        "domain_code": "MEMBER_BROWSER",
        "language_code": "zh-TW",
        "compatibility_profile": "W7TP-8D-PACKET-NATIVE/1.0",
        "source_refs": [
            cast(str, params["controller_ref"]),
            BROWSER_RECEIVER_REF,
        ],
        "payload_refs": [f"browser-packet-sha256:{content_sha256}"],
        "reconstruction_spec": {
            "mode": "L3_CANDIDATE",
            "conditions": [
                "original_packet_hash_matches",
                "total_field_verifier_required",
            ],
            "effect_contract_ref": "effect:member-browser:candidate-only",
        },
        "verification_method": "TOTAL_FIELD_CANDIDATE_RECEIVER",
        "sha256": "",
    }
    capability["sha256"] = packet_content_sha256(capability)
    return scenario, capability


def _receive_runtime_candidate(
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


def _receive_browser_transport(
    transport_envelope: Mapping[str, Any],
    *,
    replay_ledger: MutableSet[str] | None,
    received_at: dt.datetime | None,
    policy: PriorityPolicy | None,
    policy_path: Path | str,
    parser: EightDGTEParserCandidate | None,
    profile_schema_path: Path,
    base_gte_schema_path: Path,
) -> dict[str, JSONValue]:
    """Verify one unchanged browser packet and return a trace-bound receipt."""

    transport = _copy_mapping(transport_envelope, "$")
    if frozenset(transport) != BROWSER_TRANSPORT_KEYS:
        raise TotalFieldGatewayError("BROWSER_TRANSPORT_FIELDS_INVALID", "$")
    if transport.get("schema_version") != BROWSER_TRANSPORT_SCHEMA_VERSION:
        raise TotalFieldGatewayError(
            "BROWSER_TRANSPORT_SCHEMA_INVALID", "$.schema_version"
        )
    if transport.get("profile_type") != BROWSER_TRANSPORT_PROFILE:
        raise TotalFieldGatewayError(
            "BROWSER_TRANSPORT_PROFILE_INVALID", "$.profile_type"
        )
    if transport.get("sender_ref") != BROWSER_SENDER_REF:
        raise TotalFieldGatewayError(
            "BROWSER_SENDER_REF_INVALID", "$.sender_ref"
        )
    if transport.get("receiver_ref") != BROWSER_RECEIVER_REF:
        raise TotalFieldGatewayError(
            "BROWSER_RECEIVER_REF_INVALID", "$.receiver_ref"
        )
    if transport.get("return_coordinate") != BROWSER_RETURN_COORDINATE:
        raise TotalFieldGatewayError(
            "BROWSER_RETURN_COORDINATE_INVALID", "$.return_coordinate"
        )
    if transport.get("authority_granted") is not False:
        raise TotalFieldGatewayError(
            "BROWSER_AUTHORITY_GRANT_BLOCKED", "$.authority_granted"
        )

    packet_id = transport.get("packet_id")
    trace_id = transport.get("trace_id")
    content_sha256 = transport.get("content_sha256")
    if not isinstance(packet_id, str) or BROWSER_PACKET_ID.fullmatch(packet_id) is None:
        raise TotalFieldGatewayError("BROWSER_PACKET_ID_INVALID", "$.packet_id")
    if not isinstance(trace_id, str) or BROWSER_TRACE_ID.fullmatch(trace_id) is None:
        raise TotalFieldGatewayError("BROWSER_TRACE_ID_INVALID", "$.trace_id")
    if (
        not isinstance(content_sha256, str)
        or SHA256_HEX.fullmatch(content_sha256) is None
    ):
        raise TotalFieldGatewayError(
            "BROWSER_CONTENT_SHA256_INVALID", "$.content_sha256"
        )
    if transport.get("reconstruction_level") != "L3_CANDIDATE":
        raise TotalFieldGatewayError(
            "BROWSER_RECONSTRUCTION_LEVEL_ESCALATION_BLOCKED",
            "$.reconstruction_level",
        )

    packet_value = transport.get("browser_packet")
    if not isinstance(packet_value, dict):
        raise TotalFieldGatewayError(
            "BROWSER_PACKET_REQUIRED", "$.browser_packet"
        )
    packet = _copy_mapping(packet_value, "$.browser_packet")
    if packet.get("packet_type") != "xiaoj_8d_action_packet":
        raise TotalFieldGatewayError(
            "BROWSER_PACKET_TYPE_INVALID", "$.browser_packet.packet_type"
        )
    identity = packet.get("D1_identity")
    governance = packet.get("D6_governance")
    d8 = packet.get("D8_envelope")
    action = packet.get("browser_action")
    if not all(
        isinstance(value, dict) for value in (identity, governance, d8, action)
    ):
        raise TotalFieldGatewayError("BROWSER_PACKET_STRUCTURE_INVALID", "$.browser_packet")
    assert isinstance(identity, dict)
    assert isinstance(governance, dict)
    assert isinstance(d8, dict)
    assert isinstance(action, dict)
    params = action.get("params")
    if not isinstance(params, dict):
        raise TotalFieldGatewayError(
            "BROWSER_ACTION_PARAMS_REQUIRED", "$.browser_packet.browser_action.params"
        )
    if action.get("action_type") not in BROWSER_ALLOWED_ACTIONS:
        raise TotalFieldGatewayError(
            "BROWSER_ACTION_NOT_ALLOWED", "$.browser_packet.browser_action.action_type"
        )
    if action.get("dry_run") is not True or action.get("submit_forbidden") is not True:
        raise TotalFieldGatewayError(
            "BROWSER_CANDIDATE_BOUNDARY_REQUIRED", "$.browser_packet.browser_action"
        )
    if (
        params.get("candidate_only") is not True
        or params.get("requires_total_field_verify") is not True
        or params.get("cloud_candidate_only") is not True
    ):
        raise TotalFieldGatewayError(
            "BROWSER_CANDIDATE_ONLY_REQUIRED",
            "$.browser_packet.browser_action.params",
        )
    if (
        governance.get("no_plaintext_context") is not True
        or governance.get("reconstruction_level") != "L3_CANDIDATE"
    ):
        raise TotalFieldGatewayError(
            "BROWSER_GOVERNANCE_BOUNDARY_INVALID",
            "$.browser_packet.D6_governance",
        )
    if d8.get("authority_granted") is not False:
        raise TotalFieldGatewayError(
            "BROWSER_AUTHORITY_GRANT_BLOCKED",
            "$.browser_packet.D8_envelope.authority_granted",
        )
    if (
        d8.get("packet_id") != packet_id
        or d8.get("trace_id") != trace_id
        or d8.get("content_hash") != content_sha256
        or d8.get("content_sha256") != content_sha256
    ):
        raise TotalFieldGatewayError(
            "BROWSER_TRANSPORT_BINDING_MISMATCH", "$.browser_packet.D8_envelope"
        )
    recomputed_sha256 = _browser_packet_sha256(packet)
    if recomputed_sha256 != content_sha256:
        raise TotalFieldGatewayError(
            "BROWSER_CONTENT_SHA256_MISMATCH",
            "$.browser_packet.D8_envelope.content_sha256",
        )

    intent_ref = params.get("intent_ref")
    behavior_info_ref = params.get("behavior_info_ref")
    controller_ref = params.get("controller_ref")
    actor_ref = identity.get("actor_ref")
    role_ref = identity.get("role")
    for path, value in (
        ("$.browser_packet.browser_action.params.intent_ref", intent_ref),
        ("$.browser_packet.browser_action.params.behavior_info_ref", behavior_info_ref),
        ("$.browser_packet.browser_action.params.controller_ref", controller_ref),
        ("$.browser_packet.D1_identity.actor_ref", actor_ref),
        ("$.browser_packet.D1_identity.role", role_ref),
    ):
        if not isinstance(value, str) or OPAQUE_REF.fullmatch(value) is None:
            raise TotalFieldGatewayError("BROWSER_REQUIRED_REF_INVALID", path)

    ttl_seconds = d8.get("ttl_seconds")
    nonce = d8.get("nonce")
    if (
        not isinstance(ttl_seconds, int)
        or isinstance(ttl_seconds, bool)
        or ttl_seconds < 1
        or ttl_seconds > 3600
    ):
        raise TotalFieldGatewayError(
            "BROWSER_TTL_INVALID", "$.browser_packet.D8_envelope.ttl_seconds"
        )
    if not isinstance(nonce, str) or OPAQUE_REF.fullmatch(nonce) is None:
        raise TotalFieldGatewayError(
            "BROWSER_NONCE_INVALID", "$.browser_packet.D8_envelope.nonce"
        )
    created_at_value = d8.get("created_at")
    created_at = _browser_created_at(created_at_value)
    now = received_at or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        raise TotalFieldGatewayError("BROWSER_RECEIVED_AT_TIMEZONE_REQUIRED")
    current = now.astimezone(dt.timezone.utc)
    age_seconds = (current - created_at).total_seconds()
    if age_seconds < -5:
        raise TotalFieldGatewayError(
            "BROWSER_CREATED_AT_IN_FUTURE", "$.browser_packet.D8_envelope.created_at"
        )
    if age_seconds >= ttl_seconds:
        raise TotalFieldGatewayError(
            "BROWSER_TTL_EXPIRED", "$.browser_packet.D8_envelope.ttl_seconds"
        )
    if replay_ledger is None:
        raise TotalFieldGatewayError("BROWSER_REPLAY_LEDGER_REQUIRED")
    if nonce in replay_ledger:
        raise TotalFieldGatewayError(
            "BROWSER_NONCE_REPLAY", "$.browser_packet.D8_envelope.nonce"
        )

    scenario, capability = _browser_reconstruction_packets(
        packet,
        packet_id=packet_id,
        trace_id=trace_id,
        content_sha256=content_sha256,
        intent_ref=cast(str, intent_ref),
        nonce=nonce,
        ttl_seconds=ttl_seconds,
    )
    reconstruction = reconstruct_local_state(scenario, capability)
    if (
        reconstruction.get("mode") != "L3_CANDIDATE"
        or reconstruction.get("candidate_only") is not True
        or reconstruction.get("errors")
    ):
        raise TotalFieldGatewayError(
            "BROWSER_RECONSTRUCTION_VERIFICATION_FAILED", "$.reconstruction"
        )

    replay_ledger.add(nonce)
    runtime_request = _browser_runtime_request(
        packet,
        packet_id=packet_id,
        trace_id=trace_id,
        content_sha256=content_sha256,
        intent_ref=cast(str, intent_ref),
        reconstruction=reconstruction,
        created_at=cast(str, created_at_value),
    )
    gateway_result = _receive_runtime_candidate(
        runtime_request,
        previous_state=cast(Mapping[str, Any], runtime_request["resolved_fields"]),
        observation_domains={},
        policy=policy,
        policy_path=policy_path,
        parser=parser,
        profile_schema_path=profile_schema_path,
        base_gte_schema_path=base_gte_schema_path,
    )
    if gateway_result.get("commit_applied") is not False:
        raise TotalFieldGatewayError("BROWSER_CANDIDATE_COMMIT_BLOCKED")
    gateway_result_sha256 = canonical_sha256(gateway_result)
    reconstruction_sha256 = cast(str, reconstruction["sha256"])
    total_field_decision = cast(str, gateway_result["final_decision"])
    receipt: dict[str, JSONValue] = {
        "schema_version": BROWSER_RECEIPT_SCHEMA_VERSION,
        "receipt_state": "PASS",
        "receiver": "receive_candidate",
        "receiver_ref": BROWSER_RECEIVER_REF,
        "receiver_call_count": 1,
        "packet_id": packet_id,
        "trace_id": trace_id,
        "content_sha256": content_sha256,
        "intent_ref": cast(str, intent_ref),
        "reconstruction_level": "L3_CANDIDATE",
        "reconstruction_packet_sha256": reconstruction_sha256,
        "verifier_result_sha256": gateway_result_sha256,
        "total_field_decision": total_field_decision,
        "decision_reason_codes": cast(
            list[JSONValue], gateway_result["decision_reason_codes"]
        ),
        "commit_applied": False,
        "authority_granted": False,
        "action_executed": False,
        "return_coordinate": BROWSER_RETURN_COORDINATE,
    }
    receipt_sha256 = canonical_sha256(receipt)
    receipt["receipt_sha256"] = receipt_sha256
    receipt["receipt_ref"] = f"receipt_ref:sha256:{receipt_sha256}"
    result: dict[str, JSONValue] = {
        "schema_version": "w7tp.browser-total-field-result.v1",
        "packet_type": "BROWSER_TOTAL_FIELD_RESULT",
        "state": total_field_decision,
        "candidate_only": True,
        "authority_granted": False,
        "packet_id": packet_id,
        "trace_id": trace_id,
        "content_sha256": content_sha256,
        "reconstruction": cast(JSONValue, reconstruction),
        "verifier": {
            "verifier_ref": BROWSER_RECEIVER_REF,
            "state": "PASS",
            "decision": total_field_decision,
            "result_sha256": gateway_result_sha256,
        },
        "total_field_receipt": receipt,
    }
    return cast(dict[str, JSONValue], deep_copy_json(result))


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
    browser_replay_ledger: MutableSet[str] | None = None,
    browser_received_at: dt.datetime | None = None,
    member_nonce_consumer: Any | None = None,
    member_p1_verifier: (
        Callable[[Mapping[str, Any]], Mapping[str, Any]] | None
    ) = None,
    member_current_epoch: int | None = None,
    active_seat_leases: Sequence[Mapping[str, Any]] = (),
) -> dict[str, JSONValue]:
    """Route one runtime profile or browser transport through the sole receiver."""

    if candidate_payload.get("profile_type") == BROWSER_TRANSPORT_PROFILE:
        return _receive_browser_transport(
            candidate_payload,
            replay_ledger=browser_replay_ledger,
            received_at=browser_received_at,
            policy=policy,
            policy_path=policy_path,
            parser=parser,
            profile_schema_path=profile_schema_path,
            base_gte_schema_path=base_gte_schema_path,
        )
    request = dict(candidate_payload)
    context = request.get("context")
    request_mode = (
        context.get("request_mode")
        if isinstance(context, Mapping)
        else request.get("request_mode")
    )
    member_action = request.pop(MEMBER_ACTION_CANDIDATE_KEY, None)
    gate_result: Mapping[str, Any] | None = None
    if request_mode == MEMBER_ACTION_REQUEST_MODE:
        if not isinstance(member_action, Mapping):
            raise TotalFieldGatewayError(
                "HOLD_MEMBER_DUAL_RECEIPT_REQUIRED",
                f"$.{MEMBER_ACTION_CANDIDATE_KEY}",
            )
        if not isinstance(member_current_epoch, int):
            raise TotalFieldGatewayError(
                "HOLD_MEMBER_SESSION_CLOCK_REQUIRED",
                "$.member_current_epoch",
            )
        gate_result = evaluate_member_action_session(
            member_action,
            current_epoch=member_current_epoch,
            nonce_consumer=member_nonce_consumer,
            p1_verifier=member_p1_verifier,
            active_seat_leases=active_seat_leases,
        )
        if gate_result.get("state") != "PASS":
            raise TotalFieldGatewayError(
                str(gate_result.get("reason_code") or "HOLD_MEMBER_ACTION_GATE"),
                f"$.{MEMBER_ACTION_CANDIDATE_KEY}",
            )
        bound_context = dict(context) if isinstance(context, Mapping) else {}
        bound_context["member_action_gate_ref"] = gate_result["gate_ref"]
        bound_context["request_mode"] = MEMBER_ACTION_REQUEST_MODE
        request["context"] = bound_context
    elif member_action is not None:
        raise TotalFieldGatewayError(
            "HOLD_MEMBER_ACTION_MODE_REQUIRED",
            f"$.{MEMBER_ACTION_CANDIDATE_KEY}",
        )
    result = _receive_runtime_candidate(
        request,
        previous_state=previous_state,
        observation_domains=observation_domains,
        policy=policy,
        policy_path=policy_path,
        parser=parser,
        profile_schema_path=profile_schema_path,
        base_gte_schema_path=base_gte_schema_path,
    )
    if gate_result is not None:
        if result.get("commit_applied") is not False:
            raise TotalFieldGatewayError("HOLD_GENERIC_GATEWAY_EARLY_COMMIT")
        result["member_action_gate"] = cast(
            JSONValue,
            {
                "gate_ref": gate_result["gate_ref"],
                "reason_code": gate_result["reason_code"],
                "candidate_only": True,
                "runtime_released": False,
            },
        )
    return result


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
    member_nonce_consumer: Any | None = None,
    member_p1_verifier: (
        Callable[[Mapping[str, Any]], Mapping[str, Any]] | None
    ) = None,
    member_current_epoch: int | None = None,
    active_seat_leases: Sequence[Mapping[str, Any]] = (),
) -> dict[str, JSONValue]:
    """Route a Total Field pull through the sole candidate receiver."""

    return receive_candidate(
        _with_source_mode(candidate_payload, "TOTAL_FIELD_PULL"),
        previous_state=previous_state,
        observation_domains=observation_domains,
        policy=policy,
        member_nonce_consumer=member_nonce_consumer,
        member_p1_verifier=member_p1_verifier,
        member_current_epoch=member_current_epoch,
        active_seat_leases=active_seat_leases,
    )


def llm_push(
    candidate_payload: Mapping[str, Any],
    *,
    previous_state: Mapping[str, Any],
    observation_domains: Mapping[str, Any],
    policy: PriorityPolicy | None = None,
    member_nonce_consumer: Any | None = None,
    member_p1_verifier: (
        Callable[[Mapping[str, Any]], Mapping[str, Any]] | None
    ) = None,
    member_current_epoch: int | None = None,
    active_seat_leases: Sequence[Mapping[str, Any]] = (),
) -> dict[str, JSONValue]:
    """Route an LLM push through the sole candidate receiver."""

    return receive_candidate(
        _with_source_mode(candidate_payload, "LLM_PUSH"),
        previous_state=previous_state,
        observation_domains=observation_domains,
        policy=policy,
        member_nonce_consumer=member_nonce_consumer,
        member_p1_verifier=member_p1_verifier,
        member_current_epoch=member_current_epoch,
        active_seat_leases=active_seat_leases,
    )


@dataclass(frozen=True, slots=True)
class TotalFieldCandidateGateway:
    """Provider-neutral bound gateway with caller-supplied domain registry."""

    observation_domains: Mapping[str, Any]
    policy_path: Path | str = DEFAULT_POLICY_PATH
    member_nonce_consumer: Any | None = None
    member_p1_verifier: (
        Callable[[Mapping[str, Any]], Mapping[str, Any]] | None
    ) = None
    member_current_epoch: int | None = None
    active_seat_leases: Sequence[Mapping[str, Any]] = ()

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
            member_nonce_consumer=self.member_nonce_consumer,
            member_p1_verifier=self.member_p1_verifier,
            member_current_epoch=self.member_current_epoch,
            active_seat_leases=self.active_seat_leases,
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
