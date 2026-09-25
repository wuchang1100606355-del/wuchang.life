#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W7TP Commit Envelope Gate.

Read-only staged commit gate:
- does not write repo files
- does not stage files
- does not commit
- does not read secrets, env, DB, router, or network
- wraps staged classifier, py_compile, refined secret value scan, and safe selftests

Total Field boundaries:
- af7d186 router USB governance is sealed; this gate only classifies references.
- a5fde27 member sovereignty + AI quality gates is sealed; this gate only classifies references.
- ffff3fe synthetic generator sandbox remains an independent tooling lane.
- mode-only permission hygiene must not mix with functional changes.
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[1]
CLASSIFIER = ROOT / "tools" / "w7tp_staged_packet_classifier.py"

REFINED_SECRET_VALUE_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\b(?:access_token|refresh_token|client_secret|router_password)\s*[:=]\s*[A-Za-z0-9_./+=:-]{8,}", re.IGNORECASE),
]

SAFE_SELFTESTS = {
    "tools/w7tp_synthetic_seed_fixture_generator.py": ["python3", "tools/w7tp_synthetic_seed_fixture_generator.py", "--selftest"],
    "tools/w7tp_candidate_packet_extractor.py": ["python3", "tools/w7tp_candidate_packet_extractor.py", "--selftest"],
    "tools/w7tp_staged_packet_classifier.py": ["python3", "tools/w7tp_staged_packet_classifier.py"],
    "tools/w7tp_runtime_artifact_guard.py": ["python3", "tools/w7tp_runtime_artifact_guard.py"],
    "tools/w7tp_mode_only_permission_decision.py": ["python3", "tools/w7tp_mode_only_permission_decision.py", "--staged"],
}


def run_cmd(cmd: List[str], check: bool = False) -> Dict[str, object]:
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    result = {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "ok": proc.returncode == 0,
    }
    if check and proc.returncode != 0:
        raise RuntimeError(json.dumps(result, ensure_ascii=False))
    return result


def staged_entries() -> List[Dict[str, str]]:
    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-status"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    entries = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        entries.append({"status": parts[0], "path": parts[-1]})
    return entries


def run_classifier() -> Dict[str, object]:
    proc = run_cmd(["python3", str(CLASSIFIER.relative_to(ROOT))])
    try:
        parsed = json.loads(str(proc["stdout"] or "{}"))
    except json.JSONDecodeError:
        parsed = {"STATE": "HOLD_CLASSIFIER_JSON_PARSE_FAILED"}
    return {
        "ok": proc["returncode"] == 0 and str(parsed.get("STATE", "")).startswith("PASS_"),
        "returncode": proc["returncode"],
        "result": parsed,
        "stderr": proc["stderr"],
    }


def py_compile_staged_python(entries: List[Dict[str, str]]) -> List[Dict[str, object]]:
    results = []
    for entry in entries:
        path = entry["path"]
        if entry["status"].startswith("D") or not path.endswith(".py"):
            continue
        result = run_cmd(["python3", "-m", "py_compile", path])
        results.append({
            "path": path,
            "ok": result["ok"],
            "returncode": result["returncode"],
            "stderr": result["stderr"],
        })
    return results


def staged_file_text(path: str) -> str:
    proc = subprocess.run(
        ["git", "show", ":%s" % path],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        errors="replace",
    )
    return proc.stdout if proc.returncode == 0 else ""


def refined_secret_value_check(entries: List[Dict[str, str]]) -> Dict[str, object]:
    hits = []
    for entry in entries:
        path = entry["path"]
        if entry["status"].startswith("D"):
            continue
        text = staged_file_text(path)
        for lineno, line in enumerate(text.splitlines(), 1):
            for pattern in REFINED_SECRET_VALUE_PATTERNS:
                if pattern.search(line):
                    hits.append({"path": path, "line": lineno, "pattern": pattern.pattern})
                    break
    return {
        "STATE": "REFINED_SECRET_VALUE_CHECK_PASS" if not hits else "REFINED_SECRET_VALUE_CHECK_HOLD",
        "hits": hits,
        "ok": not hits,
    }


def run_safe_selftests(entries: List[Dict[str, str]]) -> List[Dict[str, object]]:
    staged_paths = {entry["path"] for entry in entries if not entry["status"].startswith("D")}
    results = []
    for path, cmd in SAFE_SELFTESTS.items():
        if path not in staged_paths:
            continue
        result = run_cmd(cmd)
        results.append({
            "path": path,
            "cmd": cmd,
            "ok": result["ok"],
            "returncode": result["returncode"],
            "stdout": result["stdout"],
            "stderr": result["stderr"],
        })
    return results


def decide(classifier: Dict[str, object], compile_results: List[Dict[str, object]], secret_check: Dict[str, object], selftests: List[Dict[str, object]]) -> str:
    if not classifier["ok"]:
        return "HOLD_COMMIT_ENVELOPE_CLASSIFIER"
    if any(not item["ok"] for item in compile_results):
        return "HOLD_COMMIT_ENVELOPE_PY_COMPILE"
    if not secret_check["ok"]:
        return "HOLD_COMMIT_ENVELOPE_REFINED_SECRET_VALUE"
    if any(not item["ok"] for item in selftests):
        return "HOLD_COMMIT_ENVELOPE_SELFTEST"
    return "PASS_COMMIT_ENVELOPE_READY"


def main() -> int:
    entries = staged_entries()
    classifier = run_classifier()
    compile_results = py_compile_staged_python(entries)
    secret_check = refined_secret_value_check(entries)
    selftests = run_safe_selftests(entries)
    decision = decide(classifier, compile_results, secret_check, selftests)
    result = {
        "STATE": decision,
        "decision": decision,
        "staged_files": entries,
        "classifier": classifier,
        "py_compile": compile_results,
        "refined_secret_value_check": secret_check,
        "selftests": selftests,
        "writes_repo": False,
        "auto_stage": False,
        "auto_commit": False,
        "deploy": False,
        "db_write": False,
        "router_restart": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if decision.startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
