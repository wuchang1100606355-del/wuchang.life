"""Deterministic Traditional-Chinese views; JSON is never the only UX."""

from __future__ import annotations

from typing import Mapping


INTERFACE_AUTHORITY_BOUNDARY_ZH_TW = "Open WebUI 只是操作介面，不是總場權威、正典或最終決策者。"


def render_execution_lease_zh_tw(lease: Mapping[str, object]) -> str:
    request = lease.get("resource_request")
    if not isinstance(request, Mapping):
        request = {}
    node_id = str(lease.get("node_id", "未知"))
    engine = request.get("container_engine") or "尚未指定"
    return "\n".join(
        [
            f"意圖：為總場候選任務在 {node_id} 保留經驗證的節點資源。",
            "總場決策理由：8D_ADI 已依同一份 NodeManifest／NodeResourceState snapshot 產生 ISSUED ExecutionLease；節點尚須驗證有效 D8 authority。",
            f"選中節點／容器：{node_id}／容器引擎 {engine}；具體 canary 尚由簽章 task envelope 綁定。",
            (
                "資源依據："
                f"CPU {request.get('cpu_count', '未知')}、RAM {request.get('ram_bytes', '未知')} bytes、"
                f"disk {request.get('disk_bytes', '未知')} bytes、GPU {request.get('gpu_count', 0)} 張／"
                f"{request.get('gpu_memory_mib', 0)} MiB、PIDs 上限 {request.get('pids_limit', '未知')}。"
            ),
            f"實際結果：ExecutionLease 狀態為 {lease.get('state', '未知')}；尚未進入 RESERVE／EXECUTE／VERIFY。",
            "未知／風險：具體任務意圖、容器身分與即時資源仍須由同一份簽章 envelope 與節點即時 snapshot 交叉驗證；任一漂移即 HOLD。",
            INTERFACE_AUTHORITY_BOUNDARY_ZH_TW,
        ]
    )


def render_placement_zh_tw(decision: Mapping[str, object]) -> str:
    resource = decision.get("node_resource_state")
    request = decision.get("resource_request")
    selected = str(decision.get("selected_node_id", "未知"))
    if not isinstance(resource, Mapping):
        resource = {}
    if not isinstance(request, Mapping):
        request = {}
    engines = decision.get("node_manifest")
    engine_text = "未觀測"
    if isinstance(engines, Mapping) and isinstance(engines.get("container_engines"), list):
        engine_text = "、".join(str(item) for item in engines["container_engines"]) or "未觀測"
    rejected = decision.get("rejected_nodes")
    unknown = "無已知排除項"
    if isinstance(rejected, list) and rejected:
        unknown = "；".join(
            f"{item.get('node_id', '未知')}:{item.get('reason_code', 'UNKNOWN')}"
            for item in rejected
            if isinstance(item, Mapping)
        ) or "有節點狀態未知"
    return "\n".join(
        [
            "意圖：依節點即時能力為總場控制任務選擇最小足夠資源。",
            f"總場決策理由：8D_ADI 候選排序選中 {selected}；此結果仍須有效總場 D8 authority 與 ExecutionLease 才能執行。",
            f"選中節點／容器能力：{selected}；容器引擎 {engine_text}。",
            (
                "資源依據："
                f"CPU {resource.get('cpu_count', '未知')}（需求 {request.get('cpu_count', '未知')}）；"
                f"RAM 可用 {resource.get('ram_available_bytes', '未知')} bytes（需求 {request.get('ram_bytes', '未知')}）；"
                f"disk 可用 {resource.get('disk_free_bytes', '未知')} bytes（需求 {request.get('disk_bytes', '未知')}）；"
                f"GPU {resource.get('gpu_count', '未知')} 張/{resource.get('gpu_memory_mib', '未知')} MiB。"
            ),
            "實際結果：尚未執行；目前只形成 CANDIDATE placement 與 ISSUED ExecutionLease。",
            f"未知／風險：{unknown}；snapshot 漂移、authority 過期或 scope 不足一律 HOLD。",
            INTERFACE_AUTHORITY_BOUNDARY_ZH_TW,
        ]
    )


