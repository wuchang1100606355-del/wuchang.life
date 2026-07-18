import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/w7tp_secondary_cloud_packet_ramp.py"
SCHEMA_NAMES = [
    "w7tp_member_entry_packet.schema.json",
    "w7tp_identity_authority_packet.schema.json",
    "w7tp_scenario_translation_packet.schema.json",
    "w7tp_capability_pull_request_packet.schema.json",
    "w7tp_capability_packet.schema.json",
    "w7tp_local_reconstruction_packet.schema.json",
    "w7tp_secondary_cloud_verification_packet.schema.json",
]

spec = importlib.util.spec_from_file_location("w7tp_secondary_cloud_packet_ramp", MODULE_PATH)
ramp = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(ramp)


def member_entry():
    return {
        "packet_id": "PKT-ENTRY-0001",
        "schema_version": "W7TP-MEMBER-ENTRY/1.0",
        "identity_ref": "identity:member-0001",
        "scenario_ref": "scenario:ASSOCIATION",
        "requested_service_ref": "service:association.activity",
        "device_binding_ref": "device:binding-0001",
        "consent_ref": "consent:member-0001-v1",
        "authorization_ref": "authorization:association-activity-0001",
        "withdrawal_ref": "withdrawal:member-0001-current",
        "qualification_ref": "qualification:association-member-0001",
        "envelope": {
            "authority_scope": ["association:activity:read"],
            "consent_state": "ACTIVE",
            "revocation_state": "CLEAR",
            "ttl_seconds": 300,
            "nonce": "entry-nonce-0001",
            "protocol": "W7TP-8D-PACKET-NATIVE/1.0",
            "verifier_ref": "verifier:taiji01.identity",
        },
    }


def identity_authority():
    return {
        "packet_id": "PKT-AUTHORITY-0001",
        "schema_version": "W7TP-IDENTITY-AUTHORITY/1.0",
        "identity_ref": "identity:member-0001",
        "role_refs": ["role:association.member"],
        "authority_scope": ["association:activity:read"],
        "consent_state": "ACTIVE",
        "revocation_state": "CLEAR",
        "consent_ref": "consent:member-0001-v1",
        "authorization_ref": "authorization:association-activity-0001",
        "withdrawal_ref": "withdrawal:member-0001-current",
        "qualification_ref": "qualification:association-member-0001",
        "device_binding_ref": "device:binding-0001",
        "scenario_ref": "scenario:ASSOCIATION",
        "envelope_verified": True,
    }


def scenario_translation():
    packet = {
        "packet_id": "PKT-8D-ASSOCIATION-0001",
        "schema_version": "W7TP-SCENARIO-TRANSLATION/1.0",
        "selected_container": "ASSOCIATION",
        "packet_type": "ASSOCIATION_SERVICE_PACKET",
        "capability_ref": "CAP_ASSOCIATION_SERVICE_V1",
        "destination_field": "ASSOCIATION_SERVICE_FIELD",
        "d1_intent": {"service_result_ref": "result:association.activity.list"},
        "d2_state": {
            "identity_ref": "identity:member-0001",
            "role_refs": ["role:association.member"],
            "consent_state": "ACTIVE",
            "workflow_state_ref": "workflow:association.activity.requested",
        },
        "d3_coordinate": {
            "node_ref": "taiji01",
            "container": "ASSOCIATION",
            "service_field": "ASSOCIATION_SERVICE_FIELD",
            "module_ref": "module:association.local",
            "task_ref": "task:association.activity.list",
        },
        "d4_evidence": {
            "evidence_refs": ["evidence:association.contract.v1"],
            "evidence_hashes": ["a" * 64],
        },
        "d5_execution": {
            "service_contract_ref": "contract:association.local",
            "local_action_ref": "action:association.activity.read",
        },
        "d6_generative_transmission": {
            "packet_protocol": "W7TP-8D-PACKET-NATIVE/1.0",
            "lookup_refs": ["lookup:association.activity.v1"],
            "reconstruction_conditions": ["contract_and_authority_match"],
            "verification_method": "LOCAL_EFFECT_CONTRACT_COMPARE",
        },
        "d7_risk": {"hard_risks": [], "authority_boundary_ok": True},
        "d8_envelope": {
            "identity_ref": "identity:member-0001",
            "authority_scope": ["association:activity:read"],
            "ttl_seconds": 300,
            "nonce": "translation-nonce-0001",
            "sha256": "0" * 64,
            "protocol": "W7TP-8D-PACKET-NATIVE/1.0",
            "verifier_ref": "verifier:taiji01.total-field",
        },
    }
    packet["d8_envelope"]["sha256"] = ramp.packet_content_sha256(packet)
    return packet


