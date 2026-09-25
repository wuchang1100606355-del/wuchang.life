from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from tools.total_field.w7tp_canonical_v2_1_legacy_adapter import (
    replay_tuple_sha256,
    validate_v2_1_packet,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = (
    ROOT / "schemas/w7tp_8d_multipurpose_packet_canonical_v2_1.schema.json"
)
CANONICAL_PATH = (
    ROOT
    / "docs/total_field/W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1_FOUNDER_LOCKED_SUCCESSOR_20260728.md"
)
PARENT_PATH = (
    ROOT
    / "docs/total_field/W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2.md"
)


def make_packet() -> dict:
    packet_id = "W7TP-V2-1-TEST-0001"
    nonce = "nonce-test-0001"
    authority_ref = "authority:local-total-field"
    namespace = "w7tp.test.contract"
    logical_time = 1
    replay_tuple = {
        "authority_ref": authority_ref,
        "namespace": namespace,
        "packet_id": packet_id,
        "nonce": nonce,
        "logical_time": logical_time,
    }
    return {
        "canonical_id": (
            "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1"
        ),
        "version": "2.1",
        "canonical_binding": {
            "canonical_path": (
                "docs/total_field/"
                "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1_FOUNDER_LOCKED_SUCCESSOR_20260728.md"
            ),
            "canonical_sha256": (
                "383aba5b7a9f5d0e948d9b43b83e7dd"
                "6b6ec9c27f025fb9069e83810f0ae870d"
            ),
            "parent_version": "2.0",
            "parent_path": (
                "docs/total_field/"
                "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2.md"
            ),
            "parent_sha256": (
                "a5281f229ced0943072cce373125be16f"
                "0d361b9352a71094ad5450a6022d5d0"
            ),
            "migration_mode": "APPEND_ONLY_SUCCESSOR",
        },
        "packet_core": (
            "UNIFIED_MULTIPURPOSE_INTERACTIVE_COUPLED_8D_STATE_FIELD_PACKET"
        ),
        "communication_contract": {
            "primary": "INTENT_COMMUNICATION",
            "secondary": "STATE_FIELD_PACKET_COMMUNICATION",
            "semantic_communication": False,
            "semantic_model_role": "CANDIDATE_EVIDENCE_ONLY",
            "floating_point_required": False,
        },
        "authority_boundary": {
            "cloud_authority": ["CANDIDATE", "EVIDENCE"],
            "llm_authority": ["CANDIDATE", "EVIDENCE"],
            "final_decision_authority": "LOCAL_TOTAL_FIELD",
            "final_seal_authority": "LOCAL_TOTAL_FIELD",
        },
        "state_field": {
            "kind": "INTERACTIVE_COUPLED_8D_STATE_FIELD",
            "dimensions": {
                "D1_INTENT": {"profile_ref": "intent:test"},
                "D2_STATE": {"profile_ref": "state:current"},
                "D3_COORDINATE": {"profile_ref": "coordinate:test"},
                "D4_EVIDENCE": {
                    "profile_ref": "evidence:test",
                    "evidence_refs": ["evidence:test-1"],
                },
                "D5_EXECUTION": {"profile_ref": "execution:no-side-effect"},
                "D6_GENERATIVE_TRANSMISSION": {
                    "protocol_ref": "protocol:w7tp-v2.1",
                    "routing_ref": "routing:local",
                    "lookup_refs": ["lookup:test"],
                    "reference_refs": ["evidence:test-1"],
                    "generation_rule_refs": ["rule:test"],
                    "reconstruction_condition_refs": ["condition:test"],
                    "equivalent_state_rule_refs": ["equivalence:test"],
                    "total_field_verifier_ref": "verifier:total-field",
                },
                "D7_RISK_QUARANTINE": {
                    "hard_risks": [],
                    "quarantine_refs": ["risk:none"],
                    "decision": "PASS",
                },
                "D8_ENVELOPE_VERIFICATION": {
                    "envelope_ref": "envelope:test",
                    "verifier_ref": "verifier:total-field",
                    "seal_policy_ref": "policy:local-seal",
                },
            },
            "coupling": {
                "transition_function": "S_NEXT=T(S_CURRENT,I,C,E,A,G,R,V)",
                "current_state_ref": "state:current",
                "intent_ref": "intent:test",
                "coordinate_ref": "coordinate:test",
                "evidence_refs": ["evidence:test-1"],
                "execution_ref": "execution:no-side-effect",
                "generation_ref": "generation:test",
                "risk_ref": "risk:none",
                "verification_ref": "verification:test",
                "target_state_ref": "state:target",
                "non_float_execution": True,
            },
        },
        "adi": {
            "packet_layer": {
                "index_kind": "OPAQUE_IRREVERSIBLE_PACKET_DECISION_INDEX",
                "namespace": namespace,
                "decision_index": "1" * 64,
                "nonce": nonce,
                "key_version_ref": "key-version:test-v1",
                "authority_ref": authority_ref,
                "evidence_refs": ["evidence:test-1"],
                "derivation_ref": "derivation:local-opaque",
                "verifier_ref": "verifier:adi-local",
                "irreversible": True,
                "reversible_identity": False,
                "database_primary_key": False,
                "floating_embedding": False,
            },
            "system_layer": {
                "index_kind": "USER_OWNED_SPATIOTEMPORAL_STATE_INDEX_NETWORK",
                "owner_authority_ref": authority_ref,
                "namespace": namespace,
                "logical_time": logical_time,
                "packet_lineage_refs": ["packet:parent"],
                "state_transition_ref": "transition:test",
                "evidence_refs": ["evidence:test-1"],
            },
            "replay_protection": {
                "tuple": replay_tuple,
                "tuple_sha256": replay_tuple_sha256(replay_tuple),
                "logical_time_monotonic": True,
            },
        },
        "lineage": {
            "append_only": True,
            "parent_ref": "packet:parent",
            "parent_sha256": "2" * 64,
            "previous_seal_ref": "seal:parent",
            "logical_time": logical_time,
            "changed_dimensions": ["D2_STATE"],
            "transition_evidence_refs": ["evidence:test-1"],
        },
        "generation": {
            "protocol_native": True,
            "state_ref": "state:current",
            "coordinate_ref": "coordinate:test",
            "lookup_refs": ["lookup:test"],
            "generation_rule_refs": ["rule:test"],
            "reconstruction_condition_refs": ["condition:test"],
            "target_state_ref": "state:target",
            "file_movement": False,
        },
        "reconstruction": {
            "local_state_field_ref": "state-field:local",
            "lookup_refs": ["lookup:test"],
            "condition_refs": ["condition:test"],
            "equivalent_state_rule_refs": ["equivalence:test"],
            "target_state_ref": "state:target",
            "total_field_verifier_ref": "verifier:total-field",
            "deterministic_operations": [
                "INTEGER",
                "BOOLEAN",
                "SYMBOLIC",
                "LOOKUP",
                "REFERENCE_RESOLUTION",
                "STATE_TRANSITION",
            ],
            "model_output_role": "CANDIDATE_EVIDENCE_ONLY",
        },
        "verification": {
            "mode": "L1_EXACT_BYTE",
            "method_ref": "method:sha256",
            "contract_ref": "contract:exact-byte",
            "decision": "PASS",
            "raw_sha256": "3" * 64,
            "byte_length": 128,
            "hash_scope": "TARGET_RAW_BYTES",
        },
        "protected_refs": {
            "materials": [
                {
                    "kind": "H64_TD",
                    "reference": "trade_secret_ref:h64_codebook",
                    "disclosure": "REFERENCE_ONLY",
                }
            ]
        },
        "envelope": {
            "packet_id": packet_id,
            "authority_ref": authority_ref,
            "version": "2.1",
            "ttl_seconds": 300,
            "nonce": nonce,
            "payload_sha256": "4" * 64,
            "canonical_json_sha256": "5" * 64,
            "verifier_ref": "verifier:total-field",
            "seal_policy_ref": "policy:local-seal",
            "seal_state": "SEALED_BY_LOCAL_TOTAL_FIELD",
            "final_seal_authority": "LOCAL_TOTAL_FIELD",
        },
    }


def test_canonical_raw_hashes_are_bound() -> None:
    assert hashlib.sha256(PARENT_PATH.read_bytes()).hexdigest() == (
        "a5281f229ced0943072cce373125be16f"
        "0d361b9352a71094ad5450a6022d5d0"
    )
    assert hashlib.sha256(CANONICAL_PATH.read_bytes()).hexdigest() == (
        "383aba5b7a9f5d0e948d9b43b83e7dd"
        "6b6ec9c27f025fb9069e83810f0ae870d"
    )


def test_schema_is_draft_2020_12_and_valid() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validate_v2_1_packet(make_packet())


def test_verification_modes_are_mutually_exclusive() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    l1 = make_packet()
    validator.validate(l1)

    l2 = make_packet()
    l2["verification"] = {
        "mode": "L2_EFFECT_EQUIVALENT",
        "method_ref": "method:effect-compare",
        "contract_ref": "contract:effect-equivalent",
        "decision": "PASS",
        "effect_contract_ref": "effect:expected",
        "comparison_fields": ["state", "control", "effect"],
        "evidence_refs": ["evidence:effect-test"],
        "local_verifier_ref": "verifier:total-field",
    }
    validator.validate(l2)

    l3 = make_packet()
    l3["verification"] = {
        "mode": "L3_CANDIDATE",
        "method_ref": "method:candidate-review",
        "contract_ref": "contract:candidate-only",
        "decision": "HOLD",
        "candidate_refs": ["candidate:test"],
        "local_decision_authority_ref": "authority:local-total-field",
        "final_authority_granted": False,
    }
    l3["envelope"]["seal_state"] = "UNSEALED_CANDIDATE"
    validator.validate(l3)

    mixed = deepcopy(l1)
    mixed["verification"]["effect_contract_ref"] = "effect:not-allowed-in-l1"
    with pytest.raises(ValidationError):
        validator.validate(mixed)


def test_legacy_flat_dimension_names_are_not_core_v2_1() -> None:
    packet = make_packet()
    dimensions = packet["state_field"]["dimensions"]
    dimensions["D7_RISK"] = dimensions.pop("D7_RISK_QUARANTINE")
    with pytest.raises(ValidationError):
        validate_v2_1_packet(packet)
