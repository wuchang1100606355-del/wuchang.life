#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify the immutable W7TP small-agent v0.1.1 runtime entrypoint patch."""

from __future__ import annotations

import ast
import hashlib
import json
import math
import os
from pathlib import Path
import py_compile
import subprocess
import sys
from typing import Any, NoReturn


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

RUN_ID = "W7TP_SMALL_AGENT_RUNTIME_ENTRYPOINT_PATCH_V0_1_1"
RELEASE_VERSION = "v0.1.1-d27230aba7a4"
RELEASE_SHA256 = "9c836304a49c10a9443264000784010804535789c916d1ae9d6c8c11443f06b6"
OLD_RELEASE_SHA256 = "5d7f220b1716d0d496cd016c962b295b96654faff0fccb96e7c6eadee2cddc2a"
OLD_RELEASE_TREE_SHA256 = (
    "2f5a47fbee773d70c94dc4f90f64c040866639f29b43eedf5c2cd57c9c2a1312"
)
POLICY_SHA256 = "d27230aba7a4ecd051f4169184c1fa5357ce5efa1d62019238d68991b0140960"
REGISTRY_SHA256 = "aa2dd18f0a14152feeebd5562126b08808cd41ef2d8f9de56ddae8b3f84c1304"
SECURITY_RELEASE_VERSION = "v0.1.3-d27230aba7a4"
SECURITY_RELEASE_SHA256 = "1c87fcddf3ca65045a1dace9efa8fa98e04aba489798c414b35ef1982c1d6052"

RELEASE = Path("manifests/w7tp_small_agent_release_v0_1_1_d27230aba7a4")
SECURITY_RELEASE = Path("manifests/w7tp_small_agent_release_v0_1_3_d27230aba7a4")
OLD_RELEASE = Path("manifests/w7tp_small_agent_release_v0_1_d27230aba7a4")
REGISTRY = Path(
    "manifests/w7tp_small_agent_node_authority_v0_1/node_authority_registry.json"
)
ENTRYPOINT = RELEASE / "bin/w7tp-small-agent"
TEST = Path("tests/test_w7tp_small_agent_runtime_entrypoint.py")

PYTHON_FILES = (
    Path("tools/w7tp_small_agent_cli.py"),
    Path("tools/w7tp_small_agent_service_runner.py"),
    Path("tools/w7tp_small_agent_healthcheck.py"),
    Path("tools/build_w7tp_small_agent_release.py"),
    Path("tools/deploy_w7tp_small_agent_all_nodes.py"),
    TEST,
    Path("scripts/verify/verify_w7tp_small_agent_runtime_entrypoint.py"),
)

PROTECTED_SHA256 = {
    Path("runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_CANONICAL.json"):
        "5ec55fec22504aa719803f398c8b408a785c145870bf4cd34434cad242ab9237",
    Path("runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_POINTER.txt"):
        "0ee90811b6f9f4ebbf798369fa32eeb3950b1c03117490f9d7c4cdc3a5d1c4fa",
    Path("runtime/total_field/active/ACTIVE_TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL.json"):
        "a3cf7ead429291afcc2fb7810877a04a9c57f7a10ccd102e5b46fedfeef01176",
    Path("runtime/total_field/active/ACTIVE_TFCT_TRUE8D_RUNTIME_POLICY_POINTER.txt"):
        "5e7367cde1b051cfb8ed71614114db1ee8b8c2ff60f08dacb3c2adbd43a037ad",
    Path("tools/d3_coordinate_transition_candidate.py"):
        "b1e67f1d22d0e53785f3939885dcb690907cb68071f7f3a682ce368a356bb918",
    Path("tools/w7tp_packet_inference_runtime.py"):
        "7918b485b83d1523c98636366c3bd41aaf3b514b0a1b35b4b1ffad066bc1205b",
}


class VerificationFailure(Exception):
    """One stable, non-sensitive verifier failure."""

    def __init__(self, reason_code: str, path: Path | str) -> None:
        self.reason_code = reason_code
        self.path = Path(path).as_posix()
        super().__init__(reason_code)


def _fail(reason_code: str, path: Path | str) -> NoReturn:
    raise VerificationFailure(reason_code, path)


