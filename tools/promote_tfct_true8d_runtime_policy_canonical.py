#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Promote the verified TFCT TRUE8D runtime policy into its dedicated chain."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL_PROMOTION_V0_1"
EXPECTED_POLICY_SHA256 = (
    "d27230aba7a4ecd051f4169184c1fa5357ce5efa1d62019238d68991b0140960"
)

SOURCE_POLICY = Path("manifests/tfct_true8d_runtime_candidate_v0_1/policy.json")
SOURCE_PACKAGE_MANIFEST = Path(
    "manifests/tfct_true8d_runtime_candidate_v0_1/package_manifest.json"
)
RUNTIME_POLICY = Path(
    "runtime/total_field/candidate/tfct_true8d_runtime_policy_v0_1.json"
)
IMPLEMENTATION_REPORT = Path(
    "docs/total_field/TFCT_TRUE8D_RUNTIME_CANDIDATE_IMPLEMENTATION_REPORT.md"
)
PACKAGE_REPORT = Path(
    "docs/total_field/TFCT_TRUE8D_RUNTIME_CANDIDATE_PACKAGE_REPORT.md"
)
RUNTIME_VERIFIER = Path("scripts/verify/verify_tfct_true8d_runtime_candidate.py")
PACKAGE_VERIFIER = Path(
    "scripts/verify/verify_tfct_true8d_runtime_candidate_package.py"
)

CANONICAL_SOURCE_DIRECTORY = Path(
    "manifests/tfct_true8d_runtime_policy_canonical_v0_1"
)
TRACKED_POLICY = CANONICAL_SOURCE_DIRECTORY / "policy.json"
CANONICAL_MANIFEST = CANONICAL_SOURCE_DIRECTORY / "canonical_manifest.json"
PROMOTION_EVIDENCE = CANONICAL_SOURCE_DIRECTORY / "promotion_evidence.json"
ROLLBACK_MANIFEST = CANONICAL_SOURCE_DIRECTORY / "rollback_manifest.json"

VERSIONED_DIRECTORY = Path(
    "runtime/total_field/TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL_V0_1_D27230ABA7A4"
)
VERSIONED_CANONICAL = (
    VERSIONED_DIRECTORY / "TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL.json"
)
VERSIONED_MANIFEST = (
    VERSIONED_DIRECTORY / "TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL_MANIFEST.json"
)
VERSIONED_EVIDENCE = (
    VERSIONED_DIRECTORY / "TFCT_TRUE8D_RUNTIME_POLICY_PROMOTION_EVIDENCE.json"
)
ACTIVE_CANONICAL = Path(
    "runtime/total_field/active/ACTIVE_TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL.json"
)
ACTIVE_POINTER = Path(
    "runtime/total_field/active/ACTIVE_TFCT_TRUE8D_RUNTIME_POLICY_POINTER.txt"
)

