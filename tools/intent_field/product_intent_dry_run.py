#!/usr/bin/env python3
"""Product intent field P0 dry-run CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


TOOL_DIR = Path(__file__).resolve().parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

from product_intent_packet_builder import build_result  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build product intent field dry-run packets.")
    parser.add_argument("--intent", required=True, help="Non-sensitive intent text for dry-run only.")
    parser.add_argument("--dry-run", action="store_true", required=True, help="Required dry-run switch.")
    parser.add_argument("--show-packet", action="store_true", help="Print state packet focused output.")
    parser.add_argument("--show-redteam", action="store_true", help="Print red-team HOLD reasons.")
    parser.add_argument("--show-accountability", action="store_true", help="Print accountability record summary.")
    parser.add_argument("--force-hold", action="store_true", help="Force a HOLD result for red-team demonstration.")
    parser.add_argument("--out", help="Optional JSON output path.")
    return parser.parse_args()


def select_view(result: dict, args: argparse.Namespace) -> dict:
    if args.show_packet:
        return {
            "run_id": result["run_id"],
            "view": "show-packet",
            "state_packet": result["state_packet"],
            "db_write": False,
            "deploy": False,
            "restart": False,
        }
    if args.show_redteam:
        return {
            "run_id": result["run_id"],
            "view": "show-redteam",
            "verifier_result": result["verifier_result"],
            "redteam_reasons": result["verifier_result"]["hold_reason_code"],
            "db_write": False,
            "deploy": False,
            "restart": False,
        }
    if args.show_accountability:
        return {
            "run_id": result["run_id"],
            "view": "show-accountability",
            "accountability_record": result["accountability_record"],
            "db_write": False,
            "deploy": False,
            "restart": False,
        }
    return result


def main() -> int:
    args = parse_args()
    result = build_result(args.intent, force_hold=args.force_hold)
    view = select_view(result, args)
    text = json.dumps(view, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
