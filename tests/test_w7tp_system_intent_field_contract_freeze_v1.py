from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATHS = {
    "intent_root": ROOT / "schemas/field/w7tp_system_intent_root_v1.schema.json",
    "minimum_delta": ROOT / "schemas/field/w7tp_system_intent_minimum_delta_v1.schema.json",
    "d8_envelope": ROOT / "schemas/field/w7tp_system_intent_d8_envelope_v1.schema.json",
    "receipt_chain": ROOT / "schemas/field/w7tp_system_intent_receipt_chain_v1.schema.json",
    "migration_rules": ROOT / "schemas/field/w7tp_system_intent_field_version_migration_rules_v1.schema.json",
    "contract_freeze": ROOT / "schemas/field/w7tp_system_intent_field_contract_freeze_v1.schema.json",
}
MIGRATION_PATH = ROOT / "configs/total_field/w7tp_system_intent_field_version_migration_rules_v1.candidate.json"
CONTRACT_PATH = ROOT / "configs/total_field/w7tp_system_intent_field_contract_freeze_v1.candidate.json"
HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
HASH_D = "d" * 64


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


SCHEMAS = {name: load_json(path) for name, path in SCHEMA_PATHS.items()}
VALIDATORS = {
    name: jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    for name, schema in SCHEMAS.items()
}


def validate(name: str, value: dict[str, Any]) -> None:
    VALIDATORS[name].validate(value)


def assert_invalid(name: str, value: dict[str, Any]) -> None:
    with pytest.raises(jsonschema.ValidationError):
        validate(name, value)


def intent_root() -> dict[str, Any]:
    return {
        "contract_version": "W7TP-SYSTEM-INTENT-ROOT/1.0",
        "intent_root_id": "intent:root:1",
        "result": {
            "result_ref": "result:service:1",
            "outcome_code": "SERVICE_INFORMATION_CANDIDATE",
            "result_sha256": HASH_A,
        },
        "subject": {
            "subject_ref": "subject:anonymous:1",
            "identity_mode": "ANONYMOUS_ROLE_REF",
            "identity_authority": "ASSOCIATION_GOVERNED_MEMBER_IDENTITY_REGISTRY",
        },
        "scene": {
            "scene_ref": "scene:cafe:counter",
            "node_refs": ["node:msi:local"],
            "service_refs": ["service:counter:candidate"],
        },
        "known_state_refs": ["state:menu:verified"],
        "constraints": ["constraint:no_write", "constraint:human_confirm"],
        "acceptance": ["acceptance:schema_valid", "acceptance:no_effect"],
        "target_product_effect": {
            "effect_ref": "effect:candidate:draft",
            "effect_class": "CANDIDATE_DRAFT",
            "formal_effect_allowed": False,
        },
        "unresolved_effect": "HOLD_BEFORE_STATE_LOAD_OR_MODEL_CALL",
        "human_confirmation_required": True,
        "authority": "CANDIDATE_ONLY",
        "raw_input_included": False,
        "member_plaintext_included": False,
        "secret_material_included": False,
    }


def minimum_delta(state: str = "NONE") -> dict[str, Any]:
    value = {
        "contract_version": "W7TP-SYSTEM-INTENT-MINIMUM-DELTA/1.0",
        "delta_id": "delta:minimum:1",
        "intent_root_ref": "intent:root:1",
        "current_state_root_ref": "state:root:current",
        "minimum_delta_state": state,
        "affected_coordinates": [],
        "stable_refs": ["state:menu:verified"],
        "changed_state": [],
        "unknown_slots": [],
        "reconstruction_conditions": ["condition:source_hash_match"],
        "verification_conditions": ["condition:candidate_hash_match"],
        "target_product_effect": "effect:candidate:draft",
        "none_effect": "BUILD_NOT_REQUIRED",
        "model_packet_policy": {
            "allowed_material": [
                "intent_root_ref",
                "current_state_root_ref",
                "stable_state_refs",
                "affected_coordinates",
                "unknown_slots",
                "target_product_effect",
                "reconstruction_conditions",
                "verification_conditions",
                "output_schema",
            ],
            "forbidden_material": [
                "RAW_USER_INPUT",
                "FULL_CONTEXT",
                "KNOWN_PRIVATE_STATE_VALUE",
                "MEMBER_PLAINTEXT",
                "PAYMENT_SECRET",
                "CREDENTIAL_OR_TOKEN",
            ],
            "output_authority": "CANDIDATE_ONLY",
        },
        "authority": "NONE",
        "raw_input_included": False,
        "full_context_included": False,
        "known_private_state_values_included": False,
        "member_plaintext_included": False,
        "secret_material_included": False,
    }
    if state == "DELTA_REQUIRED":
        value["affected_coordinates"] = ["coordinate:d2:service_state"]
        value["changed_state"] = [
            {
                "coordinate_ref": "coordinate:d2:service_state",
                "operation": "REPLACE_REFERENCE",
                "previous_state_ref": "state:service:old",
                "candidate_state_ref": "state:service:candidate",
                "candidate_state_sha256": HASH_B,
                "authority": "NONE",
            }
        ]
    return value


