from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import socket
import time
import uuid
from pathlib import Path
from typing import Any

import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from services.gateway.total_field_google_vertex import (
    TOTAL_FIELD_GOOGLE_MODEL,
    total_field_google_chat,
)
from tools.total_field_dynamic_context import build_dynamic_context
from tools.total_field_mandatory_application_gate import (
    PASS_STATE as MANDATORY_APPLICATION_PASS,
    reviewed_prompt_text,
    scan_operation,
)


router = APIRouter(tags=["openai-compat"])

OLLAMA_BASE_URL = (
    os.getenv("TAIJI_OLLAMA_BASE_URL")
    or os.getenv("WUCHANG_OLLAMA_URL")
    or os.getenv("OLLAMA_URL")
    or os.getenv("OLLAMA_HOST")
    or "http://127.0.0.1:11434"
).rstrip("/")

LOCAL_FALLBACK_MODEL = os.getenv(
    "TAIJI_TOTAL_FIELD_LOCAL_FALLBACK_MODEL", "xiaoj:latest"
)
DEFAULT_MODEL = (
    os.getenv("TAIJI_MODEL")
    or os.getenv("WUCHANG_DEFAULT_MODEL")
    or LOCAL_FALLBACK_MODEL
)

MODEL_ALIASES = {
    "gemini": TOTAL_FIELD_GOOGLE_MODEL,
    "w7tp-cloud": TOTAL_FIELD_GOOGLE_MODEL,
    "google": TOTAL_FIELD_GOOGLE_MODEL,
    "local": DEFAULT_MODEL,
    "wuchang": DEFAULT_MODEL,
    "sister-j": DEFAULT_MODEL,
}

OLLAMA_TIMEOUT = float(os.getenv("TAIJI_OLLAMA_TIMEOUT", "120"))
PROJECT_ROOT = Path(
    os.getenv("TAIJI_PROJECT_ROOT", "/home/taiji_admin/Taiji_Hub")
).resolve()
LOCAL_MODEL_MANIFEST_ROOT = (
    PROJECT_ROOT / "manifests" / "ollama_xiaoj_total_field_v0_1"
)
LOCAL_MODEL_CONTRACT_PATH = LOCAL_MODEL_MANIFEST_ROOT / "root_model_contract.json"
LOCAL_MODEL_PREFIX_PATH = LOCAL_MODEL_MANIFEST_ROOT / "system_prefix.txt"
LOCAL_CONTEXT_MAX_ITEMS = int(os.getenv("TAIJI_LOCAL_CONTEXT_MAX_ITEMS", "4"))
CONTEXT_IDENTITY_CLASS = os.getenv(
    "TAIJI_CONTEXT_IDENTITY_CLASS", "unknown"
).strip().lower()
if CONTEXT_IDENTITY_CLASS not in {"founder", "general_member", "unknown"}:
    CONTEXT_IDENTITY_CLASS = "unknown"
VOICE_INTENT_URL = os.getenv(
    "TAIJI_VOICE_INTENT_URL", "http://127.0.0.1:9011/v1/pos/voice-intent"
)
VOICE_GATEWAY_URL = os.getenv(
    "TAIJI_VOICE_GATEWAY_URL", "http://127.0.0.1:9201"
).rstrip("/")
NVR_HOST = os.getenv("TAIJI_NVR_HOST", "192.168.50.34")
NVR_WEB_PORT = int(os.getenv("TAIJI_NVR_WEB_PORT", "30080"))
NVR_RTSP_PORT = int(os.getenv("TAIJI_NVR_RTSP_PORT", "554"))
NVR_DDNS_HOST = os.getenv("TAIJI_NVR_DDNS_HOST", "p1430563.ds1.nxt.net.tw")
NVR_DDNS_WEB_PORT = int(os.getenv("TAIJI_NVR_DDNS_WEB_PORT", "30080"))


