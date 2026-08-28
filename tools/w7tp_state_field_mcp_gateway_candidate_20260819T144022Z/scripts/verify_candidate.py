#!/usr/bin/env python3
"""Run the complete local candidate verification without installing or enabling anything."""

from __future__ import annotations

import compileall
import hashlib
import json
import sys
import unittest
from pathlib import Path

from type_contract_check import check_contract


def verify_manifest(root: Path) -> tuple[bool, int]:
    manifest = root / "MANIFEST.sha256"
    if not manifest.exists():
        return False, 0
    checked = 0
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split("  ", 1)
        path = root / relative
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            return False, checked
        checked += 1
    return True, checked


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    syntax_ok = compileall.compile_dir(str(src), quiet=1)
    type_report = check_contract(root)
    suite = unittest.defaultTestLoader.discover(
        str(root / "tests"), top_level_dir=str(root)
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    manifest_ok, manifest_files = verify_manifest(root)
    summary = {
        "syntax": "PASS" if syntax_ok else "FAIL",
        "type_contract": type_report["status"],
        "annotated_functions_checked": type_report["checked_functions"],
        "resolved_runtime_callables": type_report["resolved_runtime_callables"],
        "unit_and_red_team_tests": "PASS" if result.wasSuccessful() else "FAIL",
        "tests_run": result.testsRun,
        "manifest": "PASS" if manifest_ok else "FAIL",
        "manifest_files": manifest_files,
        "formal_activation": False,
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if syntax_ok and type_report["status"] == "PASS" and result.wasSuccessful() and manifest_ok else 1


if __name__ == "__main__":
    sys.exit(main())
