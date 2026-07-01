#!/usr/bin/env python3
"""Analyze router/local kernel USB errors. Local-only; no router access."""

from __future__ import annotations

import argparse

from w7tp_router_kernel_error_common import USB_PATTERN, analyze_lines, base_result, load_text_inputs, local_kernel_text, print_json, source_unavailable


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP router kernel USB error analyzer.")
    parser.add_argument("--probe-output", action="append", help="Router read-only probe kernel log/capacity output.")
    parser.add_argument("--input", action="append", help="Local exported kernel log text.")
    parser.add_argument("--skip-local-dmesg", action="store_true")
    parser.add_argument("--include-local-journal", action="store_true")
    parser.add_argument("--journal-lines", type=int, default=400)
    args = parser.parse_args()

    file_text, file_sources = load_text_inputs((args.probe_output or []) + (args.input or []))
    local_text, local_sources = local_kernel_text(not args.skip_local_dmesg, args.include_local_journal, args.journal_lines)
    text = "\n".join([file_text, local_text])
    sources = file_sources + local_sources
    if source_unavailable(sources):
        result = base_result("w7tp_router_kernel_usb_error_analyzer", "HOLD_ROUTER_KERNEL_USB_LOG_UNAVAILABLE")
        result.update({"reason": "No readable probe/input/dmesg/journal kernel log available.", "sources": sources})
        return print_json(result)

    analysis = analyze_lines(text, USB_PATTERN, "usb")
    usb_errors = [item["text"] for item in analysis["sample_lines"]]
    state = "HOLD_ROUTER_KERNEL_USB_ERRORS_DETECTED" if analysis["errors_detected"] else "PASS_LOCAL_ROUTER_KERNEL_USB_ERROR_ANALYSIS"
    result = base_result("w7tp_router_kernel_usb_error_analyzer", state)
    result.update(
        {
            "sources": sources,
            "analysis": analysis,
            "usb_kernel_errors": usb_errors,
            "usb_error_count": analysis["error_count"],
            "repair_executed": False,
        }
    )
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
