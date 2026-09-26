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
        cls.source = cls.temp_root / "source"
        cls.receiver = cls.temp_root / "clean-receiver"
        cls.reconstructed = cls.temp_root / "reconstructed"
        origin_cell.generate_target(cls.source, origin_cell.MIN_DATASET_MIB)
        cls.receiver.mkdir()
        cls.analysis = origin_cell.analyze_source_and_generate_rules(cls.source)
        cls.expected_rows, cls.target_bytes, cls.target_manifest = origin_cell.file_manifest(cls.source)
        cls.packet = origin_cell.build_rule_packet(
            source_analysis=cls.analysis,
            generator_base_sha256=origin_cell.sha256_file(MODULE_PATH),
        )
        cls.receipt = origin_cell.reconstruct_from_rule_packet(
            cls.packet,
            cls.receiver,
            cls.reconstructed,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.temp_root, ignore_errors=True)

    def test_packet_is_joint_8d_rule_contract_without_target_bytes(self) -> None:
        field = self.packet["joint_state_field"]
        self.assertTrue(set(origin_cell.DIMENSIONS).issubset(field))
        self.assertEqual(field["D6"]["mode"], "SOURCE_GENERATED_RULE_BODY")
        self.assertEqual(field["D6"]["transmitted_target_bytes"], 0)
        self.assertTrue(field["coupling_rule"])
        self.assertTrue(field["cross_dimension_constraint"])
        self.assertTrue(field["joint_state_transition"])
        self.assertTrue(field["closure_rule"])
        self.assertTrue(field["fail_closed_rule"])
        serialized = origin_cell.canonical_json_bytes(self.packet)
        self.assertGreater(len(self.packet["reconstruction_rules"]), 0)
        self.assertEqual(
            self.packet["rule_body_sha256"],
            origin_cell.sha256_bytes(origin_cell.canonical_json_bytes(self.packet["reconstruction_rules"])),
        )
        self.assertNotIn("COMPLEX_DATASET_TARGET_RULES_V1", serialized.decode())
        self.assertFalse(origin_cell.FORBIDDEN_PACKET_KEYS.intersection(origin_cell._walk_keys(self.packet)))

    def test_rule_generated_reconstruction_matches_complete_target(self) -> None:
        _, rebuilt_bytes, rebuilt_manifest = origin_cell.file_manifest(self.reconstructed)
        self.assertEqual(rebuilt_manifest, self.target_manifest)
        self.assertEqual(rebuilt_bytes, self.target_bytes)
        self.assertEqual(self.receipt["target_files"], len(self.expected_rows))
        self.assertEqual(self.receipt["transmitted_target_bytes"], 0)
        self.assertEqual(self.receipt["differential_payload_bytes"], 0)
        self.assertEqual(self.receipt["target_preloaded_special_rules"], 0)
        self.assertEqual(self.receipt["target_preloaded_target_data"], 0)
        self.assertEqual(self.receipt["target_preloaded_base_bytes"], 0)
        self.assertEqual(self.receipt["target_preloaded_special_rule_bytes"], 0)
        self.assertEqual(self.receipt["transmitted_rule_literal_bytes"], 0)
        self.assertEqual(self.receipt["full_target_bytes_transmitted"], 0)
        self.assertFalse(self.receipt["hidden_full_transfer"])
        self.assertFalse(self.receipt["previous_state_used"])

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

    def test_base64_hidden_transfer_is_rejected(self) -> None:
        tampered = copy.deepcopy(self.packet)
        tampered["reconstruction_rules"][0]["base64"] = "Ynl0ZXM="
        tampered["rule_body_sha256"] = origin_cell.sha256_bytes(
            origin_cell.canonical_json_bytes(tampered["reconstruction_rules"])
        )
        tampered["joint_state_field"]["D6"]["rule_body_sha256"] = tampered["rule_body_sha256"]
        tampered["packet_sha256"] = origin_cell.packet_sha256(tampered)
        with self.assertRaisesRegex(origin_cell.OriginCellHold, "HOLD_DIFFERENTIAL_OR_TARGET_BYTES_FORBIDDEN"):
            origin_cell.validate_rule_packet(tampered, MODULE_PATH)

    def test_receiver_must_be_clean_room(self) -> None:
        dirty_receiver = self.temp_root / "dirty-receiver"
        dirty_receiver.mkdir()
        (dirty_receiver / "preloaded-target-data").write_text("forbidden")
        output = self.temp_root / "dirty-receiver-output"
        with self.assertRaisesRegex(origin_cell.OriginCellHold, "HOLD_RECEIVER_NOT_CLEAN_ROOM"):
            origin_cell.reconstruct_from_rule_packet(self.packet, dirty_receiver, output)
        self.assertFalse(output.exists())

    def test_removing_required_transmitted_rule_fails(self) -> None:
        tampered = copy.deepcopy(self.packet)
        removed = tampered["reconstruction_rules"].pop(1)
        tampered["execution_order"].remove(removed["id"])
        tampered["rule_body_sha256"] = origin_cell.sha256_bytes(
            origin_cell.canonical_json_bytes(tampered["reconstruction_rules"])
        )
        tampered["joint_state_field"]["D6"]["rule_body_sha256"] = tampered["rule_body_sha256"]
        tampered["packet_sha256"] = origin_cell.packet_sha256(tampered)
        output = self.temp_root / "missing-rule-output"
        with self.assertRaisesRegex(origin_cell.OriginCellHold, "HOLD_FINAL_MANIFEST_MISMATCH"):
            origin_cell.reconstruct_from_rule_packet(tampered, self.receiver, output)

    def test_same_generic_executor_reconstructs_second_dynamic_target(self) -> None:
        second_source = self.temp_root / "second-source"
        second_receiver = self.temp_root / "second-clean-receiver"
        second_output = self.temp_root / "second-reconstructed"
        origin_cell.generate_target(second_source, origin_cell.MIN_DATASET_MIB, variant=7)
        second_receiver.mkdir()
        second_analysis = origin_cell.analyze_source_and_generate_rules(second_source)
        second_packet = origin_cell.build_rule_packet(
            source_analysis=second_analysis,
            generator_base_sha256=origin_cell.sha256_file(MODULE_PATH),
        )
        second_receipt = origin_cell.reconstruct_from_rule_packet(second_packet, second_receiver, second_output)
        _, _, second_source_manifest = origin_cell.file_manifest(second_source)
        self.assertNotEqual(second_source_manifest, self.target_manifest)
        self.assertNotEqual(second_packet["rule_body_sha256"], self.packet["rule_body_sha256"])
        self.assertEqual(
            second_packet["generator_executor"]["implementation_sha256"],
            self.packet["generator_executor"]["implementation_sha256"],
        )
        self.assertEqual(second_receipt["target_manifest_sha256"], second_source_manifest)

    def test_source_analysis_rejects_provenance_not_matching_observed_state(self) -> None:
        source = self.temp_root / "provenance-mismatch-source"
        origin_cell.generate_target(source, origin_cell.MIN_DATASET_MIB, variant=3)
        with (source / "binary" / "random.bin").open("r+b") as handle:
            handle.seek(0)
            handle.write(b"observed-drift")
        with self.assertRaisesRegex(
            origin_cell.OriginCellHold,
            "HOLD_SOURCE_RULES_DO_NOT_RECONSTRUCT_OBSERVED_STATE",
        ):
            origin_cell.analyze_source_and_generate_rules(source)

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
        self.assertEqual(manifest["mainline_candidate"]["mechanism"], "SOURCE_GENERATED_INLINE_RULE_BODY")
        self.assertEqual(manifest["authority"]["total_field_decision"], "NOT_RUN")


if __name__ == "__main__":
    unittest.main()
