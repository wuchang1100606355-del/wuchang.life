#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Safe Git Stage

Stages only allowlisted canonical files and rejects runtime/data/secrets/noise.

No commit.
No git add .
No git add -A.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import json
import subprocess
from pathlib import Path
from typing import List, Tuple


ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = ROOT / "docs" / "project" / "git_stage_allowlist.txt"
REPORT_DIR = ROOT / "runtime" / "reports"

BLOCK_PATTERNS = [
    ".env",
    ".env.*",
    "keys/*",
    "*/keys/*",
    "*.key",
    "*.pem",
    "*.db",
    "*.sqlite",
    "data/*",
    "logs/*",
    "runtime/reports/*",
    "runtime/proofs/*",
    "runtime/merlin_*/*",
    "runtime/router_guard_dryrun/*",
    "runtime/patches/*",
    "open_webui_data/*",
    "*.tar.gz",
    "*.bak_*",
    "*password*",
    "*secret*",
    "*token*",
    "*private_key*",
]


def run(cmd: List[str]) -> Tuple[int, str]:
    p = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.strip()


def read_allowlist() -> List[str]:
    if not ALLOWLIST.exists():
        return []
    out = []
    for line in ALLOWLIST.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out.append(s)
    return out


def changed_files() -> List[str]:
    rc, out = run(["git", "status", "--short"])
    files = []
    for line in out.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.append(path)
    return files


def is_blocked(path: str) -> bool:
    return any(fnmatch.fnmatch(path, pat) or path.startswith(pat.rstrip("*")) for pat in BLOCK_PATTERNS)


def is_allowed(path: str, allow: List[str]) -> bool:
    for pat in allow:
        if pat.endswith("/"):
            if path.startswith(pat):
                return True
        elif fnmatch.fnmatch(path, pat):
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--stage", action="store_true")
    ap.add_argument("paths", nargs="*")
    args = ap.parse_args()

    allow = read_allowlist()
    candidates = args.paths if args.paths else changed_files()

    allowed, blocked, rejected = [], [], []
    for p in candidates:
        if is_blocked(p):
            blocked.append(p)
        elif is_allowed(p, allow):
            allowed.append(p)
        else:
            rejected.append(p)

    stage_rc = None
    stage_out = ""
    if args.stage and allowed:
        stage_rc, stage_out = run(["git", "add", "--"] + allowed)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"safe_git_stage_{ts}.md"

    report = {
        "tool": "safe_git_stage",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "dry_run": args.dry_run,
        "stage": args.stage,
        "allowlist": allow,
        "allowed": allowed,
        "blocked": blocked,
        "rejected_not_allowlisted": rejected,
        "stage_rc": stage_rc,
        "stage_out": stage_out,
        "commit": False,
    }

    lines = [
        "# Safe Git Stage Report",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Dry run: `{args.dry_run}`",
        f"- Stage: `{args.stage}`",
        "- Commit: `false`",
        "",
        "## Allowed",
        *[f"- `{x}`" for x in allowed],
        "",
        "## Blocked",
        *[f"- `{x}`" for x in blocked],
        "",
        "## Rejected Not Allowlisted",
        *[f"- `{x}`" for x in rejected],
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "decision": "staged_allowlisted_files" if args.stage else "dry_run_preview",
        "allowed": allowed,
        "blocked": blocked,
        "rejected_not_allowlisted": rejected,
        "report": str(report_path),
        "commit": False,
    }, ensure_ascii=False, indent=2))

    if blocked:
        return 2
    if args.stage and stage_rc not in (None, 0):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
