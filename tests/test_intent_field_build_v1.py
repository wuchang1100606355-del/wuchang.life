import json
from pathlib import Path

BASE = Path("runtime/total_field/landing")

def load(name):
    return json.loads((BASE / name).read_text(encoding="utf-8"))

def test_intent_field_build_candidate_only():
    data = load("INTENT_FIELD_BUILD_V1.json")
    assert data["status"] == "CANDIDATE_ONLY"
    assert data["authority"]["formal_landing_allowed"] is False
    assert data["authority"]["total_field_final_authority"] is True

def test_forbidden_actions_include_hard_risks():
    data = load("INTENT_FIELD_BUILD_V1.json")
    joined = "\n".join(data["forbidden_actions"])
    for term in ["token", "password", "secret", ".env", "會員明文", "dump DB", "寫入 Odoo", "deploy", "restart"]:
        assert term in joined

def test_nl_counter_schema_blocks_formal_write():
    data = load("NL_COUNTER_PACKET_SCHEMA_V1.json")
    assert data["packet_status"] == "CANDIDATE_ONLY"
    assert data["initial_human_review_status"] == "WAIT_HUMAN_CONFIRM"
    assert data["formal_write_allowed"] is False
    assert data["db_write"] is False
    assert data["payment_allowed"] is False
    assert data["member_plaintext_allowed"] is False

def test_existing_minimum_delta_files_are_referenced():
    data = load("INTENT_FIELD_BUILD_V1.json")
    evidence = data["source_evidence"]
    assert evidence["odoo_menu_probe"].endswith("ODOO_MENU_READONLY_PROBE_REQUEST_V1.json")
    assert evidence["human_confirm_gate"].endswith("HUMAN_CONFIRM_GATE_V1.json")
