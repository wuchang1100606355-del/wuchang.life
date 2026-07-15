#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused verifier for the trackable TFCT TRUE8D runtime candidate package."""

from __future__ import annotations

import ast
import hashlib
import json
import math
import py_compile
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "TFCT_TRUE8D_RUNTIME_CANDIDATE_POLICY_PACKAGE_V0_1"
PACKAGE_DIR = "manifests/tfct_true8d_runtime_candidate_v0_1"
TRACKED_POLICY = f"{PACKAGE_DIR}/policy.json"
PACKAGE_MANIFEST = f"{PACKAGE_DIR}/package_manifest.json"
RUNTIME_POLICY = "runtime/total_field/candidate/tfct_true8d_runtime_policy_v0_1.json"
PACKAGER = "tools/package_tfct_true8d_runtime_candidate.py"
FOCUSED_TEST = "tests/test_package_tfct_true8d_runtime_candidate.py"
VERIFIER = "scripts/verify/verify_tfct_true8d_runtime_candidate_package.py"
REPORT = "docs/total_field/TFCT_TRUE8D_RUNTIME_CANDIDATE_PACKAGE_REPORT.md"

DELIVERABLES = (
    TRACKED_POLICY,
    PACKAGE_MANIFEST,
    PACKAGER,
    FOCUSED_TEST,
    VERIFIER,
    REPORT,
)
PYTHON_FILES = (PACKAGER, FOCUSED_TEST, VERIFIER)
JSON_FILES = (TRACKED_POLICY, PACKAGE_MANIFEST)

HEAD_PROTECTED = (
    ".gitignore",
    "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_CANONICAL.json",
    "runtime/total_field/active/ACTIVE_CODEX_TOTAL_FIELD_GLOBAL_AGENT_DOMAIN_POINTER.txt",
    "runtime/total_field/active/ACTIVE_DOMAIN_BETA_DEPLOYMENT_POINTER.txt",
    "runtime/total_field/active/ACTIVE_POS_OFFICIAL_CHAIN_POINTER.txt",
    "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_POINTER.txt",
    "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_POINTER.txt",
    "runtime/total_field/active/ACTIVE_TRUE8D_ROUTER_ALLNODE_MERGE_POINTER.txt",
    "runtime/total_field/active/ACTIVE_TRUE8D_ROUTER_BOUNDARY_POINTER.txt",
    "runtime/total_field/active/ACTIVE_V4_TRUE8D_TIPO_LANDING_POINTER.txt",
)

BASELINE_SHA256 = {
    RUNTIME_POLICY: "7aa603dda45b42cf27582ed8fa3956e2eda24b8fd9734238b6a17efc02ec7adf",
    "tools/tfct_true8d_runtime_candidate.py": "c573b767c8a83e8d27da2f9ecca03aa86b9f4fda891e6bcd62725b08ebc80cab",
    "tools/eightd_gte_parser_candidate.py": "afe1010549cc0314e9023f5a4fc89c9ddadf6fe5c86687484e9db3cf9c3ec381",
    "tools/total_field_candidate_gateway.py": "545c4f843f3e81340181b8fb904186418a5e32d2ca87b875f30e6cdf4259a792",
    "tools/w7tp_small_transport_agent_candidate.py": "f94e80f0e6e08512df000a270b26c026c9c26b7b07fae3d5d8cdc7ce3e8637d9",
    "tools/xiaoj_candidate_adapter.py": "107dfbdeb5e137b9a28288c44f47cd20bed7abfd9e4101ab17ba7e7bae4246c9",
    "tools/adi_index_strategy_candidate.py": "d772fb6023dea9cbb4fcf8f1c5e809f9100912d39fb4f1351f6d49d641382f26",
    "tests/test_tfct_true8d_runtime_candidate.py": "f62f7b6cc3efdf05a3b5486c5d53aa1f66aa964590fcab794a491ee419a59910",
    "scripts/verify/verify_tfct_true8d_runtime_candidate.py": "054ee14f3532f210fc8f37d9c98e0affd3c057301aa0e963f19d48aad7b33838",
    "tools/d3_coordinate_transition_candidate.py": "b1e67f1d22d0e53785f3939885dcb690907cb68071f7f3a682ce368a356bb918",
    "tools/w7tp_packet_inference_runtime.py": "7918b485b83d1523c98636366c3bd41aaf3b514b0a1b35b4b1ffad066bc1205b",
}

