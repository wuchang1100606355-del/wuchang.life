#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify the deterministic W7TP small-agent all-node deployment package.

The verifier is deliberately a predeployment gate.  It validates the exact
release, focused tests, local fixed vector, formal-node authority resolution,
and protected-file baselines without contacting a formal node or changing a
service, Active Canonical, Pointer, database, router, or runtime policy.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import os
from pathlib import Path
import py_compile
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Any, NoReturn

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

RUN_ID = "W7TP_SMALL_AGENT_ALL_NODE_DEPLOYMENT_V0_1_D27230ABA7A4"
RELEASE_VERSION = "v0.1-d27230aba7a4"
POLICY_SHA256 = "d27230aba7a4ecd051f4169184c1fa5357ce5efa1d62019238d68991b0140960"
RELEASE_DIR = Path("manifests/w7tp_small_agent_release_v0_1_d27230aba7a4")
CURRENT_RELEASE_DIR = Path(
    "manifests/w7tp_small_agent_release_v0_1_3_d27230aba7a4"
)
FIXTURE_PATH = Path("tests/fixtures/w7tp_small_agent_deployment_vectors.json")
TEST_PATH = Path("tests/test_w7tp_small_agent_deployment.py")
BUILDER_PATH = Path("tools/build_w7tp_small_agent_release.py")
DEPLOYER_PATH = Path("tools/deploy_w7tp_small_agent_all_nodes.py")
RUNNER_PATH = Path("tools/w7tp_small_agent_service_runner.py")
HEALTHCHECK_PATH = Path("tools/w7tp_small_agent_healthcheck.py")

PYTHON_FILES = (
    BUILDER_PATH,
    DEPLOYER_PATH,
    RUNNER_PATH,
    HEALTHCHECK_PATH,
    TEST_PATH,
)

RELEASE_PAYLOAD = frozenset(
    {
        "tools/w7tp_small_transport_agent_candidate.py",
        "tools/tfct_true8d_runtime_candidate.py",
        "tools/eightd_gte_parser_candidate.py",
        "tools/total_field_candidate_gateway.py",
        "tools/xiaoj_candidate_adapter.py",
        "tools/d3_coordinate_transition_candidate.py",
        "tools/adi_index_strategy_candidate.py",
        "tools/w7tp_small_agent_service_runner.py",
        "tools/w7tp_small_agent_healthcheck.py",
        "tests/fixtures/w7tp_small_agent_deployment_vectors.json",
        "runtime_policy_reference.json",
        "capability_manifest.schema.json",
        "UNINSTALL_ROLLBACK.md",
    }
)
ROOT_MANIFESTS = frozenset(
    {
        "release_manifest.json",
        "files_sha256.json",
        "capability_manifest_template.json",
        "install_manifest.json",
        "rollback_manifest.json",
    }
)
EXPECTED_RELEASE_INVENTORY = RELEASE_PAYLOAD | ROOT_MANIFESTS

PROTECTED_SHA256 = {
    "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_CANONICAL.json": "5ec55fec22504aa719803f398c8b408a785c145870bf4cd34434cad242ab9237",
    "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_POINTER.txt": "0ee90811b6f9f4ebbf798369fa32eeb3950b1c03117490f9d7c4cdc3a5d1c4fa",
    "runtime/total_field/active/ACTIVE_TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL.json": "a3cf7ead429291afcc2fb7810877a04a9c57f7a10ccd102e5b46fedfeef01176",
    "runtime/total_field/active/ACTIVE_TFCT_TRUE8D_RUNTIME_POLICY_POINTER.txt": "5e7367cde1b051cfb8ed71614114db1ee8b8c2ff60f08dacb3c2adbd43a037ad",
    "runtime/total_field/TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL_V0_1_D27230ABA7A4/TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL.json": "a3cf7ead429291afcc2fb7810877a04a9c57f7a10ccd102e5b46fedfeef01176",
    "tools/tfct_true8d_runtime_candidate.py": "c573b767c8a83e8d27da2f9ecca03aa86b9f4fda891e6bcd62725b08ebc80cab",
    "tools/eightd_gte_parser_candidate.py": "afe1010549cc0314e9023f5a4fc89c9ddadf6fe5c86687484e9db3cf9c3ec381",
    "tools/total_field_candidate_gateway.py": "545c4f843f3e81340181b8fb904186418a5e32d2ca87b875f30e6cdf4259a792",
    "tools/w7tp_small_transport_agent_candidate.py": "f94e80f0e6e08512df000a270b26c026c9c26b7b07fae3d5d8cdc7ce3e8637d9",
    "tools/xiaoj_candidate_adapter.py": "107dfbdeb5e137b9a28288c44f47cd20bed7abfd9e4101ab17ba7e7bae4246c9",
    "tools/adi_index_strategy_candidate.py": "d772fb6023dea9cbb4fcf8f1c5e809f9100912d39fb4f1351f6d49d641382f26",
    "tools/d3_coordinate_transition_candidate.py": "b1e67f1d22d0e53785f3939885dcb690907cb68071f7f3a682ce368a356bb918",
    "tools/w7tp_packet_inference_runtime.py": "7918b485b83d1523c98636366c3bd41aaf3b514b0a1b35b4b1ffad066bc1205b",
}

