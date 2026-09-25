#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify the promoted sovereign AI multi-domain canonical chain."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.promote_sovereign_ai_multi_domain_cloud_completion_canonical import (  # noqa: E402
    ACTIVE_CANONICAL,
    ACTIVE_POINTER,
    CANONICAL_MANIFEST,
    DOMAINS,
    PROMOTION_EVIDENCE,
    ROLLBACK_MANIFEST,
    RUNTIME_CANONICAL,
    RUNTIME_EVIDENCE,
    RUNTIME_MANIFEST,
    SEMANTIC_LOCKS,
    SOURCE_MODES,
    SOURCE_POLICY,
    SOURCE_POLICY_SHA256,
    TRACKED_POLICY,
    PromotionFailure,
    canonical_json,
    canonical_sha256,
    load_strict_json,
    verify_active,
)


RUN_ID = "SOVEREIGN_AI_MULTI_DOMAIN_CLOUD_COMPLETION_CANONICAL_V0_1"
PROMOTION_TOOL = Path("tools/promote_sovereign_ai_multi_domain_cloud_completion_canonical.py")
FOCUSED_TEST = Path("tests/test_promote_sovereign_ai_multi_domain_cloud_completion_canonical.py")
REPORT = Path("docs/total_field/SOVEREIGN_AI_MULTI_DOMAIN_CLOUD_COMPLETION_CANONICAL_PROMOTION_REPORT.md")
DELIVERABLES = (
    TRACKED_POLICY,
    CANONICAL_MANIFEST,
    PROMOTION_EVIDENCE,
    ROLLBACK_MANIFEST,
    RUNTIME_CANONICAL,
    RUNTIME_MANIFEST,
    RUNTIME_EVIDENCE,
    ACTIVE_CANONICAL,
    ACTIVE_POINTER,
    PROMOTION_TOOL,
    FOCUSED_TEST,
    REPORT,
)


class VerificationFailure(ValueError):
    def __init__(self, reason_code: str, path: str) -> None:
        self.reason_code = reason_code
        self.path = path
        super().__init__(reason_code)


def _fail(reason_code: str, path: str | Path) -> None:
    raise VerificationFailure(reason_code, str(path))


def _object(relative: Path) -> dict[str, Any]:
    try:
        value = load_strict_json(ROOT / relative)
    except PromotionFailure as exc:
        _fail(exc.reason_code, relative)
    if not isinstance(value, dict):
        _fail("JSON_ROOT_NOT_OBJECT", relative)
    return value


def _verify_presence() -> None:
    for relative in DELIVERABLES:
        if not (ROOT / relative).is_file():
            _fail("CANONICAL_DELIVERABLE_MISSING", relative)
        try:
            (ROOT / relative).read_text(encoding="utf-8")
        except UnicodeError:
            _fail("CANONICAL_DELIVERABLE_NOT_UTF8", relative)


def _verify_equivalence() -> None:
    source = _object(SOURCE_POLICY)
    tracked = _object(TRACKED_POLICY)
    runtime = _object(RUNTIME_CANONICAL)
    active = _object(ACTIVE_CANONICAL)
    if canonical_sha256(source) != SOURCE_POLICY_SHA256:
        _fail("SOURCE_POLICY_MISMATCH", SOURCE_POLICY)
    expected = canonical_json(source)
    if canonical_json(tracked) != expected:
        _fail("TRACKED_CANONICAL_POLICY_MISMATCH", TRACKED_POLICY)
    if canonical_json(runtime.get("policy")) != expected:
        _fail("RUNTIME_CANONICAL_POLICY_MISMATCH", RUNTIME_CANONICAL)
    if canonical_json(active.get("policy")) != expected:
        _fail("ACTIVE_CANONICAL_POLICY_MISMATCH", ACTIVE_CANONICAL)
    if (ROOT / ACTIVE_CANONICAL).read_bytes() != (ROOT / RUNTIME_CANONICAL).read_bytes():
        _fail("ACTIVE_RUNTIME_CANONICAL_MISMATCH", ACTIVE_CANONICAL)


