from __future__ import annotations

import ast
import hashlib
import tempfile
import unittest
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from w7tp_runtime.state_field.acceptance import (
    DeterministicAcceptanceEngine,
    ExactHashAcceptanceContract,
)
from w7tp_runtime.state_field.executor import (
    DurableOperationJournal,
    StateFieldExecutor,
)
from w7tp_runtime.state_field.models import (
    ArtifactBinding,
    BindingState,
    CurrentPointer,
    EffectContract,
    EffectContractBody,
    EffectGateRequest,
    EffectState,
    ExecuteCommand,
    IdempotencyClass,
    JournalEventType,
    PrepareContext,
    REQUIRED_NATIVE_CAPABILITIES,
    ResourceReady,
    VerifiedEffectPermit,
    request_hash,
)
from w7tp_runtime.state_field.native_ports import (
    CAP_DELEGATION,
    CAP_EFFECT_GATE,
    CAP_EVIDENCE_LIFECYCLE,
    CAP_EXTERNAL_GATEWAY,
    CAP_INFORMATION_FLOW,
    LocalCreateFileEffectHandler,
    LocalCreateFileReceiverAdapter,
    NativePorts,
    StaticBindingResolver,
    StaticNativeRegistry,
    artifact_binding_hash,
    build_native_proof,
    effect_permit_proof_hash,
    encode_local_file_coordinate,
    seal_effect_permit_proof,
)
from w7tp_runtime.state_field.object_packet_store import ObjectPacketStore
from w7tp_runtime.state_field.store import (
    CASConflict as StoreCASConflict,
    StateFieldStore,
)


FIXED_NOW = datetime(2026, 8, 23, 7, 0, tzinfo=UTC)
BASE_VERSION = "sha256:" + "0" * 64


class _ExactArtifactVerifier:
    def verify_artifact(self, binding):
        return bool(binding.artifact_ref and binding.artifact_hash)

    def verify_manifest(self, binding):
        return bool(binding.manifest_ref)


class _ResourceResolver:
    def __init__(self, resource: ResourceReady, trace: list[str]) -> None:
        self.resource = resource
        self.trace = trace

    def require_resource_ready(self, mrs_ref: str) -> ResourceReady:
        self.trace.append("resource")
        if mrs_ref != self.resource.mrs_ref:
            raise AssertionError("unexpected MRS coordinate")
        return self.resource


class _IngressPort:
    def __init__(self, trace):
        self.trace = trace

    def verify_ingress(self, request):
        self.trace.append(CAP_EXTERNAL_GATEWAY)
        return build_native_proof(CAP_EXTERNAL_GATEWAY, request, "unit:ingress")


class _DelegationPort:
    def __init__(self, trace):
        self.trace = trace

    def verify_delegation(self, request):
        self.trace.append(CAP_DELEGATION)
        return build_native_proof(CAP_DELEGATION, request, "unit:delegation")


class _FlowPort:
    def __init__(self, trace):
        self.trace = trace

    def verify_flow(self, request):
        self.trace.append(CAP_INFORMATION_FLOW)
        return build_native_proof(CAP_INFORMATION_FLOW, request, "unit:flow")


class _GatePort:
    def __init__(
        self,
        trace,
        proof_store,
        native_binding_ref,
        *,
        exact_d8_authorized: bool = True,
        after_verify=None,
    ) -> None:
        self.trace = trace
        self.proof_store = proof_store
        self.native_binding_ref = native_binding_ref
        self.exact_d8_authorized = exact_d8_authorized
        self.after_verify = after_verify
        self.request = None

    def verify_exact_authorization(self, request):
        self.trace.append(CAP_EFFECT_GATE)
        self.request = request
        draft = VerifiedEffectPermit(
            policy_allowed=True,
            exact_d8_authorized=self.exact_d8_authorized,
            bound_request_hash=request_hash(request),
            native_binding_ref=self.native_binding_ref,
            proof_ref="sha256:" + "0" * 64,
            proof_hash="0" * 64,
            valid_until=FIXED_NOW + timedelta(hours=1),
        )
        permit = seal_effect_permit_proof(draft, self.proof_store)
        if self.after_verify is not None:
            self.after_verify()
        return permit


class _LifecyclePort:
    def __init__(self, trace):
        self.trace = trace

    def verify_and_advance(self, request):
        self.trace.append(CAP_EVIDENCE_LIFECYCLE)
        return build_native_proof(
            CAP_EVIDENCE_LIFECYCLE,
            request,
            "unit:lifecycle",
        )


