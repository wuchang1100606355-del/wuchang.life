"""Bounded protocol-conformance tests; these fixtures are not real E2E."""

from __future__ import annotations

import ast
import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from w7tp_runtime.state_field.canonical import (
    canonical_hash,
    canonical_json_bytes,
    canonical_json_loads,
    sha256_ref,
)
from w7tp_runtime.state_field.models import (
    DelegationRequest,
    EffectGateRequest,
    EvidenceLifecycleRequest,
    FlowRequest,
    Hold,
    IngressRepresentationRequest,
    NativeProof,
    Quarantine,
    VerifiedEffectPermit,
    request_hash,
)
from w7tp_runtime.state_field.native_cli_adapters import (
    ARTIFACT_PINS,
    AdapterHold,
    BoundedCliInvocation,
    BoundedCliResult,
    ExactDelegationEvidence,
    ExactEffectDecisionEvidence,
    ExactFlowPolicyEvidence,
    ExactLifecycleEvidence,
    build_static_candidate_ports,
)
from w7tp_runtime.state_field.native_ports import (
    CAP_DELEGATION,
    CAP_EFFECT_GATE,
    CAP_EVIDENCE_LIFECYCLE,
    CAP_EXTERNAL_GATEWAY,
    CAP_INFORMATION_FLOW,
    decode_local_file_coordinate,
)
from w7tp_runtime.state_field.object_packet_store import ObjectPacketStore
from w7tp_runtime.state_field.real_e2e_binding_candidate import (
    ADAPTER_SOURCE_PATH,
    EXPIRED_PROMOTION_D8_SHA256,
    build_real_e2e_binding_bundle_candidate,
)


CAPABILITIES = tuple(sorted(ARTIFACT_PINS))


def _ref(label: str) -> str:
    return sha256_ref(label.encode("utf-8"))


class _FixtureEvidence:
    """Synthetic unit evidence; never exported or represented as real authority."""

    def __init__(self, objects: ObjectPacketStore) -> None:
        self.objects = objects
        self.verification_state = "VERIFIED"
        self.policy_allowed = True
        self.exact_d8_authorized = True
        self.delegation_authenticity = True
        self.coordinate_conflict = False

    def _evidence(self, capability_id: str, subject_hash: str) -> str:
        return self.objects.put_bytes(
            canonical_json_bytes(
                {
                    "schema_id": "TEST_FIXTURE_ONLY_NOT_REAL_AUTHORITY",
                    "capability_id": capability_id,
                    "subject_hash": subject_hash,
                }
            )
        )

    def effect_decision(
        self, request: EffectGateRequest
    ) -> ExactEffectDecisionEvidence:
        subject_hash = request_hash(request)
        if self.coordinate_conflict:
            subject_hash = "0" * 64
        return ExactEffectDecisionEvidence(
            request_hash=subject_hash,
            effect_class="MUTATION",
            exact_effect_ref=request.effect_contract_ref,
            target_coordinate_ref=request.target_coordinate_ref,
            policy_ref=request.policy_ref,
            d8_authorization_ref=request.d8_authorization_ref,
            d8_packet_ref=request.d8_packet_ref,
            authority_ref=request.authority_ref,
            authorization_ref=request.d8_authorization_ref,
            policy_allowed=self.policy_allowed,
            exact_d8_authorized=self.exact_d8_authorized,
            valid_until=datetime(2035, 1, 1, tzinfo=UTC),
            evidence_ref=self._evidence(CAP_EFFECT_GATE, subject_hash),
            verification_state=self.verification_state,
        )

    def delegation(self, request: DelegationRequest) -> ExactDelegationEvidence:
        subject_hash = request_hash(request)
        if self.coordinate_conflict:
            subject_hash = "0" * 64
        return ExactDelegationEvidence(
            request_hash=subject_hash,
            delegation_chain_ref=request.delegation_chain_ref,
            authenticity_proven=self.delegation_authenticity,
            evidence_ref=self._evidence(CAP_DELEGATION, subject_hash),
            verification_state=self.verification_state,
        )

    def flow(self, request: FlowRequest) -> ExactFlowPolicyEvidence:
        subject_hash = request_hash(request)
        if self.coordinate_conflict:
            subject_hash = "0" * 64
        return ExactFlowPolicyEvidence(
            request_hash=subject_hash,
            policy_ref=_ref("flow-policy"),
            label_rank={"PUBLIC": 0, "CANDIDATE": 1},
            current_labels=("PUBLIC",),
            incoming_labels=("CANDIDATE",),
            destination_max_label="CANDIDATE",
            declassification_authorized=False,
            declassified_output_labels=(),
            redaction_available=False,
            redaction_output_labels=(),
            evidence_ref=self._evidence(CAP_INFORMATION_FLOW, subject_hash),
            verification_state=self.verification_state,
        )

    def lifecycle(
        self, request: EvidenceLifecycleRequest
    ) -> ExactLifecycleEvidence:
        subject_hash = request_hash(request)
        if self.coordinate_conflict:
            subject_hash = "0" * 64
        return ExactLifecycleEvidence(
            request_hash=subject_hash,
            target_coordinate_ref=_ref("target-coordinate"),
            started_at="2026-08-23T06:05:04Z",
            ended_at="2026-08-23T06:05:05Z",
            authority_ref=_ref("test-fixture-authority-not-real"),
            previous_receipt_hash="0" * 64,
            artifact_hashes=("1" * 64,),
            evidence_ref=self._evidence(CAP_EVIDENCE_LIFECYCLE, subject_hash),
            verification_state=self.verification_state,
        )


