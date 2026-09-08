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
    build_source_preserving_model_orchestration_packet,
    build_sovereign_ai_member_seat_admission,
    build_total_field_capability_requirement_packet,
    build_v_shape_vram_prediction_projection,
    build_dynamic_context,
    canonical_sha256,
)
from tools.developer_memory_builder import (  # noqa: E402
    persist_founder_target_lock,
    persist_model_source_context,
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
        production_contract_path = (
            ROOT / "configs/total_field/w7tp_8dadi_d6_contract_v2_3.json"
        )
        write_text(
            self.root / "configs/total_field/w7tp_8dadi_d6_contract_v2_3.json",
            production_contract_path.read_text(encoding="utf-8"),
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

    @staticmethod
    def _model_source_export(
        *,
        account: str,
        statement: str = "由總場提供最小上下文，讓小模型執行受限工作。",
        limitations: list[str] | None = None,
        digest: str | None = None,
    ) -> dict:
        value = {
            "schema_version": "1.0.0",
            "export_id": f"export-{account}",
            "source_account": {"source_account_coordinate": account},
            "source_threads": [{"thread_id": f"thread-{account}"}],
            "access_limitations": limitations or [],
            "founder_statements": [
                {
                    "speaker": "USER",
                    "verbatim_user_statement": statement,
                    "normalized_claim": "總場提供最小上下文讓小模型執行受限工作",
                    "thread_title": "模型協作",
                    "thread_id_or_url": f"https://chatgpt.example/c/{account}?secret=redacted",
                    "timestamp": "2026-09-07T00:00:00+08:00",
                    "status": "OBSERVED",
                    "superseded_by": None,
                }
            ],
            "skills_and_capabilities": [
                {
                    "skill_or_capability_name": "來源保留式模型協作",
                    "artifact_or_exact_coordinate": "skill://external/model-source",
                    "trigger": ["模型協作"],
                    "inputs": ["來源匯出"],
                    "outputs": ["候選來源封套"],
                    "tool_binding": "external:unverified",
                    "side_effects": False,
                    "failure_modes": ["來源不足"],
                    "acceptance_conditions": ["來源保留"],
                    "example_cases": ["跨帳號對話整理"],
                    "observed_status": "DOCUMENTED_ONLY",
                    "authority_boundary": ["NO_D8"],
                }
            ],
            "conflicts": [],
            "authority_boundary": [
                "AI_IS_NOT_AUTHORITY",
                "CHAT_MEMORY_IS_D4_EVIDENCE_ONLY",
                "SOURCE_ACCOUNT_REMAINS_SEPARATE",
                "CANDIDATE_IS_NOT_CANONICAL",
                "NO_EXTERNAL_EFFECT",
                "TOTAL_FIELD_REOBSERVATION_REQUIRED",
            ],
        }
        if digest is not None:
            value["source_digest"] = {"algorithm": "SHA-256", "value": digest}
        return value

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

    def test_model_source_request_is_candidate_only_and_not_d6(self):
        packet = build_source_preserving_model_orchestration_packet(
            mode="PREPARE_SOURCE_REQUEST",
            task_scope="本機上下文與小模型雲端協作",
            current_founder_intent_ref="founder_intent_ref:current",
            source_account_coordinate="account_ref:work",
            generated_at="2026-09-07T00:00:00+00:00",
        )
        self.assertEqual(packet["state"], "MODEL_SOURCE_REQUEST_READY")
        self.assertEqual(
            packet["D6_GENERATIVE_TRANSMISSION"]["classification"],
            "NOT_D6_MODEL_SOURCE_SOLICITATION",
        )
        self.assertFalse(packet["D8_ENVELOPE_AUTHORITY"]["operation_authority"])
        self.assertIn("輸出單一可解析 UTF-8 JSON", packet["D4_EVIDENCE"]["prompt_zh_TW"])

    def test_model_source_assimilation_preserves_accounts_exact_claims_and_skills(self):
        packet = build_source_preserving_model_orchestration_packet(
            mode="ASSIMILATE_SOURCE_EXPORTS",
            task_scope="本機上下文與小模型雲端協作",
            current_founder_intent_ref="founder_intent_ref:current",
            source_exports=[
                self._model_source_export(account="account-a"),
                self._model_source_export(account="account-b"),
            ],
            generated_at="2026-09-07T00:00:00+00:00",
        )
        self.assertEqual(packet["state"], "SOURCE_PRESERVING_MODEL_ORCHESTRATION_CANDIDATE_READY")
        bindings = packet["D3_COORDINATE"]["source_bindings"]
        self.assertEqual(
            {item["source_account_coordinate"] for item in bindings},
            {"account-a", "account-b"},
        )
        self.assertFalse(packet["D3_COORDINATE"]["source_account_identity_merge"])
        claims = packet["D4_EVIDENCE"]["exact_claim_groups"]
        self.assertEqual(len(claims), 1)
        self.assertEqual(len(claims[0]["sources"]), 2)
        self.assertIn("verbatim_user_statement", claims[0]["sources"][0])
        self.assertNotIn("?secret=", claims[0]["sources"][0]["thread_id_or_url"])
        capabilities = packet["D4_EVIDENCE"]["documented_capability_groups"]
        self.assertEqual(len(capabilities), 1)
        self.assertFalse(capabilities[0]["skill_registration_eligible"])
        self.assertIn("example_cases", capabilities[0]["sources"][0]["capability_contract"])
        self.assertFalse(packet["D5_EXECUTION_POLICY"]["semantic_similarity_used"])
        self.assertFalse(packet["D5_EXECUTION_POLICY"]["majority_vote_used"])
        self.assertEqual(
            packet["D5_EXECUTION_POLICY"]["controller"],
            "TOTAL_FIELD_USING_8D_ADI",
        )
        self.assertFalse(packet["D8_ENVELOPE_AUTHORITY"]["model_authority"])

    def test_model_source_digest_conflict_is_retained(self):
        packet = build_source_preserving_model_orchestration_packet(
            mode="ASSIMILATE_SOURCE_EXPORTS",
            task_scope="來源摘要驗證",
            current_founder_intent_ref="founder_intent_ref:current",
            source_exports=[
                self._model_source_export(account="account-a", digest="0" * 64)
            ],
            generated_at="2026-09-07T00:00:00+00:00",
        )
        conflicts = packet["D7_RISK_QUARANTINE"]["conflicts"]
        self.assertTrue(
            any(item["type"] == "SOURCE_DECLARED_DIGEST_MISMATCH" for item in conflicts)
        )
        self.assertEqual(len(packet["D4_EVIDENCE"]["exact_claim_groups"]), 1)

    def test_model_source_secret_holds_without_retention(self):
        source = self._model_source_export(account="account-a")
        source["access_token"] = "abcdefghijklmnop123456"
        packet = build_source_preserving_model_orchestration_packet(
            mode="ASSIMILATE_SOURCE_EXPORTS",
            task_scope="來源摘要驗證",
            current_founder_intent_ref="founder_intent_ref:current",
            source_exports=[source],
        )
        self.assertEqual(packet["state"], "HOLD_MODEL_SOURCE_SECRET_OR_MEMBER_PLAINTEXT")
        self.assertFalse(packet["source_payload_retained"])
        self.assertFalse(packet["D8_ENVELOPE_AUTHORITY"]["operation_authority"])

    def test_mcp_lists_and_calls_model_source_orchestration(self):
        server = TotalFieldContextMcpServer(self.root)
        listed = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        names = [item["name"] for item in listed["result"]["tools"]]
        self.assertIn("orchestrate_model_source_context", names)
        called = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "orchestrate_model_source_context",
                    "arguments": {
                        "mode": "ASSIMILATE_SOURCE_EXPORTS",
                        "task_scope": "小模型雲端協作",
                        "current_founder_intent_ref": "founder_intent_ref:current",
                        "source_exports": [self._model_source_export(account="account-a")],
                    },
                },
            }
        )
        packet = json.loads(called["result"]["content"][0]["text"])
        self.assertEqual(packet["schema_id"], "W7TP_8DADI_MODEL_SOURCE_ORCHESTRATION_V1")
        self.assertFalse(called["result"]["isError"])

    def test_model_source_context_persists_idempotently_in_existing_8dadi_index(self):
        export_path = self.root / "incoming/source-export.json"
        write_json(export_path, self._model_source_export(account="account-a"))
        arguments = {
            "root": self.root,
            "export_paths": [export_path],
            "task_scope": "本機上下文與小模型雲端協作",
            "current_founder_intent_ref": "founder_intent_ref:current",
        }
        first = persist_model_source_context(**arguments)
        second = persist_model_source_context(**arguments)
        self.assertEqual(first["state"], "PASS_MODEL_SOURCE_CONTEXT_INDEXED")
        self.assertEqual(second["state"], "PASS_MODEL_SOURCE_CONTEXT_ALREADY_INDEXED")
        self.assertEqual(second["files_changed"], [])
        self.assertFalse(first["raw_exports_copied"])
        self.assertFalse(first["current_founder_intent_changed"])
        self.assertFalse(first["d8_granted"])
        packet = build_dynamic_context("小模型雲端協作", root=self.root, max_items=8)
        self.assertEqual(packet["state"], "TOTAL_FIELD_DYNAMIC_CONTEXT_READY")
        paths = [item["relative_path"] for item in packet["context_items"]]
        self.assertIn(first["record_ref"], paths)

    def test_founder_target_lock_supersedes_old_intent_and_replays_new_goal(self):
        old_source_relative = Path(
            "runtime/total_field/intake/old-founder/FOUNDER_INTENT.json"
        )
        old_source = {
            "schema_id": "W7TP_8DADI_FOUNDER_INTENT_REENTRY_V1",
            "reentry_id": "old-founder",
            "created_at": "2026-09-03T00:00:00+00:00",
            "source_class": "FOUNDER_DECLARATION",
            "state": "ACTIVE_FOUNDER_INTENT_DECLARATION_REQUIRES_LIVE_REOBSERVATION",
            "D1": {"intent": "舊目標"},
            "D2": {"target_state": "OLD"},
            "D3": {
                "system_nodes": [
                    {"node": "taiji01", "roles": ["server"], "status": "OLD_OBSERVATION"}
                ]
            },
            "D4": {"latest_observations": {"taiji01": "OLD"}},
            "D5": {"sequence": ["INTENT", "REOBSERVATION"]},
            "D6": {"generative_transmission": "old description"},
            "D7": {"pollution_guards": ["NO_LEGACY_TARGET_IMPORT"]},
            "D8": {"packet_self_authority": False},
            "natural_language_execution_contract": {"input": "founder natural language"},
            "network_policy": {"primary": "LAN", "fallback": "VPN"},
            "legacy_boundary": {"version_2_1": "HISTORICAL_D4_ONLY"},
            "authority_boundary": {
                "founder_intent_is_target_source": True,
                "this_packet_grants_execution_authority": False,
            },
        }
        old_source_sha = write_json(self.root / old_source_relative, old_source)
        old_record_relative = Path("records/governance/human/old-founder.json")
        write_json(
            self.root / "runtime/developer_memory" / old_record_relative,
            {
                "schema_version": "1.0",
                "memory_id": old_source_sha,
                "category": "governance/human",
                "status": "active",
                "trust": "founder_declared",
                "source": {
                    "path": old_source_relative.as_posix(),
                    "sha256": old_source_sha,
                    "size_bytes": (self.root / old_source_relative).stat().st_size,
                },
                "payload": {
                    "type": "W7TP_8DADI_FOUNDER_INTENT_REENTRY",
                    "intent": "舊目標",
                },
            },
        )
        index_path = self.root / "runtime/developer_memory/indexes/memory_index.jsonl"
        with index_path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "memory_id": old_source_sha,
                        "category": "governance/human",
                        "status": "active",
                        "trust": "founder_declared",
                        "record_path": old_record_relative.as_posix(),
                        "source_path": old_source_relative.as_posix(),
                        "source_sha256": old_source_sha,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

        arguments = {
            "root": self.root,
            "primary_goal_zh_tw": (
                "以上品聊國咖啡館服務員影音 AI 小J參加中華電信大賽，"
                "向世人展示 8DADI 能力並取得成績與輿論目光。"
            ),
            "product_name_zh_tw": "上品聊國咖啡館服務員影音 AI 小J",
            "competition_name_zh_tw": "中華電信大賽",
            "created_at": "2026-09-07T00:00:00+00:00",
        }
        first = persist_founder_target_lock(**arguments)
        second = persist_founder_target_lock(**arguments)
        self.assertEqual(first["state"], "PASS_FOUNDER_TARGET_LOCK_INDEXED")
        self.assertEqual(second["state"], "PASS_FOUNDER_TARGET_ALREADY_LOCKED")
        self.assertEqual(second["files_changed"], [])

        latest = {}
        for line in index_path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            latest[row["memory_id"]] = row
        self.assertEqual(latest[old_source_sha]["status"], "superseded")
        self.assertEqual(
            latest[first["active_founder_intent_sha256"]]["status"], "active"
        )
        packet = build_dynamic_context(
            "中華電信 上品聊國 影音 AI 小J 8DADI",
            root=self.root,
            identity_class="founder",
            generated_at="2026-09-07T00:01:00+00:00",
        )
        projection = packet["founder_intent_projection"]
        self.assertEqual(packet["state"], "TOTAL_FIELD_DYNAMIC_CONTEXT_READY")
        self.assertIn("中華電信大賽", projection["D1"]["primary_goal_zh_TW"])
        self.assertTrue(projection["target_lock"]["locked"])
        self.assertTrue(projection["optimization_policy"]["purpose_transfer_forbidden"])
        self.assertEqual(
            projection["high_cost_work_policy"]["current_scope"],
            "LOCATE_COMPARE_AND_RECOMMEND_ONLY",
        )
        self.assertEqual(
            projection["D3"]["system_nodes"][0]["status"],
            "PRIOR_SOURCE_REFERENCE_REQUIRES_LIVE_REOBSERVATION",
        )
        self.assertFalse(projection["D8"]["this_target_lock_grants_external_effect"])

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
        self.assertEqual(
            route["tool_contract_validation"]["allowed_mcp_tools"],
            ["get_total_field_dynamic_context", "orchestrate_model_source_context"],
        )
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

    def test_workspace_adi_five_axis_annotation_preserves_8d_and_authority_boundary(self):
        contract_path = ROOT / "configs/total_field/w7tp_8dadi_d6_contract_v2_3.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        annotation = contract["adi_five_axis_coordinate_annotation"]

        self.assertEqual(
            list(contract["dimensions"]),
            ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8"],
        )
        self.assertEqual(
            [item["axis"] for item in annotation["axes"]],
            ["C1_DOMAIN", "C2_ENTITY", "C3_TOPOLOGY", "C4_TIME_STATE", "C5_AUTHORITY"],
        )
        self.assertEqual(
            annotation["coordinate_kind"],
            "DISCRETE_INDEXED_FIVE_AXIS_REFERENCE",
        )
        self.assertEqual(
            annotation["odoo_w5c_projection"]["field_mapping"],
            {
                "w5c_domain": "C1_DOMAIN",
                "w5c_entity": "C2_ENTITY",
                "w5c_topology": "C3_TOPOLOGY",
                "w5c_time_state": "C4_TIME_STATE",
                "w5c_authority": "C5_AUTHORITY",
            },
        )
        self.assertEqual(
            annotation["odoo_w5c_projection"]["w5c_code_role"],
            "COMPOSITE_LOOKUP_KEY_NOT_A_SIXTH_AXIS",
        )
        self.assertFalse(
            annotation["odoo_w5c_projection"]["projection_may_define_canonical_or_d8"]
        )
        self.assertIn("不生成浮點距離", annotation["time_space_quantization_boundary"])
        self.assertIn("離散狀態整數運算", annotation["founder_intent_addendum_zh_TW"])
        lookup = annotation["discrete_integer_lookup_math"]
        self.assertEqual(
            lookup["state_representation"],
            "VERSIONED_NAMESPACE_BOUND_DISCRETE_INTEGER_CODES",
        )
        self.assertIn("VERSIONED_TABLE_LOOKUP", lookup["operations"])
        self.assertIn("INTEGER_NAMESPACE", lookup["lookup_table_binding_requires"])
        self.assertFalse(lookup["floating_point_required_for_known_discrete_lookup"])
        self.assertFalse(lookup["semantic_similarity_or_llm_guess_used_for_coordinate_value"])
        self.assertFalse(lookup["integer_lookup_alone_guarantees_correct_external_effect"])
        self.assertTrue(lookup["reconstruction_and_external_effect_still_require_reobservation"])
        self.assertFalse(contract["file_self_establishes_canonical_or_d8"])

    def test_workspace_adaptive_dimension_projection_cannot_reduce_effect_authority(self):
        contract_path = ROOT / "configs/total_field/w7tp_8dadi_d6_contract_v2_3.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        projection = contract["adaptive_internal_dimension_projection"]

        self.assertEqual(projection["full_observation_envelope"], "D1_TO_D8")
        self.assertEqual(
            projection["selector"],
            "ADI_FIVE_AXIS_AFFECTED_COORDINATE_CLOSURE",
        )
        self.assertEqual(
            projection["internal_dimension_count"],
            "TASK_DEPENDENT_MINIMUM_SUFFICIENT_K_NOT_A_FIXED_LOWER_DIMENSION",
        )
        self.assertFalse(projection["projection_is_canonical_redefinition"])
        self.assertFalse(projection["projection_may_erase_source_lineage_or_authority"])
        self.assertEqual(
            projection["external_effect_gate_must_resolve"],
            [
                "D1_INTENT_REFERENCE",
                "D5_EXECUTION_POLICY",
                "D7_RISK_BOUNDARY",
                "D8_ENVELOPE_REFERENCE",
            ],
        )
        self.assertEqual(
            projection["performance_claim"],
            "CANDIDATE_REQUIRES_CONTROLLED_BASELINE_MEASUREMENT",
        )

    def test_total_field_is_non_custodial_and_association_custodies_personal_information(self):
        contract_path = ROOT / "configs/total_field/w7tp_8dadi_d6_contract_v2_3.json"
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        model = contract["total_field_capability_and_field_data_custody_model"]
        device_base = contract["registered_device_generative_base"]
        orchestration = contract["scene_agnostic_hardware_orchestration"]
        resource_field = contract["distributed_resource_field"]

        self.assertTrue(model["single_total_field_capability_plane"])
        self.assertFalse(model["total_field_persistent_raw_data_custody"])
        self.assertEqual(device_base["applies_to"], "EACH_REGISTERED_AND_ADMITTED_DEVICE")
        self.assertIn("IDENTITY_PACKET_REFERENCE", device_base["base_is_specific_to"])
        self.assertIn("AUTHORITY_SCOPE", device_base["base_is_specific_to"])
        self.assertFalse(device_base["identical_base_across_devices_required"])
        self.assertIn("COMMON_SCHEMA", device_base["base_may_contain"])
        self.assertIn("PERSON_SPECIFIC_PLAINTEXT", device_base["base_must_not_contain"])
        self.assertIn(
            "ASSOCIATION_PERSONAL_INFORMATION_MASTER",
            device_base["capability_compartments"]["cafe_general_member"]
            ["may_not_reconstruct"],
        )
        self.assertIn(
            "MATCHING_IDENTITY_SEAT_DEVICE_BASE",
            device_base["capability_compartments"]
            ["property_committee_approved_caller"]["may_reconstruct_only_with"],
        )
        self.assertEqual(
            device_base["wrong_or_missing_base_result"],
            "OPAQUE_UNRECONSTRUCTABLE_PACKET_WITH_NO_PARTIAL_PERSONAL_INFORMATION_OUTPUT",
        )
        self.assertEqual(
            device_base["receiver_output"],
            "LOCAL_RECONSTRUCTED_EXACT_FILE_OR_PURPOSE_BOUND_CONTROLLED_VIEW",
        )
        self.assertTrue(device_base["design_requirement_does_not_prove_live_base_installed"])
        user_scene = orchestration["personal_browser_ai_user_scene"]
        self.assertEqual(
            user_scene["classification"],
            "PERSONAL_USER_SCENE_BROWSER_PROJECTION",
        )
        self.assertIn(
            "CLOUD_AND_LOCAL_MODEL_ORGANS",
            user_scene["application_scene_composition"],
        )
        self.assertTrue(user_scene["cloud_and_local_models_are_replaceable_organs"])
        self.assertTrue(user_scene["composition_forms_one_application_scene"])
        self.assertTrue(user_scene["application_scene_is_not_parallel_8dadi_or_total_field"])
        self.assertTrue(user_scene["uses_existing_total_field_and_8dadi_core"])
        self.assertTrue(user_scene["one_person_session_for_concurrent_scene_seats"])
        self.assertFalse(user_scene["manual_provider_account_switch_required"])
        self.assertTrue(user_scene["active_scene_and_role_must_be_visible"])
        self.assertIn("8DADI_EXACT", user_scene["scene_and_capability_resolution"])
        self.assertIn("DISTRIBUTED_RESOURCE_FIELD", user_scene["resource_dispatch"])
        self.assertFalse(user_scene["browser_may_directly_control_nodes_or_hardware"])
        self.assertEqual(
            resource_field["primary_human_entrypoint"],
            "PERSONAL_BROWSER_AI_USER_SCENE",
        )
        self.assertTrue(resource_field["entrypoint_does_not_own_or_merge_distributed_resources"])
        self.assertTrue(
            resource_field[
                "user_never_selects_physical_node_or_model_account_when_intent_and_scope_are_unambiguous"
            ]
        )
        self.assertIn("CLOUD_DRIVE_STORAGE", resource_field["logical_pool_includes"])
        unification = resource_field["8dadi_logical_unification"]
        self.assertIn("CONTAINER", unification["unified_coordinate_classes"])
        self.assertIn("DATABASE", unification["unified_coordinate_classes"])
        self.assertIn("CLOUD_DRIVE_ITEM", unification["unified_coordinate_classes"])
        self.assertTrue(unification["does_not_physically_merge_memory_storage_database_or_accounts"])
        self.assertTrue(unification["does_not_merge_scene_data_identity_seats_or_authority"])
        self.assertTrue(unification["does_not_copy_every_capability_to_every_node"])
        cloud_drive = resource_field["cloud_drive_capability"]
        self.assertEqual(
            cloud_drive["classification"],
            "EXTERNAL_CLOUD_STORAGE_MATERIAL_AND_INDEX_CAPABILITY_ORGAN",
        )
        self.assertEqual(cloud_drive["founder_declared_organization_shared_drive_count"], 3)
        self.assertEqual(
            cloud_drive["live_shared_drive_identifiers_and_permissions"],
            "NOT_YET_OBSERVED",
        )
        self.assertFalse(cloud_drive["whole_drive_sync_or_replication_by_default"])
        self.assertFalse(cloud_drive["ordinary_drive_UPLOAD_DOWNLOAD_OR_FILE_COPY_IS_D6"])
        self.assertFalse(cloud_drive["credentials_or_raw_personal_information_in_model_context"])
        self.assertIn("ADI_FIVE_AXIS_COORDINATE", model["field_registration_requires"])
        self.assertIn("D8_SCOPE_REFERENCE", model["field_registration_requires"])
        self.assertEqual(
            model["authority_rule"],
            "EACH_FIELD_CUSTODIES_ITS_NON_PERSONAL_BUSINESS_DATA_WHILE_ASSOCIATION_FIELD_CUSTODIES_PERSONAL_INFORMATION_MASTER_AND_TOTAL_FIELD_MAY_NOT_CONVERT_TECHNICAL_CONTROL_INTO_DATA_OWNERSHIP",
        )
        self.assertEqual(
            model["odoo_role"],
            "PRIMARY_FIELD_BUSINESS_APPLICATION_AND_BROWSER_PROJECTION_NOT_TOTAL_FIELD_AUTHORITY_OR_DATA_OWNER",
        )
        association = model["five_chang_association_primary_field"]
        self.assertEqual(
            association["scene_reality_classification"],
            "FOUNDER_DECLARED_CURRENT_REAL_WORLD_SCENE_PENDING_LIVE_EVIDENCE_BINDING",
        )
        self.assertTrue(association["mandatory"])
        self.assertIn(
            "WORK_POINT_6_SHALL_ESTABLISH_COMMUNITY_BASIC_DATA",
            association["current_official_work_point_support"],
        )
        self.assertEqual(
            association["hydrology_coordinate_rule"],
            "COMMUNITY_HYDROLOGY_IS_INDEXED_UNDER_GEOGRAPHY_AND_ENVIRONMENT_WITH_SOURCE_LINEAGE",
        )
        custody = model["personal_information_field_custody"]
        self.assertEqual(
            custody["total_field_role"],
            "ORCHESTRATE_MASKED_PROJECTION_NO_PERSONAL_DATA_CUSTODY",
        )
        self.assertEqual(
            custody["personal_information_master_custodian"],
            "FIVE_CHANG_ASSOCIATION_FIELD",
        )
        self.assertIn(
            "CROSS_SCENE_PERSONAL_DATA_ACCESS_AUDIT",
            custody["association_custody_information_classes"],
        )
        self.assertFalse(custody["total_field_may_persist_member_plaintext"])
        self.assertFalse(custody["other_scene_may_create_personal_information_master"])
        self.assertTrue(
            custody["lawful_duty_access_must_not_be_blocked_by_extra_technical_approval"]
        )

        committee = model["property_management_committee_field"]
        self.assertEqual(
            committee["scene_reality_classification"],
            "DEMONSTRATION_SCENE_NOT_CURRENT_REAL_WORLD_OPERATING_FIELD",
        )
        self.assertTrue(committee["demonstration_only"])
        self.assertFalse(committee["live_real_world_legal_or_personal_data_authority"])
        self.assertEqual(committee["demo_data_rule"], "SYNTHETIC_OR_DEIDENTIFIED_DATA_ONLY")
        self.assertTrue(committee["mandatory"])
        self.assertTrue(committee["legal_responsibility_remains_with_committee"])
        self.assertTrue(
            committee[
                "personal_data_use_is_mandatory_when_irreducibly_required_for_legal_duty"
            ]
        )
        self.assertEqual(
            committee["personal_information_master_custodian"],
            "FIVE_CHANG_ASSOCIATION_FIELD",
        )
        self.assertIn(
            "APARTMENT_BUILDING_MANAGEMENT_ACT_ARTICLE_20",
            committee["statutory_coordinates"],
        )
        self.assertIn("ARTICLE_35", committee["statutory_coordinates"])
        self.assertFalse(committee["committee_scene_may_proxy_or_receive_personal_payload"])
        self.assertEqual(
            committee["delivery_target"],
            "APPROVED_CALLER_REGISTERED_DEVICE_ONLY",
        )

        identity_projection = model["sovereign_identity_packet_scene_projection"]
        self.assertEqual(
            identity_projection["identity_packet_class"],
            "8DADI_SOVEREIGN_PERSON_IDENTITY_PACKET",
        )
        self.assertTrue(identity_projection["one_person_one_sovereign_identity_packet"])
        founder_person = identity_projection["founder_natural_person_identity_root"]
        self.assertEqual(
            founder_person["subject_reference"],
            "FOUNDER_NATURAL_PERSON_SOVEREIGN_IDENTITY_ROOT",
        )
        self.assertEqual(founder_person["system_role"], "NATURAL_PERSON_FOUNDER")
        self.assertEqual(
            founder_person["declared_google_login_binding_reference"],
            "FOUNDER_PERSONAL_GOOGLE_ACCOUNT_O970106_REF",
        )
        self.assertTrue(founder_person["google_account_is_authenticator_not_person_identity"])
        self.assertFalse(founder_person["founder_identity_root_is_organization_or_scene"])
        self.assertIn(
            "FIVE_CHANG_ASSOCIATION_CHAIRPERSON",
            founder_person["linked_current_scene_roles"],
        )
        self.assertIn(
            "SHANGPIN_LIAOGUO_CAFE_OWNER",
            founder_person["linked_current_scene_roles"],
        )
        self.assertEqual(founder_person["live_authenticator_binding_state"], "NOT_YET_OBSERVED")
        self.assertTrue(identity_projection["concurrent_scene_seats_allowed"])
        self.assertTrue(
            identity_projection["single_sovereign_identity_session_for_concurrent_scene_seats"]
        )
        self.assertFalse(
            identity_projection["manual_account_switch_required_for_scene_selection"]
        )
        ai_binding = identity_projection["personal_ai_api_account_binding"]
        self.assertEqual(ai_binding["single_controller"], "EXISTING_TOTAL_FIELD_8DADI")
        self.assertEqual(
            ai_binding["replaceable_unit"],
            "AI_MODEL_COMPUTE_CONNECTOR_NOT_8DADI_INSTANCE",
        )
        self.assertFalse(ai_binding["creates_parallel_8dadi_or_total_field"])
        self.assertFalse(ai_binding["api_account_login_alone_establishes_sovereign_identity"])
        self.assertIn("SOVEREIGN_IDENTITY_PACKET_REFERENCE", ai_binding["binding_requires"])
        self.assertFalse(ai_binding["automatic_email_address_identity_merge"])
        self.assertTrue(
            ai_binding["multiple_person_owned_ai_api_accounts_may_bind_to_one_person_packet"]
        )
        self.assertTrue(ai_binding["provider_credentials_are_opaque_to_models_scenes_and_total_field_context"])
        self.assertTrue(ai_binding["scene_action_still_requires_active_scene_packet"])
        self.assertEqual(
            identity_projection["founder_declared_existing_scene_roles"]
            ["association_chairperson"]["state"],
            "FOUNDER_DECLARED_EXISTING_ROLE_PENDING_LIVE_EVIDENCE_BINDING",
        )
        scene_portfolio = identity_projection["founder_scene_portfolio"]
        self.assertEqual(
            scene_portfolio["current_real_world_scenes"],
            ["FIVE_CHANG_ASSOCIATION", "SHANGPIN_LIAOGUO_CAFE"],
        )
        self.assertEqual(
            scene_portfolio["demonstration_scenes"],
            ["PROPERTY_MANAGEMENT_COMMITTEE"],
        )
        self.assertFalse(
            scene_portfolio[
                "demonstration_scene_may_imply_current_person_role_or_legal_authority"
            ]
        )
        self.assertEqual(
            identity_projection["founder_declared_existing_scene_roles"]
            ["cafe_owner"]["state"],
            "FOUNDER_DECLARED_EXISTING_ROLE_PENDING_LIVE_EVIDENCE_BINDING",
        )
        self.assertIn(
            "WITHOUT_REPERFORMING_ELECTION_APPLICATION_OR_BUSINESS_FORMATION",
            identity_projection["existing_role_admission_rule"],
        )
        self.assertFalse(identity_projection["founder_system_identity_root_is_universal_scene_role"])
        self.assertTrue(identity_projection["founder_scene_action_requires_linked_scene_packet"])
        self.assertIn(
            "SOVEREIGN_IDENTITY_ROOT_REFERENCE",
            identity_projection["scene_packet_must_bind"],
        )
        self.assertFalse(
            identity_projection[
                "system_founder_authority_may_bypass_missing_scene_packet_for_scene_data_or_business_action"
            ]
        )
        self.assertIn(
            "PROPERTY_COMMITTEE_CHAIRPERSON_SEAT",
            identity_projection["scene_seat_examples"],
        )
        self.assertFalse(identity_projection["seat_may_rewrite_person_identity"])
        self.assertFalse(identity_projection["seat_scope_may_leak_to_other_scene"])
        self.assertTrue(
            identity_projection[
                "one_registered_device_may_hold_multiple_isolated_scene_base_compartments"
            ]
        )
        self.assertTrue(
            identity_projection[
                "natural_language_scene_switch_does_not_merge_scene_data_or_authority"
            ]
        )
        self.assertIn("NO_ACCOUNT_RELOGIN", identity_projection["browser_scene_experience"])
        self.assertIn(
            "STEP_UP_REGISTERED_DEVICE_UNLOCK",
            identity_projection["privileged_external_effect_confirmation"],
        )
        self.assertFalse(
            identity_projection[
                "cloud_or_local_model_account_may_define_person_identity_or_scene_seat"
            ]
        )

        chairperson = model["property_committee_chairperson_seat_lifecycle"]
        self.assertEqual(
            chairperson["current_use_classification"],
            "DEMONSTRATION_WORKFLOW_TEMPLATE_NOT_ACTIVE_FOUNDER_SEAT",
        )
        self.assertEqual(
            chairperson["person_identity_continuity"],
            "SAME_8DADI_SOVEREIGN_PERSON_IDENTITY_PACKET",
        )
        self.assertEqual(
            chairperson["seat_issuer"],
            "ELECTED_PROPERTY_MANAGEMENT_COMMITTEE_FIELD",
        )
        self.assertIn("CHAIRPERSON_SEAT_REFERENCE", chairperson["activation_requires"])
        self.assertIn(
            "CHAIRPERSON_ROLE_CAPABILITY_SKILL_REFERENCE",
            chairperson["activation_requires"],
        )
        self.assertIn(
            "CHAIRPERSON_DEVICE_D6_BASE_REFERENCE",
            chairperson["activation_requires"],
        )
        self.assertFalse(chairperson["skill_or_base_alone_grants_authority"])
        self.assertIn("TERM_EXPIRED", chairperson["deactivation_triggers"])
        self.assertIn("GENERAL_MEMBER_IDENTITY_RETAINED", chairperson["deactivation_effect"])
        self.assertEqual(chairperson["live_seat_skill_and_device_base_state"], "NOT_YET_OBSERVED")

        invocation = model["cross_scene_personal_information_invocation"]
        self.assertEqual(
            invocation["control_plane"],
            "CALLING_SCENE_PREAPPROVAL_RECEIPT_TO_TOTAL_FIELD_COMPLIANCE_RESOLUTION",
        )
        self.assertEqual(
            invocation["data_plane"],
            "ASSOCIATION_PERSONAL_INFORMATION_FIELD_DIRECT_TO_APPROVED_CALLER_REGISTERED_DEVICE_WITHOUT_TRAVERSING_CALLING_SCENE_DATA_STORE",
        )
        self.assertIn("CALLER_DEVICE_REFERENCE", invocation["request_must_record"])
        self.assertIn(
            "SCENE_PREAPPROVAL_RECEIPT_REFERENCE", invocation["request_must_record"]
        )
        self.assertIn("PURPOSE_CODE", invocation["scene_preapproval_receipt_must_bind"])
        self.assertIn(
            "CALLER_DEVICE_D6_BASE_REFERENCE",
            invocation["scene_preapproval_receipt_must_bind"],
        )
        self.assertFalse(invocation["calling_scene_receives_personal_payload"])
        self.assertTrue(invocation["caller_device_must_be_registered_and_bound_to_approved_seat"])
        self.assertTrue(invocation["recipient_bound_reconstruction_capability_required"])
        self.assertFalse(
            invocation["packet_or_reconstruction_metadata_alone_may_reveal_personal_information"]
        )
        self.assertTrue(invocation["receipt_is_single_use_or_explicitly_bounded"])
        self.assertTrue(invocation["all_access_is_append_only_auditable"])
        self.assertFalse(invocation["technical_governance_may_obstruct_valid_legal_authority"])

        sovereignty = model["personal_data_sovereignty_and_checks_balances"]
        self.assertEqual(
            sovereignty["optimization_objective"],
            "MAXIMIZE_LAWFUL_AUTHORIZED_UTILITY_UNDER_PERSONAL_DATA_SOVEREIGNTY",
        )
        self.assertEqual(
            sovereignty["separated_functions"]["custody"],
            "FIELD_DEFINED_DATA_CUSTODY_SCOPE",
        )
        self.assertIn("SPECIFIC_PURPOSE_REQUIRED", sovereignty["hard_constraints"])
        self.assertIn("NO_REIDENTIFICATION", sovereignty["hard_constraints"])
        self.assertIn(
            "LEGAL_DUTY_ACCESS_MUST_NOT_BE_DEFEATED_BY_EXTRA_TECHNICAL_APPROVAL",
            sovereignty["hard_constraints"],
        )
        self.assertIn("CORRECTION", sovereignty["data_subject_controls"])
        self.assertFalse(
            sovereignty[
                "founder_or_model_may_override_data_subject_rights_or_lawful_purpose_boundary"
            ]
        )
        self.assertEqual(
            sovereignty["external_legal_evidence_role"],
            "D4_EVIDENCE_ONLY_NOT_ARCHITECTURE_AUTHORITY",
        )
        field_scopes = model["field_scoped_information_custody_model"]
        self.assertEqual(field_scopes["custody_scopes"]["total_field"]["persistent_holds"], [])
        self.assertIn(
            "PERSON_IDENTITY_MASTER",
            field_scopes["custody_scopes"]["association_personal_information_field"]["holds"],
        )
        self.assertIn(
            "ORDER_INVENTORY_PAYMENT_AND_SHIFT_DETAIL",
            field_scopes["custody_scopes"]["cafe_field"]["holds"],
        )
        self.assertIn(
            "LEGAL_DUTY_EXECUTION_RECORD",
            field_scopes["custody_scopes"]["property_management_committee_field"]["holds"],
        )
        self.assertIn(
            "TOTAL_FIELD_ORCHESTRATES_ASSOCIATION_PERSONAL_INFORMATION_FIELD_TO_PROPERTY_COMMITTEE_EXACT_LAWFUL_DUTY_VIEW_WITH_APPEND_ONLY_ACCESS_AUDIT",
            field_scopes["cross_scope_flows"],
        )
        self.assertIn("NO_RAW_GLOBAL_REPLICATION", field_scopes["performance_rules"])
        self.assertIn("NO_REIDENTIFICATION", field_scopes["privacy_rules"])
        self.assertFalse(
            field_scopes["total_field_or_any_field_may_unilaterally_expand_another_field_scope"]
        )
        boundary = model["field_to_total_field_information_boundary"]
        self.assertFalse(boundary["total_field_may_materialize_field_detail"])
        self.assertFalse(boundary["total_field_may_persist_deidentified_research_statistics"])
        self.assertTrue(boundary["persistent_research_result_requires_designated_research_field"])
        self.assertFalse(boundary["statistics_may_be_reidentified_or_joined_to_person"])
        self.assertFalse(boundary["cross_scene_detail_copy"])
        self.assertIn("ACTION_CLASS", boundary["behavior_envelope_fields"])
        self.assertIn("AGGREGATED_VALUE", boundary["deidentified_research_statistic_fields"])
        self.assertIn("NO_DIRECT_IDENTIFIER", boundary["research_statistic_constraints"])
        self.assertIn(
            "TRANSACTION_LINE_DETAIL",
            boundary["detailed_operating_information_remains_in_child"],
        )
        self.assertNotIn(
            "MEMBER_PROFILE",
            boundary["detailed_operating_information_remains_in_child"],
        )
        cafe = model["cafe_field_data_custody"]
        self.assertEqual(
            cafe["scene_reality_classification"],
            "FOUNDER_DECLARED_CURRENT_REAL_WORLD_SCENE_PENDING_LIVE_EVIDENCE_BINDING",
        )
        self.assertEqual(cafe["role"], "CAFE_FIELD_DATA_CUSTODIAN_AND_BUSINESS_CAPABILITY_PROJECTION")
        self.assertEqual(cafe["observed_runtime_database"], "wuchang_odoo")
        self.assertTrue(cafe["retains_detailed_operating_information"])
        self.assertIn("MENU_CONTENT", cafe["cafe_owned_content_classes"])
        self.assertIn("OPERATING_RECORD_DETAIL", cafe["cafe_owned_content_classes"])
        self.assertTrue(cafe["exports_only_deidentified_research_statistics_to_total_field"])
        self.assertFalse(cafe["may_redefine_total_field_root"])
        self.assertEqual(
            cafe["writeback_rule"],
            "RETURN_COORDINATE_BOUND_BEHAVIOR_AND_DEIDENTIFIED_RESEARCH_STATISTICS_TO_TOTAL_FIELD_FOR_D1_TO_D8_REOBSERVATION",
        )
        query_projection = model["cafe_aggregate_query_projection"]
        self.assertEqual(
            query_projection["query_mode"],
            "TOTAL_FIELD_SCOPED_QUERY_OF_CAFE_AGGREGATE_PROJECTION",
        )
        self.assertIn(
            "TOTAL_REVENUE_BY_APPROVED_PERIOD",
            query_projection["queryable_metrics"],
        )
        self.assertIn(
            "PRODUCT_SALES_TOTAL_BY_APPROVED_PERIOD",
            query_projection["queryable_metrics"],
        )
        self.assertIn("SALES_TOTAL_BY_TIME_WINDOW", query_projection["queryable_metrics"])
        self.assertIn("NO_PERSONAL_IDENTIFIER", query_projection["response_constraints"])
        self.assertIn(
            "NO_RECIPE_COST_SUPPLIER_PRICE_MARGIN_OR_OTHER_BUSINESS_SECRET",
            query_projection["response_constraints"],
        )
        self.assertFalse(query_projection["may_return_raw_business_detail"])
        self.assertFalse(query_projection["may_return_person_level_behavior"])
        self.assertFalse(query_projection["may_expose_business_secret"])
        masking = model["association_personal_information_lookup_and_scene_projection"]
        self.assertEqual(
            masking["association_custody_field_role"],
            "MATCH_PERSON_UNDER_EXACT_LEGAL_OR_AUTHORIZED_PURPOSE_SCOPE",
        )
        self.assertIn("OPAQUE_MEMBER_REFERENCE", masking["child_query_fields"])
        self.assertIn("MASKED_OPERATIONAL_MEMBER_REFERENCE", masking["child_may_receive"])
        self.assertIn("MASKED_DISPLAY_REFERENCE", masking["child_may_receive"])
        self.assertIn("APPLICABLE_MEMBER_BENEFIT_SET", masking["child_may_receive"])
        self.assertFalse(masking["child_may_receive_or_store_member_master_detail"])
        self.assertTrue(
            masking["child_to_total_return_inherits_behavior_and_deidentified_statistics_boundary"]
        )
        self.assertFalse(masking["merchant_or_model_may_receive_member_plaintext_by_default"])
        self.assertEqual(
            masking["controlled_view_purpose"],
            "CALLING_SCENE_EXACT_LAWFUL_PURPOSE_ONLY",
        )
        self.assertTrue(
            masking[
                "controlled_view_may_include_identifying_fields_only_when_exact_lawful_duty_requires_them"
            ]
        )
        self.assertFalse(masking["controlled_view_may_define_d8_or_root_authority"])
        handoff = model["membership_application_handoff"]
        self.assertEqual(handoff["cafe_role"], "MEMBERSHIP_APPLICATION_INTAKE_INTERFACE_ONLY")
        self.assertEqual(
            handoff["total_field_role"],
            "ORCHESTRATE_HANDOFF_AND_MASKED_STATUS_RETURN_NO_DATA_CUSTODY",
        )
        self.assertEqual(
            handoff["association_custody_field_role"],
            "STORE_PROCESS_AND_GOVERN_MEMBERSHIP_APPLICATION",
        )
        self.assertFalse(handoff["total_field_may_persist_application_plaintext"])
        self.assertFalse(handoff["child_may_persist_application_plaintext"])
        self.assertFalse(handoff["child_may_approve_or_activate_membership"])
        membership_paths = handoff["membership_classes_and_compute_capability_binding"]
        personal_member = membership_paths["personal_member_path"]
        self.assertFalse(personal_member["self_owned_distributed_compute_required"])
        self.assertFalse(personal_member["cloud_or_local_model_is_member"])
        self.assertIn("PERSON_OWNED_CLOUD_AI_API_CONNECTOR", personal_member["may_bind"])
        group_member = membership_paths["distributed_compute_group_member_path"]
        self.assertFalse(group_member["compute_capability_alone_grants_group_membership"])
        self.assertTrue(group_member["association_field_issues_group_member_seat_after_approval"])
        self.assertFalse(group_member["ai_or_total_field_may_self_approve_group_membership"])
        self.assertTrue(group_member["resource_ownership_remains_with_contributor"])
        self.assertEqual(group_member["current_live_bylaws_eligibility_binding"], "NOT_YET_OBSERVED")
        self.assertIn("MASKED_APPLICATION_STATE", handoff["total_field_returns_to_child"])
        self.assertTrue(model["parallel_total_field_forbidden"])

    def test_workspace_root_model_contract_is_total_field_controlled_passive_organ(self):
        packet = build_dynamic_context(
            "請說明本地根模型與紅隊告警",
            root=ROOT,
            max_items=4,
            identity_class="founder",
            generated_at="2026-07-27T00:00:00+00:00",
        )
        self.assertEqual(packet["state"], "TOTAL_FIELD_DYNAMIC_CONTEXT_READY")
        projection = packet["capability_route"]["root_model_projection"]
        self.assertEqual(projection["runtime_model_name"], "xiaoj:latest")
        self.assertEqual(projection["base_model"], "xiaoj-backbrain:latest")
        self.assertEqual(
            projection["model_role"],
            "PASSIVE_REPLACEABLE_REASONING_GENERATION_ORGAN",
        )
        self.assertEqual(projection["controller"], "TOTAL_FIELD_USING_8D_ADI")
        self.assertFalse(projection["model_output_is_authority"])
        self.assertIsNone(projection["parameter_class"])
        self.assertIsNone(projection["core_model_count"])
        self.assertIsNone(projection["unified_model_mode"])

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

    def test_member_identity_cannot_block_or_override_total_field_authority(self):
        packet = build_dynamic_context(
            "會員系統必須接入 Odoo 但不得取得總場權威",
            root=ROOT,
            max_items=4,
            identity_class="founder",
            generated_at="2026-09-03T00:00:00+00:00",
        )
        contract = packet["identity_seat_boundary_contract"]
        lookup = packet["adi_discrete_integer_lookup_math_contract"]
        data_projection = packet["data_custody_and_cafe_research_projection"]
        data_binding = packet["data_custody_source_binding"]
        self.assertEqual(
            data_projection["personal_information_field_custody"]["total_field_role"],
            "ORCHESTRATE_MASKED_PROJECTION_NO_PERSONAL_DATA_CUSTODY",
        )
        self.assertEqual(
            lookup["state_representation"],
            "VERSIONED_NAMESPACE_BOUND_DISCRETE_INTEGER_CODES",
        )
        self.assertIn("VERSIONED_TABLE_LOOKUP", lookup["operations"])
        self.assertFalse(lookup["floating_point_required_for_known_discrete_lookup"])
        self.assertFalse(lookup["semantic_similarity_or_llm_guess_used_for_coordinate_value"])
        self.assertFalse(lookup["integer_lookup_alone_guarantees_correct_external_effect"])
        self.assertTrue(lookup["reobservation_required"])
        self.assertEqual(
            data_projection["personal_information_field_custody"]
            ["personal_information_master_custodian"],
            "FIVE_CHANG_ASSOCIATION_FIELD",
        )
        self.assertEqual(
            data_projection["personal_data_sovereignty_and_checks_balances"]
            ["optimization_objective"],
            "MAXIMIZE_LAWFUL_AUTHORIZED_UTILITY_UNDER_PERSONAL_DATA_SOVEREIGNTY",
        )
        self.assertIn(
            "TOTAL_REVENUE_BY_APPROVED_PERIOD",
            data_projection["cafe_aggregate_query_projection"]["queryable_metrics"],
        )
        self.assertEqual(
            data_projection["membership_application_handoff"]["total_field_role"],
            "ORCHESTRATE_HANDOFF_AND_MASKED_STATUS_RETURN_NO_DATA_CUSTODY",
        )
        self.assertEqual(
            data_projection["cross_scene_personal_information_invocation"]["data_plane"],
            "ASSOCIATION_PERSONAL_INFORMATION_FIELD_DIRECT_TO_APPROVED_CALLER_REGISTERED_DEVICE_WITHOUT_TRAVERSING_CALLING_SCENE_DATA_STORE",
        )
        self.assertEqual(
            data_binding["relative_path"],
            "configs/total_field/w7tp_8dadi_d6_contract_v2_3.json",
        )
        self.assertFalse(data_binding["file_self_establishes_canonical_or_d8"])
        self.assertTrue(contract["identity_and_seat_are_envelope_preconditions"])
        self.assertEqual(
            contract["identity_packet_class"],
            "8DADI_SOVEREIGN_PERSON_IDENTITY_PACKET",
        )
        self.assertFalse(contract["identity_is_d1"])
        self.assertFalse(contract["identity_is_d8"])
        self.assertFalse(contract["founder_path_blocked_by_member_system"])
        self.assertFalse(contract["founder_system_identity_root_is_universal_scene_role"])
        self.assertTrue(contract["founder_scene_action_requires_linked_scene_packet"])
        self.assertTrue(contract["scene_packet_references_same_sovereign_identity_root"])
        self.assertFalse(
            contract["founder_authority_may_bypass_missing_scene_packet_for_scene_action"]
        )
        self.assertFalse(contract["odoo_is_total_field_authority"])
        self.assertEqual(
            contract["member_personal_information_custodian"],
            "FIVE_CHANG_ASSOCIATION_FIELD",
        )
        self.assertFalse(contract["member_plaintext_in_model_context"])
        self.assertTrue(contract["scene_receives_purpose_bound_controlled_projection_only"])
        self.assertTrue(
            contract[
                "identifying_fields_allowed_only_when_exact_lawful_duty_requires_them"
            ]
        )
        self.assertFalse(contract["scene_application_may_proxy_personal_payload"])
        self.assertFalse(contract["scene_may_persist_member_plaintext_by_default"])
        self.assertEqual(
            contract["membership_application_processor"],
            "FIVE_CHANG_ASSOCIATION_FIELD_ORCHESTRATED_BY_TOTAL_FIELD",
        )
        self.assertTrue(contract["scene_caller_preapproval_receipt_required"])
        self.assertEqual(
            contract["personal_data_delivery_target"],
            "APPROVED_CALLER_REGISTERED_DEVICE_DIRECT_FROM_ASSOCIATION_FIELD",
        )
        self.assertFalse(contract["calling_scene_receives_personal_payload"])
        self.assertTrue(contract["caller_device_d6_base_is_identity_seat_scope_specific"])
        self.assertFalse(contract["identical_d6_base_across_devices_required"])
        self.assertTrue(contract["role_elevation_preserves_sovereign_person_identity"])
        self.assertIn(
            "COMMITTEE_ISSUED_ACTIVE_CHAIRPERSON_SEAT",
            contract["property_chairperson_capability_requires"],
        )
        self.assertFalse(contract["total_field_may_self_grant_property_chairperson_seat"])
        self.assertFalse(
            contract[
                "cafe_general_member_base_may_reconstruct_association_personal_information"
            ]
        )
        self.assertTrue(
            contract[
                "personal_information_reconstruction_requires_recipient_bound_capability"
            ]
        )
        self.assertTrue(
            contract[
                "packet_metadata_alone_is_insufficient_for_personal_information_reconstruction"
            ]
        )
        self.assertEqual(
            contract["cafe_membership_application_role"],
            "INTAKE_INTERFACE_HANDOFF_ONLY",
        )
        membership_paths = contract["membership_capability_paths"]
        self.assertFalse(
            membership_paths["personal_member"]["self_owned_distributed_compute_required"]
        )
        self.assertFalse(membership_paths["personal_member"]["cloud_or_local_model_is_member"])
        self.assertTrue(
            membership_paths["distributed_compute_group_member"]
            ["registered_distributed_compute_may_apply"]
        )
        self.assertFalse(
            membership_paths["distributed_compute_group_member"]
            ["compute_capability_alone_grants_group_membership"]
        )
        self.assertTrue(
            membership_paths["distributed_compute_group_member"]
            ["association_current_bylaws_and_human_approval_required"]
        )
        self.assertEqual(
            membership_paths["distributed_compute_group_member"]
            ["current_live_bylaws_eligibility_binding"],
            "NOT_YET_OBSERVED",
        )
        self.assertFalse(contract["membership_change_rehashes_canonical_root"])
        self.assertFalse(contract["membership_change_may_rewrite_header"])
        self.assertTrue(contract["member_effect_requires_separate_d8"])
        self.assertTrue(contract["one_person_one_sovereign_identity_packet"])
        founder_person = contract["founder_natural_person_identity_root"]
        self.assertEqual(
            founder_person["subject_reference"],
            "FOUNDER_NATURAL_PERSON_SOVEREIGN_IDENTITY_ROOT",
        )
        self.assertEqual(founder_person["system_role"], "NATURAL_PERSON_FOUNDER")
        self.assertEqual(
            founder_person["declared_google_login_binding_reference"],
            "FOUNDER_PERSONAL_GOOGLE_ACCOUNT_O970106_REF",
        )
        self.assertFalse(founder_person["account_identifier_in_model_context"])
        self.assertTrue(founder_person["google_account_is_authenticator_not_person_identity"])
        self.assertFalse(founder_person["founder_identity_root_is_organization_or_scene"])
        self.assertTrue(
            founder_person["personal_browser_ai_is_user_scene_projection_of_this_person"]
        )
        self.assertTrue(contract["concurrent_scene_seats_allowed"])
        self.assertTrue(
            contract["single_sovereign_identity_session_for_concurrent_scene_seats"]
        )
        self.assertFalse(contract["manual_account_switch_required_for_scene_selection"])
        self.assertTrue(contract["provider_account_bindings_reference_same_person_packet"])
        ai_binding = contract["personal_ai_api_account_binding"]
        self.assertEqual(ai_binding["single_controller"], "EXISTING_TOTAL_FIELD_8DADI")
        self.assertEqual(
            ai_binding["replaceable_unit"],
            "AI_MODEL_COMPUTE_CONNECTOR_NOT_8DADI_INSTANCE",
        )
        self.assertFalse(ai_binding["creates_parallel_8dadi_or_total_field"])
        self.assertFalse(ai_binding["api_account_login_alone_establishes_sovereign_identity"])
        self.assertTrue(ai_binding["sovereign_identity_packet_binding_required"])
        self.assertFalse(ai_binding["automatic_email_address_identity_merge"])
        self.assertTrue(
            ai_binding["multiple_person_owned_ai_api_accounts_may_bind_to_one_person_packet"]
        )
        self.assertFalse(ai_binding["provider_credentials_visible_to_model_or_scene"])
        self.assertTrue(ai_binding["provider_usage_and_budget_remain_account_scoped"])
        self.assertTrue(ai_binding["scene_action_still_requires_active_scene_packet"])
        self.assertEqual(
            contract["founder_declared_existing_scene_roles"]["association_chairperson"],
            "FOUNDER_DECLARED_EXISTING_ROLE_PENDING_LIVE_EVIDENCE_BINDING",
        )
        self.assertEqual(
            contract["founder_declared_existing_scene_roles"]["cafe_owner"],
            "FOUNDER_DECLARED_EXISTING_ROLE_PENDING_LIVE_EVIDENCE_BINDING",
        )
        scene_portfolio = contract["founder_scene_portfolio"]
        self.assertEqual(
            scene_portfolio["current_real_world_scenes"],
            ["FIVE_CHANG_ASSOCIATION", "SHANGPIN_LIAOGUO_CAFE"],
        )
        self.assertEqual(
            scene_portfolio["demonstration_scenes"],
            ["PROPERTY_MANAGEMENT_COMMITTEE"],
        )
        self.assertFalse(
            scene_portfolio[
                "demonstration_scene_may_imply_current_person_role_or_legal_authority"
            ]
        )
        self.assertFalse(scene_portfolio["demonstration_scene_external_effect"])
        self.assertFalse(
            contract["existing_role_admission_requires_re_election_or_business_reformation"]
        )
        self.assertTrue(
            contract[
                "one_registered_device_may_hold_multiple_isolated_scene_base_compartments"
            ]
        )
        self.assertTrue(
            contract["natural_language_scene_switch_does_not_merge_scene_data_or_authority"]
        )
        self.assertIn("NO_ACCOUNT_RELOGIN", contract["browser_scene_experience"])
        self.assertIn(
            "STEP_UP_REGISTERED_DEVICE_UNLOCK",
            contract["privileged_external_effect_confirmation"],
        )
        self.assertFalse(
            contract["cloud_or_local_model_account_may_define_person_identity_or_scene_seat"]
        )
        self.assertTrue(contract["permissions_are_packet_scoped"])
        self.assertEqual(contract["founder_login_providers"], ["LINE", "GOOGLE"])
        self.assertTrue(contract["provider_subjects_map_to_same_person_packet"])
        self.assertFalse(contract["automatic_email_identity_merge"])
        self.assertEqual(contract["default_ai_seat"], "CLOUD_CANDIDATE_SMALL_MODEL")
        self.assertTrue(contract["member_owned_ai_capability_allowed"])
        self.assertEqual(contract["central_cloud_usage_default"], "NOT_USED")
        self.assertFalse(contract["system_mutation_default"])
        self.assertTrue(contract["founder_verification_is_not_d8"])
        self.assertEqual(contract["unverified_system_mutation"], "BLOCK")
        interface = contract["browser_ai_interface"]
        self.assertEqual(interface["selected_projection"], "OPEN_WEBUI")
        self.assertEqual(
            interface["role"],
            "PERSONAL_BROWSER_AI_USER_SCENE_INTERFACE",
        )
        self.assertEqual(interface["scene_class"], "PERSONAL_USER_SCENE_BROWSER_PROJECTION")
        self.assertIn(
            "CLOUD_AND_LOCAL_MODEL_ORGANS",
            interface["application_scene_composition"],
        )
        self.assertTrue(interface["cloud_and_local_models_are_replaceable_organs"])
        self.assertTrue(interface["composition_forms_one_application_scene"])
        self.assertTrue(interface["application_scene_is_not_parallel_8dadi_or_total_field"])
        self.assertTrue(interface["one_person_session_for_concurrent_scene_seats"])
        self.assertFalse(interface["manual_provider_account_switch_required"])
        self.assertTrue(interface["active_scene_and_role_must_be_visible"])
        self.assertIn("8DADI_EXACT", interface["intent_and_capability_resolution"])
        self.assertIn("TOTAL_FIELD", interface["distributed_resource_dispatch"])
        unification = interface["8dadi_logical_unification"]
        self.assertTrue(unification["one_8dadi_control_plane"])
        self.assertTrue(unification["physical_and_scene_boundaries_preserved"])
        self.assertFalse(unification["whole_system_replication_required"])
        cloud_drive = interface["cloud_drive_capability"]
        self.assertEqual(cloud_drive["founder_declared_organization_shared_drive_count"], 3)
        self.assertEqual(
            cloud_drive["live_shared_drive_identifiers_and_permissions"],
            "NOT_YET_OBSERVED",
        )
        self.assertFalse(cloud_drive["whole_drive_sync_or_replication_by_default"])
        self.assertFalse(cloud_drive["ordinary_drive_transfer_is_d6"])
        self.assertFalse(interface["user_selects_physical_node_or_model_account_by_default"])
        self.assertFalse(interface["direct_node_or_hardware_control"])
        self.assertFalse(interface["is_xiaoj_core"])
        self.assertFalse(interface["is_person_identity_root"])
        self.assertFalse(interface["is_total_field_authority"])
        self.assertFalse(interface["provider_credentials_visible_to_model"])
        self.assertTrue(
            interface[
                "personal_ai_api_account_requires_sovereign_identity_packet_binding"
            ]
        )
        self.assertTrue(
            interface[
                "multiple_bound_personal_ai_api_accounts_share_one_person_session_not_one_budget"
            ]
        )
        self.assertFalse(
            interface["provider_or_model_account_is_person_identity_or_scene_authority"]
        )
        self.assertFalse(interface["parallel_member_system"])
        self.assertFalse(interface["configuration_write_authority"])
        self.assertTrue(
            interface["live_compatibility_reobservation_required_before_write"]
        )

    @staticmethod
    def _member_ai_seat_args() -> dict[str, object]:
        allowed = [
            "READ_MINIMUM_DYNAMIC_CONTEXT",
            "ODOO_ROLE_SCOPED_BUSINESS_USE",
            "USE_MEMBER_OWN_AI_CAPABILITY",
            "SUBMIT_CANDIDATE_RESULT",
        ]
        return {
            "person_packet_ref": "person_packet_ref:member:sha256:" + "a" * 64,
            "tenant_ref": "tenant_ref:wuchang",
            "seat_ref": "seat_ref:xiaoj:member",
            "person_permission_scopes": allowed,
            "login_provider": "GOOGLE",
            "login_subject_ref": "login_subject_ref:google:sha256:" + "b" * 64,
            "login_binding_receipt_ref": (
                "login_binding_receipt_ref:sha256:" + "c" * 64
            ),
            "login_binding_verified": True,
            "ai_provider_id": "provider-neutral",
            "provider_ai_session_ref": "provider_ai_session_ref:sha256:" + "d" * 64,
            "provider_ai_session_verified": True,
            "small_model_ref": "model_ref:xiaoj:small",
            "requested_capabilities": allowed,
            "acknowledged_invariants": {
                "AI_ACCOUNT_IS_NOT_PERSON_IDENTITY",
                "AI_ACCOUNT_IS_NOT_TOTAL_FIELD_AUTHORITY",
                "MEMBER_PERMISSIONS_COME_FROM_PERSON_PACKET",
                "UNVERIFIED_SEAT_CANNOT_MODIFY_SYSTEM",
                "SYSTEM_MUTATION_REQUIRES_FOUNDER_VERIFICATION_AND_D8",
                "ODOO_USE_IS_ROLE_SCOPED",
                "PROVIDER_CREDENTIALS_ARE_NOT_EXPOSED_TO_MODEL",
            },
            "session_ttl_seconds": 900,
        }

    def test_member_owned_ai_enters_non_authoritative_small_model_candidate_seat(self):
        packet = build_sovereign_ai_member_seat_admission(
            **self._member_ai_seat_args()
        )
        self.assertEqual(packet["state"], "PASS_CLOUD_CANDIDATE_SMALL_MODEL_SEAT")
        self.assertTrue(packet["candidate_only"])
        self.assertFalse(packet["credentials_included"])
        self.assertEqual(packet["D2_STATE"]["model_class"], "SMALL_MODEL")
        self.assertEqual(
            packet["D6_GENERATIVE_TRANSMISSION"]["member_ai_usage_charge_owner"],
            "MEMBER_PROVIDER_ACCOUNT",
        )
        self.assertEqual(packet["D1_INTENT"]["central_usage_default"], "NOT_USED")
        self.assertFalse(packet["D5_EXECUTION_POLICY"]["odoo_system_administration"])
        self.assertFalse(packet["D5_EXECUTION_POLICY"]["direct_system_mutation"])
        self.assertFalse(packet["D8_ENVELOPE_AUTHORITY"]["operation_authority"])
        self.assertFalse(packet["D8_ENVELOPE_AUTHORITY"]["canonical"])

    def test_unverified_person_packet_cannot_request_system_mutation(self):
        args = self._member_ai_seat_args()
        args["person_permission_scopes"] = ["SYSTEM_MUTATION"]
        args["requested_capabilities"] = ["SYSTEM_MUTATION"]
        packet = build_sovereign_ai_member_seat_admission(**args)
        self.assertEqual(
            packet["state"],
            "BLOCK_SYSTEM_MUTATION_UNVERIFIED_PERSON_PACKET",
        )
        self.assertFalse(packet["D5_EXECUTION_POLICY"]["direct_system_mutation"])

    def test_founder_verified_mutation_request_still_holds_for_exact_d8(self):
        args = self._member_ai_seat_args()
        args["person_permission_scopes"] = ["SYSTEM_MUTATION"]
        args["requested_capabilities"] = ["SYSTEM_MUTATION"]
        args["founder_verified_for_system_mutation"] = True
        packet = build_sovereign_ai_member_seat_admission(**args)
        self.assertEqual(packet["state"], "HOLD_SYSTEM_MUTATION_D8_REQUIRED")
        self.assertFalse(packet["D5_EXECUTION_POLICY"]["direct_system_mutation"])
        self.assertFalse(packet["D8_ENVELOPE_AUTHORITY"]["founder_verification_is_d8"])
        self.assertTrue(
            packet["D8_ENVELOPE_AUTHORITY"]["system_mutation_requires_exact_d8"]
        )

    def test_unverified_member_ai_provider_session_holds(self):
        args = self._member_ai_seat_args()
        args["provider_ai_session_verified"] = False
        packet = build_sovereign_ai_member_seat_admission(**args)
        self.assertEqual(
            packet["state"],
            "HOLD_MEMBER_AI_PROVIDER_SESSION_UNVERIFIED",
        )

    def test_member_ai_seat_rejects_scalar_permission_input(self):
        args = self._member_ai_seat_args()
        args["person_permission_scopes"] = "SYSTEM_MUTATION"
        args["requested_capabilities"] = "SYSTEM_MUTATION"
        packet = build_sovereign_ai_member_seat_admission(**args)
        self.assertEqual(packet["state"], "HOLD_SOVEREIGN_AI_SEAT_INPUT_INVALID")
        self.assertEqual(
            packet["D7_RISK_QUARANTINE"]["invalid_collections"],
            ["person_permission_scopes", "requested_capabilities"],
        )

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
