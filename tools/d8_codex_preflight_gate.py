#!/usr/bin/env python3
import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from d8_guard_eval import (  # noqa: E402
    canonical_json,
    decide,
    evaluation_insert_projection,
    evaluation_insert_projection_sha256,
    persist_evaluation,
    load_alerts,
    matches,
    prepare_evaluation,
    readonly_sql_audit,
    reset_readonly_sql_audit,
    validate_evaluation,
)

EXIT_CODES = {
    "PASS": 0,
    "INFO": 0,
    "WARN": 10,
    "HOLD": 20,
    "BLOCK": 30,
    "ERROR": 40,
}


def apply_mode_policy(decision: str, reason: str, mode: str, scope: dict) -> tuple[str, str]:
    explicit_release = scope.get("explicit_human_release") is True
    if mode == "production" and not explicit_release:
        return "HOLD", reason + "; production mode requires explicit_human_release=true"
    if mode == "land" and decision == "WARN" and not explicit_release:
        return "HOLD", reason + "; land mode escalates WARN to HOLD without explicit human release"
    return decision, reason


def write_report(summary: dict) -> Path:
    report_dir = ROOT / "runtime/d8_db/reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d_%H%M%S")
    path = report_dir / f"D8_CODEX_PREFLIGHT_{stamp}.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def source_repo_root() -> Path:
    common = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "--git-common-dir"], text=True
    ).strip()
    common_path = Path(common)
    if not common_path.is_absolute():
        common_path = ROOT / common_path
    return common_path.resolve().parent


def readonly_output_dir(run_id: str) -> Path:
    root = ROOT.resolve()
    source = source_repo_root()
    base = (root / "runtime" / "d8" / "preflight").resolve()
    out = (base / run_id).resolve()
    if root == source:
        raise RuntimeError("read-only preflight cannot run in source worktree")
    if out != root and root not in out.parents:
        raise RuntimeError("read-only preflight output escaped current worktree")
    if out == source or source in out.parents:
        raise RuntimeError("read-only preflight output entered source worktree")
    if out.parent != base:
        raise RuntimeError("read-only preflight run id escaped its output directory")
    return out


def readonly_hashes(candidate: dict) -> dict:
    candidate_packet = canonical_json(candidate).encode("utf-8")
    return {
        "candidate_envelope_sha256": candidate["envelope"]["candidate_sha256"],
        "candidate_file_sha256": hashlib.sha256(candidate_packet).hexdigest(),
        "would_insert_sha256": evaluation_insert_projection_sha256(candidate),
    }


def validate_readonly_audit(audit: dict) -> None:
    if audit.get("transaction_read_only_confirmed") is not True:
        raise RuntimeError("database read-only protection was not confirmed")
    queries = audit.get("queries")
    if audit.get("query_count") != 1 or not isinstance(queries, list) or len(queries) != 1:
        raise RuntimeError("read-only preflight must execute exactly one allowlisted query")
    query = queries[0]
    if query.get("statement_class") != "SELECT" or not re.fullmatch(
        r"[0-9a-f]{64}", str(query.get("sql_sha256") or "")
    ):
        raise RuntimeError("read-only query audit record is invalid")
    if audit.get("mutation_count") != 0:
        raise RuntimeError("SQL mutation was observed in read-only preflight")
    if audit.get("xid_assigned") is not False:
        raise RuntimeError("transaction id was assigned in read-only preflight")


def readonly_verifier_result(validation: dict | None, summary: dict, *, evidence_ready: bool) -> str:
    if (
        evidence_ready
        and validation is not None
        and validation.get("state") == "PASS"
        and summary.get("decision") in {"PASS", "INFO"}
        and summary.get("exit_code") == 0
    ):
        return "PASS"
    return "HOLD"


