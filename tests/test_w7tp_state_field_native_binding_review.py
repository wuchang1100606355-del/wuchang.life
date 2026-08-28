"""Direct regressions for the targeted adapter review only."""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from tests.test_w7tp_state_field_native_binding_candidate import (
    _FixtureBoundedRunner,
    _FixtureEvidence,
)
from w7tp_runtime.state_field.canonical import sha256_ref
from w7tp_runtime.state_field.models import EffectGateRequest, FlowRequest, Hold, Quarantine
from w7tp_runtime.state_field.native_cli_adapters import (
    ARTIFACT_PINS,
    build_static_candidate_ports,
)
from w7tp_runtime.state_field.native_ports import (
    CAP_EFFECT_GATE,
    CAP_INFORMATION_FLOW,
)
from w7tp_runtime.state_field.object_packet_store import ObjectPacketStore


def _ref(label: str) -> str:
    return sha256_ref(label.encode("utf-8"))


class _MismatchedFlowRunner(_FixtureBoundedRunner):
    def invoke(self, invocation):
        result = super().invoke(invocation)
        if invocation.capability_id == CAP_INFORMATION_FLOW:
            return replace(
                result,
                stdout_lines=(
                    "DECISION=ALLOW",
                    "NEXT_LABELS=PUBLIC",
                    "D8_AUTHORITY_CREATED=false",
                ),
            )
        return result


class _ExpiredEffectEvidence(_FixtureEvidence):
    def effect_decision(self, request):
        return replace(
            super().effect_decision(request),
            valid_until=datetime(2020, 1, 1, tzinfo=UTC),
        )


class TargetedNativeBindingReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.objects = ObjectPacketStore(Path(self.temporary.name) / "objects")
        self.binding_refs = {
            capability_id: _ref("review-binding:" + capability_id)
            for capability_id in ARTIFACT_PINS
        }
        self.manifest_refs = {
            capability_id: _ref("review-manifest:" + capability_id)
            for capability_id in ARTIFACT_PINS
        }

    def _registry(self, runner, evidence):
        return build_static_candidate_ports(
            runner=runner,
            objects=self.objects,
            evidence=evidence,
            binding_refs=self.binding_refs,
            manifest_refs=self.manifest_refs,
        )

    def test_next_labels_must_exactly_match_verified_policy(self) -> None:
        runner = _MismatchedFlowRunner(self.objects)
        evidence = _FixtureEvidence(self.objects)
        registry = self._registry(runner, evidence)
        request = FlowRequest(
            resource_ref=_ref("resource"),
            ingress_proof_ref=_ref("ingress"),
            delegation_proof_ref=_ref("delegation"),
            effect_contract_ref=_ref("contract"),
            target_coordinate_ref=_ref("target"),
        )
        adapter = registry[self.binding_refs[CAP_INFORMATION_FLOW]]
        with self.assertRaisesRegex(
            Quarantine, "NATIVE_FLOW_OUTPUT_POLICY_CONFLICT"
        ):
            adapter.verify_flow(request)

    def test_expired_exact_d8_evidence_is_a_hold(self) -> None:
        runner = _FixtureBoundedRunner(self.objects)
        evidence = _ExpiredEffectEvidence(self.objects)
        registry = self._registry(runner, evidence)
        contract_hash = "a" * 64
        request = EffectGateRequest(
            effect_contract_ref=f"sha256:{contract_hash}",
            effect_contract_hash=contract_hash,
            policy_ref=_ref("policy"),
            d8_authorization_ref=_ref("test-d8-authorization-not-real"),
            d8_packet_ref=_ref("test-d8-packet-not-real"),
            authority_ref=_ref("test-authority-not-real"),
            base_version_ref=None,
            base_generation=0,
            target_coordinate_ref=_ref("target"),
            acceptance_contract_ref=_ref("acceptance"),
            flow_proof_ref=_ref("flow"),
        )
        adapter = registry[self.binding_refs[CAP_EFFECT_GATE]]
        with self.assertRaisesRegex(
            Hold, "HOLD_EXACT_D8_AUTHORIZATION_EXPIRED"
        ):
            adapter.verify_exact_authorization(request)


if __name__ == "__main__":
    unittest.main()