class _CountingHandler:
    handler_ref = "effect.local.create-new-file.v1"
    idempotency = IdempotencyClass.IDEMPOTENT

    def __init__(self, delegate, store):
        self.delegate = delegate
        self.store = store
        self.count = 0

    def apply(self, prepared, exact_input):
        events = self.store.journal_events("operation-1")
        if not events or events[-1].event_type != "EFFECT_STARTED":
            raise AssertionError("EFFECT_STARTED was not durable before apply")
        self.count += 1
        return self.delegate.apply(prepared, exact_input)


class _SubstitutingAdapter:
    adapter_ref = "receiver.local.create-new-file.v1"

    def __init__(self, delegate):
        self.delegate = delegate

    def prepare(self, context):
        prepared = self.delegate.prepare(context)
        return replace(
            prepared,
            target_coordinate_ref="local-file-v1:forged-target",
        )

    def observe(self, context):
        return self.delegate.observe(context)


class _CASConflictStore:
    def __init__(self, delegate):
        self.delegate = delegate

    def __getattr__(self, name):
        return getattr(self.delegate, name)

    def commit_state(self, write):
        del write
        raise StoreCASConflict("STATE_DRIFT_RECOMPUTE_NEW_OPERATION")


def _binding(capability_id: str) -> ArtifactBinding:
    provisional = ArtifactBinding(
        binding_ref="sha256:" + "0" * 64,
        binding_hash="0" * 64,
        node_id="MSI",
        workspace_id="unit-workspace",
        artifact_ref=f"unit-artifact:{capability_id}",
        manifest_ref=f"unit-manifest:{capability_id}",
        artifact_hash=hashlib.sha256(capability_id.encode()).hexdigest(),
        capability_id=capability_id,
        version="1.0.0",
        adapter_ref="unit.native.v1",
        binding_state=BindingState.VERIFIED,
        evidence_ref=f"unit-evidence:{capability_id}",
        observed_at="2026-08-23T07:00:00Z",
    )
    digest = artifact_binding_hash(provisional)
    return replace(
        provisional,
        binding_ref=f"sha256:{digest}",
        binding_hash=digest,
    )


