#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXIT_CODES = {"PASS": 0, "INFO": 0, "WARN": 10, "HOLD": 20, "BLOCK": 30, "ERROR": 40}


def slug(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")
    return clean[:80] or "TASK"


def permission_for(decision: str) -> dict:
    if decision == "PASS":
        return {"allow_sandbox": True, "allow_land": True}
    if decision == "INFO":
        return {"allow_sandbox": True, "allow_land": True, "log_info": True}
    if decision == "WARN":
        return {"allow_sandbox": True, "allow_land": False, "requires_human_review": True}
    if decision in {"HOLD", "BLOCK"}:
        return {"allow_sandbox": False, "allow_land": False, "stop": True}
    return {"allow_sandbox": False, "allow_land": False, "stop": True, "error": True}


def parse_kv(stdout: str) -> dict:
    parsed: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            parsed[key.strip()] = value.strip()
    return parsed


def run_preflight(task_name: str, mode: str, scope_json: str, run_id: str, preflight_mode: str) -> tuple[dict, int, str, str]:
    cmd = [
        "python3",
        "tools/d8_codex_preflight_gate.py",
        "--run-id",
        run_id,
        "--task-name",
        task_name,
        "--mode",
        mode,
        "--scope-json",
        scope_json,
        "--preflight-mode",
        preflight_mode,
    ]
    proc = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return parse_kv(proc.stdout), proc.returncode, proc.stdout, proc.stderr


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a D8 Codex task capsule after preflight")
    parser.add_argument("--task-name", required=True)
    parser.add_argument("--mode", choices=["sandbox", "land", "production", "review"], required=True)
    parser.add_argument("--scope-json", required=True)
    parser.add_argument("--preflight-mode", choices=["PERSIST", "READ_ONLY"], default="PERSIST")
    parser.add_argument("--allowed-paths-json", default="[]")
    parser.add_argument("--forbidden-paths-json", default="[]")
    parser.add_argument("--expected-output", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    scope = json.loads(args.scope_json)
    allowed_paths = json.loads(args.allowed_paths_json)
    forbidden_paths = json.loads(args.forbidden_paths_json)
    task_id = "D8_CODEX_TASK_" + dt.datetime.now(dt.UTC).strftime("%Y%m%d_%H%M%S") + "_" + slug(args.task_name)
    preflight, exit_code, stdout, stderr = run_preflight(args.task_name, args.mode, args.scope_json, task_id, args.preflight_mode)
    decision = preflight.get("DECISION", "ERROR")
    if decision not in EXIT_CODES:
        decision = "ERROR"
        exit_code = EXIT_CODES[decision]

    capsule = {
        "task_id": task_id,
        "task_name": args.task_name,
        "mode": args.mode,
        "preflight_mode": args.preflight_mode,
        "scope_json": scope,
        "allowed_paths": allowed_paths,
        "forbidden_paths": forbidden_paths,
        "expected_output": args.expected_output,
        "dry_run": args.dry_run,
        "preflight_decision": decision,
        "preflight_exit_code": exit_code,
        "permission": permission_for(decision),
        "preflight_stdout": stdout,
        "preflight_stderr_class": "present" if stderr else "empty",
        "safety_flags": {
            "SECRET_READ": False,
            "MEMBER_PLAINTEXT_READ": False,
            "RAW_AUDIO_SAVED": False,
            "PRODUCTION_DB_WRITE": False,
            "D8_LOCAL_DB_WRITE": args.preflight_mode == "PERSIST",
            "SERVICE_RESTART": False,
            "DEPLOY": False,
            "PRODUCTION_RELEASE": False,
            "EXTERNAL_API_CALL": False,
            "EMBEDDING_GENERATED": False,
            "EXECUTABLE_REDTEAM_ARTIFACTS": False,
            "POLLUTION_GUARD": True,
            "REVERSE_INDEX_ISOLATION": True,
            "DO_NOT_TOUCH_AGENTS_MD": True,
        },
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
    }

    out_dir = ROOT / "runtime/total_field/codex_preflight/tasks"
    out_dir.mkdir(parents=True, exist_ok=True)
    capsule_path = out_dir / f"{task_id}.json"
    capsule_path.write_text(json.dumps(capsule, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"STATE={decision}")
    print("ACTION=D8_CODEX_TASK_BOOTSTRAP")
    print(f"TASK_ID={task_id}")
    print(f"TASK_NAME={args.task_name}")
    print(f"MODE={args.mode}")
    print(f"PREFLIGHT_DECISION={decision}")
    print(f"EXIT_CODE={exit_code}")
    print(f"CAPSULE={capsule_path.relative_to(ROOT).as_posix()}")
    print(f"ALLOW_SANDBOX={str(capsule['permission'].get('allow_sandbox', False)).upper()}")
    print(f"ALLOW_LAND={str(capsule['permission'].get('allow_land', False)).upper()}")
    print("SECRET_READ=FALSE")
    print("PRODUCTION_DB_WRITE=FALSE")
    print("SERVICE_RESTART=FALSE")
    print("DEPLOY=FALSE")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
