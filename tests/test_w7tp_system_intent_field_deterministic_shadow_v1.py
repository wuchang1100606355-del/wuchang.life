from __future__ import annotations

import ast
import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.total_field.w7tp_system_intent_field_deterministic_shadow import (  # noqa: E402
    CONTROLLER_ID,
    canonical_sha256,
    run_shadow,
)


CONTROLLER_PATH = ROOT / "tools/total_field/w7tp_system_intent_field_deterministic_shadow.py"
BUNDLE_PATH = ROOT / "configs/total_field/w7tp_system_intent_field_deterministic_shadow_v1.candidate.json"
BUNDLE_SCHEMA_PATH = ROOT / "schemas/field/w7tp_system_intent_field_deterministic_shadow_v1.schema.json"
DELTA_SCHEMA_PATH = ROOT / "schemas/field/w7tp_system_intent_minimum_delta_v1.schema.json"
TRACE_PATH = ROOT / (
    "runtime/total_field/inbox/"
    "W7TP_SYSTEM_INTENT_FIELD_L03_DETERMINISTIC_CORE_SHADOW_20260819T041655Z/"
    "DECISION_TRACE.json"
)
HASH_A = "a" * 64
HASH_B = "b" * 64


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


BUNDLE = load_json(BUNDLE_PATH)
BUNDLE_SCHEMA = load_json(BUNDLE_SCHEMA_PATH)
DELTA_SCHEMA = load_json(DELTA_SCHEMA_PATH)
BUNDLE_VALIDATOR = jsonschema.Draft202012Validator(BUNDLE_SCHEMA)
DELTA_VALIDATOR = jsonschema.Draft202012Validator(DELTA_SCHEMA)


def request(intent_code: str = "STAFF_ASSIST") -> dict[str, Any]:
    effect_by_intent = {
        "MENU_QUERY": "effect:menu-information-only",
        "STAFF_ASSIST": "effect:staff-assist-guidance",
        "SERVICE_REQUEST": "effect:service-request-draft",
        "DISPLAY_UPDATE": "effect:display-update-draft",
        "POS_ORDER_CREATE": "effect:pos-order-draft",
    }
    return {
        "request_version": "W7TP-SYSTEM-INTENT-FIELD-SHADOW-REQUEST/1.0",
        "attempt_ref": "attempt:l03:001",
        "idempotency_ref": "idempotency:l03:001",
        "nonce_ref": "nonce:l03:001",
        "intent_code": intent_code,
        "intent_root_ref": "intent:root:l03-001",
        "scope_ref": "scope:counter:01",
        "expected_state_version": 7,
        "expected_state_sha256": HASH_A,
        "requested_effect_ref": effect_by_intent.get(intent_code, "effect:unknown"),
        "human_confirmation_state": "CONFIRMED",
        "declared_unknown_slots": [],
        "raw_input_included": False,
        "member_plaintext_included": False,
        "secret_material_included": False,
    }


def state(current_product_ref: str = "product:legacy-v1") -> dict[str, Any]:
    return {
        "scope_ref": "scope:counter:01",
        "state_root_ref": "state:root:counter-01-v7",
        "state_version": 7,
        "state_sha256": HASH_A,
        "verified": True,
        "canonical_lock_state": "LOCKED",
        "coordinate_bound": True,
        "evidence_complete": True,
        "hard_risk": False,
        "current_product_ref": current_product_ref,
        "stable_state_refs": ["state:menu:verified-v3", "state:role-binding:staff-v1"],
    }


def state_index(current_product_ref: str = "product:legacy-v1") -> dict[str, dict[str, Any]]:
    return {"scope:counter:01": state(current_product_ref)}


def assert_no_effect(result: dict[str, Any]) -> None:
    trace = result["decision_trace"]
    assert trace["model_call_count"] == 0
    assert trace["formal_effect_count"] == 0
    assert trace["authority"] == {
        "decision_authority": "TOTAL_FIELD",
        "controller_authority": "NONE",
        "formal_landing_allowed": False,
        "applies_change": False,
        "memory_effect": False,
        "database_write": False,
        "deployment": False,
        "restart": False,
        "remote_write": False,
    }


def test_bundle_schema_is_valid_closed_and_instance_is_hash_bound() -> None:
    jsonschema.Draft202012Validator.check_schema(BUNDLE_SCHEMA)
    BUNDLE_VALIDATOR.validate(BUNDLE)
    stack: list[Any] = [BUNDLE_SCHEMA]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    observed = hashlib.sha256(CONTROLLER_PATH.read_bytes()).hexdigest()
    assert observed == BUNDLE["controller"]["sha256"]
    assert BUNDLE["controller"]["controller_id"] == CONTROLLER_ID


