from __future__ import annotations

import unittest

from fido2.utils import websafe_encode

from tools.total_field_passkey_d8 import approval_challenge, canonical_json, sha256


class TotalFieldPasskeyD8Tests(unittest.TestCase):
    def test_challenge_is_exact_claim_and_nonce_bound(self) -> None:
        nonce = websafe_encode(b"n" * 32)
        claims = {"scope": "AUTHORIZE_GIT_PUSH", "target_tree": "a" * 40}
        first = approval_challenge(claims, nonce)
        self.assertEqual(first, approval_challenge(dict(reversed(list(claims.items()))), nonce))
        self.assertNotEqual(first, approval_challenge({**claims, "target_tree": "b" * 40}, nonce))
        self.assertNotEqual(first, approval_challenge(claims, websafe_encode(b"m" * 32)))
        self.assertEqual(len(first), 32)

    def test_canonical_payload_is_stable(self) -> None:
        self.assertEqual(canonical_json({"b": 2, "a": 1}), b'{"a":1,"b":2}')
        self.assertEqual(len(sha256(b"evidence")), 64)


if __name__ == "__main__":
    unittest.main()
