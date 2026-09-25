#!/usr/bin/env python3
"""Analyze router thermal hotspots from local sensors and read-only probe output."""

from __future__ import annotations

import argparse

from w7tp_router_thermal_common import (
    base_result,
    collect_temperature_readings_from_text,
    load_report_temperatures,
    load_text_inputs,
    local_sensor_snapshot,
    print_json,
    state_from_temperature,
    summarize_temperatures,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP router thermal hotspot analyzer.")
    parser.add_argument("--probe-output", action="append")
    parser.add_argument("--thermal-json", action="append")
    parser.add_argument("--skip-local-sensors", action="store_true")
    args = parser.parse_args()

    snapshot = local_sensor_snapshot(skip_sensors=args.skip_local_sensors)
    probe_text, probe_sources = load_text_inputs(args.probe_output)
    report_readings, report_sources = load_report_temperatures(args.thermal_json)
    readings = list(snapshot["readings"])
    readings.extend(collect_temperature_readings_from_text(probe_text, "router_readonly_probe"))
    readings.extend(report_readings)
    summary = summarize_temperatures(readings)

    thermal_floor = 60.0
    hotspots = [
        item
        for item in sorted(readings, key=lambda row: float(row["temperature_c"]), reverse=True)
        if summary["max_temperature_c"] is not None and float(item["temperature_c"]) >= max(thermal_floor, summary["max_temperature_c"] - 5.0)
    ][:10]
    state = state_from_temperature("PASS_ROUTER_THERMAL_HOTSPOT_ANALYSIS", summary["max_temperature_c"])
    result = base_result("w7tp_router_thermal_hotspot_analyzer", state)
    result.update(
        {
            "probe_sources": probe_sources,
            "thermal_json_sources": report_sources,
            "summary": summary,
            "hotspots": hotspots,
            "thermal_floor_c": thermal_floor,
            "thermal_control_action_executed": False,
        }
    )
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
