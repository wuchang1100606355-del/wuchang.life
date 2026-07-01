#!/usr/bin/env python3
"""Analyze JFFS kernel log lines from local probe output. No router access."""

from __future__ import annotations

import argparse

from w7tp_jffs_repair_common import analyze_jffs_log, base_result, load_text_inputs, print_json


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP local JFFS kernel log analyzer.")
    parser.add_argument("--probe-output", action="append", help="Router read-only probe output or exported kernel log.")
    args = parser.parse_args()

    text, sources = load_text_inputs(args.probe_output)
    if not text.strip():
        result = base_result("w7tp_jffs_kernel_log_analyzer", "HOLD_JFFS_KERNEL_LOG_PROBE_REQUIRED")
        result.update({"reason": "Provide --probe-output from a read-only router probe.", "probe_sources": sources})
        return print_json(result)

    analysis = analyze_jffs_log(text)
    state = "HOLD_JFFS_KERNEL_ERRORS_DETECTED" if analysis["jffs_errors_detected"] else "PASS_LOCAL_JFFS_KERNEL_LOG_ANALYSIS"
    result = base_result("w7tp_jffs_kernel_log_analyzer", state)
    result.update(
        {
            "probe_sources": sources,
            "analysis": analysis,
            "jffs_kernel_errors": [sample["text"] for sample in analysis["sample_lines"]],
            "error_count": analysis["total_hits"],
            "device_action_executed": False,
        }
    )
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
