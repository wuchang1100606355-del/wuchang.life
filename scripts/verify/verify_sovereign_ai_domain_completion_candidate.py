#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify the sovereign multi-domain cloud-completion candidate package."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "SOVEREIGN_AI_MULTI_DOMAIN_CLOUD_COMPLETION_CANDIDATE_V0_1"
TEST_PATH = ROOT / "tests/test_sovereign_ai_domain_completion_candidate.py"
SCHEMA_PATH = (
    ROOT / "schemas/field/sovereign_ai_domain_completion_candidate.schema.json"
)
POLICY_PATH = (
    ROOT
    / "runtime/total_field/candidate/sovereign_ai_domain_completion_policy_v0_1.json"
)
REPORT_PATH = (
    ROOT
    / "docs/total_field/SOVEREIGN_AI_MULTI_DOMAIN_CLOUD_COMPLETION_CANDIDATE_REPORT.md"
)
MODULE_PATHS = (
    ROOT / "tools/sovereign_ai_domain_completion_candidate.py",
    ROOT / "tools/domain_completion_total_field_gateway.py",
)
EXPECTED_FILES = MODULE_PATHS + (POLICY_PATH, SCHEMA_PATH, TEST_PATH, REPORT_PATH)

EXPECTED_SOURCE_MODES = [
    "TOTAL_FIELD_PULL",
    "LLM_PUSH",
    "XIAOJ_LOCAL",
    "RULE_LOOKUP",
    "HUMAN_INPUT",
]
EXPECTED_CLASSES = [
    "SAFE_DERIVED",
    "EVIDENCE_REQUIRED",
    "OWNER_CONFIRMATION_REQUIRED",
    "PRIVACY_RESTRICTED",
    "LEGAL_REVIEW_REQUIRED",
    "FINANCIAL_REVIEW_REQUIRED",
    "UNSUPPORTED",
]
EXPECTED_DOMAINS = {"COMMUNITY", "COMMERCE", "PROPERTY"}
FORBIDDEN_IMPORTS = {
    "aiohttp",
    "boto3",
    "httpx",
    "odoo",
    "openai",
    "psycopg",
    "psycopg2",
    "requests",
    "socket",
    "sqlite3",
    "sqlalchemy",
    "subprocess",
    "urllib",
}
FORBIDDEN_CALL_NAMES = {
    "eval",
    "exec",
    "system",
    "popen",
    "remove",
    "rename",
    "replace_file",
    "unlink",
}


class VerificationFailure(Exception):
    """Stable verifier failure with path and optional line."""

    def __init__(self, reason_code: str, path: Path | str, line: int = 0) -> None:
        self.reason_code = reason_code
        self.path = str(path)
        self.line = line
        super().__init__(reason_code)


def _fail(reason_code: str, path: Path | str, line: int = 0) -> None:
    raise VerificationFailure(reason_code, path, line)


def _reject_constant(token: str) -> None:
    raise ValueError(token)


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(key)
        result[key] = value
    return result


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_reject_constant,
            object_pairs_hook=_reject_duplicates,
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        _fail("JSON_READ_OR_PARSE_FAILED", path)
    if not isinstance(value, dict):
        _fail("JSON_ROOT_NOT_OBJECT", path)
    return value


def _verify_files() -> None:
    for path in EXPECTED_FILES:
        if not path.is_file():
            _fail("REQUIRED_FILE_MISSING", path)
        try:
            path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            _fail("UTF8_READ_FAILED", path)