FIXTURE_KEYS = frozenset(
    {
        "schema_version",
        "run_id",
        "release_version",
        "policy_sha256",
        "capability_manifest",
        "candidate",
        "d1_intent",
        "persona_text",
        "gateway_request",
        "previous_state",
        "proposed_state",
        "observation_domains",
        "gateway_results",
        "expected",
    }
)
CAPABILITY_KEYS = frozenset(
    {
        "agent_ref",
        "version",
        "protocol_version",
        "supported_schema_versions",
        "supported_rule_refs",
        "supported_reconstructors",
        "available_asset_refs",
        "observation_domain_ref",
        "privacy_boundary_ref",
        "execution_permissions",
    }
)
CANDIDATE_KEYS = frozenset(
    {
        "candidate_ref",
        "schema_version",
        "protocol_version",
        "required_agent_version",
        "rule_ref",
        "reconstructor_ref",
        "reconstruction_mode",
        "observation_domain_ref",
        "privacy_boundary_ref",
        "asset_refs",
        "lookup_refs",
        "reconstruction_condition_refs",
        "routing_refs",
        "requires_raw_channel",
        "raw_channel_ref",
    }
)


@dataclass(frozen=True, slots=True)
class VerificationFailure(Exception):
    """One stable, non-sensitive verifier failure."""

    reason_code: str
    file: str
    line: int = 1

    def __str__(self) -> str:
        """Return only the stable reason code."""

        return self.reason_code


class StrictJsonFailure(ValueError):
    """Internal strict-JSON signal translated at the approved file boundary."""

    def __init__(self, reason_code: str) -> None:
        """Store one stable JSON reason code."""

        self.reason_code = reason_code
        super().__init__(reason_code)


def _fail(reason_code: str, file: Path | str, line: int = 1) -> NoReturn:
    """Raise one stable verifier failure."""

    raise VerificationFailure(reason_code, Path(file).as_posix(), line)


def _read_text(path: Path | str) -> str:
    """Read one exact repository path as UTF-8."""

    relative = Path(path)
    try:
        return (ROOT / relative).read_text(encoding="utf-8")
    except FileNotFoundError:
        _fail("REQUIRED_FILE_MISSING", relative)
    except (OSError, UnicodeError):
        _fail("REQUIRED_FILE_NOT_UTF8", relative)


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Decode an object while rejecting duplicate member names."""

    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonFailure("DUPLICATE_JSON_MEMBER")
        result[key] = value
    return result


def _reject_constant(_token: str) -> NoReturn:
    """Reject JSON NaN and Infinity tokens."""

    raise StrictJsonFailure("NON_FINITE_JSON_NUMBER")


def _ensure_finite(value: Any) -> None:
    """Reject nested non-finite values and non-string object keys."""

    if isinstance(value, float) and not math.isfinite(value):
        raise StrictJsonFailure("NON_FINITE_JSON_NUMBER")
    if isinstance(value, dict):
        for key, nested in value.items():
            if not isinstance(key, str):
                raise StrictJsonFailure("NON_STRING_JSON_MEMBER")
            _ensure_finite(nested)
    elif isinstance(value, list):
        for nested in value:
            _ensure_finite(nested)


def _load_json(path: Path | str) -> Any:
    """Load strict UTF-8 JSON from one exact repository path."""

    relative = Path(path)
    try:
        value = json.loads(
            _read_text(relative),
            object_pairs_hook=_strict_pairs,
            parse_constant=_reject_constant,
        )
        _ensure_finite(value)
        return value
    except StrictJsonFailure as error:
        _fail(error.reason_code, relative)
    except json.JSONDecodeError as error:
        _fail("JSON_PARSE_FAILED", relative, error.lineno)


def _canonical_json(value: Any) -> str:
    """Serialize using the locked deterministic JSON contract."""

    try:
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError, RecursionError):
        _fail("CANONICAL_JSON_FAILED", "<value>")


def _canonical_sha256(value: Any) -> str:
    """Return SHA-256 over canonical UTF-8 JSON."""

    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _raw_sha256(path: Path | str) -> str:
    """Return SHA-256 over one exact file's bytes."""

    relative = Path(path)
    try:
        return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    except FileNotFoundError:
        _fail("REQUIRED_FILE_MISSING", relative)
    except OSError:
        _fail("FILE_READ_FAILED", relative)


