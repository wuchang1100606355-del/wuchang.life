#!/usr/bin/env python3
"""8D ADI resource arbitration helper for the existing Total Field control path.

This module selects capability providers. It does not create D8 authority,
Canonical state, a second ADI, or any provider-side execution authority.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen

DEFAULT_ROOT = Path("/home/taiji_admin/Taiji_Hub")
TOPOLOGY_PATH = DEFAULT_ROOT / "configs" / "taiji_topology.json"
PRIMARY_INFORMATION_SEARCH_NODES = ["taiji01", "MSI"]
RESOURCE_FABRIC_SCOPE = "ALL_ROUTER_DESCENDANTS"
ALLOWED_CLOUD_RETURNS = [
    "HYPOTHESIS_DELTA",
    "DESIGN_DELTA",
    "CODE_PATCH_CANDIDATE",
    "TEST_CANDIDATE",
    "RISK_CANDIDATE",
    "RESOURCE_RECOMMENDATION",
]
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _http_json(url: str, timeout: float = 1.0) -> dict[str, Any]:
    try:
        with urlopen(url, timeout=timeout) as response:
            raw = response.read(128 * 1024)
        return {"ok": True, "data": json.loads(raw.decode("utf-8"))}
    except Exception as exc:
        return {"ok": False, "error_type": type(exc).__name__}


def _sha(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def classify_intent(intent: str) -> dict[str, bool]:
    text = str(intent or "").casefold()
    has = lambda words: any(word.casefold() in text for word in words)
    return {
        "code": has(["程式", "code", "開發", "修正", "重構", "api", "模組"]),
        "design": has(["設計", "design", "架構", "architecture", "規劃", "plan", "產品", "product"]),
        "complex_code": has(["跨檔", "重構", "架構", "複雜", "大型", "multi-file"]),
        "org_knowledge": has([
            "workspace", "drive", "gmail", "calendar", "docs", "sheets",
            "雲端硬碟", "郵件", "行事曆", "文件", "試算表", "工作區",
        ]),
        "heavy_reasoning": has([
            "深度", "研究", "全域", "比較", "推演", "競品", "架構",
            "reasoning", "research", "benchmark",
        ]),
        "sensitive": has([
            "秘密", "密碼", "token", "private key", "私鑰", "會員明文",
            "個資", "credential", "secret",
        ]),
        "effectful": has([
            "做", "修", "整合", "建構", "啟用", "部署", "恢復", "修改",
            "implement", "fix", "deploy", "enable", "write",
        ]),
        "product_design": has([
            "產品", "競品", "競賽", "展示", "product", "competition",
        ]),
        "latency_sensitive": has(["立即", "即時", "低延遲", "realtime", "latency"]),
    }


def _resource_base(
    resource_id: str,
    resource_type: str,
    node: str,
    provider: str,
    model_or_service: str,
) -> dict[str, Any]:
    return {
        "RESOURCE_ID": resource_id,
        "RESOURCE_TYPE": resource_type,
        "NODE": node,
        "PROVIDER": provider,
        "MODEL_OR_SERVICE": model_or_service,
        "CURRENT_STATE": "UNKNOWN",
        "CAPABILITY_SET": [],
        "CONTEXT_LOCATION": node,
        "PRIVACY_CLASS": "UNKNOWN",
        "AUTHORITY_CLASS": "NONE",
        "COST_CLASS": "UNKNOWN",
        "SUBSCRIPTION_CLASS": "UNKNOWN",
        "LATENCY_CLASS": "UNKNOWN",
        "TRANSFER_COST": "UNKNOWN",
        "TOOL_CAPABILITY": "NONE",
        "VERIFICATION_COST": "UNKNOWN",
        "RECOVERY_DISTANCE": "UNKNOWN",
        "OBSERVED_AT": _now(),
        "EVIDENCE_REFS": [],
    }


def probe_router_resource_fabric(root: Path = DEFAULT_ROOT) -> list[dict[str, Any]]:
    topology_path = root / "configs" / "taiji_topology.json"
    try:
        topo = json.loads(topology_path.read_text(encoding="utf-8"))
    except Exception:
        topo = {}

    resources: list[dict[str, Any]] = []
    for node_name, meta in (topo.get("nodes") or {}).items():
        if not isinstance(meta, dict):
            continue
        item = _resource_base(
            f"ROUTER_NODE_{str(node_name).upper()}",
            "ROUTER_CHILD_NODE",
            str(node_name),
            "TAIJI_ROUTER",
            str(node_name),
        )
        item.update({
            "CURRENT_STATE": "REGISTERED_AVAILABLE_RESOURCE",
            "CAPABILITY_SET": list(meta.get("role") or []),
            "CONTEXT_LOCATION": f"router://nodes/{node_name}",
            "PRIVACY_CLASS": "ROUTER_FABRIC",
            "AUTHORITY_CLASS": "RESOURCE_CAPABILITY_NOT_D8",
            "COST_CLASS": "REGISTERED_RESOURCE",
            "SUBSCRIPTION_CLASS": "SYSTEM_RESOURCE",
            "LATENCY_CLASS": "ROUTER_DEPENDENT",
            "TRANSFER_COST": "ADI_AFFECTED_CLOSURE_ONLY",
            "TOOL_CAPABILITY": "ROUTER_DISPATCHABLE_RESOURCE",
            "VERIFICATION_COST": "REOBSERVE_BEFORE_EFFECT",
            "RECOVERY_DISTANCE": "ROUTER_DEPENDENT",
            "MAX_AUTHORITY_LEVEL": meta.get("max_authority_level"),
            "EVIDENCE_REFS": [str(topology_path), f"router://nodes/{node_name}"],
        })
        resources.append(item)

    for service_name, endpoint in (topo.get("services") or {}).items():
        item = _resource_base(
            f"ROUTER_SERVICE_{str(service_name).upper()}",
            "ROUTER_CHILD_SERVICE",
            "taiji01-router",
            "TAIJI_ROUTER",
            str(service_name),
        )
        item.update({
            "CURRENT_STATE": "REGISTERED_AVAILABLE_RESOURCE",
            "CAPABILITY_SET": [str(service_name)],
            "CONTEXT_LOCATION": f"router://services/{service_name}",
            "PRIVACY_CLASS": "ROUTER_FABRIC",
            "AUTHORITY_CLASS": "RESOURCE_CAPABILITY_NOT_D8",
            "COST_CLASS": "REGISTERED_RESOURCE",
            "SUBSCRIPTION_CLASS": "SYSTEM_RESOURCE",
            "LATENCY_CLASS": "ROUTER_DEPENDENT",
            "TRANSFER_COST": "ADI_AFFECTED_CLOSURE_ONLY",
            "TOOL_CAPABILITY": "ROUTER_SERVICE",
            "VERIFICATION_COST": "REOBSERVE_BEFORE_EFFECT",
            "RECOVERY_DISTANCE": "ROUTER_DEPENDENT",
            "ENDPOINT": endpoint,
            "EVIDENCE_REFS": [str(topology_path), f"router://services/{service_name}"],
        })
        resources.append(item)
    return resources


def probe_taiji01_node() -> dict[str, Any]:
    item = _resource_base(
        "TAIJI01_NODE", "SERVER_NODE", "taiji01", "W7TP_LOCAL", "taiji01 Server"
    )
    total_ok = _http_json("http://127.0.0.1:8082/healthz", timeout=2).get("ok", False)
    adi_ok = _http_json("http://127.0.0.1:9110/health", timeout=2).get("ok", False)
    item.update({
        "CURRENT_STATE": "AVAILABLE_CONNECTED" if total_ok or adi_ok else "HOLD_NODE_UNAVAILABLE",
        "CAPABILITY_SET": [
            "INFORMATION_SEARCH_NODE", "SERVER_FIRST_DEVELOPMENT", "CPU", "RAM",
            "STORAGE", "RUNTIME", "TOTAL_FIELD_HOST", "NATIVE_ADI_HOST",
            "EVIDENCE_CONVERGENCE", "FORMAL_EFFECT_HOST",
        ],
        "CONTEXT_LOCATION": "taiji01:/home/taiji_admin/Taiji_Hub",
        "PRIVACY_CLASS": "LOCAL_SERVER_NODE",
        "AUTHORITY_CLASS": "TOTAL_FIELD_HOST_EFFECT_BOUNDARY",
        "COST_CLASS": "OWNED_LOCAL_COMPUTE",
        "SUBSCRIPTION_CLASS": "OWNED",
        "LATENCY_CLASS": "LOCAL",
        "TRANSFER_COST": "LOW",
        "TOOL_CAPABILITY": "SERVER_RUNTIME_AND_INFORMATION_SEARCH",
        "VERIFICATION_COST": "LOW",
        "RECOVERY_DISTANCE": "SHORTEST_AUTHORITY_PATH",
        "EVIDENCE_REFS": [
            "http://127.0.0.1:8082/healthz",
            "http://127.0.0.1:9110/health",
            "taiji01:/home/taiji_admin/Taiji_Hub",
        ],
    })
    return item


def probe_tailnet_nodes() -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = []
    try:
        proc = subprocess.run(
            ["tailscale", "status", "--json"],
            text=True, capture_output=True, timeout=5,
        )
        if proc.returncode != 0:
            return resources
        status = json.loads(proc.stdout)
    except Exception:
        return resources
    peers = status.get("Peer") or {}
    for peer in peers.values():
        host = str(peer.get("HostName") or "").strip()
        if not host or host.casefold() == "msi":
            continue
        ips = peer.get("TailscaleIPs") or []
        online = bool(peer.get("Online"))
        rid_host = re.sub(r"[^A-Za-z0-9_.:-]+", "-", host).strip("-") or "peer"
        rid = "TAILNET_NODE:" + rid_host
        item = _resource_base(rid, "DISTRIBUTED_COMPUTE_NODE", host, "TAILSCALE", host)
        item.update({
            "CURRENT_STATE": "AVAILABLE_NETWORK_REACHABLE" if online else "REGISTERED_OFFLINE",
            "CAPABILITY_SET": ["DISTRIBUTED_NODE", "NETWORK_RESOURCE"],
            "CONTEXT_LOCATION": host,
            "PRIVACY_CLASS": "TAILNET_NODE",
            "AUTHORITY_CLASS": "CAPABILITY_SOURCE_NOT_D8",
            "COST_CLASS": "NODE_SPECIFIC",
            "SUBSCRIPTION_CLASS": "REGISTERED_RESOURCE",
            "LATENCY_CLASS": "TAILNET",
            "TRANSFER_COST": "ROUTED_BY_8D_ADI",
            "TOOL_CAPABILITY": "NODE_CAPABILITY_TO_BE_LOCALIZED",
            "VERIFICATION_COST": "PROBE_BEFORE_USE",
            "RECOVERY_DISTANCE": "NODE_SPECIFIC",
            "EVIDENCE_REFS": ["tailscale://"+host] + [f"tailscale-ip://{ip}" for ip in ips],
            "NETWORK_REACHABLE": online,
            "TOOL_AGENT_REACHABLE": "UNKNOWN",
        })
        resources.append(item)
    return resources


def probe_msi_node() -> dict[str, Any]:
    item = _resource_base(
        "MSI_NODE", "DEVELOPER_NODE", "MSI", "W7TP_LOCAL", "MSI Developer Device"
    )
    reachable = False
    latency = "UNKNOWN"
    try:
        proc = subprocess.run(
            ["tailscale", "ping", "-c", "1", "--timeout=3s", "100.84.204.114"],
            text=True, capture_output=True, timeout=5,
        )
        reachable = proc.returncode == 0
        if reachable:
            latency = "TAILNET_DIRECT_OR_RELAY_REACHABLE"
    except Exception:
        reachable = False
    item.update({
        "CURRENT_STATE": "AVAILABLE_CONNECTED" if reachable else "HOLD_NODE_UNREACHABLE",
        "CAPABILITY_SET": [
            "DEVELOPER_DEVICE", "DESIGN_SOURCE", "EXPERIMENT_SOURCE",
            "GPU_VRAM", "WINDOWS", "WSL", "LOCAL_REPO", "LOCAL_SKILLS",
            "LOCAL_MODELS", "BROWSER_IDE", "ENGINEERING_EVIDENCE_SOURCE",
        ],
        "CONTEXT_LOCATION": "MSI_DEVELOPER_DEVICE",
        "PRIVACY_CLASS": "LOCAL_DEVELOPER_NODE",
        "AUTHORITY_CLASS": "CAPABILITY_SOURCE_NOT_D8",
        "COST_CLASS": "OWNED_LOCAL_COMPUTE",
        "SUBSCRIPTION_CLASS": "OWNED",
        "LATENCY_CLASS": latency,
        "TRANSFER_COST": "ADI_AFFECTED_CLOSURE_ONLY",
        "TOOL_CAPABILITY": "REMOTE_NODE_CAPABILITY_SOURCE",
        "VERIFICATION_COST": "LOCALIZE_AND_REOBSERVE",
        "RECOVERY_DISTANCE": "SHORT",
        "EVIDENCE_REFS": [
            "tailscale://MSI/100.84.204.114",
            "MSI:/home/taiji_admin/Taiji_Hub",
            "MSI:/home/taiji_admin/Taiji_Hub/.skill-build",
            "MSI:/home/taiji_admin/Taiji_Hub/docs",
            "MSI:/home/taiji_admin/Taiji_Hub/runtime",
            "MSI:/home/taiji_admin/Taiji_Hub/products",
            "MSI:/home/taiji_admin/Taiji_Hub/tests",
        ],
    })
    return item


def probe_local_ollama(url: str, model: str) -> dict[str, Any]:
    item = _resource_base(
        "MSI_OLLAMA_LOCAL", "MODEL_COMPUTE", "MSI", "OLLAMA", model
    )
    probe = _http_json(url.rstrip("/") + "/api/tags", timeout=3.0)
    names = []
    if probe.get("ok"):
        names = [
            row.get("name") for row in probe["data"].get("models", [])
            if isinstance(row, dict)
        ]
    item.update({
        "CURRENT_STATE": "AVAILABLE" if model in names else "HOLD_MODEL_NOT_PRESENT",
        "CAPABILITY_SET": ["LANGUAGE", "INTENT", "CODE", "TOOLS", "LOCAL_REVIEW"],
        "PRIVACY_CLASS": "LOCAL",
        "AUTHORITY_CLASS": "CANDIDATE_ONLY_NOT_D8",
        "COST_CLASS": "LOCAL_COMPUTE",
        "SUBSCRIPTION_CLASS": "LOCAL_OWNED",
        "LATENCY_CLASS": "LAN_OR_TAILNET",
        "TRANSFER_COST": "LOW",
        "TOOL_CAPABILITY": "SHADOW_SOURCE_TOOLS",
        "VERIFICATION_COST": "LOW_TO_MEDIUM",
        "RECOVERY_DISTANCE": "SHORT",
        "EVIDENCE_REFS": [url.rstrip("/") + "/api/tags"],
    })
    return item


def probe_gemini_code_assist() -> dict[str, Any]:
    item = _resource_base(
        "GEMINI_CODE_ASSIST", "MODEL_COMPUTE", "taiji01-code-server",
        "GOOGLE", "Gemini SDLC Agent",
    )
    try:
        proc = subprocess.run(
            ["ss", "-lntp"], text=True, capture_output=True, timeout=3
        )
        ports = []
        for line in proc.stdout.splitlines():
            if "node" not in line:
                continue
            match = re.search(r"127\.0\.0\.1:(\d+)", line)
            if match:
                ports.append(int(match.group(1)))
    except Exception:
        ports = []
    for port in sorted(set(ports)):
        url = f"http://127.0.0.1:{port}/.well-known/agent-card.json"
        probe = _http_json(url, timeout=0.35)
        card = probe.get("data") if probe.get("ok") else None
        if isinstance(card, dict) and card.get("name") == "Gemini SDLC Agent":
            adapter_path = DEFAULT_ROOT / "tools/gemini_code_assist_a2a_candidate.py"
            context_pull_path = DEFAULT_ROOT / "tools/total_field_dynamic_context_pull.py"
            pointer_bound = adapter_path.is_file() and context_pull_path.is_file()
            capabilities = [
                "CODE_GENERATION", "MULTI_FILE_REASONING", "PLAN",
                "WRITE_CANDIDATE", "CHECKPOINT_RESTORE",
            ]
            if pointer_bound:
                capabilities.extend([
                    "POINTER_FIRST_DYNAMIC_CONTEXT_PULL",
                    "TOTAL_FIELD_CANDIDATE_RETURN",
                    "ISOLATED_A2A_WORKSPACE",
                ])
            item.update({
                "CURRENT_STATE": "AVAILABLE",
                "CAPABILITY_SET": capabilities,
                "PRIVACY_CLASS": "CLOUD_SUBSCRIPTION",
                "AUTHORITY_CLASS": "CANDIDATE_ONLY_NOT_D8",
                "COST_CLASS": "SUBSCRIPTION",
                "SUBSCRIPTION_CLASS": "PAID_CURRENT_MONTH",
                "LATENCY_CLASS": "CLOUD_INTERACTIVE",
                "TRANSFER_COST": (
                    "POINTER_FIRST_CONTEXT_PULL_REQUIRED"
                    if pointer_bound else "STATIC_CELL_REQUIRED"
                ),
                "TOOL_CAPABILITY": (
                    "A2A_POINTER_FIRST_CANDIDATE"
                    if pointer_bound else "A2A_AGENT"
                ),
                "CONTEXT_BINDING_STATE": (
                    "POINTER_FIRST_TOTAL_FIELD_BOUND"
                    if pointer_bound else "HOLD_POINTER_FIRST_ADAPTER_MISSING"
                ),
                "SOURCE_WRITE_AUTHORITY": "NONE",
                "FORMAL_EFFECT_RETURN": "TAIJI01_TOTAL_FIELD",
                "WORKSPACE_POLICY": "ISOLATED_TASK_WORKSPACE_REQUIRED",
                "VERIFICATION_COST": "MEDIUM",
                "RECOVERY_DISTANCE": "MEDIUM",
                "EVIDENCE_REFS": [
                    url,
                    str(adapter_path),
                    str(context_pull_path),
                ],
                "A2A_URL": f"http://127.0.0.1:{port}/",
                "AGENT_VERSION": card.get("version"),
            })
            return item
    item["CURRENT_STATE"] = "HOLD_AGENT_NOT_DISCOVERED"
    return item


def probe_vertex(root: Path) -> dict[str, Any]:
    item = _resource_base(
        "GOOGLE_VERTEX_GEMINI", "MODEL_COMPUTE", "GOOGLE_CLOUD",
        "GOOGLE_VERTEX_AI", "Gemini",
    )
    config = root / "config" / "w7tp_vertex_candidate_gateway.json"
    gateway = root / "tools" / "total_field" / "w7tp_vertex_candidate_gateway.py"
    try:
        data = json.loads(config.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    configured = (
        gateway.is_file()
        and data.get("provider") == "GOOGLE_VERTEX_AI"
        and bool(data.get("project"))
        and bool(data.get("model"))
    )
    item.update({
        "CURRENT_STATE": "AVAILABLE_CONFIGURED" if configured else "HOLD_NOT_CONFIGURED",
        "CAPABILITY_SET": ["HEAVY_REASONING", "STRUCTURED_CANDIDATE", "RESEARCH"],
        "PRIVACY_CLASS": "CLOUD",
        "AUTHORITY_CLASS": "CANDIDATE_ONLY_NOT_D8",
        "COST_CLASS": "CLOUD_API",
        "SUBSCRIPTION_CLASS": "PROJECT_RESOURCE",
        "LATENCY_CLASS": "CLOUD",
        "TRANSFER_COST": "STATIC_CELL_REQUIRED",
        "TOOL_CAPABILITY": "VERTEX_CANDIDATE_GATEWAY",
        "VERIFICATION_COST": "MEDIUM_TO_HIGH",
        "RECOVERY_DISTANCE": "SHORT_NO_DIRECT_EFFECT",
        "EVIDENCE_REFS": [str(config), str(gateway)],
        "PROJECT": data.get("project"),
        "MODEL": data.get("model"),
    })
    return item
def probe_workspace(root: Path) -> dict[str, Any]:
    item = _resource_base(
        "GOOGLE_WORKSPACE_ORG", "ORG_KNOWLEDGE_SOURCE", "GOOGLE_WORKSPACE",
        "GOOGLE", "wuchang.life",
    )
    broker = root / "configs" / "cloud" / "local_xiaoj_cloud_api_broker_dryrun.template.json"
    adapters = sorted(
        root.glob(
            "runtime/total_field/google_org_brain/"
            "GOOGLE_ORG_BRAIN_ADAPTER_*/GOOGLE_ORG_BRAIN_ADAPTER_PACKET.json"
        )
    )
    configured = broker.is_file() and bool(adapters)
    item.update({
        "CURRENT_STATE": (
            "REGISTERED_EXTERNAL_CONTEXT_SOURCE" if configured
            else "HOLD_CONTEXT_ADAPTER_EVIDENCE_MISSING"
        ),
        "CAPABILITY_SET": [
            "DRIVE", "DOCS", "SHEETS", "GMAIL", "CALENDAR", "ORG_CONTEXT",
        ],
        "CONTEXT_LOCATION": "wuchang.life",
        "PRIVACY_CLASS": "ORG_DATA_LOCALIZE_BEFORE_MODEL",
        "AUTHORITY_CLASS": "ORG_KNOWLEDGE_SOURCE_NOT_D8",
        "COST_CLASS": "WORKSPACE_SUBSCRIPTION_OR_API",
        "SUBSCRIPTION_CLASS": "NONPROFIT_ORG_RESOURCE",
        "LATENCY_CLASS": "CLOUD_CONTEXT",
        "TRANSFER_COST": "ADI_LOCALIZE_THEN_STATIC_CELL",
        "TOOL_CAPABILITY": "EXTERNAL_CONNECTOR_OR_ADAPTER",
        "VERIFICATION_COST": "SOURCE_REFETCH_REQUIRED",
        "RECOVERY_DISTANCE": "NO_DIRECT_EFFECT",
        "EVIDENCE_REFS": [str(broker)] + [str(adapters[-1])] if adapters else [str(broker)],
    })
    return item


def probe_total_field() -> list[dict[str, Any]]:
    total = _resource_base(
        "TAIJI01_TOTAL_FIELD", "AUTHORITY_EXECUTION", "taiji01",
        "W7TP", "Total Field",
    )
    th = _http_json("http://127.0.0.1:8082/healthz", timeout=2)
    total.update({
        "CURRENT_STATE": "AVAILABLE" if th.get("ok") else "HOLD_UNAVAILABLE",
        "CAPABILITY_SET": ["VERIFY", "EFFECT_GATE", "REOBSERVE", "ROLLBACK"],
        "PRIVACY_CLASS": "LOCAL_AUTHORITY",
        "AUTHORITY_CLASS": "FORMAL_EFFECT_BOUNDARY",
        "COST_CLASS": "LOCAL",
        "SUBSCRIPTION_CLASS": "OWNED",
        "LATENCY_CLASS": "LOCAL",
        "TRANSFER_COST": "LOW",
        "TOOL_CAPABILITY": "RUNTIME_EFFECT",
        "VERIFICATION_COST": "REQUIRED",
        "RECOVERY_DISTANCE": "SHORTEST_AUTHORITY_PATH",
        "EVIDENCE_REFS": ["http://127.0.0.1:8082/healthz"],
    })
    adi = _resource_base(
        "TAIJI01_NATIVE_ADI", "INDEX_VERIFIER", "taiji01",
        "W7TP", "Native ADI",
    )
    ah = _http_json("http://127.0.0.1:9110/health", timeout=2)
    adi.update({
        "CURRENT_STATE": "AVAILABLE" if ah.get("ok") else "HOLD_UNAVAILABLE",
        "CAPABILITY_SET": ["ADI_COORDINATE", "STATE_PACKET", "RECONSTRUCTION"],
        "PRIVACY_CLASS": "LOCAL",
        "AUTHORITY_CLASS": "PRIMARY_DECISION_ENGINE_NOT_AUTHORITY",
        "COST_CLASS": "LOCAL",
        "SUBSCRIPTION_CLASS": "OWNED",
        "LATENCY_CLASS": "LOCAL",
        "TRANSFER_COST": "LOW",
        "TOOL_CAPABILITY": "INDEX_AND_RECONSTRUCT",
        "VERIFICATION_COST": "LOW",
        "RECOVERY_DISTANCE": "SHORT",
        "EVIDENCE_REFS": ["http://127.0.0.1:9110/health"],
    })
    return [total, adi]


def _is_registered(resource: dict[str, Any]) -> bool:
    return bool(resource.get("RESOURCE_ID"))


def _is_available(resource: dict[str, Any]) -> bool:
    state = str(resource.get("CURRENT_STATE", ""))
    return (
        state.startswith("AVAILABLE")
        or state == "REGISTERED_EXTERNAL_CONTEXT_SOURCE"
        or state == "REGISTERED_AVAILABLE_RESOURCE"
    )


def arbitrate_resources(
    intent: str,
    *,
    root: Path = DEFAULT_ROOT,
    local_ollama_url: str,
    local_model: str,
    google_allowed: bool = True,
) -> dict[str, Any]:
    profile = classify_intent(intent)
    resources = [
        probe_taiji01_node(),
        probe_msi_node(),
        probe_local_ollama(local_ollama_url, local_model),
        probe_gemini_code_assist(),
        probe_vertex(root),
        probe_workspace(root),
        *probe_router_resource_fabric(root),
        *probe_tailnet_nodes(),
        *probe_total_field(),
    ]
    by_id = {item["RESOURCE_ID"]: item for item in resources}
    registered = [rid for rid, item in by_id.items() if _is_registered(item)]
    available = [rid for rid, item in by_id.items() if _is_available(item)]
    denied: list[str] = []
    hold: list[str] = [
        rid for rid, item in by_id.items() if not _is_available(item)
    ]
    qualified: list[str] = []
    preferred: list[str] = []
    parallel: list[str] = []
    why_selected: dict[str, str] = {}
    why_not: dict[str, str] = {}

    cloud_ids = {"GEMINI_CODE_ASSIST", "GOOGLE_VERTEX_GEMINI"}
    if profile["sensitive"]:
        denied.extend(rid for rid in cloud_ids if rid in available)
        for rid in cloud_ids:
            why_not[rid] = "Sensitive payload requires local truth/context reduction first."
    elif not google_allowed:
        denied.extend(rid for rid in cloud_ids if rid in available)
        for rid in cloud_ids:
            why_not[rid] = "Google compute disabled for this request."

    information_search_required = (
        profile["design"]
        or profile["code"]
        or profile["product_design"]
        or profile["heavy_reasoning"]
    )
    for rid in ["TAIJI01_NODE", "MSI_NODE"]:
        if rid in available:
            qualified.append(rid)
            if information_search_required:
                parallel.append(rid)
                why_selected[rid] = (
                    "Required information-search node for 8D ADI affected-closure localization."
                )

    if "MSI_OLLAMA_LOCAL" in available:
        qualified.append("MSI_OLLAMA_LOCAL")
        if information_search_required:
            why_selected["MSI_OLLAMA_LOCAL"] = (
                "Model-compute child of MSI_NODE; used only after MSI developer-node "
                "design/experiment evidence has been localized."
            )
    if profile["code"] and "GEMINI_CODE_ASSIST" in available and "GEMINI_CODE_ASSIST" not in denied:
        qualified.append("GEMINI_CODE_ASSIST")
    if profile["heavy_reasoning"] and "GOOGLE_VERTEX_GEMINI" in available and "GOOGLE_VERTEX_GEMINI" not in denied:
        qualified.append("GOOGLE_VERTEX_GEMINI")
    if profile["org_knowledge"] and "GOOGLE_WORKSPACE_ORG" in available:
        qualified.append("GOOGLE_WORKSPACE_ORG")

    if profile["complex_code"] and "GEMINI_CODE_ASSIST" in qualified:
        preferred.append("GEMINI_CODE_ASSIST")
        why_selected["GEMINI_CODE_ASSIST"] = (
            "High-value complex code task matches paid Code Assist SDLC capability."
        )
        if "MSI_OLLAMA_LOCAL" in qualified:
            parallel.append("MSI_OLLAMA_LOCAL")
            why_selected["MSI_OLLAMA_LOCAL"] = "Local reconstruction and verification companion."
    elif "MSI_OLLAMA_LOCAL" in qualified:
        preferred.append("MSI_OLLAMA_LOCAL")
        why_selected["MSI_OLLAMA_LOCAL"] = (
            "Shortest low-transfer local path for current task profile."
        )

    if profile["heavy_reasoning"] and "GOOGLE_VERTEX_GEMINI" in qualified:
        if "GOOGLE_VERTEX_GEMINI" not in preferred:
            parallel.append("GOOGLE_VERTEX_GEMINI")
        why_selected["GOOGLE_VERTEX_GEMINI"] = (
            "Heavy structured reasoning can use cloud candidate compute with static cells."
        )
    if profile["org_knowledge"] and "GOOGLE_WORKSPACE_ORG" in qualified:
        parallel.append("GOOGLE_WORKSPACE_ORG")
        why_selected["GOOGLE_WORKSPACE_ORG"] = (
            "Organization context source; ADI localization required before model handoff."
        )

    for rid in ["TAIJI01_NATIVE_ADI", "TAIJI01_TOTAL_FIELD"]:
        if rid in available:
            qualified.append(rid)
    parallel.extend(
        rid for rid in ["TAIJI01_NATIVE_ADI", "TAIJI01_TOTAL_FIELD"]
        if rid in available
    )
    qualified = list(dict.fromkeys(qualified))
    preferred = list(dict.fromkeys(preferred))
    parallel = list(dict.fromkeys(parallel))
    denied = list(dict.fromkeys(denied))
    hold = list(dict.fromkeys(hold))

    return {
        "STATE": "PASS_RESOURCE_ARBITRATION",
        "TASK_PROFILE": profile,
        "RESOURCE_ROUTER": {
            "ROUTER_ID": "TAIJI_RESOURCE_ROUTER",
            "ROUTER_TYPE": "DISTRIBUTED_COMPUTE_RESOURCE_ROUTER",
            "DECISION_ENGINE": "8D_ADI",
            "FORMAL_EFFECT_BOUNDARY": "TAIJI01_TOTAL_FIELD",
            "INFORMATION_SEARCH_NODES": ["TAIJI01_NODE", "MSI_NODE"],
            "CHILD_RESOURCES": registered,
            "RULE": "Every child is a registered resource; only currently available and policy-qualified children may be selected for a work cell.",
        },
        "RESOURCE_COORDINATES": resources,
        "REGISTERED_SET": registered,
        "AVAILABLE_SET": available,
        "QUALIFIED_SET": qualified,
        "PREFERRED_SET": preferred,
        "PARALLEL_SET": parallel,
        "DENIED_SET": denied,
        "HOLD_SET": hold,
        "WHY_SELECTED": why_selected,
        "WHY_NOT_SELECTED": why_not,
        "PRIMARY_INFORMATION_SEARCH_NODES": PRIMARY_INFORMATION_SEARCH_NODES,
        "RESOURCE_FABRIC_SCOPE": RESOURCE_FABRIC_SCOPE,
        "ROUTER_RESOURCE_SET": [
            rid for rid in available
            if rid.startswith("ROUTER_NODE_") or rid.startswith("ROUTER_SERVICE_")
        ],
        "DESIGN_LOCALIZATION_REQUIRED": bool(
            profile["design"] or profile["code"] or profile["product_design"] or profile["heavy_reasoning"]
        ),
        "DESIGN_SOURCE_SET": (
            ["taiji01", "MSI"]
            if (profile["design"] or profile["code"] or profile["product_design"] or profile["heavy_reasoning"])
            else ["taiji01"]
        ),
        "DUAL_SEARCH_RULE": (
            "For design/architecture/product work, ADI-localize the affected closure on both "
            "taiji01 and MSI before declaring a gap or creating new design. Do not full-scan either node."
        ),
        "MSI_DESIGN_LOCALIZATION_RULE": (
            "ADI-localize MSI developer-device design/experiment/skill evidence; "
            "read only the affected closure, not the whole device."
        ),
        "REQUIRED_HANDOFF": (
            "STATIC_STATE_CELL_PACKET for any cloud/model boundary; "
            "Total Field remains formal effect boundary."
        ),
        "EXPECTED_RETURN": ALLOWED_CLOUD_RETURNS,
        "OBSERVED_AT": _now(),
    }


def build_static_state_cell_envelope(
    intent: str,
    *,
    task_id: str,
    affected_closure: list[str],
    resource_decision: dict[str, Any],
    ttl_seconds: int = 300,
) -> dict[str, Any]:
    intent_hash = hashlib.sha256(intent.encode("utf-8")).hexdigest()
    seed = {
        "task_id": task_id,
        "intent_hash": intent_hash,
        "affected_closure": affected_closure,
        "preferred": resource_decision.get("PREFERRED_SET", []),
    }
    cell_id = "cell:" + _sha(seed)[:24]
    packet = {
        "CELL_ID": cell_id,
        "TASK_CLASS": resource_decision.get("TASK_PROFILE", {}),
        "INTENT_REF": "sha256:" + intent_hash,
        "ADI_COORDINATE": "taiji01:8D_ADI:current-work-cell",
        "SOURCE_COORDINATES": affected_closure,
        "TARGET_COORDINATE": "taiji01:/home/taiji_admin/Taiji_Hub",
        "OBSERVED_FACT_REFS": [],
        "STATE_CODES": ["CANDIDATE_INPUT", "LOCAL_TRUTH_REQUIRED"],
        "SOURCE_HASHES": [],
        "CURRENT_STATE_SUMMARY": "LOCAL_TOTAL_FIELD_OWNS_TRUTH",
        "TARGET_STATE_SUMMARY": "MINIMUM_REQUIRED_DELTA",
        "MINIMUM_REQUIRED_DELTA": "TO_BE_LOCALIZED",
        "INTERFACE_SIGNATURES": [],
        "NECESSARY_CODE_FRAGMENTS": [],
        "DEPENDENCY_REFS": [],
        "PRODUCT_LEVEL_TARGET": None,
        "COMPETITOR_COORDINATES": [],
        "CONSTRAINTS": ["NO_CLOUD_AUTHORITY", "NO_RAW_SECRET", "MINIMUM_CONTEXT"],
        "FORBIDDEN_EFFECTS": ["D8_PASS", "CANONICAL", "DEPLOYED", "DB_WRITE"],
        "OUTPUT_SCHEMA": ALLOWED_CLOUD_RETURNS,
        "RECONSTRUCTION_RULE": "LOCAL_RECONSTRUCTION_REQUIRED",
        "VERIFICATION_RULE": "LOCAL_8D_ADI_AND_DETERMINISTIC_TESTS_REQUIRED",
        "TTL": ttl_seconds,
        "NONCE": secrets.token_hex(12),
    }
    packet["EVIDENCE_HASH"] = _sha(packet)
    return packet
