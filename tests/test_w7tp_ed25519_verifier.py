#!/usr/bin/env python3
"""Production Ed25519 verifier and Stage B runtime-binding tests."""

from __future__ import annotations

import copy
import hashlib
import unittest
from unittest import mock

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import tools.total_field.w7tp_ed25519_verifier as verifier_module
from tools.total_field.w7tp_ed25519_verifier import (
    DOMAIN_SEPARATOR,
    build_stage_b_signed_bytes,
    validate_stage_b_signature,
    verify_ed25519_signature,
)


PACKET_CANONICAL_ID = "W7TP_GENESIS_STAGE_B_CRYPTO_BOUND_PREIMAGE_V2"
PUBLIC_KEY_REF = "test-only:ephemeral-ed25519-public-key"


class Ed25519VerifierTest(unittest.TestCase):
    def setUp(self) -> None:
        self.private_key = Ed25519PrivateKey.generate()
        self.public_key_bytes = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.fingerprint = hashlib.sha256(self.public_key_bytes).hexdigest()
        self.stage_b = {
            "candidate_only": True,
            "generation": "GENESIS",
            "nested": {"z": 3, "a": 1},
            "unsigned": True,
        }
        self.signed_bytes = build_stage_b_signed_bytes(
            domain_separator=DOMAIN_SEPARATOR,
            packet_canonical_id=PACKET_CANONICAL_ID,
            stage_b_object_without_signature=self.stage_b,
        )
        self.signature_hex = self.private_key.sign(self.signed_bytes).hex()

    def _resolve(self, key_ref: str) -> bytes | None:
        return self.public_key_bytes if key_ref == PUBLIC_KEY_REF else None

    def _validate(self, **overrides: object):
        values: dict[str, object] = {
            "domain_separator": DOMAIN_SEPARATOR,
            "packet_canonical_id": PACKET_CANONICAL_ID,
            "stage_b_object_without_signature": self.stage_b,
            "public_key_ref": PUBLIC_KEY_REF,
            "public_key_resolver": self._resolve,
            "expected_public_key_fingerprint": self.fingerprint,
            "signature_hex": self.signature_hex,
        }
        values.update(overrides)
        return validate_stage_b_signature(**values)  # type: ignore[arg-type]

    def test_01_valid_signature_passes_through_stage_b_entrypoint(self) -> None:
        result = self._validate()
        self.assertTrue(result.valid)
        self.assertEqual(result.reason_code, "PASS_ED25519_SIGNATURE_VALID")
        self.assertEqual(result.public_key_fingerprint, self.fingerprint)

    def test_stage_b_entrypoint_calls_builder_and_verifier(self) -> None:
        with (
            mock.patch.object(verifier_module, "build_stage_b_signed_bytes", wraps=build_stage_b_signed_bytes) as builder_call,
            mock.patch.object(verifier_module, "verify_ed25519_signature", wraps=verify_ed25519_signature) as verifier_call,
        ):
            result = self._validate()
        self.assertTrue(result.valid)
        builder_call.assert_called_once()
        verifier_call.assert_called_once()
        self.assertEqual(
            verifier_call.call_args.kwargs["signed_bytes"], self.signed_bytes
        )

    def test_02_payload_changed_rejects(self) -> None:
        changed = copy.deepcopy(self.stage_b)
        changed["generation"] = "GENESIS_CHANGED"
        result = self._validate(stage_b_object_without_signature=changed)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason_code, "REJECT_ED25519_SIGNATURE_INVALID")

    def test_03_signature_changed_rejects(self) -> None:
        replacement = "0" if self.signature_hex[-1] != "0" else "1"
        changed = self.signature_hex[:-1] + replacement
        result = verify_ed25519_signature(
            public_key_bytes=self.public_key_bytes,
            signature_hex=changed,
            signed_bytes=self.signed_bytes,
        )
        self.assertFalse(result.valid)
        self.assertEqual(result.reason_code, "REJECT_ED25519_SIGNATURE_INVALID")

    def test_04_wrong_public_key_rejects(self) -> None:
        wrong_key = Ed25519PrivateKey.generate().public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        result = verify_ed25519_signature(
            public_key_bytes=wrong_key,
            signature_hex=self.signature_hex,
            signed_bytes=self.signed_bytes,
        )
        self.assertFalse(result.valid)
        self.assertEqual(result.reason_code, "REJECT_ED25519_SIGNATURE_INVALID")

    def test_05_malformed_signature_hex_holds(self) -> None:
        result = verify_ed25519_signature(
            public_key_bytes=self.public_key_bytes,
            signature_hex="zz" * 64,
            signed_bytes=self.signed_bytes,
        )
        self.assertEqual(result.reason_code, "HOLD_ED25519_SIGNATURE_ENCODING_INVALID")

    def test_06_uppercase_signature_hex_holds(self) -> None:
        result = verify_ed25519_signature(
            public_key_bytes=self.public_key_bytes,
            signature_hex="AB" * 64,
            signed_bytes=self.signed_bytes,
        )
        self.assertEqual(result.reason_code, "HOLD_ED25519_SIGNATURE_ENCODING_INVALID")

    def test_07_63_byte_signature_holds(self) -> None:
        result = verify_ed25519_signature(
            public_key_bytes=self.public_key_bytes,
            signature_hex="ab" * 63,
            signed_bytes=self.signed_bytes,
        )
        self.assertEqual(result.reason_code, "HOLD_ED25519_SIGNATURE_LENGTH_INVALID")

    def test_08_65_byte_signature_holds(self) -> None:
        result = verify_ed25519_signature(
            public_key_bytes=self.public_key_bytes,
            signature_hex="ab" * 65,
            signed_bytes=self.signed_bytes,
        )
        self.assertEqual(result.reason_code, "HOLD_ED25519_SIGNATURE_LENGTH_INVALID")

    def test_09_placeholder_signature_blocks(self) -> None:
        for placeholder in ("0" * 128, "a" * 128):
            with self.subTest(placeholder=placeholder[0]):
                result = verify_ed25519_signature(
                    public_key_bytes=self.public_key_bytes,
                    signature_hex=placeholder,
                    signed_bytes=self.signed_bytes,
                )
                self.assertEqual(
                    result.reason_code,
                    "BLOCK_ED25519_PLACEHOLDER_TRUST_MATERIAL",
                )

    def test_10_placeholder_public_key_fingerprint_blocks(self) -> None:
        result = self._validate(expected_public_key_fingerprint="1" * 64)
        self.assertEqual(
            result.reason_code,
            "BLOCK_ED25519_PLACEHOLDER_TRUST_MATERIAL",
        )

    def test_11_signed_byte_reconstruction_is_deterministic(self) -> None:
        second = build_stage_b_signed_bytes(
            domain_separator=DOMAIN_SEPARATOR,
            packet_canonical_id=PACKET_CANONICAL_ID,
            stage_b_object_without_signature=self.stage_b,
        )
        self.assertEqual(second, self.signed_bytes)

    def test_12_object_key_order_does_not_change_signed_bytes(self) -> None:
        reordered = {
            "unsigned": True,
            "nested": {"a": 1, "z": 3},
            "generation": "GENESIS",
            "candidate_only": True,
        }
        rebuilt = build_stage_b_signed_bytes(
            domain_separator=DOMAIN_SEPARATOR,
            packet_canonical_id=PACKET_CANONICAL_ID,
            stage_b_object_without_signature=reordered,
        )
        self.assertEqual(rebuilt, self.signed_bytes)

    def test_13_changed_domain_separator_invalidates_signature(self) -> None:
        result = self._validate(domain_separator="W7TP_TOTAL_FIELD_V2_CHANGED")
        self.assertEqual(result.reason_code, "REJECT_ED25519_SIGNATURE_INVALID")

    def test_14_changed_packet_canonical_id_invalidates_signature(self) -> None:
        result = self._validate(packet_canonical_id=PACKET_CANONICAL_ID + "_CHANGED")
        self.assertEqual(result.reason_code, "REJECT_ED25519_SIGNATURE_INVALID")

    def test_15_changed_stage_b_field_invalidates_signature(self) -> None:
        changed = copy.deepcopy(self.stage_b)
        changed["unsigned"] = False
        result = self._validate(stage_b_object_without_signature=changed)
        self.assertEqual(result.reason_code, "REJECT_ED25519_SIGNATURE_INVALID")

    def test_public_key_wrong_length_holds(self) -> None:
        result = verify_ed25519_signature(
            public_key_bytes=b"short",
            signature_hex=self.signature_hex,
            signed_bytes=self.signed_bytes,
        )
        self.assertEqual(result.reason_code, "HOLD_ED25519_PUBLIC_KEY_INVALID")

    def test_placeholder_public_key_bytes_block(self) -> None:
        result = verify_ed25519_signature(
            public_key_bytes=bytes(32),
            signature_hex=self.signature_hex,
            signed_bytes=self.signed_bytes,
        )
        self.assertEqual(
            result.reason_code,
            "BLOCK_ED25519_PLACEHOLDER_TRUST_MATERIAL",
        )

    def test_fingerprint_mismatch_rejects_before_signature_verification(self) -> None:
        result = self._validate(expected_public_key_fingerprint="2" * 64)
        self.assertEqual(
            result.reason_code,
            "REJECT_ED25519_PUBLIC_KEY_FINGERPRINT_MISMATCH",
        )

    def test_resolver_exception_holds_without_raw_exception(self) -> None:
        def failing_resolver(_: str) -> bytes:
            raise RuntimeError("test-only resolver failure")

        result = self._validate(public_key_resolver=failing_resolver)
        self.assertEqual(result.reason_code, "HOLD_ED25519_PUBLIC_KEY_UNAVAILABLE")

    def test_float_stage_b_value_holds_canonicalization(self) -> None:
        changed = copy.deepcopy(self.stage_b)
        changed["float"] = 1.5
        result = self._validate(stage_b_object_without_signature=changed)
        self.assertEqual(
            result.reason_code,
            "HOLD_SIGNED_BYTES_CANONICALIZATION_UNRESOLVED",
        )

    def test_signature_field_in_stage_b_object_holds(self) -> None:
        changed = copy.deepcopy(self.stage_b)
        changed["signature"] = self.signature_hex
        result = self._validate(stage_b_object_without_signature=changed)
        self.assertEqual(result.reason_code, "HOLD_STAGE_B_SIGNATURE_FIELD_PRESENT")


    def test_empty_and_odd_length_signatures_fail_closed(self) -> None:
        for signature_hex in ("", "a"):
            with self.subTest(signature_hex=signature_hex):
                result = verify_ed25519_signature(
                    public_key_bytes=self.public_key_bytes,
                    signature_hex=signature_hex,
                    signed_bytes=self.signed_bytes,
                )
                self.assertFalse(result.valid)
                self.assertEqual(
                    result.reason_code,
                    "HOLD_ED25519_SIGNATURE_ENCODING_INVALID",
                )

    def test_non_bytes_inputs_fail_closed(self) -> None:
        public_key_result = verify_ed25519_signature(
            public_key_bytes=bytearray(self.public_key_bytes),  # type: ignore[arg-type]
            signature_hex=self.signature_hex,
            signed_bytes=self.signed_bytes,
        )
        signed_bytes_result = verify_ed25519_signature(
            public_key_bytes=self.public_key_bytes,
            signature_hex=self.signature_hex,
            signed_bytes="not-bytes",  # type: ignore[arg-type]
        )
        self.assertFalse(public_key_result.valid)
        self.assertEqual(
            public_key_result.reason_code,
            "HOLD_ED25519_PUBLIC_KEY_INVALID",
        )
        self.assertFalse(signed_bytes_result.valid)
        self.assertEqual(
            signed_bytes_result.reason_code,
            "HOLD_ED25519_SIGNED_BYTES_INVALID",
        )

    def test_cyclic_stage_b_object_holds_without_raw_exception(self) -> None:
        cyclic: dict[str, object] = {}
        cyclic["cycle"] = cyclic
        result = self._validate(stage_b_object_without_signature=cyclic)
        self.assertFalse(result.valid)
        self.assertEqual(
            result.reason_code,
            "HOLD_SIGNED_BYTES_CANONICALIZATION_UNRESOLVED",
        )

if __name__ == "__main__":
    unittest.main()
