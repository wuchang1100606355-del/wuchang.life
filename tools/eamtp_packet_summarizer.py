#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EAMTP Packet Summarizer

Read EAMTP JSON / JSONL packets and generate a compact markdown summary.

Safety:
- read-only input
- no packet mutation
- no service restart
- no SSH
- no DB write
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "runtime" / "reports"


def get_nested(obj: Dict[str, Any], paths: List[str], default: str = "") -> str:
    for path in paths:
        cur: Any = obj
        ok = True
        for part in path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok and cur is not None:
            if isinstance(cur, (dict, list)):
                return json.dumps(cur, ensure_ascii=False)[:180]
            return str(cur)
    return default


def load_packets(path: Path) -> List[Dict[str, Any]]:
    packets: List[Dict[str, Any]] = []
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return packets

    if path.suffix.lower() == ".jsonl":
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                packets.append(obj)
            except Exception:
                packets.append({"_parse_error": line[:200]})
        return packets

    try:
        obj = json.loads(text)
        if isinstance(obj, list):
            packets.extend([x if isinstance(x, dict) else {"value": x} for x in obj])
        elif isinstance(obj, dict):
            # common report wrapper
            if isinstance(obj.get("packets"), list):
                packets.extend([x if isinstance(x, dict) else {"value": x} for x in obj["packets"]])
            elif isinstance(obj.get("eamtp_packet"), dict):
                packets.append(obj["eamtp_packet"])
            else:
                packets.append(obj)
    except Exception as e:
        packets.append({"_parse_error": str(e), "_source_preview": text[:200]})

    return packets


def summarize_packet(obj: Dict[str, Any]) -> Dict[str, str]:
    if "eamtp_packet" in obj and isinstance(obj["eamtp_packet"], dict):
        obj = obj["eamtp_packet"]

    return {
        "packet_id": get_nested(obj, [
            "packet_id",
            "id",
            "event_id",
            "header.packet_id",
            "ledger.packet_id"
        ], "-"),
        "intent_type": get_nested(obj, [
            "intent_type",
            "intent.intent_type",
            "d2_intent.intent_type",
            "d1_intent.intent_type",
            "event_type"
        ], "-"),
        "privacy_level": get_nested(obj, [
            "privacy_level",
            "privacy.level",
            "d4_privacy_consent.privacy_level",
            "d4_privacy.privacy_level"
        ], "-"),
        "risk_level": get_nested(obj, [
            "risk_level",
            "risk.level",
            "d5_risk_governance.risk_level",
            "d5_risk.risk_level"
        ], "-"),
        "preferred_lane": get_nested(obj, [
            "preferred_lane",
            "routing.preferred_lane",
            "d6_routing.preferred_lane",
            "d6_execution.preferred_lane"
        ], "-"),
        "state": get_nested(obj, [
            "state",
            "status",
            "d7_state.state",
            "d7_runtime.state"
        ], "-"),
        "decision": get_nested(obj, [
            "decision",
            "policy.decision",
            "router_decision",
            "driver_decision"
        ], "-"),
        "reasons": get_nested(obj, [
            "reasons",
            "policy.reasons",
            "risk.reasons",
            "d5_risk_governance.reasons"
        ], "-"),
    }


def markdown(rows: List[Dict[str, str]], source: str) -> str:
    lines = []
    lines.append("# EAMTP Packet Summary")
    lines.append("")
    lines.append(f"- Generated: `{dt.datetime.now(dt.timezone.utc).isoformat()}`")
    lines.append(f"- Source: `{source}`")
    lines.append(f"- Count: `{len(rows)}`")
    lines.append("- Mode: `read-only / no mutation`")
    lines.append("")
    lines.append("| # | Packet ID | Intent | Privacy | Risk | Lane | State | Decision | Reasons |")
    lines.append("|---:|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        lines.append(
            f"| {i} | `{r['packet_id']}` | {r['intent_type']} | {r['privacy_level']} | "
            f"{r['risk_level']} | {r['preferred_lane']} | {r['state']} | "
            f"{r['decision']} | {r['reasons']} |"
        )
    lines.append("")
    return "\n".join(lines)


def find_default_file() -> Path | None:
    candidates = [
        ROOT / "runtime" / "router_guard_dryrun" / "eamtp_router_guard_dryrun.jsonl",
        ROOT / "runtime" / "router_guard_dryrun" / "merlin_intent_driver_plan_only.jsonl",
        ROOT / "runtime" / "reports",
    ]
    for p in candidates:
        if p.is_file():
            return p
        if p.is_dir():
            files = sorted(p.glob("*eamtp*.json*"), key=lambda x: x.stat().st_mtime, reverse=True)
            if files:
                return files[0]
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    if args.file:
        path = Path(args.file)
        if not path.is_absolute():
            path = ROOT / path
    else:
        found = find_default_file()
        if found is None:
            REPORT_DIR.mkdir(parents=True, exist_ok=True)
            path = REPORT_DIR / "eamtp_packet_summary_sample.jsonl"
            path.write_text(json.dumps({
                "packet_id": "sample_eamtp",
                "intent_type": "sample",
                "privacy_level": "redacted",
                "risk_level": "low",
                "preferred_lane": "local",
                "state": "sample",
                "decision": "allow_low_risk",
                "reasons": ["sample_only"]
            }, ensure_ascii=False) + "\n", encoding="utf-8")
        else:
            path = found

    packets = load_packets(path)
    rows = [summarize_packet(p) for p in packets]

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = Path(args.out) if args.out else REPORT_DIR / f"eamtp_packet_summary_{ts}.md"
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(markdown(rows, str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)), encoding="utf-8")

    json_path = REPORT_DIR / f"eamtp_packet_summary_{ts}.json"
    json_path.write_text(json.dumps({
        "tool": "eamtp_packet_summarizer",
        "source": str(path),
        "markdown": str(out),
        "count": len(rows),
        "rows": rows,
        "input_mutated": False,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "decision": "eamtp_packet_summary_generated",
        "source": str(path),
        "markdown": str(out),
        "json": str(json_path),
        "count": len(rows),
        "input_mutated": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
