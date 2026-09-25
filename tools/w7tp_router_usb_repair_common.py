#!/usr/bin/env python3
"""Shared helpers for the local-only W7TP router USB repair suite."""

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
}

SEALED_PACKET_REFS = [
    "af7d186 router USB dead-letter mailbox governance",
    "a5fde27 member sovereignty + AI quality gates",
]

BASE_SAFETY_FLAGS = {
    "router_write": False,
    "usb_write": False,
    "jffs_write": False,
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
}

KERNEL_ERROR_PATTERNS = {
    "io_error": re.compile(r"\b(i/o error|buffer i/o error|blk_update_request|rejecting i/o)\b", re.I),
    "usb_reset": re.compile(r"\b(reset|resetting)\b.*\busb\b|\busb\b.*\b(reset|resetting)\b", re.I),
    "usb_disconnect": re.compile(r"\busb\b.*\b(disconnect|device not accepting address|device descriptor read)\b", re.I),
    "uas_error": re.compile(r"\b(uas|uas_eh_abort_handler|uas_eh_device_reset_handler)\b", re.I),
    "filesystem_error": re.compile(r"\b(ext4-fs error|fat-fs.*error|exfat.*error|read-only file system)\b", re.I),
    "storage_timeout": re.compile(r"\b(timeout|timed out|abort command|failed command|medium error)\b", re.I),
}


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
    except PermissionError as exc:
        return {
            "command": cmd,
            "returncode": 126,
            "stdout": "",
            "stderr": str(exc),
            "available": True,
            "timed_out": False,
        }


def base_result(tool: str, state: str, *, usb_write: bool = False) -> dict[str, Any]:
    safety = dict(BASE_SAFETY_FLAGS)
    safety["usb_write"] = bool(usb_write)
    return {
        "STATE": state,
        "tool": tool,
        "run_at_utc": utc_now(),
        "scope": "LOCAL_ONLY_NO_ROUTER_TOUCH",
        "router_capacity_guard": dict(ROUTER_CAPACITY_GUARD),
        "sealed_packets_not_modified": list(SEALED_PACKET_REFS),
        "safety_flags": safety,
    }


def print_json(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if str(payload.get("STATE", "")).startswith("PASS_") else 1


def parse_json_maybe(text: str) -> Any | None:
    if not text.strip():
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def read_json_file(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_text_limited(path: str, limit: int = 500000) -> tuple[str, bool]:
    with open(path, "rb") as handle:
        data = handle.read(limit + 1)
    truncated = len(data) > limit
    if truncated:
        data = data[:limit]
    return data.decode("utf-8", errors="replace"), truncated


def valid_device_path(value: str | None) -> bool:
    if not value:
        return False
    if ".." in value:
        return False
    if not value.startswith("/dev/"):
        return False
    return bool(re.fullmatch(r"/dev/[A-Za-z0-9._/\-]+", value))


def find_mounts_for_device(device: str) -> dict[str, Any]:
    direct = run_cmd(["findmnt", "-nr", "--source", device, "-o", "TARGET,OPTIONS,FSTYPE"], stdout_limit=50000)
    lsblk = run_cmd(["lsblk", "-J", "-o", "NAME,PATH,TYPE,FSTYPE,MOUNTPOINT,MOUNTPOINTS", device], stdout_limit=100000)
    return {
        "device": device,
        "findmnt": direct,
        "lsblk": lsblk,
        "mounted": bool(direct.get("stdout", "").strip()),
    }


def analyze_kernel_log(text: str, sample_limit: int = 25) -> dict[str, Any]:
    counts = {name: 0 for name in KERNEL_ERROR_PATTERNS}
    samples: list[dict[str, Any]] = []
    lines = text.splitlines()
    for idx, line in enumerate(lines, start=1):
        matched = []
        for name, pattern in KERNEL_ERROR_PATTERNS.items():
            if pattern.search(line):
                counts[name] += 1
                matched.append(name)
        if matched and len(samples) < sample_limit:
            samples.append(
                {
                    "line_number": idx,
                    "patterns": matched,
                    "text": truncate_text(line, 500),
                }
            )
    total_hits = sum(counts.values())
    return {
        "line_count": len(lines),
        "counts": counts,
        "total_hits": total_hits,
        "usb_errors_detected": total_hits > 0,
        "sample_lines": samples,
    }


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


def smart_passed_from_payload(payload: Any) -> bool | None:
    if not isinstance(payload, dict):
        return None
    smart_status = payload.get("smart_status")
    if isinstance(smart_status, dict) and isinstance(smart_status.get("passed"), bool):
        return smart_status["passed"]
    for path, value in walk_json(payload):
        if path.endswith(".smart_status.passed") and isinstance(value, bool):
            return value
    return None


def collect_temperature_values(payload: Any) -> list[float]:
    temps: list[float] = []
    for path, value in walk_json(payload):
        key = path.rsplit(".", 1)[-1].lower()
        if isinstance(value, (int, float)) and (
            key.endswith("_input")
            or key in {"temp", "temperature", "temperature_c", "current"}
            or "temperature" in path.lower()
        ):
            val = float(value)
            if val > 1000:
                val = val / 1000.0
            if -50.0 <= val <= 150.0:
                temps.append(val)
    return temps


def sysfs_thermal_readings() -> list[dict[str, Any]]:
    readings: list[dict[str, Any]] = []
    base = Path("/sys/class/thermal")
    if not base.exists():
        return readings
    for temp_path in sorted(base.glob("thermal_zone*/temp")):
        try:
            raw = temp_path.read_text(encoding="utf-8").strip()
            value = float(raw)
            if value > 1000:
                value = value / 1000.0
            type_path = temp_path.with_name("type")
            zone_type = type_path.read_text(encoding="utf-8").strip() if type_path.exists() else temp_path.parent.name
            readings.append({"source": str(temp_path), "type": zone_type, "temperature_c": value})
        except (OSError, ValueError):
            continue
    return readings


def file_exists(path: str) -> bool:
    try:
        return os.path.exists(path)
    except OSError:
        return False
