#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused non-live tests for governed dual-candidate natural-language I/O."""

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

from tools.domain_completion_total_field_gateway import (  # noqa: E402
    DomainCompletionTotalFieldGateway,
)
from tools.sovereign_ai_domain_completion_candidate import (  # noqa: E402
    build_candidate,
)
from tools.w7tp_packet_inference_cockpit_server import (  # noqa: E402
    run_dual_llm_governed_nlio,
)
from tools.xiaoj_candidate_adapter import (  # noqa: E402
    CandidateProviderFailure,
    DEGRADABLE_FAILURE_CLASSES,
    DEGRADATION_POLICY_VERSION,
    DualLLMGovernedNLIOCoordinator,
    NON_DEGRADABLE_FAILURE_CLASSES,
)


class FakeProvider:
    """Injected candidate provider with no credential or network access."""

    def __init__(
        self,
        candidates: tuple[dict[str, Any], ...],
        call_log: list[str],
        layer: str,
        *,
        failure_class: str | None = None,
    ) -> None:
        self._candidates = copy.deepcopy(candidates)
        self._call_log = call_log
        self._layer = layer
        self._failure_class = failure_class

    def candidates_for(
        self, request_ref: str, source_mode: str
    ) -> tuple[dict[str, Any], ...]:
        if not request_ref.startswith("nlio:sha256:"):
            raise AssertionError("raw request text reached provider")
        self._call_log.append(self._layer)
        if self._failure_class is not None:
            raise CandidateProviderFailure(self._failure_class)
        expected_mode = "XIAOJ_LOCAL" if self._layer == "LOCAL" else "LLM_PUSH"
        if source_mode != expected_mode:
            raise AssertionError("provider source mode mismatch")
        return copy.deepcopy(self._candidates)


class SpyGateway:
    def __init__(self, gateway: DomainCompletionTotalFieldGateway) -> None:
        self._gateway = gateway
        self.call_count = 0
        self.received: tuple[dict[str, Any], ...] = ()

    def receive_batch(
        self,
        candidates: tuple[dict[str, Any], ...],
        *,
        previous_values: dict[str, Any],
        forced_hold_reason: str | None = None,
    ) -> tuple[dict[str, Any], ...]:
        self.call_count += 1
        self.received = copy.deepcopy(candidates)
        return self._gateway.receive_batch(
            candidates,
            previous_values=previous_values,
            forced_hold_reason=forced_hold_reason,
        )


