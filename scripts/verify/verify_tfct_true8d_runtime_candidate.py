#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused, deterministic verifier for the TFCT TRUE8D runtime candidate."""

from __future__ import annotations

import ast
import hashlib
import json
import py_compile
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, RefResolver


ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "TFCT_TRUE8D_RUNTIME_CANDIDATE_V0_1"

NEW_FILES = (
    "tools/tfct_true8d_runtime_candidate.py",
    "tools/eightd_gte_parser_candidate.py",
    "tools/total_field_candidate_gateway.py",
    "tools/w7tp_small_transport_agent_candidate.py",
    "tools/xiaoj_candidate_adapter.py",
    "tools/adi_index_strategy_candidate.py",
    "runtime/total_field/candidate/tfct_true8d_runtime_policy_v0_1.json",
    "schemas/field/8d_gte_runtime_candidate_profile_v0_1.schema.json",
    "tests/fixtures/tfct_true8d_runtime_candidate_vectors.json",
    "tests/test_tfct_true8d_runtime_candidate.py",
    "scripts/verify/verify_tfct_true8d_runtime_candidate.py",
    "docs/total_field/TFCT_TRUE8D_RUNTIME_CANDIDATE_IMPLEMENTATION_REPORT.md",
)

PYTHON_FILES = tuple(path for path in NEW_FILES if path.endswith(".py"))
POLICY_PATH = "runtime/total_field/candidate/tfct_true8d_runtime_policy_v0_1.json"
PROFILE_SCHEMA_PATH = "schemas/field/8d_gte_runtime_candidate_profile_v0_1.schema.json"
BASE_GTE_SCHEMA_PATH = "schemas/field/8d_governance_tensor_expression_candidate.schema.json"
FIXTURE_PATH = "tests/fixtures/tfct_true8d_runtime_candidate_vectors.json"
TEST_PATH = "tests/test_tfct_true8d_runtime_candidate.py"
REPORT_PATH = "docs/total_field/TFCT_TRUE8D_RUNTIME_CANDIDATE_IMPLEMENTATION_REPORT.md"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

HEAD_PROTECTED = (
    "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_CANONICAL.json",
    "runtime/total_field/active/ACTIVE_CODEX_TOTAL_FIELD_GLOBAL_AGENT_DOMAIN_POINTER.txt",
    "runtime/total_field/active/ACTIVE_DOMAIN_BETA_DEPLOYMENT_POINTER.txt",
    "runtime/total_field/active/ACTIVE_POS_OFFICIAL_CHAIN_POINTER.txt",
    "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_POINTER.txt",
    "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_POINTER.txt",
    "runtime/total_field/active/ACTIVE_TRUE8D_ROUTER_ALLNODE_MERGE_POINTER.txt",
    "runtime/total_field/active/ACTIVE_TRUE8D_ROUTER_BOUNDARY_POINTER.txt",
    "runtime/total_field/active/ACTIVE_V4_TRUE8D_TIPO_LANDING_POINTER.txt",
    "tensor_8d",
    "tensor_8d_boot.py",
)

