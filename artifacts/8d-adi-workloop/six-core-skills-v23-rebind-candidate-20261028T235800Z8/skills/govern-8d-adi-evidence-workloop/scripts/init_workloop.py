#!/usr/bin/env python3
"""Create a reversible, candidate-only 8D ADI evidence workloop scaffold."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path


SCHEMA_VERSION = "w7tp-8d-adi-evidence-workloop/1.0"
RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{2,95}")
EFFECT_CLASSES = {f"E{number}" for number in range(6)}
FIELD_NAMES = {
    "D1": "INTENT",
    "D2": "STATE",
    "D3": "COORDINATE",
    "D4": "EVIDENCE",
    "D5": "EXECUTION_POLICY",
    "D6": "GENERATIVE_TRANSMISSION",
    "D7": "RED_TEAM_RISK_CONFINEMENT",
    "D8": "ENVELOPE_AUTHORITY",
}


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--intent", required=True)
    parser.add_argument("--effect-class", choices=sorted(EFFECT_CLASSES), default="E2")
    parser.add_argument("--natural-person-ref", default="UNKNOWN_UNVERIFIED")
    parser.add_argument("--member-ref", default="UNKNOWN_UNVERIFIED")
    parser.add_argument("--xiaoj-ref", default="UNKNOWN_UNVERIFIED")
    parser.add_argument("--role-id", default="UNKNOWN_UNVERIFIED")
    parser.add_argument("--seat-id", default="UNKNOWN_UNVERIFIED")
    parser.add_argument("--access-profile-ref", default="UNKNOWN_UNVERIFIED")
    args = parser.parse_args()

    if not RUN_ID_PATTERN.fullmatch(args.run_id):
        print("HOLD_INIT_INVALID_RUN_ID")
        return 2

    project_root = Path(args.project_root).expanduser().resolve()
    if not project_root.is_dir():
        print("HOLD_INIT_PROJECT_ROOT_NOT_FOUND")
        return 2

    run_rel = Path("artifacts") / "8d-adi-workloop" / args.run_id
    run_dir = project_root / run_rel
    if run_dir.exists():
        print(f"HOLD_INIT_RUN_ALREADY_EXISTS:{run_dir}")
        return 2

    (run_dir / "evidence").mkdir(parents=True)
    (run_dir / "sensory-gates").mkdir()
    created_at = datetime.now().astimezone().isoformat(timespec="seconds")

    identity = {
        "natural_person_ref": args.natural_person_ref,
        "member_ref": args.member_ref,
        "xiaoj_identity_ref": args.xiaoj_ref,
        "role_id": args.role_id,
        "seat_id": args.seat_id,
        "access_profile_ref": args.access_profile_ref,
        "member_boundary": args.member_ref,
    }
    envelope = {
        "schema_version": SCHEMA_VERSION,
        "run_id": args.run_id,
        "lifecycle_state": "DRAFT_LOCAL",
        "created_at": created_at,
        "maximum_effect_class": args.effect_class,
        "identity_and_seat": identity,
        "product_output_contract": {
            "title": args.title,
            "one_sentence": args.intent,
            "acceptance_ids": ["AC-1"],
            "non_goals": [],
            "budget_fuse": {"limit": 2, "unit": "attempt"},
        },
        "d1_d8": {
            "D1": {
                "name": FIELD_NAMES["D1"],
                "state": "KNOWN",
                "value": args.intent,
                "evidence_label": "DEFINITION",
                "observation_status": "DECLARED_ONLY",
            },
            "D2": {
                "name": FIELD_NAMES["D2"],
                "state": "UNKNOWN",
                "value": "CURRENT_AND_TARGET_STATE_REQUIRE_EVIDENCE",
            },
            "D3": {
                "name": FIELD_NAMES["D3"],
                "state": "KNOWN",
                "value": {
                    "run_path": run_rel.as_posix(),
                    "logical_time": created_at,
                    "adi_resolution": "RANGE_UNRESOLVED",
                },
            },
            "D4": {
                "name": FIELD_NAMES["D4"],
                "state": "UNKNOWN",
                "value": "EVIDENCE_NOT_YET_ATTACHED",
            },
            "D5": {
                "name": FIELD_NAMES["D5"],
                "state": "KNOWN",
                "value": {
                    "effect_class": args.effect_class,
                    "action": "CANDIDATE_ARTIFACTS_ONLY",
                    "rollback": "REMOVE_ONLY_THIS_UNPROMOTED_RUN_DIRECTORY",
                    "forbidden": [
                        "ADI_WRITE",
                        "CANONICAL_MUTATION",
                        "DB_WRITE",
                        "DEPLOY",
                        "POINTER_MUTATION",
                        "ROLE_OR_SEAT_CHANGE",
                    ],
                },
            },
            "D6": {
                "name": FIELD_NAMES["D6"],
                "state": "NOT_REQUIRED",
                "value": {
                    "claimed": False,
                    "carrier_is_not_w7tp": True,
                    "technical_definition": "NOT_CLAIMED",
                },
            },
            "D7": {
                "name": FIELD_NAMES["D7"],
                "state": "KNOWN",
                "value": {
                    "open_findings": [],
                    "stop_on_high_or_critical": True,
                },
            },
            "D8": {
                "name": FIELD_NAMES["D8"],
                "state": "KNOWN",
                "value": {
                    "candidate_only": True,
                    "total_field_receiver": "TOTAL_FIELD_WORKLOOP_RECEIVER",
                    "total_field_decision": "NOT_REVIEWED",
                    "canonical_mutation": False,
                },
            },
        },
        "red_team": {
            "RED_TEAM_PRE_DEFINITION": "NOT_RUN",
            "RED_TEAM_PRE_ACTIVATION": "NOT_RUN",
            "RED_TEAM_POST_OPERATION": "NOT_RUN",
        },
        "source_hashes": {},
    }
    write_json(run_dir / "intent-envelope.json", envelope)

    order = f"""# 8D ADI Order: {args.title}

