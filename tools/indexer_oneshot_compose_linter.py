#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


DEFAULT = Path("configs/containers/wuchang_indexer_oneshot.compose.template.yml")

REQUIRED_PATTERNS = {
    "missing_service:wuchang_indexer_oneshot": r"(?m)^\s{2}wuchang_indexer_oneshot:\s*$",
    "missing_image:w7tp-indexer:latest": r"(?m)^\s+image:\s*w7tp-indexer:latest\s*$",
    "missing_command:python_-u_watcher.py": (
        r"(?m)^\s+command:\s*(?:python\s+-u\s+watcher\.py|"
        r"\[\s*[\"']python[\"']\s*,\s*[\"']-u[\"']\s*,\s*"
        r"[\"']watcher\.py[\"']\s*\])\s*$"
    ),
    "restart_must_be_no": r'(?m)^\s+restart:\s*"no"\s*$',
    "network_mode_must_be_none": r'(?m)^\s+network_mode:\s*"none"\s*$',
    "read_only_must_be_true": r"(?m)^\s+read_only:\s*true\s*$",
}

FORBIDDEN_PATTERNS = {
    "forbidden_compose_start": r"docker\s+compose\s+up",
    "forbidden_container_run": r"docker\s+run",
    "forbidden_restart_unless_stopped": r"(?m)^\s+restart:\s*[\"']?unless-stopped[\"']?\s*$",
    "forbidden_restart_always": r"(?m)^\s+restart:\s*[\"']?always[\"']?\s*$",
    "forbidden_host_network": r"(?m)^\s+network_mode:\s*[\"']?host[\"']?\s*$",
    "forbidden_privileged_mode": r"(?m)^\s+privileged:\s*true\s*$",
    "forbidden_root_mount": r"(?m)^\s*-\s*[\"']?/\s*:",
    "forbidden_env_mount": r"\.env",
    "forbidden_keys_mount": r"(?<![A-Za-z0-9_])keys(?![A-Za-z0-9_])",
    "forbidden_ssh_mount": r"\.ssh",
    "forbidden_private_key_mount": r"private_key",
    "forbidden_formal_db_mount": r"Taiji_Odoo/postgres_data",
    "forbidden_raw_member_data_mount": r"raw_member_data",
}


def lint_text(text: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for error, pattern in REQUIRED_PATTERNS.items():
        if re.search(pattern, text) is None:
            errors.append(error)

    for error, pattern in FORBIDDEN_PATTERNS.items():
        if re.search(pattern, text, flags=re.IGNORECASE):
            errors.append(error)

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the plan-only W7TP indexer one-shot compose template."
    )
    parser.add_argument("--file", default=str(DEFAULT))
    args = parser.parse_args()

    path = Path(args.file)
    try:
        text = path.read_text(encoding="utf-8")
        errors, warnings = lint_text(text)
    except OSError:
        errors = ["compose_template_unreadable"]
        warnings = []

    decision = "safe_plan_only" if not errors else "rejected"
    print(
        json.dumps(
            {
                "decision": decision,
                "file": str(path),
                "errors": errors,
                "warnings": warnings,
                "compose_start": False,
                "ssh": False,
                "restart": False,
                "container_move": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
