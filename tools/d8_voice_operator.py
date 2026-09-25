#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/home/taiji_admin/Taiji_Hub")
CONSOLE = ROOT / "tools" / "d8_total_field_console.sh"
REPORT_DIR = ROOT / "runtime" / "total_field" / "voice_operator"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def route(text: str) -> list[str]:
    t = normalize(text)
    if any(k in t for k in ["狀態", "status", "總場狀態"]):
        return ["status"]
    if any(k in t for k in ["檢查", "doctor", "健康"]):
        return ["doctor"]
    if any(k in t for k in ["告警", "alert", "alerts", "示警"]):
        return ["alerts", "--limit", "20"]
    if any(k in t for k in ["紅隊", "redteam", "錯誤"]):
        return ["redteam", "--limit", "20"]
    if any(k in t for k in ["評估", "eval", "evals", "guard"]):
        return ["evals", "--limit", "20"]
    if any(k in t for k in ["封存", "seal"]):
        return ["seal"]
    if any(k in t for k in ["安全讀取", "safe read", "readonly"]):
        return [
            "preflight",
            "--task-name", "SAFE_TOTAL_FIELD_STATUS_READ",
            "--mode", "sandbox",
            "--scope-json", '{"readonly":true,"target":"d8_total_field_current_status"}',
        ]
    return ["help"]


def run_console(args: list[str]) -> dict:
    proc = subprocess.run(
        [str(CONSOLE)] + args,
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=60,
    )
    return {
        "args": ["tools/d8_total_field_console.sh"] + args,
        "returncode": proc.returncode,
        "output": proc.stdout,
    }


def handle(text: str, dry_run: bool = False) -> dict:
    args = route(text)
    result = {
        "state": "DRY_RUN" if dry_run else "EXECUTED",
        "input_text": text,
        "routed_args": args,
        "raw_audio_saved": False,
        "external_api_call": False,
        "production_db_write": False,
        "deploy": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if not dry_run:
        result["console_result"] = run_console(args)
    report = REPORT_DIR / f"D8_VOICE_OPERATOR_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result["report"] = report.relative_to(ROOT).as_posix()
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text")
    ap.add_argument("--interactive", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.interactive:
        print("STATE=PASS_D8_VOICE_OPERATOR_INTERACTIVE_READY")
        while True:
            try:
                s = input("D8> ")
            except EOFError:
                break
            if normalize(s) in ("exit", "quit", "q", "離開"):
                break
            print(json.dumps(handle(s, args.dry_run), ensure_ascii=False, indent=2))
    else:
        if not args.text:
            raise SystemExit("--text or --interactive required")
        print(json.dumps(handle(args.text, args.dry_run), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
