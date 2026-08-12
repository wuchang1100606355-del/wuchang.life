from __future__ import annotations

import copy

import pytest

from tools.total_field.w7tp_intent_field_suite import (
    member_sovereign_identity as verifier,
)


P0 = verifier._P0


def evidence(field, payload):
    payload_sha256 = P0.sha256_json(payload)
    kind = verifier.EVIDENCE_KIND_BY_FIELD[field]
    return {
        "schema_version": verifier.EVIDENCE_SCHEMA_VERSION,
        "evidence_ref": f"{kind}_ref:sha256:{payload_sha256}",
        "payload_sha256": payload_sha256,
        "payload": payload,
    }


def rebind(candidate, field):
    candidate[field] = evidence(field, candidate[field]["payload"])


def root_registry_entry(root, *, current):
    return {
        "identity_root_ref": root["identity_root_ref"],
        "root_packet_ref": root["root_packet_ref"],
        "subject_binding_ref": root["subject_binding_ref"],
        "root_generation": root["root_generation"],
        "revocation_epoch": root["revocation_epoch"],
        "current": current,
    }


def build_candidate(
    label="member-one",
    *,
    member_decision="CONSENT",
    general_member_role=False,
):
    previous_root = P0.synthetic_root(label, generation=1)
    previous_root["root_state"] = "SUPERSEDED_CANDIDATE"
    previous_root = P0.seal_content(previous_root)
    current_root = P0.synthetic_root(label, generation=2)

    root_registry = P0.synthetic_root_registry(current_root)
    root_registry["entries"].insert(
        0, root_registry_entry(previous_root, current=False)
    )
    proof_registry = P0.synthetic_proof_registry(current_root)
    proof_registry["proofs"].update(
        P0.synthetic_proof_registry(previous_root)["proofs"]
    )

    packets = P0.synthetic_derived_packets(current_root)
    if general_member_role:
        role_seat = copy.deepcopy(packets["role_seat"])
        role_seat["payload"]["role_ref"] = P0.ref(
            "role_ref", f"{label}:general-member-role"
        )
        role_seat["payload"]["seat_ref"] = P0.ref(
            "seat_ref", f"{label}:general-member-seat"
        )
        role_seat["payload"]["seat_lease_cas_ref"] = P0.ref(
            "seat_lease_cas_ref", f"{label}:general-member-seat-cas"
        )
        packets["role_seat"] = P0.seal_content(role_seat)
    role_seat_registry = P0.synthetic_role_seat_registry(
        current_root, packets["role_seat"]
    )

    dual_receipt = P0.synthetic_dual_receipt(
        current_root,
        packets["consent"]["action_binding"],
        member_decision=member_decision,
    )
    member_proof_registry = P0.synthetic_member_proof_registry(
        current_root, dual_receipt
    )
    payloads = {
        "root_chain_evidence": {
            "roots": [previous_root, current_root],
        },
        "root_registry_evidence": root_registry,
        "proof_registry_evidence": proof_registry,
        "derived_packets_evidence": packets,
        "role_seat_registry_evidence": role_seat_registry,
        "nonce_replay_evidence": {
            "derived_seen": [],
            "receipt_seen": [],
        },
        "dual_receipt_evidence": dual_receipt,
        "member_proof_registry_evidence": member_proof_registry,
        "verification_context_evidence": {
            "observed_at": P0.FIXED_NOW,
        },
    }
    return {field: evidence(field, payload) for field, payload in payloads.items()}


def verify(candidate):
    return verifier.verify_member_sovereign_identity_candidate(candidate)


def test_p0_hash_binding_is_exact():
    assert verifier.verify_p0_hash_binding() == {
        "p0_content_sha256": verifier.P0_CONTENT_SHA256,
        "p0_manifest_sha256": verifier.P0_MANIFEST_SHA256,
    }


def test_complete_hash_bound_candidate_passes_without_mutation():
    candidate = build_candidate()
    before = copy.deepcopy(candidate)
    assert verify(candidate) == {
        "state": "PASS",
        "reason_code": "PASS_P1_READ_ONLY_VERIFIER_CANDIDATE",
        "candidate_only": True,
        "p0_content_sha256": verifier.P0_CONTENT_SHA256,
        "p0_manifest_sha256": verifier.P0_MANIFEST_SHA256,
    }
    assert candidate == before


