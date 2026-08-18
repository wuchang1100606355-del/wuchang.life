#!/usr/bin/env python3
"""W7TP 會員自然人身分佐證候選測試。"""

from __future__ import annotations

import unittest

from tools.total_field.w7tp_member_natural_person_corroboration_candidate import (
    HOLD_CONFLICT,
    PASS_STATE,
    build_google_ui_intent,
    evaluate_candidate,
)


A = "a" * 64
B = "b" * 64
C = "c" * 64
D = "d" * 64


def base_request() -> dict:
    return {
        "member_ref": "member_ref:founder",
        "explicit_human_confirmation": True,
        "human_confirmation_ref":
            "human_confirmation_ref:founder-natural-person-v1",
        "anchor_nonce_sha256": A,
        "google_corroboration": None,
        "existing_google_subject_sha256": None,
        "current_epoch": 1000,
        "fresh_auth_seconds": 300,
    }


def google_evidence(subject: str = B) -> dict:
    return {
        "verification_state": "PASS_TRUSTED_IDENTITY_PROJECTION",
        "provider_ref": "provider_ref:google",
        "provider_subject_sha256": subject,
        "identity_projection_ref":
            "identity_projection_ref:sha256:" + C,
        "identity_projection_sha256": D,
        "issuer_ref": "issuer_ref:google-verified-boundary",
        "issued_at_epoch": 900,
        "expires_at_epoch": 1100,
        "auth_time_epoch": 950,
        "amr": ["pwd"],
    }


class MemberNaturalPersonCorroborationCandidateTest(unittest.TestCase):

    def test_local_anchor_does_not_require_google(self) -> None:
        result = evaluate_candidate(base_request())

        self.assertEqual(result["state"], PASS_STATE)
        self.assertTrue(result["candidate_only"])
        self.assertFalse(result["formal_authority_created"])
        self.assertEqual(result["total_field_decision"], "NOT_RUN")

        anchor = result["natural_person_anchor_candidate"]
        self.assertEqual(anchor["anchor_type"], "SELF_DEFINED_LOCAL")
        self.assertFalse(anchor["external_provider_derived"])
        self.assertFalse(anchor["device_derived"])
        self.assertFalse(anchor["server_derived"])
        self.assertFalse(anchor["role_derived"])

        self.assertEqual(
            result["assurance"]["state"],
            "BASE_LOCAL_HUMAN_CONFIRMED",
        )

    def test_google_verified_corroboration_increases_assurance(self) -> None:
        request = base_request()
        request["google_corroboration"] = google_evidence()

        result = evaluate_candidate(request)

        self.assertEqual(result["state"], PASS_STATE)
        receipt = result["google_corroboration_receipt_candidate"]
        self.assertEqual(
            receipt["state"],
            "VERIFIED_GOOGLE_CORROBORATION",
        )
        self.assertFalse(receipt["identity_authority"])
        self.assertFalse(receipt["raw_token_retained"])
        self.assertEqual(receipt["freshness_state"], "FRESH")
        self.assertEqual(
            result["assurance"]["state"],
            "GOOGLE_CORROBORATED_FRESH_AUTH",
        )

    def test_google_subject_conflict_holds(self) -> None:
        request = base_request()
        request["google_corroboration"] = google_evidence(B)
        request["existing_google_subject_sha256"] = C

        result = evaluate_candidate(request)

        self.assertEqual(result["state"], HOLD_CONFLICT)
        self.assertIsNone(result["natural_person_anchor_candidate"])
        self.assertIsNone(result["member_binding_candidate"])
        self.assertFalse(result["formal_authority_created"])

    def test_raw_token_or_plaintext_is_blocked(self) -> None:
        request = base_request()
        google = google_evidence()
        google["id_token"] = "forbidden"
        request["google_corroboration"] = google

        result = evaluate_candidate(request)

        self.assertEqual(
            result["state"],
            "HOLD_PLAINTEXT_OR_RAW_CREDENTIAL_FORBIDDEN",
        )

    def test_founder_is_position_bound_to_member(self) -> None:
        result = evaluate_candidate(base_request())

        binding = result["founder_position_binding_candidate"]

        self.assertIsNotNone(binding)
        self.assertEqual(
            binding["principal_ref"],
            "member_ref:founder",
        )
        self.assertEqual(
            binding["role_ref"],
            "role_ref:founder_developer",
        )
        self.assertTrue(
            binding["founder_is_position_not_identity"]
        )

    def test_candidate_is_deterministic_with_fixed_nonce(self) -> None:
        request = base_request()
        request["google_corroboration"] = google_evidence()

        first = evaluate_candidate(request)
        second = evaluate_candidate(
            dict(reversed(list(request.items())))
        )

        self.assertEqual(first, second)

    def test_ui_intent_reuses_existing_google_login(self) -> None:
        intent = build_google_ui_intent()

        self.assertTrue(intent["user_initiated"])
        self.assertTrue(intent["reuse_existing_google_member_login"])
        self.assertFalse(intent["raw_token_retained"])
        self.assertFalse(intent["google_is_identity_authority"])
        self.assertTrue(intent["google_is_optional_corroboration"])
        self.assertIn("auth_time", intent["requested_assurance_claims"])
        self.assertIn("amr", intent["requested_assurance_claims"])


if __name__ == "__main__":
    unittest.main()