def d8_envelope() -> dict[str, Any]:
    return {
        "contract_version": "W7TP-SYSTEM-INTENT-D8-ENVELOPE/1.0",
        "envelope_id": "envelope:d8:1",
        "state": "CANDIDATE_READY_FOR_TOTAL_FIELD",
        "intent_root_ref": "intent:root:1",
        "current_state_root_ref": "state:root:current",
        "minimum_delta_ref": "delta:minimum:1",
        "field_refs": [
            {"dimension": f"D{index}", "state_ref": f"state:d{index}:1", "state_sha256": HASH_A}
            for index in range(1, 8)
        ],
        "reconstruction_condition_refs": ["condition:source_hash_match"],
        "verification_instruction_refs": ["verifier:contract:1"],
        "receipt_chain_ref": "receipt_chain:candidate:1",
        "authority": {
            "decision_authority": "TOTAL_FIELD",
            "total_field_authority_state": "INACTIVE",
            "envelope_authority": "CANDIDATE_ONLY",
            "model_has_authority": False,
            "adapter_has_authority": False,
            "device_has_authority": False,
            "formal_effect_authorized": False,
        },
        "human_confirmation_required": True,
        "created_at_utc": "2026-08-18T20:44:13Z",
        "expires_at_utc": "2026-08-18T20:49:13Z",
        "nonce": "nonce:d8:1",
        "envelope_sha256": HASH_B,
        "verifier_ref": "verifier:d8:1",
        "raw_input_included": False,
        "full_context_included": False,
        "member_plaintext_included": False,
        "secret_material_included": False,
        "formal_landing_allowed": False,
        "applies_change": False,
        "memory_effect": False,
        "database_write": False,
        "deployment": False,
        "restart": False,
        "remote_write": False,
    }


def decision_receipt(decision: str, human_state: str, candidate_hash: str | None) -> dict[str, Any]:
    return {
        "receipt_version": "W7TP-DECISION-RECEIPT/1.0",
        "receipt_id": "receipt:decision:1",
        "receipt_type": "DECISION",
        "issued_at_utc": "2026-08-18T20:44:13Z",
        "issuer_ref": "issuer:local:verifier",
        "scope_ref": "scope:l02:candidate",
        "input_state_sha256": HASH_A,
        "candidate_sha256": candidate_hash,
        "decision": decision,
        "reason_codes": ["reason:three_gates_closed"],
        "human_confirmation_state": human_state,
        "formal_authority": False,
        "previous_receipt_sha256": None,
        "receipt_sha256": HASH_D,
    }