BASELINE_SHA256 = {
    "tools/d3_coordinate_transition_candidate.py": "b1e67f1d22d0e53785f3939885dcb690907cb68071f7f3a682ce368a356bb918",
    "runtime/total_field/candidate/d3_coordinate_transition_rules_v0_3.json": "43befc782b086bce9bdf5be0e686de6645b6416b7d582afc44699a035623b287",
    "tools/w7tp_packet_inference_runtime.py": "7918b485b83d1523c98636366c3bd41aaf3b514b0a1b35b4b1ffad066bc1205b",
    "scripts/verify/verify_d3_coordinate_transition_candidate.py": "9ffe9011fab06f26501f024b1fd21e804870d2f42f242abbcc4e964ecfb72fe4",
    "scripts/verify/verify_w7tp_packet_inference_runtime.py": "22c722253918c86888cd40e2e742cc1f4e6bfe760a81cb92f4532e2a554e905a",
    "tests/test_d3_coordinate_transition_candidate.py": "7b21e3416c8bace9d1be6521fef3cf0f383ea0c266caa495feff77e80ebfcb01",
    "tests/test_w7tp_packet_runtime_d3_replay.py": "f87bb7845b0de81ea8ea778f59002d18584699e063da5058c15760112e4527a5",
    "docs/total_field/D3_DETERMINISTIC_COORDINATE_TRANSITION_CANDIDATE_REPORT.md": "74a6dd51fd2047dd00ce1bda39cc0d94b839c6da665de1c319755a10f920e2bb",
    "docs/total_field/TFCT_THEORY_CANDIDATE.md": "187782168272bc75aca5064988cf6bc23c88b42ce0a487d11d23801a702aa324",
    "docs/total_field/TFCT_MATHEMATICS_CANDIDATE.md": "17ff4bbd2359dfca5efdda64f8d043a5a922fbcb3edc1b65c62ab31328a10be2",
    "docs/total_field/TFCT_TRUE8D_ENGINEERING_CANDIDATE.md": "8c58361aa0949c0ef9040248732473f84af0f59fb405c72fa6b69ab902a64fb4",
    "docs/total_field/8D_GOVERNANCE_TENSOR_EXPRESSION_CANDIDATE.md": "6f607cff51fbf31ffc1fccc644270562bff243a72037453c78e12847f8cb0070",
    "docs/total_field/W7TP_SMALL_GENERATIVE_TRANSPORT_AGENT_CANDIDATE.md": "09372e4782f8bacdd5b7771aa6939cadb422d0a80496fb504d10e423063e1610",
    "docs/total_field/XIAOJ_SOVEREIGN_AGENT_CANDIDATE.md": "f78a05307446455a66f9f97c056eb1be3c0b12d0f35131347810e76836452710",
    "docs/total_field/ADI_INDEX_STRATEGY_CANDIDATE.md": "2679eea8dcbaa88d06d54c4b849e01665ccaf68376d964b187ab3e63fa20f68b",
    "docs/total_field/TFCT_LIVING_LAB_DEMO_CANDIDATE.md": "ae0de334b273bdd0c6adb6db0223800152b8f6aeb7be3f5bc7d4b072e88628de",
    "docs/total_field/TFCT_TRUE8D_W7TP_CONSOLIDATION_REPORT.md": "0f4f0c98fef5162ae5509c9134660b86d28d9b6ada702ccb92d483d0bbc9ae07",
    "schemas/field/8d_governance_tensor_expression_candidate.schema.json": "cf468878aa95ca0516017af9cb2e7f41cd41f195548cecdf1a3d7b4a6f473e98",
    "scripts/verify/verify_tfct_true8d_w7tp_candidate_consolidation.py": "b486856cfe762e9535e8709e0f3ea0735e001f4ab7f8d53a87948f961d084582",
    "tests/test_tfct_true8d_w7tp_candidate_consolidation.py": "1599ef8d9fd2afda50e72e0fb70a14f018a620f08433302d664dbadec55348ac",
}


@dataclass(frozen=True)
class VerificationFailure(Exception):
    """Single stable verifier failure without sensitive payload content."""

    reason_code: str
    file: str
    line: int = 1

    def __str__(self) -> str:
        return self.reason_code


def _fail(reason_code: str, file: str, line: int = 1) -> None:
    """Raise one structured verifier failure."""

    raise VerificationFailure(reason_code, file, line)


def _read(path: str) -> str:
    """Read one approved path as UTF-8 text."""

    try:
        return (ROOT / path).read_text(encoding="utf-8")
    except FileNotFoundError:
        _fail("NEW_FILE_MISSING", path)
    except UnicodeError:
        _fail("NEW_FILE_NOT_UTF8", path)
    raise AssertionError("unreachable")


