#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify the scoped node-authority registry and deployment overlay locally."""

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
from typing import Any, NoReturn

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

RUN_ID = "W7TP_SMALL_AGENT_ALL_NODE_DEPLOYMENT_V0_1_D27230ABA7A4"
REGISTRY = Path(
    "manifests/w7tp_small_agent_node_authority_v0_1/"
    "node_authority_registry.json"
)
SCHEMA = Path("schemas/w7tp_small_agent_node_authority_registry_candidate.schema.json")
MAPPING_REPORT = Path(
    "docs/total_field/W7TP_REMOTE_PLATFORM_ROLE_MAPPING_CANDIDATE_REPORT.md"
)
DEPLOYER = Path("tools/deploy_w7tp_small_agent_all_nodes.py")
TEST = Path("tests/test_w7tp_small_agent_node_authority.py")
ACTIVE = Path(
    "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_CANONICAL.json"
)
POINTER = Path(
    "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_POINTER.txt"
)
POLICY_ACTIVE = Path(
    "runtime/total_field/active/ACTIVE_TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL.json"
)
POLICY_POINTER = Path(
    "runtime/total_field/active/ACTIVE_TFCT_TRUE8D_RUNTIME_POLICY_POINTER.txt"
)
RELEASE = Path("manifests/w7tp_small_agent_release_v0_1_d27230aba7a4")
RELEASE_VERSION = "v0.1-d27230aba7a4"
RELEASE_SHA256 = "5d7f220b1716d0d496cd016c962b295b96654faff0fccb96e7c6eadee2cddc2a"
POLICY_SHA256 = "d27230aba7a4ecd051f4169184c1fa5357ce5efa1d62019238d68991b0140960"
OWNER_SCOPE = "W7TP_SMALL_AGENT_INSTALL_V0_1_ONLY"
FORMAL_NODE_IDS = (
    "taiji01",
    "MSI",
    "penguin",
    "localhost",
    "DESKTOP-OHE05SC",
    "wuchang-us-free-node",
    "V3_MIX_EDLA_GL",
    "RT-BE86U-7428",
)
EXPECTED_KINDS = {
    "taiji01": "linux",
    "MSI": "windows",
    "penguin": "linux",
    "localhost": "iOS",
    "DESKTOP-OHE05SC": "linux",
    "wuchang-us-free-node": "linux",
    "V3_MIX_EDLA_GL": "android",
    "RT-BE86U-7428": "ASUSWRT-Merlin router",
}
REGISTRY_KEYS = frozenset(
    {
        "schema_version",
        "run_id",
        "owner_confirmation",
        "owner_authority_grant",
        "owner_authority_scope",
        "canonical_source",
        "candidate_schema_ref",
        "formal_node_ids",
        "not_in_active_canonical",
        "remote_platform_role_mappings",
        "nodes",
    }
)
NODE_KEYS = frozenset(
    {
        "node_id",
        "canonical_source",
        "kind",
        "hostname",
        "address",
        "authority",
        "authority_scope",
        "observation_domain",
        "connection_method",
        "deployment_eligibility",
        "evidence_refs",
        "alias_of",
        "reason_code",
    }
)
NODE_OPTIONAL_KEYS = frozenset({"ssh_user"})
PROTECTED = {
    ACTIVE: "5ec55fec22504aa719803f398c8b408a785c145870bf4cd34434cad242ab9237",
    POINTER: "0ee90811b6f9f4ebbf798369fa32eeb3950b1c03117490f9d7c4cdc3a5d1c4fa",
    POLICY_ACTIVE: "a3cf7ead429291afcc2fb7810877a04a9c57f7a10ccd102e5b46fedfeef01176",
    POLICY_POINTER: "5e7367cde1b051cfb8ed71614114db1ee8b8c2ff60f08dacb3c2adbd43a037ad",
}


class VerificationFailure(Exception):
    """Stable verifier failure without caller data."""

    def __init__(self, reason_code: str, file: Path | str) -> None:
        self.reason_code = reason_code
        self.file = Path(file).as_posix()
        super().__init__(reason_code)


def _fail(reason_code: str, file: Path | str) -> NoReturn:
    raise VerificationFailure(reason_code, file)


def _raw_sha256(relative: Path) -> str:
    try:
        return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    except OSError:
        _fail("FILE_READ_FAILED", relative)


