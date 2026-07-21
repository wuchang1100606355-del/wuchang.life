#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Candidate-only multi-domain adapter for the existing Total Field gateway.

Every valid attribute is independently projected into TRUE8D and delegated to
``tools.total_field_candidate_gateway.receive_candidate``.  This module adds no
second convergence engine and performs no external or persistent side effect.
"""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from typing import Any, Mapping, Sequence, cast

from tools.sovereign_ai_domain_completion_candidate import (
    CompletionProvider,
    DomainCompletionError,
    GovernanceCandidate,
    JSONValue,
    POLICY_PATH,
    RUN_ID,
    adapter_for,
    build_xiaoj_envelope,
    canonical_sha256,
    deep_copy_json,
    validate_candidate,
)
from tools.tfct_true8d_runtime_candidate import PriorityPolicy, load_policy
from tools.total_field_candidate_gateway import (
    TotalFieldGatewayError,
    receive_candidate as total_field_receive_candidate,
)


RESULT_SCHEMA_VERSION = "sovereign-ai-domain-completion-result/0.1"
GATEWAY_REF = "tools.total_field_candidate_gateway.receive_candidate"
ADAPTER_GATEWAY_REF = "tools.domain_completion_total_field_gateway.receive_candidate"
DECISION_PRIORITY = ("QUARANTINE", "BLOCK", "HOLD", "ALLOW")
SINGLE_PROVIDER_ACTION_HOLD_REASON = "HOLD_SINGLE_PROVIDER_ACTION_NOT_AUTHORIZED"
SINGLE_PROVIDER_ACTION_HOLD_MARKER = "single_provider_action_not_authorized"


def _load_domain_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    """Load the closed deterministic domain-completion policy."""

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise DomainCompletionError("DOMAIN_POLICY_READ_FAILED") from exc
    if not isinstance(value, dict):
        raise DomainCompletionError("DOMAIN_POLICY_INVALID")
    required = {
        "schema_version",
        "run_id",
        "status",
        "cloud_completion",
        "domains",
        "allowed_source_modes",
        "sensitivity_classes",
        "decision_priority",
        "gate_rules",
        "restricted_attributes",
        "runtime_hold_marker_keys",
        "authority_forbidden_keys",
        "side_effects",
    }
    if set(value) != required:
        raise DomainCompletionError("DOMAIN_POLICY_KEYS_INVALID")
    if value["run_id"] != RUN_ID or value["status"] != "CANDIDATE":
        raise DomainCompletionError("DOMAIN_POLICY_IDENTITY_INVALID")
    if value["cloud_completion"] != "SUPPORTED_AS_CANDIDATE_ONLY":
        raise DomainCompletionError("DOMAIN_POLICY_AUTHORITY_INVALID")
    if value["decision_priority"] != list(DECISION_PRIORITY):
        raise DomainCompletionError("DOMAIN_POLICY_PRIORITY_INVALID")
    side_effects = value["side_effects"]
    if not isinstance(side_effects, dict) or any(side_effects.values()):
        raise DomainCompletionError("DOMAIN_POLICY_SIDE_EFFECT_INVALID")
    return cast(dict[str, Any], deep_copy_json(value))


def _runtime_policy(domain_policy: Mapping[str, Any]) -> PriorityPolicy:
    """Extend only D6 marker names while retaining the existing runtime core."""

    base = load_policy()
    markers = domain_policy.get("runtime_hold_marker_keys")
    if not isinstance(markers, list) or not all(
        isinstance(item, str) and item for item in markers
    ):
        raise DomainCompletionError("DOMAIN_POLICY_MARKERS_INVALID")
    names = tuple(sorted(frozenset(base.sensitive_key_names) | frozenset(markers)))
    return replace(base, sensitive_key_names=names)


def _normalize_attribute(value: str) -> str:
    return value.strip().casefold().replace("-", "_").replace(" ", "_")


def _classification(
    candidate: GovernanceCandidate,
    policy: Mapping[str, Any],
    *,
    conflict: bool,
) -> tuple[str, str, str, str | None]:
    """Return effective sensitivity, decision, stable reason, and D6 marker."""

    if conflict:
        return (
            candidate.sensitivity,
            "HOLD",
            "HOLD_CANDIDATE_CONFLICT_DETECTED",
            "domain_candidate_conflict",
        )
    restricted = policy.get("restricted_attributes")
    if not isinstance(restricted, dict):
        raise DomainCompletionError("DOMAIN_POLICY_RESTRICTIONS_INVALID")
    attribute = _normalize_attribute(candidate.attribute_name)

    def listed(group: str) -> bool:
        values = restricted.get(group)
        if not isinstance(values, list):
            raise DomainCompletionError("DOMAIN_POLICY_RESTRICTIONS_INVALID")
        return attribute in values

    if listed("SECRET_BLOCK"):
        return (
            "PRIVACY_RESTRICTED",
            "BLOCK",
            "BLOCK_RAW_SECRET_ATTRIBUTE",
            "domain_privacy_restricted",
        )

    effective = candidate.sensitivity
    for group in (
        "PRIVACY_RESTRICTED",
        "OWNER_CONFIRMATION_REQUIRED",
        "LEGAL_REVIEW_REQUIRED",
        "FINANCIAL_REVIEW_REQUIRED",
        "EVIDENCE_REQUIRED",
    ):
        if listed(group):
            effective = group
            break

    if candidate.requires_human_confirmation and effective in {
        "SAFE_DERIVED",
        "EVIDENCE_REQUIRED",
    }:
        return (
            effective,
            "HOLD",
            "HOLD_HUMAN_CONFIRMATION_REQUIRED",
            "domain_owner_confirmation_required",
        )
    if effective == "SAFE_DERIVED":
        return effective, "ALLOW", "ATTRIBUTE_CANDIDATE_ALLOWED", None
    if effective == "EVIDENCE_REQUIRED":
        if candidate.evidence_refs:
            return effective, "ALLOW", "ATTRIBUTE_EVIDENCE_ACCEPTED", None
        return (
            effective,
            "HOLD",
            "HOLD_EVIDENCE_REQUIRED",
            "domain_evidence_required",
        )
    gate_rules = policy.get("gate_rules")
    if not isinstance(gate_rules, dict) or effective not in gate_rules:
        raise DomainCompletionError("DOMAIN_ATTRIBUTE_UNCLASSIFIED")
    rule = gate_rules[effective]
    if not isinstance(rule, dict):
        raise DomainCompletionError("DOMAIN_POLICY_GATE_INVALID")
    decision = rule.get("decision")
    reason_code = rule.get("reason_code")
    if decision not in DECISION_PRIORITY or not isinstance(reason_code, str):
        raise DomainCompletionError("DOMAIN_POLICY_GATE_INVALID")
    marker_by_class = {
        "OWNER_CONFIRMATION_REQUIRED": "domain_owner_confirmation_required",
        "PRIVACY_RESTRICTED": "domain_privacy_restricted",
        "LEGAL_REVIEW_REQUIRED": "domain_legal_review_required",
        "FINANCIAL_REVIEW_REQUIRED": "domain_financial_review_required",
        "UNSUPPORTED": "domain_unsupported",
    }
    return effective, decision, reason_code, marker_by_class.get(effective)


def _more_restrictive(left: str, right: str) -> str:
    return left if DECISION_PRIORITY.index(left) <= DECISION_PRIORITY.index(right) else right


def _candidate_semantic_fingerprint(candidate: GovernanceCandidate) -> str:
    """Identify governance-equivalent candidates without provider provenance."""

    return canonical_sha256(
        {
            "candidate_value": candidate.candidate_value,
            "requires_human_confirmation": candidate.requires_human_confirmation,
            "sensitivity": candidate.sensitivity,
        }
    )


def _safe_candidate_value(
    candidate: GovernanceCandidate, effective_sensitivity: str
) -> JSONValue:
    """Keep privacy-restricted values out of runtime results and TFS candidates."""

    if effective_sensitivity == "PRIVACY_RESTRICTED":
        return {
            "candidate_hash": candidate.candidate_hash,
            "value_status": "REDACTED_BY_D6",
        }
    return deep_copy_json(candidate.candidate_value)


def _state_fields(
    candidate: GovernanceCandidate,
    value: JSONValue,
    *,
    effective_sensitivity: str,
    marker: str | None,
    previous: bool,
) -> dict[str, JSONValue]:
    """Project one candidate value into the existing eight-field runtime shape."""

    d6: dict[str, JSONValue] = {
        "privacy_boundary_ref": "privacy:sovereign-domain-completion/v0.1"
    }
    if marker is not None and not previous:
        d6[marker] = True
    fields: dict[str, JSONValue] = {
        "D1": {
            "intent_ref": "intent:sovereign-domain-attribute-completion/v0.1"
        },
        "D2": {
            "attribute_ref": candidate.identity_key,
            "value": deep_copy_json(value),
        },
        "D3": {
            "domain": candidate.domain,
            "entity_ref": candidate.entity_ref,
            "attribute_name": candidate.attribute_name,
        },
        "D4": {
            "candidate_hash": candidate.candidate_hash,
            "confidence": candidate.confidence,
            "evidence_refs": list(candidate.evidence_refs),
            "model_ref": candidate.model_ref,
            "provider_ref": candidate.provider_ref,
            "sensitivity": effective_sensitivity,
        },
        "D5": {
            "execution_ref": ADAPTER_GATEWAY_REF,
            "candidate_only": True,
            "db_write": False,
            "deploy": False,
            "restart": False,
            "router_write": False,
        },
        "D6": d6,
        "D7": {
            "rule_ref": candidate.rule_ref,
            "routing_ref": GATEWAY_REF,
            "reconstruction_condition": "ATTRIBUTE_CANDIDATE_REFERENCE_ONLY",
        },
        "D8": {
            "adjudication_policy_ref": "policy:sovereign-domain-completion/v0.1"
        },
    }
    return fields


def _runtime_request(
    candidate: GovernanceCandidate,
    proposed: Mapping[str, JSONValue],
    runtime_policy: PriorityPolicy,
) -> dict[str, JSONValue]:
    source_mode = "LLM_PUSH" if candidate.source_mode == "LLM_PUSH" else "TOTAL_FIELD_PULL"
    gte: dict[str, JSONValue] = {
        "schema_version": "8d-gte-candidate/0.1",
        "lifecycle": "CANDIDATE",
        "event_ref": candidate.event_ref,
        "observation_domain_ref": candidate.observation_domain_ref,
        "dimensions": dict(runtime_policy.dimension_refs),
        "constraint_hypergraph_ref": runtime_policy.constraint_hypergraph_ref,
        "convergence_operator_ref": runtime_policy.convergence_operator_ref,
        "priority_policy_ref": runtime_policy.priority_policy_ref,
        "fixed_point_status": "PENDING",
        "verification": {"final_decision": "PENDING", "commit_applied": False},
        "tfs_result": None,
    }
    request: dict[str, JSONValue] = {
        "profile_schema_version": "8d-gte-runtime-candidate-profile/0.1",
        "profile_type": "RUNTIME_REQUEST",
        "gte": gte,
        "source_mode": source_mode,
        "event": {
            "event_id": f"{candidate.event_ref}:{candidate.candidate_hash}",
            "event_ref": candidate.event_ref,
            "event_code": "STATE_UPDATE",
            "logical_time": f"logical:{candidate.event_ref}:{candidate.candidate_hash}",
        },
        "rule_set_ref": candidate.rule_ref,
        "resolved_fields": dict(proposed),
        "context": {
            "candidate_hash": candidate.candidate_hash,
            "domain_completion_source_mode": candidate.source_mode,
            "domain_completion_run_id": RUN_ID,
        },
        "adi_requested": False,
    }
    if source_mode == "LLM_PUSH":
        request["candidate_only"] = True
    return request


class DomainCompletionTotalFieldGateway:
    """Per-attribute adapter bound to the sole existing Total Field receiver."""

    def __init__(
        self,
        *,
        observation_domains: Mapping[str, Any],
        policy_path: Path = POLICY_PATH,
    ) -> None:
        copied = deep_copy_json(dict(observation_domains))
        if not isinstance(copied, dict):
            raise DomainCompletionError("OBSERVATION_DOMAINS_INVALID")
        self._observation_domains = copied
        self._domain_policy = _load_domain_policy(policy_path)
        self._runtime_policy = _runtime_policy(self._domain_policy)

    def _receive_validated(
        self,
        candidate: GovernanceCandidate,
        *,
        previous_value: JSONValue,
        conflict: bool = False,
        forced_hold_reason: str | None = None,
    ) -> dict[str, JSONValue]:
        effective, requested_decision, requested_reason, marker = _classification(
            candidate, self._domain_policy, conflict=conflict
        )
        runtime_policy = self._runtime_policy
        if forced_hold_reason is not None:
            if forced_hold_reason != SINGLE_PROVIDER_ACTION_HOLD_REASON:
                raise DomainCompletionError("FORCED_HOLD_REASON_UNSUPPORTED")
            requested_decision = "HOLD"
            requested_reason = forced_hold_reason
            marker = SINGLE_PROVIDER_ACTION_HOLD_MARKER
            runtime_policy = replace(
                runtime_policy,
                sensitive_key_names=tuple(
                    sorted(
                        frozenset(runtime_policy.sensitive_key_names)
                        | {SINGLE_PROVIDER_ACTION_HOLD_MARKER}
                    )
                ),
            )
        safe_value = _safe_candidate_value(candidate, effective)
        previous_fields = _state_fields(
            candidate,
            deep_copy_json(previous_value),
            effective_sensitivity=effective,
            marker=None,
            previous=True,
        )
        proposed_fields = _state_fields(
            candidate,
            safe_value,
            effective_sensitivity=effective,
            marker=marker,
            previous=False,
        )
        request = _runtime_request(candidate, proposed_fields, runtime_policy)
        try:
            runtime_result = total_field_receive_candidate(
                request,
                previous_state=previous_fields,
                observation_domains=self._observation_domains,
                policy=runtime_policy,
            )
        except TotalFieldGatewayError as exc:
            raise DomainCompletionError(exc.reason_code, exc.path) from exc
        runtime_decision = cast(str, runtime_result["final_decision"])
        final_decision = _more_restrictive(requested_decision, runtime_decision)
        runtime_commit = runtime_result["commit_applied"] is True
        if requested_decision != "ALLOW" and runtime_commit:
            raise DomainCompletionError("ALLOW_ONLY_COMMIT_INVARIANT_BROKEN")
        commit_applied = final_decision == "ALLOW" and runtime_commit
        committed_value = safe_value if commit_applied else deep_copy_json(previous_value)
        reasons = list(cast(list[str], runtime_result["decision_reason_codes"]))
        if requested_reason not in reasons:
            reasons.append(requested_reason)
        reasons = sorted(frozenset(reasons))
        result: dict[str, JSONValue] = {
            "schema_version": RESULT_SCHEMA_VERSION,
            "run_id": RUN_ID,
            "candidate_hash": candidate.candidate_hash,
            "domain": candidate.domain,
            "entity_ref": candidate.entity_ref,
            "attribute_name": candidate.attribute_name,
            "source_mode": candidate.source_mode,
            "sensitivity": effective,
            "fixed_point_status": cast(str, runtime_result["fixed_point_status"]),
            "runtime_final_decision": runtime_decision,
            "final_decision": final_decision,
            "decision_reason_codes": reasons,
            "commit_applied": commit_applied,
            "previous": deep_copy_json(previous_value),
            "proposed": safe_value,
            "committed": committed_value,
            "state_ref": cast(str, runtime_result["state_ref"]),
            "tfid": cast(str, runtime_result["tfid"]),
            "total_field_hash": cast(str, runtime_result["total_field_hash"]),
            "candidate_source_is_authority": False,
            "cloud_llm_is_committer": False,
            "xiaoj_is_final_authority": False,
            "persona_governance_separation": "PASS",
            "total_field_gateway": GATEWAY_REF,
            "runtime_result_sha256": canonical_sha256(runtime_result),
        }
        copied = deep_copy_json(result)
        assert isinstance(copied, dict)
        return copied

    def receive_candidate(
        self,
        candidate: Mapping[str, Any],
        *,
        previous_value: JSONValue,
    ) -> dict[str, JSONValue]:
        """Validate and adjudicate one candidate through the common gateway."""

        validated = validate_candidate(candidate)
        adapter_for(validated.domain).adapt(validated.to_dict())
        return self._receive_validated(
            validated, previous_value=deep_copy_json(previous_value)
        )

    def receive_batch(
        self,
        candidates: Sequence[Mapping[str, Any]],
        *,
        previous_values: Mapping[str, Any],
        forced_hold_reason: str | None = None,
    ) -> tuple[dict[str, JSONValue], ...]:
        """Independently adjudicate unique candidates; one failure cannot commit peers."""

        previous = deep_copy_json(dict(previous_values))
        if not isinstance(previous, dict):
            raise DomainCompletionError("PREVIOUS_VALUES_INVALID")
        accepted: list[GovernanceCandidate] = []
        rejected: list[dict[str, JSONValue]] = []
        seen_hashes: set[str] = set()
        for raw in candidates:
            try:
                item = validate_candidate(raw)
                adapter_for(item.domain).adapt(item.to_dict())
            except DomainCompletionError as exc:
                rejected.append(
                    {
                        "schema_version": RESULT_SCHEMA_VERSION,
                        "run_id": RUN_ID,
                        "candidate_hash": None,
                        "final_decision": "BLOCK",
                        "decision_reason_codes": [exc.reason_code],
                        "commit_applied": False,
                        "total_field_gateway": GATEWAY_REF,
                    }
                )
                continue
            if item.candidate_hash in seen_hashes:
                continue
            seen_hashes.add(item.candidate_hash)
            accepted.append(item)
        fingerprints: dict[str, set[str]] = {}
        for item in accepted:
            fingerprints.setdefault(item.identity_key, set()).add(
                _candidate_semantic_fingerprint(item)
            )
        results: list[dict[str, JSONValue]] = []
        for item in accepted:
            previous_value = cast(JSONValue, previous.get(item.identity_key))
            results.append(
                self._receive_validated(
                    item,
                    previous_value=previous_value,
                    conflict=len(fingerprints[item.identity_key]) > 1,
                    forced_hold_reason=forced_hold_reason,
                )
            )
        results.extend(rejected)
        return tuple(cast(dict[str, JSONValue], deep_copy_json(item)) for item in results)

    def _receive_from_provider(
        self,
        provider: CompletionProvider,
        request_ref: str,
        source_mode: str,
        previous_values: Mapping[str, Any],
    ) -> tuple[dict[str, JSONValue], ...]:
        candidates = provider.candidates_for(request_ref, source_mode)
        return self.receive_batch(candidates, previous_values=previous_values)

    def total_field_pull(
        self,
        provider: CompletionProvider,
        request_ref: str,
        *,
        previous_values: Mapping[str, Any],
    ) -> tuple[dict[str, JSONValue], ...]:
        return self._receive_from_provider(
            provider, request_ref, "TOTAL_FIELD_PULL", previous_values
        )

    def llm_push(
        self,
        provider: CompletionProvider,
        request_ref: str,
        *,
        previous_values: Mapping[str, Any],
    ) -> tuple[dict[str, JSONValue], ...]:
        return self._receive_from_provider(
            provider, request_ref, "LLM_PUSH", previous_values
        )

    def xiaoj_local(
        self,
        provider: CompletionProvider,
        request_ref: str,
        *,
        persona_text: str,
        previous_values: Mapping[str, Any],
    ) -> tuple[dict[str, JSONValue], ...]:
        candidates = provider.candidates_for(request_ref, "XIAOJ_LOCAL")
        governance = tuple(
            build_xiaoj_envelope(persona_text, item).governance_payload()
            for item in candidates
        )
        return self.receive_batch(governance, previous_values=previous_values)


def receive_candidate(
    candidate: Mapping[str, Any],
    *,
    previous_value: JSONValue,
    observation_domains: Mapping[str, Any],
) -> dict[str, JSONValue]:
    """Functional facade for the single domain-completion adapter."""

    return DomainCompletionTotalFieldGateway(
        observation_domains=observation_domains
    ).receive_candidate(candidate, previous_value=previous_value)


__all__ = [
    "ADAPTER_GATEWAY_REF",
    "DomainCompletionTotalFieldGateway",
    "GATEWAY_REF",
    "RESULT_SCHEMA_VERSION",
    "receive_candidate",
]