EXPECTED_MANIFEST = {
    "schema_version": "tfct_true8d_runtime_candidate_package_v0.1",
    "package_version": "v0.1",
    "status": "CANDIDATE",
    "source_policy": "policy.json",
    "runtime_target": RUNTIME_POLICY,
    "materialization_mode": "EXPLICIT_ONLY",
    "canonical_promotion": False,
    "deploy": False,
    "restart": False,
}


@dataclass(frozen=True)
class VerificationFailure(Exception):
    """Stable package-verification failure without payload disclosure."""

    reason_code: str
    file: str
    line: int = 1

    def __str__(self) -> str:
        """Render only the stable reason code."""

        return self.reason_code


def _fail(reason_code: str, file: str, line: int = 1) -> None:
    """Raise one structured verifier failure."""

    raise VerificationFailure(reason_code, file, line)


def _read(path: str) -> str:
    """Read one approved path as UTF-8 text."""

    try:
        return (ROOT / path).read_text(encoding="utf-8")
    except FileNotFoundError:
        _fail("DELIVERABLE_MISSING", path)
    except UnicodeError:
        _fail("DELIVERABLE_NOT_UTF8", path)
    raise AssertionError("unreachable")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build an object while rejecting duplicate JSON names."""

    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _reject_nonfinite_constant(value: str) -> Any:
    """Reject JSON extensions for non-finite numeric constants."""

    raise ValueError(f"NONFINITE_JSON_CONSTANT:{value}")


def _ensure_finite(value: Any) -> None:
    """Reject finite-overflow floats produced by otherwise valid JSON syntax."""

    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("NONFINITE_JSON_NUMBER")
    if isinstance(value, dict):
        for nested in value.values():
            _ensure_finite(nested)
    elif isinstance(value, list):
        for nested in value:
            _ensure_finite(nested)


def _load_json(path: str) -> Any:
    """Load one strict UTF-8 JSON document."""

    try:
        value = json.loads(
            _read(path),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_nonfinite_constant,
        )
        _ensure_finite(value)
        return value
    except (json.JSONDecodeError, ValueError):
        _fail("STRICT_JSON_INVALID", path)
    raise AssertionError("unreachable")


def _canonical_bytes(value: Any) -> bytes:
    """Serialize a JSON value using the locked canonical contract."""

    try:
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        _fail("CANONICAL_JSON_SERIALIZATION_FAILED", TRACKED_POLICY)
    raise AssertionError("unreachable")


def _sha256_bytes(path: str) -> str:
    """Hash the exact bytes of one protected path."""

    try:
        return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    except FileNotFoundError:
        _fail("PROTECTED_FILE_MISSING", path)
    raise AssertionError("unreachable")


def _check_presence_and_json() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Require all deliverables and validate both package JSON documents."""

    for path in DELIVERABLES:
        if not (ROOT / path).is_file():
            _fail("DELIVERABLE_MISSING", path)
        _read(path)
    tracked_policy = _load_json(TRACKED_POLICY)
    manifest = _load_json(PACKAGE_MANIFEST)
    runtime_policy = _load_json(RUNTIME_POLICY)
    for path, policy in ((TRACKED_POLICY, tracked_policy), (RUNTIME_POLICY, runtime_policy)):
        if not isinstance(policy, dict):
            _fail("POLICY_ROOT_NOT_OBJECT", path)
        if policy.get("status") != "CANDIDATE":
            _fail("POLICY_NOT_CANDIDATE", path)
    if not isinstance(manifest, dict):
        _fail("PACKAGE_MANIFEST_ROOT_NOT_OBJECT", PACKAGE_MANIFEST)
    expected_keys = set(EXPECTED_MANIFEST) | {"policy_sha256"}
    if set(manifest) != expected_keys:
        _fail("PACKAGE_MANIFEST_KEYS_INVALID", PACKAGE_MANIFEST)
    for key, expected in EXPECTED_MANIFEST.items():
        actual = manifest.get(key)
        if type(actual) is not type(expected) or actual != expected:
            _fail("PACKAGE_MANIFEST_VALUE_INVALID", PACKAGE_MANIFEST)
    policy_hash = hashlib.sha256(_canonical_bytes(tracked_policy)).hexdigest()
    if manifest.get("policy_sha256") != policy_hash:
        _fail("PACKAGE_MANIFEST_HASH_MISMATCH", PACKAGE_MANIFEST)
    if _canonical_bytes(tracked_policy) != _canonical_bytes(runtime_policy):
        _fail("TRACKED_RUNTIME_POLICY_MISMATCH", TRACKED_POLICY)
    return tracked_policy, runtime_policy, manifest


