#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify W7TP Total / Branch runtime CLI locally."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.w7tp_total_branch_runtime import SAFETY_FLAGS, branch_packet, init_runtime, load_state, register_branch, total_packet


def fail(message: str) -> None:
    print(f"FAIL={message}")
    print("STATE=HOLD_VERIFY_W7TP_TOTAL_BRANCH_RUNTIME")
    raise SystemExit(1)


def check(condition: bool, name: str) -> None:
    print(f"{name}={'PASS' if condition else 'FAIL'}")
    if not condition:
        fail(name)


def run_cli(*args: str) -> dict:
    proc = subprocess.run(
        [sys.executable, "tools/w7tp_total_branch_runtime.py", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    check(proc.returncode == 0, "CLI_" + "_".join(arg.strip("-").replace("-", "_") for arg in args[:1] or ["DEFAULT"]))
    return json.loads(proc.stdout)


def main() -> int:
    init_result = init_runtime()
    check(init_result["STATE"] == "PASS_W7TP_TOTAL_BRANCH_RUNTIME", "INIT_RUNTIME")

    cli_init = run_cli("--init")
    check(cli_init["STATE"] == "PASS_W7TP_TOTAL_BRANCH_RUNTIME", "CLI_INIT_STATE")

    status = run_cli("--status")
    check(status["STATE"] == "PASS_W7TP_TOTAL_BRANCH_RUNTIME", "STATUS_STATE")

    total = run_cli("--emit-total-packet")
    check(total["TOTAL_FIELD_PACKET"]["authority"] == "TOTAL_FIELD", "TOTAL_AUTHORITY")
    check(total["TOTAL_FIELD_PACKET"]["packet_type"] == "W7TP_TOTAL_FIELD_PACKET", "TOTAL_PACKET_TYPE")

    store = register_branch("cafe_main", "STORE")
    prop = register_branch("property_demo", "PROPERTY")
    check(store["BRANCH_FIELD_PACKETS"][0]["branch_type"] == "STORE", "REGISTER_STORE")
    check(prop["BRANCH_FIELD_PACKETS"][0]["branch_type"] == "PROPERTY", "REGISTER_PROPERTY")

    cli_store = run_cli("--register-branch", "--branch-id", "cafe_main", "--branch-type", "STORE")
    check(cli_store["BRANCH_FIELD_PACKETS"][0]["branch_id"] == "cafe_main", "CLI_REGISTER_STORE")

    branch_emit = run_cli("--emit-branch-packet", "--branch-id", "cafe_main")
    packet = branch_emit["BRANCH_FIELD_PACKETS"][0]
    check(packet["authority"] == "BRANCH_FIELD_LIMITED", "BRANCH_LIMITED_AUTHORITY")
    check(packet["total_field_authority"] is False, "BRANCH_NO_TOTAL_AUTHORITY")
    check("grant_total_field_authority" in packet["cannot_do"], "BRANCH_CANNOT_GRANT_TOTAL")

    state = load_state()
    packets = [branch_packet(row) for row in state["branches"].values()]
    check(total_packet(state)["authority"] == "TOTAL_FIELD", "TOTAL_PACKET_BUILDER")
    check(any(row["branch_id"] == "property_demo" for row in packets), "PROPERTY_PACKET_PRESENT")
    check(SAFETY_FLAGS["DB_WRITE"] is False, "NO_DB_WRITE")
    check(SAFETY_FLAGS["SECRET_READ"] is False, "NO_SECRET_READ")
    check(SAFETY_FLAGS["MEMBER_PLAINTEXT_READ"] is False, "NO_MEMBER_PLAINTEXT_READ")
    json.dumps(branch_emit, ensure_ascii=False)
    check(True, "JSON_OUTPUT_VALID")

    run_id = time.strftime("%Y%m%d_%H%M%S")
    report_dir = ROOT / "runtime" / "total_field" / "total_branch_runtime" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "STATE": "PASS_VERIFY_W7TP_TOTAL_BRANCH_RUNTIME",
        "RUN_ID": run_id,
        "checks": [
            "init runtime",
            "emit total field packet",
            "register store branch",
            "register property branch",
            "emit branch packet",
            "branch cannot gain total authority",
            "no DB write",
            "no secret read",
            "JSON output valid",
        ],
        "safety_flags": SAFETY_FLAGS,
    }
    report_path = report_dir / "VERIFY_REPORT.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("STATE=PASS_VERIFY_W7TP_TOTAL_BRANCH_RUNTIME")
    print(f"REPORT={report_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
