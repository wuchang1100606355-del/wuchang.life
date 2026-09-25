#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only verifier for the candidate D3 deterministic transition engine."""

from __future__ import annotations

import copy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.d3_coordinate_transition_candidate import (  # noqa: E402
    transition_coordinate,
    verify_transition_record,
)


def main() -> int:
    previous = {"node": {"id": "node-candidate", "position": {"x": 0, "y": 2}}}
    context = {
        "coordinate_delta": {"node": {"position": {"x": 3}}},
        "d7_reference": {"rule_ref": "candidate/rules/state-update-v0.3"},
    }
    inputs = {
        "previous_coord": previous,
        "event_code": "STATE_UPDATE",
        "event_id": "evt-d3-fixed-001",
        "logical_time": "logical:000001",
        "rule_ref": "candidate/rules/state-update-v0.3",
        "context": context,
    }
    before = copy.deepcopy(inputs)
    first = transition_coordinate(**inputs)
    second = transition_coordinate(**inputs)
    verification = verify_transition_record(first)

    checks = {
        "DETERMINISTIC_REPLAY": first["transition_hash"] == second["transition_hash"],
        "ALLOW_ONLY_COMMIT": first["committed"] == first["proposed"] and first["commit_applied"],
        "CALLER_INPUT_UNCHANGED": inputs == before,
        "TRANSITION_HASH_VERIFY": verification["valid"],
    }
    for name, passed in checks.items():
        print(f"{name}={'PASS' if passed else 'FAIL'}")
    if not all(checks.values()):
        print("STATE=HOLD_VERIFY_D3_DETERMINISTIC_TRANSITION_CANDIDATE")
        return 1
    print("STATE=PASS_VERIFY_D3_DETERMINISTIC_TRANSITION_CANDIDATE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
