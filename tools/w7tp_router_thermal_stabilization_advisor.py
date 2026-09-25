#!/usr/bin/env python3
"""Total Field review packet advisor for router thermal stabilization."""

from __future__ import annotations

import argparse

from w7tp_router_thermal_common import (
    THERMAL_DOWNPRESSURE_C,
    base_result,
    collect_temperature_readings_from_text,
    detect_throttle,
    load_report_temperatures,
    load_text_inputs,
    print_json,
    risk_score,
    summarize_temperatures,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP router thermal stabilization advisor for Total Field review.")
    parser.add_argument("--thermal-json", action="append")
    parser.add_argument("--probe-output", action="append")
    parser.add_argument("--usb-repair-complete-evidence")
    args = parser.parse_args()

    readings, sources = load_report_temperatures(args.thermal_json)
    probe_text, probe_sources = load_text_inputs(args.probe_output)
    readings.extend(collect_temperature_readings_from_text(probe_text, "router_readonly_probe"))
    throttle = detect_throttle(probe_text)
    if not readings and not probe_text.strip():
        result = base_result("w7tp_router_thermal_stabilization_advisor", "HOLD_ROUTER_THERMAL_STABILIZATION_INPUT_REQUIRED")
        result.update({"reason": "Provide thermal analysis JSON or read-only probe output.", "stabilization_action_executed": False})
        return print_json(result)

    summary = summarize_temperatures(readings)
    risk = risk_score(summary, throttle_detected=throttle["throttle_detected"])
    max_temp = summary["max_temperature_c"]
    downpressure_required = max_temp is not None and max_temp >= THERMAL_DOWNPRESSURE_C
    state = "PASS_ROUTER_THERMAL_STABILIZATION_ADVICE_READY"
    if downpressure_required:
        state = "HOLD_ROUTER_THERMAL_DOWNPRESSURE_REQUIRED"
    elif risk["risk_level"] in {"critical", "high"}:
        state = "HOLD_ROUTER_THERMAL_STABILIZATION_REVIEW_REQUIRED"
    elif not args.usb_repair_complete_evidence:
        state = "HOLD_ROUTER_THERMAL_STABILIZATION_USB_REPAIR_EVIDENCE_REQUIRED"

    result = base_result("w7tp_router_thermal_stabilization_advisor", state)
    result.update(
        {
            "thermal_json_sources": sources,
            "probe_sources": probe_sources,
            "usb_repair_complete_evidence": args.usb_repair_complete_evidence,
            "summary": summary,
            "throttle": throttle,
            "risk": risk,
            "thermal_downpressure_required": downpressure_required,
            "stabilization_action_executed": False,
            "formal_router_action": "HOLD",
            "jffs_repair_allowed": False,
            "total_field_review_notes": [
                "Thermal at or above 78C requires downpressure before repair progression.",
                "USB repair evidence is required before any JFFS repair planning.",
                "This suite produces recommendations only and does not control router thermal behavior.",
            ],
            "stabilization_advice": [
                "Reduce router workload and packet write pressure during cooling retest.",
                "Improve physical airflow and placement before any router maintenance window.",
                "Retest with read-only probe after cooling changes.",
                "Keep USB and JFFS repair flows on HOLD until thermal and USB evidence are acceptable.",
            ],
        }
    )
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
