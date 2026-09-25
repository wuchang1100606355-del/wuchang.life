#!/usr/bin/env python3
"""Shared helpers for local-only router thermal stabilization tools."""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any


THERMAL_DOWNPRESSURE_C = 78.0
THERMAL_HIGH_C = 65.0

ROUTER_CAPACITY_GUARD = {
    "required_before_execution": True,
    "status": "HOLD_USB_STORAGE_ERRORS_DETECTED",
    "thermal_downpressure_threshold_c": THERMAL_DOWNPRESSURE_C,
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
    "deploy": False,
    "restart": False,
    "reboot": False,
    "db_write": False,
    "ssh": False,
    "secret_read": False,
    "env_read": False,
    "member_plaintext_read": False,
    "privilege_escalation": False,
    "thermal_control_write": False,
}

TEMP_PATTERN = re.compile(r"([+-]?[0-9]{2,3}(?:\.[0-9]+)?)\s*(?:C|c|\u00b0C|\u00b0c)?")
RELEVANT_TEMP_LINE = re.compile(
    r"temp|thermal|heat|cpu|soc|core|package|radio|wifi|wlan|fan|zone|dmu",
    re.I,
)
THROTTLE_PATTERN = re.compile(
    r"throttl|thermal trip|overheat|over temperature|freq.*cap|cpu.*cap|thermal.*limit|thermal.*shutdown",
    re.I,
)


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
        "scope": "LOCAL_ONLY_THERMAL_ANALYSIS_NO_ROUTER_TOUCH",
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


def load_text_inputs(paths: list[str] | None, limit: int = 500000) -> tuple[str, list[dict[str, Any]]]:
    chunks: list[str] = []
    sources: list[dict[str, Any]] = []
    for path in paths or []:
        text, truncated = read_text_limited(path, limit)
        chunks.append(text)
        sources.append({"path": path, "truncated": truncated})
    return "\n".join(chunks), sources


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


def collect_temperature_readings_from_text(text: str, source: str) -> list[dict[str, Any]]:
    readings: list[dict[str, Any]] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        if not RELEVANT_TEMP_LINE.search(line):
            continue
        for match in TEMP_PATTERN.finditer(line):
            prefix = line[: match.start()].lower()
            if re.search(r"(high|crit|max)\s*=\s*$", prefix):
                continue
            try:
                value = float(match.group(1))
            except ValueError:
                continue
            if 15.0 <= value <= 130.0:
                readings.append(
                    {
                        "source": source,
                        "line_number": idx,
                        "label": truncate_text(line.strip(), 240),
                        "temperature_c": value,
                    }
                )
    return readings


def collect_temperature_readings_from_json(payload: Any, source: str) -> list[dict[str, Any]]:
    readings: list[dict[str, Any]] = []
    for path, value in walk_json(payload):
        key = path.rsplit(".", 1)[-1].lower()
        if not isinstance(value, (int, float)):
            continue
        if not (
            key.endswith("_input")
            or key in {"temp", "temperature", "temperature_c", "current", "max_temperature_c"}
            or "temperature" in path.lower()
        ):
            continue
        temp = float(value)
        if temp > 1000:
            temp = temp / 1000.0
        if 15.0 <= temp <= 130.0:
            readings.append({"source": source, "path": path, "label": path, "temperature_c": temp})
    return readings


def local_sensor_snapshot(skip_sensors: bool = False) -> dict[str, Any]:
    raw = {"stdout": "", "returncode": None}
    json_cmd = {"stdout": "", "returncode": None}
    json_payload = None
    readings: list[dict[str, Any]] = []
    if not skip_sensors:
        raw = run_cmd(["sensors"], stdout_limit=300000)
        json_cmd = run_cmd(["sensors", "-j"], stdout_limit=300000)
        readings.extend(collect_temperature_readings_from_text(raw.get("stdout", ""), "local_sensors_raw"))
        try:
            json_payload = json.loads(json_cmd.get("stdout", "")) if json_cmd.get("stdout", "").strip() else None
        except json.JSONDecodeError:
            json_payload = None
        if json_payload is not None:
            readings.extend(collect_temperature_readings_from_json(json_payload, "local_sensors_json"))
    return {
        "sensors_raw_command": raw,
        "sensors_json_command": json_cmd,
        "sensors_json": json_payload,
        "thermal_raw": raw.get("stdout", ""),
        "readings": readings,
    }


def summarize_temperatures(readings: list[dict[str, Any]]) -> dict[str, Any]:
    values = [float(item["temperature_c"]) for item in readings]
    max_temp = max(values) if values else None
    avg_temp = round(sum(values) / len(values), 2) if values else None
    hotspot = None
    if readings:
        hotspot = max(readings, key=lambda item: float(item["temperature_c"]))
    return {
        "count": len(readings),
        "max_temperature_c": max_temp,
        "avg_temperature_c": avg_temp,
        "hotspot": hotspot,
        "thermal_downpressure_required": max_temp is not None and max_temp >= THERMAL_DOWNPRESSURE_C,
        "thermal_high": max_temp is not None and max_temp >= THERMAL_HIGH_C,
    }


def state_from_temperature(pass_state: str, max_temp: float | None) -> str:
    if max_temp is not None and max_temp >= THERMAL_DOWNPRESSURE_C:
        return "HOLD_ROUTER_THERMAL_DOWNPRESSURE_REQUIRED"
    if max_temp is not None and max_temp >= THERMAL_HIGH_C:
        return "HOLD_ROUTER_THERMAL_HIGH"
    return pass_state


def detect_throttle(text: str) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        if THROTTLE_PATTERN.search(line):
            matches.append({"line_number": idx, "text": truncate_text(line.strip(), 500)})
    return {"throttle_detected": bool(matches), "match_count": len(matches), "matches": matches[:40]}


def risk_score(summary: dict[str, Any], throttle_detected: bool = False) -> dict[str, Any]:
    max_temp = summary.get("max_temperature_c")
    score = 0
    reasons: list[str] = []
    if max_temp is not None and max_temp >= THERMAL_DOWNPRESSURE_C:
        score += 60
        reasons.append("max temperature at or above 78C downpressure threshold")
    elif max_temp is not None and max_temp >= THERMAL_HIGH_C:
        score += 35
        reasons.append("max temperature above high threshold")
    if throttle_detected:
        score += 35
        reasons.append("thermal throttle indicators detected")
    if score >= 70:
        level = "critical"
    elif score >= 35:
        level = "high"
    elif score >= 15:
        level = "medium"
    else:
        level = "low"
    return {"score": score, "risk_level": level, "reasons": reasons}


def load_report_temperatures(paths: list[str] | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    readings: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    for path in paths or []:
        payload = read_json_file(path)
        readings.extend(collect_temperature_readings_from_json(payload, path))
        sources.append({"path": path})
    return readings, sources
