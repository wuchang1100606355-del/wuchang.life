from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs/total_field/COMMUNITY_INVENTOR_ACADEMIC_COOPERATION_MODEL.md"


def test_academic_cooperation_model_preserves_three_party_structure():
    doc = DOC_PATH.read_text(encoding="utf-8")
    assert "Individual inventor / social worker / system architect" in doc
    assert "Community development association / public-interest field owner" in doc
    assert "University, college, lab, research center, or academic reviewer" in doc
    assert "Academic public-interest field lab" in doc


def test_academic_model_blocks_premature_transfer_and_private_extraction():
    doc = DOC_PATH.read_text(encoding="utf-8")
    assert "No patent transfer" in doc
    assert "No donation completion" in doc
    assert "No revenue receipt" in doc
    assert "No permanent data custody" in doc
    assert "Do not frame the inventor as secretly extracting community assets" in doc
    assert "Do not let AI approve contract" in doc


def test_academic_model_requires_professional_and_ethics_gates():
    doc = DOC_PATH.read_text(encoding="utf-8")
    assert "Conflict-of-interest disclosure" in doc
    assert "Patent attorney review" in doc
    assert "Accountant review" in doc
    assert "Data protection review" in doc
    assert "Human-subject or ethics review" in doc
    assert "No-delete evidence package" in doc


def test_academic_model_links_official_reference_sources():
    doc = DOC_PATH.read_text(encoding="utf-8")
    assert "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=J0070007" in doc
    assert "https://edu.law.moe.gov.tw/LawContent.aspx?id=FL041667" in doc
    assert "https://law.moea.gov.tw/LawContent.aspx?id=FL009576" in doc
    assert "https://glrs.moi.gov.tw/LawContent.aspx?id=FL002637" in doc
    assert "https://www.mohw.gov.tw/dl-13651-d87538a5-83fc-4ef1-9c10-4645f4aa7aba.html" in doc
