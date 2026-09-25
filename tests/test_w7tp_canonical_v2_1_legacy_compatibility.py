from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tools.total_field.w7tp_canonical_v2_1_legacy_adapter import (
    ContractViolation,
    load_and_validate_v2_packet,
    project_v2_packet,
)


ROOT = Path(__file__).resolve().parents[1]
ADAPTER_SCHEMA = (
    ROOT / "schemas/field/w7tp_canonical_v2_to_v2_1_legacy_adapter_v1.schema.json"
)


def make_v2_packet() -> dict:
    profile = lambda value: {"profile_ref": value}
    risk = {"hard_risks": [], "decision": "PASS"}
    envelope = {
        "packet_id": "W7TP-V2-LEGACY-0001",
        "authority_ref": "authority:legacy-local",
        "version": "2.0.0",
        "ttl_seconds": 300,
        "nonce": "legacy-nonce-0001",
        "sha256": "1" * 64,
        "verifier_ref": "verifier:legacy-v2",
        "seal_policy": "legacy-read-only",
    }
    d6 = {
        "protocol": "W7TP_V2",
        "routing": "LOCAL",
        "segmentation": "NONE",
        "merge_conditions": ["ALL_SEGMENTS_PRESENT"],
        "lookup": profile("lookup:legacy"),
        "references": ["evidence:legacy"],
        "generation_rules": ["rule:legacy"],
        "reconstruction_contract": "contract:legacy-reconstruct",
        "verification_contract": "contract:legacy-verify",
        "residual": [],
        "refill_policy": "NONE",
        "on_demand_materialization": True,
    }
    return {
        "canonical_id": "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2",
        "version": "2.0.0",
        "packet_core": "UNIFIED_MULTIPURPOSE_8D_PACKET",
        "technology_flags": {
            "packet_carries_transport_protocol": True,
            "packet_carries_reconstruction_conditions": True,
            "packet_carries_reconstruction_contract": True,
            "packet_carries_verification_method": True,
            "packet_carries_verification_contract": True,
            "model_required": False,
            "llm_required": False,
            "neural_network_required": False,
            "floating_point_inference_required": False,
            "diffusion_required": False,
            "latent_codec": False,
            "neural_codec": False,
        },
        "dimensions": {
            "D1_INTENT": profile("intent:legacy"),
            "D2_STATE": profile("state:legacy"),
            "D3_COORDINATE": profile("coordinate:legacy"),
            "D4_EVIDENCE": profile("evidence:legacy"),
            "D5_EXECUTION": profile("execution:legacy"),
            "D6_GENERATIVE_TRANSMISSION": d6,
            "D7_RISK": risk,
            "D8_ENVELOPE": envelope,
        },
        "domain_profile": {
            "domain": "DOCUMENT",
            "state_profile": profile("state:legacy"),
            "coordinate_profile": profile("coordinate:legacy"),
            "lookup_profile": profile("lookup:legacy"),
            "generation_profile": profile("generation:legacy"),
            "reconstruction_profile": profile("reconstruction:legacy"),
            "verification_profile": profile("verification:legacy"),
        },
        "generation_packet": {
            "state": profile("state:legacy"),
            "coordinate": profile("coordinate:legacy"),
            "lookup": profile("lookup:legacy"),
            "generation_rule": ["rule:legacy"],
            "reconstruction_contract": "contract:legacy-reconstruct",
            "verification_contract": "contract:legacy-verify",
            "target_equivalence": "effect-equivalent",
        },
        "transmission_packet": {
            "routing": "LOCAL",
            "path": ["node:source", "node:target"],
            "segment": 0,
            "order": 0,
            "ttl": 300,
            "reference": ["evidence:legacy"],
            "hash": "2" * 64,
            "merge_condition": ["ALL_SEGMENTS_PRESENT"],
            "delivery_state": "VERIFIED",
        },
        "composition_mode": "SEPARATE",
        "reconstruction": {
            "core": [
                "NON_FLOAT_DETERMINISTIC_LOOKUP",
                "INTEGER_STATE_TRANSITION",
                "RULE_EXPANSION",
                "REFERENCE_RESOLUTION",
                "COORDINATE_RECONSTRUCTION",
                "EQUIVALENT_STATE_GENERATION",
                "TOTAL_FIELD_VERIFICATION",
            ],
            "zero_prior_content_receiver": True,
            "materialization": "LIMITED_RECONSTRUCTION",
            "economic_mode": "W7TP_GENERATIVE",
        },
        "verification": {
            "level": "L3_CANDIDATE",
            "method_ref": "method:legacy",
            "contract_ref": "contract:legacy",
            "decision": "HOLD",
        },
        "risk": risk,
        "envelope": envelope,
    }


def project(raw: bytes) -> dict:
    return project_v2_packet(
        raw,
        source_ref="packet:legacy-v2-0001",
        authority_ref="authority:local-total-field",
        namespace="w7tp.legacy.test",
        logical_time=10,
        nonce="projection-nonce-0001",
    )


def test_legacy_projection_preserves_raw_digest_and_embeds_no_source() -> None:
    packet = make_v2_packet()
    original = deepcopy(packet)
    raw = json.dumps(packet, ensure_ascii=False, indent=2).encode("utf-8")
    receipt = project(raw)
    schema = json.loads(ADAPTER_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(receipt)

    assert packet == original
    assert receipt["source"]["raw_sha256"] == hashlib.sha256(raw).hexdigest()
    assert receipt["source"]["byte_length"] == len(raw)
    assert receipt["source"]["bytes_mutated"] is False
    assert receipt["projection"]["source_content_embedded"] is False
    assert "packet_core" not in json.dumps(receipt)


def test_raw_digest_tracks_bytes_while_canonical_digest_tracks_json_value() -> None:
    packet = make_v2_packet()
    raw_pretty = json.dumps(packet, indent=2).encode("utf-8")
    raw_compact = json.dumps(packet, sort_keys=True, separators=(",", ":")).encode()
    pretty = project(raw_pretty)
    compact = project(raw_compact)

    assert pretty["source"]["raw_sha256"] != compact["source"]["raw_sha256"]
    assert (
        pretty["source"]["canonical_json_sha256"]
        == compact["source"]["canonical_json_sha256"]
    )


def test_invalid_v2_identity_is_rejected_without_projection() -> None:
    packet = make_v2_packet()
    packet["canonical_id"] = "NOT_CANONICAL_V2"
    raw = json.dumps(packet).encode("utf-8")
    with pytest.raises(ContractViolation):
        load_and_validate_v2_packet(raw)
