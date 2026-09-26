#!/usr/bin/env python3
"""MSI local-LLM endpoint routing: LAN first, Windows Tailscale fallback."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Any


MSI_LAN_IP = "192.168.50.82"
MSI_WINDOWS_TAILSCALE_IP = "100.105.82.28"
DEPRECATED_MSI_WSL_TAILSCALE_IP = "100.84.204.114"
MSI_LAN_OLLAMA_URL = f"http://{MSI_LAN_IP}:11434"
MSI_WINDOWS_TAILSCALE_OLLAMA_URL = f"http://{MSI_WINDOWS_TAILSCALE_IP}:11434"
DEPRECATED_MSI_WSL_TAILSCALE_OLLAMA_URL = f"http://{DEPRECATED_MSI_WSL_TAILSCALE_IP}:11434"

BASE_ENDPOINTS = (
    {
        "ref": "MSI_LAN_PRIMARY",
        "url": MSI_LAN_OLLAMA_URL,
        "transport": "LAN",
        "priority": 10,
    },
    {
        "ref": "MSI_WINDOWS_TAILSCALE_FALLBACK",
        "url": MSI_WINDOWS_TAILSCALE_OLLAMA_URL,
        "transport": "TAILSCALE_WINDOWS",
        "priority": 20,
    },
)


def endpoint_candidates(override_url: str | None = None) -> list[dict[str, Any]]:
    """Return ordered candidates; deprecated WSL Tailscale is never admitted."""
    candidates = [dict(item) for item in BASE_ENDPOINTS]
    override = str(override_url or "").strip().rstrip("/")
    if (
        override
        and override != DEPRECATED_MSI_WSL_TAILSCALE_OLLAMA_URL
        and all(item["url"] != override for item in candidates)
    ):
        candidates.append(
            {
                "ref": "MSI_OPERATOR_OVERRIDE_FALLBACK",
                "url": override,
                "transport": "OPERATOR_OVERRIDE",
                "priority": 30,
            }
        )
    return sorted(candidates, key=lambda item: int(item["priority"]))


def endpoint_has_model(url: str, model: str, timeout: float = 2.0) -> bool:
    request = urllib.request.Request(url.rstrip("/") + "/api/tags", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            value = json.loads(response.read().decode("utf-8"))
    except (
        OSError,
        TimeoutError,
        urllib.error.URLError,
        json.JSONDecodeError,
    ):
        return False
    models = value.get("models") if isinstance(value, Mapping) else None
    if not isinstance(models, list):
        return False
    return any(
        isinstance(item, Mapping)
        and (item.get("name") == model or item.get("model") == model)
        for item in models
    )


def resolve_msi_ollama_url(
    model: str,
    *,
    override_url: str | None = None,
    timeout: float = 2.0,
) -> dict[str, Any]:
    """Resolve the first live endpoint without ever selecting deprecated WSL TS."""
    attempts: list[dict[str, Any]] = []
    for item in endpoint_candidates(override_url):
        ok = endpoint_has_model(str(item["url"]), model, timeout=timeout)
        attempts.append(
            {
                "ref": item["ref"],
                "transport": item["transport"],
                "url": item["url"],
                "available": ok,
            }
        )
        if ok:
            return {
                "state": "PASS_MSI_LOCAL_LLM_ROUTE",
                "selected_url": item["url"],
                "selected_ref": item["ref"],
                "selected_transport": item["transport"],
                "model": model,
                "lan_first": True,
                "deprecated_wsl_tailscale_selected": False,
                "attempts": attempts,
            }
    return {
        "state": "HOLD_MSI_LOCAL_LLM_UNREACHABLE",
        "selected_url": None,
        "selected_ref": None,
        "selected_transport": None,
        "model": model,
        "lan_first": True,
        "deprecated_wsl_tailscale_selected": False,
        "attempts": attempts,
    }


__all__ = [
    "DEPRECATED_MSI_WSL_TAILSCALE_IP",
    "DEPRECATED_MSI_WSL_TAILSCALE_OLLAMA_URL",
    "MSI_LAN_IP",
    "MSI_LAN_OLLAMA_URL",
    "MSI_WINDOWS_TAILSCALE_IP",
    "MSI_WINDOWS_TAILSCALE_OLLAMA_URL",
    "endpoint_candidates",
    "endpoint_has_model",
    "resolve_msi_ollama_url",
]
