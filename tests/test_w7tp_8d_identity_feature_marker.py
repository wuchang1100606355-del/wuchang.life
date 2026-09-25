import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas/w7tp_8d_identity_feature_marker.schema.json"
CONFIG_PATH = ROOT / "configs/w7tp_8d_identity_feature_marker.example.json"
CASES_PATH = ROOT / "tests/fixtures_w7tp_8d_identity_feature_marker_synthetic_cases.json"
DOC_PATH = ROOT / "docs/total_field/W7TP_8D_IDENTITY_FEATURE_MARKING_POLICY.md"
ATLAS_SCHEMA_PATH = ROOT / "W7TP_FIELD_ATLAS/schemas/w7tp_8d_identity_code.schema.yaml"


MERCHANT_FUNCTIONS = {
    "MERCHANT_RESPONSIBLE_PERSON",
    "MERCHANT_STORE_MANAGER",
    "MERCHANT_STAFF",
    "MERCHANT_TAGGED_MEMBER",
    "MERCHANT_MEMBER",
}

PROPERTY_FUNCTIONS = {
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

ASSOCIATION_FUNCTIONS = {
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

FORBIDDEN_KEYS = {
    "name",
    "phone",
    "address",
    "license_plate",
    "id_number",
    "token",
    "secret",
    "password",
    "final_decision",
    "db_write",
    "secret_read",
    "member_plaintext_persist",
}

SPATIAL_BINDING_MODES = {
    "STATIC_GROUP_FIELD_ANCHOR",
    "STATIC_ORGANIZATION_JURISDICTION",
    "STATIC_PROPERTY_OR_FACILITY_ANCHOR",
    "STATIC_MERCHANT_OR_SERVICE_AREA",
}

POSITIONING_SUBJECTS = {
    "GROUP_ENTITY",
    "ORGANIZATION",
    "ASSOCIATION_JURISDICTION",
    "PROPERTY_OR_BUILDING",
    "MERCHANT_SITE",
    "EQUIPMENT",
    "FACILITY",
}

DEMOGRAPHIC_COHORTS = {
    "CHILDREN",
    "YOUTH",
    "YOUNG_ADULTS",
    "WORKING_AGE",
    "ELDERLY",
    "OLDER_ELDERLY",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def packet_payload(case):
    packet = json.loads(json.dumps(case))
    packet.pop("case_id", None)
    return packet


def founder_case():
    return next(
        case for case in load_json(CASES_PATH)
        if "ASSOCIATION_IMMUTABLE_FOUNDER" in case["feature_domains"]["association"]["functions"]
    )


def walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk_keys(child)
    elif isinstance(value, list):
        for item in value:
            yield from walk_keys(item)


def all_functions_from_schema(schema, domain):
    if domain == "merchant":
        return set(schema["properties"]["feature_domains"]["properties"]["merchant"]["properties"]["functions"]["items"]["enum"])
    if domain == "property":
        return set(schema["properties"]["feature_domains"]["properties"]["property"]["properties"]["functions"]["items"]["enum"])
    return set(schema["properties"]["feature_domains"]["properties"]["association"]["properties"]["functions"]["items"]["enum"])


def assert_marker_contract(packet):
    assert packet["feature_assertion_mode"] == "candidate_marker_only"
    assert packet["contains_member_plaintext"] is False
    assert packet["plaintext_identity_forbidden"] is True
    assert packet["requires_total_field_verify"] is True
    assert not (FORBIDDEN_KEYS & set(walk_keys(packet)))
    vehicle = packet["feature_domains"]["property"]["vehicle_features"]
    assert vehicle.get("license_plate_plaintext_included") is False
    association = packet["feature_domains"]["association"]
    if "ASSOCIATION_IMMUTABLE_FOUNDER" in association["functions"]:
        assert association["immutable_founder_marker"] is True
        assert association["founder_marker_mutable"] is False
        assert association["role_rotation_can_override"] is False
        assert association["founder_ref"].startswith("FOUNDER_REF:")
    spatial = packet.get("spatial_binding")
    if spatial:
        assert packet["subject_basis"] in {"GROUP_ENTITY", "EQUIPMENT", "FACILITY"}
        assert packet["identity_scope"] in {"GROUP_IDENTITY", "ASSET_OR_FACILITY_IDENTITY"}
        assert spatial["static_group_positioning_only"] is True
        assert spatial["personal_positioning_allowed"] is False
        assert spatial["contains_precise_person_location"] is False
        assert spatial["contains_member_plaintext"] is False
        assert spatial["masking_definition"] == "MASKED_DATA_IS_NON_IDENTIFIABLE_PERSONAL_DATA"
        assert spatial["reidentification_possible"] is False
        assert spatial["masked_payload_can_identify_person"] is False
        assert spatial["requires_total_field_verify"] is True
        demographic = spatial.get("aggregate_demographic_context")
        if demographic:
            assert demographic["aggregation_level"] in {"LI_LEVEL", "SERVICE_AREA_LEVEL", "PUBLIC_STATISTICAL_AREA"}
            assert demographic["ranking_allowed"] is True
            assert demographic["person_level_data_allowed"] is False
            assert demographic["household_level_data_allowed"] is False
            assert demographic["contains_member_plaintext"] is False
            assert demographic["reidentification_possible"] is False
            assert demographic["masked_payload_can_identify_person"] is False


def test_schema_covers_requested_identity_feature_enums():
    schema = load_json(SCHEMA_PATH)
    assert set(schema["properties"]["subject_basis"]["enum"]) >= {"NATURAL_PERSON", "GROUP_ENTITY", "VEHICLE", "EQUIPMENT", "FACILITY"}
    assert set(schema["properties"]["residency_feature"]["enum"]) >= {"COMMUNITY_RESIDENT", "NON_COMMUNITY_RESIDENT"}
    assert set(schema["properties"]["merchant_feature"]["enum"]) >= {"COMMUNITY_MERCHANT", "NON_COMMUNITY_MERCHANT"}
    assert all_functions_from_schema(schema, "merchant") == MERCHANT_FUNCTIONS
    assert all_functions_from_schema(schema, "property") == PROPERTY_FUNCTIONS
    assert all_functions_from_schema(schema, "association") == ASSOCIATION_FUNCTIONS
    assert schema["properties"]["feature_assertion_mode"]["const"] == "candidate_marker_only"
    assert schema["properties"]["requires_total_field_verify"]["const"] is True
    spatial = schema["properties"]["spatial_binding"]["properties"]
    assert set(spatial["binding_mode"]["enum"]) == SPATIAL_BINDING_MODES
    assert set(spatial["positioning_subject"]["enum"]) == POSITIONING_SUBJECTS
    assert spatial["personal_positioning_allowed"]["const"] is False
    assert spatial["masking_definition"]["const"] == "MASKED_DATA_IS_NON_IDENTIFIABLE_PERSONAL_DATA"
    demographic = spatial["aggregate_demographic_context"]["properties"]
    assert set(demographic["cohort_buckets"]["items"]["enum"]) == DEMOGRAPHIC_COHORTS
    assert demographic["person_level_data_allowed"]["const"] is False
    assert demographic["household_level_data_allowed"]["const"] is False
    assert demographic["masked_payload_can_identify_person"]["const"] is False


def test_synthetic_cases_validate_against_json_schema():
    schema = load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    for case in load_json(CASES_PATH):
        errors = sorted(validator.iter_errors(packet_payload(case)), key=lambda error: list(error.path))
        assert errors == []


def test_example_config_is_ref_only_and_denies_authority():
    config = load_json(CONFIG_PATH)
    assert config["feature_assertion_mode"] == "candidate_marker_only"
    assert config["requires_total_field_verify"] is True
    assert config["contains_member_plaintext"] is False
    assert set(config["merchant_feature_functions"]) == MERCHANT_FUNCTIONS
    assert set(config["property_feature_functions"]) == PROPERTY_FUNCTIONS
    assert set(config["association_feature_functions"]) == ASSOCIATION_FUNCTIONS
    assert "final_decision" in config["denied_authority"]
    assert "db_write" in config["denied_authority"]
    assert "secret_read" in config["denied_authority"]
    assert config["static_group_spatial_positioning_policy"]["static_group_positioning_only"] is True
    assert config["static_group_spatial_positioning_policy"]["personal_positioning_allowed"] is False
    assert config["aggregate_demographic_spatial_policy"]["non_commercial_institution"] is True
    assert config["aggregate_demographic_spatial_policy"]["resident_protection_intent"] is True
    assert config["aggregate_demographic_spatial_policy"]["person_level_data_allowed"] is False
    assert config["masking_definition_policy"]["definition"] == "MASKED_DATA_IS_NON_IDENTIFIABLE_PERSONAL_DATA"
    assert config["masking_definition_policy"]["reidentification_possible"] is False
    assert "personal_positioning" in config["denied_authority"]
    assert "reidentifiable_masked_payload" in config["denied_authority"]


def test_synthetic_identity_feature_cases_cover_requested_domains():
    cases = load_json(CASES_PATH)
    assert len(cases) == 5
    assert any(case["residency_feature"] == "COMMUNITY_RESIDENT" for case in cases)
    assert any(case["merchant_feature"] == "COMMUNITY_MERCHANT" for case in cases)
    assert any(case["feature_domains"]["property"]["enabled"] for case in cases)
    assert any(case["feature_domains"]["association"]["enabled"] for case in cases)
    assert any(case.get("spatial_binding") for case in cases)
    assert any(
        case.get("spatial_binding", {}).get("aggregate_demographic_context")
        for case in cases
    )
    assert any(
        "ASSOCIATION_IMMUTABLE_FOUNDER" in case["feature_domains"]["association"]["functions"]
        for case in cases
    )
    for case in cases:
        assert_marker_contract(packet_payload(case))


def test_redteam_rejects_authority_and_founder_mutation_bypasses():
    schema = load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    base = packet_payload(founder_case())

    db_write_attack = dict(base)
    db_write_attack["db_write"] = True
    assert list(validator.iter_errors(db_write_attack))

    founder_override_attack = json.loads(json.dumps(base))
    founder_override_attack["feature_domains"]["association"]["founder_marker_mutable"] = True
    assert list(validator.iter_errors(founder_override_attack))

    missing_founder_ref_attack = json.loads(json.dumps(base))
    del missing_founder_ref_attack["feature_domains"]["association"]["founder_ref"]
    assert list(validator.iter_errors(missing_founder_ref_attack))


def test_redteam_rejects_domain_flag_mismatch_bypasses():
    schema = load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)

    merchant_case = packet_payload(load_json(CASES_PATH)[1])
    merchant_disabled_attack = json.loads(json.dumps(merchant_case))
    merchant_disabled_attack["feature_domains"]["merchant"]["enabled"] = False
    assert list(validator.iter_errors(merchant_disabled_attack))

    non_merchant_case = packet_payload(load_json(CASES_PATH)[0])
    non_merchant_function_attack = json.loads(json.dumps(non_merchant_case))
    non_merchant_function_attack["feature_domains"]["merchant"]["enabled"] = True
    non_merchant_function_attack["feature_domains"]["merchant"]["functions"] = ["MERCHANT_STORE_MANAGER"]
    assert list(validator.iter_errors(non_merchant_function_attack))

    association_case = packet_payload(founder_case())
    disabled_association_role_attack = json.loads(json.dumps(association_case))
    disabled_association_role_attack["feature_domains"]["association"]["enabled"] = False
    assert list(validator.iter_errors(disabled_association_role_attack))


def test_redteam_rejects_subject_basis_identity_scope_cross_field_bypass():
    schema = load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    base = packet_payload(load_json(CASES_PATH)[0])

    personal_as_group_scope = json.loads(json.dumps(base))
    personal_as_group_scope["subject_basis"] = "NATURAL_PERSON"
    personal_as_group_scope["identity_scope"] = "GROUP_IDENTITY"
    assert list(validator.iter_errors(personal_as_group_scope))

    group_as_personal_scope = json.loads(json.dumps(base))
    group_as_personal_scope["subject_basis"] = "GROUP_ENTITY"
    group_as_personal_scope["identity_scope"] = "BASIC_PERSONAL_IDENTITY"
    assert list(validator.iter_errors(group_as_personal_scope))

    equipment_as_personal_scope = json.loads(json.dumps(base))
    equipment_as_personal_scope["subject_basis"] = "EQUIPMENT"
    equipment_as_personal_scope["identity_scope"] = "BASIC_PERSONAL_IDENTITY"
    assert list(validator.iter_errors(equipment_as_personal_scope))


def test_redteam_rejects_personal_positioning_and_reidentifiable_masking():
    schema = load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)

    spatial_case = packet_payload(load_json(CASES_PATH)[2])

    natural_person_positioning_attack = json.loads(json.dumps(spatial_case))
    natural_person_positioning_attack["subject_basis"] = "NATURAL_PERSON"
    natural_person_positioning_attack["identity_scope"] = "BASIC_PERSONAL_IDENTITY"
    assert list(validator.iter_errors(natural_person_positioning_attack))

    precise_coordinate_attack = json.loads(json.dumps(spatial_case))
    precise_coordinate_attack["spatial_binding"]["latitude"] = 25.0804429673534
    precise_coordinate_attack["spatial_binding"]["longitude"] = 121.497961092329
    assert list(validator.iter_errors(precise_coordinate_attack))

    reidentification_attack = json.loads(json.dumps(spatial_case))
    reidentification_attack["spatial_binding"]["reidentification_possible"] = True
    assert list(validator.iter_errors(reidentification_attack))

    demographic_case = packet_payload(load_json(CASES_PATH)[-1])
    person_level_demographic_attack = json.loads(json.dumps(demographic_case))
    person_level_demographic_attack["spatial_binding"]["aggregate_demographic_context"]["person_level_data_allowed"] = True
    assert list(validator.iter_errors(person_level_demographic_attack))


def test_docs_and_field_atlas_reference_feature_marker_boundary():
    doc = DOC_PATH.read_text(encoding="utf-8")
    atlas = ATLAS_SCHEMA_PATH.read_text(encoding="utf-8")
    assert "八維碼身份可標記身份特徵" in doc
    assert "標記不是正式身分裁決" in doc
    assert "創辦人（不可變更）" in doc
    assert "靜態團體定位" in doc
    assert "遮罩後必須無法辨識個資" in doc
    assert "聚合人口統計 ref" in doc
    assert "identity_feature_marker_ref" in atlas
    assert "candidate_marker_only" in atlas
    assert "ASSOCIATION_IMMUTABLE_FOUNDER" in atlas


if __name__ == "__main__":
    test_schema_covers_requested_identity_feature_enums()
    test_synthetic_cases_validate_against_json_schema()
    test_example_config_is_ref_only_and_denies_authority()
    test_synthetic_identity_feature_cases_cover_requested_domains()
    test_redteam_rejects_authority_and_founder_mutation_bypasses()
    test_redteam_rejects_domain_flag_mismatch_bypasses()
    test_redteam_rejects_subject_basis_identity_scope_cross_field_bypass()
    test_redteam_rejects_personal_positioning_and_reidentifiable_masking()
    test_docs_and_field_atlas_reference_feature_marker_boundary()
    print("PASS")