def _verify_schema() -> None:
    schema = _load_json(SCHEMA_PATH)
    try:
        Draft202012Validator.check_schema(schema)
    except Exception:
        _fail("SCHEMA_DRAFT_2020_12_INVALID", SCHEMA_PATH)
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        _fail("SCHEMA_DRAFT_ID_INVALID", SCHEMA_PATH)
    if schema.get("additionalProperties") is not False:
        _fail("SCHEMA_ROOT_NOT_CLOSED", SCHEMA_PATH)
    required = schema.get("required")
    expected = {
        "schema_version",
        "domain",
        "entity_ref",
        "attribute_name",
        "candidate_value",
        "source_mode",
        "model_ref",
        "provider_ref",
        "event_ref",
        "observation_domain_ref",
        "rule_ref",
        "evidence_refs",
        "confidence",
        "sensitivity",
        "requires_human_confirmation",
        "candidate_hash",
    }
    if not isinstance(required, list) or set(required) != expected:
        _fail("SCHEMA_REQUIRED_FIELDS_INVALID", SCHEMA_PATH)
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        _fail("SCHEMA_PROPERTIES_INVALID", SCHEMA_PATH)
    if properties.get("source_mode", {}).get("enum") != EXPECTED_SOURCE_MODES:
        _fail("SCHEMA_SOURCE_MODES_INVALID", SCHEMA_PATH)
    if properties.get("sensitivity", {}).get("enum") != EXPECTED_CLASSES:
        _fail("SCHEMA_SENSITIVITY_CLASSES_INVALID", SCHEMA_PATH)


def _verify_policy() -> None:
    policy = _load_json(POLICY_PATH)
    if policy.get("run_id") != RUN_ID or policy.get("status") != "CANDIDATE":
        _fail("POLICY_IDENTITY_INVALID", POLICY_PATH)
    if policy.get("cloud_completion") != "SUPPORTED_AS_CANDIDATE_ONLY":
        _fail("POLICY_CANDIDATE_ONLY_INVALID", POLICY_PATH)
    domains = policy.get("domains")
    if not isinstance(domains, dict) or set(domains) != EXPECTED_DOMAINS:
        _fail("POLICY_DOMAINS_INVALID", POLICY_PATH)
    if not all(isinstance(domains[name], list) and domains[name] for name in domains):
        _fail("POLICY_DOMAIN_INVENTORY_EMPTY", POLICY_PATH)
    if policy.get("allowed_source_modes") != EXPECTED_SOURCE_MODES:
        _fail("POLICY_SOURCE_MODES_INVALID", POLICY_PATH)
    if policy.get("sensitivity_classes") != EXPECTED_CLASSES:
        _fail("POLICY_SENSITIVITY_CLASSES_INVALID", POLICY_PATH)
    if policy.get("decision_priority") != ["QUARANTINE", "BLOCK", "HOLD", "ALLOW"]:
        _fail("POLICY_DECISION_PRIORITY_INVALID", POLICY_PATH)
    side_effects = policy.get("side_effects")
    expected_side_effects = {
        "db_write",
        "deploy",
        "restart",
        "router_write",
        "canonical_write",
        "pointer_write",
    }
    if (
        not isinstance(side_effects, dict)
        or set(side_effects) != expected_side_effects
        or any(side_effects.values())
    ):
        _fail("POLICY_SIDE_EFFECT_BOUNDARY_INVALID", POLICY_PATH)
    rules = policy.get("gate_rules")
    if not isinstance(rules, dict) or set(rules) != set(EXPECTED_CLASSES):
        _fail("POLICY_GATE_RULES_INVALID", POLICY_PATH)


def _verify_python_boundaries() -> None:
    gateway_source = MODULE_PATHS[1].read_text(encoding="utf-8")
    if "receive_candidate as total_field_receive_candidate" not in gateway_source:
        _fail("EXISTING_TOTAL_FIELD_GATEWAY_NOT_USED", MODULE_PATHS[1])
    if "run_convergence" in gateway_source or "evaluate_candidate" in gateway_source:
        _fail("SECOND_RUNTIME_ENGINE_FORBIDDEN", MODULE_PATHS[1])
    for path in MODULE_PATHS:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            _fail("PYTHON_SYNTAX_INVALID", path, exc.lineno or 0)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots = {alias.name.split(".")[0] for alias in node.names}
                if roots & FORBIDDEN_IMPORTS:
                    _fail("FORBIDDEN_IMPORT", path, node.lineno)
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] in FORBIDDEN_IMPORTS:
                    _fail("FORBIDDEN_IMPORT", path, node.lineno)
            elif isinstance(node, ast.Call):
                name = ""
                if isinstance(node.func, ast.Name):
                    name = node.func.id.casefold()
                elif isinstance(node.func, ast.Attribute):
                    name = node.func.attr.casefold()
                if name in FORBIDDEN_CALL_NAMES:
                    _fail("FORBIDDEN_EXECUTION_API", path, node.lineno)


