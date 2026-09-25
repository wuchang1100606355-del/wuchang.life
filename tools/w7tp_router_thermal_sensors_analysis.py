#!/usr/bin/env python3
"""Router thermal sensors analysis. Local sensors and read-only probe only."""

from __future__ import annotations

import argparse

from w7tp_router_thermal_common import (
    base_result,
    collect_temperature_readings_from_text,
    load_text_inputs,
    local_sensor_snapshot,
    print_json,
    state_from_temperature,
    summarize_temperatures,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP local router thermal sensors analysis.")
    parser.add_argument("--probe-output", action="append", help="Router read-only probe thermal output.")
    parser.add_argument("--skip-local-sensors", action="store_true")
    args = parser.parse_args()

    snapshot = local_sensor_snapshot(skip_sensors=args.skip_local_sensors)
    probe_text, probe_sources = load_text_inputs(args.probe_output)
    readings = list(snapshot["readings"])
    readings.extend(collect_temperature_readings_from_text(probe_text, "router_readonly_probe"))
    summary = summarize_temperatures(readings)
    state = state_from_temperature("PASS_LOCAL_ROUTER_THERMAL_SENSORS", summary["max_temperature_c"])

    result = base_result("w7tp_router_thermal_sensors_analysis", state)
    result.update(
        {
            "thermal_raw": snapshot["thermal_raw"],
            "local_sensors": snapshot,
            "probe_sources": probe_sources,
            "readings": readings,
            "summary": summary,
            "thermal_control_action_executed": False,
        }
    )
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
