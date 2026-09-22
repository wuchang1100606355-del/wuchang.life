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
MODULE_PATH = (
    ROOT
    / "products"
    / "eight_dimensional_generative_memory"
    / "w7tp_origin_cell_generative_v2.py"
)
MANIFEST_PATH = (
    ROOT
    / "products"
    / "eight_dimensional_generative_memory"
    / "w7tp_origin_cell_generative_v2_manifest.json"
)

SPEC = importlib.util.spec_from_file_location("w7tp_origin_cell_generative_v2", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to load Origin Cell V2 candidate")
origin_cell = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(origin_cell)


class OriginCellGenerativeV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_root = Path(tempfile.mkdtemp(prefix="test-origin-cell-generative-v2-"))
        cls.base = cls.temp_root / "base"
        cls.expected = cls.temp_root / "expected"
        cls.reconstructed = cls.temp_root / "reconstructed"
        origin_cell.generate_base(cls.base, origin_cell.MIN_DATASET_MIB)
        shutil.copytree(cls.base, cls.expected)
        origin_cell.apply_rule_profile(cls.expected)
        _, cls.base_bytes, cls.base_manifest = origin_cell.file_manifest(cls.base)
        cls.expected_rows, cls.target_bytes, cls.target_manifest = origin_cell.file_manifest(cls.expected)
        cls.packet = origin_cell.build_rule_packet(
            dataset_mib=origin_cell.MIN_DATASET_MIB,
            base_manifest_sha256=cls.base_manifest,
            target_manifest_sha256=cls.target_manifest,
            generator_base_sha256=origin_cell.sha256_file(MODULE_PATH),
        )
        cls.receipt = origin_cell.reconstruct_from_rule_packet(
            cls.packet,
            cls.base,
            cls.reconstructed,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.temp_root, ignore_errors=True)

    def test_packet_is_joint_8d_rule_contract_without_target_bytes(self) -> None:
        field = self.packet["joint_state_field"]
        self.assertTrue(set(origin_cell.DIMENSIONS).issubset(field))
        self.assertEqual(field["D6"]["mode"], "RULE_PROFILE_REFERENCE")
        self.assertEqual(field["D6"]["transmitted_target_bytes"], 0)
        self.assertTrue(field["coupling_rule"])
        self.assertTrue(field["cross_dimension_constraint"])
        self.assertTrue(field["joint_state_transition"])
        self.assertTrue(field["closure_rule"])
        self.assertTrue(field["fail_closed_rule"])
        serialized = origin_cell.canonical_json_bytes(self.packet)
        self.assertLess(len(serialized), 8192)
        self.assertFalse(origin_cell.FORBIDDEN_PACKET_KEYS.intersection(origin_cell._walk_keys(self.packet)))

    def test_rule_generated_reconstruction_matches_complete_target(self) -> None:
        _, rebuilt_bytes, rebuilt_manifest = origin_cell.file_manifest(self.reconstructed)
        self.assertEqual(rebuilt_manifest, self.target_manifest)
        self.assertEqual(rebuilt_bytes, self.target_bytes)
        self.assertEqual(self.receipt["target_files"], len(self.expected_rows))
        self.assertEqual(self.receipt["transmitted_target_bytes"], 0)
        self.assertEqual(self.receipt["differential_payload_bytes"], 0)

    def test_packet_tamper_fails_closed(self) -> None:
        tampered = copy.deepcopy(self.packet)
        tampered["minimum_new_information"]["dataset_mib"] += 8
        with self.assertRaisesRegex(origin_cell.OriginCellHold, "HOLD_PACKET_SELF_HASH_MISMATCH"):
            origin_cell.validate_rule_packet(tampered, MODULE_PATH)

    def test_embedded_payload_key_is_rejected_even_with_valid_self_hash(self) -> None:
        tampered = copy.deepcopy(self.packet)
        tampered["payload"] = "not-allowed"
        tampered["packet_sha256"] = origin_cell.packet_sha256(tampered)
        with self.assertRaisesRegex(
            origin_cell.OriginCellHold,
            "HOLD_DIFFERENTIAL_OR_TARGET_BYTES_FORBIDDEN",
        ):
            origin_cell.validate_rule_packet(tampered, MODULE_PATH)

    def test_wrong_base_manifest_fails_before_output_creation(self) -> None:
        wrong_base = self.temp_root / "wrong-base"
        shutil.copytree(self.base, wrong_base)
        with (wrong_base / "files" / "f00000.bin").open("r+b") as handle:
            handle.seek(0)
            handle.write(b"drift")
        output = self.temp_root / "wrong-base-output"
        with self.assertRaisesRegex(origin_cell.OriginCellHold, "HOLD_BASE_MANIFEST_MISMATCH"):
            origin_cell.reconstruct_from_rule_packet(self.packet, wrong_base, output)
        self.assertFalse(output.exists())

    def test_lineage_manifest_binds_successor_and_preserves_predecessor(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertEqual(manifest["state"], "CANDIDATE_NOT_CANONICAL")
        self.assertEqual(manifest["successor"]["source_sha256"], origin_cell.sha256_file(MODULE_PATH))
        self.assertEqual(
            manifest["predecessor"]["program_sha256"],
            origin_cell.PREDECESSOR_PROGRAM_SHA256,
        )
        self.assertEqual(
            manifest["predecessor"]["classification"],
            "PROVEN_HISTORICAL_DIFFERENTIAL_RECONSTRUCTION",
        )
        self.assertTrue(manifest["predecessor"]["preserved_append_only"])
        self.assertEqual(manifest["mainline_candidate"]["mechanism"], "RULE_GENERATIVE_BASE_ONLY")
        self.assertEqual(manifest["authority"]["total_field_decision"], "NOT_RUN")


if __name__ == "__main__":
    unittest.main()