def _release_inventory() -> frozenset[str]:
    """Inventory only the fixed release directory and reject links."""

    release_root = ROOT / RELEASE_DIR
    if not release_root.is_dir() or release_root.is_symlink():
        _fail("RELEASE_DIRECTORY_MISSING", RELEASE_DIR)
    inventory: set[str] = set()
    pending = [release_root]
    while pending:
        directory = pending.pop()
        try:
            entries = sorted(directory.iterdir(), key=lambda item: item.name)
        except OSError:
            _fail("RELEASE_DIRECTORY_UNREADABLE", directory.relative_to(ROOT))
        for entry in entries:
            relative = entry.relative_to(release_root).as_posix()
            if entry.is_symlink():
                _fail("RELEASE_SYMLINK_FORBIDDEN", RELEASE_DIR / relative)
            if entry.is_dir():
                pending.append(entry)
            elif entry.is_file():
                inventory.add(relative)
            else:
                _fail("RELEASE_SPECIAL_FILE_FORBIDDEN", RELEASE_DIR / relative)
    return frozenset(inventory)


def _check_presence_and_compile() -> None:
    """Require the exact deliverables and compile the five new Python files."""

    required = PYTHON_FILES + (FIXTURE_PATH,)
    for relative in required:
        if not (ROOT / relative).is_file():
            _fail("REQUIRED_FILE_MISSING", relative)
        _read_text(relative)
    inventory = _release_inventory()
    if inventory != EXPECTED_RELEASE_INVENTORY:
        _fail("RELEASE_INVENTORY_MISMATCH", RELEASE_DIR)
    with tempfile.TemporaryDirectory(prefix="w7tp-verifier-pyc-") as directory:
        output = Path(directory)
        for index, relative in enumerate(PYTHON_FILES):
            try:
                py_compile.compile(
                    str(ROOT / relative),
                    cfile=str(output / f"{index}.pyc"),
                    doraise=True,
                )
            except py_compile.PyCompileError as error:
                line = int(getattr(error.exc_value, "lineno", 1) or 1)
                _fail("PYTHON_COMPILE_FAILED", relative, line)


