#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic verifier for the promoted TFCT TRUE8D runtime policy."""

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
RUN_ID = "TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL_PROMOTION_V0_1"
POLICY_SHA256 = "d27230aba7a4ecd051f4169184c1fa5357ce5efa1d62019238d68991b0140960"

CANDIDATE_PACKAGE = "manifests/tfct_true8d_runtime_candidate_v0_1"
CANDIDATE_POLICY = f"{CANDIDATE_PACKAGE}/policy.json"
CANDIDATE_PACKAGE_MANIFEST = f"{CANDIDATE_PACKAGE}/package_manifest.json"
RUNTIME_CANDIDATE_POLICY = (
    "runtime/total_field/candidate/tfct_true8d_runtime_policy_v0_1.json"
)

CANONICAL_SOURCE_DIR = "manifests/tfct_true8d_runtime_policy_canonical_v0_1"
TRACKED_POLICY = f"{CANONICAL_SOURCE_DIR}/policy.json"
CANONICAL_MANIFEST = f"{CANONICAL_SOURCE_DIR}/canonical_manifest.json"
PROMOTION_EVIDENCE = f"{CANONICAL_SOURCE_DIR}/promotion_evidence.json"
ROLLBACK_MANIFEST = f"{CANONICAL_SOURCE_DIR}/rollback_manifest.json"

RUNTIME_CANONICAL_DIR = (
    "runtime/total_field/TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL_V0_1_D27230ABA7A4"
)
RUNTIME_CANONICAL = (
    f"{RUNTIME_CANONICAL_DIR}/TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL.json"
)
RUNTIME_CANONICAL_MANIFEST = (
    f"{RUNTIME_CANONICAL_DIR}/TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL_MANIFEST.json"
)
RUNTIME_PROMOTION_EVIDENCE = (
    f"{RUNTIME_CANONICAL_DIR}/TFCT_TRUE8D_RUNTIME_POLICY_PROMOTION_EVIDENCE.json"
)

ACTIVE_CANONICAL = (
    "runtime/total_field/active/ACTIVE_TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL.json"
)
ACTIVE_POINTER = (
    "runtime/total_field/active/ACTIVE_TFCT_TRUE8D_RUNTIME_POLICY_POINTER.txt"
)
POINTER_TARGET = str(ROOT / RUNTIME_CANONICAL)
ACTIVE_TRUE8D = (
    "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_CANONICAL.json"
)

PROMOTION_TOOL = "tools/promote_tfct_true8d_runtime_policy_canonical.py"
FOCUSED_TEST = "tests/test_promote_tfct_true8d_runtime_policy_canonical.py"
VERIFIER = "scripts/verify/verify_tfct_true8d_runtime_policy_canonical.py"

SOURCE_JSON_FILES = (
    TRACKED_POLICY,
    CANONICAL_MANIFEST,
    PROMOTION_EVIDENCE,
    ROLLBACK_MANIFEST,
)
RUNTIME_JSON_FILES = (
    RUNTIME_CANONICAL,
    RUNTIME_CANONICAL_MANIFEST,
    RUNTIME_PROMOTION_EVIDENCE,
)
JSON_FILES = SOURCE_JSON_FILES + RUNTIME_JSON_FILES + (ACTIVE_CANONICAL,)
PYTHON_FILES = (PROMOTION_TOOL, FOCUSED_TEST, VERIFIER)
DELIVERABLES = JSON_FILES + PYTHON_FILES + (ACTIVE_POINTER,)

EXPECTED_SEMANTIC_SCOPE = (
    "FINITE_CONVERGENCE",
    "FIXED_POINT_DETECTION",
    "CYCLE_DETECTION",
    "TIMEOUT_DETECTION",
    "D8_ADJUDICATION",
    "ALLOW_ONLY_COMMIT",
    "TFID_CANDIDATE_CONTRACT",
    "TOTAL_FIELD_HASH_CONTRACT",
    "CANDIDATE_ONLY_LLM",
    "LOCAL_EQUIVALENCE_ONLY",
)
EXPECTED_OPEN_PROBLEMS = {
    "OBSERVATION_DOMAIN_COMPLETENESS",
    "FIXED_POINT_EXISTENCE_THEOREM",
    "FIXED_POINT_UNIQUENESS_THEOREM",
    "GLOBAL_FINITE_CONVERGENCE_THEOREM",
    "DISTRIBUTED_CONSENSUS_PROTOCOL",
    "CANONICAL_TFID_HASH_CONTRACT",
    "PRODUCTION_ADI_ALGORITHM",
    "AGENT_PACKAGING",
    "PERFORMANCE_EVIDENCE",
}
EXPECTED_SEMANTIC_LOCKS = {
    "D6": "Sovereign Privacy Field",
    "D7": "Generative Transmission & Resource Routing Field",
    "D8": "Red-Team Detour Alert & Quarantine Field",
    "commit_rule": "ALLOW_ONLY",
    "consensus_mode": "LOCAL_EQUIVALENCE_ONLY",
}

