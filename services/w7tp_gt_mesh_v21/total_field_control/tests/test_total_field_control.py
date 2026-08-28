from __future__ import annotations

import copy
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from typing import Mapping

from w7tp_gt_mesh.core import MeshHold
from w7tp_gt_mesh.journal import MeshStorage

from total_field_control.adapters import CanaryActionDispatcher, CanaryPolicy, RunnerResult
from total_field_control.agent import TotalFieldNodeAgent
from total_field_control.authority import REQUIRED_CONTROL_SCOPES, verify_task_envelope
from total_field_control.controller import plan_task_envelope
from total_field_control.placement import deterministic_place


NOW = 2_000_000_000
IMAGE_REF = "registry.example/w7tp/canary@sha256:" + "a" * 64


class InjectedTestEd25519:
    """Test-only signer/verifier contract; no key material exists in the tree."""

    def sign_detached(self, *, verifier_ref: str, payload_sha256: str) -> str:
        return f"ed25519:test:{verifier_ref}:{payload_sha256}"

    def verify_detached(self, *, verifier_ref: str, payload_sha256: str, signature: str) -> bool:
        return signature == self.sign_detached(
            verifier_ref=verifier_ref,
            payload_sha256=payload_sha256,
        )


class FakeDispatcher:
    def __init__(self) -> None:
        self.policy = CanaryPolicy(allowed_image_refs=[IMAGE_REF])
        self.executions = 0

    def validate(self, operation: str, parameters: Mapping[str, object]) -> None:
        self.policy.validate(operation, parameters)

    def execute(self, operation: str, parameters: Mapping[str, object]) -> dict[str, object]:
        self.validate(operation, parameters)
        self.executions += 1
        return {"operation": operation, "state": "EXECUTED", "target": parameters["name"]}

    def verify(self, operation: str, parameters: Mapping[str, object]) -> dict[str, object]:
        self.validate(operation, parameters)
        return {"verification_state": "PASS", "target": parameters["name"]}


def utc_text(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, tz=UTC).isoformat().replace("+00:00", "Z")


def active_authority(*, scopes: list[str] | None = None) -> dict[str, object]:
    return {
        "schema_id": "W7TP_ACTIVE_TOTAL_FIELD_AUTHORITY_V1",
        "active": True,
        "state": "ACTIVE",
        "authority_id": "authority_ref:total_field_runtime_v2:taiji01:control:ed25519",
        "authority_scope": scopes or sorted(REQUIRED_CONTROL_SCOPES),
        "issued_at": utc_text(NOW - 60),
        "expires_at": utc_text(NOW + 600),
    }


def authority_profile(*, active: bool = True) -> dict[str, object]:
    return {
        "schema_id": "W7TP_ACTIVE_TOTAL_FIELD_AUTHORITY_RUNTIME_PROFILE_V2_CANDIDATE",
        "active": active,
        "authorization_boundary": {"execution_authority": True},
        "node_binding": {
            "authority_runtime_owner": "taiji01",
            "ledger_owner_node": "taiji01",
            "cross_node_authority_allowed": True,
        },
        "signature_verifier": {
            "algorithm": "Ed25519",
            "implementation": "tools.total_field_ed25519_backend:Ed25519DetachedSignatureBackend",
            "trusted_verifier_refs": ["verifier_ref:total_field_runtime_v1"],
        },
    }


def snapshot(
    node_id: str,
    *,
    cpu: int,
    ram: int,
    disk: int,
    gpu_mib: list[int] | None = None,
    engine: str | None = "docker",
) -> dict[str, object]:
    probes: list[dict[str, object]] = []
    if engine:
        probes.append(
            {
                "probe": "container_metadata",
                "state": "OBSERVED",
                "engine": engine,
            }
        )
    return {
        "schema_id": "W7TP_GT_MESH_NODE_SNAPSHOT_V21",
        "node": {"node_id": node_id},
        "resources": {
            "cpu": {"logical_count": cpu},
            "ram": {"available_bytes": ram},
            "disks": [
                {
                    "free_bytes": disk,
                    "observation_state": "OBSERVED_METADATA_ONLY",
                }
            ],
            "gpus": [
                {"memory_total_mib": value, "observation_state": "OBSERVED_METADATA_ONLY"}
                for value in (gpu_mib or [])
            ],
        },
        "containers": [],
        "probe_evidence": probes,
    }


