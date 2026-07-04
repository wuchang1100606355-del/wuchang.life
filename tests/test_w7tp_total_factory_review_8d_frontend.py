from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = ROOT / "docs/total_field/W7TP_TOTAL_FACTORY_REVIEW_8D_ENCRYPTED_SOVEREIGN_AI_FRONTEND.md"


def test_total_factory_review_converges_8d_frontend_definition():
    text = REVIEW_PATH.read_text(encoding="utf-8")

    assert "STATE=TOTAL_FACTORY_REVIEW_READY_CANDIDATE" in text
    assert "DECISION=VERIFY_READY_NOT_RELEASED" in text
    assert "8D加密式主權AI" in text
    assert "0.5-2B LLM" in text
    assert "自帶控制瀏覽器" in text
    assert "雲端候選總場規範" in text
    assert "AI 使用者介面" in text
    assert "ΩGI 總場 = final governance authority" in text


def test_total_factory_review_keeps_release_and_authority_blocked():
    text = REVIEW_PATH.read_text(encoding="utf-8")

    assert "Production release | HOLD" in text
    assert "External cloud enablement | HOLD" in text
    assert "Odoo / POS write | BLOCK" in text
    assert "Payment capture | BLOCK" in text
    assert "Member plaintext / raw browser page | BLOCK" in text
    assert "CLOUD_AUTHORITY=FALSE" in text
    assert "LLM_AUTHORITY=FALSE" in text
    assert "CODEX_AUTHORITY=FALSE" in text


def test_total_factory_review_pins_cloud_minimality_gates():
    text = REVIEW_PATH.read_text(encoding="utf-8")

    assert "UX_NOT_BELOW_CLOUD_BASELINE" in text
    assert "CLOUD_DEPENDENCY_PRECISE" in text
    assert "CLOUD_DEPENDENCY_LOW" in text
    assert "CLOUD_DEPENDENCY_NON_INFERABLE" in text
    assert "NO_STABLE_CLOUD_USER_ID" in text
    assert "cloud_dependency_not_precise_low_non_inferable" in text
    assert "total_factory_frontend_review_gate_failed" in text


def test_total_factory_review_links_evidence_refs():
    text = REVIEW_PATH.read_text(encoding="utf-8")

    required_refs = [
        "W7TP_8D_ENCRYPTED_SOVEREIGN_AI_USER_INTERFACE.md",
        "W7TP_USER_EXPERIENCE_CLOUD_MINIMALITY_POLICY.md",
        "W7TP_CLOUD_COMPUTE_PACKETIZED_RETURN_SPEC.md",
        "W7TP_XIAOJ_SERVICE_PERSONA_POLICY.md",
        "W7TP_MEMBER_AI_LLM_PREFIX_POLICY.md",
        "W7TP_BREAKTHROUGH_INVENTION_AI_COMPREHENSION_POLICY.md",
        "W7TP_PATENT_FIRST_SALES_FIRST_TOTAL_FIELD_STRATEGY.md",
    ]
    for ref in required_refs:
        assert ref in text


if __name__ == "__main__":
    test_total_factory_review_converges_8d_frontend_definition()
    test_total_factory_review_keeps_release_and_authority_blocked()
    test_total_factory_review_pins_cloud_minimality_gates()
    test_total_factory_review_links_evidence_refs()
    print("PASS")