def test_member_denial_returns_block_candidate():
    result = verify(build_candidate(member_decision="DENY"))
    assert result["state"] == "BLOCK"
    assert result["reason_code"] == "BLOCK_MEMBER_OR_TOTAL_FIELD_DECISION"


@pytest.mark.parametrize("field", tuple(verifier.EVIDENCE_KIND_BY_FIELD))
def test_every_missing_snapshot_registry_or_evidence_holds_not_evidenced(field):
    candidate = build_candidate()
    del candidate[field]
    result = verify(candidate)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_NOT_EVIDENCED"


def test_evidence_payload_tamper_without_hash_rebind_holds():
    candidate = build_candidate()
    candidate["root_registry_evidence"]["payload"]["entries"][0][
        "current"
    ] = True
    result = verify(candidate)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_EVIDENCE_HASH_MISMATCH"


def test_broken_root_version_link_holds():
    candidate = build_candidate()
    roots = candidate["root_chain_evidence"]["payload"]["roots"]
    roots[-1]["previous_root_packet_ref"] = P0.ref(
        "member_root_packet_ref", "wrong-previous-root"
    )
    roots[-1] = P0.seal_content(roots[-1])
    rebind(candidate, "root_chain_evidence")
    result = verify(candidate)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_ROOT_CHAIN_LINK_MISMATCH"


def test_revocation_epoch_regression_holds():
    candidate = build_candidate()
    roots = candidate["root_chain_evidence"]["payload"]["roots"]
    roots[0]["revocation_epoch"] = roots[-1]["revocation_epoch"] + 1
    roots[0] = P0.seal_content(roots[0])
    registry_entries = candidate["root_registry_evidence"]["payload"]["entries"]
    registry_entries[0]["revocation_epoch"] = roots[0]["revocation_epoch"]
    rebind(candidate, "root_chain_evidence")
    rebind(candidate, "root_registry_evidence")
    result = verify(candidate)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_ROOT_REVOCATION_EPOCH_REGRESSION"


def test_missing_bound_registry_record_holds_not_evidenced():
    candidate = build_candidate()
    candidate["root_registry_evidence"]["payload"]["entries"].pop(0)
    rebind(candidate, "root_registry_evidence")
    result = verify(candidate)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_NOT_EVIDENCED"


def test_missing_bound_proof_ref_holds_not_evidenced():
    candidate = build_candidate()
    previous_root = candidate["root_chain_evidence"]["payload"]["roots"][0]
    del candidate["proof_registry_evidence"]["payload"]["proofs"][
        previous_root["member_verification_proof_ref"]
    ]
    rebind(candidate, "proof_registry_evidence")
    result = verify(candidate)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_NOT_EVIDENCED"


def test_expired_derived_packet_ttl_holds():
    candidate = build_candidate()
    candidate["verification_context_evidence"]["payload"][
        "observed_at"
    ] = "2026-07-25T00:11:00Z"
    rebind(candidate, "verification_context_evidence")
    result = verify(candidate)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_DERIVED_PACKET_TIME_INVALID"


def test_previously_seen_derived_nonce_holds_replay():
    candidate = build_candidate()
    session = candidate["derived_packets_evidence"]["payload"]["session"]
    candidate["nonce_replay_evidence"]["payload"]["derived_seen"].append(
        {
            "replay_domain_ref": session["replay_domain_ref"],
            "nonce_ref": session["nonce_ref"],
        }
    )
    rebind(candidate, "nonce_replay_evidence")
    result = verify(candidate)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_DERIVED_PACKET_REPLAY"


def test_previously_seen_receipt_nonce_holds_replay():
    candidate = build_candidate()
    member = candidate["dual_receipt_evidence"]["payload"]["member_receipt"]
    candidate["nonce_replay_evidence"]["payload"]["receipt_seen"].append(
        {
            "authority": member["authority"],
            "nonce_ref": member["nonce_ref"],
        }
    )
    rebind(candidate, "nonce_replay_evidence")
    result = verify(candidate)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_RECEIPT_REPLAY"


def test_role_seat_snapshot_mismatch_holds():
    candidate = build_candidate()
    candidate["role_seat_registry_evidence"]["payload"][
        "seat_lease_cas_ref"
    ] = P0.ref("seat_lease_cas_ref", "wrong-seat-cas")
    rebind(candidate, "role_seat_registry_evidence")
    result = verify(candidate)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_SEAT_LEASE_RACE"