def _canonical_sha256(value: Any) -> str:
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        _fail("CANONICAL_JSON_FAILED", REGISTRY)
    return hashlib.sha256(encoded).hexdigest()


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("DUPLICATE_JSON_MEMBER", REGISTRY)
        result[key] = value
    return result


def _reject_constant(_token: str) -> NoReturn:
    _fail("NON_FINITE_JSON_NUMBER", REGISTRY)


def _ensure_finite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        _fail("NON_FINITE_JSON_NUMBER", REGISTRY)
    if isinstance(value, dict):
        for nested in value.values():
            _ensure_finite(nested)
    elif isinstance(value, list):
        for nested in value:
            _ensure_finite(nested)


def _load_json(relative: Path) -> Any:
    try:
        text = (ROOT / relative).read_text(encoding="utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_strict_pairs,
            parse_constant=_reject_constant,
        )
    except VerificationFailure:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError):
        _fail("JSON_READ_FAILED", relative)
    _ensure_finite(value)
    return value


def _check_protected() -> None:
    for path, expected in PROTECTED.items():
        if _raw_sha256(path) != expected:
            _fail("PROTECTED_FILE_CHANGED", path)


def _check_registry() -> dict[str, Any]:
    registry = _load_json(REGISTRY)
    schema = _load_json(SCHEMA)
    active = _load_json(ACTIVE)
    if not isinstance(schema, dict):
        _fail("AUTHORITY_CANDIDATE_SCHEMA_INVALID", SCHEMA)
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(registry)
    except (SchemaError, ValidationError):
        _fail("AUTHORITY_CANDIDATE_SCHEMA_VALIDATION_FAILED", SCHEMA)
    if not isinstance(registry, dict) or frozenset(registry) != REGISTRY_KEYS:
        _fail("AUTHORITY_REGISTRY_SHAPE_INVALID", REGISTRY)
    fixed = {
        "schema_version": "w7tp.small-agent.node-authority-registry/v0.1",
        "run_id": RUN_ID,
        "owner_confirmation": "YES",
        "owner_authority_grant": "FORMAL_NON_ROUTER_NODES_W7TP_SMALL_AGENT_INSTALL_ONLY",
        "owner_authority_scope": OWNER_SCOPE,
        "canonical_source": ACTIVE.as_posix(),
    }
    if any(registry.get(key) != value for key, value in fixed.items()):
        _fail("AUTHORITY_REGISTRY_IDENTITY_INVALID", REGISTRY)
    if registry.get("formal_node_ids") != list(FORMAL_NODE_IDS):
        _fail("FORMAL_NODE_LIST_MISMATCH", REGISTRY)
    if not isinstance(active, dict) or [
        item.get("node_id") for item in active.get("nodes", []) if isinstance(item, dict)
    ] != list(FORMAL_NODE_IDS):
        _fail("ACTIVE_FORMAL_NODE_LIST_MISMATCH", ACTIVE)
    excluded = registry.get("not_in_active_canonical")
    if excluded != [
        {"subject": "taiji03", "reason_code": "NOT_IN_ACTIVE_CANONICAL"},
        {"subject": "drallion", "reason_code": "NOT_IN_ACTIVE_CANONICAL"},
    ]:
        _fail("NON_ACTIVE_RECORD_MISMATCH", REGISTRY)
    mappings = registry.get("remote_platform_role_mappings")
    if not isinstance(mappings, list) or len(mappings) != 2:
        _fail("REMOTE_PLATFORM_MAPPING_COUNT_INVALID", REGISTRY)
    mapping_by_id = {
        item.get("node_id"): item for item in mappings if isinstance(item, dict)
    }
    if set(mapping_by_id) != {"V3_MIX_EDLA_GL", "drallion"}:
        _fail("REMOTE_PLATFORM_MAPPING_NODE_SET_INVALID", REGISTRY)
    v3_mapping = mapping_by_id["V3_MIX_EDLA_GL"]
    expected_v3 = {
        "node_role": "SUNMI_POS",
        "platform": "ANDROID_13",
        "voice_capabilities": ["GOOGLE_COMMERCIAL_VOICE_AUTHORIZED"],
        "containerization": "SUPPORTED",
        "container_transport": (
            "ANDROID_COMPATIBLE_CONTAINER_OR_EXISTING_FORMAL_APPLICATION_ONLY"
        ),
        "mapping_source": "OWNER_CONFIRMED",
        "deployment_eligibility": False,
        "hold_reason": "HOLD_NODE_OFFLINE",
    }
    if any(v3_mapping.get(key) != value for key, value in expected_v3.items()):
        _fail("V3_PLATFORM_ROLE_MAPPING_INVALID", REGISTRY)
    drallion_mapping = mapping_by_id["drallion"]
    expected_drallion = {
        "node_role": "CHROMEOS_NODE",
        "platform": "CHROMEOS",
        "platform_variant": "ANDROID_ARC_CLIENT_VISIBLE_TO_TAILSCALE",
        "container_transport": "CHROMEOS_CROSTINI_OR_EXISTING_CONTAINER_ONLY",
        "formal_status": "NONFORMAL_MAPPING",
        "mapping_source": "OWNER_CONFIRMED",
        "deployment_eligibility": False,
        "hold_reason": "HOLD_NODE_OFFLINE",
    }
    if any(
        drallion_mapping.get(key) != value
        for key, value in expected_drallion.items()
    ):
        _fail("DRALLION_PLATFORM_ROLE_MAPPING_INVALID", REGISTRY)
    if "drallion" in registry.get("formal_node_ids", []) or any(
        isinstance(item, dict) and item.get("node_id") == "drallion"
        for item in registry.get("nodes", [])
    ):
        _fail("DRALLION_FORMAL_PROMOTION_FORBIDDEN", REGISTRY)
    if "taiji01" in mapping_by_id:
        _fail("TAIJI01_REMOTE_MAPPING_WRITE_FORBIDDEN", REGISTRY)
    nodes = registry.get("nodes")
    if not isinstance(nodes, list) or len(nodes) != len(FORMAL_NODE_IDS):
        _fail("AUTHORITY_NODE_COUNT_MISMATCH", REGISTRY)
    by_id: dict[str, dict[str, Any]] = {}
    for item in nodes:
        if (
            not isinstance(item, dict)
            or not NODE_KEYS.issubset(item)
            or not frozenset(item).issubset(NODE_KEYS | NODE_OPTIONAL_KEYS)
        ):
            _fail("AUTHORITY_NODE_SHAPE_INVALID", REGISTRY)
        node_id = item.get("node_id")
        if node_id not in FORMAL_NODE_IDS or node_id in by_id:
            _fail("AUTHORITY_NODE_SET_INVALID", REGISTRY)
        if item.get("kind") != EXPECTED_KINDS[node_id]:
            _fail("AUTHORITY_NODE_KIND_MISMATCH", REGISTRY)
        if item.get("canonical_source") != f"{ACTIVE.as_posix()}#node={node_id}":
            _fail("AUTHORITY_CANONICAL_SOURCE_INVALID", REGISTRY)
        if item.get("authority") != "OWNER_AUTHORIZED" or item.get("authority_scope") != OWNER_SCOPE:
            _fail("OWNER_AUTHORITY_SCOPE_INVALID", REGISTRY)
        if not isinstance(item.get("observation_domain"), str) or not item["observation_domain"]:
            _fail("OBSERVATION_DOMAIN_INVALID", REGISTRY)
        evidence = item.get("evidence_refs")
        if not isinstance(evidence, list) or not evidence or any(
            not isinstance(ref, str) or not ref for ref in evidence
        ) or len(evidence) != len(set(evidence)):
            _fail("AUTHORITY_EVIDENCE_INVALID", REGISTRY)
        if not isinstance(item.get("deployment_eligibility"), bool):
            _fail("DEPLOYMENT_ELIGIBILITY_INVALID", REGISTRY)
        by_id[node_id] = item
    if tuple(by_id) != FORMAL_NODE_IDS:
        _fail("AUTHORITY_NODE_ORDER_INVALID", REGISTRY)
    eligible = [node_id for node_id, item in by_id.items() if item["deployment_eligibility"]]
    if eligible != ["taiji01", "penguin"]:
        _fail("ELIGIBLE_NODE_SET_INVALID", REGISTRY)
    local = by_id["taiji01"]
    if (
        local.get("hostname") != "taiji01"
        or local.get("address") != "taiji01"
        or local.get("connection_method") != "LOCAL_SHELL"
        or local.get("alias_of") is not None
        or "local-command:hostname:exact=taiji01" not in local["evidence_refs"]
        or "local-command:hostnamectl-static:exact=taiji01" not in local["evidence_refs"]
    ):
        _fail("LOCAL_IDENTITY_EVIDENCE_INVALID", REGISTRY)
    ssh = by_id["penguin"]
    if (
        ssh.get("address") != "100.111.139.7"
        or ssh.get("connection_method") != "SSH"
        or ssh.get("ssh_user") != "taiji_02"
        or not any("tailscale-status-json" in ref and "online=true" in ref for ref in ssh["evidence_refs"])
        or not any("ssh-G" in ref and "parsed=true" in ref for ref in ssh["evidence_refs"])
    ):
        _fail("SSH_EVIDENCE_INVALID", REGISTRY)
    if any("ssh_user" in item for node_id, item in by_id.items() if node_id != "penguin"):
        _fail("SSH_USER_SCOPE_INVALID", REGISTRY)
    router = by_id["RT-BE86U-7428"]
    if router.get("deployment_eligibility") is not False or router.get("reason_code") != "HOLD_ROUTER_WRITE_NOT_AUTHORIZED":
        _fail("ROUTER_WRITE_BOUNDARY_INVALID", REGISTRY)
    for node_id, item in by_id.items():
        alias = item.get("alias_of")
        if alias is not None:
            if alias not in by_id or alias == node_id or item["deployment_eligibility"]:
                _fail("ALIAS_DEDUPLICATION_INVALID", REGISTRY)
        if not item["deployment_eligibility"] and item.get("reason_code") in {
            "HOLD_FORMAL_NODE_OR_AUTHORITY_UNRESOLVED",
            "HOLD_DEPLOYMENT_NOT_AUTHORIZED",
        }:
            _fail("OWNER_AUTHORITY_NOT_APPLIED", REGISTRY)
    if by_id["V3_MIX_EDLA_GL"].get("reason_code") != "HOLD_NODE_OFFLINE":
        _fail("V3_OFFLINE_HOLD_INVALID", REGISTRY)
    return registry