@router.get("/v1/models")
def list_models() -> dict[str, Any]:
    names = _available_models()
    if not names:
        names = [DEFAULT_MODEL]
    if TOTAL_FIELD_GOOGLE_MODEL not in names:
        names.insert(0, TOTAL_FIELD_GOOGLE_MODEL)

    return {
        "object": "list",
        "data": [
            {
                "id": name,
                "object": "model",
                "created": 0,
                "owned_by": (
                    "total-field-google-vertex"
                    if name == TOTAL_FIELD_GOOGLE_MODEL
                    else "taiji-local"
                ),
            }
            for name in names
        ],
    }


@router.post("/v1/chat/completions", response_model=None)
async def chat_completions(request: Request) -> dict[str, Any] | StreamingResponse:
    body = await request.json()
    if body.get("stream") is True:
        non_streaming_body = dict(body)
        non_streaming_body["stream"] = False
        result = _complete_chat(non_streaming_body)
        return StreamingResponse(
            _openai_sse_events(result),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    return _complete_chat(body)


def _openai_sse_events(result: dict[str, Any]):
    completion_id = str(result["id"])
    created = int(result["created"])
    model = str(result["model"])
    content = str(result["choices"][0]["message"]["content"])
    first = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"role": "assistant", "content": content},
                "finish_reason": None,
            }
        ],
        "taiji": result.get("taiji") or {},
    }
    final = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield "data: " + json.dumps(first, ensure_ascii=False, separators=(",", ":")) + "\n\n"
    yield "data: " + json.dumps(final, ensure_ascii=False, separators=(",", ":")) + "\n\n"
    yield "data: [DONE]\n\n"


def _complete_chat(body: dict[str, Any]) -> dict[str, Any]:
    if body.get("stream") is True:
        raise HTTPException(status_code=400, detail="streaming_not_supported_in_phase_b")

    messages = _normalize_messages(body)
    if not messages:
        raise HTTPException(status_code=422, detail="messages_or_prompt_required")

    model = _resolve_model(body.get("model"))
    if model == TOTAL_FIELD_GOOGLE_MODEL:
        try:
            content, usage, total_field_metadata = total_field_google_chat(messages, body)
            backend = total_field_metadata["backend"]
            total_field_metadata.setdefault("inference_route", "GOOGLE_VERTEX")
            total_field_metadata["answer_source"] = _answer_source(
                source_class="CLOUD_MODEL",
                route="CLOUD_DIRECT",
                provider="GOOGLE_VERTEX",
                model=str(total_field_metadata.get("provider_model") or model),
            )
        except HTTPException as exc:
            google_failure = _google_availability_failure(exc)
            if not google_failure:
                raise
            fallback_model = _resolve_model(LOCAL_FALLBACK_MODEL)
            messages, local_context_metadata = _attach_local_total_field_context(
                messages,
                body,
            )
            options = _ollama_options(body)
            data, backend = _chat_with_fallback(fallback_model, messages, options)
            gpu_execution = _observe_local_gpu_execution(fallback_model)
            content = _extract_content(data)
            usage = _usage(data, messages, content)
            total_field_metadata = {
                "total_field_pull": False,
                "google_total_field_pull_attempted": True,
                "google_failure_state": google_failure,
                "inference_route": "LOCAL_AFTER_GOOGLE_UNAVAILABLE",
                "inference_route_is_generative_transmission": False,
                "generative_transmission_used": False,
                "provider_model": fallback_model,
                "answer_source": _answer_source(
                    source_class="LOCAL_MODEL",
                    route="LOCAL_AFTER_CLOUD_UNAVAILABLE",
                    provider="OLLAMA",
                    model=fallback_model,
                    gpu_execution=gpu_execution,
                ),
                "8dadi_index_only": True,
                "candidate_authority": False,
                "execution_authorized": False,
                "plaintext_persisted": False,
                **local_context_metadata,
            }
    else:
        messages, local_context_metadata = _attach_local_total_field_context(
            messages,
            body,
        )
        options = _ollama_options(body)
        data, backend = _chat_with_fallback(model, messages, options)
        gpu_execution = _observe_local_gpu_execution(model)
        content = _extract_content(data)
        usage = _usage(data, messages, content)
        total_field_metadata = {
            "inference_route": "LOCAL_DIRECT",
            "inference_route_is_generative_transmission": False,
            "generative_transmission_used": False,
            "candidate_authority": False,
            "execution_authorized": False,
            "answer_source": _answer_source(
                source_class="LOCAL_MODEL",
                route="LOCAL_DIRECT",
                provider="OLLAMA",
                model=model,
                gpu_execution=gpu_execution,
            ),
            **local_context_metadata,
        }

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
        "usage": usage,
        "taiji": {
            "compat_layer": "phase_b",
            "backend": backend,
            "plaintext_persisted": False,
            **total_field_metadata,
        },
    }


