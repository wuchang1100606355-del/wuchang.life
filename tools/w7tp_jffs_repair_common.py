#!/usr/bin/env python3
"""Shared helpers for the local-only W7TP JFFS health repair suite."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


ROUTER_CAPACITY_GUARD = {
    "required_before_execution": True,
    "status": "HOLD_USB_STORAGE_ERRORS_DETECTED",
    "jffs_repair_prerequisite": "USB_REPAIR_MUST_COMPLETE_BEFORE_JFFS_REPAIR",
}

SEALED_PACKET_REFS = [
    "af7d186 router USB dead-letter mailbox governance",
    "a5fde27 member sovereignty + AI quality gates",
]

BASE_SAFETY_FLAGS = {
    "router_write": False,
    "jffs_write": False,
    "usb_write": False,
    "router_config_write": False,
    "deploy": False,
    "restart": False,
    "reboot": False,
    "db_write": False,
    "ssh": False,
    "secret_read": False,
    "env_read": False,
    "member_plaintext_read": False,
    "privilege_escalation": False,
    "scrub_executed": False,
}

JFFS_LOG_PATTERNS = {
    "jffs_error": re.compile(r"\bjffs2?\b.*\b(error|warning|corrupt|crc|fail|failed)\b", re.I),
    "jffs_no_space": re.compile(r"\b(no space left|enospc|write.*no space)\b", re.I),
    "jffs_readonly": re.compile(r"\b(read-only file system|remount-ro|readonly)\b", re.I),
    "jffs_erase": re.compile(r"\bjffs2?\b.*\b(erase|eraseblock|cleanmarker|summary)\b", re.I),
    "jffs_mount": re.compile(r"\bjffs2?\b.*\b(mount|mounted|unmount|remount)\b", re.I),
    "mtd_error": re.compile(r"\b(mtd|nand|flash)\b.*\b(error|bad block|ecc|erase failed|write failed)\b", re.I),
}

TEMP_PATTERN = re.compile(r"(?<![A-Za-z0-9])([0-9]{2,3}(?:\.[0-9]+)?)\s*(?:C|c|\u00b0C|\u00b0c)?")
DF_PERCENT_PATTERN = re.compile(r"(?<![0-9])([0-9]{1,3})%")


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def truncate_text(value: str, limit: int = 200000) -> str:
    if limit <= 0 or len(value) <= limit:
        return value
    return value[:limit] + "\n...[truncated]..."


def run_cmd(cmd: list[str], timeout: int = 20, stdout_limit: int = 200000, stderr_limit: int = 20000) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            shell=False,
        )
        return {
            "command": cmd,
            "returncode": completed.returncode,
            "stdout": truncate_text(completed.stdout, stdout_limit),
            "stderr": truncate_text(completed.stderr, stderr_limit),
            "available": True,
            "timed_out": False,
        }
    except FileNotFoundError as exc:
        return {
            "command": cmd,
            "returncode": 127,
            "stdout": "",
            "stderr": str(exc),
            "available": False,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": cmd,
            "returncode": 124,
            "stdout": truncate_text(exc.stdout or "", stdout_limit),
            "stderr": truncate_text(exc.stderr or "", stderr_limit),
            "available": True,
            "timed_out": True,
        }


def base_result(tool: str, state: str) -> dict[str, Any]:
    return {
        "STATE": state,
        "tool": tool,
        "run_at_utc": utc_now(),
        "scope": "LOCAL_ONLY_ANALYSIS_NO_ROUTER_TOUCH",
        "router_capacity_guard": dict(ROUTER_CAPACITY_GUARD),
        "sealed_packets_not_modified": list(SEALED_PACKET_REFS),
        "safety_flags": dict(BASE_SAFETY_FLAGS),
    }


def print_json(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if str(payload.get("STATE", "")).startswith("PASS_") else 1


def read_text_limited(path: str, limit: int = 500000) -> tuple[str, bool]:
    with open(path, "rb") as handle:
        data = handle.read(limit + 1)
    truncated = len(data) > limit
    if truncated:
        data = data[:limit]
    return data.decode("utf-8", errors="replace"), truncated


def read_json_file(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_text_inputs(paths: list[str] | None, limit: int = 500000) -> tuple[str, list[dict[str, Any]]]:
    chunks: list[str] = []
    sources: list[dict[str, Any]] = []
    for path in paths or []:
        text, truncated = read_text_limited(path, limit)
        chunks.append(text)
        sources.append({"path": path, "truncated": truncated})
    return "\n".join(chunks), sources


def parse_jffs_df(text: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        lowered = line.lower()
        if "jffs" not in lowered and "/jffs" not in lowered:
            continue
        use_percent = None
        match = DF_PERCENT_PATTERN.search(line)
        if match:
            try:
                use_percent = int(match.group(1))
            except ValueError:
                use_percent = None
        rows.append({"line": truncate_text(line, 500), "use_percent": use_percent})
    max_use = max((row["use_percent"] for row in rows if row["use_percent"] is not None), default=None)
    return {
        "jffs_detected": bool(rows),
        "rows": rows,
        "max_use_percent": max_use,
        "free_space_low": max_use is not None and max_use >= 90,
    }


def analyze_jffs_log(text: str, sample_limit: int = 30) -> dict[str, Any]:
    counts = {name: 0 for name in JFFS_LOG_PATTERNS}
    samples: list[dict[str, Any]] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        matched = []
        for name, pattern in JFFS_LOG_PATTERNS.items():
            if pattern.search(line):
                counts[name] += 1
                matched.append(name)
        if matched and len(samples) < sample_limit:
            samples.append({"line_number": idx, "patterns": matched, "text": truncate_text(line, 500)})
    total_hits = sum(counts.values())
    return {
        "line_count": len(text.splitlines()),
        "counts": counts,
        "total_hits": total_hits,
        "jffs_errors_detected": total_hits > 0,
        "sample_lines": samples,
    }


def analyze_write_pressure(text: str) -> dict[str, Any]:
    lowered = text.lower()
    indicators = {
        "jffs_writable_true": "jffs_writable=true" in lowered,
        "jffs_writable_false": "jffs_writable=false" in lowered,
        "no_space": bool(re.search(r"no space left|not enough space|enospc|100%|9[0-9]%", lowered)),
        "readonly": bool(re.search(r"read-only|remount-ro|readonly", lowered)),
        "log_rotation": bool(re.search(r"logrotate|\.log-1|syslog\.log|security.*log", lowered)),
        "db_on_jffs": bool(re.search(r"/jffs/.*\.(db|sqlite|sqlite3)\b", lowered)),
        "dead_letter_on_jffs": "jffs_only" in lowered or re.search(r"/jffs/.*dead.?letter", lowered) is not None,
        "mtd_or_flash_write_error": bool(re.search(r"\b(mtd|nand|flash)\b.*\b(write failed|erase failed|bad block|ecc)\b", lowered)),
    }
    score = 0
    if indicators["jffs_writable_false"]:
        score += 15
    if indicators["no_space"]:
        score += 35
    if indicators["readonly"]:
        score += 35
    if indicators["log_rotation"]:
        score += 15
    if indicators["db_on_jffs"]:
        score += 25
    if indicators["dead_letter_on_jffs"]:
        score += 40
    if indicators["mtd_or_flash_write_error"]:
        score += 35
    pressure = "high" if score >= 50 else "medium" if score >= 25 else "low"
    return {"score": score, "pressure": pressure, "indicators": indicators}


def collect_temperatures(text: str) -> list[float]:
    values: list[float] = []
    relevant_lines = [
        line
        for line in text.splitlines()
        if re.search(r"temp|thermal|cpu|soc|acpi|fan|heat", line, re.I)
    ]
    for line in relevant_lines:
        for match in TEMP_PATTERN.finditer(line):
            try:
                value = float(match.group(1))
            except ValueError:
                continue
            if 20.0 <= value <= 130.0:
                values.append(value)
    return values


def walk_json(obj: Any) -> list[tuple[str, Any]]:
    out: list[tuple[str, Any]] = []

    def _walk(value: Any, path: str) -> None:
        out.append((path, value))
        if isinstance(value, dict):
            for key, child in value.items():
                _walk(child, f"{path}.{key}")
        elif isinstance(value, list):
            for idx, child in enumerate(value):
                _walk(child, f"{path}[{idx}]")

    _walk(obj, "$")
    return out


def bool_seen(payloads: list[Any], key_name: str, expected: bool) -> bool:
    for payload in payloads:
        for path, value in walk_json(payload):
            if path.rsplit(".", 1)[-1] == key_name and value is expected:
                return True
    return False


def max_numeric_key(payloads: list[Any], key_name: str) -> float | None:
    values: list[float] = []
    for payload in payloads:
        for path, value in walk_json(payload):
            if path.rsplit(".", 1)[-1] == key_name and isinstance(value, (int, float)):
                values.append(float(value))
    return max(values) if values else None


def valid_local_file(path: str | None) -> bool:
    if not path or "\x00" in path or ".." in Path(path).parts:
        return False
    try:
        return Path(path).is_file()
    except OSError:
        return False


def image_magic_summary(path: str, sample_bytes: int = 1048576) -> dict[str, Any]:
    image = Path(path)
    size = image.stat().st_size
    with image.open("rb") as handle:
        head = handle.read(min(sample_bytes, size))
        if size > sample_bytes:
            handle.seek(max(0, size - sample_bytes))
            tail = handle.read(sample_bytes)
        else:
            tail = b""
    combined = head + tail
    le_magic = combined.count(b"\x85\x19")
    be_magic = combined.count(b"\x19\x85")
    ff_ratio = combined.count(b"\xff") / len(combined) if combined else 0.0
    zero_ratio = combined.count(b"\x00") / len(combined) if combined else 0.0
    return {
        "size_bytes": size,
        "sampled_bytes": len(combined),
        "jffs2_magic_little_endian_count": le_magic,
        "jffs2_magic_big_endian_count": be_magic,
        "ff_ratio": round(ff_ratio, 4),
        "zero_ratio": round(zero_ratio, 4),
        "possible_jffs2": le_magic > 0 or be_magic > 0,
        "empty_or_erased_like": size == 0 or ff_ratio > 0.95 or zero_ratio > 0.95,
    }
