#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from d8_guard_eval import decide, insert_evaluation, load_alerts, matches  # noqa: E402

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


def main() -> int:
    parser = argparse.ArgumentParser(description="D8 Codex preflight gate")
    parser.add_argument("--task-name", required=True)
    parser.add_argument("--scope-json", required=True)
    parser.add_argument("--mode", choices=["sandbox", "land", "production", "review"], required=True)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()

    run_id = args.run_id or "D8_CODEX_PREFLIGHT_" + dt.datetime.now(dt.UTC).strftime("%Y%m%d_%H%M%S")
    try:
        scope = json.loads(args.scope_json)
        if not isinstance(scope, dict):
            raise ValueError("scope-json must decode to an object")
        alerts = load_alerts()
        matched = [alert for alert in alerts if matches(alert, scope)]
        decision, reason = decide(matched)
        decision, reason = apply_mode_policy(decision, reason, args.mode, scope)
        insert_evaluation(run_id, args.task_name, {"mode": args.mode, **scope}, matched, decision, reason)
        exit_code = EXIT_CODES[decision]
    except Exception as exc:  # report a non-secret operational error
        matched = []
        decision = "ERROR"
        reason = f"preflight error: {exc.__class__.__name__}"
        exit_code = EXIT_CODES[decision]

    summary = {
        "state": decision,
        "action": "D8_CODEX_PREFLIGHT_GATE",
        "run_id": run_id,
        "task_name": args.task_name,
        "mode": args.mode,
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
    report = write_report(summary)
    summary["report"] = report.relative_to(ROOT).as_posix()

    print(f"STATE={decision}")
    print("ACTION=D8_CODEX_PREFLIGHT_GATE")
    print(f"TASK_NAME={args.task_name}")
    print(f"MODE={args.mode}")
    print(f"DECISION={decision}")
    print(f"EXIT_CODE={exit_code}")
    print(f"MATCHED_ALERTS_COUNT={len(matched)}")
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
