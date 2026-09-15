from __future__ import annotations

import copy
from unittest.mock import Mock, patch

from tools.total_field.w7tp_intent_field_suite import (
    founder_identity_evidence_provider as provider,
)
from tools.total_field.w7tp_intent_field_suite import (
    member_sovereign_identity as p1,
)


P0 = p1._P0


def _p1_evidence(field, payload):
    payload_sha256 = P0.sha256_json(payload)
    kind = p1.EVIDENCE_KIND_BY_FIELD[field]
    return {
        "schema_version": p1.EVIDENCE_SCHEMA_VERSION,
        "evidence_ref": f"{kind}_ref:sha256:{payload_sha256}",
        "payload_sha256": payload_sha256,
        "payload": payload,
    }


def _provider_evidence(kind, payload):
    payload_sha256 = P0.sha256_json(payload)
    return {
        "schema_version": provider.PROVIDER_EVIDENCE_SCHEMA_VERSION,
        "evidence_ref": f"{kind}_ref:sha256:{payload_sha256}",
        "payload_sha256": payload_sha256,
        "payload": payload,
    }


def _root_registry_entry(root, *, current):
    return {
        "identity_root_ref": root["identity_root_ref"],
        "root_packet_ref": root["root_packet_ref"],
        "subject_binding_ref": root["subject_binding_ref"],
        "root_generation": root["root_generation"],
        "revocation_epoch": root["revocation_epoch"],
        "current": current,
    }


def _p1_candidate(label="founder-member"):
    previous_root = P0.synthetic_root(label, generation=1)
    previous_root["root_state"] = "SUPERSEDED_CANDIDATE"
    previous_root = P0.seal_content(previous_root)
    current_root = P0.synthetic_root(label, generation=2)
    root_registry = P0.synthetic_root_registry(current_root)
    root_registry["entries"].insert(
        0, _root_registry_entry(previous_root, current=False)
    )
    proof_registry = P0.synthetic_proof_registry(current_root)
    proof_registry["proofs"].update(
        P0.synthetic_proof_registry(previous_root)["proofs"]
    )
    packets = P0.synthetic_derived_packets(current_root)
    role_seat_registry = P0.synthetic_role_seat_registry(
        current_root, packets["role_seat"]
    )
    dual_receipt = P0.synthetic_dual_receipt(
        current_root, packets["consent"]["action_binding"]
    )
    payloads = {
        "root_chain_evidence": {"roots": [previous_root, current_root]},
        "root_registry_evidence": root_registry,
        "proof_registry_evidence": proof_registry,
        "derived_packets_evidence": packets,
        "role_seat_registry_evidence": role_seat_registry,
        "nonce_replay_evidence": {"derived_seen": [], "receipt_seen": []},
        "dual_receipt_evidence": dual_receipt,
        "member_proof_registry_evidence": P0.synthetic_member_proof_registry(
            current_root, dual_receipt
        ),
        "verification_context_evidence": {"observed_at": P0.FIXED_NOW},
    }
    return {
        field: _p1_evidence(field, payload)
        for field, payload in payloads.items()
    }


def _snapshot(label="founder-member"):
    candidate = _p1_candidate(label)
    root = candidate["root_chain_evidence"]["payload"]["roots"][-1]
    registry = candidate["root_registry_evidence"]
    role_seat = candidate["derived_packets_evidence"]["payload"]["role_seat"]
    role_payload = role_seat["payload"]
    transmission = role_seat["generative_transmission"]
    cardinality = sum(
        entry.get("current") is True
        and entry.get("subject_binding_ref") == root["subject_binding_ref"]
        for entry in registry["payload"]["entries"]
    )
    return {
        "registry_coordinate": provider.REGISTRY_COORDINATE,
        "p1_candidate": candidate,
        "current_root_registry_cardinality_evidence": _provider_evidence(
            "current_root_registry_cardinality_evidence",
            {
                "registry_coordinate": provider.REGISTRY_COORDINATE,
                "registry_ref": registry["payload"]["registry_ref"],
                "root_registry_snapshot_sha256": registry["payload_sha256"],
                "cardinality": cardinality,
            },
        ),
        "8d_adi_binding_evidence": _provider_evidence(
            "8d_adi_binding_evidence",
            {
                "registry_coordinate": provider.REGISTRY_COORDINATE,
                "identity_root_ref": root["identity_root_ref"],
                "role_seat_ref": role_payload["role_seat_ref"],
                "protocol": transmission["protocol"],
                "state_packet_ref": transmission["state_packet_ref"],
                "total_field_verify_ref": transmission[
                    "total_field_verify_ref"
                ],
                "adi_binding_ref": P0.ref("adi_binding_ref", label),
                "receipt_ref": P0.ref(
                    "founder_identity_binding_receipt_ref", label
                ),
            },
        ),
    }


