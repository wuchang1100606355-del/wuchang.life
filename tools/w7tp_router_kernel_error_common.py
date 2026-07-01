#!/usr/bin/env python3
"""Shared helpers for local-only router kernel error repair suite."""

from __future__ import annotations

import datetime as dt
import json
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
    "usb_write": False,
    "jffs_write": False,
    "router_config_write": False,
    "kernel_write": False,
    "network_write": False,
    "deploy": False,
    "restart": False,
    "reboot": False,
    "db_write": False,
    "ssh": False,
    "secret_read": False,
    "env_read": False,
    "member_plaintext_read": False,
    "privilege_escalation": False,
    "repair_executed": False,
}

USB_PATTERN = re.compile(r"\busb\b.*\b(error|reset|descriptor|disconnect|failed|timeout|over-current|uas)\b", re.I)
STORAGE_PATTERN = re.compile(
    r"\b(i/o error|buffer i/o error|blk_update_request|rejecting i/o|medium error|write failed|read failed|"
    r"ext4-fs error|fat-fs.*error|exfat.*error|read-only file system|remount-ro|bad block|ecc|mtd|nand|uas)\b",
    re.I,
)
NETWORK_PATTERN = re.compile(
    r"\b(netdev watchdog|link is down|link down|carrier lost|tx timeout|rx error|tx error|firmware crash|"
    r"deauth|disassoc|wlan|wifi|wireless|eth[0-9]*|br[0-9]*|wan|lan|phy|dhcp)\b.*"
    r"\b(error|fail|failed|timeout|down|reset|crash|lost|watchdog|drop|overflow)\b",
    re.I,
)
NETWORK_EVENT_PATTERN = re.compile(
    r"\b(eth[0-9]*|link down|link up|carrier lost|network unreachable|netdev watchdog|"
    r"wlan|wifi|wireless|br[0-9]*|wan|lan|phy|dhcp)\b",
    re.I,
)
SEVERE_PATTERN = re.compile(
    r"\b(kernel panic|oops|call trace|segfault|watchdog|hung task|read-only file system|"
    r"i/o error|bad block|ecc|thermal shutdown|reset super.*usb|netdev watchdog)\b",
    re.I,
)


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def truncate_text(value: str, limit: int = 200000) -> str:
    if limit <= 0 or len(value) <= limit:
        return value
    return value[:limit] + "\n...[truncated]..."


def redact_line(value: str) -> str:
    value = re.sub(r"\b([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b", "<MAC>", value)
    value = re.sub(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", "<IPV4>", value)
    return truncate_text(value, 800)


def run_cmd(cmd: list[str], timeout: int = 20, stdout_limit: int = 250000, stderr_limit: int = 20000) -> dict[str, Any]:
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
        "scope": "LOCAL_ONLY_KERNEL_ANALYSIS_NO_ROUTER_TOUCH",
        "router_capacity_guard": dict(ROUTER_CAPACITY_GUARD),
        "sealed_packets_not_modified": list(SEALED_PACKET_REFS),
        "safety_flags": dict(BASE_SAFETY_FLAGS),
    }


