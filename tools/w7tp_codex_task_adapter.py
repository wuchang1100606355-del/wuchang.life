#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build W7TP Codex task packets and Markdown tasks."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

SAFETY_FLAGS = {
    "SECRET_READ": False,
    "MEMBER_PLAINTEXT_READ": False,
    "RAW_AUDIO_SAVED": False,
    "DB_WRITE": False,
    "PAYMENT_CAPTURE": False,
    "SERVICE_RESTART": False,
    "DEPLOY": False,
    "PRODUCTION_RELEASE": False,
    "EXTERNAL_API_CALL": False,
    "MODEL_DOWNLOAD": False,
    "LLM_AUTHORITY": False,
    "CODEX_AUTHORITY": False,
    "AUTO_STAGE": False,
    "AUTO_COMMIT": False,
}

DEFAULT_FORBIDDEN_ACTIONS = [
    "git_add_dot",
    "auto_commit",
    "deploy",
    "service_restart",
    "secret_read",
    "member_plaintext_read",
    "db_write",
    "payment_capture",
]

DEFAULT_FORBIDDEN_FILES = [
    ".env",
    "**/.env",
    "**/*token*",
    "**/*secret*",
    "**/*private*key*",
    "data/internal_members/**",
    "Wuchang_Odoo_Core/**",
]

DEFAULT_REQUIRED_OUTPUTS = [
    "CODEX_RESULT_PACKET",
    "verify summary",
    "risk scan review",
    "exact stage plan",
    "commit plan",
]

DEFAULT_VERIFY_COMMANDS = [
    "python3 -m py_compile <changed python files>",
    "python3 <relevant verify script>",
]

DEFAULT_RISK_SCAN_COMMANDS = [
    "grep -RInE '<safety-pattern>' <exact files> || true",
]


def flatten(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        for item in value.split():
            if item and item not in result:
                result.append(item)
    return result


def work_id(title: str, intent: str) -> str:
    digest = hashlib.sha256(f"{title}\n{intent}\n{int(time.time())}".encode("utf-8")).hexdigest()[:12]
    return "codex_task_" + digest


def build_packet(
    title: str,
    intent: str,
    allowed_files: list[str],
    forbidden_files: list[str],
    required_outputs: list[str],
    verify_commands: list[str],
    risk_scan_commands: list[str],
) -> dict[str, Any]:
    return {
        "packet_type": "W7TP_CODEX_TASK_PACKET",
        "version": "v0.1",
        "codex_authority": False,
        "candidate_only": True,
        "work_id": work_id(title, intent),
        "title": title,
        "intent": intent,
        "allowed_files": allowed_files,
        "forbidden_files": forbidden_files,
        "required_outputs": required_outputs,
        "verify_commands": verify_commands,
        "risk_scan_commands": risk_scan_commands,
        "completion_state": "READY_FOR_REVIEW",
        "forbidden_actions": DEFAULT_FORBIDDEN_ACTIONS,
        "safety_flags": SAFETY_FLAGS,
    }


def bullets(values: list[str]) -> str:
    return "\n".join(f"- `{value}`" for value in values) if values else "- `(none)`"


def render_markdown(packet: dict[str, Any]) -> str:
    return f"""# W7TP Codex Task Packet

## Authority Boundary

- Codex 不是總場
- Codex is not Total Field authority
- candidate only
- `codex_authority=false`
- `candidate_only=true`

## Title

{packet["title"]}

## Intent

{packet["intent"]}

## CODEX_TASK_PACKET

```json
{json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True)}
```

## Allowed Files

{bullets(packet["allowed_files"])}

## Forbidden Files

{bullets(packet["forbidden_files"])}

## Safety Flags

```json
{json.dumps(packet["safety_flags"], ensure_ascii=False, indent=2, sort_keys=True)}
```

## Verify Commands

{bullets(packet["verify_commands"])}

## Risk Scan

{bullets(packet["risk_scan_commands"])}

## Forbidden Actions

{bullets(packet["forbidden_actions"])}

## Git Rules

- no git add .
- no auto commit
- no deploy
- exact stage plan only after review

## Final Response Format

```text
STATE=<PASS_OR_HOLD>
FILES_CHANGED:
- <exact file>
VERIFY:
- <command/result>
RISK_SCAN:
- reviewed; false positives marked when safety-policy text only
NEXT:
git diff -- <exact files>
then exact stage only
```
"""


def write_text(path_text: str, text: str) -> Path:
    path = (ROOT / path_text).resolve() if not Path(path_text).is_absolute() else Path(path_text)
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError("out path must be inside repo") from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def run_adapter(
    title: str,
    intent: str,
    allowed_files: list[str],
    out: str,
    forbidden_files: list[str] | None = None,
    required_outputs: list[str] | None = None,
    verify_commands: list[str] | None = None,
    risk_scan_commands: list[str] | None = None,
) -> dict[str, Any]:
    if not title.strip() or not intent.strip():
        raise ValueError("title and intent are required")
    allowed = flatten(allowed_files)
    if not allowed:
        raise ValueError("allowed files are required")
    packet = build_packet(
        title.strip(),
        intent.strip(),
        allowed,
        flatten(forbidden_files or DEFAULT_FORBIDDEN_FILES),
        flatten(required_outputs or DEFAULT_REQUIRED_OUTPUTS),
        flatten(verify_commands or DEFAULT_VERIFY_COMMANDS),
        flatten(risk_scan_commands or DEFAULT_RISK_SCAN_COMMANDS),
    )
    task_path = write_text(out, render_markdown(packet))
    return {
        "STATE": "PASS_W7TP_CODEX_TASK_ADAPTER",
        "CODEX_TASK_PACKET": packet,
        "TASK_FILE": str(task_path.relative_to(ROOT)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("--intent", required=True)
    parser.add_argument("--allowed-files", nargs="+", action="append", required=True)
    parser.add_argument("--forbidden-files", nargs="+", action="append", default=[])
    parser.add_argument("--required-outputs", nargs="+", action="append", default=[])
    parser.add_argument("--verify-commands", nargs="+", action="append", default=[])
    parser.add_argument("--risk-scan-commands", nargs="+", action="append", default=[])
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    try:
        result = run_adapter(
            args.title,
            args.intent,
            [item for group in args.allowed_files for item in group],
            args.out,
            [item for group in args.forbidden_files for item in group],
            [item for group in args.required_outputs for item in group] or None,
            [item for group in args.verify_commands for item in group] or None,
            [item for group in args.risk_scan_commands for item in group] or None,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except ValueError as exc:
        print(json.dumps({"STATE": "HOLD_W7TP_CODEX_TASK_ADAPTER", "ERROR": str(exc), "SAFETY_FLAGS": SAFETY_FLAGS}, ensure_ascii=False, indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
