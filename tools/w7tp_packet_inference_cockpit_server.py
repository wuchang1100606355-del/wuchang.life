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
RUN_ROOT = ROOT / "runtime" / "total_field" / "packet_inference_cockpit"

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
    forbidden_actions = []
    if packet_chain:
        last_packet = packet_chain[-1] if isinstance(packet_chain[-1], dict) else {}
        forbidden_actions = packet_field(last_packet, "D5_execution", "forbidden_actions") or []
    requires_human_review = decision in {"HOLD", "BLOCK"}

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
                "lookup_lane": "ACTIVE",
                "verifier_authority": "TOTAL_FIELD",
                "external_api": False,
                "db_write": False,
                "payment_capture": False,
                "member_plaintext_read": False,
            },
            "summary": {
                "decision": decision,
                "output": zh_tw,
                "packet_count": len(timeline),
            },
        },
    }


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
            "summary": {"decision": "HOLD", "output": output, "packet_count": 1},
        },
        "fallback": True,
        "error": reason,
    }


def run_runtime(text: str, branch: str, actor_role: str, channel: str) -> dict[str, Any]:
    if not RUNTIME.exists():
        return fallback_response(text, "runtime file missing")

    cmd_variants = [
        ["python3", str(RUNTIME), "--text", text, "--branch", branch, "--actor-role", actor_role, "--channel", channel],
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
            return normalize_runtime_output(data, text)
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
            if not text:
                return safe_json_response(self, 400, {"STATE": "HOLD_EMPTY_TEXT"})

            result = run_runtime(text, branch, actor_role, channel)
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
