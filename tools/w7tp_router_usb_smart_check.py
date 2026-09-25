#!/usr/bin/env python3
"""Local USB SMART check. Requires a local /dev device and never writes."""

from __future__ import annotations

import argparse

from w7tp_router_usb_repair_common import (
    base_result,
    file_exists,
    parse_json_maybe,
    print_json,
    run_cmd,
    smart_passed_from_payload,
    valid_device_path,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP local USB SMART check. No router access.")
    parser.add_argument("--device", help="Local block device, for example /dev/sdb")
    parser.add_argument("--smart-device-type", help="Optional smartctl -d value, for example sat")
    args = parser.parse_args()

    if not args.device:
        result = base_result("w7tp_router_usb_smart_check", "HOLD_SMART_DEVICE_REQUIRED")
        result.update(
            {
                "reason": "Provide --device /dev/...",
                "candidate_devices": run_cmd(["lsblk", "-o", "NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE,MODEL,SERIAL"]),
            }
        )
        return print_json(result)

    if not valid_device_path(args.device) or not file_exists(args.device):
        result = base_result("w7tp_router_usb_smart_check", "HOLD_SMART_DEVICE_INVALID")
        result.update({"device": args.device, "reason": "Device path must exist under /dev and must not contain traversal."})
        return print_json(result)

    version = run_cmd(["smartctl", "--version"], stdout_limit=50000)
    if not version["available"]:
        result = base_result("w7tp_router_usb_smart_check", "HOLD_SMARTCTL_NOT_AVAILABLE")
        result.update({"device": args.device, "smartctl_version": version, "install_hint": "Install smartmontools locally, then rerun."})
        return print_json(result)

    base_cmd = ["smartctl"]
    if args.smart_device_type:
        base_cmd.extend(["-d", args.smart_device_type])

    health = run_cmd(base_cmd + ["-H", "-j", args.device], stdout_limit=200000)
    attributes = run_cmd(base_cmd + ["-A", "-j", args.device], stdout_limit=300000)
    full = run_cmd(base_cmd + ["-a", "-j", args.device], stdout_limit=500000)
    health_json = parse_json_maybe(health.get("stdout", ""))
    attributes_json = parse_json_maybe(attributes.get("stdout", ""))
    full_json = parse_json_maybe(full.get("stdout", ""))
    smart_passed = smart_passed_from_payload(health_json)
    smart_output = full.get("stdout", "") or health.get("stdout", "")
    smart_errors = "Error" in smart_output or "FAILED" in smart_output or smart_passed is False

    if smart_passed is True:
        state = "PASS_LOCAL_USB_SMART_CHECK"
    elif smart_passed is False:
        state = "HOLD_SMART_HEALTH_FAILED"
    else:
        state = "HOLD_SMART_HEALTH_UNKNOWN"

    result = base_result("w7tp_router_usb_smart_check", state)
    result.update(
        {
            "device": args.device,
            "smart_device_type": args.smart_device_type,
            "smart_passed": smart_passed,
            "smart_output": smart_output,
            "smart_errors": bool(smart_errors),
            "commands": {
                "smartctl_version": version,
                "smartctl_health": health,
                "smartctl_attributes": attributes,
                "smartctl_all": full,
            },
            "smartctl_health_json": health_json,
            "smartctl_attributes_json": attributes_json,
            "smartctl_all_json": full_json,
            "notes": [
                "USB bridges may require --smart-device-type sat.",
                "This tool does not perform SMART self-tests or writes.",
                "Privilege escalation is intentionally not used; permission gaps return HOLD for human handling.",
            ],
        }
    )
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