@router.post("/v1/taiji/hearing/intent")
async def hearing_intent(request: Request) -> dict[str, Any]:
    """Accept node-local speech recognition text through the Total Field path.

    Raw audio remains at the source node.  This endpoint accepts only the
    transcript and source coordinate, then invokes the same governed model
    path as browser text input.
    """

    body = await request.json()
    transcript = str(body.get("transcript") or "").strip()
    source_node = str(body.get("source_node") or "").strip()
    if not transcript or not source_node:
        raise HTTPException(
            status_code=422,
            detail="transcript_and_source_node_required",
        )

    chat_body: dict[str, Any] = {
        "model": body.get("model") or DEFAULT_MODEL,
        "messages": [{"role": "user", "content": transcript}],
        "temperature": body.get("temperature", 0.2),
        "max_tokens": body.get("max_tokens", 512),
    }
    if body.get("user"):
        chat_body["user"] = body["user"]
    result = _complete_chat(chat_body)
    result["taiji"]["hearing"] = {
        "schema_id": "W7TP_8DADI_HEARING_INGRESS_V2_3",
        "source_node": source_node,
        "application": str(body.get("application") or "natural_language"),
        "locale": str(body.get("locale") or "zh-TW"),
        "recognition_location": "SOURCE_NODE_LOCAL_OR_HARDWARE",
        "raw_audio_received": False,
        "raw_audio_stored": False,
        "transcript_digest": hashlib.sha256(transcript.encode("utf-8")).hexdigest(),
        "execution_authorized": False,
        "result_requires_total_field_effect_decision": True,
    }
    return result


@router.post("/v1/taiji/vision/analyze")
async def vision_analyze(request: Request) -> dict[str, Any]:
    """Analyze one necessary frame locally without storing the image."""

    body = await request.json()
    prompt = str(body.get("prompt") or "請以繁體中文描述目前畫面。只陳述可觀測內容。")
    source_node = str(body.get("source_node") or "").strip()
    encoded, image_format, image_sha256 = _validated_image_payload(
        body.get("image_base64")
    )
    if not source_node:
        raise HTTPException(status_code=422, detail="source_node_required")

    model = _resolve_model(body.get("model") or "xiaoj:latest")
    if model == TOTAL_FIELD_GOOGLE_MODEL:
        raise HTTPException(
            status_code=422,
            detail="VISION_REQUIRES_LOCAL_REGISTERED_MODEL",
        )
    messages, context_metadata = _attach_local_total_field_context(
        [{"role": "user", "content": prompt}],
        body,
    )
    messages[-1]["images"] = [encoded]  # Ollama image input; memory-only request body.
    data, backend = _chat_with_fallback(model, messages, _ollama_options(body))
    gpu_execution = _observe_local_gpu_execution(model)
    content = _extract_content(data)
    usage = _usage(data, messages, content)
    return {
        "id": "vision-" + uuid.uuid4().hex,
        "object": "taiji.vision.analysis",
        "created": int(time.time()),
        "model": model,
        "result": content,
        "usage": usage,
        "taiji": {
            "schema_id": "W7TP_8DADI_VISION_INGRESS_V2_3",
            "backend": backend,
            "source_node": source_node,
            "image_format": image_format,
            "image_sha256": image_sha256,
            "image_persisted": False,
            "minimum_required_frame_only": True,
            "8dadi_dynamic_context_used": True,
            "inference_route_is_generative_transmission": False,
            "generative_transmission_used": False,
            "candidate_authority": False,
            "execution_authorized": False,
            "answer_source": _answer_source(
                source_class="LOCAL_MODEL",
                route="LOCAL_DIRECT",
                provider="OLLAMA",
                model=model,
                gpu_execution=gpu_execution,
            ),
            **context_metadata,
        },
    }


