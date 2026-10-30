"""Candidate-only regression tests. No Total Field authority is issued here."""
import hashlib
import importlib.util
import json
import runpy
import sys
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / "products/eight_dimensional_generative_memory"
sys.path.insert(0, str(ROOT))
from services import w7tp_gst_v23_runtime as service  # noqa: E402


spec = importlib.util.spec_from_file_location(
    "isolated_consumer", PRODUCT / "w7tp_gst_v23_runtime_consumer_candidate.py",
)
consumer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(consumer)


class D6IdentityGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        codec_path = PRODUCT / "universal_origin_cell_codec_v2.py"
        with patch.object(Path, "write_text", return_value=0):
            cls.fixture = runpy.run_path(str(codec_path), run_name="__main__")
        cls.codec = cls.fixture["UniversalOriginCellDecoder"]

    def hold(self, fn, expected):
        with self.assertRaises(Exception) as raised:
            fn()
        self.assertEqual(getattr(raised.exception, "code", ""), expected)

    def test_exact_source_bytes(self):
        self.assertEqual(
            hashlib.sha256((PRODUCT / "universal_origin_cell_codec_v2.py").read_bytes()).hexdigest(),
            "345af4963feb2fd88c684a96c505aafae63ad46c2c16e5c4dd13722eb3c7a23b",
        )
        self.assertEqual(
            hashlib.sha256((PRODUCT / "w7tp_origin_cell_generative_v2.py").read_bytes()).hexdigest(),
            "5cde10544819f3783c083a229b04569fd054a0cacc5bb981d99708b0e132ce19",
        )

    def test_both_bindings(self):
        result = consumer.inspect_binding()
        self.assertEqual(result["state"], "PASS_GST_V23_RUNTIME_CONSUMER_STATIC_BINDING")

    def test_570_79_bytes_byte_exact(self):
        f = self.fixture
        original = sum(map(len, (f["raw_c1"], f["raw_c2"], f["raw_c3"], f["raw_c4"])))
        self.assertEqual(original, 24658)
        self.assertEqual((len(f["cold"]), len(f["warm"])), (570, 79))
        receipt = consumer.reconstruct_binary_session([f["cold"], f["warm"]])
        self.assertEqual(
            [x["reconstructed_bytes"] for x in receipt["binary_session_outputs"]],
            [original, original],
        )
        target_sha = {
            str(i): hashlib.sha256(f["raw_c" + str(i)]).hexdigest()
            for i in range(1, 5)
        }
        self.assertEqual(
            [x["channels_sha256"] for x in receipt["binary_session_outputs"]],
            [target_sha, target_sha],
        )

    def test_float_and_diff_rejected_before_any_output(self):
        self.hold(
            lambda: consumer.require_discrete_generative_identity(
                {"reconstruction_rules": [{"primitive": "WRITE_PRNG_BYTES", "seed": 1.5}]}
            ),
            "HOLD_FLOAT_PARAMETER_FORBIDDEN",
        )
        self.hold(
            lambda: consumer.require_discrete_generative_identity({"delta": {"at": 1}}),
            "HOLD_DIFF_MASQUERADING_AS_D6_REJECTED",
        )
        self.hold(
            lambda: service.verify_origin_cell_semantic_purity({"seed": 1.5}),
            "HOLD_FLOAT_PARAMETER_FORBIDDEN",
        )
        self.hold(
            lambda: service.verify_origin_cell_semantic_purity({"upserts": []}),
            "HOLD_DIFF_MASQUERADING_AS_D6_REJECTED",
        )

    def test_binary_trailing_bytes_and_warm_without_substrate(self):
        cold, warm = self.fixture["cold"], self.fixture["warm"]
        self.hold(
            lambda: consumer.reconstruct_binary_session([cold + b"x"]),
            "HOLD_TRAILING_GARBAGE_BYTES",
        )
        self.hold(
            lambda: consumer.reconstruct_binary_session([warm]),
            "HOLD_WARM_SESSION_SUBSTRATE_REQUIRED",
        )

    def test_d7_decompression_bomb_rejected(self):
        compressed = zlib.compress(b"x" * 70000)
        packet = b"\x8e\x01" + len(compressed).to_bytes(2, "big") + compressed + b"\x8d\x01\x01\x01"
        self.hold(
            lambda: consumer._preflight_binary_output(
                packet, self.codec(), max_packet=65536,
                max_bundle=65536, max_output=67108864,
            ),
            "HOLD_D7_SUBSTRATE_RESOURCE_LIMIT",
        )

    def test_d7_expanded_output_rejected(self):
        pack = self.fixture["AutoOriginCellEncoder"].pack_bundle({1: [b"x"]}, {1: [0]})
        mux = b"\x8d\x01\x01\x01\x04\x01\xff\xffA"
        packet = b"\x8e\x00" + len(pack).to_bytes(2, "big") + pack + mux
        self.hold(
            lambda: consumer._preflight_binary_output(
                packet, self.codec(), max_packet=65536,
                max_bundle=65536, max_output=1024,
            ),
            "HOLD_D7_RECONSTRUCTION_RESOURCE_LIMIT",
        )

    def test_literal_only_not_misidentified_as_procedural(self):
        pack = self.fixture["AutoOriginCellEncoder"].pack_bundle({1: [b"x"]}, {1: [0]})
        mux = b"\x8d\x01\x01\x01\x06\x00\x01A"
        packet = b"\x8e\x00" + len(pack).to_bytes(2, "big") + pack + mux
        self.hold(
            lambda: consumer._preflight_binary_output(
                packet, self.codec(), max_packet=65536,
                max_bundle=65536, max_output=1024,
            ),
            "HOLD_DIFF_MASQUERADING_AS_D6_REJECTED",
        )

    def test_wrong_codec_binding_hash_rejected(self):
        contract = consumer.load_contract()
        contract["binary_origin_cell_binding"]["source_sha256"] = "0" * 64
        self.hold(
            lambda: consumer.load_binary_origin_cell(contract),
            "HOLD_BINARY_ORIGIN_CELL_SOURCE_HASH_MISMATCH",
        )

    def test_rule_output_resource_budget_rejected(self):
        contract = consumer.load_contract()
        self.hold(
            lambda: consumer.preflight_rule_resource_budget({
                "reconstruction_rules": [{
                    "primitive": "WRITE_PRNG_BYTES", "size": 67108865, "seed": 1,
                }]
            }, contract),
            "HOLD_D7_RECONSTRUCTION_RESOURCE_LIMIT",
        )

    def test_formal_delivery_does_not_bypass_d8(self):
        f = self.fixture
        self.hold(
            lambda: service.deliver_binary_cell_session(
                [f["cold"], f["warm"]], root=ROOT,
                active_binding_path=ROOT / "intentionally_missing_formal_binding.json",
            ),
            "HOLD_GST_RUNTIME_JSON_READ_FAILED",
        )


if __name__ == "__main__":
    unittest.main()
