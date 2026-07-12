import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from w7tp_runtime.gt_converter import (
    NotGenerativelyReducible,
    pack,
    reconstruct,
    seal,
    verify,
)


class GenerativeTransferConverterTests(unittest.TestCase):
    def test_repeat_byte_recipe(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.bin"
            packet = root / "packet.json"
            source.write_bytes(b"\x00" * 512)

            document = pack(source, packet, run_id="TEST_REPEAT_BYTE")

            self.assertEqual(document["recipe"]["block_hex"], "00")
            self.assertEqual(document["recipe"]["repeat_count"], 512)
            self.assertLess(document["recipe"]["block_size_bytes"], source.stat().st_size)

    def test_repeat_block_end_to_end(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.bin"
            packet = root / "packet.json"
            output = root / "output.bin"
            seal_file = root / "seal.json"
            source.write_bytes(b"W7TP-BLOCK" * 128)

            document = pack(source, packet, run_id="TEST_REPEAT_BLOCK")
            self.assertEqual(document["recipe"]["type"], "repeat_block")
            self.assertEqual(document["recipe"]["repeat_count"], 128)
            reconstruct(packet, output)
            result = verify(packet, output)
            record = seal(packet, output, seal_file, result)

            self.assertEqual(record["verifier_decision"], "PASS")
            self.assertEqual(record["expected_sha256"], record["actual_sha256"])
            self.assertEqual(source.read_bytes(), output.read_bytes())

    def test_non_repeated_input_holds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.bin"
            source.write_bytes(bytes(range(251)) + b"not-periodic")
            with self.assertRaises(NotGenerativelyReducible):
                pack(source, root / "packet.json")
            self.assertFalse((root / "packet.json").exists())

    def test_cli_reports_hold_for_non_reducible_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.bin"
            source.write_bytes(b"unique-data-without-a-period")
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "w7tp_runtime.gt_converter_cli",
                    "pack",
                    str(source),
                    str(root / "packet.json"),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(proc.returncode, 20)
            self.assertIn("STATE=HOLD_NOT_GENERATIVELY_REDUCIBLE", proc.stdout)

    def test_tampered_output_holds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.bin"
            packet = root / "packet.json"
            output = root / "output.bin"
            source.write_bytes(b"abc123" * 64)
            pack(source, packet)
            reconstruct(packet, output)
            output.write_bytes(output.read_bytes() + b"tamper")
            result = verify(packet, output)
            self.assertEqual(result["verifier_decision"], "HOLD")


if __name__ == "__main__":
    unittest.main()
