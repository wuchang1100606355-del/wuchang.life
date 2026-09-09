from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from services.gateway.openai_compat import (
    TOTAL_FIELD_GOOGLE_MODEL,
    _google_availability_failure,
    chat_completions,
    hearing_intent,
    perception_status,
    vision_analyze,
)


class _Request:
    def __init__(self, body: dict) -> None:
        self._body = body

    async def json(self) -> dict:
        return self._body


def test_google_failure_classifier_excludes_8dadi_hold() -> None:
    assert (
        _google_availability_failure(
            HTTPException(status_code=503, detail="HOLD_GOOGLE_VERTEX_TRANSPORT_FAILED")
        )
        == "HOLD_GOOGLE_VERTEX_TRANSPORT_FAILED"
    )
    assert (
        _google_availability_failure(
            HTTPException(status_code=503, detail="HOLD_8DADI_DYNAMIC_CONTEXT_NOT_READY")
        )
        is None
    )


def test_google_unavailable_uses_local_inference_without_claiming_d6() -> None:
    body = {
        "model": "w7tp-cloud",
        "messages": [{"role": "user", "content": "自然語言測試"}],
        "max_tokens": 32,
    }
    local_data = {
        "message": {"content": "本機推理已接續"},
        "prompt_eval_count": 4,
        "eval_count": 3,
    }
    with (
        patch(
            "services.gateway.openai_compat._resolve_model",
            side_effect=[TOTAL_FIELD_GOOGLE_MODEL, "xiaoj:latest"],
        ),
        patch(
            "services.gateway.openai_compat.total_field_google_chat",
            side_effect=HTTPException(
                status_code=502,
                detail="HOLD_GOOGLE_VERTEX_TRANSPORT_FAILED",
            ),
        ),
        patch(
            "services.gateway.openai_compat._chat_with_fallback",
            return_value=(local_data, "ollama_api_chat"),
        ),
        patch(
            "services.gateway.openai_compat.build_dynamic_context",
            return_value={
                "state": "TOTAL_FIELD_DYNAMIC_CONTEXT_READY",
                "retrieval_method": "8DADI_MEMORY_INDEX_ONLY",
                "packet_sha256": "a" * 64,
                "founder_intent_projection": {"state": "CURRENT"},
                "context_items": [],
                "policy": {"8dadi_index_only": True, "workspace_search": False},
            },
        ),
        patch(
            "services.gateway.openai_compat.scan_operation",
            side_effect=[
                {
                    "state": "PASS_TOTAL_FIELD_RULE_APPLICATION_REVIEW",
                    "coordinates": {
                        "branch": "main",
                        "head": "b" * 40,
                        "tree": "c" * 40,
                    },
                    "work_target_sha256": "d" * 64,
                },
                {
                    "state": "PASS_TOTAL_FIELD_RULE_APPLICATION_REVIEW",
                    "work_target_sha256": "d" * 64,
                },
            ],
        ),
        patch(
            "services.gateway.openai_compat.reviewed_prompt_text",
            return_value='{"state":"REVIEWED_IN_MEMORY_AI_CONTEXT"}',
        ),
    ):
        result = asyncio.run(chat_completions(_Request(body)))

    assert result["choices"][0]["message"]["content"] == "本機推理已接續"
    assert "[W7TP fallback" not in result["choices"][0]["message"]["content"]
    assert result["taiji"]["inference_route"] == "LOCAL_AFTER_GOOGLE_UNAVAILABLE"
    assert result["taiji"]["generative_transmission_used"] is False
    assert result["taiji"]["inference_route_is_generative_transmission"] is False
    assert result["taiji"]["8dadi_dynamic_context_used"] is True
    assert result["taiji"]["mandatory_application_review"] is True
    assert result["taiji"]["work_target_sha256"] == "d" * 64


def test_alignment_failure_does_not_fall_back_to_model() -> None:
    body = {
        "model": "w7tp-cloud",
        "messages": [{"role": "user", "content": "自然語言測試"}],
    }
    with (
        patch(
            "services.gateway.openai_compat._resolve_model",
            return_value=TOTAL_FIELD_GOOGLE_MODEL,
        ),
        patch(
            "services.gateway.openai_compat.total_field_google_chat",
            side_effect=HTTPException(
                status_code=503,
                detail="HOLD_8DADI_DYNAMIC_CONTEXT_NOT_READY",
            ),
        ),
        pytest.raises(HTTPException) as exc,
    ):
        asyncio.run(chat_completions(_Request(body)))
    assert exc.value.detail == "HOLD_8DADI_DYNAMIC_CONTEXT_NOT_READY"


def test_hearing_ingress_keeps_raw_audio_at_source_node() -> None:
    completed = {
        "choices": [{"message": {"content": "您好"}}],
        "taiji": {},
    }
    with patch(
        "services.gateway.openai_compat._complete_chat",
        return_value=completed,
    ):
        result = asyncio.run(
            hearing_intent(
                _Request(
                    {
                        "transcript": "小J你好",
                        "source_node": "taiji04_sunmi_pos",
                        "application": "cafe_ordering",
                    }
                )
            )
        )
    hearing = result["taiji"]["hearing"]
    assert hearing["raw_audio_received"] is False
    assert hearing["raw_audio_stored"] is False
    assert hearing["source_node"] == "taiji04_sunmi_pos"
    assert hearing["execution_authorized"] is False


def test_perception_status_does_not_probe_ddns_when_lan_is_available() -> None:
    def http_health(url: str) -> dict:
        assert "p1430563.ds1.nxt.net.tw" not in url
        return {"ok": True, "state": "REACHABLE", "status_code": 200}

    with (
        patch("services.gateway.openai_compat._http_health", side_effect=http_health),
        patch(
            "services.gateway.openai_compat._tcp_health",
            return_value={"ok": True, "state": "REACHABLE"},
        ),
        patch(
            "services.gateway.openai_compat._route_source_ip",
            return_value="192.168.50.82",
        ),
    ):
        result = perception_status()
    route = result["D3_coordinate"]["route"]
    assert route["lan_observed"] is True
    assert route["vpn_or_ddns_escalated"] is False
    assert result["D6_generative_transmission"]["used"] is False


def test_vision_analysis_uses_memory_only_local_frame() -> None:
    png_1x1 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
        "/x8AAusB9Wl2bVQAAAAASUVORK5CYII="
    )
    local_data = {
        "message": {"content": "畫面中有一個像素。"},
        "prompt_eval_count": 4,
        "eval_count": 5,
    }
    with (
        patch("services.gateway.openai_compat._resolve_model", return_value="xiaoj:latest"),
        patch(
            "services.gateway.openai_compat._attach_local_total_field_context",
            return_value=([{"role": "user", "content": "描述畫面"}], {"8dadi_index_only": True}),
        ),
        patch(
            "services.gateway.openai_compat._chat_with_fallback",
            return_value=(local_data, "ollama_api_chat"),
        ),
    ):
        result = asyncio.run(
            vision_analyze(
                _Request(
                    {
                        "source_node": "store_lilin_nvr",
                        "prompt": "描述畫面",
                        "image_base64": png_1x1,
                    }
                )
            )
        )
    assert result["result"] == "畫面中有一個像素。"
    assert result["taiji"]["image_persisted"] is False
    assert result["taiji"]["generative_transmission_used"] is False
    assert result["taiji"]["execution_authorized"] is False
