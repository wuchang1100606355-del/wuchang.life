#!/usr/bin/env python3
"""Detect router thermal throttle indicators from read-only probe output."""

from __future__ import annotations

import argparse

from w7tp_router_thermal_common import base_result, detect_throttle, load_text_inputs, print_json


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP router thermal throttle detector.")
    parser.add_argument("--probe-output", action="append", help="Router read-only probe output.")
    args = parser.parse_args()

    text, sources = load_text_inputs(args.probe_output)
    if not text.strip():
        result = base_result("w7tp_router_thermal_throttle_detector", "HOLD_ROUTER_THERMAL_THROTTLE_PROBE_REQUIRED")
        result.update({"reason": "Provide --probe-output from a router read-only probe.", "probe_sources": sources})
        return print_json(result)

    analysis = detect_throttle(text)
    state = "HOLD_ROUTER_THERMAL_THROTTLE_DETECTED" if analysis["throttle_detected"] else "PASS_ROUTER_THERMAL_THROTTLE_NOT_DETECTED"
    result = base_result("w7tp_router_thermal_throttle_detector", state)
    result.update({"probe_sources": sources, "analysis": analysis, "thermal_control_action_executed": False})
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
