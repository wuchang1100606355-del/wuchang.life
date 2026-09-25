#!/usr/bin/env python3
"""Local-only GPT/cloud candidate resilience guard.

This tool reads a JSON fixture, simulates cloud latency/availability policy,
and returns a safe decision. It never calls cloud services, reads env, SSHes,
writes DB, deploys, restarts services, or emits the raw packet.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


SECRET_VALUE_KEYS = {
    "refresh_token",
    "access_token",
    "client_secret",
    "router_password",
    "private_key",
    "api_key",
    "secret",
    "token",
}

SECRET_VALUE_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
]

SAFETY_FLAGS = {
    "secret_read": False,
    "env_dump": False,
    "member_plaintext_read": False,
    "raw_audio_read": False,
    "db_write": False,
    "deploy": False,
    "service_restart": False,
    "production_release": False,
    "external_cloud_call": False,
    "router_write": False,
    "router_reboot": False,
    "router_service_restart": False,
    "usb_write": False,
    "jffs_write": False,
}


def walk(obj: Any, path: str = "$") -> list[tuple[str, str, Any]]:
    out: list[tuple[str, str, Any]] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            current = f"{path}.{key}"
            out.append((current, key, value))
            out.extend(walk(value, current))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            out.extend(walk(value, f"{path}[{idx}]"))
    return out


def load_packet(path: str) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("root JSON value must be an object")
    return data


def packet_hash(packet: dict[str, Any]) -> str:
    encoded = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def refined_secret_value_check(packet: dict[str, Any]) -> dict[str, Any]:
    hits: list[dict[str, Any]] = []
    for path, key, value in walk(packet):
        lowered = str(key).lower()
        if lowered in SECRET_VALUE_KEYS:
            if isinstance(value, str) and value.strip():
                hits.append({"path": path, "key": key, "value_present": True})
            elif value not in ("", None, False):
                hits.append({"path": path, "key": key, "value_present": True})
        if isinstance(value, str):
            for pattern in SECRET_VALUE_PATTERNS:
                if pattern.search(value):
                    hits.append({"path": path, "key": key, "pattern": pattern.pattern, "value_present": True})
                    break
    return {
        "STATE": "REFINED_SECRET_VALUE_CHECK_PASS" if not hits else "REFINED_SECRET_VALUE_CHECK_HOLD",
        "ok": not hits,
        "hits": hits,
    }


def as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "pass", "available"}
    return bool(value)


def as_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def cloud_context(packet: dict[str, Any]) -> dict[str, Any]:
    cloud = packet.get("cloud") if isinstance(packet.get("cloud"), dict) else packet
    return {
        "latency_ms": as_int(cloud.get("latency_ms"), 0),
        "timeout_ms": max(1, as_int(cloud.get("timeout_ms"), 5000)),
        "cloud_available": as_bool(cloud.get("cloud_available", cloud.get("available")), True),
        "cloud_authority": as_bool(cloud.get("cloud_authority"), False),
        "candidate_only": as_bool(cloud.get("candidate_only"), True),
        "fallback_available": as_bool(cloud.get("fallback_available"), False),
        "local_lookup_available": as_bool(cloud.get("local_lookup_available"), False),
        "queue_available": as_bool(cloud.get("queue_available"), False),
        "dead_letter_available": as_bool(cloud.get("dead_letter_available"), False),
        "raw_packet_echo": as_bool(cloud.get("raw_packet_echo", packet.get("raw_packet_echo")), False),
    }


def safe_summary(packet: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    coordinate = packet.get("coordinate", [])
    coordinate_markers = coordinate if isinstance(coordinate, list) else [str(coordinate)]
    endpoints = packet.get("endpoints") if isinstance(packet.get("endpoints"), dict) else {}
    return {
        "intent": packet.get("intent"),
        "coordinate_markers": [str(item) for item in coordinate_markers],
        "top_level_keys": sorted(packet.keys()),
        "evidence_ref_present": bool(packet.get("evidence_ref")),
        "endpoint_refs_present": sorted(endpoints.keys()),
        "latency_ms": context["latency_ms"],
        "timeout_ms": context["timeout_ms"],
        "cloud_available": context["cloud_available"],
        "candidate_only": context["candidate_only"],
        "raw_packet_echo": context["raw_packet_echo"],
    }


def evaluate_cloud_resilience(packet: dict[str, Any]) -> dict[str, Any]:
    context = cloud_context(packet)
    secret_check = refined_secret_value_check(packet)
    errors: list[str] = []
    warnings: list[str] = []
    decision = "UI_STATUS_ONLY"
    state = "PASS_CLOUD_CANDIDATE_RESILIENCE_READY"
    latency_exceeded = context["latency_ms"] > context["timeout_ms"]
    cloud_unavailable = not context["cloud_available"]
    circuit_breaker_reasons: list[str] = []

    if not secret_check["ok"]:
        errors.append("secret value detected")
        state = "HOLD_SECRET_VALUE_DETECTED"
        decision = "HOLD"
    elif context["raw_packet_echo"]:
        errors.append("raw packet echo requested")
        state = "HOLD_RAW_PACKET_ECHO"
        decision = "HOLD"
    elif context["cloud_authority"]:
        errors.append("cloud candidate attempted authority")
        state = "HOLD_CLOUD_AUTHORITY"
        decision = "HOLD"
    elif not context["candidate_only"]:
        errors.append("cloud result is not candidate-only")
        state = "HOLD_CANDIDATE_POLICY"
        decision = "HOLD"
    else:
        if latency_exceeded:
            warnings.append("cloud latency exceeded timeout")
            circuit_breaker_reasons.append("latency_exceeded")
        if cloud_unavailable:
            warnings.append("cloud unavailable")
            circuit_breaker_reasons.append("cloud_unavailable")
        if latency_exceeded or cloud_unavailable:
            if context["fallback_available"] and context["local_lookup_available"]:
                state = "FALLBACK_LOCAL_LOOKUP"
                decision = "FALLBACK_LOCAL_LOOKUP"
            elif context["queue_available"]:
                state = "QUEUE_CANDIDATE"
                decision = "QUEUE_CANDIDATE"
            elif context["dead_letter_available"]:
                state = "DEAD_LETTER_REQUIRED"
                decision = "DEAD_LETTER_REQUIRED"
            else:
                state = "HOLD_CLOUD_UNAVAILABLE" if cloud_unavailable else "HOLD_CLOUD_LATENCY_EXCEEDED"
                decision = "HOLD"
                errors.append("cloud failed and no fallback or queue is available")

    return {
        "STATE": state,
        "state": state,
        "decision": decision,
        "errors": errors,
        "warnings": warnings,
        "safe_summary": safe_summary(packet, context),
        "packet_hash": packet_hash(packet),
        "refined_secret_value_check": secret_check,
        "circuit_breaker": {
            "enabled": True,
            "open": bool(circuit_breaker_reasons),
            "reasons": circuit_breaker_reasons,
            "blocks_executable_cloud_output": True,
        },
        "cloud_call": False,
        "db_write": False,
        "router_write": False,
        "service_restart": False,
        "external_cloud_call": False,
        "safety": dict(SAFETY_FLAGS),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP cloud candidate resilience guard.")
    parser.add_argument("--file", required=True)
    args = parser.parse_args()

    try:
        packet = load_packet(args.file)
        result = evaluate_cloud_resilience(packet)
    except Exception as exc:  # noqa: BLE001 - CLI must return structured HOLD.
        result = {
            "STATE": "HOLD_MISSING_EVIDENCE",
            "state": "HOLD_MISSING_EVIDENCE",
            "decision": "HOLD",
            "errors": [str(exc)],
            "warnings": [],
            "cloud_call": False,
            "db_write": False,
            "router_write": False,
            "service_restart": False,
            "external_cloud_call": False,
            "safety": dict(SAFETY_FLAGS),
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if str(result.get("state", "")).startswith("HOLD_") else 0


if __name__ == "__main__":
    raise SystemExit(main())
