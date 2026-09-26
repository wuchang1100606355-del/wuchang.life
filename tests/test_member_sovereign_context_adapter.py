#!/usr/bin/env python3
from __future__ import annotations

import copy
import unittest

from tools.total_field.member_sovereign_context_adapter import (
    MemberSovereignContextHold,
    build_member_model_visible_context,
    build_member_sovereign_context_candidate,
    canonical_sha256,
)
from tools.total_field_dynamic_context_pull import validate_model_visible_context


def ref(kind: str, label: str) -> str:
    return f"{kind}_ref:sha256:" + canonical_sha256({"kind": kind, "label": label})


def request_fixture() -> dict:
    natural = ref("member", "person-a")
    root = ref("member_identity_root", "person-a")
    organization = ref("organization", "org-a")
    seat = ref("seat", "member-seat-a")
    role = ref("role", "member-role-a")
    session = ref("session", "s1")
    scene = ref("scene", "scene1")
    purpose = ref("purpose", "ask-model")
    scope = [ref("scope", "member-ai")]
    action_hash = canonical_sha256({"purpose": purpose, "scope": scope})
    member_receipt = ref("member_consent_receipt", "r1")
    tf_receipt = ref("total_field_receipt", "r1")
    nonce_ev = ref("nonce_consumption_evidence", "n1")
    gate_material = {
        "schema_version": "w7tp.member-session-dual-receipt-9107.v1",
        "identity_root_ref": root,
        "root_generation": 1,
        "revocation_epoch": 0,
        "session_ref": session,
        "scene_ref": scene,
        "action_hash": action_hash,
        "scope_refs": scope,
        "effect_class": "REVERSIBLE_ENGINEERING",
        "member_consent_receipt_ref": member_receipt,
        "total_field_receipt_ref": tf_receipt,
        "nonce_consumption_evidence_ref": nonce_ev,
        "member_consent_authority": "member",
        "safety_and_landing_authority": "total_field_verifier",
        "process_authority": "odoo",
        "candidate_authority": "none",
    }
    gate_result = {
        "state": "PASS",
        "reason_code": "PASS_P3_SESSION_DUAL_RECEIPT_9107_GATE_CANDIDATE",
        "candidate_only": True,
        "generic_gateway_ready": True,
        "runtime_released": False,
        "action_executed": False,
        "member_consent_authority": "member",
        "safety_and_landing_authority": "total_field_verifier",
        "process_authority": "odoo",
        "candidate_authority": "none",
        "gate_ref": "member_action_gate_ref:sha256:" + canonical_sha256(gate_material),
        "gate_material": gate_material,
    }
    request = {
        "member_ref": natural,
        "identity_root_ref": root,
        "root_generation": 1,
        "revocation_epoch": 0,
        "p1_identity_candidate": {
            "derived_packets_evidence": {
                "payload": {
                    "role_seat": {
                        "payload": {
                            "organization_ref": organization,
                            "seat_ref": seat,
                            "role_ref": role,
                        }
                    }
                }
            }
        },
        "session": {
            "session_ref": session,
            "scope_refs": scope,
            "effect_class": "REVERSIBLE_ENGINEERING",
            "issued_at_epoch": 100,
            "expires_at_epoch": 200,
        },
        "scene": {
            "scene_ref": scene,
            "scope_refs": scope,
            "effect_class": "REVERSIBLE_ENGINEERING",
        },
        "action": {
            "action_hash": action_hash,
            "purpose_ref": purpose,
            "scope_refs": scope,
            "effect_class": "REVERSIBLE_ENGINEERING",
        },
        "member_consent_receipt": {
            "receipt_ref": member_receipt,
            "receipt_state": "CONSENT",
            "authority": "member",
        },
        "total_field_receipt": {
            "receipt_ref": tf_receipt,
            "receipt_state": "PASS",
            "authority": "total_field_verifier",
        },
    }
    return {"request": request, "gate": gate_result}