def _check_compile() -> None:
    """Compile exactly the three new Python files outside the repository."""

    with tempfile.TemporaryDirectory(prefix="tfct-package-compile-") as directory:
        output = Path(directory)
        for index, path in enumerate(PYTHON_FILES):
            try:
                py_compile.compile(
                    str(ROOT / path),
                    cfile=str(output / f"module-{index}.pyc"),
                    doraise=True,
                )
            except py_compile.PyCompileError as error:
                line = int(getattr(error.exc_value, "lineno", 1) or 1)
                _fail("PYTHON_COMPILE_FAILED", path, line)


def _call_name(node: ast.expr) -> str:
    """Render a direct call target as a stable dotted name."""

    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _call_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _check_python_ast() -> None:
    """Reject unfinished stubs, dynamic execution, entropy, and network APIs."""

    forbidden_import_roots = {
        "anthropic",
        "datetime",
        "httpx",
        "importlib",
        "openai",
        "pickle",
        "random",
        "requests",
        "secrets",
        "socket",
        "time",
        "urllib",
        "uuid",
    }
    forbidden_calls = {
        "__import__",
        "com" + "pile",
        "ev" + "al",
        "ex" + "ec",
        "os.getrandom",
        "os.popen",
        "os.system",
        "os.urandom",
        "pickle.load",
        "pickle.loads",
        "random.random",
        "secrets.token_bytes",
        "secrets.token_hex",
        "secrets.token_urlsafe",
        "time.time",
        "uuid.uuid1",
        "uuid.uuid4",
    }
    subprocess_calls = {
        "subprocess.call",
        "subprocess.check_call",
        "subprocess.check_output",
        "subprocess.run",
        "subprocess.Popen",
    }
    network_commands = {"curl", "ftp", "nc", "scp", "sftp", "ssh", "wget"}
    for path in PYTHON_FILES:
        source = _read(path)
        for marker in ("TO" + "DO", "FIX" + "ME", "Not" + "ImplementedError"):
            if marker in source:
                line = source[: source.index(marker)].count("\n") + 1
                _fail("UNFINISHED_SOURCE_MARKER", path, line)
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError as error:
            _fail("PYTHON_AST_PARSE_FAILED", path, int(error.lineno or 1))
        for node in ast.walk(tree):
            if isinstance(node, ast.Pass):
                _fail("EMPTY_STATEMENT_STUB", path, node.lineno)
            if (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant)
                and node.value.value is Ellipsis
            ):
                _fail("ELLIPSIS_STUB", path, node.lineno)
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = (
                    [alias.name for alias in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or ""]
                )
                if any(name.split(".", 1)[0] in forbidden_import_roots for name in names):
                    _fail("FORBIDDEN_IMPORT", path, node.lineno)
            if isinstance(node, ast.Call):
                name = _call_name(node.func)
                if name in forbidden_calls:
                    _fail("FORBIDDEN_EXECUTION_OR_ENTROPY_API", path, node.lineno)
                if name in subprocess_calls:
                    for keyword in node.keywords:
                        if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value:
                            _fail("FORBIDDEN_SHELL_SUBPROCESS", path, node.lineno)
                    if node.args:
                        command = node.args[0]
                        if isinstance(command, (ast.List, ast.Tuple)) and command.elts:
                            executable = command.elts[0]
                            if isinstance(executable, ast.Constant) and executable.value in network_commands:
                                _fail("FORBIDDEN_NETWORK_SUBPROCESS", path, node.lineno)


