from __future__ import annotations

import copy
import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

from products.eight_dimensional_generative_memory import (
    w7tp_receiver_capability_contract_v1 as receiver,
)


ROOT = Path(__file__).resolve().parents[1]
SUCCESSOR_PATH = (
    ROOT
    / "products/eight_dimensional_generative_memory/"
    "w7tp_origin_cell_gst_universal_v23_candidate.py"
)


def load_successor():
    spec = importlib.util.spec_from_file_location(
        "origin_cell_successor_for_receiver_test",
        SUCCESSOR_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


origin = load_successor()


def universal_contract():
    descriptor_sha = origin.sha256_bytes(
        origin.canonical_json_bytes(origin.protocol_descriptor())
    )
    return receiver.build_universal_executor_contract(
        executor_contract=origin.EXECUTOR_CONTRACT,
        implementation_sha256=receiver.sha256_file(SUCCESSOR_PATH),
        protocol_descriptor_sha256=descriptor_sha,
        material_base_contracts=[
            origin.material_base_contract("ASCII26_SYMBOLS_V1"),
            origin.material_base_contract("OCTET256_V1"),
        ],
        max_reconstructed_bytes=origin.MAX_RECONSTRUCTED_BYTES,
    )


def observed_capability():
    contract = universal_contract()
    return copy.deepcopy(
        contract["receiver_requirement"]["primitive_binding"]
    )


class ReceiverBoundAutoCellizerTests(unittest.TestCase):
    def test_current_universal_executor_matches_contract(self) -> None:
        contract = universal_contract()
        result = receiver.match_universal_executor_capability(
            contract,
            observed_capability(),
        )
        self.assertEqual(
            result["state"],
            "PASS_UNIVERSAL_EXECUTOR_CAPABILITY_MATCH",
        )
        self.assertEqual(result["equivalence_level"], "BYTE_EXACT")

    def test_protocol_descriptor_drift_fails_closed(self) -> None:
        contract = universal_contract()
        observed = observed_capability()
        observed["protocol_descriptor_sha256"] = "0" * 64
        with self.assertRaisesRegex(
            receiver.ReceiverCapabilityHold,
            "HOLD_UNIVERSAL_PROTOCOL_DESCRIPTOR_MISMATCH",
        ):
            receiver.match_universal_executor_capability(
                contract,
                observed,
            )

    def test_unknown_tree_auto_cellizes_with_u_fallback_and_exact_rebuild(
        self,
    ) -> None:
        source_root = Path(
            tempfile.mkdtemp(prefix="w7tp-auto-cell-source-", dir="/dev/shm")
        )
        work_root = Path(
            tempfile.mkdtemp(prefix="w7tp-auto-cell-work-", dir="/dev/shm")
        )
        try:
            (source_root / "nested").mkdir()
            (source_root / "plain.txt").write_bytes(
                b"HELLO W7TP 8D ADI\n" * 3
            )
            (source_root / "nested" / "unicode.txt").write_text(
                "原胞狀態傳輸：未知來源\n",
                encoding="utf-8",
            )
            (source_root / "nested" / "opaque.bin").write_bytes(
                bytes([0, 1, 2, 3, 255, 128, 10, 65, 66, 67])
            )

            packet = origin.build_packet_from_tree(
                source_root,
                default_base_id="ASCII26_SYMBOLS_V1",
            )
            self.assertGreater(
                packet["metrics"]["raw_material_u_bytes"],
                0,
            )
            self.assertLess(
                packet["metrics"]["raw_material_u_bytes"],
                packet["metrics"]["target_fact_bytes"],
            )
            self.assertEqual(
                packet["metrics"]["differential_payload_bytes"],
                0,
            )
            self.assertEqual(
                packet["metrics"]["difference_analysis_payload_bytes"],
                0,
            )

            contract = universal_contract()
            envelope = receiver.build_universal_receiver_bound_envelope(
                packet,
                contract,
            )
            self.assertFalse(envelope["authority"]["canonical"])
            self.assertFalse(
                envelope["authority"]["execution_authorized"]
            )

            output = work_root / "rebuilt"
            receipt = origin.reconstruct_to_directory(packet, output)
            self.assertEqual(
                receipt["state"],
                "PASS_EXACT_GENERATIVE_STATE_RECONSTRUCTION",
            )
            for path in (
                "plain.txt",
                "nested/unicode.txt",
                "nested/opaque.bin",
            ):
                self.assertEqual(
                    (source_root / path).read_bytes(),
                    (output / path).read_bytes(),
                )
        finally:
            shutil.rmtree(source_root, ignore_errors=True)
            shutil.rmtree(work_root, ignore_errors=True)

    def test_receiver_bound_envelope_rejects_descriptor_drift(self) -> None:
        contract = universal_contract()
        packet = origin.build_packet({"unknown.bin": bytes(range(32))})
        packet["protocol_descriptor_sha256"] = "0" * 64
        packet["packet_sha256"] = origin.packet_sha256(packet)
        with self.assertRaisesRegex(
            receiver.ReceiverCapabilityHold,
            "HOLD_UNIVERSAL_PACKET_PROTOCOL_DESCRIPTOR_MISMATCH",
        ):
            receiver.build_universal_receiver_bound_envelope(
                packet,
                contract,
            )


if __name__ == "__main__":
    unittest.main()
