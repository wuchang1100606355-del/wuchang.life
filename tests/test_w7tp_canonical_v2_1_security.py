from __future__ import annotations

from copy import deepcopy

import pytest
from jsonschema import ValidationError

from tools.total_field.w7tp_canonical_v2_1_legacy_adapter import (
    ContractViolation,
    InMemoryReplayGuard,
    replay_tuple_sha256,
    validate_v2_1_packet,
)
from test_w7tp_canonical_v2_1_contract import make_packet


def refresh_replay_tuple(packet: dict) -> None:
    replay_tuple = packet["adi"]["replay_protection"]["tuple"]
    packet["adi"]["replay_protection"]["tuple_sha256"] = replay_tuple_sha256(
        replay_tuple
    )


def test_h64_and_protected_material_are_reference_only() -> None:
    packet = make_packet()
    validate_v2_1_packet(packet)

    exposed = deepcopy(packet)
    exposed["state_field"]["dimensions"]["D6_GENERATIVE_TRANSMISSION"][
        "generation_rule_refs"
    ] = ["rule:RAW_H64-TD_MATERIAL"]
    with pytest.raises(ContractViolation, match="reference-only"):
        validate_v2_1_packet(exposed)


def test_cloud_or_llm_cannot_claim_final_authority() -> None:
    packet = make_packet()
    packet["authority_boundary"]["cloud_authority"] = ["FINAL_DECISION"]
    with pytest.raises(ValidationError):
        validate_v2_1_packet(packet)


def test_replay_tuple_is_single_use_and_logical_time_is_monotonic() -> None:
    guard = InMemoryReplayGuard()
    packet = make_packet()
    guard.accept(packet)
    with pytest.raises(ContractViolation, match="already observed"):
        guard.accept(packet)

    stale = make_packet()
    stale["envelope"]["packet_id"] = "W7TP-V2-1-TEST-STALE"
    stale["envelope"]["nonce"] = "nonce-test-stale"
    stale["adi"]["packet_layer"]["nonce"] = "nonce-test-stale"
    stale_tuple = stale["adi"]["replay_protection"]["tuple"]
    stale_tuple["packet_id"] = "W7TP-V2-1-TEST-STALE"
    stale_tuple["nonce"] = "nonce-test-stale"
    refresh_replay_tuple(stale)
    with pytest.raises(ContractViolation, match="not monotonic"):
        guard.accept(stale)


def test_namespace_and_logical_time_mismatch_are_rejected() -> None:
    namespace_mismatch = make_packet()
    namespace_mismatch["adi"]["system_layer"]["namespace"] = "w7tp.other.test"
    with pytest.raises(ContractViolation, match="namespace mismatch"):
        validate_v2_1_packet(namespace_mismatch)

    time_mismatch = make_packet()
    time_mismatch["lineage"]["logical_time"] = 2
    with pytest.raises(ContractViolation, match="logical time mismatch"):
        validate_v2_1_packet(time_mismatch)


def test_append_only_lineage_cannot_be_disabled() -> None:
    packet = make_packet()
    packet["lineage"]["append_only"] = False
    with pytest.raises(ValidationError):
        validate_v2_1_packet(packet)