Run-ID: {args.run_id}
Lifecycle: DRAFT_LOCAL
Frozen: NOT_FROZEN
Owner-ref: {args.natural_person_ref}
Effect-class: {args.effect_class}

## D1 Intent
{args.intent}

## Verified facts
- [DEFINITION|DECLARED_ONLY] Founder/member intent supplied for this run | source: intent-envelope.json | hash: NONE

## Materials
- Allowed: user-authorized project evidence | licence: NOT_APPLICABLE | checked: {created_at}
- Excluded: raw credentials and protected member plaintext | reason: protected context boundary

## Build specification
- artifact directory = {run_rel.as_posix()} | source: intent-envelope.json#run_id

## Budget fuse
- Limit: 2 attempt
- Stop condition: stop at or before limit and preserve evidence

## Acceptance
- [ ] AC-1: replace this placeholder with one observable product result | evidence: evidence/ac-1.txt

## Non-goals
- live, protected, formal, ADI, canonical, pointer, identity, Seat, or database mutation

## D2-D8 projection
- D2 STATE: UNKNOWN_UNVERIFIED current and target state
- D3 COORDINATE: {run_rel.as_posix()} at {created_at}; ADI range unresolved
- D4 EVIDENCE: intent-envelope.json; further evidence required
- D5 EXECUTION_POLICY: candidate artifact only; rollback this unpromoted run directory
- D6 GENERATIVE_TRANSMISSION: NOT_CLAIMED; carrier is not W7TP
- D7 RED_TEAM_RISK_CONFINEMENT: three red-team event coordinates not yet run
- D8 ENVELOPE_AUTHORITY: candidate only; Total Field decision NOT_REVIEWED
"""
    (run_dir / "order.md").write_text(order, encoding="utf-8")

    init_event = {
        "event_id": "evt-0001",
        "logical_time": created_at,
        "event_type": "DECISION",
        "status": "OPEN",
        "evidence_label": "CANDIDATE",
        "observation_status": "DECLARED_ONLY",
        "source_ref": (run_rel / "intent-envelope.json").as_posix(),
        "source_sha256": "NONE",
        "summary": "Created a candidate-only 8D ADI workloop scaffold.",
        "authority_state": "DRAFT_LOCAL",
        "supersedes": [],
    }
    (run_dir / "decisions.jsonl").write_text(
        json.dumps(init_event, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (run_dir / "budget.jsonl").write_text("", encoding="utf-8")

    handoff = {
        "schema_version": SCHEMA_VERSION,
        "run_id": args.run_id,
        "destination_ref": "UNASSIGNED",
        "authority_state": "DRAFT_LOCAL",
        "running_work": [],
        "spent_assets": [],
        "dependencies": [],
        "open_debt": ["Replace the scaffold placeholders with observed evidence."],
        "evidence_refs": [(run_rel / "intent-envelope.json").as_posix()],
        "holds": [],
        "next_action": "Complete and freeze the order against current evidence.",
    }
    write_json(run_dir / "handoff.json", handoff)

    closeout = f"""# 8D ADI Closeout: {args.title}

Status: HOLD
Run-ID: {args.run_id}

## Acceptance
- [BLOCKED] AC-1: order remains an unfrozen scaffold | evidence: NONE | reason: acceptance and target evidence are not yet bound

## Independent functional verification
- Not run while the order is unfrozen | evidence: NONE

## Protected unchanged state
- ADI, canonical pointers, live services, databases, identity, Seat, and member data were not changed.

## Total Field
- Decision: NOT_REVIEWED

## Next
- Complete current-state evidence and freeze the order.
"""
    (run_dir / "closeout.md").write_text(closeout, encoding="utf-8")

    print(json.dumps({
        "state": "CREATED_CANDIDATE_WORKLOOP",
        "run_id": args.run_id,
        "path": str(run_dir),
        "lifecycle": "DRAFT_LOCAL",
        "canonical_mutation": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
