#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W7TP Runtime Artifact Guard.

- Does not write repo files.
- Does not stage files.
- Does not commit.
- Does not deploy.
- Checks only whether runtime/ artifacts are staged.
"""

import json
import subprocess


def staged_files():
    return subprocess.check_output(
        ["git", "diff", "--cached", "--name-only"],
        text=True,
    ).splitlines()


def main() -> int:
    files = staged_files()
    runtime = [path for path in files if path.startswith("runtime/")]

    if runtime:
        print(json.dumps({
            "STATE": "HOLD_RUNTIME_ARTIFACT_STAGED",
            "decision": "HOLD",
            "files": runtime,
            "writes_repo": False,
            "auto_stage": False,
            "auto_commit": False,
            "deploy": False,
        }, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps({
        "STATE": "PASS_RUNTIME_ARTIFACT_GUARD",
        "decision": "PASS",
        "files": [],
        "writes_repo": False,
        "auto_stage": False,
        "auto_commit": False,
        "deploy": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
