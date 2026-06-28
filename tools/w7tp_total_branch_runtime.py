#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W7TP Total / Branch runtime solidification CLI.

This tool is local-file only. It writes runtime JSON only under
runtime/total_field/total_branch_runtime/.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = ROOT / "runtime" / "total_field" / "total_branch_runtime"
STATE_PATH = RUNTIME_DIR / "state.json"

BRANCH_TYPES = {"STORE", "PROPERTY", "ASSOCIATION", "BROWSER", "WEBSITE", "VOICE", "CUSTOM"}

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
    "CODEX_AUTHORITY": False,
    "AUTO_STAGE": False,
    "AUTO_COMMIT": False,
}

TOTAL_DECISIONS = [
    "ALLOW",
    "HOLD",
    "BLOCK",
    "VERIFY_READY",
    "STAGE_READY",
    "COMMIT_READY",
    "RELEASE_READY",
    "SEALED",
]

TOTAL_FORBIDDEN = [
    "secret_read",
    "member_plaintext_read",
    "payment_capture",
    "db_write_without_packet",
    "deploy_without_explicit_packet",
    "codex_authority",
]

BRANCH_CANNOT_DO = [
    "grant_total_field_authority",
    "read_member_plaintext",
    "capture_payment_without_human_review",
    "deploy",
    "read_secret",
]


def now_run_id() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def default_state() -> dict[str, Any]:
    return {
        "runtime_id": "w7tp_total_branch_runtime_v01",
        "created_at_unix": int(time.time()),
        "updated_at_unix": int(time.time()),
        "total_field_id": "w7tp_total_field_v01",
        "branches": {},
        "safety_flags": SAFETY_FLAGS,
    }


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return default_state()
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: dict[str, Any]) -> None:
    state["updated_at_unix"] = int(time.time())
    write_json(STATE_PATH, state)


def valid_branch_id(branch_id: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", branch_id or ""))


def total_packet(state: dict[str, Any]) -> dict[str, Any]:
    base = "runtime/total_field/total_branch_runtime"
    return {
        "packet_type": "W7TP_TOTAL_FIELD_PACKET",
        "version": "v0.1",
        "authority": "TOTAL_FIELD",
        "total_field_id": state.get("total_field_id", "w7tp_total_field_v01"),
        "work_queue_ref": f"{base}/work_queue.jsonl",
        "schema_registry_ref": "schemas/field/",
        "verifier_registry_ref": "scripts/verify/",
        "risk_policy_ref": f"{base}/risk_policy.json",
        "evidence_chain_ref": f"{base}/evidence_chain.jsonl",
        "commit_queue_ref": f"{base}/commit_queue.jsonl",
        "release_manifest_ref": f"{base}/release_manifest.json",
        "seal_ref": f"{base}/seal.json",
        "decisions": TOTAL_DECISIONS,
        "forbidden": TOTAL_FORBIDDEN,
    }


def branch_packet(branch: dict[str, Any]) -> dict[str, Any]:
    branch_id = branch["branch_id"]
    branch_type = branch["branch_type"]
    base = f"runtime/total_field/total_branch_runtime/branches/{branch_id}"
    return {
        "packet_type": "W7TP_BRANCH_FIELD_PACKET",
        "version": "v0.1",
        "authority": "BRANCH_FIELD_LIMITED",
        "branch_id": branch_id,
        "branch_type": branch_type,
        "allowed_capabilities": branch.get("allowed_capabilities", default_capabilities(branch_type)),
        "local_route_table_ref": f"{base}/route_table.json",
        "local_verifier_subset_ref": f"{base}/verifier_subset.json",
        "template_set_ref": f"{base}/template_set.json",
        "risk_policy_subset_ref": f"{base}/risk_policy_subset.json",
        "release_manifest_ref": f"{base}/release_manifest.json",
        "cannot_do": BRANCH_CANNOT_DO,
        "total_field_authority": False,
    }


def default_capabilities(branch_type: str) -> list[str]:
    table = {
        "STORE": ["local_lookup", "draft_order_candidate", "store_projection"],
        "PROPERTY": ["local_lookup", "repair_request_candidate", "property_projection"],
        "ASSOCIATION": ["local_lookup", "activity_candidate", "association_projection"],
        "BROWSER": ["local_lookup", "browser_projection"],
        "WEBSITE": ["local_lookup", "website_projection"],
        "VOICE": ["local_lookup", "voice_projection"],
        "CUSTOM": ["local_lookup", "custom_projection"],
    }
    return table.get(branch_type, table["CUSTOM"])


def output(state: dict[str, Any], branch_packets: list[dict[str, Any]] | None = None, next_text: str = "") -> dict[str, Any]:
    packets = branch_packets
    if packets is None:
        packets = [branch_packet(branch) for branch in sorted(state.get("branches", {}).values(), key=lambda row: row["branch_id"])]
    return {
        "STATE": "PASS_W7TP_TOTAL_BRANCH_RUNTIME",
        "SAFETY_FLAGS": SAFETY_FLAGS,
        "TOTAL_FIELD_PACKET": total_packet(state),
        "BRANCH_FIELD_PACKETS": packets,
        "NEXT": next_text or "git diff -- <exact files> then exact stage only",
    }


def init_runtime() -> dict[str, Any]:
    state = load_state()
    save_state(state)
    return output(state, next_text="runtime initialized; register branch or emit packets")


def register_branch(branch_id: str, branch_type: str) -> dict[str, Any]:
    if not valid_branch_id(branch_id):
        raise ValueError("invalid branch id")
    branch_type = branch_type.upper()
    if branch_type not in BRANCH_TYPES:
        raise ValueError("invalid branch type")
    state = load_state()
    state.setdefault("branches", {})[branch_id] = {
        "branch_id": branch_id,
        "branch_type": branch_type,
        "registered_at_unix": int(time.time()),
        "allowed_capabilities": default_capabilities(branch_type),
        "total_field_authority": False,
    }
    save_state(state)
    return output(state, branch_packets=[branch_packet(state["branches"][branch_id])], next_text="branch registered; emit branch packet or run verifier")


def emit_branch(branch_id: str) -> dict[str, Any]:
    state = load_state()
    branch = state.get("branches", {}).get(branch_id)
    if not branch:
        raise ValueError("branch not registered")
    packet = branch_packet(branch)
    if packet.get("authority") != "BRANCH_FIELD_LIMITED" or packet.get("total_field_authority") is not False:
        raise ValueError("branch authority violation")
    return output(state, branch_packets=[packet], next_text="branch packet emitted; verifier must review before any stage plan")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--register-branch", action="store_true")
    parser.add_argument("--branch-id", default="")
    parser.add_argument("--branch-type", default="")
    parser.add_argument("--emit-total-packet", action="store_true")
    parser.add_argument("--emit-branch-packet", action="store_true")
    args = parser.parse_args()

    try:
        if args.init:
            result = init_runtime()
        elif args.status:
            result = output(load_state(), next_text="status emitted")
        elif args.register_branch:
            result = register_branch(args.branch_id, args.branch_type)
        elif args.emit_total_packet:
            result = output(load_state(), branch_packets=[], next_text="total packet emitted")
        elif args.emit_branch_packet:
            result = emit_branch(args.branch_id)
        else:
            result = output(load_state(), next_text="choose --init, --status, --register-branch, --emit-total-packet, or --emit-branch-packet")
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except ValueError as exc:
        print(json.dumps({"STATE": "HOLD_W7TP_TOTAL_BRANCH_RUNTIME", "ERROR": str(exc), "SAFETY_FLAGS": SAFETY_FLAGS}, ensure_ascii=False, indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
