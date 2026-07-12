#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXIT_CODES = {"PASS": 0, "INFO": 0, "WARN": 10, "HOLD": 20, "BLOCK": 30, "FAIL": 40, "ERROR": 40}


def stamp() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y%m%d_%H%M%S")


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")[:90] or "TASK"


def kv(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def psql(sql: str) -> str:
    cmd = [
        "docker", "compose", "--env-file", ".env.d8.local", "-f", "compose.d8.yml",
        "exec", "-T", "d8_db", "psql", "-U", "taiji", "-d", "taiji_d8", "-At", "-c", sql,
    ]
    return subprocess.check_output(cmd, cwd=ROOT, text=True).strip()


def count(sql: str) -> int:
    return int(psql(sql) or "0")


def permission(decision: str) -> dict:
    if decision == "PASS":
        return {"allow_sandbox": True, "allow_land": True, "requires_human_review": False}
    if decision == "INFO":
        return {"allow_sandbox": True, "allow_land": True, "requires_human_review": False}
    if decision == "WARN":
        return {"allow_sandbox": True, "allow_land": False, "requires_human_review": True}
    if decision in {"HOLD", "BLOCK"}:
        return {"allow_sandbox": False, "allow_land": False, "requires_human_review": True, "stop": True}
    return {"allow_sandbox": False, "allow_land": False, "requires_human_review": True, "stop": True, "error": True}


def safety_flags(*, d8_local_db_write: bool = True) -> dict:
    return {
        "SECRET_READ": False,
        "MEMBER_PLAINTEXT_READ": False,
        "RAW_AUDIO_SAVED": False,
        "PRODUCTION_DB_WRITE": False,
        "D8_LOCAL_DB_WRITE": d8_local_db_write,
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


def latest_capsule(task_name: str | None = None) -> Path | None:
    base = ROOT / "runtime/total_field/codex_mandatory_workflow/tasks"
    if not base.exists():
        return None
    items = sorted(base.glob("D8_MANDATORY_TASK_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if task_name:
        token = slug(task_name)
        items = [p for p in items if token in p.name]
    return items[0] if items else None


def latest_path(pattern: str) -> str | None:
    items = sorted(ROOT.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return items[0].relative_to(ROOT).as_posix() if items else None


def write_report(prefix: str, payload: dict) -> str:
    out = ROOT / "runtime/d8_db/reports"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{prefix}_{stamp()}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path.relative_to(ROOT).as_posix()


def cmd_start(args: argparse.Namespace) -> int:
    task_id = f"D8_MANDATORY_TASK_{stamp()}_{slug(args.task_name)}"
    scope = json.loads(args.scope_json)
    if args.explicit_human_release:
        scope["explicit_human_release"] = True
    scope_json = json.dumps(scope, ensure_ascii=False)
    preflight = run([
        "tools/d8_total_field_console.sh", "preflight",
        "--run-id", task_id,
        "--task-name", args.task_name,
        "--mode", args.mode,
        "--scope-json", scope_json,
        "--preflight-mode", args.preflight_mode,
    ])
    pre = kv(preflight.stdout)
    decision = pre.get("DECISION") or pre.get("STATE") or "ERROR"
    boot = run([
        "python3", "tools/d8_codex_task_bootstrap.py",
        "--task-name", args.task_name,
        "--mode", args.mode,
        "--scope-json", scope_json,
        "--allowed-paths-json", args.allowed_paths_json,
        "--forbidden-paths-json", args.forbidden_paths_json,
        "--expected-output", args.expected_output,
        "--preflight-mode", args.preflight_mode,
        "--dry-run",
    ])
    boot_kv = kv(boot.stdout)
    capsule = {
        "task_id": task_id,
        "task_name": args.task_name,
        "mode": args.mode,
        "scope_json": scope,
        "allowed_paths": json.loads(args.allowed_paths_json),
        "forbidden_paths": json.loads(args.forbidden_paths_json),
        "expected_output": args.expected_output,
        "preflight_decision": decision,
        "permission": permission(decision),
        "mandatory_preflight": True,
        "preflight_report": latest_path("runtime/d8_db/reports/D8_CODEX_PREFLIGHT_*.json"),
        "bootstrap_capsule": boot_kv.get("CAPSULE"),
        "preflight_stdout": preflight.stdout,
        "bootstrap_stdout": boot.stdout,
        "safety_flags": safety_flags(d8_local_db_write=args.preflight_mode == "PERSIST"),
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
    }
    out_dir = ROOT / "runtime/total_field/codex_mandatory_workflow/tasks"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{task_id}.json"
    path.write_text(json.dumps(capsule, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"STATE={decision}")
    print("ACTION=D8_CODEX_MANDATORY_WORKFLOW_START")
    print(f"TASK_ID={task_id}")
    print(f"TASK_NAME={args.task_name}")
    print(f"DECISION={decision}")
    print(f"ALLOW_SANDBOX={str(capsule['permission'].get('allow_sandbox', False)).upper()}")
    print(f"ALLOW_LAND={str(capsule['permission'].get('allow_land', False)).upper()}")
    print(f"STOP={str(capsule['permission'].get('stop', False)).upper()}")
    print(f"CAPSULE={path.relative_to(ROOT).as_posix()}")
    return EXIT_CODES.get(decision, 40)


def cmd_finalize(args: argparse.Namespace) -> int:
    capsule_path = Path(args.capsule) if args.capsule else latest_capsule(args.task_name)
    if not capsule_path:
        print("STATE=ERROR")
        print("REASON=no capsule found")
        return 40
    if not capsule_path.is_absolute():
        capsule_path = ROOT / capsule_path
    capsule = json.loads(capsule_path.read_text(encoding="utf-8"))
    state = args.task_state
    seal_dir = ROOT / "runtime/total_field/codex_mandatory_workflow/seals"
    seal_dir.mkdir(parents=True, exist_ok=True)
    seal = seal_dir / f"D8_MANDATORY_TASK_RESULT_{stamp()}_{slug(capsule['task_name'])}.md"
    lines = [
        "# D8 Mandatory Task Result Seal",
        "",
        f"TASK_ID={capsule['task_id']}",
        f"TASK_NAME={capsule['task_name']}",
        f"TASK_STATE={state}",
        f"RESULT_SUMMARY={args.result_summary}",
        "PRODUCTION_DB_WRITE=FALSE",
        "SERVICE_RESTART=FALSE",
        "DEPLOY=FALSE",
    ]
    seal.write_text("\n".join(lines) + "\n", encoding="utf-8")
    writeback_report = None
    if state in {"WARN", "HOLD", "BLOCK", "FAIL"}:
        alert_level = "BLOCK" if state == "FAIL" else state
        wb = run([
            "python3", "tools/d8_redteam_writeback.py",
            "--run-id", capsule["task_id"],
            "--event-type", f"MANDATORY_WORKFLOW_{state}",
            "--alert-level", alert_level,
            "--title", f"Mandatory workflow {state}",
            "--summary", args.result_summary or f"Mandatory workflow finalized with {state}",
            "--evidence-json", json.dumps({"capsule": capsule_path.relative_to(ROOT).as_posix(), "task_state": state}, ensure_ascii=False),
            "--reverse-refs-json", json.dumps([{"capsule": capsule_path.relative_to(ROOT).as_posix()}], ensure_ascii=False),
            "--affected-paths-json", json.dumps(capsule.get("forbidden_paths", []), ensure_ascii=False),
            "--candidate-rule", f"Mandatory workflow {state} must remain quarantined and non-executable.",
        ])
        try:
            writeback_report = json.loads(wb.stdout).get("report")
        except Exception:
            writeback_report = None
    result = {
        "task_id": capsule["task_id"],
        "task_name": capsule["task_name"],
        "task_state": state,
        "result_summary": args.result_summary,
        "capsule": capsule_path.relative_to(ROOT).as_posix(),
        "seal": seal.relative_to(ROOT).as_posix(),
        "writeback_report": writeback_report,
        "safety_flags": safety_flags(),
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
    }
    result_dir = ROOT / "runtime/total_field/codex_mandatory_workflow/results"
    result_dir.mkdir(parents=True, exist_ok=True)
    result_path = result_dir / f"D8_MANDATORY_RESULT_{stamp()}_{slug(capsule['task_name'])}.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"STATE={state}")
    print("ACTION=D8_CODEX_MANDATORY_WORKFLOW_FINALIZE")
    print(f"CAPSULE={capsule_path.relative_to(ROOT).as_posix()}")
    print(f"SEAL={seal.relative_to(ROOT).as_posix()}")
    print(f"RESULT={result_path.relative_to(ROOT).as_posix()}")
    print(f"WRITEBACK_REPORT={writeback_report or 'false'}")
    return EXIT_CODES.get(state, 40)


def cmd_validate(args: argparse.Namespace) -> int:
    base = ROOT / "runtime/total_field/codex_mandatory_workflow/tasks"
    capsules = [json.loads(p.read_text(encoding="utf-8")) for p in base.glob("D8_MANDATORY_TASK_*.json")] if base.exists() else []
    expected_flags = safety_flags()
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
    checks = {
        "capsules_exist": bool(capsules),
        "all_mandatory_preflight": all(c.get("mandatory_preflight") is True for c in capsules),
        "warn_allow_land_false": all(c.get("permission", {}).get("allow_land") is False for c in capsules if c.get("preflight_decision") == "WARN"),
        "hold_block_stop_true": all(c.get("permission", {}).get("stop") is True for c in capsules if c.get("preflight_decision") in {"HOLD", "BLOCK"}),
        "forbidden_not_in_allowed": all(not (set(c.get("allowed_paths", [])) & set(c.get("forbidden_paths", []))) for c in capsules),
        "all_capsule_safety_flags_valid": all(c.get("safety_flags", {}) == expected_flags for c in capsules),
        "safe_memory_no_redteam": count("SELECT COUNT(*) FROM d8_safe_memory WHERE body ILIKE '%MANDATORY_WORKFLOW_FAIL%' OR body ILIKE '%MANDATORY_WORKFLOW_WARN%' OR body ILIKE '%MANDATORY_WORKFLOW_HOLD%';") == 0,
        "mandatory_redteam_writeback_non_executable": count("SELECT COUNT(*) FROM d8_redteam_events WHERE event_type LIKE 'MANDATORY_WORKFLOW_%' AND executable=false AND quarantine=true AND retrieval_scope='redteam_only' AND pollution_guard=true AND reverse_index_only=true;") >= 1,
        "mandatory_possible_alert_writeback_non_executable": count("SELECT COUNT(*) FROM d8_possible_alerts WHERE event_type LIKE 'D8_WRITEBACK_ALERT_MANDATORY_WORKFLOW_%' AND executable=false AND quarantine=true AND retrieval_scope='redteam_only' AND pollution_guard=true AND reverse_index_only=true;") >= 1,
        "all_redteam_events_guarded": redteam_count == redteam_guarded,
        "all_possible_alerts_guarded": alerts_count == alerts_guarded,
    }
    state = "PASS" if all(checks.values()) else "FAIL"
    payload = {"state": state, "action": "D8_MANDATORY_WORKFLOW_VALIDATE", "checks": checks, "capsule_count": len(capsules)}
    payload["report"] = write_report("D8_MANDATORY_WORKFLOW_VALIDATE", payload)
    print(f"STATE={state}")
    print("ACTION=D8_MANDATORY_WORKFLOW_VALIDATE")
    print(f"REPORT={payload['report']}")
    return 0 if state == "PASS" else 40


def cmd_doctor(args: argparse.Namespace) -> int:
    checks = {
        "preflight_tool_exists": (ROOT / "tools/d8_codex_preflight_gate.py").exists(),
        "bootstrap_tool_exists": (ROOT / "tools/d8_codex_task_bootstrap.py").exists(),
        "writeback_tool_exists": (ROOT / "tools/d8_redteam_writeback.py").exists(),
        "console_exists": (ROOT / "tools/d8_total_field_console.py").exists(),
        "db_reachable": False,
        "possible_alerts_ge_3": False,
        "guard_evaluations_exists": False,
        "redteam_events_exists": False,
        "policy_exists": (ROOT / "runtime/total_field/operator_console/D8_TOTAL_FIELD_OPERATOR_CONSOLE_POLICY.json").exists(),
        "pollution_guard_valid": False,
    }
    try:
        psql("SELECT 1;")
        checks["db_reachable"] = True
        checks["possible_alerts_ge_3"] = count("SELECT COUNT(*) FROM d8_possible_alerts;") >= 3
        checks["guard_evaluations_exists"] = count("SELECT COUNT(*) FROM d8_guard_evaluations;") >= 1
        checks["redteam_events_exists"] = count("SELECT COUNT(*) FROM d8_redteam_events;") >= 1
        rt = count("SELECT COUNT(*) FROM d8_redteam_events;")
        rtg = count("SELECT COUNT(*) FROM d8_redteam_events WHERE executable=false AND quarantine=true AND retrieval_scope='redteam_only' AND pollution_guard=true AND reverse_index_only=true;")
        checks["pollution_guard_valid"] = rt == rtg
    except Exception:
        pass
    state = "PASS" if all(checks.values()) else "FAIL"
    print(f"STATE={state}")
    print("ACTION=D8_MANDATORY_WORKFLOW_DOCTOR")
    print(f"CHECKS={json.dumps(checks, ensure_ascii=False)}")
    return 0 if state == "PASS" else 40


def cmd_help(_: argparse.Namespace) -> int:
    print("Commands: start, finalize, validate, doctor, help")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="D8 mandatory Codex workflow")
    parser.add_argument("command", nargs="?", default="help")
    parser.add_argument("--task-name", default="")
    parser.add_argument("--mode", default="sandbox")
    parser.add_argument("--preflight-mode", choices=["PERSIST", "READ_ONLY"], default="PERSIST")
    parser.add_argument("--scope-json", default="{}")
    parser.add_argument("--allowed-paths-json", default="[]")
    parser.add_argument("--forbidden-paths-json", default="[]")
    parser.add_argument("--expected-output", default="")
    parser.add_argument("--task-state", choices=["PASS", "INFO", "WARN", "HOLD", "BLOCK", "FAIL"], default="PASS")
    parser.add_argument("--result-summary", default="")
    parser.add_argument("--evidence-json", default="{}")
    parser.add_argument("--explicit-human-release", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--capsule")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "start":
        return cmd_start(args)
    if args.command == "finalize":
        return cmd_finalize(args)
    if args.command == "validate":
        return cmd_validate(args)
    if args.command == "doctor":
        return cmd_doctor(args)
    if args.command == "help":
        return cmd_help(args)
    print("STATE=ERROR")
    print(f"REASON=unknown command {args.command}")
    return 40


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
