#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merlin manual execution result recorder.

This module records a human-reported outcome for a generated Merlin checklist.
It never logs in to a router, invokes SSH, applies configuration, or restarts a
service.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional


ROOT = Path(__file__).resolve().parents[2]
CHECKLIST_DIR = ROOT / "runtime" / "merlin_human_execution_checklist"
RESULT_DIR = ROOT / "runtime" / "merlin_execution_result"
REPORT_DIR = ROOT / "runtime" / "reports"
VALID_OUTCOMES = {
    "completed",
    "abandoned",
    "rollback_needed",
    "failed",
    "observation_only",
}
SENSITIVE_TEXT = re.compile(
    r"(api[ _-]?key|access[ _-]?token|private[ _-]?key|password|passwd|credential|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|Bearer\s+\S+|sk-[A-Za-z0-9_-]{8,})",
    re.IGNORECASE,
)


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)[:120]


def sha256_obj(obj: Dict[str, Any]) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def latest_checklist() -> Optional[Path]:
    candidates = sorted(
        CHECKLIST_DIR.glob("*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def resolve_checklist(selection: str | None) -> Path:
    if selection and selection != "latest":
        path = (ROOT / selection).resolve() if not Path(selection).is_absolute() else Path(selection).resolve()
        try:
            path.relative_to(ROOT)
        except ValueError as exc:
            raise ValueError("checklist must be a file within the repository") from exc
    else:
        path = latest_checklist()
        if path is None:
            raise ValueError("no checklist JSON found")
    if not path.is_file() or path.suffix.lower() != ".json":
        raise ValueError("checklist must be an existing JSON file")
    return path


def read_checklist_metadata(path: Path) -> Dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if obj.get("status") != "manual_checklist_ready":
        raise ValueError("only manual_checklist_ready checklist can receive an execution result")
    if obj.get("auto_execute") is not False or obj.get("executable") is not False:
        raise ValueError("checklist is not marked manual-only")
    required = ("intent", "ticket_id", "ticket_hash", "approval_record_hash", "checklist_hash")
    missing = [field for field in required if not obj.get(field)]
    if missing:
        raise ValueError("checklist missing required metadata: " + ", ".join(missing))
    return {field: obj[field] for field in required}


def validated_operator_text(value: str, field: str) -> str:
    if SENSITIVE_TEXT.search(value):
        raise ValueError(f"{field} contains a sensitive-data marker")
    return value.strip()[:500]


def build_record(
    checklist_path: Path,
    metadata: Dict[str, Any],
    outcome: str,
    operator: str,
    note: str,
) -> Dict[str, Any]:
    record: Dict[str, Any] = {
        "recorder": "merlin_execution_result_recorder",
        "mode": "human_result_record_only",
        "created_at": utc_now(),
        "outcome": outcome,
        "operator": operator,
        "note": note,
        "intent": metadata["intent"],
        "ticket_id": metadata["ticket_id"],
        "ticket_hash": metadata["ticket_hash"],
        "approval_record_hash": metadata["approval_record_hash"],
        "checklist_hash": metadata["checklist_hash"],
        "source_checklist": str(checklist_path.relative_to(ROOT)),
        "auto_execute": False,
        "executable": False,
        "safety": {
            "no_router_login": True,
            "no_ssh": True,
            "no_http_router_api": True,
            "no_configuration_apply": True,
            "no_restart": True,
            "no_credential_storage": True,
            "result_record_only": True,
        },
    }
    record["result_hash"] = sha256_obj(record)
    return record


def to_markdown(record: Dict[str, Any], result_path: Path) -> str:
    return "\n".join(
        [
            "# Merlin Execution Result Record",
            "",
            f"- Outcome: `{record['outcome']}`",
            f"- Intent: `{record['intent']}`",
            f"- Ticket ID: `{record['ticket_id']}`",
            f"- Checklist Hash: `{record['checklist_hash']}`",
            f"- Result Hash: `{record['result_hash']}`",
            f"- Operator: `{record['operator'] or 'not_specified'}`",
            f"- Note: `{record['note'] or 'none'}`",
            f"- Source Checklist: `{record['source_checklist']}`",
            f"- Result JSONL: `{result_path.relative_to(ROOT)}`",
            "",
            "## Outcome Meaning",
            "",
            "- This is a human-provided result record only.",
            "- It is not proof that this script contacted or modified a router.",
            "",
            "## Safety Boundary",
            "",
            "- No router login by this script.",
            "- No SSH by this script.",
            "- No HTTP router admin API call.",
            "- No configuration apply.",
            "- No service restart.",
            "- No password, API key, token, private key, or credential storage.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--checklist",
        default="latest",
        help="Checklist selection: latest or a repository-relative JSON path.",
    )
    parser.add_argument("--checklist-json", default=None)
    parser.add_argument("--latest-checklist", action="store_true", help="Compatibility alias for --checklist latest.")
    parser.add_argument("--status", required=True, choices=sorted(VALID_OUTCOMES))
    parser.add_argument("--operator", default="")
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    try:
        selection = args.checklist_json or ("latest" if args.latest_checklist else args.checklist)
        checklist_path = resolve_checklist(selection)
        metadata = read_checklist_metadata(checklist_path)
        operator = validated_operator_text(args.operator, "operator")
        note = validated_operator_text(args.note, "note")
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        print(json.dumps({"status": "rejected_record", "reason": str(exc)}, ensure_ascii=False, indent=2))
        return 2

    record = build_record(checklist_path, metadata, args.status, operator, note)
    timestamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    base = f"{timestamp}_{safe_name(str(record['ticket_id']))}_{safe_name(record['outcome'])}"
    result_path = RESULT_DIR / f"result_{base}.jsonl"
    report_path = REPORT_DIR / f"merlin_execution_result_{timestamp}.md"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(to_markdown(record, result_path), encoding="utf-8")

    print(
        json.dumps(
            {
                "status": "result_recorded",
                "outcome": record["outcome"],
                "ticket_id": record["ticket_id"],
                "result_hash": record["result_hash"],
                "result_jsonl": str(result_path),
                "report": str(report_path),
                "auto_execute": False,
                "executable": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