def print_json(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if str(payload.get("STATE", "")).startswith("PASS_") else 1


def read_text_limited(path: str, limit: int = 800000) -> tuple[str, bool]:
    with open(path, "rb") as handle:
        data = handle.read(limit + 1)
    truncated = len(data) > limit
    if truncated:
        data = data[:limit]
    return data.decode("utf-8", errors="replace"), truncated


def load_text_inputs(paths: list[str] | None, limit: int = 800000) -> tuple[str, list[dict[str, Any]]]:
    chunks: list[str] = []
    sources: list[dict[str, Any]] = []
    for path in paths or []:
        text, truncated = read_text_limited(path, limit)
        chunks.append(text)
        sources.append({"type": "file", "path": path, "truncated": truncated})
    return "\n".join(chunks), sources


def local_kernel_text(include_dmesg: bool, include_journal: bool, journal_lines: int) -> tuple[str, list[dict[str, Any]]]:
    chunks: list[str] = []
    sources: list[dict[str, Any]] = []
    if include_dmesg:
        dmesg = run_cmd(["dmesg"], stdout_limit=400000)
        chunks.append(dmesg.get("stdout", ""))
        sources.append({"type": "local_dmesg", "command": dmesg})
    if include_journal:
        journal = run_cmd(["journalctl", "-k", "-n", str(max(1, journal_lines)), "--no-pager"], stdout_limit=400000)
        chunks.append(journal.get("stdout", ""))
        sources.append({"type": "local_journalctl_kernel", "command": journal})
    return "\n".join(chunk for chunk in chunks if chunk), sources


def source_unavailable(sources: list[dict[str, Any]]) -> bool:
    if not sources:
        return True
    for source in sources:
        cmd = source.get("command")
        if isinstance(cmd, dict) and cmd.get("returncode") == 0 and cmd.get("stdout", "").strip():
            return False
        if source.get("type") == "file":
            return False
    return True


def analyze_lines(text: str, pattern: re.Pattern[str], category: str, sample_limit: int = 80) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    severe_count = 0
    for idx, line in enumerate(text.splitlines(), start=1):
        if not pattern.search(line):
            continue
        if SEVERE_PATTERN.search(line):
            severe_count += 1
        if len(matches) < sample_limit:
            matches.append({"line_number": idx, "text": redact_line(line), "severe": bool(SEVERE_PATTERN.search(line))})
    return {
        "category": category,
        "line_count": len(text.splitlines()),
        "error_count": len(matches) if len(matches) < sample_limit else sum(1 for line in text.splitlines() if pattern.search(line)),
        "sample_limit": sample_limit,
        "severe_count": severe_count,
        "errors_detected": bool(matches),
        "sample_lines": matches,
    }


def read_json_file(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


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


def collect_counts(payloads: list[Any]) -> dict[str, int]:
    counts = {"usb": 0, "storage": 0, "network": 0, "severe": 0}
    for payload in payloads:
        if isinstance(payload, dict):
            direct_counts = payload.get("counts")
            if isinstance(direct_counts, dict):
                for key in counts:
                    value = direct_counts.get(key)
                    if isinstance(value, int):
                        counts[key] += value
            category = payload.get("category")
            error_count = payload.get("error_count")
            severe_count = payload.get("severe_count")
            if isinstance(category, str) and category in {"usb", "storage", "network"} and isinstance(error_count, int):
                counts[category] += error_count
            if isinstance(severe_count, int):
                counts["severe"] += severe_count
        for path, value in walk_json(payload):
            leaf = path.rsplit(".", 1)[-1]
            if isinstance(value, int):
                if leaf in {"usb_error_count"}:
                    counts["usb"] += value
                elif leaf in {"storage_error_count"}:
                    counts["storage"] += value
                elif leaf in {"network_error_count"}:
                    counts["network"] += value
                elif leaf in {"severe_count"}:
                    counts["severe"] += value
            if leaf == "category" and isinstance(value, str) and value in counts:
                pass
    return counts


def classify_severity(counts: dict[str, int]) -> dict[str, Any]:
    score = counts["usb"] * 10 + counts["storage"] * 15 + counts["network"] * 8 + counts["severe"] * 25
    reasons: list[str] = []
    if counts["storage"]:
        reasons.append("kernel storage errors detected")
    if counts["usb"]:
        reasons.append("kernel USB errors detected")
    if counts["network"]:
        reasons.append("kernel network errors detected")
    if counts["severe"]:
        reasons.append("severe kernel markers detected")
    if score >= 80 or counts["storage"] >= 3 or counts["severe"] >= 2:
        severity = "critical"
    elif score >= 40 or counts["storage"] or counts["usb"] >= 3:
        severity = "high"
    elif score >= 15:
        severity = "medium"
    else:
        severity = "low"
    return {"score": score, "severity": severity, "reasons": reasons}


def load_reports(paths: list[str] | None) -> tuple[list[Any], list[dict[str, Any]]]:
    payloads: list[Any] = []
    sources: list[dict[str, Any]] = []
    for path in paths or []:
        payloads.append(read_json_file(path))
        sources.append({"path": path})
    return payloads, sources