def _verify_report() -> None:
    text = REPORT_PATH.read_text(encoding="utf-8")
    required = (
        "CLOUD_COMPLETION=SUPPORTED_AS_CANDIDATE_ONLY",
        "COMMUNITY",
        "COMMERCE",
        "PROPERTY",
        "Total Field Gateway",
        "ALLOW-only",
        "Fake/InMemory",
        "persona",
        "DB_WRITE=NO",
        "DEPLOY=NO",
        "RESTART=NO",
        "ROUTER_WRITE=NO",
        "ACTIVE_CANONICAL_WRITE=NO",
        "POINTER_WRITE=NO",
    )
    for marker in required:
        if marker not in text:
            _fail("REPORT_MARKER_MISSING", REPORT_PATH)
    if "CLOUD_COMPLETION=FULL_AUTHORITY" in text:
        _fail("REPORT_FULL_AUTHORITY_FORBIDDEN", REPORT_PATH)


def _verify_test_shape() -> None:
    try:
        tree = ast.parse(TEST_PATH.read_text(encoding="utf-8"), filename=str(TEST_PATH))
    except SyntaxError as exc:
        _fail("TEST_SYNTAX_INVALID", TEST_PATH, exc.lineno or 0)
    methods = sorted(
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    if len(methods) != 30:
        _fail("FOCUSED_TEST_COUNT_INVALID", TEST_PATH)
    expected_prefixes = {f"test_{index:02d}_" for index in range(1, 31)}
    actual_prefixes = {name[:8] for name in methods}
    if actual_prefixes != expected_prefixes:
        _fail("FOCUSED_TEST_NUMBERING_INVALID", TEST_PATH)


def _run_focused_test() -> None:
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
    output = completed.stdout
    if completed.returncode != 0:
        _fail("FOCUSED_TEST_FAILED", TEST_PATH)
    if "Ran 30 tests" not in output or "\nOK\n" not in output:
        _fail("FOCUSED_TEST_OUTPUT_INVALID", TEST_PATH)
    forbidden = ("skipped=", "expected failures=", "unexpected successes=")
    if any(marker in output for marker in forbidden):
        _fail("FOCUSED_TEST_NOT_STRICT_PASS", TEST_PATH)


def _verify_protected_paths() -> None:
    completed = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", "runtime/total_field/active"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode not in {0}:
        _fail("ACTIVE_CANONICAL_CHANGED", "runtime/total_field/active")
    listed = subprocess.run(
        ["git", "ls-files", "*POINTER*.json", "*pointer*.json"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if listed.returncode != 0:
        _fail("POINTER_INVENTORY_FAILED", ROOT)
    pointer_paths = [line for line in listed.stdout.splitlines() if line]
    if pointer_paths:
        diffed = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", *pointer_paths],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if diffed.returncode != 0:
            _fail("POINTER_CHANGED", "POINTER_FILES")


def main() -> int:
    try:
        _verify_files()
        _verify_schema()
        _verify_policy()
        _verify_python_boundaries()
        _verify_report()
        _verify_test_shape()
        _run_focused_test()
        _verify_protected_paths()
    except VerificationFailure as exc:
        print("STATE=HOLD_VERIFY_SOVEREIGN_AI_DOMAIN_COMPLETION_CANDIDATE")
        print(f"REASON_CODE={exc.reason_code}")
        print(f"FILE={exc.path}")
        print(f"LINE={exc.line}")
        return 1
    print("STATE=PASS_VERIFY_SOVEREIGN_AI_DOMAIN_COMPLETION_CANDIDATE")
    print(f"RUN_ID={RUN_ID}")
    print("TEST_COUNT=30")
    print("CLOUD_COMPLETION=SUPPORTED_AS_CANDIDATE_ONLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
