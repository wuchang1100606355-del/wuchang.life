#!/usr/bin/env python3
"""Bind exact router intents to the existing Total Field Merlin plan chain.

This adapter is deliberately plan-only. It never contacts the router, reads
credentials, changes routes/NVRAM/firewall, restarts a service, or disables a
fallback VPN. A router effect needs a separately registered and verified D8
scope.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.router.merlin_intent_driver import CATALOG, build_merlin_plan


CONTRACT_PATH = (
    ROOT
    / ".skill-build"
    / "w7tp-router-wireguard-control"
    / "references"
    / "total-field-capability-contract.json"
)
AUTHORITY_RUNTIME_PATH = ROOT / "configs/total_field/active_total_field_authority_runtime_v1.json"
SUPPORTED_INTENTS = (
    "observe_status",
    "lan_dns_direct_plan",
    "wireguard_dual_stack_plan",
    "wireguard_peer_plan",
    "wireguard_cutover_plan",
    "wireguard_disable_plan",
)
SENSITIVE = re.compile(
    r"(password|passwd|private[ _-]?key|preshared[ _-]?key|\bpsk\b|token|credential|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|Bearer\s+\S+)",
    re.IGNORECASE,
)


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"TOP_LEVEL_NOT_OBJECT:{path.relative_to(ROOT)}")
    return value


def build_router_packet(intent: str, note: str = "") -> dict[str, Any]:
    if intent not in SUPPORTED_INTENTS or intent not in CATALOG:
        raise ValueError("UNREGISTERED_ROUTER_INTENT")
    if SENSITIVE.search(note):
        raise ValueError("SENSITIVE_NOTE_REJECTED")

    contract = load_object(CONTRACT_PATH)
    authority_runtime = load_object(AUTHORITY_RUNTIME_PATH)
    plan = build_merlin_plan(intent=intent, note=note.strip()[:500])
    observation_only = intent == "observe_status"
    state = (
        "OBSERVE_PLAN_READY"
        if observation_only
        else "HOLD_D8_ROUTER_NETWORK_EFFECT_NOT_REGISTERED"
    )

    packet: dict[str, Any] = {
        "schema_id": "W7TP_TOTAL_FIELD_ROUTER_ADJUSTMENT_PACKET_V1",
        "skill_id": "w7tp-router-wireguard-control",
        "state": state,
        "D1_INTENT": {
            "intent": intent,
            "founder_intent": contract["intent"],
        },
        "D2_STATE": {
            "plan_decision": plan["decision"],
            "plan_risk": plan["risk"],
            "router_effect_performed": False,
            "runtime_authority_active": authority_runtime.get("active") is True,
            "runtime_authority_state": authority_runtime.get("state", "UNKNOWN"),
        },
        "D3_COORDINATE": {
            "repository": "/home/taiji_admin/Taiji_Hub",
            "router_model": contract["target"]["router_model"],
            "wireguard_udp_port": contract["target"]["wireguard_udp_port"],
            "existing_total_field_chain": contract["existing_total_field_chain"],
        },
        "D4_EVIDENCE": {
            "contract_ref": CONTRACT_PATH.relative_to(ROOT).as_posix(),
            "contract_sha256": sha256_file(CONTRACT_PATH),
            "authority_runtime_ref": AUTHORITY_RUNTIME_PATH.relative_to(ROOT).as_posix(),
            "authority_runtime_sha256": sha256_file(AUTHORITY_RUNTIME_PATH),
            "merlin_plan_hash": plan["plan_hash"],
        },
        "D5_EXECUTION_POLICY": {
            "maximum_effect": "READ_ONLY_PLAN" if observation_only else "HOLD_NO_NETWORK_EFFECT",
            "tool_route": [
                "runtime.router.merlin_intent_driver.build_merlin_plan",
                "runtime.router.merlin_apply_queue.make_ticket",
                "runtime.router.merlin_approval_gate.decide",
                "runtime.router.merlin_human_execution_checklist.build_checklist",
                "runtime.router.merlin_execution_result_recorder.build_record",
            ],
            "required_effect_scope": contract["execution"]["required_effect_scope"],
            "required_scope_state": contract["execution"]["required_scope_state"],
            "single_mutation_only": True,
            "rollback_required": True,
            "reobservation_required": True,
        },
        "D6_MAPPING": contract["d6_mapping"],
        "D7_RISK": {
            "forbidden_effects": contract["forbidden_effects"],
            "secret_material_loaded": False,
            "tailscale_disabled": False,
        },
        "D8_ENVELOPE": {
            "authority": contract["authority"],
            "effect_authorized": False,
            "model_is_authority": False,
        },
        "candidate_plan": plan,
    }
    packet["packet_sha256"] = canonical_sha256(packet)
    return packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--intent", choices=SUPPORTED_INTENTS)
    parser.add_argument("--note", default="")
    parser.add_argument("--list-intents", action="store_true")
    args = parser.parse_args()

    if args.list_intents:
        print(
            json.dumps(
                {
                    "skill_id": "w7tp-router-wireguard-control",
                    "intents": list(SUPPORTED_INTENTS),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if not args.intent:
        parser.error("--intent is required unless --list-intents is used")
    try:
        packet = build_router_packet(args.intent, args.note)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {
                    "state": "HOLD_ROUTER_SKILL_INPUT_OR_EVIDENCE_INVALID",
                    "reason": str(exc),
                    "router_effect_performed": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    print(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
