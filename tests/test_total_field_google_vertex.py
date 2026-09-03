from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from services.gateway.total_field_google_vertex import (
    REQUIRED_ACKNOWLEDGEMENTS,
    _bounded_total_field_header,
    total_field_google_chat,
)


def _context() -> dict:
    return {
        "state": "TOTAL_FIELD_DYNAMIC_CONTEXT_READY",
        "retrieval_method": "8DADI_MEMORY_INDEX_ONLY",
        "packet_sha256": "a" * 64,
        "intent_translation_application_rules": {
            "required_acknowledgements": list(REQUIRED_ACKNOWLEDGEMENTS),
            "network_policy": "LAN_FIRST_VPN_ONLY_WHEN_LAN_UNAVAILABLE",
            "legacy_policy": "V2_1_D4_HISTORY_ONLY",
        },
        "policy": {
            "8dadi_index_only": True,
            "workspace_search": False,
        },
    }


def test_header_keeps_model_non_authoritative() -> None:
    header = _bounded_total_field_header(_context())
    assert header["pull_owner"] == "TOTAL_FIELD"
    assert header["result_state"] == "CANDIDATE_ONLY"
    assert header["execution_authorized"] is False
    assert header["system_mutation_allowed"] is False
    assert header["cloud_may_define_total_field"] is False


def test_header_holds_when_alignment_invariant_is_missing() -> None:
    context = _context()
    context["intent_translation_application_rules"]["required_acknowledgements"].pop()
    with pytest.raises(HTTPException) as exc:
        _bounded_total_field_header(context)
    assert exc.value.detail == "HOLD_8DADI_ALIGNMENT_INVARIANTS_INCOMPLETE"


@patch("services.gateway.total_field_google_vertex._google_access_token", return_value="opaque")
@patch("services.gateway.total_field_google_vertex.requests.post")
@patch("services.gateway.total_field_google_vertex.build_dynamic_context")
def test_total_field_google_pull_uses_8dadi_context(
    build_context: Mock,
    post: Mock,
    token: Mock,
) -> None:
    build_context.return_value = _context()
    response = Mock(status_code=200)
    response.json.return_value = {
        "modelVersion": "gemini-2.5-flash-lite",
        "candidates": [{"content": {"parts": [{"text": "完成建構建議"}]}}],
        "usageMetadata": {
            "promptTokenCount": 20,
            "candidatesTokenCount": 5,
            "totalTokenCount": 25,
        },
    }
    post.return_value = response

    content, usage, metadata = total_field_google_chat(
        [{"role": "user", "content": "請依 8DADI 建構"}],
        {"temperature": 0, "max_tokens": 64},
    )

    assert content == "完成建構建議"
    assert usage["total_tokens"] == 25
    assert metadata["total_field_pull"] is True
    assert metadata["8dadi_index_only"] is True
    assert metadata["candidate_authority"] is False
    assert metadata["execution_authorized"] is False
    sent = post.call_args.kwargs["json"]
    header = sent["systemInstruction"]["parts"][0]["text"]
    assert "W7TP_8DADI_TOTAL_FIELD_GOOGLE_PULL_HEADER_V1" in header
    assert "TOTAL_FIELD" in header


@patch("services.gateway.total_field_google_vertex.build_dynamic_context")
def test_total_field_google_pull_holds_without_8dadi_ready(context: Mock) -> None:
    context.return_value = {"state": "HOLD", "policy": {}}
    with pytest.raises(HTTPException) as exc:
        total_field_google_chat(
            [{"role": "user", "content": "請建構"}],
            {},
        )
    assert exc.value.detail == "HOLD_8DADI_DYNAMIC_CONTEXT_NOT_READY"
