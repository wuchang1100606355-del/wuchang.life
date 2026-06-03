# 五常智慧雲｜雲端模型受控轉嫁層
# 原則：本地優先、使用者授權、脫敏後轉送、不可預設外洩

import os, time, hashlib

def _h(x: str) -> str:
    return hashlib.sha256(str(x).encode()).hexdigest()

def cloud_router_state():
    return {
        "version": "Wuchang-CloudModelRouter-v1",
        "name": "雲端模型受控轉嫁層",
        "status": "active",
        "policy": {
            "local_first": True,
            "cloud_requires_user_authorization": True,
            "pii_must_be_desensitized": True,
            "plaintext_context_upload": False,
            "tool_invocation_user_controlled": True,
            "carbon_accounting_required": True
        },
        "providers": {
            "google_workspace_gemini": {
                "enabled": bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")),
                "account_hint": "admin@wuchang.life",
                "use_case": "high_variance_reasoning_after_desensitization"
            },
            "openai_or_other_cloud": {
                "enabled": bool(os.getenv("OPENAI_API_KEY")),
                "use_case": "optional external model, only after authorization"
            },
            "local_ollama": {
                "enabled": True,
                "endpoint": "http://wuchang_gpu_brain:11434",
                "use_case": "default local inference"
            }
        }
    }

def decide_model_route(
    prompt_tokens: int = 1000,
    sensitivity: str = "normal",
    variance: float = 0.2,
    user_allow_cloud: bool = False,
    local_memory_ok: bool = True
):
    prompt_tokens = int(prompt_tokens)
    variance = float(variance)

    if sensitivity in ["pii", "private", "sensitive"]:
        route = "local_only"
        reason = "sensitive_data_must_remain_local"
    elif not user_allow_cloud:
        route = "local_only"
        reason = "user_has_not_authorized_cloud"
    elif local_memory_ok and variance < 0.6:
        route = "local_ollama"
        reason = "local_model_sufficient"
    else:
        route = "controlled_cloud_model"
        reason = "high_variance_or_resource_shortage_with_user_authorization"

    return {
        "version": "Wuchang-CloudRouteDecision-v1",
        "prompt_tokens": prompt_tokens,
        "sensitivity": sensitivity,
        "variance": variance,
        "user_allow_cloud": bool(user_allow_cloud),
        "local_memory_ok": bool(local_memory_ok),
        "route": route,
        "reason": reason,
        "upload_plaintext": False,
        "required_preprocess": [
            "five_d_state_check",
            "pii_desensitization",
            "semantic_fragmentation",
            "nameless_context_routing"
        ] if route == "controlled_cloud_model" else [],
        "carbon_accounting": "required"
    }

def cloud_payload_manifest(prompt: str = "五常智慧雲", user_allow_cloud: bool = False):
    token = _h(prompt)[:16]
    if not user_allow_cloud:
        return {
            "version": "Wuchang-CloudPayloadManifest-v1",
            "allowed": False,
            "reason": "user_authorization_required",
            "object_token": token
        }
    return {
        "version": "Wuchang-CloudPayloadManifest-v1",
        "allowed": True,
        "object_token": token,
        "plaintext_included": False,
        "payload_type": "desensitized_metric_fragment",
        "rules": [
            "no_raw_pii",
            "no_full_plaintext_context",
            "only_metric_code_or_summary",
            "log_to_carbon_accounting",
            "log_to_ai_hippocampus"
        ]
    }
