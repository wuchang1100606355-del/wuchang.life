from __future__ import annotations

import ast
import hashlib
import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from w7tp_runtime.state_field.acceptance import (
    DeterministicAcceptanceEngine,
    ExactHashAcceptanceContract,
)
from w7tp_runtime.state_field.canonical import (
    canonical_hash,
    canonical_json_bytes,
    canonical_json_loads,
    sha256_ref,
)
from w7tp_runtime.state_field.journal_recovery import (
    RecoveryDecision,
    RecoveryEngine,
    StartedEffectRecord,
    post_effect_cas_conflict,
    validate_effect_transition,
)
from w7tp_runtime.state_field.models import (
    ArtifactBinding,
    BindingState,
    CurrentPointer,
    DelegationRequest,
    EffectContract,
    EffectContractBody,
    EffectGateRequest,
    EffectObservation,
    EffectState,
    EvidenceLifecycleRequest,
    FlowRequest,
    Hold,
    IdempotencyClass,
    IngressRepresentationRequest,
    JournalEventType,
    NativeProof,
    ObservationContext,
    PrepareContext,
    PreparedEffect,
    Quarantine,
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
    CurrentWorktreeBindingResolver,
    LocalCreateFileEffectHandler,
    LocalCreateFileReceiverAdapter,
    StaticBindingResolver,
    StaticNativeRegistry,
    artifact_binding_hash,
    build_native_proof,
    effect_permit_proof_hash,
    encode_local_file_coordinate,
    prepared_effect_descriptor_ref,
    require_exact_effect_permit,
    require_exact_native_proof,
    seal_effect_permit_proof,
)
from w7tp_runtime.state_field.object_packet_store import ObjectPacketStore


REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_BRANCH = "agent/moving-v-v2-taiji8d-local-canary"
CURRENT_HEAD = "348e4f440b4a2d62a9f9cc169f94ab7fb3964e44"
STARTED_EVENT_REF = "sha256:" + "d" * 64


def make_contract(
    target_ref: str,
    payload: bytes,
    *,
    operation_id: str = "op-1",
    idempotency: IdempotencyClass = IdempotencyClass.IDEMPOTENT,
    acceptance_ref: str = "sha256:" + "a" * 64,
) -> EffectContract:
    body = EffectContractBody(
        schema_id="W7TP_EFFECT_CONTRACT_V1",
        operation_id=operation_id,
        target_coordinate_ref=target_ref,
        base_version_ref="sha256:" + "b" * 64,
        base_generation=7,
        receiver_adapter_ref="receiver.local.create-new-file.v1",
        effect_handler_ref="effect.local.create-new-file.v1",
        effect_input_ref=sha256_ref(payload),
        acceptance_contract_ref=acceptance_ref,
        idempotency_key=f"idempotency:{operation_id}",
        idempotency=idempotency,
    )
    digest = canonical_hash(body)
    return EffectContract(body, digest, f"sha256:{digest}")


