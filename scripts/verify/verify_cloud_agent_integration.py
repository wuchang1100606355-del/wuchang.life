#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused verifier for Cloud -> XiaoJ -> Total Field integration."""

from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "CLOUD_AGENT_DIRECT_INTEGRATION_V0_1"
PROVIDER_PATH = ROOT / "tools/cloud_agent_candidate_provider.py"
XIAOJ_PATH = ROOT / "tools/xiaoj_candidate_adapter.py"
GATEWAY_PATH = ROOT / "tools/total_field_candidate_gateway.py"
RUNTIME_PATH = ROOT / "tools/tfct_true8d_runtime_candidate.py"
TEST_PATH = ROOT / "tests/test_cloud_agent_integration.py"
REQUIRED_FILES = (
    PROVIDER_PATH,
    XIAOJ_PATH,
    GATEWAY_PATH,
    RUNTIME_PATH,
    TEST_PATH,
)


class VerificationFailure(Exception):
    def __init__(self, reason_code: str, path: Path | str, line: int = 0) -> None:
        self.reason_code = reason_code
        self.path = str(path)
        self.line = line
        super().__init__(reason_code)


def _fail(reason_code: str, path: Path | str, line: int = 0) -> None:
    raise VerificationFailure(reason_code, path, line)


def _source(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        _fail("UTF8_READ_FAILED", path)


def _tree(path: Path) -> ast.AST:
    try:
        return ast.parse(_source(path), filename=str(path))
    except SyntaxError as exc:
        _fail("PYTHON_SYNTAX_INVALID", path, exc.lineno or 0)


def _verify_files() -> None:
    for path in REQUIRED_FILES:
        if not path.is_file():
            _fail("REQUIRED_FILE_MISSING", path)
        _tree(path)


def _function_names(tree: ast.AST) -> set[str]:
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _class_names(tree: ast.AST) -> set[str]:
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}


def _verify_provider() -> None:
    source = _source(PROVIDER_PATH)
    tree = _tree(PROVIDER_PATH)
    if "CloudCandidateProvider" not in _class_names(tree):
        _fail("CLOUD_PROVIDER_CLASS_MISSING", PROVIDER_PATH)
    if "generate_candidate" not in _function_names(tree):
        _fail("CLOUD_PROVIDER_METHOD_MISSING", PROVIDER_PATH)
    required = (
        "GOOGLE_APPLICATION_CREDENTIALS",
        "google.auth.default",
        "AuthorizedSession",
        '"source_mode": SOURCE_MODE',
        '"provider_ref": PROVIDER_REF',
        '"model_ref": MODEL_REF',
        '"candidate_only": True',
        "CLOUD_FORBIDDEN_AUTHORITY_OUTPUT",
    )
    for marker in required:
        if marker not in source:
            _fail("CLOUD_PROVIDER_CONTRACT_MISSING", PROVIDER_PATH)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {"open", "print"}:
                _fail("CREDENTIAL_READ_OR_OUTPUT_API_FORBIDDEN", PROVIDER_PATH, node.lineno)
    forbidden_imports = {"sqlite3", "subprocess", "psycopg", "psycopg2", "odoo"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots = {alias.name.split(".")[0] for alias in node.names}
            if roots & forbidden_imports:
                _fail("SIDE_EFFECT_IMPORT_FORBIDDEN", PROVIDER_PATH, node.lineno)
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in forbidden_imports:
                _fail("SIDE_EFFECT_IMPORT_FORBIDDEN", PROVIDER_PATH, node.lineno)


def _verify_xiaoj() -> None:
    source = _source(XIAOJ_PATH)
    required = (
        "CloudCandidateProvider as GCPCloudCandidateProvider",
        "def cloud_push(",
        "selected_provider.generate_candidate(prompt, context_copy)",
        "build_candidate_envelope(",
        'payload["candidate_only"] = True',
        "total_field_receive_candidate(",
    )
    for marker in required:
        if marker not in source:
            _fail("XIAOJ_CLOUD_INTEGRATION_MISSING", XIAOJ_PATH)
    if source.count("total_field_receive_candidate(") != 1:
        _fail("XIAOJ_MULTIPLE_SUBMISSION_PATHS", XIAOJ_PATH)


def _verify_gateway() -> None:
    source = _source(GATEWAY_PATH)
    required = (
        "CLOUD_AUTHORITY_RESULT_KEYS",
        "RESERVED_CONTEXT_KEYS",
        "_trusted_context_claim_path",
        '"adi_fixture"',
        '"adi_result"',
        '"test_only"',
        'declared_source_mode == "LLM_PUSH"',
        'candidate_only = request.pop("candidate_only", None)',
        '"BLOCK_UNAUTHORIZED_CLOUD_COMMIT"',
        'request["candidate_only"] = True',
    )
    for marker in required:
        if marker not in source:
            _fail("GATEWAY_CANDIDATE_ONLY_ENFORCEMENT_MISSING", GATEWAY_PATH)


def _verify_runtime() -> None:
    source = _source(RUNTIME_PATH)
    required = (
        "DECISION_SEVERITY",
        '"ALLOW": 0',
        '"HOLD": 1',
        '"BLOCK": 2',
        '"QUARANTINE": 3',
        "D7_NESTED_RAW_KEYS",
        '"raw_data"',
        '"base64_payload"',
        '"content_bytes"',
        '"previous": runtime.previous_state.to_dict()',
        '"committed": runtime.committed_state.to_dict()',
        "canonical_tfs_match",
        "LLM_PUSH_D6_BLOCKED_KEYS",
        "LLM_PUSH_SIDE_EFFECT_KEYS",
        'context.get("source_mode") == "LLM_PUSH"',
        '"LLM_PUSH_D6_SECURITY_BLOCKED"',
        '"LLM_PUSH_D7_REFERENCE_ONLY_REQUIRED"',
        '"LLM_PUSH_DIRECT_ALLOW_BLOCKED"',
        "commit_applied = fixed_point_status == \"REACHED\" and final_decision == \"ALLOW\"",
    )
    for marker in required:
        if marker not in source:
            _fail("RUNTIME_CLOUD_GUARD_MISSING", RUNTIME_PATH)


def _verify_test_shape() -> None:
    source = _source(TEST_PATH)
    tree = _tree(TEST_PATH)
    tests = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    ]
    if len(tests) != 10:
        _fail("FOCUSED_TEST_COUNT_INVALID", TEST_PATH)
    if "class FakeCloudProvider" not in source or "FakeAuthorizedSession" not in source:
        _fail("FAKE_CLOUD_PROVIDER_MISSING", TEST_PATH)
    if "patch.object" not in source or '"_authorized_session"' not in source:
        _fail("REAL_CLOUD_CALL_NOT_DISABLED", TEST_PATH)


