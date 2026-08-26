from __future__ import annotations

import ast
import hashlib
import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from w7tp_runtime.gt_packet_v2 import PacketV2
from w7tp_runtime.state_field.controlled_experiment_v1.bridge import (
    BRIDGE_MODES,
    PlacementPlanner,
    apply_delta,
    build_delta,
    execute_bridge,
)
from w7tp_runtime.state_field.controlled_experiment_v1.contracts import (
    ContractError,
    build_candidate_packet,
    canonical_bytes,
    probe_resource_catalog,
    sha256_bytes,
    validate_candidate_packet,
)
from w7tp_runtime.state_field.controlled_experiment_v1.pipeline import (
    RECEIVER_ADAPTER_ID,
    IsolationError,
    SingleCandidateIngress,
    require_isolated_output,
    run_controlled_demo,
    verify_run,
    write_bytes_new,
)


FIXED_NOW = datetime(2026, 8, 26, 7, 0, tzinfo=UTC)
REPO_ROOT = Path(__file__).resolve().parents[1]


class ControlledExperimentContractsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = b"alpha-beta-gamma"
        self.target = b"alpha-DELTA-beta-gamma-tail"
        self.delta = build_delta(self.base, self.target)
        self.catalog = probe_resource_catalog(now=FIXED_NOW)

    def test_resource_catalog_has_required_shape_and_explicit_gpu_state(self) -> None:
        self.assertTrue(self.catalog["candidate_only"])
        resources = self.catalog["resources"]
        kinds = {item["kind"] for item in resources}
        self.assertTrue({"CPU", "RAM", "STORAGE", "GPU_VRAM", "VRAM_SIMULATOR"} <= kinds)
        real_gpu = next(item for item in resources if item["kind"] == "GPU_VRAM")
        self.assertEqual(real_gpu["authority_state"], "NOT_AUTHORIZED")
        simulator = next(item for item in resources if item["kind"] == "VRAM_SIMULATOR")
        self.assertEqual(simulator["evidence_state"], "SIMULATED")
        encoded = canonical_bytes(self.catalog)
        self.assertNotIn(b"PRIVATE KEY", encoded)
        self.assertNotIn(b"client_secret", encoded)

    def test_delta_and_all_bridge_modes_are_byte_exact(self) -> None:
        self.assertEqual(apply_delta(self.base, self.delta), self.target)
        planner = PlacementPlanner(self.catalog["resources"])
        for mode in BRIDGE_MODES:
            placement = planner.choose(mode, now=FIXED_NOW)
            result = execute_bridge(
                mode,
                base=self.base,
                target=self.target,
                delta=self.delta,
                placement=placement,
            )
            self.assertEqual(result.output, self.target)
            self.assertEqual(sha256_bytes(result.output), sha256_bytes(self.target))
        real_gpu = next(item for item in self.catalog["resources"] if item["kind"] == "GPU_VRAM")
        simulated = planner.choose("RECONSTRUCT_GPU_SIMULATED", now=FIXED_NOW)
        self.assertNotEqual(real_gpu["resource_id"], simulated.resource_id)

    def test_delta_hash_mismatch_fails_closed(self) -> None:
        with self.assertRaisesRegex(ContractError, "DELTA_BASE_HASH_HOLD"):
            apply_delta(b"wrong-base", self.delta)

    def test_planner_rejects_expired_revoked_and_unauthorized_resources(self) -> None:
        ram = next(item for item in self.catalog["resources"] if item["kind"] == "RAM")
        expired = {**ram, "lease": {**ram["lease"], "expires_at": "2026-08-26T06:59:59Z"}}
        with self.assertRaisesRegex(ContractError, "PLACEMENT_NO_AUTHORIZED_RESOURCE_HOLD"):
            PlacementPlanner([expired]).choose("FULL_COPY", now=FIXED_NOW)
        revoked = {**ram, "revoke": {**ram["revoke"], "revoked": True}}
        with self.assertRaisesRegex(ContractError, "PLACEMENT_NO_AUTHORIZED_RESOURCE_HOLD"):
            PlacementPlanner([revoked]).choose("FULL_COPY", now=FIXED_NOW)
        unauthorized = {**ram, "authority_state": "NOT_AUTHORIZED"}
        with self.assertRaisesRegex(ContractError, "PLACEMENT_NO_AUTHORIZED_RESOURCE_HOLD"):
            PlacementPlanner([unauthorized]).choose("FULL_COPY", now=FIXED_NOW)

    def test_packet_has_closed_d1_d8_and_rejects_d8_escalation(self) -> None:
        packet = build_candidate_packet(
            run_id="W7TP_CE_8D_TEST",
            task_id="TEST_8D",
            scenario_id="S01",
            sequence=1,
            source_version="0" * 40,
            base=self.base,
            target=self.target,
            delta=self.delta,
            resource_ids=["msi-ram-local"],
            issued_at=FIXED_NOW,
        )
        self.assertEqual(
            set(packet["state_field_8d"]),
            {
                "D1_INTENT",
                "D2_STATE",
                "D3_COORDINATE",
                "D4_EVIDENCE",
                "D5_EXECUTION_OR_POLICY",
                "D6_GENERATIVE_TRANSMISSION",
                "D7_RISK_OR_QUARANTINE",
                "D8_ENVELOPE_OR_AUTHORITY",
            },
        )
        validate_candidate_packet(packet, now=FIXED_NOW)
        packet["state_field_8d"]["D8_ENVELOPE_OR_AUTHORITY"]["candidate_only"] = False
        packet.pop("packet_sha256")
        packet["packet_sha256"] = sha256_bytes(canonical_bytes(packet))
        with self.assertRaisesRegex(ContractError, "PACKET_D8_AUTHORITY_HOLD"):
            validate_candidate_packet(packet, now=FIXED_NOW)


