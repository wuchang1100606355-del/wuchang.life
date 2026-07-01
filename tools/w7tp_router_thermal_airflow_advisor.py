#!/usr/bin/env python3
"""Airflow advisor for router thermal stabilization. Advice only."""

from __future__ import annotations

import argparse

from w7tp_router_thermal_common import (
    base_result,
    collect_temperature_readings_from_text,
    load_report_temperatures,
    load_text_inputs,
    print_json,
    risk_score,
    state_from_temperature,
    summarize_temperatures,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP router thermal airflow advisor.")
    parser.add_argument("--thermal-json", action="append")
    parser.add_argument("--probe-output", action="append")
    args = parser.parse_args()

    readings, sources = load_report_temperatures(args.thermal_json)
    probe_text, probe_sources = load_text_inputs(args.probe_output)
    readings.extend(collect_temperature_readings_from_text(probe_text, "router_readonly_probe"))
    if not readings:
        result = base_result("w7tp_router_thermal_airflow_advisor", "HOLD_ROUTER_THERMAL_AIRFLOW_INPUT_REQUIRED")
        result.update({"reason": "Provide --thermal-json or --probe-output.", "thermal_json_sources": sources, "probe_sources": probe_sources})
        return print_json(result)
    summary = summarize_temperatures(readings)
    risk = risk_score(summary)
    state = state_from_temperature("PASS_ROUTER_THERMAL_AIRFLOW_ADVICE_READY", summary["max_temperature_c"])
    result = base_result("w7tp_router_thermal_airflow_advisor", state)
    result.update(
        {
            "thermal_json_sources": sources,
            "probe_sources": probe_sources,
            "summary": summary,
            "risk": risk,
            "airflow_action_executed": False,
            "advice": [
                "Increase passive airflow around router intake and exhaust sides.",
                "Remove stacked equipment from above and below the router.",
                "Use a low-noise external fan only as a human-operated physical action.",
                "Reduce USB and packet write pressure until temperatures remain below 65C.",
                "Do not change router config, clock, services, or fan controls from this tool.",
            ],
        }
    )
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
