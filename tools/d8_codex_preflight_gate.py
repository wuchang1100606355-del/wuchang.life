#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from d8_guard_eval import (  # noqa: E402
    canonical_json,
    decide,
    persist_evaluation,
    load_alerts,
    matches,
    prepare_evaluation,
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
    out = (root / "runtime" / "d8" / "preflight" / run_id).resolve()
    if root == source:
        raise RuntimeError("read-only preflight cannot run in source worktree")
    if out != root and root not in out.parents:
        raise RuntimeError("read-only preflight output escaped current worktree")
    if out == source or source in out.parents:
        raise RuntimeError("read-only preflight output entered source worktree")
    return out


def write_readonly_evidence(run_id: str, candidate: dict, validation: dict, summary: dict) -> Path:
    out = readonly_output_dir(run_id)
    out.mkdir(parents=True, exist_ok=False)
    candidate_hash = candidate["envelope"]["candidate_sha256"]
    (out / "canonical_evaluation_candidate.json").write_text(
        canonical_json(candidate) + "\n", encoding="utf-8"
    )
    (out / "WOULD_INSERT_SHA256").write_text(candidate_hash + "\n", encoding="utf-8")
    report = {
        "state": validation["state"], "checks": validation["checks"],
        "D8_LOCAL_DB_WRITE": False, "PRODUCTION_PERSISTENCE": "NOT_RUN",
        "PREFLIGHT_MODE": "READ_ONLY",
    }
    (out / "validation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    verifier = {
        "VERIFIER_RESULT": validation["state"], "WOULD_INSERT_SHA256": candidate_hash,
        "decision": summary["decision"], "D8_LOCAL_DB_WRITE": False,
        "PRODUCTION_PERSISTENCE": "NOT_RUN", "PREFLIGHT_MODE": "READ_ONLY",
    }
    (out / "verifier_result.json").write_text(
        json.dumps(verifier, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return out


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
    try:
        scope = json.loads(args.scope_json)
        if not isinstance(scope, dict):
            raise ValueError("scope-json must decode to an object")
        alerts = load_alerts(read_only=args.preflight_mode == "READ_ONLY")
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
    readonly_dir = None
    if args.preflight_mode == "READ_ONLY" and candidate is not None and validation is not None:
        readonly_dir = write_readonly_evidence(run_id, candidate, validation, summary)
        summary["report"] = (readonly_dir / "validation_report.json").relative_to(ROOT).as_posix()
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
        print(f"PREFLIGHT={'PASS_READ_ONLY' if validation and validation['state'] == 'PASS' else 'HOLD'}")
        print(f"VERIFIER_RESULT={validation['state'] if validation else 'HOLD'}")
        print(f"WOULD_INSERT_SHA256={candidate['envelope']['candidate_sha256'] if candidate else 'false'}")
        print(f"OUTPUT_ROOT={readonly_dir.relative_to(ROOT).as_posix() if readonly_dir else 'false'}")
        print("D8_LOCAL_DB_WRITE=false\nPRODUCTION_PERSISTENCE=NOT_RUN")
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
