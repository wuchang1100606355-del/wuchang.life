from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import requests
from fastapi import HTTPException

from tools.total_field_dynamic_context import build_dynamic_context


PROJECT_ROOT = Path(
    os.getenv("TAIJI_PROJECT_ROOT", "/home/taiji_admin/Taiji_Hub")
).resolve()
VERTEX_PROJECT = os.getenv("TAIJI_VERTEX_PROJECT", "my-j-483304")
VERTEX_LOCATION = os.getenv("TAIJI_VERTEX_LOCATION", "us-central1")
VERTEX_MODEL = os.getenv("TAIJI_VERTEX_MODEL", "gemini-2.5-flash-lite")
TOTAL_FIELD_GOOGLE_MODEL = os.getenv(
    "TAIJI_TOTAL_FIELD_GOOGLE_MODEL", "w7tp-total-field-google"
)
VERTEX_TIMEOUT = float(os.getenv("TAIJI_VERTEX_TIMEOUT", "120"))
MAX_CONTEXT_ITEMS = int(os.getenv("TAIJI_VERTEX_MAX_CONTEXT_ITEMS", "4"))
WINDOWS_POWERSHELL = Path(
    "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
)
WINDOWS_GCLOUD = (
    r"C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.ps1"
)

REQUIRED_ACKNOWLEDGEMENTS = (
    "AI_IS_NOT_AUTHORITY",
    "UNKNOWN_WILL_NOT_BE_INVENTED",
    "CANDIDATE_WILL_NOT_BE_PROMOTED_AUTOMATICALLY",
    "LEGACY_WILL_NOT_DEFINE_TARGET",
    "EXECUTION_REQUIRES_REOBSERVATION",
    "LAN_PRECEDES_VPN",
)


def _last_user_text(messages: list[dict[str, str]]) -> str:
    for item in reversed(messages):
        if item.get("role") == "user" and item.get("content"):
            return str(item["content"])
    return ""


