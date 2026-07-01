#!/usr/bin/env python3
"""JFFS scrub advisor. Advice only; never executes scrub or writes JFFS."""

from __future__ import annotations

import argparse
from typing import Any

from w7tp_jffs_repair_common import base_result, bool_seen, max_numeric_key, print_json, read_json_file


def load_optional(path: str | None) -> Any | None:
    return read_json_file(path) if path else None


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP JFFS scrub advisor. No action execution.")
    parser.add_argument("--free-space-json")
    parser.add_argument("--write-pressure-json")
    parser.add_argument("--kernel-json")
    parser.add_argument("--image-json")
    parser.add_argument("--usb-repair-complete-evidence", help="Optional evidence ref only; does not unlock execution.")
    args = parser.parse_args()

    named_payloads = {
        "free_space": load_optional(args.free_space_json),
        "write_pressure": load_optional(args.write_pressure_json),
        "kernel": load_optional(args.kernel_json),
        "image": load_optional(args.image_json),
    }
    payloads = [payload for payload in named_payloads.values() if payload is not None]
    if not payloads:
        result = base_result("w7tp_jffs_scrub_advisor", "HOLD_JFFS_SCRUB_INPUT_REQUIRED")
        result.update({"reason": "Provide at least one prior JFFS analysis JSON.", "scrub_executed": False})
        return print_json(result)

    free_low = bool_seen(payloads, "free_space_low", True)
    kernel_errors = bool_seen(payloads, "jffs_errors_detected", True)
    image_blank = bool_seen(payloads, "empty_or_erased_like", True)
    pressure_score = max_numeric_key(payloads, "score") or 0.0

    state = "PASS_JFFS_SCRUB_ADVICE_READY"
    if not args.usb_repair_complete_evidence:
        state = "HOLD_JFFS_SCRUB_ADVICE_USB_REPAIR_REQUIRED"
    elif free_low or kernel_errors or image_blank or pressure_score >= 50:
        state = "HOLD_JFFS_SCRUB_HUMAN_MAINTENANCE_REQUIRED"

    result = base_result("w7tp_jffs_scrub_advisor", state)
    result.update(
        {
            "input_reports": {
                "free_space_json": args.free_space_json,
                "write_pressure_json": args.write_pressure_json,
                "kernel_json": args.kernel_json,
                "image_json": args.image_json,
            },
            "usb_repair_complete_evidence": args.usb_repair_complete_evidence,
            "jffs_repair_allowed": False,
            "scrub_executed": False,
            "risk_flags": {
                "free_space_low": free_low,
                "kernel_errors": kernel_errors,
                "image_blank_or_erased_like": image_blank,
                "pressure_score": pressure_score,
            },
            "advice": [
                "Do not run router JFFS scrub from this tool.",
                "Keep JFFS limited to pointer/status metadata.",
                "Complete and evidence USB repair before any JFFS repair planning.",
                "If JFFS is low-space or read-only, plan human maintenance window and offline backup review.",
                "Remove high-churn logs/databases from JFFS design; move durable records to USB after USB health is proven.",
            ],
        }
    )
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