def _load_json(path: str) -> Any:
    """Load strict JSON while rejecting non-finite constants."""

    try:
        return json.loads(_read(path), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (json.JSONDecodeError, ValueError):
        _fail("JSON_PARSE_FAILED", path)
    raise AssertionError("unreachable")


def _sha256(path: str) -> str:
    """Return SHA-256 for one exact protected path."""

    try:
        return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    except FileNotFoundError:
        _fail("PROTECTED_FILE_MISSING", path)
    raise AssertionError("unreachable")


def _check_presence_and_compile() -> None:
    """Require all deliverables and compile every new Python file."""

    for path in NEW_FILES:
        if not (ROOT / path).is_file():
            _fail("NEW_FILE_MISSING", path)
    for path in PYTHON_FILES:
        try:
            py_compile.compile(str(ROOT / path), doraise=True)
        except py_compile.PyCompileError as error:
            line = int(getattr(error.exc_value, "lineno", 1) or 1)
            _fail("PYTHON_COMPILE_FAILED", path, line)


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
        "compile",
        "datetime.datetime.now",
        "datetime.now",
        "eval",
        "exec",
        "importlib.import_module",
        "os.getrandom",
        "os.urandom",
        "pickle.load",
        "pickle.loads",
        "secrets.token_bytes",
        "secrets.token_hex",
        "secrets.token_urlsafe",
    }

    def call_name(node: ast.expr) -> str:
        """Render a stable dotted name for a direct call target."""

        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            prefix = call_name(node.value)
            return f"{prefix}.{node.attr}" if prefix else node.attr
        return ""

    for path in PYTHON_FILES:
        text = _read(path)
        for marker in ("TO" + "DO", "FIX" + "ME", "Not" + "ImplementedError"):
            if marker in text:
                _fail("BANNED_STUB_MARKER", path, text[: text.index(marker)].count("\n") + 1)
        tree = ast.parse(text, filename=path)
        if path.startswith("tools/"):
            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    if ast.get_docstring(node) is None:
                        _fail("DOCSTRING_MISSING", path, node.lineno)
        for node in ast.walk(tree):
            if isinstance(node, ast.Pass):
                _fail("EMPTY_PASS_STUB", path, node.lineno)
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
                    _fail("FORBIDDEN_DYNAMIC_OR_NETWORK_IMPORT", path, node.lineno)
            if isinstance(node, ast.Call):
                name = call_name(node.func)
                if name in forbidden_calls:
                    _fail("FORBIDDEN_EXECUTION_API", path, node.lineno)
                if name in {
                    "subprocess.call",
                    "subprocess.check_call",
                    "subprocess.check_output",
                    "subprocess.run",
                    "subprocess.Popen",
                } and node.args:
                    command = node.args[0]
                    if isinstance(command, (ast.List, ast.Tuple)) and command.elts:
                        first = command.elts[0]
                        if isinstance(first, ast.Constant) and first.value in {
                            "curl",
                            "wget",
                            "nc",
                            "ssh",
                        }:
                            _fail("FORBIDDEN_NETWORK_SUBPROCESS", path, node.lineno)


def _absolutize_local_refs(value: Any, base_id: str) -> Any:
    """Rewrite base-schema local refs for the installed legacy resolver."""

    if isinstance(value, dict):
        return {
            key: (
                base_id + nested
                if key == "$ref" and isinstance(nested, str) and nested.startswith("#/")
                else _absolutize_local_refs(nested, base_id)
            )
            for key, nested in value.items()
        }
    if isinstance(value, list):
        return [_absolutize_local_refs(item, base_id) for item in value]
    return value


def _schema_refs(value: Any) -> tuple[str, ...]:
    """Collect every explicit schema reference without using comments."""

    refs: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            if key == "$ref" and isinstance(nested, str):
                refs.append(nested)
            refs.extend(_schema_refs(nested))
    elif isinstance(value, list):
        for nested in value:
            refs.extend(_schema_refs(nested))
    return tuple(refs)


