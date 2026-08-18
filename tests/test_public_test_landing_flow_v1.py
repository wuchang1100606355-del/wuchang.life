import json
from pathlib import Path

BASE = Path("runtime/total_field/landing")
PACKET = BASE / "PUBLIC_TEST_LANDING_FLOW_V1.json"
DOC = Path("docs/landing/PUBLIC_TEST_LANDING_FLOW_V1.md")

def load():
    return json.loads(PACKET.read_text(encoding="utf-8"))

def test_public_test_flow_is_candidate_only():
    data = load()
    assert data["status"] == "CANDIDATE_ONLY"
    assert data["formal_landing_allowed"] is False
    assert data["authority"]["human_confirm_required"] is True
    assert data["authority"]["formal_write_allowed"] is False

def test_source_artifacts_exist():
    data = load()
    evidence = data["source_evidence"]
    for key in [
        "intent_field_build_packet",
        "nl_counter_schema",
        "odoo_menu_probe",
        "human_confirm_gate",
        "ten_real_world_cases",
    ]:
        assert Path(evidence[key]).exists(), key

def test_global_constraints_block_hard_risks():
    data = load()
    constraints = data["global_constraints"]
    for key, value in constraints.items():
        assert value is False, key

def test_flow_has_required_steps():
    data = load()
    steps = {step["step_id"] for step in data["flow_steps"]}
    required = {
        "S01_SCOPE_LOCK",
        "S02_MENU_READONLY",
        "S03_NL_COUNTER_PACKET",
        "S04_HUMAN_CONFIRM_GATE",
        "S05_REAL_WORLD_TESTS",
        "S06_PUBLIC_TEST_ENTRY_READY",
    }
    assert required.issubset(steps)

def test_forbidden_actions_cover_hard_risks():
    data = load()
    joined = "\n".join(data["forbidden_actions"])
    for term in [
        "token",
        "password",
        "secret",
        ".env",
        "google_credentials.xml",
        "data/internal_members",
        "會員明文",
        "dump DB",
        "DB write",
        "寫入 Odoo",
        "deploy",
        "restart",
        "reboot",
        "git push",
    ]:
        assert term in joined

def test_doc_created_and_matches_next_action():
    text = DOC.read_text(encoding="utf-8")
    assert "STATE=CANDIDATE_ONLY" in text
    assert "NEXT_SINGLE_ACTION=建立 PUBLIC_TEST_ENTRY_CANDIDATE_V1" in text