def receipt_chain(state: str = "CANDIDATE_READY_FOR_TOTAL_FIELD") -> dict[str, Any]:
    value: dict[str, Any] = {
        "contract_version": "W7TP-SYSTEM-INTENT-RECEIPT-CHAIN/1.0",
        "chain_id": "receipt_chain:candidate:1",
        "chain_state": state,
        "decision_receipt": decision_receipt(state, "CONFIRMED", HASH_B),
        "transition_receipt": {
            "receipt_version": "W7TP-TRANSITION-RECEIPT/1.0",
            "receipt_id": "receipt:transition:1",
            "receipt_type": "TRANSITION",
            "issued_at_utc": "2026-08-18T20:44:14Z",
            "issuer_ref": "issuer:local:verifier",
            "scope_ref": "scope:l02:candidate",
            "decision_receipt_ref": "receipt:decision:1",
            "from_state_ref": "state:root:current",
            "to_state_ref": "state:root:candidate",
            "transition_code": "CANDIDATE_STATE_ONLY",
            "input_state_sha256": HASH_A,
            "output_state_sha256": HASH_B,
            "applies_change": False,
            "previous_receipt_sha256": HASH_D,
            "receipt_sha256": HASH_C,
        },
        "effect_receipt": {
            "receipt_version": "W7TP-EFFECT-RECEIPT/1.0",
            "receipt_id": "receipt:effect:1",
            "receipt_type": "EFFECT",
            "decision_receipt_ref": "receipt:decision:1",
            "scope_ref": "scope:l02:candidate",
            "input_state_sha256": HASH_A,
            "candidate_sha256": HASH_B,
            "effect_type": "NONE",
            "effect_result": "NOT_APPLIED_CANDIDATE_ONLY",
            "output_state_sha256": HASH_A,
            "rollback_receipt_ref": "receipt:rollback:1",
            "observed_at": "2026-08-18T20:44:15Z",
            "issuer_ref": "issuer:local:verifier",
            "applies_change": False,
            "formal_authority": False,
            "previous_receipt_sha256": HASH_C,
            "receipt_sha256": HASH_B,
        },
        "rollback_receipt": {
            "receipt_version": "W7TP-ROLLBACK-RECEIPT/1.0",
            "receipt_id": "receipt:rollback:1",
            "receipt_type": "ROLLBACK",
            "effect_receipt_ref": "receipt:effect:1",
            "scope_ref": "scope:l02:candidate",
            "rollback_target_ref": "state:root:current",
            "rollback_result": "NOT_REQUIRED_NO_EFFECT",
            "input_state_sha256": HASH_A,
            "output_state_sha256": HASH_A,
            "verified_state_sha256": HASH_A,
            "observed_at": "2026-08-18T20:44:16Z",
            "issuer_ref": "issuer:local:verifier",
            "applies_change": False,
            "previous_receipt_sha256": HASH_B,
            "receipt_sha256": HASH_A,
        },
        "replay_protection": {
            "nonce": "nonce:receipt:1",
            "attempt_id": "attempt:receipt:1",
            "idempotency_key": "idempotency:receipt:1",
            "prior_receipt_ref": None,
            "single_use_nonce_required": True,
            "duplicate_submission_policy": "RETURN_OR_HOLD_ORIGINAL_RECEIPT_NO_NEW_EFFECT",
            "replay_policy": "HOLD_REPLAY_NO_NEW_EFFECT",
            "race_policy": "TERMINAL_RECEIPT_AND_CAS_PRECEDENCE",
        },
        "authority": {
            "decision_authority": "TOTAL_FIELD",
            "chain_authority": "CANDIDATE_ONLY",
            "formal_landing_allowed": False,
            "applies_change": False,
            "memory_effect": False,
            "database_write": False,
            "deployment": False,
            "restart": False,
            "remote_write": False,
        },
    }
    if state == "HOLD":
        value["decision_receipt"] = decision_receipt("HOLD", "REQUIRED_PENDING", None)
        value["transition_receipt"] = None
        value["effect_receipt"] = None
        value["rollback_receipt"] = None
    elif state == "BUILD_NOT_REQUIRED":
        value["decision_receipt"] = decision_receipt("BUILD_NOT_REQUIRED", "NOT_APPLICABLE", None)
        value["transition_receipt"] = None
        value["effect_receipt"] = None
        value["rollback_receipt"] = None
    return value


def test_all_schemas_are_valid_draft_2020_12_and_typed_objects_are_closed() -> None:
    for name, schema in SCHEMAS.items():
        jsonschema.Draft202012Validator.check_schema(schema)
        stack: list[Any] = [schema]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                if node.get("type") == "object":
                    assert node.get("additionalProperties") is False, name
                stack.extend(node.values())
            elif isinstance(node, list):
                stack.extend(node)


def test_contract_freeze_and_migration_instances_validate_and_are_hash_bound() -> None:
    contract = load_json(CONTRACT_PATH)
    migration = load_json(MIGRATION_PATH)
    validate("contract_freeze", contract)
    validate("migration_rules", migration)
    for artifact in contract["contract_artifacts"]:
        observed = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
        assert observed == artifact["sha256"]


def test_intent_root_accepts_reference_only_candidate() -> None:
    validate("intent_root", intent_root())


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("raw_input_included",), True),
        (("member_plaintext_included",), True),
        (("secret_material_included",), True),
        (("authority",), "TOTAL_FIELD"),
        (("target_product_effect", "formal_effect_allowed"), True),
        (("subject", "identity_mode"), "FULL_MEMBER_PLAINTEXT"),
    ],
)
def test_intent_root_forbidden_material_and_authority_fail_closed(path: tuple[str, ...], value: Any) -> None:
    candidate = intent_root()
    target: dict[str, Any] = candidate
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    assert_invalid("intent_root", candidate)


