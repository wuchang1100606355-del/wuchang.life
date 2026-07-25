from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

from tools.total_field.founder_variable_cognition_gate import (
    FUTURE_IDENTITY_ADAPTERS,
    build_sealed_founder_root,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.total_field.wuchang_three_org_container_scene_bridge import (  # noqa: E402
    ROOKIE_MESSAGE,
    bind_taiji04_local_entry_to_founder_scene,
    build_audiovisual_natural_language_service_candidate,
    build_eight_d_media_transport_packet,
    build_three_org_scene_candidate,
    classify_scene,
    load_three_org_scene_map,
    render_three_org_scene_response,
    resolve_scene_profile,
)


class WuchangThreeOrgContainerSceneBridgeTests(unittest.TestCase):
    def test_policy_is_safe(self):
        data = load_three_org_scene_map()
        self.assertFalse(data["policy"]["live_container_switch"])
        self.assertFalse(data["policy"]["docker_compose_up"])
        self.assertFalse(data["policy"]["db_write"])
        self.assertFalse(data["policy"]["deploy"])
        self.assertFalse(data["policy"]["restart"])
        self.assertEqual(
            data["odoo_community_core"]["supporting_modules"],
            ["business_organization", "property_organization", "public_welfare_organization"],
        )

    def test_classify_scenes(self):
        self.assertEqual(classify_scene("商業雲票券幸福幣"), "business_scene")
        self.assertEqual(classify_scene("物業雲公道伯法令"), "property_scene")
        self.assertEqual(classify_scene("協會公益志工許願樹"), "association_scene")
        self.assertEqual(classify_scene("創辦人統覽商家物業與公益"), "founder_scene")

    def test_business_scene_shows_property_and_association(self):
        profile = resolve_scene_profile("business_scene")
        self.assertEqual(profile["primary_module"], "business_organization")
        self.assertIn("property_organization", profile["visible_modules"])
        self.assertIn("public_welfare_organization", profile["visible_modules"])
        self.assertFalse(profile["live_container_action"])

    def test_property_scene_uses_property_container_candidate(self):
        profile = resolve_scene_profile("property_scene")
        self.assertEqual(profile["container_profile_candidate"], "container_profile:property_cloud_candidate")
        self.assertEqual(profile["primary_module"], "property_organization")

    def test_association_scene_uses_public_welfare_module(self):
        profile = resolve_scene_profile("association_scene")
        self.assertEqual(profile["primary_module"], "public_welfare_organization")
        self.assertEqual(profile["container_profile_candidate"], "container_profile:association_public_welfare_candidate")

    def test_build_business_landing_candidate(self):
        candidate = build_three_org_scene_candidate(intent_text="商業落地展示物業及協會")
        self.assertEqual(candidate["STATE"], "PASS_CANDIDATE")
        self.assertEqual(candidate["target_scene"], "business_scene")
        self.assertTrue(candidate["business_landing_showcases_property_and_association"])
        self.assertFalse(candidate["live_container_switch"])
        self.assertIn("eight_d_packet", candidate)

    def test_hard_risk_blocks_live_container_switch(self):
        candidate = build_three_org_scene_candidate(
            intent_text="直接換容器啟用商業場景",
            requested_actions=["live_container_switch", "docker_compose_up"]
        )
        self.assertEqual(candidate["STATE"], "BLOCK")
        self.assertIn("live_container_switch", candidate["blocked_actions"])
        self.assertIn("docker_compose_up", candidate["blocked_actions"])
        response = render_three_org_scene_response(candidate)
        self.assertEqual(response["member_facing_message"], ROOKIE_MESSAGE)

    def test_8d_packet_has_total_field_authority(self):
        candidate = build_three_org_scene_candidate(intent_text="物業雲場景")
        packet = candidate["eight_d_packet"]
        self.assertEqual(packet["d8_envelope"]["decision_authority"], "total_field")
        self.assertTrue(packet["d8_envelope"]["owner_admin_review_required"])
        self.assertTrue(packet["d7_risk"]["live_container_switch_blocked"])
        self.assertTrue(packet["d7_risk"]["docker_action_blocked"])


    def test_taiji04_audiovisual_console_profile(self):
        service = load_three_org_scene_map()["taiji04_audiovisual_natural_language_service"]
        self.assertEqual(service["state"], "SOURCE_CANDIDATE_ENABLED")
        self.assertEqual(service["node_ref"], "node_ref:taiji04")
        self.assertTrue(service["platform"]["touchscreen"])
        self.assertTrue(service["platform"]["external_hdmi_display"])
        self.assertIn("merchant_backend", service["role_workspaces"])
        self.assertIn("community_secretary_backend", service["role_workspaces"])
        self.assertIn("chair_and_secretary_backend", service["role_workspaces"])
        self.assertFalse(service["hdmi_window"]["member_plaintext"])

    def test_founder_local_audiovisual_scene_reuses_three_org_candidate(self):
        profile = resolve_scene_profile("founder_scene")
        self.assertEqual(profile["scene"], "founder_scene")
        self.assertEqual(profile["scene_role"], "cross_organization_founder_local_console")
        self.assertEqual(
            profile["container_profile_candidate"],
            "container_profile:business_cloud_candidate"
        )
        self.assertEqual(
            set(profile["visible_modules"]),
            {"business_organization", "property_organization", "public_welfare_organization"}
        )
        self.assertFalse(profile["live_container_action"])

    def test_founder_local_audiovisual_candidate_is_gated_and_not_runtime_bound(self):
        candidate = build_audiovisual_natural_language_service_candidate(
            intent_text="創辦人以影音統覽商業物業公益候選",
            input_mode="audiovisual_event"
        )
        control = candidate["founder_scene_control"]
        self.assertEqual(candidate["STATE"], "PASS_CANDIDATE")
        self.assertEqual(candidate["target_scene"], "founder_scene")
        self.assertEqual(control["principal_ref"], "member_ref:founder")
        self.assertEqual(
            control["identity_gate_ref"],
            "gate_ref:existing_local_founder_root"
        )
        self.assertTrue(control["explicit_founder_command_per_action"])
        self.assertTrue(control["total_field_review_required"])
        self.assertTrue(control["local_only"])
        self.assertFalse(control["runtime_bound"])
        self.assertFalse(control["authority_increase"])
        self.assertFalse(control["founder_private_detail_on_hdmi"])
        self.assertTrue(
            candidate["eight_d_packet"]["d7_risk"]["founder_identity_gate_required"]
        )

    def test_founder_scene_blocks_production_activation(self):
        candidate = build_audiovisual_natural_language_service_candidate(
            intent_text="創辦人影音場景直接啟用",
            input_mode="voice",
            requested_actions=["production_activation"]
        )
        self.assertEqual(candidate["STATE"], "BLOCK")
        self.assertEqual(candidate["target_scene"], "founder_scene")
        self.assertIn("production_activation", candidate["blocked_actions"])

    def test_audiovisual_candidate_builds_schema_valid_8d_media_packets(self):
        candidate = build_audiovisual_natural_language_service_candidate(
            intent_text="社區總幹事以影音說明住戶服務",
            input_mode="audiovisual_event"
        )
        self.assertEqual(candidate["STATE"], "PASS_CANDIDATE")
        self.assertFalse(candidate["runtime_activation"])
        self.assertFalse(candidate["raw_media_to_cloud"])
        self.assertEqual(
            set(candidate["media_transport_packets"]),
            {"image", "audio", "audiovisual_sync"}
        )
        schema = json.loads(
            Path("schemas/w7tp_8d_multipurpose_packet_canonical_v2.schema.json").read_text(
                encoding="utf-8"
            )
        )
        validator = Draft202012Validator(schema)
        for packet in candidate["media_transport_packets"].values():
            validator.validate(packet)

    def test_audio_defaults_to_non_source_l2_equivalent_reconstruction(self):
        packet = build_eight_d_media_transport_packet(domain="AUDIO")
        self.assertEqual(packet["verification"]["level"], "L2_EQUIVALENT")
        self.assertEqual(
            packet["verification"]["method_ref"],
            "verifier_ref:audio_non_source_equivalent"
        )
        self.assertEqual(
            packet["generation_packet"]["target_equivalence"],
            "AUDIO_SEMANTIC_TIMING_PROSODY_AND_SERVICE_EFFECT_EQUIVALENT"
        )
        self.assertIn(
            "non_source_audio_equivalent_reconstruction",
            packet["generation_packet"]["generation_rule"]
        )

    def test_authorized_commercial_voice_endpoint_is_candidate_only(self):
        candidate = build_audiovisual_natural_language_service_candidate(
            intent_text="商米語音端點播報服務提醒",
            input_mode="voice"
        )
        endpoint = candidate["authorized_commercial_voice_endpoint_candidate"]
        speech = candidate["eight_d_media_transport_basis"]["audio_packet"][
            "speech_control_profile"
        ]
        self.assertEqual(endpoint["hardware_class"], "SUNMI_POS")
        self.assertEqual(endpoint["execution_node_ref"], "node_ref:taiji04")
        self.assertTrue(endpoint["same_as_taiji04_hardware"])
        self.assertTrue(endpoint["google_commercial_voice_hardware_license"])
        self.assertEqual(endpoint["network_scope"], "authorized_vpn_node_only")
        self.assertTrue(endpoint["authorization_evidence_required"])
        self.assertFalse(endpoint["runtime_bound"])
        self.assertFalse(endpoint["actuation_without_authorization"])
        self.assertFalse(endpoint["source_voice_copy"])
        self.assertTrue(speech["pronunciation_lexicon_ref"])
        self.assertTrue(speech["emotion_class_and_bounded_intensity_ref"])

    def test_three_d_scene_builds_video_packet_for_film_reconstruction(self):
        candidate = build_audiovisual_natural_language_service_candidate(
            intent_text="以3D場景重構社區服務短片",
            input_mode="three_d_scene"
        )
        packet = candidate["media_transport_packets"]["three_d_film"]
        design = candidate["eight_d_media_transport_basis"]["three_d_scene_film_packet"]
        asset = design["asset_candidates"][0]
        self.assertEqual(packet["domain_profile"]["domain"], "VIDEO")
        self.assertEqual(design["reconstruction"], "local_3d_scene_to_verified_film_candidate")
        self.assertFalse(design["raw_video_file_transfer"])
        self.assertEqual(asset["asset_ref"], "asset_ref:J.vroid_user_supplied")
        self.assertFalse(asset["binary_available_on_current_linux_node"])
        self.assertIsNone(asset["sha256"])
        self.assertFalse(asset["raw_asset_transfer"])

    def test_raw_media_cloud_and_live_stream_actions_block(self):
        candidate = build_audiovisual_natural_language_service_candidate(
            intent_text="將現場影音送雲端",
            input_mode="audiovisual_event",
            requested_actions=["raw_audio_to_cloud", "live_camera_stream"]
        )
        self.assertEqual(candidate["STATE"], "BLOCK")
        self.assertEqual(
            candidate["blocked_actions"],
            ["live_camera_stream", "raw_audio_to_cloud"]
        )


class Taiji04FounderSceneEntryBindingTests(unittest.TestCase):
    command_ref = "command_ref:taiji04-founder-binding-fixture"

    def setUp(self):
        self.root = build_sealed_founder_root(
            "sha256:" + "1" * 64,
            "https://accounts.google.com",
            "2" * 64
        )
        self.identity_request = {
            "device_principal_fingerprint": "sha256:" + "1" * 64,
            "google_oidc_issuer": "https://accounts.google.com",
            "google_oidc_subject_sha256": "2" * 64,
            "explicit_founder_command": True,
            "founder_command_ref": self.command_ref,
            "d8_decision": "ALLOW",
            "future_identity_adapters": dict(FUTURE_IDENTITY_ADAPTERS)
        }
        self.developer_request = {
            "member_ref": "member_ref:founder",
            "xiaoj_agent_ref": "xiaoj_agent_ref:founder-local",
            "member_role_refs": ["role_ref:founder_developer"],
            "organization_context": {
                "organization_ref": "organization_ref:taiji",
                "scope_refs": ["scope_ref:taiji04-founder-scene"]
            },
            "device_or_channel_binding": {
                "binding_type": "DEVICE",
                "binding_ref": "device_ref:taiji04",
                "binding_hash": hashlib.sha256(b"taiji04-fixture").hexdigest()
            },
            "delegation_envelope": {
                "delegation_ref": "delegation_ref:taiji04-founder-fixture",
                "issuer_member_ref": "member_ref:founder",
                "subject_member_ref": "member_ref:founder",
                "bound_xiaoj_agent_ref": "xiaoj_agent_ref:founder-local",
                "allowed_role_refs": ["role_ref:founder_developer"],
                "issued_at_epoch": 100,
                "expires_at_epoch": 200,
                "nonce": "nonce:taiji04-delegation-fixture",
                "revoked": False,
                "subdelegation": False
            },
            "ttl_seconds": 100,
            "nonce": "nonce:taiji04-session-fixture",
            "revocation_state": "ACTIVE",
            "membership_state": "ACTIVE",
            "principal_verified": True,
            "command_ref": self.command_ref,
            "verification_refs": [
                "evidence_ref:founder-root-fixture",
                "evidence_ref:developer-card-fixture"
            ]
        }
        self.roles = {
            "member_ref:founder": ["role_ref:founder_developer", "role_ref:member"],
            "member_ref:member-a": ["role_ref:member"]
        }
        command_hash = hashlib.sha256(
            json.dumps(
                self.command_ref,
                ensure_ascii=False,
                sort_keys=True,
                default=str
            ).encode("utf-8")
        ).hexdigest()
        self.preflight = {
            "decision": "PASS",
            "candidate_only": True,
            "formal_execution_authority": False,
            "command_ref_sha256": command_hash
        }

    def bind(self, *, input_mode="audiovisual_event", intent_text="商家物業公益統覽"):
        return bind_taiji04_local_entry_to_founder_scene(
            intent_text=intent_text,
            input_mode=input_mode,
            developer_session_request=self.developer_request,
            role_table=self.roles,
            current_epoch=110,
            founder_identity_request=self.identity_request,
            sealed_founder_root=self.root,
            total_field_preflight_receipt=self.preflight,
            lawful_scope_confirmed=True,
            evidence_refs=["evidence_ref:taiji04-binding-fixture"]
        )

    def test_entry_calls_existing_founder_scene_and_priority_wins(self):
        target = (
            "tools.total_field.wuchang_three_org_container_scene_bridge."
            "build_audiovisual_natural_language_service_candidate"
        )
        with patch(target, wraps=build_audiovisual_natural_language_service_candidate) as called:
            result = self.bind(intent_text="商家物業公益場景")
        called.assert_called_once()
        self.assertEqual(called.call_args.kwargs["requested_scene"], "founder_scene")
        self.assertEqual(result["STATE"], "PASS_TAIJI04_FOUNDER_SCENE_SOURCE_BOUND")
        self.assertEqual(result["target_scene"], "founder_scene")
        self.assertEqual(result["cloud_candidate"], "business_cloud_candidate")
        self.assertFalse(result["runtime_enabled"])
        self.assertFalse(result["formal_execution_authority"])
        self.assertEqual(
            result["scene_envelope"]["checkout_workstation_mode"],
            "CLERK_HUMAN_CONTROLLED"
        )
        self.assertTrue(
            result["scene_envelope"][
                "member_checkout_requires_purchasing_member_confirmation"
            ]
        )
        self.assertFalse(
            result["scene_envelope"]["clerk_may_substitute_member_confirmation"]
        )
        self.assertFalse(
            result["scene_envelope"]["ai_may_substitute_member_confirmation"]
        )
        self.assertFalse(result["scene_envelope"]["autonomous_checkout"])
        self.assertFalse(result["scene_envelope"]["payment_execution"])

    def test_non_founder_developer_card_cannot_pass(self):
        self.developer_request["member_ref"] = "member_ref:member-a"
        self.developer_request["xiaoj_agent_ref"] = "xiaoj_agent_ref:member-a"
        self.developer_request["member_role_refs"] = ["role_ref:member"]
        delegation = self.developer_request["delegation_envelope"]
        delegation["issuer_member_ref"] = "member_ref:member-a"
        delegation["subject_member_ref"] = "member_ref:member-a"
        delegation["bound_xiaoj_agent_ref"] = "xiaoj_agent_ref:member-a"
        delegation["allowed_role_refs"] = ["role_ref:member"]
        result = self.bind()
        self.assertNotEqual(result["STATE"], "PASS_TAIJI04_FOUNDER_SCENE_SOURCE_BOUND")
        self.assertFalse(result["founder_scene_binding"])

    def test_missing_per_action_founder_command_cannot_pass(self):
        self.identity_request["explicit_founder_command"] = False
        result = self.bind()
        self.assertEqual(result["STATE"], "BLOCK_NO_EXPLICIT_FOUNDER_COMMAND")
        self.assertFalse(result["founder_scene_binding"])

    def test_all_input_modes_share_one_founder_scene_envelope(self):
        for mode in ("text", "voice", "image_event", "audiovisual_event", "three_d_scene"):
            with self.subTest(mode=mode):
                result = self.bind(input_mode=mode)
                envelope = result["scene_envelope"]
                self.assertEqual(envelope["entry_ref"], "entry_ref:taiji04_local_audiovisual_natural_language")
                self.assertEqual(envelope["scene_ref"], "scene_ref:founder_scene")
                self.assertEqual(envelope["input_mode"], mode)
                self.assertFalse(envelope["formal_execution_authority"])

    def test_cloud_fragment_excludes_identity_hdmi_raw_media_secret_and_plaintext(self):
        result = self.bind()
        fragment = result["cloud_fragment"]
        serialized = json.dumps(fragment, ensure_ascii=False).casefold()
        for forbidden in (
            "member_ref",
            "principal_ref",
            "founder_identity",
            "hdmi_private",
            "raw_audio",
            "raw_video",
            "secret",
            "member_plaintext"
        ):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(fragment["payload_mode"], "DEIDENTIFIED_INCOMPLETE_REFERENCE_ONLY")
        self.assertEqual(fragment["cloud_candidate"], "business_cloud_candidate")

    def test_isolated_total_field_receipt_has_no_execution_or_commit(self):
        result = self.bind()
        receipt = result["total_field_receipt"]
        self.assertEqual(receipt["state"], "ISOLATED_TOTAL_FIELD_CANDIDATE_RECEIPT")
        self.assertEqual(receipt["final_decision"], "HOLD")
        self.assertFalse(receipt["commit_applied"])
        self.assertEqual(receipt["lifecycle"], "CANDIDATE")
        self.assertFalse(receipt["formal_execution_authority"])
        self.assertRegex(result["packet_sha256"], r"^[0-9a-f]{64}\Z")
        self.assertRegex(receipt["receipt_sha256"], r"^[0-9a-f]{64}\Z")

    def test_taiji04_taiji03_and_drallion_roles_are_distinct(self):
        result = self.bind()
        service = load_three_org_scene_map()[
            "taiji04_audiovisual_natural_language_service"
        ]
        platform = service["platform"]
        roles = service["organization_node_roles"]
        endpoint = service["organization_audiovisual_execution_point"]
        self.assertEqual(
            service["node_role"],
            "sunmi_pos_clerk_human_controlled_checkout_and_google_commercial_voice_endpoint"
        )
        self.assertEqual(
            roles["node_ref:taiji04"],
            "sunmi_pos_clerk_human_controlled_checkout_workstation_and_google_commercial_voice_hardware"
        )
        self.assertEqual(
            roles["node_ref:taiji03"],
            "organization_super_administrator_control_device"
        )
        self.assertEqual(
            roles["node_ref:drallion"],
            "organization_service_desk_audiovisual_ai_execution_point"
        )
        titles = service["organization_node_role_titles"]
        self.assertEqual(titles["node_ref:taiji03"], "組織超級管理員控制設備")
        self.assertEqual(
            titles["node_ref:taiji04"],
            "商米 POS 店員人控結帳作業台及 Google 商用語音硬體"
        )
        self.assertEqual(service["workspace_host_node_ref"], "node_ref:taiji03")
        self.assertEqual(
            service["role_workspaces"]["clerk_human_controlled_checkout_workspace"],
            "店員人控結帳作業台"
        )
        self.assertEqual(
            platform["hardware_class"],
            "SUNMI_POS"
        )
        self.assertEqual(
            platform["network_role"],
            "LOCAL_CONTROL_AND_VOICE_HARDWARE_NOT_PUBLIC_ENDPOINT"
        )
        self.assertTrue(platform["google_commercial_voice_hardware_license"])
        self.assertTrue(platform["clerk_human_controlled_checkout_workstation"])
        self.assertTrue(
            platform["member_checkout_requires_purchasing_member_confirmation"]
        )
        self.assertFalse(platform["clerk_may_substitute_member_confirmation"])
        self.assertFalse(platform["ai_may_substitute_member_confirmation"])
        self.assertFalse(platform["administrator_may_substitute_member_confirmation"])
        self.assertFalse(platform["identity_verification_equals_checkout_consent"])
        self.assertFalse(platform["autonomous_checkout"])
        self.assertFalse(platform["payment_execution"])
        self.assertEqual(platform["network_node_ref"], "node_ref:taiji04")
        self.assertFalse(platform["public_endpoint"])
        self.assertEqual(endpoint["node_ref"], "node_ref:drallion")
        self.assertEqual(
            endpoint["node_role"],
            "organization_service_desk_audiovisual_ai_execution_point"
        )
        self.assertEqual(
            endpoint["hardware_relation"],
            "SEPARATE_ORGANIZATION_AUDIOVISUAL_EXECUTION_NODE"
        )
        self.assertEqual(endpoint["hardware_class_evidence_state"], "UNKNOWN_NOT_SHOWN")
        self.assertEqual(
            endpoint["google_commercial_voice_hardware_license_evidence_state"],
            "UNKNOWN_NOT_SHOWN"
        )
        self.assertEqual(endpoint["platform"], "ANDROID")
        self.assertEqual(endpoint["os_version"], "13")
        display = endpoint["display_hardware"]
        self.assertEqual(display["display_count"], 2)
        self.assertTrue(display["touchscreen"])
        self.assertTrue(display["external_hdmi_display"])
        self.assertFalse(display["founder_private_detail_on_hdmi"])
        self.assertFalse(display["member_plaintext_on_hdmi"])
        self.assertFalse(display["secret_on_hdmi"])
        self.assertFalse(display["raw_media_on_hdmi"])
        self.assertEqual(endpoint["private_network"], "TAILSCALE")
        self.assertTrue(endpoint["assigned_execution_point"])
        self.assertFalse(endpoint["service_runtime_verified"])
        self.assertFalse(endpoint["runtime_enabled"])
        self.assertFalse(endpoint["invite_url_stored"])
        self.assertFalse(endpoint["node_key_stored"])
        self.assertEqual(
            result["scene_envelope"]["execution_node_ref"],
            "node_ref:drallion"
        )
        self.assertEqual(
            result["scene_envelope"]["entry_network_role"],
            "LOCAL_CONTROL_AND_VOICE_HARDWARE_NOT_PUBLIC_ENDPOINT"
        )

    def test_member_and_guest_checkout_paths_preserve_identity_and_consent(self):
        result = self.bind()
        checkout_paths = result["checkout_paths"]
        member_ai = result["member_centered_sovereign_ai"]
        browser = checkout_paths["member_mobile_browser_ai"]
        counter = checkout_paths["counter_xiaoj_audiovisual_natural_language"]
        clerk = checkout_paths["clerk_phone_last_three_digits"]
        guest = checkout_paths["non_member_guest"]

        self.assertTrue(browser["enabled_as_source_candidate"])
        self.assertTrue(browser["purchasing_member_confirmation_required"])
        self.assertFalse(browser["ai_may_confirm_for_member"])
        self.assertTrue(counter["merchant_service_xiaoj_assistance"])
        self.assertTrue(counter["purchasing_member_confirmation_required"])
        self.assertFalse(counter["xiaoj_may_confirm_for_member"])
        self.assertEqual(clerk["input_purpose"], "MEMBER_LOOKUP_HINT_ONLY")
        self.assertFalse(clerk["identity_authentication"])
        self.assertFalse(clerk["checkout_consent"])
        self.assertTrue(clerk["purchasing_member_confirmation_required"])
        self.assertEqual(guest["phone_last_three_digits_input"], "BLANK")
        self.assertEqual(guest["checkout_label"], "一般路人")
        self.assertFalse(guest["member_identity_packet_access"])
        self.assertFalse(guest["member_resource_access"])

        self.assertTrue(member_ai["member_is_system_participant"])
        self.assertTrue(
            member_ai[
                "system_bound_identity_packet_required_for_member_resource_access"
            ]
        )
        self.assertEqual(
            member_ai["resource_access_mode"],
            "CAPABILITY_AND_RESOURCE_REFERENCES_ONLY"
        )
        self.assertTrue(member_ai["resource_scope_must_match_purchasing_member"])
        self.assertFalse(member_ai["cross_member_resource_access"])
        self.assertFalse(member_ai["member_plaintext_to_cloud"])
        self.assertFalse(member_ai["raw_identity_material_to_cloud"])
        self.assertFalse(member_ai["identity_verification_equals_checkout_consent"])
        self.assertTrue(member_ai["phone_last_three_digits_are_lookup_hint_only"])
        self.assertFalse(member_ai["non_member_guest_has_member_resource_access"])

    def test_existing_three_org_routes_are_unchanged(self):
        self.assertEqual(resolve_scene_profile("business_scene")["primary_module"], "business_organization")
        self.assertEqual(resolve_scene_profile("property_scene")["primary_module"], "property_organization")
        self.assertEqual(resolve_scene_profile("association_scene")["primary_module"], "public_welfare_organization")


if __name__ == "__main__":
    unittest.main(verbosity=2)
