import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas/w7tp_property_association_merge_relation.schema.json"
CONFIG_PATH = ROOT / "configs/w7tp_property_association_merge_relation.example.json"
DOC_PATH = ROOT / "docs/total_field/W7TP_PROPERTY_ASSOCIATION_MERGE_RELATION_MAP.md"


PROPERTY_ROLES = {
    "PROPERTY_CHAIRPERSON",
    "PROPERTY_VICE_CHAIRPERSON",
    "PROPERTY_TREASURER",
    "PROPERTY_GENERAL_MANAGER",
    "PROPERTY_UNIT_OWNER",
    "PROPERTY_RESIDENT",
    "PROPERTY_VEHICLE_TYPE",
    "PROPERTY_VEHICLE_COLOR",
    "PROPERTY_EQUIPMENT",
    "PROPERTY_FACILITY",
}

ASSOCIATION_ROLES = {
    "ASSOCIATION_IMMUTABLE_FOUNDER",
    "ASSOCIATION_CHAIRPERSON",
    "ASSOCIATION_SECRETARY_GENERAL",
    "ASSOCIATION_VICE_CHAIRPERSON",
    "ASSOCIATION_EXECUTIVE_DIRECTOR",
    "ASSOCIATION_DIRECTOR",
    "ASSOCIATION_EXECUTIVE_SUPERVISOR",
    "ASSOCIATION_SUPERVISOR",
    "ASSOCIATION_SECRETARY",
    "ASSOCIATION_STAFF",
    "ASSOCIATION_MEMBER",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_merge_relation_config_validates_against_schema():
    schema = load_json(SCHEMA_PATH)
    config = load_json(CONFIG_PATH)
    errors = sorted(Draft202012Validator(schema).iter_errors(config), key=lambda error: list(error.path))
    assert errors == []


def test_merge_relation_keeps_authority_candidate_only():
    config = load_json(CONFIG_PATH)
    assert config["merge_mode"] == "candidate_relation_only"
    assert config["authority"] == "candidate_only"
    assert config["requires_total_field_verify"] is True
    assert config["contains_member_plaintext"] is False
    assert config["plaintext_identity_forbidden"] is True
    boundary = config["authority_boundary"]
    assert boundary["candidate_only"] is True
    for key in [
        "final_decision",
        "db_write",
        "secret_read",
        "member_plaintext_read",
        "resident_plaintext_read",
        "payment_capture",
        "formal_send",
        "role_elevation_without_verifier",
    ]:
        assert boundary[key] is False


def test_property_and_association_branches_are_related_but_not_collapsed():
    config = load_json(CONFIG_PATH)
    property_branch = config["branches"]["property_service_branch"]
    association_branch = config["branches"]["association_service_branch"]

    assert property_branch["scene_context"] == "PROPERTY_CONTEXT"
    assert property_branch["xiaoj_projection"] == "BUILDING_DIGITAL_SECRETARY"
    assert property_branch["identity_feature_domain"] == "property"
    assert property_branch["handoff_group"] == "resident_property_management"
    assert set(property_branch["role_functions"]) == PROPERTY_ROLES

    assert association_branch["scene_context"] == "ASSOCIATION_CONTEXT"
    assert association_branch["xiaoj_projection"] == "COMMUNITY_SERVICE_STAFF"
    assert association_branch["identity_feature_domain"] == "association"
    assert association_branch["handoff_group"] == "association_sovereign_member"
    assert set(association_branch["role_functions"]) == ASSOCIATION_ROLES

    assert set(property_branch["role_functions"]).isdisjoint(set(association_branch["role_functions"]))
    assert config["merge_rules"]["service_view_can_merge"] is True
    assert config["merge_rules"]["role_refs_remain_independent"] is True
    assert config["merge_rules"]["no_cross_domain_role_override"] is True


def test_community_field_composition_covers_user_described_domains():
    config = load_json(CONFIG_PATH)
    composition = config["community_field_composition"]
    dimensions = {item["dimension_id"] for item in composition["dimensions"]}
    assert composition["field_name"] == "WUCHANG_COMMUNITY_TOTAL_FIELD"
    assert dimensions == {
        "PROPERTY_DIMENSION",
        "COMMERCE_DIMENSION",
        "TERRITORY_DIMENSION",
        "ASSOCIATION_DIMENSION",
        "FOUNDER_CALCULATION_DIMENSION",
        "COMMUNITY_LITERATURE_CORPUS_DIMENSION",
    }
    founder_knowledge = composition["founder_design_knowledge"]
    assert founder_knowledge["calculation_ref_mode"] == "ref_only"
    assert founder_knowledge["literature_corpus_ref_mode"] == "ref_only"
    assert founder_knowledge["plaintext_corpus_inline"] is False
    assert founder_knowledge["member_memory_authority"] is False
    assert founder_knowledge["direct_execution_authority"] is False
    assert founder_knowledge["requires_total_field_verify"] is True
    assert config["merge_rules"]["community_field_contains_property_commerce_territory_association"] is True
    assert config["merge_rules"]["founder_calculation_ref_only"] is True
    assert config["merge_rules"]["community_literature_corpus_ref_only"] is True


def test_relation_edges_cover_context_persona_handoff_and_founder_boundary():
    config = load_json(CONFIG_PATH)
    edges = {(edge["from"], edge["to"], edge["relation_type"]) for edge in config["relation_edges"]}
    assert ("PROPERTY_CONTEXT", "BUILDING_DIGITAL_SECRETARY", "SCENE_CONTEXT_TO_PERSONA") in edges
    assert ("ASSOCIATION_CONTEXT", "COMMUNITY_SERVICE_STAFF", "SCENE_CONTEXT_TO_PERSONA") in edges
    assert ("PROPERTY_CONTEXT", "resident_property_management", "HANDOFF_REF_GROUP") in edges
    assert ("ASSOCIATION_CONTEXT", "association_sovereign_member", "HANDOFF_REF_GROUP") in edges
    assert ("ASSOCIATION_IMMUTABLE_FOUNDER", "association_rotating_roles", "FOUNDER_IMMUTABILITY_OVERRIDES_ROTATION") in edges
    assert ("property_role_ref", "association_role_ref", "ROLE_BOUNDARY_SEPARATES_AUTHORITY") in edges
    assert ("WUCHANG_COMMUNITY_TOTAL_FIELD", "PROPERTY_DIMENSION", "COMMUNITY_FIELD_CONTAINS_DOMAIN") in edges
    assert ("WUCHANG_COMMUNITY_TOTAL_FIELD", "COMMERCE_DIMENSION", "COMMUNITY_FIELD_CONTAINS_DOMAIN") in edges
    assert ("WUCHANG_COMMUNITY_TOTAL_FIELD", "TERRITORY_DIMENSION", "COMMUNITY_FIELD_CONTAINS_DOMAIN") in edges
    assert ("WUCHANG_COMMUNITY_TOTAL_FIELD", "ASSOCIATION_DIMENSION", "COMMUNITY_FIELD_CONTAINS_DOMAIN") in edges
    assert ("TERRITORY_DIMENSION", "WUCHANG_COMMUNITY_TOTAL_FIELD", "TERRITORY_ANCHORS_COMMUNITY") in edges
    assert ("8D_SOVEREIGN_AI_COMMUNITY_XIAOJ", "WUCHANG_COMMUNITY_TOTAL_FIELD", "SOVEREIGN_AI_PERSONA_ANCHORS_COMMUNITY_FIELD") in edges
    assert ("SOCIAL_WORKER_GOVERNANCE_CENTER", "8D_SOVEREIGN_AI_COMMUNITY_XIAOJ", "SOCIAL_WORKER_GOVERNS_CARE_INTENT") in edges
    assert ("CAREGIVER_EMPLOYEE_EXECUTION", "8D_SOVEREIGN_AI_COMMUNITY_XIAOJ", "CAREGIVER_EMPLOYEE_EXECUTES_CARE") in edges
    assert ("ELDER_ACTIVE_PARTICIPATION", "PUBLIC_VALUE_DIMENSION", "ELDER_ACTIVE_PARTICIPATION_SUPPORTS_PUBLIC_VALUE") in edges
    assert ("W7TP_007_VOLUNTEER_DELIVERY", "PROPERTY_DIMENSION", "VOLUNTEER_DELIVERY_BRIDGES_PROPERTY_COMMERCE") in edges
    assert ("W7TP_007_VOLUNTEER_DELIVERY", "COMMERCE_DIMENSION", "VOLUNTEER_DELIVERY_BRIDGES_PROPERTY_COMMERCE") in edges
    assert ("FOUNDER_CALCULATION_DIMENSION", "WUCHANG_COMMUNITY_TOTAL_FIELD", "FOUNDER_CALCULATION_SUPPORTS_DESIGN") in edges
    assert ("COMMUNITY_LITERATURE_CORPUS_DIMENSION", "WUCHANG_COMMUNITY_TOTAL_FIELD", "LITERATURE_CORPUS_SUPPORTS_DESIGN") in edges


def test_source_refs_preserve_conversation_traceability():
    config = load_json(CONFIG_PATH)
    refs = {source["source_ref"] for source in config["source_refs"]}
    assert "CODEX_SESSION_REF:2026-06-28/019f0ec4-e4b8-7bf0-8075-a57447908611" in refs
    assert "CODEX_ATTACHMENT_REF:f3769bdf-07e2-4c75-9e2b-506b6b7160b6" in refs
    assert "CODEX_SESSION_REF:2026-06-26/019f0526-d478-7ea3-912a-3f17ad165396" in refs
    assert "CODEX_SESSION_REF:2026-06-30/019f18ea-cdde-78c3-87d3-9c4e73669257" in refs
    assert "CODEX_SESSION_REF:2026-07-02/019f22d3-901a-7672-b5b1-72a21b67018c" in refs
    assert "REPO_DOC_REF:Taiji_Governance/system_info/wuchang_jurisdiction_coordinate_analysis_2026-05-12.md" in refs
    assert "REPO_DOC_REF:Taiji_Governance/system_info/community_branch_group_member_mapping_2026-05-12.md" in refs
    assert "REPO_DOC_REF:docs/strategy/wuchang_sovereign_economic_engine_v8_zh.md" in refs


def test_docs_capture_merge_boundary():
    doc = DOC_PATH.read_text(encoding="utf-8")
    assert "這是社區總場，不只是物業加協會" in doc
    assert "有物業、有商業、有地域、有協會" in doc
    assert "創辦人的細緻推算與社區大量文獻" in doc
    assert "關聯圖只做 candidate relation" in doc
    assert "大樓數位秘書小J" in doc
    assert "社區服務員小J" in doc
    assert "ASSOCIATION_IMMUTABLE_FOUNDER" in doc
    assert "8D_SOVEREIGN_AI_COMMUNITY_XIAOJ" in doc
    assert "8維碼主權 AI 社區小J" in doc
    assert "社工是意圖場的人類治理責任人與社區知能中樞" in doc
    assert "照服員是照護執行員工" in doc
    assert "退而不休" in doc
    assert "不得互相覆蓋" in doc


if __name__ == "__main__":
    test_merge_relation_config_validates_against_schema()
    test_merge_relation_keeps_authority_candidate_only()
    test_property_and_association_branches_are_related_but_not_collapsed()
    test_community_field_composition_covers_user_described_domains()
    test_relation_edges_cover_context_persona_handoff_and_founder_boundary()
    test_source_refs_preserve_conversation_traceability()
    test_docs_capture_merge_boundary()
    print("PASS")
