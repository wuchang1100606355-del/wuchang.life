import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/w7tp_total_field_non_floating_ai.py"
SCHEMA_PATH = ROOT / "schemas/w7tp_total_field_active_question_packet.schema.json"

spec = importlib.util.spec_from_file_location("w7tp_total_field_non_floating_ai", MODULE_PATH)
engine = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(engine)


def base_state(**updates):
    packet = {
        "rule_version": engine.RULE_VERSION,
        "lookup_version": engine.LOOKUP_VERSION,
        "input_valid": True,
        "bug_evidence_refs": [],
        "evidence_refs": ["evidence:total-field.rule.v1"],
        "missing_state_refs": [],
        "conflicting_evidence_refs": [],
        "authority_conflict_refs": [],
        "reconstruction_gap_refs": [],
        "unresolved_route_refs": [],
        "unmatched_condition_refs": [],
    }
    packet.update(updates)
    return packet


def test_active_question_schema_is_valid_draft_2020_12():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)


def test_all_six_explicit_gap_rules_create_ordered_question_packets():
    packet = base_state(
        missing_state_refs=["state:missing:1"],
        conflicting_evidence_refs=["evidence:conflict:1"],
        authority_conflict_refs=["authority:conflict:1"],
        reconstruction_gap_refs=["reconstruction:gap:1"],
        unresolved_route_refs=["route:unresolved:1"],
        unmatched_condition_refs=["condition:unmatched:1"],
    )
    questions = engine.generate_active_question_packets("RUN-ACTIVE-QUESTION-0001", packet)
    assert [question["question_type"] for question in questions] == [
        "MISSING_STATE_QUESTION_PACKET",
        "EVIDENCE_CONFLICT_QUESTION_PACKET",
        "AUTHORITY_CLARIFICATION_PACKET",
        "RECONSTRUCTION_GAP_PACKET",
        "UNRESOLVED_ROUTE_PACKET",
        "NEW_RULE_CANDIDATE_PACKET",
    ]
    assert all(question["state"] == "HOLD" for question in questions)
    assert all(question["seal_status"] == "NOT_SEALED" for question in questions)
    assert all(question["execution_authority"] is False for question in questions)


def test_question_packets_are_deterministic_for_equivalent_ref_sets():
    first = base_state(missing_state_refs=["state:b", "state:a", "state:a"])
    second = base_state(missing_state_refs=["state:a", "state:b"])
    assert engine.generate_active_question_packets("RUN-DETERMINISTIC-0001", first) == engine.generate_active_question_packets(
        "RUN-DETERMINISTIC-0001", second
    )


def test_no_gap_yields_pass_without_llm():
    result = engine.evaluate_total_field_state("RUN-NO-GAP-0001", base_state())
    assert result["state"] == "PASS"
    assert result["questions"] == []
    assert result["deterministic_core"] is True
    assert result["llm_required"] is False


def test_stale_lookup_invalid_input_and_bug_evidence_hold():
    result = engine.evaluate_total_field_state(
        "RUN-ENGINEERING-AUDIT-0001",
        base_state(
            lookup_version="W7TP-TOTAL-FIELD-LOOKUP/0.9",
            input_valid=False,
            bug_evidence_refs=["bug:evidence:1"],
        ),
    )
    assert result["state"] == "HOLD"
    assert set(result["errors"]) == {
        "LOOKUP_VERSION_UNSUPPORTED",
        "INPUT_INVALID",
        "ENGINEERING_BUG_EVIDENCE_PRESENT",
    }


def test_active_question_prevents_seal():
    evaluation = engine.evaluate_total_field_state(
        "RUN-HOLD-SEAL-0001", base_state(unresolved_route_refs=["route:missing"])
    )
    candidate = {"verification_result": "VERIFIED", "candidate_only": False}
    assert engine.can_seal_candidate(candidate, evaluation) is False


def test_unverified_or_candidate_output_never_seals():
    evaluation = engine.evaluate_total_field_state("RUN-CANDIDATE-0001", base_state())
    assert engine.can_seal_candidate(
        {"verification_result": "UNVERIFIED", "candidate_only": False}, evaluation
    ) is False
    assert engine.can_seal_candidate(
        {"verification_result": "VERIFIED", "candidate_only": True}, evaluation
    ) is False
    assert engine.can_seal_candidate(
        {"verification_result": "VERIFIED", "candidate_only": False}, evaluation
    ) is True


def test_engine_uses_no_floating_point_or_token_inference_runtime():
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "random" not in source
    assert "float(" not in source
    assert "openai" not in source.lower()
    assert "gemini" not in source.lower()