SEMANTIC_SCOPE = (
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
SEMANTIC_LOCKS = {
    "D6": "Sovereign Privacy Field",
    "D7": "Generative Transmission & Resource Routing Field",
    "D8": "Red-Team Detour Alert & Quarantine Field",
    "commit_rule": "ALLOW_ONLY",
    "consensus_mode": "LOCAL_EQUIVALENCE_ONLY",
}
OPEN_PROBLEMS = (
    "OBSERVATION_DOMAIN_COMPLETENESS",
    "FIXED_POINT_EXISTENCE_THEOREM",
    "FIXED_POINT_UNIQUENESS_THEOREM",
    "GLOBAL_FINITE_CONVERGENCE_THEOREM",
    "DISTRIBUTED_CONSENSUS_PROTOCOL",
    "CANONICAL_TFID_HASH_CONTRACT",
    "PRODUCTION_ADI_ALGORITHM",
    "AGENT_PACKAGING",
    "PERFORMANCE_EVIDENCE",
)

CANONICAL_OUTPUTS = (
    TRACKED_POLICY,
    CANONICAL_MANIFEST,
    PROMOTION_EVIDENCE,
    ROLLBACK_MANIFEST,
    VERSIONED_CANONICAL,
    VERSIONED_MANIFEST,
    VERSIONED_EVIDENCE,
    ACTIVE_CANONICAL,
    ACTIVE_POINTER,
)


class PromotionFailure(ValueError):
    """Represent one stable promotion failure without exposing source payloads."""

    def __init__(self, reason_code: str, path: str = "") -> None:
        """Store a deterministic reason code and an optional safe path."""
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.path = path


@dataclass(frozen=True)
class VerificationResult:
    """Describe a successful deterministic source or active verification."""

    status: str
    policy_sha256: str


@dataclass(frozen=True)
class PromotionResult:
    """Describe a completed or already-complete promotion."""

    status: str
    files_written: tuple[str, ...]


def _duplicate_guard(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build a JSON object while rejecting duplicate member names."""
    value: dict[str, Any] = {}
    for key, nested in pairs:
        if key in value:
            raise PromotionFailure("JSON_DUPLICATE_KEY")
        value[key] = nested
    return value


def _reject_nonfinite(value: str) -> Any:
    """Reject decoder extensions for non-finite numbers."""
    raise PromotionFailure("JSON_NONFINITE_VALUE", value)


def _require_finite(value: Any) -> None:
    """Reject overflow and nested non-finite numeric values."""
    if isinstance(value, float) and not math.isfinite(value):
        raise PromotionFailure("JSON_NONFINITE_VALUE")
    if isinstance(value, dict):
        for nested in value.values():
            _require_finite(nested)
    elif isinstance(value, list):
        for nested in value:
            _require_finite(nested)


def load_strict_json(path: str | Path) -> Any:
    """Read strict UTF-8 JSON with duplicate and non-finite rejection."""
    source = Path(path)
    try:
        raw = source.read_bytes()
    except FileNotFoundError as error:
        raise PromotionFailure("SOURCE_FILE_MISSING", str(source)) from error
    except OSError as error:
        raise PromotionFailure("SOURCE_FILE_READ_FAILED", str(source)) from error
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise PromotionFailure("SOURCE_FILE_NOT_UTF8", str(source)) from error
    try:
        value = json.loads(
            text,
            object_pairs_hook=_duplicate_guard,
            parse_constant=_reject_nonfinite,
        )
        _require_finite(value)
        return value
    except PromotionFailure:
        raise
    except (json.JSONDecodeError, RecursionError) as error:
        raise PromotionFailure("STRICT_JSON_INVALID", str(source)) from error


def canonical_json(value: Any) -> str:
    """Serialize one JSON value with the locked deterministic settings."""
    try:
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except ValueError as error:
        raise PromotionFailure("JSON_NONFINITE_VALUE") from error
    except (TypeError, RecursionError) as error:
        raise PromotionFailure("JSON_NOT_CANONICALIZABLE") from error


def canonical_sha256(value: Any) -> str:
    """Return SHA-256 of the locked canonical JSON representation."""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _read_utf8(root: Path, relative: Path) -> str:
    """Read one approved evidence document as strict UTF-8."""
    path = root / relative
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise PromotionFailure("SOURCE_EVIDENCE_MISSING", str(relative)) from error
    except UnicodeError as error:
        raise PromotionFailure("SOURCE_EVIDENCE_NOT_UTF8", str(relative)) from error


def _require_object(value: Any, reason_code: str) -> dict[str, Any]:
    """Require a parsed JSON root to be an object."""
    if not isinstance(value, dict):
        raise PromotionFailure(reason_code)
    return value


def _expected_package_manifest() -> dict[str, Any]:
    """Build the exact accepted candidate package manifest."""
    return {
        "schema_version": "tfct_true8d_runtime_candidate_package_v0.1",
        "package_version": "v0.1",
        "status": "CANDIDATE",
        "source_policy": "policy.json",
        "runtime_target": str(RUNTIME_POLICY),
        "policy_sha256": EXPECTED_POLICY_SHA256,
        "materialization_mode": "EXPLICIT_ONLY",
        "canonical_promotion": False,
        "deploy": False,
        "restart": False,
    }


def _require_markers(text: str, markers: tuple[str, ...], path: Path) -> None:
    """Require deterministic PASS evidence markers without rerunning a suite."""
    for marker in markers:
        if marker not in text:
            raise PromotionFailure("SOURCE_PASS_EVIDENCE_INVALID", str(path))


def _check_policy_boundaries(policy: dict[str, Any]) -> None:
    """Verify the promoted engineering contract without changing its semantics."""
    if policy.get("status") != "CANDIDATE":
        raise PromotionFailure("SOURCE_POLICY_STATUS_INVALID", str(SOURCE_POLICY))
    if policy.get("consensus_mode") != "LOCAL_EQUIVALENCE_ONLY":
        raise PromotionFailure("SOURCE_CONSENSUS_BOUNDARY_INVALID", str(SOURCE_POLICY))
    if policy.get("distributed_consensus_status") != "OPEN_PROBLEM":
        raise PromotionFailure("SOURCE_DISTRIBUTED_CONSENSUS_INVALID", str(SOURCE_POLICY))
    if policy.get("adi_mode") != "DISABLED_UNLESS_EXPLICIT_TEST_FIXTURE":
        raise PromotionFailure("SOURCE_ADI_BOUNDARY_INVALID", str(SOURCE_POLICY))
    commit = policy.get("commit_rule")
    expected_commit = {
        "action": "COMMIT_PROPOSED_ONLY",
        "final_decision": "ALLOW",
        "fixed_point_status": "REACHED",
        "status": "CANDIDATE",
    }
    if commit != expected_commit:
        raise PromotionFailure("SOURCE_ALLOW_ONLY_COMMIT_INVALID", str(SOURCE_POLICY))
    sources = policy.get("candidate_only_sources")
    required_sources = {
        "LLM_PUSH",
        "SMALL_TRANSPORT_AGENT",
        "TOTAL_FIELD_PULL",
        "XIAOJ_CANDIDATE",
    }
    if not isinstance(sources, list) or not required_sources.issubset(sources):
        raise PromotionFailure("SOURCE_CANDIDATE_AUTHORITY_INVALID", str(SOURCE_POLICY))


def verify_source(root: str | Path = ROOT) -> VerificationResult:
    """Verify the accepted candidate source, package, hash, and PASS evidence."""
    base = Path(root)
    tracked = _require_object(
        load_strict_json(base / SOURCE_POLICY), "SOURCE_POLICY_NOT_OBJECT"
    )
    runtime = _require_object(
        load_strict_json(base / RUNTIME_POLICY), "RUNTIME_POLICY_NOT_OBJECT"
    )
    package = _require_object(
        load_strict_json(base / SOURCE_PACKAGE_MANIFEST),
        "SOURCE_PACKAGE_MANIFEST_NOT_OBJECT",
    )
    if canonical_json(tracked) != canonical_json(runtime):
        raise PromotionFailure("SOURCE_POLICY_MISMATCH", str(SOURCE_POLICY))
    digest = canonical_sha256(tracked)
    if digest != EXPECTED_POLICY_SHA256:
        raise PromotionFailure("SOURCE_POLICY_MISMATCH", str(SOURCE_POLICY))
    if package != _expected_package_manifest():
        raise PromotionFailure(
            "SOURCE_PACKAGE_MANIFEST_INVALID", str(SOURCE_PACKAGE_MANIFEST)
        )
    _check_policy_boundaries(tracked)

    implementation_report = _read_utf8(base, IMPLEMENTATION_REPORT)
    package_report = _read_utf8(base, PACKAGE_REPORT)
    runtime_verifier = _read_utf8(base, RUNTIME_VERIFIER)
    package_verifier = _read_utf8(base, PACKAGE_VERIFIER)
    _require_markers(
        implementation_report,
        (
            "TFCT_TRUE8D_RUNTIME_CANDIDATE_V0_1",
            "45/45 PASS",
            "PASS_VERIFY_TFCT_TRUE8D_RUNTIME_CANDIDATE",
            "15/15 PASS",
        ),
        IMPLEMENTATION_REPORT,
    )
    _require_markers(
        package_report,
        (
            "TFCT_TRUE8D_RUNTIME_CANDIDATE_POLICY_PACKAGE_V0_1",
            "PASS 15/15",
            "PASS_VERIFY_TFCT_TRUE8D_RUNTIME_CANDIDATE_PACKAGE",
            "CANONICAL_EQUIVALENCE=MATCH",
        ),
        PACKAGE_REPORT,
    )
    _require_markers(
        runtime_verifier,
        (
            "STATE=PASS_VERIFY_TFCT_TRUE8D_RUNTIME_CANDIDATE",
            'print("TEST_COUNT=45")',
        ),
        RUNTIME_VERIFIER,
    )
    _require_markers(
        package_verifier,
        (
            "STATE=PASS_VERIFY_TFCT_TRUE8D_RUNTIME_CANDIDATE_PACKAGE",
            'print("TEST_COUNT=15")',
        ),
        PACKAGE_VERIFIER,
    )
    return VerificationResult("MATCH", digest)


def _canonical_manifest_value() -> dict[str, Any]:
    """Build the deterministic canonical manifest."""
    return {
        "schema_version": "tfct_true8d_runtime_policy_canonical_manifest_v0.1",
        "canonical_scope": "TFCT_TRUE8D_RUNTIME_POLICY",
        "canonical_version": "v0.1",
        "status": "ACTIVE_CANONICAL",
        "state": "PASS",
        "source_candidate_run_id": "TFCT_TRUE8D_RUNTIME_CANDIDATE_V0_1",
        "source_package_run_id": (
            "TFCT_TRUE8D_RUNTIME_CANDIDATE_POLICY_PACKAGE_V0_1"
        ),
        "source_policy": "policy.json",
        "source_policy_sha256": EXPECTED_POLICY_SHA256,
        "semantic_scope": list(SEMANTIC_SCOPE),
        "distributed_consensus": "OPEN_PROBLEM",
        "production_adi": "OPEN_PROBLEM",
        "deploy": False,
        "restart": False,
    }


def _promotion_evidence_value() -> dict[str, Any]:
    """Build deterministic owner and accepted-PASS promotion evidence."""
    return {
        "schema_version": "tfct_true8d_runtime_policy_promotion_evidence_v0.1",
        "promotion_run_id": RUN_ID,
        "state": "PASS",
        "owner": {
            "owner_confirmation": "YES",
            "owner_decision": "確認升格",
            "owner_scope": "僅升格已通過驗證的 TFCT／TRUE8D Runtime Policy 與工程契約",
            "owner_excludes": [
                "THEOREM_PROMOTION",
                "DISTRIBUTED_CONSENSUS",
                "PRODUCTION_ADI",
                "DEPLOYMENT",
                "PERFORMANCE_CLAIMS",
            ],
        },
        "source_run_ids": {
            "runtime_candidate": "TFCT_TRUE8D_RUNTIME_CANDIDATE_V0_1",
            "candidate_package": (
                "TFCT_TRUE8D_RUNTIME_CANDIDATE_POLICY_PACKAGE_V0_1"
            ),
            "d3_candidate": "D3_COORDINATE_TRANSITION_V0_3_CANDIDATE",
            "document_consolidation": (
                "TFCT_TRUE8D_W7TP_8DGTE_SYSTEM_CONSOLIDATION_CANDIDATE_V0_1"
            ),
        },
        "accepted_validation": [
            {
                "stage": "D3_CANDIDATE",
                "status": "PASS",
                "test_count": "15/15",
            },
            {
                "stage": "D3_VERIFIER",
                "status": "PASS",
                "test_count": "4/4",
            },
            {
                "stage": "RUNTIME_REPLAY",
                "status": "PASS",
                "test_count": "4/4",
            },
            {
                "stage": "RUNTIME_REPLAY_VERIFIER",
                "status": "PASS",
                "test_count": "9/9",
            },
            {
                "stage": "RUNTIME_CANDIDATE",
                "status": "PASS_TFCT_TRUE8D_RUNTIME_CANDIDATE_IMPLEMENTED",
                "test_count": "45/45",
                "verifier": "PASS_VERIFY_TFCT_TRUE8D_RUNTIME_CANDIDATE",
            },
            {
                "stage": "CANDIDATE_PACKAGE",
                "status": "PASS_TFCT_TRUE8D_RUNTIME_CANDIDATE_PACKAGED",
                "test_count": "15/15",
                "verifier": (
                    "PASS_VERIFY_TFCT_TRUE8D_RUNTIME_CANDIDATE_PACKAGE"
                ),
            },
            {
                "stage": "DOCUMENT_INTEGRATION",
                "status": "PASS",
                "test_count": "8/8",
            },
        ],
        "policy_sha256": EXPECTED_POLICY_SHA256,
        "source_policy": str(SOURCE_POLICY),
        "runtime_policy": str(RUNTIME_POLICY),
        "source_documents": [
            str(IMPLEMENTATION_REPORT),
            str(PACKAGE_REPORT),
            str(RUNTIME_VERIFIER),
            str(PACKAGE_VERIFIER),
        ],
        "protected_files_unchanged": True,
        "other_active_canonical_write": False,
        "other_pointer_write": False,
        "d3_write": False,
        "packet_runtime_write": False,
        "db_write": False,
        "deploy": False,
        "restart": False,
        "router_write": False,
        "PATENT_CANDIDATE_REVIEW_REQUIRED": "YES",
    }


def _rollback_manifest_value() -> dict[str, Any]:
    """Build first-promotion rollback provenance for absent dedicated entries."""
    return {
        "schema_version": "tfct_true8d_runtime_policy_rollback_manifest_v0.1",
        "promotion_run_id": RUN_ID,
        "previous_active_pointer_exists": False,
        "previous_active_pointer_content": None,
        "previous_active_canonical_exists": False,
        "previous_active_canonical_sha256": None,
        "promoted_pointer": str(ACTIVE_POINTER),
        "promoted_canonical": str(VERSIONED_CANONICAL),
        "rollback_requires_owner_confirmation": True,
        "rollback_executed": False,
    }


def _runtime_envelope_value(policy: dict[str, Any]) -> dict[str, Any]:
    """Build the full runtime canonical envelope around the unchanged policy."""
    return {
        "schema_version": "tfct_true8d_runtime_policy_canonical_v0.1",
        "state": "PASS",
        "status": "ACTIVE_CANONICAL",
        "canonical_scope": "TFCT_TRUE8D_RUNTIME_POLICY",
        "canonical_version": "v0.1",
        "source_policy_sha256": EXPECTED_POLICY_SHA256,
        "policy": policy,
        "semantic_locks": dict(SEMANTIC_LOCKS),
        "open_problems": list(OPEN_PROBLEMS),
    }


def _json_file_text(value: Any) -> str:
    """Render a human-readable deterministic JSON file."""
    try:
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        ) + "\n"
    except (TypeError, ValueError, RecursionError) as error:
        raise PromotionFailure("CANONICAL_ARTIFACT_SERIALIZATION_FAILED") from error


def _artifact_payloads(root: Path, policy: dict[str, Any]) -> dict[Path, str]:
    """Build every promotion file before any filesystem mutation occurs."""
    manifest = _canonical_manifest_value()
    evidence = _promotion_evidence_value()
    rollback = _rollback_manifest_value()
    envelope = _runtime_envelope_value(policy)
    pointer_target = str((root / VERSIONED_CANONICAL).resolve()) + "\n"
    return {
        TRACKED_POLICY: _json_file_text(policy),
        CANONICAL_MANIFEST: _json_file_text(manifest),
        PROMOTION_EVIDENCE: _json_file_text(evidence),
        ROLLBACK_MANIFEST: _json_file_text(rollback),
        VERSIONED_CANONICAL: _json_file_text(envelope),
        VERSIONED_MANIFEST: _json_file_text(manifest),
        VERSIONED_EVIDENCE: _json_file_text(evidence),
        ACTIVE_CANONICAL: _json_file_text(envelope),
        ACTIVE_POINTER: pointer_target,
    }


def _atomic_write_new(path: Path, content: str) -> None:
    """Create one file through a deterministic temporary name and atomic replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tfct-promotion.tmp")
    if path.exists() or path.is_symlink() or temporary.exists() or temporary.is_symlink():
        raise PromotionFailure(
            "HOLD_EXISTING_RUNTIME_POLICY_CANONICAL_CONFLICT", str(path)
        )
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists() or path.is_symlink():
            raise PromotionFailure(
                "HOLD_EXISTING_RUNTIME_POLICY_CANONICAL_CONFLICT", str(path)
            )
        os.replace(temporary, path)
    except PromotionFailure:
        if temporary.exists() or temporary.is_symlink():
            temporary.unlink()
        raise
    except OSError as error:
        if temporary.exists() or temporary.is_symlink():
            temporary.unlink()
        raise PromotionFailure("CANONICAL_ATOMIC_WRITE_FAILED", str(path)) from error


def _load_artifact_object(root: Path, relative: Path, reason: str) -> dict[str, Any]:
    """Load one promoted JSON artifact as an object."""
    return _require_object(load_strict_json(root / relative), reason)


def _assert_equal(left: Any, right: Any, reason: str, path: Path) -> None:
    """Require canonical JSON equality for an explicit equivalence class."""
    if canonical_json(left) != canonical_json(right):
        raise PromotionFailure(reason, str(path))


def verify_active(root: str | Path = ROOT) -> VerificationResult:
    """Verify the dedicated tracked, versioned, Active, and Pointer chain."""
    base = Path(root)
    source_result = verify_source(base)
    source_policy = _load_artifact_object(
        base, SOURCE_POLICY, "SOURCE_POLICY_NOT_OBJECT"
    )
    tracked_policy = _load_artifact_object(
        base, TRACKED_POLICY, "TRACKED_CANONICAL_POLICY_NOT_OBJECT"
    )
    manifest = _load_artifact_object(
        base, CANONICAL_MANIFEST, "CANONICAL_MANIFEST_NOT_OBJECT"
    )
    evidence = _load_artifact_object(
        base, PROMOTION_EVIDENCE, "PROMOTION_EVIDENCE_NOT_OBJECT"
    )
    rollback = _load_artifact_object(
        base, ROLLBACK_MANIFEST, "ROLLBACK_MANIFEST_NOT_OBJECT"
    )
    envelope = _load_artifact_object(
        base, VERSIONED_CANONICAL, "RUNTIME_CANONICAL_NOT_OBJECT"
    )
    runtime_manifest = _load_artifact_object(
        base, VERSIONED_MANIFEST, "RUNTIME_CANONICAL_MANIFEST_NOT_OBJECT"
    )
    runtime_evidence = _load_artifact_object(
        base, VERSIONED_EVIDENCE, "RUNTIME_PROMOTION_EVIDENCE_NOT_OBJECT"
    )
    active = _load_artifact_object(
        base, ACTIVE_CANONICAL, "ACTIVE_CANONICAL_NOT_OBJECT"
    )

    _assert_equal(
        source_policy,
        tracked_policy,
        "TRACKED_CANONICAL_POLICY_MISMATCH",
        TRACKED_POLICY,
    )
    _assert_equal(
        tracked_policy,
        envelope.get("policy"),
        "RUNTIME_CANONICAL_POLICY_MISMATCH",
        VERSIONED_CANONICAL,
    )
    if canonical_sha256(tracked_policy) != EXPECTED_POLICY_SHA256:
        raise PromotionFailure("CANONICAL_POLICY_HASH_MISMATCH", str(TRACKED_POLICY))
    _assert_equal(
        manifest,
        _canonical_manifest_value(),
        "CANONICAL_MANIFEST_MISMATCH",
        CANONICAL_MANIFEST,
    )
    _assert_equal(
        manifest,
        runtime_manifest,
        "RUNTIME_CANONICAL_MANIFEST_MISMATCH",
        VERSIONED_MANIFEST,
    )
    _assert_equal(
        evidence,
        _promotion_evidence_value(),
        "PROMOTION_EVIDENCE_MISMATCH",
        PROMOTION_EVIDENCE,
    )
    _assert_equal(
        evidence,
        runtime_evidence,
        "RUNTIME_PROMOTION_EVIDENCE_MISMATCH",
        VERSIONED_EVIDENCE,
    )
    _assert_equal(
        rollback,
        _rollback_manifest_value(),
        "ROLLBACK_MANIFEST_MISMATCH",
        ROLLBACK_MANIFEST,
    )
    _assert_equal(
        envelope,
        _runtime_envelope_value(tracked_policy),
        "RUNTIME_CANONICAL_ENVELOPE_MISMATCH",
        VERSIONED_CANONICAL,
    )
    _assert_equal(
        envelope,
        active,
        "ACTIVE_CANONICAL_MISMATCH",
        ACTIVE_CANONICAL,
    )

    locks = envelope.get("semantic_locks")
    if locks != SEMANTIC_LOCKS:
        raise PromotionFailure("SEMANTIC_LOCK_MISMATCH", str(VERSIONED_CANONICAL))
    if envelope.get("open_problems") != list(OPEN_PROBLEMS):
        raise PromotionFailure("OPEN_PROBLEMS_NOT_PRESERVED", str(VERSIONED_CANONICAL))
    _check_policy_boundaries(tracked_policy)
    if manifest.get("distributed_consensus") != "OPEN_PROBLEM":
        raise PromotionFailure("DISTRIBUTED_CONSENSUS_NOT_OPEN", str(CANONICAL_MANIFEST))
    if manifest.get("production_adi") != "OPEN_PROBLEM":
        raise PromotionFailure("PRODUCTION_ADI_NOT_OPEN", str(CANONICAL_MANIFEST))

    pointer_path = base / ACTIVE_POINTER
    try:
        pointer = pointer_path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise PromotionFailure("ACTIVE_POINTER_MISSING", str(ACTIVE_POINTER)) from error
    except UnicodeError as error:
        raise PromotionFailure("ACTIVE_POINTER_NOT_UTF8", str(ACTIVE_POINTER)) from error
    expected_target = str((base / VERSIONED_CANONICAL).resolve())
    if pointer.strip() != expected_target:
        raise PromotionFailure("ACTIVE_POINTER_TARGET_INVALID", str(ACTIVE_POINTER))
    target = Path(pointer.strip())
    if not target.is_file() or target.resolve() != (base / VERSIONED_CANONICAL).resolve():
        raise PromotionFailure("ACTIVE_POINTER_TARGET_MISSING", str(ACTIVE_POINTER))
    return VerificationResult("MATCH", source_result.policy_sha256)


def promote(
    root: str | Path = ROOT,
    owner_confirmation: str = "",
) -> PromotionResult:
    """Perform the owner-authorized, dedicated, no-unknown-overwrite promotion."""
    base = Path(root)
    if owner_confirmation != "YES":
        raise PromotionFailure("OWNER_CONFIRMATION_REQUIRED")
    verify_source(base)
    existing = tuple(
        relative
        for relative in CANONICAL_OUTPUTS
        if (base / relative).exists() or (base / relative).is_symlink()
    )
    if existing:
        if len(existing) == len(CANONICAL_OUTPUTS):
            try:
                verify_active(base)
            except PromotionFailure as error:
                raise PromotionFailure(
                    "HOLD_EXISTING_RUNTIME_POLICY_CANONICAL_CONFLICT",
                    error.path,
                ) from error
            return PromotionResult("ALREADY_PROMOTED", ())
        raise PromotionFailure(
            "HOLD_EXISTING_RUNTIME_POLICY_CANONICAL_CONFLICT", str(existing[0])
        )

    policy = _load_artifact_object(base, SOURCE_POLICY, "SOURCE_POLICY_NOT_OBJECT")
    payloads = _artifact_payloads(base, policy)
    written: list[str] = []
    for relative in CANONICAL_OUTPUTS:
        _atomic_write_new(base / relative, payloads[relative])
        written.append(str(relative))
    verify_active(base)
    return PromotionResult("PROMOTED", tuple(written))


def rollback_plan(root: str | Path = ROOT) -> dict[str, Any]:
    """Return a deterministic read-only rollback plan requiring renewed authority."""
    base = Path(root)
    verify_active(base)
    rollback = _load_artifact_object(
        base, ROLLBACK_MANIFEST, "ROLLBACK_MANIFEST_NOT_OBJECT"
    )
    return {
        "state": "ROLLBACK_PLAN_ONLY",
        "promotion_run_id": RUN_ID,
        "owner_confirmation_required": "YES",
        "rollback_requires_owner_confirmation": True,
        "previous_active_pointer_exists": rollback[
            "previous_active_pointer_exists"
        ],
        "steps": [
            "OBTAIN_NEW_OWNER_CONFIRMATION",
            "VERIFY_ROLLBACK_MANIFEST",
            "VERIFY_CURRENT_DEDICATED_ACTIVE_CHAIN",
            "RESTORE_PREVIOUS_DEDICATED_ENTRY_ONLY_IF_REAUTHORIZED",
            "RERUN_DEDICATED_CHAIN_VERIFICATION",
        ],
        "write_executed": False,
    }


def _parser() -> argparse.ArgumentParser:
    """Build the four-command deterministic promotion CLI."""
    parser = argparse.ArgumentParser(
        description="Promote or verify the dedicated TFCT TRUE8D runtime policy chain."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("verify-source")
    promote_parser = subparsers.add_parser("promote")
    promote_parser.add_argument("--owner-confirmation", required=True)
    subparsers.add_parser("verify-active")
    subparsers.add_parser("rollback-plan")
    return parser


def _print_failure(error: PromotionFailure) -> int:
    """Print one stable HOLD state without a traceback or payload disclosure."""
    if error.reason_code == "SOURCE_POLICY_MISMATCH":
        state = "HOLD_SOURCE_POLICY_MISMATCH"
    elif "EXISTING_RUNTIME_POLICY_CANONICAL_CONFLICT" in error.reason_code:
        state = "HOLD_EXISTING_RUNTIME_POLICY_CANONICAL_CONFLICT"
    elif error.reason_code == "OWNER_CONFIRMATION_REQUIRED":
        state = "HOLD_OWNER_CONFIRMATION_REQUIRED"
    else:
        state = "HOLD_TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL_PROMOTION"
    print(f"STATE={state}")
    print(f"REASON_CODE={error.reason_code}")
    if error.path:
        print(f"FILE={error.path}")
    return 1


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch source verification, promotion, active verification, or rollback plan."""
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "verify-source":
            result = verify_source(ROOT)
            print("STATE=PASS_VERIFY_SOURCE_TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL")
            print("CANONICAL_EQUIVALENCE=MATCH")
            print(f"SOURCE_POLICY_SHA256={result.policy_sha256}")
            return 0
        if arguments.command == "promote":
            result = promote(ROOT, owner_confirmation=arguments.owner_confirmation)
            print("STATE=PASS_TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL_PROMOTED")
            print(f"PROMOTION_RESULT={result.status}")
            print(f"FILES_WRITTEN={len(result.files_written)}")
            return 0
        if arguments.command == "verify-active":
            result = verify_active(ROOT)
            print("STATE=PASS_VERIFY_ACTIVE_TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL")
            print("CANONICAL_EQUIVALENCE=MATCH")
            print(f"SOURCE_POLICY_SHA256={result.policy_sha256}")
            return 0
        plan = rollback_plan(ROOT)
        print("STATE=PASS_ROLLBACK_PLAN_TFCT_TRUE8D_RUNTIME_POLICY_CANONICAL")
        print("OWNER_CONFIRMATION_REQUIRED=YES")
        print(f"WRITE_EXECUTED={str(plan['write_executed']).upper()}")
        for index, step in enumerate(plan["steps"], start=1):
            print(f"STEP_{index}={step}")
        return 0
    except PromotionFailure as error:
        return _print_failure(error)


if __name__ == "__main__":
    raise SystemExit(main())
