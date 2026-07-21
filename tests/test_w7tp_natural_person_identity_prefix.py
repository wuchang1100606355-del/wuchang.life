from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tools.total_field.w7tp_field_application_runtime import FieldApplicationError
from tools.total_field.w7tp_intent_field_suite.api import (
    capabilities_payload,
    process_http_request,
)
from tools.total_field.w7tp_intent_field_suite.identity_prefix import (
    assert_llm_candidate_does_not_mutate_identity,
    build_natural_person_identity_prefix,
    verify_natural_person_identity_prefix,
)
from tools.total_field.w7tp_intent_field_suite.packet_builder import process_intent


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas/field/w7tp_natural_person_identity_prefix.schema.json"
PREFIX_CONFIG_PATH = ROOT / "configs/w7tp_member_llm_prefix_policy.example.json"
PREFIX_DOC_PATH = ROOT / "docs/total_field/W7TP_MEMBER_AI_LLM_PREFIX_POLICY.md"


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def ref(prefix: str, label: str) -> str:
    return f"{prefix}:sha256:{digest(label)}"


def identity_prefix(label: str = "person-one"):
    return build_natural_person_identity_prefix(
        identity_packet_ref=ref("identity_packet_ref", f"{label}-packet"),
        protected_plaintext_binding_ref=ref(
            "identity_binding_ref", f"{label}-protected-record"
        ),
        identity_registry_ref=ref(
            "identity_registry_ref", f"{label}-total-field-registry"
        ),
        field_context_ref="field_context_ref:wuchang.shared-runtime",
        device_bindings=[
            {
                "device_ref": ref("device_ref", f"{label}-device-one"),
                "binding_ref": ref("binding_ref", f"{label}-device-one-binding"),
                "state": "ACTIVE",
            }
        ],
        provider_bindings=[
            {
                "provider_ref": "provider_ref:google",
                "provider_subject_sha256": digest(f"{label}-google-opaque-subject"),
                "binding_ref": ref("binding_ref", f"{label}-google-binding"),
                "state": "ACTIVE",
            },
            {
                "provider_ref": "provider_ref:line",
                "provider_subject_sha256": digest(f"{label}-line-opaque-subject"),
                "binding_ref": ref("binding_ref", f"{label}-line-binding"),
                "state": "ACTIVE",
            },
            {
                "provider_ref": "provider_ref:community-social",
                "provider_subject_sha256": digest(
                    f"{label}-other-social-opaque-subject"
                ),
                "binding_ref": ref("binding_ref", f"{label}-other-social-binding"),
                "state": "ACTIVE",
            },
        ],
        source_refs=[ref("source_ref", f"{label}-identity-canonical")],
        binding_evidence_refs=[ref("evidence_ref", f"{label}-binding-evidence")],
    )


def registry_for(packet):
    return {
        "entries": [
            {
                "protected_plaintext_binding_ref": packet["D1"][
                    "protected_plaintext_binding_ref"
                ],
                "identity_packet_ref": packet["D1"]["identity_packet_ref"],
            }
        ]
    }


COMPLETE_GENERIC_INTENT = {
    "requested_result": "分析候選",
    "constraints": "只讀",
    "evidence_refs": ["repo 正典"],
}


def test_identity_prefix_is_schema_valid_ref_only_and_provider_extensible():
    packet = identity_prefix()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(packet)) == []
    assert [item["provider_ref"] for item in packet["D6"]["provider_bindings"]] == [
        "provider_ref:community-social",
        "provider_ref:google",
        "provider_ref:line",
    ]
    serialized = json.dumps(packet, ensure_ascii=False, sort_keys=True)
    assert "google-opaque-subject" not in serialized
    assert "line-opaque-subject" not in serialized
    assert packet["D1"]["plaintext_identity_visible"] is False
    assert packet["D5"]["llm_may_modify_prefix"] is False


def test_missing_registry_is_not_denial_and_verified_registry_passes():
    packet = identity_prefix()
    missing = verify_natural_person_identity_prefix(packet)
    assert missing["state"] == "NOT_YET_EVIDENCED"
    assert missing["candidate_processing_allowed"] is True
    assert missing["formal_adoption_allowed"] is False

    verified = verify_natural_person_identity_prefix(
        packet,
        identity_registry_snapshot=registry_for(packet),
    )
    assert verified["state"] == "PASS_IDENTITY_PREFIX_VERIFIED"
    assert verified["formal_adoption_allowed"] is True


