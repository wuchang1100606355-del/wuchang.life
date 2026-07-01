#!/usr/bin/env python3
"""Total Field governance engine v2 manager sandbox.

The manager composes flow guard, router capacity guard, and GPT/cloud
candidate resilience policy. It is local-only and emits a safe decision record
without raw packet echo.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from w7tp_cloud_candidate_resilience_guard import (
    SAFETY_FLAGS,
    evaluate_cloud_resilience,
    packet_hash,
    refined_secret_value_check,
)


HOLD_STATES = {
    "HOLD_SECRET_VALUE_DETECTED",
    "HOLD_RAW_PACKET_ECHO",
    "HOLD_CLOUD_AUTHORITY",
    "HOLD_CANDIDATE_POLICY",
    "HOLD_CLOUD_UNAVAILABLE",
    "HOLD_CLOUD_LATENCY_EXCEEDED",
    "HOLD_ROUTER_CAPACITY_NOT_VERIFIED",
    "HOLD_USB_STORAGE_ERRORS_DETECTED",
    "HOLD_MISSING_EVIDENCE",
    "HOLD_UNAPPROVED_ROUTER_ACTION",
}


def load_packet(path: str) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("root JSON value must be an object")
    return data


def normalize_coordinate(packet: dict[str, Any]) -> list[str]:
    coordinate = packet.get("coordinate", [])
    if isinstance(coordinate, list):
        return sorted({str(item) for item in coordinate})
    if isinstance(coordinate, dict):
        return sorted(f"{key}:{value}" for key, value in coordinate.items())
    if coordinate:
        return [str(coordinate)]
    return ["local"]


def router_capacity_gate(packet: dict[str, Any]) -> str:
    guard = packet.get("router_capacity_guard")
    if not isinstance(guard, dict):
        return "HOLD_ROUTER_CAPACITY_NOT_VERIFIED"
    if guard.get("required_before_execution") is not True:
        return "HOLD_ROUTER_CAPACITY_NOT_VERIFIED"
    return str(guard.get("status") or "HOLD_ROUTER_CAPACITY_NOT_VERIFIED")


def blocked_router_action(packet: dict[str, Any], capacity_gate: str) -> str | None:
    if not capacity_gate.startswith("HOLD_"):
        return None
    policy = packet.get("policy") if isinstance(packet.get("policy"), dict) else {}
    blocked_fields = {
        "usb_dead_letter_enable": "USB mailbox enable attempted while capacity guard is HOLD",
        "jffs_pointer_write": "JFFS pointer write attempted while capacity guard is HOLD",
        "router_write": "router write attempted while capacity guard is HOLD",
        "service_restart": "service restart attempted while capacity guard is HOLD",
    }
    for key, reason in blocked_fields.items():
        value = policy.get(key, "HOLD")
        if value not in ("HOLD", False, None):
            return reason
    return None


def endpoint_ref_summary(packet: dict[str, Any]) -> dict[str, Any]:
    endpoints = packet.get("endpoints") if isinstance(packet.get("endpoints"), dict) else {}
    return {
        "endpoint_ref_keys": sorted(endpoints.keys()),
        "public_ip_ref_present": bool(endpoints.get("public_ip_ref")),
        "ddns_ref_present": bool(endpoints.get("ddns_ref")),
        "lan_router_ref_present": bool(endpoints.get("lan_router_ref")),
        "router_password_saved": bool(endpoints.get("router_password_saved")),
    }


def safe_summary(packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "intent": packet.get("intent"),
        "coordinate_normalized": normalize_coordinate(packet),
        "evidence_ref_present": bool(packet.get("evidence_ref")),
        "endpoint_refs": endpoint_ref_summary(packet),
        "top_level_keys": sorted(packet.keys()),
    }


def manager_decision(packet: dict[str, Any]) -> dict[str, Any]:
    secret_check = refined_secret_value_check(packet)
    capacity_gate = router_capacity_gate(packet)
    cloud_result = evaluate_cloud_resilience(packet)
    raw_packet_echo = bool(packet.get("raw_packet_echo") or cloud_result.get("safe_summary", {}).get("raw_packet_echo"))
    errors: list[str] = []
    warnings: list[str] = []
    state = "PASS_MANAGER_SANDBOX_READY"
    decision = "UI_STATUS_ONLY"

    if not secret_check["ok"]:
        state = "HOLD_SECRET_VALUE_DETECTED"
        decision = "HOLD"
        errors.append("refined secret value check failed")
    elif raw_packet_echo:
        state = "HOLD_RAW_PACKET_ECHO"
        decision = "HOLD"
        errors.append("raw packet echo requested")
    elif str(cloud_result.get("state", "")).startswith("HOLD_"):
        state = str(cloud_result["state"])
        decision = "HOLD"
        errors.extend(str(item) for item in cloud_result.get("errors", []))
    else:
        blocked_action = blocked_router_action(packet, capacity_gate)
        if blocked_action:
            state = "HOLD_UNAPPROVED_ROUTER_ACTION"
            decision = "HOLD"
            errors.append(blocked_action)
        elif cloud_result.get("decision") in {"FALLBACK_LOCAL_LOOKUP", "QUEUE_CANDIDATE", "DEAD_LETTER_REQUIRED"}:
            decision = str(cloud_result["decision"])
            warnings.extend(str(item) for item in cloud_result.get("warnings", []))
        elif capacity_gate.startswith("HOLD_"):
            decision = "UI_STATUS_ONLY"
            warnings.append(f"router capacity gate remains {capacity_gate}")

    return {
        "STATE": state,
        "state": state,
        "decision": decision,
        "errors": errors,
        "warnings": warnings,
        "router_capacity_gate": capacity_gate,
        "cloud_resilience_gate": str(cloud_result.get("state")),
        "cloud_resilience_decision": str(cloud_result.get("decision")),
        "command_allowed": False,
        "requires_human_approval": True,
        "packet_hash": packet_hash(packet),
        "raw_packet_echo": False,
        "safe_summary": safe_summary(packet),
        "refined_secret_value_check": secret_check,
        "safety": dict(SAFETY_FLAGS),
        "cloud_result_safe_summary": cloud_result.get("safe_summary", {}),
        "cloud_circuit_breaker": cloud_result.get("circuit_breaker", {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP Total Field governance engine v2 manager sandbox.")
    parser.add_argument("--file", required=True)
    args = parser.parse_args()

    try:
        packet = load_packet(args.file)
        result = manager_decision(packet)
    except Exception as exc:  # noqa: BLE001 - CLI must return structured HOLD.
        result = {
            "STATE": "HOLD_MISSING_EVIDENCE",
            "state": "HOLD_MISSING_EVIDENCE",
            "decision": "HOLD",
            "errors": [str(exc)],
            "warnings": [],
            "command_allowed": False,
            "requires_human_approval": True,
            "router_capacity_gate": "HOLD_MISSING_EVIDENCE",
            "cloud_resilience_gate": "HOLD_MISSING_EVIDENCE",
            "packet_hash": "sha256:" + "0" * 64,
            "raw_packet_echo": False,
            "safety": dict(SAFETY_FLAGS),
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if str(result.get("state", "")).startswith("HOLD_") else 0


if __name__ == "__main__":
    raise SystemExit(main())
