#!/usr/bin/env python3
"""Aggregate router thermal risk level from local reports."""

from __future__ import annotations

import argparse

from w7tp_router_thermal_common import (
    base_result,
    collect_temperature_readings_from_text,
    detect_throttle,
    load_report_temperatures,
    load_text_inputs,
    print_json,
    risk_score,
    state_from_temperature,
    summarize_temperatures,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP router thermal risk level analyzer.")
    parser.add_argument("--thermal-json", action="append")
    parser.add_argument("--probe-output", action="append")
    args = parser.parse_args()

    readings, sources = load_report_temperatures(args.thermal_json)
    probe_text, probe_sources = load_text_inputs(args.probe_output)
    readings.extend(collect_temperature_readings_from_text(probe_text, "router_readonly_probe"))
    throttle = detect_throttle(probe_text)
    if not readings and not probe_text.strip():
        result = base_result("w7tp_router_thermal_risk_level_analyzer", "HOLD_ROUTER_THERMAL_RISK_INPUT_REQUIRED")
        result.update({"reason": "Provide --thermal-json or --probe-output.", "thermal_json_sources": sources, "probe_sources": probe_sources})
        return print_json(result)

    summary = summarize_temperatures(readings)
    risk = risk_score(summary, throttle_detected=throttle["throttle_detected"])
    state = state_from_temperature("PASS_ROUTER_THERMAL_RISK_LEVEL_ANALYSIS", summary["max_temperature_c"])
    if risk["risk_level"] in {"critical", "high"} and state.startswith("PASS_"):
        state = "HOLD_ROUTER_THERMAL_RISK_HIGH"
    result = base_result("w7tp_router_thermal_risk_level_analyzer", state)
    result.update(
        {
            "thermal_json_sources": sources,
            "probe_sources": probe_sources,
            "summary": summary,
            "throttle": throttle,
            "risk": risk,
            "thermal_control_action_executed": False,
        }
    )
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
