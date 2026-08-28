"""Positive and fail-closed vectors for the pure V3 candidate adapter."""

from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path
import struct
import sys
import unittest


MODULE_PATH = Path(__file__).with_name("known_novel_v3.py")
SPEC = importlib.util.spec_from_file_location("known_novel_v3_candidate", MODULE_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import bootstrap guard
    raise RuntimeError("candidate module could not be loaded")
v3 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = v3
SPEC.loader.exec_module(v3)


def packet_object(packet: bytes) -> dict[str, object]:
    value = json.loads(packet)
    if not isinstance(value, dict):
        raise AssertionError("test packet is not an object")
    return value


def rep(pattern: bytes, size: int) -> bytes:
    return (pattern * ((size + len(pattern) - 1) // len(pattern)))[:size]


class ExactW7G3PositiveVectors(unittest.TestCase):
    def test_source_coordinate_is_pinned(self) -> None:
        self.assertEqual(
            v3.SOURCE_SHA256,
            "d9ce00a7656926a57ecbfc1c639c0c53ac12790dba2eec2802e23dd8477d8913",
        )

    def test_all_known_round_trip(self) -> None:
        block_size = 14
        target = b"".join(
            rep(v3.W7G3_TOKEN_TABLE[token_id], block_size) for token_id in range(4)
        )
        wire, known_count, novel_count = v3.encode_w7g3(
            target, block_size=block_size
        )
        rebuilt, decoded_known, decoded_novel = v3.decode_w7g3(wire)
        self.assertEqual(rebuilt, target)
        self.assertEqual((known_count, novel_count), (4, 0))
        self.assertEqual((decoded_known, decoded_novel), (4, 0))

    def test_mixed_fixed_wire_vector_matches_observed_layout(self) -> None:
        block_size = 14
        novel = b"0123456789ABCD"
        target = (
            rep(v3.W7G3_TOKEN_TABLE[0], block_size)
            + novel
            + rep(v3.W7G3_TOKEN_TABLE[3], block_size)
        )
        expected = (
            struct.pack("!4sIIII", b"W7G3", 42, 14, 2, 1)
            + struct.pack("!HB", 0, 0)
            + struct.pack("!HB", 2, 3)
            + struct.pack("!H", 1)
            + novel
        )
        wire, known_count, novel_count = v3.encode_w7g3(
            target, block_size=block_size
        )
        self.assertEqual(wire, expected)
        self.assertEqual((known_count, novel_count), (2, 1))
        self.assertEqual(v3.decode_w7g3(expected), (target, 2, 1))

    def test_all_novel_and_deterministic(self) -> None:
        target = bytes(range(32))
        first = v3.encode_w7g3(target, block_size=8)
        second = v3.encode_w7g3(target, block_size=8)
        self.assertEqual(first, second)
        wire, known_count, novel_count = first
        self.assertEqual((known_count, novel_count), (0, 4))
        self.assertEqual(v3.decode_w7g3(wire)[0], target)

    def test_packet_carries_and_verifies_lookup_contract(self) -> None:
        target = rep(v3.W7G3_TOKEN_TABLE[1], 14) + b"novel-block-01"
        packet = v3.encode_w7g3_packet(target, block_size=14)
        obj = packet_object(packet)
        self.assertEqual(obj["lookup_ref"], v3.W7G3_LOOKUP_REF)
        self.assertEqual(obj["lookup_version"], v3.W7G3_LOOKUP_VERSION)
        self.assertEqual(obj["lookup_sha256"], v3.w7g3_lookup_sha256())
        self.assertEqual(packet, v3.canonical_json_bytes(obj))
        result = v3.decode_packet(packet)
        self.assertEqual(result.state, target)
        self.assertEqual(result.codec_mode, v3.MODE_W7G3_EXACT)
        self.assertEqual((result.known_count, result.novel_count), (1, 1))


class ExactW7G3NegativeVectors(unittest.TestCase):
    def assert_reason(self, expected: str, body: bytes) -> None:
        with self.assertRaisesRegex(v3.KnownNovelV3Error, f"^{expected}$"):
            v3.decode_w7g3(body)

    def test_reachable_decoder_rejections(self) -> None:
        cases = {
            "PACKET_TOO_SMALL": b"",
            "MAGIC_INVALID": struct.pack("!4sIIII", b"NOPE", 1, 1, 0, 1),
            "SIZE_INVALID": struct.pack("!4sIIII", b"W7G3", 0, 1, 0, 0),
            "BLOCK_SIZE_INVALID": struct.pack("!4sIIII", b"W7G3", 1, 0, 0, 1),
            "BLOCK_COUNT_TOO_LARGE": struct.pack(
                "!4sIIII", b"W7G3", 65_536, 1, 0, 65_536
            ),
            "COVERAGE_COUNT_INVALID": struct.pack(
                "!4sIIII", b"W7G3", 2, 1, 0, 1
            ),
            "KNOWN_RECORD_TRUNCATED": struct.pack(
                "!4sIIII", b"W7G3", 1, 1, 1, 0
            ),
            "ADI_TOKEN_NOT_FOUND": struct.pack(
                "!4sIIII", b"W7G3", 1, 1, 1, 0
            )
            + struct.pack("!HB", 0, 255),
            "NOVEL_RECORD_TRUNCATED": struct.pack(
                "!4sIIII", b"W7G3", 1, 1, 0, 1
            )
            + struct.pack("!H", 0),
        }
        for reason, body in cases.items():
            with self.subTest(reason=reason):
                self.assert_reason(reason, body)

    def test_non_divisible_geometry(self) -> None:
        self.assert_reason(
            "BLOCK_SIZE_INVALID",
            struct.pack("!4sIIII", b"W7G3", 2, 3, 0, 0),
        )

    def test_known_coordinate_out_of_range(self) -> None:
        body = struct.pack("!4sIIII", b"W7G3", 1, 1, 1, 0) + struct.pack(
            "!HB", 1, 0
        )
        self.assert_reason("KNOWN_COORDINATE_INVALID", body)

    def test_duplicate_known_coordinate(self) -> None:
        body = (
            struct.pack("!4sIIII", b"W7G3", 2, 1, 2, 0)
            + struct.pack("!HB", 0, 0)
            + struct.pack("!HB", 0, 1)
        )
        self.assert_reason("KNOWN_COORDINATE_INVALID", body)

    def test_novel_coordinate_out_of_range(self) -> None:
        body = (
            struct.pack("!4sIIII", b"W7G3", 1, 1, 0, 1)
            + struct.pack("!H", 1)
            + b"x"
        )
        self.assert_reason("NOVEL_COORDINATE_INVALID", body)

    def test_novel_duplicate_of_known_coordinate(self) -> None:
        body = (
            struct.pack("!4sIIII", b"W7G3", 2, 1, 1, 1)
            + struct.pack("!HB", 0, 0)
            + struct.pack("!H", 0)
            + b"x"
        )
        self.assert_reason("NOVEL_COORDINATE_INVALID", body)

    def test_trailing_bytes(self) -> None:
        wire, _, _ = v3.encode_w7g3(b"abcd", block_size=4)
        self.assert_reason("TRAILING_BYTES", wire + b"x")

    def test_encoder_rejects_invalid_inputs(self) -> None:
        bad_calls = (
            lambda: v3.encode_w7g3("bytes-required", block_size=1),
            lambda: v3.encode_w7g3(b"", block_size=1),
            lambda: v3.encode_w7g3(b"a", block_size=True),
            lambda: v3.encode_w7g3(b"abc", block_size=2),
            lambda: v3.encode_w7g3(b"x" * 65_536, block_size=1),
        )
        for call in bad_calls:
            with self.subTest(call=call):
                with self.assertRaises(v3.KnownNovelV3Error):
                    call()


class PreviousBasePositiveVectors(unittest.TestCase):
    BASE = b"AAAABBBBAAAACCCC"
    TARGET = b"AAAAXXXXCCCCBBBB"

    def test_generalized_wire_reuses_lowest_base_coordinate(self) -> None:
        wire, known_count, novel_count = v3.encode_previous_base_wire(
            self.TARGET,
            previous_base=self.BASE,
            block_size=4,
        )
        self.assertEqual((known_count, novel_count), (3, 1))
        header_size = struct.calcsize("!4sIIII")
        header = struct.unpack_from("!4sIIII", wire, 0)
        self.assertEqual(header, (b"W7B1", 16, 4, 3, 1))
        known = [
            struct.unpack_from("!HH", wire, header_size + offset * 4)
            for offset in range(3)
        ]
        # Target block 0 matches duplicate base blocks 0 and 2; coordinate 0 wins.
        self.assertEqual(known, [(0, 0), (2, 3), (3, 1)])
        self.assertEqual(
            v3.decode_previous_base_wire(wire, previous_base=self.BASE),
            (self.TARGET, 3, 1),
        )

    def test_all_novel_and_deterministic(self) -> None:
        target = b"11112222"
        base = b"AAAABBBB"
        first = v3.encode_previous_base_wire(
            target, previous_base=base, block_size=4
        )
        second = v3.encode_previous_base_wire(
            target, previous_base=base, block_size=4
        )
        self.assertEqual(first, second)
        self.assertEqual(first[1:], (0, 2))

    def test_packet_binds_resolved_previous_base(self) -> None:
        packet = v3.encode_previous_base_packet(
            self.TARGET,
            previous_base=self.BASE,
            block_size=4,
            lookup_ref="w7tp://state/previous/base/demo",
            lookup_version="logical-time-42",
        )
        obj = packet_object(packet)
        self.assertEqual(obj["codec_mode"], v3.MODE_PREVIOUS_BASE)
        self.assertEqual(obj["lookup_ref"], "w7tp://state/previous/base/demo")
        self.assertEqual(obj["lookup_version"], "logical-time-42")
        expected_hash = v3.previous_base_lookup_sha256(
            self.BASE,
            block_size=4,
            lookup_ref="w7tp://state/previous/base/demo",
            lookup_version="logical-time-42",
        )
        self.assertEqual(obj["lookup_sha256"], expected_hash)
        result = v3.decode_packet(packet, previous_base=self.BASE)
        self.assertEqual(result.state, self.TARGET)
        self.assertEqual((result.known_count, result.novel_count), (3, 1))


class PreviousBaseNegativeVectors(unittest.TestCase):
    def test_general_mode_never_accepts_w7g3_magic(self) -> None:
        w7g3_wire, _, _ = v3.encode_w7g3(b"abcd", block_size=4)
        with self.assertRaisesRegex(v3.KnownNovelV3Error, "^MAGIC_INVALID$"):
            v3.decode_previous_base_wire(w7g3_wire, previous_base=b"abcd")

    def test_base_coordinate_out_of_range(self) -> None:
        body = struct.pack("!4sIIII", b"W7B1", 4, 4, 1, 0) + struct.pack(
            "!HH", 0, 1
        )
        with self.assertRaisesRegex(
            v3.KnownNovelV3Error, "^BASE_COORDINATE_INVALID$"
        ):
            v3.decode_previous_base_wire(body, previous_base=b"abcd")

    def test_missing_or_wrong_previous_base_fails_closed(self) -> None:
        packet = v3.encode_previous_base_packet(
            b"AAAAXXXX",
            previous_base=b"AAAABBBB",
            block_size=4,
            lookup_ref="w7tp://state/previous/base/one",
            lookup_version="1",
        )
        with self.assertRaisesRegex(
            v3.KnownNovelV3Error, "^PREVIOUS_BASE_REQUIRED$"
        ):
            v3.decode_packet(packet)
        with self.assertRaisesRegex(
            v3.KnownNovelV3Error, "^LOOKUP_BINDING_INVALID$"
        ):
            v3.decode_packet(packet, previous_base=b"CCCCDDDD")

    def test_lookup_identity_is_required(self) -> None:
        for lookup_ref, lookup_version in (("", "1"), ("ref", ""), (None, "1")):
            with self.subTest(ref=lookup_ref, version=lookup_version):
                with self.assertRaises(v3.KnownNovelV3Error):
                    v3.encode_previous_base_packet(
                        b"abcd",
                        previous_base=b"abcd",
                        block_size=4,
                        lookup_ref=lookup_ref,
                        lookup_version=lookup_version,
                    )


class PacketContractNegativeVectors(unittest.TestCase):
    TARGET = b"abcdefghijklmnop"

    def setUp(self) -> None:
        self.packet = v3.encode_w7g3_packet(self.TARGET, block_size=8)

    def changed(self, key: str, value: object) -> bytes:
        obj = packet_object(self.packet)
        obj[key] = value
        return v3.canonical_json_bytes(obj)

    def assert_changed_reason(self, key: str, value: object, reason: str) -> None:
        with self.assertRaisesRegex(v3.KnownNovelV3Error, f"^{reason}$"):
            v3.decode_packet(self.changed(key, value))

    def test_packet_must_be_canonical_and_exact_shape(self) -> None:
        pretty = json.dumps(packet_object(self.packet), indent=2).encode("utf-8")
        with self.assertRaisesRegex(
            v3.KnownNovelV3Error, "^PACKET_NOT_CANONICAL$"
        ):
            v3.decode_packet(pretty)
        obj = packet_object(self.packet)
        obj["unexpected"] = True
        with self.assertRaisesRegex(v3.KnownNovelV3Error, "^PACKET_SHAPE_INVALID$"):
            v3.decode_packet(v3.canonical_json_bytes(obj))

    def test_schema_version_source_and_mode_bindings(self) -> None:
        vectors = (
            ("schema_id", "wrong", "PACKET_SCHEMA_INVALID"),
            ("packet_version", "99", "PACKET_VERSION_INVALID"),
            ("source_sha256", "0" * 64, "SOURCE_BINDING_INVALID"),
            ("codec_mode", "UNKNOWN", "CODEC_MODE_INVALID"),
            ("codec_version", "wrong", "CODEC_VERSION_INVALID"),
        )
        for key, value, reason in vectors:
            with self.subTest(key=key):
                self.assert_changed_reason(key, value, reason)

    def test_all_three_lookup_coordinates_are_enforced(self) -> None:
        vectors = (
            ("lookup_ref", "w7tp://wrong"),
            ("lookup_version", "wrong"),
            ("lookup_sha256", "0" * 64),
        )
        for key, value in vectors:
            with self.subTest(key=key):
                self.assert_changed_reason(key, value, "LOOKUP_BINDING_INVALID")

    def test_payload_encoding_size_hash_and_base64_are_enforced(self) -> None:
        self.assert_changed_reason("payload_encoding", "hex", "PAYLOAD_ENCODING_INVALID")
        self.assert_changed_reason("payload_bytes", 0, "PAYLOAD_SIZE_INVALID")
        self.assert_changed_reason("payload_sha256", "0" * 64, "PAYLOAD_HASH_INVALID")
        self.assert_changed_reason("payload_b64", "!", "PAYLOAD_INVALID")

    def test_payload_wire_count_and_target_are_enforced(self) -> None:
        obj = packet_object(self.packet)
        wire = bytearray(base64.b64decode(obj["payload_b64"]))
        wire[-1] ^= 1
        obj["payload_b64"] = base64.b64encode(wire).decode("ascii")
        obj["payload_sha256"] = v3.sha256_hex(bytes(wire))
        with self.assertRaisesRegex(v3.KnownNovelV3Error, "^TARGET_HASH_INVALID$"):
            v3.decode_packet(v3.canonical_json_bytes(obj))

        self.assert_changed_reason("known_count", 99, "COUNT_BINDING_INVALID")
        self.assert_changed_reason("target_bytes", 99, "TARGET_SIZE_INVALID")
        self.assert_changed_reason("target_sha256", "0" * 64, "TARGET_HASH_INVALID")

    def test_hash_and_numeric_field_types_are_strict(self) -> None:
        self.assert_changed_reason("target_sha256", "not-a-hash", "PACKET_HASH_FIELD_INVALID")
        self.assert_changed_reason("known_count", True, "PACKET_NUMERIC_FIELD_INVALID")
        self.assert_changed_reason("target_bytes", -1, "PACKET_NUMERIC_FIELD_INVALID")

    def test_invalid_json_and_non_bytes_are_rejected(self) -> None:
        with self.assertRaisesRegex(v3.KnownNovelV3Error, "^PACKET_JSON_INVALID$"):
            v3.decode_packet(b"{")
        with self.assertRaisesRegex(v3.KnownNovelV3Error, "^PACKET_INVALID$"):
            v3.decode_packet("not-bytes")


if __name__ == "__main__":
    unittest.main(verbosity=2)
