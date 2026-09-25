#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Forty-five focused conformance tests for the TRUE8D runtime candidate."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.adi_index_strategy_candidate import (  # noqa: E402
    ADIInputContract,
    DeterministicFixtureADIIndexStrategy,
    DisabledADIIndexStrategy,
)
from tools.d3_coordinate_transition_candidate import (  # noqa: E402
    legacy_packet_to_transition_inputs,
    transition_coordinate,
    verify_transition_record,
)
from tools.eightd_gte_parser_candidate import (  # noqa: E402
    EightDGTEParserCandidate,
    GTECandidateParseError,
)
from tools.tfct_true8d_runtime_candidate import (  # noqa: E402
    Event,
    ObservationDomain,
    canonical_json,
    compare_tfs_equivalence,
    load_policy,
    run_convergence,
)
from tools.total_field_candidate_gateway import (  # noqa: E402
    TotalFieldGatewayError,
    llm_push,
    total_field_pull,
)
from tools.w7tp_small_transport_agent_candidate import (  # noqa: E402
    AgentVersion,
    CandidateReceiver,
    CapabilityManifest,
    GatewayResponse,
    SmallTransportAgentError,
    TransportCandidate,
)
from tools.xiaoj_candidate_adapter import (  # noqa: E402
    InMemoryCandidateProvider,
    XiaoJCandidateError,
    build_candidate_envelope,
)


FIXTURE_PATH = ROOT / "tests/fixtures/tfct_true8d_runtime_candidate_vectors.json"
PROFILE_SCHEMA_PATH = (
    ROOT / "schemas/field/8d_gte_runtime_candidate_profile_v0_1.schema.json"
)
ACTIVE_CANONICAL_PATH = (
    ROOT
    / "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_CANONICAL.json"
)


def _reverse_objects(value: Any) -> Any:
    """Recursively reverse object insertion order without changing values."""

    if isinstance(value, dict):
        return {
            key: _reverse_objects(value[key])
            for key in reversed(tuple(value.keys()))
        }
    if isinstance(value, list):
        return [_reverse_objects(item) for item in value]
    return value