class DualLLMGovernedNLIOTests(unittest.TestCase):
    def setUp(self) -> None:
        self.observation_ref = "observation-domain:community:dual-nlio:v0.1"
        self.gateway = DomainCompletionTotalFieldGateway(
            observation_domains={
                self.observation_ref: {
                    "configured": True,
                    "observations": {
                        "observation_ref": "observation:community:dual-nlio:v0.1"
                    },
                }
            }
        )

    def _candidate(
        self,
        value: Any = "相容候選",
        *,
        attribute_name: str = "public_description",
        provider_ref: str = "provider:fake:local:v0.1",
        event_ref: str = "event:dual-nlio:local:001",
    ) -> dict[str, Any]:
        return build_candidate(
            domain="COMMUNITY",
            entity_ref="entity:community:dual-nlio:001",
            attribute_name=attribute_name,
            candidate_value=value,
            source_mode="TOTAL_FIELD_PULL",
            model_ref=f"model:{provider_ref}",
            provider_ref=provider_ref,
            event_ref=event_ref,
            observation_domain_ref=self.observation_ref,
            rule_ref="rules/tfct/identity_v0_1",
            evidence_refs=[],
            confidence=0.75,
            sensitivity="SAFE_DERIVED",
            requires_human_confirmation=False,
        )

    @staticmethod
    def _identity(candidate: dict[str, Any]) -> str:
        return "|".join(
            str(candidate[key])
            for key in ("domain", "entity_ref", "attribute_name")
        )

    def _run(
        self,
        local: dict[str, Any],
        cloud: dict[str, Any],
        *,
        persona_text: str = "這是自然語言候選回覆。",
    ) -> tuple[dict[str, Any], SpyGateway, list[str]]:
        call_log: list[str] = []
        spy = SpyGateway(self.gateway)
        coordinator = DualLLMGovernedNLIOCoordinator(
            local_provider=FakeProvider((local,), call_log, "LOCAL"),
            cloud_provider=FakeProvider((cloud,), call_log, "CLOUD"),
            domain_gateway=spy,
        )
        result = coordinator.process(
            "請用自然語言處理這個需求",
            previous_values={self._identity(local): "舊值"},
            persona_text=persona_text,
            channel="web",
        )
        return result, spy, call_log

    def test_local_and_cloud_are_sequentially_received_by_existing_gateway(self) -> None:
        local = self._candidate()
        cloud = self._candidate(
            provider_ref="provider:fake:cloud:v0.1",
            event_ref="event:dual-nlio:cloud:001",
        )
        with patch(
            "tools.domain_completion_total_field_gateway.total_field_receive_candidate",
            wraps=__import__(
                "tools.domain_completion_total_field_gateway",
                fromlist=["total_field_receive_candidate"],
            ).total_field_receive_candidate,
        ) as receiver:
            result, spy, call_log = self._run(local, cloud)
        self.assertEqual(call_log, ["LOCAL", "CLOUD"])
        self.assertEqual(receiver.call_count, 2)
        self.assertEqual(spy.call_count, 1)
        self.assertEqual(len(spy.received), 2)
        self.assertTrue(result["both_received"])

    def test_compatible_candidates_converge_under_total_field_allow(self) -> None:
        result, _spy, _calls = self._run(
            self._candidate(),
            self._candidate(
                provider_ref="provider:fake:cloud:v0.1",
                event_ref="event:dual-nlio:cloud:001",
            ),
        )
        self.assertEqual(result["total_field_final_decision"], "ALLOW")
        self.assertEqual(result["renderer_decision"], "PASS")
        self.assertFalse(result["degraded_mode"])
        self.assertTrue(result["dual_convergence"])
        self.assertTrue(result["reply_text"])
        self.assertTrue(all(item["commit_applied"] for item in result["candidate_results"]))

    def test_conflicting_candidates_use_domain_conflict_and_hold(self) -> None:
        result, _spy, _calls = self._run(
            self._candidate("候選甲"),
            self._candidate(
                "候選乙",
                provider_ref="provider:fake:cloud:v0.1",
                event_ref="event:dual-nlio:cloud:001",
            ),
        )
        self.assertEqual(result["total_field_final_decision"], "HOLD")
        self.assertEqual(result["renderer_decision"], "HOLD")
        self.assertFalse(result["degraded_mode"])
        self.assertFalse(result["dual_convergence"])
        self.assertEqual(result["failure_class"], "DOMAIN_CANDIDATE_CONFLICT")
        self.assertTrue(result["reply_text"])
        self.assertTrue(
            all(
                "HOLD_CANDIDATE_CONFLICT_DETECTED"
                in item["decision_reason_codes"]
                for item in result["candidate_results"]
            )
        )

    def test_candidate_authority_claim_never_reaches_total_field(self) -> None:
        local = self._candidate()
        local["final_decision"] = "ALLOW"
        cloud = self._candidate(provider_ref="provider:fake:cloud:v0.1")
        result, spy, _calls = self._run(local, cloud)
        self.assertEqual(result["STATE"], "HOLD_NON_DEGRADABLE_PROVIDER_FAILURE")
        self.assertEqual(result["failure_class"], "FORBIDDEN_AUTHORITY")
        self.assertEqual(spy.call_count, 0)
        self.assertFalse(result["degraded_mode"])
        self.assertFalse(result["candidate_sources_are_authority"])

    def test_persona_is_excluded_from_governance_hashes_and_results(self) -> None:
        local = self._candidate()
        cloud = self._candidate(
            provider_ref="provider:fake:cloud:v0.1",
            event_ref="event:dual-nlio:cloud:001",
        )
        first, _spy, _calls = self._run(local, cloud, persona_text="語氣甲")
        second, _spy, _calls = self._run(local, cloud, persona_text="語氣乙")
        self.assertEqual(
            first["local_candidate_hashes"], second["local_candidate_hashes"]
        )
        self.assertEqual(
            first["cloud_candidate_hashes"], second["cloud_candidate_hashes"]
        )
        self.assertEqual(first["candidate_results"], second["candidate_results"])
        governance_json = json.dumps(first["candidate_results"], ensure_ascii=False)
        self.assertNotIn("語氣甲", governance_json)

    def test_pass_hold_and_block_all_render_natural_language(self) -> None:
        passing, _spy, _calls = self._run(
            self._candidate(), self._candidate(provider_ref="provider:fake:cloud:v0.1")
        )
        holding, _spy, _calls = self._run(
            self._candidate("甲"),
            self._candidate("乙", provider_ref="provider:fake:cloud:v0.1"),
        )
        blocking, _spy, _calls = self._run(
            self._candidate(attribute_name="raw_token"),
            self._candidate(
                attribute_name="raw_token",
                provider_ref="provider:fake:cloud:v0.1",
            ),
        )
        self.assertEqual(
            [
                passing["renderer_decision"],
                holding["renderer_decision"],
                blocking["renderer_decision"],
            ],
            ["PASS", "HOLD", "BLOCK"],
        )
        self.assertTrue(
            all(item["reply_text"] for item in (passing, holding, blocking))
        )

    def test_local_timeout_cloud_success_chat_only_degrades_through_gate(self) -> None:
        candidate = self._candidate()
        call_log: list[str] = []
        spy = SpyGateway(self.gateway)
        coordinator = DualLLMGovernedNLIOCoordinator(
            local_provider=FakeProvider(
                (), call_log, "LOCAL", failure_class="PROVIDER_TIMEOUT"
            ),
            cloud_provider=FakeProvider((candidate,), call_log, "CLOUD"),
            domain_gateway=spy,
        )
        result = coordinator.process(
            "自然語言請求",
            previous_values={self._identity(candidate): "舊值"},
            persona_text="備援聊天候選",
        )
        self.assertEqual(result["STATE"], "PASS")
        self.assertTrue(result["degraded_mode"])
        self.assertFalse(result["dual_convergence"])
        self.assertEqual(result["available_provider"], "CLOUD")
        self.assertEqual(result["missing_provider"], "LOCAL")
        self.assertEqual(result["failure_class"], "PROVIDER_TIMEOUT")
        self.assertEqual(call_log, ["LOCAL", "CLOUD"])
        self.assertEqual(spy.call_count, 1)
        self.assertIn("備援模式", result["reply_text"])
        serialized = json.dumps(result["candidate_results"], ensure_ascii=False)
        self.assertNotIn("tfid", serialized)
        self.assertNotIn("total_field_hash", serialized)

    def test_cloud_unavailable_local_success_chat_only_degrades(self) -> None:
        candidate = self._candidate()
        call_log: list[str] = []
        spy = SpyGateway(self.gateway)
        result = DualLLMGovernedNLIOCoordinator(
            local_provider=FakeProvider((candidate,), call_log, "LOCAL"),
            cloud_provider=FakeProvider(
                (), call_log, "CLOUD", failure_class="PROVIDER_UNAVAILABLE"
            ),
            domain_gateway=spy,
        ).process(
            "自然語言請求",
            previous_values={self._identity(candidate): "舊值"},
            persona_text="本地備援候選",
        )
        self.assertEqual(result["total_field_final_decision"], "ALLOW")
        self.assertEqual(result["available_provider"], "LOCAL")
        self.assertEqual(result["missing_provider"], "CLOUD")
        self.assertEqual(result["failure_class"], "PROVIDER_UNAVAILABLE")
        self.assertTrue(result["degraded_mode"])
        self.assertEqual(spy.call_count, 1)

    def test_single_provider_code_draft_is_candidate_only(self) -> None:
        candidate = self._candidate("diff --git a/demo.py b/demo.py\n+print('draft')")
        call_log: list[str] = []
        spy = SpyGateway(self.gateway)
        result = DualLLMGovernedNLIOCoordinator(
            local_provider=FakeProvider((candidate,), call_log, "LOCAL"),
            cloud_provider=FakeProvider(
                (), call_log, "CLOUD", failure_class="TRANSPORT_UNREACHABLE"
            ),
            domain_gateway=spy,
        ).process(
            "請給程式碼草稿",
            previous_values={self._identity(candidate): "舊值"},
            request_mode="CODE_DRAFT_ONLY",
        )
        draft = result["code_draft_candidate"]
        self.assertEqual(draft["status"], "CANDIDATE_ONLY")
        self.assertIn("diff --git", draft["text"])
        self.assertFalse(draft["file_write"])
        self.assertFalse(draft["execution"])
        self.assertFalse(draft["commit"])
        self.assertFalse(draft["deploy"])
        self.assertTrue(result["degraded_mode"])
        self.assertEqual(spy.call_count, 1)

    def test_single_provider_action_request_holds_through_total_field(self) -> None:
        candidate = self._candidate()
        call_log: list[str] = []
        spy = SpyGateway(self.gateway)
        result = DualLLMGovernedNLIOCoordinator(
            local_provider=FakeProvider((candidate,), call_log, "LOCAL"),
            cloud_provider=FakeProvider(
                (), call_log, "CLOUD", failure_class="PROVIDER_UNAVAILABLE"
            ),
            domain_gateway=spy,
        ).process(
            "請執行動作",
            previous_values={self._identity(candidate): "舊值"},
            request_mode="ACTION_REQUEST",
        )
        self.assertEqual(result["STATE"], "HOLD_SINGLE_PROVIDER_ACTION_NOT_AUTHORIZED")
        self.assertEqual(result["total_field_final_decision"], "HOLD")
        self.assertEqual(result["renderer_decision"], "HOLD")
        self.assertIn("單一路徑可用", result["reply_text"])
        self.assertIn("執行部分已暫停", result["reply_text"])
        self.assertEqual(spy.call_count, 1)
        self.assertFalse(result["side_effects_performed"])

    def test_chat_only_with_requested_effect_is_treated_as_action_hold(self) -> None:
        candidate = self._candidate()
        call_log: list[str] = []
        spy = SpyGateway(self.gateway)
        result = DualLLMGovernedNLIOCoordinator(
            local_provider=FakeProvider((candidate,), call_log, "LOCAL"),
            cloud_provider=FakeProvider(
                (), call_log, "CLOUD", failure_class="PROVIDER_UNAVAILABLE"
            ),
            domain_gateway=spy,
        ).process(
            "請寫入檔案",
            previous_values={self._identity(candidate): "舊值"},
            request_mode="CHAT_ONLY",
            requested_effects={"file_write": True},
        )
        self.assertEqual(result["STATE"], "HOLD_SINGLE_PROVIDER_ACTION_NOT_AUTHORIZED")
        self.assertEqual(result["total_field_final_decision"], "HOLD")
        self.assertEqual(spy.call_count, 1)

    def test_single_provider_secret_boundary_is_not_degradable(self) -> None:
        candidate = self._candidate(attribute_name="raw_token")
        call_log: list[str] = []
        spy = SpyGateway(self.gateway)
        result = DualLLMGovernedNLIOCoordinator(
            local_provider=FakeProvider((candidate,), call_log, "LOCAL"),
            cloud_provider=FakeProvider(
                (), call_log, "CLOUD", failure_class="PROVIDER_UNAVAILABLE"
            ),
            domain_gateway=spy,
        ).process(
            "自然語言請求",
            previous_values={self._identity(candidate): "舊值"},
        )
        self.assertEqual(result["failure_class"], "SECRET_OR_MEMBER_PLAINTEXT_BOUNDARY")
        self.assertFalse(result["degraded_mode"])
        self.assertEqual(spy.call_count, 0)

    def test_invalid_schema_is_non_degradable(self) -> None:
        invalid = self._candidate()
        invalid.pop("domain")
        valid = self._candidate(provider_ref="provider:fake:cloud:v0.1")
        call_log: list[str] = []
        spy = SpyGateway(self.gateway)
        result = DualLLMGovernedNLIOCoordinator(
            local_provider=FakeProvider((invalid,), call_log, "LOCAL"),
            cloud_provider=FakeProvider((valid,), call_log, "CLOUD"),
            domain_gateway=spy,
        ).process(
            "自然語言請求",
            previous_values={self._identity(valid): "舊值"},
        )
        self.assertEqual(result["failure_class"], "INVALID_SCHEMA")
        self.assertFalse(result["degraded_mode"])
        self.assertEqual(spy.call_count, 0)

    def test_two_provider_failures_hold_without_gateway(self) -> None:
        candidate = self._candidate()
        call_log: list[str] = []
        spy = SpyGateway(self.gateway)
        result = DualLLMGovernedNLIOCoordinator(
            local_provider=FakeProvider(
                (), call_log, "LOCAL", failure_class="PROVIDER_TIMEOUT"
            ),
            cloud_provider=FakeProvider(
                (), call_log, "CLOUD", failure_class="PROVIDER_UNAVAILABLE"
            ),
            domain_gateway=spy,
        ).process(
            "自然語言請求",
            previous_values={self._identity(candidate): "舊值"},
        )
        self.assertEqual(result["STATE"], "HOLD_BOTH_PROVIDERS_UNAVAILABLE")
        self.assertEqual(result["renderer_decision"], "HOLD")
        self.assertTrue(result["reply_text"])
        self.assertEqual(spy.call_count, 0)

    def test_policy_file_matches_closed_failure_classes(self) -> None:
        path = (
            ROOT
            / "manifests/w7tp_xiaoj_single_provider_degradation_policy_v1/"
            "policy.json"
        )
        policy = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(policy["schema_version"], DEGRADATION_POLICY_VERSION)
        self.assertEqual(
            set(policy["degradable_failure_classes"]),
            set(DEGRADABLE_FAILURE_CLASSES),
        )
        self.assertEqual(
            set(policy["non_degradable_failure_classes"]),
            set(NON_DEGRADABLE_FAILURE_CLASSES),
        )

    def test_cockpit_exposes_injected_coordinator_without_new_route(self) -> None:
        local = self._candidate()
        cloud = self._candidate(provider_ref="provider:fake:cloud:v0.1")
        call_log: list[str] = []
        result = run_dual_llm_governed_nlio(
            "自然語言輸入",
            local_provider=FakeProvider((local,), call_log, "LOCAL"),
            cloud_provider=FakeProvider((cloud,), call_log, "CLOUD"),
            domain_gateway=self.gateway,
            previous_values={self._identity(local): "舊值"},
            persona_text="自然語言回覆",
        )
        self.assertEqual(result["renderer_decision"], "PASS")
        self.assertEqual(call_log, ["LOCAL", "CLOUD"])
        self.assertTrue(result["reply_text"])


if __name__ == "__main__":
    unittest.main()
