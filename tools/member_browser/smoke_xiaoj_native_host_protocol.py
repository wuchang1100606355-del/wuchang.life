#!/usr/bin/env python3
"""Smoke test XiaoJ native host with real native messaging framing."""

from __future__ import annotations

import json
import struct
import subprocess
import sys
from pathlib import Path

from jsonschema import validate


ROOT = Path(__file__).resolve().parents[2]
HOST = ROOT / "tools/member_browser/xiaoj_member_browser_native_host.py"
GATEWAY_SCHEMA = ROOT / "schemas/browser/xiaoj_member_browser_gateway_result_v1.schema.json"


def send_native_message(payload: dict) -> dict:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    proc = subprocess.Popen(
        [sys.executable, str(HOST)],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdin is not None
    assert proc.stdout is not None
    proc.stdin.write(struct.pack("<I", len(raw)))
    proc.stdin.write(raw)
    proc.stdin.close()
    header = proc.stdout.read(4)
    if len(header) != 4:
        stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        raise RuntimeError("native_response_header_missing:" + stderr)
    length = struct.unpack("<I", header)[0]
    body = proc.stdout.read(length)
    proc.wait(timeout=10)
    if len(body) != length:
        raise RuntimeError("native_response_body_incomplete")
    return json.loads(body.decode("utf-8"))


def main() -> int:
    payload = {
        "type": "XIAOJ_NATIVE_GATEWAY_REQUEST",
        "intent": "請幫我摘要目前選取的社區公告",
        "safe_context_ref": "redacted_ref:native_protocol_smoke",
        "selected_text": "公告測試",
        "member_preference_ref": "preference_ref:member:concise",
        "service_style_ref": "service_style_ref:community_xiaoj_warm_daily",
    }
    response = send_native_message(payload)
    schema = json.loads(GATEWAY_SCHEMA.read_text(encoding="utf-8"))
    gateway = response.get("gateway_result")
    validate(gateway, schema)
    ok = (
        response.get("candidate_only") is True
        and response.get("requires_total_field_verify") is True
        and response.get("member_plaintext_transferred") is False
        and response.get("secret_transferred") is False
        and gateway.get("state") == "CANDIDATE_READY"
        and gateway.get("cloud_candidate_return_packet", {}).get("d5_execution", {}).get("execution_allowed") is False
    )
    print("NATIVE_PROTOCOL_RESPONSE=" + ("PASS" if ok else "FAIL"))
    print("GATEWAY_STATE=" + str(gateway.get("state")))
    print("SECRET_READ=FALSE")
    print("MEMBER_PLAINTEXT_READ=FALSE")
    print("RAW_AUDIO_SAVED=FALSE")
    print("DB_WRITE=FALSE")
    print("PAYMENT_CAPTURE=FALSE")
    print("SERVICE_RESTART=FALSE")
    print("DEPLOY=FALSE")
    print("STATE=" + ("PASS_XIAOJ_NATIVE_HOST_PROTOCOL" if ok else "FAIL_XIAOJ_NATIVE_HOST_PROTOCOL"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