def _call_name(node: ast.expr) -> str:
    """Render a direct dotted call target."""

    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _call_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _ancestor_names(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> tuple[str, str]:
    """Return the nearest function and class ancestor names."""

    function_name = ""
    class_name = ""
    current = parents.get(node)
    while current is not None:
        if not function_name and isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function_name = current.name
        if not class_name and isinstance(current, ast.ClassDef):
            class_name = current.name
        current = parents.get(current)
    return function_name, class_name


def _check_python_ast() -> None:
    """Reject unfinished, dynamic, nondeterministic, or unsafe code paths."""

    forbidden_imports = {
        "anthropic",
        "datetime",
        "httpx",
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
        "eval",
        "exec",
        "os.popen",
        "os.system",
        "pickle.load",
        "pickle.loads",
        "subprocess.call",
        "subprocess.check_call",
        "subprocess.check_output",
    }
    allowed_subprocess_contexts = {
        ("_run_local_entrypoint", ""),
        ("run", "LocalLinuxExecutor"),
        ("run", "SSHExecutor"),
        ("transfer_release", "SSHExecutor"),
    }
    marker_values = ("TO" + "DO", "FIX" + "ME")
    for relative in PYTHON_FILES:
        text = _read_text(relative)
        for marker in marker_values:
            location = text.find(marker)
            if location >= 0:
                _fail("UNFINISHED_MARKER", relative, text[:location].count("\n") + 1)
        try:
            tree = ast.parse(text, filename=relative.as_posix())
        except SyntaxError as error:
            _fail("PYTHON_PARSE_FAILED", relative, int(error.lineno or 1))
        parents = {
            child: parent
            for parent in ast.walk(tree)
            for child in ast.iter_child_nodes(parent)
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Pass):
                _fail("EMPTY_PASS_FORBIDDEN", relative, node.lineno)
            if (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant)
                and node.value.value is Ellipsis
            ):
                _fail("ELLIPSIS_FORBIDDEN", relative, node.lineno)
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = (
                    [alias.name for alias in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or ""]
                )
                if any(name.split(".", 1)[0] in forbidden_imports for name in names):
                    _fail("FORBIDDEN_IMPORT", relative, node.lineno)
            if not isinstance(node, ast.Call):
                continue
            name = _call_name(node.func)
            if name in forbidden_calls or name == "compile":
                _fail("FORBIDDEN_EXECUTION_API", relative, node.lineno)
            if name == "subprocess.Popen":
                function_name, class_name = _ancestor_names(node, parents)
                if relative != RUNNER_PATH or (
                    function_name,
                    class_name,
                ) != ("run_installed_service", ""):
                    _fail("SUBPROCESS_OUTSIDE_CONSTRAINED_EXECUTOR", relative, node.lineno)
                shell_keywords = [item for item in node.keywords if item.arg == "shell"]
                if shell_keywords and not (
                    len(shell_keywords) == 1
                    and isinstance(shell_keywords[0].value, ast.Constant)
                    and shell_keywords[0].value.value is False
                ):
                    _fail("SUBPROCESS_SHELL_POLICY_FAILED", relative, node.lineno)
            if name == "subprocess.run":
                function_name, class_name = _ancestor_names(node, parents)
                deployer_context_allowed = (
                    relative == DEPLOYER_PATH
                    and (function_name, class_name) in allowed_subprocess_contexts
                )
                healthcheck_context_allowed = (
                    relative == HEALTHCHECK_PATH
                    and (function_name, class_name) == ("run_healthcheck", "")
                )
                if not (deployer_context_allowed or healthcheck_context_allowed):
                    _fail("SUBPROCESS_OUTSIDE_CONSTRAINED_EXECUTOR", relative, node.lineno)
                shell_keywords = [item for item in node.keywords if item.arg == "shell"]
                explicit_shell_false = (
                    len(shell_keywords) == 1
                    and isinstance(shell_keywords[0].value, ast.Constant)
                    and shell_keywords[0].value.value is False
                )
                if (
                    deployer_context_allowed
                    and not explicit_shell_false
                    or healthcheck_context_allowed
                    and shell_keywords
                    and not explicit_shell_false
                ):
                    _fail("SUBPROCESS_SHELL_POLICY_FAILED", relative, node.lineno)


def _require_string_list(value: Any, file: Path, field: str) -> None:
    """Require a duplicate-free array of non-empty strings."""

    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ) or len(value) != len(set(value)):
        _fail("FIXTURE_SCHEMA_FAILED", file)


