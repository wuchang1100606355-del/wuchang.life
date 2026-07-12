import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import w7tp_runtime.gt_converter as converter


PRODUCT_REDTEAM_CASES = [
    "reject_duplicate_json_keys",
    "reject_bool_as_repeat_count",
    "reject_unknown_required_fields",
    "reject_packet_over_size_limit",
    "reject_deeply_nested_json",
    "reject_log_injection_value",
    "reject_windows_reserved_output_name",
    "reject_case_insensitive_output_collision",
    "reject_concurrent_output_race",
    "reject_stale_or_forged_lock",
    "reject_partial_temp_as_completed_output",
    "hold_unsigned_packet_authenticity",
    "pass_chunked_large_reconstruction",
    "pass_cross_platform_deterministic_bytes",
    "pass_safe_canonical_seal_report",
]


class ProductGTConverterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "source.bin"
        self.packet = self.root / "sample.w7tp.json"
        self.outputs = self.root / "output"
        self.outputs.mkdir()
        self.source.write_bytes(b"W7TP-PRODUCT-BLOCK" * 8192)
        self.core = converter.GTConverter()

    def tearDown(self):
        self.temporary.cleanup()

    def pack(self, target="result.bin"):
        return self.core.pack(self.source, self.packet, run_id="PRODUCT_TEST", target_relative_path=target)

    def document(self):
        return json.loads(self.packet.read_text())

    def write(self, document, rehash=True):
        if rehash:
            converter._set_packet_hash(document)
        self.packet.write_bytes(converter._canonical_bytes(document) + b"\n")

    def test_reject_duplicate_json_keys(self):
        self.packet.write_text('{"protocol":"W7TP-GTF","protocol":"evil"}\n')
        with self.assertRaisesRegex(converter.ConverterHold, "DUPLICATE_JSON_KEY"):
            self.core.inspect(self.packet)

    def test_reject_bool_as_repeat_count(self):
        self.pack(); doc = self.document(); doc["recipe"]["repeat_count"] = True; self.write(doc)
        with self.assertRaisesRegex(converter.ConverterHold, "INVALID_REPEAT_COUNT"):
            self.core.inspect(self.packet)

    def test_reject_unknown_required_fields(self):
        self.pack(); doc = self.document(); doc["unexpected"] = 1; self.write(doc)
        with self.assertRaisesRegex(converter.ConverterHold, "UNKNOWN_OR_MISSING_FIELDS"):
            self.core.inspect(self.packet)

    def test_reject_packet_over_size_limit(self):
        tiny = converter.GTConverter(converter.ConverterPolicy(max_packet_bytes=32))
        self.packet.write_bytes(b"x" * 33)
        with self.assertRaisesRegex(converter.ConverterHold, "PACKET_SIZE_LIMIT"):
            tiny.inspect(self.packet)

    def test_reject_deeply_nested_json(self):
        value = {}; cursor = value
        for _ in range(converter.MAX_JSON_DEPTH + 2):
            cursor["x"] = {}; cursor = cursor["x"]
        self.packet.write_bytes(converter._canonical_bytes(value) + b"\n")
        with self.assertRaisesRegex(converter.ConverterHold, "JSON_DEPTH_EXCEEDED"):
            self.core.inspect(self.packet)

    def test_reject_log_injection_value(self):
        with self.assertRaisesRegex(converter.ConverterHold, "UNSAFE_RUN_ID"):
            self.core.pack(self.source, self.packet, run_id="OK\nSTATE=PASS")

    def test_reject_windows_reserved_output_name(self):
        with self.assertRaisesRegex(converter.ConverterBlock, "WINDOWS_RESERVED_NAME"):
            self.core.pack(self.source, self.packet, target_relative_path="CON.txt")

    def test_reject_case_insensitive_output_collision(self):
        self.pack("Result.bin"); (self.outputs / "result.BIN").write_bytes(b"existing")
        with self.assertRaisesRegex(converter.ConverterBlock, "CASE_INSENSITIVE_COLLISION|OUTPUT_EXISTS"):
            self.core.reconstruct(self.packet, self.outputs)

    def test_reject_concurrent_output_race(self):
        self.pack(); lock = self.outputs / ".result.bin.w7tp.lock"; lock.write_text("other")
        with self.assertRaisesRegex(converter.ConverterBlock, "OUTPUT_LOCKED"):
            self.core.reconstruct(self.packet, self.outputs)

    def test_reject_stale_or_forged_lock(self):
        self.pack(); lock = self.outputs / ".result.bin.w7tp.lock"; lock.write_text("forged\nSTATE=PASS")
        with self.assertRaisesRegex(converter.ConverterBlock, "OUTPUT_LOCKED"):
            self.core.reconstruct(self.packet, self.outputs)
        self.assertEqual(lock.read_text(), "forged\nSTATE=PASS")

    def test_reject_partial_temp_as_completed_output(self):
        self.pack(); partial = self.outputs / ".w7tp-gtf-partial.tmp"; partial.write_bytes(b"partial")
        result = self.core.reconstruct(self.packet, self.outputs)
        self.assertNotEqual(result.output_path, partial)
        self.assertEqual(partial.read_bytes(), b"partial")

    def test_hold_unsigned_packet_authenticity(self):
        packed = self.pack(); rebuilt = self.core.reconstruct(self.packet, self.outputs)
        checked = self.core.verify(self.packet, rebuilt.output_path)
        self.assertEqual(packed.authenticity, checked.authenticity, "UNVERIFIED")

    def test_pass_chunked_large_reconstruction(self):
        self.source.write_bytes(b"0123456789ABCDEF" * 131072)
        self.pack(); result = self.core.reconstruct(self.packet, self.outputs)
        self.assertEqual(result.actual_sha256, hashlib.sha256(self.source.read_bytes()).hexdigest())

    def test_pass_cross_platform_deterministic_bytes(self):
        self.pack(); result = self.core.reconstruct(self.packet, self.outputs)
        self.assertEqual(result.output_path.read_bytes(), self.source.read_bytes())

    def test_pass_safe_canonical_seal_report(self):
        self.pack(); rebuilt = self.core.reconstruct(self.packet, self.outputs)
        checked = self.core.verify(self.packet, rebuilt.output_path); report = self.root / "report.json"
        self.core.seal(checked, report); raw = report.read_bytes(); doc = json.loads(raw)
        self.assertEqual(raw, converter._canonical_bytes(doc) + b"\n")
        self.assertNotIn(str(self.root), raw.decode())
        self.assertNotIn("block_hex", doc)
        self.assertEqual(doc["authenticity"], "UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
