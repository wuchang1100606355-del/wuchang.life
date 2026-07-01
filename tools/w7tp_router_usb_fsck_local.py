#!/usr/bin/env python3
"""Local USB fsck gate. Dry-run by default; repair requires explicit consent."""

from __future__ import annotations

import argparse

from w7tp_router_usb_repair_common import base_result, file_exists, find_mounts_for_device, print_json, run_cmd, valid_device_path


def fsck_state(returncode: int, repair: bool) -> str:
    if returncode == 0:
        return "PASS_LOCAL_FSCK_REPAIR_COMPLETED" if repair else "PASS_LOCAL_FSCK_DRYRUN_COMPLETED"
    if returncode == 127:
        return "HOLD_FSCK_NOT_AVAILABLE"
    return "HOLD_FSCK_REPORTED_ISSUES"


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP local-only fsck tool. No router access.")
    parser.add_argument("--device", help="Local unmounted block device or partition, for example /dev/sdb1")
    parser.add_argument("--check-readonly", action="store_true", help="Run fsck -n against the local device.")
    parser.add_argument("--repair", action="store_true", help="Run fsck -y. This can write to the local USB filesystem.")
    parser.add_argument("--i-understand-local-usb-write", action="store_true", help="Required with --repair.")
    args = parser.parse_args()

    if not args.device:
        result = base_result("w7tp_router_usb_fsck_local", "HOLD_FSCK_DEVICE_REQUIRED")
        result.update({"reason": "Provide --device /dev/..."})
        return print_json(result)

    if not valid_device_path(args.device) or not file_exists(args.device):
        result = base_result("w7tp_router_usb_fsck_local", "HOLD_FSCK_DEVICE_INVALID")
        result.update({"device": args.device, "reason": "Device path must exist under /dev and must not contain traversal."})
        return print_json(result)

    mounts = find_mounts_for_device(args.device)

    if args.repair and not args.i_understand_local_usb_write:
        result = base_result("w7tp_router_usb_fsck_local", "HOLD_FSCK_REPAIR_REQUIRES_EXPLICIT_LOCAL_USB_WRITE_ACK")
        result.update({"device": args.device, "mounted": mounts["mounted"], "mounts": mounts})
        return print_json(result)

    if args.repair and mounts["mounted"]:
        result = base_result("w7tp_router_usb_fsck_local", "HOLD_FSCK_REPAIR_BLOCKED_DEVICE_MOUNTED")
        result.update({"device": args.device, "mounts": mounts, "reason": "Unmount locally before repair. This tool will not unmount for you."})
        return print_json(result)

    if args.repair:
        command = ["fsck", "-y", args.device]
        usb_write = True
    elif args.check_readonly:
        command = ["fsck", "-n", args.device]
        usb_write = False
    else:
        command = ["fsck", "-N", args.device]
        usb_write = False

    fsck = run_cmd(command, timeout=120, stdout_limit=400000, stderr_limit=100000)
    result = base_result("w7tp_router_usb_fsck_local", fsck_state(fsck["returncode"], args.repair), usb_write=usb_write)
    result.update(
        {
            "device": args.device,
            "mode": "repair" if args.repair else "readonly_check" if args.check_readonly else "plan_only",
            "mounts": mounts,
            "command_result": fsck,
            "fsck_output": fsck.get("stdout", ""),
            "fsck_errors": "error" in fsck.get("stdout", "").lower() or fsck["returncode"] not in {0},
            "repair_executed": bool(args.repair and args.i_understand_local_usb_write and not mounts["mounted"]),
            "privilege_escalation_attempted": False,
        }
    )
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