class TFCTTrue8DRuntimeCandidateTests(unittest.TestCase):
    """Focused deterministic, governance, adapter, and fallback checks."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.vectors = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        cls.parser = EightDGTEParserCandidate()
        cls.policy = load_policy()

    def _request(self) -> dict[str, Any]:
        """Return a fresh closed runtime request without wrapper source mode."""

        return {
            "profile_schema_version": "8d-gte-runtime-candidate-profile/0.1",
            "profile_type": "RUNTIME_REQUEST",
            "gte": copy.deepcopy(self.vectors["gte_candidate"]),
            "event": copy.deepcopy(self.vectors["event"]),
            "rule_set_ref": self.vectors["rule_set_ref"],
            "resolved_fields": copy.deepcopy(self.vectors["resolved_fields"]),
            "context": copy.deepcopy(self.vectors["context"]),
            "adi_requested": False,
        }

    def _pull(
        self,
        request: dict[str, Any] | None = None,
        *,
        previous: dict[str, Any] | None = None,
        domains: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Evaluate one fresh deterministic pull request."""

        return total_field_pull(
            request or self._request(),
            previous_state=previous or copy.deepcopy(self.vectors["previous"]),
            observation_domains=(
                copy.deepcopy(self.vectors["observation_domains"])
                if domains is None
                else domains
            ),
        )

    def _core(
        self,
        *,
        previous: dict[str, Any] | None = None,
        candidate: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        rule_set_ref: str | None = None,
        event_id: str | None = None,
        logical_time: Any | None = None,
        observation_domain_ref: str | None = None,
        configured: bool = True,
    ):
        """Run the candidate core with fixed caller-controlled inputs."""

        domain_ref = observation_domain_ref or self.vectors["gte_candidate"][
            "observation_domain_ref"
        ]
        event = Event(
            event_ref=self.vectors["event"]["event_ref"],
            event_code=self.vectors["event"]["event_code"],
            event_id=event_id or self.vectors["event"]["event_id"],
            logical_time=(
                self.vectors["event"]["logical_time"]
                if logical_time is None
                else logical_time
            ),
            rule_set_ref=rule_set_ref or self.vectors["rule_set_ref"],
            priority_policy_ref=self.vectors["gte_candidate"]["priority_policy_ref"],
            observation_domain_ref=domain_ref,
        )
        domain = ObservationDomain(
            observation_domain_ref=domain_ref,
            configured=configured,
            observations={"observation_ref": "observation:fixture:v0.1"},
        )
        return run_convergence(
            previous=(
                copy.deepcopy(self.vectors["previous"])
                if previous is None
                else previous
            ),
            candidate=(
                copy.deepcopy(self.vectors["resolved_fields"])
                if candidate is None
                else candidate
            ),
            event=event,
            observation_domain=domain,
            context=(
                {"source_mode": "TOTAL_FIELD_PULL"}
                if context is None
                else context
            ),
            policy=self.policy,
        )

    def _manifest(self) -> CapabilityManifest:
        """Build the fixed small-agent capability manifest."""

        item = self.vectors["small_agent"]["manifest"]
        return CapabilityManifest(
            agent_version=AgentVersion(
                item["agent_ref"], item["agent_version"], item["protocol_version"]
            ),
            supported_schema_versions=(item["supported_schema_version"],),
            supported_rule_refs=(item["rule_ref"],),
            supported_reconstructors=(item["reconstructor_ref"],),
            available_asset_refs=(item["asset_ref"],),
            observation_domain_ref=item["observation_domain_ref"],
            privacy_boundary_ref=item["privacy_boundary_ref"],
            execution_permissions=(
                "RESOLVE_REFERENCE",
                "BUILD_RECONSTRUCTION_REQUEST",
                "REQUEST_EQUIVALENCE_VERIFICATION",
                "SUBMIT_CANDIDATE",
            ),
        )

    def _transport_candidate(self, **updates: Any) -> TransportCandidate:
        """Build one fixed small-agent candidate with explicit overrides."""

        value = copy.deepcopy(self.vectors["small_agent"]["candidate"])
        value.update(updates)
        return TransportCandidate.from_mapping(value)

    def _adi_input(self, **updates: Any) -> ADIInputContract:
        """Build one complete deterministic ADI fixture contract."""

        value = copy.deepcopy(self.vectors["adi_fixture"])
        value.update(updates)
        value["candidate_refs"] = tuple(value["candidate_refs"])
        return ADIInputContract(**value)

    def test_01_identical_input_same_canonical_payload(self) -> None:
        first = self.parser.parse_dict(copy.deepcopy(self.vectors["gte_candidate"]))
        second = self.parser.parse_dict(copy.deepcopy(self.vectors["gte_candidate"]))
        self.assertEqual(first.canonical_payload, second.canonical_payload)

    def test_02_identical_input_same_candidate_hash(self) -> None:
        first = self.parser.parse_dict(copy.deepcopy(self.vectors["gte_candidate"]))
        second = self.parser.parse_dict(copy.deepcopy(self.vectors["gte_candidate"]))
        self.assertEqual(first.candidate_hash, second.candidate_hash)

    def test_03_identical_input_same_tfid(self) -> None:
        self.assertEqual(self._pull()["tfid"], self._pull()["tfid"])

    def test_04_identical_input_same_total_field_hash(self) -> None:
        self.assertEqual(
            self._pull()["total_field_hash"], self._pull()["total_field_hash"]
        )

    def test_05_key_order_does_not_change_result(self) -> None:
        normal = self.parser.parse_dict(copy.deepcopy(self.vectors["gte_candidate"]))
        reversed_value = self.parser.parse_dict(
            _reverse_objects(self.vectors["gte_candidate"])
        )
        self.assertEqual(normal.canonical_payload, reversed_value.canonical_payload)
        self.assertEqual(normal.candidate_hash, reversed_value.candidate_hash)

    def test_06_context_key_order_does_not_change_result(self) -> None:
        first = self._request()
        first["context"] = {
            "request_ref": "request:fixture:001",
            "d3_context": {"z_ref": "z:fixture", "a_ref": "a:fixture"},
        }
        second = copy.deepcopy(first)
        second["context"] = _reverse_objects(first["context"])
        self.assertEqual(self._pull(first), self._pull(second))

    def test_07_event_id_changes_result(self) -> None:
        baseline = self._pull()
        changed = self._request()
        changed["event"]["event_id"] = "event-id:fixture:002"
        replay = self._pull(changed)
        self.assertNotEqual(baseline["total_field_hash"], replay["total_field_hash"])
        self.assertNotEqual(
            baseline["d3_transition"]["transition_hash"],
            replay["d3_transition"]["transition_hash"],
        )

    def test_08_logical_time_changes_result(self) -> None:
        baseline = self._pull()
        changed = self._request()
        changed["event"]["logical_time"] = "logical-time:fixture:002"
        replay = self._pull(changed)
        self.assertNotEqual(baseline["total_field_hash"], replay["total_field_hash"])

    def test_09_rule_set_ref_changes_result(self) -> None:
        baseline = self._pull()
        changed = self._request()
        changed["rule_set_ref"] = "rules/tfct/normalize_v0_1"
        replay = self._pull(changed)
        self.assertNotEqual(baseline["total_field_hash"], replay["total_field_hash"])

    def test_10_observation_domain_ref_changes_result(self) -> None:
        baseline = self._pull()
        changed = self._request()
        new_ref = "observation-domain:fixture:v0.2"
        changed["gte"]["observation_domain_ref"] = new_ref
        domains = copy.deepcopy(self.vectors["observation_domains"])
        domains[new_ref] = copy.deepcopy(next(iter(domains.values())))
        replay = self._pull(changed, domains=domains)
        self.assertNotEqual(baseline["total_field_hash"], replay["total_field_hash"])

    def test_11_nan_is_rejected(self) -> None:
        value = copy.deepcopy(self.vectors["gte_candidate"])
        value["dimensions"]["D1_ref"] = float("nan")
        with self.assertRaises(GTECandidateParseError) as caught:
            self.parser.parse_dict(value)
        self.assertEqual(caught.exception.reason_code, "GTE_NON_FINITE_NUMBER")

    def test_12_infinity_is_rejected(self) -> None:
        value = copy.deepcopy(self.vectors["gte_candidate"])
        value["dimensions"]["D1_ref"] = float("inf")
        with self.assertRaises(GTECandidateParseError) as caught:
            self.parser.parse_dict(value)
        self.assertEqual(caught.exception.reason_code, "GTE_NON_FINITE_NUMBER")

    def test_13_non_json_compatible_value_is_rejected(self) -> None:
        value = copy.deepcopy(self.vectors["gte_candidate"])
        value["dimensions"]["D1_ref"] = {"not-json"}
        with self.assertRaises(GTECandidateParseError) as caught:
            self.parser.parse_dict(value)
        self.assertEqual(caught.exception.reason_code, "GTE_NON_JSON_VALUE")

    def test_14_missing_dimension_is_rejected(self) -> None:
        value = copy.deepcopy(self.vectors["gte_candidate"])
        del value["dimensions"]["D8_ref"]
        with self.assertRaises(GTECandidateParseError) as caught:
            self.parser.parse_dict(value)
        self.assertEqual(caught.exception.reason_code, "GTE_MISSING_DIMENSION")

    def test_15_extra_field_is_rejected(self) -> None:
        value = copy.deepcopy(self.vectors["gte_candidate"])
        value["unexpected"] = "caller-private-fixture-marker"
        with self.assertRaises(GTECandidateParseError) as caught:
            self.parser.parse_dict(value)
        self.assertEqual(caught.exception.reason_code, "GTE_EXTRA_FIELD")
        self.assertNotIn("caller-private-fixture-marker", str(caught.exception))

    def test_16_candidate_cannot_commit(self) -> None:
        value = copy.deepcopy(self.vectors["gte_candidate"])
        value["verification"]["commit_applied"] = True
        with self.assertRaises(GTECandidateParseError) as caught:
            self.parser.parse_dict(value)
        self.assertEqual(caught.exception.reason_code, "GTE_CANDIDATE_COMMIT_FORBIDDEN")

    def test_17_llm_push_cannot_submit_committed_state(self) -> None:
        request = self._request()
        request["committed"] = copy.deepcopy(self.vectors["resolved_fields"])
        with self.assertRaises(TotalFieldGatewayError) as caught:
            llm_push(
                request,
                previous_state=copy.deepcopy(self.vectors["previous"]),
                observation_domains=copy.deepcopy(self.vectors["observation_domains"]),
            )
        self.assertEqual(
            caught.exception.reason_code, "BLOCK_UNAUTHORIZED_CLOUD_COMMIT"
        )

    def test_18_total_field_pull_cannot_bypass_receive_candidate(self) -> None:
        sentinel = {"gateway": "called"}
        with patch(
            "tools.total_field_candidate_gateway.receive_candidate",
            return_value=sentinel,
        ) as common:
            result = total_field_pull(
                self._request(),
                previous_state=copy.deepcopy(self.vectors["previous"]),
                observation_domains=copy.deepcopy(self.vectors["observation_domains"]),
            )
        self.assertEqual(result, sentinel)
        self.assertEqual(common.call_count, 1)
        self.assertEqual(common.call_args.args[0]["source_mode"], "TOTAL_FIELD_PULL")

    def test_19_allow_and_fixed_point_commits(self) -> None:
        result = self._pull()
        self.assertEqual(result["fixed_point_status"], "REACHED")
        self.assertEqual(result["final_decision"], "ALLOW")
        self.assertTrue(result["commit_applied"])
        self.assertEqual(result["committed"], result["proposed"])

    def test_20_hold_preserves_previous(self) -> None:
        result = self._pull(domains={})
        self.assertEqual(result["final_decision"], "HOLD")
        self.assertFalse(result["commit_applied"])
        self.assertEqual(result["committed"], result["previous"])

    def test_21_block_preserves_previous(self) -> None:
        candidate = copy.deepcopy(self.vectors["resolved_fields"])
        candidate["D8"]["final_decision"] = "ALLOW"
        candidate["D7"]["unsupported_body"] = True
        result = self._core(candidate=candidate)
        self.assertEqual(result.final_decision, "BLOCK")
        self.assertFalse(result.commit_applied)
        self.assertEqual(result.committed.to_dict(), result.previous.to_dict())

    def test_22_quarantine_preserves_previous(self) -> None:
        result = self._core(
            context={
                "source_mode": "TOTAL_FIELD_PULL",
                "hard_risk_codes": ["DB_WRITE_REQUESTED"],
            }
        )
        self.assertEqual(result.final_decision, "QUARANTINE")
        self.assertFalse(result.commit_applied)
        self.assertEqual(result.committed.to_dict(), result.previous.to_dict())

    def test_23_max_iterations_returns_hold(self) -> None:
        result = self._core(
            rule_set_ref="rules/tfct/test_timeout_v0_1",
            context={"source_mode": "TOTAL_FIELD_PULL", "test_fixture": True},
        )
        self.assertEqual(result.fixed_point_status, "MAX_ITERATIONS_REACHED")
        self.assertEqual(result.final_decision, "HOLD")
        self.assertIn("CONVERGENCE_TIMEOUT", result.decision_reason_codes)

    def test_24_cycle_returns_hold(self) -> None:
        result = self._core(
            rule_set_ref="rules/tfct/test_cycle_v0_1",
            context={"source_mode": "TOTAL_FIELD_PULL", "test_fixture": True},
        )
        self.assertEqual(result.fixed_point_status, "CYCLE_DETECTED")
        self.assertEqual(result.final_decision, "HOLD")
        self.assertIn("CONVERGENCE_CYCLE_DETECTED", result.decision_reason_codes)
        quarantined = self._core(
            rule_set_ref="rules/tfct/test_cycle_v0_1",
            context={
                "source_mode": "TOTAL_FIELD_PULL",
                "test_fixture": True,
                "hard_risk_codes": ["DB_WRITE_REQUESTED"],
            },
        )
        self.assertEqual(quarantined.final_decision, "QUARANTINE")
        blocked_candidate = copy.deepcopy(self.vectors["resolved_fields"])
        blocked_candidate["D8"]["final_decision"] = "ALLOW"
        blocked = self._core(
            candidate=blocked_candidate,
            rule_set_ref="rules/tfct/test_cycle_v0_1",
            context={"source_mode": "TOTAL_FIELD_PULL", "test_fixture": True},
        )
        self.assertEqual(blocked.final_decision, "BLOCK")

    def test_25_hard_risk_is_blocked_or_quarantined(self) -> None:
        result = self._core(
            context={
                "source_mode": "TOTAL_FIELD_PULL",
                "hard_risk_codes": ["ROUTER_WRITE_REQUESTED"],
                "password": True,
            }
        )
        self.assertIn(result.final_decision, {"BLOCK", "QUARANTINE"})
        self.assertIn("D6_HARD_RISK_QUARANTINED", result.decision_reason_codes)

    def test_26_sensitive_key_activates_d6_gate(self) -> None:
        result = self._core(
            context={"source_mode": "TOTAL_FIELD_PULL", "password": True}
        )
        self.assertIn(result.final_decision, {"HOLD", "BLOCK"})
        self.assertIn("D6_SENSITIVE_KEY_PRESENT", result.decision_reason_codes)
        previous = copy.deepcopy(self.vectors["previous"])
        previous["D3"]["password"] = True
        candidate = copy.deepcopy(self.vectors["resolved_fields"])
        candidate["D3"] = {}
        inherited = self._core(previous=previous, candidate=candidate)
        self.assertEqual(inherited.final_decision, "HOLD")
        self.assertFalse(inherited.commit_applied)
        proposed = copy.deepcopy(self.vectors["resolved_fields"])
        proposed["D3"]["nested"] = {
            "member_plaintext": "SENSITIVE-FIXTURE-VALUE-MUST-NOT-BE-ECHOED"
        }
        scanned = self._core(previous=previous, candidate=proposed)
        d6 = next(
            item
            for item in scanned.constraint_results
            if item.constraint_ref == "constraints/tfct/d6_sovereign_privacy_v0_1"
        )
        paths = d6.evidence["key_paths"]
        for state_name in ("previous", "proposed", "current", "committed"):
            self.assertTrue(
                any(path.startswith(f"$.{state_name}.") for path in paths),
                state_name,
            )
        self.assertNotIn(
            "SENSITIVE-FIXTURE-VALUE-MUST-NOT-BE-ECHOED",
            json.dumps(
                {
                    "decision_reason_codes": scanned.decision_reason_codes,
                    "d6_evidence": d6.evidence,
                },
                ensure_ascii=False,
            ),
        )

    def test_27_d7_accepts_reference_only_content(self) -> None:
        result = self._core()
        d7 = next(
            item
            for item in result.constraint_results
            if item.constraint_ref == "constraints/tfct/d7_reference_only_v0_1"
        )
        self.assertEqual(d7.outcome, "PASS")
        self.assertEqual(d7.reason_code, "D7_REFERENCE_ONLY_PASS")

    def test_28_d7_raw_payload_requires_raw_channel(self) -> None:
        for raw_key in (
            "raw_payload",
            "raw_data",
            "blob",
            "binary",
            "base64_payload",
            "plaintext",
            "content_bytes",
        ):
            candidate = copy.deepcopy(self.vectors["resolved_fields"])
            candidate["D7"] = {
                "reconstruction_condition": {
                    "nested": {raw_key: {"fixture": True}}
                }
            }
            result = self._core(candidate=candidate)
            self.assertEqual(result.final_decision, "HOLD", raw_key)
            self.assertIn("RAW_CHANNEL_REQUIRED", result.decision_reason_codes)

    def test_29_xiaoj_persona_is_excluded_from_governance_tfs(self) -> None:
        provider_source = self._request()
        provider = InMemoryCandidateProvider(
            provider_ref="provider:fixture:v0.1",
            model_ref="model:fixture:v0.1",
            governance_candidate=provider_source,
            persona_text="persona-alpha",
        )
        provider_source["context"]["after_construction"] = True
        supplied = provider.generate_candidate({"request_ref": "request:fixture:001"})
        self.assertNotIn("after_construction", supplied["governance_candidate"]["context"])
        first = build_candidate_envelope(
            source_mode="TOTAL_FIELD_PULL",
            model_ref=supplied["model_ref"],
            provider_ref=supplied["provider_ref"],
            event_ref=self.vectors["event"]["event_ref"],
            observation_domain_ref=self.vectors["gte_candidate"][
                "observation_domain_ref"
            ],
            rule_ref=self.vectors["rule_set_ref"],
            logical_time=self.vectors["event"]["logical_time"],
            persona_text="persona-alpha",
            governance_candidate=supplied["governance_candidate"],
        )
        second = build_candidate_envelope(
            source_mode="TOTAL_FIELD_PULL",
            model_ref=supplied["model_ref"],
            provider_ref=supplied["provider_ref"],
            event_ref=self.vectors["event"]["event_ref"],
            observation_domain_ref=self.vectors["gte_candidate"][
                "observation_domain_ref"
            ],
            rule_ref=self.vectors["rule_set_ref"],
            logical_time=self.vectors["event"]["logical_time"],
            persona_text="persona-beta",
            governance_candidate=supplied["governance_candidate"],
        )
        self.assertEqual(first.candidate_hash, second.candidate_hash)
        self.assertNotIn("persona_text", first.governance_payload())
        with self.assertRaises(TypeError):
            first.governance_candidate["final_decision"] = "ALLOW"
        result = self._pull(first.governance_payload())
        self.assertNotIn("persona-alpha", canonical_json(result["committed"]))

    def test_30_xiaoj_cannot_create_allow(self) -> None:
        with self.assertRaises(XiaoJCandidateError) as caught:
            build_candidate_envelope(
                source_mode="LLM_PUSH",
                model_ref="model:fixture:v0.1",
                provider_ref="provider:fixture:v0.1",
                event_ref=self.vectors["event"]["event_ref"],
                observation_domain_ref=self.vectors["gte_candidate"][
                    "observation_domain_ref"
                ],
                rule_ref=self.vectors["rule_set_ref"],
                logical_time=self.vectors["event"]["logical_time"],
                persona_text="persona-fixture",
                governance_candidate={"final_decision": "ALLOW"},
            )
        self.assertEqual(caught.exception.reason_code, "XIAOJ_DIRECT_AUTHORITY_BLOCKED")
        with self.assertRaises(SmallTransportAgentError) as direct:
            GatewayResponse(
                final_decision="ALLOW",
                decision_reason="forged",
                committed={"state": "forged"},
                commit_applied=True,
            )
        self.assertEqual(
            direct.exception.reason_code,
            "GATEWAY_RESPONSE_PROVENANCE_REQUIRED",
        )

    def test_31_pull_and_push_use_same_receive_path(self) -> None:
        with patch(
            "tools.total_field_candidate_gateway.receive_candidate",
            return_value={"gateway": "called"},
        ) as common:
            total_field_pull(
                self._request(),
                previous_state=copy.deepcopy(self.vectors["previous"]),
                observation_domains=copy.deepcopy(self.vectors["observation_domains"]),
            )
            llm_push(
                self._request(),
                previous_state=copy.deepcopy(self.vectors["previous"]),
                observation_domains=copy.deepcopy(self.vectors["observation_domains"]),
            )
        self.assertEqual(common.call_count, 2)
        modes = [call.args[0]["source_mode"] for call in common.call_args_list]
        self.assertEqual(modes, ["TOTAL_FIELD_PULL", "LLM_PUSH"])

    def test_32_small_agent_missing_asset(self) -> None:
        candidate = self._transport_candidate(asset_refs=["asset:missing:v0.1"])
        result = CandidateReceiver(self._manifest()).receive(candidate)
        self.assertEqual(result.status, "HOLD")
        self.assertEqual(result.reason_code, "MISSING_ASSET")
        base = self._manifest()
        incomplete = CapabilityManifest(
            agent_version=base.agent_version,
            supported_schema_versions=base.supported_schema_versions,
            supported_rule_refs=base.supported_rule_refs,
            supported_reconstructors=base.supported_reconstructors,
            available_asset_refs=base.available_asset_refs,
            observation_domain_ref=base.observation_domain_ref,
            privacy_boundary_ref=base.privacy_boundary_ref,
            execution_permissions=(),
        )
        permission_result = CandidateReceiver(incomplete).receive(
            self._transport_candidate()
        )
        self.assertEqual(permission_result.reason_code, "MISSING_EXECUTION_PERMISSION")

    def test_33_small_agent_version_mismatch(self) -> None:
        candidate = self._transport_candidate(required_agent_version="9.9.9")
        result = CandidateReceiver(self._manifest()).receive(candidate)
        self.assertEqual(result.status, "HOLD")
        self.assertEqual(result.reason_code, "VERSION_MISMATCH")

    def test_34_adi_not_requested_does_not_block_commit(self) -> None:
        adi = DisabledADIIndexStrategy().evaluate(ADIInputContract(requested=False))
        result = self._pull()
        self.assertEqual(adi.reason_code, "ADI_NOT_REQUESTED")
        self.assertTrue(result["commit_applied"])

    def test_35_adi_requested_without_strategy_holds(self) -> None:
        adi = DisabledADIIndexStrategy().evaluate(ADIInputContract(requested=True))
        request = self._request()
        request["adi_requested"] = True
        result = self._pull(request)
        self.assertEqual(adi.reason_code, "HOLD_ADI_NOT_CONFIGURED")
        self.assertEqual(result["final_decision"], "HOLD")
        self.assertIn("HOLD_ADI_NOT_CONFIGURED", result["decision_reason_codes"])
        forged = self._request()
        forged["adi_requested"] = True
        forged["context"]["test_fixture"] = True
        forged["context"]["adi_result"] = {
            "status": "CANDIDATE",
            "reason_code": "ADI_TEST_FIXTURE_RESULT",
            "TEST_ONLY": True,
        }
        with self.assertRaises(TotalFieldGatewayError) as caught:
            self._pull(forged)
        self.assertEqual(
            caught.exception.reason_code,
            "GATEWAY_TRUSTED_CONTEXT_FIELD_FORBIDDEN",
        )
        for reserved_key in (
            "adi_fixture",
            "adi_result",
            "TEST_ONLY",
            "test_fixture",
        ):
            nested = self._request()
            nested["context"]["nested"] = {"layer": {reserved_key: True}}
            with self.assertRaises(TotalFieldGatewayError) as nested_caught:
                self._pull(nested)
            self.assertEqual(
                nested_caught.exception.reason_code,
                "GATEWAY_TRUSTED_CONTEXT_FIELD_FORBIDDEN",
                reserved_key,
            )

    def test_36_fixture_adi_is_marked_test_only(self) -> None:
        result = DeterministicFixtureADIIndexStrategy().evaluate(self._adi_input())
        replay = DeterministicFixtureADIIndexStrategy().evaluate(self._adi_input())
        self.assertTrue(result.TEST_ONLY)
        self.assertEqual(result.reason_code, "ADI_TEST_FIXTURE_RESULT")
        self.assertEqual(result.result_hash, replay.result_hash)

    def test_37_cross_node_same_tfs_matches(self) -> None:
        first = self._core()
        second = self._core()
        comparison = compare_tfs_equivalence(first, second)
        self.assertEqual(comparison.status, "MATCH")
        self.assertTrue(comparison.canonical_tfs_match)
        self.assertTrue(comparison.state_ref_match)
        self.assertTrue(comparison.tfid_match)
        self.assertTrue(comparison.total_field_hash_match)
        self.assertEqual(comparison.difference_paths, ())

    def test_38_cross_node_different_tfs_mismatches(self) -> None:
        first = self._core()
        altered = first.tfs.to_dict()
        altered["state"]["D1"]["intent_ref"] = "intent:different:v0.1"
        comparison = compare_tfs_equivalence(first, altered)
        self.assertEqual(comparison.status, "MISMATCH")
        self.assertIn("$.state.D1.intent_ref", comparison.difference_paths)
        ref_only = first.tfs.to_dict()
        ref_only["state_ref"] = "tfs-state:candidate:v0.1:" + ("0" * 64)
        ref_comparison = compare_tfs_equivalence(first, ref_only)
        self.assertEqual(ref_comparison.status, "MISMATCH")
        self.assertFalse(ref_comparison.canonical_tfs_match)
        self.assertFalse(ref_comparison.state_ref_match)
        self.assertIn("$.state_ref", ref_comparison.difference_paths)
        tfid_only = first.tfs.to_dict()
        tfid_only["tfid"] = "tfid:candidate:v0.1:" + ("0" * 64)
        tfid_comparison = compare_tfs_equivalence(first, tfid_only)
        self.assertFalse(tfid_comparison.canonical_tfs_match)
        self.assertFalse(tfid_comparison.tfid_match)
        self.assertIn("$.tfid", tfid_comparison.difference_paths)
        hash_only = first.tfs.to_dict()
        hash_only["total_field_hash"] = "0" * 64
        hash_comparison = compare_tfs_equivalence(first, hash_only)
        self.assertFalse(hash_comparison.canonical_tfs_match)
        self.assertFalse(hash_comparison.total_field_hash_match)
        self.assertIn("$.total_field_hash", hash_comparison.difference_paths)

    def test_39_previous_input_is_not_mutated(self) -> None:
        previous = copy.deepcopy(self.vectors["previous"])
        baseline = copy.deepcopy(previous)
        self._pull(previous=previous)
        self.assertEqual(previous, baseline)

    def test_40_nested_input_is_not_shallowly_aliased(self) -> None:
        request = self._request()
        previous = copy.deepcopy(self.vectors["previous"])
        request_baseline = copy.deepcopy(request)
        previous_baseline = copy.deepcopy(previous)
        result = self._pull(request, previous=previous)
        result["proposed"]["D3"]["nested"]["lane"] = "mutated-result-only"
        self.assertEqual(request, request_baseline)
        self.assertEqual(previous, previous_baseline)

    def test_41_legacy_fields_require_compatibility_adapter(self) -> None:
        adapted = legacy_packet_to_transition_inputs(
            {
                "D3_coordinate": {"x": 0},
                "D6_gt": {"rule_ref": "legacy-safe-ref:v0.1"},
                "D7_risk": {"legacy": True},
                "D8_envelope": {"legacy": True},
            },
            event_code="STATE_UPDATE",
            event_id="event-id:legacy:001",
            logical_time="logical-time:legacy:001",
            rule_ref="rules/tfct/identity_v0_1",
        )
        self.assertEqual(adapted["previous_coord"], {"x": 0})
        self.assertEqual(
            adapted["context"]["d7_reference"]["rule_ref"],
            "legacy-safe-ref:v0.1",
        )
        marker = adapted["context"]["legacy_adapter"]
        self.assertEqual(marker["unmapped_decision_field"], "D7_risk")
        self.assertEqual(marker["unmapped_envelope_field"], "D8_envelope")

    def test_42_active_d6_d7_d8_semantics_are_preserved(self) -> None:
        active = json.loads(ACTIVE_CANONICAL_PATH.read_text(encoding="utf-8"))
        dimensions = {item["id"]: item["field_en"] for item in active["dimensions"]}
        self.assertEqual(dimensions["D6"], "Sovereign Privacy Field")
        self.assertEqual(
            dimensions["D7"],
            "Generative Transmission & Resource Routing Field",
        )
        self.assertEqual(
            dimensions["D8"],
            "Red-Team Detour Alert & Quarantine Field",
        )
        cases = (
            (
                ("dimensions", "D3_ref"),
                "field:unknown:D3:v0.1",
                "HOLD_DIMENSION_PROJECTION_NOT_CONFIGURED",
            ),
            (
                ("constraint_hypergraph_ref",),
                "constraints/unknown/v0_1",
                "HOLD_CONSTRAINT_HYPERGRAPH_NOT_CONFIGURED",
            ),
            (
                ("convergence_operator_ref",),
                "convergence/unknown/v0_1",
                "HOLD_CONVERGENCE_OPERATOR_NOT_CONFIGURED",
            ),
        )
        for path, unknown_ref, reason_code in cases:
            request = self._request()
            target = request["gte"]
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = unknown_ref
            result = self._pull(request)
            self.assertEqual(result["final_decision"], "HOLD", path)
            self.assertIn(reason_code, result["decision_reason_codes"])

    def test_43_existing_d3_engine_is_precisely_callable(self) -> None:
        record = transition_coordinate(
            previous_coord={"x": 0},
            event_code="STATE_UPDATE",
            event_id="event-id:d3:fixture:001",
            logical_time="logical-time:d3:fixture:001",
            rule_ref="rules/tfct/identity_v0_1",
            context={"coordinate_delta": {"x": 1}},
        )
        verification = verify_transition_record(record)
        self.assertEqual(record["proposed"], {"x": 1})
        self.assertTrue(verification["valid"])

    def test_44_d3_decision_metadata_stays_outside_d3_body(self) -> None:
        result = self._core()
        d3 = result.proposed.D3
        self.assertIsInstance(d3, dict)
        for forbidden in (
            "transition_hash",
            "event_id",
            "logical_time",
            "commit_applied",
            "final_decision",
        ):
            self.assertNotIn(forbidden, d3)
        self.assertIn("d3_transition", result.proposed.D4)
        self.assertEqual(
            result.proposed.D4["d3_transition"]["transition_hash"],
            result.d3_transition["transition_hash"],
        )

    def test_45_stable_error_codes_are_reproducible(self) -> None:
        profile_schema = json.loads(PROFILE_SCHEMA_PATH.read_text(encoding="utf-8"))
        runtime_result = profile_schema["$defs"]["runtime_result"]
        self.assertEqual(
            set(runtime_result["required"]), set(runtime_result["properties"])
        )
        cases: list[dict[str, Any]] = []
        extra = copy.deepcopy(self.vectors["gte_candidate"])
        extra["unexpected"] = True
        cases.append(extra)
        missing = copy.deepcopy(self.vectors["gte_candidate"])
        del missing["dimensions"]["D5_ref"]
        cases.append(missing)
        candidate_commit = copy.deepcopy(self.vectors["gte_candidate"])
        candidate_commit["verification"]["commit_applied"] = True
        cases.append(candidate_commit)
        committed_non_allow = copy.deepcopy(self.vectors["gte_candidate"])
        committed_non_allow["lifecycle"] = "COMMITTED"
        committed_non_allow["fixed_point_status"] = "REACHED"
        committed_non_allow["verification"] = {
            "final_decision": "BLOCK",
            "commit_applied": False,
        }
        committed_non_allow["tfs_result"] = {
            "state_ref": "state:fixture:v0.1",
            "tfid": "tfid:fixture:v0.1",
            "total_field_hash": "hash:fixture:v0.1",
        }
        cases.append(committed_non_allow)
        for value in cases:
            codes: list[str] = []
            for _ in range(2):
                try:
                    self.parser.parse_dict(copy.deepcopy(value))
                except GTECandidateParseError as error:
                    codes.append(error.reason_code)
            self.assertEqual(len(codes), 2)
            self.assertEqual(codes[0], codes[1])
        with tempfile.TemporaryDirectory(prefix="tfct-runtime-candidate-") as directory:
            root = Path(directory)
            duplicate = root / "duplicate.json"
            duplicate.write_text('{"same":1,"same":2}', encoding="utf-8")
            invalid = root / "invalid.json"
            invalid.write_text("{", encoding="utf-8")
            invalid_utf8 = root / "invalid-utf8.json"
            invalid_utf8.write_bytes(b"\xff")
            expected = (
                (duplicate, "GTE_DUPLICATE_KEY"),
                (invalid, "GTE_INVALID_JSON"),
                (invalid_utf8, "GTE_INVALID_UTF8"),
            )
            for path, reason_code in expected:
                replay_codes: list[str] = []
                for _ in range(2):
                    try:
                        self.parser.parse_file(path)
                    except GTECandidateParseError as error:
                        replay_codes.append(error.reason_code)
                self.assertEqual(replay_codes, [reason_code, reason_code])
        first = self._core(rule_set_ref="rules/tfct/not-registered:v0.1")
        second = self._core(rule_set_ref="rules/tfct/not-registered:v0.1")
        self.assertEqual(first.final_decision, "HOLD")
        self.assertEqual(first.decision_reason_codes, second.decision_reason_codes)
        self.assertIn("HOLD_RULE_SET_NOT_CONFIGURED", first.decision_reason_codes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
