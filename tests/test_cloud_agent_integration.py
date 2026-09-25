#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ten focused tests for Cloud -> XiaoJ -> Total Field integration."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.cloud_agent_candidate_provider import (  # noqa: E402
    CloudCandidateProvider,
)
from tools.total_field_candidate_gateway import (  # noqa: E402
    TotalFieldGatewayError,
    receive_candidate,
)
from tools.xiaoj_candidate_adapter import (  # noqa: E402
    build_candidate_envelope,
    cloud_push,
)


class FakeResponse:
    def __init__(self, generated: dict[str, Any]) -> None:
        self._generated = copy.deepcopy(generated)

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": json.dumps(
                                    self._generated,
                                    sort_keys=True,
                                    ensure_ascii=False,
                                )
                            }
                        ]
                    }
                }
            ]
        }


class FakeAuthorizedSession:
    def __init__(self, generated: dict[str, Any]) -> None:
        self._generated = copy.deepcopy(generated)
        self.call_count = 0

    def post(self, endpoint: str, *, json: dict[str, Any], timeout: int) -> FakeResponse:
        self.call_count += 1
        if not endpoint.startswith("https://") or timeout <= 0 or not json:
            raise AssertionError("invalid fake request")
        return FakeResponse(self._generated)


class FakeCloudProvider:
    """No-network provider implementing the direct cloud contract."""

    def __init__(self, result: dict[str, Any]) -> None:
        self._result = copy.deepcopy(result)
        self.call_count = 0

    def generate_candidate(self, prompt: str, context: dict) -> dict:
        if not prompt or not isinstance(context, dict):
            raise AssertionError("invalid fake provider call")
        self.call_count += 1
        return copy.deepcopy(self._result)


class CloudAgentIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.domain_ref = "observation-domain:cloud-agent:fixture:v0.1"
        self.observation_domains = {
            self.domain_ref: {
                "configured": True,
                "observations": {
                    "observation_ref": "observation:cloud-agent:fixture:v0.1"
                },
            }
        }
        self.previous = {
            "D1": {"intent_ref": "intent:cloud-agent:fixture:v0.1"},
            "D2": {"state_ref": "state:previous:cloud-agent:fixture:v0.1"},
            "D3": {"node_ref": "node:cloud-agent:fixture", "x": 0},
            "D4": {"evidence_ref": "evidence:previous:fixture:v0.1"},
            "D5": {"execution_ref": "execution:previous:fixture:v0.1"},
            "D6": {"privacy_boundary_ref": "privacy:cloud-agent:fixture:v0.1"},
            "D7": {
                "rule_ref": "reconstruction-rule:cloud-agent:fixture:v0.1",
                "routing_ref": "routing:cloud-agent:fixture:v0.1",
                "reconstruction_condition": "condition:cloud-agent:fixture:v0.1",
            },
            "D8": {"adjudication_policy_ref": "d8-policy:cloud-agent:fixture:v0.1"},
        }

    def _runtime_request(self) -> dict[str, Any]:
        event_ref = "event:cloud-agent:fixture:001"
        return {
            "profile_schema_version": "8d-gte-runtime-candidate-profile/0.1",
            "profile_type": "RUNTIME_REQUEST",
            "gte": {
                "schema_version": "8d-gte-candidate/0.1",
                "lifecycle": "CANDIDATE",
                "event_ref": event_ref,
                "observation_domain_ref": self.domain_ref,
                "dimensions": {
                    "D1_ref": "field/tfct/D1/v0_1",
                    "D2_ref": "field/tfct/D2/v0_1",
                    "D3_ref": "field/tfct/D3/v0_1",
                    "D4_ref": "field/tfct/D4/v0_1",
                    "D5_ref": "field/tfct/D5/v0_1",
                    "D6_ref": "field/tfct/D6/v0_1",
                    "D7_ref": "field/tfct/D7/v0_1",
                    "D8_ref": "field/tfct/D8/v0_1",
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
            "source_mode": "LLM_PUSH",
            "event": {
                "event_id": "event-id:cloud-agent:fixture:001",
                "event_ref": event_ref,
                "event_code": "STATE_UPDATE",
                "logical_time": "logical-time:cloud-agent:fixture:001",
            },
            "rule_set_ref": "rules/tfct/identity_v0_1",
            "resolved_fields": {
                "D1": {"intent_ref": "intent:cloud-agent:fixture:v0.1"},
                "D2": {"state_ref": "state:proposed:cloud-agent:fixture:v0.1"},
                "D3": {"node_ref": "node:cloud-agent:fixture", "x": 1},
                "D4": {"evidence_ref": "evidence:candidate:fixture:v0.1"},
                "D5": {"execution_ref": "execution:candidate:fixture:v0.1"},
                "D6": {"privacy_boundary_ref": "privacy:cloud-agent:fixture:v0.1"},
                "D7": {
                    "rule_ref": "reconstruction-rule:cloud-agent:fixture:v0.1",
                    "routing_ref": "routing:cloud-agent:fixture:v0.1",
                    "reconstruction_condition": "condition:cloud-agent:fixture:v0.1",
                },
                "D8": {
                    "adjudication_policy_ref": "d8-policy:cloud-agent:fixture:v0.1"
                },
            },
            "context": {"request_ref": "request:cloud-agent:fixture:001"},
            "adi_requested": False,
        }

    def _provider_result(self, request: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "source_mode": "LLM_PUSH",
            "provider_ref": "gcp",
            "model_ref": "cloud-llm",
            "candidate": copy.deepcopy(request or self._runtime_request()),
            "confidence": 0.8,
            "event_ref": "event:cloud-agent:fixture:001",
            "observation_domain_ref": self.domain_ref,
            "rule_ref": "rules/tfct/identity_v0_1",
            "candidate_only": True,
        }

    def _context(self, *, persona_text: str = "") -> dict[str, Any]:
        return {
            "event_ref": "event:cloud-agent:fixture:001",
            "observation_domain_ref": self.domain_ref,
            "rule_ref": "rules/tfct/identity_v0_1",
            "logical_time": "logical-time:cloud-agent:fixture:001",
            "previous_state": copy.deepcopy(self.previous),
            "observation_domains": copy.deepcopy(self.observation_domains),
            "persona_text": persona_text,
            "cloud_context": {"request_ref": "request:cloud-agent:fixture:001"},
            "cloud_project_id": "project-fixture",
            "cloud_location": "us-central1",
            "cloud_model_name": "model-fixture",
        }

    def _push(self, request: dict[str, Any] | None = None, *, persona_text: str = ""):
        provider = FakeCloudProvider(self._provider_result(request))
        result = cloud_push(
            "produce a candidate",
            self._context(persona_text=persona_text),
            provider=provider,
        )
        self.assertEqual(provider.call_count, 1)
        return result

    def test_01_cloud_to_candidate_success(self) -> None:
        request = self._runtime_request()
        session = FakeAuthorizedSession({"candidate": request, "confidence": 0.8})
        provider = CloudCandidateProvider()
        with patch.object(
            provider,
            "_authorized_session",
            return_value=(session, "project-fixture"),
        ):
            result = provider.generate_candidate(
                "produce a candidate", self._context()
            )
        self.assertEqual(session.call_count, 1)
        self.assertTrue(result["candidate_only"])
        self.assertEqual(result["source_mode"], "LLM_PUSH")
        self.assertEqual(result["provider_ref"], "gcp")
        self.assertEqual(result["model_ref"], "cloud-llm")

    def test_02_cloud_xiaoj_gateway_success(self) -> None:
        result = self._push()
        self.assertEqual(result["final_decision"], "ALLOW")
        self.assertTrue(result["commit_applied"])

    def test_03_cloud_cannot_directly_commit(self) -> None:
        request = self._runtime_request()
        request["candidate_only"] = True
        request["committed"] = True
        with self.assertRaises(TotalFieldGatewayError) as caught:
            receive_candidate(
                request,
                previous_state=self.previous,
                observation_domains=self.observation_domains,
            )
        self.assertEqual(
            caught.exception.reason_code, "BLOCK_UNAUTHORIZED_CLOUD_COMMIT"
        )
        for reserved_key in ("adi_fixture", "adi_result", "TEST_ONLY"):
            forged = self._runtime_request()
            forged["context"]["nested"] = {reserved_key: True}
            with self.assertRaises(TotalFieldGatewayError) as forged_caught:
                self._push(forged)
            self.assertEqual(
                forged_caught.exception.reason_code,
                "GATEWAY_TRUSTED_CONTEXT_FIELD_FORBIDDEN",
                reserved_key,
            )

    def test_04_db_write_injection_is_blocked(self) -> None:
        request = self._runtime_request()
        request["resolved_fields"]["D5"]["db_write"] = True
        result = self._push(request)
        self.assertEqual(result["final_decision"], "BLOCK")
        self.assertFalse(result["commit_applied"])

    def test_05_restart_injection_is_blocked(self) -> None:
        request = self._runtime_request()
        request["resolved_fields"]["D5"]["restart"] = True
        result = self._push(request)
        self.assertEqual(result["final_decision"], "BLOCK")
        self.assertFalse(result["commit_applied"])

    def test_06_raw_token_injection_is_blocked(self) -> None:
        request = self._runtime_request()
        request["resolved_fields"]["D6"]["raw_token"] = "fixture-not-a-secret"
        result = self._push(request)
        self.assertEqual(result["final_decision"], "BLOCK")
        self.assertFalse(result["commit_applied"])
        inherited_previous = copy.deepcopy(self.previous)
        inherited_previous["D3"]["nested"] = {
            "member_plaintext": "PRIVATE-FIXTURE-MUST-NOT-BE-ECHOED"
        }
        inherited_request = self._runtime_request()
        inherited_request["candidate_only"] = True
        inherited = receive_candidate(
            inherited_request,
            previous_state=inherited_previous,
            observation_domains=self.observation_domains,
        )
        self.assertEqual(inherited["final_decision"], "BLOCK")
        self.assertNotIn(
            "PRIVATE-FIXTURE-MUST-NOT-BE-ECHOED",
            json.dumps(
                {
                    "decision_reason_codes": inherited["decision_reason_codes"],
                    "constraint_results": inherited["constraint_results"],
                },
                ensure_ascii=False,
            ),
        )

    def test_07_legal_candidate_can_allow_after_convergence(self) -> None:
        result = self._push()
        self.assertEqual(result["fixed_point_status"], "REACHED")
        self.assertEqual(result["final_decision"], "ALLOW")
        self.assertTrue(result["commit_applied"])
        ref_cases = (
            (("dimensions", "D1_ref"), "field/unknown/D1/v0_1"),
            (("constraint_hypergraph_ref",), "constraints/unknown/v0_1"),
            (("convergence_operator_ref",), "convergence/unknown/v0_1"),
        )
        for path, value in ref_cases:
            request = self._runtime_request()
            target = request["gte"]
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            held = self._push(request)
            self.assertEqual(held["final_decision"], "HOLD", path)
            self.assertFalse(held["commit_applied"])

    def test_08_hold_preserves_previous(self) -> None:
        for raw_key in (
            "raw_payload",
            "raw_data",
            "blob",
            "binary",
            "base64_payload",
            "plaintext",
            "content_bytes",
        ):
            request = self._runtime_request()
            request["resolved_fields"]["D7"]["reconstruction_condition"] = {
                "nested": {raw_key: {"status": "reference-required"}}
            }
            result = self._push(request)
            self.assertEqual(result["final_decision"], "HOLD", raw_key)
            self.assertFalse(result["commit_applied"])
            self.assertEqual(result["committed"], self.previous)
        severe = self._runtime_request()
        severe["resolved_fields"]["D7"]["reconstruction_condition"] = {
            "nested": {"raw_data": True}
        }
        severe["context"]["hard_risk_codes"] = ["DB_WRITE_REQUESTED"]
        severe_result = self._push(severe)
        self.assertEqual(severe_result["final_decision"], "QUARANTINE")

    def test_09_persona_is_not_in_tfs(self) -> None:
        persona = "PERSONA-FIXTURE-MUST-NOT-ENTER-TFS"
        result = self._push(persona_text=persona)
        self.assertNotIn(persona, json.dumps(result, ensure_ascii=False))

    def test_10_candidate_hash_is_stable(self) -> None:
        generated = self._provider_result()
        first = build_candidate_envelope(
            source_mode="LLM_PUSH",
            model_ref=generated["model_ref"],
            provider_ref=generated["provider_ref"],
            event_ref=generated["event_ref"],
            observation_domain_ref=generated["observation_domain_ref"],
            rule_ref=generated["rule_ref"],
            logical_time="logical-time:cloud-agent:fixture:001",
            persona_text="persona-alpha",
            governance_candidate=generated["candidate"],
        )
        second = build_candidate_envelope(
            source_mode="LLM_PUSH",
            model_ref=generated["model_ref"],
            provider_ref=generated["provider_ref"],
            event_ref=generated["event_ref"],
            observation_domain_ref=generated["observation_domain_ref"],
            rule_ref=generated["rule_ref"],
            logical_time="logical-time:cloud-agent:fixture:001",
            persona_text="persona-beta",
            governance_candidate=generated["candidate"],
        )
        self.assertEqual(first.candidate_hash, second.candidate_hash)


if __name__ == "__main__":
    unittest.main(verbosity=2)