class NativeProofTests(unittest.TestCase):
    def test_native_proof_binds_exact_request_and_capability(self):
        request = IngressRepresentationRequest(
            resource_ref="sha256:" + "1" * 64,
            manifest_ref="sha256:" + "2" * 64,
            effect_contract_ref="sha256:" + "3" * 64,
            capability_binding_refs=("sha256:" + "4" * 64,),
        )
        proof = build_native_proof(
            CAP_EXTERNAL_GATEWAY,
            request,
            "native-verifier:v1",
        )
        self.assertIs(
            require_exact_native_proof(
                proof, request, CAP_EXTERNAL_GATEWAY
            ),
            proof,
        )

        changed = replace(request, manifest_ref="sha256:" + "5" * 64)
        with self.assertRaisesRegex(
            Quarantine, "NATIVE_PROOF_REQUEST_HASH_CONFLICT"
        ):
            require_exact_native_proof(
                proof, changed, CAP_EXTERNAL_GATEWAY
            )

    def test_effect_permit_binds_contract_not_handler(self):
        request = EffectGateRequest(
            effect_contract_ref="sha256:" + "1" * 64,
            effect_contract_hash="1" * 64,
            policy_ref="policy:v1",
            d8_authorization_ref="d8-auth:fixture",
            d8_packet_ref="d8-packet:fixture",
            authority_ref="founder:fixture",
            base_version_ref="sha256:" + "2" * 64,
            base_generation=3,
            target_coordinate_ref="target:fixture",
            acceptance_contract_ref="sha256:" + "3" * 64,
            flow_proof_ref="sha256:" + "4" * 64,
        )
        native_binding_ref = "sha256:" + "8" * 64
        with tempfile.TemporaryDirectory() as temporary:
            proof_store = ObjectPacketStore(Path(temporary) / "proofs")
            provisional = VerifiedEffectPermit(
                policy_allowed=True,
                exact_d8_authorized=True,
                bound_request_hash=request_hash(request),
                native_binding_ref=native_binding_ref,
                proof_ref="sha256:" + "0" * 64,
                proof_hash="0" * 64,
                valid_until=datetime(2100, 1, 1, tzinfo=UTC),
            )
            permit = seal_effect_permit_proof(provisional, proof_store)
            self.assertIs(
                require_exact_effect_permit(
                    permit,
                    request,
                    proof_store=proof_store,
                    expected_native_binding_ref=native_binding_ref,
                    now=datetime(2099, 1, 1, tzinfo=UTC),
                ),
                permit,
            )

            changed = replace(
                request,
                effect_contract_ref="sha256:" + "9" * 64,
                effect_contract_hash="9" * 64,
            )
            with self.assertRaisesRegex(
                Quarantine, "EFFECT_PERMIT_REQUEST_HASH_CONFLICT"
            ):
                require_exact_effect_permit(
                    permit,
                    changed,
                    proof_store=proof_store,
                    expected_native_binding_ref=native_binding_ref,
                    now=datetime(2099, 1, 1, tzinfo=UTC),
                )

            with self.assertRaisesRegex(
                Quarantine, "EFFECT_PERMIT_NATIVE_BINDING_CONFLICT"
            ):
                require_exact_effect_permit(
                    permit,
                    request,
                    proof_store=proof_store,
                    expected_native_binding_ref="sha256:" + "9" * 64,
                    now=datetime(2099, 1, 1, tzinfo=UTC),
                )

    def test_effect_permit_rejects_naked_unstored_proof_hash(self):
        request = EffectGateRequest(
            "sha256:" + "1" * 64,
            "1" * 64,
            "policy:v1",
            "d8-auth:fixture",
            "d8-packet:fixture",
            "founder:fixture",
            None,
            0,
            "target:fixture",
            "sha256:" + "2" * 64,
            "sha256:" + "3" * 64,
        )
        native_binding_ref = "sha256:" + "8" * 64
        provisional = VerifiedEffectPermit(
            policy_allowed=True,
            exact_d8_authorized=True,
            bound_request_hash=request_hash(request),
            native_binding_ref=native_binding_ref,
            proof_ref="sha256:" + "0" * 64,
            proof_hash="0" * 64,
            valid_until=datetime(2100, 1, 1, tzinfo=UTC),
        )
        digest = effect_permit_proof_hash(provisional)
        naked = replace(
            provisional,
            proof_ref=f"sha256:{digest}",
            proof_hash=digest,
        )
        with tempfile.TemporaryDirectory() as temporary:
            empty_store = ObjectPacketStore(Path(temporary) / "proofs")
            with self.assertRaisesRegex(
                Hold, "HOLD_EFFECT_PERMIT_PROOF_UNAVAILABLE"
            ):
                require_exact_effect_permit(
                    naked,
                    request,
                    proof_store=empty_store,
                    expected_native_binding_ref=native_binding_ref,
                    now=datetime(2099, 1, 1, tzinfo=UTC),
                )

    def test_policy_allow_does_not_replace_exact_d8_authorization(self):
        request = EffectGateRequest(
            "sha256:" + "1" * 64,
            "1" * 64,
            "policy:v1",
            "d8-auth:fixture",
            "d8-packet:fixture",
            "founder:fixture",
            None,
            0,
            "target:fixture",
            "sha256:" + "2" * 64,
            "sha256:" + "3" * 64,
        )
        native_binding_ref = "sha256:" + "8" * 64
        provisional = VerifiedEffectPermit(
            policy_allowed=True,
            exact_d8_authorized=False,
            bound_request_hash=request_hash(request),
            native_binding_ref=native_binding_ref,
            proof_ref="sha256:" + "0" * 64,
            proof_hash="0" * 64,
            valid_until=datetime(2100, 1, 1, tzinfo=UTC),
        )
        with tempfile.TemporaryDirectory() as temporary:
            proof_store = ObjectPacketStore(Path(temporary) / "proofs")
            permit = seal_effect_permit_proof(provisional, proof_store)
            with self.assertRaisesRegex(
                Hold, "HOLD_EXACT_D8_AUTHORIZATION_MISSING"
            ):
                require_exact_effect_permit(
                    permit,
                    request,
                    proof_store=proof_store,
                    expected_native_binding_ref=native_binding_ref,
                    now=datetime(2099, 1, 1, tzinfo=UTC),
                )