REQUEST = {
    "cpu_count": 2,
    "ram_bytes": 2_000_000_000,
    "disk_bytes": 4_000_000_000,
    "gpu_count": 0,
    "gpu_memory_mib": 0,
    "pids_limit": 64,
    "container_engine": "docker",
}


class TotalFieldControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.signatures = InjectedTestEd25519()
        self.authority = active_authority()
        self.profile = authority_profile()
        self.small = snapshot("taiji02", cpu=4, ram=4_000_000_000, disk=8_000_000_000)
        self.large = snapshot("taiji03", cpu=16, ram=32_000_000_000, disk=64_000_000_000, gpu_mib=[8192])

    def envelope(self, *, now: int = NOW) -> tuple[dict[str, object], dict[str, object]]:
        return plan_task_envelope(
            snapshots=[self.large, self.small],
            resource_request=REQUEST,
            task_id="task-canary-001",
            intent="驗證總場 canary 硬體調度閉環",
            operation="container_run_canary",
            parameters={
                "engine": "docker",
                "name": "w7tp-canary-control-test",
                "image_ref": IMAGE_REF,
                "command": ["python3", "-V"],
            },
            logical_time=1,
            issued_at_epoch=now,
            ttl_seconds=300,
            verifier_ref="verifier_ref:total_field_runtime_v1",
            signer=self.signatures,
            active_authority=self.authority,
            authority_profile=self.profile,
            nonce="1" * 32,
        )

    def test_deterministic_placement_extends_existing_planner(self) -> None:
        first = deterministic_place([self.large, self.small], REQUEST)
        second = deterministic_place([self.small, self.large], REQUEST)
        self.assertEqual(first["selected_node_id"], "taiji02")
        self.assertEqual(first["selected_snapshot_sha256"], second["selected_snapshot_sha256"])
        self.assertIn("PlacementPlanner", str(first["base_planner"]))
        self.assertEqual(first["execution_lease"]["state"], "ISSUED")
        self.assertEqual(
            first["execution_lease"]["state_machine"],
            ["ISSUED", "ACKNOWLEDGED", "RUNNING", "RESULT_CANDIDATE", "ACCEPTED", "EXPIRED", "REJECTED"],
        )
        lease_summary = first["execution_lease"]["human_summary_zh_tw"]
        for label in ("意圖：", "總場決策理由：", "選中節點／容器：", "資源依據：", "實際結果：", "未知／風險："):
            self.assertIn(label, lease_summary)
        self.assertTrue(lease_summary.endswith("不是總場權威、正典或最終決策者。"))
        self.assertIn("總場決策理由", first["human_summary_zh_tw"])

    def test_controller_normalizes_defaulted_resource_limits(self) -> None:
        compact_request = {
            "cpu_count": 2,
            "ram_bytes": 2_000_000_000,
            "disk_bytes": 4_000_000_000,
            "container_engine": "docker",
        }
        _, envelope = plan_task_envelope(
            snapshots=[self.small],
            resource_request=compact_request,
            task_id="task-default-limits",
            intent="驗證資源預設值單一綁定",
            operation="container_run_canary",
            parameters={
                "engine": "docker",
                "name": "w7tp-canary-default-limits",
                "image_ref": IMAGE_REF,
                "command": [],
            },
            logical_time=2,
            issued_at_epoch=NOW,
            ttl_seconds=300,
            verifier_ref="verifier_ref:total_field_runtime_v1",
            signer=self.signatures,
            active_authority=self.authority,
            authority_profile=self.profile,
            nonce="3" * 32,
        )
        d2 = envelope["dimensions"]["D2_STATE"]
        d5 = envelope["dimensions"]["D5_EXECUTION"]
        self.assertEqual(d2["resource_request"], d2["execution_lease"]["resource_request"])
        self.assertEqual(d2["resource_request"], d5["parameters"]["resource_limits"])
        self.assertEqual(d2["resource_request"]["pids_limit"], 128)
        self.assertEqual(d2["resource_request"]["gpu_count"], 0)

    def test_resource_insufficient_holds(self) -> None:
        impossible = {**REQUEST, "ram_bytes": 100_000_000_000}
        with self.assertRaisesRegex(MeshHold, "HOLD_NO_CAPABLE_NODE"):
            deterministic_place([self.small, self.large], impossible)

    def test_authority_rejection(self) -> None:
        _, envelope = self.envelope()
        rejected = copy.deepcopy(envelope)
        rejected["dimensions"]["D8_ENVELOPE_VERIFICATION"]["authority_ref"] = "authority:MSI"
        with self.assertRaisesRegex(MeshHold, "HOLD_TOTAL_FIELD_AUTHORITY_REQUIRED"):
            verify_task_envelope(
                rejected,
                signature_verifier=self.signatures,
                active_authority=self.authority,
                authority_profile=self.profile,
                now_epoch=NOW + 1,
            )

    def test_current_promotion_only_authority_gap_holds(self) -> None:
        current_like = active_authority(scopes=["PROMOTE_ACCEPTED_CANDIDATE"])
        placement = deterministic_place([self.small], REQUEST)
        from total_field_control.authority import build_task_envelope

        envelope = build_task_envelope(
            task_id="task-scope-gap",
            intent="scope gap",
            target_node_id="taiji02",
            selected_snapshot_sha256=str(placement["selected_snapshot_sha256"]),
            operation="container_run_canary",
            parameters={"engine": "docker", "name": "w7tp-canary-gap", "image_ref": IMAGE_REF, "command": []},
            resource_request=REQUEST,
            node_manifest=placement["node_manifest"],
            node_resource_state=placement["node_resource_state"],
            execution_lease=placement["execution_lease"],
            logical_time=1,
            issued_at_epoch=NOW,
            ttl_seconds=300,
            verifier_ref="verifier_ref:total_field_runtime_v1",
            signer=self.signatures,
            active_authority=current_like,
            authority_profile=self.profile,
            nonce="2" * 32,
        )
        with self.assertRaisesRegex(MeshHold, "HOLD_TOTAL_FIELD_CONTROL_SCOPE_MISSING_OR_EXPANDED"):
            verify_task_envelope(
                envelope,
                signature_verifier=self.signatures,
                active_authority=current_like,
                authority_profile=self.profile,
                now_epoch=NOW + 1,
            )

    def test_tamper_and_ttl_hold(self) -> None:
        _, envelope = self.envelope()
        tampered = copy.deepcopy(envelope)
        tampered["dimensions"]["D5_EXECUTION"]["operation"] = "service_stop_canary"
        with self.assertRaisesRegex(MeshHold, "HOLD_TASK_ENVELOPE_HASH_MISMATCH"):
            verify_task_envelope(
                tampered,
                signature_verifier=self.signatures,
                active_authority=self.authority,
                authority_profile=self.profile,
                now_epoch=NOW + 1,
            )
        with self.assertRaisesRegex(MeshHold, "HOLD_TASK_EXPIRED_OR_NOT_YET_VALID"):
            verify_task_envelope(
                envelope,
                signature_verifier=self.signatures,
                active_authority=self.authority,
                authority_profile=self.profile,
                now_epoch=NOW + 300,
            )

    def test_reserve_execute_verify_receipts_and_replay(self) -> None:
        _, envelope = self.envelope()
        dispatcher = FakeDispatcher()
        with tempfile.TemporaryDirectory() as temporary:
            with MeshStorage(Path(temporary) / "runtime") as storage:
                agent = TotalFieldNodeAgent(
                    storage=storage,
                    node_id="taiji02",
                    signature_verifier=self.signatures,
                    dispatcher=dispatcher,
                )
                result = agent.process(
                    envelope,
                    current_snapshot=self.small,
                    active_authority=self.authority,
                    authority_profile=self.profile,
                    now_epoch=NOW + 1,
                )
                self.assertEqual(result["state"], "PASS_TOTAL_FIELD_CANARY_TASK_VERIFIED")
                self.assertIn("意圖：", result["human_summary_zh_tw"])
                self.assertIn("總場決策理由：", result["human_summary_zh_tw"])
                self.assertIn("選中節點／容器：", result["human_summary_zh_tw"])
                self.assertIn("實際結果：", result["human_summary_zh_tw"])
                self.assertIn("未知／風險：", result["human_summary_zh_tw"])
                self.assertTrue(result["human_summary_zh_tw"].endswith("不是總場權威、正典或最終決策者。"))
                self.assertEqual(dispatcher.executions, 1)
                reservations = list(storage.journal.records("total_field_control_reservations"))
                executions = list(storage.journal.records("total_field_control_executions"))
                verifications = list(storage.journal.records("total_field_control_verifications"))
                adi_states = list(storage.journal.records("total_field_control_adi_state"))
                self.assertEqual([len(reservations), len(executions), len(verifications), len(adi_states)], [1, 1, 1, 1])
                for receipt in (*reservations, *executions, *verifications):
                    summary = receipt["human_summary_zh_tw"]
                    for label in ("意圖：", "總場決策理由：", "選中節點／容器：", "資源依據：", "實際結果：", "未知／風險："):
                        self.assertIn(label, summary)
                    self.assertIn("w7tp-canary-control-test", summary)
                    self.assertTrue(summary.endswith("不是總場權威、正典或最終決策者。"))
                self.assertEqual(
                    adi_states[0]["transition"],
                    "ISSUED_TO_ACKNOWLEDGED_TO_RUNNING_TO_RESULT_CANDIDATE_TO_ACCEPTED",
                )
                with self.assertRaisesRegex(MeshHold, "HOLD_CONTROL_TASK_REPLAY"):
                    agent.process(
                        envelope,
                        current_snapshot=self.small,
                        active_authority=self.authority,
                        authority_profile=self.profile,
                        now_epoch=NOW + 2,
                    )
                self.assertEqual(dispatcher.executions, 1)

    def test_policy_never_accepts_formal_service(self) -> None:
        policy = CanaryPolicy(allowed_image_refs=[IMAGE_REF])
        with self.assertRaisesRegex(MeshHold, "HOLD_CANARY_SERVICE_NAME_REQUIRED"):
            policy.validate("service_stop_canary", {"unit": "postgresql.service", "scope": "system"})

    def test_generic_existing_container_capability_exists_but_default_scope_rejects(self) -> None:
        container_id = "b" * 64
        parameters = {
            "engine": "docker",
            "container_id": container_id,
            "current_state_sha256": "c" * 64,
        }
        default_policy = CanaryPolicy(allowed_existing_container_ids=[container_id])
        with self.assertRaisesRegex(MeshHold, "HOLD_MANAGE_EXISTING_CONTAINER_NOT_AUTHORIZED"):
            default_policy.validate("container_stop_existing", parameters)
        explicitly_authorized = CanaryPolicy(
            allowed_existing_container_ids=[container_id],
            manage_existing_scope_authorized=True,
        )
        explicitly_authorized.validate("container_stop_existing", parameters)
        _, envelope = plan_task_envelope(
            snapshots=[self.small],
            resource_request=REQUEST,
            task_id="task-existing-container-scope-gap",
            intent="驗證既有容器能力預設未授權",
            operation="container_stop_existing",
            parameters=parameters,
            logical_time=3,
            issued_at_epoch=NOW,
            ttl_seconds=300,
            verifier_ref="verifier_ref:total_field_runtime_v1",
            signer=self.signatures,
            active_authority=self.authority,
            authority_profile=self.profile,
            nonce="4" * 32,
        )
        with self.assertRaisesRegex(MeshHold, "HOLD_TOTAL_FIELD_CONTROL_SCOPE_MISSING_OR_EXPANDED"):
            verify_task_envelope(
                envelope,
                signature_verifier=self.signatures,
                active_authority=self.authority,
                authority_profile=self.profile,
                now_epoch=NOW + 1,
            )

    def test_container_run_engine_args_cross_bind_resource_limits(self) -> None:
        calls: list[tuple[str, ...]] = []

        def runner(argv: object, timeout_seconds: int) -> RunnerResult:
            del timeout_seconds
            calls.append(tuple(str(item) for item in argv))
            return RunnerResult(0, "d" * 64)

        dispatcher = CanaryActionDispatcher(allowed_image_refs=[IMAGE_REF], runner=runner)
        limits = {
            "cpu_count": 3,
            "ram_bytes": 3_000_000_000,
            "disk_bytes": 4_000_000_000,
            "gpu_count": 1,
            "gpu_memory_mib": 4096,
            "pids_limit": 72,
            "container_engine": "docker",
        }
        dispatcher.execute(
            "container_run_canary",
            {
                "engine": "docker",
                "name": "w7tp-canary-resource-bind",
                "image_ref": IMAGE_REF,
                "command": [],
                "resource_limits": limits,
            },
        )
        argv = calls[0]
        self.assertEqual(argv[argv.index("--cpus") + 1], "3")
        self.assertEqual(argv[argv.index("--memory") + 1], "3000000000")
        self.assertEqual(argv[argv.index("--pids-limit") + 1], "72")
        self.assertEqual(argv[argv.index("--gpus") + 1], "1")


if __name__ == "__main__":
    unittest.main()