def _verify_governance() -> None:
    runtime = _object(RUNTIME_CANONICAL)
    if runtime.get("status") != "ACTIVE_CANONICAL" or runtime.get("run_id") != RUN_ID:
        _fail("RUNTIME_CANONICAL_IDENTITY_INVALID", RUNTIME_CANONICAL)
    if runtime.get("domains") != {domain: "ACTIVE_CANONICAL" for domain in DOMAINS}:
        _fail("CANONICAL_DOMAIN_STATUS_INVALID", RUNTIME_CANONICAL)
    if runtime.get("cloud_completion") != "SUPPORTED_AS_CANDIDATE_ONLY":
        _fail("CANDIDATE_ONLY_BOUNDARY_INVALID", RUNTIME_CANONICAL)
    if runtime.get("semantic_locks") != SEMANTIC_LOCKS:
        _fail("CANONICAL_SEMANTIC_LOCK_INVALID", RUNTIME_CANONICAL)
    if runtime.get("source_modes") != {
        mode: "TOTAL_FIELD_GATEWAY_REQUIRED" for mode in SOURCE_MODES
    }:
        _fail("COMMON_GATEWAY_LOCK_INVALID", RUNTIME_CANONICAL)
    side_effects = runtime.get("side_effects")
    if not isinstance(side_effects, dict) or any(side_effects.values()):
        _fail("CANONICAL_SIDE_EFFECT_BOUNDARY_INVALID", RUNTIME_CANONICAL)
    policy = _object(TRACKED_POLICY)
    rules = policy.get("gate_rules")
    restricted = policy.get("restricted_attributes")
    required_rules = {
        "EVIDENCE_REQUIRED",
        "FINANCIAL_REVIEW_REQUIRED",
        "LEGAL_REVIEW_REQUIRED",
        "OWNER_CONFIRMATION_REQUIRED",
        "PRIVACY_RESTRICTED",
    }
    if not isinstance(rules, dict) or not required_rules.issubset(rules):
        _fail("CANONICAL_REVIEW_CLASSIFICATION_INVALID", TRACKED_POLICY)
    if not isinstance(restricted, dict) or not required_rules.issubset(restricted):
        _fail("CANONICAL_RESTRICTED_ATTRIBUTES_INVALID", TRACKED_POLICY)


def _verify_manifests() -> None:
    manifest = _object(CANONICAL_MANIFEST)
    evidence = _object(PROMOTION_EVIDENCE)
    rollback = _object(ROLLBACK_MANIFEST)
    runtime_manifest = _object(RUNTIME_MANIFEST)
    runtime_evidence = _object(RUNTIME_EVIDENCE)
    if manifest.get("owner_confirmation") != "YES":
        _fail("OWNER_CONFIRMATION_MISSING", CANONICAL_MANIFEST)
    if manifest.get("source_policy_sha256") != SOURCE_POLICY_SHA256:
        _fail("CANONICAL_MANIFEST_HASH_INVALID", CANONICAL_MANIFEST)
    if evidence != runtime_evidence or evidence.get("state") != "PASS":
        _fail("PROMOTION_EVIDENCE_INVALID", PROMOTION_EVIDENCE)
    runtime = _object(RUNTIME_CANONICAL)
    if runtime_manifest.get("runtime_canonical_sha256") != canonical_sha256(runtime):
        _fail("RUNTIME_MANIFEST_HASH_INVALID", RUNTIME_MANIFEST)
    if rollback.get("status") != "PLAN_ONLY" or rollback.get("automatic_rollback") is not False:
        _fail("ROLLBACK_MANIFEST_INVALID", ROLLBACK_MANIFEST)


def _verify_pointer() -> None:
    expected = str((ROOT / RUNTIME_CANONICAL).resolve())
    actual = (ROOT / ACTIVE_POINTER).read_text(encoding="utf-8").strip()
    if actual != expected:
        _fail("ACTIVE_POINTER_TARGET_INVALID", ACTIVE_POINTER)


