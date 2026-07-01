#!/usr/bin/env python3
"""Read-only local JFFS image health check."""

from __future__ import annotations

import argparse
from pathlib import Path

from w7tp_jffs_repair_common import base_result, image_magic_summary, print_json, run_cmd, valid_local_file


def main() -> int:
    parser = argparse.ArgumentParser(description="W7TP local JFFS image health check. Read-only.")
    parser.add_argument("--image", help="Local JFFS image file to inspect.")
    parser.add_argument("--sample-bytes", type=int, default=1048576)
    args = parser.parse_args()

    if not args.image:
        result = base_result("w7tp_jffs_image_health_check", "HOLD_JFFS_IMAGE_REQUIRED")
        result.update({"reason": "Provide --image pointing to a local JFFS image backup."})
        return print_json(result)

    if not valid_local_file(args.image):
        result = base_result("w7tp_jffs_image_health_check", "HOLD_JFFS_IMAGE_INVALID")
        result.update({"image": args.image, "reason": "Image must be an existing local file without path traversal."})
        return print_json(result)

    image = Path(args.image)
    summary = image_magic_summary(args.image, max(4096, args.sample_bytes))
    file_cmd = run_cmd(["file", "-b", args.image], stdout_limit=50000)
    state = "PASS_LOCAL_JFFS_IMAGE_HEALTH_CHECK"
    if summary["size_bytes"] == 0:
        state = "HOLD_JFFS_IMAGE_EMPTY"
    elif not summary["possible_jffs2"]:
        state = "HOLD_JFFS_IMAGE_TYPE_UNKNOWN"
    elif summary["empty_or_erased_like"]:
        state = "HOLD_JFFS_IMAGE_ERASED_OR_BLANK_LIKE"

    result = base_result("w7tp_jffs_image_health_check", state)
    result.update(
        {
            "image": str(image),
            "file_command": file_cmd,
            "image_health": summary,
            "content_dumped": False,
            "write_action_executed": False,
        }
    )
    return print_json(result)


if __name__ == "__main__":
    raise SystemExit(main())