# These are the pre-promotion paths already protected by the accepted verifiers.
# The two dedicated promotion entries are intentionally absent from this tuple.
HEAD_PROTECTED = (
    ".gitignore",
    ACTIVE_TRUE8D,
    "runtime/total_field/active/ACTIVE_CODEX_TOTAL_FIELD_GLOBAL_AGENT_DOMAIN_POINTER.txt",
    "runtime/total_field/active/ACTIVE_DOMAIN_BETA_DEPLOYMENT_POINTER.txt",
    "runtime/total_field/active/ACTIVE_POS_OFFICIAL_CHAIN_POINTER.txt",
    "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_POINTER.txt",
    "runtime/total_field/active/ACTIVE_TRUE8D_ALLNODE_WITH_ROUTER_POINTER.txt",
    "runtime/total_field/active/ACTIVE_TRUE8D_ROUTER_ALLNODE_MERGE_POINTER.txt",
    "runtime/total_field/active/ACTIVE_TRUE8D_ROUTER_BOUNDARY_POINTER.txt",
    "runtime/total_field/active/ACTIVE_V4_TRUE8D_TIPO_LANDING_POINTER.txt",
)

# Exact accepted pre-promotion byte baselines.  No repository discovery is used.
BASELINE_SHA256 = {
    CANDIDATE_POLICY: "a9b6ccbabea14e577cff0aeffba059b1be660ff461e65bd4d439fb35d96a4d69",
    CANDIDATE_PACKAGE_MANIFEST: "678d07dad0fc39dea75fada9e30f949542b25f182732ae7c3ac45e705d6aebcb",
    RUNTIME_CANDIDATE_POLICY: "7aa603dda45b42cf27582ed8fa3956e2eda24b8fd9734238b6a17efc02ec7adf",
    "tools/tfct_true8d_runtime_candidate.py": "c573b767c8a83e8d27da2f9ecca03aa86b9f4fda891e6bcd62725b08ebc80cab",
    "tools/eightd_gte_parser_candidate.py": "afe1010549cc0314e9023f5a4fc89c9ddadf6fe5c86687484e9db3cf9c3ec381",
    "tools/total_field_candidate_gateway.py": "545c4f843f3e81340181b8fb904186418a5e32d2ca87b875f30e6cdf4259a792",
    "tools/w7tp_small_transport_agent_candidate.py": "f94e80f0e6e08512df000a270b26c026c9c26b7b07fae3d5d8cdc7ce3e8637d9",
    "tools/xiaoj_candidate_adapter.py": "107dfbdeb5e137b9a28288c44f47cd20bed7abfd9e4101ab17ba7e7bae4246c9",
    "tools/adi_index_strategy_candidate.py": "d772fb6023dea9cbb4fcf8f1c5e809f9100912d39fb4f1351f6d49d641382f26",
    "tests/test_tfct_true8d_runtime_candidate.py": "f62f7b6cc3efdf05a3b5486c5d53aa1f66aa964590fcab794a491ee419a59910",
    "scripts/verify/verify_tfct_true8d_runtime_candidate.py": "054ee14f3532f210fc8f37d9c98e0affd3c057301aa0e963f19d48aad7b33838",
    "scripts/verify/verify_tfct_true8d_runtime_candidate_package.py": "1b70012d5731b4127ce67fb7470537f5d1a778eefbcd79032ef97b6774714dc4",
    "docs/total_field/TFCT_TRUE8D_RUNTIME_CANDIDATE_IMPLEMENTATION_REPORT.md": "1b3caae1abacd1ba57195b438b1554ab96028f5c3a51c550d5ca021868b54257",
    "docs/total_field/TFCT_TRUE8D_RUNTIME_CANDIDATE_PACKAGE_REPORT.md": "4aef5058405520d7e99e1425445a06e6b7f42d2d3271cc6d01fc19a723dfdadb",
    "tools/d3_coordinate_transition_candidate.py": "b1e67f1d22d0e53785f3939885dcb690907cb68071f7f3a682ce368a356bb918",
    "tools/w7tp_packet_inference_runtime.py": "7918b485b83d1523c98636366c3bd41aaf3b514b0a1b35b4b1ffad066bc1205b",
}