def _check_json_and_schema() -> None:
    """Validate JSON, schema resolution, and positive runtime vectors."""

    policy = _load_json(POLICY_PATH)
    schema = _load_json(PROFILE_SCHEMA_PATH)
    fixtures = _load_json(FIXTURE_PATH)
    if not isinstance(policy, dict) or policy.get("status") != "CANDIDATE":
        _fail("POLICY_NOT_CANDIDATE", POLICY_PATH)
    required_policy = {
        "schema_version",
        "policy_version",
        "max_iterations",
        "allowed_source_modes",
        "stable_decisions",
        "hard_risk_codes",
        "sensitive_key_names",
        "candidate_only_sources",
        "commit_rule",
        "cycle_policy",
        "timeout_policy",
        "consensus_mode",
        "adi_mode",
        "rule_refs",
        "priority_policy_ref",
        "constraint_hypergraph_ref",
        "convergence_operator_ref",
        "dimension_refs",
        "constraint_refs",
    }
    if not required_policy.issubset(policy):
        _fail("POLICY_CONTRACT_INCOMPLETE", POLICY_PATH)
    if policy.get("consensus_mode") != "LOCAL_EQUIVALENCE_ONLY":
        _fail("CONSENSUS_BOUNDARY_INVALID", POLICY_PATH)
    if not isinstance(fixtures, dict) or fixtures.get("run_id") != RUN_ID:
        _fail("FIXTURE_CONTRACT_INVALID", FIXTURE_PATH)
    try:
        Draft202012Validator.check_schema(schema)
    except Exception:
        _fail("RUNTIME_SCHEMA_INVALID", PROFILE_SCHEMA_PATH)
    base = _load_json(BASE_GTE_SCHEMA_PATH)
    base_id = base.get("$id") if isinstance(base, dict) else None
    if not isinstance(base_id, str) or base_id not in _schema_refs(schema):
        _fail("BASE_GTE_SCHEMA_REFERENCE_MISSING", PROFILE_SCHEMA_PATH)
    try:
        resolvable_base = _absolutize_local_refs(base, base_id)
        resolver = RefResolver.from_schema(
            schema,
            store={base_id: resolvable_base},
        )
        validator = Draft202012Validator(schema, resolver=resolver)
        request = {
            "profile_schema_version": "8d-gte-runtime-candidate-profile/0.1",
            "profile_type": "RUNTIME_REQUEST",
            "gte": fixtures["gte_candidate"],
            "source_mode": "TOTAL_FIELD_PULL",
            "event": fixtures["event"],
            "rule_set_ref": fixtures["rule_set_ref"],
            "resolved_fields": fixtures["resolved_fields"],
            "context": fixtures["context"],
            "adi_requested": False,
        }
        if list(validator.iter_errors(request)):
            _fail("RUNTIME_REQUEST_VECTOR_INVALID", PROFILE_SCHEMA_PATH)
        from tools.total_field_candidate_gateway import total_field_pull

        result = total_field_pull(
            request,
            previous_state=fixtures["previous"],
            observation_domains=fixtures["observation_domains"],
        )
        if list(validator.iter_errors(result)):
            _fail("RUNTIME_RESULT_VECTOR_INVALID", PROFILE_SCHEMA_PATH)
        required_result_fields = tuple(schema["$defs"]["runtime_result"]["required"])
        result_properties = schema["$defs"]["runtime_result"]["properties"]
        if set(required_result_fields) != set(result_properties):
            _fail("RUNTIME_RESULT_REQUIRED_FIELDS_INCOMPLETE", PROFILE_SCHEMA_PATH)
        if schema["$defs"]["runtime_result"].get("minProperties") != len(
            result_properties
        ):
            _fail("RUNTIME_RESULT_MIN_PROPERTIES_WEAK", PROFILE_SCHEMA_PATH)
        for field_name in required_result_fields:
            invalid = dict(result)
            del invalid[field_name]
            if not list(validator.iter_errors(invalid)):
                _fail("RUNTIME_RESULT_REQUIRED_FIELD_WEAK", PROFILE_SCHEMA_PATH)
    except VerificationFailure:
        raise
    except Exception:
        _fail("RUNTIME_SCHEMA_VECTOR_CHECK_FAILED", PROFILE_SCHEMA_PATH)


