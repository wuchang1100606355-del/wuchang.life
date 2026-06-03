# 五常智慧雲｜AI 海馬迴 + AI 小腦 碳排放計算
# 目的：估算本地 AI、分片、無明文上下文、冷熱碟映射相較雲端推論之碳節省

from datetime import datetime, timezone

# 可日後改成台電/實測係數
GRID_KGCO2E_PER_KWH = 0.494
LOCAL_GPU_WATT = 115
LOCAL_CPU_IO_WATT = 18
CLOUD_GPU_WATT_EQUIV = 420
NETWORK_WATT_EQUIV = 35

def kwh(watt: float, seconds: float):
    return watt * seconds / 3600 / 1000

def calculate_wuchang_carbon(
    prompt_tokens: int = 1000,
    response_tokens: int = 1000,
    local_runtime_sec: float = 30,
    cloud_runtime_sec: float = 30,
    shard_count: int = 5,
    cold_write_mb: float = 0,
    local_gpu_watt: float = LOCAL_GPU_WATT,
    cloud_gpu_watt: float = CLOUD_GPU_WATT_EQUIV,
):
    total_tokens = int(prompt_tokens) + int(response_tokens)

    local_compute_kwh = kwh(local_gpu_watt, local_runtime_sec)
    local_io_kwh = kwh(LOCAL_CPU_IO_WATT, local_runtime_sec)
    local_total_kwh = local_compute_kwh + local_io_kwh

    cloud_compute_kwh = kwh(cloud_gpu_watt, cloud_runtime_sec)
    cloud_network_kwh = kwh(NETWORK_WATT_EQUIV, cloud_runtime_sec)
    cloud_total_kwh = cloud_compute_kwh + cloud_network_kwh

    local_kgco2e = local_total_kwh * GRID_KGCO2E_PER_KWH
    cloud_kgco2e = cloud_total_kwh * GRID_KGCO2E_PER_KWH
    saved_kgco2e = max(cloud_kgco2e - local_kgco2e, 0)

    return {
        "version": "Wuchang-CarbonAccounting-Hippocampus-Cerebellum-v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "basis": {
            "ai_cerebellum": [
                "five_d_memory_cleanup",
                "resource_prediction",
                "system_io_management",
                "hot_warm_cold_storage_mapping"
            ],
            "ai_hippocampus": [
                "metric_small_model_topology",
                "nameless_context_router",
                "sqlite_memory_index",
                "semantic_shattering",
                "router_usb_dead_letter_box"
            ],
            "storage_policy": {
                "hot_disk": "系統空間",
                "warm_disk": "本機工作/索引空間",
                "cold_disk": "Google Drive 組織共用空間/五常共用空間"
            }
        },
        "input": {
            "prompt_tokens": prompt_tokens,
            "response_tokens": response_tokens,
            "total_tokens": total_tokens,
            "local_runtime_sec": local_runtime_sec,
            "cloud_runtime_sec": cloud_runtime_sec,
            "shard_count": shard_count,
            "cold_write_mb": cold_write_mb
        },
        "energy": {
            "local_kwh": round(local_total_kwh, 8),
            "cloud_reference_kwh": round(cloud_total_kwh, 8),
            "avoided_kwh": round(max(cloud_total_kwh - local_total_kwh, 0), 8)
        },
        "carbon": {
            "grid_factor_kgco2e_per_kwh": GRID_KGCO2E_PER_KWH,
            "local_kgco2e": round(local_kgco2e, 8),
            "cloud_reference_kgco2e": round(cloud_kgco2e, 8),
            "saved_kgco2e": round(saved_kgco2e, 8),
            "reduction_percent": round((saved_kgco2e / cloud_kgco2e * 100), 2) if cloud_kgco2e else 0
        },
        "claim_safe_wording": "Estimated avoided emissions under defined local-first workload; requires measured wattage for formal ESG reporting."
    }