def write_readonly_evidence(
    run_id: str,
    candidate: dict,
    validation: dict,
    summary: dict,
    sql_audit: dict,
) -> dict:
    out = readonly_output_dir(run_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    staging = out.parent / f".{out.name}.tmp"
    if out.exists() or staging.exists():
        raise FileExistsError("read-only evidence target or staging directory already exists")
    staging.mkdir(parents=False, exist_ok=False)
    hashes = readonly_hashes(candidate)
    projection = evaluation_insert_projection(candidate)
    verifier_result = readonly_verifier_result(validation, summary, evidence_ready=True)
    structural_validation = validation.get("state", "HOLD")
    try:
        (staging / "canonical_evaluation_candidate.json").write_text(
            canonical_json(candidate), encoding="utf-8"
        )
        (staging / "canonical_would_insert_projection.json").write_text(
            canonical_json(projection), encoding="utf-8"
        )
        (staging / "CANDIDATE_ENVELOPE_SHA256").write_text(
            hashes["candidate_envelope_sha256"] + "\n", encoding="utf-8"
        )
        (staging / "CANDIDATE_FILE_SHA256").write_text(
            hashes["candidate_file_sha256"] + "\n", encoding="utf-8"
        )
        (staging / "WOULD_INSERT_SHA256").write_text(
            hashes["would_insert_sha256"] + "\n", encoding="utf-8"
        )
        audit_report = {
            **sql_audit,
            "READ_ONLY_CONFIRMED": True,
            "SQL_MUTATION_COUNT": 0,
            "XID_ASSIGNED": False,
            "D8_LOCAL_DB_WRITE": False,
            "PRODUCTION_PERSISTENCE": "NOT_RUN",
        }
        (staging / "sql_readonly_audit.json").write_text(
            json.dumps(audit_report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        report = {
            "state": verifier_result,
            "STRUCTURAL_VALIDATION": structural_validation,
            "PREFLIGHT": "PASS_READ_ONLY" if verifier_result == "PASS" else "HOLD",
            "checks": validation["checks"],
            "D8_LOCAL_DB_WRITE": False, "PRODUCTION_PERSISTENCE": "NOT_RUN",
            "PREFLIGHT_MODE": "READ_ONLY",
            **{key.upper(): value for key, value in hashes.items()},
            "READ_ONLY_CONFIRMED": True,
            "SQL_MUTATION_COUNT": 0,
            "XID_ASSIGNED": False,
        }
        (staging / "validation_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        verifier = {
            "VERIFIER_RESULT": verifier_result,
            "STRUCTURAL_VALIDATION": structural_validation,
            **{key.upper(): value for key, value in hashes.items()},
            "decision": summary["decision"], "D8_LOCAL_DB_WRITE": False,
            "PRODUCTION_PERSISTENCE": "NOT_RUN", "PREFLIGHT_MODE": "READ_ONLY",
            "READ_ONLY_CONFIRMED": True,
            "SQL_MUTATION_COUNT": 0,
            "XID_ASSIGNED": False,
        }
        (staging / "verifier_result.json").write_text(
            json.dumps(verifier, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        staging.rename(out)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return {"output_dir": out, **hashes}


def main() -> int:
    parser = argparse.ArgumentParser(description="D8 Codex preflight gate")
    parser.add_argument("--task-name", required=True)
    parser.add_argument("--scope-json", required=True)
    parser.add_argument("--mode", choices=["sandbox", "land", "production", "review"], required=True)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--preflight-mode", choices=["PERSIST", "READ_ONLY"], default="PERSIST")
    args = parser.parse_args()

    run_id = args.run_id or "D8_CODEX_PREFLIGHT_" + dt.datetime.now(dt.UTC).strftime("%Y%m%d_%H%M%S")
    candidate = None
    validation = None
    sql_audit = {}
    if args.preflight_mode == "READ_ONLY":
        reset_readonly_sql_audit()
    try:
        scope = json.loads(args.scope_json)
        if not isinstance(scope, dict):
            raise ValueError("scope-json must decode to an object")
        alerts = load_alerts(read_only=args.preflight_mode == "READ_ONLY")
        if args.preflight_mode == "READ_ONLY":
            sql_audit = readonly_sql_audit()
            validate_readonly_audit(sql_audit)
        matched = [alert for alert in alerts if matches(alert, scope)]
        decision, reason = decide(matched)
        decision, reason = apply_mode_policy(decision, reason, args.mode, scope)
        evaluation_scope = {"mode": args.mode, **scope}
        candidate = prepare_evaluation(run_id, args.task_name, evaluation_scope, matched, decision, reason)
        validation = validate_evaluation(candidate)
        if validation["state"] != "PASS":
            raise ValueError("evaluation candidate validation failed")
        if args.preflight_mode == "PERSIST":
            persist_evaluation(candidate)
        exit_code = EXIT_CODES[decision]
    except Exception as exc:  # report a non-secret operational error
        matched = []
        decision = "HOLD" if args.preflight_mode == "READ_ONLY" else "ERROR"
        reason = f"preflight error: {exc.__class__.__name__}"
        exit_code = EXIT_CODES[decision]

    summary = {
        "state": decision,
        "action": "D8_CODEX_PREFLIGHT_GATE",
        "run_id": run_id,
        "task_name": args.task_name,
        "mode": args.mode,
        "preflight_mode": args.preflight_mode,
        "decision": decision,
        "exit_code": exit_code,
        "matched_alerts_count": len(matched),
        "matched_alerts": [
            {"alert_id": alert.get("event_type"), "alert_level": alert.get("alert_level")}
            for alert in matched
        ],
        "reason": reason,
        "safety_flags": {
            "SECRET_READ": False,
            "PRODUCTION_DB_WRITE": False,
            "D8_LOCAL_DB_WRITE": args.preflight_mode == "PERSIST",
            "SERVICE_RESTART": False,
            "DEPLOY": False,
            "EXTERNAL_API_CALL": False,
            "EMBEDDING_GENERATED": False,
            "POLLUTION_GUARD": True,
            "REVERSE_INDEX_ISOLATION": True,
            "EXECUTABLE_ALERTS": False,
        },
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
    }
    readonly_evidence = None
    if args.preflight_mode == "READ_ONLY" and candidate is not None and validation is not None:
        try:
            readonly_evidence = write_readonly_evidence(
                run_id, candidate, validation, summary, sql_audit
            )
            summary["report"] = (
                readonly_evidence["output_dir"] / "validation_report.json"
            ).relative_to(ROOT).as_posix()
        except Exception as exc:
            decision = "HOLD"
            exit_code = EXIT_CODES[decision]
            reason = f"evidence write error: {exc.__class__.__name__}"
            summary.update({
                "state": decision,
                "decision": decision,
                "exit_code": exit_code,
                "reason": reason,
            })
    elif args.preflight_mode == "PERSIST":
        report = write_report(summary)
        summary["report"] = report.relative_to(ROOT).as_posix()

    print(f"STATE={decision}")
    print("ACTION=D8_CODEX_PREFLIGHT_GATE")
    print(f"TASK_NAME={args.task_name}")
    print(f"MODE={args.mode}")
    print(f"DECISION={decision}")
    print(f"EXIT_CODE={exit_code}")
    print(f"MATCHED_ALERTS_COUNT={len(matched)}")
    print(f"PREFLIGHT_MODE={args.preflight_mode}")
    if args.preflight_mode == "READ_ONLY":
        hashes = readonly_hashes(candidate) if candidate else {
            "candidate_envelope_sha256": "false",
            "candidate_file_sha256": "false",
            "would_insert_sha256": "false",
        }
        structural_validation = validation.get("state", "HOLD") if validation else "HOLD"
        verifier_result = readonly_verifier_result(
            validation, summary, evidence_ready=readonly_evidence is not None
        )
        print(f"PREFLIGHT={'PASS_READ_ONLY' if verifier_result == 'PASS' else 'HOLD'}")
        print(f"VERIFIER_RESULT={verifier_result}")
        print(f"STRUCTURAL_VALIDATION={structural_validation}")
        print(f"CANDIDATE_ENVELOPE_SHA256={hashes['candidate_envelope_sha256']}")
        print(f"CANDIDATE_FILE_SHA256={hashes['candidate_file_sha256']}")
        print(f"WOULD_INSERT_SHA256={hashes['would_insert_sha256']}")
        print(
            "OUTPUT_ROOT="
            + (
                readonly_evidence["output_dir"].relative_to(ROOT).as_posix()
                if readonly_evidence is not None
                else "false"
            )
        )
        read_only_confirmed = sql_audit.get("transaction_read_only_confirmed") is True
        print(f"READ_ONLY_CONFIRMED={str(read_only_confirmed).upper()}")
        if read_only_confirmed:
            print(f"SQL_MUTATION_COUNT={sql_audit.get('mutation_count', 'UNKNOWN')}")
            print(f"XID_ASSIGNED={str(sql_audit.get('xid_assigned')).upper()}")
        else:
            print("SQL_MUTATION_COUNT=UNKNOWN")
            print("XID_ASSIGNED=UNKNOWN")
        print("D8_LOCAL_DB_WRITE=false\nPRODUCTION_PERSISTENCE=NOT_RUN")
    print(f"REPORT={summary.get('report', 'false')}")
    print("SECRET_READ=FALSE")
    print("PRODUCTION_DB_WRITE=FALSE")
    print("SERVICE_RESTART=FALSE")
    print("DEPLOY=FALSE")
    print("EXTERNAL_API_CALL=FALSE")
    print("EMBEDDING_GENERATED=FALSE")
    print("POLLUTION_GUARD=TRUE")
    print("REVERSE_INDEX_ISOLATION=TRUE")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
