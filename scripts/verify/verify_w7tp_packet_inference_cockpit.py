#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify the local W7TP packet inference cockpit."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "tools" / "w7tp_packet_inference_cockpit_server.py"
RUN_ROOT = ROOT / "runtime" / "total_field" / "packet_inference_cockpit"

REQUIRED_FILES = [
    "tools/w7tp_packet_inference_cockpit_server.py",
    "web/packet_inference_cockpit/index.html",
    "web/packet_inference_cockpit/app.js",
    "web/packet_inference_cockpit/styles.css",
    "scripts/verify/verify_w7tp_packet_inference_cockpit.py",
    "schemas/field/W7TP_PACKET_INFERENCE_COCKPIT_API_V01.schema.note.json",
    "docs/total_field/W7TP_PACKET_INFERENCE_COCKPIT_SPEC.md",
]


def fail(message: str) -> None:
    print(f"FAIL={message}")
    print("STATE=HOLD_VERIFY_W7TP_PACKET_INFERENCE_COCKPIT")
    raise SystemExit(1)


def check(condition: bool, name: str) -> None:
    print(f"{name}={'PASS' if condition else 'FAIL'}")
    if not condition:
        fail(name)


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def choose_port() -> int:
    for port in (8765, 8766):
        if port_free(port):
            return port
    fail("ports 8765 and 8766 unavailable")
    return 8766


def request_json(url: str, payload: dict | None = None) -> dict:
    if payload is None:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_health(base_url: str) -> dict:
    last_error = ""
    for _ in range(30):
        try:
            return request_json(base_url + "/api/health")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = repr(exc)
            time.sleep(0.2)
    fail("server health unavailable: " + last_error)
    return {}


def forbidden_actions(result: dict) -> list:
    verifier = result.get("FINAL_VERIFIER") or {}
    if isinstance(verifier.get("forbidden_actions"), list):
        return verifier["forbidden_actions"]
    chain = result.get("PACKET_CHAIN") or []
    if chain and isinstance(chain[-1], dict):
        execution = chain[-1].get("D5_execution") or {}
        return execution.get("forbidden_actions") or []
    return []


