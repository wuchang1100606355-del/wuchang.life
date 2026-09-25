"""Deterministic always-on red-team drift monitor for the shared runtime.

The monitor performs no model inference and never echoes inspected input.  It
only returns stable alert codes for Total Field review.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from tools.total_field.w7tp_field_application_runtime import AUTHORITY_KEYS, SENSITIVE_KEYS


CLIENT_DRIFT_RULES: tuple[dict[str, Any], ...] = (
    {
        "code": "GT_CORE_DEFINITION_DRIFT",
        "severity": "CRITICAL",
        "markers": (
            "生成式傳輸是檔案搬運",
            "生成式傳輸等於檔案搬運",
            "雲端同步就是生成式傳輸",
            "任意檔案都能小封包下載",
            "用生成式傳輸下載任意檔案",
            "下載解密就是生成式傳輸",
        ),
    },
    {
        "code": "TOTAL_FIELD_AUTHORITY_DRIFT",
        "severity": "CRITICAL",
        "markers": (
            "ai 自動核准",
            "ai直接核准",
            "略過總場",
            "繞過總場",
            "自設 d8",
            "跳過人工審查",
            "正式執行權交給 ai",
        ),
    },
    {
        "code": "SERVER_LLM_BOUNDARY_DRIFT",
        "severity": "CRITICAL",
        "markers": (
            "伺服器執行 llm",
            "伺服器運行 llm",
            "taiji01 執行 llm",
            "taiji01 運行 llm",
            "雲端執行模型",
            "server-side llm",
        ),
    },
    {
        "code": "UNSAFE_SIDE_EFFECT_DRIFT",
        "severity": "HIGH",
        "markers": (
            "直接部署",
            "直接重啟",
            "直接寫入資料庫",
            "直接改路由器",
            "略過確認直接執行",
        ),
    },
    {
        "code": "PUBLIC_TRUST_OVERCLAIM_DRIFT",
        "severity": "HIGH",
        "markers": (
            "已核准發明專利",
            "google 背書",
            "政府背書",
        ),
    },
)

EXTRA_SENSITIVE_KEYS = frozenset(
    {
        "access_token",
        "client_secret",
        "email",
        "member_name",
        "password",
        "payment_data",
        "phone",
        "raw_audio",
        "raw_image",
        "resident_name",
    }
)
EMAIL_PATTERN = re.compile(r"(?<![\w.-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])")
BEARER_PATTERN = re.compile(r"\bBearer\s+[A-Za-z0-9._~-]{8,}", re.IGNORECASE)
PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")


def client_drift_rules() -> list[dict[str, Any]]:
    """Return the safe public subset used for device-local live preflight."""

    return [
        {
            "code": rule["code"],
            "severity": rule["severity"],
            "markers": list(rule["markers"]),
        }
        for rule in CLIENT_DRIFT_RULES
    ]


def _inspect(value: Any, text_parts: list[str], keys: set[str]) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            keys.add(str(key).strip().casefold())
            _inspect(item, text_parts, keys)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _inspect(item, text_parts, keys)
    elif isinstance(value, str):
        text_parts.append(value.casefold())


def evaluate_drift(value: Any) -> dict[str, Any]:
    """Inspect one state transition without retaining or returning its content."""

    text_parts: list[str] = []
    keys: set[str] = set()
    _inspect(value, text_parts, keys)
    text = " ".join(text_parts)
    alerts: list[dict[str, str]] = []

    for rule in CLIENT_DRIFT_RULES:
        if any(marker.casefold() in text for marker in rule["markers"]):
            alerts.append(
                {
                    "code": str(rule["code"]),
                    "severity": str(rule["severity"]),
                    "required_action": "HOLD_AND_TOTAL_FIELD_REVIEW",
                }
            )

    sensitive_keys = SENSITIVE_KEYS | EXTRA_SENSITIVE_KEYS
    if keys.intersection(sensitive_keys) or EMAIL_PATTERN.search(text) or BEARER_PATTERN.search(text) or PRIVATE_KEY_PATTERN.search(text):
        alerts.append(
            {
                "code": "SENSITIVE_DATA_BOUNDARY_ALERT",
                "severity": "CRITICAL",
                "required_action": "BLOCK_INPUT_AND_REMOVE_SENSITIVE_DATA",
            }
        )
    if keys.intersection(AUTHORITY_KEYS):
        alerts.append(
            {
                "code": "AUTHORITY_FIELD_ESCALATION_ALERT",
                "severity": "CRITICAL",
                "required_action": "BLOCK_AND_TOTAL_FIELD_REVIEW",
            }
        )

    unique = {item["code"]: item for item in alerts}
    ordered = [unique[code] for code in sorted(unique)]
    return {
        "schema_version": "W7TP-REDTEAM-DRIFT-MONITOR/1.0",
        "mode": "ALWAYS_ON_EVERY_STATE_TRANSITION",
        "perspective": "REDTEAM",
        "status": "DRIFT_ALERT" if ordered else "MONITORING_CLEAR",
        "alert_count": len(ordered),
        "alerts": ordered,
        "checked_boundaries": [
            "GT_CORE_DEFINITION",
            "TOTAL_FIELD_AUTHORITY",
            "USER_DEVICE_ONLY_LLM",
            "NO_UNAUTHORIZED_SIDE_EFFECTS",
            "SENSITIVE_DATA",
            "PUBLIC_TRUST_CLAIMS",
        ],
        "decision_authority": "LOCAL_TOTAL_FIELD_ONLY",
        "llm_execution": "NONE_DETERMINISTIC_RULES",
        "input_retained": False,
        "input_echoed": False,
    }
