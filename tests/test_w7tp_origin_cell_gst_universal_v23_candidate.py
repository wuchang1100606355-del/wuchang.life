#!/usr/bin/env python3
from __future__ import annotations

import base64
import copy
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "products/eight_dimensional_generative_memory/w7tp_origin_cell_gst_universal_v23_candidate.py"

SPEC = importlib.util.spec_from_file_location(
    "origin_cell_successor",
    MODULE_PATH,
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("unable to load origin-cell successor")
origin = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(origin)


def independent_ai_reference_decode(packet: dict) -> dict[str, bytes]:
    """Independent decoder using only public JSON opcode semantics."""

    result: dict[str, bytes] = {}
    for cell in packet["file_cells"]:
        base_id = cell["base_id"]
        if base_id == "ASCII26_SYMBOLS_V1":
            codes = [9, 10, 13, *range(32, 127)]
        elif base_id == "OCTET256_V1":
            codes = list(range(256))
        else:
            raise AssertionError(base_id)
        atoms = [bytes([code]) for code in codes]
        u = {
            segment["segment_id"]: base64.b64decode(
                segment["base64"]
            )
            for segment in cell["material_u"]
        }
        out = bytearray()
        for op in cell["program"]:
            if op["op"] == "BASE_INDICES":
                for index in op["indices"]:
                    out.extend(atoms[index])
            elif op["op"] == "BASE_RLE":
                out.extend(
                    atoms[op["index"]] * op["count"]
                )
            elif op["op"] == "U_SEGMENT":
                out.extend(u[op["segment_id"]])
            else:
                raise AssertionError(op["op"])
        result[cell["path"]] = bytes(out)
    return result


class OriginCellCanonicalSuccessorTests(unittest.TestCase):
    def test_zero_raw_material_ascii_and_nonzero_wire(self) -> None:
        source = (
            b"ABCDEFGHIJKLMNOPQRSTUVWXYZ\n"
            b"abcdefghijklmnopqrstuvwxyz\n"
            b"0123456789 !@#$%^&*()_+-=[]{};':\",./<>?\n"
        )
        packet = origin.build_packet({"alphabet.txt": source})
        validation = origin.validate_packet(packet)
        self.assertEqual(
            packet["metrics"]["raw_material_u_bytes"],
            0,
        )
        self.assertEqual(
            packet["joint_state_field"]["D6"][
                "raw_material_u_bytes"
            ],
            0,
        )
        self.assertGreater(validation["wire_bytes"], 0)
        self.assertEqual(
            origin.reconstruct_single_file_bytes(packet),
            source,
        )
        self.assertFalse(
            packet["joint_state_field"]["D6"][
                "difference_analysis_transmitted"
            ]
        )

    def test_difference_analysis_is_understanding_not_transport(self) -> None:
        source = b"AAAABBBBCCCC----W7TP"
        views = origin.observe_perspectives(
            source,
            base_id="ASCII26_SYMBOLS_V1",
        )
        analysis = origin.difference_analysis(views)
        self.assertEqual(
            analysis["analysis_role"],
            "UNDERSTANDING_NOT_TRANSMISSION",
        )
        self.assertTrue(
            analysis["relations"][
                "all_material_available_in_base"
            ]
        )
        self.assertTrue(
            analysis["relations"]["has_repeat_structure"]
        )
        packet = origin.build_packet({"state.txt": source})
        serialized = origin.canonical_json_bytes(
            packet
        ).decode("utf-8")
        self.assertNotIn('"delta"', serialized)
        self.assertNotIn('"diff"', serialized)
        self.assertNotIn('"patch"', serialized)
        self.assertEqual(
            packet["metrics"][
                "difference_analysis_payload_bytes"
            ],
            0,
        )
        self.assertEqual(
            packet["metrics"]["differential_payload_bytes"],
            0,
        )

    def test_independent_ai_reference_decoder_reconstructs_exact_state(
        self,
    ) -> None:
        source = (
            b"RULE BASE -> INDEX + POSITION + ORDER\n" * 5
        )
        packet = origin.build_packet({"state.txt": source})
        transported = json.loads(
            origin.canonical_json_bytes(packet).decode("utf-8")
        )
        rebuilt = independent_ai_reference_decode(transported)
        self.assertEqual(rebuilt["state.txt"], source)
        self.assertEqual(
            origin.sha256_bytes(rebuilt["state.txt"]),
            packet["file_cells"][0]["target_sha256"],
        )
        self.assertFalse(
            packet["joint_state_field"]["D8"]["model_authority"]
        )

    def test_uncovered_unicode_becomes_material_u(self) -> None:
        source = "W7TP 原胞狀態傳輸".encode("utf-8")
        packet = origin.build_packet({"state.txt": source})
        self.assertGreater(
            packet["metrics"]["raw_material_u_bytes"],
            0,
        )
        self.assertLess(
            packet["metrics"]["raw_material_u_bytes"],
            len(source),
        )
        self.assertEqual(
            origin.reconstruct_single_file_bytes(packet),
            source,
        )

    def test_octet256_can_reference_every_byte_without_raw_u(
        self,
    ) -> None:
        source = bytes(range(256)) * 3
        packet = origin.build_packet(
            {"binary.bin": source},
            default_base_id="OCTET256_V1",
        )
        self.assertEqual(
            packet["metrics"]["raw_material_u_bytes"],
            0,
        )
        self.assertGreater(
            len(origin.canonical_json_bytes(packet)),
            0,
        )
        self.assertEqual(
            origin.reconstruct_single_file_bytes(packet),
            source,
        )

    def test_packet_tamper_fails_closed(self) -> None:
        packet = origin.build_packet(
            {"state.txt": b"HELLO"}
        )
        tampered = copy.deepcopy(packet)
        tampered["file_cells"][0]["program"][0][
            "indices"
        ][0] += 1
        with self.assertRaisesRegex(
            origin.OriginCellHold,
            "HOLD_PACKET_SELF_HASH_MISMATCH",
        ):
            origin.validate_packet(tampered)

    def test_rule_base_drift_fails_even_after_self_hash_recomputed(
        self,
    ) -> None:
        packet = origin.build_packet(
            {"state.txt": b"HELLO"}
        )
        tampered = copy.deepcopy(packet)
        tampered["material_base_contracts"][0][
            "atom_table_sha256"
        ] = "0" * 64
        tampered["packet_sha256"] = origin.packet_sha256(
            tampered
        )
        with self.assertRaisesRegex(
            origin.OriginCellHold,
            "HOLD_MATERIAL_BASE_DRIFT",
        ):
            origin.validate_packet(tampered)

    def test_path_escape_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            origin.OriginCellHold,
            "HOLD_PATH_ESCAPES_ROOT",
        ):
            origin.build_packet({"../escape.txt": b"NO"})

    def test_multi_file_tree_reconstructs_exactly(self) -> None:
        source = {
            "a.txt": b"AAAAA\n",
            "nested/b.txt": b"BBBBB\n",
            "nested/c.bin": bytes(range(16)),
        }
        packet = origin.build_packet(
            source,
            per_file_base={
                "nested/c.bin": "OCTET256_V1"
            },
        )
        temp = Path(
            tempfile.mkdtemp(
                prefix="origin-cell-successor-test-"
            )
        )
        try:
            output = temp / "out"
            receipt = origin.reconstruct_to_directory(
                packet,
                output,
            )
            self.assertEqual(
                receipt["state"],
                "PASS_EXACT_GENERATIVE_STATE_RECONSTRUCTION",
            )
            for relative, expected in source.items():
                self.assertEqual(
                    (output / relative).read_bytes(),
                    expected,
                )
        finally:
            shutil.rmtree(temp, ignore_errors=True)

    def test_recomputed_d8_authority_escalation_is_rejected(self) -> None:
        packet = origin.build_packet({"state.txt": b"HELLO"})
        tampered = copy.deepcopy(packet)
        tampered["joint_state_field"]["D8"]["model_authority"] = True
        tampered["packet_sha256"] = origin.packet_sha256(tampered)
        with self.assertRaisesRegex(
            origin.OriginCellHold,
            "HOLD_D8_AUTHORITY_ESCALATION",
        ):
            origin.validate_packet(tampered)

    def test_recomputed_execution_policy_escalation_is_rejected(self) -> None:
        packet = origin.build_packet({"state.txt": b"HELLO"})
        tampered = copy.deepcopy(packet)
        tampered["joint_state_field"]["D5"]["canonical_pointer_write"] = True
        tampered["packet_sha256"] = origin.packet_sha256(tampered)
        with self.assertRaisesRegex(
            origin.OriginCellHold,
            "HOLD_EXECUTION_POLICY_ESCALATION",
        ):
            origin.validate_packet(tampered)

    def test_oversized_rle_rejected_before_materialization(self) -> None:
        packet = origin.build_packet({"state.txt": b"AAAA"})
        tampered = copy.deepcopy(packet)
        tampered["file_cells"][0]["program"] = [
            {
                "op": "BASE_RLE",
                "index": tampered["file_cells"][0]["program"][0]["index"],
                "count": origin.MAX_RECONSTRUCTED_BYTES + 1,
            }
        ]
        tampered["packet_sha256"] = origin.packet_sha256(tampered)
        with self.assertRaisesRegex(
            origin.OriginCellHold,
            "HOLD_BASE_RLE_INVALID",
        ):
            origin.validate_packet(tampered)

    def test_selftest_locks_founder_semantics(self) -> None:
        result = origin.selftest()
        self.assertEqual(
            result["state"],
            "PASS_FOUNDER_SEMANTICS_SELFTEST",
        )
        self.assertEqual(
            result["raw_source_material_bytes"],
            0,
        )
        self.assertGreater(result["wire_bytes"], 0)
        self.assertFalse(
            result["difference_analysis_is_transmission"]
        )
        self.assertFalse(
            result["model_specific_reasoning_required"]
        )


if __name__ == "__main__":
    unittest.main()
