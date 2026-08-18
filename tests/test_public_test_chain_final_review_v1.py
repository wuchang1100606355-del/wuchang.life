import json
from pathlib import Path

BASE = Path("runtime/total_field/landing")
PACKET = BASE / "PUBLIC_TEST_CHAIN_FINAL_REVIEW_V1.json"
DOC = Path("docs/landing/PUBLIC_TEST_CHAIN_FINAL_REVIEW_V1.md")

def load():
    # 中文註解：讀取公開測試鏈路最終審查封包
    return json.loads(PACKET.read_text(encoding="utf-8"))

def test_final_review_blocks_formal_actions():
    # 中文註解：最終審查仍禁止正式落地與高風險動作
    data = load()
    assert data["status"] == "FINAL_REVIEW_CANDIDATE"
    assert data["formal_landing_allowed"] is False
    assert data["deploy_allowed"] is False
    assert data["restart_allowed"] is False
    assert data["db_write_allowed"] is False
    assert data["payment_allowed"] is False
    assert data["member_plaintext_allowed"] is False

def test_required_artifacts_exist():
    # 中文註解：確認前序所有封包與文件存在
    data = load()
    for item in data["required_artifacts"]:
        assert Path(item).exists(), item

def test_chain_decision_is_candidate_pass_and_formal_hold():
    # 中文註解：候選鏈路可人審，但正式落地仍 HOLD
    data = load()
    decision = data["chain_decision"]
    assert decision["ready_for_public_test_human_review"] is True
    assert decision["ready_for_formal_landing"] is False
    assert decision["ready_for_db_write"] is False
    assert decision["ready_for_payment"] is False
    assert decision["ready_for_member_plaintext"] is False
    assert decision["ready_for_deploy"] is False
    assert decision["decision"] == "PASS_CANDIDATE_CHAIN_HOLD_FORMAL"

def test_forbidden_next_actions_cover_hard_risks():
    # 中文註解：確認下一步禁止項覆蓋全部硬風險
    data = load()
    joined = "\n".join(data["forbidden_next_actions"])
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

def test_hard_risk_result_all_false():
    # 中文註解：本鏈路沒有執行硬風險動作
    data = load()
    for key, value in data["hard_risk_result"].items():
        assert value is False, key

def test_doc_created_and_next_action_matches():
    # 中文註解：確認最終審查文件存在且下一步一致
    text = DOC.read_text(encoding="utf-8")
    assert "STATE=PASS_CANDIDATE_CHAIN_HOLD_FORMAL" in text
    assert "NEXT_SINGLE_ACTION=人審確認是否建立 PUBLIC_TEST_FRONTEND_DRAFT_V1；仍不部署" in text