def main() -> int:
    for rel in REQUIRED_FILES:
        check((ROOT / rel).exists(), f"FILE_EXISTS_{rel}")

    compile_server = subprocess.run([sys.executable, "-m", "py_compile", str(SERVER)], cwd=ROOT, text=True, capture_output=True, check=False)
    check(compile_server.returncode == 0, "SERVER_PY_COMPILE")

    port = choose_port()
    proc = subprocess.Popen(
        [sys.executable, str(SERVER), "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    results: list[dict] = []
    try:
        health = wait_for_health(base_url)
        check(health.get("STATE") == "PASS_W7TP_PACKET_INFERENCE_COCKPIT_HEALTH", "HEALTH_STATE")
        check(health.get("runtime_available") is True, "HEALTH_RUNTIME_AVAILABLE")
        check(health.get("external_api") is False, "HEALTH_EXTERNAL_API_FALSE")
        check(health.get("db_write") is False, "HEALTH_DB_WRITE_FALSE")

        cases = [
            ("RECOMMEND", "我今天有點累，想喝不太苦的，幫我推薦"),
            ("PAYMENT", "幫我直接結帳付款"),
            ("MEMBER", "我要查會員完整電話和地址"),
            ("ALLERGY", "我對牛奶有點敏感，想喝順口的"),
            ("UNKNOWN", "qqq xyz 未知請求"),
            ("PROFILE", "你沒有我的資訊嗎"),
            ("CLAIMED_IDENTITY", "我是創辦人江政隆你認識我嗎"),
            ("ROLE", "我的角色是什麼"),
        ]
        for label, text in cases:
            result = request_json(
                base_url + "/api/chat",
                {"text": text, "branch": "cafe_main", "actor_role": "counter_ai", "channel": "web_cockpit"},
            )
            results.append({"label": label, "result": result})
            check(result.get("RUN_MODE") in {"MODEL_FREE_PACKET_BY_PACKET_INFERENCE", "FALLBACK_MODEL_FREE_HOLD"}, f"{label}_RUN_MODE")
            check("COCKPIT_VIEW" in result, f"{label}_COCKPIT_VIEW")
            check(len(result.get("COCKPIT_VIEW", {}).get("timeline", [])) >= 1, f"{label}_TIMELINE")
            check(all(value is False for value in (result.get("SAFETY_FLAGS") or {}).values()), f"{label}_SAFETY_FALSE")

        recommend = results[0]["result"]
        payment = results[1]["result"]
        member = results[2]["result"]
        allergy = results[3]["result"]
        unknown = results[4]["result"]
        profile = results[5]["result"]
        claimed_identity = results[6]["result"]
        role = results[7]["result"]

        check(recommend.get("FINAL_VERIFIER", {}).get("decision") != "BLOCK", "RECOMMEND_NOT_BLOCK")
        check(payment.get("FINAL_VERIFIER", {}).get("decision") in {"HOLD", "BLOCK"}, "PAYMENT_HOLD_OR_BLOCK")
        check("payment_capture" in forbidden_actions(payment), "PAYMENT_CAPTURE_FORBIDDEN")
        check(member.get("FINAL_VERIFIER", {}).get("decision") in {"BLOCK", "HOLD"}, "MEMBER_BLOCK_OR_HOLD")
        check(member.get("SAFETY_FLAGS", {}).get("MEMBER_PLAINTEXT_READ") is False, "MEMBER_PLAINTEXT_PERMISSION_FALSE")
        allergy_decision = allergy.get("FINAL_VERIFIER", {}).get("decision")
        allergy_text = json.dumps(allergy, ensure_ascii=False)
        check(allergy_decision == "HOLD" or "allergy" in allergy_text or "敏感" in allergy_text, "ALLERGY_HOLD_OR_RISK")
        check(unknown.get("FINAL_VERIFIER", {}).get("decision") == "HOLD", "UNKNOWN_HOLD")
        check(profile.get("FINAL_VERIFIER", {}).get("decision") != "BLOCK", "PROFILE_NOT_BLOCK")
        check(profile.get("SAFETY_FLAGS", {}).get("MEMBER_PLAINTEXT_READ") is False, "PROFILE_MEMBER_PLAINTEXT_FALSE")
        claimed_text = json.dumps(claimed_identity, ensure_ascii=False)
        check(claimed_identity.get("FINAL_VERIFIER", {}).get("decision") == "HOLD", "CLAIMED_IDENTITY_HOLD")
        check("CLAIMED_IDENTITY_PACKET" in claimed_text, "CLAIMED_IDENTITY_PACKET_PRESENT")
        check('"accepted_as_truth": false' in claimed_text, "CLAIMED_IDENTITY_NOT_TRUSTED")
        check(role.get("FINAL_VERIFIER", {}).get("decision") == "HOLD", "ROLE_HOLD")
        check("member_plaintext_read" in forbidden_actions(role), "ROLE_MEMBER_PLAINTEXT_FORBIDDEN")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)

    run_id = time.strftime("%Y%m%d_%H%M%S")
    report_dir = RUN_ROOT / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "STATE": "PASS_VERIFY_W7TP_PACKET_INFERENCE_COCKPIT",
        "RUN_ID": run_id,
        "base_url": base_url,
        "cases": [
            {
                "label": row["label"],
                "input_hash": row["result"].get("INPUT_TEXT_HASH"),
                "decision": row["result"].get("FINAL_VERIFIER", {}).get("decision"),
                "packet_count": len(row["result"].get("COCKPIT_VIEW", {}).get("timeline", [])),
            }
            for row in results
        ],
    }
    report_path = report_dir / "VERIFY_REPORT.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("STATE=PASS_VERIFY_W7TP_PACKET_INFERENCE_COCKPIT")
    print(f"REPORT={report_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