class MemberSovereignContextAdapterTest(unittest.TestCase):
    def build(self):
        f = request_fixture()
        contract = build_member_sovereign_context_candidate(
            member_action_request=f["request"],
            verified_gate_result=f["gate"],
            organization_request_ref=ref("organization_request", "req1"),
            audit_ref=ref("audit", "t011a"),
            allowed_capability_refs=[
                ref("capability", "local-llm"),
                ref("capability", "candidate-return"),
            ],
        )
        return f, contract

    def test_builds_ref_only_member_sovereign_context(self):
        f, c = self.build()
        self.assertEqual(c["state"], "PASS_MEMBER_SOVEREIGN_CONTEXT_CANDIDATE")
        self.assertTrue(c["candidate_only"])
        self.assertFalse(c["runtime_effect"])
        coord = c["member_coordinate"]
        self.assertNotEqual(coord["natural_person_ref"], coord["seat_ref"])
        sep = c["request_authorization_separation"]
        self.assertFalse(sep["organization_request_is_member_authorization"])
        self.assertEqual(sep["member_authorization_authority"], "member")
        self.assertEqual(c["data_boundary"]["model_visible_member_data"], "OPAQUE_REFERENCES_ONLY")
        self.assertEqual(c["authority_route"]["formal_effect_route"], "EXISTING_TAIJI01_TOTAL_FIELD")

    def test_projects_into_existing_dynamic_context_contract(self):
        _, c = self.build()
        context = build_member_model_visible_context(c)
        self.assertEqual(validate_model_visible_context(context), context)
        projection = context["state_projection"]["member_sovereign_context"]
        self.assertEqual(projection["source_context_sha256"], c["context_sha256"])
        encoded = str(context).lower()
        self.assertNotIn("member_plaintext", encoded)
        self.assertNotIn("private_key", encoded)
        self.assertNotIn("bearer ", encoded)

    def test_no_second_authority_system_is_created(self):
        _, c = self.build()
        for field in (
            "second_identity_root_created",
            "second_8d_created",
            "second_d8_created",
            "second_gst_created",
            "second_total_field_created",
        ):
            self.assertFalse(c[field])
        self.assertEqual(c["authority_route"]["candidate_authority"], "NONE")
        self.assertEqual(c["authority_route"]["model_authority"], "NONE")

    def test_gate_request_binding_drift_holds(self):
        f = request_fixture()
        bad = copy.deepcopy(f["gate"])
        bad["gate_material"]["scope_refs"] = [ref("scope", "wrong")]
        bad["gate_ref"] = "member_action_gate_ref:sha256:" + canonical_sha256(bad["gate_material"])
        with self.assertRaisesRegex(
            MemberSovereignContextHold,
            "HOLD_MEMBER_GATE_REQUEST_BINDING_MISMATCH",
        ):
            build_member_sovereign_context_candidate(
                member_action_request=f["request"],
                verified_gate_result=bad,
                organization_request_ref=ref("organization_request", "req1"),
                audit_ref=ref("audit", "t011a"),
                allowed_capability_refs=[],
            )

    def test_legal_basis_path_is_modeled_but_not_invented(self):
        f = request_fixture()
        with self.assertRaisesRegex(
            MemberSovereignContextHold,
            "HOLD_LEGAL_BASIS_VERIFIER_NOT_BOUND",
        ):
            build_member_sovereign_context_candidate(
                member_action_request=f["request"],
                verified_gate_result=f["gate"],
                organization_request_ref=ref("organization_request", "req1"),
                audit_ref=ref("audit", "t011a"),
                allowed_capability_refs=[],
                authority_basis_mode="LEGAL_BASIS",
                legal_basis_ref=ref("legal_basis", "law1"),
                legal_basis_verification_ref=ref("legal_basis_verification", "law1"),
            )

    def test_identity_cannot_collapse_into_seat(self):
        f = request_fixture()
        bad = copy.deepcopy(f["request"])
        bad["p1_identity_candidate"]["derived_packets_evidence"]["payload"]["role_seat"]["payload"]["seat_ref"] = bad["member_ref"]
        with self.assertRaisesRegex(
            MemberSovereignContextHold,
            "HOLD_IDENTITY_SEAT_OR_ORGANIZATION_COLLAPSE",
        ):
            build_member_sovereign_context_candidate(
                member_action_request=bad,
                verified_gate_result=f["gate"],
                organization_request_ref=ref("organization_request", "req1"),
                audit_ref=ref("audit", "t011a"),
                allowed_capability_refs=[],
            )


if __name__ == "__main__":
    unittest.main()
