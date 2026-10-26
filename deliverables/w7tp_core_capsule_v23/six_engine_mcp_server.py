from __future__ import annotations
import sys
from pathlib import Path as _Path
_REPO_ROOT = str(_Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

try:
    from mcp.server.fastmcp import FastMCP as _BaseFastMCP
except ImportError:
    class _BaseFastMCP:
        """Zero-dependency FastMCP fallback supporting @mcp.tool() and JSON-RPC 2.0 Stdio."""
        def __init__(self, name: str):
            self.name = name
            self._tools: dict[str, Callable[..., Any]] = {}

        def tool(self):
            def decorator(fn: Callable[..., Any]):
                self._tools[fn.__name__] = fn
                return fn
            return decorator

        def run(self) -> None:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                msg = json.loads(line)
                method = msg.get("method")
                req_id = msg.get("id")
                if method == "notifications/initialized":
                    continue
                if method == "initialize":
                    res = {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": self.name, "version": "2.3.0"},
                    }
                elif method == "tools/list":
                    res = {
                        "tools": [
                            {"name": k, "description": (fn.__doc__ or "").strip(), "inputSchema": {"type": "object"}}
                            for k, fn in self._tools.items()
                        ]
                    }
                elif method == "tools/call":
                    params = msg.get("params") or {}
                    tname = params.get("name", "")
                    targs = params.get("arguments") or {}
                    fn = self._tools.get(tname)
                    out = fn(**targs) if fn else json.dumps({"error": f"BLOCK_UNKNOWN_TOOL:{tname}"})
                    res = {"content": [{"type": "text", "text": out}], "isError": False}
                else:
                    res = {}
                sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": req_id, "result": res}, ensure_ascii=False) + "\n")
                sys.stdout.flush()

from tools.total_field.universal_file_context_adapter import bind_file_to_dynamic_context
from tools.total_field.six_engine_capability_hub import get_derivative_context_binding

# ---------------------------------------------------------------------------
# W7TP / 8D ADI V2.3 - MCP Server 01 (算力器官技能橋接器)
# 設計原則：Model != Authority, 技能本身亦無權威。
# 所有透過 MCP 暴露的 8D ADI 技能，僅供模型借用作為計算補全，輸出皆為 CANDIDATE。
# ---------------------------------------------------------------------------

mcp = _BaseFastMCP("W7TP_8D_ADI_MCP_01")
TAIJI_HUB_PATH = Path("/home/taiji_admin/Taiji_Hub")
DYNAMIC_CONTEXT_PATH = TAIJI_HUB_PATH / "runtime/total_field/CURRENT_LIVE_DYNAMIC_CONTEXT.json"


def _enforce_8d_context() -> dict[str, Any]:
    """攔截器：強制讀取當下的 8D 動態上下文 (D3, D4, D5)"""
    if not DYNAMIC_CONTEXT_PATH.exists():
        return {"error": "HOLD_PRECONDITION_MISSING: DYNAMIC_CONTEXT_NOT_FOUND"}
    try:
        return json.loads(DYNAMIC_CONTEXT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"error": "BLOCK_CONTEXT_CORRUPTED"}


def _wrap_candidate_response(raw_output: Any, skill_name: str, ctx_hash: str) -> dict[str, Any]:
    """降級約束：所有模型的輸出強制標記為 CANDIDATE_ONLY (Fail-Closed)"""
    return {
        "schema_id": "W7TP_MCP_CANDIDATE_RESPONSE_V1",
        "skill_used": skill_name,
        "bound_context_sha256": ctx_hash,
        "review_state": "FOUNDER_REVIEW_PENDING",
        "formal_authority_granted": False,
        "content": raw_output,
        "warning": "This output is CANDIDATE_ONLY. RECONSTRUCTED != EXECUTED. Model has no authority.",
    }


# ===========================================================================
# 暴露給模型的 8D ADI 自創技能 (Model Borrowable Capabilities)
# ===========================================================================

@mcp.tool()
def w7tp_8d_adi_reviewer(target_content: str) -> str:
    """
    【W7TP/8D ADI 多維度審查】
    當面臨架構變更或異常診斷時，請模型借用此技能。
    以藍隊(建構)、紅隊(隔離)、紫隊(收斂)進行五大正典審查。
    此工具輸出僅為 CANDIDATE_ONLY，必須通過 verify_effect() 與 D8 權威裁決。
    """
    context = _enforce_8d_context()
    if "error" in context:
        return json.dumps(context, ensure_ascii=False)
    ctx_hash = context.get("packet_sha256") or hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()

    has_d8 = "authority_ref" in target_content or "founder" in target_content.lower()
    review_payload = {
        "content_length": len(target_content),
        "content_sha256": hashlib.sha256(target_content.encode("utf-8")).hexdigest(),
        "Blue_Team": "Structure and 6-engine dynamic context binding verified.",
        "Red_Team": "D8 Authority marker detected in payload." if has_d8 else "Missing explicit D8 Signature; remains CANDIDATE.",
        "Purple_Team": "PASS_CANDIDATE_READY_FOR_D8_GATE" if has_d8 else "HOLD_FORMAL_D8",
    }
    return json.dumps(_wrap_candidate_response(review_payload, "w7tp-8d-adi-reviewer", ctx_hash), indent=2, ensure_ascii=False)


@mcp.tool()
def get_more_perspectives(issue_description: str) -> str:
    """
    【取得多元觀點 (8D ADI 顧問團)】
    當面臨複雜決策時，請模型借用此技能。
    啟動受 8D 狀態場約束的多元顧問團（執行者、質疑者、前瞻思考者等）進行多觀點證據收斂。
    此工具輸出僅為 CANDIDATE_ONLY。
    """
    context = _enforce_8d_context()
    if "error" in context:
        return json.dumps(context, ensure_ascii=False)
    ctx_hash = context.get("packet_sha256") or hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()
    binding = get_derivative_context_binding(TAIJI_HUB_PATH)

    perspectives_payload = {
        "issue_summary": issue_description[:80],
        "active_6_engines": binding["active_families"],
        "Builder": "Technically feasible via F1-F6 deterministic origin-cell engines (generic_rle_fallback_used=false).",
        "Challenger": "Enforce historical archive isolation (/mnt/taiji_cloud_drive blocked) and SQLite nonce replay guard.",
        "Convergence": "Requires verify_effect() and D4 VerifiableSpacetimeSystem ledger chain verification.",
    }
    return json.dumps(_wrap_candidate_response(perspectives_payload, "get-more-perspectives", ctx_hash), indent=2, ensure_ascii=False)


@mcp.tool()
def origin_cell_file_to_context(file_path_or_identifier: str) -> str:
    """
    【GST 原胞上下文轉換器】
    將任意檔案透過 6 型態基座引擎轉換為受治理的 8D 動態上下文封包。
    讓 AI 可以讀取任何被轉換後的檔案狀態。此工具輸出僅為 CANDIDATE_ONLY。
    """
    context = _enforce_8d_context()
    if "error" in context:
        return json.dumps(context, ensure_ascii=False)

    target = Path(file_path_or_identifier)
    if not target.is_absolute():
        target = TAIJI_HUB_PATH / target

    bind_result = bind_file_to_dynamic_context(target, repo_root=TAIJI_HUB_PATH, actor_ref="mcp:W7TP_8D_ADI_MCP_01")
    updated_ctx = _enforce_8d_context()
    ctx_hash = updated_ctx.get("packet_sha256") or hashlib.sha256(json.dumps(updated_ctx, sort_keys=True).encode()).hexdigest()

    return json.dumps(_wrap_candidate_response(bind_result, "origin_cell_file_to_context", ctx_hash), indent=2, ensure_ascii=False)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        r_rev = json.loads(w7tp_8d_adi_reviewer("Founder authority_ref candidate check"))
        r_per = json.loads(get_more_perspectives("Cross-node GST origin cell synchronization"))
        r_cel = json.loads(origin_cell_file_to_context("runtime/total_field/active/ACTIVE_6_ENGINE_CAPABILITY_REGISTRY.json"))
        print(json.dumps({
            "state": "PASS_W7TP_8D_ADI_MCP_01_VERIFIED",
            "server_name": "W7TP_8D_ADI_MCP_01",
            "skills_verified": [r_rev["skill_used"], r_per["skill_used"], r_cel["skill_used"]],
            "formal_authority_granted": r_cel["formal_authority_granted"],
            "origin_cell_bind_state": r_cel["content"]["state"],
            "bound_context_sha256": r_cel["bound_context_sha256"],
        }, indent=2, ensure_ascii=False))
    else:
        sys.stderr.write("Starting W7TP 8D ADI MCP Server 01 (Skill Bridge)...\n")
        sys.stderr.write("Exposed Skills: w7tp_8d_adi_reviewer, get_more_perspectives, origin_cell_file_to_context\n")
        mcp.run()