def _run_focused_tests() -> None:
    try:
        completed = subprocess.run(
            [sys.executable, "-u", str(TEST_PATH)],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired:
        _fail("FOCUSED_TEST_TIMEOUT", TEST_PATH)
    if completed.returncode != 0:
        _fail("FOCUSED_TEST_FAILED", TEST_PATH)
    if "Ran 10 tests" not in completed.stdout or "\nOK\n" not in completed.stdout:
        _fail("FOCUSED_TEST_OUTPUT_INVALID", TEST_PATH)
    if "skipped=" in completed.stdout:
        _fail("FOCUSED_TEST_SKIPPED", TEST_PATH)


def _verify_protected_paths() -> None:
    active = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", "runtime/total_field/active"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if active.returncode != 0:
        _fail("ACTIVE_CANONICAL_CHANGED", "runtime/total_field/active")
    pointers = subprocess.run(
        ["git", "ls-files", "*POINTER*.json", "*pointer*.json"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if pointers.returncode != 0:
        _fail("POINTER_INVENTORY_FAILED", ROOT)
    paths = [line for line in pointers.stdout.splitlines() if line]
    if paths:
        changed = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", *paths],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if changed.returncode != 0:
            _fail("POINTER_CHANGED", "POINTER_FILES")


def main() -> int:
    try:
        _verify_files()
        _verify_provider()
        _verify_xiaoj()
        _verify_gateway()
        _verify_runtime()
        _verify_test_shape()
        _run_focused_tests()
        _verify_protected_paths()
    except VerificationFailure as exc:
        print("STATE=HOLD_VERIFY_CLOUD_AGENT_INTEGRATION")
        print(f"REASON_CODE={exc.reason_code}")
        print(f"FILE={exc.path}")
        print(f"LINE={exc.line}")
        return 1
    print("STATE=PASS_CLOUD_AGENT_INTEGRATED")
    print(f"RUN_ID={RUN_ID}")
    print("TEST_COUNT=10")
    print("COMMON_GATEWAY=tools.total_field_candidate_gateway.receive_candidate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
