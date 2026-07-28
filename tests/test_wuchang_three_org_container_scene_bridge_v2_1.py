from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from tools.total_field.wuchang_three_org_container_scene_bridge import (
    CANONICAL_V2_1_ID,
    CANONICAL_V2_1_PATH,
    CANONICAL_V2_1_SHA256,
    CANONICAL_V2_1_VERSION,
    _isolated_total_field_translation_request,
    build_audiovisual_natural_language_service_candidate,
    build_eight_d_media_transport_packet,
    build_three_org_scene_candidate,
)


EXPECTED_DIMENSIONS = {
    "D1_INTENT",
    "D2_STATE",
    "D3_COORDINATE",
    "D4_EVIDENCE",
    "D5_EXECUTION",
    "D6_GENERATIVE_TRANSMISSION",
    "D7_RISK_QUARANTINE",
    "D8_ENVELOPE_VERIFICATION",
}
SCHEMA = json.loads(
    Path("schemas/w7tp_8d_multipurpose_packet_canonical_v2_1.schema.json").read_text(
        encoding="utf-8"
    )
)
VALIDATOR = Draft202012Validator(SCHEMA)


def _assert_v2_1_binding(packet):
    VALIDATOR.validate(packet["core_packet"])
    assert packet["canonical_id"] == CANONICAL_V2_1_ID
    assert packet["version"] == CANONICAL_V2_1_VERSION
    assert packet["canonical_binding"]["path"] == CANONICAL_V2_1_PATH
    assert packet["canonical_binding"]["sha256"] == CANONICAL_V2_1_SHA256
    assert packet["canonical_binding"]["migration_mode"] == "APPEND_ONLY_SUCCESSOR"
    assert set(packet["dimensions"]) == EXPECTED_DIMENSIONS
    assert packet["state_field"]["mode"] == "INTERACTIVE_COUPLED_8D_STATE_FIELD"
    assert packet["communication_contract"]["semantic_communication"] is False
    assert packet["lineage"]["mode"] == "APPEND_ONLY"
    assert packet["lineage"]["historical_packet_rewritten"] is False
    assert packet["lineage"]["logical_time"].startswith("logical-time:")
    assert packet["protected_refs"]["mode"] == "REFERENCE_ONLY"
    assert packet["protected_refs"]["inline_protected_material"] is False
    assert packet["adi"]["packet_layer"]["index_state"] == "NOT_ALLOCATED"
    assert packet["adi"]["packet_layer"]["floating_point_embedding"] is False
    assert packet["core_packet"]["version"] == "2.1"


def test_media_packets_emit_v2_1_with_explicit_l1_l2_l3_modes():
    expected = {
        "L1_FULL": "L1_EXACT_BYTE",
        "L2_EQUIVALENT": "L2_EFFECT_EQUIVALENT",
        "L3_CANDIDATE": "L3_CANDIDATE",
    }

    for level, mode in expected.items():
        packet = build_eight_d_media_transport_packet(
            domain="IMAGE",
            verification_level=level,
        )
        _assert_v2_1_binding(packet)
        assert packet["verification"]["level"] == level
        assert packet["verification"]["mode"] == mode
        assert packet["envelope"]["verification_mode"] == mode
        assert packet["envelope"]["nonce"]
        assert packet["envelope"]["logical_time"] == packet["lineage"]["logical_time"]


def test_audio_effect_equivalence_is_not_semantic_communication():
    packet = build_eight_d_media_transport_packet(domain="AUDIO")

    assert packet["verification"]["mode"] == "L2_EFFECT_EQUIVALENT"
    assert (
        packet["generation_packet"]["target_equivalence"]
        == "AUDIO_SEMANTIC_TIMING_PROSODY_AND_SERVICE_EFFECT_EQUIVALENT"
    )
    assert packet["communication_contract"]["semantic_model_role"] == "CANDIDATE_PARSER_ONLY"


def test_three_org_packet_uses_v2_1_core_and_read_only_legacy_projection():
    packet = build_three_org_scene_candidate(
        intent_text="商業場景候選",
        evidence_refs=["evidence_ref:fixture"],
    )["eight_d_packet"]

    _assert_v2_1_binding(packet)
    assert packet["verification"]["mode"] == "L3_CANDIDATE"
    assert packet["d8_envelope"] is packet["legacy_profile_adapter"]["projection"]["d8_envelope"]
    assert packet["d7_risk"] is packet["legacy_profile_adapter"]["projection"]["d7_risk"]
    assert packet["legacy_profile_adapter"]["mode"] == "READ_ONLY_LEGACY_FLAT_PROFILE_PROJECTION"
    assert packet["legacy_profile_adapter"]["historical_packet_rewritten"] is False


def test_audiovisual_packet_uses_v2_1_core_and_preserves_flat_read_api():
    packet = build_audiovisual_natural_language_service_candidate(
        intent_text="協會影音服務候選",
        input_mode="audiovisual_event",
    )["eight_d_packet"]

    _assert_v2_1_binding(packet)
    assert packet["verification"]["mode"] == "L3_CANDIDATE"
    assert packet["d8_envelope"]["decision_authority"] == "total_field"
    assert packet["d7_risk"]["member_plaintext_to_cloud_blocked"] is True
    assert packet["legacy_profile_adapter"]["historical_packet_rewritten"] is False


def test_isolated_gte_profile_remains_closed_and_unchanged():
    request, previous = _isolated_total_field_translation_request(
        packet_sha256="a" * 64,
        cloud_fragment_sha256="b" * 64,
    )
    before = copy.deepcopy(previous)

    assert request["profile_schema_version"] == "8d-gte-runtime-candidate-profile/0.1"
    assert "legacy_profile_adapter" not in request
    assert previous == before