def _check_semantics() -> None:
    """Require locked governance markers and reject definition drift."""

    core = _read("tools/tfct_true8d_runtime_candidate.py")
    gateway = _read("tools/total_field_candidate_gateway.py")
    small = _read("tools/w7tp_small_transport_agent_candidate.py")
    xiaoj = _read("tools/xiaoj_candidate_adapter.py")
    adi = _read("tools/adi_index_strategy_candidate.py")
    report = _read(REPORT_PATH)
    required = {
        "tools/tfct_true8d_runtime_candidate.py": (
            "transition_coordinate",
            "DECISION_SEVERITY",
            '"ALLOW": 0',
            '"HOLD": 1',
            '"BLOCK": 2',
            '"QUARANTINE": 3',
            "D7_NESTED_RAW_KEYS",
            '"previous": runtime.previous_state.to_dict()',
            '"proposed": runtime.proposed_state.to_dict()',
            '"current": runtime.current_state.to_dict()',
            '"committed": runtime.committed_state.to_dict()',
            "canonical_tfs_match",
            "QUARANTINE",
            "BLOCK",
            "HOLD",
            "ALLOW",
            "LOCAL_EQUIVALENCE_ONLY",
            "tfid:candidate:v0.1:",
        ),
        POLICY_PATH: (
            "CONVERGENCE_CYCLE_DETECTED",
            "CONVERGENCE_TIMEOUT",
            "HOLD_OBSERVATION_DOMAIN_NOT_CONFIGURED",
        ),
        "tools/total_field_candidate_gateway.py": (
            "TOTAL_FIELD_PULL",
            "LLM_PUSH",
            "receive_candidate",
            "Candidate Source",
            "_trusted_context_claim_path",
            '"adi_fixture"',
            '"adi_result"',
            '"test_only"',
            "_projection_validation",
        ),
        "tools/w7tp_small_transport_agent_candidate.py": (
            "MISSING_ASSET",
            "UNSUPPORTED_RULE",
            "UNSUPPORTED_RECONSTRUCTOR",
            "VERSION_MISMATCH",
            "RAW_CHANNEL_REQUIRED",
        ),
        "tools/xiaoj_candidate_adapter.py": (
            "persona_text",
            "governance_candidate",
            "XIAOJ_DIRECT_AUTHORITY_BLOCKED",
        ),
        "tools/adi_index_strategy_candidate.py": (
            "Absolute Distance Spiral Index",
            "HOLD_ADI_NOT_CONFIGURED",
            "ADI_NOT_REQUESTED",
            "TEST_ONLY",
        ),
        REPORT_PATH: (
            "D6 = Sovereign Privacy Field",
            "D7 = Generative Transmission & Resource Routing Field",
            "D8 = Red-Team Detour Alert & Quarantine Field",
            "CONSENSUS_MODE=LOCAL_EQUIVALENCE_ONLY",
            "DISTRIBUTED_CONSENSUS=OPEN_PROBLEM",
            "PATENT_CANDIDATE_REVIEW_REQUIRED=YES",
        ),
    }
    source_map = {
        "tools/tfct_true8d_runtime_candidate.py": core,
        POLICY_PATH: _read(POLICY_PATH),
        "tools/total_field_candidate_gateway.py": gateway,
        "tools/w7tp_small_transport_agent_candidate.py": small,
        "tools/xiaoj_candidate_adapter.py": xiaoj,
        "tools/adi_index_strategy_candidate.py": adi,
        REPORT_PATH: report,
    }
    for path, markers in required.items():
        for marker in markers:
            if marker not in source_map[path]:
                _fail("SEMANTIC_MARKER_MISSING", path)
    prohibited = (
        "生成式傳輸是檔案搬運",
        "generative transmission is file transfer",
        "ADI is the production algorithm",
        "D8 is a hash",
    )
    for path, text in source_map.items():
        for phrase in prohibited:
            if phrase.lower() in text.lower():
                _fail("TECHNICAL_DEFINITION_DRIFT", path)
    if "proposed if commit_applied else previous" not in core and "proposed if should_commit else previous" not in core:
        _fail("ALLOW_ONLY_COMMIT_MARKER_MISSING", "tools/tfct_true8d_runtime_candidate.py")