def capability_packet(mode="L2_EQUIVALENT"):
    packet = {
        "capability_ref": "CAP_ASSOCIATION_SERVICE_V1",
        "packet_type": "PROFESSIONAL_RULE_PACKET",
        "schema_version": "W7TP-CAPABILITY/1.0",
        "domain_code": "ASSOCIATION",
        "language_code": "zh-TW",
        "compatibility_profile": "W7TP-8D-PACKET-NATIVE/1.0",
        "source_refs": ["source:association.rule.reviewed.v1"],
        "payload_refs": ["payload:association.rule.v1"],
        "reconstruction_spec": {
            "mode": mode,
            "conditions": ["local_contract_present", "authority_verified"],
            "effect_contract_ref": "effect:association.activity.read.v1",
        },
        "verification_method": "LOCAL_EFFECT_CONTRACT_COMPARE",
    }
    packet["sha256"] = ramp.packet_content_sha256(packet)
    return packet


def capability_pull():
    return ramp.build_capability_pull_request(
        "CAP_ASSOCIATION_SERVICE_V1",
        "PROFESSIONAL_RULE_PACKET",
        "ASSOCIATION",
        "zh-TW",
        "W7TP-8D-PACKET-NATIVE/1.0",
        "pull-nonce-0001",
        capability_ref="CAP_ASSOCIATION_SERVICE_V1",
    )


def full_path(mode="L2_EQUIVALENT"):
    entry = member_entry()
    authority = identity_authority()
    translation = scenario_translation()
    capability = capability_packet(mode)
    pull = capability_pull()
    reconstruction = ramp.reconstruct_local_state(translation, capability)
    audit = ramp.run_multilayer_audit(
        member_entry_packet=entry,
        identity_authority_packet=authority,
        scenario_translation_packet=translation,
        capability_pull_request_packet=pull,
        capability_packet=capability,
        local_reconstruction_packet=reconstruction,
    )
    return translation, reconstruction, audit


def test_all_seven_json_schemas_parse_and_are_valid_draft_2020_12():
    for name in SCHEMA_NAMES:
        schema = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)


def test_valid_identity_reference_passes():
    assert ramp.validate_member_entry_packet(member_entry())["state"] == "PASS"
    result = ramp.resolve_identity_authority(member_entry(), identity_authority())
    assert result["state"] == "PASS"
    assert result["identity_ref"] == "identity:member-0001"


def test_member_sovereignty_refs_must_match_verified_authority_packet():
    fields = ("consent_ref", "authorization_ref", "withdrawal_ref", "qualification_ref")
    for field in fields:
        authority = identity_authority()
        authority[field] = f"{field.removesuffix('_ref')}:mismatch"
        result = ramp.resolve_identity_authority(member_entry(), authority)
        assert result["state"] == "HOLD"
        assert f"AUTHORITY_MISMATCH:{field}" in result["errors"]


def test_denied_consent_or_withdrawn_identity_cannot_pass_member_gate():
    denied = member_entry()
    denied["envelope"]["consent_state"] = "DENIED"
    assert "CONSENT_DENIED" in ramp.validate_member_entry_packet(denied)["errors"]

    withdrawn = member_entry()
    withdrawn["envelope"]["revocation_state"] = "REVOKED"
    assert "IDENTITY_REVOKED" in ramp.validate_member_entry_packet(withdrawn)["errors"]


def test_member_plaintext_entering_packet_holds():
    packet = member_entry()
    packet["member_name"] = "forbidden-example"
    result = ramp.validate_member_entry_packet(packet)
    assert result["state"] == "HOLD"
    assert any("FORBIDDEN_UPLINK_FIELD" in error for error in result["errors"])


def test_complete_intent_uplink_attempt_holds():
    packet = capability_pull()
    packet["full_intent"] = "forbidden-complete-intent-example"
    result = ramp.validate_no_uplink_plaintext(packet, require_minimal_pull=True)
    assert result["state"] == "HOLD"
    assert "CAPABILITY_PULL_NOT_MINIMAL" in result["errors"]


