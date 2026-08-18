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
        "skill_id": "w7tp_generative_transmission",
        "name": "W7TP Generative Transmission",
        "version": "1.0.0",
        "source_path": "manifests/ollama_xiaoj_total_field_v0_1/routing_policy.json",
        "description": "狀態場封包、引用、查表、重構條件、等價狀態生成與總場驗證。",
        "triggers": ["生成式傳輸", "重構條件", "等價狀態", "查表", "引用"],
        "status": "READY_LOCAL",
        "tool_refs": ["local:deterministic_reference_lookup"],
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
        entry.update(
            {
                "source_sha256": sha256_bytes(path.read_bytes()),
                "source_kind": "W7TP_LOCAL_CAPABILITY",
                "required_context": "Hash-bound Taiji_Hub evidence and Founder candidate-only policy.",
                "validation": "Verify source SHA-256 and run the named local verifier or MCP contract.",
            }
        )
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
        "manifests/ollama_xiaoj_total_field_v0_1/founder_all_skills_8d_index.json",
        "web/founder_skill_catalog/index.html",
    ):
        if path not in existing_paths:
            existing_paths.append(path)
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
        "mcp_tools": ["get_total_field_dynamic_context"],
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
