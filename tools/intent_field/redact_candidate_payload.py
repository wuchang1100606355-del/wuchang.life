#!/usr/bin/env python3
"""Redact or hold cloud-candidate payloads before any external use."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


HARD_RISK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("secret_assignment", re.compile(r"(?i)\b(secret|api[_-]?key|access[_-]?key)\s*[:=]\s*['\"]?[^'\"\s]{8,}")),
    ("credential_assignment", re.compile(r"(?i)\b(pass(?:word)?|credential)\s*[:=]\s*['\"]?[^'\"\s]{8,}")),
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("oauth_secret_assignment", re.compile(r"(?i)\boauth[_-]?secret\s*[:=]\s*['\"]?[^'\"\s]{8,}")),
    ("database_url", re.compile(r"(?i)\b(?:postgres|postgresql|mysql|mongodb|redis)://[^\s\"']+")),
    ("taiwan_id_like", re.compile(r"\b[A-Z][12]\d{8}\b")),
    ("phone_like", re.compile(r"\b09\d{2}[- ]?\d{3}[- ]?\d{3}\b")),
)


def scan_text(text: str) -> dict[str, Any]:
    risks: list[dict[str, Any]] = []
    redacted = text
    for label, pattern in HARD_RISK_PATTERNS:
        matches = list(pattern.finditer(text))
        if not matches:
            continue
        risks.append({"risk_type": label, "count": len(matches)})
        redacted = pattern.sub(f"[REDACTED:{label}]", redacted)
    return {
        "status": "HOLD" if risks else "PASS",
        "hard_risk_count": sum(item["count"] for item in risks),
        "risk_labels": risks,
        "redacted_text": redacted,
    }


def scan_jsonable(payload: Any) -> dict[str, Any]:
    return scan_text(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description="Redact or hold candidate payloads.")
    parser.add_argument("input", nargs="?", help="Input file. Reads stdin when omitted.")
    parser.add_argument("--output", help="Write scan result JSON to this path.")
    parser.add_argument("--redacted-output", help="Write redacted text to this path when provided.")
    args = parser.parse_args()

    if args.input:
        text = Path(args.input).read_text(encoding="utf-8", errors="ignore")
    else:
        text = sys.stdin.read()

    result = scan_text(text)
    public_result = {k: v for k, v in result.items() if k != "redacted_text"}

    if args.output:
        Path(args.output).write_text(json.dumps(public_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.redacted_output:
        Path(args.redacted_output).write_text(result["redacted_text"], encoding="utf-8")

    print(json.dumps(public_result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
