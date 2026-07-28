"""Wuchang three-organization container scene bridge.

商業組織 / 物業組織 / 公益組織三大模組共撐 Odoo 社區。

Local devices can switch scenes by container-profile candidates:
- business scene
- property scene
- association / public welfare scene
- founder local audiovisual scene

Candidate-only:
- no docker action
- no live container switch
- no deploy
- no restart
- no DB write
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from tools.total_field.founder_variable_cognition_gate import (
    ALLOW,
    evaluate_founder_identity_gate,
)
from tools.total_field.xiaoj_member_bound_session_candidate import (
    evaluate_session,
    receive_cloud_fragment,
)
from tools.total_field_candidate_gateway import receive_candidate


DEFAULT_MAP_PATH = Path("configs/total_field/wuchang_three_org_container_scene_map.json")
TAIJI04_LOCAL_ENTRY_REF = "entry_ref:taiji04_local_audiovisual_natural_language"
FOUNDER_SCENE = "founder_scene"
BUSINESS_CLOUD_CANDIDATE = "business_cloud_candidate"
XIAOJ_DEVELOPER_CARD_REF = (
    "manifest_ref:xiaoj_member_bound_developer_seat_candidate_v0_1"
)
ROOKIE_MESSAGE = "這個我不懂，我只是個菜鳥，我幫你問店長或學長"
CANONICAL_V2_1_ID = (
    "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1"
)
CANONICAL_V2_1_VERSION = "2.1"
CANONICAL_V2_1_PATH = (
    "docs/total_field/"
    "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2_1.md"
)
CANONICAL_V2_1_SHA256 = (
    "e960d14254df083ffed711e2c44b76fc2075541716881bc3d1034cb26cffbaba"
)
PARENT_CANONICAL_V2_PATH = (
    "docs/total_field/"
    "W7TP_8D_MULTIPURPOSE_GENERATIVE_TRANSMISSION_PACKET_CANONICAL_V2.md"
)
PARENT_CANONICAL_V2_SHA256 = (
    "a5281f229ced0943072cce373125be16f0d361b9352a71094ad5450a6022d5d0"
)

VERIFICATION_MODES = {
    "L1_FULL": "L1_EXACT_BYTE",
    "L2_EQUIVALENT": "L2_EFFECT_EQUIVALENT",
    "L3_CANDIDATE": "L3_CANDIDATE",
}

HARD_RISK_ACTIONS = {
    "delete",
    "restore",
    "deploy",
    "restart",
    "db_write",
    "router_write",
    "docker_compose_up",
    "docker_restart",
    "live_container_switch",
    "production_activation",
    "payment_capture",
    "formal_public_service_claim",
    "member_plaintext_exposure",
    "secret_exposure",
    "raw_audio_to_cloud",
    "raw_video_to_cloud",
    "live_microphone_stream",
    "live_camera_stream"
}


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _fingerprint(value: Any, length: int = 16) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()[:length]


def _sha256(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _actions(values: Sequence[str] | None) -> set[str]:
    return {
        str(value).strip().lower().replace("-", "_")
        for value in (values or [])
        if str(value).strip()
    }


def _canonical_v2_1_binding() -> Dict[str, Any]:
    return {
        "canonical_id": CANONICAL_V2_1_ID,
        "version": CANONICAL_V2_1_VERSION,
        "path": CANONICAL_V2_1_PATH,
        "sha256": CANONICAL_V2_1_SHA256,
        "parent_version": "2.0.0",
        "parent_path": PARENT_CANONICAL_V2_PATH,
        "parent_sha256": PARENT_CANONICAL_V2_SHA256,
        "migration_mode": "APPEND_ONLY_SUCCESSOR",
    }


def _append_only_lineage(packet_id: str, packet_hash: str) -> Dict[str, Any]:
    logical_time = f"logical-time:{packet_hash[:16]}"
    return {
        "mode": "APPEND_ONLY",
        "packet_ref": packet_id,
        "parent_ref": "parent_ref:none_initial_packet",
        "parent_sha256": None,
        "logical_time": logical_time,
        "transition_ref": f"transition_ref:{packet_hash[:16]}",
        "historical_packet_rewritten": False,
    }


def _communication_contract() -> Dict[str, Any]:
    return {
        "mode": "INTENT_AND_STATE_FIELD_PACKET_COMMUNICATION",
        "intent_communication": True,
        "state_field_packet_communication": True,
        "semantic_communication": False,
        "semantic_model_role": "CANDIDATE_PARSER_ONLY",
    }


def _adi_boundary() -> Dict[str, Any]:
    return {
        "packet_layer": {
            "mode": "LOCAL_IRREVERSIBLE_PACKET_ADJUDICATION_INDEX",
            "index_state": "NOT_ALLOCATED",
            "normalized_fields_ref": "packet_fields_ref:canonical_normalized",
            "nonce_ref": "envelope_ref:nonce",
            "key_version_ref": "protected_ref:local_authority_key_version",
            "evidence_ref": "dimensions_ref:D4_EVIDENCE",
            "member_plaintext": False,
            "reversible_identity_code": False,
            "floating_point_embedding": False,
        },
        "system_layer": {
            "mode": "USER_OWNED_SPATIOTEMPORAL_STATE_INDEX_NETWORK",
            "packet_lineage_ref": "lineage_ref:this_packet",
            "logical_time_ref": "lineage_ref:logical_time",
            "state_transition_ref": "lineage_ref:transition",
            "namespace_ref": "namespace_ref:wuchang_three_org",
            "evidence_graph_ref": "dimensions_ref:D4_EVIDENCE",
        },
    }


def _protected_reference_boundary() -> Dict[str, Any]:
    return {
        "mode": "REFERENCE_ONLY",
        "h64_td_ref": "protected_ref:H64-TD",
        "codebook_ref": "protected_ref:complete_codebook",
        "mapping_table_ref": "protected_ref:mapping_table",
        "recovery_material_ref": "protected_ref:recovery_material",
        "inline_protected_material": False,
        "cloud_candidate_material": False,
        "log_material": False,
    }


def _core_verification(
    *,
    verification_level: str,
    packet_hash: str,
    payload_byte_length: int,
    decision: str,
    evidence_refs: Sequence[str],
    packet_id: str,
) -> Dict[str, Any]:
    verification_mode = VERIFICATION_MODES[verification_level]
    common = {
        "mode": verification_mode,
        "method_ref": f"verifier:w7tp-{verification_mode.lower()}",
        "contract_ref": f"contract:w7tp-{verification_mode.lower()}",
    }
    if verification_mode == "L1_EXACT_BYTE":
        return {
            **common,
            "decision": decision if decision in {"PASS", "HOLD", "BLOCK"} else "HOLD",
            "raw_sha256": packet_hash,
            "byte_length": payload_byte_length,
            "hash_scope": "TARGET_RAW_BYTES",
        }
    if verification_mode == "L2_EFFECT_EQUIVALENT":
        return {
            **common,
            "decision": decision if decision in {"PASS", "HOLD", "BLOCK"} else "HOLD",
            "effect_contract_ref": "effect:state-control-service-result",
            "comparison_fields": ["state", "control", "effect"],
            "evidence_refs": list(evidence_refs),
            "local_verifier_ref": "verifier:local-total-field",
        }
    return {
        **common,
        "decision": "BLOCK" if decision == "BLOCK" else "HOLD",
        "candidate_refs": [f"candidate:{packet_id}"],
        "local_decision_authority_ref": "authority:local-total-field",
        "final_authority_granted": False,
    }


def _build_v2_1_core_packet(
    *,
    packet_id: str,
    packet_hash: str,
    nonce: str,
    verification_level: str,
    decision: str,
    intent_ref: str,
    state_ref: str,
    coordinate_ref: str,
    evidence_values: Sequence[str],
    execution_ref: str,
    target_state_ref: str,
    lookup_refs: Sequence[str],
    generation_rule_refs: Sequence[str],
    reconstruction_condition_refs: Sequence[str],
    hard_risks: Sequence[str] = (),
    payload_byte_length: int = 0,
) -> Dict[str, Any]:
    logical_time = max(1, int(packet_hash[:12], 16))
    evidence_refs = list(dict.fromkeys(
        f"evidence:{_sha256(value)}"
        for value in evidence_values
    )) or [f"evidence:{packet_hash}"]
    lineage_ref = f"lineage:{packet_hash[:16]}"
    transition_ref = f"transition:{packet_hash[:16]}"
    generation_ref = f"generation:{packet_hash[:16]}"
    risk_ref = f"risk:{packet_hash[:16]}"
    verification_ref = f"verification:{packet_hash[:16]}"
    envelope_ref = f"envelope:{packet_hash[:16]}"
    namespace = "wuchang.three-org"
    authority_ref = "authority:local-total-field"
    replay_tuple = {
        "authority_ref": authority_ref,
        "namespace": namespace,
        "packet_id": packet_id,
        "nonce": nonce,
        "logical_time": logical_time,
    }
    verification = _core_verification(
        verification_level=verification_level,
        packet_hash=packet_hash,
        payload_byte_length=payload_byte_length,
        decision=decision,
        evidence_refs=evidence_refs,
        packet_id=packet_id,
    )
    risk_decision = decision if decision in {"PASS", "HOLD", "BLOCK"} else "HOLD"
    d6 = {
        "protocol_ref": "protocol:w7tp-8d-generative-transmission-v2.1",
        "routing_ref": "routing:local-total-field-reconstructor",
        "lookup_refs": list(lookup_refs),
        "reference_refs": [intent_ref, coordinate_ref, *evidence_refs],
        "generation_rule_refs": list(generation_rule_refs),
        "reconstruction_condition_refs": list(reconstruction_condition_refs),
        "equivalent_state_rule_refs": ["rule:governed-equivalent-state"],
        "total_field_verifier_ref": "verifier:local-total-field",
    }

    return {
        "canonical_id": CANONICAL_V2_1_ID,
        "version": CANONICAL_V2_1_VERSION,
        "canonical_binding": {
            "canonical_path": CANONICAL_V2_1_PATH,
            "canonical_sha256": CANONICAL_V2_1_SHA256,
            "parent_version": "2.0",
            "parent_path": PARENT_CANONICAL_V2_PATH,
            "parent_sha256": PARENT_CANONICAL_V2_SHA256,
            "migration_mode": "APPEND_ONLY_SUCCESSOR",
        },
        "packet_core": "UNIFIED_MULTIPURPOSE_INTERACTIVE_COUPLED_8D_STATE_FIELD_PACKET",
        "communication_contract": {
            "primary": "INTENT_COMMUNICATION",
            "secondary": "STATE_FIELD_PACKET_COMMUNICATION",
            "semantic_communication": False,
            "semantic_model_role": "CANDIDATE_EVIDENCE_ONLY",
            "floating_point_required": False,
        },
        "authority_boundary": {
            "cloud_authority": ["CANDIDATE", "EVIDENCE"],
            "llm_authority": ["CANDIDATE", "EVIDENCE"],
            "final_decision_authority": "LOCAL_TOTAL_FIELD",
            "final_seal_authority": "LOCAL_TOTAL_FIELD",
        },
        "state_field": {
            "kind": "INTERACTIVE_COUPLED_8D_STATE_FIELD",
            "dimensions": {
                "D1_INTENT": {"profile_ref": intent_ref},
                "D2_STATE": {"profile_ref": state_ref},
                "D3_COORDINATE": {"profile_ref": coordinate_ref},
                "D4_EVIDENCE": {
                    "profile_ref": f"evidence-profile:{packet_hash[:16]}",
                    "evidence_refs": evidence_refs,
                },
                "D5_EXECUTION": {"profile_ref": execution_ref},
                "D6_GENERATIVE_TRANSMISSION": d6,
                "D7_RISK_QUARANTINE": {
                    "hard_risks": list(hard_risks),
                    "quarantine_refs": [f"quarantine:{packet_hash[:16]}"],
                    "decision": risk_decision,
                },
                "D8_ENVELOPE_VERIFICATION": {
                    "envelope_ref": envelope_ref,
                    "verifier_ref": "verifier:local-total-field",
                    "seal_policy_ref": "seal-policy:local-total-field",
                },
            },
            "coupling": {
                "transition_function": "S_NEXT=T(S_CURRENT,I,C,E,A,G,R,V)",
                "current_state_ref": state_ref,
                "intent_ref": intent_ref,
                "coordinate_ref": coordinate_ref,
                "evidence_refs": evidence_refs,
                "execution_ref": execution_ref,
                "generation_ref": generation_ref,
                "risk_ref": risk_ref,
                "verification_ref": verification_ref,
                "target_state_ref": target_state_ref,
                "non_float_execution": True,
            },
        },
        "adi": {
            "packet_layer": {
                "index_kind": "OPAQUE_IRREVERSIBLE_PACKET_DECISION_INDEX",
                "namespace": namespace,
                "decision_index": packet_hash,
                "nonce": nonce,
                "key_version_ref": "key-version:local-authority-current",
                "authority_ref": authority_ref,
                "evidence_refs": evidence_refs,
                "derivation_ref": "derivation:local-authority-normalized-fields",
                "verifier_ref": "verifier:local-adi",
                "irreversible": True,
                "reversible_identity": False,
                "database_primary_key": False,
                "floating_embedding": False,
            },
            "system_layer": {
                "index_kind": "USER_OWNED_SPATIOTEMPORAL_STATE_INDEX_NETWORK",
                "owner_authority_ref": authority_ref,
                "namespace": namespace,
                "logical_time": logical_time,
                "packet_lineage_refs": [lineage_ref],
                "state_transition_ref": transition_ref,
                "evidence_refs": evidence_refs,
            },
            "replay_protection": {
                "tuple": replay_tuple,
                "tuple_sha256": _sha256(replay_tuple),
                "logical_time_monotonic": True,
            },
        },
        "lineage": {
            "append_only": True,
            "parent_ref": "canonical-parent:w7tp-v2",
            "parent_sha256": PARENT_CANONICAL_V2_SHA256,
            "previous_seal_ref": "seal:none-initial",
            "logical_time": logical_time,
            "changed_dimensions": [
                "D1_INTENT",
                "D2_STATE",
                "D3_COORDINATE",
                "D4_EVIDENCE",
                "D5_EXECUTION",
                "D6_GENERATIVE_TRANSMISSION",
                "D7_RISK_QUARANTINE",
                "D8_ENVELOPE_VERIFICATION",
            ],
            "transition_evidence_refs": evidence_refs,
        },
        "generation": {
            "protocol_native": True,
            "state_ref": state_ref,
            "coordinate_ref": coordinate_ref,
            "lookup_refs": list(lookup_refs),
            "generation_rule_refs": list(generation_rule_refs),
            "reconstruction_condition_refs": list(reconstruction_condition_refs),
            "target_state_ref": target_state_ref,
            "file_movement": False,
        },
        "reconstruction": {
            "local_state_field_ref": "state-field:local-total-field",
            "lookup_refs": list(lookup_refs),
            "condition_refs": list(reconstruction_condition_refs),
            "equivalent_state_rule_refs": ["rule:governed-equivalent-state"],
            "target_state_ref": target_state_ref,
            "total_field_verifier_ref": "verifier:local-total-field",
            "deterministic_operations": [
                "INTEGER",
                "BOOLEAN",
                "SYMBOLIC",
                "LOOKUP",
                "REFERENCE_RESOLUTION",
                "STATE_TRANSITION",
            ],
            "model_output_role": "CANDIDATE_EVIDENCE_ONLY",
        },
        "verification": verification,
        "protected_refs": {
            "materials": [
                {
                    "kind": "H64_TD",
                    "reference": "protected_ref:H64-TD",
                    "disclosure": "REFERENCE_ONLY",
                },
                {
                    "kind": "CODEBOOK",
                    "reference": "protected_ref:complete-codebook",
                    "disclosure": "REFERENCE_ONLY",
                },
                {
                    "kind": "MAPPING_TABLE",
                    "reference": "protected_ref:mapping-table",
                    "disclosure": "REFERENCE_ONLY",
                },
                {
                    "kind": "RECOVERY_MATERIAL",
                    "reference": "protected_ref:recovery-material",
                    "disclosure": "REFERENCE_ONLY",
                },
            ],
        },
        "envelope": {
            "packet_id": packet_id,
            "authority_ref": authority_ref,
            "version": CANONICAL_V2_1_VERSION,
            "ttl_seconds": 900,
            "nonce": nonce,
            "payload_sha256": packet_hash,
            "canonical_json_sha256": _sha256(
                {
                    "packet_id": packet_id,
                    "packet_hash": packet_hash,
                    "nonce": nonce,
                    "logical_time": logical_time,
                }
            ),
            "verifier_ref": "verifier:local-total-field",
            "seal_policy_ref": "seal-policy:local-total-field",
            "seal_state": "UNSEALED_CANDIDATE",
            "final_seal_authority": "LOCAL_TOTAL_FIELD",
        },
    }


def load_three_org_scene_map(path: str | Path = DEFAULT_MAP_PATH) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    if data.get("mode") != "candidate_only_no_live_container_action":
        raise ValueError("three-org scene map must remain candidate-only")

    policy = data.get("policy") or {}
    required_false = [
        "delete",
        "restore",
        "deploy",
        "restart",
        "db_write",
        "router_write",
        "web_cockpit_touch",
        "runtime_bulk_output",
        "docker_compose_up",
        "docker_restart",
        "live_container_switch",
        "production_activation",
        "payment_capture",
        "formal_public_service_claim",
        "member_plaintext_exposure",
        "secret_exposure"
    ]
    bad = [key for key in required_false if policy.get(key) is not False]
    if bad:
        raise ValueError("unsafe policy: " + ",".join(bad))

    modules = data["odoo_community_core"]["supporting_modules"]
    if modules != ["business_organization", "property_organization", "public_welfare_organization"]:
        raise ValueError("Odoo community must be supported by three org modules")

    service = data.get("taiji04_audiovisual_natural_language_service") or {}
    required_false = [
        "runtime_activation",
        "live_microphone_stream",
        "live_camera_stream",
        "db_write",
        "deploy",
        "restart",
        "router_write"
    ]
    unsafe = [key for key in required_false if service.get(key) is not False]
    if unsafe:
        raise ValueError("unsafe TAIJI04 audiovisual service: " + ",".join(unsafe))

    founder_control = service.get("founder_scene_control") or {}
    founder_required_false = [
        "runtime_bound",
        "authority_increase",
        "production_activation",
        "direct_db_write",
        "raw_founder_identity_to_cloud",
        "founder_private_detail_on_hdmi"
    ]
    unsafe_founder = [key for key in founder_required_false if founder_control.get(key) is not False]
    if unsafe_founder:
        raise ValueError("unsafe founder scene control: " + ",".join(unsafe_founder))
    if founder_control.get("local_only") is not True:
        raise ValueError("founder scene must remain local-only")

    execution_point = service.get("organization_audiovisual_execution_point") or {}
    if execution_point.get("node_ref") != "node_ref:drallion":
        raise ValueError("organization audiovisual execution point must be drallion")
    execution_required_false = [
        "service_runtime_verified",
        "runtime_enabled",
        "raw_audio_input",
        "raw_video_input",
        "member_plaintext_input",
        "founder_identity_input",
        "invite_url_stored",
        "creator_identity_stored",
        "node_id_stored",
        "node_key_stored",
        "execution_without_founder_command"
    ]
    unsafe_execution_point = [
        key for key in execution_required_false
        if execution_point.get(key) is not False
    ]
    if unsafe_execution_point:
        raise ValueError(
            "unsafe organization audiovisual execution point: "
            + ",".join(unsafe_execution_point)
        )
    display_hardware = execution_point.get("display_hardware") or {}
    if (
        display_hardware.get("display_count") != 2
        or display_hardware.get("touchscreen") is not True
        or display_hardware.get("external_hdmi_display") is not True
    ):
        raise ValueError("drallion service desk must expose touchscreen and HDMI displays")
    display_required_false = [
        "founder_private_detail_on_hdmi",
        "member_plaintext_on_hdmi",
        "secret_on_hdmi",
        "raw_media_on_hdmi"
    ]
    unsafe_display = [
        key for key in display_required_false
        if display_hardware.get(key) is not False
    ]
    if unsafe_display:
        raise ValueError("unsafe drallion HDMI display: " + ",".join(unsafe_display))

    platform = service.get("platform") or {}
    if (
        platform.get("hardware_class") != "SUNMI_POS"
        or platform.get("google_commercial_voice_hardware_license") is not True
        or platform.get("network_node_ref") != "node_ref:taiji04"
        or platform.get("network_role")
        != "LOCAL_CONTROL_AND_VOICE_HARDWARE_NOT_PUBLIC_ENDPOINT"
        or platform.get("public_endpoint") is not False
    ):
        raise ValueError("TAIJI04 must remain SUNMI POS with Google commercial voice license")

    node_roles = service.get("organization_node_roles") or {}
    expected_node_roles = {
        "node_ref:taiji04": (
            "sunmi_pos_clerk_human_controlled_checkout_workstation_"
            "and_google_commercial_voice_hardware"
        ),
        "node_ref:taiji03": "organization_super_administrator_control_device",
        "node_ref:drallion": (
            "organization_service_desk_audiovisual_ai_execution_point"
        )
    }
    if node_roles != expected_node_roles:
        raise ValueError("organization node role mapping invalid")
    expected_titles = {
        "node_ref:taiji04": "商米 POS 店員人控結帳作業台及 Google 商用語音硬體",
        "node_ref:taiji03": "組織超級管理員控制設備",
        "node_ref:drallion": "組織服務台自然語言影音 AI 執行點"
    }
    if service.get("organization_node_role_titles") != expected_titles:
        raise ValueError("organization node role titles invalid")
    if (
        service.get("node_role")
        != "sunmi_pos_clerk_human_controlled_checkout_and_google_commercial_voice_endpoint"
    ):
        raise ValueError("TAIJI04 role must remain SUNMI POS voice endpoint")
    if service.get("workspace_host_node_ref") != "node_ref:taiji03":
        raise ValueError("super hall workspace host must remain TAIJI03")
    if (
        execution_point.get("node_role")
        != "organization_service_desk_audiovisual_ai_execution_point"
    ):
        raise ValueError("drallion role must remain organization service desk")

    if (
        platform.get("clerk_human_controlled_checkout_workstation") is not True
        or platform.get("member_checkout_requires_purchasing_member_confirmation")
        is not True
        or platform.get("clerk_may_substitute_member_confirmation") is not False
        or platform.get("ai_may_substitute_member_confirmation") is not False
        or platform.get("administrator_may_substitute_member_confirmation")
        is not False
        or platform.get("identity_verification_equals_checkout_consent") is not False
        or platform.get("autonomous_checkout") is not False
        or platform.get("payment_execution") is not False
    ):
        raise ValueError(
            "TAIJI04 member checkout requires purchasing-member confirmation"
        )

    checkout_paths = service.get("checkout_paths") or {}
    member_browser = checkout_paths.get("member_mobile_browser_ai") or {}
    counter_xiaoj = (
        checkout_paths.get("counter_xiaoj_audiovisual_natural_language") or {}
    )
    clerk_last_three = checkout_paths.get("clerk_phone_last_three_digits") or {}
    non_member_guest = checkout_paths.get("non_member_guest") or {}
    if (
        member_browser.get("enabled_as_source_candidate") is not True
        or member_browser.get("purchasing_member_confirmation_required") is not True
        or member_browser.get("ai_may_confirm_for_member") is not False
        or counter_xiaoj.get("enabled_as_source_candidate") is not True
        or counter_xiaoj.get("purchasing_member_confirmation_required") is not True
        or counter_xiaoj.get("xiaoj_may_confirm_for_member") is not False
        or clerk_last_three.get("input_purpose") != "MEMBER_LOOKUP_HINT_ONLY"
        or clerk_last_three.get("identity_authentication") is not False
        or clerk_last_three.get("checkout_consent") is not False
        or clerk_last_three.get("purchasing_member_confirmation_required") is not True
        or non_member_guest.get("phone_last_three_digits_input") != "BLANK"
        or non_member_guest.get("checkout_label") != "一般路人"
        or non_member_guest.get("member_identity_packet_access") is not False
        or non_member_guest.get("member_resource_access") is not False
    ):
        raise ValueError("TAIJI04 member and guest checkout paths invalid")

    member_ai = service.get("member_centered_sovereign_ai") or {}
    if (
        member_ai.get("member_is_system_participant") is not True
        or member_ai.get(
            "system_bound_identity_packet_required_for_member_resource_access"
        ) is not True
        or member_ai.get("resource_access_mode")
        != "CAPABILITY_AND_RESOURCE_REFERENCES_ONLY"
        or member_ai.get("resource_scope_must_match_purchasing_member") is not True
        or member_ai.get("cross_member_resource_access") is not False
        or member_ai.get("member_plaintext_to_cloud") is not False
        or member_ai.get("raw_identity_material_to_cloud") is not False
        or member_ai.get("identity_verification_equals_checkout_consent") is not False
        or member_ai.get("phone_last_three_digits_are_lookup_hint_only") is not True
        or member_ai.get("non_member_guest_has_member_resource_access") is not False
    ):
        raise ValueError("member-centered sovereign AI boundary invalid")

    voice_endpoint = service.get("authorized_commercial_voice_endpoint_candidate") or {}
    endpoint_required_false = [
        "runtime_bound",
        "source_voice_copy",
        "speaker_impersonation",
        "raw_audio_to_vpn",
        "actuation_without_authorization"
    ]
    unsafe_endpoint = [key for key in endpoint_required_false if voice_endpoint.get(key) is not False]
    if unsafe_endpoint:
        raise ValueError("unsafe commercial voice endpoint: " + ",".join(unsafe_endpoint))

    return data


def classify_scene(intent_text: str) -> str:
    text = str(intent_text or "").lower()

    if any(x in text for x in ["創辦人", "founder"]):
        return "founder_scene"

    if any(x in text for x in ["商業", "商家", "票券", "幸福幣", "商業雲", "business", "merchant"]):
        return "business_scene"

    if any(x in text for x in ["物業", "公道伯", "管委會", "法令", "優良社區", "property"]):
        return "property_scene"

    if any(x in text for x in ["協會", "公益", "志工", "社工", "照服", "許願樹", "基金", "association", "welfare"]):
        return "association_scene"

    return "business_scene"


def resolve_scene_profile(scene: str, *, map_data: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    data = dict(map_data or load_three_org_scene_map())
    profiles = data["local_device_scene_profiles"]
    resolved = str(scene or "business_scene")
    profile = dict(profiles.get(resolved) or profiles["business_scene"])

    return {
        "scene": resolved if resolved in profiles else "business_scene",
        "zh": profile["zh"],
        "scene_role": profile.get("scene_role", "three_org_scene"),
        "container_profile_candidate": profile["container_profile"],
        "primary_module": profile["primary_module"],
        "visible_modules": list(profile["visible_modules"]),
        "landing_message": profile["landing_message"],
        "live_container_action": False
    }


def build_eight_d_media_transport_packet(
    *,
    domain: str,
    scene_ref: str = "scene_ref:taiji04_local_media",
    verification_level: str = "L2_EQUIVALENT"
) -> Dict[str, Any]:
    """Build a schema-shaped 8D image/audio/video transport packet."""

    resolved_domain = str(domain or "").upper()
    if resolved_domain not in {"IMAGE", "AUDIO", "VIDEO", "AUDIOVISUAL"}:
        raise ValueError("unsupported 8D media domain")
    if verification_level not in VERIFICATION_MODES:
        raise ValueError("unsupported verification level")
    verification_mode = VERIFICATION_MODES[verification_level]

    profile_ref = {
        "IMAGE": "profile_ref:w7tp_image_domain_profile_v1",
        "AUDIO": "profile_ref:w7tp_audiovisual_domain_profile_v1:audio",
        "VIDEO": "profile_ref:w7tp_audiovisual_domain_profile_v1:video_3d_scene",
        "AUDIOVISUAL": "profile_ref:w7tp_audiovisual_domain_profile_v1:sync"
    }[resolved_domain]
    verification_ref = {
        "L1_FULL": "verifier_ref:media_exact",
        "L2_EQUIVALENT": "verifier_ref:media_state_equivalent",
        "L3_CANDIDATE": "verifier_ref:media_candidate"
    }[verification_level]
    target_equivalence = verification_level
    if resolved_domain == "AUDIO" and verification_level == "L2_EQUIVALENT":
        verification_ref = "verifier_ref:audio_non_source_equivalent"
        target_equivalence = (
            "AUDIO_SEMANTIC_TIMING_PROSODY_AND_SERVICE_EFFECT_EQUIVALENT"
        )
    packet_seed = {
        "canonical_path": CANONICAL_V2_1_PATH,
        "canonical_sha256": CANONICAL_V2_1_SHA256,
        "domain": resolved_domain,
        "scene_ref": scene_ref,
        "verification_mode": verification_mode,
        "profile_ref": profile_ref
    }
    packet_hash = _sha256(packet_seed)
    packet_id = f"packet:taiji04:{resolved_domain.lower()}:{packet_hash[:16]}"
    nonce = _sha256({"packet_id": packet_id, "scene_ref": scene_ref})[:32]
    lineage = _append_only_lineage(packet_id, packet_hash)
    envelope = {
        "packet_id": packet_id,
        "authority_ref": "authority_ref:total_field",
        "version": CANONICAL_V2_1_VERSION,
        "canonical_ref": CANONICAL_V2_1_PATH,
        "canonical_sha256": CANONICAL_V2_1_SHA256,
        "ttl_seconds": 900,
        "nonce": nonce,
        "logical_time": lineage["logical_time"],
        "lineage_ref": lineage["packet_ref"],
        "verification_mode": verification_mode,
        "sha256": packet_hash,
        "verifier_ref": verification_ref,
        "seal_policy": "candidate_only_total_field_review"
    }
    risk = {"hard_risks": [], "decision": "PASS"}
    d6 = {
        "protocol": "W7TP_8D_GENERATIVE_TRANSMISSION_V2_1",
        "communication_contract": _communication_contract(),
        "routing": "total_field_to_authorized_local_reconstructor",
        "segmentation": f"{resolved_domain.lower()}_state_coordinate_segment",
        "merge_conditions": ["packet_order_valid", "hash_valid", "ttl_valid"],
        "lookup": {"profile_ref": f"lookup_ref:{resolved_domain.lower()}"},
        "references": [scene_ref, profile_ref],
        "generation_rules": [
            "integer_state_transition",
            "coordinate_reconstruction",
            "reference_resolution",
            "on_demand_materialization"
        ] + ([
            "non_source_audio_equivalent_reconstruction"
        ] if resolved_domain == "AUDIO" and verification_level == "L2_EQUIVALENT" else []),
        "reconstruction_contract": f"contract_ref:{resolved_domain.lower()}_local_reconstruction",
        "verification_contract": f"contract_ref:{resolved_domain.lower()}_{verification_level.lower()}",
        "residual": [],
        "refill_policy": "reference_only_no_raw_media_cloud_refill",
        "on_demand_materialization": True
    }
    core_packet = _build_v2_1_core_packet(
        packet_id=packet_id,
        packet_hash=packet_hash,
        nonce=nonce,
        verification_level=verification_level,
        decision="PASS",
        intent_ref=f"intent:{resolved_domain.lower()}-reconstruction",
        state_ref=f"state:{resolved_domain.lower()}-candidate",
        coordinate_ref=f"coordinate:{resolved_domain.lower()}",
        evidence_values=[scene_ref, profile_ref],
        execution_ref="execution:authorized-local-reconstructor",
        target_state_ref=f"target-state:{resolved_domain.lower()}-reconstructed",
        lookup_refs=[f"lookup:{resolved_domain.lower()}-profile"],
        generation_rule_refs=[
            "rule:integer-state-transition",
            "rule:reference-resolution",
            "rule:coordinate-reconstruction",
        ],
        reconstruction_condition_refs=[
            "condition:packet-order-valid",
            "condition:hash-valid",
            "condition:ttl-valid",
        ],
        payload_byte_length=len(_stable_json(packet_seed).encode("utf-8")),
    )

    return {
        "canonical_id": CANONICAL_V2_1_ID,
        "version": CANONICAL_V2_1_VERSION,
        "canonical_binding": _canonical_v2_1_binding(),
        "core_packet": core_packet,
        "packet_core": "UNIFIED_MULTIPURPOSE_8D_PACKET",
        "communication_contract": _communication_contract(),
        "state_field": {
            "mode": "INTERACTIVE_COUPLED_8D_STATE_FIELD",
            "coupled_dimensions": [
                "D1_INTENT",
                "D2_STATE",
                "D3_COORDINATE",
                "D4_EVIDENCE",
                "D5_EXECUTION",
                "D6_GENERATIVE_TRANSMISSION",
                "D7_RISK_QUARANTINE",
                "D8_ENVELOPE_VERIFICATION",
            ],
            "transition_ref": lineage["transition_ref"],
            "total_field_verifier_ref": "verifier_ref:total_field",
        },
        "lineage": lineage,
        "adi": _adi_boundary(),
        "protected_refs": _protected_reference_boundary(),
        "technology_flags": {
            "packet_carries_transport_protocol": True,
            "packet_carries_reconstruction_conditions": True,
            "packet_carries_reconstruction_contract": True,
            "packet_carries_verification_method": True,
            "packet_carries_verification_contract": True,
            "model_required": False,
            "llm_required": False,
            "neural_network_required": False,
            "floating_point_inference_required": False,
            "diffusion_required": False,
            "latent_codec": False,
            "neural_codec": False
        },
        "dimensions": {
            "D1_INTENT": {"profile_ref": f"intent_ref:{resolved_domain.lower()}_reconstruction"},
            "D2_STATE": {"profile_ref": f"state_ref:{resolved_domain.lower()}_candidate"},
            "D3_COORDINATE": {"profile_ref": f"coordinate_ref:{resolved_domain.lower()}"},
            "D4_EVIDENCE": {"profile_ref": f"evidence_ref:{packet_hash}"},
            "D5_EXECUTION": {"profile_ref": "execution_ref:authorized_local_reconstructor"},
            "D6_GENERATIVE_TRANSMISSION": d6,
            "D7_RISK_QUARANTINE": risk,
            "D8_ENVELOPE_VERIFICATION": envelope
        },
        "domain_profile": {
            "domain": resolved_domain,
            "state_profile": {"profile_ref": profile_ref},
            "coordinate_profile": {"profile_ref": f"coordinate_profile_ref:{resolved_domain.lower()}"},
            "lookup_profile": {"profile_ref": f"lookup_profile_ref:{resolved_domain.lower()}"},
            "generation_profile": {"profile_ref": f"generation_profile_ref:{resolved_domain.lower()}"},
            "reconstruction_profile": {"profile_ref": f"reconstruction_profile_ref:{resolved_domain.lower()}"},
            "verification_profile": {"profile_ref": verification_ref}
        },
        "generation_packet": {
            "state": {"profile_ref": f"state_ref:{resolved_domain.lower()}_candidate"},
            "coordinate": {"profile_ref": f"coordinate_ref:{resolved_domain.lower()}"},
            "lookup": {"profile_ref": f"lookup_ref:{resolved_domain.lower()}"},
            "generation_rule": d6["generation_rules"],
            "reconstruction_contract": d6["reconstruction_contract"],
            "verification_contract": d6["verification_contract"],
            "target_equivalence": target_equivalence
        },
        "transmission_packet": {
            "routing": d6["routing"],
            "path": ["total_field", "authorized_linux_node", "local_reconstructor"],
            "segment": 0,
            "order": 0,
            "ttl": envelope["ttl_seconds"],
            "reference": d6["references"],
            "hash": packet_hash,
            "merge_condition": d6["merge_conditions"],
            "delivery_state": "READY"
        },
        "composition_mode": "SEPARATE",
        "reconstruction": {
            "core": [
                "NON_FLOAT_DETERMINISTIC_LOOKUP",
                "INTEGER_STATE_TRANSITION",
                "RULE_EXPANSION",
                "REFERENCE_RESOLUTION",
                "COORDINATE_RECONSTRUCTION",
                "EQUIVALENT_STATE_GENERATION",
                "TOTAL_FIELD_VERIFICATION"
            ],
            "zero_prior_content_receiver": True,
            "materialization": "ON_DEMAND_MATERIALIZATION",
            "economic_mode": "W7TP_GENERATIVE"
        },
        "verification": {
            "level": verification_level,
            "mode": verification_mode,
            "method_ref": verification_ref,
            "contract_ref": d6["verification_contract"],
            "decision": "PASS"
        },
        "risk": risk,
        "envelope": envelope
    }


def build_audiovisual_natural_language_service_candidate(
    *,
    intent_text: str,
    input_mode: str = "text",
    requested_scene: str | None = None,
    node_ref: str = "node_ref:taiji04",
    requested_actions: Sequence[str] | None = None,
    evidence_refs: Sequence[str] | None = None
) -> Dict[str, Any]:
    """Build the local-first TAIJI04 audiovisual service candidate."""

    data = load_three_org_scene_map()
    service = data["taiji04_audiovisual_natural_language_service"]
    actions = _actions(requested_actions)
    blocked_actions = sorted(actions & HARD_RISK_ACTIONS)
    profile = resolve_scene_profile(
        requested_scene or classify_scene(intent_text),
        map_data=data
    )
    mode = str(input_mode or "").strip().lower()
    evidence = list(evidence_refs or [])
    missing_fields = []

    if not str(intent_text or "").strip():
        missing_fields.append("intent_text")
    if not str(node_ref or "").startswith("node_ref:"):
        missing_fields.append("node_ref")
    if mode not in service["input_modes"]:
        missing_fields.append("input_mode")

    media_transport_packets = {}
    if mode in {"image_event", "audiovisual_event"}:
        media_transport_packets["image"] = build_eight_d_media_transport_packet(
            domain="IMAGE",
            scene_ref=f"scene_ref:taiji04:{profile['scene']}"
        )
    if mode in {"voice", "audiovisual_event"}:
        media_transport_packets["audio"] = build_eight_d_media_transport_packet(
            domain="AUDIO",
            scene_ref=f"scene_ref:taiji04:{profile['scene']}"
        )
    if mode == "audiovisual_event":
        media_transport_packets["audiovisual_sync"] = build_eight_d_media_transport_packet(
            domain="AUDIOVISUAL",
            scene_ref=f"scene_ref:taiji04:{profile['scene']}"
        )
    if mode == "three_d_scene":
        media_transport_packets["three_d_film"] = build_eight_d_media_transport_packet(
            domain="VIDEO",
            scene_ref=f"scene_ref:taiji04:{profile['scene']}"
        )

    base = {
        "intent_text": intent_text,
        "input_mode": mode,
        "node_ref": node_ref,
        "target_scene": profile["scene"],
        "evidence_refs": evidence,
        "blocked_actions": blocked_actions,
        "missing_fields": missing_fields
    }
    fp = _fingerprint(base)

    if blocked_actions:
        decision = "BLOCK"
        reason = "AUDIOVISUAL_HARD_RISK_ACTION_REQUESTED"
    elif missing_fields:
        decision = "HOLD"
        reason = "AUDIOVISUAL_REQUIRED_FIELD_MISSING"
    else:
        decision = "PASS_CANDIDATE"
        reason = "TAIJI04_AUDIOVISUAL_SOURCE_CANDIDATE_READY_FOR_TOTAL_FIELD_REVIEW"

    packet_id = f"packet:taiji04:audiovisual-scene:{fp}"
    packet_hash = _sha256(
        {
            "canonical_sha256": CANONICAL_V2_1_SHA256,
            "packet_id": packet_id,
            "decision": decision,
            "evidence_refs": evidence,
        }
    )
    lineage = _append_only_lineage(packet_id, packet_hash)
    nonce = _sha256({"packet_id": packet_id, "logical_time": lineage["logical_time"]})[:32]
    risk_quarantine = {
        "blocked_actions": blocked_actions,
        "missing_fields": missing_fields,
        "raw_media_to_cloud_blocked": True,
        "member_plaintext_to_cloud_blocked": True,
        "direct_runtime_write_blocked": True,
        "founder_identity_gate_required": profile["scene"] == "founder_scene"
    }
    envelope_verification = {
        "packet_id": packet_id,
        "version": CANONICAL_V2_1_VERSION,
        "canonical_ref": CANONICAL_V2_1_PATH,
        "canonical_sha256": CANONICAL_V2_1_SHA256,
        "decision_authority": "total_field",
        "owner_admin_review_required": True,
        "ttl_required": True,
        "nonce_required": True,
        "nonce": nonce,
        "logical_time": lineage["logical_time"],
        "verification_mode": "L3_CANDIDATE",
        "sha256": packet_hash,
        "seal": f"candidate:{fp}"
    }
    legacy_flat_profile = {
        "d1_intent": "taiji04_local_first_audiovisual_natural_language_service",
        "d2_state": decision,
        "d3_coordinate": {
            "node_ref": node_ref,
            "target_scene": profile["scene"],
            "container_profile_candidate": profile["container_profile_candidate"],
            "input_mode": mode,
            "scene_role": profile["scene_role"]
        },
        "d4_evidence": {
            "evidence_refs": evidence,
            "candidate_fingerprint": fp
        },
        "d5_execution": {
            "mode": "source_candidate_local_first",
            "pipeline": service["local_pipeline"],
            "runtime_activation": False,
            "db_write": False,
            "deploy": False,
            "restart": False
        },
        "d6_technical_definition": service["linux_total_field_scheduling"]["generative_transmission"],
        "d6_media_transport_basis": service["eight_d_media_transport_basis"],
        "d7_risk": risk_quarantine,
        "d8_envelope": envelope_verification
    }
    eight_d_packet = {
        "canonical_id": CANONICAL_V2_1_ID,
        "version": CANONICAL_V2_1_VERSION,
        "canonical_binding": _canonical_v2_1_binding(),
        "core_packet": _build_v2_1_core_packet(
            packet_id=packet_id,
            packet_hash=packet_hash,
            nonce=nonce,
            verification_level="L3_CANDIDATE",
            decision="BLOCK" if decision == "BLOCK" else "HOLD",
            intent_ref="intent:taiji04-audiovisual-service",
            state_ref=f"state:{decision.lower().replace('_', '-')}",
            coordinate_ref=f"coordinate:taiji04-{profile['scene'].replace('_', '-')}",
            evidence_values=evidence or [f"candidate-fingerprint:{fp}"],
            execution_ref="execution:source-candidate-local-first",
            target_state_ref="target-state:total-field-reviewed-audiovisual-candidate",
            lookup_refs=["lookup:taiji04-audiovisual-profile"],
            generation_rule_refs=[
                "rule:reference-resolution",
                "rule:local-state-reconstruction",
            ],
            reconstruction_condition_refs=[
                "condition:total-field-review",
                "condition:no-raw-media-cloud",
            ],
            hard_risks=blocked_actions,
            payload_byte_length=len(_stable_json(legacy_flat_profile).encode("utf-8")),
        ),
        "communication_contract": _communication_contract(),
        "state_field": {
            "mode": "INTERACTIVE_COUPLED_8D_STATE_FIELD",
            "transition_ref": lineage["transition_ref"],
            "total_field_verifier_ref": "verifier_ref:total_field",
        },
        "dimensions": {
            "D1_INTENT": legacy_flat_profile["d1_intent"],
            "D2_STATE": legacy_flat_profile["d2_state"],
            "D3_COORDINATE": legacy_flat_profile["d3_coordinate"],
            "D4_EVIDENCE": legacy_flat_profile["d4_evidence"],
            "D5_EXECUTION": legacy_flat_profile["d5_execution"],
            "D6_GENERATIVE_TRANSMISSION": {
                "protocol": "W7TP_8D_GENERATIVE_TRANSMISSION_V2_1",
                "definition": legacy_flat_profile["d6_technical_definition"],
                "media_transport_basis": legacy_flat_profile["d6_media_transport_basis"],
            },
            "D7_RISK_QUARANTINE": risk_quarantine,
            "D8_ENVELOPE_VERIFICATION": envelope_verification,
        },
        "verification": {
            "level": "L3_CANDIDATE",
            "mode": "L3_CANDIDATE",
            "decision": decision,
        },
        "lineage": lineage,
        "adi": _adi_boundary(),
        "protected_refs": _protected_reference_boundary(),
        "legacy_profile_adapter": {
            "mode": "READ_ONLY_LEGACY_FLAT_PROFILE_PROJECTION",
            "source_profile": "wuchang_three_org_audiovisual_flat_8d/1.0",
            "historical_packet_rewritten": False,
            "projection": legacy_flat_profile,
        },
        **legacy_flat_profile,
    }

    return {
        "STATE": decision,
        "candidate_ref": f"taiji04_audiovisual_service_candidate:{fp}",
        "candidate_type": "wuchang_taiji04_audiovisual_natural_language_service_candidate",
        "source_design_enabled": True,
        "runtime_activation": False,
        "node_ref": node_ref,
        "node_role": service["node_role"],
        "platform": service["platform"],
        "checkout_paths": service["checkout_paths"],
        "member_centered_sovereign_ai": service["member_centered_sovereign_ai"],
        "organization_node_roles": service["organization_node_roles"],
        "organization_node_role_titles": service["organization_node_role_titles"],
        "workspace_host_node_ref": service["workspace_host_node_ref"],
        "role_workspaces": service["role_workspaces"],
        "scene_role": profile["scene_role"],
        "organization_audiovisual_execution_point": service[
            "organization_audiovisual_execution_point"
        ],
        "founder_scene_control": (
            service["founder_scene_control"]
            if profile["scene"] == "founder_scene"
            else None
        ),
        "input_mode": mode,
        "local_pipeline": service["local_pipeline"],
        "touchscreen_window": service["touchscreen_window"],
        "hdmi_window": service["hdmi_window"],
        "cloud_boundary": service["cloud_boundary"],
        "eight_d_media_transport_basis": service["eight_d_media_transport_basis"],
        "media_transport_packets": media_transport_packets,
        "authorized_commercial_voice_endpoint_candidate": service[
            "authorized_commercial_voice_endpoint_candidate"
        ],
        "linux_total_field_scheduling": service["linux_total_field_scheduling"],
        "target_scene": profile["scene"],
        "container_profile_candidate": profile["container_profile_candidate"],
        "visible_modules": profile["visible_modules"],
        "evidence_refs": evidence,
        "blocked_actions": blocked_actions,
        "missing_fields": missing_fields,
        "live_microphone_stream": False,
        "live_camera_stream": False,
        "member_plaintext_to_cloud": False,
        "raw_media_to_cloud": False,
        "db_write": False,
        "deploy": False,
        "restart": False,
        "router_write": False,
        "eight_d_packet": eight_d_packet,
        "total_field_candidate_decision": {
            "decision": decision,
            "reason": reason,
            "next": "TOTAL_FIELD_OWNER_ADMIN_REVIEW"
        }
    }


def _taiji04_founder_binding_denied(state: str) -> Dict[str, Any]:
    return {
        "STATE": state,
        "taiji04_entry": TAIJI04_LOCAL_ENTRY_REF,
        "founder_scene_binding": False,
        "runtime_enabled": False,
        "formal_execution_authority": False,
        "deploy": False,
        "restart": False,
        "db_write": False,
        "router_write": False,
        "canonical_write": False
    }


def _isolated_total_field_translation_request(
    *,
    packet_sha256: str,
    cloud_fragment_sha256: str
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    event_ref = f"event:taiji04:founder-scene:{packet_sha256[:16]}"
    observation_domain_ref = "observation-domain:taiji04-founder-scene-isolated:v0.1"
    dimensions = {
        "D1_ref": "field/tfct/D1/v0_1",
        "D2_ref": "field/tfct/D2/v0_1",
        "D3_ref": "field/tfct/D3/v0_1",
        "D4_ref": "field/tfct/D4/v0_1",
        "D5_ref": "field/tfct/D5/v0_1",
        "D6_ref": "field/tfct/D6/v0_1",
        "D7_ref": "field/tfct/D7/v0_1",
        "D8_ref": "field/tfct/D8/v0_1"
    }
    previous = {
        "D1": {"intent_ref": "intent_ref:none"},
        "D2": {"state_ref": "state_ref:isolated_previous"},
        "D3": {"node_ref": "node_ref:taiji04"},
        "D4": {"evidence_ref": "evidence_ref:none"},
        "D5": {"execution_ref": "execution_ref:none"},
        "D6": {"privacy_boundary_ref": "privacy_ref:reference_only"},
        "D7": {
            "rule_ref": "rule_ref:reference_only",
            "routing_ref": "routing_ref:isolated",
            "reconstruction_condition": "condition_ref:unconfigured_domain"
        },
        "D8": {"adjudication_policy_ref": "d8_ref:candidate_only"}
    }
    proposed = {
        "D1": {"intent_ref": f"intent_sha256:{packet_sha256}"},
        "D2": {"state_ref": "state_ref:founder_scene_source_candidate"},
        "D3": {
            "node_ref": "node_ref:taiji04",
            "scene_ref": "scene_ref:founder_scene",
            "container_profile_ref": "container_profile:business_cloud_candidate",
            "execution_node_ref": "node_ref:drallion"
        },
        "D4": {"evidence_ref": f"cloud_fragment_sha256:{cloud_fragment_sha256}"},
        "D5": {"execution_ref": "execution_ref:none_candidate_only"},
        "D6": {
            "privacy_boundary_ref": "privacy_ref:deidentified_incomplete_reference_only"
        },
        "D7": {
            "rule_ref": "rule_ref:total_field_translation_candidate",
            "routing_ref": "routing_ref:taiji04_to_isolated_total_field",
            "reconstruction_condition": "condition_ref:reference_only_candidate"
        },
        "D8": {"adjudication_policy_ref": "d8_ref:founder_command_candidate_only"}
    }
    request = {
        "profile_schema_version": "8d-gte-runtime-candidate-profile/0.1",
        "profile_type": "RUNTIME_REQUEST",
        "gte": {
            "schema_version": "8d-gte-candidate/0.1",
            "lifecycle": "CANDIDATE",
            "event_ref": event_ref,
            "observation_domain_ref": observation_domain_ref,
            "dimensions": dimensions,
            "constraint_hypergraph_ref": "constraints/tfct/runtime-hypergraph/v0_1",
            "convergence_operator_ref": "convergence/tfct/finite-fixed-point/v0_1",
            "priority_policy_ref": "priority/tfct/candidate/v0_1",
            "fixed_point_status": "PENDING",
            "verification": {"final_decision": "PENDING", "commit_applied": False},
            "tfs_result": None
        },
        "source_mode": "LLM_PUSH",
        "candidate_only": True,
        "event": {
            "event_id": f"event-id:{packet_sha256[:16]}",
            "event_ref": event_ref,
            "event_code": "STATE_UPDATE",
            "logical_time": f"logical-time:{packet_sha256[:16]}"
        },
        "rule_set_ref": "rules/tfct/identity_v0_1",
        "resolved_fields": proposed,
        "context": {
            "request_ref": f"request_ref:taiji04:{packet_sha256[:16]}",
            "translation_ref": f"translation_sha256:{cloud_fragment_sha256}"
        },
        "adi_requested": False
    }
    return request, previous


def bind_taiji04_local_entry_to_founder_scene(
    *,
    intent_text: str,
    input_mode: str,
    developer_session_request: Mapping[str, Any],
    role_table: Mapping[str, Sequence[str]],
    current_epoch: int,
    founder_identity_request: Mapping[str, Any],
    sealed_founder_root: Mapping[str, Any] | None,
    total_field_preflight_receipt: Mapping[str, Any],
    lawful_scope_confirmed: bool,
    evidence_refs: Sequence[str] | None = None,
    active_developer_seats: Sequence[Mapping[str, Any]] = ()
) -> Dict[str, Any]:
    """Bind the existing TAIJI04 entry to the existing Founder scene."""

    command_ref = str(founder_identity_request.get("founder_command_ref") or "").strip()
    if founder_identity_request.get("explicit_founder_command") is not True or not command_ref:
        return _taiji04_founder_binding_denied("BLOCK_NO_EXPLICIT_FOUNDER_COMMAND")
    if lawful_scope_confirmed is not True:
        return _taiji04_founder_binding_denied("BLOCK_LAWFUL_SCOPE_NOT_CONFIRMED")

    developer_session = evaluate_session(
        developer_session_request,
        role_table,
        current_epoch=current_epoch,
        active_developer_seats=active_developer_seats
    )
    if developer_session.get("state") != "PASS_MEMBER_BOUND_CANDIDATE":
        return _taiji04_founder_binding_denied("BLOCK_XIAOJ_DEVELOPER_CARD")
    operation_record = developer_session.get("operation_record") or {}
    capability_envelope = developer_session.get("d8_capability_envelope_candidate") or {}
    capabilities = set(capability_envelope.get("capability_refs") or [])
    required_capabilities = {
        "TOTAL_FIELD_TRANSLATION",
        "FOUNDER_AUTHORIZED_CLOUD_MODEL_ENHANCEMENT"
    }
    if (
        operation_record.get("principal") != "member_ref:founder"
        or operation_record.get("actor") != "xiaoj_agent_ref:founder-local"
        or operation_record.get("command") != command_ref
        or "role_ref:founder_developer" not in operation_record.get("role", [])
        or not required_capabilities.issubset(capabilities)
    ):
        return _taiji04_founder_binding_denied(
            "BLOCK_NON_FOUNDER_OR_DEVELOPER_CARD_MISMATCH"
        )

    founder_gate = evaluate_founder_identity_gate(
        founder_identity_request,
        sealed_founder_root
    )
    if founder_gate.get("decision") != ALLOW:
        return _taiji04_founder_binding_denied("BLOCK_FOUNDER_ROOT_OR_COMMAND")

    command_ref_sha256 = _sha256(command_ref)
    if (
        total_field_preflight_receipt.get("decision") != "PASS"
        or total_field_preflight_receipt.get("candidate_only") is not True
        or total_field_preflight_receipt.get("formal_execution_authority") is not False
        or total_field_preflight_receipt.get("command_ref_sha256") != command_ref_sha256
    ):
        return _taiji04_founder_binding_denied("BLOCK_TOTAL_FIELD_PREFLIGHT")

    scene_candidate = build_audiovisual_natural_language_service_candidate(
        intent_text=intent_text,
        input_mode=input_mode,
        requested_scene=FOUNDER_SCENE,
        node_ref="node_ref:taiji04",
        evidence_refs=evidence_refs
    )
    if (
        scene_candidate.get("STATE") != "PASS_CANDIDATE"
        or scene_candidate.get("target_scene") != FOUNDER_SCENE
        or scene_candidate.get("container_profile_candidate")
        != "container_profile:business_cloud_candidate"
    ):
        return _taiji04_founder_binding_denied("BLOCK_FOUNDER_SCENE_NOT_BOUND")

    media_packet_refs = [
        {
            "media_kind": media_kind,
            "packet_sha256": packet["envelope"]["sha256"]
        }
        for media_kind, packet in sorted(
            scene_candidate["media_transport_packets"].items()
        )
    ]
    scene_envelope = {
        "entry_ref": TAIJI04_LOCAL_ENTRY_REF,
        "entry_hardware_class": "SUNMI_POS",
        "google_commercial_voice_hardware_license": True,
        "checkout_workstation_mode": "CLERK_HUMAN_CONTROLLED",
        "member_checkout_requires_purchasing_member_confirmation": True,
        "clerk_may_substitute_member_confirmation": False,
        "ai_may_substitute_member_confirmation": False,
        "administrator_may_substitute_member_confirmation": False,
        "identity_verification_equals_checkout_consent": False,
        "checkout_paths": scene_candidate["checkout_paths"],
        "member_centered_sovereign_ai": scene_candidate[
            "member_centered_sovereign_ai"
        ],
        "autonomous_checkout": False,
        "payment_execution": False,
        "entry_network_role": "LOCAL_CONTROL_AND_VOICE_HARDWARE_NOT_PUBLIC_ENDPOINT",
        "scene_ref": "scene_ref:founder_scene",
        "input_mode": input_mode,
        "container_profile_ref": "container_profile:business_cloud_candidate",
        "developer_card_ref": XIAOJ_DEVELOPER_CARD_REF,
        "execution_node_ref": scene_candidate[
            "organization_audiovisual_execution_point"
        ]["node_ref"],
        "execution_transport_ref": "transport_ref:tailscale_private_network",
        "execution_runtime_verified": False,
        "intent_ref_sha256": _sha256(intent_text),
        "command_ref_sha256": command_ref_sha256,
        "evidence_refs_sha256": [_sha256(value) for value in (evidence_refs or [])],
        "media_packet_refs": media_packet_refs,
        "total_field_translation": True,
        "candidate_only": True,
        "formal_execution_authority": False
    }
    packet_sha256 = _sha256(scene_envelope)
    cloud_fragment = {
        "fragment_type": "CANDIDATE",
        "candidate_ref": f"candidate_ref:taiji04:{packet_sha256[:16]}",
        "target_scene_ref": "scene_ref:founder_scene",
        "cloud_candidate": BUSINESS_CLOUD_CANDIDATE,
        "container_profile_ref": "container_profile:business_cloud_candidate",
        "execution_node_ref": "node_ref:drallion",
        "packet_sha256": packet_sha256,
        "payload_mode": "DEIDENTIFIED_INCOMPLETE_REFERENCE_ONLY",
        "media_packet_refs": media_packet_refs,
        "formal_execution_authority": False
    }
    cloud_intake = receive_cloud_fragment(
        cloud_fragment,
        developer_session,
        founder_authorized=True
    )
    if cloud_intake.get("state") != "PASS_RECEIVE_CANDIDATE_REQUIRED":
        return _taiji04_founder_binding_denied("BLOCK_CLOUD_FRAGMENT_BOUNDARY")

    gateway_request, previous_state = _isolated_total_field_translation_request(
        packet_sha256=packet_sha256,
        cloud_fragment_sha256=cloud_intake["fragment_sha256"]
    )
    gateway_result = receive_candidate(
        gateway_request,
        previous_state=previous_state,
        observation_domains={}
    )
    gateway_gte = gateway_result.get("gte") or {}
    if gateway_result.get("commit_applied") is not False or gateway_gte.get("lifecycle") != "CANDIDATE":
        return _taiji04_founder_binding_denied("BLOCK_ISOLATED_TOTAL_FIELD_COMMIT")
    receipt = {
        "state": "ISOLATED_TOTAL_FIELD_CANDIDATE_RECEIPT",
        "final_decision": gateway_result.get("final_decision"),
        "commit_applied": False,
        "lifecycle": "CANDIDATE",
        "observation_domain": "UNCONFIGURED_ISOLATED",
        "formal_execution_authority": False
    }
    receipt["receipt_sha256"] = _sha256(receipt)

    return {
        "STATE": "PASS_TAIJI04_FOUNDER_SCENE_SOURCE_BOUND",
        "taiji04_entry": TAIJI04_LOCAL_ENTRY_REF,
        "taiji04_hardware": {
            "hardware_class": "SUNMI_POS",
            "google_commercial_voice_hardware_license": True,
            "clerk_human_controlled_checkout_workstation": True,
            "member_checkout_requires_purchasing_member_confirmation": True,
            "clerk_may_substitute_member_confirmation": False,
            "ai_may_substitute_member_confirmation": False,
            "administrator_may_substitute_member_confirmation": False,
            "identity_verification_equals_checkout_consent": False,
            "autonomous_checkout": False,
            "payment_execution": False,
            "network_node_ref": "node_ref:taiji04",
            "network_role": "LOCAL_CONTROL_AND_VOICE_HARDWARE_NOT_PUBLIC_ENDPOINT",
            "public_endpoint": False
        },
        "checkout_paths": scene_candidate["checkout_paths"],
        "member_centered_sovereign_ai": scene_candidate[
            "member_centered_sovereign_ai"
        ],
        "founder_scene_binding": "source_candidate_bound",
        "target_scene": FOUNDER_SCENE,
        "cloud_candidate": BUSINESS_CLOUD_CANDIDATE,
        "developer_card_ref": XIAOJ_DEVELOPER_CARD_REF,
        "organization_audiovisual_execution_point": {
            "node_ref": "node_ref:drallion",
            "node_role": "organization_service_desk_audiovisual_ai_execution_point",
            "platform": "ANDROID",
            "os_version": "13",
            "hardware_relation": "SEPARATE_ORGANIZATION_AUDIOVISUAL_EXECUTION_NODE",
            "hardware_class_evidence_state": "UNKNOWN_NOT_SHOWN",
            "google_commercial_voice_hardware_license_evidence_state": "UNKNOWN_NOT_SHOWN",
            "private_network": "TAILSCALE",
            "display_hardware": {
                "display_count": 2,
                "touchscreen": True,
                "external_hdmi_display": True,
                "founder_private_detail_on_hdmi": False,
                "member_plaintext_on_hdmi": False,
                "secret_on_hdmi": False,
                "raw_media_on_hdmi": False
            },
            "service_runtime_verified": False
        },
        "xiaoj_capabilities": sorted(required_capabilities),
        "scene_envelope": scene_envelope,
        "cloud_fragment": cloud_fragment,
        "packet_sha256": packet_sha256,
        "total_field_receipt": receipt,
        "runtime_enabled": False,
        "formal_execution_authority": False,
        "deploy": False,
        "restart": False,
        "db_write": False,
        "router_write": False,
        "canonical_write": False
    }


def build_three_org_scene_candidate(
    *,
    intent_text: str,
    local_device_ref: str = "local_device_ref:node_c_or_lobby_xiaoj",
    requested_scene: str | None = None,
    requested_actions: Sequence[str] | None = None,
    evidence_refs: Sequence[str] | None = None,
    extra_fields: Mapping[str, Any] | None = None
) -> Dict[str, Any]:
    data = load_three_org_scene_map()
    actions = _actions(requested_actions)
    blocked_actions = sorted(actions & HARD_RISK_ACTIONS)
    scene = requested_scene or classify_scene(intent_text)
    profile = resolve_scene_profile(scene, map_data=data)
    evidence = list(evidence_refs or [])
    extra = dict(extra_fields or {})

    missing_fields = []
    for key, value in {
        "intent_goal": intent_text,
        "target_scene": profile["scene"],
        "primary_module": profile["primary_module"],
        "visible_modules": profile["visible_modules"],
        "local_device_ref": local_device_ref,
        "container_profile_candidate": profile["container_profile_candidate"]
    }.items():
        if not value:
            missing_fields.append(key)

    base = {
        "intent_text": intent_text,
        "local_device_ref": local_device_ref,
        "scene_profile": profile,
        "evidence_refs": evidence,
        "blocked_actions": blocked_actions,
        "missing_fields": missing_fields,
        "extra_fields": extra
    }
    fp = _fingerprint(base)

    if blocked_actions:
        decision = "BLOCK"
        reason = "HARD_RISK_ACTION_REQUESTED"
    elif missing_fields:
        decision = "HOLD"
        reason = "MISSING_REQUIRED_THREE_ORG_SCENE_FIELD"
    else:
        decision = "PASS_CANDIDATE"
        reason = "THREE_ORG_CONTAINER_SCENE_CANDIDATE_READY_FOR_TOTAL_FIELD_REVIEW"

    packet_id = f"packet:wuchang:three-org-scene:{fp}"
    packet_hash = _sha256(
        {
            "canonical_sha256": CANONICAL_V2_1_SHA256,
            "packet_id": packet_id,
            "decision": decision,
            "evidence_refs": evidence,
        }
    )
    lineage = _append_only_lineage(packet_id, packet_hash)
    nonce = _sha256({"packet_id": packet_id, "logical_time": lineage["logical_time"]})[:32]
    risk_quarantine = {
        "blocked_actions": blocked_actions,
        "missing_fields": missing_fields,
        "live_container_switch_blocked": True,
        "docker_action_blocked": True
    }
    envelope_verification = {
        "packet_id": packet_id,
        "version": CANONICAL_V2_1_VERSION,
        "canonical_ref": CANONICAL_V2_1_PATH,
        "canonical_sha256": CANONICAL_V2_1_SHA256,
        "decision_authority": "total_field",
        "owner_admin_review_required": True,
        "nonce": nonce,
        "logical_time": lineage["logical_time"],
        "verification_mode": "L3_CANDIDATE",
        "sha256": packet_hash,
        "seal": f"candidate:{fp}"
    }
    legacy_flat_profile = {
        "d1_intent": "three_org_modules_support_odoo_community_container_scene_switch",
        "d2_state": decision,
        "d3_coordinate": {
            "target_scene": profile["scene"],
            "primary_module": profile["primary_module"],
            "visible_modules": profile["visible_modules"],
            "local_device_ref": local_device_ref
        },
        "d4_evidence": {
            "evidence_refs": evidence,
            "candidate_fingerprint": fp
        },
        "d5_execution": {
            "mode": "candidate_only",
            "container_profile_candidate": profile["container_profile_candidate"],
            "live_container_switch": False,
            "docker_compose_up": False,
            "db_write": False,
            "deploy": False,
            "restart": False
        },
        "d6_technical_definition": (
            "business_property_public_welfare_modules share Odoo community and "
            "local devices switch scene by container profile candidate"
        ),
        "d7_risk": risk_quarantine,
        "d8_envelope": envelope_verification
    }
    eight_d_packet = {
        "canonical_id": CANONICAL_V2_1_ID,
        "version": CANONICAL_V2_1_VERSION,
        "canonical_binding": _canonical_v2_1_binding(),
        "core_packet": _build_v2_1_core_packet(
            packet_id=packet_id,
            packet_hash=packet_hash,
            nonce=nonce,
            verification_level="L3_CANDIDATE",
            decision="BLOCK" if decision == "BLOCK" else "HOLD",
            intent_ref="intent:wuchang-three-org-scene",
            state_ref=f"state:{decision.lower().replace('_', '-')}",
            coordinate_ref=f"coordinate:{profile['scene'].replace('_', '-')}",
            evidence_values=evidence or [f"candidate-fingerprint:{fp}"],
            execution_ref="execution:candidate-only-container-profile",
            target_state_ref="target-state:total-field-reviewed-three-org-scene",
            lookup_refs=["lookup:wuchang-three-org-scene-profile"],
            generation_rule_refs=[
                "rule:reference-resolution",
                "rule:container-scene-state-reconstruction",
            ],
            reconstruction_condition_refs=[
                "condition:total-field-review",
                "condition:no-live-container-switch",
            ],
            hard_risks=blocked_actions,
            payload_byte_length=len(_stable_json(legacy_flat_profile).encode("utf-8")),
        ),
        "communication_contract": _communication_contract(),
        "state_field": {
            "mode": "INTERACTIVE_COUPLED_8D_STATE_FIELD",
            "transition_ref": lineage["transition_ref"],
            "total_field_verifier_ref": "verifier_ref:total_field",
        },
        "dimensions": {
            "D1_INTENT": legacy_flat_profile["d1_intent"],
            "D2_STATE": legacy_flat_profile["d2_state"],
            "D3_COORDINATE": legacy_flat_profile["d3_coordinate"],
            "D4_EVIDENCE": legacy_flat_profile["d4_evidence"],
            "D5_EXECUTION": legacy_flat_profile["d5_execution"],
            "D6_GENERATIVE_TRANSMISSION": {
                "protocol": "W7TP_8D_GENERATIVE_TRANSMISSION_V2_1",
                "mode": "L3_CANDIDATE",
                "definition": legacy_flat_profile["d6_technical_definition"],
                "reference_lookup_reconstruction": True,
                "total_field_verification": True,
            },
            "D7_RISK_QUARANTINE": risk_quarantine,
            "D8_ENVELOPE_VERIFICATION": envelope_verification,
        },
        "verification": {
            "level": "L3_CANDIDATE",
            "mode": "L3_CANDIDATE",
            "decision": decision,
        },
        "lineage": lineage,
        "adi": _adi_boundary(),
        "protected_refs": _protected_reference_boundary(),
        "legacy_profile_adapter": {
            "mode": "READ_ONLY_LEGACY_FLAT_PROFILE_PROJECTION",
            "source_profile": "wuchang_three_org_flat_8d/1.0",
            "historical_packet_rewritten": False,
            "projection": legacy_flat_profile,
        },
        **legacy_flat_profile,
    }

    return {
        "STATE": decision,
        "candidate_ref": f"three_org_scene_candidate:{fp}",
        "candidate_type": "wuchang_three_org_container_scene_candidate",
        "intent_goal": intent_text,
        "odoo_community_core": data["odoo_community_core"],
        "three_org_modules": data["three_org_modules"],
        "target_scene": profile["scene"],
        "primary_module": profile["primary_module"],
        "visible_modules": profile["visible_modules"],
        "local_device_ref": local_device_ref,
        "container_profile_candidate": profile["container_profile_candidate"],
        "landing_message": profile["landing_message"],
        "business_landing_showcases_property_and_association": profile["scene"] == "business_scene",
        "live_container_switch": False,
        "docker_compose_up": False,
        "docker_restart": False,
        "db_write": False,
        "deploy": False,
        "restart": False,
        "payment_capture": False,
        "production_activation": False,
        "evidence_refs": evidence,
        "missing_fields": missing_fields,
        "blocked_actions": blocked_actions,
        "review_chain": data["scene_switch_rules"]["same_review_chain"],
        "eight_d_packet": eight_d_packet,
        "total_field_candidate_decision": {
            "decision": decision,
            "reason": reason,
            "next": "TOTAL_FIELD_OWNER_ADMIN_REVIEW"
        }
    }


def render_three_org_scene_response(candidate: Mapping[str, Any]) -> Dict[str, Any]:
    decision = str(candidate.get("STATE") or "HOLD")

    if decision == "PASS_CANDIDATE":
        msg = str(candidate.get("landing_message") or "我先幫你整理三大模組 Odoo 社區候選場景，交給總場確認。")
    elif decision == "BLOCK":
        msg = ROOKIE_MESSAGE
    else:
        msg = "資料還不夠，我先幫你列成缺件候選，交給店長或學長確認。"

    return {
        "decision": decision,
        "member_facing_message": msg,
        "live_container_switch": False,
        "docker_compose_up": False,
        "db_write": False,
        "deploy": False,
        "restart": False,
        "next_action": "TOTAL_FIELD_OWNER_ADMIN_REVIEW"
    }
