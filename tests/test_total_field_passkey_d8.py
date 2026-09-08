from __future__ import annotations

import unittest

from fido2.utils import websafe_encode

from tools.total_field_passkey_d8 import (
    DEPLOY_RESTART_SCOPE,
    GIT_PUSH_SCOPE,
    PasskeyD8Rejected,
    approval_challenge,
    canonical_json,
    normalized_scopes,
    require_admitted_authenticator,
    require_platform_authenticator,
    sha256,
)


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

    def test_exact_combined_effect_scopes_are_admitted(self) -> None:
        self.assertEqual(
            normalized_scopes([GIT_PUSH_SCOPE, DEPLOY_RESTART_SCOPE]),
            (GIT_PUSH_SCOPE, DEPLOY_RESTART_SCOPE),
        )

    def test_unknown_or_duplicate_effect_scope_is_rejected(self) -> None:
        with self.assertRaisesRegex(PasskeyD8Rejected, "PASSKEY_SCOPE_INVALID"):
            normalized_scopes([GIT_PUSH_SCOPE, GIT_PUSH_SCOPE])
        with self.assertRaisesRegex(PasskeyD8Rejected, "PASSKEY_SCOPE_INVALID"):
            normalized_scopes(["AUTHORIZE_EVERYTHING"])

    def test_platform_authenticator_is_accepted(self) -> None:
        self.assertEqual(require_platform_authenticator({"authenticatorAttachment": "platform"}), "platform")

    def test_external_security_key_is_rejected(self) -> None:
        with self.assertRaisesRegex(PasskeyD8Rejected, "PASSKEY_PLATFORM_AUTHENTICATOR_REQUIRED"):
            require_platform_authenticator({"authenticatorAttachment": "cross-platform"})

    def test_hybrid_phone_is_admitted(self) -> None:
        response = {
            "authenticatorAttachment": "cross-platform",
            "response": {"transports": ["hybrid", "internal"]},
        }
        self.assertEqual(
            require_admitted_authenticator(response, allow_hybrid_mobile=True),
            "cross-platform",
        )

    def test_enrolled_hybrid_phone_assertion_is_admitted(self) -> None:
        response = {"authenticatorAttachment": "cross-platform", "response": {}}
        enrolled = {"transports": ["hybrid", "internal"]}
        self.assertEqual(
            require_admitted_authenticator(response, enrolled, allow_hybrid_mobile=True),
            "cross-platform",
        )

    def test_external_non_hybrid_security_key_is_rejected(self) -> None:
        response = {
            "authenticatorAttachment": "cross-platform",
            "response": {"transports": ["usb"]},
        }
        with self.assertRaisesRegex(PasskeyD8Rejected, "PASSKEY_ADMITTED_AUTHENTICATOR_REQUIRED"):
            require_admitted_authenticator(response, allow_hybrid_mobile=True)


if __name__ == "__main__":
    unittest.main()
