"""Isolated founder-root-first authority resolver tests; ephemeral keys only."""
import base64
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tools import total_field_authority_resolver as resolver
from tools.total_field.w7tp_ed25519_verifier import build_stage_b_signed_bytes


class FounderMasterAuthorityV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.key = Ed25519PrivateKey.generate()
        pub = self.key.public_key()
        (self.root / "pub.pem").write_bytes(pub.public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        ))
        pubraw = pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.anchor = {
            "public_key_pem_ref": "pub.pem",
            "ed25519_raw_public_key_fingerprint_sha256": hashlib.sha256(pubraw).hexdigest(),
            "verifier_ref": "verifier_ref:founder_sovereign_root_v1",
            "authorized_effect_domains": [],
        }
        receipt_dir = self.root / (
            "runtime/total_field/authority_artifacts/"
            "W7TP_TOTAL_FIELD_ROOT_OF_TRUST_BOOTSTRAP_20260821T1557+0800"
        )
        receipt_dir.mkdir(parents=True)
        (receipt_dir / "INDEPENDENT_FOUNDER_SOVEREIGN_ROOT_ROLE_PROMOTION_GRANT_ACTIVE.json").write_text("{}")
        (receipt_dir / "CANONICAL_TRUST_POLICY_PROMOTION_RECEIPT_20261020.json").write_text("{}")
        self.active = self.root / "runtime/total_field/ACTIVE_TOTAL_FIELD_AUTHORITY.json"
        self.active.parent.mkdir(parents=True, exist_ok=True)
        self.body = {
            "schema": "w7tp.total_field.active_authority/2.0",
            "authority_issuer": "FOUNDER_SOVEREIGN_ROOT",
            "status": "PASS_AUTHORITY_ACTIVE",
            "developer_bypass": True,
            "effects": ["PASS_FOUNDER_UNIVERSAL_AUTHORITY_ACTIVE", "AUTHORIZE_XIAOJ_3D_ISOLATED_GATEWAY_PREVIEW_DEPLOY"],
            "updated_at": "2026-10-29T12:00:00+08:00",
        }

    def sign(self, body=None):
        body = copy.deepcopy(body or self.body)
        domain = "W7TP_FOUNDER_UNIVERSAL_MASTER_V2"
        canonical_id = "founder-universal-master-test:v2"
        signed = build_stage_b_signed_bytes(
            domain_separator=domain, packet_canonical_id=canonical_id,
            stage_b_object_without_signature=body,
        )
        signed_sha = hashlib.sha256(signed).hexdigest()
        return {
            **body,
            "domain_separator": domain,
            "packet_canonical_id": canonical_id,
            "stage_b_object_without_signature": body,
            "stage_b_signature_hex": self.key.sign(signed).hex(),
            "detached_signature_artifact": {
                "verifier_ref": self.anchor["verifier_ref"],
                "signed_payload_sha256": signed_sha,
                "signature": "ed25519:" + base64.b64encode(
                    self.key.sign(signed_sha.encode("ascii"))
                ).decode("ascii"),
            },
        }

    def evaluate(self, packet, effect="PASS_FOUNDER_UNIVERSAL_AUTHORITY_ACTIVE"):
        self.active.write_text(json.dumps(packet, ensure_ascii=False))
        with patch.object(resolver, "FOUNDER_SINGLE_IDENTITY_ROOT_POLICY_V1", {
            "authorized_sovereign_node_root_key": self.anchor
        }), patch.object(
            resolver, "resolve_founder_sovereign_root_role_promotion_authority",
            return_value={"state": "PASS_TEST_ANCHOR"}
        ), patch.object(
            resolver, "verify_canonical_trust_policy_promotion",
            return_value={"state": "PASS_TEST_POLICY"}
        ):
            return resolver.resolve_total_field_authority_dual_schema(
                repo_root=self.root, required_effect=effect
            )

    def test_valid_founder_root_signature_has_highest_precedence(self):
        r = self.evaluate(self.sign())
        self.assertTrue(r["authority_verified"])
        self.assertEqual(r["authority_precedence"], "FOUNDER_SOVEREIGN_ROOT_HIGHEST")

    def test_founder_signature_is_not_subordinate_to_developer_bypass_flag(self):
        body = copy.deepcopy(self.body)
        body["developer_bypass"] = False
        r = self.evaluate(self.sign(body))
        self.assertTrue(r["authority_verified"])
        self.assertEqual(r["authority_precedence"], "FOUNDER_SOVEREIGN_ROOT_HIGHEST")

    def test_unsigned_status_and_bypass_cannot_impersonate_founder(self):
        r = self.evaluate(self.body)
        self.assertFalse(r["authority_verified"])
        self.assertNotEqual(r["state"], "PASS_DUAL_SCHEMA_AUTHORITY_RESOLVED")

    def test_tampered_effect_rejected(self):
        packet = self.sign()
        packet["effects"] = ["INJECT_UNSIGNED_EFFECT"]
        r = self.evaluate(packet, "INJECT_UNSIGNED_EFFECT")
        self.assertEqual(r["state"], "HOLD_FOUNDER_MASTER_SIGNED_BODY_MISMATCH")

    def test_forged_signature_rejected(self):
        packet = self.sign()
        packet["stage_b_signature_hex"] = "00" * 64
        r = self.evaluate(packet)
        self.assertEqual(r["state"], "HOLD_STAGE_B_SIGNATURE_INVALID")

    def test_ungranted_effect_rejected_even_with_valid_signature(self):
        r = self.evaluate(self.sign(), "INJECT_UNGRANTED_EFFECT")
        self.assertEqual(r["state"], "HOLD_REQUIRED_EFFECT_NOT_GRANTED")


if __name__ == "__main__":
    unittest.main()