class _ExactBindingVerifier:
    def verify_artifact(self, binding: ArtifactBinding) -> bool:
        return binding.artifact_hash == "a" * 64

    def verify_manifest(self, binding: ArtifactBinding) -> bool:
        return binding.manifest_ref.startswith("sha256:")


class _FivePort:
    def verify_ingress(self, request):
        return build_native_proof(CAP_EXTERNAL_GATEWAY, request, "v")

    def verify_exact_authorization(self, request):
        raise AssertionError("not invoked by registry unit test")

    def verify_delegation(self, request):
        return build_native_proof(CAP_DELEGATION, request, "v")

    def verify_flow(self, request):
        return build_native_proof(CAP_INFORMATION_FLOW, request, "v")

    def verify_and_advance(self, request):
        return build_native_proof(CAP_EVIDENCE_LIFECYCLE, request, "v")


class BindingAndRegistryTests(unittest.TestCase):
    def _binding(self, capability_id: str) -> ArtifactBinding:
        fields = {
            "node_id": "msi",
            "workspace_id": "taiji-hub",
            "artifact_ref": f"artifact:{capability_id}:v1",
            "manifest_ref": "sha256:" + "b" * 64,
            "artifact_hash": "a" * 64,
            "capability_id": capability_id,
            "version": "1",
            "adapter_ref": f"static:{capability_id}:v1",
        }
        provisional = ArtifactBinding(
            binding_ref="sha256:" + "0" * 64,
            binding_hash="0" * 64,
            binding_state=BindingState.VERIFIED,
            evidence_ref="sha256:" + "c" * 64,
            observed_at="2026-08-23T00:00:00Z",
            **fields,
        )
        digest = artifact_binding_hash(provisional)
        return replace(
            provisional,
            binding_ref=f"sha256:{digest}",
            binding_hash=digest,
        )

    def test_five_bindings_require_explicit_coordinates_and_static_ports(self):
        bindings = tuple(
            self._binding(capability)
            for capability in sorted(REQUIRED_NATIVE_CAPABILITIES)
        )
        selected = StaticBindingResolver(
            bindings, _ExactBindingVerifier()
        ).require_verified_exact_set(
            tuple(binding.binding_ref for binding in bindings)
        )
        port = _FivePort()
        registry = StaticNativeRegistry(
            {
                binding.binding_ref: port
                for binding in bindings
            }
        )
        native = registry.bind_all_static(selected)
        self.assertIs(native.external_gateway, port)
        self.assertIs(native.effect_gate, port)
        self.assertIs(native.delegation, port)
        self.assertIs(native.information_flow, port)
        self.assertIs(native.evidence_lifecycle, port)

        candidate = replace(
            bindings[0],
            binding_state=BindingState.CANDIDATE,
        )
        candidate_hash = artifact_binding_hash(candidate)
        forged_verified = replace(
            candidate,
            binding_ref=f"sha256:{candidate_hash}",
            binding_hash=candidate_hash,
            binding_state=BindingState.VERIFIED,
        )
        with self.assertRaisesRegex(
            Quarantine, "NATIVE_BINDING_HASH_CONFLICT"
        ):
            StaticBindingResolver(
                (forged_verified,), _ExactBindingVerifier()
            ).require_verified_exact_set(
                (forged_verified.binding_ref,),
                required_capabilities=frozenset(
                    {forged_verified.capability_id}
                ),
            )

    def test_msi_current_worktree_missing_anchor_is_expected_hold(self):
        result = CurrentWorktreeBindingResolver().resolve_current_worktree_only(
            root=REPO_ROOT,
            branch=CURRENT_BRANCH,
            head=CURRENT_HEAD,
            required_capabilities=REQUIRED_NATIVE_CAPABILITIES,
        )
        self.assertEqual(result.state, "HOLD")
        self.assertEqual(result.scope, "MSI_CURRENT_WORKTREE_ONLY")
        self.assertEqual(
            result.reason,
            "MSI_CURRENT_WORKTREE_NATIVE_SKILLS_ANCHOR_MISSING",
        )


