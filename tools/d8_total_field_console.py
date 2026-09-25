#!/usr/bin/env python3
import argparse
import csv
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = Path("runtime/total_field/operator_console/D8_TOTAL_FIELD_OPERATOR_CONSOLE_POLICY.json")
EXIT_CODES = {"PASS": 0, "INFO": 0, "WARN": 10, "HOLD": 20, "BLOCK": 30, "ERROR": 40}


def now_stamp() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y%m%d_%H%M%S")


def psql(sql: str, *, tuples_only: bool = True) -> str:
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
    ]
    if tuples_only:
        cmd.append("-At")
    cmd.extend(["-c", sql])
    return subprocess.check_output(cmd, cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()


def count(sql: str) -> int:
    return int(psql(sql) or "0")


def latest(pattern: str) -> str | None:
    matches = sorted(ROOT.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0].relative_to(ROOT).as_posix() if matches else None


def write_json_report(prefix: str, payload: dict) -> str:
    out_dir = ROOT / "runtime/d8_db/reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{prefix}_{now_stamp()}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path.relative_to(ROOT).as_posix()


def print_summary(payload: dict, json_mode: bool) -> None:
    if json_mode:
        print(json.dumps(payload, ensure_ascii=False))
        return
    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            print(f"{key.upper()}={json.dumps(value, ensure_ascii=False)}")
        else:
            print(f"{key.upper()}={value}")


def base_counts() -> dict:
    alert_counts = {
        "HOLD": count("SELECT COUNT(*) FROM d8_possible_alerts WHERE alert_level='HOLD';"),
        "WARN": count("SELECT COUNT(*) FROM d8_possible_alerts WHERE alert_level='WARN';"),
        "INFO": count("SELECT COUNT(*) FROM d8_possible_alerts WHERE alert_level='INFO';"),
        "BLOCK": count("SELECT COUNT(*) FROM d8_possible_alerts WHERE alert_level='BLOCK';"),
    }
    return {
        "d8_memory_count": count("SELECT COUNT(*) FROM d8_memory;"),
        "redteam_events_count": count("SELECT COUNT(*) FROM d8_redteam_events;"),
        "possible_alerts_count": count("SELECT COUNT(*) FROM d8_possible_alerts;"),
        "guard_evaluations_count": count("SELECT COUNT(*) FROM d8_guard_evaluations;"),
        "alert_counts": alert_counts,
    }


def safety_summary() -> dict:
    return {
        "SECRET_READ": False,
        "MEMBER_PLAINTEXT_READ": False,
        "RAW_AUDIO_SAVED": False,
        "PRODUCTION_DB_WRITE": False,
        "D8_LOCAL_DB_WRITE": True,
        "SERVICE_RESTART": False,
        "DEPLOY": False,
        "PRODUCTION_RELEASE": False,
        "EXTERNAL_API_CALL": False,
        "EMBEDDING_GENERATED": False,
        "EXECUTABLE_REDTEAM_ARTIFACTS": False,
        "POLLUTION_GUARD": True,
        "REVERSE_INDEX_ISOLATION": True,
        "DO_NOT_TOUCH_AGENTS_MD": True,
    }


def cmd_status(args: argparse.Namespace) -> int:
    try:
        payload = {
            "state": "PASS",
            "action": "D8_TOTAL_FIELD_CONSOLE_STATUS",
            **base_counts(),
            "latest_reports": {
                "phase1": latest("runtime/d8_db/reports/D8_DBIFY_20260623_152850_FINAL_REPORT.json"),
                "phase6": latest("runtime/d8_db/reports/D8_PHASE6_TOTAL_FIELD_OPERATOR_COMMAND_CONSOLE_*_FINAL_REPORT.json"),
                "console_status": latest("runtime/d8_db/reports/D8_CONSOLE_STATUS_*.json"),
            },
            "latest_backups": {
                "phase5": latest("runtime/d8_db/backups/taiji_d8_phase5_codex_task_template_writeback_*.dump"),
                "phase6": latest("runtime/d8_db/backups/taiji_d8_phase6_total_field_operator_console_*.dump"),
            },
            "active_pointer": "runtime/total_field/master_index/ACTIVE_GT_8D_PACKET_POINTER.json"
            if (ROOT / "runtime/total_field/master_index/ACTIVE_GT_8D_PACKET_POINTER.json").exists()
            else None,
            "safety_summary": safety_summary(),
        }
        payload["report"] = write_json_report("D8_CONSOLE_STATUS", payload)
        print_summary(payload, args.json)
        return 0
    except subprocess.CalledProcessError:
        print("STATE=FAIL_DB_UNREACHABLE")
        return 40


def table_exists(name: str) -> bool:
    return count(
        "SELECT COUNT(*) FROM information_schema.tables "
        f"WHERE table_schema='public' AND table_name='{name}';"
    ) == 1


def cmd_doctor(args: argparse.Namespace) -> int:
    checks: dict[str, bool] = {"root_path": ROOT.as_posix() == "/home/taiji_admin/Taiji_Hub"}
    try:
        psql("SELECT 1;")
        checks["db_reachable"] = True
        for table in ["d8_memory", "d8_redteam_events", "d8_possible_alerts", "d8_guard_evaluations"]:
            checks[f"{table}_exists"] = table_exists(table)
        checks["console_policy_exists"] = (ROOT / POLICY_PATH).exists()
        for tool in [
            "tools/d8_codex_preflight_gate.py",
            "tools/d8_codex_task_bootstrap.py",
            "tools/d8_redteam_writeback.py",
        ]:
            checks[tool.replace("/", "_").replace(".", "_") + "_exists"] = (ROOT / tool).exists()
        redteam_count = count("SELECT COUNT(*) FROM d8_redteam_events;")
        redteam_guarded = count(
            "SELECT COUNT(*) FROM d8_redteam_events "
            "WHERE executable=false AND quarantine=true AND retrieval_scope='redteam_only' "
            "AND pollution_guard=true AND reverse_index_only=true;"
        )
        alerts_count = count("SELECT COUNT(*) FROM d8_possible_alerts;")
        alerts_guarded = count(
            "SELECT COUNT(*) FROM d8_possible_alerts "
            "WHERE executable=false AND quarantine=true AND retrieval_scope='redteam_only' "
            "AND pollution_guard=true AND reverse_index_only=true;"
        )
        checks["redteam_pollution_guard_valid"] = redteam_count == redteam_guarded
        checks["executable_redteam_artifacts_false"] = alerts_count == alerts_guarded
        state = "PASS" if all(checks.values()) else "FAIL"
    except subprocess.CalledProcessError:
        state = "FAIL_DB_UNREACHABLE"
        checks["db_reachable"] = False
    payload = {"state": state, "action": "D8_TOTAL_FIELD_CONSOLE_DOCTOR", "checks": checks}
    payload["report"] = write_json_report("D8_CONSOLE_DOCTOR", payload)
    print_summary(payload, args.json)
    return 0 if state == "PASS" else 40


def query_json(sql: str) -> list[dict]:
    raw = psql(sql)
    return json.loads(raw or "[]")


def cmd_alerts(args: argparse.Namespace) -> int:
    limit = max(1, args.limit)
    rows = query_json(
        "SELECT COALESCE(jsonb_agg(to_jsonb(a)), '[]'::jsonb) FROM ("
        "SELECT event_type AS alert_id, alert_level, title, promotion_status, executable, "
        "quarantine, retrieval_scope, pollution_guard, reverse_index_only, created_at "
        "FROM d8_possible_alerts ORDER BY created_at DESC "
        f"LIMIT {limit}) a;"
    )
    payload = {
        "state": "PASS",
        "action": "D8_TOTAL_FIELD_CONSOLE_ALERTS",
        "possible_alerts_count": count("SELECT COUNT(*) FROM d8_possible_alerts;"),
        "rows": rows,
    }
    print_summary(payload, args.json)
    return 0


def cmd_redteam(args: argparse.Namespace) -> int:
    limit = max(1, args.limit)
    rows = query_json(
        "SELECT COALESCE(jsonb_agg(to_jsonb(e)), '[]'::jsonb) FROM ("
        "SELECT run_id, event_type, alert_level, title, promotion_status, executable, quarantine, "
        "retrieval_scope, pollution_guard, reverse_index_only, created_at "
        "FROM d8_redteam_events WHERE quarantine=true AND retrieval_scope='redteam_only' "
        "ORDER BY created_at DESC "
        f"LIMIT {limit}) e;"
    )
    payload = {
        "state": "PASS",
        "action": "D8_TOTAL_FIELD_CONSOLE_REDTEAM",
        "redteam_events_count": count("SELECT COUNT(*) FROM d8_redteam_events;"),
        "rows": rows,
    }
    print_summary(payload, args.json)
    return 0


def cmd_evals(args: argparse.Namespace) -> int:
    limit = max(1, args.limit)
    rows = query_json(
        "SELECT COALESCE(jsonb_agg(to_jsonb(g)), '[]'::jsonb) FROM ("
        "SELECT run_id, task_name, decision, executable, pollution_guard, created_at "
        "FROM d8_guard_evaluations ORDER BY created_at DESC "
        f"LIMIT {limit}) g;"
    )
    payload = {
        "state": "PASS",
        "action": "D8_TOTAL_FIELD_CONSOLE_EVALS",
        "guard_evaluations_count": count("SELECT COUNT(*) FROM d8_guard_evaluations;"),
        "rows": rows,
    }
    print_summary(payload, args.json)
    return 0


def pass_through(tool: str, args: argparse.Namespace, extra: list[str]) -> int:
    cmd = ["python3", tool]
    if args.task_name:
        cmd += ["--task-name", args.task_name]
    if args.mode:
        cmd += ["--mode", args.mode]
    if args.scope_json:
        cmd += ["--scope-json", args.scope_json]
    if hasattr(args, "allowed_paths_json") and args.allowed_paths_json:
        cmd += ["--allowed-paths-json", args.allowed_paths_json]
    if hasattr(args, "forbidden_paths_json") and args.forbidden_paths_json:
        cmd += ["--forbidden-paths-json", args.forbidden_paths_json]
    if hasattr(args, "expected_output") and args.expected_output:
        cmd += ["--expected-output", args.expected_output]
    if args.event_type:
        cmd += ["--event-type", args.event_type]
    if args.alert_level:
        cmd += ["--alert-level", args.alert_level]
    if args.title:
        cmd += ["--title", args.title]
    if args.summary:
        cmd += ["--summary", args.summary]
    if args.evidence_json:
        cmd += ["--evidence-json", args.evidence_json]
    if args.reverse_refs_json:
        cmd += ["--reverse-refs-json", args.reverse_refs_json]
    if args.affected_paths_json:
        cmd += ["--affected-paths-json", args.affected_paths_json]
    if args.candidate_rule:
        cmd += ["--candidate-rule", args.candidate_rule]
    if args.dry_run:
        cmd += ["--dry-run"]
    cmd += extra
    proc = subprocess.run(cmd, cwd=ROOT, text=True)
    return proc.returncode


def cmd_preflight(args: argparse.Namespace, extra: list[str]) -> int:
    return pass_through("tools/d8_codex_preflight_gate.py", args, extra)


def cmd_bootstrap(args: argparse.Namespace, extra: list[str]) -> int:
    return pass_through("tools/d8_codex_task_bootstrap.py", args, extra)


def cmd_writeback(args: argparse.Namespace, extra: list[str]) -> int:
    cmd = ["python3", "tools/d8_redteam_writeback.py"]
    if not any(item == "--run-id" for item in extra):
        cmd += ["--run-id", "D8_TOTAL_FIELD_OPERATOR_CONSOLE_WRITEBACK"]
    if args.event_type:
        cmd += ["--event-type", args.event_type]
    if args.alert_level:
        cmd += ["--alert-level", args.alert_level]
    if args.title:
        cmd += ["--title", args.title]
    if args.summary:
        cmd += ["--summary", args.summary]
    if args.evidence_json:
        cmd += ["--evidence-json", args.evidence_json]
    if args.reverse_refs_json:
        cmd += ["--reverse-refs-json", args.reverse_refs_json]
    if args.affected_paths_json:
        cmd += ["--affected-paths-json", args.affected_paths_json]
    if args.candidate_rule:
        cmd += ["--candidate-rule", args.candidate_rule]
    if args.dry_run:
        cmd += ["--dry-run"]
    cmd += extra
    proc = subprocess.run(cmd, cwd=ROOT, text=True)
    return proc.returncode


def cmd_seal(args: argparse.Namespace) -> int:
    counts = base_counts()
    seal_dir = ROOT / "runtime/total_field/status"
    seal_dir.mkdir(parents=True, exist_ok=True)
    path = seal_dir / f"D8_TOTAL_FIELD_OPERATOR_CONSOLE_{now_stamp()}_SEAL.md"
    payload = {
        "state": "PASS",
        "action": "D8_TOTAL_FIELD_CONSOLE_SEAL",
        **counts,
        "latest_reports": {
            "status": latest("runtime/d8_db/reports/D8_CONSOLE_STATUS_*.json"),
            "doctor": latest("runtime/d8_db/reports/D8_CONSOLE_DOCTOR_*.json"),
        },
        "safety_flags": safety_summary(),
        "console_policy": POLICY_PATH.as_posix(),
        "executable": False,
        "pollution_guard": True,
        "reverse_index_isolation": True,
    }
    lines = ["# D8 Total Field Operator Console Seal", ""]
    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            lines.append(f"{key.upper()}={json.dumps(value, ensure_ascii=False)}")
        else:
            lines.append(f"{key.upper()}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    payload["seal"] = path.relative_to(ROOT).as_posix()
    payload["report"] = write_json_report("D8_CONSOLE_SEAL", payload)
    print_summary(payload, args.json)
    return 0


def cmd_help(_: argparse.Namespace) -> int:
    print("D8 Total Field Console commands:")
    print("  status | doctor | alerts | redteam | evals | preflight | bootstrap | writeback | seal | help")
    print("Examples:")
    print("  tools/d8_total_field_console.sh status")
    print("  tools/d8_total_field_console.sh alerts --limit 10")
    print("  tools/d8_total_field_console.sh preflight --task-name SAFE_TOTAL_FIELD_STATUS_READ --mode sandbox --scope-json '{\"readonly\":true}'")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="D8 Total Field operator console")
    parser.add_argument("command", nargs="?", default="help")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--task-name")
    parser.add_argument("--mode")
    parser.add_argument("--scope-json")
    parser.add_argument("--allowed-paths-json")
    parser.add_argument("--forbidden-paths-json")
    parser.add_argument("--expected-output")
    parser.add_argument("--event-type")
    parser.add_argument("--alert-level")
    parser.add_argument("--title")
    parser.add_argument("--summary")
    parser.add_argument("--evidence-json")
    parser.add_argument("--reverse-refs-json")
    parser.add_argument("--affected-paths-json")
    parser.add_argument("--candidate-rule")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args, extra = parser.parse_known_args(argv)
    command = args.command
    if command == "status":
        return cmd_status(args)
    if command == "doctor":
        return cmd_doctor(args)
    if command == "alerts":
        return cmd_alerts(args)
    if command == "redteam":
        return cmd_redteam(args)
    if command == "evals":
        return cmd_evals(args)
    if command == "preflight":
        return cmd_preflight(args, extra)
    if command == "bootstrap":
        return cmd_bootstrap(args, extra)
    if command == "writeback":
        return cmd_writeback(args, extra)
    if command == "seal":
        return cmd_seal(args)
    if command == "help":
        return cmd_help(args)
    print("STATE=ERROR")
    print(f"REASON=unknown command: {command}")
    return 40


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
