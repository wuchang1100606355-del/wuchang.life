#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W7TP Governance Packet Auditor.

- Does not write repo files.
- Does not stage files.
- Does not commit.
- Does not deploy.
- Audits one packet and prints a review summary.
- Does not echo secret values; reports value_present only.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


SECRET_VALUE_KEYS = {
    "refresh_token",
    "access_token",
    "client_secret",
    "router_password",
    "private_key",
}
HIGH_PRESSURE_COORDS = {"USB", "D6", "router_authority"}


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


def pressure_lane(coordinate: str) -> str:
    if coordinate in HIGH_PRESSURE_COORDS or any(marker in coordinate for marker in HIGH_PRESSURE_COORDS):
        return "high_pressure"
    return "low_pressure"


def secret_value_issues(packet: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues = []
    for path, key, value in walk(packet):
        if key not in SECRET_VALUE_KEYS:
            continue
        if isinstance(value, str) and value.strip():
            issues.append({"issue": "secret_value_present", "path": path, "key": key, "value_present": True})
        elif value not in ("", None, False):
            issues.append({"issue": "secret_value_present", "path": path, "key": key, "value_present": True})
    return issues


def audit(packet: Dict[str, Any]) -> Dict[str, Any]:
    issues: List[Any] = []
    coordinate = coordinate_value(packet)
    lane = pressure_lane(coordinate)

    if coordinate == "USB" and packet.get("mailbox_backend") == "jffs_only":
        issues.append({"issue": "USB mailbox cannot use JFFS backend"})

    if coordinate in {"D6", "router_authority"} and not packet.get("evidence_ref"):
        issues.append({"issue": "high-pressure path missing evidence_ref"})

    if packet.get("cloud_authority") is True:
        issues.append({"issue": "cloud authority is forbidden"})

    if packet.get("requires_authority") and lane == "low_pressure":
        issues.append({"issue": "low-pressure flow requests authority"})

    issues.extend(secret_value_issues(packet))

    return {
        "STATE": "HOLD_GOVERNANCE_PACKET" if issues else "PASS_GOVERNANCE_PACKET",
        "coordinate": coordinate,
        "intent": packet.get("intent") or packet.get("D1_intent", {}).get("intent_id"),
        "pressure_lane": lane,
        "issues": issues,
        "issue_count": len(issues),
        "has_evidence_ref": bool(packet.get("evidence_ref")),
        "writes_repo": False,
        "auto_stage": False,
        "auto_commit": False,
        "deploy": False,
        "db_write": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    args = parser.parse_args()

    packet = json.loads(Path(args.file).read_text(encoding="utf-8"))
    if not isinstance(packet, dict):
        result = {
            "STATE": "HOLD_GOVERNANCE_PACKET_INVALID_INPUT",
            "reason": "root JSON value must be an object",
            "writes_repo": False,
            "auto_stage": False,
            "auto_commit": False,
            "deploy": False,
            "db_write": False,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    result = audit(packet)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["STATE"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