class LocalEffectAndAcceptanceTests(unittest.TestCase):
    def test_bounded_local_create_file_and_deterministic_acceptance(self):
        payload = b"bounded benign candidate effect\n"
        expected_hash = hashlib.sha256(payload).hexdigest()
        acceptance_contract = ExactHashAcceptanceContract.seal(expected_hash)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "target").mkdir()
            objects = ObjectPacketStore(root / "evidence-store")
            target_ref = encode_local_file_coordinate(
                root, "unit-workspace", "target/result.bin"
            )
            contract = make_contract(
                target_ref,
                payload,
                acceptance_ref=acceptance_contract.acceptance_contract_ref,
            )
            context = PrepareContext(
                contract=contract,
                resource=ResourceReady(
                    "resource-1", "resource:1", "manifest:1", "mrs:1"
                ),
                pointer=CurrentPointer(
                    "resource-1", contract.body.base_version_ref, 7
                ),
            )
            adapter = LocalCreateFileReceiverAdapter(
                root,
                "unit-workspace",
                objects=objects,
            )
            handler = LocalCreateFileEffectHandler(
                root, "unit-workspace"
            )

            prepared = adapter.prepare(context)
            absent = adapter.observe(
                ObservationContext(
                    contract,
                    prepared,
                    STARTED_EVENT_REF,
                )
            )
            self.assertEqual(absent.effect_state, EffectState.ABSENT)
            absent_packet = canonical_json_loads(
                objects.get_exact(absent.evidence_ref)
            )
            self.assertEqual(absent_packet["effect_state"], "ABSENT")
            self.assertEqual(
                absent_packet["observation_method"],
                "DIR_FD_NOFOLLOW_FSTAT",
            )
            self.assertEqual(
                absent_packet["started_event_ref"],
                STARTED_EVENT_REF,
            )

            outcome = handler.apply(prepared, payload)
            self.assertEqual(outcome.result_ref, f"sha256:{expected_hash}")
            observed = adapter.observe(
                ObservationContext(
                    contract,
                    prepared,
                    STARTED_EVENT_REF,
                )
            )
            self.assertEqual(observed.effect_state, EffectState.COMPLETE)
            self.assertEqual(observed.actual_hash, expected_hash)
            observed_packet = canonical_json_loads(
                objects.get_exact(observed.evidence_ref)
            )
            self.assertEqual(observed_packet["actual_hash"], expected_hash)
            self.assertEqual(
                observed_packet["effect_contract_ref"],
                contract.effect_contract_ref,
            )
            self.assertEqual(
                observed_packet["started_event_ref"],
                STARTED_EVENT_REF,
            )

            acceptance = DeterministicAcceptanceEngine(
                (acceptance_contract,),
                objects=objects,
            ).evaluate_exact(
                acceptance_contract.acceptance_contract_ref,
                observed,
            )
            self.assertTrue(acceptance.accepted)
            acceptance_packet = canonical_json_loads(
                objects.get_exact(acceptance.evidence_ref)
            )
            self.assertTrue(acceptance_packet["accepted"])
            self.assertEqual(
                acceptance_packet["observation_ref"],
                observed.observation_ref,
            )

    def test_receiver_observe_requires_valid_started_event_ref(self):
        payload = b"started event evidence binding"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "target").mkdir()
            objects = ObjectPacketStore(root / "evidence-store")
            target_ref = encode_local_file_coordinate(
                root,
                "unit-workspace",
                "target/result.bin",
            )
            contract = make_contract(target_ref, payload)
            context = PrepareContext(
                contract,
                ResourceReady("r", "rr", "m", "mrs"),
                CurrentPointer("r", contract.body.base_version_ref, 7),
            )
            adapter = LocalCreateFileReceiverAdapter(
                root,
                "unit-workspace",
                objects=objects,
            )
            prepared = adapter.prepare(context)

            for started_event_ref in (None, "started-event:not-sha256"):
                with self.subTest(started_event_ref=started_event_ref):
                    with self.assertRaisesRegex(
                        Quarantine,
                        "OBSERVATION_STARTED_EVENT_REF_CONFLICT",
                    ):
                        adapter.observe(
                            ObservationContext(
                                contract,
                                prepared,
                                started_event_ref,
                            )
                        )

    def test_receiver_rejects_contract_root_outside_bound_workspace(self):
        payload = b"no escape"
        with tempfile.TemporaryDirectory() as allowed, tempfile.TemporaryDirectory() as other:
            objects = ObjectPacketStore(Path(allowed) / "evidence-store")
            target_ref = encode_local_file_coordinate(
                Path(other).resolve(), "unit-workspace", "result.bin"
            )
            contract = make_contract(target_ref, payload)
            context = PrepareContext(
                contract,
                ResourceReady("r", "rr", "m", "mrs"),
                CurrentPointer("r", contract.body.base_version_ref, 7),
            )
            adapter = LocalCreateFileReceiverAdapter(
                Path(allowed).resolve(),
                "unit-workspace",
                objects=objects,
            )
            with self.assertRaisesRegex(
                Quarantine, "TARGET_WORKSPACE_BINDING_CONFLICT"
            ):
                adapter.prepare(context)

    def test_receiver_observe_rejects_parent_symlink_swap(self):
        payload = b"must stay beneath bound workspace"
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as outside:
            root = Path(temporary).resolve()
            outside_root = Path(outside).resolve()
            (root / "target").mkdir()
            objects = ObjectPacketStore(root / "evidence-store")
            target_ref = encode_local_file_coordinate(
                root,
                "unit-workspace",
                "target/result.bin",
            )
            contract = make_contract(target_ref, payload)
            context = PrepareContext(
                contract,
                ResourceReady("r", "rr", "m", "mrs"),
                CurrentPointer("r", contract.body.base_version_ref, 7),
            )
            adapter = LocalCreateFileReceiverAdapter(
                root,
                "unit-workspace",
                objects=objects,
            )
            prepared = adapter.prepare(context)

            (root / "target").rename(root / "original-target")
            (root / "target").symlink_to(
                outside_root,
                target_is_directory=True,
            )

            with self.assertRaisesRegex(
                Quarantine, "TARGET_PATH_SYMLINK_OR_KIND_CONFLICT"
            ):
                adapter.observe(
                    ObservationContext(
                        contract,
                        prepared,
                        STARTED_EVENT_REF,
                    )
                )
            self.assertFalse((outside_root / "result.bin").exists())

    def test_receiver_observe_rejects_workspace_root_symlink_swap(self):
        payload = b"root identity must not drift"
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as outside:
            base = Path(temporary).resolve()
            workspace = base / "workspace"
            workspace.mkdir()
            (workspace / "target").mkdir()
            outside_root = Path(outside).resolve()
            objects = ObjectPacketStore(base / "evidence-store")
            target_ref = encode_local_file_coordinate(
                workspace,
                "unit-workspace",
                "target/result.bin",
            )
            contract = make_contract(target_ref, payload)
            context = PrepareContext(
                contract,
                ResourceReady("r", "rr", "m", "mrs"),
                CurrentPointer("r", contract.body.base_version_ref, 7),
            )
            adapter = LocalCreateFileReceiverAdapter(
                workspace,
                "unit-workspace",
                objects=objects,
            )
            prepared = adapter.prepare(context)

            workspace.rename(base / "original-workspace")
            workspace.symlink_to(outside_root, target_is_directory=True)

            with self.assertRaisesRegex(
                Quarantine, "TARGET_WORKSPACE_SYMLINK_OR_KIND_CONFLICT"
            ):
                adapter.observe(
                    ObservationContext(
                        contract,
                        prepared,
                        STARTED_EVENT_REF,
                    )
                )
            self.assertFalse((outside_root / "target/result.bin").exists())

    def test_acceptance_rejects_naked_unstored_observation_ref(self):
        payload = b"naked observation is not evidence"
        expected_hash = hashlib.sha256(payload).hexdigest()
        acceptance_contract = ExactHashAcceptanceContract.seal(expected_hash)
        observation = EffectObservation(
            EffectState.COMPLETE,
            "sha256:" + "1" * 64,
            "sha256:" + "1" * 64,
            expected_hash,
        )
        with tempfile.TemporaryDirectory() as temporary:
            objects = ObjectPacketStore(Path(temporary) / "evidence-store")
            engine = DeterministicAcceptanceEngine(
                (acceptance_contract,),
                objects=objects,
            )
            with self.assertRaisesRegex(
                Hold, "HOLD_ACCEPTANCE_OBSERVATION_UNAVAILABLE"
            ):
                engine.evaluate_exact(
                    acceptance_contract.acceptance_contract_ref,
                    observation,
                )

    def test_acceptance_rejects_wrong_persisted_observation_packet(self):
        payload = b"persisted packet must bind observation claims"
        expected_hash = hashlib.sha256(payload).hexdigest()
        acceptance_contract = ExactHashAcceptanceContract.seal(expected_hash)
        wrong_packet = canonical_json_bytes(
            {
                "schema_id": "W7TP_LOCAL_FILE_OBSERVATION_V1",
                "effect_state": EffectState.ABSENT,
                "started_event_ref": STARTED_EVENT_REF,
                "actual_hash": None,
            }
        )
        with tempfile.TemporaryDirectory() as temporary:
            objects = ObjectPacketStore(Path(temporary) / "evidence-store")
            wrong_ref = objects.put_bytes(wrong_packet)
            observation = EffectObservation(
                EffectState.COMPLETE,
                wrong_ref,
                wrong_ref,
                expected_hash,
            )
            engine = DeterministicAcceptanceEngine(
                (acceptance_contract,),
                objects=objects,
            )
            with self.assertRaisesRegex(
                Quarantine, "ACCEPTANCE_OBSERVATION_BODY_CONFLICT"
            ):
                engine.evaluate_exact(
                    acceptance_contract.acceptance_contract_ref,
                    observation,
                )


