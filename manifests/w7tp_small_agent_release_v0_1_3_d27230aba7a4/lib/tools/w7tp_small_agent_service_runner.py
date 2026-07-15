#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-shot, stdio-only runner for the candidate W7TP small agent.

The runner composes the existing candidate receiver, reference resolvers,
reconstruction builder, Total Field gateway, and ALLOW-only commit guard.  It
does not listen on a port, contact an LLM, persist governance payloads, or
create another D8 adjudicator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence, cast

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.tfct_true8d_runtime_candidate import deep_copy_json
from tools.total_field_candidate_gateway import llm_push, total_field_pull
from tools.w7tp_small_transport_agent_candidate import (
    AgentVersion,
    CandidateReceiver,
    CapabilityManifest,
    GatewayResponse,
    ReconstructionRequest,
    SmallTransportAgentError,
    TransportCandidate,
    apply_allow_only_commit,
    build_equivalence_verification_request,
    submit_to_gateway,
)


RUNNER_SCHEMA_VERSION = "w7tp-small-agent-service-runner/v0.1"
VECTOR_SCHEMA_VERSION = "w7tp-small-agent-deployment-vectors/v0.1"
COMMON_RECEIVE_PATH = "AgentService._receive_through_gateway/v0.1"
SOURCE_MODES = frozenset({"TOTAL_FIELD_PULL", "LLM_PUSH"})
DEFAULT_STATE_DIR = Path.home() / ".local" / "state" / "w7tp-small-agent"
AUDIT_FILENAME = "latest_audit.json"
_D1_KEYS = frozenset({"intent_ref", "task_ref", "goal_ref"})
_MANIFEST_KEYS = frozenset(
    {
        "agent_ref",
        "version",
        "protocol_version",
        "supported_schema_versions",
        "supported_rule_refs",
        "supported_reconstructors",
        "available_asset_refs",
        "observation_domain_ref",
        "privacy_boundary_ref",
        "execution_permissions",
    }
)
_D7_RAW_KEYS = frozenset(
    {
        "body",
        "bytes",
        "content",
        "data",
        "file",
        "payload",
        "plaintext",
        "raw",
        "raw_data",
        "raw_payload",
        "secret",
    }
)
_AUDIT_KEYS = frozenset(
    {
        "schema_version",
        "status",
        "source_mode",
        "common_receive_path",
        "agent_ref",
        "candidate_ref",
        "rule_ref",
        "observation_domain_ref",
        "manifest_hash",
        "candidate_hash",
        "d1_projection_hash",
        "gateway_result_hash",
        "committed_hash",
        "final_decision",
        "commit_applied",
        "tfid",
        "total_field_hash",
        "test_only",
    }
)


class ServiceError(ValueError):
    """Stable service error that never contains caller governance content."""

    def __init__(self, reason_code: str, path: str = "$") -> None:
        """Initialize the error from one stable code and structural path."""

        self.reason_code = reason_code
        self.path = path
        super().__init__(f"{reason_code}:{path}")


def _copy(value: Any, path: str = "$") -> Any:
    """Return a detached strict JSON value and translate core errors."""

    try:
        return deep_copy_json(value)
    except Exception as exc:
        raise ServiceError("INVALID_JSON_VALUE", path) from exc


