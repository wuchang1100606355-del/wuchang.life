from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/sovereign_voucher_checkout.py"
SPEC = importlib.util.spec_from_file_location("sovereign_voucher_checkout_contract", SERVICE)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


class LiaoguoSovereignVoucherCheckoutTests(unittest.TestCase):
    def setUp(self):
        self.org = "organization:liaoguo-cafe"
        self.member = "SVC-0011223344556677"
        self.seat = module.hash_ref("seat_ref", {"seat": "clerk"})
        self.pepper = "x" * 64
        self.lookup = module.build_lookup_receipt(
            organization_ref=self.org,
            seat_ref=self.seat,
            issued_at="2026-09-29 20:00:00",
            matched=True,
            member_ref=self.member,
            masked_display="江先生",
            entitlement_count=10,
        )

    def test_v23_dimensions_are_canonical_and_coupled(self):
        self.assertEqual(
            module.V23_DIMENSIONS,
            (
                "D1_INTENT",
                "D2_STATE",
                "D3_COORDINATE",
                "D4_EVIDENCE",
                "D5_EXECUTION_POLICY",
                "D6_GENERATIVE_STATE_TRANSMISSION",
                "D7_RISK_ISOLATION",
                "D8_ENVELOPE_AUTHORITY",
            ),
        )
        self.assertEqual(
            module.COUPLING_RULE,
            "ONE_COUPLED_DYNAMIC_STATE_FIELD_NOT_PIPELINE",
        )

    def test_phone_last3_uses_keyed_digest_and_does_not_echo_digits(self):
        digest = module.phone_last3_hmac(
            organization_ref=self.org,
            last_three="757",
            pepper=self.pepper,
        )
        self.assertRegex(digest, r"^[0-9a-f]{64}$")
        self.assertNotIn("757", digest)
        self.assertTrue(
            module.phone_last3_matches(
                stored_digest=digest,
                organization_ref=self.org,
                last_three="757",
                pepper=self.pepper,
            )
        )
        self.assertFalse(
            module.phone_last3_matches(
                stored_digest=digest,
                organization_ref=self.org,
                last_three="758",
                pepper=self.pepper,
            )
        )

    def test_no_match_withholds_member_and_entitlement(self):
        receipt = module.build_lookup_receipt(
            organization_ref=self.org,
            seat_ref=self.seat,
            issued_at="2026-09-29 20:00:00",
            matched=False,
        )
        self.assertNotIn("member_ref", receipt)
        self.assertNotIn("entitlement_count", receipt)
        self.assertFalse(receipt["phone_last3_disclosed"])

    def test_match_can_reveal_only_masked_display_and_ten_vouchers(self):
        self.assertEqual(self.lookup["masked_display"], "江先生")
        self.assertEqual(self.lookup["entitlement_count"], 10)
        self.assertFalse(self.lookup["identity_authentication"])
        self.assertFalse(self.lookup["checkout_consent"])

    def test_request_is_exactly_one_red_tea_and_waits_for_owner(self):
        packet = module.build_red_tea_redeem_request(
            lookup_receipt=self.lookup,
            sandbox_member_ref=self.member,
            sandbox_organization_ref=self.org,
            sandbox_product_ref="DR_RED_TEA",
            voucher_ref="VCH-TEST-001",
            voucher_hash="a" * 64,
            order_ref="ORDER-001",
            issued_at="2026-09-29 20:01:00",
        )
        self.assertEqual(packet["D1_INTENT"]["quantity"], 1)
        self.assertEqual(packet["D2_STATE"]["state"], "PENDING_OWNER_CONFIRMATION")
        self.assertFalse(packet["D5_EXECUTION_POLICY"]["clerk_may_redeem"])
        self.assertTrue(packet["D5_EXECUTION_POLICY"]["member_confirmation_required"])
        self.assertEqual(
            packet["D6_GENERATIVE_STATE_TRANSMISSION"]["differential_payload_bytes"],
            0,
        )
        self.assertFalse(
            packet["D6_GENERATIVE_STATE_TRANSMISSION"]["predecessor_state_required"]
        )

    def test_only_same_member_can_authorize_and_10_to_9_is_hashed(self):
        packet = module.build_red_tea_redeem_request(
            lookup_receipt=self.lookup,
            sandbox_member_ref=self.member,
            sandbox_organization_ref=self.org,
            sandbox_product_ref="DR_RED_TEA",
            voucher_ref="VCH-TEST-001",
            voucher_hash="a" * 64,
            order_ref="ORDER-001",
            issued_at="2026-09-29 20:01:00",
        )
        confirmation_ref = module.hash_ref("member-consent", {"request": packet["request_hash"]})
        confirmation = module.build_owner_confirmation(
            request_packet=packet,
            confirmer_member_ref=self.member,
            confirmation_ref=confirmation_ref,
            decision="CONSENT",
            confirmed_at="2026-09-29 20:02:00",
        )
        evidence = module.build_transaction_evidence(
            request_packet=packet,
            confirmation=confirmation,
            voucher_count_before=10,
            voucher_count_after=9,
            voucher_hash_before="a" * 64,
            voucher_hash_after="b" * 64,
            executed_at="2026-09-29 20:02:01",
            executor_ref="odoo-user:7",
        )
        self.assertEqual(evidence["voucher_count_before"], 10)
        self.assertEqual(evidence["voucher_count_after"], 9)
        self.assertEqual(evidence["effect"]["voucher_quantity"], -1)
        self.assertEqual(evidence["effect"]["happiness_coin_delta"], 0)
        self.assertRegex(evidence["transaction_hash"], r"^[0-9a-f]{64}$")

    def test_red_team_rejects_cross_member_and_invalid_transition(self):
        packet = module.build_red_tea_redeem_request(
            lookup_receipt=self.lookup,
            sandbox_member_ref=self.member,
            sandbox_organization_ref=self.org,
            sandbox_product_ref="DR_RED_TEA",
            voucher_ref="VCH-TEST-001",
            voucher_hash="a" * 64,
            order_ref="ORDER-001",
            issued_at="2026-09-29 20:01:00",
        )
        with self.assertRaisesRegex(
            module.SovereignCheckoutHold,
            "HOLD_CROSS_MEMBER_CONFIRMATION",
        ):
            module.build_owner_confirmation(
                request_packet=packet,
                confirmer_member_ref="SVC-OTHER",
                confirmation_ref=module.hash_ref("member-consent", "other"),
                decision="CONSENT",
                confirmed_at="2026-09-29 20:02:00",
            )

    def test_source_blocks_legacy_direct_redeem_and_old_8d_names(self):
        member_source = (
            ROOT / "Taiji_Odoo/addons/wuchang_member_registration/models/member_registration.py"
        ).read_text(encoding="utf-8")
        assembly_source = (
            ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/eightd_system_assembly.py"
        ).read_text(encoding="utf-8")
        self.assertIn("HOLD_MEMBER_OWNER_CONFIRMATION_REQUIRED", member_source)
        self.assertIn("_redeem_from_verified_sovereign_checkout", member_source)
        self.assertNotIn('"id": "D1_identity"', assembly_source)
        self.assertIn('"id": "D1_INTENT"', assembly_source)
        self.assertIn("ONE_COUPLED_DYNAMIC_STATE_FIELD_NOT_PIPELINE", assembly_source)


if __name__ == "__main__":
    unittest.main()