class ExecutorHarness:
    def __init__(self, testcase: unittest.TestCase) -> None:
        self.testcase = testcase
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        (self.workspace / "target").mkdir()
        self.objects = ObjectPacketStore(self.root / "objects")
        self.store = StateFieldStore(self.root / "state.sqlite3")
        self.store.register_workspace(
            workspace_id="unit-workspace",
            node_id="MSI",
            root_ref=str(self.workspace),
            created_at="2026-08-23T07:00:00Z",
        )
        self.store.register_resource(
            resource_id="resource-1",
            workspace_id="unit-workspace",
            resource_kind="FILE",
            version_ref=BASE_VERSION,
            generation=0,
            created_at="2026-08-23T07:00:00Z",
        )
        self.payload = b"candidate executor exact payload\n"
        self.input_ref = self.objects.put_bytes(self.payload)
        self.acceptance_contract = ExactHashAcceptanceContract.seal(
            hashlib.sha256(self.payload).hexdigest()
        )
        target_ref = encode_local_file_coordinate(
            self.workspace,
            "unit-workspace",
            "target/result.bin",
        )
        self.contract = EffectContract.seal(
            EffectContractBody(
                schema_id="W7TP_EFFECT_CONTRACT_V1",
                operation_id="operation-1",
                target_coordinate_ref=target_ref,
                base_version_ref=BASE_VERSION,
                base_generation=0,
                receiver_adapter_ref="receiver.local.create-new-file.v1",
                effect_handler_ref="effect.local.create-new-file.v1",
                effect_input_ref=self.input_ref,
                acceptance_contract_ref=(
                    self.acceptance_contract.acceptance_contract_ref
                ),
                idempotency_key="idempotency-1",
                idempotency=IdempotencyClass.IDEMPOTENT,
            ),
            self.objects,
        )
        self.bindings = tuple(
            _binding(capability)
            for capability in sorted(REQUIRED_NATIVE_CAPABILITIES)
        )
        self.binding_resolver = StaticBindingResolver(
            self.bindings,
            _ExactArtifactVerifier(),
        )
        self.trace: list[str] = []
        self.resource = ResourceReady(
            resource_id="resource-1",
            resource_ref="resource:unit:1",
            manifest_ref="manifest:unit:1",
            mrs_ref="mrs:unit:1",
        )
        self.adapter = LocalCreateFileReceiverAdapter(
            self.workspace,
            "unit-workspace",
            objects=self.objects,
        )
        self.handler = _CountingHandler(
            LocalCreateFileEffectHandler(
                self.workspace,
                "unit-workspace",
            ),
            self.store,
        )
        self.command = ExecuteCommand(
            operation_id="operation-1",
            resource_id="resource-1",
            mrs_ref="mrs:unit:1",
            effect_contract_ref=self.contract.effect_contract_ref,
            native_binding_refs=tuple(
                binding.binding_ref for binding in self.bindings
            ),
            policy_ref="policy:unit:allow",
            d8_authorization_ref="d8-auth:unit:exact",
            d8_packet_ref="d8-packet:unit:exact",
            authority_ref="authority:unit:fixture",
            delegation_chain_ref="delegation:unit:bounded",
            idempotency_key="idempotency-1",
            attempt_no=1,
        )
        self.gate_binding_ref = next(
            binding.binding_ref
            for binding in self.bindings
            if binding.capability_id == CAP_EFFECT_GATE
        )
        self.gate = _GatePort(
            self.trace,
            self.objects,
            self.gate_binding_ref,
        )

    def registry(self, gate=None):
        gate = gate or self.gate
        mapping = {
            next(b.binding_ref for b in self.bindings if b.capability_id == CAP_EXTERNAL_GATEWAY):
                _IngressPort(self.trace),
            next(b.binding_ref for b in self.bindings if b.capability_id == CAP_DELEGATION):
                _DelegationPort(self.trace),
            next(b.binding_ref for b in self.bindings if b.capability_id == CAP_INFORMATION_FLOW):
                _FlowPort(self.trace),
            next(b.binding_ref for b in self.bindings if b.capability_id == CAP_EFFECT_GATE):
                gate,
            next(b.binding_ref for b in self.bindings if b.capability_id == CAP_EVIDENCE_LIFECYCLE):
                _LifecyclePort(self.trace),
        }
        return StaticNativeRegistry(mapping)

    def executor(self, *, store=None, gate=None, adapter=None, handler=None):
        adapter = adapter or self.adapter
        handler = handler or self.handler
        return StateFieldExecutor(
            store=store or self.store,
            objects=self.objects,
            binding_resolver=self.binding_resolver,
            native_registry=self.registry(gate),
            resource_resolver=_ResourceResolver(self.resource, self.trace),
            acceptance_engine=DeterministicAcceptanceEngine(
                (self.acceptance_contract,),
                objects=self.objects,
            ),
            adapters={adapter.adapter_ref: adapter},
            handlers={handler.handler_ref: handler},
            clock=lambda: FIXED_NOW,
        )

    def seed_started(self, materialized_bytes: bytes | None):
        flow_proof_ref = "sha256:" + "4" * 64
        gate_request = EffectGateRequest(
            effect_contract_ref=self.contract.effect_contract_ref,
            effect_contract_hash=self.contract.effect_contract_hash,
            policy_ref=self.command.policy_ref,
            d8_authorization_ref=self.command.d8_authorization_ref,
            d8_packet_ref=self.command.d8_packet_ref,
            authority_ref=self.command.authority_ref,
            base_version_ref=self.contract.body.base_version_ref,
            base_generation=self.contract.body.base_generation,
            target_coordinate_ref=self.contract.body.target_coordinate_ref,
            acceptance_contract_ref=(
                self.contract.body.acceptance_contract_ref
            ),
            flow_proof_ref=flow_proof_ref,
        )
        permit = self.gate.verify_exact_authorization(gate_request)
        self.store.claim_effect_operation(
            idempotency_key=self.command.idempotency_key,
            operation_id=self.command.operation_id,
            effect_contract_ref=self.contract.effect_contract_ref,
            attempt_no=1,
            claimed_at="2026-08-23T07:00:00Z",
        )
        pointer = CurrentPointer(
            resource_id="resource-1",
            version_ref=BASE_VERSION,
            generation=0,
        )
        journal = DurableOperationJournal(
            self.store,
            self.objects,
            self.command,
            self.contract,
            lambda: FIXED_NOW,
        )
        journal.append_sync(
            JournalEventType.EFFECT_PREPARED,
            {
                "ingress_proof_ref": "sha256:" + "1" * 64,
                "delegation_proof_ref": "sha256:" + "2" * 64,
                "flow_proof_ref": flow_proof_ref,
                "permit_proof_ref": permit.proof_ref,
                "gate_request_hash": permit.bound_request_hash,
                "native_binding_refs": [
                    binding.binding_ref for binding in self.bindings
                ],
                "pointer_generation": 0,
                "pointer_version_ref": BASE_VERSION,
                "receiver_prepare_effect": "NONE",
            },
        )
        prepared = self.adapter.prepare(
            PrepareContext(
                contract=self.contract,
                resource=self.resource,
                pointer=pointer,
            )
        )
        started_ref = journal.append_sync(
            JournalEventType.EFFECT_STARTED,
            {
                "prepared": asdict(prepared),
                "effect_input_ref": self.contract.body.effect_input_ref,
            },
        )
        if materialized_bytes is not None:
            self.handler.delegate.apply(prepared, materialized_bytes)
        return prepared, started_ref

    def close(self):
        self.store.close()
        self.temporary.cleanup()