def _raw_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        _fail("FILE_READ_FAILED", path)


def _canonical_json(value: Any) -> str:
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
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("DUPLICATE_JSON_MEMBER", "<json>")
        result[key] = value
    return result


def _reject_constant(_token: str) -> NoReturn:
    _fail("NON_FINITE_JSON_NUMBER", "<json>")


def _ensure_finite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        _fail("NON_FINITE_JSON_NUMBER", "<json>")
    if isinstance(value, dict):
        for key, nested in value.items():
            if not isinstance(key, str):
                _fail("NON_STRING_JSON_MEMBER", "<json>")
            _ensure_finite(nested)
    elif isinstance(value, list):
        for nested in value:
            _ensure_finite(nested)


def _load_json(path: Path) -> Any:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_pairs,
            parse_constant=_reject_constant,
        )
    except VerificationFailure:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError):
        _fail("JSON_READ_FAILED", path)
    _ensure_finite(value)
    return value


def _inventory(directory: Path) -> set[str]:
    """Inventory only one named release tree, rejecting links/special files."""

    if not directory.is_dir() or directory.is_symlink():
        _fail("RELEASE_DIRECTORY_INVALID", directory)
    result: set[str] = set()
    pending = [directory]
    while pending:
        current = pending.pop()
        try:
            entries = sorted(current.iterdir(), key=lambda item: item.name)
        except OSError:
            _fail("RELEASE_INVENTORY_FAILED", current)
        for entry in entries:
            relative = entry.relative_to(directory).as_posix()
            if entry.is_symlink():
                _fail("RELEASE_LINK_FORBIDDEN", entry)
            if entry.is_dir():
                pending.append(entry)
            elif entry.is_file():
                result.add(relative)
            else:
                _fail("RELEASE_SPECIAL_FILE_FORBIDDEN", entry)
    return result


def _tree_sha256(directory: Path) -> str:
    """Hash one named release tree using the deployer's bounded tree contract."""

    digest = hashlib.sha256()
    for relative in sorted(_inventory(directory)):
        relative_bytes = relative.encode("utf-8")
        content = (directory / relative).read_bytes()
        digest.update(len(relative_bytes).to_bytes(8, "big"))
        digest.update(relative_bytes)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _check_release_internal(directory: Path, expected_version: str, expected_hash: str) -> None:
    manifest = _load_json(directory / "release_manifest.json")
    files_document = _load_json(directory / "files_sha256.json")
    if not isinstance(manifest, dict) or not isinstance(files_document, dict):
        _fail("RELEASE_MANIFEST_SHAPE_INVALID", directory)
    if manifest.get("release_version") != expected_version:
        _fail("RELEASE_VERSION_MISMATCH", directory)
    if manifest.get("release_sha256") != expected_hash:
        _fail("RELEASE_SHA256_MISMATCH", directory)
    identity = manifest.get("release_identity")
    if not isinstance(identity, dict) or _canonical_sha256(identity) != expected_hash:
        _fail("RELEASE_IDENTITY_INVALID", directory)
    files = files_document.get("files")
    if not isinstance(files, dict) or not files:
        _fail("RELEASE_FILES_MANIFEST_INVALID", directory)
    expected_inventory = set(files) | {"files_sha256.json", "release_manifest.json"}
    identity_refs = {
        "capability_manifest_template_ref": "capability_manifest_template_sha256",
        "install_manifest_ref": "install_manifest_sha256",
        "rollback_manifest_ref": "rollback_manifest_sha256",
    }
    for reference_key, identity_hash_key in identity_refs.items():
        reference = manifest.get(reference_key)
        expected_reference_hash = identity.get(identity_hash_key)
        if not isinstance(reference, str) or not isinstance(expected_reference_hash, str):
            _fail("RELEASE_IDENTITY_REFERENCE_INVALID", directory)
        expected_inventory.add(reference)
        if reference in files:
            actual_reference_hash = _raw_sha256(directory / reference)
        else:
            actual_reference_hash = _canonical_sha256(_load_json(directory / reference))
        if actual_reference_hash != expected_reference_hash:
            _fail("RELEASE_IDENTITY_REFERENCE_HASH_MISMATCH", directory / reference)
    if _inventory(directory) != expected_inventory:
        _fail("RELEASE_INVENTORY_MISMATCH", directory)
    for relative, expected_file_hash in sorted(files.items()):
        if not isinstance(relative, str) or not isinstance(expected_file_hash, str):
            _fail("RELEASE_FILES_MANIFEST_INVALID", directory)
        if _raw_sha256(directory / relative) != expected_file_hash:
            _fail("RELEASE_FILE_HASH_MISMATCH", directory / relative)
    if identity.get("files_sha256") != files:
        _fail("RELEASE_IDENTITY_FILE_MAP_MISMATCH", directory)
    files_document_hash = _canonical_sha256(files_document)
    if manifest.get("files_sha256_hash") != files_document_hash:
        _fail("RELEASE_FILES_DOCUMENT_HASH_MISMATCH", directory)
    if "files_sha256_hash" in identity and identity["files_sha256_hash"] != files_document_hash:
        _fail("RELEASE_IDENTITY_FILES_DOCUMENT_HASH_MISMATCH", directory)


