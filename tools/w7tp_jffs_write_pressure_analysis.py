#!/usr/bin/env python3
"""Analyze JFFS write pressure from router read-only probe output."""

from __future__ import annotations

import argparse

from w7tp_jffs_repair_common import analyze_write_pressure, base_result, load_text_inputs, print_json


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP local JFFS write-pressure analysis.")
    parser.add_argument("--probe-output", action="append", help="Router read-only probe output.")
    args = parser.parse_args()

    text, sources = load_text_inputs(args.probe_output)
    if not text.strip():
        result = base_result("w7tp_jffs_write_pressure_analysis", "HOLD_JFFS_WRITE_PRESSURE_PROBE_REQUIRED")
        result.update({"reason": "Provide --probe-output from a router read-only probe.", "probe_sources": sources})
        return print_json(result)

    analysis = analyze_write_pressure(text)
    state = "PASS_LOCAL_JFFS_WRITE_PRESSURE_ANALYSIS"
    if analysis["pressure"] == "medium":
        state = "HOLD_JFFS_WRITE_PRESSURE_REVIEW"
    if analysis["pressure"] == "high":
        state = "HOLD_JFFS_WRITE_PRESSURE_HIGH"

    result = base_result("w7tp_jffs_write_pressure_analysis", state)
    result.update({"probe_sources": sources, "analysis": analysis, "write_action_executed": False})
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
