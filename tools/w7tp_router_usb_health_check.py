#!/usr/bin/env python3
"""Local USB health check for router-capacity repair planning."""

from __future__ import annotations

import argparse

from w7tp_router_usb_repair_common import analyze_kernel_log, base_result, print_json, run_cmd


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP local USB health check. No router access.")
    parser.add_argument("--kernel-log-limit", type=int, default=200000)
    args = parser.parse_args()

    blk = run_cmd(["lsblk", "-o", "NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE,MODEL,SERIAL"], stdout_limit=200000)
    if blk["returncode"] != 0:
        blk = run_cmd(["lsblk", "-o", "NAME,SIZE,TYPE,MOUNTPOINT"], stdout_limit=200000)

    dmesg = run_cmd(["dmesg"], stdout_limit=args.kernel_log_limit)
    analysis = analyze_kernel_log(dmesg.get("stdout", ""))
    usb_errors_detected = bool(analysis["usb_errors_detected"])

    state = "PASS_LOCAL_USB_HEALTH_CHECK"
    if dmesg["returncode"] != 0:
        state = "HOLD_KERNEL_LOG_UNAVAILABLE"
    if usb_errors_detected:
        state = "HOLD_USB_STORAGE_ERRORS_DETECTED"

    result = base_result("w7tp_router_usb_health_check", state)
    result.update(
        {
            "lsblk": blk.get("stdout", ""),
            "kernel_log": dmesg.get("stdout", ""),
            "usb_errors_detected": usb_errors_detected,
            "commands": {"lsblk": blk, "dmesg": dmesg},
            "kernel_log_analysis": analysis,
        }
    )
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