def _check_no_sensitive_literals() -> None:
    """Scan only new deliverables for credential-shaped literals."""

    secret_patterns = (
        re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        re.compile(
            r"(?i)(?:api[_-]?key|password|raw[_-]?token|client[_-]?secret)\s*[=:]\s*['\"]?[A-Za-z0-9._-]{16,}"
        ),
    )
    for path in NEW_FILES:
        text = _read(path)
        for pattern in secret_patterns:
            match = pattern.search(text)
            if match:
                _fail("RAW_SECRET_LITERAL_DETECTED", path, text[: match.start()].count("\n") + 1)


def _check_protected_files() -> None:
    """Compare tracked and untracked protected paths with exact reporting."""

    for path in HEAD_PROTECTED:
        result = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", path],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            _fail("HEAD_PROTECTED_FILE_CHANGED", path)
    status = subprocess.run(
        [
            "git",
            "status",
            "--porcelain",
            "--untracked-files=no",
            "--",
            "runtime/total_field/active",
            "tensor_8d",
            "tensor_8d_boot.py",
        ],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if status.returncode != 0:
        _fail("PROTECTED_STATUS_CHECK_FAILED", "runtime/total_field/active")
    if status.stdout.strip():
        changed = status.stdout.splitlines()[0][3:].strip()
        _fail("PROTECTED_WORKTREE_PATH_CHANGED", changed)
    for path, expected in BASELINE_SHA256.items():
        if _sha256(path) != expected:
            _fail("BASELINE_PROTECTED_FILE_CHANGED", path)


def _run_focused_test() -> None:
    """Run exactly the new focused test and reject skips or count drift."""

    result = subprocess.run(
        [sys.executable, str(ROOT / TEST_PATH)],
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
                file_name = TEST_PATH
            _fail("FOCUSED_TEST_FAILED", file_name, int(line_text))
        _fail("FOCUSED_TEST_FAILED", TEST_PATH)
    if "Ran 45 tests" not in result.stdout or "OK" not in result.stdout:
        _fail("FOCUSED_TEST_COUNT_MISMATCH", TEST_PATH)
    if re.search(r"\bskipped\b|expected failures|unexpected successes", result.stdout):
        _fail("FOCUSED_TEST_NOT_STRICT_PASS", TEST_PATH)


def verify() -> None:
    """Run only the approved focused checks."""

    _check_presence_and_compile()
    _check_python_ast()
    _check_json_and_schema()
    _check_semantics()
    _check_no_sensitive_literals()
    _check_protected_files()
    _run_focused_test()


def main() -> int:
    """Print one stable state without a traceback."""

    try:
        verify()
    except VerificationFailure as failure:
        print("STATE=HOLD_VERIFY_TFCT_TRUE8D_RUNTIME_CANDIDATE")
        print(f"REASON_CODE={failure.reason_code}")
        print(f"FILE={failure.file}")
        print(f"LINE={failure.line}")
        return 1
    except Exception:
        print("STATE=HOLD_VERIFY_TFCT_TRUE8D_RUNTIME_CANDIDATE")
        print("REASON_CODE=UNEXPECTED_VERIFIER_FAILURE")
        print("FILE=scripts/verify/verify_tfct_true8d_runtime_candidate.py")
        print("LINE=1")
        return 1
    print("STATE=PASS_VERIFY_TFCT_TRUE8D_RUNTIME_CANDIDATE")
    print(f"RUN_ID={RUN_ID}")
    print("TEST_COUNT=45")
    print("CONSENSUS_MODE=LOCAL_EQUIVALENCE_ONLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
