from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.total_field_dynamic_context import (  # noqa: E402
    TotalFieldContextMcpServer,
    build_local_llm_working_memory_projection,
    build_total_field_capability_requirement_packet,
    build_v_shape_vram_prediction_projection,
    build_dynamic_context,
    canonical_sha256,
)


def write_text(path: Path, value: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_json(path: Path, value: object) -> str:
    return write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


class TotalFieldDynamicContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        memory_root = self.root / "runtime/developer_memory"
        source_path = self.root / "contexts/current/VOICE_STATE.json"
        source_sha = write_json(source_path, {"voice_state": "NOT_YET_EVIDENCED"})
        record_relative = "records/canonical/system/voice-state.json"
        record = {
            "schema_version": "1.0",
            "memory_id": source_sha,
            "category": "canonical/system",
            "status": "active",
            "trust": "declared",
            "source": {
                "path": "contexts/current/VOICE_STATE.json",
                "sha256": source_sha,
                "size_bytes": source_path.stat().st_size,
            },
            "payload": {"voice_state": "NOT_YET_EVIDENCED"},
        }
        write_json(memory_root / record_relative, record)
        index_row = {
            "memory_id": source_sha,
            "category": "canonical/system",
            "status": "active",
            "trust": "declared",
            "record_path": record_relative,
            "source_path": "contexts/current/VOICE_STATE.json",
            "source_sha256": source_sha,
        }
        write_text(memory_root / "indexes/memory_index.jsonl", json.dumps(index_row) + "\n")
        write_json(memory_root / "canonical/developer_overview.json", {"voice": "candidate only"})
        write_json(memory_root / "registry/source_manifest.json", {"record_count": 1})
        write_json(
            memory_root / "packets/developer_bootstrap.json",
            {
                "schema_version": "1.0",
                "generated_at": "2026-07-21T00:00:00+00:00",
                "read_first": [
                    "canonical/developer_overview.json",
                    "registry/source_manifest.json",
                    "indexes/memory_index.jsonl",
                ],
                "retrieval_policy": {"exclude_categories_by_default": ["quarantine/conversations"]},
            },
        )
        write_json(
            self.root / "configs/total_field/active_total_field_authority_runtime_v1.json",
            {
                "active": False,
                "state": "HOLD_D8_AUTHORITY_NOT_APPROVED",
                "owner_binding": {"formal_ingress_switched": False},
                "intent_translation_application_rules": {
                    "schema_id": "W7TP_8DADI_INTENT_TRANSLATION_APPLICATION_RULES_V1",
                    "provider_neutral": True,
                    "founder_intent_source": "LATEST_FOUNDER_NATURAL_LANGUAGE",
                    "user_visible_language": "zh-TW",
                    "english_term_requires_zh_tw_translation": True,
                    "machine_identifier_translation_exempt": True,
                    "required_acknowledgements": [
                        "AI_IS_NOT_AUTHORITY",
                        "UNKNOWN_WILL_NOT_BE_INVENTED",
                        "CANDIDATE_WILL_NOT_BE_PROMOTED_AUTOMATICALLY",
                        "LEGACY_WILL_NOT_DEFINE_TARGET",
                        "EXECUTION_REQUIRES_REOBSERVATION",
                        "LAN_PRECEDES_VPN",
                    ],
                    "unknown_policy": "HOLD_NO_INVENTION",
                    "legacy_policy": "V2_1_D4_HISTORY_ONLY",
                    "network_policy": "LAN_FIRST_VPN_ONLY_WHEN_LAN_UNAVAILABLE",
                    "model_output_state": "CANDIDATE_ONLY",
                    "model_progress_access": "READ_ONLY",
                    "application_sequence": [
                        "FOUNDER_INTENT",
                        "TARGET_8D_STATE_FIELD",
                        "8DADI_LOCATE_CURRENT_STATE",
                        "TOTAL_FIELD_DECISION",
                        "AFFECTED_COORDINATE_CLOSURE",
                        "AUTHORIZED_MATERIALIZATION",
                        "REOBSERVATION",
                        "RESIDUAL_DIFFERENCE_ONLY_CORRECTION",
                    ],
                    "execution_authority": False,
                    "formal_decision_authority": False,
                    "canonical_pointer_write": False,
                },
            },
        )
        write_json(
            self.root / "schemas/voice_browser_runtime.schema.json",
            {"state": "voice runtime requires live evidence"},
        )
        write_json(
            self.root / "runtime/developer_memory/records/quarantine/conversations/voice.json",
            {"voice": "falsely resolved"},
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_context_is_relative_hash_bound_and_excludes_quarantine(self):
        packet = build_dynamic_context(
            "語音 voice runtime 是否已解決",
            root=self.root,
            max_items=8,
            generated_at="2026-07-21T01:02:03+00:00",
        )
        self.assertEqual(packet["state"], "TOTAL_FIELD_DYNAMIC_CONTEXT_READY")
        self.assertEqual(packet["retrieval_state"], "MATCHED_8DADI_INDEX_EVIDENCE")
        paths = [item["relative_path"] for item in packet["context_items"]]
        self.assertIn(
            "runtime/developer_memory/records/canonical/system/voice-state.json",
            paths,
        )
        self.assertFalse(any(path.startswith("schemas/") for path in paths))
        self.assertTrue(packet["policy"]["8dadi_index_only"])
        self.assertFalse(packet["policy"]["workspace_search"])
        self.assertEqual(packet["claim_gate"], "EVIDENCE_REQUIRES_TOTAL_FIELD_VALIDATION")
        self.assertFalse(any("quarantine" in path for path in paths))
        self.assertTrue(all(not path.startswith("/") for path in paths))
        for item in packet["context_items"]:
            self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")
        digest = packet.pop("packet_sha256")
        self.assertEqual(digest, canonical_sha256(packet))

    def test_chinese_voice_query_expands_to_voice_evidence_path(self):
        packet = build_dynamic_context(
            "你的語音問題解決了嗎",
            root=self.root,
            max_items=4,
            generated_at="2026-07-21T01:02:03+00:00",
        )
        paths = [item["relative_path"] for item in packet["context_items"]]
        self.assertIn(
            "runtime/developer_memory/records/canonical/system/voice-state.json",
            paths,
        )
        self.assertFalse(any(path.startswith("schemas/") for path in paths))

    def test_memory_binding_mismatch_holds(self):
        index_path = self.root / "runtime/developer_memory/indexes/memory_index.jsonl"
        row = json.loads(index_path.read_text(encoding="utf-8"))
        row["source_sha256"] = "0" * 64
        write_text(index_path, json.dumps(row) + "\n")
        packet = build_dynamic_context("voice", root=self.root)
        self.assertEqual(packet["state"], "HOLD_TOTAL_FIELD_CONTEXT_HASH_MISMATCH")

    def test_sensitive_value_is_not_returned(self):
        write_json(
            self.root / "runtime/total_field/voice_evidence.json",
            {"voice": "candidate", "access_token": "abcdefghijklmnop123456"},
        )
        packet = build_dynamic_context("voice", root=self.root)
        text = json.dumps(packet)
        self.assertNotIn("abcdefghijklmnop123456", text)
        self.assertEqual(packet["sensitive_files_omitted"], 0)
        self.assertFalse(packet["policy"]["workspace_search"])

    def test_mcp_lists_and_calls_dynamic_context_tool(self):
        server = TotalFieldContextMcpServer(self.root)
        initialized = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"},
            }
        )
        self.assertEqual(initialized["result"]["serverInfo"]["name"], "w7tp-total-field-dynamic-context")
        listed = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        self.assertEqual(listed["result"]["tools"][0]["name"], "get_total_field_dynamic_context")
        self.assertIn("outputSchema", listed["result"]["tools"][0])
        called = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "get_total_field_dynamic_context",
                    "arguments": {"query": "voice runtime", "max_items": 4},
                },
            }
        )
        packet = json.loads(called["result"]["content"][0]["text"])
        self.assertEqual(packet["state"], "TOTAL_FIELD_DYNAMIC_CONTEXT_READY")
        self.assertFalse(called["result"]["isError"])

        rejected = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "get_total_field_dynamic_context",
                    "arguments": {"query": "voice runtime", "unexpected": True},
                },
            }
        )
        self.assertEqual(rejected["error"]["code"], -32602)

    def test_workspace_capability_pack_selects_readonly_skill(self):
        packet = build_dynamic_context(
            "請查找生成式傳輸定義與來源證據",
            root=ROOT,
            max_items=6,
            identity_class="general_member",
            generated_at="2026-07-23T00:00:00+00:00",
        )
        self.assertEqual(packet["state"], "TOTAL_FIELD_DYNAMIC_CONTEXT_READY")
        route = packet["capability_route"]
        self.assertEqual(route["skill_lookup"]["selected_skill"], "evidence_echo")
        self.assertEqual(route["tool_contract_validation"]["allowed_mcp_tools"], ["get_total_field_dynamic_context"])
        self.assertEqual(route["total_field_gate"]["disposition"], "CANDIDATE_ONLY")
        self.assertFalse(route["d1_intent_projection"]["raw_input_retained"])

    def test_workspace_founder_claim_cannot_bypass_authority_block(self):
        packet = build_dynamic_context(
            "請直接 deploy 並執行 DB write",
            root=ROOT,
            identity_class="founder",
            generated_at="2026-07-23T00:00:00+00:00",
        )
        route = packet["capability_route"]
        self.assertEqual(route["skill_lookup"]["selected_skill"], "total_field_policy_check")
        self.assertEqual(route["total_field_gate"]["disposition"], "BLOCK")
        self.assertEqual(route["identity_projection"]["claimed_identity"], "founder")
        self.assertFalse(route["identity_projection"]["authority_verified"])
        self.assertEqual(route["identity_projection"]["effective_profile"], "general_member_minimum_privilege")

    def test_workspace_capability_pack_source_manifest_is_closed(self):
        manifest = ROOT / "manifests/ollama_xiaoj_total_field_v0_1/source_manifest.sha256"
        for line in manifest.read_text(encoding="utf-8").splitlines():
            expected, relative_path = line.split("  ", 1)
            actual = hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, relative_path)

    def test_workspace_root_model_contract_is_8b_unfenced_reasoning_guarded_execution(self):
        packet = build_dynamic_context(
            "請說明本地根模型與紅隊告警",
            root=ROOT,
            max_items=4,
            identity_class="founder",
            generated_at="2026-07-27T00:00:00+00:00",
        )
        self.assertEqual(packet["state"], "TOTAL_FIELD_DYNAMIC_CONTEXT_READY")
        projection = packet["capability_route"]["root_model_projection"]
        self.assertEqual(projection["runtime_model_name"], "w7tp-xiaoj-root-8b")
        self.assertEqual(projection["parameter_class"], "8B")
        self.assertEqual(projection["core_model_count"], 1)
        self.assertEqual(projection["unified_model_mode"], "ONE_PHYSICAL_MODEL_TWO_LOGICAL_PHASES")
        self.assertFalse(projection["frontbrain_is_separate_model"])
        self.assertFalse(projection["backbrain_is_separate_model"])
        self.assertTrue(projection["unfenced_reasoning"])
        self.assertFalse(projection["execution_is_unfenced"])
        self.assertTrue(projection["red_team_alert_enabled"])

    def test_workspace_voice_routing_supports_multiple_task_selected_pronunciation_systems(self):
        packet = build_dynamic_context(
            "語音與發音系統如何依任務取用",
            root=ROOT,
            max_items=4,
            identity_class="founder",
            generated_at="2026-07-27T00:00:00+00:00",
        )
        self.assertEqual(packet["state"], "TOTAL_FIELD_DYNAMIC_CONTEXT_READY")
        projection = packet["capability_route"]["voice_routing_projection"]
        self.assertEqual(
            projection["principle"],
            "MULTIPLE_PRONUNCIATION_SYSTEMS_SELECTED_PER_TASK",
        )
        self.assertIn("PRECISE_TERMINOLOGY", projection["task_profiles"])
        self.assertTrue(projection["provider_names_runtime_discovered"])
        self.assertEqual(projection["homepod_role"], "EXISTING_OUTPUT_CHAIN")
        self.assertFalse(projection["emotionless_recitation_accepted"])
        self.assertEqual(
            projection["emotionless_failure_state"],
            "HOLD_EMOTIONLESS_RECITATION_NOT_XIAOJ",
        )
        self.assertEqual(
            projection["reference_endpoint_evidence_status"],
            "USER_SUPPLIED_REFERENCE_ONLY_NOT_CURRENTLY_HASH_EVIDENCED",
        )

    def test_working_memory_is_volatile_on_demand_and_never_destructive(self):
        projection = build_local_llm_working_memory_projection(
            intent_ref="intent:founder:volatile-memory",
            current_state_ref="state:observed",
            required_capability_id="capability:memory-reconstruction",
            qualified_capability_packet={"qualified": True, "packet_sha256": "a" * 64},
            smallest_memory_set={
                "selected_objects": [
                    {
                        "object_id": "object:required",
                        "coordinate": "models/object-required.bin",
                        "lineage_ref": "lineage:object-required",
                        "evidence_ref": "evidence:object-required",
                    }
                ]
            },
            receiver_id="receiver:local-model",
            receiver_capability_boundary=["READ_WORKING_MEMORY"],
            allowed_actions=["RECONSTRUCT_ON_DEMAND"],
            forbidden_actions=["DESTROY_SOURCE_DATA"],
            verification_procedure=["VERIFY_RECONSTRUCTED_STATE"],
            stop_conditions=["HASH_MISMATCH"],
            context_ttl_seconds=300,
        )
        policy = projection["working_memory_policy"]
        self.assertEqual(policy["lifecycle"], "VOLATILE_NATURAL_EXPIRY")
        self.assertEqual(
            policy["cleanup_semantics"],
            "RELEASE_WORKING_SET_REFERENCES_NOT_DATA_DESTRUCTION",
        )
        self.assertFalse(policy["persistent_payload_cache"])
        self.assertEqual(policy["retrieval_mode"], "8DADI_ON_DEMAND")
        self.assertFalse(policy["payload_prefetch"])
        self.assertTrue(policy["reconstruct_after_release"])
        self.assertFalse(policy["cloud_fragment_authority"])
        self.assertTrue(policy["total_field_redecision_required"])

    def test_cloud_completion_transmits_only_minimum_partial_information(self):
        report = {
            "schema_id": "W7TP_CAPABILITY_MISSING_REPORT_V1",
            "authority": False,
            "candidate_only": True,
            "current_intent_ref": "intent:founder:on-demand-reconstruction",
            "missing_capability_id": "capability:missing-delta",
            "receiver_id": "receiver:local-model",
            "receiver_version": "2.3",
            "current_available_capabilities": ["capability:8dadi-index"],
            "task_id": "task:minimal-cloud-fragment",
            "missing_schema_version": "1",
            "evidence": ["evidence:local-gap"],
            "missing_lookup_resource": "index:capability:missing-delta",
            "missing_verification_capability": "verify:exact-reconstruction",
            "packet_sha256": "b" * 64,
        }
        packet = build_total_field_capability_requirement_packet(
            report,
            target_base_state={"state_ref": "local:base"},
            reusable_capability_refs=["capability:8dadi-index"],
            created_at="2026-09-03T00:00:00Z",
        )
        completion = packet["D6_GENERATIVE_COMPLETION"]
        self.assertEqual(
            completion["cloud_input_scope"],
            "MINIMUM_TASK_REQUIRED_PARTIAL_INFORMATION",
        )
        self.assertEqual(completion["local_reconstruction"], "8DADI_INDEX_LINEAGE_RULE_BOUND")
        self.assertFalse(completion["full_context_transmission"])
        self.assertTrue(completion["return_to_total_field_before_effect"])

    def test_v_shape_vram_projection_keeps_hits_and_releases_only_unhit_residency(self):
        packet = build_v_shape_vram_prediction_projection(
            intent_ref="intent:founder:vram-v-shape",
            current_logical_time=8,
            receiver_id="gpu:msi:rtx4070",
            item_observations=[
                {
                    "object_id": "tensor:hit",
                    "coordinate": "models/tensor-hit.bin",
                    "grid_cell_ref": "vram-grid:t8:hit:tensor-hit",
                    "adi_locator_ref": "adi:object:tensor-hit",
                    "state_sha256": "c" * 64,
                    "last_hit_logical_time": 8,
                    "predicted_hit": True,
                    "observed_hit_state": "HIT",
                    "vram_bytes": 4096,
                    "storage_state_ref": "storage:tensor-hit",
                    "reconstruction_rule_ref": "reconstruct:tensor-hit",
                    "evidence_ref": "evidence:tensor-hit",
                },
                {
                    "object_id": "tensor:unhit",
                    "coordinate": "models/tensor-unhit.bin",
                    "grid_cell_ref": "vram-grid:t8:unhit:tensor-unhit",
                    "adi_locator_ref": "adi:object:tensor-unhit",
                    "state_sha256": "d" * 64,
                    "last_hit_logical_time": 6,
                    "predicted_hit": True,
                    "observed_hit_state": "MISS",
                    "vram_bytes": 8192,
                    "storage_state_ref": "storage:tensor-unhit",
                    "reconstruction_rule_ref": "reconstruct:tensor-unhit",
                    "evidence_ref": "evidence:tensor-unhit",
                },
                {
                    "object_id": "tensor:false-negative",
                    "coordinate": "models/tensor-false-negative.bin",
                    "grid_cell_ref": "vram-grid:t8:hit:tensor-false-negative",
                    "adi_locator_ref": "adi:object:tensor-false-negative",
                    "state_sha256": "e" * 64,
                    "last_hit_logical_time": 7,
                    "predicted_hit": False,
                    "observed_hit_state": "HIT",
                    "vram_bytes": 2048,
                    "storage_state_ref": "storage:tensor-false-negative",
                    "reconstruction_rule_ref": "reconstruct:tensor-false-negative",
                    "evidence_ref": "evidence:tensor-false-negative",
                },
            ],
        )
        self.assertEqual(packet["D2_STATE"]["retained_vram_bytes"], 6144)
        self.assertEqual(packet["D2_STATE"]["released_vram_bytes"], 8192)
        hit_by_id = {
            item["object_id"]: item
            for item in packet["D5_EXECUTION_POLICY"]["hit_axis"]
        }
        self.assertEqual(hit_by_id["tensor:hit"]["vram_action"], "KEEP_VRAM_RESIDENT")
        self.assertEqual(
            hit_by_id["tensor:false-negative"]["vram_action"],
            "8DADI_MINIMUM_DELTA_RECONSTRUCT_THEN_KEEP",
        )
        unhit = packet["D5_EXECUTION_POLICY"]["unhit_routes"][0]
        self.assertEqual(unhit["vram_action"], "EARLY_RELEASE_VRAM_RESIDENCY_ONLY")
        self.assertEqual(unhit["prediction_outcome"], "PREDICTION_MISS_EARLY_RELEASE")
        self.assertEqual(unhit["future_action"], "8DADI_RECONSTRUCT_ON_DEMAND")
        self.assertEqual(unhit["source_data_effect"], "NONE")
        self.assertEqual(packet["D3_COORDINATE"]["state_cell_model"], "DISCRETE_GRID")
        self.assertEqual(
            packet["D3_COORDINATE"]["grid_assignment"],
            "INPUT_8DADI_COORDINATE_ONLY",
        )
        self.assertEqual(
            packet["D3_COORDINATE"]["locator"],
            "ADI_EXACT_OBJECT_ID_TO_CURRENT_MEMORY_TIER",
        )
        self.assertFalse(packet["D3_COORDINATE"]["workspace_search"])
        self.assertFalse(packet["D5_EXECUTION_POLICY"]["persistent_source_destruction"])
        self.assertFalse(packet["D6_GENERATIVE_TRANSMISSION"]["full_state_transfer"])
        self.assertEqual(
            packet["D6_GENERATIVE_TRANSMISSION"]["transmission_unit"],
            "MINIMUM_GENERATIVE_STATE_PROJECTION_PACKET",
        )
        self.assertTrue(
            packet["D6_GENERATIVE_TRANSMISSION"]
            ["transmission_reconstructs_state_without_payload_cache"]
        )
        self.assertTrue(
            packet["D6_GENERATIVE_TRANSMISSION"]["receiver_reconstructs_with_local_resources"]
        )
        self.assertFalse(
            packet["D6_GENERATIVE_TRANSMISSION"]["cpu_cache_transferable_to_gpu"]
        )
        self.assertTrue(packet["D6_GENERATIVE_TRANSMISSION"]["host_ram_staging_allowed"])
        self.assertEqual(
            packet["D6_GENERATIVE_TRANSMISSION"]["dual_storage_mapping"],
            "ADI_LOCAL_BASE_CLOUD_GENERATIVE_COMPLETION",
        )
        self.assertFalse(packet["D6_GENERATIVE_TRANSMISSION"]["cloud_direct_to_vram"])
        self.assertFalse(packet["D8_ENVELOPE_AUTHORITY"]["operation_authority"])
        self.assertFalse(packet["D8_ENVELOPE_AUTHORITY"]["model_may_expand_context"])
        self.assertEqual(
            packet["D1_INTENT"]["context_control"],
            "CURRENT_INTENT_ONLY",
        )
        self.assertFalse(packet["D4_EVIDENCE"]["recency_or_frequency_authority"])
        self.assertFalse(packet["numeric_distance_model_used"])

    def test_dynamic_context_exposes_vram_prediction_contract(self):
        packet = build_dynamic_context(
            "以 8DADI 調度 VRAM 並按需重建",
            root=ROOT,
            max_items=4,
            identity_class="founder",
            generated_at="2026-09-03T00:00:00+00:00",
        )
        contract = packet["vram_prediction_workflow_contract"]
        self.assertEqual(contract["vertex"], "CURRENT_LOGICAL_TIME")
        self.assertEqual(contract["opening_direction"], "FUTURE")
        self.assertEqual(contract["state_cell_model"], "DISCRETE_GRID")
        self.assertEqual(contract["locator"], "ADI_EXACT_OBJECT_ID_TO_CURRENT_MEMORY_TIER")
        self.assertFalse(contract["workspace_search"])
        self.assertEqual(
            contract["context_control"],
            "CURRENT_FOUNDER_INTENT_TO_8DADI_DEPENDENCY_CLOSURE",
        )
        self.assertFalse(contract["model_may_expand_context"])
        self.assertEqual(contract["retrieval"], "8DADI_ON_DEMAND_RECONSTRUCTION")
        self.assertEqual(contract["cloud_input"], "MINIMUM_PARTIAL_INFORMATION_ONLY")
        self.assertTrue(contract["transmission_compensates_cache"])
        self.assertFalse(contract["cpu_cache_transferable_to_gpu"])
        self.assertTrue(contract["host_ram_staging_allowed"])
        self.assertEqual(
            contract["dual_storage_mapping"]["mode"],
            "ADI_LOGICAL_GENERATIVE_STATE_MAPPING",
        )
        self.assertEqual(
            contract["dual_storage_mapping"]["local"],
            "PRIMARY_RECONSTRUCTION_BASE",
        )
        self.assertEqual(
            contract["generative_transmission_definition"],
            "TRANSMIT_MINIMUM_STATE_GENERATOR_NOT_MATERIALIZED_TENSOR",
        )
        self.assertFalse(contract["dual_storage_mapping"]["cloud_direct_to_vram"])
        self.assertFalse(contract["source_data_destruction"])
        self.assertFalse(contract["operation_authority"])

    def test_dynamic_context_regions_are_intent_controlled_inside_one_envelope(self):
        packet = build_dynamic_context(
            "依最新意圖劃分上下文區域",
            root=ROOT,
            max_items=4,
            identity_class="founder",
            generated_at="2026-09-03T00:00:00+00:00",
        )
        contract = packet["context_region_contract"]
        self.assertTrue(contract["single_total_field_envelope"])
        self.assertEqual(
            contract["selection"],
            "CURRENT_FOUNDER_INTENT_TO_8DADI_EXACT_DEPENDENCY_CLOSURE",
        )
        self.assertEqual(
            set(contract["regions"]),
            {
                "CORE_AUTHORITY",
                "CURRENT_INTENT_TASK",
                "ADI_RETRIEVED_DEPENDENCY",
                "GENERATIVE_DELTA",
                "EXCLUDED_D4_REFERENCES",
                "TRANSIENT_WORKING_SET",
            },
        )
        self.assertFalse(contract["semantic_similarity_used"])
        self.assertFalse(contract["region_may_change_authority"])
        self.assertFalse(contract["model_may_move_item_between_regions"])
        regions = packet["context_regions"]
        self.assertEqual(set(regions), set(contract["regions"]))
        self.assertFalse(regions["CORE_AUTHORITY"]["payloads_inlined"])
        self.assertFalse(regions["ADI_RETRIEVED_DEPENDENCY"]["payloads_inlined"])
        self.assertEqual(regions["TRANSIENT_WORKING_SET"]["lifecycle"], "TTL_VOLATILE")
        layout = packet["context_layout_contract"]
        header = layout["zones"]["HEADER_IMMUTABLE"]
        dynamic_window = layout["zones"]["DYNAMIC_INTENT_WINDOW"]
        personalization = layout["zones"]["PERSONALIZATION_SETTINGS"]
        self.assertFalse(header["mutable"])
        self.assertTrue(dynamic_window["rebuilt_per_intent"])
        self.assertFalse(personalization["may_override_header"])
        self.assertFalse(personalization["may_change_d8_authority"])
        self.assertFalse(personalization["may_change_canonical"])
        self.assertFalse(layout["model_may_rewrite_layout"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
