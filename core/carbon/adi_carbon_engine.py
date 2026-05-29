# 五常智慧雲 ADI / 碳排放計算核心
LAMBDA_C = 0.000475

def calculate_carbon_credit(local_tokens: int, cloud_tokens_avoided: int, energy_factor: float = LAMBDA_C):
    saved_units = max(int(cloud_tokens_avoided) - int(local_tokens), 0)
    carbon_saved = saved_units * energy_factor
    return {
        "adi_version": "Wuchang-ADI-v1",
        "local_tokens": int(local_tokens),
        "cloud_tokens_avoided": int(cloud_tokens_avoided),
        "saved_compute_units": saved_units,
        "carbon_saved_kgco2e": round(carbon_saved, 6),
        "method": "local-first AI avoided cloud inference estimate"
    }
