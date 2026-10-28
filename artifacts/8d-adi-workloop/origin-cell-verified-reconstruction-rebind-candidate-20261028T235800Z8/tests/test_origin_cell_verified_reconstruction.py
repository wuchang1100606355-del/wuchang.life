#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "candidate"))

import origin_cell_verified_reconstruction as vr  # noqa: E402


def raw_repeat_packet(value: int = 0x41, count: int = 32) -> tuple[bytes, bytes]:
    if not 0 <= value <= 255 or not 1 <= count <= 65535:
        raise ValueError("invalid fixture")
    packet = struct.pack(
        ">BBBBBBH",
        0x8D,  # warm packet
        1,     # one target
        1,     # target id
        1,     # one opcode
        4,     # OP_RAW_REPEAT
        1,     # pattern length
        count,
    ) + bytes([value])
    return packet, bytes([value]) * count


class VerifiedReconstructionCandidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.packet, self.target = raw_repeat_packet()
        self.source_sha = hashlib.sha256(self.target).hexdigest()
        self.common = {
            "source_state_sha256": self.source_sha,
            "source_size_bytes": len(self.target),
            "namespace": "test:w7tp:origin-cell:v21",
            "reconstruction_contract": "BYTE_EXACT_FIXTURE_V1",
            "route_ref": "route_ref:test-file-class",
        }

    def issue_seal(self):
        return vr.full_verify_and_issue_candidate_seal(
            packet=self.packet,
            expected_targets={1: self.target},
            d4_evidence_refs=["evidence:test:byte-exact"],
            observed_at="2026-10-23T23:31:00+08:00",
            **self.common,
        )

    def test_codec_anchor_matches_existing_total_field_anchor(self):
        obs = vr.codec_anchor_observation()
        self.assertTrue(obs["match"])
        self.assertEqual(obs["actual_sha256"], vr.EXPECTED_CODEC_SHA256)

    def test_same_input_produces_same_reconstruction_key(self):
        codec = vr._load_codec_module()
        d1 = codec.UniversalOriginCellDecoder()
        d2 = codec.UniversalOriginCellDecoder()
        b1 = vr.build_reconstruction_binding(
            packet=self.packet,
            base_cache_sha256=d1.cache_sha256(),
            **self.common,
        )
        b2 = vr.build_reconstruction_binding(
            packet=self.packet,
            base_cache_sha256=d2.cache_sha256(),
            **self.common,
        )
        self.assertEqual(b1["reconstruction_key"], b2["reconstruction_key"])

    def test_full_verification_issues_d4_candidate_not_d8_authority(self):
        seal = self.issue_seal()
        vr.verify_trust_seal_record(seal)
        self.assertEqual(
            seal["state"], "CANDIDATE_RECONSTRUCTION_TRUST_SEAL_VERIFIED"
        )
        self.assertFalse(seal["effect_authorization"])
        self.assertTrue(seal["current_d8_required_for_effect"])
        self.assertFalse(seal["reconstructed_equals_executed"])

    def test_verified_same_identity_uses_fast_path(self):
        seal = self.issue_seal()
        index = vr.build_trust_index([seal])
        result = vr.fast_reconstruct_with_trust_seal(
            packet=self.packet,
            trust_index=index,
            **self.common,
        )
        self.assertEqual(result["state"], "PASS_TRUST_SEAL_FAST_RECONSTRUCTION")
        self.assertEqual(result["target_state_digest"], seal["target_state_digest"])
        self.assertEqual(
            result["verified_reconstruction_identity"],
            seal["verified_reconstruction_identity"],
        )
        self.assertFalse(result["effect_authorization"])

    def test_packet_drift_leaves_fast_path_and_requires_full_verification(self):
        seal = self.issue_seal()
        index = vr.build_trust_index([seal])
        changed_packet, changed_target = raw_repeat_packet(value=0x42, count=32)
        changed_common = dict(self.common)
        changed_common["source_state_sha256"] = hashlib.sha256(changed_target).hexdigest()
        result = vr.fast_reconstruct_with_trust_seal(
            packet=changed_packet,
            trust_index=index,
            **changed_common,
        )
        self.assertEqual(result["state"], "HOLD_FULL_VERIFICATION_REQUIRED")
        self.assertFalse(result["effect_authorization"])

    def test_source_identity_drift_leaves_fast_path(self):
        seal = self.issue_seal()
        index = vr.build_trust_index([seal])
        changed = dict(self.common)
        changed["source_state_sha256"] = hashlib.sha256(b"different-source").hexdigest()
        result = vr.fast_reconstruct_with_trust_seal(
            packet=self.packet,
            trust_index=index,
            **changed,
        )
        self.assertEqual(result["state"], "HOLD_FULL_VERIFICATION_REQUIRED")

    def test_trust_seal_tamper_is_rejected(self):
        seal = self.issue_seal()
        tampered = dict(seal)
        tampered["effect_authorization"] = True
        with self.assertRaises(vr.ReconstructionHold) as ctx:
            vr.verify_trust_seal_record(tampered)
        self.assertIn(
            ctx.exception.code,
            {
                "HOLD_TRUST_SEAL_BINDING_MISMATCH",
                "BLOCK_TRUST_SEAL_EFFECT_AUTHORITY_ESCALATION",
            },
        )

    def test_wrong_expected_target_cannot_receive_seal(self):
        with self.assertRaises(vr.ReconstructionHold) as ctx:
            vr.full_verify_and_issue_candidate_seal(
                packet=self.packet,
                expected_targets={1: b"X" * len(self.target)},
                d4_evidence_refs=["evidence:test:wrong-target"],
                observed_at="2026-10-23T23:31:00+08:00",
                **self.common,
            )
        self.assertEqual(ctx.exception.code, "HOLD_RECONSTRUCTED_BYTES_MISMATCH")

    def test_model_may_propose_information_relations_only(self):
        candidate = vr.normalize_model_integration_candidate({
            "input_refs": ["ref:A", "ref:B"],
            "relation_candidates": [
                {
                    "subject_ref": "ref:A",
                    "predicate": "SUPPLEMENTS",
                    "object_ref": "ref:B",
                }
            ],
            "rule_candidate_ref": "candidate:rule:17",
        })
        self.assertEqual(candidate["state"], "CANDIDATE_ONLY")
        self.assertFalse(candidate["model_output_is_authority"])
        self.assertFalse(candidate["model_output_is_effect"])

    def test_model_candidate_cannot_smuggle_execution_or_authority(self):
        with self.assertRaises(vr.ReconstructionHold) as ctx:
            vr.normalize_model_integration_candidate({
                "input_refs": ["ref:A"],
                "relation_candidates": [
                    {
                        "subject_ref": "ref:A",
                        "predicate": "SAME_STATE",
                        "object_ref": "ref:A",
                    }
                ],
                "execute": "rm -rf /",
            })
        self.assertEqual(
            ctx.exception.code, "BLOCK_MODEL_CANDIDATE_EFFECT_OR_AUTHORITY_FIELD"
        )

    def test_unknown_relation_is_hold_not_model_guess(self):
        with self.assertRaises(vr.ReconstructionHold) as ctx:
            vr.normalize_model_integration_candidate({
                "input_refs": ["ref:A", "ref:B"],
                "relation_candidates": [
                    {
                        "subject_ref": "ref:A",
                        "predicate": "MAYBE_SIMILAR",
                        "object_ref": "ref:B",
                    }
                ],
            })
        self.assertEqual(ctx.exception.code, "HOLD_MODEL_RELATION_NOT_ALLOWED")

    def test_rehashed_forged_seal_from_untrusted_evidence_source_is_rejected(self):
        seal = self.issue_seal()
        forged = dict(seal)
        forged_ver = dict(forged["verification"])
        forged_ver["d4_evidence_refs"] = ["forged:untrusted:external-claim"]
        forged_ver["evidence_producer"] = "untrusted:external-actor"
        forged["verification"] = forged_ver
        forged.pop("trust_seal_sha256", None)
        forged["trust_seal_sha256"] = vr.canonical_hash(forged)
        with self.assertRaises(vr.ReconstructionHold) as ctx:
            vr.verify_trust_seal_record(forged)
        self.assertIn(
            ctx.exception.code,
            {"HOLD_UNTRUSTED_D4_EVIDENCE_PRODUCER", "HOLD_UNTRUSTED_D4_EVIDENCE_SOURCE"},
        )
        with self.assertRaises(vr.ReconstructionHold):
            vr.build_trust_index([forged])


if __name__ == "__main__":
    unittest.main()