def test_controller_ast_has_no_external_io_clock_random_subprocess_or_model_interface() -> None:
    tree = ast.parse(CONTROLLER_PATH.read_text(encoding="utf-8"))
    imported: set[str] = set()
    called_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                called_names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                called_names.add(node.func.attr)
    assert imported <= {"__future__", "hashlib", "json"}
    assert not imported & {"os", "pathlib", "socket", "subprocess", "time", "random", "requests", "sqlite3"}
    assert not called_names & {
        "open",
        "print",
        "input",
        "exec",
        "eval",
        "compile",
        "system",
        "popen",
        "connect",
        "request",
        "urlopen",
    }
    run_shadow_node = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_shadow"
    )
    assert [argument.arg for argument in run_shadow_node.args.args] == [
        "request",
        "scoped_state_by_ref",
        "rule_bundle",
    ]


def test_unresolved_intent_holds_before_scoped_state_access_and_calls_no_model() -> None:
    class StateMustNotLoad:
        def __getitem__(self, key: str) -> Any:
            raise AssertionError(f"state accessed for unresolved intent: {key}")

    result = run_shadow(request("UNDECLARED_INTENT"), StateMustNotLoad(), BUNDLE)
    assert result["decision"] == "HOLD"
    assert result["reason_code"] == "LOCAL_HOLD_INTENT_UNRESOLVED"
    assert result["decision_trace"]["state_load_calls"] == 0
    assert result["decision_trace"]["intent_resolution"] == "UNRESOLVED_HOLD_BEFORE_STATE_LOAD_OR_MODEL"
    assert_no_effect(result)


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (lambda value: value.update({"raw_user_input": "must-not-enter-trace"}), "HOLD_SCHEMA_UNKNOWN_FIELD"),
        (lambda value: value.update({"raw_input_included": True}), "HOLD_FORBIDDEN_DATA_MATERIAL"),
        (lambda value: value.update({"member_plaintext_included": True}), "HOLD_FORBIDDEN_DATA_MATERIAL"),
        (lambda value: value.update({"secret_material_included": True}), "HOLD_FORBIDDEN_DATA_MATERIAL"),
        (lambda value: value.update({"declared_unknown_slots": [{}]}), "HOLD_ENVELOPE_INVALID"),
    ],
)
def test_invalid_or_forbidden_request_fails_closed_before_state_load(mutation: Any, reason: str) -> None:
    class StateMustNotLoad:
        def __getitem__(self, key: str) -> Any:
            raise AssertionError(key)

    candidate = request()
    mutation(candidate)
    result = run_shadow(candidate, StateMustNotLoad(), BUNDLE)
    assert result["decision"] == "HOLD"
    assert result["reason_code"] == reason
    assert result["decision_trace"]["state_load_calls"] == 0
    assert "must-not-enter-trace" not in json.dumps(result, sort_keys=True)
    assert_no_effect(result)


def test_known_no_change_intent_returns_build_not_required_without_model() -> None:
    result = run_shadow(request("MENU_QUERY"), state_index("product:menu-current"), BUNDLE)
    assert result["decision"] == "BUILD_NOT_REQUIRED"
    assert result["reason_code"] == "NO_MINIMUM_DELTA"
    assert result["candidate_delta"] is None
    assert result["decision_trace"]["state_load_calls"] == 1
    assert result["decision_trace"]["gates"] == [
        {"gate_id": "GATE_1_CANONICAL_LOCK", "result": "PASS"},
        {"gate_id": "GATE_2_INTENT_PRODUCT_GAP", "result": "NO_MINIMUM_DELTA"},
        {"gate_id": "GATE_3_HUMAN_UI_PRODUCT_REVIEW", "result": "NOT_APPLICABLE_NO_GAP"},
    ]
    assert_no_effect(result)


def test_known_deterministic_intent_builds_reference_only_minimum_delta() -> None:
    result = run_shadow(request(), state_index(), BUNDLE)
    assert result["decision"] == "CANDIDATE_READY_FOR_TOTAL_FIELD"
    assert result["reason_code"] == "DETERMINISTIC_REFERENCE_DELTA_READY"
    assert result["decision_trace"]["state_load_calls"] == 1
    assert result["decision_trace"]["gates"][-1] == {
        "gate_id": "GATE_3_HUMAN_UI_PRODUCT_REVIEW",
        "result": "PASS_CONFIRMED",
    }
    delta = result["candidate_delta"]
    assert isinstance(delta, dict)
    DELTA_VALIDATOR.validate(delta)
    assert delta["authority"] == "NONE"
    assert delta["unknown_slots"] == []
    assert delta["raw_input_included"] is False
    assert delta["member_plaintext_included"] is False
    assert delta["secret_material_included"] is False
    assert_no_effect(result)