def _google_access_token() -> str:
    commands = [
        ["gcloud", "auth", "print-access-token"],
    ]
    if WINDOWS_POWERSHELL.is_file():
        commands.append(
            [
                str(WINDOWS_POWERSHELL),
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                f"& '{WINDOWS_GCLOUD}' auth print-access-token",
            ]
        )

    for command in commands:
        try:
            result = subprocess.run(
                command,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            continue
        token = result.stdout.strip()
        if result.returncode == 0 and len(token) >= 80:
            return token

    raise HTTPException(
        status_code=503,
        detail="HOLD_GOOGLE_IDENTITY_TOKEN_UNAVAILABLE",
    )


def _vertex_contents(messages: list[dict[str, str]]) -> tuple[list[dict[str, Any]], str]:
    system_parts: list[str] = []
    contents: list[dict[str, Any]] = []
    for item in messages:
        role = str(item.get("role") or "user")
        text = str(item.get("content") or "").strip()
        if not text:
            continue
        if role == "system":
            system_parts.append(text)
            continue
        contents.append(
            {
                "role": "model" if role == "assistant" else "user",
                "parts": [{"text": text}],
            }
        )
    return contents, "\n\n".join(system_parts)


def _bounded_total_field_header(context: dict[str, Any]) -> dict[str, Any]:
    rules = context.get("intent_translation_application_rules") or {}
    required = tuple(rules.get("required_acknowledgements") or ())
    if not set(REQUIRED_ACKNOWLEDGEMENTS).issubset(set(required)):
        raise HTTPException(
            status_code=503,
            detail="HOLD_8DADI_ALIGNMENT_INVARIANTS_INCOMPLETE",
        )
    return {
        "schema_id": "W7TP_8DADI_TOTAL_FIELD_GOOGLE_PULL_HEADER_V1",
        "pull_owner": "TOTAL_FIELD",
        "provider_role": "REPLACEABLE_CLOUD_REASONING_ORGAN",
        "result_state": "CANDIDATE_ONLY",
        "execution_authorized": False,
        "system_mutation_allowed": False,
        "canonical_write_allowed": False,
        "active_pointer_write_allowed": False,
        "cloud_may_define_total_field": False,
        "user_visible_language": "zh-TW",
        "english_terms_require_zh_tw_translation": True,
        "required_acknowledgements": list(REQUIRED_ACKNOWLEDGEMENTS),
        "8dadi_context_packet_sha256": context.get("packet_sha256"),
        "8dadi_retrieval_method": context.get("retrieval_method"),
        "network_policy": rules.get("network_policy"),
        "legacy_policy": rules.get("legacy_policy"),
    }


def total_field_google_chat(
    messages: list[dict[str, str]],
    body: dict[str, Any],
) -> tuple[str, dict[str, int], dict[str, Any]]:
    query = _last_user_text(messages)
    if not query:
        raise HTTPException(status_code=422, detail="TOTAL_FIELD_PULL_REQUIRES_USER_INTENT")

    context = build_dynamic_context(
        root=PROJECT_ROOT,
        query=query,
        max_items=MAX_CONTEXT_ITEMS,
        identity_class="founder",
    )
    policy = context.get("policy") or {}
    if (
        context.get("state") != "TOTAL_FIELD_DYNAMIC_CONTEXT_READY"
        or context.get("retrieval_method") != "8DADI_MEMORY_INDEX_ONLY"
        or policy.get("8dadi_index_only") is not True
        or policy.get("workspace_search") is not False
    ):
        raise HTTPException(
            status_code=503,
            detail="HOLD_8DADI_DYNAMIC_CONTEXT_NOT_READY",
        )

    contents, supplied_system = _vertex_contents(messages)
    if not contents:
        raise HTTPException(status_code=422, detail="TOTAL_FIELD_PULL_REQUIRES_CONTENT")
    header = _bounded_total_field_header(context)
    system_instruction = {
        "role": "system",
        "contract": header,
        "instruction": (
            "你是由總場拉取的可替換 Google 雲端推理器。依使用者最新意圖提供繁體中文結果。"
            "你不是權威，不得宣稱已寫入、已部署、已啟用或已完成未重新觀測的效果。"
        ),
        "upstream_system_instruction": supplied_system,
    }

    max_tokens = body.get("max_tokens", 1024)
    try:
        max_tokens = max(1, min(int(max_tokens), 4096))
    except (TypeError, ValueError):
        max_tokens = 1024
    try:
        temperature = float(body.get("temperature", 0.2))
    except (TypeError, ValueError):
        temperature = 0.2

    vertex_payload = {
        "systemInstruction": {
            "parts": [
                {
                    "text": json.dumps(
                        system_instruction,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                }
            ]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": max(0.0, min(temperature, 2.0)),
            "maxOutputTokens": max_tokens,
        },
    }

    endpoint = (
        f"https://{VERTEX_LOCATION}-aiplatform.googleapis.com/v1/projects/"
        f"{VERTEX_PROJECT}/locations/{VERTEX_LOCATION}/publishers/google/models/"
        f"{VERTEX_MODEL}:generateContent"
    )
    try:
        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {_google_access_token()}",
                "Content-Type": "application/json",
            },
            json=vertex_payload,
            timeout=VERTEX_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail="HOLD_GOOGLE_VERTEX_TRANSPORT_FAILED",
        ) from exc
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "HOLD_GOOGLE_VERTEX_REJECTED",
                "status_code": response.status_code,
            },
        )
    try:
        data = response.json()
        parts = data["candidates"][0]["content"]["parts"]
        content = "".join(
            str(item.get("text") or "") for item in parts if isinstance(item, dict)
        ).strip()
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="HOLD_GOOGLE_VERTEX_RESPONSE_INVALID",
        ) from exc
    if not content:
        raise HTTPException(status_code=502, detail="HOLD_GOOGLE_VERTEX_EMPTY_RESULT")

    raw_usage = data.get("usageMetadata") or {}
    prompt_tokens = int(raw_usage.get("promptTokenCount") or 0)
    completion_tokens = int(raw_usage.get("candidatesTokenCount") or 0)
    usage = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": int(raw_usage.get("totalTokenCount") or (prompt_tokens + completion_tokens)),
    }
    metadata = {
        "backend": "total_field_google_vertex",
        "provider_model": data.get("modelVersion") or VERTEX_MODEL,
        "total_field_pull": True,
        "8dadi_index_only": True,
        "8dadi_context_packet_sha256": context.get("packet_sha256"),
        "candidate_authority": False,
        "execution_authorized": False,
        "plaintext_persisted": False,
    }
    return content, usage, metadata
