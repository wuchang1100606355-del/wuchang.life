#!/usr/bin/env python3
"""Local USB replacement decision advisor. It reads reports and writes nothing to devices."""

from __future__ import annotations

import argparse
from typing import Any

from w7tp_router_usb_repair_common import base_result, collect_temperature_values, print_json, read_json_file, walk_json


def any_bool_at_key(payloads: list[Any], key_name: str, expected: bool) -> bool:
    for payload in payloads:
        for path, value in walk_json(payload):
            if path.rsplit(".", 1)[-1] == key_name and value is expected:
                return True
    return False


def max_kernel_hits(payloads: list[Any]) -> int:
    hits = 0
    for payload in payloads:
        for path, value in walk_json(payload):
            if path.endswith(".total_hits") and isinstance(value, int):
                hits = max(hits, value)
    return hits


def load_optional(path: str | None) -> Any | None:
    return read_json_file(path) if path else None


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP local USB replacement advisor.")
    parser.add_argument("--health-json")
    parser.add_argument("--smart-json")
    parser.add_argument("--kernel-json")
    parser.add_argument("--thermal-json")
    args = parser.parse_args()

    named_payloads = {
        "health": load_optional(args.health_json),
        "smart": load_optional(args.smart_json),
        "kernel": load_optional(args.kernel_json),
        "thermal": load_optional(args.thermal_json),
    }
    payloads = [value for value in named_payloads.values() if value is not None]

    if not payloads:
        result = base_result("w7tp_router_usb_replacement_advisor", "HOLD_REPLACEMENT_INPUT_REQUIRED")
        result.update({"reason": "Provide at least one --health-json, --smart-json, --kernel-json, or --thermal-json report."})
        return print_json(result)

    score = 0
    reasons: list[str] = []

    if any_bool_at_key(payloads, "smart_passed", False):
        score += 45
        reasons.append("SMART health failed.")
    if any_bool_at_key(payloads, "usb_errors_detected", True):
        score += 30
        reasons.append("USB/storage errors detected in kernel or health report.")

    hits = max_kernel_hits(payloads)
    if hits >= 10:
        score += 25
        reasons.append("Repeated kernel storage errors detected.")
    elif hits >= 3:
        score += 15
        reasons.append("Multiple kernel storage errors detected.")

    temperatures = []
    for payload in payloads:
        temperatures.extend(collect_temperature_values(payload))
    max_temp = max(temperatures) if temperatures else None
    if max_temp is not None and max_temp >= 75.0:
        score += 20
        reasons.append("Critical thermal reading detected.")
    elif max_temp is not None and max_temp >= 65.0:
        score += 10
        reasons.append("High thermal reading detected.")

    if score >= 60:
        recommendation = "REPLACE_USB_NOW"
        state = "HOLD_REPLACE_USB_NOW"
    elif score >= 35:
        recommendation = "HOLD_AND_RUN_LOCAL_FSCK_SMART_RETEST"
        state = "HOLD_USB_RETEST_REQUIRED"
    else:
        recommendation = "MONITOR_AND_KEEP_ROUTER_CAPACITY_GUARD_HOLD"
        state = "PASS_USB_REPLACEMENT_ADVICE_READY"

    result = base_result("w7tp_router_usb_replacement_advisor", state)
    result.update(
        {
            "score": score,
            "recommendation": recommendation,
            "reasons": reasons,
            "max_kernel_hits": hits,
            "max_temperature_c": max_temp,
            "input_reports": {
                "health_json": args.health_json,
                "smart_json": args.smart_json,
                "kernel_json": args.kernel_json,
                "thermal_json": args.thermal_json,
            },
            "device_action_executed": False,
        }
    )
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