def render_task_envelope_zh_tw(envelope: Mapping[str, object]) -> str:
    dimensions = envelope.get("dimensions")
    if not isinstance(dimensions, Mapping):
        return "意圖：未知。\n總場決策：HOLD，8D envelope 不完整。\n" + INTERFACE_AUTHORITY_BOUNDARY_ZH_TW
    d1 = dimensions.get("D1_INTENT")
    d2 = dimensions.get("D2_STATE")
    d3 = dimensions.get("D3_COORDINATE")
    d5 = dimensions.get("D5_EXECUTION")
    if not isinstance(d1, Mapping):
        d1 = {}
    if not isinstance(d2, Mapping):
        d2 = {}
    if not isinstance(d3, Mapping):
        d3 = {}
    if not isinstance(d5, Mapping):
        d5 = {}
    parameters = d5.get("parameters")
    if not isinstance(parameters, Mapping):
        parameters = {}
    target = parameters.get("name") or parameters.get("unit") or "未指定 canary"
    request = d2.get("resource_request")
    if not isinstance(request, Mapping):
        request = {}
    return "\n".join(
        [
            f"意圖：{d1.get('intent', '未知')}。",
            "總場決策理由：只在 taiji01 總場控制端簽發、8D_ADI 為主要決策引擎，節點端仍須逐項驗證 authority/scope/TTL/nonce/hash/Ed25519。",
            f"選中節點／容器：{d3.get('target_node_id', '未知')}／{target}；操作 {d5.get('operation', '未知')}。",
            (
                "資源依據："
                f"CPU {request.get('cpu_count', '未知')}、RAM {request.get('ram_bytes', '未知')} bytes、"
                f"disk {request.get('disk_bytes', '未知')} bytes、GPU {request.get('gpu_count', 0)} 張。"
            ),
            "實際結果：尚未執行；ExecutionLease 為 ISSUED，必須經 RESERVE／EXECUTE／VERIFY，並沿用 ACKNOWLEDGED／RUNNING／RESULT_CANDIDATE／ACCEPTED 狀態鏈。",
            "未知／風險：任何 live authority、節點 snapshot、canary label 或驗證結果不符即 HOLD；既有正式服務不可變更。",
            INTERFACE_AUTHORITY_BOUNDARY_ZH_TW,
        ]
    )


def render_receipt_zh_tw(
    *,
    phase: str,
    state: str,
    node_id: str,
    task_id: str,
    detail: Mapping[str, object],
) -> str:
    operation = detail.get("operation", "待定")
    target = detail.get("target_identity", "尚未綁定")
    request = detail.get("resource_request")
    if isinstance(request, Mapping):
        resource_text = (
            f"CPU {request.get('cpu_count', '未知')}、RAM {request.get('ram_bytes', '未知')} bytes、"
            f"disk {request.get('disk_bytes', '未知')} bytes、GPU {request.get('gpu_count', 0)} 張、"
            f"PIDs {request.get('pids_limit', '未知')}"
        )
    else:
        resource_text = "綁定 envelope 的 NodeResourceState 與 ExecutionLease"
    reason = detail.get("reason_code")
    risk = f"HOLD 原因 {reason}" if reason else "仍為候選證據；不升格 canonical 或 final authority"
    return "\n".join(
        [
            f"意圖：執行總場任務 {task_id}。",
            f"總場決策理由：taiji01 簽發的 D8 envelope 已通過前置驗證，進入 {phase}。",
            f"選中節點／容器：{node_id}／{target}；操作 {operation}。",
            f"資源依據：{resource_text}；階段 {phase}。",
            f"實際結果：{state}。",
            f"未知／風險：{risk}；既有正式服務不可變更。",
            INTERFACE_AUTHORITY_BOUNDARY_ZH_TW,
        ]
    )
