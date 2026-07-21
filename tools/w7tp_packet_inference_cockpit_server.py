#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local W7TP packet inference cockpit server.

The server wraps the existing packet-by-packet runtime and serves a static
cockpit UI. It performs no external API calls and writes only redacted local
audit reports for cockpit runs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import subprocess
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web" / "packet_inference_cockpit"
RUNTIME = ROOT / "tools" / "w7tp_packet_inference_runtime.py"
PR_LAYER = ROOT / "tools" / "w7tp_total_field_pr_layer.py"
RUN_ROOT = ROOT / "runtime" / "total_field" / "packet_inference_cockpit"
CANONICAL_GATE_AVAILABLE = False
try:
    from tools.total_field.final_state_gate import run_total_field_gate
    from tools.total_field.human_response_renderer import render_human_response

    CANONICAL_GATE_AVAILABLE = True
except Exception:  # pragma: no cover - defensive import guard for environment issues
    run_total_field_gate = None
    render_human_response = None

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
    "MODEL_REQUIRED": False,
    "LLM_AUTHORITY": False,
}


def run_dual_llm_governed_nlio(
    request_text: str,
    *,
    local_provider: Any,
    cloud_provider: Any,
    domain_gateway: Any,
    previous_values: dict[str, Any],
    persona_text: str = "",
    channel: str = "web",
    request_mode: str = "CHAT_ONLY",
    requested_effects: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Expose injected dual-candidate NLIO without adding another server route."""

    from tools.xiaoj_candidate_adapter import DualLLMGovernedNLIOCoordinator

    return DualLLMGovernedNLIOCoordinator(
        local_provider=local_provider,
        cloud_provider=cloud_provider,
        domain_gateway=domain_gateway,
    ).process(
        request_text,
        previous_values=previous_values,
        persona_text=persona_text,
        channel=channel,
        request_mode=request_mode,
        requested_effects=requested_effects,
    )


def _render_human_response_payload(final_verifier: dict[str, Any], source_channel: str = "web") -> dict[str, Any]:
    channel = source_channel or "web"
    try:
        from tools.total_field.human_response_renderer import render_human_response

        return render_human_response(
            {
                **final_verifier,
                "source_channel": final_verifier.get("source_channel") or channel,
            },
            channel=channel,
        )
    except Exception:
        return {
            "state": "HUMAN_RESPONSE_RENDERED",
            "decision": "HOLD",
            "risk_level": "MEDIUM",
            "channel": "WEB",
            "reply_text": "這個候選需要再確認，我先暫停，不會執行任何正式動作。",
            "requires_confirmation": True,
            "candidate_reply_only": True,
            "formal_send_executed": False,
            "line_reply_sent": False,
            "db_write": False,
            "odoo_write": False,
            "deploy": False,
            "restart": False,
            "persona_voice_hint": "系統保守回退中，保持高風險提示。",
            "media_response": {
                "mode": "TEXT_ONLY",
                "audio_script": "",
                "voice_hint": "no_audio",
                "video_mode": "NONE",
                "video_hint": "高風險情況下不提供影像回覆。",
            },
            "redaction": {
                "raw_d_dimensions_exposed": False,
                "verifier_internals_exposed": False,
                "h64_td_exposed": False,
            },
        }


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def safe_json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0") or "0")
    raw = handler.rfile.read(length)
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def packet_field(packet: dict[str, Any], *path: str) -> Any:
    current: Any = packet
    for key in path:
        if not isinstance(current, dict):
            return ""
        current = current.get(key)
    return current if current is not None else ""


def normalize_runtime_output(data: dict[str, Any], text: str) -> dict[str, Any]:
    packet_chain = data.get("PACKET_CHAIN") or data.get("packet_chain") or []
    final_verifier = data.get("FINAL_VERIFIER") or data.get("VERIFIER") or {}
    language = data.get("LANGUAGE_RECONSTRUCTION") or {}
    timeline = []

    for idx, pkt in enumerate(packet_chain):
        if not isinstance(pkt, dict):
            continue
        timeline.append(
            {
                "index": idx,
                "step": pkt.get("step") or pkt.get("STEP") or pkt.get("packet_type") or f"S{idx}",
                "packet_type": pkt.get("packet_type") or pkt.get("PACKET_TYPE") or "UNKNOWN_PACKET",
                "packet_hash": pkt.get("packet_hash") or packet_field(pkt, "D8_envelope", "packet_hash"),
                "parent_packet_hash": pkt.get("parent_packet_hash") or "",
                "risk_code": pkt.get("risk_code") or packet_field(pkt, "D7_risk", "risk_code"),
                "decision": pkt.get("decision") or packet_field(pkt, "D7_risk", "decision"),
                "table_ref": pkt.get("table_ref") or packet_field(pkt, "D6_gt", "table_ref"),
                "template_ref": pkt.get("template_ref") or packet_field(pkt, "D6_gt", "template_ref"),
                "packet": pkt,
            }
        )

    if not timeline and isinstance(data.get("PACKET"), dict):
        pkt = data["PACKET"]
        timeline.append(
            {
                "index": 0,
                "step": "SINGLE_PACKET",
                "packet_type": pkt.get("packet_type", "W7TP_PACKET"),
                "packet_hash": packet_field(pkt, "D8_envelope", "packet_hash"),
                "parent_packet_hash": "",
                "risk_code": packet_field(pkt, "D7_risk", "risk_code"),
                "decision": packet_field(pkt, "D7_risk", "decision"),
                "table_ref": packet_field(pkt, "D6_gt", "table_ref"),
                "template_ref": packet_field(pkt, "D6_gt", "template_ref"),
                "packet": pkt,
            }
        )

    decision = final_verifier.get("decision") or data.get("decision") or "HOLD"
    zh_tw = language.get("zh_TW") or language.get("zh-TW") or language.get("text") or ""
    semantic_ir = language.get("semantic_ir") if isinstance(language.get("semantic_ir"), dict) else {}
    scene_context = semantic_ir.get("scene_context") or {}
    forbidden_actions = []
    if packet_chain:
        last_packet = packet_chain[-1] if isinstance(packet_chain[-1], dict) else {}
        forbidden_actions = packet_field(last_packet, "D5_execution", "forbidden_actions") or []
    requires_human_review = decision in {"HOLD", "BLOCK"}

    human_response = _render_human_response_payload(
        final_verifier,
        source_channel=str(data.get("CHANNEL") or data.get("channel") or "web"),
    )
    answer_text = human_response.get("reply_text") or zh_tw or "無法產生候選回覆。"
    return {
        "STATE": "PASS_W7TP_PACKET_INFERENCE_COCKPIT_CHAT",
        "RUN_MODE": "MODEL_FREE_PACKET_BY_PACKET_INFERENCE",
        "SAFETY_FLAGS": SAFETY_FLAGS,
        "INPUT_TEXT_HASH": sha256_text(text),
        "PACKET_CHAIN": packet_chain,
        "FINAL_VERIFIER": {
            **final_verifier,
            "forbidden_actions": forbidden_actions,
            "requires_human_review": requires_human_review,
        },
        "LANGUAGE_RECONSTRUCTION": language,
        "COCKPIT_VIEW": {
            "timeline": timeline,
            "badges": {
                "decision": decision,
                "model_lane": "OFF",
                "future_model_mode": "CANDIDATE_ONLY",
                "pr_layer": "PENDING",
                "llm_authority": False,
                "verifier_decision_locked": True,
                "model_output": "candidate-only",
                "lookup_lane": "ACTIVE",
                "verifier_authority": "TOTAL_FIELD",
                "external_api": False,
                "db_write": False,
                "payment_capture": False,
                "member_plaintext_read": False,
            },
            "summary": {
                "decision": decision,
                "output": answer_text,
                "raw_verified_draft": zh_tw or answer_text,
                "pr_refined_answer": answer_text,
                "decision_locked": True,
                "packet_count": len(timeline),
            },
            "human_response": human_response,
            "scene_context": scene_context,
        },
    }


def build_pr_request(result: dict[str, Any]) -> dict[str, Any]:
    verifier = result.get("FINAL_VERIFIER") or {}
    language = result.get("LANGUAGE_RECONSTRUCTION") or {}
    semantic_ir = language.get("semantic_ir") or {}
    identity_profile = semantic_ir.get("identity_profile") or {}
    scene_context = semantic_ir.get("scene_context") or {}
    return {
        "packet_type": "TOTAL_FIELD_PR_REQUEST_PACKET",
        "version": "v0.1",
        "input_text_hash": result.get("INPUT_TEXT_HASH", ""),
        "verified_decision": verifier.get("decision", "HOLD"),
        "verifier_reasons": verifier.get("reasons", []),
        "semantic_ir": semantic_ir,
        "safe_answer_draft": language.get("zh_TW", ""),
        "forbidden_actions": verifier.get("forbidden_actions", []),
        "safety_flags": result.get("SAFETY_FLAGS", SAFETY_FLAGS),
        "identity_state": {
            "claimed_identity": bool(identity_profile.get("claimed_identity_packet")),
            "accepted_as_truth": bool(identity_profile.get("accepted_as_truth", False)),
            "verified_role_ref": None,
            "dev_identity_override": scene_context.get("dev_identity_override"),
        },
        "cloud_model_ref": str(result.get("requested_ai_key_ref") or ""),
        "public_context_only": True,
    }


def _safe_ai_key_ref(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) > 200:
        return ""
    return text


def _safe_translator_profile(value: str) -> str:
    profile = str(value or "").strip().lower()
    if profile in {"raw", "human", "poetic", "compact"}:
        return profile
    return "raw"


def _render_gate_human_summary(
    payload: dict[str, Any],
    request_text: str,
    channel: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not CANONICAL_GATE_AVAILABLE or run_total_field_gate is None or render_human_response is None:
        return payload, payload.get("FINAL_VERIFIER") if isinstance(payload.get("FINAL_VERIFIER"), dict) else {}

    try:
        gate_request = {
            "text": request_text,
            "source_channel": channel,
            "channel": channel,
            "include_adi_5d": True,
        }
        total_field_gate = run_total_field_gate(gate_request)
        human_response = render_human_response(total_field_gate, channel=channel)

        # Keep runtime verifier for traceability while replacing authority decision with total-field.
        runtime_verifier = payload.get("FINAL_VERIFIER") if isinstance(payload.get("FINAL_VERIFIER"), dict) else {}
        total_field_gate = dict(total_field_gate)
        if runtime_verifier:
            total_field_gate["runtime_verifier"] = runtime_verifier

        payload["FINAL_VERIFIER"] = total_field_gate
        payload["FINAL_VERIFIER"]["authority"] = "total_field_gate"

        decision = str(total_field_gate.get("decision") or "HOLD")
        reply_text = str(human_response.get("reply_text") or "")
        if not reply_text:
            reply_text = payload.get("LANGUAGE_RECONSTRUCTION", {}).get("zh_TW", "") or request_text

        payload.setdefault("LANGUAGE_RECONSTRUCTION", {})
        payload["LANGUAGE_RECONSTRUCTION"]["zh_TW"] = reply_text
        payload["LANGUAGE_RECONSTRUCTION"]["raw_verified_draft"] = reply_text
        payload["LANGUAGE_RECONSTRUCTION"]["pr_refined_zh_TW"] = reply_text
        payload.setdefault("COCKPIT_VIEW", {}).setdefault("summary", {})
        summary = payload["COCKPIT_VIEW"]["summary"]
        summary["decision"] = decision
        summary["output"] = reply_text
        summary["raw_verified_draft"] = reply_text
        summary["pr_refined_answer"] = reply_text
        summary["decision_locked"] = True
        payload["COCKPIT_VIEW"]["human_response"] = human_response
        payload["COCKPIT_VIEW"]["badges"]["decision"] = decision
        payload["COCKPIT_VIEW"]["badges"]["verifier_decision_locked"] = True
        payload["COCKPIT_VIEW"]["badges"]["verifier_authority"] = "TOTAL_FIELD"
        payload["COCKPIT_VIEW"]["summary"]["packet_count"] = len(payload.get("COCKPIT_VIEW", {}).get("timeline", []))
        payload["TOTAL_FIELD_GATE"] = total_field_gate
        return payload, human_response
    except Exception:
        # Keep legacy behavior if gate layer fails; never fail public API rendering.
        return payload, payload.get("FINAL_VERIFIER") if isinstance(payload.get("FINAL_VERIFIER"), dict) else {}


def apply_pr_layer(
    result: dict[str, Any], ai_key_ref: str = "", cloud_translator_profile: str = ""
) -> dict[str, Any]:
    if not PR_LAYER.exists():
        result["COCKPIT_VIEW"]["badges"]["pr_layer"] = "TEMPLATE_FALLBACK"
        result["COCKPIT_VIEW"]["badges"]["model_lane"] = "OFF"
        result["COCKPIT_VIEW"]["cloud_model"] = {
            "requested": False,
            "requested_ai_key_ref": "",
            "translator_profile": _safe_translator_profile(cloud_translator_profile),
            "response_model_lane": "OFF",
            "response_text": "",
            "response_text_available": False,
            "response_packet": {},
        }
        return result

    request_packet = build_pr_request(result)
    model_ref = _safe_ai_key_ref(ai_key_ref)
    if model_ref:
        request_packet["cloud_model_ref"] = model_ref
        result["requested_ai_key_ref"] = model_ref
    try:
        proc = subprocess.run(
            [
                "python3",
                str(PR_LAYER),
                "--request-json",
                json.dumps(request_packet, ensure_ascii=False),
                *(["--model", model_ref] if model_ref else ["--disable-model"]),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=12,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or proc.stdout or "PR layer nonzero")[:1000])
        pr_data = json.loads(proc.stdout)
    except Exception as exc:
        pr_data = {
            "STATE": "HOLD_PR_LAYER_FALLBACK",
            "MODEL_LANE": "TEMPLATE_FALLBACK",
            "REQUEST_PACKET": request_packet,
            "RESPONSE_PACKET": {
                "packet_type": "TOTAL_FIELD_PR_RESPONSE_PACKET",
                "candidate_only": True,
                "model_authority": False,
                "verified_decision_unchanged": True,
                "text_zh_TW": request_packet["safe_answer_draft"],
                "error": repr(exc),
            },
            "FINAL_TEXT": request_packet["safe_answer_draft"],
        }

    final_text = str(pr_data.get("FINAL_TEXT") or request_packet["safe_answer_draft"])
    original_decision = result.get("FINAL_VERIFIER", {}).get("decision", "HOLD")
    response_packet = pr_data.get("RESPONSE_PACKET") if isinstance(pr_data.get("RESPONSE_PACKET"), dict) else {}
    model_lane = str(pr_data.get("MODEL_LANE") or "TEMPLATE_FALLBACK")
    response_text = str(response_packet.get("text_zh_TW") or final_text or request_packet["safe_answer_draft"]).strip()
    result["LANGUAGE_RECONSTRUCTION"]["raw_verified_draft"] = request_packet["safe_answer_draft"]
    result["LANGUAGE_RECONSTRUCTION"]["pr_refined_zh_TW"] = final_text
    result["LANGUAGE_RECONSTRUCTION"]["zh_TW"] = final_text
    result["PR_LAYER"] = {
        "STATE": pr_data.get("STATE"),
        "MODEL_LANE": pr_data.get("MODEL_LANE", "TEMPLATE_FALLBACK"),
        "REQUEST_PACKET": pr_data.get("REQUEST_PACKET", request_packet),
        "RESPONSE_PACKET": response_packet,
        "decision_locked": True,
        "verified_decision": original_decision,
    }
    result["COCKPIT_VIEW"]["badges"]["pr_layer"] = pr_data.get("MODEL_LANE", "TEMPLATE_FALLBACK")
    result["COCKPIT_VIEW"]["badges"]["model_lane"] = model_lane
    result["COCKPIT_VIEW"]["badges"]["llm_authority"] = False
    result["COCKPIT_VIEW"]["badges"]["verifier_decision_locked"] = True
    result["COCKPIT_VIEW"]["badges"]["model_output"] = "candidate-only"
    result["COCKPIT_VIEW"]["cloud_model"] = {
        "requested": bool(model_ref),
        "requested_ai_key_ref": model_ref,
        "translator_profile": _safe_translator_profile(cloud_translator_profile),
        "response_model_lane": model_lane,
        "response_text": response_text,
        "response_text_available": bool(response_text),
        "response_packet": response_packet,
    }
    result["COCKPIT_VIEW"]["summary"]["output"] = final_text
    result["COCKPIT_VIEW"]["summary"]["raw_verified_draft"] = request_packet["safe_answer_draft"]
    result["COCKPIT_VIEW"]["summary"]["pr_refined_answer"] = final_text
    result["COCKPIT_VIEW"]["summary"]["decision_locked"] = True
    result["FINAL_VERIFIER"]["decision"] = original_decision
    result["CLOUD_MODEL_REF"] = model_ref
    return result


def fallback_response(text: str, reason: str) -> dict[str, Any]:
    run_id = "fallback_" + uuid.uuid4().hex[:12]
    now = int(time.time())
    packet_hash = sha256_text(text + run_id)
    seal = sha256_text(packet_hash + ":seal")
    packet = {
        "packet_type": "W7TP_COCKPIT_FALLBACK_PACKET",
        "version": "v0.1",
        "step": "S_FALLBACK_HOLD",
        "parent_packet_hash": "",
        "D1_intent": {"intent_id": "unknown", "confidence_level": "L0"},
        "D2_state": {"state_buckets": {"fallback": True}},
        "D3_coordinate": {"channel": "web_cockpit"},
        "D4_evidence": {"input_hash": sha256_text(text), "run_id": run_id},
        "D5_execution": {
            "allowed_actions": ["ask_clarifying_question"],
            "forbidden_actions": ["payment_capture", "member_plaintext_read"],
        },
        "D6_gt": {"table_ref": "tables/fallback_v1", "template_ref": "templates/clarify_v1"},
        "D7_risk": {"risk_code": "runtime_error", "decision": "HOLD", "reasons": [reason]},
        "D8_envelope": {
            "packet_id": "pkt_" + uuid.uuid4().hex,
            "created_at_unix": now,
            "ttl_seconds": 300,
            "nonce": uuid.uuid4().hex,
            "packet_hash": packet_hash,
            "seal": seal,
        },
    }
    output = "目前總場 runtime 暫時無法完成推理，已進入 HOLD 補問流程。"
    timeline = [
        {
            "index": 0,
            "step": "S_FALLBACK_HOLD",
            "packet_type": packet["packet_type"],
            "packet_hash": packet_hash,
            "parent_packet_hash": "",
            "risk_code": "runtime_error",
            "decision": "HOLD",
            "table_ref": "tables/fallback_v1",
            "template_ref": "templates/clarify_v1",
            "packet": packet,
        }
    ]
    return {
        "STATE": "HOLD_RUNTIME_ERROR",
        "RUN_MODE": "FALLBACK_MODEL_FREE_HOLD",
        "SAFETY_FLAGS": SAFETY_FLAGS,
        "INPUT_TEXT_HASH": sha256_text(text),
        "PACKET_CHAIN": [packet],
        "FINAL_VERIFIER": {
            "decision": "HOLD",
            "reasons": [reason],
            "forbidden_actions": ["payment_capture", "member_plaintext_read"],
            "requires_human_review": True,
        },
        "LANGUAGE_RECONSTRUCTION": {
            "semantic_ir": {"speech_act": "ASK_CONFIRMATION", "decision": "HOLD"},
            "zh_TW": output,
        },
        "COCKPIT_VIEW": {
            "timeline": timeline,
            "badges": {
                "decision": "HOLD",
                "model_lane": "OFF",
                "future_model_mode": "CANDIDATE_ONLY",
                "lookup_lane": "FALLBACK",
                "verifier_authority": "TOTAL_FIELD",
                "external_api": False,
                "db_write": False,
                "payment_capture": False,
                "member_plaintext_read": False,
            },
            "summary": {
                "decision": "HOLD",
                "output": _render_human_response_payload({"decision": "HOLD", "risk_level": "HIGH"}, "web").get("reply_text", output),
                "packet_count": 1,
            },
            "human_response": _render_human_response_payload({"decision": "HOLD", "risk_level": "HIGH"}, "web"),
        },
        "fallback": True,
        "error": reason,
    }


def run_runtime(
    text: str,
    branch: str,
    actor_role: str,
    channel: str,
    dev_role_ref: str = "",
    dev_identity_switch: bool = False,
    authenticated_role_ref: str = "",
    signed_identity_packet_ref: str = "",
    ai_key_ref: str = "",
    cloud_translator_profile: str = "",
) -> dict[str, Any]:
    if not RUNTIME.exists():
        return fallback_response(text, "runtime file missing")

    cmd_variants = [
        [
            "python3",
            str(RUNTIME),
            "--text",
            text,
            "--branch",
            branch,
            "--actor-role",
            actor_role,
            "--channel",
            channel,
            *(["--dev-role-ref", dev_role_ref, "--dev-identity-switch"] if dev_identity_switch and dev_role_ref else []),
            *(["--authenticated-role-ref", authenticated_role_ref] if authenticated_role_ref else []),
            *(["--signed-identity-packet-ref", signed_identity_packet_ref] if signed_identity_packet_ref else []),
        ],
        ["python3", str(RUNTIME), "--text", text],
    ]
    last_error = ""
    for cmd in cmd_variants:
        try:
            result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=15, check=False)
            if result.returncode != 0:
                last_error = (result.stderr or result.stdout or "runtime nonzero")[:2000]
                continue
            data = json.loads(result.stdout)
            payload = normalize_runtime_output(data, text)
            payload, _ = _render_gate_human_summary(payload, text, channel)
            payload["requested_ai_key_ref"] = _safe_ai_key_ref(ai_key_ref)
            payload["CLOUD_MODEL_REF"] = _safe_ai_key_ref(ai_key_ref)
            payload["cloud_translator_profile"] = _safe_translator_profile(cloud_translator_profile)
            return apply_pr_layer(
                payload,
                ai_key_ref=_safe_ai_key_ref(ai_key_ref),
                cloud_translator_profile=_safe_translator_profile(cloud_translator_profile),
            )
        except Exception as exc:  # Runtime fallback must never crash the UI.
            last_error = repr(exc)
    return fallback_response(text, last_error or "runtime failed")


def static_target(path: str) -> Path | None:
    route = path.split("?", 1)[0]
    if route == "/":
        route = "/index.html"
    rel = route.lstrip("/")
    target = (WEB_DIR / rel).resolve()
    try:
        target.relative_to(WEB_DIR.resolve())
    except ValueError:
        return None
    return target


class CockpitHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/api/health":
            return safe_json_response(
                self,
                200,
                {
                    "STATE": "PASS_W7TP_PACKET_INFERENCE_COCKPIT_HEALTH",
                    "runtime_available": RUNTIME.exists(),
                    "external_api": False,
                    "db_write": False,
                    "payment_capture": False,
                    "member_plaintext_read": False,
                },
            )

        target = static_target(self.path)
        if target is None or not target.exists() or not target.is_file():
            self.send_response(404)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(b"not found")
            return

        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        body = target.read_bytes()
        if content_type.startswith("text/") or content_type in {"application/javascript"}:
            content_type += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path != "/api/chat":
            return safe_json_response(self, 404, {"STATE": "NOT_FOUND"})

        try:
            body = read_json_body(self)
            text = str(body.get("text", "")).strip()
            branch = str(body.get("branch", "cafe_main"))
            actor_role = str(body.get("actor_role", "counter_ai"))
            channel = str(body.get("channel", "web_cockpit"))
            dev_role_ref = str(body.get("dev_role_ref", ""))
            dev_identity_switch = bool(body.get("dev_identity_switch", False))
            authenticated_role_ref = str(body.get("authenticated_role_ref", ""))
            signed_identity_packet_ref = str(body.get("signed_identity_packet_ref", ""))
            ai_key_ref = str(body.get("ai_key_ref", ""))
            cloud_translator_profile = str(body.get("cloud_translator_profile", "raw"))
            if not text:
                return safe_json_response(self, 400, {"STATE": "HOLD_EMPTY_TEXT"})

            result = run_runtime(
                text,
                branch,
                actor_role,
                channel,
                dev_role_ref=dev_role_ref,
                dev_identity_switch=dev_identity_switch,
                authenticated_role_ref=authenticated_role_ref,
                signed_identity_packet_ref=signed_identity_packet_ref,
                ai_key_ref=ai_key_ref,
                cloud_translator_profile=cloud_translator_profile,
            )
            RUN_ROOT.mkdir(parents=True, exist_ok=True)
            run_file = RUN_ROOT / f"chat_{int(time.time())}_{uuid.uuid4().hex[:8]}.json"
            audit = dict(result)
            audit["INPUT_TEXT"] = "[NOT_STORED]"
            run_file.write_text(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            result["COCKPIT_VIEW"]["summary"]["audit_file"] = str(run_file.relative_to(ROOT))

            return safe_json_response(self, 200, result)
        except Exception as exc:
            return safe_json_response(self, 500, fallback_response("", "server error: " + repr(exc)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    WEB_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), CockpitHandler)
    print("STATE=PASS_W7TP_PACKET_INFERENCE_COCKPIT_SERVER_START")
    print(f"URL=http://{args.host}:{args.port}/")
    print("SAFETY_FLAGS=" + json.dumps(SAFETY_FLAGS, sort_keys=True))
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
