"""Rules for the XiaoJ single-8B local model and governed cloud candidates."""

from __future__ import annotations

from typing import Any


LOCAL_PRIMARY_MODEL: dict[str, Any] = {
    "name": "W7TP XiaoJ Qwen3 Abliterated 8B",
    "provider": "ollama_local",
    "model": "xiaoj:latest",
    "base_model": "huihui_ai/qwen3-abliterated:8b",
    "physical_model_count": 1,
    "roles": ["chat", "reasoning", "edit", "apply"],
    "contextLength": 8192,
    "maxTokens": 2048,
    "temperature": 0.2,
}

# Compatibility name only. There is no separate physical frontbrain model.
FRONTBRAIN_MODEL = LOCAL_PRIMARY_MODEL

BASE_SYSTEM_MESSAGE_LINES = [
    "請一律使用自然繁體中文回答。",
    "程式碼、指令、路徑及識別名稱可以保留原文。",
    "先直接說結果，再說必要原因。",
    "不得把模型輸出宣稱為執行權威。",
    "不得自動啟動 TTS。",
]

DEFAULT_ACCEPTANCE_CRITERIA: dict[str, Any] = {
    "language": "zh-TW",
    "single_human_response": True,
    "quality_threshold": 0.8,
    "no_tts": True,
}

PROTECTED_PATH_PREFIXES = (
    "identity",
    "owner_identity",
    "owner_ref",
    "membership",
    "role",
    "authority",
    "permission",
    "evidence",
    "provenance",
    "decision",
    "committed",
    "committed_state",
    "canonical",
    "formal_hash",
    "hash",
    "execution",
    "credential",
    "credentials",
    "token",
    "private_key",
    "secret",
    "adc",
    "certificate",
    "member_plaintext",
    "biometric",
)

CLOUD_FILLABLE_PATHS = (
    "draft.continuation",
    "draft.style_polish",
    "draft.missing_local_detail",
    "response.natural_zh_tw",
)

CLOUD_REQUEST_ALLOWED_KEYS = frozenset(
    {
        "request_hash",
        "rule_capsule_hash",
        "locked_fields",
        "fillable_paths",
        "minimal_deidentified_context",
        "acceptance_criteria",
        "nonce",
        "ttl_seconds",
        "single_use",
        "return_schema",
    }
)

FORBIDDEN_CLOUD_CONTEXT_KEYS = frozenset(
    {
        "adc",
        "api_key",
        "authorization",
        "biometric_template",
        "certificate_pin",
        "credential",
        "credentials",
        "member_plaintext",
        "password",
        "private_key",
        "raw_credential",
        "secret",
        "token",
    }
)

FORBIDDEN_AUTHORITY_CLAIM_KEYS = frozenset(
    {
        "allow",
        "allow_status",
        "committed",
        "committed_state",
        "deployment_authority",
        "execution_authority",
        "final_decision",
        "formal_hash",
        "identity_elevation",
        "owner_identity",
        "rule_change_effect",
    }
)

CANDIDATE_ONLY_AUTHORITY = "CANDIDATE_ONLY"
LOCAL_SOURCE = "local_8b"
FRONTBRAIN_SOURCE = LOCAL_SOURCE
# Kept only so old evidence can be rejected/contained by the candidate gateway.
BACKBRAIN_SOURCE = "backbrain_disabled_legacy"
CLOUD_SOURCE = "cloud"
RULE_CAPSULE_REF = "W7TP-XIAOJ-SINGLE-8B-CLOUD-CANDIDATE-CORE/2.3"
