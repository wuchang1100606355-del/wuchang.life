#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Total Field PR layer for safe answer tone rendering.

LLM is the public-relations layer of Total Field, not the authority of Total Field.
LLM 是總場的公關層，不是總場的權威層。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from typing import Any


SAFETY_FLAGS = {
    "SECRET_READ": False,
    "MEMBER_PLAINTEXT_READ": False,
    "RAW_AUDIO_SAVED": False,
    "DB_WRITE": False,
    "PAYMENT_CAPTURE": False,
    "SERVICE_RESTART": False,
    "DEPLOY": False,
    "PRODUCTION_RELEASE": False,
    "EXTERNAL_API_CALL": False,
    "MODEL_DOWNLOAD": False,
    "LLM_AUTHORITY": False,
}

MUST_NOT_CLAIM = [
    "verified identity",
    "member plaintext access",
    "payment completed",
    "database write completed",
]

UNSAFE_TEXT_MARKERS = [
    "已驗證身分",
    "身分已驗證",
    "會員明文",
    "完整電話",
    "完整地址",
    "身分證",
    "身份證",
    "已完成付款",
    "扣款完成",
    "已寫入資料庫",
    "已寫入 DB",
]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def parse_json_arg(value: str, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def local_ollama_base() -> str:
    host = os.environ.get("OLLAMA_HOST", "").strip()
    if not host:
        return "http://127.0.0.1:11434"
    if host.startswith("127.0.0.1:") or host.startswith("localhost:"):
        return "http://" + host
    if host.startswith("http://127.0.0.1:") or host.startswith("http://localhost:"):
        return host.rstrip("/")
    return "http://127.0.0.1:11434"


def ollama_tags(base: str) -> list[dict[str, Any]]:
    url = base.rstrip("/") + "/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=1.5) as response:
            data = json.loads(response.read().decode("utf-8"))
        models = data.get("models") or []
        return models if isinstance(models, list) else []
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return []


def choose_model(base: str, explicit_model: str = "") -> str:
    if explicit_model:
        return explicit_model
    models = ollama_tags(base)
    if not models:
        return ""
    first = models[0]
    return str(first.get("name") or first.get("model") or "")


def build_request_packet(
    input_text_hash: str,
    decision: str,
    verifier_reasons: list[str],
    semantic_ir: dict[str, Any],
    safe_answer: str,
    forbidden_actions: list[str],
    safety_flags: dict[str, bool],
    identity_state: dict[str, Any],
) -> dict[str, Any]:
    return {
        "packet_type": "TOTAL_FIELD_PR_REQUEST_PACKET",
        "version": "v0.1",
        "input_text_hash": input_text_hash,
        "verified_decision": decision,
        "verifier_reasons": verifier_reasons,
        "semantic_ir": semantic_ir,
        "safe_answer_draft": safe_answer,
        "forbidden_actions": forbidden_actions,
        "safety_flags": safety_flags,
        "identity_state": identity_state,
        "public_context_only": True,
    }


def template_refine(request_packet: dict[str, Any]) -> str:
    draft = str(request_packet.get("safe_answer_draft") or "").strip()
    decision = str(request_packet.get("verified_decision") or "HOLD")
    semantic_ir = request_packet.get("semantic_ir") or {}
    intent = str(semantic_ir.get("intent_id") or "")
    scene_context = semantic_ir.get("scene_context") or {}
    scene_type = str(scene_context.get("context_type") or "")
    dev_override = scene_context.get("dev_identity_override") or {}
    if not draft:
        draft = "目前總場已收到請求，但需要先完成 verifier 檢查。"

    if dev_override.get("enabled") is True:
        return "已偵測本機開發者設備，可進入本機工程對話；這不等同於自然人身分驗證，仍不會讀取 secret、會員明文、付款或部署。總場仍維持 verifier 決策、no DB write 與 candidate-only 模型邊界。"
    if scene_type == "VERIFIED_FOUNDER_ROLE":
        return draft if "總場" in draft else "已收到已驗證 role_ref / signed identity packet 的總場工程脈絡；仍維持 no secret、no plaintext、no payment、no production deploy without explicit packet。"
    if scene_type == "CLAIMED_FOUNDER_CONTEXT":
        return "我收到你的身分聲明，但不會直接視為已驗證。若有登入狀態、role_ref 或 8D 身分封包，總場可用去識別方式確認可用權限。"
    if intent == "claimed_founder_identity":
        return "我收到你的身分聲明；我可以溫和地協助說明下一步，但不會把這句話直接視為已驗證身分。總場會先保留 claimed_identity_packet，等 role_ref、登入狀態或 verifier 驗證後，再決定可使用的功能。"
    if intent in {"identity_context_query", "role_context_query"}:
        return "我目前不能只憑一句話確認你的真實身分或角色。若你已登入，或提供 8D 身分封包，我可以用 role_ref / member_ref 的去識別化方式判斷可用權限；不會顯示會員明文資料。"
    if intent == "member_context_query":
        return "我可以協助你確認會員情境，但只能使用 member_ref / role_ref 這類去識別化參照；不讀 DB、不顯示會員明文，也不輸出電話、地址或證件資料。"
    if scene_type == "STORE_CONTEXT":
        return draft if draft.startswith("櫃台") else "櫃台這邊可以先協助整理：" + draft
    if scene_type == "PROPERTY_CONTEXT":
        return draft if "物業" in draft else "物業服務脈絡已建立：" + draft
    if scene_type == "ASSOCIATION_CONTEXT":
        return draft if "協會" in draft else "協會公益治理脈絡下，我可以先協助整理候選流程：" + draft
    if scene_type == "FOUNDER_CONTEXT":
        return draft if "總場" in draft else "以總場工程/架構討論角度來看：" + draft
    if scene_type == "GENERAL_CHAT_CONTEXT":
        return draft if draft.startswith("我在") else "我在，先陪你慢慢整理。" + draft
    if "payment_capture" in request_packet.get("forbidden_actions", []):
        return "我可以協助整理付款請求，但付款或扣款必須停在人工確認流程；總場不會自動 payment capture，也不會把決策改成允許。"
    if "你會做什麼" in draft or intent == "unknown":
        return draft
    if decision == "HOLD" and "驗證" not in draft and "確認" not in draft:
        return draft + " 這一步仍需先完成驗證或人工確認。"
    return draft


def build_prompt(request_packet: dict[str, Any]) -> str:
    safe_payload = {
        "verified_decision": request_packet.get("verified_decision"),
        "verifier_reasons": request_packet.get("verifier_reasons"),
        "semantic_ir": request_packet.get("semantic_ir"),
        "safe_answer_draft": request_packet.get("safe_answer_draft"),
        "forbidden_actions": request_packet.get("forbidden_actions"),
        "identity_state": request_packet.get("identity_state"),
        "scene_context": (request_packet.get("semantic_ir") or {}).get("scene_context"),
    }
    return (
        "你是總場的公關轉譯層，不是總場本身。\n"
        "LLM is the public-relations layer of Total Field, not the authority of Total Field.\n"
        "LLM 是總場的公關層，不是總場的權威層。\n"
        "你不能改變 verifier 決策。\n"
        "你不能新增事實。\n"
        "你不能聲稱已驗證身分。\n"
        "你不能讀取或推測會員明文。\n"
        "你只能把 safe_answer_draft 用更自然、溫和、清楚的繁體中文重寫。\n"
        "若 decision=HOLD，必須保留需要驗證或需要人工確認語意。\n"
        "若 decision=BLOCK，必須保留拒絕語意。\n"
        "只輸出改寫後文字，不要輸出 JSON。\n\n"
        + dumps(safe_payload)
    )


def call_local_ollama(request_packet: dict[str, Any], model: str) -> str:
    base = local_ollama_base()
    chosen = choose_model(base, model)
    if not chosen:
        return ""
    payload = {
        "model": chosen,
        "prompt": build_prompt(request_packet),
        "stream": False,
        "options": {"temperature": 0.2},
    }
    req = urllib.request.Request(
        base.rstrip("/") + "/api/generate",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
        return str(data.get("response") or "").strip()
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return ""


def output_is_safe(text: str, decision: str) -> bool:
    if not text.strip():
        return False
    if any(marker in text for marker in UNSAFE_TEXT_MARKERS):
        return False
    if decision == "HOLD" and not any(marker in text for marker in ("驗證", "確認", "HOLD", "保留")):
        return False
    if decision == "BLOCK" and not any(marker in text for marker in ("不能", "不可", "拒絕", "BLOCK")):
        return False
    return True


def response_packet(text: str, lane: str) -> dict[str, Any]:
    return {
        "packet_type": "TOTAL_FIELD_PR_RESPONSE_PACKET",
        "version": "v0.1",
        "candidate_only": True,
        "model_authority": False,
        "verified_decision_unchanged": True,
        "text_zh_TW": text,
        "style": "calm_public_relations",
        "must_not_claim": MUST_NOT_CLAIM,
        "requires_final_safety_check": True,
        "model_lane": lane,
        "created_at_unix": int(time.time()),
        "packet_id": "pr_" + uuid.uuid4().hex,
    }


def run_pr_layer(request_packet: dict[str, Any], model: str = "", disable_model: bool = False) -> dict[str, Any]:
    decision = str(request_packet.get("verified_decision") or "HOLD")
    lane = "FALLBACK_TEMPLATE"
    final_text = template_refine(request_packet)
    if not disable_model:
        candidate = call_local_ollama(request_packet, model)
        if output_is_safe(candidate, decision):
            lane = "LOCAL_OLLAMA"
            final_text = candidate
    if lane == "FALLBACK_TEMPLATE" and not final_text:
        lane = "OFF"
        final_text = str(request_packet.get("safe_answer_draft") or "")
    return {
        "STATE": "PASS_W7TP_TOTAL_FIELD_PR_LAYER",
        "RUN_MODE": "LOCAL_MODEL_PR_LAYER_OR_TEMPLATE_FALLBACK",
        "MODEL_LANE": lane,
        "SAFETY_FLAGS": SAFETY_FLAGS,
        "REQUEST_PACKET": request_packet,
        "RESPONSE_PACKET": response_packet(final_text, lane),
        "FINAL_TEXT": final_text,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", default="")
    parser.add_argument("--safe-answer", default="")
    parser.add_argument("--decision", default="HOLD")
    parser.add_argument("--model", default="")
    parser.add_argument("--request-json", default="")
    parser.add_argument("--semantic-ir-json", default="")
    parser.add_argument("--forbidden-actions-json", default="")
    parser.add_argument("--safety-flags-json", default="")
    parser.add_argument("--identity-state-json", default="")
    parser.add_argument("--disable-model", action="store_true")
    args = parser.parse_args()

    if args.request_json:
        request_packet = parse_json_arg(args.request_json, {})
    else:
        semantic_ir = parse_json_arg(args.semantic_ir_json, {})
        forbidden_actions = parse_json_arg(args.forbidden_actions_json, [])
        safety_flags = parse_json_arg(args.safety_flags_json, SAFETY_FLAGS)
        identity_state = parse_json_arg(args.identity_state_json, {"claimed_identity": False, "accepted_as_truth": False, "verified_role_ref": None})
        request_packet = build_request_packet(
            sha256_text(args.text),
            args.decision,
            [],
            semantic_ir if isinstance(semantic_ir, dict) else {},
            args.safe_answer,
            forbidden_actions if isinstance(forbidden_actions, list) else [],
            safety_flags if isinstance(safety_flags, dict) else SAFETY_FLAGS,
            identity_state if isinstance(identity_state, dict) else {"claimed_identity": False, "accepted_as_truth": False, "verified_role_ref": None},
        )
    result = run_pr_layer(request_packet, model=args.model, disable_model=args.disable_model)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
