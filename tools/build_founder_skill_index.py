#!/usr/bin/env python3
"""Build the Founder-only 8D skill index from active, explicit skill sources.

This is a deterministic metadata indexer. It hashes SKILL.md bytes but never
copies their bodies, reads credentials, connects accounts, or grants runtime
authority to the local model.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "manifests/ollama_xiaoj_total_field_v0_1"
REGISTRY_PATH = PACK / "capability_registry.json"
INDEX_PATH = PACK / "founder_all_skills_8d_index.json"
CATALOG_PATH = ROOT / "web/founder_skill_catalog/index.html"

ACTIVE_SKILL_ROOTS = (
    Path("/home/taiji_admin/.agents/skills"),
    Path("/home/taiji_admin/.codex/skills/derive-8d-adi-insight"),
    Path("/home/taiji_admin/.codex/skills/.system"),
    Path("/home/taiji_admin/.codex/plugins/cache"),
)

CONTINUE_LOCAL_TOOLS = (
    "read_file",
    "create_new_file",
    "file_glob_search",
    "ls",
    "run_terminal_command",
)

W7TP_SKILLS = (
    {
        "skill_id": "evidence_echo",
        "name": "W7TP Evidence Echo",
        "version": "0.1",
        "source_path": "tools/ollama_total_field_skill_bridge.py",
        "description": "唯讀回傳去敏後的證據摘要與來源引用。",
        "triggers": ["證據", "來源", "引用", "SHA-256", "目前狀態"],
        "status": "READY_LOCAL",
        "tool_refs": ["local:OllamaTotalFieldSkillBridge.invoke"],
    },
    {
        "skill_id": "candidate_outline",
        "name": "W7TP Candidate Outline",
        "version": "0.1",
        "source_path": "tools/ollama_total_field_skill_bridge.py",
        "description": "建立不具權威的本機候選輪廓。",
        "triggers": ["候選", "草案", "規劃", "實作", "修正"],
        "status": "READY_LOCAL",
        "tool_refs": ["local:OllamaTotalFieldSkillBridge.invoke"],
    },
    {
        "skill_id": "total_field_policy_check",
        "name": "W7TP Total Field Policy Check",
        "version": "0.1",
        "source_path": "tools/ollama_total_field_skill_bridge.py",
        "description": "檢查權威、副作用與禁止輸出。",
        "triggers": ["權限", "授權", "部署", "重啟", "DB write", "router"],
        "status": "READY_LOCAL",
        "tool_refs": ["local:OllamaTotalFieldSkillBridge.invoke"],
    },
    {
        "skill_id": "w7tp_dynamic_context",
        "name": "W7TP Dynamic Context",
        "version": "1.0.0",
        "source_path": "tools/total_field_dynamic_context.py",
        "description": "以現有 MCP 取得雜湊綁定的唯讀總場上下文與技能路由。",
        "triggers": ["動態上下文", "技能查表", "總場證據", "工作區現況"],
        "status": "READY_MCP",
        "tool_refs": ["mcp:get_total_field_dynamic_context"],
    },
    {
        "skill_id": "w7tp_model_source_orchestration",
        "name": "W7TP Model Source Orchestration",
        "version": "1.0.0",
        "source_path": "tools/total_field_dynamic_context.py",
        "description": "由總場固定目標並調用其他模型來源，保留帳號座標、原句、衝突與能力契約，供本機 8DADI 動態上下文重放。",
        "triggers": [
            "GPT駕駛GPT",
            "模型協作",
            "跨帳號意圖",
            "對話匯出",
            "技能融合",
            "小模型雲端算力",
            "上下文恢復",
        ],
        "status": "READY_MCP",
        "tool_refs": ["mcp:orchestrate_model_source_context"],
    },
    {
        "skill_id": "w7tp_true8d_contract",
        "name": "W7TP TRUE8D Contract Sandbox",
        "version": "2.0",
        "source_path": "tools/total_field/w7tp_true8d_contract_sandbox.py",
        "description": "驗證 D1-D8 無副作用候選投影與硬風險優先序。",
        "triggers": ["8D", "TRUE8D", "狀態投影", "總場驗證", "證據封包"],
        "status": "READY_LOCAL",
        "tool_refs": ["local:w7tp_true8d_contract_sandbox"],
    },
    {
        "skill_id": "w7tp-capability-assimilator",
        "name": "W7TP Capability Assimilator",
        "version": "1.1.0",
        "source_path": ".skill-build/w7tp-capability-assimilator/SKILL.md",
        "description": "將外部軟體可觀測能力轉為實作無關的 8D ADI 能力契約，只產生有來源的候選與最小差異。",
        "triggers": ["能力同化", "能力吸收", "外部軟體分析", "clean-room", "最小能力差異"],
        "status": "READY_LOCAL",
        "tool_refs": [
            "linux:python3 .skill-build/w7tp-capability-assimilator/scripts/source_manifest.py --repo <SOURCE_REPOSITORY>",
            "linux:python3 .skill-build/w7tp-capability-assimilator/scripts/validate_assimilation_packet.py <PACKET_JSON>",
        ],
        "required_context": "Exact source coordinate, observed evidence, target Total Field baseline, and no external authority inheritance.",
        "validation": "Run source_manifest.py, validate the packet, preserve provenance, and keep every result candidate-only until separately reviewed.",
        "source_package_sha256": "95c1621ba8435a650716b8efe252e21804609a71a36a1842a35fee4907bb3bfa",
    },
    {
        "skill_id": "deep-research",
        "name": "Deep Research",
        "version": "0.1.15",
        "source_path": ".skill-build/deep-research/SKILL.md",
        "description": "只在明確要求深度研究時，透過受控 Deep Research 連接器產生具來源的研究成果。",
        "triggers": ["深度研究", "deep research", "$deep-research"],
        "status": "NEEDS_CONNECTOR",
        "tool_refs": ["controlled_connector:deep_research_work"],
        "required_context": "Explicit Deep Research intent plus an available Deep Research Work connector and source access.",
        "validation": "Confirm the connector is available at use time; pure Linux execution must return HOLD_CONNECTOR_REQUIRED instead of claiming success.",
    },
    {
        "skill_id": "w7tp_generative_transmission",
        "name": "W7TP Generative Transmission",
        "version": "1.1.0",
        "source_path": ".skill-build/w7tp-internal-generative-transmission/SKILL.md",
        "description": "合併內部生成式傳輸技能至既有總場單一路由：區網優先、VPN 備援、目的端依引用與最小新資訊確定性重構，再由總場重新觀測。",
        "triggers": ["生成式傳輸", "內部生成式傳輸", "區網優先", "VPN備援", "重構條件", "等價狀態", "接收端重構", "查表", "引用"],
        "status": "READY_LOCAL",
        "tool_refs": [
            "local:deterministic_reference_lookup",
            "linux:PYTHONPATH=services/w7tp_gt_mesh_v21 python3 -m w7tp_gt_mesh --config <CONFIG_JSON> doctor",
            "compatibility_adapter:w7tp_gt_mesh.packet.build_transfer",
            "compatibility_adapter:w7tp_gt_mesh.receiver.MeshReceiver.receive",
        ],
        "required_context": "Current 8DADI 2.3 D6 contract, registered nodes, target/base/delta/references/coordinates/reconstruction/verification rules, and a separately authorized effect scope.",
        "validation": "The Linux mesh command proves only adapter readiness. V2.1-named implementation remains compatibility evidence; transmission is valid only when rebound to the current 2.3 D6 contract and reobserved by Total Field.",
        "merged_skill_ids": ["w7tp-internal-generative-transmission"],
        "supporting_source_paths": [
            "manifests/ollama_xiaoj_total_field_v0_1/routing_policy.json",
            "configs/total_field/w7tp_8dadi_d6_contract_v2_3.json",
        ],
    },
    {
        "skill_id": "w7tp_8d_adi_origin_cell_fusion",
        "name": "W7TP 8D ADI Origin-Cell Context Transmission",
        "version": "1.0.0",
        "source_path": "tools/total_field_dynamic_context.py",
        "description": "沿既有總場主鏈合併 8D ADI 感知、動態上下文、生成式傳輸與狀態原胞投影驗證；所有輸出維持候選並返回總場重觀測。",
        "triggers": ["原胞之力", "狀態原胞傳播", "原胞四投影", "8D ADI 感知", "原胞生成式傳輸"],
        "status": "READY_LOCAL",
        "tool_refs": [
            "local:tools.total_field_dynamic_context.build_dynamic_context",
            "local:tools.total_field_dynamic_context.build_8dadi_state_cell_projection",
            "local:tools.total_field_dynamic_context.verify_8dadi_state_cell_projection",
            "local:derive-8d-adi-insight/model_perception_amplifier.py",
            "local:derive-8d-adi-insight/origin_cell_views_validator.py",
        ],
    },
)

PLATFORM_INTERNAL = (
    ("codex_web_research_runtime", "Codex Web Research Runtime", ["網頁研究", "瀏覽器", "搜尋"]),
    ("codex_image_runtime", "Codex Image Generation Runtime", ["圖像生成", "私人影像重構"]),
    ("codex_sites_runtime", "Codex Sites Hosting Runtime", ["網站建立", "網站驗證", "部署"]),
    ("codex_document_control_runtime", "Codex Document Control Runtime", ["文件", "PDF", "試算表", "簡報"]),
    ("codex_collaboration_runtime", "Codex Collaboration Runtime", ["子代理", "平行代理", "協作"]),
)

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "minLength": 1},
        "context_refs": {"type": "array", "items": {"type": "string"}},
        "identity_profile_ref": {"const": "FOUNDER_ALL_SKILLS"},
    },
    "required": ["intent", "identity_profile_ref"],
    "additionalProperties": False,
}

OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["state", "skill_id", "candidate", "evidence", "authority"],
    "properties": {
        "state": {"enum": ["CANDIDATE_ONLY", "HOLD", "BLOCK"]},
        "skill_id": {"type": "string"},
        "candidate": {"type": ["object", "null"]},
        "evidence": {"type": "array"},
        "authority": {"const": "FOUNDER_FULL_SKILL_USE_CANDIDATE_ONLY"},
    },
    "additionalProperties": True,
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def _frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return ""
    parts = text.split("---", 2)
    return parts[1] if len(parts) == 3 else ""


def _field(block: str, name: str) -> str | None:
    match = re.search(rf"(?m)^{re.escape(name)}:\s*(.+?)\s*$", block)
    if match is None:
        return None
    return match.group(1).strip().strip("'\"")


def _skill_id_from_path(path: Path) -> str:
    return path.parent.name


def _source_version(path: Path, frontmatter: str, source_sha256: str) -> str:
    versions = re.findall(r"/(?:canva|github|gmail|google-drive|openai-developers|openai-templates|slack)/([^/]+)/", path.as_posix())
    if versions:
        return versions[0]
    match = re.search(r'(?m)^\s*version:\s*["\']?([^"\'\s]+)', frontmatter)
    return match.group(1) if match else f"sha256:{source_sha256[:12]}"


def _triggers(description: str, skill_id: str) -> list[str]:
    when = re.split(r"\bWHEN:\s*", description, maxsplit=1, flags=re.IGNORECASE)
    source = when[1] if len(when) == 2 else f"{skill_id} {description}"
    quoted = re.findall(r'"([^"]{2,80})"', source)
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9.+#/-]{2,}|[\u3400-\u9fff]{2,}", source)
    values: list[str] = []
    for value in quoted + tokens:
        normalized = value.strip(" ,.;:")
        if normalized and normalized.casefold() not in {item.casefold() for item in values}:
            values.append(normalized)
        if len(values) >= 12:
            break
    return values or [skill_id]


def _classify(path: Path, skill_id: str) -> tuple[str, list[str], str]:
    value = path.as_posix()
    if skill_id == "derive-8d-adi-insight":
        return (
            "READY_LOCAL",
            [
                "local:derive-8d-adi-insight/model_perception_amplifier.py",
                "local:derive-8d-adi-insight/origin_cell_views_validator.py",
                "local:tools.total_field_dynamic_context.build_dynamic_context",
                "local:tools.total_field_dynamic_context.build_8dadi_state_cell_projection",
                "local:tools.total_field_dynamic_context.verify_8dadi_state_cell_projection",
            ],
            "Exact installed Skill source, packet verifier, state-cell projection, dynamic-context and Total Field reobservation are required.",
        )
    if "/.agents/skills/" in value:
        return (
            "NEEDS_CONNECTOR",
            ["controlled_connector:azure_cli_or_azure_mcp"],
            "Azure identity, subscription context, and least-privilege login are required at use time.",
        )
    if "/canva/" in value:
        return "NEEDS_CONNECTOR", ["controlled_connector:canva"], "Canva connector authorization is required."
    if "/github/" in value:
        return "NEEDS_CONNECTOR", ["controlled_connector:github"], "GitHub connector authorization is required."
    if "/gmail/" in value:
        return "NEEDS_CONNECTOR", ["controlled_connector:gmail"], "Gmail connector authorization is required."
    if "/google-drive/" in value:
        return "NEEDS_CONNECTOR", ["controlled_connector:google_drive"], "Google Drive connector authorization is required."
    if "/slack/" in value:
        return "NEEDS_CONNECTOR", ["controlled_connector:slack"], "Slack connector authorization is required."
    if "/openai-developers/" in value:
        return "NEEDS_CONNECTOR", ["controlled_connector:openai_platform"], "OpenAI platform secure setup is required."
    if "/openai-templates/" in value:
        return (
            "NEEDS_LOCAL_ADAPTER",
            ["candidate_adapter:document_or_artifact_renderer"],
            "Template source exists; Continue has no mapped document-control renderer.",
        )
    if skill_id in {"skill-creator", "plugin-creator"}:
        return "READY_LOCAL", [f"continue_builtin:{tool}" for tool in CONTINUE_LOCAL_TOOLS], "Workspace files and validation context."
    return (
        "NEEDS_LOCAL_ADAPTER",
        [f"candidate_adapter:{skill_id}"],
        "Skill definition exists but its Codex runtime tool is not exported to Continue.",
    )


def _maximum_effect(status: str) -> str:
    return {
        "READY_LOCAL": "LOCAL_CANDIDATE",
        "READY_MCP": "READ_ONLY_MCP_EVIDENCE",
        "NEEDS_CONNECTOR": "CONNECTOR_REQUEST_CANDIDATE",
        "NEEDS_LOCAL_ADAPTER": "DEFINITION_ONLY",
        "PLATFORM_INTERNAL_UNEXPORTABLE": "OPAQUE_REFERENCE_ONLY",
    }[status]


def _packet(entry: dict[str, Any], source_manifest_sha256: str, ordinal: int) -> dict[str, Any]:
    source_path = entry.get("source_path")
    source_sha256 = entry.get("source_sha256")
    base = {
        "schema_version": "1.0.0",
        "skill_id": entry["skill_id"],
        "skill_name": entry["name"],
        "skill_version": entry["version"],
        "status": entry["status"],
        "D1_INTENT": {
            "triggers": entry["triggers"],
            "description": entry["description"],
            "required_context": entry["required_context"],
        },
        "D2_STATE": {
            "mapping_state": entry["status"],
            "runtime_claim": entry["status"] in {"READY_LOCAL", "READY_MCP"},
            "superseded": False,
        },
        "D3_COORDINATE": {
            "node": "MSI_LOCAL_WSL",
            "repository": "/home/taiji_admin/Taiji_Hub",
            "source_path": source_path,
            "ordinal": ordinal,
        },
        "D4_EVIDENCE": {
            "source_sha256": source_sha256,
            "source_manifest_sha256": source_manifest_sha256,
            "source_kind": entry["source_kind"],
        },
        "D5_EXECUTION": {
            "tool_refs": entry["tool_refs"],
            "input_schema": INPUT_SCHEMA,
            "output_schema": OUTPUT_SCHEMA,
            "maximum_effect": _maximum_effect(entry["status"]),
            "single_founder_confirmation_required_for_side_effect": True,
            "model_commit_allowed": False,
        },
        "D6_TECHNICAL_DEFINITION": {
            "lookup": "DETERMINISTIC_INTEGER_TRIGGER_SCORE",
            "load_on_demand": True,
            "full_skill_body_in_default_context": False,
            "validation": entry["validation"],
        },
        "D7_RISK": {
            "credential_to_model": False,
            "false_ready_claim_forbidden": True,
            "connector_login_only_at_use_time": entry["status"] == "NEEDS_CONNECTOR",
            "platform_hidden_prompt_copied": False,
        },
        "D8_ENVELOPE": {
            "model_identity": "FOUNDER_PRIVATE_XIAOJ",
            "owner": "江政隆",
            "access_profile": "FOUNDER_ALL_SKILLS",
            "member_boundary": "OWNER_ONLY",
            "interface": "FOUNDER_VPN_FULL",
            "receiver": "get_total_field_dynamic_context",
            "return_authority": "FOUNDER_FULL_SKILL_USE_CANDIDATE_ONLY",
        },
    }
    if entry.get("merged_skill_ids"):
        base["D2_STATE"]["merged_skill_ids"] = list(entry["merged_skill_ids"])
    if entry.get("supporting_sources"):
        base["D4_EVIDENCE"]["supporting_sources"] = list(entry["supporting_sources"])
    if entry.get("source_package_sha256"):
        base["D4_EVIDENCE"]["source_package_sha256"] = entry["source_package_sha256"]
    base["packet_id"] = f"skill8d:{ordinal:04d}:{entry['skill_id']}:{canonical_sha256(base)[:16]}"
    base["packet_sha256"] = canonical_sha256(base)
    return base


def _discover_skill_md() -> list[dict[str, Any]]:
    paths: set[Path] = set()
    for root in ACTIVE_SKILL_ROOTS:
        if root.is_dir():
            paths.update(root.rglob("SKILL.md"))
    entries: list[dict[str, Any]] = []
    for path in sorted(paths, key=lambda item: item.as_posix()):
        data = path.read_bytes()
        text = data.decode("utf-8", errors="replace")
        frontmatter = _frontmatter(text)
        skill_id = _field(frontmatter, "name") or _skill_id_from_path(path)
        description = _field(frontmatter, "description") or f"Skill source: {skill_id}"
        source_sha256 = sha256_bytes(data)
        status, tool_refs, required_context = _classify(path, skill_id)
        entries.append(
            {
                "skill_id": skill_id,
                "name": skill_id,
                "version": _source_version(path, frontmatter, source_sha256),
                "source_path": path.as_posix(),
                "source_sha256": source_sha256,
                "source_kind": "SKILL_MD",
                "description": description,
                "triggers": _triggers(description, skill_id),
                "required_context": required_context,
                "status": status,
                "tool_refs": tool_refs,
                "validation": "Verify exact SKILL.md SHA-256, then load the body on demand under its declared tool boundary.",
            }
        )
    return entries


def _local_entries() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for value in W7TP_SKILLS:
        path = ROOT / value["source_path"]
        entry = dict(value)
        entry["source_sha256"] = sha256_bytes(path.read_bytes())
        entry["source_kind"] = "W7TP_LOCAL_CAPABILITY"
        entry.setdefault(
            "required_context",
            "Hash-bound Taiji_Hub evidence and Founder candidate-only policy.",
        )
        entry.setdefault(
            "validation",
            "Verify source SHA-256 and run the named local verifier or MCP contract.",
        )
        if entry.get("supporting_source_paths"):
            entry["supporting_sources"] = [
                {
                    "path": relative,
                    "sha256": sha256_bytes((ROOT / relative).read_bytes()),
                }
                for relative in entry["supporting_source_paths"]
            ]
        entries.append(entry)
    for skill_id, name, triggers in PLATFORM_INTERNAL:
        entries.append(
            {
                "skill_id": skill_id,
                "name": name,
                "version": "opaque-current-platform",
                "source_path": "PLATFORM_INTERNAL_OPAQUE_REF",
                "source_sha256": None,
                "source_kind": "PLATFORM_INTERNAL_NO_PORTABLE_SOURCE",
                "description": "Codex 平台目前可使用，但沒有可合法移植至 Continue 的本機來源與工具契約。",
                "triggers": triggers,
                "required_context": "Platform-owned runtime; no exportable local source.",
                "status": "PLATFORM_INTERNAL_UNEXPORTABLE",
                "tool_refs": ["platform_internal:not_exported"],
                "validation": "Keep opaque; do not copy hidden prompts or claim Continue readiness.",
            }
        )
    return entries


def _formal_skill_contracts(entries: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    assimilator = entries["w7tp-capability-assimilator"]
    transmission = entries["w7tp_generative_transmission"]
    research = entries["deep-research"]
    return [
        {
            "id": "w7tp-capability-assimilator",
            "skill_execution_state": "READY_LOCAL",
            "taxonomy_level": "E2_LOCAL_WRITE_FREE_ANALYSIS",
            "purpose": "把外部系統的可觀測能力轉成有來源、無外部權威繼承的 8D ADI 候選能力契約。",
            "when_to_use": "需要分析、同化、比較或 clean-room 重構外部軟體能力時。",
            "how_to_use": "先以 Linux 產生來源座標，再建立最小差異候選，最後用結構與權威硬牆驗證器檢查。",
            "triggers": assimilator["triggers"],
            "context_references": [
                "CURRENT_FOUNDER_INTENT_REF",
                "CURRENT_TOTAL_FIELD_BASELINE_REF",
                "EXACT_EXTERNAL_SOURCE_REF",
                "OBSERVED_CAPABILITY_EVIDENCE_REFS",
            ],
            "input_contract": "EXACT_SOURCE_COORDINATE_PLUS_OBSERVED_EVIDENCE_PLUS_TARGET_BASE_STATE",
            "output_kind": "CapabilityContractCandidate",
            "tool_binding": assimilator["tool_refs"][0],
            "additional_tool_bindings": assimilator["tool_refs"][1:],
            "side_effects": False,
            "side_effect_class": "READ_ONLY_SOURCE_ANALYSIS_AND_LOCAL_CANDIDATE_VALIDATION",
            "failure_contract": "UNKNOWN_OR_MISSING_SOURCE_EVIDENCE_RETURNS_PRECONDITION_MISSING_OR_HOLD",
            "d6_mapping": "NOT_D6_UNLESS_A_COMPLETE_TARGET_BASE_DELTA_REFERENCE_COORDINATE_RECONSTRUCTION_AND_VERIFICATION_CONTRACT_EXISTS",
            "d8_requirement": "EXTERNAL_SOURCE_OR_SKILL_CANNOT_GRANT_D8_OR_CANONICAL_AUTHORITY",
            "reobservation_contract": "Recompute source coordinates and hashes, then revalidate the same packet without executing the source project.",
            "source": assimilator["source_path"],
            "source_sha256": assimilator["source_sha256"],
            "source_package_sha256": assimilator["source_package_sha256"],
            "examples": {
                "allow": "抽取外部專案的輸入、輸出、失敗模式與能力效果，形成候選能力契約。",
                "hold": "只有說明文字或名稱相似，卻沒有可觀測來源座標與證據。",
            },
        },
        {
            "id": "w7tp_generative_transmission",
            "skill_execution_state": "READY_LOCAL_FOR_LOOKUP_ADAPTER_READINESS_REQUIRES_CURRENT_CONTRACT_FOR_EFFECT",
            "taxonomy_level": "E2_LOCAL_READ_ONLY_E4_ONLY_AFTER_SEPARATE_AUTHORIZATION",
            "purpose": "由總場沿既有單一路由，以區網優先、VPN 備援完成狀態場封包定位、目的端重構與重新觀測。",
            "when_to_use": "已具備目標、基座、最小差異、引用、座標、重構規則及驗證規則的內部節點工作。",
            "how_to_use": "先執行確定性引用查表及 Linux adapter doctor；任何傳送、接收寫入或啟用仍須另行綁定當次 D8 範圍。",
            "triggers": transmission["triggers"],
            "context_references": [
                "CURRENT_FOUNDER_INTENT_REF",
                "W7TP_8DADI_D6_CONTRACT_V2_3_REF",
                "REGISTERED_SOURCE_AND_DESTINATION_NODE_REFS",
                "TARGET_BASE_DELTA_AND_RECONSTRUCTION_REFS",
            ],
            "input_contract": "TARGET_BASE_STATE_PLUS_MINIMUM_REQUIRED_DELTA_PLUS_REFERENCES_PLUS_COORDINATES_PLUS_RECONSTRUCTION_AND_VERIFICATION_RULES",
            "output_kind": "ReconstructableStateFieldPacketCandidate",
            "tool_binding": transmission["tool_refs"][0],
            "additional_tool_bindings": transmission["tool_refs"][1:],
            "side_effects": False,
            "side_effect_class": "LOOKUP_AND_ADAPTER_READINESS_ONLY_TRANSMISSION_EFFECT_REQUIRES_D8",
            "failure_contract": "MISSING_CURRENT_CONTRACT_NODE_BASE_REFERENCE_OR_REOBSERVATION_RETURNS_HOLD",
            "d6_mapping": "CURRENT_8DADI_2_3_TARGET_BASE_DELTA_REFERENCES_COORDINATES_RECONSTRUCTION_AND_VERIFICATION_REQUIRED",
            "d8_requirement": "TRANSMISSION_RECEIVE_WRITE_ACTIVATION_AND_PROMOTION_REQUIRE_SEPARATE_EXACT_AUTHORIZATION",
            "reobservation_contract": "Destination reconstructs locally, verifies the equivalent-state digest, and returns evidence to Total Field for reobservation.",
            "source": transmission["source_path"],
            "source_sha256": transmission["source_sha256"],
            "supporting_sources": transmission["supporting_sources"],
            "merged_skill_ids": transmission["merged_skill_ids"],
            "compatibility_boundary": "services/w7tp_gt_mesh_v21 is historical adapter evidence only and cannot redefine the current 2.3 contract.",
            "examples": {
                "allow": "在已登記節點間以區網優先驗證重構前置條件與 adapter readiness。",
                "hold": "把 Git、SSH、檔案複製、模型輸出或 V2.1 相容層直接稱為目前 D6 完成。",
            },
        },
        {
            "id": "deep-research",
            "skill_execution_state": "NEEDS_CONNECTOR",
            "taxonomy_level": "E3_EXTERNAL_READ_ONLY_AFTER_CONNECTOR_AVAILABLE",
            "purpose": "在明確要求深度研究時，使用受控外部研究能力產生可引用的研究成果。",
            "when_to_use": "使用者明確說深度研究、選用 Deep Research，且連接器在本次執行環境可用時。",
            "how_to_use": "Linux 總場負責查表與門檻判定；實際研究交由已連接的 Deep Research Work 執行並保留來源。",
            "triggers": research["triggers"],
            "context_references": [
                "EXPLICIT_DEEP_RESEARCH_INTENT_REF",
                "AVAILABLE_DEEP_RESEARCH_CONNECTOR_REF",
                "RESEARCH_SOURCE_SCOPE_REF",
            ],
            "input_contract": "EXPLICIT_RESEARCH_REQUEST_PLUS_SOURCE_SCOPE",
            "output_kind": "CitedResearchArtifact",
            "tool_binding": research["tool_refs"][0],
            "side_effects": False,
            "side_effect_class": "READ_ONLY_EXTERNAL_RESEARCH",
            "failure_contract": "PURE_LINUX_OR_MISSING_CONNECTOR_RETURNS_HOLD_CONNECTOR_REQUIRED",
            "d6_mapping": "CLOUD_RESEARCH_OR_MODEL_OUTPUT_IS_NOT_D6",
            "d8_requirement": "RESEARCH_RESULT_IS_EVIDENCE_NOT_AUTHORITY",
            "reobservation_contract": "Reopen cited sources and confirm the artifact remains bound to the requested scope.",
            "source": research["source_path"],
            "source_sha256": research["source_sha256"],
            "examples": {
                "allow": "明確要求深度研究後，由可用連接器建立具引用成果。",
                "hold": "在純 Linux 終端沒有連接器時宣稱已完成深度研究。",
            },
        },
    ]


def _render_catalog(index: dict[str, Any]) -> str:
    rows = []
    for packet in index["skill_packets"]:
        coordinate = packet["D3_COORDINATE"]
        execution = packet["D5_EXECUTION"]
        rows.append(
            "<tr>"
            f"<td>{html.escape(packet['skill_name'])}</td>"
            f"<td><span class=\"status {packet['status']}\">{packet['status']}</span></td>"
            f"<td><code>{html.escape(str(coordinate['source_path']))}</code></td>"
            f"<td><code>{html.escape(', '.join(execution['tool_refs']))}</code></td>"
            "</tr>"
        )
    counts = index["classification_counts"]
    cards = "".join(
        f"<div class=\"card\"><strong>{html.escape(state)}</strong><span>{count}</span></div>"
        for state, count in sorted(counts.items())
    )
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src 'none'; connect-src 'none'; form-action 'none'; base-uri 'none'">
<title>Founder 私人小J技能目錄</title>
<style>
body{{font-family:system-ui,"Noto Sans TC",sans-serif;background:#08111f;color:#e5eefc;margin:0;padding:24px}}main{{max-width:1500px;margin:auto}}h1{{margin-bottom:6px}}.boundary{{color:#93c5fd}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin:24px 0}}.card{{background:#101d31;border:1px solid #274263;border-radius:14px;padding:16px;display:flex;justify-content:space-between}}table{{width:100%;border-collapse:collapse;background:#0d192a}}th,td{{padding:10px;border-bottom:1px solid #253a55;text-align:left;vertical-align:top}}th{{position:sticky;top:0;background:#15263d}}code{{white-space:normal;word-break:break-all;color:#bfdbfe}}.status{{font-weight:800}}.READY_LOCAL,.READY_MCP{{color:#86efac}}.NEEDS_CONNECTOR,.NEEDS_LOCAL_ADAPTER{{color:#fde68a}}.PLATFORM_INTERNAL_UNEXPORTABLE{{color:#fca5a5}}
</style>
</head>
<body><main>
<h1>Founder 私人小J技能目錄</h1>
<p class="boundary">OWNER_ONLY · FOUNDER_VPN_FULL · 所有輸出仍為 Candidate，副作用需單次 Founder 確認與總場驗證。</p>
<section class="cards">{cards}</section>
<table><thead><tr><th>技能</th><th>狀態</th><th>精確來源</th><th>可用工具／接合</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
</main></body></html>
"""