def _run_entrypoint(command: str) -> list[str]:
    environment = {
        "HOME": "/nonexistent",
        "PATH": "/usr/bin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    try:
        completed = subprocess.run(
            [str((ROOT / ENTRYPOINT).resolve()), command],
            cwd="/",
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        _fail("ENTRYPOINT_EXECUTION_FAILED", ENTRYPOINT)
    if completed.returncode != 0 or completed.stderr:
        _fail(f"ENTRYPOINT_{command.upper().replace('-', '_')}_FAILED", ENTRYPOINT)
    return completed.stdout.rstrip("\n").splitlines()


def _check_entrypoint() -> None:
    entrypoint = ROOT / ENTRYPOINT
    if not entrypoint.is_file() or entrypoint.is_symlink():
        _fail("ENTRYPOINT_MISSING", ENTRYPOINT)
    try:
        mode = entrypoint.stat().st_mode
    except OSError:
        _fail("ENTRYPOINT_STAT_FAILED", ENTRYPOINT)
    if mode & 0o111 == 0:
        _fail("ENTRYPOINT_NOT_EXECUTABLE", ENTRYPOINT)
    if not entrypoint.read_bytes().startswith(b"#!/usr/bin/env python3\n"):
        _fail("ENTRYPOINT_SHEBANG_INVALID", ENTRYPOINT)

    version = _run_entrypoint("version")
    expected_version = [
        "agent_name=w7tp-small-agent",
        f"agent_version={RELEASE_VERSION}",
        f"release_sha256={RELEASE_SHA256}",
        f"policy_sha256={POLICY_SHA256}",
        "schema_version=w7tp-small-agent-cli/v0.1.1",
    ]
    if version != expected_version:
        _fail("ENTRYPOINT_VERSION_OUTPUT_INVALID", ENTRYPOINT)

    expected_states = {
        "health": "STATE=PASS_W7TP_SMALL_AGENT_HEALTH",
        "self-test": "STATE=PASS_W7TP_SMALL_AGENT_SELF_TEST",
    }
    for command, state in expected_states.items():
        lines = _run_entrypoint(command)
        if len(lines) != 2 or lines[0] != state:
            _fail(f"ENTRYPOINT_{command.upper().replace('-', '_')}_OUTPUT_INVALID", ENTRYPOINT)
        try:
            evidence = json.loads(
                lines[1],
                object_pairs_hook=_strict_pairs,
                parse_constant=_reject_constant,
            )
        except (json.JSONDecodeError, UnicodeError):
            _fail("ENTRYPOINT_EVIDENCE_JSON_INVALID", ENTRYPOINT)
        _ensure_finite(evidence)
        if lines[1] != _canonical_json(evidence):
            _fail("ENTRYPOINT_EVIDENCE_NOT_CANONICAL", ENTRYPOINT)
        if not isinstance(evidence, dict) or evidence.get("status") != "PASS":
            _fail("ENTRYPOINT_EVIDENCE_STATUS_INVALID", ENTRYPOINT)
        if evidence.get("release_sha256") != RELEASE_SHA256:
            _fail("ENTRYPOINT_EVIDENCE_RELEASE_MISMATCH", ENTRYPOINT)
        if evidence.get("policy_sha256") != POLICY_SHA256:
            _fail("ENTRYPOINT_EVIDENCE_POLICY_MISMATCH", ENTRYPOINT)
        checks = evidence.get("checks")
        if not isinstance(checks, dict):
            _fail("ENTRYPOINT_EVIDENCE_CHECKS_INVALID", ENTRYPOINT)
        if command == "self-test":
            required = {
                "d1_projection": "PASS",
                "candidate_replay": "PASS",
                "total_field_pull": "PASS",
                "llm_push": "PASS",
                "common_receive_path": "PASS",
                "allow_only_commit": "PASS",
                "llm_direct_commit": "BLOCKED",
                "persona_governance_separation": "PASS",
                "raw_secret_scan": "PASS",
            }
            if any(checks.get(key) != value for key, value in required.items()):
                _fail("ENTRYPOINT_SELF_TEST_SEMANTICS_INVALID", ENTRYPOINT)


def _check_sources() -> None:
    for relative in PYTHON_FILES:
        path = ROOT / relative
        if not path.is_file():
            _fail("PYTHON_FILE_MISSING", relative)
        try:
            py_compile.compile(str(path), doraise=True)
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(relative))
        except (OSError, UnicodeError, SyntaxError, py_compile.PyCompileError):
            _fail("PYTHON_COMPILE_FAILED", relative)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in {"eval", "exec"}:
                    _fail("DYNAMIC_CODE_EXECUTION_FORBIDDEN", relative)
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [item.name for item in node.names]
                if any(name == "pickle" or name.startswith("pickle.") for name in names):
                    _fail("PICKLE_FORBIDDEN", relative)
        text = path.read_text(encoding="utf-8")
        if ("TO" + "DO") in text or ("FIX" + "ME") in text:
            _fail("SOURCE_PLACEHOLDER_FORBIDDEN", relative)

    test_tree = ast.parse((ROOT / TEST).read_text(encoding="utf-8"), filename=str(TEST))
    test_names = [
        node.name
        for node in ast.walk(test_tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]
    if len(test_names) != 30 or len(set(test_names)) != 30:
        _fail("FOCUSED_TEST_COUNT_NOT_30", TEST)


def _check_release_safety() -> None:
    """Reject dynamic identity inputs and recognizable raw credential material."""

    release_root = ROOT / RELEASE
    manifest = _load_json(release_root / "release_manifest.json")
    if not isinstance(manifest, dict) or not isinstance(
        manifest.get("release_identity"), dict
    ):
        _fail("RELEASE_IDENTITY_INVALID", RELEASE)
    dynamic_identity_keys = {
        "build_time",
        "created_at",
        "datetime",
        "now",
        "pid",
        "process_id",
        "random",
        "timestamp",
        "uuid",
    }
    if any(
        str(key).casefold() in dynamic_identity_keys
        for key in manifest["release_identity"]
    ):
        _fail("NONDETERMINISTIC_RELEASE_IDENTITY", RELEASE / "release_manifest.json")

    private_key_marker = b"-----" + b"BEGIN " + b"PRIVATE KEY-----"
    raw_secret_markers = (
        private_key_marker,
        b"sk-" + b"proj-",
        b"ghp" + b"_",
        b"xoxb" + b"-",
    )
    repository_path = str(ROOT).encode("utf-8")
    for relative in sorted(_inventory(release_root)):
        content = (release_root / relative).read_bytes()
        if repository_path in content or b"/tmp/" in content:
            _fail("BUILD_PATH_LEAK", RELEASE / relative)
        if any(marker in content for marker in raw_secret_markers):
            _fail("RAW_SECRET_MATERIAL_FOUND", RELEASE / relative)

    for relative in sorted(_inventory(release_root)):
        if not relative.endswith(".py") and relative != "bin/w7tp-small-agent":
            continue
        try:
            tree = ast.parse(
                (release_root / relative).read_text(encoding="utf-8"),
                filename=relative,
            )
        except (OSError, UnicodeError, SyntaxError):
            _fail("PACKAGED_PYTHON_PARSE_FAILED", RELEASE / relative)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {item.name.split(".", 1)[0] for item in node.names}
            elif isinstance(node, ast.ImportFrom):
                names = {(node.module or "").split(".", 1)[0]}
            else:
                names = set()
            if names & {"pickle", "random", "secrets", "uuid"}:
                _fail("NONDETERMINISTIC_OR_UNSAFE_IMPORT", RELEASE / relative)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in {"eval", "exec"}:
                    _fail("DYNAMIC_CODE_EXECUTION_FORBIDDEN", RELEASE / relative)


def _check_protected() -> None:
    if _raw_sha256(ROOT / REGISTRY) != REGISTRY_SHA256:
        _fail("AUTHORITY_REGISTRY_CHANGED", REGISTRY)
    for relative, expected in PROTECTED_SHA256.items():
        if _raw_sha256(ROOT / relative) != expected:
            _fail("PROTECTED_FILE_CHANGED", relative)


def _run_focused_test() -> None:
    try:
        completed = subprocess.run(
            [sys.executable, str(ROOT / TEST)],
            cwd=str(ROOT),
            env={
                "HOME": os.environ.get("HOME", "/nonexistent"),
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "PYTHONDONTWRITEBYTECODE": "1",
            },
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        _fail("FOCUSED_TEST_EXECUTION_FAILED", TEST)
    if completed.returncode != 0 or "Ran 30 tests" not in completed.stdout:
        _fail("FOCUSED_TEST_FAILED", TEST)


def verify() -> None:
    """Run the bounded local-only entrypoint verification."""

    from tools.build_w7tp_small_agent_release import (
        verify_security_runtime_patch_release,
    )

    _check_sources()
    _check_protected()
    _check_release_safety()
    _check_release_internal(
        ROOT / OLD_RELEASE,
        "v0.1-d27230aba7a4",
        OLD_RELEASE_SHA256,
    )
    if _tree_sha256(ROOT / OLD_RELEASE) != OLD_RELEASE_TREE_SHA256:
        _fail("OLD_RELEASE_TREE_CHANGED", OLD_RELEASE)
    _check_release_internal(ROOT / RELEASE, RELEASE_VERSION, RELEASE_SHA256)
    _check_release_internal(
        ROOT / SECURITY_RELEASE,
        SECURITY_RELEASE_VERSION,
        SECURITY_RELEASE_SHA256,
    )
    try:
        result = verify_security_runtime_patch_release(ROOT, ROOT / SECURITY_RELEASE)
    except Exception:
        _fail("SECURITY_PATCH_SOURCE_VERIFICATION_FAILED", SECURITY_RELEASE)
    if result.release_sha256 != SECURITY_RELEASE_SHA256:
        _fail("SECURITY_PATCH_SOURCE_HASH_MISMATCH", SECURITY_RELEASE)
    _check_entrypoint()
    _run_focused_test()


def main() -> int:
    try:
        verify()
    except VerificationFailure as error:
        print("STATE=HOLD_VERIFY_W7TP_SMALL_AGENT_RUNTIME_ENTRYPOINT")
        print(f"REASON_CODE={error.reason_code}")
        print(f"FILE={error.path}")
        return 1
    print("STATE=PASS_VERIFY_W7TP_SMALL_AGENT_RUNTIME_ENTRYPOINT")
    print(f"RUN_ID={RUN_ID}")
    print(f"RELEASE_VERSION={RELEASE_VERSION}")
    print(f"RELEASE_SHA256={RELEASE_SHA256}")
    print(f"SECURITY_RELEASE_VERSION={SECURITY_RELEASE_VERSION}")
    print(f"SECURITY_RELEASE_SHA256={SECURITY_RELEASE_SHA256}")
    print(f"POLICY_SHA256={POLICY_SHA256}")
    print("TEST_COUNT=30")
    print("OLD_RELEASE_UNCHANGED=YES")
    print("AUTHORITY_REGISTRY_VALIDATED=YES")
    print("RAW_SECRET_SCAN=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
