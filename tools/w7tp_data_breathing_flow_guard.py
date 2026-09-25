#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W7TP Data Breathing Flow Guard.

- Does not write repo files.
- Does not stage files.
- Does not commit.
- Does not deploy.
- Does not read secrets intentionally; if secret-value fields are present in
  the inspected JSON, it reports HOLD without echoing raw packet content.
- Does not write DB.
- Performs rhythm checks only: PASS / HOLD.

Total Field constraints:
- af7d186 router USB dead-letter governance is sealed; this guard does not
  modify it.
- a5fde27 member sovereignty + AI quality gates is sealed; this guard does not
  modify it.
- ffff3fe synthetic generator sandbox is isolated; this guard does not mix it.
- Mode-only permission hygiene is outside this guard.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


FORBIDDEN_SECRET_VALUE_KEYS = {
    "refresh_token",
    "access_token",
    "client_secret",
    "router_password",
    "private_key",
}

HIGH_PRESSURE_MARKERS = {
    "USB",
    "usb",
    "D6",
    "d6",
    "router_authority",
    "router",
}

LOW_PRESSURE_MARKERS = {
    "LAN",
    "lan",
    "GPT",
    "gpt",
    "cloudflare",
    "Cloudflare",
    "cloud_candidate",
}


def walk(obj: Any, path: str = "$") -> Iterable[Tuple[str, str, Any]]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            current = "%s.%s" % (path, key)
            yield current, key, value
            yield from walk(value, current)
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            yield from walk(value, "%s[%s]" % (path, idx))


def packet_summary(packet: Dict[str, Any], source_file: str) -> Dict[str, Any]:
    return {
        "source_file": source_file,
        "top_level_keys": sorted(packet.keys()),
        "run_id": packet.get("run_id"),
        "packet_type": packet.get("packet_type"),
        "decision": packet.get("decision") or packet.get("route_decision") or packet.get("backend_decision"),
        "evidence_ref_present": bool(packet.get("evidence_ref")),
    }


def refined_secret_value_check(packet: Dict[str, Any]) -> Dict[str, Any]:
    """
    Refined Total Field secret check.

    This checks values only for explicit secret-value field names. It does not
    perform broad pattern matching and therefore does not treat governance text
    such as "secret check" as a secret.
    """
    hits = []
    for path, key, value in walk(packet):
        if key not in FORBIDDEN_SECRET_VALUE_KEYS:
            continue
        if isinstance(value, str) and value.strip():
            hits.append({"path": path, "key": key, "value_present": True})
        elif value not in ("", None, False):
            hits.append({"path": path, "key": key, "value_present": True})
    return {
        "STATE": "REFINED_SECRET_VALUE_CHECK_PASS" if not hits else "REFINED_SECRET_VALUE_CHECK_HOLD",
        "ok": not hits,
        "hits": hits,
    }


def string_fields(packet: Dict[str, Any]) -> List[str]:
    fields = []
    for _, _, value in walk(packet):
        if isinstance(value, str):
            fields.append(value)
    return fields


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
    """
    High / low pressure classification:
    - USB / D6 / router authority -> high_pressure
    - LAN / GPT / cloudflare / cloud_candidate -> low_pressure
    """
    coord = coordinate_value(packet)
    haystack = " ".join([coord] + string_fields(packet))
    if any(marker in haystack for marker in HIGH_PRESSURE_MARKERS):
        return "high_pressure"
    if any(marker in haystack for marker in LOW_PRESSURE_MARKERS):
        return "low_pressure"
    return "low_pressure"


def evidence_required(packet: Dict[str, Any], pressure: str, coord: str) -> bool:
    if pressure != "high_pressure":
        return False
    if coord in {"USB", "D6", "router_authority"}:
        return True
    if any(marker in coord for marker in ["USB", "D6", "router_authority", "router"]):
        return True
    return bool(packet.get("requires_authority"))


def forbidden_actions(packet: Dict[str, Any]) -> List[str]:
    actions = []
    direct = packet.get("forbidden_actions")
    if isinstance(direct, list):
        actions.extend(str(item) for item in direct)
    d5 = packet.get("D5_execution")
    if isinstance(d5, dict) and isinstance(d5.get("forbidden_actions"), list):
        actions.extend(str(item) for item in d5["forbidden_actions"])
    return sorted(set(actions))