@dataclass(frozen=True)
class VerificationFailure(Exception):
    """One stable verification failure without sensitive payload content."""

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
    """Read one approved path as strict UTF-8 text."""

    try:
        return (ROOT / path).read_text(encoding="utf-8")
    except FileNotFoundError:
        _fail("CANONICAL_DELIVERABLE_MISSING", path)
    except UnicodeError:
        _fail("CANONICAL_DELIVERABLE_NOT_UTF8", path)
    raise AssertionError("unreachable")


def _duplicate_guard(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build a JSON object while rejecting duplicate member names."""

    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("DUPLICATE_JSON_MEMBER")
        result[key] = value
    return result


def _reject_nonfinite_constant(value: str) -> Any:
    """Reject JavaScript-style non-finite JSON constants."""

    raise ValueError(f"NONFINITE_JSON_CONSTANT:{value}")


def _ensure_finite(value: Any) -> None:
    """Reject numeric overflow and nested non-finite values."""

    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("NONFINITE_JSON_NUMBER")
    if isinstance(value, dict):
        for nested in value.values():
            _ensure_finite(nested)
    elif isinstance(value, list):
        for nested in value:
            _ensure_finite(nested)


def _load_json(path: str) -> Any:
    """Parse one JSON document using the strict canonical input contract."""

    try:
        value = json.loads(
            _read(path),
            object_pairs_hook=_duplicate_guard,
            parse_constant=_reject_nonfinite_constant,
        )
        _ensure_finite(value)
        return value
    except json.JSONDecodeError as error:
        _fail("STRICT_JSON_INVALID", path, int(error.lineno or 1))
    except ValueError:
        _fail("STRICT_JSON_INVALID", path)
    raise AssertionError("unreachable")


def _canonical_bytes(value: Any, source: str) -> bytes:
    """Serialize a value with the locked deterministic JSON settings."""

    try:
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        _fail("CANONICAL_SERIALIZATION_FAILED", source)
    raise AssertionError("unreachable")


def _canonical_hash(value: Any, source: str) -> str:
    """Return the canonical SHA-256 identity of one JSON value."""

    return hashlib.sha256(_canonical_bytes(value, source)).hexdigest()


def _byte_hash(path: str) -> str:
    """Return the exact byte SHA-256 of one protected path."""

    try:
        return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    except FileNotFoundError:
        _fail("PROTECTED_FILE_MISSING", path)
    raise AssertionError("unreachable")


def _require_object(value: Any, path: str, reason: str) -> dict[str, Any]:
    """Require a JSON object without coercion."""

    if not isinstance(value, dict):
        _fail(reason, path)
    return value


def _check_presence_and_utf8() -> None:
    """Require exactly the promotion artifacts consumed by this verifier."""

    for path in DELIVERABLES:
        if not (ROOT / path).is_file():
            _fail("CANONICAL_DELIVERABLE_MISSING", path)
        _read(path)


def _check_package_source(
    candidate_policy: dict[str, Any],
    runtime_candidate: dict[str, Any],
) -> None:
    """Reconfirm the accepted package identity without rerunning its tests."""

    package = _require_object(
        _load_json(CANDIDATE_PACKAGE_MANIFEST),
        CANDIDATE_PACKAGE_MANIFEST,
        "PACKAGE_MANIFEST_ROOT_INVALID",
    )
    expected = {
        "schema_version": "tfct_true8d_runtime_candidate_package_v0.1",
        "package_version": "v0.1",
        "status": "CANDIDATE",
        "source_policy": "policy.json",
        "runtime_target": RUNTIME_CANDIDATE_POLICY,
        "policy_sha256": POLICY_SHA256,
        "materialization_mode": "EXPLICIT_ONLY",
        "canonical_promotion": False,
        "deploy": False,
        "restart": False,
    }
    if package != expected:
        _fail("SOURCE_PACKAGE_MANIFEST_INVALID", CANDIDATE_PACKAGE_MANIFEST)
    if _canonical_bytes(candidate_policy, CANDIDATE_POLICY) != _canonical_bytes(
        runtime_candidate, RUNTIME_CANDIDATE_POLICY
    ):
        _fail("SOURCE_POLICY_RUNTIME_MISMATCH", CANDIDATE_POLICY)
    if _canonical_hash(candidate_policy, CANDIDATE_POLICY) != POLICY_SHA256:
        _fail("SOURCE_POLICY_HASH_MISMATCH", CANDIDATE_POLICY)


def _check_canonical_manifest(manifest: dict[str, Any]) -> None:
    """Validate the promoted scope, provenance, and retained open boundaries."""

    exact_values = {
        "schema_version": "tfct_true8d_runtime_policy_canonical_manifest_v0.1",
        "canonical_scope": "TFCT_TRUE8D_RUNTIME_POLICY",
        "canonical_version": "v0.1",
        "status": "ACTIVE_CANONICAL",
        "state": "PASS",
        "source_candidate_run_id": "TFCT_TRUE8D_RUNTIME_CANDIDATE_V0_1",
        "source_package_run_id": "TFCT_TRUE8D_RUNTIME_CANDIDATE_POLICY_PACKAGE_V0_1",
        "source_policy": "policy.json",
        "source_policy_sha256": POLICY_SHA256,
        "distributed_consensus": "OPEN_PROBLEM",
        "production_adi": "OPEN_PROBLEM",
        "deploy": False,
        "restart": False,
    }
    for key, expected in exact_values.items():
        actual = manifest.get(key)
        if type(actual) is not type(expected) or actual != expected:
            _fail("CANONICAL_MANIFEST_VALUE_INVALID", CANONICAL_MANIFEST)
    scope = manifest.get("semantic_scope")
    if not isinstance(scope, list) or tuple(scope) != EXPECTED_SEMANTIC_SCOPE:
        _fail("CANONICAL_SEMANTIC_SCOPE_INVALID", CANONICAL_MANIFEST)


def _walk_values(value: Any) -> tuple[Any, ...]:
    """Flatten scalar evidence values in deterministic traversal order."""

    values: list[Any] = []
    if isinstance(value, dict):
        for nested in value.values():
            values.extend(_walk_values(nested))
    elif isinstance(value, list):
        for nested in value:
            values.extend(_walk_values(nested))
    else:
        values.append(value)
    return tuple(values)


def _has_key_value(value: Any, key: str, expected: Any) -> bool:
    """Find one exact key/value assertion anywhere in an evidence tree."""

    if isinstance(value, dict):
        if key in value and type(value[key]) is type(expected) and value[key] == expected:
            return True
        return any(_has_key_value(nested, key, expected) for nested in value.values())
    if isinstance(value, list):
        return any(_has_key_value(nested, key, expected) for nested in value)
    return False


def _check_promotion_evidence(evidence: dict[str, Any]) -> None:
    """Require accepted PASS provenance, Owner authority, and safety evidence."""

    scalars = set(_walk_values(evidence))
    required_values = {
        RUN_ID,
        "TFCT_TRUE8D_RUNTIME_CANDIDATE_V0_1",
        "TFCT_TRUE8D_RUNTIME_CANDIDATE_POLICY_PACKAGE_V0_1",
        "PASS_TFCT_TRUE8D_RUNTIME_CANDIDATE_IMPLEMENTED",
        "PASS_TFCT_TRUE8D_RUNTIME_CANDIDATE_PACKAGED",
        "PASS_VERIFY_TFCT_TRUE8D_RUNTIME_CANDIDATE",
        "PASS_VERIFY_TFCT_TRUE8D_RUNTIME_CANDIDATE_PACKAGE",
        POLICY_SHA256,
        CANDIDATE_POLICY,
        RUNTIME_CANDIDATE_POLICY,
    }
    if not required_values.issubset(scalars):
        _fail("PROMOTION_EVIDENCE_INCOMPLETE", PROMOTION_EVIDENCE)
    if not ({45, "45", "45/45"} & scalars):
        _fail("RUNTIME_TEST_EVIDENCE_MISSING", PROMOTION_EVIDENCE)
    if not ({15, "15", "15/15"} & scalars):
        _fail("PACKAGE_TEST_EVIDENCE_MISSING", PROMOTION_EVIDENCE)
    if not _has_key_value(evidence, "owner_confirmation", "YES"):
        _fail("OWNER_CONFIRMATION_EVIDENCE_MISSING", PROMOTION_EVIDENCE)
    if not (
        _has_key_value(evidence, "protected_files_unchanged", True)
        or _has_key_value(evidence, "protected_files_unchanged", "YES")
    ):
        _fail("PROTECTED_FILE_EVIDENCE_MISSING", PROMOTION_EVIDENCE)
    if not (
        _has_key_value(evidence, "PATENT_CANDIDATE_REVIEW_REQUIRED", "YES")
        or _has_key_value(evidence, "patent_candidate_review_required", True)
    ):
        _fail("PATENT_REVIEW_EVIDENCE_MISSING", PROMOTION_EVIDENCE)


def _check_rollback_manifest(rollback: dict[str, Any]) -> None:
    """Validate informational rollback provenance without executing rollback."""

    required_keys = {
        "promotion_run_id",
        "previous_active_pointer_exists",
        "previous_active_pointer_content",
        "previous_active_canonical_sha256",
        "promoted_pointer",
        "promoted_canonical",
        "rollback_requires_owner_confirmation",
    }
    if not required_keys.issubset(rollback):
        _fail("ROLLBACK_MANIFEST_INCOMPLETE", ROLLBACK_MANIFEST)
    if rollback.get("promotion_run_id") != RUN_ID:
        _fail("ROLLBACK_RUN_ID_INVALID", ROLLBACK_MANIFEST)
    if type(rollback.get("previous_active_pointer_exists")) is not bool:
        _fail("ROLLBACK_PREVIOUS_POINTER_STATE_INVALID", ROLLBACK_MANIFEST)
    if rollback.get("promoted_pointer") != ACTIVE_POINTER:
        _fail("ROLLBACK_PROMOTED_POINTER_INVALID", ROLLBACK_MANIFEST)
    if rollback.get("promoted_canonical") != RUNTIME_CANONICAL:
        _fail("ROLLBACK_PROMOTED_CANONICAL_INVALID", ROLLBACK_MANIFEST)
    if rollback.get("rollback_requires_owner_confirmation") is not True:
        _fail("ROLLBACK_OWNER_CONFIRMATION_NOT_REQUIRED", ROLLBACK_MANIFEST)
    existed = rollback["previous_active_pointer_exists"]
    previous_content = rollback["previous_active_pointer_content"]
    previous_hash = rollback["previous_active_canonical_sha256"]
    if not existed and (previous_content is not None or previous_hash is not None):
        _fail("ROLLBACK_ABSENT_BASELINE_INVALID", ROLLBACK_MANIFEST)
    if existed and not isinstance(previous_content, str):
        _fail("ROLLBACK_POINTER_CONTENT_INVALID", ROLLBACK_MANIFEST)
    if previous_hash is not None and not re.fullmatch(r"[0-9a-f]{64}", previous_hash):
        _fail("ROLLBACK_PREVIOUS_HASH_INVALID", ROLLBACK_MANIFEST)


def _check_policy_semantics(policy: dict[str, Any]) -> None:
    """Lock ALLOW-only commit, candidate authority, local equivalence, and ADI."""

    commit = policy.get("commit_rule")
    if not isinstance(commit, dict):
        _fail("POLICY_COMMIT_RULE_MISSING", TRACKED_POLICY)
    required_commit = {
        "action": "COMMIT_PROPOSED_ONLY",
        "final_decision": "ALLOW",
        "fixed_point_status": "REACHED",
        "status": "CANDIDATE",
    }
    if commit != required_commit:
        _fail("ALLOW_ONLY_COMMIT_LOCK_INVALID", TRACKED_POLICY)
    if policy.get("stable_decisions") != ["ALLOW", "HOLD", "BLOCK", "QUARANTINE"]:
        _fail("D8_DECISION_SET_INVALID", TRACKED_POLICY)
    if policy.get("decision_priority") != ["QUARANTINE", "BLOCK", "HOLD", "ALLOW"]:
        _fail("D8_PRIORITY_INVALID", TRACKED_POLICY)
    candidate_sources = policy.get("candidate_only_sources")
    if not isinstance(candidate_sources, list) or not {
        "LLM_PUSH",
        "SMALL_TRANSPORT_AGENT",
        "TOTAL_FIELD_PULL",
        "XIAOJ_CANDIDATE",
    }.issubset(candidate_sources):
        _fail("CANDIDATE_ONLY_LLM_BOUNDARY_INVALID", TRACKED_POLICY)
    forbidden_authority = policy.get("authority_forbidden_keys")
    if not isinstance(forbidden_authority, list) or not {
        "commit_applied",
        "committed",
        "tfid",
        "total_field_hash",
    }.issubset(forbidden_authority):
        _fail("CANDIDATE_AUTHORITY_GUARD_INVALID", TRACKED_POLICY)
    if policy.get("consensus_mode") != "LOCAL_EQUIVALENCE_ONLY":
        _fail("LOCAL_EQUIVALENCE_LOCK_INVALID", TRACKED_POLICY)
    if policy.get("distributed_consensus_status") != "OPEN_PROBLEM":
        _fail("DISTRIBUTED_CONSENSUS_NOT_OPEN", TRACKED_POLICY)
    if policy.get("adi_mode") != "DISABLED_UNLESS_EXPLICIT_TEST_FIXTURE":
        _fail("PRODUCTION_ADI_BOUNDARY_INVALID", TRACKED_POLICY)


def _active_dimension_map(active: dict[str, Any]) -> dict[str, Any]:
    """Extract the pre-existing Active TRUE8D English semantic definitions."""

    dimensions = active.get("dimensions")
    if not isinstance(dimensions, list):
        _fail("ACTIVE_TRUE8D_DIMENSIONS_INVALID", ACTIVE_TRUE8D)
    result: dict[str, Any] = {}
    for item in dimensions:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            result[item["id"]] = item.get("field_en")
    return result


def _check_runtime_envelope(
    envelope: dict[str, Any],
    policy: dict[str, Any],
    active_true8d: dict[str, Any],
) -> None:
    """Validate the versioned canonical envelope and immutable semantic locks."""

    expected = {
        "schema_version": "tfct_true8d_runtime_policy_canonical_v0.1",
        "state": "PASS",
        "status": "ACTIVE_CANONICAL",
        "canonical_scope": "TFCT_TRUE8D_RUNTIME_POLICY",
        "canonical_version": "v0.1",
        "source_policy_sha256": POLICY_SHA256,
    }
    for key, value in expected.items():
        if envelope.get(key) != value:
            _fail("RUNTIME_CANONICAL_ENVELOPE_INVALID", RUNTIME_CANONICAL)
    if _canonical_bytes(envelope.get("policy"), RUNTIME_CANONICAL) != _canonical_bytes(
        policy, TRACKED_POLICY
    ):
        _fail("RUNTIME_CANONICAL_POLICY_MISMATCH", RUNTIME_CANONICAL)
    locks = envelope.get("semantic_locks")
    if locks != EXPECTED_SEMANTIC_LOCKS:
        _fail("RUNTIME_SEMANTIC_LOCK_INVALID", RUNTIME_CANONICAL)
    active_dimensions = _active_dimension_map(active_true8d)
    for dimension in ("D6", "D7", "D8"):
        if active_dimensions.get(dimension) != EXPECTED_SEMANTIC_LOCKS[dimension]:
            _fail("ACTIVE_TRUE8D_SEMANTIC_CONFLICT", ACTIVE_TRUE8D)
    open_problems = envelope.get("open_problems")
    if not isinstance(open_problems, list) or not EXPECTED_OPEN_PROBLEMS.issubset(
        open_problems
    ):
        _fail("OPEN_PROBLEMS_NOT_PRESERVED", RUNTIME_CANONICAL)


def _check_json_identity() -> None:
    """Check source, versioned, mirror, manifest, and evidence equivalence."""

    candidate_policy = _require_object(
        _load_json(CANDIDATE_POLICY), CANDIDATE_POLICY, "SOURCE_POLICY_ROOT_INVALID"
    )
    runtime_candidate = _require_object(
        _load_json(RUNTIME_CANDIDATE_POLICY),
        RUNTIME_CANDIDATE_POLICY,
        "RUNTIME_CANDIDATE_POLICY_ROOT_INVALID",
    )
    tracked_policy = _require_object(
        _load_json(TRACKED_POLICY), TRACKED_POLICY, "TRACKED_POLICY_ROOT_INVALID"
    )
    manifest = _require_object(
        _load_json(CANONICAL_MANIFEST),
        CANONICAL_MANIFEST,
        "CANONICAL_MANIFEST_ROOT_INVALID",
    )
    evidence = _require_object(
        _load_json(PROMOTION_EVIDENCE),
        PROMOTION_EVIDENCE,
        "PROMOTION_EVIDENCE_ROOT_INVALID",
    )
    rollback = _require_object(
        _load_json(ROLLBACK_MANIFEST),
        ROLLBACK_MANIFEST,
        "ROLLBACK_MANIFEST_ROOT_INVALID",
    )
    runtime_envelope = _require_object(
        _load_json(RUNTIME_CANONICAL),
        RUNTIME_CANONICAL,
        "RUNTIME_CANONICAL_ROOT_INVALID",
    )
    runtime_manifest = _require_object(
        _load_json(RUNTIME_CANONICAL_MANIFEST),
        RUNTIME_CANONICAL_MANIFEST,
        "RUNTIME_MANIFEST_ROOT_INVALID",
    )
    runtime_evidence = _require_object(
        _load_json(RUNTIME_PROMOTION_EVIDENCE),
        RUNTIME_PROMOTION_EVIDENCE,
        "RUNTIME_EVIDENCE_ROOT_INVALID",
    )
    active_envelope = _require_object(
        _load_json(ACTIVE_CANONICAL),
        ACTIVE_CANONICAL,
        "ACTIVE_CANONICAL_ROOT_INVALID",
    )
    active_true8d = _require_object(
        _load_json(ACTIVE_TRUE8D),
        ACTIVE_TRUE8D,
        "ACTIVE_TRUE8D_ROOT_INVALID",
    )

    _check_package_source(candidate_policy, runtime_candidate)
    candidate_bytes = _canonical_bytes(candidate_policy, CANDIDATE_POLICY)
    for path, policy in (
        (RUNTIME_CANDIDATE_POLICY, runtime_candidate),
        (TRACKED_POLICY, tracked_policy),
    ):
        if _canonical_bytes(policy, path) != candidate_bytes:
            _fail("CANONICAL_POLICY_EQUIVALENCE_MISMATCH", path)
        if _canonical_hash(policy, path) != POLICY_SHA256:
            _fail("CANONICAL_POLICY_HASH_MISMATCH", path)

    _check_canonical_manifest(manifest)
    _check_promotion_evidence(evidence)
    _check_rollback_manifest(rollback)
    _check_policy_semantics(tracked_policy)
    _check_runtime_envelope(runtime_envelope, tracked_policy, active_true8d)

    if _canonical_bytes(manifest, CANONICAL_MANIFEST) != _canonical_bytes(
        runtime_manifest, RUNTIME_CANONICAL_MANIFEST
    ):
        _fail("CANONICAL_MANIFEST_MIRROR_MISMATCH", RUNTIME_CANONICAL_MANIFEST)
    if _canonical_bytes(evidence, PROMOTION_EVIDENCE) != _canonical_bytes(
        runtime_evidence, RUNTIME_PROMOTION_EVIDENCE
    ):
        _fail("PROMOTION_EVIDENCE_MIRROR_MISMATCH", RUNTIME_PROMOTION_EVIDENCE)
    if _canonical_bytes(runtime_envelope, RUNTIME_CANONICAL) != _canonical_bytes(
        active_envelope, ACTIVE_CANONICAL
    ):
        _fail("ACTIVE_CANONICAL_MIRROR_MISMATCH", ACTIVE_CANONICAL)


def _check_pointer() -> None:
    """Require the dedicated Pointer to select the immutable versioned target."""

    pointer = _read(ACTIVE_POINTER)
    if pointer.strip() != POINTER_TARGET:
        _fail("ACTIVE_POINTER_TARGET_INVALID", ACTIVE_POINTER)
    if not Path(pointer.strip()).is_file():
        _fail("ACTIVE_POINTER_TARGET_MISSING", ACTIVE_POINTER)


def _compile_python() -> None:
    """Compile exactly the three promotion Python files outside the repository."""

    with tempfile.TemporaryDirectory(prefix="tfct-canonical-compile-") as directory:
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
    """Render a direct Python call target as a stable dotted name."""

    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _call_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _subprocess_executable(node: ast.Call) -> str | None:
    """Extract a literal subprocess executable when statically available."""

    if not node.args:
        return None
    command = node.args[0]
    if not isinstance(command, (ast.List, ast.Tuple)) or not command.elts:
        return None
    executable = command.elts[0]
    if isinstance(executable, ast.Constant) and isinstance(executable.value, str):
        return executable.value
    return None


def _check_python_boundaries() -> None:
    """Reject dynamic code, entropy, network, DB, and operational side effects."""

    forbidden_import_roots = {
        "anthropic",
        "datetime",
        "ftplib",
        "http",
        "httpx",
        "importlib",
        "openai",
        "pickle",
        "psycopg",
        "psycopg2",
        "pymysql",
        "random",
        "requests",
        "secrets",
        "socket",
        "sqlalchemy",
        "sqlite3",
        "time",
        "urllib",
        "uuid",
    }
    forbidden_calls = {
        "__import__",
        "compile",
        "eval",
        "exec",
        "importlib.import_module",
        "os.getrandom",
        "os.popen",
        "os.system",
        "os.urandom",
        "pickle.dump",
        "pickle.dumps",
        "pickle.load",
        "pickle.loads",
        "random.random",
        "secrets.token_bytes",
        "secrets.token_hex",
        "secrets.token_urlsafe",
    }
    subprocess_calls = {
        "subprocess.call",
        "subprocess.check_call",
        "subprocess.check_output",
        "subprocess.run",
        "subprocess.Popen",
    }
    forbidden_executables = {
        "ansible",
        "ansible-playbook",
        "az",
        "curl",
        "docker",
        "ftp",
        "helm",
        "kubectl",
        "mysql",
        "nc",
        "netcat",
        "odoo",
        "psql",
        "scp",
        "service",
        "sftp",
        "ssh",
        "systemctl",
        "wget",
    }
    for path in PYTHON_FILES:
        source = _read(path)
        for marker in ("TO" + "DO", "FIX" + "ME"):
            position = source.find(marker)
            if position >= 0:
                _fail(
                    "UNFINISHED_SOURCE_MARKER",
                    path,
                    source[:position].count("\n") + 1,
                )
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError as error:
            _fail("PYTHON_AST_INVALID", path, int(error.lineno or 1))
        for node in ast.walk(tree):
            if isinstance(node, ast.Pass):
                _fail("PASS_STATEMENT_FORBIDDEN", path, node.lineno)
            if (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant)
                and node.value.value is Ellipsis
            ):
                _fail("ELLIPSIS_FORBIDDEN", path, node.lineno)
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = (
                    [alias.name for alias in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or ""]
                )
                if any(
                    name.split(".", 1)[0] in forbidden_import_roots for name in names
                ):
                    _fail("FORBIDDEN_IMPORT", path, node.lineno)
            if isinstance(node, ast.Call):
                name = _call_name(node.func)
                if name in forbidden_calls:
                    _fail("FORBIDDEN_EXECUTION_API", path, node.lineno)
                if name in subprocess_calls:
                    for keyword in node.keywords:
                        if (
                            keyword.arg == "shell"
                            and isinstance(keyword.value, ast.Constant)
                            and keyword.value.value is True
                        ):
                            _fail("FORBIDDEN_SHELL_SUBPROCESS", path, node.lineno)
                    executable = _subprocess_executable(node)
                    if executable in forbidden_executables:
                        _fail("FORBIDDEN_OPERATIONAL_SUBPROCESS", path, node.lineno)


def _check_sensitive_literals() -> None:
    """Reject credential material and assigned raw member plaintext."""

    patterns = (
        re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        re.compile(
            r"(?i)(?:api[_-]?key|password|raw[_-]?token|client[_-]?secret)"
            r"\s*[=:]\s*['\"]?[A-Za-z0-9._-]{16,}"
        ),
        re.compile(
            r"(?i)(?:member[_ -]?plaintext|raw[_ -]?member[_ -]?data)"
            r"\s*[=:]\s*['\"]?[^\s'\"]{8,}"
        ),
    )
    for path in DELIVERABLES:
        source = _read(path)
        for pattern in patterns:
            match = pattern.search(source)
            if match:
                _fail(
                    "SENSITIVE_LITERAL_DETECTED",
                    path,
                    source[: match.start()].count("\n") + 1,
                )


def _check_protected_files() -> None:
    """Protect all pre-existing Active/Pointer and accepted implementation inputs."""

    for path in HEAD_PROTECTED:
        diff = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", path],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if diff.returncode == 1:
            _fail("OTHER_ACTIVE_OR_POINTER_CHANGED", path)
        if diff.returncode not in (0, 1):
            _fail("PROTECTED_DIFF_CHECK_FAILED", path)
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
        _fail("OTHER_ACTIVE_OR_POINTER_CHANGED", changed)
    for path, expected in BASELINE_SHA256.items():
        if _byte_hash(path) != expected:
            _fail("PROTECTED_BASELINE_CHANGED", path)


def _run_focused_test() -> None:
    """Run only the 25-case canonical-promotion focused test."""

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
    if "Ran 25 tests" not in result.stdout:
        _fail("FOCUSED_TEST_COUNT_MISMATCH", FOCUSED_TEST)
    if not re.search(r"^OK\s*$", result.stdout, re.MULTILINE):
        _fail("FOCUSED_TEST_NOT_OK", FOCUSED_TEST)
    if re.search(
        r"\bskipped\b|expected failures|unexpected successes", result.stdout
    ):
        _fail("FOCUSED_TEST_NOT_STRICT", FOCUSED_TEST)


def _run_verify_active() -> None:
    """Require the promotion tool's independent active-chain verification."""

    result = subprocess.run(
        [sys.executable, str(ROOT / PROMOTION_TOOL), "verify-active"],
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        _fail("PROMOTION_TOOL_VERIFY_ACTIVE_FAILED", PROMOTION_TOOL)
    if not re.search(r"^STATE=PASS[^\r\n]*$", result.stdout, re.MULTILINE):
        _fail("PROMOTION_TOOL_VERIFY_ACTIVE_STATE_INVALID", PROMOTION_TOOL)


def verify() -> None:
    """Run the focused promotion verification sequence."""

    _check_presence_and_utf8()
    for path in JSON_FILES:
        _load_json(path)
    _check_json_identity()
    _check_pointer()
    _compile_python()
    _check_python_boundaries()
    _check_sensitive_literals()
    _check_protected_files()
    _run_focused_test()
    _run_verify_active()


def main() -> int:
    """Print a stable machine-readable result without traceback disclosure."""

    try:
        verify()
    except VerificationFailure as failure:
        print("STATE=HOLD_VERIFY_TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL")
        print(f"REASON_CODE={failure.reason_code}")
        print(f"FILE={failure.file}")
        print(f"LINE={failure.line}")
        return 1
    except Exception:
        print("STATE=HOLD_VERIFY_TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL")
        print("REASON_CODE=UNEXPECTED_VERIFIER_FAILURE")
        print(f"FILE={VERIFIER}")
        print("LINE=1")
        return 1
    print("STATE=PASS_VERIFY_TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL")
    print(f"RUN_ID={RUN_ID}")
    print("TEST_COUNT=25")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
