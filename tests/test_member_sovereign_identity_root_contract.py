from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = (
    ROOT / "scripts/verify/verify_member_sovereign_identity_root_contract.py"
)
SPEC = importlib.util.spec_from_file_location(
    "verify_member_sovereign_identity_root_contract",
    VERIFIER_PATH,
)
assert SPEC is not None and SPEC.loader is not None
verifier = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = verifier
SPEC.loader.exec_module(verifier)


@pytest.fixture()
def schemas():
    return verifier.check_schemas()


@pytest.fixture()
def root_packet():
    return verifier.synthetic_root()


@pytest.fixture()
def derived_packets(root_packet):
    return verifier.synthetic_derived_packets(root_packet)


def verify_derived_candidate(
    packet,
    root_packet,
    *,
    seen_nonces=None,
    role_seat_registry=None,
):
    return verifier.verify_derived_packet(
        packet,
        root_packet,
        root_registry_snapshot=verifier.synthetic_root_registry(root_packet),
        proof_registry_snapshot=verifier.synthetic_proof_registry(root_packet),
        seen_nonces=set() if seen_nonces is None else seen_nonces,
        role_seat_registry_snapshot=role_seat_registry,
    )


def verify_derived_chain_candidate(packets, root_packet):
    return verifier.verify_derived_chain(
        packets,
        root_packet,
        root_registry_snapshot=verifier.synthetic_root_registry(root_packet),
        proof_registry_snapshot=verifier.synthetic_proof_registry(root_packet),
        role_seat_registry_snapshot=verifier.synthetic_role_seat_registry(
            root_packet, packets["role_seat"]
        ),
    )


def verify_dual_candidate(
    packet,
    root_packet,
    *,
    seen_nonces=None,
    member_proof_registry=None,
):
    return verifier.verify_dual_receipt(
        packet,
        root_packet,
        root_registry_snapshot=verifier.synthetic_root_registry(root_packet),
        proof_registry_snapshot=verifier.synthetic_proof_registry(root_packet),
        member_proof_registry_snapshot=(
            verifier.synthetic_member_proof_registry(root_packet, packet)
            if member_proof_registry is None
            else member_proof_registry
        ),
        seen_nonces=set() if seen_nonces is None else seen_nonces,
    )