@router.get("/v1/taiji/perception/status")
def perception_status() -> dict[str, Any]:
    nvr_web = _http_health(f"http://{NVR_HOST}:{NVR_WEB_PORT}/")
    nvr_rtsp = _tcp_health(NVR_HOST, NVR_RTSP_PORT)
    nvr_ddns = (
        {"ok": False, "state": "NOT_PROBED_LAN_PRIMARY_AVAILABLE"}
        if nvr_web["ok"] and nvr_rtsp["ok"]
        else _http_health(f"http://{NVR_DDNS_HOST}:{NVR_DDNS_WEB_PORT}/")
    )
    voice_intent = _http_health(VOICE_INTENT_URL.rsplit("/v1/", 1)[0] + "/healthz")
    voice_output = _http_health(f"{VOICE_GATEWAY_URL}/healthz")
    route_source_ip = _route_source_ip(NVR_HOST, NVR_WEB_PORT)
    lan_observed = route_source_ip.startswith(("192.168.", "10.", "172.16."))
    return {
        "schema_id": "W7TP_8DADI_TOTAL_FIELD_PERCEPTION_STATUS_V2_3",
        "state": "OBSERVED_WITH_AUTHENTICATED_MEDIA_PATH_HOLD",
        "D1_intent": "TOTAL_FIELD_VISUAL_AND_HEARING_ORGANS",
        "D2_state": {
            "vision_source_reachable": bool(nvr_web["ok"] and nvr_rtsp["ok"]),
            "hearing_ingress_ready": bool(voice_intent["ok"]),
            "voice_task_gateway_ready": bool(voice_output["ok"]),
        },
        "D3_coordinate": {
            "vision": {
                "node": "store_lilin_nvr",
                "host": NVR_HOST,
                "web_port": NVR_WEB_PORT,
                "rtsp_port": NVR_RTSP_PORT,
            },
            "hearing": {
                "mode": "ANY_REGISTERED_NODE_TRANSCRIPT_TO_SINGLE_TOTAL_FIELD_GATEWAY",
                "endpoint": "/v1/taiji/hearing/intent",
            },
            "vision_analysis": {
                "mode": "REGISTERED_NODE_SINGLE_FRAME_TO_LOCAL_MODEL",
                "endpoint": "/v1/taiji/vision/analyze",
            },
            "route": {
                "policy": "LAN_FIRST_VPN_ONLY_WHEN_LAN_UNAVAILABLE",
                "source_ip": route_source_ip,
                "lan_observed": lan_observed,
                "ddns_backup": f"{NVR_DDNS_HOST}:{NVR_DDNS_WEB_PORT}",
                "ddns_probe_state": nvr_ddns["state"],
                "vpn_or_ddns_escalated": nvr_ddns["state"]
                != "NOT_PROBED_LAN_PRIMARY_AVAILABLE",
            },
        },
        "D4_evidence": {
            "nvr_web": nvr_web,
            "nvr_rtsp": nvr_rtsp,
            "nvr_ddns_backup": nvr_ddns,
            "voice_intent_service": voice_intent,
            "voice_task_gateway": voice_output,
        },
        "D5_execution_policy": {
            "visual_sampling": "MINIMUM_REQUIRED_FRAME_OR_EVENT_ONLY",
            "continuous_raw_feed_to_model": False,
            "raw_audio_upload": False,
            "source_node_speech_recognition": True,
        },
        "D6_generative_transmission": {
            "used": False,
            "reason": "PERCEPTION_REACHABILITY_AND_TRANSCRIPT_ROUTING_ARE_NOT_D6",
        },
        "D7_risk": {
            "nvr_login_required_for_media": True,
            "stream_path_known": False,
            "camera_control_allowed": False,
            "recording_or_alarm_change_allowed": False,
        },
        "D8_authority": {
            "login_is_authentication_not_final_authority": True,
            "model_output_is_candidate": True,
            "physical_effect_requires_total_field_and_human_scope": True,
        },
    }


