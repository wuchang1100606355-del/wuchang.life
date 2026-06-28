#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify W7TP Codex task adapter locally."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.w7tp_codex_task_adapter import DEFAULT_FORBIDDEN_ACTIONS, run_adapter


def fail(message: str) -> None:
    print(f"FAIL={message}")
    print("STATE=HOLD_VERIFY_W7TP_CODEX_TASK_ADAPTER")
    raise SystemExit(1)


def check(condition: bool, name: str) -> None:
    print(f"{name}={'PASS' if condition else 'FAIL'}")
    if not condition:
        fail(name)


def main() -> int:
    run_id = time.strftime("%Y%m%d_%H%M%S")
    out_path = f"runtime/total_field/codex_tasks/{run_id}/xiaoj_casual_chat_task.md"
    allowed = ["tools/w7tp_packet_inference_runtime.py", "web/packet_inference_cockpit/app.js"]
    forbidden = [".env", "data/internal_members/**", "Wuchang_Odoo_Core/**"]

    result = run_adapter(
        "小J 閒話家常能力",
        "add casual conversation layer",
        allowed,
        out_path,
        forbidden_files=forbidden,
        verify_commands=["python3 -m py_compile tools/w7tp_packet_inference_runtime.py"],
        risk_scan_commands=["grep -RInE '<safety-pattern>' tools/w7tp_packet_inference_runtime.py || true"],
    )
    packet = result["CODEX_TASK_PACKET"]
    check(result["STATE"] == "PASS_W7TP_CODEX_TASK_ADAPTER", "ADAPTER_STATE")
    check(packet["packet_type"] == "W7TP_CODEX_TASK_PACKET", "TASK_PACKET_TYPE")
    check(packet["codex_authority"] is False, "CODEX_AUTHORITY_FALSE")
    check(packet["candidate_only"] is True, "CANDIDATE_ONLY_TRUE")
    for action in ["git_add_dot", "auto_commit", "deploy", "secret_read", "member_plaintext_read"]:
        check(action in packet["forbidden_actions"], f"FORBIDDEN_{action}")
    check(packet["allowed_files"] == allowed, "ALLOWED_FILES_EXACT")
    check(packet["forbidden_files"] == forbidden, "FORBIDDEN_FILES_PRESENT")

    task_file = ROOT / result["TASK_FILE"]
    check(task_file.exists(), "TASK_FILE_EXISTS")
    text = task_file.read_text(encoding="utf-8")
    for phrase in [
        "Codex 不是總場",
        "candidate only",
        "Allowed Files",
        "Forbidden Files",
        "Safety Flags",
        "Verify Commands",
        "Risk Scan",
        "no git add .",
        "no auto commit",
        "Final Response Format",
    ]:
        check(phrase in text, "TASK_MARKDOWN_" + phrase.replace(" ", "_").replace(".", "DOT"))

    cli_out = f"runtime/total_field/codex_tasks/{run_id}/cli_task.md"
    cli = subprocess.run(
        [
            sys.executable,
            "tools/w7tp_codex_task_adapter.py",
            "--title",
            "CLI task",
            "--intent",
            "verify cli adapter",
            "--allowed-files",
            "tools/w7tp_total_branch_runtime.py",
            "tools/w7tp_codex_task_adapter.py",
            "--forbidden-files",
            ".env",
            "data/internal_members/**",
            "--out",
            cli_out,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    check(cli.returncode == 0, "CLI_RETURN_ZERO")
    cli_data = json.loads(cli.stdout)
    check(cli_data["CODEX_TASK_PACKET"]["codex_authority"] is False, "CLI_CODEX_AUTHORITY_FALSE")
    check((ROOT / cli_data["TASK_FILE"]).exists(), "CLI_TASK_FILE_EXISTS")
    check(set(DEFAULT_FORBIDDEN_ACTIONS).issubset(set(cli_data["CODEX_TASK_PACKET"]["forbidden_actions"])), "CLI_DEFAULT_FORBIDDEN_ACTIONS")

    report_dir = ROOT / "runtime" / "total_field" / "codex_tasks" / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "STATE": "PASS_VERIFY_W7TP_CODEX_TASK_ADAPTER",
        "RUN_ID": run_id,
        "task_file": result["TASK_FILE"],
        "checks": [
            "create CODEX_TASK_PACKET",
            "render markdown task",
            "codex_authority=false",
            "candidate_only=true",
            "forbidden actions present",
            "allowed_files exact",
            "forbidden_files present",
            "task file exists",
        ],
    }
    report_path = report_dir / "VERIFY_REPORT.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("STATE=PASS_VERIFY_W7TP_CODEX_TASK_ADAPTER")
    print(f"REPORT={report_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
