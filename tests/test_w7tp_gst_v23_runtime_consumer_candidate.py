#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONSUMER_PATH = ROOT / "products/eight_dimensional_generative_memory/w7tp_gst_v23_runtime_consumer_candidate.py"
ORIGIN_PATH = ROOT / "products/eight_dimensional_generative_memory/w7tp_origin_cell_generative_v2.py"
CONTRACT_PATH = ROOT / "products/eight_dimensional_generative_memory/w7tp_gst_v23_runtime_consumer_contract.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


consumer = load_module("w7tp_gst_v23_runtime_consumer_candidate", CONSUMER_PATH)
origin = load_module("w7tp_origin_cell_generative_v2_for_consumer_test", ORIGIN_PATH)


class GstV23RuntimeConsumerCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(tempfile.mkdtemp(prefix="test-gst-v23-consumer-"))
        prepared = origin.prepare_workspace(cls.root / "packet-workspace", origin.MIN_DATASET_MIB)
        cls.packet_path = Path(prepared["packet_path"])
        cls.expected_manifest = prepared["target_manifest_sha256"]

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.root, ignore_errors=True)

    def test_binding_inspection_is_v23_and_has_no_runtime_effect(self) -> None:
        before = set(self.root.iterdir())
        result = consumer.inspect_binding()
        after = set(self.root.iterdir())
        self.assertEqual(result["state"], "PASS_GST_V23_RUNTIME_CONSUMER_BINDING_CANDIDATE")
        self.assertEqual(result["founder_current_baseline"], "W7TP_8D_ADI_V2.3")
        self.assertFalse(result["runtime_activated"])
        self.assertEqual(before, after)

    def test_authority_scopes_are_not_substituted(self) -> None:
        contract = consumer.load_contract()
        authority = contract["authority_resolution"]
        self.assertEqual(authority["legacy_v2_1_master_pointer_role"], "STALE_HISTORICAL_COORDINATE_NOT_CURRENT_VERSION_AUTHORITY")
        self.assertEqual(authority["true8d_allnode_router_canonical_role"], "TOPOLOGY_AND_OBSERVATION_SCOPE_NOT_W7TP_VERSION_AUTHORITY")
        self.assertEqual(authority["v2_3_structure_evidence_role"], "STRUCTURE_EVIDENCE_NOT_RUNTIME_ACTIVATION")
        self.assertEqual(authority["runtime_activation_evidence_role"], "SEPARATE_REQUIRED_FORMAL_RECEIPT")

    def test_one_binding_preserves_multi_path_topology(self) -> None:
        contract = consumer.load_contract()
        topology = contract["execution_topology"]
        self.assertEqual(contract["consumer_relation"]["cardinality"], "ONE_EXPLICIT_BINDING_MANY_ALLOWED_RUNTIME_NODES_AND_CARRIERS")
        self.assertEqual(len(topology["allowed_capability_paths"]), 6)
        self.assertEqual(topology["communication_coordinate_source"], "EXISTING_TOTAL_FIELD_MANAGED_BINDING_ONLY")
        self.assertFalse(topology["guessed_port_allowed"])

    def test_isolated_consumer_executes_existing_origin_cell_and_delivers_receipt(self) -> None:
        workspace = self.root / "isolated-consumer-run"
        result = consumer.run_isolated_candidate(self.packet_path, workspace)
        self.assertEqual(result["state"], "PASS_ISOLATED_GST_V23_CONSUMER_RECONSTRUCTION")
        self.assertEqual(result["target_manifest_sha256"], self.expected_manifest)
        self.assertEqual(result["differential_payload_bytes"], 0)
        self.assertEqual(result["transmitted_target_bytes"], 0)
        self.assertTrue(result["candidate_isolated_execution"])
        self.assertFalse(result["runtime_activated"])
        self.assertFalse(result["formal_delivery"])
        self.assertTrue((workspace / "empty_receiver").is_dir())
        self.assertTrue((workspace / "reconstructed").is_dir())

    def test_formal_path_fails_before_workspace_without_valid_founder_activation(self) -> None:
        receipt = self.root / "invalid-activation-receipt.json"
        receipt.write_text(json.dumps({"decision": "ALLOW"}), encoding="utf-8")
        workspace = self.root / "forbidden-formal-run"
        with self.assertRaisesRegex(consumer.ConsumerHold, "HOLD_FOUNDER_ACTIVATION_RECORD_INVALID"):
            consumer.activate_once(self.packet_path, workspace, receipt)
        self.assertFalse(workspace.exists())

    def test_valid_founder_activation_executes_real_reconstruction(self) -> None:
        contract = consumer.load_contract()
        receipt = self.root / "founder-activation-receipt.json"
        receipt.write_text(json.dumps({
            "schema_version": "w7tp-gst-v23-founder-runtime-activation/1",
            "state": "FOUNDER_DIRECT_RUNTIME_ACTIVATION_AUTHORIZED",
            "binding_id": contract["binding_id"],
            "founder_baseline": "W7TP_8D_ADI_V2.3",
            "contract_sha256": consumer.sha256_file(CONTRACT_PATH),
            "activation_scope": "GST_V23_RUNTIME_CONSUMER_BINDING_ONLY",
            "canonical_pointer_change": False,
            "service_restart": False,
            "rollback_operation": contract["rollback"]["operation"],
            "reviewed_commit": "f9776463cc40bf8cb39c57fa0585d14d18c2df84",
            "founder_directive_ref": "CURRENT_SESSION_EXPLICIT_ACTIVATE",
        }), encoding="utf-8")
        result = consumer.activate_once(self.packet_path, self.root / "founder-active-run", receipt)
        self.assertEqual(result["state"], "PASS_FOUNDER_AUTHORIZED_GST_V23_RUNTIME_RECONSTRUCTION")
        self.assertTrue(result["runtime_activated"])
        self.assertTrue(result["founder_authorized_delivery"])
        self.assertFalse(result["formal_delivery"])
        self.assertEqual(result["target_manifest_sha256"], self.expected_manifest)
        self.assertEqual(result["total_field_decision"], "NOT_RUN")

    def test_contract_rejects_legacy_pointer_as_current_authority(self) -> None:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        contract["authority_resolution"]["legacy_v2_1_master_pointer_role"] = "CURRENT_VERSION_AUTHORITY"
        tampered = self.root / "tampered-contract.json"
        tampered.write_text(json.dumps(contract), encoding="utf-8")
        with self.assertRaisesRegex(consumer.ConsumerHold, "HOLD_AUTHORITY_SCOPE_RESOLUTION_INVALID"):
            consumer.load_contract(tampered)

    def test_contract_rejects_differential_or_fallback_semantics(self) -> None:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        contract["consumer_relation"]["differential_transfer_allowed"] = True
        tampered = self.root / "tampered-semantics-contract.json"
        tampered.write_text(json.dumps(contract), encoding="utf-8")
        with self.assertRaisesRegex(consumer.ConsumerHold, "HOLD_FORBIDDEN_CONSUMER_SEMANTICS"):
            consumer.load_contract(tampered)

    def test_rule_code_remains_separate_candidate(self) -> None:
        relation = consumer.load_contract()["consumer_relation"]
        self.assertFalse(relation["received_rule_code_formal_contract"])
        self.assertEqual(relation["received_rule_code_status"], "SEPARATE_CANDIDATE_DISCUSSION_REQUIRED")


if __name__ == "__main__":
    unittest.main()
