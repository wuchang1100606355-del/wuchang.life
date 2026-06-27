#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


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


def write_report(summary: dict) -> Path:
    out_dir = ROOT / "runtime/d8_db/reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / ("D8_REDTEAM_WRITEBACK_" + dt.datetime.now(dt.UTC).strftime("%Y%m%d_%H%M%S") + ".json")
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def insert_event(args, evidence: dict, reverse_refs: list, affected_paths: list) -> str:
    payload = {
        "run_id": args.run_id,
        "source": "d8_redteam_writeback",
        "event_type": args.event_type,
        "alert_level": args.alert_level,
        "title": args.title,
        "summary": args.summary,
        "evidence_ref": evidence,
        "reverse_refs": reverse_refs,
        "affected_paths": affected_paths,
        "candidate_rule": args.candidate_rule,
        "promotion_status": "candidate",
    }
    sql = f"SELECT d8_register_redteam_event({sql_literal(json.dumps(payload, ensure_ascii=False))}::jsonb);"
    return run_psql(sql)


def maybe_insert_possible_alert(args, evidence: dict, reverse_refs: list, affected_paths: list, event_id: str) -> bool:
    if args.alert_level not in {"WARN", "HOLD", "BLOCK"} or not args.candidate_rule:
        return False
    alert_id = "D8_WRITEBACK_ALERT_" + args.event_type
    sql = f"""
    INSERT INTO d8_possible_alerts (
      run_id, source, event_type, alert_level, title, summary, evidence_ref,
      reverse_refs, affected_paths, candidate_rule, promotion_status,
      executable, quarantine, retrieval_scope, pollution_guard, reverse_index_only
    )
    SELECT
      {sql_literal(args.run_id)},
      'd8_redteam_writeback',
      {sql_literal(alert_id)},
      {sql_literal(args.alert_level)},
      {sql_literal(args.title)},
      {sql_literal(args.summary)},
      {sql_literal(json.dumps({**evidence, 'source_event_id': event_id}, ensure_ascii=False))}::jsonb,
      {sql_literal(json.dumps(reverse_refs, ensure_ascii=False))}::jsonb,
      {sql_literal(json.dumps(affected_paths, ensure_ascii=False))}::jsonb,
      {sql_literal(args.candidate_rule)},
      'candidate',
      false,
      true,
      'redteam_only',
      true,
      true
    WHERE NOT EXISTS (
      SELECT 1 FROM d8_possible_alerts
      WHERE run_id = {sql_literal(args.run_id)}
        AND event_type = {sql_literal(alert_id)}
    );
    """
    run_psql(sql)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Write non-executable redteam evidence to D8 quarantine")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--event-type", required=True)
    parser.add_argument("--alert-level", choices=["INFO", "WARN", "HOLD", "BLOCK"], required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--evidence-json", default="{}")
    parser.add_argument("--reverse-refs-json", default="[]")
    parser.add_argument("--affected-paths-json", default="[]")
    parser.add_argument("--candidate-rule", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    evidence = json.loads(args.evidence_json)
    reverse_refs = json.loads(args.reverse_refs_json)
    affected_paths = json.loads(args.affected_paths_json)
    preview = {
        "run_id": args.run_id,
        "event_type": args.event_type,
        "alert_level": args.alert_level,
        "title": args.title,
        "summary": args.summary,
        "evidence_ref": evidence,
        "reverse_refs": reverse_refs,
        "affected_paths": affected_paths,
        "candidate_rule": args.candidate_rule,
        "executable": False,
        "quarantine": True,
        "retrieval_scope": "redteam_only",
        "pollution_guard": True,
        "reverse_index_only": True,
        "promotion_status": "candidate",
    }
    event_id = None
    possible_alert_considered = False
    if not args.dry_run:
        event_id = insert_event(args, evidence, reverse_refs, affected_paths)
        possible_alert_considered = maybe_insert_possible_alert(args, evidence, reverse_refs, affected_paths, event_id)

    summary = {
        "action": "D8_REDTEAM_WRITEBACK",
        "dry_run": args.dry_run,
        "event_id": event_id,
        "possible_alert_considered": possible_alert_considered,
        "preview": preview,
        "safety_flags": {
            "SECRET_READ": False,
            "PRODUCTION_DB_WRITE": False,
            "SERVICE_RESTART": False,
            "DEPLOY": False,
            "EXTERNAL_API_CALL": False,
            "EMBEDDING_GENERATED": False,
            "EXECUTABLE_REDTEAM_ARTIFACTS": False,
            "POLLUTION_GUARD": True,
            "REVERSE_INDEX_ISOLATION": True,
        },
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
    }
    report = write_report(summary)
    summary["report"] = report.relative_to(ROOT).as_posix()
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
