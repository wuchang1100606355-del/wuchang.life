from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from products.eight_dimensional_generative_memory import (
    w7tp_receiver_capability_contract_v1 as receiver_contract_mod,
)


ROOT = Path(__file__).resolve().parents[1]
ORIGIN_PATH = (
    ROOT
    / "products/eight_dimensional_generative_memory/"
    "w7tp_origin_cell_gst_universal_v23_candidate.py"
)
CONSUMER_PATH = (
    ROOT
    / "products/eight_dimensional_generative_memory/"
    "w7tp_origin_cell_gst_universal_receiver_candidate.py"
)
CONTRACT_PATH = (
    ROOT
    / "products/eight_dimensional_generative_memory/"
    "w7tp_origin_cell_gst_universal_receiver_contract.json"
)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


origin = load_module("universal_origin_for_gated_test", ORIGIN_PATH)
consumer = load_module("universal_receiver_consumer_test", CONSUMER_PATH)


class UniversalReceiverGatedCandidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(
            tempfile.mkdtemp(
                prefix="w7tp-universal-receiver-gate-",
                dir="/dev/shm",
            )
        )
        self.source = self.root / "source"
        self.source.mkdir()
        (self.source / "nested").mkdir()
        (self.source / "plain.txt").write_bytes(
            b"HELLO W7TP 8D ADI\n" * 3
        )
        (self.source / "nested" / "unicode.txt").write_text(
            "原胞狀態傳輸：未知來源\n",
            encoding="utf-8",
        )
        (self.source / "nested" / "opaque.bin").write_bytes(
            bytes([0, 1, 2, 3, 255, 128, 10, 65, 66, 67])
        )
        self.packet = origin.build_packet_from_tree(
            self.source,
            default_base_id="ASCII26_SYMBOLS_V1",
        )
        self.packet_path = self.root / "packet.json"
        self.packet_path.write_text(
            json.dumps(
                self.packet,
                ensure_ascii=False,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_binding_is_tracked_candidate_and_disabled(self) -> None:
        result = consumer.inspect_binding()
        self.assertEqual(
            result["state"],
            "PASS_UNIVERSAL_RECEIVER_GATED_BINDING_CANDIDATE",
        )
        self.assertEqual(
            result["receiver_match_state"],
            "PASS_UNIVERSAL_EXECUTOR_CAPABILITY_MATCH",
        )
        self.assertFalse(result["runtime_activated"])
        self.assertFalse(result["canonical"])
        self.assertEqual(result["total_field_decision"], "NOT_RUN")

    def test_gate_passes_before_exact_materialization(self) -> None:
        workspace = self.root / "workspace"
        result = consumer.run_isolated_candidate(
            self.packet_path,
            workspace,
        )
        self.assertEqual(
            result["state"],
            "PASS_UNIVERSAL_RECEIVER_GATED_EXACT_RECONSTRUCTION_CANDIDATE",
        )
        self.assertEqual(
            result["receiver_gate_state"],
            "PASS_UNIVERSAL_EXECUTOR_CAPABILITY_MATCH",
        )
        self.assertEqual(
            result["reconstruction_state"],
            "PASS_EXACT_GENERATIVE_STATE_RECONSTRUCTION",
        )
        self.assertGreater(result["raw_material_u_bytes"], 0)
        self.assertFalse(result["difference_analysis_was_transmission"])
        self.assertFalse(result["canonical_runtime_effect"])
        output = Path(result["output_root"])
        for relative in (
            "plain.txt",
            "nested/unicode.txt",
            "nested/opaque.bin",
        ):
            self.assertEqual(
                (self.source / relative).read_bytes(),
                (output / relative).read_bytes(),
            )

    def test_receiver_descriptor_mismatch_holds_before_workspace(self) -> None:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        receiver_contract = copy.deepcopy(
            contract["receiver_capability_contract"]
        )
        receiver_contract["receiver_requirement"]["primitive_binding"][
            "protocol_descriptor_sha256"
        ] = "0" * 64
        receiver_contract["contract_sha256"] = (
            receiver_contract_mod.contract_sha256(receiver_contract)
        )
        contract["receiver_capability_contract"] = receiver_contract
        tampered = self.root / "tampered-receiver-contract.json"
        tampered.write_text(
            json.dumps(contract, ensure_ascii=False),
            encoding="utf-8",
        )
        workspace = self.root / "must-not-exist"
        with self.assertRaisesRegex(
            consumer.UniversalReceiverConsumerHold,
            "HOLD_UNIVERSAL_PROTOCOL_DESCRIPTOR_MISMATCH",
        ):
            consumer.run_isolated_candidate(
                self.packet_path,
                workspace,
                contract_path=tampered,
            )
        self.assertFalse(workspace.exists())

    def test_successor_source_hash_drift_holds_before_workspace(self) -> None:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        contract["universal_successor_binding"][
            "source_sha256"
        ] = "0" * 64
        tampered = self.root / "tampered-source-binding.json"
        tampered.write_text(
            json.dumps(contract, ensure_ascii=False),
            encoding="utf-8",
        )
        workspace = self.root / "must-not-exist"
        with self.assertRaisesRegex(
            consumer.UniversalReceiverConsumerHold,
            "HOLD_UNIVERSAL_SUCCESSOR_SOURCE_HASH_MISMATCH",
        ):
            consumer.run_isolated_candidate(
                self.packet_path,
                workspace,
                contract_path=tampered,
            )
        self.assertFalse(workspace.exists())

    def test_formal_candidate_contract_forbids_raw_bypass(self) -> None:
        contract = consumer.load_contract()
        self.assertFalse(
            contract["governance"][
                "direct_raw_materialization_formal_allowed"
            ]
        )
        self.assertEqual(
            contract["formal_candidate_pipeline"],
            [
                "VALIDATE_PACKET",
                "MATCH_RECEIVER_CAPABILITY",
                "BUILD_RECEIVER_BOUND_ENVELOPE",
                "MATERIALIZE",
                "VERIFY_RECONSTRUCTION_RECEIPT",
            ],
        )


if __name__ == "__main__":
    unittest.main()
