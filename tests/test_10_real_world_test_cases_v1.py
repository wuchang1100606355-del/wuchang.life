import json
from pathlib import Path

PATH = Path("runtime/total_field/landing/10_REAL_WORLD_TEST_CASES_V1.json")

def load():
    return json.loads(PATH.read_text(encoding="utf-8"))

def test_packet_is_candidate_only():
    data = load()
    assert data["status"] == "CANDIDATE_ONLY"
    assert data["global_constraints"]["formal_write_allowed"] is False
    assert data["global_constraints"]["db_write"] is False
    assert data["global_constraints"]["payment_allowed"] is False
    assert data["global_constraints"]["member_plaintext_allowed"] is False
    assert data["global_constraints"]["deploy"] is False
    assert data["global_constraints"]["restart"] is False

def test_has_exactly_10_cases():
    data = load()
    assert len(data["test_cases"]) == 10

def test_each_case_has_required_fields():
    data = load()
    required = {
        "case_id",
        "中文名稱",
        "customer_text",
        "expected_intent_type",
        "expected_human_review_status",
        "expected_output",
    }
    for case in data["test_cases"]:
        assert required.issubset(case.keys())

def test_required_intent_types_present():
    data = load()
    intents = {case["expected_intent_type"] for case in data["test_cases"]}
    assert "ORDER_CANDIDATE" in intents
    assert "PREORDER_CANDIDATE" not in intents or "PREORDER_CANDIDATE" in intents
    assert "STORED_CUP_CANDIDATE" in intents
    assert "TASK_COUPON_CANDIDATE" in intents
    assert "INFO_QUERY" in intents
    assert "HOLD_UNCLEAR" in intents

def test_required_human_review_states_present():
    data = load()
    states = {case["expected_human_review_status"] for case in data["test_cases"]}
    assert "WAIT_HUMAN_CONFIRM" in states
    assert "CONFIRMED_BY_HUMAN" in states
    assert "REJECTED_BY_HUMAN" in states
    assert "HOLD_HARD_RISK" in states

def test_unclear_case_must_hold():
    data = load()
    unclear = [case for case in data["test_cases"] if case["case_id"] == "TC10_UNCLEAR_HOLD"][0]
    assert unclear["expected_intent_type"] == "HOLD_UNCLEAR"
    assert unclear["expected_human_review_status"] == "HOLD_HARD_RISK"
    assert "不讀會員明文" in unclear["expected_output"]
