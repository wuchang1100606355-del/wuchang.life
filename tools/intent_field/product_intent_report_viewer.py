#!/usr/bin/env python3
"""CLI viewer for static product intent dry-run dashboard output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="View product intent dry-run P2 report summary.")
    parser.add_argument("--p2", required=True, help="P2 output directory.")
    parser.add_argument("--out", help="Optional JSON summary path.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_summary(p2_dir: Path) -> dict[str, Any]:
    data = load_json(p2_dir / "dashboard_data.json")
    required_html = [
        "dashboard.html",
        "pass_case_report.html",
        "hold_case_report.html",
        "redteam_summary.html",
        "accountability_summary.html",
    ]
    return {
        "state": "PRODUCT_INTENT_FIELD_DRY_RUN_P2_VIEWER",
        "p2": str(p2_dir),
        "intent_request_id": data["intent_request_id"],
        "candidate_action_id": data["candidate_action_id"],
        "state_packet_id": data["state_packet_id"],
        "verifier_result": data["verifier_result"],
        "redteam_reason": data["redteam_reason"],
        "html_files_present": all((p2_dir / name).exists() for name in required_html),
        "dashboard_data_present": (p2_dir / "dashboard_data.json").exists(),
        "db_write": False,
        "deploy": False,
        "restart": False,
    }


def main() -> int:
    args = parse_args()
    summary = build_summary(Path(args.p2))
    text = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if summary["html_files_present"] and summary["dashboard_data_present"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
