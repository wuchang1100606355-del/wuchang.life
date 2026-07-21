#!/usr/bin/env python3
"""Role mapping and isolation tests for the unactivated XiaoJ seat candidate."""

from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from tools.total_field.xiaoj_member_bound_session_candidate import (
    evaluate_session,
    receive_cloud_fragment,
)


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "manifests/xiaoj_member_bound_developer_seat_candidate_v0_1/policy.json"
SCHEMA_PATH = ROOT / "schemas/xiaoj_member_bound_developer_seat_candidate.schema.json"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class XiaoJMemberBoundDeveloperSeatCandidateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(cls.schema)

    def request(self, member: str = "member_ref:founder", agent: str = "xiaoj_agent_ref:founder-local") -> dict:
        roles = ["role_ref:founder_developer"] if member == "member_ref:founder" else ["role_ref:member"]
        return {
            "member_ref": member,
            "xiaoj_agent_ref": agent,
            "member_role_refs": list(roles),
            "organization_context": {"organization_ref": "organization_ref:taiji", "scope_refs": ["scope_ref:local-development"]},
            "device_or_channel_binding": {"binding_type": "DEVICE", "binding_ref": "device_ref:msi", "binding_hash": digest("device")},
            "delegation_envelope": {
                "delegation_ref": "delegation_ref:fixture",
                "issuer_member_ref": member,
                "subject_member_ref": member,
                "bound_xiaoj_agent_ref": agent,
                "allowed_role_refs": list(roles),
                "issued_at_epoch": 100,
                "expires_at_epoch": 200,
                "nonce": "nonce:delegation-fixture",
                "revoked": False,
                "subdelegation": False
            },
            "ttl_seconds": 100,
            "nonce": "nonce:session-fixture",
            "revocation_state": "ACTIVE",
            "membership_state": "ACTIVE",
            "principal_verified": True,
            "command_ref": "command_ref:local-development-fixture",
            "verification_refs": ["evidence_ref:member-verification", "evidence_ref:role-table-snapshot"]
        }

    def roles(self) -> dict[str, list[str]]:
        return {
            "member_ref:founder": ["role_ref:founder_developer", "role_ref:member"],
            "member_ref:member-a": ["role_ref:member"],
            "member_ref:member-b": ["role_ref:member"]
        }

    def test_verified_member_and_bound_xiaoj_create_candidate_session(self) -> None:
        result = evaluate_session(self.request(), self.roles(), current_epoch=110)
        self.assertEqual(result["state"], "PASS_MEMBER_BOUND_CANDIDATE")
        self.assertEqual(result["d7_disposition"], "PASS")
        self.assertFalse(result["role_activated"])
        self.assertIsNone(result["d8_capability_envelope_candidate"]["final_decision"])
        self.assertTrue(result["d8_capability_envelope_candidate"]["requires_total_field_verify"])

    def test_non_member_and_inactive_member_are_blocked(self) -> None:
        nonmember = self.request("member_ref:unknown", "xiaoj_agent_ref:unknown")
        self.assertEqual(evaluate_session(nonmember, self.roles(), current_epoch=110)["state"], "BLOCK_NON_MEMBER")
        inactive = self.request("member_ref:member-a", "xiaoj_agent_ref:member-a")
        inactive["membership_state"] = "INACTIVE"
        self.assertEqual(evaluate_session(inactive, self.roles(), current_epoch=110)["state"], "BLOCK_INACTIVE_MEMBER")

    def test_xiaoj_binding_and_cross_member_identity_are_isolated(self) -> None:
        unbound = self.request("member_ref:member-a", "xiaoj_agent_ref:member-a")
        unbound["delegation_envelope"]["bound_xiaoj_agent_ref"] = "xiaoj_agent_ref:other"
        self.assertEqual(evaluate_session(unbound, self.roles(), current_epoch=110)["state"], "BLOCK_XIAOJ_NOT_BOUND")
        crossed = self.request("member_ref:member-a", "xiaoj_agent_ref:member-a")
        crossed["delegation_envelope"]["subject_member_ref"] = "member_ref:member-b"
        self.assertEqual(evaluate_session(crossed, self.roles(), current_epoch=110)["state"], "BLOCK_IDENTITY_MISMATCH")

    def test_revoked_and_expired_delegation_are_blocked(self) -> None:
        revoked = self.request()
        revoked["delegation_envelope"]["revoked"] = True
        self.assertEqual(evaluate_session(revoked, self.roles(), current_epoch=110)["state"], "BLOCK_DELEGATION_REVOKED")
        expired = self.request()
        self.assertEqual(evaluate_session(expired, self.roles(), current_epoch=200)["state"], "BLOCK_DELEGATION_EXPIRED")

    def test_permissions_are_intersection_with_existing_role_table(self) -> None:
        asserted = self.request("member_ref:member-a", "xiaoj_agent_ref:member-a")
        asserted["member_role_refs"].append("role_ref:founder_developer")
        asserted["delegation_envelope"]["allowed_role_refs"].append("role_ref:founder_developer")
        self.assertEqual(evaluate_session(asserted, self.roles(), current_epoch=110)["state"], "BLOCK_SELF_DECLARED_ROLE")

    def test_founder_developer_seat_is_exclusive_and_nontransferable(self) -> None:
        result = evaluate_session(self.request(), self.roles(), current_epoch=110)
        seat = result["founder_developer_seat"]
        self.assertEqual(seat["max_seats"], 1)
        self.assertTrue(seat["exclusive"])
        self.assertFalse(seat["transferable"])
        self.assertFalse(seat["subdelegation"])
        permissions = result["d8_capability_envelope_candidate"]["capability_refs"]
        self.assertEqual(permissions, ["LOCAL_SOURCE_CHANGE", "LOCAL_TEST", "LOCAL_SANDBOX", "LOCAL_EVIDENCE_WRITE"])
        forbidden = set(self.policy["independent_founder_authorization_required"])
        self.assertFalse(forbidden & set(permissions))

    def test_operation_record_separates_principal_actor_role_command_evidence(self) -> None:
        result = evaluate_session(self.request(), self.roles(), current_epoch=110)
        record = result["operation_record"]
        self.assertEqual(set(record), {"principal", "actor", "role", "command", "evidence"})
        self.assertEqual(record["principal"], "member_ref:founder")
        self.assertEqual(record["actor"], "xiaoj_agent_ref:founder-local")

    def test_cloud_fragment_requires_founder_and_verified_member_xiaoj(self) -> None:
        session = evaluate_session(self.request(), self.roles(), current_epoch=110)
        fragment = {"fragment_type": "CANDIDATE", "candidate_ref": "candidate_ref:cloud-fragment", "evidence_hash": digest("cloud")}
        self.assertEqual(receive_cloud_fragment(fragment, session, founder_authorized=False)["state"], "BLOCK_CLOUD_CANDIDATE_NOT_AUTHORIZED")
        accepted = receive_cloud_fragment(fragment, session, founder_authorized=True)
        self.assertEqual(accepted["state"], "PASS_RECEIVE_CANDIDATE_REQUIRED")
        self.assertEqual(accepted["intake"], "receive_candidate")
        self.assertTrue(accepted["requires_total_field_verify"])
        direct = receive_cloud_fragment(fragment, {"state": "HOLD"}, founder_authorized=True)
        self.assertEqual(direct["state"], "BLOCK_CLOUD_DIRECT_CONNECTION")

    def test_cloud_fragment_cannot_contain_member_ref(self) -> None:
        session = evaluate_session(self.request(), self.roles(), current_epoch=110)
        fragment = {"fragment_type": "EVIDENCE_FRAGMENT", "member_ref": "member_ref:forbidden"}
        self.assertEqual(receive_cloud_fragment(fragment, session, founder_authorized=True)["state"], "BLOCK_CLOUD_MEMBER_REF_OR_PLAINTEXT")

    def test_no_side_effect_or_server_llm_authority(self) -> None:
        result = evaluate_session(self.request(), self.roles(), current_epoch=110)
        for key in ("db_write", "deploy", "restart", "router_write", "canonical_change", "role_activated"):
            self.assertFalse(result[key])
        self.assertEqual(result["server_llm"], "BLOCK")
        self.assertEqual(result["member_plaintext_count"], 0)


if __name__ == "__main__":
    unittest.main()