def _check_release_immutable() -> None:
    manifest = _load_json(RELEASE / "release_manifest.json")
    files_document = _load_json(RELEASE / "files_sha256.json")
    if not isinstance(manifest, dict) or not isinstance(files_document, dict):
        _fail("RELEASE_MANIFEST_INVALID", RELEASE)
    if manifest.get("release_version") != RELEASE_VERSION or manifest.get("release_sha256") != RELEASE_SHA256:
        _fail("RELEASE_IDENTITY_CHANGED", RELEASE / "release_manifest.json")
    identity = manifest.get("release_identity")
    if not isinstance(identity, dict) or _canonical_sha256(identity) != RELEASE_SHA256:
        _fail("RELEASE_IDENTITY_CHANGED", RELEASE / "release_manifest.json")
    if identity.get("policy_sha256") != POLICY_SHA256:
        _fail("POLICY_SHA256_MISMATCH", RELEASE / "release_manifest.json")
    files = files_document.get("files")
    if not isinstance(files, dict) or identity.get("files_sha256") != files:
        _fail("RELEASE_FILES_MANIFEST_INVALID", RELEASE / "files_sha256.json")
    for name, expected in files.items():
        path = RELEASE / str(name)
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            _fail("RELEASE_FILE_HASH_INVALID", path)
        if _raw_sha256(path) != expected:
            _fail("RELEASE_FILE_HASH_MISMATCH", path)
    if (ROOT / RELEASE / "bin/w7tp-small-agent").is_file():
        _fail("UNEXPECTED_RELEASE_RUNTIME_ENTRYPOINT", RELEASE / "bin/w7tp-small-agent")


