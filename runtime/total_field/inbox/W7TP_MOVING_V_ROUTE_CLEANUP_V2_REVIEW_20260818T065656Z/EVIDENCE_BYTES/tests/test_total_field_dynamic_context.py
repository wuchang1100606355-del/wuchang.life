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
            "status": "historical_snapshot",
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
            "status": "historical_snapshot",
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
        self.assertEqual(packet["retrieval_state"], "MATCHED_CURRENT_AND_SNAPSHOT_EVIDENCE")
        paths = [item["relative_path"] for item in packet["context_items"]]
        self.assertIn("schemas/voice_browser_runtime.schema.json", paths)
        schema_item = next(item for item in packet["context_items"] if item["relative_path"].startswith("schemas/"))
        self.assertEqual(schema_item["evidence_class"], "CONTRACT_DEFINITION_NOT_RUNTIME_PROOF")
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
        self.assertIn("schemas/voice_browser_runtime.schema.json", paths)

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
        self.assertGreaterEqual(packet["sensitive_files_omitted"], 1)

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