def test_intent_root_unknown_or_missing_field_is_rejected() -> None:
    candidate = intent_root()
    candidate["raw_user_input"] = "forbidden"
    assert_invalid("intent_root", candidate)
    candidate = intent_root()
    del candidate["acceptance"]
    assert_invalid("intent_root", candidate)


def test_minimum_delta_none_returns_build_not_required_contract() -> None:
    candidate = minimum_delta("NONE")
    validate("minimum_delta", candidate)
    assert candidate["none_effect"] == "BUILD_NOT_REQUIRED"


def test_minimum_delta_accepts_deterministic_and_unknown_slot_candidates() -> None:
    deterministic = minimum_delta("DELTA_REQUIRED")
    validate("minimum_delta", deterministic)
    unknown = minimum_delta("DELTA_REQUIRED")
    unknown["changed_state"] = []
    unknown["unknown_slots"] = [
        {
            "slot_id": "slot:service:choice",
            "coordinate_ref": "coordinate:d2:service_state",
            "expected_schema_ref": "schema:enum:service_choice",
            "constraint_refs": ["constraint:no_private_value"],
            "output_authority": "CANDIDATE_ONLY",
        }
    ]
    validate("minimum_delta", unknown)


def test_minimum_delta_none_with_change_and_required_without_delta_are_rejected() -> None:
    no_delta = minimum_delta("NONE")
    no_delta["affected_coordinates"] = ["coordinate:d2:service_state"]
    assert_invalid("minimum_delta", no_delta)
    required = minimum_delta("DELTA_REQUIRED")
    required["affected_coordinates"] = []
    required["changed_state"] = []
    assert_invalid("minimum_delta", required)


@pytest.mark.parametrize(
    "field",
    [
        "raw_input_included",
        "full_context_included",
        "known_private_state_values_included",
        "member_plaintext_included",
        "secret_material_included",
    ],
)
def test_minimum_delta_forbidden_data_flags_are_const_false(field: str) -> None:
    candidate = minimum_delta("DELTA_REQUIRED")
    candidate[field] = True
    assert_invalid("minimum_delta", candidate)


def test_minimum_delta_model_packet_and_unknown_fields_are_closed() -> None:
    candidate = minimum_delta("DELTA_REQUIRED")
    candidate["model_packet_policy"]["allowed_material"].append("raw_input")
    assert_invalid("minimum_delta", candidate)
    candidate = minimum_delta("DELTA_REQUIRED")
    candidate["changed_state"][0]["inline_value"] = "forbidden"
    assert_invalid("minimum_delta", candidate)


def test_d8_envelope_accepts_exact_ordered_d1_to_d7_refs() -> None:
    candidate = d8_envelope()
    validate("d8_envelope", candidate)
    assert [item["dimension"] for item in candidate["field_refs"]] == [f"D{i}" for i in range(1, 8)]


def test_d8_envelope_rejects_reordered_or_missing_field_refs() -> None:
    candidate = d8_envelope()
    candidate["field_refs"][0], candidate["field_refs"][1] = candidate["field_refs"][1], candidate["field_refs"][0]
    assert_invalid("d8_envelope", candidate)
    candidate = d8_envelope()
    candidate["field_refs"].pop()
    assert_invalid("d8_envelope", candidate)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("raw_input_included", True),
        ("full_context_included", True),
        ("member_plaintext_included", True),
        ("secret_material_included", True),
        ("formal_landing_allowed", True),
        ("applies_change", True),
        ("memory_effect", True),
        ("database_write", True),
        ("deployment", True),
        ("restart", True),
        ("remote_write", True),
    ],
)
def test_d8_envelope_hardwalls_fail_closed(field: str, value: Any) -> None:
    candidate = d8_envelope()
    candidate[field] = value
    assert_invalid("d8_envelope", candidate)


def test_d8_envelope_rejects_authority_escalation_and_unknown_field() -> None:
    candidate = d8_envelope()
    candidate["authority"]["model_has_authority"] = True
    assert_invalid("d8_envelope", candidate)
    candidate = d8_envelope()
    candidate["full_payload"] = {}
    assert_invalid("d8_envelope", candidate)


