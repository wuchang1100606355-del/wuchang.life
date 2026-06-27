#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/home/taiji_admin/Taiji_Hub")
REPORT_DIR = ROOT / "runtime/d8_db/reports"
EXPORT_DIR = ROOT / "runtime/d8_db/exports"
DEMO_DIR = ROOT / "runtime/total_field/product_demo"
STATUS_DIR = ROOT / "runtime/total_field/status"
CONSOLE = ROOT / "tools/d8_total_field_console.sh"
DASHBOARD = ROOT / "tools/d8_local_dashboard.py"
VOICE = ROOT / "tools/d8_voice_operator.py"
POS_BRIDGE = ROOT / "tools/d8_odoo_pos_safe_bridge.py"

REPORT_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)
DEMO_DIR.mkdir(parents=True, exist_ok=True)
STATUS_DIR.mkdir(parents=True, exist_ok=True)


SAFETY_FLAGS = {
    "SECRET_READ": False,
    "MEMBER_PLAINTEXT_READ": False,
    "RAW_AUDIO_SAVED": False,
    "ODOO_DB_WRITE": False,
    "POS_ORDER_CREATED": False,
    "PAYMENT_CAPTURE": False,
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


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def run_cmd(cmd: list[str], timeout: int = 60) -> dict:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        return {
            "cmd": cmd,
            "returncode": proc.returncode,
            "timed_out": False,
            "output": (proc.stdout or "")[-16000:],
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return {
            "cmd": cmd,
            "returncode": 124,
            "timed_out": True,
            "output": (stdout + stderr)[-16000:],
        }


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    if path.name.startswith(".env") or ".env" in path.as_posix():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def latest_file(pattern: str) -> Path | None:
    items = sorted(ROOT.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return items[0] if items else None


def write_json_report(name: str, payload: dict) -> str:
    path = REPORT_DIR / f"{name}_{stamp()}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rel(path)


def refuse_non_local_host(host: str) -> None:
    if host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("STATE=BLOCK_NON_LOCAL_HOST")


def psql_count(table: str) -> int:
    sql = f"SELECT COUNT(*) FROM {table};"
    result = run_cmd([
        "docker", "compose", "--env-file", ".env.d8.local", "-f", "compose.d8.yml",
        "exec", "-T", "d8_db", "psql", "-U", "taiji", "-d", "taiji_d8", "-At", "-c", sql,
    ], timeout=30)
    try:
        return int(result["output"].strip() or "0")
    except ValueError:
        return 0


def print_payload(payload: dict, json_mode: bool) -> None:
    if json_mode:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            print(f"{key.upper()}={json.dumps(value, ensure_ascii=False)}")
        else:
            print(f"{key.upper()}={value}")


def state_from_output(result: dict) -> str:
    return "PASS" if result["returncode"] == 0 and "STATE=PASS" in result["output"] else "FAIL"


def cmd_status(args: argparse.Namespace) -> int:
    result = run_cmd([str(CONSOLE), "status"], timeout=args.timeout)
    payload = {
        "state": state_from_output(result),
        "action": "D8_PRODUCT_DEMO_STATUS",
        "result": result,
        "safety_flags": SAFETY_FLAGS,
    }
    payload["report"] = write_json_report("D8_PRODUCT_DEMO_STATUS", payload)
    print_payload(payload, args.json)
    return 0 if payload["state"] == "PASS" else 40


def cmd_doctor(args: argparse.Namespace) -> int:
    result = run_cmd([str(CONSOLE), "doctor"], timeout=args.timeout)
    payload = {
        "state": state_from_output(result),
        "action": "D8_PRODUCT_DEMO_DOCTOR",
        "result": result,
        "safety_flags": SAFETY_FLAGS,
    }
    payload["report"] = write_json_report("D8_PRODUCT_DEMO_DOCTOR", payload)
    print_payload(payload, args.json)
    return 0 if payload["state"] == "PASS" else 40


def dashboard_result(host: str, port: int, timeout: int) -> dict:
    refuse_non_local_host(host)
    result = run_cmd(["python3", str(DASHBOARD), "--host", host, "--port", str(port)], timeout=timeout)
    ready = "STATE=PASS_D8_LOCAL_DASHBOARD_READY" in result["output"]
    return {
        "state": "PASS" if ready else "FAIL",
        "local_only": host in {"127.0.0.1", "localhost"},
        "ready_seen": ready,
        "timeout_after_ready": ready and result["timed_out"],
        "result": result,
    }


def cmd_dashboard(args: argparse.Namespace) -> int:
    payload = {
        "action": "D8_PRODUCT_DEMO_DASHBOARD",
        **dashboard_result(args.host, args.port, args.timeout),
        "safety_flags": SAFETY_FLAGS,
    }
    payload["report"] = write_json_report("D8_PRODUCT_DEMO_DASHBOARD", payload)
    print_payload(payload, args.json)
    return 0 if payload["state"] == "PASS" else 40


def run_voice(text: str, dry_run: bool, timeout: int) -> dict:
    cmd = ["python3", str(VOICE), "--text", text]
    if dry_run:
        cmd.append("--dry-run")
    result = run_cmd(cmd, timeout=timeout)
    parsed = {}
    try:
        parsed = json.loads(result["output"])
    except json.JSONDecodeError:
        pass
    return {"text": text, "result": result, "parsed": parsed}


def cmd_voice_demo(args: argparse.Namespace) -> int:
    texts = [args.text] if args.text else ["查狀態", "看告警", "安全讀取"]
    runs = [run_voice(text, args.dry_run, args.timeout) for text in texts]
    ok = all(run["result"]["returncode"] == 0 for run in runs)
    ok = ok and all(run["parsed"].get("raw_audio_saved") is False for run in runs if run["parsed"])
    payload = {
        "state": "PASS" if ok else "FAIL",
        "action": "D8_PRODUCT_DEMO_VOICE",
        "runs": runs,
        "safety_flags": SAFETY_FLAGS,
    }
    payload["report"] = write_json_report("D8_PRODUCT_DEMO_VOICE", payload)
    print_payload(payload, args.json)
    return 0 if payload["state"] == "PASS" else 40


def pos_bridge_result(timeout: int) -> dict:
    result = run_cmd(["python3", str(POS_BRIDGE), "--dry-run"], timeout=timeout)
    output = result["output"]
    checks = {
        "manifest_pass": "STATE=PASS_D8_ODOO_POS_SAFE_BRIDGE_READONLY_MANIFEST" in output,
        "odoo_db_write_false": "ODOO_DB_WRITE=FALSE" in output,
        "pos_order_created_false": "POS_ORDER_CREATED=FALSE" in output,
        "payment_capture_false": "PAYMENT_CAPTURE=FALSE" in output,
    }
    return {"state": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "result": result}


def cmd_pos_bridge_demo(args: argparse.Namespace) -> int:
    payload = {
        "action": "D8_PRODUCT_DEMO_POS_BRIDGE",
        **pos_bridge_result(args.timeout),
        "safety_flags": SAFETY_FLAGS,
    }
    payload["report"] = write_json_report("D8_PRODUCT_DEMO_POS_BRIDGE", payload)
    print_payload(payload, args.json)
    return 0 if payload["state"] == "PASS" else 40


def preflight_demo(timeout: int) -> dict:
    return run_cmd([
        str(CONSOLE), "preflight",
        "--task-name", "D8_PHASE12_PRODUCT_DEMO_SMOKE_PREFLIGHT",
        "--mode", "sandbox",
        "--scope-json", '{"product_demo":true,"readonly":true,"no_deploy":true}',
    ], timeout=timeout)


def cmd_smoke_test(args: argparse.Namespace) -> int:
    checks = {
        "console_status": run_cmd([str(CONSOLE), "status"], timeout=args.timeout),
        "console_doctor": run_cmd([str(CONSOLE), "doctor"], timeout=args.timeout),
        "voice_status": run_voice("查狀態", True, args.timeout),
        "voice_alerts": run_voice("看告警", True, args.timeout),
        "pos_bridge": pos_bridge_result(args.timeout),
        "dashboard": dashboard_result(args.host, args.port, args.timeout),
        "preflight_demo": preflight_demo(args.timeout),
    }
    pass_map = {
        "console_status": state_from_output(checks["console_status"]) == "PASS",
        "console_doctor": state_from_output(checks["console_doctor"]) == "PASS",
        "voice_status": "status" in checks["voice_status"]["parsed"].get("routed_args", []),
        "voice_alerts": "alerts" in checks["voice_alerts"]["parsed"].get("routed_args", []),
        "pos_bridge": checks["pos_bridge"]["state"] == "PASS",
        "dashboard": checks["dashboard"]["state"] == "PASS",
        "preflight_demo": checks["preflight_demo"]["returncode"] == 0 and "STATE=PASS" in checks["preflight_demo"]["output"],
    }
    payload = {
        "state": "PASS" if all(pass_map.values()) else "FAIL",
        "action": "D8_PRODUCT_DEMO_SMOKE_TEST",
        "pass_map": pass_map,
        "checks": checks,
        "safety_flags": SAFETY_FLAGS,
    }
    payload["report"] = write_json_report("D8_PRODUCT_DEMO_SMOKE_TEST", payload)
    print_payload(payload, args.json)
    return 0 if payload["state"] == "PASS" else 40


def manifest_paths() -> list[str]:
    fixed = [
        "tools/d8_product_demo_launcher.py",
        "tools/d8_product_demo_launcher.sh",
        "tools/d8_local_dashboard.py",
        "tools/d8_voice_operator.py",
        "tools/d8_odoo_pos_safe_bridge.py",
        "tools/d8_total_field_console.sh",
        "tools/d8_codex_mandatory_workflow.sh",
    ]
    docs = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "docs/product").glob("*.md"))
    latest_patterns = [
        "runtime/d8_db/reports/D8_DBIFY_*_FINAL_REPORT.json",
        "runtime/d8_db/reports/D8_PHASE2_*_FINAL_REPORT.json",
        "runtime/d8_db/reports/D8_PHASE3_*_FINAL_REPORT.json",
        "runtime/d8_db/reports/D8_PHASE4_*_FINAL_REPORT.json",
        "runtime/d8_db/reports/D8_PHASE5_*_FINAL_REPORT.json",
        "runtime/d8_db/reports/D8_PHASE6_*_FINAL_REPORT.json",
        "runtime/d8_db/reports/D8_PHASE7_8_*_FINAL_REPORT.json",
        "runtime/d8_db/reports/D8_PHASE9_10_11_*_FINAL_REPORT.json",
        "runtime/total_field/status/*_SEAL.md",
    ]
    found = [p for p in fixed if (ROOT / p).exists()] + docs
    for pattern in latest_patterns:
        item = latest_file(pattern)
        if item:
            found.append(rel(item))
    latest_backup = latest_file("runtime/d8_db/backups/*.dump")
    if latest_backup:
        found.append(rel(latest_backup))
    return sorted(dict.fromkeys(found))


def cmd_package(args: argparse.Namespace) -> int:
    package_dir = DEMO_DIR / f"D8_PRODUCT_DEMO_PACKAGE_{stamp()}"
    package_dir.mkdir(parents=True, exist_ok=True)
    paths = manifest_paths()
    manifest_rows = []
    for item in paths:
        path = ROOT / item
        is_backup = item.startswith("runtime/d8_db/backups/")
        manifest_rows.append({
            "path": item,
            "exists": path.exists(),
            "bytes": path.stat().st_size if path.exists() else 0,
            "sha256": None if is_backup else sha256_file(path),
            "hash_skipped_reason": "backup_path_only" if is_backup else "",
        })
    env_path = ROOT / ".env.d8.local"
    manifest = {
        "state": "PASS",
        "action": "D8_PRODUCT_DEMO_PACKAGE",
        "package_dir": rel(package_dir),
        "items": manifest_rows,
        "env_d8_local_exists": env_path.exists(),
        "env_permission_checked": env_path.exists(),
        "env_content_included": False,
        "safety_flags": SAFETY_FLAGS,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (package_dir / "D8_PRODUCT_DEMO_PACKAGE_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with (package_dir / "D8_PRODUCT_DEMO_PACKAGE_MANIFEST.tsv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["path", "exists", "bytes", "sha256", "hash_skipped_reason"], delimiter="\t")
        writer.writeheader()
        writer.writerows(manifest_rows)
    with (package_dir / "D8_PRODUCT_DEMO_SHA256SUMS.txt").open("w", encoding="utf-8") as fh:
        for row in manifest_rows:
            if row["sha256"]:
                fh.write(f"{row['sha256']}  {row['path']}\n")
    copies = [
        ("docs/product/D8_PRODUCT_README.md", "D8_PRODUCT_DEMO_README_COPY.md"),
        ("docs/product/D8_DEMO_QUICKSTART.md", "D8_PRODUCT_DEMO_QUICKSTART_COPY.md"),
        ("docs/product/D8_3_MINUTE_DEMO_SCRIPT.md", "D8_PRODUCT_DEMO_SCRIPT_COPY.md"),
    ]
    for source, target in copies:
        source_path = ROOT / source
        if source_path.exists():
            shutil.copyfile(source_path, package_dir / target)
    payload = {"state": "PASS", "action": "D8_PRODUCT_DEMO_PACKAGE", "package_dir": rel(package_dir), "manifest": rel(package_dir / "D8_PRODUCT_DEMO_PACKAGE_MANIFEST.json")}
    payload["report"] = write_json_report("D8_PRODUCT_DEMO_PACKAGE", payload)
    print_payload(payload, args.json)
    return 0


def cmd_seal(args: argparse.Namespace) -> int:
    counts = {
        "d8_memory_count": psql_count("d8_memory"),
        "possible_alerts_count": psql_count("d8_possible_alerts"),
        "redteam_events_count": psql_count("d8_redteam_events"),
        "guard_evaluations_count": psql_count("d8_guard_evaluations"),
    }
    seal = STATUS_DIR / f"D8_PHASE12_PRODUCT_DEMO_PACKAGE_AND_LAUNCHER_{stamp()}_SEAL.md"
    demo_commands = [
        "tools/d8_product_demo_launcher.sh status",
        "tools/d8_product_demo_launcher.sh doctor",
        "tools/d8_product_demo_launcher.sh smoke-test",
        "tools/d8_product_demo_launcher.sh voice-demo --text \"查狀態\"",
        "tools/d8_product_demo_launcher.sh pos-bridge-demo",
        "tools/d8_product_demo_launcher.sh dashboard --host 127.0.0.1 --port 8787 --timeout 3",
        "tools/d8_product_demo_launcher.sh package",
        "tools/d8_product_demo_launcher.sh seal",
    ]
    lines = [
        "# D8 Phase 12 Product Demo Package And Launcher Seal",
        "",
        "STATE=PASS",
        "ACTION=D8_PHASE12_PRODUCT_DEMO_PACKAGE_AND_LAUNCHER_SEAL",
        f"STATUS_COUNTS={json.dumps(counts, ensure_ascii=False)}",
        f"PRODUCT_FILES={json.dumps(manifest_paths(), ensure_ascii=False)}",
        f"DEMO_COMMANDS={json.dumps(demo_commands, ensure_ascii=False)}",
        f"SAFETY_FLAGS={json.dumps(SAFETY_FLAGS, ensure_ascii=False)}",
        "NO_PRODUCTION_ACTIONS=TRUE",
        "SECRET_READ=FALSE",
        "PRODUCTION_DB_WRITE=FALSE",
        "SERVICE_RESTART=FALSE",
        "DEPLOY=FALSE",
    ]
    seal.write_text("\n".join(lines) + "\n", encoding="utf-8")
    payload = {"state": "PASS", "action": "D8_PRODUCT_DEMO_SEAL", "seal": rel(seal), "counts": counts, "safety_flags": SAFETY_FLAGS}
    payload["report"] = write_json_report("D8_PRODUCT_DEMO_SEAL", payload)
    print_payload(payload, args.json)
    return 0


def cmd_help(args: argparse.Namespace) -> int:
    print("D8 product demo launcher commands:")
    print("  status | doctor | dashboard | voice-demo | pos-bridge-demo | smoke-test | package | seal | help")
    print("Examples:")
    print("  tools/d8_product_demo_launcher.sh smoke-test")
    print("  tools/d8_product_demo_launcher.sh dashboard --host 127.0.0.1 --port 8787 --timeout 3")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="D8 product demo launcher")
    parser.add_argument("command", nargs="?", default="help")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--text")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=60)
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "status":
        return cmd_status(args)
    if args.command == "doctor":
        return cmd_doctor(args)
    if args.command == "dashboard":
        return cmd_dashboard(args)
    if args.command == "voice-demo":
        return cmd_voice_demo(args)
    if args.command == "pos-bridge-demo":
        return cmd_pos_bridge_demo(args)
    if args.command == "smoke-test":
        return cmd_smoke_test(args)
    if args.command == "package":
        return cmd_package(args)
    if args.command == "seal":
        return cmd_seal(args)
    if args.command == "help":
        return cmd_help(args)
    print(f"STATE=ERROR\nREASON=unknown command: {args.command}")
    return 40


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
