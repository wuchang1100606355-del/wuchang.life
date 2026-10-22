#!/usr/bin/env python3
"""MSI local-LLM endpoint routing: LAN first, Windows Tailscale fallback."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Any


MSI_LAN_IP = "192.168.50.82"
MSI_WINDOWS_TAILSCALE_IP = "100.105.82.28"
DEPRECATED_MSI_WSL_TAILSCALE_IP = "100.84.204.114"
MSI_LAN_OLLAMA_URL = f"http://{MSI_LAN_IP}:11435"  # existing LAN bridge, verified /api/tags and /api/show
MSI_WINDOWS_TAILSCALE_OLLAMA_URL = f"http://{MSI_WINDOWS_TAILSCALE_IP}:11434"
MSI_WSL_REVERSE_SSH_OLLAMA_URL = "http://127.0.0.1:11435"
DEPRECATED_MSI_WSL_TAILSCALE_OLLAMA_URL = f"http://{DEPRECATED_MSI_WSL_TAILSCALE_IP}:11434"

MODEL_BINDINGS = {
    "xiaoj-local-dev:v2.3": {
        "digest": "5f7563e28e7f8a55433a3978add47a08a08a684e2b2ba3cd0b23e4a1c88e4e9c",
        "system_marker": "W7TP_XIAOJ_TOTAL_FIELD_MODEL_ORGAN_PREFIX_V2_3",
    },
}

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
    {
        "ref": "MSI_WSL_REVERSE_SSH_FALLBACK",
        "url": MSI_WSL_REVERSE_SSH_OLLAMA_URL,
        "transport": "SSH_REVERSE_TUNNEL",
        "priority": 30,
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
                "priority": 40,
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
    record = next(
        (
            item
            for item in models
            if isinstance(item, Mapping)
            and (item.get("name") == model or item.get("model") == model)
        ),
        None,
    )
    if record is None:
        return False
    binding = MODEL_BINDINGS.get(model)
    if binding is None:
        return True
    if record.get("digest") != binding["digest"]:
        return False

    show_request = urllib.request.Request(
        url.rstrip("/") + "/api/show",
        data=json.dumps({"model": model}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(show_request, timeout=timeout) as response:
            show = json.loads(response.read().decode("utf-8"))
    except (
        OSError,
        TimeoutError,
        urllib.error.URLError,
        json.JSONDecodeError,
    ):
        return False
    return (
        isinstance(show, Mapping)
        and binding["system_marker"] in str(show.get("system") or "")
    )


def lan_host_reachable(*, timeout: float = 1.0) -> bool:
    """Verify existing MSI LAN host access, independent of model health.

    A model mismatch or unavailable API is not a physical LAN outage.
    No VPN or reverse tunnel may be selected while a LAN service responds.
    """
    for port in (11435, 22):
        try:
            with socket.create_connection((MSI_LAN_IP, port), timeout=timeout):
                return True
        except OSError:
            continue
    return False


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
        if not ok and item["transport"] == "LAN" and lan_host_reachable(
            timeout=min(timeout, 1.0),
        ):
            return {
                "state": "HOLD_MSI_LAN_MODEL_NOT_READY_NO_FALLBACK",
                "selected_url": None,
                "selected_ref": None,
                "selected_transport": None,
                "model": model,
                "lan_first": True,
                "lan_reachable": True,
                "fallback_blocked_while_lan_reachable": True,
                "deprecated_wsl_tailscale_selected": False,
                "attempts": attempts,
            }
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
    "MSI_WSL_REVERSE_SSH_OLLAMA_URL",
    "endpoint_candidates",
    "endpoint_has_model",
    "lan_host_reachable",
    "resolve_msi_ollama_url",
]