def _check_fixture_schema() -> dict[str, Any]:
    """Validate the closed fixed-vector structure and commit semantics."""

    fixture = _load_json(FIXTURE_PATH)
    if not isinstance(fixture, dict) or frozenset(fixture) != FIXTURE_KEYS:
        _fail("FIXTURE_SCHEMA_FAILED", FIXTURE_PATH)
    fixed_scalars = {
        "schema_version": "w7tp-small-agent-deployment-vectors/v0.1",
        "run_id": RUN_ID,
        "release_version": RELEASE_VERSION,
        "policy_sha256": POLICY_SHA256,
    }
    if any(fixture.get(key) != value for key, value in fixed_scalars.items()):
        _fail("FIXTURE_IDENTITY_MISMATCH", FIXTURE_PATH)
    capability = fixture.get("capability_manifest")
    candidate = fixture.get("candidate")
    if not isinstance(capability, dict) or frozenset(capability) != CAPABILITY_KEYS:
        _fail("FIXTURE_SCHEMA_FAILED", FIXTURE_PATH)
    if not isinstance(candidate, dict) or frozenset(candidate) != CANDIDATE_KEYS:
        _fail("FIXTURE_SCHEMA_FAILED", FIXTURE_PATH)
    for key in (
        "supported_schema_versions",
        "supported_rule_refs",
        "supported_reconstructors",
        "available_asset_refs",
        "execution_permissions",
    ):
        _require_string_list(capability.get(key), FIXTURE_PATH, key)
    for key in (
        "asset_refs",
        "lookup_refs",
        "reconstruction_condition_refs",
        "routing_refs",
    ):
        _require_string_list(candidate.get(key), FIXTURE_PATH, key)
    if candidate.get("requires_raw_channel") is not False or candidate.get("raw_channel_ref") is not None:
        _fail("FIXTURE_RAW_CHANNEL_FORBIDDEN", FIXTURE_PATH)
    d1_intent = fixture.get("d1_intent")
    if not isinstance(d1_intent, dict) or frozenset(d1_intent) != {
        "intent_ref",
        "task_ref",
        "goal_ref",
    } or any(not isinstance(value, str) or not value for value in d1_intent.values()):
        _fail("FIXTURE_SCHEMA_FAILED", FIXTURE_PATH)
    for field in (
        "gateway_request",
        "previous_state",
        "proposed_state",
        "observation_domains",
        "expected",
    ):
        if not isinstance(fixture.get(field), dict):
            _fail("FIXTURE_SCHEMA_FAILED", FIXTURE_PATH)
    if fixture["gateway_request"]:
        _fail("PRODUCTION_GATEWAY_FIXTURE_FORBIDDEN", FIXTURE_PATH)
    results = fixture.get("gateway_results")
    if not isinstance(results, dict) or frozenset(results) != {
        "ALLOW",
        "HOLD",
        "BLOCK",
        "QUARANTINE",
    }:
        _fail("FIXTURE_GATE_SCHEMA_FAILED", FIXTURE_PATH)
    for decision in ("ALLOW", "HOLD", "BLOCK", "QUARANTINE"):
        result = results[decision]
        if not isinstance(result, dict) or result.get("final_decision") != decision:
            _fail("FIXTURE_GATE_SCHEMA_FAILED", FIXTURE_PATH)
        expected_commit = decision == "ALLOW"
        if result.get("commit_applied") is not expected_commit:
            _fail("ALLOW_ONLY_COMMIT_FAILED", FIXTURE_PATH)
        expected_state = result.get("proposed") if expected_commit else result.get("previous")
        if result.get("committed") != expected_state:
            _fail("ALLOW_ONLY_COMMIT_FAILED", FIXTURE_PATH)
        if decision == "ALLOW" and (
            not isinstance(result.get("tfid"), str)
            or not isinstance(result.get("total_field_hash"), str)
        ):
            _fail("FIXTURE_GATE_SCHEMA_FAILED", FIXTURE_PATH)
    return fixture


