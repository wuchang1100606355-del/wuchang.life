#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Google Cloud LLM candidate provider with no Total Field authority.

Authentication is delegated to Google Application Default Credentials.  This
module never opens, serializes, or logs the credential file.  Network access
occurs only when ``generate_candidate`` is explicitly called; tests inject a
FakeCloudProvider and never instantiate this transport.
"""

from __future__ import annotations

import json
import math
import os
import re
from typing import Any, Mapping, cast


SOURCE_MODE = "LLM_PUSH"
PROVIDER_REF = "gcp"
MODEL_REF = "cloud-llm"
GOOGLE_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
FORBIDDEN_OUTPUT_KEYS = frozenset(
    {
        "committed",
        "commit_applied",
        "tfid",
        "total_field_hash",
        "tfs",
        "db_write",
        "deploy",
        "restart",
        "router_write",
    }
)
SENSITIVE_INPUT_KEYS = frozenset(
    {
        "api_key",
        "credential",
        "member_plaintext",
        "password",
        "private_key",
        "raw_key",
        "raw_secret",
        "raw_token",
        "secret",
        "token",
    }
)
RESOURCE_TOKEN = re.compile(r"^[A-Za-z0-9._:-]+$")


class CloudCandidateProviderError(ValueError):
    """Stable cloud-provider failure without response or credential content."""

    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


def _copy_json(value: Any) -> Any:
    """Strictly detach a finite JSON value."""

    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        return json.loads(
            encoded,
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise CloudCandidateProviderError("CLOUD_INPUT_NOT_JSON_COMPATIBLE") from exc


def _matching_key_path(
    value: Any, names: frozenset[str], path: str = "$"
) -> str | None:
    """Return only the first structural path matching protected key names."""

    if isinstance(value, dict):
        for key in sorted(value):
            child = f"{path}.{key}"
            if key.casefold() in names:
                return child
            found = _matching_key_path(value[key], names, child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found = _matching_key_path(item, names, f"{path}[{index}]")
            if found is not None:
                return found
    return None


def _forbidden_output_path(value: Any, path: str = "$") -> str | None:
    """Allow only the schema-required false commit declaration in 8D-GTE."""

    if isinstance(value, dict):
        for key in sorted(value):
            child = f"{path}.{key}"
            normalized = key.casefold()
            if normalized in FORBIDDEN_OUTPUT_KEYS:
                schema_declaration = (
                    child == "$.gte.verification.commit_applied"
                    and value[key] is False
                )
                if not schema_declaration:
                    return child
            found = _forbidden_output_path(value[key], child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found = _forbidden_output_path(item, f"{path}[{index}]")
            if found is not None:
                return found
    return None


def _required_ref(context: Mapping[str, Any], key: str) -> str:
    value = context.get(key)
    if not isinstance(value, str) or not value:
        raise CloudCandidateProviderError("CLOUD_REQUIRED_REFERENCE_MISSING")
    return value


class CloudCandidateProvider:
    """Executable Vertex AI REST provider that emits candidate-only envelopes."""

    def __init__(self, *, timeout_seconds: int = 60) -> None:
        if not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool):
            raise CloudCandidateProviderError("CLOUD_TIMEOUT_INVALID")
        if timeout_seconds < 1 or timeout_seconds > 300:
            raise CloudCandidateProviderError("CLOUD_TIMEOUT_INVALID")
        self._timeout_seconds = timeout_seconds

    def _authorized_session(self) -> tuple[Any, str]:
        """Create an ADC session without reading or exposing credential material."""

        if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            raise CloudCandidateProviderError(
                "CLOUD_APPLICATION_CREDENTIALS_NOT_CONFIGURED"
            )
        try:
            import google.auth
            from google.auth.transport.requests import AuthorizedSession

            credentials, project_id = google.auth.default(scopes=[GOOGLE_SCOPE])
            session = AuthorizedSession(credentials)
        except Exception as exc:
            raise CloudCandidateProviderError("CLOUD_ADC_INITIALIZATION_FAILED") from exc
        if not isinstance(project_id, str) or not project_id:
            project_id = ""
        return session, project_id

    def _endpoint(
        self, context: Mapping[str, Any], adc_project_id: str
    ) -> tuple[str, str]:
        project_id = context.get("cloud_project_id", adc_project_id)
        location = context.get(
            "cloud_location", os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        )
        model_name = context.get(
            "cloud_model_name", os.environ.get("GOOGLE_CLOUD_LLM_MODEL")
        )
        for value in (project_id, location, model_name):
            if not isinstance(value, str) or not value or not RESOURCE_TOKEN.fullmatch(value):
                raise CloudCandidateProviderError("CLOUD_RESOURCE_CONFIGURATION_INVALID")
        host = (
            "aiplatform.googleapis.com"
            if location == "global"
            else f"{location}-aiplatform.googleapis.com"
        )
        endpoint = (
            f"https://{host}/v1/projects/{project_id}/locations/{location}"
            f"/publishers/google/models/{model_name}:generateContent"
        )
        return endpoint, cast(str, model_name)

    def generate_candidate(self, prompt: str, context: dict) -> dict:
        """Generate one JSON candidate while withholding all commit authority."""

        if not isinstance(prompt, str) or not prompt.strip():
            raise CloudCandidateProviderError("CLOUD_PROMPT_REQUIRED")
        if not isinstance(context, dict):
            raise CloudCandidateProviderError("CLOUD_CONTEXT_REQUIRED")
        context_copy = _copy_json(context)
        if not isinstance(context_copy, dict):
            raise CloudCandidateProviderError("CLOUD_CONTEXT_REQUIRED")
        event_ref = _required_ref(context_copy, "event_ref")
        observation_domain_ref = _required_ref(
            context_copy, "observation_domain_ref"
        )
        rule_ref = _required_ref(context_copy, "rule_ref")
        cloud_context = context_copy.get("cloud_context", {})
        if not isinstance(cloud_context, dict):
            raise CloudCandidateProviderError("CLOUD_CONTEXT_REQUIRED")
        if _matching_key_path(cloud_context, SENSITIVE_INPUT_KEYS) is not None:
            raise CloudCandidateProviderError("CLOUD_SENSITIVE_CONTEXT_BLOCKED")

        session, adc_project_id = self._authorized_session()
        endpoint, _ = self._endpoint(context_copy, adc_project_id)
        instruction = (
            "Return one JSON object with keys candidate and confidence. "
            "candidate must remain a proposal and must not contain committed, "
            "commit_applied, TFS, TFID, Total Field Hash, DB write, deploy, "
            "restart, or router-write claims."
        )
        request_body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": json.dumps(
                                {
                                    "instruction": instruction,
                                    "prompt": prompt,
                                    "context": cloud_context,
                                },
                                sort_keys=True,
                                ensure_ascii=False,
                                separators=(",", ":"),
                                allow_nan=False,
                            )
                        }
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
            },
        }
        try:
            response = session.post(
                endpoint, json=request_body, timeout=self._timeout_seconds
            )
            response.raise_for_status()
            response_body = response.json()
            text = response_body["candidates"][0]["content"]["parts"][0]["text"]
            generated = json.loads(
                text,
                parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
            )
        except Exception as exc:
            raise CloudCandidateProviderError("CLOUD_GENERATION_FAILED") from exc
        if not isinstance(generated, dict):
            raise CloudCandidateProviderError("CLOUD_RESPONSE_SCHEMA_INVALID")
        candidate = generated.get("candidate")
        confidence = generated.get("confidence")
        if not isinstance(candidate, dict):
            raise CloudCandidateProviderError("CLOUD_RESPONSE_SCHEMA_INVALID")
        if (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not math.isfinite(float(confidence))
            or not 0 <= float(confidence) <= 1
        ):
            raise CloudCandidateProviderError("CLOUD_CONFIDENCE_INVALID")
        if _forbidden_output_path(candidate) is not None:
            raise CloudCandidateProviderError("CLOUD_FORBIDDEN_AUTHORITY_OUTPUT")
        candidate_copy = _copy_json(candidate)
        return {
            "source_mode": SOURCE_MODE,
            "provider_ref": PROVIDER_REF,
            "model_ref": MODEL_REF,
            "candidate": candidate_copy,
            "confidence": float(confidence),
            "event_ref": event_ref,
            "observation_domain_ref": observation_domain_ref,
            "rule_ref": rule_ref,
            "candidate_only": True,
        }

    def generate_fill_response(
        self,
        packet: Mapping[str, Any],
        transport_context: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Fill one governed packet without exposing the Total Field rule core."""

        from tools.total_field_cloud_fill_packet import (
            build_cloud_fill_response,
            validate_cloud_fill_request,
        )

        validated = validate_cloud_fill_request(packet)
        locked = cast(dict[str, Any], validated["locked"])
        context_copy = _copy_json(dict(transport_context))
        if not isinstance(context_copy, dict):
            raise CloudCandidateProviderError("CLOUD_CONTEXT_REQUIRED")
        if _matching_key_path(context_copy, SENSITIVE_INPUT_KEYS) is not None:
            raise CloudCandidateProviderError("CLOUD_SENSITIVE_CONTEXT_BLOCKED")
        session, adc_project_id = self._authorized_session()
        endpoint, configured_model = self._endpoint(context_copy, adc_project_id)
        model_ref = context_copy.get("cloud_model_ref", MODEL_REF)
        model_version = context_copy.get("cloud_model_version")
        if not isinstance(model_ref, str) or not model_ref:
            raise CloudCandidateProviderError("CLOUD_RESOURCE_CONFIGURATION_INVALID")
        if not isinstance(model_version, str) or not model_version:
            raise CloudCandidateProviderError("CLOUD_RESOURCE_CONFIGURATION_INVALID")
        if PROVIDER_REF not in locked["allowed_provider_refs"]:
            raise CloudCandidateProviderError("CLOUD_PROVIDER_NOT_AUTHORIZED")
        if f"{model_ref}@{model_version}" not in locked["allowed_model_refs"]:
            raise CloudCandidateProviderError("CLOUD_MODEL_VERSION_NOT_AUTHORIZED")
        cloud_input = {
            "instruction": (
                "Fill only the declared cloud_fillable fields. Return concise rationale, "
                "assumptions, uncertainties, risk candidates, verification candidates, "
                "and evidence references. Do not return chain of thought or any authority, "
                "commit, deployment, canonical, pointer, TFS, TFID, or Total Field claim."
            ),
            "packet_id": locked["packet_id"],
            "question_type_ref": locked["question_type_ref"],
            "sanitized_question": locked["sanitized_question"],
            "product_output_contract": locked["product_output_contract"],
            "static_rule_capsule_ref": locked["static_rule_capsule_ref"],
            "dynamic_rule_projection": locked["dynamic_rule_projection"],
            "allowed_information_scope": locked["allowed_information_scope"],
            "fillable_paths": locked["fillable_paths"],
            "reconstruction_conditions": locked["reconstruction_conditions"],
            "verification_conditions": locked["verification_conditions"],
            "max_output_tokens": locked["max_output_tokens"],
        }
        request_body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": json.dumps(
                                cloud_input,
                                sort_keys=True,
                                ensure_ascii=False,
                                separators=(",", ":"),
                                allow_nan=False,
                            )
                        }
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": locked["max_output_tokens"],
                "responseMimeType": "application/json",
            },
        }
        try:
            response = session.post(
                endpoint, json=request_body, timeout=self._timeout_seconds
            )
            response.raise_for_status()
            response_body = response.json()
            text = response_body["candidates"][0]["content"]["parts"][0]["text"]
            generated = json.loads(
                text,
                parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
            )
            usage = response_body["usageMetadata"]
            input_tokens = usage["promptTokenCount"]
            output_tokens = usage["candidatesTokenCount"]
        except Exception as exc:
            raise CloudCandidateProviderError("CLOUD_FILL_GENERATION_FAILED") from exc
        if not isinstance(generated, dict):
            raise CloudCandidateProviderError("CLOUD_FILL_RESPONSE_SCHEMA_INVALID")
        if (
            not isinstance(input_tokens, int)
            or isinstance(input_tokens, bool)
            or not isinstance(output_tokens, int)
            or isinstance(output_tokens, bool)
        ):
            raise CloudCandidateProviderError("CLOUD_USAGE_ACCOUNTING_INVALID")
        if configured_model != context_copy.get("cloud_model_name"):
            raise CloudCandidateProviderError("CLOUD_MODEL_CONFIGURATION_DRIFT")
        return cast(
            dict[str, Any],
            build_cloud_fill_response(
                validated,
                cloud_fillable=generated,
                provider_ref=PROVIDER_REF,
                model_ref=model_ref,
                model_version=model_version,
                model_input_tokens=input_tokens,
                model_output_tokens=output_tokens,
            ),
        )


__all__ = ["CloudCandidateProvider", "CloudCandidateProviderError"]
