from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STRATEGY_PATH = ROOT / "docs/total_field/W7TP_PATENT_FIRST_SALES_FIRST_TOTAL_FIELD_STRATEGY.md"
ENGINE_PATH = ROOT / "docs/strategy/wuchang_sovereign_economic_engine_v8_zh.md"
COMPREHENSION_PATH = ROOT / "docs/total_field/W7TP_BREAKTHROUGH_INVENTION_AI_COMPREHENSION_POLICY.md"
USER_INTERFACE_PATH = ROOT / "docs/total_field/W7TP_8D_ENCRYPTED_SOVEREIGN_AI_USER_INTERFACE.md"
CLOUD_MINIMALITY_PATH = ROOT / "docs/total_field/W7TP_USER_EXPERIENCE_CLOUD_MINIMALITY_POLICY.md"


def test_patent_first_sales_first_total_field_strategy_is_recorded():
    text = STRATEGY_PATH.read_text(encoding="utf-8")

    assert "不是先完整打造系統再找錢" in text
    assert "8D加密式主權AI" in text
    assert "8D_ENCRYPTED_SOVEREIGN_AI" in text
    assert "0.5-2B LLM" in text
    assert "self-contained controlled browser" in text
    assert "cloud-candidate total-field norms" in text
    assert "先專利占位" in text
    assert "先銷售可落地外層成果" in text
    assert "第一桶金" in text
    assert "ΩGI = ⋂ᵢ₌₁⁸ Ωᵢ" in text
    assert "8D intent packet" in text
    assert "no-GPU low-latency governance verification path" in text
    assert "社工治理中樞規劃" in text
    assert "物業商業外送治理模組" in text
    assert "核心黑盒" not in text
    assert "full eight-field collapse logic" in text


def test_sovereign_economic_engine_uses_first_bucket_route():
    text = ENGINE_PATH.read_text(encoding="utf-8")

    assert "專利先行與第一桶金路線" in text
    assert "先專利占位" in text
    assert "第一桶金反哺總場" in text
    assert "總場再串接社區" in text
    assert "不得建議在未經專利與合約審查前" in text


def test_ai_comprehension_policy_blocks_premature_core_disclosure():
    text = COMPREHENSION_PATH.read_text(encoding="utf-8")

    assert "Patent-First Sales-First Rule" in text
    assert "先專利占位" in text
    assert "AI must not recommend premature full disclosure" in text
    assert "社區小J導入包" in text
    assert "8維碼治理顧問" in text
    assert "第一桶金反哺總場，總場再串接社區" in text


def test_8d_encrypted_sovereign_ai_user_interface_definition():
    text = USER_INTERFACE_PATH.read_text(encoding="utf-8")

    assert "8D加密式主權AI" in text
    assert "0.5-2B LLM" in text
    assert "自帶控制瀏覽器" in text
    assert "雲端候選總場規範" in text
    assert "三要素合一" in text
    assert "AI 使用者介面" in text
    assert "It is not the total-field authority itself" in text
    assert "CLOUD_AUTHORITY=CANDIDATE_ONLY" in text
    assert "使用者體驗不可低於雲端" in text
    assert "CLOUD_DEPENDENCY_NON_INFERABLE=TRUE" in text


def test_user_experience_cloud_minimality_policy():
    text = CLOUD_MINIMALITY_PATH.read_text(encoding="utf-8")

    assert "使用者體驗不可低於雲端" in text
    assert "雲端依賴需又精準、又低、又無可回推" in text
    assert "CLOUD_DEPENDENCY_PRECISE=TRUE" in text
    assert "CLOUD_DEPENDENCY_LOW=TRUE" in text
    assert "CLOUD_DEPENDENCY_NON_INFERABLE=TRUE" in text
    assert "cloud_dependency_not_precise_low_non_inferable" in text
    assert "stable cross-session user identifier" in text


if __name__ == "__main__":
    test_patent_first_sales_first_total_field_strategy_is_recorded()
    test_8d_encrypted_sovereign_ai_user_interface_definition()
    test_user_experience_cloud_minimality_policy()
    test_sovereign_economic_engine_uses_first_bucket_route()
    test_ai_comprehension_policy_blocks_premature_core_disclosure()
    print("PASS")