def _refresh_source_manifest() -> None:
    manifest_path = PACK / "source_manifest.sha256"
    existing_paths = []
    if manifest_path.exists():
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                _, path = line.split("  ", 1)
                existing_paths.append(path)
    for path in (
        "tools/build_founder_skill_index.py",
        "tools/validate_total_field_skill_registry.py",
        "manifests/ollama_xiaoj_total_field_v0_1/founder_all_skills_8d_index.json",
        "web/founder_skill_catalog/index.html",
    ):
        if path not in existing_paths:
            existing_paths.append(path)
    for skill_root in (
        ROOT / ".skill-build/w7tp-capability-assimilator",
        ROOT / ".skill-build/w7tp-internal-generative-transmission",
        ROOT / ".skill-build/deep-research",
    ):
        if skill_root.is_dir():
            for path in sorted(skill_root.rglob("*")):
                if path.is_file():
                    relative = path.relative_to(ROOT).as_posix()
                    if relative not in existing_paths:
                        existing_paths.append(relative)
    lines = []
    for relative in existing_paths:
        path = ROOT / relative
        if path.is_file():
            lines.append(f"{sha256_bytes(path.read_bytes())}  {relative}")
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build() -> dict[str, Any]:
    entries = _discover_skill_md() + _local_entries()
    entries.sort(key=lambda item: (item["skill_id"], item["source_path"]))
    source_bindings = [
        {"skill_id": item["skill_id"], "path": item["source_path"], "sha256": item["source_sha256"]}
        for item in entries
    ]
    skill_source_manifest_sha256 = canonical_sha256(source_bindings)
    packets = [_packet(entry, skill_source_manifest_sha256, index) for index, entry in enumerate(entries, 1)]
    counts = dict(sorted(Counter(packet["status"] for packet in packets).items()))
    index = {
        "schema_id": "W7TP_FOUNDER_ALL_SKILLS_8D_INDEX_V1",
        "version": "1.0.0",
        "model_identity": "FOUNDER_PRIVATE_XIAOJ",
        "owner": "江政隆",
        "access_profile": "FOUNDER_ALL_SKILLS",
        "member_boundary": "OWNER_ONLY",
        "interface": "FOUNDER_VPN_FULL",
        "authority": "FOUNDER_FULL_SKILL_USE_CANDIDATE_ONLY",
        "discovery_roots": [path.as_posix() for path in ACTIVE_SKILL_ROOTS],
        "excluded_sources": [
            ".codex/sessions",
            "archived_sessions",
            "rollout_summaries",
            "Taiji_Hub recovery copies",
            "Taiji_Hub virtual-environment copies",
        ],
        "skills_discovered": len(packets),
        "classification_counts": counts,
        "mcp_tools": [
            "get_total_field_dynamic_context",
            "orchestrate_model_source_context",
        ],
        "continue_local_tools": list(CONTINUE_LOCAL_TOOLS),
        "skill_source_manifest_sha256": skill_source_manifest_sha256,
        "skill_packets": packets,
    }
    index["index_sha256"] = canonical_sha256(index)
    INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    registry["model_identity"] = "FOUNDER_PRIVATE_XIAOJ"
    registry["owner"] = "江政隆"
    registry["access_profile"] = "FOUNDER_ALL_SKILLS"
    registry["member_boundary"] = "OWNER_ONLY"
    registry["interface"] = "FOUNDER_VPN_FULL"
    registry["authority"] = "FOUNDER_FULL_SKILL_USE_CANDIDATE_ONLY"
    formal_contracts = _formal_skill_contracts(
        {entry["skill_id"]: entry for entry in entries}
    )
    replaced_ids = {contract["id"] for contract in formal_contracts}
    registry["skills"] = [
        contract
        for contract in registry.get("skills", [])
        if contract.get("id") not in replaced_ids
    ] + formal_contracts
    registry["skill_registration_governance"] = {
        "schema_id": "W7TP_TOTAL_FIELD_SKILL_REGISTRATION_V2_3",
        "current_baseline": "8DADI_W7TP_2_3",
        "current_d6_contract_ref": "configs/total_field/w7tp_8dadi_d6_contract_v2_3.json",
        "registered_skill_ids": [
            "w7tp-capability-assimilator",
            "w7tp_generative_transmission",
            "deep-research",
        ],
        "merged_aliases": {
            "w7tp-internal-generative-transmission": "w7tp_generative_transmission"
        },
        "attached_source_packages": [
            {
                "name": "w7tp-capability-assimilator.zip",
                "sha256": "95c1621ba8435a650716b8efe252e21804609a71a36a1842a35fee4907bb3bfa",
                "disposition": "MERGED_WITH_NEWER_LOCAL_SKILL_SOURCE",
            },
            {
                "name": "govern-total-field-skills (2).zip",
                "sha256": "316438982b912a22a7e575e04fa4d359ec72a92b3291b81cf41296dcf6940cb4",
                "disposition": "COMPATIBLE_TAXONOMY_AND_VALIDATION_RULES_ASSIMILATED_ONLY",
                "rejected_binding": "V2_1_CANONICAL_LOCK_CANNOT_DOWNGRADE_CURRENT_2_3_BASELINE",
            },
        ],
        "registration_rules": {
            "ready_requires_tool_binding": True,
            "connector_capability_cannot_claim_local_execution": True,
            "platform_internal_cannot_claim_local_execution": True,
            "skill_is_not_canonical_authority": True,
            "side_effect_requires_separate_exact_authorization": True,
            "reobservation_required_for_completion": True,
            "no_bulk_promotion": True,
        },
        "linux_validation_command": "python3 tools/validate_total_field_skill_registry.py",
    }
    registry["founder_all_skills_index"] = {
        "path": INDEX_PATH.relative_to(ROOT).as_posix(),
        "sha256": sha256_bytes(INDEX_PATH.read_bytes()),
        "skills_discovered": len(packets),
        "classification_counts": counts,
        "load_policy": "ON_DEMAND_DETERMINISTIC_INTEGER_LOOKUP",
        "default_context_contains_full_skill_bodies": False,
    }
    registry["founder_skill_summaries"] = [
        {
            "skill_id": packet["skill_id"],
            "name": packet["skill_name"],
            "status": packet["status"],
            "source_path": packet["D3_COORDINATE"]["source_path"],
            "source_sha256": packet["D4_EVIDENCE"]["source_sha256"],
            "tool_refs": packet["D5_EXECUTION"]["tool_refs"],
            "packet_id": packet["packet_id"],
        }
        for packet in packets
    ]
    REGISTRY_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_PATH.write_text(_render_catalog(index), encoding="utf-8")
    _refresh_source_manifest()
    return {
        "state": "PASS_FOUNDER_SKILL_INDEX_BUILT",
        "skills_discovered": len(packets),
        "classification_counts": counts,
        "index_path": INDEX_PATH.relative_to(ROOT).as_posix(),
        "catalog_path": CATALOG_PATH.relative_to(ROOT).as_posix(),
    }


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, sort_keys=True))
