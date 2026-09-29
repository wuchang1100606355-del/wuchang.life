"""Cloud capability adapters. Every provider returns Candidate-only output."""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from typing import Any

import requests

from tools.total_field.xiaoj_fusion_rules import CANDIDATE_ONLY_AUTHORITY, CLOUD_SOURCE
from tools.total_field_candidate_gateway import _forbidden_authority_claim_paths


def _candidate_only(
    value: Mapping[str, Any],
    *,
    provider: str,
    provider_model: str | None = None,
) -> dict[str, Any]:
    raw = dict(value)
    forbidden = _forbidden_authority_claim_paths(raw)
    if forbidden:
        raise ValueError("cloud_candidate_returned_forbidden_authority:" + ",".join(forbidden))
    raw["source"] = CLOUD_SOURCE
    raw["authority"] = CANDIDATE_ONLY_AUTHORITY
    raw["candidate_type"] = "Candidate"
    metadata = raw.setdefault("metadata", {})
    if isinstance(metadata, dict):
        metadata["provider"] = provider
        if provider_model:
            metadata["provider_model"] = provider_model
        metadata["cloud_inference_is_d6"] = False
        metadata["external_effect"] = False
    return raw


class GCPCloudCandidateProvider:
    """Existing Google/Vertex candidate adapter. A live client is injected elsewhere."""

    provider_name = "GOOGLE_VERTEX"

    def __init__(self, client: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None) -> None:
        self.client = client
        self.calls: list[dict[str, Any]] = []
        self.state = "READY_WITH_INJECTED_CLIENT" if client else "HOLD_LIVE_CLIENT_NOT_BOUND"

    def provide_candidate(self, packet: Mapping[str, Any]) -> dict[str, Any] | None:
        if self.client is None:
            return None
        self.calls.append(dict(packet))
        raw = self.client(packet)
        return _candidate_only(raw, provider=self.provider_name)

    def get_candidate(self, packet: Mapping[str, Any]) -> dict[str, Any] | None:
        return self.provide_candidate(packet)

    def __call__(self, packet: Mapping[str, Any]) -> dict[str, Any] | None:
        return self.provide_candidate(packet)


class OllamaCloudCandidateProvider:
    """Ollama Cloud adapter using the local Ollama API as the transport."""

    provider_name = "OLLAMA_CLOUD"

    def __init__(
        self,
        client: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
        *,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.client = client
        self.model = (model or os.getenv("TAIJI_OLLAMA_CLOUD_MODEL", "")).strip()
        self.base_url = (
            base_url
            or os.getenv("TAIJI_OLLAMA_BASE_URL")
            or "http://127.0.0.1:11434"
        ).rstrip("/")
        self.timeout = timeout
        self.calls: list[dict[str, Any]] = []
        self.state = (
            "READY_WITH_INJECTED_CLIENT"
            if client
            else ("READY_MODEL_REF_CONFIGURED" if self.model else "HOLD_PROVIDER_MODEL_UNCONFIGURED")
        )

    def provide_candidate(self, packet: Mapping[str, Any]) -> dict[str, Any] | None:
        if self.client is not None:
            self.calls.append(dict(packet))
            raw = self.client(packet)
            return _candidate_only(raw, provider=self.provider_name, provider_model=self.model or None)
        if not self.model:
            return None

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a replaceable cloud capability source. "
                        "Return JSON only with patch, quality_score, assumptions. "
                        "Do not claim identity, authority, execution, deployment, canonical or committed state."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                },
            ],
            "format": "json",
            "stream": False,
            "think": False,
        }
        self.calls.append(dict(packet))
        try:
            response = requests.post(
                self.base_url + "/api/chat",
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException:
            self.state = "HOLD_OLLAMA_CLOUD_TRANSPORT_FAILED"
            return None
        if response.status_code >= 400:
            self.state = "HOLD_OLLAMA_CLOUD_REJECTED"
            return None
        try:
            data = response.json()
            content = str((data.get("message") or {}).get("content") or data.get("response") or "")
            raw = json.loads(content)
            if not isinstance(raw, Mapping):
                raise TypeError("candidate_not_mapping")
        except (ValueError, TypeError):
            self.state = "HOLD_OLLAMA_CLOUD_RESPONSE_INVALID"
            return None
        self.state = "PASS_CANDIDATE_RECEIVED"
        return _candidate_only(raw, provider=self.provider_name, provider_model=self.model)

    def get_candidate(self, packet: Mapping[str, Any]) -> dict[str, Any] | None:
        return self.provide_candidate(packet)

    def __call__(self, packet: Mapping[str, Any]) -> dict[str, Any] | None:
        return self.provide_candidate(packet)


def registered_cloud_capabilities() -> dict[str, Any]:
    """Expose capability state without triggering an external request."""
    ollama_cloud = OllamaCloudCandidateProvider()
    return {
        "GOOGLE_VERTEX": {
            "authority": CANDIDATE_ONLY_AUTHORITY,
            "cloud_inference_is_d6": False,
            "state": "EXISTING_SEPARATE_GATEWAY_ROUTE",
        },
        "OLLAMA_CLOUD": {
            "authority": CANDIDATE_ONLY_AUTHORITY,
            "cloud_inference_is_d6": False,
            "state": ollama_cloud.state,
            "model_ref_configured": bool(ollama_cloud.model),
        },
    }


# The legacy agent discovers a module-level provider callable.  Define it only
# when an explicit Ollama Cloud model ref exists, so an unconfigured machine
# keeps the prior HOLD_NO_CLOUD_PROVIDER behavior instead of attempting egress.
if os.getenv("TAIJI_OLLAMA_CLOUD_MODEL", "").strip():
    def complete_candidate(packet: Mapping[str, Any]) -> dict[str, Any]:
        provider = OllamaCloudCandidateProvider()
        candidate = provider.provide_candidate(packet)
        if candidate is None:
            raise RuntimeError(provider.state)
        return candidate
