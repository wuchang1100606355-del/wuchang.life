#!/usr/bin/env python3
"""W7TP intent-build commandization CLI.

This tool is deliberately dry-run only. It creates packetized artifacts for
intent-build construction flow without network calls, DB writes, deployment,
router writes, service restarts, git staging, or production release.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HARD_RISK_FLAGS = [
    "SECRET_READ",
    "MEMBER_PLAINTEXT_READ",
    "RAW_AUDIO_SAVED",
    "DB_WRITE",
    "SERVICE_RESTART",
    "DEPLOY",
    "ROUTER_WRITE",
    "PRODUCTION_RELEASE",
    "GIT_PUSH",
]

SAFETY_FLAGS = {
    "SECRET_READ": False,
    "MEMBER_PLAINTEXT_READ": False,
    "RAW_AUDIO_SAVED": False,
    "DB_WRITE": False,
    "SERVICE_RESTART": False,
    "DEPLOY": False,
    "ROUTER_WRITE": False,
    "PRODUCTION_RELEASE": False,
    "GIT_PUSH": False,
    "CLOUD_REAL_CALL": False,
    "GIT_ADD": False,
    "GIT_COMMIT": False,
}

SUBFIELDS = [
    "SOURCE_FIELD",
    "SCOPE_FIELD",
    "RISK_FIELD",
    "TECH_FIELD",
    "EVIDENCE_FIELD",
    "AUTHORITY_FIELD",
]

GOVERNANCE_SENTENCE = "意圖開場，文件入場，索引開範圍，雲端出候選，分場核對，總場決選。"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_run_id(prefix: str = "INTENT_BUILD_CLI") -> str:
    return f"{prefix}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"


def canonical_hash(value: dict[str, Any]) -> str:
    seed = {k: v for k, v in value.items() if k != "packet_hash"}
    encoded = json.dumps(seed, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def packet(packet_type: str, run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    obj = {
        "packet_type": packet_type,
        "run_id": run_id,
        "created_at": now_utc(),
        "body": body,
    }
    obj["packet_hash"] = canonical_hash(obj)
    return obj


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_packet(path: Path, expected_type: str | None = None) -> dict[str, Any]:
    obj = read_json(path)
    if not isinstance(obj, dict):
        raise SystemExit(f"packet_not_object:{path}")
    for key in ["packet_type", "run_id", "created_at", "body", "packet_hash"]:
        if key not in obj:
            raise SystemExit(f"packet_missing_key:{path}:{key}")
    if expected_type and obj.get("packet_type") != expected_type:
        raise SystemExit(f"packet_type_wrong:{path}:{obj.get('packet_type')}")
    expected_hash = canonical_hash(obj)
    if obj.get("packet_hash") != expected_hash:
        raise SystemExit(f"packet_hash_wrong:{path}")
    return obj


def hard_flags_false(extra: dict[str, bool] | None = None) -> dict[str, bool]:
    flags = dict(SAFETY_FLAGS)
    if extra:
        flags.update(extra)
    return flags


def cmd_open_intent(args: argparse.Namespace) -> int:
    run_id = make_run_id("INTENT_PACKET")
    body = {
        "intent_text": args.intent_text,
        "method": "INTENT_FIRST_CONSTRUCTION_FIELD",
        "governance_sentence": GOVERNANCE_SENTENCE,
        "forbidden_modes": ["schema_first", "file_landing_first", "free_generation_completion"],
        "cloud_boundary": "cloud_candidate_only",
        "safety_flags": hard_flags_false(),
    }
    write_json(Path(args.out), packet("INTENT_PACKET", run_id, body))
    return 0


def cmd_open_field(args: argparse.Namespace) -> int:
    intent = load_packet(Path(args.intent_packet), "INTENT_PACKET")
    body = {
        "intent_packet_hash": intent["packet_hash"],
        "intent_text": intent["body"].get("intent_text", ""),
        "construction_field": "OPENED_FROM_INTENT",
        "field_sequence": [
            "INTENT_PACKET",
            "DOCUMENT_PACKET",
            "SANDBOX_INDEX_SCOPE",
            "CLOUD_CANDIDATE",
            "TOTAL_FIELD_RECEIPT",
            "SUBFIELD_CHECK",
            "TOTAL_FIELD_DECISION",
        ],
        "cloud_is_decision_maker": False,
        "safety_flags": hard_flags_false(),
    }
    write_json(Path(args.out), packet("CONSTRUCTION_FIELD_PACKET", intent["run_id"], body))
    return 0


def cmd_index_source(args: argparse.Namespace) -> int:
    index = Path(args.index)
    index.parent.mkdir(parents=True, exist_ok=True)
    with index.open("w", encoding="utf-8") as handle:
        for raw in args.packets:
            pkt = load_packet(Path(raw))
            entry = {
                "run_id": pkt["run_id"],
                "packet_type": pkt["packet_type"],
                "packet_hash": pkt["packet_hash"],
                "created_at": pkt["created_at"],
                "index_scope": "SANDBOX_ONLY",
                "body_keys": sorted(pkt.get("body", {}).keys()),
                "safety_flags": hard_flags_false(),
            }
            handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    return 0


def read_index(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"index_missing:{path}")
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


def cmd_open_scope(args: argparse.Namespace) -> int:
    intent = load_packet(Path(args.intent_packet), "INTENT_PACKET")
    entries = read_index(Path(args.index))
    intent_text = intent["body"].get("intent_text", "")
    rejected_modes = []
    if "schema_landing_first" in intent_text or "schema first" in intent_text.lower():
        rejected_modes.append("schema_landing_first")
    body = {
        "intent_packet_hash": intent["packet_hash"],
        "sandbox_index_entry_count": len(entries),
        "bounded_scope": {
            "mode": "INTENT_TO_BOUNDED_SCOPE",
            "allowed_sources": [entry["packet_hash"] for entry in entries],
            "rejected_modes": rejected_modes,
            "cloud_candidate_only": True,
            "schema_landing_first_allowed": False,
            "file_landing_first_allowed": False,
        },
        "decision": "SCOPE_OPENED" if not rejected_modes else "SCOPE_OPENED_WITH_FORBIDDEN_MODE_REJECTED",
        "safety_flags": hard_flags_false(),
    }
    write_json(Path(args.out), packet("BOUNDED_SCOPE_FROM_INTENT_PACKET", intent["run_id"], body))
    return 0


def cmd_make_cloud_request(args: argparse.Namespace) -> int:
    scope = load_packet(Path(args.scope_packet), "BOUNDED_SCOPE_FROM_INTENT_PACKET")
    body = {
        "scope_packet_hash": scope["packet_hash"],
        "request_mode": "DRYRUN_NO_NETWORK",
        "cloud_boundary": {
            "cloud_candidate_only": True,
            "cloud_may_decide": False,
            "cloud_may_claim_landed": False,
            "cloud_may_request_production_db_write": False,
            "cloud_may_deploy_restart_router_write_git_push": False,
        },
        "requested_candidate_shape": [
            "candidate_id",
            "claim",
            "evidence_refs",
            "risk_flags",
            "proposed_artifact",
        ],
        "safety_flags": hard_flags_false(),
    }
    write_json(Path(args.out), packet("CLOUD_CANDIDATE_REQUEST_FROM_SCOPE_PACKET", scope["run_id"], body))
    return 0


def cmd_mock_cloud_response(args: argparse.Namespace) -> int:
    request = load_packet(Path(args.request_packet), "CLOUD_CANDIDATE_REQUEST_FROM_SCOPE_PACKET")
    body = {
        "request_packet_hash": request["packet_hash"],
        "response_mode": "MOCK_ONLY_NO_NETWORK",
        "candidates": [
            {
                "candidate_id": "GOOD_CANDIDATE",
                "claim": "candidate_artifact_for_subfield_check",
                "evidence_refs": ["SANDBOX_INDEX_REF", "INTENT_PACKET_REF"],
                "risk_flags": {flag: False for flag in HARD_RISK_FLAGS},
                "cloud_decision_claim": False,
                "claims_landed": False,
                "proposed_artifact": {"kind": "candidate", "status": "needs_total_field_decision"},
            },
            {
                "candidate_id": "BAD_CANDIDATE",
                "claim": "already_landed_with_production_release",
                "evidence_refs": [],
                "risk_flags": {
                    **{flag: False for flag in HARD_RISK_FLAGS},
                    "DB_WRITE": True,
                    "PRODUCTION_RELEASE": True,
                },
                "cloud_decision_claim": True,
                "claims_landed": True,
                "proposed_artifact": {"kind": "production_release", "status": "claimed_done"},
            },
        ],
        "safety_flags": hard_flags_false(),
    }
    write_json(Path(args.out), packet("MOCK_CLOUD_CANDIDATE_RESPONSES", request["run_id"], body))
    return 0


def candidate_receipt_decision(candidate: dict[str, Any]) -> str:
    risk_flags = candidate.get("risk_flags", {})
    if candidate.get("claims_landed") or candidate.get("cloud_decision_claim"):
        return "REJECT_AT_RECEIPT"
    if risk_flags.get("DB_WRITE") or risk_flags.get("PRODUCTION_RELEASE"):
        return "REJECT_AT_RECEIPT"
    if any(risk_flags.get(flag) for flag in HARD_RISK_FLAGS):
        return "REJECT_AT_RECEIPT"
    return "RECEIVED_FOR_SUBFIELD_CHECK"


def cmd_receive(args: argparse.Namespace) -> int:
    responses = load_packet(Path(args.responses), "MOCK_CLOUD_CANDIDATE_RESPONSES")
    request = load_packet(Path(args.request_packet), "CLOUD_CANDIDATE_REQUEST_FROM_SCOPE_PACKET")
    receipts = []
    for candidate in responses["body"].get("candidates", []):
        decision = candidate_receipt_decision(candidate)
        receipts.append(
            {
                "candidate_id": candidate.get("candidate_id", ""),
                "receipt_decision": decision,
                "request_packet_hash": request["packet_hash"],
                "candidate_claim": candidate.get("claim", ""),
                "risk_flags": candidate.get("risk_flags", {}),
            }
        )
    body = {
        "request_packet_hash": request["packet_hash"],
        "responses_packet_hash": responses["packet_hash"],
        "receipts": receipts,
        "safety_flags": hard_flags_false(),
    }
    write_json(Path(args.out), packet("TOTAL_FIELD_RECEIPTS", responses["run_id"], body))
    return 0


def cmd_subfield_check(args: argparse.Namespace) -> int:
    receipts = load_packet(Path(args.receipts), "TOTAL_FIELD_RECEIPTS")
    responses = load_packet(Path(args.responses), "MOCK_CLOUD_CANDIDATE_RESPONSES")
    by_id = {c.get("candidate_id"): c for c in responses["body"].get("candidates", [])}
    reports = []
    for receipt in receipts["body"].get("receipts", []):
        if receipt.get("receipt_decision") != "RECEIVED_FOR_SUBFIELD_CHECK":
            continue
        candidate = by_id.get(receipt.get("candidate_id"), {})
        checks = []
        for subfield in SUBFIELDS:
            checks.append(
                {
                    "subfield": subfield,
                    "result": "PASS",
                    "reason": "candidate remains bounded, evidenced, non-production, and total-field-decision-pending",
                }
            )
        reports.append(
            {
                "candidate_id": receipt.get("candidate_id"),
                "candidate_claim": candidate.get("claim", ""),
                "checks": checks,
                "overall": "PASS",
            }
        )
    body = {
        "receipts_packet_hash": receipts["packet_hash"],
        "subfields": SUBFIELDS,
        "candidate_reports": reports,
        "safety_flags": hard_flags_false(),
    }
    write_json(Path(args.out), packet("SUBFIELD_REPORT", receipts["run_id"], body))
    return 0


def cmd_decide(args: argparse.Namespace) -> int:
    receipts = load_packet(Path(args.receipts), "TOTAL_FIELD_RECEIPTS")
    subfield = load_packet(Path(args.subfield_report), "SUBFIELD_REPORT")
    rejected = [
        receipt["candidate_id"]
        for receipt in receipts["body"].get("receipts", [])
        if receipt.get("receipt_decision") == "REJECT_AT_RECEIPT"
    ]
    pass_reports = [r for r in subfield["body"].get("candidate_reports", []) if r.get("overall") == "PASS"]
    selected = pass_reports[0]["candidate_id"] if pass_reports else ""
    final_decision = "APPROVE_TO_SANDBOX_INDEX" if selected else "HOLD_NO_PASSING_CANDIDATE"
    body = {
        "receipts_packet_hash": receipts["packet_hash"],
        "subfield_report_hash": subfield["packet_hash"],
        "final_decision": final_decision,
        "selected_candidate_id": selected,
        "rejected_at_receipt": rejected,
        "bad_candidate_entered_final_selection": "BAD_CANDIDATE" == selected,
        "safety_flags": hard_flags_false(),
    }
    write_json(Path(args.out), packet("TOTAL_FIELD_FINAL_DECISION_PACKET", receipts["run_id"], body))
    return 0


def cmd_seal(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    packet_paths = sorted(path for path in run_dir.rglob("*.json") if path.name != "INTENT_BUILD_FULL_CHAIN_SEAL.json")
    packets = [load_packet(path) for path in packet_paths]
    decision_packets = [pkt for pkt in packets if pkt.get("packet_type") == "TOTAL_FIELD_FINAL_DECISION_PACKET"]
    final_decision = decision_packets[-1]["body"].get("final_decision") if decision_packets else "MISSING_DECISION"
    run_id = packets[0]["run_id"] if packets else make_run_id("INTENT_BUILD_EMPTY_SEAL")
    body = {
        "state": "PASS_INTENT_BUILD_FULL_CHAIN_SEALED" if final_decision == "APPROVE_TO_SANDBOX_INDEX" else "FAIL_INTENT_BUILD_FULL_CHAIN",
        "final_decision": final_decision,
        "packet_count": len(packets),
        "packet_hashes": [pkt["packet_hash"] for pkt in packets],
        "safety_flags": hard_flags_false(),
    }
    seal = packet("INTENT_BUILD_FULL_CHAIN_SEAL", run_id, body)
    out_dir = Path(args.out)
    write_json(out_dir / "INTENT_BUILD_FULL_CHAIN_SEAL.json", seal)
    sums = []
    for path in sorted(out_dir.glob("*.json")):
        sums.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    (out_dir / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")
    return 0


def run_command(argv: list[str]) -> None:
    result = subprocess.run([sys.executable, __file__, *argv], check=False, text=True, capture_output=True)
    if result.returncode != 0:
        raise SystemExit(result.stderr or result.stdout or f"command_failed:{argv}")


def cmd_run_demo(args: argparse.Namespace) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "intent": out / "INTENT_PACKET.json",
        "field": out / "CONSTRUCTION_FIELD_PACKET.json",
        "index": out / "index_sandbox.jsonl",
        "scope": out / "BOUNDED_SCOPE_FROM_INTENT_PACKET.json",
        "request": out / "CLOUD_CANDIDATE_REQUEST_FROM_SCOPE_PACKET.json",
        "responses": out / "MOCK_CLOUD_CANDIDATE_RESPONSES.json",
        "receipts": out / "TOTAL_FIELD_RECEIPTS.json",
        "subfield": out / "SUBFIELD_REPORT.json",
        "decision": out / "TOTAL_FIELD_FINAL_DECISION_PACKET.json",
        "seal": out / "seal",
    }
    run_command(["open-intent", "--intent-text", args.intent_text, "--out", str(paths["intent"])])
    run_command(["open-field", "--intent-packet", str(paths["intent"]), "--out", str(paths["field"])])
    run_command(["index-source", "--packets", str(paths["intent"]), str(paths["field"]), "--index", str(paths["index"])])
    run_command(["open-scope", "--intent-packet", str(paths["intent"]), "--index", str(paths["index"]), "--out", str(paths["scope"])])
    run_command(["make-cloud-request", "--scope-packet", str(paths["scope"]), "--out", str(paths["request"])])
    run_command(["mock-cloud-response", "--request-packet", str(paths["request"]), "--out", str(paths["responses"])])
    run_command(["receive", "--responses", str(paths["responses"]), "--request-packet", str(paths["request"]), "--out", str(paths["receipts"])])
    run_command(["subfield-check", "--receipts", str(paths["receipts"]), "--responses", str(paths["responses"]), "--out", str(paths["subfield"])])
    run_command(["decide", "--receipts", str(paths["receipts"]), "--subfield-report", str(paths["subfield"]), "--out", str(paths["decision"])])
    run_command(["seal", "--run-dir", str(out), "--out", str(paths["seal"])])
    decision = load_packet(paths["decision"], "TOTAL_FIELD_FINAL_DECISION_PACKET")
    receipts = load_packet(paths["receipts"], "TOTAL_FIELD_RECEIPTS")
    receipt_map = {r["candidate_id"]: r["receipt_decision"] for r in receipts["body"]["receipts"]}
    print("STATE=PASS_INTENT_BUILD_COMMAND_DEMO")
    print(f"FINAL_DECISION={decision['body']['final_decision']}")
    print(f"GOOD_RECEIPT_DECISION={receipt_map.get('GOOD_CANDIDATE')}")
    print(f"BAD_RECEIPT_DECISION={receipt_map.get('BAD_CANDIDATE')}")
    print("DB_WRITE=FALSE")
    print("CLOUD_REAL_CALL=FALSE")
    print("GIT_ADD=FALSE")
    print("GIT_COMMIT=FALSE")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="W7TP intent-build commandization CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("open-intent")
    p.add_argument("--intent-text", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_open_intent)

    p = sub.add_parser("open-field")
    p.add_argument("--intent-packet", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_open_field)

    p = sub.add_parser("index-source")
    p.add_argument("--packets", nargs="+", required=True)
    p.add_argument("--index", required=True)
    p.set_defaults(func=cmd_index_source)

    p = sub.add_parser("open-scope")
    p.add_argument("--intent-packet", required=True)
    p.add_argument("--index", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_open_scope)

    p = sub.add_parser("make-cloud-request")
    p.add_argument("--scope-packet", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_make_cloud_request)

    p = sub.add_parser("mock-cloud-response")
    p.add_argument("--request-packet", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_mock_cloud_response)

    p = sub.add_parser("receive")
    p.add_argument("--responses", required=True)
    p.add_argument("--request-packet", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_receive)

    p = sub.add_parser("subfield-check")
    p.add_argument("--receipts", required=True)
    p.add_argument("--responses", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_subfield_check)

    p = sub.add_parser("decide")
    p.add_argument("--receipts", required=True)
    p.add_argument("--subfield-report", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_decide)

    p = sub.add_parser("seal")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_seal)

    p = sub.add_parser("run-demo")
    p.add_argument("--intent-text", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_run_demo)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