def test_three_p0_schemas_are_draft_2020_12_and_closed(schemas):
    assert set(schemas) == {"root", "derived", "dual_receipt"}

    def assert_explicit_objects_are_closed(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False
            for value in node.values():
                assert_explicit_objects_are_closed(value)
        elif isinstance(node, list):
            for value in node:
                assert_explicit_objects_are_closed(value)

    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["additionalProperties"] is False
        assert_explicit_objects_are_closed(schema)


def test_three_p0_schemas_reuse_one_action_basis_type_set(schemas):
    expected_effect_classes = [
        "E0_ANSWER",
        "E1_READ",
        "E2_CANDIDATE",
        "E3_SANDBOX",
        "E4_REVERSIBLE_WRITE",
        "E5_HIGH_IMPACT",
    ]
    canonical_defs = schemas["derived"]["$defs"]
    for schema in schemas.values():
        assert schema["$defs"]["purpose_ref"] == canonical_defs["purpose_ref"]
        assert schema["$defs"]["scope_refs"] == canonical_defs["scope_refs"]
        assert schema["$defs"]["effect_class"] == canonical_defs["effect_class"]
    assert canonical_defs["effect_class"]["enum"] == expected_effect_classes


def test_root_is_candidate_non_bearer_with_exact_authorities(
    schemas, root_packet
):
    verifier.validate_instance(schemas["root"], root_packet)
    assert root_packet["authority_model"] == {
        "member_consent_authority": "member",
        "safety_and_landing_authority": "total_field_verifier",
        "process_authority": "odoo",
        "candidate_authority": "none",
    }
    assert root_packet["candidate_only"] is True
    assert root_packet["runtime_enabled"] is False
    assert root_packet["formal_execution_authority"] is False
    assert root_packet["authority_granted"] is False
    assert root_packet["bearer_authority"] is False
    assert root_packet["root_policy"]["possession_conveys_authority"] is False
    assert root_packet["root_policy"]["permanent_roles_in_root"] is False
    assert root_packet["root_policy"]["permanent_scopes_in_root"] is False


def test_root_v1_and_rotated_generation_previous_ref_rules(schemas):
    first = verifier.synthetic_root(generation=1)
    second = verifier.synthetic_root(generation=2)
    verifier.validate_instance(schemas["root"], first)
    verifier.validate_instance(schemas["root"], second)
    assert first["previous_root_packet_ref"] is None
    assert second["previous_root_packet_ref"] == verifier.ref(
        "member_root_packet_ref", "member-one:root-generation:1"
    )

    invalid_first = copy.deepcopy(first)
    invalid_first["previous_root_packet_ref"] = verifier.ref(
        "member_root_packet_ref", "unexpected-previous"
    )
    with pytest.raises(ValidationError):
        verifier.validate_instance(schemas["root"], invalid_first)

    invalid_second = copy.deepcopy(second)
    invalid_second["previous_root_packet_ref"] = None
    with pytest.raises(ValidationError):
        verifier.validate_instance(schemas["root"], invalid_second)


def test_root_rejects_role_embedding_plaintext_shape_and_wrong_authority(
    schemas, root_packet
):
    mutations = [
        ("role_refs", [verifier.ref("role_ref", "founder")]),
        ("member_name", verifier.digest("synthetic-member-display")),
        (
            "session_ref",
            verifier.ref("member_session_ref", "root-must-not-be-session"),
        ),
    ]
    for key, value in mutations:
        invalid = copy.deepcopy(root_packet)
        invalid[key] = value
        with pytest.raises(ValidationError):
            verifier.validate_instance(schemas["root"], invalid)

    invalid = copy.deepcopy(root_packet)
    invalid["authority_model"]["member_consent_authority"] = (
        "total_field_verifier"
    )
    with pytest.raises(ValidationError):
        verifier.validate_instance(schemas["root"], invalid)


def test_root_requires_matching_registry_and_proof_evidence(root_packet):
    result = verifier.verify_root(
        root_packet,
        root_registry_snapshot=verifier.synthetic_root_registry(root_packet),
        proof_registry_snapshot=verifier.synthetic_proof_registry(root_packet),
    )
    assert result == {
        "state": "PASS_ROOT_CONTRACT_CANDIDATE",
        "authority_granted": False,
        "runtime_enabled": False,
    }

    with pytest.raises(verifier.ContractHold) as caught:
        verifier.verify_root(
            root_packet,
            root_registry_snapshot=verifier.synthetic_root_registry(root_packet),
            proof_registry_snapshot=None,
        )
    assert caught.value.code == "HOLD_ROOT_PROOF_NOT_EVIDENCED"


def test_all_six_derived_variants_are_schema_valid_and_candidate_only(
    schemas, root_packet, derived_packets
):
    assert {packet["packet_type"] for packet in derived_packets.values()} == {
        "MEMBER_SESSION",
        "MEMBER_SCENE",
        "MEMBER_CONSENT",
        "MEMBER_REVOCATION",
        "MEMBER_RECOVERY",
        "MEMBER_ROLE_SEAT_LEASE",
    }
    for packet in derived_packets.values():
        verifier.validate_instance(schemas["derived"], packet)
        assert packet["candidate_only"] is True
        assert packet["runtime_enabled"] is False
        assert packet["formal_execution_authority"] is False
        assert packet["authority_granted"] is False
        assert packet["root_packet_accepted_as_action_credential"] is False


def test_derived_chain_binds_root_subject_session_scene_and_scope(
    root_packet, derived_packets
):
    result = verify_derived_chain_candidate(derived_packets, root_packet)
    assert result["state"] == "PASS_DERIVED_CHAIN_CONTRACT_CANDIDATE"
    assert result["packet_count"] == 6
    assert result["authority_granted"] is False

    cross_member = copy.deepcopy(derived_packets["scene"])
    cross_member["subject_binding_ref"] = verifier.ref(
        "member_subject_binding_ref", "other-member"
    )
    cross_member = verifier.seal_content(cross_member)
    with pytest.raises(verifier.ContractHold) as caught:
        verify_derived_candidate(cross_member, root_packet)
    assert caught.value.code == "HOLD_DERIVED_ROOT_BINDING"


def test_action_hash_binds_complete_action_basis_and_normalizes_scope_set(
    derived_packets,
):
    action = derived_packets["consent"]["action_binding"]
    original_hash = verifier.action_hash(action)
    assert original_hash == action["action_hash"]
    assert {
        "root_ref",
        "root_generation",
        "session_ref",
        "scene_ref",
        "action_type",
        "target_ref",
        "parameters_sha256",
        "purpose_ref",
        "scope_refs",
        "resource_refs",
        "effect_class",
        "member_display_hash",
        "terms_version",
    } <= set(verifier.action_hash_basis(action))

    changed_display = copy.deepcopy(action)
    changed_display["member_display_hash"] = verifier.digest(
        "changed-member-display"
    )
    assert verifier.action_hash(changed_display) != original_hash

    changed_terms = copy.deepcopy(action)
    changed_terms["terms_version"] = "member-terms-v2"
    assert verifier.action_hash(changed_terms) != original_hash

    changed_subject = copy.deepcopy(action)
    changed_subject["subject_binding_ref"] = verifier.ref(
        "member_subject_binding_ref", "other-member"
    )
    assert verifier.action_hash(changed_subject) != original_hash

    changed_epoch = copy.deepcopy(action)
    changed_epoch["revocation_epoch"] += 1
    assert verifier.action_hash(changed_epoch) != original_hash

    changed_purpose = copy.deepcopy(action)
    changed_purpose["purpose_ref"] = verifier.ref(
        "purpose_ref", "changed-purpose"
    )
    assert verifier.action_hash(changed_purpose) != original_hash

    changed_effect = copy.deepcopy(action)
    changed_effect["effect_class"] = "E5_HIGH_IMPACT"
    assert verifier.action_hash(changed_effect) != original_hash

    scope_one = verifier.ref("scope_ref", "scope-one")
    scope_two = verifier.ref("scope_ref", "scope-two")
    first_order = copy.deepcopy(action)
    first_order["scope_refs"] = [scope_two, scope_one, scope_two]
    second_order = copy.deepcopy(action)
    second_order["scope_refs"] = [scope_one, scope_two]
    assert verifier.action_hash(first_order) == verifier.action_hash(second_order)


@pytest.mark.parametrize("field", ["purpose_ref", "scope_refs", "effect_class"])
def test_action_hash_basis_missing_field_is_schema_rejected(
    schemas, derived_packets, field
):
    invalid = copy.deepcopy(derived_packets["consent"])
    del invalid["action_binding"][field]
    with pytest.raises(ValidationError):
        verifier.validate_instance(schemas["derived"], invalid)


def test_wrong_purpose_scope_add_remove_and_effect_replacement_hold(
    root_packet, derived_packets
):
    wrong_purpose = copy.deepcopy(derived_packets["scene"])
    wrong_purpose["payload"]["purpose_ref"] = verifier.ref(
        "purpose_ref", "wrong-purpose"
    )
    wrong_purpose = verifier.seal_content(wrong_purpose)
    with pytest.raises(verifier.ContractHold) as caught:
        verify_derived_candidate(wrong_purpose, root_packet)
    assert caught.value.code == "HOLD_ACTION_PURPOSE_MISMATCH"

    scope_added = copy.deepcopy(derived_packets["scene"])
    scope_added["payload"]["scope_refs"].append(
        verifier.ref("scope_ref", "unbound-added-scope")
    )
    scope_added = verifier.seal_content(scope_added)
    with pytest.raises(verifier.ContractHold) as caught:
        verify_derived_candidate(scope_added, root_packet)
    assert caught.value.code == "HOLD_ACTION_SCOPE_MISMATCH"

    scope_removed = copy.deepcopy(derived_packets["scene"])
    second_scope = verifier.ref("scope_ref", "second-bound-scope")
    scope_removed["action_binding"]["scope_refs"].append(second_scope)
    scope_removed["action_binding"]["action_hash"] = verifier.action_hash(
        scope_removed["action_binding"]
    )
    scope_removed["payload"]["action_hash"] = scope_removed["action_binding"][
        "action_hash"
    ]
    scope_removed = verifier.seal_content(scope_removed)
    with pytest.raises(verifier.ContractHold) as caught:
        verify_derived_candidate(scope_removed, root_packet)
    assert caught.value.code == "HOLD_ACTION_SCOPE_MISMATCH"

    effect_replaced = copy.deepcopy(derived_packets["scene"])
    effect_replaced["action_binding"]["effect_class"] = "E5_HIGH_IMPACT"
    effect_replaced = verifier.seal_content(effect_replaced)
    with pytest.raises(verifier.ContractHold) as caught:
        verify_derived_candidate(effect_replaced, root_packet)
    assert caught.value.code == "HOLD_ACTION_HASH_MISMATCH"


def test_transaction_action_binds_amount_currency_and_target(
    schemas, derived_packets
):
    action = derived_packets["consent"]["action_binding"]
    assert action["action_class"] == "TRANSACTION"
    assert action["amount_currency_hash"] == verifier.amount_currency_hash(
        25900, "TWD", action["target_ref"]
    )
    assert verifier.amount_currency_hash(
        25901, "TWD", action["target_ref"]
    ) != action["amount_currency_hash"]
    assert verifier.amount_currency_hash(
        25900, "USD", action["target_ref"]
    ) != action["amount_currency_hash"]
    assert verifier.amount_currency_hash(
        25900, "TWD", verifier.ref("target_ref", "other-target")
    ) != action["amount_currency_hash"]

    missing_transaction_hash = copy.deepcopy(derived_packets["consent"])
    missing_transaction_hash["action_binding"]["amount_currency_hash"] = None
    with pytest.raises(ValidationError):
        verifier.validate_instance(
            schemas["derived"], missing_transaction_hash
        )

    non_transaction_with_hash = copy.deepcopy(derived_packets["session"])
    non_transaction_with_hash["action_binding"]["amount_currency_hash"] = (
        verifier.digest("unexpected-amount-currency")
    )
    with pytest.raises(ValidationError):
        verifier.validate_instance(
            schemas["derived"], non_transaction_with_hash
        )


def test_replay_revocation_and_recovery_fail_closed(
    root_packet, derived_packets
):
    seen: set[tuple[str, str]] = set()
    verify_derived_candidate(
        derived_packets["session"], root_packet, seen_nonces=seen
    )
    with pytest.raises(verifier.ContractHold) as caught:
        verify_derived_candidate(
            derived_packets["session"], root_packet, seen_nonces=seen
        )
    assert caught.value.code == "HOLD_DERIVED_PACKET_REPLAY"

    bad_revocation = copy.deepcopy(derived_packets["revocation"])
    bad_revocation["payload"]["previous_revocation_epoch"] = 1
    bad_revocation["payload"]["new_revocation_epoch"] = 1
    bad_revocation = verifier.seal_content(bad_revocation)
    with pytest.raises(verifier.ContractHold) as caught:
        verify_derived_candidate(bad_revocation, root_packet)
    assert caught.value.code == "HOLD_REVOCATION_EPOCH_RACE"

    bad_recovery = copy.deepcopy(derived_packets["recovery"])
    bad_recovery["payload"]["new_root_generation"] = (
        root_packet["root_generation"] + 2
    )
    bad_recovery = verifier.seal_content(bad_recovery)
    with pytest.raises(verifier.ContractHold) as caught:
        verify_derived_candidate(bad_recovery, root_packet)
    assert caught.value.code == "HOLD_RECOVERY_ROTATION_RACE"


def test_founder_role_is_short_lived_nontransferable_seat_projection(
    schemas, root_packet, derived_packets
):
    assert "role_ref" not in root_packet
    assert "seat_ref" not in root_packet
    seat = derived_packets["role_seat"]
    verifier.validate_instance(schemas["derived"], seat)
    assert seat["payload"]["transferable"] is False
    assert seat["payload"]["subdelegation_allowed"] is False
    assert (
        seat["payload"]["founder_role_requires_explicit_member_root_binding"]
        is True
    )
    assert seat["payload"]["atomic_seat_lease_required"] is True
    assert seat["payload"]["seat_lease_cas_ref"].startswith(
        "seat_lease_cas_ref:sha256:"
    )
    result = verify_derived_candidate(
        seat,
        root_packet,
        role_seat_registry=verifier.synthetic_role_seat_registry(
            root_packet, seat
        ),
    )
    assert result["state"] == "PASS_MEMBER_ROLE_SEAT_LEASE_CONTRACT_CANDIDATE"

    with pytest.raises(verifier.ContractHold) as caught:
        verify_derived_candidate(seat, root_packet)
    assert caught.value.code == "HOLD_ROLE_SEAT_REGISTRY_NOT_EVIDENCED"

    invalid = copy.deepcopy(seat)
    invalid["payload"]["transferable"] = True
    with pytest.raises(ValidationError):
        verifier.validate_instance(schemas["derived"], invalid)


def test_dual_receipt_requires_independent_member_total_field_and_odoo_roles(
    schemas, root_packet, derived_packets
):
    packet = verifier.synthetic_dual_receipt(
        root_packet, derived_packets["consent"]["action_binding"]
    )
    verifier.validate_instance(schemas["dual_receipt"], packet)
    assert packet["member_receipt"]["authority"] == "member"
    assert packet["total_field_receipt"]["authority"] == (
        "total_field_verifier"
    )
    assert packet["odoo_binding"]["authority"] == "odoo"
    assert packet["odoo_binding"]["not_authorization_receipt"] is True
    assert packet["authority_model"]["candidate_authority"] == "none"
    assert packet["aggregate_state"] == "READY_CANDIDATE"

    result = verify_dual_candidate(packet, root_packet)
    assert result == {
        "state": "PASS_DUAL_RECEIPT_READY_CANDIDATE",
        "candidate_only": True,
        "authority_granted": False,
        "runtime_enabled": False,
    }


@pytest.mark.parametrize(
    ("receipt_name", "field", "replacement", "expected_code"),
    [
        (
            "total_field_receipt",
            "action_hash",
            verifier.digest("other-action"),
            "HOLD_ACTION_HASH_RECEIPT_MISMATCH",
        ),
        (
            "total_field_receipt",
            "member_display_hash",
            verifier.digest("other-display"),
            "HOLD_MEMBER_DISPLAY_HASH_MISMATCH",
        ),
        (
            "member_receipt",
            "terms_version",
            "member-terms-v2",
            "HOLD_TERMS_VERSION_MISMATCH",
        ),
        (
            "member_receipt",
            "amount_currency_hash",
            verifier.digest("other-amount-currency"),
            "HOLD_AMOUNT_CURRENCY_HASH_MISMATCH",
        ),
        (
            "member_receipt",
            "purpose_ref",
            verifier.ref("purpose_ref", "other-member-purpose"),
            "HOLD_PURPOSE_REF_MISMATCH",
        ),
        (
            "total_field_receipt",
            "purpose_ref",
            verifier.ref("purpose_ref", "other-total-field-purpose"),
            "HOLD_PURPOSE_REF_MISMATCH",
        ),
        (
            "member_receipt",
            "scope_refs",
            [verifier.ref("scope_ref", "other-member-scope")],
            "HOLD_SCOPE_REFS_MISMATCH",
        ),
        (
            "total_field_receipt",
            "scope_refs",
            [verifier.ref("scope_ref", "other-total-field-scope")],
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
def test_dual_receipt_cross_commitment_mismatch_holds(
    root_packet,
    derived_packets,
    receipt_name,
    field,
    replacement,
    expected_code,
):
    packet = verifier.synthetic_dual_receipt(
        root_packet, derived_packets["consent"]["action_binding"]
    )
    packet[receipt_name][field] = replacement
    packet[receipt_name] = verifier.seal_receipt(packet[receipt_name])
    packet = verifier.seal_content(packet)
    with pytest.raises(verifier.ContractHold) as caught:
        verify_dual_candidate(packet, root_packet)
    assert caught.value.code == expected_code


def test_dual_receipt_rejects_cross_root_action_even_when_receipts_agree(
    root_packet, derived_packets
):
    packet = verifier.synthetic_dual_receipt(
        root_packet, derived_packets["consent"]["action_binding"]
    )
    other_root = verifier.synthetic_root("member-two")
    other_action = verifier.synthetic_action_binding(
        other_root,
        label="member-two:scene-action",
        session_ref=packet["session_ref"],
        scene_ref=packet["scene_ref"],
        transaction=True,
    )
    packet["action_binding"] = other_action
    for receipt_name in ("member_receipt", "total_field_receipt"):
        receipt = packet[receipt_name]
        for key in (
            "identity_root_ref",
            "root_packet_ref",
            "subject_binding_ref",
            "root_generation",
            "revocation_epoch",
            "action_hash",
            "purpose_ref",
            "scope_refs",
            "effect_class",
            "member_display_hash",
            "terms_version",
            "amount_currency_hash",
        ):
            receipt[key] = other_action[key]
        packet[receipt_name] = verifier.seal_receipt(receipt)
    packet["odoo_binding"]["action_hash"] = other_action["action_hash"]
    packet = verifier.seal_content(packet)

    with pytest.raises(verifier.ContractHold) as caught:
        verify_dual_candidate(packet, root_packet)
    assert caught.value.code == "HOLD_ACTION_ROOT_BINDING_MISMATCH"


def test_member_receipt_requires_matching_proof_registry(
    root_packet, derived_packets
):
    packet = verifier.synthetic_dual_receipt(
        root_packet, derived_packets["consent"]["action_binding"]
    )
    common = {
        "root_registry_snapshot": verifier.synthetic_root_registry(root_packet),
        "proof_registry_snapshot": verifier.synthetic_proof_registry(root_packet),
        "seen_nonces": set(),
    }
    with pytest.raises(verifier.ContractHold) as caught:
        verifier.verify_dual_receipt(
            packet,
            root_packet,
            member_proof_registry_snapshot=None,
            **common,
        )
    assert caught.value.code == "HOLD_MEMBER_PROOF_REGISTRY_NOT_EVIDENCED"

    invalid_registry = verifier.synthetic_member_proof_registry(
        root_packet, packet
    )
    invalid_registry["proofs"][packet["member_receipt"]["member_proof_ref"]][
        "action_hash"
    ] = verifier.digest("forged-action-proof")
    with pytest.raises(verifier.ContractHold) as caught:
        verify_dual_candidate(
            packet,
            root_packet,
            member_proof_registry=invalid_registry,
        )
    assert caught.value.code == "HOLD_MEMBER_RECEIPT_INVALID"


def test_candidate_verifiers_require_replay_evidence(
    root_packet, derived_packets
):
    with pytest.raises(verifier.ContractHold) as caught:
        verifier.verify_derived_packet(
            derived_packets["session"],
            root_packet,
            root_registry_snapshot=verifier.synthetic_root_registry(root_packet),
            proof_registry_snapshot=verifier.synthetic_proof_registry(root_packet),
            seen_nonces=None,
        )
    assert caught.value.code == "HOLD_REPLAY_LEDGER_NOT_EVIDENCED"

    dual = verifier.synthetic_dual_receipt(
        root_packet, derived_packets["consent"]["action_binding"]
    )
    with pytest.raises(verifier.ContractHold) as caught:
        verifier.verify_dual_receipt(
            dual,
            root_packet,
            root_registry_snapshot=verifier.synthetic_root_registry(root_packet),
            proof_registry_snapshot=verifier.synthetic_proof_registry(root_packet),
            member_proof_registry_snapshot=(
                verifier.synthetic_member_proof_registry(root_packet, dual)
            ),
            seen_nonces=None,
        )
    assert caught.value.code == "HOLD_REPLAY_LEDGER_NOT_EVIDENCED"


def test_every_authority_surface_is_const_rejected(
    schemas, derived_packets, root_packet
):
    wrong_derived = copy.deepcopy(derived_packets["scene"])
    wrong_derived["payload"]["issuing_process_authority"] = "member"
    with pytest.raises(ValidationError):
        verifier.validate_instance(schemas["derived"], wrong_derived)

    dual = verifier.synthetic_dual_receipt(
        root_packet, derived_packets["consent"]["action_binding"]
    )
    wrong_total_field = copy.deepcopy(dual)
    wrong_total_field["total_field_receipt"]["authority"] = "member"
    with pytest.raises(ValidationError):
        verifier.validate_instance(
            schemas["dual_receipt"], wrong_total_field
        )

    wrong_odoo = copy.deepcopy(dual)
    wrong_odoo["odoo_binding"]["authority"] = "member"
    with pytest.raises(ValidationError):
        verifier.validate_instance(schemas["dual_receipt"], wrong_odoo)


def test_total_field_pass_never_substitutes_for_member_consent(
    root_packet, derived_packets
):
    packet = verifier.synthetic_dual_receipt(
        root_packet,
        derived_packets["consent"]["action_binding"],
        member_decision="DENY",
        total_field_decision="PASS",
    )
    result = verify_dual_candidate(packet, root_packet)
    assert result["state"] == "BLOCK_MEMBER_OR_TOTAL_FIELD_DECISION"
    assert packet["aggregate_state"] == "BLOCK"
    assert result["authority_granted"] is False


def test_dual_receipt_missing_wrong_authority_and_replay_are_rejected(
    schemas, root_packet, derived_packets
):
    packet = verifier.synthetic_dual_receipt(
        root_packet, derived_packets["consent"]["action_binding"]
    )
    missing = copy.deepcopy(packet)
    del missing["member_receipt"]
    with pytest.raises(ValidationError):
        verifier.validate_instance(schemas["dual_receipt"], missing)

    wrong_authority = copy.deepcopy(packet)
    wrong_authority["member_receipt"]["authority"] = "odoo"
    with pytest.raises(ValidationError):
        verifier.validate_instance(schemas["dual_receipt"], wrong_authority)

    seen: set[tuple[str, str]] = set()
    verify_dual_candidate(packet, root_packet, seen_nonces=seen)
    with pytest.raises(verifier.ContractHold) as caught:
        verify_dual_candidate(packet, root_packet, seen_nonces=seen)
    assert caught.value.code == "HOLD_RECEIPT_REPLAY"


def test_raw_amount_currency_and_member_plaintext_shapes_are_rejected(
    schemas, root_packet, derived_packets
):
    dual = verifier.synthetic_dual_receipt(
        root_packet, derived_packets["consent"]["action_binding"]
    )
    for key in ("amount", "currency", "member_name", "provider_subject"):
        invalid = copy.deepcopy(dual)
        invalid[key] = verifier.digest(f"synthetic-forbidden:{key}")
        with pytest.raises(ValidationError):
            verifier.validate_instance(schemas["dual_receipt"], invalid)


def test_verifier_self_check_covers_contract_red_team_matrix():
    result = verifier.run_contract_self_check()
    assert result["state"] == "PASS_P0_SOURCE_CONTRACT_CANDIDATE"
    assert result["schema_count"] == 3
    assert result["derived_variant_count"] == 6
    assert result["red_team_case_count"] >= 30
    assert {item["result"] for item in result["red_team_results"]} == {
        "PASS"
    }
    assert result["candidate_only"] is True
    assert result["authority_granted"] is False
    assert result["runtime_enabled"] is False
    assert result["next_hold"] == "HOLD_P1_RUNTIME_VERIFIER_NOT_AUTHORIZED"


def test_sha256_manifest_is_exact_self_excluding_and_read_only():
    result = verifier.verify_manifest()
    assert result["state"] == "PASS_SHA256_MANIFEST"
    assert result["file_count"] == 5
