#!/usr/bin/env python3
"""Local USB remount readiness check. It never performs mount or remount."""

from __future__ import annotations

import argparse

from w7tp_router_usb_repair_common import base_result, find_mounts_for_device, print_json, run_cmd, valid_device_path


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP local USB remount check. No remount is executed.")
    parser.add_argument("--device", help="Local device or partition, for example /dev/sdb1")
    parser.add_argument("--mountpoint", help="Local mountpoint to inspect")
    args = parser.parse_args()

    mount = run_cmd(["mount"], stdout_limit=300000)
    result = base_result("w7tp_router_usb_remount_check", "PASS_LOCAL_USB_MOUNT_CHECK")
    result.update(
        {
            "mounts": mount.get("stdout", ""),
            "usb_mounted": "/media" in mount.get("stdout", "") or "/mnt" in mount.get("stdout", ""),
            "mount_command": mount,
            "remount_executed": False,
            "mount_executed": False,
            "reason": "Inspection only. This tool emits operator checklist items and does not run mount.",
        }
    )

    if args.device:
        if not valid_device_path(args.device):
            result["STATE"] = "HOLD_REMOUNT_DEVICE_INVALID"
            result.update({"device": args.device})
            return print_json(result)
        result["device_mounts"] = find_mounts_for_device(args.device)

    if args.mountpoint:
        result["mountpoint"] = args.mountpoint
        result["mountpoint_findmnt"] = run_cmd(["findmnt", "-J", "--target", args.mountpoint], stdout_limit=100000)

    if not args.device and not args.mountpoint:
        result["reason"] = "General mount table inspection only. Provide --device or --mountpoint for targeted local inspection."

    result["operator_checklist"] = [
        "Confirm the target is a local USB device, not router storage.",
        "Confirm no service is writing to the mountpoint before any manual remount.",
        "Prefer manual read-only remount first when corruption is suspected.",
        "Do not perform router deploy, restart, reboot, JFFS write, or SSH from this flow.",
    ]
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
