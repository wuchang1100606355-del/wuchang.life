#!/usr/bin/env python3
"""Offline XiaoJ LINE WORKS release readiness check.

This tool reads a human-filled refs JSON file, builds a candidate notification,
and runs the local LINE WORKS preflight. It performs no DB writes, no deploys,
no service restarts, no secret reads, and no external API calls.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/p1_intent_engine.py"
CONNECTOR = ROOT / "Taiji_Odoo/addons/wuchang_cafe_ai_gateway/services/lineworks_connector.py"
DEFAULT_REFS = ROOT / "packets/product_av_ordering_ai/lineworks_release_refs_template.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def is_placeholder_ref(value: Any) -> bool:
    text = str(value or "")
    return (
        not text
        or text.startswith("REF_")
        or text.endswith("_NO_SECRET")
        or text.endswith("_NO_MEMBER_PLAINTEXT")
        or text.endswith("_NO_TOKEN_VALUE")
        or text == "0" * 64
    )


def release_ref_readiness(refs: dict, required_refs: list[str]) -> dict:
    gate_refs = refs.get("lineworks_send") if isinstance(refs.get("lineworks_send"), dict) else {}
    missing = [key for key in required_refs if key not in gate_refs]
    unverified = []
    placeholders = []
    for key in required_refs:
        value = gate_refs.get(key) if isinstance(gate_refs, dict) else None
        if not isinstance(value, dict):
            continue
        if value.get("verified") is not True:
            unverified.append(key)
        if is_placeholder_ref(value.get("ref")) or is_placeholder_ref(value.get("packet_hash")):
            placeholders.append(key)
    return {
        "missing_release_refs": missing,
        "unverified_release_refs": unverified,
        "placeholder_release_refs": placeholders,
    }


def connector_ref_readiness(refs: dict, required_connector_refs: list[str]) -> dict:
    connector_refs = refs.get("connector_refs") if isinstance(refs.get("connector_refs"), dict) else {}
    missing = [key for key in required_connector_refs if not connector_refs.get(key)]
    placeholders = [key for key in required_connector_refs if is_placeholder_ref(connector_refs.get(key))]
    return {
        "connector_refs": connector_refs,
        "missing_connector_refs": missing,
        "placeholder_connector_refs": placeholders,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline LINE WORKS release readiness check")
    parser.add_argument("--refs", default=str(DEFAULT_REFS), help="Path to lineworks release refs JSON")
    parser.add_argument("--message", default="LINE WORKS 候選通知 readiness 檢查", help="Candidate message preview")
    parser.add_argument("--target-ref", default="TARGET_REF_READINESS_CHECK", help="Target ref or masked/hash ref for readiness")
    parser.add_argument("--actor-ref", default="ACTOR_REF_READINESS_CHECK", help="Actor ref or masked/hash ref for readiness")
    parser.add_argument("--channel", default="member_service", help="Notification channel")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    refs_path = Path(args.refs).expanduser()
    if not refs_path.is_absolute():
        refs_path = ROOT / refs_path
    refs = read_json(refs_path)
    engine = load_module("p1_intent_engine_lineworks_readiness", ENGINE)
    connector = load_module("lineworks_connector_readiness", CONNECTOR)

    required_release_refs = list(engine.FORMAL_RELEASE_GATES["lineworks_send"]["required_refs"])
    release_readiness = release_ref_readiness(refs, required_release_refs)
    connector_readiness = connector_ref_readiness(refs, connector.REQUIRED_CONNECTOR_REFS)

    candidate = engine.lineworks_notify_payload(args.message, args.target_ref, args.channel, args.actor_ref)
    release_status = engine.formal_release_status_payload({"lineworks_send": refs.get("lineworks_send", {})})
    preflight = connector.build_lineworks_send_preflight(
        candidate,
        release_status,
        connector_readiness["connector_refs"],
    )

    blockers = []
    for key in ["missing_release_refs", "unverified_release_refs", "placeholder_release_refs"]:
        if release_readiness[key]:
            blockers.append(key)
    for key in ["missing_connector_refs", "placeholder_connector_refs"]:
        if connector_readiness[key]:
            blockers.append(key)
    if preflight.get("unsafe_connector_ref_keys"):
        blockers.append("unsafe_connector_ref_keys")
    if preflight.get("unsafe_connector_ref_shape_keys"):
        blockers.append("unsafe_connector_ref_shape_keys")
    if preflight.get("send_allowed") is not True:
        blockers.append("lineworks_preflight_not_ready")

    state = "PASS_LINEWORKS_RELEASE_READINESS" if not blockers else "HOLD_LINEWORKS_RELEASE_READINESS"
    report = {
        "schema": "W7TP_XIAOJ_LINEWORKS_RELEASE_READINESS_REPORT_V1",
        "state": state,
        "refs_path": str(refs_path),
        "release_gate_decision": release_status.get("formal_release_gates", {}).get("lineworks_send", {}).get("decision"),
        "release_ready": release_status.get("formal_release_gates", {}).get("lineworks_send", {}).get("release_ready") is True,
        "preflight_state": preflight.get("state"),
        "preflight_send_allowed": preflight.get("send_allowed") is True,
        "blockers": blockers,
        **release_readiness,
        "missing_connector_refs": connector_readiness["missing_connector_refs"],
        "placeholder_connector_refs": connector_readiness["placeholder_connector_refs"],
        "unsafe_connector_ref_keys": preflight.get("unsafe_connector_ref_keys", []),
        "unsafe_connector_ref_shape_keys": preflight.get("unsafe_connector_ref_shape_keys", []),
        "side_effects": {
            "external_api_call": False,
            "formal_lineworks_send": False,
            "secret_read": False,
            "member_plaintext_read": False,
            "db_write": False,
            "deploy": False,
            "service_restart": False,
        },
        "preflight_envelope_hash": preflight.get("request_envelope_hash", ""),
        "candidate_packet_hash": candidate.get("authority_packet", {}).get("packet_hash", ""),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
