#!/usr/bin/env python3
"""Validate W7TP capability-assimilation packet structure and authority hard walls.

This validator proves form and selected hard-wall checks only. It does not prove
semantic truth, source-code correctness, license clearance, or real D8 authority.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

REQUIRED_TOP = {
    "state", "operation", "source", "target", "capabilities",
    "target_base_state", "minimum_required_delta", "authority_conflicts",
    "evidence_gaps", "d1", "d2", "d3", "d4", "d5", "d6", "d7", "d8",
}

STATE_ENUM = {
    "PASS_READ_ONLY_ASSIMILATION",
    "PRECONDITION_MISSING",
    "HOLD_TRUE_HARD_RISK",
    "BLOCK_AUTHORITY_INVERSION",
}
OP_ENUM = {"DISCOVER", "ACQUIRE", "EXTRACT", "COMPARE", "ASSIMILATE", "VALIDATE"}
STATUS_ENUM = {
    "DOCUMENTED_ONLY", "IMPLEMENTED", "UPSTREAM_TESTED",
    "VERIFIED_CURRENT_RUN", "UNKNOWN", "ABSENT",
}
DISPOSITION_ENUM = {"REUSE_DIRECTLY", "ADAPT", "REIMPLEMENT", "REJECT"}

CAP_REQUIRED = {
    "capability_id", "source_component", "status", "input", "output",
    "state_dependency", "side_effect", "evidence_output", "failure_mode",
    "security_assumption", "disposition", "d1", "d2", "d3", "d4",
    "d5", "d6", "d7", "d8",
}

# Detect explicit authority promotions. This is intentionally conservative and
# only rejects strong equality/assignment-style claims, not ordinary prose
# that discusses external identity or policy mechanisms.
FORBIDDEN_PATTERNS = [
    re.compile(r"(?i)\b(source[_ -]?admin|platform[_ -]?admin|reviewer|oidc[_ -]?(subject|identity)|policy[_ -]?allow|plugin[_ -]?pass|ci[_ -]?pass|source[_ -]?done|skill[_ -]?trigger)\b\s*(==|=|->|→|becomes?|is)\s*\b(founder|founder[_ -]?identity|d8|d8[_ -]?authority|effect[_ -]?authorization|w7tp[_ -]?(pass|active|canonical)|canonical[_ -]?decision)\b"),
    re.compile(r"(?i)\bexternal\b.{0,40}\b(grants?|defines?|becomes?)\b.{0,40}\b(d8[_ -]?authority|founder[_ -]?identity|w7tp[_ -]?canonical)\b"),
]


def flatten_strings(obj: Any):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for key, value in obj.items():
            yield str(key)
            yield from flatten_strings(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from flatten_strings(value)


def validate(data: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    missing = sorted(REQUIRED_TOP - data.keys())
    if missing:
        errors.append(f"missing top-level fields: {', '.join(missing)}")

    if data.get("state") not in STATE_ENUM:
        errors.append(f"invalid state: {data.get('state')!r}")
    if data.get("operation") not in OP_ENUM:
        errors.append(f"invalid operation: {data.get('operation')!r}")

    source = data.get("source")
    if not isinstance(source, dict):
        errors.append("source must be an object")
    else:
        if not source.get("repository"):
            errors.append("source.repository is required")
        evidence_status = source.get("evidence_status")
        if evidence_status not in STATUS_ENUM - {"ABSENT"}:
            errors.append(f"invalid source.evidence_status: {evidence_status!r}")

    caps = data.get("capabilities")
    if not isinstance(caps, list):
        errors.append("capabilities must be an array")
        caps = []

    ids: set[str] = set()
    for index, cap in enumerate(caps):
        label = f"capabilities[{index}]"
        if not isinstance(cap, dict):
            errors.append(f"{label} must be an object")
            continue
        cap_missing = sorted(CAP_REQUIRED - cap.keys())
        if cap_missing:
            errors.append(f"{label} missing fields: {', '.join(cap_missing)}")
        cap_id = cap.get("capability_id")
        if not isinstance(cap_id, str) or not cap_id.strip():
            errors.append(f"{label}.capability_id must be a non-empty string")
        elif cap_id in ids:
            errors.append(f"duplicate capability_id: {cap_id}")
        else:
            ids.add(cap_id)
        if cap.get("status") not in STATUS_ENUM:
            errors.append(f"{label} invalid status: {cap.get('status')!r}")
        if cap.get("disposition") not in DISPOSITION_ENUM:
            errors.append(f"{label} invalid disposition: {cap.get('disposition')!r}")

        d8_text = " ".join(flatten_strings(cap.get("d8")))
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(d8_text):
                errors.append(f"{label}.d8 contains authority-inversion promotion")
                break

    if not isinstance(data.get("authority_conflicts"), list):
        errors.append("authority_conflicts must be an array")
    if not isinstance(data.get("evidence_gaps"), list):
        errors.append("evidence_gaps must be an array")

    whole_text = " ".join(flatten_strings(data))
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(whole_text):
            errors.append("packet contains an explicit authority-inversion promotion")
            break

    if data.get("state") == "PASS_READ_ONLY_ASSIMILATION" and data.get("project_code_executed") is True:
        warnings.append("PASS_READ_ONLY_ASSIMILATION with project_code_executed=true requires careful evidence wording")

    if not caps:
        warnings.append("capabilities is empty")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", help="Assimilation packet JSON path")
    args = parser.parse_args()

    path = Path(args.packet)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"STATE=FAIL\nERROR=JSON_READ_ERROR:{exc}")
        return 2

    if not isinstance(data, dict):
        print("STATE=FAIL\nERROR=TOP_LEVEL_NOT_OBJECT")
        return 2

    errors, warnings = validate(data)
    if errors:
        print("STATE=FAIL")
        for item in errors:
            print(f"ERROR={item}")
        for item in warnings:
            print(f"WARNING={item}")
        return 1

    print("STATE=PASS")
    print("VALIDATION_SCOPE=STRUCTURE_AND_AUTHORITY_HARD_WALL_ONLY")
    print(f"CAPABILITY_COUNT={len(data.get('capabilities', []))}")
    for item in warnings:
        print(f"WARNING={item}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
