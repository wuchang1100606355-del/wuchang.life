import json
from pathlib import Path

BASE = Path("runtime/total_field/landing")
PACKET = BASE / "PUBLIC_TEST_ENTRY_CANDIDATE_V1.json"
DOC = Path("docs/landing/PUBLIC_TEST_ENTRY_CANDIDATE_V1.md")

def load():
    # 中文註解：讀取前場入口候選封包
    return json.loads(PACKET.read_text(encoding="utf-8"))

def test_entry_is_candidate_only_and_no_formal_actions():
    # 中文註解：確認入口仍是候選，不允許正式動作
    data = load()
    assert data["status"] == "CANDIDATE_ONLY"
    assert data["formal_landing_allowed"] is False
    assert data["deploy_allowed"] is False
    assert data["restart_allowed"] is False
    assert data["db_write_allowed"] is False
    assert data["payment_allowed"] is False
    assert data["member_plaintext_allowed"] is False

def test_source_artifacts_exist():
    # 中文註解：確認前面已建立的來源封包仍存在
    data = load()
    evidence = data["source_evidence"]
    for key in [
        "public_test_landing_flow_packet",
        "intent_field_build_packet",
        "nl_counter_schema",
        "odoo_menu_probe",
        "human_confirm_gate",
        "ten_real_world_cases",
    ]:
        assert Path(evidence[key]).exists(), key

def test_visible_functions_are_candidate_safe():
    # 中文註解：確認前場可見功能僅限候選測試
    data = load()
    visible = "\n".join(data["entry_definition"]["visible_functions"])
    assert "點餐詢問" in visible
    assert "預購候選" in visible
    assert "寄杯候選" in visible
    assert "任務券候選" in visible
    assert "人審確認狀態" in visible
    assert "正式金流" not in visible
    assert "正式建立訂單" not in visible

def test_forbidden_runtime_actions_cover_hard_risks():
    # 中文註解：確認硬風險都被封鎖
    data = load()
    joined = "\n".join(data["forbidden_runtime_actions"])
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
        "正式金流",
        "deploy",
        "restart",
        "reboot",
        "router write",
        "git push",
    ]:
        assert term in joined

def test_human_review_policy_is_locked():
    # 中文註解：確認小J只能候選，人審為必要條件
    data = load()
    policy = data["human_review_policy"]
    assert policy["human_confirm_required"] is True
    assert policy["default_state"] == "WAIT_HUMAN_CONFIRM"
    assert policy["approve_state"] == "CONFIRMED_BY_HUMAN"
    assert policy["reject_state"] == "REJECTED_BY_HUMAN"
    assert policy["hard_risk_state"] == "HOLD_HARD_RISK"
    assert policy["xiaoj_authority"] == "CANDIDATE_ONLY"

def test_doc_created_and_matches_next_action():
    # 中文註解：確認說明文件存在且下一步正確
    text = DOC.read_text(encoding="utf-8")
    assert "STATE=CANDIDATE_ONLY" in text
    assert "NEXT_SINGLE_ACTION=建立 PUBLIC_TEST_CHAIN_FINAL_REVIEW_V1" in text