def _check_release_contract() -> str:
    """Verify release hashes, identity, capability schema, and safety manifests."""

    json_files = sorted(
        name for name in EXPECTED_RELEASE_INVENTORY if name.endswith(".json")
    )
    documents = {
        name: _load_json(RELEASE_DIR / name)
        for name in json_files
    }
    release = documents["release_manifest.json"]
    files_document = documents["files_sha256.json"]
    capability_schema = documents["capability_manifest.schema.json"]
    capability = documents["capability_manifest_template.json"]
    install = documents["install_manifest.json"]
    rollback = documents["rollback_manifest.json"]
    policy_reference = documents["runtime_policy_reference.json"]
    if not all(
        isinstance(item, dict)
        for item in (
            release,
            files_document,
            capability_schema,
            capability,
            install,
            rollback,
            policy_reference,
        )
    ):
        _fail("RELEASE_JSON_OBJECT_REQUIRED", RELEASE_DIR)
    files = files_document.get("files")
    if not isinstance(files, dict) or frozenset(files) != RELEASE_PAYLOAD:
        _fail("RELEASE_FILES_MAP_MISMATCH", RELEASE_DIR / "files_sha256.json")
    digest_pattern = re.compile(r"^[0-9a-f]{64}$")
    for name, expected in files.items():
        if not isinstance(expected, str) or not digest_pattern.fullmatch(expected):
            _fail("RELEASE_FILE_HASH_INVALID", RELEASE_DIR / "files_sha256.json")
        if _raw_sha256(RELEASE_DIR / name) != expected:
            _fail("RELEASE_FILE_HASH_MISMATCH", RELEASE_DIR / name)
    if files_document.get("schema_version") != "w7tp.small-agent.files-sha256/v0.1" or files_document.get("release_version") != RELEASE_VERSION:
        _fail("FILES_MANIFEST_IDENTITY_MISMATCH", RELEASE_DIR / "files_sha256.json")
    identity = release.get("release_identity")
    release_sha256 = release.get("release_sha256")
    if not isinstance(identity, dict) or not isinstance(release_sha256, str):
        _fail("RELEASE_IDENTITY_MISSING", RELEASE_DIR / "release_manifest.json")
    if identity.get("files_sha256") != files or identity.get("policy_sha256") != POLICY_SHA256:
        _fail("RELEASE_IDENTITY_MISMATCH", RELEASE_DIR / "release_manifest.json")
    if identity.get("release_version") != RELEASE_VERSION or identity.get("status") != "CANDIDATE_DEPLOYABLE":
        _fail("RELEASE_IDENTITY_MISMATCH", RELEASE_DIR / "release_manifest.json")
    if _canonical_sha256(identity) != release_sha256 or not digest_pattern.fullmatch(release_sha256):
        _fail("RELEASE_SHA256_MISMATCH", RELEASE_DIR / "release_manifest.json")
    if release.get("files_sha256_hash") != _canonical_sha256(files_document):
        _fail("FILES_MANIFEST_HASH_MISMATCH", RELEASE_DIR / "release_manifest.json")
    hashed_manifests = {
        "capability_manifest_template_sha256": capability,
        "install_manifest_sha256": install,
        "rollback_manifest_sha256": rollback,
    }
    if any(identity.get(key) != _canonical_sha256(value) for key, value in hashed_manifests.items()):
        _fail("RELEASE_DEPENDENCY_HASH_MISMATCH", RELEASE_DIR / "release_manifest.json")
    if identity.get("runtime_policy_reference_sha256") != _raw_sha256(
        RELEASE_DIR / "runtime_policy_reference.json"
    ):
        _fail("POLICY_REFERENCE_HASH_MISMATCH", RELEASE_DIR / "release_manifest.json")
    release_flags = {
        "direct_tfs_commit": False,
        "allow_only_commit": True,
        "canonical_promotion": False,
        "production_deployment_complete": False,
    }
    if any(release.get(key) is not value for key, value in release_flags.items()):
        _fail("RELEASE_GOVERNANCE_FLAG_MISMATCH", RELEASE_DIR / "release_manifest.json")
    try:
        Draft202012Validator.check_schema(capability_schema)
        Draft202012Validator(capability_schema).validate(capability)
    except (SchemaError, ValidationError) as error:
        _fail(
            "CAPABILITY_SCHEMA_FAILED",
            RELEASE_DIR / "capability_manifest.schema.json",
            int(getattr(error, "lineno", 1) or 1),
        )
    if capability.get("status") != "CANDIDATE_DEPLOYABLE" or capability.get("agent_version") != RELEASE_VERSION or capability.get("policy_sha256") != POLICY_SHA256 or capability.get("direct_commit") is not False:
        _fail("CAPABILITY_MANIFEST_POLICY_FAILED", RELEASE_DIR / "capability_manifest_template.json")
    install_flags = {
        "current_switch": "ATOMIC_SYMLINK_REPLACE",
        "service_mode": "USER_SYSTEMD_IF_AVAILABLE",
        "restart_policy": "ONLY_IF_RELEASE_CONTENT_CHANGED",
        "requires_root": False,
        "firewall_write": False,
        "router_write": False,
        "database_write": False,
        "external_port_open": False,
    }
    if any(install.get(key) != value for key, value in install_flags.items()):
        _fail("INSTALL_MANIFEST_UNSAFE", RELEASE_DIR / "install_manifest.json")
    rollback_flags = {
        "rollback_action": "ATOMIC_RESTORE_PREVIOUS_CURRENT_TARGET",
        "healthcheck_after_rollback": True,
        "delete_previous_release": False,
        "delete_failed_release": False,
        "requires_root": False,
        "router_write": False,
        "database_write": False,
    }
    if any(rollback.get(key) != value for key, value in rollback_flags.items()):
        _fail("ROLLBACK_MANIFEST_UNSAFE", RELEASE_DIR / "rollback_manifest.json")
    policy_flags = {
        "status": "CANDIDATE_DEPLOYABLE",
        "reference_mode": "READ_ONLY",
        "policy_sha256": POLICY_SHA256,
        "canonical_write": False,
        "pointer_write": False,
    }
    if any(policy_reference.get(key) != value for key, value in policy_flags.items()):
        _fail("POLICY_REFERENCE_CONTRACT_FAILED", RELEASE_DIR / "runtime_policy_reference.json")
    active_policy = _load_json(
        Path("runtime/total_field/active/ACTIVE_TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL.json")
    )
    if not isinstance(active_policy, dict) or _canonical_sha256(active_policy.get("policy")) != POLICY_SHA256:
        _fail("ACTIVE_POLICY_HASH_MISMATCH", "runtime/total_field/active/ACTIVE_TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL.json")
    return release_sha256


def _run_checked(command: list[str], reason_code: str) -> subprocess.CompletedProcess[str]:
    """Run one local validation command without a shell or remote side effect."""

    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            shell=False,
            timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired):
        _fail(reason_code, command[1] if len(command) > 1 else "<command>")
    if result.returncode != 0:
        _fail(reason_code, command[1] if len(command) > 1 else "<command>")
    return result