def _rebind_root_registry(snapshot):
    candidate = snapshot["p1_candidate"]
    candidate["root_registry_evidence"] = _p1_evidence(
        "root_registry_evidence",
        candidate["root_registry_evidence"]["payload"],
    )
    registry = candidate["root_registry_evidence"]
    root = candidate["root_chain_evidence"]["payload"]["roots"][-1]
    cardinality = sum(
        entry.get("current") is True
        and entry.get("subject_binding_ref") == root["subject_binding_ref"]
        for entry in registry["payload"]["entries"]
    )
    snapshot["current_root_registry_cardinality_evidence"] = (
        _provider_evidence(
            "current_root_registry_cardinality_evidence",
            {
                "registry_coordinate": provider.REGISTRY_COORDINATE,
                "registry_ref": registry["payload"]["registry_ref"],
                "root_registry_snapshot_sha256": registry["payload_sha256"],
                "cardinality": cardinality,
            },
        )
    )


def test_complete_snapshot_calls_p1_once_and_returns_refs_only():
    snapshot = _snapshot()
    before = copy.deepcopy(snapshot)
    reader = Mock(return_value=snapshot)
    with patch.object(
        provider,
        "verify_member_sovereign_identity_candidate",
        wraps=p1.verify_member_sovereign_identity_candidate,
    ) as verify:
        result = provider.ReadOnlyFounderIdentityEvidenceProviderCandidate(
            reader
        ).collect_and_verify()
    assert result["state"] == "PASS"
    assert result["root_registry_cardinality"] == 1
    assert result["candidate_only"] is True
    assert result["second_registry_created"] is False
    assert result["member_plaintext_read"] is False
    assert result["p1_verifier_result"]["state"] == "PASS"
    assert reader.call_args.args == (provider.REGISTRY_COORDINATE,)
    assert verify.call_count == 1
    assert snapshot == before
    assert set(result) == {
        "state",
        "reason_code",
        "candidate_only",
        "provider_id",
        "registry_coordinate",
        "root_registry_cardinality",
        "founder_role_seat_ref",
        "founder_identity_root_ref",
        "founder_identity_binding_receipt_ref",
        "8d_adi_binding_evidence_ref",
        "current_root_registry_cardinality_evidence_ref",
        "p1_verifier_result",
        "second_registry_created",
        "member_plaintext_read",
    }


def test_unconfigured_or_zero_cardinality_holds_without_p1_call():
    missing_reader = Mock(return_value=None)
    missing = provider.ReadOnlyFounderIdentityEvidenceProviderCandidate(
        missing_reader
    ).collect_and_verify()
    assert missing["reason_code"] == "HOLD_REGISTRY_NOT_CONFIGURED"

    snapshot = _snapshot()
    snapshot["p1_candidate"]["root_registry_evidence"]["payload"][
        "entries"
    ] = []
    _rebind_root_registry(snapshot)
    with patch.object(
        provider, "verify_member_sovereign_identity_candidate"
    ) as verify:
        result = provider.ReadOnlyFounderIdentityEvidenceProviderCandidate(
            Mock(return_value=snapshot)
        ).collect_and_verify()
    assert result["reason_code"] == "HOLD_ROOT_REGISTRY_EMPTY"
    assert result["root_registry_cardinality"] == 0
    verify.assert_not_called()


def test_second_current_root_holds_without_creating_registry():
    snapshot = _snapshot()
    registry = snapshot["p1_candidate"]["root_registry_evidence"]["payload"]
    registry["entries"].append(copy.deepcopy(registry["entries"][-1]))
    _rebind_root_registry(snapshot)
    with patch.object(
        provider, "verify_member_sovereign_identity_candidate"
    ) as verify:
        result = provider.ReadOnlyFounderIdentityEvidenceProviderCandidate(
            Mock(return_value=snapshot)
        ).collect_and_verify()
    assert result["reason_code"] == "HOLD_SECOND_IDENTITY_ROOT"
    assert result["root_registry_cardinality"] == 2
    assert result["second_registry_created"] is False
    verify.assert_not_called()


def test_member_plaintext_key_is_rejected_before_p1():
    snapshot = _snapshot()
    snapshot["email"] = "private-fixture@example.invalid"
    with patch.object(
        provider, "verify_member_sovereign_identity_candidate"
    ) as verify:
        result = provider.ReadOnlyFounderIdentityEvidenceProviderCandidate(
            Mock(return_value=snapshot)
        ).collect_and_verify()
    assert result["reason_code"] == "HOLD_MEMBER_PLAINTEXT_BOUNDARY"
    assert result["member_plaintext_read"] is False
    verify.assert_not_called()


def test_missing_8d_adi_binding_holds_before_p1():
    snapshot = _snapshot()
    del snapshot["8d_adi_binding_evidence"]
    with patch.object(
        provider, "verify_member_sovereign_identity_candidate"
    ) as verify:
        result = provider.ReadOnlyFounderIdentityEvidenceProviderCandidate(
            Mock(return_value=snapshot)
        ).collect_and_verify()
    assert result["reason_code"] == "HOLD_8D_ADI_BINDING_NOT_EVIDENCED"
    verify.assert_not_called()


def test_registry_coordinate_mismatch_holds_before_p1():
    snapshot = _snapshot()
    snapshot["registry_coordinate"] = "odoo18://second-registry"
    with patch.object(
        provider, "verify_member_sovereign_identity_candidate"
    ) as verify:
        result = provider.ReadOnlyFounderIdentityEvidenceProviderCandidate(
            Mock(return_value=snapshot)
        ).collect_and_verify()
    assert result["reason_code"] == "HOLD_REGISTRY_COORDINATE_MISMATCH"
    assert result["second_registry_created"] is False
    verify.assert_not_called()