def hold(state: str, reason: str, packet: Dict[str, Any], source_file: str, pressure: str, coord: str, extra: Dict[str, Any] = None) -> Dict[str, Any]:
    result = {
        "STATE": state,
        "decision": "HOLD",
        "reason": reason,
        "pressure_lane": pressure,
        "coordinate": coord,
        "forbidden_actions": forbidden_actions(packet),
        "packet_summary": packet_summary(packet, source_file),
        "writes_repo": False,
        "auto_stage": False,
        "auto_commit": False,
        "deploy": False,
        "db_write": False,
        "secret_read": False,
    }
    if extra:
        result.update(extra)
    return result


def flow_guard(packet: Dict[str, Any], source_file: str = "") -> Dict[str, Any]:
    """
    Flow Guard main logic:
    - check coordinate
    - check pressure lane
    - check refined secret values
    - check misplaced or unauthorized authority requirements
    """
    coord = coordinate_value(packet)
    intent = str(packet.get("intent", "") or packet.get("D1_intent", {}).get("intent_id", ""))
    pressure = classify_pressure_lane(packet)

    secret_check = refined_secret_value_check(packet)
    if not secret_check["ok"]:
        return hold(
            "HOLD_FLOW_SECRET_VALUE",
            "refined secret value check failed",
            packet,
            source_file,
            pressure,
            coord,
            {"refined_secret_value_check": secret_check},
        )

    if packet.get("mailbox_backend") == "jffs_only":
        return hold(
            "HOLD_FLOW_JFFS_BACKEND",
            "USB dead-letter mailbox cannot use JFFS-only backend",
            packet,
            source_file,
            pressure,
            coord,
        )

    jffs_status = packet.get("jffs_status")
    if isinstance(jffs_status, dict) and jffs_status.get("role") not in {None, "pointer_status_only"}:
        return hold(
            "HOLD_FLOW_JFFS_ROLE",
            "JFFS role must remain pointer/status only",
            packet,
            source_file,
            pressure,
            coord,
        )

    usb_dead_letter_status = packet.get("usb_dead_letter_status")
    if isinstance(usb_dead_letter_status, dict):
        if usb_dead_letter_status.get("required") is True and usb_dead_letter_status.get("healthy") is False:
            return hold(
                "HOLD_FLOW_USB_BACKEND_UNAVAILABLE",
                "required USB dead-letter backend is unavailable",
                packet,
                source_file,
                pressure,
                coord,
            )

    if evidence_required(packet, pressure, coord) and not packet.get("evidence_ref"):
        return hold(
            "HOLD_FLOW_MISSING_EVIDENCE",
            "high-pressure path missing evidence_ref",
            packet,
            source_file,
            pressure,
            coord,
        )

    if pressure == "low_pressure" and packet.get("requires_authority"):
        return hold(
            "HOLD_FLOW_LOW_PRESSURE_AUTHORITY",
            "low-pressure flow cannot request router authority",
            packet,
            source_file,
            pressure,
            coord,
        )

    if packet.get("cloud_authority") is True:
        return hold(
            "HOLD_FLOW_CLOUD_AUTHORITY",
            "cloud authority is forbidden in Data Breathing Flow governance",
            packet,
            source_file,
            pressure,
            coord,
        )

    return {
        "STATE": "PASS_FLOW_RHYTHM",
        "decision": "PASS",
        "pressure_lane": pressure,
        "coordinate": coord,
        "intent": intent,
        "forbidden_actions": forbidden_actions(packet),
        "refined_secret_value_check": secret_check,
        "packet_summary": packet_summary(packet, source_file),
        "writes_repo": False,
        "auto_stage": False,
        "auto_commit": False,
        "deploy": False,
        "db_write": False,
        "secret_read": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="JSON packet/report file to inspect")
    args = parser.parse_args()

    source = Path(args.file)
    packet = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(packet, dict):
        result = {
            "STATE": "HOLD_FLOW_INVALID_PACKET",
            "decision": "HOLD",
            "reason": "root JSON value must be an object",
            "source_file": str(source),
            "writes_repo": False,
            "auto_stage": False,
            "auto_commit": False,
            "deploy": False,
            "db_write": False,
            "secret_read": False,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    result = flow_guard(packet, str(source))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["STATE"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
