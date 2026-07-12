import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import w7tp_runtime.gt_converter as converter


REDTEAM_CASES = [
    "pass_repeat_block_reconstructs_exact_bytes",
    "hold_full_source_disguised_as_single_block",
    "hold_reduction_ratio_below_16x",
    "hold_repeat_count_zero_or_negative",
    "hold_repeat_count_overflow",
    "hold_output_size_limit_exceeded",
    "hold_invalid_or_odd_block_hex",
    "hold_unknown_protocol_or_version",
    "hold_unknown_recipe_type",
    "hold_tampered_recipe",
    "hold_tampered_expected_sha256",
    "hold_existing_output_without_overwrite",
    "hold_absolute_path",
    "hold_parent_path_traversal",
    "hold_symlink_escape",
    "hold_nonreducible_random_input",
    "pass_integrity_but_authenticity_unverified",
]


class GenerativeTransferConverterRedTeamTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "source.bin"
        self.packet = self.root / "packet.json"
        self.output_root = self.root / "outputs"
        self.output_root.mkdir()
        self.source.write_bytes(b"W7TP-DETERMINISTIC-BLOCK\n" * 4096)

    def tearDown(self):
        self.temporary.cleanup()

    def _pack(self, target="result.bin"):
        return converter.pack(
            self.source,
            self.packet,
            run_id="REDTEAM_TEST",
            target_relative_path=target,
        )

    def _read_packet(self):
        return json.loads(self.packet.read_text())

    def _write_packet(self, packet, *, rehash=True):
        if rehash:
            converter._set_packet_hash(packet)
        self.packet.write_bytes(converter._canonical_bytes(packet) + b"\n")

    def test_pass_repeat_block_reconstructs_exact_bytes(self):
        self._pack()
        result = converter.reconstruct(self.packet, self.output_root)
        verification = converter.verify(self.packet, result["output_path"])
        self.assertEqual(verification["verifier_decision"], "PASS")
        self.assertEqual(self.source.read_bytes(), Path(result["output_path"]).read_bytes())

    def test_hold_full_source_disguised_as_single_block(self):
        self._pack()
        packet = self._read_packet()
        data = self.source.read_bytes()
        packet["recipe"].update(
            block_hex=data.hex(), block_size_bytes=len(data), repeat_count=1, output_size_bytes=len(data)
        )
        self._write_packet(packet)
        with self.assertRaises(converter.NotGenerativelyReducible):
            converter.load_packet(self.packet)

    def test_hold_reduction_ratio_below_16x(self):
        self._pack()
        packet = self._read_packet()
        block = b"small-non-product-block"
        data = block * 2
        digest = hashlib.sha256(data).hexdigest()
        packet["source"].update(size_bytes=len(data), sha256=digest)
        packet["recipe"].update(
            block_hex=block.hex(), block_size_bytes=len(block), repeat_count=2, output_size_bytes=len(data)
        )
        packet["verification"]["expected_sha256"] = digest
        self._write_packet(packet)
        with self.assertRaises(converter.NotGenerativelyReducible):
            converter.load_packet(self.packet)

    def test_hold_repeat_count_zero_or_negative(self):
        for count in (0, -1):
            with self.subTest(count=count):
                self._pack()
                packet = self._read_packet()
                packet["recipe"]["repeat_count"] = count
                packet["recipe"]["output_size_bytes"] = packet["recipe"]["block_size_bytes"] * count
                packet["source"]["size_bytes"] = packet["recipe"]["output_size_bytes"]
                self._write_packet(packet)
                with self.assertRaises(converter.NotGenerativelyReducible):
                    converter.load_packet(self.packet)
                self.packet.unlink()

    def test_hold_repeat_count_overflow(self):
        self._pack()
        packet = self._read_packet()
        count = converter.MAX_REPEAT_COUNT + 1
        packet["recipe"].update(repeat_count=count, output_size_bytes=count)
        packet["source"]["size_bytes"] = count
        self._write_packet(packet)
        with self.assertRaises(converter.NotGenerativelyReducible):
            converter.load_packet(self.packet)

    def test_hold_output_size_limit_exceeded(self):
        self._pack()
        packet = self._read_packet()
        block = b"X" * 1024
        count = converter.MAX_OUTPUT_BYTES // len(block) + 1
        size = len(block) * count
        packet["recipe"].update(
            block_hex=block.hex(), block_size_bytes=len(block), repeat_count=count, output_size_bytes=size
        )
        packet["source"]["size_bytes"] = size
        self._write_packet(packet)
        with self.assertRaises(converter.ConverterHold):
            converter.load_packet(self.packet)

    def test_hold_invalid_or_odd_block_hex(self):
        for value in ("0", "0g", "00 00", " 00", ""):
            with self.subTest(value=value):
                self._pack()
                packet = self._read_packet()
                packet["recipe"]["block_hex"] = value
                self._write_packet(packet)
                with self.assertRaises(converter.ConverterHold):
                    converter.load_packet(self.packet)
                self.packet.unlink()

    def test_hold_unknown_protocol_or_version(self):
        for field, value in (("protocol", "OTHER"), ("protocol_version", "9.9.9")):
            with self.subTest(field=field):
                self._pack()
                packet = self._read_packet()
                packet[field] = value
                self._write_packet(packet)
                with self.assertRaises(converter.ConverterHold):
                    converter.load_packet(self.packet)
                self.packet.unlink()

    def test_hold_unknown_recipe_type(self):
        self._pack()
        packet = self._read_packet()
        packet["recipe"]["type"] = "copy_file"
        self._write_packet(packet)
        with self.assertRaises(converter.ConverterHold):
            converter.load_packet(self.packet)

    def test_hold_tampered_recipe(self):
        self._pack()
        packet = self._read_packet()
        packet["recipe"]["repeat_count"] += 1
        self._write_packet(packet, rehash=False)
        with self.assertRaisesRegex(converter.ConverterHold, "canonical packet hash mismatch"):
            converter.load_packet(self.packet)

    def test_hold_noncanonical_packet_bytes(self):
        self._pack()
        self.packet.write_bytes(self.packet.read_bytes() + b" ")
        with self.assertRaisesRegex(converter.ConverterHold, "not canonical JSON"):
            converter.load_packet(self.packet)

    def test_hold_tampered_expected_sha256(self):
        self._pack()
        packet = self._read_packet()
        forged = "0" * 64
        packet["source"]["sha256"] = forged
        packet["verification"]["expected_sha256"] = forged
        self._write_packet(packet)
        with self.assertRaisesRegex(converter.ConverterHold, "reconstructed SHA-256 mismatch"):
            converter.reconstruct(self.packet, self.output_root)
        self.assertFalse((self.output_root / "result.bin").exists())
        self.assertEqual(list(self.output_root.iterdir()), [])

    def test_hold_existing_output_without_overwrite(self):
        self._pack()
        output = self.output_root / "result.bin"
        output.write_bytes(b"existing")
        with self.assertRaisesRegex(converter.ConverterHold, "will not be overwritten"):
            converter.reconstruct(self.packet, self.output_root)
        self.assertEqual(output.read_bytes(), b"existing")

    def test_hold_atomic_publish_race_without_overwrite(self):
        self._pack()
        output = self.output_root / "result.bin"

        def competing_link(_source, destination, **_kwargs):
            Path(destination).write_bytes(b"competitor")
            raise FileExistsError(destination)

        with mock.patch("os.link", side_effect=competing_link):
            with self.assertRaisesRegex(converter.ConverterHold, "will not be overwritten"):
                converter.reconstruct(self.packet, self.output_root)
        self.assertEqual(output.read_bytes(), b"competitor")
        self.assertFalse(any(path.name.startswith(".w7tp-gtf-") for path in self.output_root.iterdir()))

    def test_hold_absolute_path(self):
        self._pack()
        packet = self._read_packet()
        for target in ("/tmp/escape.bin", "C:\\escape.bin"):
            with self.subTest(target=target):
                packet["reconstruction_target"]["relative_path"] = target
                self._write_packet(packet)
                with self.assertRaises(converter.ConverterHold):
                    converter.load_packet(self.packet)

    def test_hold_parent_path_traversal(self):
        self._pack()
        packet = self._read_packet()
        packet["reconstruction_target"]["relative_path"] = "../escape.bin"
        self._write_packet(packet)
        with self.assertRaises(converter.ConverterHold):
            converter.load_packet(self.packet)

    def test_hold_symlink_escape(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.output_root / "link").symlink_to(outside, target_is_directory=True)
        self._pack(target="link/escape.bin")
        with self.assertRaisesRegex(converter.ConverterHold, "escaped output root|symlink"):
            converter.reconstruct(self.packet, self.output_root)
        self.assertEqual(list(outside.iterdir()), [])

    def test_hold_nonreducible_random_input(self):
        self.source.write_bytes(bytes(range(256)) + b"non-periodic-tail")
        with self.assertRaises(converter.NotGenerativelyReducible):
            converter.pack(self.source, self.packet)
        self.assertFalse(self.packet.exists())

    def test_pass_integrity_but_authenticity_unverified(self):
        packet = self._pack()
        result = converter.reconstruct(self.packet, self.output_root)
        verification = converter.verify(self.packet, result["output_path"])
        self.assertEqual(packet["authenticity"], "UNVERIFIED")
        self.assertEqual(verification["integrity"], "PASS")
        self.assertEqual(verification["authenticity"], "UNVERIFIED")
        self.assertNotIn("AUTHENTICITY_PASS", json.dumps(verification))

    def test_output_limit_checked_before_materialization(self):
        self._pack()
        packet = self._read_packet()
        packet["recipe"]["output_size_bytes"] = converter.MAX_OUTPUT_BYTES + 1
        packet["source"]["size_bytes"] = converter.MAX_OUTPUT_BYTES + 1
        self._write_packet(packet)
        with mock.patch("tempfile.NamedTemporaryFile") as temporary:
            with self.assertRaises(converter.ConverterHold):
                converter.reconstruct(self.packet, self.output_root)
            temporary.assert_not_called()


if __name__ == "__main__":
    unittest.main()