@pytest.mark.parametrize("state", ["HOLD", "BUILD_NOT_REQUIRED", "CANDIDATE_READY_FOR_TOTAL_FIELD"])
def test_receipt_chain_accepts_all_three_fail_closed_states(state: str) -> None:
    validate("receipt_chain", receipt_chain(state))


@pytest.mark.parametrize("missing", ["transition_receipt", "effect_receipt", "rollback_receipt"])
def test_candidate_ready_requires_decision_transition_effect_and_rollback_receipts(missing: str) -> None:
    candidate = receipt_chain()
    candidate[missing] = None
    assert_invalid("receipt_chain", candidate)


def test_receipt_effect_and_authority_cannot_apply_change() -> None:
    candidate = receipt_chain()
    candidate["effect_receipt"]["applies_change"] = True
    assert_invalid("receipt_chain", candidate)
    candidate = receipt_chain()
    candidate["authority"]["database_write"] = True
    assert_invalid("receipt_chain", candidate)


def test_replay_duplicate_and_race_policies_are_closed_and_non_effecting() -> None:
    candidate = receipt_chain()
    replay = candidate["replay_protection"]
    assert replay["single_use_nonce_required"] is True
    assert replay["duplicate_submission_policy"] == "RETURN_OR_HOLD_ORIGINAL_RECEIPT_NO_NEW_EFFECT"
    assert replay["replay_policy"] == "HOLD_REPLAY_NO_NEW_EFFECT"
    assert replay["race_policy"] == "TERMINAL_RECEIPT_AND_CAS_PRECEDENCE"
    replay["race_policy"] = "LAST_WRITER_WINS"
    assert_invalid("receipt_chain", candidate)


def test_hold_and_build_not_required_cannot_smuggle_effect_receipts() -> None:
    for state in ("HOLD", "BUILD_NOT_REQUIRED"):
        candidate = receipt_chain(state)
        candidate["effect_receipt"] = receipt_chain()["effect_receipt"]
        assert_invalid("receipt_chain", candidate)


def test_migration_rules_fail_closed_and_never_auto_promote() -> None:
    rules = load_json(MIGRATION_PATH)
    validate("migration_rules", rules)
    assert rules["unsupported_version_effect"] == "HOLD_VERSION_UNSUPPORTED"
    assert rules["lossy_migration_effect"] == "HOLD_LOSSY_MIGRATION_FORBIDDEN"
    assert rules["authority_increase_effect"] == "HOLD_AUTHORITY_ESCALATION"
    assert rules["hash_mismatch_effect"] == "HOLD_SOURCE_HASH_MISMATCH"
    assert rules["current_decision"]["automatic_migration_allowed"] is False
    assert rules["current_decision"]["automatic_promotion_allowed"] is False


def test_migration_rules_reject_effect_authority_and_unknown_fields() -> None:
    rules = load_json(MIGRATION_PATH)
    rules["authority"]["applies_change"] = True
    assert_invalid("migration_rules", rules)
    rules = load_json(MIGRATION_PATH)
    rules["migration_rules"][0]["silent_default"] = True
    assert_invalid("migration_rules", rules)


def test_contract_freeze_preserves_single_field_identity_ownership_and_no_effect() -> None:
    contract = load_json(CONTRACT_PATH)
    boundary = contract["identity_and_ownership_boundary"]
    assert boundary["member_identity_sovereignty_source"] == "ASSOCIATION_GOVERNED_MEMBER_IDENTITY_REGISTRY"
    assert boundary["service_identity_mode"] == "ROLE_BINDING_OR_8D_IDENTITY_PACKET_REFERENCE_ONLY"
    assert boundary["full_member_plaintext_replication_allowed"] is False
    assert boundary["technical_ownership_transfer_proven"] is False
    assert boundary["technical_ownership_and_runtime_authority_are_separate"] is True
    assert all(value is False for key, value in contract["authority"].items() if key != "decision_authority")


def test_contract_construction_order_matches_true8d_sandbox() -> None:
    import sys

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools.total_field.w7tp_true8d_contract_sandbox import construction_order

    contract = load_json(CONTRACT_PATH)
    assert tuple(contract["construction_order"]) == construction_order()


def test_contract_freeze_unknown_field_is_rejected() -> None:
    contract = load_json(CONTRACT_PATH)
    contract["second_total_field"] = True
    assert_invalid("contract_freeze", contract)