@pytest.mark.parametrize(
    ("confirmation", "reason"),
    [
        ("REQUIRED_PENDING", "HOLD_HUMAN_CONFIRMATION_REQUIRED"),
        ("NOT_APPLICABLE", "HOLD_HUMAN_CONFIRMATION_REQUIRED"),
        ("REJECTED", "HOLD_HUMAN_REJECTED"),
    ],
)
def test_gate_three_human_review_fails_closed(confirmation: str, reason: str) -> None:
    candidate = request()
    candidate["human_confirmation_state"] = confirmation
    result = run_shadow(candidate, state_index(), BUNDLE)
    assert result["decision"] == "HOLD"
    assert result["reason_code"] == reason
    assert result["candidate_delta"] is None
    assert_no_effect(result)


@pytest.mark.parametrize(
    ("key", "value", "reason"),
    [
        ("verified", False, "HOLD_STATE_UNVERIFIED"),
        ("canonical_lock_state", "UNLOCKED", "HOLD_CANONICAL_LOCK_FAILED"),
        ("coordinate_bound", False, "HOLD_COORDINATE_UNBOUND"),
        ("evidence_complete", False, "HOLD_EVIDENCE_INCOMPLETE"),
        ("hard_risk", True, "HOLD_HARD_RISK"),
    ],
)
def test_gate_one_state_conditions_fail_closed(key: str, value: Any, reason: str) -> None:
    candidate_state = state()
    candidate_state[key] = value
    result = run_shadow(request(), {"scope:counter:01": candidate_state}, BUNDLE)
    assert result["decision"] == "HOLD"
    assert result["reason_code"] == reason
    assert result["candidate_delta"] is None
    assert_no_effect(result)


def test_target_effect_mismatch_holds_at_gate_two() -> None:
    candidate = request()
    candidate["requested_effect_ref"] = "effect:unbound-target"
    result = run_shadow(candidate, state_index(), BUNDLE)
    assert result["decision"] == "HOLD"
    assert result["reason_code"] == "HOLD_TARGET_EFFECT_MISMATCH"
    assert result["decision_trace"]["gates"][-1]["gate_id"] == "GATE_2_INTENT_PRODUCT_GAP"
    assert_no_effect(result)


def test_unknown_slot_route_holds_locally_and_never_calls_model() -> None:
    candidate = request("POS_ORDER_CREATE")
    candidate["declared_unknown_slots"] = ["slot:pos:item-selection"]
    result = run_shadow(candidate, state_index(), BUNDLE)
    assert result["decision"] == "HOLD"
    assert result["reason_code"] == "LOCAL_HOLD_UNKNOWN_SLOT_REQUIRES_L04"
    assert result["decision_trace"]["intent_resolution"] == "RESOLVED_UNKNOWN_SLOT_ROUTE_NO_MODEL"
    assert result["decision_trace"]["model_call_count"] == 0
    assert_no_effect(result)


def test_every_versioned_known_intent_bypasses_model() -> None:
    for rule in BUNDLE["rules"]:
        candidate = request(rule["intent_code"])
        if rule["route_mode"] == "UNKNOWN_SLOT_HOLD":
            candidate["declared_unknown_slots"] = ["slot:declared:one"]
        result = run_shadow(candidate, state_index(), BUNDLE)
        assert result["reason_code"] != "LOCAL_HOLD_INTENT_UNRESOLVED"
        assert result["decision_trace"]["model_call_count"] == 0
        assert result["decision_trace"]["formal_effect_count"] == 0


def test_replay_and_duplicate_submission_are_byte_deterministic() -> None:
    first = run_shadow(request(), state_index(), BUNDLE)
    replay = run_shadow(deepcopy(request()), deepcopy(state_index()), deepcopy(BUNDLE))
    duplicate = run_shadow(request(), state_index(), BUNDLE)
    assert first == replay == duplicate
    assert json.dumps(first, sort_keys=True, separators=(",", ":")) == json.dumps(
        duplicate, sort_keys=True, separators=(",", ":")
    )
    trace_without_hash = deepcopy(first["decision_trace"])
    observed_trace_hash = trace_without_hash.pop("trace_sha256")
    assert canonical_sha256(trace_without_hash) == observed_trace_hash
    assert_no_effect(first)