def _verify_tool_boundaries() -> None:
    try:
        tree = ast.parse((ROOT / PROMOTION_TOOL).read_text(encoding="utf-8"))
    except SyntaxError:
        _fail("PROMOTION_TOOL_SYNTAX_INVALID", PROMOTION_TOOL)
    forbidden_imports = {
        "aiohttp", "boto3", "httpx", "odoo", "openai", "psycopg",
        "psycopg2", "requests", "socket", "sqlite3", "sqlalchemy", "subprocess",
    }
    forbidden_calls = {
        "connect", "deploy", "restart", "reboot", "system", "popen",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if {alias.name.split(".")[0] for alias in node.names} & forbidden_imports:
                _fail("FORBIDDEN_IMPORT", PROMOTION_TOOL)
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in forbidden_imports:
                _fail("FORBIDDEN_IMPORT", PROMOTION_TOOL)
        elif isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
            if name.casefold() in forbidden_calls:
                _fail("FORBIDDEN_OPERATION_CALL", PROMOTION_TOOL)


def _verify_no_sensitive_payload() -> None:
    for relative in (
        CANONICAL_MANIFEST,
        PROMOTION_EVIDENCE,
        ROLLBACK_MANIFEST,
        RUNTIME_CANONICAL,
        RUNTIME_MANIFEST,
        RUNTIME_EVIDENCE,
        ACTIVE_CANONICAL,
    ):
        value = _object(relative)
        serialized = json.dumps(value, ensure_ascii=False).casefold()
        forbidden_fragments = ("sk-proj-", "-----begin private key-----", "member-plaintext-fixture")
        if any(fragment in serialized for fragment in forbidden_fragments):
            _fail("SENSITIVE_PAYLOAD_DETECTED", relative)


def _verify_other_active_and_pointers() -> None:
    listed = subprocess.run(
        ["git", "ls-files", "runtime/total_field/active", "*POINTER*", "*pointer*"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if listed.returncode != 0:
        _fail("PROTECTED_PATH_INVENTORY_FAILED", ROOT)
    excluded = {str(ACTIVE_CANONICAL), str(ACTIVE_POINTER)}
    protected = sorted({line for line in listed.stdout.splitlines() if line and line not in excluded})
    if not protected:
        return
    diffed = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", *protected],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if diffed.returncode != 0:
        _fail("OTHER_ACTIVE_OR_POINTER_CHANGED", "PROTECTED_ACTIVE_AND_POINTERS")


def _run_focused_tests() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / FOCUSED_TEST)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0 or "Ran 28 tests" not in completed.stdout or "\nOK\n" not in completed.stdout:
        _fail("FOCUSED_TESTS_FAILED", FOCUSED_TEST)


def _verify_report() -> None:
    text = (ROOT / REPORT).read_text(encoding="utf-8")
    markers = (
        "OWNER_CONFIRMATION=YES",
        "CLOUD_COMPLETION=SUPPORTED_AS_CANDIDATE_ONLY",
        "COMMUNITY_DOMAIN=ACTIVE_CANONICAL",
        "COMMERCE_DOMAIN=ACTIVE_CANONICAL",
        "PROPERTY_DOMAIN=ACTIVE_CANONICAL",
        "D4_EVIDENCE_GATE=REQUIRED",
        "D6_PRIVACY_GATE=REQUIRED",
        "D8_ADJUDICATION=REQUIRED",
        "ALLOW_ONLY_COMMIT=REQUIRED",
        "PATENT_CANDIDATE_REVIEW_REQUIRED=YES",
        "DB_WRITE=NO",
        "DEPLOY=NO",
        "RESTART=NO",
        "ROUTER_WRITE=NO",
        "Open Problems",
    )
    if any(marker not in text for marker in markers):
        _fail("PROMOTION_REPORT_INCOMPLETE", REPORT)


def main() -> int:
    try:
        _verify_presence()
        verify_active(ROOT)
        _verify_equivalence()
        _verify_governance()
        _verify_manifests()
        _verify_pointer()
        _verify_tool_boundaries()
        _verify_no_sensitive_payload()
        _verify_other_active_and_pointers()
        _verify_report()
        _run_focused_tests()
    except (VerificationFailure, PromotionFailure) as exc:
        reason = getattr(exc, "reason_code", "CANONICAL_VERIFICATION_FAILED")
        path = getattr(exc, "path", "")
        print("STATE=HOLD_VERIFY_SOVEREIGN_AI_MULTI_DOMAIN_CLOUD_COMPLETION_CANONICAL")
        print(f"REASON_CODE={reason}")
        print(f"FILE={path}")
        return 1
    print("STATE=PASS_VERIFY_SOVEREIGN_AI_MULTI_DOMAIN_CLOUD_COMPLETION_CANONICAL")
    print(f"RUN_ID={RUN_ID}")
    print("TEST_COUNT=28")
    print(f"SOURCE_POLICY_SHA256={SOURCE_POLICY_SHA256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