def _check_builder_and_tests() -> None:
    """Verify the current source release and the 30-case focused test."""

    builder = _run_checked(
        [
            sys.executable,
            str(ROOT / BUILDER_PATH),
            "verify-security-runtime-patch",
            "--output-dir",
            str(ROOT / CURRENT_RELEASE_DIR),
        ],
        "RELEASE_BUILDER_VERIFY_FAILED",
    )
    if (
        "STATE=PASS_W7TP_SMALL_AGENT_SECURITY_RUNTIME_PATCH_RELEASE_VERIFIED"
        not in builder.stdout
    ):
        _fail("RELEASE_BUILDER_OUTPUT_FAILED", BUILDER_PATH)
    test_source = ast.parse(_read_text(TEST_PATH), filename=TEST_PATH.as_posix())
    test_count = sum(
        1
        for node in ast.walk(test_source)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    if test_count != 30:
        _fail("FOCUSED_TEST_COUNT_MISMATCH", TEST_PATH)
    focused = _run_checked(
        [sys.executable, str(ROOT / TEST_PATH)],
        "FOCUSED_TEST_FAILED",
    )
    transcript = focused.stdout + focused.stderr
    if not re.search(r"Ran\s+30\s+tests?\b", transcript) or not re.search(
        r"(?m)^OK$", transcript
    ):
        _fail("FOCUSED_TEST_OUTPUT_FAILED", TEST_PATH)


def _check_deployment_safety_and_formal_nodes() -> None:
    """Resolve exactly eight formal nodes without constructing an executor."""

    from tools.deploy_w7tp_small_agent_all_nodes import (
        DeploymentError,
        _safe_command,
        resolve_formal_nodes,
    )

    dangerous = (
        ("sudo", "systemctl", "restart", "w7tp-small-agent"),
        ("systemctl", "restart", "w7tp-small-agent"),
        ("iptables", "-L"),
        ("nft", "list", "ruleset"),
        ("firewall-cmd", "--state"),
        ("reboot",),
        ("mysql",),
        ("psql",),
        ("sqlite3",),
        ("nvram", "show"),
    )
    for command in dangerous:
        try:
            _safe_command(command)
        except DeploymentError:
            continue
        _fail("UNSAFE_COMMAND_ALLOWLIST_FAILED", DEPLOYER_PATH)
    try:
        accepted = _safe_command(
            ("systemctl", "--user", "is-active", "w7tp-small-agent.service")
        )
    except DeploymentError:
        _fail("USER_SERVICE_COMMAND_REJECTED", DEPLOYER_PATH)
    if accepted[0:2] != ("systemctl", "--user"):
        _fail("USER_SERVICE_COMMAND_REJECTED", DEPLOYER_PATH)
    try:
        nodes = resolve_formal_nodes(ROOT)
    except DeploymentError:
        _fail("FORMAL_NODE_RESOLUTION_FAILED", DEPLOYER_PATH)
    if len(nodes) != 8:
        _fail("FORMAL_NODE_COUNT_MISMATCH", "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_CANONICAL.json")
    eligible = [
        node
        for node in nodes
        if isinstance(node.deployment_eligibility, dict)
        and node.deployment_eligibility.get("status") == "ELIGIBLE"
    ]
    routers = [node for node in nodes if "router" in node.kind.casefold()]
    if eligible:
        _fail("UNEXPECTED_ELIGIBLE_NODE", DEPLOYER_PATH)
    if len(routers) != 1:
        _fail("ROUTER_NODE_COUNT_MISMATCH", DEPLOYER_PATH)
    router_eligibility = routers[0].deployment_eligibility
    if not isinstance(router_eligibility, dict) or router_eligibility.get("reason_code") != "HOLD_ROUTER_WRITE_NOT_AUTHORIZED":
        _fail("ROUTER_WRITE_BOUNDARY_FAILED", DEPLOYER_PATH)
    if any(
        not isinstance(node.deployment_eligibility, dict)
        or node.deployment_eligibility.get("status") != "HOLD"
        for node in nodes
    ):
        _fail("FORMAL_AUTHORITY_HOLD_FAILED", DEPLOYER_PATH)


def _check_service_self_test(fixture: dict[str, Any]) -> None:
    """Run the local fixed vector and preserve the production-gateway HOLD."""

    from tools.w7tp_small_agent_service_runner import ServiceError, run_self_test

    try:
        result = run_self_test(fixture)
    except ServiceError:
        _fail("SERVICE_SELF_TEST_FAILED", RUNNER_PATH)
    pass_fields = (
        "capability_manifest",
        "d1_projection",
        "candidate_replay",
        "common_receive_path",
        "allow_only_commit",
        "persona_governance_separation",
        "d7_reference_only",
    )
    if result.get("status") != "PASS" or any(
        result.get(field) != "PASS" for field in pass_fields
    ):
        _fail("SERVICE_SELF_TEST_FAILED", RUNNER_PATH)
    if result.get("commit_gates") != {
        "ALLOW": "PASS",
        "HOLD": "PASS",
        "BLOCK": "PASS",
        "QUARANTINE": "PASS",
    }:
        _fail("SERVICE_COMMIT_GATES_FAILED", RUNNER_PATH)
    if result.get("llm_direct_commit") != "BLOCKED" or result.get("fixture_gateway") != "TEST_ONLY":
        _fail("SERVICE_CANDIDATE_BOUNDARY_FAILED", RUNNER_PATH)
    if result.get("total_field_pull") != "TEST_ONLY_PASS" or result.get("llm_push") != "TEST_ONLY_PASS":
        _fail("SERVICE_FIXED_VECTOR_INGRESS_FAILED", RUNNER_PATH)
    if result.get("gateway_profile_status") != "HOLD_VECTOR_GATEWAY_PROFILE_NOT_CONFIGURED":
        _fail("PRODUCTION_GATEWAY_STATUS_FALSIFIED", RUNNER_PATH)
    if result.get("production_gateway_results_hash") is not None:
        _fail("PRODUCTION_GATEWAY_STATUS_FALSIFIED", RUNNER_PATH)


def _check_sensitive_material() -> None:
    """Reject credential-shaped material without exposing matched content."""

    inspected = PYTHON_FILES + (FIXTURE_PATH,)
    inspected += tuple(RELEASE_DIR / name for name in sorted(EXPECTED_RELEASE_INVENTORY))
    forbidden_patterns = (
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----\s+"
            r"[A-Za-z0-9+/=\r\n]{32,}\s+"
            r"-----END [A-Z ]*PRIVATE KEY-----"
        ),
        re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
        re.compile(r"\bAKIA(?!IOSFODNN7EXAMPLE)[0-9A-Z]{16}\b"),
        re.compile(r"(?i)bearer\s+[A-Za-z0-9._~-]{20,}"),
    )
    for relative in inspected:
        text = _read_text(relative)
        for pattern in forbidden_patterns:
            match = pattern.search(text)
            if match is not None:
                _fail("RAW_SECRET_MATERIAL_FOUND", relative, text[: match.start()].count("\n") + 1)


