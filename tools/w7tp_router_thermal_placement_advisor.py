#!/usr/bin/env python3
"""Router placement advisor for thermal stabilization. Advice only."""

from __future__ import annotations

import argparse

from w7tp_router_thermal_common import (
    base_result,
    collect_temperature_readings_from_text,
    load_report_temperatures,
    load_text_inputs,
    print_json,
    state_from_temperature,
    summarize_temperatures,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP router thermal placement advisor.")
    parser.add_argument("--thermal-json", action="append")
    parser.add_argument("--probe-output", action="append")
    args = parser.parse_args()

    readings, sources = load_report_temperatures(args.thermal_json)
    probe_text, probe_sources = load_text_inputs(args.probe_output)
    readings.extend(collect_temperature_readings_from_text(probe_text, "router_readonly_probe"))
    if not readings:
        result = base_result("w7tp_router_thermal_placement_advisor", "HOLD_ROUTER_THERMAL_PLACEMENT_INPUT_REQUIRED")
        result.update({"reason": "Provide --thermal-json or --probe-output.", "thermal_json_sources": sources, "probe_sources": probe_sources})
        return print_json(result)
    summary = summarize_temperatures(readings)
    state = state_from_temperature("PASS_ROUTER_THERMAL_PLACEMENT_ADVICE_READY", summary["max_temperature_c"])
    result = base_result("w7tp_router_thermal_placement_advisor", state)
    result.update(
        {
            "thermal_json_sources": sources,
            "probe_sources": probe_sources,
            "summary": summary,
            "placement_action_executed": False,
            "advice": [
                "Place router in open air, not inside a cabinet or behind a monitor.",
                "Keep at least 10 cm clearance on all ventilated sides.",
                "Keep USB storage away from router heat exhaust.",
                "Avoid direct sun, wall corners, and dense cable bundles around vents.",
                "Retest thermal probe after physical placement changes.",
            ],
        }
    )
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
