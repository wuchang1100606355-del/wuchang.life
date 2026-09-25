#!/usr/bin/env python3
"""Tests for plan-defined scene, identity, privacy, ADI, temporal, and canary adapters."""

from __future__ import annotations

import unittest

from tools.total_field.w7tp_non_live_build_adapters import (
    adi_direct_slot,
    build_read_only_canary_proposal,
    evaluate_identity_evidence,
    evaluate_image_step_up,
    validate_scene_state,
    verify_temporal_chain,
)
from tools.total_field.w7tp_true8d_contract_sandbox import canonical_sha256


class TotalFieldNonLiveCandidatesTest(unittest.TestCase):
    def test_scene_state_structured_profiles_and_scalar_hold(self) -> None:
        for profile in ("ASSOCIATION", "CAFE_POS", "GENERIC", "HOUSEHOLD", "PROPERTY", "IDENTITY", "MEDICAL", "BUSINESS", "COMMUNITY", "IMAGE_STEP_UP"):
            value = {"profile_ref": profile, "source": "fixture:non-live", "baseline": {"state": "A"}, "proposed": {"state": "B"}, "transition": {"code": "CANDIDATE"}}
            first = validate_scene_state(value)
            second = validate_scene_state(value)
            self.assertEqual(first, second)
            self.assertEqual(first["state"], "PASS_CANDIDATE")
            self.assertFalse(first["commit_applied"])
        self.assertEqual(validate_scene_state("scalar")["state"], "HOLD_D2_META_CONTRACT_INCOMPLETE")
        self.assertEqual(validate_scene_state({"profile_ref": "GENERIC", "source": "x", "baseline": {}, "proposed": {}, "transition": {}})["state"], "HOLD_D2_META_CONTRACT_INCOMPLETE")

    def test_identity_is_hashed_candidate_only_and_forbidden_plaintext_blocks(self) -> None:
        evidence = {key: canonical_sha256(key) for key in ("issuer_hash", "subject_hash", "device_principal_hash", "session_ref_hash", "connection_ref_hash", "explicit_intent_hash")}
        evidence.update({"local_natural_person_verifier_ref": "verifier:local-natural-person:v1", "authority_state_ref": "authority:current:v1"})
        result = evaluate_identity_evidence(evidence)
        self.assertEqual(result["state"], "PASS_CANDIDATE_IDENTITY_EVIDENCE")
        self.assertFalse(result["final_authority"])
        blocked = evaluate_identity_evidence({**evidence, "member_plaintext": "forbidden"})
        self.assertEqual(blocked["state"], "BLOCK_REQUEST_FORBIDDEN_FIELD")

    def test_image_step_up_is_result_only_and_zeroized(self) -> None:
        value = {"result_state": "PASS", "evidence_ref": "stepup:evidence:v1", "algorithm_version_ref": "algorithm:stepup:v1", "result_hash": canonical_sha256("pass"), "volatile_lifecycle_complete": True, "zeroization_evidence_ref": "zeroization:volatile:v1"}
        result = evaluate_image_step_up(value)
        self.assertEqual(result["state"], "PASS_STEP_UP_RESULT_REFERENCE_ONLY")
        self.assertEqual(result["raw_image_disk_count"], 0)
        self.assertEqual(result["raw_image_uplink_count"], 0)
        self.assertEqual(evaluate_image_step_up({**value, "raw_image": "forbidden"})["state"], "BLOCK_RAW_IMAGE_RETENTION_UPLINK_OR_PROFILING")

    def test_adi_boundaries_collisions_and_integer_policy(self) -> None:
        first = adi_direct_slot({"interval_start": 0, "interval_end": 100, "timestamp": 99, "slot_count": 10, "collision_refs": ["candidate:a", "candidate:b"]})
        self.assertEqual(first["slot"], 9)
        self.assertEqual(first["collision_bucket_size"], 2)
        self.assertFalse(first["unconditional_o1_claim"])
        self.assertFalse(first["adi_authority"])
        self.assertEqual(adi_direct_slot({"interval_start": 0, "interval_end": 100, "timestamp": 100, "slot_count": 10, "collision_refs": []})["state"], "HOLD_UNRESOLVED_COLLISION_OR_INTERVAL_POLICY")
        self.assertEqual(adi_direct_slot({"interval_start": 0, "interval_end": 100, "timestamp": 1.5, "slot_count": 10, "collision_refs": []})["state"], "HOLD_UNRESOLVED_COLLISION_OR_INTERVAL_POLICY")

    def test_temporal_chain_detects_reorder_and_replay(self) -> None:
        first = {"record_ref": "record:0", "previous_hash": "0" * 64, "payload_hash": canonical_sha256("a"), "logical_index": 0, "nonce": "nonce:0", "ttl_seconds": 30, "trusted_time_ref": "trusted-time:fixture:0", "signature_ref": "signature:fixture:0"}
        second = {"record_ref": "record:1", "previous_hash": canonical_sha256(first), "payload_hash": canonical_sha256("b"), "logical_index": 1, "nonce": "nonce:1", "ttl_seconds": 30, "trusted_time_ref": "trusted-time:fixture:1", "signature_ref": "signature:fixture:1"}
        self.assertEqual(verify_temporal_chain([first, second])["state"], "PASS_TEMPORAL_EVIDENCE_CHAIN_CANDIDATE")
        self.assertEqual(verify_temporal_chain([second, first])["state"], "HOLD_TEMPORAL_INSERT_OR_REORDER")
        replay = dict(second); replay["nonce"] = "nonce:0"
        self.assertEqual(verify_temporal_chain([first, replay])["state"], "QUARANTINE_TEMPORAL_REPLAY")

    def test_canary_remains_proposal_only(self) -> None:
        proposal = build_read_only_canary_proposal([canonical_sha256("evidence")])
        self.assertFalse(proposal["canary_start_authorized"])
        self.assertEqual(proposal["execution_count"], 0)
        self.assertFalse(proposal["db_write"])
        self.assertFalse(proposal["deploy"])
        self.assertFalse(proposal["restart"])
        self.assertEqual(proposal["server_llm"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