def _validated_image_payload(value: Any) -> tuple[str, str, str]:
    encoded = str(value or "").strip()
    if encoded.startswith("data:"):
        try:
            header, encoded = encoded.split(",", 1)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="invalid_image_data_url") from exc
        if ";base64" not in header:
            raise HTTPException(status_code=422, detail="image_must_be_base64")
    if not encoded or len(encoded) > 12_000_000:
        raise HTTPException(status_code=413, detail="image_missing_or_too_large")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(status_code=422, detail="invalid_image_base64") from exc
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        image_format = "png"
    elif raw.startswith(b"\xff\xd8\xff"):
        image_format = "jpeg"
    elif raw.startswith(b"RIFF") and raw[8:12] == b"WEBP":
        image_format = "webp"
    else:
        raise HTTPException(status_code=422, detail="unsupported_image_format")
    return encoded, image_format, hashlib.sha256(raw).hexdigest()


def _attach_local_total_field_context(
    messages: list[dict[str, str]],
    body: dict[str, Any],
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    query = _last_user_text(messages)
    if not query:
        raise HTTPException(status_code=422, detail="TOTAL_FIELD_CONTEXT_REQUIRES_USER_INTENT")

    alignment_prefix, alignment = _load_local_model_alignment()
    context = build_dynamic_context(
        root=PROJECT_ROOT,
        query=query,
        max_items=LOCAL_CONTEXT_MAX_ITEMS,
        identity_class=CONTEXT_IDENTITY_CLASS,
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

    target_lock = scan_operation(
        repo_root=PROJECT_ROOT,
        operation="PREFLIGHT",
        actor_class="SYSTEM",
        query=query,
    )
    if target_lock.get("state") != MANDATORY_APPLICATION_PASS:
        raise HTTPException(
            status_code=503,
            detail=str(target_lock.get("reason") or "HOLD_TOTAL_FIELD_TARGET_LOCK"),
        )
    inference_review = scan_operation(
        repo_root=PROJECT_ROOT,
        operation="AI_INFERENCE",
        actor_class="AI",
        query=query,
        expected_branch=target_lock["coordinates"]["branch"],
        expected_head=target_lock["coordinates"]["head"],
        expected_tree=target_lock["coordinates"]["tree"],
        expected_work_target_sha256=target_lock["work_target_sha256"],
    )
    if inference_review.get("state") != MANDATORY_APPLICATION_PASS:
        raise HTTPException(
            status_code=503,
            detail=str(inference_review.get("reason") or "HOLD_TOTAL_FIELD_AI_INFERENCE"),
        )
    mandatory_context = json.loads(reviewed_prompt_text(inference_review))

    evidence_items: list[dict[str, Any]] = []
    for item in context.get("context_items") or []:
        if not isinstance(item, dict):
            continue
        if item.get("source_current_matches_snapshot") is not True:
            continue
        evidence_items.append(
            {
                "reference": item.get("relative_path"),
                "sha256": item.get("sha256"),
                "trust": item.get("trust"),
                "status": item.get("status"),
                "evidence_class": item.get("evidence_class"),
                "matched_terms": item.get("matched_terms") or [],
                "evidence_excerpt": str(item.get("snippet") or "")[:1200],
            }
        )

    login_subject = str(body.get("user") or "").strip()
    login_subject_sha256 = (
        hashlib.sha256(login_subject.encode("utf-8")).hexdigest()
        if login_subject
        else None
    )
    header = {
        "schema_id": "W7TP_8DADI_LOCAL_MODEL_CONTEXT_HEADER_V2_3",
        "current_user_intent": query,
        "current_user_intent_is_d1_input": True,
        "8dadi_context_packet_sha256": context.get("packet_sha256"),
        "8dadi_retrieval_method": context.get("retrieval_method"),
        "context_identity_class": CONTEXT_IDENTITY_CLASS,
        "founder_intent_projection": context.get("founder_intent_projection"),
        "mandatory_total_field_local_rule_context": mandatory_context,
        "work_target_sha256": inference_review["work_target_sha256"],
        "evidence_items": evidence_items,
        "evidence_is_d4_only": True,
        "legacy_may_define_target": False,
        "v2_1_role": "D4_HISTORY_ONLY_WHEN_EXPLICITLY_REQUIRED",
        "network_policy": "LAN_FIRST_VPN_ONLY_WHEN_LAN_UNAVAILABLE",
        "model_role": "PASSIVE_REPLACEABLE_REASONING_ORGAN",
        "model_output_state": "CANDIDATE_RETURN_TO_TOTAL_FIELD",
        "total_field_alignment_prefix": alignment_prefix,
        "total_field_alignment": alignment,
        "model_may_self_report_answer_source": False,
        "execution_authorized": False,
        "system_mutation_allowed": False,
        "login": {
            "subject_present": bool(login_subject),
            "subject_sha256": login_subject_sha256,
            "authentication_is_not_final_authority": True,
            "founder_authority_verified": False,
        },
        "instruction_zh_tw": (
            "以最新使用者自然語言作為本次 D1 意圖輸入；八維索引證據僅供定位，"
            "舊版與歷史證據不得反向定義目標。只用繁體中文。"
            "不得虛構未知狀態，不得把候選、測試、登入或服務存在升格為權威、部署或完成。"
            "需要實體效果時只提出精確作用封包，交回總場與有效人審權限裁決。"
        ),
    }
    contextual_messages = [
        {
            "role": "system",
            "content": (
                alignment_prefix
                + "\n\nTOTAL_FIELD_CONTEXT_JSON\n"
                + json.dumps(
                    header,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            ),
        },
        *messages,
    ]
    metadata = {
        "8dadi_index_only": True,
        "8dadi_dynamic_context_used": True,
        "8dadi_context_packet_sha256": context.get("packet_sha256"),
        "mandatory_application_review": True,
        "work_target_sha256": inference_review["work_target_sha256"],
        "context_identity_class": CONTEXT_IDENTITY_CLASS,
        "founder_intent_projection_present": bool(
            context.get("founder_intent_projection")
        ),
        "context_evidence_count": len(evidence_items),
        "login_subject_present": bool(login_subject),
        "login_is_final_authority": False,
        **alignment,
    }
    return contextual_messages, metadata


def _load_local_model_alignment() -> tuple[str, dict[str, Any]]:
    try:
        contract_bytes = LOCAL_MODEL_CONTRACT_PATH.read_bytes()
        prefix_bytes = LOCAL_MODEL_PREFIX_PATH.read_bytes()
        contract = json.loads(contract_bytes)
        prefix = prefix_bytes.decode("utf-8").strip()
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="HOLD_LOCAL_LLM_ALIGNMENT_PREFIX_UNREADABLE",
        ) from exc
    if (
        contract.get("schema_id") != "W7TP_XIAOJ_MODEL_ORGAN_CONTRACT_V2_3"
        or contract.get("state") != "ACTIVE_RUNTIME_ALIGNMENT_CONTRACT"
        or (contract.get("model") or {}).get("visible_model_id") != LOCAL_FALLBACK_MODEL
        or not prefix.startswith("W7TP_XIAOJ_TOTAL_FIELD_MODEL_ORGAN_PREFIX_V2_3")
    ):
        raise HTTPException(
            status_code=503,
            detail="HOLD_LOCAL_LLM_ALIGNMENT_PREFIX_INVALID",
        )
    return prefix, {
        "local_model_contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "local_model_prefix_sha256": hashlib.sha256(prefix_bytes).hexdigest(),
        "local_model_contract_version": str(contract.get("version") or ""),
        "required_local_model": LOCAL_FALLBACK_MODEL,
        "alignment_prefix_bound": True,
    }


def _answer_source(
    *,
    source_class: str,
    route: str,
    provider: str,
    model: str,
    gpu_execution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = {
        "source_class": source_class,
        "route": route,
        "provider": provider,
        "model": model,
        "determined_by": "TOTAL_FIELD_GATEWAY",
        "model_self_report_used": False,
    }
    if gpu_execution is not None:
        result["gpu_execution"] = gpu_execution
    return result


def _observe_local_gpu_execution(model: str) -> dict[str, Any]:
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/ps", timeout=5)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="HOLD_LOCAL_LLM_GPU_EXECUTION_NOT_OBSERVABLE",
        ) from exc
    models = data.get("models", []) if isinstance(data, dict) else []
    observed = next(
        (
            item
            for item in models
            if isinstance(item, dict) and item.get("name") == model
        ),
        None,
    )
    if not observed:
        raise HTTPException(
            status_code=503,
            detail="HOLD_LOCAL_LLM_GPU_EXECUTION_NOT_PROVEN",
        )
    size = int(observed.get("size") or 0)
    size_vram = int(observed.get("size_vram") or 0)
    if size <= 0 or size_vram < size:
        raise HTTPException(
            status_code=503,
            detail="HOLD_LOCAL_LLM_FULL_GPU_RESIDENCY_REQUIRED",
        )
    return {
        "state": "PASS_LOCAL_LLM_FULL_GPU_EXECUTION",
        "model": model,
        "digest": str(observed.get("digest") or ""),
        "total_size_bytes": size,
        "vram_size_bytes": size_vram,
        "full_gpu_residency": True,
        "observed_by": "TOTAL_FIELD_OLLAMA_RUNTIME",
    }


def _last_user_text(messages: list[dict[str, str]]) -> str:
    for item in reversed(messages):
        if item.get("role") == "user" and item.get("content"):
            return str(item["content"])
    return ""


def _http_health(url: str) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        response = requests.get(url, timeout=2, allow_redirects=False)
    except requests.RequestException as exc:
        return {
            "ok": False,
            "state": "UNREACHABLE",
            "error_class": type(exc).__name__,
        }
    return {
        "ok": response.status_code < 500,
        "state": "REACHABLE",
        "status_code": response.status_code,
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
    }


def _tcp_health(host: str, port: int) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=2):
            pass
    except OSError as exc:
        return {
            "ok": False,
            "state": "UNREACHABLE",
            "error_class": type(exc).__name__,
        }
    return {
        "ok": True,
        "state": "REACHABLE",
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
    }


def _route_source_ip(host: str, port: int) -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect((host, port))
        return str(sock.getsockname()[0])
    except OSError:
        return "UNKNOWN"
    finally:
        sock.close()


def _google_availability_failure(exc: HTTPException) -> str | None:
    detail = exc.detail
    if isinstance(detail, dict):
        code = str(detail.get("error") or "")
    else:
        code = str(detail or "")
    allowed = {
        "HOLD_GOOGLE_IDENTITY_TOKEN_UNAVAILABLE",
        "HOLD_GOOGLE_VERTEX_TRANSPORT_FAILED",
        "HOLD_GOOGLE_VERTEX_REJECTED",
        "HOLD_GOOGLE_VERTEX_RESPONSE_INVALID",
        "HOLD_GOOGLE_VERTEX_EMPTY_RESULT",
    }
    return code if code in allowed else None


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
    if requested == TOTAL_FIELD_GOOGLE_MODEL:
        return requested
    names = _available_models()
    if requested in names or not names:
        return requested
    raise HTTPException(
        status_code=503,
        detail={"error": "HOLD_REQUESTED_MODEL_UNAVAILABLE", "model": requested},
    )


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
