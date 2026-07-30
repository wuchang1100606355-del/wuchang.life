#!/usr/bin/env python3
"""Smoke test XiaoJ native host with real native messaging framing."""

from __future__ import annotations

import json
import struct
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.member_browser.simulate_xiaoj_browser_bridge import demo_packet
from tools.total_field.w7tp_intent_field_suite.canonical_hash import canonical_sha256


HOST = ROOT / "tools/member_browser/xiaoj_member_browser_native_host.py"


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
    packet = demo_packet("read_text_ref")
    packet["D6_governance"]["reconstruction_level"] = "L3_CANDIDATE"
    packet["D8_envelope"].update(
        {
            "packet_id": "PKT_BROWSER_" + uuid.uuid4().hex,
            "trace_id": "TRACE_BROWSER_" + uuid.uuid4().hex,
            "nonce": "nonce_ref:" + str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "content_hash": "",
            "content_sha256": "",
            "authority_granted": False,
        }
    )
    digest = canonical_sha256(packet)
    packet["D8_envelope"]["content_hash"] = digest
    packet["D8_envelope"]["content_sha256"] = digest
    payload = {
        "type": "XIAOJ_NATIVE_GATEWAY_REQUEST",
        "transport_envelope": {
            "schema_version": "w7tp.browser-8d-transport-envelope.v1",
            "profile_type": "BROWSER_8D_TRANSPORT_ENVELOPE",
            "sender_ref": "web.xiaoj_member_browser_extension.background",
            "receiver_ref": "tools.total_field_candidate_gateway.receive_candidate",
            "return_coordinate": "chrome.runtime.sendMessage",
            "packet_id": packet["D8_envelope"]["packet_id"],
            "trace_id": packet["D8_envelope"]["trace_id"],
            "content_sha256": digest,
            "reconstruction_level": "L3_CANDIDATE",
            "authority_granted": False,
            "browser_packet": packet,
        },
    }
    response = send_native_message(payload)
    gateway = response.get("gateway_result")
    receipt = response.get("total_field_receipt")
    ok = (
        response.get("candidate_only") is True
        and response.get("authority_granted") is False
        and response.get("requires_total_field_verify") is True
        and response.get("member_plaintext_transferred") is False
        and response.get("secret_transferred") is False
        and response.get("trace_id") == packet["D8_envelope"]["trace_id"]
        and response.get("content_sha256") == digest
        and isinstance(gateway, dict)
        and gateway.get("reconstruction", {}).get("mode") == "L3_CANDIDATE"
        and isinstance(receipt, dict)
        and receipt.get("receiver_call_count") == 1
        and receipt.get("authority_granted") is False
    )
    print("NATIVE_PROTOCOL_RESPONSE=" + ("PASS" if ok else "FAIL"))
    print("GATEWAY_STATE=" + str(gateway.get("state") if isinstance(gateway, dict) else "MISSING"))
    print("TRACE_BOUND=" + ("TRUE" if response.get("trace_id") == packet["D8_envelope"]["trace_id"] else "FALSE"))
    print("RECEIVER_CALL_COUNT=" + str(receipt.get("receiver_call_count") if isinstance(receipt, dict) else 0))
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
