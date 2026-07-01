#!/usr/bin/env python3
"""Wait for Windows GPT/Codex repair evidence and seal the observed result."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from collect_windows_gpt_codex_results import collect, sha256, write_outputs


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_wait_outputs(report: dict[str, Any], out_dir: Path) -> tuple[Path, Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "WINDOWS_GPT_CODEX_WAIT_REPORT.json"
    text_path = out_dir / "WINDOWS_GPT_CODEX_WAIT_REPORT.txt"
    seal_path = out_dir / "WINDOWS_GPT_CODEX_WAIT_REPORT_SEAL.txt"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    text_lines = [
        "TAIJI_WINDOWS_GPT_CODEX_WAIT_REPORT_V1",
        f"generated_at_utc={report['generated_at_utc']}",
        f"state={report['state']}",
        f"reason={report['reason']}",
        f"roots={';'.join(report['roots'])}",
        f"timeout_sec={report['timeout_sec']}",
        f"interval_sec={report['interval_sec']}",
        f"polls={report['polls']}",
        f"elapsed_sec={report['elapsed_sec']}",
        f"latest_collection_state={report['latest_collection'].get('state', '')}",
        f"latest_collection_json={report['latest_collection'].get('json_path', '')}",
    ]
    text_path.write_text("\n".join(text_lines) + "\n", encoding="utf-8")
    seal_lines = [
        "schema=TAIJI_WINDOWS_GPT_CODEX_WAIT_REPORT_SEAL_V1",
        f"generated_at_utc={utc_now()}",
        f"wait_report_json={json_path}",
        f"wait_report_json_sha256={sha256(json_path)}",
        f"wait_report_text={text_path}",
        f"wait_report_text_sha256={sha256(text_path)}",
        "side_effects.installs_packages=false",
        "side_effects.changes_network_settings=false",
        "side_effects.changes_user_path=false",
        "side_effects.reads_secret_values=false",
        "side_effects.external_api_mutation=false",
    ]
    collection_json = report["latest_collection"].get("json_path")
    collection_text = report["latest_collection"].get("text_path")
    collection_seal = report["latest_collection"].get("seal_path")
    if collection_json:
        seal_lines.append(f"collection_json={collection_json}")
        seal_lines.append(f"collection_json_sha256={sha256(Path(collection_json))}")
    if collection_text:
        seal_lines.append(f"collection_text={collection_text}")
        seal_lines.append(f"collection_text_sha256={sha256(Path(collection_text))}")
    if collection_seal:
        seal_lines.append(f"collection_seal={collection_seal}")
        seal_lines.append(f"collection_seal_sha256={sha256(Path(collection_seal))}")
    seal_path.write_text("\n".join(seal_lines) + "\n", encoding="utf-8")
    return json_path, text_path, seal_path


def run_wait(roots: list[Path], out_dir: Path, timeout_sec: float, interval_sec: float) -> dict[str, Any]:
    started = time.monotonic()
    polls = 0
    latest_collection_paths: tuple[Path, Path, Path] | None = None
    latest_collection: dict[str, Any] = {}
    deadline = started + timeout_sec

    while True:
        polls += 1
        latest_collection = collect(roots)
        latest_collection_paths = write_outputs(latest_collection, out_dir / "latest_collection")
        if latest_collection["state"] == "PASS_WINDOWS_GPT_CODEX_REPAIR_VERIFIED":
            state = "PASS_WINDOWS_GPT_CODEX_REPAIR_VERIFIED"
            reason = "windows_readiness_evidence_collected"
            break
        now = time.monotonic()
        if timeout_sec <= 0 or now >= deadline:
            state = "HOLD_WINDOWS_GPT_CODEX_REPAIR_WAIT_TIMEOUT"
            reason = latest_collection.get("readiness", {}).get("reason", "not_ready_before_timeout")
            break
        time.sleep(min(interval_sec, max(0.0, deadline - now)))

    elapsed = round(time.monotonic() - started, 3)
    collection_json, collection_text, collection_seal = latest_collection_paths or ("", "", "")
    return {
        "schema": "TAIJI_WINDOWS_GPT_CODEX_WAIT_REPORT_V1",
        "state": state,
        "reason": reason,
        "generated_at_utc": utc_now(),
        "roots": [str(root) for root in roots],
        "timeout_sec": timeout_sec,
        "interval_sec": interval_sec,
        "polls": polls,
        "elapsed_sec": elapsed,
        "latest_collection": {
            "state": latest_collection.get("state", ""),
            "readiness": latest_collection.get("readiness", {}),
            "repair": latest_collection.get("repair", {}),
            "launch": latest_collection.get("launch", {}),
            "counts": latest_collection.get("counts", {}),
            "json_path": str(collection_json),
            "text_path": str(collection_text),
            "seal_path": str(collection_seal),
        },
        "side_effects": {
            "installs_packages": False,
            "changes_network_settings": False,
            "changes_user_path": False,
            "reads_secret_values": False,
            "external_api_mutation": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roots", nargs="+", type=Path, help="Root directories containing synced Windows evidence.")
    parser.add_argument("--out-dir", type=Path, default=None, help="Directory for wait and collection reports.")
    parser.add_argument("--timeout-sec", type=float, default=1800.0, help="Maximum time to wait. Use 0 for one poll.")
    parser.add_argument("--interval-sec", type=float, default=10.0, help="Polling interval in seconds.")
    args = parser.parse_args()

    if args.interval_sec <= 0:
        raise SystemExit("--interval-sec must be positive")
    roots = [root.resolve() for root in args.roots]
    missing_roots = [str(root) for root in roots if not root.exists()]
    if missing_roots:
        raise SystemExit(f"root not found: {', '.join(missing_roots)}")
    out_dir = args.out_dir.resolve() if args.out_dir else roots[0] / "result_wait"

    report = run_wait(roots, out_dir, args.timeout_sec, args.interval_sec)
    json_path, text_path, seal_path = write_wait_outputs(report, out_dir)
    print(f"STATE={report['state']}")
    print(f"WAIT_JSON={json_path}")
    print(f"WAIT_TEXT={text_path}")
    print(f"WAIT_SEAL={seal_path}")
    return 0 if report["state"] == "PASS_WINDOWS_GPT_CODEX_REPAIR_VERIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
