#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W7TP Flow Rhythm Aggregator.

- Does not write repo files.
- Does not stage files.
- Does not commit.
- Does not deploy.
- Aggregates runtime Flow Monitor reports only.
"""

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List


def high_pressure_count(record: Dict[str, Any]) -> int:
    if isinstance(record.get("metrics"), dict):
        return int(record["metrics"].get("high_pressure_event_count", 0))
    return 1 if record.get("pressure_lane") == "high_pressure" else 0


def low_pressure_count(record: Dict[str, Any]) -> int:
    if isinstance(record.get("metrics"), dict):
        return int(record["metrics"].get("low_pressure_event_count", 0))
    return 1 if record.get("pressure_lane") == "low_pressure" else 0


def hold_count(record: Dict[str, Any]) -> int:
    if isinstance(record.get("metrics"), dict):
        return int(record["metrics"].get("hold_event_count", 0))
    return 1 if record.get("is_hold") or record.get("guard", {}).get("is_hold") else 0


def dead_letter_count(record: Dict[str, Any]) -> int:
    if isinstance(record.get("metrics"), dict):
        return int(record["metrics"].get("dead_letter_count", 0))
    return 1 if record.get("dead_letter") else 0


def secret_risk_count_for_record(record: Dict[str, Any]) -> int:
    if isinstance(record.get("metrics"), dict):
        return int(record["metrics"].get("secret_value_present_count", 0))
    return 1 if record.get("secret_value_present") or record.get("refined_secret_value_check", {}).get("value_present") else 0


def evidence_ref_present_count(record: Dict[str, Any]) -> int:
    if isinstance(record.get("metrics"), dict):
        return int(record["metrics"].get("evidence_ref_present_count", 0))
    return 1 if record.get("has_evidence_ref") else 0


def aggregate(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    high = sum(high_pressure_count(record) for record in records)
    low = sum(low_pressure_count(record) for record in records)
    hold = sum(hold_count(record) for record in records)
    dead = sum(dead_letter_count(record) for record in records)
    secret_risk_count = sum(secret_risk_count_for_record(record) for record in records)
    evidence = sum(evidence_ref_present_count(record) for record in records)

    total = len(records)
    return {
        "STATE": "PASS_FLOW_RHYTHM_AGGREGATE",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "record_count": total,
        "high_pressure_count": high,
        "low_pressure_count": low,
        "hold_count": hold,
        "dead_letter_count": dead,
        "secret_value_present_count": secret_risk_count,
        "evidence_ref_present_count": evidence,
        "hold_density": hold / total if total else 0,
        "dead_letter_density": dead / total if total else 0,
        "writes_repo": False,
        "auto_stage": False,
        "auto_commit": False,
        "deploy": False,
        "db_write": False,
        "records": records,
    }


def default_out_dir() -> Path:
    run_id = "FLOW_AGGREGATE_%s" % time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    return Path("runtime") / "data_breathing_flow" / run_id


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", nargs="+", required=True)
    parser.add_argument("--out-dir")
    parser.add_argument("--stdout-only", action="store_true")
    args = parser.parse_args()

    records = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.files]
    if not all(isinstance(record, dict) for record in records):
        print(json.dumps({
            "STATE": "HOLD_FLOW_RHYTHM_AGGREGATE_INVALID_RECORD",
            "reason": "all input JSON roots must be objects",
            "writes_repo": False,
            "auto_stage": False,
            "auto_commit": False,
            "deploy": False,
            "db_write": False,
        }, ensure_ascii=False, indent=2))
        return 1

    agg = aggregate(records)
    if args.stdout_only:
        print(json.dumps(agg, ensure_ascii=False, indent=2))
        return 0

    out = Path(args.out_dir) if args.out_dir else default_out_dir()
    out.mkdir(parents=True, exist_ok=True)
    out_file = out / "FLOW_RHYTHM_AGGREGATE.json"
    out_file.write_text(json.dumps(agg, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "STATE": "PASS_FLOW_RHYTHM_AGGREGATE_WRITE",
        "out_file": str(out_file),
        "writes_repo": False,
        "auto_stage": False,
        "auto_commit": False,
        "deploy": False,
        "db_write": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
