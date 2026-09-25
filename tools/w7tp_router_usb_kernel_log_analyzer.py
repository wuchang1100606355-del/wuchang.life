#!/usr/bin/env python3
"""Local kernel log analyzer for USB/storage fault evidence."""

from __future__ import annotations

import argparse

from w7tp_router_usb_repair_common import analyze_kernel_log, base_result, print_json, read_text_limited, run_cmd


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP local USB kernel log analyzer.")
    parser.add_argument("--input", help="Optional local text log. If omitted, runs dmesg.")
    parser.add_argument("--input-limit", type=int, default=500000)
    args = parser.parse_args()

    if args.input:
        text, truncated = read_text_limited(args.input, args.input_limit)
        source = {"type": "file", "path": args.input, "truncated": truncated}
        dmesg = None
    else:
        dmesg = run_cmd(["dmesg"], stdout_limit=args.input_limit)
        text = dmesg.get("stdout", "")
        source = {"type": "dmesg", "command": dmesg}

    analysis = analyze_kernel_log(text)
    usb_kernel_errors = [
        line
        for line in text.splitlines()
        if "usb" in line.lower() and ("error" in line.lower() or "reset" in line.lower())
    ]
    if dmesg is not None and dmesg["returncode"] != 0:
        state = "HOLD_KERNEL_LOG_UNAVAILABLE"
    elif analysis["usb_errors_detected"]:
        state = "HOLD_USB_STORAGE_ERRORS_DETECTED"
    else:
        state = "PASS_LOCAL_USB_KERNEL_ANALYSIS"

    result = base_result("w7tp_router_usb_kernel_log_analyzer", state)
    result.update(
        {
            "source": source,
            "analysis": analysis,
            "usb_kernel_errors": usb_kernel_errors,
            "error_count": len(usb_kernel_errors),
            "device_action_executed": False,
        }
    )
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