def _check_protected_files() -> None:
    """Require every protected baseline to retain its exact task-start hash."""

    for path, expected in PROTECTED_SHA256.items():
        if _raw_sha256(path) != expected:
            _fail("PROTECTED_FILE_CHANGED", path)


def verify() -> str:
    """Run the complete local-only deployment-package verification."""

    _check_presence_and_compile()
    _check_python_ast()
    fixture = _check_fixture_schema()
    release_sha256 = _check_release_contract()
    _check_builder_and_tests()
    _check_deployment_safety_and_formal_nodes()
    _check_service_self_test(fixture)
    _check_sensitive_material()
    _check_protected_files()
    return release_sha256


def main() -> int:
    """Print a deterministic PASS or one stable failure triple."""

    try:
        release_sha256 = verify()
    except VerificationFailure as error:
        print("STATE=HOLD_VERIFY_W7TP_SMALL_AGENT_ALL_NODE_DEPLOYMENT_PACKAGE")
        print(f"REASON_CODE={error.reason_code}")
        print(f"FILE={error.file}")
        print(f"LINE={error.line}")
        return 1
    print("STATE=PASS_VERIFY_W7TP_SMALL_AGENT_ALL_NODE_DEPLOYMENT_PACKAGE")
    print(f"RUN_ID={RUN_ID}")
    print(f"RELEASE_VERSION={RELEASE_VERSION}")
    print(f"RELEASE_SHA256={release_sha256}")
    print(f"POLICY_SHA256={POLICY_SHA256}")
    print("FORMAL_NODES=8")
    print("ELIGIBLE_NODES=0")
    print("ROUTER_NODES_HELD=1")
    print("REMOTE_COMMANDS_EXECUTED=0")
    print("SERVICE_SELF_TEST=PASS")
    print("GATEWAY_PROFILE_STATUS=HOLD_VECTOR_GATEWAY_PROFILE_NOT_CONFIGURED")
    print("TEST_COUNT=30")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
