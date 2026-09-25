#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W7TP Total Field Governance Engine V2.

Read-only orchestration layer for Total Field governance checks:
- does not modify sealed commits af7d186 or a5fde27
- does not mix synthetic generator sandbox ffff3fe into governance packets
- does not stage, commit, deploy, read secrets, write DB, or restart services
- default mode writes nothing; optional --out-dir writes runtime-only evidence

Pipeline:
repo gate -> flow guard -> flow monitor -> aggregator -> auditor -> coordinate map
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict


TOOLS_DIR = Path(__file__).resolve().parent
ROOT = TOOLS_DIR.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from w7tp_data_breathing_flow_guard import flow_guard  # noqa: E402
from w7tp_data_breathing_flow_monitor import monitor  # noqa: E402
from w7tp_flow_rhythm_aggregator import aggregate  # noqa: E402
from w7tp_governance_packet_auditor import audit  # noqa: E402
from w7tp_packet_coordinate_map import coordinate_map  # noqa: E402


def run_json_tool(cmd: list[str]) -> Dict[str, Any]:
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    try:
        parsed = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        parsed = {
            "STATE": "HOLD_TOOL_JSON_PARSE_FAILED",
            "stdout": proc.stdout,
        }
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "ok": proc.returncode == 0,
        "result": parsed,
        "stderr": proc.stderr,
    }


def load_packet(path: Path) -> Dict[str, Any]:
    packet = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(packet, dict):
        raise ValueError("packet root JSON value must be an object")
    return packet


def state_ok(state: str, allow_hold: bool = False) -> bool:
    if state.startswith("PASS_"):
        return True
    return allow_hold and state.startswith("HOLD_")


def engine_state(repo_gate: Dict[str, Any], guard: Dict[str, Any], auditor: Dict[str, Any]) -> str:
    repo_state = str(repo_gate.get("result", {}).get("STATE", ""))
    guard_state = str(guard.get("STATE", ""))
    auditor_state = str(auditor.get("STATE", ""))

    if not state_ok(repo_state):
        return "HOLD_TOTAL_FIELD_GOVERNANCE_ENGINE_REPO_GATE"
    if guard_state.startswith("HOLD_"):
        return "HOLD_TOTAL_FIELD_GOVERNANCE_ENGINE_FLOW_GUARD"
    if auditor_state.startswith("HOLD_"):
        return "HOLD_TOTAL_FIELD_GOVERNANCE_ENGINE_AUDITOR"
    return "PASS_TOTAL_FIELD_GOVERNANCE_ENGINE_V2"


def run_engine(packet_path: Path) -> Dict[str, Any]:
    packet = load_packet(packet_path)
    repo_gate = run_json_tool(["python3", "tools/w7tp_commit_envelope_gate.py"])
    runtime_guard = run_json_tool(["python3", "tools/w7tp_runtime_artifact_guard.py"])
    mode_only = run_json_tool(["python3", "tools/w7tp_mode_only_permission_decision.py", "--staged"])

    guard = flow_guard(packet, str(packet_path))
    monitor_record = monitor(packet, guard, str(packet_path), "in_memory_flow_guard")
    aggregate_record = aggregate([monitor_record])
    auditor = audit(packet)
    coord = coordinate_map(packet)

    state = engine_state(repo_gate, guard, auditor)
    return {
        "STATE": state,
        "task": "W7TP_TOTAL_FIELD_GOVERNANCE_ENGINE_V2",
        "source_packet_file": str(packet_path),
        "repo_gate": repo_gate,
        "runtime_artifact_guard": runtime_guard,
        "mode_only_permission_decision": mode_only,
        "flow_guard": guard,
        "flow_monitor": monitor_record,
        "flow_rhythm_aggregate": aggregate_record,
        "governance_packet_auditor": auditor,
        "packet_coordinate_map": coord,
        "sealed_commits": {
            "router_usb_dead_letter_governance": "af7d186",
            "member_sovereignty_ai_quality_gates": "a5fde27",
            "synthetic_generator_sandbox": "ffff3fe",
        },
        "writes_repo": False,
        "auto_stage": False,
        "auto_commit": False,
        "deploy": False,
        "db_write": False,
        "secret_read": False,
    }


def default_out_dir() -> Path:
    run_id = "GOVERNANCE_ENGINE_V2_%s" % time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    return ROOT / "runtime" / "total_field_governance_engine" / run_id


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="packet JSON to inspect")
    parser.add_argument("--out-dir", help="optional runtime-only output directory")
    args = parser.parse_args()

    try:
        result = run_engine(Path(args.file))
    except Exception as exc:
        result = {
            "STATE": "HOLD_TOTAL_FIELD_GOVERNANCE_ENGINE_ERROR",
            "reason": str(exc),
            "writes_repo": False,
            "auto_stage": False,
            "auto_commit": False,
            "deploy": False,
            "db_write": False,
            "secret_read": False,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    if args.out_dir:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "TOTAL_FIELD_GOVERNANCE_ENGINE_V2_REPORT.json"
        out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        result = {
            "STATE": result["STATE"] + "_WRITTEN" if result["STATE"].startswith("PASS_") else result["STATE"],
            "out_file": str(out_file),
            "writes_repo": False,
            "auto_stage": False,
            "auto_commit": False,
            "deploy": False,
            "db_write": False,
            "secret_read": False,
        }

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if str(result["STATE"]).startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
