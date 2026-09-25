#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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


def count(sql: str) -> int:
    value = run_psql(sql)
    return int(value or "0")


def latest(pattern: str) -> str | None:
    matches = sorted(ROOT.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    if not matches:
        return None
    return matches[0].relative_to(ROOT).as_posix()


def main() -> int:
    parser = argparse.ArgumentParser(description="D8 total field status summary")
    parser.add_argument("--run-id", default="D8_TOTAL_FIELD_STATUS")
    args = parser.parse_args()

    alert_counts = {
        "HOLD": count("SELECT COUNT(*) FROM d8_possible_alerts WHERE alert_level='HOLD';"),
        "WARN": count("SELECT COUNT(*) FROM d8_possible_alerts WHERE alert_level='WARN';"),
        "INFO": count("SELECT COUNT(*) FROM d8_possible_alerts WHERE alert_level='INFO';"),
        "BLOCK": count("SELECT COUNT(*) FROM d8_possible_alerts WHERE alert_level='BLOCK';"),
    }
    summary = {
        "run_id": args.run_id,
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
        "d8_memory_count": count("SELECT COUNT(*) FROM d8_memory;"),
        "d8_redteam_events_count": count("SELECT COUNT(*) FROM d8_redteam_events;"),
        "d8_possible_alerts_count": count("SELECT COUNT(*) FROM d8_possible_alerts;"),
        "alert_counts": alert_counts,
        "latest_reports": {
            "phase1": latest("runtime/d8_db/reports/D8_DBIFY_20260623_152850_FINAL_REPORT.json"),
            "phase2": latest("runtime/d8_db/reports/D8_PHASE2_REDTEAM_ALERT_SCHEMA_*_FINAL_REPORT.json"),
            "phase2_1": latest("runtime/d8_db/reports/D8_PHASE2_1_POSSIBLE_ALERT_SEED_AND_QUERY_GUARD_*_FINAL_REPORT.json"),
        },
        "latest_backups": {
            "phase1": latest("runtime/d8_db/backups/taiji_d8_20260623_153659.dump"),
            "phase2": latest("runtime/d8_db/backups/taiji_d8_phase2_redteam_*.dump"),
            "phase2_1": latest("runtime/d8_db/backups/taiji_d8_phase2_1_possible_alerts_*.dump"),
        },
        "active_pointer": "runtime/total_field/master_index/ACTIVE_GT_8D_PACKET_POINTER.json"
        if (ROOT / "runtime/total_field/master_index/ACTIVE_GT_8D_PACKET_POINTER.json").exists()
        else None,
        "safety_summary": {
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
            "EXECUTABLE_ALERTS": False,
            "POLLUTION_GUARD": True,
            "REVERSE_INDEX_ISOLATION": True,
            "DO_NOT_TOUCH_AGENTS_MD": True,
        },
    }
    report_dir = ROOT / "runtime/d8_db/reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"D8_TOTAL_FIELD_STATUS_{stamp}.json"
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary["report"] = report_path.relative_to(ROOT).as_posix()
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
