#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RANK = {"PASS": 0, "INFO": 1, "WARN": 2, "HOLD": 3, "BLOCK": 4}


def run_psql(sql: str) -> str:
    cmd = [
        "docker",
        "compose",
        "--env-file",
        ".env.d8.local",
        "-f",
        "compose.d8.yml",
        "exec",
        "-T",
        "d8_db",
        "psql",
        "-U",
        "taiji",
        "-d",
        "taiji_d8",
        "-At",
        "-c",
        sql,
    ]
    return subprocess.check_output(cmd, cwd=ROOT, text=True).strip()


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def load_alerts() -> list[dict]:
    raw = run_psql(
        """
        SELECT COALESCE(jsonb_agg(to_jsonb(a)), '[]'::jsonb)
        FROM (
          SELECT id, run_id, event_type, alert_level, title, summary,
                 evidence_ref, reverse_refs, affected_paths
          FROM d8_active_possible_alerts
          ORDER BY created_at
        ) a;
        """
    )
    return json.loads(raw or "[]")


def matches(alert: dict, scope: dict) -> bool:
    evidence = alert.get("evidence_ref") or {}
    alert_id = str(alert.get("event_type") or "")
    text = " ".join(
        str(x).lower()
        for x in [
            alert.get("event_type"),
            alert.get("title"),
            alert.get("summary"),
            evidence.get("pattern"),
            evidence.get("possible_error"),
            evidence.get("correct_action"),
            json.dumps(alert.get("reverse_refs") or [], ensure_ascii=False),
            json.dumps(alert.get("affected_paths") or [], ensure_ascii=False),
        ]
    )
    if scope.get("human_review_required") and alert_id == "D8_ALERT_HUMAN_REVIEW_REQUIRED":
        return True
    if scope.get("pre_existing_non_d8_diff") and alert_id == "D8_ALERT_PRE_EXISTING_NON_D8_DIFF":
        return True
    if (
        "rerun_ingestion" in str(scope.get("request", "")).lower()
        and alert_id == "D8_ALERT_PHASE1_BASELINE_READY"
    ):
        return True
    if scope.get("d8_memory_count") and alert_id == "D8_ALERT_PHASE1_BASELINE_READY":
        return True
    if scope.get("file") and str(scope["file"]).lower() in text and "pre-existing" in text:
        return alert_id == "D8_ALERT_PRE_EXISTING_NON_D8_DIFF"
    return False


def decide(matched: list[dict]) -> tuple[str, str]:
    if not matched:
        return "PASS", "no active possible_alert matched task scope"
    decision = max((a.get("alert_level", "INFO") for a in matched), key=lambda level: RANK.get(level, 0))
    return decision, "matched active possible_alerts: " + ", ".join(a.get("event_type", "") for a in matched)


def insert_evaluation(run_id: str, task_name: str, scope: dict, matched: list[dict], decision: str, reason: str) -> None:
    payload = {
        "scope": scope,
        "matched_alerts": [
            {
                "id": a.get("id"),
                "alert_id": a.get("event_type"),
                "alert_level": a.get("alert_level"),
            }
            for a in matched
        ],
    }
    sql = f"""
    INSERT INTO d8_guard_evaluations (
      run_id, task_name, task_scope, matched_alerts, decision, reason,
      executable, pollution_guard
    )
    VALUES (
      {sql_literal(run_id)},
      {sql_literal(task_name)},
      {sql_literal(json.dumps(scope, ensure_ascii=False))}::jsonb,
      {sql_literal(json.dumps(payload["matched_alerts"], ensure_ascii=False))}::jsonb,
      {sql_literal(decision)},
      {sql_literal(reason)},
      false,
      true
    );
    """
    run_psql(sql)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate task scope against D8 possible alerts")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--task-name", required=True)
    parser.add_argument("--scope-json", required=True)
    args = parser.parse_args()

    scope = json.loads(args.scope_json)
    alerts = load_alerts()
    matched = [alert for alert in alerts if matches(alert, scope)]
    decision, reason = decide(matched)
    insert_evaluation(args.run_id, args.task_name, scope, matched, decision, reason)
    summary = {
        "run_id": args.run_id,
        "task_name": args.task_name,
        "decision": decision,
        "reason": reason,
        "matched_alerts": [
            {"alert_id": a.get("event_type"), "alert_level": a.get("alert_level")}
            for a in matched
        ],
        "executable": False,
        "pollution_guard": True,
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