def test_scope_expansion_outside_action_hash_holds():
    candidate = build_candidate()
    packets = candidate["derived_packets_evidence"]["payload"]
    packets["scene"]["payload"]["scope_refs"].append(
        P0.ref("scope_ref", "unbound-expanded-scope")
    )
    packets["scene"] = P0.seal_content(packets["scene"])
    rebind(candidate, "derived_packets_evidence")
    result = verify(candidate)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_ACTION_SCOPE_MISMATCH"


def test_effect_class_replacement_outside_action_hash_holds():
    candidate = build_candidate()
    packets = candidate["derived_packets_evidence"]["payload"]
    packets["scene"]["action_binding"]["effect_class"] = "E5_HIGH_IMPACT"
    packets["scene"] = P0.seal_content(packets["scene"])
    rebind(candidate, "derived_packets_evidence")
    result = verify(candidate)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_ACTION_HASH_MISMATCH"


@pytest.mark.parametrize(
    ("receipt_name", "field", "replacement", "expected_code"),
    [
        (
            "member_receipt",
            "purpose_ref",
            P0.ref("purpose_ref", "other-member-purpose"),
            "HOLD_PURPOSE_REF_MISMATCH",
        ),
        (
            "total_field_receipt",
            "purpose_ref",
            P0.ref("purpose_ref", "other-total-field-purpose"),
            "HOLD_PURPOSE_REF_MISMATCH",
        ),
        (
            "member_receipt",
            "scope_refs",
            [P0.ref("scope_ref", "other-member-scope")],
            "HOLD_SCOPE_REFS_MISMATCH",
        ),
        (
            "total_field_receipt",
            "scope_refs",
            [P0.ref("scope_ref", "other-total-field-scope")],
            "HOLD_SCOPE_REFS_MISMATCH",
        ),
        (
            "member_receipt",
            "effect_class",
            "E5_HIGH_IMPACT",
            "HOLD_EFFECT_CLASS_MISMATCH",
        ),
        (
            "total_field_receipt",
            "effect_class",
            "E5_HIGH_IMPACT",
            "HOLD_EFFECT_CLASS_MISMATCH",
        ),
    ],
)
def test_either_dual_receipt_basis_mismatch_holds(
    receipt_name, field, replacement, expected_code
):
    candidate = build_candidate()
    dual = candidate["dual_receipt_evidence"]["payload"]
    dual[receipt_name][field] = replacement
    dual[receipt_name] = P0.seal_receipt(dual[receipt_name])
    candidate["dual_receipt_evidence"]["payload"] = P0.seal_content(dual)
    rebind(candidate, "dual_receipt_evidence")
    result = verify(candidate)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == expected_code


def test_founder_and_general_member_share_root_contract():
    founder = build_candidate("founder-member")
    general = build_candidate(
        "general-member", general_member_role=True
    )
    assert verify(founder)["state"] == "PASS"
    assert verify(general)["state"] == "PASS"
    founder_root = founder["root_chain_evidence"]["payload"]["roots"][-1]
    general_root = general["root_chain_evidence"]["payload"]["roots"][-1]
    assert founder_root["schema_version"] == general_root["schema_version"]
    assert founder_root["root_policy"] == general_root["root_policy"]
    assert "role_ref" not in founder_root
    assert "seat_ref" not in founder_root
    assert (
        founder["derived_packets_evidence"]["payload"]["role_seat"]["payload"][
            "role_ref"
        ]
        != general["derived_packets_evidence"]["payload"]["role_seat"][
            "payload"
        ]["role_ref"]
    )


def test_role_embedding_in_root_holds_schema():
    candidate = build_candidate()
    root = candidate["root_chain_evidence"]["payload"]["roots"][-1]
    root["role_ref"] = P0.ref("role_ref", "embedded-founder-role")
    rebind(candidate, "root_chain_evidence")
    result = verify(candidate)
    assert result["state"] == "HOLD"
    assert result["reason_code"] == "HOLD_SCHEMA_INVALID"


def test_output_contract_is_candidate_state_only():
    for candidate in (
        build_candidate(),
        build_candidate(member_decision="DENY"),
        None,
    ):
        result = verify(candidate)
        assert result["state"] in {"PASS", "HOLD", "BLOCK"}
        assert set(result) == {
            "state",
            "reason_code",
            "candidate_only",
            "p0_content_sha256",
            "p0_manifest_sha256",
        }
        assert result["candidate_only"] is True