@pytest.mark.parametrize(("field", "value"), [("expected_state_version", 6), ("expected_state_sha256", HASH_B)])
def test_state_version_or_hash_race_holds_by_cas(field: str, value: Any) -> None:
    candidate = request()
    candidate[field] = value
    result = run_shadow(candidate, state_index(), BUNDLE)
    assert result["decision"] == "HOLD"
    assert result["reason_code"] == "HOLD_STATE_VERSION_RACE"
    assert result["decision_trace"]["gates"] == [
        {"gate_id": "GATE_1_CANONICAL_LOCK", "result": "HOLD_CAS_MISMATCH"}
    ]
    assert_no_effect(result)


def test_bundle_authority_escalation_holds_before_state_load() -> None:
    class StateMustNotLoad:
        def __getitem__(self, key: str) -> Any:
            raise AssertionError(key)

    escalated = deepcopy(BUNDLE)
    escalated["authority"]["applies_change"] = True
    result = run_shadow(request(), StateMustNotLoad(), escalated)
    assert result["decision"] == "HOLD"
    assert result["reason_code"] == "HOLD_AUTHORITY_ESCALATION"
    assert result["decision_trace"]["state_load_calls"] == 0
    assert_no_effect(result)


def test_bundle_schema_rejects_unknown_fields_model_or_effect_authority() -> None:
    unknown = deepcopy(BUNDLE)
    unknown["undeclared"] = True
    with pytest.raises(jsonschema.ValidationError):
        BUNDLE_VALIDATOR.validate(unknown)

    model = deepcopy(BUNDLE)
    model["rules"][0]["model_allowed"] = True
    with pytest.raises(jsonschema.ValidationError):
        BUNDLE_VALIDATOR.validate(model)

    effect = deepcopy(BUNDLE)
    effect["authority"]["formal_landing_allowed"] = True
    with pytest.raises(jsonschema.ValidationError):
        BUNDLE_VALIDATOR.validate(effect)


def test_candidate_packet_is_minimized_to_contract_allowlist_and_no_original_input() -> None:
    sample_private_text = "SENSITIVE_SAMPLE_MUST_NOT_APPEAR"
    candidate = request()
    candidate["raw_user_input"] = sample_private_text
    held = run_shadow(candidate, state_index(), BUNDLE)
    assert sample_private_text not in json.dumps(held, sort_keys=True)

    ready = run_shadow(request(), state_index(), BUNDLE)
    packet = ready["candidate_delta"]["model_packet_policy"]
    assert packet["allowed_material"] == [
        "intent_root_ref",
        "current_state_root_ref",
        "stable_state_refs",
        "affected_coordinates",
        "unknown_slots",
        "target_product_effect",
        "reconstruction_conditions",
        "verification_conditions",
        "output_schema",
    ]
    assert packet["output_authority"] == "CANDIDATE_ONLY"
    assert ready["candidate_delta"]["known_private_state_values_included"] is False
    assert_no_effect(ready)


def test_decision_trace_artifact_is_hash_bound_and_covers_required_terminal_paths() -> None:
    evidence = load_json(TRACE_PATH)
    assert evidence["scenario_count"] == len(evidence["scenarios"]) == 5
    expected_scenarios = {
        "KNOWN_REFERENCE_DELTA_READY": "CANDIDATE_READY_FOR_TOTAL_FIELD",
        "KNOWN_NO_DELTA_BUILD_NOT_REQUIRED": "BUILD_NOT_REQUIRED",
        "UNRESOLVED_HOLD_BEFORE_STATE": "HOLD",
        "KNOWN_UNKNOWN_SLOT_LOCAL_HOLD": "HOLD",
        "CAS_RACE_HOLD": "HOLD",
    }
    assert {item["scenario_id"] for item in evidence["scenarios"]} == set(expected_scenarios)
    for item in evidence["scenarios"]:
        result = item["result"]
        trace = deepcopy(result["decision_trace"])
        observed_hash = trace.pop("trace_sha256")
        assert canonical_sha256(trace) == observed_hash
        assert trace["bundle_sha256"] == canonical_sha256(BUNDLE)
        assert trace["decision"] == result["decision"] == expected_scenarios[item["scenario_id"]]
        assert trace["model_call_count"] == 0
        assert trace["formal_effect_count"] == 0
        assert trace["authority"]["applies_change"] is False
        if result["candidate_delta"] is not None:
            DELTA_VALIDATOR.validate(result["candidate_delta"])