class SingleReceiverTests(unittest.TestCase):
    def _packet(self, sequence: int = 1, issued: datetime = FIXED_NOW) -> dict[str, object]:
        base = b"base"
        target = b"base-plus"
        return build_candidate_packet(
            run_id="W7TP_CE_TEST",
            task_id="TEST",
            scenario_id=f"S{sequence}",
            sequence=sequence,
            source_version="0" * 40,
            base=base,
            target=target,
            delta=build_delta(base, target),
            resource_ids=["msi-ram-local"],
            issued_at=issued,
            ttl_seconds=60,
        )

    def _carrier(self, root: Path, packet: dict[str, object], name: str) -> Path:
        packet_path = root / f"{name}.json"
        write_bytes_new(packet_path, canonical_bytes(packet))
        carrier = root / f"{name}.html"
        run_id = f"W7TP_GTF_{hashlib.sha256(canonical_bytes(packet)).hexdigest()[:32]}"
        PacketV2().compose(packet_path, carrier, run_id, f"{name}.json", intent="DIRECT_TRANSFER_ALLOWED")
        return carrier

    def test_existing_receiver_is_only_ingress_and_rejects_replay_order_expiry(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as directory:
            root = Path(directory)
            ingress = SingleCandidateIngress()
            self.assertEqual(ingress.receiver_adapter_id, RECEIVER_ADAPTER_ID)
            first = self._packet()
            carrier = self._carrier(root, first, "first")
            received, _ = ingress.receive(carrier, root / "receive-1", now=FIXED_NOW)
            self.assertEqual(received, first)
            with self.assertRaisesRegex(ContractError, "RECEIVER_DUPLICATE_PACKET_HOLD"):
                ingress.receive(carrier, root / "receive-replay", now=FIXED_NOW)

            out_of_order_ingress = SingleCandidateIngress()
            second = self._packet(sequence=2)
            second_carrier = self._carrier(root, second, "second")
            with self.assertRaisesRegex(ContractError, "RECEIVER_SEQUENCE_HOLD"):
                out_of_order_ingress.receive(second_carrier, root / "receive-order", now=FIXED_NOW)

            expired_ingress = SingleCandidateIngress()
            expired = self._packet(issued=FIXED_NOW - timedelta(minutes=2))
            expired_carrier = self._carrier(root, expired, "expired")
            with self.assertRaisesRegex(ContractError, "PACKET_LEASE_HOLD"):
                expired_ingress.receive(expired_carrier, root / "receive-expired", now=FIXED_NOW)

    def test_carrier_hash_tamper_fails_before_candidate_processing(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as directory:
            root = Path(directory)
            packet = self._packet()
            carrier = self._carrier(root, packet, "tamper")
            raw = carrier.read_bytes()
            marker = b'"adjudication":"DIRECT_TRANSFER"'
            self.assertIn(marker, raw)
            carrier.write_bytes(raw.replace(marker, b'"adjudication":"W7TP_HYBRID"', 1))
            with self.assertRaisesRegex(ValueError, "PACKET_INTEGRITY_HOLD"):
                SingleCandidateIngress().receive(carrier, root / "receive-tamper", now=FIXED_NOW)


class IsolationAndEndToEndTests(unittest.TestCase):
    def test_isolation_rejects_repository_and_boundary_root(self) -> None:
        with self.assertRaises(IsolationError):
            require_isolated_output(REPO_ROOT / "runtime" / "total_field" / "forbidden")
        with self.assertRaises(IsolationError):
            require_isolated_output(Path("/tmp/w7tp_controlled_experiment_v1"))

    def test_package_has_no_authority_canonical_promotion_or_odoo_imports(self) -> None:
        package = REPO_ROOT / "w7tp_runtime" / "state_field" / "controlled_experiment_v1"
        forbidden = (
            "total_field_authority",
            "canonical_pointer",
            "governed_promotion",
            "Taiji_Odoo",
        )
        for path in sorted(package.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            imports: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
            joined = "\n".join(imports)
            for name in forbidden:
                self.assertNotIn(name, joined, f"{path} imports forbidden {name}")

    def test_core_candidate_has_no_process_or_network_imports(self) -> None:
        package = REPO_ROOT / "w7tp_runtime" / "state_field" / "controlled_experiment_v1"
        core = (
            package / "__init__.py",
            package / "__main__.py",
            package / "bridge.py",
            package / "cli.py",
            package / "contracts.py",
            package / "pipeline.py",
            REPO_ROOT / "tools" / "run_w7tp_controlled_experiment_v1.py",
        )
        forbidden_roots = {"http", "socket", "urllib", "subprocess", "requests", "httpx", "aiohttp"}
        for path in core:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            imported_roots: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported_roots.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported_roots.add(node.module.split(".")[0])
            self.assertFalse(imported_roots & forbidden_roots, f"{path} imports held capability")

    def test_end_to_end_generates_five_append_only_receipts_and_verifies(self) -> None:
        active = REPO_ROOT / "runtime" / "total_field" / "ACTIVE_TOTAL_FIELD_AUTHORITY.json"
        pointer = REPO_ROOT / "runtime" / "total_field" / "master_index" / "ACTIVE_W7TP_CANONICAL_POINTER.json"
        before = (active.read_bytes(), pointer.read_bytes())
        parent = Path("/tmp/w7tp_controlled_experiment_v1")
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="test-parent-", dir=parent) as temporary:
            output = Path(temporary) / "candidate-run"
            summary = run_controlled_demo(output_dir=output, repo_root=REPO_ROOT, now=FIXED_NOW)
            self.assertEqual(summary["state"], "PHASE_B_CANDIDATE_FUNCTIONAL")
            self.assertFalse(summary["ready_for_controlled_demo"])
            self.assertEqual(summary["receiver_adapter"], RECEIVER_ADAPTER_ID)
            self.assertEqual(len(summary["scenarios"]), 5)
            self.assertEqual(len(list((output / "receipts").glob("*.json"))), 5)
            self.assertEqual(verify_run(output)["state"], "PASS")
            html = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn("CANDIDATE", html)
            self.assertIn("SIMULATED", html)
            self.assertIn("NOT_REVIEWED", html)
            self.assertNotIn("canonical 寫入按鈕", html)
        self.assertEqual(before, (active.read_bytes(), pointer.read_bytes()))

if __name__ == "__main__":
    unittest.main()