def test_minimal_capability_pull_request_passes_with_exact_nine_fields():
    packet = capability_pull()
    assert set(packet) == ramp.MINIMAL_PULL_FIELDS
    assert len(packet) == 9
    assert packet["capability_ref"] == "CAP_ASSOCIATION_SERVICE_V1"
    assert ramp.validate_no_uplink_plaintext(packet, require_minimal_pull=True)["state"] == "PASS"
    assert packet["return_protocol"] == "W7TP-PULL-PACKET-ONLY/1.0"


def test_all_frontend_containers_route_to_fixed_contracts():
    route_table = json.loads(
        (ROOT / "runtime/total_field/secondary_cloud/scenario_route_table.json").read_text(
            encoding="utf-8"
        )
    )
    expected = {
        "ASSOCIATION": ("ASSOCIATION_SERVICE_PACKET", "CAP_ASSOCIATION_SERVICE_V1"),
        "PROPERTY": ("PROPERTY_SERVICE_PACKET", "CAP_PROPERTY_SERVICE_V1"),
        "CAFE_POS": ("CAFE_POS_SERVICE_PACKET", "CAP_CAFE_POS_SERVICE_V1"),
        "HOUSEHOLD": ("HOUSEHOLD_SERVICE_PACKET", "CAP_HOUSEHOLD_SERVICE_V1"),
        "GENERIC": ("GENERIC_INTENT_PACKET", "CAP_GENERIC_INTENT_V1"),
    }
    for container, (packet_type, capability_ref) in expected.items():
        result = ramp.resolve_scenario_container(f"scenario:{container}", route_table)
        assert result["state"] == "PASS"
        assert result["selected_container"] == container
        assert result["packet_type"] == packet_type
        assert result["capability_ref"] == capability_ref


def test_local_reconstruction_passes_without_external_answering():
    translation = scenario_translation()
    reconstruction = ramp.reconstruct_local_state(translation, capability_packet())
    assert reconstruction["reconstruction_location"] == "TAIJI01_LOCAL"
    assert reconstruction["comparison_result"] == "EQUIVALENT"
    assert reconstruction["local_verified"] is True
    assert reconstruction["sha256"] == ramp.packet_content_sha256(reconstruction)


def test_packet_protocol_verification_method_and_multilayer_audit_pass():
    translation, _, audit = full_path()
    assert translation["d6_generative_transmission"]["packet_protocol"] == ramp.PACKET_PROTOCOL
    assert translation["d6_generative_transmission"]["verification_method"]
    assert audit["state"] == "PASS"
    assert len(audit["layers"]) == 8
    assert all(layer["state"] == "PASS" for layer in audit["layers"])


def test_unverified_candidate_cannot_seal():
    translation, reconstruction, audit = full_path("L3_CANDIDATE")
    packet = ramp.produce_verification_packet(
        run_id="RUN-20260711-CANDIDATE",
        scenario_translation_packet=translation,
        local_reconstruction_packet=reconstruction,
        audit_result=audit,
    )
    assert reconstruction["candidate_only"] is True
    assert packet["state"] == "HOLD"
    assert packet["seal_status"] == "NOT_SEALED"


def test_no_llm_full_packet_path_and_frontend_contract_pass():
    translation, reconstruction, audit = full_path()
    packet = ramp.produce_verification_packet(
        run_id="RUN-20260711-FORMAL",
        scenario_translation_packet=translation,
        local_reconstruction_packet=reconstruction,
        audit_result=audit,
    )
    required_frontend_fields = {
        "state",
        "run_id",
        "packet_id",
        "selected_container",
        "packet_type",
        "capability_ref",
        "current_stage",
        "verification_result",
        "evidence_refs",
        "sha256",
        "seal_status",
        "confidence",
    }
    assert required_frontend_fields <= set(packet)
    assert packet["state"] == "PASS"
    assert packet["seal_status"] == "SEALED"
    assert packet["cloud_mode"] == "PULL_PACKET_ONLY"
    assert packet["member_upload"] == "DENY"
    assert packet["reconstruct"] == "TAIJI01_LOCAL"
    assert packet["verify"] == "LOCAL_OR_TOTAL_FIELD"
    assert packet["confidence"] is None
    assert packet["sha256"] == ramp.packet_content_sha256(packet)
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "Math.random" not in source
    assert "setTimeout" not in source