class _Journal:
    def __init__(self, started: StartedEffectRecord) -> None:
        self.started = started
        self.actions: list[object] = []

    def require_started_without_observed(self, operation_id):
        self.actions.append(("require_started", operation_id))
        return self.started

    def append_sync(self, event_type, payload):
        self.actions.append(("append", event_type, dict(payload)))
        return "sha256:" + "e" * 64


class _Loader:
    def __init__(self, contract):
        self.contract = contract

    def load(self, ref):
        if ref != self.contract.effect_contract_ref:
            raise AssertionError("wrong contract ref")
        return self.contract


class _RecoveryAdapter:
    adapter_ref = "receiver.local.create-new-file.v1"

    def __init__(self, observation, actions):
        self.observation = observation
        self.actions = actions

    def prepare(self, context):
        raise AssertionError("recovery must not prepare before observation")

    def observe(self, context):
        self.actions.append("observe")
        return self.observation


class _RecoveryHandler:
    handler_ref = "effect.local.create-new-file.v1"

    def __init__(self, idempotency, actions):
        self.idempotency = idempotency
        self.actions = actions

    def apply(self, prepared, exact_input):
        self.actions.append("apply")
        raise AssertionError("recovery must not blindly reapply")


class RecoveryTests(unittest.TestCase):
    def _recover(self, state, idempotency=IdempotencyClass.IDEMPOTENT):
        payload = b"recovery"
        target = "target:recovery"
        contract = make_contract(
            target,
            payload,
            operation_id="recover-1",
            idempotency=idempotency,
        )
        prepared = PreparedEffect(
            effect_contract_ref=contract.effect_contract_ref,
            receiver_adapter_ref=contract.body.receiver_adapter_ref,
            effect_handler_ref=contract.body.effect_handler_ref,
            descriptor_ref=prepared_effect_descriptor_ref(contract),
            target_coordinate_ref=target,
            idempotency_key=contract.body.idempotency_key,
        )
        started = StartedEffectRecord(
            "recover-1",
            contract.effect_contract_ref,
            prepared,
            "sha256:" + "d" * 64,
            1,
        )
        journal = _Journal(started)
        receiver_actions: list[str] = []
        actual_hash = (
            hashlib.sha256(payload).hexdigest()
            if state in {EffectState.COMPLETE, EffectState.PARTIAL}
            else None
        )
        observation = EffectObservation(
            state,
            "sha256:" + "1" * 64,
            "sha256:" + "2" * 64,
            actual_hash,
        )
        adapter = _RecoveryAdapter(observation, receiver_actions)
        handler = _RecoveryHandler(idempotency, receiver_actions)
        engine = RecoveryEngine(
            journal,
            _Loader(contract),
            adapters={adapter.adapter_ref: adapter},
            handlers={handler.handler_ref: handler},
        )
        result = engine.recover_started_without_observed("recover-1")
        return result, journal, receiver_actions

    def test_started_without_observed_first_reobserves_complete(self):
        result, journal, receiver_actions = self._recover(
            EffectState.COMPLETE
        )
        self.assertEqual(receiver_actions, ["observe"])
        self.assertEqual(
            result.decision, RecoveryDecision.RESUME_AFTER_OBSERVATION
        )
        self.assertEqual(
            journal.actions[-1][1], JournalEventType.EFFECT_OBSERVED
        )

    def test_absent_idempotent_allows_fresh_exact_retry_decision(self):
        result, _, receiver_actions = self._recover(EffectState.ABSENT)
        self.assertEqual(receiver_actions, ["observe"])
        self.assertEqual(
            result.decision,
            RecoveryDecision.RETRY_IDEMPOTENT_EXACT_OPERATION,
        )
        self.assertTrue(result.retry_allowed)

    def test_absent_non_idempotent_holds(self):
        result, _, receiver_actions = self._recover(
            EffectState.ABSENT,
            IdempotencyClass.NON_IDEMPOTENT,
        )
        self.assertEqual(receiver_actions, ["observe"])
        self.assertEqual(
            result.decision, RecoveryDecision.HOLD_NON_IDEMPOTENT
        )
        self.assertFalse(result.retry_allowed)

    def test_partial_and_unknown_quarantine_without_reapply(self):
        for state in (EffectState.PARTIAL, EffectState.UNKNOWN):
            with self.subTest(state=state):
                result, _, receiver_actions = self._recover(state)
                self.assertEqual(receiver_actions, ["observe"])
                self.assertEqual(
                    result.decision,
                    RecoveryDecision.QUARANTINE_UNKNOWN_EFFECT,
                )

    def test_journal_retry_transition_requires_proven_absent_idempotent(self):
        with self.assertRaisesRegex(
            Quarantine, "EFFECT_JOURNAL_UNSAFE_RETRY_CONFLICT"
        ):
            validate_effect_transition(
                JournalEventType.EFFECT_FAILED,
                JournalEventType.EFFECT_PREPARED,
            )
        validate_effect_transition(
            JournalEventType.EFFECT_FAILED,
            JournalEventType.EFFECT_PREPARED,
            retry_proven_absent=True,
            retry_idempotent=True,
        )

    def test_post_effect_cas_conflict_never_reapplies(self):
        result = post_effect_cas_conflict("op-cas")
        self.assertEqual(result.state, "QUARANTINED")
        self.assertFalse(result.retry_allowed)
        self.assertEqual(
            result.decision,
            RecoveryDecision.QUARANTINE_POST_EFFECT_CAS_CONFLICT,
        )


class StaticSafetyTests(unittest.TestCase):
    def test_runtime_modules_have_no_dynamic_or_command_execution(self):
        forbidden_imports = {"importlib", "subprocess"}
        forbidden_calls = {"eval", "exec", "compile", "__import__"}
        for relative in (
            "w7tp_runtime/state_field/native_ports.py",
            "w7tp_runtime/state_field/acceptance.py",
            "w7tp_runtime/state_field/journal_recovery.py",
        ):
            tree = ast.parse((REPO_ROOT / relative).read_text("utf-8"))
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
            self.assertTrue(forbidden_imports.isdisjoint(imported), relative)
            self.assertTrue(forbidden_calls.isdisjoint(calls), relative)


if __name__ == "__main__":
    unittest.main(verbosity=2)
