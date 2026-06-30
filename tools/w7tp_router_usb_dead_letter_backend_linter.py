#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lint a W7TP router USB dead-letter backend status record.

This linter reads only the JSON file passed with --file. It does not read
environment variables, use SSH, call cloud services, write databases, or start
containers.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SECRET_KEYS = {
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

AVAILABLE_DECISIONS = {
    "USB_MAILBOX_OK",
    "USB_MAILBOX_OK_JFFS_POINTER_OK",
    "USB_MAILBOX_OK_JFFS_DEGRADED",
}

HOLD_DECISIONS = {
    "HOLD_USB_DEAD_LETTER_BACKEND_UNAVAILABLE",
    "HOLD_NO_SAFE_BACKEND",
    "HOLD_SECRET_PATTERN_DETECTED",
    "HOLD_ROUTER_AUTHORITY_NOT_VERIFIED",
}

ALL_DECISIONS = AVAILABLE_DECISIONS | HOLD_DECISIONS


def walk(obj: Any, path: str = "$"):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield path, key, value
            yield from walk(value, "%s.%s" % (path, key))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            yield from walk(value, "%s[%s]" % (path, idx))


def lint(obj: Any, source: Path) -> dict:
    errors = []
    warnings = []

    if not isinstance(obj, dict):
        errors.append("root must be an object")
        obj = {}

    backend_decision = obj.get("backend_decision")
    if backend_decision not in ALL_DECISIONS:
        errors.append("backend_decision invalid")

    usb_dlm = obj.get("usb_dead_letter_status", {})
    jffs = obj.get("jffs_status", {})
    if not isinstance(usb_dlm, dict):
        errors.append("usb_dead_letter_status must be an object")
        usb_dlm = {}
    if not isinstance(jffs, dict):
        errors.append("jffs_status must be an object")
        jffs = {}

    usb_required = usb_dlm.get("required")
    usb_healthy = usb_dlm.get("healthy")
    jffs_healthy = jffs.get("healthy")
    jffs_degraded = jffs.get("degraded")
    mailbox_path = usb_dlm.get("mailbox_path")

    if usb_required is True and usb_healthy is False:
        if backend_decision not in {
            "HOLD_USB_DEAD_LETTER_BACKEND_UNAVAILABLE",
            "HOLD_NO_SAFE_BACKEND",
        }:
            errors.append("unhealthy required USB mailbox must HOLD")

    if usb_healthy is True and jffs_healthy is True:
        if backend_decision != "USB_MAILBOX_OK_JFFS_POINTER_OK":
            errors.append("USB healthy and JFFS healthy requires USB_MAILBOX_OK_JFFS_POINTER_OK")

    if usb_healthy is True and jffs_degraded is True:
        if backend_decision != "USB_MAILBOX_OK_JFFS_DEGRADED":
            errors.append("USB healthy and JFFS degraded requires USB_MAILBOX_OK_JFFS_DEGRADED")

    if backend_decision in AVAILABLE_DECISIONS and not mailbox_path:
        errors.append("available backend_decision requires non-empty mailbox_path")

    if jffs.get("role") != "pointer_status_only":
        errors.append("jffs_status.role must be pointer_status_only")

    flags = obj.get("safety_flags", {})
    if isinstance(flags, dict):
        expected = {
            "SECRET_READ": False,
            "ENV_DUMP": False,
            "MEMBER_PLAINTEXT_READ": False,
            "RAW_AUDIO_READ": False,
            "ROUTER_PASSWORD_SAVE": False,
            "USB_DEAD_LETTER_REQUIRED": True,
            "JFFS_POINTER_OR_STATUS_ONLY": True,
        }
        for key, value in expected.items():
            if flags.get(key) is not value:
                errors.append("safety_flags.%s must be %r" % (key, value))
    else:
        errors.append("safety_flags must be an object")

    for path, key, value in walk(obj):
        lowered = key.lower()
        if lowered in SECRET_KEYS:
            errors.append("forbidden key at %s.%s" % (path, key))
        if isinstance(value, str):
            for pattern in SECRET_VALUE_PATTERNS:
                if pattern.search(value):
                    errors.append("secret-like value at %s.%s" % (path, key))
                    break

    return {
        "decision": "PASS" if not errors else "HOLD",
        "file": str(source),
        "errors": errors,
        "warnings": warnings,
        "cloud_call": False,
        "ssh": False,
        "db_write": False,
        "secret_saved": False,
        "backend_decision": backend_decision,
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
            "backend_decision": None,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    result = lint(obj, source)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