class StateFieldExecutorTests(unittest.TestCase):
    def setUp(self):
        self.harness = ExecutorHarness(self)

    def tearDown(self):
        self.harness.close()

    def test_full_candidate_loop_and_exact_replay(self):
        executor = self.harness.executor()
        result = executor.execute(self.harness.command)

        self.assertEqual(result.state, "COMPLETED")
        self.assertFalse(result.replayed)
        self.assertEqual(
            self.harness.trace,
            [
                "resource",
                CAP_EXTERNAL_GATEWAY,
                CAP_DELEGATION,
                CAP_INFORMATION_FLOW,
                CAP_EFFECT_GATE,
                CAP_EVIDENCE_LIFECYCLE,
            ],
        )
        self.assertEqual(
            self.harness.gate.request.effect_contract_ref,
            self.harness.contract.effect_contract_ref,
        )
        self.assertNotEqual(
            self.harness.gate.request.effect_contract_ref,
            self.harness.contract.body.effect_handler_ref,
        )
        self.assertEqual(self.harness.handler.count, 1)
        self.assertEqual(
            (self.harness.workspace / "target/result.bin").read_bytes(),
            self.harness.payload,
        )
        pointer = self.harness.store.load_current_pointer_fresh("resource-1")
        self.assertEqual(pointer.generation, 1)
        self.assertTrue(self.harness.store.receipt_exists(result.receipt_ref))
        self.assertTrue(
            self.harness.store.transition_exists(result.transition_ref)
        )
        event_types = tuple(
            event.event_type
            for event in self.harness.store.journal_events("operation-1")
        )
        self.assertEqual(
            event_types,
            (
                "EFFECT_PREPARED",
                "EFFECT_STARTED",
                "EFFECT_OBSERVED",
                "EFFECT_ACCEPTED",
                "STATE_COMMITTED",
            ),
        )

        trace_before = tuple(self.harness.trace)
        replay = executor.execute(self.harness.command)
        self.assertEqual(replay.state, "COMPLETED")
        self.assertTrue(replay.replayed)
        self.assertEqual(replay.receipt_ref, result.receipt_ref)
        self.assertEqual(self.harness.handler.count, 1)
        self.assertEqual(tuple(self.harness.trace), trace_before)
        self.assertEqual(
            self.harness.store.load_current_pointer_fresh(
                "resource-1"
            ).generation,
            1,
        )

    def test_pointer_drift_after_gate_has_no_effect(self):
        def drift():
            self.harness.store.connection.execute(
                "UPDATE current_pointer SET generation = generation + 1 "
                "WHERE resource_id = 'resource-1'"
            )

        gate = _GatePort(
            self.harness.trace,
            self.harness.objects,
            self.harness.gate_binding_ref,
            after_verify=drift,
        )
        result = self.harness.executor(gate=gate).execute(
            self.harness.command
        )
        self.assertEqual(result.state, "HOLD")
        self.assertEqual(
            result.reason,
            "STATE_DRIFT_RECOMPUTE_NEW_OPERATION",
        )
        self.assertTrue(result.no_effect)
        self.assertEqual(self.harness.handler.count, 0)
        self.assertFalse(
            (self.harness.workspace / "target/result.bin").exists()
        )
        self.assertEqual(
            tuple(
                event.event_type
                for event in self.harness.store.journal_events("operation-1")
            ),
            ("STATE_DRIFT",),
        )

    def test_policy_allow_never_substitutes_for_exact_d8(self):
        gate = _GatePort(
            self.harness.trace,
            self.harness.objects,
            self.harness.gate_binding_ref,
            exact_d8_authorized=False,
        )
        result = self.harness.executor(gate=gate).execute(
            self.harness.command
        )
        self.assertEqual(result.state, "HOLD")
        self.assertEqual(
            result.reason,
            "HOLD_EXACT_D8_AUTHORIZATION_MISSING",
        )
        self.assertEqual(self.harness.handler.count, 0)
        self.assertFalse(
            (self.harness.workspace / "target/result.bin").exists()
        )

    def test_post_effect_cas_conflict_quarantines_without_reapply(self):
        conflict_store = _CASConflictStore(self.harness.store)
        result = self.harness.executor(store=conflict_store).execute(
            self.harness.command
        )
        self.assertEqual(result.state, "QUARANTINED")
        self.assertEqual(
            result.reason,
            "QUARANTINE_POST_EFFECT_CAS_CONFLICT",
        )
        self.assertEqual(self.harness.handler.count, 1)
        self.assertTrue(
            (self.harness.workspace / "target/result.bin").exists()
        )
        self.assertEqual(
            self.harness.store.load_current_pointer_fresh(
                "resource-1"
            ).generation,
            0,
        )
        self.assertEqual(
            self.harness.store.journal_events("operation-1")[-1].event_type,
            "EFFECT_FAILED",
        )

        retry = self.harness.executor().execute(
            replace(self.harness.command, attempt_no=2)
        )
        self.assertEqual(retry.state, "QUARANTINED")
        self.assertEqual(self.harness.handler.count, 1)

    def test_started_recovery_reobserves_and_commits_without_reapply(self):
        self.harness.seed_started(self.harness.payload)

        result = self.harness.executor().execute(self.harness.command)

        self.assertEqual(result.state, "COMPLETED")
        self.assertEqual(self.harness.handler.count, 0)
        self.assertEqual(
            self.harness.store.load_current_pointer_fresh(
                "resource-1"
            ).generation,
            1,
        )
        self.assertEqual(
            tuple(
                event.event_type
                for event in self.harness.store.journal_events(
                    "operation-1"
                )
            ),
            (
                "EFFECT_PREPARED",
                "EFFECT_STARTED",
                "EFFECT_OBSERVED",
                "EFFECT_ACCEPTED",
                "STATE_COMMITTED",
            ),
        )

    def test_partial_recovery_quarantines_without_reapply(self):
        self.harness.seed_started(b"wrong receiver bytes")

        result = self.harness.executor().execute(self.harness.command)

        self.assertEqual(result.state, "QUARANTINED")
        self.assertEqual(
            result.reason,
            "QUARANTINE_EFFECT_STATE_UNKNOWN_OR_PARTIAL",
        )
        self.assertEqual(self.harness.handler.count, 0)
        self.assertEqual(
            self.harness.store.load_current_pointer_fresh(
                "resource-1"
            ).generation,
            0,
        )

    def test_new_attempt_cannot_bypass_started_recovery(self):
        self.harness.seed_started(None)

        result = self.harness.executor().execute(
            replace(self.harness.command, attempt_no=2)
        )

        self.assertEqual(result.state, "QUARANTINED")
        self.assertEqual(result.reason, "ATTEMPT_NUMBER_SEQUENCE_CONFLICT")
        self.assertEqual(self.harness.handler.count, 0)
        self.assertFalse(
            (self.harness.workspace / "target/result.bin").exists()
        )

    def test_proven_absent_retry_reruns_gate_and_base_check(self):
        self.harness.seed_started(None)
        recovered = self.harness.executor().execute(self.harness.command)
        self.assertEqual(recovered.state, "HOLD")
        self.assertEqual(self.harness.handler.count, 0)

        retried = self.harness.executor().execute(
            replace(self.harness.command, attempt_no=2)
        )

        self.assertEqual(retried.state, "COMPLETED")
        self.assertEqual(self.harness.handler.count, 1)
        self.assertEqual(
            self.harness.trace.count(CAP_EFFECT_GATE),
            2,
        )
        self.assertEqual(
            self.harness.store.load_current_pointer_fresh(
                "resource-1"
            ).generation,
            1,
        )

    def test_prepared_target_substitution_is_terminal(self):
        malicious = _SubstitutingAdapter(self.harness.adapter)

        result = self.harness.executor(adapter=malicious).execute(
            self.harness.command
        )

        self.assertEqual(result.state, "QUARANTINED")
        self.assertEqual(result.reason, "PREPARED_EFFECT_BINDING_CONFLICT")
        self.assertEqual(self.harness.handler.count, 0)
        self.assertEqual(
            self.harness.store.journal_events("operation-1")[-1].event_type,
            "EFFECT_FAILED",
        )

    def test_executor_has_no_dynamic_or_command_execution(self):
        source = Path(
            "w7tp_runtime/state_field/executor.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_imports = {"importlib", "subprocess"}
        forbidden_calls = {"eval", "exec", "compile", "__import__"}
        imported = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
        }
        self.assertTrue(forbidden_imports.isdisjoint(imported))
        self.assertTrue(forbidden_calls.isdisjoint(calls))


if __name__ == "__main__":
    unittest.main(verbosity=2)
