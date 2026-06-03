# 五常智慧雲｜一問雙路徑減碳資訊收集 + 用量透明揭示 + 滅碳量

import hashlib, math

CARBON_FACTOR_KGCO2E_PER_KWH = 0.494

def _h(x: str) -> str:
    return hashlib.sha256(str(x).encode()).hexdigest()

def estimate_usage(question: str = "什麼是低碳AI？", user_allow_cloud: bool = False, response_tokens_est: int = 800):
    q_bytes = len(question.encode("utf-8"))
    prompt_tokens_est = max(1, math.ceil(q_bytes / 4))
    response_tokens_est = int(response_tokens_est)

    local_processing_tokens = prompt_tokens_est + response_tokens_est
    cloud_processing_tokens = 0 if not user_allow_cloud else prompt_tokens_est + response_tokens_est

    local_input_bytes = q_bytes
    cloud_transmit_bytes = 0 if not user_allow_cloud else q_bytes

    total_processing_tokens = local_processing_tokens + cloud_processing_tokens
    total_transmit_bytes = local_input_bytes + cloud_transmit_bytes

    estimated_local_kwh = local_processing_tokens * 0.00000008
    estimated_cloud_reference_kwh = max(total_processing_tokens, local_processing_tokens) * 0.00000028
    avoided_kwh = max(estimated_cloud_reference_kwh - estimated_local_kwh, 0)
    carbon_saved_kgco2e = avoided_kwh * CARBON_FACTOR_KGCO2E_PER_KWH
    reduction_percent_est = (avoided_kwh / estimated_cloud_reference_kwh * 100) if estimated_cloud_reference_kwh else 0

    return {
        "version": "Wuchang-UsageDisclosure-v2",
        "question_token": _h(question)[:16],
        "plaintext_retained": False,
        "usage": {
            "prompt_tokens_est": prompt_tokens_est,
            "response_tokens_est": response_tokens_est,
            "local_processing_tokens": local_processing_tokens,
            "cloud_processing_tokens": cloud_processing_tokens,
            "total_processing_tokens": total_processing_tokens
        },
        "transmission": {
            "local_input_bytes": local_input_bytes,
            "cloud_transmit_bytes": cloud_transmit_bytes,
            "total_transmit_bytes": total_transmit_bytes,
            "cloud_enabled": bool(user_allow_cloud)
        },
        "carbon_reduction": {
            "estimated_local_kwh": round(estimated_local_kwh, 8),
            "estimated_cloud_reference_kwh": round(estimated_cloud_reference_kwh, 8),
            "avoided_kwh": round(avoided_kwh, 8),
            "carbon_factor_kgco2e_per_kwh": CARBON_FACTOR_KGCO2E_PER_KWH,
            "carbon_saved_kgco2e": round(carbon_saved_kgco2e, 8),
            "reduction_percent_est": round(reduction_percent_est, 2)
        },
        "disclosure": {
            "must_show_to_user": True,
            "local_route_default": True,
            "cloud_requires_user_authorization": True,
            "sensitive_data_to_cloud_allowed": False,
            "must_show_usage": True,
            "must_show_transmission": True,
            "must_show_carbon_reduction": True
        }
    }

def dual_path_manifest(question: str = "什麼是低碳AI？", user_allow_cloud: bool = False):
    usage = estimate_usage(question, user_allow_cloud)
    return {
        "version": "Wuchang-DualPath-CarbonCollection-v2",
        "question_token": usage["question_token"],
        "purpose": "research_demo_carbon_aware_ai_collection",
        "routes": {
            "path_A_local": {
                "enabled": True,
                "default": True,
                "model_layer": "Open WebUI / Ollama / wuchang_gpu_brain",
                "data_policy": "local_first",
                "usage_counted_as": "local_processing_tokens"
            },
            "path_B_cloud_free_trial": {
                "enabled": bool(user_allow_cloud),
                "requires_user_authorization": True,
                "model_layer": "Gemini / OpenAI / Claude / DeepSeek / OpenRouter / legal free-or-trial APIs",
                "data_policy": "desensitized_summary_or_metric_fragment_only",
                "usage_counted_as": "cloud_processing_tokens_and_cloud_transmit_bytes"
            }
        },
        "usage_disclosure": usage,
        "public_notice": "All trial/free cloud model use must disclose estimated local processing, cloud transfer, cloud processing, total usage, avoided kWh, carbon saved, and reduction percentage."
    }

def dual_path_notice():
    return {
        "version": "Wuchang-FreeModel-UsePolicy-v2",
        "title": "免費/試用雲端模型串接與用量揭示政策",
        "rules": [
            "本地模型為預設路徑",
            "雲端免費或試用模型僅供研究、展示、比較與受控備援",
            "不轉售免費額度",
            "不繞過平台速率限制",
            "不送出個資、敏感資料或完整社區原始資料",
            "送雲前須經使用者授權、脫敏、摘要或度規分片",
            "每次呼叫必須明示使用量、傳輸量、本地處理量、雲端處理量、總量、預估節電量、滅碳量與減碳比例",
            "每次雲端轉嫁應寫入碳帳本與路由紀錄"
        ],
        "required_user_visible_metrics": [
            "local_processing_tokens",
            "cloud_processing_tokens",
            "cloud_transmit_bytes",
            "total_processing_tokens",
            "total_transmit_bytes",
            "avoided_kwh",
            "carbon_saved_kgco2e",
            "reduction_percent_est"
        ]
    }
