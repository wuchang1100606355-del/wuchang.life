#!/usr/bin/env python3
"""Collect Windows GPT/Codex repair outputs and decide completion evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


READINESS_REPORT = "WINDOWS_GPT_CODEX_READINESS_REPORT.json"
READINESS_SEAL = "READINESS_EVIDENCE_SEAL.txt"
TRIAGE_REPORT = "WINDOWS_GPT_CODEX_TRIAGE_SUMMARY.json"
REPAIR_REPORT = "WINDOWS_GPT_CODEX_REPAIR_REPORT.json"
LAUNCH_REPORT = "FULL_REPAIR_LAUNCH_REPORT.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def parse_seal(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def newest(paths: list[Path]) -> Path | None:
    existing = [path for path in paths if path.exists()]
    if not existing:
        return None
    return max(existing, key=lambda path: path.stat().st_mtime)


def find_named(root: Path, name: str) -> list[Path]:
    return sorted(root.rglob(name))


def verify_readiness_seal(readiness_path: Path) -> dict[str, Any]:
    seal_path = readiness_path.with_name(READINESS_SEAL)
    if not seal_path.exists():
        return {"seal_found": False, "passed": False, "failures": ["readiness_seal_missing"]}
    seal = parse_seal(seal_path)
    failures: list[str] = []
    expected_report = seal.get("readiness_report_sha256")
    if expected_report and expected_report != sha256(readiness_path):
        failures.append("readiness_report_sha256_mismatch")
    summary_path_text = seal.get("readiness_summary")
    summary_hash = seal.get("readiness_summary_sha256")
    if summary_path_text and summary_hash:
        summary_path = Path(summary_path_text)
        if not summary_path.exists():
            sibling = readiness_path.with_name(summary_path.name)
            summary_path = sibling
        if not summary_path.exists():
            failures.append("readiness_summary_missing")
        elif sha256(summary_path) != summary_hash:
            failures.append("readiness_summary_sha256_mismatch")
    return {
        "seal_found": True,
        "seal_path": str(seal_path),
        "seal": seal,
        "failures": failures,
        "passed": not failures,
    }


def classify_readiness(report: dict[str, Any]) -> dict[str, Any]:
    state = report.get("state", "")
    failures = list(report.get("failures", []))
    warnings = list(report.get("warnings", []))
    codex = report.get("codex", {})
    endpoints = report.get("endpoints", [])
    api_status = None
    for endpoint in endpoints:
        if endpoint.get("name") == "openai_api":
            api_status = endpoint.get("https_head", {}).get("status_code")
    completion_ready = (
        state == "PASS_WINDOWS_GPT_CODEX_READINESS"
        and bool(codex.get("present"))
        and bool(codex.get("version", {}).get("ok"))
        and api_status in {200, 401}
        and not failures
    )
    return {
        "state": state,
        "completion_ready": completion_ready,
        "codex_present": bool(codex.get("present")),
        "codex_version_ok": bool(codex.get("version", {}).get("ok")),
        "openai_api_status": api_status,
        "failures": failures,
        "warnings": warnings,
    }


def summarize_launch_report(path: Path | None) -> dict[str, Any]:
    if not path:
        return {
            "found": False,
            "reason": "launch_report_missing",
        }
    try:
        report = read_json(path)
    except Exception as exc:  # pragma: no cover - diagnostic script
        return {
            "found": True,
            "path": str(path),
            "sha256": sha256(path),
            "read_ok": False,
            "error": str(exc),
        }
    side_effects = report.get("side_effects", {})
    return {
        "found": True,
        "path": str(path),
        "sha256": sha256(path),
        "read_ok": True,
        "state": report.get("state", ""),
        "completion_ready": bool(report.get("completion_ready")),
        "repair_user_path_requested": bool(report.get("repair_user_path_requested")),
        "may_change_user_path": bool(side_effects.get("may_change_user_path")),
        "actual_changes_user_path": bool(side_effects.get("actual_changes_user_path")),
        "repair_state": report.get("repair_state", {}),
        "readiness_state": report.get("readiness_state", {}),
    }


def summarize_repair_report(path: Path | None) -> dict[str, Any]:
    if not path:
        return {
            "found": False,
            "reason": "repair_report_missing",
        }
    try:
        report = read_json(path)
    except Exception as exc:  # pragma: no cover - diagnostic script
        return {
            "found": True,
            "path": str(path),
            "sha256": sha256(path),
            "read_ok": False,
            "error": str(exc),
        }
    return {
        "found": True,
        "path": str(path),
        "sha256": sha256(path),
        "read_ok": True,
        "state": report.get("state", ""),
        "changes_user_path": bool(report.get("side_effects", {}).get("changes_user_path")),
        "codex_initial_present": bool(report.get("commands", {}).get("codex", {}).get("present")),
        "codex_post_repair_present": bool(report.get("post_repair_commands", {}).get("codex", {}).get("present")),
        "codex_post_repair_version_ok": bool(report.get("post_repair_versions", {}).get("codex", {}).get("ok")),
    }


def infer_package_root(roots: list[Path]) -> Path:
    if not roots:
        return Path(".").resolve()
    root = roots[0]
    if root.name == "evidence_from_windows_current":
        return root.parent
    return root


def build_next_action(roots: list[Path], readiness_summary: dict[str, Any]) -> dict[str, Any]:
    package_root = infer_package_root(roots)
    if readiness_summary.get("completion_ready"):
        return {
            "state": "NO_ACTION_REQUIRED",
            "message": "Windows GPT/Codex repair evidence is verified.",
            "windows_primary_entrypoint": "",
            "windows_read_only_entrypoint": "",
            "linux_collect_command": "bash ./COLLECT_WINDOWS_RESULTS.sh",
            "linux_wait_command": "bash ./WAIT_FOR_WINDOWS_RESULTS.sh 1800 10",
        }
    reason = str(readiness_summary.get("reason") or "unknown")
    if reason == "readiness_report_missing":
        message = (
            "Windows-side readiness evidence has not been captured. "
            "Run the one-click Windows repair entrypoint from the package root, then collect again."
        )
    elif reason == "readiness_seal_failed":
        message = (
            "Windows readiness evidence exists but its seal failed. "
            "Start a fresh batch and rerun the one-click Windows repair entrypoint."
        )
    else:
        message = (
            "Windows readiness evidence is present but not complete. "
            "Review the readiness report, then rerun the one-click Windows repair entrypoint if needed."
        )
    return {
        "state": "WINDOWS_ACTION_REQUIRED",
        "reason": reason,
        "message": message,
        "package_root": str(package_root),
        "windows_primary_entrypoint": "00_DOUBLE_CLICK_REPAIR_WINDOWS_GPT_CODEX.cmd",
        "windows_read_only_entrypoint": "00_DOUBLE_CLICK_DIAGNOSE_WINDOWS_GPT_CODEX.cmd",
        "windows_primary_entrypoint_legacy": "RUN_WINDOWS_ONE_CLICK_REPAIR_KEEP_OPEN.cmd",
        "windows_read_only_entrypoint_legacy": "RUN_WINDOWS_ONE_CLICK_DIAGNOSE_KEEP_OPEN.cmd",
        "windows_expected_sync_root": str(package_root / "evidence_from_windows_current"),
        "linux_collect_command": "bash ./COLLECT_WINDOWS_RESULTS.sh",
        "linux_wait_command": "bash ./WAIT_FOR_WINDOWS_RESULTS.sh 1800 10",
    }


def find_named_many(roots: list[Path], name: str) -> list[Path]:
    paths: list[Path] = []
    for root in roots:
        if root.exists():
            paths.extend(find_named(root, name))
    return sorted(set(paths))


def collect(roots: list[Path]) -> dict[str, Any]:
    readiness_reports = find_named_many(roots, READINESS_REPORT)
    triage_reports = find_named_many(roots, TRIAGE_REPORT)
    repair_reports = find_named_many(roots, REPAIR_REPORT)
    launch_reports = find_named_many(roots, LAUNCH_REPORT)

    latest_readiness = newest(readiness_reports)
    latest_triage = newest(triage_reports)
    latest_repair = newest(repair_reports)
    latest_launch = newest(launch_reports)

    readiness_summary: dict[str, Any] = {
        "found": False,
        "completion_ready": False,
        "reason": "readiness_report_missing",
    }
    if latest_readiness:
        report = read_json(latest_readiness)
        seal_check = verify_readiness_seal(latest_readiness)
        classified = classify_readiness(report)
        readiness_summary = {
            "found": True,
            "path": str(latest_readiness),
            "sha256": sha256(latest_readiness),
            "seal_check": seal_check,
            **classified,
            "completion_ready": bool(classified["completion_ready"] and seal_check["passed"]),
        }
        if not seal_check["passed"]:
            readiness_summary["reason"] = "readiness_seal_failed"
        elif not classified["completion_ready"]:
            readiness_summary["reason"] = "readiness_state_not_complete"
        else:
            readiness_summary["reason"] = "readiness_complete"

    state = "PASS_WINDOWS_GPT_CODEX_REPAIR_VERIFIED" if readiness_summary["completion_ready"] else "HOLD_WINDOWS_GPT_CODEX_REPAIR_NOT_VERIFIED"
    return {
        "schema": "TAIJI_WINDOWS_GPT_CODEX_RESULT_COLLECTION_V1",
        "state": state,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "roots": [str(root) for root in roots],
        "counts": {
            "readiness_reports": len(readiness_reports),
            "triage_reports": len(triage_reports),
            "repair_reports": len(repair_reports),
            "launch_reports": len(launch_reports),
        },
        "latest": {
            "readiness_report": str(latest_readiness) if latest_readiness else "",
            "triage_report": str(latest_triage) if latest_triage else "",
            "repair_report": str(latest_repair) if latest_repair else "",
            "launch_report": str(latest_launch) if latest_launch else "",
        },
        "readiness": readiness_summary,
        "repair": summarize_repair_report(latest_repair),
        "launch": summarize_launch_report(latest_launch),
        "next_action": build_next_action(roots, readiness_summary),
        "side_effects": {
            "installs_packages": False,
            "changes_network_settings": False,
            "changes_user_path": False,
            "reads_secret_values": False,
            "external_api_mutation": False,
        },
    }


def write_outputs(collection: dict[str, Any], out_dir: Path) -> tuple[Path, Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "WINDOWS_GPT_CODEX_RESULT_COLLECTION.json"
    text_path = out_dir / "WINDOWS_GPT_CODEX_RESULT_COLLECTION.txt"
    seal_path = out_dir / "WINDOWS_GPT_CODEX_RESULT_COLLECTION_SEAL.txt"

    json_path.write_text(json.dumps(collection, ensure_ascii=False, indent=2), encoding="utf-8")
    readiness = collection["readiness"]
    lines = [
        "TAIJI_WINDOWS_GPT_CODEX_RESULT_COLLECTION_V1",
        f"generated_at_utc={collection['generated_at_utc']}",
        f"state={collection['state']}",
        f"roots={';'.join(collection['roots'])}",
        f"readiness_found={readiness.get('found')}",
        f"completion_ready={readiness.get('completion_ready')}",
        f"reason={readiness.get('reason')}",
        f"latest_readiness={collection['latest']['readiness_report']}",
        f"latest_repair={collection['latest']['repair_report']}",
        f"latest_launch={collection['latest']['launch_report']}",
        f"repair_changes_user_path={collection['repair'].get('changes_user_path')}",
        f"repair_codex_post_repair_present={collection['repair'].get('codex_post_repair_present')}",
        f"launch_actual_changes_user_path={collection['launch'].get('actual_changes_user_path')}",
        f"launch_state={collection['launch'].get('state', '')}",
        f"launch_completion_ready={collection['launch'].get('completion_ready')}",
        f"launch_readiness_state={collection['launch'].get('readiness_state', {}).get('state', '')}",
        f"next_action_state={collection['next_action'].get('state', '')}",
        f"next_action_message={collection['next_action'].get('message', '')}",
        f"windows_primary_entrypoint={collection['next_action'].get('windows_primary_entrypoint', '')}",
        f"windows_read_only_entrypoint={collection['next_action'].get('windows_read_only_entrypoint', '')}",
        f"linux_collect_command={collection['next_action'].get('linux_collect_command', '')}",
        f"linux_wait_command={collection['next_action'].get('linux_wait_command', '')}",
    ]
    text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    seal_lines = [
        "schema=TAIJI_WINDOWS_GPT_CODEX_RESULT_COLLECTION_SEAL_V1",
        f"generated_at_utc={datetime.now(timezone.utc).isoformat()}",
        f"collection_json={json_path}",
        f"collection_json_sha256={sha256(json_path)}",
        f"collection_text={text_path}",
        f"collection_text_sha256={sha256(text_path)}",
        "side_effects.installs_packages=false",
        "side_effects.changes_network_settings=false",
        "side_effects.changes_user_path=false",
        "side_effects.reads_secret_values=false",
        "side_effects.external_api_mutation=false",
    ]
    seal_path.write_text("\n".join(seal_lines) + "\n", encoding="utf-8")
    return json_path, text_path, seal_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roots", nargs="+", type=Path, help="Root directories containing Windows repair evidence.")
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args()

    roots = [root.resolve() for root in args.roots]
    missing_roots = [str(root) for root in roots if not root.exists()]
    if missing_roots:
        raise SystemExit(f"root not found: {', '.join(missing_roots)}")
    out_dir = args.out_dir.resolve() if args.out_dir else roots[0] / "result_collection"
    collection = collect(roots)
    json_path, text_path, seal_path = write_outputs(collection, out_dir)

    print(f"STATE={collection['state']}")
    print(f"COLLECTION_JSON={json_path}")
    print(f"COLLECTION_TEXT={text_path}")
    print(f"COLLECTION_SEAL={seal_path}")
    return 0 if collection["state"] == "PASS_WINDOWS_GPT_CODEX_REPAIR_VERIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