def test_positive_duplicate_mapping_conflict_holds_without_second_account():
    packet = identity_prefix()
    registry = registry_for(packet)
    registry["entries"].append(
        {
            "protected_plaintext_binding_ref": packet["D1"][
                "protected_plaintext_binding_ref"
            ],
            "identity_packet_ref": ref("identity_packet_ref", "conflicting-packet"),
        }
    )
    result = verify_natural_person_identity_prefix(
        packet,
        identity_registry_snapshot=registry,
    )
    assert result["state"] == "HOLD_IDENTITY_PACKET_CONFLICT"
    assert result["candidate_processing_allowed"] is False


def test_tampering_prefix_hash_or_binding_is_held():
    packet = identity_prefix()
    tampered = copy.deepcopy(packet)
    tampered["D6"]["provider_bindings"][0]["provider_subject_sha256"] = digest(
        "tampered-subject"
    )
    result = verify_natural_person_identity_prefix(tampered)
    assert result["state"] == "HOLD_IDENTITY_PREFIX_INTEGRITY"
    assert result["integrity"] == "FAIL"
    assert "IDENTITY_PREFIX_SHA256_MISMATCH" in result["reason_codes"]


def test_llm_writable_candidate_cannot_supply_or_replace_identity_prefix():
    with pytest.raises(FieldApplicationError) as caught:
        assert_llm_candidate_does_not_mutate_identity(
            {"candidate": {"identity_prefix": identity_prefix()}}
        )
    assert caught.value.reason_code == "LLM_IDENTITY_PREFIX_MUTATION_ATTEMPT"

    status, result = process_http_request(
        json.dumps(
            {
                "profile": "GENERIC",
                "identity_prefix": identity_prefix(),
                "intent": COMPLETE_GENERIC_INTENT,
            }
        ).encode("utf-8")
    )
    assert status == 422
    assert result["reason_code"] == "LLM_IDENTITY_PREFIX_MUTATION_ATTEMPT"


def test_shared_runtime_attaches_only_trusted_prefix_and_binds_guided_state():
    packet = identity_prefix()
    registry = registry_for(packet)
    result = process_intent(
        "GENERIC",
        COMPLETE_GENERIC_INTENT,
        trusted_identity_prefix=packet,
        identity_registry_snapshot=registry,
    )
    assert result["identity_prefix"] == packet
    assert result["D1"]["identity_packet_ref"] == packet["D1"]["identity_packet_ref"]
    assert result["D8"]["identity_prefix_sha256"] == packet["D8"]["prefix_sha256"]
    assert result["D8"]["identity_binding_evidence_state"] == "PASS_IDENTITY_PREFIX_VERIFIED"
    assert result["D8"]["llm_identity_prefix_mutable"] is False

    first = process_intent(
        "GENERIC",
        {"requested_result": "分析候選"},
        trusted_identity_prefix=packet,
        identity_registry_snapshot=registry,
    )
    guided_schema = json.loads(
        (ROOT / "schemas/field/w7tp_guided_completion.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert list(Draft202012Validator(guided_schema).iter_errors(first)) == []
    assert first["identity_prefix_sha256"] == packet["D8"]["prefix_sha256"]
    other = identity_prefix("person-two")
    with pytest.raises(FieldApplicationError) as caught:
        process_intent(
            "GENERIC",
            {"requested_result": "分析候選"},
            state_id=first["state_id"],
            question_id=first["question"]["question_id"],
            answer="只讀",
            trusted_identity_prefix=other,
            identity_registry_snapshot=registry_for(other),
        )
    assert caught.value.reason_code == "GUIDED_STATE_MISMATCH"


def test_capability_and_policy_pin_the_immutable_prefix_boundary():
    capability = capabilities_payload()["natural_person_identity_prefix"]
    assert capability["one_natural_person_one_dedicated_packet"] is True
    assert capability["device_and_social_accounts_are_bindings"] is True
    assert capability["llm_mutable"] is False
    assert capability["http_body_prefix_accepted"] is False
    assert capability["trusted_gateway_binding_state"] == "NOT_YET_EVIDENCED"

    config = json.loads(PREFIX_CONFIG_PATH.read_text(encoding="utf-8"))[
        "natural_person_identity_prefix"
    ]
    assert config["one_natural_person_one_dedicated_identity_packet"] is True
    assert config["plaintext_identity_visible_to_llm"] is False
    assert config["llm_mutable"] is False
    assert config["missing_evidence_is_denial"] is False
    assert {"provider_ref:google", "provider_ref:line"} <= set(
        config["supported_provider_ref_examples"]
    )

    policy = PREFIX_DOC_PATH.read_text(encoding="utf-8")
    assert "SYSTEM_IMMUTABLE_PREFIX" in policy
    assert "NOT_YET_EVIDENCED" in policy
    assert "Google、LINE 或其他社群帳號" in policy
