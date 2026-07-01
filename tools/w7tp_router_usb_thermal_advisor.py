#!/usr/bin/env python3
"""Local thermal advisor for USB/router-capacity repair planning. Advice only."""

from __future__ import annotations

import argparse

from w7tp_router_usb_repair_common import (
    base_result,
    collect_temperature_values,
    parse_json_maybe,
    print_json,
    run_cmd,
    sysfs_thermal_readings,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP local USB thermal down-pressure advisor.")
    parser.add_argument("--skip-sensors", action="store_true", help="Do not run sensors -j.")
    args = parser.parse_args()

    sensors = None
    sensors_raw = None
    sensor_temps = []
    if not args.skip_sensors:
        sensors = run_cmd(["sensors", "-j"], stdout_limit=300000)
        sensors_raw = run_cmd(["sensors"], stdout_limit=300000)
        sensor_json = parse_json_maybe(sensors.get("stdout", ""))
        if sensor_json is not None:
            sensor_temps = collect_temperature_values(sensor_json)
    else:
        sensor_json = None

    sysfs_readings = sysfs_thermal_readings()
    sysfs_temps = [float(item["temperature_c"]) for item in sysfs_readings]
    all_temps = sensor_temps + sysfs_temps
    max_temp = max(all_temps) if all_temps else None

    if max_temp is not None and max_temp >= 75.0:
        state = "HOLD_THERMAL_CRITICAL"
    elif max_temp is not None and max_temp >= 65.0:
        state = "HOLD_THERMAL_HIGH"
    else:
        state = "PASS_THERMAL_ADVICE_READY"

    result = base_result("w7tp_router_usb_thermal_advisor", state)
    result.update(
        {
            "max_temperature_c": max_temp,
            "sensors_command": sensors,
            "sensors_raw_command": sensors_raw,
            "sensors_json": sensor_json,
            "thermal_raw": sensors_raw.get("stdout", "") if sensors_raw else "",
            "sysfs_thermal_readings": sysfs_readings,
            "downclock_or_config_action_executed": False,
            "advice": [
                "Move router to cooler area.",
                "Avoid placing router near walls or enclosed spaces.",
                "Ensure USB is not overheating.",
                "Replace USB if thermal throttling persists.",
                "Keep router_capacity_guard on HOLD until USB storage errors are cleared by evidence.",
                "Reduce write frequency to the USB dead-letter backend before retest.",
                "Use a powered USB hub or replace with higher-endurance storage if resets continue.",
                "Do not change router clock, router config, JFFS, or services from this local tool.",
            ],
        }
    )
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
