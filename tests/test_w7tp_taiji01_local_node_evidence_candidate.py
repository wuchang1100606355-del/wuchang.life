"""taiji01 本機節點證據候選測試。"""

import copy
import hashlib
import json
import unittest

from tools.total_field.w7tp_taiji01_local_node_evidence_candidate import (
    MACHINE_ID_PATH,
    PRODUCT_UUID_PATH,
    SSH_PUBLIC_KEY_PATHS,
    build_local_node_evidence,
    verify_local_node_evidence,
)


MATERIAL = {
    "machine_id": "raw-machine-id-test-value",
    "ssh_host_public_key": "ssh-ed25519 AAAATESTONLY local-test",
}
CHALLENGE = "verifier-nonce-test-001"


def reseal(packet):
    basis = dict(packet)
    basis.pop("evidence_sha256", None)
    encoded = json.dumps(
        basis,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    packet["evidence_sha256"] = hashlib.sha256(encoded).hexdigest()
    return packet


class Taiji01LocalNodeEvidenceCandidateTest(unittest.TestCase):
    def test_deterministic_and_ref_only(self):
        first = build_local_node_evidence(
            hostname="taiji01",
            source_material=MATERIAL,
            challenge=CHALLENGE,
        )
        second = build_local_node_evidence(
            hostname="taiji01",
            source_material=MATERIAL,
            challenge=CHALLENGE,
        )

        self.assertEqual(first, second)
        self.assertEqual(
            first["state"],
            "PASS_LOCAL_NODE_EVIDENCE_CANDIDATE",
        )
        self.assertNotIn(MATERIAL["machine_id"], str(first))
        self.assertNotIn(MATERIAL["ssh_host_public_key"], str(first))

    def test_wrong_hostname_holds(self):
        result = build_local_node_evidence(
            hostname="other-node",
            source_material=MATERIAL,
            challenge=CHALLENGE,
        )
        self.assertEqual(
            result["reason_code"],
            "HOLD_LOCAL_NODE_TARGET_MISMATCH",
        )

    def test_single_source_holds(self):
        result = build_local_node_evidence(
            hostname="taiji01",
            source_material={"machine_id": "one-source-only"},
            challenge=CHALLENGE,
        )
        self.assertEqual(
            result["reason_code"],
            "HOLD_LOCAL_NODE_EVIDENCE_INSUFFICIENT",
        )

    def test_no_authority_or_identity_created(self):
        result = build_local_node_evidence(
            hostname="taiji01",
            source_material=MATERIAL,
            challenge=CHALLENGE,
        )
        self.assertEqual(result["authority"], "NONE")
        self.assertFalse(result["identity_created"])
        self.assertFalse(result["device_sovereignty_created"])
        self.assertFalse(result["inventory_write"])
        self.assertFalse(result["db_write"])
        self.assertFalse(result["deploy"])
        self.assertFalse(result["restart"])
        self.assertFalse(result["git_push"])

    def test_tamper_is_rejected(self):
        result = build_local_node_evidence(
            hostname="taiji01",
            source_material=MATERIAL,
            challenge=CHALLENGE,
        )
        tampered = copy.deepcopy(result)
        tampered["source_hashes"]["machine_id"] = "0" * 64

        valid, reason = verify_local_node_evidence(tampered)
        self.assertFalse(valid)
        self.assertIn(
            reason,
            {
                "LOCAL_NODE_FINGERPRINT_MISMATCH",
                "EVIDENCE_SHA256_MISMATCH",
            },
        )

    def test_clean_candidate_verifies(self):
        result = build_local_node_evidence(
            hostname="taiji01",
            source_material=MATERIAL,
            challenge=CHALLENGE,
        )
        valid, reason = verify_local_node_evidence(
            result,
            expected_source_material=MATERIAL,
            expected_challenge=CHALLENGE,
        )
        self.assertTrue(valid)
        self.assertEqual(
            reason,
            "PASS_LOCAL_NODE_EVIDENCE_LOCAL_RECHECKED",
        )

    def test_all_safety_flags_are_enforced_after_reseal(self):
        for field in (
            "identity_created",
            "device_sovereignty_created",
            "inventory_write",
            "db_write",
            "deploy",
            "restart",
            "git_push",
            "raw_identifier_exposed",
        ):
            with self.subTest(field=field):
                result = build_local_node_evidence(
                    hostname="taiji01",
                    source_material=MATERIAL,
                    challenge=CHALLENGE,
                )
                result[field] = True
                reseal(result)
                valid, reason = verify_local_node_evidence(
                    result,
                    expected_source_material=MATERIAL,
                    expected_challenge=CHALLENGE,
                )
                self.assertFalse(valid)
                self.assertEqual(reason, f"{field.upper()}_FORBIDDEN")

    def test_unknown_and_missing_fields_are_rejected(self):
        result = build_local_node_evidence(
            hostname="taiji01",
            source_material=MATERIAL,
            challenge=CHALLENGE,
        )
        result["raw_identifier"] = "must-not-be-accepted"
        reseal(result)
        self.assertEqual(
            verify_local_node_evidence(result)[1],
            "UNKNOWN_FIELD_REJECTED",
        )

        result = build_local_node_evidence(
            hostname="taiji01",
            source_material=MATERIAL,
            challenge=CHALLENGE,
        )
        result.pop("semantic_boundary")
        reseal(result)
        self.assertEqual(
            verify_local_node_evidence(result)[1],
            "REQUIRED_FIELD_MISSING",
        )

    def test_resealed_forged_source_is_rejected_by_local_recheck(self):
        forged_material = {
            "machine_id": "forged-machine",
            "ssh_host_public_key": "ssh-ed25519 FORGED local-test",
        }
        result = build_local_node_evidence(
            hostname="taiji01",
            source_material=forged_material,
            challenge=CHALLENGE,
        )
        valid, reason = verify_local_node_evidence(
            result,
            expected_source_material=MATERIAL,
            expected_challenge=CHALLENGE,
        )
        self.assertFalse(valid)
        self.assertEqual(reason, "LOCAL_SOURCE_MISMATCH")

    def test_wrong_challenge_and_replay_are_rejected(self):
        result = build_local_node_evidence(
            hostname="taiji01",
            source_material=MATERIAL,
            challenge=CHALLENGE,
        )
        valid, reason = verify_local_node_evidence(
            result,
            expected_source_material=MATERIAL,
            expected_challenge="different-verifier-nonce",
        )
        self.assertFalse(valid)
        self.assertEqual(reason, "CHALLENGE_MISMATCH")

    def test_missing_challenge_is_verified_hold_not_pass(self):
        result = build_local_node_evidence(
            hostname="taiji01",
            source_material=MATERIAL,
            challenge=None,
        )
        valid, reason = verify_local_node_evidence(result)
        self.assertFalse(valid)
        self.assertEqual(
            reason,
            "VERIFIED_HOLD_LOCAL_NODE_CHALLENGE_REQUIRED",
        )

    def test_state_reason_and_semantic_boundary_are_enforced(self):
        cases = (
            ("state", "UNKNOWN", "STATE_INVALID"),
            ("reason_code", "PASS_WITHOUT_REASON", "PASS_REASON_MISMATCH"),
            (
                "semantic_boundary",
                {"node_is_authority": True},
                "SEMANTIC_BOUNDARY_MISMATCH",
            ),
        )
        for field, value, expected_reason in cases:
            with self.subTest(field=field):
                result = build_local_node_evidence(
                    hostname="taiji01",
                    source_material=MATERIAL,
                    challenge=CHALLENGE,
                )
                result[field] = value
                reseal(result)
                valid, reason = verify_local_node_evidence(result)
                self.assertFalse(valid)
                self.assertEqual(reason, expected_reason)

    def test_source_paths_do_not_use_ssh_private_keys(self):
        paths = [
            str(MACHINE_ID_PATH),
            str(PRODUCT_UUID_PATH),
            *(str(path) for path in SSH_PUBLIC_KEY_PATHS),
        ]
        for path in paths:
            self.assertFalse(
                path.endswith(
                    (
                        "ssh_host_ed25519_key",
                        "ssh_host_ecdsa_key",
                        "ssh_host_rsa_key",
                    )
                )
            )


if __name__ == "__main__":
    unittest.main()