def _check_deployer_contract() -> None:
    try:
        text = (ROOT / DEPLOYER).read_text(encoding="utf-8")
        tree = ast.parse(text, filename=DEPLOYER.as_posix())
    except (OSError, UnicodeError, SyntaxError):
        _fail("DEPLOYER_PARSE_FAILED", DEPLOYER)
    required_markers = (
        "--authority-registry",
        "OWNER_AUTHORIZED",
        OWNER_SCOPE,
        "LOCAL_SHELL",
        "HOLD_ROUTER_WRITE_NOT_AUTHORIZED",
        "HOLD_RELEASE_RUNTIME_ENTRYPOINT_MISSING",
    )
    if any(marker not in text for marker in required_markers):
        _fail("DEPLOYER_AUTHORITY_CONTRACT_MISSING", DEPLOYER)
    forbidden_calls = {"os.system", "os.popen", "eval", "exec", "subprocess.Popen"}

    def call_name(node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            prefix = call_name(node.value)
            return f"{prefix}.{node.attr}" if prefix else node.attr
        return ""

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and call_name(node.func) in forbidden_calls:
            _fail("UNSAFE_DEPLOYER_API", DEPLOYER)
    from tools.deploy_w7tp_small_agent_all_nodes import (
        DeploymentError,
        _safe_command,
        resolve_formal_nodes,
    )

    records = resolve_formal_nodes(ROOT, ROOT / REGISTRY)
    if [record.node_id for record in records] != list(FORMAL_NODE_IDS):
        _fail("DEPLOYER_FORMAL_NODE_SET_INVALID", DEPLOYER)
    if [
        record.node_id
        for record in records
        if isinstance(record.deployment_eligibility, dict)
        and record.deployment_eligibility.get("status") == "ELIGIBLE"
    ] != ["taiji01", "penguin"]:
        _fail("DEPLOYER_ELIGIBILITY_OVERLAY_INVALID", DEPLOYER)
    for command in (("mysql",), ("psql",), ("sqlite3",), ("nvram", "show")):
        try:
            _safe_command(command)
        except DeploymentError:
            continue
        _fail("PROHIBITED_WRITE_COMMAND_ACCEPTED", DEPLOYER)


def _check_sensitive_material() -> None:
    """Scan only the new authority artifacts for credential-shaped material."""

    inspected = (
        REGISTRY,
        SCHEMA,
        MAPPING_REPORT,
        DEPLOYER,
        TEST,
        Path(__file__).resolve().relative_to(ROOT),
    )
    patterns = (
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        re.compile(r"(?i)bearer\s+[A-Za-z0-9._~-]{20,}"),
    )
    for path in inspected:
        try:
            text = (ROOT / path).read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            _fail("SENSITIVE_SCAN_READ_FAILED", path)
        if any(pattern.search(text) is not None for pattern in patterns):
            _fail("RAW_SECRET_MATERIAL_FOUND", path)


def _check_compile_and_tests() -> None:
    if not (ROOT / TEST).is_file():
        _fail("FOCUSED_TEST_MISSING", TEST)
    source = (ROOT / TEST).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=TEST.as_posix())
    count = sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
        for node in ast.walk(tree)
    )
    if count != 18:
        _fail("FOCUSED_TEST_COUNT_MISMATCH", TEST)
    with tempfile.TemporaryDirectory(prefix="w7tp-authority-pyc-") as directory:
        for index, path in enumerate((DEPLOYER, TEST, Path(__file__).resolve().relative_to(ROOT))):
            try:
                py_compile.compile(
                    str(ROOT / path),
                    cfile=str(Path(directory) / f"{index}.pyc"),
                    doraise=True,
                )
            except py_compile.PyCompileError:
                _fail("PYTHON_COMPILE_FAILED", path)
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, str(ROOT / TEST)],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        shell=False,
        timeout=180,
    )
    transcript = result.stdout + result.stderr
    if result.returncode != 0 or not re.search(r"Ran\s+18\s+tests?\b", transcript) or not re.search(r"(?m)^OK$", transcript):
        _fail("FOCUSED_TEST_FAILED", TEST)


