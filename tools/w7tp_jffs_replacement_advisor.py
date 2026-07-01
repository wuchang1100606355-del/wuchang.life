#!/usr/bin/env python3
"""JFFS replacement/maintenance decision advisor. Advice only."""

from __future__ import annotations

import argparse
from typing import Any

from w7tp_jffs_repair_common import base_result, bool_seen, max_numeric_key, print_json, read_json_file


def load_optional(path: str | None) -> Any | None:
    return read_json_file(path) if path else None


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP JFFS replacement advisor.")
    parser.add_argument("--free-space-json")
    parser.add_argument("--write-pressure-json")
    parser.add_argument("--kernel-json")
    parser.add_argument("--image-json")
    parser.add_argument("--thermal-json")
    args = parser.parse_args()

    payloads = [
        payload
        for payload in [
            load_optional(args.free_space_json),
            load_optional(args.write_pressure_json),
            load_optional(args.kernel_json),
            load_optional(args.image_json),
            load_optional(args.thermal_json),
        ]
        if payload is not None
    ]
    if not payloads:
        result = base_result("w7tp_jffs_replacement_advisor", "HOLD_JFFS_REPLACEMENT_INPUT_REQUIRED")
        result.update({"reason": "Provide one or more JFFS analysis reports."})
        return print_json(result)

    score = 0
    reasons: list[str] = []
    if bool_seen(payloads, "free_space_low", True):
        score += 25
        reasons.append("JFFS free space is low.")
    if bool_seen(payloads, "jffs_errors_detected", True):
        score += 35
        reasons.append("JFFS kernel errors detected.")
    if bool_seen(payloads, "empty_or_erased_like", True):
        score += 35
        reasons.append("JFFS image appears blank, erased, or invalid.")
    pressure_score = max_numeric_key(payloads, "score") or 0.0
    if pressure_score >= 50:
        score += 30
        reasons.append("JFFS write pressure is high.")
    max_temp = max_numeric_key(payloads, "max_temperature_c")
    if max_temp is not None and max_temp >= 75:
        score += 20
        reasons.append("Thermal stress is critical.")
    elif max_temp is not None and max_temp >= 65:
        score += 10
        reasons.append("Thermal stress is elevated.")

    if score >= 70:
        state = "HOLD_JFFS_MAINTENANCE_OR_ROUTER_FLASH_REVIEW_REQUIRED"
        recommendation = "HUMAN_MAINTENANCE_WINDOW_AND_FLASH_HEALTH_REVIEW"
    elif score >= 35:
        state = "HOLD_JFFS_DEGRADED_RETEST_REQUIRED"
        recommendation = "KEEP_JFFS_POINTER_ONLY_AND_RETEST_AFTER_USB_REPAIR"
    else:
        state = "PASS_JFFS_REPLACEMENT_ADVICE_READY"
        recommendation = "MONITOR_KEEP_POINTER_STATUS_ONLY"

    result = base_result("w7tp_jffs_replacement_advisor", state)
    result.update(
        {
            "score": score,
            "recommendation": recommendation,
            "reasons": reasons,
            "max_temperature_c": max_temp,
            "device_action_executed": False,
            "jffs_replacement_executed": False,
        }
    )
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