class _FixtureBoundedRunner:
    """Recorded CLI contract behavior; never launches a process or effect."""

    def __init__(self, objects: ObjectPacketStore, mode: str = "ok") -> None:
        self.objects = objects
        self.mode = mode
        self.invocations: list[BoundedCliInvocation] = []

    def _evidence(self, invocation: BoundedCliInvocation) -> str:
        return self.objects.put_bytes(
            canonical_json_bytes(
                {
                    "schema_id": "TEST_BOUNDED_RUNNER_EVIDENCE_V1",
                    "artifact_sha256": invocation.expected_artifact_sha256,
                    "capability_id": invocation.capability_id,
                    "input_ref": invocation.input_ref,
                    "mode": self.mode,
                }
            )
        )

    def invoke(self, invocation: BoundedCliInvocation) -> BoundedCliResult:
        self.invocations.append(invocation)
        evidence_ref = self._evidence(invocation)
        observed_hash = invocation.expected_artifact_sha256
        if self.mode == "wrong_hash":
            observed_hash = "0" * 64
        if self.mode in {"timeout", "failure"}:
            return BoundedCliResult(
                state="TIMEOUT" if self.mode == "timeout" else "FAILED",
                exit_code=None,
                stdout_lines=(),
                output_bytes=None,
                observed_artifact_sha256=observed_hash,
                evidence_ref=evidence_ref,
                runner_ref="test.fixture.bounded-runner.not-real-e2e",
            )
        if self.mode == "malformed_output":
            return BoundedCliResult(
                state="COMPLETED",
                exit_code=0,
                stdout_lines=("MALFORMED",),
                output_bytes=b"{" if invocation.output_file_required else None,
                observed_artifact_sha256=observed_hash,
                evidence_ref=evidence_ref,
                runner_ref="test.fixture.bounded-runner.not-real-e2e",
            )

        payload = canonical_json_loads(invocation.input_bytes)
        output: bytes | None = None
        if invocation.capability_id == CAP_EXTERNAL_GATEWAY:
            candidate = dict(payload)
            candidate.update(
                {
                    "source_runtime_required": False,
                    "source_authority_inherited": False,
                    "w7tp_d8_authority_created": False,
                    "contract_state": "W7TP_NATIVE_GATEWAY_CANDIDATE",
                }
            )
            if self.mode == "authority_forgery":
                candidate["source_authority_inherited"] = True
            digest = canonical_hash(candidate)
            candidate["contract_sha256"] = digest
            output = (json.dumps(candidate, indent=2, ensure_ascii=False) + "\n").encode()
            lines = (
                "STATE=PASS_GATEWAY_CONTRACT_BUILT",
                "OUTPUT=bounded-output.json",
                f"CONTRACT_SHA256={digest}",
            )
        elif invocation.capability_id == CAP_EFFECT_GATE:
            lines = (
                "DECISION=ALLOW_EXECUTE",
                "D8_REQUIRED=true",
                "AUTHORIZATION_REF="
                + str(payload["d8_authorization"]["authorization_ref"]),
            )
        elif invocation.capability_id == CAP_DELEGATION:
            authenticity = "true" if self.mode == "authority_forgery" else "false"
            lines = (
                "STATE=PASS_BOUNDED_DELEGATION_CHAIN",
                f"GRANT_COUNT={len(payload['grants'])}",
                f"AUTHENTICITY_PROVEN={authenticity}",
            )
        elif invocation.capability_id == CAP_INFORMATION_FLOW:
            authority = "true" if self.mode == "authority_forgery" else "false"
            labels = sorted(
                set(payload["current_labels"]) | set(payload["incoming_labels"])
            )
            lines = (
                "DECISION=ALLOW",
                "NEXT_LABELS=" + ",".join(labels),
                f"D8_AUTHORITY_CREATED={authority}",
            )
        elif invocation.capability_id == CAP_EVIDENCE_LIFECYCLE:
            receipt = dict(payload)
            receipt.update(
                {
                    "receipt_state": "W7TP_EXECUTION_EVIDENCE",
                    "authority_created": self.mode == "authority_forgery",
                }
            )
            digest = canonical_hash(receipt)
            receipt["receipt_sha256"] = digest
            output = (json.dumps(receipt, indent=2, ensure_ascii=False) + "\n").encode()
            lines = (
                "STATE=PASS_EXECUTION_RECEIPT_BUILT",
                f"RECEIPT_SHA256={digest}",
                "OUTPUT=bounded-output.json",
            )
        else:
            raise AssertionError("unexpected fixture capability")
        return BoundedCliResult(
            state="COMPLETED",
            exit_code=0,
            stdout_lines=lines,
            output_bytes=output,
            observed_artifact_sha256=observed_hash,
            evidence_ref=evidence_ref,
            runner_ref="test.fixture.bounded-runner.not-real-e2e",
            external_effect_observed=self.mode == "external_effect",
        )


class NativeBindingCandidateConformanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.objects = ObjectPacketStore(Path(self.temporary.name) / "objects")
        self.binding_refs = {
            capability_id: _ref("binding:" + capability_id)
            for capability_id in CAPABILITIES
        }
        self.manifest_refs = {
            capability_id: _ref("manifest:" + capability_id)
            for capability_id in CAPABILITIES
        }
        chain = {
            "grants": [
                {
                    "grant_id": "root",
                    "parent_grant_id": None,
                    "founder_grant_ref": _ref("test-founder-grant-not-real"),
                    "delegation_allowed": True,
                    "capabilities": list(CAPABILITIES),
                    "targets": ["candidate-target"],
                    "purposes": ["protocol-conformance-fixture"],
                    "effect_classes": ["MUTATION"],
                    "valid_from": "2026-08-23T00:00:00Z",
                    "expires_at": "2035-01-01T00:00:00Z",
                }
            ]
        }
        self.chain_ref = self.objects.put_bytes(canonical_json_bytes(chain))
        contract_hash = "a" * 64
        self.requests = {
            CAP_EXTERNAL_GATEWAY: IngressRepresentationRequest(
                resource_ref=_ref("resource"),
                manifest_ref=_ref("resource-manifest"),
                effect_contract_ref=f"sha256:{contract_hash}",
                capability_binding_refs=tuple(self.binding_refs.values()),
            ),
            CAP_EFFECT_GATE: EffectGateRequest(
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
                flow_proof_ref=_ref("flow-proof"),
            ),
            CAP_DELEGATION: DelegationRequest(
                ingress_proof_ref=_ref("ingress-proof"),
                effect_contract_ref=f"sha256:{contract_hash}",
                delegation_chain_ref=self.chain_ref,
            ),
            CAP_INFORMATION_FLOW: FlowRequest(
                resource_ref=_ref("resource"),
                ingress_proof_ref=_ref("ingress-proof"),
                delegation_proof_ref=_ref("delegation-proof"),
                effect_contract_ref=f"sha256:{contract_hash}",
                target_coordinate_ref=_ref("target"),
            ),
            CAP_EVIDENCE_LIFECYCLE: EvidenceLifecycleRequest(
                operation_id="fixture-operation-not-real-e2e",
                effect_contract_ref=f"sha256:{contract_hash}",
                ingress_proof_ref=_ref("ingress-proof"),
                delegation_proof_ref=_ref("delegation-proof"),
                flow_proof_ref=_ref("flow-proof"),
                gate_proof_ref=_ref("gate-proof"),
                observation_ref=_ref("observation"),
                acceptance_evidence_ref=_ref("acceptance-evidence"),
            ),
        }

    def _build(self, mode: str = "ok"):
        runner = _FixtureBoundedRunner(self.objects, mode)
        evidence = _FixtureEvidence(self.objects)
        registry = build_static_candidate_ports(
            runner=runner,
            objects=self.objects,
            evidence=evidence,
            binding_refs=self.binding_refs,
            manifest_refs=self.manifest_refs,
        )
        adapters = {
            capability_id: registry[self.binding_refs[capability_id]]
            for capability_id in CAPABILITIES
        }
        return runner, evidence, registry, adapters

    def _call(self, capability_id: str, adapter: object, request: object | None = None):
        value = self.requests[capability_id] if request is None else request
        method_name = {
            CAP_EXTERNAL_GATEWAY: "verify_ingress",
            CAP_EFFECT_GATE: "verify_exact_authorization",
            CAP_DELEGATION: "verify_delegation",
            CAP_INFORMATION_FLOW: "verify_flow",
            CAP_EVIDENCE_LIFECYCLE: "verify_and_advance",
        }[capability_id]
        return getattr(adapter, method_name)(value)

    def test_01_each_port_requires_exact_implementation_hash(self) -> None:
        runner, _, _, adapters = self._build()
        for capability_id in CAPABILITIES:
            self._call(capability_id, adapters[capability_id])
        self.assertEqual(len(runner.invocations), 5)
        for invocation in runner.invocations:
            self.assertEqual(
                invocation.expected_artifact_sha256,
                ARTIFACT_PINS[invocation.capability_id].implementation_sha256,
            )

    def test_02_each_port_rejects_wrong_artifact_hash(self) -> None:
        _, _, _, adapters = self._build("wrong_hash")
        for capability_id in CAPABILITIES:
            with self.subTest(capability_id=capability_id):
                with self.assertRaises(Quarantine):
                    self._call(capability_id, adapters[capability_id])

    def test_03_each_port_accepts_its_correct_typed_request(self) -> None:
        _, _, _, adapters = self._build()
        for capability_id in CAPABILITIES:
            with self.subTest(capability_id=capability_id):
                result = self._call(capability_id, adapters[capability_id])
                if capability_id == CAP_EFFECT_GATE:
                    self.assertIsInstance(result, VerifiedEffectPermit)
                else:
                    self.assertIsInstance(result, NativeProof)

    def test_04_each_port_rejects_malformed_request_type(self) -> None:
        _, _, _, adapters = self._build()
        for capability_id in CAPABILITIES:
            with self.subTest(capability_id=capability_id):
                with self.assertRaises(Hold):
                    self._call(capability_id, adapters[capability_id], object())

    def test_05_each_port_rejects_malformed_capability_output(self) -> None:
        _, _, _, adapters = self._build("malformed_output")
        for capability_id in CAPABILITIES:
            with self.subTest(capability_id=capability_id):
                with self.assertRaises(AdapterHold):
                    self._call(capability_id, adapters[capability_id])

    def test_06_effect_gate_cannot_manufacture_d8(self) -> None:
        _, evidence, _, adapters = self._build()
        evidence.exact_d8_authorized = False
        with self.assertRaisesRegex(Hold, "HOLD_EXACT_D8_AUTHORIZATION_MISSING"):
            self._call(CAP_EFFECT_GATE, adapters[CAP_EFFECT_GATE])

    def test_07_each_cli_cannot_manufacture_authority(self) -> None:
        _, evidence, _, adapters = self._build("authority_forgery")
        evidence.exact_d8_authorized = False
        evidence.delegation_authenticity = False
        for capability_id in CAPABILITIES:
            with self.subTest(capability_id=capability_id):
                with self.assertRaises((Hold, Quarantine)):
                    self._call(capability_id, adapters[capability_id])

    def test_08_registry_is_static_and_source_has_no_dynamic_execution(self) -> None:
        _, _, registry, _ = self._build()
        with self.assertRaises(TypeError):
            registry[_ref("extra")] = object()  # type: ignore[index]
        source_path = Path(__file__).resolve().parents[1] / ADAPTER_SOURCE_PATH
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertTrue({"subprocess", "importlib", "shlex"}.isdisjoint(imported))
        forbidden_calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertTrue({"eval", "exec", "__import__"}.isdisjoint(forbidden_calls))

    def test_09_each_port_timeout_and_failure_are_evidenced_holds(self) -> None:
        for mode in ("timeout", "failure"):
            _, _, _, adapters = self._build(mode)
            for capability_id in CAPABILITIES:
                with self.subTest(mode=mode, capability_id=capability_id):
                    with self.assertRaises(AdapterHold) as raised:
                        self._call(capability_id, adapters[capability_id])
                    self.assertEqual(
                        self.objects.get_exact(raised.exception.evidence_ref)
                        is not None,
                        True,
                    )

    def test_10_each_port_maps_deterministically(self) -> None:
        _, _, _, adapters = self._build()
        for capability_id in CAPABILITIES:
            with self.subTest(capability_id=capability_id):
                first = self._call(capability_id, adapters[capability_id])
                second = self._call(capability_id, adapters[capability_id])
                self.assertEqual(first, second)

    def test_external_effect_signal_is_quarantined_for_every_port(self) -> None:
        _, _, _, adapters = self._build("external_effect")
        for capability_id in CAPABILITIES:
            with self.subTest(capability_id=capability_id):
                with self.assertRaises(Quarantine):
                    self._call(capability_id, adapters[capability_id])

    def test_candidate_bundle_is_complete_deterministic_and_not_authority(self) -> None:
        first = build_real_e2e_binding_bundle_candidate()
        second = build_real_e2e_binding_bundle_candidate()
        self.assertEqual(first.document, second.document)
        self.assertEqual(len(first.manifests), 5)
        self.assertEqual(len(first.binding_records), 5)
        self.assertEqual(first.document.body["STATE"], "REAL_E2E_BINDING_BUNDLE_CANDIDATE_READY")
        self.assertEqual(first.binding_packet.body["VERIFIED_BINDING_CANDIDATE_COUNT"], 5)
        self.assertEqual(first.authorization_request.body["D8_STATE"], "NOT_GRANTED")
        self.assertEqual(first.authorization_request.body["AUTHORITY_STATE"], "NOT_GRANTED")
        self.assertTrue(first.authorization_request.body["REQUEST_IS_NOT_AUTHORITY"])
        self.assertEqual(
            first.authorization_request.body["REJECTED_D8"]["SHA256"],
            EXPIRED_PROMOTION_D8_SHA256,
        )
        required_contract_fields = {
            "CONTRACT_ID",
            "TARGET",
            "BASE_STATE_REF",
            "EXPECTED_EFFECT",
            "MAXIMUM_EFFECT",
            "INPUT_REFS",
            "OUTPUT_CONTRACT",
            "RECEIVER",
            "IDEMPOTENCY",
            "OBSERVATION_RULE",
            "ACCEPTANCE_RULE",
            "ROLLBACK_OR_COMPENSATION",
            "TIMEOUT",
            "TTL",
            "NONCE",
            "GENERATION",
            "POINTER_VERSION",
            "RISK",
            "STOP_CONDITIONS",
            "EVIDENCE_DESTINATION",
        }
        self.assertTrue(required_contract_fields.issubset(first.effect_contract.body))
        coordinate = decode_local_file_coordinate(first.effect_contract.body["TARGET"])
        self.assertEqual(
            coordinate.logical_path,
            "runtime/total_field/state_field/real_e2e_candidate/"
            "W7TP_STATE_FIELD_REAL_E2E_OUTPUT.bin",
        )
        sealed_refs = first.seal_all(self.objects)
        self.assertEqual(len(sealed_refs), 21)
        for packet in (
            *first.manifests,
            *first.binding_records,
            first.binding_packet,
            first.effect_contract,
            first.authorization_request,
            first.document,
        ):
            self.assertEqual(packet.ref, sha256_ref(packet.raw))


if __name__ == "__main__":
    unittest.main()
