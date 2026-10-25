#!/usr/bin/env python3
"""Validate an 8D ADI evidence workloop without promoting its authority."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


SCHEMA_VERSION = "w7tp-8d-adi-evidence-workloop/1.0"
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
LIFECYCLES = {"DRAFT_LOCAL", "CANDIDATE_FOR_TOTAL_FIELD_REVIEW"}
EFFECT_CLASSES = {f"E{number}" for number in range(6)}
EVIDENCE_LABELS = {"FACT", "DEFINITION", "INFERENCE", "CLAIM", "CANDIDATE", "HOLD"}
OBSERVATION_STATUSES = {
    "OBSERVED_DIRECT",
    "OBSERVED_AUTHORIZED_API",
    "DERIVED_FROM_OBSERVED",
    "DECLARED_ONLY",
    "STALE_EVIDENCE",
    "BLOCKED_BY_AUTHORITY",
    "UNREACHABLE",
    "UNKNOWN_UNVERIFIED",
}
EVENT_TYPES = {
    "ORDER_FROZEN",
    "ORDER_AMENDED",
    "DECISION",
    "CORRECTION",
    "REJECTION",
    "DIAGNOSIS_STAGE",
    "GATE_OPENED",
    "GATE_DISPOSITION",
    "HOLD",
    "AUTHORIZATION_REQUEST",
    "HANDOFF",
    "CLOSEOUT",
}
FINAL_STATUSES = {"DONE", "CLOSED_FAILED", "STOPPED", "GATE_HOLD", "HOLD"}
REQUIRED_FILES = {
    "intent-envelope.json",
    "order.md",
    "decisions.jsonl",
    "budget.jsonl",
    "handoff.json",
    "closeout.md",
}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
AC_ORDER_PATTERN = re.compile(r"^- \[[ xX]\] (AC-[A-Za-z0-9._-]+):", re.MULTILINE)
AC_CLOSE_PATTERN = re.compile(
    r"^- \[(PASS|FAIL|BLOCKED)\] (AC-[A-Za-z0-9._-]+):.*?\| evidence: ([^|\r\n]+)",
    re.MULTILINE,
)
INDEPENDENT_PATTERN = re.compile(
    r"Independent functional verification:.*?\| evidence: ([^|\r\n]+)",
    re.IGNORECASE,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path, errors: list[str]) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"INVALID_JSON:{path.name}:{exc}")
        return {}


def resolve_ref(project_root: Path, run_dir: Path, reference: str) -> Path | None:
    value = reference.strip().strip(chr(96))
    if not value or value == "NONE" or "://" in value:
        return None
    value = value.split("#", 1)[0]
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    project_candidate = project_root / candidate
    if project_candidate.exists():
        return project_candidate
    return run_dir / candidate


def validate(run_dir: Path) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    run_dir = run_dir.expanduser().resolve()
    project_root = run_dir.parents[2] if len(run_dir.parents) >= 3 else run_dir.parent

    if not run_dir.is_dir():
        return {
            "result": "HOLD_WORKLOOP_INVALID",
            "run_dir": str(run_dir),
            "errors": ["RUN_DIRECTORY_NOT_FOUND"],
            "warnings": [],
            "canonical_mutation": False,
        }

    missing = sorted(name for name in REQUIRED_FILES if not (run_dir / name).is_file())
    errors.extend(f"MISSING_REQUIRED_FILE:{name}" for name in missing)

    envelope_obj = read_json(run_dir / "intent-envelope.json", errors) if not missing else {}
    envelope = envelope_obj if isinstance(envelope_obj, dict) else {}
    run_id = envelope.get("run_id")
    lifecycle = envelope.get("lifecycle_state")
    final_status = "UNKNOWN"
    total_field_decision = "NOT_REVIEWED"

    if envelope.get("schema_version") != SCHEMA_VERSION:
        errors.append("INVALID_SCHEMA_VERSION")
    if run_id != run_dir.name:
        errors.append("RUN_ID_PATH_MISMATCH")
    if lifecycle not in LIFECYCLES:
        errors.append("INVALID_LIFECYCLE")
    if envelope.get("maximum_effect_class") not in EFFECT_CLASSES:
        errors.append("INVALID_EFFECT_CLASS")

    identity = envelope.get("identity_and_seat")
    identity_keys = {
        "natural_person_ref",
        "member_ref",
        "xiaoj_identity_ref",
        "role_id",
        "seat_id",
        "access_profile_ref",
        "member_boundary",
    }
    if not isinstance(identity, dict):
        errors.append("IDENTITY_AND_SEAT_NOT_OBJECT")
    else:
        for key in sorted(identity_keys):
            if key not in identity or not isinstance(identity[key], str) or not identity[key]:
                errors.append(f"IDENTITY_FIELD_MISSING:{key}")

    fields = envelope.get("d1_d8")
    if not isinstance(fields, dict):
        errors.append("D1_D8_NOT_OBJECT")
        fields = {}
    for key, expected_name in FIELD_NAMES.items():
        field = fields.get(key)
        if not isinstance(field, dict):
            errors.append(f"MISSING_FIELD:{key}")
            continue
        if field.get("name") != expected_name:
            errors.append(f"INVALID_FIELD_NAME:{key}")

    d6_value = fields.get("D6", {}).get("value", {}) if isinstance(fields.get("D6"), dict) else {}
    if not isinstance(d6_value, dict):
        errors.append("D6_VALUE_NOT_OBJECT")
    elif d6_value.get("claimed") is True:
        errors.append("D6_W7TP_CLAIM_REQUIRES_SEPARATE_PROTOCOL_PROOF")

    d8_value = fields.get("D8", {}).get("value", {}) if isinstance(fields.get("D8"), dict) else {}
    if not isinstance(d8_value, dict):
        errors.append("D8_VALUE_NOT_OBJECT")
    else:
        total_field_decision = str(d8_value.get("total_field_decision", "NOT_REVIEWED"))
        if d8_value.get("candidate_only") is not True:
            errors.append("D8_MUST_REMAIN_CANDIDATE_ONLY")
        if d8_value.get("canonical_mutation") is not False:
            errors.append("D8_CANONICAL_MUTATION_FORBIDDEN")
        if not d8_value.get("total_field_receiver"):
            errors.append("D8_TOTAL_FIELD_RECEIVER_MISSING")
        if total_field_decision not in {"NOT_REVIEWED", "HOLD"}:
            errors.append("TOTAL_FIELD_RECEIPT_CANNOT_BE_SELF_ASSERTED")

    order_text = ""
    if (run_dir / "order.md").is_file():
        order_text = (run_dir / "order.md").read_text(encoding="utf-8")
    order_acceptance_ids = AC_ORDER_PATTERN.findall(order_text)
    if not order_acceptance_ids:
        errors.append("ORDER_HAS_NO_ACCEPTANCE_ID")
    if len(order_acceptance_ids) != len(set(order_acceptance_ids)):
        errors.append("ORDER_DUPLICATE_ACCEPTANCE_ID")

    events: list[dict[str, object]] = []
    event_ids: set[str] = set()
    decision_path = run_dir / "decisions.jsonl"
    if decision_path.is_file():
        for line_number, raw_line in enumerate(decision_path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw_line.strip():
                continue
            try:
                event = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                errors.append(f"INVALID_DECISION_JSONL:{line_number}:{exc}")
                continue
            if not isinstance(event, dict):
                errors.append(f"DECISION_NOT_OBJECT:{line_number}")
                continue
            event_id = event.get("event_id")
            if not isinstance(event_id, str) or not event_id:
                errors.append(f"DECISION_EVENT_ID_MISSING:{line_number}")
            elif event_id in event_ids:
                errors.append(f"DECISION_EVENT_ID_DUPLICATE:{event_id}")
            else:
                event_ids.add(event_id)
            if event.get("event_type") not in EVENT_TYPES:
                errors.append(f"DECISION_EVENT_TYPE_INVALID:{line_number}")
            if event.get("evidence_label") not in EVIDENCE_LABELS:
                errors.append(f"DECISION_EVIDENCE_LABEL_INVALID:{line_number}")
            if event.get("observation_status") not in OBSERVATION_STATUSES:
                errors.append(f"DECISION_OBSERVATION_STATUS_INVALID:{line_number}")
            if not isinstance(event.get("logical_time"), str) or not event.get("logical_time"):
                errors.append(f"DECISION_LOGICAL_TIME_MISSING:{line_number}")
            if not isinstance(event.get("supersedes"), list):
                errors.append(f"DECISION_SUPERSEDES_NOT_ARRAY:{line_number}")
            source_ref = event.get("source_ref")
            source_hash = event.get("source_sha256")
            if not isinstance(source_ref, str) or not source_ref:
                errors.append(f"DECISION_SOURCE_REF_MISSING:{line_number}")
            elif source_hash != "NONE":
                if not isinstance(source_hash, str) or not SHA256_PATTERN.fullmatch(source_hash):
                    errors.append(f"DECISION_SOURCE_HASH_INVALID:{line_number}")
                else:
                    target = resolve_ref(project_root, run_dir, source_ref)
                    if target is None or not target.is_file():
                        errors.append(f"DECISION_SOURCE_NOT_FOUND:{line_number}:{source_ref}")
                    elif sha256_file(target) != source_hash:
                        errors.append(f"DECISION_SOURCE_HASH_MISMATCH:{line_number}:{source_ref}")
            events.append(event)

    frozen_events = [event for event in events if event.get("event_type") == "ORDER_FROZEN"]
    if lifecycle == "CANDIDATE_FOR_TOTAL_FIELD_REVIEW":
        if not frozen_events:
            errors.append("CANDIDATE_LIFECYCLE_WITHOUT_ORDER_FROZEN")
        elif not any(event.get("source_sha256") == sha256_file(run_dir / "order.md") for event in frozen_events):
            errors.append("NO_ORDER_FROZEN_EVENT_MATCHES_CURRENT_ORDER")

    budget_path = run_dir / "budget.jsonl"
    if budget_path.is_file():
        for line_number, raw_line in enumerate(budget_path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw_line.strip():
                continue
            try:
                item = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                errors.append(f"INVALID_BUDGET_JSONL:{line_number}:{exc}")
                continue
            if not isinstance(item, dict) or not isinstance(item.get("amount"), (int, float)):
                errors.append(f"INVALID_BUDGET_EVENT:{line_number}")

    handoff_obj = read_json(run_dir / "handoff.json", errors) if (run_dir / "handoff.json").is_file() else {}
    handoff = handoff_obj if isinstance(handoff_obj, dict) else {}
    for key in ("running_work", "spent_assets", "dependencies", "open_debt", "evidence_refs", "holds"):
        if not isinstance(handoff.get(key), list):
            errors.append(f"HANDOFF_ARRAY_MISSING:{key}")
    if not isinstance(handoff.get("next_action"), str) or not handoff.get("next_action"):
        errors.append("HANDOFF_NEXT_ACTION_MISSING")

    closeout_text = ""
    if (run_dir / "closeout.md").is_file():
        closeout_text = (run_dir / "closeout.md").read_text(encoding="utf-8")
    status_match = re.search(r"^Status: ([A-Z_]+)$", closeout_text, re.MULTILINE)
    if not status_match or status_match.group(1) not in FINAL_STATUSES:
        errors.append("CLOSEOUT_STATUS_INVALID")
    else:
        final_status = status_match.group(1)

    close_records = AC_CLOSE_PATTERN.findall(closeout_text)
    close_by_id = {ac_id: (status, evidence.strip()) for status, ac_id, evidence in close_records}
    for ac_id in order_acceptance_ids:
        if ac_id not in close_by_id:
            errors.append(f"CLOSEOUT_ACCEPTANCE_MISSING:{ac_id}")
    if final_status == "DONE":
        if lifecycle != "CANDIDATE_FOR_TOTAL_FIELD_REVIEW":
            errors.append("DONE_REQUIRES_FROZEN_CANDIDATE_LIFECYCLE")
        for ac_id in order_acceptance_ids:
            status, evidence_ref = close_by_id.get(ac_id, ("MISSING", "NONE"))
            if status != "PASS":
                errors.append(f"DONE_ACCEPTANCE_NOT_PASS:{ac_id}")
            evidence_path = resolve_ref(project_root, run_dir, evidence_ref)
            if evidence_path is None or not evidence_path.is_file():
                errors.append(f"DONE_ACCEPTANCE_EVIDENCE_NOT_FOUND:{ac_id}:{evidence_ref}")
        independent_match = INDEPENDENT_PATTERN.search(closeout_text)
        if not independent_match:
            errors.append("DONE_INDEPENDENT_VERIFICATION_MISSING")
        else:
            independent_ref = independent_match.group(1).strip()
            independent_path = resolve_ref(project_root, run_dir, independent_ref)
            if independent_path is None or not independent_path.is_file():
                errors.append(f"DONE_INDEPENDENT_EVIDENCE_NOT_FOUND:{independent_ref}")

    red_team = envelope.get("red_team")
    if not isinstance(red_team, dict):
        errors.append("RED_TEAM_NOT_OBJECT")
    else:
        for coordinate in (
            "RED_TEAM_PRE_DEFINITION",
            "RED_TEAM_PRE_ACTIVATION",
            "RED_TEAM_POST_OPERATION",
        ):
            if coordinate not in red_team:
                errors.append(f"RED_TEAM_COORDINATE_MISSING:{coordinate}")
            elif final_status == "DONE" and red_team[coordinate] in {"NOT_RUN", "", None}:
                errors.append(f"DONE_RED_TEAM_NOT_RECORDED:{coordinate}")

    gates_root = run_dir / "sensory-gates"
    if gates_root.is_dir():
        for gate_path in sorted(gates_root.glob("*/gate.json")):
            gate_obj = read_json(gate_path, errors)
            gate = gate_obj if isinstance(gate_obj, dict) else {}
            review_files = gate.get("review_files")
            if not isinstance(review_files, list) or not review_files:
                errors.append(f"GATE_REVIEW_BATCH_EMPTY:{gate_path.parent.name}")
                continue
            for item in review_files:
                if not isinstance(item, dict):
                    errors.append(f"GATE_REVIEW_ITEM_INVALID:{gate_path.parent.name}")
                    continue
                file_path = resolve_ref(project_root, run_dir, str(item.get("path", "")))
                claimed_hash = item.get("sha256")
                if file_path is None or not file_path.is_file():
                    errors.append(f"GATE_REVIEW_FILE_NOT_FOUND:{gate_path.parent.name}")
                elif not isinstance(claimed_hash, str) or sha256_file(file_path) != claimed_hash:
                    errors.append(f"GATE_REVIEW_HASH_MISMATCH:{gate_path.parent.name}")
            if gate.get("status") == "APPROVED":
                for key in ("reviewer_identity_ref", "disposition", "approved_scope", "reviewed_at"):
                    if not gate.get(key):
                        errors.append(f"GATE_APPROVAL_FIELD_MISSING:{gate_path.parent.name}:{key}")

    if final_status == "DONE" and errors:
        warnings.append("DONE_DECLARATION_REJECTED_BY_VALIDATOR")
    if errors:
        result = "HOLD_WORKLOOP_INVALID"
    elif final_status == "DONE":
        result = "PASS_WORKLOOP_VALID"
    else:
        result = "PASS_WORKLOOP_DRAFT_VALID"

    return {
        "result": result,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "lifecycle_state": lifecycle,
        "closeout_status": final_status,
        "total_field_decision": total_field_decision,
        "canonical_mutation": False,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    parser.add_argument("--report")
    args = parser.parse_args()

    report = validate(Path(args.run_dir))
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        Path(args.report).write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if str(report["result"]).startswith("PASS_") else 2


if __name__ == "__main__":
    sys.exit(main())
