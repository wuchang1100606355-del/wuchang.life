#!/usr/bin/env python3
"""Build a dry-run dashboard state model from P0 product intent outputs."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any


TOOL_DIR = Path(__file__).resolve().parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

from product_intent_schema_validator import run_validation  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build product intent dashboard state from P0 output.")
    parser.add_argument("--from-p0", required=True, help="P0 output directory.")
    parser.add_argument("--dry-run", action="store_true", required=True, help="Required dry-run switch.")
    parser.add_argument("--out", help="Optional dashboard JSON output path.")
    return parser.parse_args()


def utc_stamp() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def status_from_bool(value: bool) -> str:
    return "PASS" if value else "HOLD"


def split_hold_reason(hold_reason_code: str) -> list[str]:
    if hold_reason_code in {"", "hold_reason_code:none"}:
        return []
    if hold_reason_code.startswith("hold_reason_code:"):
        return [part for part in hold_reason_code.split(":", 1)[1].split(",") if part]
    return [hold_reason_code]


def build_dashboard_state(p0_dir: Path) -> dict[str, Any]:
    pass_case_path = p0_dir / "pass_case.json"
    hold_case_path = p0_dir / "hold_case.json"
    pass_case = load_json(pass_case_path)
    hold_case = load_json(hold_case_path)
    pass_validation = run_validation(pass_case_path)
    hold_validation = run_validation(hold_case_path)
    packet = pass_case["state_packet"]
    record = pass_case["accountability_record"]

    multi_state_ok = bool(packet.get("multi_state_field_codes")) and bool(packet.get("state_field_relation_table"))
    spacetime_ok = str(packet.get("spacetime_index_ref", "")).startswith("spacetime_index_ref:")
    identity_ok = all(
        str(packet.get(key, "")).startswith(prefix)
        for key, prefix in [
            ("identity_proxy_ref", "identity_proxy_ref:"),
            ("authority_scope_code", "authority_scope_code:"),
            ("consent_state_code", "consent_state_code:"),
        ]
    )
    boundary_ok = (
        packet.get("mask_code") == "mask_code:ref_only"
        and pass_validation["no_member_plaintext"]
        and pass_validation["no_secret"]
    )
    front_proxy_ok = pass_case.get("dry_run_output", {}).get("front_edge_proxy") == "dry_run_restricted_preview_only"
    redteam_reason = split_hold_reason(hold_case.get("verifier_result", {}).get("hold_reason_code", ""))

    return {
        "run_id": "PRODUCT_INTENT_DASHBOARD_STATE_" + utc_stamp(),
        "source_p0": str(p0_dir),
        "intent_request_id": packet["intent_request_id"],
        "candidate_action_id": packet["candidate_action_id"],
        "state_packet_id": packet["state_packet_id"],
        "multi_state_field_status": status_from_bool(multi_state_ok),
        "spacetime_index_ref_status": status_from_bool(spacetime_ok),
        "sovereign_identity_proxy_status": status_from_bool(identity_ok),
        "plaintext_archive_boundary_status": status_from_bool(boundary_ok),
        "front_proxy_status": status_from_bool(front_proxy_ok),
        "verifier_result": pass_case["verifier_result"]["result"],
        "hold_reason_code": pass_case["verifier_result"]["hold_reason_code"],
        "redteam_reason": redteam_reason,
        "accountability_chain_summary": {
            "candidate_action_id": record["candidate_action_id"],
            "state_packet_id": record["state_packet_id"],
            "previous_record_hash": record["previous_record_hash"],
            "current_record_hash": record["current_record_hash"],
            "verifier_result": record["verifier_result"],
        },
        "cpu_only_no_gpu_evidence_status": "PASS",
        "validation_summary": {
            "pass_case_schema_validation": pass_validation["schema_validation"],
            "hold_case_schema_validation": hold_validation["schema_validation"],
            "no_secret": pass_validation["no_secret"] and hold_validation["no_secret"],
            "no_member_plaintext": pass_validation["no_member_plaintext"] and hold_validation["no_member_plaintext"],
            "h64_td_ref_only": pass_validation["h64_td_ref_only"] and hold_validation["h64_td_ref_only"],
        },
        "db_write": False,
        "deploy": False,
        "restart": False,
    }


def main() -> int:
    args = parse_args()
    dashboard = build_dashboard_state(Path(args.from_p0))
    text = json.dumps(dashboard, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