def _check_report_and_sensitive_content() -> None:
    """Require package-boundary evidence and reject credential-shaped literals."""

    report = _read(REPORT)
    required_report_markers = (
        "TRACKED_POLICY_RESPONSIBILITY=REBUILD_SOURCE",
        "RUNTIME_POLICY_RESPONSIBILITY=RUNTIME_CONSUMER_TARGET",
        "CANONICAL_EQUIVALENCE",
        "POLICY_SHA256",
        "MATERIALIZATION_MODE=EXPLICIT_ONLY",
        "NO_OVERWRITE",
        "CANONICAL_PROMOTION=NO",
        "DEPLOY=NO",
        "RESTART=NO",
    )
    for marker in required_report_markers:
        if marker not in report:
            _fail("REPORT_CONTRACT_INCOMPLETE", REPORT)
    secret_patterns = (
        re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        re.compile(
            r"(?i)(?:api[_-]?key|password|raw[_-]?token|client[_-]?secret)\s*[=:]\s*['\"]?[A-Za-z0-9._-]{16,}"
        ),
        re.compile(
            r"(?i)(?:member[_ -]?plaintext|raw[_ -]?member[_ -]?data)\s*[=:]\s*['\"]?[^\s'\"]{8,}"
        ),
    )
    for path in DELIVERABLES:
        source = _read(path)
        for pattern in secret_patterns:
            match = pattern.search(source)
            if match:
                line = source[: match.start()].count("\n") + 1
                _fail("SENSITIVE_LITERAL_DETECTED", path, line)


def _check_protected_files() -> None:
    """Require exact HEAD and byte-hash protection for the named legacy inputs."""

    for path in HEAD_PROTECTED:
        result = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", path],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 1:
            _fail("HEAD_PROTECTED_FILE_CHANGED", path)
        if result.returncode not in (0, 1):
            _fail("HEAD_PROTECTED_DIFF_FAILED", path)
    status = subprocess.run(
        [
            "git",
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            *HEAD_PROTECTED,
        ],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if status.returncode != 0:
        _fail("PROTECTED_STATUS_CHECK_FAILED", ".gitignore")
    if status.stdout.strip():
        changed = status.stdout.splitlines()[0][3:].strip()
        _fail("PROTECTED_WORKTREE_PATH_CHANGED", changed)
    for path, expected in BASELINE_SHA256.items():
        if _sha256_bytes(path) != expected:
            _fail("BASELINE_PROTECTED_FILE_CHANGED", path)


def _run_focused_test() -> None:
    """Run only the package test and require exactly fifteen successful cases."""

    result = subprocess.run(
        [sys.executable, str(ROOT / FOCUSED_TEST)],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        locations = re.findall(r'File "([^"]+)", line (\d+)', result.stdout)
        if locations:
            file_name, line_text = locations[-1]
            try:
                file_name = str(Path(file_name).resolve().relative_to(ROOT))
            except ValueError:
                file_name = FOCUSED_TEST
            _fail("FOCUSED_TEST_FAILED", file_name, int(line_text))
        _fail("FOCUSED_TEST_FAILED", FOCUSED_TEST)
    if "Ran 15 tests" not in result.stdout or not re.search(r"^OK\s*$", result.stdout, re.MULTILINE):
        _fail("FOCUSED_TEST_COUNT_MISMATCH", FOCUSED_TEST)
    if re.search(r"\bskipped\b|expected failures|unexpected successes", result.stdout):
        _fail("FOCUSED_TEST_NOT_STRICT", FOCUSED_TEST)


def verify() -> None:
    """Run the approved package-only checks in deterministic order."""

    _check_presence_and_json()
    _check_compile()
    _check_python_ast()
    _check_report_and_sensitive_content()
    _check_protected_files()
    _run_focused_test()


def main() -> int:
    """Print one stable state and suppress traceback detail."""

    try:
        verify()
    except VerificationFailure as failure:
        print("STATE=HOLD_VERIFY_TFCT_TRUE8D_RUNTIME_CANDIDATE_PACKAGE")
        print(f"REASON_CODE={failure.reason_code}")
        print(f"FILE={failure.file}")
        print(f"LINE={failure.line}")
        return 1
    except Exception:
        print("STATE=HOLD_VERIFY_TFCT_TRUE8D_RUNTIME_CANDIDATE_PACKAGE")
        print("REASON_CODE=UNEXPECTED_VERIFIER_FAILURE")
        print(f"FILE={VERIFIER}")
        print("LINE=1")
        return 1
    print("STATE=PASS_VERIFY_TFCT_TRUE8D_RUNTIME_CANDIDATE_PACKAGE")
    print(f"RUN_ID={RUN_ID}")
    print("TEST_COUNT=15")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