def canonical_json(value: Any) -> str:
    """Serialize a strict JSON value with the repository canonical form."""

    try:
        return json.dumps(
            _copy(value),
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ServiceError("INVALID_JSON_VALUE") from exc


def canonical_sha256(value: Any) -> str:
    """Return a deterministic SHA-256 over canonical UTF-8 JSON."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Decode an object while rejecting duplicate JSON members."""

    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ServiceError("DUPLICATE_JSON_MEMBER", f"$.{key}")
        result[key] = value
    return result


def _reject_constant(token: str) -> None:
    """Reject JSON NaN and Infinity tokens deterministically."""

    raise ServiceError("NON_FINITE_JSON_NUMBER", f"$.{token}")


def load_json_file(path: Path | str) -> dict[str, Any]:
    """Load one UTF-8 JSON object with duplicate and non-finite rejection."""

    source = Path(path)
    try:
        value = json.loads(
            source.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_pairs,
            parse_constant=_reject_constant,
        )
    except ServiceError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ServiceError("JSON_READ_FAILED", str(source)) from exc
    if not isinstance(value, dict):
        raise ServiceError("JSON_OBJECT_REQUIRED", str(source))
    return cast(dict[str, Any], _copy(value))


def _non_empty_string(value: Any, path: str) -> str:
    """Return one required non-empty string or raise a stable error."""

    if not isinstance(value, str) or not value:
        raise ServiceError("REQUIRED_REFERENCE_MISSING", path)
    return value


def _string_tuple(value: Any, path: str) -> tuple[str, ...]:
    """Validate a unique JSON array of non-empty reference strings."""

    if not isinstance(value, list):
        raise ServiceError("REFERENCE_ARRAY_REQUIRED", path)
    result = tuple(
        _non_empty_string(item, f"{path}[{index}]")
        for index, item in enumerate(value)
    )
    if len(result) != len(frozenset(result)):
        raise ServiceError("DUPLICATE_REFERENCE", path)
    return result


def build_capability_manifest(config: Mapping[str, Any]) -> CapabilityManifest:
    """Build the existing immutable capability manifest from a closed mapping."""

    if not isinstance(config, Mapping):
        raise ServiceError("CAPABILITY_MANIFEST_OBJECT_REQUIRED", "$.capability_manifest")
    copied = _copy(dict(config), "$.capability_manifest")
    if not isinstance(copied, dict):
        raise ServiceError("CAPABILITY_MANIFEST_OBJECT_REQUIRED", "$.capability_manifest")
    keys = frozenset(copied)
    if keys != _MANIFEST_KEYS:
        reason = "CAPABILITY_MANIFEST_MEMBER_MISMATCH"
        raise ServiceError(reason, "$.capability_manifest")
    try:
        return CapabilityManifest(
            agent_version=AgentVersion(
                agent_ref=_non_empty_string(
                    copied["agent_ref"], "$.capability_manifest.agent_ref"
                ),
                version=_non_empty_string(
                    copied["version"], "$.capability_manifest.version"
                ),
                protocol_version=_non_empty_string(
                    copied["protocol_version"],
                    "$.capability_manifest.protocol_version",
                ),
            ),
            supported_schema_versions=_string_tuple(
                copied["supported_schema_versions"],
                "$.capability_manifest.supported_schema_versions",
            ),
            supported_rule_refs=_string_tuple(
                copied["supported_rule_refs"],
                "$.capability_manifest.supported_rule_refs",
            ),
            supported_reconstructors=_string_tuple(
                copied["supported_reconstructors"],
                "$.capability_manifest.supported_reconstructors",
            ),
            available_asset_refs=_string_tuple(
                copied["available_asset_refs"],
                "$.capability_manifest.available_asset_refs",
            ),
            observation_domain_ref=_non_empty_string(
                copied["observation_domain_ref"],
                "$.capability_manifest.observation_domain_ref",
            ),
            privacy_boundary_ref=_non_empty_string(
                copied["privacy_boundary_ref"],
                "$.capability_manifest.privacy_boundary_ref",
            ),
            execution_permissions=_string_tuple(
                copied["execution_permissions"],
                "$.capability_manifest.execution_permissions",
            ),
        )
    except SmallTransportAgentError as exc:
        raise ServiceError(exc.reason_code, "$.capability_manifest") from exc


def project_d1_intent(intent: Mapping[str, Any]) -> dict[str, str]:
    """Project the fixed intent contract into a detached D1 reference object."""

    if not isinstance(intent, Mapping):
        raise ServiceError("D1_INTENT_OBJECT_REQUIRED", "$.d1_intent")
    copied = _copy(dict(intent), "$.d1_intent")
    if not isinstance(copied, dict) or frozenset(copied) != _D1_KEYS:
        raise ServiceError("D1_INTENT_MEMBER_MISMATCH", "$.d1_intent")
    return {
        key: _non_empty_string(copied[key], f"$.d1_intent.{key}")
        for key in ("intent_ref", "task_ref", "goal_ref")
    }


def _find_d7_raw_key(value: Any, path: str = "$.D7") -> str | None:
    """Return the first D7 raw-content path while allowing opaque references."""

    if isinstance(value, dict):
        for key in sorted(value):
            child = f"{path}.{key}"
            if key.casefold() in _D7_RAW_KEYS:
                return child
            found = _find_d7_raw_key(value[key], child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found = _find_d7_raw_key(item, f"{path}[{index}]")
            if found is not None:
                return found
    return None


def _assert_d7_reference_only(gateway_request: Mapping[str, Any]) -> None:
    """Reject explicit raw content in D7 before entering the existing runtime."""

    resolved = gateway_request.get("resolved_fields")
    if not isinstance(resolved, Mapping) or "D7" not in resolved:
        return
    found = _find_d7_raw_key(resolved["D7"])
    if found is not None:
        raise ServiceError("D7_RAW_PAYLOAD_BLOCKED", found)


@dataclass(frozen=True, slots=True)
class HashOnlyAuditReporter:
    """Persist only deterministic hashes, statuses, and opaque references."""

    state_dir: Path = DEFAULT_STATE_DIR

    def report(self, record: Mapping[str, Any]) -> Path:
        """Atomically replace the latest bounded audit record."""

        copied = _copy(dict(record), "$.audit")
        if not isinstance(copied, dict) or not frozenset(copied).issubset(_AUDIT_KEYS):
            raise ServiceError("AUDIT_FIELD_NOT_ALLOWED", "$.audit")
        target_dir = Path(self.state_dir).expanduser()
        try:
            target_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            target = target_dir / AUDIT_FILENAME
            temporary = target_dir / f".{AUDIT_FILENAME}.tmp"
            with temporary.open("w", encoding="utf-8") as handle:
                handle.write(canonical_json(copied))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, target)
        except OSError as exc:
            raise ServiceError("AUDIT_WRITE_FAILED", str(target_dir)) from exc
        return target


class GatewayAdapter(Protocol):
    """Injectable adapter contract used without granting D8 authority."""

    test_only: bool

    def receive(
        self,
        request: Mapping[str, Any],
        *,
        previous_state: Mapping[str, Any],
        observation_domains: Mapping[str, Any],
        source_mode: str,
    ) -> Mapping[str, Any]:
        """Return gateway-owned evidence for one source mode."""

        raise ServiceError("GATEWAY_ADAPTER_INTERFACE_ONLY")


@dataclass(frozen=True, slots=True)
class _FixedDecisionGatewayAdapter:
    """Deterministic fixture adapter that is impossible to mistake for production."""

    result: Mapping[str, Any]
    test_only: bool = True

    def receive(
        self,
        request: Mapping[str, Any],
        *,
        previous_state: Mapping[str, Any],
        observation_domains: Mapping[str, Any],
        source_mode: str,
    ) -> Mapping[str, Any]:
        """Return one detached fixed decision without network or model access."""

        del request, previous_state, observation_domains
        if source_mode not in SOURCE_MODES:
            raise ServiceError("SOURCE_MODE_UNSUPPORTED", "$.source_mode")
        copied = _copy(dict(self.result), "$.gateway_results")
        if not isinstance(copied, dict):
            raise ServiceError("FIXTURE_GATEWAY_RESULT_INVALID", "$.gateway_results")
        return copied


@dataclass(frozen=True, slots=True)
class _CachedGatewayClient:
    """Expose already-received D8 evidence to the existing commit-guard bridge."""

    result: Mapping[str, Any]

    def receive_candidate(
        self, candidate: Mapping[str, Any], *, source_mode: str
    ) -> Mapping[str, Any]:
        """Return detached evidence while ignoring duplicate candidate transport."""

        del candidate
        if source_mode not in SOURCE_MODES:
            raise ServiceError("SOURCE_MODE_UNSUPPORTED", "$.source_mode")
        copied = _copy(dict(self.result), "$.gateway_result")
        if not isinstance(copied, dict):
            raise ServiceError("GATEWAY_RESULT_INVALID", "$.gateway_result")
        return copied


def _normalize_gateway_result(value: Mapping[str, Any]) -> dict[str, Any]:
    """Adapt existing runtime evidence to the small-agent response contract."""

    copied = _copy(dict(value), "$.gateway_result")
    if not isinstance(copied, dict):
        raise ServiceError("GATEWAY_RESULT_INVALID", "$.gateway_result")
    decision = copied.get("final_decision")
    commit_applied = copied.get("commit_applied")
    if decision not in {"ALLOW", "HOLD", "BLOCK", "QUARANTINE"}:
        raise ServiceError("GATEWAY_DECISION_INVALID", "$.gateway_result.final_decision")
    if not isinstance(commit_applied, bool):
        raise ServiceError("GATEWAY_COMMIT_FLAG_INVALID", "$.gateway_result.commit_applied")
    previous = copied.get("previous")
    proposed = copied.get("proposed")
    committed = copied.get("committed")
    if previous is None or proposed is None:
        raise ServiceError("GATEWAY_STATE_EVIDENCE_MISSING", "$.gateway_result")
    if committed is None:
        committed = proposed if decision == "ALLOW" and commit_applied else previous
    reasons = copied.get("decision_reason_codes")
    if isinstance(reasons, list) and reasons and isinstance(reasons[0], str):
        decision_reason = reasons[0]
    else:
        supplied_reason = copied.get("decision_reason")
        decision_reason = (
            supplied_reason
            if isinstance(supplied_reason, str) and supplied_reason
            else f"{decision}_GATEWAY_RESULT"
        )
    normalized: dict[str, Any] = {
        "final_decision": decision,
        "decision_reason": decision_reason,
        "committed": committed,
        "commit_applied": commit_applied,
    }
    for key in ("tfid", "total_field_hash"):
        item = copied.get(key)
        if isinstance(item, str) and item:
            normalized[key] = item
    return normalized


def _prepare_gateway_request(
    gateway_request: Mapping[str, Any], d1_projection: Mapping[str, str]
) -> dict[str, Any]:
    """Attach or verify the D1 projection without changing any other field."""

    copied = _copy(dict(gateway_request), "$.gateway_request")
    if not isinstance(copied, dict):
        raise ServiceError("GATEWAY_REQUEST_OBJECT_REQUIRED", "$.gateway_request")
    if not copied:
        return copied
    resolved = copied.get("resolved_fields")
    if not isinstance(resolved, dict):
        raise ServiceError("GATEWAY_RESOLVED_FIELDS_REQUIRED", "$.gateway_request.resolved_fields")
    supplied = resolved.get("D1")
    if supplied is not None and supplied != dict(d1_projection):
        raise ServiceError("D1_PROJECTION_MISMATCH", "$.gateway_request.resolved_fields.D1")
    resolved["D1"] = dict(d1_projection)
    _assert_d7_reference_only(copied)
    return copied


def _fixture_gateway_result(
    value: Mapping[str, Any],
    *,
    default_previous: Any,
    default_proposed: Any,
) -> dict[str, Any]:
    """Validate and complete one explicitly test-only fixed decision record."""

    copied = _copy(dict(value), "$.gateway_results")
    if not isinstance(copied, dict):
        raise ServiceError("FIXTURE_GATEWAY_RESULT_INVALID", "$.gateway_results")
    decision = copied.get("final_decision")
    applied = copied.get("commit_applied")
    previous = copied.get("previous", default_previous)
    proposed = copied.get("proposed", default_proposed)
    if decision not in {"ALLOW", "HOLD", "BLOCK", "QUARANTINE"}:
        raise ServiceError("FIXTURE_GATEWAY_DECISION_INVALID", "$.gateway_results")
    if not isinstance(applied, bool) or previous is None or proposed is None:
        raise ServiceError("FIXTURE_GATEWAY_RESULT_INVALID", "$.gateway_results")
    expected_committed = proposed if decision == "ALLOW" and applied else previous
    supplied_committed = copied.get("committed")
    if supplied_committed is not None and supplied_committed != expected_committed:
        raise ServiceError("FIXTURE_COMMITTED_STATE_MISMATCH", "$.gateway_results")
    copied["previous"] = previous
    copied["proposed"] = proposed
    copied["committed"] = expected_committed
    copied["decision_reason"] = f"TEST_ONLY_{decision}"
    return copied


class AgentService:
    """Compose the accepted agent and Total Field components in one-shot form."""

    def __init__(
        self,
        *,
        gateway_adapter: GatewayAdapter | None = None,
        audit_reporter: HashOnlyAuditReporter | None = None,
    ) -> None:
        """Bind an optional explicit adapter and bounded audit reporter."""

        self._gateway_adapter = gateway_adapter
        self._audit_reporter = audit_reporter

    def _receive_through_gateway(
        self,
        request: Mapping[str, Any],
        *,
        previous_state: Mapping[str, Any],
        observation_domains: Mapping[str, Any],
        source_mode: str,
    ) -> tuple[dict[str, Any], str, bool]:
        """Use the sole common ingress for both permitted source modes."""

        if source_mode not in SOURCE_MODES:
            raise ServiceError("SOURCE_MODE_UNSUPPORTED", "$.source_mode")
        if self._gateway_adapter is not None:
            supplied = self._gateway_adapter.receive(
                request,
                previous_state=previous_state,
                observation_domains=observation_domains,
                source_mode=source_mode,
            )
            result = _copy(dict(supplied), "$.gateway_result")
            if not isinstance(result, dict):
                raise ServiceError("GATEWAY_RESULT_INVALID", "$.gateway_result")
            return result, COMMON_RECEIVE_PATH, bool(self._gateway_adapter.test_only)
        if not request:
            raise ServiceError(
                "HOLD_VECTOR_GATEWAY_PROFILE_NOT_CONFIGURED",
                "$.gateway_request",
            )
        try:
            if source_mode == "TOTAL_FIELD_PULL":
                supplied = total_field_pull(
                    request,
                    previous_state=previous_state,
                    observation_domains=observation_domains,
                )
            else:
                supplied = llm_push(
                    request,
                    previous_state=previous_state,
                    observation_domains=observation_domains,
                )
        except Exception as exc:
            reason = getattr(exc, "reason_code", "TOTAL_FIELD_GATEWAY_FAILED")
            raise ServiceError(str(reason), "$.gateway_request") from exc
        result = _copy(dict(supplied), "$.gateway_result")
        if not isinstance(result, dict):
            raise ServiceError("GATEWAY_RESULT_INVALID", "$.gateway_result")
        return result, COMMON_RECEIVE_PATH, False

    def _prepare_agent(
        self, vector: Mapping[str, Any]
    ) -> tuple[CapabilityManifest, TransportCandidate, ReconstructionRequest, dict[str, str]]:
        """Validate manifest, candidate, references, reconstruction, and D1."""

        manifest_value = vector.get("capability_manifest")
        candidate_value = vector.get("candidate")
        d1_value = vector.get("d1_intent")
        if not isinstance(manifest_value, Mapping):
            raise ServiceError("CAPABILITY_MANIFEST_OBJECT_REQUIRED")
        if not isinstance(candidate_value, Mapping):
            raise ServiceError("CANDIDATE_OBJECT_REQUIRED", "$.candidate")
        if not isinstance(d1_value, Mapping):
            raise ServiceError("D1_INTENT_OBJECT_REQUIRED", "$.d1_intent")
        manifest = build_capability_manifest(manifest_value)
        try:
            candidate = TransportCandidate.from_mapping(candidate_value)
            received = CandidateReceiver(manifest).receive(candidate)
        except SmallTransportAgentError as exc:
            raise ServiceError(exc.reason_code, "$.candidate") from exc
        if received.status != "CANDIDATE" or received.reconstruction_request is None:
            raise ServiceError(received.reason_code, "$.candidate")
        return manifest, candidate, received.reconstruction_request, project_d1_intent(d1_value)

    def run_fixed_vector(
        self, vector: Mapping[str, Any], source_mode: str
    ) -> dict[str, Any]:
        """Run one fixed vector and return only hashes, statuses, and references."""

        copied = _copy(dict(vector), "$")
        if not isinstance(copied, dict):
            raise ServiceError("VECTOR_OBJECT_REQUIRED")
        if copied.get("schema_version") != VECTOR_SCHEMA_VERSION:
            raise ServiceError("VECTOR_SCHEMA_VERSION_UNSUPPORTED", "$.schema_version")
        manifest, candidate, reconstruction, d1 = self._prepare_agent(copied)
        gateway_value = copied.get("gateway_request")
        previous_value = copied.get("previous_state")
        domains_value = copied.get("observation_domains")
        if not isinstance(gateway_value, Mapping):
            raise ServiceError("GATEWAY_REQUEST_OBJECT_REQUIRED", "$.gateway_request")
        if not isinstance(previous_value, Mapping):
            raise ServiceError("PREVIOUS_STATE_OBJECT_REQUIRED", "$.previous_state")
        if not isinstance(domains_value, Mapping):
            raise ServiceError("OBSERVATION_DOMAINS_OBJECT_REQUIRED", "$.observation_domains")
        request = _prepare_gateway_request(gateway_value, d1)
        raw_result, marker, test_only = self._receive_through_gateway(
            request,
            previous_state=previous_value,
            observation_domains=domains_value,
            source_mode=source_mode,
        )
        normalized = _normalize_gateway_result(raw_result)
        previous = raw_result.get("previous")
        proposed = raw_result.get("proposed")
        if previous is None or proposed is None:
            raise ServiceError("GATEWAY_STATE_EVIDENCE_MISSING", "$.gateway_result")
        evidence_hash = canonical_sha256(normalized)
        equivalence = build_equivalence_verification_request(
            candidate_ref=candidate.candidate_ref,
            verification_level=candidate.reconstruction_mode,
            expected_state_ref=f"state-ref:sha256:{canonical_sha256(previous)}",
            reconstructed_state_ref=f"state-ref:sha256:{canonical_sha256(proposed)}",
            verifier_ref="verifier:w7tp-small-agent:local-equivalence/v0.1",
            evidence_refs=(f"sha256:{evidence_hash}",),
        )
        try:
            response: GatewayResponse = submit_to_gateway(
                _CachedGatewayClient(normalized),
                reconstruction,
                equivalence,
                source_mode=source_mode,
            )
            guard = apply_allow_only_commit(previous, proposed, response)
        except SmallTransportAgentError as exc:
            raise ServiceError(exc.reason_code, "$.gateway_result") from exc
        audit: dict[str, Any] = {
            "schema_version": RUNNER_SCHEMA_VERSION,
            "status": "PASS",
            "source_mode": source_mode,
            "common_receive_path": marker,
            "agent_ref": manifest.agent_version.agent_ref,
            "candidate_ref": candidate.candidate_ref,
            "rule_ref": candidate.rule_ref,
            "observation_domain_ref": candidate.observation_domain_ref,
            "manifest_hash": canonical_sha256(copied["capability_manifest"]),
            "candidate_hash": canonical_sha256(
                {
                    "candidate": copied["candidate"],
                    "d1_intent": d1,
                    "capability_manifest": copied["capability_manifest"],
                }
            ),
            "d1_projection_hash": canonical_sha256(d1),
            "gateway_result_hash": canonical_sha256(raw_result),
            "committed_hash": canonical_sha256(guard.committed),
            "final_decision": guard.final_decision,
            "commit_applied": guard.commit_applied,
            "tfid": normalized.get("tfid"),
            "total_field_hash": normalized.get("total_field_hash"),
            "test_only": test_only,
        }
        if self._audit_reporter is not None:
            self._audit_reporter.report(audit)
        return cast(dict[str, Any], _copy(audit))


def run_fixed_vector(vector: Mapping[str, Any], source_mode: str) -> dict[str, Any]:
    """Run one production-adapter vector through a fresh one-shot service."""

    return AgentService().run_fixed_vector(vector, source_mode)


def _run_fixture_decision(
    vector: Mapping[str, Any], decision_value: Mapping[str, Any], source_mode: str
) -> dict[str, Any]:
    """Run one fixed decision through the same service ingress for self-test."""

    if "previous_state" not in vector or "proposed_state" not in vector:
        raise ServiceError("FIXTURE_STATE_EVIDENCE_MISSING", "$")
    result = _fixture_gateway_result(
        decision_value,
        default_previous=vector["previous_state"],
        default_proposed=vector["proposed_state"],
    )
    service = AgentService(gateway_adapter=_FixedDecisionGatewayAdapter(result))
    return service.run_fixed_vector(vector, source_mode)


def run_self_test(vector: Mapping[str, Any]) -> dict[str, Any]:
    """Replay the fixed vector and verify candidate-only service invariants."""

    copied = _copy(dict(vector), "$")
    if not isinstance(copied, dict):
        raise ServiceError("VECTOR_OBJECT_REQUIRED")
    manifest, candidate, _request, d1 = AgentService()._prepare_agent(copied)
    results = copied.get("gateway_results")
    if not isinstance(results, dict):
        raise ServiceError("FIXTURE_GATEWAY_RESULTS_REQUIRED", "$.gateway_results")
    for decision in ("ALLOW", "HOLD", "BLOCK", "QUARANTINE"):
        value = results.get(decision)
        if not isinstance(value, Mapping):
            raise ServiceError("FIXTURE_GATEWAY_RESULT_MISSING", f"$.gateway_results.{decision}")
        if value.get("final_decision") != decision:
            raise ServiceError("FIXTURE_GATEWAY_DECISION_MISMATCH", f"$.gateway_results.{decision}")

    replay_left = _run_fixture_decision(copied, results["ALLOW"], "TOTAL_FIELD_PULL")
    replay_right = _run_fixture_decision(copied, results["ALLOW"], "TOTAL_FIELD_PULL")
    if replay_left != replay_right:
        raise ServiceError("CANDIDATE_REPLAY_MISMATCH")
    push = _run_fixture_decision(copied, results["ALLOW"], "LLM_PUSH")
    if replay_left["common_receive_path"] != push["common_receive_path"]:
        raise ServiceError("COMMON_RECEIVE_PATH_MISMATCH")

    gates: dict[str, str] = {}
    for decision in ("ALLOW", "HOLD", "BLOCK", "QUARANTINE"):
        value = cast(Mapping[str, Any], results[decision])
        outcome = _run_fixture_decision(copied, value, "TOTAL_FIELD_PULL")
        expected_applied = decision == "ALLOW" and value.get("commit_applied") is True
        previous = value.get("previous", copied.get("previous_state"))
        proposed = value.get("proposed", copied.get("proposed_state"))
        if previous is None or proposed is None:
            raise ServiceError("FIXTURE_STATE_EVIDENCE_MISSING", f"$.gateway_results.{decision}")
        expected_state = proposed if expected_applied else previous
        if outcome["commit_applied"] is not expected_applied:
            raise ServiceError("ALLOW_ONLY_COMMIT_FAILED", f"$.gateway_results.{decision}")
        if outcome["committed_hash"] != canonical_sha256(expected_state):
            raise ServiceError("COMMITTED_STATE_GUARD_FAILED", f"$.gateway_results.{decision}")
        gates[decision] = "PASS"

    persona_a = cast(dict[str, Any], _copy(copied))
    persona_b = cast(dict[str, Any], _copy(copied))
    persona_a["persona_text"] = "TEST_ONLY_PERSONA_A"
    persona_b["persona_text"] = "TEST_ONLY_PERSONA_B"
    persona_a_result = _run_fixture_decision(
        persona_a, results["ALLOW"], "TOTAL_FIELD_PULL"
    )
    persona_b_result = _run_fixture_decision(
        persona_b, results["ALLOW"], "TOTAL_FIELD_PULL"
    )
    if persona_a_result["candidate_hash"] != persona_b_result["candidate_hash"]:
        raise ServiceError("PERSONA_GOVERNANCE_SEPARATION_FAILED")
    try:
        _assert_d7_reference_only({"resolved_fields": {"D7": {"payload": "TEST_ONLY"}}})
    except ServiceError as exc:
        if exc.reason_code != "D7_RAW_PAYLOAD_BLOCKED":
            raise
    else:
        raise ServiceError("D7_RAW_PAYLOAD_GUARD_FAILED")

    gateway_request = copied.get("gateway_request")
    gateway_profile_status = "READY"
    production_results: dict[str, Any] = {}
    if not isinstance(gateway_request, dict) or not gateway_request:
        gateway_profile_status = "HOLD_VECTOR_GATEWAY_PROFILE_NOT_CONFIGURED"
    else:
        production_service = AgentService()
        production_results["TOTAL_FIELD_PULL"] = production_service.run_fixed_vector(
            copied, "TOTAL_FIELD_PULL"
        )
        production_results["LLM_PUSH"] = production_service.run_fixed_vector(
            copied, "LLM_PUSH"
        )
        if (
            production_results["TOTAL_FIELD_PULL"]["common_receive_path"]
            != production_results["LLM_PUSH"]["common_receive_path"]
        ):
            raise ServiceError("COMMON_RECEIVE_PATH_MISMATCH")

    result = {
        "schema_version": RUNNER_SCHEMA_VERSION,
        "status": "PASS",
        "agent_ref": manifest.agent_version.agent_ref,
        "candidate_ref": candidate.candidate_ref,
        "capability_manifest": "PASS",
        "d1_projection": "PASS",
        "d1_projection_hash": canonical_sha256(d1),
        "candidate_replay": "PASS",
        "candidate_hash": replay_left["candidate_hash"],
        "common_receive_path": "PASS",
        "common_receive_path_marker": COMMON_RECEIVE_PATH,
        "allow_only_commit": "PASS",
        "commit_gates": gates,
        "persona_governance_separation": "PASS",
        "d7_reference_only": "PASS",
        "fixture_gateway": "TEST_ONLY",
        "total_field_pull": "TEST_ONLY_PASS",
        "llm_push": "TEST_ONLY_PASS",
        "llm_direct_commit": "BLOCKED",
        "gateway_profile_status": gateway_profile_status,
        "production_gateway_results_hash": (
            canonical_sha256(production_results) if production_results else None
        ),
    }
    return cast(dict[str, Any], _copy(result))


def _json_from_stdin() -> dict[str, Any]:
    """Read one strict JSON object from standard input."""

    try:
        value = json.loads(
            sys.stdin.read(),
            object_pairs_hook=_strict_pairs,
            parse_constant=_reject_constant,
        )
    except ServiceError:
        raise
    except json.JSONDecodeError as exc:
        raise ServiceError("STDIN_JSON_INVALID") from exc
    if not isinstance(value, dict):
        raise ServiceError("STDIN_JSON_OBJECT_REQUIRED")
    return cast(dict[str, Any], _copy(value))


def _installed_entrypoint(release_dir: Path | str) -> Path:
    """Resolve one executable installed entrypoint within its release root."""

    try:
        root = Path(release_dir).expanduser().resolve(strict=True)
        binary = (root / "bin" / "w7tp-small-agent").resolve(strict=True)
    except OSError as exc:
        raise ServiceError("RUNTIME_ENTRYPOINT_MISSING", "bin/w7tp-small-agent") from exc
    if root not in binary.parents or not binary.is_file():
        raise ServiceError("RUNTIME_ENTRYPOINT_INVALID", "bin/w7tp-small-agent")
    if not os.access(binary, os.X_OK):
        raise ServiceError("RUNTIME_ENTRYPOINT_NOT_EXECUTABLE", "bin/w7tp-small-agent")
    return binary


def _service_environment() -> dict[str, str]:
    """Return a minimal child environment with no inherited PYTHONPATH."""

    return {
        "HOME": str(Path.home()),
        "LANG": "C.UTF-8",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
    }


def run_installed_service(release_dir: Path | str) -> int:
    """Call the installed foreground service and forward normal stop signals."""

    binary = _installed_entrypoint(release_dir)
    try:
        process = subprocess.Popen(
            [str(binary), "service-run"],
            cwd="/",
            env=_service_environment(),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ServiceError("RUNTIME_SERVICE_COMMAND_FAILED") from exc
    previous_handlers = {
        signal_number: signal.getsignal(signal_number)
        for signal_number in (signal.SIGTERM, signal.SIGINT)
    }

    def forward_stop(signal_number: int, _frame: Any) -> None:
        """Forward an authorized stop signal to the foreground child."""

        if process.poll() is None:
            process.send_signal(signal_number)

    try:
        for signal_number in previous_handlers:
            signal.signal(signal_number, forward_stop)
        return process.wait()
    finally:
        for signal_number, handler in previous_handlers.items():
            signal.signal(signal_number, handler)


def _parser() -> argparse.ArgumentParser:
    """Build the stdio-only command parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    self_test = subparsers.add_parser("self-test", help="run a fixed vector")
    self_test.add_argument("--vector", required=True, type=Path)
    handle = subparsers.add_parser("handle-json", help="handle one stdin vector")
    handle.add_argument("--source-mode", choices=sorted(SOURCE_MODES), required=True)
    handle.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    service = subparsers.add_parser(
        "service-run", help="delegate to the installed foreground entrypoint"
    )
    service.add_argument("--release-dir", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run one self-test or one JSON request without opening a port."""

    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "service-run":
            return run_installed_service(arguments.release_dir)
        if arguments.command == "self-test":
            result = run_self_test(load_json_file(arguments.vector))
        else:
            vector = _json_from_stdin()
            service = AgentService(
                audit_reporter=HashOnlyAuditReporter(Path(arguments.state_dir))
            )
            result = service.run_fixed_vector(vector, arguments.source_mode)
        print(canonical_json(result))
        return 0
    except ServiceError as exc:
        print(
            canonical_json(
                {
                    "schema_version": RUNNER_SCHEMA_VERSION,
                    "status": "HOLD",
                    "reason_code": exc.reason_code,
                    "path": exc.path,
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = (
    "AgentService",
    "COMMON_RECEIVE_PATH",
    "DEFAULT_STATE_DIR",
    "HashOnlyAuditReporter",
    "RUNNER_SCHEMA_VERSION",
    "ServiceError",
    "build_capability_manifest",
    "canonical_json",
    "canonical_sha256",
    "load_json_file",
    "main",
    "project_d1_intent",
    "run_fixed_vector",
    "run_installed_service",
    "run_self_test",
)
