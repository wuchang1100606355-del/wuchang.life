#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lint a W7TP USB dead-letter mailbox record.

This linter reads only the JSON file passed with --file. It does not read
environment variables, open network connections, use SSH, write databases, or
start containers.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


FORBIDDEN_KEYS = {
    "secret",
    "token",
    "refresh_token",
    "access_token",
    "client_secret",
    "private_key",
    "router_password",
    "member_plaintext",
    "raw_audio",
}

SECRET_VALUE_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\b(?:secret|token|password|bearer)\s*[:=]\s*\S+", re.IGNORECASE),
]


def walk(obj: Any, path: str = "$"):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield path, key, value
            yield from walk(value, "%s.%s" % (path, key))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            yield from walk(value, "%s[%s]" % (path, idx))


def find_bool(obj: Any, key_name: str, expected: bool) -> bool:
    target = key_name.lower()
    for _, key, value in walk(obj):
        if key.lower() == target and value is expected:
            return True
    return False


def lint(obj: Any, source: Path) -> dict:
    errors = []
    warnings = []

    if not isinstance(obj, dict):
        errors.append("root must be an object")
        obj = {}

    mailbox_backend = obj.get("mailbox_backend")
    if mailbox_backend != "usb":
        errors.append("mailbox_backend must be usb")
    if mailbox_backend == "jffs_only":
        errors.append("mailbox_backend=jffs_only is forbidden")

    if obj.get("cloud_authority") is True or find_bool(obj, "cloud_authority", True):
        errors.append("cloud_authority=true is forbidden")

    if find_bool(obj, "member_plaintext", True):
        errors.append("member_plaintext=true is forbidden")

    for path, key, value in walk(obj):
        lowered = key.lower()
        if lowered in FORBIDDEN_KEYS:
            errors.append("forbidden key at %s.%s" % (path, key))
        if isinstance(value, str):
            for pattern in SECRET_VALUE_PATTERNS:
                if pattern.search(value):
                    errors.append("secret-like value at %s.%s" % (path, key))
                    break

    flags = obj.get("safety_flags", {})
    if isinstance(flags, dict):
        expected = {
            "SECRET_READ": False,
            "ENV_DUMP": False,
            "MEMBER_PLAINTEXT_READ": False,
            "RAW_AUDIO_READ": False,
            "ROUTER_PASSWORD_SAVE": False,
            "USB_DEAD_LETTER_REQUIRED": True,
        }
        for key, value in expected.items():
            if flags.get(key) is not value:
                errors.append("safety_flags.%s must be %r" % (key, value))
    else:
        errors.append("safety_flags must be an object")

    if mailbox_backend == "usb" and not obj.get("mailbox_backend_path"):
        errors.append("mailbox_backend_path is required for usb mailbox")

    return {
        "decision": "PASS" if not errors else "HOLD",
        "file": str(source),
        "errors": errors,
        "warnings": warnings,
        "cloud_call": False,
        "ssh": False,
        "db_write": False,
        "secret_saved": False,
        "mailbox_backend": mailbox_backend,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    args = parser.parse_args(argv)

    source = Path(args.file)
    try:
        obj = json.loads(source.read_text(encoding="utf-8"))
    except Exception as exc:
        result = {
            "decision": "HOLD",
            "file": str(source),
            "errors": ["json read/parse failed: %s" % exc],
            "warnings": [],
            "cloud_call": False,
            "ssh": False,
            "db_write": False,
            "secret_saved": False,
            "mailbox_backend": None,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    result = lint(obj, source)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
