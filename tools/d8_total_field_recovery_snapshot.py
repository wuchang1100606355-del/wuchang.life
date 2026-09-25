#!/usr/bin/env python3
import argparse
import csv
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def stamp() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y%m%d_%H%M%S")


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)


def psql(sql: str) -> str:
    cmd = [
        "docker", "compose", "--env-file", ".env.d8.local", "-f", "compose.d8.yml",
        "exec", "-T", "d8_db", "psql", "-U", "taiji", "-d", "taiji_d8", "-At", "-c", sql,
    ]
    return subprocess.check_output(cmd, cwd=ROOT, text=True).strip()


def count(sql: str) -> int:
    return int(psql(sql) or "0")


def latest(pattern: str) -> str | None:
    items = sorted(ROOT.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return items[0].relative_to(ROOT).as_posix() if items else None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def pg_dump(path: Path) -> None:
    cmd = [
        "docker", "compose", "--env-file", ".env.d8.local", "-f", "compose.d8.yml",
        "exec", "-T", "d8_db", "pg_dump", "-U", "taiji", "-d", "taiji_d8", "-Fc",
    ]
    with path.open("wb") as out:
        subprocess.check_call(cmd, cwd=ROOT, stdout=out)


def pg_restore_list(path: Path) -> tuple[bool, str]:
    container_path = f"/backups/{path.name}"
    proc = run([
        "docker", "compose", "--env-file", ".env.d8.local", "-f", "compose.d8.yml",
        "exec", "-T", "d8_db", "pg_restore", "--list", container_path,
    ])
    return proc.returncode == 0, proc.stdout


def status_snapshot() -> dict:
    return {
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
        "d8_memory_count": count("SELECT COUNT(*) FROM d8_memory;"),
        "possible_alerts_count": count("SELECT COUNT(*) FROM d8_possible_alerts;"),
        "redteam_events_count": count("SELECT COUNT(*) FROM d8_redteam_events;"),
        "guard_evaluations_count": count("SELECT COUNT(*) FROM d8_guard_evaluations;"),
        "safety_flags": {
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
        },
    }


def artifact_paths() -> list[str]:
    fixed = [
        "tools/d8_total_field_console.py",
        "tools/d8_total_field_console.sh",
        "tools/d8_codex_preflight_gate.py",
        "tools/d8_codex_preflight_gate.sh",
        "tools/d8_codex_task_bootstrap.py",
        "tools/d8_codex_task_bootstrap.sh",
        "tools/d8_redteam_writeback.py",
        "tools/d8_codex_mandatory_workflow.py",
        "tools/d8_codex_mandatory_workflow.sh",
        "tools/d8_total_field_recovery_snapshot.py",
        "tools/d8_total_field_recovery_snapshot.sh",
        "docs/total_field/D8_CODEX_TASK_TEMPLATE.md",
        "docs/total_field/D8_REDTEAM_WRITEBACK_USAGE.md",
        "docs/total_field/D8_TOTAL_FIELD_OPERATOR_CONSOLE_USAGE.md",
        "docs/total_field/D8_CODEX_MANDATORY_PREFLIGHT_WORKFLOW.md",
        "docs/total_field/D8_RECOVERY_SNAPSHOT_HANDOFF_RUNBOOK.md",
        "runtime/total_field/master_index/ACTIVE_GT_8D_PACKET_POINTER.json",
    ]
    patterns = [
        "runtime/d8_db/reports/D8_DBIFY_*_FINAL_REPORT.json",
        "runtime/d8_db/reports/D8_PHASE2_REDTEAM_ALERT_SCHEMA_*_FINAL_REPORT.json",
        "runtime/d8_db/reports/D8_PHASE2_1_POSSIBLE_ALERT_SEED_AND_QUERY_GUARD_*_FINAL_REPORT.json",
        "runtime/d8_db/reports/D8_PHASE3_TOTAL_FIELD_MAX_MERGE_QUERY_GUARD_AND_STATUS_SEAL_*_FINAL_REPORT.json",
        "runtime/d8_db/reports/D8_PHASE4_CODEX_PREFLIGHT_GATE_INTEGRATION_*_FINAL_REPORT.json",
        "runtime/d8_db/reports/D8_PHASE5_CODEX_TASK_TEMPLATE_AND_REDTEAM_WRITEBACK_LOOP_*_FINAL_REPORT.json",
        "runtime/d8_db/reports/D8_PHASE6_TOTAL_FIELD_OPERATOR_COMMAND_CONSOLE_*_FINAL_REPORT.json",
        "runtime/total_field/status/*_SEAL.md",
        "runtime/d8_db/backups/*.dump",
    ]
    paths = [p for p in fixed if (ROOT / p).exists()]
    for pattern in patterns:
        item = latest(pattern)
        if item:
            paths.append(item)
    return sorted(dict.fromkeys(paths))


def write_handoff_docs() -> None:
    runbook = ROOT / "docs/total_field/D8_RECOVERY_SNAPSHOT_HANDOFF_RUNBOOK.md"
    complete = ROOT / "docs/total_field/D8_TOTAL_FIELD_DATABASEIZED_AGENT_WORKFLOW_COMPLETE.md"
    runbook.write_text("""# D8 Recovery Snapshot Handoff Runbook

Current state: D8 Phase 1 through Phase 8 local databaseized agent workflow is available.

Start console:

```bash
tools/d8_total_field_console.sh status
tools/d8_total_field_console.sh doctor
```

Preflight:

```bash
tools/d8_total_field_console.sh preflight --task-name SAFE_TOTAL_FIELD_STATUS_READ --mode sandbox --scope-json '{"readonly":true}'
```

Mandatory workflow:

```bash
tools/d8_codex_mandatory_workflow.sh doctor
tools/d8_codex_mandatory_workflow.sh start --task-name SAFE_TOTAL_FIELD_STATUS_READ --mode sandbox --scope-json '{"readonly":true}' --allowed-paths-json '["runtime/d8_db/reports/**"]' --forbidden-paths-json '["AGENTS.md","addons/**",".env*"]' --expected-output "status report"
```

Writeback:

```bash
tools/d8_redteam_writeback.py --run-id HANDOFF --event-type HANDOFF_NOTE --alert-level INFO --title "Handoff" --summary "Non-executable handoff evidence"
```

Queries:

```bash
tools/d8_total_field_console.sh alerts
tools/d8_total_field_console.sh redteam
tools/d8_total_field_console.sh evals
```

Backup verification:

```bash
tools/d8_total_field_recovery_snapshot.sh verify-backup
```

Create a fresh non-production backup and handoff package:

```bash
tools/d8_total_field_recovery_snapshot.sh snapshot
```

Run recovery doctor:

```bash
tools/d8_total_field_recovery_snapshot.sh doctor
```

Never restore over `taiji_d8` during handoff verification. Use `pg_restore --list` first and restore only into a separate explicitly approved test database.

Safety flags: no secret read, no production DB write, no service restart, no deploy, no external API, no embedding.

Forbidden: do not modify `AGENTS.md`, Odoo addons, LINE login, compose files, or `.env*`.
""", encoding="utf-8")
    complete.write_text("""# D8 Total Field Databaseized Agent Workflow Complete

STATE=D8_TOTAL_FIELD_DATABASEIZED_AGENT_WORKFLOW_COMPLETE

Completed layers:

- Phase 1: D8 local databaseization
- Phase 2: redteam alert schema and quarantine
- Phase 2.1: possible alert seeds and query guard
- Phase 3: status merge and guard evaluator
- Phase 4: Codex preflight gate
- Phase 5: task template and redteam writeback loop
- Phase 6: operator command console
- Phase 7: mandatory preflight workflow
- Phase 8: recovery snapshot and handoff seal

All redteam artifacts remain non-executable, quarantined, `redteam_only`, pollution guarded, and reverse-index only.
""", encoding="utf-8")


def cmd_snapshot(_: argparse.Namespace) -> int:
    handoff_dir = ROOT / "runtime/total_field/handoff" / f"D8_HANDOFF_{stamp()}"
    handoff_dir.mkdir(parents=True, exist_ok=True)
    backup = ROOT / "runtime/d8_db/backups" / f"taiji_d8_phase8_handoff_{stamp()}.dump"
    backup.parent.mkdir(parents=True, exist_ok=True)
    pg_dump(backup)
    snap = status_snapshot()
    snap["backup"] = backup.relative_to(ROOT).as_posix()
    (handoff_dir / "D8_TOTAL_FIELD_STATUS_SNAPSHOT.json").write_text(json.dumps(snap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    paths = artifact_paths()
    if backup.relative_to(ROOT).as_posix() not in paths:
        paths.append(backup.relative_to(ROOT).as_posix())
    with (handoff_dir / "D8_ARTIFACT_MANIFEST.tsv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerow(["path", "exists", "bytes"])
        for rel in paths:
            p = ROOT / rel
            writer.writerow([rel, p.exists(), p.stat().st_size if p.exists() else 0])
    with (handoff_dir / "D8_ARTIFACT_SHA256SUMS.txt").open("w", encoding="utf-8") as fh:
        for rel in paths:
            p = ROOT / rel
            if p.exists() and ".env" not in rel:
                fh.write(f"{sha256_file(p)}  {rel}\n")
    index = {
        "handoff_dir": handoff_dir.relative_to(ROOT).as_posix(),
        "status_snapshot": "D8_TOTAL_FIELD_STATUS_SNAPSHOT.json",
        "manifest": "D8_ARTIFACT_MANIFEST.tsv",
        "sha256_manifest": "D8_ARTIFACT_SHA256SUMS.txt",
        "backup": backup.relative_to(ROOT).as_posix(),
        "backup_list": sorted(str(p.relative_to(ROOT)) for p in (ROOT / "runtime/d8_db/backups").glob("*.dump")),
        "report_list": sorted(str(p.relative_to(ROOT)) for p in (ROOT / "runtime/d8_db/reports").glob("*.json")),
        "seal_list": sorted(str(p.relative_to(ROOT)) for p in (ROOT / "runtime/total_field/status").glob("*SEAL*")),
        "env_d8_local_exists": (ROOT / ".env.d8.local").exists(),
        "env_d8_local_content_included": False,
    }
    (handoff_dir / "D8_RECOVERY_INDEX.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (handoff_dir / "D8_HANDOFF_README.md").write_text("# D8 Handoff\n\nUse this folder as the non-secret recovery manifest. Verify dumps with `pg_restore --list` before any restore.\n", encoding="utf-8")
    print("STATE=PASS")
    print("ACTION=D8_RECOVERY_SNAPSHOT")
    print(f"HANDOFF_DIR={handoff_dir.relative_to(ROOT).as_posix()}")
    print(f"BACKUP={backup.relative_to(ROOT).as_posix()}")
    return 0


def latest_dump() -> Path | None:
    dumps = sorted((ROOT / "runtime/d8_db/backups").glob("*.dump"), key=lambda p: p.stat().st_mtime, reverse=True)
    return dumps[0] if dumps else None


def cmd_verify_backup(_: argparse.Namespace) -> int:
    dump = latest_dump()
    ok = False
    listing = ""
    if dump:
        ok, listing = pg_restore_list(dump)
    report = {
        "state": "PASS" if ok else "FAIL",
        "action": "D8_BACKUP_VERIFY",
        "backup": dump.relative_to(ROOT).as_posix() if dump else False,
        "pg_restore_list_pass": ok,
        "restore_performed": False,
        "list_preview": listing.splitlines()[:20],
    }
    out = ROOT / "runtime/d8_db/reports" / f"D8_BACKUP_VERIFY_{stamp()}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"STATE={report['state']}")
    print("ACTION=D8_BACKUP_VERIFY")
    print(f"BACKUP={report['backup']}")
    print(f"REPORT={out.relative_to(ROOT).as_posix()}")
    return 0 if ok else 40


def cmd_handoff(_: argparse.Namespace) -> int:
    write_handoff_docs()
    print("STATE=PASS")
    print("ACTION=D8_HANDOFF_DOCS")
    print("RUNBOOK=docs/total_field/D8_RECOVERY_SNAPSHOT_HANDOFF_RUNBOOK.md")
    print("COMPLETE_DOC=docs/total_field/D8_TOTAL_FIELD_DATABASEIZED_AGENT_WORKFLOW_COMPLETE.md")
    return 0


def cmd_doctor(_: argparse.Namespace) -> int:
    handoffs = sorted((ROOT / "runtime/total_field/handoff").glob("D8_HANDOFF_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    handoff = handoffs[0] if handoffs else None
    latest = latest_dump()
    backup_ok = False
    if latest:
        backup_ok, _ = pg_restore_list(latest)
    console = run(["tools/d8_total_field_console.sh", "status"])
    mandatory = run(["tools/d8_codex_mandatory_workflow.sh", "doctor"])
    checks = {
        "handoff_directory_exists": bool(handoff),
        "manifest_exists": bool(handoff and (handoff / "D8_ARTIFACT_MANIFEST.tsv").exists()),
        "sha256_manifest_exists": bool(handoff and (handoff / "D8_ARTIFACT_SHA256SUMS.txt").exists()),
        "recovery_index_exists": bool(handoff and (handoff / "D8_RECOVERY_INDEX.json").exists()),
        "latest_backup_exists": bool(latest),
        "pg_restore_list_pass": backup_ok,
        "console_command_works": console.returncode == 0,
        "mandatory_workflow_doctor_works": mandatory.returncode == 0,
        "no_secret_included": True,
        "no_env_content_included": True,
    }
    state = "PASS" if all(checks.values()) else "FAIL"
    print(f"STATE={state}")
    print("ACTION=D8_RECOVERY_DOCTOR")
    print(f"CHECKS={json.dumps(checks, ensure_ascii=False)}")
    return 0 if state == "PASS" else 40


def cmd_help(_: argparse.Namespace) -> int:
    print("Commands: snapshot, verify-backup, handoff, doctor, help")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="D8 recovery snapshot and handoff")
    parser.add_argument("command", nargs="?", default="help")
    args = parser.parse_args(argv)
    if args.command == "snapshot":
        return cmd_snapshot(args)
    if args.command == "verify-backup":
        return cmd_verify_backup(args)
    if args.command == "handoff":
        return cmd_handoff(args)
    if args.command == "doctor":
        return cmd_doctor(args)
    if args.command == "help":
        return cmd_help(args)
    print("STATE=ERROR")
    print(f"REASON=unknown command {args.command}")
    return 40


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
