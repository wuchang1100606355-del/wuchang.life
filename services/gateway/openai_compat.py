from __future__ import annotations

import hashlib
import os
import time
import uuid
from typing import Any

import requests
from fastapi import APIRouter, HTTPException, Request


router = APIRouter(tags=["openai-compat"])

OLLAMA_BASE_URL = (
    os.getenv("TAIJI_OLLAMA_BASE_URL")
    or os.getenv("WUCHANG_OLLAMA_URL")
    or os.getenv("OLLAMA_URL")
    or os.getenv("OLLAMA_HOST")
    or "http://127.0.0.1:11434"
).rstrip("/")

DEFAULT_MODEL = (
    os.getenv("TAIJI_MODEL")
    or os.getenv("WUCHANG_DEFAULT_MODEL")
    or "llama3.1:latest"
)

MODEL_ALIASES = {
    "gemini": DEFAULT_MODEL,
    "local": DEFAULT_MODEL,
    "wuchang": DEFAULT_MODEL,
    "sister-j": DEFAULT_MODEL,
}

OLLAMA_TIMEOUT = float(os.getenv("TAIJI_OLLAMA_TIMEOUT", "120"))


@router.get("/v1/models")
def list_models() -> dict[str, Any]:
    names = _available_models()
    if not names:
        names = [DEFAULT_MODEL]

    return {
        "object": "list",
        "data": [
            {
                "id": name,
                "object": "model",
                "created": 0,
                "owned_by": "taiji-local",
            }
            for name in names
        ],
    }


@router.post("/v1/chat/completions")
async def chat_completions(request: Request) -> dict[str, Any]:
    body = await request.json()
    if body.get("stream") is True:
        raise HTTPException(status_code=400, detail="streaming_not_supported_in_phase_b")

    messages = _normalize_messages(body)
    if not messages:
        raise HTTPException(status_code=422, detail="messages_or_prompt_required")

    model = _resolve_model(body.get("model"))
    options = _ollama_options(body)

    data, backend = _chat_with_fallback(model, messages, options)
    content = _extract_content(data)

    return {
        "id": "chatcmpl-" + uuid.uuid4().hex,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": _usage(data, messages, content),
        "taiji": {
            "compat_layer": "phase_b",
            "backend": backend,
            "plaintext_persisted": False,
        },
    }


@router.get("/v1/audio/voices")
def audio_voices() -> dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {
                "id": "wuchang-local",
                "name": "Wuchang Local Voice",
                "provider": "local",
            },
            {
                "id": "silent-review",
                "name": "Silent Review",
                "provider": "local",
            },
        ],
        "taiji": {
            "compat_layer": "phase_b",
            "plaintext_persisted": False,
        },
    }


@router.post("/v1/audio/speech")
async def audio_speech(request: Request) -> dict[str, Any]:
    body = await request.json()
    text = str(body.get("input") or body.get("text") or "")
    return {
        "status": "accepted",
        "object": "audio.speech",
        "mode": "local_tts_candidate",
        "voice": str(body.get("voice") or "wuchang-local"),
        "raw_audio_stored": False,
        "text_digest": hashlib.sha256(text.encode("utf-8")).hexdigest() if text else "",
        "taiji": {
            "compat_layer": "phase_b",
            "plaintext_persisted": False,
        },
    }


def _available_models() -> list[str]:
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []

    models = data.get("models", []) if isinstance(data, dict) else []
    return [item["name"] for item in models if isinstance(item, dict) and item.get("name")]


def _resolve_model(name: Any) -> str:
    requested = str(name or DEFAULT_MODEL)
    requested = MODEL_ALIASES.get(requested, requested)
    names = _available_models()
    if requested in names or not names:
        return requested
    return names[0]


def _normalize_messages(body: dict[str, Any]) -> list[dict[str, str]]:
    messages = body.get("messages")
    if isinstance(messages, list):
        normalized: list[dict[str, str]] = []
        for item in messages:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "user")
            content = _content_to_text(item.get("content"))
            if content:
                normalized.append({"role": role, "content": content})
        if normalized:
            return normalized

    prompt = _content_to_text(body.get("prompt"))
    if prompt:
        return [{"role": "user", "content": prompt}]
    return []


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") in {None, "text"}:
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return " ".join(parts)
    return ""


def _ollama_options(body: dict[str, Any]) -> dict[str, Any]:
    options: dict[str, Any] = {}
    for key in ("temperature", "top_p", "seed"):
        if key in body:
            options[key] = body[key]
    if "max_tokens" in body:
        options["num_predict"] = body["max_tokens"]
    return options


def _chat_with_fallback(
    model: str,
    messages: list[dict[str, str]],
    options: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    chat_payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    if options:
        chat_payload["options"] = options

    try:
        chat_response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=chat_payload,
            timeout=OLLAMA_TIMEOUT,
        )
    except requests.RequestException as exc:
        chat_response = None
        chat_error = str(exc)
    else:
        chat_error = ""
        if chat_response.status_code < 400:
            return _json_or_502(chat_response), "ollama_api_chat"

    generate_payload: dict[str, Any] = {
        "model": model,
        "prompt": _messages_to_prompt(messages),
        "stream": False,
    }
    if options:
        generate_payload["options"] = options

    try:
        generate_response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=generate_payload,
            timeout=OLLAMA_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "ollama_upstream_error",
                "chat_status": getattr(chat_response, "status_code", 0),
                "chat_error": chat_error,
                "generate_error": str(exc),
            },
        ) from exc

    if generate_response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "ollama_upstream_error",
                "chat_status": getattr(chat_response, "status_code", 0),
                "chat_error": chat_error,
                "generate_status": generate_response.status_code,
            },
        )
    return _json_or_502(generate_response), "ollama_api_generate_fallback"


def _json_or_502(response: requests.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="ollama_invalid_json") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="ollama_invalid_payload")
    return data


def _messages_to_prompt(messages: list[dict[str, str]]) -> str:
    lines = [f"{item['role']}: {item['content']}" for item in messages]
    lines.append("assistant:")
    return "\n".join(lines)


def _extract_content(data: dict[str, Any]) -> str:
    message = data.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content
    response = data.get("response")
    if isinstance(response, str):
        return response
    return ""


def _usage(data: dict[str, Any], messages: list[dict[str, str]], content: str) -> dict[str, int]:
    prompt_text = _messages_to_prompt(messages)
    prompt_tokens = _count_or_estimate(data.get("prompt_eval_count"), prompt_text)
    completion_tokens = _count_or_estimate(data.get("eval_count"), content)
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }


def _count_or_estimate(value: Any, text: str) -> int:
    if isinstance(value, int) and value >= 0:
        return value
    return max(1, len(text.split()))
