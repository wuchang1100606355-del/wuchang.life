#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W7TP Data Breathing Flow Monitor.

- Does not write repo files.
- Does not stage files.
- Does not commit.
- Does not deploy.
- Does not read secrets intentionally; if secret-value fields are present in
  inspected JSON, it records value_present only and never echoes the value.
- Does not write DB.
- Observes rhythm only; Flow Guard is the PASS/HOLD authority.

Total Field constraints:
- af7d186 router USB dead-letter governance is sealed; this monitor does not
  modify it.
- a5fde27 member sovereignty + AI quality gates is sealed; this monitor does
  not modify it.
- ffff3fe synthetic generator sandbox is isolated; this monitor does not mix it.
- Mode-only permission hygiene is outside this monitor.
"""

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple


ROOT = Path(__file__).resolve().parents[1]
SECRET_VALUE_KEYS = {
    "refresh_token",
    "access_token",
    "client_secret",
    "router_password",
    "private_key",
}
HIGH_PRESSURE_MARKERS = {"USB", "usb", "D6", "d6", "router_authority", "router"}


def walk(obj: Any, path: str = "$") -> Iterable[Tuple[str, str, Any]]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            current = "%s.%s" % (path, key)
            yield current, key, value
            yield from walk(value, current)
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            yield from walk(value, "%s[%s]" % (path, idx))


def coordinate_value(packet: Dict[str, Any]) -> str:
    coord = packet.get("coordinate", "")
    if isinstance(coord, dict):
        return json.dumps(coord, ensure_ascii=False, sort_keys=True)
    if coord:
        return str(coord)
    if packet.get("mailbox_backend") == "usb" or packet.get("usb_mount_ref") or packet.get("usb_dead_letter_status"):
        return "USB"
    if "usb" in str(packet.get("dead_letter_ref", "")).lower():
        return "USB"
    if packet.get("router_id_ref") or packet.get("node_type") == "router":
        return "router_authority"
    if "D6" in str(packet.get("packet_type", "")) or "D6" in str(packet.get("schema_ref", "")):
        return "D6"
    if packet.get("source_node_type") == "cloud_candidate":
        return "cloud_candidate"
    return ""


def classify_pressure_lane(packet: Dict[str, Any]) -> str:
    coord = coordinate_value(packet)
    strings = [coord]
    for _, _, value in walk(packet):
        if isinstance(value, str):
            strings.append(value)
    haystack = " ".join(strings)
    if any(marker in haystack for marker in HIGH_PRESSURE_MARKERS):
        return "high_pressure"
    return "low_pressure"


def refined_secret_value_state(packet: Dict[str, Any]) -> Dict[str, Any]:
    hits = []
    for path, key, value in walk(packet):
        if key not in SECRET_VALUE_KEYS:
            continue
        if isinstance(value, str) and value.strip():
            hits.append({"path": path, "key": key, "value_present": True})
        elif value not in ("", None, False):
            hits.append({"path": path, "key": key, "value_present": True})
    return {
        "STATE": "REFINED_SECRET_VALUE_CHECK_PASS" if not hits else "REFINED_SECRET_VALUE_CHECK_HOLD",
        "value_present": bool(hits),
        "hits": hits,
    }


def is_dead_letter(packet: Dict[str, Any]) -> bool:
    if packet.get("dead_letter") is True:
        return True
    if packet.get("decision") == "DEAD_LETTER":
        return True
    if packet.get("route_decision") == "DEAD_LETTER":
        return True
    if packet.get("dead_letter_ref"):
        return True
    return False


def monitor(packet: Dict[str, Any], guard_result: Dict[str, Any], packet_file: str, guard_file: str) -> Dict[str, Any]:
    pressure = classify_pressure_lane(packet)
    guard_state = str(guard_result.get("STATE", ""))
    secret_state = refined_secret_value_state(packet)
    coordinate = coordinate_value(packet)
    has_evidence_ref = bool(packet.get("evidence_ref") or guard_result.get("packet_summary", {}).get("evidence_ref_present"))
    is_hold = guard_state.startswith("HOLD")

    return {
        "STATE": "PASS_FLOW_MONITOR_OBSERVATION",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_packet_file": packet_file,
        "source_guard_file": guard_file,
        "coordinate": coordinate,
        "intent": packet.get("intent") or packet.get("D1_intent", {}).get("intent_id"),
        "pressure_lane": pressure,
        "metrics": {
            "high_pressure_event_count": 1 if pressure == "high_pressure" else 0,
            "low_pressure_event_count": 1 if pressure == "low_pressure" else 0,
            "hold_event_count": 1 if is_hold else 0,
            "dead_letter_count": 1 if is_dead_letter(packet) else 0,
            "evidence_ref_present_count": 1 if has_evidence_ref else 0,
            "secret_value_present_count": 1 if secret_state["value_present"] else 0,
        },
        "guard": {
            "STATE": guard_state,
            "is_hold": is_hold,
            "decision": guard_result.get("decision"),
            "reason": guard_result.get("reason"),
        },
        "dead_letter": is_dead_letter(packet),
        "refined_secret_value_check": secret_state,
        "has_evidence_ref": has_evidence_ref,
        "writes_repo": False,
        "auto_stage": False,
        "auto_commit": False,
        "deploy": False,
        "db_write": False,
        "secret_read": False,
    }


def default_out_dir() -> Path:
    run_id = "FLOW_MONITOR_%s" % time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    return ROOT / "runtime" / "data_breathing_flow" / run_id


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="JSON packet/report file to observe")
    parser.add_argument("--guard", required=True, help="JSON Flow Guard result file")
    parser.add_argument("--out-dir", help="runtime output dir; defaults to runtime/data_breathing_flow/<RUN_ID>")
    parser.add_argument("--stdout-only", action="store_true", help="do not write runtime report; print observation only")
    args = parser.parse_args()

    packet_path = Path(args.file)
    guard_path = Path(args.guard)
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    guard_result = json.loads(guard_path.read_text(encoding="utf-8"))

    if not isinstance(packet, dict) or not isinstance(guard_result, dict):
        result = {
            "STATE": "HOLD_FLOW_MONITOR_INVALID_INPUT",
            "reason": "packet and guard JSON roots must be objects",
            "writes_repo": False,
            "auto_stage": False,
            "auto_commit": False,
            "deploy": False,
            "db_write": False,
            "secret_read": False,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    record = monitor(packet, guard_result, str(packet_path), str(guard_path))
    if args.stdout_only:
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return 0

    out_dir = Path(args.out_dir) if args.out_dir else default_out_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "FLOW_RHYTHM_REPORT.json"
    out_file.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "STATE": "PASS_FLOW_MONITOR_WRITE",
        "out_file": str(out_file),
        "writes_repo": False,
        "auto_stage": False,
        "auto_commit": False,
        "deploy": False,
        "db_write": False,
        "secret_read": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
