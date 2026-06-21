#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/taiji_admin/Taiji_Hub")
API = ROOT / "runtime/sandbox/pos_mvp_autodev/api/pos_mvp_api.py"
VERIFY = ROOT / "scripts/verify/verify_pos_mvp_sandbox.sh"


def main() -> int:
    if not API.exists():
        raise SystemExit(f"missing sandbox API: {API}")
    init = subprocess.run(
        [sys.executable, str(API), "init"],
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    verify = subprocess.run(
        ["bash", str(VERIFY)],
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    print(json.dumps({
        "STATE": "POS_MVP_SANDBOX_FILES_GENERATED",
        "SANDBOX": "runtime/sandbox/pos_mvp_autodev",
        "MENU_SOURCE": "REAL_MENU_FROM_REPO_ODOO_XML",
        "GENERATE_STDOUT": init.stdout.splitlines()[:3],
        "VERIFY_RESULT": "PASS" if "STATE=POS_MVP_SANDBOX_AUTODEV_PASS" in verify.stdout else "UNKNOWN",
        "SECRET_READ": False,
        "MEMBER_PLAINTEXT_READ": False,
        "DB_WRITE": False,
        "SERVICE_RESTART": False,
        "DEPLOY": False,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
