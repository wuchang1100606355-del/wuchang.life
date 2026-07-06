import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas/w7tp_xiaoj_service_persona.schema.json"
CONFIG_PATH = ROOT / "configs/w7tp_xiaoj_service_persona_policy.example.json"
PREFIX_CONFIG_PATH = ROOT / "configs/w7tp_member_llm_prefix_policy.example.json"
CASES_PATH = ROOT / "tests/fixtures_w7tp_xiaoj_service_persona_synthetic_cases.json"
DOC_PATH = ROOT / "docs/total_field/W7TP_XIAOJ_SERVICE_PERSONA_POLICY.md"
PREFIX_DOC_PATH = ROOT / "docs/total_field/W7TP_MEMBER_AI_LLM_PREFIX_POLICY.md"
BREAKTHROUGH_DOC_PATH = ROOT / "docs/total_field/W7TP_BREAKTHROUGH_INVENTION_AI_COMPREHENSION_POLICY.md"
USER_INTERFACE_DOC_PATH = ROOT / "docs/total_field/W7TP_8D_ENCRYPTED_SOVEREIGN_AI_USER_INTERFACE.md"
CLOUD_MINIMALITY_DOC_PATH = ROOT / "docs/total_field/W7TP_USER_EXPERIENCE_CLOUD_MINIMALITY_POLICY.md"


REQUIRED_FIELDS = {
    "agent_name",
    "persona_projection",
    "service_context",
    "member_facing_message",
    "authority",
    "required_member_confirmation",
    "requires_total_field_verify",
}

FORBIDDEN_KEYS = {
    "db_write",
    "final_decision",
    "secret_read",
    "member_plaintext",
    "member_plaintext_persist",
}