def verify() -> None:
    _check_protected()
    _check_registry()
    _check_release_immutable()
    _check_deployer_contract()
    _check_sensitive_material()
    _check_compile_and_tests()
    _check_protected()
    _check_release_immutable()


def main() -> int:
    try:
        verify()
    except VerificationFailure as error:
        print("STATE=HOLD_VERIFY_W7TP_SMALL_AGENT_NODE_AUTHORITY")
        print(f"REASON_CODE={error.reason_code}")
        print(f"FILE={error.file}")
        return 1
    print("STATE=PASS_VERIFY_W7TP_SMALL_AGENT_NODE_AUTHORITY")
    print(f"RUN_ID={RUN_ID}")
    print(f"AUTHORITY_REGISTRY={REGISTRY.as_posix()}")
    print("FORMAL_NODES=8")
    print("ELIGIBLE_NODES=2")
    print("ROUTER_NODES_HELD=1")
    print("TEST_COUNT=18")
    print(f"CANDIDATE_SCHEMA={SCHEMA.as_posix()}")
    print("REMOTE_PLATFORM_MAPPINGS=2")
    print("RELEASE_RUNTIME_ENTRYPOINT=HOLD_RELEASE_RUNTIME_ENTRYPOINT_MISSING")
    print("REMOTE_COMMANDS_EXECUTED=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
