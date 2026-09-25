#!/usr/bin/env python3
"""Analyze thermal impact on JFFS from read-only probe output."""

from __future__ import annotations

import argparse

from w7tp_jffs_repair_common import base_result, collect_temperatures, load_text_inputs, print_json


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP JFFS thermal impact analyzer.")
    parser.add_argument("--probe-output", action="append", help="Router read-only probe output with thermal lines.")
    args = parser.parse_args()

    text, sources = load_text_inputs(args.probe_output)
    if not text.strip():
        result = base_result("w7tp_jffs_thermal_impact_analyzer", "HOLD_JFFS_THERMAL_PROBE_REQUIRED")
        result.update({"reason": "Provide --probe-output from router read-only thermal probe.", "probe_sources": sources})
        return print_json(result)

    values = collect_temperatures(text)
    max_temp = max(values) if values else None
    if max_temp is not None and max_temp >= 75.0:
        state = "HOLD_JFFS_THERMAL_CRITICAL"
    elif max_temp is not None and max_temp >= 65.0:
        state = "HOLD_JFFS_THERMAL_HIGH"
    else:
        state = "PASS_JFFS_THERMAL_IMPACT_ANALYSIS"

    result = base_result("w7tp_jffs_thermal_impact_analyzer", state)
    result.update(
        {
            "probe_sources": sources,
            "temperatures_c": values,
            "max_temperature_c": max_temp,
            "thermal_action_executed": False,
            "advice": [
                "Do not change router clock, config, services, or JFFS from this tool.",
                "Treat high heat as a JFFS write-risk multiplier.",
                "Keep JFFS pointer/status only and reduce write churn.",
                "Complete USB repair evidence before any JFFS maintenance planning.",
            ],
        }
    )
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