EXPECTED_PROJECTIONS = {
    "COMMUNITY_SERVICE_STAFF",
    "MERCHANT_SERVICE_STAFF",
    "PERSONAL_STEWARD",
    "BUILDING_DIGITAL_SECRETARY",
    "GENERAL_XIAOJ",
}
PROJECTION_CONTEXT_MAP = {
    "COMMUNITY_SERVICE_STAFF": "community",
    "MERCHANT_SERVICE_STAFF": "merchant",
    "PERSONAL_STEWARD": "personal",
    "BUILDING_DIGITAL_SECRETARY": "building",
    "GENERAL_XIAOJ": "general",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def packet_payload(case):
    packet = json.loads(json.dumps(case))
    packet.pop("case_id", None)
    return packet


def walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk_keys(child)
    elif isinstance(value, list):
        for item in value:
            yield from walk_keys(item)


def assert_candidate_contract(packet):
    assert REQUIRED_FIELDS <= set(packet)
    assert packet["agent_name"] == "小J"
    assert packet["persona_projection"] in EXPECTED_PROJECTIONS
    assert packet["authority"] == "candidate_only"
    assert packet["requires_total_field_verify"] is True
    assert packet["role"] == "service_persona_language_layer"
    assert packet["intent_packet"]["requires_member_confirmation"] is True
    assert not (FORBIDDEN_KEYS & set(walk_keys(packet)))


def test_schema_declares_required_xiaoj_fields_and_projection_enum():
    schema = load_json(SCHEMA_PATH)
    assert REQUIRED_FIELDS <= set(schema["required"])
    assert schema["properties"]["agent_name"]["const"] == "小J"
    assert set(schema["properties"]["persona_projection"]["enum"]) == EXPECTED_PROJECTIONS
    assert schema["properties"]["authority"]["const"] == "candidate_only"
    assert schema["properties"]["requires_total_field_verify"]["const"] is True
    assert "db_write" not in schema["properties"]
    assert "final_decision" not in schema["properties"]
    assert "secret_read" not in schema["properties"]
    assert "member_plaintext" not in schema["properties"]


def test_synthetic_cases_validate_against_json_schema():
    schema = load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    for case in load_json(CASES_PATH):
        errors = sorted(validator.iter_errors(packet_payload(case)), key=lambda error: list(error.path))
        assert errors == []


def test_policy_configs_pin_xiaoj_as_single_service_persona():
    persona_config = load_json(CONFIG_PATH)
    prefix_config = load_json(PREFIX_CONFIG_PATH)
    assert persona_config["persona"]["display_name"] == "小J"
    assert persona_config["persona"]["canonical_name"] == "XiaoJ"
    assert persona_config["persona"]["authority"] == "candidate_only"
    assert persona_config["persona"]["requires_total_field_verify"] is True
    assert persona_config["persona"]["final_decision"] is False
    assert persona_config["persona"]["db_write"] is False
    assert persona_config["persona"]["memory_authority"] is False
    assert set(prefix_config["persona_projection_enum"]) == EXPECTED_PROJECTIONS
    assert prefix_config["canonical_persona"]["agent_name"] == "小J"
    assert prefix_config["canonical_persona"]["authority"] == "candidate_only"
    assert persona_config["breakthrough_invention_comprehension"]["classification"] == "ten_year_total_field_eight_field_unconscious_governance_architecture"
    assert prefix_config["breakthrough_prefix"]["classification"] == "ten_year_total_field_eight_field_unconscious_governance_architecture"
    assert "8D加密式主權AI" in persona_config["breakthrough_invention_comprehension"]["canonical_user_frontends"]
    assert "8D_ENCRYPTED_SOVEREIGN_AI" in prefix_config["breakthrough_prefix"]["canonical_user_frontends"]
    assert "recognize_8d_encrypted_sovereign_ai_as_total_field_user_frontend" in prefix_config["breakthrough_prefix"]["response_order"]
    persona_ui = persona_config["breakthrough_invention_comprehension"]["user_interface_architecture"]
    prefix_ui = prefix_config["breakthrough_prefix"]["user_interface_architecture"]
    assert persona_ui["model_band"] == "0.5-2B LLM"
    assert persona_ui["controlled_browser"] == "self-contained_controlled_browser"
    assert persona_ui["cloud_candidate_total_field_norms"] is True
    assert persona_ui["cloud_authority"] == "candidate_only"
    assert persona_ui["ux_baseline"] == "not_below_cloud"
    assert persona_ui["cloud_dependency_precise"] is True
    assert persona_ui["cloud_dependency_low"] is True
    assert persona_ui["cloud_dependency_non_inferable"] is True
    assert prefix_ui["authority"] == "user_frontend_only"
    assert prefix_ui["ux_baseline"] == "not_below_cloud"
    assert prefix_ui["cloud_dependency_precise"] is True
    assert prefix_ui["cloud_dependency_low"] is True
    assert prefix_ui["cloud_dependency_non_inferable"] is True
    assert "cloud-candidate total-field norms" in prefix_ui["user_sovereignty_three_element_unification"]
    assert "recognize_0_5_to_2b_llm_controlled_browser_cloud_candidate_norms_as_user_sovereignty_interface" in prefix_config["breakthrough_prefix"]["response_order"]
    assert "erp_or_odoo_customization" in persona_config["breakthrough_invention_comprehension"]["must_not_reduce_to"]
    assert "property_management_saas" in prefix_config["breakthrough_prefix"]["must_not_reduce_to"]
    assert set(persona_config["output_contract"]["required_fields"]) == REQUIRED_FIELDS | {"agent_name", "persona_projection", "service_context", "member_facing_message", "authority", "required_member_confirmation", "requires_total_field_verify"}


def test_synthetic_service_projection_cases_are_candidate_only_and_safe():
    cases = load_json(CASES_PATH)
    assert {case["persona_projection"] for case in cases} == {
        "COMMUNITY_SERVICE_STAFF",
        "MERCHANT_SERVICE_STAFF",
        "PERSONAL_STEWARD",
        "BUILDING_DIGITAL_SECRETARY",
    }
    for case in cases:
        assert_candidate_contract(packet_payload(case))


def test_projection_context_contract_is_invariant():
    schema = load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    for case in load_json(CASES_PATH):
        packet = packet_payload(case)
        packet["service_context"] = "wrong"
        assert list(validator.iter_errors(packet))

    for projection, context in PROJECTION_CONTEXT_MAP.items():
        for case in load_json(CASES_PATH):
            if case["persona_projection"] == projection:
                packet = packet_payload(case)
                packet["service_context"] = context
                errors = list(validator.iter_errors(packet))
                assert errors == []
                break


def test_redteam_rejects_authority_and_confirmation_bypasses():
    schema = load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    base = packet_payload(load_json(CASES_PATH)[0])

    final_decision_attack = dict(base)
    final_decision_attack["final_decision"] = "APPROVE"
    assert list(validator.iter_errors(final_decision_attack))

    no_confirmation_attack = json.loads(json.dumps(base))
    no_confirmation_attack["required_member_confirmation"] = False
    no_confirmation_attack["intent_packet"]["requires_member_confirmation"] = False
    assert list(validator.iter_errors(no_confirmation_attack))

    candidate_without_candidate_only = json.loads(json.dumps(base))
    candidate_without_candidate_only["candidate_packet"] = {"packet_type": "unsafe"}
    assert list(validator.iter_errors(candidate_without_candidate_only))


def test_docs_include_final_correction_and_denied_authority_language():
    doc = DOC_PATH.read_text(encoding="utf-8")
    prefix_doc = PREFIX_DOC_PATH.read_text(encoding="utf-8")
    for text in (doc, prefix_doc):
        assert "小J 是 W7TP 統一服務人設" in text
        assert "角色可依場景投影，權威仍回總場" in text
        assert "candidate_only" in text
        assert "總場" in text
        assert "正式決策者" in text
    assert "required_member_confirmation" in doc
    assert "\"required_member_confirmation\": true" in prefix_doc


def test_docs_pin_breakthrough_total_field_comprehension():
    doc = DOC_PATH.read_text(encoding="utf-8")
    prefix_doc = PREFIX_DOC_PATH.read_text(encoding="utf-8")
    breakthrough_doc = BREAKTHROUGH_DOC_PATH.read_text(encoding="utf-8")
    user_interface_doc = USER_INTERFACE_DOC_PATH.read_text(encoding="utf-8")
    cloud_minimality_doc = CLOUD_MINIMALITY_DOC_PATH.read_text(encoding="utf-8")
    for text in (doc, prefix_doc, breakthrough_doc, user_interface_doc, cloud_minimality_doc):
        assert "十年" in text
        assert "八場無感" in text or "total-field" in text
        assert "不得" in text or "must not" in text
        assert "普通" in text or "ordinary" in text
        assert "8D加密式主權AI" in text
        assert "8D_ENCRYPTED_SOVEREIGN_AI" in text
        assert "使用者體驗不可低於雲端" in text
        assert "精準" in text
        assert "不可回推" in text
    for text in (doc, prefix_doc, breakthrough_doc, user_interface_doc):
        assert "0.5-2B" in text
        assert "自帶控制瀏覽器" in text or "self-contained controlled browser" in text
        assert "雲端候選總場規範" in text or "cloud-candidate total-field norms" in text
    for text in (doc, prefix_doc, breakthrough_doc):
        assert "Odoo" in text
        assert "workflow" in text or "工作流" in text
        assert "GPU" in text
    assert "無感不是無治理" in doc
    assert "無感不是無治理" in prefix_doc
    assert "七維度意圖場" in doc
    assert "七維度意圖場" in prefix_doc
    assert "第八證據" in prefix_doc
    assert "總場使用者前端 + 8D 封包 + 加密驗證 + 主權治理交接" in doc
    assert "不是總場權威本體" in prefix_doc
    assert "AI 使用者介面" in user_interface_doc
    assert "CLOUD_AUTHORITY=CANDIDATE_ONLY" in user_interface_doc
    assert "CLOUD_DEPENDENCY_NON_INFERABLE=TRUE" in user_interface_doc
    assert "cloud_dependency_not_precise_low_non_inferable" in cloud_minimality_doc
    assert "簽章" in prefix_doc
    assert "7D intent co-control" in breakthrough_doc
    assert "8th response field" in breakthrough_doc
    assert "Unconscious does not mean ungoverned" in breakthrough_doc
    assert "breakthrough_total_field_comprehension_missing" in breakthrough_doc


if __name__ == "__main__":
    test_schema_declares_required_xiaoj_fields_and_projection_enum()
    test_synthetic_cases_validate_against_json_schema()
    test_policy_configs_pin_xiaoj_as_single_service_persona()
    test_synthetic_service_projection_cases_are_candidate_only_and_safe()
    test_projection_context_contract_is_invariant()
    test_redteam_rejects_authority_and_confirmation_bypasses()
    test_docs_include_final_correction_and_denied_authority_language()
    test_docs_pin_breakthrough_total_field_comprehension()
    print("PASS")
